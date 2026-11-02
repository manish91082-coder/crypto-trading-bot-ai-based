# पाँच Brains रखें, फ़ैसला सबूत को सौंपें

**मुख्य निष्कर्ष:** आपका प्रस्ताव **ढाँचे में ज़्यादातर सही है, पर उसका "दिमाग" ग़लत जगह पर है।** आठ timeframes को आठ bots के बजाय एक साझा system मानना, बंद candle पर ही फ़ैसला लेना, हर फ़ैसले का log रखना और नए model को frozen benchmark से हराने की शर्त रखना, ये सब बाहरी साहित्य और हमारे अपने verified नतीजों से मेल खाते हैं। तीन हिस्से सबसे जोखिम भरे हैं। पहला, **Master Brain जो हर regime में "सबसे अच्छी" strategy चुनता है।** Regime-switching का out-of-sample सबूत सबसे कमज़ोर है। Equities में plain HMM switching ने costs के बाद S&P पर buy-and-hold से भी कम CAGR दिया (8.5% बनाम 10.2%), और estimated weights वाली selection आम तौर पर सीधे equal-weight मिश्रण से हारती है। दूसरा, **5m/15m को अलग decision engine बनाना।** हमारी Swing Anatomy में 5m/15m swing-following का औसत खर्च से पहले ही लगभग शून्य है (+0.02%/+0.05% प्रति trade), और 15m/5m features ने AUC में सिर्फ़ +0.0008 जोड़ा। इसलिए छोटे timeframes का काम सिर्फ़ execution timing होना चाहिए। तीसरा, **बिना trial registry के Strategy Discovery।** हर नई खोज multiple-testing का बोझ बढ़ाती है, और crypto technical rules data-snooping correction के बाद बार-बार ढहे हैं। प्रस्ताव में कुछ बुनियादी चीज़ें छूट भी गई हैं: `available_at` वाला point-in-time feature store, cost/funding/liquidity brain, portfolio-स्तर का long-short risk, execution brain, champion–challenger shadow और kill-switch। दो विरोधाभास user के निर्णय के बिना आगे नहीं बढ़ सकते। प्रस्ताव कहता है "SL/TP auto नहीं लगेगा", जबकि चल रहा 1D system user-approved F7 नियम (exchange stop entry ×1.5, 30-दिन cooldown) पर चलता है। और प्रस्ताव में capital "₹10,000" लिखा है, जबकि project का capital $10,000 है। सुझाया गया अगला कदम कोई नया brain नहीं है। अगला कदम है **Swing Anatomy Phase 2**: 4h/1h पर top-down features वाला swing AI, pre-registered protocol, measured costs और independent verifier के साथ। चल रहा 1D cloud system इस पूरे काम में अछूता रहेगा।

> **अस्वीकरण:** यह शोध-रिपोर्ट है, वित्तीय या निवेश सलाह नहीं। लेखक licensed advisor नहीं है। इस रिपोर्ट में कोई नया backtest नहीं चलाया गया। "हमारे" आँकड़े project की verified reports से हैं (हर जगह file का नाम दिया गया है), और बाहरी आँकड़े नीचे दिए स्रोतों से। ज़्यादातर बाहरी स्रोत abstract, repository page या search snippet के स्तर पर पढ़े गए। **⚠** चिह्न का मतलब है: preprint, सिर्फ़ abstract/snippet, secondary summary, या विवादित दावा। "प्रस्ताव" और "gate" वाली संख्याएँ हमारे सुझाव हैं, साहित्य से निकली संख्याएँ नहीं।

---

## प्रस्ताव का सार: छह हिस्से, एक साझा system

User के प्रस्ताव को बिना बदले इस तरह रखा जा सकता है। Binance पर spot और USDT-M perps में long और short, दोनों दिशाओं में trading होगी, 4H और उससे छोटे timeframes (5m, 15m, 30m, 1h, 4h) पर, और 1D/1W/1M सिर्फ़ संदर्भ के लिए। इसके लिए **पाँच brains** होंगे। (A) **Market Intelligence Brain** regime पहचानेगा: bullish, bearish, sideways, breakout, pullback, high/low volatility, अचानक बदलाव, साथ में trend strength, momentum, volume और structure। (B) **Market Map & Zone Brain** support/resistance zones, swing highs/lows, breakout levels, retest areas, liquidity zones और पुराने invalidation levels रखेगा, और हर zone के साथ price, समय, timeframe, strength और freshness दर्ज होंगे। (C) **Indicator & Volume Brain** EMA/SMA, RSI, MACD, ATR, Bollinger, ADX, Donchian, volume expansion, relative volume और candle patterns देखेगा, और redundant indicators से बचेगा। (D) **Strategy Knowledge Brain** स्थापित और शोधित strategies की library होगी, जिसमें हर strategy के उपयुक्त regime, timeframe, entry/exit नियम, failure conditions और costs के बाद का ऐतिहासिक प्रदर्शन दर्ज होगा। (E) **Master Decision Brain** strategy, timeframe, capital और trade/no-trade चुनेगा।

आठ timeframes (5m से 1M) **एक साझा decision system** होंगे, आठ अलग bots नहीं, और system विरोधाभास पकड़ेगा। प्रस्ताव का उदाहरण: अगर 5m BUY कहे पर 4h/1D की मज़बूत resistance ऊपर हो और volume कमज़ोर हो, तो trade नहीं। हर timeframe का एक **precomputed historical knowledge store** होगा, जिसमें S/R और swing levels, regime periods, हर regime में strategy का प्रदर्शन, entries के बाद MFE/MAE, invalidation और stop-reference levels, volume-price संबंध, false signals और failure conditions, fees के बाद profitability/drawdown/trade frequency, और "किस जानकारी से कौन-सा फ़ैसला हुआ और नतीजा क्या रहा" का log रहेगा। प्रस्ताव में दो नोट हैं। पहला, stop-reference levels सिर्फ़ विश्लेषण के लिए हैं, और SL/TP अपने-आप नहीं लगेंगे क्योंकि user ने पहले ऐसा कहा था। दूसरा, Binance kline archives में सिर्फ़ OHLCV है, इसलिए order-book depth, live spread और liquidation data के लिए अलग स्रोत चाहिए।

Strategy brain के चार हिस्से होंगे: **Library** (trend, momentum, breakout, pullback, mean reversion, volatility setups), **Discovery** (नए feature/rule combinations खोजना और हर असफलता log करना), **Tournament** (fees, slippage, DD, trade count और regimes पर निष्पक्ष साझा परीक्षण), और **Controlled Learning** (नया model तभी आएगा जब वह frozen benchmark और independent test दोनों को हराए)। हर candle close पर फ़ैसले का क्रम होगा: Market → Zone → Volume → Strategy → Multi-timeframe → Risk (capital "₹10,000, USDT में बदलकर", exposure, fees, adverse move) → Master, जिसका आउटपुट BUY/HOLD/SELL/NO TRADE होगा, कारण और confidence के साथ। अधूरी candle या भविष्य की जानकारी इस्तेमाल नहीं होगी। पूरा pipeline होगा: market-understanding AI → strategy-selecting AI → controlled-learning AI → verified backtesting → paper trading।

## Component-दर-component फ़ैसला: ढाँचा सही, तीन हिस्से जोखिम भरे

नीचे की तालिका हर हिस्से पर फ़ैसला देती है। "सही" का मतलब है कि सबूत design का समर्थन करता है। "आंशिक रूप से सही" का मतलब है कि विचार ठीक है पर रूप बदलना होगा। "जोखिम भरा" का मतलब है कि सबूत कमज़ोर या उल्टा है, इसलिए यह हिस्सा सिर्फ़ एक परखी जाने वाली परिकल्पना बन सकता है। जो हिस्से जोखिम भरे हैं, वे अपने मौजूदा रूप में अपनाए जाएँ तो पैसा खो सकते हैं। प्रस्ताव का कोई लिखा हुआ हिस्सा पूरी तरह "ग़लत" नहीं है। "ग़लत" सिर्फ़ एक संभावित व्याख्या पर लागू होता है: अगर "AI" से LLM को numeric trading फ़ैसला देना अभिप्रेत हो (आख़िरी पंक्ति)।

