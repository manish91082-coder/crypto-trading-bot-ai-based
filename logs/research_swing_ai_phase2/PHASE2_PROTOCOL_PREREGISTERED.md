# Swing Anatomy Phase 2: can an AI pick the good rallies? (pre-registered)

Written and SHA256-locked before any Phase 2 model is trained. Code: `src/research/swing_ai_phase2.py`. Verifier: `src/audits/verify_swing_ai_phase2.py`.
No trading, no deploy, no GitHub.

## Question
Phase 1 found:
- Following every confirmed rally gives a NEGATIVE median trade on every timeframe.
- The money comes only from a few large rallies, on 4h and above.
- Single factors are weak (|rho| ≤ 0.17).

Phase 2 asks: at the moment a rally is confirmed in real time, can an AI that uses ALL Phase 1 factors tell which rallies are worth following? The answer must hold after cost, on held-out time, in both eras.

## Events (real time, failed signals included)
- **Coins and data:** the 10 coins, from the same spliced, SHA-verified data and the same bars as Phase 1:
  - `load_spliced` 1h/1d;
  - 4h/8h/12h aggregated from 1h; 1W/1M from 1d;
  - the 99 % wick clip; ATR14.
- **Timeframes:** 4h, 8h, 12h, 1D.
- **ENTRY event:** a bar i where the causal ZigZag state (`swing_strategy_1d.zz`, K = 3) becomes +1 (it was not +1 at bar i−1).
- **EXIT:** the first later bar j where the state is −1. If there is no such bar before the data end, the trade is open; it is excluded and counted.
- **Trade:**
  - Entry at close[i], exit at close[j]. These are the confirmation-bar closes, the same convention as the Phase 1 descriptive table.
  - net = close[j] / close[i] × (1 − 0.0025) / (1 + 0.0025) − 1, i.e. 0.25 % per fill, the research cost.
  - **Label** = 1 if net > 0.
  - **Known time** = the end of bar j.

## Features (fixed, ALL 25 Phase 1 factors, not a subset)
- Measured at bar i with the exact Phase 1 code. The column list is the same as the `c_` columns:
  - ret5, ret20, dist_sma50_atr, dist_sma200_atr, rsi14, atr_pct, atr_ratio100, vol_ratio20, taker_ratio, range_pos50, dd_from_high200, sup_dist_atr, res_dist_atr, vap_at_price;
  - htf_state_{1M, 1W, 1D, 4h, 1h} (only for higher timeframes, NaN otherwise);
  - btc_ret20, btc_state_same_tf (NaN for BTC);
  - fng, fng_chg7;
  - hour, weekday.
- Plus `tf_code` (4h = 0, 8h = 1, 12h = 2, 1D = 3). One pooled model is used for the 4 timeframes.

## Model and test
- **Model:** HGB research recipe (depth 3, 300 iterations, lr 0.05, leaf 200, l2 1, random_state 0).
- **Monthly walk-forward:**
  - Test months 2019-01 .. 2026-09.
  - For month T: train on all events whose label was known before T. Test on events whose entry bar ends in [T, T + 1 month).
- **CONTROL:** the same walk-forward with permuted training labels (seed 2).
- **Selection rule (causal):**
  - Follow a test event only if its score ≥ the median score of that month's model on its own training rows.
  - "ALL" = follow every event.
- **Periods:** P1 = 2019-01..2020-12, P2 = 2021-01..2026-09.

## Gates (all must hold → PASS)
- **G0 (data):**
  - For events whose bar i equals a Phase 1 K = 3 rally leg's `confirm_i` (same coin and timeframe), all 25 factor values equal the stored Phase 1 `c_` values (|diff| < 1e-9, or both NaN).
  - At least 95 % of the events must have such a match.
- **G1 (pipeline sanity):**
  - planted feature = label + N(0, 2.79) → AUC ≥ 0.55;
  - leak feature = net → AUC > 0.95.
- **G2:** AI AUC over all test events: CI low > 0.50, and AUC > CONTROL AUC.
  - 95 % month-block bootstrap, 2000 reps.
- **G3:** AI AUC CI low > 0.50 in P1 AND in P2, separately.
- **G4 (money, after cost):** mean net per trade of SELECTED − ALL:
  - month-block CI low > 0 over all test months;
  - point estimate > 0 in P1 AND P2.

**Decision:**
- PASS → "AI rally filter" becomes a candidate.
  - It goes to the forward log as a shadow line, only after the user agrees.
  - It still needs a portfolio test, because overlapping trades and capital limits are not modelled here.
- FAIL → reported. Swing information stays descriptive (dashboard).

## Report-only (no gates)
- Per timeframe: AUC, mean net of ALL / SELECTED / REJECTED, win share, n.
- Open trades excluded.
- **Time-reversed frozen check:** train on events with entry ≥ 2021-01-01 whose label was known before 2026-10-01, and test on the entries of 2017-08..2020-12.
- Feature importance is NOT computed (no fishing).

## Limits stated now
- The trades of different coins and timeframes overlap and are correlated. Month-block resampling handles part of this, not all.
- Entry and exit at the confirmation close assume a fill at that price; the next-open gap is not modelled. 0.25 % per fill is used; the Step 2 order-book study suggests that is conservative for $333 orders.
- About 7,500 events in total: CIs will be wide, especially in P1.
