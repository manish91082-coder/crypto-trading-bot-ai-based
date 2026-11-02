# STEP 23 PROTOCOL — 4H timeframe brain (pre-registered)

Written and SHA256-locked before any 4H model is trained. Code: `src/pipeline_1d/step23_4h_brain.py`.
Spot, long-only, $10,000, free data only, 100 % invested (user's instruction), cost 0.25 % per fill. No GitHub action. Nothing is deployed.

## Question
Can an AI brain that sees 4-hour candles pick the large coins that beat the other large coins, well enough to make
money after costs, and better than the 1D Step 19 system on the same coins?

## Data (no new download)
- **4H candles:** built from the SHA256-verified 1h files.
  - 2020–26 from `data/universe_all/1h`; 2018–19 from `data/universe_pre2020/1h`.
  - Bars are UTC 00/04/08/12/16/20. open = first hourly open, close = last hourly close, high = max, low = min, volume / quote volume / trades / taker-buy = sums.
  - A bar with no hourly candle is missing (NaN). No price is invented for features or labels.
- **Cross-check (reported):** per coin-day, the 6 bars aggregated must equal the 1d candle (rtol 1e-9 for prices, 1e-6 for volume). The mismatch share is reported.

## Universes (point-in-time; daily rule, used for the 6 bars of the NEXT UTC day)
- **TEST U(d):** exactly the Step 19 universe: top-20 eligible coins by 30-day mean USD volume among the reference 30 + half-B coins.
  - Eligible = 30-day mean USD volume ≥ $2M AND ≥ 120 candles.
  - It is re-derived and must equal `logs/strategy_1d_step19_largecap/universe_U.csv`.
- **TRAIN universe T(d):** top-30 eligible coins by the same volume rule among the reference 30 + half-A coins.
  - Half-B coins are never trained on (unseen-coins rule).
- **2018–19 confirmation universe:** the Step 22 U (all coins existed before the A/B split).

## Features (31, all known at the bar close)
- **Returns:** r1, r3, r6, r18, r42, r84 (bars).
- **Shape (ATR-normalised, 14-bar ATR):** dist_hi30, dist_lo30, dist_hi90, atr_pct, range_atr, body_atr, upwick_atr, lowick_atr.
- **Activity:** vol_ratio30, trades_ratio30, taker_buy_ratio, taker_ratio_6, taker_ratio_chg, rv6 (6-bar std of r1).
- **Time and BTC:** bar_hour, btc_r1, btc_r6, btc_r42.
- **Cross-sectional ranks inside the row's own universe at that bar:** xr_r1, xr_r6, xr_r42, xr_vol_ratio30, xr_taker_buy_ratio, xr_dist_hi30, xr_atr_pct.

## Labels (relative, the Step 15 idea on 4H)
- **R_h:** coin open(t+1)→open(t+1+h) return > median of the same return over the row's universe at bar t, for h = 6 (1 day) and h = 30 (5 days).
- **Known time:** open(t+1+h).

## Brains
- **Model:** HGB depth 3, 300 iterations, lr 0.05, min leaf 200, l2 1, random_state 0 (the 1D recipe).
- **Training:** monthly walk-forward 2021-01..2026-09 on TRAIN rows with labels known before the 1st of the month, predicting TEST rows of that month.
- **CONTROL:** shuffled training labels (numpy seed 23).
- **Frozen final brains (for 2018–19):** trained once on TRAIN rows with labels known before 2026-10-01, then applied to the 2018-02..2019-12 U rows.

## Trading rule (fixed; one per brain)
- **Rebalance:**
  - Rebalance every h bars at a UTC day boundary: R6 daily, R30 every 5 days, counted from 2021-01-01 00:00.
  - Target the top 5 scores in TEST U; keep a coin while its rank ≤ 10.
  - Orders fill at the next bar open. Buy = min(1.00 × equity / 5, cash / (1 + cost)).
- **Missing bar:** a missing bar trades and marks at the last close.
- **Delisted coin:** sold at its last real close.
- **Comparators (same window 2021-01-01..2026-09-30, 100 % invested):**
  - 1D Step 19 rule (`U_AI_predictions.csv`). It must reproduce $74,452 (± $1), as shown to the user before.
  - CONTROL brain.
  - BTC hold.
- **Max drawdown and Calmar:** measured on equity at each UTC day close, the same as the 1D system.

## Gates (2 brains → Bonferroni 98.75 % CI for skill)
- **G0 integrity:**
  - TEST U equals the Step 19 file.
  - The 1D comparator reproduces $74,452 ± $1.
  - The 4H-vs-1d cross-check mismatch share is < 1 % of coin-days.
- **G1 pipeline (on R6):** planted (label + N(0, 2.79)) AUC ≥ 0.55 AND leak (the R6 relative return) AUC > 0.95.
- **G2 skill (per brain):** AUC 98.75 % month-block CI low > 0.50 AND AUC > its CONTROL.
- **G3 trading (per brain):**
  - (a) CAGR > 0
  - (b) Calmar > 1D Step 19 (100 %), > CONTROL and > BTC hold
  - (c) per-trade net mean 95 % CI low > 0
  - (d) CAGR > 0 at a cost of 0.40 % per fill
- **G4 untouched-time confirmation (per brain, frozen final brain):** 2018-02..2019-12 U-row AUC 95 % CI low > 0.50.
- **Decision:**
  - G1 fails → `INVALID`.
  - A brain passes G2, G3 and G4 → `PASS_R{h}`; if both pass, the higher Calmar wins. It becomes a candidate sleeve for Step 27; forward paper first.
  - G2 and G4 pass but G3 fails → `SKILL_ONLY`.
  - Otherwise → `FAIL`.

## Honest limitations
- **Cost:** the R6 rule trades daily, and Step 14 showed that 1-day edges can be eaten by cost. This is why both h are tested and G3(d) exists.
- **Shared history:** the 2021–26 test path was already used for 1D. 4H brains have never been trained or tested on it, and 2018–19 is a second, earlier path.
- **Execution:** trading at the next 4H open assumes the order executes at that open (no slippage beyond cost).

## Verification
`src/audits/verify_step23_claims.py`:
- re-derives a sample of 4H bars and labels from raw 1h files;
- recomputes the AUCs (Mann-Whitney);
- re-simulates the AI portfolios with separate code;
- recomputes the gates.
