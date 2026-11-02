# NP2: composite of the NP1-confirmed signals, with the final test on the sealed holdout. Locked 2026-10-26

## Background
- **NP1** (SHA 9addc94b, verifier ALL PASS): 14 (feature, horizon) pairs were significant in D and confirmed in V, but no single-feature rule beat the 0.092% round-trip taker cost.
- **NP2 asks:** does an equal-weight or ridge combination raise the signal enough to pass costs?
- **H stays sealed** until the DV stage below has written `np2_selection.json` with its SHA.
- **Inputs:**
  - `logs/research_nonprice/np1_features_1h.parquet`; its SHA is in NP1 `OUTPUT_SHA256.txt`. It already holds H rows; the DV stage filters them out.
  - Costs from `deploy/fees.json`.
- **Code:**
  - main `src/research/nonprice_np2.py`, stages `DV` and `H`;
  - verifier `src/audits/verify_nonprice_np2.py` (independent).
- **Honesty note.** V was used in NP1 to confirm the features, so V is not independent for NP2 and is only a filter. The decisive test is H.

## Feature sets and signs (taken from NP1 s1_D / s1_V; the sign is that of the D mean monthly IC)

| h | Set | Features (sign) |
|---|---|---|
| 1h | ALL | OI_CHG_1H (−), OI_CHG_24H (−), FUT_TAKER_1H (−), SPOT_TAKER_1H (−), DEPTH_IMB1_1H (+), DEPTH_IMB5_1H (+), CTRL_RET_1H (−), CTRL_RET_24H (−) |
| 1h | NODEPTH | the same without the two DEPTH features |
| 4h | ALL | OI_CHG_24H (−), SPOT_TAKER_1H (−), DEPTH_IMB1_1H (+), DEPTH_IMB5_1H (+), CTRL_RET_24H (−) |
| 4h | NODEPTH | the same without DEPTH |

- **24h** has only one confirmed feature (PREM_Z, already tested in NP1 S2), so it is not part of NP2.
- **Sampling:** per horizon as in NP1 (1h: every hour; 4h: 00, 04, …, 20 UTC).
- **D:**
  - for the ALL sets, D = 2023-01-01 … 2023-12-31 (depth starts 2023);
  - for NODEPTH, D = 2020-09-01 … 2023-12-31.
- **V** = 2024. **H** = 2025-01-01 … 2026-09-30.

## Transform (past-only)
- For each feature: p = its percentile among its own sampled values in [t − 90 days, t), the same as NP1 S2 (needs ≥ 30 past values); then u = p − 0.5.
- A sample is used only if all the features of the set have a p value.

## Scores
- **EQ:** score = mean over the features of sign_f × u_f.
  - Long if score ≥ θ; short if score ≤ −θ.
  - θ ∈ {0.15, 0.20, 0.25}.
- **RIDGE:**
  - **Fit, on the D rows of that set only:** β = (XᵀX + λI)⁻¹ Xᵀy, where:
    - X = the matrix of u_f (no sign applied, no intercept);
    - y = r_h;
    - λ = 0.1 × n_D.
  - **Prediction:** pred = X β.
  - **Trading:** trade when |pred| ≥ the q-quantile of |pred| over the D rows, q ∈ {0.80, 0.90, 0.95}; the direction is sign(pred).
  - β and the thresholds are frozen after D.
- **Configs:** 2 h × 2 sets × (3 EQ + 3 RIDGE) = **24**.

## Trades
- Entry at close(t), exit at close(t + h). One trade per sample.
- Net = side × r_h − 0.092%.

## DV stage (in-sample D, filter V); it writes `np2_dv_summary.csv` and `np2_selection.json`

**Reported per config and period:**
- trades, win %;
- mean net %, weekly-cluster t;
- total;
- months positive, worst month;
- long / short means.

**Selection (mechanical).** Candidates must have D mean net > 0, D t ≥ 2.0 **and** V mean net > 0. Up to 3 of them, ranked by D t, are selected.

If no config is a candidate, H stays sealed and NP2 ends as "no edge".

## H stage (run once, only for the selected configs)

**H gate** (all must hold; the z is Bonferroni for up to 3 configs):
1. mean net per trade > 0, and the weekly-cluster lower bound at z = 2.39 is > 0;
2. ≥ 60% of the H months are positive (≥ 13 of 21);
3. the 2025 sum > 0 and the 2026-01 … 09 sum > 0.

**Outputs:** every H trade, a daily table (every H day, with zeros), the monthly table and the gate results.

## Verifier
1. Recompute every percentile, score and ridge β (with its own linear algebra), every DV / H trade and summary, and the selection.
2. Check that the DV stage read no H row.
3. Check the costs.
