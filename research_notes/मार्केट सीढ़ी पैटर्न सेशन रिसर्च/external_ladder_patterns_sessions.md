# External evidence: market "ladder" structure, chart/candlestick patterns, and crypto session effects

Research date: 2026-10-17. About 23 tool calls. Read-depth legend used below:
- [ABSTRACT] = only the abstract or publisher/repository page was read.
- [SECONDARY] = only a secondary summary was read (Quantpedia, CXO, a search-engine summary, a news piece). Numbers may be imprecise.
- [FULL] = full text read. No paper reached FULL in this session. SSRN, ScienceDirect, Aalto and Springer all returned 403 or a login redirect.
- [PREPRINT] = working paper, thesis or SSRN paper, not peer-reviewed.
- [PRACTITIONER] = not peer-reviewed vendor, blog or book material.

Overall caveat for the report writer: none of these papers was read in full. Effect sizes come from abstracts or secondary summaries. Do not present them as more precise than that.

## Q1. Market structure as a "ladder/staircase" (Dow theory HH/HL, swings, pullback depth, Fibonacci, Elliott)

### Takeaway
The only peer-reviewed support for the "staircase" view is historical and indirect. Brown, Goetzmann and Kumar (1998) found risk-adjusted value in Hamilton's Dow-theory timing over 1902–1929, and say frictions eroded it later. Fibonacci retracement levels and Elliott-wave counts have no credible peer-reviewed out-of-sample support. We found no crypto-specific peer-reviewed test of HH/HL swing structure, pullback depth or Fibonacci levels.

### Cited Findings
- **Brown, Goetzmann & Kumar (1998), *Journal of Finance* 53(4), "The Dow Theory: William Peter Hamilton's Track Record Re-Considered".** They re-tested the 255 Wall Street Journal editorials Hamilton wrote over 1902–1929, adjusting for risk. Cowles (1934) had found no forecasting skill. After risk adjustment, Hamilton's timing shows high Sharpe ratios and positive alphas. A summary reports he called short-term direction correctly about 60% of the time, with better accuracy in bear markets. A neural-network version of his rules, run over 1930–1997, beat buy-and-hold by about 4.4 percentage points a year. That figure is from a MarketWatch quote reproduced by NYU Stern, so it is not costed. The authors note that after 1929, trading frictions rule out large excess returns, especially since the 1970s. [ABSTRACT/SECONDARY] — [Yale page](https://viking.som.yale.edu/the-dow-theory-william-peter-hamiltons-track-record-re-considered); [NYU archive](https://archive.nyu.edu/handle/2451/26858); [NYU Stern news](https://www.stern.nyu.edu/experience-stern/news/prof-stephen-brown-s-research-dow-theory-featured)
  - OOS: partly. The neural-network extension is out-of-time. After costs: not established. Contested in the sense that it reverses Cowles (1934).
