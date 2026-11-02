# आज की पूरी research एक जगह: क्या करना है, क्या नहीं, किस क्रम में, और AI कैसे लगातार काम करेगा (17 अक्टूबर 2026)

**यह file क्या है:** 17 अक्टूबर 2026 की सुबह से अब तक की हर research, measurement और फ़ैसले का integration।
- इसमें **कोई नया आँकड़ा नहीं है।** हर संख्या नीचे दी गई source files में से किसी एक से ली गई है, और उसका हवाला साथ दिया है।
- पुरानी files बदली नहीं गईं। जहाँ बाद की जाँच ने कोई पुरानी बात सुधारी, वह भाग 9 (errata) में दर्ज है, और यहाँ हर जगह **सुधरा हुआ** मान इस्तेमाल हुआ है।
- **GitHub:** कुछ नहीं। Cloud पर चल रहा 1D system और laptop की production files अछूती हैं।
- मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## भाग 0. Source files: कुछ भी खोने न पाए
| # | File | उसमें क्या है | SHA256 (शुरुआत) | Size |
|---|---|---|---|---|
| S1 | `PLAN_NEXT_TARGET_R2_17_OCT_2026.md` | अगला timeframe कौन (4H पहले); timeframes की तुलना | `14714836…` | 8.3 KB |
| S2 | `RESEARCH_4H_TRADING_LONG_SHORT_17_OCT_2026.md` | 4H long-short पर बाहरी research; experiments X0–X10 | `0476ce8f…` | 78 KB |
| S3 | `FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md` | Binance fee (BNB), live spread, break-even, 4H candle की चाल | `0531b065…` | 8.2 KB |
| S4 | `RESEARCH_AI_ARCHITECTURE_MULTI_TF_17_OCT_2026.md` | भाग 1 (आपके design की जाँच), भाग 2 (लगातार scan-learn-decide), भाग 3 (सत्यापन, errata, अंतिम design), भाग 4 (सीढ़ी), भाग 5 (test entry) | `b7b18af2…` | 291 KB |
| S5 | `REPORT_LADDER_PATTERNS_SESSIONS_17_OCT_2026.md` | सीढ़ी, line patterns, sessions (pre-registered + verifier PASS); test entry वाला जोड़ भी इसमें | `a6244819…` | 38 KB |
| S6 | `REPORT_PROBE_SCALEIN_LADDER_17_OCT_2026.md` | Test entry और scale-in का simulation, 1,44,967 trades (pre-registered + verifier PASS) | `68cda951…` | 15 KB |
| S7 | `logs/research_r2/fee_spread_check/` | Live order book के raw snapshots (SHA सहित), demo `commissionRate` | — | — |
| S8 | `logs/research_ladder_sessions/` | Protocol `e7ae067d…`, tables A1–A7, B1–B4, P1–P2, claims, verify_log | — | — |
| S9 | `logs/research_probe_scalein/` | Protocol `90814d65…`, S1, S2, trades.parquet, claims, verify_log | — | — |
| S10 | `research_notes/` (6 folders: 4H, architecture, continuous brain, timeframe sync, ladder, test entry) | बाहरी research के notes, links के साथ | — | — |
| S11 | `deploy/crontab.txt`, `logs/forward_ls_f4/CODE_CHANGES_AFTER_LOCK.md` | सुबह के cloud सुधार (F4 07:45, M10 11:15) | `1525e074…`, `0831087b…` | — |
| S12 | Backup `E:\cryptobot_snapshots\2026-10-17_1D_frozen\` | पूरे 1D system की frozen copy: 105,181 files, 2.88 GB; tar की गिनती manifest से मिलाई गई | tar `64e8144f…` | — |

**आज का code (सिर्फ़ research, production नहीं):**
- `src/research_r2/fee_spread_check.py`
- `src/research/ladder_sessions.py` (`6962deb9…`) और `ladder_sessions_postlock.py` (`ac7dd5bc…`), verifier `src/audits/verify_ladder_sessions.py` (`b17789ce…`)
- `src/research/probe_scalein.py` (`52f49641…`), verifier `src/audits/verify_probe_scalein.py` (`263bea25…`)

---

## भाग 1. आज क्या-क्या हुआ (क्रम से)
1. **सुबह: cloud VM का पहला दिन (S11)।**
   - सभी 15 jobs exit 0 के साथ चले और हर verifier PASS हुआ।
   - दो कमियाँ मिलीं और ठीक हुईं:
     - F4 का schedule उसकी deadline के बराबर था, जिससे वह 44 सेकंड late हुआ। अब वह **07:45 IST** पर चलता है। 90 दिन में 5 late दिनों की छूट है, जिनमें से 2 इस्तेमाल हो चुके।
     - M10 F6 से पहले चल रहा था। अब वह **11:15** पर चलता है।
   - Paper का पहला दिन: LS_RS $10,032.52 (+0.33%), E11 shadow $10,039.19, LO $9,950.45।
2. **Backup (S12):** 1D system की frozen copy बनी और verify हुई।
3. **अगला target (S1):** 4H पहले, 1h बाद में, weekly और monthly सिर्फ़ "मौसम" बताने वाली परत।
4. **साफ़ किया गया** कि हमारे H4 और H1 दिमाग असली 4H या 1h trading नहीं करते। वे दिन में एक बार फ़ैसला लेते हैं और उनका hold ~5 दिन है। इनकी इजाज़त 14 अक्टूबर को मिली थी (रिकॉर्ड से जाँचा)।
5. **4H research (S2):** costs के बाद 4H पर कोई signal साबित नहीं, trend सबसे ज़्यादा समर्थित; experiments X0–X10।
6. **आपकी आपत्ति** ("कच्ची research, खर्च नापो") पर **fee और spread का असली माप हुआ (S3)।** नतीजा: पुरानी research ने खर्च 3–6 गुना ज़्यादा माना था।
7. **आपका AI design (5 brains, 8 timeframes):** जाँचा गया (S4 भाग 1)।
8. **लगातार scan → learn → decide brain (S4 भाग 2)।** आपने तय किया: stop अपने-आप, 10,000 USDT, 4H पहले।
9. **पूरे document का स्वतंत्र सत्यापन (S4 भाग 3):** 4 बड़ी गलतियाँ पकड़ी गईं, timeframe-वार अंतिम design बना।
10. **सीढ़ी, patterns और sessions (S5):** pre-registered study, verifier PASS।
11. **Test entry और scale-in (S6):** pre-registered simulation, verifier PASS।

---

## भाग 2. आपके तय फ़ैसले (स्थायी)
| # | फ़ैसला | स्रोत |
|---|---|---|
| U1 | **Stop loss अपने-आप, market देखकर।** F7 का फ़ैसला कायम: 1D shorts पर stop entry ×1.5, 30 दिन cooldown। Take profit और trailing stop भी रहेंगे | आपका संदेश, S4 भाग 2–3 |
| U2 | **Capital 10,000 USDT:** 8,000 trading में, 2,000 risk reserve (80/20) | USER_DECISIONS_16_OCT, S4 |
| U3 | **Fee BNB से (default)।** Spot पर 25% छूट; futures पर 10% छूट, बशर्ते BNB futures wallet में हो | आपका संदेश, S3 |
| U4 | **आख़िर में सारे timeframes (5m से 1M तक) एक साथ sync में, पर शुरुआत 4H से** | आपका संदेश |
| U5 | **Long और short दोनों, spot और futures दोनों** | आपका संदेश |
| U6 | **अभी सिर्फ़ research, coding नहीं** | आपका संदेश |
| U7 | **Cloud का 1D system और laptop का system नहीं छूना है** | आपका संदेश |
| U8 | **Tax और कानूनी बातें बाद में** | 16 अक्टूबर |

---

## भाग 3. सबसे ज़रूरी verified तथ्य (सुधरे हुए मान)
### 3.1 खर्च (S3, S4 भाग 3)
| Round trip ($1,000 trade, fee + median spread) | BNB के साथ | BNB के बिना |
|---|---|---|
| Futures taker (demo API 0.04%) | **0.085%** | 0.092% |
| Futures taker (FAQ 0.05%, अभी खुला सवाल) | ~0.10% | ~0.11% |
| Futures maker, दोनों तरफ़ | ~0.04% | ~0.04% |
| Spot market | **0.17%** | ~0.22% |

- **Stop पर slippage:** F7 protocol +1% मानता है। इसलिए risk = stop दूरी + 1% + खर्च।
  - उदाहरण: 40 USDT risk और 3% stop पर notional ≈ **979 USDT**, 1,333 नहीं।
- **सबसे छोटी order** (आज live API से): spot 5 USDT (DOGE 1); futures 5 USDT (XRP, SOL, DOGE), 20 USDT (ETH, LINK), 50 USDT (BTC, साथ में कम से कम 0.001 BTC)।
- पुरानी research में खर्च **0.5% round trip** माना गया था, जो 3–6 गुना ज़्यादा था। 1h R4 इसी अनुमान पर "डूबा" था, इसलिए उसे नए खर्च पर दोबारा परखना होगा, एक नए trial की तरह।

### 3.2 हर timeframe का व्यवहार (हमारा data, 8 coins, 2020–2026; S4 भाग 3)
| TF | Median candle चाल | खर्च, चाल का % | व्यवहार (VR) | भूमिका |
|---|---|---|---|---|
| 5m | 0.12% | **68%** | हल्का पलटाव (0.947) | सिर्फ़ execution |
| 15m | 0.22% | 38% | हल्का पलटाव (0.950) | सिर्फ़ execution |
| 1h | 0.43% | 20% | हल्का पलटाव (0.940) | दूसरा alpha (बाद में) |
| **4h** | 0.86% | **10%** | लगभग random (0.995) | **पहला alpha** |
| 1D | 2.33% | 3.7% | हल्का पलटाव (0.942) | मौजूदा 1D system + context |
| 1W | 6.69% | 1.3% | trend (1.18), पर सिर्फ़ 353 bars | context; बाद में trend sleeve |
| 1M | 16.7% | 0.5% | trend (1.24), पर सिर्फ़ 81 bars | सिर्फ़ context |

### 3.3 Swing और सीढ़ी (S5, Swing Anatomy Phase 1)
- **Swing का आकार:** आम swing ≈ 5 ATR, हर timeframe पर। Confirm होने तक ~57% पूरा हो चुका होता है, ~2 ATR (median) बचता है। बची चाल का conditional mean **3.0–3.8 ATR** है, यानी कमाई tail में है।
- **बड़ा timeframe साथ हो** तो छोटे swing की चाल +0.5 से +0.8 ATR ज़्यादा होती है। 1W का असर साफ़ नहीं, 1M का उल्टा।
- **Market किस हालत में रहता है:** ऊपर की सीढ़ी में 31–36% समय, नीचे की सीढ़ी में 29–31%, बाकी ~35% सिकुड़न या फैलाव।
- **सीढ़ियाँ छोटी होती हैं:** ~50% सिर्फ़ 1 कदम की, 5 या ज़्यादा कदम वाली सिर्फ़ 1–3%। नीचे की सीढ़ियाँ और भी छोटी।
- **Pullback** पिछली चाल का 45–77% (median ~0.61)। **Fibonacci साबित नहीं** (lock के बाद की density जाँच में)।
- **Double top या bottom** के बाद उल्टी दिशा का अगला कदम 3–9 percentage points ज़्यादा बार आता है। यह सबसे साफ़ pattern है, पर सिर्फ़ विवरण है।
- **सीढ़ी का अगला कदम:** 4h पर हल्का फ़ायदा (~52% बनाम 48.7%); 5m से 1h पर कोई फ़ायदा नहीं।
- **Sessions:**
  - दिशा किसी session में साबित नहीं। ETF आने के बाद US session की दिशा उलट गई।
  - US session (18:30–02:30 IST) सबसे सक्रिय है: प्रति घंटे सबसे ज़्यादा हलचल, 1h के 39–43% swing यहीं पलटते हैं, और random walk से उम्मीद से ज़्यादा दिन के high और low यहीं बनते हैं।

### 3.4 Test entry और scale-in (S6, 1,44,967 सीढ़ी trades, BNB fees)
| TF | पूरी entry (R/trade) | Test/किस्तों में | सबसे बुरे 5% trades (V0 → V2) |
|---|---|---|---|
| 5m | −0.12 | −0.07 से −0.08 | −1.05 → −0.68 |
| 15m | −0.05 | −0.02 से −0.04 | −0.98 → −0.62 |
| 1h | +0.03 | +0.03 | −0.93 → −0.58 |
| **4h long** | **+0.106** | +0.076 से +0.083 | −0.91 → **−0.57** |
| 4h short | +0.054 | +0.037 से +0.045 | −0.96 → −0.59 |
| 1D long (153 trades) | +0.23 | +0.24 से +0.28 | −0.92 → −0.43 |
| 1D short | +0.105 | +0.04 से +0.05 | −0.89 → −0.58 |

- **Pre-registered फ़ैसला: scale-in की सिफ़ारिश साबित नहीं।** Test entry एक **बीमा** है: कमाई ~20–30% कम, बड़ा नुकसान 13–38% कम।
- **5m और 15m:** हर तरीका घाटे में है। "हर 5 मिनट थोड़ा कमाना" खर्च में डूब जाता है (5m पर कुल लगभग −12,000 R)।
- **Paper test (V3)** ने कमज़ोर साल (2025-10 से 2026-09) में 1D long पर −0.36 R को लगभग 0 किया। नमूना छोटा है।

### 3.5 AI पर पिछले verified सबक (सुधरे हुए)
- **Ranking skill असली है:** D1 0.559, 4H R6 0.568, 1h R24 0.565। पर ये तीनों 0.89–0.95 correlated हैं, यानी एक ही दाँव।
- **Exit का AI (Step 26):** AUC 0.672 पर skill थी, **पर पैसे में नहीं बदली** (Calmar 0.623 बनाम 0.920)। इसलिए exit नियमों से होगा, और AI exit एक अलग trial होगा जिसका gate Calmar/DD होगा, AUC नहीं।
- **"Market से कब बाहर रहें" वाला दिमाग असफल रहा** (AUC 0.523)। Swing पर entry लेने वाला AI भी असफल रहा (0.530–0.539)।
- **15m/5m features** से AUC में सिर्फ़ +0.0008 जुड़ा।
- **गिरावट रोकने के** साबित तरीके सिर्फ़ position size और long-short का ढाँचा हैं।

### 3.6 बाहरी साहित्य का सार (S2, S4, S10; ज़्यादातर abstract या summary स्तर पर)
- **Trend/breakout** सबसे समर्थित style है। Mean reversion, pairs trading और weekly ranking खर्च के बाद ~0 या घाटे में। Carry शर्त-आधारित है और घटता जा रहा है।
- **Candlestick patterns:** out-of-sample नकारात्मक। Chart patterns में थोड़ी जानकारी है, पर अकेले trade करने पर फ़ायदा कमज़ोर।
- **Strategies को मिलाना** (equal-weight) उन्हें चुनने (regime switching) से ज़्यादा मज़बूत है। Persistent, धीरे बदलने वाला regime model ठीक है; तेज़, बार-बार switching कमज़ोर।
- **लगातार (online) सीखने का** खर्च के बाद बेहतर होने का कोई सबूत नहीं। तय समय पर retraining, कई windows का औसत, और frozen model पर drift alarm बेहतर तरीका है।
- **LLM से trade के फ़ैसले:** कई साल के ईमानदार test में buy-and-hold को नहीं हराया। ऊपर से पुराने prices याद रहने (look-ahead) का खतरा है।
- **Day trading:** ~97% घाटे में (Taiwan, Brazil)। 0.2% के छोटे target पर taker के साथ 75% जीत चाहिए।
- **Stops:** random walk में stop expected return घटाता है, और momentum हो तभी मदद करता है (Kaminski & Lo)। Crypto पर अध्ययन मिले-जुले हैं।

---

## भाग 4. क्या करना है (DO), सबूत के साथ
| # | करना है | क्यों (सबूत) |
|---|---|---|
| D1 | **4H पहला AI alpha sleeve** (long + short, futures; spot long तब जब funding महँगी हो) | खर्च चाल का 10%; हज़ारों bars; 4h सीढ़ी पर V0 +0.106 R (long), +0.054 (short) |
| D2 | **AI का सवाल 1D से अलग हो:** confirm हुआ swing या सीढ़ी का कदम, उसके साथ अगले बड़े TF की हालत और volume। AI तय करे कि trade लेना है या नहीं, किस दिशा में, और calibrated probability दे (meta-label) | 1D/H4/H1 0.89–0.95 correlated; volume spike सबसे लगातार factor; double top/bottom और सीढ़ी की हालत छोटे पर असली inputs |
| D3 | **Exit नियमों से:** तीन परतों में stop (exchange पर catastrophe stop MARK_PRICE पर → swing के पार ATR buffer वाला initial stop → trailing/time stop); trailing को प्राथमिकता, fixed 2 ATR TP सिर्फ़ तुलना के लिए | Exit AI पैसे में fail; कमाई tail में (mean 3.0–3.8 ATR) |
| D4 | **Size तय करने वाला function:** risk = base × f(probability) × context × HTF झुकाव; ¼–½ Kelly की सीमा; risk में slippage और खर्च शामिल | S4 भाग 3; F7 का 1% slippage |
| D5 | **Test entry या किस्तों में entry (V2/V3) "बीमा" विकल्प के रूप में।** AI का भरोसा कम हो या market जोखिम भरा हो, तो इसका इस्तेमाल हो; pre-registered trial से तय होगा | S6: बुरे trades का नुकसान 38% तक कम, कमाई ~20–30% कम; V3 ने कमज़ोर साल में बचाया |
| D6 | **5m/15m सिर्फ़ entry के समय के लिए** (post-only, ≤1 घंटे की window, फिर taker) | खर्च चाल का 38–68%; S6 में घाटा |
| D7 | **बड़ा TF size तय करे, veto नहीं।** हर TF सिर्फ़ अपनी आख़िरी **बंद** candle देखे (`available_at`)। छोटा TF बड़े के ख़िलाफ़ सिर्फ़ exposure घटा सके | Top-down से mean बढ़ता है, पर hit rate नहीं; look-ahead से बचाव |
| D8 | **Knowledge store** हर जानकारी के "कब पता चली" समय के साथ (swing और सीढ़ी के labels confirm होने के समय पर); hash-chained decision ledger; trial registry | Leakage से बचाव; विधि की निरंतरता |
| D9 | **तय समय पर retraining** (4h/1h हर महीने, 1W तिमाही), कई windows का औसत, नया model पहले shadow में, फिर gate, फिर **manual** promotion | Online learning का कोई सबूत नहीं; Blind Spot preprint |
| D10 | **Monitor और kill switch:** drift को frozen model पर नापना, bar की उम्र, reconcile, असली खर्च। **अपने-आप सिर्फ़ risk घटे** | S4 भाग 2–3 |
| D11 | **अलग sub-account और one-way mode** (account-wide setting; live से पहले एक बार तय) | Binance docs; 1D system से टकराव न हो |
| D12 | **Execution:** stop `/fapi/v1/algoOrder` से, `workingType=MARK_PRICE`; पहले नया stop लगे फिर पुराना cancel हो; idempotent clientOrderId; reconcile | Binance changelog (verified) |
| D13 | **Benchmark:** equal-weight + vol targeting, नियम वाला trend baseline (X2), shuffled-label, random-entry और random-exit controls | S2, S4 |
| D14 | **Gates:** DSR ≥ 0.95, PBO < 0.30, 1.5× खर्च (बिना-BNB खर्च पर भी) net > 0, 1D से correlation ≤ 0.70 या combined Calmar बेहतर, **trial budget 20** | S4 भाग 3 |
| D15 | **साफ़ holdout = सिर्फ़ 17 अक्टूबर 2026 के बाद का forward data।** 2018–19 frozen, पर सिर्फ़ spot-direction के लिए | Errata #4 |
| D16 | **Short के लिए अलग नियम:** liquid coins तक सीमित; नए listed coins पर नहीं; profit जल्दी; short में scale-in नहीं | S5 (नीचे की सीढ़ियाँ छोटी), S6 (1D short V2 घाटा), S2 |
| D17 | **बाद में (gate के बाद):** 1h (pooled model में), learned context, weekly trend (पहले नियम), carry सिर्फ़ तब जब basis चौड़ा हो | S4 भाग 3, S2 |

## भाग 5. क्या नहीं करना (DON'T), कारण के साथ
| # | नहीं करना | कारण |
|---|---|---|
| N1 | **5m/15m पर अलग से trading या scalping ("हर 5 मिनट एक रुपया")** | खर्च > कमाई; S6 में −12,000 R; day traders में ~97% घाटे में |
| N2 | **Fibonacci, Elliott wave या candlestick के नियम** | हमारे data में और बाहरी research में साबित नहीं |
| N3 | **Session के हिसाब से दिशा के नियम** | किसी session में दिशा साबित नहीं; ETF के बाद US उलटा |
| N4 | **LLM से trade के फ़ैसले** | OOS सबूत नहीं; look-ahead का खतरा |
| N5 | **Live model का अपने-आप बदलना (online learning या live RL)** | सबूत नहीं; drift छिप जाता है |
| N6 | **Master brain का हर regime में strategy बदलना (hard switching)** | मिलाना ज़्यादा मज़बूत है; switching का सबूत कमज़ोर |
| N7 | **कई एक जैसे (correlated) दिमाग**; अभी 30m/8h/12h के sleeves | 0.89–0.95 correlation = एक ही दाँव; trials बढ़ते हैं |
| N8 | **1W/1M को gate या veto बनाना**; monthly का अलग system | 1W का असर साफ़ नहीं, 1M का उल्टा; सिर्फ़ 81 monthly bars |
| N9 | **सिर्फ़ fixed 2 ATR target** (tail कट जाती है) | कमाई tail में है |
| N10 | **Short में scale-in; 5m से 1h पर scale-in को कमाई का तरीका मानना** | S6 |
| N11 | **2025-10 से 2026-09 को holdout मानना** | यह अवधि पहले देखी जा चुकी है |
| N12 | **AUC को अकेला gate मानना** | Step 26: AUC 0.672, फिर भी पैसे में fail |
| N13 | **Pairs trading, mean reversion के sleeves, या हमेशा चालू carry** | खर्च के बाद ~0 या घाटा; carry घटता जा रहा है |
| N14 | **Cloud का 1D system, उसका account या position mode छूना** | U7 |
| N15 | **अधूरी (partial) बड़े TF की candle या `.asof` इस्तेमाल करना** | Look-ahead; project का नियम `df["asof"]` लिखने का है |
| N16 | **हर बार हर signal पर पूरी size, बिना risk सीमा के** | F7/K1 के सबक; correlation = 1 मानकर caps |

---

## भाग 6. AI कैसे काम करेगा: लगातार scan, analysis, फ़ैसला, निगरानी और सीखना
### 6.1 दिमाग और परतें (अंतिम ढाँचा, S4 भाग 3)
| # | हिस्सा | प्रकार | काम | कब से |
|---|---|---|---|---|
| **B1** | **Context दिमाग** | पहले नियम, बाद में AI (अलग trial) | 1D/1W/1M से market का मौसम → सिर्फ़ risk multiplier (0.5–1.0); कभी दिशा नहीं, कभी veto नहीं | शुरुआत से (नियम के रूप में) |
| **B2-fast** | **4h alpha / meta-label दिमाग** | AI (gradient boosting, coins पर pooled) | सीढ़ी या swing का signal → लेना है या नहीं, दिशा, probability | Phase A (पहला AI) |
| B2-slow | 1D system | मौजूदा, अलग | जैसा चल रहा है | अछूता |
| B2-weekly | Weekly trend | पहले नियम | बाद में | Phase E |
| **B3** | **Size function** | Calibrated, सीखा हुआ दिमाग नहीं | probability × context × HTF झुकाव → size; पूरी entry या test entry (D5) | B2 के साथ |
| **L4** | **Risk और stop engine** | नियम, veto के साथ | risk = stop + 1% + खर्च; caps; तीन-परत stops; DD पर risk घटाना; cooldown | हमेशा |
| **L5** | **Execution परत** | नियम | 5m/15m पर entry का समय; post-only, फिर taker | हमेशा |
| **L6** | **Monitor / kill switch** | Infrastructure | drift, data की उम्र, reconcile, खर्च; alarm; सिर्फ़ size घटाना या रोकना | हमेशा |

**अभी live में सिर्फ़ एक AI दिमाग (B2-fast) होगा।** अंत में अधिकतम चार सीखने वाले हिस्से होंगे, साथ में तीन नियम वाली परतें।

### 6.2 लगातार चलने वाला चक्र: हर 5 मिनट पर क्या होता है
System एक हमेशा चलने वाली service होगी (VM पर systemd के नीचे, अलग sub-account)। Binance के live data stream पर हर बंद candle एक "event" है।

```
हर 5 मिनट (5m candle बंद होने पर), और जिस बड़े TF की candle भी उसी पल बंद हुई हो उसके लिए, क्रम 1M → 1W → 1D → 4h → 1h → 15m → 5m:

 ① SCAN / DATA      Binance stream (x=true) → candle लिखो → छूटी candle REST से भरो → data की उम्र और घड़ी जाँचो
 ② KNOWLEDGE        हर TF: ATR, सीढ़ी की हालत (UP/DOWN/सिकुड़न/फैलाव), swing points (confirm-time पर), double top/bottom,
                    volume spike, अगले बड़े TF की बंद हालत, funding/basis, session → store में available_at के साथ
 ③ MONITOR (L6)     खुली positions का reconcile (exchange बनाम हमारी किताब), stop मौजूद है? drift? data बासी?
                    गड़बड़ हो तो → size घटाओ या रोको (कभी बढ़ाओ नहीं) + आपको alert
 ④ खुले trades      हर 5m: trailing stop आगे खिसकाओ (पहले नया, फिर पुराना cancel), time stop गिनो,
                    test entry (V2/V3) वाले trade में "भाव साथ दे तो size बढ़ाओ" का trigger जाँचो
 ⑤ DECIDE           सिर्फ़ जब 4h candle बंद हो: B1 का multiplier (1D close से) → B2-fast: signal + probability
                    → B3: size और तरीका (पूरी entry या test entry) → Coordinator (सारे sleeves का net) → L4 risk engine (veto)
 ⑥ EXECUTE (L5)     अगले ≤1 घंटे में 5m/15m पर post-only entry; न भरे तो taker; साथ में exchange पर catastrophe stop
 ⑦ RECORD           हर input, model version, फ़ैसला, fill, खर्च → hash-chained ledger
 ⑧ LEARN (तय समय)   trade बंद → label → हर महीने retrain (कई windows का औसत) → नया model shadow में
                    → gate (verifier) → आपकी मंज़ूरी पर promotion
