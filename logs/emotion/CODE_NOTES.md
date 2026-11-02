# EMO-1: interpretation notes (written before any study result)

## Note 1 (2026-10-22, during the smoke test on 2 symbols; no portfolio or gate number has been computed)

**Missing values.**
- A metrics value ≤ 0 is treated as missing. The early ETH files hold OI-value 0 rows, which would give ±inf.
- In 2021-12 … 2022-03, `sum_toptrader_long_short_ratio` and `sum_taker_long_short_vol_ratio` are empty (checked for ETH and DOGE). From 2022-04 they are filled 288/288 per day.
- By the protocol's "complete features" rule, those early rebalances drop out, so the effective dev window starts when the four score features exist.

**Taker 1 d.**
- The mean of log(buySellRatio) over the 5 m rows with t − 1 d < create_time ≤ t − 1 min.
- At least 200 of the 288 rows are required; otherwise the value is missing.

**Portfolio.**
- Long legs 0.5/q each and short legs −0.5/q each, where q = ⌊20% of n⌋ (≥ 1).
- BTC hedge = −Σ wᵢβᵢ.
- Everything is then scaled so that Σ|wᵢ| + |hedge| = 1.
- The hedge pays no funding and is charged turnover fees like any leg.

**Fills and holding.** Fills at the open of the 1 h bar starting at t + 1 h. Held to the next rebalance's fill.

**R1 (daily).** Rebalances only at 00:00 UTC. The return is from the open at t + 1 h to the open at t + 25 h, with the funding paid in that window.

**R2.** The primary score has no candle term, so R2 equals P. The candle features are reported as rank-IC only.

**DSR.**
- The project's `n1_portfolio.dsr` on monthly returns (as E-2), N = 114, with sr_var ∈ {0.01, 0.05, 0.10} in E-2's monthly-SR units.
- G4 uses 0.05.

**ECO for G2/G3.** The E-2 daily ECO-W2 equity (`e2_daily_series.parquet`: the dev and P3 columns), turned into daily returns.

2. **Candle features with ±inf; dev not bit-reproducible (2026-10-24).**
   - **±inf.** In `panel.parquet` (bd1e40b8…), `rv_change` has 60 rows of +inf (the 167 h volatility = 0); `qv_surprise` and `wick_1d` have none.
     - There are 0 such rows in the dev window (≤ 2024-12-31): the dev candle rank-IC table is unaffected.
     - The holdout window has them. Any candle use must first treat ±inf as missing, in a pre-registered protocol.
   - **Not bit-reproducible.** The dev run changes at the 1e-14 relative level from run to run (see CODE_CHANGES of 2026-10-24); gates and decisions are unchanged.
