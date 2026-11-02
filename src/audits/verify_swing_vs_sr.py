"""
Independent verifier for logs/research_swing_vs_sr.
V1 protocol hash as locked; G0 (1D swing-study reproduction) all identical.
V2 200 random Part-A rows: SR hits re-derived with plain loops (fractal levels re-found, activation, close-break scan),
   VAP share re-derived from raw 1h candles.
V3 200 random Part-B events: first touch and TURN flag re-derived with plain loops against freshly computed ZigZag pivots.
V4 headline Part-A / Part-B means recomputed from the saved tables.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "research", SRC / "analytics"):
    sys.path.insert(0, str(p))
from config import LOGS_DIR
import swing_study_1d as SS
import swing_vs_sr_study as W

D = LOGS_DIR / "research_swing_vs_sr"
C = json.loads((D / "claims.json").read_text())


def levels_plain(b, side):
    hi, lo, ts = b.high.values, b.low.values, b.timestamp.values
    out = []
    for i in range(3, len(b) - 4):
        if side == "resistance" and hi[i] == hi[i - 3:i + 4].max():
            out.append((hi[i], ts[i + 4]))
        if side == "support" and lo[i] == lo[i - 3:i + 4].min():
            out.append((lo[i], ts[i + 4]))
    return out


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / W.PROTO).read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    assert C["G0_all_identical"]
    print(f"[V1 PASS] protocol hash as locked; G0: {len(C['G0'])} coin x K 1D swing sets reproduced exactly")
    A = pd.read_csv(D / "partA_pivots_and_control.csv.gz", parse_dates=["touch_time"])
    B = pd.read_csv(D / "partB_events.csv.gz", parse_dates=["touch_time"])
    cache, lvc = {}, {}
    sa = A.sample(200, random_state=21)
    for r in sa.itertuples():
        if r.coin not in cache:
            cache[r.coin] = W.load_bars(r.coin)
        bars, h1, _ = cache[r.coin]
        sw = bars[r.swing_tf]
        cl, ts = sw.close.values, sw.timestamp.values
        side = "support" if r.kind == "L" else "resistance"
        hit_any = False
        for tfl in W.TFL_FOR[r.swing_tf]:
            key = (r.coin, tfl, side)
            if key not in lvc:
                lvc[key] = levels_plain(bars[tfl], side)
            hit = False
            for L, ct in lvc[key]:
                a = int(np.searchsorted(ts, ct, "left"))
                if a > r.idx or abs(L - r.price) > W.NEAR * r.atr:
                    continue
                seg = cl[a:r.idx]
                broken = (seg < L).any() if side == "support" else (seg > L).any()
                if not broken:
                    hit = True
                    break
            assert float(hit) == getattr(r, f"sr_{tfl}"), (r, tfl, hit)
            hit_any |= hit
        assert float(hit_any) == r.sr_any
        w = h1[(h1.timestamp >= r.touch_time - W.VAP_W[r.swing_tf]) & (h1.timestamp < r.touch_time)]
        if np.isfinite(r.vap):
            m = (w.low <= r.price + W.BAND * r.atr) & (w.high >= r.price - W.BAND * r.atr)
            assert abs(w.quote_volume[m].sum() / w.quote_volume.sum() - r.vap) < 1e-9
    print("[V2 PASS] 200 Part-A rows: SR hits (plain-loop levels, activation, close-break) and VAP re-derived")
    piv_cache = {}
    for r in B.sample(200, random_state=22).itertuples():
        bars, _, _ = cache[r.coin] if r.coin in cache else cache.setdefault(r.coin, W.load_bars(r.coin))
        sw = bars[r.swing_tf]
        key = (r.coin, r.swing_tf)
        if key not in piv_cache:
            piv_cache[key] = SS.zigzag_pivots(sw, W.K_PRIMARY)
        kd = "H" if r.side == "resistance" else "L"
        turn = any(q["kind"] == kd and r.touch_i <= q["idx"] <= r.touch_i + 2 and abs(q["price"] - r.level) <= W.NEAR * r.atr
                   for q in piv_cache[key])
        assert float(turn) == r.turn, (r, turn)
        hi, lo = sw.high.values, sw.low.values
        assert (hi[r.touch_i] >= r.level) if r.side == "resistance" else (lo[r.touch_i] <= r.level)
    print("[V3 PASS] 200 Part-B events: touch and TURN flag re-derived against freshly computed ZigZag pivots")
    TA = pd.read_csv(D / "partA_table.csv")
    for t in TA[TA.measure == "sr_any"].itertuples():
        g = A[(A.swing_tf == t.swing_tf) & (A.K == t.K)]
        assert abs(round(g[g.group == "SWING"].sr_any.mean(), 4) - t.mean_a) < 1e-9
    TB = pd.read_csv(D / "partB_table.csv")
    for t in TB[(TB.comparison == "REAL_vs_CONTROL") & (TB.side == "both")].itertuples():
        g = B[(B.swing_tf == t.swing_tf) & (B.kind == "REAL")]
        assert abs(round(g.turn.mean(), 4) - t.mean_a) < 1e-9
    print("[V4 PASS] headline Part-A and Part-B rates recomputed")


if __name__ == "__main__":
    main()
