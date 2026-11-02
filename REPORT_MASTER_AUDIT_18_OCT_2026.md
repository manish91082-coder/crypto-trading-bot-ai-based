# Master Integrated Research का ज़मीनी audit: गलतियाँ, कमियाँ, सुधार, और loss घटाने, trades बढ़ाने व profit बढ़ाने के रास्ते (18 अक्टूबर 2026)

**किसका audit:** `MASTER_INTEGRATED_RESEARCH_17_OCT_2026.md` (SHA `3347489d…`)।

**तरीका:**
- **Protocol:** पहले से लिखा और lock किया गया: `logs/research_master_audit/MASTER_AUDIT_PROTOCOL_PREREGISTERED.md`, SHA `554f13fd…`, lock 2026-10-17T18:41Z।
- **Study code:** `src/research/master_audit_portfolio.py` (`e5d885ec…`)।
- **Independent verifier:** `src/audits/verify_master_audit.py` (`d436f2eb…`)। इसने 66 जाँचें कीं: 64 PASS, 2 FAIL। दोनों FAIL rounding के हैं, उनकी व्याख्या नीचे §1 में है।
- **Lock के बाद के नोट:** `CODE_CHANGES_AFTER_LOCK.md`।

**क्या छुआ नहीं गया:** कोई order नहीं, कोई training नहीं। Cloud 1D system और laptop production अछूते हैं। `archive/` का इस्तेमाल नहीं हुआ। GitHub पर कुछ नहीं हुआ।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। नीचे के नतीजे research हैं, निवेश सलाह नहीं।

---

## सार (सबसे ज़रूरी 10 बातें)
1. **Master के आँकड़े सही निकले।**
   - सभी 15 source और code SHA मेल खाते हैं।
   - 47 आँकड़ों में से 45 हूबहू मिले। 1 छोटी rounding गलती है (4h long p05 −0.90 है, −0.91 नहीं)। 1 rounding की सीमा पर है (1D खर्च 3.65%)।
2. **Futures taker fee शायद 0.05% है, 0.04% नहीं।**
   - बाहरी स्रोत regular user के लिए 0.02% maker / 0.05% taker बताते हैं। Demo API ने 0.04% दिया था।
   - इसलिए असली round trip ~0.085% नहीं, ~**0.108%** मानना चाहिए।
   - असर नापा: 4h पर Calmar 0.83 से घटकर 0.78। मामूली है, पर A0 में यही base cost होना चाहिए।
3. **असली funding से shorts बेहतर निकले।** Master ने हर trade पर 0.01%/8h खर्च माना था, पर असली history में shorts को औसतन funding **मिली**:
   - 4h short: +0.054 से **+0.074 R**;
   - 1D short: +0.109 से **+0.148 R**।
   - Longs थोड़ा कमज़ोर हुए (4h long +0.106 से +0.101)।
4. **Portfolio स्तर पर पहली बार पैसे में आँकड़े** (सिर्फ़ नियम वाले सीढ़ी signals, बिना AI; 8,000 USDT; 0.5% risk प्रति trade; एक साथ अधिकतम 6 trades):
   - 2020-02 से 2026-09 में 8,000 से **14,629**;
   - **CAGR 9.5%, max DD 11.4%, Calmar 0.83, ~267 trades/साल**।
   - **चेतावनी:** आख़िरी साल (P3) **−1.1%** रहा।
5. **Loss घटाने के तीन "स्वाभाविक" नियम नुकसानदेह निकले** (pre-registered फ़ैसला):

   | नियम | DD | Calmar | फ़ैसला |
   |---|---|---|---|
   | DD 10% होने पर risk आधा करना | 11.4% → 13.1% (बढ़ा) | 0.83 → 0.52 | **does not help** |
   | 4 लगातार losses के बाद 24 घंटे रुकना | — | — | trade-off |
   | एक दिशा में अधिकतम 3 positions | — | 0.45 | **does not help** |

6. **कारण: कमाई कुछ ही trades से आती है।**
   - 4h पर कुल कमाई का ~**60%** सबसे अच्छे 10% trades से आता है।
   - उन्हें हटा दें तो कुल **घाटा** बचता है: 4h long +103 R से −142 R।
   - इसलिए जो भी नियम trades छोड़ता है, वह tail वाले winners भी छोड़ता है।
