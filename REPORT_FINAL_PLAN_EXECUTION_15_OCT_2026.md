# अंतिम योजना का execution: क्रम 1 से 8 (चलती रिपोर्ट)

**GitHub:** कुछ नहीं | **Trade:** कोई नहीं | **Testnet ETH position:** छुई नहीं

**हर step:** protocol lock → code → अलग verifier → Hindi हिस्सा यहाँ।

---

## क्रम 1, S1: हमारे 2021–26 के नतीजों में किस्मत कितनी है?
**Protocol:** `logs/research_overfit_s1/S1_PROTOCOL_PREREGISTERED.md`, 08:21 UTC पर lock।
**Verifier:** V1–V4 PASS।

**सूत्रों की जाँच:**
- दोनों सूत्र मूल papers के text से लिए गए।
- Deflated Sharpe का code paper का अपना उदाहरण हूबहू दोहराता है: 0.9004 / 0.9505 / 0.9505।
- Verifier ने DSR को scipy के बिना, और 403 PBO combinations को सीधे-सादे loops से दोबारा गिना।

**Data:**
- 2021–26 पर चलाए गए **60 अलग strategy-tests** की daily equity।
- 113 files, सबके SHA जाँचे गए।
- Placebo (नकली दिमाग), cost-stress और हूबहू duplicates बाहर रखे गए।

### नतीजे
| | Sharpe (सालाना) | DSR, N = 60 | N = 75 | N = 150 | 95% पर पक्का? |
|---|---|---|---|---|---|
| **M_AI3-50%** (हमारी सिफारिश) | 0.93 | **0.44** | 0.41 | 0.31 | **नहीं** |
| **R24 अकेला** (सबसे अच्छा sleeve) | 1.02 | **0.54** | 0.50 | 0.40 | **नहीं** |

- **PBO = 65%** (12,870 combinations)। यानी जो strategy पहले आधे data में सबसे अच्छी चुनी गई, वह दूसरे आधे में 65% बार बाकियों के median से नीचे रही। Paper का आम नियम PBO > 5% होने पर reject करता है।
- चुनी गई strategy का दूसरे आधे में घाटा: 20% combinations में।

**सिर्फ report के लिए (protocol से बाहर):**
- बहुत-से tests असल में एक ही strategy के रूप हैं (जैसे f = 30/50/75/100%), इसलिए असली स्वतंत्र N कम है।
- M_AI3-50% का DSR: N = 20 पर 0.63; N = 10 पर 0.75; N = 5 पर 0.86; N = 2 पर 0.97।
- यानी **"पक्का" सिर्फ तब होता, जब हमने लगभग 2 ही चीज़ें परखी होतीं।**

**तुलना:** BTC hold का Sharpe 0.57–0.60 है, और सारे coins बराबर रखने (EW) का 0.59। हमारी strategy 0.93 पर है, यानी आगे दिखती है, पर यह बढ़त सांख्यिकी के हिसाब से पक्की नहीं।

### इसका ईमानदार मतलब
1. **2021–26 का पैसे वाला नतीजा** ($53,884 आदि) **साबित नहीं करता** कि यह किस्मत नहीं है। इतनी कोशिशों के बाद ऐसा नतीजा संयोग से भी मिल सकता है।
2. **जो अब भी मज़बूत है:** relative skill (AUC) का वह सबूत, जो **कभी न देखे 2018–19 data पर frozen दिमागों** से आया (0.526–0.546, CI 0.5 से ऊपर)। वह selection से नहीं, एक बार की परीक्षा से आया था। पर वह भी पैसे का सबूत नहीं, सिर्फ ranking का है।
3. **इसलिए forward log ही असली जज है।** उसी के बाद, और छोटी रकम से ही असली पैसा।
4. **आगे के हर नए test से N और बढ़ेगा।** इसलिए आगे के steps में pass की शर्तें सख्त रहेंगी, और हर नतीजा इसी नज़र से पढ़ा जाएगा।

---

