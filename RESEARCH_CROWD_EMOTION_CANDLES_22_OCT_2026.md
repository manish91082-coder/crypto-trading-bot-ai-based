# भीड़ के emotions, candles और "5% वाला माइंडसेट": गहरी research + audit (22 अक्टूबर 2026)

**सवाल (user):**
- क्या 1m/5m/15m candles करोड़ों traders के emotions दिखाती हैं?
- क्या 90–95% लोग candles और technicals देखकर trade करते हैं?
- क्या market इन्हीं emotions से चलता है?
- अगर हम इन emotions को गणित से पकड़ लें, तो क्या हमारे पास वह "5% वाला माइंडसेट" होगा जो 95% के पास नहीं है?
- क्या कर सकते हैं, कैसे, और फ़ायदा क्या होगा (spot या futures, दोनों पर)?

**तरीका (इसी अनुशासन से):**
- (a) बाहरी research: academic studies, Binance docs और data। हर दावे के साथ स्रोत की गुणवत्ता लिखी है।
- (b) हमारे अपने पुराने, verified नतीजे: TFX/TFX-S/DISC, S4/S5, AI trials, master audit।
- (c) VM से Binance के public historical data की **आज की जाँच** (§4)।
- (d) Report के आख़िर में इसी report का audit: कौन-सा दावा जाँचा, और क्या ग़लत निकला (§9)।
- इस report में कोई नया backtest नहीं चला। हर "काम करेगा या नहीं" वाला सवाल एक pre-registered study (§7) से ही तय होगा।

**सीधा जवाब, एक line में:**
- आपकी बात का **आधा हिस्सा सही है**: candles में भीड़ का व्यवहार दिखता है, और हमने उसे गणित से नापा भी है।
- पर **आधा ग़लत है**: candle **सबको** दिखती है, जिसमें हज़ारों तेज़ machines भी हैं। इसलिए candle से emotion पढ़ना अपने-आप में "5% वाला" फ़ायदा नहीं है।
- असली फ़ायदा तीन जगह से आ सकता है:
  1. ऐसा data जो भीड़ की **positioning** सीधे दिखाता है (सिर्फ़ दाम नहीं);
  2. सही timeframe, जहाँ खर्च फ़ायदे को न खा जाए;
  3. वह जोखिम उठाने का अनुशासन जो भीड़ से emotions की वजह से नहीं होता।

---

## 1. आपके हर दावे की जाँच

| आपका दावा | फ़ैसला | सबूत |
|---|---|---|
| "हर minute की candle लोगों के emotions बताती है" | **आंशिक सही** | Candle (OHLCV) उस minute के **सारे** orders का नतीजा है: इंसान, bots, market makers, arbitrage और liquidation engines। Emotion उसका एक हिस्सा है, पूरा नहीं। एक minute पर ज़्यादातर volume machines का माना जाता है। "60–80% bots" जैसे आँकड़े हर जगह घूमते हैं, पर उनका **कोई primary स्रोत नहीं मिला** (§10 में स्रोत), इसलिए मैं कोई पक्का % नहीं दे रहा |
| "90–95% लोग candle/technical देखकर trade करते हैं" | **अप्रमाणित** | ऐसा कोई सर्वे या study नहीं मिला जो यह % नापे। जो मिला: Binance का औसत trade size छोटा है, यानी retail वाला venue (Kaiko/ForkLog, 2020 data) |
| "95% हारते हैं, 5% अलग सोचते हैं" | **इसका पहला हिस्सा सबूत के क़रीब है** | Taiwan (Barber, Lee, Liu, Odean; 1992–2006): **1% से कम** day traders लगातार, भरोसे से fees के बाद कमाते हैं; हर साल ~80% हारते हैं। Brazil (Chague, De-Losso, Giovannetti 2020): 300 से ज़्यादा दिन trade करने वालों में **97% हारे** (1,504/1,551)। ये stocks/futures के हैं, crypto के नहीं। (कई जगह secondary स्रोत; मूल papers पढ़ना बाकी, §10) |
| "Market इन्हीं emotions से चलता है" | **आंशिक सही** | Short-term में भीड़ का व्यवहार (overreaction, herding, forced liquidations) दाम हिलाता है। Long-term में liquidity, macro, बड़े players और ख़बरें भी उतनी ही बड़ी वजहें हैं |
| "Emotions गणित से पकड़ लें तो 95% से अलग माइंडसेट मिल जाएगा" | **ग़लत, अगर सिर्फ़ candle से** | Candle public है। Emotion के जो pattern candle में हैं, उन्हें दुनिया की हर quant firm पहले से नापती है। जो pattern बचते हैं, वे या तो **खर्च से छोटे** हैं (हमारा 5m–30m का नतीजा, §2) या **बहुत असहज** हैं (बड़े trends, crash hedge)। "5% वाला" फ़र्क ज़्यादातर अनुशासन, खर्च, और ऐसे data से आता है जिसे भीड़ नहीं देखती |