7. **Test entry (V2) portfolio स्तर पर एक "बीमा" ही है, मुफ़्त नहीं।**
   - DD 11.4% से 10.4% हुआ, पर Calmar 0.83 से 0.68 गिरा।
   - Final 14,629 से 12,613 हुआ।
8. **Trades बढ़ाने का सबसे अच्छा तरीका 4h + 1D है, 1h नहीं।**
   - 4h+1D: Calmar **0.96** (CAGR 12.3%, DD 12.8%, ~300 trades/साल)।
   - 1h नियम वाले signals जोड़ने पर DD 24–28% हो जाता है। अकेले 1h का Calmar 0.14 है।
   - Monthly correlation: 4h–1D 0.35, 4h–1h 0.15।
9. **Profit बढ़ाने के संकेत:**
   - 60-bar time stop पर बंद हुए trades औसतन **+0.8 से +1.07 R** पर थे, और उनमें से 14% ने 2R से ज़्यादा कमाया था। यानी time stop winners को काट रहा हो सकता है, और A4 में लंबा या बिना time stop परखना चाहिए।
   - Maker entry से Calmar 0.83 से **0.92** हुआ।
10. **Master में कुछ ज़रूरी चीज़ें गायब थीं:**
    - margin mode और leverage की सीमा;
    - BNB balance का प्रबंधन;
    - kill switch की संख्याएँ (27 लगातार losses भी सामान्य हैं);
    - नीचे की सीढ़ी में continuation का कोई फ़ायदा नहीं है;
    - 1D long के लिए spot सस्ता है;
    - 1D system के साथ एक साझा (global) risk सीमा।

    पूरी सूची §3 में है।

---

## 1. ज़मीनी जाँच: master के आँकड़े बनाम source (verifier, Part A)
| जाँच | नतीजा | Source का मान |
|---|---|---|
| भाग 0 के 15 SHA (reports, code, protocols, crontab) | **सब PASS** | — |
| 3.4 V0 R/trade (5m −0.12, 15m −0.05, 1h +0.03, 4h long +0.106 / short +0.054, 1D long +0.23 / short +0.105) | PASS | −0.1235, −0.0516, 0.0269, 0.1061, 0.0541, 0.2275, 0.1045 |
| 3.4 V1–V3 की सीमाएँ (6 पंक्तियाँ) | PASS | जैसे 4h long [0.083, 0.082, 0.076] |
| 3.4 सबसे बुरे 5% (7 पंक्तियाँ) | 6 PASS, **1 FAIL** | 4h long V0 −0.9046, यानी **−0.90** छपना चाहिए था, master में −0.91 |
| 1D long 153 trades; 5m कुल −12,000 R; 1D long P3 −0.36 → V3 ≈ 0 | PASS | 153; −12,066; −0.358 → −0.004 |
| 3.2 timeframe तालिका (चाल, खर्च %, VR; 7 TF) | 6 PASS, **1 सीमा पर** | 1D खर्च 3.65% (source में 4 decimal तक rounded), master में 3.7% |
| 3.3 सीढ़ी: UP 31–36%, DOWN 29–31%, बाकी ~35%, 1 कदम ~50%, 5+ कदम 1–3%, नीचे की सीढ़ियाँ छोटी | PASS | 0.311–0.362; 0.291–0.313; 0.348–0.376; 0.41–0.53; ≤3.2%; 1.14 बनाम 1.33 कदम |
| Pullback median ~0.61 (IQR 45–77%) | PASS | 0.608; q25 0.44–0.49, q75 0.75–0.79 |
| Double top/bottom +3 से +9 pp | PASS (5m से 4h) | +2.7 से +8.9 |
| 4h सीढ़ी का अगला कदम ~52% बनाम 48.7% | PASS, **पर अधूरा** | सिर्फ़ UP सीढ़ी में। DOWN सीढ़ी में 43.3% और 31.5%, जबकि base 43.6% है, यानी **कोई फ़ायदा नहीं** |
| US session में 1h swings 39–43% | PASS | 38.6% / 43.3% |
| Demo taker 0.04% / maker 0.02%; risk 40 USDT → notional ~979 | PASS | 0.0004/0.0002; 979.2 |