## क्रम 2, F1 + F2: Long-short (AI के मज़बूत coins long, सबसे कमज़ोर coins futures पर short): **PASS, पर गंभीर चेतावनियों के साथ**
**Protocol:** `logs/strategy_f2_longshort/F2_PROTOCOL_PREREGISTERED.md`
**Verifier:** V1–V3 PASS। Verifier ने 150 short trades की कीमत, funding (सीधे loop से), liquidation और P&L दोबारा गिने।

**Data (F1):**
- Binance Vision से USD-M perpetual 1h candles और funding, 2020–26, 135 coins।
- **21,870 files: 12,912 का checksum सही, 8,958 के लिए 404 (उस समय वह perpetual नहीं था), कोई खराब file नहीं।**
- Scale जाँच: 132 coins ठीक; 3 बाहर (IDEX, RAY, STRAX); 3 का perpetual ही नहीं था।

**G0:** short बंद करने पर engine ने Step 27 के research नतीजे **cent तक** दोहराए, 2021–26 और 2018–19 दोनों में।

**Lock के बाद 1 बदलाव (दर्ज):**
- Funding अब isolated position के margin में जाती है, wallet में नहीं। तीन sources (Binance support thread, Pluang, BitMEX) यही कहते हैं।
- Liquidation का नियम भी उसी के हिसाब से बदला।
- पहले वाला run cash negative होने पर रुक गया था; उससे कोई long-short नतीजा नहीं बना था।

### नतीजे (M_AI3, $10k, 2021–26 में असली perpetual data)
| | Long-only 50% | **Long-short** | Long-short (short का खर्च 0.20%) | नकली दिमाग वाला long-short |
|---|---|---|---|---|
| अंतिम रकम | $53,884 | **$110,479** | $84,628 | $2,374 |
| सबसे बड़ी गिरावट | 49.0% | **30.3%** | 30.2% | 84.5% |
| Calmar | 0.695 | **1.712** | 1.493 | −0.26 |
| 2022 (मंदी) | −41.6% | **+45.4%** | +35.8% | −36.3% |
| 2025 | −7.5% | +46.8% | | |

| 2018–19 (synthetic short*) | Long-only 50% | **Long-short** |
|---|---|---|
| अंतिम रकम | $6,546 | **$11,438** |
| सबसे बड़ी गिरावट | 53.9% | **18.8%** |
| 2018 | −40.1% | +4.2% |

\* उस समय perpetual futures नहीं थे। इसलिए spot की कीमत पर short माना गया: funding नहीं, और हर coin short के लायक माना गया। यानी यह आशावादी (optimistic) अनुमान है।

**सारे gates (G1–G6) PASS।**

### ईमानदार चेतावनियाँ (बहुत ज़रूरी)
1. **Short की कमाई कुछ ही trades पर टिकी है।** हर sleeve में सबसे बड़े 8 short trades कुल short कमाई का 73–107% हैं। ये ज़्यादातर **2025–26 के नए listed coins** (BANK, SYN, HEMI, EIGEN आदि) हैं, जो बाद में बहुत गिरे।
   - हर sleeve के सबसे बड़े 10 short trades हटाएँ, तो नतीजा **~$110k से ~$69k** रह जाता है। यह अब भी long-only ($54k) से ऊपर है। (सिर्फ report के लिए, मोटा हिसाब।)
2. **Short वाला हिस्सा तेज़ी के सालों में घाटे में रहा:** 2021, 2023 और 2024 में। कमाई 2022, 2025 और 2026 में आई।
3. **69 बार liquidation हुआ** (short के बाद कीमत दोगुनी हुई)। ये नुकसान गिने गए हैं, पर असल में यह सबसे बड़ा खतरा है।
4. **Short वालों ने कुल मिलाकर funding चुकाई** (करीब $40k, तीनों sleeves मिलाकर), यह गिनी गई है। कमज़ोर coins पर short करने की भीड़ रहती है।
5. **सिर्फ hedge या skill? (सिर्फ report के लिए)** AI के long + सिर्फ BTC का short देने पर 2021–26 में $35.6k और 2018–19 में $6.3k आया। यानी **फायदा AI के चुने कमज़ोर coins से है, सिर्फ market hedge से नहीं।** नकली दिमाग वाला long-short भी डूबा ($2,374)।
6. **Deflated Sharpe (N = 79): 0.875।** पहले के 0.44 से बहुत बेहतर, पर **अब भी 95% वाली सीमा से नीचे**।
7. यह सब 2021–26 के उसी data पर है, जिसे हम बहुत बार देख चुके हैं। **असली जज सिर्फ forward (paper) log होगा।**

