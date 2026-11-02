# AI/ML Methods for a Daily Crypto Long-Short Allocation System — Evidence Base

(Notes are in English for citation precision; the final report should be in Hindi per project rules. Researched 2026-10-16, ~22 tool calls. Items marked "abstract-only" were not checked against full text.)

Our context: HistGradientBoosting classifiers, target = "beats cross-sectional median over next 5d / 1d", AUC ~0.56-0.57 vs shuffled 0.50; new features (futures basis/funding, bear data) failed; PBO 65%.

## 1. Cross-sectional ML return prediction in crypto (and equity background)

### Takeaway
The best-documented crypto cross-sectional ML study (Cakici et al. 2024) finds that model complexity adds little (OLS often matches or beats trees and NNs), signal comes from a few simple characteristics (price, past alpha, illiquidity, momentum), and alpha lives mostly in small, illiquid, volatile coins. Daily-horizon ML in the top-100 coins gives only ~53-54% accuracy; claimed high post-cost Sharpes (3+) are single-paper results that no one has independently replicated.

### Cited Findings
**Crypto (primary evidence)**
- Cakici, Shahzad, Będowska-Sójka & Zaremba, "Machine learning and the cross-section of cryptocurrency returns", *International Review of Financial Analysis* vol. 94 (2024), art. 103244. Simplest methods work best: OLS visibly outperforms regression trees and neural networks — [RePEc](https://ideas.repec.org/a/eee/finana/v94y2024ics1057521924001765.html); [ICM open repository](https://open.icm.edu.pl/handle/123456789/25543)
- Same paper: predictability comes mainly from a handful of simple characteristics (market price, past alpha, illiquidity, momentum). Eight ML models were tested. — [docshare copy/FAQ](https://docshare.wps.com/document/machine-learning-and-the-cross-section-of-cryptocurrency-returns/119387/_payload.json); [ICM](https://open.icm.edu.pl/handle/123456789/25543)
- Same paper: despite high turnover, most ML strategies stay profitable after trading costs, BUT the alphas are concentrated in hard-to-trade assets and depend critically on extreme returns of small, illiquid, volatile coins. — [RePEc](https://ideas.repec.org/a/eee/finana/v94y2024ics1057521924001765.html); [docshare](https://docshare.wps.com/document/machine-learning-and-the-cross-section-of-cryptocurrency-returns/119387/_payload.json)
- Same paper: unlike equities, the abnormal returns come from the LONG leg and persist over time (i.e., the short leg adds little). — [docshare](https://docshare.wps.com/document/machine-learning-and-the-cross-section-of-cryptocurrency-returns/119387/_payload.json)
- Jaquart, Köpke & Weinhardt, "Machine learning for cryptocurrency market prediction and trading", *J. Finance and Data Science* 8 (2022) 331-352: predicts binary RELATIVE daily movements of the 100 largest coins (close to our "beats the median" target). Average accuracy 52.9%-54.1%; 57.5%-59.5% on the 10% most confident predictions per class and day. — [DOAJ](https://doaj.org/article/cfc09801314441198e3e1c92a3914e54); [KIT repository](https://publikationen.bibliothek.kit.edu/1000153546/149798497)
- Same paper: LSTM and GRU ensemble long-short portfolios report annualized OOS Sharpe after transaction costs of 3.23 and 3.12, vs. buy-and-hold 1.33 (abstract-only; cost assumptions and survivorship handling of "100 largest" not verified). — [DOAJ](https://doaj.org/article/cfc09801314441198e3e1c92a3914e54)
- Jaquart, Dann & Weinhardt (2021, JFDS vol. 7), bitcoin 1-60 minute horizons: RNNs and gradient boosting classifiers best; technical features most relevant; predictability increases with longer horizons; a quantile long-short strategy has large gross returns but NEGATIVE returns after transaction costs due to short holding periods. — [KIT](https://publikationen.bibliothek.kit.edu/1000150665); search summary of [KIT PDF](https://publikationen.bibliothek.kit.edu/1000150665/149388567)
- Fieberg, Liedtke, Poddig, Walker & Zaremba, "A Trend Factor for the Cross-Section of Cryptocurrency Returns" (*JFQA*, 2025): ML-aggregated technical-indicator signal "CTREND" on 3,000+ coins; abstract claims robustness across subperiods, market states, designs, and survival after transaction costs (full OOS design not verified; PDF link returned 404). — [JFQA page](https://jfqa.org/?p=9800); [Cambridge](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178)
- Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency", *Journal of Finance* 2022 (77:1133-1177, DOI 10.1111/jofi.13119): three factors (crypto market, size, momentum) capture the cross-section; weekly long-short quintile sorts; 10 characteristic strategies all explained by the 3-factor model. (Non-ML baseline, weekly rebalancing.) — [NBER w25882](https://www.nber.org/papers/w25882.pdf); [SSRN](https://papers.ssrn.com/abstract=3379131); [Yale Cowles PDF](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
- Mercik, Zaremba & Demir: a 36-factor crypto "factor zoo" is absorbed by 2-3 factors. — search summary of [ICM repository](https://open.icm.edu.pl/bitstreams/21636cf6-61df-4fb5-9ae4-4195d592cd26/download)
- Conflicting newer claim: a 2026 lecture abstract (Taiwan, Tunghai Univ.) reports gradient boosting/XGBoost more than triples the Sharpe of an OLS benchmark in value-weighted crypto portfolios — opposite to Cakici on complexity. Abstract only, not peer-review-verified. — [stat.thu.edu.tw](https://stat.thu.edu.tw/web/news/detail.php?id=891)

**Equity background (clearly not crypto)**
- Gu, Kelly & Xiu, "Empirical Asset Pricing via Machine Learning", RFS 2020: trees and neural nets best, due to nonlinear interactions; dominant predictors are momentum, liquidity, volatility; ML forecasts in some cases double performance of regression-based strategies. — [NBER w25398](https://www.nber.org/papers/w25398.pdf); [SSRN](https://papers.ssrn.com/abstract=3306110)
- GKX: penalized linear models recover only ~0.26% monthly OOS R² (monthly-level predictability is tiny even in the best equity study). — [Mirova summary](https://www.research-center.mirova.com/en/research-library/Empirical-Asset-Pricing-via-Machine-Learning)

### Inferences
- Our AUC 0.56-0.57 is in line with (arguably slightly better than) the 53-54% daily accuracy in Jaquart-Köpke-Weinhardt. The literature does not suggest that a model swap (GBM→NN) will lift this much; Cakici even finds OLS ≥ trees/NNs in crypto.
- Because Cakici finds alpha concentrated in illiquid small coins and in the long leg, a 10-coin liquid universe with a symmetric short book should expect WEAKER results than published headline numbers. The short leg is the least-supported part of a crypto long-short book.
- Daily rebalancing is where costs bite hardest (Jaquart-Dann-Weinhardt: gross positive → net negative at short horizons). Weekly rebalancing (Liu-Tsyvinski-Wu convention) is the better-supported frequency.
- High-Sharpe claims (3+) from a "100 largest coins" universe should be flagged for possible survivorship (constituent selection with hindsight) until full text is checked.

### Gaps
- Could not retrieve full texts of Cakici et al. (403) or CTREND (404): exact sample period, coin count, OOS window, rebalancing frequency, Sharpe per model and net-of-cost numbers remain unverified.
- Akyildirim et al. (crypto ML classification) not retrieved in this pass.
- No study found that measures decay of crypto ML signals in liquid large-cap coins specifically at weekly frequency; Cakici claims persistence, not decay.
- Exact GKX NN OOS R² and long-short Sharpe numbers not verified (a 2018 draft says Sharpe >2.0 — not confirmed vs published version).

## 2. Learning-to-rank vs classification/regression for long-short portfolios

### Takeaway
The Oxford-Man LTR paper (Poh, Lim, Zohren, Roberts) reports LambdaMART Sharpe ~2.16 vs ~0.27 for regression-then-rank MLP on NYSE stocks, but it is equity, monthly, gross of costs, has no classification baseline and no significance tests, and is unreplicated. The improvement in ranking metrics is tiny (NDCG ~0.55→0.58). Treat LTR as a cheap experiment (LightGBM/XGBoost "lambdarank" objective), not a proven fix.

### Cited Findings
- Poh, Lim, Zohren & Roberts, "Building Cross-Sectional Systematic Strategies by Learning to Rank" (arXiv 2012.07149, Oxford-Man): NYSE stocks 1980-2019, monthly rebalance, 100 long/100 short, 15% vol target, price-only features (3/6/12m returns, MACD), target = 21-day return; models re-tuned every 5 years. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2012.07149); [arXiv](https://arxiv.org/pdf/2012.07149)
- Results (Sharpe, vol-scaled): Random 0.155, JT momentum 0.551, Baz MACD 0.696, MLP regression 0.265, RankNet 1.502, LambdaMART 2.156, ListNet 1.970, ListMLE 1.611. Max drawdown LambdaMART 0.231 vs MLP 0.641. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2012.07149)
- Ranking metrics: Kendall tau 0.032 (LambdaMART) vs 0.008 (MLP); NDCG@100 longs 0.576 vs 0.550. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2012.07149)
- Caveats: all returns WITHOUT transaction costs, no breakeven analysis; no statistical tests; no classification baseline; 50 HyperOpt iterations with no sensitivity reported. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2012.07149)
- SOTAVerified lists the paper as unverified / not reproduced. — search summary of [sotaverified.org](https://sotaverified.org/papers/building-cross-sectional-systematic)
- Follow-up: Transformer re-ranking on 31 currencies improved Sharpe ~20% over the original LTR methods (same group, arXiv 2105.10019). — [arXiv](https://arxiv.org/abs/2105.10019v2)

### Inferences
- Our current setup (binary "beats median") is essentially a pointwise classifier — the category the LTR paper argues is weakest. A pairwise/listwise objective directly optimizes the order used to build long and short books, so it is the most literature-motivated model-side change. But the gap between tiny NDCG gains and huge Sharpe gains in that paper is a red flag for in-sample tuning luck; any test must be pre-registered and counted in our PBO trial count.
- With only 10 coins per day, listwise LTR has very few items per query; benefits shown with ~1,000 stocks may not transfer.

### Gaps
- No crypto-specific LTR study with costs was found.
- No independent replication of the Poh et al. numbers found.

## 3. Meta-labeling for sizing/filtering

### Takeaway
Meta-labeling (López de Prado 2017; formalized by Joubert and co-authors in JFDS) separates "side" from "size": a secondary model estimates the probability the primary signal is right and sizes accordingly. Peer-reviewed evidence is mostly methodological/synthetic: calibration helps fixed sizing functions, and ensembles help most when data has multiple regimes. No crypto OOS evidence found.

### Cited Findings
- Meta-labeling was developed in 2017 by Marcos López de Prado; core idea: separate trade direction (side) from trade sizing. — [Wikipedia (secondary)](https://en.wikipedia.org/wiki/Meta-Labeling)
- Joubert, "Meta-Labeling: Calibration and Position Sizing" (JFDS): the secondary model's output is read as probability of a profitable trade; fixed position-sizing methods improve significantly with probability calibration, while methods that learn their sizing function from training data gain no significant benefit. — search summary of [Joubert LinkedIn listing](https://ae.linkedin.com/in/jacquesjoubert) and [Wikipedia](https://en.wikipedia.org/wiki/Meta-Labeling) (authorship/venue not verified on journal site)
- Thumm, Barucca & Joubert, "Ensemble Meta-Labeling", JFDS 5(1):10-26 (2023), DOI 10.3905/jfds.2022.1.114: ensembles help most when data contains multiple regimes and is nonlinear. — [UCL Discovery](https://discovery-pp.ucl.ac.uk/id/eprint/10169066)
- Analogous evidence in crypto: Jaquart-Köpke-Weinhardt find accuracy rises from ~53-54% to ~57.5-59.5% when only the top-10% most confident predictions are used — i.e., confidence-based filtering (the meta-labeling idea) adds hit-rate. — [DOAJ](https://doaj.org/article/cfc09801314441198e3e1c92a3914e54)

### Inferences
- For us, meta-labeling = use calibrated P(beats median) to size positions (and to skip low-confidence days), rather than equal-weight top/bottom-k. Calibration (isotonic/Platt) on OOS folds is a cheap prerequisite.
- Higher hit-rate on confident subsets comes with fewer trades, so turnover drops too — helpful for costs at daily frequency.

### Gaps
- Joubert's foundational "Meta-Labeling: Theory and Framework" (JFDS 2022) full text not retrieved; no real-data crypto OOS meta-labeling study found.

## 4. Regime detection (HMM / Markov switching) and regime-conditioned allocation

### Takeaway
HMMs identify bull/bear/calm states in BTC/ETH returns in-sample, and one peer-reviewed paper (Figà-Talamanca et al. 2021) links HMM specifications to profitable strategies, but no rigorous crypto study was found showing regime-conditioned allocation improves OOS drawdowns after costs. Evidence is weak.

### Cited Findings
- Figà-Talamanca, Focardi & Patacca (2021, *North American J. of Economics and Finance*): finite-state HMM for BTC, ETH, LTC, XMR, Jan 2016-Oct 2019; specifications chosen by OOS forecasting; claim profitable strategies (drawdown not reported in snippet). — [EconPapers](https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000577)
- "Exploring the Predictability of Cryptocurrencies via Bayesian Hidden Markov Models" (arXiv 2011.03741): a four-state HMM separates bull, bear and calm regimes for Bitcoin; focus is predictability, not allocation. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2011.03741)
- Thumm-Barucca-Joubert: ensemble learners extract regimes better and help most in multi-regime nonlinear data (indirect regime evidence). — [UCL Discovery](https://discovery-pp.ucl.ac.uk/id/eprint/10169066)
- Equity/other-asset background only: an NCCU thesis on Taiwan equities/US bonds reports HMM regime allocation raised Sharpe, Sortino and drawdown-adjusted return (thesis, not peer-reviewed). — [NCCU](https://ah.lib.nccu.edu.tw/handle/140.119/141066)

### Inferences
- Regime models are best used as a gross-exposure / long-short-mix switch (e.g., reduce net long or overall gross in a "bear/high-vol" state), not as another alpha model. Given our failed "bear data" feature experiment, adding regime as an input feature is less promising than using it as an exposure overlay — but this is inference, not tested evidence.
- HMM state labels are smoothed with future data if fit on the full sample; must use filtered (forward-only) probabilities in walk-forward.

### Gaps
- No peer-reviewed crypto study found showing regime-conditioned allocation reduces OOS drawdown net of costs. Markov-switching GARCH crypto papers not retrieved.

## 5. Reinforcement learning for crypto portfolio allocation

### Takeaway
RL crypto results are the least reliable category: the classic Jiang-Xu-Liang (2017) paper reports ≥4x returns in 50 days on Poloniex 30-minute data (short test windows, bull market); robustness benchmarks find DRL agents generalize poorly; and even the FinRL-group paper that explicitly controls backtest overfitting via PBO shows all agents LOSING money in its 2-month test. Not recommended as the core allocator.

### Cited Findings
- Jiang, Xu & Liang (arXiv 1706.10059, 2017): CNN/RNN/LSTM policy networks on Poloniex, 30-minute periods, three backtests; claims at least 4-fold returns in 50 days even with 0.25% commission. — [arXiv](https://arxiv.org/abs/1706.10059)
- Velay et al. (arXiv 2306.10950): most DRL portfolio algorithms not robust; strategies generalize poorly and degrade quickly in backtesting. — [arXiv](https://www.arxiv.org/abs/2306.10950)
- Zhang, Munos & Bengio (Google, 2018): standard RL agents overfit in various ways; call for more careful evaluation protocols. — [Google Research](https://research.google/pubs/a-study-on-overfitting-in-deep-reinforcement-learning/)
- Preprint (RiskLens Trader, Research Square): large seed variance — one PPO seed strongly positive OOS while another loses money; single-seed reporting can materially overstate RL performance. — [Research Square](https://assets-eu.researchsquare.com/files/rs-9824202/v1_covered_2dbf3593-a58c-4edb-bb2a-bb85e54443cb.pdf)
- Gort et al., "Deep RL for Cryptocurrency Trading: Practical Approach to Address Backtest Overfitting" (arXiv 2209.05559): 10 coins, 5-min bars, train Feb-Apr 2022, test May 1-Jun 27 2022 (~57 days); combinatorial CV (N=5, k=2); agents with PBO ≥10% rejected; cost 0.3%, slippage ignored. Test returns: equal-weight −47.78%, PPO (CPCV, PBO 8.0%) −34.96%, PPO walk-forward (PBO 17.5%) −49.39%, PPO K-fold (PBO 7.9%) −55.54%, TD3 (PBO 9.6%) −59.08%, SAC (PBO 21.3%) −59.48%. No Sharpe reported. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2209.05559); [arXiv](https://arxiv.org/pdf/2209.05559)
- Same paper's motivation: earlier DRL crypto studies optimistically reported backtest profits likely suffering from false positives due to overfitting. — [arXiv abstract](https://arxiv.org/abs/2209.05559v1)

### Inferences
- Even with PBO screening, a low-PBO agent (TD3, 9.6%) was among the worst — PBO screening is necessary but not sufficient.
- For a 10-coin daily system with ~2,000-3,000 daily observations, RL sample efficiency is a major problem; supervised ranking + explicit sizing rules is more defensible.

### Gaps
- No independent audit of FinRL crypto results found; Jiang-Xu-Liang per-model numbers not retrieved.

## 6. Ensembles / model averaging across horizons; score vs rank averaging

### Takeaway
Direct evidence is thin. Ensembles show up in the better crypto results (Jaquart-Köpke-Weinhardt's best portfolios are LSTM/GRU ensembles) and in meta-labeling research (ensembles help in multi-regime data), but no crypto study comparing score averaging vs rank averaging was found.

### Cited Findings
- Best long-short Sharpes in Jaquart-Köpke-Weinhardt come from LSTM and GRU ENSEMBLE models (3.23 / 3.12 after costs, abstract). — [DOAJ](https://doaj.org/article/cfc09801314441198e3e1c92a3914e54)
- Ensemble meta-labeling helps most with multiple regimes and nonlinear data; different fusion strategies may aid model selection. — [UCL Discovery](https://discovery-pp.ucl.ac.uk/id/eprint/10169066)
- CTREND aggregates many technical signals via ML into one factor that is robust across subperiods/market states (abstract). — [JFQA](https://jfqa.org/?p=9800)

### Inferences
- Averaging our 1d and 5d models (rank-average of cross-sectional ranks is scale-free and robust to miscalibration; score-average requires calibrated probabilities) is a low-degree-of-freedom ensemble and reduces variance without adding many trials to the PBO count. This is reasoning, not cited evidence.

### Gaps
- No peer-reviewed crypto evidence found for horizon-ensembles or score-vs-rank averaging.

## 7. Overfitting controls used by top institutions

### Takeaway
The standard toolkit — walk-forward, purged/embargoed CV, CSCV-based PBO, Deflated Sharpe Ratio, and multiple-testing hurdles (t > 3.0) — is well documented. Our PBO of 65% means the in-sample-best configuration lands below the OOS median in about two-thirds of splits, which by this framework means the selection process is overfit.

### Cited Findings
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting", *Journal of Computational Finance*: hold-out style methods are unreliable for investment backtests; propose CSCV to estimate PBO. — [SSRN](https://papers.ssrn.com/abstract=2326253); [Risk.net](https://www.risk.net/2471206); [carmamaths PDF](https://carmamaths.org/jon/backtest2.pdf)
- PBO method: split T×N trial-return matrix into S blocks; for each symmetric IS/OOS combination, rank the IS-best trial out of sample; PBO = fraction of splits where it falls below the OOS median. — [LuxAlgo summary](https://www.luxalgo.com/library/concept/probability-of-backtest-overfitting/); consistent with [SSRN abstract](https://papers.ssrn.com/abstract=2326253)
- Deflated Sharpe Ratio (Bailey & López de Prado, JPM 2014): corrects Sharpe for selection bias under multiple testing and non-normal returns. — [Trading Strategy docs (secondary)](https://tradingstrategy.ai/docs/learn/backtesting.html); [LuxAlgo](https://www.luxalgo.com/library/concept/probability-of-backtest-overfitting/)
- Harvey, Liu & Zhu, "...and the Cross-Section of Expected Returns", RFS 29(1):5-68 (2016): 316 factors reviewed; recommend t-statistic > 3.0 (p < ~0.0027) for new factors; argue most claimed findings in financial economics are likely false. — [NBER w20592](https://www.nber.org/papers/w20592); [SSRN](https://papers.ssrn.com/abstract=2513152); [CXO Advisory](https://www.cxoadvisory.com/big-ideas/taming-the-factor-zoo/)
- Combinatorial purged CV used in practice for crypto DRL; walk-forward PPO showed PBO 17.5% vs 8.0% for CPCV in Gort et al. — [ar5iv](https://ar5iv.labs.arxiv.org/html/2209.05559)
- Joubert, "Enhanced Backtesting for Practitioners" (JPM) covers backtesting pitfalls. — search summary of [Joubert LinkedIn](https://ae.linkedin.com/in/jacquesjoubert)

### Inferences
- With PBO 65%, the right response per this literature is to REDUCE the number of configurations searched (fewer, pre-registered variants), use purged/embargoed CV with embargo ≥ label horizon (5 days for the 5d target), report DSR using the true trial count, and rely on forward paper trading as the final gate.
- AUC 0.56-0.57 vs 0.50 shuffled is real skill at the prediction level, but PBO measures the SELECTION of strategy configs; both can be true: some signal exists while the specific chosen portfolio rules are overfit.

### Gaps
- Original DSR paper text not fetched (cited via secondary summaries). López de Prado's AFML purging/embargo chapter not fetched directly. No institution-specific (AQR/Man AHL/Two Sigma) public documents retrieved in this pass.
