# Event-Driven, Real-Time Multi-Timeframe Architecture for a Binance (Spot + USDT-M) Trading System

Research date: 2026-10-17. Binance facts were checked against developers.binance.com pages and the official binance-spot-api-docs markdown on raw.githubusercontent.com (read-only). Anything not verified this session is listed under Gaps.

## Q1. Binance data feeds: kline WS, combined streams, limits, 24h disconnects, ping/pong, user data streams, ALGO_UPDATE, REST fallback, gap backfill, clock sync

### Takeaway
Bar-close triggers should key on the kline `x` ("Is this kline closed?") flag, deduplicated by the kline open time `t`. Every connection must expect a forced disconnect at 24h and on announced server maintenance (`serverShutdown`). On each reconnect, and on a timer, missed bars should be backfilled from REST `/klines`, which are keyed by open time. USDT-M changed in 2025-2026 in ways that matter here. Conditional orders now go through the Algo Service (`/fapi/v1/algoOrder`, `ALGO_UPDATE`). WebSocket URLs are routed by `/public`, `/market` and `/private`. Spot REST listenKey user streams were retired in 2026.

### Cited Findings
**Spot market streams**
- Endpoints: `wss://stream.binance.com:9443` or `:443`. Raw stream URL `/ws/<stream>`, combined stream URL `/stream?streams=a/b/c`, or SUBSCRIBE with `method`/`params`/`id` — [Binance Spot WS Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams)
- "A single connection to stream.binance.com is only valid for 24 hours; expect to be disconnected at the 24 hour mark." — [binance-spot-api-docs web-socket-streams.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/web-socket-streams.md)
- Spot keepalive: the server sends a ping frame every 20 seconds and disconnects if no pong arrives within a minute. "Unsolicited pong frames are allowed, but will not prevent disconnection." — [web-socket-streams.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/web-socket-streams.md). The changelog of 2025-01-28 records the change from 3 minutes to 20 seconds — [Spot CHANGELOG](https://developers.binance.com/docs/binance-spot-api-docs/CHANGELOG)
- Spot limits: 5 incoming messages per second per connection; at most 1024 streams per connection; "300 connections per attempt every 5 minutes per IP" — [web-socket-streams.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/web-socket-streams.md)
- Spot kline stream `<symbol>@kline_<interval>` pushes updates for the current kline. Update speed is 1000 ms for `1s` and 2000 ms for other intervals. There is also a UTC+8 variant, `@kline_<interval>@+08:00`. Payload fields: `t` start, `T` close, `o/h/l/c`, `v`, `n`, `x` = "Is this kline closed?", `q`, `V`, `Q` — [Spot WS Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams)
- Add `timeUnit=MICROSECOND` to the URL to get microsecond timestamps — [web-socket-streams.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/web-socket-streams.md)
- Since 2026-05-06, WebSocket API and Streams send a `serverShutdown` event 10 minutes before a disconnection. Infrastructure upgrades can drop connections: one starting 2026-07-09 07:00 UTC could disconnect connections "for up to an hour" — [Spot CHANGELOG](https://developers.binance.com/docs/binance-spot-api-docs/CHANGELOG)

**USDT-M (USDⓈ-M) futures streams**
- Base `wss://fstream.binance.com` with routed paths: `/public` for high-frequency public market data, `/market` for regular market data, and `/private` for user data. Connections without a routed path get only Public data. For example, `@depth` works on them but `@markPrice` does not — [USDⓈ-M WS Connect](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Connect)
- Changelog: the "Important WebSocket Change Notice" was added 2026-03-05. Decommissioning of legacy URLs was listed for 2026-04-23 (entry dated 2026-04-02) — [Derivatives change log](https://developers.binance.com/docs/derivatives/change-log)
- USDT-M keepalive: 24h validity; the server pings every 3 minutes and disconnects if no pong arrives within 10 minutes; unsolicited pongs are allowed. Limits: 10 incoming messages per second and at most **1024** streams per connection. "IPs that are repeatedly disconnected may be banned" — [USDⓈ-M WS Connect](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Connect)
- Conflict: older pages and code say 200 streams per connection. The COIN-M page says 200, and NautilusTrader's Binance futures client hard-codes `MAX_STREAMS_PER_CONNECTION = 200` — [COIN-M Connect](https://developers.binance.com/docs/derivatives/coin-margined-futures/websocket-market-streams/Connect), [Nautilus client.rs](https://nautilustrader.io/docs/core-latest/src/nautilus_binance/futures/websocket/client.rs.html)
- After the CM migration, some streams carry merged UM and CM data. New fields: `ps` (pair) and `st` (1 = UM, 2 = CM) — [USDⓈ-M WS market streams](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams)

**User data streams (fills and positions)**
- USDT-M: `POST`/`PUT`/`DELETE /fapi/v1/listenKey`. "User data streams will close after 60 minutes." Binance recommends a keepalive ping "about every 60 minutes". POST on an account that already has an active key returns that key and extends it 60 minutes — [USDⓈ-M User Data Streams](https://developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams). The user data WS sits under the `/private` route — [USDⓈ-M WS Connect](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Connect)
- Spot: "Receiving user data streams on wss://stream.binance.com:9443 using a listenKey is now deprecated" (2025-04-07). `userDataStream.subscribe.signature` was added 2025-08-12. REST `userDataStream` POST/PUT/DELETE and WS-API `userDataStream.start/.ping/.stop` stop working "starting from 2026-02-20, 07:00 UTC" (entry dated 2026-01-21) — [Spot CHANGELOG](https://developers.binance.com/docs/binance-spot-api-docs/CHANGELOG)
- Spot user-stream events: `outboundAccountPosition` (balance changed), `executionReport` (order updates), `balanceUpdate`, `listStatus` (order lists), and `eventStreamTerminated` (token expiry, logout or unsubscribe). The doc gives no ordering or duplicate guarantees — [user-data-stream.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/user-data-stream.md)

**ALGO_UPDATE and the Algo Service (USDT-M)**
- Effective 2025-12-09, the conditional types STOP_MARKET, TAKE_PROFIT_MARKET, STOP, TAKE_PROFIT and TRAILING_STOP_MARKET moved to the Algo Service. Endpoints: `/fapi/v1/algoOrder`, `openAlgoOrders`, `allAlgoOrders`. Placing these types via `POST /fapi/v1/order` or `batchOrders` returns `-4120 STOP_ORDER_SWITCH_ALGO` — [Derivatives change log](https://developers.binance.com/docs/derivatives/change-log)
- `CONDITIONAL_ORDER_TRIGGER_REJECT` was deprecated effective 2025-12-15; rejection reasons now arrive in `ALGO_UPDATE`. On 2025-12-29 the `MAX_NUM_ALGO_ORDERS` filter was removed and the conditional-order limit became 200 across all symbols. From 2026-08-21 the `ia` (activated) field is live, so a trailing stop can push NEW twice: first `ia:false`, then `ia:true` — [Derivatives change log](https://developers.binance.com/docs/derivatives/change-log)
- ALGO_UPDATE statuses include NEW, TRIGGERING, TRIGGERED, FINISHED, CANCELED, REJECTED and EXPIRED. The payload carries `"fs":"UM"` — [Event Algo Order Update (PM docs)](https://developers.binance.com/docs/derivatives/portfolio-margin/user-data-streams/Event-Algo-Order-Update). NautilusTrader issue #3287 shows the `-4120` failure from legacy code — [GitHub issue](https://github.com/nautechsystems/nautilus_trader/issues/3287)
- From 2026-08-07, ACCOUNT_UPDATE adds an `S` (symbol) field, sent only when the reason is FUNDING_FEE — [Derivatives change log](https://developers.binance.com/docs/derivatives/change-log)

**REST fallback, backfill and clock**
- `GET /api/v3/klines`: weight 2, limit default 500 and max 1000. "Klines are uniquely identified by their open time." Intervals are case-sensitive and include `1w` and `1M` — [rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md)
- `GET /api/v3/time` returns server time with weight 1. SIGNED requests need `timestamp` in ms or µs. `recvWindow` defaults to 5000 with a max of 60000, and "It is recommended to use a small recvWindow of 5000 or less!" Requests are rejected if the timestamp is about 1 s ahead of server time or older than recvWindow — [rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md)
- HTTP 5XX means execution status is "UNKNOWN and could have been a success". Check order status before retrying. A 429 comes with `Retry-After`; repeated violations get an HTTP 418 IP ban, escalating from 2 minutes to 3 days — [rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md)
- `newClientOrderId` must be unique among open orders. Reuse "can be accepted only when the previous one is filled, otherwise the order will be rejected" — [rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md)

### Inferences
- Bar-close trigger rule: emit a `BarClosed(symbol, tf, open_time)` event only when `k.x == true`, and make it idempotent on `(symbol, tf, t)`. The kline push interval is 2 s, so the closed bar normally arrives within about 2 s of `T`. A REST poll at `T + a few seconds` is a robust fallback for when the WS message is lost.
- Gap detection: keep `last_closed_open_time[symbol, tf]`. On every closed bar, and on every reconnect, check that the new `t` equals the last `t` plus the interval. If not, backfill from `/klines?startTime=` (max 1000 bars per call). 1M bars have variable length, so use calendar math rather than a fixed ms step.
- Deriving higher timeframes: the system can subscribe only to 5m (or 1m) and aggregate 15m/1h/4h/1D/1W/1M locally, then cross-check against the exchange's closed klines. This reduces the stream count, but there is drift risk at week and month boundaries. Binance 1w bars open Monday 00:00 UTC (training knowledge, not verified this session).
- Stream budget: 10 coins × 7 timeframes = 70 kline streams, far under the 1024 limit (or 200 on older docs). One connection per market (spot, USDT-M `/market`), plus a second warm standby connection for overlap at the 24h roll, is enough.
- Fills and positions: on USDT-M use the listenKey on `/private`, renewed every 30-50 minutes. On spot use WS-API `userDataStream.subscribe.signature`. In both cases periodically reconcile against REST (open orders, `openAlgoOrders`, position and account endpoints), because no ordering guarantee is documented.
- Clock: sync offset against `/api/v3/time` (or `/fapi/v1/time`) at startup and every few minutes. Keep recvWindow ≤ 5000. Bar-close logic should use exchange `T`/`t`, not local time.

### Gaps
- I did not read the full text of the USDⓈ-M kline stream page, so its kline push speed and the existence of a `@kline` `x` field on the `/market` route were not quoted directly. Binance's futures kline payload shape is generally the same as spot (training knowledge, not verified this session).
- The USDT-M klines REST limit (default 500, max 1500 in training knowledge) was not verified; the fetched page was a landing page.
- The futures WS per-IP connection-attempt limit is not stated on the Connect page.
- The exact USDT-M user-data event list (ORDER_TRADE_UPDATE, ACCOUNT_UPDATE, listenKeyExpired, ALGO_UPDATE on UM) was not quoted from the UM event pages this session. The ALGO_UPDATE fields above come from the Portfolio Margin page and the change log.
- I could not confirm whether the 2026-04-23 decommission of legacy futures WS URLs actually happened as scheduled.

## Q2. Architecture patterns in established frameworks: backtest = live parity, message bus, persistence, idempotency, reconciliation, crash recovery

### Takeaway
Mature frameworks share one pattern. Strategy code receives typed events (bar, fill, order update) from an in-process message bus, and the same code runs in backtest and live. A separate execution engine owns order state, assigns client order IDs, persists to a cache or DB, and reconciles against the venue at startup and continuously. Live adds failure modes a backtest cannot reproduce.

### Cited Findings
- NautilusTrader: "The same strategy and execution-algorithm code can run across backtest and live environments." The docs also say live adds venue, transport, timing, persistence, external-activity and reconciliation behavior that simulation may not reproduce — [Nautilus Live](https://nautilustrader.io/docs/latest/concepts/live)
- Nautilus startup reconciliation aligns cached orders and positions with venue reports before trader components start. Continuous checks then monitor in-flight orders, open orders and positions. Cache restoration requires a backing DB with loading enabled. "Submission recovery does not extend across restarts." On shutdown, unresolved client order IDs produce an error — [Nautilus Live](https://nautilustrader.io/docs/latest/concepts/live)
- Nautilus message bus: typed in-process publish/subscribe. It has `heartbeat_timeout_secs` (default three heartbeat intervals), `QueueMonitorConfig` (queue depth and dispatch latency triggers) and `LiveNodeConfig.shutdown_on_error` — [Nautilus Live](https://nautilustrader.io/docs/latest/concepts/live)
- Nautilus RiskEngine pre-trade checks cover precision, quantity bounds, reduce-only not increasing the position, `max_notional_per_order`, submit/modify rate limits, and trading state ACTIVE/HALTED/REDUCING. Duplicate fills are detected via `trade_id` — [Nautilus Execution](https://nautilustrader.io/docs/latest/concepts/execution)
- Freqtrade loop: runs every `internals.process_throttle_secs`. Each iteration fetches open trades from persistence, refreshes the pairlist, downloads OHLCV including informative pairs, analyzes each pair "only executed once per Candle", checks order timeouts and price adjustments, then checks exits, position adjustments and entries. Callbacks run every ~5 s live but once per candle in backtest, "which can cause backtesting mismatches" — [Freqtrade bot basics](https://www.freqtrade.io/en/stable/bot-basics/)
- QuantConnect LEAN Algorithm Framework pipeline: Universe Selection → Alpha (emits `Insight`) → Portfolio Construction (emits `PortfolioTarget`, units to hold) → Risk Management (adjusts targets) → Execution (trades to reach targets). "The models should not communicate" — [LEAN framework overview](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview)
- Binance's own idempotency hooks: `newClientOrderId` is unique among open orders, and on 5XX the status is UNKNOWN, so query before retrying — [rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md)

### Inferences
- Recommended loop (scan → analyze → decide → act → record):
  1. **Ingest:** WS and REST adapters publish `BarClosed` and `OrderEvent` on a bus.
  2. **Knowledge base:** an append-only, point-in-time store (e.g., parquet or SQLite/Postgres with `asof` = bar close time and `knowledge_time` = when ingested). Features are computed only from bars with `T` ≤ the decision time.
  3. **Per-timeframe deciders:** each subscribes to its own timeframe and emits Insights or targets, not orders.
  4. **Portfolio/coordinator:** combines targets into one net target per symbol and account.
  5. **Risk gate.**
  6. **Execution engine:** diffs the target against the reconciled position, sends orders with a deterministic `clientOrderId`, for example a hash of (decision_id, symbol, leg).
  7. **Recorder:** writes every event and decision with SHA hashes, for audit and replay.
- For backtest = live parity, drive the backtester with the exact same `BarClosed` event objects, replayed from the recorded store. The decider code path stays identical, and only the adapter and clock change. Freqtrade's documented mismatch (callback frequency) is the kind of drift to design out.
- Crash recovery: on restart, (a) load persisted state, (b) REST-reconcile open orders, algo orders, positions and balances, (c) backfill missing bars, (d) recompute any decision whose bar closed while the system was down. Only act if it is still actionable and within a freshness window; otherwise log it as skipped.

### Gaps
- I did not fetch Hummingbot, Zipline or Backtrader docs, or Nautilus's dedicated reconciliation page. Config names such as `reconciliation_lookback_mins` and `open_check_interval_secs` are training knowledge and were not verified.
- I found no first-party engineering blog from an established trading firm in this pass.
- Freqtrade's `process_only_new_candles` and `merge_informative_pair` lookahead handling were not on the fetched page (training knowledge says they exist).

## Q3. Multi-timeframe coordination: capital allocation, netting across sleeves, conflict resolution, sub-accounts, one-way vs hedge mode

### Takeaway
On Binance USDT-M, position mode is one global setting per account. It applies to every symbol and (after the CM migration) is shared by UM and CM. It cannot be changed while any order or position is open. Without separate sub-accounts, sleeves on the same symbol therefore either net into one exchange position (one-way mode) or get at most one LONG and one SHORT bucket (hedge mode). The standard solution is virtual per-sleeve positions inside the system, with a coordinator that nets them into one exchange order. Nautilus's NETTING-per-strategy and LEAN's Insight → PortfolioTarget model take this approach.

### Cited Findings
- `POST /fapi/v1/positionSide/dual`: `dualSidePosition=true` means Hedge Mode and `false` means One-way. The setting applies to "EVERY symbol", and "UM and CM share the same dualSidePosition setting". A change is rejected with `-4067` (open orders exist) or `-4068` (open position exists) — [Change Position Mode](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Position-Mode)
- `positionSide` defaults to BOTH in one-way mode; LONG or SHORT "must be sent in Hedge Mode". `reduceOnly` "Cannot be sent in Hedge Mode" — [Change Position Mode / New Order notes](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Position-Mode)
- Change log: from 2026-04-14 COIN-M `dualSidePosition` must match UM. Error `-4531` (2026-05-13) rejects UM mode changes blocked by open CM positions or orders — [Derivatives change log](https://developers.binance.com/docs/derivatives/change-log)
- Nautilus OMS types: NETTING gives one position per instrument *and strategy*, with ID `{instrument_id}-{strategy_id}`. HEDGING allows multiple positions. If the strategy and venue OMS types differ, the ExecutionEngine assigns or overrides `position_id` on fills — [Nautilus Execution](https://nautilustrader.io/docs/latest/concepts/execution)
- Nautilus also warns that registering multiple clients for one venue "does not provide end-to-end account isolation for positions and order management across same-venue accounts" — [Nautilus Live](https://nautilustrader.io/docs/latest/concepts/live)
- LEAN: alphas emit Insights, and portfolio construction turns them into per-asset `PortfolioTarget`s. The overview notes that default models can over-concentrate and that a custom model could give each insight its own separately tracked allocation. It does not describe netting across alphas — [LEAN framework overview](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview)

### Inferences
- Three coordination designs, with trade-offs:
  1. **Netting (recommended default, one-way mode).** Each timeframe sleeve has a risk budget (e.g., a vol-targeted fraction of equity) and a virtual signed position. The exchange order is `Σ sleeve_targets − actual_position`. Opposite signals (4H long, 1h short) partly cancel. This saves fees and margin while keeping per-sleeve PnL attribution in the ledger.
  2. **Priority or hierarchy rules.** A higher timeframe sets the regime or direction filter; a lower timeframe only times entries or scales size within it (e.g., 1h short is vetoed while 4H is long, or limited to reducing exposure). This is simpler but discards information.
  3. **Physical separation.** Use Binance sub-accounts (one per sleeve), or hedge mode for exactly two opposing buckets. This gives isolation and clean attribution at the cost of double fees and margin, transfer overhead, and hedge mode's lack of `reduceOnly`.
- Because position mode is global and cannot change with open positions, choose it once, before going live. For multi-sleeve systems, one-way plus internal virtual sleeves is the most flexible.
- Spot has no shorting and no positions, only balances. Sleeves on spot are therefore inherently long/flat, and netting means summing target holdings and clipping at ≥ 0.
- Per-sleeve risk budgets plus a global gross and net exposure cap belong in the risk gate (step 5 of the Q2 loop), applied after netting.

### Gaps
- I did not fetch Binance sub-account docs this session (creation limits, API keys per sub-account, transfer endpoints, whether futures can be enabled per sub-account). The sub-account option above is untested against current docs.
- I found no authoritative or academic source quantifying netting versus separate-sleeve performance for multi-timeframe crypto strategies.

## Q4. Compute, latency, scheduling, monitoring

### Takeaway
Bar-close decisions from 5m to 1M are low-frequency. Binance pushes klines every 2 s, and a decision has minutes of budget, so a small VM is sufficient. The operational risk is liveness, not latency: run a long-running service under a supervisor (systemd), with heartbeats and staleness alarms, rather than cron.

### Cited Findings
- The kline update cadence is 2000 ms for non-1s intervals — [Spot WS Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams)
- Forced disconnects come from the 24h validity, `serverShutdown` notices (10 minutes ahead), and maintenance windows of up to an hour (2026-07-09) — [Spot CHANGELOG](https://developers.binance.com/docs/binance-spot-api-docs/CHANGELOG)
- Nautilus offers `heartbeat_timeout_secs` and a queue monitor with depth and latency triggers — [Nautilus Live](https://nautilustrader.io/docs/latest/concepts/live)
- Freqtrade uses a long-running loop throttled by `process_throttle_secs`, not cron — [Freqtrade bot basics](https://www.freqtrade.io/en/stable/bot-basics/)

### Inferences
- Use a long-running async service (asyncio or Rust) under systemd with `Restart=always`, a watchdog, and logs to journald or files. Cron can serve as a backstop job that verifies the service heartbeat and closed-bar freshness, and runs a REST-polled decision if the WS path is dead.
- Monitoring signals to track:
  - Last closed bar age per (symbol, tf) against the expected interval plus a grace period.
  - WS reconnect count.
  - listenKey renew success.
  - Clock offset against serverTime.
  - Reconciliation diff (internal positions against exchange).
  - Order reject codes (`-4120`, `-1021` timestamp, 429/418).
  - Equity drawdown.
  - Alerts via Telegram or email.
- The 5m decision has a budget of a few seconds to minutes, while 1W and 1M decisions can afford heavy model inference. Stagger heavy work so 1D/1W/1M runs do not block the 5m path; for example, run them in separate worker processes fed by the same bus.

### Gaps
- I found no vendor or benchmark source giving VM sizing numbers for this workload. The sizing advice is engineering inference only.

## Q5. Testing: stream replay, paper/shadow mode, chaos tests

### Takeaway
Record every raw WS message and REST response with receive timestamps, and replay them through the same adapters for deterministic tests. Run paper or shadow mode on Binance testnet or demo endpoints before live. Inject disconnects, duplicate or out-of-order bars, 5XX/UNKNOWN order states and restarts to prove that reconciliation and backfill work.

### Cited Findings
- Binance provides test and demo market-stream endpoints: `wss://stream.testnet.binance.vision` and `wss://demo-stream.binance.com:9443` — [Spot WS Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams). The futures testnet stream is `wss://stream.binancefuture.com` — [USDⓈ-M WS market streams](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams)
- Nautilus explicitly notes that live adds behavior a simulation may not reproduce: transport, timing, reconciliation — [Nautilus Live](https://nautilustrader.io/docs/latest/concepts/live)
- 5XX means status UNKNOWN, a case that tests must cover so retries do not create duplicate orders — [rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md)

### Inferences
- Test matrix:
  - (a) Replay golden recorded days; decisions must be byte-identical to the logged ones.
  - (b) Kill the WS mid-bar and at the bar close; the bar must still be processed exactly once via REST backfill.
  - (c) Duplicate `x=true` messages must not double-trigger.
  - (d) A process crash after order send but before the ack is recorded; on restart, reconcile via `clientOrderId` with no duplicate order.
  - (e) A listenKey expiry and the 24h roll.
  - (f) Clock skew greater than 1 s must be detected and corrected.
  - (g) Legacy conditional order types must be rejected (`-4120`) so only the algoOrder path is used.
- Shadow mode: run the live decision engine against real mainnet data while sending orders only to testnet, or not at all, and compare the shadow ledger with backtest replay of the same days.

### Gaps
- I found no authoritative public source (framework doc or firm blog) that prescribes chaos-testing procedures for crypto bots. The matrix above is inference.
- I did not verify testnet parity with mainnet for ALGO_UPDATE and the `/private` routing.
