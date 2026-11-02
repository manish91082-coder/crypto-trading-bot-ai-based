# Crypto price behaviour and strategy evidence by timeframe (5m to 1M)

Status note (read first): this research session hit a web-search session limit after about 12 tool calls, so coverage is partial. Primary-text verification was possible for two papers only (Liu & Tsyvinski NBER w24877 full text; Liu, Tsyvinski & Wu 2019 working-paper full text), which were downloaded and text-extracted locally. All other items are from abstracts or search-engine summaries and are marked [ABSTRACT/SUMMARY ONLY]. Anything I could not verify this session is listed under Gaps, not under Cited Findings. Internal numbers come from `internal_tf_stats.md` (SHA-locked data in data/universe_hf, 8 coins, 2020-01..2026-09).

## Q1. Autocorrelation and variance ratios by horizon: what does the literature say, and does it agree with our internal numbers?

### Takeaway
The literature is horizon-split, matching our data in sign. At intraday horizons, crypto shows both momentum and reversal, depending on conditions. At daily horizons, early-sample Bitcoin (2011-2018) showed positive daily and weekly time-series momentum. Cross-sectional momentum works at 1-4 weeks and reverses beyond about 4 weeks. Our 2020-2026 data shows mild mean reversion from 5m to 1D (VR(4) 0.94-0.995) and trend at 1W/1M (VR 1.18/1.24). That agrees with the weekly-momentum literature. It disagrees with Liu & Tsyvinski's positive daily coefficient, which most plausibly reflects a sample-period (pre-2018) and maturity effect, and the weekly/monthly internal numbers are statistically weak (N=353 and N=81).

### Cited Findings
**Daily and weekly time-series momentum (Liu & Tsyvinski, NBER WP 24877, Aug 2018; published RFS 2021). Full text verified locally:**
- Bitcoin daily: today's return positively and significantly predicts the 1-, 3-, 5- and 6-day-ahead returns. A 1-SD (5.55%) daily move implies +0.33% next day (coefficient 0.06). — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- Bitcoin weekly: the current week's return predicts the 1-, 2-, 3- and 4-week-ahead returns. Coefficients are 0.19/0.22/0.21/0.09, with OLS t = 3.73/4.52/4.26/1.72 but bootstrapped t = 2.17/2.73/2.47/1.40, so the 4-week horizon is not significant under bootstrap. A 1-SD weekly move (16.64%) implies +3.16% the next week. — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- Quintile sort of weekly Bitcoin returns: the top quintile returns 11.22%/week next week (Sharpe 0.45) versus 2.60% for the bottom quintile. In the no-look-ahead version (cutoffs from the first 2 years), the spread shrinks to 4.53 pp at t+1 and 8.23 pp at t+2. — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf); the same 11.2%/2.6% figures appear in [CXO Advisory summary](https://www.cxoadvisory.com/currency-trading/crypto-asset-risks-and-returns/)
- Ripple daily momentum is significant at 1-5 days. Ethereum is significant only at 1 day (+), and its 5-day coefficient is negative (−0.08). The paper says ETH momentum is "less significant". — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- Bitcoin Sharpe ratio rises with frequency: 0.09 daily, 0.23 weekly, 0.31 monthly. Skewness also rises with horizon: 0.80, 1.76, 4.32. — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- Day-of-week: there is no Monday effect, but Saturday returns are lower for all three coins. — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)

