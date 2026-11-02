# Changes after the log-ship protocol lock (965b924c…)

## 1. 2026-10-19: false checksum mismatch found by laptop test T2, then fixed
- **What T2 found.** Every run reported 1 mismatch.
- **Cause.** The shipper's own `logs/log_ship/md5_cache.json` was inside the mirror set (`logs/log_ship`). Its MD5 was taken before the file was rewritten in the same run, so the remote copy never matched. Because of the rule "no deletion when any mismatch", nothing would ever have been freed.
- **Fix.** `md5_cache.json` (a local performance cache, not a log) and `RUNNING.lock` are excluded from the mirror set. The ledger and manifests are still mirrored: they are written after the copy step, so they go out in the next hour.

## 2. 2026-10-19: verifier default paths (found in VM test T5)
- **Problem.** With the verifier placed outside the project (`/tmp` on the VM), `Path(__file__).parents[2]` raised IndexError.
- **Fix.** The defaults are now resolved only when `--root` or `--protocol-dir` is not given. The check logic is unchanged.

## Test results
- **Laptop (rclone stub):** T1–T4 + verifier = 5/5 PASS, after change 1.
- **VM T5 (real rclone v1.60.1 from the Ubuntu repo; local-disk remote; on a COPY of the live folders, so the live files were not touched):**
  - run 1: 597 files mirrored, 8 idle `.out` files rotated to `hourly/` and freed, the 2026-10-10 test backup freed, recent backups (17–19 Oct) kept;
  - run 2: only the shipper's own 2 files copied;
  - a tampered remote data file → verifier W2 FAIL;
  - the next ship re-copied it → W1–W4 PASS.
- **T6 (real Google Drive):** pending the user's one-time rclone authorisation.
778ead9b0f11be70aca576759ebd216fcc7422c910d17a717099f48958d80c56 *deploy/ship_logs_drive.py
436da8300478c9c6bf1f9facef68b3c17f5bcc0f64a44e87d30ba3ee2be5615c *src/audits/verify_log_ship.py
0c314817edd2e35e0b77db5bca4f7c17bac3f8e24d39a4fc567cfde17ab317a2 *src/audits/test_log_ship.py
aeeb22758741302845d8c454e521324ebca11e062c95ab9f3a36f9862ac8d7a3 *src/audits/rclone_stub.py

## 3. 2026-10-19: v2 (bundle per hour) under the locked amendment `LOG_SHIP_PROTOCOL_V2_AMENDMENT.md` (071f2fe7…)
- **Why.** On the VM, real Drive took about 7 s per file (20 files in 2 min 28 s). The v1 T6 run was stopped after about 20 min with 17 files uploaded.
- **What changed.**
  - `deploy/ship_logs_drive.py` was rewritten: one tar.gz plus a manifest per hour, and a shipped index that is updated only after MD5 verification.
  - `src/audits/verify_log_ship.py` was rewritten: it downloads bundles and checks the md5 of every member.
  - `src/audits/test_log_ship.py`: tests T1–T5.
- **Laptop result (stub):** 6/6 PASS. T5 = a tampered remote bundle → W2 FAIL, as intended.
- **The v1 partial uploads stay on Drive, untouched:** 17 files under `mirror/` and 20 diagnostic files under `_diag/`.
3a711aaf0dda7ff58879b5051b180498a0811e714bad4625928e4835dcc0461f *deploy/ship_logs_drive.py
5e025275ee7ad140118172c2b6b565a9e9f43abdb90d966b0a1d2b8d06d0b33c *src/audits/verify_log_ship.py
f6b65c4c6ce706dc2ed1b50a44dabb42bb3e35f75d5f4243dc6c7e7c875082c9 *src/audits/test_log_ship.py

## 4. 2026-10-22: v3 (amendment `LOG_SHIP_PROTOCOL_V3_AMENDMENT.md`, 634f5b18…)

