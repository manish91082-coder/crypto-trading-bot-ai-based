# PRED-1: live forecasts of the next 10 bar closes, then checked against the market. Pre-registered 2026-10-29, before the first forecast

## 1. The request (user, chat, 2026-10-29)
- **Add price prediction to the live desk:** forecast the next 10 prices on each timeframe, for example the next 10 one-minute closes, the next 10 five-minute closes (50 minutes), and so on.
- **Write the method down in a file:** the formula, and on what basis each forecast is made.
- **Verify every forecast** with a verifier once those bars exist: how far each of the 10 prices was from the forecast, and how right the forecasts are.
- **Learn from it** as a live trader would.

## 2. What is forecast
| Item | Setting |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT (Binance spot, public mirror data-api.binance.vision) |
| Timeframes | 1m, 5m, 15m, 1h, 4h, 1d |
| Horizons | h = 1 … 10 bars ahead (1m: 10 minutes; 5m: 50 minutes; 15m: 2.5 hours; 1h: 10 hours; 4h: 40 hours; 1d: 10 days) |
| Target | the CLOSE of each of the next 10 bars |
| When | at every bar close, 2 s after it, from CLOSED bars only (the bar still forming is dropped) |
| Record | each forecast goes into `predictions.jsonl` before its target bars exist: hash-chained line, sha of the closes used, UTC time |

## 3. The formulas (`src/live_paper/predict.py`, version PRED1-v1; c = log close, r = log return)
| Model | Formula (log scale, then exp) | Idea |
|---|---|---|
| M0 naive | ĉ = c_T | random walk: "the next price is the last price", the benchmark every model must beat |
| M1 drift | ĉ = c_T + h · mean(r, last 100 bars) | recent drift continues |
| M2 ema_trend | ĉ = c_T + 0.5 · h · (EMA10_T − EMA10_{T−5}) / 5 | short trend continues, damped by half |
| M3 mean_rev | ĉ = c_T + (EMA20_T − c_T) · (1 − 0.9^h) | price returns toward its EMA20 |
| M4 ar1 | OLS r_t = a + b·r_{t−1} on the last 500 returns, iterated h steps | short-term autocorrelation |
| M5 ensemble | mean of M1 … M4 | combination |
| M6 selector | per symbol / timeframe / horizon, the model of M0 … M5 with the lowest squared error over its last 200 matured forecasts (M0 until 30 have matured) | online learning, scored out of sample (it only uses forecasts that matured before) |

**Band:** 95% band = c_T ± 1.96 · sd(r, last 100) · √h, around M0. It measures whether the forecast uncertainty is right.

## 4. Verification (`src/audits/verify_pred1.py`, written separately; it fetches the market data itself)
**V1 integrity:** the hash chain of predictions.jsonl is intact. Every target time lies after the forecast time, and every base bar is closed at the forecast time.

**V2 no look-ahead, recomputed:** for a sample of forecasts the verifier fetches the closed bars up to the base bar itself, recomputes M0–M5 with its own code, and must match the recorded numbers.

**V3 outcomes:** for every matured target, the actual close comes from the official klines. Recorded per forecast:
- error in basis points, log(actual / forecast) × 10⁴;
- whether the predicted direction (forecast vs base close) was right;
- whether the actual fell inside the 95% band.

**V4 metrics,** per timeframe × model × horizon:
- n; MAE and RMSE in bps;
- skill vs M0 = 1 − MSE / MSE_M0;
- direction hit rate (moves of exactly 0 excluded) with a binomial p vs 50%;
- Diebold-Mariano test vs M0 on squared errors, Newey-West variance with lag h (forecasts overlap);
- band coverage (should be about 95%).

**Context:** for each timeframe, the direction hit rate a trade would need to beat the round-trip fee, from the project's fee-hurdle map.

## 5. What counts as "the forecasts work" (written before any outcome)
A model is useful on a timeframe and horizon only when all of these hold:
- ≥ 300 matured forecasts;
- skill > 0;
- DM p ≤ 0.05 (Benjamini-Hochberg over every model × timeframe × horizon tested);
- the direction hit rate is above the fee-hurdle rate for that timeframe.

Before that the results are descriptive. A model that beats M0 statistically but not the fee hurdle is "real but not tradeable".

**Prior expectation, written now:** crypto prices are very close to a random walk at these horizons (this project's oracle, fee-hurdle and turn studies). M0 is expected to be hard to beat; any skill is expected to be small, mostly at 1m–5m (tiny autocorrelation), and below the fee hurdle.

## 6. Honest limits
- **Data:** the Binance spot public mirror, with official klines as truth.
- **Gaps:** laptop sleep or network loss means missing forecasts. They are logged by their absence and never back-filled.
- **No P&L:** forecasts here are not trades. The LPT-1 desk may use a model only after §5 is met.

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
