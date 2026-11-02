"""
Step 19: R5 selection inside the point-in-time top-20 most liquid coins (reference 30 + unseen half B).
Protocol: logs/strategy_1d_step19_largecap/STEP19_PROTOCOL_PREREGISTERED.md (SHA256 locked before any output).
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
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step19_largecap"
PROTO_NAME = "STEP19_PROTOCOL_PREREGISTERED.md"
ASOF, OOS_START = S15.ASOF, S15.OOS_START
U_SIZE, N_HOLD, KEEP = 20, 5, 10
COST, COST_STRESS = 0.0025, 0.0040


def usd30(data, last):
    out = {}
    for s, df in data.items():
        v = (df.volume * df.close).where(df.timestamp <= last[s])
        out[s] = pd.Series(v.rolling(30, min_periods=30).mean().values, index=df.timestamp)
    return out


def run_rule(rows, n, keep, px, last, cost):
    S15.N, S15.KEEP_RANK = n, keep
    return S15.simulate_rebalance(rows, 5, px, last, cost)


def btc_hold(px, cost):
    o = px["BTCUSDT"]
    d0 = OOS_START
    notional = S14.INVEST * S14.CAPITAL
    units = notional / o.at[d0, "open"]
    cash = S14.CAPITAL - notional * (1 + cost)
    dates = pd.date_range(OOS_START, ASOF, freq="D")
    eq = pd.DataFrame(dict(date=dates, equity=[cash + units * o.at[d, "close"] for d in dates], n_held=1))
    final = cash + units * o.at[ASOF, "close"] * (1 - cost)
    tr = pd.DataFrame([dict(symbol="BTCUSDT", entry_date=d0, entry=o.at[d0, "open"], exit_date=ASOF, exit=o.at[ASOF, "close"],
                            reason="hold", cost=notional * (1 + cost), pnl=final - S14.CAPITAL)])
    return tr, eq, final, notional * 2


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = hashlib.sha256((OUT / PROTO_NAME).read_bytes()).hexdigest()
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_)
    split = pd.read_csv(S15.SPLIT)
    assert hashlib.sha256(S15.SPLIT.read_bytes()).hexdigest() == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    half = dict(zip(split.symbol, split.half))
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", ASOF)
    data_n = {s: data_n[s] for s in half}
    last_n = {s: last_n[s] for s in half}
    Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, S13.UNI / "1h", S13.UNI / "1h", ASOF, S11.fng_table())
    Pn["half"] = Pn.symbol.map(half)
    Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= S15.MIN_HIST)
    Pk["eligible"] = Pk.liquid & (Pk.idx + 1 >= S15.MIN_HIST)
    # Step 15 label construction, exactly (h = 5)
    Pk["fwd_r5"], Pk["known_r5"] = S15.add_relative(Pk, data_k, last_k, 5)
    Pn["fwd_r5"], Pn["known_r5"] = S15.add_relative(Pn, data_n, last_n, 5)
    med = Pk.dropna(subset=["fwd_r5"]).groupby("date")["fwd_r5"].median()
    for P in (Pk, Pn):
        rel = P["fwd_r5"] - P.date.map(med)
        P["label_r5"] = np.where(rel.isna(), np.nan, (rel > 0).astype(float))
    train = pd.concat([Pk, Pn[Pn.eligible & (Pn.half == "A_design")]], ignore_index=False).reset_index(drop=True)
    test = Pn[Pn.eligible & (Pn.half == "B_confirm") & (Pn.date >= OOS_START)].reset_index(drop=True)
    nk = len(Pk)                                   # the first nk rows of `train` are the reference-coin rows (Pk order)
    print(f"train {len(train)} (reference rows {nk}), B test {len(test)} ({time.time()-t0:.0f}s)", flush=True)

    preds = {}
    for lab, sh in (("AI", False), ("CONTROL", True)):
        pk, pn, _ = S13.wf_transfer(train, test, F, "label_r5", "known_r5", "date", sh, 5, S11.KW)
        if lab == "AI":
            ref = pd.read_csv(LOGS_DIR / "strategy_1d_step15_slow" / "R5_AI_test_predictions.csv")
            got = pn.reindex(test.index).values
            assert len(ref) == len(test) and (ref.symbol.values == test.symbol.values).all()
            claims["G0_max_diff_vs_step15"] = float(np.nanmax(np.abs(ref.score.values - got)))
            print("G0 max diff vs Step 15 B predictions:", claims["G0_max_diff_vs_step15"], flush=True)
        known_pred = pk[pk.index < nk]
        rows_k = train.loc[known_pred.index, ["symbol", "date", "idx", "eligible", "label_r5"]].assign(score=known_pred.values)
        rows_b = test[["symbol", "date", "idx", "eligible", "label_r5"]].assign(score=pn.reindex(test.index).values)
        preds[lab] = pd.concat([rows_k, rows_b], ignore_index=True)
    g0 = claims["G0_max_diff_vs_step15"] < 1e-12

    # ---------------- universe ----------------
    data_all, last_all = {**data_k, **data_n}, {**last_k, **last_n}
    vol = usd30({s: data_all[s] for s in set(preds["AI"].symbol)}, last_all)
    U = preds["AI"][preds["AI"].eligible & (preds["AI"].date >= OOS_START)][["symbol", "date"]].copy()
    U["usd30"] = [vol[s].get(d, np.nan) for s, d in zip(U.symbol, U.date)]
    U["urank"] = U.groupby("date").usd30.rank(ascending=False, method="first")
    U = U[U.urank <= U_SIZE]
    U.to_csv(OUT / "universe_U.csv", index=False)
    claims["universe_rows"] = len(U)
    claims["universe_reference_share"] = float(U.symbol.isin(data_k).mean())
    print(f"U rows {len(U)}; share of reference coins {claims['universe_reference_share']:.3f} ({time.time()-t0:.0f}s)", flush=True)

    rowsU = {lab: U.merge(p[["symbol", "date", "score", "label_r5"]], on=["symbol", "date"], how="left") for lab, p in preds.items()}
    for lab, r in rowsU.items():
        assert r.score.notna().all()
        r.to_csv(OUT / f"U_{lab}_predictions.csv", index=False)
        m = r.label_r5.notna()
        claims[f"{lab}_skill_U"] = S13.auc_ci(r.label_r5[m].values.astype(int), r.score[m].values,
                                               r.date[m].dt.to_period("M").astype(str).values)
    print("skill U", {lab: round(claims[f"{lab}_skill_U"]["auc"], 4) for lab in preds}, claims["AI_skill_U"], flush=True)

    # ---------------- trading ----------------
    px = {s: data_all[s].set_index("timestamp")[["open", "close"]] for s in set(U.symbol) | {"BTCUSDT"}}
    mom = {s: data_all[s].set_index("timestamp").close.pct_change(20) for s in set(U.symbol)}
    simple = U[["symbol", "date"]].copy()
    simple["score"] = [mom[s].get(d, np.nan) for s, d in zip(simple.symbol, simple.date)]
    ew = U[["symbol", "date"]].assign(score=1.0)
    runs = {}
    for name, rows, n, keep, cost in (("AI", rowsU["AI"][["symbol", "date", "score"]], N_HOLD, KEEP, COST),
                                      ("CONTROL", rowsU["CONTROL"][["symbol", "date", "score"]], N_HOLD, KEEP, COST),
                                      ("SIMPLE", simple, N_HOLD, KEEP, COST), ("EW_U", ew, U_SIZE, U_SIZE, COST),
                                      ("AI_cost040", rowsU["AI"][["symbol", "date", "score"]], N_HOLD, KEEP, COST_STRESS)):
        tr, eq, final, traded = run_rule(rows, n, keep, px, last_all, cost)
        tr.to_csv(OUT / f"{name}_trades.csv", index=False)
        eq.to_csv(OUT / f"{name}_equity.csv", index=False)
        runs[name] = S14.summarize(tr, eq, final, traded, name)
    tr, eq, final, traded = btc_hold(px, COST)
    eq.to_csv(OUT / "BTC_HOLD_equity.csv", index=False)
    runs["BTC_HOLD"] = S14.summarize(tr, eq, final, traded, "BTC_HOLD")
    for k, v in runs.items():
        print(k, {x: v.get(x) for x in ("final", "cagr_pct", "max_dd_pct", "calmar", "trades", "avg_trade_pct", "trade_ci_low_pct")}, flush=True)
    claims["portfolio"] = runs
    ai = runs["AI"]
    gates = dict(G0=g0,
                 G1_skill=claims["AI_skill_U"]["ci_low"] > 0.50 and claims["AI_skill_U"]["auc"] > claims["CONTROL_skill_U"]["auc"],
                 G2a_cagr=ai["cagr_pct"] > 0,
                 G2b_calmar=all(ai["calmar"] > runs[k]["calmar"] for k in ("EW_U", "BTC_HOLD", "CONTROL", "SIMPLE")),
                 G2c_trade_ci=ai["trade_ci_low_pct"] > 0,
                 G2d_years=sum(ai.get(f"ret_{y}", 0.0) > 0 for y in range(2021, 2027)) >= 4,
                 G2e_cost040=runs["AI_cost040"]["cagr_pct"] > 0,
                 G2f_maxdd=ai["max_dd_pct"] < 50)
    gates = {k: bool(v) for k, v in gates.items()}
    g2 = all(v for k, v in gates.items() if k.startswith("G2"))
    gates["decision"] = ("INVALID" if not gates["G0"] else "PASS" if gates["G1_skill"] and g2 else
                         "PARTIAL_SKILL_RULE_FAILS" if gates["G1_skill"] else "FAIL")
    claims["gates"] = gates
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
