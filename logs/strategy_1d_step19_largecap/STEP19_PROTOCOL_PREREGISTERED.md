# STEP 19 PROTOCOL — R5 selection inside the large, liquid coins (pre-registered)

Written and SHA256-locked before any Step 19 model output is produced. Code: `src/pipeline_1d/step19_large_caps_1d.py`.
Spot, 1D, long-only, $10,000, free data only. No GitHub action. Nothing is deployed by this step.

## Why (evidence gathered before this protocol; market prices only, no AI output)
Non-overlapping 5-day steps, 2021-01..2026-09. What $1 became:
- BTC 2.88
- point-in-time top-10 coins by volume 1.34
- rank 11–30: 0.55
- rank 31–100: 0.62
- rank > 100: 0.56

Small/mid altcoins lose about half over the period, which is why Steps 15/17/18 long-only books failed although R5 selection skill is proven. Hypothesis: the same R5 selection inside the large, liquid coins avoids that negative drift.

## Brain (frozen recipe = Step 15 R5, no change)
- R5 is re-run exactly as in Step 15: training = 30 reference coins + eligible A coins; monthly walk-forward; HGB core recipe; shuffled CONTROL.
- This time the predictions are written for the 30 reference coins too. A prediction for month T always comes from a model trained on labels known before T, so it is out-of-time.
- Integrity check G0: the re-run's predictions for the B coins must equal the Step 15 file (max |diff| < 1e-12).

## Universe and rule (fixed, no grid)
- **Universe U(d):** the 20 coins with the highest trailing-30-day mean daily USDT volume on day d. Candidates are eligible rows (liquid, ≥ 120 candles up to d) of the 30 reference coins + the B coins. A coins are excluded, because they are R5 training coins and not reference coins.
- **Rule:** rebalance every 5 days (2021-01-01 + 5k). Rank U(d) by R5 score. Target top 5; keep a held coin while its rank in U(d) ≤ 10 (a coin that leaves U is sold). Orders execute at the next open. Each buy = min(0.80 × equity / 5, cash / (1 + cost)). Cost 0.25 % per fill.
- **Benchmarks** (same 0.80 exposure, same cost):
  - EW_U: equal weight in all U coins, same rebalance days.
  - BTC_HOLD: buy BTC at the first open, hold to the end.
  - CONTROL: shuffled-label R5, same rule.
  - SIMPLE: 20-day price return ranking, same rule.
  - AI at 0.40 % per fill.

## Gates
- **G0:** reproduction of the Step 15 B predictions (else `INVALID`).
- **G1 skill inside U:** R5 AUC on U rows (Step 15 relative label), 95 % month-block CI lower bound > 0.50 AND > CONTROL AUC.
- **G2 trading (AI):**
  - (a) CAGR > 0;
  - (b) Calmar > EW_U, > BTC_HOLD, > CONTROL and > SIMPLE;
  - (c) per-trade net mean 95 % month-block CI lower bound > 0;
  - (d) ≥ 4 of 6 calendar years positive;
  - (e) CAGR > 0 at 0.40 % per fill;
  - (f) max drawdown < 50 %.
- **Decision:**
  - all pass → `PASS` → paper portfolio in the Step 16 forward log; testnet only after ≥ 90 forward days without alarm;
  - G1 only → `PARTIAL_SKILL_RULE_FAILS`;
  - otherwise → `FAIL`.

## Honest limitations (stated before the result)
- The 30 reference coins and the 2021–2026 period were used in Steps 6–18.
- U is mostly reference coins, so this is an out-of-TIME test (walk-forward), not an out-of-coin test.
- The design was chosen after the drift evidence above, but the brain and the rule are fixed.
- The clean judge remains the forward data (Step 16).

## Verification
`src/audits/verify_step19_claims.py`:
- re-derives U from raw volumes;
- re-derives labels from raw opens;
- recomputes the AUCs;
- re-simulates AI, CONTROL, EW_U and BTC_HOLD with separate code;
- recomputes the gates.
