# Research: Multi-timeframe "Opportunity Scanner" दिमाग (5m से 1 महीने तक) — क्या बन सकता है, क्या नहीं, और कैसे

**तारीख:** 15 अक्टूबर 2026 | **GitHub:** कुछ नहीं | **कोई trading नहीं, कोई deploy नहीं**

**आधार:**
- (A) हमारा अपना SHA256-verified Binance data;
- (B) हमारे पिछले 27 steps के verified नतीजे;
- (C) छपी हुई research, web पर जाँची गई (स्रोत आखिर में)।

**संख्याओं की files:** हर संख्या `logs/scanner_research_horizon_stats.txt` में है, और नीचे दिए code से दोबारा बनाई जा सकती है।

---

## 1. सवाल
एक ऐसा दिमाग जो लगातार scan करे, और हर timeframe (5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M) के लिए बताए:
- market ऊपर जाएगा या नीचे;
- कितना जाएगा;
- कौन-सा मौका है।

## 2. सबूत A: हर timeframe पर coin कितना हिलता है, और खर्च के बाद कमाने के लिए कितनी बार सही होना पड़ेगा
**Data:** top-20 universe के 10 सबसे आम coins (BTC, ETH, BNB, XRP, DOGE, ADA, SOL, LINK, AVAX, TRX), 2021-01 से 2026-09। Non-overlapping open→open returns।

**"ज़रूरी hit-rate":** अगर जीत और हार औसतन बराबर आकार की हों, तो खर्च निकालकर बराबरी पर आने के लिए कितने % trades सही होने चाहिए। सूत्र: 0.5 + खर्च / (2 × औसत हलचल)। 100% से ज़्यादा का मतलब है नामुमकिन।

**Binance spot fee** (binance.com से जाँची): 0.100% maker/taker। BNB से चुकाने पर 0.075%।
- आने-जाने का खर्च: BNB के साथ 0.15%, बिना BNB 0.20%। इसमें spread/slippage नहीं जुड़ा।
- हमारी research में 0.25% प्रति fill (0.50% round-trip) माना गया है, जो सावधानी वाला अनुमान है।

| Timeframe | Samples | आम हलचल (median) | औसत हलचल | 0.5% से बड़ी हलचल | ज़रूरी hit-rate @0.50% | @0.20% | @0.15% |
|---|---|---|---|---|---|---|---|
| 5m | 60.4 लाख | 0.10% | 0.18% | 6.5% बार | **नामुमकिन (192%)** | **नामुमकिन (107%)** | 92.6% |
| 15m | 20.1 लाख | 0.18% | 0.31% | 17% | नामुमकिन (132%) | 82.6% | 74.5% |
| 30m | 10.1 लाख | 0.26% | 0.43% | 27% | नामुमकिन (108%) | 73.2% | 67.4% |
| 1h | 5.0 लाख | 0.36% | 0.61% | 38% | 91.3% | 66.5% | 62.4% |
| 4h | 1.26 लाख | 0.73% | 1.22% | 62% | 70.5% | 58.2% | 56.1% |
| 1d | 20,980 | 2.03% | 3.17% | 85% | 57.9% | 53.2% | 52.4% |
| 1w | 2,990 | 5.64% | 8.71% | 95% | 52.9% | 51.1% | 50.9% |
| 1M | 690 | 12.1% | 22.4% | 98% | 51.1% | 50.4% | 50.3% |

**मतलब:**
- 5m–30m पर, सबसे कम खर्च में भी, AI को 67–93% बार सही होना पड़ेगा। Market prediction में ऐसी accuracy का कोई verified सबूत नहीं है। हमारी सबसे अच्छी skill AUC 0.57 के आसपास है, यानी मोटे तौर पर 53–55% सही।
- यह कमज़ोरी AI की नहीं है। यह गणित है: छोटे timeframe पर हलचल खर्च के मुकाबले बहुत छोटी होती है।

## 3. सबूत B: दिशा predictable है या सिर्फ हलचल का आकार?
लगातार दो returns का आपसी मेल (correlation), वही 10 coins:

| Timeframe | दिशा: अभी ऊपर, तो अगली बार भी ऊपर? | आकार: अभी बड़ी हलचल, तो अगली बार भी बड़ी? |
|---|---|---|
| 5m | −0.029 | **+0.414** |
| 15m | −0.002 | **+0.394** |
| 30m | −0.024 | **+0.370** |
| 1h | −0.009 | **+0.336** |
| 4h | −0.011 | **+0.301** |
| 1d | −0.034 | **+0.231** |
| 1w | **+0.112** (coin के हिसाब से −0.004 से +0.303) | +0.154 |

**मतलब:**
- 5m से 1d तक, अकेले coin की **दिशा** का पिछले return से रिश्ता लगभग शून्य है (−0.03 से 0)।
- पर **हलचल का आकार** काफी predictable है (0.23–0.41)। Market "शांत" रहेगा या "तूफानी", यह पहले से दिखता है; ऊपर या नीचे, यह नहीं।
- 1 हफ्ते पर हल्का momentum दिखता है (+0.11)। यह छपी research से मेल खाता है (Liu & Tsyvinski, नीचे)। पर samples कम हैं (हर coin के लगभग 300 हफ्ते), और coins के बीच फर्क बहुत है।
- **सावधानी:** 5m पर कई candles में कीमत बिल्कुल नहीं बदलती, इसलिए "same-sign" वाला आँकड़ा नहीं दिखाया। Correlation इससे प्रभावित नहीं होता।

## 4. सबूत C: हमारे अपने दिमाग पहले ही यही दिखा चुके हैं
| Step | सवाल | Skill | पैसे में |
|---|---|---|---|
| 14 | 1 दिन ऊपर/नीचे (छोटे coins) | AUC 0.530 | हर trade +0.57%, खर्च 0.50% → **fail** |
| 17, 20, 21 | Market ऊपर/नीचे/crash | नहीं, या पैसे में उल्टा | **fail** |
| 24 R4 | अगले 4 घंटे में कौन आगे (बड़े coins) | AUC 0.545 (असली) | हर trade **−0.21%**, $10k → $49 |
| 23/24 | अगले 1 दिन में कौन आगे (बड़े coins) | **AUC 0.565–0.568**, 2018–19 में 0.546 | **pass**, हर trade +1.1–1.2% |
| 26 | कौन-सा coin 24 घंटे में 5% से ज़्यादा गिरेगा | **AUC 0.672** | पैसा नहीं बढ़ा: इसने volatility पहचानी, दिशा नहीं |
| 25 | 15m/5m data, 1 दिन वाले सवाल में | +0.0008 AUC | फर्क नहीं |

**सबक:**
1. AI "किसके मुकाबले कौन बेहतर" (relative) सीख पाता है; "ऊपर या नीचे" (absolute) नहीं।
2. AI "कितनी हलचल होगी" अच्छे से सीखता है।
3. जितना छोटा timeframe, उतना ज़्यादा खर्च पूरी कमाई खा जाता है।

