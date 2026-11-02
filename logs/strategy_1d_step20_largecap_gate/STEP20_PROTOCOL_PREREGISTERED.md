# STEP 20 PROTOCOL — "when to stay out" brain for the LARGE-CAP market (pre-registered)

Written and SHA256-locked before any Step 20 model is trained. Code: `src/pipeline_1d/step20_largecap_gate_1d.py`.
Spot, 1D, long-only, $10,000, free data only. No GitHub action. Nothing is deployed by this step.

## Why (evidence)
Step 19 proved selection skill inside the top-20 coins:
- AUC 0.559, CI 0.549–0.571.
- $65,275, beating BTC hold on Calmar.
- Per-trade CI > 0.

It failed only on max drawdown (73 %) and years. Its bad years are the market's bad years: 2022 AI −65 % (BTC −56 %), 2025 AI −14 % (BTC −6 %).
Step 17's market brain failed on the SMALL-alt median. This step asks the same kind of question about the LARGE-cap market.

## Market brain
- **Universe for market features and label:** U(d) as in Step 19, the point-in-time top-20 by 30-day mean USDT volume among eligible reference + B coins. It is computed for every day from 2020 on, so the brain has training history.
- **Label:** 1 if the equal-weight mean open(d+1)→open(d+6) return of the U(d) coins (with a valid return) > 0. Known on d+6.
- **Features (18, from U(d) rows at the close of d):** the Step 17 market-feature definition, now computed on U instead of the small-alt universe:
  - medians of r1, r5, r20, r60, vol_ratio30, atr_pct, dist_hi55_atr, dist_lo55_atr, taker_buy_ratio;
  - std of r5;
  - share with dist_hi20_atr ≥ 0;
  - BTC r5, r20, K3 state;
  - breadth;
  - Fear & Greed (3).
- **Model:** = Step 17 market recipe (HGB depth 2, 200 iterations, lr 0.05, leaf 50, l2 1, random_state 0). Monthly walk-forward 2021-01..2026-09 on labels known before the 1st. A shuffled CONTROL is trained identically.

## System (fixed)
- Step 19's AI rule (frozen Step 19 R5 predictions, `U_AI_predictions.csv`, SHA256 in lock file): top 5 of U, keep while rank ≤ 10, rebalance every 5 days, 0.25 % per fill.
- **Gate:** on a rebalance day, if P(market up) < that month's model training base rate → sell everything at the next open and hold USDT until the next rebalance day that allows trading.
- **Internal check:** the same simulator WITHOUT the gate must reproduce Step 19 AI final $65,274.51.
- **Runs:**
  - GATED (AI gate)
  - GATED_CONTROL (shuffled gate)
  - UNGATED (= Step 19)
  - GATED at 0.40 %
  - BTC_HOLD (Step 19 definition)

## Gates
- **G1:** planted (label + N(0, 2.79)) AUC ≥ 0.55 AND leak (the U mean 5-day return itself) AUC > 0.95.
- **G2 skill:** AUC 95 % month-block CI lower bound > 0.50 AND AUC > CONTROL.
- **G3 GATED system:**
  - (a) CAGR > 0
  - (b) Calmar > UNGATED, > GATED_CONTROL and > BTC_HOLD
  - (c) per-trade net mean CI lower bound > 0
  - (d) ≥ 4 of 6 years positive
  - (e) CAGR > 0 at 0.40 %
  - (f) max drawdown < 50 %
- **Decision:**
  - all → `PASS` → paper portfolio in the Step 16 forward log; testnet only after ≥ 90 forward days without alarm.
  - G3 passes but G2 fails → `SYSTEM_PASSES_BUT_BRAIN_UNPROVEN` (not deployed).
  - G1 fails → `INVALID`.
  - otherwise → `FAIL`.

## Honest limitations
- This is a pure time test: one market path, about 2,000 overlapping days, roughly 400 independent 5-day periods.
- The 2021–2026 market path is known to me. The brain is learned by a fixed walk-forward recipe, so nothing can be tuned to it.
- Step 17's similar brain failed.
- The market label uses U coins, which include B coins. That is not look-ahead (only past labels are used), and coin-level hold-out matters only for selection skill.

## Verification
`src/audits/verify_step20_claims.py`:
- re-derives the market label from raw opens;
- recomputes both AUCs;
- re-simulates GATED, GATED_CONTROL and UNGATED with separate code from the saved gate predictions and base rates;
- recomputes the gates.
