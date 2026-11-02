# Precomputed Market Knowledge Store (Point-in-Time Feature Store) and Controlled Learning / Model Governance for an ML Trading System

Researcher notes, 2026-10-17. Scope: (a) point-in-time (PIT) feature stores and trading-specific leakage hazards; (b) per-decision records; (c) MFE/MAE; (d) controlled learning and governance; (e) online vs walk-forward retraining evidence.
Notation used below: "Inference" = my reasoning from the cited findings, not a sourced fact. Items I could not verify from a primary source are moved to Gaps.

**Important update found during research:** SR 11-7 (2011) has been **superseded** (April 17, 2026) by revised interagency guidance from the Fed, OCC and FDIC (Fed letter SR 26-2). Any report that cites "SR 11-7" as current should say it is superseded. Details under Q3.

---

## Q1. What design patterns guarantee no look-ahead in multi-timeframe features? (feature stores, as-of joins, bitemporal data, versioning, lineage, trading leakage hazards)

### Takeaway
Production feature stores prevent leakage with one core rule: for each training/decision row (the "spine", keyed by entity + timestamp), join only the latest feature value whose timestamp is <= that row's timestamp (an as-of / point-in-time join), optionally also requiring that the value had been *created/available* by then (a second, "knowledge/processing" time). In trading, the leakage risk comes less from the join and more from *what timestamp you stamp on a feature*: a value must be stamped with the time it became knowable (bar close + confirmation lag), not the time of the event it describes (e.g., a pivot's bar).

### Cited Findings

