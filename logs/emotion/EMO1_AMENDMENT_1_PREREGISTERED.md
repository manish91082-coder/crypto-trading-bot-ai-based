# EMO-1 amendment 1 (2026-10-24): explicit concat sort (code hygiene, no result change allowed)

**Amends:** the EMO-1 code `src/research/emo1_study.py` ac5f954111a8…. The protocol `EMO1_PROTOCOL_PREREGISTERED.md` is unchanged.

**Lock and approval.** Locked before the code change. The user approved the work on 2026-10-24.

## Why

The dev run of 2026-10-23 printed a pandas `Pandas4Warning` at line 121 (419 times) and at line 218 (once):

> "Sorting by default when concatenating all DatetimeIndex is deprecated … In the future, pandas will respect the default of sort=False."

Today pandas sorts. A future pandas would not sort, and the beta (line 121) and the G2/G3 join (line 218) could silently change.

## Change

- Lines 121 and 218: `pd.concat([...], axis=1)` → `pd.concat([...], axis=1, sort=True)`.
- This writes down today's behaviour. Nothing else changes.

## Proof required (all, or the change is reverted)

- **P1:** the original panel, panel SHA file and dev report files are backed up first, to `data/emotion/emo1_backup_pre_A1/` and `logs/emotion/backup_pre_A1/`.
- **P2:** `emo1_study.py build` with the new code gives a `panel.parquet` whose SHA256 == bd1e40b831075f5578aa16ccf6d0cb2ffdc79044c49643a3de04b1d68df16eb1.
- **P3:** `emo1_study.py dev` with the new code gives a report equal to the recorded dev report (e8f84fc42c8b…) in every field except `code_sha256`.
- **P4:** `verify_emo1.py dev` gives 4/4 PASS.
- **P5:** no Pandas4Warning from lines 121 and 218 in the new run's output.

## Record

- The recorded dev report (e8f84fc42c8b…, made by ac5f954111a8…) stays the authoritative one and is restored after the check.
- The new run's report is kept as `EMO1_DEV_REPORT_postA1.json`.
- The holdout stays unopened.

## Not in scope (a finding to record only)

- Lines 111–112 make ±inf or NaN when a 24 h/48 h volume difference or the 167 h volatility is 0 (RuntimeWarning in the dev run).
  - These feed only the exploratory candle rank-IC table, not the P score or the gates.
  - The count of such rows is recorded in CODE_NOTES. Any fix belongs to a future pre-registered candle trial.
