# Changes after the FR protocol lock (3d9c9693…)

## 1. 2026-10-19: S-series paging bug found in T1, then fixed (recorder code)
- **What T1 showed.** The first local run passed V1–V7, but V4 reported 368 missing 5m stamps: exactly 16 in each of the 23 `taker_ratio` series and 0 in the other five endpoints.
- **Cause, measured on the stored raw files.** `/futures/data/takerlongshortRatio` returns rows from floor(startTime) to the 5m grid, whereas the other five endpoints return rows from ceil(startTime). With fixed 500-stamp windows and the `ts >= startTime` keep rule, one stamp was lost at every page boundary.
- **Fix.** Cursor paging: the next request starts 1 ms after the last KEPT stamp. The keep rule itself is unchanged.
- **The T1 output is kept unchanged as evidence** in `logs/forward_recorder_r2_localtest_T1_bugged_kept_as_evidence/`. Nothing was deleted. T1 was then re-run from scratch into a fresh `logs/forward_recorder_r2_localtest/`.

## 2. 2026-10-19: verifier V8 added (a stronger check; the protocol is only narrowed)
- **What V8 does.** It re-queries Binance for up to 60 randomly sampled missing 5m S stamps inside the 30-day window. A stamp that exists at Binance means the recorder lost it, and V8 FAILs.
- **Why it was added.** The protocol treated missing S stamps as "reported, not a failure" because Binance omits periods with no trades. That rule alone would have hidden this bug.
- **Result on the bugged T1:** 60 of 60 sampled missing stamps were present at Binance, so V8 = FAIL, as it should be.

## 3. Finality margin and stale lock (implementation details written into the first code version, declared here)
- **Finality margin.** A 5m S row is kept only when ts + 5 min ≤ the run's server time.
- **Stale lock.** A lock file older than 3 h is treated as stale (a crashed run): it is removed and noted in the ledger. Without this, one crash would stop the recorder for good, and data older than 30 days would be lost.
557fa486ff86b77793735bdb4e3502c14bc8f2f04f5710d3e87f3d4482cf81c2 *src/execution/forward_recorder_r2.py
f5b17a125ccdfd9f19a25292a85f298dc787ace434fc8cbf385491f28ded940b *src/audits/verify_forward_recorder_r2.py

## 4. 2026-10-19: crash safety, code SHA at start, LOST note, test-only options (recorder; found by code review)
- **Crash safety.** A crash between the state write and the ledger line left an orphan run folder and a state that counted unchained rows. That would make the verifier fail forever, and it could skip data.
  - The run now writes `raw/<run>/state_after.json`, then the manifest, then the ledger line (whose `state_sha256` is the hash of `state_after.json`), and only then replaces `state.json` by an atomic rename.
  - At start, `recover()` quarantines every run folder without a ledger line to `raw_orphans/`. It takes `state.json` only if its SHA equals the last ledger line's; otherwise it restores from that run's `state_after.json`; otherwise it stops with a message.
- **Code SHA.** It is now hashed at the start of the run, not at the end, so an edit made during a run cannot be attributed to it.
- **LOST note.** A series whose last stamp is older than the 29-day window gets a ledger note with the number of unrecoverable stamps.
- **Test-only options:** `--test-symbols`, `--test-server-offset-ms` and `--test-s-back-days`. Each is refused without `--test-symbols`, and each writes a "TEST" note into the ledger. Production runs never pass them.

## 5. 2026-10-19: verifier
- **V2a.** Run folders are matched to ledger lines by run_id, no longer by order. An orphan folder FAILs, with a message.
- **State hash.** `state_after.json` is checked against the ledger `state_sha256` when it is present.
- **Network retries.** The V3 and V8 public requests retry 3 times (2 s, 5 s, 10 s). A request that still fails makes the check FAIL; it never passes.
  - **Why:** a transient connection reset crashed the verifier during the T2 rerun. That log is kept in `T2_T4_tests_after_change3.txt`.

## Test evidence after changes 3–5
- **`T5_T9_robust_tests.txt`:**
  - T5: a 3-day downtime with all 12 S series resumed (up to 3 pages per series);
  - T6: a crash before the ledger line;
  - T7: a crash after the ledger line;
  - T8: the LOST note;
  - T9: the guard.
  - All PASS.
- **The first T5 design was flawed and is kept:** `T5_T9_robust_tests_run1_offset_artifact.txt`. Its offset start fell outside Binance's 30-day window, so 5 of the 6 endpoints returned HTTP 400 and were not really resume-tested. Fixed with `--test-s-back-days 5`; run 1 now has 0 HTTP errors and 12 of 12 series.
- **`T2_T4_tests_after_change3.txt` + `T2_verify_after_change3.txt`:** the main local root, now 3 chained runs. Verifier 9/9 PASS; T3a/b/c and T4 PASS.
e19d45796cf6d700b148cc264805c55326ca52c6d5a71d6b16bdb03544bba572 *src/execution/forward_recorder_r2.py
c6a6e7cdb4d481afaab4cad5188741f087375c4f3b57e3f91ce65004d3205bcd *src/audits/verify_forward_recorder_r2.py
257c489fdc8b4cf45b8fdcf6a7358d1fe3490e1a596d0778e3473ed69fda9c8d *src/audits/test_forward_recorder_r2_robust.py
