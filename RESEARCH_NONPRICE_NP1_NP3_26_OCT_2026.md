# NP1–NP3: भाव के अलावा जानकारी (funding, basis, open interest, positioning, order flow, order book) से BTC का अगला move: 26 अक्टूबर 2026

> **सार:**
> - **पहली बार ऐसी जानकारी मिली जो सच में अगला move बताती है।**
>   - 18 में से 14 (feature, समय) जोड़े discovery (2020-09 – 2023) **और** अलग validation (2024), दोनों में statistically मज़बूत निकले। उदाहरण: order-book का झुकाव, open interest का बदलाव, taker (आक्रामक) खरीद/बिक्री।
> - **पर अकेले किसी feature का असर fees से छोटा है।** हर single-feature trading नियम fees के बाद घाटे में रहा: S2 gate पर 14 में से 0 पास।
> - **NP2** (संकेतों का composite) और **NP3** (limit-order / maker execution) भी fees के बाद पास नहीं हुए। Holdout (2025-01 – 2026-09) अब भी **sealed** है।
>
> **Evidence:**
> - Protocol `logs/research_nonprice/NP1_PROTOCOL_PREREGISTERED.md`, SHA `9addc94b…`, कोई नतीजा देखने से पहले lock।
> - Code `src/research/nonprice_np1.py`।
> - Verifier `src/audits/verify_nonprice_np1.py`: **ALL PASS**।
>   - 2,000 random rows अलग code से दोबारा बनाए;
>   - सारे 54 + 28 t_IC values plain loops से दोबारा गिने;
>   - हर S2 trade दोबारा बनाया।

## 1. Data (download आपकी अनुमति से, आज)

- **Source:** Binance का official public bucket (data.binance.vision)।
- **Files:** **3,830** files। हर file Binance की अपनी SHA256 checksum से मिलाई गई; **0 fail** (`data/external/binance_public/DATA_ACQUISITION.md`)।

| Dataset | अवधि | किस काम का |
|---|---|---|
| Funding rate (8 घंटे) | 2020-01 – 2026-09 | Longs/shorts में से कौन भीड़ में है |
| Premium index (5m) | 2020-01 – 2026-09 | Futures बनाम spot का फ़र्क |
| Futures klines (5m, taker buy volume के साथ) | 2020-01 – 2026-09 | आक्रामक खरीद/बिक्री |
| Metrics (5m): open interest, top-trader और retail long/short ratio, taker ratio | 2020-09 – 2026-09 | Positioning |
| Order-book depth (±1% … ±5%, ~30 सेकंड) | 2023-01 – 2026-09 | Book का झुकाव |
| Liquidations | **उपलब्ध नहीं** (Binance इसे public नहीं देता) | — |

- **Quality:**
  - Funding हमारी पुरानी file से 7,395/7,395 मिला।
  - Futures 1h, पुरानी file से 59,160 में से 59,157 घंटों में मिला। जो 3 घंटे नहीं मिले, उनमें official file को सही माना गया।
  - बाकी विवरण `clean/QC_REPORT.md` में है।

## 2. Stage 1: क्या यह जानकारी अगला move बताती है? (trading नहीं, सिर्फ़ माप)

**Test:**
- हर feature और हर समय (1 घंटा, 4 घंटे, 24 घंटे) के लिए हर महीने का rank correlation (IC) निकाला गया।
- Discovery में |t| ≥ 3 चाहिए था, और validation (2024) में वही दिशा, |t| ≥ 2 के साथ।

**Validation में पक्के हुए 14 संकेत:**

| Feature | समय | Discovery t | 2024 t | अर्थ |
|---|---|---|---|---|
| पिछले 1 घंटे का भाव-बदलाव (control) | 1h | −7.9 | **−15.2** | 1 घंटे में तेज़ चाल अगले घंटे थोड़ी पलटती है |
| Spot taker खरीद का हिस्सा (1h) | 1h | −6.7 | −6.2 | आक्रामक खरीद के बाद हल्का पलटाव |
| Futures taker खरीद का हिस्सा (1h) | 1h | −5.0 | −5.0 | वही |
| Open interest बदलाव (24h) | 1h | −4.4 | −8.5 | OI बढ़ने के बाद भाव कमज़ोर |
| Open interest बदलाव (1h) | 1h | −4.0 | −4.9 | वही |
| Order-book झुकाव ±1% | 1h | **+8.6** | +4.5 | Bids भारी हों तो भाव ऊपर जाता है |
| Order-book झुकाव ±5% | 1h | +4.9 | +3.8 | वही |
| पिछले 24 घंटे का भाव-बदलाव (control) | 1h | −7.9 | −5.1 | पलटाव |
| Order-book झुकाव ±1% | 4h | +5.0 | +4.9 | |
| Order-book झुकाव ±5% | 4h | +3.5 | +4.4 | |
| Open interest बदलाव (24h) | 4h | −3.3 | −5.6 | |
| Spot taker खरीद (1h) | 4h | −3.7 | −2.4 | |
| पिछले 24 घंटे का बदलाव (control) | 4h | −6.2 | −3.0 | |
| Premium z-score | 24h | −4.1 | −2.3 | Futures महँगे हों तो अगला दिन कमज़ोर |

