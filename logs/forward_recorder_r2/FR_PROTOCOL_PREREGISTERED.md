# R2 forward recorder (क्रम 2): pre-registered (2026-10-19)

This protocol is locked with SHA256 (`FR_PROTOCOL_SHA256.txt`) before the code is written. Every change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.

It is a **data recorder only**:
- no orders and no keys (only public endpoints);
- no AI and no trading decisions;
- it does not read or write anything belonging to the 1D cloud system;
- `archive/` is not used.

## Why (verified on 2026-10-19 from two sources)
1. **The clean holdout of the R2 work is forward data from 2026-10-17 onward** (master D15 and N11). It must be recorded with proof of *when* it was known.
2. **Some Binance futures statistics cannot be downloaded later.** The Binance docs for `GET /futures/data/openInterestHist` say "Only the data of the latest 1 month is available"; the long/short-ratio and basis pages give the same 30-day limit. A live test on 2026-10-19 confirmed it:
   - `openInterestHist` and `takerlongshortRatio` 29 days back → HTTP 200;
   - the same 40 days back → HTTP 400.

   Data not recorded within 30 days is lost for good.
3. **Klines and funding can be re-downloaded** (a 2020-02-01 5m kline was returned live). They are still stored per run, for two reasons:
   - as point-in-time evidence (the file write time = `available_at`);
   - to detect any later revision by the exchange.
4. **Live snapshots** cannot be re-downloaded at all. These are:
   - the premium index (mark, index, last funding rate, next funding time);
   - open interest now;
   - perp depth (100 levels);
   - spot best bid/ask;
   - the per-symbol funding interval (`/fapi/v1/fundingInfo` showed symbols at 4h intervals, which is M14 in the master audit).

## Universe (frozen here)
23 symbols, each a USDT perpetual and spot pair:
- the 10 research coins: BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LTC, LINK;
- the top-20 USDT perpetuals by 24h quote volume, from the live `/fapi/v1/ticker/24hr` at 2026-10-19 ≈ 11:30 UTC, restricted to perps that also trade on spot: BTC, ETH, ZEC, SOL, NEAR, XRP, HYPE, DOGE, PUMP, BNB, WLD, ENA, SUI, UNI, GTC, FIL, INJ, SAND, ADA, TIA.

**Union:** ADA, BNB, BTC, DOGE, DOT, ENA, ETH, FIL, GTC, HYPE, INJ, LINK, LTC, NEAR, PUMP, SAND, SOL, SUI, TIA, UNI, WLD, XRP, ZEC.

This list is the basis of the universe test (M13). It is not changed silently; any change needs a new protocol version.

## What one run records (every series, for every symbol)
| Group | Endpoint | Series | Window per run |
|---|---|---|---|
| K (re-downloadable) | `GET /api/v3/klines` (spot) | 5m, 15m, 1h, 4h, 1d | closed bars after the last stored open time |
| K | `GET /fapi/v1/klines` (perp) | 1h, 4h | same |
| K | `GET /fapi/v1/markPriceKlines` | 1h, 4h | same |
| K | `GET /fapi/v1/fundingRate` | events | after the last stored funding time |
| S (30-day limit) | `GET /futures/data/openInterestHist`, `topLongShortAccountRatio`, `topLongShortPositionRatio`, `globalLongShortAccountRatio`, `takerlongshortRatio` | period 5m | after the last stored timestamp |
| S | `GET /futures/data/basis` (pair, contractType=PERPETUAL) | period 5m | same |
| L (live only) | `GET /fapi/v1/premiumIndex`, `/fapi/v1/openInterest`, `/fapi/v1/depth?limit=100`, `/api/v3/ticker/bookTicker` | snapshot | now |
| L, all symbols at once | `GET /fapi/v1/fundingInfo`; `/fapi/v1/exchangeInfo` (the 23 entries only) | snapshot | now |

**Rules for every series:**
- **Closed bars only:** a kline is stored only if its close time < the server time at the start of the run.
- **First run (bootstrap):**
  - K series start at 2026-10-17 00:00 UTC, the start of the clean forward holdout;
  - S series take everything still available, back to the server time minus 29 days (the 30-day edge minus one day of safety).
- **Paging:** S endpoints return at most 500 rows (≈ 41.7 h of 5m data) per call, so the recorder pages forward with startTime until it reaches the server time. Requests are throttled to stay below Binance's documented limit (1,000 requests per 5 min on the `/futures/data` endpoints).
- **Server time:** taken from `/api/v3/time` and `/fapi/v1/time` at the start of the run. The skew against the machine clock is written to the ledger.

## Storage
- **Raw responses** (byte-exact JSON) go to `<root>/raw/<run_id>/<group>_<endpoint>_<symbol>_<series>.json.gz`, together with a `manifest.json` that holds each file's SHA256, row count, first and last timestamp, request parameters and write time (UTC).
- **State** of the last stored timestamp per series is kept in `<root>/state.json`. The verifier recomputes it from the manifests.
- **Ledger** `<root>/ledger.csv`, append-only and hash-chained. Each line holds:
  - run_id, start_utc, end_utc;
  - server time and skew;
  - the SHA256 of the manifest;
  - the number of files and rows;
  - the gaps found;
  - the HTTP errors;
  - the protocol and code SHA256;
  - notes, prev_sha256 and line_sha256.
- **Local test:** root = `logs/forward_recorder_r2_localtest/`.
- **Cloud (later, only after the user's approval):** root = `data/forward_r2/` on the VM.
- The local test chain is never mixed with the cloud chain.

## Failure handling
- **One failed request does not stop the run.** It is retried up to 3 times (2 s, 5 s, 10 s back-off), then logged in the ledger's HTTP errors.
- **The next run resumes from the state,** so nothing inside the 30-day window is lost.
- **A run that finds another run's lock file exits without writing** (no two writers).

## Independent verifier `src/audits/verify_forward_recorder_r2.py` (its own code)
- **V1:** the ledger hash chain and line hashes; the protocol SHA equals the lock.
- **V2:** every file in every manifest exists, its SHA256 matches, and the manifest SHA equals its ledger line.
- **V3 (replay):** for K series, a random sample of stored klines and funding rows (seed = run date) is re-fetched from the public API. It must be **byte-equal after JSON parse, 100%**.
- **V4 (continuity):** no missing bar in any K kline series across all runs (open times step exactly by the interval).
  - Missing 5m S timestamps are counted and reported; Binance omits periods with no trades.
- **V5 (no look-ahead):** every stored kline has close time < the run's server start time, and every S or L timestamp ≤ the file write time.
- **V6 (no duplicates):** no open time or timestamp appears twice in a series across runs.
- **V7 (state):** `state.json` equals the state recomputed from the manifests.

## Local tests (before any cloud step)
- **T1:** a real run, then the verifier: all PASS.
- **T2:** a second run right after it, which must add only new rows (V6 PASS) and a 2nd chained ledger line.
- **T3 tamper**, on a copy:
  - flip one byte in one raw file → V2 must FAIL;
  - delete one ledger line → V1 must FAIL;
  - edit state.json → V7 must FAIL.
- **T4 lock:** a run started while a lock file exists exits without writing.

## Cloud step (not part of this protocol's execution; needs the user's "yes")
- A separate cron line on the VM, every 4 hours, 7 minutes after each 4h close: 05:37, 09:37, 13:37, 17:37, 21:37 and 01:37 IST.
- Its own folder.
- Nothing of the 1D system is changed except the crontab file, which gets the added lines.
