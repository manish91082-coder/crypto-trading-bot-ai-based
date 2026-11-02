# Spot DCA study: changes after the protocol lock (5a44d2c6…)

1. **Run 1** (code bce49f58520e…) produced `SPOT_DCA_RESULTS_run1.json`. The verifier's first run failed V2, V3 and V4. Investigation:
   - **V4 (10 exits):** the exits were correct. `pandas.to_json` writes 10 significant digits by default, so the saved exit prices were rounded just beyond the 1e-9 check.
     - **Study fix (output only):** `double_precision=15`.
   - **V3 (final 12,806 vs 2,617):** a verifier gap. The open-at-end file had no buy list, so the cash loop missed those buys.
     - **Study fix (output only):** the open positions' buys are saved.
     - **Verifier fix:** they are now cash outflows.
   - **V2 (ALGOUSDT 2021-05-26):** the study was right.
     - 27 coins were graded that day, and their buys (6,759 of 6,980 cash) came first under the protocol's ranking (deeper dd90 first). No cash was left for ALGO.
     - The verifier's "cash ≥ 50% of equity" proxy was too weak. It now tests a missed entry only when the cash left after the study's actual buys of the next open still covers it.
2. **Run 2** (code with the two output-only fixes): `SPOT_DCA_RESULTS.json` equals run 1 in every field except `code_sha256`.
3. **Verifier** `src/audits/verify_spot_dca.py`: 7/7 PASS on run 2 (`verify_stdout.txt`). Honest limit of V2: only 10 of the 200 graded (coin, day) cases had enough cash to be a real test, because cash usually ran out.
