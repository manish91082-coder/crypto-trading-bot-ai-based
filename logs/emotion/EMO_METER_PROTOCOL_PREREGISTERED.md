# EMO meter (R-A): hourly crowd-emotion meter, information only (pre-registered 2026-10-22)

**Source:** `RESEARCH_CROWD_EMOTION_CANDLES_22_OCT_2026.md` §6 R-A.

**Scope:**
- Public Binance endpoints only: no keys, NO orders.
- The meter makes **no trading claim** and feeds nothing into ECO decisions.
- Any trading use needs EMO-1 (its own protocol and gates) first.

## 1. Universe and cadence

**Universe.** Every perp in the last ECO plan record (`data/eco/ledger.jsonl`: `held_net` or `targets_net` keys), plus BTCUSDT and ETHUSDT. At most 40, sorted by name.

**Cadence.** Run hourly (cron), after the ECO cycle.

**Requests per symbol:**
- `/futures/data/openInterestHist`, `topLongShortPositionRatio`, `globalLongShortAccountRatio`, `takerlongshortRatio`, each with `period=1h, limit=49`;
- `/fapi/v1/klines` with `interval=1h, limit=49`.

**Requests once per run:** `/fapi/v1/premiumIndex` (funding).

## 2. Features (per symbol; from closed 1h data only; fixed before any data was looked at)

Only fully closed hours are used: rows with timestamp < the current hour.

| Feature | Definition |
|---|---|
| `oi_chg_24h` | sumOpenInterestValue last / value 24 h earlier − 1 |
| `top_pos_ls` | log(top-trader position longShortRatio), last |
| `retail_acct_ls` | log(global account longShortRatio), last |
| `smart_minus_retail` | `top_pos_ls − retail_acct_ls` |
| `taker_24h` | mean of log(buySellRatio) over the last 24 rows |
| `funding` | `lastFundingRate` |
| `wick_24h` | mean over 24 closed 1h bars of (high − low − \|close − open\|) / (high − low); bars with high = low are skipped |
| `vol_surprise` | quote volume of the last 24 bars / that of the 24 bars before − 1 |
| `ret_24h` | close last / close 24 bars earlier − 1 |

**Crowding score** (cross-sectional, symbols with all features): the mean of the percentile ranks of `oi_chg_24h`, `retail_acct_ls`, `taker_24h` and `funding`. A high score means a crowded long. Equal weights, no fitting.

**Market temperature:** the medians of `retail_acct_ls`, `taker_24h`, `funding` and `oi_chg_24h` across the universe.

## 3. Ledger and checks

**Ledger.** `data/emotion/ledger.jsonl`, hash-chained. Each record holds:
- the raw last values used;
- the features and scores;
- the errors;
- the code SHA.

A symbol with a failed request is listed in `errors` and left out of the ranks.

**Verifier `src/audits/verify_emotion_live.py`:**
- M1: the chain;
- M2: hourly cadence (gaps > 90 min listed; FAIL if any in the last 24 h);
- M3: the crowding scores recomputed from the recorded features equal the recorded scores (1e-12);
- M4: no record with > 20% of symbols in error in the last 24 h;
- M5: the protocol SHA is constant and matches this file.

**Offline test `src/audits/test_emotion_meter.py`.** A fake HTTP source with known numbers checks:
- every feature against a hand calculation;
- the closed-hour cut;
- the rank math;
- that one symbol erroring stays out of the ranks;
- that verifier M3 FAILs on a tampered score.
