"""
Step 15: slower RELATIVE question (5 / 10 days vs the 30-coin median) + many-coin training, tested on unseen half B.
Protocol: logs/strategy_1d_step15_slow/STEP15_PROTOCOL_PREREGISTERED.md (SHA256 locked before any training).
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
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step15_slow"
PROTO_NAME = "STEP15_PROTOCOL_PREREGISTERED.md"
SPLIT = LOGS_DIR / "strategy_1d_step14_rule" / "coin_split.csv"
ASOF = pd.Timestamp("2026-09-30")
OOS_START = pd.Timestamp("2021-01-01")
HS = (5, 10)
N, KEEP_RANK = 10, 20
COST, COST_STRESS = 0.0025, 0.0040
MIN_HIST = 120


def add_relative(P, data, last, h):
    """fwd_h = open(d+1+h)/open(d+1) - 1 (only if that open is a real candle), known_h = date of open(d+1+h)."""
    fwd = np.full(len(P), np.nan)
    known = np.full(len(P), np.datetime64("NaT"), dtype="datetime64[ns]")
    for s, idx in P.groupby("symbol").groups.items():
        df = data[s]
        o, ts = df.open.values, df.timestamp.values
        last_ok = int(np.searchsorted(ts, np.datetime64(min(last[s], ASOF)), side="right")) - 1
        i = P.loc[idx, "idx"].values
        ok = i + 1 + h <= last_ok
        f = np.full(len(i), np.nan)
        f[ok] = o[i[ok] + 1 + h] / o[i[ok] + 1] - 1
        k = np.full(len(i), np.datetime64("NaT"), dtype="datetime64[ns]")
        k[ok] = ts[i[ok] + 1 + h]
        pos = P.index.get_indexer(idx)
        fwd[pos], known[pos] = f, k
    return fwd, known


def simulate_rebalance(rows, h, px, last, cost):
    """Fixed rule: every h days rank, target top N, keep while rank <= KEEP_RANK; orders at next open."""
    by_day = {d: g.sort_values(["score", "symbol"], ascending=[False, True]).symbol.values
              for d, g in rows.dropna(subset=["score"]).groupby("date")}
    cash, pos, trades, out, traded = S14.CAPITAL, {}, [], [], 0.0
    sell_orders, buy_orders = [], []

    def sell(s, price, d, why):
        nonlocal cash, traded
        p = pos.pop(s)
        cash += p["units"] * price * (1 - cost)
        traded += p["units"] * price
        trades.append(dict(symbol=s, entry_date=p["entry_date"], entry=p["entry"], exit_date=d, exit=price, reason=why,
                           cost=p["cost"], pnl=p["units"] * price * (1 - cost) - p["cost"]))

    for k, d in enumerate(pd.date_range(OOS_START, ASOF, freq="D")):
        for s in [s for s in pos if d > last[s]]:
            sell(s, px[s].at[last[s], "close"], d, "data_end")
        for s in sell_orders:
            if s in pos:
                sell(s, px[s].at[d, "open"], d, "rebalance_exit")
        eq_open = cash + sum(p["units"] * px[s].at[d, "open"] for s, p in pos.items())
        for s in buy_orders:
            if s in pos or len(pos) >= N or d > last[s]:
                continue
            o = px[s].at[d, "open"]
            notional = min(S14.INVEST * eq_open / N, cash / (1 + cost))
            if notional < 10:
                continue
            cash -= notional * (1 + cost)
            traded += notional
            pos[s] = dict(units=notional / o, entry=o, cost=notional * (1 + cost), entry_date=d)
        assert cash >= -1e-6
        out.append(dict(date=d, equity=cash + sum(p["units"] * px[s].at[d, "close"] for s, p in pos.items()), n_held=len(pos)))
        sell_orders, buy_orders = [], []
        if k % h != 0:
            continue
        ranked = list(by_day.get(d, []))
        rank = {s: i + 1 for i, s in enumerate(ranked)}
        keep = [s for s in pos if rank.get(s, 10 ** 9) <= KEEP_RANK]
        sell_orders = [s for s in pos if s not in keep]
        buy_orders = [s for s in ranked[:N] if s not in pos][:N - len(keep)]
    for s in list(pos):
        sell(s, px[s].at[min(ASOF, last[s]), "close"], ASOF, "end_of_test")
    tr, eq = pd.DataFrame(trades), pd.DataFrame(out)
    assert abs(S14.CAPITAL + (tr.pnl.sum() if len(tr) else 0.0) - cash) < 1e-6
    return tr, eq, cash, traded


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = hashlib.sha256((OUT / PROTO_NAME).read_bytes()).hexdigest()
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_, split_sha256=hashlib.sha256(SPLIT.read_bytes()).hexdigest())
    assert claims["split_sha256"] == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    split = pd.read_csv(SPLIT)
    half = dict(zip(split.symbol, split.half))

    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", ASOF)
    missing = set(half) - set(data_n)
    assert not missing, f"split coins missing: {sorted(missing)[:10]}"
    data_n = {s: data_n[s] for s in half}
    last_n = {s: last_n[s] for s in half}
    Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, S13.UNI / "1h", S13.UNI / "1h", ASOF, S11.fng_table())
    Pn["half"] = Pn.symbol.map(half)
    Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= MIN_HIST)
    print(f"rows known {len(Pk)}, other {len(Pn)} (eligible A {int((Pn.eligible & (Pn.half == 'A_design')).sum())}, "
          f"eligible B OOS {int((Pn.eligible & (Pn.half == 'B_confirm') & (Pn.date >= OOS_START)).sum())}) ({time.time()-t0:.0f}s)", flush=True)

    for h in HS:
        Pk[f"fwd_r{h}"], Pk[f"known_r{h}"] = add_relative(Pk, data_k, last_k, h)
        Pn[f"fwd_r{h}"], Pn[f"known_r{h}"] = add_relative(Pn, data_n, last_n, h)
        med = Pk.dropna(subset=[f"fwd_r{h}"]).groupby("date")[f"fwd_r{h}"].median()
        for P in (Pk, Pn):
            m = P.date.map(med)
            P[f"rel_r{h}"] = P[f"fwd_r{h}"] - m
            P[f"label_r{h}"] = np.where(P[f"rel_r{h}"].isna(), np.nan, (P[f"rel_r{h}"] > 0).astype(float))
    train = pd.concat([Pk, Pn[Pn.eligible & (Pn.half == "A_design")]], ignore_index=False).reset_index(drop=True)
    test = Pn[Pn.eligible & (Pn.half == "B_confirm") & (Pn.date >= OOS_START)].reset_index(drop=True)
    claims.update(rows_train=len(train), rows_test=len(test), n_features=len(F))
    allrows = pd.Series(True, index=test.index)

    # ---- G1 ----
    rng = np.random.default_rng(42)
    tr2, te2 = train.copy(), test.copy()
    tr2["planted"] = tr2.label_r5 + rng.normal(0, 2.79, len(tr2))
    te2["planted"] = te2.label_r5 + rng.normal(0, 2.79, len(te2))
    tr2["leak"], te2["leak"] = tr2.rel_r5, te2.rel_r5
    _, sp, _ = S13.wf_transfer(tr2, te2, F + ["planted"], "label_r5", "known_r5", "date", kw=S11.KW)
    _, sl, _ = S13.wf_transfer(tr2, te2, F + ["leak"], "label_r5", "known_r5", "date", kw=S11.KW)
    claims["sanity_planted"] = S13.skill(te2, sp, "label_r5", allrows)
    claims["sanity_leak"] = S13.skill(te2, sl, "label_r5", allrows)
    g1 = claims["sanity_planted"]["auc"] >= 0.55 and claims["sanity_leak"]["auc"] > 0.95
    print("G1", round(claims["sanity_planted"]["auc"], 4), round(claims["sanity_leak"]["auc"], 4), g1, f"({time.time()-t0:.0f}s)", flush=True)
    del tr2, te2
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))

    # ---- brains ----
    px = {s: df.set_index("timestamp")[["open", "close"]] for s, df in data_n.items()}
    mom = {s: df.set_index("timestamp").close.pct_change(20) for s, df in data_n.items()}
    simple = test[["symbol", "date"]].copy()
    simple["score"] = [mom[s].get(d, np.nan) for s, d in zip(simple.symbol, simple.date)]
    res = {}
    for h in HS:
        preds = {}
        for lab, sh in (("AI", False), ("CONTROL", True)):
            _, pn, lg = S13.wf_transfer(train, test, F, f"label_r{h}", f"known_r{h}", "date", sh, h, S11.KW)
            lg.to_csv(OUT / f"R{h}_{lab}_training_log.csv", index=False)
            preds[lab] = pn
            claims[f"R{h}_{lab}_skill"] = S13.skill(test, pn, f"label_r{h}", allrows, S13.BONF_LO, S13.BONF_HI)
            test[["symbol", "date", "idx", f"label_r{h}", f"fwd_r{h}", f"rel_r{h}"]].assign(score=pn).to_csv(
                OUT / f"R{h}_{lab}_test_predictions.csv", index=False)
        print(f"R{h} skill AI", {k: round(v, 4) for k, v in claims[f'R{h}_AI_skill'].items()},
              "CONTROL", round(claims[f"R{h}_CONTROL_skill"]["auc"], 4), f"({time.time()-t0:.0f}s)", flush=True)
        runs = {}
        for lab, sc, cost in (("AI", preds["AI"], COST), ("CONTROL", preds["CONTROL"], COST), ("SIMPLE", None, COST),
                              ("AI_cost040", preds["AI"], COST_STRESS)):
            rows = simple if sc is None else test[["symbol", "date"]].assign(score=sc.reindex(test.index).values)
            tr, eq, final, traded = simulate_rebalance(rows, h, px, last_n, cost)
            tr.to_csv(OUT / f"R{h}_{lab}_trades.csv", index=False)
            eq.to_csv(OUT / f"R{h}_{lab}_equity.csv", index=False)
            runs[lab] = S14.summarize(tr, eq, final, traded, f"R{h}_{lab}")
            print(f"  R{h} {lab}", {k: runs[lab][k] for k in ("final", "cagr_pct", "max_dd_pct", "calmar", "trades",
                                                            "avg_trade_pct", "trade_ci_low_pct", "turnover_x")}, flush=True)
        claims[f"R{h}_portfolio"] = runs
        a, c = claims[f"R{h}_AI_skill"], claims[f"R{h}_CONTROL_skill"]
        ai = runs["AI"]
        g = dict(G2_skill=a["ci_low"] > 0.50 and a["auc"] > c["auc"],
                 G3a_cagr=ai["cagr_pct"] > 0,
                 G3b_beats=ai["calmar"] > runs["CONTROL"]["calmar"] and ai["calmar"] > runs["SIMPLE"]["calmar"],
                 G3c_trade_ci=bool(ai["trade_ci_low_pct"] > 0),
                 G3d_years=sum(ai.get(f"ret_{y}", 0.0) > 0 for y in range(2021, 2027)) >= 4,
                 G3e_cost040=runs["AI_cost040"]["cagr_pct"] > 0)
        g = {k: bool(v) for k, v in g.items()}
        g["pass"] = all(g.values())
        res[h] = g
        claims[f"R{h}_gates"] = g
        (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    passing = [h for h in HS if res[h]["pass"]]
    if not g1:
        dec = "INVALID_PIPELINE_CHECK_FAILED"
    elif passing:
        dec = f"PASS_R{max(passing, key=lambda h: claims[f'R{h}_portfolio']['AI']['calmar'])}"
    elif any(res[h]["G2_skill"] for h in HS):
        dec = "PARTIAL_SKILL_RULE_FAILS"
    else:
        dec = "FAIL_NO_SKILL"
    claims["G1_pipeline"] = bool(g1)
    claims["decision"] = dec
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nDECISION:", dec, json.dumps({h: res[h] for h in HS}), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
