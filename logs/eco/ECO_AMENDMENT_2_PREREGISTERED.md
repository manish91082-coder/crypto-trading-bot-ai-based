# ECO amendment 2 (2026-10-22): safety and accounting fixes from the audit (no strategy change)

**Amends:** `ECO_PROTOCOL_PREREGISTERED.md` (15a3c837…) and `ECO_AMENDMENT_1_PREREGISTERED.md` (0a448a79…). Everything not named here stays the same.

**Source:** the findings come from `AUDIT_ECOSYSTEM_QUALITY_COVERAGE_22_OCT_2026.md`, part 1 §2.1–2.2 and part 2 §7.1–7.12 and §8.

**Scope.** This amendment is locked before the code changes. It changes no strategy input:
- no producer, signal, weight, cap, band, fee, kill threshold, guard D or stop level changes;
- it changes only what happens on error paths, at a halt, at a delisting, and how fills, funding and files are recorded.

**Trial budget.** Untouched: still 3 of 4 used.

## 1. Kill switch completeness (part 1 §2.1, §2.2; part 2 §7.10)

**At the kill cycle:**
- Every symbol on which the ecosystem holds a position is closed. This includes symbols frozen by a reconcile mismatch or a fired guard.
- The close uses the **exchange** quantity (reduce-only).
- The 40-order limit does not apply to closing orders in that cycle.
- A residual difference between the ledger and the exchange on a frozen symbol is written to the notes.

**After the halt (halted cycles):**
- Each cycle still marks equity and records `eco_equity`, `held_net` and the exchange positions.
- If the exchange still shows a position on a symbol the ecosystem held, a reduce-only close is sent.
- No opening order is ever sent while halted.

**Reset:** a new tool `src/eco/eco_reset.py`.
- `--show` prints the state, the halt reason, frozen / guard-fired symbols and the exchange positions.
- `--reset --reason "..." --yes` sets `halted = None` and `peak = current eco equity`. Without the peak reset, the next cycle would halt again at once.
- `--unfreeze SYM` clears a guard-fired symbol.
- Each reset appends a ledger record with `mode = "reset"`.
- Only the user runs it.

## 2. Marking when a price is missing (part 2 §7.2)

- The state keeps `last_px` per perp: the last mark price seen.
- A held perp without a price this cycle is marked at `last_px`, with a note.
- The rest of the book is marked at current prices, so equity and the kill switch keep working.
- `n_px_missing` counts consecutive cycles with a fallback (an alert condition, §8).
- Attribution uses the same marking prices, so the identity still holds.

## 3. Delisting rule (part 2 §8)

**Signal.** A TRADING perp whose `exchangeInfo.deliveryDate` is before 2100-01-01 is "delisting announced". This is the field Binance sets to the settlement time; checked live on 2026-10-22 for MITO, PTB and VELODROME.

**Rule:**
- Every component target on such a perp is set to 0, so it is closed and never opened.
- A held perp that is no longer TRADING (SETTLING or absent) is marked at `last_px`, noted, and raised as an alert. Code cannot trade it.

**Logging.** The perps under this rule are written to the ledger (`delisting`).

## 4. Exchange truth (part 2 §7.3, §7.4, §7.6)

**Market orders:**
- A demo fill counts only when `status` is FILLED or PARTIALLY_FILLED, `executedQty > 0` and `avgPrice > 0`.
- Otherwise the order is queried up to 3 times, 1 s apart.
- If it is still not confirmed, the journal entry is **kept**: the next cycle recovers it by `clientOrderId`, and nothing is booked now.
- `allocate_fill` refuses a non-zero fill at a price ≤ 0.

**Stop orders:**
- `TRIGGERING` → keep, and decide in the next cycle.
- `TRIGGERED` or `FINISHED` → book `actualQty` at `actualPrice` (Query Algo Order). If `actualQty` is 0 or missing → "finished without a fill": drop the stop and book nothing.
- If `actualPrice` is 0 while `actualQty > 0`, book at the trigger price (CODE_NOTES 3) and note it.
- Other terminal statuses (CANCELED, REJECTED, EXPIRED, MISSING) → drop; the stop is re-placed if still wanted (as before).

