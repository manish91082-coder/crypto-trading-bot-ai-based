# Return-predictive signals in crypto at intraday to few-day horizons (4H focus), and net-of-cost survival

Scope: signals usable by a 4H-bar LONG/SHORT system on Binance spot and USDT-M perps (holds of 4h to about 3 days).
Method: 18 search/fetch calls (Oct 2026). Most items were checked from the abstract or landing page only. A full-PDF check is marked where one was done.
Verification labels used below:
- [ABSTRACT-VERIFIED]: read the primary abstract or landing page this session.
- [SEARCH-SNIPPET]: seen only in search-result summaries, not opened. Treat with lower confidence.
- [NOT VERIFIED]: from background knowledge only. Must be checked before use.
- PRE-2021 = old evidence that may have decayed.
- PREPRINT = not peer-reviewed.

---

## 1. Time-series momentum / trend at intraday horizons

### Takeaway
There is peer-reviewed evidence of BTC intraday momentum (first half-hour predicts last half-hour, Financial Review 2022). Its sample is pre-2021, though, and it does not map onto 4H bars. At 1h to 4h horizons, one study finds negative autocorrelation (mean reversion), the opposite sign. Lower-frequency trend following (daily bars, Donchian or time-series momentum) has the most net-of-cost support. No peer-reviewed study tests 4H-bar trend following with Binance costs.

