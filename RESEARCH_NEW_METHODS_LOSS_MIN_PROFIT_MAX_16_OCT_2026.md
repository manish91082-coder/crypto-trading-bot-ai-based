# नए तरीके (अब तक की reports से बिल्कुल अलग): नुकसान कम से कम, फायदा ज़्यादा से ज़्यादा
**16 अक्टूबर 2026, 1D, spot + futures**

**दायरा:** आपके निर्देश से इसमें **सिर्फ वे तरीके हैं जो पिछली किसी report में नहीं आए।**

**पहले आ चुके (इसलिए यहाँ नहीं):**
- swing, relative ranking, trend, mean reversion, breakout;
- carry, pairs, options, listing/unlock;
- on-chain, sentiment, calendar, arbitrage, grid;
- RL, vol targeting, Kelly, CPPI, risk parity, HMM, LTR, meta-labeling।

**अनुशासन:**
- [बाहरी] = शोध (link सहित)।
- [हमारा] = हमारे verified data पर आज की जाँच।
- ⚠ = एक ही स्रोत / विवादित / सिर्फ सार पढ़ा।
- Investment और staking नहीं।
- मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## भाग 1. नए संकेत: कमाई के नए स्रोत

### 1.1 Lottery (MAX) effect: ★ सबसे मज़बूत नया उम्मीदवार
**क्या है:** जिन coins में हाल में एक दिन का बहुत बड़ा उछाल आया ("lottery" जैसे coins), लोग उन्हें ज़्यादा कीमत देकर खरीदते हैं, और बाद में वे पीछे रहते हैं।

