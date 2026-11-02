# STEP 22 PROTOCOL — untouched 2018–2019 exam of the frozen Step 19 system + account breaker (pre-registered)

Written and SHA256-locked BEFORE any 2017–2019 price is analysed. Code: `src/pipeline_1d/step22_pre2020_exam_1d.py`.
Spot, 1D, long-only, $10,000, free data only. No GitHub action. Nothing is deployed by this step.

## What was known when this was written (honesty)
- The 2017-08..2019-12 Binance files were downloaded before the lock (`src/downloaders/download_universe_pre2020.py`,
  same evidence rules as the 2020–26 downloader: S3 listing, SHA256 vs `.CHECKSUM`, first continuous run of months,
  1d cut at the first missing day). Only file metadata (symbols, months, rows, SHA) was looked at before the lock.
- No model, label, threshold or parameter of this test is fitted on 2017–2019 data. Every parameter was fixed on 2020–2026.
- General public history is known to the author (the 2018 bear market). This is why the test is ONE shot with
  fixed gates. After this step these years are no longer untouched.

## Systems under test (all frozen)
- **Brain:** the live forward brain `data/forward/models/r5_2026-10.joblib`.
  - Its SHA256 must equal the Step 16 ledger value `549187143955c2346ca4c3c12e661395eb88fbdee50c49eb4defca1ec9848847`.
  - Recipe: Step 15 R5 (47 core features, HGB depth 3 / 300 / lr 0.05 / leaf 200 / l2 1, random_state 0).
  - Trained on the 30 reference coins plus eligible A-half coins, labels known before 2026-10-01.
  - Every 2017–2019 row is unseen. The brain is used as-is and never retrained. This is a time-reversed
    out-of-sample test: the brain has seen later years, but never these.
- **CONTROL brain:**
  - Same rows and recipe, labels randomly permuted (numpy seed 22).
  - The same retraining with real labels (AI_RETRAIN) must reproduce the frozen brain's predictions.
- **Features:**
  - Built with `core_rows_1d.build`, unchanged, from `data/universe_pre2020`, as-of 2019-12-31.
  - Reference coins are the 30 Step 13 reference coins that exist at that time; all other coins are "new" coins.
  - Fear & Greed comes from the locked file (starts 2018-02-01).
- **Eligible row:** 30-day mean USD volume ≥ $2M AND ≥ 120 candles up to that day (as-of rule).
- **Universe U(d):** top-20 eligible coins by 30-day mean USD volume (all coins; the A/B split does not exist before 2020).
- **Trading rule (Step 19, unchanged):**
  - Rebalance every 5 days from the test start: target the top 5 by score, keep while rank ≤ 10.
  - Orders fill at the next open. Each buy = min(INVEST × equity / 5, cash / (1 + cost)).
  - Cost 0.25 % per fill. A delisted coin is sold at its last real close.
