# DISC: coverage audit + discovery measurements (pre-registered 2026-10-20, before any D-result is computed)

**Why.** The user asked for missing / gaps / add-ons / improvements / enhancements: which indicator, strategy, timeframe, mathematics, AI brain, training and testing was left out, found through search, analysis and discovery, in the same discipline. TFX-S was a quality audit; it was not this. This study has two parts:
- **C0:** a documented coverage matrix.
- **D1–D6:** descriptive measurements of the uncovered items for which we hold verified data.

This is not an A0 trial. Every cell measured here adds to the multiple-testing count that a later trial must carry. All data from 2020 to 2026-09 is "seen".

## C0 Coverage matrix (documentary)
For each item, in these dimensions:
- indicators / features;
- strategy families;
- timeframes;
- data sources;
- mathematics / risk;
- AI model classes;
- training methods;
- testing methods.

Each item gets:
- a status: TESTED (file + result), PARTIAL, or NOT TESTED;
- evidence: code grep in `src/` + report file;
- external evidence, if any;
- data availability;
- a priority (H/M/L) with a one-line reason.

## Data (all already in the project, SHA-verified at download)
- Spot 5m: `data/universe_hf/5m`.
- Perp 1h: `data/futures_um/*_perp_1h.csv.gz`.
- Funding: `data/futures_um/*_funding.csv`.
- Daily metrics: `data/futures_info/*_metrics_daily.csv`, 30 coins, 2020-09 →. Columns: oi, oi_value, top_ls_acc, top_ls_pos, global_ls, taker_ls_vol.
- Premium (basis) 1d: `data/futures_info/*_premium_1d.csv`, 30 coins.
- Universes: U1 (core10); U2X (T14 PIT-liquid coins minus LUNAUSDT and STRAXUSDT, as in TFX-S).
- Windows: entries 2020-02-01 … < 2026-10-01; P1 < 2024-01-01; P2 < 2025-10-01; P3 = the rest (seen, report only).
- Seed 20261022.

## D1 Funding carry (delta-neutral)
- **Position:** long spot + short perp, equal notional, per coin. Decisions at 00:00 UTC daily.
- **D1a:** always on, from the coin's first funding row.
- **D1b:** on when the trailing 7-day mean funding rate (per 8h) > 0.0001; off when it is ≤ 0. Hysteresis: stay on between 0 and 0.0001.
- **Daily P&L per unit notional:** Σ funding received over the day (short perp receives +rate) + spot daily return − perp daily return (basis change), with closes at 00:00 UTC (spot from 5m, perp from 1h). U1 requires the liquidity rule only for U2X.
- **Cost:** each on/off switch costs spot 0.085%/side + perp 0.054%/side, i.e. a full round trip of 0.278% per on+off.
- **Reports:**
  - per universe: equal-weight daily series over the active coins, plus annualised return per unit notional and per unit capital (÷ 2, since the spot leg and the perp margin each need capital), Sharpe, MDD;
  - by year;
  - the worst 1-day basis move;
  - the maximum perp adverse move within any holding spell (a liquidation-risk proxy at 1× isolated);
  - monthly correlation with the TFX-S U1 trend-long pooled 4h–1D sleeve.

## D2 Extra indicator families with the TFX machinery
- **Machinery:** exactly as in TFX: state machines long/short, next-open fills, costs, funding, 20 random-timing controls, coin-year and **month-block** CIs.
- **Universe and TFs:** U1; TFs 15m, 1h, 4h, 8h, 12h, 1D.
- **Canonical parameters (fixed now):**

| Family | Long entry / exit | Short entry / exit |
|---|---|---|
| SUPERT | Supertrend(10, 3) direction up; exit when it flips down | Mirror |
| ICHI | tenkan(9) > kijun(26); exit when ≤ | tenkan < kijun; exit when ≥ |
| ADXDI | ADX14 > 25 and +DI > −DI; exit when ADX14 < 20 or +DI ≤ −DI | ADX14 > 25 and −DI > +DI; exit when ADX < 20 or −DI ≤ +DI |
| STOCH | %K(14) smoothed by 3 < 20; exit when > 50 | > 80; exit when < 50 |
| KSQZ | A squeeze (BB(20,2) inside Keltner(20, 1.5·ATR20)) ended on the previous bar and close > upper BB; exit when close < SMA20 | Squeeze ended and close < lower BB; exit when close > SMA20 |
| VWAP20 | close > rolling 20-bar VWAP; exit when ≤ | close < VWAP20; exit when ≥ |
| OBV | OBV > EMA20(OBV); exit when ≤ | OBV < EMA20(OBV); exit when ≥ |

