# Multi-scale AI "brains" across timeframes (5m to 1M): structure and fast/slow coordination

Research notes, 2026-10-17. Status labels: [PEER] peer-reviewed or journal; [PREPRINT] arXiv/SSRN without a confirmed venue; [VENDOR] fund or marketing research; [2ND] secondary summary only, not checked against the primary source; [IS] in-sample or unclear OOS.
Coverage: about 15 web calls. Many primary tables were behind paywalls or failed to load, so they are not reproduced. Every number below has a source, and missing numbers are listed under Gaps.

## Q1. Is there OOS evidence that hierarchical or multi-timescale models beat simple ensembles of single-horizon models in trading?

### Takeaway
I found no rigorous OOS evidence, net of costs, that a learned hierarchical or multi-timescale model beats a simple ensemble of single-horizon models in trading. The strong multi-scale evidence is in volatility forecasting with linear mixed-frequency models (HAR, MIDAS), and those are simple. Hierarchical RL trading papers are mostly conference or preprint work. They compare against other RL or benchmark models, not against a simple equal-weight ensemble of horizon models.

### Cited Findings
- **HAR (Corsi 2009).** Next-day realized variance is regressed on daily, weekly (5-day) and monthly (22-day) RV averages by OLS. This is a constrained AR(22) [PEER]. It is widely used as a benchmark that "often outperform[s] more complex models" — [arXiv 2506.07928](https://arxiv.org/pdf/2506.07928) [PREPRINT]; see also ["HARd to Beat", arXiv 2406.08041](https://arxiv.org/html/2406.08041v1) [PREPRINT]. That paper argues that the choice of rolling window explains much of the apparent gain of ML over HAR.
- **MIDAS (Ghysels, Santa-Clara, Valkanov).**
  - Daily realized power, built from 5-minute absolute returns, was the best predictor of future volatility.
  - Using the 5-minute data directly did not improve forecasts.
  - One to two months of daily lags captured persistence.
  - The authors say this held in and out of sample — [NBER w10914](https://www.nber.org/papers/w10914) [PEER, J. Econometrics 2006].
  - A 2019 review covering 30 assets, horizons of 5–66 days and 2005–2018 data found MIDAS gave the most precise variance forecasts in and out of sample — [Ghysels et al., Annual Review of Financial Economics 2019](https://ideas.repec.org/a/anr/refeco/v11y2019p173-195.html) [PEER].
- **Temporal Fusion Transformer (Lim, Arik, Loeff, Pfister; Oxford/Google).**
  - One model gives multi-horizon forecasts, using variable-selection and gating layers.
  - A third-party summary reports about 7% lower P50 loss and 9% lower P90 loss than benchmarks — [arXiv 1912.09363](https://arxiv.org/abs/1912.09363v3) [PEER, IJF 2021; numbers 2ND].
  - The test datasets are electricity, traffic, retail and volatility. No trading P&L test was found.
- **HRPM hierarchical RL (Wang et al., AAAI 2021).**
  - The high-level policy sets portfolio weights at low frequency. The low-level policy executes buys and sells at high frequency to reduce trading cost.
  - The abstract claims "significant improvement" over state-of-the-art methods but gives no numbers, OOS period or flat-baseline ablation — [arXiv 2012.12620](https://arxiv.org/abs/2012.12620) [PEER conference; evidence not verified].
- **Hierarchical Reinforced Trader (HRT).**
  - A PPO high-level controller picks stocks and a DDPG low-level controller executes.
  - The authors report a higher Sharpe than standalone DRL models and the S&P 500 — [arXiv 2410.14927](https://arxiv.org/html/2410.14927v1) [PREPRINT].
- **TRIALS: pair selection plus trading as one hierarchical RL problem.** The authors argue that splitting the two steps limits performance — [arXiv 2301.10724](https://arxiv.org/abs/2301.10724) [PREPRINT/conference].
- **Multi-scale Two-way DNN (IJCAI 2020).** It uses wavelet and downsampling scales and reports that multi-scale information helps. The snippets show no single-scale OOS ablation with transaction costs — [IJCAI 2020](https://www.ijcai.org/Proceedings/2020/628) [PEER conference].
- **Forecast combination puzzle.**
  - A simple average often beats "optimal" estimated weights, because estimating the weights adds variance when the optimal weights are near equal — Smith & Wallis (2009), discussed in [arXiv 1505.00475](https://arxiv.org/pdf/1505.00475) and the [50-year review, arXiv 2205.04216](https://arxiv.org/pdf/2205.04216).
  - Elliott finds the gain from optimal weights "often small enough to be overshadowed by estimation error" — [Elliott, UCSD](https://econweb.ucsd.edu/~gelliott/Combination.pdf).

### Inferences
- The evidence favors simple fixed-structure multi-scale designs (HAR-style daily/weekly/monthly features in one linear model, or an equal-weight blend) over learned hierarchical controllers. Learned hierarchies add parameters that the combination puzzle says will be eaten by estimation error.
- MIDAS's finding that raw 5-minute data adds nothing beyond a good daily summary of it matches our result that 15m/5m features add only +0.0008 AUC. Intraday data is better used as a summarized feature (realized vol, range) or for execution than as a separate alpha brain.
- Hierarchical RL papers mostly show their value in execution cost, with the low-level policy cutting cost. That supports a separate execution layer, not more alpha brains.

### Gaps
- I found no paper with a pre-registered, cost-inclusive OOS comparison of "hierarchical multi-timescale model" vs "equal-weight ensemble of per-horizon models" on crypto or futures.
- HRPM, HRT and TRIALS full tables (OOS dates, Sharpe after costs, flat ablations) were not retrieved.

## Q2. One shared model across horizons, or separate models per horizon? (M4/M5, cross-learning)

### Takeaway
Forecasting competitions favor global, cross-learned models, meaning one model trained across many series, and simple ensembles of them. That is evidence for sharing across series, and it carries over by analogy to coins. Direct evidence on one shared model across horizons vs per-horizon models in trading is thin. TFT shows that one multi-horizon model is competitive in general forecasting.

### Cited Findings
- **M4 found that cross-learning helps.** "The top two performers both used models estimated on many time series." The winner (Smyl's ES-RNN) used global weights with per-series local parameters — summarized in [arXiv 2009.07701 (Kaggle competitions review)](https://arxiv.org/pdf/2009.07701) and [arXiv 1909.00590](https://arxiv.org/pdf/1909.00590) [2ND for M4 wording]. One review notes the winner was weak on daily and weekly data [2ND, single paper].
- **Kaggle competition review.** "Ensemble models using cross-learning tend to outperform local time series models" — [arXiv 2009.07701](https://arxiv.org/abs/2009.07701v1) [PEER, IJF].
- **M5 (Makridakis, Spiliotis, Assimakopoulos, IJF 38(4) 2022).**
  - The data is 42,840 hierarchical Walmart series.
  - The winner was an equal-weighted ensemble of LightGBM models, and almost all of the top 50 used LightGBM.
  - Simple ML improved on benchmarks by up to about 20% — [IDEAS](https://ideas.repec.org/a/eee/intfor/v38y2022i4p1346-1364.html), [KU Leuven follow-up](https://lirias.kuleuven.be/retrieve/636194) [PEER; details 2ND].
- **Cross-scale caution.** A preprint finds that global tree forecasters "collapse at the hierarchical aggregate" when M5 is re-run at a different granularity — [arXiv 2609.27912](https://arxiv.org/pdf/2609.27912) [PREPRINT, not checked]. A model trained at one scale may not transfer to another.
- **Local vs global for hierarchical forecasting** is studied in [arXiv 2411.06394](https://arxiv.org/pdf/2411.06394) [PREPRINT; results not retrieved].

### Inferences
- **Pooling across coins** (one global model per horizon with coin ID or vol-normalized features) is well supported by M4/M5.
- **Pooling across horizons in one model** is a separate question.
  - Our own data says the D1/H4/H1 ranking brains were 0.89–0.95 correlated. They answer the same question, so separate per-horizon ranking brains add maintenance without diversification.
  - Either merge them into one model with HAR-style multi-scale features, or keep one primary horizon (D1) and use lower timeframes only for timing.
- The M5 winner was an equal-weight ensemble of simple GBMs. This supports equal-weight blending with no learned stacking weights for whatever few brains remain.

### Gaps
- The original M4 (IJF 2020) and M5 tables broken down by horizon were not retrieved. Whether the global-model advantage changes with horizon is unverified.
- I found no trading study that directly compares one multi-horizon return model vs separate per-horizon models on the same OOS P&L.

## Q3. How do CTAs and multi-strategy funds blend multiple speeds, and what does it do to drawdowns and turnover?

### Takeaway
CTAs combine several trend speeds, mostly with fixed weights and vol scaling.
- Faster speeds give better crisis protection and positive skew, but lower Sharpe after costs and higher turnover.
- Slower speeds give higher Sharpe but weaker short-horizon crisis protection.
- Speeds are chosen to minimize correlation between them; Man AHL reports 0.17 between its fastest and slowest.
- A 2025 preprint finds the medium horizon redundant and proposes a short+long barbell.

### Cited Findings
- **Man AHL, "The Need for Speed in Trend-Following Strategies" (2023) [VENDOR].**
  - Setup: double-EWMA crossover models, used at AHL for about three decades and still the largest risk allocation. Backtest from 1995 to Aug 2022 on 50 liquid futures and FX markets, with 25% risk to each asset class.
  - Correlation between the fastest and slowest speed is 0.17. Speeds were chosen to span trend lengths while minimizing correlation.
  - Risk-adjusted returns rise as speed slows. Skew is positive and higher for faster speeds.
  - After costs, Sharpe falls materially for fast speeds. Turnover falls as speed slows.
  - In the worst S&P quintile (1-month and 3-month windows), performance improves as speed increases.
  - Blends: an "Equal Blend" of 5 speeds, a "Slow Blend", and a "V.Slow" single speed, each scaled to 10% vol. All reduced drawdowns when mixed 50/50 with a 60/40 portfolio, and more fast allocation gave better downside mitigation.
  - AHL claims it cuts transaction costs about 2x versus bank algos (unverified claim).
  - Source: [Man Group](https://www.man.com/insights/need-for-speed-trend-following). The tables were in charts that did not load, so numbers are missing.
- **AQR, "A Century of Evidence on Trend-Following Investing" (Hurst, Ooi, Pedersen) [PEER, JPM 2017].**
  - It combines 1-, 3- and 12-month time-series momentum, equal-weighted.
  - Secondary summaries give the Sharpe after 2/20 fees as about 0.4 (CXO) or 0.76 (Swedroe). These conflict, possibly because they measure different things, and are unverified — [AQR](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing?aqrPDF=1), [CXO](https://www.cxoadvisory.com/momentum-investing/trend-following-with-intrinsic-momentum-over-the-very-long-run), [ETF.com/Swedroe](https://www.etf.com/sections/index-investor-corner/swedroe-why-financial-trends-persist).
- **Etienne, Ohana, Benhamou et al. (Ai For Alpha), "Revisiting the Structure of Trend Premia" [PREPRINT, arXiv 2510.23150].**
  - Horizons tested: 20, 60, 125, 250 and 500 days on futures, with OOS rolling windows (8-year train, 6-month test).
  - Single horizons, 2015–2025 Sharpe: 20d 0.20, 60d 0.21, 125d 0.21, 250d 0.42, 500d 0.47. All horizons blended: 0.36.
  - Max drawdown: 500d 14.5%, all horizons 21.6%.
  - Correlations: 250d–500d 0.90, 125d–250d 0.84, 125d–60d 0.81. The 20d sleeve is 0.44–0.66 correlated with the slower ones.
  - Full period 2013–2025 Sharpe: equal-weight 0.79, optimized weights 0.72, "dynamic" persistence rule 0.86.
  - Conclusions:
    - Equal weighting is suboptimal, but estimated weights did not beat it overall.
    - The medium (125d) layer "largely overlaps with its neighboring horizons".
  - Caveats: a single vendor group; not a clean ablation — [arXiv](https://arxiv.org/html/2510.23150v2).
- **Baltas & Kosowski, "Demystifying Time-Series Momentum" (1974–2013).** Better volatility estimation and trend detection significantly reduce turnover and rebalancing costs — [Imperial/SSRN](https://spiral.imperial.ac.uk/bitstream/10044/1/41472/4/SSRN-id2140091.pdf) [PEER/WP].
- **Newfound Research [VENDOR blog].** Fast trend models limited losses in week-long drawdowns. Intermediate and slow models did best in 3-month to 1-year drawdowns. A blend was not tested directly — [Newfound](https://blog.thinknewfound.com/2019/04/the-speed-limit-of-trend/).
- **Gârleanu & Pedersen, "Dynamic Trading with Predictable Returns and Transaction Costs" (JF 2013) [PEER].**
  - Optimal policy: trade partway toward an "aim portfolio", which is a weighted average of the current and expected future Markowitz portfolios.
  - Slower-decaying signals get more weight, because "they lead to a favorable positioning both now and in the future."
  - Tested on commodity futures, it gave better net returns than naive benchmarks — [NBER w15205](https://www.nber.org/papers/w15205).

### Inferences
- **Speeds diversify only when they are weakly correlated.** Man's fastest vs slowest is 0.17, and the preprint's 20d vs others is 0.44–0.66. Neighboring speeds are 0.8–0.9 correlated and are redundant. That is our D1/H4/H1 situation at 0.89–0.95.
- **A minimal multi-speed set is a barbell.** One genuinely fast sleeve plus one slow sleeve, with equal risk and fixed weights. Do not use learned weights, per the combination puzzle and the preprint, where optimized weights got 0.72 vs 0.79 for equal weight.
- **Gârleanu-Pedersen gives the formal rule for fast/slow coordination.** The portfolio is driven mainly by slow signals. Fast signals adjust the aim only slightly and should mostly change the timing and pace of trades, not the target.

### Gaps
- Man AHL Sharpe, drawdown and turnover tables by speed (charts did not load).
- AQR per-lookback Sharpe and the combined figure (the two secondary numbers conflict).
- No crypto-specific study of trend speed blending was retrieved.

## Q4. How should fast timeframes (5m/15m) be used: execution and entry refinement, or standalone alpha? How should higher-timeframe brains constrain lower ones?

### Takeaway
In the institutional literature the fast layer mainly does execution: it schedules trades to minimize implementation shortfall given the slow signal's alpha decay. Hierarchical RL papers frame the low-level policy the same way, as a cost minimizer. I found no peer-reviewed evidence on veto vs tilt vs size gating between timeframes in trading. The only formal guidance is Gârleanu-Pedersen: the slow signal sets the target, and fast signals and costs set the pace.

### Cited Findings
- **Almgren-Chriss.**
  - It minimizes the mean (impact) and variance (risk) of implementation shortfall, with closed-form solutions under linear impact and a trivial alpha profile.
  - In practice impact is nonlinear and the schedule is sensitive to the alpha profile.
  - Bertsimas & Lo trade impact off against time-varying alpha — [Wikipedia: Alpha Profiling](https://en.wikipedia.org/wiki/Alpha_Profiling) [2ND].
- **Execution depends on alpha decay.**
  - The shape of short-term alpha decay matters, not just its size. Urgent trades show exponential decay with a time constant of about 10–60 minutes.
  - An aggressive start is optimal only when alpha outweighs the extra impact — [USPTO patent 8433645](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8433645) [patent, not peer-reviewed].
- **Lehalle & Neuman, "Incorporating Signals into Optimal Trading"** extends the framework to short-term signals used in execution — [arXiv 1704.00847](https://ar5iv.arxiv.org/html/1704.00847) [PEER, Finance & Stochastics; details not retrieved].
- **HRPM's low-level, high-frequency policy** exists "to minimize the trading cost" of the low-frequency weight decisions — [arXiv 2012.12620](https://arxiv.org/abs/2012.12620).
- **A large AHL quant fund saw "no need for high frequency trading"** — [Risk.net](https://www.risk.net/infrastructure/trading-platforms/1730110/mans-21bn-quant-fund-sees-no-need-high-frequency-trading) [VENDOR interview; content not fetched].
- **Gârleanu-Pedersen**: fast-decaying signals get less weight in the aim portfolio — [NBER w15205](https://www.nber.org/papers/w15205).

### Inferences
- **15m/5m should be an execution and entry-timing layer for the D1 decision, not an alpha brain.** Our +0.0008 AUC from 15m/5m features and MIDAS's result on 5-minute data both point the same way.
- **Its success metric should be implementation shortfall vs the D1 decision price** (bps saved), not AUC or Sharpe.
- **How higher timeframes should constrain lower ones**, based on our internal evidence:
  - When the next higher timeframe agrees, the move is +0.5 to +0.8 ATR (Swing Anatomy). This supports a tilt or size multiplier from the higher timeframe, not a hard veto.
  - A veto throws away trades. A tilt keeps them and scales risk.
  - 1W context shows no clear effect and 1M is reversed, so 1W/1M should not be gates. At most they could be a pre-registered experiment.
  - This is our inference only. No external OOS study comparing veto vs tilt was found.
- **Keep the direction one-way.** Higher timeframes set the target and the risk budget. Lower timeframes only pick timing within a bounded window, for example up to N bars after the D1 signal, and then execute at market. This stops a fast layer from sitting on a slow signal indefinitely. Our inference, consistent with how alpha decay is used in execution.

### Gaps
- No peer-reviewed OOS study of "higher-timeframe veto vs tilt vs size" for lower-timeframe entries was found.
- Crypto-specific execution evidence (spot/perp impact at our size) was not researched; it is probably negligible at testnet or small size.

## Q5. Recommended minimal set of brains, and evidence-based reasons to keep the number small

### Takeaway
The evidence favors a small, low-correlation set with fixed simple combination rules. Estimated combination weights tend to lose to equal weights. Correlated sleeves give no diversification. Learned hierarchies add parameters without proven OOS gain. Meta-labeling, as a size or filter brain, has mixed evidence.

### Cited Findings
- **Estimated weights lose to simple averages** when the true weights are near equal (Smith & Wallis 2009). Gains from optimal weights are "often small enough to be overshadowed by estimation error" (Elliott) — [arXiv 1505.00475](https://arxiv.org/pdf/1505.00475), [Elliott](https://econweb.ucsd.edu/~gelliott/Combination.pdf).
- **The optimized horizon weights underperformed equal weight** over 2013–2025, with Sharpe 0.72 vs 0.79 — [arXiv 2510.23150](https://arxiv.org/html/2510.23150v2) [PREPRINT].
- **Redundant sleeves.** Adjacent horizons are 0.81–0.90 correlated, and the medium layer adds "limited informational value" and acts as a drag — [arXiv 2510.23150](https://arxiv.org/pdf/2510.23150).
- **Meta-labeling.**
  - An article titled "Meta-Labeling: Calibration and Position Sizing" (JFDS, attributed to Joubert et al.) reports that calibration significantly improves fixed sizing methods, while data-trained sizing gave "no significant advantage" — [LinkedIn listing](https://ae.linkedin.com/in/jacquesjoubert) [2ND, not verified].
  - A practitioner critique argues meta-labeling is "not a silver bullet" when trained on the same data as the primary model — [QuantConnect forum](https://www.quantconnect.com/forum/discussion/14706/why-meta-labeling-is-not-a-silver-bullet/) [opinion].
  - The Hudson & Thames OOS demonstration is a toy example — [Hudson & Thames](https://hudsonthames.org/?p=3043) [VENDOR].

### Inferences
These are our proposal, not externally validated.

**Recommended minimal brains, at most 5:**
1. **Context/regime (slow, D1/1W summary).** It outputs a risk-budget multiplier only, as a tilt, never as a direction. With HAR-style multi-scale volatility and trend features, this matches the strongest multi-scale evidence.
2. **One primary alpha brain (D1)**, pooled across coins (M4/M5 cross-learning). Merge H4/H1 into it as HAR-style features, or drop them, since they are 0.89–0.95 correlated.
3. **Optional second alpha only if its OOS correlation with #1 is low** (for example below 0.5, a barbell analogue). Blend it at equal risk with fixed weights.
4. **Size/risk.** Vol targeting, the higher-timeframe agreement tilt (+0.5..+0.8 ATR evidence), and portfolio caps. Use calibrated probability with a fixed sizing rule rather than a learned sizer, per the meta-labeling calibration finding.
5. **Execution (15m/5m).**
   - It handles timing within a bounded window.
   - It is judged on implementation shortfall vs the D1 decision price.
   - It never changes direction or the target size.

**A monitor/kill-switch** is infrastructure, not a learned brain. It tracks drift, live vs backtest, and bot-alive status.

**Reasons to stay small:**
- **Estimation error** (combination puzzle).
- **Correlated brains add no diversification** (internal 0.89–0.95; external adjacent-horizon 0.8–0.9).
- **Each brain adds multiple-testing degrees of freedom.** Each added brain must pass our skill gate against a shuffled control.
- **Maintenance and failure surface on a live bot.**

### Gaps
- A peer-reviewed paper on the deflated Sharpe ratio or multiple testing was not fetched in this session. Cite it from a verified source if used.
- I found no published evidence on the optimal number of model components in live trading systems.
- The Joubert JFDS article was not verified at the source.