**बाहरी जाँच (fee):**
- Binance support का पन्ना पुष्टि करता है कि USDⓈ-M futures पर BNB से fee देने पर **10% छूट** मिलती है, बशर्ते BNB futures wallet में हो। BNB कम पड़े तो fee **USDT में कटती है और छूट नहीं मिलती।**
- Regular user की दर 0.02% maker / **0.05% taker** है। यह तीसरे पक्ष के स्रोतों से है, Binance की live fee table से पुष्टि होनी बाकी है।
- Demo API ने 0.04% बताया था। इसलिए असली account का `commissionRate` (master भाग 8) अब और ज़रूरी हो गया है। तब तक **0.05% को base** मानना सुरक्षित है।

---

## 2. नई ज़मीनी study: loss, trades, profit (Part B; verifier PASS)
**Setup:** S6 के 4h/1h/1D सीढ़ी trades (signals, stops, 3 ATR trailing, 60-bar time stop वही)।
- **बदलाव:**
  - असली funding;
  - 8,000 USDT;
  - notional = risk ÷ (stop% + 1% + 0.09%);
  - leverage cap 3×;
  - coin के minimum notional;
  - perp listing से पहले के 47 trades बाहर।
- **Equity सिर्फ़ realised है,** इसलिए असली intraday DD इससे ज़्यादा होगा।

### 2.1 असली funding (B1)
| TF, side | माना गया funding (R) | असली funding (R) | Net R (माना) → Net R (असली) | P1 / P2 / P3 (असली) |
|---|---|---|---|---|
| 4h long | 0.012 | 0.017 | 0.106 → **0.101** | 0.116 / 0.184 / **−0.123** |
| 4h short | 0.015 | **−0.004** (मिला) | 0.055 → **0.074** | 0.055 / 0.084 / 0.116 |
| 1D long | 0.021 | 0.039 | 0.231 → **0.213** | 0.298 / 0.138 / **−0.352** |
| 1D short | 0.038 | −0.001 | 0.109 → **0.148** | −0.027 / 0.206 / 0.499 |
| 1h long / short | 0.007 | 0.007 / −0.003 | 0.026 / 0.002 → 0.025 / 0.012 | — |

**मतलब:**
- Bull market में longs funding देते हैं और shorts पाते हैं।
- **आख़िरी साल (P3) में 4h और 1D के longs घाटे में रहे और shorts कमाई में।** यह master में 4h के लिए दर्ज नहीं था।

### 2.2 Risk और एक साथ कितने trades (G1; 4h, long + short)
| Risk/trade | K (एक साथ अधिकतम) | Final (8,000 से) | CAGR | Max DD | Calmar | Trades/साल |
|---|---|---|---|---|---|---|
| 0.25% | 3 | 10,043 | 3.5% | 5.5% | 0.63 | 180 |
| 0.25% | 6 | 10,921 | 4.8% | 5.8% | 0.83 | 267 |
| **0.5%** | 3 | 12,490 | 6.9% | 10.8% | 0.64 | 180 |
| **0.5%** | **6** | **14,629** | **9.5%** | **11.4%** | **0.83** | **267** |
| 0.5% | 10 / असीमित | 14,820 | 9.7% | 12.0% | 0.81 | 284 |
| 1.0% | 6 | 24,858 | 18.6% | 22.4% | 0.83 | 267 |
| 1.0% | 10 / असीमित | 25,213 | 18.8% | 22.8% | 0.83 | 284 |

- **Calmar लगभग स्थिर (~0.83) है।** Risk दोगुना करें तो कमाई और DD दोनों लगभग दोगुने होते हैं। कितना risk लेना है, यह **आपका फ़ैसला** है; data बस यह तालिका देता है।
- **K = 3 से नुकसान है:** 713 signals छूटते हैं, Calmar 0.64। K = 6 पर्याप्त है।
- **Leverage:** 0.5% पर अधिकतम 0.71× और 1% पर 1.41×। Median notional 638 USDT है (95th percentile 1,473)।
- कोई signal minimum notional की वजह से नहीं छूटा। 10,000 USDT के लिए 3× isolated margin काफ़ी है।

### 2.3 Trades बढ़ाना (G2; 0.5%, K = 10)
| Streams | CAGR | Max DD | Calmar | Trades/साल | P3 |
|---|---|---|---|---|---|
| 4h | 9.7% | 12.0% | 0.81 | 284 | +0.1% |
| 1h | 5.1% | **36.1%** | 0.14 | 1,157 | −10.4% |
| 1D | 3.9% | 4.2% | 0.92 | 44 | +6.3% |
| 4h+1h | 14.0% | 27.7% | 0.51 | 1,306 | −4.7% |
| **4h+1D** | **12.3%** | **12.8%** | **0.96** | **299** | **+3.3%** |
| 4h+1h+1D | 15.6% | 23.7% | 0.66 | 1,137 | +1.9% |

