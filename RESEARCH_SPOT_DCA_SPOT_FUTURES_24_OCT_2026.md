# Spot पर "entry की quality के हिसाब से 2% / 5% खरीद + गिरने पर और खरीद + सिर्फ़ take profit (कोई stop loss नहीं)", और spot + futures की जोड़ियाँ: verified research (24 अक्टूबर 2026)

> **Discipline:**
> - Protocol नतीजों से पहले SHA से lock किया गया: `logs/research_spot_dca/SPOT_DCA_PROTOCOL_PREREGISTERED.md`, SHA `5a44d2c6…`।
> - Code `src/research/spot_dca_study.py` (`5dae6709…`) है।
> - अलग verifier `src/audits/verify_spot_dca.py` (`aadf72f5…`) के **7/7 PASS**।
> - नतीजे: `logs/research_spot_dca/SPOT_DCA_RESULTS.json` (`66bc3316…`)।
> - यह सिर्फ़ historical simulation है। कोई order नहीं दिया गया, live system में कुछ नहीं बदला।
> - मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। नीचे दी गई allocation table research scenarios हैं, निजी सलाह नहीं।

---

## 0. एक नज़र में (सीधा जवाब)

| सवाल | Verified जवाब |
|---|---|
| 2% / 5% खरीद + averaging down + 10% take profit, बिना stop loss, काम करता है? | **नहीं।** 2020-07 से 2026-09 तक 10,000 USDT **2,617** रह गए (−73.8%, CAGR −19.3%, max drawdown **−89.9%**)। उसी समय BTC को बस hold करने पर CAGR +42.3% रहा |
| पर trades तो जीतते हैं? | हाँ, **97% trades profit में बंद हुए** (342 में से 332)। फिर भी account डूबा। 332 जीतों से +10,521 आए। पर 10 delisted coins ने −7,714 और 14 फँसी positions ने −10,190 खा लिए |
| "Entry perfection" (grade A/B) से फ़र्क पड़ता है? | **नहीं।** Random coins खरीदने वाले 100 control runs से यह बेहतर नहीं निकला। पूरी अवधि में 53वें percentile पर रहा (बीच में), और holdout (2024–26) में random से भी **बुरा** (2nd percentile) |
| Take profit का % बदलें (3/5/20%, या market के हिसाब से)? | हर variant घाटे में रहा: final 1,808 से 8,243 के बीच, यानी कोई भी 10,000 से ऊपर नहीं गया |
| −50% stop loss लगाएँ तो? | और बुरा: 1,474। समस्या सिर्फ़ stop न होना नहीं है, इस तरीके में **edge ही नहीं है** |
| Spot long + perp short (cash-and-carry)? | हमेशा positive नहीं, पर कम risk वाली कमाई। BTC funding notional पर 2021 में +30.6% था, 2025 में +5.1%, और 2026 (सितंबर तक) +2.2%। Capital के हिसाब से (spot + उतना ही margin) Q3 test में **CAGR ~4.6%, drawdown ~1%** |
| "Market ऊपर जाने के बाद नीचे आता ही है": +30% rise के बाद short? | **नहीं।** 35 trades, सिर्फ़ 31% जीते, औसत **−13.1%** प्रति trade। सबसे बुरा −99.8% (ETH, दिसंबर 2020) |
| 10,000 कैसे बाँटें? | इस DCA तरीके को जोड़ने से हर मिश्रण **बिगड़ा**। ECO (backtest) + थोड़ा carry ही बेहतर दिखा। यह research scenario है, सलाह नहीं (§5) |

---

## 1. Test क्या किया (protocol के नियम, नतीजे देखने से पहले lock)

**Data**
- Binance के **सभी** USDT spot pairs, 679 coins, daily bars, 2020–2026।
- इनमें **delisted coins भी शामिल हैं**, जैसे LUNA, FTT, SRM, SXP, EOS, DENT और REEF। हर file का SHA `input_manifest.csv` में दर्ज है।
- सिर्फ़ ज़िंदा coins पर test करने से नतीजे बहुत अच्छे दिखते (survivorship bias)। St. Gallen की study के मुताबिक़ equal-weight crypto portfolios में यह bias **~62% सालाना** तक होता है।

