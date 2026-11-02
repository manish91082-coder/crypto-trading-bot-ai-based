# 1D वाले AI दिमाग: क्या बचा है, और क्या सुधार हो सकते हैं (deep research)

**तारीख:** 15 अक्टूबर 2026 | **GitHub:** कुछ नहीं | **Trading:** कुछ नहीं

**यह file सिर्फ research और योजना है। कोई नया model नहीं बना, कोई नया नतीजा नहीं।**

**संख्याएँ दो तरह की हैं:**
- **[हमारा सबूत]:** हमारी अपनी verified files (`claims.json`) से।
- **[बाहरी]:** peer-reviewed papers से। हर paper कम से कम दो जगह (journal या SSRN/NBER, और एक दूसरा source) से मिलाया गया।

**ईमानदार सीमा:** बाहरी papers के ज़्यादातर पूरे text नहीं, बल्कि abstract और भरोसेमंद सार पढ़े गए। इसलिए उनसे सिर्फ दिशा ली है, हमारे लिए कोई पक्की संख्या नहीं।

---

## 1. अभी 1D पर क्या है [हमारा सबूत]
"1D" से मतलब है **दिन में एक बार फैसला लेने वाले दिमाग**:

| दिमाग | सवाल | AUC 2021–26 | AUC 2018–19 (कभी न देखा) | $10k 2021–26 (100% लगाकर) | सबसे बड़ी गिरावट |
|---|---|---|---|---|---|
| D1 (R5, daily candles) | 5 दिन में कौन बाकियों से आगे | 0.559 | 0.526 | $74,452 | 81% |
| H4 (R6, 4h candles) | 1 दिन में कौन आगे | 0.568 | 0.546 | $98,735 | 78% |
| H1 (R24, 1h candles) | 1 दिन में कौन आगे | 0.565 | 0.546 | $201,548 | 75% |

**Setup:** तीनों मिलाकर (M_AI3), 50% पैसा लगाकर:
- 2021–26: $53,884;
- 2018–19: $6,546, जबकि BTC hold का नतीजा $6,961 था।

**सबसे बड़ी कमज़ोरियाँ:**
1. मंदी (bear market) में BTC से हारना।
2. 49–81% की गिरावटें।
3. खर्च पर बहुत निर्भरता।

## 2. जो पहले ही परखा जा चुका है (दोबारा नहीं करना) [हमारा सबूत]
| परखा गया | नतीजा |
|---|---|
| Market timing / गिरावट से बचना (Steps 17, 20, 21, 22, 26) | 5 बार fail |
| हलचल के हिसाब से size (Step 28) | Fail |
| 15m/5m features (Step 25) | AUC +0.0008, पैसा कम |
| S/R + VAP + swing features (Step 29) | AUC +0.0008, पैसा कम |
| Swing AI (Phase 2) | थोड़ी skill, पैसा पक्का नहीं |
| Breakout + दौर (Step 30) | 2018–19 में घाटा |
| ज़्यादा coins (सारे liquid B coins, Step 15) | skill है, पर trading नियम fail |
| हफ्ते वाला दिमाग | Step 15 के R5/R10 में पहले ही परखा (0.545 / 0.541) |
| "ऊपर जाएगा या नहीं" (absolute) दिमाग, futures data समेत (Step 10) | AUC 0.52–0.53, fail |

---

## 3. जो **अभी तक नहीं परखा गया**: उम्मीदवार, सबूत के साथ

### A. Overfitting का हिसाब: हमारे "अच्छे" नतीजों में किस्मत कितनी है ★ सबसे पहले
**क्यों:**
- हमने 2021–26 के data पर लगभग 30 steps में दर्जनों चीज़ें परखीं।
- जितनी ज़्यादा कोशिशें, उतना ज़्यादा मौका कि सबसे अच्छा नतीजा संयोग हो।

