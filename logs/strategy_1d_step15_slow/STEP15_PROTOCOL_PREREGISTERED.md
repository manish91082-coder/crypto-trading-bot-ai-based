# STEP 15 PROTOCOL — slower, relative question + many-coin training (pre-registered)

Written and SHA256-locked before any Step 15 model is trained. Code: `src/pipeline_1d/step15_slow_relative_1d.py`.
Spot, 1D, long-only, $10,000, free data only. No GitHub action. Nothing is deployed by this step.

## Why (evidence)
Step 14: the 1-day brain has real skill (gross +0.57 % per trade vs control −0.19 %), but the trades last 1.8 days
and the 0.50 % round-trip cost eats it. A question whose answer lasts longer can produce fewer trades with bigger
moves. Whether that works is unknown; this step tests it.

## Brains
- R5 and R10: label = 1 if the coin's open(d+1)→open(d+1+h) return (h = 5 or 10 days) is greater than the MEDIAN
  of the same return of the 30 reference coins (the Step 6–12 coins with a valid return that day); else 0.
  Label known on day d+1+h. No coin outside the 30 enters the median, so no test coin influences any label.
- Model, features and monthly walk-forward exactly as the Step 13 core recipe (`core_rows_1d.build`, 47 features,
  HistGradientBoosting depth 3 / 300 iter / lr 0.05 / leaf 200 / l2 1, random_state 0), re-trained on the 1st of
  each month 2021-01..2026-09 on labels known before that day. Shuffled-label CONTROL trained identically.

## Data and rows
- `data/universe_all` (SHA256-verified), as of 2026-09-30, read through `core_rows_1d` (replay-proven identical to
  Step 13).
- Coins: the 30 reference coins + the 531 coins of `logs/strategy_1d_step14_rule/coin_split.csv`
  (A_design 265 / B_confirm 266, SHA256 a1633340…).
- An unseen-coin row is ELIGIBLE when it is liquid (Step 13 rule) AND the coin has ≥ 120 daily candles up to and
  including that day (fixes the Step 13 whole-history rule, see the Step 13 addendum).
- TRAINING rows: all reference-coin rows + eligible A rows. TEST rows: eligible B rows, 2021-01..2026-09.
- Disclosure: half B was used once before (Step 14, 1-day rule only). Its 5/10-day relative outcomes have not been
  examined by any step.

## Fixed trading rule (no grid, no tuning)
Every h days (rebalance days = 2021-01-01 + k·h), at the close of the rebalance day: rank the eligible B coins by
score. Target = top 10. A held coin is kept while its rank ≤ 20. Others are sold, and the free slots are filled from the top
ranks. Orders execute at the next open. Each buy = min(0.80 × equity at that open / 10, cash / (1 + cost)). Between
rebalances positions are only touched if a coin's data ends (sold at its last real close). Cost 0.25 % per fill.
The same rule is run with CONTROL scores and with SIMPLE scores (20-day price return, a non-AI ranking),
and for AI at 0.40 % per fill.

## Gates
- G1 pipeline (on R5): planted feature (label + N(0, 2.79)) AUC ≥ 0.55 AND leak feature (the relative 5-day return
  itself) AUC > 0.95, on B test rows.
- G2 skill (per horizon): AUC on B test rows, month-block bootstrap 98.75 % interval (Bonferroni for 2 horizons,
  2,000 resamples) lower bound > 0.50 AND AUC > CONTROL AUC.
- G3 trading (per horizon):
  - (a) AI CAGR > 0;
  - (b) AI Calmar > CONTROL Calmar and > SIMPLE Calmar;
  - (c) mean net return per AI trade, 95 % month-block CI (by entry month) lower bound > 0;
  - (d) ≥ 4 of 6 calendar years positive;
  - (e) AI CAGR > 0 at 0.40 % per fill.
- Decision:
  - If G1 fails → `INVALID_PIPELINE_CHECK_FAILED`.
  - A horizon PASSES if G2 and all of G3 pass. If any horizon passes → `PASS_<h>` (if both pass, the higher Calmar). That brain and rule then enter the Step 16 forward log as a paper portfolio. Testnet only after ≥ 90 forward days without a Step 16 alarm.
  - If G2 passes but G3 fails → `PARTIAL_SKILL_RULE_FAILS`.
  - Otherwise → `FAIL_NO_SKILL`.

## Verification
All numbers go to `claims.json`. `src/audits/verify_step15_claims.py`:
- re-derives labels from raw opens;
- recomputes AUCs with the rank formula;
- re-simulates every portfolio with separate code;
- recomputes the gates.
