# A4 changes after the protocol lock (caf7dcee…)

## 1. 2026-10-19: the cost-stress gate was computed only for a "V0 taker" final config
- **What happened.** In the first run the pre-registered entry rule adopted MAKER, by a small margin: dev Calmar 0.797 vs 0.789, P1 0.717 vs 0.714, P2 1.722 vs 1.716. The cost / slippage stresses were coded only for V0 taker, so they were `None`, and the gate was reported FAIL by a coding artefact.
- **Fix.** The 1.5× fee, 2× fee and 0.3% stop-slippage stresses now run on the FINAL config. A `scale` factor multiplies ALL fees, including the maker fee, as the protocol says ("1.5× and 2× fees").
- **Nothing else changed.** The re-run is deterministic: grid, selection, PBO, random-entry control and DSR are recomputed identically. First-run stdout: `a4_stdout_run1.txt`.

## 2. 2026-10-19: verifier MTM indexing (verifier only)
- **What happened.** The verifier looked up 4h lows by timestamp and failed on the single missing 4h bar of the data (2020-02-19 16:00 UTC, Binance outage; it is the only gap in all 10 coins).
- **The convention used everywhere.** The study, S6 and A1 all index the holding period by BAR COUNT (exit_time = entry + (exit_idx + 1) × 4h). Only 1 S-LAD long trade (ETH) spans that gap, so the effect is negligible.
- **Fix.** The verifier now uses the same bar-index convention.

## 3. 2026-10-19: PBO ranking made robust to floating-point ties (study + verifier)
- **What the verifier showed.** Its own monthly-return matrix equals the study's to 3e-16, and all 6 portfolios are equal (final and DD to 1e-6). Yet PBO came out 0.8789 vs 0.8697.
- **Cause.** Some configs share almost all of their trades (e.g. 3_120 and 3_1000), so their block Sharpe ratios tie. Ties sit exactly at the median rank, where logit = 0. A 1e-16 difference breaks the tie either way and flips the "< 0" test for some combinations.
- **Fix.** The Sharpe ratios are rounded to 12 decimals before ranking, in both programs.
- **The verdict cannot change:** both values are far above the 0.30 gate.
- A4 was re-run with this change; the first two run logs are kept.
