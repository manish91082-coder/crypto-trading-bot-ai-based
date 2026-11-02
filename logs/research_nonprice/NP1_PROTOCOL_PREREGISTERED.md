# NP1: does non-price information (funding, basis, open interest, positioning, order flow, order book) predict BTC returns beyond costs? Locked 2026-10-26

## 0. Why, and the honesty rules

- **The question.** The 9-month study (`logs/oracle_9m_2026`) and the methods bench showed that rules built only on price have a gross return of about 0 per trade. NP1 asks whether information other than price changes that.
- **The data.** Binance public files, downloaded 2026-10-26 with the user's permission, every zip checksum-verified (`data/external/binance_public/DATA_ACQUISITION.md`, `clean/QC_REPORT.md`).
- **Separate from:** the methods bench (Batch 1) and `oracle_9m`. NP1 has its own code and folder.
- **Code:**
  - main: `src/research/nonprice_np1.py`;
  - verifier: `src/audits/verify_nonprice_np1.py` (independent, plain loops / its own pandas code, no import from the main code).
- **Split** (the features below have not been looked at in any period before this lock):

| Period | Dates | Use |
|---|---|---|
| **D** (discovery) | 2020-09-01 … 2023-12-31 | finding candidates |
| **V** (validation) | 2024-01-01 … 2024-12-31 | first confirmation |
| **H** (holdout) | 2025-01-01 … 2026-09-30 | **sealed.** Opened once, through Amendment 1, only for the configs that pass V |

- **Price paths of every period have been seen** in earlier price-only work. This is recorded; it does not leak the new features.
- **Depth features** exist only from 2023-01-01. Their D is 2023-01-01 … 2023-12-31.
- **Costs** come only from `deploy/fees.json`: futures taker 0.046% per side, i.e. 0.092% per round trip.
- **Not claimed:** a rule that fails here is not called "close". Every number has a CI.

## 1. Data alignment (no lookahead)

**Decision times t:** every hour on the hour, UTC. The price is the futures 5m close of the bar ending at t (`clean/fut5m.parquet`).

**Availability lags:**

| Source | Value usable at t |
|---|---|
| A 5m bar (fut, spot, premium) with open time b | for t ≥ b + 5 min |
| A metrics row with create_time c | for t ≥ c + 5 min (one safety bar) |
| A depth 5m mean of [b, b + 5m) | for t ≥ b + 5 min |
| Funding settled at calc_time s | for t ≥ s |

**Targets:** the forward futures return r_h = close(t + h) / close(t) − 1, for **h = 1 h, 4 h, 24 h**.

**Sampling** (non-overlapping per horizon):

| h | Decision times |
|---|---|
| 1 h | every hour |
| 4 h | t ∈ {00, 04, …, 20} |
| 24 h | t = 00:00 |

Any sample with a missing feature or a missing target is dropped. The counts are reported.

## 2. Features (18, fixed now; z-scores use only past values)

| Id | Definition at t |
|---|---|
| FUND_LVL | last settled funding rate |
| FUND_Z | (FUND_LVL − mean) / sd of the 90 settlements before it (inclusive of it) |
| PREM_1H | mean premium-index close over the 12 bars ending at t |
| PREM_Z | (PREM_1H − mean) / sd of the hourly PREM_1H over the trailing 30 days (720 values) |
| BASIS | fut close / spot close − 1 at t (spot = `data/universe_hf/5m`) |
| OI_CHG_1H | ln(OI_t / OI_{t−1h}); OI = sum_open_interest_value of the last available metrics row |
| OI_CHG_24H | ln(OI_t / OI_{t−24h}) |
| OI_RET_4H | ln(OI_t / OI_{t−4h}) × sign(ret_4h); ret_4h = futures close(t) / close(t − 4 h) − 1 |
| TOP_LS_Z | z of sum_toptrader_long_short_ratio vs the trailing 30 days of hourly values |
| RETAIL_LS_Z | z of count_long_short_ratio, the same way |
| TOP_MINUS_RETAIL | TOP_LS_Z − RETAIL_LS_Z |
| TAKER_LS_1H | ln of the mean sum_taker_long_short_vol_ratio over the 12 metrics rows ending at t |
| FUT_TAKER_1H | Σ taker_buy_volume / Σ volume over the 12 futures 5m bars ending at t, − 0.5 |
| SPOT_TAKER_1H | the same with spot taker_buy_base / volume |
| DEPTH_IMB1_1H | mean imb1 over the 12 depth bars ending at t (2023+) |
| DEPTH_IMB5_1H | mean imb5, the same way (2023+) |
| CTRL_RET_1H | futures close(t) / close(t − 1 h) − 1 (price-only control) |
| CTRL_RET_24H | futures close(t) / close(t − 24 h) − 1 (price-only control) |

