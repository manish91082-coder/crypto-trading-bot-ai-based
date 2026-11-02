# A4 (rule-only): exits, entry and sizing for S-LAD long (sub-protocol of A0 `4d49d411…` + amendments 1, 2), pre-registered 2026-10-19

**Context.** A3 (T05) FAILED, so there is no AI sleeve. The user chose on 2026-10-19 to continue WITHOUT AI on the strongest A1 signal: S-LAD long (corrected: +0.128 R, CI 0.064–0.192). This protocol is locked before any A4 number is computed.

**Trials (A0 §9 allocation, registered before the run):**
- T06–T11: the 6 exit configs;
- T12: V2 test entry;
- T13: maker entry.

After A4: 13 of 20 trials used.

## Signals and data
- **Signals:** S-LAD long from the REAL-TIME pivot timeline (`r2_realtime_pivots.swing_signals`), 10 coins, entry 2020-02-01 … 2026-09-30.
- **Trade set:** the same for every config, namely the signals with ≥ 60 bars of 4h data after entry and with perp available (as in `a1c_trades`).
- **Bars:** `probe_scalein.bars(coin, "4h")`, and 5m bars from `data/universe_hf/5m` for the maker fill model.
- **Costs:** fee 0.054% per side (base); real funding over the holding interval (the audit's B1 routine); sensitivities at 1.5× and 2× fees, and a stop-slippage stress where every stop fill is 0.3% worse.
- **Periods:** dev = P1 (2020-02 … 2023-12) + P2 (2024-01 … 2025-09); P3 (2025-10 … 2026-09) is reported only.

## Exit grid (T06–T11)
- trailing stop k ∈ {3, 4} ATR (best high of the earlier bars − k × ATR, never below the initial stop);
- time stop ∈ {60 bars, 120 bars, "none" = 1,000-bar cap};
- initial stop = pivot − 0.5 ATR, as in S6.
- A trade with fewer bars left than its cap is closed at the close of the last available bar, and this is marked.
- The default is (3 ATR, 60).

## Entry variants (on the selected exit)
- **T12 V2 (test entry):** 0.25 at entry, +0.25 at +1 ATR, +0.5 at +2 ATR, with the S6 fill rules.
- **T13 maker entry (A0 §10):**
  - a post-only buy limit at the 4h open, valid for 12 five-minute bars;
  - filled if a later 5m low < the limit;
  - fee 0.018% (0.02% maker × 0.9 BNB, no spread);
  - if not filled, a taker buy at the close of the 12th 5m bar with fee 0.054%;
  - the stop level is unchanged and R = entry fill − stop.
  - Reported: the fill rate and the mean net R of filled vs unfilled trades (adverse selection).

## Portfolio (the A0 §6 simulator, S-LAD long only)
- 8,000 USDT; f = 0.5%; K = 6; one position per coin; ≤ 3× notional; minimum notional;
- notional = f·E / (R/entry + 0.01 + 0.0009);
- **mark-to-market DD** at each 4h bar's low; Calmar = CAGR / MTM-DD.

## Pre-registered selection and gates
1. **Exit selection (plateau rule).**
   - Pick the exit config with the highest dev MTM-Calmar, but only if every grid neighbour (the same k with the adjacent time stop, and the same time stop with the other k) has a dev Calmar ≥ 80% of it.
   - Otherwise keep the default (3, 60).
2. **Entry variants.** V2 or maker is adopted only if its dev Calmar AND its Calmar in P1 AND in P2 all exceed the selected exit's. Otherwise, V0 taker.
3. **Gates for "A4 rule sleeve provisional PASS"** (final config):
   - **PBO < 0.30.** CSCV, 16 time blocks of the dev monthly returns, over the 6 exit configs. Logit of the OOS rank of the IS-best config < 0 counts as overfit.
   - **Beats random entry.** Dev MTM-Calmar > the 95th percentile of 100 random-entry portfolios. Each one has the same number of long entries per coin and calendar year at uniformly drawn 4h bars (seed 20261019 + i), initial stop = entry − 2 × ATR_14 of the previous bar, and the same exit config.
   - **Cost.** Mean net R per trade > 0 at 1.5× and at 2× fees, and with the 0.3% stop-slippage stress.
   - **Stability.** MTM-Calmar > 0 in P1 and in P2.
   - **DSR ≥ 0.95.** Monthly dev returns; N = 13 trials; the SR variance is that of the 6 exit configs' monthly Sharpe ratios.
   - **Deferred to A5** (as in A3): G-I (2018–19 out-of-time, once, on the frozen config) and the 1D-correlation check.
4. **Sizing table (information, not a selection).** For the final config: f ∈ {0.25, 0.5, 0.75, 1.0}%, giving CAGR, MTM-DD and Calmar. The risk level is the user's decision.

## Outputs
`logs/r2_4h_a4/`: `A4_exit_grid.csv`, `A4_entry_variants.csv`, `A4_maker_fills.csv`, `A4_random_entry.csv`, `A4_pbo.json`, `A4_sizing.csv`, `claims_a4.json`, trades parquet.

## Verifier (own code) `src/audits/verify_r2_a4.py`
1. Re-simulates 200 random trades of 3 configs with its own loop: gross R, exit index, fee and funding to 1e-9.
2. Recomputes the exit grid's mean R and the plateau selection from the trades.
3. Recomputes PBO from the monthly-return matrix with its own CSCV code.
4. Re-implements the MTM portfolio for the final config; final equity and DD to 1e-6.
5. Checks the claims and SHAs.
