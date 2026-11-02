# Step 9 — same AI test as Step 8, with MORE INFORMATION (pre-registered 2026-10-13, before any Step 9 result)

Only change vs Step 8: extra causal features from 1-hour Binance klines (still 1D trading, decisions at the daily close;
no 4H/1H trading module). Everything else (30-coin point-in-time universe, labels, models, monthly re-training, trading
policy, risk layer, skill gates G1/G2/G3, decision rule, anti-false-claim rules) is IDENTICAL to Step 8
(STEP8_PROTOCOL_PREREGISTERED.md sha256 62047cb3...).

## Data (evidence rules)
* 1h klines, all 12 columns, 30 coins, 2020-01..2026-09, Binance Vision monthly files, each zip SHA256-verified against
  Binance's .CHECKSUM; timestamps auto-detected (ms / us).  The local data/raw/*_1h/15m files are NOT used: they start
  2021-10 and every row from 2025-01-01 has a corrupted timestamp (e.g. year 56971).
* Cross-check against the verified 1D files for every coin-day: first 1h open == 1D open, max high == 1D high,
  min low == 1D low, last close == 1D close, sum volume == 1D volume (rtol 1e-6). Mismatches are counted and reported;
  features of a mismatching day are set to missing (never silently used).

## New features (day t uses only the 24 hours of day t and earlier days -> known at the daily close)
order flow : taker_buy_ratio (taker buy base / volume), its 5-day mean, change vs 5-day mean, taker ratio of the last
             4 hours, trades / 30-day mean trades, average trade size / 30-day mean
intraday   : close position in the day's range, last-4h return, last-4h volume share, std of hourly returns,
             max intraday drawdown from the running high, hour of the day's high, hour of the day's low
Entry brain: Step 8 features + all new features. Exit brain: Step 8 exit features + all new features.

## Gates and decision: exactly Step 8 (AUC >= 0.55, CI low > 0.50, > shuffled control, top quintile > bottom;
portfolio Calmar > baseline and > control). FAIL = nothing deployed.