**फैसला (protocol के हिसाब से):** PASS → **long-short paper forward log (F4) का उम्मीदवार।** कोई असली या futures order नहीं।

---

## क्रम 3, S2: 2017–19 का मंदी वाला data training में: **तीनों दिमाग FAIL**
**Protocol:** `logs/research_s2_bear_training/S2_PROTOCOL_PREREGISTERED.md`

**Verifier:** तीनों PASS।
- AUC सीधे Mann-Whitney से दोबारा गिना।
- R6 का 2022-06 वाला model शुरू से दोबारा train किया: 3,600 predictions हूबहू मिलीं (फर्क 8e-17)। यानी training में भविष्य का data नहीं घुसा।

**Lock के बाद 1 बदलाव (दर्ज):** D1 में 2017–19 वाले rows में "half" column नहीं था। पहला run model बनने से पहले ही रुक गया था। Fix के बाद दोबारा चलाया।

| दिमाग | 2017–19 के जोड़े गए rows | AUC पहले → बाद | 2022 में AUC का फर्क | $10k (2021–26) पहले → बाद | 2022 का return पहले → बाद | फैसला |
|---|---|---|---|---|---|---|
| R6 (4h) | 40,622 | 0.5676 → 0.5673 | −0.003 | $98,735 → $62,748 | −74.1% → −67.2% | **FAIL** |
| R24 (1h) | 54,064 | 0.5653 → 0.5649 | −0.0015 | $201,548 → $104,091 | −67.0% → −69.9% | **FAIL** |
| D1 (R5) | 8,382 | 0.5593 → 0.5591 | +0.0076 | $74,452 → $47,957 | −73.6% → −73.3% | **FAIL** |

**मतलब:**
- पुराना मंदी वाला data जोड़ने से ranking की skill **नहीं बढ़ी**, और पैसा घटा। 2018–19 का data छोटा भी है: कुल का 3.5–10%।
- **सबसे ज़रूरी सीख:** मंदी की कमज़ोरी training data से नहीं सुलझती। वह सुलझती दिखती है **portfolio के ढाँचे** से, यानी long-short (F2), जहाँ इसी दिमाग ने 2022 में +45% किया।
- **फैसला:** दिमाग पहले जैसे ही रहेंगे। 2018–19 अब भी exam के तौर पर इस्तेमाल हो सकता है, क्योंकि ये नए models अपनाए नहीं गए।

---

## क्रम 4, S3: futures की जानकारी (funding + basis) relative दिमागों में: **तीनों दिमाग FAIL**
**Protocol:** `logs/research_s3_futures_features/S3_PROTOCOL_PREREGISTERED.md` (SHA lock: पहले दर्ज, फिर run)

**जोड़े गए 6 features** (सिर्फ जानकारी, futures में कोई trade नहीं): basis_now, basis_7d, fund_24h, fund_7d, और basis व funding का उसी bar में rank।
- **इन्हें क्यों आज़माया:** Chi et al. (2023) के मुताबिक basis सबसे मज़बूत predictor था।
- **Data:** F1 वाली SHA-checked perpetual files।
- **Coverage:** तीनों दिमागों में test rows में से 98.6% के पास basis मौजूद था।

**Verifier:** तीनों PASS।
- 60 rows के features raw files से सीधे loops द्वारा दोबारा बनाए। सिर्फ उस bar के बंद होने तक का data लिया, यानी भविष्य का data नहीं।
- AUC सीधे Mann-Whitney से दोबारा गिना, और साल-दर-साल फर्क व gates भी दोबारा गिने।

