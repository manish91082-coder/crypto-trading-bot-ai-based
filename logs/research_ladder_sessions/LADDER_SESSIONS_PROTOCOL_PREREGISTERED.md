# Ladder (सीढ़ी) structure + sessions: descriptive study (pre-registered, 2026-10-17)

This file is locked with SHA256 before any result is computed. It is a descriptive research study only: no trading rule, no AI training, no orders. Every change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.

## Data (already verified)
- **Swings:** `data/derived/swing_anatomy/legs_all.parquet`, SHA256 `bbe7a4fd…0f8f0f` (matches `claims_phase1.json`).
  - 10 coins (BTC ETH BNB SOL XRP ADA DOGE DOT LTC LINK), period 2017-08..2026-09.
  - Primary K = 3; K = 2 and K = 4 are robustness checks.
- **Timeframes:**
  - 5m, 15m, 1h, 4h, 1D and 1W are analysed.
  - 1M is shown in tables only (59 legs at K = 3 is too few for inference).
- **Sessions:** raw 1h candles in `data/universe_all/1h/<coin>_1h_full.csv.gz`, same 10 coins, 2020-01-01..2026-09-30, UTC.
- `archive/` is not used.

## A. Ladder structure (per coin and timeframe, legs sorted by `start_time`)
1. **Swing points.**
   - The end of a Rally leg is a swing High (H); the end of a Decline leg is a swing Low (L).
   - Each H is labelled HH if its price is above the previous H, otherwise LH.
   - Each L is labelled HL if its price is above the previous L, otherwise LL.
2. **State at each swing point** (latest H label + latest L label):
   - **UP ladder** = HH & HL
   - **DOWN ladder** = LH & LL
   - **CONTRACTION** = LH & HL
   - **EXPANSION** = HH & LL
3. **Ladder runs.**
   - A run is a maximal block of consecutive swing points in the UP state (or the DOWN state).
   - **Steps** = number of rally legs (UP) or decline legs (DOWN) whose end lies inside the run.
   - Report: state shares (time-weighted by bars and by count), the run-length distribution (1, 2, 3, 4, 5+ steps), and the median steps.
4. **Pullback depth (retracement).**
   - Inside UP runs: the size of each decline leg ÷ the size of the rally leg before it, in price terms. Inside DOWN runs, the mirror image.
   - Report median and quartiles, plus bins 0–0.236, 0.236–0.382, 0.382–0.5, 0.5–0.618, 0.618–0.786, 0.786–1.0.
   - **Fibonacci test (fixed now):** the share of ratios within ±0.02 of 0.382, 0.5 and 0.618 is compared with the average share within ±0.02 of the control points 0.30, 0.44, 0.56 and 0.70.
     - Claim "Fibonacci clustering" only if the fib share is above the control share with a 95% bootstrap CI (resampled by coin-year block) that excludes 0, on at least 4 of 6 timeframes.
5. **Ladder style (runs with ≥ 3 steps).**
   - First half vs second half of the run, mean retracement and mean leg size (in ATR):
     - **ACCELERATING:** retracements smaller and legs bigger in the second half
     - **DECELERATING:** retracements bigger and legs smaller
     - **STEADY:** both changes are within ±10%
     - otherwise **MIXED**
   - 1-step runs are called **V/impulse**.
6. **How a ladder ends.** For each UP run, which comes first after the last HH: an LH (lower high) or an LL (break of structure)? Report the shares; the mirror case is reported for DOWN runs.
7. **Step continuation (descriptive, NOT a tradable rule).**
   - Inside an UP run with k completed steps (k = 1..5), the share of cases where the next swing high is an HH. The mirror case is reported for DOWN runs.
   - **Caveat (must be stated):** labels are known only after the swing's `confirm_time`.
8. **Double top / bottom.**
   - Two consecutive swing highs (or lows) within 0.5 × ATR of each other, using `atr_start` of the second leg.
   - Report the frequency, and the share of cases where the next swing low is an LL (for tops) or the next swing high is an HH (for bottoms), vs the unconditional share.

## B. Sessions (raw 1h, UTC)
- **Session windows:** Asia 00–08, Europe 08–13, US 13–21, Late-US 21–24, all UTC.
- **Per session and coin:**
  - mean log return (bps per session);
  - median |return|;
  - share of the day's total |1h return| sum;
  - share of daily highs and daily lows formed in each session (hour of the UTC day's max high and min low).
- **Splits:**
  - (i) period 2020–2023 vs 2024-01..2026-09;
  - (ii) weekday vs weekend;
  - (iii) daily structure state, taken from the 1D K = 3 swings using only swings with `confirm_time` ≤ that day's 00:00 UTC (causal): UP / DOWN / other.
- **Statistical rule:** a session effect on returns is called "consistent" only if:
  - its 95% bootstrap CI (resampled by day, 2,000 draws, seed 20261017) on the pooled 10 coins excludes 0, **and**
  - it has the same sign in both periods.

  Everything else is reported as "not proven".
- **1h swing extremes:** share of 1h K = 3 swing highs and lows (`end_time` hour) by session, vs the uniform expectation (hours-in-session ÷ 24).

## Outputs
- All outputs go to `logs/research_ladder_sessions/` as CSV tables, plus `claims_ladder_sessions.json`.
- Report in Hindi.

## Verifier (separate code)
`src/audits/verify_ladder_sessions.py` recomputes the following with its own simple loops and must match:
1. For BTC and ETH on 4h and 1D (K = 3): HH/LH/HL/LL counts and state shares, exactly.
2. Retracement medians for those cells, within 1e-9.
3. BTC session mean returns and daily-high/low session shares from the raw 1h file, within 1e-9.
4. The JSON claims against the CSV tables.

## Honest limits (fixed in advance)
- This is description, not prediction. Swing labels are known only after confirmation (~57% of a swing is done by then, from Phase 1).
- 10 large coins only.
- The 2025-10..2026-09 data has already been seen in earlier work.
