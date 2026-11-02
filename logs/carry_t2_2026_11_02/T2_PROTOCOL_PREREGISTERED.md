# T2-CARRY: forward paper test of cash-and-carry. Pre-registered 2026-11-02

Locked by SHA-256 before the first forward funding event. The first event that can count is 2026-11-02 16:00 UTC.

## Why

- Item T2 of `CONSOLIDATED_ACTION_PLAN_28_OCT_2026.md`. The user approved it on 2026-11-02, asking for the same discipline as the other forward tests.
- `RESEARCH_SPOT_DCA_SPOT_FUTURES_24_OCT_2026.md` measured funding income only. It left out the spot and perp price gap (basis), and it never tested live data.
- The question: does a live, direction-neutral carry position earn more than its costs, once funding, basis and all fees are counted?

## What is expected, stated before any forward number

From `PRELOCK_HISTORY.json` (`src/research/carry_t2_prelock.py`, already open data, Binance funding to 2026-09-30):

| Rolling 90-day net, % of capital | n | p5 | p50 | p95 | share ≤ 0 |
|---|---|---|---|---|---|
| Since 2023 | 1,280 | -0.083 | +0.586 | +2.485 | 7.6% |
| Since 2025 | 549 | -0.246 | +0.376 | +0.677 | 17.7% |
| 2026 only | 184 | -0.334 | -0.010 | +0.551 | 50.5% |

- **2026 carry is about break-even after costs.** A FAIL or a near-zero result is a likely outcome, and this test is not expected to find large income.
- The windows overlap, so these are descriptive and not independent samples.

## Positions

- **Primary track C-MIX:** paper capital 10,000 USDT, of which 5,000 is notional (2,500 BTC, 2,500 ETH) and 5,000 is margin. Capital = 2 × notional, as in the study.
- Long spot + short perp of equal entry notional, 1× per coin, held continuously. No funding filter, no rebalancing, no top-up, no leverage change.
- **Information-only tracks:** C-BTC and C-ETH, each on 5,000 capital. They are parts of C-MIX. They are not decision inputs and cannot replace it.

## Data

- **Spot:** Binance spot 1h klines from `data-api.binance.vision`.
- **Perp price and funding:** Bybit linear BTCUSDT and ETHUSDT, public REST (8h funding). Binance futures endpoints are blocked from the laptop. This is the same proxy as LPT-1 and FWD-R2.
- **Proxy check, 2026 to 30 September:** funding sum on notional Binance vs Bybit: BTC 2.20% vs 1.82%, ETH 1.45% vs 1.80%. Per-event correlation is 0.58 and 0.68, so the proxy is fair for sums and not for single events.
- **Limit:** this measures carry on Bybit funding, not Binance funding. See Reconciliation.

## Timing

- FORWARD_START = 2026-11-02T08:00:00Z. Entry price = the open of that 1h bar on each leg.
- FORWARD_END = 2027-01-31T08:00:00Z, which is 90 days and 270 funding events per coin.
- Funding counted = events with START < time ≤ END. The 08:00 event of the start day is excluded.

## Accounting (per coin, N = entry notional)

- qs = N / spot_entry, qp = N / perp_entry.
- Funding cash per event = rate × qp × (perp open of the hour of the event). A positive rate is income to the short.
- Fees, read once from `deploy/fees.json` `rules` and frozen in `carry_freeze.json`: fs = `paper_spot_per_side`, ff = `paper_futures_taker_per_side`. Never hard-coded.
- Entry cost = N × (fs + ff). Exit cost at any mark = fs × qs × spot + ff × qp × perp, booked in full from the start.
- Equity at the close of each hour = capital + qs × (spot − spot_entry) − qp × (perp − perp_entry) + funding so far − entry cost − exit cost at that mark.
- Margin ratio per coin, using the hour's perp high = (N − qp × (high − perp_entry) + funding so far) / (qp × high).
- Idle margin earns 0. Bybit and Binance venue transfer cost and exchange failure are not modelled.

## Verdict: on C-MIX at FORWARD_END, no earlier verdict

**PASS needs all of:**
1. 270 funding events on each coin, with no gap, and every hour bar present. If not: INCONCLUSIVE, and the gap is reported.
2. Net return on capital > 0.
3. Net return on capital ≥ +0.188% in the 90 days (half of the since-2025 median, the same half-of-backtest idea as FWD-R2). Base rate of this hurdle: 74% since 2025, 40% in 2026.
4. Max drawdown of hourly equity < 2.0% of capital (twice the study's ~1%).
5. Lowest margin ratio on any coin stays ≥ 0.25.

**FAIL:** condition 1 met and any of 2–5 not met. A margin ratio below 0.25 at any time ends the test early as FAIL, because the position would need a top-up the rules do not allow.

- A PASS only allows a new pre-registered step: the ECO + carry mix (T1) or a demo. It is not a claim of profit and authorises no real money.
- The hurdle is weak by design: +0.188% in 90 days is about 0.76% a year. The report must say this next to any PASS.

## Reconciliation (information only)

At FORWARD_END the same window is recomputed with Binance funding if it can be read (VM logs or the public archive), and the two nets are reported side by side. A sign difference is flagged in the report. It does not change the verdict.

## Runs and records

- `src/live_paper/forward_carry.py` recomputes everything from public bars each run. A laptop outage loses no data, because funding history and klines stay available.
- `carry_forward.jsonl` is hash-chained, with the same `prev` rule as LPT-1. `carry_series.csv` holds the hourly series.
- It runs on the laptop only. The VM and the crontab are not touched.
- Any code change after this lock is written in `T2_CODE_CHANGES_AFTER_LOCK.md`.

## Verification

- Hand-number tests: `src/audits/test_forward_carry.py`.
- Independent verifier: `src/audits/verify_forward_carry.py`. Plain Python standard library, its own API calls, recomputes every hour and every funding event, checks the chain, the fees, the frozen entry prices, the protocol SHA, the identity with the Spot-DCA study, and runs mutation checks.
