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
