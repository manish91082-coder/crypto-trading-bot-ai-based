# Market Regime Detection and Strategy Selection ("Master Decision Brain") — Evidence File

Scope: does a regime-detecting brain that switches to the "best" strategy per regime work out-of-sample (OOS), compared with simpler options (static ensemble, equal-weight combination, volatility scaling)? Crypto is the main focus.

Source-status legend:
- [F] = fetched or read in this session. Numbers come from the page.
- [S] = only the search-result summary was seen. Verify before quoting numbers.
- [K] = canonical paper cited from prior knowledge, with a DOI or SSRN link. It was NOT re-fetched this session, so the report writer should verify exact figures.
- IS = in-sample. NC = no transaction costs. Both are flagged where relevant.

---

## Q1. Regime detection methods (HMM, Markov-switching, change-point, clustering, volatility regimes, ADX): OOS accuracy, lag, and whether lag kills switching profits (crypto evidence)

### Takeaway
Regime models do find bull, bear and calm states after the fact. The best OOS evidence found is in equities (Shu, Yu & Mulvey 2024): regime switching helped mainly by cutting drawdowns, but only after the model was made persistent (jump penalty) to stop whipsaw. A plain HMM switched too often and lost much of its edge to costs. Detection lag is real: about 2 weeks at both the onset and the end of the COVID crash, and a cited median of 25 days. I found no crypto study with a fully documented, cost-inclusive OOS trading backtest of HMM regime switching. The crypto HMM papers are mostly density-forecast or descriptive studies.

