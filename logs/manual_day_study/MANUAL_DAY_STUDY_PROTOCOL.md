# Manual (AI-reasoned) study of 10 random BTC days: perfect direction, entry and exit, and the formula behind them. Locked 2026-10-26

This method is locked with SHA256 before any day is chosen or viewed. It does **not** touch the running methods bench (Batch 1).

## What the user asked (2026-10-26)

- Take 10 random days and the BTC candles of every available timeframe for each.
- Work out the perfect entry, exit and direction by direct reasoning, not by a script, trying every combination.
- Reverse-engineer the formula.
- Log every step, with ground evidence and no hallucination.

## Honesty rules (fixed now)

1. **Two different things are recorded for every day, and kept apart:**
   - (a) **Hindsight-perfect.** The best long and short trade of the day: entry at the day's low or high, exit at the opposite extreme. This needs knowledge of the future, so it is not a strategy.
   - (b) **Knowable at the time.** For every candidate rule, I only look at candles that were already closed when the entry would have happened, and record whether that rule would have caught the move in real time.
2. **A formula from 10 days is a hypothesis, not a result.** It is written down as a pre-registered rule and is only accepted after testing on hundreds of unseen days, through the bench discipline.
3. **Code is used only to:**
   - draw the 10 days with a recorded seed;
   - print raw candles;
   - check every number I compute (calculator role) at the end of each day's log.
   - All reasoning is mine and is written in the log before the arithmetic check runs.

## Days

- seed 20261026, numpy `default_rng`.
- 10 distinct days drawn uniformly from 2020-01-08 … 2026-09-29. This leaves room for a week of history before and the day after.

## Data per day

**Verified sources:**
- `data/universe_hf/5m` (SHA 657844920c9b…) → 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, aggregated by UTC clock;
- `data/universe_hf/15m`;
- `data/raw/BTCUSDT_1d_Raw_5Years.csv`, cross-checked against `data/universe_all/1d` → 1d, and 1w (Monday start), 1M and 1y aggregated.

**1m:** from `archive/cleanup_2026_10_15/data/raw/BTCUSDT_1m_Raw_5Years.csv` (the user-allowed raw exception).
- Only for days in 2021-10-01 … 2024-12-31, because later timestamps are corrupt.
- Only after its 5m aggregation matches the verified 5m for that day.

**Context shown before the day:** the last 7 daily candles, the last 4 weekly candles, the last 3 monthly candles, and the year so far.

## Recorded per day (in `logs/manual_day_study/day_XX_<date>.md`)

1. **Context** that was known at 00:00 UTC.
2. **The day's path** on every timeframe.
3. **Hindsight-perfect long and short:** entry time and price, exit time and price, gross %, net % after `deploy/fees.json` (futures taker 0.092% round trip; spot 0.17%).
4. **For each candidate entry rule:**
   - when it would have fired, using only closed candles;
   - its entry, exit and net;
   - how far it was from the perfect entry (minutes and %).
5. **My reasoning step by step**, then the arithmetic check output.

## After 10 days

- A synthesis: which features were present before the good entries, and on how many of the 10 days.
- The candidate formula(s), written as exact rules.
- The list of what must be tested before any formula can be trusted.