---

## 2. हमने emotion को पहले ही गणित से नापा है: हमारे अपने verified नतीजे

**यह सबसे अहम हिस्सा है।** आप जो "emotion पकड़ना" चाहते हैं, उसका बड़ा हिस्सा हम पिछले 10 दिनों में pre-registered studies में नाप चुके हैं:

| Emotion (behavioral finance का नाम) | Candle में कैसे दिखता है | हमने क्या नापा | नतीजा | स्रोत |
|---|---|---|---|---|
| **घबराहट या लालच में ज़्यादा प्रतिक्रिया** (overreaction) | 5m–30m पर तेज़ चाल फिर उलट जाती है | RSI/Bollinger जैसी "उलटी" entries random से बेहतर; trend entries random से बदतर | **Timing असली है (p < 0.005)**, पर taker खर्च (~0.108% round trip) के बाद हर cell घाटे में। Maker खर्च पर कुछ long cells positive थे, पर आख़िरी साल में negative, और adverse selection नापा नहीं गया | TFX/TFX-S/DISC (`RESEARCH_COLLECTIVE_BRAIN_SATURATION_20_OCT_2026.md`) |
| खर्च बनाम चाल | — | 5m पर cost = median चाल का **68%**, 15m पर **38%** | छोटे TF पर emotion का signal खर्च में डूब जाता है | `MASTER_INTEGRATED_RESEARCH_17_OCT_2026.md` line 85–86 |
| **धीरे-धीरे यक़ीन होना और भीड़ का पीछे आना** (underreaction, herding) | 4h–1D पर trend चलता रहता है | Trend families | **कमाई कुछ बड़े trades से** (Sleeve A: 34% win, सबसे अच्छे 10% trades = कमाई का 155%) | TFX-S; audit भाग 1 §4.5 |
| **डर से ज़्यादा बेचना** (capitulation) | 8h–1D पर oversold | RSI long | Robust candidate → N1 का B sleeve (70% win) | TFX-S |
| **भीड़ का एक तरफ़ भागना** | Cross-section में जीतने वाले coins | 1D XS momentum | 7/7 साल positive → N1 का D sleeve | DISC |
| **Crash का डर** | Alts का गिरना | Alt trend-short | हर बड़े crash में कमाया → N1 का C sleeve (crash hedge) | DISC |
| Volume का अचानक बढ़ना | Volume spike | AI features | सबसे लगातार factor | Master research D2 |
| Double top/bottom | Chart pattern | S5 | उल्टी दिशा का अगला कदम 3–9 pp ज़्यादा बार; यह विवरण है, अकेले पर trade कमज़ोर | S5, master line 99 |
| **Candlestick patterns** (doji, engulfing…) | — | S5 | **Out-of-sample नकारात्मक** | Master line 129 |
| 15m/5m candles को AI में जोड़ना | — | AI | AUC में सिर्फ़ **+0.0008** | Master line 124 |
| Funding/premium extreme ("भीड़ बहुत ज़्यादा long है") पर उल्टा short | — | DISC | **बुरी तरह fail** | DISC |
| AI से "बुरे" trades छोड़ना (emotion filter) | — | T18 | Calmar गिरा | audit भाग 1 §4.4 |