**Lock के बाद 1 बदलाव (सिर्फ verifier में, दर्ज):**
- D1 के rank check में verifier गलत समूह से तुलना कर रहा था: सिर्फ file की rows।
- Code पूरे दैनिक panel में rank बनाता है। इसलिए verifier अब panel दोबारा बनाकर 60 rows जाँचता है: PASS।
- Model, predictions या कोई दावा नहीं बदला। R6 और R24 दोबारा verify किए: PASS।

| दिमाग | AUC पहले → बाद | AUC फर्क का 95% CI | कितने सालों में AUC बढ़ा (6 में से) | $10k (2021–26) पहले → बाद | Calmar पहले → बाद | सबसे बड़ी गिरावट पहले → बाद | 2022 पहले → बाद | फैसला |
|---|---|---|---|---|---|---|---|---|
| R6 (4h) | 0.5676 → 0.5677 | −0.0016 … +0.0016 | 4 | $98,735 → $78,871 | 0.625 → 0.583 | 78.4% → 74.2% | −74.1% → −67.1% | **FAIL** |
| R24 (1h) | 0.5653 → 0.5659 | −0.0015 … +0.0023 | 3 | $201,548 → $86,201 | 0.92 → 0.571 | 74.7% → 79.6% | −67.0% → −76.0% | **FAIL** |
| D1 (R5) | 0.5593 → 0.5621 | −0.0010 … +0.0066 | 3 | $74,452 → $39,657 | 0.515 → 0.312 | 81.3% → 87.0% | −73.6% → −77.3% | **FAIL** |

**मतलब:**
- **Ranking की skill में कोई पक्का सुधार नहीं।** तीनों के CI शून्य को पार करते हैं। D1 में AUC +0.0028 बढ़ा, पर यह भी पक्का नहीं है।
- **पैसा तीनों में घटा:** R24 में आधे से भी कम, D1 में लगभग आधा। Steps 25 और 29 में भी यही पैटर्न दिखा था: AUC थोड़ा ऊपर, पैसा नीचे। इसलिए money gate ज़रूरी था।
- **ईमानदार कमियाँ:**
  1. 2018–19 का exam संभव नहीं था, क्योंकि उस समय perpetual नहीं थे।
  2. D1 में test coins का rank सिर्फ test coins के बीच बना, जबकि research वाला D1 नियम known coins के सापेक्ष rank बनाता है। यह protocol के शब्दों के मुताबिक था, पर research नियम से अलग था। नतीजा देखने के बाद इसे बदलकर दोबारा नहीं चलाया, ताकि खुद को धोखा न हो।
- **फैसला:** दिमाग पहले जैसे ही रहेंगे। Futures data का अब तक साबित फायदा **सिर्फ short करने की क्षमता (F2)** में है, features के रूप में नहीं।
- S2 और S3 दोनों FAIL हुए। इसलिए **F3** (बेहतर दिमागों के साथ long-short) की शर्त पूरी नहीं हुई, और F3 नहीं चलेगा।

---

## क्रम 5, F7: long-short के short हिस्से पर risk नियम: **PASS** (verified)
**Protocol:** `logs/strategy_f7_risk/F7_PROTOCOL_PREREGISTERED.md` (SHA lock: a3a945…, run से पहले)

**Code:**
- Engine: `src/pipeline_1d/f7_risk.py`। यह F2 engine की copy है, F2 का engine छुआ नहीं गया।
- Runner: `f7_run.py`।
- Verifier: `src/audits/verify_f7_claims.py`।

**ईमानदार खुलासा:** F2 के short trades पहले ही देखे जा चुके थे। उनमें 50% से ज़्यादा नुकसान वाले trades ने हर sleeve में $132k–$198k डुबोए थे। इसलिए F7 skill का नया सबूत **नहीं** है। यह risk की परत है, जो live system में वैसे भी लगनी है। नियमों की values risk के तर्क से तय की गईं, खोजकर नहीं।

