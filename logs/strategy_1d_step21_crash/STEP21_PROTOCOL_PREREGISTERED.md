# STEP 21 PROTOCOL — crash-risk brain for the large-cap market (pre-registered)

Written and SHA256-locked before any Step 21 model is trained. Code: `src/pipeline_1d/step21_crash_brain_1d.py`.
Spot, 1D, long-only, $10,000, free data only. No GitHub action. Nothing is deployed by this step.

## Why (evidence)
- Step 19: proven selection inside the top-20 coins ($65,275, beats BTC hold), but max drawdown 73 % and 3 losing years.
- Steps 17 and 20: an up/down market gate failed (Step 20 skill was real, but the gate missed the biggest rally weeks).
- This step asks a narrower question: not "up or down", only "is a big fall coming?". AI leaves the market only on its highest-risk days, so most rally weeks stay invested.

## Label (chosen from market prices only, before any model)
crash10(d) = 1 if the equal-weight mean open(d+1)→open(d+11) return of the Step 19 universe U(d) coins (top-20 by 30-day USDT volume, reference + B coins) is below −10 %. Known on d+11.
Frequency 2021–2026 (prices only): 19.1 % of days. By year 2021–2026:
- 2021: 17 %
- 2022: 29 %
- 2023: 12 %
- 2024: 19 %
- 2025: 22 %
- 2026: 15 %

## Brain
- **Features:** the 18 Step 20 market features computed on U(d).
- **Model:** the Step 17/20 market recipe (HGB depth 2, 200 iterations, lr 0.05, leaf 50, l2 1, random_state 0).
- **Training:** monthly walk-forward 2021-01..2026-09 on labels known before the 1st of the month.
- **CONTROL:** a shuffled-label brain trained identically.

## Alarm and system (fixed)
- **Alarm on day d:** P(crash) ≥ the 80th percentile of all the brain's predictions from strictly EARLIER months (no alarm in the first month).
- **System:** Step 19 AI rule (frozen `U_AI_predictions.csv`), unchanged otherwise. On a rebalance day with an alarm, sell everything at the next open and stay in USDT until a rebalance day without an alarm.
- **Runs:** ALARM (AI), ALARM_CONTROL (shuffled brain), UNGATED (must reproduce Step 19 $65,274.51), ALARM at 0.40 %, BTC_HOLD.

## Gates (stricter: third market-timing attempt after Steps 17 and 20)
- **G1:** planted (label + N(0, 2.79)) AUC ≥ 0.55 AND leak (the U 10-day mean return) AUC > 0.95.
- **G2 skill:** AUC **99 %** month-block CI lower bound > 0.50 (Bonferroni over the 3 market-timing attempts) AND AUC > CONTROL.
- **G3 ALARM system:**
  - (a) CAGR > 0
  - (b) Calmar > UNGATED, > ALARM_CONTROL and > BTC_HOLD
  - (c) per-trade net mean CI lower bound > 0
  - (d) ≥ 4 of 6 years positive
  - (e) CAGR > 0 at 0.40 %
  - (f) max drawdown < 50 %
- **Decision:**
  - all pass → `PASS` → paper portfolio in the Step 16 forward log; testnet only after ≥ 90 forward days without alarm.
  - G3 passes but G2 fails → `SYSTEM_PASSES_BUT_BRAIN_UNPROVEN` (not deployed).
  - G1 fails → `INVALID`.
  - otherwise → `FAIL`.

## Honest limitations
- This is a pure time test on one market path that I have already seen.
- Two earlier market-timing attempts failed, which is why the stricter CI is used.
- The forward data remains the clean judge.

## Verification
`src/audits/verify_step21_claims.py`:
- re-derives crash10 from raw opens;
- recomputes the AUCs and the causal 80th-percentile thresholds;
- re-simulates ALARM, ALARM_CONTROL and UNGATED with separate code;
- recomputes the gates.
