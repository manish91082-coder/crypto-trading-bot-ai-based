# Steps 1–6 की report: N1 portfolio, N2 regime, N3 execution, Step 4 risk नियम, N5 AI, Step 6 forward (20 अक्टूबर 2026)

**तरीका:**
- हर step का protocol कोई नतीजा देखने से पहले लिखा गया और SHA से lock हुआ।
- Trial registry में T15–T18 दर्ज हैं: 20 में से 18 इस्तेमाल हुए, 2 बचे हैं।
- हर step का अपना independent verifier है, जिसका code अलग है।
- Lock के बाद का हर बदलाव `CODE_CHANGES_AFTER_LOCK.md` या `CODE_NOTES.md` में दर्ज है।
- Simulation सिर्फ़ historical data पर हुआ: कोई order नहीं गया, पैसा नहीं लगा, cloud का 1D system और laptop production छुए नहीं गए।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## 0. सीधा नतीजा

| Step | Trial | नतीजा | एक लाइन में |
|---|---|---|---|
| 1. N1 portfolio (4 sleeves, बिना AI) | T15 | ✅ **PASS** (7/7 gates, verifier 5/5) | Random entry, cost, DSR, PBO और 2018–19 तक में टिका। FINAL = **बिना stop** वाला config |
| 2. N2 regime (rule + jump model) | T16 | ❌ **FAIL** (verifier 5/5) | दोनों regime नियमों ने dev Calmar घटाया। गिरावट वाले दौर (P3, 2018–19) में मदद की, पर gate dev/P1/P2 पर था |
| 3. N3 execution | T17 | ✅ **PASS, provisional** (verifier 4/4) | **X2 spot/perp routing** ने Calmar 3.26 → 3.65 किया। Maker entry (X1) gate पर fail |
| 4. Risk नियम (anti-liquidation, heat cap) | — | ✅ Code और tests (6/6) | अलग module है, किसी चलते engine से **नहीं** जुड़ा |
| 5. N5 AI meta-label | T18 | ❌ **FAIL** (verifier 4/4) | AI में असली skill है (AUC 0.54 > shuffled), पर आधे trades छोड़ने से portfolio Calmar 3.65 → 2.2–2.5 गिरा |
| 6. Forward demo | — | ⏳ **शुरू नहीं हुआ** | इसके लिए आपकी मंज़ूरी और 90 दिन का असली forward data चाहिए (भाग 7) |

**अभी का सबसे अच्छा candidate:** N1 K1 (बिना stop) + X2 (spot/perp routing) + X3 (funding guard)। AI नहीं, regime overlay नहीं।
- Dev (2020-02 … 2025-09) पर Calmar **3.65**, CAGR ~100%, MTM drawdown 27%।
- **पर ये in-sample नंबर हैं**: sleeves इसी data को देखकर चुने गए थे।
- P3 (अक्टूबर 2025 – सितंबर 2026) में यही system **negative** रहा (Calmar −0.39)।

असली सबूत सिर्फ़ forward data देगा। ये नंबर भविष्य के मुनाफ़े का वादा नहीं हैं।

---

## 1. N1: चार sleeves वाला portfolio (Step 1)

**Protocol `20ffc364…`, verifier `verify_n1.py` 5/5 PASS.**

### क्या परखा
| Sleeve | क्या | Universe | Budget |
|---|---|---|---|
| A | Trend-long: TSMOM, EMAX, MACD, DONCH × 4h/8h/12h/1D = 16 sub-signals | 10 बड़े coins | 0.8× |
| B | RSI14 oversold-long × 8h/12h/1D | 10 बड़े coins | 0.4× |
| C | Trend-short (crash hedge) | ~120 liquid coins | 0.4× |
| D | 1D XS momentum (Gemini का screener = हमारा D4) | ~120 liquid coins | 0.4× |

- **Costs:** taker 0.054% प्रति side और असली funding।
- **Capital:** 10,000 USDT, मासिक sizing।
- **Drawdown:** हर घंटे mark-to-market।

### सात configs, और चुनाव का पहले से तय नियम
Variant तभी चुना जाता जब वह dev, P1 और P2, तीनों में K0 से बेहतर हो।

