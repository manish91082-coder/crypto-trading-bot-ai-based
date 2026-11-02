# N5: AI meta-label filter on the N1 portfolio trades (trial T18), pre-registered 2026-10-20, locked BEFORE any N1 result is known

**Parents.**
- A0 §5 / §7 AI gates (G-A … G-G).
- Lessons from A3 / T14 (an HGB meta-label failed twice), which is why a linear baseline is mandatory (research G1).
- The N1 simulator.
- The Gemini item #8 "whale ratio" feature, and #10 ensemble, as comparison only.

Research only.

**Base.** The final configuration after N3 (or N2 / N1 by the same fallback rule as N3). If N1 FAILS, N5 is a report only.

## 1. Unit, label, features
**Unit.** Every A/B/C sub-trade of the base portfolio (D is not filtered).

**Label.** y = 1 if the trade's base net return (gross − fees − funding, with the base stops and execution) > 0.

**Features** (all known at the signal bar close, i.e. the bar before entry; nothing else):
- Categoricals as integers: sleeve, TF, family, side.
- Coin TF bars:
  - returns over 1, 5 and 20 bars;
  - ATR14 / close;
  - RSI14;
  - (close − EMA20) / ATR and (close − EMA50) / ATR;
  - the Donchian-20 position (close − low20) / (high20 − low20);
  - volume z-score (20 bars).
- **Whale ratio** = the signal bar's quote_volume / trades, divided by its 20-bar mean (from the 5m `quote_volume` and `trades`).
- BTC daily (last complete day):
  - returns over 1, 7 and 30 days;
  - the R1 trend state;
  - σ20.
- Funding: the last known rate, and the 7-day mean.
- Daily futures metrics of day d − 1 (`data/futures_info`, where they exist, else missing): OI change over 1 and 7 days, top_ls_pos, global_ls, taker_ls_vol.

## 2. Models (3 configurations)
- **L.** Logistic regression (scikit-learn, C = 1.0, lbfgs, max_iter 2000). Inputs are standardised with the training window; missing values are filled with the training median, plus a missing-flag per feature.
- **H.** HistGradientBoostingClassifier with the A0 fixed hyperparameters: lr 0.05, max_iter 300, max_leaf_nodes 15, min_samples_leaf 40, l2 1.0, no early stopping, random_state 20261019.
- **E.** The mean of the L and H probabilities.

**Training.**
- Walk-forward monthly, first test month 2021-01, expanding window.
- Only trades whose exit is before the test month start (purge), plus a 1-day embargo.
- No tuning.

**Decision.**
- Take the trade if p ≥ the median p of the training window (take rate ≈ 50%). Otherwise it is skipped.
- A skipped trade frees its slot. No resizing: weights are as in the base.
- Base trades before 2021-01 (no model yet) are taken, in every configuration and control alike.

## 3. Gates (a model PASSES only if all hold; N5 PASS if at least one model passes; if several, the one with the higher dev Calmar)
- **G-A skill.**
  - The walk-forward AUC (2021-01 … 2025-09) > the 95th percentile of 20 shuffled-label runs (labels permuted within coin-month, seed 20261027 + i);
  - **and** the coin-year block-bootstrap 95% CI of AUC − 0.5 > 0.
- **G-B money per trade.** Mean net of taken − mean net of all: the coin-year block-bootstrap CI > 0.
- **G-C portfolio.**
  - Dev Calmar (2021-01 … 2025-09 decisions inside the full dev run) > base Calmar;
  - **and** > the 95th percentile of 100 random-skip portfolios with the same monthly take rate (seed 20261027 + i).
- **G-D tail.** The share of the top-decile winners that is taken ≥ the overall take rate.
- **G-E stability.** Calmar > base in P1 (2021-01 … 2023-12) and in P2.
- **G-F DSR ≥ 0.95.** N = all earlier trials + 3.
- **Report:**
  - feature importance (HGB permutation importance on the last training window);
  - the L coefficients;
  - P3 (seen).

## 4. Outputs and verifier
- **Outputs.** `logs/research_n5_ai/`: `N5_predictions.parquet` (per trade: features, label, p for L/H/E, take flags), `N5_gates.csv`, `N5_shuffled.csv`, `N5_random_skip.csv`, `claims_n5.json`, `run_log.txt`.
- **Verifier.** `src/audits/verify_n5.py`, own code:
  1. Features of 200 random trades recomputed from the raw data (PIT replay: computed from data truncated at the signal bar close must equal the stored values).
  2. A leak canary: a feature built from the trade's own net return is added on a copy; the pipeline must show AUC > 0.9.
  3. AUC and gate statistics from the prediction file.
  4. SHAs.

Any change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.