**निष्कर्ष §2:**
- (1) Candle में emotion **है**, और हमारे system के चारों N1 sleeves (A trend, B oversold, C crash, D momentum) असल में चार अलग "भीड़ के व्यवहार" ही हैं।
- (2) छोटे TF पर emotion असली है, पर **खर्च से छोटा** है।
- (3) Candle के ऊपर और candle patterns या AI जोड़ने से आज तक फ़ायदा नहीं हुआ।

**बाहरी studies भी यही कहती हैं:**
- 68 candlestick patterns, 23 coins पर: "cryptocurrency trading में बहुत कम काम के" (IEEE 2021)।
- US stocks पर 28 candlestick signals: bootstrap में कोई predictive शक्ति नहीं (Marshall, Young, Rose)।

---

## 3. Candle से बेहतर "emotion data": भीड़ की positioning

Candle बताती है कि **क्या हुआ**: दाम और volume। Positioning बताती है कि **भीड़ ने किस तरफ़ दाँव लगाया है और कितने दबाव में है**। Emotion का यही ज़्यादा सीधा माप है:

| माप | क्या दिखाता है (emotion) | कहाँ से |
|---|---|---|
| Open interest (OI) का बदलाव | नया पैसा आ रहा है या भाग रहा है | Binance futures |
| Top-trader long/short (accounts / positions) | बड़े traders की दिशा | Binance futures |
| Global long/short account ratio | आम (retail) accounts की दिशा | Binance futures |
| Taker buy/sell volume ratio | कौन घबराकर बाज़ार भाव पर ख़रीद/बेच रहा है | Binance futures, aggTrades |
| Funding rate, premium | Long पक्ष कितना भीड़ भरा है | पहले से हमारे पास |
| Liquidations | ज़बरदस्ती बेचना/ख़रीदना (panic का चरम) | Live stream; पुराना dump बंद (§4) |
| Order book depth का असंतुलन | ख़रीदने/बेचने वालों की दीवारें | bookDepth |
| Options implied vol / skew | पैसे देकर ख़रीदा गया डर | M4 collector (हमारे पास, forward) |

**Research क्या कहती है:**
- **Retail futures positioning:** Dunbar & Owusu-Amoako (2023) के अनुसार, speculative retail traders की net-short positioning का बदलाव crypto returns का statistically significant predictor है, attention, sentiment और पिछले returns को control करने के बाद भी। (सिर्फ़ abstract पढ़ा; horizon, sample और दिशा जाँचनी बाकी।)
- **Sentiment:** crypto के लिए बनाया गया lexicon daily returns का **out-of-sample R² ~3.15%** समझाता है (Chen, Guo, Renault; working paper)। Fear & Greed index पर studies छोटे samples वाली और mixed हैं।
- **Order-flow imbalance (Cont, Kukanov, Stoikov 2014):** यह उसी पल की price change का बड़ा हिस्सा समझाता है, 50 ms से 5 minute तक। पर यह **साथ-साथ** का रिश्ता है, आगे की भविष्यवाणी नहीं। इसका फ़ायदा execution में है, direction में नहीं।
- **VPIN** ("toxic flow"): विवादित। Andersen & Bondarenko के अनुसार इसकी volatility forecast की शक्ति classification की गलती से आती है, और volatility व trading intensity को control करने पर कुछ नहीं बचता।
- **Liquidation cascades** (जैसे 10-10-2025, ~$20 bn): हाल के preprints में pre-cascade warning signals "हर event में अलग" निकले, यानी कोई एक भरोसेमंद संकेत नहीं।
- **Crypto intraday:** Bitcoin में पहले आधे घंटे की return आख़िरी आधे घंटे की return बताती है। इसका दूसरा पहलू: एक 2026 preprint के अनुसार algorithmic trading की हर 15-minute boundary पर पहले आधे घंटे में short-run reversal होता है, जो 8–12 घंटे में positive हो जाता है। 3,600 coins पर daily reversal illiquid coins की वजह से है, जबकि बड़े coins में momentum है।
- **हमारा अपना सबूत:** funding/premium extreme पर contrarian short fail हुआ (§2)। यानी "भीड़ बहुत long है → short करो" जैसा सीधा नियम **काम नहीं किया**।

