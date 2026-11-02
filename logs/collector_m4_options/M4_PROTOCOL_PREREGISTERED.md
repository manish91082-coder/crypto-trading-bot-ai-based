# M4: daily public data collector for options, implied volatility and quarterly basis (pre-registered)

- Code: `src/execution/m4_options_collector.py`
- Verifier: `src/audits/verify_m4_collector.py`

**Public endpoints only:** no keys, no orders, no account. Purpose: from 3–6 months of REAL data, a later pre-registered options-overlay / tail-hedge test becomes possible. Today no free, reliable history exists.

## What is saved once a day (task 05:40 IST = 00:10 UTC, near the daily rebalance)
Every endpoint was checked live on 2026-10-16 (HTTP 200).

| # | Source | Endpoint | What |
|---|---|---|---|
| 1 | Deribit | `public/get_volatility_index_data` | BTC and ETH DVOL, last 2 days, hourly |
| 2 | Deribit | `public/get_book_summary_by_currency` (kind=option) | BTC and ETH: every option's bid/ask, mark price, mark IV, open interest, volume, underlying price |
| 3 | Deribit | `public/get_index_price` | btc_usd and eth_usd index |
| 4 | Binance options | `eapi/v1/mark` | Mark price, bid/ask IV, mark IV, greeks of every listed option |
| 5 | Binance options | `eapi/v1/ticker` | Last price, volume |
| 6 | Binance USDⓈ-M | `fapi/v1/premiumIndex` | The quarterly delivery contracts of BTC and ETH (taken from `fapi/v1/exchangeInfo`, CURRENT/NEXT_QUARTER, TRADING) and the BTCUSDT / ETHUSDT perps: mark, index, last funding |

## Storage and integrity
- Each response is stored raw as gzip JSON: `data/collector_m4/YYYY-MM-DD/<name>.json.gz`.
- Hash-chained ledger `logs/collector_m4_options/ledger.csv`: one line per day with each file's SHA256, size, the HTTP status, and a short summary (BTC/ETH DVOL close, the number of option instruments per venue, the quarterly annualised basis).
- A failed endpoint is logged and retried twice. A missing endpoint never blocks the others.

## Verifier
- Hash chain intact; every file's SHA256 equals the ledger.
- For the latest day: the summary numbers are re-derived from the raw files.
- 3 random instruments are re-fetched live, but only when the run is the same UTC day: their mark IV must be within 5 vol points (prices move).

## Use later
After ≥ 90 days of collection: a separate pre-registered protocol for an options test (Round 3 of `FINAL_ROADMAP_METHODS_16_OCT_2026.md`).