**Cross-sectional momentum (Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency", 2019 WP; published Journal of Finance 2022). Full text verified locally:**
- Coins above $1M market cap, 2014-2018, weekly rebalancing, quintile long-short. The 1-, 2-, 3- and 4-week momentum strategies earn 2.7%, 3.3%, 4.1% and 2.5% per week respectively, significant at 5% (1% for 3-week). — [Yale/Cowles PDF](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
- 8-, 16-, 50- and 100-week momentum are not significant (16-week: 0.4%/week, insignificant). — [same](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
- Momentum works among larger coins: 4.2%/week, significant, versus 0.6%/week (insignificant) below median size. Results barely change when Bitcoin is the short leg. — [same](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
- [CONTRADICTION] Grobys & Sapkota (Economics Letters 180, 2019; 143 coins, 2014-2018) find momentum insignificant. [ABSTRACT/SUMMARY ONLY] — [UWasa repository](https://osuva.uwasa.fi/items/99fceb0a-aaaa-4df2-aed1-09e6232a9df3); [IDEAS](https://ideas.repec.org/a/eee/ecolet/v180y2019icp6-10.html)
- Dobrynskaya (HSE): momentum is positive and significant for formation and holding up to 2 weeks, insignificant at 2-4 weeks, and reversed from about 4 weeks up to 2 years. She notes that weekly rebalancing incurs significant transaction costs. [SECONDARY SUMMARY ONLY] — [HSE news](https://www.hse.ru/en/news/research/559533243.html)
- Fičura (2023): weekly reversal occurs only in small and illiquid coins, while large and liquid coins show weekly momentum. [ABSTRACT ONLY] — [VSE FFA WP](https://wp.ffu.vse.cz/artkey/wps-202301-0003_impact-of-size-and-volume-on-cryptocurrency-momentum-and-reversal.php)
- Zaremba et al. (2021, per search summary): the largest and most tradeable coins show daily momentum rather than reversal, and the reversals are attributed to illiquidity. Kozlowski, Puleo & Zhou (2020) find reversal at daily, weekly and monthly rebalancing, strongest in small and illiquid coins. [SECONDARY SUMMARY ONLY; original papers not opened] — [Medeniyet repository record](https://earsiv.medeniyet.edu.tr/items/23a96c9f-3952-4bdf-aec5-abafb3aaab70); [Fairfield record](https://fairfield.elsevierpure.com/en/publications/cryptocurrency-return-reversals/)
- Bianchi, Babiak & Dickerson (J. Banking & Finance 142, 2022; USD pairs, Mar 2017 to Mar 2022): returns to liquidity provision, measured by a short-term reversal strategy, concentrate in less active, smaller, more volatile and less liquid pairs. The interaction of lagged return and volume predicts returns. [ABSTRACT ONLY] — [IDEAS](https://ideas.repec.org/a/eee/jbfina/v142y2022ics0378426622001418.html); [Riksbank WP 413](https://www.riksbank.se/globalassets/media/rapporter/working-papers/2022/no.-413-trading-volume-and-liquidity-provision-in-cryptocurreny-markets.pdf)

**Intraday (minutes to hours):**
- Wen, Bouri, Xu & Zhao (N. Am. J. Econ. & Finance 62, 2022; high-frequency BTC data, 2013-03 to 2020-05, also ETH/LTC/XRP) find both intraday momentum and intraday reversal. They link momentum to late-informed traders and reversal to overreaction to non-fundamental information. Predictability changes with jumps, FOMC days, liquidity and COVID, and timing strategies beat buy-and-hold in-sample. Exact horizons and costs are not stated in the abstract. [ABSTRACT ONLY] — [IDEAS](https://ideas.repec.org/a/eee/ecofin/v62y2022ics1062940822000833.html)
- Shen, Urquhart & Wang (Financial Review, 2022): the first half-hour return predicts the last half-hour return, using volume-defined "trading day" boundaries because BTC trades 24/7. The effect is stronger in high-volume or high-volatility sessions and is attributed to liquidity provision. Economic gains are reported, especially in downturns. No out-of-sample or after-cost replication was found. [ABSTRACT/SUMMARY ONLY] — [Birmingham repository](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/); [Reading eprint PDF](https://reading-9.eprints-hosting.org/100181/3/21Sep2021Bitcoin%20Intraday%20Time-Series%20Momentum.R2.pdf)
- Efficiency versus sampling frequency is contested. Aslan & Şensoy (Finance Research Letters, 2020) find a U-shape: efficiency is lowest at intermediate intraday frequencies, using Hurst and long-memory tests rather than VR. A 2025 CEEJ study of 16 coins, using martingale-difference tests, finds efficiency falls as frequency rises. [ABSTRACT ONLY] — [Bilkent repository](https://repository.bilkent.edu.tr/items/92242142-0a43-43d1-8df0-759f8c0b7759); [CEEJ 2025](https://reference-global.com/article/10.2478/ceej-2025-0003)
- Daily VR tests (Mallesha & Archana 2024; top-10 coins, 2020-2023) reject the random walk for most coins. The direction (VR above or below 1) was not visible in the abstract. [ABSTRACT ONLY] — [ICMAI Research Bulletin](https://icmai-rnj.in/index.php/rb/article/view/173425)

### Inferences
- **5m-1h:** our negative lag-1 autocorrelation and VR(4) of about 0.94-0.95 fit the reversal half of the "momentum and reversal" intraday literature. They also fit liquidity-provision and bid-ask-bounce explanations (Bianchi et al.). The 5m ac1 of −0.027 is far outside the ±0.0023 iid band, so it is statistically real but economically tiny next to the costs in Q2.
- **1D:** our ac1 of −0.053 (2020-2026) is the opposite sign to Liu-Tsyvinski's +0.06 daily coefficient (BTC 2011-2018). Our recent-window daily ac1 is about 0 (0.0004). A reasonable reading is that the early-sample daily momentum has not persisted into the mature, derivatives-heavy market. This is an inference, not tested against their exact specification.
- **1W:** our VR of 1.18 and ac1 of +0.117 agree in direction with weekly time-series momentum (L-T coefficient 0.19 at 1 week) and with 1-4-week cross-sectional momentum (LTW, Dobrynskaya). However, ac1 0.117 against a ±0.10 band is only borderline significant, the recent-window ac1 is just 0.026, and SOL, ADA and AVAX turn negative recently. Agreement in sign is not strong confirmation.
- **1M:** a VR of 1.24 from N=81 bars (iid band ±0.22 for ac1; XRP VR 0.57, LINK 0.97) cannot be distinguished from noise. The literature also finds no cross-sectional momentum beyond about 4-8 weeks and reversal from about 4 weeks (Dobrynskaya; LTW 8+ weeks insignificant). Monthly "trend" should therefore be treated as unproven.
- There is a size and liquidity split. Momentum lives in large, liquid coins and reversal in small, illiquid ones. Our 8-coin universe is all large-cap, so weekly momentum is the relevant literature prior for it.

### Gaps
- Could not fetch the Liu-Tsyvinski RFS 2021 published version to check whether the published sample or results differ from the 2018 WP. The verified numbers are from the WP.
- Found no crypto study reporting Lo-MacKinlay variance ratios side by side at 5m/15m/1h/4h/1D/1W. The intraday efficiency studies use other tests.
- De Nicola (2021) on intraday crypto reversal and momentum: not found or verified this session (search limit).
- Did not locate post-2020 replications of time-series momentum at daily and weekly horizons for BTC/ETH.

## Q2. Microstructure noise, bid-ask bounce and cost drag at 1-5 minutes

### Takeaway
The realized-volatility literature treats about 5 minutes as the noise/accuracy compromise, and Bitcoin papers adopt it, with noise reported as small above about 1 minute. For a trader, the binding constraint at 5m is cost, not noise. Our measured cost/median-move ratio is 68% at 5m and 38% at 15m, against 3.7% at 1D. The literature on 5m-15m strategies net of retail costs is thin and was not verified this session.

### Cited Findings
- General theory (equities): with noise, realized variance is biased and the optimal sampling frequency is finite. See Bandi & Russell, and Aït-Sahalia, Mykland & Zhang (2005), who give a closed-form expression. [SUMMARY ONLY] — [SUFE newsletter on AMZ](https://academicnewsletter.sufe.edu.cn/info/355544); [NUS IMS paper](https://imsarchives.nus.edu.sg/oldwww/Programs/econometrics/files/fb_paper1.pdf)
- A Bitcoin rough-volatility study uses 5-minute RV to limit high-frequency bias, citing Bandi & Russell (2006) and Liu et al. (2015). [arXiv preprint] — [arXiv 1904.12346](https://arxiv.org/pdf/1904.12346)
- A Bitcoin multifractality paper reports microstructure noise looks small until about 1-minute horizons, and says 5-minute RV balances bias and efficiency. [arXiv preprint; search summary] — [arXiv 2511.03314](https://arxiv.org/pdf/2511.03314)
- Liquidity-provision (reversal) returns are larger where adverse-selection fear is higher: small, volatile, illiquid pairs. This implies short-horizon reversal is partly compensation for providing liquidity, which a taker cannot capture. [ABSTRACT ONLY] — [IDEAS, Bianchi et al. 2022](https://ideas.repec.org/a/eee/jbfina/v142y2022ics0378426622001418.html)
- Internal: cost (0.085% perp taker round trip including measured spread) divided by median |bar move| is 68% at 5m, 38% at 15m, 20% at 1h, 10% at 4h, 3.7% at 1D, 1.3% at 1W and 0.5% at 1M. For BTC 5m it exceeds 100% (1.19). — internal_tf_stats.md (SHA-locked data)

### Inferences
- For a 5m taker strategy to break even on BTC, it must capture more than the median 5m candle body on every round trip. Negative ac1 of −0.03 explains about 0.1% of variance (ac1² ≈ 0.0009), far below what is needed. The 5m mean reversion we measured is real but not monetisable by takers at 0.04-0.085% round trip.
- What remains at 5m-15m is maker-side activity (earning rather than paying the spread), which needs queue priority, low latency and inventory management. Retail-access traders on a standard fee tier generally lack these. The academic attribution of intraday reversal to liquidity provision (Bianchi et al.; Shen et al.) supports this reading.
- Cost drag scales roughly as 1/sqrt(bar length) relative to the move: 68% → 38% → 20% → 10% → 3.7% for roughly 3x/4x/4x/6x bar-length steps, consistent with the sqrt-time scaling of volatility. Strategy viability therefore improves sharply from 1h upward.

### Gaps
- No verified crypto paper this session on market-making or scalping profitability net of fees for retail fee tiers, or on order-flow-imbalance strategies. The search for "high-frequency technical trading crypto after fees" failed due to the session limit.
- No verified crypto-specific bid-ask bounce magnitude (for example, Roll-implied spread) at 1-5 minutes.

## Q3. Volatility seasonality (intraday and day-of-week)

### Takeaway
Crypto volatility and volume have recurring intraday and weekly patterns: the hour after 00:00 UTC and around 16:00 UTC run higher, with weekend lulls (Saturday especially). These patterns affect 5m-4h stops and position sizing. Whether return seasonality persists is disputed.

### Cited Findings
- Hansen, Kim & Kimbrough (2021; BTC/ETH; Binance, Coinbase Pro, Uniswap V2): the first hour of the UTC day and the hour after 16:00 UTC have the highest volatility, with the first hour elevated on Mondays. Volume and volatility are lower on weekends, especially Saturday. Within the hour, there is a large volatility burst in the first minute, medium bursts at :15/:30/:45 and small bursts every 5 minutes. [arXiv preprint; Quantpedia summary] — [arXiv 2109.12142](https://arxiv.org/pdf/2109.12142); [Quantpedia](https://quantpedia.com/periodicity-in-cryptocurrencies-recurrent-patterns-in-volatility-and-volume/)
- Baur, Cahill, Godfrey & Liu (more than 15M observations, 7 exchanges): time-of-day, day-of-week and month effects vary over time and are not consistent or persistent. Weekend volume is lower and activity is higher during US stock-market hours. [ABSTRACT ONLY] — [UWA repository](https://research-repository.uwa.edu.au/en/publications/bitcoin-time-of-day-day-of-week-and-month-of-year-effects-in-retu/)
- Lower Saturday returns for BTC/XRP/ETH (2011-2018), with no Monday effect. — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)

### Inferences
- At 5m-1h, a fixed-percentage stop is miscalibrated across the day. ATR measured on the same bar size, or hour-of-day-normalised volatility, should be used, and the 00:00 UTC and 16:00 UTC bursts deserve attention. Return-based calendar strategies are contested (Baur et al.) and should not be relied on.

### Gaps
- No verified study of 4h-bar seasonality or of funding-time (00/08/16 UTC) effects on perps. Note that the volatility hours above coincide with Binance funding times, but that link is unverified.

## Q4. Which strategy families have evidence at which timeframe; holding periods

### Takeaway
The evidence density is weakest at 5m-15m, where the evidence is mostly in-sample, often pre-cost, and mechanisms point to liquidity provision. It is moderate at 1h-4h, where intraday momentum and reversal are documented but cost-sensitive. It is strongest at daily and weekly horizons: time-series momentum at 1-4 weeks, cross-sectional momentum at 1-4 weeks, and Donchian trend-following on daily bars with Sharpe above 1.5 net of fees (practitioner/academic preprint). The evidence is weak or negative beyond about 4-8 weeks, where cross-sectional momentum is insignificant or reverses.

### Cited Findings
- Zarattini (Concretum), Pagani (Parma) & Barbon (St. Gallen), "Catching Crypto Trends" (2025, SSRN/Swiss Finance Institute RP 25-80): long-only ensemble of Donchian channels with multiple lookbacks plus volatility sizing, rotating across the top 20 liquid coins using a survivorship-bias-free universe since 2015. Reported Sharpe is above 1.5 with 10.8% annual alpha versus BTC, net of fees. [PREPRINT; numbers from search summary only, not verified in text] — [IDEAS rp2580](https://ideas.repec.org/p/chf/rpseri/rp2580.html); [Barbon page](https://abarbon.com/papers/catching-crypto-trends); [CXO summary](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/)
- Time-series momentum holding period: 1-4 weeks (BTC weekly) and 1-6 days (BTC daily) in the 2011-2018 sample. — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- Cross-sectional momentum: lookback 1-4 weeks (3-week is best) with a 1-week hold. Lookbacks of 8 weeks or more fail. — [LTW 2019 WP](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
- Momentum up to 2 weeks, reversal from about 4 weeks to 2 years, with weekly-rebalance costs noted. [SECONDARY] — [HSE](https://www.hse.ru/en/news/research/559533243.html)
- Intraday half-hour momentum (BTC) and intraday momentum/reversal (BTC/ETH/LTC/XRP) both appear in-sample, with no after-cost OOS evidence found. [ABSTRACT ONLY] — [Birmingham](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/); [IDEAS Wen et al.](https://ideas.repec.org/a/eee/ecofin/v62y2022ics1062940822000833.html)
- Short-term reversal is a liquidity-provision premium concentrated in illiquid pairs. [ABSTRACT ONLY] — [IDEAS](https://ideas.repec.org/a/eee/jbfina/v142y2022ics0378426622001418.html)

Evidence map (cited where sourced above; "no verified source" means not verified this session):

| Band | Behaviour (literature + internal) | Families with some evidence | Evidence quality |
|---|---|---|---|
| 5m | Mild reversal (internal ac1 −0.027, VR 0.947); noise is small above 1 min | Market making / liquidity provision (maker side) | Weak for takers; cost/move 68% |
| 15m | Mild reversal (VR 0.95) | Same; intraday mean reversion | Weak; cost/move 38% |
| 1h | Reversal and momentum both documented; half-hour momentum | Intraday momentum/reversal timing | In-sample, abstract-only; cost/move 20% |
| 4h | VR about 1.0 (internal) | Breakout/swing: no verified source | No crypto-specific verified study |
| 1D | Early-sample BTC daily TSMOM (+); internal 2020-26 ac1 −0.05 | Donchian/trend ensemble (daily bars, multi-week holds) | Moderate (preprint, net of fees) |
| 1W | TSMOM 1-4 wk; XS momentum 1-4 wk; internal VR 1.18 | Weekly TSMOM, XS momentum (large coins) | Strongest academic evidence (RFS/JF), but 2011-2018 samples |
| 1M | XS momentum insignificant beyond 8 wk, reversal from 4 wk; internal VR 1.24 on N=81 | Cycle/halving trend: unverified | Very weak; few independent observations |

### Inferences
- The "sweet spot" where both the literature and our cost ratios point is daily bars with multi-day to multi-week holds, plus weekly signals. 4h works as an execution or entry refinement layer, since its cost ratio is 10% and VR is about 1, meaning there is no edge in persistence by itself.
- Halving or monthly cycle strategies: BTC has had only 4 halvings (2012, 2016, 2020, 2024), so there are about 3-4 independent cycle observations, which makes any statistical claim essentially untestable. Our 81 monthly bars (2020-2026) cover about 1.5 cycles. This is arithmetic, not a cited claim.

### Gaps
- Halving-cycle literature: search failed (session limit). No verified source this session.
- Carry (perp funding / basis) strategy evidence by horizon: not researched (search limit).
- 4h breakout or swing evidence specific to crypto: none found or verified.

## Q5. How holding period and exit speed should scale with timeframe

### Takeaway
No crypto academic source verified this session prescribes ATR-multiple stops by timeframe. Scaling rules have to be derived from first principles and our own data. Volatility scales roughly with sqrt(time), so stops and targets should be set in ATR of the signal timeframe, and time stops should be a fixed number of bars, matched to the horizon over which the literature finds predictability (for example, 1-4 weeks for weekly momentum, 1-6 days for daily).

### Cited Findings
- Internal median bar range: 0.29% (5m), 0.52% (15m), 1.09% (1h), 2.30% (4h), 6.16% (1D), 18.9% (1W), 49% (1M). The ratios 1h→4h (2.1x) and 4h→1D (2.7x) are close to sqrt(4)=2 and sqrt(6)≈2.45, consistent with sqrt-time scaling with slight mean reversion below 1D. — internal_tf_stats.md
- Predictability horizons in the literature: daily TSMOM 1-6 days, weekly TSMOM 1-4 weeks (4-week bootstrap insignificant), XS momentum 1-4 week lookback with 1-week hold. — [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf); [LTW](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)

### Inferences
- **Stops and targets:** express them in ATR(n) of the signal timeframe, since a fixed % stop that suits 1D (6% range) is about 21 average 5m ranges and would never trigger intrabar. A rule tuned on one timeframe does not transfer to another unless it is ATR-normalised.
- **Time stops:** set them as a fixed bar count tied to the evidence horizon. A daily trend signal with predictability at 1-6 days implies a time stop of about 5-10 daily bars. A weekly momentum signal implies 1-4 weekly bars. Holding beyond about 4 weeks moves into the reversal zone documented in the cross-section.
- **Exit speed:** on 5m-1h, where the regime is mean-reverting (VR below 1), exits should be fast: take profit quickly, because trends do not persist. On 1W, where VR is above 1, exits should be slow or trailing so the trend can run. On 1D, where VR is 0.94 internally but there is trend-following evidence from Donchian ensembles, multi-lookback ensembles are a hedge against this ambiguity.
- **Minimum move to cover costs:** a target below about 3x the round-trip cost (0.26%) is under the 5m median range, which is another reason 5m taker strategies fail.

### Gaps
- No peer-reviewed crypto study found or verified on optimal ATR-multiple stops or time-stop length by bar size. Any such parameters must be pre-registered and tested internally (walk-forward, SHA-locked) per project rules.
