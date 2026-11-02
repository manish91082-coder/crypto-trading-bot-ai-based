# Methods bench, Batch 2: volatility (A3) और volume / order flow (A4), BTC 2020 – 2026-09 (27 अक्टूबर 2026)

> **सार:**
> - 324 signal configs × 3 exits = **972 primary configs** test हुए, futures fees के साथ।
> - **एक भी config "edge" के सारे gates पास नहीं कर सका (0/972)।**
> - सिर्फ़ 1 config (Yang-Zhang low-vol follow, 4h, X3) का holdout CI 0 से ऊपर गया (G1)। वह भी multiple-testing वाली कसौटी (DSR 0.09, ज़रूरत > 0.95) में fail हुआ।
> - DSR में 972 में से 0 पास हुए। सबसे ऊँचा DSR 0.35 था।
>
> **Evidence:**
> - Protocol `logs/research_methods_bench/BATCH2_PROTOCOL_PREREGISTERED.md` (SHA `bfd73f29…`), run से पहले lock।
> - Master protocol `0ee7aff8…` और Amendment 1 `626f670a…` बिना बदलाव लागू।
> - Code: `methods_bench_b2.py` `cf6fd178…`, bench `46b16cd6…` (बदला नहीं)।
> - Lookahead test: 20 cutoffs पर 324 में से 0 configs में फ़र्क।
> - Run से पहले का एक सुधार दर्ज है: GARCH fit के लिए mean-NLL objective (`BATCH2_CODE_CHANGES.md`)।
> - Independent verifier `src/audits/verify_methods_batch2.py`: **8/8 PASS** (`batch2_verify_output.txt`)। इसमें:
>   - 300 random signals अपने code से दोबारा बने, 0 mismatch;
>   - X3 trades loop से replay किए;
>   - daily → monthly → yearly का मिलान, हर दिन मौजूद;
>   - ranking दोबारा गिनी;
>   - random control, stress और delay जाँचे;
>   - 5 नए cutoffs पर lookahead जाँचा।
> - Gate phase 2026-10-27 को लगभग 02:49 से 10:48 UTC तक चला (28,732 s)। stderr खाली रहा।

## 1. क्या test हुआ

- **A3 volatility regime:** 12 measures, जैसे NATR, RV20, EWMA, Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang, GARCH, GJR, EGARCH, vol-of-vol और kurtosis।
  - हर measure "कम volatility" (नीचे के 20%) या "ज़्यादा volatility" (ऊपर के 20%) वाले हालात में 20-bar trend के साथ (follow) या उल्टा (fade) चला।
- **A3 events:** ATR expansion, squeeze release, NR7 / NR4 / inside-bar breakout, Williams breakout, skewness और jump।
- **A4 flow:**
  - liquidity regimes: VPIN (असली taker-buy volume से), Kyle λ, Amihud, Roll spread;
  - directional rules: OBV, Chaikin, CMF, VPT, EMV, Klinger, NVI/PVI, CVD, trade intensity, relative volume, volume profile;
  - information bars: volume, dollar और imbalance bars।
- **Scales:** 15m, 1h, 4h।
- **Exits:**
  - **X1:** ±2σ triple barrier, 7 दिन;
  - **X2:** ±1%;
  - **X3:** उल्टा signal आने पर reversal।
- **Periods:**
  - D 2020–2023, V 2024, H 2025-01 – 2026-09;
  - हर दिन का record `batch2_daily.parquet` में है, साथ में `batch2_monthly.csv` और `batch2_yearly.csv`।
- **H की ईमानदार स्थिति (protocol §1):** H पहले Batch 1 और NP4 में खुल चुका था। इसलिए यहाँ `edge = True` आता भी, तो वह सिर्फ़ forward-watch का candidate होता, profit का दावा नहीं।

## 2. Gates (edge के लिए सारे पास होने चाहिए)

