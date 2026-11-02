# FWD-WATCH: forward paper tracking of the two closest candidates on unseen data from 2026-10-01. Locked 2026-10-26

## 0. Why and what

**The situation.** Every study so far (methods bench Batch 1, 9-month oracle, NP1–NP4) found no proven edge. The 2025-01 … 2026-09 holdout has been used. The only clean evidence left is data that **no study has looked at: from 2026-10-01 onward.**

**Two "closest" candidates are tracked forward, paper only:**
- **FW1** = methods bench `A2.01b_ConnorsRSI_follow_4h`, exit X3.
  - Batch 1 means per trade: D +0.44%, V +1.00%, H +0.75%.
  - n_H = 81, H CI lower bound −0.44%; not an edge.
- **FW2** = NP3 `4h|NODEPTH|RIDGE|0.9|XM`.
  - Net per trade: D +0.019% (t 0.33), V +0.025%; not an edge.

**Prior expectation, stated now:** low. Most likely both fail.

**Limits:**
- No orders; nothing is sent to any exchange.
- This record can never authorise real money. A promotion would need a new protocol.
- It is separate from ECO / paper_n1 / paper_spot_s1, and it changes nothing there.

**Code:**
- `src/forward/fwd_watch.py` (store update + evaluation);
- `src/audits/verify_fwd_watch.py` (independent).

**Output:** `data/fwd_watch/` on the VM, plus the ledgers below.

## 1. Data (public, official only)

**Seed store,** uploaded from the laptop, with SHAs in `data/fwd_watch/SEED_MANIFEST.csv`:
- spot 5m = `data/universe_hf/5m/BTCUSDT_5m_full.csv.gz`, to 2026-09-30.
  - Checked on 2026-10-26: identical to the official monthly files for 2024-03 and 2026-09 (OHLCV + taker buy, max |diff| 0).
- futures 5m and metrics = `data/external/binance_public/clean/fut5m.parquet` and `metrics5m.parquet`, to 2026-09-30, checksum-verified.
- funding = `clean/funding.parquet`, to 2026-09-30.

**Daily extension** from data.binance.vision, each zip verified against its `.CHECKSUM` (sha256), with a manifest per file:
- `data/spot/daily/klines/BTCUSDT/5m/`;
- `data/futures/um/daily/klines/BTCUSDT/5m/`;
- `data/futures/um/daily/metrics/BTCUSDT/`.

**Funding after 2026-09-30:**
- From the public endpoint `GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT`.
- When the official monthly file for a month appears, it replaces the API rows of that month. The verifier records any difference.

**Missing files:** a day whose file is not yet published is simply not appended. The job retries later.

## 2. FW1, exact rule (the bench code's definitions; bench protocol 0ee7aff8, Amendment 626f670a)

**Bars**
- The spot 5m bars are put on a complete 5m grid from 2020-01-01; missing bars become NaN.
- 4h bars use `resample("4h", label="right", closed="left")`.

**Signal**
- **The value:** crsi = (RSI(close, 3) + RSI(streak, 2) + percent-rank of the 1-bar ROC over 100 bars) / 3. RSI is Wilder's.
- **The fade signal:** +1 if crsi < 10, −1 if crsi > 90, else 0.
- **FW1 follows:** its signal is −fade.
- **The time it applies:** the 4h value counts from the first 5m bar whose close is ≥ the 4h bar's completion time (`to5m`).

**Trades** (bench `sim_reversal`):
- **Entry:** at the open of the bar after a non-zero signal bar t.
- **Exit:** at the open after the first later bar with the opposite signal, or at the close of t + 2016 bars (7 days).
- **One position at a time:** a new trade may start at the previous exit bar.
- **The chain:** it starts fresh at the forward start, 2026-10-01 00:00 UTC, as the bench starts each period fresh.

**Cost**
- 0.092% per round trip (`fees.json` futures taker per side × 2);
- plus the funding paid / received over [t, exit) at the funding events with time < bar close (bench `cum_funding`).

