"""
Step 24: 1h relative brain (Step 23 design on 1-hour candles; horizons 4 h and 24 h).
Protocol: logs/strategy_1d_step24_1h/STEP24_PROTOCOL_PREREGISTERED.md (SHA256 locked before any 1h model is trained).
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

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
import step23_4h_brain as S23
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step24_1h"
PROTO_NAME = "STEP24_PROTOCOL_PREREGISTERED.md"
UNI1H, PRE1H = S23.UNI1H, S23.PRE1H
START, END = S23.START, S23.END
END_BAR = END + pd.Timedelta(hours=23)
FINAL_T, PRE_START, PRE_END = S23.FINAL_T, S23.PRE_START, S23.PRE_END
HS = (4, 24)
CAP, N_HOLD, KEEP, U_SIZE, T_SIZE = 10_000.0, 5, 10, 20, 30
COST, COST_STRESS, CONTROL_SEED = 0.0025, 0.0040, 24
BONF_LO, BONF_HI = 0.625, 99.375
BASE = ["r1", "r4", "r12", "r24", "r72", "r168", "dist_hi24", "dist_lo24", "dist_hi168", "atr_pct", "range_atr", "body_atr",
        "upwick_atr", "lowick_atr", "vol_ratio24", "trades_ratio24", "taker_buy_ratio", "taker_ratio_12", "taker_ratio_chg",
        "rv12", "bar_hour", "btc_r1", "btc_r12", "btc_r72"]
XR = ["r1", "r12", "r72", "vol_ratio24", "taker_buy_ratio", "dist_hi24", "atr_pct"]
FEATS = BASE + [f"xr_{c}" for c in XR]
assert len(FEATS) == 31
REF = dict(R6_4H=(98734.89, 0.625), ONE_D_100=(74452.43, 0.515), BTC_HOLD=(28767.66, 0.264))


def bars_1h(path):
    h = pd.read_csv(path, parse_dates=["timestamp"])
    assert h.timestamp.dtype.kind == "M", f"{path}: timestamps not parsed"
    h = h.sort_values("timestamp")
    h["bar"] = h.timestamp.dt.floor("h")
    g = h.groupby("bar")
    b = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last(),
                          volume=g.volume.sum(), trades=g.trades.sum(), tb=g.taker_buy_base.sum(), nh=g.size()))
    return b.reindex(pd.date_range(b.index.min(), b.index.max(), freq="h"))


def features(b, btc_close):
    o, hi, lo, c, v = b.open, b.high, b.low, b.close, b.volume
    f = pd.DataFrame(index=b.index)
    for n in (1, 4, 12, 24, 72, 168):
        f[f"r{n}"] = c.pct_change(n, fill_method=None)
    pc = c.shift(1)
    tr = pd.concat([hi - lo, (hi - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1, skipna=False)
    atr = tr.rolling(14, min_periods=10).mean()
    f["dist_hi24"] = (c - hi.rolling(24, min_periods=16).max()) / atr
    f["dist_lo24"] = (c - lo.rolling(24, min_periods=16).min()) / atr
    f["dist_hi168"] = (c - hi.rolling(168, min_periods=112).max()) / atr
    f["atr_pct"] = atr / c
    f["range_atr"] = (hi - lo) / atr
    f["body_atr"] = (c - o) / atr
    f["upwick_atr"] = (hi - np.maximum(o, c)) / atr
    f["lowick_atr"] = (np.minimum(o, c) - lo) / atr
    f["vol_ratio24"] = v / v.rolling(24, min_periods=16).mean()
    f["trades_ratio24"] = b.trades / b.trades.rolling(24, min_periods=16).mean()
    f["taker_buy_ratio"] = b.tb / v
    f["taker_ratio_12"] = f.taker_buy_ratio.rolling(12, min_periods=8).mean()
    f["taker_ratio_chg"] = f.taker_buy_ratio - f.taker_ratio_12
    f["rv12"] = f.r1.rolling(12, min_periods=8).std()
    f["bar_hour"] = b.index.hour
    for n in (1, 12, 72):
        f[f"btc_r{n}"] = btc_close.pct_change(n, fill_method=None).reindex(b.index).values
    return f.replace([np.inf, -np.inf], np.nan)


def build_rows(members_by_univ, folder, btc_close, raw1d=None, hour_filter=None):
    """Rows = the 24 hours of day d+1 for every (coin, d) member. hour_filter: {univ: callable(hours)->mask}."""
    out = {k: [] for k in members_by_univ}
    px, xc = {}, [0, 0]
    coins = sorted(set().union(*[set(m.symbol) for m in members_by_univ.values()]))
    for s in coins:
        b = bars_1h(folder / f"{s}_1h_full.csv.gz")
        f = features(b, btc_close)
        for h in HS:
            f[f"fwd{h}"], f[f"known{h}"] = S23.forward(b, h)
        f["open"], f["close"] = b.open, b.close
        if raw1d is not None:
            n, bad = S23.crosscheck(b, raw1d[s])
            xc[0] += n
            xc[1] += bad
        px[s] = b[["open", "close"]].astype("float64")
        for k, m in members_by_univ.items():
            ds = m.loc[m.symbol == s, "date"].values
            if not len(ds):
                continue
            hrs = np.arange(24)
            if hour_filter and k in hour_filter:
                hrs = hrs[hour_filter[k](hrs)]
            times = (ds[:, None] + np.timedelta64(1, "D") + hrs * np.timedelta64(1, "h")).ravel()
            sub = f.reindex(times)
            sub = sub[sub.open.notna()].copy()
            sub["symbol"], sub["bar"] = s, sub.index
            out[k].append(sub.reset_index(drop=True).astype({c: "float32" for c in BASE}))
    res = {}
    for k, parts in out.items():
        R = pd.concat(parts, ignore_index=True)
        for c in XR:
            R[f"xr_{c}"] = R.groupby("bar")[c].rank(pct=True).astype("float32")
        for h in HS:
            med = R.groupby("bar")[f"fwd{h}"].transform("median")
            R[f"rel{h}"] = R[f"fwd{h}"] - med
            R[f"label{h}"] = np.where(R[f"rel{h}"].isna(), np.nan, (R[f"rel{h}"] > 0).astype(float))
        res[k] = R
    return res, px, xc


def wf(TR, TE, feats, label, known, shuffle=False, seed=0, months=None):
    rng = np.random.default_rng(seed)
    preds = []
    for T in (months if months is not None else pd.date_range(START, END, freq="MS")):
        nxt = T + pd.offsets.MonthBegin(1)
        tr = TR[(TR[known] < T) & TR[label].notna()]
        assert (tr.bar < T).all()
        y = tr[label].values.astype(int)
        if shuffle:
            y = rng.permutation(y)
        te = TE[(TE.bar >= T) & (TE.bar < nxt)]
        m = S23.fit(tr[feats].values, y)
        preds.append(pd.Series(m.predict_proba(te[feats].values)[:, 1], index=te.index))
    return pd.concat(preds).reindex(TE.index)


def sim1h(rows, h, px, cost, invest=1.0, n=N_HOLD, keep=KEEP):
    by_bar = {t: g.sort_values(["score", "symbol"], ascending=[False, True]).symbol.values
              for t, g in rows.dropna(subset=["score"]).groupby("bar")}
    grid = pd.date_range(START, END_BAR, freq="h")
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
    return dict(final=cash, eq=pd.Series(eq, index=grid), trades=tr)


def summarize1h(res):
    E = res["eq"]
    daily = E[E.index.hour == 23]
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
    h_ = S23.sha_file(OUT / PROTO_NAME)
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_)
    c23 = json.loads((S23.OUT / "claims.json").read_text())
    for k, key in (("R6_4H", "R6_AI"), ("ONE_D_100", "ONE_D_100"), ("BTC_HOLD", "BTC_HOLD")):
        assert abs(c23["portfolio"][key]["final"] - REF[k][0]) < 0.01 and abs(c23["portfolio"][key]["calmar"] - REF[k][1]) < 1e-9
    split = pd.read_csv(S15.SPLIT)
    assert S23.sha_file(S15.SPLIT) == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    A, B = set(split[split.half == "A_design"].symbol), set(split[split.half == "B_confirm"].symbol)

    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", UNI1H, END)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    known = list(data_k)
    Ute = S23.daily_members(data, last, known + sorted(B & set(data)), U_SIZE, START - pd.Timedelta(days=1), END - pd.Timedelta(days=1))
    Utr = S23.daily_members(data, last, known + sorted(A & set(data)), T_SIZE, pd.Timestamp("2020-01-01"), END - pd.Timedelta(days=1))
    u19 = pd.read_csv(S19.OUT / "universe_U.csv", parse_dates=["date"])
    u19 = u19[u19.date <= END - pd.Timedelta(days=1)]
    mine = Ute[Ute.date >= START]
    g0 = dict(a_universe_equals_step19=set(zip(mine.symbol, mine.date)) == set(zip(u19.symbol, u19.date)))
    raw1d = {s: pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"]) for s in set(Ute.symbol) | set(Utr.symbol)}
    del data_k, data_n, data
    print("universes", g0, f"({time.time()-t0:.0f}s)", flush=True)

    btc_close = bars_1h(UNI1H / "BTCUSDT_1h_full.csv.gz").close
    R, px, xc = build_rows(dict(train=Utr, test=Ute), UNI1H, btc_close, raw1d, hour_filter=dict(train=lambda hr: hr % 3 == 0))
    TR, TE = R["train"], R["test"]
    TE = TE[(TE.bar >= START) & (TE.bar <= END_BAR)].reset_index(drop=True)
    claims["crosscheck_1h_vs_1d"] = dict(coin_days=xc[0], mismatched=xc[1], share=xc[1] / max(xc[0], 1))
    g0["b_crosscheck_lt_1pct"] = claims["crosscheck_1h_vs_1d"]["share"] < 0.01
    claims.update(train_rows=len(TR), test_rows=len(TE))
    print("rows", len(TR), len(TE), claims["crosscheck_1h_vs_1d"], f"({time.time()-t0:.0f}s)", flush=True)
    del raw1d

    # G1 on 12 months (every 6th month)
    g1m = pd.date_range(START, END, freq="MS")[::6]
    TEg = TE[TE.bar.dt.to_period("M").dt.to_timestamp().isin(g1m)]
    rng = np.random.default_rng(42)
    TRp, TEp = TR[FEATS + ["bar", "label24", "known24", "rel24"]].copy(), TEg[FEATS + ["bar", "label24", "rel24"]].copy()
    TRp["planted"] = TRp.label24 + rng.normal(0, 2.79, len(TRp))
    TEp["planted"] = TEp.label24 + rng.normal(0, 2.79, len(TEp))
    TRp["leak"], TEp["leak"] = TRp.rel24, TEp.rel24
    claims["sanity_planted"] = S23.auc_ci(TEp, wf(TRp, TEp, FEATS + ["planted"], "label24", "known24", months=g1m), "label24")
    claims["sanity_leak"] = S23.auc_ci(TEp, wf(TRp, TEp, FEATS + ["leak"], "label24", "known24", months=g1m), "label24")
    del TRp, TEp, TEg
    g1 = claims["sanity_planted"]["auc"] >= 0.55 and claims["sanity_leak"]["auc"] > 0.95
    print("G1", round(claims["sanity_planted"]["auc"], 4), round(claims["sanity_leak"]["auc"], 4), g1, f"({time.time()-t0:.0f}s)", flush=True)

    runs = {}
    out = TE[["symbol", "bar", "fwd4", "label4", "fwd24", "label24"]].copy()
    for h in HS:
        for lab, sh in (("AI", False), ("CONTROL", True)):
            p = wf(TR, TE, FEATS, f"label{h}", f"known{h}", sh, CONTROL_SEED)
            out[f"R{h}_{lab}"] = p.values
            claims[f"R{h}_{lab}_skill"] = S23.auc_ci(TE, p, f"label{h}", BONF_LO, BONF_HI)
            print(f"R{h} {lab}", {k: round(v, 4) for k, v in claims[f"R{h}_{lab}_skill"].items()}, f"({time.time()-t0:.0f}s)", flush=True)
            for name, cost in ((f"R{h}_{lab}", COST),) + (((f"R{h}_AI_cost040", COST_STRESS),) if lab == "AI" else ()):
                res = sim1h(TE[["symbol", "bar"]].assign(score=p.values), h, px, cost)
                res["trades"].to_csv(OUT / f"{name}_trades.csv", index=False)
                res["eq"][res["eq"].index.hour == 23].to_csv(OUT / f"{name}_daily_equity.csv", header=["equity"], index_label="bar")
                runs[name] = summarize1h(res)
                print(" ", name, runs[name], flush=True)
    out.to_csv(OUT / "test_predictions_1h.csv", index=False)
    claims["portfolio"] = runs

    U22 = pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date"], parse_dates=["date"])
    btc_pre = bars_1h(PRE1H / "BTCUSDT_1h_full.csv.gz").close
    Rp, _, _ = build_rows(dict(pre=U22), PRE1H, btc_pre)
    P = Rp["pre"]
    P = P[(P.bar >= PRE_START) & (P.bar <= PRE_END + pd.Timedelta(hours=23))].reset_index(drop=True)
    claims["pre2020_rows"] = len(P)
    for h in HS:
        tr = TR[(TR[f"known{h}"] < FINAL_T) & TR[f"label{h}"].notna()]
        m = S23.fit(tr[FEATS].values, tr[f"label{h}"].values.astype(int))
        pp = pd.Series(m.predict_proba(P[FEATS].values)[:, 1], index=P.index)
        P[f"R{h}_FROZEN"] = pp.values
        claims[f"R{h}_pre2020_skill"] = S23.auc_ci(P, pp, f"label{h}")
        print(f"R{h} frozen 2018-19", {k: round(v, 4) for k, v in claims[f"R{h}_pre2020_skill"].items()}, flush=True)
    P[["symbol", "bar", "fwd4", "label4", "fwd24", "label24", "R4_FROZEN", "R24_FROZEN"]].to_csv(OUT / "pre2020_predictions_1h.csv", index=False)

    gates = {f"G0{k[0]}_{k[2:]}": bool(v) for k, v in g0.items()}
    gates["G0"] = all(g0.values())
    gates["G1"] = bool(g1)
    passing = []
    for h in HS:
        a, c = claims[f"R{h}_AI_skill"], claims[f"R{h}_CONTROL_skill"]
        ai = runs[f"R{h}_AI"]
        g = dict(G2_skill=a["ci_low"] > 0.50 and a["auc"] > c["auc"],
                 G3a_cagr=ai["cagr_pct"] > 0,
                 G3b_calmar=ai["calmar"] > max(REF["R6_4H"][1], REF["ONE_D_100"][1], REF["BTC_HOLD"][1], runs[f"R{h}_CONTROL"]["calmar"]),
                 G3c_trade_ci=ai["trade_ci_low_pct"] > 0,
                 G3d_cost040=runs[f"R{h}_AI_cost040"]["cagr_pct"] > 0,
                 G4_pre2020=claims[f"R{h}_pre2020_skill"]["ci_low"] > 0.50)
        g = {k: bool(v) for k, v in g.items()}
        g["pass"] = all(g.values())
        g["skill_only"] = g["G2_skill"] and g["G4_pre2020"] and not g["pass"]
        gates[f"R{h}"] = g
        if g["pass"]:
            passing.append(h)
    dec = ("INVALID_G0" if not gates["G0"] else "INVALID" if not gates["G1"] else
           f"PASS_R{max(passing, key=lambda h: runs[f'R{h}_AI']['calmar'])}" if passing else
           "SKILL_ONLY" if any(gates[f"R{h}"]["skill_only"] for h in HS) else "FAIL")
    gates["decision"] = dec
    claims["gates"] = gates
    claims["test_predictions_sha256"] = S23.sha_file(OUT / "test_predictions_1h.csv")
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
