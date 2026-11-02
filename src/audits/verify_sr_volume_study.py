"""
Independent verifier for logs/research_sr_volume.
V1 protocol hash as locked.
V2 300 random events re-derived with plain bar-by-bar loops: touch condition, touch outcome, aftermath, forward return,
   and (REAL) the VAP share from raw 1h candles.
V3 family break rates (A1 real_mean, side == both) recomputed from the event table.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "research"):
    sys.path.insert(0, str(p))
from config import LOGS_DIR
import sr_volume_study as V

D = LOGS_DIR / "research_sr_volume"
C = json.loads((D / "claims.json").read_text())
EVAL_OF = {f: e for f, _, e, _ in V.FAMILIES} | {f"R{N}": "1d" for N in V.RANGES}


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / V.PROTO).read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    print("[V1 PASS] protocol hash as locked")
    E = pd.read_csv(D / "events.csv.gz", parse_dates=["touch_time"])
    smp = pd.concat([g.sample(min(len(g), 22), random_state=9) for _, g in E.groupby(["family", "kind"])])
    cache = {}
    for r in smp.itertuples():
        etf = EVAL_OF[r.family]
        if (r.coin, etf) not in cache:
            cache[(r.coin, etf)] = V.load(r.coin, etf)
        if (r.coin, "1h") not in cache:
            cache[(r.coin, "1h")] = V.load(r.coin, "1h")
        b = cache[(r.coin, etf)]
        hi, lo, cl = b.high.values, b.low.values, b.close.values
        n, j, L, res = len(b), r.touch_i, r.level, r.side == "resistance"
        H, F = V.EVAL[etf]["H"], V.EVAL[etf]["F"]
        assert (hi[j] >= L) if res else (lo[j] <= L)
        if r.family.startswith("P"):                                  # first touch from the activation bar
            for q in range(r.active_i, j):
                assert not ((hi[q] >= L) if res else (lo[q] <= L)), (r, q)
        tr = [max(hi[q] - lo[q], abs(hi[q] - cl[q - 1]), abs(lo[q] - cl[q - 1])) for q in range(j - 14, j)]
        A = float(np.mean(tr))
        assert abs(A - r.atr) <= 1e-9 * max(1.0, A)

        def scan(start, lim, beyond, back):
            for q in range(start, min(lim, n - 1) + 1):
                x, y = beyond(q), back(q)
                if x and y:
                    return "AMB", q
                if x or y:
                    return ("X" if x else "Y"), q
            return "TO", None
        if (hi[j] >= L + A) if res else (lo[j] <= L - A):
            out, bq = "BREAK", j
        else:
            k, q = scan(j + 1, j + H, (lambda q: hi[q] >= L + A) if res else (lambda q: lo[q] <= L - A),
                        (lambda q: lo[q] <= L - A) if res else (lambda q: hi[q] >= L + A))
            out, bq = {"X": "BREAK", "Y": "BOUNCE", "AMB": "AMBIGUOUS", "TO": "TIMEOUT"}[k], q
        assert out == r.outcome, (r, out)
        if out == "BREAK":
            assert bq == r.break_i
            if (hi[bq] >= L + 2 * A) if res else (lo[bq] <= L - 2 * A):
                aft = "CONTINUE"
            else:
                k, _ = scan(bq + 1, bq + H, (lambda q: hi[q] >= L + 2 * A) if res else (lambda q: lo[q] <= L - 2 * A),
                            (lambda q: lo[q] <= L) if res else (lambda q: hi[q] >= L))
                aft = {"X": "CONTINUE", "Y": "RECLAIM", "AMB": "AMBIGUOUS", "TO": "TIMEOUT"}[k]
            assert aft == r.after, (r, aft)
            f = cl[bq + F] / cl[bq] - 1 if bq + F < n else np.nan
            assert (np.isnan(f) and np.isnan(r.fwd)) or abs(f - r.fwd) < 1e-12
        if r.kind == "REAL" and np.isfinite(r.vap):
            h = cache[(r.coin, "1h")]
            w = h[(h.timestamp >= r.touch_time - V.EVAL[etf]["W"]) & (h.timestamp < r.touch_time)]
            hit = (w.low <= L + V.BAND * A) & (w.high >= L - V.BAND * A)
            assert abs(w.quote_volume[hit].sum() / w.quote_volume.sum() - r.vap) < 1e-9
    print(f"[V2 PASS] {len(smp)} events re-derived bar by bar (touch, outcome, aftermath, forward return, VAP share)")
    A1 = pd.read_csv(D / "A1_strength.csv")
    for t in A1[A1.side == "both"].itertuples():
        x = E[(E.family == t.family) & (E.kind == "REAL") & E.outcome.isin(["BREAK", "BOUNCE"])]
        assert abs(round((x.outcome == "BREAK").mean(), 4) - t.real_mean) < 1e-9, t.family
    print(f"[V3 PASS] {int((A1.side == 'both').sum())} family break rates recomputed")


if __name__ == "__main__":
    main()
