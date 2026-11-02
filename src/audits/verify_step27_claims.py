"""
Independent verifier for logs/strategy_1d_step27_combine/claims.json.
V1 protocol hash as locked; G0 reproduction claims all true.
V2 every mix's final / max drawdown recomputed from the saved sleeve daily curves and sleeve finals (separate code).
V3 daily-return correlations recomputed.
V4 bootstrap percentiles recomputed (same seed and draw order) and the recommendation rule re-applied.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC))
from config import LOGS_DIR

D = LOGS_DIR / "strategy_1d_step27_combine"
C = json.loads((D / "claims.json").read_text())
FS = (1.0, 0.75, 0.5, 0.3)
MIXES = {"M_AI3": dict(D1=1 / 3, H4=1 / 3, H1=1 / 3), "M_AI3_BTC": dict(D1=0.25, H4=0.25, H1=0.25, BTC=0.25),
         "D1": dict(D1=1.0), "H4": dict(H4=1.0), "H1": dict(H1=1.0), "BTC": dict(BTC=1.0)}


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / "STEP27_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    assert C["G0_all"] and all(C["G0"].values())
    print(f"[V1 PASS] protocol hash as locked; all {len(C['G0'])} sleeve reproductions of verified results true")
    T = pd.DataFrame(C["decision_table"])
    rng = np.random.default_rng(27)
    for f in FS:
        for mix, w in MIXES.items():
            row = T[(T.f == f) & (T.mix == mix)].iloc[0]
            mm = []
            for per in ("MAIN", "PRE"):
                S = pd.read_csv(D / f"sleeves_{per}_f{int(f*100)}.csv", parse_dates=["date"]).set_index("date")
                fin = C["sleeve_finals"][f"{per}_f{int(f*100)}"]
                eq = sum(S[k] * wt for k, wt in w.items())
                final = sum(fin[k] * wt for k, wt in w.items())
                a = np.r_[10000.0, eq.values]
                dd = ((np.maximum.accumulate(a) - a) / np.maximum.accumulate(a)).max() * 100
                assert abs(final - row[f"{per}_final"]) < 0.01 and abs(dd - row[f"{per}_max_dd_pct"]) < 0.01, (f, mix, per)
                me = eq.groupby(eq.index.to_period("M")).last()
                mm.append((me / me.shift(1).fillna(10000.0)).values)
            pool = np.concatenate(mm)
            draws = np.prod(pool[rng.integers(0, len(pool), size=(10_000, 12))], axis=1)
            for q in (5, 50, 95):
                assert abs(round(float(np.percentile(draws, q)), 3) - row[f"y1_p{q}"]) < 1e-9, (f, mix, q)
    print(f"[V2 PASS] {len(T)} mix rows: finals and max drawdowns recomputed from sleeve curves")
    print("[V4 PASS] bootstrap percentiles recomputed exactly")
    S = pd.read_csv(D / "sleeves_MAIN_f100.csv", parse_dates=["date"]).set_index("date")
    c = S.pct_change().corr().round(3).to_dict()
    assert all(abs(c[a][b] - C["corr_daily_returns_MAIN_f100"][a][b]) < 1e-9 for a in c for b in c[a])
    print("[V3 PASS] correlations recomputed")
    ok = T[T.mix.isin(["M_AI3", "M_AI3_BTC"]) & (T.y1_p5 >= 0.50)]
    if len(ok):
        p = ok[ok.f == ok.f.max()].sort_values("y1_p50", ascending=False).iloc[0]
        assert C["recommendation"]["mix"] == p.mix and C["recommendation"]["f"] == p.f
    else:
        assert isinstance(C["recommendation"], str)
    print(f"[V4 PASS] recommendation rule re-applied -> {C['recommendation']}")


if __name__ == "__main__":
    main()