## 5. सबूत D: छपी research (web पर जाँची)
- **Liu & Tsyvinski (Review of Financial Studies, 2021):** crypto में time-series momentum मज़बूत है। Bitcoin के weekly returns का उदाहरण दिया गया है। यह हमारे 1w वाले +0.11 से मेल खाता है।
- **बड़े बनाम छोटे coins (Fičura, Finance Research Letters 2023):** बड़े और liquid coins में weekly momentum मिला, छोटे coins में reversal। एक और अध्ययन के मुताबिक बड़े coins का momentum काफी trading cost माँगता है, और उसका ज़्यादातर alpha short positions से आता है, जो spot पर मुमकिन नहीं।
- **Zaremba et al. (2021):** छोटे coins में daily reversal मिला, जो illiquidity से जुड़ा है। सबसे बड़े coins में daily momentum दिखा।
- **Intraday (5m–1h) predictability:** 16 बड़े coins पर 2025 के एक अध्ययन के अनुसार high-frequency predictability समय के साथ बदलती रही, और ज़्यादातर समय coins unpredictable रहे।
- **Order book / order flow पर deep learning (DeepLOB आदि):** अगली mid-price दिशा का अनुमान अच्छी accuracy से हो सकता है, पर वह कुछ सेकंड का खेल है। इन अध्ययनों में खर्च के बाद मुनाफे का कोई सबूत नहीं मिला। 2025 के Bybit BTC/USDT अध्ययन के अनुसार simple models भी उतने ही अच्छे निकले।
- **Volatility forecasting:** इस पर काफी research है (HAR, GARCH, LightGBM quantile models)। Volatility, दिशा से कहीं ज़्यादा predictable है। यह हमारे सबूत B और Step 26 से मेल खाता है।

## 6. नतीजा: हर timeframe पर scanner क्या कर सकता है
| Timeframe | दिशा का अनुमान | हलचल का अनुमान | खर्च के बाद trading | Scanner में क्या भूमिका |
|---|---|---|---|---|
| 5m / 15m / 30m | ✗ (लगभग शून्य) | ✓ (मज़बूत) | ✗ (गणित से नामुमकिन) | सिर्फ execution timing और risk alarm |
| 1h | ✗ | ✓ | ✗ (R4 fail) | Execution timing, risk |
| 4h | ✗ absolute; relative कमज़ोर | ✓ | ✗ अकेले | Input data की तरह (4H R6 pass) |
| **1d** | ✗ absolute; **✓ relative (साबित)** | ✓ | **✓ (R6/R24 pass)** | **मुख्य कमाई वाला दिमाग** |
| **1w** | **हल्का momentum (research + हमारा +0.11)** | ✓ | ✓ मुमकिन (खर्च छोटा पड़ता है) | **नया परखने लायक** |
| 1M | samples बहुत कम (हर coin के लगभग 69 महीने) | ✓ | मुमकिन | सिर्फ context, test करना कठिन |

**सीधा जवाब:**
- "हर 5 मिनट में market किस दिशा जाएगा" बताने वाला भरोसेमंद दिमाग, जो खर्च के बाद कमाए, **हमारे data और छपी research दोनों के अनुसार नहीं बन सकता।**
- **पर एक "Opportunity Scanner" बन सकता है, अगर उसका काम सही बाँटा जाए:**
  - बारीक timeframes हलचल और risk बताएँ;
  - रोज़ और हफ्ते के timeframes "कौन बेहतर" बताएँ;
  - और trade सिर्फ वहाँ हो जहाँ कमाई खर्च से बड़ी हो।

## 7. Scanner के संभव design (हर एक की सबूत-स्थिति के साथ)

### Option 1: Volatility scanner → position size (सबसे ज़्यादा उम्मीद वाला नया विचार)
- **क्या:** 5m–1d data से हर coin और पूरे market की अगली हलचल का अनुमान (quantiles में, जैसे "अगले 24 घंटे में 90% मौका कि हलचल X% से कम रहे")।
- **कैसे काम आएगा:** जब अनुमानित हलचल ज़्यादा हो, तो कम पैसा लगाओ; शांत समय में ज़्यादा। इसे volatility targeting कहते हैं। यह दिशा का अनुमान नहीं, सिर्फ "कितना जोखिम" का अनुमान है।
- **क्यों उम्मीद है:**
  - हलचल का आकार साबित रूप से predictable है (0.23–0.41)।
  - Step 26 का दिमाग volatility में AUC 0.67 पर पहुँचा था।
  - Crash के समय हलचल बहुत बढ़ती है, इसलिए exposure अपने-आप घटेगा।
  - Position size ही अब तक का अकेला साबित तरीका है; यह उसे "smart" बनाता है।
- **ईमानदार सीमा:**
  - Crash अचानक भी आते हैं, और तब हलचल बाद में बढ़ती है।
  - यह "market timing" से अलग है, पर पूरी तरह नहीं।
  - इसलिए random-size control से तुलना ज़रूरी है।
- **Test (Step 28):** R24/M_AI3 system में हर दिन invest fraction = target vol / अनुमानित vol, ऊपरी सीमा 100%। Pass तभी, जब ये तीनों सच हों, 2021–26 और 2018–19 दोनों पर:
  - बराबर औसत exposure वाले fixed-size system से बेहतर Calmar;
  - उससे कम गिरावट;
  - random exposure से बेहतर।

### Option 2: Weekly (1w) relative/momentum scanner
- **क्या:** "अगले हफ्ते बड़े coins में कौन आगे रहेगा", और BTC बनाम altcoins।
- **क्यों:** हफ्ते पर हलचल (औसत 8.7%) खर्च से बहुत बड़ी है, momentum के सबूत हैं (research और हमारा +0.11), और trades कम होंगे।
- **सीमा:** samples कम हैं (2021–26 में लगभग 300 हफ्ते); 2018–19 वाले लगभग 100 हफ्ते confirm के लिए। Spot पर short नहीं हो सकता।
- **Test (Step 29):** Step 23 जैसा design, weekly horizon पर।

### Option 3: Execution scanner (5m/15m का सही इस्तेमाल)
- **क्या:** रोज़ के फैसले के बाद, अगले कुछ घंटों में खरीदने या बेचने का बेहतर पल चुनना। उदाहरण: अचानक गिरावट (5m spike) के बाद limit order।
- **क्यों:** बारीक data दिशा नहीं बताता, पर spread और हलचल बताता है। इससे खर्च घट सकता है, और खर्च ही हमारी सबसे बड़ी कमज़ोरी है: 0.25% → 0.40% पर कमाई $201k से $62k।
- **Test:** पहले testnet पर limit बनाम market orders का असली खर्च नापना। Backtest में limit fills का अंदाज़ा भरोसे लायक नहीं होता, इसलिए असली नाप ज़रूरी है।

### Option 4: "Probability map" dashboard (सिर्फ जानकारी, trading नहीं)
- **क्या:** हर coin और हर timeframe के लिए:
  - P(ऊपर), जो ईमानदारी से ~50% के आसपास दिखेगा;
  - हलचल की range (quantiles);
  - relative rank।
- **फायदा:** आपको दिखेगा कि market अभी शांत है या तूफानी, और कौन-से coins relative रूप से मज़बूत हैं।
- **शर्त:** हर अनुमान forward log में लिखा जाएगा, और calibration जाँचा जाएगा: "70% कहा, तो क्या 70% बार हुआ?"
- **ख़तरा:** dashboard पर 50–53% वाले अनुमान देखकर हाथ से trade करने का मन होगा, और खर्च वही नुकसान दोहराएगा।

