# 1D Swing System: कमियाँ, गलत दावे और सुधार का रास्ता

**तारीख:** 13 अक्टूबर 2026
**GitHub:** कुछ नहीं किया गया।
**Code changes:** कोई नहीं। Bot, engine और strategy को छुआ नहीं गया; यह सिर्फ जाँच है।

**Evidence:** हर नंबर `logs/audit_1d_gaps_13oct/` की scripts से दोबारा निकाला जा सकता है:
- `diag1.py`: trades, coin, exit-reason, MFE और swing position
- `diag2.py`: बिना साल-reset वाला लगातार backtest
- `diag3.py`: ZigZag flaw और जो signals trade नहीं हुए

`diag1.py` पहले हर trade का P&L और entry price raw CSV से दोबारा मिलाता है (assert), फिर आगे के आँकड़े निकालता है।
उसी folder में `ai_final_*`, `sel_step3_before.csv` और `vault1d.csv` पुरानी scratch files हैं, जो गलती से copy हो गईं। इस audit से उनका कोई संबंध नहीं।

---

## भाग 1: जो दावे गलत या अधूरे थे (मेरे अपने भी)

### 1.1 Headline profit ($38,677) उस तरीके से नहीं बना जैसे live bot चलता है
- Walk-forward backtest हर साल अलग चलता था। इसलिए **31 दिसंबर को सारी खुली positions ज़बरदस्ती बंद** हो जाती थीं (`end_of_test`)।
- 2023–26 में ऐसे 12 trades थे, और उन्हीं से **$8,860** का P&L आया (कुल net $10,506)। इनमें SOL का +375% (2023-10-01 → 2023-12-31) भी शामिल है।
- Live bot साल के अंत में कुछ नहीं बेचता।
- **सुधरा हुआ, live जैसा नंबर:** 2021–22 walk-forward (उस समय चुने गए configs) × 2023-01-01 से 2026-09-30 तक final config का **लगातार** run (2023 से हर साल यही config चुना गया था):

| | पुराना (साल-reset) | **सही (लगातार)** |
|---|---|---|
| Final ($10k से) | $38,677 | **$40,662** (realised) |
| CAGR | 26.55% | **27.66%** |
| Max DD | 30.65% | **30.65%** (2022-03-13) |
| 2023 / 2024 / 2025 / 2026 | +60.8 / +47.7 / −1.1 / −2.3 | **+60.9 / +43.4 / +7.0 / −2.3** |

- निष्कर्ष: reset से नतीजा फूला हुआ नहीं था, थोड़ा कम ही दिख रहा था। पर पिछला monthly table (जनवरी 2025 = −2.2%) live व्यवहार नहीं दिखाता था।
- लगातार run में जनवरी 2025 **+11.7%** है, क्योंकि XRP की position चलती रही।
- सही monthly table: `logs/audit_1d_gaps_13oct/monthly_continuous.csv`।
- 30-09-2026 को equity अपने peak से 16.7% नीचे थी (पहले 22.5% बताया था; वह भी reset वाले curve से था)।

### 1.2 "Live = backtest" वाला audit किस backtest से मिला था
- L1 replay audit (124 trades हूबहू मिले) **लगातार** backtest से मिलाया गया था, साल-reset वाले B0 (133 trades) से नहीं।
- इसलिए "live bot का नतीजा = $38,677" कहना गलत था। Live के बराबर ऊपर वाला लगातार वाला नंबर है।
- 124 + 6 (30-09-2026 को खुली positions) = 130 trades; `diag2.py` में यही गिनती आई।

### 1.3 "Fully AI-based" का दावा: final system में कोई AI/ML model **नहीं** है
- Final system के नियम हाथ से बनाए गए हैं (ZigZag swing + BTC filter), और 9,072 combinations में से walk-forward से चुने गए।
- AI से size करने की दो कोशिशें (Step 4: ML features; Step 4b: swing confluence) अनदेखे data पर फेल हुईं और reject हुईं।
- आपने कहा था "कोई indicator नहीं"। पर system में ये चीज़ें हैं:
  - **ATR(14)** (swing की दूरी K×ATR, stop 1.5×ATR);
  - 20-दिन momentum (जब ज़्यादा signals हों तो कौन पहले, उसकी ranking)।
- यानी swing की परिभाषा ATR नाम के volatility माप पर टिकी है। यह छुपाना नहीं चाहिए।

