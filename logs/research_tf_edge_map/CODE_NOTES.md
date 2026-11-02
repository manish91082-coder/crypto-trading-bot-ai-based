# TFX code notes (interpretations fixed BEFORE any cell result was computed, 2026-10-20)
Only a BTC smoke test (U1, 5m/4h/1D/1W trade counts and means) was looked at before these notes; no cell table, CI or reading had been computed.
1. BB sd20 = pandas rolling std (sample, ddof=1).
2. Bonferroni CI: 2,000 bootstrap draws cannot reach the 1-0.05/N quantiles, so the Bonferroni interval = mean +- z(1-0.05/N/2) x bootstrap SE.
3. 1m: bars only from G1-usable months; a 1m trade is kept only if no bar is missing between entry and exit fill (contiguity check).
4. Random-timing pool: eligible fill bars in the same period (P1/P2/P3) as the trade, with j + hold < n; U2 eligibility = liquid fill day.
5. U2 liquidity: daily perp quote volume series reindexed to every calendar day; rolling 30-day median over the 30 days before the day with >= 20 present days (same as T14 liq_ok).
6. Trades per coin-year = dev trades / dev eligible bar-time in years.
7. G1 also drops all 1m rows whose timestamp cannot be parsed (the known corrupt 2025+ raw timestamps: ~0.87-0.92M rows per coin).

## Change after run 1 (2026-10-20) — bug, not a definition change
- Run 1 wrote U1 1m and 1M trades into `data/derived/tf_edge_map/U1/1m` and `.../1M`. On Windows these are the SAME folder (case-insensitive), so the 1M files overwrote the 1m files (same coin file names) and both TFs read the 1M trades (identical rows in the cell table). Found by me while reading the cell table (1m and 1M rows identical, 1m only had a TSMOM-long cell).
- Fix: folders `1min` / `1mo` (`DIRN`). U1 trades fully re-run (same seed, same order) so the U1 random draws are deterministic; U2 trades untouched (no 1m/1M; own RNG). Run-1 outputs kept as `TFX_cells_run1_BUG_1m_1M_shared_folder.csv`, `claims_tfx_run1_BUG.json`, `run1_stdout.txt`.

## Post-hoc data-integrity finding and sensitivity (2026-10-20, after reading run-1 U2 cells)
- U2 cell means/excess had absurd values (e.g. 1D RSI long excess -83%). Cause: LUNAUSDT spot symbol was re-used for LUNA 2.0 after the May-2022 collapse: daily open / previous close = 177,399x on 2022-05-31; random-control draws spanning it give returns of +33,000%. A scan of all 135 candidates (daily open/prev close > 3x or < 1/3, |close change| > 200%) flagged LUNAUSDT (relaunch) and STRAXUSDT (2024-03-28 gap < 1/3); other big moves (DOGE, SHIB, SOL, HIFI, UNFI ...) are real market moves and stay.
- The locked U2 table is reported as computed. A clearly labelled POST-HOC sensitivity `TFX_cells_POSTHOC_excl_LUNA_STRAX.csv` (same code, those two symbols removed from trades, controls and coin-years) is added. Readings from it are post-hoc and carry less weight.

## TFX-S implementation notes (fixed before any S-result, 2026-10-20)
- S-1: trade exit time for S6 month attribution = entry_time + hold x TF duration (1M = 30.4375 days); exact except across data gaps (trade files store bar indices, not exit timestamps).
- S-2: S6 months with no exits = 0 P&L for that sleeve; denominators = eligible coins in the month (U1: coin has 5m data in the month; U2/U2X: >= 1 liquid day in the month).
- S-3: "U2X" = U2 posthoc (LUNAUSDT, STRAXUSDT removed); its Bonferroni N = the posthoc table's cell count.
- S-4: top1pct_share = sum of the top ceil(1%) net_taker trades / total net_taker sum (can exceed 1 or be negative when the total is small or negative).

## DISC implementation notes (fixed before any D-result, 2026-10-20)
- D1: day label d = [d, d+1) UTC; daily return close(d)/close(d-1); funding counted for rate times in (d, d+1]; state for day d uses the trailing-7-day mean of rates with time in (d-7, d]; switch cost 0.139% per on or off (half of 0.278%). Equal weight over coins that are ON that day; days with no coin on = 0.
- D2: Supertrend uses Wilder ATR(10) and the standard final-band recursion, first 10 bars flat; ADX/DI Wilder (alpha 1/14); Stochastic %K raw 14 smoothed SMA3; KSQZ "squeeze ended on the previous bar" implemented as squeeze true at t-1 and false at t, entry at t needs close beyond the BB band at t; Keltner ATR20 = 20-bar mean true range; VWAP20 on typical price (H+L+C)/3.
- D3: percentile = mid-rank of today's value within the trailing 365 rows incl. today (>= 180 rows); signals on day d (metrics day-aggregate known after day end) -> entry at next day's 00:00 open; hold 5 days; control pool = eligible days with j+5 < n.
- D4: rebalance every 5 bars from the first bar >= 2020-02-01; needs >= 10 eligible coins; quintile size = floor(n/5); turnover cost 0.054% x sum|w_new - w_old| (weights 1/q per leg).
- D5: months = dev months 2020-02..2025-09; cells with n_dev >= 30; SE from the joint bootstrap.
- D6: window sleeve P&L normalised by the month's eligible coin count (TFX-S S6 definition).

## DISC run-1 crash (2026-10-20) and finalize step
- D1-D6 all completed and wrote their CSV/parquet outputs; the run then crashed in main() while computing the carry-vs-trend correlation (np.corrcoef on an object-dtype Series). No D-result file was changed afterwards.
- Fix: explicit float arrays; `python src/research/disc_study.py finalize` recomputes only the claims step (carry correlations, N_eff with/without D2 families, from the saved D2 trades with the identical definitions) and writes claims_disc.json. run_d2's in-memory N_eff was never written in run 1, so it is recomputed here from the saved trades.

## verify_disc check 5 FAIL (2026-10-20) — kept as FAIL, explained post-hoc
- U1 net_taker: study p_RC 0.058 / p_SPA 0.0455 (2,000 draws, seed 20261027) vs verifier 0.036 / 0.030 (4,000 draws, seed 777): outside the pre-registered +-0.02. Excess p identical (0.004).
- Post-hoc `src/audits/diag_d5_seed_stability.py` (10 seeds x 2,000/4,000 draws): RC 0.037-0.054, SPA 0.032-0.045; T_max 3.34-3.48 (study 3.32). The studentising SE is re-estimated from each bootstrap, so a p-value at the 5% boundary moves by a few points between runs. Reading reported as "p ~ 0.03-0.06, borderline, not proven". The verifier tolerance was not loosened.