**`deploy/ship_logs_drive.py`.** The `MIRROR` list gains the ECO and PAPER-N1 paths and the live configs / crontab backups. Nothing else changed.

**`src/audits/verify_log_ship.py`:**
- W4 `ESSENTIAL` gains `data/eco` and `data/paper_n1` (the ledger and state of each).
- W1 also checks the V3 lock, and its message names v3.
- **Typo fixed before the first run:** a comment had swallowed the closing bracket of `ESSENTIAL`.

**`src/audits/test_log_ship.py`.** Optional 3rd argument (copies of the v3 paths) and new test T6.

**Laptop test.** Fresh copies of the VM logs and the v3 paths (2026-10-22 05:2x UTC): T1–T6 7/7 PASS. W4 is 13/13. T5 shows the expected W2/W3 FAIL on a tampered bundle.

**Open point for the ECO cut-over.** W4 lists `logs/futures_testnet_f6/state_demo.json`. The cut-over renames that file, so W4 must be updated in the same step; that is a recorded change then.

## 5. 2026-10-22: v4 (amendment `LOG_SHIP_PROTOCOL_V4_AMENDMENT.md`, e6f900d5…)

**`deploy/ship_logs_drive.py`** 63679cf1bc69…
- New `open_by_process` (reads `/proc/<pid>/fd`; `LOGSHIP_PROC_ROOT` for tests).
- F1 step 1 skips an idle `.out` that a process still holds open.
- The result manifest lists the skipped files (`out_busy`).

**`src/audits/verify_log_ship.py`** df7ec3d14fca…: W1 also checks the V4 lock.

**`src/audits/test_log_ship.py`** 9bed43c0806c…: new T7.
- A first draft had a broken string literal: a shell heredoc turned `\n` into a newline. It was fixed with an editor before the first run.

**Laptop test** (inputs: the v3 VM copies): T1–T7 8/8 PASS. T5 shows the expected W2/W3 FAIL on a tampered bundle.

**Not deployed.** VM deploy follows the user's go together with ECO amendment 2.

## 6. 2026-10-22: v5 (amendment `LOG_SHIP_PROTOCOL_V5_AMENDMENT.md`, 07a199f3…)

- `deploy/ship_logs_drive.py` **fb8da9398b95…**: MIRROR gains `logs/emotion`, the EMO ledger, the EMO-1 manifest / eligible / symbols files and the new crontab backup.
- `src/audits/verify_log_ship.py` **7d95943b5b70…**: W1 checks the V5 lock; W4 also requires `data/emotion/ledger.jsonl`.
- **Laptop test:** v3 inputs plus the emotion paths, T1–T7 8/8 PASS, W4 14/14.

## 7. 2026-10-25: v6 (amendment `LOG_SHIP_PROTOCOL_V6_AMENDMENT.md`, 7d8fd51e…)

- `deploy/ship_logs_drive.py` **8d3a4df69f50…**: MIRROR gains `data/paper_spot_s1`, `logs/paper_spot_s1` and the cut-over crontab backup.
- `src/audits/verify_log_ship.py` **5fca063c8ebe…**:
  - W1 checks the V6 lock;
  - the W4 essential F6 state is now `state_demo_retired_2026-10-25.json` (renamed at the ECO cut-over);
  - W4 also requires the eco_demo ledger + state and the eco_shadow ledger (17 files).
- **VM test**, in a /tmp mirror of the project. Inputs: copies of 10 small real log dirs (336 files) + an extra root with 63 v3/v6 files, including a stand-in paper_spot_s1 ledger.
  - **New code:** T1, T2, T3, T4, T5, T6 and T7 PASS; W4 17/17. **T4-verify FAILED** (W1 chain / W2 md5 / W3 after several ship runs inside the same UTC hour).
  - **Baseline, the OLD live code on the same inputs:** the same T4-verify W1/W2/W3 failure pattern. On top of it:
    - W4 FAIL, because the old essential `state_demo.json` no longer exists;
    - T6 FAIL, because the v6 paths are not shipped.
  - **So the T4-verify failure is pre-existing and not caused by v6.** It shows up when several bundles are made inside one UTC hour on the VM (the earlier laptop runs passed). Production makes one bundle per hour.
  - Recorded as an open item for a separate investigation.
