# Step 16B: code changes after the lock (2026-10-15 05:03 UTC)

## 1. Verifier V1 parsing bug (verifier only; logger code unchanged)
- `verify_forward_multi_16b.py` V1 read `PROTOCOL_SHA256.txt` with `.split()` and compared the code hash with token 1, which is the protocol FILE NAME, not the code hash. V1 therefore failed although every hash matched the lock (checked with sha256sum: protocol a8a6b7a3…, logger 23d5e9f7…, both equal to the lock).
- Fix: parse the lock file line by line into {path: sha}. No logic of the logger, the protocol or the checks V2–V5 changed.
- Verifier SHA before the fix: 246b85a85f07f29a359ce7d16f7b35c4ce613f7f58edd1ebecb6d2dfad13300e (as locked).
- Verifier SHA after the fix: 44588776574363f8914630eb4ce40825aff2985d82c1806077b0b2194965bc32  src/audits/verify_forward_multi_16b.py

## 2. Verifier V5: `r.asof` (verifier only)
- In V5, `r` is a pandas Series; `r.asof` is the pandas method `Series.asof`, not the column "asof", so the file path was wrong (FileNotFoundError). The hash-chain check before it had already passed.
- Fix: `r["asof"]`. Nothing else changed.
- Verifier SHA after fix 2: 40eaadb46ebe05a1789a6af7d822e0134d87595bcdc753e5e016715f1d869eae

## 3. 2026-10-16: verifier no longer writes into the forward run_log (audit finding)
- **Problem:** `verify_forward_multi_16b.py` V2 trains September models into a temporary folder through `forward_multi_16b.month_model`. That function logs via `log()`, so its "trained …" lines landed in `logs/forward_multi_16b/run_log.txt`.
  - In that file, lines 5–6 (2026-10-15 05:11–05:12 UTC) and lines 7–8 (18:34–18:36 UTC) are VERIFIER lines. Their models went to a temporary folder.
  - Lines 2–3 are the October production models, trained by the `--test` run.
  - The append-only log is not edited; this note is the correction.
- **Fix:** the verifier sets `FM.RUNLOG = logs/forward_multi_16b/verify_run_log.txt` right after the import.
- **Unchanged:** the ledger, predictions, models and the logger code.

## 4. 2026-10-16 ~12:15 IST: accept a LATE run (newer data present) instead of failing
- **What happened:** the PC was asleep until 10:20 IST. All tasks then fired together. The Step 16 logger finished at 10:43 IST and updated the live 1h folder up to 2026-10-16 03:00. 16B had already failed at 10:20 (Step 16 file not yet written). A manual re-run then failed at `assert btc1h == asof 23:00`, because newer bars now existed.
- **Fix:** `btc1h >= asof 23:00`. A late run is written to the notes and is marked by the existing `on_time` flag.
- **Why it is safe:**
  - Daily data is cut at the as-of day (`core_rows_1d.load_folder`: `timestamp <= asof`).
  - Scored rows are only the bars of the as-of day.
  - The paper simulators stop at END_BAR (as-of 20:00 / 23:00).
  - Every feature looks only backwards: the audit of 2026-10-16 (truncation test, `src/audits/audit_brains_noleak.py` A) showed identical features with files cut at the bar end.
- **The as-of 2026-10-15 line is LATE (`on_time=False`).** It is reported as such and does not count as on-time forward evidence.

## 5. 2026-10-16: wait for Step 16 instead of failing
In a scheduled (non-test) run, 16B now checks every 60 s, for up to 90 minutes, for the Step 16 prediction file before giving up. This is the root cause of the 2026-10-16 failure: every task fired together after a late wake. Scores are unchanged; only the start time moves.

## 6. 2026-10-16 (E2E integration test finding): the SHA256 after changes 3–5 had not been written here
- The E2E test (`src/audits/e2e_integration_test.py`, B1) ran verifier V1, which correctly refused: the current logger
  hash was not in this file. Changes 3–5 above were described but their resulting hashes were not recorded.
- Hashes after changes 3–5 (no other change; code lines involved: logger 188–198 `range(90)` wait, `btc1h >=`,
  `late_data` note; verifier: `FM.RUNLOG = ... verify_run_log.txt` after the import):
  - be7181767b56f08331625e5a718b81deae09f3ef53c8e637b2502e43a5a41a6f  src/execution/forward_multi_16b.py
  - b52940eb32c690bdc608ad3f1ed82936c2bc5caee1955f29ef3925e5e0dca3c2  src/audits/verify_forward_multi_16b.py
- Limitation stated honestly: the pre-change file was not kept (it is not in git), so "no other change" rests on the
  verifier V2–V4 equivalence checks (run again in the E2E test) rather than on a line diff.

## 7. 2026-10-16 (E2E finding): the FORWARD ledger had no verifier check
- V5 checks only the --test ledger. New V6 (verifier only; logger unchanged): forward ledger hash chain, prediction /
  input / model / paper equity file hashes, paper_M_AI3 == last M_AI3 of the paper equity file. First run: PASS (1 line).
- Verifier SHA after change 7: 74d7d71befddce63bc73eb5253735102adbc27f4c3fadb05766f4b3462ca2d97  src/audits/verify_forward_multi_16b.py

## 2026-10-25: fee amendment 2 (`logs/fees/FEE_AMENDMENT_2_1D_RECORDERS_PREREGISTERED.md` a111c707…)

- `src/execution/forward_multi_16b.py` code SHA **5c91d473d0fcc74c0677194ef1dc373ddcaeabe688f4634fc68b6864d76f7064**: COST 0.0025 → **0.00085** (true fee: BNB 0.075% + impact 0.010%), asserted against `deploy/fees.json`.
- `src/audits/verify_forward_multi_16b.py` 1404383272ce…: V4 passes cost 0.0025 explicitly (engine identity vs Step 27 at the research cost).
- **Effective:** as-of 2026-10-25 (run of 2026-10-26 07:30 IST).
- The paper is recomputed from PAPER_START every day, so this as-of shows a one-time level jump. Earlier ledger lines are unchanged.
- The pass rule (AUC) does not use costs.