**निष्कर्ष §3:**
- Positioning data emotion का ज़्यादा सीधा और कम इस्तेमाल हुआ माप है। Research में इसके predictive होने के संकेत हैं।
- पर कोई भी ऐसा साफ़, cost के बाद, survivorship-free सबूत नहीं मिला कि यह crypto में अकेले trade करके पैसा देता है।
- इसलिए इसे सिर्फ़ pre-registered test से ही साबित करना होगा।

---

## 4. आज की data जाँच (VM, 22-10-2026; public `data.binance.vision`, HTTP status)

| Data | उपलब्ध? | कब से | ख़ास बात |
|---|---|---|---|
| `futures/um/daily/metrics` (5m: OI, OI value, top-trader L/S accounts और positions, global L/S, taker buy/sell ratio) | ✅ | **BTC: 2020-09** (2020-08 = 404); **SOL, DOGE: 2021-12** (2021-09 = 404); ETH 2021-06 = 404 | **डूबे coins भी हैं:** FTT 2022-10 ✅, LUNA 2022-04 ✅। यानी survivorship-free। एक दिन = 288 rows (5 minute) |
| `aggTrades` (हर trade, buyer/seller कौन था) | ✅ | BTC 2020-01 भी ✅ | Order-flow imbalance ख़ुद बनाया जा सकता है (data बहुत बड़ा) |
| `bookDepth` (±1…5% पर depth और notional) | ✅ | 2023-06 ✅, 2022-01 ❌ | ~28,800 rows/दिन |
| `liquidationSnapshot` | ❌ (404) | — | Binance ने बंद किया (preprint भी यही कहता है)। सिर्फ़ live stream बचा |
| Binance API (`openInterestHist`, ratios) | सिर्फ़ 30 दिन | — | हमारा FR2 recorder 19-10 से इन्हें 5m पर जमा कर रहा है: पक्का forward out-of-sample |

**मतलब:**
- Alts पर ~4.8 साल (2021-12 → आज) और BTC पर ~6 साल का **5-minute crowd positioning data**, डूबे coins समेत, मुफ़्त और public है।
- अब तक हमारी किसी research ने इसे इस्तेमाल नहीं किया।
- यही "वह data जो 95% लोग नहीं देखते" का सबसे ठोस उम्मीदवार है: charts पर यह आम तौर पर नहीं दिखता।

---

## 5. इसका असली मतलब: "5% वाला माइंडसेट" कहाँ से आता है

सबूतों से तीन स्रोत निकलते हैं। इनमें से कोई भी "candle को बेहतर पढ़ना" नहीं है:

**1. अनुशासन और असहजता (behavioral premium):**
- Trend की कमाई कुछ बड़े trades से आती है, और 66% trades हारते हैं।
- भीड़ हारने वाले trades से घबराकर system छोड़ देती है, और बड़े winners जल्दी बेच देती है (disposition effect)।
- हमारा system यह emotion नहीं करता। **यही हमारा 5% वाला हिस्सा पहले से है।**

**2. खर्च और timeframe का चुनाव:**
- भीड़ 1m–15m पर trade करती है, जहाँ cost चाल का 38–68% है।
- हम 4h–1D पर हैं। वहाँ वही emotion (herding) खर्च से बड़ा है।

**3. ऐसा data या व्यवहार जो भीड़ नहीं देखती:**
- Positioning (§3–4) और cross-section (कौन-सा coin सबसे ज़्यादा भीड़ भरा है)।
- यह **अभी अप्रमाणित** है। §7 इसी का test है।

**Emotion पकड़ने से सबसे भरोसेमंद फ़ायदा नई कमाई नहीं, बल्कि loss और DD घटाना हो सकता है:**
- भीड़ के चरम (बहुत ऊँचा OI और funding के साथ crowded longs) liquidation cascade का ख़तरा बढ़ाते हैं।
- वहाँ size घटाना या hedge बढ़ाना, यानी risk का filter, ज़्यादा यथार्थवादी उपयोग है।
- पर ध्यान रहे: AI से trades छोड़ना (T18) और funding contrarian पहले fail हुए हैं। इसलिए यह भी test से ही तय होगा।

