# Schema: logs/oracle_9m_2026 tables

Conventions for every file:
- Format: Parquet (zstd) for the oracle tables, CSV / JSON for the Part B results.
- Times are UTC and naive. Bar times are open times.
- Percent columns end in `_pct`.
- 2026-02-13 (the manual-study Day 10) is present in the oracle tables. It is excluded from every statistic and from the Part B daily / monthly tables.

## oracle_day.parquet: one row per day (273)

**Price and timing**

| Column | Meaning |
|---|---|
| date | the UTC day |
| open, high, low, close, volume | the day's OHLCV (from 5m) |
| ret_pct | (close / open − 1) × 100 |
| range_pct | (high / low − 1) × 100 |
| t_high, t_low | open time of the 5m bar with the day high / low (first occurrence) |
| low_first | True if the low came before the high |
| body_ratio | \|close − open\| / (high − low) |
| day_type | TREND if body_ratio ≥ 0.6, RANGE if ≤ 0.3, else MIXED |
| first8h_range_pct | max high / min low − 1 over the 5m bars 00:00 … 07:55 |
| prior_close_pos | (pdc − pdl) / (pdh − pdl) |

**Prior-day and 7-day levels**

| Column | Meaning |
|---|---|
| pdh, pdl, pdc | prior day high / low / close |
| d7h, d7l | high / low of the 7 full prior days |

**A1 extreme oracle**

| Column | Meaning |
|---|---|
| a1_long_entry_t / a1_long_entry | best long: the 5m low it buys at (bar i) |
| a1_long_exit_t / a1_long_exit | the later 5m high it sells at (bar j > i) |
| a1_long_gross_pct | gross % of the best long |
| a1_long_net_fut_pct | gross − 0.092 |
| a1_long_net_spot_pct | gross − 0.17 |
| a1_short_* | the same for the short: sell at a 5m high, cover at a later 5m low |

**Distances to levels**

| Column | Meaning |
|---|---|
| dist_{low,high}_round_pct | \|price − nearest round thousand\| / price × 100 |
| dist_{low,high}_{pdh,pdl,d7h,d7l}_pct | \|price − level\| / level × 100 |

## oracle_tf.parquet: one row per (day, tf); tf ∈ 5m, 15m, 30m, 1h, 4h (1,365 rows)

**Price points.** The price points are the day open, then every bar close: n_points = bars + 1. A point's time is the moment its price is known: 00:00, then each bar's close time.

| Column | Meaning |
|---|---|
| n_points | the number of price points |
| a2_long_gross_pct, a2_long_entry_t, a2_long_exit_t | best single close-to-close long |
| a2_short_* | the same for the short |
| a3_FUT_total_pct, a3_FUT_n_trades | max sum of non-overlapping long / short trades, cost 0.046% per side, and the number of trades in that set |
| a3_SPOT_* | the same for longs only, cost 0.085% per side |
| a3_FUT_MAKER_* | the same at 0.028% per side (sensitivity) |

## oracle_trades.parquet: every trade of the optimal FUT and SPOT sets (43,863 rows)

| Column | Meaning |
|---|---|
| date, tf, mode, side | the day, the timeframe, FUT or SPOT, long or short |
| entry_time, entry_px, exit_time, exit_px | price-point times and prices |
| bars | exit point − entry point |
| gross_pct, net_pct | net = gross − 2 × the cost per side |
| mae_pct, mfe_pct | worst / best 5m excursion over the bars with open time in [entry_time, exit_time). MAE < 0 means the price never went against the trade |

## sweep_events.parquet: one row per (15m bar, level) sweep-reclaim (8,150 rows)

| Column | Meaning |
|---|---|
| date, bar_time | the day and the 15m sweep bar |
| side | **bull:** low < level < close. **bear:** close < level < high |
| level_type, level | round, pdh, pdl, d7h or d7l; the level price |
| depth_pct | how far the wick went past the level |
| new_extreme | the bar or the previous bar (same day) set a new day low (bull) or high (bear) |
| confirmed | the H2′-c confirmation: the first of the next 2 bars that closes in the trade direction, with the extreme holding |
| confirm_time | the time of that confirming bar |
| mfe_to_eod_pct, mae_to_eod_pct | from the sweep-bar close to the day's end |
| ret_to_close_pct | to the day close, signed in the trade direction |
| extreme_held | no later bar of the day went beyond the sweep extreme |
| is_day_extreme | the sweep extreme is the day low (bull) or high (bear) |

## Part B (formula v1)

| File | Contents |
|---|---|
| v1_trades.csv | every trade: variant, date, sweep_time, entry_time, side, entry_px, sl, tp, R_pct, exit_time, exit_px, reason (SL, SL_gap, TP, TP_gap, EOD), gross_pct, net_pct |
| v1_daily.csv | every one of the 272 statistic days × variant, with zeros on days without a trade; oracle_fut15_pct = the A3 FUT 15m total of that day |
| v1_monthly.csv | month × variant: trades, wins, net_pct, oracle_fut15_pct |
| V1_RESULTS.json | the summary per variant, the random-control figures and the four pass checks |