**Universe** (उसी दिन तक का data ही इस्तेमाल):
- कम से कम 200 दिन का इतिहास हो।
- 30 दिन का median volume ≥ 10M USDT हो।
- Stablecoins, fiat pairs और leveraged tokens बाहर।

**Entry की "perfection" (grade):**

| Grade | शर्त | Size |
|---|---|---|
| **A** | 90 दिन के high से ≥ 30% नीचे, RSI14 ≤ 35, और आज का close कल के high से ऊपर (पलटाव) | **5%** of equity |
| **B** | ≥ 15% नीचे, RSI ≤ 45, और पलटाव | **2%** |

**Deep buy (averaging down):**
- Price आखिरी खरीद से 15% नीचे हो और पलटाव का दिन हो, तो फिर से खरीद।
- Size 5% (अगर grade A वाली शर्तें भी पूरी हों) या 2%।
- एक coin में अधिकतम 4 extra buys।

**Exit:**
- सिर्फ़ **take profit**: औसत खरीद भाव से +10% पर पूरा बेचना।
- कोई stop loss नहीं।
- Delist होने वाला coin उसके आखिरी दाम पर बेचा माना गया। यह असलियत से उदार है, असल में इससे कम मिलता।

**बाकी नियम:**
- Fee 0.085% प्रति तरफ़।
- फ़ैसला close पर, खरीद अगले दिन के open पर (future data का इस्तेमाल नहीं)।
- Cash पर कोई ब्याज नहीं।

**Control:** यही नियम, पर coin **random** चुने गए, 100 बार। इससे पता चलता है कि "perfect entry" का कोई असली फ़ायदा है या नहीं।

**अवधियाँ:** Full (2020-07 → 2026-09), dev (2020-07 → 2023-12), और holdout (2024-01 → 2026-09, नए 10,000 से)।

---

## 2. Q1 के नतीजे: spot DCA, बिना stop loss

### 2.1 मुख्य configuration (P)

| अवधि | 10,000 → | CAGR | Max DD | Trades | जीते | Delisted का नुकसान | अंत में फँसी positions |
|---|---|---|---|---|---|---|---|
| Full 2020-07 → 2026-09 | **2,617** | −19.3% | **−89.9%** | 342 | 97.1% | −7,714 | 14, unrealized −10,190 |
| Dev 2020-07 → 2023-12 | 7,688 | −7.2% | −76.2% | 276 | 99.3% | −1,567 | 20, −9,581 |
| Holdout 2024-01 → 2026-09 | **1,797** | −46.5% | **−91.1%** | 143 | 95.8% | −1,987 | 26, −10,389 |
| *तुलना:* BTC hold (full) | n/a | **+42.3%** | −76.6% | n/a | n/a | n/a | n/a |
| *तुलना:* ETH hold (full) | n/a | +48.1% | −79.3% | n/a | n/a | n/a | n/a |

**साल के अंत में equity:**

| साल का अंत | Equity |
|---|---|
| 2020 | 10,724 |
| 2021 | 13,622 (peak **17,098**, 15 नवंबर 2021) |
| 2022 | 4,376 |
| 2023 | 7,688 |
| 2024 | 9,254 |
| 2025 | 3,081 |
| सितंबर 2026 | **2,617** |

### 2.2 "97% जीत, फिर भी डूबा": पैसा कहाँ गया

- **332 take-profit trades** से कुल **+10,521**। औसत +31.7 प्रति trade, आधे trades 8 दिन में बंद हुए।
- **सबसे बड़े delisted नुकसान:** ये coins हर गिरावट पर और खरीदे गए, फिर बंद हो गए।

