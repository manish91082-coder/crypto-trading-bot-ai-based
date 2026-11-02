# Trading Costs and Execution Requirements for a 4H Binance Long/Short System (Spot + USDT-M Perps)

Research date: 2026-10-17. All Binance pages were fetched on this date unless noted. Fee pages are rendered dynamically, so some numbers come from Binance FAQ pages rather than the live fee table (see Gaps).

## 1. Binance fee schedule (spot VIP0, USDT-M VIP0, BNB discounts)

### Takeaway
Regular-user (VIP0) cost is 0.10%/0.10% maker/taker on spot (0.075% with the BNB 25% discount) and 0.02%/0.05% maker/taker on USDT-M futures (10% off when paid in BNB held in the futures wallet). A taker round trip costs about 20 bps on spot and 10 bps on perps before spread, slippage and funding.

### Cited Findings
- Spot regular user (VIP 0): maker 0.100% / taker 0.100%; with "BNB 25% off": 0.0750% / 0.0750%. — [Binance Fee Schedule](https://www.binance.com/en/fee/schedule) (fetched 2026-10-17)
- USDT-M futures, "Regular User": maker 0.02%, taker 0.05%. Worked examples: buying 1 BTC at 10,104 USDT with a taker order costs 5.052 USDT (0.05%); a maker sell of 1 BTC at 11,104 USDT costs 2.2208 USDT (0.02%). — [Binance FAQ: Futures fee structure & calculations](https://www.binance.com/en/support/faq/binance-futures-fee-structure-fee-calculations-360033544231) (page last updated 2026-05-01; it says the information "may be outdated" and that fees are subject to change)
- USDT-M BNB discount: 10% off standard fees when fees are paid in BNB. The BNB must sit in the USDⓈ-M Futures wallet. If that balance is insufficient, USDT is deducted and no discount applies. — [same FAQ](https://www.binance.com/en/support/faq/binance-futures-fee-structure-fee-calculations-360033544231)
- Third-party confirmation of 0.02%/0.05% for regular users (under $15M 30-day volume or under 25 BNB): — [Finder](https://www.finder.com/binance-futures-fees) (secondary, may be stale)
- The FAQ says futures fees vary by VIP level and points to the live USDⓈ-M fee table. The live futures fee page (binance.com/en/fee/futureFee) did not render numbers when fetched. — [Binance futureFee page](https://www.binance.com/en/fee/futureFee)
- The same FAQ mentions MiCA restrictions on unauthorized stablecoins for EEA users and new legal/clearing terms effective 5 January 2026. It also links a 2025-09-11 limited-time fee discount for USDC-margined perpetuals. — [Binance FAQ](https://www.binance.com/en/support/faq/binance-futures-fee-structure-fee-calculations-360033544231)

### Inferences
- Round-trip fees per unit notional (fees only):
  - Perp taker/taker: 2 × 5 bps = **10 bps** (9 bps with BNB).
  - Perp maker/maker: 2 × 2 bps = **4 bps** (3.6 bps with BNB).
  - Perp maker entry + taker exit (common when stops fire): **7 bps**.
  - Spot taker/taker: **20 bps** (15 bps with BNB). Spot maker/maker: also 20 bps (15 with BNB), because VIP0 spot maker = taker.
- On spot at VIP0, maker execution saves no fee. The only saving is the half-spread. On perps, maker saves 3 bps per side.
- Perps are therefore roughly half the fee cost of spot. Shorting on spot needs margin borrowing (extra interest), so for a long/short 4H system, perps are the natural venue for both legs. Spot is mainly useful as a long-only fallback.

### Gaps
- The live USDT-M VIP fee table could not be read (JavaScript-rendered). The 0.02%/0.05% figure comes from an official FAQ updated 2026-05-01. Verify in the account's own fee page or via `GET /fapi/v1/commissionRate` before going live.
- Any regional variation (EEA/MiCA entities, other Binance affiliates) and any 2026 promo tiers were not checked.

## 2. Funding mechanics on USDT-M perpetuals

### Takeaway
Funding is a peer-to-peer payment, by default every 8h at 00:00, 08:00 and 16:00 UTC. It is charged only on positions open at the exact settlement timestamp. Some contracts use 4h intervals, and a contract switches to 1h after a settlement hits the cap or floor. A 4H system closed on UTC 4h boundaries will cross a settlement at about every second bar boundary on 8h contracts, and at every bar boundary on 4h contracts.

### Cited Findings
- Formula: F = [Average Premium Index (P) + clamp(interest rate − P, 0.05%, −0.05%)] / (8/N), where N is the funding interval in hours. Funding amount = position notional (mark price × size) × F. — [Binance FAQ: Introduction to Funding Rates](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- Interest rate is 0.03%/day (0.01% per 8h). ETHBTC uses 0%. If the premium index is between −0.04% and +0.06%, the funding rate equals 0.01%. — [same](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- Premium Index P = [max(0, Impact Bid − Index) − max(0, Index − Impact Ask)] / Index. It is sampled every 5 s and time-weighted over 5,760 points for an 8h interval (720 for 1h). Impact Margin Notional = 200 USDT / initial margin rate at max leverage (for example, 4,000 USDT at a 5% IMR). — [same](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- Cap/floor = ±0.75 × maintenance margin ratio for listed symbols such as BTCUSDT, ETHUSDT and BNBUSDT. Other USDⓈ-M perps are capped at ±2%. In extreme conditions the cap/floor can be adjusted, within limits of −1 and 1. — [same](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- A positive rate means longs pay shorts, and a negative rate means shorts pay longs. Binance takes no fee. You pay or receive funding only if you hold a position at the funding time, and settlement can deviate by up to 15 s. Binance can change the interval during extreme volatility. — [same](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- Since 2025-05-02 08:00 UTC, a settlement that hits the cap or floor switches the contract to hourly funding within about 15 minutes, with no announcement. Since 2026-01-02 12:00 UTC, a 1h contract whose absolute rate stays at or below 0.025% for 16 consecutive cycles reverts to every 4 hours on the 17th cycle. — [same](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- API changelog (2026-07-23): `GET /fapi/v1/fundingRate` added `rateType` (`Regular` / `Special`). `Special` covers extra funding generated by stock dividends on stock-linked perps. No 2025–2026 changelog entry changed the default intervals. — [Binance Derivatives Change Log](https://developers.binance.com/docs/derivatives/change-log)

### Inferences
- With the baseline rate (0.01%/8h), the cost is 1 bp per settlement crossed: about 0.5 bp per 4h bar on average for longs, and a credit of the same size for shorts. That is small next to fees. During euphoric markets, rates of several times the baseline (and up to the cap) make funding material for multi-bar holds, so funding must be modeled per symbol from historical `fundingRate` data, not assumed constant.
- Bar-boundary timing matters. Execution at 00:00/08:00/16:00 UTC coincides with settlement. An order filling a few seconds before or after the timestamp, plus the ±15 s settlement jitter, decides whether one funding payment applies. Backtests should assume the position present at the settlement is charged, and execution logic should be consistent (for example, act 30–60 s after the bar close, after settlement).
- Never hard-code 8h. Read each symbol's interval (`GET /fapi/v1/fundingInfo`; not fetched here, verify) at every run, because contracts can switch to 1h automatically.
- Funding is a signal-correlated cost. Crowded momentum longs tend to pay positive funding, so a long/short momentum book may carry a systematic funding drag on longs and a credit on shorts.

### Gaps
- No official list of which USDT-M symbols currently use 4h versus 8h intervals was retrieved. That list is dynamic and must be pulled from the API.
- Empirical distributions of funding rates (mean or percentiles per coin) were not gathered in this pass.

## 3. Slippage, spreads and depth (top coins vs mid/small caps)

### Takeaway
For BTC/ETH on Binance, quoted and effective spreads are a fraction of a basis point, and $1k–$10k orders barely touch depth, so fees dominate. For mid and small caps, spreads and depth deteriorate sharply and depth can vanish in stress. Per-symbol order-book sampling is needed, because no reliable public 2025–2026 cross-section of altcoin spreads was found.

### Cited Findings
- An academic study built daily effective bid-ask spreads from Binance perpetual trade records for five currencies. The effective spread averages about 0.1 bp, the same order of magnitude as quoted spreads. It runs somewhat larger because taker orders walk several levels and the estimator absorbs some price impact. — [Ackerer, Hugonnier & Jermann, "Fundamentals of Perpetual Futures", arXiv 2212.06888](https://arxiv.org/pdf/2212.06888) (snippet-level; the five coins were not confirmed)
- Kaiko: SOL-USDT shows the widest spread interquartile range and the most outliers, on Binance, suggesting Binance's SOL liquidity lags its other pairs. DOGE has tighter USDT spreads than XRP, SOL and ADA. USDT pairs have the tightest spreads in crypto. — [Kaiko, "A cheatsheet for bid-ask spreads"](https://www.kaiko.com/resources/a-cheatsheet-for-bid-ask-spreads) (via search snippet; the full page timed out; data is from about 2023)
- Kaiko data reported in secondary press: Binance BTC 1% market depth exceeded $600M by October 2025. — [finance.ua citing Kaiko](https://finance.ua/ua/goodtoknow/kaiko-shcho-stoit-za-zrostanniam-binance-do-300-mln-korystuvachiv-tsyfry-spredy-ta-hlybyna) (secondary, not verified at Kaiko)
- Stress example: during the false BTC ETF report in October 2023, Binance BTC 0.1% ask depth collapsed from about 100 BTC to about 1.2 BTC. — [FXStreet citing Kaiko](https://www.fxstreet.com/amp/cryptocurrencies/news/bitcoin-liquidity-on-binance-plummeted-during-the-etf-rumor-induced-market-rollercoaster-kaiko-202310170704)
- Amberdata (2025): about $16.53M of BTC orders rest within 100 bps of mid on Binance BTC/FDUSD. — [Amberdata report landing page](https://go.amberdata.io/the-architecture-of-market-depth-how-liquidity-really-works-in-crypto-markets) (via snippet; the URL now redirects because Kaiko acquired Amberdata)
- Kaiko defines 1% depth as the USD value of bids plus asks within 1% of mid. — [Kaiko docs](https://docs.kaiko.com/getting-started/kaiko-examples/compare-market-depth-between-exchanges)
- Crypto momentum is significant only among the most liquid coins. The illiquid "losers" leg suffers wider spreads. — [Momentum and liquidity in cryptocurrencies, arXiv 1904.00890](https://arxiv.org/pdf/1904.00890)
- One crypto cross-sectional momentum study assumes a 26 bps per-trade cost. Its best model stays positive up to 29 bps. — [Transfer Ranking, arXiv 2208.09968](https://arxiv.org/pdf/2208.09968)

### Inferences
These estimates come from the evidence above. They are not measured and must be verified with live order-book snapshots.
- BTC/ETH perps, $1k–$10k orders: half-spread plus impact is about 0.1–1 bp per side. Taker round trip all-in is about 10–12 bps.
- Large alts (SOL, BNB, XRP, DOGE) perps: plausibly 1–3 bps per side. All-in taker round trip is about 12–16 bps.
- Mid/small caps: spread plus impact can be 5–30+ bps per side, and much worse during news or liquidations. All-in round trip is about 20–70+ bps.
- Spot is generally thinner than perps for alts, and its fees are double. Spot all-in taker round trip for majors is about 21–25 bps.
- A conservative backtest assumption is 12 bps round trip for BTC/ETH perps, 15–20 bps for top-20 alt perps, and 30+ bps for anything outside the top 30 (or exclude those coins). Add funding separately. A stress multiplier of 2–3× should be applied on high-volatility bars, because depth collapses when stops cluster (see the 2023 example).

### Gaps
- No verified 2025–2026 table of Binance spreads or depth per coin (BTC/ETH/SOL vs small caps) was obtainable for free. Kaiko and Amberdata data is paywalled, and the Kaiko page timed out.
- Recommended remedy: sample `GET /fapi/v1/depth` and `bookTicker` per symbol at each 4H close for 2–4 weeks and compute the cost to fill $1k, $5k and $10k. This also creates evidence for the project's evidence requirement.

## 4. Break-even edge and turnover control

### Takeaway
A 4H perp system must earn at least about 10–15 bps gross per round trip on majors (more on alts) just to break even. Turnover control through no-trade buffers, minimum holds and partial adjustment is theoretically optimal under proportional costs, and empirically lower-turnover crypto momentum holds up better after costs.

### Cited Findings
- Under proportional and fixed costs, the optimal policy has a no-trade region around the frictionless target, and the investor stays put until a boundary is breached. Under quadratic (impact) costs, trading continuously in small amounts is optimal. — [Asymptotic methods for transaction costs, arXiv 2407.07100](https://arxiv.org/pdf/2407.07100)
- Under proportional cost ε, the no-trade band width scales as about ε^(1/3), from balancing trading losses against displacement losses. — [Portfolio Selection with Small Transaction Costs, arXiv 1205.4588](https://arxiv.org/pdf/1205.4588)
- Gârleanu–Pedersen is the classic solution for quadratic costs with predictable returns. The optimal policy trades partially toward an "aim" portfolio, a weighted average of current and future expected targets. Fast-decaying signals get less weight. — referenced in [Optimal multi-asset trading with linear costs, arXiv 1905.04821](https://arxiv.org/pdf/1905.04821); original paper: [Gârleanu & Pedersen, NBER w15205 / J. Finance 2013](https://www.nber.org/papers/w15205) (original not fetched in this session)
- Crypto momentum (2014–2020, coins above $1M cap): weekly rebalancing carries significant transaction costs, while 2–8 week revision periods produce similar results and are more practical. — [HSE / Dobrynskaya](https://www.hse.ru/en/news/research/559533243.html)
- A turnover penalty in a mean-variance framework discourages excessive rebalancing in crypto portfolios, but it can also affect gross returns and risk. — [arXiv 2501.12841](https://arxiv.org/pdf/2501.12841)
- Monash: short lookbacks give high Sharpe ratios for crypto trend-following, but frequent rebalancing costs erode profits. — [Monash MCFS](https://www.monash.edu/business/mcfs/our-research/all-projects/investment-strategy/trend-following-strategies-for-crypto-investors)

### Inferences
- Break-even arithmetic per round trip (perp, majors): gross edge needed ≥ fees (4–10 bps) + spread/impact (about 1–2 bps) + expected funding (about 0–1 bp per 8h crossed) ≈ **8–13 bps at minimum, 15 bps with a safety margin**. For alts, plan on ≥ 20–40 bps. Spot needs ≥ 22–25 bps for majors.
- Annual cost drag = cost per round trip × round trips per year. At 6 bars per day, flipping every bar gives about 2,190 round trips a year. At 10 bps that is about 219% of notional per year, which is impossible to overcome. Even one round trip per day costs about 36.5%/year at 10 bps. Turnover is the dominant design variable for 4H systems.
- Practical controls:
  - Hysteresis: enter at signal > θ_in and exit at signal < θ_out < θ_in.
  - No-trade band: skip rebalances whose |Δweight| is below a buffer (for example, 20–30% of the target weight, or a band sized from cost via the ε^(1/3) scaling).
  - Minimum holding period of N bars.
  - Partial adjustment (Gârleanu–Pedersen style): move a fraction toward the target each bar.
  - Signal smoothing: average signals over several bars.
  - A cost-aware objective: optimize net Sharpe with a turnover penalty, not gross Sharpe.
- Always report gross versus net results and turnover per year, and test cost sensitivity at 1×, 1.5× and 2× the assumed costs.

### Gaps
- No crypto-specific empirical study of buffer or no-trade-zone rules at 4H frequency was found. Their effect must be measured in the project's own pre-registered backtests.

## 5. Maker (limit/post-only) vs taker execution

### Takeaway
On perps, maker execution saves 3 bps per side plus the half-spread, but it carries non-fill and adverse-selection risk: fills arrive mostly when price moves against you, and missed fills cluster on the best trades. For a 4H signal, a short time-boxed post-only attempt followed by a taker fallback is the usual compromise. On spot VIP0 there is no fee benefit at all.

### Cited Findings
- Live-trading experiments on Binance BTC perpetuals: profitable orders tend to get worse-than-expected outcomes. The effect is strongest for market orders, which get worse fill prices. Marketable limit orders have a substantial probability of failing to fill immediately. Failure to fill is associated with positive future short-term returns. The discrepancies are tied to volatility, latency and liquidity. — [Oxford/QMUL, Quantitative Finance 2025 (RePEc)](https://ideas.repec.org/a/taf/quantf/v25y2025i6p919-947.html); [ORA](https://ora.ox.ac.uk/objects/uuid:cdab1de2-7576-42e2-abae-ab12371eba76)
- Limit-order fills are induced whenever there is an adverse price movement (the "negative drift" of a fill). Backtested fill rates range from 30% to 85% depending on the fill model, so simulated maker performance is highly assumption-sensitive. — [The Negative Drift of a Limit Order Fill, arXiv 2407.16527](https://arxiv.org/pdf/2407.16527)
- Binance spot `LIMIT_MAKER` is a post-only order, rejected if it would match immediately as a taker. — [Binance Spot API trading endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints)

### Inferences
- Do not backtest maker fees with 100% fills. Model fill probability, and charge taker cost on the unfilled share (with the adverse move during the wait).
- Suggested 4H executor policy: post-only (perps `timeInForce=GTX`; verify in the New Order docs) at the best bid/ask, wait 30–120 s, reprice once or twice, then fall back to a taker order. Always use taker for stops and risk exits.
- Expected saving on perps: at most about 3 bps fee plus about 0.5 bp spread per side on majors. Fill-rate risk can erase this when signals are strong, so measure realized slippage versus the decision price in live or testnet logs.

### Gaps
- No study measuring realized maker-versus-taker net cost on Binance perps for small (under $10k) orders at 4H frequency was found.

## 6. Order types, API mechanics, rate limits and test environments

### Takeaway
Since 2025-12-09, USDT-M conditional orders (STOP_MARKET, TAKE_PROFIT_MARKET, STOP, TAKE_PROFIT, TRAILING_STOP_MARKET) must go through `POST /fapi/v1/algoOrder`. The old `/fapi/v1/order` path rejects them with -4120. Spot supports STOP_LOSS(_LIMIT), LIMIT_MAKER, OCO, OTO, OTOCO and OPO order lists. Use `demo-fapi.binance.com` for the futures demo and `testnet.binance.vision` for the spot testnet.

### Cited Findings
**USDT-M algo / conditional orders**
- Changelog (2025-11-06): "Effective on 2025-12-09, USDⓈ-M Futures will migrate conditional orders to the Algo Service". After migration, `POST /fapi/v1/order` and `/fapi/v1/batchOrders` reject these types with error -4120 STOP_ORDER_SWITCH_ALGO. — [Binance Derivatives Change Log](https://developers.binance.com/docs/derivatives/change-log)
- The `CONDITIONAL_ORDER_TRIGGER_REJECT` user-stream event was deprecated effective 2025-12-15. Rejection reasons now arrive in `ALGO_UPDATE`. — [Change Log](https://developers.binance.com/docs/derivatives/change-log)
- Since 2025-12-29, the conditional-order limit is 200 across all symbols, and the `MAX_NUM_ALGO_ORDERS` filter was removed from exchangeInfo. — [Change Log](https://developers.binance.com/docs/derivatives/change-log)
- Since 2026-06-20, `POST /fapi/v1/algoOrder` counts weight 1 against the 10 s order limit and 1 against the 1 min order limit, with IP weight 0. — [Change Log](https://developers.binance.com/docs/derivatives/change-log)
- `POST /fapi/v1/algoOrder` details:
  - `algoType=CONDITIONAL`, covering STOP_MARKET, TAKE_PROFIT_MARKET, STOP, TAKE_PROFIT and TRAILING_STOP_MARKET. It uses a trigger price instead of the old stopPrice field.
  - `closePosition`: used with STOP_MARKET or TAKE_PROFIT_MARKET; closes the whole position when triggered. It cannot be combined with `quantity` or `reduceOnly`, and in Hedge Mode it cannot be used for BUY-LONG or SELL-SHORT.
  - `reduceOnly`: default false; cannot be sent in Hedge Mode or with closePosition=true.
  - `workingType`: MARK_PRICE or CONTRACT_PRICE, default CONTRACT_PRICE.
  - `priceProtect`: default false; when on, the gap between mark and contract price at trigger must not exceed the symbol's `triggerProtect` from exchangeInfo.
  - Source: [New Algo Order (TRADE)](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Algo-Order)
- Modify Order: sending `reduceOnly=true` against an order not placed as reduce-only is rejected with -5047. After the COIN-M migration, UM and CM share the same `dualSidePosition` setting. Changing it is rejected with -4067 if open orders exist and -4068 if a position is open. — [Binance USDⓈ-M trade docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Algo-Order)
- Community reports confirm STOP_MARKET submissions failing with -4120 after the switch. — [nautilus_trader issue #3287](https://github.com/nautechsystems/nautilus_trader/issues/3287)

**USDT-M general info**
- Production REST: `https://fapi.binance.com`. Testnet REST: `https://demo-fapi.binance.com`. Testnet WebSocket: `wss://demo-fstream.binance.com`. — [USDⓈ-M General Info](https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info). The older host `testnet.binancefuture.com` still appears on the New Algo Order page and in older guides ([Medium](https://medium.com/@joaotx/building-a-binance-futures-client-in-python-part-i-3c3ac3b40639)). This conflicts with General Info; verify which one is live.
- Rate limits come from the `rateLimits` array in `/fapi/v1/exchangeInfo`. Responses carry `X-MBX-USED-WEIGHT-1M` and `X-MBX-ORDER-COUNT-10S/1M` headers. Weight limits apply per IP, and order limits apply per account. — [General Info](https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info)
- `recvWindow` defaults to 5000 ms. The server accepts a request only if `timestamp < serverTime + 1000` and `serverTime − timestamp ≤ recvWindow`. — [General Info](https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info)
- Error semantics:
  - HTTP 503 "Unknown error…" means the request may have succeeded. Do not treat it as a failure; verify through the user stream or an orderId/clientOrderId query.
  - 503 "Service Unavailable" and "Internal error" are definite failures. Retry with backoff of about 200/400/800 ms, for 3–5 attempts.
  - -1008 throttling is a definite failure. Close-position, reduce-only and cancel requests are exempt from this throttling.
  - 429 means back off. Continuing after 429s produces 418 IP bans, which scale from 2 minutes to 3 days.
  - Source: [General Info](https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info)
- 2026-07-29: `historicalTrades` weight rose from 20 to 200. — [Change Log](https://developers.binance.com/docs/derivatives/change-log)

**Spot**
- `STOP_LOSS` triggers a market order. `STOP_LOSS_LIMIT` places a limit order on trigger and needs price, stopPrice (or trailingDelta) and timeInForce. `LIMIT_MAKER` is post-only. — [Spot trading endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints)
- OCO (`POST /api/v3/orderList/oco`) pairs an above and a below order. One leg must be LIMIT_MAKER, TAKE_PROFIT or TAKE_PROFIT_LIMIT; the other must be STOP_LOSS or STOP_LOSS_LIMIT. It counts as 2 unfilled orders. OTO, OTOCO and OPO (`/api/v3/orderList/opo`, working plus pending order) also exist. — [same](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints)
- Spot `newClientOrderId` can be reused only after the previous order is filled; otherwise the order is rejected. `listClientOrderId` must be unique among open order lists. — [same](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints)
- Spot testnet: `https://testnet.binance.vision`. — [same](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints)
- Spot Demo Mode uses a demo API key from Binance Demo Trading with demo URLs. Demo mode always has the same features as the live exchange, whereas the testnet sometimes gets features first. — [Spot Demo Mode](https://developers.binance.com/en/docs/products/spot/demo-mode/general-info)
- Demo outages happen: COIN-M demo trading was unavailable from 2026-06-16 02:00 to 2026-06-23 10:00 UTC. — [Change Log](https://developers.binance.com/docs/derivatives/change-log)

### Inferences
- Any executor or library written before December 2025 that places STOP_MARKET via `/fapi/v1/order` is broken. Protective stops must use `/fapi/v1/algoOrder` and be tracked through `ALGO_UPDATE`, which is a separate ID space from normal orders. Reconciliation must query both the open-orders and open-algo-orders endpoints.
- For stops, prefer `workingType=MARK_PRICE`. Mark price is index-based and less prone to wick-triggering on thin last-trade prints than CONTRACT_PRICE (the default). Set it explicitly.
- Use `closePosition=true` (One-way mode) for the catastrophic stop, so that it closes whatever size remains. Use `reduceOnly=true` on all exit or TP orders so an exit can never flip or increase a position.
- At 4H frequency, rate limits are not binding for a 10–30 coin universe. The real risk is a burst at the bar close, so sequence calls and read the headers.

### Gaps
- Exact numeric USDT-M limits (REQUEST_WEIGHT per minute, ORDERS per 10 s and per minute) were not on the General Info page. Read them from `exchangeInfo.rateLimits` at startup.
- Futures `newClientOrderId` rules (max length, allowed characters, duplicate behavior) and the details of the spot OTO/OTOCO endpoints were not retrieved.
- The `demo-fapi` vs `testnet.binancefuture.com` conflict was not resolved by a single authoritative statement.

## 7. Operational requirements for an executor running every 4 hours

### Takeaway
The executor must be clock-disciplined, idempotent and self-reconciling. It runs shortly after the UTC 4H close, fetches only closed bars, derives deterministic clientOrderIds, treats unknown-status responses as "maybe filled", reconciles exchange state against intended state on every run, keeps exchange-side stops at all times, and has a kill switch and alerting.

### Cited Findings
- The timestamp and recvWindow checks (5000 ms default, server rejects if `timestamp ≥ serverTime + 1000`) require clock sync. — [USDⓈ-M General Info](https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info)
- A timed-out 503 may have executed, so verify through the WebSocket or an orderId query to avoid duplicates. Back off on 429 to avoid 418 bans. — [General Info](https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info)
- Funding settles at 00/08/16 UTC (±15 s), and intervals can switch to 1h automatically. — [Funding FAQ](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- Spot clientOrderId reuse is rejected while the previous order is still open, which makes it usable as an idempotency key. — [Spot trading endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints)
- Close-position, reduce-only and cancel requests are exempt from -1008 throttling, so risk-reducing actions get through under load. — [General Info](https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info)

### Inferences
These are an engineering checklist derived from the cited mechanics.
1. **Clock alignment.** Sync with NTP and compare against `GET /fapi/v1/time`. Trigger at 00/04/08/12/16/20 UTC plus 30–90 s. Fetch klines and drop any bar whose `closeTime > now` (the forming bar). Assert that the last closed bar's openTime equals the expected boundary; if data is stale, skip and alert rather than trade on old data.
2. **Data latency.** Klines can lag a few seconds after the close. Retry until the expected bar appears, with a deadline of a few minutes, then skip the cycle.
3. **Idempotency.** Use clientOrderId = hash(strategy, symbol, bar_open_time, leg, attempt). Before placing an order, query by that ID. On timeouts or unknown 503s, query before resending.
4. **Retries.** Use exponential backoff on definite failures. Never blind-retry ambiguous ones. Honor 429s and the used-weight headers.
5. **Reconciliation each run.** Compare intended positions and orders against `positionRisk`, open orders and open algo orders (after the 2025 migration). Fix drift by reduce-only trades. Detect orphan stops (a stop with no position) and positions without stops.
6. **Exchange-side protection.** A `closePosition` STOP_MARKET (MARK_PRICE) through `/fapi/v1/algoOrder` must exist for every open perp, so the account survives executor downtime between runs (4h gaps).
7. **Kill switch.** Trigger flatten-and-halt on equity drawdown, a cumulative-slippage breach, repeated API errors, data staleness, or a manual flag file. Flatten with reduce-only market orders, which are exempt from -1008 throttling.
8. **Monitoring and logging.** Record a per-run heartbeat. For each order, log decision price versus fill price (realized slippage), fees and funding paid (from the income history). Send alerts on missed runs, and run a daily P&L reconciliation against the exchange.
9. **Configuration from the exchange.** Read tick and lot sizes, minimum notional, `triggerProtect`, funding interval, leverage brackets and commission rate (`/fapi/v1/commissionRate`) at startup. Hard-coded values silently go stale.
10. **Environment parity.** Test on `demo-fapi.binance.com` (and the spot demo or `testnet.binance.vision`). Demo environments have outages, and the testnet can diverge from production features, so dry-run any new endpoint (such as algoOrder) there before production.

### Gaps
- No official Binance "best practices for bots" document covering reconciliation or kill switches was found. Items 1–10 are engineering inferences grounded in the cited API semantics, not quoted Binance guidance.
- Kline publication latency after the bar close was not documented in the sources retrieved.
