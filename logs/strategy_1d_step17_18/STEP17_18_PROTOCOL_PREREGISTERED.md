# STEP 17 + 18 PROTOCOL — "when to stay out" (market brain) + "where NOT to trade" (veto brain) (pre-registered)

Written and SHA256-locked before any Step 17/18 model is trained. Code: `src/pipeline_1d/step17_18_market_veto_1d.py`.
Spot, 1D, long-only, $10,000, free data only. No GitHub action. Nothing is deployed by this step.

## Why (evidence from Step 15)
R5 picks beat the other coins in every one of the 6 years, but when the whole altcoin market falls (2022, 2025) the
picks fall too. Long-only R5 had an 86 % max drawdown and only 2 of 6 positive years. Missing: (17) knowing when to be
out of the market, (18) knowing which trades not to take.

## Why one run for both
Both brains feed one trading decision. Testing them in separate runs would mean more looks at half B. Each brain still
has its OWN skill gate, so the run shows which brain works.

## Inputs (frozen)
- R5 scores: `logs/strategy_1d_step15_slow/R5_AI_test_predictions.csv` (Step 15, not re-trained; SHA256 in lock file).
- Rows/features: `core_rows_1d.build` as of 2026-09-30 on `data/universe_all`. Coins: 30 reference + the 531 split coins.
  Eligible unseen row = liquid AND ≥ 120 candles up to that day (Step 15 rule).
- TRAINING universe = all reference-coin rows + eligible A rows. TEST = eligible B rows, 2021-01..2026-09.

## Market features (one row per day, from the TRAINING universe only, values at the close of d)
- Medians of r1, r5, r20, r60, vol_ratio30, atr_pct, dist_hi55_atr, dist_lo55_atr, taker_buy_ratio.
- Std of r5 (dispersion).
- Share of coins with dist_hi20_atr ≥ 0.
- BTC r5, r20, K3 state.
- Breadth (breadth_k3_up_t).
- Fear & Greed (fng, fng_chg7, fng_z30).
- 18 features in total.

## Step 17 market brain
- **Label (training):** 1 if the median open(d+1)→open(d+6) return of the TRAINING-universe coins with a valid return > 0. Known on d+6.
- **Model:** HistGradientBoosting, depth 2, 200 iterations, lr 0.05, min_samples_leaf 50, l2 1.0, random_state 0. Re-trained monthly (1st of month, labels known before it), 2021-01..2026-09. A shuffled-label CONTROL is trained identically.
- **Skill test (on B):** label = median 5-day return of the ELIGIBLE B coins that day > 0. AUC with 95 % month-block CI (2,000 resamples).

## Step 18 veto brain ("trade kahan nahi lena")
- **Label:** 1 = BAD trade = the coin's open(d+1)→open(d+6) return < −0.5 % (a loss after the 0.50 % round-trip cost).
- **Features:** the 47 core coin features + the 18 market features of that day.
- **Model:** = Step 13 core recipe (depth 3, 300 iterations, lr 0.05, leaf 200, l2 1.0, random_state 0). Monthly walk-forward on the training universe. Shuffled CONTROL.
- **Skill test (on B):** AUC of P(bad) on eligible B rows, 95 % month-block CI.

## Fixed trading system (FULL) — no grid, no tuning
- **Base rule:** Step 15 R5 rule. Rebalance every 5 days (2021-01-01 + 5k), target top 10 by R5 score, keep a held coin while its rank ≤ 20, orders at the next open, each buy = min(0.80 × equity / 10, cash / (1 + cost)), cost 0.25 % per fill.
- **Market gate:** on a rebalance day, if P(market up) < that month's model training base rate, sell everything at the next open and buy nothing.
- **Veto:** on a rebalance day, coins with P(bad) > that month's veto-model training base rate are excluded. They are not bought, and a held vetoed coin is sold. Ranks are computed among the non-vetoed coins.
- **Runs:**
  - FULL (AI brains)
  - CONTROL_FULL (R5 + shuffled market + shuffled veto brains)
  - R5_ONLY (= Step 15 rule)
  - FULL at 0.40 % per fill
  - Ablations, reported only and NOT used for the decision: R5 + market only, R5 + veto only.

## Gates
- **G1 pipeline (each brain, on B):** planted feature (label + N(0, 2.79)) AUC ≥ 0.55 AND leak feature (the 5-day return that defines the label) AUC > 0.95.
- **G2a market skill:** AUC CI lower bound > 0.50 AND AUC > CONTROL.
- **G2b veto skill:** same rule.
- **G3 FULL system:**
  - (a) CAGR > 0
  - (b) Calmar > R5_ONLY Calmar AND > CONTROL_FULL Calmar
  - (c) 95 % month-block CI of the mean net return per trade, lower bound > 0
  - (d) ≥ 4 of 6 calendar years positive
  - (e) CAGR > 0 at 0.40 % per fill
  - (f) max drawdown < 50 %
- **Decision:**
  - all pass → `PASS_FULL_SYSTEM` → paper portfolio in the Step 16 forward log; testnet only after ≥ 90 forward days without alarm.
  - G3 passes but G2a or G2b fails → `SYSTEM_PASSES_BUT_BRAIN_UNPROVEN` (not deployed).
  - G1 fails → `INVALID_PIPELINE_CHECK_FAILED`.
  - otherwise → `FAIL`.

## Honest limitations (stated before the result)
- Half B was used before: Step 14 (1-day rule) and Step 15 (R5 portfolio, whose yearly path I have seen). The brains are learned by walk-forward with a fixed recipe, so that knowledge cannot be tuned in. The DESIGN choice (adding a market brain) was motivated by Step 15.
- The market is shared by halves A and B, so the market brain's B test is a time test (one market path 2021–2026, ~2,100 overlapping days, roughly 400 independent 5-day periods), not an independent-coins test.
- The clean judge remains the forward data (Step 16).

## Verification
All numbers go to `claims.json`. `src/audits/verify_step17_18_claims.py` re-derives both labels from raw opens, recomputes the AUCs and the gate/veto decisions from the saved predictions and base rates, re-simulates FULL, CONTROL_FULL and R5_ONLY with separate code, and recomputes the gates.
