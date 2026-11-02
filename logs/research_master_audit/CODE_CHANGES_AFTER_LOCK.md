# Changes after the protocol lock (554f13fd…)

- **Study code** `src/research/master_audit_portfolio.py`: written after the lock and run once. There were no edits after the first run, and no grid was added or dropped.
- **Verifier** `src/audits/verify_master_audit.py`: also written after the lock.
  - Its Part A rounding rule is strict: the source value, rounded to the master's printed precision, must equal the printed value. Two checks FAIL under it:
    - **4h long p05 V0:** the source is -0.9046, so the printed value should be -0.90; the master prints -0.91. This is a real but cosmetic erratum.
    - **1D cost / median move:** the source table stores 0.0365, which is already rounded to 4 decimals, and the master prints 3.7%. Whether it rounds to 3.6 or 3.7 cannot be decided from the stored value, so this is a rounding edge, not an error.
  - The verifier imports `prepare()` from the study module to obtain the real-funding net R. Two parts are its own independent code:
    - the funding recomputation (pandas masks, 300 random trades);
    - the portfolio loop.

## 2026-10-19: verifier exit code
- **Problem.** `verify_master_audit.py` printed FAIL lines but always exited 0. The final laptop regression of 2026-10-19 showed exit=0 with "FAIL 2".
- **Fix.** It now exits 1 when any check FAILs. The checks themselves are unchanged.
- **Expected result.** Exit 1, because of the 2 known rounding FAILs (4h long p05 printed −0.91 instead of −0.90; 1D cost 3.65% on a rounding edge). Both are documented in the audit report.
- **Known future change.** The A0 check of `deploy/crontab.txt` (`1525e074…`) will FAIL by design once the R2 cron lines are added to `deploy/crontab.txt`. It pins the 17-Oct version.