---

## 6. क्या कर सकते हैं: तीन रास्ते, ईमानदार उम्मीद के साथ

| रास्ता | क्या | उम्मीद (सबूत से) | ख़तरा |
|---|---|---|---|
| **R-A: Emotion meter** (सिर्फ़ जानकारी, trade नहीं) | Hourly "भीड़ की हालत": candle features (wick/body ratio, volume surprise, realized vol jump, short-term autocorrelation) + positioning (OI बदलाव, L/S ratios, taker ratio, funding) का z-score composite। Dashboard और alert | पक्का बनेगा; trading पर असर शून्य | "चार्ट देखकर फ़ैसला" वाली आदत, जो discipline तोड़ती है। इसे सिर्फ़ जानकारी मानें |
| **R-B: Crowding cross-section sleeve** (नया, अलग edge) | हर 4h/1D: coins को "crowding score" से rank करें (retail बहुत long, top traders उलटे, OI तेज़ बढ़ा, funding ऊँचा)। सबसे कम crowded long, सबसे ज़्यादा crowded short, market-neutral | Literature में संकेत (retail positioning predictive); हमारा funding-contrarian fail हुआ, पर वह market-wide और सिर्फ़ एक माप पर था। **अनिश्चित, शायद छोटा** | Shorts की cost और squeeze; overfitting; trials की गिनती |
| **R-C: Risk filter** (मौजूदा sleeves पर) | Crowding या cascade का ख़तरा ऊँचा हो तो N1/1D का gross या size घटाएँ | DD घटा सकता है; पर पिछले filters (T18, K2 heat cap) ने Calmar घटाया | बड़े winners कटना (भाग 1 §4.4 का सबक) |

**मेरी सलाह का क्रम:**
1. R-A बनाएँ; खर्च लगभग नहीं।
2. फिर R-B का **एक** pre-registered trial (§7)।
3. R-C तभी, जब R-B में positioning का असर साबित हो।
4. Minute-स्तर पर scalping कभी नहीं (§2 का सबूत)।

---

## 7. Pre-registered study का design: EMO-1 (lock से पहले का draft, अभी नहीं चलाया)

**Data (EMO-0):**
- `data.binance.vision` metrics (5m) + 1h perp klines + funding। Universe: point-in-time liquid USDT perps, **डूबे coins समेत**।
- हर file का SHA manifest।
- 2021-12 से पहले का data सिर्फ़ BTC के लिए है, इसलिए study 2021-12 से शुरू।

**Features** (हर coin, हर 4h close पर, सिर्फ़ पिछला data):
- OI का 1d/3d बदलाव;
- top-trader और global L/S ratio, और उनका अंतर ("smart बनाम retail");
- taker buy/sell ratio का 1d औसत;
- funding का 3d औसत;
- candle emotion: wick/body, volume surprise, 1d realized vol का बदलाव।

हर feature का cross-sectional rank निकाला जाए। इन ranks के बराबर-weight औसत से एक **crowding score** बनता है: पहले से तय, कोई fitting नहीं।

**Portfolio:**
- 4h पर rebalance;
- सबसे कम crowded 20% long, सबसे ज़्यादा crowded 20% short;
- beta-neutral;
- taker 0.054% + spread;
- असली funding।

**Windows:**
- dev 2021-12 → 2024-12;
- **holdout 2025-01 → 2026-09**, जो एक ही बार खुलेगा;
- फिर forward: FR2 data (19-10-2026 से) और paper।

**Gates (सब ज़रूरी):**
- (1) holdout पर net Sharpe > 0, और block-bootstrap CI का निचला सिरा > 0;
- (2) existing ECO के साथ daily correlation < 0.3;
- (3) ECO + EMO का Calmar ECO अकेले से बेहतर, dev और holdout दोनों में;
- (4) DSR, उस sensitivity table के साथ जिसमें SR variance 0.01, 0.05 और 0.10 हो (audit भाग 1 §1.1 का सबक);
- (5) shuffled-feature control fail हो, यानी signal सच में features से आए।