- **Discovery में बने पर 2024 में नहीं टिके** (14): funding level, basis (1h और 4h), top-trader बनाम retail, वगैरह।
- पूरी सूची `s1_D.csv` और `s1_V.csv` में है।

## 3. Stage 2: अकेले feature से trading

**नियम:** feature पिछले 90 दिनों के top 20% में हो तो उसकी दिशा में trade, bottom 20% में हो तो उल्टी दिशा में। 1h, 4h या 24h hold, fees 0.092%।

| Feature / समय | 2024 trades | Gross / trade | Net / trade | Positive महीने (12 में) |
|---|---|---|---|---|
| 1h वाले 8 configs | ~3,500 हर एक | −0.006 … +0.027% | −0.065 … −0.098% | **0** |
| OI बदलाव 24h / 4h | 872 | +0.065% | −0.027% | 4 |
| Order-book ±5% / 4h | 937 | +0.067% | −0.025% | 3 |
| Premium z / 24h | 154 | +0.231% | +0.139% (t 0.6) | 7 |

**फ़ैसला:** 14 में से 0 पास (शर्तें: net > 0, t ≥ 2, और 12 में से ≥ 7 महीने positive)।

**वजह, गणित में:**
- संकेत की ताकत IC लगभग 0.04–0.08 है।
- 1 घंटे में भाव का आम फैलाव (σ) 0.67% और 4 घंटे में 1.34% है।
- इसलिए एक trade की अपेक्षित कमाई लगभग IC × σ ≈ 0.03–0.10% बनती है।
- Fees 0.092% हैं, इसलिए **अकेला संकेत fees लगभग खा जाता है।**

## 4. NP2: कई संकेत मिलाकर (composite)

**Lock और जाँच:**
- Protocol `NP2_PROTOCOL_PREREGISTERED.md`, SHA `b6d8d754…`।
- Verifier `verify_nonprice_np2.py`: ALL PASS।
  - हर percentile, score और ridge β अपने अलग code से दोबारा बनाया गया।
  - सभी 24 configs के हर trade का भी मिलान हुआ।

**क्या test हुआ:**
- **Configs:** 2 समय (1h, 4h) × 2 sets (order book के साथ और बिना) × (बराबर-weight score के 3 thresholds + ridge model के 3 thresholds) = 24।
- **Ridge:** सिर्फ़ discovery data पर fit हुआ।
- **Selection की शर्त:** discovery में net > 0 और t ≥ 2, और 2024 में net > 0।

**नतीजा:**
- **24 में से 0 configs इस शर्त पर पास हुए।**
- 1h पर: in-sample (discovery) में भी gross सिर्फ़ −0.02 … +0.03% प्रति trade रहा।
- 4h पर: सबसे अच्छा gross 0.06–0.08% रहा, जो fees (0.092%) से कम है।
- Holdout **sealed** रहा।

## 5. NP3: limit orders (maker) से fees घटाकर

**Lock और जाँच:**
- Protocol `NP3_PROTOCOL_PREREGISTERED.md`, SHA `8e4488b4…`।
- Verifier `verify_nonprice_np3.py`: ALL PASS।
  - 173,970 trades raw 5m bars से अपने code से दोबारा बनाए गए।

**Execution के नियम:**
- **Entry:** limit order, जो तभी भरा माना गया जब 15 मिनट के अंदर भाव limit के **पार** गया। सिर्फ़ छूना काफ़ी नहीं।
- **Exit, दो तरह:**
  - taker;
  - limit order, न भरे तो 15 मिनट बाद taker।
- **Fees `fees.json` से:** maker 0.018% प्रति side, taker 0.046% प्रति side।

**नतीजा:**
- 48 configs में से **0** configs selection शर्त पर पास हुए।
- **Fill rate:** ~97–99%।
- **सबसे अच्छा:** 4h ridge (order book के बिना) + maker exit।
  - Discovery में +0.019% प्रति trade (t 0.33), 2024 में +0.025%।
  - यानी लगभग शून्य, और statistically कोई सबूत नहीं।
