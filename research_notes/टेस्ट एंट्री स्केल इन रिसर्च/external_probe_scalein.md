# Probe/test entries, scaling-in (pyramiding), confirmed/delayed entry, and "earn a little every 5 minutes": external evidence

Compiled 2026-10-17. English evidence notes for a Hindi report. Labels: [PEER] peer-reviewed, [WP] working paper/preprint, [PRAC] practitioner/book/forum, [OFFICIAL] exchange docs, [LIVE] read directly from the live API in this session, [CALC] my own arithmetic (no external source).
Nothing from the project's archive/ folder was used.

## Q1. Pyramiding / scaling-in vs full-size entry: what does the evidence say?

### Takeaway
I found no peer-reviewed controlled test of "with pyramiding vs without" (same entries, exits and costs) for any asset. The rule itself is well documented (Turtles: add a unit every 0.5N, up to 4 units). Theory says scaling in after a favorable move is just a position size that depends on past returns. It adds value only when returns at the holding horizon are positively autocorrelated (momentum), and it destroys value under a random walk or mean reversion. Kaminski & Lo prove the mirror image of this for stop-losses. Any value here has to be shown in the project's own pre-registered test.

### Cited Findings
- **Turtle rule (documented).** Add 1 unit at every 0.5N (N = 20-day ATR) move in favor of the previous entry. Cap of 4 units per market, with further caps for correlated markets and per direction (e.g. 12 units one way). [PRAC] MQL5 "Original Turtle Trading Rules" implementation article — [MQL5](https://www.mql5.com/en/articles/23448). Sources disagree on two points. Covel's book describes adding every full N, not 0.5N. The cap for closely correlated markets is given as 6 in one source and 10 in another — [metalsmine forum thread](https://www.metalsmine.com/thread/371711-turtle-trading). I could not open the primary text (Faith, *Way of the Turtle*, 2007, and Faith's free "Original Turtle Trading Rules" PDF).
- **No isolated test of pyramiding in the Turtle sources.** The Turtle results usually quoted are for the full system (entry + pyramiding + 2N stop + exits). I found no source that switches pyramiding on and off with everything else held fixed. (Gap; see below.)
- **Practitioner anecdote, contested.** One trader says most of the pyramiding systems he backtested did worse with pyramiding on. The same poster says adding to winners can still make sense in principle. [PRAC] single forum anecdote, not a controlled study — [EliteTrader](https://www.elitetrader.com/et/threads/pyramiding-adding-to-a-trade.114830/).
- **Mechanism (practitioner).** Each added unit sits closer to the trailed stop, so normal pullbacks stop out more often and the win rate falls. The payoff comes only from long trends — [LuxAlgo](https://www.luxalgo.com/library/concept/pyramiding/). Adds of equal size raise account-level risk sharply. Adds of decreasing size keep the original risk profile — [TradersSecondBrain](https://traderssecondbrain.com/guides/pyramiding-strategy). [PRAC] Neither source gives an out-of-sample test.
- **Clenow, *Following the Trend* (Wiley, 2013; 2nd ed. 2023).** The core diversified-futures model uses ATR-based sizing with a 100-day-high entry and a 50-day-low exit. The public summaries I found do not mention pyramiding — [O'Reilly listing](https://oreilly.com/library/view/following-the-trend/9781118410844); [QuantConnect forum](https://www.quantconnect.com/forum/discussion/19661/clenow-follow-the-trend-futures-trading-strategy/). [PRAC] I could not verify from the book's text whether Clenow tests pyramiding.
- **Stop-loss theory (mirror of scaling-in).** Kaminski & Lo, "When do stop-loss rules stop losses?", *Journal of Financial Markets* 18 (2014) 234–254, doi:10.1016/j.finmar.2013.07.001 [PEER]. Under a random walk, simple 0/1 stop-loss rules always reduce expected return. Under momentum (positive serial correlation) they can add value. On daily index futures, some stop rules raised expected return and cut volatility. The working paper reported +50–100 bps/month during stop-out periods; I did not verify that figure against the published version — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/114876); [SIFR WP abstract](https://swopec.hhs.se/sifrwp/abs/sifrwp0063.htm). (I could not read the full PDF: HTTP 429.)
- **Optimal trend-following weights.** Valeyre (2022), arXiv 2201.06635 [WP]. The approximately optimal portfolio weight is a linear mix of a term driven by autocorrelation (trend) and an expected-return term. A position that grows with the trend signal is therefore optimal only to the extent that the autocorrelation term is positive — [arXiv](https://arxiv.org/abs/2201.06635).
- **Crypto has time-series momentum at weekly horizons.** Liu & Tsyvinski, "Risks and Returns of Cryptocurrency", *RFS* 34(6) 2021, 2689–2727 [PEER]. They report "a strong time-series momentum effect" and find that investor-attention proxies forecast returns. The sample is BTC/XRP/ETH at daily/weekly frequency, in-sample, and transaction costs are not the focus — [IDEAS/RFS](https://ideas.repec.org/a/oup/rfinst/v34y2021i6p2689-2727..html); [NBER WP 24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf).
- **Crypto intraday is mixed and often mean-reverting.**
  - BTC shows negative first-order autocorrelation at 1-, 2- and 4-hour horizons, and larger moves reverse more — "On the Intraday Behavior of Bitcoin", *Ledger* [PEER] — [Ledger](https://ledger.pitt.edu/ojs/ledger/article/view/213).
  - Significant autocorrelation at 5-minute and 1-hour frequencies on BTC/ETH markets, with mixed sign — arXiv 2003.13517 [WP] — [arXiv](https://arxiv.org/abs/2003.13517).
  - 5-minute first-order autocorrelations across altcoins are about −0.09 to +0.01 — arXiv 2009.04200 [WP] — [arXiv](https://arxiv.org/pdf/2009.04200).
  - These findings come from abstracts and snippets. I did not verify them in the full texts.

### Inferences
- Pyramiding is not an independent edge. It is a bet that returns are positively autocorrelated over the remaining holding horizon. Crypto shows momentum at daily/weekly horizons (Liu & Tsyvinski) but intraday reversal at 1–4 hours (Ledger). So adding to 5-minute or 1-hour winners works against the documented sign, while adding on a 1D/4H trend system is at least consistent with it. This is an inference; it has not been tested here.
- Scaling in (e.g. 25% probe, then adds) also costs extra: one more round of fees per add, and a worse average price than a full-size entry at the first signal. When the trade fails, the loss is smaller. When it succeeds, the profit is smaller than full size from the start, unless the system has momentum at the add horizon.
- Martingale (averaging down) is the opposite bet: it wins under mean reversion and is ruinous under trends or fat tails. I found no peer-reviewed sizing study that compares martingale with anti-martingale (gap).

### Gaps
- No published controlled ablation of "Turtle with vs without the 0.5N adds". The project would need to run it itself: pre-registered, SHA-locked, same signals, fees included.
- I could not confirm the half-N vs full-N rule from Faith's primary text.
- I could not obtain Clenow's view on pyramiding from the book text.
- No academic paper found on "optimal scaling into a position under momentum" as a stochastic-control problem. The closest are Valeyre (2022) and a UGA PhD thesis (Kong 2010) on trend following with regime switching, which does not cover scaling in — [UGA PDF](https://openscholar.uga.edu/record/18625/files/kong_hoi-tin_201008_phd.pdf).
- No direct empirical study of retail "averaging down" vs "pyramiding" found. Only the disposition-effect literature (Q3).

## Q2. "Paper-confirm then enter" (delayed or confirmed entry): does waiting for a favorable move help after costs?

### Takeaway
I found no academic evidence that confirmation entries (entering only after price moves x ATR in favor) beat immediate entry after costs. The strongest specific evidence is a warning: confirmation filters easily create look-ahead bias through the fill price. One documented case turned a −0.11 R system into a fake +0.90 R. Economically, a confirmed entry equals "immediate entry minus the first x ATR of the move", plus more stop-outs from reversals. It can only help if the move after confirmation is more persistent than the move after the original signal.

### Cited Findings
- **Confirmation-filter bug case study (2026).** [PRAC] blog by Timon-pascal Krueger, 26 Sep 2026.
  - Setup: breakout on a 10-minute reference candle at 12:10 NY, on NQ/Dow/SPX, 2015–2026.
  - Gate: volume must reach at least its 20-period average.
  - Bug: the trigger came a median of 100 minutes late, but the backtest still filled at the breakout level.
  - Reported vs corrected: gated version reported +0.90 R/trade and a 59.8% win rate (7,941 trades). The honest version is about −0.11 R/trade with a 29.3% win rate.
  - Size of the head start: at trigger time the median trade was already about 0.35 R in profit. In 63% of trades price was already past the level, and the 75th percentile was about 1.2 R.
  - The author did not test whether volume confirmation, priced at the trigger candle, adds value.
  - [MQL5 blog](https://www.mql5.com/en/blogs/post/776238)
- **Stop-loss theory applies symmetrically.** Waiting for a favorable move is a conditional entry on past returns. Its value depends on serial correlation, exactly as in Kaminski & Lo (2014) [PEER] — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/114876).
- **Short-horizon BTC tends to reverse at 1–4 hours** — [Ledger](https://ledger.pitt.edu/ojs/ledger/article/view/213). Waiting for an intraday favorable move therefore tends to buy just before a partial reversal. (This is an inference from the Ledger finding, not a direct test.)

### Inferences
- "Paper-confirm" (watching a virtual position and entering only if it is up by x) is the same as entering with a lag of x. Test it like this:
  - fill at the actual confirmation bar's next open, never at the original signal price;
  - charge the full fee and spread;
  - compare against immediate entry and against a random-delay control.
- On Binance, a "test trade" of 5 USDT (Q4) costs nearly nothing in fees but gives no information beyond what a paper position gives. Price action is the same for both. Only fill quality and slippage differ, and those are not measurable at 5 USDT size.

### Gaps
- No peer-reviewed study comparing breakout-confirmation entry with immediate entry after costs, in crypto or elsewhere. Search returned only TradingView scripts and blogs.

## Q3. Economics of very frequent small-profit trading ("earn a little every 5 minutes")

### Takeaway
The large-sample evidence on retail short-horizon traders is consistently negative after costs:
- Taiwan: 97% of day traders are likely to lose in future day trading.
- Brazil futures: 97% of persistent day traders lost money, and only 3% had positive net daily returns.
- EU CFDs: 74–89% of retail accounts lose money.
- Crypto: most app users lost money on bitcoin.

The fee arithmetic is brutal at small targets. With taker fees, a 0.2–0.3% target needs a 67–100% win rate just to break even.

### Cited Findings
- **Barber, Lee, Liu & Odean, Taiwan (Cross-Section of Speculator Skill).** [WP, May 2011 version] All day traders, Taiwan Stock Exchange, 1992–2006. Out-of-sample sort: rank traders in year y, measure year y+1.
  - Top 500: +49.5 bps/day before fees, +28.1 bps/day after fees.
  - Bottom-ranked: −17.5 before, −34.2 after.
  - So a tiny persistent elite exists; the majority does not profit.
  - Verified from the PDF text — [Berkeley PDF](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf).
  - Secondary commentary: over a typical 6-month horizon, fewer than 20% earn profits net of costs — [Investment Executive](https://investmentexecutive.com/?p=328717).
  - The often-quoted "less than 1% are predictably profitable" appears only in secondary sources (a TradingView blog). I could not verify it in a primary abstract, so treat it as unverified.
- **Barber, Lee, Liu, Odean (& Zhang), "Learning, Fast or Slow", *Review of Asset Pricing Studies* 10(1) 2020, 61–93** [PEER]. Same Taiwan data.
  - 74% of day-trading volume comes from traders with a history of losses.
  - 97% of day traders are likely to lose money in future day trading.
  - Persistence fits overconfidence and biased learning better than rational learning.
  - [IDEAS](https://ideas.repec.org/a/oup/rasset/v10y2020i1p61-93..html); [AEA 2019 draft](https://aeaweb.org/conference/2019/preliminary/paper/ZKnGb4Zh)
- **Barber, Lee, Liu & Odean (2009), *RFS*, "Just how much do individual investors lose by trading?"** [PEER]. Complete Taiwan data, 1995–1999. Individual trading costs them 3.8 percentage points a year, and aggregate losses exceed 2% of Taiwan GDP — [Berkeley PDF](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/justhowmuchdoindividualinvestorslose_rfs_2009.pdf).
- **Chague, De-Losso & Giovannetti, "Day Trading for a Living?"** [WP, SSRN 3423101, 2019, rev. 2020; FGV-EESP].
  - Sample: Brazil mini-Ibovespa futures; everyone who started 2013–2015 and kept trading at least 300 days (19,646 individuals had first day-traded).
  - 97% lost money.
  - Only 11% had positive gross and 3.0% positive net average daily returns.
  - Only about 0.4–0.5% earned more than a bank teller (US$54/day); the top earner made US$310/day with high risk.
  - No evidence of learning.
  - Net of exchange and brokerage fees, before taxes and course/platform costs.
  - Caveat: one period and one market — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101); [FGV repository](https://repositorio.fgv.br/items/e87d04fc-4b4c-4a56-ab5a-1c84c1afde1b/full); [CXO summary](https://www.cxoadvisory.com/investing-expertise/day-trading-a-bust/).
- **ESMA (2018) product intervention** [OFFICIAL]. National regulators' analyses found 74–89% of retail CFD accounts lose money, with average losses of €1,600–€29,000 per client. Leverage caps of 30:1 to 2:1 followed. The figures date from 2018 — [ESMA](https://www.esma.europa.eu/node/84933).
- **BIS Bulletin No. 69, Cornelli, Doerr, Frost & Gambacorta, "Crypto shocks and retail losses" (Feb 2023)** [OFFICIAL/central-bank research].
  - Data: crypto app downloads, Aug 2015–Dec 2022.
  - Most retail crypto app users in nearly all economies lost money on bitcoin.
  - Retail bought while large holders sold around Terra/Luna and FTX.
  - The "$431 / 47.89%" loss figure comes from a $100/month model, and secondary sources call it both average and median, so check the PDF before using it — [BIS](https://www.bis.org/publ/bisbull69.htm).
- **Disposition effect.** Odean (1998), *Journal of Finance*, "Are Investors Reluctant to Realize Their Losses?" [PEER]. 10,000 discount-brokerage accounts. Investors realize winners more readily than losers, and later returns do not justify it — [Berkeley](https://faculty.haas.berkeley.edu/odean/papers/disposition/disposition.html). This matters for small-target scalping: taking small profits quickly while holding losers is the disposition pattern.
- **No peer-reviewed study of retail crypto-perp leverage outcomes found.** Only vendor and press reports, e.g. Leverage.Trading's Sept 2025 report and Coinglass liquidation totals of about $154.6B for 2025 — [The Block press release](https://www.theblock.co/press-releases/376264/); [MEXC news](https://www.mexc.com/news/388166). Treat as weak evidence.
- **Breakeven win rates [CALC].**
  - Formula: win rate p must satisfy p·TP − (1−p)·SL − RT = 0, so p* = (SL + RT)/(TP + SL). RT is round-trip fees as a fraction. Spread, slippage and funding are excluded, so real breakevens are higher.
  - Fee assumptions (Q4): spot taker 0.1%/side, or 0.075% with BNB; USDT-M futures taker 0.05%/side (0.045% with BNB) and maker 0.02%/side (0.018% with BNB).

| Target/Stop | Spot taker (RT 0.20%) | Spot BNB (0.15%) | Futures taker (0.10%) | Futures taker+BNB (0.09%) | Futures maker (0.04%) | Futures maker+BNB (0.036%) |
|---|---|---|---|---|---|---|
| 0.2% / 0.2% | 100% | 87.5% | 75.0% | 72.5% | 60.0% | 59.0% |
| 0.3% / 0.3% | 83.3% | 75.0% | 66.7% | 65.0% | 56.7% | 56.0% |
| 0.5% / 0.5% | 70.0% | 65.0% | 60.0% | 59.0% | 54.0% | 53.6% |
| 0.3% / 0.6% | 88.9% | 83.3% | 77.8% | 76.7% | 71.1% | 70.7% |
| 1.0% / 1.0% | 60.0% | 57.5% | 55.0% | 54.5% | 52.0% | 51.8% |

### Inferences
- "Earn a little every 5 minutes" with market orders needs win rates that no documented retail population achieves. Only maker-only execution, possibly with VIP or rebate tiers, brings breakeven close to 50–56%. Maker-only adds adverse-selection risk: you get filled mainly when price is about to move against you. No retail-level evidence shows that this is overcome.
- 5-minute crypto returns have small, mixed-sign autocorrelation (Q1). The raw signal is tiny compared with 0.1–0.2% round-trip costs.
- The Chague and Taiwan results show competing at short horizons against HFTs is the hardest setting. Any 5-minute claim in the project needs an after-cost, out-of-sample, shuffled-control test before belief.

### Gaps
- No academic sample of Binance retail scalpers or perp traders with after-fee P&L found.
- No study of maker-rebate scalping profitability for retail.
- BIS loss figure not verified from the PDF.

## Q4. Binance specifics: how small can a "test trade" be, and how do BNB fee discounts work?

### Takeaway
On the live API (snapshot serverTime 2026-10-16 08:01 UTC):
- Spot minimum notional is 5 USDT for BTC/ETH/SOL/ADA-USDT and 1 USDT for DOGEUSDT.
- USDT-M perpetual minimum notional is 5 USDT for 519 symbols, 20 USDT for ETH/BCH/LTC/ETC/LINK, and 50 USDT for BTCUSDT.
- Binance says these thresholds change without notice. (A third-party note mentions an earlier $100 BTC-perp minimum; today's live value is 50.)
- BNB discount: 25% on spot/margin. For USDT-M futures, 10%, and only if the BNB is in the USDT-M futures wallet.

### Cited Findings
- **Spot NOTIONAL filter definition** [OFFICIAL]. Fields: minNotional, applyMinToMarket, maxNotional, applyMaxToMarket, avgPriceMins. An order must satisfy minNotional ≤ price×qty ≤ maxNotional. MARKET orders use the volume-weighted average price over the last avgPriceMins minutes (the last price if 0) — [Binance spot filters](https://developers.binance.com/docs/binance-spot-api-docs/filters).
- **Live spot values** [LIVE]. GET api.binance.com/api/v3/exchangeInfo, fetched 2026-10-16/17:
  - BTCUSDT, ETHUSDT, SOLUSDT, ADAUSDT: NOTIONAL minNotional 5.0, applyMinToMarket true, maxNotional 9,000,000, avgPriceMins 5.
  - DOGEUSDT: minNotional 1.0.
- **Futures MIN_NOTIONAL definition** [OFFICIAL]. Field `notional` (doc example "5.0"); notional = price×quantity. For MARKET orders the mark price is used — [Binance USDⓈ-M common definition](https://developers.binance.com/docs/derivatives/usds-margined-futures/common-definition).
- **Live futures values** [LIVE]. GET fapi.binance.com/fapi/v1/exchangeInfo, serverTime 1792137674760 = 2026-10-16 08:01:14 UTC, TRADING USDT perpetuals:
  - notional 5 → 519 symbols (e.g. XRP, ADA, BNB, TRX, ATOM);
  - notional 20 → 5 symbols (ETH, BCH, LTC, ETC, LINK);
  - notional 50 → BTCUSDT.
  - The quantity step (LOT_SIZE/MARKET_LOT_SIZE) also limits the smallest order; I did not tabulate it.
- **Thresholds change** [OFFICIAL]. "Binance Futures may adjust the minimum order threshold from time to time without prior notice" — [Binance contract specs](https://www.binance.com/en/support/articles/360033161972). A third-party note mentions a $100 BTC-perp minimum at some earlier time — [Tardis roadmap](https://roadmap.tardis.dev/feature-requests/p/add-minimum-order-notional-to-meta-data). This conflicts with the live 50; the live value governs.
- **Spot fees** [OFFICIAL]. Standard spot fee is 0.1% for regular users — [Binance fee structure FAQ](https://www.binance.com/en/support/faq/fee-structure-on-binance-115000429332).
  - Paying with BNB saves 25% on spot and margin fees and 10% on futures. The FAQ says the 25% is valid "until further notice".
  - Requires BNB in the Spot wallet and the BNB-deduction toggle on. If the BNB balance is insufficient, the full fee is charged.
  - [Binance BNB fee FAQ](https://www.binance.com/en/support/faq/how-to-use-bnb-to-pay-for-fees-and-earn-25-discount-115000583311?hl=en)
- **Futures fees** [OFFICIAL].
  - 10% discount on standard USDⓈ-M fees when paying with BNB. The BNB must be transferred to the USDⓈ-M Futures wallet; otherwise fees are charged in USDT with no discount.
  - Worked example uses regular maker 0.02% and taker 0.05%.
  - Taker-program discounts stack on top of the BNB and VIP rates.
  - [Binance Futures fee FAQ](https://www.binance.com/en-IN/support/faq/binance-futures-fee-structure-fee-calculations-360033544231)
  - Conflict: a user-written Binance Square post lists taker 0.04%, and an older FAQ example shows 0.015%/0.040% — [Binance Square](https://www.binance.com/en/square/post/14496572008914). Use the account's live commission rate (GET /fapi/v1/commissionRate) as ground truth.

### Inferences
- A probe of about 5–6 USDT is feasible on most spot pairs and most perps. ETH-perp needs at least 20 USDT and BTC-perp at least 50 USDT, so the probe size must be read from exchangeInfo at runtime.
- Fee cost of a 5 USDT spot probe round trip with BNB: about 5 × 0.0015 = 0.0075 USDT [CALC]. The cost is negligible. Its information value equals a paper trade, apart from fill realism.
- Scaling a probe up into a full position pays the per-side fee on each add. The fee rate is proportional, so the total fee is the same as one full-size entry, but the average entry price is worse if adds happen after a favorable move.

### Gaps
- I did not tabulate LOT_SIZE/stepSize, PRICE_FILTER or PERCENT_PRICE limits. These can also block tiny orders.
- I did not verify the current VIP-0 futures taker rate from the account endpoint.
- Testnet minimums may differ from mainnet.
