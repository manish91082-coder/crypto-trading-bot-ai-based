# STEP 24 PROTOCOL — 1h timeframe brain (pre-registered)

Written and SHA256-locked before any 1h model is trained. Code: `src/pipeline_1d/step24_1h_brain.py`.
It is the Step 23 design (same universes, same model, same gate logic) moved to 1-hour candles.
Spot, long-only, $10,000, 100 % invested, cost 0.25 % per fill. No GitHub action. Nothing is deployed.

## Question
Do 1-hour candles give a tradable edge, either faster (4 hours) or for the same 1-day question, beyond the 4H R6 brain
(Step 23 PASS) and the 1D system?

## Data
- **Candles:** the SHA256-verified 1h files (2020–26 `universe_all/1h`, 2018–19 `universe_pre2020/1h`), used as they are.
  - Hourly grid; a missing hour is NaN. An off-hour 2018 candle is floored to its hour.
  - If two candles fall in the same hour, they are aggregated with the Step 23 rule.
- **Cross-check (reported, G0):** the 24 hours aggregated per coin-day vs the 1d candle; mismatch share < 1 %.

## Universes
Identical to Step 23:
- **TEST U(d):** = Step 19 universe, re-derived and asserted.
- **TRAIN T(d):** top-30 of the reference + half-A coins.
- **2018–19:** the Step 22 U.

U(d) applies to the 24 hours of day d+1.

## Features (31, known at the hour close)
- **Returns:** r1, r4, r12, r24, r72, r168.
- **Shape (14-hour ATR):** dist_hi24, dist_lo24, dist_hi168, atr_pct, range_atr, body_atr, upwick_atr, lowick_atr.
- **Activity:** vol_ratio24, trades_ratio24, taker_buy_ratio, taker_ratio_12, taker_ratio_chg, rv12.
- **Time and BTC:** bar_hour, btc_r1, btc_r12, btc_r72.
- **Ranks inside the row's universe at that hour:** xr_r1, xr_r12, xr_r72, xr_vol_ratio24, xr_taker_buy_ratio, xr_dist_hi24, xr_atr_pct.

## Labels
- **R_h:** coin open(t+1)→open(t+1+h) return > universe median at hour t, for h = 4 (4 hours) and h = 24 (1 day).
- **Known time:** open(t+1+h).

## Brains
- **Model:** HGB depth 3, 300 iterations, lr 0.05, leaf 200, l2 1, random_state 0. Monthly walk-forward 2021-01..2026-09.
- **Training rows:** TRAIN rows whose hour is a multiple of 3 (00, 03, …, 21). This is a fixed, label-blind 1/3 subsample, chosen only for compute time. Test rows: all hours.
- **CONTROL:** shuffled labels (seed 24).
- **Frozen final brains:** labels known before 2026-10-01, applied to 2018-02..2019-12.
- **G1 planted/leak check (R24):** run on 12 months only (every 6th month from 2021-01), for compute time.

## Trading rule
- **Rebalance:** every h hours: R4 every 4 hours, R24 daily at 00:00 UTC.
  - Target the top 5, keep while rank ≤ 10. Orders at the next hour open.
  - Buy = min(equity / 5, cash / (1 + cost)).
- **Missing hour:** trades and marks at the last close.
- **Delisted coin:** sold at its last real close.
- **Comparators:**
  - 4H R6 (Step 23 PASS): $98,734.89, Calmar 0.625.
  - 1D Step 19 at 100 %: $74,452.43, Calmar 0.515.
  - CONTROL.
  - BTC hold: $28,767.66, Calmar 0.264.
- **Drawdown:** measured on equity at UTC day close.

## Gates (2 brains → Bonferroni 98.75 %)
- **G0:**
  - universe equals Step 19;
  - 1h-vs-1d mismatch < 1 %.
- **G1:** planted AUC ≥ 0.55 AND leak > 0.95.
- **G2 skill (per brain):** AUC 98.75 % CI low > 0.50 AND AUC > CONTROL.
- **G3 trading (per brain):**
  - (a) CAGR > 0;
  - (b) Calmar > 4H R6 (0.625), > 1D (0.515), > CONTROL and > BTC (0.264);
  - (c) per-trade 95 % CI low > 0;
  - (d) CAGR > 0 at 0.40 %.
- **G4:** frozen brain 2018–19 AUC 95 % CI low > 0.50.
- **Decision:**
  - `INVALID` if G0/G1 fail.
  - `PASS_R{h}` if G2+G3+G4 pass (higher Calmar wins).
  - `SKILL_ONLY` if G2+G4 pass but G3 fails.
  - else `FAIL`.
- **Why the bar is high:** G3(b) requires beating 4H R6. A 1h brain is only useful if it adds over what already passed.

## Honest limitations
- **Cost:** R4 trades every 4 hours, and cost is expected to dominate (Step 14 evidence).
- **Data path:** the same 2021–26 path as Steps 19 and 23.

## Verification
`src/audits/verify_step24_claims.py`:
- re-derives a sample of forward returns from raw 1h;
- re-derives all labels;
- recomputes the AUCs;
- re-simulates both AI portfolios;
- recomputes the gates.
