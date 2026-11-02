# PAPER-N1 amendment 1 (2026-10-22): robustness and funding fixes from the ecosystem audit (no signal change)

**Amends:** `PAPER_N1_PROTOCOL_PREREGISTERED.md`.

**Source:** `AUDIT_ECOSYSTEM_QUALITY_COVERAGE_22_OCT_2026.md` part 3 §17.1 (N-1 … N-4).

**Lock and approval.** Locked before the code change. The user approved it on 2026-10-22.

**Scope.** Signals, sleeves, weights, venues, fees, the safety rules and the universe are unchanged.

## Changes

1. **Missed cycles are caught up (N-1).**
   - A run finds every 4 h boundary after the state's `last_T`, up to the latest, and runs them in order with the same live public data. It caps at 12 boundaries (2 days); older gaps are noted, and only the latest 12 are run.
   - A second cron line, 15 min after the first, retries an idempotent run.
2. **D-sleeve close without a price (N-2).** It uses the position's last mark price instead of failing the whole cycle. The case is noted.
3. **Funding on the mark value (N-3).**
   - The funding paid for an event is side × rate × |units| × the position's last mark price (`last_px`, the previous cycle's open).
   - Before, it used the entry notional.
   - From this change on, forward funding numbers differ slightly from the old rule.
4. **Two-phase write (N-4).**
   - The new state is written to `state.json.pending` (fsync), then the ledger line is appended (fsync), then `os.replace` makes it the state.
   - At start:
     - a pending state whose `last_T` equals the ledger's last T is completed (roll forward);
     - otherwise it is discarded, because its ledger line was never written.

## Checks

- **Replay of 2025-06-01 … 2025-08-01**, old code vs new code on the same data:
  - identical open / close actions;
  - equity differs only through funding.
- **Unit checks:**
  - the catch-up list of boundaries;
  - pending roll-forward and discard;
  - D close without a price.
- **`verify_paper_live.py` L3** now passes when every code SHA in the ledger is listed in `logs/paper_n1/CODE_CHANGES_AFTER_LOCK.md`.
