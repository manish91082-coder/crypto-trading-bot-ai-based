# A1 correction (A0 amendment 2, 1b49a9de…): S-LAD and S-DTB from REAL-TIME pivots

**Code:** `src/research/r2_realtime_pivots.py`, `src/research/r2_a1_correction.py`. The original A1 files are kept unchanged.

## What changed, trade by trade (`signal_diff.csv`)
- **2,374 swing trades are identical.** Same coin, side and entry time; gross R equal, except 1 (see below).
- **20 new trades at pivots that were confirmed live but FAILED later.** The final pivot list (hindsight) had dropped them. S-LAD: 15; S-DTB: 5. Mean gross about −0.6 to −0.9 R; most are −1.0 R (the stop beyond the failed pivot).
- **6 timing corrections + 1 spurious old signal + 1 changed gross**, all within 12 days of a SAME-CANDLE pivot tie.
  - `legs_all` has 114 legs on 4h (1.5%) that share their `start_time` with another leg; that is, two pivots fall on one candle.
  - Sorting by `start_time` scrambles them, so `ladder_sessions.points` linked labels and known times to the wrong pivot. Example: BTC L 58,700 was confirmed live on 2024-02-29 08:00, but the old table says 2024-03-05 20:00.
  - The real-time event order (`seq`) is correct.
  - The shares on other timeframes are 1h 1.56%, 15m 1.13%, 5m 1.07% and 1D 3.27%. This affects the ladder study S5 and S6 slightly; see the errata index.

## Effect on A1 (`A1c_vs_A1.csv`; gate rule unchanged; all 8 signal-sides still PASS)
| Signal | Original mean net R | Corrected mean net R | Corrected CI |
|---|---|---|---|
| S-LAD long | 0.134 | 0.128 | 0.064 to 0.192 |
| S-LAD short | 0.062 | 0.053 | **−0.008** to 0.115 (now touches 0) |
| S-DTB long | 0.068 | 0.068 | — |
| S-DTB short | 0.070 | 0.046 | — |
| S-BRK, S-TRD | unchanged | — | — |

**From now on, A2 and A3 use `a1c_trades.parquet`.**
