# Training, Validating and Backtesting ML Trading Brains on 4H Crypto Bars (long + short, spot + perps)

Scope note: the research budget was limited to about 15 search/fetch calls. Items marked "(canonical, not re-fetched)" are standard references whose existence and core claim I am confident of, but whose text was not opened this session. Verify exact numbers against the primary source before quoting them in a claims file. No 4H-specific peer-reviewed crypto ML study was found. All horizon evidence below comes from 1-minute to 120-minute, hourly or daily studies, so applying it to 4H is an inference.

## 1. Labeling: fixed-horizon, triple-barrier, cross-sectional rank, vol-scaled, meta-labeling

### Takeaway
No 2019-2026 crypto study isolating the out-of-sample (OOS), after-cost gain from triple-barrier labels or meta-labeling was found. The evidence for these methods is mostly methodological, practitioner-level or in-sample. The best-documented crypto ML successes use simple labels: cross-sectional "beat the median" labels (Fischer et al. 2019) and next-day direction (Jaquart et al. 2022). For meta-labeling, the most concrete published result concerns sizing through calibration, not the gain in signal quality.

### Cited Findings
- **Cross-sectional rank label, crypto, after costs.** Fischer, Krauss and Deinert (2019, JRFM 12(1)) trained a random forest on lagged returns of 40 coins. The label was whether each coin would beat the cross-sectional median over the next 120 minutes. The strategy went long the top 3 and short the bottom 3. OOS (18 Jun to 17 Sep 2018), it made more than 100,000 trades and returned 7.1 bp/day after 15 bp per half-turn. The authors themselves flag limits to arbitrage and volume constraints. The OOS window is only 3 months. — [FAU CRIS](https://cris.fau.de/publications/216708387); [RePEc](https://ideas.repec.org/a/gam/jjrfmx/v12y2019i1p31-d205554.html)
- **Fixed-horizon direction, daily, 100 coins.** Jaquart, Köpke and Weinhardt (2022, J. Finance and Data Science) report accuracy of 52.9-54.1%. A long-short portfolio from LSTM/GRU ensembles reached an OOS Sharpe after costs of 3.23 and 3.12, against 1.33 for buy-and-hold. This is a single study and the Sharpe is unusually high, so treat it as optimistic until replicated. — [DOAJ record](https://doaj.org/article/cfc09801314441198e3e1c92a3914e54)
- **Fixed-horizon direction, intraday 1-60 min, BTC.** Jaquart, Dann and Weinhardt (2021, JFDS) found that predictability rises with horizon length. A long-short quantile strategy made up to 39% per month before costs and was negative after costs because holding periods were very short. — [KIT repository](https://publikationen.bibliothek.kit.edu/1000150665) (summary via search; title and metadata at that link not individually verified)
- **Triple-barrier and information-driven bars in crypto.** Grądzki, Wójcik and Lessmann (2025, Financial Innovation 11:136) studied information-driven bars, triple-barrier labeling and deep learning on BTC and ETH. I could not access its OOS tables, so whether triple-barrier or meta-labeling beats fixed-horizon after costs in that paper is unverified. — cited by [arXiv 2608.26158](https://arxiv.org/pdf/2608.26158)
- **Information bars are contested.** An independent EURUSD replication notes that the claimed superiority of information-driven bars is asserted in AFML end-of-chapter exercises rather than demonstrated. — [MQL5 article](https://www.mql5.com/en/articles/23310)
- **Overlapping labels.** When labels are computed every bar over an N-bar horizon, they overlap. That overlap is the reason purged CV is required, and it applies to both triple-barrier and fixed-horizon labels. — [LuxAlgo concept page](https://www.luxalgo.com/library/concept/label-definition-and-prediction-horizon.md)
- **Meta-labeling definition.** A primary model generates the side (long or short). A secondary model predicts whether the primary signal will be profitable, and its probability drives the bet/no-bet decision and the position size. — [Wikipedia: Meta-Labeling](https://en.wikipedia.org/wiki/Meta-Labeling)
- **Meta-labeling calibration result (JFDS, "Meta-Labeling: Calibration and Position Sizing").** The paper tested six sizing algorithms, including a new "sigmoid optimal position sizing" (SOPS). From the abstract: calibration significantly improves *fixed* sizing functions, while methods that fit their sizing function on training data gain no significant advantage. Only a secondary abstract was read, and the study uses controlled or simulated settings, not crypto. — [Wikipedia: Meta-Labeling](https://en.wikipedia.org/wiki/Meta-Labeling); [UZH record](https://www.merlin.uzh.ch/publication/show/22343)
- **TradingView "Triple Barrier with Meta Labeling" scripts.** Their authors state the results are in-sample with no costs or slippage, so they are not evidence. — [TradingView](https://www.tradingview.com/scripts/position-sizing/)

### Inferences
- At 4H, a label horizon of 1-6 bars (4-24h) sits between the Jaquart intraday horizons, where gross edge is destroyed by costs, and the daily horizon, where edge survived costs. The lesson from both studies is to label on a horizon long enough that the expected move clearly exceeds round-trip costs plus funding.
- Use cost-aware labels. Label a long as positive only if the forward return exceeds roughly round-trip cost plus a margin, or volatility-scale the return (r / sigma) and drop the dead zone. This mirrors the cost-aware filter that rescued Bysik and Ślepaczuk's results (section 3).
- For a long + short universe, a cross-sectional rank label (beat the median) has the best crypto evidence (Fischer et al.). It also neutralizes market beta, which helps the short side.
- Pre-register any meta-labeling layer. Its benefit must be proven against the primary model alone on the same OOS folds, and against a shuffled-label control.

### Gaps
- No crypto paper was found that reports an OOS, after-cost ablation of triple-barrier against fixed-horizon labels, or of meta-labeling against no meta-labeling.
- Grądzki et al. (2025) full results were not accessed.

## 2. Cross-validation: purged/embargoed k-fold, CPCV, walk-forward; retraining cadence; leakage

### Takeaway
Purging removes training samples whose label windows overlap the test period, and embargo adds a further gap after the test set. Both are mandatory with overlapping 4H labels. One synthetic-environment comparison (Arian et al., 2024) favors combinatorial purged CV (CPCV) over walk-forward for detecting overfitting. Walk-forward remains the realistic final simulation. The best practice is CPCV for model and hyperparameter selection, then a single, untouched walk-forward or holdout period for the final claim.

### Cited Findings
- **Purged CV, CPCV and embargo.** Purged CV removes training observations whose label intervals overlap test observations, and embargo removes a buffer after each test fold to block serial-correlation leakage (López de Prado, AFML). — [Wikipedia: Purged cross-validation](https://en.wikipedia.org/wiki/Purged_cross-validation)
- **CPCV paths.** CPCV generates C(N,k) train/test combinations, for example 15 combinations for N=6 and k=2, and reassembles them into multiple backtest paths, giving a distribution of OOS performance instead of a single path. — [skill doc summary](https://skillselion.com/skills/agiprolabs/claude-trading-skills/walk-forward-validation); [fynance CPCV docs](https://fynance.readthedocs.io/en/latest/generated/fynance.data.combinatorial_purged_cv.html)
- **Weakness of walk-forward.** It evaluates one sequence of test sets, so its performance estimate has high variance and depends on one historical path. — [LuxAlgo](https://www.luxalgo.com/library/concept/purged-cross-validation/)
- **Arian et al. (2024) comparison.** In a synthetic controlled environment, CPCV was superior at mitigating overfitting risk, while walk-forward remains the industry standard for realistic simulation. This is a second-hand citation; the primary paper was not opened. — cited in [arXiv 2512.12924](https://arxiv.org/pdf/2512.12924)
- **Walk-forward in practice, crypto.** Bysik and Ślepaczuk used a 27-fold walk-forward on hourly BTC perps from 2018 to 2026. Results varied widely across folds, and losses concentrated in the 2022 bear market and late 2025. A single aggregate number hides this regime dependence. — [arXiv 2606.00060](https://arxiv.org/abs/2606.00060)

### Inferences
These are engineering inferences, not sourced claims.
- **Purge length.** With 4H bars and label horizon H bars, purge at least H bars around each test fold. The embargo should cover the longest feature lookback that touches the test period's labels, and at least about 1% of the sample (the AFML heuristic). For triple-barrier labels, purge using each event's actual end time (t1), not a fixed H.
- **Partially formed bars.** Every feature at decision time t must use only bars closed at or before t. Common leaks:
  - resampling 1h/15m to 4H with label='right' or closed='right' mismatches;
  - funding-rate or open-interest snapshots stamped at period end but published later;
  - cross-sectional ranks computed with coins whose bar is not yet closed;
  - rolling normalization (z-scores, scalers) fitted on the full sample;
  - universe membership chosen with hindsight (survivorship).
- **Same-bar execution leak.** Trade at the open of bar t+1, never the close of bar t, because the close is the feature input.
- **Retraining cadence.** No crypto study comparing retraining frequencies was found. A common setup is to retrain monthly or quarterly with an expanding or rolling window and pre-register the choice. The across-fold variance in Bysik and Ślepaczuk suggests regime drift is real, which argues for rolling windows or periodic retraining. Test both, and count both as trials for the deflated Sharpe ratio (DSR).

### Gaps
- The primary Arian et al. (2024) paper was not retrieved.
- No empirical study was found on optimal retrain frequency, or on expanding versus rolling windows, for intraday crypto.

## 3. Model choice: GBM vs deep (LSTM/GRU/Transformer/TCN) vs linear, OOS after costs

### Takeaway
The 2024-2026 evidence does not show deep models beating gradient boosting after costs on crypto. The best recent hourly study (Bysik and Ślepaczuk, 2026) found XGBoost descriptively best, but with differences that were not significant and with no strategy significantly beating buy-and-hold in Sharpe terms. The largest cross-sectional study (Cakici et al., 2024) found limited benefit from model complexity, with signal driven by a few simple characteristics. Costs, not model class, are the dominant determinant of intraday profitability.

### Cited Findings
- **Bysik and Ślepaczuk (arXiv 2606.00060, May 2026).**
  - Data and protocol: 70,872 hourly Binance USD-M BTCUSDT perp bars from 2018 to 2026, 27-fold walk-forward. Models: XGBoost, LSTM and iTransformer.
  - Gross results: XGBoost long-only 73.5% annualized compounded return (ARC); iTransformer long-short 181.8% ARC.
  - With 10 bp per change and naive sign trading: XGBoost long-only fell to -64.0% ARC and iTransformer long-short to -98.6%.
  - Cost-aware filter (trade only when the predicted magnitude exceeds a cost threshold): XGBoost long-only reached 65.4% ARC and Sharpe 1.09, versus LSTM 49.4% / 0.84 and iTransformer 34.9% / 0.64. Trades fell from 10,619 to 251.
  - Robustness: long-only results stayed profitable at costs up to 25 bp.
  - Caveats: model differences were not statistically significant, and "none of the cost-aware strategies significantly outperforms buy-and-hold in Sharpe-ratio terms." This is a preprint, not yet peer reviewed.
  — [arXiv 2606.00060 via EmergentMind](https://www.emergentmind.com/papers/2606.00060)
- **Cakici, Shahzad, Będowska-Sójka and Zaremba (2024, Int. Review of Financial Analysis 94, 103244).** In the cross-section of cryptocurrency returns, the benefit from model complexity is limited. Despite high turnover, most ML strategies remain profitable after trading costs. Signals derive mainly from market price, past alpha, illiquidity and momentum. — [ICM open repository](https://open.icm.edu.pl/handle/123456789/25543)
- **Cryptocurrency risk factors via ML (2026 seminar abstract, Tunghai Univ.).** Gradient boosting beats linear benchmarks OOS, and XGBoost more than triples the OLS Sharpe in value-weighted portfolios. This is a talk abstract, not peer reviewed. — [THU news](https://stat.thu.edu.tw/web/news/detail.php?id=891)
- **Jaquart et al. (2021) intraday.** RNNs and gradient boosting classifiers were "especially well suited", technical features were most important, and results were negative after costs. — [KIT](https://publikationen.bibliothek.kit.edu/1000150665)
- **Jaquart et al. (2022) daily.** LSTM/GRU ensembles reached an OOS Sharpe of 3.1-3.2 after costs. This is the strongest pro-deep-learning crypto result found, from a single study. — [DOAJ](https://doaj.org/article/cfc09801314441198e3e1c92a3914e54)
- **Fischer and Krauss (2018, EJOR), equities, daily (canonical, not re-fetched).** LSTM beat random forest, a deep neural net and logistic regression on S&P 500 constituents. Edge decayed after about 2010 and was largely arbitraged away in later years. — [EJOR DOI 10.1016/j.ejor.2017.11.054](https://doi.org/10.1016/j.ejor.2017.11.054)

### Inferences
- The default brain for 4H should be a GBM (LightGBM, XGBoost or HistGB) on tabular features. It is cheaper, more stable across folds, easier to calibrate, and is the best or tied model in the 2024-2026 crypto evidence.
- Add a linear or logistic baseline and a buy-and-hold baseline to every report.
- Deep sequence models should enter only as ensemble members, and only if they beat the GBM on CPCV folds after costs and after deflated-Sharpe adjustment.
- A cost-aware "no-trade zone" matters more than the choice of model.

### Gaps
- No 4H-specific head-to-head comparison was found.
- No peer-reviewed TCN-vs-GBM crypto study after costs was found.
- The "Kehinde et al." study named in the brief could not be located within budget, so its findings are unverified.

## 4. Features at 4H: lags, volatility, volume, taker imbalance, funding, OI, basis, cross-sectional ranks, BTC regime

### Takeaway
Peer-reviewed evidence supports simple price-based characteristics: momentum and past returns, price level, illiquidity, past alpha and technical indicators. Evidence that funding rate or open interest add OOS predictive power for returns is thin. One study found ML funding-rate forecasts did not beat a static rule.

### Cited Findings
- **Price-based characteristics.** The dominant cross-sectional crypto predictors are market price, past alpha, illiquidity and momentum. — [Cakici et al. 2024](https://open.icm.edu.pl/handle/123456789/25543)
- **Technical features.** Technical features were the most important group in intraday BTC prediction. — [Jaquart et al. 2021, KIT](https://publikationen.bibliothek.kit.edu/1000150665)
- **Lagged returns.** Lagged returns alone (multiple lags) were enough to produce a cross-sectional edge after costs at 120-minute horizons. — [Fischer et al. 2019](https://cris.fau.de/publications/216708387)
- **Funding-rate forecasting.** On Binance Futures, 8 assets, walk-forward: Ridge and XGBoost forecasts of funding failed to beat a static rule (Cohen's d < 0.2), because funding is strongly mean-reverting. — [Thai journal JSTKU](https://ph03.tci-thaijo.org/index.php/JSTKU/article/view/4724)
- **Funding and market trend.** BitMEX funding was modeled with GARCH and Granger tests as a market-trend gauge. This is not an ML trading test. — [arXiv 1912.03270](https://arxiv.org/abs/1912.03270)

### Inferences
- **Recommended 4H feature set:**
  - log returns over 1, 2, 3, 6, 12, 18, 42 and 84 bars;
  - realized volatility (Parkinson or Garman-Klass) over several windows;
  - volume z-scores and Amihud illiquidity;
  - taker buy/sell imbalance;
  - funding level and change;
  - OI change against price change;
  - perp-spot basis;
  - cross-sectional ranks of all the above;
  - BTC trend and volatility regime flags.
- Treat funding, OI and basis as hypotheses to be proven by ablation (with and without) on purged folds, not as known edges.
- Feature importance should be measured on OOS folds, using permutation importance or MDA with purging, not by in-sample gain.

### Gaps
- No peer-reviewed study was found that quantifies OOS feature importance of taker imbalance, OI or basis in crypto ML at 4H.

## 5. Regime detection (HMM, volatility regimes): does it help OOS?

### Takeaway
HMMs identify crypto regimes (bull, bear, calm) and give OOS *forecasting-density* gains. No study was found showing an HMM regime-switching crypto strategy beating simpler baselines after costs OOS.

### Cited Findings
- **Bayesian HMMs.** For BTC, ETH and XRP, Bayesian HMMs improved predictive densities over a random walk, and a 4-state BTC model separated bull, bear and calm regimes. This is a forecasting study, not a trading backtest. — [arXiv 2011.03741](https://ar5iv.labs.arxiv.org/html/2011.03741)
- **Figà-Talamanca, Focardi and Patacca (2021, NAJEF).** HMMs on BTC, ETH, LTC and XMR were selected partly by OOS forecast performance. The authors say the regimes "may be exploited" for strategies, which is speculative, and no net-of-cost results were seen. — [EconPapers](https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000577)
- **HMM factor switching, US equities, OOS Sep 2017 to Apr 2020.** The strategy beat the individual factor models. This is not crypto evidence. — [JRFM 13(12):311](https://www.mdpi.com/1911-8074/13/12/311/htm)
- **Regime dependence in walk-forward.** Losses concentrated in the 2022 bear market and late 2025, which indicates regime dependence but does not show that an HMM would have fixed it. — [arXiv 2606.00060](https://www.emergentmind.com/papers/2606.00060)

### Inferences
- Feed regime as a feature, such as an HMM state probability fitted causally (forward filter only, re-fit inside each training fold). Do not hard-switch between models, which multiplies the number of trials.
- HMM smoothing (forward-backward) uses future data and is a leak. Use only filtered probabilities.

### Gaps
- No OOS, net-of-cost crypto evidence was found that regime models add value over a regime-agnostic GBM.

## 6. Ensembles, model averaging, probability calibration for sizing

### Takeaway
Ensembles of recurrent nets produced the best daily crypto result found (Jaquart 2022). Calibration helps fixed sizing rules but not sizing rules that are themselves learned (meta-labeling calibration paper).

### Cited Findings
- **LSTM and GRU ensembles.** Ensembles reached Sharpe 3.23 and 3.12 after costs, daily, 100 coins. — [DOAJ](https://doaj.org/article/cfc09801314441198e3e1c92a3914e54)
- **Calibration and sizing.** Probability calibration significantly improves fixed position-sizing functions. Sizing functions estimated from training data get no significant gain from calibration. — [Meta-Labeling (Wikipedia summary of the JFDS paper)](https://en.wikipedia.org/wiki/Meta-Labeling); [UZH record](https://www.merlin.uzh.ch/publication/show/22343)

### Inferences
- Average 3-5 GBMs with different seeds and feature subsets, plus optionally one sequence model. Calibrate with isotonic or Platt scaling fitted on a separate purged calibration fold, never on the test fold.
- Size with a capped linear or sigmoid function of (p - 0.5), or with fractional Kelly using a conservative fraction.
- Check reliability diagrams per fold, since crypto probabilities drift with regime.

### Gaps
- No crypto-specific study was found on calibration quality across regimes.

## 7. Backtest rigor: fills, funding, latency, PBO, DSR, multiple testing, placebo controls, holdout, paper-trading power, capacity

### Takeaway
The statistical toolkit is mature:
- probability of backtest overfitting (PBO) via combinatorially symmetric CV (CSCV);
- deflated Sharpe ratio (DSR) for selection bias and non-normality;
- minimum track record length (MinTRL);
- Harvey-Liu-Zhu t > 3;
- Arnott-Harvey-Markowitz protocol.

Evidence (888 Quantopian strategies) shows that backtest Sharpe barely predicts OOS Sharpe, and the gap widens with more backtesting. Execution realism (next-bar open, intrabar barrier ordering on finer data, funding accrual) is engineering practice, with little academic literature.

### Cited Findings
- **PBO via CSCV.** CSCV splits the return matrix into blocks and forms all in-sample and OOS halves. PBO is the probability that the in-sample-best configuration underperforms the median configuration OOS. — [CRAN pbo README](https://ftp.fau.de/cran/web/packages/pbo/readme/README.html); [Bailey et al. "overfit tools" PDF](https://www.davidhbailey.com/dhbpapers/overfit-tools-at.pdf)
- **PBO caveat.** PBO's logit is ordinal and can be biased when poor configurations sit near the median. — [arXiv 2008.09481](https://arxiv.org/pdf/2008.09481)
- **Trial budget.** High simulated Sharpe is easy to achieve after a small number of trials. With only 5 years of daily data, no more than about 45 strategy variations should be tried. — [Bailey et al., "Pseudo-Mathematics and Financial Charlatanism"](https://scholarworks.wmich.edu/math_pubs/40/)
- **DSR.** The deflated Sharpe ratio corrects for selection bias under multiple testing and for non-normal returns (Bailey and López de Prado, JPM 2014). — [SSRN 2460551](https://papers.ssrn.com/abstract=2460551)
- **MinTRL.** Minimum track record length is the track-record length needed to reject "true SR ≤ threshold" at a given confidence, and it lengthens with negative skew and fat tails. The source is the Journal of Risk paper "The Sharpe Ratio Efficient Frontier", which includes Python code. — [Risk.net](https://www.risk.net/journal-risk/2223785/sharpe-ratio-efficient-frontier); [RePEc](https://ideas.repec.org/a/rsk/journ4/2223785.html); [PerformanceAnalytics MinTrackRecord](https://www.quantargo.com/help/r/latest/packages/PerformanceAnalytics/NEWS/MinTrackRecord)
  - Approximate formula, NOT verified against the paper: MinTRL ≈ 1 + [1 − γ3·SR + ((γ4 − 1)/4)·SR²]·(z_α/(SR − SR*))², with SR the per-period Sharpe ratio. Verify before use.
- **Backtest vs OOS (888 Quantopian strategies).** Backtest Sharpe had little value for predicting OOS performance, and more backtesting meant a larger IS/OOS gap. — [Wiecki et al. "All that Glitters Is Not Gold" PDF](https://c.mql5.com/forextsd/forum/208/All%20that%20Glitters%20Is%20Not%20Gold%20-%20Comparing%20Backtest%20and%20Out-of-Sample%20Performance%20on%20a%20Large%20Cohort%20o.pdf)
- **Research protocol.** Arnott, Harvey and Markowitz propose a backtesting protocol for the ML era: pre-specify, count all trials, and be skeptical of complex models. — [SSRN 3275654](https://papers.ssrn.com/abstract=3275654)
- **Harvey, Liu and Zhu (2016, RFS) (canonical, not re-fetched).** Given hundreds of tested factors, a new factor should clear t > 3.0 rather than 2.0. — [RFS DOI 10.1093/rfs/hhv059](https://doi.org/10.1093/rfs/hhv059)
- **Cost realism.** At 10 bp per change, hourly sign strategies collapse, and a cost-aware filter that cut trades about 40x restored profitability. — [arXiv 2606.00060](https://www.emergentmind.com/papers/2606.00060)
- **Capacity.** Fischer et al. explicitly flag total volume constraints as limiting their intraday crypto strategy. — [FAU CRIS](https://cris.fau.de/publications/216708387)

### Inferences
These are engineering and statistical inferences, not sourced claims.
- **Fills and latency.**
  - Signal on the closed 4H bar t; enter at the open of bar t+1, plus slippage of half the spread plus an impact term proportional to √(size / bar volume).
  - Simulate stop, take-profit and liquidation inside each 4H bar using 1m data (or 15m/1h if 1m is unavailable).
  - If both stop and target fall in the same finest sub-bar, assume the adverse one hit first (conservative).
  - Never use 4H high/low ordering heuristics alone.
- **Funding.**
  - Accrue at each funding timestamp the position is held over: longs pay when the rate is positive, shorts receive.
  - Use the actual historical rate per timestamp, not an average.
  - Not verified this session: Binance moved some USD-M symbols from 8h to 4h/1h funding intervals, so use per-symbol interval history rather than assuming 8h.
- **Placebo and controls.**
  - Run the full pipeline (training plus backtest) on shuffled labels (permute labels within the training folds) and on circularly time-shifted labels.
  - The real model's OOS metric should exceed at least the 95th percentile of placebo runs.
  - Also compare against random-entry strategies with identical turnover and holding period.
- **Multiple testing.** Log every configuration tried. Feed the number of trials N and the variance of trial Sharpes into the DSR, and report PBO from CSCV across all configurations.
- **Holdout.** Reserve the most recent 6-12 months as a sealed holdout, touched once, after the protocol and code are SHA-locked.
- **Forward paper-trading power.** This is approximate, assuming normal returns, SR* = 0 and 95% one-sided confidence (z ≈ 1.645). Required years ≈ (1.645 / annual SR)².
  - True annual SR 2.0: about 0.68 years (roughly 8 months).
  - SR 1.5: about 1.2 years.
  - SR 1.0: about 2.7 years.
  - SR 0.5: about 10.8 years.
  - Negative skew and fat tails, which crypto has, lengthen these. A 1-3 month paper test can only rule out disasters or bugs; it cannot confirm an edge unless the true SR exceeds about 4.
- **Capacity.** Estimate the participation rate as position size divided by the 4H bar volume of the traded symbol. Re-run the backtest with an impact model at 2x, 5x and 10x the planned capital, and report the AUM at which net SR halves. Lower-cap altcoins on the short side also face borrow limits on spot, and open-interest or position limits on perps.

### Gaps
- No academic paper was found that quantifies the bias from coarse-bar versus fine-bar intrabar stop simulation in crypto.
- No peer-reviewed crypto capacity study for 4H ML strategies was found.
- Binance per-symbol funding-interval changes were not verified this session.