### Cited Findings
- **Statistical Jump Model (JM) vs HMM vs buy-and-hold (B&H), Shu, Yu & Mulvey (Princeton), Journal of Asset Management 2024 [F]:**
  - Setup: S&P 500, DAX and Nikkei daily data. The OOS period is 1990–2023, with 10 bps one-way costs and a base 1-day trading delay (a signal at the close of t is executed at the close of t+1). Delay robustness was tested at 1, 5 and 10 days. — [arXiv 2402.05272](https://arxiv.org/html/2402.05272v3)
  - OOS Sharpe, B&H / HMM / JM: S&P 0.48 / 0.54 / 0.68; DAX 0.30 / 0.35 / 0.44; Nikkei 0.12 / 0.19 / 0.31. Max drawdown on the S&P: −55.2% / −28.9% / −26.6%. CAGR on the S&P: 10.2% / **8.5%** / 11.2%. The HMM strategy earned *less* return than B&H on the S&P. — [arXiv 2402.05272](https://arxiv.org/html/2402.05272v3)
  - Turnover on the S&P: HMM 141% vs JM 44%. Nikkei: 290% vs 72%. — [same](https://arxiv.org/html/2402.05272v3)
  - Whipsaw: an unsmoothed HMM makes about 8.5 regime shifts per year, and still about 2 per year with a 20-day smoothing window. The JM falls from 9.7 shifts per year with no penalty to under 1 per year at typical penalties. The authors say the HMM S&P strategy "frequently" underperformed B&H because of trading costs and lower identification accuracy. — [same](https://arxiv.org/html/2402.05272v3)
  - Lag: during the COVID crash, JM online signals lagged by about half a month at both onset and recovery. The paper cites a median detection lag of 25 calendar days from prior work. Latency causes missed rebounds, but the strategy still avoided about 20% of the drawdown. — [same](https://arxiv.org/html/2402.05272v3)
  - The authors call HMMs fragile, sensitive to mis-estimation and mis-specification, and give small samples, unbalanced data and high state persistence as causes. — [arXiv 2402.05272](https://arxiv.org/pdf/2402.05272)
- **Nystrup (DTU) regime-based allocation [S]:** adjusting equity weight gradually as a linear function of the forecast regime probability gave OOS performance similar to switching 100%/0%. Soft, probability-weighted exposure is as good as hard switching and has lower turnover. — [Nystrup thesis, DTU](https://www2.imm.dtu.dk/pubdb/pubs/6808-full.html)
- **Sparse jump model for dynamic factor allocation [S]:** extends the JM with feature weighting (Nystrup et al. 2021). Its online inference, where lag matters, was not visible in the snippet. — [arXiv 2410.14841](https://arxiv.org/pdf/2410.14841)
- **Crypto HMM studies [S]:**
  - A Bayesian non-homogeneous HMM (4 states) separates bull, bear and calm regimes for BTC. Its focus is predictive density, not a trading rule. — [arXiv 2011.03741](https://ar5iv.labs.arxiv.org/html/2011.03741)
  - Figà-Talamanca, Focardi & Patacca (2021) fit HMMs to BTC, ETH, LTC and XMR, selected by AIC/BIC and OOS forecast accuracy. They *claim* the models "may be exploited" for profitable strategies, but the snippet showed no OOS P&L. — [RePEc, N. Am. J. Econ. & Finance v57 2021](https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000577)
  - A two-state HMM with macro and BTC-specific covariates, descriptive only. — [VU Vilnius](https://epublications.vu.lt/object/elaba:246222004/246222004.pdf)
- **HMM factor-switching template (equities) [S]:** an HMM switches between factor models with OOS from Sep 2017 to Apr 2020. That OOS window is short. — [JRFM 13(12):311](https://www.mdpi.com/1911-8074/13/12/311/htm)
- **Regime literature review [K]:** Ang & Timmermann, "Regime Changes and Financial Markets," *Annual Review of Financial Economics* 4 (2012). Regime models capture skewness, fat tails and time-varying correlations well IS. Real-time regime *identification* is much harder. — [doi:10.1146/annurev-financial-110311-101808](https://doi.org/10.1146/annurev-financial-110311-101808)

### Inferences
- The OOS benefit of regime detection shows up mostly as **lower drawdown and volatility (risk-off filtering)**, not as higher return. Raw HMM switching can lower CAGR below buy-and-hold once costs and a 1-day delay are applied.
- Persistence control matters more than model sophistication: a jump penalty, minimum holding time or hysteresis. Unsmoothed HMMs whipsaw at about 8–10 switches per year.
- A 2–4 week detection lag is the norm in daily-data studies. A regime brain therefore cannot catch V-shaped crypto reversals. It helps mainly in long, persistent bear phases such as 2018 and 2022.
- No study found used ADX, change-point or clustering filters in crypto with a costed OOS test. For the crypto regime part of the bot, assume the evidence is **unproven** and test it under a pre-registered protocol.

### Gaps
- No crypto paper was found with documented OOS **regime-classification accuracy** (for example, % of days correctly labeled in real time) or a costed regime-switching backtest. Change-point methods (BOCPD, CUSUM) and ADX trend filters in crypto: no rigorous OOS evidence was found in this session.
- The 25-day median-lag figure is second-hand, cited inside Shu et al. The original source was not retrieved.

---

## Q2. Strategy selection, meta-learning and "strategy tournaments": does picking the recent winner work, or is it performance chasing?

### Takeaway
The weight of evidence favours **combining over selecting**. With realistic estimation windows, 1/N beats optimized allocation (DeMiguel et al.). Equal-weight forecast combination routinely beats estimated "optimal" weights (the forecast combination puzzle). Combining many weak equity-premium predictors beats any single selected predictor OOS (Rapach-Strauss-Zhou). Picking the recent best strategy is a form of estimated-weight optimization with extreme weights (1/0), so it inherits the worst of the estimation error. No study found shows robust OOS gains from "tournament" strategy selection in crypto.

### Cited Findings
- **Forecast combination puzzle, theory [S]:** Claeskens, Magnus, Vasnev & Wang, *IJF* 32(3), 2016. When combination weights are *estimated*, the combined forecast can be biased and has higher variance. They conclude "there is no guarantee that the 'optimal' forecast combination will be better than the equal-weight case, or even improve on the original forecasts." — [Tinbergen/VU record](https://research.vu.nl/en/publications/the-forecast-combination-puzzle-a-simple-theoretical-explanation-2/); [RePEc WP](https://econpapers.repec.org/RePEc:dgr:uvatin:20140127)
- **Empirical counterpart:** Smith & Wallis (2009, *Oxford Bulletin of Econ. & Stat.*) [K]. A 50-year review places Claeskens et al. as the theoretical explanation of this empirical finding [S]. — [Wang, Hyndman, Li et al., "Forecast combinations: an over 50-year review," arXiv 2205.04216](https://arxiv.org/pdf/2205.04216)
- **Contested nuance [S]:** Elliott (UCSD) argues the puzzle also needs the gains from optimal weights to be *small* to begin with, not only estimation error. — [Elliott, "Combination" (UCSD)](https://econweb.ucsd.edu/~gelliott/Combination.pdf)
- **Rapach, Strauss & Zhou (2010, *RFS* 23(2):821–862) [S]:** model uncertainty and instability "seriously impair" individual predictive regressions. Combining forecasts gives statistically and economically significant OOS gains over the historical average, consistently over time, and greatly reduces forecast volatility. — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v23y2010i2p821-862.html)
- **Welch & Goyal (2008) [S]:** many in-sample equity-premium predictors fail OOS against the historical mean. This is the motivating "selection fails" fact. — cited in [Rapach et al. record](https://profiles.wustl.edu/en/publications/out-of-sample-equity-premium-prediction-combination-forecasts-and/)
- **Neely, Rapach, Tu & Zhou (*Management Science*) [S]:** technical indicators have IS and OOS predictive power comparable to macro variables, and combining them helps. — [WUSTL profile](https://profiles.wustl.edu/en/publications/forecasting-the-equity-risk-premium-the-role-of-technical-indicat/)
- **DeMiguel, Garlappi & Uppal (2009, *RFS* 22(5):1915–1953) [K]:** in their tests, none of 14 optimizing models consistently beat 1/N OOS in Sharpe, certainty equivalent or turnover. The estimation window needed for mean-variance to beat 1/N is about 3,000 months for 25 assets. — [doi:10.1093/rfs/hhm075](https://doi.org/10.1093/rfs/hhm075). Verify exact figures.
- **Timmermann (2006), "Forecast Combinations," *Handbook of Economic Forecasting* Vol. 1 ch. 4 [K]:** simple combinations are robust to structural breaks and model instability. Selecting a single "best" model is fragile when relative performance shifts. — [doi:10.1016/S1574-0706(05)01004-9](https://doi.org/10.1016/S1574-0706(05)01004-9)
- **Crypto ensembles, voting vs single agents (FinRL contests) [S]:** majority-vote ensembles of DQN agents gave higher Sharpe than single agents on OOS crypto. The test window is very short, so this is weak evidence. — [arXiv 2501.10709](https://arxiv.org/pdf/2501.10709); [arXiv 2504.02281](https://arxiv.org/pdf/2504.02281)

### Inferences
- A "master brain" that picks one strategy per regime is the high-variance end of the combination spectrum. The null to beat is the **equal-weight blend of all candidate strategies with volatility targeting**. The brain should be adopted only if it beats that blend on a pre-registered OOS test with costs, after a multiple-testing correction (see Q4).
- A defensible middle ground is **shrinkage**: regime-conditional *tilts* around equal weights, for example ±20%, rather than hard 1/0 selection. This matches Nystrup's finding that probability-weighted exposure matches hard switching with less turnover.

### Gaps
- I did not find peer-reviewed studies that directly test "pick last-N-month best trading strategy" persistence in crypto. Dynamic model averaging (Raftery-style forgetting factors) in crypto trading was not reviewed this session.

---

## Q3. Ensembles and stacking in trading ML: robustness vs single models

### Takeaway
Ensembles usually reduce variance and are more robust than single models, and this is consistent with the combination literature. However, the crypto-specific ensemble papers are mostly short-window, often deep-RL, and some report implausibly high Sharpe ratios. Their headline numbers should not be trusted without replication.

### Cited Findings
- An LSTM/GRU ensemble long-short crypto strategy reports OOS Sharpe after costs of 3.23 (LSTM) and 3.12 (GRU), vs 1.33 for buy-and-hold. (*Journal of Finance and Data Science*, Nov 2022) [S]. The very high Sharpe should be treated as suspicious until replicated. — [DOAJ record](https://doaj.org/article/cfc09801314441198e3e1c92a3914e54)
- A stacking/blending study of generative and discriminative classifiers for crypto direction uses purged walk-forward CV. The snippet did not show cost or P&L data. — [arXiv 1902.07855](https://arxiv.org/abs/1902.07855)
- A mixture-distribution ensemble of deep RL agents for intraday crypto claims significant OOS improvement over a DRL benchmark and B&H. Costs were not visible in the snippet [S]. — [arXiv 2309.00626](https://ar5iv.labs.arxiv.org/html/2309.00626)
- Gu, Kelly & Xiu (2020, *RFS* 33(5)) [K]: in equities, neural-net *ensembles* (averaging across random seeds) gave the best OOS R² in ML return prediction. Ensembling is used as a variance-reduction device. — [doi:10.1093/rfs/hhaa009](https://doi.org/10.1093/rfs/hhaa009)

### Inferences
- Seed-averaging, bagging and simple averaging of heterogeneous models are low-risk improvements. Stacking (a learned meta-model) adds a second layer of estimated weights and so re-introduces the combination-puzzle problem. Prefer simple averaging unless stacking wins on a pre-registered OOS test.

### Gaps
- No rigorous crypto study was found that compares stacking vs averaging vs a single best model with explicit costs over multiple market cycles.

---

## Q4. Multiple testing and backtest overfitting: PBO/CSCV, Deflated Sharpe, Harvey-Liu-Zhu, White RC / Hansen SPA, FDR; trial registries

### Takeaway
When many strategies or regime rules are searched, the best backtest is upward-biased by construction. Several tools exist and all require the **full count of trials**:
- PBO/CSCV: the probability that the IS-best configuration ranks below the median OOS.
- The Deflated Sharpe Ratio.
- The Harvey-Liu-Zhu t > 3 hurdle and Sharpe haircuts.
- White's Reality Check and Hansen's SPA.
- FDR or step-down methods.

Hence the need for a trial registry that logs every experiment, including failed ones. Crypto technical-rule studies that apply these corrections give **mixed** results.

### Cited Findings
- **PBO/CSCV [S]:** Bailey, Borwein, López de Prado & Zhu, *Journal of Computational Finance* 20(4) (2017), doi:10.21314/JCF.2016.322. Standard hold-out is "unreliable and inaccurate" for investment backtests. CSCV is a model-free, nonparametric estimate of PBO. — [SSRN 2326253](https://papers.ssrn.com/abstract=2326253); [Risk.net](https://www.risk.net/journal-of-computational-finance/2471206/the-probability-of-backtest-overfitting); [eScholarship PDF](https://escholarship.org/content/qt4w1110bb/qt4w1110bb.pdf). An R implementation exists. — [CRAN pbo](https://packages.oit.ncsu.edu/cran/web/packages/pbo/readme/README.html)
- **CPCV [S]:** combinatorial purged CV gives many OOS paths and so a *distribution* of Sharpe. Walk-forward gives a single path, which cannot distinguish a lucky split from a robust one. — [fynance docs](https://fynance.readthedocs.io/en/latest/generated/fynance.data.combinatorial_purged_cv.html); [Wikipedia: Purged cross-validation](https://en.wikipedia.org/wiki/Purged_cross-validation). These are secondary sources. The primary source is López de Prado, *Advances in Financial Machine Learning* (Wiley 2018) [K].
- **Deflated Sharpe Ratio [K]:** Bailey & López de Prado, *Journal of Portfolio Management* 40(5) 2014. It corrects the Sharpe ratio for the number of trials, the variance of trial Sharpes, non-normality and track length. — [SSRN 2460551](https://papers.ssrn.com/abstract=2460551)
- **Harvey, Liu & Zhu (2016, *RFS* 29(1):5–68) [K]:** given the hundreds of factors tested, a new factor should clear t > 3.0, not 2.0. — [doi:10.1093/rfs/hhv059](https://doi.org/10.1093/rfs/hhv059). Harvey & Liu, "Backtesting," *JPM* 2015, gives Sharpe "haircuts" for multiple testing [K]. — [SSRN 2345489](https://papers.ssrn.com/abstract=2345489)
- **White (2000) Reality Check [K]:** *Econometrica* 68(5):1097–1126. — [doi:10.1111/1468-0262.00152](https://doi.org/10.1111/1468-0262.00152). **Hansen (2005) SPA [K]:** *JBES* 23(4):365–380. It is less sensitive to poor or irrelevant alternatives than the RC. — [doi:10.1198/073500105000000063](https://doi.org/10.1198/073500105000000063). A newer GLR-based SPA test claims more power than Hansen SPA [S]. — [Cai, Jiang & Zhang, Xiamen WP](https://soe.xmu.edu.cn/info/5401/570214.htm)
- **Sullivan, Timmermann & White (1999, *JF* 54(5)) [K]:** the best of about 8,000 technical rules on the DJIA was significant 1897–1986 after the RC, but had no OOS edge in 1987–1996. This is the canonical "decay after discovery" result. — [doi:10.1111/0022-1082.00163](https://doi.org/10.1111/0022-1082.00163)
- **Crypto, multiple-testing-corrected technical rules (contested):**
  - Hudson & Urquhart (*Annals of OR* 297, 2021) [S]: about 15,000 rules on 2 BTC markets plus 3 other coins. They find predictability and profitability in all classes after multiple-hypothesis correction, with break-even costs well above typical crypto costs. **But there was no predictability for Bitcoin in the OOS period**, while some remained in other coins. — [IDEAS](https://ideas.repec.org/a/spr/annopr/v297y2021i1d10.1007_s10479-019-03357-1.html); [Hull repository](https://hull-repository.worktribe.com/output/2328042)
  - Anghel (*Finance Research Letters* 39, 2021) [S]: with the RC applied, significant excess returns from crypto rules were *rarely* achieved. The returns mostly loaded on market beta. — [IDEAS](https://ideas.repec.org/a/eee/finlet/v39y2021ics1544612320304414.html)
  - A 2023 *J. Accounting & Finance* study on BTC/USDT and ETH/USDT [S]: no profitable strategies in either period after data-snooping adjustment. — [articlegateway](https://articlegateway.com/index.php/JAF/article/view/6453)
  - An Erasmus thesis on 5-min BTC [S]: many rules were profitable after snooping and cost adjustment, but profitability was unstable and declined over time. This is a thesis, so lower weight. — [EUR thesis](https://thesis.eur.nl/pub/41546/Bakker.pdf)
- **FDR [K]:** Barras, Scaillet & Wermers (2010, *JF* 65(1)) applied FDR to mutual-fund alphas. — [doi:10.1111/j.1540-6261.2009.01527.x](https://doi.org/10.1111/j.1540-6261.2009.01527.x). Romano & Wolf (2005, *Econometrica*) give the StepM step-down method [K]. — [doi:10.1111/j.1468-0262.2005.00615.x](https://doi.org/10.1111/j.1468-0262.2005.00615.x)

### Inferences
- A regime brain multiplies the trial count: (number of regime definitions) × (number of strategies) × (hyperparameters) × (mapping choices). Every one of these must go into the trial registry, and the DSR or PBO must be computed on the *full* count. Otherwise the brain's backtest is not evidence.
- Practical registry fields: trial id, timestamp, code and data SHA, hypothesis, parameter grid size, IS/OOS split, cost model, all metrics (including failures), and a decision. N_trials and the variance of trial Sharpes feed directly into the DSR.
- The crypto pattern matches Sullivan et al.: rules that pass multiple-testing tests IS often fail in later OOS windows, especially for BTC as the market matured.

### Gaps
- No published crypto study was found that reports PBO/CSCV for regime-switching or meta-selection systems specifically.
- The Arian, Norouzi & Seco (2024) paper comparing CPCV with walk-forward was searched for but not retrieved. It is unverified, so it was not cited.

---

## Q5. Strategy discovery via genetic programming / automated search in crypto: OOS survival

### Takeaway
GP papers in crypto often report OOS profitability, but they are typically single-market, short-sample, and rarely apply multiple-testing correction or test on distant OOS periods. The broader GP/GA literature warns that rules profitable just after the training window decay in more distant OOS periods and often fail after realistic costs. I found **no quantified "survival rate"** (the fraction of discovered rules still profitable OOS) for crypto.

### Cited Findings
- Ha & Moon (2018, *Memetic Computing*) [S]: GP found crypto technical patterns that were "profitable and frequent" OOS and useful in a portfolio simulation. — [GP bibliography](https://gpbib.cs.ucl.ac.uk/gp-html/ha_Memetic_Computing.html)
- A 2021 GP study on 5 trend indicators for BTC (2017–2020) claims to beat buy-and-hold. Its peer-review status is unclear. — [Academia.edu](https://www.academia.edu/78030439/A_Real_Time_Adaptive_Bitcoin_Trading_System_Using_Genetic_Programming)
- Deng et al. (2012), on GA rules in FX: rules can look profitable in *near* OOS, but "it is hard to believe" they profit in *distant* OOS periods. — [GP bibliography](https://gpbib.cs.ucl.ac.uk/gp-html/DENG_2012_PCS.html)
- An intraday GP/rule study (1999): no excess returns after realistic transaction costs. — [GP bibliography 99-016](https://gpbib.cs.ucl.ac.uk/gp-html/99-016.html)
- Agapitos et al. (PPSN 2010) address "evolutionary learning of technical rules without data-mining bias." Detailed results were not retrieved. — [GP bibliography](https://gpbib.cs.ucl.ac.uk/gp-html/agapitos_etal_ppsn2010.html)
- A study of GP rules on the Shenzhen index reports significant OOS excess returns after costs. These are non-crypto results. — [IDEAS, Computational Economics 43(3) 2014](https://ideas.repec.org/a/kap/compec/v43y2014i3p301-311.html)
- In FX technical portfolios, mean Sharpe fell from 0.66 IS to 0.06 OOS, with no survival after modest costs [S]. This is a figure from the search summary and the source paper was not identified precisely. Treat it as unverified.

### Inferences
- Automated search is the most extreme multiple-testing case. Any GP or tournament output must pass a DSR or PBO computed with the full population size, plus a *distant*, untouched holdout (for example, the most recent 12+ months, locked by SHA).

### Gaps
- No systematic crypto meta-study of GP rule OOS survival rates was found.

---

## Q6. "No trade" / abstention: do confidence thresholds improve net returns?

### Takeaway
Selective prediction reliably raises *accuracy on the trades taken*, at the cost of coverage. The evidence that it raises *net returns* is thin and mixed. In the main trading paper found, some selective models turned negative Sharpe positive and others did not. Accuracy gains did not map one-to-one into profit.

### Cited Findings
- **Chalkidis & Savani, "Trading via Selective Classification" (Univ. of Liverpool, ACM ICAIF 2021) [F]:** — [arXiv 2110.14914](https://ar5iv.labs.arxiv.org/html/2110.14914); [Liverpool repository](https://livrepository.liverpool.ac.uk/3142465/)
  - Setup: 5 CME metal futures, 30-minute bars from 2011 to 2019 (about 97k bars), walk-forward and fully OOS, with slippage of 0–0.5 ticks. The abstention threshold was set with SGR (Geifman & El-Yaniv) on max class probability.
  - Binary accuracy rose from about 51–54% to 52–57% at 37–63% coverage. For example, logistic regression went from 53.50% to 55.79% at 47.5% coverage.
  - Sharpe at 0.3-tick slippage: selective logistic regression was positive on all 4 feature sets (0.02–0.28), while the non-selective version was mixed (−0.08 to 0.16). Selective feed-forward net: 0.33 and 0.15 on two sets. **LSTMs were negative in every configuration**, and many configurations were unprofitable.
  - Ternary selective models had higher accuracy but *worse* backtests than binary selective models.
  - The text and the table disagree on random-forest results. The authors call it a "proof of concept."
- **Deep Gamblers (Liu et al., NeurIPS 2019) [S]:** an abstention loss derived from the gambling doubling-rate, a portfolio-theory link. It is a general ML method, not a trading test. — [NeurIPS 2019](https://papers.nips.cc/paper/2019/hash/0c4b1eeb45c90b52bfb9d07943d855ab-Abstract.html)

### Inferences
- Abstention mainly helps through cost avoidance: fewer trades, each with a higher hit rate. The threshold should therefore be set on **expected net P&L (edge minus cost)**, not on accuracy, and chosen on validation data only. Threshold choice is itself a tuned parameter and must go into the trial registry.

### Gaps
- No crypto-specific study of cost-aware abstention with net-return results was found.

---

## Q7. Position sizing from model confidence (calibration, fractional Kelly) and volatility scaling

### Takeaway
- **Volatility scaling** has the strongest support among the simple alternatives in trend and time-series momentum, including crypto TSMOM. For broad equity factors, its OOS and net-of-cost benefit is **contested**.
- **Fractional Kelly** is theoretically justified by estimation error, but this session found little rigorous empirical evidence for confidence-proportional sizing. Most of the material is practitioner or blog-level.
- No solid evidence was found that *probability calibration* of ML signals improves net trading returns.

### Cited Findings
- **Moreira & Muir (2017, *JF* 72(4)) [K]:** volatility-managed factor portfolios give large alphas and Sharpe gains. — [doi:10.1111/jofi.12513](https://doi.org/10.1111/jofi.12513)
- **Cederburg, O'Doherty, Wang & Yan (2020, *JFE* 138(1)) [S/K]:** across 103 equity strategies, volatility-managed versions do *not* systematically beat unmanaged ones OOS. The IS alphas are not implementable in real time because of unstable spanning regressions. — [Alpha Architect summary](https://alphaarchitect.com/does-portfolio-timing-based-on-volatility-signals-outperform-buy-and-hold/); [Lehigh PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf)
- **Barroso & Detzel:** reported as finding that the gains do not survive transaction costs [S, secondary]. — [via LBS paper](https://lbsresearch.london.edu/id/eprint/3716)
- **DeMiguel, Martín-Utrera & Uppal (*JF* 2024) [S]:** a *conditional multifactor* volatility-managed portfolio beats its unconditional counterpart OOS and net of costs. The debate is therefore **unresolved**. — [LBS repository](https://lbsresearch.london.edu/id/eprint/3716)
- **Volatility scaling in TSMOM:** Moskowitz, Ooi & Pedersen (2012, *JFE* 104(2)) [K]. — [doi:10.1016/j.jfineco.2011.11.003](https://doi.org/10.1016/j.jfineco.2011.11.003)
- **Crypto TSMOM and costs:**
  - Han, Kang & Ryu (AUT) [S]: time-series momentum in crypto is strong, cross-sectional momentum is weak. Many momentum portfolios are liquidated once costs and daily swings are included. — [AUT PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf)
  - Man Group (practitioner) [S]: trend-following works in crypto. Peak risk-adjusted returns come at about 10–15 coins, after which costs and liquidity outweigh diversification. — [Man Group, "In crypto we trend"](https://www.man.com/insights/in-crypto-we-trend)
  - A single-author 2026 arXiv preprint [S] reports an OOS Sharpe of 2.41 (2022–2024) and a volatility-scaled TSMOM Sharpe of 1.83 vs 0.54–0.65 unscaled. **It is unreviewed and its table labels are inconsistent, so treat it as low reliability.** — [arXiv 2602.11708](https://arxiv.org/pdf/2602.11708)
  - Liu & Tsyvinski (2021, *RFS* 34(6), "Risks and Returns of Cryptocurrency") [K]: documents time-series momentum in crypto. — [doi:10.1093/rfs/hhaa113](https://doi.org/10.1093/rfs/hhaa113)
- **Kelly:**
  - MacLean, Thorp & Ziemba (2010, *Quantitative Finance* 10(7)) [K], "good and bad properties" of Kelly: full Kelly gives very large drawdowns, and fractional Kelly trades growth for security. — [doi:10.1080/14697688.2010.506108](https://doi.org/10.1080/14697688.2010.506108)
  - Practitioner sources [S, low quality] note that a 100-trade win-rate estimate has about ±5% standard error. An estimate of 60% when the truth is 55% makes full Kelly overbet by about 50%. "Half Kelly keeps about 75% of growth" is a common rule of thumb; for a log-utility Gaussian bet it follows from growth ∝ f(2−f). — [LuxAlgo](https://www.luxalgo.com/library/concept/kelly-criterion/)

### Inferences
- Volatility targeting is the cheapest, best-supported baseline and should be in every comparison arm (static ensemble + vol-target vs regime brain + vol-target).
- If sizing uses model confidence, the probabilities must first be calibrated on held-out data (reliability diagram, Brier score) and then capped (for example, ≤ ¼–½ Kelly). This is a design principle from estimation-error logic, not an empirically proven return enhancer.

### Gaps
- No peer-reviewed crypto evidence was found on confidence-proportional or calibrated-Kelly sizing beating fixed or volatility-targeted sizing net of costs.
- No peer-reviewed crypto-specific volatility-managed-portfolio OOS study was retrieved. The crypto evidence for volatility scaling is practitioner material plus an unreviewed preprint.

---

### Overall bottom line for the report writer (inference, not a cited claim)
The evidence hierarchy for crypto, from most to least supported OOS:
1. Diversified time-series momentum or trend following with volatility targeting.
2. Equal-weight or simple-average ensembles of strategies and models.
3. Regime filters used as soft, persistent risk-off overlays. These mainly reduce drawdown.
4. Hard regime-to-strategy switching or "pick the recent winner" selection. This has the weakest evidence, the largest multiple-testing burden, and costs from lag and whipsaw.

A "master brain" should be judged against (1) + (2) under a pre-registered protocol that includes DSR/PBO on the full trial count.
