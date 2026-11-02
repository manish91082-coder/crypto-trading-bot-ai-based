# Step 16 logger code changes after the protocol lock (every ledger line carries the code SHA256)

1. 2026-10-14 (before the first real forward run): added the Step 15 R5 brain (p_r5 column + `eligible` flag), exactly
   as the protocol allows ("brains frozen later (Step 15) are added with their own forward start date").
   Evidence of equivalence: src/audits/replay_r5_vs_step15.py 2026-09-15 -> 44/44 coins identical (max diff 5.6e-17).
   R5 forward start = the first real forward day (as-of 2026-10-13). No trading rule is logged (R5 rule failed Step 15).
2. 2026-10-14: `on_time` was computed from the run START time, the protocol says the prediction must be LOGGED before
   d+1 03:00 UTC. Fixed: `written_utc` (time the prediction file exists) is now logged and used for `on_time`.
   Consequence, stated plainly: the first real run (as-of 2026-10-13) started 02:50 UTC (PC was asleep 04:29–08:16 IST,
   the task ran on wake) and its prediction file was written ~03:13 UTC (run_log). Its ledger line says on_time=True,
   but under the protocol it is LATE -> as-of 2026-10-13 is NOT counted as forward evidence. The ledger is append-only
   and is not edited; this note is the correction.
   Fix of the cause: WakeToRun enabled on the task; Windows "Allow wake timers" (AC) is currently "Important only"
   (system setting, left to the user).

3. 2026-10-15: ledger READER fixed (found during the folder cleanup, before the next scheduled run).
   - **Cause:** change 2 added the `written_utc` field, but the append-only ledger keeps its original 19-column header. The as-of 2026-10-14 line therefore has 20 fields, and `pd.read_csv(ledger)` (used to fetch the previous line hash) raises ParserError. The next run (as-of 2026-10-15) would have FAILED.
   - **Fix:** a new `read_ledger()` maps every row by its field count (19 = old columns, 20 = `written_utc` in 2nd position). The ledger file itself is NOT edited.
   - **Evidence:**
     - the hash chain checks out (line 2 prev_sha256 = line 1 line_sha256);
     - a simulated append on a COPY of the ledger works and chains correctly.
   - **Forward status:** as-of 2026-10-14 was written at 01:06:46 UTC, on time. It is the first valid forward day.