### Option 5: Futures data से risk alarm (सिर्फ जानकारी, आपके नियम के अनुसार)
- **क्या:** funding rate, open interest का अचानक बदलना, liquidation जैसे संकेत (data/futures_info पहले से है)।
- **स्थिति:** Step 10 में futures features थे, पर बाद के core brain से हटाए गए, क्योंकि यह data हर coin के लिए नहीं है। इसलिए यह सिर्फ बड़े coins के risk alarm के रूप में परखा जा सकता है। अभी तक कोई सबूत नहीं है।

### Option 6: 5m–1h की directional trading (नहीं करना चाहिए)
- सबूत A, B और C (R4), तीनों के अनुसार spot पर retail fee के साथ यह नुकसान का रास्ता है।
- यह सिर्फ market-making setup (maker rebate, बहुत तेज़ execution, order book data) में मुमकिन है, जो हमारे लक्ष्य (free data, spot) के बाहर है।

## 8. लगातार चलने वाले scanner का ढाँचा (अगर Options 1–4 पास हों)
1. **Data:**
   - Binance public REST (और बाद में websocket), सिर्फ बंद हो चुकी candles: 5m, 15m, 1h, 1d।
   - हर fetch का raw backup और SHA रखा जाएगा, जैसे अभी के forward logger में है।
   - 30m, 4h, 1w और 1M candles इन्हीं से बनेंगी, और 1d से मिलाकर जाँची जाएँगी (cross-check)।
2. **Features:** वही verified functions (Steps 9, 23, 24, 25)। हर feature "भविष्य न देखने" वाले truncation test से गुज़रेगा।
3. **Models (हर एक अपने काम का):**
   - Vol model: 5m → 1d horizons, quantile outputs।
   - Relative model: 1d (R24, पहले से), 1w (नया)।
   - Execution model, अगर Option 3 पास हो।
4. **Schedule:**
   - Vol/risk scan हर 5–15 मिनट (सस्ता compute)।
   - Relative ranking दिन में एक बार (00:00 UTC), हफ्ते में एक बार (weekly)।
   - Model re-training महीने में एक बार, जैसे अभी।
5. **Log और निगरानी:**
   - हर prediction hash-chained ledger में लिखी जाएगी।
   - Calibration और AUC की rolling जाँच होगी, और skill गिरे तो alarm (Step 16 protocol जैसा)।
6. **Machine:** इस PC पर हो सकता है (4 cores, 8 GB RAM)।
   - 5m scan हल्का है, 300 coins का fetch लगभग 1 मिनट।
   - Training भारी है (Step 24 में लगभग 2 घंटे)। उसे रात में चलाना होगा।
   - PC sleep न हो, यह ज़रूरी है ("Allow wake timers" अभी भी "Important only" पर है)।

## 9. सुझाया क्रम (हर step पहले जैसे अनुशासन में: lock → run → verifier → report)
| क्रम | काम | क्यों पहले |
|---|---|---|
| 1 | Forward logger में 4H R6, 1h R24 और M_AI3 50% paper portfolio | साफ सबूत सिर्फ यहीं से आएगा; समय लगता है, इसलिए जल्दी शुरू हो |
| 2 | **Step 28: Volatility scanner → position size** (Option 1) | गिरावट हमारी सबसे बड़ी समस्या है, और यह अकेला नया विचार है जो साबित predictable चीज़ पर टिका है |
| 3 | Step 29: Weekly relative/momentum (Option 2) | खर्च के हिसाब से सबसे सुरक्षित timeframe, और research का समर्थन |
| 4 | Testnet पर असली खर्च, limit बनाम market (Option 3) | खर्च हर नतीजे को सबसे ज़्यादा हिलाता है |
| 5 | Probability-map dashboard (Option 4) | सिर्फ जानकारी के लिए, तब जब ऊपर वाले हिस्से तैयार हों |
| ✗ | 5m–1h directional trading | सबूत के आधार पर नहीं करना |

## 10. जो वादा नहीं किया जा सकता
- कोई भी दिमाग "हर 5 मिनट में market कहाँ जाएगा" भरोसे से नहीं बता सकता। हमारा data यही दिखाता है: दिशा का रिश्ता −0.03 से 0 के बीच है।
- Volatility वाला scanner गिरावट घटा सकता है, पर पूरी तरह रोक नहीं सकता। यह भी test से ही पता चलेगा।
- 2021–26 और 2018–19, दोनों अब "देखे हुए" data हैं। हर नए विचार का अंतिम जज forward log है।

---

## स्रोत
- Liu & Tsyvinski, "Risks and Returns of Cryptocurrency", Review of Financial Studies 34(6), 2021: https://ideas.repec.org/a/oup/rfinst/v34y2021i6p2689-2727..html, VoxEU सार: https://voxeu.org/article/risks-and-returns-cryptocurrencies
- Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency": https://papers.ssrn.com/abstract=3379131
- बड़े coins में weekly momentum, छोटे में reversal; momentum और trading cost (search summary): https://wp.ffu.vse.cz/artkey/wps-202301-0003_impact-of-size-and-volume-on-cryptocurrency-momentum-and-reversal.php, https://jfin-swufe.springeropen.com/articles/10.1186/s40854-021-00291-9/tables/4
- Cryptocurrency return reversals (Kozlowski, Puleo, Zhou): https://fairfield.elsevierpure.com/en/publications/cryptocurrency-return-reversals/
- Short-term reversal, momentum, liquidity (Zaremba et al.): https://earsiv.medeniyet.edu.tr/items/23a96c9f-3952-4bdf-aec5-abafb3aaab70
- Bitcoin intraday time-series momentum: https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/
- Intraday predictability बदलती रहती है, ज़्यादातर unpredictable (2025): https://reference-global.com/article/10.2478/ceej-2025-0003
- Intraday HF patterns, CRIX (Petukhina, Reule, Härdle): https://arxiv.org/pdf/2009.04200
- Intraday return predictability: momentum, reversal, or both (NAJEF 2022; पूरा पाठ नहीं मिला, इसलिए इसके नतीजे नहीं लिखे): https://ideas.repec.org:443/a/eee/ecofin/v62y2022ics1062940822000833.html
- LOB deep learning बनाम simple models, Bybit BTC/USDT (2025): https://arxiv.org/abs/2506.05764
- Crypto order book पर DeepLOB (thesis): https://aaltodoc.aalto.fi/items/02ce9c54-029e-477c-9adb-3c52ff6a41b1
- Crypto volatility के probabilistic forecasts (2025): https://arxiv.org/abs/2508.15922
- Binance spot fee schedule (0.100% / BNB के साथ 0.075%): https://www.binance.com/en/fee/schedule

---

# भाग 2 (15 अक्टूबर 2026): Swing Support / Resistance — research + हमारे data पर सीधा test

## 11. सवाल (user का प्रस्ताव)
हर timeframe (5m, 15m, 30m, 1h, 4h, 8h, 12h, 1d, 1w) के swing support/resistance का AI इंजन बनाया जाए, जो पुराने और नए सारे levels याद रखे। फिर पल भर में बताए:
- support टूटा या नहीं;
- अगला support/resistance कौन-सा है।

क्या इससे Opportunity Scanner मज़बूत होगा?