**Feature-store PIT joins (production tooling)**
- Feast: for each entity row, "Feast will scan backward in time from the entity dataframe timestamp up to a maximum of the TTL time"; TTL "is relative to each timestamp within the entity dataframe." — [Feast docs: Point-in-time joins](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)
- Feast: by default only the event timestamp constrains the join; a `created_timestamp_column` only breaks ties between rows with the same event timestamp (highest created wins), so **backfilled or corrected values can still leak into earlier training rows**. The option `filter_by_created_timestamp=True` restricts each entity row to feature values *created at or before* its timestamp, approximating what the online store would have served; rows with NULL created timestamp are excluded and unsupported stores raise an error. — [Feast docs](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)
- Hopsworks: "a point-in-time correct join is a temporal join between two tables"; it "starts with the timestamps for the labels and retrieves the most recent feature values"; in SQL it is an ASOF LEFT JOIN; the failure mode is "information from the future is unintentionally used for training" (label leakage). — [Hopsworks dictionary: point-in-time correct joins](https://www.hopsworks.ai/dictionary/point-in-time-correct-joins)
- pandas `merge_asof`: `direction='backward'` "selects the last row in the right DataFrame whose 'on' key is less than or equal to the left's key"; `allow_exact_matches=False` makes it strictly less-than; `tolerance` caps staleness; `by` matches per symbol; both frames "must be first sorted by the merge key". — [pandas docs: merge_asof](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html)
- Uber Michelangelo: shared Feature Store with canonical feature names, owner/description/SLA metadata (~10,000 features at time of writing); same batch pipeline feeds training and serving; near-real-time features (Kafka/Samza) are written to Cassandra *and logged to HDFS for training*; feature transforms are DSL expressions where "the same expressions are applied at training time and at prediction time." — [Uber Engineering: Meet Michelangelo](https://www.uber.com/blog/michelangelo-machine-learning-platform/)
- Google ML Test Score, Monitor 3: "Training and serving features compute the same values"; different code paths for the same feature cause "training/serving skew" that "requires careful monitoring". — [Breck et al. 2017, The ML Test Score](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/)
- Sculley et al. (NeurIPS 2015) on *unstable data dependencies*: input signals that change behaviour over time (e.g., produced by another model or lookup table) are dangerous because "even 'improvements' to input signals may have arbitrary detrimental effects"; mitigation is "to create a versioned copy of a given signal" (frozen until vetted), at the cost of staleness and maintaining versions. — [Hidden Technical Debt in ML Systems](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)
- Sculley et al.: "CACE principle: Changing Anything Changes Everything"; also warns of glue code, "pipeline jungles", undeclared consumers and hidden feedback loops — including the example of "two stock-market prediction models from two different investment companies" influencing each other. — [Hidden Technical Debt in ML Systems](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

**Trading-specific leakage hazards**
- ZigZag / swing pivots: the newest leg keeps extending to each new extreme and only freezes once price reverses by the threshold, so pivots are confirmed late; buying at ZigZag lows in a backtest trades on points identified only later (look-ahead). A single-author (non-peer-reviewed) backtest port of MetaQuotes ZigZag(12/5/3) on SP500 H1 reported ~81% of drawn newest pivots later repaint away. "No-repaint" variants simply wait a fixed number of bars (e.g., 5–8) for the fractal to confirm. — [abctradinggroup: repainting explained](https://www.abctradinggroup.com/indicator-repainting); [forge.mql5.io pivot_expectancy research script](https://forge.mql5.io/aron3/Warrior_EA/src/branch/main/research/pivot_expectancy_stock.py); [NinjaTrader forum: ZigZag slow to update](https://ninjatrader.com/support/forum/forum/ninjatrader-7/indicator-development-aa/51112-zigzag-very-slow-to-update-why) (evidence quality: practitioner, not academic — flagged)
- Higher-timeframe (HTF) values from a partially formed bar: TradingView Pine docs state HTF values often repaint because "a historical bar on the chart might include data from a realtime bar on the HTF"; their non-repainting recipe is `request.security(..., close[1], lookahead=barmerge.lookahead_on)` — i.e., offset by one HTF bar; without the offset, `lookahead_on` "will look to the future states of historical HTF bars". The cost: new HTF data is only available from the open of the next HTF bar. — [TradingView Pine FAQ: other data and timeframes](https://tradingview.com/pine-script-docs/faq/other-data-and-timeframes); [TradingView "Higher-timeframe requests" publication](https://www.tradingview.com/script/W1YpYcOI-Higher-timeframe-requests/)
- Overlapping labels / CV leakage: Lopez de Prado (AFML 2018, Ch. 7 "Cross-Validation in Finance") introduced purging (drop training observations whose label windows overlap the test period) and an embargo (buffer after the test set); combinatorial purged CV (CPCV) is the extension. — [Wikipedia: Purged cross-validation](https://en.wikipedia.org/wiki/Purged_cross-validation); [fynance CPCV docs citing Ch. 7](https://fynance.readthedocs.io/en/latest/generated/fynance.data.combinatorial_purged_cv.html); [mizarlabs docs](https://mizarlabs.readthedocs.io/en/latest/mizarlabs.model.html) (secondary sources; book text not directly accessed)
- Survivorship in crypto: Stöckl (2022, Financial Markets and Portfolio Management) over 3,904 coins 2014–2021 estimated annualized survivorship bias of 0.93% (value-weighted) vs 62.19% (equal-weighted), and a size premium overstated by about half in survivor-only samples. — [Univ. St. Gallen repository](https://alexandria.unisg.ch/handle/20.500.14171/108037) (figures as reported in search summary; full paper not opened — verify before quoting)
- CoinGecko data (as reported by ForkLog): 14,039 of >24,000 listed projects counted as "died" 2014–2023. — [ForkLog](https://forklog.com/en/why-the-crypto-market-is-not-immune-to-survivorship-bias/) (secondary)
- Bar alignment/timezone on Binance: klines are "uniquely identified by their open time"; each kline has open time (index 0) and close time (index 6); with the `timeZone` parameter "kline intervals are interpreted in that timezone instead of UTC", but "`startTime` and `endTime` are always interpreted in UTC". — [Binance Spot API: market data endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)

### Inferences
Design patterns that, together, guarantee no look-ahead (my synthesis):
1. **Two timestamps per feature row (bitemporal-lite):** `event_time` (what period the value describes, e.g., bar open) and `available_at` (earliest wall-clock time the value was knowable = bar close time + data latency + confirmation lag). **Joins must key on `available_at`, never `event_time`.** This mirrors Feast's `created_timestamp` + `filter_by_created_timestamp` behaviour. Restated/backfilled data gets a new row with a later `available_at`; never overwrite.
2. **Stamp by Binance open-time convention carefully:** since klines are keyed by open time, a naïve join of a 1d bar (keyed 00:00 UTC) to a 5m decision at 10:00 UTC the same day injects that day's unfinished close. The fix is to stamp HTF features at `close_time` (open + interval) and join backward.
3. **Confirmation-lag features:** pivots, ZigZag legs, support/resistance and fractals must be emitted at the bar where they were *confirmed* (e.g., pivot high at bar t with k right-side bars is only available at t+k close). Store `pivot_bar_time` as a payload field but `available_at = confirm_bar_close`.
4. **Bar-by-bar replay test (invariance test):** recompute every feature using data truncated at each decision time and assert equality with the precomputed store. Any mismatch = look-ahead/repaint. This is a concrete implementation of ML Test Score Monitor 3 (train/serve parity).
5. **Single code path:** the same feature function computes the offline store and the live value (Michelangelo DSL pattern).
6. **Versioned, immutable feature definitions:** `feature_name@version` + code hash + source-data SHA; a model records the exact feature versions it was trained on (Sculley's "versioned copy" mitigation; fits this project's SHA-lock rule).
7. **Point-in-time universe:** the tradable coin set at time t is a feature too (listing/delisting dates), to avoid survivorship bias.
8. **Purged + embargoed CV** whenever labels span multiple bars (e.g., triple-barrier / N-bar forward returns).

### Gaps
- Tecton and Hopsworks official docs on bitemporal "time travel"/Hudi commit time were not fetched; the Hopsworks claim above is from its dictionary page only.
- I did not find a primary Binance statement on whether the most recent kline returned by REST is incomplete (practitioner knowledge says it is — the last kline is the live, still-forming bar — but unverified here). Weekly (1w) and monthly (1M) kline boundary conventions (week start day, calendar month) were also not verified from Binance docs.
- Stöckl survivorship numbers come from a search summary; the paper itself was not opened.
- No peer-reviewed quantification of ZigZag/pivot look-ahead found; evidence is practitioner-level.

---

## Q2. How should higher-timeframe context (daily, weekly) be joined to lower-timeframe decisions (5m, 1h) without using an unfinished higher-timeframe bar?

### Takeaway
Use a backward as-of join keyed on the HTF bar's **close/availability time**, with strict inequality if decisions happen at the same instant as the HTF close, so each 5m/1h decision only sees the last *completed* daily/weekly bar. This is the same idea as TradingView's `close[1]` + `lookahead_on` recipe and Feast/Hopsworks PIT joins.

### Cited Findings
- TradingView's documented non-repainting HTF method offsets the HTF expression by one bar (`close[1]`) with `lookahead_on`; without the offset, results "look to the future states of historical HTF bars, retrieving values before the times at which they're available"; new HTF values become available only at the open of the subsequent HTF bar. — [TradingView Higher-timeframe requests](https://www.tradingview.com/script/W1YpYcOI-Higher-timeframe-requests/); [Pine FAQ](https://tradingview.com/pine-script-docs/faq/other-data-and-timeframes)
- `merge_asof(direction='backward', allow_exact_matches=False, tolerance=..., by='symbol')` implements "last value strictly before" with a staleness cap. — [pandas merge_asof](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html)
- Feast TTL acts as a staleness cap measured per entity row. — [Feast docs](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)
- Binance klines keyed by open time; timezone parameter changes interval interpretation but start/end are UTC. — [Binance API docs](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)

### Inferences
Recommended recipe (synthesis):
```
htf = daily_bars.assign(available_at = open_time + 1d (+ ingest latency))
ltf = decisions_5m.assign(decision_time = bar_close_time_of_5m)   # decide on closed 5m bars only
X = merge_asof(ltf.sort_values('decision_time'),
               htf.sort_values('available_at'),
               left_on='decision_time', right_on='available_at',
               by='symbol', direction='backward',
               allow_exact_matches=True,   # only if available_at already includes latency; else False
               tolerance=pd.Timedelta('2d'))
```
- Check: for a 5m decision at 2026-10-17 10:00 UTC, the joined daily row must be 2026-10-16 (closed 2026-10-17 00:00), never 2026-10-17.
- If a "partial current HTF bar" is desired as a feature (e.g., today's running high), compute it explicitly from the LTF bars up to `decision_time` (a causal rolling aggregation), and name it differently (`d1_partial_high`) so it is never confused with completed-bar features.
- Use UTC everywhere; Binance `timeZone` alters bar boundaries, so mixing timezones would misalign daily bars.
- Weekly/monthly: same rule; additionally verify Binance's week/month boundary convention (Gap).
- Unit tests: (1) assert `joined.available_at <= decision_time` for all rows; (2) bar-by-bar replay equality; (3) a deliberate "leak canary" (feed the future close) should make backtest performance jump — confirming the test harness can detect leakage.

### Gaps
- No academic paper specifically on multi-timeframe join correctness in trading was found; guidance comes from tooling docs and practitioner sources.

---

## Q3. What do regulators/industry recommend for model validation and change control? (SR 11-7 and successor, ML Test Score, Hidden Tech Debt, model registry, champion-challenger, shadow mode, rollback, per-decision records)

### Takeaway
Regulatory guidance (SR 11-7 → superseded April 2026 by risk-based interagency guidance SR 26-2) centers on: model inventory, documentation, independent "effective challenge", validation = conceptual soundness + outcomes analysis (e.g., backtesting) + ongoing monitoring, governance proportionate to model risk. Engineering guidance (Google) operationalizes this: canary/shadow before serving, quick rollback, reproducible training, staleness tests, prediction-bias and action-limit monitoring. Registries (MLflow) provide versioned models with mutable aliases (e.g., `champion`) for controlled promotion/rollback.

### Cited Findings

**Regulatory**
- Revised interagency guidance (FRB, OCC, FDIC; April 2026) **supersedes and replaces** FRB SR 11-7, OCC Bulletin 2011-12, the OCC "Model Risk Management" handbook booklet, FDIC FIL 22-2017, and related BSA/AML statements. — [KPMG Regulatory Alert, April 2026](https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2026/model-risk-management-revised-interagency-guidance-reg-alert.pdf); [Federal Reserve: Supervisory Guidance on Model Risk Management (SR 26-2, dated April 17, 2026)](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm)
- Revised guidance: model = "a complex quantitative method, system, or approach that applies statistical, economic, or financial theories to process input data into quantitative estimates"; includes AI models but **excludes generative and agentic AI** from formal scope; excludes simple arithmetic and deterministic rule-based processes. Not enforceable standards; supervisory criticism arises only when insufficient risk management is linked to unsafe/unsound practice. Risk-based: rigor "commensurate" with inherent risk and materiality; generally aimed at banks >$30bn. — [KPMG alert](https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2026/model-risk-management-revised-interagency-guidance-reg-alert.pdf); [Fed SR 26-2 page](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm)
- Validation components (revised guidance): conceptual soundness of design (assumptions, data selection), construction (interpretability, benchmarking) and testing; **outcomes analysis** vs real-world outcomes, e.g., "standalone activities such as back-testing or outlier analysis"; ongoing monitoring of whether the model performs as expected given changes in data or market conditions. Validation generally before first use; timing/frequency depends on "frequency and scope of model changes". — [Fed SR 26-2 page](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm); [KPMG alert](https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2026/model-risk-management-revised-interagency-guidance-reg-alert.pdf)
- Effective challenge: "critical analysis conducted by objective experts" with expertise, independence and organizational standing to effect change (revised); original SR 11-7 framed it as depending on incentives, competence and influence. — [Fed SR 26-2 page](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm); [Fed SR 11-7 letter (now superseded)](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm) (the 2011 page returned 404 on fetch; wording via search snippet)
- Governance: model inventory with information sufficient to understand individual and aggregate risk; documentation to "track recommendations, responses, exceptions and effectively manage model changes/updates and remediation"; vendor models held to the same principles. Note: the Fed page itself does not define a formal change-control process or "material change". — [KPMG alert](https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2026/model-risk-management-revised-interagency-guidance-reg-alert.pdf); [Fed SR 26-2 page](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm)

**Engineering governance (Google)**
- ML Test Score: 28 tests in 4 groups (Data, Model, Infrastructure, Monitoring). Scoring: ½ point per test executed manually and documented; 1 point if automated and repeated; sum per section; **final score = minimum across the 4 sections**. Interpretation: 0 = research project; (0,1] serious holes; (1,2] first-pass productionization; (2,3] reasonably tested; (3,5] strong automated testing "appropriate for mission-critical systems"; >5 exceptional. — [Breck et al. 2017 (PDF)](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- Model tests include: "The impact of model staleness is known" — explicitly citing "financial ML applications" as rapidly changing, non-stationary; recommended method is a small A/B with older models to get an "age-versus-quality curve"; "A simpler model is not better" (regularly compare with a baseline). — [ML Test Score](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- Infra tests: training is reproducible; pipeline integration-tested; model quality validated before serving; "Models are canaried before serving" (run old and new concurrently, new model on a small, gradually increased fraction of traffic); "Serving models can be rolled back" — rollback should be practiced "normally, when not in emergency conditions". — [ML Test Score](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- Monitoring tests: dependency changes notify; data invariants hold; train/serve not skewed; models not too stale; numerically stable; no computing-performance regression; no prediction-quality regression — with thresholds set (e.g., from launch-time bounds) and both "dramatic and slow-leak regressions" monitored. — [ML Test Score](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- Sculley et al. monitoring: **prediction bias** (distribution of predicted labels should equal observed labels — a useful diagnostic for sudden world changes); **action limits** ("set and enforce action limits as a sanity check" in systems that act in the real world, firing alerts and manual intervention); monitor upstream producers; also warns about **fixed thresholds in dynamic systems** (manually set decision thresholds become invalid when the model updates). — [Hidden Technical Debt](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

**Registry, shadow, champion-challenger, per-decision logging**
- MLflow Model Registry: registered model has "a unique name, contains versions, aliases, tags"; aliases are mutable references (e.g., `champion` → version N, loadable as `models:/MyModel@champion`), so reassigning the alias changes which version serves; tags like `validation_status:approved`; each version links to the run/notebook that produced it (lineage). — [MLflow docs: Model Registry](https://mlflow.org/docs/latest/ml/model-registry/)
- Shadow testing (AWS SageMaker): a copy of live requests is routed to the shadow variant; "Only the responses of the production variant are returned to the calling application"; shadow responses can be logged for offline comparison before promotion. — [AWS SageMaker: Shadow tests](https://docs.aws.amazon.com/sagemaker/latest/dg/shadow-tests.html)
- Michelangelo per-model metadata: who trained it and when, full config (features, hyperparameters, compute), references to train/test datasets, feature distributions/importance, accuracy metrics/charts, learned parameters; models deployed by UUID + tag; A/B via experimentation framework; predictions logged and later **joined with observed outcomes** to measure live accuracy with threshold alerts. — [Uber Michelangelo](https://www.uber.com/blog/michelangelo-machine-learning-platform/)

### Inferences
Per-decision record ("decision ledger") schema, synthesized from Michelangelo + ML Test Score + MRM documentation expectations:
- `decision_id`, `decision_time (UTC)`, `symbol`, `timeframe`
- `feature_vector` (or hash + pointer into PIT store) with `feature_set_version`, `data_snapshot_sha`, max `available_at` among inputs (must be <= decision_time; assert at write)
- `model_name`, `model_version`, `registry_alias` (champion / challenger / shadow), `code_git_sha`
- `raw_output` (probabilities/scores), `threshold_used`, `action` (incl. "no trade"), `risk_overrides` (governor vetoes, action-limit hits)
- Execution: intended vs filled price, fees, slippage
- Outcome (written later, append-only): realized PnL, label at horizon, MFE, MAE, bars held, exit reason
- Make the ledger append-only and hash-chained so it can serve as independent-verifier evidence (consistent with this project's SHA-lock rule).
Champion–challenger in a trading bot: challenger runs in **shadow** (paper decisions logged against the same inputs, no orders) for a pre-registered period; promotion requires pre-registered gates (e.g., out-of-sample metric beats champion and a shuffled-label control, no regression in drawdown); promotion = alias flip; rollback = alias flip back (practiced routinely per ML Test Score Infra 7). Because the revised MRM guidance is risk-based and non-prescriptive, a solo/retail operator should treat it as a checklist of principles, not a compliance requirement.

### Gaps
- Original SR 11-7 full text (2011 PDF) could not be fetched (404 on Fed URLs during this session); its specific wording on change control is not quoted here.
- No authoritative source located for a formal "champion–challenger" standard in trading; shadow-mode evidence is from a cloud vendor doc.

---

## Q4. MFE/MAE analysis as a research tool — sources and pitfalls

### Takeaway
MAE (worst unrealized loss during a trade) and MFE (best unrealized gain) are attributed to John Sweeney's work on adverse excursion (mid-1990s) and are used to calibrate stops/targets by plotting excursions against final outcome. Primary-source access was not achieved; most available material is practitioner-level.

### Cited Findings
- Sweeney is credited with introducing MAE; NexusFi states his 1996 book "Maximum Adverse Excursion" (publisher listing not found). — [NexusFi wiki: MAE](https://nexusfi.com/wiki/trading-wiki/Maximum-Adverse-Excursion)
- Sweeney proposed analyzing adverse excursion as a rational basis for stop placement and plotting each trade's MAE/MFE against its final outcome to show where stops and targets belong; winners tend to cluster at low MAE. — [LuxAlgo: MAE/MFE-informed management](https://www.luxalgo.com/library/concept/mae-mfe-informed-management.md); [LuxAlgo: MAE/MFE distributions](https://www.luxalgo.com/library/concept/mae-mfe-distributions.md)
- Rule-of-thumb claims (e.g., "place stop to retain 75–85% of winners") come from user posts, not Sweeney. — [TradingView community post](https://pl.tradingview.com/chart/BTCUSD/vvTceYm2-Adverse-excursion-a-key-concept-for-risk-management) (low reliability)

### Inferences (pitfalls — my reasoning, not sourced)
- **Intrabar path ambiguity:** with OHLC bars you don't know whether the high or low came first; MFE/MAE on the entry/exit bar is ambiguous. Use finer data (1m) for excursion paths.
- **Circularity / overfitting:** choosing stops from the MAE distribution of the same trades used for evaluation is in-sample optimization; MAE-derived stops must be chosen on training folds and validated out-of-sample (purged).
- **Stop changes the distribution:** MAE measured under one stop level truncates the distribution; changing the stop changes which trades survive (path dependence).
- **Normalize** excursions by volatility (e.g., ATR at entry) so different regimes/coins are comparable.
- **As labels:** MFE/MAE use future bars by definition — legitimate as *outcome/label* fields in the decision ledger, never as features.
- **Fees/slippage and funding** shift effective MFE/MAE in crypto.

### Gaps
- Sweeney's book/articles (e.g., Technical Analysis of Stocks & Commodities) not accessed; bibliographic details unverified.
- No peer-reviewed study of MFE/MAE-based stop optimization out-of-sample was found.

---

## Q5. Is online learning better than walk-forward retraining for trading models? Evidence (incl. drift detection: ADWIN, PSI, KS, performance-based)

### Takeaway
There is **no strong direct evidence** that online/continual learning beats periodic walk-forward retraining for trading. Landmark finance-ML work (Gu, Kelly & Xiu 2020) used annual refits with an expanding window. A recent (non-peer-reviewed) large streaming-ML study found periodic retraining beat drift-triggered retraining under abrupt/gradual drift, with reactive triggers only helping under recurring drift. Drift detectors (ADWIN, PSI, KS) are useful as *monitors/alerts*, but PSI's popular 0.1/0.25 thresholds lack statistical grounding.

### Cited Findings
- Gu, Kelly & Xiu (RFS 2020): "We divide the 60 years of data into 18 years of training sample (1957 - 1974), 12 years of validation sample (1975 - 1986), and the remaining 30 years (1987 - 2016) for out-of-sample testing... we avoid recursively refitting models each month. Instead, we refit once every year... Each time we refit, we increase the training sample by one year. We maintain the same size of the validation sample, but roll it forward". Trees and neural nets performed best; dominant predictors were momentum, liquidity and volatility variants. — [NBER w25398](https://www.nber.org/papers/w25398.pdf); [SSRN abstract](https://papers.ssrn.com/abstract=3159577)
- Dasari (arXiv 2608.19488, Aug 2026, single-author preprint): 3,933 runs, 3 datasets, 3 drift regimes; compared periodic, error-threshold, ADWIN-triggered, and no-retrain. Findings: whether the model learns **incrementally** mattered more than the retraining policy (with per-sample updates, no policy beat no-retrain by a practically significant margin in 54 comparisons); without incremental updates, policy choice moved post-drift accuracy by 15–55 pp; **periodic retraining significantly outperformed reactive policies under abrupt and gradual drift**; reactive advantage only under recurring drift (not significant after multiple-comparison correction per search summary); documented a latency-budget queueing effect that silently halves effective retraining budgets. Caveat: incremental result is for a linear online learner with *immediate labels* — trading labels are delayed. — [arXiv 2608.19488](https://arxiv.org/abs/2608.19488)
- Gama, Žliobaitė, Bifet, Pechenizkiy, Bouchachia, "A Survey on Concept Drift Adaptation", ACM Computing Surveys 46(4), 2014: defines concept drift as a change over time in the relationship between inputs and target; categorizes adaptation strategies and evaluation. — [Bournemouth eprint](https://eprints.bournemouth.ac.uk/22491/); [DOI 10.1145/2523813](https://api.crossref.org/works/10.1145/2523813)
- ADWIN (Bifet & Gavaldà, SIAM SDM 2007): window length adapts online to the observed rate of change; formal bounds on false-positive and false-negative rates; ADWIN2 is the efficient bucketed version using Hoeffding-type tests to drop the older sub-window when means differ. — [Paper record (IP Paris)](https://researchportal.ip-paris.fr/en/publications/learning-from-time-changing-data-with-adaptive-windowing/); [scikit-multiflow ADWIN docs](https://scikit-multiflow.readthedocs.io/en/latest/api/generated/skmultiflow.drift_detection.ADWIN.html)
- PSI: the 0.1 / 0.25 traffic-light thresholds (attributed to Lewis) are widely used, but Yurdakul (2018 WMU dissertation; Yurdakul & Naranjo, J. Risk Model Validation) show a rescaled PSI is asymptotically chi-square and argue for critical values that depend on sample size and number of bins; Risk.net summary: the 0.10/0.25 use "does not have any support or references in the academic world". — [arXiv 2303.01227 review](https://arxiv.org/pdf/2303.01227); [Risk.net: Statistical properties of the PSI](https://www.risk.net/journal-of-risk-model-validation/7725371/statistical-properties-of-the-population-stability-index); [WMU ScholarWorks](https://scholarworks.wmich.edu/dissertations/3208/)
- ML Test Score explicitly calls financial ML non-stationary and recommends measuring an age-vs-quality (staleness) curve to set update frequency. — [ML Test Score](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- Sculley et al.: models that act in the world create direct/hidden feedback loops (a model influencing its own future training data) — relevant to online learning on one's own executed trades. — [Hidden Technical Debt](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)
- Time-varying neural network for stock returns (arXiv 2003.02515) argues the true model is "noisy, complex and time-varying" and uses per-interval training, but does not run a head-to-head vs periodic retraining. — [arXiv 2003.02515](https://arxiv.org/html/2003.02515)

### Inferences
- For a daily/intraday crypto system with **delayed labels** (outcome known only after the holding horizon), naïve online updating is risky: labels arrive late, feedback loops exist, and each update is an unvalidated model change (conflicts with MRM "validate before use"). The defensible default is **scheduled walk-forward retraining** (expanding or rolling window, purged/embargoed), with each retrained model treated as a *challenger* that must pass pre-registered gates in shadow before alias promotion.
- Use drift detectors as **alerts that trigger review or an early challenger build**, not as auto-deploy triggers: ADWIN on a stream of realized per-trade errors/returns (performance-based drift), PSI/KS on feature distributions (data drift), and prediction-bias checks (Sculley). Set PSI/KS thresholds via sample-size-aware critical values or via a null distribution computed on historical non-drift periods, not 0.1/0.25 folklore.
- Determine retrain cadence empirically via the ML Test Score staleness curve: backtest models of different ages on the same OOS period and see how quickly edge decays.
- Note on multiple testing: every retrain/promotion is another trial; keep a trial count for deflated-Sharpe-style corrections (Lopez de Prado concept; not verified in this session).

### Gaps
- No peer-reviewed head-to-head study of online learning vs periodic walk-forward retraining on crypto or equity trading P&L was found. The Dasari preprint is not finance-specific and not peer-reviewed.
- Gama et al. survey content (taxonomy details, whether ADWIN is covered) was not read in full.
- KS-test-specific guidance for financial feature drift (e.g., autocorrelation invalidating i.i.d. assumptions of KS p-values) was not sourced in this session; treat KS p-values on autocorrelated series as unreliable (inference).
- Lopez de Prado's Deflated Sharpe Ratio / trial-counting not verified from source here.
