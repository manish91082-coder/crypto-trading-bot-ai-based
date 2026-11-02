# T14 code notes
- `src/research/r2_t14_model.py` was generated mechanically from `r2_a3_brain.main`. The only substitutions:
  - the protocol check (T14, plus the A3 protocol SHA pinned);
  - DSR N trials 5 -> 14;
  - the verdict text and the output file names.
- The data paths are set by overriding `A3.STORE`, `A3.A1C` and `A3.OUT`. Every function is imported unchanged.

## Verifier change after the model run (2026-10-20)
- `verify_r2_t14.py` check 1 crashed (IndexError) on its first sampled row: a newly listed coin had < 2 legs at T. The verifier now gives NaN there, the same rule as `r2_a2_store.swing_feats_from_list` (the 10 A2 coins never had this case). No study code or result changed; the first verifier output is kept as `verify_t14_stdout_run1_crash.txt`.
