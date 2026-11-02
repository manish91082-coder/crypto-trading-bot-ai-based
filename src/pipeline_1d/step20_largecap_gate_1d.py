"""
Step 20: market ("when to stay out") brain for the LARGE-cap market + Step 19's proven top-20 selection.
Protocol: logs/strategy_1d_step20_largecap_gate/STEP20_PROTOCOL_PREREGISTERED.md (SHA256 locked before training).
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

OUT = LOGS_DIR / "strategy_1d_step20_largecap_gate"
PROTO_NAME = "STEP20_PROTOCOL_PREREGISTERED.md"
U19 = LOGS_DIR / "strategy_1d_step19_largecap"
ASOF, OOS_START = S15.ASOF, S15.OOS_START
COST, COST_STRESS = 0.0025, 0.0040


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
        P["fwd5"], P["known5"] = S15.add_relative(P, d, l, 5)
    data_all, last_all = {**data_k, **data_n}, {**last_k, **last_n}
    cand = pd.concat([Pk[Pk.eligible], Pn[Pn.eligible]], ignore_index=True)
    vol = S19.usd30(data_all, last_all)
    cand["usd30"] = [vol[s].get(d, np.nan) for s, d in zip(cand.symbol, cand.date)]
    cand["urank"] = cand.groupby("date").usd30.rank(ascending=False, method="first")
    U = cand[cand.urank <= S19.U_SIZE].copy()
    u19 = pd.read_csv(U19 / "universe_U.csv", parse_dates=["date"])
    a = set(zip(U[U.date >= OOS_START].symbol, U[U.date >= OOS_START].date))
    assert a == set(zip(u19.symbol, u19.date)), "universe differs from Step 19"
    print(f"U rows all dates {len(U)} (from {U.date.min().date()}), identical to Step 19 from 2021 ({time.time()-t0:.0f}s)", flush=True)

    M = S17.market_features(U)
    lab = U.dropna(subset=["fwd5"]).groupby("date").agg(mean=("fwd5", "mean"), known=("known5", "max"))
    M["m_label"] = (lab["mean"] > 0).astype(float).reindex(M.index)
    M["m_known"] = lab.known.reindex(M.index)
    M["m_mean_fwd5"] = lab["mean"].reindex(M.index)
    M = M.reset_index().rename(columns={"index": "date"})
    Mt = M[M.date >= OOS_START]
    ok = Mt.m_label.notna()
    claims["days_test"] = int(ok.sum())

    rng = np.random.default_rng(42)
    Mp = M.copy()
    Mp["planted"] = Mp.m_label + rng.normal(0, 2.79, len(Mp))
    Mp["leak"] = Mp.m_mean_fwd5
    Dp = dict(train=Mp, test=Mp[Mp.date >= OOS_START])
    sp, _ = S17.wf(Dp, S17.MKT + ["planted"], "m_label", "m_known", S17.KW_M)
    sl, _ = S17.wf(Dp, S17.MKT + ["leak"], "m_label", "m_known", S17.KW_M)
    claims["sanity_planted"] = S17.auc_ci(Mt.m_label[ok], sp, Mt.date[ok])
    claims["sanity_leak"] = S17.auc_ci(Mt.m_label[ok], sl, Mt.date[ok])
    g1 = claims["sanity_planted"]["auc"] >= 0.55 and claims["sanity_leak"]["auc"] > 0.95
    print("G1", round(claims["sanity_planted"]["auc"], 4), round(claims["sanity_leak"]["auc"], 4), g1, flush=True)

    D = dict(train=M, test=Mt)
    gates_in = {}
    for labn, sh in (("AI", False), ("CONTROL", True)):
        pm, bm = S17.wf(D, S17.MKT, "m_label", "m_known", S17.KW_M, sh, 20)
        claims[f"{labn}_skill"] = S17.auc_ci(Mt.m_label[ok], pm, Mt.date[ok])
        claims[f"{labn}_base"] = bm
        mo = Mt[["date", "m_label", "m_mean_fwd5"]].assign(p_mkt=pm.reindex(Mt.index).values)
        mo["base"] = mo.date.dt.strftime("%Y-%m").map(bm)
        mo.to_csv(OUT / f"market_{labn}_predictions.csv", index=False)
        gates_in[labn] = {d: bool(p >= b) for d, p, b in zip(mo.date, mo.p_mkt, mo.base)}
        print(labn, {k: round(v, 4) for k, v in claims[f"{labn}_skill"].items()}, flush=True)

    rows = pd.read_csv(U19 / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    px = {s: data_all[s].set_index("timestamp")[["open", "close"]] for s in set(rows.symbol) | {"BTCUSDT"}}
    S15.N, S15.KEEP_RANK = S19.N_HOLD, S19.KEEP
    runs = {}
    for name, gate, cost in (("UNGATED", None, COST), ("GATED", gates_in["AI"], COST),
                             ("GATED_CONTROL", gates_in["CONTROL"], COST), ("GATED_cost040", gates_in["AI"], COST_STRESS)):
        tr, eq, final, traded = S17.simulate_full(rows, gate, px, last_all, cost)
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
    g = runs["GATED"]
    gates = dict(G1=g1, G2_skill=claims["AI_skill"]["ci_low"] > 0.50 and claims["AI_skill"]["auc"] > claims["CONTROL_skill"]["auc"],
                 G3a_cagr=g["cagr_pct"] > 0,
                 G3b_calmar=all(g["calmar"] > runs[k]["calmar"] for k in ("UNGATED", "GATED_CONTROL", "BTC_HOLD")),
                 G3c_trade_ci=g["trade_ci_low_pct"] > 0,
                 G3d_years=sum(g.get(f"ret_{y}", 0.0) > 0 for y in range(2021, 2027)) >= 4,
                 G3e_cost040=runs["GATED_cost040"]["cagr_pct"] > 0, G3f_maxdd=g["max_dd_pct"] < 50)
    gates = {k: bool(v) for k, v in gates.items()}
    g3 = all(v for k, v in gates.items() if k.startswith("G3"))
    gates["decision"] = ("INVALID" if not gates["G1"] else "PASS" if g3 and gates["G2_skill"] else
                         "SYSTEM_PASSES_BUT_BRAIN_UNPROVEN" if g3 else "FAIL")
    claims["gates"] = gates
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