### 1.4 "हर दिन के swing का permutation" जितना माँगा था, उतना नहीं हुआ
- **हुआ:** हर दिन, हर coin की swing table (Step 2), और 7 entry तरीके × stop × trailing × exit × risk = 9,072 नियम-combinations का walk-forward।
- **नहीं हुआ:**
  - entry और exit, दोनों के अलग-अलग swing पैमानों (K) का मेल। Grid में exit हमेशा entry वाले K पर ही था।
  - structure-based stop (swing low के नीचे)।
  - आंशिक profit booking।
  - "best entry / best exit day" का oracle बनाकर उससे सीखना।

### 1.5 Survivorship bias: 10 coins आज (2026) की नज़र से चुने गए हैं
- SOL, DOGE, XRP वे coins हैं जो बच गए और बड़े हुए। उन्हीं से 2023–26 का ~60% profit आया (SOL $3,577 + XRP $2,770, नीचे देखें)।
- 2021 में trader LUNA, FTT जैसे coins भी चुन सकता था, जो बाद में डूब गए। वे universe में नहीं हैं।
- **इसलिए असली भविष्य का नतीजा backtest से कम होने की संभावना है।** यह अभी ठीक नहीं हुआ है।

---

## भाग 2: Code में असली गलती (छोटी, पर गलती है)

**ZigZag का "failed confirmation" flaw** (`swing_study_1d.zigzag_pivots` + `swing_strategy_1d.zigzag_event_flags`)
- जब कोई swing confirm होने के बाद फेल होता है (price पिछले pivot के पार चला जाता है), तो algorithm अंदर दिशा बदल देता है, पर **कोई event नहीं लिखता**। इसलिए causal "state" पुरानी दिशा में अटका रहता है।
- **BTC regime (K3) पर असर, data से:**
  - 2023-05-10 से 2023-06-20 तक **41 दिन** filter "BTC ऊपर" दिखाता रहा, जबकि BTC अपने swing low के नीचे था।
  - 2026-06-24 से 12 दिन यही हुआ।
- **Coins (K4) पर असर:** पुराना swing high टूटा पर entry signal नहीं बना। 6 साल में ऐसे 8 मामले मिले, और उनके नतीजे मिले-जुले रहे:
  - ETH 2020-12 (+170%) और BNB 2021-04 (+42%) छूटे;
  - LINK 2024-03 (−30%) और SOL 2022-08 (−23%) से बचाव हुआ।
- **असर छोटा है, पर logic गलत है।** इसे ठीक करके पूरा walk-forward दोबारा चलाना होगा।

---

## भाग 3: Trades की असली तस्वीर (2023–26, final config, 133 trades)

### 3.1 "25/75" ratio
Code में कोई fixed 1:3 (25:75) risk-reward या take-profit **नहीं** है। असल आँकड़े ये हैं:

| | मूल्य |
|---|---|
| Win rate | **32.3%** (2024 में 25.6%), यानी लगभग 1 जीत, 2 हार |
| औसत जीत / औसत हार | +40.4% / −7.0%, payoff **5.7 : 1** |
| Expectancy प्रति trade | +8.3% |
| Profit factor | 2.65 |

### 3.2 Exit के कारण के हिसाब से

| Exit | Trades | Win% | औसत | P&L |
|---|---|---|---|---|
| Stop (1.5 ATR) | **82 (62%)** | 0% | −7.3% | −$6,044 |
| उल्टा swing (opposite leg) | 39 | 85% | +20.5% | +$7,690 |
| साल-अंत force close | 12 | 83% | +75.5% | +$8,860 |

**सबसे बड़ा leak (data से):**
- **Winners ने अपने सबसे ऊँचे स्तर (MFE) का median सिर्फ 37% रखा** (median MFE +39.4%, median exit +13.7%)।
- **90 हारे हुए trades में से 44 पहले +5% ऊपर गए थे, और 19 तो +10% ऊपर गए थे**, फिर stop पर बंद हुए।
- कारण: exit तभी होता है जब K=4 का उल्टा swing confirm हो, यानी peak से कम से कम 4 ATR नीचे गिरने के बाद। ज़्यादा मुनाफ़ा उसी इंतज़ार में वापस चला जाता है।

### 3.3 Swing में हम कहाँ घुसते और निकलते हैं (hindsight K4 swing; 0 = swing low, 1 = swing high)
- 106 trades मिलान हुए: **median entry 0.47 पर, median exit 0.49 पर।**
- यानी आम trade swing के बीच में घुसता है और लगभग वहीं निकलता है।
- पूरा profit कुछ बड़े swings से आता है:
  - top 5 trades = $9,773, जो net $10,506 का 93% है;
  - सारे losers मिलकर = −$6,368।

