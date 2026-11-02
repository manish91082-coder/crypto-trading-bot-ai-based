"""
Step 23: 4H relative brain (which large coins beat the other large coins over the next 1 / 5 days, seen on 4H candles).
Protocol: logs/strategy_1d_step23_4h/STEP23_PROTOCOL_PREREGISTERED.md (SHA256 locked before any 4H model is trained).
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core_rows_1d as CR
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
import step15_slow_relative_1d as S15
import step19_large_caps_1d as S19
import step22_pre2020_exam_1d as S22
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step23_4h"
PROTO_NAME = "STEP23_PROTOCOL_PREREGISTERED.md"
UNI1H, PRE1H = S13.UNI / "1h", DATA_DIR / "universe_pre2020" / "1h"
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30")
END_BAR = END + pd.Timedelta(hours=20)
FINAL_T = pd.Timestamp("2026-10-01")
PRE_START, PRE_END = pd.Timestamp("2018-02-01"), pd.Timestamp("2019-12-31")
HS = (6, 30)
CAP, N_HOLD, KEEP, U_SIZE, T_SIZE = 10_000.0, 5, 10, 20, 30
COST, COST_STRESS, CONTROL_SEED = 0.0025, 0.0040, 23
BONF_LO, BONF_HI = 0.625, 99.375
BASE = ["r1", "r3", "r6", "r18", "r42", "r84", "dist_hi30", "dist_lo30", "dist_hi90", "atr_pct", "range_atr", "body_atr",
        "upwick_atr", "lowick_atr", "vol_ratio30", "trades_ratio30", "taker_buy_ratio", "taker_ratio_6", "taker_ratio_chg",
        "rv6", "bar_hour", "btc_r1", "btc_r6", "btc_r42"]
XR = ["r1", "r6", "r42", "vol_ratio30", "taker_buy_ratio", "dist_hi30", "atr_pct"]
FEATS = BASE + [f"xr_{c}" for c in XR]
assert len(FEATS) == 31


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bars_4h(path):
    h = pd.read_csv(path, parse_dates=["timestamp"])
    assert h.timestamp.dtype.kind == "M", f"{path}: timestamps not parsed"
    h = h.sort_values("timestamp")
    h["bar"] = h.timestamp.dt.floor("4h")
    g = h.groupby("bar")
    b = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last(),
                          volume=g.volume.sum(), trades=g.trades.sum(), tb=g.taker_buy_base.sum(), nh=g.size()))
    return b.reindex(pd.date_range(b.index.min(), b.index.max(), freq="4h"))


def features(b, btc_close):
    o, hi, lo, c, v = b.open, b.high, b.low, b.close, b.volume
    f = pd.DataFrame(index=b.index)
    for n in (1, 3, 6, 18, 42, 84):
        f[f"r{n}"] = c.pct_change(n, fill_method=None)
    pc = c.shift(1)
    tr = pd.concat([hi - lo, (hi - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1, skipna=False)
    atr = tr.rolling(14, min_periods=10).mean()
    f["dist_hi30"] = (c - hi.rolling(30, min_periods=20).max()) / atr
    f["dist_lo30"] = (c - lo.rolling(30, min_periods=20).min()) / atr
    f["dist_hi90"] = (c - hi.rolling(90, min_periods=60).max()) / atr
    f["atr_pct"] = atr / c
    f["range_atr"] = (hi - lo) / atr
    f["body_atr"] = (c - o) / atr
    f["upwick_atr"] = (hi - np.maximum(o, c)) / atr
    f["lowick_atr"] = (np.minimum(o, c) - lo) / atr
    f["vol_ratio30"] = v / v.rolling(30, min_periods=20).mean()
    f["trades_ratio30"] = b.trades / b.trades.rolling(30, min_periods=20).mean()
    f["taker_buy_ratio"] = b.tb / v
    f["taker_ratio_6"] = f.taker_buy_ratio.rolling(6, min_periods=4).mean()
    f["taker_ratio_chg"] = f.taker_buy_ratio - f.taker_ratio_6
    f["rv6"] = f.r1.rolling(6, min_periods=4).std()
    f["bar_hour"] = b.index.hour
    for n in (1, 6, 42):
        f[f"btc_r{n}"] = btc_close.pct_change(n, fill_method=None).reindex(b.index).values
    return f.replace([np.inf, -np.inf], np.nan)


def forward(b, h):
    """fwd = open(t+1+h)/open(t+1) - 1 (NaN if either bar is missing), known = open time of bar t+1+h."""
    o, ts = b.open.values, b.index.values
    n = len(o)
    i = np.arange(n)
    ok = i + 1 + h <= n - 1
    f = np.full(n, np.nan)
    f[ok] = o[i[ok] + 1 + h] / o[i[ok] + 1] - 1
    k = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    k[ok] = ts[i[ok] + 1 + h]
    return f, k


def daily_members(data, last, cand, size, first_day, last_day):
    """Eligible (30d mean USD vol >= $2M and >= 120 candles) coins of `cand`, top-`size` by 30d mean USD volume per day."""
    vol = S19.usd30({s: data[s] for s in cand}, last)
    rows = []
    for s in cand:
        df = data[s]
        real = (df.timestamp <= last[s]).values
        idx = np.arange(len(df))
        u = vol[s].values
        ok = real & (u >= S13.LIQ_MIN_USD) & (idx + 1 >= S15.MIN_HIST) & (idx >= 60) & \
            (df.timestamp >= first_day).values & (df.timestamp <= last_day).values
        rows.append(pd.DataFrame(dict(symbol=s, date=df.timestamp.values[ok], usd30=u[ok])))
    R = pd.concat(rows, ignore_index=True)
    R["urank"] = R.groupby("date").usd30.rank(ascending=False, method="first")
    return R[R.urank <= size].reset_index(drop=True)


def crosscheck(b, raw1d):
    d = b.dropna(subset=["open"]).copy()
    d["day"] = d.index.normalize()
    g = d.groupby("day")
    a = pd.DataFrame(dict(o=g.open.first(), h=g.high.max(), l=g.low.min(), c=g.close.last(), v=g.volume.sum()))
    r = raw1d.set_index("timestamp").join(a, how="inner")
    ok = (np.isclose(r.o, r.open, rtol=1e-9) & np.isclose(r.h, r.high, rtol=1e-9) & np.isclose(r.l, r.low, rtol=1e-9)
          & np.isclose(r.c, r.close, rtol=1e-9) & np.isclose(r.v, r.volume, rtol=1e-6))
    return int(len(r)), int((~ok).sum())


def build_rows(members_by_univ, folder, btc_close, raw1d=None):
    """members_by_univ: {name: DataFrame(symbol, date)}. Rows = the 6 bars of day d+1 for every (coin, d) member."""
    out = {k: [] for k in members_by_univ}
    px, xc = {}, [0, 0]
    coins = sorted(set().union(*[set(m.symbol) for m in members_by_univ.values()]))
    for s in coins:
        b = bars_4h(folder / f"{s}_1h_full.csv.gz")
        f = features(b, btc_close)
        for h in HS:
            f[f"fwd{h}"], f[f"known{h}"] = forward(b, h)
        f["open"], f["close"] = b.open, b.close
        if raw1d is not None:
            n, bad = crosscheck(b, raw1d[s])
            xc[0] += n
            xc[1] += bad
        px[s] = b[["open", "close"]]
        for k, m in members_by_univ.items():
            ds = m.loc[m.symbol == s, "date"].values
            if not len(ds):
                continue
            times = (ds[:, None] + np.timedelta64(1, "D") + np.arange(6) * np.timedelta64(4, "h")).ravel()
            sub = f.reindex(times)
            sub = sub[sub.open.notna()].copy()
            sub["symbol"], sub["bar"] = s, sub.index
            out[k].append(sub.reset_index(drop=True))
    res = {}
    for k, parts in out.items():
        R = pd.concat(parts, ignore_index=True)
        for c in XR:
            R[f"xr_{c}"] = R.groupby("bar")[c].rank(pct=True)
        for h in HS:
            med = R.groupby("bar")[f"fwd{h}"].transform("median")
            R[f"rel{h}"] = R[f"fwd{h}"] - med
            R[f"label{h}"] = np.where(R[f"rel{h}"].isna(), np.nan, (R[f"rel{h}"] > 0).astype(float))
        res[k] = R
    return res, px, xc


def fit(X, y):
    return HistGradientBoostingClassifier(random_state=0, **S11.KW).fit(X, y)


def wf(TR, TE, feats, label, known, shuffle=False, seed=0):
    rng = np.random.default_rng(seed)
    preds = []
    for T in pd.date_range(START, END, freq="MS"):
        nxt = T + pd.offsets.MonthBegin(1)
        tr = TR[(TR[known] < T) & TR[label].notna()]
        assert (tr.bar < T).all()
        y = tr[label].values.astype(int)
        if shuffle:
            y = rng.permutation(y)
        te = TE[(TE.bar >= T) & (TE.bar < nxt)]
        m = fit(tr[feats].values, y)
        preds.append(pd.Series(m.predict_proba(te[feats].values)[:, 1], index=te.index))
    return pd.concat(preds).reindex(TE.index)


def auc_ci(R, p, label, lo=2.5, hi=97.5):
    m = R[label].notna() & p.notna()
    return S13.auc_ci(R[label][m].values.astype(int), p[m].values, R.bar[m].dt.to_period("M").astype(str).values, lo, hi)


def sim4h(rows, h, px, cost, invest=1.0, n=N_HOLD, keep=KEEP):
    by_bar = {t: g.sort_values(["score", "symbol"], ascending=[False, True]).symbol.values
              for t, g in rows.dropna(subset=["score"]).groupby("bar")}
    grid = pd.date_range(START, END_BAR, freq="4h")
    o, c, lastb = {}, {}, {}
    for s in set(rows.symbol):
        b = px[s]
        lastb[s] = b.close.last_valid_index()
        cf = b.close.reindex(grid).ffill()
        o[s] = b.open.reindex(grid).fillna(cf.shift(1)).values
        c[s] = cf.values
    cash, pos, trades, eq = CAP, {}, [], []
    sell_o, buy_o = [], []

    def sell(s, price, t, why):
        nonlocal cash
        p = pos.pop(s)
        cash += p["units"] * price * (1 - cost)
        trades.append(dict(symbol=s, entry_time=p["t"], exit_time=t, reason=why, cost=p["cost"],
                           pnl=p["units"] * price * (1 - cost) - p["cost"]))

    for k, t in enumerate(grid):
        for s in [s for s in pos if t > lastb[s]]:
            sell(s, float(px[s].close.loc[lastb[s]]), t, "data_end")
        for s in sell_o:
            if s in pos:
                sell(s, o[s][k], t, "rebalance_exit")
        e0 = cash + sum(p["units"] * o[s][k] for s, p in pos.items())
        for s in buy_o:
            if s in pos or len(pos) >= n or t > lastb[s] or not np.isfinite(o[s][k]):
                continue
            a = min(invest * e0 / n, cash / (1 + cost))
            if a < 10:
                continue
            cash -= a * (1 + cost)
            pos[s] = dict(units=a / o[s][k], cost=a * (1 + cost), t=t)
        assert cash >= -1e-6
        eq.append(cash + sum(p["units"] * c[s][k] for s, p in pos.items()))
        sell_o, buy_o = [], []
        if (k + 1) % h:
            continue
        ranked = list(by_bar.get(t, []))
        rank = {s: i + 1 for i, s in enumerate(ranked)}
        kept = [s for s in pos if rank.get(s, 10 ** 9) <= keep]
        sell_o = [s for s in pos if s not in kept]
        buy_o = [s for s in ranked[:n] if s not in pos][:n - len(kept)]
    for s in list(pos):
        sell(s, c[s][len(grid) - 1], grid[-1], "end_of_test")
    tr = pd.DataFrame(trades)
    assert abs(CAP + tr.pnl.sum() - cash) < 1e-6
    E = pd.Series(eq, index=grid)
    return dict(final=cash, eq=E, trades=tr)


def summarize4h(res):
    E = res["eq"]
    daily = E[E.index.hour == 20]
    a = np.r_[CAP, daily.values]
    pk = np.maximum.accumulate(a)
    dd = float(((pk - a) / pk).max())
    cagr = (res["final"] / CAP) ** (365.25 / (END - START).days) - 1
    ye = daily.groupby(daily.index.year).last()
    yr = (ye / ye.shift(1).fillna(CAP) - 1) * 100
    tr = res["trades"]
    r = (tr.pnl / tr.cost).values
    lo, hi = S11.block_ci(r, pd.to_datetime(tr.entry_time).dt.to_period("M").astype(str).values)
    return dict(final=round(float(res["final"]), 2), cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd * 100, 2),
                calmar=round(cagr / dd, 3), trades=int(len(tr)), avg_trade_pct=round(float(r.mean() * 100), 3),
                trade_ci_low_pct=round(lo * 100, 3), trade_ci_high_pct=round(hi * 100, 3),
                avg_hold_hours=round(float((tr.exit_time - tr.entry_time).dt.total_seconds().mean() / 3600), 1),
                **{f"ret_{y}": round(float(v), 2) for y, v in yr.items()})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha_file(OUT / PROTO_NAME)
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_)
    split = pd.read_csv(S15.SPLIT)
    assert sha_file(S15.SPLIT) == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    A, B = set(split[split.half == "A_design"].symbol), set(split[split.half == "B_confirm"].symbol)

    # ---------------- universes ----------------
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", UNI1H, END)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    known = list(data_k)
    Ute = daily_members(data, last, known + sorted(B & set(data)), U_SIZE, START - pd.Timedelta(days=1), END - pd.Timedelta(days=1))
    Utr = daily_members(data, last, known + sorted(A & set(data)), T_SIZE, pd.Timestamp("2020-01-01"), END - pd.Timedelta(days=1))
    u19 = pd.read_csv(S19.OUT / "universe_U.csv", parse_dates=["date"])
    mine = Ute[Ute.date >= START]
    u19 = u19[u19.date <= END - pd.Timedelta(days=1)]
    g0 = dict(a_universe_equals_step19=set(zip(mine.symbol, mine.date)) == set(zip(u19.symbol, u19.date)))
    claims.update(test_member_days=len(Ute), train_member_days=len(Utr), test_coins=int(Ute.symbol.nunique()), train_coins=int(Utr.symbol.nunique()))
    print("universes", claims, g0, f"({time.time()-t0:.0f}s)", flush=True)

    # ---------------- 1D comparator (must reproduce $74,452) ----------------
    rows19 = pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    px1 = {s: data[s].set_index("timestamp")[["open", "low", "close"]] for s in set(rows19.symbol) | {"BTCUSDT"}}
    r1d = S22.simulate(rows19, START, END, px1, last, 1.0, N_HOLD, KEEP)
    g0["b_reproduce_1d_100"] = abs(r1d["final"] - 74452) < 1.0
    one_d = S22.summary(r1d, START, END)
    btc = S22.summary(S22.btc_hold(px1, START, END, COST), START, END)
    raw1d = {s: pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"]) for s in set(Ute.symbol) | set(Utr.symbol)}
    del px1

    # ---------------- 4H rows ----------------
    btc_close = bars_4h(UNI1H / "BTCUSDT_1h_full.csv.gz").close
    R, px, xc = build_rows(dict(train=Utr, test=Ute), UNI1H, btc_close, raw1d)
    TR, TE = R["train"], R["test"]
    TE = TE[(TE.bar >= START) & (TE.bar <= END_BAR)].reset_index(drop=True)
    claims["crosscheck_4h_vs_1d"] = dict(coin_days=xc[0], mismatched=xc[1], share=xc[1] / max(xc[0], 1))
    g0["c_crosscheck_lt_1pct"] = claims["crosscheck_4h_vs_1d"]["share"] < 0.01
    claims.update(train_rows=len(TR), test_rows=len(TE))
    print("rows", len(TR), len(TE), claims["crosscheck_4h_vs_1d"], f"({time.time()-t0:.0f}s)", flush=True)
    del raw1d

    # ---------------- G1 pipeline sanity (R6) ----------------
    rng = np.random.default_rng(42)
    TRp, TEp = TR.copy(), TE.copy()
    TRp["planted"] = TRp.label6 + rng.normal(0, 2.79, len(TRp))
    TEp["planted"] = TEp.label6 + rng.normal(0, 2.79, len(TEp))
    TRp["leak"], TEp["leak"] = TRp.rel6, TEp.rel6
    claims["sanity_planted"] = auc_ci(TEp, wf(TRp, TEp, FEATS + ["planted"], "label6", "known6"), "label6")
    claims["sanity_leak"] = auc_ci(TEp, wf(TRp, TEp, FEATS + ["leak"], "label6", "known6"), "label6")
    del TRp, TEp
    g1 = claims["sanity_planted"]["auc"] >= 0.55 and claims["sanity_leak"]["auc"] > 0.95
    print("G1", round(claims["sanity_planted"]["auc"], 4), round(claims["sanity_leak"]["auc"], 4), g1, f"({time.time()-t0:.0f}s)", flush=True)

    # ---------------- brains + portfolios ----------------
    runs = dict(ONE_D_100=one_d, BTC_HOLD=btc)
    out = TE[["symbol", "bar", "fwd6", "rel6", "label6", "fwd30", "rel30", "label30"]].copy()
    for h in HS:
        for lab, sh in (("AI", False), ("CONTROL", True)):
            p = wf(TR, TE, FEATS, f"label{h}", f"known{h}", sh, CONTROL_SEED)
            out[f"R{h}_{lab}"] = p.values
            claims[f"R{h}_{lab}_skill"] = auc_ci(TE, p, f"label{h}", BONF_LO, BONF_HI)
            print(f"R{h} {lab}", {k: round(v, 4) for k, v in claims[f"R{h}_{lab}_skill"].items()}, f"({time.time()-t0:.0f}s)", flush=True)
            for name, cost in ((f"R{h}_{lab}", COST),) + (((f"R{h}_AI_cost040", COST_STRESS),) if lab == "AI" else ()):
                res = sim4h(TE[["symbol", "bar"]].assign(score=p.values), h, px, cost)
                res["eq"].to_csv(OUT / f"{name}_equity.csv", header=["equity"], index_label="bar")
                res["trades"].to_csv(OUT / f"{name}_trades.csv", index=False)
                runs[name] = summarize4h(res)
                print(" ", name, runs[name], flush=True)
    out.to_csv(OUT / "test_predictions_4h.csv", index=False)
    claims["portfolio"] = runs

    # ---------------- G4: frozen final brains on 2018-19 ----------------
    U22 = pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date"], parse_dates=["date"])
    btc_pre = bars_4h(PRE1H / "BTCUSDT_1h_full.csv.gz").close
    Rp, _, _ = build_rows(dict(pre=U22), PRE1H, btc_pre)
    P = Rp["pre"]
    P = P[(P.bar >= PRE_START) & (P.bar <= PRE_END + pd.Timedelta(hours=20))].reset_index(drop=True)
    claims["pre2020_rows"] = len(P)
    for h in HS:
        tr = TR[(TR[f"known{h}"] < FINAL_T) & TR[f"label{h}"].notna()]
        m = fit(tr[FEATS].values, tr[f"label{h}"].values.astype(int))
        pp = pd.Series(m.predict_proba(P[FEATS].values)[:, 1], index=P.index)
        P[f"R{h}_FROZEN"] = pp.values
        claims[f"R{h}_pre2020_skill"] = auc_ci(P, pp, f"label{h}")
        print(f"R{h} frozen 2018-19", {k: round(v, 4) for k, v in claims[f"R{h}_pre2020_skill"].items()}, flush=True)
    P[["symbol", "bar", "fwd6", "label6", "fwd30", "label30", "R6_FROZEN", "R30_FROZEN"]].to_csv(OUT / "pre2020_predictions_4h.csv", index=False)

    # ---------------- gates ----------------
    gates = {f"G0{k[0]}_{k[2:]}": bool(v) for k, v in g0.items()}
    gates["G0"] = all(g0.values())
    gates["G1"] = bool(g1)
    passing = []
    for h in HS:
        a, c = claims[f"R{h}_AI_skill"], claims[f"R{h}_CONTROL_skill"]
        ai = runs[f"R{h}_AI"]
        g = dict(G2_skill=a["ci_low"] > 0.50 and a["auc"] > c["auc"],
                 G3a_cagr=ai["cagr_pct"] > 0,
                 G3b_calmar=all(ai["calmar"] > runs[k]["calmar"] for k in ("ONE_D_100", f"R{h}_CONTROL", "BTC_HOLD")),
                 G3c_trade_ci=ai["trade_ci_low_pct"] > 0,
                 G3d_cost040=runs[f"R{h}_AI_cost040"]["cagr_pct"] > 0,
                 G4_pre2020=claims[f"R{h}_pre2020_skill"]["ci_low"] > 0.50)
        g = {k: bool(v) for k, v in g.items()}
        g["pass"] = all(g.values())
        g["skill_only"] = g["G2_skill"] and g["G4_pre2020"] and not g["pass"]
        gates[f"R{h}"] = g
        if g["pass"]:
            passing.append(h)
    if not gates["G0"]:
        dec = "INVALID_G0"
    elif not gates["G1"]:
        dec = "INVALID"
    elif passing:
        dec = f"PASS_R{max(passing, key=lambda h: runs[f'R{h}_AI']['calmar'])}"
    elif any(gates[f"R{h}"]["skill_only"] for h in HS):
        dec = "SKILL_ONLY"
    else:
        dec = "FAIL"
    gates["decision"] = dec
    claims["gates"] = gates
    claims["test_predictions_sha256"] = sha_file(OUT / "test_predictions_4h.csv")
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