## 12. छपी research क्या कहती है (web पर जाँची, सिर्फ जितना स्रोत में लिखा है)
| अध्ययन | Market | क्या मिला |
|---|---|---|
| Osler 2000 (NY Fed) | Currency, intraday | विश्लेषकों के S/R levels ने दिन के भीतर trend रुकने का अनुमान दिया, पर असर हर market और हर firm में अलग था |
| Osler 2003 (Journal of Finance) | Currency orders | Take-profit orders गोल numbers पर जमा होते हैं, इसलिए वहाँ पलटाव आता है। Stop-loss orders level के ठीक पार जमा होते हैं, इसलिए level टूटने पर तेज़ी आती है ("price cascade") |
| Chung & Bellotti 2021 (arXiv) | Intraday | जिस level पर पहले ज़्यादा बार पलटाव हुआ, वहाँ फिर पलटने का मौका ज़्यादा; समय के साथ असर घटता है |
| Tsinaslanidis 2024 (Springer) | BTC, ETH, BNB, daily 2018–22 | Support पर पलटाव resistance से ज़्यादा। तीन strategies में से दो buy-and-hold से (risk के हिसाब से) बेहतर रहीं, और वह भी तीन में से सिर्फ एक coin पर; यानी नतीजे मिले-जुले |
| Urquhart 2017 (Economics Letters) | Bitcoin | कीमतें गोल numbers पर जमा होती हैं, पर उसके बाद return में कोई खास pattern नहीं |
| Brock et al. 1992 → Sullivan, Timmermann & White 1999 | Stocks | Range-breakout नियम 1992 में फायदेमंद दिखे। पर हज़ारों नियम आज़माने से होने वाली संयोग वाली गलती (data-snooping) ठीक करने पर फायदा गायब हुआ |

**सार:** S/R का असर "बिल्कुल नहीं" भी नहीं है और "पक्का" भी नहीं; market, समय और तरीके पर निर्भर है। इसलिए अपने data पर नापना ज़रूरी था।

## 13. हमारा test (pre-registered, SHA-locked, verifier PASS)
- **Protocol:** `logs/research_sr_levels/SR_STUDY_PROTOCOL_PREREGISTERED.md`।
- **Code:** `src/research/sr_levels_study.py`।
- **Verifier:** `verify_sr_study.py` → V1–V3 PASS। 414 events candle-दर-candle दोबारा गिने गए।
- **Lock के बाद के बदलाव:** दो, दोनों सिर्फ file लिखने/पढ़ने से जुड़े, logic नहीं बदला (`CODE_CHANGES_AFTER_LOCK.md`)।

**Data:** 10 बड़े coins, 2021–26, 9 timeframes, कुल **36.4 लाख events**।

**तरीका:**
- **Swing level:** वह candle जिसका high/low आस-पास की 3+3 candles में सबसे ऊँचा/नीचा हो। यह 3 candles बाद ही पता चलता है, इसलिए भविष्य नहीं देखा गया।
- **पहली बार छूना:** जब कीमत level को पहली बार छूती है, तो देखा गया कि वह पहले 1 ATR वापस गई (**पलटी**) या 1 ATR पार गई (**टूटी**)।
- **तुलना:** उतनी ही संख्या में साधारण candles के high/low (control) से।

### नतीजा: असली swing levels पर कीमत ज़्यादा टूटती है, कम पलटती है
| Timeframe | Events (असली) | असली level पर पलटा | साधारण level पर पलटा | फर्क, %-points (95% CI) |
|---|---|---|---|---|
| 5m | 13.9 लाख | 46.6% | 48.2% | −1.6 (−1.9 से −1.4) |
| 15m | 4.35 लाख | 45.3% | 48.2% | −2.9 (−3.3 से −2.6) |
| 30m | 2.10 लाख | 44.3% | 47.9% | −3.6 (−4.0 से −3.2) |
| 1h | 1.02 लाख | 43.6% | 47.7% | −4.1 (−4.7 से −3.5) |
| 4h | 24,145 | 42.5% | 46.4% | −3.9 (−4.9 से −2.8) |
| 8h | 11,866 | 42.7% | 46.4% | −3.7 (−5.2 से −2.2) |
| 12h | 7,828 | 42.7% | 46.4% | −3.7 (−5.4 से −1.9) |
| 1d | 3,838 | 42.2% | 46.7% | −4.5 (−7.0 से −1.9) |
| 1w | 467 | 45.0% | 46.8% | −1.8 (−8.1 से +4.8) → data बहुत कम, कोई निष्कर्ष नहीं |

(सारी संख्याएँ: `logs/research_sr_levels/results_table.csv`)

**Robustness जाँच** (pre-registered नहीं, अलग से की गई; `robustness_clean_control.txt`):
- **डर क्या था:** एक साधारण candle का high अक्सर किसी असली swing level के ठीक नीचे होता है, जिससे control बिगड़ सकता है।
- **क्या किया:** ऐसे control events हटाए गए। बचे हुए "साफ control" पर पलटाव 15m से 1d तक **48.5–49.4%** रहा, यानी संयोग जितना (~50%)।
- **नतीजा:** असली levels उनसे **4–7 points कम** पलटते हैं:

  | Timeframe | फर्क |
  |---|---|
  | 15m | −3.9 |
  | 1h | −5.7 |
  | 4h | −6.0 |
  | 1d | −6.8 |

- झुकाव असर को छोटा दिखा रहा था; असली असर और बड़ा है।

### पुराने levels (user का सवाल)
- Level बनने के 500 से ज़्यादा candles बाद पहली बार छूने पर भी असली levels कमज़ोर ही रहे (उदाहरण: 1h पर 39.8% बनाम 41.9%)।
- बड़े timeframes पर samples कम हैं, इसलिए CI चौड़ी है।
- **यह सबूत नहीं मिला कि पुराने levels "छुपी हुई मज़बूत दीवार" होते हैं।**

### Timeframes का मेल (confluence)
- 1h के 25.6% touches पर 1d का कोई level भी पास (0.5 ATR के अंदर) था।
- वहाँ पलटाव 42.8% रहा, बिना मेल वाले में 43.9%। फर्क −1.05 points (CI −2.05 से −0.10)।
- **यानी दो timeframes मिलने पर level ज़्यादा मज़बूत नहीं, बल्कि थोड़ा ज़्यादा टूटा।**

### पैसे में (support पर खरीदो, target +1 ATR, stop −1 ATR; gross अनुमान)
- 5m से 1d तक हर timeframe पर expected value **नकारात्मक** है, क्योंकि पलटाव 50% से कम है। उदाहरण: 1d पर −0.90%, 1h पर −0.13%, और यह खर्च से पहले।
- 1w पर अनुमान सकारात्मक दिखता है, पर वहाँ सिर्फ 252 events हैं और control से कोई फर्क नहीं। इसे सबूत नहीं मानता।

## 14. निष्कर्ष: सबूत के आधार पर
1. **"Support पर खरीदो, resistance पर बेचो" हमारे crypto data में काम नहीं करता।** यह 5m से 1d तक हर timeframe पर, 36 लाख events पर, verifier से जाँचा गया।
2. **पर swing levels बेमतलब भी नहीं हैं। वे "टूटने वाली जगहें" हैं:**
   - असली levels पर टूटने का मौका साधारण levels से साफ ज़्यादा है।
   - यह Osler (2003) के stop-loss cascade वाले विचार से मेल खाता है: level के पार stop orders जमा होते हैं, और छूते ही कीमत तेज़ी से पार निकलती है।
   - यह व्याख्या एक अनुमान है, साबित नहीं; हमारे पास order data नहीं है।
