# Batch 2: code notes (written before any Batch 2 result)

**Code:** `src/research/methods_bench_b2.py`. It imports the bench (`methods_bench.py`, 46b16cd6…, unchanged) and the engine (`btc_entry_study.py`, unchanged).

1. **Implementation conventions the protocol leaves open:**
   - **Klinger:** trend_0 = +1 and cm_0 = dm_0. When cm = 0 (h = l), vf = 0, to avoid a division by zero. The start values fade out within the EMA55.
   - **EMV:** v = 0 gives inf, which is set to NaN.
   - **Amihud:** qv = 0 is treated as NaN.
   - **Volume profile:** a window whose highest high equals its lowest low gives 0.
2. **GARCH standardization.** The D-period mean and std of r (per scale) are stored in `batch2_garch_params.json` together with the fitted parameters, and used for every bar.
   - The lookahead test passes them in fixed, as the protocol states for the parameters.
   - Inside D, the GARCH values use parameters fitted on all of D (in-sample for D, as the protocol states). V and H use no data after their own bar.
3. **Smoke test (2026-10-27, before the lock was used for any number):**
   - **What was run:** signal generation only, on 2022-06…2022-12, with placeholder GARCH parameters.
   - **Signals:** 324 configurations; none all-zero.
   - **Info-bar frequency check (2022):** about 44 volume bars and 7.6 imbalance bars per day.
   - **Not computed:** no trade, metric or gate.
4. **Gate phase:** the gate phase runs in 3 worker processes (protocol §9). The results are put back in the configuration order before the merge, so the outputs are identical to a sequential loop.
