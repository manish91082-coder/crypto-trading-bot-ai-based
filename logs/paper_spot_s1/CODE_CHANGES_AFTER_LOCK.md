# PAPER-SPOT-S1: code written after the protocol lock (a74553bfa318…, 2026-10-25 04:42:59 UTC)

## Code
- 46f07e9ba14e…  paper_spot_s1.py
- a30a5c389581…  verify_paper_spot_s1.py

## Notes, decided before the first real run
1. **The ledger is the source of truth.** The state (cash, qty, benchmark units, last D) is rebuilt from the last ledger line on every run. `state.json` only mirrors it, as the protocol names it.
   - **Why:** a crash between the ledger append and the state write would otherwise repeat a day.
   - `bench_units` is stored in every line, so the replay is exact.
2. **Sandbox pre-flight on the VM (2026-10-25 ~04:50 UTC).** A temporary copy with D0 = 2026-10-10 and output to /tmp/s1test.
   - **Catch-up:** 15 days (10–24 Oct) were processed in one run.
   - **Verifier:**
     - S2, S3, S4 and S5 (fresh fetch) PASS;
     - S1 FAILED as it should: the temp copy's code SHA is not listed, and the harness's attempt to list it did nothing because this file did not exist yet. That failure shows the S1 check works.
   - **Idempotency:** a second run left the ledger byte-unchanged; so did a run with `state.json` deleted.
   - **Rebuild:** after the last 3 lines were deleted, catch-up rebuilt them and the chain and S2–S4 PASS again.
   - The temp copies were deleted. The /tmp output is not part of the record.
   - **Reading from the pre-flight (information only):** on 2026-10-24 BTC closed at 80,888.16 against an SMA200 of 72,942.35, so the signal was "in". The first real decision (D0 = 2026-10-25) will therefore most likely buy at the 2026-10-26 open.
3. **Crontab** `deploy/crontab_spots1.txt` b04c384dd3c0…: the current crontab plus 3 job lines (06:15 IST, retry 08:15 IST, verifier 08:40 IST with `--fresh`).
## 4. 2026-10-25: fee unification (logs/fees/FEE_AMENDMENT_PREREGISTERED.md (2d9d1485…)), before the first real record

- `src/execution/paper_spot_s1.py` **658adb92c9d5…**: FEE 0.001 → **0.00085** (BNB 0.075% + impact 0.010%), asserted against `deploy/fees.json`.
- `src/audits/verify_paper_spot_s1.py` **16b6d7a24a69…**: S3 reads the fee from `deploy/fees.json`.
- The ledger has no records yet (first decision D0 = 2026-10-25, run 2026-10-26 00:45 UTC), so every record uses 0.085%.