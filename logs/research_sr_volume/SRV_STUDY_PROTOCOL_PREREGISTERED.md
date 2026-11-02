# Big-timeframe levels, volume at levels, and what happens after a break (pre-registered)

Written and SHA256-locked before any result is computed. Code: `src/research/sr_volume_study.py`.
This is a measurement study only. No model or trading rule is fitted. Nothing is deployed. No GitHub action.

## The user's hypotheses (tested as stated)
- **H1:** Higher-timeframe levels (1M, 6-month, 1-year) are stronger, i.e. less likely to break than 1h/4h/1d levels.
- **H2:** Levels where much volume accumulated are targeted, i.e. break more often.
- **H3 ("reverse calculation"):** after a HIGH-volume support break, price falls a bit more and then RECLAIMS the level. After a high-volume resistance break, price falls back.
- **H4 (direction signal):** a support break leads to further falling and a resistance break to rising. A bigger-timeframe break gives a stronger signal.
- **Conflict:** H3 and H4 predict opposite things after a break. The data decides.

## Data
- **Coins:** BTC, ETH, BNB, XRP, DOGE, ADA, SOL, LINK, AVAX, TRX (USDT spot, SHA-verified `data/universe_all` 1h and 1d).
- **Period:** warm-up from 2020-01. Events are counted from 2021-01-01 to 2026-09-30.

## Level families
- **Evaluated on 1h bars** (ATR = 14 × 1h; outcome horizon H = 48 bars; forward return F = 24 bars):
  - **P1h:** swing levels of 1h bars (k = 3).
  - **P4h:** swing levels of 4h bars (k = 3). Active from the first 1h bar after the confirming 4h bar closes.
- **Evaluated on 1d bars** (ATR = 14 × 1d; H = 30; F = 10):
  - **P1d, P1w:** swing levels of 1d / 1w bars (k = 3).
  - **P1M:** swing levels of month bars (k = 2).
  - **R30, R90, R180, R365:** the lowest low / highest high of the previous N days (not including today).
- **Range events:** one event on day j when low[j] ≤ the previous-N-day low while low[j−1] was above its own previous-N-day low (a fresh touch). Highs are treated the same way.
- **Swing level validity:** the level must be on the right side of the last eval close when it becomes known (resistance above, support below).
- **CONTROL** (swing families only): highs/lows of random NON-swing bars of the same timeframe (numpy seed 11), same count, same activation rule.

## Outcomes
**At the first touch (bar j):**
- BREAK = price goes ≥ 1 ATR beyond the level first. This includes the touch bar.
- BOUNCE = price comes back ≥ 1 ATR from the level first, from bar j+1.
- Same-bar = ambiguous (excluded); none within H = timeout (excluded).
- **Break rate** = BREAK / (BREAK + BOUNCE).

**After a BREAK at bar b:**
- CONTINUE = price goes 1 more ATR beyond (L ∓ 2 ATR) first.
- RECLAIM = price comes back to the level L first.
- If bar b itself is already 2 ATR beyond → CONTINUE.
- **Reclaim rate** = RECLAIM / (RECLAIM + CONTINUE).

**Forward return after a break:** close[b+F] / close[b] − 1, minus the average F-bar return of all bars (same coins and period).

**Volume at the level (VAP share), at the touch:**
- The share of USDT volume in the previous window that traded through a band of ±0.25 ATR around L.
- Window: 168 hours for 1h-evaluated families, 90 days (of 1h bars) for 1d-evaluated families.
- Bars are split into terciles (low / mid / high) within each family. Terciles use full-sample thresholds; this is a description, not a trading rule.

## Analyses (all with 95 % month-block bootstrap CIs, 2000 reps)
- **A1 (H1):** break rate per family. REAL − CONTROL for swing families. R365 − R30 and P1M − P1d.
- **A2 (H2):** break rate, high-VAP tercile − low-VAP tercile, per family.
- **A3 (H3):** reclaim rate per family. High-VAP − low-VAP tercile, per family and side.
- **A4 (H4):** forward excess return after breaks, per family and side, for all breaks and for high-VAP breaks.

## Interpretation rules (fixed)
- A finding counts only if its CI excludes 0.
- Many cells are tested, so an isolated significant cell is reported as weak. A pattern is believed only if it has the same sign across most families.
- Nothing becomes a trading rule from this study. A promising pattern goes to a separate pre-registered test with costs, 2018–19 data and the forward log.

## Verification
`src/audits/verify_sr_volume_study.py`:
- re-derives 300 random events (touch, outcome, aftermath, forward return, VAP share) with plain loops;
- recomputes the family break rates from the event table.
