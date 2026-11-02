"""
POST-LOCK diagnostics for the ladder + sessions study (added 2026-10-17 AFTER seeing results; documented in
logs/research_ladder_sessions/CODE_CHANGES_AFTER_LOCK.md). They do not replace the pre-registered verdicts; they test
whether two pre-registered nulls were the right comparison:
 P1 Fibonacci: the pre-registered control points (0.30/0.44/0.56/0.70) are not density-matched. Here each level's
    +-0.02 share is compared with a LOCAL density null = share within +-0.06 of the same level / 3.
 P2 Daily high/low hour: for a driftless random walk the time of the maximum/minimum over a day follows the arcsine law,
    so the first and last hours are more likely than uniform. Expected session shares under that law are reported.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ladder_sessions as L

FIBS = [0.382, 0.5, 0.618]


def ratios(legs, tf):
    out = []
    for coin in L.COINS:
        g = legs[(legs.coin == coin) & (legs.tf == tf) & (legs.K == 3.0)].sort_values("start_time")
        if len(g) < 4:
            continue
        pt = L.points(g)
        for which, step_t, retr_t in (("UP", "H", "L"), ("DOWN", "L", "H")):
            for idx, _ in L.runs(pt, which):
                for i in idx:
                    if pt.typ.iloc[i] == retr_t and i >= 1 and pt.move.iloc[i - 1] > 0:
                        out.append(pt.move.iloc[i] / pt.move.iloc[i - 1])
    a = np.array(out)
    return a[(a > 0) & (a < 1)]


def main():
    legs = pd.read_parquet(L.LEGS, columns=["coin", "tf", "K", "direction", "start_time", "start_price", "end_time", "end_price",
                                            "end_i", "confirm_time", "atr_start", "move_atr"])
    rows = []
    for tf in L.INFER_TFS:
        a = ratios(legs, tf)
        for c in FIBS:
            obs = np.mean(np.abs(a - c) <= 0.02)
            exp = np.mean(np.abs(a - c) <= 0.06) / 3
            z = (obs - exp) / np.sqrt(exp * (1 - exp) / len(a))
            rows.append(dict(tf=tf, level=c, n=len(a), observed=obs, local_null=exp, ratio=obs / exp, z=z))
    P1 = pd.DataFrame(rows)
    P1.to_csv(L.OUT / "P1_fib_local_density_null.csv", index=False)
    def arcsine(a, b):
        return 2 / np.pi * (np.arcsin(np.sqrt(b)) - np.arcsin(np.sqrt(a)))
    edges = {"Asia": (0, 8), "Europe": (8, 13), "US": (13, 21), "LateUS": (21, 24)}
    H = pd.read_csv(L.OUT / "B3_daily_high_low_session.csv")
    H["arcsine_null"] = H.sess.map({s: arcsine(a / 24, b / 24) for s, (a, b) in edges.items()})
    H.to_csv(L.OUT / "P2_daily_high_low_vs_arcsine.csv", index=False)
    print(P1.round(4).to_string())
    print(H.round(4).to_string())


if __name__ == "__main__":
    main()