- Holdout अब भी **sealed** है।

## 6. पूरा निष्कर्ष (data जो कहता है)

1. **भाव के अलावा जानकारी असली है।**
   - Order-book का झुकाव, OI का बदलाव और taker flow, तीनों discovery और 2024 दोनों में statistically मज़बूत निकले।
   - यह पहले वाले "कुछ नहीं मिला" से अलग और नई बात है।
2. **पर उसका आकार fees से छोटा है।**
   - 1 घंटे पर संकेत की ताकत 0.01–0.03% प्रति trade है, 4 घंटे पर 0.05–0.08%।
   - Taker round trip 0.092% है, maker + taker लगभग 0.064%, maker + maker 0.036%।
   - Maker में भी net ≈ 0 रहा।
3. **इसलिए public data पर, हमारी fee level पर, BTC की छोटी-अवधि trading में अभी कोई साबित edge नहीं है।**
   - यह बात price-only (990 + 100 + v1) और non-price (NP1–NP3), दोनों पर लागू होती है।
4. **Holdout (2025-01 – 2026-09) अब भी sealed है।** किसी भी नए, बेहतर विचार की अंतिम जाँच के लिए यह साफ़ data बचा है।

## 7. अब लक्ष्य के लिए क्या बचा है (ईमानदारी से)

| रास्ता | स्थिति |
|---|---|
| ECO (trend, लंबी अवधि) demo पर | चल रहा है। TC gate ~09 नवंबर, Sleeve A forward, Paper Spot S1 |
| Funding carry (spot long + perp short) | पहले जाँचा: ~4.6% सालाना, DD ~1%, 2025–26 में घटा (24 अक्टूबर की report) |
| Daily अवधि पर non-price | Premium z-score (24h) को holdout पर जाँचा गया (NP4, §8): **फ़ेल** |
| Batch 1 (189 indicator configs) | अभी भी चल रहा है। खत्म होने पर verify होकर report आएगी |

## 8. NP4: 24 घंटे वाला premium संकेत, sealed holdout पर एक बार (आपके कहने पर, 26 अक्टूबर)

**Lock और जाँच:**
- Protocol `NP4_PROTOCOL_PREREGISTERED.md`, SHA `9ef4dd3e…`, holdout खोलने से पहले lock।
- Verifier `verify_nonprice_np4.py`: ALL PASS।
  - हर trade plain loops से दोबारा बनाया गया।
  - हर दिन (638 दिन), महीना, साल और gate का भी मिलान हुआ।

**नियम:**
- **P1:** premium z-score पिछले 90 दिनों के top 20% में हो, तो short; bottom 20% में हो, तो long। 24 घंटे hold।
- **P2:** सिर्फ़ long वाला हिस्सा।
  - इसे 2020–24 में long side ज़्यादा मज़बूत दिखने के बाद चुना गया था, इसलिए यह post-hoc है।
  - Gate में इसकी गिनती के लिए Bonferroni (z = 2.24) लगाया गया।

**पहले से दर्ज power की चेतावनी:** अगर असली कमाई +0.3–0.5% प्रति trade भी होती, तो भी 21 महीनों में P2 के gate पास करने की संभावना कम थी।

| | Trades | जीत % | Net / trade | Positive महीने | 2025 | 2026 (जन–सित) | फ़ैसला |
|---|---|---|---|---|---|---|---|
| P1 (long + short) | 271 | 45.8% | **−0.123%** | 9/21 | −35.5% | +2.3% | **फ़ेल** |
| P2 (सिर्फ़ long) | 127 | 44.1% | **−0.063%** | 9/21 | −17.9% | +9.8% | **फ़ेल** |
| P2, spot fees पर (सिर्फ़ जानकारी) | 127 | 40.9% | −0.141% | 9/21 | −23.5% | +5.5% | — |

**पढ़ने का तरीका (protocol में पहले से तय):** net negative है, इसलिए फ़ैसला यह है कि **"2020–24 वाला नतीजा 2025–26 में नहीं टिका।"**
- **कुछ बड़े महीने:**
  - 2026-02: P1 +28.7% (crash के बाद की तेज़ी);
  - 2026-04: P1 −25.0%।
- यानी नतीजा कुछ बड़े महीनों पर टिका था, और लगातार नहीं।
- **Holdout अब इस संकेत पर खर्च हो चुका है।** अब इसे दोबारा इसी data पर नहीं जाँचा जा सकता।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
