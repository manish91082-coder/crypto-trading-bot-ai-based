"""
Step 21: crash-risk brain (top-20 market falls > 10 % in 10 days) + Step 19's proven top-20 selection.
Protocol: logs/strategy_1d_step21_crash/STEP21_PROTOCOL_PREREGISTERED.md (SHA256 locked before training).
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core_rows_1d as CR
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
import step14_trading_rule_1d as S14
import step15_slow_relative_1d as S15
import step17_18_market_veto_1d as S17
import step19_large_caps_1d as S19
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step21_crash"
PROTO_NAME = "STEP21_PROTOCOL_PREREGISTERED.md"
U19 = LOGS_DIR / "strategy_1d_step19_largecap"
ASOF, OOS_START = S15.ASOF, S15.OOS_START
CRASH, HZ, ALARM_Q = -0.10, 10, 0.80
COST, COST_STRESS = 0.0025, 0.0040


def auc99(y, p, dates):
    p = p.reindex(y.index)
    assert p.notna().all()
    return S13.auc_ci(y.values.astype(int), p.values, dates.dt.to_period("M").astype(str).values, 0.5, 99.5)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = hashlib.sha256((OUT / PROTO_NAME).read_bytes()).hexdigest()
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_, u19_pred_sha256=hashlib.sha256((U19 / "U_AI_predictions.csv").read_bytes()).hexdigest())
    split = pd.read_csv(S15.SPLIT)
    B = set(split[split.half == "B_confirm"].symbol)
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", ASOF)
    data_n = {s: data_n[s] for s in B}
    last_n = {s: last_n[s] for s in B}
    Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, S13.UNI / "1h", S13.UNI / "1h", ASOF, S11.fng_table())
    for P, d, l in ((Pk, data_k, last_k), (Pn, data_n, last_n)):
        P["eligible"] = P.liquid & (P.idx + 1 >= S15.MIN_HIST)
        P["fwd10"], P["known10"] = S15.add_relative(P, d, l, HZ)
    data_all, last_all = {**data_k, **data_n}, {**last_k, **last_n}
    cand = pd.concat([Pk[Pk.eligible], Pn[Pn.eligible]], ignore_index=True)
    vol = S19.usd30(data_all, last_all)
    cand["usd30"] = [vol[s].get(d, np.nan) for s, d in zip(cand.symbol, cand.date)]
    cand["urank"] = cand.groupby("date").usd30.rank(ascending=False, method="first")
    U = cand[cand.urank <= S19.U_SIZE].copy()
    u19 = pd.read_csv(U19 / "universe_U.csv", parse_dates=["date"])
    assert set(zip(U[U.date >= OOS_START].symbol, U[U.date >= OOS_START].date)) == set(zip(u19.symbol, u19.date))
    print(f"U rows {len(U)} from {U.date.min().date()} (identical to Step 19 from 2021) ({time.time()-t0:.0f}s)", flush=True)

    M = S17.market_features(U)
    lab = U.dropna(subset=["fwd10"]).groupby("date").agg(mean=("fwd10", "mean"), known=("known10", "max"))
    M["crash"] = (lab["mean"] < CRASH).astype(float).reindex(M.index)
    M["known"] = lab.known.reindex(M.index)
    M["mean_fwd10"] = lab["mean"].reindex(M.index)
    M = M.reset_index().rename(columns={"index": "date"})
    Mt = M[M.date >= OOS_START]
    ok = Mt.crash.notna()
    claims["test_days"], claims["test_crash_rate"] = int(ok.sum()), float(Mt.crash[ok].mean())

    rng = np.random.default_rng(42)
    Mp = M.copy()
    Mp["planted"] = Mp.crash + rng.normal(0, 2.79, len(Mp))
    Mp["leak"] = Mp.mean_fwd10
    Dp = dict(train=Mp, test=Mp[Mp.date >= OOS_START])
    sp, _ = S17.wf(Dp, S17.MKT + ["planted"], "crash", "known", S17.KW_M)
    sl, _ = S17.wf(Dp, S17.MKT + ["leak"], "crash", "known", S17.KW_M)
    claims["sanity_planted"] = S17.auc_ci(Mt.crash[ok], sp, Mt.date[ok])
    claims["sanity_leak"] = S17.auc_ci(Mt.crash[ok], sl, Mt.date[ok])
    g1 = claims["sanity_planted"]["auc"] >= 0.55 and claims["sanity_leak"]["auc"] > 0.95
    print("G1", round(claims["sanity_planted"]["auc"], 4), round(claims["sanity_leak"]["auc"], 4), g1, flush=True)

    D = dict(train=M, test=Mt)
    gate = {}
    for labn, sh in (("AI", False), ("CONTROL", True)):
        pc, _ = S17.wf(D, S17.MKT, "crash", "known", S17.KW_M, sh, 21)
        claims[f"{labn}_skill99"] = auc99(Mt.crash[ok], pc, Mt.date[ok])
        mo = Mt[["date", "crash", "mean_fwd10"]].assign(p_crash=pc.reindex(Mt.index).values)
        mo["thr"] = S11.causal_pct_threshold(mo.date, mo.p_crash.values, ALARM_Q)
        mo["alarm"] = mo.p_crash >= mo.thr                       # NaN threshold (first month) -> no alarm
        mo.to_csv(OUT / f"crash_{labn}_predictions.csv", index=False)
        gate[labn] = {d: not bool(a) for d, a in zip(mo.date, mo.alarm)}
        claims[f"{labn}_alarm_days_pct"] = float(mo.alarm.mean() * 100)
        a = mo[mo.alarm & mo.crash.notna()]
        claims[f"{labn}_alarm_precision"] = float(a.crash.mean()) if len(a) else float("nan")
        print(labn, {k: round(v, 4) for k, v in claims[f"{labn}_skill99"].items()}, "alarm days %", round(claims[f"{labn}_alarm_days_pct"], 1),
              "precision", round(claims[f"{labn}_alarm_precision"], 3), flush=True)

    rows = pd.read_csv(U19 / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    px = {s: data_all[s].set_index("timestamp")[["open", "close"]] for s in set(rows.symbol) | {"BTCUSDT"}}
    S15.N, S15.KEEP_RANK = S19.N_HOLD, S19.KEEP
    runs = {}
    for name, g, cost in (("UNGATED", None, COST), ("ALARM", gate["AI"], COST), ("ALARM_CONTROL", gate["CONTROL"], COST),
                          ("ALARM_cost040", gate["AI"], COST_STRESS)):
        tr, eq, final, traded = S17.simulate_full(rows, g, px, last_all, cost)
        tr.to_csv(OUT / f"{name}_trades.csv", index=False)
        eq.to_csv(OUT / f"{name}_equity.csv", index=False)
        runs[name] = S14.summarize(tr, eq, final, traded, name)
        runs[name]["days_invested_pct"] = float((eq.n_held > 0).mean() * 100)
    assert abs(runs["UNGATED"]["final"] - 65274.51) < 0.01, "UNGATED does not reproduce Step 19"
    tr, eq, final, traded = S19.btc_hold(px, COST)
    runs["BTC_HOLD"] = S14.summarize(tr, eq, final, traded, "BTC_HOLD")
    for k, v in runs.items():
        print(k, {x: v.get(x) for x in ("final", "cagr_pct", "max_dd_pct", "calmar", "trades", "trade_ci_low_pct", "days_invested_pct")},
              {y: v.get(f"ret_{y}") for y in range(2021, 2027)}, flush=True)
    claims["portfolio"] = runs
    g = runs["ALARM"]
    gates = dict(G1=g1, G2_skill=claims["AI_skill99"]["ci_low"] > 0.50 and claims["AI_skill99"]["auc"] > claims["CONTROL_skill99"]["auc"],
                 G3a_cagr=g["cagr_pct"] > 0,
                 G3b_calmar=all(g["calmar"] > runs[k]["calmar"] for k in ("UNGATED", "ALARM_CONTROL", "BTC_HOLD")),
                 G3c_trade_ci=g["trade_ci_low_pct"] > 0,
                 G3d_years=sum(g.get(f"ret_{y}", 0.0) > 0 for y in range(2021, 2027)) >= 4,
                 G3e_cost040=runs["ALARM_cost040"]["cagr_pct"] > 0, G3f_maxdd=g["max_dd_pct"] < 50)
    gates = {k: bool(v) for k, v in gates.items()}
    g3 = all(v for k, v in gates.items() if k.startswith("G3"))
    gates["decision"] = ("INVALID" if not gates["G1"] else "PASS" if g3 and gates["G2_skill"] else
                         "SYSTEM_PASSES_BUT_BRAIN_UNPROVEN" if g3 else "FAIL")
    claims["gates"] = gates
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
