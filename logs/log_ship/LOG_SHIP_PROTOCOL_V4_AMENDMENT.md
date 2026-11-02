# Log shipping protocol v4 amendment (2026-10-22): a .out file is rotated only when no process has it open

**Amends:** `LOG_SHIP_PROTOCOL_PREREGISTERED.md`, `LOG_SHIP_PROTOCOL_V2_AMENDMENT.md`, `LOG_SHIP_PROTOCOL_V3_AMENDMENT.md`. Everything not changed here stays the same.

**Source:** `AUDIT_ECOSYSTEM_QUALITY_COVERAGE_22_OCT_2026.md` part 3. This amendment is locked before the code change.

## Why

**The v2 rule.** F1 renames a `cron_status/*.out` file to `.out.shipping` when its mtime is ≥ 15 min old. After the bundle is verified, the file is deleted.

**The gap.** `run_job.sh` opens the `.out` with `>>` when the job **starts**. A job that is still running but has printed nothing for 15 min keeps writing through its open file descriptor into the renamed file. Two cases:
- F4 waits for 16B for up to 90 min without printing (`forward_ls_f4.py` lines 257–261).
- Step16 runs for up to 1,307 s.

That output then lands in a file that is deleted after the bundle is verified, so it is lost: it never reaches a bundle.

## v4 change

F1 step 1 renames an idle `.out` only if **no process has it open**:
- On Linux, every `/proc/<pid>/fd/*` link is compared with the file's resolved path.
- If `/proc` is absent (the laptop), the v2 behaviour stays.
- A file skipped this way is listed in the result manifest (`out_busy`) and is rotated by a later run.

## Test

New laptop test T7 (rclone stub):
- A fake process root holds a descriptor entry pointing at an idle `.out`. The `LOGSHIP_PROC_ROOT` environment variable points the shipper at that test root.
- That file is **not** rotated, and the result lists it in `out_busy`.
- After the entry is removed, the next run rotates and frees it.
- T1–T6 unchanged.
