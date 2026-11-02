# S1: how much of our 2021–26 performance can be selection luck? Deflated Sharpe + PBO (pre-registered)

Locked before any S1 number is computed. Code: `src/research/overfit_audit_s1.py`. Verifier: `src/audits/verify_overfit_s1.py`.
Measurement only: no trading, no model, no GitHub.

## Sources of the methods (formulas checked against the papers' own text and numbers)
- **DSR:** Bailey & López de Prado, "The Deflated Sharpe Ratio" (JPM 2014).
  - SR0 = sqrt(V[SR]) · ((1 − γ) · Z⁻¹(1 − 1/N) + γ · Z⁻¹(1 − 1/(N·e))), with γ = 0.5772156649.
  - DSR = Z( (SR − SR0) · sqrt(T − 1) / sqrt(1 − skew·SR + (kurt − 1)/4 · SR²) ).
  - SR is per observation (not annualized); kurt is RAW kurtosis (3 for Normal).
  - **Check:** our implementation reproduces the paper's own example: N = 100 → DSR 0.9004; N = 46 → 0.9505; Normal returns with N = 88 → 0.9505. This is asserted in the code.
- **PBO (CSCV):** Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (J. Computational Finance 2017), Algorithm 2.3.
  1. Matrix M (T × N) of trial P&L.
  2. S = 16 equal row blocks; all C(16, 8) = 12,870 combinations (the paper prints 12,780, a typo).
  3. For each combination: IS = the chosen blocks in their original order, OOS = the rest; the metric is the Sharpe ratio.
  4. n* = IS best; ω = OOS rank of n* / (N + 1); λ = ln(ω / (1 − ω)).
  5. PBO = share of combinations with λ ≤ 0. Probability of OOS loss = share where the OOS Sharpe of n* < 0.

## Trials (fixed rule)
- **Period:** MAIN 2021-01-01..2026-09-30. Daily equity series:
  - 4h series → the last bar of each day;
  - 1h R24 files are already daily (23:00).
- **Included:** every saved MAIN strategy equity series in `logs/strategy_1d_step*/` (Steps 6.4–28), plus the Step 27 mixes built from `sleeves_MAIN_f{100,75,50,30}.csv`. The mixes are M_AI3 = mean(D1, H4, H1), M_AI3_BTC = mean(D1, H4, H1, BTC), and the single sleeves, as in Step 27.
- **Excluded:**
  - shuffled-label CONTROL placebos (not candidates);
  - cost-stress duplicates (`*cost040*`: the same strategy at a different assumed cost);
  - exact duplicate series (identical values, e.g. UNGATED = Step 19 AI); one copy is kept.
- **Inventory:** written with each file's SHA256 to `trials_inventory.csv`.
- **N_series** = the number of included series.
- **N_extra:** MAIN-period trials that left no daily series. These count for DSR's N only:
  - Step 25 R24_HF, Step 29 R24_SRV, Step 30 breakout, Phase 2 swing AI;
  - the 9 Step 28 report-only window/band variants;
  - today's 2 descriptive long-short checks (R24, R6).
  - N_extra = 15.

## Outputs
**DSR** for two selected strategies:
- (a) **M_AI3-50 %**, the recommendation;
- (b) **R24 alone** at 100 %, the best single sleeve.

Each is computed with:
- N = N_series, N_series + N_extra, and 2 × (N_series + N_extra);
- V[SR] = the variance of the daily SR across the included series.

These are conservative: the trials are correlated, so the effective N is smaller.

**PBO** on the included series; S = 16; T is cut to the last multiple of 16 days.

## Interpretation (fixed now)
- DSR ≥ 0.95 → "significant after deflation" at 95 %. Otherwise it is reported as "not significant after deflation", with its value.
- PBO is reported as is. The paper's customary rule rejects at PBO > 0.05.
- Neither result changes the forward log or the 50 % setup by itself. Both are information for the user's real-money decision.
