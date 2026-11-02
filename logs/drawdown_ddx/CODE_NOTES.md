# DDX code notes (written before the first full run, 2026-10-27 ~10:25 UTC)

1. **Key path fix before the first run.** Step 28 keeps its decision under `gates.decision`, not at the top level. This was found by reading the claims keys before running and was fixed in the code. No result had been produced yet.
2. **Ledger comparison ratios** (`dd_ratio_vs_comparison`, `final_ratio_vs_comparison`) use each id's first row whose role is "comparison". They are report-only (protocol §1).
3. **A16 (T19) claims hold Calmar but no drawdown.** That row records the verdict and the dev Calmar only. Its DD cells are empty on purpose.
4. **Bootstrap streams.** One parent `default_rng(20261027)` is `spawn`ed into one child per job, in this order:
   - (L = 20: ALL, P3, DEV × H 30, 90, 180, 365);
   - then (L = 5, 60: ALL, P3 × H).
   Each child draws, in order: the start indices, the jump uniforms, the fresh starts.
5. **Rolling windows** are all H-day windows of each base's daily return series. Equity starts at 1 and the start is included in the drawdown.

## Post-run notes (2026-10-27, after the first full run at ~10:30 UTC)
6. **Part A final-equity mismatches (19 rows): investigated, not "fixed".** Every drawdown matched within 0.01 pp; only finals differed, by 0.09–0.25%.
   - **Cause:** the claimed final is the cash AFTER the end-of-test close-out (the sale fee is paid). The equity file is mark-to-market BEFORE that sale.
   - **Proof:** `src/research/drawdown_ddx_final_gap.py` → `final_gap_investigation.csv`. 14 rows are reproduced exactly to 0.01 USDT:
     - Step 15/19 engine: MTM − end-of-test exit value × 0.25%;
     - F2/F7/R1 engines: mean over sleeves of 10,000 + Σ trade P&L;
     - BTC hold: (MTM − cash) × 0.25%.
   - The 4 Step 27 exposure rows have no trades file, so only the bound is shown (gap ≤ 0.25% of MTM, scaling with f). F2 AI_LO has no trades file (gap 0.13%).
   - The protocol's statement 1 therefore reads "verified except the final-equity definition (close-out fee), explained".
7. **Code-file SHA differences (report-only, protocol §1).**
   - `f2_longshort.py` and `verify_f2_claims.py` now hash exactly to the "after" SHAs written in F2 `CODE_CHANGES_AFTER_LOCK.md` §1.
   - `step17_18_market_veto_1d.py` differs from its lock SHA. Its CODE_CHANGES file documents 2 bug fixes made before any result, but records no SHA, so that link cannot be SHA-proven.
8. **Verifier fix before its first complete run.** csv reading needed `encoding="utf-8"`: a trades file holds a non-ASCII symbol name, and Windows' default cp1252 crashed at X4. No check result changed meaning; the run then gave 11/11 PASS.
9. **Part C (read-only VM read, 2026-10-27 ~10:35 UTC):** `data/eco_demo/ledger.jsonl` has 55 hourly cycles, from 2026-10-25 04:21 to 2026-10-27 10:20 UTC.
   - eco equity 9,996.98 → 9,958.12 (internal 10k scale); peak 10,063.67.
   - Running max DD 1.775% at 2026-10-26 15:20 UTC; not halted.
   - Fewer than 7 full days, so this is information only.