**नियम (RS):**
1. **Stop:** हर short पर entry × 1.50 का stop।
   - Bar का open stop के पार खुले, तो open × 1.01 पर निकलेंगे।
   - Bar के अंदर high stop छुए, तो stop × 1.01 पर निकलेंगे।
   - Live में यही STOP_MARKET reduce-only order होगा।
2. **Cooldown:** जिस coin पर stop या liquidation हुआ, उसे 30 दिन short नहीं करेंगे।
3. **आकार:** पहले जैसा। 5 shorts, हर एक 10%, 1x isolated।
4. **Kill switch (K1):** account चोटी से 35% नीचे जाए तो सब रुक जाएगा। Backtest में इसे सिर्फ गिना गया, trade के नियम की तरह नहीं चलाया।

**Verifier: पाँचों जाँचें PASS।**
- नियम बंद करने पर F2 हूबहू दोबारा बना ($0.01 तक)।
- सभी 227 stops raw 1h perp files से सीधे loops द्वारा दोबारा गिने: entry price, पहले stop न छूना, fill, funding और P&L।
- 300 rebalance exits जाँचे: कोई stop छूटा नहीं।
- सभी 227 बार cooldown का पालन हुआ।
- MaxDD, Calmar, 2022 का return और K1 सीधे loops से दोबारा गिने।

**Lock के बाद बदलाव (दर्ज, `CODE_CHANGES_AFTER_LOCK.md`):**
1. **Run से पहले:** gap-liquidation के लिए F2 वाला margin नियम ही लिया गया। Protocol के शब्दों से फर्क 0.5% से कम है।
2. **Verifier की 2 गलतियाँ ठीक कीं:**
   - एक crash।
   - Cooldown की जाँच उस ADA trade को भी गिन रही थी, जो उसी दिन खुला और उसी दिन stop हुआ।
   - ADA की 2 मार्च 2025 की +74% छलांग दो स्रोतों से पक्की है: perp data, और spot data (0.659 → high 1.149)।
   - Engine, नतीजे और दावे नहीं बदले।

| $10k, 2021–26 (तीनों sleeves का औसत) | सिर्फ long | F2 long-short (बिना नियम) | **F7 long-short + नियम (RS)** |
|---|---|---|---|
| अंत में | $53,884 | $110,479 | **$88,401** |
| सबसे बड़ी गिरावट | 49.0% | 30.3% | **21.4%** |
| Calmar | 0.695 | 1.712 | **2.159** |
| 2022 (मंदी) | −41.6% | +45.4% | **+36.5%** |
| Liquidations | — | 69 | **0** |
| K1 (35% गिरावट) कितनी बार | 1 बार (sleeves में 1–3) | H1 में 1 | **0** |

**Gates (सब PASS):**
- G1: liquidations 0 (सीमा ≤ 7)।
- G2: गिरावट 21.4%, जबकि सीमा ≤ 30.33%।
- G3: नतीजा long-only से ऊपर।
- G4: 2022 में फायदा।
- G5: 0.20% खर्च पर भी $68,730, जो long-only से ऊपर है।
- G6: नकली दिमाग + नियम = $2,005, यानी डूबा।

**ईमानदार बातें:**
1. **कीमत चुकाई:** कमाई $110k से घटकर $88k (−20%)। बदले में गिरावट 30% से 21% हुई, और liquidation शून्य हुए।
2. **Sleeves का हाल:**

   | Sleeve | F2 (बिना नियम) | RS (नियम के साथ) |
   |---|---|---|
   | H1 | $133k | $72k |
   | D1 | $122k | $104k |
   | H4 | $76k | $89k |

   यानी हर sleeve पर असर अलग है।
3. **सिर्फ report के लिए variants:**
   - stop 30%: $100k, गिरावट 23.2%;
   - stop 75%: $70k;
   - नए listed coins (30 दिन से कम) पर short नहीं: $75k, गिरावट 20.2%।

   Stop 30% बेहतर दिखा, पर **उसे नहीं चुना**, क्योंकि नतीजा देखकर चुनना धोखा होता। नियम वही रहेगा जो lock हुआ था।