"Hourly values" means the feature evaluated at each decision hour.

## 3. Stage 1: information test (no trading), on D

**Test statistic** for each (feature, h), 54 tests:
1. Compute the Spearman rank correlation (IC) between the feature and r_h within each calendar month.
2. **t_IC** = mean of the monthly ICs / (sd / √n_months).

**Also reported:**
- the pooled Spearman IC;
- the Q5 − Q1 spread of mean r_h, with quintiles from the D-period pooled values (descriptive only);
- n.

**S1 gate:** |t_IC| ≥ **3.0** in D. This is roughly a Bonferroni level for 54 tests.

**For the S1 survivors only:** the same statistic on V. "S1-confirmed" needs the same sign and t_IC ≥ 2.0 in absolute value.

## 4. Stage 2: trading rule for each S1-confirmed (feature, h)

**Signal**
- At each sampled t, take the feature's percentile within the **trailing 90 days** of its own sampled values (no future values).
- **Top quintile** (≥ 80th percentile) → a position in the direction sign(IC_D). That is long if IC_D > 0.
- **Bottom quintile** (≤ 20th percentile) → the opposite position.
- Otherwise flat.

**Trade:** entry at close(t), exit at close(t + h). One trade per sample; no overlap by construction. Net = signed r_h − 0.092%.

**Reported**
- trades, win %;
- mean net per trade, with a weekly-cluster t;
- total;
- months positive;
- worst month;
- long vs short split.

**S2 gate, on V:** all three must hold:
1. mean net > 0;
2. weekly-cluster t ≥ 2.0;
3. ≥ 7 of 12 months positive.

For information, S2 is also reported on D (in-sample).

## 5. Holdout (H)

Amendment 1 is written only after S2.
- It lists the S2-passing configs and the code SHA, and opens H once.
- **H gate:**
  1. mean net per trade > 0, with the weekly-cluster 95% lower bound > 0;
  2. ≥ 60% of months positive;
  3. both 2025 and 2026-01 … 09 sums > 0.
- If no config passes S2, H stays sealed, and the result is reported as "no non-price edge in NP1".

## 6. Outputs (`logs/research_nonprice/`)

| File | Contents |
|---|---|
| `np1_features_1h.parquet` | all features + targets at every decision hour, with D / V / H labels. The H rows stay unread until Amendment 1; the code writes them, but stage-1/2 code filters them out |
| `s1_D.csv`, `s1_V.csv` | Stage 1 |
| `s2_trades.parquet`, `s2_summary.csv`, `s2_monthly.csv` | Stage 2 |
| `run_log.txt`, `OUTPUT_SHA256.txt` | log and output SHAs |

## 7. Verifier

`verify_nonprice_np1.py` recomputes:
1. a random sample of 2,000 feature rows from the raw clean tables, with its own alignment code;
2. every monthly IC and t_IC of S1 (D and V);
3. every S2 trade and its summary;
4. that no H-period row entered S1 / S2;
5. that the fees come from `fees.json`.
