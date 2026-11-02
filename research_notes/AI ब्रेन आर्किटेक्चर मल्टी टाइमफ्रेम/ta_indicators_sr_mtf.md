# Technical Analysis in Crypto: OOS / After-Cost Evidence (Indicators, S/R, Candlesticks, Volume, Multi-Timeframe, Data-Snooping, ML Combination)

Method note: 15 searches/fetches, run 2026-10-17. Most papers were read from **abstracts, repository pages, or search snippets only**. Full texts were blocked (Springer login, Hull/Vaasa repositories returned 403 or bot-walls). Each finding says where it came from. Numbers that only appeared in secondary or press summaries are marked as such.

## Q1. Crypto TA rule papers: what survives data-snooping corrections and costs, and what happens after 2020?

### Takeaway
The pre-2019 crypto TA literature finds significant, cost-robust profitability, mainly for MA / variable-length MA (VMA) and trading-range breakout (TRB, i.e. Donchian-style) rules, some of it surviving data-snooping corrections. Three findings cut against this: Bitcoin's own out-of-sample predictability disappears in Hudson & Urquhart; intraday profitability "declines over time"; and a 2022–2023 BTC/ETH USDT study finds **no** profitable rules after snooping adjustment. The edge is regime- and period-dependent and decaying, not stable.

