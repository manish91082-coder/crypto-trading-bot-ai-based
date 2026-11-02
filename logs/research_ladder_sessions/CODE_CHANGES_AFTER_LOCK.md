# Code/analysis changes after the protocol lock (e7ae067d…)

## 1. 2026-10-17: two post-lock diagnostics (`src/research/ladder_sessions_postlock.py`)
These were added **after** the results were seen. They do not change any pre-registered number or verdict, and they are reported separately as post-hoc.

**P1 Fibonacci.**
- *Problem:* the pre-registered control points (0.30, 0.44, 0.56, 0.70) are not matched to the density of the data. 0.30 sits in the low-density tail, while 0.5 and 0.618 sit near the mode. The pre-registered test therefore favours the Fibonacci levels.
- *Diagnostic:* each Fibonacci level's ±0.02 share is compared with a local density null, defined as the ±0.06 share ÷ 3.
- *Result:* no level is clearly above its local density (ratio 0.98–1.05 on 5m–1h; z < 2 in all 18 cells).

**P2 Daily high/low hour.**
- *Problem:* for a random walk the time of the day's extreme follows the arcsine law, so a uniform null is wrong.
- *Diagnostic:* the arcsine-law session shares are added as the null.
- *Result:* Asia and Europe match that null. US shows more extremes than the null, and Late-US shows fewer.

**Pre-registered verdicts stay as computed:**
- `fibonacci_clustering = True`, from 4 of 6 timeframes;
- all four sessions "not proven".

The report must show both the pre-registered verdict and the diagnostic.
