# F4: changes after the protocol lock

## 1. Daily pending-orders file (2026-10-15 ~16:00 UTC, BEFORE the first scheduled run; no forward result exists)
- **Why:** the F6 testnet executor needs the decision taken at the close of each as-of day, i.e. what to open / close at the next open. The paper equity and positions files only show the book up to the close.
- **Engine change (`f7_risk.py`):**
  - `sim_ls` now also RETURNS `pending`. It holds the last bar's decision lists (sell / buy / cover / short), the open book before the end-of-test close (long units; short units, entry, stop) and the cooldown map.
  - No computation changed. Re-check: the F7 RS D1 sleeve re-run gives $103,663.98 and 66 stops, equal to `strategy_f7_risk/claims.json`.
- **Logger change (`forward_ls_f4.py`):** writes `paper/orders_{asof}.json` (per line and sleeve: pending + close equity) and records `orders_sha256` in the ledger line.
- **Verifier change:** V1 also checks the orders-file hash.
- **Gates, lines, rules and schedule are unchanged.**

## 2. 2026-10-16 ~00:20 IST: BUG FIX before the first scheduled run (found by the audit's sandbox pre-flight)
- **Bug:** `L16.asof == ...` in `main()`. `.asof` is the pandas DataFrame METHOD `asof`, not the column. The comparison was always False, so the first scheduled run (as-of 2026-10-15, 08:30 IST) would have FAILED with "16B has not logged …".
- **Fix:** `L16["asof"]`. The same bug in `verify_f4_forward.py` (`L.asof.iloc[-1]`) and in `futures_testnet_f6.py` (`r.asof` on a Series) is fixed the same way.
- **Also added:** `main(asof=None)`. The optional argument is used ONLY by the sandbox pre-flight (`src/audits/preflight_f4.py`); the scheduled run passes nothing.
- **Pre-flight evidence:**
  - Two sandbox days (as-of 2026-10-13 / 10-14; temp folder, live data, 16B test signals, day 1 shifted) ran without error.
  - Chain OK; C1 True on both days (LO = 16B paper); orders file written.
  - `verify_f4_forward.py` on the sandbox: V1–V5 PASS.
- **Unchanged:** nothing in `logs/forward_ls_f4` was written by the pre-flight, and no gate, line or rule changed.

## 3. 2026-10-16: wait for 16B; verifier handles an empty positions file
- **What happened:** the first scheduled run (10:20 IST, after a late wake) failed with "16B ledger missing", because 16B itself had failed (see 16B CODE_CHANGES 4–5).
- **Recovery:** both were re-run by hand at about 12:08 IST. The as-of 2026-10-15 line is LATE (`on_time=False`), C1 True. `verify_f4_forward.py`: V1–V5 PASS.
- **Fix:** `main()` now checks every 60 s, for up to 90 minutes, for the 16B ledger line of the as-of day.
- **Verifier:** V5 reads the PAPER_START positions file, which is empty because nothing is filled yet, as an empty table instead of crashing.
