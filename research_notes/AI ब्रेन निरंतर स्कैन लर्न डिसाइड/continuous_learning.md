# Continuous / Online / Incremental Learning vs Periodic Walk-Forward Retraining for Trading Models (crypto focus)

Scope note: ~17 tool calls. Primary sources fetched where possible; items marked [PREPRINT] are not peer-reviewed; [NOT FETCHED] = seen only via search snippet or reference list. No study was found that directly answers "does a continuously-learning model beat a scheduled-retrain model OOS after costs in crypto". That absence is itself the main finding.

## Q1. Empirical comparisons: online/incremental learners vs scheduled retraining, rolling vs expanding windows, recency weighting — OOS after costs

### Takeaway
No head-to-head study (online learner vs periodic walk-forward retrain, same task, net of costs, crypto) was found. The best rigorous evidence is about the *fitting scheme* (window length + re-estimation frequency): it can matter as much as or more than model class, and badly chosen schemes make ML look better than simple baselines. Mainstream finance-ML benchmark work (Gu-Kelly-Xiu) uses infrequent (annual) refits with an expanding window, not continuous learning.

### Cited Findings
- Gu, Kelly & Xiu (Review of Financial Studies 2020; NBER WP 25398): 60 years of data split into 18y training (1957-74), 12y validation (1975-86), 30y OOS test (1987-2016). "We avoid recursively refitting models each month. Instead, we refit once every year"; each refit grows training by one year (expanding), validation stays 12y and rolls forward. Rationale given: computation, and most signals update annually. Trees and neural nets were best; gains traced to nonlinear interactions. — [NBER PDF](https://www.nber.org/papers/w25398.pdf); [SSRN](https://papers.ssrn.com/abstract=3159577)
- GKX describe three schemes: fixed split, "rolling" (train+validation windows shift forward with fixed length, leverages recent information), and "recursive" (expanding). They chose a hybrid recursive-train / rolling-validation. — [NBER PDF](https://www.nber.org/papers/w25398.pdf)
- Audrino & Chassot (Univ. St.Gallen), "HARd to Beat" [PREPRINT, arXiv 2406.08041, q-fin]: on 1,445 stocks' realized volatility, ML models with extensive tuning *fail to beat* the linear HAR model once HAR uses a refined fitting scheme (window size + re-estimation frequency). They show HAR accuracy is "highly sensitive" to these two choices; literature studies with daily re-estimation + long training windows find HAR competitive/superior, while studies with suboptimal HAR schemes (e.g., expanding window updated only every 250 days, Zhang et al. 2023) find ML wins. Rolling re-estimation of ML is computationally burdensome due to hyperparameter tuning. — [arXiv abs](https://arxiv.org/abs/2406.08041); [PDF](https://arxiv.org/pdf/2406.08041)
- Pesaran & Timmermann (2007, J. Econometrics), "Selection of estimation window in the presence of breaks": it can be optimal to include pre-break data; pooling forecasts across many estimation windows gives "reasonably good and robust" performance. — [Timmermann PDF](https://rady.ucsd.edu/_files/faculty-research/timmermann/estimation-window.pdf)
- Pesaran & Pick (2011, JBES), "Forecast Combination Across Estimation Windows": averaging forecasts over windows yields lower bias and RMSFE than any single window for all but the smallest breaks; applied to weekly returns of 20 equity-index futures with lower RMSFE than competitors. Working-paper version: exponential down-weighting gives similar results but "critically depends on the choice of the weighting coefficient". — [CESifo WP 2293](https://www.cesifo.org/DocDL/cesifo1_wp2293.pdf); [RePEc](https://econpapers.repec.org/RePEc:ces:ceswps:_2293)
- Contrasting evidence: Hännikäinen (2015) finds the expanding window often gives the most accurate forecasts after a recent break (pooling advantage not universal). — [MPRA 66826](https://mpra.ub.uni-muenchen.de/66826) [NOT FETCHED]
- Crypto ML review (ScienceDirect, J. Finance & Data Science-type venue, 2022): standard practice is shifting study periods with periodic retraining to capture drift across market phases. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2405918822000174)
- Costs dominate short-horizon crypto results: a short-term Bitcoin ML study finds trading performance turns negative with 30 bps round-trip costs. — [ResearchGate](https://www.researchgate.net/publication/350199855_Short-Term_Bitcoin_Market_Prediction_via_Machine_Learning) [NOT FETCHED; snippet]
- Many Bitcoin "incremental training" deep-learning papers (e.g., Bi-LSTM with continuous incremental updates) report accuracy only and do not isolate incremental vs batch updating nor report net-of-cost PnL. — [arXiv 2212.03443](https://arxiv.org/pdf/2212.03443) [PREPRINT]
- Incremental-learning Transformer for stock prices (PMC): motivates incremental learning by batch-retrain cost but flags catastrophic forgetting as main risk (stability-plasticity). — [PMC11729973](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11729973/)
- Forecasting ML pitfalls: ML models are typically retrained only when concept drift is encountered; expanding windows suit short series. — [arXiv 2203.10716](https://arxiv.org/pdf/2203.10716) [PREPRINT]
- A 2025 study on retraining frequency of global forecasting models suggests lower retraining frequency need not hurt accuracy (excerpt truncated; not verified). — [arXiv 2506.05776](https://arxiv.org/pdf/2506.05776) [PREPRINT, NOT FETCHED]
- River ARF / Hoeffding: no source reporting River-based ARF/Hoeffding OOS trading returns in finance was found. Closest finance-specific stream learner: RCARF (Entropy 2019), an ARF extension with a "concept history" of inactive trees for recurring market regimes, aimed at abrupt market changes — classification metrics, not net trading returns. — [Entropy 21(1):25](https://doi.org/10.3390/e21010025); [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7514129/)
- ELM + explicit drift detection on financial time series (older paper) — exists, but results are authors' own setup, not a benchmark vs scheduled retraining. — [ResearchGate](https://www.researchgate.net/publication/295902726_An_approach_to_handle_concept_drift_in_financial_time_series_based_on_Extreme_Learning_Machines_and_explicit_Drift_Detection) [NOT FETCHED]

#### Time-decay / recency weighting (relevant to internal Step 11)
- López de Prado's time-decay weights (implemented in mlfinpy): decay parameter ranges from no decay to erasing the oldest observations; decay is applied over *cumulative uniqueness*, not raw calendar time, and multiplied with uniqueness weights. — [mlfinpy docs](https://mlfinpy.readthedocs.io/en/latest/Sampling.html); [MQL5 article](https://www.mql5.com/en/articles/19850)
- Practitioner guidance: too-fast decay starves the model of data; too-slow decay trains on a stale regime; choose half-life via walk-forward, not in-sample. These are opinions, no empirical comparison given. — [Halley Tech](https://halleytech.substack.com/p/financial-ml-pipeline-purged-cv-quant-research); [QuantMemo](https://quantmemo.com/concepts/recency-weighted-training-samples)
- The only rigorous decay evidence found is econometric: Pesaran & Pick report exponential down-weighting comparable to window averaging but highly sensitive to the decay coefficient. — [CESifo WP 2293](https://www.cesifo.org/DocDL/cesifo1_wp2293.pdf)
- DoubleEnsemble (Microsoft Research, ICDM 2020) uses learned sample reweighting (based on training dynamics, not time) + feature selection for financial data — an alternative to fixed time-decay. — [arXiv 2010.01265](https://arxiv.org/pdf/2010.01265)

### Inferences
- The internal Step 11 result (bagging + time-decay weakened learning) is consistent with the literature: decay effectively shrinks the effective sample size, which hurts in low signal-to-noise data; Pesaran-Pick show results hinge on the decay coefficient; Pesaran-Timmermann show pre-break data can still help. Bagging on top of down-weighted samples further reduces effective information per learner. Averaging forecasts across several window lengths (Pesaran-Pick) is a better-supported alternative to a single hard decay.
- "Continuous learning" is, empirically, best treated as one more choice of (window, refit frequency) to be tuned and pre-registered — not as an inherently superior paradigm. The HAR paper shows refit-scheme choice can flip ML-vs-baseline conclusions, so any comparison must tune both arms' schemes equally.
- For daily crypto bars, a daily-updated online learner sees only ~365 new labels/year per coin; the marginal information per update is tiny relative to noise, which favors infrequent refits with stable models.

### Gaps
- No peer-reviewed crypto study comparing River-style online learners (ARF, Hoeffding, online GBM) to monthly walk-forward retraining on net-of-cost OOS returns was found.
- No empirical study isolating time-decay weighting's effect on net trading performance was found.
- Audrino-Chassot exact numbers (heatmap values) not extracted; it is about volatility, not returns.

## Q2. Concept drift in financial time series: detection (ADWIN, DDM, Page-Hinkley, KSWIN), adaptation, delayed labels, false alarms

### Takeaway
Drift detectors are well established in the general stream-learning literature, but in noisy financial streams they suffer from two documented failure modes — missed drifts and false-alarm floods — and label-based detectors are fundamentally handicapped by delayed labels (trade outcome known only after the horizon). A very recent preprint shows adaptive learners (ARF) can actively blind external cumulative detectors.

### Cited Findings
- Lu, Liu, Dong, Gu, Gama, Zhang, "Learning under Concept Drift: A Review" (IEEE TKDE, 2018/2019; arXiv 2004.05785): reviews 130+ publications; framework of drift detection, drift understanding (when/how/where), and adaptation; lists 10 synthetic and 14 real benchmark datasets. — [arXiv](https://arxiv.org/pdf/2004.05785)
- Žliobaitė, "Learning under Concept Drift: an Overview" (2010 report): drift as non-stationary learning; adaptive training-set formation (windowing/forgetting). — [arXiv 1010.4784](https://ar5iv.arxiv.org/html/1010.4784)
- Gama, Žliobaitė, Bifet, Pechenizkiy, Bouchachia, "A Survey on Concept Drift Adaptation" (ACM Computing Surveys 2014) — standard reference; not retrieved in this session [NOT FETCHED].
- ARF mechanics (Gomes et al. 2017): each Hoeffding tree has its own ADWIN; a warning starts a background tree, a drift signal replaces the tree. — [Gomes et al. ARF PDF](https://files01.core.ac.uk/download/pdf/85165409.pdf); River API [HoeffdingAdaptiveTreeRegressor](https://riverml.xyz/dev/api/tree/HoeffdingAdaptiveTreeRegressor/)
- Minato, Popineau, Rimmel, Doan (Université Paris-Saclay/CNRS), "The Blind Spot Paradox" [PREPRINT, arXiv 2610.05853, Oct 2026]: incremental leaf updates in ARF absorb ~98.6% of the post-drift error transient, starving cumulative monitors (CUSUM, Page-Hinkley; also DDM/EDDM-type). On simulated ARMA-GARCH financial streams (ProteuS; SPY, PFF, VNQ, BWX; 12 transitions × 30 seeds) Page-Hinkley on ARF detected 0/1,080 shifts (F1=0.00) vs F1 0.73-0.96 on a static RF. Windowed detectors (ADWIN, KSWIN) are not starved the same way; KSWIN+ARF F1=1.00 (different false-alarm budget). Noisy streams cause false-alarm flooding (PHT+ARF: 86 alarms for 1 true drift on INSECTS). Bank fraud tabular data: detector F1 ≈ 0.00-0.11 (weak-signal regime). River's default ADWIN check every 32 steps adds delay (implementation artifact). — [arXiv HTML](https://arxiv.org/html/2610.05853)
- Delayed labels ("verification latency") is a recognized sub-field: label-based drift detection breaks down when labels arrive late; fallbacks are covariate (data) drift detection or semi-supervised methods. — [Alencar et al., experimental survey, Digital Signal Processing 2026](https://researchcommons.waikato.ac.nz/items/cb76efe3-148d-49a8-b406-b1a6531e599f); [Survey on delayed partially labelled streams, arXiv 2106.09170](https://arxiv.org/pdf/2106.09170); [Umer & Polikar, extreme verification latency](https://arxiv.org/pdf/2011.14917); [Frouros docs](https://frouros.readthedocs.io/en/stable/_sources/concepts.md)
- Proceed (Zhao & Shen; arXiv 2412.08435 — venue believed KDD 2025, not verified): in online time-series forecasting, ground truth is available only after the forecast horizon, so the gap between latest trainable samples and the test sample "can introduce concept drift, causing forecast models to adapt to outdated concepts"; most online methods ignore this. — [arXiv](https://arxiv.org/abs/2412.08435)
- ProteuS: generative simulator of concept drift in financial markets (used as testbed above). — [arXiv 2509.11844](https://arxiv.org/pdf/2509.11844) [PREPRINT]
- Regol et al., "When to retrain a machine learning model" (ICML 2025): retraining decisions are hard because information is limited, shift nature/impact unknown, and a cost ratio between retraining and poor performance must be specified. Not finance-specific. — [PMLR v267](https://proceedings.mlr.press/v267/regol25a.html)

### Inferences
- For a trading bot with N-day labels, any online update at time t can only use labels ending ≤ t−N (purge/embargo needed exactly as in walk-forward). "Continuous" learning thus does not remove the lag; it only shortens the refit interval.
- Using drift detectors as retrain triggers in crypto is risky: low SNR means either missed alarms or alarm floods; an ARF-type self-adapting model hides the evidence that external monitors need. A safer design: monitor a *frozen* reference model's errors / feature distributions (windowed tests like ADWIN/KSWIN) as an alarm, and let alarms trigger a human-gated, pre-registered retrain + validation, not an automatic update.

### Gaps
- No real-crypto benchmark of ADWIN/DDM/PH/KSWIN false-alarm rates on returns was found (only simulated GARCH streams).

## Q3. Catastrophic forgetting / continual learning (replay, EWC) in finance

### Takeaway
No trading study demonstrating that replay or EWC improves net OOS trading performance was found. Evidence is from other domains (vision, power forecasting) plus one RL market-making preprint listing EWC/rehearsal/freezing as mitigations.

### Cited Findings
- EWC uses Fisher information to penalize changes to parameters important for prior data; replay keeps/regenerates old samples; replay-style generators beat EWC on most tasks in a vision comparison, with EWC failing on disjoint tasks. — [Replay processes thesis, arXiv 2007.00487](https://arxiv.org/pdf/2007.00487); [Deep Generative Replay, arXiv 1705.08690](https://arxiv.org/pdf/1705.08690)
- Online EWC applied in non-stationary power forecasting. — [arXiv 2606.24955](https://arxiv.org/pdf/2606.24955) [PREPRINT]
- RL market-making preprint treats EWC, data rehearsal and layer freezing as forgetting mitigations in non-stationary markets. — [arXiv 2507.18680](https://arxiv.org/pdf/2507.18680) [PREPRINT]
- RCARF's "concept history" (storing inactive trees to reuse for recurring market regimes) is effectively a replay/memory mechanism for stream trees in markets. — [Entropy 2019](https://doi.org/10.3390/e21010025)
- Stock-price incremental Transformer frames the problem as stability-plasticity. — [PMC11729973](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11729973/)

### Inferences
- Crypto regimes recur (bull/bear/chop); a model that keeps updating on recent data will forget the last bear market just before it returns. Expanding-window retrains (or replay of all history) are the simplest anti-forgetting device and are what GKX use.

### Gaps
- No finance paper with net-of-cost OOS evidence for EWC/replay.

## Q4. RL that keeps learning live: instability and overfitting

### Takeaway
DRL trading results are fragile: high run-to-run variance, backtest overfitting, poor generalization under regime shift. Even proposed fixes are tested on very short windows. No credible evidence was found that live-updating RL agents outperform OOS.

### Cited Findings
- Gort, Liu, Sun, Gao, Chen, Wang [PREPRINT, arXiv 2209.05559]: prior DRL trading papers "optimistically reported increased profits in backtesting" that may be false positives from overfitting; they estimate probability of overfitting (hypothesis test) and reject overfitted agents. Test set: 10 cryptos, 05/01/2022-06/27/2022 (~2 months). Less-overfitted agents beat more-overfitted ones, equal weight, and S&P BDM index (no further numbers in abstract). Note: the evaluation window is very short; this is a proposed fix, not an independent audit. — [arXiv](https://arxiv.org/abs/2209.05559)
- Same paper (per search snippet): standard walk-forward validates in a single market situation and the validation period may be biased (e.g., a strong uptrend). — [arXiv HTML v6](https://arxiv.org/html/2209.05559v6)
- PRUDEX-Compass (TMLR 2023, NTU): FinRL evaluation focuses only on profit; proposes 6 axes / 17 measures incl. reliability and universality. — [arXiv 2302.00586](https://arxiv.org/pdf/2302.00586)
- A ScienceDirect 2026 article "Unstable Gains: Multiplicity-Aware Evaluation of Financial Deep Reinforcement Learning" (snippet only; page returned 403): DRL results vary across training runs; single-run backtests in volatile assets overstate performance and "regime adaptation". Could not verify authors/numbers. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2405918826000309) [NOT FETCHED; contents unverified]
- 2026 crypto multi-pair DRL preprint argues end-to-end learned policies generalize poorly under regime shift and proposes a more constrained design. — [arXiv 2606.04574](https://arxiv.org/html/2606.04574v1) [PREPRINT]
- Bailey, Borwein, López de Prado, Zhu, Probability of Backtest Overfitting (J. Computational Finance 2017) and Deflated Sharpe Ratio (2014) are the standard statistical tools here (cited via reference lists only). — [NOT FETCHED]

### Inferences
- A live-learning RL agent multiplies the selection/overfitting problem: every update is a new, unvalidated model deployed with real capital. Safe pattern: train offline, freeze, shadow-test the candidate vs incumbent on paper/testnet, promote only through pre-registered gates (multiple seeds, PBO/DSR).

### Gaps
- No safe-RL (constrained/shielded RL) trading study with OOS net results was retrieved.

## Q5. Practitioner/academic recommendations on retrain frequency

### Takeaway
Leading academic ML-in-finance work refits infrequently (annually, expanding window); practitioner commentary emphasizes hype/caution rather than continuous learning. Model-update policy should be a tuned, pre-registered hyperparameter with equal treatment of baselines.

### Cited Findings
- GKX annual refit with expanding training window and rolling validation (see Q1). — [NBER PDF](https://www.nber.org/papers/w25398.pdf)
- Audrino-Chassot: fitting scheme must be specified carefully; poorly specified baseline schemes inflate ML's apparent edge. — [arXiv 2406.08041](https://arxiv.org/abs/2406.08041)
- Pesaran-Timmermann / Pesaran-Pick: average across estimation windows for robustness to unknown breaks. — [Timmermann PDF](https://rady.ucsd.edu/_files/faculty-research/timmermann/estimation-window.pdf); [CESifo](https://www.cesifo.org/DocDL/cesifo1_wp2293.pdf)
- Man AHL's chief scientist Anthony Ledford (Bloomberg, via HedgeCo) called much ML hype overblown — ML more robust than predecessors but not revolutionary. Undated, secondary. — [HedgeCo](https://www.hedgeco.net/news/?p=55229)
- Regol et al. (ICML 2025): retrain decision should weigh retraining cost vs performance loss under uncertainty. — [PMLR](https://proceedings.mlr.press/v267/regol25a.html)
- Many "adaptive" crypto ML studies report strong in-sample but collapsed OOS performance (thesis-level evidence). — [DiVA thesis](https://www.diva-portal.org/smash/get/diva2:1970546/FULLTEXT01.pdf); [Tilburg thesis](http://arno.uvt.nl/show.cgi?fid=189524)

### Inferences (practical recommendation for this project)
1. Keep scheduled walk-forward retraining (monthly or less frequent) with purge/embargo as the default; do not switch to per-bar online updating without a pre-registered head-to-head test.
2. If testing "continuous learning", pre-register both arms (same features, labels, costs, purge), tune window/frequency for both, evaluate on SHA-locked OOS with shuffled-label control — consistent with project rules.
3. Prefer window averaging (e.g., ensemble of models on 1y/2y/3y/expanding windows) over a single hard time-decay; if decay is used, half-life must be chosen in walk-forward and reported with sensitivity.
4. Use drift detection only as a monitoring alarm on a frozen model (windowed detectors ADWIN/KSWIN on errors and feature distributions), triggering human-gated champion/challenger shadow evaluation — not automatic live updates.
5. Never let an RL agent or online learner update the live trading model directly; candidate models go to testnet shadow mode first.

### Gaps
- No Two Sigma or Man AHL primary publication on retrain frequency was retrieved.
- López de Prado's own discussion (Advances in Financial ML, ch. 4 sample weights/time decay) not fetched directly; only secondary implementations cited.
