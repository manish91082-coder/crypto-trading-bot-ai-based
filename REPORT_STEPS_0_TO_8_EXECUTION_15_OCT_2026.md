# Master Plan Steps 0–8: execution रिपोर्ट

**तारीख:** 15 अक्टूबर 2026 | **GitHub:** कुछ नहीं | **असली या testnet order:** कोई नहीं | **Testnet ETH position:** छुई नहीं

**हर step का तरीका:**
- पहले protocol लिखा और SHA256 से lock किया।
- फिर code चलाया।
- फिर एक अलग verifier ने सीधे-सादे code से नतीजे दोबारा गिने।
- Lock के बाद हुआ हर बदलाव `CODE_CHANGES_AFTER_LOCK.md` में दर्ज है।

## सार (एक नज़र में)
| Step | काम | नतीजा | Verifier |
|---|---|---|---|
| 0 | User के फैसले | 50% चुना ✓ । **Wake timer अब भी "Important only" है; इसे आपको बदलना है** | powercfg से पढ़ा |
| 1 | Forward logger 16B (4H R6 + 1h R24 + M_AI3-50% paper) | **तैयार और scheduled**; पहला run 16 अक्टूबर, 07:30 IST | V1–V5 PASS |
| 2 | असली खर्च (mainnet public order book) | **तैयार और scheduled** (05:28 / 05:32 IST); पहला अनुमान ~0.11% प्रति fill | analysis script raw से दोबारा गिनता है |
| 3 | Step 28: हलचल के हिसाब से size | **FAIL** | V1–V3 PASS |
| 4 | Phase 2: Swing AI (अच्छी rallies छाँटना) | **FAIL** (skill थोड़ी है, पर पैसे का फायदा पक्का नहीं) | V1–V5 PASS |
| 5 | Step 29: R24 + S/R + VAP + swing features | **SKILL_ADD_ONLY**: AUC में बहुत छोटा फायदा, पर portfolio खराब → अपनाया नहीं | V1–V4 PASS |
| 6 | Step 30: Breakout + तेज़ी का दौर | **FAIL** (2018–19 में घाटा) | V1–V3 PASS |
| 7 | Step 31: हफ्ते वाला दिमाग | **नहीं चलाया**: Step 15 में यह पहले ही परखा जा चुका है (नीचे वजह) | — |
| 8 | Dashboard (सिर्फ जानकारी) | **बना**: `dashboard/index.html` | verified functions से |

---

## Step 0: User के फैसले
- **पैसा:** 50% (M_AI3), आपकी हाँ के साथ।
- **Wake timer:** `powercfg` से पढ़ा तो "Allow wake timers" का AC value 2 है (= Important only)। System setting मैं नहीं बदलता, यह आपको करना है:
  - Control Panel → Power Options → Change plan settings → Change advanced power settings → Sleep → Allow wake timers → **Enable**।
  - वरना PC सोया रहा तो forward run देर से होगा और वह दिन गिनती से बाहर हो जाएगा।
- सारे नए tasks में "Wake the computer to run this task" चालू है, पर वह इसी setting पर निर्भर है।

## Step 1: Forward logger 16B
**क्या बना:**
- `src/execution/forward_multi_16b.py`, protocol `logs/forward_multi_16b/`।
- Step 16 logger को छुआ नहीं गया; उसकी files सिर्फ पढ़ी जाती हैं।

**रोज़ क्या होगा:**
- 4H R6 और 1h R24 के scores (20 coins, research वाला universe)।
- D1 (R5) scores।
- उस दिन के 1h candles।
- M_AI3-50% paper portfolio, research वाले simulators से, जिनमें कोई बदलाव नहीं।
- Hash-chained ledger।

**Paper की शुरुआत:** 2026-10-15। उस दिन का data lock के समय मौजूद नहीं था, इसलिए यह सच्चा forward test है।

**जाँच (सब PASS):**

