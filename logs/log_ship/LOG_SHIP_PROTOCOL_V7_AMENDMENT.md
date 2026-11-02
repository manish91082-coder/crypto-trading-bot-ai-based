# Log shipping protocol v7 amendment (2026-10-25): a run never reuses the (hour, tag) of an earlier run

**Amends:** v1–v6. Everything else is unchanged. Locked before the code change.

## Why (evidence gathered before this lock)

**Open item.** `CODE_CHANGES_AFTER_LOCK.md` entry 7: on the VM, T4-verify failed with W1 / W2 / W3 for the old (v5) and the new (v6) code alike.

**Reproduction.** 2026-10-25 ~05:17 UTC, VM, `/tmp/ls7` mirror:
- Inputs: the same 10 small log dirs (336 files) + an extra root with 68 v3/v6 files.
- Code: the live v6 files (ship 8d3a4df69f50, verifier 5fca063c8ebe, test 9bed43c0806c, stub aeeb22758741).
- Result: 7/8 tests passed; T4-verify FAILED, as in entry 7.

**Root cause.**
- The run tag is `HHMMSS` (one-second resolution). Every per-run name is built from `(hour, tag)`:
  - `manifests/{hour}_{tag}.json`;
  - `manifests/{hour}_{tag}.result.json`;
  - the remote `hourly/{hour}/bundle_{tag}.tar.gz` and `bundle_{tag}_manifest.json`.
- On the VM a stub run takes ~0.3 s, so back-to-back test runs fall in the same second. The ledger showed two collisions: 051703 (T2 + T3) and 051704 (T4 + the FRESH_JOB run).
- The later run overwrites the earlier run's local manifest, its result file and its remote bundle. The verifier then reports:
  - **W1:** the earlier row's manifest SHA no longer matches;
  - **W2:** the earlier row's remote bundle MD5 no longer matches;
  - **W3:** `bundle … not on remote`, or the check is blinded because the result file of the run that freed the file was overwritten.
- On the laptop each run takes > 1 s, which is why the laptop runs passed.

**The same defect, in production terms.** Seen in the test:
- The T4 run freed `TEST_JOB.out` after its bundle was verified.
- The next run in the same second overwrote that bundle on the remote.
- So the freed chunk then existed nowhere. The run also breaks the rule "nothing is ever deleted on the remote".

**Production exposure (observed, before this lock).**
- Cron starts LogShip once per hour (`55 * * * *` in IST = :25 UTC). The lock blocks overlapping runs.
- The live ledger has 136 rows with 0 duplicate `(hour, tag)` pairs and at most 2 runs per hour (manual runs on 10-19 and 10-22).
- Every live run had ≥ 4 members, so it uploaded to Drive. The last 5 runs took 55–174 s (`cron_status/LogShip.csv`). Two sequential runs therefore cannot start in the same second.
- The remaining path is two processes that start within the same second and both pass the non-atomic check `lock.exists()` → `write_text`. For example: a manual run that starts at the same instant as the cron run.
- **Conclusion:** practically unreachable in production today. The fix closes the defect itself (data overwrite on the remote), and it lets the VM test gate go green again.

## v7 change

**Shipper (`deploy/ship_logs_drive.py`):**
1. **Atomic lock.** `RUNNING.lock` is created with `O_CREAT|O_EXCL`.
   - An existing lock younger than `LOCK_STALE_S` → exit 0, "another ship run is active", the same as before.
   - An older lock is removed and creation is retried once.
2. **Unique tag.** While holding the lock, if `manifests/{hour}_{tag}.json` or `.result.json` already exists, the run waits 0.1 s and takes the time again, until the name is free.
   - Cap: 100 tries (10 s). If the cap is reached, exit 1 and write nothing (a frozen clock is the only way to reach it).
   - The tag format, the file names, the remote layout and everything else stay unchanged.

**Verifier (`src/audits/verify_log_ship.py`).** This only makes the check stricter.
- W1 also fails on any duplicate `(hour, tag)` in the ledger, and its message gives the count.
- W1 also checks the V7 lock.

**Tests (`src/audits/test_log_ship.py`):**
- **T8 (deterministic).** The test writes placeholder manifests for the current second and the next 2 seconds, then runs the shipper once. Pass when:
  - every placeholder (or a real manifest that already sat in one of those seconds) is byte-identical afterwards;
  - the new ledger row's tag is none of those tags;
  - the row is verified, with exit 0.
- **T9 (POSIX only; the VM).** 4 shipper processes start at the same time, with an rclone wrapper that sleeps 2 s per call. Pass when:
  - the ledger grows by exactly 1 row;
  - 3 processes print "another ship run is active";
  - all exit 0.
- **T8/T9-verify.** Verifier W1–W4 PASS after T7–T9 (`--hours 10`), before the T5 tamper.
- T1–T7, T4-verify and T5 are unchanged.

## Pre-registered pass criteria

All runs use the VM `/tmp/ls7` mirror with the inputs above.

- **P1 (new code).** Ship v7 + verifier v7 + test v7: every test PASSES — 11/11, W4 17/17.
- **P2 (old shipper).** Ship v6 8d3a4df69f50 + verifier v7 + test v7 on the same inputs: **T8 FAILS** (deterministic). T4-verify is expected to FAIL; that is reported, but not required, because it depends on timing.
- **P3 (control: the fix is in the shipper, not in the stricter verifier).** Ship v7 + the OLD verifier v6 5fca063c8ebe + test v7: T4-verify and T8/T9-verify PASS.
- **P4.** Laptop (stub, Windows): ship v7 + verifier v7 + test v7: every test that runs PASSES (T9 is skipped on Windows).
- **Any other outcome is reported as is.** The live shipper is not changed unless P1–P3 hold.

## Deployment

- The live VM files are replaced only after P1–P3 hold **and** the user says go.
- The amendment and its lock file go to `/opt/cryptobot/logs/log_ship` together with the code, because the v7 verifier checks the V7 lock.