**Orphan stops:**
- ECO stop orders carry `clientAlgoId` starting with `eco`.
- Each demo cycle lists `openAlgoOrders`:
  - an `eco…` order that is not in the state is cancelled and noted;
  - any other order is reported as foreign and left alone.

## 5. Files (part 2 §7.7)

**`state.json`:**
- Written to a temp file, `fsync`, then `os.replace`.
- The previous state is kept as `state.prev.json`.

**Corrupt files:**
- A state file that does not parse produces a failed ledger record with the error, not a silent crash. Nothing is auto-repaired.
- A ledger whose last line does not parse stops the run with an explicit error.

## 6. Funding timing (part 2 §7.5)

Plan-mode funding for the interval since the last cycle is computed on the positions held **before** this cycle's orders, which are the positions that were open during the interval.

## 7. Orders, caps, cut-over, producers (part 2 §7.8, §7.9, §7.12)

**Orders:**
- When more than 40 orders are needed, they are sent in descending |notional|.
- The orders left out are recorded as skipped with the reason `max_orders`.

**Caps:**
- Frozen-strategy components keep their quantity: the caps scale only the other components.

**Cut-over gate** adds two checks:
- ECO_Verify exit code 0 on each of the last 3 runs, on 3 different days;
- a report of the margin type of each adopted symbol. Isolated symbols are noted; the code does not change them.

**F4 producer:** a ledger line with `C1 = False` (F4 marks those numbers untrusted) freezes the 1D strategy for that cycle.

## 8. Live verifier and alerts (part 2 §7.1, §7.11)

**`verify_eco_live.py` adds:**
- **L8:** the last record is not halted; a halt is a FAIL with its reason.
- **L9:** attribution identity on every ok record that has both fields: |Σ attribution − acct_pnl| ≤ 1e-6.
- **L10:** **held** net positions within the caps (+ band), for records that have `held_net`.
- **L11:** every code SHA in the ledger (orchestrator, core, exchange) is listed in CODE_CHANGES.

It must not crash on halted or reset records.

**New `src/eco/eco_alerts.py`:**
- It is run hourly after the ECO cycle, and also once a day after the verifier.
- It checks: halt; failed cycle; no cycle for > 2 h; `n_px_missing` ≥ 2; a frozen strategy for > 2 cycles; a reconcile mismatch; a guard fired; delisting perps held; orphan or foreign stops; verifier FAIL.
- It appends each new alert to `logs/eco/alerts.jsonl`.
- It sends it to Telegram **only if** the user has set `ECO_TELEGRAM_TOKEN` and `ECO_TELEGRAM_CHAT` in `.env`. Without them, it writes the file only.

## 9. Tests

**`test_eco_core.py` keeps the 25 checks and adds A2 checks:**

| Check | What it tests |
|---|---|
| A2-1 | Kill with a frozen symbol: flat on the exchange |
| A2-2 | Kill with > 40 symbols: flat |
| A2-3 | Halted cycle: equity marked, residual position closed |
| A2-4 | Reset tool: resets halt and peak |
| A2-5 | Missing price: last_px marking, kill switch still fires |
| A2-6 | Delisting announced: closed and not reopened |
| A2-7 | Market order answered NEW / qty 0: journal kept, recovered next cycle, nothing booked at 0 |
| A2-8 | Stop statuses: TRIGGERING kept; FINISHED without fill not booked; FINISHED with actualQty booked at actualPrice |
| A2-9 | Orphan eco stop cancelled; foreign stop left |
| A2-10 | Corrupt state → failed record, no crash; atomic write keeps state.prev.json |
| A2-11 | Funding on pre-order positions |
| A2-12 | max_orders: largest first, rest recorded |
| A2-13 | Frozen components untouched by caps |
| A2-14 | F4 `C1 = False` → 1D frozen |
| A2-15 | Verifier: L8 FAIL on halt without crashing; L9 / L10 / L11 on a good ledger |

**Pass rule:** all old and new checks pass.

**VM (after the user's go):**
- deploy;
- run L1–L11 on the live ledger;
- one plan cycle with the new code;
- the alert job writes no false alert.
