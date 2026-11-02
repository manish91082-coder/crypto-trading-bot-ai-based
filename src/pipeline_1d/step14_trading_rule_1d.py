"""
Step 14: a low-turnover trading rule for the proven 1-day brain (B1), chosen on half A of the unseen coins and tested
ONCE on half B. Protocol: logs/strategy_1d_step14_rule/STEP14_PROTOCOL_PREREGISTERED.md (SHA256 locked).
Input = frozen Step 13 predictions (no re-training). Spot, 1D, long-only.
"""
import sys
import json
import time
import hashlib
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import step10_ai_1d as S10
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
from step6_4_survivorship_1d import load_all
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step14_rule"
IN = S13.OUT
PROTO_NAME = "STEP14_PROTOCOL_PREREGISTERED.md"
OOS_START, DATA_END = S13.OOS_START, S13.DATA_END
CAPITAL, INVEST = 10_000.0, 0.80
COST, COST_STRESS = 0.0025, 0.0040
GRID = [dict(N=n, buffer=b, q=q, regime=r) for n, b, q, r in itertools.product((3, 5, 10), (1, 3), (0.90, 0.98), (False, True))]
MIN_TRADES_A = 60


def rule_name(r):
    return f"N{r['N']}_buf{r['buffer']}_q{r['q']}_reg{'ON' if r['regime'] else 'OFF'}"


# ----------------------------------------------------------------------------------------------
# Causal inputs of the rule
# ----------------------------------------------------------------------------------------------
def prepare(rows):
    """rows: symbol, date, score (one half). Returns per-day ranking + causal thresholds + regime flag."""
    rows = rows.dropna(subset=["score"]).sort_values(["date", "score", "symbol"], ascending=[True, False, True])
    month = rows.date.dt.to_period("M")
    thr = {q: {} for q in (0.90, 0.98)}
    dmean = rows.groupby("date").score.mean()
    dmon = dmean.index.to_period("M")
    reg_med = {}
    for m in sorted(month.unique()):
        past = rows.score[month < m]
        for q in thr:
            thr[q][m] = past.quantile(q) if len(past) else np.nan
        pm = dmean[dmon < m]
        reg_med[m] = pm.median() if len(pm) else np.nan
    regime_ok = {d: bool(v >= reg_med[d.to_period("M")]) for d, v in dmean.items()}   # NaN -> False
    by_day = {d: (g.symbol.values, g.score.values) for d, g in rows.groupby("date")}
    return dict(by_day=by_day, thr=thr, regime_ok=regime_ok)


def simulate(prep, rule, px, real_last, cost):
    N, M = rule["N"], rule["N"] * rule["buffer"]
    cash, pos, trades, rows, traded = CAPITAL, {}, [], [], 0.0
    sell_orders, buy_orders = [], []

    def sell(s, price, d, why):
        nonlocal cash, traded
        p = pos.pop(s)
        cash += p["units"] * price * (1 - cost)
        traded += p["units"] * price
        trades.append(dict(symbol=s, entry_date=p["entry_date"], entry=p["entry"], exit_date=d, exit=price, reason=why,
                           cost=p["cost"], pnl=p["units"] * price * (1 - cost) - p["cost"]))

    for d in pd.date_range(OOS_START, DATA_END, freq="D"):
        for s in [s for s in pos if d > real_last[s]]:                       # delisted: last real close
            sell(s, px[s].at[real_last[s], "close"], d, "data_end")
        for s in sell_orders:                                                # decided yesterday, at today's open
            if s in pos:
                sell(s, px[s].at[d, "open"], d, "rule_exit")
        eq_open = cash + sum(p["units"] * px[s].at[d, "open"] for s, p in pos.items())
        for s in buy_orders:
            if s in pos or len(pos) >= N or d > real_last[s]:
                continue
            o = px[s].at[d, "open"]
            notional = min(INVEST * eq_open / N, cash / (1 + cost))
            if notional < 10:
                continue
            cash -= notional * (1 + cost)
            traded += notional
            pos[s] = dict(units=notional / o, entry=o, cost=notional * (1 + cost), entry_date=d)
        assert cash >= -1e-6
        eq = cash + sum(p["units"] * px[s].at[d, "close"] for s, p in pos.items())
        rows.append(dict(date=d, equity=eq, n_held=len(pos)))
        # decisions at today's close, executed at tomorrow's open
        sell_orders, buy_orders = [], []
        syms, scores = prep["by_day"].get(d, (np.array([]), np.array([])))
        rank = {s: i + 1 for i, s in enumerate(syms)}
        ok = prep["regime_ok"].get(d, False) if rule["regime"] else True
        if not ok:
            sell_orders = list(pos)
            continue
        keep = [s for s in pos if rank.get(s, 10 ** 9) <= M]
        sell_orders = [s for s in pos if s not in keep]
        t = prep["thr"][rule["q"]][d.to_period("M")]
        elig = [s for s, sc in zip(syms[:N], scores[:N]) if sc >= t and s not in pos]
        buy_orders = elig[:N - len(keep)]
    for s in list(pos):
        sell(s, px[s].at[min(DATA_END, real_last[s]), "close"], DATA_END, "end_of_test")
    tr, eq = pd.DataFrame(trades), pd.DataFrame(rows)
    assert abs(CAPITAL + (tr.pnl.sum() if len(tr) else 0.0) - cash) < 1e-6, "cash conservation failed"
    return tr, eq, cash, traded