### 3.4 Coin के हिसाब से (2023–26)
- **घाटे में:** LTC (14 trades, −$885), DOT (14, −$247)।
- **लगभग शून्य:** BTC (+$21)।
- **सबसे ज़्यादा कमाई:** SOL +$3,577 और XRP +$2,770।
- हर coin के सिर्फ 8–17 trades हैं। इतने कम data पर coin हटाना hindsight overfitting होगा।

### 3.5 BTC filter काम करता है (evidence)
- 2023–26 में K4 के 167 up-signals आए। BTC filter ने 29 रोके। उन रोके गए swings का अकेला-trade नतीजा **औसत −8.0%, median −12.0%** रहा।
- Trade हुए signals का वही माप: औसत +16.7%।

### 3.6 Capital ज़्यादातर खाली बैठा रहता है
- पहले की रिपोर्ट: daily close पर invested हिस्सा median **12.2%**।
- आपने कहा था कि capital पड़ा नहीं रहना चाहिए। अभी का system इसके उलट है: slot = 80% ÷ 8 = equity का 10% प्रति trade।

---

## भाग 4: Testnet bot: अभी की ज़मीनी हालत (13-10-2026 09:07 IST)

- **Bot अभी चल नहीं रहा है।** कोई python process नहीं मिला।
- आखिरी heartbeat 03:28 UTC (08:58 IST) पर था। Task का "Last Result" `-1073741510` (0xC000013A) है, जो console window बंद होने या Ctrl+C पर मिलता है।
- Hourly watchdog इसे अगली बार **09:42 IST** पर फिर चालू करेगा।
- पहले भी gaps रहे: 12-10 को 16:13 UTC के बाद से 13-10 को 03:12 UTC तक कोई heartbeat नहीं।
- **कारण:** task "Interactive only" है और काली cmd window में चलता है। Window बंद करने, logoff करने या PC बंद होने पर bot बंद हो जाता है।
- **सुधार (आपकी मंज़ूरी चाहिए):** `pythonw.exe` से छिपी window में चलाना, और task को "user logged on हो या न हो" पर सेट करना।
- अब तक दोनों processed दिनों (10-11, 10-12) पर कोई signal नहीं आया। cash $10,000, कोई order नहीं गया।

---

## भाग 5: सुधार की योजना (Step 6, pre-registered)

**नियम:** हर नया विचार उसी walk-forward से (2020 से Y−1 तक सीखना, Y पर test), **लगातार run** (साल-reset नहीं), friction वही।
- **Accept तभी:** OOS Calmar मौजूदा B0 (लगातार) से बेहतर हो, और फायदा एक ही साल पर टिका न हो।
- Reject हुए विचार भी report होंगे।

| # | क्या | क्यों (ऊपर का evidence) |
|---|---|---|
| 6.0 | ZigZag failed-confirmation fix + लगातार run को नया baseline बनाना | भाग 1.1, 2 |
| 6.1 | **Exit research:** entry K4, पर exit तेज़ swing पर (K2/K3 का उल्टा swing); +N ATR के बाद stop को breakeven पर लाना; swing structure (आखिरी higher-low) पर trailing; आंशिक profit (कुछ हिस्सा +2R/+3R पर बेचना, बाकी trail) | Winners MFE का 37% ही रखते हैं; 44/90 losers पहले +5% पर थे |
| 6.2 | **Stop research:** 1.5 ATR बनाम confirm हुए swing low के नीचे वाला stop | 62% trades stop पर, औसत 8.7 दिन में |
| 6.3 | **Capital use:** slot 80%÷5 या ÷(खाली slots); invested हिस्सा और DD साथ में मापना | Median invested 12% |
| 6.4 | **Survivorship check:** Binance Vision से delisted coins (LUNA, FTT आदि) का data लेकर उसी system को चलाना | Universe hindsight से चुना गया है |
| 6.5 | Daemon reliability (pythonw, background) | भाग 4 |

**ईमानदार अपेक्षा:**
- 1D पर साल में ~35 trades ही होते हैं। जितने ज़्यादा विचार आज़माएँगे, गलती से अच्छा दिखने वाला नियम चुनने का खतरा उतना बढ़ेगा।
- इसलिए combinations सीमित और पहले से लिखे रहेंगे।
- ML/"AI brain" को exit के लिए फिर आज़माना संभव है, पर इतने कम trades पर overfit का खतरा बहुत है। पिछली दो ML कोशिशें इसी वजह से फेल हुईं।