4. **PRE 2018–19 (नकली short, सिर्फ report):** RS $10,504, जबकि long-only $6,546। सबसे बड़ी गिरावट 19.1%।
5. **खर्च:**
   - Short हिस्से ने ~$8.9k funding चुकाई।
   - Stop पर 1% slippage माना गया है। असली squeeze में यह ज़्यादा हो सकती है, यह testnet और forward में जाँचना होगा।
6. **DSR (N = 83):** 0.879, अब भी 0.95 से नीचे। **असली जज सिर्फ forward (F4) है।**

**फैसला (protocol के हिसाब से):** PASS → **RS नियम F4 paper log और F6 testnet code के risk नियम बनेंगे।**

---

## क्रम 6, F4: long-short का paper forward log: **बना, test PASS, रोज़ का task चालू** (कोई order नहीं)
**Protocol:** `logs/forward_ls_f4/F4_PROTOCOL_PREREGISTERED.md`
- SHA lock: ff1cfb8a…, 15 अक्टूबर 15:25 UTC पर।
- यह PAPER_START (15 अक्टूबर) के पहले फैसले से पहले lock हुआ। वह फैसला 16 अक्टूबर 00:00 UTC पर होता है।

**Code:** `src/execution/forward_ls_f4.py`। Verifier: `src/audits/verify_f4_forward.py`।

**कैसे काम करता है:**
- 16B की prediction files सिर्फ पढ़ता है, यानी spot paper वाले वही दिमाग और वही scores।
- हर file का hash 16B के ledger से मिलाता है।
- Futures की कीमत और funding Binance के **public API** से लेता है: कोई key नहीं, कोई account नहीं, कोई order नहीं।
- तीन lines बनाता है:
  - **LS_RS** (मुख्य, F7 नियमों के साथ);
  - LS_F2 (बिना नियम);
  - LO (जाँच के लिए)।
- **रोज़ की जाँच C1:** LO line हर दिन 16B के paper से $0.01 तक मिलनी चाहिए। न मिले तो उस दिन के LS आँकड़े "भरोसे लायक नहीं" लिखे जाएँगे।
- Hash-chained ledger।
- पहले से रखे data को 48 घंटे दोबारा download करके मिलाता है। कोई बदलाव मिले तो चुपचाप नहीं बदलता, notes में लिखता है।

**Technical test (सितंबर 2026, research predictions के साथ): तीनों PASS।**

| जाँच | नतीजा |
|---|---|
| T1: दो स्रोत | API से लिया data बनाम archive (data.binance.vision): **24,864 hours की कीमतें और 4,097 funding events हूबहू एक जैसे, 0 फर्क** |
| T2 | दोनों स्रोतों से बनी paper lines बराबर |
| T3 | LO line, research simulators से हूबहू मिली |

**ईमानदार बात:** इसी test महीने (सितंबर 2026) में LS_RS $9,041 पर रहा, जबकि LO $10,813 पर। यानी उस महीने long-short पीछे रहा। एक महीना कुछ साबित नहीं करता, पर यह दर्ज है।

**Schedule:**
- Windows task `CryptoBot_F4_LSPaper`, रोज़ 08:30 और 09:00 IST पर, 16B के बाद।
- Wake-to-run चालू। पहला run 16 अक्टूबर 08:30 IST।

**Day-90 का फैसला (as-of 12 जनवरी 2027), पहले से lock:**
- D1: 90 में से ≥ 85 दिन समय पर दर्ज हों, chain सही रहे, और C1 हर दिन PASS हो।
- D2: LS_RS की सबसे बड़ी गिरावट ≤ 30%।
- D3: LS_RS का 90 दिन का return, F7 backtest के rolling 90-दिन returns के 5वें percentile से ऊपर हो।

तीनों हों, तभी छोटा real-money pilot (आपका फैसला)। 90 दिन edge साबित नहीं कर सकते, यह पहले से लिखा है।