- Deployed to the VM after the comparison.
## 8. 2026-10-25: v7 (amendment `LOG_SHIP_PROTOCOL_V7_AMENDMENT.md`, 82d04d58…, locked 05:22:32Z; a copy was put on the VM at 05:23:35Z, before any code change). Closes the open item of entry 7.

**Root cause of the entry-7 T4-verify failure.** The run tag is `HHMMSS`. On the VM a stub run takes ~0.3 s, so back-to-back test runs got the same `(hour, tag)`. The later run then overwrote, under the same names:
- the earlier run's `manifests/{hour}_{tag}.json`;
- its `.result.json`;
- its remote `hourly/{hour}/bundle_{tag}.*`.

The verifier then reported W1 (manifest SHA), W2 (md5) and W3 (not on remote, or blinded). On the laptop a run takes > 1 s, so it never showed there.
- Reproduction (old live v6 code, `/tmp/ls7`): collisions 051703×2 and 051704×2.

**Production exposure:**
- live ledger: 136 rows, 0 duplicate `(hour, tag)`;
- every run had ≥ 4 members;
- Drive runs take 55–174 s;
- cron runs once per hour, behind the lock.

So it is practically unreachable in production. The only path was two processes starting in the same second and both passing the non-atomic lock.

**Correction to a sentence in the locked amendment.** The amendment says the freed `TEST_JOB.out` chunk "then existed nowhere". The check after the run (`v7_test_evidence/chunk_provenance.txt`) shows something narrower:
- No **verified** copy remained. The verified T4 bundle 051704 was overwritten.
- The chunk survived only inside the T3 bundle 051703. That copy was unverified and stub-corrupted (an extra byte), and its md5 matches no ledger row; it is readable only because the stub appends one byte.
- In the P2 run the chunk did survive in a verified bundle, because the run that rotated it happened to be the last writer.

So the accurate statement is: "the verified copy can be overwritten". Whether the data is really lost depends on order and luck.

**Files:**
- `deploy/ship_logs_drive.py` **aca7562982946ac1…**:
  - `take_lock()`: `O_CREAT|O_EXCL`; a stale lock (> 2 h) is taken over once;
  - under the lock, the run waits 0.1 s while `{hour}_{tag}.json` / `.result.json` already exists. Cap: 100 tries, then exit 1 with nothing written.
  - Tag format and remote layout are unchanged.
- `src/audits/verify_log_ship.py` **3ab83c855387…**: W1 also fails on duplicate `(hour, tag)` (the message gives the count) and checks the V7 lock.
- `src/audits/test_log_ship.py` **46f34e681bc2…**: T8 (placeholder manifests, deterministic), T9 (4 simultaneous runs, POSIX), T8/T9-verify before the T5 tamper.
- `src/audits/rclone_stub.py` unchanged (aeeb22758741…).

**Pre-registered results.** VM `/tmp/ls7`; inputs: 10 small real log dirs, 336 files, + extra root, 68 files. Outputs are in `v7_test_evidence/`.

| Run | Code | Result | Notes |
|---|---|---|---|
| **P1** | new | **11/11 PASS** | W4 17/17, 0 collisions |
| **P2** | old ship v6 + new verifier/test | 8/11; **T8 FAIL** (pre-registered); also T4-verify FAIL, T8/T9-verify FAIL | collisions 052949×3, 052951×2, 052952×2 (`duplicate (hour, tag) 4`); T9 PASS for the old code too (expected: the race window is microseconds) |
| **P3** | new ship + **old** verifier v6 | **11/11 PASS** | the fix is in the shipper, not in the stricter verifier |
| **P4** | new, laptop (Windows, stub) | **10/10 PASS** | T9 skipped on Windows |
| Baseline | all old v6 | 7/8 | T4-verify FAIL (`old_run1.txt`), the same as entry 7 |

