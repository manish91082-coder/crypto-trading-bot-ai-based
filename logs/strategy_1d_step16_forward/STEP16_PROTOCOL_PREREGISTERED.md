# STEP 16 PROTOCOL — forward dry-run of the AI brains on live data (pre-registered)

Written and SHA256-locked before the first forward prediction is logged. Code: `src/execution/forward_dryrun_1d.py`.
Spot, 1D, long-only research. **No orders, no testnet, no money.** No GitHub action.

## Purpose (stated honestly, with the evidence behind it)
1. Prove that the live way of working produces exactly what the research pipeline produces.
   Evidence before start: `src/audits/replay_core_vs_step13.py`:
   - **2026-09-15:** 98/98 coins identical to Step 13's p1 (max diff 5.6e-17).
   - **2023-03-15:** 185/185 identical. The 3 extra Step 13 coins came from Step 13's whole-history 120-day rule (a small look-ahead, documented in the Step 13 addendum: AUC without those rows 0.5304 vs 0.5299). The live rule counts days up to the as-of date only.
2. Collect genuinely forward predictions that cannot be altered afterwards.
3. Watch whether the skill seen in research is still there (an alarm), NOT to "prove" skill. Measured on Step 13 data, a forward window rarely proves the 1-day skill statistically: day-block CI > 0.50 in only 10 % of 30-day, 12 % of 90-day and 21 % of 180-day windows. The proof of skill is the 535-coin exam (Step 13); forward is a consistency and integrity check.

## What is logged every day
For the last fully closed UTC day d (as-of), for every liquid coin (known 30 + all other coins passing the Step 13 rules, with "≥ 120 days" counted up to d):
- B1 = the Step 13 1-day brain (core recipe, trained on the 30 known coins only, re-trained on the 1st of each month on labels known before that day; the model file's SHA256 is logged).
- Brains frozen later (Step 15) are added with their own forward start date; the logger code SHA256 is written in every ledger line, so any code change is visible.

## Data
- History up to 2026-09-30: `data/universe_all` (SHA256-verified Binance Vision files).
- From 2026-10-01: Binance public REST klines (1d + 1h, all 12 columns). Only candles whose close_time is before the run time are used. Every raw REST response is stored (gzip JSON) and its SHA256 is written in the ledger.
- Later cross-check: the forward evaluator compares every REST candle with Binance Vision DAILY files (SHA256 against .CHECKSUM) once they are published. A mismatch is reported.
- Fear & Greed: locked file values for dates ≤ 2026-10-12; newer dates come from the daily alternative.me response (raw stored, SHA256 in the ledger).
- Universe: the 705 USDT pairs known on 2026-10-13. Pairs listed later are not added (documented limitation).

## Tamper evidence and timing
- `ledger.csv`: one line per run with run time (UTC), as-of date, predictions-file SHA256, raw-data SHA256s, model SHA256, logger code SHA256, previous line hash, and this line's hash (hash chain).
- A prediction for day d counts as forward evidence only if it was logged before d+1 03:00 UTC. Features use only candles ≤ d.
- Missed days are NOT back-filled; a back-filled prediction is not forward evidence.
- The first forward day is the first as-of date logged in real time. No back-filling of 2026-10-01..10-12.

## Evaluation (`forward_evaluate_1d.py`, every 30 days; numbers fixed now)
- **Outcome:** label = open(d+1) → open(d+2) return > 0.25 %, from Vision daily files when available.
- **AUC:** computed on all logged liquid coins of valid days, with a day-block bootstrap 95 % CI.
- **Alarm thresholds** (10th percentile of historical window AUCs from Step 13 data, rows with ≥ 120 days):
  - 30 days < 0.4561
  - 60 days < 0.4726
  - 90 days < 0.4837
  - 180 days < 0.4996
  - An alarm means the skill may have broken. No new brain is deployed while an alarm is active.
- Also reported: share of days with logs on time, REST vs Vision mismatches, coins per day.

## Not in this step
No trading rule is simulated for B1 (Step 14 showed B1 cannot pay its costs). A trading rule enters forward only if a brain passes its own pre-registered research step first (Step 15).