**[बाहरी]:**
- Bailey & López de Prado, *The Deflated Sharpe Ratio* (Journal of Portfolio Management, 2014; SSRN 2460551)। यह कई कोशिशों और non-normal returns के लिए Sharpe को सुधारता है।
- Bailey, Borwein, López de Prado & Zhu, *The Probability of Backtest Overfitting* (Journal of Computational Finance, 2017; SSRN 2326253)। इसका CSCV तरीका नापता है कि "in-sample सबसे अच्छा" कितनी बार out-of-sample नीचे के आधे में गिरता है।

**क्या करेंगे:** हर step की हर कोशिश (trial) की daily equity पहले से files में है। उनसे Deflated Sharpe और PBO निकालेंगे, खासकर चुने गए M_AI3-50% के लिए।

**फायदा:**
- कोई नई trading नहीं, सिर्फ ईमानदार माप।
- असली पैसे के फैसले (जनवरी 2027) में यह अंदाज़ा साथ होगा कि नतीजे में किस्मत कितनी है।

**खर्च:** कम (कुछ घंटे)। Data लेने का कोई खतरा नहीं।

### B. मंदी (2017–19) का data training में जोड़ना ★
**[हमारा सबूत]:**
- तीनों दिमाग सिर्फ **2020 के बाद** के data पर सीखे हैं। `universe_all` 2020-01-01 से शुरू होता है।
- 2017-08 से 2019-12 का verified data (`universe_pre2020`, 92 coins) सिर्फ परीक्षा के लिए इस्तेमाल हुआ।
- और ठीक वहीं, मंदी में, दिमाग कमज़ोर निकले: 2018–19 में R24 $2,837 और D1 $3,424, जबकि BTC $6,961।
- यानी AI ने कभी पूरी मंदी (2018 में −73%) देखी ही नहीं।

**परीक्षा कैसे:** Paired walk-forward।
- पुराना दिमाग बनाम (वही दिमाग + 2017–19 training में)।
- परीक्षा के महीने वही रहेंगे (2021–26), सिर्फ training बड़ी होगी।
- 2022 (मंदी वाला साल) का हिस्सा अलग से देखा जाएगा।

**ईमानदार कीमत:** 2018–19 फिर "कभी न देखा" exam नहीं रहेगा। उसके बाद असली जज सिर्फ forward log होगा।

**फायदा (अगर pass हो):** मंदी के उदाहरण सीखने से 2022 जैसे साल में नुकसान कम हो सकता है। यह सिर्फ उम्मीद है; साबित परीक्षा से होगा।

### C. Futures की जानकारी relative दिमाग में (funding, basis/premium, OI, long-short) ★
**[हमारा सबूत]:**
- Funding, premium और OI का data **30 coins के लिए पहले से download है** (2020 से; metrics 2020-09 से)।
- यह सिर्फ Step 10 के absolute दिमाग में परखा गया था, जो fail हुआ।
- **अभी के relative दिमागों में यह कभी नहीं परखा गया।** Code में `F_CORE` futures columns को बाहर रखता है।
- Coverage: D1 universe के 76.7% coin-days का data है, पर 2024 में घटकर 66.7% रह गया। **बाकी coins का data Binance Vision से free में download करना होगा।**

**[बाहरी]:** Chi, Hao, Hu & Ran, *An empirical investigation on risk factors in cryptocurrency futures* (Journal of Futures Markets 43(8), 2023, 1161–1180):
- 2017–21 में **basis** (futures और spot की कीमत का फर्क) coins के बीच returns के फर्क का **सबसे मज़बूत संकेत** रहा।
- Daily पर असर weekly से ज़्यादा था।
- यह **हमारे relative सवाल से सीधा मेल खाता है।**

**परीक्षा कैसे:** Step 25/29 वाला paired test।
- इस बार पहले से lock होगा कि **पैसे वाली शर्त (Calmar) भी pass होनी ज़रूरी है।**
- वजह: Steps 25 और 29 में AUC बढ़ा, पर पैसा घटा।

