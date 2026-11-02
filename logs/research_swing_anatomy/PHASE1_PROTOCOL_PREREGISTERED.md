# Swing Anatomy, 2017–2026, all timeframes — Phase 1 (data + catalog + factors + descriptive analysis), pre-registered

Written and SHA256-locked before any result is computed. Code: `src/research/swing_anatomy_phase1.py`.
Measurement only: no model, no trading rule, nothing deployed, no GitHub action.

## User's request
- For every timeframe, from big to small (1Y, 6M, 1M, 1W, 1D, 12h, 8h, 4h, 1h, 30m, 15m, 5m), from 2017–18 to now: where did the market reverse, how far did it fall or rise, and in which situation.
- Use volume, indicators and support/resistance.
- Later, an AI should learn "in which situation a fall or rise goes how far".

## What can and cannot be answered (stated before the results)
- **"Why" in the causal sense cannot be proven from price data.** This study measures which situations, KNOWN AT THE TIME, came before bigger or smaller moves (associations with CIs). It does not claim causes.
- **1Y and 6M:** only about 9 / 18 candles per coin. A ZigZag/ATR cannot be computed and statistics are meaningless. They get a candle-anatomy table only: high, low, the date of each, and the maximum drawdown inside the period.
- **1M:** the 14-month ATR starts in late 2018 for BTC/ETH. Swings are few, so 1M results are case lists with wide CIs.

## Data (all SHA256-verified Binance spot)
- **Coins:** BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LTC, LINK (the swing-study coins).
- **Splicing:** each series = `universe_pre2020` (2017-08..2019-12) + `universe_all` / `universe_hf` (2020-01..2026-09).
  - Gate D1: the boundary must be contiguous (the last pre bar + 1 step = the first post bar) with no duplicate timestamps.
  - Native files are used for 1d, 1h, 15m and 5m.
  - 30m is aggregated from 5m; 4h, 8h and 12h from 1h; 1W (Monday weeks), 1M, 6M and 1Y from 1d.
  - DOGE has no 2019 15m/5m data, so its 15m/5m/30m start in 2020.
- **Cross-checks (gate D2, reported):**
  - 1h aggregated from 5m vs the native 1h file;
  - 1d aggregated from 1h vs the native 1d file;
  - mismatch share of bars (rtol 1e-9 for prices) must be < 1 %.
- **Bad prints:** the swing-study 99 % wick clip is applied to every timeframe. Counts are reported.
- **Indicator ATR:** 14-bar mean true range.

## Swings (verified function)
- `swing_study_1d.zigzag_pivots(df, K)` for K ∈ {2, 3, 4}. **PRIMARY: K = 3.** Timeframes: 1M, 1W, 1D, 12h, 8h, 4h, 1h, 30m, 15m, 5m.
- Gate D3: on the 1D data from 2020, the function reproduces `logs/swing_study_1d/swing_legs_1d.csv` (proven in the previous study). It is re-asserted for BTC.
- **DECLINE leg** = a final H pivot followed by the next L pivot. **RALLY leg** = L followed by H. For each leg:
  - start and end time and price;
  - move %;
  - move in ATR (ATR at the start pivot);
  - number of bars and days.
- **CONFIRMATION time** = the close of the start pivot's `confirm_idx` bar. This is the first moment the leg is knowable in real time.
- **REMAINING move after confirmation** = end price / close at confirmation − 1, in % and in ATR. This is the predictable and tradable part.

## Factors (all causal: computed from data up to and including the bar where they are measured)
Measured at the CONFIRMATION bar (the main analysis) and, for description only, at the start pivot bar.

| Factor | Definition |
|---|---|
| ret5, ret20 | return over 5 / 20 bars |
| dist_sma50_atr, dist_sma200_atr | (close − SMA) / ATR |
| rsi14 | Wilder RSI |
| atr_pct, atr_ratio100 | ATR / close; ATR / mean ATR of the previous 100 bars |
| vol_ratio20 | quote volume / mean of the previous 20 bars |
| taker_ratio | taker-buy quote volume / quote volume |
| range_pos50 | position of the close inside the 50-bar high/low range (0..1) |
| dd_from_high200 | close / 200-bar max high − 1 |
| sup_dist_atr, res_dist_atr | distance to the nearest UNBROKEN same-timeframe k = 3 fractal support below / resistance above, in ATR. "Unbroken" = no close beyond it since it became known. NaN if none |
| vap_at_price | share of 1h USDT volume within ±0.25 ATR of the close (see windows below) |
| htf_state_{1M, 1W, 1D, 4h, 1h} | causal ZigZag (K = 3) leg state of every HIGHER timeframe (+1 up, −1 down, 0 none), from `swing_strategy_1d.zz`, known at the end of that timeframe's last closed bar |
| btc_ret20, btc_state_same_tf | for non-BTC coins |
| fng, fng_chg7 | Fear & Greed of the previous day (from 2018-02) |
| hour, weekday | intraday timeframes |

**vap_at_price window:**

| Timeframe | Window |
|---|---|
| 5m, 15m, 30m | 1 day |
| 1h | 7 days |
| 4h, 8h, 12h | 30 days |
| 1D | 90 days |
| 1W, 1M | 365 days |

## Descriptive analyses (K = 3 unless stated; 95 % month-block bootstrap CIs, 2000 reps)
- **D-A (size and frequency):**
  - per timeframe and direction: count per year, plus median / p75 / p90 / max of move % and move ATR, and duration;
  - the same for the REMAINING move after confirmation.
- **Signed remaining move (used by D-B / D-C):** rem_atr = (close at confirmation − end price) / ATR at confirmation for declines, and (end − close) / ATR for rallies. Positive = the leg continued after confirmation.
- **D-B (top-down nesting):** per timeframe, the remaining DECLINE (ATR) split by the higher-timeframe causal states at confirmation, and the difference "1D down" − "1D up" with CI. The same for rallies.
- **D-C (situations):** for every factor and timeframe, quintiles at confirmation → median remaining move (ATR) and P(remaining ≥ 1 ATR).
  - Spearman correlation of factor vs remaining move (ranks computed once on the full sample; CI from month-block resampling of per-month sums, 2000 reps).
  - Reported for declines and rallies separately.
- **D-D (case files):** the 30 largest declines per timeframe (pooled) with their factor snapshot at confirmation, plus BTC's largest declines per year.
- **D-E (1Y / 6M anatomy):** each yearly and half-year candle per coin: O/H/L/C, the dates of H and L, and the maximum drawdown from the running high inside the period.
- **D-F (K sensitivity):** D-A for K = 2 and 4.

## Interpretation rules (fixed)
- An association counts only if its CI excludes 0 AND it has the same sign in 2017–2020 and 2021–2026 (split check, reported).
- Many factors and timeframes are tested. An isolated significant cell is reported as weak.
- No result here is a trading rule.
- Phase 2 (a separate protocol, written after this report) will train an AI on THE COMPLETE factor list above to predict the remaining move. It must not use a subset hand-picked from these results; this avoids data-snooping. It will be judged on held-out time and the forward log.

## Verification
`src/audits/verify_swing_anatomy_phase1.py`:
- re-derives 200 random legs (pivots, confirmation, remaining move) and their factors with plain loops from the spliced raw files;
- re-checks the splice gates;
- recomputes the D-A medians.
