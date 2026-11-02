# Master test bench for every method in `RESEARCH_METHODS_CATALOG_26_OCT_2026.md`, and Batch 1 (A1 trend + A2 oscillators). Pre-registered 2026-10-26

This protocol is locked with SHA256 before any number is computed. It is research only: no orders, and nothing live changes.

## Part 1. The bench (the same for every batch)

**Data:**
- `data/universe_hf/5m/BTCUSDT_5m_full.csv.gz` (SHA 657844920c9bd473…) on a full 5m UTC grid, 2020-01-01 … 2026-09-30.
- `data/futures_um/BTCUSDT_funding.csv`.
- **Costs:** `deploy/fees.json` v1 only.
  - futures taker round trip 0.092% (primary; long + short) + real funding;
  - spot round trip 0.170% (longs only).

**Scale:**
- Indicators are computed on aggregated bars of "scale" s ∈ {15m, 1h, 4h}.
- A scale bar covers the open times [T − s, T) and is known at T.
- The value is carried to every 5m decision bar whose close is ≥ T (no lookahead). The scale is a parameter, not a trading timeframe.

**Signal:**
- At each 5m bar close the signal is direction ∈ {+1, −1, 0}.
- **"State" signals** (e.g. price above an MA) can stay on for long periods. **"Event" signals** fire at thresholds or crosses.

**Entry:** when flat and the signal ≠ 0 → the next 5m open. One position at a time, no overlap.

**Exits:**
- **X1:** a triple barrier at ±2σ24, where σ24 = std of 5m log returns over 288 bars × √288, with a 7-day cap.
- **X2:** a fixed ±1% triple barrier, with a 7-day cap.
- **X3:** a signal-reversal exit. Exit at the open after the first decision bar whose signal is the opposite direction. 7-day cap → close.
- **Barrier rules:**
  - the fill is at the barrier, or at the bar open on a gap;
  - if one bar touches both TP and SL, SL counts.
- The engine is the one from the BTC entry study (verifier 500/500).

**Periods:** D 2020–2023, V 2024, H 2025-01-01 … 2026-09-30.
- H is used once per batch, for **all** configurations of that batch at the same time.
- No configuration is changed after H is seen.

**Metrics per configuration** (primary cost):
- n, mean net per trade, weekly-cluster t, win rate;
- TP-first rate vs p* (X1, X2);
- profit factor;
- the equity curve (one position, full allocation, compounding per trade);
- CAGR, max drawdown, share of positive months, worst month.

**Ranking (H)** = the mean of the rank positions of six measures:
- (1) mean net;
- (2) the lower bound of the weekly-bootstrap 95% CI (2,000 resamples, seed 7);
- (3) the share of positive months;
- (4) max drawdown (smaller is better);
- (5) profit factor;
- (6) the D-to-H consistency, i.e. the sign agreement of D, V and H means (0–3).

**"Edge" label (strict, all of these):**
- **G1:** H CI lower bound > 0;
- **G2:** n_H ≥ 100;
- **G3:** H mean ≥ the 95th percentile of 200 random-entry controls with the same n, direction mix and exit. Computed only for the top 20 by H mean, because of its cost;
- **G4:** H mean > 0 in both 2025 and 2026;
- **G5:** DSR > 0.95, with N = all primary configurations tested so far, across all batches.

**Reports per configuration:**
- **daily:** date, trades closed, net sum, equity;
- **monthly** and **yearly** returns;
- written as long-format parquet/CSV;
- the Hindi batch report gives the ranking, the top 20 with monthly and yearly tables, and the family summary.

## Part 2. Batch 1: the methods and their exact rules

Defaults are the textbook ones. Each rule is run on the 3 scales. "Fade" = the standard mean-reversion reading; "follow" = its opposite.

**A1 trend:**

