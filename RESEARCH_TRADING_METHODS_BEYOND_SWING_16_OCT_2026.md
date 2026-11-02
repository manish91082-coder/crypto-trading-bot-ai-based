# Swing के अलावा trading के और तरीके: नुकसान कम से कम, फायदा ज़्यादा से ज़्यादा (1D, spot + futures)
**16 अक्टूबर 2026, पूरा विश्लेषण: हमारे सबूत + दुनिया का शोध + गणित**

**नियम:**
- हर दावे के आगे उसका सबूत है:
  - **[हमारा]** = हमारे pre-registered और verified tests;
  - **[बाहरी]** = शोध, link सहित।
- ⚠ = एक ही स्रोत, या विवादित, या खर्च के बिना।
- Investment, staking और earn शामिल नहीं हैं।
- मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## भाग 0. पहले एक ज़रूरी सुधार: हमारा मौजूदा तरीका "swing" नहीं, "relative ranking" है
- **[हमारा]:** तीनों दिमाग (D1, R6, R24) यह नहीं बताते कि coin ऊपर जाएगा या नीचे। वे बताते हैं कि **बाकियों के मुकाबले कौन आगे रहेगा** (AUC 0.559–0.568, नकली दिमाग ~0.50)। हम top-5 को long और bottom-5 को short करते हैं, और रोज़ या हर 5 दिन में बदलते हैं।
- असली "swing" (एक coin की लहर पकड़ना) हमने Phase 1/2 में परखा था:
  - swing के पीछे चलने का औसत ~0 रहा, और 61–63% trades हारे;
  - Swing AI से पैसा पक्का नहीं हुआ।
- **यानी जो काम कर रहा है, वह cross-sectional relative momentum है, swing नहीं।** यह फर्क नीचे के हर फैसले के लिए ज़रूरी है।

---

## भाग 1. गणित: "नुकसान कम" और "फायदा ज़्यादा" असल में क्या हैं
ये पाँच तथ्य हर तरीके को परखने का पैमाना हैं (मानक गणित, स्रोत साथ में):

1. **गिरावट की असमानता:**
   - −50% के बाद वापस आने के लिए +100% चाहिए; −80% के बाद +400%।
   - इसलिए बड़ी गिरावट से बचना, बड़ी कमाई से ज़्यादा कीमती है।
2. **Volatility drag:**
   - लंबे समय की compound बढ़त ≈ औसत return − (volatility²)/2।
   - **[हमारा]:** spot अकेले का 2021–26 में औसत महीना +3.2% था, पर median साल सिर्फ +6%।
   - हलचल ज़्यादा हो, तो औसत अच्छा होते हुए भी पैसा कम बढ़ता है।
3. **Kelly (बढ़त का सबसे तेज़ रास्ता):** पूरा Kelly बहुत गहरी गिरावट देता है; 2× Kelly पर बढ़त शून्य हो जाती है। आधा Kelly ~75% बढ़त देता है, पर कहीं ज़्यादा सुरक्षित रूप से ([MacLean–Thorp–Ziemba, regime notes में])। Edge का अनुमान गलत होना सबसे बड़ा खतरा है (Chopra–Ziemba: औसत की गलती, variance की गलती से ~10 गुना भारी)।
4. **विविधता का गणित:** दो तरीके जिनका Sharpe बराबर (s) है और आपसी correlation ρ है, साथ में Sharpe ≈ s·√(2/(1+ρ)) देते हैं।
   - ρ = 0.1 पर लगभग 1.35 गुना।
   - **[हमारा, आज निकाला]:** F7 long-short और BTC funding-carry का daily correlation सिर्फ **0.08** है।
   - **Loss घटाने का सबसे सस्ता तरीका: कम मेल वाले कई तरीके साथ चलाना।**
5. **Tail का पैमाना:** औसत नहीं, सबसे बुरे 5% दिन मायने रखते हैं (CVaR, Rockafellar–Uryasev 2000)। **[हमारा]:** F7 में stop लगाने से liquidations 69 से 0 हुए, यानी tail सीधे कटा।

---

## भाग 2. Trading के सारे formats: हर एक पर फैसला

**पैमाना:**
- **नुकसान-नियंत्रण:** यह तरीका बड़ी गिरावट से कितना बचाता है।
- **फायदा:** खर्च के बाद कितना।
- **फिट:** हमारे 1D AI system और data के साथ कितना बैठता है।

