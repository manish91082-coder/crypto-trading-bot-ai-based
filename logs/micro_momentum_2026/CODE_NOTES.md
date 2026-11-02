# Micro-momentum: code notes (written before any study number)

- 2026-10-27 ~06:47 UTC (before the run; run_log start 06:50:11): unit test on synthetic data (8,000 seconds, seed 1). At 200 random seconds, a brute-force recomputation of UPMIN, RHYTHM_60/300, STRAIGHT_60/300, VOLR_60/300, TAKER_60/300, R_60/300 and F_60 matched the vectorised code (tolerance 1e-9): True. simulate() on hand cases (time exit, user exit XU, cap and forced end) and starts() gave the hand results.
- Memory: the features are computed on demand; only UPMIN, DOWNMIN, VOLR_60, TAKER_60 and RHYTHM_60 are cached.
- The trade tables keep only gross; the net is gross − 2c per cost mode, computed in the metrics.
- Spot 1s csv has no header; futures 1m csv has one. Both are detected from the first cell.
- Random-control seed for month m and seed s = s*1000 + month number (deterministic).
- 2026-10-27 ~06:53 UTC, during the run (QC only, no study number looked at): the 205 five-minute OHLC mismatches in 2026-01 were inspected. All 205 are on the open, each exactly ±0.01 USDT (1 tick); high 2 and low 1 also differ by exactly 0.01; close 0 mismatches; volume 0 mismatches. The study uses only the 1s closes. Cause not established; reported as is (protocol §2.2: never fixed silently).