**खतरा:** हमारे पिछले दो "features जोड़ो" tests ने बहुत छोटा फायदा दिखाया। यह भी वैसा हो सकता है।

### D. Label बदलना: "median से आगे" की जगह "बड़ा winner"
**[हमारा सबूत]:**
- अभी label है "median से ऊपर या नीचे", इसलिए +0.1% और +30% बराबर गिने जाते हैं।
- Phase 1 और Step 27 बताते हैं कि **कमाई कुछ बड़ी चालों से आती है।**

**[बाहरी]:** Cakici, Shahzad, Będowska-Sójka & Zaremba, *Machine learning and the cross-section of cryptocurrency returns* (International Review of Financial Analysis 94, 2024)। इसके अनुसार crypto में:
- असामान्य return मुख्य रूप से **long leg** (खरीदने वाले हिस्से) से आता है। यह spot long-only के लिए अच्छी बात है।
- ज़्यादा जटिल model का फायदा सीमित है।

**परीक्षा कैसे:** वही features और recipe, सिर्फ label बदलेगा, जैसे "top 20% relative return"। जज होगा portfolio और 2022 वाला साल।

**खर्च:** मध्यम। Training दोबारा होगी।

### E. तीनों दिमागों के scores को जोड़कर एक ranking (forecast combination)
**[हमारा सबूत]:**
- तीनों के test predictions पहले से files में हैं। इसलिए **कोई नई training नहीं**, बहुत सस्ता।
- पर तीनों का आपसी मेल 0.89–0.95 है, इसलिए फायदा छोटा रहने की उम्मीद है।

**[बाहरी]:** Gu, Kelly & Xiu, *Empirical Asset Pricing via Machine Learning* (Review of Financial Studies 33(5), 2020): trees के ensembles stocks में अच्छे रहे। यह crypto पर सीधा लागू नहीं होता।

**परीक्षा कैसे:** rank-average score पर एक portfolio (100% / 50%) बनाम M_AI3 sleeves।

**ध्यान:** यह 2021–26 पर एक और कोशिश है, इसलिए A वाले हिसाब में गिनी जाएगी।

### F. Investor attention (लोगों का ध्यान), सिर्फ data इकट्ठा करना शुरू
**[बाहरी]:**
- Liu & Tsyvinski, *Risks and Returns of Cryptocurrency* (Review of Financial Studies 34(6), 2021): **time-series momentum और investor attention** crypto returns का अनुमान देते हैं।
- Google Trends पर नतीजे **मिले-जुले** हैं:
  - Nasir et al., Financial Innovation 2019: असर कम समय का रहा;
  - Arratia & López-Barrantes 2021: अनुमान "inconsistent" रहा।

**Free data [हमने जाँचा]:** Wikimedia की official pageviews API।
- इससे हर article के रोज़ के views मिलते हैं, 2015-07 से।
- आज एक test call में Bitcoin page के 1–3 सितंबर 2026 के views मिले।
- सीमा: सिर्फ उन coins के लिए, जिनका Wikipedia article है।

**करना:** पहले data download करके verify करना; उसके बाद ही feature test (C जैसा paired)।

**उम्मीद:** कम से मध्यम।

### G. खर्च घटाना (सीधा फायदा, AI की ज़रूरत नहीं)
**[हमारा सबूत]:** खर्च 0.25% से 0.40% होने पर R24 $201k से $62k। यानी खर्च ही सबसे बड़ा lever है।

**Step 2 में पहले से चालू:**
- Mainnet order book का पहला नाप: ~0.11% प्रति fill।
- BNB से fee 0.075% (Binance का official fee page)।
- 30 rounds (~15 दिन) के बाद, पहले से तय नियम से, research को असली खर्च पर दोबारा गिना जाएगा।
- अगला सवाल (बाद में): market बनाम limit order। Limit order में fill न होने का खतरा है, इसलिए यह अलग से नापना होगा।