| Config | Dev CAGR | Dev MTM-DD | Dev Calmar | P1 | P2 | P3 (सिर्फ़ report) | चुना? |
|---|---|---|---|---|---|---|---|
| K0 (3-ATR stop) | 80% | 29% | 2.74 | 3.47 | 1.59 | −0.35 | base |
| **K1 बिना stop** | 93% | 29% | **3.26** | 4.00 | 2.87 | −0.39 | ✅ |
| K2 heat cap 6% (Gemini) | 56% | 22% | 2.50 | 3.22 | 1.38 | −0.14 | ❌ |
| K3 correlation dampener (Gemini) | 79% | 29% | 2.73 | 3.46 | 1.55 | −0.29 | ❌ |
| K4 बिना D | 71% | 33% | 2.18 | 2.68 | 2.20 | −0.75 | ❌ |
| K5 बिना C | 72% | 44% | 1.63 | 2.05 | 1.14 | −0.50 | ❌ |
| K6 inverse-vol sizing | 81% | 33% | 2.48 | 3.16 | 1.62 | −0.37 | ❌ |

**सबक:**
- Stops trend की बड़ी कमाई काटते हैं। यह TFX-S के "tail-driven" नतीजे से मेल खाता है।
- Gemini के heat cap और correlation dampener ने Calmar घटाया।
- C (short hedge) और D (XS momentum) अकेले कमज़ोर हैं, पर इन्हें हटाने से portfolio बिगड़ता है:
  - Sleeve C अकेला लगभग 0% कमाता है, पर A के साथ उसका correlation **−0.57** है।
  - C के बिना Calmar 3.26 → 1.63, और drawdown 29% → 44%।

### Gates (FINAL = K1)
| Gate | मान | नतीजा |
|---|---|---|
| G1 random entry (100 portfolios) | Calmar 3.26 > p95 1.95 | ✅ |
| G2 cost 1.5× / 2× / stop slip | मासिक औसत +6.3% / +6.1% / +6.5% | ✅ |
| G3 P1, P2 | 4.00, 2.87 | ✅ |
| G4 month bootstrap CI | +3.3% … +10.3% प्रति माह | ✅ |
| G5 DSR (N = 26 trials) | 1.00 | ✅ |
| G6 PBO (12,870 combinations) | 0.13 | ✅ |
| G7 2018–19 (पहले कभी न देखा data, spot) | Calmar 0.40, CAGR +10.5% (BTC buy-and-hold −11%) | ✅ |

### साल-दर-साल (FINAL, report-only, एक लगातार run)
| साल | Return | MTM-DD | BTC |
|---|---|---|---|
| 2020 (फ़रवरी से) | +135% | 23% | +209% |
| 2021 | **+495%** | 29% | +60% |
| 2022 | −7% | 22% | −64% |
| 2023 | +52% | 16% | +156% |
| 2024 | +84% | 19% | +121% |
| 2025 | +14% | 16% | −6% |
| 2026 (सितंबर तक) | **−10%** | 29% | −5% |

### N1 की कमज़ोरियाँ (ईमानदारी से)
1. **In-sample है।** Sleeves इसी 2020–2026 data को देखकर (TFX, TFX-S, DISC) चुने गए थे। DSR, PBO और random control इसका हिसाब रखते हैं, फिर भी dev के नंबर ज़्यादा अच्छे दिखते हैं। सिर्फ़ 2018–19 (Calmar 0.40) और आगे का forward data साफ़ सबूत हैं।
2. **एक साल पर बहुत निर्भरता।** Dev की कमाई का बड़ा हिस्सा अकेले 2021 (+495%) से आया। Trend system में ऐसा होता है, पर अगला "2021" कब आएगा, पता नहीं।
3. **हाल का दौर कमज़ोर है:** P3 (अक्टूबर 2025 – सितंबर 2026) negative, 2026 अब तक −10%।
4. **बिना stop का मतलब:** एक position कीमत बढ़ने के साथ बड़ी हो जाती है।
   - Post-hoc exposure (`N1_exposure_POSTHOC.csv`): gross का औसत 0.81×, p95 1.12×, max 1.41×।
   - एक coin का net हिस्सा 39% equity तक गया।
   - Live में इसके लिए Step 4 के नियम और per-coin cap ज़रूरी होंगे।
