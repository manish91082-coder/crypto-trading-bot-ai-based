# STEP 26 PROTOCOL — per-coin exit / "do not hold" brain on top of 1h R24 (pre-registered)

Written and SHA256-locked before any Step 26 model is trained. Code: `src/pipeline_1d/step26_exit_brain.py`.
Spot, long-only, $10,000, 100 % invested, cost 0.25 % per fill. No GitHub action. Nothing is deployed.

## Why, and why so strict (evidence)
- Every passing system has a 75–80 % max drawdown: 1D 81 %, 4H R6 78 %, 1h R24 75 %.
- Market timing failed 3 times:
  - Step 17: no skill;
  - Step 20: skill, but it lost money;
  - Step 21: invalid.
- The Step 22 account breaker was luck.
- Step 21 showed that RANDOM exits can also improve Calmar on one path.
- This is the 4th attempt, so:
  - (i) skill needs a 99 % CI;
  - (ii) the AI exit must beat a matched-frequency random exit;
  - (iii) it must work on BOTH 2021–26 and the 2018–19 period.

## Question
Per coin, not per market: will THIS large coin fall more than 5 % over the next 24 hours?
- If yes, the system does not hold it and keeps that slot in cash.
- The free slot is not refilled, so exposure really drops.

## Rows and data
- **Rows:** exactly the Step 24 rows (1h, TRAIN = top-30 reference + A coins at hours that are multiples of 3; TEST = Step 19 universe, all hours), rebuilt with `step24.build_rows`.
- **2018–19 rows:** the Step 24 2018–19 rows.

## Label
- **tail24:** absolute coin return open(t+1)→open(t+25) < −5 %.
- **Known time:** open(t+25).
- The threshold is fixed before any model. Its base rate is reported, computed from prices only.

## Features (34)
- The 31 Step 24 features.
- Plus 3 market features of the row's universe at that hour: mkt_med_r24 (median r24), mkt_share_down24 (share of coins with r24 < 0), mkt_med_rv12 (median rv12).

## Brains
- **Model:** HGB depth 3, 300 iterations, lr 0.05, leaf 200, l2 1, random_state 0. Monthly walk-forward 2021-01..2026-09.
- **CONTROL:** shuffled labels (seed 26).
- **Frozen brain:** labels known before 2026-10-01, applied to the 2018–19 rows.
- **G1 check:** planted and leak (the true fwd24) on 12 months (every 6th month).

## Exit rule (fixed)
- **Veto:** at each daily R24 decision (the 23:00 UTC bar close), a U coin is VETOED if its P(tail) ≥ the 80th percentile of all exit-brain predictions from EARLIER months. There is no veto in the first month.
- **Trading:**
  - R24 ranking is unchanged.
  - Target = original top 5 minus vetoed coins (not replaced).
  - A held coin is kept only if rank ≤ 10 AND not vetoed.
  - Buy size = equity / 5, so a vetoed slot stays cash.
- **Scores:**
  - 2021–26: Step 24 saved R24_AI walk-forward scores.
  - 2018–19: Step 24 saved R24_FROZEN scores.
- **Thresholds:** 2018–19 thresholds use the same causal rule over the 2018–19 predictions themselves.
- **Comparators per period:**
  - BASE: R24 with no veto (the 2021–26 BASE must reproduce $201,548.26 ± $0.01);
  - RANDOM: 20 seeds; on each decision day the same NUMBER of U coins as the AI vetoed, chosen uniformly at random;
  - CONTROL brain veto.

## Gates
- **G0:** rows identical to Step 24; BASE reproduces Step 24.
- **G1:** planted ≥ 0.55 AND leak > 0.95.
- **G2 skill:** AUC 99 % month-block CI low > 0.50 AND > CONTROL (2021–26).
- **G3 (2021–26) and G4 (2018–19), each:**
  - (a) max drawdown at least 10 points lower than BASE;
  - (b) Calmar > BASE Calmar;
  - (c) Calmar > the 95th percentile of the 20 RANDOM Calmars;
  - (d) 2018–19 only: AUC 95 % CI low > 0.50.
- **Decision:**
  - `INVALID` if G0/G1 fail.
  - `PASS` if G2, G3 and G4 all pass → the exit brain joins R24, with a forward paper portfolio first.
  - `FAIL` otherwise.
- **If FAIL:** the honest conclusion is that drawdown in long-only spot crypto cannot be learned away on this data, and position size is the only proven control (user's choice).

## Honest limitations
- The 2021–26 path and the 2018–19 period have both been used before for selection (not for this exit question).
- −5 % / 24 h is one fixed definition; no other is tried.

## Verification
`src/audits/verify_step26_claims.py`:
- re-derives the tail labels from raw 1h opens;
- recomputes the AUCs;
- re-simulates BASE and AI-veto for both periods with separate code;
- recomputes the gates.
