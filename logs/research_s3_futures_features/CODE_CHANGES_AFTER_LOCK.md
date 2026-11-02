# S3: changes after the protocol lock

## 1. Verifier only: D1 cross-sectional rank check (2026-10-15)
- **What failed:** `verify_s3_claims.py D1` V2 re-ranked `xr_basis_now` among the rows stored in `D1_test_predictions.csv` for a day. The assert failed.
- **Root cause (checked with data):**
  - The S3 code (`add_fut`) ranks within the full daily panel.
    - train = all known-coin rows + eligible design-half rows;
    - test = eligible confirm-half rows from the OOS start.
  - The stored file holds only the research rows. Example: 2021-07-01 had 3 stored confirm-half rows, but 14 in the panel (rank 0.785714 = 11/14).
  - So the check compared against the wrong peer set. The model code was not changed; no claim or prediction changed.
- **Fix (verifier only):**
  - For D1, the verifier rebuilds the daily panels' membership with the research loaders.
  - It recomputes basis_now / fund_24h for every panel member with plain loops from the raw files.
  - It re-ranks with a hand-written percentile rank and compares 60 stored rows on 3 days. PASS.
  - The 60-row plain-loop feature code was moved into a function. R6 and R24 were re-verified after the change: PASS.
- **Honest note on design:**
  - For D1, the confirm-half test coins are ranked among confirm-half coins only. This peer set is smaller than the training one.
  - The research D1 rule for its core xr features is different: it ranks new coins against the known-coin reference (`rank_vs_reference`).
  - The protocol said "among the rows of the same bar". The code followed that wording, but it is a deviation from the research D1 rule.
  - No future data is involved. Ranks use same-day values only, all known at t_end.
  - It is not re-run with the other rule, because that would be a post-result change. The decision stays as registered: FAIL.