| जाँच | नतीजा |
|---|---|
| V2: live code, September के 3 दिन | members = Step 19; R6 और R24 scores research से हूबहू (फर्क 5.6e-17) |
| V3: October के live models, 2018–19 पर | research के frozen दिमाग से हूबहू (51,552 और 2,05,873 rows, फर्क 5.6e-17) |
| V4: paper engine, 2021–26 पर | Step 27 से cent तक मेल: D1 $43,151.15 · H4 $49,365.87 · H1 $69,134.22 |
| V5: test run (as-of 14 अक्टूबर) | files, models और hash chain सब मेल खाए |

**Schedule:** Windows task `CryptoBot16B_ForwardMulti`, रोज़ 07:30 और 08:00 IST।

**Lock के बाद के 2 बदलाव (सिर्फ verifier में, logger code वही):**
1. V1 lock file की गलत पंक्ति पढ़ रहा था।
2. V5 में `r.asof` pandas का method निकला, column नहीं।

दोनों दर्ज हैं।

**90 दिन:** ~14 जनवरी 2027।

**Pass की शर्त (पहले से lock):**
- ≥ 90 दिन चले;
- ≤ 3 समझाए गए alarms;
- R6 या R24 में से कम से कम एक का forward AUC > 0.50।

## Step 2: असली खर्च
**Testnet क्यों नहीं:** testnet की order book नकली और पतली होती है, उससे असली spread या slippage नहीं नपता।

**इसकी जगह:** Binance mainnet की **public** order book, जो free है और जिसमें कोई order नहीं लगता।
- `src/execution/cost_snapshot_step2.py`, रोज़ 05:28 और 05:32 IST, यानी 00:00 UTC के rebalance के आसपास।
- Raw books gzip में SHA के साथ रखी जाती हैं।

**पहला round (off-schedule, सिर्फ 1, इसलिए अभी पक्का नहीं):**
- $333 के order पर spread और impact का median 0.010% है; p90 0.024% है।
- Fee 0.10% जोड़कर: **~0.11% प्रति fill** (p90 0.124%)।
- $10,000 के order पर: 0.125%। BNB fee (0.075%) के साथ: 0.085%।
- सबसे महँगे coins (FET, XLM, ADA) भी $333 पर ~0.13% से कम।

**मतलब:** research में माना गया **0.25% अब तक सावधानी वाला (conservative)** अनुमान दिखता है। पक्का फैसला 30 scheduled rounds (~15 दिन) के बाद होगा, जैसा protocol में तय है।

**सीमा:** snapshot असली fill नहीं है। 00:00 के आसपास book तेज़ी से बदल सकती है, इसलिए 23:58 और 00:02 के rounds की तुलना होगी।

## Step 3: Step 28, हलचल के हिसाब से position size: **FAIL**
**नियम:**
- पिछले 20 दिनों की हलचल (σ) देखी।
- लगाया पैसा = 0.5 × (σ का median) / σ, 0 से 1 के बीच।
- 0.10 का no-trade band, और खर्च शामिल।

**नतीजा:**

| | VOL (नियम) | बराबर औसत पैसा, fixed | Fixed 50% |
|---|---|---|---|
| 2021–26 Calmar | 0.658 | **0.721** | **0.704** |
| 2021–26 सबसे बड़ी गिरावट | 59.1% | 60.7% | 48.4% |
| 2018–19 अंतिम रकम | $4,492 | $5,730 | **$6,257** |
| 2018–19 सबसे बड़ी गिरावट | 61.6% | 59.8% | 54.8% |

- **मतलब:** शांत समय में ज़्यादा पैसा लगाने से औसत exposure 0.68 तक चला गया। उसी औसत को fixed रखने से बेहतर नतीजा आया। Crypto में हलचल के हिसाब से size बदलना यहाँ काम नहीं आया।
- 10 और 60 दिन वाले रूप भी देखे (सिर्फ report के लिए)। 2018–19 में सब fixed से बुरे निकले।
- **ईमानदार नोट:** "shuffled" तुलना कमज़ोर बनी। रोज़ बदलते weights पर खर्च बहुत लगा, इसलिए MAIN में G3 का pass मायने नहीं रखता। फैसला G1 के fail होने से ही FAIL है।
- **फैसला:** fixed 50% ही रहेगा।