**Monthly R correlation:** 4h–1D 0.35, 4h–1h 0.15, 1h–1D 0.19।

**नतीजा:**
- **ज़्यादा trades का मतलब ज़्यादा profit नहीं है।** 4h में 1h नियम वाले signals जोड़ने से trades ~4.6 गुना हुए, पर DD 12.0% से 27.7% (2.3 गुना) हो गया।
- सबसे अच्छा जोड़ **4h + 1D** है। 1D का सिस्टम पहले से cloud पर चल रहा है (अछूता)। इसलिए असली सवाल यह है कि 4h sleeve और मौजूदा 1D system को **account स्तर पर एक साझा risk budget** में कैसे रखा जाए।

### 2.4 Loss घटाने के नियम (G3; pre-registered फ़ैसला; baseline 4h, 0.5%, K = 6)
| नियम | Final | Max DD | Calmar | फ़ैसला |
|---|---|---|---|---|
| Baseline | 14,629 | 11.4% | 0.83 | — |
| L1: DD ≥ 10% पर risk आधा | 12,405 | **13.1%** | 0.52 | **does not help** (उल्टा नुकसान) |
| L2: 4 लगातार losses के बाद 24 घंटे रुकना | 13,111 | 10.8% | 0.71 | trade-off (random pause के 90th percentile 0.92 से भी नीचे) |
| L3: एक दिशा में अधिकतम 3 | 11,156 | 11.5% | 0.45 | **does not help** |
| L4: test entry V2 | 12,613 | 10.4% | 0.68 | trade-off |
| L5: सिर्फ़ long | 11,778 | 8.9% | 0.68 | trade-off |

**Robustness (नियम नहीं):**

| Scenario | Calmar |
|---|---|
| खर्च ×1.5 | 0.70 |
| Taker 0.05% | 0.78 |
| बिना BNB | 0.80 |
| **Maker entry** | **0.92** |

**क्यों:**
- कमाई कुछ ही trades में है (§2.5)। जो नियम नुकसान के बाद रुकता है या size घटाता है, वह अक्सर recovery वाले बड़े winner के समय छोटा होता है।
- L1 के साथ ठीक यही हुआ: DD घटने की जगह **बढ़ा**।

### 2.5 Profit कहाँ से आता है (B4)
| | 4h long | 4h short | 1D long | 1D short |
|---|---|---|---|---|
| Win rate | 39% | 41% | 44% | 44% |
| औसत जीत / औसत हार (R) | 1.04 / −0.49 (**2.1×**) | 0.94 / −0.53 (1.8×) | 1.19 / −0.56 (2.1×) | 0.90 / −0.43 (2.1×) |
| सबसे अच्छे 10% trades का कमाई में हिस्सा | **60%** | 60% | 56% | 50% |
| कुल R → top 10% हटाकर | +103 → **−142** | +69 → −145 | +32 → −13 | +22 → −7 |
| Time stop पर बंद (n, औसत R) | 36, **+0.81** | 72, **+1.07** | 2, +0.90 | 31, +0.88 |
| Time stop वाले जिनका gross > 2R | 14% | 14% | 0% | 13% |
| Stop पर बंद (औसत R) | +0.08 | −0.01 | +0.20 | −0.04 |

- **Portfolio में सबसे लंबी हार की लड़ी 27 trades की रही** (K = 6)। इसलिए "N लगातार losses पर alarm" वाला kill switch गलत समय पर चलेगा।

---

