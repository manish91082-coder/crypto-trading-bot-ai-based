"""
Step 22: one-shot exam of the FROZEN Step 19 system (live forward brain r5_2026-10) + account breaker on the untouched
2018-02-01..2019-12-31 Binance data.
Protocol: logs/strategy_1d_step22_pre2020/STEP22_PROTOCOL_PREREGISTERED.md (SHA256 locked before any 2017-19 analysis).
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_study_1d as SS
import core_rows_1d as CR
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
import step15_slow_relative_1d as S15
import step19_large_caps_1d as S19
import forward_dryrun_1d as FD
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step22_pre2020"
PROTO_NAME = "STEP22_PROTOCOL_PREREGISTERED.md"
PRE = DATA_DIR / "universe_pre2020"
FROZEN = DATA_DIR / "forward" / "models" / "r5_2026-10.joblib"
FROZEN_SHA = "549187143955c2346ca4c3c12e661395eb88fbdee50c49eb4defca1ec9848847"
ASOF_TRAIN, MONTH_TRAIN = pd.Timestamp("2026-09-30"), pd.Timestamp("2026-10-01")
ASOF_PRE, START, END = pd.Timestamp("2019-12-31"), pd.Timestamp("2018-02-01"), pd.Timestamp("2019-12-31")
IS_START, IS_END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30")
CAP, N_HOLD, KEEP, U_SIZE, H = 10_000.0, 5, 10, 20, 5
COST, COST_STRESS, COOL, STOP = 0.0025, 0.0040, 30, 0.25
CONTROL_SEED = 22


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_pre(dir_1d, dir_1h, asof):
    """core_rows_1d.load_folder rules, except: a reference coin may not exist yet (2017-19), and every coin (also a
    reference coin) needs a 1h file in the same folder."""
    data_k, last_k, data_n, last_n, log = {}, {}, {}, {}, []
    for f in sorted(Path(dir_1d).glob("*_1d.csv")):
        s = f.name.split("_")[0]
        why = None
        if s not in CR.KNOWN and s in S13.NOT_CRYPTO:
            why = "not a crypto asset"
        elif not (Path(dir_1h) / f"{s}_1h_full.csv.gz").exists():
            why = "no 1h file"
        if why is None:
            df = SS.load_1d(s, f)
            df = df[df.timestamp <= asof].reset_index(drop=True)
            if s not in CR.KNOWN:
                if len(df) < S13.MIN_DAYS:
                    why = f"only {len(df)} days"
                elif df.close.pct_change().abs().median() < S13.PEG_MEDIAN_ABS_RET:
                    why = "pegged price"
            elif len(df) == 0:
                why = "known coin without data"
        if why:
            log.append(dict(symbol=s, used=False, known=s in CR.KNOWN, reason=why))
            continue
        last = df.timestamp.max()
        if s in CR.KNOWN:
            data_k[s], last_k[s] = CR.pad_to(df, last, asof), last
        else:
            data_n[s], last_n[s] = CR.pad_to(df, last, asof), last
        log.append(dict(symbol=s, used=True, known=s in CR.KNOWN, first=df.timestamp.min().date(), last=last.date()))
    data_k = {s: data_k[s] for s in CR.KNOWN if s in data_k}
    return data_k, last_k, data_n, last_n, pd.DataFrame(log)


def fit_r5_control(Pk, Pn, data_k, last_k, data_n, last_n, F, month, asof, seed):
    """FD.fit_r5 line by line, with the training labels randomly permuted."""
    S15.ASOF = pd.Timestamp(asof)
    split = pd.read_csv(S15.SPLIT)
    A = set(split[split.half == "A_design"].symbol)
    Pa = Pn[Pn.eligible & Pn.symbol.isin(A)].copy()
    Pk = Pk.copy()
    Pk["fwd_r5"], Pk["known_r5"] = S15.add_relative(Pk, data_k, last_k, 5)
    Pa["fwd_r5"], Pa["known_r5"] = S15.add_relative(Pa, {s: data_n[s] for s in A if s in data_n}, last_n, 5)
    med = Pk.dropna(subset=["fwd_r5"]).groupby("date").fwd_r5.median()
    for P in (Pk, Pa):
        rel = P.fwd_r5 - P.date.map(med)
        P["label_r5"] = np.where(rel.isna(), np.nan, (rel > 0).astype(float))
    train = pd.concat([Pk, Pa]).reset_index(drop=True)
    T = pd.Timestamp(month)
    tr = train[(train.known_r5 < T) & train.label_r5.notna()]
    assert (tr.date < T).all()
    y = np.random.default_rng(seed).permutation(tr.label_r5.values.astype(int))
    m = HistGradientBoostingClassifier(random_state=0, **S11.KW).fit(tr[F].values, y)
    return m, len(tr)


# ----------------------------------------------------------------------------------------------
# Portfolio simulator (Step 19 rule + optional account breaker / hourly check / per-coin disaster stop)
# ----------------------------------------------------------------------------------------------
class Hourly:
    def __init__(self, folder):
        self.folder, self.cache = Path(folder), {}

    def get(self, s):
        if s not in self.cache:
            h = pd.read_csv(self.folder / f"{s}_1h_full.csv.gz", usecols=["timestamp", "open", "close"], parse_dates=["timestamp"])
            h = h.sort_values("timestamp")
            self.cache[s] = (h.timestamp.values, h.open.values, h.close.values)
        return self.cache[s]

    def closes(self, s, times):
        ts, _, c = self.get(s)
        i = np.searchsorted(ts, times, side="right") - 1
        assert (i >= 0).all(), f"{s}: no hourly candle before {times[0]}"
        return c[i]

    def open_at_or_after(self, s, t):
        ts, o, c = self.get(s)
        i = int(np.searchsorted(ts, np.datetime64(t), side="left"))
        return float(o[i]) if i < len(ts) else float(c[-1])


def simulate(rows, start, end, px, last, invest, n, keep, brk=None, hourly=None, stop=None, cost=COST):
    by_day = {d: g.sort_values(["score", "symbol"], ascending=[False, True]).symbol.values
              for d, g in rows.dropna(subset=["score"]).groupby("date")}
    cash, pos, trades, out, trips = CAP, {}, [], [], []
    sell_orders, buy_orders = [], []
    peak, blk, pend = CAP, None, None

    def sell(s, price, d, why):
        nonlocal cash
        p = pos.pop(s)
        cash += p["units"] * price * (1 - cost)
        trades.append(dict(symbol=s, entry_date=p["entry_date"], entry=p["entry"], exit_date=d, exit=price, reason=why,
                           cost=p["cost"], pnl=p["units"] * price * (1 - cost) - p["cost"]))

    for k, d in enumerate(pd.date_range(start, end, freq="D")):
        for s in [s for s in pos if d > last[s]]:
            sell(s, px[s].at[last[s], "close"], d, "data_end")
        for s in sell_orders:
            if s in pos:
                sell(s, px[s].at[d, "open"], d, "breaker" if pend is not None else "rebalance_exit")
        if pend is not None and not pos:
            trips.append(dict(trigger=pend[0], fill=d, peak=pend[1], equity_after=cash, loss_pct=(1 - cash / pend[1]) * 100))
            pend = None
        eq_open = cash + sum(p["units"] * px[s].at[d, "open"] for s, p in pos.items())
        for s in buy_orders:
            if s in pos or len(pos) >= n or d > last[s]:
                continue
            o = px[s].at[d, "open"]
            notional = min(invest * eq_open / n, cash / (1 + cost))
            if notional < 10:
                continue
            cash -= notional * (1 + cost)
            pos[s] = dict(units=notional / o, entry=o, cost=notional * (1 + cost), entry_date=d)
        assert cash >= -1e-6
        if stop:
            for s in list(pos):
                lvl = pos[s]["entry"] * (1 - stop)
                if px[s].at[d, "low"] <= lvl:
                    sell(s, min(px[s].at[d, "open"], lvl), d, "disaster_stop")
        if brk and hourly is not None and blk is None and pos:
            times = (d + pd.to_timedelta(np.arange(24), unit="h")).values
            cl = {s: hourly.closes(s, times) for s in pos}
            for j in range(24):
                e = cash + sum(p["units"] * cl[s][j] for s, p in pos.items())
                peak = max(peak, e)
                if e <= peak * (1 - brk):
                    t_fill = pd.Timestamp(times[j]) + pd.Timedelta(hours=1)
                    for s in list(pos):
                        sell(s, hourly.open_at_or_after(s, t_fill), d, "breaker_hourly")
                    trips.append(dict(trigger=pd.Timestamp(times[j]), fill=t_fill, peak=peak, equity_after=cash,
                                      loss_pct=(1 - cash / peak) * 100))
                    blk = d + pd.Timedelta(days=COOL)
                    break
        eq = cash + sum(p["units"] * px[s].at[d, "close"] for s, p in pos.items())
        out.append(dict(date=d, equity=eq, n_held=len(pos), cash=cash))
        sell_orders, buy_orders = [], []
        if blk is not None and d >= blk:
            blk = None
            peak = eq
        peak = max(peak, eq)
        if brk and hourly is None and blk is None and eq <= peak * (1 - brk):
            sell_orders = list(pos)
            blk = d + pd.Timedelta(days=COOL)
            pend = (d, peak)
            continue
        if blk is not None or k % H:
            continue
        ranked = list(by_day.get(d, []))
        rank = {s: i + 1 for i, s in enumerate(ranked)}
        kept = [s for s in pos if rank.get(s, 10 ** 9) <= keep]
        sell_orders = [s for s in pos if s not in kept]
        buy_orders = [s for s in ranked[:n] if s not in pos][:n - len(kept)]
    for s in list(pos):
        sell(s, px[s].at[min(end, last[s]), "close"], end, "end_of_test")
    tr = pd.DataFrame(trades)
    assert abs(CAP + (tr.pnl.sum() if len(tr) else 0.0) - cash) < 1e-6
    return dict(final=cash, eq=pd.DataFrame(out), trades=tr, trips=pd.DataFrame(trips))


def btc_hold(px, start, end, cost):
    o = px["BTCUSDT"]
    units = CAP / (1 + cost) / o.at[start, "open"]
    dates = pd.date_range(start, end, freq="D")
    eq = pd.DataFrame(dict(date=dates, equity=[units * o.at[d, "close"] for d in dates], n_held=1, cash=0.0))
    final = units * o.at[end, "close"] * (1 - cost)
    return dict(final=final, eq=eq, trades=pd.DataFrame([dict(symbol="BTCUSDT", pnl=final - CAP)]), trips=pd.DataFrame())


def summary(res, start, end):
    eq = res["eq"].set_index("date").equity
    a = np.r_[CAP, eq.values]
    pk = np.maximum.accumulate(a)
    dd = float(((pk - a) / pk).max())
    final = float(res["final"])
    cagr = (final / CAP) ** (365.25 / (end - start).days) - 1
    ye = eq.resample("YE").last()
    yr = (ye / ye.shift(1).fillna(CAP) - 1) * 100
    s = dict(final=round(final, 2), cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd * 100, 2),
             calmar=round(cagr / dd, 3) if dd > 0 else None, trades=int(len(res["trades"])),
             days_invested_pct=round(float((res["eq"].n_held > 0).mean() * 100), 1),
             **{f"ret_{y}": round(float(v), 2) for y, v in zip(ye.index.year, yr.values)})
    T = res["trips"]
    if len(T):
        s.update(breaker_trips=int(len(T)), trip_loss_worst_pct=round(float(T.loss_pct.max()), 2),
                 trip_loss_median_pct=round(float(T.loss_pct.median()), 2),
                 trip_loss_worst_usd=round(float((T.peak - T.equity_after).max()), 2))
    else:
        s.update(breaker_trips=0)
    return s


def save(name, res):
    res["eq"].to_csv(OUT / f"{name}_equity.csv", index=False)
    res["trades"].to_csv(OUT / f"{name}_trades.csv", index=False)
    if len(res["trips"]):
        res["trips"].to_csv(OUT / f"{name}_trips.csv", index=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha_file(OUT / PROTO_NAME)
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_, frozen_model_sha256=sha_file(FROZEN))
    g0 = dict(a_model_sha=claims["frozen_model_sha256"] == FROZEN_SHA)
    frozen = joblib.load(FROZEN)

    # ---------------- 2020-26: retrain check + CONTROL brain + in-sample simulator checks ----------------
    S15.ASOF = ASOF_TRAIN
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", ASOF_TRAIN)
    Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, S13.UNI / "1h", S13.UNI / "1h", ASOF_TRAIN, S11.fng_table())
    Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= S15.MIN_HIST)
    Pk["eligible"] = Pk.liquid & (Pk.idx + 1 >= S15.MIN_HIST)
    m_re, n_re = FD.fit_r5(Pk, Pn, data_k, last_k, data_n, last_n, F, MONTH_TRAIN, ASOF_TRAIN)
    m_ct, n_ct = fit_r5_control(Pk, Pn, data_k, last_k, data_n, last_n, F, MONTH_TRAIN, ASOF_TRAIN, CONTROL_SEED)
    claims.update(train_rows=n_re, control_train_rows=n_ct)
    print(f"retrained AI + CONTROL on {n_re} rows ({time.time()-t0:.0f}s)", flush=True)
    del Pk, Pn

    data_is, last_is = {**data_k, **data_n}, {**last_k, **last_n}
    rows19 = pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    px_is = {s: data_is[s].set_index("timestamp")[["open", "low", "close"]] for s in set(rows19.symbol) | {"BTCUSDT"}}
    r80 = simulate(rows19, IS_START, IS_END, px_is, last_is, 0.80, N_HOLD, KEEP)
    r100b10 = simulate(rows19, IS_START, IS_END, px_is, last_is, 1.00, N_HOLD, KEEP, brk=0.10)
    g0["c_reproduce_step19"] = abs(r80["final"] - 65274.51) < 0.01
    g0["d_reproduce_insample_b10"] = abs(r100b10["final"] - 84118) < 1.0
    ins = dict(AI_80_none=summary(r80, IS_START, IS_END), AI_100_b10=summary(r100b10, IS_START, IS_END))
    rh = simulate(rows19, IS_START, IS_END, px_is, last_is, 1.00, N_HOLD, KEEP, brk=0.10, hourly=Hourly(S13.UNI / "1h"))
    ins["AI_100_b10_hourly"] = summary(rh, IS_START, IS_END)
    save("INSAMPLE_2021_26_AI_100_b10_hourly", rh)
    claims["insample_2021_26_not_evidence"] = ins
    print("in-sample checks", {k: (v["final"], v["max_dd_pct"], v.get("breaker_trips"), v.get("trip_loss_worst_pct")) for k, v in ins.items()},
          f"({time.time()-t0:.0f}s)", flush=True)
    del data_is, px_is, data_k, data_n

    # ---------------- 2017-19 rows (untouched data) ----------------
    dk, lk, dn, ln, sel = load_pre(PRE / "1d", PRE / "1h", ASOF_PRE)
    sel.to_csv(OUT / "coin_selection_pre2020.csv", index=False)
    claims.update(reference_coins_present=sorted(dk), coins_other=len(dn),
                  excluded=sel[~sel.used].reason.value_counts().to_dict())
    print(f"pre-2020: reference {len(dk)} {sorted(dk)}, other {len(dn)} ({time.time()-t0:.0f}s)", flush=True)
    Qk, Qn, F2 = CR.build(dk, lk, dn, ln, PRE / "1h", PRE / "1h", ASOF_PRE, S11.fng_table())
    assert F2 == F
    S15.ASOF = ASOF_PRE
    for Q, d_, l_ in ((Qk, dk, lk), (Qn, dn, ln)):
        Q["eligible"] = Q.liquid & (Q.idx + 1 >= S15.MIN_HIST)
        Q["fwd5"], Q["known5"] = S15.add_relative(Q, d_, l_, 5)
    Q = pd.concat([Qk.assign(reference=True), Qn.assign(reference=False)], ignore_index=True)
    W = Q[(Q.date >= START) & (Q.date <= END)].reset_index(drop=True)
    X = W[F].values
    p_f, p_r, p_c = (m.predict_proba(X)[:, 1] for m in (frozen, m_re, m_ct))
    claims["G0b_max_abs_diff_frozen_vs_retrain"] = float(np.max(np.abs(p_f - p_r)))
    g0["b_retrain_equals_frozen"] = claims["G0b_max_abs_diff_frozen_vs_retrain"] < 1e-9
    W["score"], W["score_control"] = p_f, p_c

    med_ref = Qk.dropna(subset=["fwd5"]).groupby("date").fwd5.median()
    n_ref = Qk.dropna(subset=["fwd5"]).groupby("date").size()
    data_pre, last_pre = {**dk, **dn}, {**lk, **ln}
    vol = S19.usd30(data_pre, last_pre)
    U = W[W.eligible].copy()
    U["usd30"] = [vol[s].get(d, np.nan) for s, d in zip(U.symbol, U.date)]
    U["urank"] = U.groupby("date").usd30.rank(ascending=False, method="first")
    U = U[U.urank <= U_SIZE].reset_index(drop=True)
    rel = U.fwd5 - U.date.map(med_ref)
    U["label_r5"] = np.where(rel.isna(), np.nan, (rel > 0).astype(float))
    umed = U.groupby("date").fwd5.transform("median")
    U["label_u"] = np.where(U.fwd5.isna(), np.nan, (U.fwd5 > umed).astype(float))
    U["n_ref"] = U.date.map(n_ref)
    U[["symbol", "date", "reference", "usd30", "urank", "fwd5", "label_r5", "label_u", "n_ref", "score", "score_control"]].to_csv(
        OUT / "U_pre2020_predictions.csv", index=False)
    usz = U.groupby("date").size().reindex(pd.date_range(START, END), fill_value=0)
    g0["e_universe_every_day"] = bool((usz >= 1).all())
    claims["U_size"] = dict(min=int(usz.min()), median=float(usz.median()), max=int(usz.max()),
                            by_month_mean={str(k): round(float(v), 1) for k, v in usz.groupby(usz.index.to_period("M")).mean().items()})
    claims["U_rows"], claims["U_distinct_coins"] = int(len(U)), int(U.symbol.nunique())
    claims["n_ref_median"] = float(U.n_ref.median())
    print("U", claims["U_size"]["min"], claims["U_size"]["median"], claims["U_size"]["max"], "rows", len(U), f"({time.time()-t0:.0f}s)", flush=True)

    for lab, col in (("AI", "score"), ("CONTROL", "score_control")):
        for ln_ in ("label_r5", "label_u"):
            m = U[ln_].notna()
            claims[f"{lab}_skill_{ln_}"] = S13.auc_ci(U[ln_][m].values.astype(int), U[col][m].values,
                                                      U.date[m].dt.to_period("M").astype(str).values)
    print("skill", {k: round(v["auc"], 4) for k, v in claims.items() if "_skill_" in k}, claims["AI_skill_label_r5"], flush=True)

    # ---------------- portfolios ----------------
    px = {s: data_pre[s].set_index("timestamp")[["open", "low", "close"]] for s in set(U.symbol) | {"BTCUSDT"}}
    hourly = Hourly(PRE / "1h")
    ai = U[["symbol", "date", "score"]]
    ct = U[["symbol", "date", "score_control"]].rename(columns={"score_control": "score"})
    ew = U[["symbol", "date"]].assign(score=1.0)
    plan = [("AI_80_none", ai, 0.80, N_HOLD, KEEP, {}),
            ("AI_100_none", ai, 1.0, N_HOLD, KEEP, {}),
            ("AI_100_b10", ai, 1.0, N_HOLD, KEEP, dict(brk=0.10)),
            ("AI_100_b08", ai, 1.0, N_HOLD, KEEP, dict(brk=0.08)),
            ("AI_100_b12", ai, 1.0, N_HOLD, KEEP, dict(brk=0.12)),
            ("AI_100_b15", ai, 1.0, N_HOLD, KEEP, dict(brk=0.15)),
            ("AI_100_b20", ai, 1.0, N_HOLD, KEEP, dict(brk=0.20)),
            ("AI_100_b10_hourly", ai, 1.0, N_HOLD, KEEP, dict(brk=0.10, hourly=hourly)),
            ("AI_100_b10_stop25", ai, 1.0, N_HOLD, KEEP, dict(brk=0.10, stop=STOP)),
            ("AI_100_b10_cost040", ai, 1.0, N_HOLD, KEEP, dict(brk=0.10, cost=COST_STRESS)),
            ("CONTROL_100_none", ct, 1.0, N_HOLD, KEEP, {}),
            ("CONTROL_100_b10", ct, 1.0, N_HOLD, KEEP, dict(brk=0.10)),
            ("EW_U_100_none", ew, 1.0, U_SIZE, U_SIZE, {}),
            ("EW_U_100_b10", ew, 1.0, U_SIZE, U_SIZE, dict(brk=0.10))]
    runs = {}
    for name, rows, inv, n, keep, kw in plan:
        r = simulate(rows, START, END, px, last_pre, inv, n, keep, **kw)
        save(name, r)
        runs[name] = summary(r, START, END)
        print(name, runs[name], flush=True)
    r = btc_hold(px, START, END, COST)
    save("BTC_HOLD", r)
    runs["BTC_HOLD"] = summary(r, START, END)
    print("BTC_HOLD", runs["BTC_HOLD"], flush=True)
    claims["portfolio"] = runs

    p, btc = runs["AI_100_b10"], runs["BTC_HOLD"]["final"]
    gates = {f"G0{k[0]}_{k[2:]}": bool(v) for k, v in g0.items()}
    gates["G0"] = all(g0.values())
    gates["G1_skill"] = bool(claims["AI_skill_label_r5"]["ci_low"] > 0.50 and
                             claims["AI_skill_label_r5"]["auc"] > claims["CONTROL_skill_label_r5"]["auc"])
    g2 = dict(G2a_maxdd=p["max_dd_pct"] < 50, G2b_beats_btc=p["final"] > btc,
              G2c_beats_control_ew=p["final"] > runs["CONTROL_100_b10"]["final"] and p["final"] > runs["EW_U_100_b10"]["final"],
              G2d_breaker_cuts_dd=p["max_dd_pct"] < runs["AI_100_none"]["max_dd_pct"],
              G2e_cost040=runs["AI_100_b10_cost040"]["final"] > btc,
              G2f_neighbours=all(runs[k]["max_dd_pct"] < 50 and runs[k]["final"] > btc for k in ("AI_100_b08", "AI_100_b12")))
    gates.update({k: bool(v) for k, v in g2.items()})
    g2all = all(g2.values())
    gates["decision"] = ("INVALID" if not gates["G0"] else "PASS" if gates["G1_skill"] and g2all else
                         "SYSTEM_PASSES_SKILL_UNPROVEN" if g2all else "SKILL_HOLDS_PACKAGE_FAILS" if gates["G1_skill"] else "FAIL")
    claims["gates"] = gates
    claims["u_predictions_sha256"] = sha_file(OUT / "U_pre2020_predictions.csv")
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
