# Spot "graded entry + averaging down + take profit, no stop loss" and spot + perp combinations: pre-registered research (2026-10-24)

This protocol is locked with SHA256 before any result is computed. It is a historical simulation only: no orders, nothing deployed.

## Questions (user, 2026-10-24)

- **Q1.** The method:
  - buy 2% or 5% of the balance on spot, sized by how "perfect" the entry is;
  - hold;
  - sell everything at a fixed take-profit % (fixed, or set by market condition);
  - **no stop loss**;
  - if the price falls, hold and buy again deeper, where the market turns up.
  - How does it behave, and with what risk?
- **Q2.** Spot + futures: long spot with short perps (cash-and-carry), a short hedge in bear markets, or a short after a rise. What do they do?
- **Q3.** How could 10,000 USDT be split between such parts and the current ecosystem? This is an evidence-based scenario table, not personal advice.

## Data (SHA256 of every file used goes into `logs/research_spot_dca/input_manifest.csv`)

- **Spot daily bars:** `data/universe_all/1d/<SYMBOL>_1d.csv`.
  - All Binance USDT spot pairs, **including delisted ones** (e.g. LUNA, FTT, SRM, SXP); bars are UTC days.
  - A coin whose file ends before 2026-09-30 is treated as **delisted on its last bar**.
- **Perp funding:** `data/futures_um/<SYMBOL>_funding.csv`.
- **Ecosystem series for Q3:** `data/derived/eco/e2_daily_series.parquet`.
  - The ECO-W2 columns are joined exactly as in `src/research/emo1_study.py` `evaluate`: columns ending "|ECO-W2", excluding "P1|" and "P2|"; pct_change.
  - This is the backtest series of the deployed design, and it is labelled as such.
- `archive/` is not used.

## Universe (point in time, decided at the close of day t)

- At least 200 daily bars up to t.
- The median quote volume of the last 30 days is ≥ 10 M USDT.
- **Excluded:**
  - stable / fiat bases: USDC BUSD TUSD FDUSD USDP DAI PAX USDS USDSB SUSD UST USTC EUR GBP AUD BRL TRY AEUR EURI XUSD USD1 BFUSD RLUSD;
  - leveraged tokens (symbols ending UPUSDT, DOWNUSDT, BULLUSDT, BEARUSDT).

## Q1 strategy (primary configuration P; fixed, not optimised)

All decisions use the close of day t. All fills are at the open of day t+1.

- **Entry grade** (coin with no open position):
  - dd90 = close_t / max(high, last 90 days incl. t) − 1;
  - RSI14 (Wilder);
  - reversal = close_t > high_{t−1}.
  - **Grade A:** dd90 ≤ −30%, RSI14 ≤ 35 and reversal → buy **5% of current equity**.
  - **Grade B:** not A, dd90 ≤ −15%, RSI14 ≤ 45 and reversal → buy **2% of current equity**.
  - If cash is short, the order is: A before B, then deeper dd90, then symbol. A buy that does not fit in cash is skipped.
- **Deep buy (add):** for a coin with an open position:
  - condition: close_t ≤ 0.85 × the last buy price, and reversal;
  - size: 5% of equity if the coin's grade-A conditions also hold, otherwise 2%;
  - at most **4 adds** per position (5 buys).
- **Take profit:** sell the whole position at avg_entry × (1 + TP), with **TP = 10%** in P.
  - The fill is checked on every day from the buy day on: open ≥ TP price → fill at the open; else high ≥ TP price → fill at the TP price.
  - avg_entry is the quantity-weighted fill price.
- **No stop loss.** A delisted coin is sold at its last close (generous: in reality the holder might get less).
- **Fees:** 0.085% per side (the project's spot fee). Idle cash earns 0. Equity is marked at the daily close.

## Variants (all reported; none is chosen by its result)

- **TP:** 3%, 5%, 10% (P), 20%; and "regime TP".
  - Regime TP: 5% if BTC close < its 200-day SMA at the time of the buy, else 10%. It is recomputed at every add.
- **Adds:** max 4 (P), 0 (no averaging down), unlimited.
- **Fees:** 0.2% per side (stress).
- **Comparison only (the user wants no stop):** P with a −50% stop on avg_entry.

## Controls

- **Random entries:** 100 seeds.
  - The same days and the same number of new entries per day as P, with the same grade sizes.
  - The coins are drawn at random from the eligible, unheld coins. The same adds and exits apply (an add is triggered by price only, with no grade condition).
  - **Report:** P's percentile in the control distribution of CAGR and of max drawdown.
- **Benchmarks:** BTC buy-and-hold; ETH buy-and-hold.

## Periods

| Run | Period |
|---|---|
| Full | 2020-07-01 … 2026-09-30 |
| Dev | 2020-07-01 … 2023-12-31 |
| Holdout | 2024-01-01 … 2026-09-30 (a fresh 10,000 start) |

The holdout is reported for P and the controls with the same fixed rules. No parameter is chosen on any period.

## Metrics

- Final equity, CAGR, max drawdown (daily mark), Sharpe (daily, √365), worst month.
- Round trips; share closed by TP; median and maximum days to TP.
- Positions closed by delisting and their loss.
- Positions open at the end and their unrealized P&L; longest-held position.
- Maximum and average capital deployed.
- Worst single-coin loss in USDT.

## Q2 (spot + perp; fixed rules)

- **B1 cash-and-carry:** long spot + short perp of equal notional, on BTC and ETH, held continuously.
  - Income = funding received (short side) − entry and exit fees, 4 × 0.05% once.
  - Variant: in only while the trailing 7-day mean funding > 0. Each switch costs 4 legs × 0.05%.
  - Reported per year: net carry % on notional, and the share of funding events < 0.
  - **Margin need:** the maximum 7-day and 30-day price rise of BTC and ETH, which a 1× short's margin must survive without a top-up.
- **B2 bear hedge on P:** while BTC close < SMA200, short a BTC perp with notional = P's spot exposure at the prior close.
  - It pays and receives BTC funding; fees 0.05% per traded notional.
  - Reported: P vs P + hedge (CAGR, max drawdown).
- **B3 short after a rise:** when a coin's (BTC, ETH) 30-day return > +30%, short 1× notional at the next open for 30 days. Funding included, no stop. Reported per trade and in total.

## Q3 (allocation scenarios)

- Daily series on the common dates: ECO-W2 (backtest), P (this study) and B1 BTC carry with the funding filter.
- Mixes of 10,000, rebalanced monthly (ECO / P / carry):
  - 100/0/0;
  - 80/20/0;
  - 70/15/15;
  - 60/20/20;
  - 50/25/25;
  - 0/100/0;
  - 0/0/100.
- Reported: CAGR, max drawdown, Sharpe, and the correlations.
- These are research scenarios, not advice.

## Verifier (independent; `src/audits/verify_spot_dca.py`)

- **V1:** the input manifest SHAs.
- **V2:** 200 random (coin, day) grade decisions recomputed from the raw CSV by loops.
- **V3:** P's trade ledger replayed by an independent cash loop (fills from the raw opens and highs, fees) → the final equity and the daily equity within 1e-6.
- **V4:** 30 random TP fills satisfy the fill rule.
- **V5:** B1 funding sums per year recomputed from the raw CSV.

## Output

- `logs/research_spot_dca/` (results, ledgers, claims JSON with SHAs).
- The Hindi report `RESEARCH_SPOT_DCA_SPOT_FUTURES_24_OCT_2026.md` in the project root.
