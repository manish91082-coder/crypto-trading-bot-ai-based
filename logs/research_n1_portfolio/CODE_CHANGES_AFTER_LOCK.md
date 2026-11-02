# N1 code changes after the protocol lock

1. **Crash fix, run 1 (2026-10-20).** The run stopped at configuration K4 (without D) with `AttributeError: 'DataFrame' object has no attribute 'w'`.
   - **Cause.** The weight column `w` exists only on D trades. When D is excluded, the concatenated ledger has no `w` column, and `base_w` read it unconditionally.
   - **Fix.** `base_w` now reads `w` only when D rows exist. No logic changed.
   - **Rerun.** The full run was repeated from the start; the simulation is deterministic.
   - **Evidence.** The run-1 log, which stops after K3, is kept as `n1_stdout_run1_crash_K4.txt`. Its K0–K3 lines must equal those of run 2, and this is checked after run 2.

2. **Crash fix, run 2 (2026-10-20).** Run 2 completed every configuration, the selection and the 100 random-entry portfolios, then stopped in G7 (2018–19). The error was `IndexError: arrays used as indices must be of integer type` in `run_pf`.
   - **Cause.** `run_pf` received hour indices a/E that were not integers. These come from concatenating the G7 ledger with the D ledger.
   - **Fix.** `run_pf` casts a/E to int64, nofund to bool and fee to float (the first test showed that `nofund` was also object-typed). No logic changed.
   - **Check.** Before the full rerun, G7 alone was executed once to confirm that it runs; its numbers were not printed. The full run is then repeated from the start (deterministic).
   - **Evidence.** The run-2 log is kept as `n1_stdout_run2_crash_G7.txt`. Its config, selection and random lines must equal those of run 3.