| Coin | पहली खरीद | Buys | लगाया | नुकसान |
|---|---|---|---|---|
| SRM | नवंबर 2021 | 4 | 1,372 | **−1,263** (FTX के साथ डूबा) |
| DENT | नवंबर 2021 | 5 | 1,220 | −1,203 |
| SXP | नवंबर 2021 | 5 | 1,199 | −1,192 |
| EOS | नवंबर 2021 | 5 | 1,718 | −1,029 |
| REEF | नवंबर 2021 | 5 | 1,126 | −1,003 |

- **अंत तक फँसी positions** (2021 के bull top के आसपास खरीदी गईं, 4–5 साल बाद भी घाटे में):

| Coin | Buys | लगाया | अब मूल्य | घाटा | कब से पकड़ा है |
|---|---|---|---|---|---|
| ADA | 5 | 1,774 | 340 | **−1,436** | 1,774 दिन |
| DOT | 5 | 1,384 | 116 | −1,269 | n/a |
| DODO | n/a | n/a | n/a | −1,136 | n/a |
| FIL | n/a | n/a | n/a | −1,073 | n/a |
| COMP | n/a | n/a | n/a | −871 | n/a |

- **गणित की जड़:** हर जीत छोटी है (+10% का TP, यानी एक trade पर ~+30 USDT)। हर हार **पूरी रकम** की होती है, और उस पर 5 बार averaging down की हुई होती है (−1,000 से −1,400 USDT)।
  - **एक हार लगभग 40 जीतें मिटा देती है।**
  - Stop loss न होने का मतलब है कि नुकसान की कोई सीमा नहीं।
- **Capital फँस जाता है:**
  - औसतन **81% पैसा** खुली positions में लगा रहा, और max 99.97%।
  - इसलिए नई अच्छी entries के लिए cash नहीं बचता था। मई 2021 में एक ही दिन 27 coins grade हुए और cash खत्म हो गया।
  - हमारा ECO system hourly compounding पर चलता है। यह तरीका उसका उल्टा है: पैसा सालों तक हारने वाले coins में बंद रहता है और compound नहीं होता।

### 2.3 Variants (कोई भी नतीजा देखकर नहीं चुना गया, सब दिखाए गए हैं)

**10,000 → final (max DD), full / dev / holdout:**

| Variant | Full | Dev | Holdout |
|---|---|---|---|
| TP 3% | 4,152 (−79%) | 6,978 (−77%) | 5,970 (−72%) |
| TP 5% | 2,706 (−89%) | 8,243 (−73%) | 3,461 (−83%) |
| **TP 10% (P)** | **2,617 (−90%)** | **7,688 (−76%)** | **1,797 (−91%)** |
| TP 20% | 2,615 (−93%) | 8,095 (−81%) | 1,925 (−91%) |
| Market के हिसाब से TP (bear 5% / bull 10%) | 2,103 (−91%) | 6,896 (−78%) | 1,808 (−91%) |
| Averaging down नहीं (0 adds) | 2,298 (−91%) | 5,581 (−80%) | 3,621 (−82%) |
| असीमित adds | 2,610 (−90%) | 7,688 (−76%) | 1,710 (−91%) |
| Fee 0.2% (stress) | 2,497 (−90%) | 7,589 (−77%) | 1,854 (−91%) |
| −50% stop loss (सिर्फ़ तुलना के लिए) | 1,474 (−91%) | 5,091 (−76%) | 2,862 (−81%) |

**निष्कर्ष:** **किसी भी variant ने किसी भी अवधि में पैसा नहीं बढ़ाया।** छोटा TP (3%) थोड़ा कम बुरा रहा, क्योंकि positions जल्दी निकलती हैं और कम फँसती हैं। फिर भी घाटा ही रहा।

### 2.4 क्या "entry की perfection" काम आई? (random control)