---

## क्रम 7, F6: futures TESTNET executor: **code तैयार, पर चलाने के लिए आपकी testnet keys चाहिए**
**Protocol:** `logs/futures_testnet_f6/F6_PROTOCOL_PREREGISTERED.md` (SHA lock: 03ff573c…)

**Code:** `src/execution/futures_testnet_f6.py`। Verifier: `src/audits/verify_f6_testnet.py`।

**Ground-level जाँच से जो पक्का हुआ:**
1. **Futures के बिना-पैसे वाले environments:**
   - `https://testnet.binancefuture.com` (testnet)
   - `https://demo-fapi.binance.com` (demo)

   तीन स्रोतों से पक्का: Binance का official SDK (`@binance/common` के constants), ccxt 4.5.85, और दोनों का live ping (200)। **Code में mainnet (असली पैसे) का कोई रास्ता नहीं है।** कोई और host दिया गया तो code मना कर देगा।
2. **Stop orders का API बदल चुका है।** 9 दिसंबर 2025 से futures के STOP_MARKET orders `POST /fapi/v1/algoOrder` (algoType=CONDITIONAL) पर जाते हैं। पुराने `/fapi/v1/order` पर error -4120 आता है।
   - **स्रोत:** Binance changelog, official SDK का code, और docs के जवाब का उदाहरण (fields: `orderType`, `triggerPrice`, `algoStatus`)।
   - पुराने तरीके से लिखा code चुपचाप stop के बिना चलता।
3. **Testnet:** 570 perpetuals चालू हैं। हर order का न्यूनतम आकार 50 USDT है (BTCUSDT के filters से)।

**Executor क्या करता है:**
- F4 के LS_RS वाले रोज़ के फैसले पढ़ता है। उस file का hash F4 ledger से मिलना चाहिए।
- Short: MARKET SELL। तुरंत stop लगता है: fill × 1.50 पर STOP_MARKET reduce-only, algo endpoint से।
- Short बंद करना: MARKET BUY reduce-only।
- हर symbol पर isolated margin और 1x leverage।
- **सीमाएँ:** एक run में 40 orders, एक order sleeve की पूँजी का अधिकतम 25%, और कुल 15 shorts।
- **Kill switch K1:** account चोटी से 35% नीचे जाए तो सब बंद, सारे stops रद्द, और `HALT` file बनती है। उसके बाद आपकी जाँच तक कुछ नहीं चलेगा। `--drill-kill` से इसका अभ्यास भी हो सकता है।
- Account hedge mode में हो, तो code रुक जाएगा। Settings code नहीं बदलेगा।
- **`plan` mode:** बिना key के बताता है कि कौन से orders भेजता, पर भेजता कुछ नहीं।

**Operations जाँचें (O1–O4), लगातार ≥ 2 runs पर:**
- O1: हर order का जवाब, या छोड़ने का कारण।
- O2: हर short पर ठीक एक सही stop।
- O3: Exchange का हिसाब = हमारा हिसाब।
- O4: Kill drill के बाद कोई position नहीं, और कोई open stop नहीं।

**यह कमाई का test नहीं है।** सिर्फ यह देखता है कि system मशीन की तरह सही चलता है या नहीं।

**अभी क्या नहीं हुआ (ईमानदारी से):**
- **Testnet पर अभी एक भी order नहीं गया।** कारण:
  - (a) F4 की पहली ledger line 16 अक्टूबर 08:30 IST पर बनेगी;
  - (b) testnet keys आपको बनानी होंगी। मैं keys नहीं डालता।
- इसलिए O1–O4 अभी बाकी हैं।

**आपके काम:**
1. https://testnet.binancefuture.com (या Binance demo trading) पर account बनाएँ और API key बनाएँ।
2. Keys अपने PC के environment variables में खुद डालें: `BINANCE_FUT_TESTNET_KEY` और `BINANCE_FUT_TESTNET_SECRET`।
3. Account को one-way position mode में रखें।