## Step 4: Phase 2, Swing AI: **FAIL**
**सवाल:** 4h, 8h, 12h या 1D पर तेज़ी पक्की होते ही, क्या AI बता सकता है कि यह trade (अगली गिरावट पक्की होने तक, 0.25% खर्च के बाद) फायदे वाला होगा?

**Data:**
- 10 coins, 2017–2026, असल समय वाले signals (failed signals समेत): 7,425 trades।
- G0: 97% trades Phase 1 से मिले, factors में फर्क 0।

| | नतीजा |
|---|---|
| AI AUC (2019–26) | **0.536** (CI 0.510–0.561); नकली दिमाग 0.498 |
| AUC 2019–20 | 0.534, पर CI 0.472–0.595 (0.5 से ऊपर नहीं) → **G3 fail** |
| AUC 2021–26 | 0.537 (CI 0.508–0.565) |
| AI से चुनी rallies बनाम सारी, औसत खर्च के बाद | 3.11% बनाम 2.51%, फर्क +0.61%, CI −0.27% से +1.55% → **G4 fail** |
| उल्टे समय पर जाँच (2021–26 पर सीखा, 2017–20 पर परखा) | AUC 0.547 (CI 0.515–0.579), सिर्फ जानकारी |

**मतलब:**
- AI में **थोड़ी** skill है।
- पर अच्छी rallies छाँटने से पैसे का फायदा **पक्का नहीं** है।
- और 2019–20 में skill साबित नहीं हुई।
- इसलिए swing की जानकारी dashboard तक ही रहेगी।

**एक जानकारी (सिर्फ विवरण, portfolio नहीं):**
- 4h से 1D तक हर पक्की rally के पीछे चलने का औसत खर्च के बाद +2.5% प्रति trade रहा।
- पर 61% trades हारे, और trades आपस में overlap करते हैं।
- यह portfolio का नतीजा नहीं है।

**Lock के बाद 1 बदलाव:** दो columns (`htf_state_4h`, `htf_state_1h`) इन timeframes पर हमेशा खाली रहते हैं, और HGB उन पर crash होता था। इन्हें हटाया गया। कोई नतीजा उससे पहले नहीं बना था; बदलाव दर्ज है।

## Step 5: Step 29, R24 में S/R + VAP + swing features
Design Step 25 जैसा था: वही 10 लाख test rows, वही baseline।
6 नए features जुड़े: support/resistance की दूरी, 7 दिन का VAP, और 1h/4h/1D की ZigZag हालत।
G0 में rows हूबहू मेल खाए; features 0–0.4% ही खाली रहे।

| | R24 (पहले) | R24 + नए features |
|---|---|---|
| AUC 2021–26 | 0.5653 | 0.5661 (फर्क **+0.0008**, CI +0.00002 से +0.0015) |
| AUC 2018–19 (frozen) | 0.5463 | 0.5481 |
| $10k → (2021–26) | **$201,548** | $149,529 |
| सबसे बड़ी गिरावट | — | 79.8% |
| Calmar | **0.92** | 0.754 → **G3a fail** |
| 0.40% खर्च पर | — | $43,698 |

**मतलब:**
- S/R, volume और swing की जानकारी AI को सिर्फ **नाम-मात्र** मदद देती है।
- AUC का फायदा 0.0008 है, यानी 1000 फैसलों में करीब 1 का फर्क।
- और पैसे में नतीजा उल्टा खराब हुआ।
- यह ठीक Step 25 (15m/5m features) जैसा ही है: R24 पहले से ही ज़्यादातर जानकारी पकड़ लेता है।

**फैसला:** R24 जैसा है वैसा ही रहेगा। ये features सिर्फ dashboard में रहेंगे, जानकारी के लिए।