| अवधि | P का CAGR | Random 100 runs (median, 5% से 95%) | P किस percentile पर |
|---|---|---|---|
| Full | −19.3% | −19.6% (−25.5% से −10.9%) | 53% (random जैसा ही) |
| Dev | −7.2% | −8.9% (−16.8% से −0.1%) | 62% |
| Holdout | −46.5% | −35.5% (−43.1% से −22.8%) | **2% (random से भी बुरा)** |

**मतलब:** "कितनी perfect entry है" वाला score (गिरावट + RSI + पलटाव) पैसा बनाने में **कोई मदद नहीं करता**। Holdout में इसने उल्टा, गिरते coins को चुनकर ज़्यादा नुकसान कराया।

---

## 3. Q2 के नतीजे: spot + futures

### 3.1 Cash-and-carry (spot long + perp short, बराबर मात्रा): funding की कमाई

**Funding income, notional पर % प्रति साल** (कोष्ठक में: कितनी बार funding negative रहा, यानी short को देना पड़ा):

| साल | BTC | ETH |
|---|---|---|
| 2020 (जुलाई से) | +9.65% (8.5%) | +15.16% (2.5%) |
| 2021 | **+30.61%** (7.3%) | **+37.54%** (4.1%) |
| 2022 | +4.16% (22.1%) | +0.79% (34.2%) |
| 2023 | +7.87% (10.1%) | +8.26% (9.1%) |
| 2024 | +11.96% (8.4%) | +13.00% (4.2%) |
| 2025 | +5.13% (12.9%) | +4.93% (16.2%) |
| 2026 (सितंबर तक) | +2.20% (26.0%) | +1.45% (30.3%) |
| **कुल (हमेशा on)** | **+71.4%** | **+80.9%** |

- **7 दिन का funding positive हो तभी on रहने वाला filter:** BTC +60.3% और ETH +73.5%। यह filter **कम** कमाता है, क्योंकि on/off करने का खर्च लगता है।
- **रुझान:** कमाई साल दर साल घट रही है (2021 के ~31% से 2025–26 में ~2–5%), और negative funding वाले events बढ़ रहे हैं।
  - BIS की "Crypto carry" paper (2023, संशोधित 2025) कहती है कि carry कभी-कभी 40% सालाना से ऊपर जाता है, और यह trend-chasing छोटे निवेशकों की leverage माँग से बनता है।
  - 2025 के एक arXiv survey के मुताबिक़ 2025 में crypto-carry का Sharpe negative हो गया।
  - हमारा BTC perp funding data 2025 में भी +5.1% दिखाता है। यह अलग माप है: perp funding, जबकि survey में futures basis है। दोनों तस्वीरें ईमानदारी से दे रहा हूँ।
- **Margin का खतरा (verified, हमारे data से):**
  - 2020–26 में BTC का सबसे बड़ा उछाल 7 दिन में **+43%** और 30 दिन में **+133%** रहा। ETH का 7 दिन में +77% और 30 दिन में **+148%**।
  - यानी 1× short को बिना top-up बचाने के लिए **notional से भी ज़्यादा margin** चाहिए। तभी test में capital = 2 × notional माना गया।
  - असल में spot leg बढ़ता है और short घटता है। अगर दोनों अलग wallet में हैं, तो short का liquidation हो सकता है, भले ही कुल position neutral हो।
- **बचे हुए खतरे:** exchange का खतरा (FTX जैसा), lower funding का दौर, spot और perp के भाव में फ़र्क (basis), और fee।

### 3.2 Bear hedge (BTC SMA200 के नीचे होने पर DCA book के बराबर BTC short)

| | Final | Max DD | CAGR |
|---|---|---|---|
| DCA (P) | 2,617 | −89.9% | −19.3% |
| DCA + hedge | 4,391 | −76.2% | −12.3% |

- Hedge ने नुकसान घटाया (+1,774), **पर तरीका फिर भी घाटे में रहा।**
- एक छुपी शर्त भी है: hedge का notional idle cash के **2.65 गुना** तक गया। यानी असल में इतना margin था ही नहीं। इस हिसाब से असली नतीजा और बुरा होता।