3. **Breakout trade का अंदाज़ा (pre-registered नहीं, सिर्फ अगला test चुनने के लिए):**
   - 1d resistance टूटने की दर ~58% है। Target/stop ±1 ATR पर इसका gross अनुमान ~+0.76% बैठता है, जो 0.50% खर्च से ऊपर है।
   - 4h पर ~+0.3% (खर्च से नीचे), 1h पर ~+0.1% (नहीं)।
   - **सावधानी:** breakout पर order ठीक level पर नहीं भरता (slippage), और 2021–26 का data पहले भी कई बार इस्तेमाल हुआ है। **इसे अलग से lock करके परखे बिना, और 2018–19 व forward पर जाँचे बिना, यह दावा नहीं किया जाएगा।**

## 15. Multi-timeframe S/R इंजन: क्या बनाएँ, और कैसे
**इंजन (बनाना आसान, जाँचा हुआ code मौजूद है):**
- हर coin और हर timeframe के लिए सारे swing levels, जिनमें बहुत पुराने भी शामिल हैं।
- हर level की जानकारी: कब बना, कितनी बार छुआ गया, टूटा या नहीं, कितना पुराना है, और दूसरे timeframes से मेल।
- Levels को कीमत के क्रम में रखने पर "अगला support/resistance कौन-सा" binary search से microseconds में मिल जाता है। इस study में यही तरीका (sparse-table + binary search) 36 लाख events पर ~4 मिनट में चला।
- हर 5 मिनट पर update: नई candles आएँ तो नए levels जुड़ें और टूटे levels पर निशान लगे।

**इसका सही इस्तेमाल (सबूत के क्रम में):**
1. **AI दिमागों के लिए features।** उदाहरण:
   - सबसे पास के ऊपर और नीचे वाले level की दूरी (ATR में), हर timeframe पर;
   - "अभी-अभी कोई level टूटा" का निशान;
   - level कितना पुराना है, और कितनी बार छुआ गया;
   - ऊपर कितने levels की भीड़ है।

   ये R24 (1 दिन वाले) दिमाग में जोड़कर Step 25 जैसे paired test से नापे जाएँगे: skill बढ़ी या नहीं, 2018–19 पर टिकी या नहीं, पैसा बढ़ा या नहीं।
2. **Breakout test (pre-registered):** 4h और 1d resistance breakout, long-only, असली slippage के अंदाज़े के साथ, 2021–26 + 2018–19 + forward पर।
3. **Risk की जानकारी:** "ऊपर का level पास है और वहाँ टूटने का इतिहास है" या "नीचे का support टूटा", ये बातें dashboard पर दिखें। Trading का नियम नहीं, सिर्फ जानकारी।
4. **Execution:** stop-loss को साफ swing levels के ठीक नीचे न रखना, क्योंकि सबूत कहता है कि वहाँ टूटने का मौका ज़्यादा है, यानी stop वहीं hit होने की संभावना बढ़ती है। Testnet पर नापना होगा।

## 16. इसी तरह के और विचार (हर एक की सबूत-स्थिति)
| विचार | क्या है | सबूत | अगला कदम |
|---|---|---|---|
| Volume profile / high-volume nodes | जहाँ सबसे ज़्यादा trading हुई, वे कीमत-स्तर | अभी नहीं परखा | S/R वाले तरीके से study (1h volume से) |
| गोल numbers (BTC 60,000, ETH 3,000) | Orders की भीड़ | Bitcoin में कीमतें गोल numbers पर जमा होती हैं (Urquhart); उसके बाद return pattern नहीं | Breakout वाले test में extra feature |
| Liquidation / funding levels (futures, सिर्फ जानकारी) | जहाँ leverage वाले traders कटते हैं | Step 10 में futures features थे, पर बाद में हटाए गए (हर coin के लिए data नहीं) | सिर्फ बड़े coins के risk alarm के रूप में |
| Anchored VWAP | किसी बड़े event से अब तक की औसत कीमत | नहीं परखा | S/R जैसा study |
| बार-बार छुए गए levels | Chung & Bellotti: ज़्यादा touches → ज़्यादा पलटाव | हमने सिर्फ पहली बार छूना नापा; दूसरी/तीसरी बार वाले touches अभी नहीं | अगला S/R study |

## 17. Opportunity Scanner पर असर (भाग 1 के साथ जोड़कर)
- **भाग 1 से:** छोटे timeframes पर दिशा का अनुमान नहीं लगता, और खर्च बहुत भारी पड़ता है।
- **भाग 2 से:** S/R levels दिशा नहीं बताते, पर "यहाँ कुछ होगा" बताते हैं: टूटने का मौका ज़्यादा।
- **इसलिए scanner का ढाँचा यह बनता है:**

| काम | क्या करेगा | Status |
|---|---|---|
| **Volatility दिमाग** | कितनी हलचल होगी | Step 28 |
| **Relative दिमाग** | 1 दिन और 1 हफ्ते पर कौन बेहतर | R24 पहले से; हफ्ते वाला बाद में |
| **S/R map** | हर timeframe के levels, बतौर features और जानकारी | नया: features test + breakout test |
| **Execution** | 5m/15m से order का समय और stop की जगह | testnet पर नापना |

**सुझाया क्रम:**
1. Forward logger में 4H/1h और paper portfolio जोड़ना (इसके लिए आपकी "हाँ" चाहिए)।
2. Step 28: volatility से position size।
3. **Step 29: S/R map के features, R24 दिमाग में** (paired test)।
4. Step 30: 4h/1d resistance breakout test (pre-registered)।
5. Step 31: हफ्ते वाला relative दिमाग।

## भाग 2 के स्रोत
- Osler 2000, "Support for Resistance": https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.html
- Osler 2003 / NY Fed SR125, "Currency Orders and Exchange-Rate Dynamics": https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.html
- Osler, "Stop-loss orders and price cascades": https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.html
- Chung & Bellotti 2021, arXiv 2101.07410: https://ideas.repec.org/p/arx/papers/2101.07410.html
- Tsinaslanidis 2024: https://ideas.repec.org/h/spr/prbchp/978-3-031-49105-4_62.html
- Urquhart 2017, "Price clustering in Bitcoin": https://ideas.repec.org/a/eee/ecolet/v159y2017icp145-148.html
- Brock, Lakonishok & LeBaron 1992: https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html
- Sullivan, Timmermann & White 1999: https://researchonline.lse.ac.uk/id/eprint/119144

---

# भाग 3 (15 अक्टूबर 2026): बड़े timeframe के levels, levels पर volume, और टूटने के बाद क्या होता है

## 18. User के 4 दावे (जैसे कहे गए, वैसे ही परखे)
- **H1:** 1 महीने, 6 महीने और 1 साल के levels ज़्यादा मज़बूत होते हैं, देर से टूटते हैं।
- **H2:** जिन levels पर ज़्यादा volume इकट्ठा है, बड़े players उन्हें तोड़ते हैं (stop-loss निकालने के लिए)।
- **H3 ("उल्टा calculation"):** बड़े volume वाला support टूटे, तो कीमत थोड़ा और गिरकर वापस ऊपर आती है। बड़े volume वाला resistance टूटे, तो बाद में गिरावट आती है।
- **H4:** support टूटना यानी आगे गिरावट, resistance टूटना यानी आगे तेज़ी। बड़े timeframe का level टूटे, तो signal और मज़बूत।

