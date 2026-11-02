"""BTC-ALLTF study (2026-10-28): look-ahead test for every rule, gate and the ATR used by the stops.
Each is computed on the full bars and on prefixes (first k bars, several k); the prefix result must equal the full result on
bars 0..k-1 exactly. A rule that used any later bar would differ. Usage: python src/btc_alltf/test_lookahead.py [market tf ...]"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rules                                                                  # noqa: E402

P = Path(__file__).resolve().parents[2]
JOBS = sys.argv[1:] or ["spot", "1d", "spot", "4h", "futures", "1h", "spot", "15m"]
bad, tot = [], 0
for m, tf in zip(JOBS[::2], JOBS[1::2]):
    b = pd.read_parquet(P / f"data/derived/btc_alltf/bars/{m}_{tf}.parquet")
    if len(b) > 120_000:
        b = b.iloc[-120_000:].reset_index(drop=True)                          # last 120k bars (runtime)
    full, x = rules.compute(b, tf)
    fg = rules.gates(x)
    fa = x.atr(14).values
    n = len(b)
    for k in sorted({min(n - 1, v) for v in (300, 1000, n // 3, n // 2, n - 7)}):
        pre, xp = rules.compute(b.iloc[:k].reset_index(drop=True), tf)
        pg = rules.gates(xp)
        for rid in full:
            for side in (0, 1):
                tot += 1
                if not np.array_equal(full[rid][side][:k], pre[rid][side]):
                    i = int(np.argmax(full[rid][side][:k] != pre[rid][side]))
                    bad.append((m, tf, rid, side, k, i))
        for gk in fg:
            for side in (0, 1):
                tot += 1
                if not np.array_equal(fg[gk][side][:k], pg[gk][side]):
                    bad.append((m, tf, gk, side, k, -1))
        tot += 1
        pa = xp.atr(14).values
        if not np.allclose(fa[:k], pa, equal_nan=True, rtol=0, atol=0):
            bad.append((m, tf, "ATR14", 0, k, -1))
    print(f"{m} {tf}: {n} bars checked, failures so far {len(bad)}", flush=True)
# canary: a deliberately look-ahead rule (tomorrow's close) must be caught by the same comparison
rules.add("CANARY_FUTURE", "test", "state", lambda x: rules.st(x.c.shift(-1) > x.c, x.c.shift(-1) < x.c))
b = pd.read_parquet(P / "data/derived/btc_alltf/bars/spot_1d.parquet")
cf, _ = rules.compute(b, "1d")
cp, _ = rules.compute(b.iloc[:1000].reset_index(drop=True), "1d")
caught = not np.array_equal(cf["CANARY_FUTURE"][0][:1000], cp["CANARY_FUTURE"][0])
rules.REG.pop()
print(f"[{'PASS' if caught else 'FAIL'}] canary look-ahead rule detected: {caught}")
if not caught:
    bad.append(("canary", "1d", "CANARY_FUTURE", 0, 1000, -1))
for r in bad[:50]:
    print("[FAIL]", r)
print(f"TOTAL {tot} comparisons, FAIL {len(bad)}")
sys.exit(1 if bad else 0)
