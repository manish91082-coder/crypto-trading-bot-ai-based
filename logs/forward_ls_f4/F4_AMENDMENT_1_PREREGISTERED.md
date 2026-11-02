# F4 amendment 1 (2026-10-22): the "already logged" check reads the ledger (no paper-line change)

**Amends:** `F4_PROTOCOL_PREREGISTERED.md`.

**Source:** audit part 3 §17.2 F-1.

**Lock and approval.** Locked before the code change. The user approved it on 2026-10-22.

## Change

**Old rule.** A run used to skip when `paper/equity_<asof>.csv` existed. That file is written before the ledger line, so a crash between the two would make the second cron run skip, and the day's ledger line would never be written.

**New rule.**
- A run skips only when `ledger.csv` already has a row for that as-of.
- Otherwise it recomputes. The paper files are rebuilt deterministically from the same hashed inputs, and are overwritten.

**Unchanged:** lines, rules, data and outputs.

## Check

- A unit check of the skip decision: an equity file without a ledger row → run; a ledger row → skip.
- On the VM, the next scheduled F4 run (02:15 UTC) must log as usual. The verifier and ECO `load_f4` must read it.
