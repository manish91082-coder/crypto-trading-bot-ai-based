# PRED-1 changes after the lock (10:49:49Z)

1. `src/audits/verify_pred1.py` (the verifier, written after the lock as the protocol foresees):
   - **Fee hurdle:** the hurdle per timeframe and horizon is computed directly, p* = 0.5 + round-trip fee / (2 · mean |log move| of that timeframe and horizon), with the round-trip spot fee 2 × 0.085% from deploy/fees.json. The fee-hurdle map has values only for 1h and 1d; this is the same definition for every timeframe.
   - **Direction for M0:** a forecast equal to the base close within 1e-9 counts as "no direction", so M0 has none, as intended.
2. `predict.py` (the forecaster) is unchanged since the lock (sha in PRED1_PROTOCOL_SHA256.txt).
3. **Late forecasts** (found by verifier V1, 2026-10-29 ~17:05Z).
   - **What happened:** 54 forecasts (52 on 1m, 2 on 5m) were written 2–135 s after their first target bar had already closed. Network read timeouts plus a sequential loop over 5 symbols delayed the later symbols.
   - **Not a leak:** their inputs were only bars up to the base bar (the loop fixes `last_closed_open` before fetching, and V2 recomputes them exactly), so nothing from the future went in.
   - **Still not allowed:** by the protocol a forecast must exist before its target closes.
   - **Verifier:** target horizons that had closed before the forecast time are not scored; the count is reported.
   - **predict.py:** a forecast that would be written after its next bar closed is now skipped and logged ("SKIP"). The process that has been running since 10:50Z keeps the locked code (stopping it was not done, so the forecast stream does not get a gap). Scoring correctness does not depend on the guard: the verifier rule above excludes every late horizon, whatever the code.

4. **Restart after power loss, 2026-10-30.**
   - **Gap:** the forecaster stopped at about 08:02Z and restarted at 08:39Z. No forecasts exist for that gap.
   - **Log state:** the hash chain of predictions.jsonl was intact at 4,682 forecasts.
   - **Code:** the restarted process runs the current predict.py (sha f34bb9ea…), so the "late forecast" skip from change 3 is now active. The locked sha was 90c28d89…; the forecast formulas are unchanged.

5. **Second power loss, 2026-10-30 08:53Z; restart 2026-11-02 ~02:33Z.**
   - **Gap:** no forecasts exist for about 2 days 17.7 hours.
   - **Damage:** predictions.jsonl ended in 11,471 NUL bytes, so the last few forecasts were lost. The 4,784 lines before them are intact and the hash chain holds.
   - **Repair:** `src/live_paper/recover.py` cut only the NUL tail. The damaged file is kept as predictions.jsonl.corrupt_NUL_2026-11-02.
