# Cross-Sectional Long-Short / Market-Neutral Portfolio Construction in Crypto (Daily/Weekly Focus)

(Notes are in English so numbers and paper titles stay exact. Each Takeaway has a one-line Hindi summary for the Hindi report writer. Research date: 2026-10-16. About 20 tool calls; several publisher pages, including ScienceDirect and Springer, were paywalled, so some numbers come from abstracts or working-paper versions. Each case is flagged.)

## Q1. What do the main academic crypto factor studies find: effect sizes, samples, rebalancing frequency, and whether results survive costs?

### Takeaway
The core papers (Liu-Tsyvinski-Wu; Dobrynskaya; Cakici-Zaremba et al.; CTREND) report very large gross weekly long-short spreads of about 2.5-4.7% per week. Three things hold across them: (a) size, volume and reversal effects live mostly in micro-cap or illiquid coins; (b) cross-sectional momentum works better in large coins at 1-3 week horizons; (c) daily reversal is a small-coin phenomenon, while the largest coins show daily momentum. After realistic costs, a large share of the gross edge disappears (about 60% in one ML study), and effects decay over time.
(Hindi: बड़े कॉइन्स में 1-3 हफ्ते का मोमेंटम काम करता है। डेली रिवर्सल सिर्फ छोटे/इलिक्विड कॉइन्स में होता है। लागत के बाद ~60% तक मुनाफा खत्म हो सकता है।)

### Cited Findings
**Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency" (NBER WP 25882, May 2019; Yale/Cowles. The published version is widely cited as Journal of Finance 2022. I confirmed the JF listing only via secondary sources, and one Alpha Architect page lists a different venue.)**
- Sample: 1,707 coins with market cap > $1M, start of 2014 to end of 2018. Weekly returns are built from daily closes, and all strategies are value-weighted quintile sorts rebalanced weekly — [NBER WP 25882 PDF](https://www.nber.org/papers/w25882.pdf)
- Size: going long the smallest and short the largest quintile earns about 3.4% per week by market cap (3.9% by end-of-week price, 4.1% by max weekly price), significant at 5%. The authors note this "does not take into account trading costs and the feasibility of short selling" — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf)
- Momentum (weekly rebalance), top minus bottom quintile: 2.7% per week for 1-week momentum, 3.3% for 2-week, 4.1% for 3-week, 2.5% for 4-week. The 3-week momentum alpha is 4.2% per week (t = 2.80) — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf); the same numbers are corroborated in [NBER system PDF](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf)
- Momentum works in LARGE coins and not in small ones. In a size-median double sort, below-median momentum earns 0.6% per week (insignificant) and above-median earns 4.2% per week (significant). This is the opposite of equities — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf)
- Dollar-volume strategy: about 3.2% per week. A volatility-of-volume strategy: about 3.0% per week. A crypto 3-factor model (CMKT, CSMB, CMOM) prices 9-10 significant strategies — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf)
- No transaction-cost-adjusted returns are reported. The authors' only feasibility test replaces the short quintile with a short in Bitcoin, and they say the results "virtually do not change" — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf)

