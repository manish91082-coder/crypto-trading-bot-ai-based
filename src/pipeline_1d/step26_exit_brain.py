"""
Step 26: per-coin exit / "do not hold" brain (P(coin falls > 5 % in 24 h)) on top of the 1h R24 system.
Protocol: logs/strategy_1d_step26_exit/STEP26_PROTOCOL_PREREGISTERED.md (SHA256 locked before any Step 26 model is trained).
"""
import sys
import json
import time
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
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import step24_1h_brain as S24
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step26_exit"
PROTO_NAME = "STEP26_PROTOCOL_PREREGISTERED.md"
START, END, END_BAR, FINAL_T = S24.START, S24.END, S24.END_BAR, S24.FINAL_T
PRE_START, PRE_END = S24.PRE_START, S24.PRE_END
PRE_END_BAR = PRE_END + pd.Timedelta(hours=23)
TAIL, Q, N_RANDOM = -0.05, 0.80, 20
CAP, N_HOLD, KEEP, COST = 10_000.0, 5, 10, 0.0025
MKT = ["mkt_med_r24", "mkt_share_down24", "mkt_med_rv12"]
FEATS = S24.FEATS + MKT
REF_BASE = 201548.26


def add_market_and_label(R):
    g = R.groupby("bar")
    R["mkt_med_r24"] = g.r24.transform("median").astype("float32")
    R["mkt_share_down24"] = g.r24.transform(lambda x: (x < 0).sum() / x.notna().sum() if x.notna().any() else np.nan).astype("float32")
    R["mkt_med_rv12"] = g.rv12.transform("median").astype("float32")
    R["tail24"] = np.where(R.fwd24.isna(), np.nan, (R.fwd24 < TAIL).astype(float))
    return R


def sim_veto(rows, veto, start, end_bar, px, cost=COST, n=N_HOLD, keep=KEEP, h=24):
    """Step 24 R24 rule; at a decision bar, vetoed coins are neither kept nor bought, and their slots stay cash."""
    by_bar = {t: g.sort_values(["score", "symbol"], ascending=[False, True]).symbol.values
              for t, g in rows.dropna(subset=["score"]).groupby("bar")}
    grid = pd.date_range(start, end_bar, freq="h")
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
                sell(s, o[s][k], t, "exit")
        e0 = cash + sum(p["units"] * o[s][k] for s, p in pos.items())
        for s in buy_o:
            if s in pos or len(pos) >= n or t > lastb[s] or not np.isfinite(o[s][k]):
                continue
            a = min(e0 / n, cash / (1 + cost))
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
        v = veto.get(t, set())
        kept = [s for s in pos if rank.get(s, 10 ** 9) <= keep and s not in v]
        sell_o = [s for s in pos if s not in kept]
        target = [s for s in ranked[:n] if s not in v]
        buy_o = [s for s in target if s not in pos][:n - len(kept)]
    for s in list(pos):
        sell(s, c[s][len(grid) - 1], grid[-1], "end_of_test")
    tr = pd.DataFrame(trades)
    assert abs(CAP + (tr.pnl.sum() if len(tr) else 0) - cash) < 1e-6
    return dict(final=cash, eq=pd.Series(eq, index=grid), trades=tr)


def summary(res, start, end):
    E = res["eq"]
    daily = E[E.index.hour == 23]
    a = np.r_[CAP, daily.values]
    pk = np.maximum.accumulate(a)
    dd = float(((pk - a) / pk).max())
    cagr = (res["final"] / CAP) ** (365.25 / (end - start).days) - 1
    ye = daily.groupby(daily.index.year).last()
    yr = (ye / ye.shift(1).fillna(CAP) - 1) * 100
    return dict(final=round(float(res["final"]), 2), cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd * 100, 2),
                calmar=round(cagr / dd, 4), trades=int(len(res["trades"])),
                **{f"ret_{y}": round(float(v), 2) for y, v in yr.items()})


def veto_sets(R, p, decision_hour=23):
    """Causal 80th-percentile threshold over earlier months; returns {bar: set(vetoed symbols)} at decision bars."""
    thr = S11.causal_pct_threshold(R.bar, p.values, Q)
    flag = (p.values >= thr) & np.isfinite(thr)
    D = R.loc[flag & (R.bar.dt.hour == decision_hour).values, ["bar", "symbol"]]
    return {t: set(g.symbol) for t, g in D.groupby("bar")}, float(np.mean(flag))


