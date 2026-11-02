# Step 16B: forward log of the 4H R6 and 1h R24 brains + M_AI3-50 % paper portfolio (pre-registered)

Written and SHA256-locked on 2026-10-15, before the first forward day (as-of 2026-10-15) exists.
Code: `src/execution/forward_multi_16b.py`. Verifier: `src/audits/verify_forward_multi_16b.py`.

**Scope**
- NO ORDERS: no exchange account, no testnet, no GitHub.
- The Step 16 logger, its ledger and its files are not modified; they are only read.
- User approval for this change of the daily scheduled tasks: chat on 2026-10-15 ("0 से 8 तक ... एक एक करके execute करो", with the 50 % setup).

## What is logged every day (as-of = the last closed UTC day)
1. **Universe:** the research test universe, unchanged.
   - Reference 30 + half B of `coin_split.csv` (SHA a1633340…).
   - Top 20 by 30-day mean USD volume, using the Step 23 `daily_members` rules.
   - Coins listed after the split are NOT added. This keeps the forward test identical to what was tested.
2. **4H R6 scores:** members of day as-of − 1, scored on the 6 four-hour bars of the as-of day.
   - Features, xr ranks and the HGB recipe come from Step 23.
3. **1h R24 scores:** members of day as-of − 1, scored on the 24 hours of the as-of day (Step 24 recipe).
4. **Monthly models:** trained at the first run of each month on the research TRAIN universe (reference 30 + half A, top 30, from 2020-01-01).
   - Only rows whose label was known before the month start are used.
   - Saved once to `data/forward/models/{h4_r6,h1_r24}_YYYY-MM.joblib`; their SHA256 goes into every ledger line.
5. **D1 scores:** the Step 16 file's `p_r5` (the Step 19 R5 brain) for the members of the as-of day.
6. **Inputs:** the 1h candles of the as-of day for every member, saved with their SHA256.
   - With the Step 16 ledger, which already keeps the raw REST responses' SHA256, this preserves all forward price data.
   - Swing Anatomy Phase 2 will recompute its forward factors from this data. No separate swing snapshot is logged.
7. **Paper portfolio M_AI3, 50 %:**
   - Each sleeve starts with $10,000 and invests 50 % (`invest = 0.5`); the mix is the mean of the three sleeves.
     - D1: `step22.simulate`, rebalanced every 5 days.
     - H4: `step23.sim4h`, h = 6.
     - H1: `step24.sim1h`, h = 24.
   - Common rules: top 5, kept while rank ≤ 10, cost 0.25 % per fill, next-open fills.
   - It runs from PAPER_START = **2026-10-15**; the first decision is taken at the end of that day.
   - It is recomputed from PAPER_START every day with the unchanged research simulators.
   - A missing day's scores are replaced by the previous day's scores, and an alarm note is written. Without this, the research simulator would sell everything on a day with no scores.
8. **Ledger:** `logs/forward_multi_16b/ledger.csv`, one hash-chained line per day.
   - It holds the SHA256 of every file above, plus the code, the simulator modules and this protocol.
   - `on_time` = the line was written by as-of + 1 day 03:00 UTC.

## Schedule
- New Windows task `CryptoBot16B_ForwardMulti`, daily at 07:30 and 08:00 IST (02:00 / 02:30 UTC). The Step 16 task runs at 00:20 / 01:20 UTC.
- The run refuses to proceed (alarm, no ledger line) if:
  - Step 16 has not written its file for the as-of day, or
  - the BTC 1h data does not end at as-of 23:00.

## Gates before the task is created (all must pass; verifier)
- **V1:** protocol and code SHA as locked.
- **V2 (reproduction of the research brains through the live code path, on the live folders):**
  - For as-of 2026-09-02, 2026-09-15 and 2026-09-29, `score_day` (with a September model trained into a temporary folder) must reproduce:
    - the R6_AI scores in `logs/strategy_1d_step23_4h/test_predictions_4h.csv`,
    - the R24_AI scores in `logs/strategy_1d_step24_1h/test_predictions_1h.csv`.
  - Same symbol/bar set; maximum absolute difference < 1e-9.
  - The day's members must equal `strategy_1d_step19_largecap/universe_U.csv` for day as-of − 1.
- **V3:** the production October models, applied to the 2018–19 rows, must reproduce R6_FROZEN / R24_FROZEN (max |diff| < 1e-9). These are the research frozen brains, trained with labels known before 2026-10-01.
- **V4 (paper engine = research):** `paper()`, run with the research predictions and PAPER_START = 2021-01-01 to 2026-09-30, must reproduce the Step 27 MAIN 50 % sleeve finals within $0.01:

  | Sleeve | Final |
  |---|---|
  | D1 | $43,151.15 |
  | H4 | $49,365.87 |
  | H1 | $69,134.22 |

- **V5:** `--test` runs end-to-end on the live data (as-of 2026-10-14, written to `test/`, not to the ledger).

## Alarms (each one is reported, never hidden)
- A day without a ledger line.
- `on_time = False`.
- Any note: missing scores, members without data, carried-forward days.
- A reproduction failure in any later verifier run.

## Evaluation (after ≥ 90 forward days, about 2027-01-14; descriptive, plus these fixed checks)
- **Forward skill:** AUC of R6 (labels from the logged bars, h = 6 bars) and of R24 (h = 24), with month-block 95 % CIs. Reported against 0.50 and against the research values (0.568 / 0.565).
- **Paper portfolio vs BTC buy-and-hold at 50 %**, over the same days.
  - Reported with the Step 27 one-year range (p5 0.636 to p95) as context only.
  - 90 days is short, so no single number is called a pass.
- **The forward log "passes" (green light for the small real-money decision, which stays with the user) only if:**
  - ≥ 90 days are logged, with ≤ 3 alarms that are explained and not caused by the code;
  - all verifier re-runs pass;
  - the forward AUC point estimate of at least one of R6 / R24 is > 0.50.
  - The AUC CI is reported but not required to exclude 0.50, because 90 days are too few for that. This is stated now so that the bar is not moved later.
