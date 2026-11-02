"""
Independent verifier for logs/strategy_1d_step26_exit/claims.json.
V1 protocol hash as locked; predictions SHA as claimed.
V2 300 random rows per period: tail24 label re-derived from RAW 1h opens.
V3 AUCs recomputed (Mann-Whitney): AI and CONTROL 2021-26, AI 2018-19.
V4 BASE and AI_VETO re-simulated for both periods with separate code (thresholds re-derived independently).
V5 gates recomputed (random-exit percentiles taken from claims).
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC))
from config import DATA_DIR, LOGS_DIR

D = LOGS_DIR / "strategy_1d_step26_exit"
C = json.loads((D / "claims.json").read_text())
FOLD = {"MAIN": DATA_DIR / "universe_all" / "1h", "PRE": DATA_DIR / "universe_pre2020" / "1h"}
SPAN = {"MAIN": (pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30 23:00"), pd.Timestamp("2026-09-30")),
        "PRE": (pd.Timestamp("2018-02-01"), pd.Timestamp("2019-12-31 23:00"), pd.Timestamp("2019-12-31"))}


def auc(y, p):
    r = rankdata(p)
    n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def bars(folder, s):
    h = pd.read_csv(folder / f"{s}_1h_full.csv.gz", parse_dates=["timestamp"])
    h["timestamp"] = h.timestamp.dt.floor("h")
    h = h.sort_values("timestamp")
    g = h.groupby("timestamp")
    b = pd.DataFrame(dict(open=g.open.first(), close=g.close.last()))
    return b.reindex(pd.date_range(b.index.min(), b.index.max(), freq="h"))


def thresholds(bar, p):
    m = bar.dt.to_period("M")
    out = pd.Series(np.nan, index=bar.index)
    for mm in sorted(m.unique()):
        past = p[m < mm]
        if len(past):
            out[m == mm] = np.quantile(past, 0.80, method="linear")
    return out


def sim(P, scorecol, veto, B, start, end_bar, cost=0.0025):
    grid = pd.date_range(start, end_bar, freq="h")
    day = {t: list(g.sort_values([scorecol, "symbol"], ascending=[False, True]).symbol) for t, g in P.groupby("bar")}
    o, c, lb = {}, {}, {}
    for s, b in B.items():
        lb[s] = b.close.last_valid_index()
        cf = b.close.reindex(grid).ffill()
        o[s], c[s] = b.open.reindex(grid).fillna(cf.shift(1)).values, cf.values
    cash, held, ps, pb, curve = 10000.0, {}, [], [], []
    for k, t in enumerate(grid):
        for s in [s for s in held if t > lb[s]]:
            cash += held.pop(s) * B[s].close.loc[lb[s]] * (1 - cost)
        for s in ps:
            if s in held:
                cash += held.pop(s) * o[s][k] * (1 - cost)
        e0 = cash + sum(u * o[s][k] for s, u in held.items())
        for s in pb:
            if s in held or len(held) >= 5 or t > lb[s] or not np.isfinite(o[s][k]):
                continue
            a = min(e0 / 5, cash / (1 + cost))
            if a < 10:
                continue
            cash -= a * (1 + cost)
            held[s] = a / o[s][k]
        curve.append(cash + sum(u * c[s][k] for s, u in held.items()))
        ps, pb = [], []
        if (k + 1) % 24:
            continue
        r = day.get(t, [])
        v = veto.get(t, set())
        pos = {s: i + 1 for i, s in enumerate(r)}
        kept = [s for s in held if pos.get(s, 10 ** 9) <= 10 and s not in v]
        ps = [s for s in held if s not in kept]
        pb = [s for s in r[:5] if s not in v and s not in held][:5 - len(kept)]
    for s in list(held):
        cash += held.pop(s) * c[s][-1] * (1 - cost)
    E = pd.Series(curve, index=grid)
    d = np.r_[10000.0, E[E.index.hour == 23].values]
    dd = float(((np.maximum.accumulate(d) - d) / np.maximum.accumulate(d)).max()) * 100
    return cash, dd


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / "STEP26_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    assert hashlib.sha256((D / "test_predictions_exit.csv").read_bytes()).hexdigest() == C["test_predictions_sha256"]
    print("[V1 PASS] protocol hash as locked; predictions SHA as claimed")
    files = {"MAIN": "test_predictions_exit.csv", "PRE": "pre2020_predictions_exit.csv"}
    for per in ("MAIN", "PRE"):
        P = pd.read_csv(D / files[per], parse_dates=["bar"])
        if per == "MAIN":
            P = P.merge(pd.read_csv(LOGS_DIR / "strategy_1d_step24_1h" / "test_predictions_1h.csv", usecols=["symbol", "bar", "R24_AI"],
                                    parse_dates=["bar"]), on=["symbol", "bar"], how="left").rename(columns={"R24_AI": "score"})
        else:
            P = P.rename(columns={"R24_FROZEN": "score"})
        B = {s: bars(FOLD[per], s) for s in sorted(P.symbol.unique())}
        for r in P.sample(300, random_state=3).itertuples():
            b = B[r.symbol]
            i = b.index.get_loc(r.bar)
            f = b.open.iloc[i + 25] / b.open.iloc[i + 1] - 1 if i + 25 < len(b) else np.nan
            y = np.nan if np.isnan(f) else float(f < -0.05)
            assert (np.isnan(y) and np.isnan(r.tail24)) or y == r.tail24, (per, r.symbol, r.bar, f, r.tail24)
        print(f"[V2 PASS] {per}: 300 tail labels re-derived from raw 1h opens")
        m = P.tail24.notna()
        a = auc(P.tail24[m].values.astype(int), P.P_AI[m].values)
        want = C["AI_skill99"]["auc"] if per == "MAIN" else C["PRE_skill"]["auc"]
        assert abs(a - want) < 1e-9, (per, a, want)
        if per == "MAIN":
            ac = auc(P.tail24[m].values.astype(int), P.P_CONTROL[m].values)
            assert abs(ac - C["CONTROL_skill"]["auc"]) < 1e-9
        print(f"[V3 PASS] {per}: AI AUC {a:.4f}")
        thr = thresholds(P.bar, P.P_AI.values)
        flag = (P.P_AI >= thr) & thr.notna() & (P.bar.dt.hour == 23)
        veto = {t: set(g.symbol) for t, g in P[flag].groupby("bar")}
        start, end_bar, end = SPAN[per]
        key = "main" if per == "MAIN" else "pre"
        for name, v in (("BASE", {}), ("AI_VETO", veto)):
            final, dd = sim(P, "score", v, B, start, end_bar)
            c = C[key][name]
            assert abs(final - c["final"]) < 0.01 and abs(dd - c["max_dd_pct"]) < 0.01, (per, name, final, c)
            print(f"[V4 PASS] {per} {name}: final {final:.2f}, MaxDD {dd:.2f}%")

    g = C["gates"]
    rec = {}
    for gk, key in (("G3", "main"), ("G4", "pre")):
        r = C[key]
        rec[f"{gk}a_dd"] = r["AI_VETO"]["max_dd_pct"] <= r["BASE"]["max_dd_pct"] - 10
        rec[f"{gk}b_calmar"] = r["AI_VETO"]["calmar"] > r["BASE"]["calmar"]
        rec[f"{gk}c_random"] = r["AI_VETO"]["calmar"] > r["RANDOM_calmar_p95"]
    rec["G4d_pre_skill"] = C["PRE_skill"]["ci_low"] > 0.5
    rec["G2_skill"] = C["AI_skill99"]["ci_low"] > 0.5 and C["AI_skill99"]["auc"] > C["CONTROL_skill"]["auc"]
    assert all(rec[k] == g[k] for k in rec), (rec, g)
    print(f"[V5 PASS] gates recomputed -> {g['decision']}")


if __name__ == "__main__":
    main()
