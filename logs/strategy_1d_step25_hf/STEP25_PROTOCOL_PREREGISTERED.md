# STEP 25 PROTOCOL — do 15m / 5m candles add to the 1h R24 brain? (pre-registered)

Written and SHA256-locked before any Step 25 model is trained. Code: `src/pipeline_1d/step25_hf_features.py`.
Spot, long-only, $10,000, 100 % invested, cost 0.25 % per fill. No GitHub action. Nothing is deployed.

## Why this question (evidence, not opinion)
- Step 24, R4 (a 4-hour holding question): AUC 0.545 was real.
  - The average net trade was −0.21 %, because the 0.50 % round trip ate the edge, and $10k became $49.
  - Step 14 showed the same at 1 day for small coins.
- A 15-minute or 5-minute holding question has smaller moves per trade and the same cost per trade, so it cannot do
  better than R4. It is not tested again: that would only spend compute to repeat a known failure.
- The useful question is whether the fine data improves the 1-day decision of the proven brain (Step 24 R24).

## Data
15m and 5m spot klines downloaded by `src/downloaders/download_hf_15m_5m.py`:
- same evidence rules (SHA256 vs `.CHECKSUM`, rows inside their month, first continuous run of months);
- fixed timestamp format;
- coins = every coin ever in the Step 23/24 TRAIN or TEST universes (2020-01..2026-09, 296 coins) plus the 2018–19 U coins (33).

## Rows
Exactly the Step 24 rows, rebuilt with `step24.build_rows`:
- TEST = Step 19 universe, all hours;
- TRAIN = top-30 reference + A coins, hours that are multiples of 3.

## New features (11, for the hour bar [t, t+1h), known at t+1h)
- Only candles with open time < t+1h are used.
- Window values are read at the last 5m candle opening in [t, t+55m] (15m: [t, t+45m]). If there is none, the feature is NaN.
- Returns across a gap are NaN.
- Minimum candles per window: 1h ≥ 8, 4h ≥ 30, 24h 5m ≥ 200, 24h 15m ≥ 60. A truncation self-test proves it: features recomputed after deleting every candle at or after t+1h must be identical, on 40 random rows.
- **From 5m candles:**
  - rv5_1h, rv5_4h: std of 5m close-to-close returns over the last 1h / 4h;
  - maxdd5_4h, maxup5_4h: last close / max (or min) of the 5m closes over the last 4h, minus 1;
  - volburst5_1h: max 5m volume in the last hour / mean 5m volume over the last 24h;
  - upshare5_4h: share of 5m candles closing above their open over the last 4h.
- **From 15m candles:**
  - ret15_last: close/open − 1 of the last 15m candle;
  - taker15_last: its taker-buy ratio;
  - std15_24h: std of 15m returns over the last 24h.
- **Ranks inside the row's universe at that hour:** xr_rv5_4h, xr_maxdd5_4h.

## Brain
- **R24_HF:** the Step 24 R24 brain (same 31 features, same HGB, same monthly walk-forward, same subsample) PLUS the 11 features (42 in total).
- **Baseline:** the saved Step 24 R24_AI predictions (`test_predictions_1h.csv`). Row alignment is asserted.
- **Frozen R24_HF:** labels known before 2026-10-01, applied to the 2018–19 rows. Compared with Step 24's saved R24_FROZEN.

## Trading
- Step 24 R24 rule: daily at 00:00 UTC, top 5, keep while rank ≤ 10, next-hour open fill, 100 %, cost 0.25 %.
- Comparator: Step 24 R24_AI = $201,548.26, Calmar 0.920 (asserted from the Step 24 claims).

## Gates
- **G0:** rows identical to Step 24; the truncation self-test passes; download SHA logs exist for every coin used.
- **G2 added skill:** AUC(R24_HF) − AUC(R24), paired month-block bootstrap (2000 reps) 95 % CI lower bound > 0.
- **G3 trading:**
  - (a) Calmar > 0.920;
  - (b) per-trade 95 % CI low > 0;
  - (c) CAGR > 0 at 0.40 %.
- **G4 untouched time:** on the 2018–19 rows, AUC(R24_HF frozen) > AUC(R24 frozen) AND its 95 % CI low > 0.50.
- **Decision:**
  - all pass → `PASS_HF_ADDS`: 15m/5m features join the 1-day brain;
  - G2 passes, others fail → `SKILL_ADD_ONLY`;
  - otherwise → `FAIL_HF_ADDS_NOTHING`: the fine data is not used, and the 1h R24 brain stays as it is.

## Honest limitations
- **Same history:** the 2021–26 path is the same one used for Steps 19, 23 and 24. Only 2018–19 and the forward log are clean.
- **Short-horizon trading:** 15m and 5m are not tested as holding periods. The reason is the R4 cost evidence above, not a missing test.

## Verification
`src/audits/verify_step25_claims.py`:
- recomputes 30 random rows' HF features from the raw 5m/15m files with separate code;
- recomputes both AUCs and the paired difference;
- re-simulates the R24_HF portfolio with separate code;
- recomputes the gates.
