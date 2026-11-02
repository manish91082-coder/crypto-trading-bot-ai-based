# EMO-1: crowding cross-section study (pre-registered 2026-10-22, before any metrics data is downloaded)

**Source:** `RESEARCH_CROWD_EMOTION_CANDLES_22_OCT_2026.md` §7.

**New research family.** It is not an ECO trial. Its own trial registry: 1 primary run plus 2 robustness runs, nothing else.

**Rules:**
- No data is looked at before this lock.
- The download (stage D) records only file SHAs and row counts.

## D. Data (stage D; `src/research/emo_download.py`)

**Source:** `data.binance.vision`, USD-M futures. The symbol list is every PERPETUAL USDT symbol in `exchangeInfo` (TRADING and SETTLING) on the download day, plus any other symbol with daily files. This keeps delisted perps in.

1. **Liquidity:** monthly `klines/<SYM>/1d` zips, 2021-11 … 2026-09, for every symbol.
2. **Eligible set:** symbols whose daily quote volume has a 30-day median ≥ 50 M USDT on at least one day in 2021-12-01 … 2026-09-30.
3. **Positioning:** daily `metrics` zips (5 m rows) for the eligible symbols, 2021-12-01 … 2026-09-30.
4. **Manifest:**
   - every zip's URL, HTTP status, SHA256 and row count, in `data/emotion/emo1_raw/manifest.csv`;
   - a 404 is recorded, not retried forever.
5. **Perp 1 h klines and funding** for returns: monthly `klines/<SYM>/1h` and `fundingRate` zips for the eligible set.

## S. Study (stage S; a later session; code and verifier written after this lock, before any result is seen)

**Universe at each 4 h close t.** Eligible symbols whose trailing 30-day median quote volume is ≥ 50 M USDT using days < t's day (point-in-time), with complete features.

**Features** (from metrics rows with create_time < t; 1 h bars closed ≤ t):
- OI value change over 1 d and 3 d;
- log global account L/S ratio (last);
- log top-trader position L/S − log global account L/S;
- mean log taker buy/sell volume ratio over 1 d;
- funding mean over 3 d;
- candle: mean wick share over 1 d, quote-volume surprise (1 d vs the previous 1 d), and the change in 1 d realized vol versus 7 d.

**Crowding score.** The mean of the cross-sectional percentile ranks of four features: OI 1 d change, retail L/S, taker 1 d and funding 3 d (high = crowded long). This is fixed; there is no fitting.

**Primary portfolio (P):**
- every 4 h;
- long the least-crowded 20%, short the most-crowded 20%;
- equal weight, beta-neutral to BTC (60-day beta), gross 1.0;
- held to the next 4 h close;
- perp taker 0.054% per side on turnover;
- real funding;
- fills at the next 1 h open after t.

**Robustness runs:**
- R1: daily rebalance (00:00 UTC);
- R2: the positioning features only. This equals P's score; the candle features are reported as a separate rank-IC table, not traded.

**Windows:**
- dev 2021-12-01 … 2024-12-31;
- **holdout 2025-01-01 … 2026-09-30, opened once**, after the dev report is written and its SHA is recorded.

**Gates (all must pass on the holdout to call EMO-1 an edge):**
- G1: net Sharpe > 0, with the 95% stationary block-bootstrap CI (20-day blocks) lower bound > 0;
- G2: daily return correlation with the ECO-W2 combination < 0.3, over the overlapping days;
- G3: Calmar of 0.8 × ECO + 0.2 × EMO > ECO alone, on both dev and holdout;
- G4: DSR > 0.95 at an SR variance of 0.05. The table also shows 0.01 and 0.10, with N = all project trials (111 + 3);
- G5: shuffled control. Crowding ranks permuted within each time step, 200 times: the real Sharpe must exceed the 95th percentile.

**Verifier.** An independent script recomputes, for 300 random (t, symbol) pairs:
- the features and ranks;
- the portfolio weights;
- the next-period return.

It must match the study within 1e-9.

**Not allowed:**
- changing features, thresholds, quantiles or costs after any result;
- using the holdout before the dev report's SHA is recorded.