5. **1D system से correlation:** मासिक correlation 0.63 (56 महीने), यानी diversification कम है।
6. **Sizing table** (information): budget 0.5× → CAGR 46%, DD 23%; 1× → 93% / 29%; 1.5× → 144% / 34%। Risk level आपका फ़ैसला है।

---

## 2. N2: Regime overlay (Step 2) ❌ FAIL

**Protocol `d019c201…`, N1 का नतीजा आने से पहले lock हुआ। Verifier 5/5 PASS.**

| | Dev Calmar | Dev DD | P1 | P2 | P3 (report) | 2018–19 |
|---|---|---|---|---|---|---|
| Base (N1 FINAL) | 3.26 | 29% | 4.00 | 2.87 | −0.39 | 0.40 |
| R1 नियम (BTC EMA20/50 + vol) | 2.82 | 27% | 3.92 | 1.75 | **+0.07** | **0.88** |
| R2 jump model (λ = 50) | 1.78 | 37% | 1.92 | 2.31 | −0.43 | **0.91** |

- **Gate:** dev, P1 और P2 पर Calmar ऊपर, dev DD नीचे, और random-regime p95 से ऊपर। दोनों fail।
- **R1 गिरावट वाले दौर में मदद करता है:** P3 −0.39 → +0.07, 2018–19 0.40 → 0.88। पर तेज़ी के साल में कमाई काटता है (2021: +495% → +395%)।
- **फ़ैसला:** regime overlay नहीं अपनाया जाएगा। FAIL को बाद में "P3 में अच्छा था" कहकर PASS नहीं बनाया जाएगा।

---

## 3. N3: Execution (Step 3) ✅ PASS, provisional

**Protocol `2776e1df…`, verifier 4/4 PASS.**