**Trial budget:**
- यह ECO का trial नहीं, एक नया research family है।
- **1 primary + 2 robustness** (rebalance 1D; केवल positioning features, बिना candle features)।
- Trial registry में दर्ज होगा।

**Verifier:** एक स्वतंत्र script features और returns को दोबारा गिनेगी (हमारा V-pattern)।

**उम्मीद, ईमानदारी से:** पहले से बताना ठीक नहीं, पर prior **कम-से-मध्यम** है:
- funding-contrarian fail हुआ;
- candle/AI filters fail हुए;
- literature में संकेत हैं, पर cost के बाद का साफ़ सबूत नहीं।

अगर gate पास नहीं हुआ, तो वही नतीजा भी सच्चा ज्ञान है, और emotion meter (R-A) तब भी काम का रहेगा।

---

## 8. फ़ायदा क्या होगा (अगर काम किया), और spot/futures पर असर

| अगर | फ़ायदा | सबूत की तरह |
|---|---|---|
| R-B gates पास करे | एक नया, कम correlation वाला sleeve | E-2 में दो अलग systems मिलाने से DD 22% → 11% हुआ था (Calmar 3.36 → 5.98); तीसरा अलग edge सबसे बड़ा lever है (audit भाग 1 §4.3) |
| R-C साबित हो | बड़े crashes में कम DD | अभी अप्रमाणित |
| सिर्फ़ R-A | फ़ैसलों में साफ़ समझ, alerts | Trading पर कोई दावा नहीं |

**Spot या futures:**
- Positioning data futures market से आता है, पर emotion **पूरे market** का है। इसलिए signal spot और futures दोनों पर लागू है।
- Execution: longs spot पर हो सकते हैं (हमारा X2 सबक), shorts सिर्फ़ futures पर।
- Futures पर funding लगती है; spot पर fee ज़्यादा है (0.085% बनाम 0.054%)।

---

## 9. इस report का audit (loop: लिखा → जाँचा → सुधारा)

| # | जाँच | नतीजा |
|---|---|---|
| A1 | "90–95% technical से trade करते हैं": कोई स्रोत है? | **नहीं मिला** → "अप्रमाणित" लिखा |
| A2 | "60–80% volume bots": स्रोत? | सिर्फ़ vendor pages, कोई primary स्रोत नहीं → कोई % नहीं दिया |
| A3 | Master research line 133 कहती है "Day trading ~97% घाटे में (Taiwan, Brazil)" | **हमारे अपने दस्तावेज़ में छोटी गलती:** 97% Brazil का है। Taiwan का आँकड़ा है "1% से कम लगातार कमाते हैं, हर साल ~80% हारते हैं"। यहाँ सही लिखा; master research के errata के लिए दर्ज |
| A4 | Positioning data सच में पुराना उपलब्ध है? | **VM से HTTP जाँच की** (§4): metrics BTC 2020-09+, alts 2021-12+, डूबे FTT/LUNA भी; aggTrades ✅; bookDepth 2023+; liquidationSnapshot ❌ |
| A5 | OFI "predict" करता है? | नहीं, वह साथ-साथ का रिश्ता है → execution वाली श्रेणी में रखा |
| A6 | VPIN | विवादित → उम्मीदवार नहीं बनाया |
| A7 | हमारे अपने नतीजों के line references | `RESEARCH_COLLECTIVE_BRAIN…` lines 18–37; master research lines 85–86, 99, 124, 129: दोबारा पढ़कर मिलाए |
| A8 | Dunbar & Owusu-Amoako और Chen–Guo–Renault | सिर्फ़ abstracts पढ़े → "पढ़ना बाकी" लिखा; EMO-1 का design इन पर निर्भर नहीं, सिर्फ़ प्रेरणा है |
| A9 | Gap: options (डर का बाज़ार भाव) | M4 collector सिर्फ़ forward data देता है → R-A में जोड़ा, EMO-1 में नहीं (इतिहास नहीं है) |
| A10 | Gap: on-chain / social sentiment | हमारे पास data नहीं, और बाहरी स्रोत सशुल्क या अस्थिर हैं → दायरे से बाहर, दर्ज |
| A11 | Gap: liquidations का इतिहास | Binance dump बंद → सिर्फ़ forward (live stream) recorder से; EMO-1 में नहीं |
| A12 | Gap: maker execution पर 5m–30m reversal | Adverse selection नापे बिना नहीं; यह पहले से "D6: सिर्फ़ execution" में है |
| A13 | क्या यह report कोई trading दावा करती है? | **नहीं।** हर "काम करेगा" वाली बात EMO-1 के gates पर टिकी है |

