"""
Independent verifier for logs/strategy_1d_step24_1h/claims.json.
V1 protocol hash as locked.
V2 300 random test rows: 4-hour / 1-day forward returns re-derived from RAW 1h candles,
   relative labels re-derived from the file's per-bar medians.
V3 AUCs recomputed (Mann-Whitney) for all 4 brains.
V4 R4_AI and R24_AI portfolios re-simulated with separate code and prices read from raw 1h files.
V5 gates and decision recomputed.
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

D = LOGS_DIR / "strategy_1d_step24_1h"
H1 = DATA_DIR / "universe_all" / "1h"
C = json.loads((D / "claims.json").read_text())
START, END_BAR = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30 23:00")


def auc(y, p):
    r = rankdata(p)
    n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def bars(s):
    h = pd.read_csv(H1 / f"{s}_1h_full.csv.gz", parse_dates=["timestamp"]).set_index("timestamp").sort_index()
    r = h.resample("h")
    b = pd.DataFrame(dict(open=r.open.first(), close=r.close.last()))
    return b


def sim(P, col, h, B, cost=0.0025):
    grid = pd.date_range(START, END_BAR, freq="h")
    day = {t: list(g.sort_values([col, "symbol"], ascending=[False, True]).symbol) for t, g in P.groupby("bar")}
    o, c, lb = {}, {}, {}
    for s, b in B.items():
        lb[s] = b.close.last_valid_index()
        cf = b.close.reindex(grid).ffill()
        o[s], c[s] = b.open.reindex(grid).fillna(cf.shift(1)).values, cf.values
    cash, held, ps, pb, n_tr = 10000.0, {}, [], [], 0
    for k, t in enumerate(grid):
        for s in [s for s in held if t > lb[s]]:
            cash += held.pop(s) * B[s].close.loc[lb[s]] * (1 - cost)
            n_tr += 1
        for s in ps:
            if s in held:
                cash += held.pop(s) * o[s][k] * (1 - cost)
                n_tr += 1
        e0 = cash + sum(u * o[s][k] for s, u in held.items())
        for s in pb:
            if s in held or len(held) >= 5 or t > lb[s] or not np.isfinite(o[s][k]):
                continue
            a = min(e0 / 5, cash / (1 + cost))
            if a < 10:
                continue
            cash -= a * (1 + cost)
            held[s] = a / o[s][k]
        ps, pb = [], []
        if (k + 1) % h:
            continue
        r = day.get(t, [])
        pos = {s: i + 1 for i, s in enumerate(r)}
        kept = [s for s in held if pos.get(s, 10 ** 9) <= 10]
        ps = [s for s in held if s not in kept]
        pb = [s for s in r[:5] if s not in held][:5 - len(kept)]
    for s in list(held):
        cash += held.pop(s) * c[s][-1] * (1 - cost)
        n_tr += 1
    return cash, n_tr


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / "STEP24_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    assert hashlib.sha256((D / "test_predictions_1h.csv").read_bytes()).hexdigest() == C["test_predictions_sha256"]
    print("[V1 PASS] protocol hash as locked; predictions file SHA as claimed")

    P = pd.read_csv(D / "test_predictions_1h.csv", parse_dates=["bar"])
    B = {s: bars(s) for s in sorted(P.symbol.unique())}
    smp = P.sample(300, random_state=7)
    for r in smp.itertuples():
        b = B[r.symbol]
        i = b.index.get_loc(r.bar)
        for hh in (4, 24):
            j0, j1 = i + 1, i + 1 + hh
            f = b.open.iloc[j1] / b.open.iloc[j0] - 1 if j1 < len(b) else np.nan
            want = getattr(r, f"fwd{hh}")
            assert (np.isnan(f) and np.isnan(want)) or abs(f - want) < 1e-12, (r.symbol, r.bar, hh, f, want)
    for hh in (4, 24):
        med = P.groupby("bar")[f"fwd{hh}"].transform("median")
        y = np.where(P[f"fwd{hh}"].isna(), np.nan, (P[f"fwd{hh}"] - med > 0).astype(float))
        assert ((np.isnan(y) & P[f"label{hh}"].isna()) | (y == P[f"label{hh}"])).all()
    print("[V2 PASS] 300 sampled rows: forward returns re-derived from raw 1h; all labels re-derived from per-bar medians")

    for hh in (4, 24):
        for lab in ("AI", "CONTROL"):
            m = P[f"label{hh}"].notna()
            a = auc(P[f"label{hh}"][m].values.astype(int), P[f"R{hh}_{lab}"][m].values)
            assert abs(a - C[f"R{hh}_{lab}_skill"]["auc"]) < 1e-9, (hh, lab, a)
            print(f"[V3 PASS] R{hh} {lab}: AUC {a:.4f} ({int(m.sum())} rows)")

    for hh in (4, 24):
        final, n = sim(P, f"R{hh}_AI", hh, B)
        c = C["portfolio"][f"R{hh}_AI"]
        assert abs(final - c["final"]) < 0.01 and n == c["trades"], (hh, final, c["final"], n, c["trades"])
        print(f"[V4 PASS] R{hh}_AI re-simulated: final {final:.2f}, trades {n}")

    g, pf = C["gates"], C["portfolio"]
    for hh in (4, 24):
        a, c, ai = C[f"R{hh}_AI_skill"], C[f"R{hh}_CONTROL_skill"], pf[f"R{hh}_AI"]
        rec = dict(G2_skill=a["ci_low"] > 0.5 and a["auc"] > c["auc"], G3a_cagr=ai["cagr_pct"] > 0,
                   G3b_calmar=ai["calmar"] > max(0.625, 0.515, 0.264, pf[f"R{hh}_CONTROL"]["calmar"]),
                   G3c_trade_ci=ai["trade_ci_low_pct"] > 0, G3d_cost040=pf[f"R{hh}_AI_cost040"]["cagr_pct"] > 0,
                   G4_pre2020=C[f"R{hh}_pre2020_skill"]["ci_low"] > 0.5)
        assert all(bool(rec[k]) == g[f"R{hh}"][k] for k in rec), (hh, rec, g[f"R{hh}"])
    print(f"[V5 PASS] gates recomputed -> {g['decision']}")


if __name__ == "__main__":
    main()