### 3.3 "ऊपर गया है तो नीचे आएगा": 30 दिन में +30% के बाद 30 दिन का short (BTC और ETH)

- **35 trades:** 31% जीते, **औसत −13.1%** प्रति trade, कुल −459% (प्रति trade % का जोड़)।
- सबसे बुरा: **−99.8%** (ETH, दिसंबर 2020 में short किया, भाव दोगुना हो गया)।
- **मतलब:** तेज़ उछाल के बाद market अक्सर और ऊपर जाता है (momentum)। "नीचे आएगा ही" वाली सोच को 30 दिन में भुनाना **नुकसानदायक** है।
- हमारे ECO system में shorts trend के signal पर लगते हैं, सिर्फ़ उछाल देखकर नहीं।

---

## 4. Hourly compounding वाले हमारे ecosystem से मेल

- ECO हर घंटे positions को target पर लाता है। Risk की सीमाएँ और kill switch तय हैं, और profit तुरंत अगले cycle में काम आता है।
- यह DCA तरीका इसका उल्टा है:
  - पैसा सालों तक फँसता है (1,774 दिन तक);
  - नुकसान की कोई सीमा नहीं;
  - **एक coin में 5 बार खरीद** से concentration बढ़ता है।
- Correlation (2021–26): ECO और DCA के बीच 0.06 है। यानी यह diversification नहीं देता, सिर्फ़ नुकसान जोड़ता है।

---

## 5. Q3: 10,000 USDT के मिश्रण (research scenarios, सलाह नहीं)

**Setup:**
- 2021-01-02 → 2026-09-30, हर महीने rebalance।
- ECO = deployed design की **backtest** series (ECO-W2)। Backtest नंबर हमेशा live से ज़्यादा अच्छे दिखते हैं, live का सबूत अभी सिर्फ़ कुछ दिनों का है।
- Carry = BTC cash-and-carry, filter के साथ, capital = 2 × notional।

| मिश्रण (ECO / DCA / carry) | 10,000 → | CAGR | Max DD | Sharpe |
|---|---|---|---|---|
| 100 / 0 / 0 | 110,026 | 51.8% | −18.7% | 2.10 |
| 80 / 20 / 0 | 63,294 | 37.9% | −31.9% | 1.53 |
| 70 / 15 / 15 | 54,235 | 34.2% | −26.1% | 1.66 |
| 60 / 20 / 20 | 42,153 | 28.5% | −29.6% | 1.37 |
| 50 / 25 / 25 | 32,492 | 22.8% | −34.1% | 1.07 |
| 0 / 100 / 0 (सिर्फ़ DCA) | 2,336 | −22.4% | −90.3% | 0.00 |
| 0 / 0 / 100 (सिर्फ़ carry) | 12,954 | 4.6% | **−1.0%** | 7.37 |

**आपस का correlation:** ECO–DCA 0.06, ECO–carry 0.12, DCA–carry ≈ 0।

**पढ़ने का तरीका:**
- DCA का हर हिस्सा मिश्रण को **बिगाड़ता** है: return घटता है और drawdown बढ़ता है।
- Carry कम कमाता है, पर बहुत स्थिर है, और ECO से कम जुड़ा है।
- "ECO + थोड़ा carry" (बिना DCA) वाला मिश्रण pre-registered नहीं था, इसलिए उसका नंबर नहीं दे रहा। चाहें तो वह अगला pre-registered test हो सकता है।

---

## 6. ईमानदार सीमाएँ

