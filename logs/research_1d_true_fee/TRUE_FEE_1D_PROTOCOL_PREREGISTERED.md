# 1D (F7 RS, the deployed 1D strategy) with the true Binance fee: re-run. Pre-registered 2026-10-25

This protocol is locked with SHA256 before any number of this re-run is computed. It is a research re-run: nothing live changes from this file.

## Why

- The 1D research and its forward recorders (Step 16, 16B, F4, E11) assume a 0.25% spot fill and a 0.10% perp fill per side.
- The fee truth (`deploy/fees.json` v1, fee amendment 2d9d1485) is lower. With BNB plus the measured impact it is 0.085% spot and 0.046% perp taker per side.
- The user asked for the true fee everywhere. F4's day-90 gate D3 compares live with the F7 backtest, so the backtest reference must be re-made with the same costs before the recorders change.

## Method

- **Engine:** `src/pipeline_1d/f7_run.py` (`load`, `run`) and `f7_risk.sim_ls`, unchanged and imported. The output folder is redirected to `logs/research_1d_true_fee/`, so the locked F7 files are never written.
- **R0 (reproduction gate):** the F7 RS run with the original costs (C_LONG 0.0025, C_SHORT 0.0010, RS rules). Its daily equity must equal `logs/strategy_f7_risk/equity_MAIN_AI_RS.csv` in every cell within 1e-6. If not: INVALID, stop.
- **R1 (true fee):** the same run with C_LONG = 0.00085 and C_SHORT = 0.00046.
  - The stop slippage of 1% is **unchanged**: it is a slippage assumption, not a fee, and its truth is not measured yet.
- **R2 (information):** the long-only line (inv_s = 0) at both cost levels, i.e. the 16B paper analogue.

## Report

For R0, R1 and the LO lines, on the M_AI3 mix and the D1 / H4 / H1 sleeves:
- MAIN-window final, CAGR, max drawdown and Calmar;
- calendar-year returns;
- the sub-window 2025-10-01 … end (the ECO P3 year);
- the cost share: (R1 − R0) final equity.

## Not decided here

- **The forward-recorder amendment** (16B, F4, E11 to the true fee, plus a new D3 reference = the R1 equity) is written after this report, with its own lock.
- No gate is computed here.

## Verifier

`src/audits/verify_1d_true_fee.py`, own code:
- (1) the R0 equity file == the locked F7 file, by a csv loop;
- (2) the R1 / R0 stats recomputed from the saved equity files (CAGR, max drawdown, year returns) by loops;
- (3) the SHAs of the output files.