## 19. छपी research (web पर जाँची)
- **Stop-loss का असर, Osler (NY Fed SR150):** stop-loss वाले levels पर पहुँचते ही कीमत असामान्य रूप से तेज़ उसी दिशा में चलती है ("price cascade")। यह असर take-profit orders के असर से बड़ा होता है और घंटों तक रहता है। **यानी research continuation की ओर इशारा करती है, पलटने (reversal) की ओर नहीं।**
- **"Liquidity sweep" या stop-hunt के बाद पलटना:** इस पर कोई peer-reviewed अध्ययन नहीं मिला। यह बात ज़्यादातर trading-education sites से आती है, और "बड़े players जानबूझकर stop निकालते हैं" वाली नीयत price data से साबित नहीं की जा सकती।
- **Volume profile (कीमत के हर स्तर पर कितना volume हुआ):** कोई academic test नहीं मिला। Indicator बनाने वाले खुद लिखते हैं कि यह गारंटी नहीं है।
- **52-हफ्ते का high, George & Hwang (2004, शेयर):** साल के high के पास वाले शेयर आगे भी बढ़ते रहते हैं (anchoring)। पर कई देशों में खर्च निकालने के बाद यह फायदा ज़्यादातर गायब हो जाता है। Crypto पर परखा नहीं गया।
- **Crypto liquidation cascades (arXiv preprint):** 7 बड़े BTC cascades में से किसी के लिए भी कोई एक संकेत हर बार पहले से चेतावनी नहीं दे पाया।

## 20. हमारा test (pre-registered, SHA-locked, verifier PASS)
- **Protocol:** `logs/research_sr_volume/SRV_STUDY_PROTOCOL_PREREGISTERED.md`।
- **Code:** `src/research/sr_volume_study.py`।
- **Verifier:** `verify_sr_volume_study.py` → V1–V3 PASS, 308 events candle-दर-candle दोबारा गिने गए।
- **Data:** 10 बड़े coins, 2021–26, 2.24 लाख events।
- **Level families:**
  - swing levels: 1h, 4h, 1d, 1w, 1M;
  - पिछले 30, 90, 180 और 365 दिन के सबसे ऊँचे/नीचे भाव।
- **Level पर volume कैसे नापा:** पिछले 7 दिन (1h/4h levels के लिए) या 90 दिन (बड़े levels के लिए) में कुल volume का कितना हिस्सा उस level के ±0.25 ATR के पास trade हुआ।

### H1: बड़े timeframe के levels ज़्यादा मज़बूत? → नहीं, उल्टा
पहली बार छूने पर level टूटा:

| Level | कितनी बार टूटा | साधारण level से फर्क |
|---|---|---|
| 1h swing | 56.4% | +3.8 (CI +3.2 से +4.3) |
| 4h swing | 60.8% | +7.9 (+6.9 से +8.8) |
| 1d swing | 57.8% | +4.2 (+1.4 से +6.8) |
| 1w swing | 62.2% | +9.7 (+2.5 से +16.4) |
| **1M swing** | **68.0%** (सिर्फ 128 events) | +2.4 (CI में 0) |
| 30 दिन का high/low | 56.4% | — |
| 365 दिन का high/low | 58.8% (328 events) | — |

- 1M levels, 1d levels से **+10.2 points ज़्यादा** टूटे (CI +2.9 से +17.7)।
- 365 दिन बनाम 30 दिन वाले levels में कोई साफ फर्क नहीं।
- **सबूत यह नहीं दिखाता कि बड़े levels को तोड़ना मुश्किल है।** जब कीमत बड़े level तक पहुँचती है, तो अक्सर किसी मज़बूत चाल के साथ पहुँचती है, और पार निकल जाती है।

### H2: ज़्यादा volume वाले levels ज़्यादा टूटते हैं? → नहीं, कम टूटते हैं
ज़्यादा volume वाले एक-तिहाई levels बनाम कम volume वाले एक-तिहाई:

| Level | फर्क (ज़्यादा − कम volume, टूटने में) |
|---|---|
| 1h | **−4.3 points** (CI −5.5 से −3.2) |
| 4h | **−3.6** (−5.5 से −1.7) |
| 1d | −5.0 (−10.4 से +0.5, सीमा पर) |

**ज़्यादा volume वाले levels सच में ज़्यादा टिकते हैं।** यह user के "volume = असली support" वाले हिस्से के पक्ष में है, पर "ज़्यादा volume वाले levels निशाना बनकर टूटते हैं" के ख़िलाफ़। बड़े timeframes पर samples कम हैं, इसलिए वहाँ कोई निष्कर्ष नहीं।

### H3: बड़े volume वाला level टूटे, तो कीमत वापस आती है? → आंशिक हाँ, पर पलटना फिर भी 50% से कम
टूटने के बाद पहले level पर वापस आई (**reclaim**), या 1 ATR और आगे गई (**continue**)?

| Level | वापस आई (कुल) | ज़्यादा volume − कम volume |
|---|---|---|
| 1h | 45.0% | **+6.4 points** (CI +4.7 से +8.2) |
| 4h | 41.5% | **+7.7** (+4.4 से +11.0) |
| 1d | 40.9% | +4.0 (CI में 0) |
| 1w | 37.8% | −12.6 (कम samples) |
| 1M | **28.7%** | −21.6 (कम samples) |

- 1h और 4h पर: ज़्यादा volume वाले level के टूटने के बाद वापसी का मौका **साफ बढ़ता है** (यानी user का "उल्टा calculation" यहाँ आंशिक रूप से सही है)। फिर भी वह 45–48% है, यानी आगे बढ़ते रहना अब भी थोड़ा ज़्यादा संभावित है।
- बड़े levels (1d, 1w, 1M) टूटने पर **वापसी और कम** होती है: 1M पर सिर्फ 29%। बड़े level का टूटना आमतौर पर पक्का टूटना है।

### H4: टूटना यानी दिशा का signal? → resistance पर हाँ, पर सिर्फ तेज़ी वाले सालों में
Daily या उससे बड़े level के टूटने के बाद 10 दिन का **अतिरिक्त** return (हर 10 दिन के औसत +2.2% से ऊपर):

| Level टूटा | सारे breaks | ज़्यादा volume वाले breaks |
|---|---|---|
| 1d resistance | **+5.8%** (CI +0.9 से +11.0) | +8.5% |
| 1w resistance | **+11.3%** (+2.7 से +18.7) | +15.6% |
| 30 दिन का high | +6.4% (+1.0 से +11.4) | +7.4% |
| 90 / 180 दिन का high | +8.7% / +9.0% | +12.6% / +13.0% |
| 365 दिन का high | **+11.1%** (+3.7 से +17.8) | +14.4% |
| Support (सारे daily+ levels) | −1% से −2%, CI में 0 | — |
| 1h / 4h (दोनों तरफ) | ~0 | ~0 |

- **User के H3 का resistance वाला हिस्सा गलत निकला:** बड़े volume वाला resistance टूटने के बाद कीमत गिरती नहीं, उल्टा और ज़्यादा बढ़ती है।
- **H4 का resistance वाला हिस्सा सही निकला,** और बड़े levels (1w, 365 दिन) पर signal ज़्यादा मज़बूत था।