- **Every `T5`** shows the expected W2/W3 FAIL on the tampered bundle.
- **Note.** The first P4 attempt crashed with WinError 3: Windows MAX_PATH, because the scratchpad path is long. The rerun from a short temp path is the one reported. No code changed in between.
- **The `*_ledger_analysis.txt` files** were made after T5. The `remote_bundle_md5_ok=False` in row 1 is that tamper.

**Not deployed.** The live VM still runs v6 (8d3a4df69f50 / 5fca063c8ebe). The deploy follows the user's go, together with the V7 amendment and lock in `/opt/cryptobot/logs/log_ship`.

## 9. 2026-10-25 13:36:32 UTC: v7 deployed on the VM (record written 2026-10-28; closes the "Not deployed" line of entry 8)

The deploy was done on 2026-10-25 after the user's go ("ये तीनों काम कर दो", 13:34 UTC), but this entry was not written then. The record gap was found by CONSOL-2026-10-28 (`logs/consolidation_2026_10_28/`, item A2). This entry is written from a fresh read-only VM check (2026-10-28 08:31 UTC, `a2_evidence.py`); no code changed.

**Live files on the VM (SHA-256, mtime IST):**
- `deploy/ship_logs_drive.py` **aca7562982946ac1…**, 2026-10-25 19:06:32 IST (= 13:36:32 UTC);
- `src/audits/verify_log_ship.py` **3ab83c855387…**, same second;
- `src/audits/test_log_ship.py` **46f34e681bc2…**, same second;
- `logs/log_ship/LOG_SHIP_PROTOCOL_V7_AMENDMENT.md` 82d04d58dd9e… (lock file: "locked 2026-10-25T05:22:32Z").
- These are the SHAs of entry 8. The laptop copies are identical (laptop vs VM hash run 2026-10-28: all 177 shared files of src/ + deploy/ equal).

**Backup of v6:** `backups/logship_v6_20261025/`:
- `ship_logs_drive.py` 8d3a4df69f50…;
- `verify_log_ship.py` 5fca063c8ebe…;
- `test_log_ship.py` 9bed43c0806c…;
- `CODE_CHANGES_AFTER_LOCK.md` abbe67f54c32….
- The first two match the v6 SHAs named in entry 8. Rollback = copy these two back.

**Since the deploy (cron_status/LogShip.csv and LogShip.out, read 2026-10-28 08:31 UTC):**
- 67 hourly runs, from 2026-10-25T14:25:01Z to 2026-10-28T08:25:01Z;
- non-zero exits **0**;
- all 67 `ship …` lines say `verified True`.
- The last run before the deploy (13:25:01Z) also exited 0.
- At deploy time the real-Drive verifier gave 4/4 PASS (session record of 2026-10-25).
- **Re-run 2026-10-28, on the VM (read-only, the live verifier 3ab83c85…):**
  - `--hours 1`, 08:57–09:06 UTC:
    - W1 PASS: 212 ledger lines; chain, line hashes and manifest SHA intact; duplicate (hour, tag) 0; protocol + v2..v7 amendments == locks.
    - W2 PASS: 1 verified hour downloaded; bundle / manifest MD5 == ledger; 15 tar members md5 == manifest.
    - W3 / W4 did not finish within the 500 s timeout (W3 downloads every bundle that holds a freed file), so they are **not** re-confirmed.
  - An earlier `--hours 3` try timed out at 330 s with no output (output was buffered).
  - The hourly shipper's own `verified True` lines above cover each new bundle.

**Status:** v7 is the live log-ship version. Nothing is pending for it.
