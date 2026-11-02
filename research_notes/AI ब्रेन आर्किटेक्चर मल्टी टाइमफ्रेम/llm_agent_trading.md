# LLM-based and Multi-Agent AI Trading Systems: Honest Out-of-Sample Evidence (focus: crypto)

Research date: 2026-10-17. About 20 search and fetch calls. Most sources are arXiv preprints (flagged). Numbers marked "(secondary)" come from summaries or press reports and were not checked against the primary PDF.

## Q1. Test periods, costs and baselines in the flagship papers. Did results hold after the model's training cutoff?

### Takeaway
The flagship papers (FinMem, FinAgent, TradingAgents, CryptoTrade, StockBench) were tested on short windows of 2 to 6 months, on 1 to 20 assets, with costs usually missing or not specified. When independent groups re-ran them over longer windows, after the training cutoff, or with costs, the edge over buy-and-hold mostly disappeared. In at least one case (TradingAgents) the published buy-and-hold baseline itself appears wrong.

### Cited Findings
**FinMem / FinAgent, independent long-run re-test (FINSABER, KDD 2026).** Li, Kim, Cucuringu and Ma. Peer-reviewed (KDD '26).
- The original FinMem claim window was 2022-10-06 to 2023-04-10, on TSLA, NFLX, AMZN and MSFT. FinMem reported a TSLA Sharpe of 2.679 and a cumulative return of 61.78%. The re-run with GPT-4o-mini gave a Sharpe of 0.927 and a cumulative return of 19.94%. — [arXiv 2505.07078v5](https://arxiv.org/html/2505.07078v5)
- Over 2004–2024 on the same four stocks, buy-and-hold beat both LLM agents on NFLX, AMZN and MSFT. On AMZN, buy-and-hold had a Sharpe of 0.551 and an annual return of 15.997%, against FinMem's 0.188 and 5.695%. TSLA was the only case where an LLM agent clearly led. — [arXiv 2505.07078v5](https://arxiv.org/html/2505.07078v5)
- On rolling S&P 500 universes that include delisted stocks (63 to 91 symbols), alpha was not significant for either agent. FinMem's alpha was negative in every scenario. Paired t-tests favouring buy-and-hold gave p-values of 3e-6 to 4e-5 against FinMem. — [arXiv 2505.07078v5](https://arxiv.org/html/2505.07078v5)
- Regime behaviour: FinMem's Sharpe was -0.19 in bull years and -0.97 in bear years. FinAgent's was 0.12 in bulls and -0.38 in bears. Buy-and-hold averaged 0.61 in bull years. The authors describe the agents as "too cautious when risk is rewarded and too aggressive when it is penalised." — [arXiv 2505.07078v5](https://arxiv.org/html/2505.07078v5)
- Costs used: $0.0049 per share with a $0.99 minimum per order. FinCon and MarketSenseAI were not re-tested because their code is not open-source. — [arXiv 2505.07078v5](https://arxiv.org/html/2505.07078v5)

**TradingAgents (Xiao, Sun, Luo, Wang; arXiv 2412.20138).** Preprint; the search also surfaced an ICML 2025 listing.
- Claims: a 26.62% cumulative return and a Sharpe of 8.21 on AAPL. The paper's Table 1 lists buy-and-hold on AAPL at -5.23% (Sharpe -1.29). — [arXiv 2412.20138](https://arxiv.org/pdf/2412.20138); [DEV critique](https://dev.to/trow126/the-most-starred-llm-trading-paper-claims-buy-and-hold-lost-523-it-actually-gained-912-1jj6)
- Independent check (a blog post with a preregistered test, so not peer-reviewed): AAPL's adjusted close went from 207.88 to 226.83 between 2024-06-20 and 2024-11-19. That is **+9.12%**, not -5.23%. The baseline is off by about 14 percentage points and has the wrong sign. Costs are not modelled. The repo also has an open look-ahead bias report (Issue #203). — [DEV, trow126, Jul 2026](https://dev.to/trow126/the-most-starred-llm-trading-paper-claims-buy-and-hold-lost-523-it-actually-gained-912-1jj6)
- Sources disagree on the test window: one secondary write-up says 2024-01-01 to 2024-03-29. — [search summary / DigitalOcean](https://www.digitalocean.com/resources/articles/tradingagents-llm-framework)
- Post-cutoff re-run over 2025–2026 with realistic costs: TradingAgents' Sharpe fell from 0.43 gross to 0.22 net, and it underperformed buy-and-hold on 4 of 5 stocks. QuantAgent's Sharpe fell from -0.96 to -1.15. FinMem and QuantAgent dropped "by over 50% in some cases" after the cutoff. These figures come from an alphaXiv summary and were not checked against the PDF. — ["The Alpha Illusion", arXiv 2605.16895, May 2026, preprint](https://www.alphaxiv.org/abs/2605.16895)

**StockBench (Tsinghua and BUPT; arXiv 2510.02209, preprint).**
- Window: 2025-03-03 to 2025-06-30, 82 trading days, chosen to fall after the models' training data. Universe: the top 20 DJIA stocks. **Transaction costs, fees and slippage are not mentioned.** Starting capital was $100k. — [arXiv 2510.02209](https://arxiv.org/html/2510.02209v1)
- Results: the equal-weight buy-and-hold baseline returned 0.4% (max drawdown -15.2%). The best models returned only 1.9% to 2.5% (Kimi-K2 1.9%, Qwen3-235B-Think 2.5%, Claude-4-Sonnet 2.2%, o3 1.9%). GPT-5 returned 0.3% and GPT-OSS-20B -2.8%. In the downturn sub-window (Jan–Apr 2025), **every** LLM agent failed to beat buy-and-hold. The abstract says "most struggle to outperform buy-and-hold," while Table 2 shows 8 of 13 beating it on return, so the paper contradicts itself. — [arXiv 2510.02209](https://arxiv.org/html/2510.02209v1)

**Methodological critique ("The Alpha Illusion", arXiv 2605.16895, preprint).** The paper names three confounders: temporal contamination, unmodelled frictions (commissions, spread, slippage, impact, borrow, **token cost**, latency), and statistical noise. On short windows, the Sharpe ratio's standard error (Lo 2002) is as large as the reported effect, so many 95% confidence intervals include zero. It proposes six reporting protocols (P1–P6) and recommends using the LLM only upstream as an information extractor, not as the final decision-maker. — [alphaXiv 2605.16895](https://www.alphaxiv.org/abs/2605.16895)

### Inferences
- The FinMem claim window (Oct 2022 – Apr 2023) falls before GPT-4o's training cutoff (Oct 2023, per [Lopez-Lira et al.](https://arxiv.org/html/2504.14765v2)). So any re-run with GPT-4o-class models on that window is exposed to contamination by construction.
- Across the sources, the pattern is consistent: short windows plus no costs plus few assets plus pre-cutoff data inflates results, and fixing any one of these erodes most of the claimed edge.

### Gaps
- Primary-PDF verification of the "Alpha Illusion" numbers (seen only through the alphaXiv summary).
- FinCon (NeurIPS 2024) and StockAgent: no independent OOS re-test found. FinCon code is not public, per FINSABER.
- FinMem's original paper (AAAI Spring Symposium) test window and cost settings were not checked in the primary text.

## Q2. LLM memorization and look-ahead in financial backtests, and how to avoid it

### Takeaway
There is strong evidence that frontier LLMs memorize pre-cutoff market data. Prompt instructions ("pretend it is 2010") and masking company names do not remove it. The reliable fixes are post-cutoff-only evaluation, point-in-time (chronologically trained) models, and anonymization (which helps partly, and also removes "distraction").

### Cited Findings
- **Lopez-Lira, Tang and Zhu (University of Florida), "The Memorization Problem" (arXiv 2504.14765 / SSRN 5217505).** Tested GPT-4o (cutoff Oct 2023) and Llama-3.1-70B. — [arXiv](https://arxiv.org/html/2504.14765v2); [SSRN](https://papers.ssrn.com/abstract=5217505)
  - Pre-cutoff recall: S&P 500 daily level error of 0.61% (MAPE) with 80.6% directional accuracy, and 85.2% directional accuracy on monthly S&P returns. Threshold accuracy above 96% on macro rates. It dated WSJ headlines to the exact day 47% of the time.
  - Post-cutoff: S&P level error of 16.87% with 45.7% directional accuracy. Exact-date accuracy on headlines fell to 7.86%.
  - Telling the model to use only pre-2010 data did not help: GDP "forecasts" stayed at 98% accuracy. With masking, GPT-4o identified the company in 100% of anonymized Apple, Meta and Microsoft earnings calls.
  - Recommendations: make post-cutoff data the **primary** test sample, treat judgment tasks such as sentiment on pre-cutoff data as unsafe, and use chronologically consistent models.
- **Glasserman and Lin (Columbia), "Assessing Look-Ahead Bias in Stock Return Predictions Generated by GPT Sentiment Analysis" (arXiv 2309.17322; later in the Journal of Financial Data Science per secondary citation).** Anonymized headlines did *better* in-sample, which means the "distraction effect" (general company knowledge) outweighed look-ahead. The effect was strongest for large caps. Anonymization is recommended for de-biased backtests. — [arXiv 2309.17322](https://arxiv.org/html/2309.17322v1)
- **Chronologically consistent LLMs (He, Lv, Manela, Wu; WashU; arXiv 2502.21206).** ChronoBERT and ChronoGPT are trained only on text available up to each cutoff. In a news-to-next-day-return task, their Sharpe is comparable to state-of-the-art models, and the v3 paper concludes that lookahead bias is "modest" in that application. — [arXiv 2502.21206](https://arxiv.org/pdf/2502.21206)
- Other point-in-time and debiasing approaches, all preprints and seen only through the abstract or search summary:
  - DatedGPT: one model per year, 2013–2024. — [search result](https://arxiv.org/pdf/2512.23847)
  - Look-Ahead-Bench: a benchmark of point-in-time LLMs. — [arXiv 2601.13770](https://arxiv.org/pdf/2601.13770)
  - A regression test for lookahead bias. — [arXiv 2512.23847](https://arxiv.org/pdf/2512.23847)
  - Inference-time logit adjustment. — [arXiv 2512.06607](https://www.arxiv.org/pdf/2512.06607)
  - MemGuard-Alpha: membership-inference filtering. It reports that in-sample accuracy rises with contamination while OOS accuracy falls. — [arXiv 2603.26797](https://arxiv.org/pdf/2603.26797.pdf)
- **"Profit Mirage" (Li et al., arXiv 2510.07920, preprint).** States that "dazzling back-tested returns evaporate once the model's knowledge window ends." Introduces FinLake-Bench and FactFin (counterfactual perturbation). The abstract gives no numbers. — [arXiv 2510.07920](https://arxiv.org/abs/2510.07920)
- **CryptoTrade's leakage control was incomplete.** It chose test periods after September 2021 (GPT-3.5's cutoff), but the headline results use GPT-4 and GPT-4o, whose cutoffs are later. The test windows ran from Apr to Dec 2023. — [arXiv 2407.09546](https://arxiv.org/html/2407.09546v1)

### Inferences
- For a crypto bot, any LLM backtest on BTC/ETH data from before the model's cutoff should be treated as contaminated by default. GPT-4o-class models memorize the levels of large, famous assets best, and BTC/ETH are exactly such assets.
- The only clean evidence is a forward or paper-trading test after the cutoff, or a point-in-time model.

### Gaps
- No crypto-specific memorization study was found (for example, whether GPT-4o recalls BTC daily closes). It is likely but unmeasured in these sources.

## Q3. Where do LLMs add verified value, and where don't they?

### Takeaway
The strongest peer-level evidence of value is as an **upstream text and feature extractor**: news sentiment, and possibly factor or code generation. The weakest is as an end-to-end numeric decision-maker, where LLMs are poorly calibrated, regime-naive, costly, and hard to reproduce.

### Cited Findings
- **News signal extraction:** Lopez-Lira and Tang ("Can ChatGPT Forecast Stock Price Movements?") found that GPT-4 headline scores predict next-day drift, more strongly for small stocks and after negative news. The October 2025 version (v6) adds that **strategy returns decline as LLM adoption rises**, meaning the edge is being arbitraged away. — [arXiv 2304.07619v6](https://arxiv.org/html/2304.07619v6)
- **Alpha and factor mining:** AlphaAgent (arXiv 2502.16789, preprint) tested on CSI 500 and S&P 500 from 2021 to 2024. After costs it reports 11.0% annual excess return (IR 1.5) on CSI 500 and 8.74% (IR 1.05) on S&P 500. It uses originality and complexity regularization against alpha decay. These are self-reported and not independently replicated. Alpha-GPT's OOS numbers were not found. — [arXiv 2502.16789](https://arxiv.org/pdf/2502.16789)
- **Numeric and decision weaknesses:** LLM confidence is linguistic and overconfident (measured by ECE). LLMs handle risk limits poorly ("narrative vs numerical execution"), and show "parametric prior lock-in" (a bias toward mega-cap tech). The recommended design is LLM as extractor, with separate quantitative modules for signals, calibration, risk and execution. — [Alpha Illusion, arXiv 2605.16895](https://www.alphaxiv.org/abs/2605.16895)
- The nof1 founder said LLMs "handle numerical time-series data poorly," and that this was deliberately the models' entire context in Season 1. — [ForkLog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/)
- **Cost:** FINSABER notes that large-scale LLM backtesting is expensive, and that FinMem's commission ratio was 5 to 9 times FinAgent's (overtrading). — [arXiv 2505.07078v5](https://arxiv.org/html/2505.07078v5)
- StockBench: "excelling at static financial knowledge tasks does not necessarily translate into successful trading," and reasoning models did not beat instruct models consistently. — [arXiv 2510.02209](https://arxiv.org/html/2510.02209v1)

### Inferences
- For this project, the defensible LLM roles are news and sentiment feature extraction (with anonymization and post-cutoff validation), research and code assistance, and explanation and reporting. Final position sizing and decisions should stay with the verified quantitative model.

### Gaps
- No rigorous study was found that quantifies LLM nondeterminism (run-to-run variance in returns) or the latency impact in trading. These were raised qualitatively only.

## Q4. Crypto-specific LLM trading results and live competitions

### Takeaway
CryptoTrade (EMNLP 2024) did **not** beat buy-and-hold in bull markets: it lagged badly on SOL and BTC. Its main benefit was smaller losses in bear windows. The only live crypto LLM competition (nof1 Alpha Arena Season 1, Oct–Nov 2025) was a 2.5-week, $10k-per-model experiment. Four of six frontier LLMs lost 42% to 59%, and nof1 itself called it non-definitive.

### Cited Findings
**CryptoTrade (Li, Luo, Wang, Chen, Liu, He; National University of Singapore; EMNLP 2024 main, pp. 1094–1106).** — [ACL Anthology](https://aclanthology.org/2024.emnlp-main.63/); [arXiv 2407.09546](https://arxiv.org/html/2407.09546v1)
- Data: daily, on-chain plus news plus technicals. Test windows (2023): bear Apr 12 – Jun 16, sideways about Jun–Aug, bull Oct 1 – Dec 1. The fee is "proportional to traded value," with no rate given.

Bull-market returns:

| Asset | Buy-and-hold | CryptoTrade (GPT-4o) | CryptoTrade (GPT-4) | MACD |
|---|---|---|---|---|
| BTC | 39.66% | 28.47% | 26.35% | 13.57% |
| ETH | 22.59% | 25.47% | 25.72% | — |
| SOL | 176.72% | 115.18% | — | 23.25% |

Bear-market returns:

| Asset | Buy-and-hold | CryptoTrade (GPT-4o) |
|---|---|---|
| BTC | -15.61% | -13.71% |
| ETH | -12.24% | -15.35% |
| SOL | -36.08% | -16.32% |

- The abstract itself admits CryptoTrade beat time-series baselines **but not traditional trading signals**.
- Each window is only about 2 months. There are no multi-seed confidence intervals in the tables seen.

**nof1 Alpha Arena Season 1 (live crypto).** Oct 17/18 – Nov 3, 2025 (one source says Nov 5). Six LLMs, $10,000 each, trading crypto perpetuals on Hyperliquid with no human intervention. — [Decrypt](https://decrypt.co/345006/ai-crypto-trading-showdown-deepseek-grok-winning-gemini-implodes); [ForkLog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/)

Final balances (ForkLog; returns computed from the $10k start):

| Rank | Model | Final balance | Return |
|---|---|---|---|
| 1 | Qwen3-Max | $12,231 | +22.3% |
| 2 | DeepSeek | $10,489 | +4.9% |
| 3 | Claude Sonnet 4.5 | $5,799 | -42.0% |
| 4 | Gemini 2.5 Pro | $5,445 | -45.6% |
| 5 | Grok 4 | $4,208 | -57.9% |
| 6 | GPT-5 | $4,126 | -58.7% |

- Other outlets report slightly different figures: GPT-5 at about -62.7%, Gemini at -56.7%, Grok at -45.3%. **The sources conflict.** — [search summary incl. Yahoo/Decrypt](https://finance.yahoo.com/news/ai-crypto-trading-showdown-deepseek-202512124.html)
- DeepSeek led at over $13k mid-contest, then gave back most of the gain in a downturn. — [ForkLog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/)
- nof1 called the season exploratory, citing its short duration, modest capital and lack of statistical controls. — [aiworld.eu / search summary](https://aiworld.eu/story/ai-agents-against-the-market)

**nof1 Season 1.5 (US stocks, not crypto).** Two weeks ending Dec 3, 2025, with 32 instances and $320k deployed in total. The "mystery model," later revealed as Grok 4.20, won with an average gain of about 12% (other reports say 10% to 12%) and was profitable in all 4 competitions. GPT-5.1 placed second and Gemini 3 third. — [ForkLog](https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/); [Yahoo/Benzinga](https://finance.yahoo.com/news/elon-musks-grok-4-20-123855766.html). The organizers say trades are on-chain or verifiable; this was not independently verified here.

**Fact-subjectivity aware reasoning (arXiv 2410.12464, preprint).** A crypto LLM trading follow-up that uses CryptoTrade's tables as the comparison. Its numbers were not extracted. — [arXiv 2410.12464](https://arxiv.org/html/2410.12464v3)

### Inferences
- Season 1's dispersion of +22% to -59% across models, on the same market over the same 2.5 weeks, is consistent with leverage and noise rather than skill. With six models and one short window, no ranking is statistically meaningful.
- No crypto LLM system was found with a multi-year, post-cutoff, cost-inclusive result that beats buy-and-hold.

### Gaps
- nof1's own site and blog could not be fetched (HTTP 404). Leverage limits, asset list, trade counts and fees for Season 1 are not confirmed from the primary source.
- Any Alpha Arena Season 2 (2026) results were not found.

## Q5. Retrieval-augmented and episodic "memory" designs: does memory improve OOS results?

### Takeaway
Memory and reflection modules show gains **only in in-sample, single-window ablations by the original authors**. The one large independent long-run test of a memory agent (FinMem in FINSABER) found negative alpha and worse regime behaviour than buy-and-hold. No evidence was found that memory improves true OOS performance.

### Cited Findings
- **FinMem (Stevens Institute of Technology).** Profiling, a layered memory with an access counter that promotes events to deeper layers, and a decision module. It claims better cumulative return and Sharpe than DRL agents using less training data. — [arXiv 2311.13743](https://arxiv.org/pdf/2311.13743); [AAAI-SS](https://ojs.aaai.org/index.php/AAAI-SS/article/view/31290)
- The independent re-test of FinMem (2004–2024, more than 60 symbols including delisted stocks) found negative alpha in all scenarios and a Sharpe of -0.97 in bear years. — [FINSABER, arXiv 2505.07078v5](https://arxiv.org/html/2505.07078v5)
- **CryptoTrade reflection ablation** (ETH bull window only): the full prompt returned 28.47% (Sharpe 0.23); without reflection, 17.14% (0.06); the base prompt only, 8.40%. All variants trail or barely match buy-and-hold at 22.59% on that window, and it is one asset in one regime. — [arXiv 2407.09546](https://arxiv.org/html/2407.09546v1)
- A 2026 preprint, "From Knowing to Doing: A Memory-Controlled Benchmark for LLM Trading Agents" (arXiv 2605.28359), targets this question directly. Its content was not extracted. — [arXiv 2605.28359](https://arxiv.org/pdf/2605.28359)

### Inferences
- Episodic memory of past trades in a pre-cutoff backtest can amplify contamination, because retrieved "lessons" may encode known outcomes. Memory designs should be validated only on post-cutoff forward data.

### Gaps
- FinCon's (NeurIPS 2024) episodic and conceptual memory ablation and test window were not retrieved.
- No independent replication was found showing that memory improves OOS results.