## 3. Master में गलतियाँ और कमियाँ (पूरी सूची)
### 3.1 गलतियाँ (errata; master में भाग 11 के रूप में जोड़ी गईं)
| # | Master में | सही |
|---|---|---|
| E1 | 4h long p05 −0.91 | **−0.90** (cosmetic) |
| E2 | 4h short +0.054 R | माने गए funding पर सही; **असली funding पर +0.074** |
| E3 | 1D long +0.23 R | असली funding पर **+0.213**। Spot पर +0.245 (funding नहीं), यानी **1D long के लिए spot बेहतर** |
| E4 | Base cost 0.085% (taker 0.04%) | बाहरी स्रोतों के अनुसार taker 0.05%, यानी **~0.108%**। असली account से पुष्टि होने तक यही base |
| E5 | "4h पर सीढ़ी का अगला कदम ~52% बनाम 48.7%" | सिर्फ़ **UP** सीढ़ी में। DOWN सीढ़ी में कोई फ़ायदा नहीं (43.3%, 31.5% बनाम 43.6%) |
| E6 | L4: "DD पर risk घटाना" (§6.1) | Pre-registered test में यह **नुकसानदेह** निकला (DD 11.4% से 13.1%)। Mechanical DD-halving नहीं। Size घटाना सिर्फ़ operational गड़बड़ (data, reconcile, stop गायब) या बहुत बड़े DD पर हो |
| E7 | D5: test entry "बीमा: कमाई ~20–30% कम" | Portfolio स्तर पर final 14% कम, Calmar 18% कम, DD 9% कम। बीमा महँगा है |
| E8 | 3.4 में 4h का P3 नहीं दिखाया गया | 4h long P3 **−0.12 R** (असली funding)। आख़िरी साल में long edge टूटा |

### 3.2 कमियाँ (master में नहीं था, अब जोड़ना ज़रूरी)
| # | कमी | सुझाव (आधार) |
|---|---|---|
| M1 | Portfolio स्तर के आँकड़े (CAGR, DD, trades/साल) | §2.2 की तालिका; A5 में AI वाले signals पर यही ढाँचा |
| M2 | Margin mode, leverage, liquidation | Isolated margin; leverage ≤ 3× (0.5% पर ज़रूरत 0.71×); liquidation price हमेशा stop से बहुत दूर हो, यह entry से पहले जाँचा जाए |
| M3 | BNB balance का प्रबंधन | BNB futures wallet में रहे, वरना छूट ख़त्म (Binance support)। Monitor (L6) BNB balance जाँचे; BNB के भाव का जोखिम छोटा रखें |
| M4 | Kill switch की संख्याएँ | हार की लड़ी पर alarm नहीं (27 की लड़ी सामान्य है)। Alarm operational हों। DD पर रुकने की सीमा backtest DD के ~2× पर review (जैसे 0.5% risk पर ~22–25%); यह संख्या A0 में lock हो |
| M5 | असली funding | A0 के cost model में असली funding history; माना हुआ 0.01%/8h नहीं |
| M6 | Spot या perp routing | 1D long → spot; 4h long → लगभग बराबर (spot 0.107 बनाम perp 0.101); short → perp। X8 में इसे पहले से पंजीकृत करें |
| M7 | मौजूदा 1D system के साथ साझा risk | अलग sub-account के बावजूद **global risk budget** हो (दोनों का कुल खुला risk)। 4h–1D correlation 0.35 है, जो diversification के लिए अच्छा है |
| M8 | Time stop और trailing की लंबाई | A4 grid में "60 bar बनाम 120 bar बनाम कोई time stop नहीं" और trailing 3 बनाम 4 ATR। Trial budget में गिना जाए |
| M9 | Short signals की कमज़ोरी | DOWN सीढ़ी continuation में edge नहीं। Short के लिए AI को दूसरे features चाहिए: funding, basis, volume, HTF |
| M10 | Regime या decay की निगरानी | P3 में 4h long टूटा। L6 में rolling 6 महीने का R per trade, long और short अलग, alarm सिर्फ़ review के लिए |
| M11 | Mark-to-market DD | Forward recorder और engine से नापना; backtest का realised DD कम दिखाता है |
| M12 | Maker entry का असली fill rate | Maker से Calmar 0.83 से 0.92 हुआ, पर post-only पर adverse selection (जो भरता है वह अक्सर बुरा trade) नापा नहीं गया। A4/A7 में नापें |
| M13 | Universe | सिर्फ़ 10 बड़े coins (survivorship)। Trades बढ़ाने का सही रास्ता ज़्यादा coins (liquidity filter के साथ) हो सकता है, ज़्यादा TF नहीं। A3–A5 में परखें |
| M14 | Exchange की घटनाएँ | Delisting, API outage, ADL, funding interval का बदलना। Chaos tests (A7) में जोड़ें |

---

