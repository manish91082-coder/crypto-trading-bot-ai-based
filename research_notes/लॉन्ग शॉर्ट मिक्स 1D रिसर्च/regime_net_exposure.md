# Regime-adaptive net exposure and risk budgeting for long-short crypto portfolios

Scope note: crypto evidence comes first. Equity, futures and multi-asset evidence is labelled **[BACKGROUND, non-crypto]**. Monthly-only evidence is labelled **[MONTHLY]**. Researcher notes are in English for precision. The final report should be written in Hindi, per CLAUDE.md.

Project context: our top-5 long spot / bottom-5 short perp book (50/50) had a backtest max DD of 21%. Long-only had 49%. A "market will fall" short-timing signal failed 5 times.

---

## 1. Time-series momentum (TSMOM) / trend-following in crypto: evidence, lookbacks, bear markets, whipsaw

### Takeaway
Crypto TSMOM evidence is fairly consistent, at daily and weekly frequency, mostly in large caps, and mostly on the long side. The evidence for the short leg or long-short TSMOM is much weaker. Robust practitioner designs use an ensemble of many lookbacks (5 to 360 days) plus volatility scaling, instead of one tuned lookback. Hard crypto-specific numbers for 2018 and 2022 were not found.

### Cited Findings
- Liu & Tsyvinski, "Risks and Returns of Cryptocurrency" (NBER w24877, 2018; published in RFS 2021), report "a strong time-series momentum effect", and investor-attention proxies forecast crypto returns. — [NBER PDF](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf); [SSRN](https://papers.ssrn.com/abstract=3226806)
- Same authors: a one-standard-deviation rise in Bitcoin's current-week return goes with about a 3.16% higher return over the next week. This is a **weekly** horizon. — [VoxEU column](https://cepr.org/voxeu/columns/risks-and-returns-cryptocurrencies); [WEF](https://www.weforum.org/stories/2018/09/what-are-the-risks-and-returns-associated-with-cryptocurrencies/)
- A CXO Advisory summary of Liu-Tsyvinski reports significant time-series momentum at **daily and weekly** frequencies for BTC, XRP and ETH, with ETH less significant. This is a secondary source. — [CXO Advisory](https://www.cxoadvisory.com/currency-trading/crypto-asset-risks-and-returns/)
- Han, Kang & Ryu, "Time-Series and Cross-Sectional Momentum in the Cryptocurrency Market…under Realistic Assumptions" (working paper). With transaction costs and daily price moves included, TSMOM evidence is strong and cross-sectional momentum evidence is weak. They also note the literature is "divided" because sample selection, lookback/holding periods and test methods differ. I saw this only in a search snippet; the PDF returned HTTP 403. — [AUT/ACFR PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)
- Wisselink (Erasmus BSc thesis, 2018; daily-rebalanced). 85% of **long-only** TSMOM portfolios had significant positive excess returns, but **long-short** TSMOM portfolios did not. This is low-authority (a thesis) but directly relevant to the short leg. — [Erasmus thesis](https://thesis.eur.nl/pub/44390/Wisselink-NJ-483391-BA-thesis.pdf)
- Borgards (2021, North American Journal of Economics and Finance), "Dynamic time series momentum of cryptocurrencies": crypto has significantly larger and longer momentum periods than other assets at all frequencies. — [EconPapers](https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000590)
- Grobys, Kolari, Sandretto, Shahzad & Äijö, "Cryptocurrency momentum has (not) its moments" (Financial Markets and Portfolio Management, 2025). Large-cap crypto momentum portfolios suffer severe crashes, and a single coin can make momentum returns insignificant. Volatility management helps mitigate those crashes, and momentum is a large-cap phenomenon. — [Springer](https://link.springer.com/article/10.1007/s11408-025-00474-9); [Univ. Vaasa repository](https://osuva.uwasa.fi/handle/10024/20018)
- Zarattini, Pagani & Barbon, "Catching Crypto Trends" (SSRN 5209907 / SFI RP 25-80, 2025):
  - Method: an ensemble of Donchian-channel trend models with lookbacks of 5, 10, 20, 30, 60, 90, 150, 250 and 360 days.
  - Sizing: 25% annualized volatility target (90-day standard deviation), leverage capped at 200%, **daily rebalance**.
  - Costs tested at 0.10%, 0.25% and 0.50%.
  - Data: survivorship-free data on 21,616 assets, 2010 to March 2025.
  - Result: on a rotating top-20-liquid-coin portfolio, Sharpe above 1.5 and annualized alpha of 10.8% vs BTC, net of fees.
  - Caveats: the base design is **long-only**, and these are the authors' own backtests. — [CXO summary](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/); [IDEAS/RePEc](https://ideas.repec.org/p/chf/rpseri/rp2580.html); [Concretum](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/)
- Man Group, "In Crypto We Trend" (data to Dec 2024):
  - MA-crossover trend works best on about 10 to 15 coins, and breakouts on about 10.
  - Liquidity is "ample" only for the top 15 coins.
  - Average pairwise correlation is about 0.6, which limits diversification.
  - Volatility scaling reduces transaction costs in stress periods.
  - No drawdown, 2018/2022, or long-only vs long-short numbers are given. — [Man Group](https://www.man.com/insights/in-crypto-we-trend)
- CXO test of BTC simple-moving-average timing (Jul 2010 to Dec 2017, **gross of costs**):
  - Buy-and-hold: Sharpe about 2.0, max DD -89.5%.
  - SMA rules: Sharpe from 2.6 (5-day) down to 2.2 (100-day); max DD from -66.4% (5-day) to -70.3% (50/100-day).
  - So MA timing cut drawdown only modestly, and costs could exceed breakeven. — [CXO Advisory](https://cxoadvisory.com/?p=30879)
- Anecdotal only: in 2022 BTC traded below its 200-day MA for 70 consecutive days, one of the longest streaks on record (Bespoke, via Bloomberg). This is a description, not a backtest. — [Bloomberg](https://www.bloomberg.com/news/articles/2022-03-07/bitcoin-stuck-in-the-doldrums-is-making-some-bulls-optimistic)
- **[BACKGROUND, non-crypto][MONTHLY]** Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following Investing" (JPM, Fall 2017):
  - Setup: 67 markets, 1880 to 2016; equal-weighted 1-, 3- and 12-month TSMOM; **monthly rebalance**; each position vol-targeted, portfolio at a 10% annualized ex-ante vol target; net of simulated costs and 2/20 fees.
  - Average per-market Sharpe is about 0.4.
  - Positive returns in 8 of the 10 largest 60/40 drawdowns. Those drawdowns averaged about 15 months peak to trough.
  - Can fail in very rapid crashes (e.g. 1987).
  - The strategy itself had drawdowns of up to 25%, tied to sharp reversals and trendless periods.
  - A 20% allocation cut the max drawdown of a 60/40 portfolio. — [AQR](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing?aqrPDF=1); [PDF copy, Yale](https://fairmodel.econ.yale.edu/ec439/hurst.pdf)
- **[BACKGROUND, non-crypto]** Whipsaw and trendless periods: the SG CTA Trend Sub-Index returned -0.8% annualized from Jan 2009 to Jun 2013 (Hutchinson & O'Brien, via Swedroe). Man AHL's flagship returned 3.2% in 2024, which its CIO attributed to a lack of trends and frequent reversals. — [ETF.com / Swedroe](https://www.etf.com/sections/index-investor-corner/swedroe-trend-following-works-weakest-after-crises); [Man Group CIO podcast (LSEG)](https://www.lseg.com/en/solutions/hedge-funds/podcast/hedge-fund-huddle/season-4-episode-1-centuries-strategy-a-conversation-with-man-groups-cio)

### Inferences
- Trend "works" in crypto mainly by stepping aside (going to cash) in downtrends. The evidence for profitably **shorting** on trend is thin: Wisselink found long-short not significant, and Zarattini et al. is long-only. This fits our 5 failed short-timing tests. An overlay that cuts the long book is better supported than one that adds outright short beta.
- Hurst et al. show trend profits come from slow bear markets (about 15 months) and fail in fast crashes. Crypto crashes are often abrupt (e.g. single-day crashes), so a daily trend overlay will lag the first leg of a crash. The always-on short book in our long-short design covers that gap better than a timing signal.
- Using many lookbacks (5 to 360 days) at once is the main defence against overfitting a single "best" lookback.

### Gaps
- No primary source found with crypto TSMOM performance numbers specifically for the 2018 or 2022 bear markets.
- No quantified crypto whipsaw cost for sideways markets (e.g. 2019 or mid-2023) was found.
- Exact Han-Kang-Ryu lookback and Sharpe figures could not be read (PDF blocked).

---

## 2. Volatility targeting / volatility-managed portfolios: effect on Sharpe and max DD (crypto)

### Takeaway
Volatility targeting reliably cuts tail risk and left-tail days. Its Sharpe gains are contested out-of-sample: strong in-sample (Moreira-Muir) but mostly failing in real time across 103 equity strategies. Momentum is a notable exception. In crypto, vol management is supported mainly as a fix for momentum crashes and for BTC risk-reward. Rigorous crypto-specific max-DD numbers are scarce.

### Cited Findings
- **[BACKGROUND, non-crypto]** Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & Van Hemert, "The Impact of Volatility Targeting" (JPM 45(1), 2018, pp. 14–33):
  - Data: 60+ assets, **daily** data from as early as 1926.
  - Sharpe improves for risk assets (equities, credit) and for balanced/risk-parity portfolios; the effect is negligible for bonds, FX and commodities.
  - It lowers the likelihood of extreme returns in all asset classes and lowers max drawdown for balanced and risk-parity portfolios.
  - Mechanism: volatility clustering plus the leverage effect, which acts like a short-term momentum overlay. — [Man Institute](https://www.man.com/insights/the-impact-of-volatility-targeting); [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf)
- **[BACKGROUND, non-crypto]** Cederburg, O'Doherty, Wang & Yan, "On the Performance of Volatility-Managed Portfolios" (JFE 2020):
  - Across 103 equity strategies, vol-managed versions had higher Sharpe in only 53, and only 8 of those gains were significant.
  - Feasible real-time mean-variance combinations had **lower** Sharpe in 72 of 103 cases.
  - The authors blame structural instability; the in-sample Moreira-Muir alphas need full-sample foresight. Returns are gross.
  - Exceptions with less degradation: MOM, ROE and BAB. — [Lehigh PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf); [Alpha Architect](https://alphaarchitect.com/?p=59058); [CXO](https://www.cxoadvisory.com/volatility-effects/does-volatility-management-work-for-equity-factor-portfolios/)
- **[BACKGROUND]** DeMiguel, Martin-Utrera & Uppal (JF 2024) accept that single-factor vol management fails out-of-sample and propose a conditional multifactor version. — [LBS Research Online](https://lbsresearch.london.edu/id/eprint/3716)
- **Crypto:** Grobys et al. (2025) find that vol management mitigates crypto momentum crashes. — [Springer](https://link.springer.com/article/10.1007/s11408-025-00474-9)
- **Crypto:** Chassang & Wang (2018), via Macrosynergy:
  - Both volatility control and MinMax drawdown control considerably improve BTC's Sharpe ratio.
  - But to match the drawdowns of drawdown control, vol control must cut exposure heavily throughout, which significantly lowers returns. — [Macrosynergy, "Drawdown control"](https://macrosynergy.com/?p=41407)
- **Crypto (commercial backtest/paper-trade, weak evidence):** K33's actively managed BTC strategy (downside-vol reduction) reports Sharpe 1.07 vs 0.71 for BTC, and max DD -47.7% vs -52.3%, net of fees but hypothetical. — [K33](https://active.research.k33.com/)
- **Crypto practitioner designs:** Zarattini et al. use a 25% vol target, 90-day standard deviation and 200% cap; Man says vol scaling reduces stress-period trading costs. — [CXO](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/); [Man](https://www.man.com/insights/in-crypto-we-trend)

### Inferences
- For our long-short book, vol targeting is best treated as a **risk-normalizer**, giving roughly constant ex-ante portfolio vol, not as an alpha source. Expect less tail damage, but do not pre-register a Sharpe improvement as the success criterion, because Cederburg et al. show that claim often fails out-of-sample.
- The K33 result shows vol control alone cut BTC drawdown only modestly (47.7% vs 52.3%). Our 21% long-short DD already comes from structure (the short book), which is stronger than any vol overlay result found.

### Gaps
- No peer-reviewed crypto paper was found that reports Sharpe and max DD side by side for a vol-targeted vs unmanaged crypto portfolio at daily frequency.
- Moreira & Muir (2017, JF) was not fetched directly; it is cited here only through Cederburg et al.

---

## 3. Drawdown control rules, CPPI / TIPP, stop-trading rules: evidence and pitfalls

### Takeaway
Drawdown control (Grossman-Zhou) is mathematically the same as CPPI with a floor that tracks the running peak. It does cap drawdown, but it has well-documented pitfalls: cash lock (stuck near zero exposure after a loss, missing the recovery), gap risk when trading is discrete (very relevant to 24/7 crypto gaps and perp liquidations), and strong path dependence. On BTC it improved Sharpe in one study.

### Cited Findings
- Grossman & Zhou's optimal drawdown-constrained policy invests in the risky asset in proportion to the gap between wealth and a fraction of running-max wealth. This is CPPI with a floor that tracks the peak. — [Columbia drawdown-minimization paper](https://drupalgsb-test.paas.cc.columbia.edu/sites/default/files-efs/pubfiles/6358/drawdownminimization.pdf); see also [arXiv 2609.23272](https://arxiv.org/pdf/2609.23272)
- **Cash lock:** once the floor is hit, CPPI moves fully into the risk-free asset and cannot take part in later gains. Exposure often shrinks toward zero before the floor is hit. — [U-Cergy WP 2023-22](https://thema.u-cergy.fr/IMG/pdf/2023-22.pdf)
- Cash-lock probability rises with the multiplier and the horizon more than with the asset's dynamics, so it is a design risk. — [Freiburg seminar abstract (Gaspar)](https://www.fdm.uni-freiburg.de/seminar/Raquel%20Gaspar)
- **Gap risk:** when trading is discrete or prices gap, the portfolio can fall below the floor. A higher multiplier raises gap exposure. — [Mancinelli PhD thesis](https://tesidottorato.depositolegale.it/bitstream/20.500.14242/158460/1/Tesi_dottorato_Mancinelli.pdf); [MetricGate](https://metricgate.com/docs/constant-proportion-portfolio-insurance/)
- **Path dependence:** discrete trading creates cash-lock and gap risk. Path-dependent floor variants (Temoçin, Korn & Kestel 2018) measure cash-lock probability and expected shortfall. — [METU repository](https://open.metu.edu.tr/bitstream/handle/11511/25355/index.pdf)
- **Crypto:** Chassang & Wang (2018) find MinMax drawdown control improved BTC's Sharpe and achieved its drawdown targets with less return sacrifice than vol control. — [Macrosynergy](https://macrosynergy.com/?p=41407)
- MacLean, Thorp & Ziemba: "practitioners who wish to protect capital above all, sharply reduce risk as their drawdown increases" (i.e. drawdown-based de-risking is standard practice). — [MacLean-Thorp-Ziemba, "Good and bad properties of the Kelly criterion"](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)

### Inferences
- A hard "stop trading at -X% DD" rule on a long-short book risks cash lock. The book stops just after a loss and misses the mean-reversion of the spread. Prefer a **soft, continuous** de-risking schedule (e.g. scale gross exposure down linearly with DD, with a floor of something like 25–50% of normal, never zero) plus a pre-registered re-entry rule.
- The DD threshold and multiplier are free parameters. They need to be pre-registered and SHA-locked, or they become another overfitting knob.

### Gaps
- No crypto long-short (market-neutral) study of CPPI/TIPP or DD-stop rules was found.
- The quantitative results of the Chassang-Wang paper were seen only through a secondary summary.

---

## 4. Risk parity / inverse-volatility between long and short books; beta targeting by regime

### Takeaway
I found no reliable crypto-specific source on risk-parity weighting between a long book and a short book, or on net-BTC-beta bands such as -0.2 to +0.5. What is supported: vol-normalizing each leg (each position sized to equal volatility, as in Hurst et al. and Zarattini et al.), and the observation that crypto correlations are high (about 0.6). That means the dollar-neutral 50/50 book is only roughly beta-neutral; the short book (bottom-ranked alts) usually has higher beta than the long book.

### Cited Findings
- **[BACKGROUND][MONTHLY]** In Hurst et al., each position is sized to the same volatility and the combined book is scaled to a 10% ex-ante vol target, so that risk is consistent over time. — [Yale PDF copy](https://fairmodel.econ.yale.edu/ec439/hurst.pdf)
- **Crypto:** Zarattini et al. use volatility-based position sizing (25% target, 90-day standard deviation). — [CXO](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/)
- **Crypto:** average pairwise correlation is about 0.6 over a decade, and diversification is limited. — [Man Group](https://www.man.com/insights/in-crypto-we-trend)
- **[BACKGROUND]** Harvey et al.: vol targeting lowers max DD for **risk-parity** portfolios. — [Man Institute](https://www.man.com/insights/the-impact-of-volatility-targeting)
- **Crypto factor structure:** a market factor, a size factor and a momentum factor capture the cross-section of crypto returns. This implies the long/short legs carry market and size exposure, not just spread. — [Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency"](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)

### Inferences
- A 50/50 dollar-neutral book with a short leg of small, weak alts is likely **net short beta** in crashes (alt beta > 1) and can suffer short squeezes in alt rallies. An inverse-vol or beta-matched split between legs (short notional = long notional × beta_long/beta_short, measured on trailing daily data) is the standard way to neutralize this. It should be tested as a pre-registered variant, not assumed.
- Given the project's 5 failed short-timing tests, a **fixed, narrow beta band** (rebalanced to target) is less overfit-prone than regime-switching net exposure. Any band such as -0.2 to +0.5 has no literature backing found here and would be our own design choice.

### Gaps
- No sources were found on practitioner net-beta bands for crypto long-short funds, or on risk-parity between long and short books in crypto. More targeted search (e.g. crypto market-neutral fund disclosures, Robeco/AQR long-short equity beta management) would be needed.

---

## 5. Fractional Kelly sizing: theory and why 1/4–1/2 Kelly

### Takeaway
Full Kelly maximizes long-run growth but has deep drawdowns. Betting 2× Kelly gives zero excess growth, and growth turns negative beyond that. Errors in estimated mean returns dominate. So practitioners scale down: half Kelly keeps about 75% of the growth with much higher security.

### Cited Findings
- MacLean & Ziemba (1999) blackjack table (2% edge), reprinted in MacLean-Thorp-Ziemba:

  | Kelly fraction | P[doubling before halving] | Relative growth |
  |---|---|---|
  | 0.5 | 0.89 | 0.75 |
  | 1.0 (full Kelly) | 0.67 | 1.00 |
  | 1.5 | 0.56 | 0.75 |
  | 2.0 | 0.50 | 0.00 |

  — [MacLean-Thorp-Ziemba](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- In continuous time (geometric Brownian motion), betting exactly 2× Kelly gives a growth rate equal to the risk-free rate (Thorp 1997; Stutzer 1998; Janacek 1998). Betting above Kelly raises risk and lowers growth, so "it never pays to bet more than the Kelly strategy". — [same](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- Fractional Kelly is a blend of Kelly and cash. For lognormal assets, half Kelly matches negative-power utility with δ = -1, and quarter Kelly matches δ = -3. — [same](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- Estimation error: errors in means vs variances vs covariances matter roughly 20:2:1 (Chopra & Ziemba 1993). The authors say "the size of the wagers should be reduced" given E-log's extreme sensitivity to mean errors. — [same](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- Even half Kelly can end badly. In a 700-bet example, full Kelly could turn $1000 into $18, and half Kelly into $145. — [same](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- Telling two edges apart takes a very long time. With σ = 20% vs 10% and means of 20% vs 10%, it takes 157 years to be 95% sure which is better. — [same](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- Secondary sources (consistent with the table above): practitioners commonly use 1/2 or 1/4 Kelly. — [Wikipedia: Kelly criterion](https://en.wikipedia.org/wiki/Kelly_criterion)
- Standard result (Thorp), as a formula: in continuous time, P(wealth ever falls to fraction x) = x^(2/k − 1) for Kelly multiple k. That gives about 50% chance of ever halving at full Kelly and about 12.5% at half Kelly, with no estimation error. — derived from the continuous-time results in [MacLean-Thorp-Ziemba](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf). The formula itself is not printed in the extracted text, so treat it as a derivation.

### Inferences
- The Kelly fraction depends on the estimated mean edge, which is the least reliable input, especially after our failed tests. A crypto long-short book should use at most 1/4–1/2 of the Kelly level implied by its **out-of-sample** (not in-sample) Sharpe. If the in-sample edge is overstated by 2×, half Kelly becomes effectively full Kelly.
- Kelly also gives a natural cap on leverage: the Kelly leverage is about Sharpe / volatility. With OOS Sharpe near 1 and portfolio vol of 40%, full Kelly is about 2.5× and half Kelly about 1.25×. This is an illustrative calculation, not a sourced figure.

### Gaps
- No crypto-specific empirical study of fractional-Kelly sizing was found.

---

## 6. Regime-detection inputs for crypto (BTC vs 200-day MA, realized vol, funding, breadth) and out-of-sample evidence

### Takeaway
Out-of-sample evidence for crypto regime filters is weak or missing. The best-supported inputs are trend (price vs moving average, or TSMOM) and realized volatility. I found no rigorous out-of-sample evidence that funding rates or breadth predict returns or improve net-exposure timing. In general, timing overlays are prone to overfitting and to failing in real time.

### Cited Findings
- **Trend / MA:**
  - BTC SMA timing (2010–2017, gross) raised Sharpe (2.6 vs 2.0) and cut max DD from -89.5% to about -66% to -70%. Costs may exceed breakeven. — [CXO](https://cxoadvisory.com/?p=30879)
  - The Zarattini et al. ensemble (5–360 days) works across a survivorship-free universe. — [CXO](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/)
  - The 200-week MA "caught" the 2015, 2018 and 2022 bottoms, according to an anecdotal claim that is not a backtest. — [Tradewize blog](https://tradewize.io/blog/bitcoin-200-week-moving-average)
- **Realized volatility:** supported as a sizing input rather than a direction signal. — [Man Institute](https://www.man.com/insights/the-impact-of-volatility-targeting); [Grobys et al.](https://link.springer.com/article/10.1007/s11408-025-00474-9)
  - Its real-time out-of-sample robustness is contested in equities. — [Cederburg et al.](https://www.lehigh.edu/~xuy219/research/COWY.pdf)
- **Funding rates:**
  - Academic work found covers mechanics and pricing: longs pay shorts in proportion to the perp-spot gap. — [He, Manela, Ross & von Wachter, "Fundamentals of Perpetual Futures" (arXiv)](https://arxiv.org/pdf/2212.06888v5)
  - CryptoQuant cautions that high funding rates do not necessarily predict an inevitable price drop. — [CryptoQuant user guide](https://userguide.cryptoquant.com/cryptoquant-metrics/market/funding-rates)
  - I found no peer-reviewed out-of-sample evidence that funding rates predict direction.
- **Overfitting / instability of timing:**
  - Cederburg et al. attribute the out-of-sample failure of vol timing to structural instability. — [Lehigh PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf)
  - Han-Kang-Ryu note crypto momentum conclusions vary with sample, lookback and test choices. — [AUT PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)
  - Grobys et al. show a single coin can flip momentum significance. — [Springer](https://link.springer.com/article/10.1007/s11408-025-00474-9)
- **[BACKGROUND]** Trend works through slow bear markets but fails in abrupt crashes, and is weak in trendless periods after crises. — [Hurst et al.](https://fairmodel.econ.yale.edu/ec439/hurst.pdf); [Swedroe](https://www.etf.com/sections/index-investor-corner/swedroe-trend-following-works-weakest-after-crises)

### Inferences
- The evidence consistently favours **structural** risk control over **predictive** net-exposure timing:
  - Our 50/50 long-short already cut DD from 49% to 21% without any timing.
  - Vol targeting and soft DD de-risking change position **size**, not direction, and have more robust support.
  - Directional short timing is where both the literature (long-short TSMOM not significant; vol-timing fails out-of-sample) and our own record (5 failures) are negative.
- If a regime filter is tested, the most defensible single candidate is a slow, multi-lookback BTC trend filter that only **reduces the long book** (e.g. long book × 0.5 when BTC < 200-day MA). It should not increase shorts.
- Test discipline: one pre-registered rule, SHA-locked, compared against a shuffled-regime control, with daily costs included. Counting our 5 earlier attempts, the multiple-testing burden is already high, so a deflated-Sharpe-style correction is warranted.

### Gaps
- No out-of-sample crypto study was found that validates funding-rate, breadth or realized-vol regime switches for net exposure.
- No source was found that quantifies how often crypto regime filters fail in real time.
- Hidden Markov / regime-switching crypto models were not covered within the search budget.