### H. खाली पड़ा 50% पैसा
- 50% setup में आधा पैसा खाली रहता है।
- उस पर कुछ कमाना **आपका निवेश फैसला** है (जैसे exchange की earn सेवाएँ)।
- इसमें exchange और counterparty का जोखिम है।
- मैं licensed financial advisor नहीं हूँ, इसलिए इस पर सलाह नहीं दूँगा। सिर्फ बताया है कि यह विकल्प मौजूद है।

---

## 4. क्या **नहीं** करना (सबूत के साथ)
| ✗ | क्यों |
|---|---|
| और गहरे / जटिल models (बड़े neural networks) | [बाहरी] Cakici et al. 2024: crypto में जटिलता का फायदा सीमित। [हमारा सबूत] छोटे और जटिल features (Step 25/29) से AUC +0.0008 ही बढ़ा |
| छोटे और कम liquid coins की तरफ जाना | [बाहरी] Cakici et al. 2024: alpha "hard-to-trade", छोटे और volatile coins में है। Zaremba et al. (IRFA 2021) और Fičura (FRL 2023): reversal छोटे और illiquid coins में दिखता है, बड़े coins में momentum। [हमारा सबूत] सारे liquid coins पर trading नियम fail (Step 15) |
| बड़े coins पर "कल गिरा तो आज खरीदो" (reversal) | [बाहरी] Zaremba 2021: सबसे बड़े coins में daily momentum है, reversal नहीं |
| हलचल के हिसाब से size | [हमारा सबूत] Step 28 fail। [बाहरी] Cederburg et al. (JFE 2020): 103 strategies में volatility-managed रूप real-time में लगातार बेहतर नहीं निकले |
| Market timing की छठी कोशिश | [हमारा सबूत] 5 बार fail |
| Forward log चलते हुए असली दिमाग बदलना | 90 दिन की घड़ी दोबारा शुरू करनी पड़ेगी। नए सुधार सिर्फ "shadow" (साथ-साथ, अलग log में) चलेंगे |
| एक साथ बहुत सारे नए tests | हर कोशिश संयोग वाली "जीत" का मौका बढ़ाती है (A)। सिर्फ 3–4 चुने हुए, पहले से lock किए tests |

---

## 5. मेरा फैसला: क्रम (lead करते हुए)
| क्रम | काम | क्यों इस क्रम में | खर्च |
|---|---|---|---|
| 1 | **A: Overfitting का हिसाब (DSR + PBO)** | पहले यह जानना ज़रूरी है कि हमारे पास असल में कितनी skill है | कम |
| 2 | **B: 2017–19 का मंदी वाला data training में** | सबसे बड़ी कमज़ोरी (मंदी) पर सीधा वार; data पहले से verified है | मध्यम |
| 3 | **C: Futures की जानकारी relative दिमाग में** (पहले बचे coins का data download और verify) | Paper का सबसे मज़बूत संकेत, और हमने कभी नहीं परखा | मध्यम |
| 4 | **D: "बड़ा winner" वाला label** | कमाई बड़ी चालों से आती है | मध्यम |
| 5 | E: Scores को जोड़ना | सस्ता, पर छोटा फायदा अपेक्षित | कम |
| 6 | F: Attention data इकट्ठा करना | पहले data, फिर बाद में test | कम |
| लगातार | G: खर्च का नाप (Step 2), और forward log (Step 16B) | पहले से चालू | — |

**हर एक के लिए वही अनुशासन:**
- protocol lock, अलग verifier, shuffled control;
- 2022 (मंदी) और पैसे वाली शर्त अलग से;
- pass हुआ तो सिर्फ "shadow" forward log में।

**असली जज forward log ही रहेगा।**

**ईमानदार उम्मीद:**
- पिछले नतीजों को देखते हुए इनमें से ज़्यादातर छोटा या शून्य फायदा दे सकते हैं।
- सबसे ज़्यादा उम्मीद B (मंदी का data) और C (futures basis) से है, क्योंकि ये बिल्कुल नई जानकारी जोड़ते हैं, न कि उसी कीमत के data के नए रूप।

