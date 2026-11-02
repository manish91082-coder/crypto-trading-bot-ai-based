# ECO E-3 (replay) and E-4 (failure tests): results, 2026-10-22

**Source of truth.**
- `logs/eco/verify_eco_stdout.txt`: verifier output, 7 checks, 1 FAIL.
- `src/audits/test_eco_core.py`: 17/17 PASS.
- Replay ledgers `data/derived/eco/replay/run1|run2/ledger.jsonl`: identical, SHA `4f1e542f…`.

## E-3 replay (2026-09-01 … 09-30, 719 hourly cycles, simulated fills; a plumbing and tracking test, not a performance claim)

**Producer inputs** were built with the deployed producer code:
- F4 `build_lines`, once per as-of day. Its 09-30 LS_RS mix is 9,041.49, which equals the earlier F4 `--test` summary (9,041.49).
- The PAPER-N1 replay engine. The N1 book rebuilt from its actions equals the engine's final `state.json`: 219/219 keys and sides, units within 2.6e-8 relative (the actions round notionals to 6 decimals).

| Gate | Result |
|---|---|
| V3 targets (200 random cycles, independent code) | PASS: 0 mismatches |
| R1 attribution identity | PASS: max \|Σ components − simulated account\| = 8.35e-10 USDT |
| R3 caps | PASS: 0 violations |
| R4 stops | PASS: 9/9 F4 stops; the executor component closed in or before the same F4 bar |
| R5 order minimums | PASS: 0 violations |
| R6 determinism | PASS: two replays give identical ledger hashes |
| **R2 tracking ≤ 1.0% of E0** | **FAIL: 1.20%.** End of September: eco 9,817.25 vs paper combination 9,697.27 |

### Post-hoc decomposition of the R2 gap (computed after the FAIL; `src/audits/posthoc_eco_r2_1d_costs.py`)

**Attribution at the end of the window (account USDT, k = 1).**

| Part | Eco executor | Paper target (a × E0 × paper return) | Difference |
|---|---|---|---|
| N1 | +196.10 | +197.17 | **1.07 USDT (0.01%)**. The executor follows N1 almost exactly. |
| 1D | −378.85 | −504.29 | **125.44 USDT.** The whole gap is here. |

**1D, decomposed** with the same F4 engine on as-of 2026-09-30 (eco units = 0.5261 × 10,000 × return):

| Run | 1D return | Eco units |
|---|---|---|
| Deployed F4 cost model (long fill 0.25%, short fill 0.10%, stop slippage 1%) | −9.585% | −504.3 |
| Perp taker 0.054% on both sides | −9.196% | −483.8, i.e. **+20.5 from fees** |
| … and no stop slippage | −8.808% | −463.4, i.e. **+20.4 from stop slippage** |
| **Not explained by costs** | | **≈ 84.6 USDT** |

The unexplained part comes from execution timing:
- The executor fills at h+1 after F4 is written (≈ 03:00 UTC), while the paper fills at 00:00 UTC.
- An executor stop fills at the next hourly open, not at stop × 1.01.

In this month the timing helped the executor. In another month it can hurt. It is a real implementation difference, not an accounting error: R1 holds to 1e-9.

**Status.**
- E-3 is not fully passed. **R2 FAIL stays recorded. The gate is not changed after the fact.**
- Consequence: no demo orders (E-6) until the user decides. The two options are:
  - (a) accept a per-strategy tracking reading. N1 is 0.01%, and 1D is 2.4% of its own allocation, of which 0.8 pp is the paper cost model.
  - (b) a new pre-registered tracking test on forward data.
- E-5 (plan mode on the VM: no orders, no keys used for trading) measures exactly this tracking on live data, so it proceeds.

## E-4 failure tests: 17/17 PASS

- U1–U9: netting, attribution identity, band, internal transfer without an order, signed funding split, caps, stop suppression and release.
- T1: a crash after a fill is recovered from the write-ahead journal; no duplicate order.
- T2: a concurrent run is refused by the lock.
- T3: a stale producer is frozen.
- T4: a tampered F4 orders file or N1 ledger line causes a freeze.
- T5: HTTP 400 on one symbol; the others proceed.
- T6: a manual position change freezes only that symbol.
- T7: the kill switch flattens the book, then sends nothing.
- T8: the real public demo endpoint lists 528 TRADING USDT perps; mainnet lists 524.
  - **Finding:** the demo filters differ from mainnet on several target symbols (step, min notional, max qty). Example: LINK / LTC min notional is 5 on demo and 20 on mainnet; BTC step is 0.0001 on demo and 0.001 on mainnet.
  - Demo mode therefore takes its filters from the demo host, which is what `LiveEnv` does.
