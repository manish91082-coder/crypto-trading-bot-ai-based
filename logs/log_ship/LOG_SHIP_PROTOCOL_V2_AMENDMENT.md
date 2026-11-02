# Log shipping protocol v2 amendment (2026-10-19): hourly bundle instead of file-by-file

This amends `LOG_SHIP_PROTOCOL_PREREGISTERED.md` (`965b924c…`). Everything not changed here stays the same: the user's choices, the mirror source set, the F1 and F2 freeing rules, "never delete on Drive", the lock and the hash-chained ledger. The amendment is locked with SHA256 before the v2 code is written.

## Why (measured on the VM, 2026-10-19, real Google Drive)
- **Speed.** The first real ship (T6, v1 design, `rclone copy --files-from`) uploaded only 17 files in about 20 minutes.
- **Diagnostic.** A run on 20 small recorder files took 2 min 28 s, about 7 s per file, using rclone's built-in shared Google client: `rclone copy -v`, 20/20 transferred, rc = 0.
- **File volume.** The recorder alone writes about 470 files per run, 6 runs a day (about 2,800 files a day). The bootstrap backlog is about 3,400 files.
- **Conclusion.** The per-file design cannot keep up hourly, so it is replaced.
- **The partial v1 uploads stay as they are on Drive:** 17 files under `mirror/` and 20 diagnostic files under `_diag/`. Nothing is deleted on Drive.

## v2 design
1. **Shipped index.** `logs/log_ship/shipped_index.json` holds {relative path: md5} of every file confirmed on Drive. It is updated **only after** the hour's bundle is verified. It is not in the mirror set.
2. **To ship** = every file of the mirror set whose current md5 differs from the shipped index (new or changed), plus the F1 `.out` chunks (renamed to `.shipping` under the same idle rule: ≥ 15 min since the last write).
3. **Bundle.**
   - One `bundle_<HHMMSS>.tar.gz` holds all to-ship files, with their relative paths as member names.
   - A `bundle_<HHMMSS>_manifest.json` lists every member's path, size, md5, sha256 and kind (`mirror` / `rotated_out`).
   - Both are uploaded with `rclone copyto` to `hourly/<YYYY-MM-DD_HH>/`.
4. **Verification.** `rclone lsjson --hash` on that hour folder must show both files with MD5 equal to the local MD5. Only then:
   - the index is updated;
   - the `.shipping` chunks are deleted (F1);
   - `backups/<date>` folders older than 2 days are deleted when every file in them is in the shipped index with an equal md5 (F2).
5. **On any rclone error or mismatch:** the index is not updated and nothing is deleted. The `.shipping` chunks are kept and go into the next hour's bundle.
6. **Ledger line** fields:
   - hour; n_files_in_bundle; bundle_bytes; bundle_md5; manifest_md5;
   - verified (True/False);
   - n_rotated; n_backup_files_freed; bytes_freed; n_rclone_errors;
   - manifest_sha256 (the local manifest copy in `logs/log_ship/manifests/`);
   - prev_sha256; line_sha256.

## Verifier v2 (`src/audits/verify_log_ship.py`, own code)
- **W1:** the ledger chain and line hashes; each local manifest SHA equals its ledger line; the protocol and amendment SHAs equal their locks.
- **W2:** for up to 3 random verified hours, the bundle and manifest are downloaded from Drive. The bundle MD5 must equal the ledger, and every tar member's md5 must equal the manifest. A member whose local file still exists with a different md5 is reported (changed since), not failed.
- **W3:** every freed file (rotated `.out` and deleted backup files) appears in a verified bundle manifest with its md5, and that bundle exists on Drive with the ledger MD5.
- **W4:** the essential live files still exist on the VM (unchanged from v1).

## Tests
- **Laptop (rclone stub):**
  - T1: first run, everything bundled and verified;
  - T2: second run, only the shipper's own changed files;
  - T3: injected remote corruption → nothing freed, index unchanged, `.shipping` kept;
  - T4: the next run recovers; a `.out` modified < 15 min ago is not rotated;
  - T5: a tampered remote bundle → verifier W2 FAIL.
- **VM (real Drive):** T6 = one real run + the verifier W1–W4. Only then is the cron line added.