### A. Cross-sectional relative long-short (हमारा core): ✅ रखें
- **[हमारा]:**

  | System | $10k → | सबसे बड़ी गिरावट | 2022 |
  |---|---|---|---|
  | F2 | $110k | 30% | — |
  | **F7 (stop + cooldown)** | **$88k** | **21%** | **+36.5%** |
  | सिर्फ long | $54k | 49% | — |

  58 में से 0 बारह-महीने के windows घाटे में।
- **[बाहरी]:** बड़े coins में 1–3 हफ्ते का momentum काम करता है। Short की कमाई ज़्यादातर छोटे, illiquid coins में है। खर्च gross फायदे का ~60% खा सकता है (cross-sectional notes: Liu–Tsyvinski–Wu, Dobrynskaya, Cakici et al.)।
- **कमज़ोरी:**
  - short leg पतला है (+0.29% प्रति trade);
  - PBO 65% है;
  - फायदा forward में कम हो सकता है।
- **सुधार:** E1–E4 (BTC hedge, filters, inverse-vol) पहले से योजना में हैं।

### B. Time-series trend-following (BTC या हर coin का अपना trend): 🟡 सिर्फ "long घटाने" वाले रूप में test करें
- **[बाहरी]:**
  - Zarattini, Pagani & Barbon (Swiss Finance Institute, RP 25-80, 2025): कई Donchian lookbacks, volatility-based size, top-20 coins। **खर्च के बाद Sharpe 1.5 से ऊपर**, BTC पर 10.8% alpha ([SSRN/IDEAS](https://ideas.repec.org/p/chf/rpseri/rp2580.html), [Concretum](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/))। ⚠ यह लेखकों का अपना backtest है, और max drawdown नहीं मिला।
  - Liu–Tsyvinski (RFS 2021): BTC में हफ्ते का time-series momentum।
  - ⚠ Cambridge/Globe का paper (arXiv 2009.12155) 255% सालाना दिखाता है, पर **खर्च शून्य माना**, parameters पूरे data पर चुने, और लेखक खुद मानते हैं कि parameters "robust नहीं" हैं ([arXiv](https://ar5iv.labs.arxiv.org/html/2009.12155))। **यह दिखाता है कि ऐसे दावों पर भरोसा क्यों नहीं करना चाहिए।**
  - Trend धीमी मंदी में बचाता है, पर अचानक crash और sideways market में नुकसान देता है (Hurst–Ooi–Pedersen, गैर-crypto)।
- **[हमारा]:** 5 बार "market गिरेगा" वाला timing fail हुआ (Steps 17/20/21/22/26)। Step 30 (breakout + दौर) 2018–19 में fail रहा।
- **फैसला:** Trend से short बढ़ाना नहीं। सिर्फ **E7: multi-lookback BTC trend नकारात्मक हो, तो long book आधा।** एक ही पहले से lock किया नियम, नकली control के साथ।

### C. Mean reversion / गिरने पर खरीदना / support पर खरीदना: ❌ नहीं (बड़े coins में)
- **[बाहरी]:** Daily reversal छोटे, illiquid coins की घटना है; सबसे बड़े coins में daily momentum है (Zaremba et al., IRFA 2021)।
- **[हमारा]:**
  - Support पर खरीदना हर timeframe पर नुकसान का सौदा निकला। असली levels ज़्यादा टूटते हैं (S/R study)।
  - Step 14 का 1-दिन वाला अनुमान fail रहा।

### D. Breakout / volatility breakout: ❌ नहीं
- **[हमारा]:** Step 30 2018–19 में घाटे में; Step 29 के S/R/volume features से पैसा घटा।

### E. Market-neutral carry (spot long + perp short, एक ही coin): 🟡 छोटा "sleeve", सिर्फ funding ऊँचा हो तब
- **[हमारा, आज F1 data से]:** BTC perp short को मिली funding, साल-दर-साल (खर्च से पहले):

  | साल | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (सितंबर तक) |
  |---|---|---|---|---|---|---|---|
  | BTC | 17.2% | 30.6% | 4.2% | 7.9% | 12.0% | 5.1% | 2.2% |

  - ETH 2022: 0.8%।
  - Funding negative रहने वाले समय का हिस्सा: BTC 2022 में 22%, 2026 में 26%।
- **[बाहरी]:**
  - BIS WP 1087: औसत carry >10%।
  - He–Manela–Ross–von Wachter: Binance पर BTC ~6.4% सालाना excess (2020–मार्च 2024), position सिर्फ ~20–35% समय खुली।
  - 2025 में Sharpe negative (survey)।
  - FTX और अक्टूबर 2025 की घटनाओं ने exchange और collateral जोखिम दिखाया (same-coin notes)।
- **गुण:**
  - कीमत का जोखिम लगभग शून्य, इसलिए नुकसान-नियंत्रण बहुत अच्छा।
  - F7 से correlation 0.08, यानी विविधता।
  - पर अब फायदा पतला है (2025–26 में 2–5%)।
- **फैसला:** **E9**, funding-gated। तभी खोलें जब funding किसी पहले से तय सीमा से ऊपर हो, और उसमें खाली पड़ा USDT ही लगे।

### F. Pairs / cointegration stat-arb: ❌ नहीं
- **[बाहरी]:** Daily crypto pairs में खर्च के बाद return शून्य के पास या negative। अच्छे नतीजे parameter चुनने पर टिके हैं (same-coin notes: Fil & Kristoufek, Tadi & Witzany)।

### G. Options (BTC/ETH): 🟡 बीमा या volatility overlay, पर पहले data
- **[बाहरी]:**
  - Volatility risk premium लगातार negative रहा, यानी implied volatility, realized volatility से ऊपर ([J. Financial Markets](https://www.sciencedirect.com/science/article/pii/S1386418122000544))।
  - Deribit: ~70% समय IV > RV।
  - Covered call (20-delta, 30-दिन): खर्च के बाद 5.5% सालाना, Sharpe 0.53, और उसी साल BTC −19% ([Anchorage](https://www.anchorage.com/insights/synthetic-yield-on-bitcoin-implementation-discipline-and-performance-boundaries-of-systematic-covered-call-writing))। ⚠
  - असली quotes पर edge घटता है।
  - Put (बीमा) महँगा है।
- **फैसला:** आज से रोज़ public data (DVOL, chain) इकट्ठा करें (M4)। 3–6 महीने बाद test।

### H. Event-driven (listing, token unlock, delisting): 🟡 short-side filter के रूप में, सबसे दिलचस्प नया विचार
- **[बाहरी] listing:** पहले दिन उछाल (+14.7% abnormal, एक study), फिर हफ्तों-महीनों में गिरावट। 2024 के एक review में 31 में से सिर्फ 5 tokens छह महीने बाद listing कीमत से ऊपर थे (short-risk notes; केवल एक peer-reviewed, AFT 2025)।
- **[बाहरी] token unlocks:**
  - ⚠ Keyrock (16,000+ घटनाएँ): ~90% unlocks से नीचे का दबाव, जो ~30 दिन पहले से शुरू होता है ([Keyrock](https://keyrock.com/from-locked-to-liquidity-what-16000-token-unlocks-teach-us/))।
  - ⚠ Tokenomist (236 घटनाएँ): एक महीने का BTC के मुकाबले median return −16.3%, और 72.5% घटनाएँ नीचे खत्म हुईं। असर बड़े और नए tokens में है; स्थापित और liquid tokens पर नहीं ([Tokenomist](https://tokenomist.ai/research/do-token-unlocks-crash-prices))।
  - **ये सब industry के स्रोत हैं, peer-reviewed नहीं।**
- **[हमारा]:** F2 में short की कमाई कुछ नए 2025–26 listings पर टिकी थी। यानी हमारा AI शायद यही "नया-token गिरावट" पकड़ रहा है।
- **फैसला:**
  - **E3** (listing-age diagnostic) पहले से योजना में है।
  - Unlock calendar का भरोसेमंद, मुफ्त ऐतिहासिक data चाहिए। पहले data का स्रोत verify करें, फिर ही test।

### I. On-chain संकेत (MVRV, exchange flows): ❌ अभी नहीं
- **[बाहरी]:**
  - 2026 के review के अनुसार अलग-अलग on-chain predictors out-of-sample बार-बार fail हुए।
  - 141 variables में से सिर्फ 4 हर horizon पर random walk से बेहतर निकले।
  - एक preprint के अनुसार on-chain metrics कीमत के पीछे चलते हैं, आगे नहीं ([arXiv 2606.00071](https://arxiv.org/html/2606.00071v1))।
- **[हमारा]:** Futures data features (S3) भी fail रहे।

### J. Sentiment / attention (Fear & Greed, Twitter, Google): ⏸ पहले से आंशिक रूप में मौजूद
- **[बाहरी]:** असर ज़्यादातर in-sample है, और extreme हालात में दिखता है। सिर्फ एक ML study में held-out test (62% सही) है। खर्च के बाद का सबूत नहीं ([IREF 2021 / Sharif](https://repository.sharif.edu/resource/501394/how-people--39-s-sentiment-and-attention-affect-the-return-of-bitcoin))।
- **[हमारा]:** Fear & Greed पहले से D1 दिमाग के features में है (`fng_table`)। S6 (attention data) रोका गया है।

### K. Calendar / seasonality (हफ्ते का दिन, घंटा): ❌ नहीं
- **[बाहरी]:** Baur et al. (15 million+ observations, 7 exchanges): "कोई लगातार pattern नहीं" ([UWA](https://research-repository.uwa.edu.au/en/publications/bitcoin-time-of-day-day-of-week-and-month-of-year-effects-in-retu/))। बाकी अध्ययन मिले-जुले हैं ([Quantpedia](https://quantpedia.com/are-there-any-simple-calendar-effects-in-bitcoin-market/))।

### L. Market making / HFT / arbitrage: ❌ नहीं
- **[बाहरी]:** Binance पर triangular arbitrage खर्च और कम गहराई के बाद लगभग शून्य (FRL 2025)। Market making के लिए millisecond गति और inventory जोखिम का प्रबंधन चाहिए। यह 1D AI का काम नहीं।
- **[हमारा]:** 5m–1h पर दिशा का अनुमान ~0 रहा। R4 ने $10k को $49 कर दिया।

### M. Grid bots: ❌ नहीं
- **[बाहरी]:** Peer-reviewed सबूत नहीं। Trend में grid पीछे रहता है (instruments report)।

### N. Reinforcement learning (AI खुद तय करे कितना लगाना है): ❌ नहीं
- **[बाहरी]:** PBO-नियंत्रित FinRL study में सारे agents अपने test में घाटे में रहे। RL agents generalize नहीं करते (AI notes)।

---

## भाग 3. "नुकसान कम से कम" के औज़ार (portfolio की परत)

| औज़ार | सबूत | हमारी स्थिति |
|---|---|---|
| **1x, बिना leverage** | Kelly: गलत edge पर ज़्यादा दाँव विनाशकारी | ✅ लागू |
| **हर short पर stop + cooldown** | [हमारा] F7: 69 → 0 liquidation, गिरावट 30% → 21% | ✅ लागू (F7) |
| **Market-neutral ढाँचा** | [हमारा] गिरावट 49% → 21% | ✅ लागू |
| **कम मेल वाले कई तरीके** (relative LS + carry + बाद में options) | गणित √(2/(1+ρ)); [हमारा] ρ = 0.08 | ⏳ E9 |
| **हर leg के अंदर inverse-volatility weight + per-coin cap** | [बाहरी] momentum crashes vol-scaling से घटते हैं (Grobys 2025) | ⏳ E4। Step 28 पूरे portfolio के स्तर पर fail था; यह अलग रूप है |
| **धीरे-धीरे de-risking** (गिरावट के साथ gross घटे, एक floor, कभी शून्य नहीं) | [बाहरी] सख्त CPPI से "cash lock" होता है; धीरे-धीरे घटाना सुरक्षित | ⏳ E6 (अगला round) |
| **Kill switch** (account चोटी से 35% नीचे जाए तो सब रुके) | सामान्य जोखिम-नियम | ✅ F6 में |
| **Stop mark price पर** | [बाहरी, Binance docs] liquidation mark price पर होता है | ⏳ F6 testnet |
| **Exchange / collateral जोखिम** | FTX, अक्टूबर 2025 | ✅ नियम: yield वाला collateral नहीं |
| **Market timing से बचना** | [हमारा] 5 fail; [बाहरी] timing out-of-sample fail होता है | ✅ नियम |

## भाग 4. "फायदा ज़्यादा से ज़्यादा" के औज़ार

| औज़ार | सबूत | स्थिति |
|---|---|---|
| **खर्च घटाना (सबसे बड़ा lever)** | [हमारा] खर्च 0.25% → 0.40% होने पर R24 $201k → $62k। असली book ~0.11% | ⏳ S7, limit orders (M9), BNB fee (U6) |
| **Long leg perps पर** (fee कम, पर funding चुकानी) | [हमारा] कभी test नहीं हुआ | ⏳ E11 |
| **धीमा rebalance / hysteresis** | [बाहरी] daily turnover edge खाता है; Dobrynskaya 2–8 हफ्ते की सलाह देती हैं | ⏳ E5 |
| **Confident predictions पर ज़्यादा भार** | [बाहरी] Jaquart: सबसे confident 10% पर 57–59% सही | ⏳ E8 |
| **आधा या चौथाई Kelly, out-of-sample Sharpe पर** | MacLean–Thorp–Ziemba | ⏳ forward के बाद |
| **Volatility drag घटाना** (कम हलचल = ज़्यादा compound) | गणित | ✅ market-neutral से |

## भाग 5. AI दिमाग किस भूमिका में

| भूमिका | सबूत | फैसला |
|---|---|---|
| **Ranking** (कौन आगे) | [हमारा] AUC 0.56–0.57, असली | ✅ core |
| Meta-labeling / confidence sizing | तरीका पक्का, crypto out-of-sample सबूत नहीं | ⏳ E8 |
| Learning-to-rank (lambdarank) | सिर्फ equity, खर्च के बिना | ⏳ E10 (कम प्राथमिकता) |
| Regime classifier (HMM) | Out-of-sample सबूत कमज़ोर | ❌ अभी नहीं |
| RL allocator | Generalize नहीं करते | ❌ |
| बड़े neural networks | [बाहरी] Cakici: OLS लगभग बराबर | ❌ |

---

## भाग 6. मेरा निष्कर्ष: सबसे अच्छा ढाँचा (सब pre-registered test के बाद ही)

**"कई कम-मेल वाले sleeves + एक मज़बूत risk परत":**

| Sleeve | भूमिका | सबूत-स्तर | कब |
|---|---|---|---|
| **1. Relative long-short (F7 + E1–E4 सुधार)** | मुख्य कमाई + मंदी में बचाव | [हमारा] PASS (backtest); forward चालू | अभी |
| **2. Funding-gated BTC/ETH carry** (E9) | कम जोखिम वाली छोटी कमाई, कम मेल (ρ 0.08) | [हमारा] data + [बाहरी] BIS/He et al. | E1–E4 के बाद |
| **3. BTC trend overlay** (E7, सिर्फ long घटाए) | धीमी मंदी में long का नुकसान घटाना | [बाहरी] Zarattini/Liu–Tsyvinski | अगला round |
| **4. Options tail-बीमा / covered-call overlay** | बड़े crash का बीमा | [बाहरी] VRP; data नहीं | 3–6 महीने data के बाद |
| **Risk परत** | 1x, stops (mark price), inverse-vol, cap, धीरे-धीरे de-risking, kill switch, exchange-risk नियम | ऊपर | लगातार |

**हर दौर में अपेक्षा (साबित नहीं):**

| दौर | Sleeve 1 | Sleeve 2 | Sleeve 3 | Sleeve 4 |
|---|---|---|---|---|
| Bull | कमाई | carry ऊँचा | पूरा long | premium कमाई |
| Bear | short से बचाव | carry कम | long आधा | बीमा काम आए |
| Sideways | पतला | carry पतला | whipsaw का खर्च | premium कमाई |
| Crash | stop और gap का खतरा | ADL और exchange का खतरा | देर से | बीमा |

**ईमानदार सीमाएँ:**
1. ~20 बड़े coins, daily rebalance, Binance के खर्च और 2022 के बाद की अवधि पर कोई प्रकाशित, खर्च-सहित अध्ययन नहीं है। बाहरी शोध **दिशा** देता है, संख्याएँ नहीं।
2. हर नया test overfitting बढ़ाता है (PBO पहले ही 65%)। इसलिए एक round में ≤ 4 experiments, हर एक के ≤ 2 variants, और DSR कुल trials पर।
3. कोई भी नया sleeve F7 को **और** नकली control, दोनों को हराए, फिर forward में shadow के रूप में 90 दिन चले, उसके बाद ही अपनाया जाए।
4. अगर कुछ भी पास न हो, तो "F7 ही रखें" एक सही और वैध नतीजा है।

---

## भाग 7. Test करने की प्राथमिकता (सारे शोध को मिलाकर)

| क्रम | Experiment | लक्ष्य |
|---|---|---|
| 1 | **E1** BTC hedge वाला short book (perp या quarterly) | नुकसान ↓ |
| 2 | **E2** alt-short filters (funding, listing-age, liquidity) | नुकसान ↓ |
| 3 | **E3** listing-age diagnostic (skill है या सिर्फ नए tokens की गिरावट) | सच्चाई |
| 4 | **E4** inverse-vol + per-coin cap | नुकसान ↓ |
| 5 | **E11** long leg perps पर | फायदा ↑ (खर्च) |
| 6 | E9 funding-gated carry sleeve | विविधता |
| 7 | E5 hysteresis / धीमा rebalance | फायदा ↑ |
| 8 | E7 trend overlay (सिर्फ long घटाए) | नुकसान ↓ |
| 9 | E6 धीरे-धीरे de-risking + vol target | नुकसान ↓ |
| 10 | E8 confidence-gated shorts | फायदा ↑ |
| बाद में | Options overlay (data के बाद), token-unlock filter (data verify के बाद), E10 LTR | — |
| नहीं | Mean reversion, breakout, pairs, on-chain, calendar, HFT/arbitrage, grid, RL, बड़े NN | सबूत |

**Round 1 का budget:** E1–E4 + E11। उसके बाद नतीजे देखकर round 2।

---

## स्रोत

**पिछले research notes** (`research_notes/लॉन्ग शॉर्ट मिक्स 1D रिसर्च/`, सबके links अंदर):
- cross-sectional long-short
- same-coin / basis
- regime / net exposure
- short risk
- AI/ML

**आज के नए स्रोत:**
- [Zarattini–Pagani–Barbon, SFI RP 25-80](https://ideas.repec.org/p/chf/rpseri/rp2580.html)
- [Concretum summary](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/)
- [CXO Advisory](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/)
- [Rozario et al., arXiv 2009.12155](https://ar5iv.labs.arxiv.org/html/2009.12155)
- [Monash](https://www.monash.edu/business/mcfs/our-research/all-projects/investment-strategy/trend-following-strategies-for-crypto-investors)
- [Keyrock token unlocks](https://keyrock.com/from-locked-to-liquidity-what-16000-token-unlocks-teach-us/)
- [Tokenomist](https://tokenomist.ai/research/do-token-unlocks-crash-prices)
- [Streamflow](https://streamflow.finance/blog/do-token-unlocks-cause-price-drops)
- [arXiv 2606.00071 (Bitcoin prediction review)](https://arxiv.org/html/2606.00071v1)
- [JRFM 2024 Bitcoin return prediction](https://doi.org/10.3390/jrfm17100443)
- [Comprehensive Bitcoin predictability](https://www.researchgate.net/publication/396908181_A_Comprehensive_Look_at_Bitcoin_Return_Predictability)
- [Sharif sentiment study](https://repository.sharif.edu/resource/501394/how-people--39-s-sentiment-and-attention-affect-the-return-of-bitcoin)
- [UAEU online sentiment](https://research.uaeu.ac.ae/en/publications/predictive-role-of-online-investor-sentiment-for-cryptocurrency-m/)
- [Bocconi](https://www.unibocconi.it/en/news/cryptocurrencies-between-apparent-chaos-and-predictable-signals)
- [Baur et al. calendar effects](https://research-repository.uwa.edu.au/en/publications/bitcoin-time-of-day-day-of-week-and-month-of-year-effects-in-retu/)
- [Quantpedia calendar](https://quantpedia.com/are-there-any-simple-calendar-effects-in-bitcoin-market/)
- [Liu 2024 RePEc](https://ideas.repec.org/a/spt/apfiba/v14y2024i4f14_4_3.html)
- [Bitcoin options VRP, J. Financial Markets](https://www.sciencedirect.com/science/article/pii/S1386418122000544)
- [Anchorage covered call](https://www.anchorage.com/insights/synthetic-yield-on-bitcoin-implementation-discipline-and-performance-boundaries-of-systematic-covered-call-writing)

**हमारा data (आज):**
- `data/futures_um/{BTCUSDT,ETHUSDT}_funding.csv` (SHA-verified F1)
- `logs/strategy_f7_risk/equity_MAIN_AI_RS.csv`
- `logs/strategy_f7_risk/equity_MAIN_AI_OFF_LO.csv`
