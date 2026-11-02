"""
Independent verifier for logs/research_sr_levels (S/R evidence study).
V1 protocol hash as locked.
V2 400 random events (REAL and CONTROL, all timeframes): swing test (REAL), side condition, first touch and outcome
   re-derived with plain bar-by-bar Python loops.
V3 bounce rates in results_table.csv (part == all) recomputed from the event table.
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
import sr_levels_study as S

D = LOGS_DIR / "research_sr_levels"
C = json.loads((D / "claims.json").read_text())


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / S.PROTO).read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    print("[V1 PASS] protocol hash as locked")
    E = pd.read_csv(D / "events.csv.gz")
    smp = pd.concat([g.sample(min(len(g), 23), random_state=5) for _, g in E.groupby(["tf", "kind"])])
    cache = {}
    for r in smp.itertuples():
        key = (r.coin, r.tf)
        if key not in cache:
            cache[key] = S.bars(r.coin, r.tf)
        b = cache[key]
        hi, lo, cl = b.high.values, b.low.values, b.close.values
        n, i, c, L = len(b), r.bar_i, r.confirm_i, r.level
        res = r.side == "resistance"
        assert c == i + 3 and L == (hi[i] if res else lo[i])
        if r.kind == "REAL":
            w = hi[i - 3:i + 4] if res else lo[i - 3:i + 4]
            assert (L == w.max()) if res else (L == w.min())
        assert (L > cl[c]) if res else (L < cl[c])
        j = c + 1
        while j < n and not ((hi[j] >= L) if res else (lo[j] <= L)):
            j += 1
        assert j == r.touch_i, (r, j)
        tr = [max(hi[q] - lo[q], abs(hi[q] - cl[q - 1]), abs(lo[q] - cl[q - 1])) for q in range(j - 14, j)]
        a = float(np.mean(tr))
        assert abs(a - r.atr) <= 1e-9 * max(1, a), (a, r.atr)
        if (hi[j] >= L + a) if res else (lo[j] <= L - a):
            want = "BREAK"
        else:
            want = "TIMEOUT"
            for q in range(j + 1, min(j + 48, n - 1) + 1):
                brk = (hi[q] >= L + a) if res else (lo[q] <= L - a)
                bnc = (lo[q] <= L - a) if res else (hi[q] >= L + a)
                if brk and bnc:
                    want = "AMBIGUOUS"
                    break
                if brk or bnc:
                    want = "BREAK" if brk else "BOUNCE"
                    break
        assert want == r.outcome, (r, want)
    print(f"[V2 PASS] {len(smp)} events re-derived bar by bar (swing test, side, first touch, ATR, outcome)")
    T = pd.read_csv(D / "results_table.csv")
    for t in T[T.part == "all"].itertuples():
        s = E[(E.tf == t.tf) & ((E.side == t.side) | (t.side == "both")) & E.outcome.isin(["BOUNCE", "BREAK"])]
        for kind, col in (("REAL", "bounce_real"), ("CONTROL", "bounce_ctrl")):
            x = s[s.kind == kind]
            assert abs(round((x.outcome == "BOUNCE").mean(), 4) - getattr(t, col)) < 1e-9, (t.tf, t.side, kind)
    print(f"[V3 PASS] {int((T.part == 'all').sum())} bounce-rate rows recomputed from the event table")


if __name__ == "__main__":
    main()