| Gate | शर्त | Batch 2 में पास (972 में) | Batch 1 (567 में) |
|---|---|---|---|
| G1 | H mean के 95% CI की निचली सीमा > 0 | **1** | 0 |
| G2 | H में ≥ 100 trades | 856 | 537 |
| G3 | H mean ≥ random-entry control का 95th percentile | 52 | 12 |
| G4 | 2025 और 2026, दोनों में mean > 0 | 69 | 18 |
| G5 | DSR > 0.95 (N = 2,698, यानी अब तक test हुए सारे configs) | **0** (max 0.35) | 0 |
| G6 | 2× fees और 1-bar देरी पर भी H mean > 0 | 111 | 53 |
| **Edge** | सारे gates | **0** | 0 |

## 3. Family का सार

**ज़रूरी बात:** इस batch के लगभग हर rule का "follow" और "fade" जोड़ा है, यानी एक ही signal की उल्टी दिशा। इसलिए हर family का औसत gross अपने-आप लगभग 0 आता है, और औसत net लगभग −fee (≈ −0.095% प्रति trade)। Family का औसत इस बार कोई जानकारी नहीं देता। काम की संख्याएँ ये हैं:

| Family | Configs | पूरा 2020–26 positive | D, V, H तीनों positive |
|---|---|---|---|
| A3 regime (volatility) | 432 | 18.8% | 15 |
| A3 events | 144 | 14.6% | 5 |
| A4 regime (liquidity) | 144 | 19.4% | 7 |
| A4 flow directional | 234 | 21.4% | 11 |
| A4.10 info bars | 18 | 16.7% | 0 |
| **कुल** | **972** | **18.8%** | **38** |

- अगर हर period में positive या negative होना संयोग (50–50) होता, तो तीनों periods में positive लगभग 972 / 8 ≈ 121 configs आते। असल में सिर्फ़ 38 आए।
- Batch 1 में यह संख्या 567 में से 19 थी।
- Fee हर config को नीचे खींचती है, इसलिए संयोग से भी कम configs लगातार positive रहते हैं।

## 4. Top 20 (protocol की ranking)

**तालिका कैसे पढ़ें:**
- सभी नंबर प्रति trade औसत net % में हैं, futures fees के साथ।
- "H+ महीने" 21 में से हैं।
- Gates column G1 / G3 / G4 / G5 / G6 के क्रम में है (Y = पास, n = fail)।