| Rule | Definition |
|---|---|
| A1.01 a–d | close > MA(50) → +1, else −1 (state), for MA ∈ {SMA, EMA, HMA, KAMA(10, 2, 30)} |
| A1.02 | EMA20 > EMA50 → +1, else −1 (state) |
| A1.03 a | MACD(12, 26, 9) histogram > 0 → +1, else −1 |
| A1.03 b | MACD line > 0 → +1, else −1 (this also covers APO and PPO, whose signs are identical) |
| A1.04 | ADX(14) > 25: +DI > −DI → +1, −DI > +DI → −1; else 0 |
| A1.05 | Aroon(25): up > 70 and down < 30 → +1; down > 70 and up < 30 → −1; else 0 |
| A1.06 | Parabolic SAR (0.02, 0.2): close > SAR → +1, else −1 |
| A1.07 | Supertrend(10, 3): its direction |
| A1.08 | Ichimoku (9, 26, 52), cloud shifted 26: close above the cloud and tenkan > kijun → +1; below the cloud and tenkan < kijun → −1; else 0 |
| A1.09 | Donchian(20): close > the prior-20 high → +1; < the prior-20 low → −1; else 0 (event) |
| A1.10 | Keltner (EMA20 ± 2 × ATR10): close > upper → +1; < lower → −1; else 0 (event) |
| A1.11 | Linear regression slope over 20 bars: sign (state) |
| A1.13 | Vortex(14): VI+ > VI− → +1, else −1 |
| A1.14 a | TRIX(15) > 0 → +1, else −1 |
| A1.14 b | KST > its 9-signal → +1, else −1 |
| A1.15 | Heikin-Ashi: the last 2 HA candles green → +1; both red → −1; else 0 |
| A1.16 | Renko with bricks of 0.5%, 1%, 2% of price (these three brick sizes **replace** the 3 scales): the direction of the last brick |
| A1.17 | TSMOM: sign of the 20-bar return |
| A1.18 | Kaufman ER(10) > 0.5 → sign of the 10-bar change; else 0 |
| A1.19 | Choppiness(14) < 38.2 → sign of the EMA20 1-bar change; else 0 |

**A2 oscillators** (fade as listed, plus a follow version of each):

| Rule | Definition |
|---|---|
| A2.01 a | RSI(14) < 30 → +1, > 70 → −1 |
| A2.01 b | Connors RSI (3, 2, 100) < 10 → +1, > 90 → −1 |
| A2.02 a | Stochastic (14, 3, 3): %K < 20 and %K crosses above %D → +1; %K > 80 and crosses below → −1 |
| A2.02 b | StochRSI (14, 14, 3, 3): < 0.2 → +1, > 0.8 → −1 |
| A2.03 | Williams %R(14) < −80 → +1, > −20 → −1 |
| A2.04 | CCI(20) < −100 → +1, > 100 → −1 |
| A2.05 a | CMO(14) < −50 → +1, > 50 → −1 |
| A2.05 b | Ultimate Oscillator (7, 14, 28) < 30 → +1, > 70 → −1 |
| A2.06 a | MFI(14) < 20 → +1, > 80 → −1 |
| A2.06 b | BOP, SMA14: > 0 → +1, < 0 → −1 (pressure; "follow" is the natural reading, "fade" its opposite) |
| A2.07 | ROC(10) z-scored over 500 scale bars: z < −2 → +1, z > 2 → −1 |
| A2.08 | Bollinger (20, 2): close < lower → +1, > upper → −1 (this covers the z-score row A2.09: the same rule) |
| A2.11 | Fisher transform(10): < −1.5 and rising → +1; > 1.5 and falling → −1 |
| A2.12 | DPO, causal (close − SMA20 lagged 11 bars), z over 500 bars: < −2 → +1, > 2 → −1 |
| A2.13 | Awesome Oscillator (SMA5 − SMA34 of the median price) > 0 → +1, else −1 (a momentum reading; fade = opposite) |
| A2.14 a | Elder Ray: bull power > 0 and EMA13 rising → +1; bear power < 0 and EMA13 falling → −1; else 0 |
| A2.14 b | Force Index(13) sign |
| A2.15 a | Coppock sign |
| A2.15 b | TSI(25, 13) > its 7-signal → +1, else −1 |
| A2.17 | Rolling VWAP over 20 scale bars: z of (close − VWAP) over 500 bars < −2 → +1, > 2 → −1 |

**Deferred to later batches** (stated now):
- A1.12 Hilbert and A1.20 Hurst → batch A6;
- A2.10 divergences → batch A5;
- A2.16 OU / Bertram → batch A6.

## Verifier (`src/audits/verify_methods_batch1.py`, own code)

- **W1:** manifest SHAs.
- **W2:** 300 random (bar, rule, scale) signal values recomputed with plain-loop indicator code, which includes the scale aggregation and the no-lookahead carry.
- **W3:** the X3 reversal-exit trades of 5 random configurations replayed by a loop.
- **W4:** the daily → monthly → yearly report numbers of 5 random configurations recomputed from their trade lists.
- **W5:** the ranking order recomputed from the metrics table.
- **W6:** the G-gate booleans of the top 20 recomputed (random control for 2 of them).
