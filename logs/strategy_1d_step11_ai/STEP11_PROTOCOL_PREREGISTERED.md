# Step 11 — "Confident-only" multi-brain AI with self-monitoring (pre-registered 2026-10-13, before any Step 11 result)

HONESTY NOTE: the idea "trade only the most confident ~10% of predictions" came from looking at Step 10 out-of-sample
predictions (2021-2026). A backtest on the same years is therefore NOT fully clean. Passing this protocol only allows a
FORWARD testnet trial (section 6), which is the clean proof. No real money from a backtest alone.

## 1. Data (free only, verified)
Step 10 data (1D 30 coins point-in-time top-10 universe, verified 1h order flow, Binance futures info) + Crypto Fear &
Greed Index (alternative.me, raw JSON SHA256 29b2ca42...; 3,173 days 2018-02-01..2026-10-13, 2 missing days left
missing). FNG value of day d is published 00:00 UTC of day d -> known at the close of d.
New features: fng, fng 7-day change, fng 30-day z-score; cross-sectional ranks (0..1 across the coins that day) of
r1, r5, r20, vol_ratio30, taker_buy_ratio, fund_1d, oi_chg1, dist_hi20_atr.

## 2. Brains (all re-trained on the 1st of every month on labels known before that day)
B1 = 1-day brain (label ABS_1), B3 = 3-day brain (label ABS_3): each an average of 3 bagged
HistGradientBoostingClassifiers (max_depth 3, 300 iters, lr 0.05, min_samples_leaf 200, l2 1.0), bag = 80% bootstrap
of the training rows with seeds 0/1/2, time-decay sample weight 0.5^(age_days/365).
BS = swing-entry brain (Step 8 entry label, same bagging/decay) on swing-event days only.

## 3. Decision rule (the AI decides; thresholds come only from PAST predictions)
At the close of day d, for each point-in-time member coin:
  vote1 = B1 prob >= 90th percentile of all B1 OOS predictions made in earlier months
  vote3 = B3 prob >= 90th percentile of earlier B3 predictions
  voteS = swing event today and BS prob >= 80th percentile of earlier BS predictions
  BUY signal if votes >= 2.  (First month without history -> no trades.)
Ranking when signals > free slots: mean of the coin's percentile ranks.

## 4. Trade management (spot long-only)
Buy at the next open with 20% of equity (max 4 positions => 80%, 20% USDT reserve). Hold 3 days: sell at the open of
entry_day+3 unless a new BUY signal for the coin appeared at the previous close (then hold 3 more days).
Stop-loss 2 x ATR14 below entry (daily OHLC, gap-aware, stop checked first). Friction per fill 0.125% (base).
Portfolio DD >= 15% -> no new entries for 30 days.
SELF-MONITOR (auto-pause): every signal (taken or not) is scored as a shadow trade once its 3-day outcome is known
(open d+1 -> open d+4, minus 0.25%). If the mean of the last 40 known shadow outcomes < 0 -> no new entries until it
is >= 0 again.

## 5. Gates (all must pass)
G-sanity: planted-signal test on the new pipeline (feature = ABS_3 label + N(0, 2.79)) recovers OOS AUC in [0.57, 0.63].
G-skill : the shadow trades (all BUY signals, members) have mean net 3-day return (after 0.25%) > 0 with a monthly-block
          bootstrap 95% CI lower bound > 0, and higher than the same statistic for the label-shuffled CONTROL.
G-port  : AI portfolio Calmar (base friction) > BASELINE (equal-weight members, 80% invested, daily rebalance) and >
          CONTROL portfolio; AND AI CAGR > 0 at double friction (0.25% per fill).
G-years : AI portfolio positive in at least 4 of the 6 calendar years 2021..2026.
All numbers via claims.json, independent verifier (separate re-simulation), protocol hash checked.

## 6. If all gates pass -> FORWARD testnet trial (the real proof)
Same code live on Binance SPOT TESTNET, monthly re-training, health check hourly. Pre-registered forward success
criterion, evaluated after >= 40 closed trades or 16 weeks (whichever first): mean net trade return > 0 and the live
shadow-signal mean > 0. Fail -> stop and report. Real money is not part of this protocol.
