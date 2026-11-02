# Spot long-only sleeve (10/20/30% of capital): buy when the market turns up, hold, sell. Pre-registered (2026-10-24)

This protocol is locked with SHA256 before any result is computed. It is a historical simulation only: no orders, nothing deployed.

## Question (user, 2026-10-24)

10,000 USDT trades in the ecosystem. Should 10, 20 or 30% of it be put into **spot only**: buy when the market turns up, hold, then sell? Which rule, with what evidence, and where does the profit come from?

## Evidence base used to FIX the rules (no parameter is searched)

- **Detzel, Liu, Strauss, Zhou & Zhu (2021), Financial Management 50(1):** the price / moving-average ratio forecasts Bitcoin returns in and out of sample. An MA-timing rule beats buy-and-hold on Sharpe.
- **Liu & Tsyvinski (2021), Review of Financial Studies 34(6):** strong time-series momentum in crypto.
- **Liu, Tsyvinski & Wu (2022), Journal of Finance:** market, size and momentum factors in the cross-section.
- Windows are the conventional ones: 200-day SMA, 50/200 cross, 28-day momentum, 5 of the top 20. They are fixed here.

## Data (SHA256 of every file → `logs/research_spot_sleeve/input_manifest.csv`)

- **BTC and ETH daily:** `data/universe_pre2020/1d/<S>_1d.csv` (2017-08-17 … 2019-12-31) joined to `data/universe_all/1d/<S>_1d.csv` (2020-01-01 …).
- **Cross-section (S5):** `data/universe_all/1d/*_1d.csv`, including delisted coins. The exclusions are the same as the spot DCA study: stables, fiat, leveraged tokens.
- **ECO for the mix:** `data/derived/eco/e2_daily_series.parquet`, ECO-W2 columns joined as in `emo1_study.evaluate`. It is a backtest series and is labelled so.
- `archive/` is not used.

## Rules

- Decisions use the close of day t; fills are at the open of day t+1.
- **Fees** 0.10% per side (stress 0.25%). Cash earns 0.
- A coin that delists while held is sold at its last close.
- **B0 (benchmark):** BTC buy-and-hold.
- **B1 (benchmark):** 50/50 BTC/ETH buy-and-hold, rebalanced monthly.
- **S1 BTC SMA200:** hold BTC while close > SMA200, else USDT.
- **S2 BTC + ETH SMA200:** half the sleeve each; each half holds its coin while close > its own SMA200, else USDT.
- **S3 BTC 50/200 cross:** hold BTC while SMA50 > SMA200.
- **S4 BTC 28-day momentum:** each Monday close, hold BTC for the week if close / close 28 days earlier > 1, else USDT.
- **S5 cross-sectional momentum with a regime filter:**
  - Each Monday close, if BTC close > its SMA200: hold the 5 coins with the highest 28-day return, equal weight, among the 20 most liquid (30-day median quote volume).
  - Eligible coins have ≥ 200 bars.
  - Otherwise hold USDT.
- **S6 "turn up after a big fall":**
  - Buy BTC when close is ≥ 30% below its 365-day high AND close crosses above SMA50 (close_{t−1} ≤ SMA50_{t−1}, close_t > SMA50_t).
  - Sell when close < SMA50.

## Periods

| Period | Dates | Note |
|---|---|---|
| P0 | 2018-03-06 … 2019-12-31 | pre-2020 data; S5 skipped |
| Dev | 2020-07-01 … 2023-12-31 | |
| Holdout | 2024-01-01 … 2026-09-30 | |
| Full | 2020-07-01 … 2026-09-30 | |

Each period starts from 10,000 in USDT. The indicators use the history before the start.

## Controls and statistics

- **Random timing (S1, S2, S3, S4, S6):** 200 seeds. The rule's in-market spells and out-of-market spells (lengths in days) are shuffled independently and laid out alternately from the same start state. This keeps the time in market and the number of trades.
  - Report the rule's percentile of Sharpe (full period).
- **DSR:** the deflated Sharpe ratio (daily returns, N = 6 strategies, sr_var = the variance of the 6 strategies' daily Sharpe), as information.

## Gates (a "candidate for a forward paper test" must pass G1–G3; nothing goes live from this study)

- **G1:**
  - In dev AND in holdout, Sharpe ≥ B0's Sharpe;
  - and max drawdown at least 10 percentage points smaller than B0's in dev AND in holdout.
- **G2:** the random-timing percentile of Sharpe is ≥ 90% (full period). S5 has no timing control; it uses G2' instead.
  - **G2' (S5):** its full-period Sharpe exceeds S1's.
- **G3:** CAGR > 0 in P0 (except S5), in dev and in holdout.

## Mix with the ecosystem (information; research scenarios, not advice)

- For each strategy and share s ∈ {10%, 20%, 30%}: total = (1 − s) ECO-W2 + s × sleeve, rebalanced monthly, over the common dates.
- Report CAGR, max drawdown, Sharpe, and the correlation with ECO.

## Verifier (`src/audits/verify_spot_sleeve.py`, no shared code)

- **V1:** the manifest SHAs.
- **V2:** S1, S3, S4 and S6 equity recomputed by plain loops from the raw CSVs for every period → final equity within 1e-6 and the trade count equal.
- **V3:** S5's holdings on 20 random Mondays recomputed by loops (liquidity rank, 28-day return, the regime).
- **V4:** one 20% mix recomputed by a loop.

## Output

- `logs/research_spot_sleeve/` (results JSON with SHAs).
- The Hindi report `RESEARCH_SPOT_SLEEVE_24_OCT_2026.md` in the project root.
