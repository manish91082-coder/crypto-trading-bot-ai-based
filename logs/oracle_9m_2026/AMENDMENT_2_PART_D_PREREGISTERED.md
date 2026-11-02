# Amendment 2: Part D run record. Locked 2026-10-26 before any 2020–2025 result is computed

This records only what Amendment 1 (SHA e68da96c…) left to be filled in. It does not change any gate.

## Selected by the locked rule

- **C3 configs with lb95 > 0 and ≥ 6 / 9 months positive:** none. All 100 FUT configs had lb95 < 0; `part_c/C_RESULTS.json`, verifier ALL PASS.
- **The pre-declared lead FUT|RAND|R08|G12** is run, as Amendment 1 requires "whatever its Part C result".
  - Its Part C result: −0.100% net per trade, lb95 −0.829, 0 / 9 months positive.
  - Its rationale (Diagnostic 2) has been withdrawn as a lookahead artifact (`DIAGNOSTIC_RANDOM_BARRIER.md`, Diagnostic 3).
  - It is still run, so that no locked step is skipped.
- **Context only:** the top C1 method DIR_CLOSEPOS and the top C2 trigger ENT_SWEEP_ALL, reported with their C1 / C2 metrics.

## Data definition (a data necessity, recorded here)

**Window.** The 7-day levels need 7 full prior days, and the data starts 2020-01-01. So the first Part D day is **2020-01-08**; the last is 2025-12-31.

**Excluded:**
1. the manual-study days of that window (`logs/manual_day_study/selected_days.txt`);
2. days without 288 5m bars (15 days, found on 2026-10-26 by a bar count only):
   2020-02-09, 2020-02-19, 2020-03-04, 2020-04-25, 2020-06-28, 2020-11-30, 2020-12-21, 2020-12-25, 2021-02-11, 2021-03-06, 2021-04-20, 2021-04-25, 2021-08-13, 2021-09-29, 2023-03-24;
3. days whose prior day is incomplete, because the 00:00 slot's previous 4 h and the prior-day levels need it.
- The run log prints the counts.

**RAND sides:** drawn with `default_rng(0)` in slot order over the Part D days.

## Code

| Item | Value |
|---|---|
| Main | `src/research/oracle_9m_c.py`, SHA `bc5206913259e9d509d90b8d0a32a74c9f559e779b0991a7390edf61704ed64f`, stage `D` |
| Shared definitions | `src/research/oracle_9m.py`, SHA `e1e44e3e…`, unchanged |

**Code changes after Part C:**
1. `part_d()` was added, with `sweep_events_min` and `a1_min`. On 2026, both reproduce `sweep_events.parquet` (8,150 rows) and the A1 entries of `oracle_day.parquet` exactly; checked on 2026-10-26.
2. NaN guards were added for the previous-4h move. After a re-run, the Part C outputs are byte-identical (the OUTPUT_SHA256 diff is empty).

**Output:** `logs/oracle_9m_2026/part_d/`.

**Verifier:** `src/audits/verify_oracle_9m_d.py` (independent) runs before any number is reported.

## Gates (copied from Amendment 1, unchanged)
1. lb95 of mean net per day > 0;
2. ≥ 60% of months positive;
3. ≥ 4 of the 6 calendar years positive;
4. the RAND comparison, not applied (the lead is RAND);
5. the excluded days are listed.