def summarize(tr, eq, final, traded, label):
    s = S10.summarize_curve(eq, final, label, traded)
    s["trades"] = int(len(tr))
    if len(tr):
        r = (tr.pnl / tr.cost).values
        lo, hi = S11.block_ci(r, pd.to_datetime(tr.entry_date).dt.to_period("M").astype(str).values)
        s.update(win_rate=round(float((r > 0).mean()) * 100, 2), avg_trade_pct=float(r.mean() * 100),
                 trade_ci_low_pct=lo * 100, trade_ci_high_pct=hi * 100,
                 avg_hold_days=float((pd.to_datetime(tr.exit_date) - pd.to_datetime(tr.entry_date)).dt.days.mean()))
    else:
        s.update(win_rate=0.0, avg_trade_pct=float("nan"), trade_ci_low_pct=float("nan"), trade_ci_high_pct=float("nan"),
                 avg_hold_days=float("nan"))
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / "PROTOCOL_SHA256.txt").read_text().split()
    h = hashlib.sha256((OUT / PROTO_NAME).read_bytes()).hexdigest()
    assert h == lock[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h)
    for f in ("AI_signals_unseen.csv", "CONTROL_signals_unseen.csv"):
        claims[f"sha256_{f}"] = hashlib.sha256((IN / f).read_bytes()).hexdigest()
    split = pd.read_csv(OUT / "coin_split.csv")
    claims["sha256_coin_split"] = hashlib.sha256((OUT / "coin_split.csv").read_bytes()).hexdigest()
    assert claims["sha256_coin_split"] == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    half = dict(zip(split.symbol, split.half))

    data_k, _ = load_all()
    data_n, last_n, _ = S13.load_new(set(data_k))
    px = {s: df.set_index("timestamp")[["open", "close"]] for s, df in data_n.items()}
    sig = {lab: pd.read_csv(IN / f"{lab}_signals_unseen.csv", usecols=["symbol", "date", "p1"], parse_dates=["date"])
           .rename(columns={"p1": "score"}) for lab in ("AI", "CONTROL")}
    assert set(sig["AI"].symbol) == set(half), "split does not match the Step 13 coin list"
    mom = {s: df.set_index("timestamp").close.pct_change(20) for s, df in data_n.items()}
    simple = sig["AI"][["symbol", "date"]].copy()
    simple["score"] = [mom[s].get(d, np.nan) for s, d in zip(simple.symbol, simple.date)]
    print(f"loaded {len(data_n)} coins, {len(sig['AI'])} scored rows ({time.time() - t0:.0f}s)", flush=True)

    def part(df, h_):
        return df[df.symbol.map(half) == h_]

    # ---------------- design half A: all 24 rules ----------------
    prepA = prepare(part(sig["AI"], "A_design"))
    grid = []
    for r in GRID:
        tr, eq, final, traded = simulate(prepA, r, px, last_n, COST)
        s = summarize(tr, eq, final, traded, rule_name(r))
        grid.append({**r, **s})
    G = pd.DataFrame(grid)
    G.to_csv(OUT / "A_design_grid.csv", index=False)
    print(G[["run", "final", "cagr_pct", "max_dd_pct", "calmar", "trades", "avg_trade_pct", "turnover_x"]].to_string(), flush=True)
    ok = G[(G.trades >= MIN_TRADES_A) & (G.cagr_pct > 0)]
    if ok.empty:
        claims["decision"] = "FAIL_NO_RULE_ON_DESIGN_HALF"
        (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
        print("DECISION:", claims["decision"])
        return
    best = ok.sort_values(["calmar", "run"], ascending=[False, True]).iloc[0]
    rule = dict(N=int(best.N), buffer=int(best.buffer), q=float(best.q), regime=bool(best.regime))
    claims["chosen_rule"] = rule
    claims["chosen_rule_name"] = rule_name(rule)
    claims["A_chosen"] = {k: float(best[k]) for k in ("final", "cagr_pct", "max_dd_pct", "calmar", "trades", "avg_trade_pct")}
    print("CHOSEN on A:", rule_name(rule), f"({time.time() - t0:.0f}s)", flush=True)

    # ---------------- confirm half B: one rule, once ----------------
    runs = {}
    for lab, rows_, cost in (("AI", sig["AI"], COST), ("CONTROL", sig["CONTROL"], COST), ("SIMPLE", simple, COST),
                             ("AI_cost040", sig["AI"], COST_STRESS)):
        prep = prepare(part(rows_, "B_confirm"))
        tr, eq, final, traded = simulate(prep, rule, px, last_n, cost)
        tr.to_csv(OUT / f"B_{lab}_trades.csv", index=False)
        eq.to_csv(OUT / f"B_{lab}_equity.csv", index=False)
        runs[lab] = summarize(tr, eq, final, traded, f"B_{lab}")
        print(lab, json.dumps(runs[lab], default=str), flush=True)
    claims["B"] = runs
    ai, ct, sm, st = runs["AI"], runs["CONTROL"], runs["SIMPLE"], runs["AI_cost040"]
    gates = dict(G1_cagr=ai["cagr_pct"] > 0, G2_beats=ai["calmar"] > ct["calmar"] and ai["calmar"] > sm["calmar"],
                 G3_trade_ci=bool(ai["trade_ci_low_pct"] > 0),
                 G4_years=sum(ai.get(f"ret_{y}", 0.0) > 0 for y in range(2021, 2027)) >= 4,
                 G5_cost040=st["cagr_pct"] > 0)
    gates = {k: bool(v) for k, v in gates.items()}
    gates["decision"] = "PASS_RULE_CONFIRMED" if all(gates.values()) else "FAIL_RULE_NOT_CONFIRMED"
    claims["gates"] = gates
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