## Step 6: Step 30, Breakout + तेज़ी का दौर: **FAIL**
**नियम:**
- Daily का सबसे पास वाला न टूटा resistance, close से टूटे।
- और BTC अपने 200 दिन के औसत से ऊपर हो।
- तब अगली सुबह खरीदो और 10 दिन रखो (0.25% प्रति fill)।

| | 2021–26 (तेज़ी में) | 2018–19 (तेज़ी में) |
|---|---|---|
| Trades | 1,444 | 169 |
| औसत खर्च के बाद | **+4.10%** (CI +0.04 से +7.6) | **−4.53%** (CI −10.5 से −0.8) |
| उन्हीं दिनों सारे coins से ज़्यादा | +3.99% (CI +2.0 से +6.1) | +0.98% (CI −0.4 से +2.5) |
| साल-दर-साल | 2021 +11.8, 2023 +1.2, 2024 +5.6, **2025 −2.2**, 2026 +5.2 | 2019 −4.5 |

**मतलब:**
- 2021–26 में breakout ने उन्हीं coins को रखने से बेहतर किया।
- पर 2018–19 में तेज़ी के दौर में भी घाटा हुआ।
- 2021–26 वाला CI भी 0 के बहुत पास (+0.04%) है।
- इसलिए अकेला नियम भरोसे लायक नहीं → **FAIL**।

## Step 7: Step 31, हफ्ते वाला दिमाग: नहीं चलाया (मेरा फैसला, वजह के साथ)
- Step 15 में यह पहले ही परखा गया था:
  - R5 (5 दिन आगे, हर 5 दिन rebalance): AUC 0.545;
  - R10 (10 दिन): AUC 0.541।
- D1 sleeve **यही 5-दिन वाला दिमाग है**, यानी असल में हफ्ते वाला।
- हफ्ते के candles पर नया दिमाग बनाना उसी देखे हुए data पर एक और परीक्षा होती, जिससे संयोग से "जीत" दिखने का खतरा बढ़ता।
- Phase 1 में भी 1W की हालत का कोई असर नहीं मिला था।

## Step 8: Dashboard
**क्या बना:**
- `src/dashboard/build_dashboard.py` → `dashboard/index.html`।
- यह live data से बनता है और phone पर भी चलता है।

**हर coin के लिए 1W, 1D, 12h, 8h, 4h और 1h पर:**
- दिशा (ZigZag), और पिछले pivot से अब तक की चाल (ATR में);
- सबसे पास का न टूटा support और resistance (% दूरी);
- कीमत के पास का volume (VAP);
- ATR%, और "आम swing ~5 ATR"।

**साथ में:**
- AI ranks: R24, R6, D1।
- Paper portfolio।
- क्या साबित है और क्या नहीं।

**सिर्फ जानकारी, trading का नियम नहीं।** यह सिर्फ verified functions से बनता है।

**चलाने का तरीका:** `python src/dashboard/build_dashboard.py`। इसे रोज़ अपने-आप बनाने के लिए एक और scheduled task चाहिए; वह आपकी हाँ के बाद।

---

## अब कुल तस्वीर
1. **सिर्फ यही साबित है:** बड़े coins में relative चुनाव (D1, R6, R24)। इसका forward test **कल से शुरू** है, 50% पर, बिना order के।
2. **आज 4 नए विचार परखे गए:** हलचल के हिसाब से size, Swing AI, breakout, और S/R+volume features। **चारों अपनाने लायक नहीं निकले।** हर एक को "पास" करने की कोशिश नहीं की गई, सिर्फ पहले से तय शर्तों पर परखा गया।
3. **खर्च:** पहला असली नाप बताता है कि research का खर्च शायद ज़रूरत से ज़्यादा माना गया था। यह पक्का होगा ~15 दिन में।
4. **अगला फैसला ~14 जनवरी 2027 को,** forward log के आधार पर।

## आपके करने के काम
1. **Wake timers → Enable** (ऊपर तरीका लिखा है)।
2. 16 अक्टूबर की सुबह PC चालू या sleep में रहे, बंद नहीं।