| Component | फ़ैसला | बाहरी सबूत | हमारा आंतरिक सबूत | ज़रूरी बदलाव |
|---|---|---|---|---|
| **(A) Market Intelligence / regime brain** | आंशिक रूप से सही | Regime models बाद में states पहचानते हैं, पर real-time पहचान में ~2 हफ़्ते का lag है, और plain HMM साल में ~8.5 बार switch करके costs में edge खो देता है ([Shu, Yu & Mulvey 2024, J. Asset Mgmt](https://arxiv.org/html/2402.05272v3)) | "Market से कब बाहर रहें" brain असफल (AUC 0.523, CI 0.494 छूती है; `REPORT_1D_STEP17_18_14_OCT_2026.md`) | Regime को **feature** और soft, persistent risk-overlay बनाएँ, hard switch नहीं |
| **(B) Zone / S/R brain** | जोखिम भरा (नियम के रूप में) / आंशिक (feature के रूप में) | FX में S/R का असर round-number order clustering से है ([Osler, NY Fed](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.html)); BTC में round-number clustering है पर उसके बाद कोई return pattern नहीं ([Urquhart 2017](https://ideas.repec.org/a/eee/ecolet/v159y2017icp145-148.html)) | Swings हर TF पर ~5 ATR के self-similar हैं, और confirmed pivot तब तक ~57% हो चुका होता है (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`) | Zones = परखने लायक features; सिर्फ़ **confirmed** pivots, `available_at` = confirmation bar का close |
| **(C) Indicator & Volume brain** | आंशिक रूप से सही | Indicators कुछ ही स्वतंत्र factors में सिमटते हैं ([Neely et al. 2014](https://files.stlouisfed.org/files/htdocs/wp/2010/2010-008.pdf)); candlesticks का सबूत नकारात्मक ([IEEE Big Data 2021](https://ieeexplore.ieee.org/document/9671826)); volume का असर return × volume interaction में है, अक्सर reversal की दिशा में ([Bianchi et al. 2022, JBF](https://econpapers.repec.org/RePEc:eee:jbfina:v:142:y:2022:i:c:s0378426622001418)) | Volume spike सबसे लगातार factor (rank corr +0.03 से +0.12); पर कोई भी factor 0.17 से ऊपर नहीं (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`) | 2–4 signal families तक घटाएँ; candlestick नियम हटाएँ (सिर्फ़ OHLC shape features रहें) |
| **(D) Strategy Library** | सही (benchmark के रूप में) | Costs के बाद सबसे बार-बार positive सबूत time-series trend/breakout का है ([Gerritsen et al. 2020](https://research-portal.uu.nl/en/publications/the-profitability-of-technical-trading-rules-in-the-bitcoin-marke/)); पर edge 2020 के बाद घटा ([Li et al. 2023](https://articlegateway.com/index.php/JAF/article/view/6453)) | 1D/4h swing-following का औसत positive, 1h से नीचे ≈0 (उसी report में) | हर strategy का "after-cost" प्रदर्शन हमारे measured costs से भरें |
| **(D) Strategy Discovery** | जोखिम भरा | ~8,000 rules में से best DJIA rule अगले 10 साल में OOS edge खो बैठा ([Sullivan, Timmermann & White 1999](https://doi.org/10.1111/0022-1082.00163)); crypto GP का कोई OOS survival rate नहीं मिला | 1D काम में PBO 65% आया था (`RESEARCH_4H_TRADING_LONG_SHORT_17_OCT_2026.md` संदर्भ) | Trial registry अनिवार्य; DSR/PBO पूरे trial count पर; SPA/Reality Check |
| **(D) Strategy Tournament** | आंशिक रूप से सही | "Recent winner चुनना" estimated weights का सबसे चरम रूप है; equal-weight अक्सर जीतता है ([DeMiguel et al. 2009](https://doi.org/10.1093/rfs/hhm075); [Claeskens et al. 2016](https://research.vu.nl/en/publications/the-forecast-combination-puzzle-a-simple-theoretical-explanation-2/)) | D1/H4/H1 brains के returns 0.89–0.95 correlated (`REPORT_COMBINED_STEP27_15_OCT_2026.md`) | Tournament का विजेता equal-weight + vol-target मिश्रण को हराए, तभी अपनाएँ |
| **(D) Controlled Learning** | सही | Validation, monitoring, canary और rollback का मानक ([Breck et al. 2017, ML Test Score](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/)); online learning के periodic retraining से बेहतर होने का सबूत नहीं ⚠ ([Dasari 2026, preprint](https://arxiv.org/abs/2608.19488)) | Shuffled control और claims.json verifier पहले से project का नियम | Scheduled walk-forward retrain + shadow challenger; online learning नहीं |
| **(E) Master Decision Brain** | जोखिम भरा | Hard regime-to-strategy switching का सबूत सबसे कमज़ोर; combining selecting से बेहतर ([Rapach, Strauss & Zhou 2010](https://ideas.repec.org/a/oup/rfinst/v23y2010i2p821-862.html)) | Veto brain सिद्ध (0.529) पर redundant; ranking brains ही असली skill (D1 0.559, 4H R6 0.568, 1h R24 0.565; `AUDIT_FULL_BRAINS_AND_CODE_16_OCT_2026.md`) | Equal-weight ensemble + vol targeting null benchmark; master = ±20% tilt, 1/0 switch नहीं |
| **8-TF साझा system** | सही (विचार) / आंशिक (TF सूची) | MTF confluence का कोई peer-reviewed OOS सबूत नहीं; HTF bar की leakage आम ग़लती है ([TradingView Pine FAQ](https://tradingview.com/pine-script-docs/faq/other-data-and-timeframes)) | Top-down असली: अगला बड़ा TF साथ हो तो swing +0.47 से +0.76 ATR आगे; 1W का साफ़ असर नहीं, 1M का उल्टा | सिर्फ़ अगला बड़ा TF और 1D context रखें; 1W/1M को feature मानें, नियम नहीं; 5m/15m सिर्फ़ execution |
| **Precomputed knowledge store** | आंशिक रूप से सही | PIT joins (`available_at` पर) leakage रोकते हैं ([Feast docs](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)); MFE/MAE भविष्य के bars से बनते हैं | Swing confirmation lag मापा जा चुका है (~57%) | Store = bitemporal feature store; MFE/MAE सिर्फ़ label/outcome |
| **Decision flow (हर candle close)** | आंशिक रूप से सही | Abstention trades पर accuracy बढ़ाता है, पर net return पर सबूत मिश्रित ([Chalkidis & Savani 2021, ICAIF](https://ar5iv.labs.arxiv.org/html/2110.14914)) | AI exit brains असफल (0.505–0.526; `REPORT_EXIT_STEP26_15_OCT_2026.md`, `REPORT_1D_STEP10_AI_13_OCT_2026.md`) | Sequential veto chain की जगह एक model + अलग risk/cost/execution layers; confidence calibrated हो |
| **Pipeline** | आंशिक रूप से सही | Validation पहले, उपयोग बाद में ([Fed SR 26-2, 2026](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm)) | Pre-registration + SHA lock + verifier हमारा नियम | Protocol lock, leakage replay test, verifier, demo executor और user-निर्णय के gates जोड़ें |
| **LLM को numeric फ़ैसला देना** (अगर "AI" से LLM अभिप्रेत हो) | ग़लत | LLMs pre-cutoff market data याद रखते हैं ([Lopez-Lira et al. 2025 ⚠ preprint](https://arxiv.org/html/2504.14765v2)); लंबे OOS में LLM agents buy-and-hold से हारे ([FINSABER, KDD 2026](https://arxiv.org/html/2505.07078v5)) | — | LLM सिर्फ़ research, code और व्याख्या के लिए |

## Master Brain को चुनना नहीं, मिलाना सीखना होगा

**Regime पहचान का असली OOS फ़ायदा drawdown घटाना है, return बढ़ाना नहीं।** सबसे साफ़ OOS सबूत equities से है। Shu, Yu और Mulvey ने 1990–2023 के S&P 500, DAX और Nikkei पर 10 bps one-way cost और 1-दिन की execution delay के साथ परखा। S&P पर Sharpe buy-and-hold, HMM और Jump Model के लिए क्रमशः 0.48, 0.54 और 0.68 रहा, max drawdown −55.2%, −28.9% और −26.6% रहा, पर **HMM का CAGR 8.5% रहा, जो buy-and-hold के 10.2% से कम है** ([arXiv 2402.05272](https://arxiv.org/html/2402.05272v3))। अंतर persistence से आया। बिना smoothing का HMM साल में ~8.5 बार regime बदलता है, जबकि jump penalty वाला model साल में एक बार से कम। S&P पर HMM का turnover 141% था, JM का 44%। COVID crash में signals शुरुआत और वापसी दोनों पर ~आधा महीना देर से आए ([उसी paper में](https://arxiv.org/html/2402.05272v3))। Nystrup के DTU शोध के अनुसार regime probability के हिसाब से धीरे-धीरे exposure बदलना 100%/0% switching जितना ही अच्छा OOS रहा, और उसका turnover कम था ⚠ ([Nystrup thesis, search summary](https://www2.imm.dtu.dk/pubdb/pubs/6808-full.html))। Crypto में HMM papers मुख्यतः descriptive या density-forecast हैं। Costs के साथ OOS trading backtest वाला कोई crypto regime-switching अध्ययन नहीं मिला ([Figà-Talamanca et al. 2021 ⚠ snippet](https://econpapers.repec.org/RePEc:eee:ecofin:v:57:y:2021:i:c:s1062940821000577))। हमारा अपना "market से कब बाहर रहें" brain भी इसी pattern में बैठता है: AUC 0.523, और CI 0.494 को छूती है, यानी skill सिद्ध नहीं (`REPORT_1D_STEP17_18_14_OCT_2026.md`)। इसलिए Brain (A) को regime label देने वाली मशीन नहीं, बल्कि **regime features** (vol level, trend strength, BTC दिशा) देने वाला हिस्सा होना चाहिए, और उसका सीधा उपयोग सिर्फ़ एक धीमे, persistent risk-off overlay में हो।

**"हर regime में best strategy चुनो" forecast-combination puzzle का सबसे बुरा रूप है।** Claeskens, Magnus, Vasnev और Wang ने दिखाया कि जब combination weights estimate किए जाते हैं, तो "optimal" मिश्रण के equal-weight से बेहतर होने की कोई गारंटी नहीं, और वह मूल forecasts से भी बुरा हो सकता है ([IJF 2016, VU record](https://research.vu.nl/en/publications/the-forecast-combination-puzzle-a-simple-theoretical-explanation-2/))। DeMiguel, Garlappi और Uppal के परीक्षणों में 14 optimizing models में से कोई भी 1/N को OOS लगातार नहीं हरा पाया ⚠ (आँकड़े prior knowledge से, दोबारा fetch नहीं; [RFS 2009](https://doi.org/10.1093/rfs/hhm075))। Rapach, Strauss और Zhou ने पाया कि कई कमज़ोर predictors का मिश्रण किसी एक चुने हुए predictor से OOS बेहतर और ज़्यादा स्थिर है ([RFS 2010](https://ideas.repec.org/a/oup/rfinst/v23y2010i2p821-862.html))। "पिछले N महीनों का विजेता चुनो" में weights 1 और 0 होते हैं, यानी estimation error का सबसे बड़ा रूप। Elliott का तर्क है कि puzzle तभी पूरा लागू होता है जब optimal weights का फ़ायदा शुरू से छोटा हो ([UCSD](https://econweb.ucsd.edu/~gelliott/Combination.pdf))। Crypto में ठीक यही स्थिति है, क्योंकि हमारे brains की skill पतली है (AUC 0.53–0.57) और D1/H4/H1 brains के returns आपस में 0.89–0.95 correlated हैं (`REPORT_COMBINED_STEP27_15_OCT_2026.md`)। जब सारे candidates लगभग एक ही दाँव हों, तो उनके बीच "चुनने" से सिर्फ़ noise चुना जाता है।

**इसलिए Master Brain का null benchmark तय है: सभी candidate strategies का equal-weight मिश्रण, volatility targeting के साथ।** Crypto के लिए सबूत का क्रम यह है। सबसे ऊपर diversified time-series trend, vol targeting के साथ। उसके बाद equal-weight ensembles। फिर soft, persistent regime overlays, जो मुख्यतः drawdown घटाते हैं। सबसे नीचे hard regime switching। Vol scaling crypto TSMOM में सबसे समर्थित सरल औज़ार है ⚠ ([Han, Kang & Ryu, AUT WP](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf); [Man Group, practitioner](https://www.man.com/insights/in-crypto-we-trend)), पर equities में उसका OOS फ़ायदा विवादित है। Cederburg et al. के 103 strategies में vol-managed versions OOS में व्यवस्थित रूप से बेहतर नहीं थे ⚠ ([Lehigh PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf))। Master Brain का बचाव लायक रूप है **equal weights के आसपास ±20% जैसे regime-conditional tilts (shrinkage)**। इसे तभी अपनाया जाए जब यह pre-registered OOS test में, costs के बाद और DSR correction के बाद, equal-weight + vol-target को हराए। Confidence पर sizing के लिए probabilities पहले held-out data पर calibrate हों और ¼–½ Kelly पर capped हों। Full Kelly के drawdown बहुत बड़े होते हैं ([MacLean, Thorp & Ziemba 2010](https://doi.org/10.1080/14697688.2010.506108))। यह estimation-error के तर्क से निकला design नियम है, crypto में साबित return-enhancer नहीं।

**"No trade" सही विचार है, पर उसकी कसौटी accuracy नहीं, net edge होनी चाहिए।** Chalkidis और Savani ने 5 metal futures के 30-मिनट bars पर selective classification परखी। Accuracy 51–54% से बढ़कर 52–57% हुई, coverage 37–63% पर। Selective logistic regression सभी 4 feature sets पर positive Sharpe (0.02–0.28) तक पहुँची, पर **LSTMs हर configuration में नकारात्मक रहे**, और ternary models की accuracy ज़्यादा होने पर भी backtest बुरा रहा ([ICAIF 2021](https://ar5iv.labs.arxiv.org/html/2110.14914))। सबक यह है कि abstention का फ़ायदा मुख्यतः cost से बचने में है। इसलिए threshold "expected edge − cost" पर validation data से तय हो, और threshold का हर चुनाव trial registry में गिना जाए।

## Zones, indicators और candles: कम signals, ज़्यादा परीक्षण

**Crypto technical analysis मुख्यतः trend का proxy है, और उसका edge घटता गया है।** 2019 तक के अध्ययनों में MA, variable-length MA और trading-range breakout (Donchian-जैसे) नियम costs के बाद लाभदायक दिखे। Hudson और Urquhart ने ~15,000 rules परखे और multiple-hypothesis correction के बाद भी profitability पाई, पर **Bitcoin के OOS period में कोई predictability नहीं रही** ⚠ (abstract/working paper; [Annals of OR 2021, IDEAS](https://ideas.repec.org/a/spr/annopr/v297y2021i1d10.1007_s10479-019-03357-1.html))। Gerritsen et al. में daily BTC पर trading range breakout सबसे मज़बूत नियम था, ख़ासकर मज़बूत trend वाले बाज़ार में ([FRL 2020, Utrecht](https://research-portal.uu.nl/en/publications/the-profitability-of-technical-trading-rules-in-the-bitcoin-marke/))। 2022–2023 के BTC/ETH USDT daily और hourly data पर 200+ strategies में data-snooping adjustment के बाद **कोई लाभदायक strategy नहीं मिली** ⚠ (छोटी अवधि, कम-स्तरीय journal; [J. Accounting & Finance 2023](https://articlegateway.com/index.php/JAF/article/view/6453))। Reality Check के साथ crypto rules से excess returns "rarely" मिले और वे मुख्यतः market beta पर टिके थे ⚠ ([Anghel, FRL 2021](https://ideas.repec.org/a/eee/finlet/v39y2021ics1544612320304414.html))। 5-मिनट BTC पर नियम 2013–2017 में लाभदायक रहे, पर "profitability is highly unstable and declines over time" ⚠ (MSc thesis; [Bakker 2017](https://thesis.eur.nl/pub/41546/Bakker.pdf))। इसका मतलब है कि Strategy Library में pre-2019 के नतीजों को आज का edge न माना जाए।

**Support/resistance के लिए crypto में सबूत लगभग नहीं है, इसलिए Zone Brain नियम नहीं, feature-स्रोत होना चाहिए।** S/R का सबसे अच्छा सबूत FX का है। Osler ने छह firms के published levels में intraday trend रुकने की भविष्यवाणी करने की शक्ति पाई, जो पाँच कारोबारी दिन तक टिकी ([NY Fed EPR 2000](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.html))। इसका तंत्र round numbers पर stop-loss और take-profit orders का जमाव है: take-profit trends पलटते हैं, stops cascades पैदा करते हैं ([NY Fed Staff Report 125](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf))। Bitcoin में 10% से ज़्यादा prices "00" पर ख़त्म होते हैं, पर **round numbers के बाद कोई significant return pattern नहीं है** ([Urquhart 2017, Economics Letters](https://ideas.repec.org/a/eee/ecolet/v159y2017icp145-148.html))। Crypto में swing high/low का जो सबूत है, वह breakout की दिशा (trend) के पक्ष में है, "support से उछाल" (mean reversion) के पक्ष में नहीं ([Gerritsen et al.](https://research-portal.uu.nl/en/publications/the-profitability-of-technical-trading-rules-in-the-bitcoin-marke/))। Retests या order-book/liquidation आधारित "liquidity zones" पर costs के बाद OOS परीक्षण वाला कोई crypto अध्ययन नहीं मिला। इसलिए zones को इस तरह रखें: distance-to-nearest-confirmed-swing (ATR में), round-number distance, zone age, और zone को कितनी बार छुआ गया। ये features model में जाएँ, और उनका मूल्य shuffled control के सामने साबित हो। प्रस्ताव का उदाहरण ("5m BUY, ऊपर 4h/1D resistance, कमज़ोर volume → no trade") एक अच्छी परिकल्पना है, पर अभी सिद्ध नियम नहीं है।

**Zone Brain में सबसे बड़ा तकनीकी ख़तरा repainting है।** ZigZag का नया leg हर नए extreme तक खिंचता रहता है और threshold जितना पलटने पर ही जमता है, इसलिए pivots देर से पक्के होते हैं, और backtest में "ZigZag low पर खरीदना" भविष्य देखना है। एक single-author practitioner backtest में ~81% नए pivots बाद में repaint हो गए ⚠ ([abctradinggroup, practitioner](https://www.abctradinggroup.com/indicator-repainting))। हमारी Swing Anatomy इसे मापती है: **swing असल समय में पक्का होने तक उसका ~57% हो चुका होता है**, और उसके बाद औसतन ~2 ATR बचता है, जिसमें 75–78% बार कम से कम 1 ATR और होता है (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। इसका मतलब है कि store में हर pivot के दो समय हों: `pivot_bar_time` (payload) और `available_at` = confirmation bar का close। Join सिर्फ़ दूसरे पर हो।

**Indicators की सूची लंबी है, पर उनमें स्वतंत्र जानकारी 2–4 परिवारों की ही है।** EMA/SMA crossovers, MACD (EMAs का अंतर), price/MA ratio, Donchian और ADX सब एक ही price path से trend को अलग-अलग lookbacks पर मापते हैं। RSI और Bollinger %B छोटे horizon की momentum या overextension के normalized रूप हैं। ATR volatility है। Neely, Rapach, Tu और Zhou ने 14 technical predictors को कुछ principal components में समेटा, जो OOS में उपयोगी थे ([St. Louis Fed WP](https://files.stlouisfed.org/files/htdocs/wp/2010/2010-008.pdf))। Huang et al. के 124 BTC indicators से सिर्फ़ daily returns की संकरी रेंज में predictability मिली ⚠ (abstract; [JFDS 2019, Penn State](https://pure.psu.edu/en/publications/predicting-bitcoin-returns-using-high-dimensional-technical-indic/))। (यह कि 10+ indicators असल में 2–3 factors हैं, हमारा अनुमान है, sourced finding नहीं।) हमारे अपने नतीजे भी यही कहते हैं: momentum factors (SMA50/200 से दूरी, RSI, range में जगह) का rank correlation 0.02–0.13 है, और कोई factor 0.17 से ऊपर नहीं (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। इसलिए Brain (C) को चार परिवारों तक घटाएँ: trend level (कई lookbacks), short-horizon overextension/reversal, volatility (ATR%, ATR ratio), और volume/flow। हर परिवार से 1–3 प्रतिनिधि रखें, और "कितने indicators सहमत हैं" को confluence न मानें।

**Candlestick patterns को signal के रूप में हटाना चाहिए।** 23 बड़े coins पर 68 patterns "of little use" निकले, और कम accuracy वाले patterns ज़्यादा थे ([IEEE Big Data 2021](https://ieeexplore.ieee.org/document/9671826))। US large caps में 28 candlestick signals "for the most part do not work as expected", और एक bullish signal ने भरोसे से **नकारात्मक** return की भविष्यवाणी की ⚠ (secondary summary; [Marshall, Young & Rose 2006 via CXO](https://www.cxoadvisory.com/technical-trading/candlesticks-fiddlesticks/))। 1-मिनट BTC futures के एक positive नतीजे के लेखकों ने ख़ुद price manipulation की संभावना बताई ([Applied Economics Letters 2022](https://ideas.repec.org/a/taf/apeclt/v29y2022i10p947-954.html))। ज़्यादा से ज़्यादा body/wick ratios जैसे raw OHLC shape features model में जा सकते हैं।

**Volume सबसे उपयोगी input है, पर "volume confirms breakout" वाला नियम सबूत से नहीं निकलता।** Bianchi, Babiak और Dickerson के अनुसार crypto में lagged return × volume का interaction returns की भविष्यवाणी करता है, पर लाभदायक strategy volume-conditioned **reversal** है, जो कम activity वाले pairs में केंद्रित है ([JBF 2022](https://econpapers.repec.org/RePEc:eee:jbfina:v:142:y:2022:i:c:s0378426622001418))। Shen, Urquhart और Wang ने BTC में intraday momentum पाया, जो सबसे ज़्यादा volume वाले sessions में सबसे मज़बूत था ([Financial Review 2022](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/))। हमारे data में **swing confirmation के समय volume spike आगे की चाल का सबसे लगातार factor है, दोनों दिशाओं में और 5m से 8h/12h तक** (rank corr +0.03 से +0.12; `REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। ये दोनों बातें टकराती नहीं। Volume की दिशा का असर संदर्भ पर निर्भर है (swing confirmation पर continuation, illiquid pairs में reversal)। इसलिए volume को return और context के साथ interaction feature के रूप में दें, और sign model को सीखने दें। उसे hard-coded "confirm" नियम न बनाएँ।

## Multi-timeframe: top-down असली है, पर छोटे timeframes पर पैसा नहीं

**हमारा सबसे मज़बूत आंतरिक नतीजा top-down के पक्ष में है, और यह बाहरी साहित्य की एक कमी भरता है।** Multi-timeframe confluence (जैसे Elder का Triple Screen) को सीधे validate करने वाला कोई peer-reviewed अध्ययन नहीं मिला। Quantpedia का daily-filter-on-hourly-MACD उदाहरण सिर्फ़ illustrative है ([Quantpedia](https://quantpedia.com/how-to-design-a-simple-multi-timeframe-trend-strategy-on-bitcoin/))। हमारी Swing Anatomy (10 coins, 2017-08 से 2026-09, 12 timeframes) में **जब अगला बड़ा timeframe उसी दिशा में हो, तो छोटे timeframe का swing 0.5–0.8 ATR आगे जाता है**, और हर CI शून्य से दूर है: 15m|1h +0.47 (+0.37 से +0.58), 1h|4h +0.62 (+0.42 से +0.84), 4h|1D +0.70 (+0.25 से +1.14), 8h|1D +0.76 (+0.21 से +1.29)। **1W context का कोई साफ़ असर नहीं मिला, और 1M का असर उल्टा था** (1M नीचे हो तो 4h/8h/1h की बाकी गिरावट 0.3–0.7 ATR कम)। एक बारीकी भी है: औसत बढ़ता है, पर "कम से कम 1 ATR और" वाली संभावना ~76–78% पर लगभग वही रहती है। यानी फ़ायदा बड़ी चालों (tail) से आता है (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। इसका design पर सीधा असर है। आठ timeframes को बराबर वोट देना ग़लत है। सबसे ज़्यादा जानकारी **ठीक अगले बड़े timeframe** में है, 1D उपयोगी context है, और 1W/1M को सिर्फ़ ऐसे features के रूप में रखें जिनका मूल्य model को साबित करना हो, नियम के रूप में नहीं।

**Leakage का नियम सरल है पर सख़्त: सिर्फ़ आख़िरी बंद हुआ बड़ा bar।** TradingView के अनुसार HTF values अक्सर repaint होती हैं क्योंकि एक historical chart bar में HTF के realtime bar का data हो सकता है। उनका non-repainting तरीक़ा HTF expression को एक bar पीछे (`close[1]`) लेना है, और इसकी क़ीमत यह है कि नया HTF मान अगले HTF bar के open पर ही मिलता है ([Pine FAQ](https://tradingview.com/pine-script-docs/faq/other-data-and-timeframes); [Higher-timeframe requests](https://www.tradingview.com/script/W1YpYcOI-Higher-timeframe-requests/))। Binance klines open time से पहचानी जाती हैं ([Binance Spot API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)), इसलिए 1d bar को उसके open time (00:00 UTC) पर join करने से उसी दिन 10:00 UTC के 5m फ़ैसले में अधूरे दिन का close घुस जाता है। सही तरीक़ा: HTF row पर `available_at = open_time + interval (+ ingest latency)` लिखें, और pandas `merge_asof(direction='backward', by='symbol', tolerance=...)` से `available_at` पर join करें ([pandas docs](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html))। अगर "आज का अब तक का high" चाहिए, तो उसे छोटे bars से causal तरीके से बनाएँ और अलग नाम दें (`d1_partial_high`)। Project memory का नियम भी लागू है: `df["asof"]` लिखें, `.asof` नहीं। Binance के 1w और 1M kline boundary conventions (हफ़्ता किस दिन शुरू होता है) इस शोध में verify नहीं हुए, इसलिए उन्हें data audit में जाँचना होगा।

**5m और 15m को अलग decision engine बनाना हमारे अपने सबूत के ख़िलाफ़ है।** Swing confirmation पर entry और उल्टे confirmation पर exit की realizable रणनीति का **औसत प्रति trade, खर्च से पहले, 1D पर +10.95%, 4h पर +1.61%, 1h पर +0.33%, 15m पर +0.05% और 5m पर +0.02% है।** Median trade हर timeframe पर नकारात्मक है (−0.4 से −0.9 ATR), और 55–64% trades हारते हैं (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। ध्यान रहे कि यह भाग उस report में descriptive है, pre-registered नहीं। अब इसकी तुलना आज मापे गए costs से करें: perp taker का break-even ~0.085%, perp maker ~0.04% और spot ~0.17% है (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`)। 5m/15m का +0.02–0.05% gross edge perp maker cost से भी कम है। 15m/5m features ने 1h brain में AUC सिर्फ़ +0.0008 जोड़ा (0.5653 → 0.5661), और portfolio नतीजा बेहतर नहीं हुआ (`REPORT_HF_STEP25_14_OCT_2026.md`)। बाहरी सबूत भी यही कहता है। 183 Binance pairs पर 15-मिनट reversal ~90% pairs में significant था, पर gross edge का शिखर ~1.3 bp था जबकि round trip ~5 bp ⚠ ([Kitron & Wengrowicz 2026, preprint](https://arxiv.org/abs/2608.21888))। Hourly BTC perp पर 10 bp per change के साथ naive sign-trading में XGBoost long-only −64% ARC पर पहुँचा, और cost-aware filter ने trades 10,619 से घटाकर 251 किए तब जाकर लाभ लौटा ⚠ ([Bysik & Ślepaczuk, preprint](https://arxiv.org/abs/2606.00060))। इसलिए **5m/15m का काम execution है**: entry का सही पल, maker order कहाँ रखें, spread/slippage मापना, और stop/TP का intrabar simulation। 30m को अलग layer की ज़रूरत नहीं दिखती, क्योंकि 15m और 1h के बीच उसकी कोई अलग भूमिका सबूत में नहीं मिली।

**Shorts के लिए swing-following का सबूत और भी कमज़ोर है।** उसी तालिका में realizable short पक्ष का औसत लगभग शून्य या नकारात्मक है: 1D −0.95%, 12h −0.24%, 8h −0.11%, 4h +0.02%, 1h −0.04%, 15m −0.04% (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। यानी "गिरावट का swing पक्का हुआ, short करो" अपने-आप पैसा नहीं देता। प्रस्ताव में long और short को सममित माना गया है, जबकि हमारा data इस असममिति को साफ़ दिखाता है। Short leg को अलग से, कड़े filters के साथ साबित करना होगा।

## Knowledge store, discovery और controlled learning: हर trial गिनें

**प्रस्ताव का knowledge store असल में एक point-in-time feature store है, और उसे उसी तरह बनाना होगा।** Feast हर entity row के timestamp से पीछे की ओर देखता है, पर default में सिर्फ़ event timestamp join को सीमित करता है। इसलिए **बाद में backfill या ठीक किए गए मान पुराने training rows में leak हो सकते हैं।** `filter_by_created_timestamp=True` विकल्प हर row को उन्हीं मानों तक सीमित करता है जो उस समय तक बन चुके थे ([Feast docs](https://docs.feast.dev/getting-started/concepts/point-in-time-joins))। Uber के Michelangelo में training और serving के लिए एक ही feature expressions चलती हैं ([Uber Engineering](https://www.uber.com/blog/michelangelo-machine-learning-platform/)), और Google का ML Test Score माँगता है कि training और serving features एक ही मान दें ([Breck et al. 2017](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/))। हमारे लिए इसका रूप यह है: हर row में `event_time` और `available_at` हों, सुधार नई row बने और पुरानी कभी overwrite न हो, feature definitions versioned हों (`name@version` + code hash + data SHA), offline store और live value एक ही function से बनें, और tradable universe भी point-in-time हो। Survivorship का असर बड़ा है। Stöckl के 3,904 coins (2014–2021) में equal-weighted survivorship bias 62.19% सालाना आँका गया ⚠ (search summary; [Univ. St. Gallen](https://alexandria.unisg.ch/handle/20.500.14171/108037))।

**MFE/MAE label हैं, feature नहीं।** MAE और MFE भविष्य के bars से बनते हैं, इसलिए वे decision ledger के outcome fields में जा सकते हैं, model inputs में कभी नहीं। Sweeney की adverse-excursion पद्धति stops को MAE वितरण से तय करने की है ⚠ (practitioner स्रोत; [NexusFi](https://nexusfi.com/wiki/trading-wiki/Maximum-Adverse-Excursion))। पर उसी trades के MAE से stop चुनना in-sample optimization है। OHLC bars पर entry/exit bar का MFE/MAE ambiguous है (high पहले आया या low, पता नहीं), इसलिए excursions 1m या 5m data से बनें, ATR से normalize हों, और funding/fees उनमें शामिल हों। (ये pitfalls हमारा तर्क है, sourced finding नहीं।) हमारे लिए 5m के लिए `data/universe_hf` मुख्य स्रोत है, और archive के raw 1m files (10 coins) CLAUDE.md के अपवाद के तहत verify करने के बाद इस्तेमाल हो सकते हैं, क्योंकि उनके 2025+ 1h/15m timestamps corrupt हैं।

**Strategy Discovery सबसे बड़ा multiple-testing जाल है।** Sullivan, Timmermann और White के अनुसार DJIA पर ~8,000 rules में से सबसे अच्छा 1897–1986 में Reality Check के बाद significant था, पर 1987–1996 में उसका कोई OOS edge नहीं बचा ([JF 1999](https://doi.org/10.1111/0022-1082.00163))। Bajgrowicz और Scaillet के अनुसार निवेशक "never have been able to select ex ante" भविष्य के सबसे अच्छे rules, और कम costs भी in-sample performance को मिटा देते हैं ([JFE 2012](https://ideas.repec.org:443/a/eee/jfinec/v106y2012i3p473-491.html))। Crypto GP studies अक्सर एक market और छोटे sample पर OOS लाभ दिखाते हैं, पर discovered rules का कोई quantified survival rate नहीं मिला। FX के GA rules पर कहा गया कि नज़दीकी OOS में लाभ दिखता है पर दूर के OOS में "it is hard to believe" ([Deng et al. 2012, GP bibliography](https://gpbib.cs.ucl.ac.uk/gp-html/DENG_2012_PCS.html))। Regime brain trials को गुणा करता है: (regime परिभाषाएँ) × (strategies) × (hyperparameters) × (mapping के तरीके)। इसलिए **trial registry** अनिवार्य है, जिसमें हर प्रयोग (असफल भी) trial id, समय, code और data SHA, परिकल्पना, grid का आकार, IS/OOS split, cost model, सभी metrics और निर्णय के साथ दर्ज हो। उसी count पर Deflated Sharpe ([Bailey & López de Prado 2014](https://papers.ssrn.com/abstract=2460551)), PBO/CSCV ([Bailey et al. 2017](https://papers.ssrn.com/abstract=2326253)), और Hansen SPA ([JBES 2005](https://doi.org/10.1198/073500105000000063)) या White Reality Check ([Econometrica 2000](https://doi.org/10.1111/1468-0262.00152)) चलें। नए factor के लिए t > 3.0 की सीमा का तर्क Harvey, Liu और Zhu से है ([RFS 2016](https://doi.org/10.1093/rfs/hhv059))। ऊपर बताया गया 1h R4 मामला (AUC 0.545, पर assumed 0.5% round-trip cost में डूबा; `REPORT_1H_STEP24_14_OCT_2026.md`) इसका ठोस उदाहरण है। आज की measured cost (perp taker ~0.085%) पुरानी assumption से 3–6 गुना कम है (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`), इसलिए R4 को दोबारा परखना जायज़ है। पर यह एक **नया pre-registered trial** होगा जो registry में गिना जाएगा, पुराने नतीजे का "बचाव" नहीं। R4 एक cross-sectional long-short सवाल है, इसलिए दोनों legs की लागत गिननी होगी, और ~+0.3% gross उसके सामने पतला है।

**Controlled Learning का सही रूप scheduled walk-forward retraining है, online learning नहीं।** Gu, Kelly और Xiu ने साल में एक बार, expanding window के साथ refit किया, और हर महीने recursively refit करने से जानबूझकर बचे ([NBER w25398](https://www.nber.org/papers/w25398.pdf))। 3,933 runs वाले एक streaming-ML अध्ययन में abrupt और gradual drift के तहत **periodic retraining ने reactive (drift-triggered) policies को significantly हराया** ⚠ (single-author preprint, finance-विशिष्ट नहीं, और इसका incremental नतीजा immediate labels मानता है जबकि trading labels देर से आते हैं; [Dasari 2026](https://arxiv.org/abs/2608.19488))। Sculley et al. चेतावनी देते हैं कि जो models दुनिया में action लेते हैं, वे अपने ही भविष्य के training data को प्रभावित करते हैं (hidden feedback loops), और "Changing Anything Changes Everything" ([NeurIPS 2015](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf))। Drift detectors (ADWIN, PSI, KS) **alerts** हों, auto-deploy triggers नहीं। PSI की लोकप्रिय 0.1/0.25 सीमाओं का कोई academic आधार नहीं है ([Risk.net](https://www.risk.net/journal-of-risk-model-validation/7725371/statistical-properties-of-the-population-stability-index)), इसलिए thresholds sample-size-aware हों या historical non-drift periods के null वितरण से तय हों। Retrain cadence ML Test Score की "staleness curve" से तय करें: अलग-अलग उम्र के models को एक ही OOS period पर परखें और देखें कि edge कितनी तेज़ी से घटता है ([ML Test Score PDF](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf))। हर retrained model एक **challenger** है, जो shadow में चलकर pre-registered gates पास करे, और promotion/rollback एक registry alias बदलना हो ([MLflow Model Registry](https://mlflow.org/docs/latest/ml/model-registry/); [AWS SageMaker shadow tests](https://docs.aws.amazon.com/sagemaker/latest/dg/shadow-tests.html))।

**SR 11-7 का ज़िक्र अब उसके उत्तराधिकारी के साथ होना चाहिए।** Fed, OCC और FDIC की संशोधित interagency guidance (Fed letter **SR 26-2, 17 अप्रैल 2026**) ने SR 11-7 (2011), OCC Bulletin 2011-12 और संबंधित दस्तावेज़ों को **supersede** कर दिया है ([Federal Reserve SR 26-2](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm); [KPMG alert](https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2026/model-risk-management-revised-interagency-guidance-reg-alert.pdf))। नई guidance risk-based है, मुख्यतः $30bn से बड़े banks के लिए है, enforceable standard नहीं है, और **generative व agentic AI को औपचारिक दायरे से बाहर रखती है**। इसके validation सिद्धांत (conceptual soundness, backtesting जैसा outcomes analysis, ongoing monitoring, और objective experts का "effective challenge") हमारे लिए एक checklist हैं, compliance requirement नहीं। हमारा independent verifier इसी "effective challenge" का रूप है।

## LLM को research सहायक रखें, trading का फ़ैसला नहीं

प्रस्ताव में "AI" शब्द model-प्रकार नहीं बताता। अगर इसका मतलब LLM से BUY/SELL करवाना है, तो सबूत साफ़ तौर पर विरोध में है। **LLMs अपने training cutoff से पहले का market data याद रखते हैं।** GPT-4o ने pre-cutoff S&P 500 का daily level 0.61% त्रुटि और 80.6% directional accuracy से "बताया", पर post-cutoff त्रुटि 16.87% और accuracy 45.7% रही। "सिर्फ़ 2010 से पहले का data इस्तेमाल करो" कहने से कोई फ़र्क नहीं पड़ा ⚠ ([Lopez-Lira, Tang & Zhu, preprint](https://arxiv.org/html/2504.14765v2))। BTC/ETH ठीक वैसे ही बड़े, प्रसिद्ध assets हैं, इसलिए cutoff से पहले के किसी भी LLM crypto backtest को contaminated मानना चाहिए। FinMem और FinAgent के independent, लंबे re-test (2004–2024) में buy-and-hold ने 4 में से 3 stocks पर दोनों agents को हराया, और delisted stocks सहित S&P universes पर FinMem का alpha हर scenario में नकारात्मक रहा ([FINSABER, KDD 2026](https://arxiv.org/html/2505.07078v5))। CryptoTrade (EMNLP 2024) bull market में BTC (28.47% बनाम buy-and-hold 39.66%) और SOL (115.18% बनाम 176.72%) पर पीछे रहा ([arXiv 2407.09546](https://arxiv.org/html/2407.09546v1))। एकमात्र live crypto LLM प्रतियोगिता (nof1 Alpha Arena Season 1, ~2.5 हफ़्ते, $10k प्रति model) में छह में से चार models ने 42–59% खोया, और आयोजकों ने ख़ुद इसे निर्णायक नहीं माना ⚠ (मीडिया स्रोत, आँकड़े आपस में टकराते हैं; [ForkLog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/))। FinMem जैसे memory/reflection modules का फ़ायदा सिर्फ़ मूल लेखकों के in-sample ablations में दिखा। Independent long-run परीक्षण में वह नहीं टिका ([FINSABER](https://arxiv.org/html/2505.07078v5))। LLM की बचाव लायक भूमिकाएँ ये हैं: research और code सहायता, reports और फ़ैसलों की व्याख्या, और (भविष्य में, post-cutoff validation के साथ) news/text से features निकालना। Numeric signal, sizing, risk और execution verified quantitative modules के पास रहें।

## प्रस्ताव में जो छूट गया: costs, portfolio risk और execution

**सबसे बड़ी चूक cost/funding/liquidity brain है।** 4H पर market काफ़ी हिलता है। BTC की median 4H candle (open → close) 0.42% है, ETH की 0.52%, और altcoins की 0.6–0.84%। Perp taker break-even (~0.085%) इसका ~5 गुना छोटा है (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`)। पर यही report कहती है कि असली सवाल दिशा की accuracy है। ~0.5% की चाल पर 50% सही दिशा का मतलब है costs के बाद नुकसान। Fees का एक हिस्सा अभी अनसुलझा है: हमारा demo API taker 0.040% बताता है जबकि Binance FAQ 0.050% ([Binance Futures fee FAQ](https://www.binance.com/en/support/faq/binance-futures-fee-structure-fee-calculations-360033544231))। इसलिए दोनों मानकर हिसाब रखें, और live account की दर उसी account के `commissionRate` से SHA-lock करें। Spread+slippage tier-wise हो। BTC, ETH, BNB, SOL, XRP और DOGE पर यह लगभग शून्य है (0.000–0.012%), जबकि ADA, FET, XLM spot और QNT पर $1,000 के trade पर 0.045–0.06% है, और $10,000 पर perp/spot median 0.027%/0.040% तक बढ़ता है (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`)। Funding हर settlement timestamp की असली दर से लगे। Binance cap/floor छूने वाले contracts को बिना घोषणा hourly funding पर ले जाता है ([Binance Funding FAQ](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)), इसलिए 8h को hard-code करना ग़लत होगा। S7 order-book snapshots इस brain का data-आधार हैं। प्रस्ताव का यह नोट सही है कि kline archives में depth, live spread और liquidation data नहीं है। Binance का per-event liquidation snapshot data बंद हो चुका है ⚠ ([arXiv 2607.27070](https://arxiv.org/pdf/2607.27070))।

**दूसरी चूक portfolio-स्तर का risk है।** प्रस्ताव का Risk brain एक trade को देखता है, portfolio को नहीं। Crash में correlations एक की ओर जाते हैं: BTC–ETH lower tail 2017 से कसता गया है, और covariance पर आधारित diversification crash co-movement को कम आँकता है ⚠ ([arXiv 2606.16840, preprint](https://arxiv.org/pdf/2606.16840))। 10 अक्टूबर 2025 को एक दिन में ~$19B liquidation हुआ, BTC की top-of-book depth 90% से ज़्यादा गिरी, और कुछ hedged shorts ADL से बंद हो गए ([FTI Consulting](https://www.fticonsulting.com/zh-cn/china/insights/articles/crypto-crash-october-2025-leverage-met-liquidity))। ज़रूरी चीज़ें ये हैं: per-coin inverse-volatility sizing, gross exposure caps ऐसे जैसे correlation = 1 हो, net beta की सीमा, graduated drawdown de-risking, और यह शर्त कि नया system 1D LS line से ≤0.70 correlated हो या combined Calmar बढ़ाए। 1D, 4H और 1h brains पहले से 0.89–0.95 correlated हैं (`REPORT_COMBINED_STEP27_15_OCT_2026.md`), इसलिए एक और "कौन coin बेहतर करेगा" brain portfolio में लगभग कुछ नहीं जोड़ेगा।

**तीसरी चूक short-side के ख़ास जोखिम हैं।** Liquidation Mark Price पर trigger होता है, बचा हिस्सा Insurance Fund को जाता है, और fund कम पड़ने पर ADL मुनाफ़े वाली विपरीत positions बंद करता है ([Binance liquidation FAQ](https://www.binance.com/en/support/faq/liquidation-protocols-360033525271))। April 2025 में ALPACA delisting घोषणा के बाद कीमत कई गुना उछली, ~$43M short liquidations हुए, और एक विश्लेषण के अनुसार 1x short सिर्फ़ funding से ≥48% principal खो देता ⚠ (आँकड़े स्रोतों में अलग; [crypto.news](https://crypto.news/alpaca-token-surges-amid-binance-delisting-news/))। इसलिए short universe से delisting-घोषणा वाले coins, बहुत नई listings और कम liquidity वाले coins बाहर रहें, per-coin short notional cap हो, और funding interval बदलते ही exit हो। ये सब pre-registered filters के रूप में परखे जाएँ। Margin collateral सिर्फ़ USDT में रहे।

**चौथी चूक execution brain है।** 2025-12-09 से USDT-M के conditional orders (STOP_MARKET, TAKE_PROFIT_MARKET आदि) सिर्फ़ `POST /fapi/v1/algoOrder` से जाते हैं, और पुराना endpoint error -4120 देता है ([Binance Derivatives Change Log](https://developers.binance.com/docs/derivatives/change-log))। STOP_MARKET का `workingType` default में CONTRACT_PRICE है ([Binance API](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api)), इसलिए हर stop पर `MARK_PRICE` स्पष्ट रूप से लिखना होगा। Maker orders 3 bp/side बचाते हैं, पर Binance BTC perps पर failure-to-fill का संबंध positive future short-term returns से पाया गया, यानी सबसे अच्छे trades ही छूटते हैं ([Quantitative Finance 2025](https://ideas.repec.org/a/taf/quantf/v25y2025i6p919-947.html))। Execution brain के नियम: post-only (GTX) entry, 30–120 सेकंड इंतज़ार और फिर taker fallback; stops और risk exits हमेशा taker; idempotent `clientOrderId`; हर run पर open orders **और** open algo orders से reconciliation; और 5m/15m bars का उपयोग entry timing के लिए। 4H executor 1D system से अलग process, अलग key और अलग sub-account/namespace में चले, क्योंकि one-way mode में एक symbol पर positions आपस में netting करती हैं ⚠ (sub-account नियम verify नहीं हुए)।

**बाकी जोड़ने लायक चीज़ें इंजीनियरिंग की हैं, और हर एक हमारे evidence नियम से जुड़ी है।**

| जोड़ | क्यों | स्रोत/आधार |
|---|---|---|
| Point-in-time feature store (`event_time` + `available_at`) | HTF और pivot leakage रोकना | [Feast](https://docs.feast.dev/getting-started/concepts/point-in-time-joins); [TradingView](https://tradingview.com/pine-script-docs/faq/other-data-and-timeframes) |
| Bar-by-bar replay test + "leak canary" | हर feature को truncated data से दोबारा बनाकर store से मिलाना; जानबूझकर भविष्य का close डालकर साबित करना कि harness leakage पकड़ता है | ML Test Score Monitor 3 ([Breck et al.](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/)); synthesis |
| Hash-chained, append-only decision ledger | हर फ़ैसले के inputs (feature hash, max `available_at` ≤ decision_time), model version, threshold, action, fill, fees और बाद में outcome (P&L, MFE, MAE) | [Michelangelo](https://www.uber.com/blog/michelangelo-machine-learning-platform/); हमारा SHA-lock नियम |
| Trial registry | DSR/PBO/SPA के लिए पूरी trial गिनती | [Bailey & López de Prado](https://papers.ssrn.com/abstract=2460551) |
| Champion–challenger shadow | नया model पहले बिना orders के उसी input पर चले | [AWS shadow tests](https://docs.aws.amazon.com/sagemaker/latest/dg/shadow-tests.html); [MLflow aliases](https://mlflow.org/docs/latest/ml/model-registry/) |
| Drift monitoring (alerts) | Feature drift (PSI/KS), performance drift (ADWIN), prediction bias | [Sculley et al.](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf); [ADWIN docs](https://scikit-multiflow.readthedocs.io/en/latest/api/generated/skmultiflow.drift_detection.ADWIN.html) |
| Kill-switch और action limits | Equity DD, slippage breach, बार-बार API errors, data staleness पर reduce-only flatten-and-halt | Sculley "action limits"; 4H रिपोर्ट की checklist |
| Data quality checks | Missing/duplicate bars, UTC alignment, corrupt timestamps (raw 1m/15m 2025+ की ज्ञात समस्या), point-in-time universe | CLAUDE.md; [Binance API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints) |
| Shuffled, circular-shift और random-entry controls | Skill बनाम exposure अलग करना | Project नियम (`feedback-ai-claims-proof`) |

## उन्नत architecture: एक model, चार सहायक परतें

नीचे का ढाँचा प्रस्ताव के पाँच brains को बनाए रखता है, पर उनकी भूमिका बदलता है। Brains (A), (B) और (C) **feature producers** बनते हैं, जिनका output एक point-in-time store में जाता है। Strategy Library benchmark का काम करती है। Master Brain एक calibrated ensemble बनता है, जिसे equal-weight benchmark को हराना है। Risk, cost और execution अलग, नियम-आधारित परतें हैं, जिनके पास veto है। LLM पूरे loop के बाहर है।

```
            ┌──────────────────────── DATA LAYER (SHA-verified) ────────────────────────┐
            │ universe_all 1d/1h · universe_hf 15m/5m · perp 1h + funding (~135 coins)  │
            │ S7 order-book cost snapshots · listing/delisting dates (PIT universe)     │
            │ Data-quality checks: gaps, duplicates, UTC grid, corrupt-timestamp guard  │
            └──────────────────────────────────┬─────────────────────────────────────────┘
                                               ▼
   ┌──────────────────── POINT-IN-TIME FEATURE STORE (event_time + available_at) ─────────────────┐
   │ (A) Regime features: vol level, trend strength, BTC दिशा, persistent risk-off prob (filtered) │
   │ (B) Zone features: confirmed pivots only, ATR-distance, round-number distance, zone age       │
   │ (C) 4 signal families: trend (multi-lookback) · overextension · volatility · volume×return   │
   │ MTF: सिर्फ़ अगला बड़ा TF + 1D का आख़िरी CLOSED bar; 1W/1M = optional features                │
   │ Costs/funding/liquidity features (tier-wise, per-timestamp funding, interval flag)            │
   │ ✔ replay test  ✔ leak canary  ✔ assert max(available_at) ≤ decision_time                      │
   └──────────────────────────────────┬───────────────────────────────────────────────────────────┘
                                      ▼
   ┌──────────────── SIGNAL LAYER (decision TF: 4h/1h; 1D context) ────────────────┐
   │ (D) Strategy Library = rule baselines (trend/breakout ensemble)               │
   │ AI models: Phase-2 swing AI (4h/1h) · ranking brains (existing)               │
   │ (E) Master = calibrated ensemble; null = equal-weight + vol targeting;        │
   │     regime का असर सिर्फ़ ±tilt के रूप में                                       │
   │ Output: expected edge (ATR/%), calibrated prob, "no-trade" if edge ≤ k·cost    │
   └──────────────────────────────────┬───────────────────────────────────────────┘
                                      ▼
   ┌──────── RISK LAYER (rules, veto power) ────────┐   ┌──── COST LAYER ────┐
   │ inverse-vol sizing · gross cap (corr=1 मानकर) │◄──│ fee tier, spread,   │
   │ net beta cap · DD de-risking · short filters   │   │ funding, break-even │
   │ catastrophe stop policy (user निर्णय)          │   └─────────────────────┘
   └──────────────────────────────────┬────────────────┘
                                      ▼
   ┌──── EXECUTION LAYER (5m/15m = timing only) ────┐   ┌──── GOVERNANCE ──────────────────────┐
   │ post-only → taker fallback · algoOrder stops   │   │ trial registry · DSR/PBO/SPA          │
   │ MARK_PRICE · idempotent IDs · reconciliation   │   │ champion–challenger shadow · rollback │
   │ kill-switch · separate sub-account from 1D      │   │ drift alerts · independent verifier   │
   └──────────────────────────────────┬────────────────┘   │ hash-chained decision ledger          │
                                      ▼                    └───────────────────────────────────────┘
                     DECISION LEDGER (append-only; outcome + MFE/MAE बाद में लिखे जाएँ = labels)
                     LLM: सिर्फ़ research, code और व्याख्या; loop के बाहर
```

प्रस्ताव के decision flow से यहाँ दो बड़े अंतर हैं। पहला, Market → Zone → Volume → Strategy → MTF का **क्रमिक veto chain एक model में बदल जाता है**, जिसे ये सब features एक साथ मिलते हैं। Sequential vetoes हर कदम पर trials बढ़ाते हैं, और हमारा veto brain सिद्ध (0.529) होने के बावजूद redundant निकला था (`REPORT_1D_STEP17_18_14_OCT_2026.md`)। दूसरा, BUY/HOLD/SELL के साथ जो "confidence" आए, वह calibrated probability हो, यानी 0.6 कहे तो लगभग 60% बार सही हो। Meta-labeling साहित्य के अनुसार calibration fixed sizing functions को सुधारता है ⚠ ([Wikipedia: Meta-Labeling](https://en.wikipedia.org/wiki/Meta-Labeling))।

## चरणबद्ध, pre-registrable build plan: हर gate के बिना अगला कदम नहीं

प्रस्ताव का pipeline (market AI → strategy AI → learning AI → backtest → paper) सही दिशा में है, पर उसमें protocol lock, leakage परीक्षण, independent verifier और demo executor नहीं हैं, और "learning AI" verification से पहले आता है। नीचे का क्रम इन कमियों को भरता है। Gate thresholds हमारे प्रस्ताव हैं, जिन्हें protocol file में लिखकर SHA-lock करना होगा। हर चरण का independent verifier `claims.json` से जाँच करेगा। **चल रहे 1D cloud system को इस पूरे काम में छुआ नहीं जाएगा। उसके code को सिर्फ़ पढ़ा जा सकता है।**

| चरण | काम | निकास-शर्त (gate) |
|---|---|---|
| **0. User निर्णय** | SL/TP नीति, capital (₹ बनाम $), trade किए जाने वाले TFs (नीचे की तालिका) | User का स्पष्ट जवाब; उसके बिना protocol lock नहीं |
| **1. Research** | यह रिपोर्ट + ⚠ दावों का primary-source सत्यापन (Binance 1w/1M boundary, futures taker 0.04% बनाम 0.05%, sub-account नियम) | Verified दावों की सूची |
| **2. Protocol lock** | Phase 2 का सवाल, labels, decision TFs, cost tiers (S7 से), controls, gates, trial budget (~20–25), sealed holdout (2025-10 से 2026-09) | Protocol SHA-lock; बाद का हर बदलाव नया trial |
| **3. Knowledge store build** | PIT store: confirmed pivots, regime/zone/indicator families, cost/funding features; decision ledger schema; trial registry | Replay test 100% मेल; leak canary performance उछाले (harness काम करता है); `available_at` assertions पास |
| **4. Phase 2 swing AI** | 4h और 1h पर: "अभी पक्का हुआ swing आगे कितना चलेगा / क्या ≥3 ATR वाली बड़ी चाल है?"; inputs में Phase 1 के **सारे** factors (बाद में छाँटे बिना) और top-down features; walk-forward, purged/embargoed | OOS AUC shuffled वितरण के 95th percentile से ऊपर; 2017–2020 और 2021–2026 दोनों में skill |
| **5. Backtest** | Measured costs (perp taker 0.085%, maker 0.04%, spot 0.17%; 1×/1.5×/2× stress, taker 0.05% वाला संस्करण भी), असली funding, 5m intrabar stops, short filters, equal-weight + vol-target benchmark | Costs के बाद "बिना AI के सब swings follow करो" और trend baseline दोनों से बेहतर; DSR ≥ 0.95 पूरे trial count पर; PBO < 0.30; 1D LS से correlation ≤ 0.70 या combined Calmar बेहतर |
| **6. R4 re-test (वैकल्पिक, अलग trial)** | 1h R4 को measured costs पर नए pre-registered trial के रूप में | Registry में गिना जाए; दोनों legs की cost के बाद net > 0 at 1.5× stress |
| **7. Independent verifier** | अलग agent/script, code और data SHA से संख्याएँ दोहराए | हर दावा reproduce हो |
| **8. Sealed holdout** | एक बार खोलें | Gates वहीं भी पास; fail तो रुककर Hindi रिपोर्ट |
| **9. 90-दिन forward paper (shadow)** | Live data, कोई order नहीं, ledger में हर फ़ैसला | Realized cost ≤ 1.25× model; shadow-backtest tracking error सीमा में; कोई data/clock failure नहीं |
| **10. Demo executor** | `demo-fapi` पर algoOrder stops (MARK_PRICE), reconciliation, kill-switch, sandbox pre-flight, ≥30 दिन | शून्य orphan या stop-less positions; कोई duplicate order नहीं |
| **11. Real-money निर्णय** | सिर्फ़ user का, छोटे आकार से, 1D से अलग खाते/namespace में | User की स्पष्ट मंज़ूरी |

एक सीमा पहले से दर्ज करनी होगी: 90 दिन का paper test edge **साबित नहीं** कर सकता। Annual Sharpe 1.0 को 95% one-sided भरोसे से साबित करने में normal returns मानकर ~2.7 साल लगते हैं (≈ (1.645/SR)²), और crypto के fat tails इसे और लंबा करते हैं। इसलिए forward gates bugs, cost-model की ग़लती और disasters पकड़ने के लिए हैं, profitability साबित करने के लिए नहीं। (यह approximate formula हमारी गणना है। इसका औपचारिक ढाँचा MinTRL साहित्य में है ⚠ [Risk.net](https://www.risk.net/journal-risk/2223785/sharpe-ratio-efficient-frontier)।)

**Phase 2 अगला कदम क्यों होना चाहिए:** यह प्रस्ताव के लगभग हर अच्छे विचार को एक परीक्षण में समेटता है। Zone Brain के confirmed swings, Volume Brain का सबसे लगातार factor (volume spike), Multi-TF Brain का top-down असर और Strategy Library का trend/breakout baseline, सब इसमें आते हैं। सवाल भी वही है जो हमारे data ने खोला है: कमाई कुछ बड़ी चालों से आती है (औसत positive, median negative), तो क्या AI पहले से बता सकता है कि कौन-सा confirmed swing बड़ा बनेगा? यह 1D brains के "कौन coin बेहतर करेगा" वाले सवाल से अलग है, इसलिए portfolio में नई जानकारी जोड़ने की संभावना है। हमारे पुराने swing entry AI (AUC 0.530–0.539) और exit brains (0.505–0.526) असफल रहे थे, इसलिए Phase 2 का भी असफल होना एक वैध, संभावित नतीजा है।

## User से तीन निर्णय चाहिए, उनके बिना protocol lock नहीं होगा

| निर्णय | टकराव | विकल्प और सबूत |
|---|---|---|
| **SL/TP नीति** | प्रस्ताव कहता है "SL/TP auto नहीं लगेगा, user ने पहले कहा था"। पर चल रहा 1D system user-approved **F7** नियम पर है: exchange stop entry ×1.5 और 30-दिन cooldown (PASS: $88.4k, गिरावट 21.4%, 0 liquidation; `FINAL_INTEGRATED_PENDING_PLAN_16_OCT_2026.md`) | (क) सिर्फ़ चौड़ा, exchange-side catastrophe stop (`MARK_PRICE`), जो executor बंद होने पर भी account बचाए; (ख) कोई auto stop नहीं, सिर्फ़ analysis; (ग) tight SL/TP। Crypto में stops पर सबूत बँटा है: एक अध्ययन में volatility और returns दोनों लगभग आधे हुए ([Białkowski 2020](https://ideas.repec.org/a/eee/ecolet/v191y2020ics0165176519304227.html)), दूसरे में momentum का Sharpe बढ़ा ([Sadaqat & Butt 2023](https://ideas.repec.org/a/eee/beexfi/v39y2023ics2214635023000473.html))। Perps पर short के लिए हमारा सुझाव (क) है, पर निर्णय user का है |
| **Capital: ₹10,000 या $10,000?** | प्रस्ताव में "₹10,000, USDT में बदलकर"; project में $10,000 (80% traded / 20% reserve) | ₹10,000 लगभग सौ-सवा सौ डॉलर के बराबर है ⚠ (exchange rate verify नहीं किया)। इतने छोटे capital पर per-coin positions बहुत छोटी होंगी, और Binance की minimum notional सीमाएँ (इस शोध में verify नहीं हुईं) कई coins को बाहर कर सकती हैं। $1,000 वाले cost माप (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`) भी उस आकार पर सीधे लागू नहीं होंगे |
| **किन TFs पर trade हो?** | प्रस्ताव 5m–4h पर trade चाहता है | हमारा सुझाव: फ़ैसला 4h (और परीक्षण के बाद 1h) पर; 1D context; 5m/15m सिर्फ़ execution; 30m हटाएँ; 1W/1M सिर्फ़ optional features। आधार: 5m/15m का gross edge maker cost से भी कम, और 1W/1M का top-down असर साफ़ नहीं या उल्टा |

## हम अभी क्या नहीं जानते

हम नहीं जानते कि **Phase 2 swing AI costs के बाद कोई edge देगा या नहीं।** Phase 1 के factors अकेले कमज़ोर हैं (अधिकतम rank corr 0.17), और हमारे पिछले swing AI और exit AI असफल रहे। Phase 1 का realizable-trading भाग descriptive था, pre-registered नहीं। Multi-timeframe confluence का कोई बाहरी peer-reviewed OOS सबूत नहीं मिला, इसलिए हमारा top-down नतीजा (+0.47 से +0.76 ATR) फ़िलहाल एक ही dataset (10 coins) पर टिका है, और बड़े universe पर उसकी पुष्टि बाकी है। 1M context का उल्टा असर क्यों है, यह सिर्फ़ अनुमान है, और 1W/1M पर samples कम हैं (26–103 swings)। Crypto में costs के साथ OOS regime-switching backtest, S/R retests या liquidity zones का after-cost परीक्षण, RSI/Bollinger/ADX का अलग-अलग snooping-corrected परीक्षण, और crypto GP rules की OOS survival rate, इनमें से किसी पर अध्ययन नहीं मिला। Confidence-proportional या calibrated-Kelly sizing के fixed या vol-targeted sizing को costs के बाद हराने का crypto सबूत भी नहीं मिला। Online learning बनाम walk-forward retraining की trading P&L पर कोई peer-reviewed तुलना नहीं है। लागत में futures taker fee (0.04% बनाम 0.05%) अनसुलझी है, और $10,000 से बड़े trades या crash के समय की slippage का वितरण हमारे पास नहीं है। Binance के 1w/1M kline boundary conventions, sub-account नियम और minimum notional सीमाएँ verify नहीं हुईं। बाहरी स्रोतों में से कई preprints हैं (Kitron–Wengrowicz, Bysik–Ślepaczuk, Lopez-Lira et al., Dasari), और कई सिर्फ़ abstract स्तर पर पढ़े गए (Hudson–Urquhart, Huang et al., Grobys et al.)। सबसे बड़ा अज्ञात यह है कि कोई भी नया 4h/1h brain 1D LS line से पर्याप्त कम correlated होगा या नहीं। अगर उसकी कमाई bull-market long exposure से आती है, तो शायद नहीं होगा।

## निष्कर्ष

इस समीक्षा से सबसे बड़ा बदलाव यह है कि **"ज़्यादा brains" और "ज़्यादा समझदारी" एक चीज़ नहीं हैं।** हर नया brain, हर regime नियम और हर discovered strategy एक नया trial है, और crypto का साहित्य बार-बार दिखाता है कि जो चीज़ in-sample में सबसे चतुर दिखती है, वही out-of-sample में सबसे पहले टूटती है। प्रस्ताव की असली ताक़त उसकी intelligence में नहीं, उसके अनुशासन में है: बंद candle, साझा system, हर फ़ैसले का log, और frozen benchmark को हराने की शर्त। उन्नत design इसी अनुशासन को केंद्र में रखता है और "चुनने वाले" दिमाग को एक calibrated ensemble में बदल देता है, जिसे सबसे सरल मिश्रण को हराकर अपनी जगह कमानी होगी।

दूसरी सीख हमारे अपने data से आती है। Crypto swings हर timeframe पर एक जैसे दिखते हैं, पर पैसा हर timeframe पर एक जैसा नहीं बनता। Top-down जानकारी छोटे timeframe तक पहुँचती है, पर छोटे timeframe का edge costs में डूब जाता है। इसलिए सही ढाँचा उल्टा है: **बड़ा timeframe दिशा तय करे, 4h/1h फ़ैसला ले, और 5m/15m सिर्फ़ सही पल पर order रखे।** अगर Phase 2 भी gate पास नहीं करता, तो ईमानदार निष्कर्ष यह होगा कि 4H से नीचे अलग trading system न बनाया जाए, और छोटे timeframes का उपयोग सिर्फ़ 1D system के execution और risk के लिए हो। यह भी एक उपयोगी, सस्ता और verified नतीजा होगा।


---

# भाग 2 (17 अक्टूबर 2026): निरंतर scan → learn → decide brain, timeframe-वार फ़ैसले और अपने-आप लगने वाले stops

> **User के तीन तय निर्णय (इस भाग का आधार):** (1) **Stops अपने-आप और बाज़ार देखकर लगेंगे।** यह approved **F7** नियम के अनुरूप होगा (short stop entry ×1.5, 30-दिन cooldown), और F7 जैसा है वैसा ही रहेगा। (2) **Capital 10,000 USDT है।** इसमें 80% (8,000) trading के लिए और 20% (2,000) reserve रहेगा। (3) **अंत में सभी timeframes (5m से 1M) पर काम होगा, पर शुरुआत सिर्फ़ 4H से होगी।** अभी केवल research और design होगा, code नहीं। चल रहे 1D cloud system को छुआ नहीं जाएगा।
>
> *यह रिपोर्ट research है, वित्तीय सलाह नहीं।*

**मुख्य निष्कर्ष:** ऐसा "brain" बन सकता है जो लगातार बाज़ार देखे, हर फ़ैसला दर्ज करे और 4H से शुरू होकर हर timeframe पर अलग से फ़ैसला ले। पर इसका ईमानदार रूप वह नहीं है जो "निरंतर सीखने वाला AI" सुनकर मन में आता है। Scan, analyze, decide, act और record, ये पाँचों हर बंद candle पर अपने-आप चलें। **"Learn" वाला हिस्सा live model को कभी अपने-आप नहीं बदलेगा।** वह हर बंद candle और हर trade का नतीजा दर्ज करेगा, फिर तय समय पर (4H के लिए मासिक) walk-forward retraining करेगा। नया model पहले shadow में champion से मुक़ाबला करेगा, और pre-registered gate पास करने पर ही live में आएगा। इसकी वजह सबूत है। किसी peer-reviewed अध्ययन में costs के बाद online learning, scheduled retraining से बेहतर साबित नहीं हुई। हमारे अपने Step 11 में time-decay और bagging ने learning कमज़ोर की, और drift detectors noisy वित्तीय data में या तो drift चूकते हैं या झूठे alarms की बाढ़ लाते हैं। Stops के लिए design तीन परतों का है: सबसे बाहर F7 जैसा चौड़ा catastrophe stop, उसके अंदर ATR और swing पर आधारित बाज़ार-जागरूक stop, और फिर chandelier trailing, time stop और लगभग 2 ATR का target। Stops exchange पर `MARK_PRICE` trigger वाले algo orders होंगे। **AI entry लेगा या छोड़ेगा और size तय करेगा। Exit नियम निभाएँगे**, क्योंकि हमारे exit brains (AUC 0.505–0.526) असफल रहे थे। Timeframes अलग-अलग "sleeves" होंगे। हर sleeve की virtual position होगी, और coordinator उन्हें जोड़कर (net करके) exchange पर एक position रखेगा। Capital बाँटने का नियम सरल है: जो sleeve gate पास नहीं करता, उसका risk budget शून्य रहेगा।

## Bar close पर जागने वाला service, cron job नहीं: Binance पर event-driven ढाँचा

पूरा system एक **लंबे समय तक चलने वाला async service** होगा, जो systemd के नीचे `Restart=always` और watchdog के साथ चले। Binance हर 2 सेकंड में kline update भेजता है ([Binance Spot WS Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams))। 4H फ़ैसले के लिए कई मिनट का समय है, इसलिए छोटा VM काफ़ी है। असली ख़तरा latency नहीं, **liveness** है: connection चुपचाप मर जाए और system उसे पकड़ न पाए। Cron का काम सिर्फ़ backstop का होगा। वह जाँचेगा कि service की heartbeat और आख़िरी बंद candle ताज़ा हैं या नहीं। अगर WebSocket का रास्ता मरा हो, तो cron REST से candle खींचकर फ़ैसला चलवा सकता है। Freqtrade भी cron की जगह `process_throttle_secs` से throttled लगातार loop चलाता है ([Freqtrade bot basics](https://www.freqtrade.io/en/stable/bot-basics/))।

### ढाँचा एक नज़र में

```
 ┌─────────────────────────── BINANCE (अलग sub-account; 1D cloud system से पूरी तरह अलग) ───────────────────────────┐
 │ Spot WS :9443/:443 (ping 20s, 24h) · USDT-M wss://fstream…/market (ping 3min, 24h) · /private (user data)        │
 │ REST: /klines (backfill) · /time (clock) · openOrders · openAlgoOrders · positionRisk (reconcile)                │
 └──────────────┬───────────────────────────────────────────────────────────────┬───────────────────────────────────┘
                ▼ kline (x=true, t से dedupe)                                    ▼ ORDER_TRADE_UPDATE / ALGO_UPDATE
 ┌──────── INGEST ADAPTERS ────────┐                                  ┌──────── USER-STREAM ADAPTER ────────┐
 │ गैप जाँच: नया t = पिछला t + Δ?   │──── नहीं ───► REST backfill      │ listenKey हर 30–50 मिनट renew         │
 │ 2 connections (24h roll overlap)│                                  │ हर N मिनट REST से reconcile           │
 │ serverShutdown → पहले से नया WS │                                  └──────────────────┬────────────────┘
 └──────────────┬──────────────────┘                                                     │
                ▼  BarClosed(symbol, tf, open_time)  ── in-process MESSAGE BUS ──  OrderEvent / FillEvent
 ┌───────────────────── POINT-IN-TIME KNOWLEDGE BASE (append-only, साझा) ─────────────────────────┐
 │ bars (event_time, available_at) · features · regime/zone/volume · costs/funding · decision ledger│
 │ assert: हर फ़ैसले में max(available_at) ≤ decision_time   · SHA-hash हर snapshot पर               │
 └───────┬──────────────┬───────────────┬──────────────┬───────────────┬──────────────────────────┘
         ▼              ▼               ▼              ▼               ▼
   [4H sleeve]     [1h sleeve]     [1D sleeve]    [1W/1M context]  [5m/15m execution timing]
   सक्रिय (पहला)   gate के बाद     user निर्णय पर   पहले सिर्फ़ features  पहले सिर्फ़ order timing
   हर sleeve: frozen champion model → entry take/skip + size → नियम-आधारित exit plan → TARGET (order नहीं)
         └──────────────┴───────────────┴──────────────┴───────────────┘
                                        ▼
 ┌──────── COORDINATOR (netting) ────────┐   ┌──── RISK GATE (veto; नियम) ────────────────────────┐
 │ net_target[coin] = Σ sleeve virtual   │──►│ risk/trade cap · gross/net cap · per-coin cap     │
 │ per-sleeve P&L attribution ledger में  │   │ DD de-risk · kill-switch · data-staleness halt    │
 └───────────────────────────────────────┘   └──────────────────┬────────────────────────────────┘
                                                                ▼
 ┌──────── EXECUTION ENGINE ────────────────────────────────────────────────────────────────────┐
 │ order = net_target − reconciled position · clientOrderId = hash(decision_id, coin, leg)      │
 │ entry: post-only → taker fallback · stops: /fapi/v1/algoOrder STOP_MARKET, MARK_PRICE,        │
 │ reduceOnly/closePosition · पहले नया stop, फिर पुराना cancel (कभी बिना stop के position नहीं)    │
 └──────────────┬───────────────────────────────────────────────────────────────────────────────┘
                ▼
 RECORDER: हर raw WS message, REST response, फ़ैसला, fill, fee और बाद में outcome (MFE/MAE) → SHA chain → labels
                ▼
 LEARNING (loop के बाहर, तय समय पर): monthly walk-forward retrain → challenger → SHADOW → gate → manual promote
 MONITOR: drift alarms (frozen model पर) · bar-age · reconnects · clock offset · reconcile diff → Telegram/email
 LLM: सिर्फ़ research/code/व्याख्या; numeric फ़ैसलों से बाहर
```

### बंद candle को पहचानना और कोई candle न छूटना

Bar-close trigger kline payload के `x` flag ("Is this kline closed?") पर चलेगा, और kline के open time `t` से deduplicate होगा। यानी `BarClosed(symbol, tf, t)` event केवल `x == true` पर निकलेगा, और एक `(symbol, tf, t)` पर एक ही बार ([Binance Spot WS Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams))। REST पर भी "Klines are uniquely identified by their open time"। `/api/v3/klines` का weight 2 है, default limit 500 और अधिकतम 1000 ([rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md))। गैप पकड़ने के लिए हर `(symbol, tf)` का आख़िरी बंद `t` याद रखा जाएगा। हर नई candle पर और हर reconnect पर जाँच होगी कि नया `t` पिछले `t` में एक interval जोड़ने के बराबर है या नहीं। बराबर न हो तो `/klines?startTime=` से भरा जाएगा। 1M candles की लंबाई बदलती है, इसलिए वहाँ ms का fixed step नहीं, calendar गणित चलेगा। अगर WS संदेश खो जाए, तो `T` के कुछ सेकंड बाद एक REST poll fallback का काम करेगा।

Connections के टूटने को सामान्य घटना मानकर design करना होगा। Spot पर एक connection सिर्फ़ 24 घंटे वैध है। Server हर 20 सेकंड ping भेजता है और एक मिनट में pong न मिले तो connection काट देता है। Limits हैं: 5 incoming संदेश प्रति सेकंड, प्रति connection 1024 streams, और प्रति IP हर 5 मिनट में 300 connection attempts ([web-socket-streams.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/web-socket-streams.md))। 2026-05-06 से Binance disconnection से 10 मिनट पहले `serverShutdown` event भेजता है। 2026-07-09 जैसे infrastructure upgrades में connections "एक घंटे तक" कट सकते थे ([Spot CHANGELOG](https://developers.binance.com/docs/binance-spot-api-docs/CHANGELOG))। USDT-M पर base URL `wss://fstream.binance.com` अब routed है: `/public`, `/market` और `/private`। बिना route वाले connection पर `@markPrice` जैसे streams नहीं मिलते। वहाँ server हर 3 मिनट ping करता है, 10 मिनट में pong न मिले तो connection काटता है, 10 संदेश प्रति सेकंड और 1024 streams की सीमा है, और चेतावनी है कि "बार-बार disconnect होने वाले IPs ban हो सकते हैं" ([USDⓈ-M WS Connect](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Connect))। 1024 की संख्या पर विरोधाभास है: COIN-M page और NautilusTrader का code 200 मानते हैं ([Nautilus client.rs](https://nautilustrader.io/docs/core-latest/src/nautilus_binance/futures/websocket/client.rs.html))। हमारी ज़रूरत (10 coins × 7 timeframes = 70 streams) दोनों सीमाओं से बहुत नीचे है। इसलिए हर market के लिए एक connection, और 24h roll के समय overlap के लिए एक warm standby connection काफ़ी है। `serverShutdown` आते ही नया connection पहले खोला जाएगा।

ऊँचे timeframes को locally बनाने का विकल्प भी है: सिर्फ़ 5m (या 1m) subscribe करके 15m, 1h, 4h, 1D, 1W और 1M जोड़ लिए जाएँ, फिर exchange की बंद candles से मिलाए जाएँ। इससे streams कम होते हैं, पर सप्ताह और महीने की सीमाओं पर गड़बड़ी का ख़तरा है। Binance 1w candles का सोमवार 00:00 UTC पर खुलना इस session में verify नहीं हुआ। इसलिए शुरुआत में हर decision timeframe की kline सीधे subscribe करना सुरक्षित है, और local aggregation सिर्फ़ cross-check के लिए होगा। Clock का offset startup पर और हर कुछ मिनट पर `/fapi/v1/time` (या `/api/v3/time`) से मिलाया जाएगा। `recvWindow` ≤ 5000 रहेगा, क्योंकि server से लगभग 1 सेकंड आगे वाला timestamp reject होता है ([rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md))। Bar-close logic local घड़ी पर नहीं, exchange के `t`/`T` पर चलेगी।

### Fills, positions और 2025–26 में बदले Binance नियम

USDT-M पर user data अब भी listenKey से आता है (`POST/PUT/DELETE /fapi/v1/listenKey`), जो 60 मिनट में बंद हो जाता है ([USDⓈ-M User Data Streams](https://developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams))। इसलिए renew हर 30–50 मिनट पर होगा, और stream `/private` route पर चलेगा। Spot पर **listenKey वाला REST/WS-API user stream 2026-02-20 07:00 UTC से बंद है**, और उसकी जगह WS-API `userDataStream.subscribe.signature` आया है ([Spot CHANGELOG](https://developers.binance.com/docs/binance-spot-api-docs/CHANGELOG))। पुराने tutorials या libraries पर भरोसा करने वाला spot code चुपचाप fills खो देगा। Spot user-stream docs में संदेशों के क्रम या duplicates की कोई guarantee नहीं लिखी ([user-data-stream.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/user-data-stream.md))। इसलिए दोनों markets पर समय-समय पर REST से reconciliation अनिवार्य है।

सबसे बड़ा बदलाव stops के लिए है। **2025-12-09 से USDT-M के conditional types (STOP_MARKET, TAKE_PROFIT_MARKET, STOP, TAKE_PROFIT, TRAILING_STOP_MARKET) Algo Service पर चले गए हैं** (`/fapi/v1/algoOrder`, `openAlgoOrders`, `allAlgoOrders`)। पुराने `POST /fapi/v1/order` से ये भेजने पर `-4120 STOP_ORDER_SWITCH_ALGO` मिलता है। Rejection के कारण अब `ALGO_UPDATE` में आते हैं। 2025-12-29 से conditional orders की सीमा सभी symbols मिलाकर 200 है। 2026-08-21 से `ia` (activated) field live है, जिससे एक trailing stop NEW event दो बार भेज सकता है ([Derivatives change log](https://developers.binance.com/docs/derivatives/change-log))। NautilusTrader जैसे परिपक्व framework में भी पुराने code से `-4120` failure दर्ज हुआ ([GitHub issue #3287](https://github.com/nautechsystems/nautilus_trader/issues/3287))। हमारे लिए नियम साफ़ है: हर stop algoOrder रास्ते से जाए, `ALGO_UPDATE` के हर status (NEW, TRIGGERING, TRIGGERED, FINISHED, CANCELED, REJECTED, EXPIRED) को संभाला जाए, और test में साबित किया जाए कि legacy रास्ता इस्तेमाल ही नहीं होता।

Idempotency के लिए हर order का `newClientOrderId` deterministic होगा, जैसे `(decision_id, coin, leg)` का hash। Binance उसे खुले orders में unique रखता है। HTTP 5XX का अर्थ है कि order की हालत "UNKNOWN" है और वह सफल भी हो सकता है। इसलिए retry से पहले status पूछना ज़रूरी है। 429 पर `Retry-After` का पालन करना होगा, क्योंकि बार-बार उल्लंघन पर 418 IP ban मिलता है, जो 2 मिनट से 3 दिन तक बढ़ता है ([rest-api.md](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md))।

### Position mode: एक बार, live से पहले, सोचकर

USDT-M पर position mode पूरे account की **एक global setting** है (`dualSidePosition`)। यह "EVERY symbol" पर लागू होती है, और UM व CM दोनों में साझा है। खुले orders या positions रहते यह बदली नहीं जा सकती (`-4067`, `-4068`) ([Change Position Mode](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Position-Mode))। One-way mode में `reduceOnly` उपलब्ध है, Hedge mode में नहीं ([Binance USD-M Trade REST](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api))। इसका एक सीधा परिणाम है: **नया brain उसी account पर नहीं चल सकता जिस पर 1D cloud system चल रहा है।** वरना position mode, open orders और 200 वाली algo-order सीमा साझा हो जाएँगे, और नया system 1D system को अनजाने में बाधित कर सकता है। इसलिए अलग sub-account (या अलग testnet/demo account) ज़रूरी है। Sub-account के नियम (API keys, futures सक्षम करना, transfers) इस session में verify नहीं हुए, इसलिए यह protocol lock से पहले जाँचने का काम है। हमारी सिफ़ारिश **one-way mode और internal virtual sleeves** की है। NautilusTrader का NETTING-per-strategy model (`{instrument_id}-{strategy_id}`) यही करता है ([Nautilus Execution](https://nautilustrader.io/docs/latest/concepts/execution))।

### Backtest और live का एक ही code, और crash के बाद वापसी

परिपक्व frameworks का साझा pattern यह है कि strategy code एक in-process message bus से typed events (bar, fill, order update) लेता है, और वही code backtest और live दोनों में चलता है। NautilusTrader साफ़ कहता है कि live में venue, transport, timing, persistence और reconciliation का ऐसा व्यवहार जुड़ता है जो simulation नहीं दोहरा सकता। वह startup पर cached orders और positions को venue reports से मिलाता है, और "submission recovery restarts के पार नहीं जाती" ([Nautilus Live](https://nautilustrader.io/docs/latest/concepts/live))। QuantConnect LEAN का pipeline (Universe → Alpha `Insight` → Portfolio Construction `PortfolioTarget` → Risk → Execution) हमारे ढाँचे का भी आकार है, और उसमें "models आपस में बात न करें" का नियम है ([LEAN framework overview](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview))। Freqtrade का दर्ज mismatch चेतावनी के तौर पर काम आता है: वहाँ callbacks live में हर ~5 सेकंड चलते हैं पर backtest में candle में एक बार, जो "backtesting mismatches" पैदा करता है ([Freqtrade bot basics](https://www.freqtrade.io/en/stable/bot-basics/))। हमारा backtester recorded store से वही `BarClosed` objects replay करेगा, ताकि सिर्फ़ adapter और घड़ी बदलें, फ़ैसले का code नहीं।

Restart पर चार कदम क्रम से चलेंगे। पहला, persisted state load होगा। दूसरा, खुले orders, algo orders, positions और balances REST से reconcile होंगे। तीसरा, छूटी candles backfill होंगी। चौथा, जो candle system के बंद रहते बंद हुई, उसका फ़ैसला दोबारा गिना जाएगा, पर उस पर अमल तभी होगा जब वह अब भी freshness window के भीतर हो। वरना ledger में "skipped" दर्ज होगा।

### Testing और chaos: हर failure को जानबूझकर पैदा करना

हर raw WS संदेश और REST response, receive timestamp के साथ रिकॉर्ड होगा, ताकि उसे उसी adapter से replay किया जा सके। Binance के testnet और demo endpoints इस काम के लिए हैं: `wss://stream.testnet.binance.vision`, `wss://demo-stream.binance.com:9443` ([Spot WS Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams)), और futures के लिए `wss://stream.binancefuture.com` ([USDⓈ-M WS market streams](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams))। Testing के बारे में कोई authoritative सार्वजनिक प्रक्रिया नहीं मिली, इसलिए नीचे की matrix हमारा अपना design है।

| Chaos परीक्षण | पास होने की शर्त |
|---|---|
| Golden recorded दिनों का replay | फ़ैसले logged फ़ैसलों से byte-identical |
| Candle के बीच में और ठीक close पर WS काटना | वह candle REST backfill से ठीक एक बार process हो |
| Duplicate `x=true` संदेश | दोहरा trigger नहीं |
| Order भेजने के बाद, ack दर्ज होने से पहले crash | Restart पर `clientOrderId` से reconcile, कोई duplicate order नहीं |
| listenKey expiry और 24h roll | Fill का कोई event न खोए; reconcile diff शून्य |
| Clock skew > 1 सेकंड | पकड़ा जाए और ठीक हो, `-1021` न आए |
| Legacy conditional order भेजना | `-4120` आए; production रास्ता सिर्फ़ algoOrder |
| 5XX/UNKNOWN order status | पहले status query, फिर retry; दोहरा order नहीं |
| `serverShutdown` और घंटे भर का maintenance | Stops exchange पर बने रहें; system data-staleness पर halt करे |

Testnet पर `ALGO_UPDATE` और `/private` routing mainnet जैसे ही चलते हैं, यह verify नहीं हुआ। इसलिए shadow mode में फ़ैसले mainnet data पर होंगे, और orders सिर्फ़ testnet पर जाएँगे या कहीं नहीं जाएँगे।

## हर timeframe का अपना brain, पर exchange पर एक ही net position

हर timeframe एक अलग **sleeve** होगा। उसका अपना frozen model, अपना exit नियम, अपना risk budget और अपनी **virtual position** होगी। Sleeves orders नहीं भेजेंगे, सिर्फ़ target बताएँगे। Coordinator हर coin के लिए `net_target = Σ sleeve targets` निकालेगा। Execution engine `net_target − असली (reconciled) position` का order भेजेगा। Ledger में हर sleeve का P&L अलग से दर्ज होगा, ताकि पता रहे कि कौन-सा timeframe पैसा कमा रहा है और कौन-सा सिर्फ़ fees खा रहा है। इसके तीन विकल्प हैं, और उनका फ़र्क नीचे की तालिका में है।

| तरीका | फ़ायदा | नुकसान | हमारा उपयोग |
|---|---|---|---|
| **Netting (one-way + virtual sleeves)** | उलटे signals आपस में कटते हैं, fees और margin बचते हैं, attribution ledger में रहता है | उलटी दिशा वाले sleeves के stops virtual रहते हैं, यानी engine का ज़िंदा होना ज़रूरी | **Default** |
| Hierarchy (बड़ा TF दिशा, छोटा TF सिर्फ़ timing) | सरल, कम conflicts | जानकारी फेंकी जाती है | शुरू में 5m/15m के लिए यही (सिर्फ़ execution) |
| Physical अलगाव (sub-account प्रति sleeve, या hedge mode) | पूरी isolation, हर bucket का अपना exchange stop | दोगुनी fees और margin, transfers, hedge में `reduceOnly` नहीं | सिर्फ़ तब, जब netting के stops की समस्या बड़ी निकले |

Netting में एक ऐसा तनाव है जिसे design में पहले से सुलझाना होगा। User का निर्णय है कि stops अपने-आप लगें, और सबसे सुरक्षित stop वह है जो **exchange पर** बैठा हो, ताकि engine मर जाए तब भी account बचे। एक coin पर अगर एक ही sleeve सक्रिय है (4H वाले पूरे Phase में यही होगा), तो कोई समस्या नहीं: sleeve का stop सीधे exchange पर `reduceOnly` STOP_MARKET बनता है। एक ही दिशा के दो sleeves हों (4H long और 1h long), तो हर sleeve की मात्रा के बराबर अलग `reduceOnly` stop रखा जा सकता है। उलटी दिशा के sleeves (4H long, 1h short) में exchange पर सिर्फ़ net position होती है, इसलिए हर sleeve का अपना stop virtual बन जाता है, जिसे engine mark price देखकर लागू करता है। उस हालत में exchange पर net position का चौड़ा catastrophe stop backup का काम करता है। इसलिए हमारा प्रस्तावित नियम यह है: **जब तक दूसरा sleeve gates पास नहीं करता, conflict का सवाल ही नहीं उठता। उसके बाद, उलटी दिशा की स्थिति में छोटे timeframe के sleeve को सिर्फ़ net exposure घटाने की इजाज़त हो**, यानी नई उलटी position खोलने की नहीं। अगर यह नियम बहुत जानकारी फेंकता दिखे, तो hedge mode एक pre-registered विकल्प के तौर पर परखा जाएगा। Position mode global है और खुली positions के साथ बदला नहीं जा सकता, इसलिए यह चुनाव live से पहले एक बार होगा।

पिछली रिपोर्ट का एक सबक यहाँ भी लागू है: ऊँचे timeframe की हालत **feature** बने, veto नहीं। हमारे Phase 1 में अगला बड़ा timeframe साथ हो तो swing औसतन +0.5 से +0.8 ATR ज़्यादा चलता है, पर "कम से कम 1 ATR और" वाली संभावना लगभग वही (~76–78%) रहती है, यानी फ़र्क बड़ी चालों (tail) से आता है (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। यह जानकारी model के input में जानी चाहिए, किसी sequential veto chain में नहीं। Veto chain हर कदम पर trials बढ़ाती है, और हमारा सिद्ध veto brain भी redundant निकला था (`REPORT_1D_STEP17_18_14_OCT_2026.md`)। 1W का कोई साफ़ असर नहीं मिला, और 1M का असर उल्टा था। इसलिए 1W/1M पहले सिर्फ़ optional features होंगे।

### 10,000 USDT का बँटवारा: capital buckets नहीं, risk budgets

User के 80/20 निर्णय से **8,000 USDT trading के लिए और 2,000 USDT reserve** रहेगा। Reserve trading margin में इस्तेमाल नहीं होगा। वह सिर्फ़ तीन कामों के लिए है: margin call से बचाने वाला buffer, fees और funding का बफ़र, और drawdown के बाद नियम-आधारित refill (refill का नियम भी pre-registered होगा)। Trading हिस्से के भीतर हर timeframe को capital का अलग टुकड़ा देने के बजाय **risk budget** दिया जाएगा। कारण यह है कि sleeves एक ही coins पर net होते हैं, इसलिए capital के टुकड़े असली exposure नहीं बताते, जबकि stop दूरी पर टिका risk बताता है। पिछली रिपोर्ट का benchmark यहाँ master नियम है: proven sleeves में **equal risk + volatility targeting**, और कोई "smart" allocator तभी चुना जाएगा जब वह इस benchmark को gate पर हराए। **जो sleeve gate पास नहीं करता, उसका budget शून्य रहेगा।** इसलिए Phase 1 में पूरा trading risk 4H sleeve के पास होगा, पर कड़ी per-trade सीमा के साथ।

नीचे की संख्याएँ प्रस्ताव हैं। इन्हें protocol में लिखकर SHA-lock करना होगा, ये सबूत से निकले मान नहीं हैं। उदाहरण के लिए, प्रति trade risk trading capital का 0.5% (40 USDT) हो। Stop entry से 3% दूर हो तो notional लगभग 1,333 USDT बनता है। उस पर perp taker round trip (~0.085%) लगभग 1.1 USDT है, यानी risk amount का करीब 3%। साथ में ये सीमाएँ लगेंगी: gross notional trading capital के 1.5–2 गुने से ज़्यादा न हो, सभी coins का correlation 1 मानकर; per-coin cap; net beta cap; और drawdown पर क्रमिक de-risking। Binance की minimum notional सीमाएँ इस session में verify नहीं हुईं। 10,000 USDT पर ये शायद समस्या नहीं बनेंगी, पर कई sleeves में बँटने पर छोटे orders अटक सकते हैं।

## "निरंतर सीखना" का ईमानदार मतलब: लगातार देखना और लिखना, तय समय पर सीखना

User का सपना "हर पल सीखने वाला AI" है। सबूत कहता है कि इसका सबसे भरोसेमंद रूप **लगातार scanning और recording, तय समय पर retraining** है। मुख्य खोज एक अनुपस्थिति है। ऐसा कोई अध्ययन नहीं मिला जो एक ही task पर, costs के बाद, crypto में, online learner (River ARF, Hoeffding trees, online GBM) की scheduled walk-forward retraining से सीधी तुलना करे। जो कठोर सबूत मिला, वह **fitting scheme** के बारे में है, यानी window की लंबाई और कितनी बार दोबारा fit किया जाए, और वह दिखाता है कि यह चुनाव model के चुनाव जितना ही अहम हो सकता है। Gu, Kelly और Xiu ने वित्तीय ML का मानक benchmark बनाते हुए लिखा, "हम हर महीने recursively refit करने से बचते हैं, इसके बजाय साल में एक बार refit करते हैं"। उन्होंने expanding training window और rolling validation इस्तेमाल किया ([Gu, Kelly & Xiu, RFS 2020, NBER PDF](https://www.nber.org/papers/w25398.pdf))। Audrino और Chassot ने 1,445 stocks की volatility पर दिखाया कि जब सरल linear HAR model को ठीक fitting scheme मिलता है, तो भारी tuning वाले ML models उसे नहीं हरा पाते। यानी baseline का कमज़ोर scheme ML के edge को बढ़ा-चढ़ाकर दिखाता है ([Audrino & Chassot, arXiv 2406.08041, preprint](https://arxiv.org/abs/2406.08041))। इससे एक पक्का नियम निकलता है: अगर कभी "continuous learning" परखी जाए, तो दोनों पक्षों की window और frequency बराबर मेहनत से tune होंगी।

हमारा अपना नतीजा इसी तस्वीर में बैठता है। Step 11 में bagging और time-decay ने learning कमज़ोर की, और **monthly walk-forward retraining हमारा मानक रहा है**। Time-decay effective sample size घटाता है, जो कम signal-to-noise वाले data में नुकसान करता है। Pesaran और Pick ने पाया कि exponential down-weighting window averaging जितना ही अच्छा हो सकता है, पर वह "weighting coefficient के चुनाव पर निर्णायक रूप से निर्भर" है। जबकि **कई windows पर forecasts का औसत** छोटे breaks को छोड़कर हर स्थिति में किसी भी एक window से कम bias और कम RMSFE देता है ([Pesaran & Pick, CESifo WP 2293](https://www.cesifo.org/DocDL/cesifo1_wp2293.pdf))। Pesaran और Timmermann के अनुसार break से पहले का data भी शामिल करना कभी-कभी optimal होता है ([Pesaran & Timmermann 2007, J. Econometrics](https://rady.ucsd.edu/_files/faculty-research/timmermann/estimation-window.pdf))। इसलिए "ताज़ा data को ज़्यादा वज़न" का सबसे सुरक्षित रूप एक hard decay नहीं है। उसका सुरक्षित रूप है 1y, 2y, 3y और expanding windows पर अलग-अलग trained models का औसत। यह परिणाम सार्वभौमिक नहीं है: एक अध्ययन में हाल के break के बाद expanding window अक्सर सबसे सटीक रहा ([Hännikäinen 2015, MPRA, पढ़ा नहीं गया](https://mpra.ub.uni-muenchen.de/66826))। इसलिए window averaging भी एक pre-registered trial होगा।

Labels की देरी "online" के वादे को और कमज़ोर करती है। 4H पर अगर label का time barrier 12 candles (2 दिन) है, तो आज के फ़ैसले का label 2 दिन बाद पता चलेगा। Online update भी केवल उन labels से सीख सकता है जो कम से कम 2 दिन पुराने हैं, यानी purge और embargo की ज़रूरत बनी रहती है। "Continuous" learning lag नहीं हटाती, सिर्फ़ refit का अंतराल छोटा करती है। Online time-series forecasting में यह समस्या दर्ज है: ground truth forecast horizon के बाद ही मिलता है, और यह gap model को "पुराने concepts के अनुसार ढलने" पर मजबूर करता है ([Zhao & Shen, Proceed, arXiv 2412.08435](https://arxiv.org/abs/2412.08435))।

Drift detectors को retrain का automatic trigger बनाना भी जोखिम भरा है। एक बहुत ताज़ा preprint ने दिखाया कि Adaptive Random Forest के incremental updates post-drift error का ~98.6% सोख लेते हैं। इससे बाहर के cumulative monitors अंधे हो जाते हैं: simulated वित्तीय streams पर ARF के ऊपर Page-Hinkley ने 1,080 में से 0 shifts पकड़े, जबकि static RF पर F1 0.73–0.96 था। Noisy streams पर झूठे alarms की बाढ़ भी आई (1 असली drift पर 86 alarms) ([Minato et al., "The Blind Spot Paradox", arXiv 2610.05853, अक्टूबर 2026, preprint](https://arxiv.org/html/2610.05853))। Windowed detectors (ADWIN, KSWIN) इस तरह अंधे नहीं होते। इसका सबक: drift को एक **frozen** model की errors और feature distributions पर मापा जाए, ख़ुद को बदलते model पर नहीं। Concept drift साहित्य की समीक्षाएँ भी detection, understanding और adaptation को अलग चरण मानती हैं ([Lu et al., IEEE TKDE, arXiv 2004.05785](https://arxiv.org/pdf/2004.05785))। ICML 2025 का एक पेपर बताता है कि retrain का फ़ैसला कठिन है, क्योंकि जानकारी सीमित है, shift का स्वभाव अज्ञात है, और retrain की लागत बनाम ख़राब प्रदर्शन की लागत का अनुपात तय करना पड़ता है ([Regol et al., ICML 2025](https://proceedings.mlr.press/v267/regol25a.html))।

Live में सीखते रहने वाला RL agent सबसे ख़तरनाक रूप है, क्योंकि हर update असली पैसे पर तैनात एक नया, बिना जाँचा model है। Gort et al. ने लिखा कि पहले के DRL trading papers ने backtest में "optimistically" मुनाफ़ा दिखाया, जो overfitting से निकले false positives हो सकते हैं। उनका अपना OOS test भी सिर्फ़ लगभग 2 महीने का था ([Gort et al., arXiv 2209.05559, preprint](https://arxiv.org/abs/2209.05559))। Catastrophic forgetting पर replay या EWC से costs के बाद trading सुधार दिखाने वाला कोई अध्ययन नहीं मिला। Crypto में regimes लौटते हैं (bull, bear, chop)। हाल के data पर लगातार ढलता model पिछली मंदी को ठीक उसके लौटने से पहले भूल सकता है, और expanding window सबसे सरल anti-forgetting उपाय है।

### Learning loop का प्रस्तावित रूप

| परत | कितनी बार | अपने-आप? | क्या करती है |
|---|---|---|---|
| Scan | हर बंद candle (4H: दिन में 6 बार) | हाँ | Data ingest, गैप भरना, features PIT store में |
| Record | हर event | हाँ | Fills, fees, slippage, फ़ैसले के inputs; बाद में MFE/MAE और triple-barrier outcome = नए labels |
| Monitor | हर candle/दिन | हाँ (सिर्फ़ alarm) | Frozen champion पर ADWIN/KSWIN, feature PSI/KS, realized बनाम modeled cost, calibration (Brier) |
| **Risk घटाने वाला adaptation** | तुरंत | **हाँ, पर सिर्फ़ एक दिशा में** | Alarm, cost breach या DD पर size घटाना या halt; कभी size बढ़ाना नहीं |
| Retrain | 4H/1h/1D: मासिक; 1W/1M: तिमाही | हाँ (offline) | Window-averaged ensemble, purged/embargoed walk-forward |
| Challenger shadow | ≥ 1 retrain cycle | हाँ | नया model बिना orders उसी input पर; ledger में तुलना |
| Promote | Gate पास होने पर | **नहीं, manual + verifier** | Champion बदलना; पुराने पर rollback तैयार |

इस design का केंद्रीय सिद्धांत है कि **automatic बदलाव सिर्फ़ risk घटाने की दिशा में हो सकते हैं।** System ख़ुद size घटा सकता है, sleeve रोक सकता है या सब बंद कर सकता है। पर किसी model को बदलना, size बढ़ाना या नया sleeve शुरू करना pre-registered gate, independent verifier और user की मंज़ूरी से ही होगा। यह user के "AI ख़ुद सीखे" वाले लक्ष्य को काटता नहीं, उसे सुरक्षित रूप देता है। AI हर दिन सीखने का कच्चा माल इकट्ठा करता है, पर उस सीख का पैसे पर असर तभी होता है जब वह सबूत की कसौटी पार करे।

## अपने-आप लगने वाले stops: चौड़े, बाज़ार के हिसाब से, round numbers से दूर

Stops पर सिद्धांत साफ़ है और थोड़ा असहज भी। Random walk में stop-loss नियम expected return को हमेशा घटाता है। वह तभी फ़ायदा देता है जब returns में momentum या serial correlation हो, या बाज़ार शांत bull और volatile bear regimes के बीच बदलता हो ([Kaminski & Lo, J. Financial Markets 2014, सिर्फ़ abstract](https://dspace.mit.edu/handle/1721.1/114876); [WP संस्करण](https://swopec.hhs.se/sifrwp/abs/sifrwp0063.htm))। Lo और Remorov ने बड़े U.S. stock sample पर पाया कि **tight stops ज़्यादा trading costs के कारण buy-and-hold से पीछे रहते हैं**, और downside risk भी बहुत नहीं घटता ([Lo & Remorov, J. Financial Markets 2017, सिर्फ़ abstract](https://dspace.mit.edu/handle/1721.1/107017))। उसी काम के WP संस्करण के सारांश के अनुसार **wide stops regime-switching assets में buy-and-hold से बेहतर रहे**, बशर्ते bull regime कम volatile, bear regime ज़्यादा volatile और बदलाव कम हों ([CXO Advisory सारांश](https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth))। Crypto में सबूत सकारात्मक है, पर पुराना और सीमित है। Low-volatility crypto portfolios में एक सरल stop ने downside risk "काफ़ी" घटाया और Sharpe सुधारा (2017–2021) ([Kaya & Mostowfi, Finance Research Letters 2022](https://digitalcollection.zhaw.ch/bitstream/11475/23853/3/2022_Kaya-Mostowfi_Low-volatility-strategies-cryptocurrencies_frl.pdf))। 147 coins पर stop-loss momentum ने benchmark से बेहतर returns और Sharpe दिखाए ([Sadaqat & Butt, JBEF 2023](https://ideas.repec.org/a/eee/beexfi/v39y2023ics2214635023000473.html))। एक दूसरे अध्ययन में stops ने volatility और returns दोनों लगभग आधे किए ([Białkowski 2020, Economics Letters](https://ideas.repec.org/a/eee/ecolet/v191y2020ics0165176519304227.html))। **ATR stops बनाम fixed-% stops की कोई peer-reviewed head-to-head तुलना नहीं मिली,** न किसी asset में, न crypto में। "3×ATR से 15% बेहतर" जैसे vendor दावों के पीछे कोई अध्ययन नहीं है ([LuxAlgo](https://www.luxalgo.com/blog/how-to-use-atr-for-volatility-based-stop-losses/))।

हमारा F7 नतीजा (short stop entry ×1.5 और 30-दिन cooldown, जिससे drawdown सुधरा) इस साहित्य से मेल खाता है: stops मुख्यतः drawdown काटते हैं, mean return नहीं बढ़ाते। इसलिए design का पहला फ़ैसला है कि **4H का stop चौड़ा और regime-aware हो, tight नहीं।**

### तीन परतों वाला stop design

**परत 1, catastrophe stop (F7 का सिद्धांत):** हर खुली position के साथ exchange पर एक बहुत चौड़ा `STOP_MARKET` algo order रहेगा, `workingType=MARK_PRICE` और `closePosition=true` के साथ। इसका काम engine के मरने, API बंद होने या flash crash में account को बचाना है। 1D system का F7 नियम जैसा है वैसा ही रहेगा। 4H sleeve पर entry ×1.5 जैसी दूरी operational stop के लिए बहुत ज़्यादा है, क्योंकि 4H का आम swing 12.4% है (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। इसलिए 4H पर F7 का सिद्धांत सबसे बाहरी सुरक्षा परत बनेगा, और असली दूरी (जैसे liquidation price से पहले का कोई स्तर) protocol में तय होगी। F7 का cooldown भी अपनाया जाएगा: stop-out के बाद उसी coin और दिशा पर N candles का cooldown, जहाँ N एक pre-registered grid parameter होगा।

**परत 2, बाज़ार-जागरूक initial stop:** यह entry के समय अपने-आप लगेगा। इसकी दूरी swing संरचना और volatility दोनों से तय होगी: confirmed swing point के पार, ATR buffer के साथ, और round number से दूर। Volatility का regime (जैसे ATR percentile) multiple को चौड़ा या संकरा करेगा, पर हमेशा एक pre-registered [न्यूनतम, अधिकतम] ATR दायरे में। Round numbers से दूर रहने का कारण सबूत पर टिका है। FX में stop-loss orders गोल स्तरों के ठीक पार जमा होते हैं, और उनसे टकराने पर तेज़, ख़ुद को मज़बूत करने वाले price cascades बनते हैं ([Osler, NY Fed SR150 / JIMF 2005](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf))। Bitcoin में 10% से ज़्यादा prices 00 पर ख़त्म होती हैं ([Urquhart, Economics Letters 2017, सिर्फ़ abstract](https://eprints.soton.ac.uk/412873))। इसका अर्थ यह है कि obvious level के ठीक पार stop का hit होना ज़्यादा संभव है, और वहाँ fill भी ज़्यादा ख़राब होगा। Swing-point stops की ATR stops से तुलना करने वाला कोई अकादमिक परीक्षण नहीं मिला। "Swing − k×ATR" एक परखने लायक hypothesis है, सिद्ध नियम नहीं।

**परत 3, exit नियम:** chandelier या ATR trailing stop (entry के बाद के highest high से m×ATR नीचे, short के लिए उल्टा), time stop, और लगभग 2 ATR पर target। Chandelier की आम default (22 periods × 3 ATR) सिर्फ़ convention है, सबूत नहीं ([NexusFi](https://nexusfi.com/a/indicators/chandelier-exit))। Leung और Zhang ने गणितीय रूप से साबित किया कि trailing stop के साथ एक sell **limit** (take-profit) order जोड़ना optimal है। पर यह परिणाम exponential OU (mean-reverting) model पर है, crypto trend पर नहीं ([Leung & Zhang, Appl. Math. & Optimization 2021, arXiv 1701.03960](https://arxiv.org/pdf/1701.03960))।

### हमारे swing गणित से stop दूरी का तनाव

Phase 1 की संख्याएँ एक ढाँचागत trade-off दिखाती हैं, कोई मुफ़्त रास्ता नहीं। आम swing लगभग 5 ATR का होता है। Confirmation के समय उसका ~57% हो चुका होता है, यानी swing का शुरुआती pivot लगभग 2.85 ATR पीछे है। उसके बाद औसतन ~2 ATR और बचता है, और 75–78% बार कम से कम 1 ATR और। (यह गणना हमारी है, Phase 1 के औसतों से।) तो शुरुआती pivot के पार ATR buffer वाला "संरचनात्मक" stop entry से लगभग 3–3.5 ATR दूर पड़ेगा, जबकि target ~2 ATR है। ऐसे में break-even के लिए लगभग 60%+ बार target तक पहुँचना ज़रूरी होगा। हमें "+1 ATR तक पहुँचने" की base rate (~0.75) पता है, पर "−3 ATR से पहले +2 ATR" की नहीं। दूसरी तरफ़, extreme से 1–1.5 ATR से कसा trailing stop उन कई trades को काट देगा जिनमें अभी जगह बची है, और ~3 ATR का trailing stop बचे हुए 2 ATR का बड़ा हिस्सा लौटा देगा। इसलिए stop और exit के multiples **pre-registered grid** पर चुने जाएँगे (जैसे initial k ∈ {1.5, 2, 2.5, 3} ATR, संरचनात्मक variants और छोटे timeframe के swing के साथ), walk-forward OOS में और costs के बाद। चुनाव एक **plateau** से होगा, किसी अकेले peak से नहीं।

### Binance पर stop कैसे लगे

| विषय | फ़ैसला | आधार |
|---|---|---|
| Endpoint | `/fapi/v1/algoOrder`, `algoType=CONDITIONAL`, `triggerPrice` | [Binance USD-M Trade REST](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api); legacy पर `-4120` |
| Trigger | **`workingType=MARK_PRICE` स्पष्ट रूप से भेजें**; API default `CONTRACT_PRICE` है | [Binance docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api) |
| Type | `STOP_MARKET` (exit की guarantee; slippage संभव), stop-limit नहीं (gap में fill न होने का ख़तरा) | [Binance FAQ](https://www.binance.com/de/support/faq/360033779452) |
| आकार | One-way में `reduceOnly` (sleeve मात्रा) या `closePosition=true` (पूरी position; quantity/reduceOnly के साथ नहीं) | [Binance docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api) |
| `priceProtect` | **Testnet पर परखे बिना भरोसा नहीं।** यह mark और last के बीच अंतर बड़ा होने पर trigger रोकता है, यानी ठीक crash के समय | [Binance docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api) |
| Trailing | Native `TRAILING_STOP_MARKET` का `callbackRate` सिर्फ़ 0.1–10% है, ATR नहीं। इसलिए chandelier हर 4H close पर engine दोबारा गिनेगा और STOP_MARKET बदलेगा: **पहले नया stop, फिर पुराना cancel** | [Binance docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api); हमारा design |
| सीमा | सभी symbols पर कुल 200 conditional orders | [Derivatives change log](https://developers.binance.com/docs/derivatives/change-log) |
| Spot | `STOP_LOSS` (market) / `STOP_LOSS_LIMIT`, `trailingDelta`, OCO; short संभव नहीं | [Binance Spot trading endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints) |
| Backtest fill | Stop fill = stop और अगली candle के open में से ख़राब वाला, साथ में slippage; round numbers के पास ज़्यादा slippage | Osler के cascades से हमारा अनुमान |

Mark-price trigger last-price के पतले wicks (stop hunts) से बचाता है, पर fill फिर भी market पर होता है, इसलिए slippage बना रहता है। 4H पर spot या perp का सवाल costs तय करते हैं: perp taker round trip ~0.085%, maker ~0.04%, spot ~0.17% (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`)। Short सिर्फ़ perp पर संभव है। इसलिए 4H sleeve का स्वाभाविक घर कम leverage वाला USDT-M perp है। Spot ऊँचे timeframes (1W/1M) के long-only sleeves के लिए बाद में विचार हो सकता है, जहाँ funding का बोझ लंबी holding पर भारी पड़ सकता है।

## Entry AI तय करे, exit नियम निभाएँ: labels, meta-labeling और RL की जगह

User चाहता है कि entries और exits AI तय करे। सबूत इस इच्छा को एक ख़ास तरह से पूरा करने की सलाह देता है। हमारे per-bar "अभी exit करें?" वाले brains (AUC 0.505–0.526) और market-out brain असफल रहे। यह साहित्य से मेल खाता है: 4H पर हर candle पर exit की भविष्यवाणी लगभग अगले return के sign की भविष्यवाणी है, जो क़रीब-क़रीब random है। जो crypto काम सकारात्मक नतीजे दिखाता है, वह **formulation** बदलता है: event-based sampling, volatility-scaled barrier labels, और primary/secondary (meta) बँटवारा। BTC और ETH tick data (2018–2023) पर CUSUM-filtered bars और triple-barrier labeling ने time bars और next-bar prediction से बेहतर, costs के बाद लगातार सकारात्मक प्रदर्शन दिखाया ([Financial Innovation 2025, doi 10.1186/s40854-025-00866-w, सिर्फ़ abstract; barrier मान और cost स्तर unverified](https://link.springer.com/article/10.1186/s40854-025-00866-w))।

इसलिए प्रस्ताव यह है कि **AI चार फ़ैसले ले: किस confirmed swing पर entry, किस दिशा में, लेना या छोड़ना, और कितने size से।** Exit के लिए AI pre-registered नियमों (परत 2 और 3) का इस्तेमाल करेगा। Exit पर AI का प्रभाव एक ही नियंत्रित रास्ते से होगा: अगर अगली बंद candle पर उसी sleeve का model उलटी दिशा में ऊँची calibrated probability देता है, तो sleeve का target शून्य हो सकता है। यह "signal flip exit" भी अपने-आप में एक trial है, जिसे registry में गिना जाएगा।

**Labels:** triple-barrier labels ATR इकाइयों में होंगे, और barriers round-trip cost से काफ़ी चौड़े होंगे। अगर barrier का न्यूनतम return असली round-trip cost से कम है, तो pipeline cost वाले noise को signal समझकर सीखेगा ([MQL5 article, practitioner](https://www.mql5.com/es/articles/22372))। नीचे की तालिका दिखाती है कि यह शर्त किस timeframe पर कैसे बैठती है। "बचा हुआ ~2 ATR" आम swing का लगभग 40% है (swing ≈ 5 ATR)। ये प्रतिशत 10 coins के आम (median) swing से हमारी मोटी गणना हैं, किसी trade का अनुमान नहीं।

| TF | आम swing (%) | बचा हुआ ~2 ATR (%) | Perp taker 0.085% उसका कितना हिस्सा | Phase 1 long swing-following, costs से पहले: औसत / median |
|---|---|---|---|---|
| 5m | 1.6 | ~0.64 | ~13% | +0.02% / −0.79 ATR |
| 15m | 3.0 | ~1.2 | ~7% | +0.05% / −0.78 ATR |
| 1h | 6.2 | ~2.5 | ~3.4% | +0.33% / −0.67 ATR |
| 4h | 12.4 | ~5.0 | ~1.7% | +1.61% / −0.55 ATR |
| 1D | 30.1 | ~12 | ~0.7% | +10.95% / −0.42 ATR |

तालिका दो बातें कहती है। पहली, cost का बोझ छोटे timeframes पर कई गुना है। दूसरी, **बिना filter के हर swing follow करने का median trade हर timeframe पर ऋणात्मक है** (−0.4 से −0.9 ATR; 55–64% trades हारते हैं), कमाई कुछ बड़ी चालों से आती है, और 5m/15m/1h पर औसत costs से पहले ही लगभग शून्य है (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md`)। इसलिए AI का असली काम "कौन-सा confirmed swing बड़ा बनेगा" पहचानना है, जो पिछली रिपोर्ट का Phase 2 सवाल है। 4H पर BTC का median candle move 0.42% और alts का 0.6–0.84% है (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`)। यानी एक 4H candle का move भी taker cost का 5–10 गुना है, जो 4H को शुरुआत के लिए सबसे उचित timeframe बनाता है।

**Meta-labeling:** primary signal नियम-आधारित होगा (confirmed swing, ऊँचे TF की हालत, volume spike, जो Phase 1 का सबसे लगातार factor है)। Secondary model तय करेगा कि लेना है या नहीं, और calibrated probability से size तय करेगा। Meta-labeling पर Journal of Financial Data Science की श्रृंखला के अनुसार calibration fixed position-sizing को ठीक-ठाक सुधारता है, जबकि training data से सीखे sizing functions से ज़्यादा फ़ायदा नहीं होता ([Hudson & Thames, meta-labeling series, सिर्फ़ abstract](https://hudsonthames.org/tag/meta-labeling/); [Wikipedia: Meta-Labeling](https://en.wikipedia.org/wiki/Meta-Labeling))। Crypto में costs के बाद meta-labeling की कोई स्वतंत्र OOS पुष्टि नहीं मिली। Model को सिर्फ़ AUC से नहीं, base rate से तौला जाएगा। "+1 ATR बनाम stop" वाले barrier की base rate ~0.75 है, इसलिए meta-model को calibrated Brier या log-loss में उस base rate को हराना होगा, और shuffled-label control के 95th percentile से ऊपर रहना होगा।

**RL** बाद का research विषय है। Crypto में costs के साथ और कई साल के OOS में RL exit या stop placement का कोई credible अध्ययन नहीं मिला। Ensemble DRL पर एक preprint मानता है कि आख़िरी epoch वाले models regime shift में बुरी तरह विफल हो सकते हैं ([arXiv 2309.00626, preprint](https://arxiv.org/pdf/2309.00626))। अगर RL कभी परखा जाए, तो वह offline train होगा और freeze रहेगा, कई seeds के साथ और PBO/DSR controls के साथ चलेगा, और shadow में champion से मुक़ाबला करेगा। Live में ख़ुद को update करने वाला RL agent इस design में कहीं नहीं है।

## 4H पहले, बाकी timeframes gate पास करने पर: चरणबद्ध, pre-registrable योजना

यह योजना पिछली रिपोर्ट के 11 चरणों को continuous engine, stops और sleeves तक बढ़ाती है। सारे gate thresholds हमारे प्रस्ताव हैं। Protocol file में लिखकर उन्हें SHA-lock करना होगा, और हर दावे की जाँच independent verifier `claims.json` से करेगा। चल रहा 1D cloud system पूरी अवधि में अछूता रहेगा। उसका code सिर्फ़ पढ़ा जा सकता है।

| चरण | काम | Gate (निकास-शर्त) |
|---|---|---|
| **A0. Protocol lock (4H)** | सवाल, labels (ATR triple-barrier), stop/exit grid, cooldown grid, cost tiers (0.085/0.04/0.17%, 1×/1.5×/2× stress), position mode, sub-account, trial budget, sealed holdout | Protocol SHA-lock; बाद का हर बदलाव नया trial |
| **A1. Knowledge base + recorder** | PIT store (`event_time`, `available_at`), decision ledger, trial registry, raw message recorder | Replay 100% मेल; leak canary performance उछाले; `available_at` assertions पास |
| **A2. 4H entry AI (meta-label)** | Confirmed swing + top-down + volume features; monthly walk-forward, purged/embargoed; window-averaged ensemble बनाम एक window | OOS skill shuffled 95th percentile से ऊपर; Brier base rate से बेहतर; 2017–2020 और 2021–2026 दोनों में |
| **A3. Stop और exit परीक्षण** | (क) सिर्फ़ catastrophe, (ख) fixed ATR, (ग) swing + ATR buffer + round-number से दूरी, (घ) chandelier + time stop + ~2 ATR TP; 5m intrabar fills, gap-through | Costs के बाद plateau; drawdown घटे और net return F7-only से बदतर न हो; random-entry control से बेहतर |
| **A4. Backtest + verifier** | Equal-weight + vol-target benchmark, असली funding, short filters | Net > 0 at 1.5× cost; DSR ≥ 0.95 पूरे trial count पर; PBO < 0.30; 1D से correlation ≤ 0.70 या combined Calmar बेहतर; verifier हर संख्या दोहराए |
| **A5. Sealed holdout** | एक बार खोलें | वहाँ भी gates पास; fail होने पर रुककर Hindi रिपोर्ट |
| **A6. Engine + chaos (testnet/demo)** | Event-driven service, algoOrder stops, reconcile, kill-switch, sandbox pre-flight | ऊपर की chaos matrix 100% पास; शून्य orphan या stop-less position; शून्य duplicate order |
| **A7. 90-दिन shadow (mainnet data, कोई order नहीं) + demo executor** | हर फ़ैसला ledger में; champion-challenger ढाँचा चालू | Realized cost ≤ 1.25× model; shadow और replay का tracking error सीमा में; कोई data या clock failure नहीं |
| **A8. Real money** | सिर्फ़ user का निर्णय; 8,000 USDT का छोटा हिस्सा पहले | User की स्पष्ट मंज़ूरी |
| **B. 1h sleeve** | A0–A7 दोहराना; netting/conflict नियम सक्रिय | ऊपर के gates, और **portfolio में incremental value** (4H के साथ combined Calmar बेहतर) |
| **C. 1D sleeve** | चल रहे 1D system से अलग; integrate करना या न करना user का निर्णय | वही gates; 1D cloud system में कोई बदलाव नहीं |
| **D. 1W/1M** | पहले context features; sleeve सिर्फ़ तब जब samples पर्याप्त हों (1W/1M पर 26–103 swings) | Features का OOS योगदान साबित; sleeve के लिए वही gates |
| **E. 5m/15m** | Default भूमिका सिर्फ़ execution timing (post-only entry, stop/fill गुणवत्ता) | अलग sleeve सिर्फ़ तब, जब costs के बाद gross edge साबित हो; वरना timing ही रहें |

एक सीमा पहले से दर्ज करनी होगी। 90 दिन का shadow edge **साबित नहीं** कर सकता। Annual Sharpe 1.0 को 95% one-sided भरोसे से साबित करने में normal returns मानकर लगभग 2.7 साल लगते हैं (≈ (1.645/SR)², हमारी गणना), और crypto के fat tails यह समय और बढ़ाते हैं। Forward gates bugs, cost-model की ग़लती और disasters पकड़ने के लिए हैं। Edge का सबूत pre-registered backtest, verifier और sealed holdout से आता है।

## हम अभी क्या नहीं जानते

सबसे बड़ा अज्ञात यह है कि **4H entry AI costs के बाद कोई edge देगा या नहीं।** हमारे पिछले swing entry AI (AUC 0.530–0.539) और exit brains असफल रहे, इसलिए Phase 2 का असफल होना एक वैध और संभावित नतीजा है। अगर ऐसा हुआ, तो continuous engine फिर भी काम का है: वह 1D system के लिए execution और risk ढाँचा बन सकता है। Online learning बनाम scheduled retraining की costs के बाद crypto में कोई तुलना नहीं मिली, न time-decay के net trading असर का कोई अलग अध्ययन, न असली crypto returns पर ADWIN, KSWIN या Page-Hinkley की false-alarm दरें। "Blind Spot Paradox" अक्टूबर 2026 का ताज़ा preprint है और simulated streams पर टिका है। ATR stops बनाम fixed-% stops, swing-point stops, trailing stops, breakeven moves और partial take-profits, इनमें से किसी पर crypto का peer-reviewed OOS सबूत नहीं मिला, इसलिए ये सब हमारे अपने pre-registered परीक्षण पर टिके हैं। Kaminski–Lo, Lo–Remorov, Urquhart, meta-labeling series और Financial Innovation 2025 सिर्फ़ abstract या सारांश स्तर पर पढ़े गए।

Binance की तरफ़ कई बातें verify नहीं हुईं। USDT-M kline stream का पूरा पाठ नहीं पढ़ा गया। USDT-M `/klines` की अधिकतम limit, futures WS की प्रति-IP connection-attempt सीमा, और streams की सीमा (1024 बनाम 200) अनिश्चित हैं। यह भी पक्का नहीं कि legacy futures WS URLs 2026-04-23 को बंद हुए या नहीं। Testnet पर `ALGO_UPDATE` और `/private` की mainnet से समानता, crash के समय `priceProtect` का असली व्यवहार, और stop-market orders की slippage का वितरण भी अज्ञात है। Sub-account के नियम, minimum notional सीमाएँ, futures taker fee (demo API 0.04% बनाम FAQ 0.05%), और 1w/1M candle की सीमाएँ भी जाँचनी बाकी हैं। Netting बनाम अलग sleeves का multi-timeframe crypto पर कोई मापा हुआ तुलनात्मक अध्ययन नहीं मिला, और VM sizing पर कोई benchmark नहीं है। Funding rate का 4H perp sleeve पर असर इस भाग में नहीं मापा गया। Phase 1 के top-down और volume नतीजे सिर्फ़ 10 coins पर हैं, और बड़े universe पर उनकी पुष्टि बाकी है।

## निष्कर्ष

इस भाग से सबसे बड़ा बदलाव "निरंतर" शब्द के अर्थ में है। User का "लगातार scan, learn, decide" वाला brain बन सकता है, पर उसकी निरंतरता **देखने, लिखने और risk घटाने** में होगी, model को ख़ुद बदलने में नहीं। सबूत यह नहीं कहता कि live-learning बेहतर है। वह कहता है कि fitting scheme का चुनाव नतीजे पलट सकता है, labels देर से आते हैं, और ख़ुद ढलता model उसी drift को छिपा देता है जिसे पकड़ना था। इसलिए यहाँ AI की "समझदारी" उसके हर दिन बदलने में नहीं, बल्कि हर बदलाव से पहले उसे shadow में साबित करने की मजबूरी में है। एक ही नियम इस पूरे design को बाँधता है: **ख़ुद-ब-ख़ुद सिर्फ़ जोखिम घट सकता है, बढ़ाने के लिए हर बार सबूत चाहिए।** यही नियम stops (catastrophe परत कभी नहीं हटती), capital (unproven sleeve का budget शून्य) और learning (promotion manual) पर एक साथ लागू होता है।

दूसरी नई सीख हमारे अपने swing गणित से आती है। Stop की सही दूरी और target की उम्मीद एक-दूसरे से टकराती हैं: संरचनात्मक stop लगभग 3 ATR दूर है, जबकि बचा हुआ इनाम लगभग 2 ATR है। इसका अर्थ है कि इस system का edge, अगर है, तो **stops की चतुराई से नहीं, entry के चुनाव से आएगा**, यानी उन कुछ confirmed swings को पहचानने से जो बड़े बनते हैं। इसलिए AI की असली जगह entry और size पर है, और exits नियमों को सौंपना कमज़ोरी नहीं, हमारे असफल exit brains से सीखा गया सबक है। अगर 4H पर भी यह entry AI gate पास नहीं करता, तो ईमानदार अगला कदम और timeframes जोड़ना नहीं होगा। तब यही event-driven ढाँचा, ledger और stop परतें 1D system की सेवा में लगेंगी, और यह भी एक सस्ता, verified और उपयोगी नतीजा होगा।


---

# भाग 3 (17 अक्टूबर 2026): पूरे दस्तावेज़ का सत्यापन, सुधार और अंतिम multi-timeframe AI design

> **इस भाग का आधार (user के तय निर्णय):** Binance spot + USDT-M perps, long और short; capital 10,000 USDT, जिसमें 8,000 trading और 2,000 reserve; stops अपने-आप और बाज़ार देखकर लगेंगे, approved F7 के अनुरूप; पहले 4H, फिर सारे timeframes (5m, 15m, 1h, 4h, 1D, 1W, 1M) sync में। अभी सिर्फ़ research और design होगा, code नहीं। चल रहा 1D cloud system अछूता रहेगा।
>
> **अस्वीकरण:** यह research है, वित्तीय या निवेश सलाह नहीं। लेखक licensed advisor नहीं है। इस भाग में कोई नया backtest नहीं चला। Timeframe के आँकड़े `data/universe_hf` के SHA-locked 5m data से निकाले गए हैं (8 coins, 2020-01 से 2026-09)। ⚠ का मतलब है preprint, सिर्फ़ abstract या summary, vendor research, या इस pass में primary स्रोत न खोला गया। "प्रस्ताव" वाली हर संख्या हमारा सुझाव है। उसे protocol में लिखकर SHA-lock करना होगा, वह साहित्य से निकला मान नहीं है।

**मुख्य निष्कर्ष:** Parts 1–2 की independent जाँच में **कोई मुख्य सिफ़ारिश नहीं पलटी।** 4H पहले, exits नियमों से, equal-weight benchmark, scheduled retraining और अलग sub-account, ये सब टिके रहे। पर चार आंतरिक ग़लतियाँ ठीक करनी होंगी, क्योंकि इनसे कारण या risk की संख्याएँ बदलती हैं। (1) Exit brain के बारे में दस्तावेज़ ने कहा कि वह "असफल रहा, AUC 0.505–0.526"। असल में Step 26 के exit brain में **असली skill थी (AUC 0.672)**, पर वह पैसे में नहीं बदली। (2) 1h को ग़लती से "लगभग शून्य" कहा गया, जबकि उसका gross औसत **taker cost का ~3.9 गुना** है। (3) "5m/15m maker cost से भी कम" सिर्फ़ 5m पर सही है। (4) **Sealed holdout (2025-10 से 2026-09) दूषित है**, इसलिए अब एकमात्र साफ़ holdout 2026-10-17 के बाद का forward data है। अंतिम design छोटा है: **तीन AI brains** (धीमा context/regime brain, horizon-family वाला pooled alpha/meta-label brain, और calibrated size function) और **तीन नियम-आधारित परतें** (risk और stops engine, 5m/15m execution layer, monitor/kill-switch)। Timeframes का sync इस नियम से होता है: **बड़ा timeframe size तय करता है, दिशा पर veto नहीं लगाता। हर TF सिर्फ़ अपना आख़िरी बंद bar देखता है। छोटा TF बड़े के ख़िलाफ़ सिर्फ़ exposure घटा सकता है। और 5m/15m सिर्फ़ order का समय चुनते हैं।** हमारे data में cost एक median candle की चाल का 5m पर 68% और 1D पर 3.7% है। इसलिए stops, targets और time stops हर timeframe के अपने ATR और bar-count में होंगे, और AI alpha अभी सिर्फ़ 4H पर ठीक बैठता है।

---

## सत्यापन और सुधार (errata): सिफ़ारिशें टिकीं, चार कारण और risk की संख्याएँ बदलीं

**जाँच कैसे हुई:** Parts 1–2 (मूल दस्तावेज़ की पंक्तियाँ L1–433) के **25 बाहरी दावे** primary pages पर मिलाए गए, या "NOT CHECKED" लिखे गए। आंतरिक संख्याएँ project reports से grep की गईं, और derived गणित दोबारा किया गया। मूल दस्तावेज़ बदला नहीं गया, और `archive/` नहीं खोला गया।

**Binance वाला हिस्सा सबसे भरोसेमंद निकला।** जितनी तारीख़ें जाँची गईं, सब official changelogs से मेल खाईं। ये verify हुईं:

| Binance दावा | तारीख़ / मान | स्रोत |
|---|---|---|
| Conditional orders algoOrder पर, legacy endpoint पर `-4120` | 2025-12-09 | [Derivatives change log](https://developers.binance.com/docs/derivatives/change-log) |
| सभी symbols मिलाकर 200 conditional orders की सीमा | 2025-12-29 | वही |
| `ia` field live | 2026-08-21 | वही |
| `workingType` का default `CONTRACT_PRICE`, `priceProtect` का default false | — | [New Algo Order](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Algo-Order) |
| Position mode पूरे account की setting | — | [Change Position Mode](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Position-Mode) |
| Spot listenKey बंद | 2026-02-20 | [Spot CHANGELOG](https://developers.binance.com/docs/binance-spot-api-docs/CHANGELOG) |

**सबसे ज़्यादा भटकाने वाली ग़लतियाँ हमारे अपने आँकड़ों के हवाले में थीं**, बाहरी साहित्य में नहीं। Coordinator ने सुधार #1 ख़ुद `REPORT_EXIT_STEP26_15_OCT_2026.md` में verify किया है। इस pass में उसी file की पंक्तियाँ 19–30 दोबारा पढ़कर मिलाई गईं।

### चार आंतरिक ग़लतियाँ जो कारण या संख्या बदलती हैं

| # | कहाँ (मूल दस्तावेज़) | क्या लिखा था | सत्यापन में क्या मिला | सही कथन |
|---|---|---|---|---|
| **1** | Part 1 तालिका (L33), Part 1 L178, Part 2 BLUF (L207) और L381 | "AI exit brains असफल (AUC 0.505–0.526)"; L381: "हर candle पर exit की भविष्यवाणी लगभग random है" | Step 10 के exit brains का AUC 0.505–0.527 था (Path 2, 1 दिन: 0.527, CI 0.510–0.544; `REPORT_1D_STEP10_AI_13_OCT_2026.md` L41–42)। **पर Step 26 का exit brain (बड़ी गिरावट पहचानने वाला) AUC 0.672 पर था** (99% CI 0.644–0.699; shuffled 0.521; 2018–19 में, जो कभी देखा नहीं गया था, 0.635)। फिर भी **पैसे पर FAIL:** Calmar 0.623, जबकि exit के बिना (R24) 0.920 था; random exit (95th percentile) 0.634 से भी बेहतर नहीं; max drawdown 74.7% से 75.6% (घटा नहीं); $10k → $91,928, जबकि बिना exit $201,548 (`REPORT_EXIT_STEP26_15_OCT_2026.md` L19–30) | **"Exit की भविष्यवाणी में skill है, पर वह पैसे में नहीं बदली। इसलिए exits नियम-आधारित रहेंगे, और AI exit एक अलग, pre-registered trial होगा।"** |
| **2** | Part 2 L395 | "5m/15m/1h पर औसत costs से पहले ही लगभग शून्य" | 1h swing-following का gross औसत **+0.33% प्रति trade** है, जो measured perp taker 0.085% का **~3.9 गुना** है। Median trade अब भी नकारात्मक है (−0.67 ATR; जीत 39%)। "≈0" शब्द Swing Anatomy L152 से आया था, जो पुराने ~0.15–0.5% cost के हिसाब से लिखा गया था (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md` L142–152) | "5m/15m ≈ cost के बराबर। **1h gross-positive है** (taker का ~3.9×), पर median नकारात्मक है, इसलिए 1h दूसरा sleeve बनने का गंभीर उम्मीदवार है" |
| **3** | Part 1 L67, L186 | "5m/15m का +0.02–0.05% gross edge perp maker cost से भी कम" | Maker round trip में fee 0.036% है, spread मिलाकर ~0.04% (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`)। **5m (+0.02%) इससे नीचे है, पर 15m (+0.05%) थोड़ा ऊपर** | "5m maker cost से नीचे, 15m ≈ maker cost, दोनों taker 0.085% से बहुत नीचे" |
| **4** | Part 1 चरण 2 और 8 (L165, L171), Part 2 A0 और A5 (L407, L412); `RESEARCH_4H` L114 | Sealed holdout = 2025-10 से 2026-09 | Swing Anatomy ने 2026-09 तक का data इस्तेमाल किया, और Phase 2 को उसी के factors लेने को कहा गया है। Fee report ने 4H moves ठीक Oct 2025–Sep 2026 पर मापे। **इस Part 3 के timeframe आँकड़े भी 2026-09 तक के हैं।** यानी holdout के महीने design में दिख चुके हैं | **नया नियम:** एकमात्र साफ़ holdout **2026-10-17 और उसके बाद का forward data** है (paper/shadow)। साथ में 2018–19 frozen रहेगा, पर सिर्फ़ spot-direction skill के लिए। 2025-10 से 2026-09 अब एक घोषित "**seen**" अवधि है |

**सुधार #1 Part 2 के "AI entry ले, नियम exit करें" वाले तर्क की नींव बदलता है, निष्कर्ष नहीं।** पुराना कारण था कि exit की भविष्यवाणी random है। सही कारण इससे ज़्यादा दिलचस्प है और ज़्यादा सावधानी माँगता है। AUC सिर्फ़ ranking मापता है: AI बड़ी गिरावटों को सही क्रम में पहचानता था। पर पैसा इस पर टिका है कि exit के बाद जो चाल छूटी, उसकी क़ीमत बचाई गई गिरावट से ज़्यादा थी या नहीं। एक संभावित व्याख्या साहित्य से मेल खाती है, पर साबित नहीं है। Kaminski और Lo के अनुसार random walk में stop या exit नियम expected return घटाता है, और momentum होने पर ही फ़ायदा देता है ⚠ (WP abstract; [SIFR WP](https://swopec.hhs.se/sifrwp/abs/sifrwp0063.htm))। हमारे 1D data में VR(4) 0.94 है, यानी हल्का mean reversion (नीचे का खंड देखें)। ऐसे बाज़ार में गिरावट के बाद का rebound अक्सर छूटी हुई चाल बन जाता है। इसलिए किसी भी भविष्य के AI exit trial का gate AUC नहीं, बल्कि **Calmar और drawdown, random-exit control के मुक़ाबले** होगा, ठीक जैसे Step 26 में था।

**सुधार #4 सबसे बड़ा प्रक्रिया-संबंधी बदलाव है।** "Sealed" holdout तभी sealed है जब उसके महीनों को देखकर कोई चुनाव न हुआ हो। यहाँ factors, cost माप और timeframe आँकड़े सब उन्हीं महीनों से गुज़रे हैं। इसलिए 2025-10 से 2026-09 पर पास होना अब "नया सबूत" नहीं गिना जाएगा। वह validation का एक घोषित हिस्सा होगा। इसकी क़ीमत भी साफ़ है। साफ़ सबूत अब धीरे-धीरे आएगा, क्योंकि forward data की हर तारीख़ असली समय में बीतनी होगी। इसका व्यावहारिक नतीजा यह है कि **recorder को आज से चलाना फ़ायदेमंद है**, model बनने से पहले भी। Shadow फ़ैसले बाद में तभी साफ़ गिने जाएँगे जब protocol उस data को देखने से पहले lock हुआ हो।

### Costs, risk और stop–target गणित के सुधार

**Cost की हर संख्या में एक छिपी शर्त थी।** 0.085% (perp taker), 0.04% (maker) और 0.17% (spot) तीनों **BNB fee discount और $1,000 trade** मानते हैं। Futures पर BNB छूट तभी मिलती है जब BNB futures wallet में रखा हो (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`)। आगे से हर जगह यह पूरी तालिका इस्तेमाल होगी:

| Round trip (fee + median spread, $1,000) | BNB के साथ | BNB के बिना |
|---|---|---|
| Perp taker (demo API, 0.04%) | **0.085%** | **0.092%** |
| Perp taker (Binance FAQ, 0.05%) | ~0.10% | ~0.11% |
| Perp maker, दोनों तरफ़ | ~0.04% | ~0.04% (fee 0.040%) |
| Spot market | 0.17% | ~0.22% |

Spread trade के आकार के साथ बढ़ता है। Perp पर median spread $1,000 पर 0.012%, $3,333 पर 0.017% और $10,000 पर 0.027% है (वही report)।

**Risk के उदाहरण में stop slippage छूट गई थी, और वही सबसे बड़ा cost term है।** Part 2 (L317) का हिसाब था: 0.5% × 8,000 = 40 USDT risk, और 3% stop पर notional ≈ 1,333 USDT। यह गणित सही है। पर F7 का अपना pre-registered protocol stop पर **+1% slippage** मानता है (`logs/forward_ls_f4/F4_PROTOCOL_PREREGISTERED.md` L35)। 1,333 USDT पर यह ~13 USDT बनता है। Fees जोड़ें तो stop पर असली नुकसान **~53–54 USDT** है, 40 नहीं, यानी लगभग +33%। सही sizing नियम यह है: notional = risk ÷ (stop दूरी + stop slippage + round-trip cost) = 40 ÷ (3% + 1% + 0.085%) ≈ **979 USDT**। Demo पर stop slippage का असली वितरण मापे जाने तक F7 का 1% ही default रहेगा।

**Stop बनाम target वाले तर्क में median और mean मिल गए थे।** Part 2 (L361, L433) ने लिखा कि structural stop ~3–3.5 ATR दूर है और बचा हुआ इनाम "आम तौर पर" ~2 ATR। गणित सही है: 3/(3+2) से break-even hit rate 60% और 3.5/5.5 से 64% आती है। पर "~2 ATR" एक median-जैसा "आम" मान है। Swing Anatomy की top-down तालिका में बची हुई चाल का **conditional mean 2.98–3.81 ATR** है (`REPORT_SWING_ANATOMY_PHASE1_15_OCT_2026.md` L105–108)। यानी वितरण दाईं ओर झुका है, और edge उसी tail में है। 2 ATR का fixed target वही tail छोड़ देता है। इसलिए **tail पकड़ने के लिए trailing को प्राथमिकता** मिलेगी। Grid में बिना fixed TP वाले trailing-only variants अनिवार्य होंगे, और fixed 2 ATR TP सिर्फ़ तुलना के लिए रहेगा। "लगभग 3 ATR" (L433) को "3–3.5 ATR" लिखा जाए।

**Base rate की ग़लत व्याख्या:** "~0.75" (L397) unconditional है। उसका मतलब है कि बिना किसी stop के, किसी भी समय +1 ATR और चलने की संभावना 75–78% है। यह "**stop से पहले** +1 ATR" की base rate नहीं है। Stop k ATR पर हो तो first-passage rate इससे कम होगी। Project की किसी file में यह मान नहीं है, इसलिए इसे एक pre-registered माप के रूप में निकालना होगा, और meta-label brain उसी मापी गई दर के ख़िलाफ़ तौला जाएगा।

### बढ़ा-चढ़ाकर दिए गए citations और सुलझे सवाल

| दावा (मूल जगह) | स्थिति | सुधार |
|---|---|---|
| Shu, Yu & Mulvey: "plain HMM साल में ~8.5 बार switch करता है", "J. Asset Mgmt", और "regime-switching का OOS सबूत सबसे कमज़ोर" (L3, L23, L39) | PARTLY | 8.5×/yr Table 3 से है: unsmoothed HMM, 1982–2023। यह Table 4 वाली HMM strategy की switch rate नहीं है। arXiv पर कोई venue नहीं दिखा। सबसे अहम: **उसी paper में persistent Jump Model ने buy-and-hold को CAGR, Sharpe और MDD तीनों पर हराया** (Sharpe 0.68 बनाम 0.48), और HMM ने भी MDD आधा किया। सही वाक्य: "**hard, non-persistent** switching का सबूत सबसे कमज़ोर है" ([arXiv 2402.05272v3](https://arxiv.org/html/2402.05272v3)) |
| Lopez-Lira, Tang & Zhu: "सिर्फ़ 2010 से पहले का data इस्तेमाल करो" कहने से कोई फ़र्क नहीं पड़ा (L35, L85) | PARTLY | 0.61% / 80.58% बनाम 16.87% / 45.70% सही है। पर "pre-2010" निर्देश वाला test **quarterly GDP पर** था, S&P पर नहीं। सही वाक्य: "cutoff निर्देशों पर look-ahead रोकने के लिए भरोसा नहीं किया जा सकता" ⚠ preprint ([arXiv 2504.14765v2](https://arxiv.org/html/2504.14765v2)) |
| Gu, Kelly & Xiu: सालाना refit (L79, L321) | उद्धरण सही, उपयोग ज़्यादा | उन्होंने सालाना refit compute cost और सालाना signal updates की वजह से किया। यह **मिसाल (precedent) है, monthly के ख़िलाफ़ सबूत नहीं** ([NBER w25398](https://www.nber.org/papers/w25398.pdf)) |
| Blind Spot Paradox (L327) | VERIFIED, सुधार के साथ | 98.6% post-drift error ARF के **बचे हुए trees** सोखते हैं, पूरा forest नहीं। "1 drift पर 86 alarms" INSECTS **sensor** stream पर है। सिर्फ़ ProteuS streams simulated वित्तीय data हैं ⚠ preprint ([arXiv 2610.05853](https://arxiv.org/abs/2610.05853)) |
| FINSABER: "B&H ने 3/4 stocks पर हराया", "FinMem alpha हर scenario में नकारात्मक" (L35, L85) | PARTLY | KDD 2026 D&B (Oral), "दो दशक, 100+ symbols", "LLM advantages deteriorate significantly" verify हुए। 3/4 और "हर scenario" वाले आँकड़े abstract स्तर पर नहीं मिले। v6 (26 Jun 2026) cite करें ([arXiv 2505.07078](https://arxiv.org/abs/2505.07078)) |
| Alpha Arena: "एकमात्र live crypto LLM प्रतियोगिता", "42–59% खोया" (L85) | PARTLY / विरोधाभासी | "एकमात्र" हटाएँ। यह **Hyperliquid perps** पर चली, Binance पर नहीं। एक स्रोत GPT-5 को ~$3,733 यानी **~−63%** पर रखता है, जो 42–59% की range से बाहर है ⚠ media ([gncrypto.news](https://www.gncrypto.news/ru/news/qwen-wins-alpha-arena-season-1-with-22-percent-returns/)) |
| Lo & Remorov 2017 (L347) | ग़लत link | Handle 1721.1/107017 Remorov की **2016 PhD thesis** है, JFM 2017 का लेख नहीं। "Tight stops trading costs की वजह से B&H से पीछे" वाली बात thesis abstract में है। "Wide stops बेहतर" सिर्फ़ CXO summary से है ([MIT dspace](https://dspace.mit.edu/handle/1721.1/107017)) |
| Osler "JIMF 2005" (L355) | सामग्री सही, venue unconfirmed | Cascades और round numbers के पार stop clustering verify हुए ([NY Fed SR150](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf)) |
| DeMiguel et al. 2009 (L41, ⚠ "prior knowledge") | VERIFIED | ⚠ हटाया जा सकता है: "14 models… none is consistently better than the 1/N rule" ([IDEAS](https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html)) |
| Legacy futures WS URLs बंद हुए या नहीं (L427, "अज्ञात") | **सुलझा** | 2026-04-02 की entry के अनुसार 2026-04-23 को decommission हुए ([Derivatives change log](https://developers.binance.com/docs/derivatives/change-log))। अज्ञात सूची से हटाएँ |
| USDT-M user stream "`/private` route पर" (L217, L265) | NOT CONFIRMED | User-data-streams page पर `/private` का ज़िक्र नहीं है ([USDⓈ-M User Data Streams](https://developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams))। ⚠ लगाएँ या WS Connect page cite करें |
| Spot का replacement "`userDataStream.subscribe.signature`" (L265) | PARTLY | Changelog WS-API user-data subscription की ओर इशारा करता है। सही वाक्य: "`userDataStream.subscribe` (या `.subscribe.signature`)" |
| Fed SR 26-2 ने OCC 2011-12 को भी supersede किया (L81) | आंशिक | SR 11-7 का supersession verify हुआ। OCC वाला हिस्सा Fed pages पर नहीं लिखा, और KPMG स्रोत NOT CHECKED रहा |

### दस्तावेज़ के अंदरूनी विरोधाभास

Part 1 का "**User से तीन निर्णय चाहिए**" खंड (L180–186) और चरण 0 (L163) **अब superseded हैं**। User ने Part 2 में जवाब दे दिए थे: stops अपने-आप लगेंगे, capital 10,000 USDT (80/20) है, और सारे TFs पर काम होगा, 4H से शुरू करके। Part 1 के उस खंड पर यह नोट लगना चाहिए।

**F7 का वर्णन दो तरह से हुआ।** Part 1 (L3, L184) ने उसे "exchange stop entry ×1.5" कहा। Pre-registered protocol में F7 एक **short-side** stop है: entry ×1.50, simulation में हर bar पर जाँचा गया, +1% slippage और 30-दिन cooldown के साथ। किसी स्रोत में वह exchange पर रखा order नहीं है। Part 2 का "short stop entry ×1.5" (L203) सही है। Part 2 (L353) में F7 को exchange पर रखे catastrophe stop में बदलना एक **नया design** है, "F7 जैसा है वैसा" नहीं, और इसे इसी नाम से दर्ज किया जाए।

**Trial budget पर दो संख्याएँ थीं:** ~20–25 (Part 1 L165; `RESEARCH_4H` L92) और ~16–20 (`RESEARCH_4H` L130)। इस भाग का फ़ैसला: **4H Phase A के लिए एक ही budget, 20 trials।** इसमें असफल trials, AI-exit trial और stop/exit grid के हर variant-परिवार गिने जाएँगे। 20 पूरे होने पर नया trial तभी होगा जब user नया budget मंज़ूर करे, और DSR/PBO हमेशा कुल गिनती पर चलेंगे।

**30m, 8h और 12h बिना कारण हटाए गए थे** (Part 1 L67/L186 में "30m हटाएँ", Part 2 में सिर्फ़ 7 TFs)। इस भाग में कारण दर्ज है। User की सूची सात TFs की है, और ये तीनों उसमें नहीं हैं। पर इनमें से दो कमज़ोर नहीं हैं। 8h और 12h का gross swing-following औसत +3.15% और +5.17% है, और 8h|1D top-down असर +0.76 ATR है (Swing Anatomy)। फ़ैसला यह है कि **तीनों "research candidates" रहें, sleeves नहीं।** कारण यह है कि पड़ोसी horizons आपस में बहुत correlated होते हैं: बाहरी अध्ययन में 0.81–0.90, और हमारे D1/H4/H1 में 0.89–0.95। ऐसा हर नया sleeve diversification के बिना trials बढ़ाता है। 8h/12h की swing-स्थिति 4h model में context feature के रूप में परखी जा सकती है। 30m की 15m और 1h के बीच कोई अलग भूमिका नहीं दिखी।

**छोटी बातें:** "55–64% trades हारते हैं" को 55–63% लिखा जाए, क्योंकि जीत का हिस्सा 37–45% है। L77 का "ऊपर बताया गया 1h R4" पहले कहीं नहीं आया था, उसे ठीक करें। "2017–2020 और 2021–2026 दोनों में skill" वाले gate (L167, L409) में दो बदलाव चाहिए: 2017–2020 सिर्फ़ spot-direction labels पर संभव है, क्योंकि perp/funding data ~2020 से है, और 2021–2026 अब seen अवधि को छूता है। नया रूप नीचे की योजना में है।

**इनमें से कोई सुधार मुख्य सिफ़ारिश नहीं पलटता।** पर #1, #2, #4 और slippage वाला सुधार protocol lock से पहले लागू होने ज़रूरी हैं, क्योंकि ये gate, holdout और per-trade risk की संख्याएँ बदलते हैं।

---

## हर timeframe अलग चलता है: cost median चाल का 68% से 0.5% तक गिरता है

User की बुनियादी बात हमारे data में साफ़ दिखती है। 5m/15m और 1D/1W/1M सच में अलग तरह के बाज़ार हैं। नीचे की तालिका 8 coins (BTC, ETH, SOL, XRP, DOGE, LINK, AVAX, ADA) का median है। स्रोत `data/universe_hf` का 5m data है (left-closed, UTC पर resample), 2020-01 से 2026-09। Cost 0.085% perp taker round trip है, measured spread सहित।

| TF | Bars (प्रति coin) | Median candle body | Median high–low | Lag-1 autocorr (पूरा / 2024-10 से) | VR(4) | Cost ÷ median body |
|---|---|---|---|---|---|---|
| 5m | 709,458 | 0.12% | 0.29% | −0.027 / −0.008 | 0.947 | **68%** |
| 15m | 236,488 | 0.22% | 0.52% | −0.007 / −0.010 | 0.950 | **38%** |
| 1h | 59,129 | 0.43% | 1.09% | −0.025 / −0.013 | 0.940 | **20%** |
| 4h | 14,789 | 0.86% | 2.30% | −0.020 / +0.006 | 0.995 | **10%** |
| 1D | 2,465 | 2.33% | 6.16% | −0.053 / +0.000 | 0.942 | **3.7%** |
| 1W | 353 | 6.69% | 18.9% | +0.117 / +0.026 | **1.184** | **1.3%** |
| 1M | 81 | 16.7% | 49.0% | +0.057 / +0.090 | **1.243** | **0.5%** |

VR(4) = var(4-bar return) ÷ (4 × var(1-bar return))। 1 से ऊपर का मतलब trend, नीचे का mean reversion। Zero autocorrelation का ~95% iid band ±1.96/√N है: 5m पर ±0.002, 4h पर ±0.016, 1D पर ±0.039, 1W पर ±0.10 और 1M पर ±0.22। Crypto का volatility clustering यह band और चौड़ा करता है।

**तालिका तीन बातें कहती है।** पहली, **cost का बोझ लगभग √(bar length) के हिसाब से गिरता है।** BTC 5m पर cost ÷ median body 1.19 है, यानी एक round trip एक आम 5m candle की पूरी चाल से भी महँगा है। 1h→4h पर range 2.1× बढ़ती है और 4h→1D पर 2.7×, जो √4 = 2 और √6 ≈ 2.45 के क़रीब है। दूसरी, **5m से 1D तक हल्का mean reversion है** (VR 0.94–0.995)। 5m का ac1 −0.027 statistically असली है, क्योंकि band ±0.002 है। पर ac1² ≈ 0.0007 है, यानी return variance का एक प्रतिशत का दसवाँ हिस्सा भी नहीं। Taker के लिए इसका कोई पैसा नहीं बनता। तीसरी, **1W और 1M trend जैसे दिखते हैं** (VR 1.18 और 1.24), पर उनके bars बहुत कम हैं। 1W का ac1 +0.117 ±0.10 के band पर सिर्फ़ किनारे पर significant है। हाल की अवधि में वह +0.026 रह जाता है, और SOL, ADA, AVAX पर ऋणात्मक हो जाता है। 1M में XRP का VR 0.57 और LINK का 0.97 है। N = 81 पर इसे noise से अलग नहीं किया जा सकता।

**साहित्य से तुलना दिशा में मेल दिखाती है, ताक़त में नहीं।** Liu और Tsyvinski ने BTC 2011–2018 पर daily time-series momentum पाया: आज का return अगले 1–6 दिनों का अनुमान देता है (coefficient 0.06)। Weekly पर coefficients 1–4 हफ़्ते आगे के लिए 0.19/0.22/0.21/0.09 थे, पर bootstrap में 4-हफ़्ते वाला significant नहीं रहा ([Liu & Tsyvinski, NBER w24877, 2018; RFS 2021](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf))। हमारा 2020–2026 का daily ac1 −0.053 उल्टे चिह्न का है, और हाल में ~0 है। सबसे संभावित व्याख्या यह है कि शुरुआती, कम परिपक्व बाज़ार का daily momentum derivatives-भारी बाज़ार में नहीं टिका, पर यह हमारा अनुमान है, उनके specification पर परखा नहीं गया। Weekly पर दोनों मेल खाते हैं। Cross-sectional momentum 1–4 हफ़्ते की lookback पर 2.5–4.1% प्रति हफ़्ता कमाता है, और 8 हफ़्ते या ज़्यादा पर असफल होता है ([Liu, Tsyvinski & Wu, J. Finance 2022, WP PDF](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf))। Dobrynskaya के अनुसार ~4 हफ़्ते के बाद reversal आता है ⚠ secondary ([HSE](https://www.hse.ru/en/news/research/559533243.html)), जो हमारे 1M "trend" को और संदिग्ध बनाता है। Intraday पर momentum और reversal दोनों दर्ज हैं, और jumps, FOMC दिनों और liquidity के साथ बदलते हैं ⚠ abstract ([Wen et al., NAJEF 2022](https://ideas.repec.org/a/eee/ecofin/v62y2022ics1062940822000833.html))। Short-term reversal मुख्यतः liquidity provision का premium है, जो छोटे, कम liquid pairs में केंद्रित है ⚠ abstract ([Bianchi, Babiak & Dickerson, JBF 2022](https://ideas.repec.org/a/eee/jbfina/v142y2022ics0378426622001418.html))। इसे taker नहीं पकड़ सकता। 183 Binance pairs पर 15-मिनट reversal ~90% pairs में था, पर gross edge का शिखर ~1.3 bp था, जबकि round trip ~5 bp ⚠ preprint ([Kitron & Wengrowicz 2026](https://arxiv.org/abs/2608.21888))।

**एक बारीकी जो design को सीधे प्रभावित करती है:** 1W का अपना trend (VR 1.18) और 1W का **context** असर अलग सवाल हैं। Swing Anatomy में 4h/1h के swings पर 1W की हालत का कोई साफ़ असर नहीं मिला, और 1M का असर उल्टा था (−0.3 से −0.7 ATR)। इसलिए 1W अपने horizon पर trend sleeve का उम्मीदवार हो सकता है, पर छोटे TFs के लिए gate या filter नहीं।

Intraday volatility का ढाँचा भी stops को प्रभावित करता है। UTC दिन का पहला घंटा और 16:00 UTC के बाद का घंटा सबसे volatile होते हैं, weekends (ख़ासकर शनिवार) शांत होते हैं, और हर घंटे के पहले मिनट में और :15/:30/:45 पर bursts आते हैं ⚠ preprint ([Hansen, Kim & Kimbrough, arXiv 2109.12142](https://arxiv.org/pdf/2109.12142))। Calendar return effects समय के साथ स्थिर नहीं रहे ⚠ abstract ([Baur et al., UWA](https://research-repository.uwa.edu.au/en/publications/bitcoin-time-of-day-day-of-week-and-month-of-year-effects-in-retu/))। इसका नतीजा यह है कि 5m–1h पर fixed-% stop दिन भर ग़लत calibrated रहेगा। Stop उसी TF के ATR में होना चाहिए, और calendar return strategies पर भरोसा नहीं करना चाहिए।

---

## सात timeframes, तीन भूमिकाएँ: execution, alpha और context

ऊपर के आँकड़े, हमारी Swing Anatomy और साहित्य मिलकर हर timeframe को तीन में से एक भूमिका देते हैं। **Execution** (order का सही पल) 5m और 15m के लिए है। **Alpha** (trade का फ़ैसला) 1h, 4h और 1D के लिए है, जिसमें शुरुआत 4h से होगी। **Context** (size का झुकाव) 1W और 1M के लिए है। 1W बाद में trend sleeve भी बन सकता है।

| TF | भूमिका | उपयुक्त strategy परिवार और सबूत | AI alpha brain: अभी या बाद में (gate) |
|---|---|---|---|
| **5m** | Execution: post-only entry, fill की गुणवत्ता, stop/fill का intrabar simulation | Market making/liquidity provision maker side पर है, जिसके लिए queue priority और latency चाहिए, जो हमारे पास नहीं। Cost/move 68%। Swing-following gross +0.02% (maker cost से नीचे) | **कभी नहीं, मौजूदा costs पर।** इसका metric AUC नहीं, implementation shortfall है |
| **15m** | Execution और 4h फ़ैसले के भीतर entry timing | 15m reversal असली है पर ~1.3 bp बनाम 5 bp ⚠। Gross +0.05% ≈ maker cost। 15m/5m features ने AUC में +0.0008 जोड़ा (`REPORT_HF_STEP25_14_OCT_2026.md`) | **नहीं।** अलग sleeve सिर्फ़ maker-only research के रूप में, और तभी जब costs के बाद gross edge साबित हो |
| **1h** | दूसरा alpha (4h के बाद) | Gross +0.33% ≈ 3.9× taker, पर median −0.67 ATR। R24 ranking AUC 0.565, R4 0.545 (`AUDIT_FULL_BRAINS_AND_CODE_16_OCT_2026.md`; `REPORT_1H_STEP24_14_OCT_2026.md`)। Intraday momentum/reversal ⚠ in-sample | **बाद में (Phase B)।** 4h वाले pooled fast-swing brain में, TF को feature बनाकर। Gate: 4h sleeve के साथ combined Calmar बढ़े, और 4h से OOS correlation < 0.5 हो, तभी अलग brain |
| **4h** | **पहला alpha sleeve** | Gross +1.61% ≈ 19× taker, median −0.55 ATR, जीत 41%। VR ≈ 1.0, यानी persistence अपने-आप edge नहीं देती, edge **चुनाव** से आना होगा (कौन-सा confirmed swing बड़ा बनेगा)। 4H R6 ranking AUC 0.568 | **अभी (Phase A):** meta-label entry brain। Gates नीचे की योजना में |
| **1D** | धीमा alpha (मौजूदा 1D system) + context | Cost/move 3.7%। Donchian-ensemble trend-following का Sharpe > 1.5, fees के बाद ⚠ preprint, सिर्फ़ summary ([Zarattini, Pagani & Barbon 2025, SFI RP 25-80](https://ideas.repec.org/p/chf/rpseri/rp2580.html))। Gross +10.95% पर median −0.42 ATR। D1 AUC 0.559 | **मौजूदा 1D system अलग और अछूता रहेगा।** नया 1D sleeve सिर्फ़ user के निर्णय पर, वही gates |
| **1W** | Context feature; बाद में trend sleeve | Weekly TSMOM 1–4 हफ़्ते, XS momentum 1–4 हफ़्ते (RFS/JF, पर 2011–2018 sample); हमारा VR 1.18 सिर्फ़ किनारे पर। 4h/1h के लिए context असर साफ़ नहीं | **अभी नहीं।** पहले नियम-आधारित weekly TSMOM benchmark (spot long-only पर विचार)। AI तभी जब pooled weekly events shuffled-control gate को पर्याप्त power दें |
| **1M** | सिर्फ़ context feature | N = 81। 4–8 हफ़्ते के बाद reversal। BTC के सिर्फ़ 4 halvings, यानी 3–4 स्वतंत्र cycle observations। 1M का top-down असर उल्टा | **नहीं।** Feature के रूप में भी तभी जब उसका OOS योगदान साबित हो |

### Holding, stops, targets और time stops: उसी TF के ATR और bars में

**Scaling का सिद्धांत Swing Anatomy से आता है: swings हर timeframe पर self-similar हैं** (आम swing ~5 ATR, confirmation तक ~57% पूरा)। इसलिए **ATR इकाइयों में एक ही grid सभी timeframes पर लागू हो सकता है।** बदलता है सिर्फ़ ATR का % आकार (√समय के साथ) और cost का हिस्सा। Time stop को bars में रखना चाहिए, और उसकी लंबाई उस horizon से बँधी होनी चाहिए जिस पर साहित्य predictability पाता है। नीचे के ATR proxy आँकड़े ऊपर की median high–low से हैं। असली ATR(14) इनसे थोड़ा ऊपर होगा। Grid हमारा प्रस्ताव है।

| TF | ATR proxy (median H–L) | 0.085% cost = कितने ATR | Typical hold (प्रस्ताव) | Initial stop grid (उसी TF का ATR) | Target / trailing | Time stop grid (bars) |
|---|---|---|---|---|---|---|
| 5m | 0.29% | 0.29 ATR | — (execution window मिनटों में) | Sleeve stop नहीं; parent sleeve का stop लागू | — | Execution window ≤ 12 bars (1 घंटा), फिर taker fallback |
| 15m | 0.52% | 0.16 ATR | — | वही | — | Window ≤ 4 bars (1 घंटा) |
| 1h | 1.09% | 0.08 ATR | घंटों से ~1–2 दिन | k ∈ {1.5, 2, 2.5, 3} + structural (pivot + buffer) | Trailing-only (chandelier m ∈ {2, 3}) बनाम fixed 2 ATR | {12, 24, 48} |
| 4h | 2.30% | 0.04 ATR | ~1–5 दिन | वही grid; structural ≈ 3–3.5 ATR | वही | {6, 12, 18} (1–3 दिन) |
| 1D | 6.16% | 0.014 ATR | दिनों से हफ़्तों तक | वही; shorts पर F7 (entry ×1.5, +1% slippage, 30-दिन cooldown) बाहरी परत | Trailing को प्राथमिकता (trend ensemble) | {5, 10, 20} (daily TSMOM 1–6 दिन; trend कई हफ़्ते) |
| 1W | 18.9% | ~0.005 ATR | 1–4 हफ़्ते | Catastrophe + k ∈ {1.5, 2} | Trailing | {1, 2, 4} (4 हफ़्ते के बाद reversal zone) |
| 1M | 49% | ~0.002 ATR | — | — | — | — |

**Exit की गति पर दो सबूत टकराते हैं, और grid इसी टकराव को परखने के लिए है।** एक तरफ़ 5m–1D का VR 1 से नीचे है, जो कहता है कि छोटे timeframes पर trend टिकते नहीं, इसलिए जल्दी निकलना चाहिए। दूसरी तरफ़ Swing Anatomy कहती है कि हर timeframe पर कमाई tail से आती है (mean positive, median negative, conditional mean 3.0–3.8 ATR)। इसका मतलब है कि fixed target tail काट देता है। हमारा तर्क यह है कि 1h/4h पर trailing-only और fixed-TP दोनों variants एक ही grid में चलें, walk-forward OOS में, costs और slippage के बाद। चुनाव किसी अकेले peak से नहीं, **plateau** से होगा। 1W पर, जहाँ VR > 1 है, trailing का पक्ष पहले से मज़बूत है।

**Stops के तीन स्तर Part 2 जैसे ही रहेंगे**, बस हर TF के ATR में। सबसे बाहर exchange पर रखा catastrophe stop होगा (`STOP_MARKET`, `workingType=MARK_PRICE`)। उसके अंदर बाज़ार-जागरूक initial stop होगा (swing pivot के पार ATR buffer, और round numbers से दूर; round numbers के पार stop cascades का सबूत ([Osler, NY Fed SR150](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf)) से है)। सबसे अंदर trailing और time stop होंगे। Volatility regime (ATR percentile) multiple को सिर्फ़ pre-registered [न्यूनतम, अधिकतम] दायरे में बदल सकता है। F7 1D shorts पर जैसा है वैसा रहेगा। 4H पर F7 का सिद्धांत (चौड़ी बाहरी परत, cooldown) अपनाया जाएगा, पर उसकी दूरी protocol में अलग से तय होगी। Risk हमेशा "stop दूरी + 1% slippage + cost" पर गिना जाएगा।

---

## कम brains, कम correlation: तीन AI brains और तीन नियम-परतें

**Brains की गिनती छोटी रखने का सबूत चार दिशाओं से एक जैसा है।** पहला, **forecast combination puzzle:** जब असली optimal weights लगभग बराबर हों, तो estimated weights सीधे औसत से हारते हैं, क्योंकि weights का अनुमान variance जोड़ता है ([Smith & Wallis 2009, चर्चा arXiv 1505.00475 में](https://arxiv.org/pdf/1505.00475); [Elliott, UCSD](https://econweb.ucsd.edu/~gelliott/Combination.pdf))। दूसरा, **forecasting competitions:** M4 में शीर्ष दोनों तरीक़ों ने कई series पर एक साथ trained global models इस्तेमाल किए, और M5 (42,840 Walmart series) का विजेता LightGBM models का **equal-weight** ensemble था ([Makridakis et al., IJF 2022](https://ideas.repec.org/a/eee/intfor/v38y2022i4p1346-1364.html); [Bojer & Meldgaard, IJF review, arXiv 2009.07701](https://arxiv.org/abs/2009.07701v1))। इसका सबक है कि coins पर pooling करें, horizons पर अलग-अलग brains न बढ़ाएँ। तीसरा, **speed blending सिर्फ़ तभी diversify करता है जब speeds कम correlated हों।** Man AHL में सबसे तेज़ और सबसे धीमे trend speeds का correlation 0.17 है, और speeds इसी को कम करने के लिए चुनी गईं ⚠ vendor ([Man Group 2023](https://www.man.com/insights/need-for-speed-trend-following))। Ai For Alpha के futures अध्ययन में पड़ोसी horizons 0.81–0.90 correlated थे, 125-दिन वाली बीच की परत "largely overlaps", और 2013–2025 में equal weight (Sharpe 0.79) ने optimized weights (0.72) को हराया ⚠ preprint, एक ही vendor समूह ([Etienne et al., arXiv 2510.23150](https://arxiv.org/html/2510.23150v2))। हमारे D1/H4/H1 brains के returns 0.89–0.95 correlated हैं (`REPORT_COMBINED_STEP27_15_OCT_2026.md`), यानी वे लगभग एक ही दाँव हैं। चौथा, **high-frequency data की जानकारी summary में आ जाती है।** MIDAS में 5-मिनट returns से बना daily realized power सबसे अच्छा volatility predictor था, और raw 5-मिनट data सीधे देने से कोई सुधार नहीं हुआ ([Ghysels, Santa-Clara & Valkanov, J. Econometrics 2006, NBER w10914](https://www.nber.org/papers/w10914))। हमारा +0.0008 AUC ठीक यही कहता है। इन सबके ऊपर हमारा अपना नियम भी है: हर नया brain एक नया trial है, जिसे shuffled control के ख़िलाफ़ skill gate पास करना होगा।

**Learned hierarchy का कोई cost-सहित OOS सबूत नहीं मिला।** Hierarchical RL papers (HRPM, HRT) अपने निचले, तेज़ policy को "trading cost घटाने" के लिए रखते हैं, और flat equal-weight ensemble से साफ़ तुलना नहीं दिखाते ⚠ ([HRPM, AAAI 2021, arXiv 2012.12620](https://arxiv.org/abs/2012.12620))। यह एक अलग execution परत का समर्थन करता है, ज़्यादा alpha brains का नहीं।

### अंतिम ढाँचा

| # | Component | प्रकार | Timeframe/input | Output | कब live |
|---|---|---|---|---|---|
| **B1** | **Context/regime brain** | AI (पहले नियम-आधारित null) | 1D close पर, 1D/1W/1M के HAR-शैली summaries (vol level, trend strength, BTC दिशा, persistence) | सिर्फ़ **risk multiplier** (Phase A में 0.5–1.0, यानी सिर्फ़ घटाने वाला; gate के बाद equal weight के आसपास ±20%)। कभी दिशा नहीं, कभी veto नहीं | शुरू में नियम (vol-target + trend overlay)। Learned संस्करण एक अलग trial है, क्योंकि हमारा market-out brain (AUC 0.523, CI 0.494 छूती) असफल रहा था |
| **B2** | **Alpha / meta-label brain, horizon family के हिसाब से** | AI | B2-fast: 4h (बाद में 1h उसी pooled model में)। B2-slow: 1D (मौजूदा system, अलग)। B2-weekly: बाद में, पहले नियम | Primary signal नियम से (confirmed swing + next-HTF हालत + volume spike), brain तय करे take/skip और दिशा, साथ में calibrated probability | B2-fast: Phase A। अलग family तभी जब OOS correlation < 0.5 (barbell) |
| **B3** | **Size function** | Calibrated mapping (learned weights नहीं) | B2 की p_cal, B1 का multiplier, next-HTF agreement | Risk = base × f(p_cal) × B1 × HTF tilt, ¼–½ Kelly cap के भीतर | B2 के साथ। Calibration fixed sizing को सुधारता है, पर learned sizing का फ़ायदा साबित नहीं ⚠ (meta-labeling series, secondary) |
| **L4** | **Risk और stops engine** | नियम (learned नहीं) | सब sleeves | Per-trade risk (slippage सहित), gross/net/per-coin caps, तीन-परत stops, DD de-risking, cooldown | हमेशा। इसके पास veto है |
| **L5** | **Execution layer** | नियम; बाद में optimizer | 5m/15m bars, order book | Bounded window में entry का समय और order type | हमेशा। Metric: implementation shortfall बनाम decision price |
| **L6** | **Monitor / kill-switch** | Infrastructure | Frozen champion की errors, feature drift, bar-age, reconcile diff, realized cost | Alarm, size घटाना, halt | हमेशा। **सिर्फ़ risk घटा सकता है** |

**तो जवाब है: अभी live में एक AI brain (B2-fast, 4h), और अंत में अधिकतम चार learned हिस्से** (B1, B2-fast, B2-slow, B2-weekly), साथ में तीन नियम-परतें। B3 एक calibrated function है, स्वतंत्र दिमाग नहीं। 4H phase में primary signal नियम है, इसलिए वहाँ "alpha brain" और "meta-label brain" एक ही model हैं। B3 को अलग learned brain तभी बनाया जाएगा जब कभी B2 ख़ुद learned primary हो और meta-label उसके ऊपर gate पास करे।

---

## तेज़ और धीमे फ़ैसलों का sync: बड़ा TF size तय करे, छोटा TF सिर्फ़ समय

```
 BINANCE kline events (x=true, open time t से dedupe) — क्रम जब कई TF एक साथ बंद हों:
 1M → 1W → 1D → 4h → 1h → 15m → 5m   (exchange की t/T पर, local घड़ी पर नहीं)
                 │
                 ▼
 ┌──────────── POINT-IN-TIME STORE (event_time + available_at = open_time + interval + latency) ───────────┐
 │ join = merge_asof(direction="backward", by="symbol") on available_at; assert max(available_at) ≤ decision │
 └───────┬──────────────────────────────┬───────────────────────────────────┬──────────────────────────────┘
         ▼ SLOW (1D close, दिन में 1)     ▼ FAST-SWING (4h; बाद में 1h)        ▼ EXECUTION (5m/15m, हर bar)
 ┌──────────────────────────┐   ┌──────────────────────────────────┐   ┌─────────────────────────────────┐
 │ [B1] Context brain        │   │ [B2-fast] meta-label brain        │   │ [L5] Execution layer             │
 │ 1D/1W/1M HAR summaries    │──►│ अपना TF + next-HTF का CLOSED bar   │   │ input: sleeve का नया target       │
 │ out: risk multiplier m    │   │ + m (feature के रूप में)            │   │ window ≤ 1 घंटा: post-only →      │
 │ (tilt; न दिशा, न veto)    │   │ out: take/skip, दिशा, p_cal        │   │ taker fallback; दिशा/size कभी नहीं │
 │ [B2-slow] 1D system:      │   │ [B3] risk = base·f(p_cal)·m·tilt  │   │ metric: implementation shortfall  │
 │ अलग account, अछूता         │   │ exit plan: ATR(अपना TF) stops      │   └───────────────┬─────────────────┘
 └────────────┬─────────────┘   └────────────────┬─────────────────┘                   │
              └────────────── SLEEVE VIRTUAL POSITIONS (हर TF का target + exit plan) ──┘
                                                 ▼
 ┌──────── COORDINATOR ────────────────────────────────────────────────────────────────────────────┐
 │ net_target[coin] = Σ sleeves · same दिशा → जोड़ो (per-coin cap तक)                                │
 │ उलटी दिशा → छोटा TF सिर्फ़ net घटा सकता है, नई उलटी position नहीं · per-sleeve P&L attribution     │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                                ▼
 ┌──────── [L4] RISK & STOPS ENGINE (नियम, veto) ─────────────────────────────────────────────────┐
 │ risk = stop + 1% slippage + cost · gross cap (corr=1 मानकर) · net beta · DD de-risk · cooldown   │
 │ catastrophe stop (exchange, MARK_PRICE) · initial (swing+ATR) · trailing/time stop (अपने TF में) │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                               ▼
 EXECUTION → Binance (one-way, अलग sub-account; algoOrder STOP_MARKET; पहले नया stop, फिर पुराना cancel)
                                               ▼
 LEDGER (hash-chained) → time stop के बाद label → तय समय पर retrain → challenger SHADOW → gate → MANUAL promote
 [L6] MONITOR: frozen model पर drift · bar-age · reconcile diff · realized cost → सिर्फ़ size घटाना/halt
```

**घड़ी:** हर sleeve अपने TF के bar-close event पर जागता है। Exchange की `t`/`T` मानी जाएगी, local घड़ी नहीं। 00:00 UTC जैसे पल पर 4h, 1D और कभी 1W/1M एक साथ बंद होते हैं। तब क्रम तय रहेगा: पहले बड़े TF का bar store में `available_at` के साथ लिखा जाएगा, फिर छोटे TF का फ़ैसला चलेगा। फ़ैसला सिर्फ़ वही देखेगा जिसका `available_at` ≤ decision time है। यह determinism इसलिए ज़रूरी है ताकि backtest replay और live byte-identical रहें। Partial HTF bar कभी इस्तेमाल नहीं होगा। "आज का अब तक का high" चाहिए तो वह छोटे bars से causal तरीके से बनेगा और उसका नाम अलग होगा। Project का नियम `df["asof"]` लिखने का है, `.asof` नहीं।

**बड़ा TF tilt देता है, veto नहीं, और इसका कारण हमारे data में है।** अगला बड़ा TF साथ हो तो बची हुई चाल का **mean** 0.47–0.76 ATR बढ़ता है, पर "≥1 ATR और" की संभावना ~76–78% पर लगभग वही रहती है। यानी HTF agreement छोटे trade को अच्छा या बुरा नहीं बनाता, बस tail बड़ी करता है। Veto ऐसे trades फेंक देगा जिनकी hit rate उतनी ही है। Tilt उन्हें रखता है और size बदलता है। इसलिए HTF की हालत (1) B2 में feature के रूप में जाती है और (2) B3 में size multiplier के रूप में। दोनों रूप pre-registered होंगे, और उनमें से सिर्फ़ एक "बेहतर" को बाद में चुना नहीं जाएगा। 1W/1M gate कभी नहीं बनेंगे, क्योंकि 1W का असर साफ़ नहीं और 1M का उल्टा है।

**तेज़ और धीमे के बीच औपचारिक नियम Gârleanu–Pedersen से आता है।** Optimal policy एक "aim portfolio" की ओर आंशिक रूप से trade करती है। धीरे क्षय होने वाले signals को ज़्यादा weight मिलता है, क्योंकि वे "अभी और भविष्य दोनों में अनुकूल positioning" देते हैं ([Gârleanu & Pedersen, JF 2013, NBER w15205](https://www.nber.org/papers/w15205))। हमारे लिए इसका रूप यह है: **धीमा signal target और risk budget तय करता है, और तेज़ परत सिर्फ़ चाल की गति और समय तय करती है।** Execution साहित्य में भी तेज़ परत का काम slow signal के alpha decay को देखते हुए implementation shortfall घटाना है ([Almgren–Chriss/alpha profiling, Wikipedia summary](https://en.wikipedia.org/wiki/Alpha_Profiling) ⚠ secondary; [Lehalle & Neuman, Finance & Stochastics, arXiv 1704.00847](https://ar5iv.arxiv.org/html/1704.00847))। Execution window bounded है, जैसे 4h फ़ैसले के बाद अधिकतम 1 घंटा। Window ख़त्म होते ही taker order जाता है, ताकि तेज़ परत किसी धीमे signal पर अनिश्चित समय तक न बैठी रहे। Null benchmark "decision bar close पर तुरंत taker" है, और L5 को उसे implementation shortfall में हराना होगा। वरना सरल null ही चलेगा।

**Conflict नियम पहले से लिखे हैं, ताकि live में कोई "समझदारी" न करनी पड़े।**

| स्थिति | फ़ैसला |
|---|---|
| एक coin पर एक ही sleeve सक्रिय (पूरा Phase A) | Conflict नहीं। Sleeve का stop सीधे exchange पर `reduceOnly` STOP_MARKET |
| दो sleeves एक ही दिशा में (4h long, 1h long) | Net = जोड़, per-coin cap तक। हर sleeve का अपना `reduceOnly` stop उसकी मात्रा के बराबर |
| छोटा TF बड़े TF के ख़िलाफ़ (4h long, 1h short) | 1h सिर्फ़ net long **घटा** सकता है, नई short position नहीं खोल सकता। 1h का stop virtual रहेगा, engine उसे mark price पर लागू करेगा, और exchange पर net position का catastrophe stop backup रहेगा |
| बड़ा TF छोटे के ख़िलाफ़ नया signal दे | बड़ा TF नया target तय करता है। छोटे sleeve की virtual position उसके अपने exit नियम से बंद होगी |
| B1 risk-off (m घटा) | सभी sleeves का नया risk घटता है। खुली positions पर नए stops नहीं कसे जाते (pre-registered) |
| Monitor alarm, data staleness या DD सीमा | Size घटाना या halt, reduce-only। Size कभी अपने-आप नहीं बढ़ता |

यह "सिर्फ़ घटा सकता है" नियम सूचना फेंकता है, पर netting के virtual stops का जोखिम बहुत सीमित कर देता है। Hedge mode एक pre-registered विकल्प है, जिसे तभी परखा जाएगा जब यह नियम भारी पड़ता दिखे। Position mode account-wide है, इसलिए यह चुनाव live से पहले एक बार होगा।

---

## Scanning हर bar पर, सीखना तय समय पर: timeframe-वार learning loop

"लगातार सीखने वाला AI" का ईमानदार रूप Part 2 जैसा ही है, पर अब हर timeframe के हिसाब से। Scan, record और monitor हर बंद candle पर अपने-आप चलते हैं। Model तय समय पर offline retrain होता है, नया model challenger बनकर shadow में चलता है, और promotion manual होता है। एक सुधार यहाँ भी लागू है। Gu–Kelly–Xiu का सालाना refit सिर्फ़ एक मिसाल है, monthly के ख़िलाफ़ सबूत नहीं ([NBER w25398](https://www.nber.org/papers/w25398.pdf))। इसलिए cadence हमारी अपनी "staleness curve" से तय होगी: अलग-अलग उम्र के models को एक ही OOS अवधि पर चलाकर देखा जाएगा कि edge कितनी तेज़ी से घटता है। Window averaging (1y/2y/3y/expanding) का सहारा Pesaran और Pick का निष्कर्ष है कि कई windows का औसत छोटे breaks को छोड़कर हर स्थिति में कम bias और कम RMSFE देता है ([CESifo WP 2293](https://www.ifo.de/DocDL/cesifo1_wp2293.pdf))। ध्यान रहे कि उनका सिद्धांत breaks वाली random walks पर है और empirical test OECD inflation पर, asset returns पर नहीं। इसलिए यह भी एक trial है।

| TF | Scan (bar close) | Label देरी ≈ time stop | Retrain cadence (प्रस्ताव) | Drift monitor (frozen champion पर) | Shadow/promotion |
|---|---|---|---|---|---|
| 5m | 288/दिन | — | कोई alpha model नहीं। Execution parameters (window, post-only offset) ledger fills से मासिक review होंगे, नियम के रूप में | Fill rate, adverse selection, realized spread | Parameter बदलना भी trial है |
| 15m | 96/दिन | — | वही | वही | वही |
| 1h | 24/दिन | 12–48 bars | मासिक (B2-fast pooled), staleness curve से पुष्टि | ADWIN/KSWIN errors पर, feature PSI/KS (thresholds non-drift अवधियों के null से), Brier | ≥ 1 cycle shadow → gate → manual |
| 4h | 6/दिन | 6–18 bars | **मासिक**, purged/embargoed walk-forward, embargo ≥ time stop | वही, साथ में realized बनाम modeled cost | वही |
| 1D | 1/दिन | 5–20 bars | मौजूदा system की अपनी monthly cadence, अछूती। B1 context: तिमाही | वही | 1D system में कोई बदलाव नहीं |
| 1W | 1/हफ़्ता (boundary verify होनी है) | 1–4 bars | तिमाही या सालाना (बहुत कम events) | सिर्फ़ feature drift | — |
| 1M | 1/महीना | — | कोई model नहीं | — | — |

**Drift सिर्फ़ frozen model पर मापा जाएगा, ख़ुद बदलते model पर नहीं।** Blind Spot preprint में ARF के incremental updates ने post-drift error सोख लिया, और cumulative monitors (Page-Hinkley) ने 1,080 में से 0 shifts पकड़े, जबकि static RF पर F1 0.73–0.96 था ⚠ preprint ([arXiv 2610.05853](https://arxiv.org/abs/2610.05853))। Alarm के तीन ही नतीजे हो सकते हैं: (क) size घटाना, (ख) sleeve रोकना, (ग) तय समय से पहले retrain का प्रस्ताव, जो फिर shadow और gate से गुज़रेगा। **अपने-आप सिर्फ़ जोखिम घट सकता है।** Model बदलना, size बढ़ाना या नया sleeve शुरू करना gate, independent verifier और user की मंज़ूरी से ही होगा।

---

## संशोधित चरणबद्ध योजना: 4H पहले, साफ़ holdout अब forward data है

यह योजना Part 2 की A0–E को errata के साथ अद्यतन करती है। सारे thresholds प्रस्ताव हैं, जिन्हें protocol में SHA-lock करना होगा। हर दावे की जाँच independent verifier `claims.json` से करेगा। 1D cloud system पूरी अवधि में अछूता रहेगा।

| चरण | काम | Gate (निकास-शर्त) |
|---|---|---|
| **P0. Errata लागू करना** (अभी) | ऊपर के सभी सुधार मूल दस्तावेज़ में नोट के रूप में; Part 1 के "user निर्णय" खंड पर superseded का नोट; recorder आज से चालू (raw WS + REST, SHA chain) ताकि forward data दर्ज हो | सुधार-सूची verifier से मिलान |
| **A0. Protocol lock (4H)** | Data windows: dev/walk-forward 2021-01 से 2025-09 (perp); 2025-10 से 2026-09 "**seen**" (रिपोर्ट होगा, पर निर्णायक gate नहीं); 2018–19 frozen, सिर्फ़ spot-direction skill; **clean holdout = 2026-10-17 के बाद का forward data**। **Trial budget = 20** (एकमात्र संख्या)। Cost model: 0.085% (BNB) / 0.092% (बिना BNB) / ~0.10–0.11% (FAQ taker), stress 1×/1.5×/2×, spot 0.17%/0.22%। Risk = stop + 1% slippage + cost | Protocol SHA-lock; बाद का हर बदलाव नया trial |
| **A1. Pre-registered माप (बिना AI)** | First-passage दर P(+k ATR, −m ATR से पहले) 1h/4h पर; conditional mean बनाम median बची चाल; demo पर stop slippage का वितरण | माप verifier से दोहराए गए; ये meta-label का base rate बनेंगे |
| **A2. Knowledge base + ledger + trial registry** | PIT store, `available_at` ordering (coincident closes), decision ledger | Replay 100% मेल; leak canary performance उछाले; assertions पास |
| **A3. B2-fast (4h meta-label)** | Confirmed swing + next-HTF + volume features; monthly walk-forward, window-averaged बनाम single window; B1 = नियम-आधारित overlay | OOS skill shuffled control के 95th percentile से ऊपर; Brier A1 की base rate से बेहतर; 2018–19 spot-direction पर skill बनी रहे |
| **A4. Stops/exits grid** | Catastrophe-only; fixed ATR; structural; chandelier + time stop; **trailing-only** बनाम fixed 2 ATR TP; 5m intrabar fills, gap-through, 1% slippage | Costs के बाद plateau; DD घटे और net, catastrophe-only से बदतर न हो; random-entry control से बेहतर |
| **A5. Backtest + verifier** | Equal-weight + vol-target benchmark; असली funding; short filters | 1.5× cost पर net > 0 (बिना-BNB cost पर भी); DSR ≥ 0.95 पूरे trial count पर; PBO < 0.30; 1D से correlation ≤ 0.70 या combined Calmar बेहतर |
| **A6. AI-exit trial (वैकल्पिक, budget में गिना)** | Step 26 जैसा बड़ी-गिरावट brain 4h पर, नए pre-registration के साथ | Calmar और DD दोनों बेहतर, और **random exit control से बेहतर**। AUC अकेला gate नहीं |
| **A7. Engine + chaos (testnet/demo)** | Event-driven service, algoOrder stops, reconcile, kill-switch, sandbox pre-flight | Chaos matrix 100%; शून्य orphan या stop-less position; शून्य duplicate |
| **A8. Forward shadow = साफ़ holdout** | Protocol lock के बाद का mainnet data, कोई order नहीं (या सिर्फ़ demo) | पहले से तय न्यूनतम अवधि **और** closed trades की न्यूनतम गिनती; forward नतीजा backtest bootstrap के pre-registered निचले band से नीचे न जाए; realized cost ≤ 1.25× model; data/clock failure शून्य |
| **A9. Real money** | सिर्फ़ user का निर्णय; 8,000 USDT का छोटा हिस्सा पहले, अलग sub-account | User की स्पष्ट मंज़ूरी |
| **B. 1h** | B2-fast pooled model में TF feature के रूप में; netting नियम सक्रिय | 4h के साथ incremental value (combined Calmar); OOS correlation < 0.5 हो तभी अलग brain |
| **C. B1 learned context** | Rule overlay बनाम learned, persistent regime model | Rule null को DD/Calmar पर हराए, costs के बाद |
| **D. 1D sleeve** | मौजूदा system से अलग; user निर्णय | वही gates |
| **E. 1W** | पहले नियम-आधारित weekly TSMOM benchmark | वही gates। AI तभी जब events पर्याप्त हों |
| **F. 5m/15m execution optimizer** | Window/order-type के नियम | Implementation shortfall में "तुरंत taker" null को हराए |
| **G. 30m/8h/12h** | Research candidates; पहले features के रूप में (8h/12h context) | Feature का OOS योगदान साबित हो |

**एक सीमा पहले से दर्ज है:** forward shadow edge **साबित नहीं** कर सकता। Annual Sharpe 1.0 को 95% one-sided भरोसे से साबित करने में normal returns मानकर ~2.7 साल लगते हैं (≈ (1.645/SR)², हमारी गणना), और fat tails इसे और लंबा करते हैं। इसलिए A8 का gate "profitability साबित करो" नहीं, बल्कि "backtest से अपेक्षित सीमा के भीतर रहो, और bugs, cost की ग़लती या disaster न हो" है। अब साफ़ holdout सिर्फ़ forward data है, इसलिए यह सीमा पहले से कहीं ज़्यादा मायने रखती है। Real-money का निर्णय ऐसे सबूत पर होगा जो कभी पूरी तरह निर्णायक नहीं होगा, और user को यह पहले से पता होना चाहिए।

---

## हम अभी क्या नहीं जानते

| अज्ञात | क्यों मायने रखता है | कैसे पता चलेगा |
|---|---|---|
| 4H meta-label brain costs के बाद edge देगा या नहीं | पूरी योजना का केंद्र। पिछले swing entry AI (0.530–0.539) असफल रहे थे | A3–A5, फिर A8 |
| Step 26 की exit skill पैसे में क्यों नहीं बदली | AI exit का अगला trial इसी समझ पर टिका है। "छूटे rebound" सिर्फ़ परिकल्पना है | A6 में छूटी चाल बनाम बचाई गिरावट का विभाजन |
| "+k ATR, −m ATR से पहले" की first-passage दर | Meta-label का सही base rate और stop/target गणित | A1 माप |
| 4H पर असली stop slippage | 1% (F7) मानने से risk ~33% बढ़ता है। असली मान इससे कम या ज़्यादा हो सकता है | Demo/forward fills |
| 1W का trend (VR 1.18) टिकाऊ है या नहीं | N = 353, हाल में ac1 0.026, कुछ coins पर ऋणात्मक | Pooled weekly test; बड़ा universe |
| 1M का कोई उपयोग है या नहीं | N = 81, उल्टा top-down असर, 3–4 halving observations | शायद मौजूदा data से कभी नहीं |
| HTF tilt बनाम veto बनाम सिर्फ़ feature | कोई बाहरी OOS अध्ययन नहीं मिला; हमारा तर्क mean बनाम hit-rate पर टिका है | Pre-registered तुलना, budget में गिनी जाए |
| 1h और 4h का OOS correlation | B2-fast को pooled रखें या अलग करें | Phase B |
| Futures taker 0.04% या 0.05%, और BNB छूट की पक्की शर्तें | Cost model का आधार | Live account का `commissionRate` |
| Funding का 4H sleeve पर असर, और crash में slippage का वितरण | Short leg और tail risk | असली funding history; forward data |
| Binance 1w/1M kline boundaries, sub-account नियम, minimum notional, USDT-M WS stream सीमा (1024 बनाम 200), user stream का `/private` route | Engine की सही wiring | Primary docs + testnet |
| बाहरी साहित्य में जो NOT CHECKED रहा: Dasari 2026, Claeskens 2016, Sullivan–Timmermann–White 1999, Zarattini et al. के आँकड़े, Joubert meta-labeling, M4/M5 की horizon-वार तालिकाएँ, Man AHL की तालिकाएँ | कई तर्क इन्हीं पर टिके हैं | अगला verification pass |
| 5m/15m maker-side कभी लाभदायक होगा या नहीं | User का "fast entry, fast exit" सपना | सिर्फ़ maker-only research (F); retail fee tier पर संभावना कम |

---

## निष्कर्ष

इस सत्यापन से सबसे बड़ा सबक यह है कि **हमारी सबसे ख़तरनाक ग़लतियाँ बाहरी papers में नहीं, अपने ही आँकड़ों को दोबारा लिखने में थीं।** एक उदाहरण exit brain है: "skill नहीं थी" और "skill थी पर पैसा नहीं बना" दो अलग दुनिया हैं। पहली कहती है कि दिशा छोड़ दो। दूसरी कहती है कि सवाल को पैसे की भाषा में दोबारा पूछो, और AUC को gate मानना बंद करो। Holdout का दूषित होना भी इसी तरह चुपचाप हुआ: हर विश्लेषण ने "बस देखने" के लिए नवीनतम data छुआ। इसका नतीजा एक कड़ा पर स्वस्थ नियम है। आगे का साफ़ सबूत सिर्फ़ समय से आएगा, और इसलिए recorder को model से पहले चालू होना चाहिए।

दूसरा सबक design के बारे में है। User का सपना था कि सातों timeframes अपने-अपने दिमाग से sync में चलें। Data कहता है कि sync का मतलब बराबरी नहीं, **श्रम-विभाजन** है। 5m/15m पर cost चाल का 38–68% खा जाता है, इसलिए वहाँ "तेज़ entry, तेज़ exit" का सही अर्थ तेज़ **execution** है, तेज़ alpha नहीं। 1W/1M पर चाल बड़ी है पर observations इतने कम हैं कि वहाँ AI अभी सीख नहीं सकता, सिर्फ़ झुकाव दे सकता है। 4h बीच का वह बिंदु है जहाँ cost चाल का 10% है और data हज़ारों bars का है। इसलिए "सब timeframes sync में" का सबसे ईमानदार पहला रूप **एक AI brain, सात घड़ियाँ** है: हर timeframe अपने bar पर जागता है, अपनी भूमिका निभाता है, और अगला brain तभी जुड़ता है जब वह पहले वाले से कम correlated होकर portfolio में कुछ नया जोड़ता साबित हो।


---

# भाग 4 (17 अक्टूबर 2026): market की सीढ़ी, line patterns और sessions (हमारे data पर pre-registered study)

(यही रिपोर्ट अलग file में भी है: `REPORT_LADDER_PATTERNS_SESSIONS_17_OCT_2026.md`)


**तारीख:** 17 अक्टूबर 2026 | **GitHub:** कुछ नहीं | **कोई trading, AI training या deploy नहीं**

**Lock:**
- Protocol: `logs/research_ladder_sessions/LADDER_SESSIONS_PROTOCOL_PREREGISTERED.md`
- SHA256: `e7ae067d…2cf77`, किसी भी नतीजे से पहले lock हुआ।

**Code:**
- `src/research/ladder_sessions.py`, SHA `6962deb9…`
- Verifier: `src/audits/verify_ladder_sessions.py`, SHA `b17789ce…`

**Verifier: V1, V2, V3 सब PASS।**
- Verifier ने अलग code से गिनती दोबारा की:
  - 4h और 1D पर state के हिस्से और pullback के median, 10 coins पर, हूबहू मिले;
  - 10 coins के raw 1h data से session returns और रोज़ के high/low किस session में बने, यह भी हूबहू मिला।
- Claims JSON tables से मिला, और protocol व data के SHA नहीं बदले।

**Lock के बाद जोड़ी गई दो जाँचें** (`CODE_CHANGES_AFTER_LOCK.md` में दर्ज):
- Fibonacci के लिए local-density null, और रोज़ के high/low के लिए random-walk (arcsine) null।
- Pre-registered फ़ैसले बदले नहीं गए। दोनों जाँचें नीचे अलग दिखाई गई हैं।

**Data:**
- Phase 1 के verified swings: `legs_all.parquet` (SHA `bbe7a4fd…`, 24.5 लाख swings)।
- 10 बड़े coins: BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LTC, LINK।
- अवधि 2017-08 से 2026-09, ZigZag K = 3 (K = 2 और 4 पर robustness)।
- Sessions के लिए raw 1h data, 2020-01 से 2026-09, UTC।

**बाहरी research:** `research_notes/मार्केट सीढ़ी पैटर्न सेशन रिसर्च/`। कोई भी paper पूरा नहीं पढ़ा जा सका (SSRN, ScienceDirect और Springer ने access रोका), इसलिए बाहरी आँकड़े abstract या summary के स्तर के हैं।

---

## 0. सीढ़ी को कैसे नापा
हर swing का ऊपरी सिरा H (high) है और निचला सिरा L (low)। हर नए high की तुलना पिछले high से और हर नए low की तुलना पिछले low से हुई:
- **HH:** पिछले high से ऊँचा high। **LH:** पिछले high से नीचा high।
- **HL:** पिछले low से ऊँचा low। **LL:** पिछले low से नीचा low।

इनसे market की चार हालतें बनती हैं:

| हालत | मतलब | आपकी भाषा में |
|---|---|---|
| **UP सीढ़ी** | HH + HL | ऊपर चढ़ती सीढ़ी |
| **DOWN सीढ़ी** | LH + LL | नीचे उतरती सीढ़ी |
| **सिकुड़न (contraction)** | LH + HL | सीढ़ी रुकी, दायरा छोटा होता जा रहा है (triangle जैसा) |
| **फैलाव (expansion)** | HH + LL | दोनों तरफ़ बड़े झटके (broadening) |

**ज़रूरी सीमा:** कोई label तभी पक्का होता है जब अगला swing confirm हो जाए। Phase 1 के मुताबिक तब तक swing का लगभग 57% हिस्सा पूरा हो चुका होता है। इसलिए नीचे के सारे नतीजे **विवरण** हैं, trade करने के नियम नहीं।

## 1. Market कितने समय किस हालत में रहता है (K = 3, swings की गिनती से)
| Timeframe | UP सीढ़ी | DOWN सीढ़ी | सिकुड़न | फैलाव |
|---|---|---|---|---|
| 5m | 31.1% | 31.3% | 21.7% | 15.9% |
| 15m | 31.5% | 31.2% | 21.7% | 15.6% |
| 1h | 32.7% | 30.9% | 21.8% | 14.6% |
| 4h | 34.4% | 29.4% | 22.0% | 14.3% |
| 1D | 36.2% | 29.1% | 18.8% | 16.0% |
| 1W | 43.4% | 19.4% | 14.3% | 22.9% |
| 1M (सिर्फ़ 31 points) | 48% | 10% | 13% | 29% |

- **लगभग 35–38% समय market किसी साफ़ सीढ़ी में नहीं होता।** वह या तो सिकुड़ रहा होता है या दोनों तरफ़ फैल रहा होता है।
- बड़े timeframe पर UP का हिस्सा ज़्यादा है। इसकी एक वजह यह है कि ये 10 coins **आज भी बचे हुए बड़े coins** हैं (survivorship), और 2017–2026 में कुल मिलाकर तेज़ी रही। यह बात हर coin पर लागू नहीं होगी।
- K = 2 और K = 4 पर भी लगभग यही हिस्से मिले (`A7_robust_K.csv`)।

## 2. सीढ़ी कितनी लंबी चलती है: ज़्यादातर छोटी
UP सीढ़ी बनने के बाद उसके अंदर कितने और नए HH बने:

| Timeframe | 1 कदम | 2 | 3 | 4 | 5 या ज़्यादा | औसत |
|---|---|---|---|---|---|---|
| 5m | 50% | 19% | 6% | 2% | 1.1% | 1.20 |
| 1h | 51% | 19% | 7% | 2.6% | 1.6% | 1.30 |
| 4h | 46% | 18% | 10% | 4.7% | 2.6% | 1.45 |
| 1D | 53% | 18% | 8% | 4.6% | 3.3% | 1.50 |
| 1W (23 सीढ़ियाँ) | 30% | 17% | 22% | 4% | 4% | 1.70 |

(बाकी बचे हिस्से में 0 कदम हैं, यानी सीढ़ी बनते ही टूट गई।)

- **लंबी सीढ़ी (5 या ज़्यादा कदम) बहुत कम बनती है, सिर्फ़ 1–3%।** ज़्यादातर चाल एक-दो कदम की झटके वाली (impulse) होती है।
- **DOWN सीढ़ियाँ और भी छोटी होती हैं** (4h पर औसत 1.10, 1D पर 1.05)। गिरावट तेज़ आती है और जल्दी पलटती है।
- **सीढ़ी के ढंग** (3 या ज़्यादा कदम वाली सीढ़ियों में): हर कदम लगभग बराबर (steady) 0.5% से कम, तेज़ होती हुई (accelerating) 2–9%, धीमी पड़ती हुई (decelerating) 3–13%, मिली-जुली 4–9%।

## 3. अगला कदम ऊपर जाएगा या नहीं (सिर्फ़ विवरण)
UP सीढ़ी में k कदम हो चुके हों, तो अगला high भी HH होने का हिस्सा कितना है:

| Timeframe | k = 1 | k = 2 | k = 3 | बिना शर्त HH का हिस्सा |
|---|---|---|---|---|
| 5m | 45.6% | 43.4% | 43.4% | 46.9% |
| 1h | 45.8% | 46.4% | 43.4% | 47.3% |
| 4h | 52.0% | 52.4% | 52.6% | 48.7% |
| 1D | 52.3% | 53.1% | 66.7% (24 बार) | 52.1% |

- **5m से 1h तक सीढ़ी में होने से अगले कदम के ऊपर जाने का मौका नहीं बढ़ता।** वह बिना शर्त वाले हिस्से से भी थोड़ा कम है।
- **4h पर हल्का फ़ायदा है** (~52% बनाम 48.7%), पर यह इतना छोटा है कि अकेले trade का नियम नहीं बन सकता।
- **DOWN सीढ़ी में** अगला low LL होने का हिस्सा 31–45% है, जो बिना शर्त LL हिस्से (44–47%) से कम है। मतलब नीचे की सीढ़ी जल्दी थमती है। यह Swing Anatomy की उस बात से मेल खाता है कि swing के पीछे चलकर short करना कमज़ोर रहा।

## 4. Pullback कितना गहरा होता है, और Fibonacci
UP सीढ़ी में हर गिरावट पिछली तेज़ी का कितना हिस्सा वापस लेती है:

| Timeframe | Median | बीच के 50% |
|---|---|---|
| 5m | 0.61 | 0.46–0.77 |
| 1h | 0.61 | 0.46–0.78 |
| 4h | 0.62 | 0.49–0.77 |
| 1D | 0.63 | 0.49–0.77 |

- **हर timeframe पर आम pullback पिछली चाल का 45–77% होता है।** यह फिर से वही self-similar बात है जो Phase 1 में दिखी थी।
- यह आंशिक रूप से परिभाषा से भी आता है: UP सीढ़ी में pullback 100% से कम ही होगा, नहीं तो LL बन जाता।
- **DOWN सीढ़ी के उछाल बड़े timeframe पर छोटे हैं:** 1D पर 0.53, 1W पर 0.32 (सिर्फ़ 17 बार)। मंदी में उछाल कमज़ोर रहते हैं।

**Fibonacci (38.2%, 50%, 61.8%):**
- **Pre-registered test ने "clustering" कहा।** 5m, 15m, 1h और 4h पर इन levels के पास ±2% में ज़्यादा pullbacks मिले (4h: 6.8% बनाम 5.5%)। 6 में से 4 timeframes होने से protocol का नियम पूरा हुआ।
- **पर lock के बाद की जाँच में यह असर नहीं टिका।**
  - Protocol में तुलना के points (0.30, 0.44, 0.56, 0.70) ठीक नहीं चुने गए थे। 0.30 कम घनत्व वाले हिस्से में है, जबकि 0.5 और 0.618 वहाँ हैं जहाँ ज़्यादातर pullbacks होते ही हैं।
  - जब हर level की तुलना उसके **आस-पास के घनत्व** से की गई, तो कोई level साफ़ ऊपर नहीं निकला: ratio 0.98–1.05 (5m–1h), और सभी 18 मामलों में z < 2।
- **ईमानदार फ़ैसला:** Fibonacci levels की कोई ख़ास ताकत हमारे data में साबित नहीं हुई। Pullbacks बस आम तौर पर 45–77% के बीच होते हैं। बाहरी research में भी Fibonacci के पक्ष में कोई peer-reviewed सबूत नहीं मिला।

## 5. सीढ़ी कैसे टूटती है
| Timeframe | UP सीढ़ी: पहले lower high (थकान) | UP सीढ़ी: सीधा LL (तेज़ टूट) | DOWN सीढ़ी: पहले higher low (तल बनना) |
|---|---|---|---|
| 5m | 54% | 46% | 55% |
| 1h | 51% | 49% | 59% |
| 4h | 51% | 49% | 62% |
| 1D | 35% | **65%** | 67% |
| 1W (22 बार) | 27% | **73%** | 55% |

- **छोटे timeframe पर** UP सीढ़ी आधी बार धीरे थकती है: पहले lower high बनता है और फिर सिकुड़न आती है।
- **1D और 1W पर** ज़्यादातर सीधी तेज़ टूट होती है: पहले LL बनता है।
- **DOWN सीढ़ी** ज़्यादातर पहले higher low बनाकर ख़त्म होती है, यानी तल धीरे-धीरे बनता है।

## 6. Double top और double bottom (line chart patterns)
Double top का मतलब है दो लगातार highs जो 0.5 ATR के भीतर हों। उसके बाद अगला low LL बना या नहीं:

| Timeframe | Double top के बाद LL | बिना शर्त LL | Double bottom के बाद HH | बिना शर्त HH |
|---|---|---|---|---|
| 5m | 55.5% | 47.2% | 55.7% | 46.9% |
| 1h | 54.4% | 45.5% | 53.7% | 47.3% |
| 4h | 50.2% | 43.6% | 51.4% | 48.7% |
| 1D | 63.8% (58 बार) | 45.0% | 56.8% (81 बार) | 52.1% |

- **Double top/bottom के बाद उलटी दिशा का अगला कदम 3–9 percentage points ज़्यादा बार आता है।** यह इस पूरी study का सबसे साफ़ pattern है।
- फिर भी यह सिर्फ़ विवरण है। Pattern दूसरे swing के confirm होने पर पता चलता है, और इसमें खर्च नहीं गिना गया। इसे AI के feature के रूप में परखा जाएगा।
- **बाहरी सबूत भी यही कहते हैं:**
  - Lo, Mamaysky और Wang (2000, *Journal of Finance*) ने patterns में "incremental information" पाई।
  - Savin, Weller और Zvingelis (2007, *J. Financial Econometrics*) ने पाया कि head-and-shoulders अकेले लगभग फ़ायदा नहीं देता, पर दूसरी चीज़ों के साथ जुड़कर मदद करता है।
  - Chang और Osler (1999, *Economic Journal*) के अनुसार FX में head-and-shoulders से सरल momentum नियम बेहतर निकले।
  - (सभी abstract या summary स्तर पर पढ़े गए।)
- **Candlestick patterns:** इन्हें हमने नहीं नापा। बाहरी सबूत नकारात्मक है:
  - Marshall, Young और Rose (2006): out-of-sample कोई ताकत नहीं।
  - Crypto पर 0.5% fee के बाद कोई pattern नहीं टिका।

## 7. Sessions: Asia, Europe और US (UTC, 2020-01 से 2026-09, 10 coins)
Session की खिड़कियाँ: Asia 00–08, Europe 08–13, US 13–21, Late-US 21–24 (UTC)। भारत के समय में Asia 05:30–13:30, Europe 13:30–18:30, US 18:30–02:30, Late-US 02:30–05:30।

**(क) दिशा: किसी session में साबित नहीं।** Pre-registered नियम था: CI 0 को न छुए, और 2020–23 व 2024–26 दोनों में दिशा एक हो।

| Session | औसत (bps प्रति दिन) | 95% CI | 2020–23 | 2024–26 | फ़ैसला |
|---|---|---|---|---|---|
| Asia | +3.4 | −5.4 से +11.5 | +4.6 | +1.6 | साबित नहीं |
| Europe | +0.2 | −7.1 से +7.2 | −0.1 | +0.7 | साबित नहीं |
| US | +1.1 | −8.9 से +10.5 | **+6.6** | **−6.9** | साबित नहीं (ETF के बाद दिशा उलटी) |
| Late-US | +5.3 | −0.4 से +10.6 | +5.8 | +4.6 | साबित नहीं (करीब, पर CI 0 को छूता है) |

**(ख) हलचल: US session सबसे ज़्यादा सक्रिय है।** दिन की कुल हलचल का हिस्सा:
- US 36% (8 घंटे में, ~4.5% प्रति घंटा)।
- Asia 32% (~4.0% प्रति घंटा)।
- Europe 20% (~4.0% प्रति घंटा)।
- Late-US 12% (~4.0% प्रति घंटा)।

2024–26 में US का हिस्सा 35% से बढ़कर 39% हुआ।

**(ग) दिन का high और low किस session में बनता है**, random walk की उम्मीद (arcsine नियम) से तुलना:

| Session | High बना | Low बना | Random walk की उम्मीद | Uniform (सिर्फ़ घंटे गिनकर) |
|---|---|---|---|---|
| Asia | 39.5% | 40.0% | 39.2% | 33.3% |
| Europe | 14.0% | 12.5% | 13.5% | 20.8% |
| **US** | **29.6%** | **32.6%** (2024–26: 35.4%) | 24.3% | 33.3% |
| Late-US | 16.9% | 14.9% | 23.0% | 12.5% |

- पहली नज़र में Asia में ज़्यादा highs/lows दिखते हैं। पर random walk में भी दिन का high/low पहले और आख़िरी घंटों में ज़्यादा बनता है (arcsine नियम), और Asia में दिन का पहला घंटा आता है। उस हिसाब से **Asia और Europe बिल्कुल सामान्य हैं।**
- **US session में उम्मीद से ज़्यादा दिन के high और low बनते हैं**, और 2024 के बाद low और ज़्यादा। Late-US में उम्मीद से कम बनते हैं।

**(घ) 1h के swing कहाँ पलटते हैं:**
- US session में 39% swing highs और 43% swing lows बनते हैं, जबकि सिर्फ़ घंटों के हिसाब से 33% होने चाहिए।
- Asia में 31% highs और 28% lows।

**बाहरी सबूत से मेल:**
- Eross et al. (2019, *RIBAF*) और Baur et al. (2019, *Finance Research Letters*) के अनुसार crypto में volume और volatility शेयर बाज़ारों की घड़ी पर चलते हैं, ख़ासकर US open पर। Return की दिशा के असर स्थिर नहीं रहते।
- ETF के बाद New York के घंटों की भूमिका बढ़ने की बात एक SSRN preprint (Schmidt & Kraft) और एक Aalto thesis में मिलती है। ये सिर्फ़ summary स्तर पर पढ़े गए।

## 8. AI system के लिए इसका मतलब
1. **सीढ़ी की जानकारी AI के inputs (features) के रूप में होगी, नियम के रूप में नहीं।** इनमें शामिल हैं: हालत (UP/DOWN/सिकुड़न/फैलाव), सीढ़ी में अब तक कितने कदम हुए, पिछले pullback की गहराई, और double top/bottom। ये Phase 2 swing AI में परखे जाएँगे। हर feature पर `available_at` (confirm होने का समय) दर्ज होगा।
2. **Fibonacci का कोई नियम नहीं बनेगा।**
3. **लंबी सीढ़ियाँ कम बनती हैं, पर कमाई उन्हीं में है।** यह Phase 1 से मेल खाता है: कमाई कुछ बड़ी चालों से आती है। इसलिए exit में trailing stop रहेगा, ताकि लंबी सीढ़ी पूरी पकड़ी जा सके, और छोटी सीढ़ियों में नुकसान छोटा रहे।
4. **Short वाला हिस्सा:** नीचे की सीढ़ियाँ छोटी होती हैं और जल्दी तल बनाती हैं। इसलिए short में profit जल्दी लेने और stop के नियम अलग से परखने होंगे।
5. **Sessions दिशा के लिए नहीं, risk और execution के लिए:**
   - US session में हलचल और swing पलटने की घटनाएँ सबसे ज़्यादा होती हैं। Stop की चौड़ाई और entry के समय में यह ध्यान रखा जाए, जैसे US open से ठीक पहले तंग stop न रखना।
   - Late-US शांत रहता है।
   - दिशा के लिए कोई session नियम नहीं बनेगा, क्योंकि ETF के बाद US की दिशा उलट गई।
6. **4h पर** सीढ़ी के अगले कदम का हल्का फ़ायदा (~52% बनाम 49%) और double top/bottom का असर (+3 से +9 points) AI के लिए छोटे पर असली inputs हो सकते हैं। ये खर्च के बाद काम आते हैं या नहीं, यह सिर्फ़ pre-registered backtest बताएगा।

## 9. सीमाएँ (ईमानदारी से)
- यह सिर्फ़ विवरण है, भविष्यवाणी नहीं। Label confirm होने में देर लगती है, और इसमें खर्च शामिल नहीं है।
- सिर्फ़ 10 बड़े, आज भी बचे हुए coins (survivorship)।
- 1W और 1M पर नमूने बहुत कम हैं (23 और 9 सीढ़ियाँ), इसलिए वहाँ के नतीजे भरोसेमंद नहीं हैं।
- कई तुलनाएँ एक साथ की गई हैं। सिर्फ़ protocol वाले फ़ैसलों पर ही दावा है।
- 2025-10 से 2026-09 का data पहले देखा जा चुका है।
- Session के weekend, weekday और daily-state वाले हिस्सों पर कोई pre-registered फ़ैसला नहीं था। वे आँकड़े सिर्फ़ `B1_session_returns.csv` में दर्ज हैं।

**सारी tables:** `logs/research_ladder_sessions/` (A1–A7, B1–B4, P1–P2)।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।


---

# भाग 5 (17 अक्टूबर 2026): सीढ़ी पर long/short, test (probe) entry और धीरे-धीरे size बढ़ाना (pre-registered simulation)

(अलग file: `REPORT_PROBE_SCALEIN_LADDER_17_OCT_2026.md`)


**तारीख:** 17 अक्टूबर 2026 | **GitHub:** कुछ नहीं | **कोई order, AI training या deploy नहीं।** यह सिर्फ़ इतिहास पर simulation है।

**Lock:**
- Protocol: `logs/research_probe_scalein/PROBE_SCALEIN_PROTOCOL_PREREGISTERED.md`
- SHA256: `90814d65…cabda`, किसी भी नतीजे से पहले lock हुआ।
- Lock के बाद कोई बदलाव नहीं हुआ।

**Code:**
- `src/research/probe_scalein.py` (SHA `52f49641…`)
- Verifier: `src/audits/verify_probe_scalein.py` (SHA `263bea25…`)

**Verifier: V1, V2, V3 सब PASS।**
- 300 random trades raw 5m data से एक अलग loop में दोबारा simulate हुए। चारों तरीकों का नतीजा 1e-9 R तक हूबहू मिला।
- 4h और 1D के औसत दोबारा गिने गए।
- Claims की जाँच tables से हुई।

**Data:**
- Phase 1 के verified swings (K = 3), 10 बड़े coins।
- Candles 5m data से बनाई गईं।
- Entries 2020-02 से 2026-09 तक।
- **कुल 1,44,967 signals:** 5m 1,02,783 | 15m 31,956 | 1h 7,947 | 4h 1,976 | 1D 305।

**बाहरी research:** `research_notes/टेस्ट एंट्री स्केल इन रिसर्च/`।

---

## 1. आपका idea, जैसा परखा गया
**Signal (बिना AI, सिर्फ़ सीढ़ी के नियम से):**
- **Long:** ऊपर की सीढ़ी में नया higher low (HL) पक्का होते ही।
- **Short:** नीचे की सीढ़ी में नया lower high (LH) पक्का होते ही।
- **Entry:** पक्का होने के बाद अगली candle खुलते ही।

**Stop, अपने-आप:**
- Long पर swing low से 0.5 ATR नीचे, short पर swing high से 0.5 ATR ऊपर।
- उसके बाद trailing stop: अब तक के सबसे अच्छे भाव से 3 ATR पीछे।
- 60 candles बाद time stop।

**खर्च:**
- BNB से fee: futures पर 0.045% प्रति side, यानी 0.036% fee और ~0.009% spread।
- Funding: 0.01% हर 8 घंटे पर (सावधानी के लिए दोनों sides पर लगाई गई)।
- Spot long पर 0.085% प्रति side।
- Stress test में सारा खर्च दोगुना।

**चार तरीकों की तुलना:**

| तरीका | मतलब |
|---|---|
| **V0 पूरा** | एक बार में पूरी size |
| **V1 test + बढ़ाना** | 25% size से test entry; भाव 1 ATR हमारी तरफ़ चले तो बाकी 75% |
| **V2 सीढ़ी-दर-सीढ़ी** | 25%, फिर +1 ATR पर 25%, फिर +2 ATR पर 50% |
| **V3 paper test** | पहले सिर्फ़ paper पर नज़र; भाव 1 ATR हमारी तरफ़ चले तब पूरी size। Stop पहले लग जाए तो trade नहीं लिया जाता |

**R का मतलब:** पूरी size पर entry के समय जितना पैसा दाँव पर है, वह 1 R है। उदाहरण: 10,000 USDT का 0.5% = 40 USDT। तब +0.1 R ≈ +4 USDT प्रति trade।

## 2. नतीजे (futures, BNB fees, हर trade का औसत R)
| Timeframe | Side | V0 पूरा | V1 test+बढ़ाना | V2 सीढ़ी | V3 paper | खर्च से पहले (V0) | V0 जीत % |
|---|---|---|---|---|---|---|---|
| **5m** | long | **−0.123** | −0.082 | −0.072 | −0.068 | +0.004 | 32% |
| 5m | short | −0.111 | −0.086 | −0.079 | −0.078 | +0.014 | 33% |
| **15m** | long | −0.052 | −0.031 | −0.024 | −0.024 | +0.014 | 34% |
| 15m | short | −0.044 | −0.038 | −0.036 | −0.036 | +0.022 | 36% |
| **1h** | long | +0.027 | +0.027 | +0.028 | +0.027 | +0.061 | 37% |
| 1h | short | +0.002 | +0.003 | −0.003 | +0.003 | +0.037 | 38% |
| **4h** | long | **+0.106** | +0.083 | +0.082 | +0.076 | +0.131 | 39% |
| 4h | short | +0.054 | +0.041 | +0.045 | +0.037 | +0.082 | 40% |
| **1D** | long | +0.228 | +0.265 | +0.238 | +0.278 | +0.253 | 44% (153 trades) |
| 1D | short | +0.105 | +0.054 | +0.042 | +0.037 | +0.147 | 40% (152 trades) |

**सबसे बुरे 5% trades का नुकसान (5th percentile R):**

| Timeframe | V0 | V1 | **V2** | V3 |
|---|---|---|---|---|
| 5m | −1.05 | −0.88 | **−0.68** | −0.96 |
| 4h (long) | −0.91 | −0.79 | **−0.57** | −0.87 |
| 1D (long) | −0.92 | −0.69 | **−0.43** | −0.76 |

## 3. इसका सीधा मतलब
1. **"हर 5 मिनट पर थोड़ा-थोड़ा कमाना" खर्च की वजह से नहीं चलता।**
   - 5m पर ladder signals की खर्च से पहले की कमाई लगभग शून्य है (+0.004 R)।
   - खर्च 0.13 R प्रति trade है, इसलिए हर तरीका घाटे में है: V0 के लिए 1,02,783 trades पर कुल लगभग −12,000 R।
   - 15m भी घाटे में है।
   - Test entry से घाटा **कम** होता है, पर ख़त्म नहीं होता।
   - Table में V1/V2/V3 का "बेहतर" होना यहाँ सिर्फ़ "कम घाटा" है, क्योंकि छोटी size पर खर्च भी कम लगता है।
2. **1h बराबरी पर है** (+0.03 R long, लगभग 0 short)। यहाँ test entry से औसत नहीं बदलता, बस बड़े नुकसान घटते हैं।
3. **4h पर पूरी entry सबसे ज़्यादा कमाती है** (+0.106 R long, +0.054 short)।
   - Test entry या किस्तों में size बढ़ाने से कमाई ~20–30% घटती है (−0.01 से −0.03 R)।
   - बदले में सबसे बुरे trades का नुकसान 13–38% कम होता है।
   - **यह सौदा है: कम नुकसान के बदले कम कमाई।**
4. **1D long पर** test entry (V1, V3) का औसत थोड़ा ज़्यादा है (+0.27 बनाम +0.23 R) और नुकसान भी कम। पर सिर्फ़ 153 trades हैं, और CI 0 को पार करती है, इसलिए यह साबित नहीं है।
5. **1D short पर** size बढ़ाना कमाई घटाता है: V2 में साफ़ नुकसान (CI 0 से नीचे)। नीचे की सीढ़ियाँ छोटी होती हैं, यह बात भाग 4 से मेल खाती है।
6. **Pre-registered अंतिम फ़ैसला: "Scale-in की सिफ़ारिश साबित नहीं" (long और short दोनों)।**
   - शर्त थी कि V1 या V2 कम से कम 3 timeframes पर कमाई बढ़ाए, और 2× खर्च पर भी।
   - Long पर V2 2× खर्च में 3 timeframes पर "बेहतर" निकला, पर सामान्य खर्च में सिर्फ़ 2 पर, इसलिए नियम पूरा नहीं हुआ।
   - जहाँ "बेहतर" निकला, वह ज़्यादातर 5m/15m का "कम घाटा" है।

**Paper test (V3) पर एक अलग बात:**
- 2025-10 से 2026-09 के कमज़ोर साल में 1D long पर V0 −0.36 R रहा, जबकि V3 लगभग 0 (−0.004) रहा।
- यानी जब market साथ नहीं देता, तो "पहले देखो फिर घुसो" बचाता है।
- पर यह छोटा नमूना है, और यह अवधि पहले देखी जा चुकी है।

## 4. बाहरी सबूत (कई स्रोत)
**Pyramiding (Turtle, "जीतते trade में और जोड़ो"):**
- नियम अच्छी तरह दर्ज है: हर 0.5N पर 1 unit, ज़्यादा से ज़्यादा 4। यह practitioner स्रोत है, और 0.5N और 1N के बीच मतभेद है।
- पर **कहीं भी "pyramiding के साथ और बिना" की नियंत्रित तुलना नहीं मिली।**
- सिद्धांत (Kaminski & Lo 2014, *J. Financial Markets*): जीत के बाद size बढ़ाना तभी मदद करता है जब trend आगे चलता है (positive autocorrelation)। Market पलटता हो, तो यह नुकसान करता है।
- Crypto में:
  - Daily और weekly पर momentum मिलता है (Liu & Tsyvinski 2021, *RFS*)।
  - 1–4 घंटे पर BTC पलटता है (*Ledger* journal)।
  - हमारे अपने data में 5m से 1D तक हल्का पलटाव है (VR < 1)।

  इसलिए छोटे timeframe पर size बढ़ाना उल्टा पड़ता है। हमारा simulation यही दिखाता है।
- **"पहले confirm, फिर entry"** पर भी कोई academic सबूत नहीं मिला कि यह खर्च के बाद तुरंत entry से बेहतर है। एक चेतावनी ज़रूर मिली: backtest में confirmation के बाद भी पुराने भाव पर fill मान लेने की गलती से झूठा फ़ायदा दिखता है। हमारे simulation में fill confirmation वाले bar पर ही हुआ है, असली भाव पर।

**"थोड़ा-थोड़ा रोज़ कमाना" का इतिहास:**
- Taiwan के day traders: 97% के आगे भी घाटे में रहने की संभावना (Barber, Lee, Liu, Odean, *Review of Asset Pricing Studies* 2020)।
- Brazil: 97% ने पैसा गँवाया (Chague, De-Losso, Giovannetti, working paper)।
- EU में CFD खातों में 74–89% घाटे में (ESMA 2018)।
- Crypto apps के ज़्यादातर users घाटे में (BIS Bulletin 69, 2023)।

**Break-even जीत % (सिर्फ़ fees, spread अलग से):**
- Target और stop दोनों 0.2% हों: futures taker पर **75% जीत** चाहिए, maker पर 60%।
- Target और stop 0.3% हों: taker पर 67%, maker पर 57%।
- हमारे ladder trades की जीत 32–45% है। इसलिए छोटे target वाला तरीका यहाँ नहीं चलता।

**Binance पर सबसे छोटी order** (live API से आज verify किया):

| जगह | Minimum order |
|---|---|
| Spot BTC और ETH | 5 USDT |
| Spot DOGE | 1 USDT |
| Futures XRP, SOL, DOGE | 5 USDT |
| Futures ETH, LINK | 20 USDT |
| Futures BTC | 50 USDT, साथ में quantity कम से कम 0.001 BTC |

यानी 10,000 USDT के account में असली पैसे से test entry मुमकिन है: 25% test ≈ 250 USDT notional के आस-पास।

## 5. हमारे system के लिए फ़ैसले (प्रस्ताव, आपकी मंज़ूरी से)
1. **5m और 15m पर अलग से trading नहीं होगी।** इस study ने भाग 3 की बात पक्की की: यहाँ खर्च कमाई से बड़ा है। ये timeframes सिर्फ़ entry का समय चुनने के काम आएँगे।
2. **4h:** मुख्य तरीका पूरी entry (V0), क्योंकि सबसे ज़्यादा कमाई इसी में है। जहाँ AI का भरोसा कम हो या market जोखिम भरा लगे, वहाँ **V2 (किस्तों में)** एक विकल्प है: कमाई ~20–25% कम, पर सबसे बुरा नुकसान ~38% कम। यह चुनाव AI के meta-label और size वाले दिमाग का काम होगा, और pre-registered test से तय होगा।
3. **Paper test (V3) बिना पैसे के** खराब दौर में बचाव दिखाता है। इसे "AI को भरोसा कम हो तो पहले confirm करो" वाले नियम के रूप में अगले test में शामिल किया जाएगा।
4. **Short में size न बढ़ाएँ।** नीचे की सीढ़ियाँ छोटी होती हैं, इसलिए वहाँ profit जल्दी लेना और size पूरी रखना बेहतर दिखता है। यह भी आगे परखा जाएगा।
5. **ज़रूरी सच:** इन सबमें **AI नहीं है**, सिर्फ़ सीढ़ी के नियम हैं। 4h पर +0.1 R कुछ ही coins पर मिला है। असली system में AI का काम यह चुनना होगा कि कौन-सी सीढ़ी entry लेनी है, ताकि यह औसत बढ़े।

## 6. सीमाएँ
- Exits के नियम तय करके रखे गए, उन्हें optimize नहीं किया।
- Funding असली नहीं, मानी हुई है।
- Trades एक-दूसरे पर चढ़े हुए (overlap) हैं, इसलिए max drawdown सिर्फ़ संकेत है।
- 10 बड़े coins।
- 2025-10 से 2026-09 पहले देखा जा चुका है।
- 1D पर नमूने कम हैं।

**सारी tables:** `logs/research_probe_scalein/` (S1_summary, S2_diff_vs_full, trades.parquet)।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