| Variant | Dev Calmar | P1 | P2 | Gate |
|---|---|---|---|---|
| Base | 3.26 | 4.00 | 2.87 | — |
| X1 maker entry (fill सिर्फ़ trade-through पर; GEMV का सबक) | 3.28 | 4.03 | 2.90 | ❌ Q3 |
| X1s stress (≥ 0.05% trade-through) | 3.15 | 3.90 | 2.62 | ❌ |
| **X2 spot/perp routing** (Gemini #2) | **3.65** | **4.49** | **3.21** | ✅ |
| X3 funding guard (Gemini #3) | 3.26 | 4.00 | 2.87 | ✅ (असर लगभग शून्य) |
| **X2 + X3** | **3.65** | **4.49** | **3.21** | ✅ adopted |

**Maker entry:**
- Fill rate 96.5%। Stress (0.05% पार) में 92.7%।
- Adverse selection साफ़ दिखा:
  - fill हुए trades का औसत net +0.9%;
  - न fill हुए trades का +2.0%, क्योंकि जो trades भाग गए वे सबसे अच्छे थे।
- Implementation shortfall का CI 0 पार करता है, इसलिए gate fail। Taker entry ही रहेगी।

**X2 spot routing:**
- PIT trailing-7-day funding × expected hold > 0.062% होने पर long trade spot पर लिया जाता है।
- 39% long trades spot पर गए। Funding बचत से Calmar बढ़ा।

**X3 के बारे में ईमानदारी:**
- 3,311 triggers सब ऐसे थे जहाँ funding record entry से 1–43 ms बाद का था, यानी bar open वाली funding ही।
- N1 ने इसे trade पर चार्ज किया था (सावधानी)। X3 बस उसे हटाता है।
- असली बचत छोटी है।

**"Provisional" क्यों:** fill model historical 5m bars पर है। असली fills सिर्फ़ demo forward पर पक्के होंगे।

---

## 4. Step 4: Risk नियम

- **Module:** `src/execution/risk_rules_l4.py`, tests `src/audits/test_risk_rules_l4.py` (6/6 PASS)।
- **Anti-liquidation:** stop दूरी ≤ 0.4 × liquidation दूरी, और किसी stop के लिए अधिकतम सुरक्षित leverage।
- **Heat cap 6%:** N1 K2 के weights को 1e-16 तक दोहराता है।
- **Combined pre-trade check:** `check_order`।

**किसी चलते engine से नहीं जोड़ा गया।** Cloud पर चल रहा F6 demo बदला नहीं। उसे बदलने के लिए आपकी अलग मंज़ूरी चाहिए।

**F6 पर जानकारी:** F6 का short stop +50% पर है (1×, liquidation लगभग +99.5%)। यह Gemini के 0.4× नियम पर fail होता है (stop 0.5 > 0.4 × 0.995), पर stop फिर भी liquidation से लगभग 50% पहले लगता है। अभी कोई ख़तरा नहीं, बस जानकारी।

**N1 FINAL में stop नहीं है, फिर भी live में ज़रूरी:**
- 1× leverage;
- isolated margin;
- per-coin cap;
- एक दूर का "catastrophe stop", जो सिर्फ़ liquidation से बचाए।

Catastrophe stop N1 में परखा नहीं गया है। इसे जोड़ना नया trial होगा (2 बचे हैं)।

---

## 5. N5: AI meta-label (Step 5) ❌ FAIL

**Protocol `da95e8a1…`, verifier 4/4 PASS:**
- PIT replay 2.8e-11 तक मेल;
- leak canary AUC 1.000, यानी leak होता तो पकड़ा जाता।

| Model | AUC (2021–25) | Shuffled p95 | Taken − all (net/trade) | Dev Calmar | Base | Random-skip p95 | P1 / base | P2 / base |
|---|---|---|---|---|---|---|---|---|
| L logistic | 0.536 | 0.523 | +0.42% ✅ | 2.18 | 3.65 | 2.46 | 2.05 / 3.68 | 2.27 / 3.21 |
| H HGB | 0.545 | 0.529 | +0.36% ✅ | 2.46 | 3.65 | 2.91 | 2.25 / 3.68 | 3.08 / 3.21 |
| E ensemble | 0.547 | 0.528 | +0.54% ✅ | 2.45 | 3.65 | 2.71 | 2.62 / 3.68 | 2.92 / 3.21 |

**पहली बार AI में असली skill दिखी:**
- AUC shuffled p95 से ऊपर, CI 0.5 से ऊपर।
- Big winners को नहीं छोड़ता (tail share 56–59% > take rate)।
- चुने गए trades औसतन बेहतर।

**फिर भी portfolio बिगड़ता है:**
- आधे trades हटाने से trend sleeves का exposure आधा हो जाता है, और diversification घटता है।
- Calmar random skip के p95 से भी नीचे रहा।

**सबसे अहम features:** BTC का 30-दिन return, BTC volatility, BTC 7-दिन और 1-दिन return। यानी AI असल में market regime पढ़ रहा है, coin-specific कुछ नहीं। Gemini का "whale ratio" ऊपर के features में नहीं आया।

**P3 में AI फ़िल्टर बेहतर रहा** (0.41–0.66 बनाम base −0.39), पर यह gate नहीं था और P3 पहले देखा हुआ data है।

**फ़ैसला:** AI filter नहीं अपनाया जाएगा। सीखने की बात: AI को "skip" की जगह **size** (0.5×–1.5×) तय करना चाहिए, ताकि exposure न घटे। यह नया trial होगा।

---

## 6. Gemini वाले items का अंतिम हिसाब

| Item | कहाँ परखा | नतीजा |
|---|---|---|
| Relative-strength screener | N1 sleeve D | ✅ portfolio में रखा (हटाने पर Calmar 3.26 → 2.18) |
| Spot/perp crossover | N3 X2 | ✅ अपनाया (+0.39 Calmar) |
| Funding guard | N3 X3 | ✅ अपनाया (असर नगण्य) |
| Heat cap 6% | N1 K2 | ❌ Calmar घटा; risk module में tool के रूप में तैयार है |
| Correlation dampener | N1 K3 | ❌ |
| Anti-liquidation | Step 4 | ✅ नियम और tests तैयार, wiring आपकी मंज़ूरी पर |
| Whale ratio | N5 feature | ❌ महत्वपूर्ण नहीं निकला |
| Ensemble | N5 E | ❌ portfolio gate fail |

---

## 7. Step 6: Forward demo (अभी शुरू नहीं हुआ)

- N1 + X2 + X3 को forward पर परखने के लिए एक paper recorder चाहिए: रोज़/हर 4h signal बनाना, बिना order के ledger लिखना, और बाद में demo orders।
- यह नया code है जो VM पर cron से चलेगा। **आपकी मंज़ूरी के बिना शुरू नहीं करूँगा।**
- Real money का फ़ैसला सिर्फ़ आपका होगा, ≥ 90 forward दिन के बाद।

**पहले से चल रही जाँचें:**
- रोज़ cloud verifier;
- ~30 अक्टूबर को S7 recost;
- ~12 जनवरी 2027 को day-90 evaluation।

---

## 8. गलतियाँ जो रास्ते में मिलीं और कैसे ठीक हुईं

| कहाँ | क्या हुआ | क्या किया |
|---|---|---|
| N1 run 1 | K4 पर crash (D के बिना `w` column नहीं) | Fix, पूरा rerun; K0–K3 हूबहू मेल |
| N1 run 2 | G7 पर crash (concat से dtype) | Fix, G7 का अलग run (नंबर नहीं देखे), फिर पूरा rerun; config/random lines हूबहू मेल |
| N1 report-only | Exposure NaN | Post-hoc script (`posthoc_n1_exposure.py`); gate पर असर नहीं |
| N3 run 1 | Protocol में X3 का simulation ज़रूरी था, code में छूट गया | जोड़ा, पूरा rerun; बाकी variants हूबहू मेल |
| N3 verifier | Windows case-insensitive glob ने चलती stdout file को hash किया | Stdout को SHA check से बाहर रखा; N5 में पहले ही ठीक |
| N5 smoke test | Feature में inf (शून्य से भाग) | inf = missing, official run से पहले दर्ज |
| Verifiers (test copies पर) | Float index, छोटा history, NaN comparison | ठीक किए। NaN अब mismatch गिना जाता है, चुपचाप pass नहीं |

सब `CODE_CHANGES_AFTER_LOCK.md` / `CODE_NOTES.md` में दर्ज हैं। Crash वाले logs सबूत के तौर पर रखे गए हैं।

---

## 9. Verification सारांश

| Step | Verifier | नतीजा |
|---|---|---|
| N1 | `verify_n1.py`: 300 trades raw 5m से, अपनी equity accounting (3.5e-13), D के 50 rebalances, PBO/DSR, SHAs | 5/5 PASS |
| N2 | `verify_n2.py`: R1/m_vol (1e-16), jump-model DP और 100 states, weights × g, gates | 5/5 PASS |
| N3 | `verify_n3.py`: 300 maker fills, 200 routing decisions, shortfall CI | 4/4 PASS |
| N5 | `verify_n5.py`: PIT replay, leak canary, AUC/gates | 4/4 PASS |
| Risk | `test_risk_rules_l4.py` | 6/6 PASS |
| Registry | `verify_trial_registry.py`: 18 trials, सबके result | 5/5 PASS |

---

## 10. आगे: आपके फ़ैसले

1. **Forward paper recorder** (N1 K1 + X2 + X3, बिना order): VM पर बनाऊँ? हाँ कहें तो पहले उसका protocol दिखाऊँगा।
2. **बचे 2 trials किस पर लगाएँ?** मेरा सुझाव:
   - (a) AI को "skip" की जगह **sizing** के लिए;
   - (b) live सुरक्षा के लिए दूर का **catastrophe stop** + per-coin cap।
3. **Risk module को F6 में जोड़ना:** आपकी अलग मंज़ूरी चाहिए।

**सीधी बात:** historical data पर यह अब तक का सबसे मज़बूत नतीजा है। पर हाल का साल negative है और कमाई का बड़ा हिस्सा एक ही साल (2021) से आया है। इसलिए forward data से पहले real money नहीं।

---

# भाग 2 (21 अक्टूबर 2026): आपके कहने पर मैंने तीनों फ़ैसले लिए और लागू किए

## 11. फ़ैसले और कारण
1. **बचे 2 trials:**
   - **T19:** live सुरक्षा, यानी catastrophe stop और per-coin cap।
   - **T20:** AI को trades छोड़ने की जगह position का size तय करने देना।

   इसके बाद **20 में से 20 trials इस्तेमाल हो चुके हैं।** नई research के लिए अब नया budget तय करना होगा।
2. **Risk module F6 में नहीं जोड़ा।** F6 के सारे short 1× पर हैं और उनका stop +50% पर है। 0.4× वाला नियम हर F6 short को रोक देता, जबकि 1× पर liquidation का ख़तरा है ही नहीं। Module नए paper recorder में cap के रूप में लगाया गया है।
3. **Forward paper recorder बनाकर VM पर चालू किया।** इसमें कोई order नहीं जाता।

## 12. T19 और T20 (protocol `e6962b76…`, verifier `verify_n6.py` 5/5 PASS)

| Variant | Dev Calmar | Dev DD | P1 | P2 | P3 | फ़ैसला |
|---|---|---|---|---|---|---|
| Base (N1 + X2 + X3) | 3.65 | 27.4% | 4.49 | 3.21 | −0.39 | — |
| S1: 35% catastrophe stop | 2.90 | 32.3% | 3.53 | 3.07 | −0.50 | ❌ |
| **S2: per-coin entry cap 20%** | **4.16** | **23.7%** | **5.10** | 3.22 | −0.39 | ✅ **अपनाया** |
| S3: दोनों | 3.25 | 28.5% | 3.93 | 3.08 | −0.50 | ❌ |
| T20: AI sizing (S2 के ऊपर) | 3.65 | 29.8% | 3.87 | 4.17 | −0.25 | ❌ FAIL (dev < base 4.16, random p95 4.32 से नीचे) |

**Cap का असर:**
- सिर्फ़ 808 entries (0.7%) छोटी हुईं या छोड़ी गईं, फिर भी 2021 वाला drawdown 27.4% से घटकर 23.7% रह गया।
- **कमी:** cap सिर्फ़ entry पर लगता है। कीमत बढ़ने पर एक coin का हिस्सा फिर भी 37.6% तक गया। Live पैसे से पहले position को समय-समय पर trim करने का नियम चाहिए होगा। उसे बिना trial के जोड़ना research नहीं, सिर्फ़ engineering होगा।

**35% stop:** सिर्फ़ 0.7% trades पर लगा, फिर भी नतीजा बिगड़ा। गिरे हुए alts बाद में लौट आए।

**AI sizing:** P2 और P3 में मदद की, पर dev के gate पर fail हुआ।

**अंतिम config:** N1 K1 + X2 + cap 20%। AI और regime overlay इसमें नहीं हैं।

## 13. Step 6: forward paper recorder (चालू)
- **Protocol** `14bc8054…`। Engine `src/execution/paper_n1_portfolio.py` (VM पर SHA `fa7de425…`)। Config `deploy/paper_n1_config.json` (`a8765f81…`) research files से अपने-आप बनता है, हाथ से कोई नंबर नहीं डाला गया।
- **Replay gate:** यही engine 2025-03 से 2025-09 के पुराने data पर, हर 4 घंटे, 1,284 cycles चलाया गया, और नतीजा backtest से मिलाया गया।
  - Entries 99.3% / 99.9% मिले, कीमतें 100%, exit समय 100%, D legs 40/40।
  - पहले run में replay harness का एक bug निकला (SHIB/BONK के नाम), जिससे D 9/40 पर fail हुआ था। उसे ठीक किया गया; सबूत रखा गया है।
- **VM पर चालू:**
  - हर 4h close के 11 मिनट बाद (IST 01:41, 05:41, 09:41, 13:41, 17:41, 21:41) recorder चलता है।
  - रोज़ 07:20 IST पर ledger की जाँच होती है।
  - पहला cycle 2026-10-21 04:00 UTC का है: 54 positions, verifier 5/5।
  - Crontab में सिर्फ़ 3 lines जुड़ीं (19 jobs)। 1D system की कोई चीज़ नहीं बदली।
- **आगे:**
  - रोज़ की cloud जाँच में यह ledger भी देखा जाएगा।
  - **Day-90 मूल्यांकन लगभग 19 जनवरी 2027 को होगा।** Forward नतीजे को backtest के 90-दिन वाले band और BTC से मिलाया जाएगा।
  - Real money का फ़ैसला सिर्फ़ आपका होगा, उसके बाद।

## 14. अब क्या बचा है
- **अपने-आप चल रहा है:** paper recorder, रोज़ की जाँच, ~30 अक्टूबर का S7 recost, और 90 दिन के बाद मूल्यांकन।
- **Research:** trial budget ख़त्म हो गया है। नई research (जैसे position trim, AI sizing का दूसरा रूप) के लिए आपकी मंज़ूरी से नया budget चाहिए होगा।
- **आपके हाथ में:** rclone token rotate करना, असली account पर commissionRate देखना, और Drive files। ये पहले से लंबित हैं।
