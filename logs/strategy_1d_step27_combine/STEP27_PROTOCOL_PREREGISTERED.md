# STEP 27 PROTOCOL — combining the timeframe sleeves + position-size table (pre-registered)

Written and SHA256-locked before any combined result is computed. Code: `src/pipeline_1d/step27_combine.py`.
No new brain is trained. Only verified, frozen predictions are used. No GitHub action. Nothing is deployed.

## Sleeves (each a separate sub-account, rules unchanged; cost 0.25 % per fill)
| Sleeve | Source of scores | 2021-01..2026-09 | 2018-02..2019-12 |
|---|---|---|---|
| D1 | Step 19 R5 1D, top 5 of top-20, every 5 days | `U_AI_predictions.csv` (walk-forward) | Step 22 frozen-brain `U_pre2020_predictions.csv` |
| H4 | Step 23 4H R6, daily | `test_predictions_4h.csv` R6_AI | `pre2020_predictions_4h.csv` R6_FROZEN |
| H1 | Step 24 1h R24, daily | `test_predictions_1h.csv` R24_AI | `pre2020_predictions_1h.csv` R24_FROZEN |
| BTC | buy and hold BTCUSDT | — | — |

**Integrity (G0).** At invest fraction f = 100 %, each sleeve must reproduce its verified final value (± $0.01):

| Period | D1 | H4 | H1 | BTC |
|---|---|---|---|---|
| 2021–26 | $74,452.43 | $98,734.89 | $201,548.26 | $28,767.66 |
| 2018–19 | $3,423.80 | (new) | $2,836.59 | $6,960.89 |

## Investment fraction f (the position-size lever)
- Each sleeve buy = min(f × equity / N, cash / (1 + cost)). The rest stays in USDT at 0 % yield.
- f ∈ {100 %, 75 %, 50 %, 30 %}. BTC sleeve: f × capital in BTC.

## Mixes (fixed weights, split once at the start, NO rebalancing between sleeves, so there is no hidden cost)
- **M_AI3:** D1, H4, H1 at 1/3 each.
- **M_AI3_BTC:** D1, H4, H1, BTC at 1/4 each.
- **Single sleeves:** shown for reference.

## Reported (no tuning, nothing is selected by optimisation)
- Daily-return correlation between sleeves, 2021–26.
- For every mix, f and period: final, CAGR, max drawdown, Calmar, and year returns.
- **Range of 1-year outcomes:** month-block bootstrap (10,000 draws of 12 months with replacement) from the pooled monthly returns of BOTH periods (23 + 69 months); 5th / 25th / 50th / 75th / 95th percentile of the 1-year multiple, plus P(loss > 30 %).
  - The 2018–19 months are included on purpose, so the bear market is represented.

## Decision rule (stated now)
- No PASS/FAIL. This is a decision table for the user.
- The f choice belongs to the user: drawdown tolerance is a preference, not a fact.
- **Recommendation rule, fixed now:** recommend the mix with the higher median 1-year multiple among those whose 5th-percentile 1-year multiple is ≥ 0.50, at the largest f meeting that. If none meets it, say so.
- **Before any real money:** the recommended setup runs as a forward paper portfolio (no orders) for ≥ 90 days.

## Honest limitations
- **Shared signal:** D1, H4 and H1 select from the same top-20 coins, and H4/H1 ask the same 1-day question, so the correlation is expected to be high.
- **Short sample:** the bootstrap assumes the future looks like a mix of 2018–19 and 2021–26 months. It is a range, not a promise.

## Verification
`src/audits/verify_step27_claims.py`:
- recomputes every mix curve from the saved sleeve daily curves with separate code;
- recomputes the correlations;
- recomputes the bootstrap percentiles from the saved monthly returns with a fixed seed;
- checks the recommendation rule.
