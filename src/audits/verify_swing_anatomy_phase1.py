"""
Independent verifier for logs/research_swing_anatomy (Phase 1).
V1 protocol hash as locked; splice gate D1 all contiguous; cross-check gate D2 < 1 %.
V2 D3: zigzag_pivots on the swing-study 1D bars (2020+) reproduces logs/swing_study_1d legs for BTC, K = 2/3/4.
V3 200 random K = 3 legs: pivot prices = bar high/low, confirmation close, move / remaining arithmetic, and factors
   (ret20, RSI14 by a plain Wilder loop, SMA50 distance, vol_ratio20, nearest unbroken support by brute force, the
   higher-timeframe state by a plain scan, VAP by plain filtering) recomputed from the spliced bars.
V4 D-A medians (K = 3) recomputed from the legs file.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "research", SRC / "analytics", SRC / "pipeline_1d"):
    sys.path.insert(0, str(p))
import swing_study_1d as SS
import swing_strategy_1d as E
import swing_anatomy_phase1 as P

C = json.loads((P.OUT / "claims_phase1.json").read_text())


def close_enough(a, b, tol=1e-9):
    return (np.isnan(a) and np.isnan(b)) or abs(a - b) <= tol * max(1.0, abs(b))


def main():
    lock = (P.OUT / "PHASE1_PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((P.OUT / P.PROTO).read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    assert hashlib.sha256((P.DER / "legs_all.parquet").read_bytes()).hexdigest() == C["legs_parquet_sha256"]
    assert C["D1_all_contiguous"] and C["D2_pass"]
    print(f"[V1 PASS] hashes as locked; splice contiguous; cross-check mismatch {C['D2_mismatch_share']}")

    legs = pd.read_csv(P.LOGS_DIR / "swing_study_1d" / "swing_legs_1d.csv", parse_dates=["start_date"])
    d1 = SS.load_1d("BTCUSDT")
    for K in P.KS:
        piv = SS.zigzag_pivots(d1, K)
        st = legs[(legs.symbol == "BTCUSDT") & (legs.K == K)].sort_values(["start_date", "start_price"])
        mine = pd.DataFrame(dict(d=[d1.timestamp.iloc[q["idx"]] for q in piv[:-1]], p=[q["price"] for q in piv[:-1]])).sort_values(["d", "p"])
        assert len(st) == len(mine) and (st.start_date.values == mine.d.values).all() and np.allclose(st.start_price, mine.p, rtol=1e-9)
    print("[V2 PASS] D3: BTC 1D swing study reproduced for K = 2/3/4")

    L = pd.read_parquet(P.DER / "legs_all.parquet")
    K3 = L[L.K == P.KP]
    smp = pd.concat([g.sample(min(len(g), 20), random_state=31) for _, g in K3.groupby("tf")])
    cache = {}
    for r in smp.itertuples():
        if r.coin not in cache:
            cache[r.coin] = P.build_bars(r.coin, [], [], {})
        bars, n1h, _ = cache[r.coin]
        b = bars[r.tf]
        hi, lo, cl, qv, atr = b.high.values, b.low.values, b.close.values, b.quote_volume.values, b.ATR_14.values
        s, e, c = r.start_i, r.end_i, r.confirm_i
        assert r.start_price == (hi[s] if r.direction == "Decline" else lo[s]) and r.end_price == (lo[e] if r.direction == "Decline" else hi[e])
        assert r.confirm_close == cl[c] and s <= c
        assert close_enough(r.move_pct, (r.end_price / r.start_price - 1) * 100)
        sign = -1 if r.direction == "Decline" else 1
        assert close_enough(r.rem_atr, sign * (r.end_price - cl[c]) / atr[c])
        if c >= 20:
            assert close_enough(r.c_ret20, cl[c] / cl[c - 20] - 1)
        if c >= 21:
            assert close_enough(r.c_vol_ratio20, qv[c] / qv[c - 20:c].mean())
        if c >= 49:
            assert close_enough(r.c_dist_sma50_atr, (cl[c] - cl[c - 49:c + 1].mean()) / atr[c], 1e-7)
        # RSI14: plain Wilder recursion
        ag = al = None
        for t in range(1, c + 1):
            d = cl[t] - cl[t - 1]
            g_, l_ = max(d, 0.0), max(-d, 0.0)
            if ag is None:
                ag, al = g_, l_
            else:
                ag, al = ag + (g_ - ag) / 14, al + (l_ - al) / 14
        if c >= 14 and al > 0:
            assert close_enough(r.c_rsi14, 100 - 100 / (1 + ag / al), 1e-7)
        # nearest unbroken support: brute force over all fractal lows known by the close of bar c
        best = np.nan
        for i in range(3, c - 2):
            if i + 3 > c or lo[i] != lo[i - 3:i + 4].min():
                continue
            if lo[i] <= cl[c] and (cl[i + 3:c + 1] >= lo[i]).all():
                best = lo[i] if np.isnan(best) else max(best, lo[i])
        assert close_enough(r.c_sup_dist_atr, (cl[c] - best) / atr[c] if np.isfinite(best) else np.nan, 1e-7), (r.tf, r.coin, c)
        # higher-timeframe state by a plain scan
        tend = P.end_times(r.tf, b.timestamp.values[c:c + 1])[0]
        for h in P.HTF_LIST:
            if P.ORDER[h] >= P.ORDER[r.tf]:
                continue
            bh = bars[h]
            st = E.zz(bh, P.KP)["state"]
            et = P.end_times(h, bh.timestamp.values)
            known = [st[j] for j in range(len(bh)) if et[j] <= tend]
            assert getattr(r, f"c_htf_state_{h}") == (known[-1] if known else 0), (r.tf, h)
        # VAP by plain filtering
        w = n1h[(n1h.timestamp >= tend - P.VAP_W[r.tf].to_timedelta64()) & (n1h.timestamp < tend)]
        if len(w) >= 10 and w.quote_volume.sum() > 0:
            m = (w.low <= cl[c] + 0.25 * atr[c]) & (w.high >= cl[c] - 0.25 * atr[c])
            assert close_enough(r.c_vap_at_price, w.quote_volume[m].sum() / w.quote_volume.sum())
    print(f"[V3 PASS] {len(smp)} K=3 legs: pivots, confirmation, arithmetic and factors re-derived with plain code")

    DA = pd.read_csv(P.OUT / "DA_size_frequency.csv")
    for t in DA[DA.K == P.KP].itertuples():
        g = L[(L.K == P.KP) & (L.tf == t.tf) & (L.direction == t.direction)]
        assert close_enough(t.move_pct_median, g.move_pct.abs().median()) and close_enough(t.rem_atr_median, g.rem_atr.median())
    print("[V4 PASS] D-A medians recomputed")


if __name__ == "__main__":
    main()