- **Fibonacci retracements (38.2%, 50%, 61.8%).** We found no peer-reviewed study that confirms clustering of turning points at these ratios.
  - Wikipedia notes the significance of the levels "could not be confirmed by examining the data". It also cites Arthur Merrill's *Filtered Waves*, which concluded no reliably standard retracement exists. [SECONDARY; this is tertiary-level evidence] — [Wikipedia](https://en.wikipedia.org/wiki/Fibonacci_retracement)
  - An HKUST student project on Vanguard ETFs found Fibonacci-retracement trading significantly underperformed passive investing. [PRACTITIONER/student, not peer-reviewed] — [HKUST PDF](https://cse.hkust.edu.hk/~rossiter/independent_studies_projects/fibonacci_trading/fibonacci_trading.pdf)
  - One web page claims that 17/63 support levels and 24/66 resistance levels "aligned" with Fibonacci ratios. It has no traceable author or paper, so it is unreliable. Do not cite it as evidence. — [mental-momentum page](https://research.mental-momentum.ai/r/efficacy-fibonacci-retracement-financial-yq7tpo/efficacy-fibonacci-retracement-financial-yq7tpo.md)
  - Crypto: searches returned only exchange and education pages (KuCoin, BingX, Bitfinex blog) that assert the 61.8% level is "most watched". None tests it. [PRACTITIONER] — [Bitfinex blog](https://blog.bitfinex.com/education/chart-decoder-series-fibonacci-retracements-the-mathematical-pattern-that-predicts-market-behaviour/)
- **Elliott wave.**
  - Zhalgasbek (2023), a Nazarbayev University capstone, found no statistically significant predictive power of Elliott patterns for daily FX rates. [PREPRINT/student] — [NU repository](https://nur.nu.edu.kz/items/ce5e8705-2615-4ffe-81a0-3b4aaf7189bb)
  - D'Angelo (2017) claims accurate USD/EUR forecasts over 2009–2015. This is one pair over one period, and it is unclear whether the wave counts were fixed ex ante. [ABSTRACT, weak] — [Unipegaso](https://www.unipegaso.iris.cineca.it/handle/20.500.12607/612)
  - The common critique is that wave labelling is subjective and allows post-hoc relabelling, which is a data-mining risk. This critique comes from secondary and vendor sources, not a peer-reviewed meta-study.

### Inferences
- "Ladder" structure (HH/HL) is close to trend-following and time-series momentum. Its value, if any, likely comes from that rather than from structural geometry. An in-house test should benchmark swing-structure rules against a simple momentum or moving-average rule. This mirrors Osler's finding for head-and-shoulders, where simpler rules dominated (see Q2).
- Fibonacci and Elliott claims should be treated as unproven until our own pre-registered test with a random-walk or shuffled null shows clustering above chance.

### Gaps
- We found no peer-reviewed study on crypto swing structure or pullback-depth distribution (for example, how deep BTC pullbacks typically are within an uptrend). This would need an in-house measurement.
- We did not locate a peer-reviewed Fibonacci clustering test with a proper null. Some likely exist in obscure journals but were not surfaced.

## Q2. Classic chart patterns and candlestick patterns: OOS and after-cost evidence

### Takeaway
In equities and FX, algorithmically detected patterns carry some statistical information: Lo-Mamaysky-Wang 2000, Savin et al. 2007, and Osler & Chang 1995 for FX head-and-shoulders. Stand-alone trading profits are weak or absent, and simpler rules dominate. Candlesticks fail out-of-sample on US large caps (Marshall-Young-Rose 2006). Crypto candlestick studies find some short-horizon signal that does not survive realistic costs. The only peer-reviewed crypto chart-pattern study uses 2011–2013 Mt.Gox data and does not apply costs.

### Cited Findings
**Chart patterns: equities and FX**
- **Lo, Mamaysky & Wang (2000), *Journal of Finance* 55(4): 1705–1765, "Foundations of Technical Analysis".**
  - Method: kernel-regression smoothing to detect 10 patterns automatically, including head-and-shoulders, double bottoms, triangles, rectangles and broadening formations.
  - Sample: many US stocks, 1962–1996.
  - Test: they compare conditional and unconditional distributions of daily returns, not trading profit. "Several technical indicators do provide incremental information and may have some practical value."
  - A CFA digest notes the effect was strongest for Nasdaq stocks, and that classic head-and-shoulders may "not be optimal".
  - Costs and profitability: not tested in the abstract.
  - [ABSTRACT] — [MIT page](https://web.mit.edu/~alo/www/Papers/techanal.html); [NBER w7613](https://www.nber.org/papers/w7613); [CFA digest](https://rpc.cfainstitute.org/-/media/documents/article/cfa-digest/2001/dig-v31-n1-811-pdf.pdf)
- **Chang & Osler (1995), Federal Reserve Bank of New York Staff Report No. 4: head-and-shoulders in FX.**
  - Sample: daily major currencies against USD, March 1973 to June 1994.
  - Method: an objective algorithm, with profits compared to 10,000 bootstrapped random-walk series.
  - The published follow-up, Chang & Osler (1999) "Methodical Madness" (*Economic Journal*), found the rule profitable for some currencies but "not efficient", because simpler momentum or moving-average rules dominate it.
  - Osler's separate study on US equities found head-and-shoulders trading unprofitable.
  - [ABSTRACT/SECONDARY, PREPRINT for 1995] — [EconPapers](https://econpapers.repec.org/RePEc:fip:fednsr:4); [FRASER](https://fraser.stlouisfed.org/title/research-papers-federal-reserve-bank-new-york-6570/evaluating-chart-based-technical-analysis-head--shoulder-pattern-foreign-exchange-markets-708165); [Brandeis, Methodical Madness](https://scholarworks.brandeis.edu/esploro/outputs/journalArticle/Methodical-Madness-Technical-Analysis-and-the/9924036864101921); [Traders.com interview](https://traders.com/Documentation/FEEDbk_docs/2001/06/Abstracts_new/Interview/Interview.html)
- **Savin, Weller & Zvingelis (2007), *Journal of Financial Econometrics* 5(2): 243–265.**
  - Method: Lo et al.'s algorithm plus practitioner filters.
  - Sample: S&P 500 and Russell 2000 stocks, 1990–1999.
  - Result: head-and-shoulders predicts excess returns, with risk-adjusted excess returns of about 5–7% a year when combined with the market portfolio. However, there is "little or no support for the profitability of a stand-alone trading strategy". The S&P 500 short strategy was unprofitable, and the Russell 2000 evidence was weak. Part of the effect is negative momentum.
  - Contested or extended: Chong & Poon (2014/2017) argue both algorithms ignore the pattern's position within the trend, and that filtering improves returns.
  - [ABSTRACT + working paper] — [IDEAS](https://ideas.repec.org/a/oup/jfinec/v5yi2p243-265.html); [working paper PDF](https://www.biz.uiowa.edu/faculty/gsavin/papers/HSrevision_paw_10%2019%2006.pdf); [CXO summary](https://www.cxoadvisory.com/technical-trading/testing-the-head-and-shoulders-pattern/); [Chong & Poon on IDEAS](https://ideas.repec.org/a/bpj/sndecm/v21y2017i5p18n1.html)
- **Bulkowski (*Encyclopedia of Chart Patterns*).** This is a practitioner book. Its pattern "success rates" were not verified in this session. Flag it as non-peer-reviewed, with no independent OOS or cost audit.
  - Similarly, the vendor altFINS self-reports about 82–84% "success" for head-and-shoulders, inverse head-and-shoulders and double bottom in crypto. "Success" there means the target was hit within one pattern length. These are not net returns and are unaudited. [PRACTITIONER] — [altFINS](https://altfins.com/knowledge-base/chart-patterns/)

**Chart patterns: crypto**
- **Rink, K. (2025), *Financial Innovation* 11, "The role of technical chart patterns in the early Bitcoin market: intraday evidence from the Mt.Gox transaction dataset".**
  - Sample: more than 1.4 million transactions from more than 45,000 traders, April 2011 to September 2013. Hourly signals for five major chart patterns. The abstract does not name the patterns.
  - Results: buy-signal periods coincide with abnormal volume up more than 53%. Trades during buy signals have significantly higher average returns than trades outside them.
  - Limits: the setting is an early, inefficient, unregulated exchange. Transaction costs or OOS tests were not visible in the abstract. Generalising to 2020s markets is questionable.
  - [ABSTRACT] — [IDEAS](https://ideas.repec.org/a/spr/fininn/v11y2025i1d10.1186_s40854-025-00763-2.html); [SpringerOpen](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-025-00763-2)
- We found no peer-reviewed crypto study with OOS, after-cost results for double tops, triangles, flags, wedges or broadening patterns. Search results were dominated by education and vendor pages.

**Candlestick patterns**
- **Marshall, Young & Rose (2006), "Candlestick technical trading strategies: Can they create value for investors?"** Published in the *Journal of Banking & Finance*; venue as recalled, not confirmed in this session because the snippet was truncated.
  - Sample: DJIA component stocks, 1992–2002. This is a genuine out-of-sample test, since candlesticks were developed on 1700s rice data.
  - Test: 28 signals, bootstrap tests, 10-day holding period.
  - Result: no evidence of predictive power. The authors say the strategies are not profitable for large US stocks, although they "cannot rule out" a complementary role.
  - Contested by follow-up: a 2014 data-snooping-adjusted study found the eight 3-day reversal patterns unprofitable with the Marshall-Young-Rose holding rule, but profitable with a different exit rule. Marshall et al. later found similar null results in Japan.
  - [SECONDARY] — [Massey thesis record](https://mro.massey.ac.nz/items/edc6c1cf-63d9-4c94-a13d-92ffe1a53481/full); [CXO "Candlesticks = Fiddlesticks"](https://www.cxoadvisory.com/technical-trading/candlesticks-fiddlesticks/); [IDEAS, 2014 follow-up](https://ideas.repec.org/p/sin/wpaper/14-a010.html)
- **Crypto candlesticks.**
  - (a) An *International Review of Economics & Finance* paper (2026), "Intraday price forecasts using candlestick patterns in cryptocurrency markets".
    - Sample: hourly data, 2018–2022, many coins and exchanges, 55 reversal patterns.
    - Result: some bullish and bearish patterns precede significant returns in the predicted direction.
    - Profitability details could not be read (403). [ABSTRACT via search summary] — [ScienceDirect](https://sciencedirect.com/science/article/pii/S1059056026002716)
  - (b) "Do Candlestick Patterns Work in Cryptocurrency Trading?" (ResearchGate, about 2021). With a 0.5% fee, none of the patterns is effective. [ABSTRACT, venue unverified] — [ResearchGate](https://www.researchgate.net/publication/355991813_Do_Candlestick_Patterns_Work_in_Cryptocurrency_Trading)
  - (c) A Charles University master's thesis (2025) tested 41 patterns with skew-adjusted t-tests and binomial tests. Eight showed some predictive potential, but none was profitable after a 1% fee. Some improvement appeared under particular trend conditions. [PREPRINT/thesis] — [CUNI PDF](https://dspace.cuni.cz/bitstream/handle/20.500.11956/197060/130412926.pdf?sequence=1&isAllowed=y)
  - (d) The forex analogue, MDPI *Mathematics* (2020), studied adaptive candlesticks on EUR/USD with a Monte Carlo test. It found no net positive returns after costs. [ABSTRACT] — [MDPI](https://www.mdpi.com/2227-7390/8/5/802)
  - (e) A secondary summary of a 2026 hourly BTC-USDT study (about 70,000 observations, 27-fold walk-forward) reports that ML looked positive before costs but simple high-turnover strategies failed at 10 bp cost. This comes only via the Coin Bureau summary; we could not identify the original paper. [SECONDARY, unverified] — [Coin Bureau](https://coinbureau.com/guides/crypto-candlestick-charts)

### Inferences
- The consistent pattern across markets is that patterns carry a small amount of conditional-distribution information but no robust stand-alone profit after costs. They are often dominated by simpler trend or momentum rules.
- For our 1D/4H crypto system, chart and candle patterns are at best candidate features to be tested against a shuffled control, not standalone strategies. High-turnover intraday candle rules are the most cost-fragile.

### Gaps
- We could not read the full texts of Lo et al. or Marshall et al. to give per-pattern effect sizes. The 2026 IREF crypto candlestick paper's profitability section was also unreadable.
- We found no peer-reviewed OOS, after-cost crypto study on triangles, flags, wedges or broadening patterns.

## Q3. Crypto trading-session effects (Asia/Europe/US, time-of-day, weekday/weekend, ETF/CME hours, funding times)

### Takeaway
Robust finding: volume, volatility and liquidity follow the global equity clock. They peak when major stock markets open, especially the US, and are lowest around 00:00–early morning UTC and on weekends. Directional return effects by hour or day exist in some samples but vary over time and are not persistent (Baur et al. 2019). After the January 2024 spot ETFs, activity is more anchored to New York hours and the 3–4pm ET fixing window. One 2026 SSRN paper says hour-of-day predicts volume and volatility but not return direction. Evidence on which session earns the return is contradictory and sample-dependent.

### Cited Findings
- **Eross, McGroarty, Urquhart & Wolfe (2019), *Research in International Business and Finance* 49: 71–81, "The intraday dynamics of Bitcoin".**
  - Sample: about four years of tick data from the leading exchange, in GMT, aggregated to 5-minute intervals.
  - Results:
    - Returns increased over time.
    - Volume builds through the day and declines from about 16:00 to midnight GMT, similar to FX.
    - Realised volatility is fairly flat but peaks at the openings of the three major stock markets.
    - Liquidity is highest at the major-exchange opens and thinnest in the early morning.
    - The paper supports the mixture-of-distributions hypothesis.
  - This is descriptive and in-sample. No trading test or costs.
  - [ABSTRACT] — [IDEAS](https://ideas.repec.org:443/a/eee/riibaf/v49y2019icp71-81.html); [Reading accepted manuscript](https://centaur.reading.ac.uk/81745/3/2.R%26R.Manuscript.pdf)
- **Baur, Cahill, Godfrey & Liu (2019), *Finance Research Letters* 31: 78–92, "Bitcoin time-of-day, day-of-week and month-of-year effects in returns and trading volume".**
  - Sample: more than 15 million observations from 7 exchanges.
  - Results:
    - Effects vary over time, with no consistent or persistent pattern, which the authors read as consistent with efficiency.
    - Weekend volume is lower, and there is a higher-Monday-return effect. Both are FX-like.
    - Activity rises during US stock-exchange hours and drops from midnight to early morning.
    - USD exchanges show stronger patterns than JPY or CNY exchanges.
    - They argue the Monday effect is driven by specific years.
  - [SECONDARY via Quantpedia] — [Quantpedia](https://quantpedia.com/are-there-any-simple-calendar-effects-in-bitcoin-market/)
- **Aharon & Qadan (2019), *Finance Research Letters* 31, "Bitcoin and the day-of-the-week effect".**
  - Sample: daily data, 2010–2017, OLS and GARCH.
  - Result: day-of-week effects in both returns and volatility. A later paper summarises it as Monday showing higher return and volatility.
  - Contested by:
    - Baur et al. (2019): Monday effect is year-specific.
    - Yaya (2024, *Journal of Social Research*): no significant return day-of-week effect, only possible Monday and Friday volatility effects.
    - Kinateder & Papavassiliou (UCD working paper): no weekday return effect, but significantly lower weekend risk and higher early-week volatility.
    - Caporale & Plastun: a "reverse Monday" with higher Monday returns.
    - A Quantpedia test of a Monday strategy found it mostly not different from random trading.
  - [ABSTRACT/SECONDARY] — [Haifa CRIS](https://cris.haifa.ac.il/en/publications/bitcoin-and-the-day-of-the-week-effect/); [Yaya](https://journals.ui.edu.ng/index.php/jsr/article/view/636); [UCD WP](https://researchrepository.ucd.ie/server/api/core/bitstreams/3fe12e0f-f1c4-4226-937e-b7fc034dfcd9/content); [Quantpedia DoW](https://quantpedia.com/?p=813)
- **Shen, Urquhart & Wang (2022), *Financial Review* 57(2): 319–344, "Bitcoin intraday time-series momentum".** DOI 10.1111/fire.12290.
  - Method: the first half-hour return predicts the last half-hour return, with the "day" defined in volume-based trading time because there is no open or close.
  - Results:
    - Predictability is strongest in the sessions with the highest volume or volatility.
    - There are economic gains in market timing and asset allocation, largest in BTC downturns.
    - The authors attribute the effect to liquidity provision, as in FX, rather than late-informed trading.
  - After-cost robustness not verified.
  - [ABSTRACT] — [Birmingham](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/); [Reading accepted version](https://reading-9.eprints-hosting.org/100181/3/21Sep2021Bitcoin%20Intraday%20Time-Series%20Momentum.R2.pdf)
- **ETF era (2024–2026).**
  - **Schmidt & Kraft, "Keeping New York's hours: Bitcoin's intraday clock after the spot ETFs".** SSRN 7384239; page returned 403, so this is from the search summary only.
    - Sample: Bitstamp 5-minute data, 2020–2026.
    - Result: since the January 2024 spot ETFs, intraday activity is anchored to the New York clock. Hour-of-day predicts volume and volatility, but not the direction of returns.
    - [PREPRINT, SECONDARY] — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7384239)
  - **Aalto University thesis, "Crypto never sleeps, but humans do. Do regional hours matter for Bitcoin returns?"** Page returned 403; this is from the search summary only.
    - Sample: BTC/USDT high-frequency data, 2017–2026.
    - Result: a significant overnight premium in the Asian pseudo-session over the full sample, and none for Europe or the US. A difference-in-differences test around the spot ETFs shows the US overnight premium rising and the Asian premium falling to insignificance.
    - [PREPRINT/thesis, SECONDARY] — [Aalto](https://aaltodoc.aalto.fi/items/e4962f5a-045a-4131-b329-cc27926f6c4f)
  - **SSRN 4779488, "Impact of US Bitcoin ETF Introduction on BTC and ETH Intraday Regime Seasonality".** Two months either side of the launch. Intraday seasonality and commonality in volatility and volume, strongest on weekdays. [PREPRINT, SECONDARY; 403] — [SSRN](https://papers.ssrn.com/abstract=4779488)
  - **Kaiko (industry research, 2024).**
    - After the ETFs, volume in the 3–4pm New York benchmark-fixing window rose. ETF NAV is set off this fixing, so creations and redemptions cluster there, and Kaiko warns this may raise intraday volatility.
    - A March 2024 Kaiko note says the hourly high-low range is larger in US hours than in Asian hours.
    - [PRACTITIONER] — [Kaiko](https://www.kaiko.com/resources/btc-etfs-impact-on-spot-market-structure); [InvestmentNews](https://investmentnews.com/alternatives/bitcoin-volatility-is-more-pronounced-in-us-trading-hours/251428)
  - **Media decompositions (anecdotal; short windows).**
    - A Velo-based three-month split reports APAC +13%, US +11.5% and Europe +6.5%.
    - A 13-session window (Sep 21 to Oct 7) shows BTC −3.24% during 9:30–16:00 ET and +6.07% outside those hours. The result is sensitive to the window definition.
    - Decrypt reports that the 2024–25 "sell after US open" pattern faded, while off-hours volatility rose. Article date unverified.
    - [PRACTITIONER/media] — [DL News](https://www.dlnews.com/articles/markets/how-to-trade-bitcoin-markets-like-a-pro-in-the-etf-era/); [TokenPost](https://www.tokenpost.com/news/investing/28079); [Decrypt](https://decrypt.co/363636/bitcoin-ethereum-metaverse-tokens-sink-further-after-holiday-crypto-rally)
- **CME gaps.** No peer-reviewed test was found. The "about 95% of gaps fill" claim comes from a TradingView post with no named study. CryptoSlate documents a February 2026 gap that stayed open. The gap is a by-product of CME's closed hours, not a causal force. [PRACTITIONER] — [CryptoSlate](https://cryptoslate.com/do-cme-gaps-always-have-to-fill-bitcoins-60k-flush-says-no/)
- **Funding-time effects.**
  - Binance funding settles at 00:00, 08:00 and 16:00 UTC. The rate is based on the premium averaged over the prior 8 hours, and is often clamped at 1 bp per 8 hours.
  - Some venues (Binance, Bybit, OKX) shorten the interval when the rate hits its cap, so pooled data can mix schedules.
  - We found no peer-reviewed empirical study of price behaviour around funding timestamps.
  - [PRACTITIONER docs + arXiv primer] — [Coin Metrics docs](https://docs.coinmetrics.io/market-data/market-data-overview/market-funding-rates); [arXiv 2212.06888, "Fundamentals of Perpetual Futures"](https://arxiv.org/pdf/2212.06888)

### Inferences
- For our bot, session information is most defensible as a volatility, volume and liquidity regime feature, for example for position sizing, stop width, execution timing or avoiding thin hours. It is weakest as a directional return predictor.
- Return-by-session claims flip across samples: an Asia premium before the ETFs and a US-hours role after, per the Aalto thesis, while media windows contradict each other. Any session-direction rule needs a pre-registered pre/post-January-2024 split and a shuffled-hour control.
- Our 1D system with a 00:00 UTC close sits at the volume trough between the US close and the Asia open. Daily candles may therefore embed the ETF-hours dynamics differently than 4H candles do. This needs in-house verification.

### Gaps
- None of the ETF-era papers (Schmidt & Kraft; the Aalto thesis; SSRN 4779488) could be opened. Their sample details and effect sizes are search-summary only.
- We found no peer-reviewed study on price effects around funding-settlement times or on CME-gap fill rates.
- The Baur et al. and Aharon & Qadan coefficients were not read.
