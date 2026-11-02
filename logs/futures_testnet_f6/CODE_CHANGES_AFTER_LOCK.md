# F6: changes after the protocol lock (all before any testnet order; no run exists)

## 1. 2026-10-16: stop-sync safety fix (audit finding)
- **Before:** if a sleeve short's stop algo order was no longer open, the code assumed the stop had fired and removed the short from its state, whatever the status. A CANCELED or EXPIRED stop would have left a real (testnet) short open WITHOUT protection and outside the state.
- **Now:**
  - The short is removed only if `GET /fapi/v1/algoOrder` says TRIGGERED or FINISHED.
  - In every other case (CANCELED / EXPIRED / not found / never placed) a new STOP_MARKET reduce-only algo order is placed at fill × 1.50 and logged (`stop_replaced`).
  - A failed stop at entry is logged as "STOP NOT PLACED"; the next run re-places it.
- **Source of the status values:** the official Binance USDⓈ-M SDK (`@binance/derivatives-trading-usds-futures` 36.0.0): active, CANCELED, EXPIRED, TRIGGERED, FINISHED.
- **Unchanged:** the protocol rules (stop ×1.50, limits, K1, hosts).

## 2. 2026-10-16: `.asof` bug fix + plan-mode pre-flight
- **Bug:** `load_decision()` used `r.asof` on a pandas Series, which is the Series METHOD `asof`. Fixed to `r["asof"]`.
- **Plan mode (no keys, no orders):** run on the F4 sandbox decision of 2026-10-14. It listed 15 planned shorts with tick-rounded stops at ×1.50 on the testnet exchange filters.
- **Testnet / demo prices (checked 2026-10-16):** they track mainnet within ~0.03 % (BTC, DOGE, BCH, SUI, BNB). Testnet order-book liquidity is not the real one, so the fill-vs-paper bps measured on testnet is indicative only.

## 3. 2026-10-16: exchange-side 30-day cooldown after a stop fires (mock-exchange test finding; still no testnet order)
- **Found by** `src/audits/test_f6_mock_exchange.py` M3: after a stop TRIGGERED on the exchange, the same F4 decision
  (which still lists the coin, because the paper's own stop is computed on mainnet bars and need not fire at the same
  moment) made F6 re-open the short in the same or the next run. That breaks the F7 rule "30-day cooldown after a stop".
- **Fix:** when sync sees TRIGGERED / FINISHED, the (sleeve, symbol) gets a cooldown date in the state; opening it again
  is skipped for 30 days with the logged reason "cooldown: exchange stop fired <date> (F7 30-day rule)".
- **Effect:** the exchange book can hold fewer shorts than the paper book after a testnet-only stop. O3 reconciles the
  exchange against the STATE, so it is unaffected; the difference is visible in the run record.
- **Mock test after the fix:** 15/15 PASS (logs/e2e_integration/f6_mock_results.json): open + stop at x1.5, idempotent
  re-run, TRIGGERED -> removed + cooldown, CANCELED -> stop re-placed, drill kill (O4), K1 + HALT refusal, hedge-mode
  refusal, rejected order, host guard.
- **Operational note for the user:** K1 / drill close EVERY position on the account (protocol rule 8). Use a futures
  testnet account dedicated to F6.
- Code SHA after change 3: 67c61990ecdd2294ce0b4494f388c21839c4a1bd2079835b5618dbc761f5cd2b  src/execution/futures_testnet_f6.py

## 4. 2026-10-16: first contact with the DEMO exchange (technical ops drill, not the official O1-O4 record)
- Keys: set by the user as environment variables (BINANCE_FUT_DEMO_KEY / _SECRET, 64 characters each); read by the
  code from the user environment, never printed or stored by Claude.
- Account before: one-way mode, 5,000 USDT, no positions, no algo orders (src/audits/f6_demo_account_check.py, GET only).
- Real F4 decision of 2026-10-15 (PAPER_START) is empty -> plan run 0 actions (as expected).
- Drill (src/audits/f6_demo_ops_drill.py, records in logs/futures_testnet_f6/ops_drill_2026-10-16/, decision = F4
  preflight sandbox 2026-10-14 = technical test data):
  - run 1: 15 shorts opened, each with one STOP_MARKET algo at fill x 1.5 -> O1, O2, O3 PASS
  - run 2 (same decision): 0 actions -> O1..O3 PASS (idempotent on the real exchange)
  - drill-kill: 22 actions -> O4 PASS (zero positions, zero open algo orders); account after: 4,996.71 USDT
    (about 3.3 USDT fees + slippage on ~1,500 USDT notional opened and closed)
- Finding: 4 notes "-4067 Position side cannot be changed if there exists open orders" on /fapi/v1/marginType when a
  second sleeve opened a symbol another sleeve already held. Re-read from the exchange: all 11 symbols ISOLATED,
  leverage 1 -> harmless. Verifier O5 added (every held symbol ISOLATED + leverage 1, via /fapi/v1/symbolConfig);
  mock exchange extended with symbolConfig; mock test 15/15 PASS.
- Verifier SHA: fc52838a7ce99e576f8bcbcf2b728bd931884bbe8048acac609d74297628a98a  src/audits/verify_f6_testnet.py
- The official O1-O4 record starts with the first real F4 decision (as-of 2026-10-16, written ~08:30 IST 17 Oct).
