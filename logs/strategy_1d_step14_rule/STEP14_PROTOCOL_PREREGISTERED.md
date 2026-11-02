# STEP 14 PROTOCOL — trading rule for the proven 1-day brain (pre-registered)

Written and SHA256-locked before any Step 14 simulation is run. Code: `src/pipeline_1d/step14_trading_rule_1d.py`.
Spot, 1D, long-only, $10,000, free data only. No GitHub action. Nothing is deployed by this step.

## Input (frozen, no re-training)
- The B1 (1-day) predictions `p1` from Step 13 (`logs/strategy_1d_step13_unseen/AI_signals_unseen.csv`): brains
  trained only on the 30 known coins, monthly walk-forward, one prediction per LIQUID unseen coin-day
  (2021-01-01..2026-09-30, 531 coins). The shuffled-label CONTROL predictions from the same file
  (`CONTROL_signals_unseen.csv`). SHA256 of both files are recorded in `PROTOCOL_SHA256.txt`.
- `p1` of day d uses information up to the close of d; every trade decided on day d is executed at the OPEN of d+1.
- Prices: Step 13 loader (`S13.load_new`), same survivorship rules (delisted coin -> sold at its last real close).

## Coin split (made before any Step 14 result, file SHA256 a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0)
`coin_split.csv`: the 531 coins sorted by name, permuted with `numpy.random.default_rng(20261013)`; first half of
the permutation = A_design (265 coins), rest = B_confirm (266 coins).
A is used to choose ONE rule. B is used ONCE to test that rule. Limitation stated up front: A and B cover the same
dates, so B tests "other coins", not "another market period"; the clean time test is the forward data (Step 16).

## Rule family (all decisions from the brain's scores; nothing else)
Every day d, among the half's coins that have a score on d (liquid that day), rank by score (high first, ties by name):
- entry-eligible: rank <= N AND score >= the q-quantile of all scores of that half from strictly EARLIER months;
- a held coin is KEPT while its rank <= N x buffer (and it has a score on d); otherwise it is sold at the next open;
- free slots (N minus kept) are filled with entry-eligible coins in rank order;
- regime gate (option): if ON, trading is allowed on d only when the mean score of all the half's coins on d >= the
  median of the daily mean scores of strictly EARLIER months; when not allowed, all positions are sold and nothing is
  bought (first month: no threshold -> no trading).
- sizing: each buy = min(0.80 x equity at that open / N, cash / (1 + cost)); no rebalancing of held coins; buys < $10
  skipped. Cost 0.25 % per fill (buy and sell).
Grid (24 rules): N in {3, 5, 10}; buffer in {1, 3}; q in {0.90, 0.98}; regime gate in {OFF, ON}.

## Choosing the rule (on A only)
Among the 24 rules on A with >= 60 trades and CAGR > 0: the highest Calmar (CAGR / max drawdown). If none qualifies:
`FAIL_NO_RULE_ON_DESIGN_HALF`, B is not touched.

## Confirmation on B (one run, chosen rule only)
Runs on B with the same rule: AI (p1), CONTROL (shuffled-label p1), SIMPLE (score = 20-day price return
close(d)/close(d-20) - 1 of the same liquid rows; a trivial non-AI ranking), and AI at 0.40 % per fill.
Gates:
- G1: AI CAGR > 0 (0.25 % per fill).
- G2: AI Calmar > CONTROL Calmar AND AI Calmar > SIMPLE Calmar.
- G3: mean net return per AI trade, 95 % month-block bootstrap CI (2,000 resamples, block = entry month) lower bound > 0.
- G4: >= 4 of the 6 calendar years (2021..2026) with a positive AI return.
- G5: AI CAGR > 0 at 0.40 % per fill.
Decision: all pass -> `PASS_RULE_CONFIRMED` -> next: forward dry-run on live data (Step 16, new protocol).
Otherwise `FAIL_RULE_NOT_CONFIRMED`. The result is reported as is; no change of rule after B is seen.

## Verification
All numbers go to `claims.json`. `src/audits/verify_step14_claims.py` re-implements the rule independently and
re-simulates every reported B run from raw opens/closes, re-derives the causal thresholds and the regime gate, and
recomputes the selection on A and all gates.