## 4. Loss घटाना, trades बढ़ाना, profit बढ़ाना: क्या काम करता है (सबूत के क्रम में)
### Loss घटाना
1. **Risk per trade (f) ही सबसे सीधा लीवर है।** DD लगभग f के अनुपात में बढ़ता है (0.25% पर 5.8%, 0.5% पर 11.4%, 1% पर 22.4%)।
2. **Diversification: 4h + 1D** (correlation 0.35) से Calmar 0.81 से 0.96 हुआ।
3. **खर्च घटाना:** maker entry (Calmar 0.92), BNB से fee, 1D long spot पर।
4. **Catastrophe stop + 1% slippage वाली sizing** (पहले से master में)।
5. **Test entry (V2)** सिर्फ़ तब, जब DD कम रखना कमाई से ज़्यादा ज़रूरी हो। यह trade-off है।
6. **ना:** DD-halving, हार के बाद रुकना, एक दिशा की cap। तीनों इस data पर नुकसानदेह या बेअसर निकले।

### Trades बढ़ाना
- 4h long + short से ~267/साल (K = 6)। 1D जोड़ने पर ~300।
- **1h नियम वाले signals से नहीं** (DD 36%)। 1h तभी, जब AI उसे साबित करे (Phase B)।
- **अगला सबसे अच्छा रास्ता ज़्यादा coins हैं** (परखना बाकी)।

### Profit बढ़ाना
1. **Winners को मत काटो।** Trailing हाँ, fixed TP ना। 60 bar के time stop को A4 में लंबा करके परखें।
2. **AI (B2-fast) का असली काम है बुरे trades छाँटना, अच्छे नहीं।** Payoff 2:1 है और win rate ~40%। अगर AI 40% बुरे trades हटा दे और tail वाले winners बचे रहें, तो mean R तेज़ी से बढ़ेगा। Gate यही हो कि top-decile winners का कितना हिस्सा AI ने रखा।
3. **Shorts में funding की कमाई।** Routing और side चुनते समय funding को feature की तरह लें।
4. **Size:** Calmar स्थिर है। ज़्यादा कमाई सिर्फ़ ज़्यादा risk से आएगी, और वह फ़ैसला आपका है।

---

## 5. Priority क्रम में बदलाव (master भाग 7 पर)
- **क्रम 3 (A0 protocol) में lock करना है:**
  - base taker 0.05%;
  - असली funding;
  - realised और mark-to-market दोनों DD;
  - portfolio simulator (§2 वाला);
  - global risk budget, 1D के साथ;
  - E6 (DD-halving नहीं);
  - kill switch की संख्याएँ।
- **क्रम 4 (A1):** हर signal का mean R long और short अलग, और **P3 अलग**।
- **क्रम 7 (A4):** time stop 60 / 120 / कोई नहीं; maker entry का fill rate; V0 बनाम V2।
- **क्रम 13:** "1D sleeve" को पीछे रखने की जगह मौजूदा 1D system के साथ **account-level combination study** पहले हो (सिर्फ़ research)।
- बाकी क्रम वही रहे, और forward recorder (क्रम 2) अब भी सबसे ज़रूरी है।

## 6. ईमानदार सीमाएँ
- **सिर्फ़ नियम वाले signals:** AI नहीं, 10 बड़े coins, survivorship।
- **DD realised-only है।** असली DD ज़्यादा होगा।
- **Funding:** fill price पर, mark price पर नहीं।
- **P3** पहले देखा जा चुका है।
- **ये सब design priors हैं।** हर चुनाव A0 के 20 trials के भीतर दोबारा परखा जाएगा।
- **Fee का स्रोत:** 0.05% वाली दर तीसरे पक्ष से है; Binance की fee table या असली account से पुष्टि बाकी है।

## Sources (बाहरी)
- [Binance support: USDⓈ-M futures में BNB से fee पर 10% छूट](https://www.binance.com/es/support/articles/360033544231)
- [Finder: Binance futures fees (regular user 0.02% / 0.05%)](https://www.finder.com/binance-futures-fees)
- [Exchange fee comparison 2026](https://traderssecondbrain.com/tools/exchange-fees)

## Files
`logs/research_master_audit/`:
- protocol और `PROTOCOL_SHA256.txt`;
- B1, G1, G2, G2_corr, G3, B3, B4 CSVs;
- `claims_master_audit.json`, `run_log.txt`, `verify_log.txt`, `CODE_CHANGES_AFTER_LOCK.md`।
