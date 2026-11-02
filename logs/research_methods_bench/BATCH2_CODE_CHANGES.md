# Batch 2: changes and pre-run records

- **2026-10-27 02:17 UTC, the first `lookahead` stage, before any metric:**
  - **What went wrong.** The GARCH and GJR fits stopped at their start values on 15m, 1h and 4h. The 1h fit only failed inside the full run; it moved in a separate debug call. SLSQP reported "success" at iteration 0.
  - **The cause.** On the total negative log-likelihood the 15m gradient was ~3e5, so SLSQP's line search ended at the start point.
  - **The stage was stopped.** The params file is kept as `batch2_garch_params_REJECTED_unscaled.json` and is not used.
- **Fix:** the objective is now the **mean** negative log-likelihood (total / n). This has the same argmin, so it is the same Gaussian ML estimator as in protocol §3. maxiter is 1000 and ftol 1e-12.
- **Refit result:** every model on every scale moved off its start and reports success.
  - The GARCH 15m fit lies on the stationarity bound (α + β = 0.9999, an integrated GARCH). This is allowed by the protocol's constraint and stated here.
  - EGARCH, which had already moved, gives the same parameters as before.
- **No other change.** The lookahead stage was then run again from the start.
- **2026-10-27 ~02:45 UTC, before any metric: pre-test of verifier W2.**
  - **What was run.** The verifier's W2 part was run on its own in a scratch harness, against the signals of code cf6fd178…. It compared signal values only, with no results files.
  - **Result:** 300/300, 0 mismatches, 0 boundary cases, over 12 rules.
- **2026-10-27 02:31 UTC: lookahead test (protocol §10).**
  - **Result:** over 20 cutoffs (seed 20261027), 0 of 324 configurations differ, and no configuration has an all-zero signal. Log: `run_log_batch2.txt`.
  - **Run start:** the full `batch2` stage then started on code cf6fd178….
