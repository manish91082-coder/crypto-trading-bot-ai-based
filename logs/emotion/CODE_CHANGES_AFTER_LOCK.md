# EMO meter and EMO-1: code written after the protocol locks

- **Meter protocol** e7a20dc2… (locked 12:38 UTC):
  - `src/eco/emotion_meter.py` c0e131ab6cd9…
  - `src/audits/verify_emotion_live.py` 2add5613e8d4…
  - `src/audits/test_emotion_meter.py` d06fee71f59e…
- **Meter offline test:** E1–E5 5/5 PASS.
  - The first E5 run failed because its universe held a failing symbol: 1 of 4 = 25%, above M4's 20%. That is the correct M4 behaviour, so only the test universe was changed.
  - The order of the row-count check in `features()` was fixed before the first run.
- **Live scratch run on the VM** (12:4x UTC, /tmp copy, real public endpoints):
  - 25/25 symbols, 22 s;
  - last used rows = 11:00 UTC for the 12:00 record (the open hour excluded);
  - verifier M1–M5 5/5 PASS.
- **EMO-1 protocol** b777c510… (locked 12:42 UTC):
  - `src/research/emo_download.py` 47b950dda43a… (stage D only; no study code yet);
  - trial registry `trial_registry_emo1.csv` (P, R1, R2).
- **Downloader scratch test on the VM:**
  - BTC and FTT, 2022-09 … 11: liq 8/8 zips;
  - the second run skipped 8/8 (resume);
  - eligible: BTC only;
  - FTT metrics 2022-11-10 … 16: 5 zips, and 2 days recorded as 404 after FTT's halt;
  - perp 1h and funding: 2 zips;
  - SHA re-check: 0 mismatches.
- **EMO-1 stage S code** (written before any result; interpretation in CODE_NOTES 1):
  - `src/research/emo1_study.py` ac5f954111a8…;
  - independent verifier `src/audits/verify_emo1.py` 81b5b07997fa… (V1 row-by-row recompute from the raw zips, V2 panel SHA, V3 rebalance math, V4 point-in-time).
- **Smoke test** (VM scratch, ETH 2022-04 … 05, real zips): 25 random rows, all features + return + funding recomputed by the verifier's row method, **0 mismatches**.
  - The smoke test also found the empty early fields and the OI-value 0 rows, which became CODE_NOTES 1.
  - No portfolio, gate or score result was computed.

## 2026-10-23: EMO-1 dev run failed on a missing dependency; deployment fix (no code change)

- The chain's `dev` step (2026-10-22 19:19 UTC) stopped with `ModuleNotFoundError: n1_portfolio`.
  - No report, no gate value and no holdout data were produced; the panel (SHA bd1e40b83107…) was already built.
- **Cause (my error):** the laptop–VM comparison of 2026-10-22 listed `src/research/n1_portfolio.py` as "laptop-only research", without checking that `emo1_study.py` (`evaluate`, line 207) imports it for the DSR gate G4.
- A dependency check found two more files missing on the VM: `src/research/tf_edge_map.py` (imported by n1_portfolio) and `data/derived/eco/e2_daily_series.parquet` (G2/G3 input, line 215).
- **Fix:** the three files were copied from the laptop unchanged:
  - n1_portfolio.py afa84a3197a0…;
  - tf_edge_map.py a91516daa2c9…;
  - e2_daily_series.parquet 814e680e2799….
  - SHA-equal on both machines; an import test on the VM ran `N.dsr` successfully.
- `emo1_study.py` (ac5f954111a8…) and `verify_emo1.py` (81b5b07997fa…) are unchanged.
- `dev` and then `verify_emo1.py dev` were re-run on 2026-10-23 and appended to `emo1_chain.log`. The holdout is still unopened.

## 2026-10-24: EMO-1 amendment 1 (explicit concat sort): tried, proof FAILED on P3, reverted

**Protocol:** `EMO1_AMENDMENT_1_PREREGISTERED.md` d2f64154…, locked before the change.

**Change tried:** `sort=True` at lines 121 and 218 (code d5bf2afe29d8…).

**Proof on the VM** (log: `logs/emotion/emo1_a1_proof.log`):

| Check | Result | Detail |
|---|---|---|
| P1 | PASS | backups made |
| P2 | PASS | panel rebuilt with the new code; SHA bd1e40b83107… unchanged |
| P4 | PASS | `verify_emo1.py dev` 4/4 |
| P5 | PASS | no Pandas4Warning at 121/218 |
| **P3** | **FAIL** | the new report differs from the recorded one (e8f84fc42c8b…) in float fields, at most 1.43e-14 relative; gates, n_rebalances and every non-float field identical |

**Control.** The OLD code ac5f954111a8… was re-run on the same panel:
- It also differs from its own recorded report, by the same 1.43e-14 relative.
- `dev_rebalances_P.csv` has three different SHAs across the three runs: 1510fa87 original, 7a4754ad old re-run, c1c06136 new.
- New vs old re-run: at most 6.0e-15 relative.
- **Finding:** the dev run is not bit-reproducible, even with unchanged code (floating-point summation order). P3 as written (bit-exact) could not pass. That was an error in the amendment, not in the change.

**Action (per the locked rule "all, or the change is reverted"):**
- The code was reverted on the VM and the laptop to ac5f954111a8….
- `data/emotion/emo1/*` was restored byte-equal to the backup.
- The authoritative dev report e8f84fc42c8b… was restored.
- Run files are kept for the record: `EMO1_DEV_REPORT_postA1.json` and `EMO1_DEV_REPORT_rerun_oldcode.json`.
- The pandas warning remains. With the installed pandas 3.0.5 it sorts, so the results are as recorded.
- **Next (needs a new pre-registered amendment):** a tolerance criterion based on the run-to-run spread (e.g. ≤ 1e-12 relative and identical gates), or pinning pandas.

## 2026-10-25: EMO-1 closed

- Closeout `EMO1_CLOSEOUT_2026-10-25.md` 43da5f2a4f50…: FAIL is final, because G3 is defined on dev AND holdout and the dev G3 is false.
- The holdout is not opened, and the sort-fix amendment is not pursued.
- No code changed. A trial registry line was appended.