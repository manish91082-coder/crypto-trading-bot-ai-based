# TFX: timeframe edge map, 1m → 1M (pre-registered 2026-10-20, before any result of this study is computed)

## Purpose
The user asked for a ground-level, data-verified picture, timeframe by timeframe, of:
- the classic strategy and indicator families;
- long vs short;
- spot vs perp costs;
- whether any of them carries timing information beyond random entries.

This feeds the "collective multi-timeframe brain" research. It is a **descriptive study**: no model is fitted and no rule is adopted from it.
- It is **not** an A0 trial.
- Any cell later picked from this map becomes its own pre-registered trial, with forward data as the clean holdout.
- The number of cells tested here (reported in claims) must enter that trial's DSR / multiple-testing count.
- 2020-02 … 2026-09 is all "seen" data (Part 3 errata #4).

## Data
- **Main source:** `data/universe_hf/5m/<coin>_5m_full.csv.gz` (Binance spot 5m, SHA-verified at download).
- **Resampling:** left-closed and left-labelled in UTC:
  - 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1D with pandas rules 5min / 15min / 30min / 1h / 4h / 8h / 12h / 1D;
  - 1W = `W-MON`, closed left, labelled left (Monday 00:00 UTC weeks, as Binance);
  - 1M = `MS`.
- **1m:** `archive/cleanup_2026_10_15/data/raw/<coin>_1m_Raw_5Years.csv(.gz)` (CLAUDE.md exception), 10 core coins. It is used **only after gate G1**:
  - aggregate 1m → 5m and compare OHLC with `universe_hf` 5m, per coin and month;
  - a month is usable only if every compared 5m bar matches (rtol 1e-9) and the 1m month has no duplicate or non-monotonic timestamps;
  - unusable months are dropped and listed.
- **Funding:** `data/futures_um/<coin>_funding.csv`.
- **Liquidity:** `data/futures_um/<coin>_perp_1h.csv.gz` `quote_volume`.
- **1Y:** not simulated (≤ 7 bars per coin). The existing Swing Anatomy 1Y/6M table (`logs/research_swing_anatomy/DE_1Y_6M_anatomy.csv`) is cited as-is.

## Universes
| | Coins | Timeframes | Entries |
|---|---|---|---|
| **U1 core10** | ADA, BNB, BTC, DOGE, DOT, ETH, LINK, LTC, SOL, XRP | 1m (G1 months only), 5m … 1M | All |
| **U2 liquid** | All coins of the T14 candidate list that have a `universe_hf` 5m file | 5m … 1W | Only when the T14 point-in-time liquidity rule holds at the entry day (30 prior full days, median daily perp quote volume ≥ 50M USDT, ≥ 20 days) |

## Window and periods
- Entries from 2020-02-01 to before 2026-10-01.
- P1 < 2024-01-01; P2 < 2025-10-01; P3 = the rest.
- dev = P1 + P2. P3 is reported, never used for the reading.
- Indicator warm-up uses earlier bars (from 2020-01-01).

## Families (canonical parameters, fixed here, never tuned)
Each family is run as two independent state machines, long and short.
- A signal at the close of bar t is filled at the open of bar t+1.
- An exit signal at the close of bar u is filled at the open of bar u+1.
- No stops: the stop and exit research was A4. These are timing families.

| Family | Long entry / exit | Short entry / exit |
|---|---|---|
| TSMOM | close/close[t−20] − 1 > 0; exit when ≤ 0 | < 0; exit when ≥ 0 |
| EMAX | EMA20 > EMA50; exit when ≤ | EMA20 < EMA50; exit when ≥ |
| MACD | MACD(12,26) > signal(9); exit when ≤ | < ; exit when ≥ |
| DONCH | close > max(high[t−20..t−1]); exit when close < min(low[t−10..t−1]) | close < min(low[t−20..t−1]); exit when close > max(high[t−10..t−1]) |
| RSI | RSI14 (Wilder) < 30; exit when RSI14 > 50 | > 70; exit when < 50 |
| BB | close < SMA20 − 2·sd20; exit when close ≥ SMA20 | close > SMA20 + 2·sd20; exit when close ≤ SMA20 |

- A trade still open at the end of the data is dropped.
- The trend families (TSMOM, EMAX, MACD, DONCH) and the mean-reversion families (RSI, BB) are reported as groups too.
- The ZigZag swing-following family is **not** re-run. The Swing Anatomy "realizable follow" table (`logs/research_swing_anatomy/realizable_follow_zigzag_K3.txt`) is cited for it.

## Per trade
- **Gross:** long `exit_open / entry_open − 1`; short `(entry_open − exit_open) / entry_open`.
- **Funding (perp):**
  - the sum of funding rates with entry_time < time ≤ exit_time;
  - long pays +rate, short receives +rate;
  - a trade before the coin's first funding row is excluded from the perp columns.
- **Round-trip costs:**
  - spot taker 0.17% (long only; spot cannot short);
  - perp taker 0.108% (0.054% per side, A-series base);
  - perp maker 0.04%.
- **Net columns:** `net_spot = gross − 0.0017` (long only); `net_perp_taker = gross − 0.00108 − funding`; `net_perp_maker = gross − 0.0004 − funding`.
- **Random-timing control (per trade):**
  - 20 random entry bars drawn uniformly from the same coin's eligible bars in the same period (U2: liquid days only), seed 20261020;
  - each with the same side and the same holding length in bars;
  - `ctrl` = the mean gross of the 20;
  - `excess = gross − ctrl`. This removes drift and "average move over that hold". What remains is timing information.

## Per cell (universe × TF × family × side)
Reported values:
- n;
- trades per coin-year;
- mean and median hold (bars and hours);
- mean and median gross;
- mean gross ÷ perp-taker cost;
- mean net_spot / net_perp_taker / net_perp_maker for dev, P1, P2 and P3;
- mean excess;
- share of positive coin-years for net_perp_taker.

**CIs:** block bootstrap over coin-year blocks, 2,000 draws, seed 20261020:
- 95% CI;
- Bonferroni CI at 1 − 0.05/N_cells, where N_cells = the number of cells with n ≥ 30 in that universe.

Applied to dev mean net_perp_taker, dev mean net_spot (long), and dev mean excess.

**Readings (labels only, not adoption):**
- **COST-VIABLE (perp):** dev net_perp_taker 95% CI low > 0 **and** mean > 0 in P1 **and** in P2. **STRICT** if the Bonferroni CI low > 0 as well.
- **COST-VIABLE (spot):** the same for net_spot (long cells).
- **TIMING:** dev excess 95% CI low > 0 (STRICT with Bonferroni). Negative TIMING is reported too (CI high < 0 = worse than random).
- **Cells with n < 30:** "too few"; no reading.

## Timeframe statistics (U1 + the 8 Part 3 coins)
Per coin and TF, on close-to-close simple returns:
- ac1 over 2020-01-01 … 2026-09-30;
- ac1 from 2024-10-01;
- VR(2), VR(4), VR(8), with VR(q) = var(c/c[t−q] − 1) ÷ (q·var(1-bar return)), overlapping;
- median |close − open| / open;
- median (high − low) / open;
- 0.085% ÷ median body (the Part 3 definition).

**G0 (replication of Part 3, `research_notes/AI ब्रेन टाइमफ्रेम सिंक अंतिम सत्यापन/internal_tf_stats.md`):**
- recompute the 8-coin per-coin table with the definitions above;
- PASS per column and TF if every value matches at the printed precision (±1 in the last printed digit);
- mismatches are reported as findings about Part 3 (its exact definitions were not written down), never tuned away.

## Verifier (own code, `src/audits/verify_tf_edge_map.py`)
1. G1: recompute the 1m → 5m match for 3 coins × 3 random months.
2. For 300 random trades per universe, rebuild the bars from raw 5m (or 1m) with own code, re-derive the entry and exit indices from own indicator code, and check gross and funding.
3. Recompute two random cells' dev mean gross/net from own trades (1e-12), and their mean excess with the verifier's OWN random draws (different seed): |study − verifier| < 3 standard errors of the verifier's estimate. All cell-table means are recomputed from the trade file (1e-12).
4. Recompute 3 TF-stat rows and G0.
5. Claims, SHAs and the protocol lock.