```

- **"लगातार" का मतलब:**
  - Scan, record, monitor और stops हर 5 मिनट पर **अपने-आप** चलते हैं।
  - **फ़ैसला** अपने timeframe की candle बंद होने पर होता है: 4H पर दिन में 6 बार, बाद में 1h पर 24 बार।
  - **सीखना** तय समय पर होता है।
- **अपने-आप क्या हो सकता है:** risk घटाना, stop खिसकाना, trade बंद करना, रुक जाना।
- **बिना मंज़ूरी क्या नहीं:** size की सीमा बढ़ाना, model बदलना, नया sleeve शुरू करना। इनके लिए gate, verifier और आपकी "हाँ" चाहिए।
- **एक साथ बंद होने वाली candles:** जैसे 00:00 UTC पर 4h, 1D और कभी 1W/1M एक साथ बंद होते हैं। तब पहले बड़े TF की candle store में जाएगी, फिर छोटे TF का फ़ैसला चलेगा। इससे backtest और live हूबहू एक जैसे रहेंगे।

### 6.3 टकराव के नियम (पहले से तय)
- **एक coin पर एक sleeve:** कोई टकराव नहीं।
- **दो sleeves एक ही दिशा में:** size जुड़ता है, per-coin cap तक।
- **छोटा TF बड़े के ख़िलाफ़:** सिर्फ़ net घटा सकता है, नई उल्टी position नहीं खोल सकता।
- **Context (B1) risk-off हो:** सिर्फ़ नए trades का risk घटता है।
- **Monitor alarm:** size घटाना या रोकना, सिर्फ़ reduce-only orders से।

### 6.4 हर timeframe पर scan और learning की ताल
| TF | Scan | फ़ैसला | Retrain | भूमिका |
|---|---|---|---|---|
| 5m | 288/दिन | — | (सिर्फ़ execution के नियमों की मासिक समीक्षा) | Execution, stops की निगरानी |
| 15m | 96/दिन | — | वही | Execution |
| 1h | 24/दिन | Phase B से | मासिक | दूसरा alpha |
| **4h** | 6/दिन | **हर 4h close** | **मासिक** (purged walk-forward) | **पहला alpha** |
| 1D | 1/दिन | मौजूदा system | उसकी अपनी cadence (अछूती) | Context (B1) + 1D system |
| 1W | 1/हफ़्ता | बाद में (नियम) | तिमाही | Context, बाद में trend |
| 1M | 1/महीना | — | — | सिर्फ़ context |

---

## भाग 7. किस क्रम में करना है (priority)
हर चरण का gate पास किए बिना अगला चरण नहीं। ✋ = आपकी मंज़ूरी चाहिए। 💻 = coding चाहिए, जो आपकी "हाँ" के बाद ही होगी।

| क्रम | चरण | क्या | Gate |
|---|---|---|---|
| **0** | **अभी (रोज़)** | Cloud 1D system की रोज़ जाँच। 18 अक्टूबर: F6 का दूसरा run → drill-kill → O1–O5 और O4 → "operations ready" का फ़ैसला; F4 का 07:45 पर on time होना | Verifiers PASS |
| **1** | **Errata लागू करना** (research, कोई code नहीं) | पुरानी files पर "सुधार देखें" के नोट; यह master file ही आगे का संदर्भ | — |
| **2** ✋💻 | **Forward recorder** (अलग, छोटा; 1D VM नहीं छूना) | Live data को SHA chain के साथ आज से दर्ज करना, क्योंकि साफ़ holdout सिर्फ़ forward data है | Replay 100% मेल |
| **3** ✋ | **A0: 4H protocol lock** | सवाल, labels, data windows (dev 2021-01 से 2025-09; "seen" 2025-10 से 2026-09; holdout = forward), cost model (BNB और बिना BNB, 1×/1.5×/2×), risk formula, trial budget 20, सभी gates | SHA lock |
| **4** 💻 | **A1: बिना AI के माप** | X1 edge map: कौन-सा signal खर्च के दोगुने से ज़्यादा कमाता है। "+k ATR, −m ATR से पहले" की दर। Stop slippage। Ladder features की तैयारी | **अगर कोई signal ≥ 2× खर्च न दे, तो रुककर report** |
| 5 💻 | **A2: Knowledge store + ledger + trial registry** | `available_at` ordering, replay tests, leak canary | Replay 100%; leak canary पकड़ा जाए |
| 6 💻 | **A3: B2-fast (4h meta-label)** | सीढ़ी, swing, HTF, volume features; मासिक walk-forward; B1 नियम के रूप में | Shuffled control के 95th percentile से ऊपर; 2018–19 spot पर skill |
| 7 💻 | **A4: Stops, exits और size का grid** | Catastrophe-only / ATR / structural / trailing-only बनाम 2 ATR TP / time stop; **V0 बनाम V2/V3 (test entry)**; 5m के भीतर fills | Plateau; DD घटे; random-entry से बेहतर |
| 8 💻 | **A5: Backtest + independent verifier** | Equal-weight benchmark; असली funding; short filters (X7); spot/perp routing (X8) | DSR ≥ 0.95, PBO < 0.30, 1.5× खर्च पर net > 0, 1D से correlation ≤ 0.70 |
| 9 | A6 (वैकल्पिक) | AI exit trial (budget में गिना) | Calmar और DD, random exit से बेहतर |
| 10 💻 | **A7: Engine + chaos tests** (demo/testnet) | Event service, algoOrder, reconcile, kill switch | शून्य orphan या बिना stop वाली position |
| 11 | **A8: Forward shadow (साफ़ holdout)** | Lock के बाद का live data, कोई असली order नहीं | Backtest की अपेक्षित सीमा में; खर्च ≤ 1.25× model |
| 12 ✋ | **A9: असली पैसा** | सिर्फ़ आपका फ़ैसला; 8,000 का छोटा हिस्सा पहले; अलग sub-account | आपकी स्पष्ट "हाँ" |
| 13 | B → G | 1h (pooled) → learned context → 1D sleeve → weekly trend → 5m/15m execution optimizer → 30m/8h/12h features | हर एक के अपने gates |

**एक ईमानदार सीमा:** forward data से edge **साबित** करने में समय लगता है (Sharpe 1.0 के लिए ~2.7 साल)। इसलिए A8 का gate "backtest की सीमा में रहो, कोई bug या आपदा नहीं" है, profit साबित करना नहीं। असली पैसे का फ़ैसला कभी पूरी तरह निर्णायक सबूत पर नहीं होगा।

---

## भाग 8. अभी क्या नहीं पता
| सवाल | कैसे पता चलेगा |
|---|---|
| 4H meta-label AI खर्च के बाद edge देगा या नहीं (पिछले swing-entry AI fail हुए थे) | A3–A5, फिर A8 |
| Futures taker 0.04% है या 0.05% (असली account पर) | असली account का `commissionRate` |
| 4H पर असली stop slippage (1% मानने से risk ~33% बढ़ता है) | Demo/forward fills |
| Step 26 की exit skill पैसे में क्यों नहीं बदली | A6 |
| HTF को झुकाव दें, veto, या सिर्फ़ feature | Pre-registered तुलना |
| 1W का trend टिकाऊ है या नहीं; 1M का कोई उपयोग है या नहीं | बड़ा universe; शायद कभी नहीं |
| 1h और 4h आपस में कितने correlated होंगे | Phase B |
| Funding का असली असर (simulation में मानी हुई 0.01%/8h थी) | असली funding history |
| Binance sub-account के नियम, 1W/1M candle boundaries, stream की सीमाएँ | Docs + testnet |
| सीढ़ी और test entry के नतीजे सिर्फ़ 10 बड़े coins पर, बिना AI | A3–A5 में बड़ा universe |

---

## भाग 9. Errata: पुरानी बातें जो अब बदल गईं (यहाँ सुधरा मान ही इस्तेमाल हुआ है)
| पुरानी बात | कहाँ | सुधार |
|---|---|---|
| "Exit AI असफल, AUC 0.505–0.526" | S4 भाग 1–2 | Step 26 में AUC 0.672 था, पर पैसे में fail |
| "1h ≈ 0, खर्च से पहले" | S4 भाग 2 | 1h gross +0.33% ≈ taker का 3.9 गुना; median नकारात्मक |
| "5m/15m maker खर्च से भी कम" | S4 भाग 1 | सिर्फ़ 5m; 15m ≈ maker खर्च |
| Sealed holdout = 2025-10 से 2026-09 | S2, S4 भाग 1–2 | Forward data (17-10-2026 से) ही साफ़ holdout है |
| खर्च 0.25% प्रति fill (0.5% round trip) | Steps 13–27 | Futures ~0.085%, spot ~0.17% (BNB के साथ) |
| Trial budget 16–20 या 20–25 | S2, S4 भाग 1 | **20** |
| Risk 40 USDT → notional 1,333 | S4 भाग 2 | 1% slippage के साथ notional ~979 |
| "User से फ़ैसले चाहिए" (stops, capital, TF) | S4 भाग 1 | तय हो चुके (भाग 2, U1–U4) |
| F7 को "exchange पर रखा stop" कहा गया | S4 भाग 1 | F7 = 1D shorts पर entry ×1.5 (+1% slippage, 30 दिन cooldown); exchange पर catastrophe stop एक **नया** design है |
| Fibonacci "clustering" (pre-registered verdict) | S5 | Density से मिलाई गई जाँच में कोई ख़ास असर नहीं |
| Daily high/low "Asia में ज़्यादा" (uniform से तुलना) | S5 B3 | Random walk (arcsine) से तुलना: Asia सामान्य, असली असर US में |
| Citations: Shu et al. (switch rate), Lopez-Lira (pre-2010 test GDP पर था), Gu-Kelly-Xiu (annual refit सिर्फ़ मिसाल है), Alpha Arena (Hyperliquid पर), Lo & Remorov (link thesis का है) | S4 भाग 1–2 | S4 भाग 3 की तालिका देखें |

---

## भाग 10. आपसे अगला फ़ैसला
1. **Forward recorder (क्रम 2):** इसके लिए थोड़ा code लगेगा, और यह 1D VM से अलग चलेगा। इसे अभी शुरू करें या बाद में? यह साफ़ holdout के लिए ज़रूरी है, क्योंकि हर दिन की देरी साफ़ data का एक दिन खोती है।
2. **A0 protocol (क्रम 3):** लिखना शुरू करूँ? यह भी सिर्फ़ दस्तावेज़ है, कोई training नहीं।

तब तक रोज़ cloud 1D system की जाँच चलती रहेगी (क्रम 0)।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## भाग 11. Audit (18 अक्टूबर 2026): ज़मीनी जाँच और सुधार
**पूरी report:** `REPORT_MASTER_AUDIT_18_OCT_2026.md`।
- Protocol `554f13fd…` (pre-registered)।
- Verifier: 66 जाँचें, 64 PASS, 2 rounding वाले FAIL।
- ऊपर के भाग 0–10 बदले नहीं गए। जहाँ नीचे का सुधार लागू होता है, वहाँ **यही मान्य है।**

**सुधार (errata):**

| # | पहले | अब |
|---|---|---|
| E1 | 4h long p05 −0.91 | **−0.90** |
| E2 | 4h short +0.054 R | असली funding पर **+0.074** |
| E3 | 1D long +0.23 R | असली funding पर **+0.213**; spot पर +0.245, इसलिए **1D long के लिए spot** |
| E4 | Taker 0.04% / base 0.085% | **Taker 0.05% / base ~0.108%** को base मानें, जब तक असली account से पुष्टि न हो |
| E5 | 4h सीढ़ी का अगला कदम ~52% | **सिर्फ़ UP सीढ़ी में।** DOWN में कोई फ़ायदा नहीं |
| E6 | L4 में "DD पर risk घटाना" | **हटाएँ।** Test में नुकसानदेह (DD 11.4% → 13.1%) |
| E7 | Test entry: "कमाई ~20–30% कम" | Portfolio पर final −14%, Calmar −18%, DD −9% |
| E8 | 4h का P3 नहीं दिखाया | **4h long P3 −0.12 R; 4h short P3 +0.12 R** |

**नए DO:**

| # | करना है | सबूत |
|---|---|---|
| D18 | Portfolio simulator: 8,000 USDT, K = 6, leverage ≤ 3× isolated, coin के min notional | 0.5% risk पर CAGR 9.5%, DD 11.4%, Calmar 0.83, ~267 trades/साल (बिना AI, नियम वाले signals) |
| D19 | Cost model में असली funding history; spot/perp routing (1D long → spot) | B1, B3 |
| D20 | Global risk budget, मौजूदा 1D system के साथ (कुल खुला risk) | 4h+1D का Calmar 0.96; correlation 0.35 |
| D21 | Maker entry, पर fill rate और adverse selection नापकर | Calmar 0.83 → 0.92 (fill मानकर) |
| D22 | A4 में time stop 60 / 120 / कोई नहीं; AI का gate "tail winners बचाए" | Time stop वाले trades औसत +0.8 से +1.07 R; top 10% trades से 60% कमाई |
| D23 | L6 में BNB balance की जाँच; rolling 6 महीने का R (long/short अलग) सिर्फ़ review के लिए | BNB न हो तो छूट ख़त्म; P3 में long टूटा |

**नए DON'T:**

| # | नहीं करना | सबूत |
|---|---|---|
| N17 | Mechanical DD-halving, हार की लड़ी के बाद रुकना, एक दिशा की cap | Pre-registered: does not help / trade-off |
| N18 | Trades बढ़ाने के लिए 1h नियम वाले signals जोड़ना | DD 12% → 28%; 1h अकेले Calmar 0.14 |
| N19 | "N लगातार losses" पर kill switch | 27 की लड़ी इस data में सामान्य है |
| N20 | K = 3 जैसी तंग cap | 713 signals छूटे, Calmar 0.64 |

**A0 (क्रम 3) में अब यह भी lock होगा:**
- taker 0.05% base;
- असली funding;
- realised और mark-to-market दोनों DD;
- global risk budget;
- kill switch की संख्याएँ (backtest DD के ~2× पर review);
- P3 अलग report।


---

# भाग 12 (21 अक्टूबर 2026): अभी असल में क्या चल रहा है, आसान भाषा में

**यह भाग क्यों:** user ने पूछा कि अभी कौन-से timeframes पर trade हो रहे हैं, कौन-से brains चल रहे हैं, और entry, exit, stop, trailing stop, target और पैसा लगाने के फ़ैसले कैसे होते हैं। यहाँ सिर्फ़ वही लिखा है जो code, config और verified नतीजों में है। कुछ भी अनुमान से नहीं।

**स्रोत:**
- `deploy/paper_n1_config.json` (a8765f81…)
- `src/execution/paper_n1_portfolio.py` (fa7de425…)
- `logs/research_n1_portfolio/N1_PROTOCOL_PREREGISTERED.md`
- `logs/research_n3_execution/N3_PROTOCOL_PREREGISTERED.md`
- `logs/research_n6_safety_sizing/N6_results.csv`
- `REPORT_N1_TO_N5_PORTFOLIO_REGIME_EXECUTION_AI_20_OCT_2026.md`

**पुराने भागों के बारे में:** भाग 1–11 पहले जैसे ही हैं। जो पुरानी बातें बदलीं, वे `ERRATA_INDEX_R2_19_OCT_2026.md` में दर्ज हैं।

## 12.1 अभी दो अलग systems चल रहे हैं (दोनों cloud VM पर, कोई असली पैसा नहीं)

| System | Timeframe | AI? | क्या करता है |
|---|---|---|---|
| **1D system** (17 अक्टूबर से cloud पर) | 1D (साथ में H4 R6 / H1 R24 scores) | हाँ: D1 brain (HGB, हर महीने re-train), R6 और R24 brains | 16B forward paper, F4 long-short paper log, F6 Binance **demo** account पर demo orders (×1.5 stop के साथ) |
| **PAPER-N1** (21 अक्टूबर से) | 4h, 8h, 12h, 1D | **नहीं, सिर्फ़ नियम** | हर 4 घंटे पर paper ledger। कोई order नहीं जाता। |
| FR2 forward recorder | 5m से ऊपर, futures stats | नहीं | सिर्फ़ data रिकॉर्ड करता है (भविष्य की learning और साफ़ holdout के लिए) |

## 12.2 Brains का ईमानदार हिसाब: क्या बना, क्या पास हुआ

| Brain / प्रयास | TF | नतीजा |
|---|---|---|
| D1 swing brain (Step 7/16) | 1D | skill थोड़ी है; testnet / forward पर चल रहा है |
| R6 (4H), R24 (1H) | 4h / 1h | दोनों एक ही "अगला 1 दिन" वाला सवाल पूछते हैं, इसलिए अलग sleeve नहीं हैं |
| A3 4H entry brain (T05) | 4h | **FAIL** (AUC 0.514) |
| T14 वही brain 120 coins पर | 4h | **FAIL** (AUC 0.505) |
| N2 regime नियम (jump model, T16) | 1D | **FAIL** |
| N5 meta-label AI, trade छोड़ने के लिए (T18) | सभी | skill असली (AUC 0.54) पर पैसा घटा → **FAIL** |
| T20 AI से position size | सभी | **FAIL** (random sizing से भी कम) |
| 5m / 15m / 30m नियम | छोटे TF | costs के बाद हर cell में घाटा (TFX, Probe study) |
| 1h नियम जोड़ना | 1h | DD 12% से 28% (master audit N18) |

**निचोड़:** अब तक test हुआ कोई भी नया AI brain नियम-आधारित portfolio से ज़्यादा पैसा नहीं बना सका। इसलिए PAPER-N1 में AI नहीं है। यह फ़ैसला pre-registered gates ने लिया है, पसंद से नहीं।

## 12.3 "5m/15m/1h से लगातार सीखे, तो 4 घंटे में क्यों चलता है?"

1. **Decision सिर्फ़ candle बंद होने पर बनता है।** N1 का सबसे छोटा TF 4h है। 4h candle हर 4 घंटे में एक बार बंद होती है (00, 04, 08 … UTC; IST में 05:30, 09:30 …; cron 11 मिनट बाद चलता है ताकि candle पक्की बंद हो)। हर 5 मिनट चलाने से कोई नया signal नहीं बनेगा। 8h/12h/1D के signals तो और भी कम बार बदलते हैं।
2. **5m/15m पर पैसा नहीं निकला।** वहाँ चाल "उलटने" (mean reversion) वाली है, और median चाल के मुकाबले cost बहुत बड़ा है। TFX में 5m–30m की हर cell cost के बाद negative रही। 1h–1D पर trend चलता है, और कमाई वहीं है।
3. **"निरंतर सीखना" का अभी का मतलब:**
   - हर 4h पर scan होता है;
   - हर महीने की शुरुआत में sizing base (E_m) अपडेट होता है;
   - X2 routing हर entry पर पिछले 7 दिन की funding और पुराने trades का hold देखता है;
   - FR2 recorder 5m से ऊपर का data लगातार जमा करता है।

   **Model का re-training अभी कुछ नहीं होता।** यह जानबूझकर है: AI trials fail हुए, और नया AI trial नए trial budget और user की मंज़ूरी के बिना नहीं चलेगा।
4. **5m/15m का सही इस्तेमाल भविष्य में:** सिर्फ़ execution timing के लिए (बेहतर entry price), direction के लिए नहीं। N3 में maker entry (X1) adverse selection से fail हुई (भरे orders +0.9% vs न भरे +2.0%), इसलिए अभी यह भी नहीं है।

## 12.4 PAPER-N1 के चार sleeves (portfolio के हिस्से)

| Sleeve | Coins | Signal | Side | कुल budget |
|---|---|---|---|---|
| **A trend-long** | core10 (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LINK, LTC) | 4 नियम × 4 TF (4h, 8h, 12h, 1D) = हर coin पर 16 sub-signals | long | equity का 0.8× |
| **B oversold-long** | core10 | RSI14 < 30 पर entry, > 50 पर exit; 8h, 12h, 1D | long | 0.4× |
| **C trend-short** (crash hedge) | liquid U2X coins (30-दिन median perp volume ≥ 50M USDT) | वही 16 trend नियम, उलटे | short | 0.4× |
| **D XS momentum** | liquid U2X | 1D: 20-दिन return; सबसे ऊपर के 20% long, सबसे नीचे के 20% short; हर 5 दिन rebalance | long + short | 0.4× (0.2 + 0.2) |

**Trend के 4 नियम (A में long; C में बिल्कुल उलटे):**

| नियम | Entry (long) | Exit (long) |
|---|---|---|
| TSMOM20 | 20-bar return > 0 | 20-bar return ≤ 0 |
| EMAX | EMA20 > EMA50 | EMA20 ≤ EMA50 |
| MACD 12/26/9 | MACD > signal | MACD ≤ signal |
| DONCH 20/10 | close > पिछले 20 bars का high | close < पिछले 10 bars का low |

**Backtest में हर sleeve अकेले (dev 2020-02 … 2025-09, N1):**

| Sleeve | Calmar | Trades |
|---|---|---|
| A | 1.48 | 26,926 |
| B | 0.52 | 820 |
| C | ~0 | 90,232 |
| D | 0.20 | 4,976 |

कमाई का बड़ा हिस्सा A से आता है। C अकेले लगभग 0 है, पर crash में बचाव देता है। चारों साथ में बेहतर हैं, क्योंकि उनके बीच correlation कम है।

## 12.5 Entry, exit, stop, trailing stop, target

- **Entry:** signal वाली candle बंद होने के बाद, अगली candle के open पर। Paper में यह cycle के समय का भाव है। Market (taker) order माना गया है, क्योंकि maker fail हुआ था।
- **Exit:** उसी नियम की exit शर्त पूरी होने पर, अगली candle के open पर (ऊपर की table)। D में हर 5 दिन पर legs बदलती हैं।
- **Stop loss: अभी कोई नहीं।**
  - 3×ATR stop (K0) ने नतीजा बिगाड़ा, इसलिए pre-registered नियम से K1 (बिना stop) चुना गया।
  - 35% catastrophe stop (T19 S1) भी नुकसानदेह निकला: Calmar 4.16 से 2.90।
- **Trailing stop: अलग से कोई नहीं।** DONCH का "10-bar low से नीचे बंद" वाला exit और EMA/MACD/TSMOM का पलटना ही असल में trailing exit हैं। ये कीमत के साथ ऊपर खिसकते हैं और trend टूटते ही बाहर निकालते हैं।
- **Take profit: कोई fixed target नहीं।** Trend में कमाई कुछ बड़े winners से आती है (top 10% trades से ~60% कमाई), और target उन्हें काट देता है। B में "RSI > 50 पर निकलना" एक तरह का target है।
- **ईमानदार खतरा:** stop न होने से अचानक crash में नुकसान तब तक चलता है जब तक signal न पलटे।
  - Leverage 1× है, gross अधिकतम ~1.4×, और per-coin entry cap 20%। इसलिए liquidation का खतरा नहीं, पर drawdown हो सकता है: dev DD 23.7%, P3 32%।
  - Entry के बाद एक coin का हिस्सा कीमत बढ़ने से 37% तक जा सकता है। असली पैसे से पहले position-trim नियम चाहिए।

## 12.6 पैसा कैसे लगता है (capital और size)

- **शुरुआती capital:** 10,000 USDT (paper)।
- **E_m:** हर महीने की शुरुआत की equity। उस महीने के सारे नए trades इसी के हिसाब से size होते हैं।
- **एक sub-position का आकार (E_m का हिस्सा):**

  | Sleeve | आकार | उदाहरण (E_m = 10,000) |
  |---|---|---|
  | A | 0.8 / (16 × 10) = **0.5%** | 50 USDT |
  | B | 0.4 / (3 × 10) = **1.33%** | 133 USDT |
  | C | 0.4 / (16 × max(10, liquid coins)) | — |
  | D | 0.2 / (leg के coins), हर coin पर | — |

- **Multi-TF सहमति:** जितने ज़्यादा timeframes और नियम एक साथ "हाँ" कहें, उस coin में उतना ज़्यादा पैसा लगता है। उदाहरण: BTC पर सारे 16 A-signals on हों, तो 16 × 0.5% = 8%। यही timeframes का "sync" है: कोई master brain नहीं, सीधा जोड़।
- **Per-coin cap (T19 S2):** नई entry तभी होती है जब उस coin का net exposure 20% से कम हो। ज़रूरत हो तो entry छोटी कर दी जाती है।
- **Spot या perp (X2, सिर्फ़ A/B longs):** अगर पिछले 7 दिन की औसत funding × (पुराने trades का median hold घंटों में ÷ 8) > 0.00062, तो spot पर, नहीं तो perp पर। Shorts (C) और D हमेशा perp पर।
- **Costs:** perp taker 0.054% हर side, spot 0.085% हर side, और असली funding।
- **Leverage:** 1×। Backtest में gross सबसे ज़्यादा 1.41× गया।

## 12.7 Backtest के असली नंबर (FINAL = N1 K1 + X2 + 20% cap)

| Window | CAGR | Max DD | Calmar |
|---|---|---|---|
| dev 2020-02 … 2025-09 | 98.7% | 23.7% | 4.16 |
| P1 (… 2023-12) | 120.9% | 23.7% | 5.10 |
| P2 (2024-01 … 2025-09) | 57.2% | 17.8% | 3.22 |
| **P3 (2025-10 … 2026-09)** | **−12.5%** | **32.1%** | **−0.39** |

**सावधानी:**
- 2021 अकेले का +495% है।
- आख़िरी साल (P3) negative है।
- Sleeves उसी data को देखकर चुने गए थे (in-sample confirmation)। 2018–19 का out-of-time test कमज़ोर पास हुआ (Calmar 0.40)।
- असली परीक्षा forward data है।
- **Forward (21-10-2026, 2 cycles):** equity 10,002.60, positions 110, gross 0.283×, verifier 5/5।

## 12.8 आगे (कोड नहीं, सिर्फ़ योजना)

1. **PAPER-N1 का 90 दिन का forward:** ~19 जनवरी 2027। उसके बाद ही real money की बात।
2. **Trial budget 20/20 ख़त्म।** नई research के लिए user से नया budget चाहिए। उम्मीदवार:
   - (a) position trim;
   - (b) catastrophe protection, जो Calmar न गिराए;
   - (c) 5m/15m सिर्फ़ execution timing के लिए।
3. **User के काम:** rclone token rotation, असली account पर commissionRate।


## 12.9 पूरा system (5m से 1M तक) और "single ecosystem" की असली स्थिति (21-10-2026, VM crontab पढ़कर)

### 12.9.1 क्या सब एक single ecosystem में जुड़ गया है? **नहीं।**

Cloud पर अभी **चार अलग परतें** चल रही हैं। ये एक ही VM पर हैं, पर आपस में जुड़ी नहीं हैं: कोई साझा risk budget नहीं, कोई साझा portfolio नहीं, कोई master decision नहीं।

| परत | कब deploy | Cron jobs (VM) | किस पर निर्भर |
|---|---|---|---|
| **1. 1D system** (पहला पक्का cloud deploy) | 17-10-2026 | Step2_CostSnapshot, M4_OptionsCollector, Step16_ForwardDryRun, 16B_ForwardMulti, F4_LSPaper, N3_EVTMonitor, F6_DemoOps, M10_DailyStatus (15 lines) | उसी दिन का frozen code। तब से **बदला नहीं गया** |
| **2. FR2 forward recorder** | 19-10-2026 | FR2_Recorder (`37 1,5,9,13,17,21`) | सिर्फ़ data रिकॉर्ड करता है |
| **3. LogShip** (Drive) | 19-10-2026 | LogShip (`55 * * * *`) | सिर्फ़ logs भेजता है |
| **4. PAPER-N1** (4h–1D नियम portfolio) | 21-10-2026 | PaperN1 (`41 1,5,9,13,17,21`), PaperN1_Verify (`20 7`) | अपना अलग paper ledger, 10,000 USDT |

**17 अक्टूबर के बाद की research में से cloud पर क्या पहुँचा:**

| Research | Cloud पर? | क्यों |
|---|---|---|
| FR2 recorder | ✅ परत 2 | — |
| N1 + X2 + 20% cap | ✅ परत 4, सिर्फ़ paper | — |
| A0–A4, T14 (4H AI / S-LAD) | ❌ | FAIL या PBO fail |
| N2 regime, N5 AI, T20 AI sizing | ❌ | FAIL |
| N3 maker entry (X1) | ❌ | FAIL |
| Risk module L4 (`risk_rules_l4.py`) | ❌ F6 से नहीं जोड़ा | 0.4× नियम F6 के हर 1× short को रोक देता |
| 1D system में कोई बदलाव | ❌ जानबूझकर नहीं | User का नियम: 1D cloud system को न छूना |

**यानी:**
- research में जो पास हुआ, वह **अलग paper परत** के रूप में चल रहा है;
- 1D system अपनी जगह पर अलग चल रहा है;
- दोनों को एक portfolio, एक risk budget और एक execution में मिलाने का काम **अभी हुआ ही नहीं**।

यह जानबूझकर है:
- (1) 1D system न छूने का नियम;
- (2) PAPER-N1 का अभी कोई forward सबूत नहीं (2 cycles);
- (3) trial budget ख़त्म।

### 12.9.2 5m से 1M तक हर timeframe: अभी क्या होता है

| TF | Research का नतीजा (TFX / probe / master audit) | अभी cloud पर इस्तेमाल |
|---|---|---|
| 1m, 5m, 15m, 30m | चाल उलटने वाली (mean reversion), पर cost के बाद हर cell घाटे में | ❌ trade नहीं। FR2 सिर्फ़ data जमा करता है |
| 1h | Trend शुरू होता है, पर 1h नियम जोड़ने से DD 12% से 28% | ❌ trade नहीं। 1D system में H1 R24 score सिर्फ़ 16B paper में |
| **4h** | Trend timing+ ; 4H AI FAIL | ✅ PAPER-N1 sleeve A, C। 1D system में H4 R6 score (16B paper) |
| **8h, 12h** | Trend timing+, RSI-oversold long सबसे मज़बूत | ✅ PAPER-N1 sleeve A, B, C |
| **1D** | Trend, XS momentum (हर साल +), D1 swing brain | ✅ PAPER-N1 A, B, C, D। 1D system: D1 AI, F4 LS paper, F6 demo |
| 1W | Trend है (VR > 1) पर trades बहुत कम, CI चौड़े | ❌ कोई अलग नियम नहीं (सिर्फ़ research context) |
| 1M | Data बहुत कम (n < 30), "trend" definition पर निर्भर | ❌ कुछ नहीं |

**निचोड़:**
- असली trading-योग्य edge सिर्फ़ **4h से 1D** में मिली।
- 5m–1h और 1W–1M अभी system में trade नहीं करते।
- "5m से 1M तक सब timeframes पर लगातार सीखने वाला एक brain" वाला लक्ष्य अभी **बना नहीं है**। Research ने यह दिखाया कि इस data पर उसके हिस्से पैसा नहीं बनाते।

### 12.9.3 Single ecosystem बनाने के लिए क्या करना होगा (सिर्फ़ योजना, कोई code नहीं)

हर कदम के लिए user की अलग मंज़ूरी चाहिए:

1. **दोनों paper streams के forward नतीजे:**
   - 1D F4: day-90 लगभग 12-01-2027;
   - PAPER-N1: day-90 लगभग 19-01-2027।
2. **Combine protocol (नया trial budget):**
   - 1D system + N1 को एक portfolio में मिलाना;
   - एक साझा risk budget (कुल gross, per-coin cap, कुल DD सीमा);
   - backtest में monthly correlation 0.63 है, इसलिए दोनों का जोड़ diversification कम देगा। इसे नापना होगा।
3. **एक execution layer:** F6 जैसा एक executor, जो net position (एक coin पर सभी sleeves का जोड़) exchange पर रखे, और risk module के नियम 1× के हिसाब से ठीक करके जोड़े जाएँ।
4. **कमी पूरी करना:** position trim और crash protection (12.5)।
5. **उसके बाद ही** 1D system की जगह या उसके साथ एक combined system। पहले demo पर, फिर real money का फ़ैसला user का।
