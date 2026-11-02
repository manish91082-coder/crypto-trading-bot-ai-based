# A2 changes after the protocol lock (fc11d879…)

1. **Rows and swing features follow A0 amendment 2** (1b49a9de…, locked before any store existed).
   - Rows come from the corrected trades `logs/r2_4h_a1/correction/a1c_trades.parquet` (9,740), not the original A1 trades (9,721).
   - Swing features (`c_*`, last leg, `ladder_k`, `retr_last`) come from the REAL-TIME pivot list at T, not from `legs_all`.
   - **Why.** The A2 replay smoke test on 2026-10-19 showed that the `legs_all`-based rebuild could not see the in-progress leg. Code reading then showed that the final pivot list drops pivots that fail later (hindsight), and that pivots sharing a candle are mis-ordered.
2. **The replay runs the ORIGINAL `legs_for` on truncated data**, with a synthetic final pivot appended at the last truncated bar, so the in-progress leg (start pivot confirmed) gets a row. The legs are kept in pivot order, not sorted by start_time, because of same-candle ties.
3. **Columns that are NaN on every row are not put into `feature_list.json`.** These are `c_htf_state_4h` and `c_htf_state_1h`, which `legs_for` defines as NaN for a 4h signal. This is a trivial omission rule and is not in the protocol text.

## Result
- **Store:** 9,740 rows.
- **Replay (200 rows):** 0 mismatches on every real feature; canary 200/200 flagged.
- **Canary AUC (dev):** 0.830.
- **Features:** 36.
- **Verifier** `verify_r2_a2.py` (300 other rows, own truncation): **4/4 PASS**.