**When a trade counts:** only when it is **closed**, that is, its exit bar and exit price exist in the data. An open trade is shown, but not counted.

**Identity check:**
- The same code, started at 2025-01-01, must reproduce the 81 stored bench H trades exactly: t, dir, gross, net, exit (`logs/research_methods_bench/batch1_H_trades_A2.01b_ConnorsRSI_follow_4h_X3.csv`).
- If it does not, FW1 does not start.

## 3. FW2, exact rule (NP1 SHA 9addc94b, NP2 b6d8d754, NP3 8e4488b4)

**Decision times:** 00, 04, 08, 12, 16, 20 UTC.

**Features** (NP1 definitions):

| Feature | Definition |
|---|---|
| OI_CHG_24H | ln(OI_t / OI_{t−24h}); OI = sum_open_interest_value of the last metrics row with create_time + 5 min ≤ t |
| SPOT_TAKER_1H | Σ taker_buy_base / Σ volume over the 12 spot 5m bars ending at t, − 0.5 |
| CTRL_RET_24H | futures close(t) / close(t − 24 h) − 1 |

**Transform:** p = the percentile of each feature among its own 4h-sampled values in [t − 90 d, t), with ≥ 30 past values; u = p − 0.5.

**Score, with β frozen from the NP2 / NP3 D-fit** (2020-09-01 … 2023-12-31, n = 7,250, λ = 0.1 n):
- pred = u · β, where
  - β = [−8.449163524227228e-05, −0.00039878595881818915, −0.00011428329656457703], in the order OI_CHG_24H, SPOT_TAKER_1H, CTRL_RET_24H;
  - thr = 0.00021482419836031948, the 0.9-quantile of |pred| over D.
- Trade if |pred| ≥ thr; the side is sign(pred).

**Execution: XM**
- **Entry:** a maker limit at P = futures close(t). It fills only if a bar with open time in [t, t + 15 min) trades **through** P. No fill means no trade.
- **Exit:** a maker limit at Q = close(t + 4 h), filled on a trade-through within 15 min. Otherwise a taker exit at the close of the bar ending t + 4 h + 15 min.
- **Costs:** maker 0.018% per side; taker 0.046% per side.

**Identity check:**
- The same code must reproduce the 938 stored NP3 DV trades of this config exactly: t, side, entry, exit, net (`logs/research_nonprice/np3_dv_trades.parquet`).
- If it does not, FW2 does not start.

## 4. Forward accounting and decision (fixed now)

**Forward window:** trades whose decision / signal time is ≥ 2026-10-01 00:00 UTC.

**Daily outputs**
- `fw_trades.csv`: every closed forward trade;
- `fw_daily.csv`: every calendar day from 2026-10-01, with zeros;
- `fw_monthly.csv`;
- `fw_status.json`: last data time, open trades, counts.

**Interim reports:** at each month end. Descriptive only; no decision.

**Verdict** (one time, when the count is reached):

| Candidate | Verdict at |
|---|---|
| FW1 | ≥ 80 closed forward trades (expected after about 20 months, at the H rate of about 3.9 per month) |
| FW2 | ≥ 200 closed forward trades (expected after about 11 months) |

A candidate **PASSES** only if all hold:
1. mean net > 0;
2. the weekly-cluster 95% lower bound of the mean net per trade > 0;
3. ≥ 55% of the months positive.

Otherwise it **FAILS**, and tracking stops.

**Early stop:** none on performance. The data checks below may pause tracking.

## 5. Data integrity (every run)
- Every appended file passes its CHECKSUM.
- The 5m grid has no duplicate times.
- **Per-day bar counts are recorded:**
  - a futures or spot day with < 288 bars is flagged;
  - such a day is still used, with NaN bars, exactly as in the research code.
- Funding from the API vs the official monthly file: the maximum |diff| is recorded per month.

## 6. Schedule (VM, IST)
- **`FwdWatch`:** 11:40 and a retry at 15:40. Binance publishes the daily files about one day later.
- **`FwdWatch_Verify`:** right after each run.
