"""
Independent verifier for logs/strategy_1d_step14_rule/claims.json (separate implementation of the rule).
V1 hashes: protocol, coin split, Step 13 prediction files unchanged.
V2 split re-derived from the seed; causal thresholds and regime flags recomputed with separate code.
V3 all 24 rules re-simulated on half A; the chosen rule re-selected.
V4 the four B runs re-simulated; final equity, max drawdown, trade count and trade CI match.
V5 gates and decision recomputed.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics"):
    sys.path.insert(0, str(p))
import step13_unseen_coins_1d as S13
import step11_ai_confident_1d as S11
from step6_4_survivorship_1d import load_all

D = S13.OUT.parent / "strategy_1d_step14_rule"
C = json.loads((D / "claims.json").read_text())
START, END = S13.OOS_START, S13.DATA_END


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def causal(rows):
    rows = rows.dropna(subset=["score"]).copy()
    rows["m"] = rows.date.dt.to_period("M")
    months = sorted(rows.m.unique())
    thr = {0.9: {}, 0.98: {}}
    daily = rows.groupby("date").score.mean().to_frame("v")
    daily["m"] = daily.index.to_period("M")
    med = {}
    for m in months:
        earlier = rows.loc[rows.m < m, "score"].values
        for q in thr:
            thr[q][m] = np.quantile(earlier, q) if len(earlier) else np.nan
        e2 = daily.loc[daily.m < m, "v"].values
        med[m] = np.median(e2) if len(e2) else np.nan
    reg = {d: (v >= med[m]) if not np.isnan(med[m]) else False for d, v, m in zip(daily.index, daily.v, daily.m)}
    order = rows.sort_values(["date", "score", "symbol"], ascending=[True, False, True])
    rank = {d: list(zip(g.symbol, g.score)) for d, g in order.groupby("date")}
    return thr, reg, rank


def run(rows, rule, opn, cls, last, cost):
    thr, reg, rank = causal(rows)
    N, M = rule["N"], rule["N"] * rule["buffer"]
    cash, held, pend_sell, pend_buy, curve, rets, months = 10000.0, {}, [], [], [], [], []
    for d in pd.date_range(START, END, freq="D"):
        for s in list(held):
            if d > last[s]:
                u, c, ed = held.pop(s)
                v = u * cls[s][last[s]] * (1 - cost)
                cash += v
                rets.append(v / c - 1)
                months.append(ed.strftime("%Y-%m"))
        for s in pend_sell:
            if s in held:
                u, c, ed = held.pop(s)
                v = u * opn[s][d] * (1 - cost)
                cash += v
                rets.append(v / c - 1)
                months.append(ed.strftime("%Y-%m"))
        e_open = cash + sum(u * opn[s][d] for s, (u, c, ed) in held.items())
        for s in pend_buy:
            if s in held or len(held) >= N or d > last[s]:
                continue
            amt = min(0.8 * e_open / N, cash / (1 + cost))
            if amt < 10:
                continue
            cash -= amt * (1 + cost)
            held[s] = (amt / opn[s][d], amt * (1 + cost), d)
        curve.append(cash + sum(u * cls[s][d] for s, (u, c, ed) in held.items()))
        today = rank.get(d, [])
        pos_of = {s: i + 1 for i, (s, _) in enumerate(today)}
        if rule["regime"] and not reg.get(d, False):
            pend_sell, pend_buy = list(held), []
            continue
        kept = [s for s in held if pos_of.get(s, 10 ** 9) <= M]
        pend_sell = [s for s in held if s not in kept]
        t = thr[rule["q"]][d.to_period("M")]
        pend_buy = [s for s, sc in today[:N] if sc >= t and s not in held][:N - len(kept)]
    for s in list(held):
        u, c, ed = held.pop(s)
        v = u * cls[s][min(END, last[s])] * (1 - cost)
        cash += v
        rets.append(v / c - 1)
        months.append(ed.strftime("%Y-%m"))
    eq = np.r_[10000.0, curve]
    dd = float(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max())
    yrs = (END - START).days / 365.25
    cagr = (cash / 10000) ** (1 / yrs) - 1
    return dict(final=cash, dd=dd * 100, cagr=cagr * 100, calmar=cagr / dd, trades=len(rets),
                rets=np.array(rets), months=np.array(months), curve=pd.Series(curve, index=pd.date_range(START, END)))


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert sha(D / "STEP14_PROTOCOL_PREREGISTERED.md") == lock[0] == C["protocol_sha256"]
    assert sha(D / "coin_split.csv") == C["sha256_coin_split"] == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    for f in ("AI_signals_unseen.csv", "CONTROL_signals_unseen.csv"):
        assert sha(S13.OUT / f) == C[f"sha256_{f}"] and C[f"sha256_{f}"] in lock
    print("[V1 PASS] protocol, split and Step 13 prediction files unchanged")

    split = pd.read_csv(D / "coin_split.csv")
    coins = np.array(sorted(split.symbol))
    perm = np.random.default_rng(20261013).permutation(len(coins))
    a = set(coins[perm[:len(coins) // 2]])
    assert set(split[split.half == "A_design"].symbol) == a and len(a) == 265
    print("[V2 PASS] split re-derived from seed 20261013 (265 A / 266 B)")

    data_k, _ = load_all()
    data_n, last, _ = S13.load_new(set(data_k))
    opn = {s: df.set_index("timestamp").open.to_dict() for s, df in data_n.items()}
    cls = {s: df.set_index("timestamp").close.to_dict() for s, df in data_n.items()}
    sig = {lab: pd.read_csv(S13.OUT / f"{lab}_signals_unseen.csv", usecols=["symbol", "date", "p1"], parse_dates=["date"])
           .rename(columns={"p1": "score"}) for lab in ("AI", "CONTROL")}
    closes = {s: df.set_index("timestamp").close for s, df in data_n.items()}
    simple = sig["AI"][["symbol", "date"]].copy()
    simple["score"] = [closes[s].get(d) / closes[s].get(d - pd.Timedelta(days=20)) - 1
                       if (d - pd.Timedelta(days=20)) in closes[s].index else np.nan for s, d in zip(simple.symbol, simple.date)]
    A = lambda df: df[df.symbol.isin(a)]
    B = lambda df: df[~df.symbol.isin(a)]

    grid = pd.read_csv(D / "A_design_grid.csv")
    res = []
    for g in grid.itertuples():
        rule = dict(N=int(g.N), buffer=int(g.buffer), q=float(g.q), regime=bool(g.regime))
        r = run(A(sig["AI"]), rule, opn, cls, last, 0.0025)
        assert abs(r["final"] - g.final) < 0.01 and r["trades"] == g.trades, (g.run, r["final"], g.final)
        res.append((rule, r))
    okr = [(rule, r) for rule, r in res if r["trades"] >= 60 and r["cagr"] > 0]
    best = max(okr, key=lambda x: x[1]["calmar"])[0] if okr else None
    assert best == C["chosen_rule"], (best, C["chosen_rule"])
    print(f"[V3 PASS] 24 rules re-simulated on A (finals match); re-selected rule = {best}")

    out = {}
    for lab, rows, cost in (("AI", sig["AI"], 0.0025), ("CONTROL", sig["CONTROL"], 0.0025), ("SIMPLE", simple, 0.0025),
                            ("AI_cost040", sig["AI"], 0.0040)):
        r = run(B(rows), best, opn, cls, last, cost)
        c = C["B"][lab]
        assert abs(r["final"] - c["final"]) < 0.01 and abs(r["dd"] - c["max_dd_pct"]) < 0.01 and r["trades"] == c["trades"], (lab, r["final"], c["final"])
        lo, hi = S11.block_ci(r["rets"], r["months"])
        assert abs(lo * 100 - c["trade_ci_low_pct"]) < 1e-9
        ye = r["curve"].resample("YE").last()
        yr = (ye / ye.shift(1).fillna(10000.0) - 1) * 100
        r["years_pos"] = int(sum(v > 0 for v in yr.values))
        out[lab] = r
        print(f"[V4 PASS] B {lab}: final {r['final']:.2f}, MaxDD {r['dd']:.2f}%, trades {r['trades']}, "
              f"mean trade {r['rets'].mean() * 100:.3f}% (CI low {lo * 100:.3f}%), positive years {r['years_pos']}")
    ai = out["AI"]
    rec = dict(G1_cagr=ai["cagr"] > 0, G2_beats=ai["calmar"] > out["CONTROL"]["calmar"] and ai["calmar"] > out["SIMPLE"]["calmar"],
               G3_trade_ci=C["B"]["AI"]["trade_ci_low_pct"] > 0, G4_years=ai["years_pos"] >= 4, G5_cost040=out["AI_cost040"]["cagr"] > 0)
    g = C["gates"]
    assert all(bool(rec[k]) == g[k] for k in rec), {k: (rec[k], g[k]) for k in rec}
    assert g["decision"] == ("PASS_RULE_CONFIRMED" if all(rec.values()) else "FAIL_RULE_NOT_CONFIRMED")
    print(f"[V5 PASS] gates recomputed -> {g['decision']}")


if __name__ == "__main__":
    main()
