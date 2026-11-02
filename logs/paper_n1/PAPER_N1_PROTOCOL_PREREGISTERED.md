# PAPER-N1: forward paper recorder for the N1 portfolio, pre-registered 2026-10-20, BEFORE its first forward cycle

**Purpose.** Step 6. The only clean evidence for N1 is data after 2026-10-01, which no research step has seen. This recorder runs the frozen portfolio forward on public Binance data and writes a hash-chained paper ledger.
- **No keys and no orders.** Public endpoints only.
- **Real money:** only the user's decision, and not before ≥ 90 forward days.

**Frozen config.** `deploy/paper_n1_config.json` (SHA in the ledger, every line):
- N1 FINAL K1: 4 sleeves A/B/C/D, TFX signals, no signal stops;
- N3 X2 spot/perp routing (X3 is implicit: orders after the bar open do not pay the bar-open funding);
- the T19 safety rule exactly as adopted by `claims_n6.json`;
- T20 AI sizing only if T20 PASSED. If it passed, it is added later as a separately locked amendment, because live features need their own replay test.

**Engine.** `src/execution/paper_n1_portfolio.py`:
- One cycle per 4h boundary T. VM cron at 7 min after each close, like FR2.
- Signals are computed only from bars that closed by T. Entries and exits are priced at the open of the bar starting at T, as in the backtest. 10,000 USDT paper, month-start sizing, taker fees, real funding.
- **First cycle:** sub-signals already "on" are opened at the current open and marked `init`. This mimics a portfolio started on that day.
- Missed cycles are not back-filled. A flip seen late is not entered.

**Replay test, before deployment (gate for deployment).**
- **Run:** the same engine, in replay mode on local research data, every 4h from 2025-03-01 to 2025-10-01.
- **Compare with:** the N1 FINAL backtest ledger (`data/derived/n1/trades_K1.parquet`), A/B/C entries after 2025-03-15 (excluding `init`), plus the D legs.
- **Pass if:**
  - ≥ 95% of the backtest A/B/C entries in the window appear in the replay with the same entry time, and their prices match to 1e-9;
  - ≥ 95% of the replay entries appear in the backtest;
  - for matched trades, the exit times agree in ≥ 95%;
  - the D leg sets agree in ≥ 90% of rebalances.
- The tolerance exists because the live engine computes EMAs from a 333-day (4h) or 1,000-day (1D) window, not from 2020. Every mismatch is listed, never hidden.
- The routing flags are reported against `N3_fills.parquet`. They are not gated, because the PIT median hold is frozen in the config.

**Live checks (daily cloud check).**
- The ledger hash chain is intact.
- The config SHA is constant.
- No data errors, or the errors are listed.
- Equity and positions are reported.

**Evaluation at day 90 (report, not a gate).**
- The forward return, MTM-DD and Calmar against:
  - the backtest band (the distribution of 90-day windows in dev);
  - BTC buy-and-hold.
- The user decides.
