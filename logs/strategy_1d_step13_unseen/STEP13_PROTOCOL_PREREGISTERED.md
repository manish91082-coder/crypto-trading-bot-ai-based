# STEP 13 PROTOCOL — Unseen-coins exam of the Step 12 brain design (pre-registered)

Written and SHA256-locked BEFORE any model is trained or any prediction is made on the unseen coins.
Code: `src/pipeline_1d/step13_unseen_coins_1d.py`. Spot, 1D, long-only, free data only. No GitHub action.

## Why
Steps 7–12 were six AI attempts on the SAME 30 coins and the SAME 2021-01..2026-09 period. Repeated testing on one
data set can make one attempt look good by chance. Coins the brains have never seen give genuinely new data without
waiting months for forward data. This is a one-shot exam: the result is reported whatever it is, and nothing in the
design may be changed after the first result is seen (a change = new step, new protocol).

## Data
- Every USDT spot pair on Binance Vision (leveraged tokens excluded), 1D and 1h, 2020-01..2026-09, every zip
  SHA256-checked against Binance's .CHECKSUM (`src/downloaders/download_universe_all_usdt.py`).
- Survivorship-free: delisted pairs included; first continuous history only (a later relisting is never glued on);
  after the last real candle the price is frozen (same rule as Step 6.4).
- Unseen coins = all pairs NOT among the 30 training coins, excluding by NAME (decided before results): stablecoins,
  fiat, wrapped / liquid-staking coins, gold tokens and Binance tokenized stocks/ETFs (lists `NOT_CRYPTO`,
  `STOCK_TOKENS` in the code); plus a data rule for any pegged asset the name list missed: median |daily
  close-to-close return| over the coin's history < 0.3 %; plus coins with < 120 daily candles, coins whose data ends
  before 2021-03-02, coins without a 1h file. Every exclusion and its reason is written to `unseen_coin_selection.csv`.
- 1h days that fail the 1h-vs-1D cross-check get missing 1h features (Step 9 rule).

## Brain (frozen = Step 12 recipe, "core" features)
- B1 (next 1 day), B3 (next 3 days): HistGradientBoosting depth 3, 300 iter, lr 0.05, min_samples_leaf 200, l2 1.0,
  label = open(d+1)→open(d+1+h) return > 0.25%. BS (swing entry): Step 8 triple-barrier label on Step 7 swing
  candidates, same model with min_samples_leaf 100. No bagging, no time decay (= Step 12).
- Features: Step 8 daily (23) + Step 9 1h (13) + BTC K3 state + breadth + Fear&Greed (3) + cross-sectional ranks of
  r1, r5, r20, vol_ratio30, taker_buy_ratio, dist_hi20_atr. **No futures-derived features** (they do not exist for all
  coins and having a perpetual is a selection effect). Swing brain: Step 7 features ∪ the daily+1h set + Fear&Greed.
- Training: ONLY the 30 known coins, re-trained on the 1st of every month 2021-01..2026-09 on labels known before
  that day. Shuffled-label CONTROL trained identically.
- Market inputs for unseen coins (breadth, cross-sectional ranks) are measured against the same 30-coin reference
  set (rank = pandas average-percentile of the value inside the 30-coin values of that day plus itself).

## Test rows and trading
- Skill rows: unseen coin-days 2021-01..2026-09 that are LIQUID: trailing-30-day mean daily USDT volume
  (volume × close, days up to and including the row's day) ≥ $2,000,000.
- Trading (Step 12 rules unchanged): BUY when ≥ 2 of 3 brains are in their top band (B1/B3 top 10 %, BS top 20 %;
  cut-offs = quantiles of predictions from EARLIER months only, computed on the liquid unseen rows), only point-in-time
  universe members = each year the 10 unseen coins with the highest trailing-365-day USDT volume on Dec 31;
  3-day hold, 2 ATR stop, max 4 positions × 20 %, 15 % drawdown pause, 40-signal shadow self-monitor.
- Cost: **0.25 % per fill** (2× the Step 12 assumption) for the AI, CONTROL and the equal-weight BASELINE;
  shadow return = open(d+1)→open(d+4) − 0.50 %.

## Gates (all on unseen coins)
- **G1 pipeline:** leak test (future 1-day return as a feature) AUC > 0.95 AND planted test (label_3 + N(0, 2.79),
  theoretical AUC ≈ 0.60) AUC ≥ 0.55. Note, stated before the result: Step 11/12 used the band 0.57–0.63 and Step 12
  reached 0.5665; G1's job here is only to prove the transfer pipeline works (learns a real planted signal, labels
  aligned), so the lower bound is 0.55. A G1 failure makes the exam INVALID, not a pass or fail of the brain.
- **G2 skill (primary):** for B1 or B3: AUC month-block bootstrap 98.75 % interval (95 % Bonferroni-corrected for two
  brains, 2,000 resamples) lower bound > 0.50 AND AUC > the CONTROL AUC.
- **G3 trading:** shadow mean net return 95 % month-block CI lower bound > 0 AND AI CAGR > 0 AND AI Calmar > CONTROL
  Calmar AND AI Calmar > BASELINE Calmar AND ≥ 4 of 6 calendar years positive.

## Decision
- G1 + G2 + G3 → `PASS_BRAIN_GENERALISES` → next step: forward dry-run on live data + retrain on all coins (new protocol).
- G1 + G2 only → `PARTIAL_SKILL_BUT_TRADING_RULE_FAILS` → skill is real; trading rule needs a new protocol.
- G1 ok, G2 fails → `FAIL_NO_TRANSFERABLE_SKILL` → the Steps 7–12 brains learned nothing that transfers.
- G1 fails → `INVALID_PIPELINE_CHECK_FAILED`.
Reference only (no gate): B1/B3 AUC on the 30 known coins' member rows with this core recipe.

## Verification
All numbers go to `claims.json`; an independent verifier recomputes AUCs with labels re-derived from raw opens,
the causal cut-offs, the shadow returns and re-simulates the portfolios with separate code. Nothing is deployed by
this step in any outcome.
