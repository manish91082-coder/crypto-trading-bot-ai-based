# Step 10 — method check + new information + shorter question (pre-registered 2026-10-13, before any Step 10 result)
Trading stays SPOT, long-only, 1D decisions at the daily close, $10,000, fee 0.075% + slippage 0.05% per fill,
20% reserve. Futures data is used ONLY as information (no futures trading). Universe: 30 coins, point-in-time top 10.

## 10.0 Method sanity (is our pipeline able to learn at all?)
S-A Planted signal: add feature planted = label + N(0, 2.79) (theoretical AUC ~0.60) to the Path-2 h=1 dataset; the
    unchanged walk-forward must recover OOS AUC in [0.57, 0.63]. Same test on the Path-1 entry dataset.
S-B Alignment: a deliberately leaked feature (the realised forward return itself) must give OOS AUC > 0.95 (proves
    labels and rows are aligned). These features are used ONLY in this check.
If S-A fails the method is broken -> stop and fix before any other claim.

## 10.1 New information (Binance Vision, SHA256-verified, USD-M futures public data, information only)
* funding rate (8h settlements -> daily sum and 7-day sum), premium index 1d (futures premium vs spot index: close,
  7-day mean), open interest from daily `metrics` files (last value of the day; 1-day and 7-day % change; top-trader
  and global long/short ratios; taker long/short volume ratio).
* BTC dominance PROXY (true market-cap dominance is not in Binance data): BTC share of the 30 coins' spot USDT volume
  (7-day), and BTC vs equal-weight-alt 7/30-day relative return.
* Perp symbol map: SHIB -> 1000SHIBUSDT; coins/days without a perp -> missing (never filled with fake values).
* Evidence checks: every file SHA256 vs .CHECKSUM; funding timestamps on the 8h grid; premium-index candles continuous;
  coverage per coin reported.

## Path 1 — swing entries (Step 8 setup) + 10.1 features
Identical to Step 8/9 (labels, models, monthly re-training, policy, portfolios) with Step 9 features + 10.1 features.
Gates exactly Step 8: G1/G2 AUC >= 0.55, CI low > 0.50, > shuffled control, top quintile > bottom; G3 Calmar.

## Path 2 — shorter question, every coin-day
Rows: every coin-day with real data (30 coins), decision at the close of day d, execution at open d+1.
Labels (h = 1 and 3 days): ABS_h = open[d+1+h] / open[d+1] - 1 - 0.25% > 0 (profitable after round-trip cost).
Features: Step 9 daily + 1h features + 10.1 features + swing states. Model per h: HistGradientBoostingClassifier
(max_depth 3, 300 iters, lr 0.05, min_samples_leaf 200, l2 1.0), re-trained on the 1st of every month on labels known
before that day. Skill measured on point-in-time member rows.
Skill gate per h: AUC >= 0.53, monthly-block bootstrap 95% CI low > 0.50, > shuffled control, top quintile > bottom.
Portfolio per h (daily re-evaluation): at each close hold the members with P >= max(0.5, training base rate), top 4 by
P, 20% of equity each (max 80%); rebalance at the next open paying friction on traded notional. Baseline = all members
equal weight, 80% invested, same rebalancing/cost model. Control = shuffled-label models, same policy.
G3 (path 2): AI Calmar > baseline AND > control.

## Decision
Deploy to TESTNET only a configuration that passes ALL its skill gates AND its G3 (best Calmar if several).
Otherwise FAIL -> nothing deployed. Any later change = new protocol number. All numbers via claims.json + verifier.
