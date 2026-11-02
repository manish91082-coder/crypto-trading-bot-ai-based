# CONSOL-2026-10-28: consolidation of the 24–27 Oct research + live ECO state (pre-registered)

Written 2026-10-28, before the VM snapshot is taken and before the consolidated report is written.

## 1. Purpose and limits
- The user asked (2026-10-28) for one file listing everything from the last days of research and the live ecosystem: what to add, why, and the benefit, with nothing missed and nothing invented.
- This is a **compilation**, not new research:
  - no new backtest, no new fit, no parameter choice;
  - no holdout is opened;
  - nothing on the VM is written, restarted or deployed. The VM is read only.
- Every recommendation must point to an existing, verified source.

## 2. Sources (fixed list; SHA256 recorded in `source_manifest.csv` at lock time)
Research reports, 24–27 Oct 2026 (root folder):
1. RESEARCH_SPOT_DCA_SPOT_FUTURES_24_OCT_2026.md
2. RESEARCH_SPOT_SLEEVE_24_OCT_2026.md
3. RESEARCH_ECO_MONTHLY_OUTLOOK_25_OCT_2026.md
4. RESEARCH_ROOT_CAUSE_25_OCT_2026.md
5. RESEARCH_BTC_DIRECTION_ENTRY_EXIT_25_OCT_2026.md
6. RESEARCH_METHODS_CATALOG_26_OCT_2026.md
7. RESEARCH_MANUAL_10_DAYS_BTC_26_OCT_2026.md
8. RESEARCH_ORACLE_9M_2026_PART_A_B_26_OCT_2026.md
9. RESEARCH_ORACLE_9M_2026_PART_C_D_26_OCT_2026.md
10. RESEARCH_NONPRICE_NP1_NP3_26_OCT_2026.md
11. RESEARCH_METHODS_BENCH_BATCH1_26_OCT_2026.md
12. RESEARCH_GREEN_CANDLE_JAN_2026_27_OCT_2026.md
13. RESEARCH_MICRO_MOMENTUM_1S_2026_27_OCT_2026.md
14. RESEARCH_FEE_HURDLE_MAP_27_OCT_2026.md
15. RESEARCH_DRAWDOWN_DDX_27_OCT_2026.md
16. RESEARCH_METHODS_BENCH_BATCH2_27_OCT_2026.md
17. RESEARCH_TURN_DETECT_2026_27_OCT_2026.md

Ecosystem / open-item records:

18. logs/fees/FEES_RECORD.md and logs/fees/FEE_AMENDMENT_2_RESULTS.md
19. logs/research_1d_true_fee/TRUE_FEE_1D_RESULTS.json
20. logs/log_ship/CODE_CHANGES_AFTER_LOCK.md (v7 status)
21. logs/eco/HEALTH_CHECK_2026-10-26.md
22. logs/eco_maker/MK1_PROTOCOL_PREREGISTERED.md, logs/fwd_watch/FWD_WATCH_PROTOCOL_PREREGISTERED.md, logs/live_collect/LIQ_COLLECTOR_RECORD.md, logs/paper_spot_s1/PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md
23. logs/strategy_f7_risk/F7_PROTOCOL_PREREGISTERED.md (data period of the 1D rule choice)
24. deploy/crontab.txt, deploy/fees.json

## 3. Study verifier outputs (each must show 0 FAIL)
The stored outputs of the verifiers of sources 1–17 are listed in `verifier_manifest.csv` with their SHA.
- The monthly-outlook verifier (source 3) stores no output. It is re-run once into `verify_monthly_outlook_rerun.txt`, read-only.
- The manual-day study (source 7) has per-day check files; each must end in `BAD 0`.

## 4. VM snapshot (read-only)
- **Commands:** one `gcloud compute ssh` session running only read commands: `crontab -l | sha256sum`, `tail`/`cat`/`wc` of status CSVs, ledgers and decision files, `ps`/`uptime`/`df`/`free`.
- **Not run:** verifiers that write files. No restart, no edit.
- **Output:** saved verbatim to `vm_snapshot.txt`, with its SHA in `vm_snapshot_SHA256.txt`.
- **Expected installed crontab SHA:** `13443469f4ec…` (`deploy/crontab.txt`). A mismatch is reported, not fixed.

## 5. Claims and checks
- **claims.json:** every number in the consolidated report's tables comes from `claims.json`. Each entry has:
  - an id and the value as written;
  - the source file;
  - an exact substring that must occur in that source file, as locked in `source_manifest.csv` (or in `vm_snapshot.txt`).
- **Verifier** `src/audits/verify_consolidation.py` (written after this lock, independent of the report text):
  - **K1:** source SHAs equal the manifest.
  - **K2:** every verifier output in `verifier_manifest.csv` has its SHA and contains a 0-FAIL total. The 10 manual-day check files each end in `BAD 0`.
  - **K3:** every claim substring occurs in its source.
  - **K4:** every claim value printed in the report occurs in the report.
  - **K5:** coverage: every source 1–17 file name occurs in the report.
  - **K6:** every item in the report's action ledger has exactly one class from §6 and at least one source.
  - **K7:** the VM snapshot SHA matches, and the snapshot has a `crontab -l` SHA line.

## 6. Classification rules (fixed now)
Each item gets exactly one class:
- **A (करें, आपकी हाँ के बाद):** safety, monitoring or operations items that change **no** trading decision, already built and tested (or a small code + test job), where the source names the benefit.
- **W (इंतज़ार, पहले से locked gate):** a forward gate already running. No action except reading it on its date.
- **T (नया pre-registered test, अभी लागू नहीं):** an idea a source marked as a hypothesis or next test. It needs its own protocol and the user's yes. Nothing is traded on it.
- **S (रोकें / न जोड़ें):** the sources show it fails after fees or against a random control.
- **U (आपकी तरफ़ का फ़ैसला या काम).**

**Hard rule:** no item that changes trading logic, capital or weights may be class A on backtest evidence alone. Such items are W or T.

## 7. Output
- **Report:** `CONSOLIDATED_ACTION_PLAN_28_OCT_2026.md` (Hindi).
- **Evidence:** `claims.json`, `verify_output.txt` and `REPORT_SHA256.txt` in this folder.
