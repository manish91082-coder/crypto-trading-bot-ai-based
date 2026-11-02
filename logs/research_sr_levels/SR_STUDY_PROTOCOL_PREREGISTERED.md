# Support/Resistance evidence study (pre-registered)

Written and SHA256-locked before any result is computed. Code: `src/research/sr_levels_study.py`.
This is a measurement study only: no model, no trading system, nothing deployed, no GitHub action.

## Question
Do swing support/resistance levels (past swing lows/highs) stop the price more often than ordinary price levels, on
each timeframe from 5m to 1w? Does the effect depend on the level's age (old levels) and on confluence with a higher timeframe?
Is the effect big enough to matter after cost?

## Data (all SHA256-verified Binance spot)
- **Coins:** the 10 coins most often in the Step 19 top-20 universe: BTC, ETH, BNB, XRP, DOGE, ADA, SOL, LINK, AVAX, TRX (USDT pairs).
- **Period:** 2021-01-01 .. 2026-09-30.
- **Timeframes and sources:**

| Timeframe | Source |
|---|---|
| 5m | `data/universe_hf/5m` |
| 15m | `data/universe_hf/15m` |
| 30m | aggregated from 5m |
| 1h | `data/universe_all/1h` |
| 4h, 8h, 12h | aggregated from 1h (UTC-aligned) |
| 1d | `data/universe_all/1d` |
| 1w | aggregated from 1d (Monday weeks) |

- **Aggregation rule:** open = first, high = max, low = min, close = last. Only bars that contain data are used.

## Definitions (fixed)
- **ATR:** 14-bar mean true range of the timeframe.
- **Swing level (REAL):** bar i is a swing high if high[i] = max(high[i−3 .. i+3]) (k = 3). It is only KNOWN at bar i+3, the confirmation time c. Swing lows are defined the same way with lows.
  - Resistance = swing high, support = swing low.
  - A level is kept only if it is on the correct side at c: resistance > close[c], support < close[c].
- **CONTROL level:** the high (for resistance) or low (for support) of a randomly chosen NON-swing bar.
  - Same count per coin, timeframe and side as REAL (numpy seed 7).
  - Same 3-bar confirmation delay and the same side condition at c.
  - It answers: "is a swing level special, or would any old price level do the same?"
- **First touch:** the first bar j > c whose high ≥ L (resistance) or low ≤ L (support). Only the first touch of each level is used.
- **Outcome after the touch** (m = 1 ATR, the ATR at bar j−1; horizon 48 bars):
  - **BREAK:** price goes beyond the level by ≥ 1 ATR first. This includes the touch bar itself (high[j] ≥ L + ATR for resistance).
  - **BOUNCE:** price comes back from the level by ≥ 1 ATR first, starting from bar j+1. That means low ≤ L − ATR for resistance, high ≥ L + ATR for support.
  - Both in the same bar → ambiguous (excluded, counted). Neither within 48 bars → timeout (excluded, counted).
- **Bounce rate:** BOUNCE / (BOUNCE + BREAK).

## Measurements
1. **Effect:** bounce rate REAL − CONTROL, per timeframe and side.
   - CI: 95 % month-block bootstrap (2000 reps, months of the touch time, pooled over coins).
   - **Effect exists:** CI lower bound > 0.
2. **Age:** age at first touch (bars from c to j), in 3 buckets (≤ 50, 51–500, > 500 bars). REAL vs CONTROL in each bucket. This answers "do OLD levels still work?".
3. **Confluence (1h only):** 1h REAL touches where a REAL 1d swing level of the same side, confirmed before the touch and within the previous 365 days, lies within 0.5 × ATR(1h) of L. Bounce rate with vs without confluence (95 % bootstrap CI of the difference).
4. **Economics:**
   - For support touches (long-only): expected value of "buy at the touch, target +1 ATR, stop −1 ATR" = (2p − 1) × ATR%.
   - Compared with round-trip cost 0.20 % (fee only) and 0.50 % (our research cost).
   - Uses the median ATR% of the timeframe. These are gross estimates, not a backtest.

## Interpretation rules (fixed)
- An effect is "real" only if the CI lower bound is > 0.
- An effect is "tradable" only if the gross EV per trade > 0.50 % cost on the median ATR.
- Otherwise the S/R map is still allowed as INFORMATION (features / context for brains), but not as a stand-alone trading rule.
- No parameter (k = 3, m = 1, H = 48) is changed after results are seen. Sensitivity runs are not part of this study.

## Verification
`src/audits/verify_sr_study.py`:
- re-derives 400 random events (REAL and CONTROL) by plain bar-by-bar loops from the raw files: the swing test, the first touch and the outcome;
- recomputes the bounce rates from the saved event table.