- **Account breaker (user's choice, fixed on 2021–26):**
  - Trigger: account equity ≤ peak × (1 − b).
  - Action: sell everything at the next open, and make no buys for 30 days.
  - Reset: after the 30 days the peak is reset to the current equity.
  - Daily check uses daily close equity.
  - Hourly check uses hourly close equity from 1h candles, sells at the next hourly open, and keeps a running hourly peak.
- **Test window:** 2018-02-01 .. 2019-12-31. Fear & Greed starts 2018-02-01; the brain was never trained without it.
  Labels need open(d+6), so skill rows end 2019-12-25.

## Runs (start $10,000, cost 0.25 % unless named)

| Name | Brain | Invest | Breaker |
|---|---|---|---|
| AI_80_none | AI | 80 % | none (Step 19 exactly) |
| AI_100_none | AI | 100 % | none |
| **AI_100_b10** | AI | 100 % | 10 %, daily (**PRIMARY**, user's package) |
| AI_100_b08 / b12 / b15 / b20 | AI | 100 % | 8 / 12 / 15 / 20 %, daily |
| AI_100_b10_hourly | AI | 100 % | 10 %, hourly check |
| AI_100_b10_stop25 | AI | 100 % | b10 daily + per-coin disaster stop at entry × 0.75 (daily low; gap-aware fill = min(open, stop)) |
| AI_100_b10_cost040 | AI | 100 % | b10 daily, cost 0.40 % |
| CONTROL_100_none, CONTROL_100_b10 | CONTROL | 100 % | none / b10 |
| EW_U_100_none, EW_U_100_b10 | equal weight | 100 % | none / b10 (all U coins, N = keep = 20) |
| BTC_HOLD | — | 100 % | buy at the first open, hold |

## Skill measurement
- **Label:** R5 = coin open(d+1)→open(d+6) return > median of the reference coins' same return that day
  (Step 15/19 definition).
- **Secondary label (reported, not gated):** > median of U(d).
- **AUC:** AUC on U rows in the window, 95 % month-block bootstrap CI (2000 reps).

## Gates
- **G0 integrity** (all must hold, else `INVALID`):
  - (a) Frozen model SHA = ledger SHA.
  - (b) AI_RETRAIN predictions equal the frozen brain's predictions on all 2018–19 rows (max |diff| < 1e-9).
  - (c) The new simulator reproduces Step 19 on 2021-01-01..2026-09-30 with `U_AI_predictions.csv`: 80 %/none = $65,274.51 (± $0.01).
  - (d) The 2021–26 in-sample 100 %/b10 daily figure shown to the user ($84,118) is reproduced (± $1).
  - (e) Every test-window day has ≥ 1 U coin.
- **G1 out-of-time selection skill:** AI AUC 95 % CI low > 0.50 AND AI AUC > CONTROL AUC.
- **G2 primary system AI_100_b10:**
  - (a) max drawdown < 50 %
  - (b) final > BTC_HOLD final
  - (c) final > CONTROL_100_b10 final AND > EW_U_100_b10 final
  - (d) max drawdown < AI_100_none max drawdown
  - (e) AI_100_b10_cost040 final > BTC_HOLD final
  - (f) neighbours b08 and b12: each has max drawdown < 50 % AND final > BTC_HOLD final
- **Decision:**
  - G0, G1 and G2 all pass → `PASS`. The package goes to a paper portfolio in the forward log; real money only after ≥ 90 forward days without alarm.
  - G2 passes, G1 fails → `SYSTEM_PASSES_SKILL_UNPROVEN`.
  - G1 passes, G2 fails → `SKILL_HOLDS_PACKAGE_FAILS`.
  - Neither passes → `FAIL`.

## Also reported (not gated)
- Breaker trips: count, loss at each exit fill measured from the peak (in % and in $), worst and median, for daily and hourly checks.
- Year returns for 2018 and 2019, U size per day, and the number of reference coins per day.
- The 2021–26 in-sample hourly-check result, for comparison (in-sample, not evidence).

## Not tested here (and why)
- The Step 20 market gate (decision `FAIL`) and the Step 21 crash brain (`INVALID`): they are not part of the system,
  and testing rejected ideas on the only untouched data would waste it.

## Honest limitations
- **Download metadata (listing dates only, no prices) seen before the lock:**
  - 92 USDT pairs have 1d files in 2017-08..2019-12; 875 monthly zips are SHA256-verified.
  - BCCUSDT is cut at 2018-11-15 (delisted). VENUSDT keeps only its first month (swap to VET).
  - On 2018-02-01 only BTC and ETH have ≥ 120 candles. Until about mid-2018 U therefore has fewer than 5 coins, so the
    system holds every U coin and the AI selection is inactive. Selection only matters once U has more than 5 coins.
- 23 months and few coins in 2018: the U universe can hold fewer than 20 coins, and the reference set fewer than 30,
  so the brain's rank features see a smaller cross-section than in training.
- One market path. The 10 % breaker level was chosen by the user after seeing 2021–26 results; only this test is clean for it.

## Verification
`src/audits/verify_step22_claims.py`:
- re-derives U(d) and the R5 labels from raw files;
- recomputes AUC with the Mann-Whitney rank formula;
- re-simulates AI_100_none, AI_100_b10, CONTROL_100_b10 and BTC_HOLD with separate code;
- recomputes the gates.