### Cited Findings
- **Shen, Urquhart & Wang, "Bitcoin Intraday Time-Series Momentum," *Financial Review* 57(2), 2022, pp. 319-344 (Univ. of Reading / Birmingham).**
  - Because BTC has no close, the authors use a volume-based clock. The first half-hour return predicts the last half-hour return.
  - Predictability is strongest in high-volume and high-volatility sessions. They attribute it to liquidity provision rather than late-informed trading.
  - They report economic gains from market timing, especially in downturns.
  - Sample is pre-2021 (PRE-2021). Net-of-cost numbers were not verified. [SEARCH-SNIPPET + repository page] — [Birmingham repository](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/); [Reading accepted manuscript](https://reading-9.eprints-hosting.org/100181/3/21Sep2021Bitcoin%20Intraday%20Time%20Series%20Momentum.R2.pdf)
- **Borgards (2021), *North American Journal of Economics and Finance* 57.**
  - Covers 20 cryptocurrencies at interday and intraday frequencies.
  - Finds longer momentum periods than in US stocks, which the author links to noise trading. PRE-2021 data. [SEARCH-SNIPPET] — [EconPapers](https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000590)
- **De Nicola (2021), *Ledger*.**
  - Finds significant negative first-order autocorrelation in 1h, 2h and 4h returns, i.e. mean reversion at exactly the 4H horizon.
  - This contradicts a naive "4h trend" assumption. The PDF fetch failed, so details are unverified. [SEARCH-SNIPPET] — [Ledger PDF](https://ledger.pitt.edu/ojs/ledger/article/download/213/212/1232)
- **"Systematic Trend-Following with Adaptive Portfolio Construction" (arXiv 2602.11708, 2026, PREPRINT).**
  - Out-of-sample Jan 2022 to Dec 2024. The cost model includes a 4 bp taker fee, slippage tied to 5-minute volume, and 8-hour perp funding.
  - Best variant: net Sharpe about 2.41. Simple 1-month and 3-month time-series momentum: net Sharpe about 0.5-0.65.
  - The signal frequency is not clearly intraday, and the 2.41 is a best-variant result, so selection bias is likely. [SEARCH-SNIPPET] — [arXiv 2602.11708](https://arxiv.org/pdf/2602.11708)
- **Zarattini, Pagani & Barbon, "Catching Crypto Trends; A Tactical Approach for Bitcoin and Altcoins" (SSRN 5209907, 2025).**
  - A Donchian-channel ensemble on a rotational top-20 portfolio reports Sharpe above 1.5 net of fees, per the search snippet.
  - The SSRN page returned 403, so frequency, fee and long-only details are unverified. [SEARCH-SNIPPET] — [SSRN](https://papers.ssrn.com/sol3/Delivery.cfm/5209907.pdf?abstractid=5209907&mirid=1)
- **"A Decade of Evidence of Trend Following Investing in Cryptocurrencies" (arXiv 2009.12155, 2020).**
  - Daily trend following. The snippet says its returns assume negligible trading costs. PRE-2021. [SEARCH-SNIPPET] — [arXiv 2009.12155](https://arxiv.org/pdf/2009.12155)
- **"A Trend Factor for the Cross Section of Cryptocurrency Returns," *Journal of Financial and Quantitative Analysis* (Cambridge).**
  - The snippet says the trend signal survives transaction costs.
  - It is a cross-sectional, lower-frequency (weekly-type) signal. [SEARCH-SNIPPET] — [JFQA](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178)
- **Bysik & Ślepaczuk, "Machine Learning-Based Bitcoin Trading Under Transaction Costs: Evidence From Walk-Forward Forecasting" (arXiv 2606.00060, May 2026, PREPRINT).** [ABSTRACT-VERIFIED]
  - Data: about 70,000 hourly BTC-USDT observations, 2018-2026. Models: XGBoost, LSTM and iTransformer in a 27-fold walk-forward.
  - Gross performance is positive in selected configurations. Naive sign-based strategies fail once a 10 bp per-trade cost is applied.
  - A cost-aware filter (trade only when the forecast magnitude exceeds a cost threshold) restores profitability in some configurations. The best long-only XGBoost reports more than 65% annualised return and Sharpe above 1.
  - Bootstrap tests do not confirm that any model dominates. — [arXiv 2606.00060](https://arxiv.org/abs/2606.00060)
  - A search snippet adds that hourly cost drag was 1.43-6.06 bp per hour, and that "transaction costs can completely reverse the conclusion drawn from gross equity curves." [SEARCH-SNIPPET] — [arXiv HTML](https://arxiv.org/html/2606.00060v1)

### Inferences
- At the 1h-4h horizon, the evidence on the sign of autocorrelation is mixed (De Nicola: reversal; Shen et al.: intraday momentum in specific windows). Neither a pure 4H trend nor a pure 4H reversal rule has strong published support.
- The robust net-of-cost trend evidence is at daily-plus frequency. A 4H system may do best using trend as a slower regime filter, with 4H bars used for entry timing.
- The Bysik & Ślepaczuk result is directly relevant to an AI system. A no-trade band of roughly "predicted move > round-trip cost" is the main driver of net profitability, not model choice.

### Gaps
- No peer-reviewed, Binance-specific 4H time-series momentum study with explicit costs and 2022-2026 data was found.
- Net-of-cost effect sizes for Shen et al. (2022) were not verified.
- No post-publication decay study was found for intraday BTC momentum.

---

## 2. Short-term reversal (hours to 1-3 days)

### Takeaway
Reversal is robust in gross terms. However, it is concentrated in illiquid or small coins and is largely compensation for providing liquidity. The largest coins show daily momentum rather than reversal. At 15-minute horizons on Binance, the gross edge (about 1.3 bp) is far below costs. Short-term reversal is the signal least likely to survive 0.1-0.5% round-trip costs on liquid coins.

### Cited Findings
- **"Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets," *International Review of Financial Analysis* 78 (2021).**
  - Daily data on more than 3,600 coins. Low previous-day-return coins outperform high-return coins the next day.
  - The effect is driven by illiquidity. The handful of largest, most tradeable coins show daily **momentum**, not reversal. Sample is mostly PRE-2021. [SEARCH-SNIPPET] — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1057521921002349); [IDEAS/RePEc](https://ideas.repec.org/a/eee/finana/v78y2021ics1057521921002349.html)
- **Riksbank Working Paper No. 413 (2022), also in *Journal of Banking & Finance* 142 (2022): "Trading volume and liquidity provision in cryptocurrency markets."**
  - Uses short-term reversal returns as a proxy for liquidity-provision returns.
  - These returns are larger in low-activity, smaller and more volatile pairs. [SEARCH-SNIPPET] — [Riksbank WP 413](https://www.riksbank.se/globalassets/media/rapporter/working-papers/2022/no.-413-trading-volume-and-liquidity-provision-in-cryptocurreny-markets.pdf); [EconPapers JBF](https://econpapers.repec.org/RePEc:eee:jbfina:v:142:y:2022:i:c:s0378426622001418)
- **Kitron & Wengrowicz, "Short-horizon mean reversion in cryptocurrency markets: a matched cross-market measurement" (arXiv 2608.21888, Aug 2026, PREPRINT).** [ABSTRACT-VERIFIED]
  - Data: 183 Binance pairs, every coin-year since 2021, with a frozen six-month holdout and comparison against 187 US stocks and ETFs.
  - 90% of pairs show significant directional reversal at 15 minutes. The gross edge peaks near **1.3 bp per trade** against an assumed 5 bp round-trip, which is "too small to clear benchmark spot capture costs."
  - Reversal concentrates after moves driven by aggressive taker flow. Lag-one autocorrelation on the major coins is near zero. — [arXiv 2608.21888](https://arxiv.org/abs/2608.21888)
- **Equity analogue (not crypto).** Short-term reversal fails to survive costs at large capacity in US stocks.
  - The cited thresholds are about $9bn in the US and $13bn globally. [SEARCH-SNIPPET] — [NBER conference paper](https://conference.nber.org/conf_papers/f68262/f68262.pdf)
- **Practitioner GitHub backtests: low reliability and unverified.**
  - Cross-sectional 1h reversal on Kraken with fee and half-spread costs: [billybraith17/crypto-stat-arb](https://github.com/billybraith17/crypto-stat-arb)
  - A 4H Binance stat-arb: [Jamestilfords/statarb-crypto](https://raw.githubusercontent.com/Jamestilfords/statarb-crypto/main/README.md)
  - Reversal "robust up to 20 bps": [ccollins80/crypto-stat-arb](https://raw.githubusercontent.com/ccollins80/crypto-stat-arb/main/README.md)
  - Do not treat any of these as evidence.

### Inferences
- On liquid Binance coins (the BTC, ETH, SOL tier), reversal at 4h-1d horizons is weak or of the wrong sign (daily momentum in the largest coins). On illiquid coins it is stronger, but that is where spread, slippage and short-borrow or funding costs are highest.
- Expected net edge for a 4H taker strategy using reversal on liquid coins: likely about zero or negative. This is an inference, not measured at 4H.
- Taker-flow-driven moves are the ones that revert (Kitron & Wengrowicz). The taker buy/sell ratio is a plausible conditioning variable for a reversal model.

### Gaps
- No study was found that directly measures 4H or 1-3 day reversal net of Binance fees, split by liquidity tier, on 2022-2026 data.

---

## 3. Cross-sectional momentum at hours-to-days horizons

### Takeaway
The canonical crypto cross-sectional evidence (Liu, Tsyvinski & Wu) is at **weekly** frequency, with market, size and momentum factors. No verified evidence was found that cross-sectional momentum works at hourly or 4H frequency net of costs. At the daily horizon, the evidence is "momentum in large coins, reversal in small coins."

### Cited Findings
- **Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency" (NBER WP 25882; *Journal of Finance* 2022, DOI 10.1111/jofi.13119).**
  - Three factors (crypto market, size and momentum) explain 9-10 cross-sectional strategies.
  - Portfolios are formed **weekly** (quintile sorts, long top / short bottom).
  - The sample is about 2014-2018, so PRE-2021 with decay possible.
  - The snippets conflict on the venue: JF 2022 vs. an Alpha Architect mention of *Economic Modelling* (2020). The JF listing is the more credible. [SEARCH-SNIPPET] — [NBER w25882](https://www.nber.org/papers/w25882.pdf); [SSRN 3379131](https://papers.ssrn.com/abstract=3379131); [Yale Cowles PDF](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf); [Alpha Architect summary](https://alphaarchitect.com/2022/06/factors-investing-in-cryptocurrency)
- **AUT working paper on time-series and cross-sectional momentum in crypto.** It exists, but its details were not opened. — [AUT ACFR PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)
- **Daily cross-sectional pattern.** Momentum holds in the largest coins and reversal in illiquid coins (IRFA 2021, Section 2 above). — [IDEAS](https://ideas.repec.org/a/eee/finana/v78y2021ics1057521921002349.html)

### Inferences
- For a 4H system, cross-sectional momentum is probably better used as a **slow ranking input** (e.g., 1-4 week relative strength, for choosing which coins to go long vs. short) than as a 4H-horizon signal.

### Gaps
- No verified post-2021 out-of-sample test of the Liu-Tsyvinski-Wu momentum factor was found.
- No intraday (hourly or 4H) cross-sectional momentum paper with costs was found.

---

## 4. Intraday seasonality (time-of-day, day-of-week, funding times, session opens)

### Takeaway
There is strong, repeatedly documented periodicity in **volatility, volume and liquidity**: by hour of day, day of week, global market opens and clock-time marks. Evidence for tradable **directional return** seasonality is weak, mostly in-sample, and from secondary sources. The newest finding (Kim & Hansen 2026) is that order imbalance at quarter-hour openings predicts returns 4-12 hours ahead on Binance perps, which matches the 4H horizon directly.

### Cited Findings
- **Kim & Hansen, "The Quarter-Hour Effect: Periodic Algorithmic Trading and Return Predictability in Cryptocurrency Futures" (arXiv 2607.09426, July 2026, PREPRINT).** [ABSTRACT-VERIFIED]
  - Data: trades on 6 Binance perpetual contracts.
  - Volatility and volume burst at 1-minute, 5-minute and quarter-hour marks. Trade-size roundness falls during these bursts, which the authors link to algorithmic participation.
  - Opening returns are predictable out of sample. **Opening order imbalance predicts returns over 4-12 hours**, with much weaker effects at finer clock-time frequencies.
  - Effect sizes and net-of-cost results were not on the abstract page. — [arXiv 2607.09426](https://arxiv.org/abs/2607.09426)
- **"Periodicity in Cryptocurrency Volatility and Liquidity" (arXiv 2109.12142).**
  - BTC and ETH on Binance, Coinbase Pro and Uniswap V2. Strong day-of-week, hour-of-day and within-hour periodicity in volatility and liquidity.
  - The authors conjecture that algo trading drives these patterns, and that some relate to perp funding rates.
  - This is about volatility and liquidity, not return direction. [SEARCH-SNIPPET] — [arXiv 2109.12142](https://arxiv.org/pdf/2109.12142)
- **Reading working paper (Univ. of Reading).**
  - Realised volatility is fairly constant through the day but highest at the opening times of the three major stock markets. Liquidity is highest at those opens and lowest in the early morning.
  - PRE-2021. [SEARCH-SNIPPET] — [Reading manuscript](https://centaur.reading.ac.uk/81745/3/2.R%26R.Manuscript.pdf)
- **"Rise of the Machines?" (arXiv 2009.04200).**
  - Absolute returns fall during European sleeping hours (Jul-Aug 2018, a very short sample). PRE-2021. [SEARCH-SNIPPET] — [arXiv 2009.04200](https://arxiv.org/pdf/2009.04200)
- **Quantpedia summary of a Gemini hourly BTC study (2015-2022).**
  - No statistically significant negative hour; the worst hours are 03:00-04:00 UTC.
  - Proposes an in-sample rule (buy 21:00 UTC, sell 23:00 UTC). This is secondary, in-sample and at high risk of data-mining. [SEARCH-SNIPPET] — [Quantpedia](https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/); [Quantpedia strategy page](https://quantpedia.com/strategies/intraday-seasonality-in-bitcoin)
- **Funding times (00/08/16 UTC).** No academic study was found of directional returns around Binance funding settlement times.
  - Mechanics: Binance funding = average premium + clamp(1 bp - P, ±5 bp), and it tends to stick at 1 bp per 8h. [SEARCH-SNIPPET] — [Maverick Quant substack](https://maverickquant.substack.com/p/perpetual-futures)
  - An unverified comparison site claims BTC funding on Binance is clamped at 0.01% about 31% of the time. It also says major exchanges introduced dynamic settlement frequency in 2025 when rates hit caps. [SEARCH-SNIPPET, low reliability] — [spark.money](https://www.spark.money/tools/funding-rate-comparison)

### Inferences
- Time-of-day and session dummies are well justified as **volatility, liquidity and cost features** (position sizing, deciding when to execute). They are weakly justified as directional alpha.
- A 4H bar grid aligned to UTC (00, 04, 08, 12, 16, 20) puts bar boundaries on funding times and near the Asia, Europe and US opens. Clock-time effects at bar opens (Kim & Hansen) may therefore be directly exploitable as features, pending full-paper verification.

### Gaps
- Weekend and day-of-week **return** effects in 2022-2026 were not verified this session. No source was opened.
- There is no academic evidence on directional returns around funding times.
- Effect sizes for Kim & Hansen were not checked.

---

## 5. Volume, order-flow imbalance, taker ratio, OI, funding, basis and liquidations as predictors

### Takeaway
- **Order-flow and taker imbalance:** best documented at minutes-to-hours horizons. The 2026 Binance-perp evidence shows predictive power out to 4-12h (Kim & Hansen).
- **Funding and basis ("carry"):** BIS research shows that high crypto carry predicts **crashes** and **liquidations of shorts**, so it is useful mainly as a crowding and risk signal, at monthly horizons in that study.
- **Open interest and liquidations as return predictors:** no rigorous academic evidence was found. Practitioner claims are mostly about volatility, not direction.

### Cited Findings
- **Order imbalance at 4-12h horizons on Binance perps.** Kim & Hansen 2026, see Section 4. — [arXiv 2607.09426](https://arxiv.org/abs/2607.09426)
- **Taker-flow-driven moves revert at 15 minutes.** The gross edge is too small for costs. Kitron & Wengrowicz 2026. — [arXiv 2608.21888](https://arxiv.org/abs/2608.21888)
- **Cross-venue BTC trade flows.** The "Fragmentation, Price Formation, and Cross-Impact in Bitcoin Markets" paper argues that the cross-section of trade flows should explain future returns, but describes that as ongoing work. [SEARCH-SNIPPET] — [arXiv 2108.09750](https://arxiv.org/pdf/2108.09750)
- **Evans-Lyons framework.** A practitioner summary says world order flow explains about 11% of daily crypto returns. The underlying paper was not identified, so this is unverified. [SEARCH-SNIPPET] — [tradingstrategy.ai order flow](https://tradingstrategy.ai/docs/learn/order-flow.html)
- **Schmeling, Schrimpf & Todorov, "Crypto carry," BIS Working Paper 1087 (April 2023).** [ABSTRACT-VERIFIED]
  - "A high crypto carry predicts future price crashes." Rising carry coincides with higher prices for crash insurance.
  - Carry can reach about 60% per year and averages above 10% per year.
  - Drivers: a volatile convenience yield linked to leveraged retail trend-chasing, plus scarce arbitrage capital. — [BIS WP 1087 page](https://www.bis.org/publ/work1087.htm)
  - A search snippet from the PDF adds: carry predicts liquidations of **short** futures positions, and a 10% rise in standardized carry predicts short liquidations of about 22% of total open interest over the next month. The sample reportedly runs to July 2024 (likely a revised version).
  - The direction (short liquidations) is as given by the snippet and should be checked in the full PDF. [SEARCH-SNIPPET] — [BIS WP 1087 PDF](https://www.bis.org/publ/work1087.pdf)
- **Christin, Routledge, Soska & Zetlin-Jones, "The Crypto Carry Trade" (CMU).** The paper exists; its content was not reviewed. — [CMU PDF](https://www.andrew.cmu.edu/user/azj/files/CarryTrade.v1.0.pdf)
- **"Fundamentals of Perpetual Futures" (arXiv 2212.06888, He, Manela, Ross & von Wachter per background knowledge; authors [NOT VERIFIED]).**
  - No-arbitrage pricing for perps. Funding tracks the average perp-spot spread.
  - The perp-spot arbitrage strategy on Binance has a high Sharpe. At the high fee tier, adding the spread cuts BTC Sharpe from 3.35 to 3.27.
  - This is an arbitrage result, not a directional signal. [SEARCH-SNIPPET] — [arXiv 2212.06888](https://arxiv.org/html/2212.06888v7)
- **BitMEX funding vs. BTC price (arXiv 1912.03270, 2019).** GARCH and Granger causality on a small sample. PRE-2021. [SEARCH-SNIPPET] — [arXiv 1912.03270](https://www.arxiv.org/abs/1912.03270)
- **Liquidation cascades.** An arXiv 2026 preprint on early-warning signals across 7 BTCUSDT perp cascades finds them "event-heterogeneous."
  - It notes that Binance's per-event liquidationSnapshot data has been discontinued, so historical liquidation data now needs a commercial source. [SEARCH-SNIPPET] — [arXiv 2607.27070](https://arxiv.org/pdf/2607.27070)
- **Practitioner view (Amberdata blog, coinalyze).** Funding does not directly predict price but signals imbalance. High OI means higher cascade potential in **both** directions. These are non-rigorous sources. — [Amberdata funding](https://blog.amberdata.io/funding-rates-how-they-impact-perpetual-swap-positions); [Amberdata leverage & liquidations](https://blog.amberdata.io/leverage-liquidations-the-31b-deleveraging)

### Inferences
- For a 4H model, the most evidence-supported microstructure inputs are: signed order imbalance or taker buy/sell imbalance, especially at bar opens; and funding or basis **extremes** as crowding and crash-risk features.
- OI change and liquidations are better treated as volatility and risk-regime features than as directional alpha, because direction-specific evidence is lacking.
- Data-availability risk: Binance liquidation snapshots were discontinued, and funding settlement frequency became dynamic in 2025 per an unverified source. Feature pipelines must handle both.

### Gaps
- No peer-reviewed cross-sectional study of perp funding-rate level or change as a predictor of 4h-3d returns was found. Rigorous OI-change return-predictability evidence was also not found.

---

## 6. Volatility and range breakout strategies

### Takeaway
Breakout and channel (Donchian) trend systems are the best-documented technical rules in crypto. Recent practitioner-academic work reports net Sharpe above 1.5 for a top-20 Donchian ensemble. These are daily-frequency and long-biased as far as could be verified. No peer-reviewed 4H breakout study with costs was found.

### Cited Findings
- **Zarattini, Pagani & Barbon (SSRN 5209907, 2025).** Donchian ensemble, rotational top-20 portfolio, net Sharpe above 1.5 per the snippet. Details are unverified because the page returned 403. [SEARCH-SNIPPET] — [SSRN](https://papers.ssrn.com/sol3/Delivery.cfm/5209907.pdf?abstractid=5209907&mirid=1)
- **arXiv 2602.11708 (2026).** Adaptive trend following, 2022-2024 out-of-sample, net of fees, slippage and funding. Simple time-series momentum gets Sharpe of about 0.5-0.65. [SEARCH-SNIPPET] — [arXiv 2602.11708](https://arxiv.org/pdf/2602.11708)
- **arXiv 2607.19497 "The Science and Practice of Trend-Following Systems" (2026).** It appeared in search, but its content was not reviewed. — [arXiv 2607.19497](https://arxiv.org/pdf/2607.19497)

### Inferences
- Breakout rules at 4H would have higher turnover than at daily. Per Section 8, costs then consume a much larger share of the edge.

### Gaps
- No 4H-specific breakout paper was found. The short side of breakout systems in crypto is undocumented in the sources reviewed.

---

## 7. Signals documented for SHORTS specifically

### Takeaway
The most consistent short-side evidence is (a) new token listings, which tend to fall after listing, and (b) high carry or funding, which predicts crashes. Evidence for (a) is from media and industry analysts, not peer-reviewed work. Both carry squeeze risk.

### Cited Findings
- **New listings (2024 Binance listings, industry study).**
  - Average listing pump of about 87%. 98% of Binance-listed tokens later "dump", with about a 70% decline from listing price.
  - The sample is 389 tokens across six CEXs, so it is not Binance-only. Media study, not peer-reviewed. — [BitPinas](https://bitpinas.com/cryptocurrency/binance-token-listing-dump/); [Forklog](https://forklog.com/en/study-reveals-binance-token-listings-as-investor-traps/)
- **New listings (2024 analyst "Flow").** About 80% of 6-month-recent Binance listings fell below their first-day price, and a portfolio of them lost about 18%.
  - The analyst attributes this to high-FDV, VC-backed launches. Memecoins were exceptions. — [FXStreet](https://www.fxstreet.com/cryptocurrencies/news/binance-effect-fades-less-than-20-tokens-are-profitable-six-months-after-listing-202405201006)
- **Contested.** Binance disputes the allegations about its listing process, and The Block could not verify either side. — [The Block](https://www.theblock.co/post/374675/binance-claims-does-not-profit-token-listing-calls-allegations-false-defamatory)
- **High carry or funding.** It predicts future price crashes (BIS WP 1087). — [BIS](https://www.bis.org/publ/work1087.htm)
- **Same paper, opposite implication.** High carry also predicts liquidations of **short** futures positions (snippet). Shorting into high funding may first get squeezed. [SEARCH-SNIPPET] — [BIS PDF](https://www.bis.org/publ/work1087.pdf)

### Inferences
- Listing-decay shorts operate over weeks to months, not 4h-3d. Early-day squeezes, thin liquidity and high or volatile funding on new perps make the 4H-horizon short risky.
- Funding extremes are better as a **filter** (avoid adding longs into crowded-long funding) than as a standalone short trigger.

### Gaps
- No peer-reviewed short-side 4H study was found. Crowded-long (long/short ratio) evidence was not found. Net short returns after funding and borrow are unquantified.

---

## 8. Typical gross edge per trade at 4h-1d vs. round-trip costs of 0.1-0.5%

### Takeaway
Every directly measured short-horizon edge found is tiny relative to costs:
- 15-minute reversal: about 1.3 bp gross vs. 5 bp cost.
- Hourly ML on BTC: positive gross, negative net at 10 bp per trade unless trades are filtered hard.

At 4h-1d, the gross edge per trade must exceed roughly 10-50 bp to clear the stated cost range. The evidence found supports that only for slower trend or breakout rules and cost-filtered ML. No paper reports a verified per-trade 4H edge.

### Cited Findings
- **15-minute Binance reversal.** About 1.3 bp gross edge vs. a 5 bp round-trip, which does not clear costs. — [arXiv 2608.21888](https://arxiv.org/abs/2608.21888)
- **Hourly BTC-USDT ML at 10 bp per trade.**
  - Naive strategies fail net of costs. A cost-threshold filter restores profitability. The cost drag was 1.43-6.06 bp per hour (the latter from a snippet). — [arXiv 2606.00060](https://arxiv.org/abs/2606.00060)
- **Binance fee context.** A consumer guide reports that in September 2025 Binance announced 0% maker / 0.01% taker on 20+ "Tier 0" pairs. This is secondary; check Binance's official schedule. [SEARCH-SNIPPET] — [Motley Fool](https://www.fool.com/investing/stock-market/market-sectors/financials/cryptocurrency-stocks/transaction-fees/)
- **Cost-model example from 2022-2024 research.** 4 bp taker fee plus volume-scaled slippage plus 8h funding. — [arXiv 2602.11708](https://arxiv.org/pdf/2602.11708)
- **Spread vs. Sharpe for perp arbitrage on Binance.** Adding the spread cut Sharpe from 3.35 to 3.27 at the high fee tier. — [arXiv 2212.06888](https://arxiv.org/html/2212.06888v7)

### Inferences
- A system trading every 4H bar roughly 6 times a day at 10 bp round-trip pays about 60 bp per day. No documented signal comes near that.
- Holding periods of 1-3 days, a cost-aware no-trade band, and maker execution where possible are needed for any of these signals to have a chance of positive net returns.
- For perps, funding (often 1 bp per 8h, but much larger in extremes) is an additional holding cost for longs in bullish regimes, and income for shorts.
- Priority ranking for a 4H AI system, by evidence strength net of costs (inference):
  1. Slow trend or breakout regime (daily+) as a filter or direction bias.
  2. Order and taker imbalance at bar opens (2026 preprint, needs verification).
  3. Funding or carry extremes as a crowding and crash-risk feature.
  4. Volatility and liquidity seasonality for sizing and execution timing.
  5. Short-term reversal, only on liquid coins after taker-flow spikes, and likely cost-negative.
  6. Listing-decay shorts: slow horizon and high squeeze risk.

### Gaps
- No source gives a measured gross per-trade edge at exactly the 4h or 1d horizon for any signal on 2022-2026 Binance data. Measuring this on the project's own SHA-locked data (pre-registered, gross vs. net) is the only way to close the gap.
- Weekend and day-of-week return effects, funding-time return effects, Liu-Tsyvinski-Wu post-publication decay, and the AQR, Man, Kaiko, Glassnode and Coinbase Institutional practitioner reports were not covered in this session.