**[बाहरी]:**
- Grobys & Junttila, *Journal of International Financial Markets, Institutions and Money* (2021): सबसे कम और सबसे ज़्यादा MAX वाले समूहों में **हर हफ्ते 1.5% से ज़्यादा का अंतर**। यह BTC risk और microstructure के नियंत्रण के बाद भी बना रहा ([JYX](https://jyx.jyu.fi/handle/123456789/74624), [Vaasa](https://www.uwasa.fi/en/newshub/news/new-study-detects-lottery-behavior-cryptocurrency-markets))।
- ⚠ उनका sample छोटा है: 20 coins, 2016–2019।
- एक बाद का अध्ययन intraday पर भी यही पाता है: MAX में 1 standard deviation बढ़ने पर अगला return −0.043% ([RePEc](https://ideas.repec.org/a/eme/sefpps/sef-07-2024-0461.html))।

**[हमारा, आज: सिर्फ विवरण, test नहीं]:**
- **Data:** हमारे Step 19 के 41,824 coin-days (2021–26, ~20 बड़े coins प्रतिदिन)।
- **MAX** = पिछले 7 दिनों का सबसे बड़ा एक-दिन का return, जो उस दिन के बंद होने तक पता होता है।
- **Label:** अगले 5 दिन में median से आगे रहा या नहीं।

| MAX समूह (रोज़ 5 हिस्से) | सबसे कम | 2 | 3 | 4 | सबसे ज़्यादा |
|---|---|---|---|---|---|
| अगले 5 दिन median से आगे | **52.6%** | 51.9% | 49.0% | 45.9% | **41.5%** |

- **हर साल 2021–2026 में** सबसे ज़्यादा MAX वाला समूह सबसे नीचे या लगभग सबसे नीचे रहा (2026: 37.9%)।
- **हमारा AI score इससे पहले से जुड़ा है:** रोज़ का औसत Spearman correlation **−0.38**। यानी दिमाग इसका कुछ हिस्सा पहले से पकड़ता है। अलग से जोड़ने पर कितना नया फायदा मिलेगा, यह पता नहीं।

**ईमानदार चेतावनी:**
- यह जाँच उसी data पर हुई है जो पहले से देखा जा चुका है।
- इसे फायदे का सबूत नहीं माना जा सकता, सिर्फ test करने का कारण माना जा सकता है।
- Test pre-registered हो, और उसमें नकली control हो।

**उपयोग के विचार (test करने के लिए):**
- (क) **Long book से** सबसे ज़्यादा MAX वाले coins हटाना।
- (ख) **Short के लिए** ऊँचे-MAX वाले coins को प्राथमिकता, पर stop के साथ, क्योंकि यही coins squeeze भी करते हैं।

**नुकसान/फायदा:** long book में नुकसान घटाना और short book की कमाई बढ़ाना, दोनों।

### 1.2 Low-volatility / idiosyncratic volatility anomaly: ❌ सबूत आपस में टकराते हैं
- [बाहरी] University of Sydney (*Journal of Empirical Finance*, 4,000+ coins, 2015–22): सबसे कम idiosyncratic risk वाले coins +80.6% सालाना, सबसे ज़्यादा वाले −9.36% ([Sydney](https://www.sydney.edu.au/news-opinion/news/2023/11/01/huge-crypto-study-finds-high-risk-doesnt-equal-reward.html))।
- **उल्टा:** Burggraf & Rudolf (*Finance Research Letters* 2021, 1,000 coins): "कोई significant low-vol premium नहीं" ([RePEc](https://ideas.repec.org/a/eee/finlet/v40y2021ics154461232030667x.html))।
- **और उल्टा:** Zhang & Li (*RIBAF* 2020): idiosyncratic volatility का return से **positive** संबंध ([RePEc](https://ideas.repec.org/a/eee/riibaf/v54y2020ics0275531920301926.html))।
- **फैसला:** दिशा ही पक्की नहीं है, इसलिए अभी नहीं।

### 1.3 BTC के बाद alts का चलना (lead-lag): ❌ 1D पर नहीं
- [बाहरी] Kurihara & Matsumoto (*Asia-Pacific Financial Markets* 2026): छोटे coins BTC की चाल पर देर से प्रतिक्रिया करते हैं। ⚠ यह hourly/intraday पर है, और कम liquid coins में सबसे मज़बूत।
- Daily पर सबूत कमज़ोर और कभी उल्टा (JBFE 2024; Pirgaip et al. 2019) ([UW](https://press.wz.uw.edu.pl/jbfe/vol2024/iss1/5))।
- **फैसला:** हमारे 1D, बड़े coins वाले system के लिए नहीं।

### 1.4 Stablecoin (Tether) issuance से BTC का अनुमान: ❌ नहीं
- [बाहरी] Griffin & Shams ("Is Bitcoin Really Un-Tethered?", *Journal of Finance* 2020): 2017 की तेज़ी में Tether के प्रवाह वाले 1% घंटों से BTC की compound कमाई का 50% से ज़्यादा आया।
- पर यह **manipulation का अध्ययन** है, trading signal नहीं, और विवादित है। दूसरे अध्ययन में daily data पर असर insignificant रहा ([Quantpedia](https://quantpedia.com/a-very-influential-paper-about-tether-bitcoin-relationship-manipulation/), [Bitcoin Magazine](https://bitcoinmagazine.com/markets/new-study-argues-tether-wasnt-used-prop-bitcoin-price))।
- **फैसला:** पुराना दौर, विवादित, और signal नहीं।

### 1.5 Macro events (FOMC, CPI, नौकरी के आँकड़े): 🟡 दिशा नहीं, जोखिम-नियंत्रण के लिए
**[बाहरी]:**
- Fed Board के शोधकर्ता (Kroner, Mohammed, Vega, मार्च 2026): FOMC, CPI और NFP पर crypto की volatility, volume और spread उछलते हैं। ⚠ यह secondary सार से है ([summary](https://rwatimes.substack.com/p/how-do-cryptocurrencies-price-economic))।
- Volmex: CPI और Fed के फैसलों पर BTC की volatility बढ़ती है, फिर घोषणा के बाद implied volatility गिरती है ([PDF](https://volmex.finance/Macroeconomic%20Announcements%20Fuel%20Volatility%20An%20In-Depth%20Analysis.pdf))।
- BlockScholes: 2022 के बीच से CPI surprise और उसी दिन के BTC return में negative संबंध ([BlockScholes](https://www.blockscholes.com/premium-research/bitcoins-macro-correlations))।
- **उल्टा:** NY Fed (Benigno & Rosa 2023) में BTC macro news से लगभग "orthogonal" निकला ([NY Fed](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1052.pdf))।

**फैसला:**
- दिशा का अनुमान नहीं लगाना है।
- **नुकसान-नियंत्रण का विचार:** FOMC/CPI वाले दिन नए shorts न खोलना, या gross थोड़ा घटाना।
- पहले से lock किया gate हो, घोषणाओं की तारीखें सरकारी calendar से ली जाएँ, और नकली-तारीखों वाला control हो।

### 1.6 Liquidation cascade के बाद: ❌ सबूत नहीं, पर एक जोखिम-सीख
- [बाहरी] अक्टूबर 2025 के cascade के बाद spread ~23 दिन में सामान्य हुए, **पर order book की गहराई महीनों तक 1/4 से 1/3 कम रही** (*Journal of FinTech & Digital Assets*) ([Lincoln](https://journals.lincoln.ac.nz/index.php/JFDA/article/view/1395))।
- बाद में उछाल आने के सिर्फ विवरण मिले, मापे हुए आँकड़े नहीं ([CoinShares](https://coinshares.com/insights/knowledge/billions-in-liquidations-what-happened/))।
- **फैसला:** trading signal नहीं। **सीख:** बड़े cascade के बाद slippage मान्यता से ज़्यादा होगा, इसलिए stop की slippage का अनुमान बढ़ाकर रखें।

---

## भाग 2. Portfolio बनाने के नए तरीके (नुकसान घटाने के लिए)

### 2.1 Hierarchical Risk Parity (HRP, López de Prado 2016): ❌ हमारे लिए नहीं
- [बाहरी] Burggraf (*Finance Research Letters* 2021): crypto में HRP ने tail-risk-adjusted return बेहतर किया ([RePEc](https://ideas.repec.org/a/eee/finlet/v38y2021ics154461232030177x.html))।
- **पर:** UCEMA (2026; Binance universe, survivorship-corrected, 2020–26):
  - HRP का Sharpe सिर्फ 0.69–0.75 रहा;
  - **Covid के बाद 51–64% पूँजी गई**;
  - "edge सांख्यिकीय रूप से नाज़ुक" ([UCEMA](https://ucema.edu.ar/documento-trabajo/hierarchical-risk-parity-variants-cryptocurrency-portfolios-denoising-detoning), [PDF](https://maynard.ucema.edu.ar/sites/default/files/2026-06/dt928.pdf))।
- **फैसला:** HRP long-only allocation का तरीका है। हमारे 5+5 वाले long-short में इसकी जगह नहीं।

### 2.2 Rebalancing premium (volatility harvesting, "Shannon's demon"): ✅ पहले से मिल रहा है, बस समझना ज़रूरी
- [बाहरी] Willenbrock: कम मेल वाले, हिलते assets को बार-बार बराबर करने से अतिरिक्त compound बढ़त मिलती है; crypto में significant premium ([Quantpedia](https://quantpedia.com/estimating-rebalancing-premium-in-cryptocurrencies/))। ⚠ पूरा paper नहीं पढ़ा।
- यह गणित (Fernholz) से भी आता है।
- **हमारे लिए मतलब:** हम हर position को बराबर (10%) रखकर rebalance करते हैं, इसलिए यह premium कुछ हद तक पहले से मिल रहा है।
- **संतुलन:** बार-बार rebalance से premium मिलता है, पर खर्च बढ़ता है। इसलिए E5 (hysteresis) में दोनों का संतुलन देखना ज़रूरी है।

### 2.3 Dynamic hedge ratio (DCC-GARCH): 🟡 E1 के BTC hedge का आकार तय करने में
- [बाहरी] BTC futures से BTC spot का hedge: effectiveness 0.64 (*Frontiers* 2021)। Hedge ratios समय के साथ बदलते हैं ([Frontiers](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2021.704900/pdf))।
- Alt-coins पर DCC-GARCH का सीधा अध्ययन कम है; सिर्फ एक Erasmus thesis (copula) है ([thesis](https://thesis.eur.nl/pub/59420/Master_Thesis_Final_Dylan_van_Gemeren_477690.pdf))।
- पिछली research में crypto betas का अनुमान कमज़ोर निकला था (R² ~20%)।
- **फैसला:** E1 में BTC hedge के लिए दो विकल्प: तय अनुपात, या shrink किया हुआ rolling/DCC beta। सिर्फ 2 variants।

---

## भाग 3. जोखिम का नया गणित

### 3.1 Extreme Value Theory (EVT, peaks-over-threshold): ✅ जोखिम-monitor के लिए (trading नियम नहीं)
- [बाहरी] Opala, Fischer & Svoboda (2022): BTC/ETH/LTC पर **सिर्फ EVT (POT) 99.9% के backtest में पास हुआ**; बाकी तरीके early-2021 की volatility में fail हुए ([preprint](https://www.preprints.org/manuscript/202307.0187))। Gkillas & Katsiampa (*Economics Letters* 2018) ने भी crypto tail risk नापा ([SHU](https://shura.shu.ac.uk/18993/))।
- **हमारे लिए:** normal distribution मानकर tail risk का अनुमान कम आता है।
- **विचार:** EVT से हर दिन portfolio का 99% / 99.9% का tail-loss अनुमान बनाना, और उससे kill switch व per-coin cap को परखना। Trading पर कोई असर नहीं, सिर्फ जानकारी और सीमा।

### 3.2 Exit का design (trailing stop, take-profit, time-stop, triple-barrier): 🟡 कमज़ोर सबूत
- [बाहरी] ⚠ arXiv preprint (2604.27150, 900+ crypto trades): सख्त loss-सीमा, जल्दी profit लेना और नज़दीकी trailing ने risk-adjusted नतीजा सुधारा ([arXiv](https://arxiv.org/pdf/2604.27150))। एक ही system के trades हैं, peer-reviewed नहीं।
- **[हमारा]:**
  - F7 का stop (×1.5) PASS है।
  - **Step 26 का "exit दिमाग" FAIL** रहा था।
- **फैसला:** shorts पर trailing stop एक test हो सकता है (अगला round), पर सबूत कमज़ोर है।

---

## भाग 4. AI का नया तरीका

### 4.1 Conformal prediction / "अनिश्चित हो तो trade मत करो": 🟡 विचार अच्छा, crypto सबूत नहीं
- [बाहरी] Conformal Predictive Portfolio Selection (equity) में बेहतर returns ([arXiv 2410.16333](https://arxiv.org/html/2410.16333v2))।
- ⚠ FinAbstain के नतीजे लेखकों ने खुद "simulated" कहे हैं ([arXiv 2607.24875](https://arxiv.org/pdf/2607.24875))।
- Cross-sectional stock ranker में अनिश्चित दिनों पर exposure घटाने का विचार ([arXiv 2603.13252](https://arxiv.org/pdf/2603.13252))।
- **कोई crypto empirical अध्ययन नहीं मिला।**
- **फैसला:** E8 (confidence-gated shorts) के साथ मिलाकर ही, अलग test नहीं।

## भाग 5. Execution (फायदा बढ़ाने के लिए)

### 5.1 Optimal execution (Almgren–Chriss, TWAP/VWAP में बाँटना): ❌ $10k पर ज़रूरत नहीं
- Order को टुकड़ों में बाँटना बड़े orders के market impact के लिए है (Almgren & Chriss 2000, *Journal of Risk*)।
- **[हमारा]:** हमारी cost study बताती है कि ~$333–1,000 के orders पर खर्च मुख्यतः fee और spread है, impact नहीं।
- **फैसला:** limit बनाम market order (M9) ज़्यादा काम का है। टुकड़े करना सिर्फ बड़ी पूँजी पर।

---

## भाग 6. सार और प्राथमिकता

| # | नया तरीका | सबूत | नुकसान ↓ / फायदा ↑ | फैसला |
|---|---|---|---|---|
| 1 | **Lottery (MAX) filter** | peer-reviewed + [हमारा] हर साल लगातार | दोनों | ★ **test करें (N1)** |
| 2 | **Macro-event gate** (FOMC/CPI पर नए shorts नहीं / gross कम) | volatility उछाल: कई स्रोत; दिशा: विवादित | नुकसान ↓ | 🟡 test (N2) |
| 3 | **EVT tail-risk monitor** | peer-reviewed backtest | नुकसान ↓ (सीमाएँ सही) | ✅ बनाएँ (N3, trading पर असर नहीं) |
| 4 | **Shrunk/DCC beta से BTC hedge** | आंशिक | नुकसान ↓ | 🟡 E1 का variant |
| 5 | Shorts पर trailing stop | कमज़ोर | नुकसान ↓ | अगला round |
| 6 | Conformal / अनिश्चितता gate | crypto में नहीं | — | E8 के साथ |
| 7 | Rebalancing premium | सिद्धांत + Quantpedia | फायदा ↑ (पहले से) | E5 में संतुलन |
| — | Low-vol, lead-lag (1D), stablecoin, liquidation-signal, HRP, Almgren–Chriss | टकराव / गलत timeframe / अनुपयुक्त | — | ❌ नहीं |

### Test के लिए पहले से lock करने लायक नियम

**N1: MAX filter**
- **MAX** = पिछले 7 दिनों का सबसे बड़ा daily return।
- **Long:** उस दिन के top-MAX 20% coins long के लिए अयोग्य; उनकी जगह अगला rank।
- **Short:** कोई बदलाव नहीं (variant A), या top-MAX को short में प्राथमिकता (variant B)।
- **Gates बनाम F7:** long side का payoff और PF बेहतर; कुल गिरावट ≤ F7; 2022 > 0।
- **Control:** उतने ही coins को random हटाना।
- **खुलासा:** यह pattern आज data पर देखा जा चुका है।

**N2: Macro gate**
- Fed और BLS की सरकारी तारीखों पर उस दिन नए shorts नहीं (variant A), या पूरा gross ×0.5 (variant B)।
- **Control:** उतनी ही random तारीखें।
- **Primary metric:** सबसे बुरे 5% दिन (CVaR)। Sharpe नहीं।

**N3: EVT monitor**
- रोज़ 99% और 99.9% का tail-loss अनुमान, F4 के साथ log।
- कोई trading नियम नहीं।
- 90 दिन बाद जाँच: अनुमान सही निकले या नहीं।

**Trial budget:** पिछली योजना के Round 1 (E1–E4 + E11) के साथ **सिर्फ N1** जोड़ें। N2 अगले round में। N3 trading नहीं, इसलिए trial नहीं गिना जाएगा।

**कुल ईमानदार निष्कर्ष:**
- पूरी खोज के बाद **सिर्फ एक नया कमाई का संकेत (MAX) ठोस दिखा।** उसका भी कुछ हिस्सा हमारा AI पहले से पकड़ता है।
- बाकी नए तरीके या तो **जोखिम-नियंत्रण** के हैं (macro gate, EVT, hedge sizing), या सबूत में कमज़ोर या अनुपयुक्त हैं।
- सबसे बड़ा फायदा अब भी खर्च घटाने, ढाँचे (long-short + risk नियम) और forward सबूत से आएगा।