**पर robustness जाँच (pre-registered नहीं, `robustness_by_year.txt`) ने यह असर कमज़ोर किया।** Resistance टूटने के बाद का औसत अतिरिक्त return, साल के हिसाब से:

| 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| **+22.6%** | **−6.4%** | +3.1% | +8.8% | −1.3% | −3.3% |

- यह असर तेज़ी वाले सालों (2021, 2024) से आया। मंदी वाले सालों में resistance breakouts नुकसान वाले रहे।
- यानी यह मुख्य रूप से **market के दौर का असर** है, कोई अपने-आप चलने वाला नियम नहीं।

## 21. सीधा जवाब: "क्या मैं सही हूँ?"
| दावा | नतीजा |
|---|---|
| H1: बड़े levels देर से टूटते हैं | ✗ **नहीं।** पहुँचने पर वे ज़्यादा टूटते हैं (1M: 68%) |
| H2: ज़्यादा volume वाले levels टूटते हैं | ✗ **उल्टा।** वे कम टूटते हैं, यानी ज़्यादा मज़बूत हैं |
| H3: बड़े volume वाला support टूटे तो वापसी | ◐ **आंशिक।** 1h/4h पर वापसी का मौका +6 से +8 points बढ़ता है, पर फिर भी 50% से कम। बड़े levels पर वापसी और कम |
| H3: बड़े volume वाला resistance टूटे तो गिरावट | ✗ **उल्टा।** आगे और तेज़ी आई |
| H4: बड़े level का टूटना ज़्यादा मज़बूत signal | ◐ **resistance पर हाँ** (टूटना ज़्यादा पक्का, कम वापसी, बड़ा return), पर **सिर्फ तेज़ी वाले दौर में** |
| "बड़े players stop-loss निकालकर पलटाते हैं" | Price data से नीयत साबित नहीं हो सकती। Research और हमारा data, दोनों continuation की ओर इशारा करते हैं |

## 22. AI दिमागों में कैसे इस्तेमाल करें (सबूत के आधार पर)
सबूत कहता है कि ये चीज़ें **अकेले trading नियम नहीं** हैं, पर दिमागों के लिए **काम की जानकारी (features)** हो सकती हैं:

1. **Level map features** (हर coin, हर timeframe, हर घंटे; सिर्फ पुराने data से):
   - सबसे पास के support/resistance की दूरी (ATR में): 1h, 4h, 1d, 1w, 1M;
   - उन levels पर volume का हिस्सा (ऊपर बताया तरीका), क्योंकि ज़्यादा volume = ज़्यादा टिकाऊ;
   - "अभी-अभी टूटा" वाले निशान: कौन-सा level, किस timeframe का, कितने volume का, कितने घंटे पहले;
   - 30, 90 और 365 दिन के high/low से दूरी (52-हफ्ते high वाला विचार)।
2. **दौर के साथ जोड़ना:** H4 का असर तेज़ी के दौर पर टिका है, इसलिए यह feature अकेले नहीं चलेगा। AI दिमाग (HGB) features के आपसी मेल खुद सीखता है, जैसे "breakout + मज़बूत market" बनाम "breakout + कमज़ोर market"। यही AI का असली काम है।
3. **परखने का क्रम (हर step lock → run → verifier):**
   - **Step 29:** ये level features R24 (1 दिन वाले) दिमाग में जोड़ना। Paired test (Step 25 जैसा): skill बढ़ी? 2018–19 पर टिकी? पैसा बढ़ा?
   - **Step 30:** daily/weekly resistance breakout को market के दौर वाली शर्त के साथ परखना। पहले से तय नियम, 2021–26 + 2018–19 + forward, असली खर्च और slippage के साथ।
   - **Volatility दिमाग (Step 28)** के साथ: level टूटने के बाद हलचल बढ़ती है, यह भी feature बन सकता है।
4. **जोखिम की जानकारी (dashboard):** "1w/1M support टूटा, और वापसी का इतिहास कम है", यह बात user को पल भर में दिखे। यही user का मूल विचार है: पुराने levels नज़र से न छूटें। इंजन यह कर सकता है।

## 23. ईमानदार सीमाएँ
- 1M और 365 दिन वाले levels के events कम हैं (128 और 328), इसलिए उनकी CIs चौड़ी हैं।
- कई cells परखे गए, इसलिए अकेला significant नतीजा कमज़ोर माना गया। भरोसा सिर्फ उन patterns पर है जो कई families में एक ही दिशा में दिखे:
  - असली levels ज़्यादा टूटते हैं;
  - ज़्यादा volume वाले levels ज़्यादा टिकते हैं;
  - 1h/4h पर ज़्यादा volume वाले breaks के बाद वापसी ज़्यादा होती है।
- Events एक-दूसरे पर चढ़े हुए हैं (10 coins साथ चलते हैं, और 10 दिन की windows overlap करती हैं)। Month-block bootstrap इसका कुछ हिस्सा संभालता है, पूरा नहीं।
- सारे नतीजे gross हैं, खर्च से पहले। कोई भी बात trading नियम तभी बनेगी जब वह Step 30 जैसे अलग, lock किए हुए test में पास हो।

## भाग 3 के स्रोत
- Osler, "Stop-Loss Orders and Price Cascades in Currency Markets" (NY Fed SR150): https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.html
- Osler 2003 / SR125 (take-profit बनाम stop-loss clustering): https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.html
- George & Hwang 2004, 52-week high (सारांश): https://quantpedia.com/strategies/52-weeks-high-effect-in-stocks
- 52-week high, कई देश और transaction costs: https://bura.brunel.ac.uk/bitstream/2438/31239/1/FullText.pdf
- Volume profile बतौर reactive tool (IBKR Campus): https://ibkrcampus.com/?p=207713
- BTC liquidation cascades early-warning preprint (CryptoSlate के ज़रिए): https://cryptoslate.com/new-bitcoin-study-shows-the-strongest-recurring-liquidation-warning-signs-cannot-warn-of-an-individual-crash/

---

# भाग 4 (15 अक्टूबर 2026): Swings (ZigZag) बनाम Support/Resistance + Volume — दोनों कितने मिलते हैं?

## 24. सवाल (user)
हमने swings निकाले थे (कहाँ-कहाँ market पलटा), और S/R + volume भी निकाले। दोनों की तुलना करो: कितना मेल है, कितना फर्क है? और क्या S/R + volume से swing की पुष्टि (confirmation) मिलती है?

## 25. ईमानदारी से: हमारे पास कौन-सा swing data था
| Timeframe | Status |
|---|---|
| **1D** | Verified Step 2 swing study (ZigZag-ATR, K = 2/3/4, 10 coins, 2020–26) |
| **4H** | सिर्फ पुराने system की files (archive में, तरीका unverified, पूरा ledger सिर्फ BTC का)। इस्तेमाल नहीं किया |
| **1h** | कभी निकाला ही नहीं गया था |

- 1h और 4h swings इसलिए **उसी verified function** (`zigzag_pivots`) से अभी निकाले गए।
- **G0:** उस function ने पुरानी 1D study के सभी 30 sets (10 coins × K 2/3/4) **हूबहू दोहराए**। एक जगह (LINK, 2023-11-09) एक ही दिन में low और high दोनों बने थे; उन्हें order-free तरीके से मिलाया गया।

