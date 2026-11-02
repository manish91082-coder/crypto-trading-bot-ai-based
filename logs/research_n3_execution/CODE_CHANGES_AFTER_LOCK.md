# N3 code changes after the protocol lock

1. **X3 simulation missing from run 1 (2026-10-20).**
   - **What the protocol requires.** If the X3 funding-guard count is > 0, the delay rule must be simulated as one more configuration.
   - **What run 1 did.** It counted 3,311 triggers and added one configuration to the DSR count, but did not simulate X3. Run 1's verdict ("X2") is therefore not final.
   - **Kept as evidence.** `n3_stdout_run1_X3_missing.txt` and `claims_n3_run1_X3_missing.json`.
   - **Diagnosis, before the rerun.** Every one of the 3,311 triggers is a funding record stamped 1–43 ms after the TF bar open (e.g. 00:00:00.005), against an entry at 00:00:00.000.
     - N1's convention (funding counts when f > entry) therefore charges the bar-open funding to these entries. That is conservative.
     - A live order placed after the bar close would be filled after f and would not pay it.
   - **Implementation.** For flagged trades (perp only), the next funding payment side × rate × w is credited back at hour a + 1. This means the entry is delayed to just after f; the price change over ≤ 43 ms is ignored.
   - **Adoption rule.** The protocol's "if X1 and X2 both pass, also run their combination" is applied to every passing variant (X1, X2, X3), with the same Q1–Q2 acceptance test.
   - **Rerun.** The full N3 is rerun. Base, X1, X1s and X2 must reproduce run 1 exactly.

2. **Verifier X4 (2026-10-20).** The claims list SHA-hashes every `N3_*` file. Because Windows paths are case-insensitive, this glob also matched `n3_stdout.txt`, the run's own stdout, which was still being written when the claims were saved. Its SHA can therefore never match afterwards.
   - The verifier now skips `*stdout*` names in the SHA check. Every result file is still checked.
   - The N5 code glob was fixed in the same way before N5's first run.
   - The first verifier run (4 checks, X4 FAIL) is kept as `verify_n3_stdout_run1.txt`.
