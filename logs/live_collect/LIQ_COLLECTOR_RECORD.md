# Live liquidation collector: record (2026-10-26)

## Why
- Binance publishes no liquidation history (the `liquidationSnapshot` listing for BTCUSDT on data.binance.vision is empty).
- If liquidations are useful, this data can only come from collecting it ourselves, from now on.
- It is research data only. No keys, no orders.

## What

**Stream:** `wss://fstream.binance.com/market/ws/!forceOrder@arr`. It carries the liquidation orders of all USD-M symbols.
- **Checked 2026-10-26:** the older path `/ws/...` completes the websocket upgrade but sends **no data**. This was tested with btcusdt@aggTrade and with !forceOrder@arr; on the same host, `/market/ws/...` streams data.
- **A known limit of this stream** (Binance documentation): it pushes at most the latest liquidation per symbol per 1,000 ms. It is a snapshot stream, so counts are a lower bound, not every liquidation.

**Code:** `src/collect/liq_collector.py`.
- It is stdlib only (its own RFC 6455 client), so no package is installed.
- It replies to pings, reconnects with backoff, and records every CONNECT / DISCONNECT in `sessions.log`, so gaps are explicit.

**Storage:** `data/live_collect/liq/` on the VM.
- One line per message: the receive time + the raw message.
- **On a day change:** the finished day is gzipped, and its line count and SHA256 go into `MANIFEST.csv`.

**Test on the VM (2026-10-26 15:53–15:55 UTC, 120 s):** 76 messages from 31 symbols, 7 of them BTCUSDT; a clean STOP. Rough size: 16 MB/day raw, a few MB/day gzipped.

**Process:** cron every 5 min starts the collector. A second copy exits at once, because of `flock` on `.lock`.

**Verifier:** `src/audits/verify_liq_collector.py`, run daily. It checks:
- the MANIFEST SHAs and line counts;
- that every stored line is valid JSON with e = forceOrder;
- the heartbeat age;
- the disconnect gaps per day.

## Use
- Nothing in ECO or any paper system reads this data.
- Any later study on it needs its own pre-registered protocol and enough months of data.
