# TFX-S: saturation audit of the TFX research (pre-registered 2026-10-20, before any S-measurement is computed)

**Scope.** The user asked to saturate today's research (`RESEARCH_COLLECTIVE_BRAIN_SATURATION_20_OCT_2026.md`, TFX). That means repeated rounds of audit → measure → integrate, until no new finding changes a conclusion. It covers errors, gaps, add-ons, improvements and enhancements, on a mathematical scale, in the same discipline.

This is descriptive and not an A0 trial. It reuses the verified TFX trade files (`data/derived/tf_edge_map`, `claims_tfx.json` cells_sha 055621f5… after run 2). Nothing in TFX is changed.

## Round-1 audit findings that motivate the measurements (found by reading, before any S-measurement)

| # | Finding | Type |
|---|---|---|
| A1 | **Report error:** "5m–30m … maker पर भी घाटे में" is false. The TFX table already shows net_maker_dev > 0 for several long cells (e.g. 15m EMAX long +0.149%, 15m RSI long +0.128%, 30m EMAX long +0.344%). No CI was computed for maker. | Material (wording / conclusion) |
| A2 | **Report arithmetic:** S_combo for ρ = 0.20, K = 6 was written ×1.89; correct √(6/2) = ×1.73. K = 6, ρ = 0.90 is ×1.044, written ×1.05. | Minor |
| A3 | **CI dependence:** coin-year blocks treat coins as independent, but crypto coins co-move strongly in time, so the CIs are likely too narrow. Time blocks (calendar month, all coins together) are needed. | Possibly material |
| A4 | **Heavy tails:** means can be driven by a few pumps (U2) or a few long trades (1D/1W). Robust statistics are needed. | Possibly material |
| A5 | **Alt costs understated:** the cost model is 0.054%/side for every coin. Measured spot half-spreads (Step 2 snapshots) are larger for alts (e.g. ADA ≈ 2.2 bps vs BTC ≈ 0). A cost stress is needed. | Possibly material |
| A6 | **One regime switch:** the "regime decides side" claim rests on one P3 year. A per-calendar-year breakdown is needed. | Possibly material |
| A7 | **Correlations never measured:** the design math (S_combo, "add a brain only if ρ < 0.5") was never fed with measured ρ between sleeves (TF × family × side). | Gap |
| A8 | **No effective trial count:** the "cells count in a later DSR" rule has no formula. | Gap |
| A9 | **Survivorship (U2):** the candidate list is today's coins. Delisted coins that crashed are missing, which biases U2 longs up and shorts down. Stated, not fixed. | Limitation |
| A10 | **Maker both sides:** maker on entry and exit at the bar open is optimistic (adverse selection, non-fills; A4 measured 96.6% entry fill with a 1-h window). | Limitation |

## S-measurements

Universes:
- U1;
- U2 locked;
- U2-posthoc (excluding LUNAUSDT and STRAXUSDT).

dev = P1 + P2 unless stated. Seed 20261021.

### S1 Time-block bootstrap
For every cell with n_dev ≥ 30:
- resample calendar-month blocks, with all coins of a month together, 2,000 draws;
- 95% CI and Bonferroni CI (normal approximation with the bootstrap SE; N = the cells of that universe, as in TFX);
- for net_taker, net_maker, net_spot (long cells) and excess.

The readings are re-derived with the TFX rules, using month blocks in place of coin-year blocks. Report every reading that changes.

### S2 Robust statistics
Per cell:
- median excess;
- 5% two-sided trimmed mean of excess and of net_taker;
- the share of the cell's total net_taker P&L that comes from its top 1% of trades.

### S3 Cost stress
- net at 2× taker: gross − 0.00216 − funding;
- break-even round-trip cost = mean(gross − funding);
- reading COST-VIABLE-2X: month-block CI low > 0, with P1 > 0 and P2 > 0.

### S4 Maker
The S1 month-block CI for net_maker, plus its P1, P2 and P3 means.
- Reading MAKER-VIABLE: month-block CI low > 0, with P1 > 0 and P2 > 0.
- The report must carry the A10 caveat.

### S5 Per calendar year
For TFs {30m, 1h, 4h, 8h, 12h, 1D} and the trend group {TSMOM, EMAX, MACD, DONCH} pooled, per side and per year 2020 … 2026 (entry year):
- mean net_taker;
- mean excess;
- n.

Plus:
- the BTC calendar-year return (1D closes, `universe_hf` 5m resampled);
- the Spearman correlation across years between the BTC yearly return and the (long − short) mean net, per TF;
- the share of years in which excess > 0, per side and TF.

### S6 Sleeve series and correlations
- **Sleeve:** (universe, TF, family, side).
- **Monthly realized series:** for each sleeve, month m value = Σ net_taker of trades **exiting** in m ÷ the number of coins eligible in m (U1: coins with data; U2: coins with ≥ 1 liquid day). These are realized-P&L series, not MTM; 1D/1W lumps are expected.
- **Per sleeve (dev months):** mean, SD, annualised Sharpe = √12 · mean / SD, and the maximum drawdown of the cumulative sum.
- **Correlation matrices** (dev months, pairwise complete, ≥ 24 common months):
  - (a) the same family and side across TFs;
  - (b) long vs short, the same TF and family;
  - (c) trend vs MR, the same TF;
  - (d) U1 trend long vs U2-posthoc trend short.
- **Effective number of independent sleeves:** N_eff = (Σλ)² / Σλ² of the correlation matrix of all U1 sleeves with ≥ 24 dev months (eigenvalues λ). The same for the trend-only sleeves at 1h–1D.
- **No combined portfolio is computed here.** That is N1, a separate trial.

### S7 Effective trial count for TFX
N_eff (S6 formula) over all cells with n_dev ≥ 30, per universe. It is recorded as the multiple-testing count any later trial that picks a TFX cell must add to its DSR N.

### S8 Report audit
Every number in sections 0–8 of the report is checked against the files (scripted list plus manual). Each mismatch is listed and corrected in the report with a visible "सुधार" note.

## Saturation loop rule
After each round, the findings are classified:
- **Material:** changes the sign or label of a headline conclusion, or a recommendation (N1–N5 order or content).
- **Minor:** anything else.

Rules:
- The next round audits the new outputs and the integrated report.
- **Saturation = one full audit round with 0 material findings.**
- At most 4 rounds. If not saturated by then, the report says so and lists what remains.
- Each round's findings are logged in `logs/research_tf_edge_map/SATURATION_LOG.md`.

## Verifier (`src/audits/verify_tfx_saturation.py`, own code)
1. S1 for 3 random cells: own month-block bootstrap. The CI must be within ±10% of the CI width (Monte Carlo), and the reading must be identical; the means must be exact.
2. S2 / S3 for 5 random cells from the trade files: exact (1e-12).
3. S5: recompute 3 random (TF, side, year) means exactly, and the BTC yearly returns.
4. S6: rebuild 3 random sleeves' monthly series, Sharpe and MDD exactly; 3 random correlations; N_eff from own eigen-decomposition.
5. SHAs and the protocol lock.
