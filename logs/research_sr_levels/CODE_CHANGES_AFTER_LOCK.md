# S/R study: changes after the lock

1. **Crash in the final `claims.json` write.** `json.dumps` cannot use the tuple keys of the outcome-count dictionary.
   - The crash happened after the event table and the result CSVs were written. The results were not looked at before the fix.
   - **Fix:** keys become "tf|kind" strings. The logic is unchanged, and the full study was re-run.
62b99b5c4fa25d2a4d6d4ba5cc8dd761037497ff65b87992ba515334db36e956 *src/research/sr_levels_study.py
2. verify_sr_study.py: the sampling line was rewritten without groupby.apply (pandas 3 drops the group columns). The checks are unchanged.