**Lock और जाँच:**
- Protocol `logs/research_swing_vs_sr/SWING_SR_PROTOCOL_PREREGISTERED.md`, code `src/research/swing_vs_sr_study.py`।
- **Verifier** `verify_swing_vs_sr.py` → **V1–V4 PASS:**
  - 200 swing points के S/R-मेल और volume साधारण loops से दोबारा गिने गए;
  - 200 touches के "swing बना या नहीं" दोबारा जाँचे गए, ZigZag खुद नए सिरे से चलाकर।

## 26. भाग A: Swing जहाँ पलटा, वहाँ पहले से कोई S/R level था?
**शर्तें:** level swing से **पहले** बन चुका हो, तब तक कोई close उसके पार न गया हो, और swing की कीमत उस level से 0.5 ATR के अंदर हो। तुलना: उतने ही random bars से।

| Swing timeframe (K = 3) | Swing points | किसी S/R level पर पलटे | Random points | फर्क (95% CI) |
|---|---|---|---|---|
| 1h | 22,084 | **51.5%** | 24.7% | **+26.8** (+25.9 से +27.7) |
| 4h | 5,525 | **50.9%** | 23.8% | **+27.1** (+25.1 से +29.0) |
| 1d | 870 | **43.9%** | 23.5% | **+20.5** (+15.9 से +25.2) |

- K = 2 और K = 4 पर भी यही pattern है। जितना बड़ा swing (K = 4), उतना ज़्यादा मेल: 1h पर 53%, 4h पर 54%, 1d पर 46%।
- **बड़े timeframe के levels से भी मेल है:**
  - 4h swings में से 16.5% 1d levels पर पलटे (random 4.2%);
  - 1d swings में से 12.9% 1w levels पर पलटे (random 2.9%)।
- **मतलब:** लगभग **आधे swings किसी पुराने, न टूटे S/R level पर पलटते हैं,** जो random से लगभग दोगुना है। यानी swing और S/R की "जगह" काफी मेल खाती है।

**पर volume उल्टा निकला:**
| Swing timeframe (K = 3) | Swing point पर "ज़्यादा volume" वाली कीमत | Random |
|---|---|---|
| 1h | **17.1%** | 33.3% |
| 4h | **17.4%** | 33.3% |
| 1d | **11.5%** | 33.3% |

- Swing का मोड़ (सबसे ऊँची या सबसे नीची कीमत) अक्सर वहाँ होता है **जहाँ पहले बहुत कम trading हुई थी।** कीमत वहाँ थोड़ी देर ही रुकती है (wick), और पलट जाती है।
- **"S/R + ज़्यादा volume" का जोड़** swing points पर random से सिर्फ थोड़ा ज़्यादा मिला: K = 3 पर 1h +1.2, 4h +1.9 points, और 1d पर कोई फर्क नहीं। K = 4 पर तो कम मिला। यानी यह जोड़ swing की पहचान नहीं है।
- ऐसे swings के बाद की चाल का आकार भी बाकी swings से साफ अलग नहीं निकला (CIs में 0)।

## 27. भाग B: S/R level छूने पर swing बनता है? (confirmation)
Level को पहली बार छूने के 0–2 bars के अंदर, उसी level के पास K = 3 वाला swing मोड़ बना?

| Timeframe | असली S/R touch | Random level touch | फर्क (CI) | ज़्यादा volume वाले levels | कम volume वाले levels |
|---|---|---|---|---|---|
| 1h | **8.0%** | 4.9% | +3.0 (+2.8 से +3.3) | 6.4% | **9.9%** |
| 4h | **8.0%** | 5.2% | +2.8 (+2.4 से +3.2) | 6.4% | **10.2%** |
| 1d | **7.6%** | 4.4% | +3.2 (+2.0 से +4.4) | 5.7% | **11.7%** |

- असली S/R पर swing बनने का मौका random से ज़्यादा है, पर **कुल मिलाकर सिर्फ ~8%।** यानी **100 में से 92 touches पर बड़ा swing नहीं बनता।** S/R touch अकेले कोई पक्की पुष्टि नहीं है।
- **ज़्यादा volume वाले levels पर swing कम बनता है** (6%), **कम volume वाले पर ज़्यादा** (10–12%)। यह फर्क तीनों timeframes पर साफ है (CI 0 से दूर)।
- **भाग 3 से जोड़कर:** ज़्यादा volume वाले levels कम टूटते हैं (भाग 3) और उन पर तेज़ पलटाव भी कम होता है (यहाँ)। यानी **ज़्यादा volume वाले levels पर कीमत अटकती है, ऊपर-नीचे होती रहती है।** तेज़ मोड़ कम volume वाली कीमतों पर आते हैं।
- जब swing बनता है, तो उसके बाद की चाल का median लगभग 5 ATR है (1h 5.1, 4h 4.9, 1d 5.2)।

## 28. नई समझ (insight)
1. **जगह (location) का मेल मज़बूत है:** लगभग आधे swings पुराने, न टूटे S/R levels पर पलटते हैं (random से ~2×)। तो user की बात "swing और S/R साथ चलते हैं" **जगह के मामले में सही है।**
2. **पर "पहले से बता देना" (prediction) कमज़ोर है:** level छूने पर सिर्फ ~8% बार swing बनता है। ज़्यादातर बार कीमत अटकती है या पार निकल जाती है (भाग 2: असली levels ज़्यादा टूटते हैं)।
3. **Volume का रोल उल्टा है:**
   - ज़्यादा volume वाली कीमत = अटकने का इलाका (balance)।
   - कम volume वाली कीमत = तेज़ मोड़ या तेज़ पार (swing का सिरा)।
   - इसलिए "S/R + ज़्यादा volume = swing confirmation" वाला जोड़ **data में नहीं मिला।** "S/R + कम volume" पर मोड़ ज़्यादा बनते हैं, पर फिर भी सिर्फ 10–12% बार।
4. **AI के लिए मतलब:** ये चीज़ें अकेले confirmation नहीं हैं, पर **अच्छी जानकारी (features)** हैं, क्योंकि जगह का मेल 2× है:
   - सबसे पास का न टूटा S/R level;
   - उस कीमत पर volume (ज़्यादा = अटकाव, कम = तेज़ मोड़/पार);
   - level किस timeframe का है;
   - ZigZag swing की हालत (अभी up leg है या down leg, और leg की उम्र)।

   AI (HGB) इनके आपसी मेल से वह सीख सकता है जो कोई एक सादा नियम नहीं सीख पाता। यह Step 29 का paired test बताएगा।

## 29. सीमाएँ
- Swing points (ZigZag final pivots) पीछे देखकर (hindsight) पता चलते हैं। भाग A "कहाँ हुआ" बताता है, trading signal नहीं। भाग B का touch real-time में पता चलता है, पर "swing बना" वाला निशान भी बाद में ही पक्का होता है।
- "Swing पुराने low/high के पास पलटा" में double-bottom/retest जैसा स्वाभाविक pattern भी शामिल है। Random control इसे ध्यान में रखकर तुलना करता है, फिर भी इसे "कारण" न समझा जाए।
- 1d पर samples कम हैं (870 swings), बाकी timeframes पर बहुत ज़्यादा।
- सारे नतीजे gross हैं, खर्च से पहले, और कोई trading नियम नहीं। आगे Step 29/30 में पहले से lock किए गए test होंगे।
