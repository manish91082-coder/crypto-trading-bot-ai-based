# Hourly log shipping from the cloud VM to Google Drive, and freeing space: pre-registered (2026-10-19)

**User request (2026-10-19):** every log the bot produces goes to a Google Drive folder every hour, and the VM is freed.

**User choices (asked and answered the same day):**
- **Route:** directly from the VM with rclone. The user authorises Google Drive once, themselves. Claude never types or sees a token or password.
- **Deletion:** the safe rule. A file is deleted from the VM only after its checksum is confirmed on Drive, and only files that no job or verifier reads again.

This protocol is locked with SHA256 before the code is written. Every change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.

## Ground facts (measured on the VM on 2026-10-19; not assumptions)
- **Disk:** 48 GB, 13 GB used (26%). The space mostly holds the static bundle (research logs ≈ 1.8 GB, data ≈ 2.8 GB) and changes little.
- **RAM:** 0.6 of 3.9 GB used. Log files do not live in RAM, so shipping logs does not free RAM. RAM is freed only when a job ends, and every job already ends.
- **What grows each day:**
  - the live-system ledgers, run records and raw files: a few MB per day;
  - the market caches `data/forward/live_1h` (646 MB) and `live_1d` (72 MB), which Step16 **rewrites** every day: about 520 MB of files modified since 2026-10-17.
- **Who reads what again (grep of `src/execution`, `src/audits`, `deploy`):**
  - `backups/<date>/` is written by M10 and read by no code. It is a same-disk safety copy.
  - `logs/cron_status/*.out` is appended to by `run_job.sh` and read by no code. M10 reads the `.csv` files, not `.out`.
  - The ledgers, `state*.json`, models, the market caches and the raw files cited by SHA in the ledgers (Step16 `rest_raw`, Step2 `depth_raw`, M4 `data/collector_m4`) **are** read again, by the next run or by the verifiers.

## What is shipped every hour (copy only; nothing on Drive is ever deleted by this job)
- **Remote root:** `gdrive:CryptoBot_1D_Cloud_VM/`.
- **Mirror set,** copied with `rclone copy` (new or changed files only) to `mirror/<same relative path>`:
  - `logs/`: `forward_ls_f4`, `forward_multi_16b`, `strategy_1d_step16_forward`, `monitor_n3_evt`, `collector_m4_options`, `cost_study_step2`, `futures_testnet_f6`, `cron_status`, `daily_status`, `log_ship`, and `forward_recorder_r2` once it is deployed;
  - `data/`: `forward/rest_raw`, `forward/depth_raw`, `forward/models`, `forward_f4`, `collector_m4`, and `forward_r2` once it is deployed;
  - `deploy/crontab.txt`.
- **Not mirrored:**
  - `data/forward/live_1h` and `live_1d`: re-downloadable market caches, rewritten daily, about 0.5 GB per day of upload;
  - the static research logs and data of the bundle: their originals are on the laptop and in the frozen E: snapshot.
- **Hour folder** `hourly/<YYYY-MM-DD_HH>/` (UTC hour of the run):
  - the rotated `.out` chunks;
  - `ship_manifest.json`, listing every file copied or rotated this hour with its size, MD5, SHA256 and remote path, plus the check results.

## What is freed on the VM (only these two; nothing else)
**F1 `.out` rotation.**
1. A `logs/cron_status/<job>.out` file whose last modification is ≥ 15 minutes old (so no job is writing to it) is renamed atomically to `<job>.out.shipping`. `run_job.sh` opens `.out` with `>>` at each job start, so a new `.out` is simply created next time.
2. It is uploaded to `hourly/<hour>/<job>.out`.
3. The remote MD5 (`rclone md5sum`) must equal the local MD5.
4. Only then is the `.shipping` file deleted. On any mismatch or error, the `.shipping` file is kept and retried next hour.

**F2 old backups.**
- `backups/<date>/` folders more than 2 days old are deleted only after every file in them is present at `mirror/backups/<date>/` with an equal MD5.
- The backups folder is therefore in the mirror set too.

**Never deleted by this job:**
- ledgers, state files, protocols and models;
- `data/forward/*`, `data/forward_f4`, `data/collector_m4`, `data/forward_r2`;
- run records, `cron_status/*.csv` and `daily_status/*`.

## Ledger and safety
- **Ship ledger** `logs/log_ship/ledger.csv`, append-only and hash-chained. Each line holds:
  - the run time and the hour;
  - files copied and bytes;
  - files checked and mismatches;
  - files freed and bytes freed;
  - rclone errors;
  - the manifest SHA;
  - prev_sha256 and line_sha256.
- **Lock file:** if another ship run is active, the run exits (stale after 2 h).
- **On any rclone error:** nothing is deleted in that run. Copies are retried next hour.
- **Keys:** the rclone config holds the Drive token (`~/.config/rclone/rclone.conf`, chmod 600). It is created by the user's own `rclone config` / `rclone authorize`, and Claude never prints it.
- **Cron:** one line, at minute 55 of every hour.
  - It is added to `deploy/crontab.txt` and the VM crontab only after the remote test (T5) passes.
  - Minute 55 avoids the job starts at :00, :02, :10, :15, :20, :28, :30, :32, :37, :40, :45 and :50 IST.

## Verifier (own code) `src/audits/verify_log_ship.py`
- **W1:** the ledger chain and line hashes; the protocol SHA equals the lock.
- **W2:** for a random sample of mirror files (default 40), the remote MD5 equals the local MD5. A file changed locally since the last ship is reported, not failed.
- **W3:** every freed `.out` chunk and every deleted backup file listed in the manifests exists on the remote with its recorded MD5.
- **W4:** no file outside the F1 and F2 rules has disappeared from the VM. Every ledger and state file the M10 status lists still exists.

## Tests
- **T1–T4 (laptop, rclone simulated by a stub with the same CLI subset):**
  - T1: a normal run;
  - T2: a second run with no changes copies nothing and frees nothing;
  - T3: an injected MD5 mismatch means nothing is freed;
  - T4: a `.out` modified less than 15 min ago is not rotated.
- **T5 (VM, real rclone, local-disk remote `/tmp/ls_t5_remote`):** the same as T1–T3 with the real binary.
- **T6 (VM, real Google Drive, after the user's authorisation):** one real run plus the verifier. Only then is the cron line added.