### Cited Findings
- **Hudson & Urquhart, "Technical trading and cryptocurrencies"** (Annals of Operations Research vol. 297, pp. 191–220; online 2019, issue 2021):
  - Tested nearly 15,000 technical rules on two Bitcoin markets and three other cryptocurrencies.
  - Found "significant predictability and profitability for each class of technical trading rule in each cryptocurrency."
  - Breakeven transaction costs were "substantially higher than those typically found" in crypto.
  - Results held after multiple-hypothesis (data-snooping) procedures.
  - Rules gave better risk-adjusted returns than buy-and-hold.
  - **Caveat from the working-paper version:** "no predictability for Bitcoin in the out-of-sample period," while predictability remained in the other coins.
  - Source is abstract/snippet only; the full text was not accessible. — [Reading repository](https://reading-clone.eprints-hosting.org/85715); [Springer DOI page](https://link.springer.com/article/10.1007/s10479-019-03357-1); [Hull working paper](https://hull-repository.worktribe.com/OutputFile/2639834)
- **Corbet, Eraslan, Lucey & Sensoy (2019), Finance Research Letters 31:32–37:**
  - Tested MA-oscillator and trading-range-breakout (support/resistance) rules on **high-frequency** Bitcoin data.
  - Found "strong support for the moving average strategies." The VMA rule performed best, and its buy signals earned more than its sell signals.
  - Source is abstract only. I did not verify the sample period or the cost treatment. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finlet/v31y2019icp32-37.html); [DCU repository](https://doras.dcu.ie/25053)
- **Gerritsen, Bouri, Ramezanifar & Roubaud (2020), FRL 34:101263:**
  - Tested 7 trend-following indicators on daily BTC. The abstract gives the sample as July 2010 – Jan 2019; a secondary summary says 3,084 daily observations ending Dec 2018, so the exact window is unconfirmed.
  - **Trading range breakout** was the main source of predictive power. It beat buy-and-hold on the Sharpe ratio, with significance from bootstrapping.
  - The advantage was strongest in strongly trending markets. Sub-periods broadly confirmed the result. — [Utrecht research portal](https://research-portal.uu.nl/en/publications/the-profitability-of-technical-trading-rules-in-the-bitcoin-marke/); [IDEAS](https://ideas.repec.org/a/eee/finlet/v34y2020ics1544612319303770.html)
- **Detzel, Liu, Strauss, Zhou & Zhu (2021), Financial Management 50(1):107–137:**
  - Builds an equilibrium model in which TA arises from rational learning when fundamentals are hard to value.
  - **Ratios of price to its moving average forecast daily BTC returns in- and out-of-sample.**
  - Strategies built on these ratios earn economically significant alpha and Sharpe-ratio gains versus buy-and-hold.
  - Source is abstract only. — [IDEAS](https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html); [WUSTL profile](https://profiles.wustl.edu/en/publications/learning-and-predictability-via-technical-analysis-evidence-from-/)
  - **Contested:** this partly conflicts with Hudson & Urquhart's "no BTC OOS predictability" (see above).
- **Grobys, Ahmed & Sapkota (2020), FRL 35:**
  - Daily data on eleven cryptocurrencies. Snippet: the evidence suggests crypto markets are inefficient, i.e. the VMA rules show some profitability.
  - I could not open the PDF (bot-wall), so the rule-level results, the cost results, and the Bitcoin vs. non-Bitcoin split are **unverified**. — [IDEAS](https://ideas.repec.org/a/eee/finlet/v35y2020ics1544612320300829.html); [Vaasa repository PDF (blocked)](https://osuva.uwasa.fi/bitstream/10024/11192/2/Osuva_%20Grobys_Ahmed_Sapkota_2020.pdf)
- A study of privacy coins found that simple technical rules **do not** beat buy-and-hold across the whole set. This is a secondary snippet; the paper identity was not confirmed. — [Bilkent repository summary context](https://repository.bilkent.edu.tr/items/dc8e15f8-5083-44db-8f69-5bb278a8d093)
- **Post-2020: Li, Wang, Wang & Yang (2023), Journal of Accounting and Finance:**
  - Tested 200+ technical strategies on BTC/USDT and ETH/USDT using **daily and hourly** data, 2022–2023. In-sample ran to Jan 2023, out-of-sample after that.
  - Found "a lack of profitable technical trading strategies in both the analysis sample and prediction sample periods, even after rigorous adjustments for data snooping."
  - Caveat: the window is short and unusual (a bear market followed by recovery), and the journal is low-tier. — [Article Gateway](https://articlegateway.com/index.php/JAF/article/view/6453)
- **Intraday decay (Bakker, 2017, Erasmus MSc thesis, not peer-reviewed):**
  - 3,312 intraday rules on **5-minute BTC/USD**, Jan 2013 – Jul 2017.
  - Many rules stayed significantly profitable after data-snooping adjustment and transaction costs.
  - However, "profitability is highly unstable and declines over time." — [Erasmus thesis page](https://thesis.eur.nl/pub/41546/); [PDF](https://thesis.eur.nl/pub/41546/Bakker.pdf)

### Inferences
- Rule families that recur as winners in early crypto (2010–2019) are long-horizon MA / price-to-MA ratio, VMA, and range breakout (Donchian/TRB). Oscillator-type rules (RSI, MACD) rarely appear as headline survivors in the abstracts I saw. This is consistent with crypto TA "working" mostly as a **trend/time-series-momentum proxy**.
- Evidence weakens as the sample moves later. Bitcoin is the most liquid and most arbitraged market, and it loses OOS predictability first (Hudson & Urquhart). This matches the adaptive-markets pattern seen in FX (Q6).
- Any claim for this project should be tested on post-2020 data with a snooping-robust test. Results before 2019 should not be treated as evidence of a current edge.

### Gaps
- I found no paper that separately tests RSI, Bollinger Bands, ADX or ATR in crypto OOS with data-snooping control and costs. The abstracts lump them into "rule classes" or do not mention them.
- I could not get breakeven-cost figures (in basis points) for Hudson & Urquhart or Corbet et al. without the full text.
- Ahmed et al. (other papers) were not retrieved individually.

## Q2. Support/resistance, round numbers, liquidity zones

### Takeaway
In FX, published S/R levels have modest but real predictive power for **intraday trend interruptions**. The mechanism is clustering of stop-loss and take-profit orders at round numbers (Osler, NY Fed). In Bitcoin, prices cluster at round numbers (more than 10% of prices end in "00"), but **no significant return pattern follows round numbers**. I found no rigorous after-cost OOS trading evidence for S/R or "liquidity zones" in crypto.

### Cited Findings
- **Osler (2000), NY Fed Economic Policy Review:**
  - Used S/R levels published by six FX firms. They help predict intraday trend interruptions.
  - Predictive power "varies across the exchange rates and firms examined."
  - The power lasted at least five business days after the levels were published. — [NY Fed EPR](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.html); [PDF](https://resources.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf)
- **Osler (NY Fed Staff Report 125, c. 2001/2004; published in the Journal of Finance in 2003 per the literature, not verified here):**
  - Studied stop-loss and take-profit orders at a large FX dealing bank.
  - The requested execution rates are strongly clustered at **round numbers**, which are often used as S/R levels.
  - This is a microstructure explanation for why S/R levels matter: take-profits tend to reverse trends, and stops tend to cause cascades through the level. — [Staff Report 125 PDF](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf); [FRASER](https://fraser.stlouisfed.org/title/staff-reports-federal-reserve-bank-new-york-9235/stop-loss-orders-price-cascades-currency-markets-673381)
- **Urquhart (2017), "Price clustering in Bitcoin," Economics Letters 159:145–148:**
  - "Over 10% of prices ending with 00 decimals compared to other variations."
  - **No significant pattern of returns after round numbers.**
  - Price and volume are positively related to clustering, which supports the negotiation hypothesis. — [IDEAS](https://ideas.repec.org/a/eee/ecolet/v159y2017icp145-148.html); [Southampton](https://eprints.soton.ac.uk/412873)
- Mbanga (2019, Applied Economics Letters): Bitcoin whole-number clustering is strongest on Fridays and weakest on Mondays. — [Missouri State](https://bearworks.missouristate.edu/articles-cob/431)
- Corbet et al. (2019) explicitly frame their TRB rules as tests of S/R levels on high-frequency BTC. They found TRB weaker than MA rules. — [IDEAS](https://ideas.repec.org/a/eee/finlet/v31y2019icp32-37.html)
- Gerritsen et al. (2020): TRB (breakout above recent highs, below recent lows) was the best daily BTC rule. This is evidence that **breakouts** of swing-high/low ranges carry information, mainly in trending regimes. — [Utrecht portal](https://research-portal.uu.nl/en/publications/the-profitability-of-technical-trading-rules-in-the-bitcoin-marke/)

### Inferences
- Round numbers are where orders sit (clustering is real), but in BTC that has not been shown to produce a tradable return pattern. Treat round numbers or "liquidity zones" as a possible **feature for volatility, reversal or stop-hunt events**, not as a validated signal.
- In crypto, the support for swing-high/low levels comes from the breakout (trend) direction, not from "bounce off support" mean reversion.

### Gaps
- I found no peer-reviewed crypto study of S/R "retests" or "liquidity zones" (order-book or liquidation-level based) with OOS after-cost trading results.
- Osler's FX results are based on 1990s data; I found no evidence on decay.

## Q3. Candlestick patterns

### Takeaway
The evidence is consistently negative. Candlesticks had no value in US large-cap stocks (Marshall, Young & Rose 2006). A 68-pattern test on the top 23 cryptocurrencies found them of "little use." Isolated positive crypto results are unreplicated or are flagged by their own authors as possibly due to manipulation.

### Cited Findings
- **Marshall, Young & Rose (2006), Journal of Banking & Finance**, "Candlestick technical trading strategies: Can they create value for investors?":
  - 28 candlestick signals on DJIA stocks with a 10-day holding period.
  - Per a secondary summary, the signals "for the most part do not work as expected." One bullish single-day signal reliably predicted a **negative** return.
  - The bootstrap details were not verified from the original. — [CXO Advisory summary](https://www.cxoadvisory.com/technical-trading/candlesticks-fiddlesticks/)
- **"Do Candlestick Patterns Work in Cryptocurrency Trading?" (IEEE Big Data 2021):**
  - 68 patterns, daily data, top 23 cryptocurrencies.
  - Concluded the patterns are of little use; more patterns showed low accuracy than high accuracy. — [IEEE Xplore](https://ieeexplore.ieee.org/document/9671826); [EdUHK](https://repository.eduhk.hk/en/publications/do-candlestick-patterns-work-in-cryptocurrency-trading/)
- **Applied Economics Letters (2022), BTC futures, consecutive 1-minute candles:**
  - Profit per trade with take-profit exits. Held out-of-sample in an up-trending period.
  - The authors suggest the effect may reflect **price manipulation**, not a reliable pattern. — [IDEAS](https://ideas.repec.org/a/taf/apeclt/v29y2022i10p947-954.html)
- **Charles University bachelor thesis (2025):**
  - 8 of 41 patterns showed predictive potential.
  - 2 of those produced returns opposite to their bearish labels.
  - Not peer-reviewed. — [CUNI](https://dodo.is.cuni.cz/handle/20.500.11956/197060)

### Inferences
- Candlestick patterns should not be a standalone signal component. At most, use them as raw OHLC shape features (body/wick ratios) inside an ML model, and test them against a shuffled control.

### Gaps
- I found no crypto candlestick study with formal data-snooping correction (RC/SPA) and after-cost OOS testing.

## Q4. Volume confirmation (relative volume, volume spikes)

### Takeaway
In crypto, volume matters **as an interaction with past returns**. The best evidence (Bianchi, Babiak & Dickerson, JBF 2022) shows that lagged return × volume predicts returns, but the profitable strategy is a volume-conditioned **reversal** (liquidity provision), concentrated in lower-activity pairs. That is close to the opposite of "a volume spike confirms continuation." Intraday, the first half-hour return predicts the last half-hour return most strongly in the **high-volume** sessions.

### Cited Findings
- **Bianchi, Babiak & Dickerson (2022), JBF 142:106547**, "Trading volume and liquidity provision in cryptocurrency markets":
  - USD pairs on multiple centralized exchanges, Mar 2017 – Mar 2022.
  - Returns to liquidity provision (proxied by short-term reversal) are concentrated in pairs with **lower** market activity.
  - Panel regressions show that the interaction of lagged returns and volume has significant predictive power. — [EconPapers](https://econpapers.repec.org/RePEc:eee:jbfina:v:142:y:2022:i:c:s0378426622001418); [Warwick WRAP](https://wrap.warwick.ac.uk/165914/)
  - Press coverage of the working paper reported that the volume–return interaction predicts returns intraday and daily, and that a conditional reversal strategy beat momentum after costs. It cited a net annualized return of 342% and Sharpe 2.4; these are **press figures, not verified from the paper, so treat with caution**. — [Opalesque](https://www.opalesque.com/industry-updates/5498/evidence-highly-informed-traders-are-driving-cryptocurrency-prices.html)
- **Shen, Urquhart & Wang (2022), Financial Review 57(2):319–344**, "Bitcoin intraday time-series momentum":
  - Uses volume to define the trading "day." The first half-hour return positively predicts the last half-hour return.
  - Predictability is highest in sessions with the highest volume or volatility.
  - Gains in market timing are largest in downturns. — [Birmingham](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/); [Reading accepted manuscript](https://reading-9.eprints-hosting.org/100181/3/21Sep2021Bitcoin%20Intraday%20Time-Series%20Momentum.R2.pdf)
- Neely, Rapach, Tu & Zhou (2014) include on-balance-volume MAs among their equity technical predictors, and these are useful in combination (see Q6). — [St. Louis Fed WP](https://files.stlouisfed.org/files/htdocs/wp/2010/2010-008.pdf)
- Urquhart (2017): volume is positively related to round-number clustering. This links volume to order placement, not to continuation. — [IDEAS](https://ideas.repec.org/a/eee/ecolet/v159y2017icp145-148.html)

### Inferences
- "Relative volume confirms a breakout" is not directly supported. The supported specification is a **return × volume interaction**, and its sign can be reversal for illiquid pairs. A bot should let a model learn the sign rather than hard-code "volume confirms."

### Gaps
- I found no crypto study that specifically tests "volume-spike breakout confirmation" OOS after costs.

## Q5. Multi-timeframe / higher-timeframe trend filters; time-series momentum across horizons; intraday after costs

### Takeaway
I found **no peer-reviewed study** that validates multi-timeframe (top-down) confluence as such. The idea is practitioner material (Elder's Triple Screen) and unvalidated blog backtests. The nearest academic support is indirect:
- Time-series momentum in crypto is strong, though many portfolios become insignificant once realistic costs and liquidations are included (Han, Kang & Ryu).
- Intraday half-hour momentum exists in BTC (Shen et al.).
- Intraday 5m TA profits decayed over 2013–2017 (Bakker).

### Cited Findings
- **Han, Kang & Ryu**, "Time-Series and Cross-Sectional Momentum in the Cryptocurrency Market: A Comprehensive Analysis under Realistic Assumptions" (AUT working paper):
  - Time-series momentum evidence is strong; cross-sectional momentum evidence is weak.
  - After transaction costs and daily price fluctuations, many momentum portfolios are liquidated, and many with significant gross returns earn insignificant net profits. — [AUT PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)
- **Liu, Tsyvinski & Wu (2022, Journal of Finance):** crypto market, size and **momentum** (cross-sectional, weekly) factors capture the cross-section of expected returns. I could not verify the exact time-series momentum horizon from search results. — [NBER w25882](https://www.nber.org/papers/w25882.pdf); [SSRN](https://papers.ssrn.com/abstract=3379131)
- **Shen, Urquhart & Wang (2022):** BTC intraday time-series momentum, first half-hour → last half-hour. — [Birmingham](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/)
- **Intraday efficiency (FRL 2020):** crypto weak-form efficiency shows a **U-shape** across sampling frequencies, so an intermediate intraday frequency is the most efficient. Source is abstract only; costs are not addressed. — [Bilkent](https://repository.bilkent.edu.tr/items/92242142-0a43-43d1-8df0-759f8c0b7759)
- **Petukhina, Reule & Härdle (2021, European Journal of Finance):** intraday high-frequency crypto trading patterns, including intraday momentum. Source is abstract only. — [arXiv 2009.04200](https://arxiv.org/abs/2009.04200v1)
- **Equity analogue:** high-frequency momentum and contrarian strategies on US blue chips do not beat the benchmark once reasonable costs are included. — [Business Perspectives](https://businessperspectives.org/journals/investment-management-and-financial-innovations/issue-493/high-frequency-momentum-and-contrarian-strategies-in-u-s-blue-chips)
- **Practitioner-only MTF evidence:**
  - Quantpedia's illustrative BTC strategy uses a daily trend filter on hourly MACD entries. It is not a validated OOS study.
  - A backtesting guide warns that the higher-timeframe condition must use the **last closed bar** to avoid look-ahead bias. — [Quantpedia](https://quantpedia.com/how-to-design-a-simple-multi-timeframe-trend-strategy-on-bitcoin/); [Backtrex guide](https://backtrex.com/en/blog/multi-timeframe-backtesting-guide)
- **Preprints (unverified, single-author):**
  - AdaptiveTrend reports Sharpe 2.41 vs 0.65 for 1-month TSMOM, net of a 4 bps taker fee, slippage and funding. — [arXiv 2602.11708](https://arxiv.org/pdf/2602.11708)
  - Barbon's "Catching Crypto Trends" reports Sharpe > 1.5 net of fees on a top-20 rotation. — [abarbon.com](https://abarbon.com/papers/catching-crypto-trends)

### Inferences
- A daily trend filter on intraday entries is consistent with the evidence that crypto TA mostly captures time-series momentum. However, its **incremental** value over the daily trend signal alone is untested in the literature. It must be pre-registered and tested in-house against (a) the daily trend alone and (b) a shuffled-entry control.
- At the 5m–1h horizon, costs dominate. The documented intraday edges are decaying (Bakker) or session/volume-specific (Shen et al.).

### Gaps
- I found no peer-reviewed paper on "nested" or multi-timeframe confluence in crypto, FX or equities with OOS after-cost evidence.
- I found no crypto paper reporting the after-cost Sharpe of 5m/15m indicator rules for the post-2020 period.

## Q6. Data-snooping (White RC, Hansen SPA, STW), decay, indicator redundancy, and ML combination vs single rules

### Takeaway
In mature markets, the classic snooping-corrected results are sobering:
- **Equities (STW 1999; Bajgrowicz & Scaillet 2012):** the best DJIA rules' outperformance disappears out-of-sample (STW), and persistence tests show the future best rules could not be picked in advance. Low costs wipe out even in-sample gains (Bajgrowicz & Scaillet).
- **FX:** Hsu, Taylor & Wang find predictability across 30 currencies with a stepwise test, but Coakley et al. find almost no rule significant in 2006–2015.

Combining indicators helps in equities: principal components of technical indicators forecast the equity premium OOS (Neely et al. 2014). In crypto, ML-combination evidence (Huang et al. 2019; Bakker 2017) is positive but narrow and weakly cost-validated.

### Cited Findings
- **Sullivan, Timmermann & White (1999, Journal of Finance):**
  - White's Reality Check over a large universe of rules (extending Brock-Lakonishok-LeBaron's 26 rules), 100 years of daily DJIA.
  - On the following 10 years (1987–1996) out-of-sample, the best rule earned a statistically insignificant 8.63% per year before costs. This figure is from a secondary citation, not the original. — [FMG discussion paper](https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf); [IDEAS](https://ideas.repec.org/p/fmg/fmgdps/dp303.html); [LSE](https://researchonline.lse.ac.uk/id/eprint/119144)
- **Bajgrowicz & Scaillet (2012, JFE 106(3):473–491):**
  - DJIA 1897–2011, using false-discovery-rate control.
  - Persistence tests: an investor "would never have been able to select ex ante the future best-performing rules."
  - "Even in-sample, the performance is completely offset by the introduction of low transaction costs." — [IDEAS](https://ideas.repec.org:443/a/eee/jfinec/v106y2012i3p473-491.html); [CFA digest](https://rpc.cfainstitute.org/research/cfa-digest/2013/02/technical-trading-revisited-false-discoveries-persistence-tests-and-transaction-costs-digest)
- **Hsu, Taylor & Wang (2016, Journal of International Economics 102:188–208):**
  - 30 currencies, 45 years, 21,000+ rules, stepwise SPA test.
  - Found predictability and excess profitability, cross-validated OOS, with time variation consistent with market immaturity. — [WUSTL](https://profiles.wustl.edu/en/publications/technical-trading-is-it-still-beating-the-foreign-exchange-market/)
- **Coakley, Marzano & Nankervis (2016, IRFA):**
  - Step-SPA test on 22 currencies, 1996–2015.
  - Sharp fall in the number of rules robust to snooping; "virtually no traditional rule is significant in the 2006–2015 sub-sample." — [Essex PDF](https://repository.essex.ac.uk/18805/1/1-s2.0-S1057521916301958-main.pdf)
- **Futures decay:** technical trading profits were substantial in 1978–1984 but "no longer available in the 1985–2003 period." — [AgEcon](https://ageconsearch.umn.edu/record/19039/files/cp05pa01.pdf)
- **Neely, Rapach, Tu & Zhou (2014, Management Science):**
  - Technical indicators (MA, momentum, OBV) show significant in- and out-of-sample equity-premium predictive power, matching or exceeding macro variables.
  - A few principal components combine 14 technical and 14 macro predictors efficiently. OOS period 1960–2008.
  - A secondary summary notes few buy signals after the mid-1980s; not verified. — [St. Louis Fed WP](https://files.stlouisfed.org/files/htdocs/wp/2010/2010-008.pdf); [CXO summary](https://www.cxoadvisory.com/fundamental-valuation/technical-boost-to-fundamental-stock-market-forecasting)
- **Huang et al. (2019, Journal of Finance and Data Science 5(3):140–155):**
  - Classification tree on **124 BTC price-based technical indicators**.
  - Strong OOS predictive power, but **only for narrow ranges** of daily returns. Abstract only; costs not verified. — [Penn State](https://pure.psu.edu/en/publications/predicting-bitcoin-returns-using-high-dimensional-technical-indic/)
- **Bakker (2017):** a neural-network combination of 5m rule signals beat individual rules and benchmarks on risk-adjusted profit and breakeven costs. Thesis, not peer-reviewed. — [Erasmus](https://thesis.eur.nl/pub/41546/)
- **Islas Anguiano & García-Medina (arXiv 2511.00665, 2025):**
  - An LSTM (≈65.23% cumulative return) beat LightGBM, EMA crossover, MACD+ADX and buy-and-hold on BTC around the spot-ETF period.
  - **The abstract does not mention costs or OOS design**, so this is weak evidence. — [arXiv](https://arxiv.org/abs/2511.00665)

### Inferences
- **Redundancy:** EMA/SMA crossovers, MACD (a difference of EMAs), price/MA ratio, momentum, Donchian/TRB and ADX are all functions of the same price path, mostly measuring trend at different lookbacks. RSI and Bollinger %B are normalized short-horizon momentum/deviation measures. This is why combining many of them gives diminishing returns.
- Neely et al. compress 14 technical predictors into a few principal components. Huang et al. find that 124 indicators yield only narrow-range predictability. Both are consistent with a low effective dimensionality, i.e. only a few independent signals.
- My view (not a sourced finding): treat 10+ indicators as roughly 2–3 independent factors (trend level, short-term reversal/overextension, volatility). Any study counting "many indicators agree" as confluence overstates the evidence.
- **Snooping in-house:** every rule or feature-set variant tried counts toward the multiple-testing universe. Use White RC / Hansen SPA / StepM or FDR, and report the number of configurations tried.
- **ML vs single rules:** ML combination is the more promising route (Neely; Bakker; Huang). However, the crypto evidence lacks rigorous after-cost, snooping-corrected OOS validation. Any ML claim must beat (a) the best single trend rule and (b) a shuffled-label control.

### Gaps
- I found no crypto study that applies Hansen SPA to ML models vs single rules after costs.
- I found no quantitative study measuring the correlation or redundancy among crypto indicator signals.
- I could not verify the original STW tables or Hansen (2005) directly.