| # | Config | Exit | D | V | H | H trades | H CI निचली सीमा | H+ महीने | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | G1 G3 G4 G5 G6 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Garman-Klass LOW follow 4h | X3 | +0.00 | +0.61 | +0.44 | 148 | −0.05 | 12 | +0.47 | +0.63 | −0.70 | +0.27 | +0.61 | +0.24 | +0.74 | nYYnY |
| 2 | Yang-Zhang LOW follow 4h | X3 | −0.03 | +0.51 | +0.52 | 150 | **+0.01** | 12 | +0.66 | +0.45 | −0.74 | +0.21 | +0.51 | +0.36 | +0.74 | YYYnY |
| 3 | Rogers-Satchell LOW follow 4h | X3 | −0.17 | +0.39 | +0.50 | 144 | −0.02 | 12 | +0.27 | −0.07 | −0.74 | +0.26 | +0.39 | +0.39 | +0.68 | nYYnY |
| 4 | Parkinson LOW follow 4h | X3 | −0.34 | +0.40 | +0.47 | 151 | −0.03 | 12 | −0.94 | +0.04 | −0.68 | +0.19 | +0.40 | +0.33 | +0.68 | nYYnY |
| 5 | Yang-Zhang HIGH follow 15m | X1 | +0.44 | +0.14 | +0.56 | 168 | −0.08 | 13 | +0.72 | +0.85 | +0.42 | −0.20 | +0.14 | −0.10 | +1.40 | nYnnY |
| 6 | Jump follow 15m | X3 | +0.28 | +0.26 | +0.34 | 301 | −0.06 | 12 | +0.59 | +0.05 | +0.17 | +0.28 | +0.26 | +0.32 | +0.38 | nYYnY |
| 7 | Roll spread HIGH fade 4h | X3 | −0.74 | +0.10 | +0.58 | 118 | −0.02 | 11 | −1.56 | −0.74 | −0.10 | −0.66 | +0.05 | +0.54 | +0.62 | nYYnY |
| 8 | NATR LOW follow 4h | X3 | −0.02 | +0.03 | +0.48 | 147 | −0.05 | 11 | +0.81 | +0.23 | −0.84 | +0.45 | +0.03 | +0.45 | +0.52 | nYYnY |
| 9 | Parkinson LOW fade 15m | X1 | −0.22 | −0.33 | +0.73 | 114 | −0.01 | 13 | −0.95 | −1.06 | +1.19 | −0.09 | −0.38 | +0.38 | +1.20 | nYYnY |
| 10 | Garman-Klass LOW fade 15m | X1 | −0.53 | −0.58 | +0.78 | 112 | −0.04 | 11 | −1.64 | −1.03 | +0.90 | −0.39 | −0.63 | +0.82 | +0.78 | nYYnY |
| 11 | Vol-of-vol LOW fade 4h | X3 | −0.18 | −0.48 | +0.57 | 145 | −0.11 | 14 | +0.22 | +0.49 | −0.92 | −0.61 | −0.49 | +0.77 | +0.18 | nYYnY |
| 12 | Ease of Movement follow 4h | X3 | −0.01 | +0.27 | +0.14 | 389 | −0.10 | 13 | +0.13 | −0.16 | −0.08 | +0.05 | +0.27 | +0.13 | +0.17 | nYYnY |
| 13 | Rogers-Satchell LOW follow 4h | X1 | −0.47 | +0.15 | +0.46 | 99 | −0.19 | 13 | −0.44 | −1.61 | +0.10 | −0.02 | +0.15 | +0.09 | +0.92 | nnYnY |
| 14 | Vol-of-vol HIGH follow 4h | X1 | +0.49 | +0.76 | +0.47 | 88 | −0.42 | 13 | +0.33 | +0.26 | +0.93 | +0.28 | +0.76 | −0.09 | +1.11 | nnnnY |
| 15 | Vol-of-vol HIGH follow 4h | X3 | +0.10 | +0.54 | +0.47 | 104 | −0.30 | 11 | −0.04 | +0.29 | +0.24 | −0.12 | +0.54 | −0.03 | +1.51 | nYnnY |
| 16 | ATR expansion follow 4h | X3 | +0.41 | +0.28 | +0.39 | 143 | −0.34 | 14 | +1.53 | +0.22 | +0.13 | −0.08 | +0.28 | +0.44 | +0.32 | nYYnY |
| 17 | ATR expansion follow 1h | X1 | +0.15 | +0.46 | +0.45 | 166 | −0.19 | 11 | −0.08 | +0.73 | +0.10 | −0.10 | +0.43 | +0.12 | +0.97 | nYYnY |
| 18 | Amihud HIGH fade 4h | X1 | −0.22 | +0.09 | +0.81 | 76 | −0.24 | 10 | −0.26 | +0.84 | −0.70 | −0.49 | +0.09 | +0.74 | +0.75 | nYYnY |
| 19 | Yang-Zhang LOW follow 1h | X3 | +0.11 | −0.03 | +0.04 | 536 | −0.14 | 12 | +0.37 | −0.11 | +0.18 | −0.00 | −0.03 | +0.06 | +0.01 | nYYnn |
| 20 | Kurtosis LOW fade 4h | X3 | +0.35 | −0.19 | +0.34 | 106 | −0.34 | 11 | −0.14 | +2.09 | −0.32 | −0.42 | −0.20 | +0.22 | +0.47 | nnYnY |