**Audit का निचोड़:** 3 दावे बदले (A1, A2, A3), 4 gaps दर्ज हुए (A9–A12), और data की उपलब्धता असली जाँच से पक्की हुई। बचे हुए gaps जानबूझकर दायरे से बाहर हैं, क्योंकि उनका data हमारे पास नहीं है।

**"Zero gap" पर ईमानदार बयान:** research के स्तर पर उपलब्ध सबूत saturate हो गए हैं: नए searches वही studies दोबारा दिखाते हैं। असली जवाब ("क्या यह पैसा देता है") सिर्फ़ EMO-1 देगा।

---

## 10. स्रोत

- [Barber, Lee, Liu, Odean: individual investors' losses (RFS 2009, PDF)](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/justhowmuchdoindividualinvestorslose_rfs_2009.pdf)
- [Day trading review (secondary, TradingView)](https://my.tradingview.com/chart/EURUSD/pJsnrpJF-The-Ineffectiveness-of-Day-Trading-A-Critical-Review-of-Empiric)
- [Kaiko: whale vs retail trade size](https://blog.kaiko.com/an-analysis-of-whale-and-retail-trade-size-and-direction-7db548879292)
- [ForkLog on Kaiko whale study](https://forklog.com/en/on-which-exchanges-do-bitcoin-whales-show-the-most-activity/)
- [Kraken: crypto AI trading bots (algorithmic share context)](https://www.kraken.com/learn/crypto-ai-trading-bots)
- [Do Candlestick Patterns Work in Cryptocurrency Trading? (IEEE 2021)](https://ieeexplore.ieee.org/document/9671826)
- [Marshall, Young, Rose: candlestick market timing](https://ideas.repec.org/a/ris/jofitr/0834.html)
- [Cont, Kukanov, Stoikov: price impact of order book events](https://arxiv.org/abs/1011.6402)
- [Order book imbalance in crypto (Towards Data Science)](https://towardsdatascience.com/price-impact-of-order-book-imbalance-in-cryptocurrency-markets-bf39695246f6)
- [Andersen & Bondarenko on VPIN (Review of Finance)](https://ideas.repec.org/a/oup/revfin/v19y2015i1p1-54..html)
- [Dunbar & Owusu-Amoako: crypto returns and trading behavior](https://digitalcommons.uncfsu.edu/college_business_economics/314)
- [Chen, Guo, Renault: crypto sentiment and return predictability](https://papers.ssrn.com/abstract=3398423)
- [Fear and Greed vs Bitcoin prices (Economics & Finance 2023)](https://ideas.repec.org/a/eee/ecofin/v67y2023ics1062940823000475.html)
- [Sentiment in bubble regimes (HU Berlin)](https://www.wiwi.hu-berlin.de/de/forschung/irtg/results/discussion-papers/discussion-papers-2017-1/irtg1792dp2019-016.pdf)
- [Bitcoin intraday time-series momentum](https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/)
- [The Quarter-Hour Effect in crypto futures (2026 preprint)](https://arxiv.org/pdf/2607.09426)
- [Short-term reversal and momentum in crypto](https://earsiv.medeniyet.edu.tr/items/23a96c9f-3952-4bdf-aec5-abafb3aaab70)
- [Liquidation cascade early-warning (2026 preprint)](https://arxiv.org/pdf/2607.27070)
- [BitMEX: State of Crypto Perps 2025](https://www.bitmex.com/blog/site-announcement/state-of-crypto-perps-2025)
- [Binance public data: metrics file format (GitHub issue)](https://github.com/binance/binance-public-data/issues/211)

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