---

## 6. Sources (हर एक की जाँच कम से कम दो जगह से)
- Liu, Tsyvinski & Wu, *Common Risk Factors in Cryptocurrency*, Journal of Finance 77 (2022) 1133–1177: [SSRN](https://papers.ssrn.com/abstract=3379131) · [NBER w25882](https://www.nber.org/papers/w25882.pdf) · [Yale Cowles](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
- Liu & Tsyvinski, *Risks and Returns of Cryptocurrency*, Review of Financial Studies 34(6) (2021) 2689–2727: [IDEAS/RePEc](https://ideas.repec.org/a/oup/rfinst/v34y2021i6p2689-2727..html) · [SSRN](https://papers.ssrn.com/abstract=3226806) · [NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- Chi, Hao, Hu & Ran, *An empirical investigation on risk factors in cryptocurrency futures*, Journal of Futures Markets 43(8) (2023) 1161–1180: [IDEAS/RePEc](https://ideas.repec.org/a/wly/jfutmk/v43y2023i8p1161-1180.html) · [Infona](https://www.infona.pl/resource/bwmeta1.element.wiley-fut-v-43-i-8-fut22425)
- Cakici, Shahzad, Będowska-Sójka & Zaremba, *Machine learning and the cross-section of cryptocurrency returns*, International Review of Financial Analysis 94 (2024) 103244: [Open repository](https://open.icm.edu.pl/handle/123456789/25543)
- Fieberg, Liedtke, Poddig, Walker & Zaremba, *A Trend Factor for the Cross-Section of Cryptocurrency Returns*, JFQA: [Cambridge](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/S0022109024000747) · [JFQA pdf](https://jfqa.org/wp-content/uploads/2024/09/24955-trend-factor-cross-section-crypto-returns.pdf)
- Zaremba et al., *Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets*, IRFA 2021: [repository](https://earsiv.medeniyet.edu.tr/items/23a96c9f-3952-4bdf-aec5-abafb3aaab70)
- Fičura, size और volume का momentum/reversal पर असर, FRL 2023: [VŠE working paper](https://wp.ffu.vse.cz/artkey/wps-202301-0003_impact-of-size-and-volume-on-cryptocurrency-momentum-and-reversal.php)
- Gu, Kelly & Xiu, *Empirical Asset Pricing via Machine Learning*, Review of Financial Studies 33(5) (2020) 2223–2273: [NBER](https://nber.org/papers/w25398) · [SSRN](https://papers.ssrn.com/abstract=3306110)
- Cederburg, O'Doherty, Wang & Yan, *On the performance of volatility-managed portfolios*, Journal of Financial Economics 138(1) (2020) 95–117: [Lehigh pdf](https://www.lehigh.edu/~xuy219/research/COWY.pdf) · [Arizona](https://experts.arizona.edu/en/publications/on-the-performance-of-volatility-managed-portfolios/)
- Bailey & López de Prado, *The Deflated Sharpe Ratio*, Journal of Portfolio Management 2014: [SSRN 2460551](https://papers.ssrn.com/abstract=2460551)
- Bailey, Borwein, López de Prado & Zhu, *The Probability of Backtest Overfitting*, Journal of Computational Finance 2017: [SSRN 2326253](https://papers.ssrn.com/abstract=2326253) · [CRAN pbo](https://cran.hafro.is/web/packages/pbo/vignettes/pbo.html)
- Gârleanu & Pedersen, *Dynamic Trading with Predictable Returns and Transaction Costs*, Journal of Finance 68(6) (2013): [NBER](https://www.nber.org/papers/w15205)
- Nasir et al., Google searches और Bitcoin, Financial Innovation 2019: [White Rose](https://eprints.whiterose.ac.uk/184076/1/s40854-018-0119-8.pdf)
- Wikimedia pageviews API (2015-07 से): [reference](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html); आज एक call से जाँचा गया।