**Dobrynskaya, "Cryptocurrency Momentum and Reversal" (Journal of Alternative Investments 2023, Vol. 26 No. 1; HSE)**
- Coins with market cap > $1M, 2014-2020. Ranking windows run from 1 week to 2 years and holding periods from 1 week to 3 months. The best result is 2-week sort, hold and rebalance at about 70% per year. Returns fall with longer windows, and reversal begins at about 4-6 weeks. She notes that weekly trading is costly and suggests 2-8 week rebalancing — [HSE news summary](https://spb.hse.ru/en/news/559533243.html); [HSE publication record](https://publications.hse.ru/view/811744977)

**Zaremba, Bilgin, Long, Mercik & Szczygielski, "Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets" (International Review of Financial Analysis vol. 78, 2021) — DAILY frequency**
- More than 3,600 coins with daily data. Previous-day return strongly predicts the cross-section: low-return coins outperform high-return coins (daily reversal). Other predictors do not explain it, and the authors attribute it to illiquidity. The handful of largest, most tradeable coins show daily MOMENTUM instead — [IDEAS/RePEc abstract](https://ideas.repec.org/a/eee/finana/v78y2021ics1057521921002349.html)
- A related summary says weekly reversal occurs in small and illiquid coins only, while large and liquid coins show weekly momentum (attributed to Zaremba et al. 2021) — [Fičura 2023, FFA WP summary](https://wp.ffu.vse.cz/artkey/wps-202301-0003_impact-of-size-and-volume-on-cryptocurrency-momentum-and-reversal.php)

**Bianchi, Babiak & Dickerson, "Trading volume and liquidity provision in cryptocurrency markets" (Journal of Banking & Finance vol. 142, 2022; Warwick/QMUL; also Riksbank WP 413)**
- USD pairs on several centralised exchanges, March 2017 to March 2022. Returns from short-term-reversal (liquidity provision) concentrate in low-activity pairs, which are smaller, more volatile and less liquid. The working-paper version says results survive linear transaction costs (I checked the abstract and WP only, not the full published text) — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jbfina/v142y2022ics0378426622001418.html); [Riksbank WP 413](https://www.riksbank.se/globalassets/media/rapporter/working-papers/2022/no.-413-trading-volume-and-liquidity-provision-in-cryptocurreny-markets.pdf)

**Fieberg, Liedtke & Zaremba, "Cryptocurrency anomalies and economic constraints" (International Review of Financial Analysis vol. 94, 2024)**
- Size and volume anomalies come from economically negligible micro-caps. Momentum persists in larger coins, but it has "substantial trading costs" and its alphas come largely from SHORT positions. Most abnormal returns occur in bull markets and fade over time. The authors advise focusing on long positions and accounting for costs — [IDEAS/RePEc abstract](https://ideas.repec.org/a/eee/finana/v94y2024ics1057521924001509.html). The net-return tables were not accessible to me (ScienceDirect paywall).

**Cakici, Shahzad, Będowska-Sójka & Zaremba, "Machine learning and the cross-section of cryptocurrency returns" (IRFA 2024; WP version of 6 Dec 2022 read in full; Fordham / Montpellier BS / Poznań)**
- More than 500 major coins across 250 exchanges, 2017-2022, 34 characteristics and 10 ML models, with weekly rebalancing as the baseline. The value-weighted forecast-combination long-short earns 4.72% per week at an annualized Sharpe of 5.37. Daily-forecast strategies earn lower (still significant) returns than weekly or bi-weekly ones — [AFFI 2023 WP PDF](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- The top predictors are simple price-based features: idiosyncratic volatility, CAPM alpha, max daily return, nominal price, VaR, and distance to the 90-day high. Grouped by category, past returns, volatility and liquidity matter most — [same WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Alphas fell by about 30% in the second half of the sample (Apr 2020 to Jul 2022) — [same WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Costs: weekly long-short turnover is 78.6-110.8% (COMB 83.9%), and breakeven costs are 133-281 bp. With a fixed 30 bp (long) / 40 bp (short) one-way cost, net returns are 1.66-4.13% per week. With variable costs (Corwin-Schultz / Abdi-Ranaldo spread plus 10 bp), strategies lose about 60% of gross profit on average, and 2 of 10 (PLS, SVM) become insignificant — [same WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)

**CTREND: Fieberg, Liedtke, Poddig, Walker & Zaremba, "A Trend Factor for the Cross Section of Cryptocurrency Returns" (JFQA, 2024/25)**
- Combines price and volume signals across horizons. Value-weighted, weekly rebalanced. The extreme-quintile spread is 3.87% per week with a long-short Sharpe of 1.94, and it subsumes the momentum effect (the figures come from a search snippet of the Cambridge PDF and were not checked in the full text; single source) — [Cambridge/JFQA PDF](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/4C1509ACBA33D5DCAF0AC24379148178/S0022109024000747a.pdf/trend_factor_for_the_cross_section_of_cryptocurrency_returns.pdf); [JFQA listing](https://jfqa.org/2024/page/4)

**Factor momentum and factor zoo (Zaremba group)**
- Fieberg, Liedtke, Metko & Zaremba, "Cryptocurrency Factor Momentum" (Quantitative Finance 23(12), 2023): 34 anomalies, more than 3,900 coins, 2014-2022. Past-winner factors beat past-loser factors, and the effect traces back to price momentum — [open.icm.edu.pl](https://open.icm.edu.pl/items/d9f44e22-0614-4db8-8585-6dcba8906bb5); [T&F](https://www.tandfonline.com/doi/abs/10.1080/14697688.2023.2269999)
- Mercik, Zaremba & Demir, "Crypto factor zoo": 36 predictors are replicated, 2-3 factors absorb all significant alphas, and liquidity variables dominate (abstract-level only; the PDF returned 403) — [open.icm.edu.pl](https://open.icm.edu.pl/bitstreams/21636cf6-61df-4fb5-9ae4-4195d592cd26/download)

**Contrary evidence**
- Grobys & Sapkota, "Cryptocurrencies and momentum" (Economics Letters 180, 2019; Univ. of Vaasa): 143 coins, 2014-2018, "do not indicate any evidence of significant momentum payoffs", including for the top-30 by market cap. Its formation horizon is, I believe, MONTHLY (not verified) — [IDEAS](https://ideas.repec.org/a/eee/ecolet/v180y2019icp6-10.html); [Vaasa repository](https://osuva.uwasa.fi/items/99fceb0a-aaaa-4df2-aed1-09e6232a9df3)
- A study with realistic assumptions (AUT / Auckland working paper) finds strong time-series momentum but WEAK cross-sectional momentum. Its cross-sectional momentum max drawdown is 55.0%, losers often rebound sharply, and many "significant" portfolios become insignificant once costs and daily price moves are included — [AUT ACFR PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)

### Inferences
- In a universe of about 20 large-cap Binance coins, the literature points to SHORT-HORIZON MOMENTUM (1-3 weeks) and, at the daily horizon, daily momentum rather than reversal, because these are the "largest, most tradeable" coins. A 1-day reversal feature is likely to be weak or wrong-signed in this universe.
- Every headline number above (2.5-4.7% per week) is gross, value-weighted, and drawn from universes of hundreds to thousands of coins, mostly 2014-2022. In a 20-coin universe the spreads should be much smaller. The 30% alpha decay and the bull-market dependence suggest post-2022 performance is lower again.
- Weekly or bi-weekly rebalancing beats daily rebalancing after costs in both the ML study and Dobrynskaya. A daily-ranked system may gain by holding positions longer (for example, rebalancing only when the rank changes a lot) rather than fully re-forming every day.

### Gaps
- No peer-reviewed study I found tests a ~20-coin, large-cap-only, DAILY-rebalanced long-short net of Binance-level costs.
- Exact Journal of Finance 2022 publication details for Liu-Tsyvinski-Wu are confirmed only via secondary listings, and published-version numbers may differ from the 2019 NBER WP.
- Liu & Tsyvinski, "Risks and Returns of Cryptocurrency" (RFS 2021), and Borri & Shakhnov were not retrieved in this pass. No numbers are given for them.
- Jia et al. and the Grobys 2025 follow-up ("Cryptocurrency momentum has (not) its moments", FMPM) were not checked.

## Q2. Long-short construction choices: dollar-neutral vs beta-neutral, equal-weight vs volatility-weighted legs, names per leg, sector/factor neutralization. Which reduces drawdowns?

### Takeaway
Direct crypto evidence on construction choices is thin. Three findings stand out: (1) Liu-Tsyvinski-Wu show that a short leg made of BTC gives virtually the same results as shorting the bottom quintile; (2) beta hedging works poorly in crypto because betas are hard to forecast, and only BTC hedges reduce variance meaningfully; (3) ML results hold under both equal- and value-weighting. Drawdowns of 30-55% happen even in "market-neutral" academic long-short books.
(Hindi: बीटा-हेजिंग क्रिप्टो में कमजोर है। BTC को शॉर्ट लेग बनाने से नतीजे लगभग वैसे ही रहे। मार्केट-न्यूट्रल किताब में भी 30-55% ड्रॉडाउन आए।)

### Cited Findings
- Liu-Tsyvinski-Wu replace each strategy's short quintile with a short in Bitcoin, and "the results virtually do not change". They also report a hedging test in which the squared weekly Sharpe ratio rises from 0.057 (unhedged) to 0.076 when the strategy is hedged against unpriced factor components — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf)
- Momentum long-short strategies have some exposure to the coin market (R² ranges from about 0% for 1-week momentum to 6.8% for the max-day-price strategy against CMKT). So a dollar-neutral book is not automatically market-neutral — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf)
- "Crypto market betas: the limits of predictability and hedging" (Financial Innovation, 2025; Springer, paywalled, so details come from a search snippet): beta-hedged, market-neutral crypto portfolios are "largely inefficient" and reduce variance only for a small subset, mainly Bitcoin. The best beta-forecast R² is about 20%, against 58-60% for large US stocks. A naive hedge gives about a 17% variance reduction, and only for BTC — [Financial Innovation article](https://link.springer.com/article/10.1186/s40854-025-00777-w); [ResearchGate copy](https://www.researchgate.net/publication/391737271_Crypto_market_betas_the_limits_of_predictability_and_hedging)
- ML long-short alphas are similar under equal weighting (3-factor alphas 1.86-4.28% per week) and value weighting (2.11-4.73% per week). Value-weighted portfolios cap the weight of the largest coins — [Cakici et al. WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Tail risk in academic crypto long-short books: maximum weekly losses are often above 20% (SVM 33.43% in 7 days), and max drawdowns are usually 30-40% (SVM 58.83%) — [Cakici et al. WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Cross-sectional momentum max drawdown is 55.0%, which the authors attribute partly to high correlation among coins — [AUT ACFR PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)
- In the 2022 crash, BTC, ETH, BNB, ADA and XRP all entered deep drawdowns almost simultaneously, which limits diversification inside crypto (secondary, from a search snippet) — [arXiv sentiment-aware MV paper](https://arxiv.org/pdf/2508.16378)
- Equity background, practitioner view: in 2022, beta-neutral long/short books with unhedged style tilts had material drawdowns driven by residual factor exposure — [Resonanz Capital](https://resonanzcapital.com/insights/what-the-hedge-leaves-behind)
- Background: Liu-Tsyvinski-Wu use quintiles, and some appendix results use terciles. Results are robust to terciles per the authors, but I found no crypto study that systematically varies names per leg (for example 3 vs 5 vs 10) — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf)

### Inferences
- For a top-5 / bottom-5 book in a ~20-coin universe, dollar neutrality leaves a beta mismatch whenever the shorted coins have higher beta than the longs. In a crash (shorts fall more) this helps; in an alt rally it hurts. Because rolling betas forecast poorly (R² about 20%), beta-neutral weights should be shrunk heavily toward 1, or estimated over long windows, rather than trusted precisely.
- An alternative supported by Liu-Tsyvinski-Wu's robustness test: short BTC (or a BTC/ETH basket) instead of the bottom-5 alts when the short-leg signal is weak. This removes idiosyncratic short-squeeze risk while keeping most of the market hedge.
- Inverse-volatility weighting of legs is a standard practitioner choice. I found no crypto paper that tests it against equal weighting for drawdown reduction, so it should be treated as a hypothesis to pre-register.

### Gaps
- No crypto-specific peer-reviewed comparison of dollar-neutral vs beta-neutral vs vol-weighted legs with drawdown statistics was found.
- No crypto evidence on sector neutrality (L1 / DeFi / meme buckets) was found.
- No 2022-specific drawdown numbers for academic crypto cross-sectional long-short factors were found. CTREND and the ML papers end in 2022, but I did not see year-by-year tables.

## Q3. How does the short leg perform? Is the alpha in the long or short leg? Small/illiquid and delisting/survivorship effects?

### Takeaway
In the academic crypto literature the alpha is mostly in the SHORT leg, and that short leg is mostly SMALL, ILLIQUID coins that are hard or impossible to short. Among large, shortable coins, the short-leg edge shrinks a lot. This matches the system's observation of a weak short leg (+0.29% per trade, payoff 0.81). One source claims the opposite (long-leg alpha), but the full working paper I read says short leg, so that claim is unverified.
(Hindi: रिसर्च में अल्फा ज़्यादातर शॉर्ट लेग में है, लेकिन वह छोटे/इलिक्विड कॉइन्स से आता है जिन्हें शॉर्ट करना मुश्किल है। बड़े कॉइन्स में शॉर्ट लेग कमजोर होना अपेक्षित है।)

### Cited Findings
- ML strategies: "alphas predominantly come from the short legs". For value-weighted portfolios, top-quintile mean weekly returns are only 0.14% (PLS) to 1.00% (NN1), while bottom-quintile returns are -2.05% (PLS) to -3.84% (COMB). The return pattern is "L-shaped" — [Cakici et al. WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- The ML short leg is made of small coins. The average market cap in the bottom quintile is about $100-600M, against $3-9B in the top quintile. The bottom quintile holds only 0.8-9.1% of total market cap, and under 1% for almost half the strategies. The authors call large shorts in tiny coins of "questionable" feasibility because of lending fees, deposit requirements and borrow availability — [Cakici et al. WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Alphas in the tercile with the highest limits to arbitrage (high idiosyncratic volatility, illiquidity, bid-ask spread) are about 3 times those in the easiest-to-trade tercile — [Cakici et al. WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Momentum in larger coins "extracts alphas largely from short positions", carries substantial trading costs, and works mostly in bull markets. The authors recommend focusing on LONG positions — [Fieberg, Liedtke & Zaremba 2024, IRFA abstract](https://ideas.repec.org/a/eee/finana/v94y2024ics1057521924001509.html)
- In anomaly long-short strategies, 13 of 14 anomalies earn higher returns in the low-liquidity group — [Liquidity in the cryptocurrency market and commonalities across anomalies, IRFA 2022 (abstract snippet)](https://www.sciencedirect.com/science/article/abs/pii/S1057521922000679)
- CONFLICT: a search snippet for the published IRFA version of the ML paper said abnormal returns "originate from the long leg", "contrary to the stock market". The Dec-2022 WP full text I read says the opposite (short legs). This is unresolved. The snippet may be a summarizer error or a revision in the published version — [ScienceDirect listing (paywalled)](https://www.sciencedirect.com/science/article/abs/pii/S1057521924001765) vs [WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Losers often rebound sharply and inflict large losses on cross-sectional momentum short legs — [AUT ACFR PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)
- Survivorship and outlier handling: Liu-Tsyvinski-Wu use all coins with market cap > $1M (from CoinMarketCap, including dead coins in the sample period) and winsorize non-return variables at 1/99% — [NBER WP 25882](https://www.nber.org/papers/w25882.pdf). The ML paper removes weekly returns below -99.9% or above 200% as data errors — [Cakici et al. WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)

### Inferences
- The system's weak short leg (+0.29% per trade, payoff 0.81) is what the literature predicts for a universe of about 20 large caps. The short-side mispricing that academic papers harvest sits in coins outside this universe. This is a structural limit, not necessarily a model bug.
- Practical options suggested by the evidence (to pre-register and test, not proven): (a) shrink the short leg's gross exposure, for example long 1.0 / short 0.5; (b) replace the alt short basket with BTC (or BTC+ETH) as a beta hedge, as in Liu-Tsyvinski-Wu; (c) short only when the model's bottom-rank conviction is extreme, rather than always shorting 5 names; (d) watch squeeze risk from losers' rebounds, which hits a payoff ratio of 0.81 hardest.
- Survivorship in our own data: a Binance-listed universe selected today excludes coins that were delisted. The literature's short-leg alpha partly comes from coins that collapse or get delisted. Our backtest's short leg may therefore look WORSE than an unbiased one, while the long leg may look better (survivors). The prior memory note on the survivorship check is relevant here.

### Gaps
- No study found that reports short-leg returns specifically for a top-20 large-cap universe.
- No quantitative study found of crypto delisting returns (for example, the average return in the final month before a Binance delisting).

## Q4. Realistic costs: spot taker fees, perp fees, funding paid by shorts, slippage for small caps, capacity

### Takeaway
At Binance base tier the fees are about 0.10% spot (maker/taker), and USDⓈ-M perps are about 0.02% maker / 0.05% taker (some guides say 0.04% taker). Funding is positive most of the time with a 0.01% per 8h baseline, so shorts in perps usually RECEIVE funding, but alt shorts can pay heavily when funding turns negative in sell-offs. Academic net-return studies use 30-40 bp one-way all-in costs, and spread-based costs remove about 60% of gross weekly ML alpha.
(Hindi: Binance स्पॉट ~0.10%, फ्यूचर्स ~0.02%/0.05%। आमतौर पर फंडिंग पॉज़िटिव रहती है तो शॉर्ट को फंडिंग मिलती है। रिसर्च में लागत के बाद ~60% अल्फा खत्म हुआ।)

### Cited Findings
- Binance spot VIP 0 is 0.1% maker and taker. Binance's own support article uses Regular User futures fees of 0.02% maker / 0.05% taker in its example. Some third-party guides list 0.04% taker. BNB payment gives a 10% discount on USDⓈ-M futures fees. Fee schedules change, so the official page should be checked — [Binance support article](https://www.binance.com/es/support/articles/360033544231); [QuantConnect fee models](https://quantconnect.com/docs/v2/writing-algorithms/reality-modeling/transaction-fees/supported-models)
- Funding mechanics: Binance funding combines the premium index with a fixed interest component and settles at 00:00, 08:00 and 16:00 UTC — [Maverick Quant](https://maverickquant.substack.com/p/perpetual-futures). The fixed interest floor means longs often pay shorts even at a slight discount, which is why funding is usually small and positive — [BitMEX Q3-2025 derivatives report](https://www.bitmex.com/blog/2025q3-derivatives-report)
- 0.01% per 8h (about 10.95% per year) is the typical "neutral" rate — [TradingView script description](https://in.tradingview.com/scripts/perpetuals/). The claims that funding is positive more than 92% of the time on major platforms and that Binance BTC sits at the 0.01% clamp about 31% of the time are UNVERIFIED dashboard figures (single source) — [Spark funding comparison](https://www.spark.money/tools/funding-rate-comparison)
- Academic cost assumptions: a fixed 30 bp (long) / 40 bp (short) one-way fee, taken from Bianchi et al. (2022) as "fairly conservative ... for a market maker", or a variable cost equal to the estimated spread plus 10 bp. Breakeven costs for weekly ML strategies are 133-281 bp per unit of turnover — [Cakici et al. WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Capacity: the short legs that carry the alpha cover under 1% of crypto market cap for about half of ML strategies, so capacity is a binding limit — [Cakici et al. WP](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F)
- Daily rebalancing costs more than weekly: Dobrynskaya recommends 2-8 week rebalancing because of costs — [HSE summary](https://spb.hse.ru/en/news/559533243.html)

### Inferences
- Rough round-trip cost for our structure at base tier with taker orders: long spot at about 0.10% x 2 = 0.20% plus slippage; short perp at about 0.05% x 2 = 0.10% plus slippage. A daily full re-formation therefore costs about 0.3% or more per leg-pair round trip. Against a short-leg edge of +0.29% per trade, the short leg's net edge may be near zero when turnover is high. This should be checked against the system's actual cost model.
- Funding is usually a tailwind for perp shorts (shorts receive about 0.01% per 8h, or 0.03% per day, at baseline). But the bottom-ranked alts are the ones most likely to have negative funding during sell-offs, and the short then pays. Funding should be logged per trade, and the funding rate could be tried as a feature or filter.

### Gaps
- No peer-reviewed estimate was found of average Binance alt-perp funding conditional on being a bottom-ranked coin.
- No Kaiko or Amberdata market-depth or slippage numbers were retrieved for top-20 coins (not searched successfully in this pass).
- The current exact Binance USDⓈ-M taker fee (0.04% vs 0.05%) needs checking on the official fee page.

## Q5. Practitioner research from established firms (AQR, Man/AHL, Two Sigma, Coinbase, Kaiko, Amberdata, Glassnode, CF Benchmarks, Fidelity Digital Assets, 21Shares) on market-neutral crypto and 2022 drawdowns

### Takeaway
I found NO public research from the named firms that backtests cross-sectional crypto long-short or market-neutral strategies with drawdown figures. AQR's relevant public work (factor momentum, trend) covers traditional assets. The only 2022 market-neutral evidence I found is single-fund anecdotes, which are not usable as benchmarks.
(Hindi: नामित संस्थानों का कोई सार्वजनिक क्रिप्टो लॉन्ग-शॉर्ट बैकटेस्ट नहीं मिला। 2022 के लिए सिर्फ इक्का-दुक्का फंड के उदाहरण हैं।)

### Cited Findings
- AQR's "Factor Momentum Everywhere" and "Trends Everywhere" are traditional-asset studies, not crypto cross-sectional work — [AQR Factor Momentum Everywhere](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/Factor-Momentum-Everywhere-JPM-Quant-19.pdf?sc_lang=en); [AQR Trends Everywhere](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-Trends-Everywhere_JOIM.pdf?sc_lang=en)
- Pythagoras' market-neutral arbitrage fund gained 8.8% in 2022 despite a 10% exposure to FTX (it recovered about 7% and hedged by shorting FTT). AUM roughly halved to under $40M. This is an arbitrage fund, not cross-sectional factor investing — [Business Standard / Bloomberg](https://www.business-standard.com/amp/article/markets/how-two-pythagoras-crypto-hedge-funds-dodged-the-market-collapse-122120400839_1.html)
- Contrast: Multicoin Capital's hedge fund (directional, not market-neutral) lost 91.4% in 2022 — [CoinDesk](https://coindesk-coindesk-prod.cdn.arcpublishing.com/business/2023/03/04/multicoin-capitals-hedge-fund-lost-914-last-year-investor-letter-reveals/)
- The number of crypto market-neutral strategies rose 57% in 2021 and 23% in 2022 (Galaxy VisionTrack whitepaper, via a search snippet) — [Galaxy VisionTrack 2023 whitepaper](https://glxy.galaxy.com/hubfs/VisionTrack/GLXY_2023_Whitepaper_VisionTrack.pdf)
- A 2025 industry report says market-neutral crypto funds were the main group with meaningful gains in a difficult 2025, while directional funds struggled — [InvestmentNews](https://www.investmentnews.com/alternatives/crypto-chaos-jolts-hedge-funds-in-worst-year-since-2022-crash/263643)
- One fund (ANB Investments) reports +36% while BTC lost about 70% (Apr 2021 to Apr 2022). It describes a quant delta-neutral approach that can also tilt net long or short. This is self-reported and not a pure beta-hedged book — [The Hedge Fund Journal](https://thehedgefundjournal.com/anb-investments-quantitative-delta-neutral-trading/)

### Inferences
- Since no institutional public benchmark exists, our own pre-registered backtest plus the academic papers above are the only defensible yardsticks. Any claim that "market-neutral crypto has low drawdowns" should not be stated without our own evidence. Academic cross-sectional long-shorts show 30-55% max drawdowns.

### Gaps
- Coinbase Institutional, Kaiko, Amberdata, Glassnode, CF Benchmarks, Fidelity Digital Assets, 21Shares, Man/AHL and Two Sigma: no market-neutral cross-sectional crypto research was found in this pass. Their research pages may contain relevant pieces (for example, Kaiko liquidity/slippage reports), but none were retrieved or verified.
- No crypto market-neutral hedge fund INDEX return or drawdown for 2022 was found.

---
### Summary of direct relevance to our system (~20 large-cap Binance coins, daily GBM ranks, long top-5 spot / short bottom-5 perps)
1. Large-cap universe: expect momentum (1-3 week, and daily) rather than reversal. Check that the model's features or signs are consistent with this — [Zaremba et al. 2021](https://ideas.repec.org/a/eee/finana/v78y2021ics1057521921002349.html); [Liu-Tsyvinski-Wu](https://www.nber.org/papers/w25882.pdf)
2. A weak short leg is the expected outcome, because the literature's short alpha lives in micro-caps. Candidates to pre-register: a smaller short leg, a BTC-hedge short, or conviction-gated shorts — [Cakici et al.](https://affi2023.eventsadmin.com/Papers/ViewContribution?cid=8390&h=A0CBBA4C296557EB2205D3ECCD9DBD7F); [Fieberg et al. 2024](https://ideas.repec.org/a/eee/finana/v94y2024ics1057521924001509.html)
3. Weekly or bi-weekly holding beats daily re-formation after costs. Consider rank hysteresis or a longer hold.
4. Precise beta-neutral weighting is not reliable in crypto (beta R² about 20%), so shrink heavily — [Financial Innovation 2025](https://link.springer.com/article/10.1186/s40854-025-00777-w)
5. Expect 30-55% drawdowns even in long-short books, and edges that decay over time (about -30%) and concentrate in bull markets.