हर config के महीने-दर-महीने और साल-दर-साल आँकड़े (दोनों costs, चारों periods) `batch2_monthly.csv` और `batch2_yearly.csv` में हैं।

## 5. सबसे ऊपर वाला cluster: "कम volatility में 4h trend के साथ चलो"

- Ranking के 1, 2, 3, 4 और 8 नंबर असल में **एक ही विचार** हैं: जब 4h volatility अपने पिछले 500 bars में नीचे के 20% में हो, तब 20-bar trend की दिशा में trade लो, और उल्टा signal आने पर निकलो। सिर्फ़ volatility नापने का तरीक़ा अलग है।
- इसलिए ये 5 अलग-अलग सबूत नहीं हैं, एक ही bet हैं।
- **यह विचार कितना मज़बूत है?** उसी नियम में volatility सिर्फ़ closing prices से नापी जाए, तो H में नतीजा negative आता है:

| Volatility का तरीक़ा (LOW follow 4h, X3) | H mean | H CI निचली सीमा | DSR |
|---|---|---|---|
| Yang-Zhang (high/low/open/close) | +0.52% | +0.01% | 0.09 |
| Rogers-Satchell | +0.50% | −0.02% | 0.09 |
| NATR | +0.48% | −0.05% | 0.07 |
| Parkinson | +0.47% | −0.03% | 0.07 |
| Garman-Klass | +0.44% | −0.05% | 0.06 |
| RV20 (सिर्फ़ close) | **−0.15%** | −0.77% | 0.0003 |
| EWMA (सिर्फ़ close) | **−0.23%** | −0.79% | 0.0002 |
| GARCH / GJR / EGARCH (close) | **−0.23 / −0.20 / −0.09%** | ≤ −0.67% | < 0.001 |

  नाप के तरीक़े में छोटे से बदलाव से नतीजा उलट जाता है। साथ ही D (2020–23) में यह लगभग 0 था और 2022 में हर रूप लगभग −0.7% रहा।
- **Protocol के हिसाब से यह edge नहीं है, और forward-watch का candidate भी नहीं।** Candidate सिर्फ़ `edge = True` बनता है।

## 6. Batch 1 के साथ तुलना और निष्कर्ष

- **दोनों batches मिलाकर:** 1,539 primary configs (trend, oscillators, volatility, volume, order flow) और 0 edge।
- **इस batch में ज़्यादा configs G3, G4 और G6 पास करते दिखे।** पर multiple-testing की असली कसौटी (DSR) पर सबसे अच्छा 0.35 रहा, जबकि ज़रूरत 0.95 की है। Batch 1 में भी यही हाल था।
- **Fee-hurdle map से मेल खाता है:**
  - 15m / 1h / 4h पर BTC की औसत चाल fee के मुक़ाबले छोटी है (1h पर 62% सही दिशा चाहिए);
  - ये indicators औसतन लगभग 50% पर हैं।
- **अब तक की पूरी तस्वीर:** एक coin (BTC) पर price, volume या volatility का कोई भी नियम, 15 मिनट से 4 घंटे तक की समय-सीमा पर, fee के बाद कमाई नहीं दे रहा।
  - इसमें 9 महीने की study, non-price study, green candle, 1-second study, Batch 1 और Batch 2 सब शामिल हैं।
  - Project में जो skill साबित है, वह कई coins की आपस में तुलना (1–7 दिन) में है, और वह ECO में पहले से live है।
- **आगे:** batches 3–7 (catalog में) अभी बाक़ी हैं, हर एक का अपना lock होगा। सवाल यह है कि उन्हें चलाना कितना उपयोगी है।
  - दोनों batches का नतीजा और fee-hurdle map मिलकर बताते हैं कि BTC के 15m–4h indicator rules से edge मिलने की संभावना कम है।
  - Batch 3–7 चलाने हैं या नहीं, यह आपका फ़ैसला है।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये backtest नतीजे हैं।
