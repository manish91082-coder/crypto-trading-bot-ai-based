# Clarifications decided while coding, BEFORE any Step 8 result existed (2026-10-13)
1. Exit-brain feature "entry probability" is DROPPED: for in-sample training rows it would be an in-sample prediction
   (leakage-like optimism). The exit brain uses only market + trade-state features.
2. Skill gates G1/G2 are measured on candidates of point-in-time universe members (the coins actually tradable that
   year); all-coin AUC is reported for information only.
3. Bootstrap CI = block bootstrap over calendar months (1,000 resamples), because same-day candidates are correlated.
4. Labels whose 30-day (entry) / 20-day (exit) window runs past a coin's last real candle (delisting) or past
   2026-09-30 are "unknown" and never used for training or scoring.
5. Exit rows exist for each candidate from its entry day up to 60 days while the 1.5 ATR catastrophic stop is not hit;
   a portfolio position looks up the exit prediction of exactly that (candidate, day) row (identical state).