def random_vetoes(R, ai_veto, seed, decision_hour=23):
    rng = np.random.default_rng(seed)
    out = {}
    for t, g in R[R.bar.dt.hour == decision_hour].groupby("bar"):
        k = len(ai_veto.get(t, ()))
        if k:
            out[t] = set(rng.choice(g.symbol.values, size=min(k, len(g)), replace=False))
    return out


def period(name, R, scores, p, ctl, px, start, end, end_bar, claims, base_ref=None):
    rows = R[["symbol", "bar"]].assign(score=scores)
    res = {}
    base = sim_veto(rows, {}, start, end_bar, px)
    res["BASE"] = summary(base, start, end)
    if base_ref is not None:
        claims[f"{name}_base_reproduces"] = abs(base["final"] - base_ref) < 0.01
    v_ai, share = veto_sets(R, p)
    claims[f"{name}_veto_share_all_rows"] = share
    claims[f"{name}_veto_decisions"] = int(sum(len(x) for x in v_ai.values()))
    r = sim_veto(rows, v_ai, start, end_bar, px)
    r["trades"].to_csv(OUT / f"{name}_AI_VETO_trades.csv", index=False)
    r["eq"][r["eq"].index.hour == 23].to_csv(OUT / f"{name}_AI_VETO_daily_equity.csv", header=["equity"], index_label="bar")
    res["AI_VETO"] = summary(r, start, end)
    if ctl is not None:
        v_c, _ = veto_sets(R, ctl)
        res["CONTROL_VETO"] = summary(sim_veto(rows, v_c, start, end_bar, px), start, end)
    rc = [summary(sim_veto(rows, random_vetoes(R, v_ai, 1000 + i), start, end_bar, px), start, end)["calmar"] for i in range(N_RANDOM)]
    res["RANDOM_calmars"] = rc
    res["RANDOM_calmar_p95"] = float(np.percentile(rc, 95))
    print(name, {k: v for k, v in res.items() if k != "RANDOM_calmars"}, flush=True)
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = S23.sha_file(OUT / PROTO_NAME)
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_)
    split = pd.read_csv(S15.SPLIT)
    A, B = set(split[split.half == "A_design"].symbol), set(split[split.half == "B_confirm"].symbol)
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S24.UNI1H, END)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    known = list(data_k)
    Ute = S23.daily_members(data, last, known + sorted(B & set(data)), 20, START - pd.Timedelta(days=1), END - pd.Timedelta(days=1))
    Utr = S23.daily_members(data, last, known + sorted(A & set(data)), 30, pd.Timestamp("2020-01-01"), END - pd.Timedelta(days=1))
    del data_k, data_n, data
    btc_close = S24.bars_1h(S24.UNI1H / "BTCUSDT_1h_full.csv.gz").close
    R, px, _ = S24.build_rows(dict(train=Utr, test=Ute), S24.UNI1H, btc_close, hour_filter=dict(train=lambda hr: hr % 3 == 0))
    TR, TE = add_market_and_label(R["train"]), R["test"]
    TE = add_market_and_label(TE[(TE.bar >= START) & (TE.bar <= END_BAR)].reset_index(drop=True))
    base = pd.read_csv(S24.OUT / "test_predictions_1h.csv", usecols=["symbol", "bar", "R24_AI"], parse_dates=["bar"])
    g0 = dict(rows_identical=bool(len(base) == len(TE) and (base.symbol.values == TE.symbol.values).all() and (base.bar.values == TE.bar.values).all()))
    claims["tail_base_rate_train"] = float(TR.tail24.mean())
    claims["tail_base_rate_test"] = float(TE.tail24.mean())
    print("rows", len(TR), len(TE), g0, "tail base rates", claims["tail_base_rate_train"], claims["tail_base_rate_test"], f"({time.time()-t0:.0f}s)", flush=True)

    g1m = pd.date_range(START, END, freq="MS")[::6]
    TEg = TE[TE.bar.dt.to_period("M").dt.to_timestamp().isin(g1m)]
    rng = np.random.default_rng(42)
    TRp, TEp = TR[FEATS + ["bar", "tail24", "known24", "fwd24"]].copy(), TEg[FEATS + ["bar", "tail24", "fwd24"]].copy()
    TRp["planted"] = TRp.tail24 + rng.normal(0, 2.79, len(TRp))
    TEp["planted"] = TEp.tail24 + rng.normal(0, 2.79, len(TEp))
    TRp["leak"], TEp["leak"] = -TRp.fwd24, -TEp.fwd24
    claims["sanity_planted"] = S23.auc_ci(TEp, S24.wf(TRp, TEp, FEATS + ["planted"], "tail24", "known24", months=g1m), "tail24")
    claims["sanity_leak"] = S23.auc_ci(TEp, S24.wf(TRp, TEp, FEATS + ["leak"], "tail24", "known24", months=g1m), "tail24")
    del TRp, TEp, TEg
    g1 = claims["sanity_planted"]["auc"] >= 0.55 and claims["sanity_leak"]["auc"] > 0.95
    print("G1", round(claims["sanity_planted"]["auc"], 4), round(claims["sanity_leak"]["auc"], 4), g1, f"({time.time()-t0:.0f}s)", flush=True)

    p_ai = S24.wf(TR, TE, FEATS, "tail24", "known24")
    p_ct = S24.wf(TR, TE, FEATS, "tail24", "known24", True, 26)
    claims["AI_skill99"] = S23.auc_ci(TE, p_ai, "tail24", 0.5, 99.5)
    claims["CONTROL_skill"] = S23.auc_ci(TE, p_ct, "tail24")
    print("skill", claims["AI_skill99"], claims["CONTROL_skill"]["auc"], f"({time.time()-t0:.0f}s)", flush=True)
    TE[["symbol", "bar", "fwd24", "tail24"]].assign(P_AI=p_ai.values, P_CONTROL=p_ct.values).to_csv(OUT / "test_predictions_exit.csv", index=False)
    claims["main"] = period("MAIN_2021_26", TE, base.R24_AI.values, p_ai, p_ct, px, START, END, END_BAR, claims, REF_BASE)
    g0["base_reproduces"] = bool(claims["MAIN_2021_26_base_reproduces"])

    U22 = pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date"], parse_dates=["date"])
    btc_pre = S24.bars_1h(S24.PRE1H / "BTCUSDT_1h_full.csv.gz").close
    Rp, pxp, _ = S24.build_rows(dict(pre=U22), S24.PRE1H, btc_pre)
    P = Rp["pre"]
    P = add_market_and_label(P[(P.bar >= PRE_START) & (P.bar <= PRE_END_BAR)].reset_index(drop=True))
    pb = pd.read_csv(S24.OUT / "pre2020_predictions_1h.csv", usecols=["symbol", "bar", "R24_FROZEN"], parse_dates=["bar"])
    g0["pre_rows_identical"] = bool(len(pb) == len(P) and (pb.symbol.values == P.symbol.values).all() and (pb.bar.values == P.bar.values).all())
    tr = TR[(TR.known24 < FINAL_T) & TR.tail24.notna()]
    mf = S23.fit(tr[FEATS].values, tr.tail24.values.astype(int))
    pp = pd.Series(mf.predict_proba(P[FEATS].values)[:, 1], index=P.index)
    claims["PRE_skill"] = S23.auc_ci(P, pp, "tail24")
    print("2018-19 skill", claims["PRE_skill"], flush=True)
    P[["symbol", "bar", "fwd24", "tail24"]].assign(P_AI=pp.values, R24_FROZEN=pb.R24_FROZEN.values).to_csv(OUT / "pre2020_predictions_exit.csv", index=False)
    claims["pre"] = period("PRE_2018_19", P, pb.R24_FROZEN.values, pp, None, pxp, PRE_START, PRE_END, PRE_END_BAR, claims)

    def g34(r):
        return dict(a_dd=r["AI_VETO"]["max_dd_pct"] <= r["BASE"]["max_dd_pct"] - 10,
                    b_calmar=r["AI_VETO"]["calmar"] > r["BASE"]["calmar"],
                    c_random=r["AI_VETO"]["calmar"] > r["RANDOM_calmar_p95"])
    gates = dict(G0=all(g0.values()), **{f"G0_{k}": v for k, v in g0.items()}, G1=bool(g1),
                 G2_skill=claims["AI_skill99"]["ci_low"] > 0.50 and claims["AI_skill99"]["auc"] > claims["CONTROL_skill"]["auc"])
    gates.update({f"G3{k}": v for k, v in g34(claims["main"]).items()})
    gates.update({f"G4{k}": v for k, v in g34(claims["pre"]).items()})
    gates["G4d_pre_skill"] = claims["PRE_skill"]["ci_low"] > 0.50
    gates = {k: bool(v) for k, v in gates.items()}
    ok = gates["G2_skill"] and all(v for k, v in gates.items() if k[:2] in ("G3", "G4"))
    gates["decision"] = "INVALID" if not (gates["G0"] and gates["G1"]) else "PASS" if ok else "FAIL"
    claims["gates"] = gates
    claims["test_predictions_sha256"] = S23.sha_file(OUT / "test_predictions_exit.csv")
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
