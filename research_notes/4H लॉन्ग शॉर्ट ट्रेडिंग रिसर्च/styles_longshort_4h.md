# Trading styles for a 4H crypto system and long/short combination (spot + USDT-M perps)

Scope note: 16 web searches/fetches (2026-10-17). Several key sources (SSRN, Springer, MDPI) returned 403 or paywall, so some figures come from abstracts or search-engine summaries and are flagged as such. Nothing below is from the project's own backtests. Treat every number as a claim to re-verify under the project's protocol (pre-registration + SHA lock + independent verifier) before relying on it.

## Q1. Which hours-to-days styles have published out-of-sample, net-of-cost evidence in crypto? (Sharpe, MDD, trade frequency)

### Takeaway
The only style at the hours-to-days horizon with repeated positive net evidence is **time-series trend following** (Donchian/breakout ensembles, vol-scaled), with reported net Sharpe around 1.5 and most of the return made in bull regimes. **Short-horizon mean reversion** is statistically real but too small to cover costs at 15m. **Cross-sectional weekly momentum** on tradable Binance perps does not survive costs in a 2020-2026 replication. Headline Sharpe ratios above 2 come from single-author or vendor preprints with internal inconsistencies.

### Cited Findings
- **Trend / breakout (BTC + top-20 altcoins):** Zarattini, Pagani and Barbon (Concretum Group), "Catching Crypto Trends", use an ensemble of Donchian-channel trend models with different lookbacks, volatility-based sizing, and a rotational top-20-liquidity altcoin portfolio. They report net-of-fees Sharpe "above 1.5" and 10.8% annualized alpha versus BTC. The landing page does not state the bar frequency, MDD, or cost assumptions. — [Concretum Group](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/)
- **Intraday BTC trend (Concretum, separate study):** An ensemble of high-frequency trend models, vol-targeted to 20%, reportedly had a gross-of-fees Sharpe of about 1.6 over 2018-2025. It also reports a "Monday Asia open" seasonality that strengthened after mid-2020. This figure is from a search summary and is gross of fees. — [Concretum: seasonality in Bitcoin intraday trend trading](https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/)
- **6H trend long/short (AdaptiveTrend, arXiv 2602.11708, Bui & Nguyen, Talyxion Research, Feb 2026):**
  - Setup: Binance Futures, 150+ perps, 6-hour bars, 70% long / 30% short. In-sample 2021; out-of-sample 2022-2024 with monthly re-optimization.
  - Headline result: Sharpe 2.41, MDD -12.7%, annual return 40.5%, volatility 16.8%.
  - Activity: about 142 trades/month, 134% turnover.
  - Cost sensitivity: Sharpe falls to 2.01 at 8 bp and 1.62 at 12 bp.
  - **Red flags:** Sharpe does not reconcile with the stated return and volatility ((40.5-4.5)/16.8 ≈ 2.14). The end date of the OOS window is inconsistent. The paper models 8h funding but calls 6h aligned with "4x daily" funding. Universe construction and survivorship are unaddressed. Not peer-reviewed. Treat as **unverified**. — [arXiv 2602.11708](https://arxiv.org/html/2602.11708v1)
- **Older trend evidence (likely decayed or overfit):** "A Decade of Evidence of Trend Following Investing in Cryptocurrencies" finds optimized SMA rules give the best Sharpe, but optimal parameters are often hyper-tuned, an overfitting concern. — [arXiv 2009.12155](https://ar5iv.labs.arxiv.org/html/2009.12155)
- **Time-series momentum, 20 coins (NAJEF 2021):** Covers interday and intraday frequencies. Momentum periods in crypto are longer than in US stocks. Pre-2021 sample. — [EconPapers](https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000590)
- **Short-horizon mean reversion (Kitron & Wengrowicz, arXiv 2608.21888, Aug 2026):**
  - Data: 15-minute bars, 183 Binance pairs versus 187 US stocks/ETFs, with a permutation null and a frozen 6-month holdout.
  - Prevalence: about 90% of Binance pairs show significant directional reversal (versus 2.7% of US equities). This holds in every focal coin-year since 2021.
  - Mechanism: the reversal is concentrated after aggressive taker-flow moves.
  - **Economics:** the gross edge peaks near **1.3 bp/trade against a 5 bp round-trip cost**, so it is not tradable at spot taker costs. — [arXiv 2608.21888](https://arxiv.org/abs/2608.21888)
- **Cross-sectional momentum net of costs (Arefev, SSRN 7404139, Binance perps 2020-2026):** Per the search-engine summary of the abstract, neither the J=1/K=1 nor the J=2/K=2 week specification yields a net spread distinguishable from zero. The gross 1-week spread is roughly equal to the assumed 0.40 pp/week cost. Direct fetch returned 403, so this is **unconfirmed from the full text**. — [SSRN 7404139](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7404139)
- **Momentum vs reversal horizons (Dobrynskaya, 2,000 coins, 2014-2020):** Positive momentum up to 2-4 weeks, significant reversal beyond 1 month. Older sample, possibly decayed. — [Dobrynskaya, HSE](https://conference.hse.ru/files/download_file_ex?hash=FAE0AB2DC7A67656E89A0B1CB27D8C7D&id=3B5EE9A5-0B18-458A-9458-B4ED0F6C6664)
- **Liquidity dependence of reversal (Leong & Kwok):** Short-term reversal sits mainly in small, illiquid coins. Large liquid coins show weekly momentum instead. — [ResearchGate](https://www.researchgate.net/publication/354881251_Up_or_down_Short-term_reversal_momentum_and_liquidity_effects_in_cryptocurrency_markets)
- **Behavioural cross-sectional reversal (Finance Research Letters 2025):** Profitability is reported to survive "conservative" transaction costs. Abstract only. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S154461232501058X)
- **Cost assumption reference:** An AUT momentum paper assumes 15 bp per trade, estimated from actual fees and slippage. — [AUT ACFR](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)

### Inferences
- At 4H, trend/breakout is the style best supported by evidence. The plausible honest net Sharpe band is roughly 1.0-1.6, not the 2.4 seen in weakly-vetted preprints.
- Mean reversion at sub-hour horizons is real but cost-dominated. A 4H mean-reversion sleeve must clear about 10-20 bp round trip and would need much larger per-trade edges than the 1.3 bp documented at 15m.
- Cross-sectional weekly momentum on large perps sits at roughly zero net, so it is not a good primary sleeve.

### Gaps
- No peer-reviewed paper found specifically on **4H bars** with net Sharpe and MDD. Evidence is at 15m, 1h, 6h, daily, or weekly.
- The full Zarattini et al. PDF was not read, so MDD, bar frequency, trade count and long-only versus long-short status are unverified.
- The Arefev full text was not accessible.

## Q2. Pairs trading / stat-arb (cointegration) at hourly/4H frequency in crypto

### Takeaway
Evidence on Binance data is consistently **weak to negative after costs** at hourly frequency. Results are highly sensitive to parameters and costs, and some studies find daily beats hourly. The most recent hourly Binance-perp study (2026) reports negative net returns.

### Cited Findings
- **Fil & Kristoufek (IEEE Access 2020), 26 Binance coins:**
  - Tests distance and cointegration methods at 5-minute, 1-hour and daily frequencies.
  - Strategies underperform classical benchmarks and are highly sensitive to parameters and costs.
  - Higher frequency performed significantly better, notably at 5-minute.
  - Pre-2020 data. — [IEEE Xplore 9200323](https://ieeexplore.ieee.org/document/9200323)
- **Charles University thesis (Binance 2018 data):** Mostly unprofitable after costs. The cointegration method gives a slight loss. Moving from daily to hourly gives mixed results. — [CUNI dspace](https://dspace.cuni.cz/handle/20.500.11956/109634)
- **Setzer thesis (Univ. Católica Portuguesa, 2022):** Engle-Granger cointegration with a 210-day formation window and 75-day trading window (walk-forward). The **daily** strategy beat the **hourly** one. Not peer-reviewed. — [UCP repository](https://repositorio.ucp.pt/entities/publication/640a8e22-8bd7-442f-9ab0-490d843829c8)
- **Comparison study (30 Binance coins, Q1 2022):** Compares six pair-selection methods at 1, 5 and 60 minutes. Distance was best at 60 minutes. Cointegration and Hurst were comparable at 1 and 5 minutes. Short sample. — [NISC abstract](https://www.nisc.co.za/products/abstracts/37380/pairs-trading-in-cryptocurrency-markets-a-comparative-study-of-statistical-methods)
- **QFE 2026 (AIMS Press):** Copula-based pairs on 26,257 hourly observations of 10 major Binance USDT perps (2021-2023) produced **negative net returns after trading costs**. Per a search summary; the PDF could not be parsed. — [QFE-10-02-016](https://www.aimspress.com/aimspress-data/qfe/2026/2/PDF/QFE-10-02-016.pdf)
- **Turku thesis:** Compares distance, cointegration and copula methods in crypto (abstract only). — [UTUPub](https://www.utupub.fi/handle/11111/24573)

### Inferences
- Pairs/stat-arb on large-cap Binance coins at 1h-4h does not have convincing net-of-cost OOS support through 2023.
- One plausible reason is that crypto majors are highly co-moving (BTC-beta dominated), so spreads are small relative to fees. This is an inference, not directly tested in these sources.
- If tried at all, it should be a small, pre-registered sleeve with maker execution assumptions tested explicitly.

### Gaps
- No source quantified decay year by year for crypto pairs trading.
- Trade counts and MDD from these studies were not extracted (full texts not read).

## Q3. Funding-rate / cash-and-carry (spot long + perp short) returns 2020-2026, drawdowns, risks, compression

### Takeaway
Carry has been large on average but highly time-varying:
- BIS reports average carry above 10% p.a. for BTC/ETH, with peaks up to about 60%.
- An academic perp-arbitrage backtest on Binance hourly data (2020 to Mar 2024) shows Sharpe of about 1.8 for BTC after high costs, with very low MDD (about -4%). The funding component was negative in 2022-2023, and deviations shrink about 11% per year.
- 2025 on-chain yields (sUSDe) of about 4-7% show compression.
- Key risks are funding flips, margin/liquidation of the perp leg, exchange failure (FTX), and crash-correlated unwinds.

### Cited Findings
- **BIS WP 1087 "Crypto carry" (Schmeling, Schrimpf, Todorov; Apr 2023, revised Oct 2025):**
  - Carry can reach about 60% p.a. and averages above 10% p.a. for BTC/ETH, far above carry in other asset classes.
  - Carry is driven by convenience yield from trend-chasing retail leverage and scarce arbitrage capital.
  - Arbitrage is risky because margins spike and positions get liquidated in drawdowns.
  - **High carry predicts future crashes.** — [BIS WP 1087](https://www.bis.org/publ/work1087.htm)
- **He, Manela, Ross, von Wachter, "Fundamentals of Perpetual Futures" (arXiv 2212.06888v5):**
  - Data: Binance hourly, BTC/ETH from 2020-01-08 to 2024-03-11 (BNB, DOGE and ADA also included).
  - Perp arbitrage, high-cost tier, annualized excess return / Sharpe / MDD: BTC 6.38% / 1.80 / -4.43%; ETH 9.59% / 2.55 / -3.94%; BNB 18.41% / 4.84 / -1.11%; DOGE 23.31% / 3.58 / -8.56%; ADA 12.03% / 2.68 / -4.35%.
  - Without fees, BTC Sharpe is 3.53.
  - BTC Sharpe by year: 2020 2.26, 2021 2.39, **2022 0.70**, 2023 1.32, 2024 partial 11.52.
  - Return decomposition (no-fee): most return comes from **price convergence**, not funding (BTC 13.70% total = 8.64% convergence + 5.06% funding). The funding component of BTC was **negative in 2022 and 2023** and appears to be diminishing.
  - Absolute futures-spot deviation shrinks about **11% per year**.
  - Not a BIS paper; it is a separate academic paper. — [arXiv 2212.06888v5](https://arxiv.org/html/2212.06888v5)
- **Springer (Digital Finance, 2026), CEX-DEX funding arbitrage as a basis trade:**
  - Data: Binance BTC/ETH/SOL funding, Jan 2021 to Dec 2024.
  - Argues the trade must be evaluated on funding, market, liquidity, liquidation and settlement risk, not the funding spread alone.
  - Builds a liquidation survival model and stress tests. Numbers not accessible (paywall). — [Springer s42521-026-00213-3](https://link.springer.com/article/10.1007/s42521-026-00213-3)
- **MDPI Mathematics 14(2):346, "Two-Tiered Structure of Funding Rate Markets":** Simulates delta-neutral portfolios on spreads of at least 20 bp with $10k per opportunity, evaluated by Sharpe and MDD. Results not retrieved (403). — [MDPI](https://www.mdpi.com/2227-7390/14/2/346)
- **Compression evidence, 2025:** Aave sUSDe 30-day supply APY was 7.17% (Oct 1, 2025), 4.29% (Nov 1, 2025) and 5.14% (Dec 1, 2025). sUSDe yield tracks the funding Ethena earns on short perps. This is an on-chain dashboard, not a peer-reviewed source. — [Aavescan sUSDe](https://aavescan.com/rates/ethena-susde)
- **Post-crash context:** A secondary source reports that sUSDe-related supply peaked near $14.8B (Oct 7, 2025) and fell below $6B by spring 2026 after the Oct 10, 2025 crash. Unverified. — [Datawallet](https://www.datawallet.com/crypto/october-10-crypto-crash-explained); [Eco](https://eco.com/support/en/articles/15254002-ethena-usde-and-susde-2026-delta-neutral-yield)
- **Contested or unverified practitioner figures:**
  - "115.9% over six months, max loss 1.92%" is attributed to a 2025 ScienceDirect study, but only found second-hand.
  - Vendor claims of 8-25% APY after fees are not peer-reviewed.
  - Treat all of these as **unverified marketing**. — [search summary sources: BJF](https://bjftradinggroup.com/funding-rate-arbitrage/), [Buildix](https://www.buildix.trade/blog/crypto-funding-rate-arbitrage-delta-neutral-hyperliquid-binance)
- **Negative funding persistence:** Example reports of BTC funding negative for about 46 days around the FTX bottom. Persistently negative funding did not reliably produce squeezes. — [Phemex](https://phemex.com/blogs/bitcoin-funding-rates-negative-46-days-ftx-bottom); [OKX](https://www.okx.com/en-us/orbit/insight/89388657396640)

### Inferences
- A naive "always on" spot-long/perp-short carry probably yields low single digits to roughly 10% p.a. in 2024-2026 after fees. It is very low-volatility, but it has tail risk at crash points, which is exactly when carry was highest per BIS.
- Most of the published arbitrage Sharpe comes from **timing the entry when the deviation is wide** (convergence), not passive funding collection. For a 4H system, that implies a conditional, threshold-based carry sleeve.
- Carry is roughly uncorrelated with the direction of trend sleeves but **positively linked to bull regimes** (high funding in booms). It is a regime-dependent diversifier, not a pure hedge.

### Gaps
- No peer-reviewed full-period 2020-2026 funding-carry return series was found. 2025-2026 evidence is on-chain or vendor data only.
- No quantified liquidation probability by leverage was accessible (the Springer paper has it, paywalled).
- The Kaiko, Amberdata and Glassnode funding statistics reports were not located in this pass.

## Q4. Combining trend and mean-reversion sleeves; documented diversification in crypto

### Takeaway
**No study was found that directly tests a combined trend + mean-reversion crypto portfolio with OOS net results.** The pieces point in opposite directions by horizon and liquidity, which suggests diversification, but that is untested.

### Cited Findings
- Search found no direct combined-portfolio test. Quantpedia has separate trend and local-high/low studies on BTC. — [Quantpedia crypto tag](https://quantpedia.com/tag/cryptocurrencies/page/2/)
- Horizon split:
  - Momentum up to 2-4 weeks, reversal beyond 1 month. — [Dobrynskaya](https://conference.hse.ru/files/download_file_ex?hash=FAE0AB2DC7A67656E89A0B1CB27D8C7D&id=3B5EE9A5-0B18-458A-9458-B4ED0F6C6664)
  - Strong 15m reversal on about 90% of Binance pairs. — [arXiv 2608.21888](https://arxiv.org/abs/2608.21888)
- Liquidity split: reversal in illiquid coins, momentum in liquid ones. — [Leong & Kwok](https://www.researchgate.net/publication/354881251_Up_or_down_Short-term_reversal_momentum_and_liquidity_effects_in_cryptocurrency_markets)
- Ensembles of trend lookbacks (rather than trend + MR) are used by Concretum to diversify parameter risk. — [Concretum](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/)
- Regime profile of a trend long/short book (AdaptiveTrend, unverified): bull +68.3% (Sharpe 3.42), sideways +18.7% (Sharpe 1.87), **bear -4.2% (Sharpe -0.31)**. — [arXiv 2602.11708](https://arxiv.org/html/2602.11708v1)

### Inferences
- Trend makes money in bull runs and loses or whipsaws in sideways and bear markets. A mean-reversion or carry sleeve is the logical complement for sideways regimes, but the 4H mean-reversion edge must be proven net of costs first.
- Diversifying across trend lookbacks (ensemble) is better supported than adding an unproven MR sleeve.

### Gaps
- No crypto-specific evidence on the correlation between trend and MR sleeves, or the Sharpe uplift from combining them.

## Q5. Long-short construction: BTC beta hedging, dollar vs beta neutral, short-side problems, does the short leg add value?

### Takeaway
Academic crypto factor work forms long-short quintile portfolios and finds market, size and momentum factors explain the cross-section. Recent net-of-cost replications on tradable perps find weekly cross-sectional spreads close to zero. Practitioner papers tilt long (for example 70/30) because of positive drift and short costs. Direct evidence that the **short leg adds net value** in crypto was not found.

### Cited Findings
- **Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency" (Journal of Finance 2022, 77:1133-1177, DOI 10.1111/jofi.13119):** Three factors (crypto market, size, momentum) capture cross-sectional expected returns. Long-short is built as top versus bottom quintile, weekly.
  - Versions disagree on the count of successful characteristics: the SSRN version says 10, the NBER version says 9.
  - Alpha Architect lists a different venue, which conflicts with the JF listing.
  - Pre-2020 sample, so likely decayed. — [SUFE listing](https://academicnewsletter.sufe.edu.cn/info/359095); [SSRN 3379131](https://papers.ssrn.com/abstract=3379131); [NBER w25882](https://www.nber.org/papers/w25882.pdf)
- **Net-of-cost cross-sectional replication on Binance perps 2020-2026:** Spread is indistinguishable from zero (abstract summary only). — [SSRN 7404139](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7404139)
- **Asymmetric long/short sizing (AdaptiveTrend):**
  - 70% long / 30% short is justified by positive drift and higher short costs. The 50/50 variant is loosely called "dollar-neutral".
  - Short candidates are the smallest-cap coins, with a stricter entry threshold (Sharpe ≥ 1.7 versus 1.3 for longs).
  - No standalone short-leg performance is reported.
  - Short-leg capacity is estimated at about $5-10M before slippage exceeds 10 bp. — [arXiv 2602.11708](https://arxiv.org/html/2602.11708v1)
- **Short-side frictions:**
  - Negative funding means shorts pay longs.
  - Squeezes occur in crowded shorts (single-case altcoin example: BAT +95% in a week with negative funding).
  - Negative funding is not a reliable squeeze predictor.
  - [FinanceFeeds](https://financefeeds.com/what-does-negative-funding-mean-in-crypto/); [KuCoin news](https://www.kucoin.com/news/flash/bat-surges-95-in-a-week-amid-negative-funding-rate-and-short-squeeze); [OKX](https://www.okx.com/en-us/orbit/insight/89388657396640)
- **Crash linkage:** High carry predicts crashes, and arbitrage positions face margin spikes and liquidations in drawdowns. This is relevant to the perp leg of any hedged book. — [BIS WP 1087](https://www.bis.org/publ/work1087.htm)

### Inferences
- **Same coin vs different coins:**
  - Same-coin spot long + perp short is the carry trade (delta-neutral, earns basis/funding).
  - Different-coin long/short is a relative-value or factor bet that, in crypto, mostly loads on altcoin-versus-BTC beta.
  - A beta-neutral book (sizing shorts by rolling beta to BTC) is the standard practice to isolate idiosyncratic return. No crypto-specific source in this pass quantified dollar-neutral versus beta-neutral outcomes. Altcoin betas to BTC are typically above 1, so a dollar-neutral alt-long/BTC-short book would be net long market beta. This is an inference.
- **Net exposure by regime:** Given trend's bear-regime losses and positive long-run drift, a defensible design is a net-long tilt in bull regimes and flat-to-short in bear regimes. The short leg should be limited to liquid majors to avoid squeeze and capacity risk.
- The short leg's value in crypto is **unproven in this literature pass**. A project test should report long-only, short-only and combined sleeves separately against a shuffled control.

### Gaps
- No paper found isolating short-leg alpha in crypto net of funding and borrow.
- No published comparison of dollar-neutral versus beta-neutral crypto books.
- No Man Group, AQR or Coinbase/Fidelity practitioner note was retrieved on crypto long/short construction.

## Q6. Concurrent positions / coins; raising trade count (6 decisions/day, staggered tranches) and the cost trade-off

### Takeaway
More decision points raise turnover and cost drag almost linearly. Published 6H systems with about 140 trades/month lose about 0.4 Sharpe per extra 4 bp of cost. The better-documented way to add trades without adding cost-driven noise is **breadth** (more independent coins or sleeves) plus **tranching / staggered rebalances**, which reduces "rebalance timing luck" rather than adding turnover.

### Cited Findings
- **Cost sensitivity at 6H (AdaptiveTrend):** about 142 trades/month with 134% turnover. Sharpe 2.41 at 4 bp, 2.01 at 8 bp, 1.62 at 12 bp. Universe is about 15 longs plus K_S shorts, equal-weighted within each leg. — [arXiv 2602.11708](https://arxiv.org/html/2602.11708v1)
- **Concretum uses a top-20 liquid altcoin rotation** (breadth) with vol-based sizing. — [Concretum](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/)
- **15m reversal edge of 1.3 bp versus 5 bp round trip:** at very high decision frequency, costs swamp the edge. — [arXiv 2608.21888](https://arxiv.org/abs/2608.21888)
- **Weekly cross-sectional momentum:** the gross spread of about 0.40 pp/week is roughly equal to costs. Turnover kills it. — [SSRN 7404139](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7404139)
- **Illustrative only (GitHub backtest, non-peer-reviewed):** 138% daily turnover produces about 101% annual cost drag. — [GitHub prams2104](https://github.com/prams2104/crypto-momentum-backtest)
- **Rebalance timing luck and tranching (Hoffstein, Faber, Braun 2020, Newfound):**
  - Performance is highly sensitive to the rebalance schedule. In equity factor indices, timing luck often exceeds 100 bp/year.
  - Remedy: tranching, i.e. rebalancing "a little but frequently". Newfound applies a 1-month tranche to trend signals.
  - Equities and multi-asset only, not crypto. — [Newfound RTL tag](https://blog.thinknewfound.com/tag/rebalance-timing-luck/); [Newfound 2013](https://blog.thinknewfound.com/2013/08/the-luck-of-the-rebalance-timing/)

### Inferences
- For a 4H bar system, 6 decision points/day is natural. Act on a signal only when it changes, or split entries into tranches (for example 3 to 6 sub-positions offset by one 4H bar each). That adds trade *events* but keeps total notional turnover similar, so fee drag is roughly unchanged. It also reduces the variance from which bar the signal fired on.
- The cheapest route to more independent trades is more coins and more uncorrelated sleeves (trend ensemble lookbacks, conditional carry), not faster signals. Effective breadth is limited because crypto co-moves heavily with BTC.
- Use maker execution, or measure realized fees and slippage. Every 4 bp of round-trip cost at about 140 trades/month costs roughly 0.4 Sharpe (AdaptiveTrend sensitivity, unverified).

### Gaps
- No crypto-specific study of tranching or staggered entries was found.
- No published distribution of "typical number of concurrent positions" for professional crypto long/short funds was found.
- No AQR or Man Group crypto-specific practitioner evidence was retrieved in this pass.
