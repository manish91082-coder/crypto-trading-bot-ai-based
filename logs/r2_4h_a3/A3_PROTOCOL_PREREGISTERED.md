# A3: B2-fast 4h meta-label brain (sub-protocol of A0 `4d49d411…` + amendments 1 `b89f0a82…`, 2 `1b49a9de…`), pre-registered 2026-10-19

This protocol is locked before any model is fitted. It is **trial T05** in `logs/r2_4h_a0/trial_registry.csv`, registered before the run. It narrows A0 §5–§7 and does not widen them.

## Data
- **Rows:** `data/derived/r2_a2/feature_store.parquet` (A2, verifier PASS) with perp_ok = True (9,655 rows).
- **Joined from** `logs/r2_4h_a1/correction/a1c_trades.parquet`: exit_idx, net_x1_5, net_x2, R_price, entry_px, atr.
- **Features:** exactly `data/derived/r2_a2/feature_list.json` (36). `signal_type` is categorical.
- **Label:** net_base > 0.
- **Exit time** of a row = entry_time + (exit_idx + 1) × 4h.

## Walk-forward (A0 §5)
- **Test months:**
  - **development:** 2021-01 … 2025-09 (P1 = 2021-01 … 2023-12, P2 = 2024-01 … 2025-09);
  - **P3:** 2025-10 … 2026-09, reported only.
- **Training set for month M:** rows with entry ≥ 2020-02-01 and exit time < M_start − 1 day (purge + 1-day embargo). A month is skipped if the training set has fewer than 300 rows.
- **Model:** sklearn `HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0, early_stopping=False, random_state=20261019, categorical_features=[signal_type])`.
  - It is fitted on the earliest 80% of the training rows (by entry_time).
  - Isotonic calibration (`out_of_bounds="clip"`) is fitted on the model's probabilities for the latest 20%.
- **Decision rule (A0 §5):**
  - take if p ≥ thr, where thr = the median calibrated p on that calibration slice;
  - size multiplier m = clip((p − 0.5) / 0.1, 0.5, 1.5).

## Portfolio simulator (A0 §6)
- **Settings:**
  - 8,000 USDT; f = 0.5% × m of realised equity;
  - K = 6; one open position per coin; a new trade opposite to an open position on the same coin is skipped;
  - total notional ≤ 3 × equity;
  - minimum notional: BTC 50 with qty ≥ 0.001, ETH 20, LINK 20, others 5;
  - notional = f·m·E / (R_price/entry_px + 0.01 + 0.0009);
  - P&L = N × net_base × R_price/entry_px;
  - order: entry_time, then signal_type, then coin.
- **Mark-to-market drawdown.**
  - At every 4h bar close, equity = realised + Σ over open trades of the unrealised P&L at that bar's ADVERSE extreme: low for longs, high for shorts. Bars come from `probe_scalein.bars` 4h.
  - Max DD is taken on this curve; the realised DD is also reported.
- **Window:** gates use dev only. P3 is reported.

## Gates (all must hold for "A3 provisional PASS")
| Id | Condition |
|---|---|
| G-A skill | Pooled dev walk-forward AUC > the 95th percentile of 20 shuffled-label runs (training labels permuted within coin × month, seeds 20261019 + s; test labels real) **and** the 95% bootstrap CI (coin-year blocks, 2,000, seed 20261019) of AUC − 0.5 lies above 0 |
| G-B money per trade | Mean net_base of taken − mean net_base of all dev signals: bootstrap CI (same blocks) > 0. **Also** the same at net_x1_5 |
| G-C portfolio | AI (A0 rule with m) MTM-Calmar > the take-all baseline (m = 1) MTM-Calmar, **and** > the 95th percentile of 100 random-skip portfolios. Random skip = the same number of signals per calendar month as the AI took, chosen uniformly (seed 20261019 + i), each assigned a random permutation of that month's AI m values |
| G-D tail | Among the top decile of dev rows by net_base, the share the AI took ≥ the AI's overall take rate |
| G-E stability | In P1 and in P2 separately: mean net_base of taken > 0, **and** AI MTM-Calmar > baseline MTM-Calmar |
| G-G cost | Mean net of taken > 0 at net_x1_5 **and** at net_x2 |
| G-H diversification | Correlation of monthly returns of the AI portfolio vs the 1D system ≤ 0.70, **or** the 50/50 monthly-rebalanced combination's Calmar > the better of the two. 1D system = mean of the D1, H4 and H1 equity columns of `logs/strategy_1d_step27_combine/sleeves_MAIN_f50.csv` (each normalised to 1 at 2021-01-01), the 50% exposure that the live paper engine uses |
| DSR | Deflated Sharpe ≥ 0.95, using the AI portfolio's monthly returns (dev). N trials = 5 (T01–T05). The SR variance across trials is estimated by the variance of the 20 shuffled-control portfolios' monthly Sharpe ratios. Skewness and kurtosis come from the AI's monthly returns (Bailey & López de Prado) |

**Deferred to A5** (pre-registered here, not skipped):
- **PBO:** fewer than 4 A3/A4 configurations exist yet, so it is "not computable" now and is never a pass.
- **G-I (2018–19 out-of-time check):** done once on the final frozen configuration, so as not to spend the 2018–19 data twice.

**Verdict.**
- **"A3 provisional PASS"** if all gates above hold.
- Otherwise **"A3 FAIL"**: no AI sleeve, a report, and the user decides.
- A provisional PASS is never a deployment decision.

## Outputs
`logs/r2_4h_a3/`:
- `oos_predictions.parquet` (row id, month, p, take, m);
- `A3_gates.csv`, `A3_portfolio.csv` (AI, baseline, random-skip summary);
- `shuffled_auc.csv`, `claims_a3.json`, `run_log.txt`, `verify_log.txt`.

## Verifier (own code) `src/audits/verify_r2_a3.py`
1. Re-fits 6 random test months with its own code; p must equal the study to 1e-9.
2. Recomputes AUC, G-B and G-D from the OOS file.
3. Re-implements the MTM portfolio for the AI and the baseline; final equity and MTM DD must match to 1e-6.
4. Checks the claims, gate flags and SHAs.