- Volume comes from the 5m `volume` column, summed per bar.
- **Extra report:**
  - the correlation of each new sleeve's monthly series (TFX-S definition) with the 6 existing families at the same TF and side;
  - N_eff of the U1 sleeve set (TFX-S) with vs without the new families: the increment shows whether they add an independent bet.

## D3 Derivatives-data rules (1D, 30 coins with metrics; P&L on perp with taker cost + funding)
- **Time exit:** 5 daily bars. Entries at the next 00:00 open after the signal day.
- **Non-overlapping:** a new entry is allowed only after the previous same-side trade has exited.
- **Signals** (percentiles over the coin's own trailing 365 days, needing ≥ 180 days):

| Rule | Signal |
|---|---|
| FUNDX | 3-day mean funding ≥ 90th pct → short; ≤ 10th pct → long |
| LSCON | global_ls ≥ 90th pct → short; ≤ 10th → long |
| TOPLS | top_ls_pos ≥ 90th → short; ≤ 10th → long |
| PREMX | prem_close ≥ 90th → short; ≤ 10th → long |
| OITR | 7-day price return > 0 and 7-day oi_value change > 0 → long; both < 0 → short |

- The same random-timing control (hold = 5 bars) and month-block CIs as TFX.

## D4 Simple cross-sectional momentum rule (U2X)
- **TFs:** 4h, 8h, 1D.
- At each rebalance bar (every 5 bars), rank the eligible coins (liquid that day, ≥ 25 bars of history) by their past-20-bar return.
- Long the top quintile and short the bottom quintile, equal weight, hold 5 bars.
- **Cost:** perp taker 0.054%/side on the turnover, plus funding.
- **Reports:** the per-period mean bar return, the monthly series, Sharpe, MDD, by-year, and the correlation with the TFX-S sleeves.

## D5 Data-snooping-robust test over the TFX cells (White Reality Check + Hansen SPA)
- **Per universe** (U1, U2X): cells with n_dev ≥ 30. Statistic T_k = mean / SE (studentised) of the per-trade dev excess, and separately of net_taker.
- **Joint month-block bootstrap** (2,000 draws, all cells resampled with the same months).
- **White RC:** p = P(max_k (T*_k − T_k) ≥ max_k T_k).
- **Hansen SPA (consistent):** re-centre only the cells with T_k ≥ −√(2 · ln ln n_months); the other cells keep their null shifted by T_k.
- **Reading:** "best cell beats random / beats zero after snooping" if p < 0.05.

## D6 Crisis stress table
- **Windows:** the 8 largest non-overlapping 7-day BTC close-to-close declines in 2020-02 … 2026-09, from the 5m data resampled to 1D (objective choice, no hand-picked dates).
- **Sleeves:** for each window, the summed net_taker of the trades open during the window, attributed pro-rata by overlap in bars. This is applied to:
  - U1 trend-long pooled 4h–1D;
  - U1 RSI-long 8h–1D;
  - U2X trend-short pooled 4h–1D;
  - D1b carry (summed daily P&L in the window).
- BTC's return in each window is reported alongside.

## Verifier (`src/audits/verify_disc.py`, own code)
1. D1: recompute two coins' daily carry P&L and on/off states (1e-12) and the U1 aggregate means.
2. D2: 300 random new-family trades rebuilt with the verifier's own indicator code (entry condition, flat-before, first exit, gross, funding); the month-block readings of 3 random cells re-bootstrapped (±10% CI width).
3. D3: 100 random trades (signal percentile, entry and exit index, gross, funding) recomputed.
4. D4: 3 random rebalances recomputed (ranks, legs, period return).
5. D5: own joint bootstrap; p-values within ±0.02, and the same reading.
6. D6: windows recomputed; one sleeve's window sums exact.
7. SHAs and the protocol lock.