- **Daily bars:** एक ही दिन में खरीद और TP का क्रम मान लिया गया (खरीद open पर, फिर TP)। Hourly data पर नतीजा थोड़ा बदल सकता है, पर ~−74% के घाटे को पलट दे, ऐसा संभव नहीं।
- **Delisting:** coin आखिरी दाम पर बिका माना गया, जो असलियत से उदार है।
- **सिर्फ़ Binance spot data।** Liquidity की सीमा 10M है।
- **सिर्फ़ BTC/ETH पर यही तरीका test नहीं किया गया** (protocol में नहीं था)। वहाँ delisting का खतरा नहीं है, पर 2021–22 में −77% जैसी गिरावट वहाँ भी आई। अगर आज़माना हो, तो यह नया pre-registered test होगा।
- **Funding carry में** spot और perp के भाव का अंतर (basis P&L), borrow cost और exchange risk शामिल नहीं हैं।
- **Q3 का ECO हिस्सा backtest है**, live नहीं।

---

## 7. Verification (क्या जाँचा, क्या गलत मिला, क्या ठीक किया)

| Check | नतीजा |
|---|---|
| V1 | 679 input files का SHA, manifest से मेल ✅ |
| V2 | Grade वाले (coin, दिन) loops से निकाले गए। जहाँ cash बचा था, वहाँ study ने कोई entry नहीं छोड़ी ✅ (सीमा: cash ज़्यादातर खत्म रहता था, इसलिए सिर्फ़ 10 मामले असली test बने) |
| V2b | Study की हर नई entry अपने grade की शर्त पूरी करती है (RSI, गिरावट, पलटाव loops से दोबारा गिने) ✅ |
| V3 | पूरा ledger अलग cash loop से दोबारा चलाया: final **2,617.24 = report**, 21 तारीखों पर equity 1e-6 तक बराबर ✅ |
| V4 | सभी 342 exits fill के नियम पर सही ✅ |
| V5 | BTC और ETH का funding हर साल raw CSV से दोबारा गिना ✅ |

**पहली बार verifier चलाने पर 3 checks fail हुए थे। तीनों की जाँच की, और इनमें से कोई भी study के logic की गलती नहीं निकला:**
1. JSON में prices 10 अंक तक कटे हुए थे। Output ठीक किया।
2. Verifier में खुली positions की खरीद नहीं जुड़ी थी। Verifier ठीक किया।
3. ALGO की entry cash खत्म होने से छूटी थी, protocol के नियम के मुताबिक़ सही। Verifier की शर्त ठीक की।

Fix के बाद दूसरा run हर नतीजे में पहले run जैसा ही रहा, सिर्फ़ code SHA बदला। सब `logs/research_spot_dca/CODE_CHANGES_AFTER_LOCK.md` में दर्ज है।

---

## 8. Sources (बाहरी)

- BIS Working Paper No. 1087, "Crypto carry" (Schmeling, Schrimpf, Todorov; 2023, संशोधित 2025): https://www.bis.org/publ/work1087.htm
- "Cryptocurrency as an Investable Asset Class: Coming of Age" (arXiv 2510.14435; 2025 में carry Sharpe का negative होना): https://arxiv.org/pdf/2510.14435
- Survivorship / delisting bias, St. Gallen (3,904 coins, 2014–2021): https://alexandria.unisg.ch/handle/20.500.14171/108037
- Averaging down और martingale के खतरे (practitioner स्रोत, peer-reviewed नहीं): https://www.luxalgo.com/library/concept/averaging-down.md और https://www.mql5.com/en/blogs/post/773495

---

## 9. आगे (सिर्फ़ सुझाव, कोई deploy नहीं)

1. यह DCA तरीका live ecosystem में **न जोड़ा जाए**। Data कहता है कि इससे पैसा डूबता है।
2. अगर spot का कोई हिस्सा चाहिए, तो सबसे कम खतरे वाला विकल्प cash-and-carry दिखा (BTC/ETH, पूरा margin)। उसे भी पहले अलग pre-registered forward paper test से गुज़ारना होगा। कमाई घट रही है (2025–26 में ~2–5% notional पर)।
3. "सिर्फ़ BTC/ETH पर averaging down + TP" और "ECO + carry" अगले pre-registered tests हो सकते हैं, आपकी हाँ पर।

*मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।*
