# Collective (master) AI brain: पूरी research, ज़मीनी जाँच और आगे का रास्ता (20 अक्टूबर 2026)

**आपका सवाल:**
- 1m से 1M (और 1Y) तक हर timeframe की candles को लगातार scan करके अलग-अलग timeframe पर अलग फ़ैसले लेने वाले brains, और उनके ऊपर एक master brain।
- हर timeframe पर entry, exit, stop-loss, trailing और take-profit; spot और futures दोनों।
- हमने अब तक कितना बनाया, research पूरी (saturate) करके ज़मीनी स्तर पर जाँचना, गणितीय model, training कैसे होगी, और बाकी कैसे मिलेगा।
- अभी कोई coding नहीं।

**इस report के आधार:**
1. पुरानी research `RESEARCH_AI_ARCHITECTURE_MULTI_TF_17_OCT_2026.md` (Parts 1–5) और सारी step reports।
2. **एक नई pre-registered study, TFX** (protocol `04db1fea…`, run से पहले lock)। इसमें 11 timeframes, 6 आम strategy/indicator families, long और short, spot और perp का खर्च और असली funding है, और हर trade की तुलना random entry से की गई है। इसका independent verifier अलग से है। Bot का कोई code नहीं बदला गया; सिर्फ़ research measurement का code लिखा गया।
3. नए बाहरी स्रोत; जिनकी पूरी जाँच नहीं हुई उन पर ⚠ लगा है।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।

---

> **⚠ Saturation audit के बाद यह report बदली गई है।** भाग 2 (आख़िर में) में पूरा audit है: TFX-S protocol `120c92b4…`, verifier 6/6 PASS। पहले संस्करण के 7 निष्कर्ष बदले, और हर बदली जगह पर "सुधार" लिखा है। मुख्य बदलाव:
> 1. पहले के "STRICT" और "साफ़" दावे, महीने-वार (time-block) जाँच में नहीं टिके।
> 2. Trend की बढ़त कुछ बड़े trades (tail) से आती है। आम trade random से बदतर है।
> 3. यह बढ़त साल-दर-साल बदलती है।
> 4. एक नया robust candidate मिला: 8h–1D पर oversold ख़रीदना (RSI long)।
> 5. Alts के shorts कमज़ोर निकले।
> 6. 5m–30m पर maker खर्च पर कुछ long cells positive हैं (पहला संस्करण कहता था कि सब negative हैं)।
> 7. 117 cells असल में सिर्फ़ ~4–5 स्वतंत्र दाँव हैं।

> **⚠ भाग 3 (coverage audit, DISC `a9f46d40…`) के बाद और बदलाव:**
> 1. Snooping-proof test (White/Hansen SPA) में "खर्च के बाद पैसा" सीमा पर है (U1: p 0.03–0.06, seed के हिसाब से) और alts पर साबित नहीं। Timing असली है (p < 0.005), पर वह खर्च के नीचे की तेज़ reversal है।
> 2. सात नए indicators (Supertrend, Ichimoku, ADX, Stochastic, Keltner squeeze, VWAP, OBV) कोई नया स्वतंत्र दाँव नहीं जोड़ते: N_eff 3.98 → 3.87।
> 3. **नए candidates:**
>    - 1D cross-sectional momentum: 7/7 साल positive, trend से ρ 0.16, Sharpe 0.40।
>    - Alt trend-short: हर बड़े crash में कमाया, यानी crash hedge।
>    - Funding carry (gated): हर साल ≥ 0, पर अब सिर्फ़ 0–4%/साल, trend से ρ 0.63, और liquidation-margin का जोखिम।
> 4. Funding या premium extreme पर contrarian short बुरी तरह fail हुआ।
> 5. संशोधित योजना 3.8 में है: N1 में XS momentum और crash-hedge variants; N2 में jump model; N5 में linear baseline।

## 0. सीधा जवाब: आगे क्या करना चाहिए (saturation के बाद, संशोधित)

### 0.1 हर timeframe का स्वभाव अलग है (नापा गया, verified)

**5m–30m: बाज़ार उलटता है।**
- RSI/Bollinger जैसी "उलटी" entries random से बेहतर हैं।
- Trend entries random से बदतर हैं।
- Taker खर्च (0.108%) पर सब घाटे में हैं।
- **सुधार:** maker खर्च (0.04%) पर कुछ long cells महीने-वार CI में positive हैं। पर आख़िरी साल में वे भी negative थे, और maker fills की adverse selection अभी मापी नहीं गई है।

**1h–1D: trend timing का औसत random से बेहतर है।**
- **सुधार:** यह बढ़त "आम" trade की नहीं, **कुछ बड़े trends (tail)** की है।
  - Median trend trade random से बदतर है।
  - Top 1% trades कुल मुनाफ़े का 31–122% देते हैं।
- यह **साल पर निर्भर** है: 2022 और 2025 में trend-long की timing भी random से बदतर रही।
- Long–short का मुनाफ़ा BTC के साल के return से जुड़ा है: Spearman 0.71–0.89, 7 साल।

**बदलाव का बिंदु 30m–1h पर है।** यह बात टिकी।

### 0.2 सबसे robust नई चीज़: 8h, 12h और 1D पर "oversold ख़रीदना" (RSI < 30 long)

- Median और trimmed (outliers हटाकर) दोनों positive हैं, और tail पर निर्भरता कम है (top 1% = 11–21%)।
- 10 बड़े coins पर monthly Sharpe ~1.05, max drawdown ~0.2–0.26 (प्रति-coin इकाई)। Trend-long से correlation ≈ 0।
- **सीमा:** आख़िरी साल में 10 बड़े coins पर यह negative रहा, liquid alts पर positive।

### 0.3 Master brain का गणितीय सच: 117 cells ≈ 4–5 स्वतंत्र दाँव (N_eff)

- ज़्यादा timeframes जोड़ने से लगभग कुछ नहीं मिलता। 4h–1D में एक ही family के अलग-अलग timeframes का correlation median 0.57 है, और 1h–1D के 40 trend sleeves ≈ 3.9 स्वतंत्र दाँव हैं।
- **Diversification इनसे आता है:**
  - long बनाम short (ρ −0.28)
  - बड़े coins का trend-long बनाम alts का trend-short (median ρ −0.34)
  - trend बनाम oversold-long (ρ ≈ 0)
- **इसलिए master brain "timeframes" के बीच नहीं, "स्वभाव" के बीच risk बाँटे:** trend, mean-reversion long, और regime के हिसाब से long/short।

### 0.4 AI पर सच (बदला नहीं)

अब तक कोई AI brain पैसे में साधारण नियमों से बेहतर साबित नहीं हुआ। Master brain पहले गणित से बँधा combiner होगा।

### 0.5 अगले कदम (संशोधित; सब pre-registered; बचे 6 trials में से)

| # | काम |
|---|---|
| N1 | **तीन कम-correlated sleeves** (बिना AI): (a) 10 बड़े coins पर trend-long, 4h–1D एक साथ, एक ही दाँव मानकर; (b) 8h–1D oversold-long (RSI); (c) trend-short, regime से gated |
| N2 | **Regime नियम** (long/short risk का झुकाव)। अब यह सबसे अहम है, क्योंकि मुनाफ़े का चिह्न साल के trend से जुड़ा है |
| N3 | **Maker execution** (5m/15m), adverse-selection माप के साथ |
| N4 | Alt shorts: **प्राथमिकता घटाई गई** (monthly Sharpe −0.46 से +0.57) |
| N5 | AI meta-label: आख़िरी, सिर्फ़ N1–N3 पास होने पर |

**Forward recorder चल रहा है।** साफ़ सबूत 17 अक्टूबर 2026 के बाद के data से ही आएगा।

---

## 1. अब तक क्या बना है (timeframe-वार, files से जाँचा हुआ)

| Timeframe | Data (verified) | Rules / research | AI brain (training) | नतीजा | Live (cloud) |
|---|---|---|---|---|---|
| **1m** | 10 coins, 2021-10 से 2024-12। 2025+ के timestamps ख़राब हैं। 399 में से 312 coin-months 5m से हूबहू मिले (G1) | TFX (आज) | कोई नहीं | सब खर्च के बाद घाटे में (नीचे) | नहीं |
| **5m / 15m** | 296 coins, 2020-01 से 2026-09 (SHA); pre-2020 भी | S/R studies, Swing Anatomy, TFX | Step 25 (R24 में 15m/5m features) | AUC +0.0008, पैसा घटा → अपनाया नहीं | नहीं |
| **30m** | 5m से बनाया | Swing Anatomy, TFX | कोई नहीं | — | नहीं |
| **1h** | 699 pairs (universe_all) | S/R, Swing Anatomy | **R24 (Step 24)**: AUC 0.565 | Skill है, portfolio में इस्तेमाल | **हाँ**, 16B का हिस्सा (1D पर) |
| **4h** | 1h/5m से | R2: A1 edge map, A1c, A4 exits, ladder, probe | **R6 (Step 23)** AUC 0.568; **A3** (swing meta-label) FAIL; **T14** (120 coins) FAIL | R6 इस्तेमाल में; swing-AI FAIL | **हाँ**, 16B का हिस्सा (1D पर) |
| **8h / 12h** | 5m से | Swing Anatomy, TFX | कोई नहीं | — | नहीं |
| **1D** | 699 pairs + pre-2020 | पूरा 1D rebuild (Steps 6–30) | B1/R5/R10 (coin चुनना), market-timing (×3 FAIL), exit brain (FAIL), veto | Step 19 सबसे अच्छा; M_AI3 paper | **हाँ** (Step16, 16B, F4, F6 demo) |
| **1W** | 1d से | Step 15 R5/R10 (5/10 दिन), Swing Anatomy, TFX | R5/R10 (relative) | Skill है, long-only DD भारी | R5 scores log होते हैं |
| **1M** | 1d से | Swing Anatomy (top-down उल्टा) | कोई नहीं | बहुत कम data | नहीं |
| **1Y / 6M** | 1d से | Swing Anatomy DE table (BTC 2017–2026 साल-दर-साल) | कोई नहीं | सिर्फ़ विवरण (9 साल = 9 data points) | नहीं |

**Master/collective brain का मौजूदा रूप:** Step 27 "M_AI3", यानी D1, H4 और H1 brains को 1/3 each मिलाकर 50% exposure पर।
- यह एक **नियम-आधारित combiner** है, learned master नहीं।
- इसके तीनों brains का आपसी correlation 0.89–0.95 है, यानी तीनों लगभग एक ही दाँव हैं।

**क्या नहीं बना:**
- Event-driven multi-TF engine
- Regime brain (B1)
- Execution layer (L5)
- 4h/8h/12h trend sleeve
- Short-side multi-TF sleeve
- Coordinator और netting

ये सब Part 3 में design के रूप में मौजूद हैं, code में नहीं।

---

## 2. नई study TFX: हर timeframe पर हर strategy (pre-registered, verified)

### 2.1 तरीका (संक्षेप में; पूरा `logs/research_tf_edge_map/TFX_PROTOCOL_PREREGISTERED.md` में)

**Families:** canonical parameters पहले से तय थे, बाद में बदले नहीं गए।
- TSMOM (20 bar)
- EMA 20/50 cross
- MACD 12/26/9
- Donchian 20/10
- RSI14 30/50/70
- Bollinger 20,2

**Trade के नियम:**
- हर family long और short दो अलग state machines में चलती है।
- Signal bar close पर बनता है और fill अगले bar के open पर होता है।
- Stop नहीं रखा गया, क्योंकि यह timing की परख है।

**खर्च:**
- Spot taker: 0.17% round trip
- Perp taker: 0.108% + असली funding
- Perp maker: 0.04% + funding

**Random-timing control:** हर trade के लिए उसी coin और उसी period में 20 random entries ली गईं, उतने ही bars के hold के साथ। **Excess** = trade − random। यह drift (बाज़ार का सामान्य ऊपर-नीचे) हटाकर सिर्फ़ "timing की जानकारी" नापता है।

**Universes:**
- **U1** = 10 बड़े coins।
- **U2** = T14 वाले liquid coins, शर्त: पिछले 30 दिन का median perp volume ≥ 50M USDT।

**Periods:**
- **dev** = 2020-02 से 2025-09।
- **P3** = 2025-10 से 2026-09। यह "seen" अवधि है और सिर्फ़ report होती है।

**मूल्यांकन:** coin-year block bootstrap से CI निकले, और साथ में Bonferroni CI (U1 में 117 cells, U2 में 107)।

**यह descriptive study है, कोई trial नहीं।** यहाँ से जो भी rule आगे चुना जाएगा, वह अपना अलग pre-registered trial बनेगा, और इन cells की गिनती उसके multiple-testing हिसाब में जुड़ेगी।

### 2.2 मुख्य नतीजा: 30m–1h पर बाज़ार का स्वभाव पलटता है

**U1 (10 बड़े coins, dev 2020-02 से 2025-09):** हर timeframe पर family-groups का औसत। Excess random timing के मुक़ाबले है, और net perp taker खर्च के बाद है (% प्रति trade)।

| TF | Trend families excess | Trend net | Mean-reversion (RSI/BB) excess | MR net | सबसे साफ़ पढ़ाई |
|---|---|---|---|---|---|
| 1m | −0.001% | −0.109% | +0.004% | −0.104% | चाल ≈ 0; खर्च सब खा जाता है (maker पर भी −0.02 से −0.05%) |
| 5m | −0.017% | −0.124% | **+0.041%** | −0.067% | Trend random से **बदतर**, reversal बेहतर; दोनों घाटे में |
| 15m | −0.018% | −0.126% | **+0.053%** | −0.056% | वही |
| 30m | +0.034% | −0.081% | −0.026% | −0.139% | **बदलाव शुरू** |
| 1h | **+0.171%** | +0.058% | −0.157% | −0.232% | Trend अब random से बेहतर |
| 4h | **+0.909%** | +0.764% | −1.172% | −1.133% | Trend साफ़; उलटी entries नुकसानदेह |
| 8h | **+2.58%** | +2.44% | −2.20% | −2.14% | वही, और मज़बूत |
| 12h | **+4.17%** | +4.05% | −2.81% | −2.84% | वही |
| 1D | **+14.0%** | +15.1% | −5.30% | −4.53% | वही |
| 1W | +62% | +80% | (कम trades) | — | बहुत कम trades, भरोसा कम |
| 1M | — | — | — | — | लगभग सब cells "too few" (n < 30) |

**U2 (liquid alts, post-hoc: LUNA/STRAX हटाकर; कारण 2.4 में)** में भी वही बदलाव दिखता है:
- 5m–30m पर सारे trend cells **TIMING− STRICT** हैं, और सारे RSI/BB cells **TIMING+ STRICT**।
- 1h से 12h तक trend TIMING+ है।

यानी यह पैटर्न सिर्फ़ 10 coins की बात नहीं है।

**साहित्य से मेल:** छोटे horizon पर reversal, यानी liquidity provision का premium, और 1–4 हफ़्ते पर time-series momentum, दोनों पहले से दर्ज हैं (Part 3 के स्रोत: Liu & Tsyvinski; Liu, Tsyvinski & Wu; Bianchi et al. ⚠; Kitron & Wengrowicz ⚠)। TFX इसे हमारे Binance data पर, खर्च सहित, timeframe-दर-timeframe नापती है।

### 2.3 Long बनाम short: regime ही सबसे बड़ा फ़ैसला है

**U1, perp taker net, P3 (2025-10 से 2026-09, गिरता बाज़ार; seen):** सभी 6 families का औसत, % प्रति trade।

| TF | Long | Short |
|---|---|---|
| 5m | −0.12 | −0.11 |
| 1h | −0.18 | −0.12 |
| 4h | **−0.63** | **+0.24** |
| 8h | −1.76 | +1.11 |
| 12h | −2.77 | +1.98 |
| 1D | **−4.86** | **+5.18** |

- **dev (2020–2025, बड़ा bull market) में long trend cells भारी फ़ायदे में थे, और short ज़्यादातर घाटे में।**
- पर excess, यानी timing की जानकारी, **दोनों तरफ़ लगभग बराबर** है। उदाहरण: 4h EMA cross का excess long पर +2.39% और short पर +2.27% है।
- **मतलब:** trend-timing असली है और दोनों दिशाओं में काम करता है। कौन-सा पक्ष पैसा बनाएगा, यह बाज़ार की दिशा (regime) पर टिका है। इसलिए master brain का सबसे अहम काम "कौन-सी strategy" चुनना नहीं, बल्कि **long और short के बीच risk का बँटवारा** है।

> **सुधार (saturation, भाग 2.4):** "timing दोनों दिशाओं में असली है" सिर्फ़ औसत पर सही है। साल-दर-साल देखें तो trend-long का excess 2022 और 2025 में negative था। Long−short मुनाफ़ा BTC के साल के return से जुड़ा है (Spearman 0.71–0.89)।

### 2.4 सबसे मज़बूत cells (U1 dev; प्रति trade, perp taker के बाद)

| Cell | Trades/coin-year | Median hold | Net dev | 95% CI निचला | P1 / P2 | P3 | Excess | पढ़ाई |
|---|---|---|---|---|---|---|---|---|
| 4h TSMOM long | 113 | 16 घंटे | +0.60% | +0.34% | +0.72 / +0.34 | −0.41 | +0.34% | Cost-viable STRICT, TIMING+ |
| 4h MACD long | 85 | 44 घंटे | +0.63% | +0.37% | +0.68 / +0.53 | −0.39 | +0.21% | STRICT |
| 8h MACD long | 40 | 96 घंटे | +2.33% | +1.59% | +2.77 / +1.43 | −0.85 | +1.30% | STRICT, TIMING+ |
| 8h TSMOM long | 55 | 24 घंटे | +1.60% | +1.04% | +1.80 / +1.17 | −0.50 | +0.94% | STRICT, TIMING+ |
| 12h MACD long | 27 | 144 घंटे | +2.99% | +1.80% | +3.33 / +2.23 | −0.99 | +1.31% | STRICT, TIMING+ |
| 1D MACD long | 13 | 13 दिन | +6.22% | +3.56% | +7.40 / +3.94 | −3.94 | +2.56% | STRICT, TIMING+ |

**U2 (liquid alts, post-hoc):**
- **Trend shorts** 8h–1D पर cost-viable STRICT और TIMING+ STRICT हैं। उदाहरण: 8h EMA cross short +1.64%, 12h +2.64%। P3 में भी positive हैं। यह हमारी पुरानी खोज से मेल खाता है कि ज़्यादातर छोटे alts समय के साथ गिरते हैं (Steps 17–18, F2)।
- **पर** U2 के 4h–1D long trend cells में "positive coin-years" 29–51% ही हैं (median 37%)। यानी ज़्यादातर coin-years में घाटा है, और फ़ायदा कुछ बड़े pumps से आता है। T14 वाला सबक यहाँ भी लागू है।

> **सुधार (saturation, भाग 2.2–2.3):**
> - ऊपर की तालिका के "STRICT" शब्द coin-year bootstrap से आए थे। Crypto coins एक साथ चलते हैं, इसलिए वह bootstrap CI को बहुत सँकरा बनाता है।
> - महीने-वार bootstrap में U1 के 14 STRICT cells में से 0 STRICT बचे। ये cells फिर भी 95% CI पर positive हैं, 2× खर्च पर भी।
> - Trend cells की median और trimmed excess negative है, यानी कमाई tail से आती है।
> - U2 alt trend-shorts महीने-वार जाँच में cost-viable नहीं रहे। उनका monthly Sharpe −0.46 से +0.57 है।

### 2.5 ईमानदार सीमाएँ (TFX)

- **ये P&L नहीं, timing के माप हैं।** इनमें stops नहीं हैं, position sizing नहीं है, positions का overlap नहीं गिना गया, और portfolio drawdown भी नहीं। Long trend cells की कमाई का बड़ा हिस्सा 2020–2025 का bull market है; excess उसे हटाकर देखता है, net नहीं।
- **1W/1M पर बहुत कम trades हैं:** 1M पर ज़्यादातर cells n < 30, और 1W पर CI बहुत चौड़े। 1M का "trend" definition के हिसाब से बदल जाता है (2.6 देखें)।
- **2020-02 से 2026-09 तक सब data पहले देखा जा चुका है।** साफ़ सबूत सिर्फ़ forward data से आएगा।
- **U2 का data issue:**
  - LUNAUSDT symbol 2022-05 के crash के बाद LUNA 2.0 के लिए दोबारा इस्तेमाल हुआ, और कीमत में 177,399× की नकली छलाँग आई।
  - इससे U2 का locked table कई cells में बिगड़ा, जैसे 1D RSI long का excess −83%।
  - Locked table वैसा ही रखा गया है। LUNA और STRAX को हटाकर उसी code से एक **post-hoc** sensitivity table (`TFX_cells_POSTHOC_excl_LUNA_STRAX.csv`) अलग से बनाई गई है, और ऊपर की U2 पढ़ाई उसी से है। Post-hoc होने की वजह से उसका वज़न कम है।
- **मेरी code की गलती:**
  - Windows में folder नाम case-insensitive होते हैं, इसलिए "1m" और "1M" के trades एक ही folder में मिल गए।
  - मैंने cell table पढ़ते हुए यह पकड़ा, folders के नाम अलग किए, और U1 पूरा दोबारा चलाया।
  - बाकी 9 timeframes के सारे deterministic आँकड़े run 1 और run 2 में **हूबहू (अंतर 0)** मिले।
  - सब `CODE_NOTES.md` में दर्ज है, और पुराने outputs सबूत के तौर पर रखे गए हैं।

### 2.6 Part 3 की timeframe-तालिका की दोबारा जाँच (G0)

| Column | Part 3 से मेल |
|---|---|
| Bars, body, cost ratio | सब हूबहू (184/392 values match) |
| Range, ac1, VR(4) | Protocol वाली definitions (simple returns, (H−L)/open) पर नहीं मिले |

**बाद का निदान (post-hoc):** Part 3 ने **log returns और (H−L)/low** इस्तेमाल किए थे। उन definitions पर BTC के सारे मान हूबहू मिलते हैं (जैसे 1D ac1 −0.0724, VR4 0.9295; 1W VR4 1.1983)। यानी Part 3 के आँकड़े सही थे, बस उनकी definition लिखी नहीं गई थी।

**इससे निकली नई सीख:** 1M का VR(4) definition पर बहुत निर्भर है।

| BTC 1M, VR(4) | मान |
|---|---|
| Log, overlapping | 1.27 |
| Log, non-overlapping | 0.97 |
| Simple returns | 2.25 |

**इसलिए "1M पर trend है" वाला दावा मज़बूत नहीं है। 1W पर तीनों definitions में VR > 1 है** (1.17–1.36)।

---

## 3. बाहरी सबूत (इस pass में नए)

| स्रोत | क्या कहता है | हमारे लिए |
|---|---|---|
| Hudson & Urquhart, "Technical trading and cryptocurrencies", *Annals of OR* 297 (2021) ⚠ abstract/secondary | लगभग 15,000 technical rules, 5 classes। In-sample में predictability और profit दिखे, data-snooping tests के बाद भी। **पर Bitcoin पर out-of-sample में कोई predictability नहीं** मिली; दूसरे coins पर बनी रही | Rules की भीड़ से एक चुनना ख़तरनाक है। हमारी trial-गिनती और forward holdout ज़रूरी हैं |
| Sullivan, Timmermann & White, *JF* 54(5) 1999 ⚠ abstract | White's Reality Check से data-snooping का हिसाब। Brock et al. के rules 1987–1996 में out-of-sample insignificant रहे | TFX के 117/107 cells का Bonferroni इसी वजह से है |
| Detzel, Liu, Strauss, Zhou, Zhu, *Financial Management* 50(1) 2021 ⚠ abstract | Price/MA ratios BTC के daily returns को in और out of sample predict करते हैं (rational-learning model) | 1D trend timing (TFX) से मेल |
| Forecasting (MDPI) 8(3) 40, 2026 ⚠ highlights | BTC पर 15m/4h/1D/3D का hierarchical multi-timeframe ML; ROC-AUC 0.57–0.61; gross +35.97% (2025 OOS) "खर्च के बाद नगण्य" | **Multi-TF AI भी AUC 0.6 पर पैसा नहीं बनाता।** हमारे A3/T14 जैसा |
| Mixture-of-experts / gated regime models (2025–26 preprints) ⚠ | Return के लिए learned gate का खर्च सहित OOS सबूत नहीं मिला। Volatility पर soft routing hard routing से बेहतर | Master brain में learned gating नहीं; soft risk tilt |
| Zarattini, Pagani & Barbon, "Catching Crypto Trends", SFI RP 25-80 (2025) ⚠ abstract | Survivorship-free data पर कई lookbacks वाले Donchian ensemble, volatility sizing, top-20 liquid coins के rotating portfolio के साथ। Fees के बाद Sharpe > 1.5, BTC पर alpha 10.8%/साल | बड़े और liquid coins पर trend (N1a) से मेल; fee के बाद के detail tables नहीं देखे |
| Live Binance BTC-perp maker experiment, arXiv 2502.18625 (2025) ⚠ preprint | 4 लाख+ maker orders। Fill होने की संभावना और fill के बाद के return में उलटा रिश्ता (adverse selection); contrarian maker बेहतर | N3: maker की बचत adverse selection में जा सकती है, इसलिए demo fills पर मापना ज़रूरी |
| Deflated Sharpe ratio (Bailey & López de Prado 2014; Wikipedia summary) ⚠ secondary | Correlated trials को clustering या correlation-matrix के eigenvalues से "effective N" में गिना जाए | TFX का N_eff ≈ 5 आगे के DSR में जुड़ेगा |
| Kelly estimation-risk साहित्य (Chopra–Ziemba; MacLean–Thorp–Ziemba 2011; arXiv 2508.18868) ⚠ | Mean की ग़लती covariance से कई गुना (~20:2:1) महँगी है; fractional Kelly एक बफ़र है | Size को ¼–½ Kelly पर cap; learned sizing नहीं |
| Part 3 के verified स्रोत (Gârleanu–Pedersen; forecast combination puzzle; M4/M5; Man AHL ⚠) | धीमा signal target तय करे, तेज़ परत execution करे; equal weights अक्सर जीतते हैं | ढाँचा वही रहता है |

---

## 4. Collective / master brain का गणितीय model

**संकेत (notation):**
- coin *i*
- timeframe τ ∈ {5m, 15m, 1h, 4h, 8h, 12h, 1D, 1W}
- sleeve *s* = (strategy family, τ, side)
- फ़ैसले का समय = उस τ के bar का close

### 4.1 परतें और उनके गणितीय काम

**परत 0, PIT store:** हर feature x के साथ `available_at` लिखा जाता है। फ़ैसले के समय t पर सिर्फ़ वही data इस्तेमाल होता है जिसका `available_at ≤ t` (merge_asof backward)। यही हमारी leak-proof नींव है (A2 में 500 replay, 0 leak)।

**परत 1, Regime / context (B1), हर 1D close पर:**
- Output सिर्फ़ दो multipliers हैं: g_L(t) और g_S(t) ∈ [g_min, 1]। ये long और short sleeves के risk budget तय करते हैं।
- Volatility target:

  m_vol = min(1, σ* / σ̂_BTC,20d)

- Phase 1 (नियम):

  g_L = m_vol · (BTC_1D_trend > 0 ? 1 : g_min)
  g_S = m_vol · (BTC_1D_trend < 0 ? 1 : g_min)

- बाद में learned (persistent jump/HMM) संस्करण, अलग trial के रूप में।
- **कारण:** TFX 2.3 के अनुसार P3 में long/short का चिह्न regime से पलटता है।

**परत 2, Opportunity scanners (हर τ, नियम):**
- हर sleeve का signal s_{i,s}(t) ∈ {−1, 0, +1}, सिर्फ़ उन families का जिन्होंने TFX और फिर अपना trial पास किया हो।
- 5m–30m पर कोई alpha sleeve नहीं, क्योंकि खर्च के बाद हर cell नकारात्मक है।

**परत 3, Specialist (meta-label) brains, वैकल्पिक:**
- p_{i,s}(t) = P(net R > 0 | x) होता है, isotonic से calibrated।
- Model coins पर pooled है, और पड़ोसी τ पर भी, जिसमें τ एक feature होता है (global model; M4/M5 का सबक)।
- **Gate:** shuffled-label p95 और random-skip p95 दोनों से ऊपर हो, और DSR पूरे trial count पर हो।
- यह परत तभी चालू होगी जब gate पास हो; अब तक नहीं हुआ (A3, T14)।

**परत 4, Master combiner (risk budgeting, learned नहीं):**

1. **Per-trade अपेक्षित R** (R units में):

   μ_j = p_j · W̄_s − (1 − p_j) · L̄_s − c_j

   W̄ और L̄ calibration slice से आते हैं; AI न हो तो p_j = sleeve की historical win rate। Trade तभी जब μ_j > 0।

2. **Sleeve weight** (forecast-combination puzzle के कारण equal-risk से शुरू):

   b_s = B / K

   जहाँ B कुल risk budget है (8,000 USDT का 0.5% per trade × K slots) और K सक्रिय sleeves हैं।

3. **Trade का risk:**

   risk_j = b_s · g_side(t) · f(p_j) · h_HTF

   - f(p) = clip((p − 0.5)/0.1, 0.5, 1.5) (A3 जैसा)
   - h_HTF ∈ [0.8, 1.2] = अगले बड़े TF की सहमति का tilt, कभी veto नहीं

4. **Notional (Part 3 errata से):**

   N_j = risk_j / (stop दूरी + stop slippage + round-trip cost)

5. **Kelly cap:** binary payoff के लिए

   f* = p − (1 − p)/b

   Size हमेशा ≤ ¼–½ f* पर रखा जाता है। अगर p ≈ 0.5 और b ≈ 1, तो f* ≈ 0। **यही गणित बताता है कि AUC 0.50–0.51 वाले brains को size बढ़ाने का हक़ नहीं।**

6. **Portfolio बाधाएँ:**
   - Σ|N| ≤ 3E (gross)
   - |Σ N_i| ≤ net cap
   - per-coin cap
   - √(wᵀΣw) ≤ σ_target, जहाँ Σ sleeves की rolling covariance है

**परत 5, Netting और coordinator:**

net_i = Σ_s N_{i,s}

- एक दिशा में sleeves → जोड़ (per-coin cap तक)।
- **छोटा τ बड़े τ के विरोध में सिर्फ़ net घटा सकता है**, नई उलटी position नहीं खोल सकता।

**परत 6, Execution (L5):**
- Window W_τ के भीतर (जैसे 4h फ़ैसले के बाद ≤ 1 घंटा) implementation shortfall घटाना। फिर taker fallback।
- **TFX 2.2 के अनुसार यह परत reversal का फ़ायदा ले:** long के लिए 5m/15m पर छोटी गिरावट पर post-only order। A4 में maker fill 96.6% था, और जो orders नहीं भरे उनका net R भरे orders से कम था।

**परत 7, Risk engine (L4) और monitor (L6):** नियम-आधारित, veto के अधिकार के साथ।
- Catastrophe stop exchange पर (MARK_PRICE)।
- DD de-risking, cooldown।
- Drift alarm सिर्फ़ risk घटा सकता है।

### 4.2 Brains जोड़ने का गणित: कब सच में फ़ायदा है

K sleeves हों, हर एक का Sharpe S, और आपसी correlation ρ, तो equal-weight combination का Sharpe:

S_combo = S · √(K / (1 + (K − 1)ρ))

| ρ | K = 3 | K = 6 |
|---|---|---|
| 0.90 (हमारे D1/H4/H1) | ×1.035 | ×1.044 |
| 0.50 | ×1.22 | ×1.31 |
| 0.20 | ×1.46 | ×1.73 |

**सबक:** 1D, 4h और 1h पर एक ही सवाल पूछने वाले brains (ρ 0.89–0.95) जोड़ने से लगभग कुछ नहीं मिलता (+3.5%)। फ़ायदा तब आता है जब sleeves **अलग चीज़** पकड़ें:
- long trend और short trend (regime के अनुसार उलटे)
- बड़े coins और alts के shorts
- trend और execution-reversal

इसलिए "हर timeframe का अपना brain" तभी जुड़ेगा जब उसका OOS correlation बाकियों से < 0.5 हो। यह Part 3 का gate है, और ऊपर की तालिका उसका गणितीय आधार है।

**सुधार (saturation):**
- पहले संस्करण में तालिका के दो मान ग़लत थे: K = 6, ρ = 0.20 पर ×1.89 लिखा था, सही ×1.73 है; और ρ = 0.90 पर ×1.05 की जगह ×1.044।
- अब ρ नापा जा चुका है (भाग 2.5):
  - 4h–1D में एक ही family के अलग-अलग TFs: median 0.57
  - long बनाम short: −0.28
  - U1 trend-long बनाम alt trend-short: −0.34 (median)
  - trend-long बनाम RSI-long: ≈ 0
  - N_eff ≈ 4–5

**Negative ρ पर ध्यान:** ρ < 0 वाले sleeves को जोड़ने से Sharpe तभी बढ़ता है जब दोनों का अपेक्षित return > 0 हो। Short sleeves का dev-अवधि का return negative था, इसलिए उनका फ़ायदा सिर्फ़ regime-gating से आ सकता है।

---

## 5. हर timeframe पर training कैसे होगी (जब कोई AI component gate के लिए आए)

| TF | Label | Features | Retrain | Validation |
|---|---|---|---|---|
| 1h, 4h, 8h, 12h (एक pooled "fast-swing" model, τ feature) | Triple-barrier / first-passage R उसी τ के ATR में; time stop = τ के हिसाब से bars | अपना τ + अगले बड़े τ का **बंद** bar; volume spike; funding; OI/taker (F6 metrics, 30 coins); regime multiplier | मासिक, purged + embargo ≥ time stop | Walk-forward; shuffled labels (20); random-skip portfolios (100); DSR (कुल trials); PBO (≥ 4 configs); forward shadow |
| 1D | मौजूदा system (R5/B1, monthly) | अछूता | अछूता | अछूता |
| 1W | पहले नियम (weekly TSMOM); AI तभी जब events पर्याप्त हों | — | तिमाही | वही gates |
| 5m–30m | **कोई alpha model नहीं**। Execution parameters (window, offset) के नियम | Fills ledger | मासिक review | Implementation shortfall बनाम "तुरंत taker" |
| 1M / 1Y | कोई model नहीं (N बहुत कम) | सिर्फ़ context | — | — |

**"लगातार सीखना" का ईमानदार मतलब:**
- हर bar पर scan और ledger चलता है।
- सीखना तय समय पर होता है: नया model challenger बनता है → shadow में चलता है → gate → manual promotion।
- अपने-आप सिर्फ़ risk घट सकता है (Part 3 का नियम)।

---

## 6. Entry, exit, SL, TP और trailing: हर timeframe पर

**सबूत का सार:**
1. Exits की tuning शोर है: A4 में PBO 0.84 था, और 6 exits में से "सबसे अच्छा" आगे median से नीचे चला गया।
2. AI exit (Step 26) में skill थी (AUC 0.67), पर पैसा नहीं बना।
3. Swings हर timeframe पर ATR में self-similar हैं, और कमाई tail से आती है (mean > median)।

**इसलिए:**
- **SL और trailing नियम-आधारित होंगे, उसी τ के ATR में।** प्रस्ताव:
  - Initial stop = structural (pivot + buffer) या 2–3 ATR।
  - Trailing chandelier 3 ATR।
  - Time stop: 4h पर 60 bars, बाकी TFs पर उसी अनुपात में।
  - **Fixed TP नहीं।** Fixed 2 ATR TP tail काट देता है, इसलिए trailing को प्राथमिकता।
- **Grid से "सबसे अच्छा" नहीं चुना जाएगा।** Plateau नियम से default रहेगा।
- **Entry:** धीमे τ का signal + execution layer पर reversal-maker entry (TFX 2.2, A4 maker)।
- **Risk per trade:** stop + 1% slippage + cost से निकलेगा, ¼–½ Kelly के भीतर।
- **Catastrophe stop** हमेशा exchange पर रहेगा।
- **सुधार (saturation, भाग 2.3):** trend की कमाई tail से आती है, क्योंकि top 1% trades कुल मुनाफ़े का 31–122% देते हैं। इसलिए जीतते trade को कभी fixed TP से न काटें। Trailing इतना ढीला रहे कि बड़ी चाल पकड़ी जा सके। Mean-reversion long (RSI) का exit उसका अपना नियम है (RSI > 50); उस पर trend वाला trailing नहीं लगेगा।

---

## 7. Spot बनाम futures

- **Short सिर्फ़ perp पर संभव है।** ~~TFX के अनुसार trend shorts (alts, 8h–1D) ही सबसे "regime-proof" दिखे।~~ **सुधार:** महीने-वार जाँच में alt trend-shorts का monthly Sharpe −0.46 से +0.57 और drawdown 0.35–1.15 निकला। ये regime-proof नहीं हैं, बस 2022 जैसे गिरते सालों में कमाते हैं।
- **Long के लिए perp सस्ता पड़ता है:**
  - Cost 0.108% बनाम spot 0.17%।
  - E11 (perp पर longs) में खर्च की बचत लगभग +0.30% प्रति trade थी और funding का बोझ लगभग −0.17%, यानी net फ़ायदा perp का रहा (`REPORT_R1_E11_PERP_LONGS_16_OCT_2026.md`)। Bull market में funding बढ़ने का जोखिम बना रहता है।
- **फ़ैसला:** अलग "spot brain" और "futures brain" नहीं। **एक ही signal**, और venue का चुनाव execution/risk परत का नियम होगा:
  - short → perp
  - long → perp, सिवाय तब जब user tax/जोखिम के कारण spot चाहे
- **Tax की बात (Sec 115BBH, पहले दर्ज):** आपने tax को अभी के लिए अलग रखा है। Real money से पहले CA की राय ज़रूरी है।

---

## 8. क्या बाकी है और कैसे मिलेगा (चरण और gates; saturation के बाद संशोधित)

| # | काम | किस सबूत पर | Gate (pre-registered होगा) | Trial |
|---|---|---|---|---|
| N0 | आपका फ़ैसला: संशोधित दिशा मंज़ूर? | — | — | — |
| N1 | **तीन sleeves, बिना AI:** (a) U1 trend-long (4h/8h/12h/1D × 4 trend families; N_eff ≈ 1 दाँव, इसलिए एक sleeve, equal-weight); (b) 8h/12h/1D RSI-oversold long; (c) trend-short (U1 + liquid alts), सिर्फ़ regime के साथ। हर एक ATR stops, trend पर fixed TP नहीं | TFX + TFX-S (2.2–2.6) | MTM portfolio: random-entry p95 से ऊपर; 1.5×/2× cost; DSR ≥ 0.95 (N = 14 पुराने trials + TFX का N_eff ≈ 5 + नए); PBO < 0.30; P1 और P2 दोनों positive; **महीने-वार block bootstrap** | T15 |
| N2 | **Regime नियम** (g_L/g_S: BTC 1D/1W trend + volatility), N1 के ऊपर | TFX-S 2.4 (Spearman 0.71–0.89) | N1 के ऊपर DD घटे और Calmar बढ़े, **हर साल अलग से report**; P3 घोषित "seen" | T16 |
| N3 | Execution: 5m/15m maker entry, adverse-selection माप के साथ | TFX 2.2, TFX-S 2.6, A4, arXiv 2502.18625 ⚠ | Implementation shortfall "तुरंत taker" से बेहतर; न भरे orders की लागत; demo पर असली fills | T17 |
| N4 | Alt shorts को अलग sleeve बनाना: **प्राथमिकता घटाई गई** (N1c में शामिल) | TFX-S 2.5 | — | (budget में नहीं) |
| N5 | Meta-label AI, N1–N3 के ऊपर (वैकल्पिक) | A3/T14 FAIL | Shuffled और random-skip controls से ऊपर | T18 |
| N6 | Engine + chaos test + forward shadow | Part 3 A7–A8 | 0 orphan/stop-less; forward नतीजा backtest band के भीतर | — |
| — | Real money | — | सिर्फ़ आपका फ़ैसला, ≥ 90 forward दिन के बाद | — |

**Trial budget:** 20 में से 14 इस्तेमाल हो चुके हैं। N1, N2, N3 और N5 = 4 और, फिर 2 बचेंगे। TFX/TFX-S descriptive हैं और budget में नहीं गिने जाते, पर उनका N_eff (≈ 5) आगे के DSR में जुड़ेगा।

---

## 9. हम अभी क्या नहीं जानते

- Trend-timing की बढ़त costs, stops और overlap के साथ **portfolio स्तर** पर टिकेगी या नहीं। TFX सिर्फ़ प्रति-trade timing मापती है (N1 में पता चलेगा)।
- Regime नियम P3 जैसे मोड़ को समय पर पकड़ेगा या नहीं। Market-timing AI तीन बार fail हुआ था (Steps 17, 20, 21)। नियम-आधारित volatility/trend overlay अलग चीज़ है, पर वह भी अप्रमाणित है।
- 5m/15m reversal execution maker queue और adverse selection के बाद असली फ़ायदा देगा या नहीं (N3 + demo fills)।
- 1W/1M पर कोई भरोसेमंद निष्कर्ष मौजूदा data से शायद कभी नहीं निकलेगा।
- Oversold-long (RSI 8h–1D) बड़े coins पर आख़िरी साल negative क्यों रहा, और alts पर positive क्यों। यह 1 साल का data है, इसलिए noise भी हो सकता है।
- Trend की tail-निर्भरता का मतलब है कि बहुत कम घटनाएँ नतीजा तय करती हैं। Forward data में ऐसी 2–3 घटनाएँ आने में साल लग सकते हैं।
- **2020–2026 का पूरा data "seen" है।** कोई भी backtest नतीजा तब तक "साबित" नहीं, जब तक forward data उसे backtest band के भीतर न दिखाए।

---

## 10. सत्यापन (TFX)

- **Protocol:** `logs/research_tf_edge_map/TFX_PROTOCOL_PREREGISTERED.md` (`04db1fea…`), run से पहले lock।
- **Code:** `src/research/tf_edge_map.py`। Verifier: `src/audits/verify_tf_edge_map.py`, अपना code, study को import नहीं करता।
- **Verifier नतीजा:** **8/8 PASS** (`logs/research_tf_edge_map/verify_stdout.txt`):
  - G1 में 1m का मिलान 9 coin-months पर
  - 300 U1 और 300 U2 trades verifier के अपने bars, indicators, state और funding से दोबारा बने, 0 mismatch
  - सारे cells के n और means trade files से (अंतर 2e-16)
  - Excess अपने random draws से 3 SE के भीतर
  - TF stats
  - G0
  - SHAs

  Post-hoc LUNA/STRAX table उसी verified code और उन्हीं trade files से बनी है, पर उसका अलग verifier run नहीं हुआ।
- **Outputs:**
  - `TFX_cells.csv` (locked, run 2)
  - `TFX_cells_POSTHOC_excl_LUNA_STRAX.csv`
  - `TF_stats.csv`, `G0_part3_replication.csv`, `G1_1m_usability.csv`
  - `claims_tfx.json`, `CODE_NOTES.md`
  - Run-1 bug outputs, सबूत के तौर पर
- **Trade files:** `data/derived/tf_edge_map/`

---

# भाग 2: Saturation audit (TFX-S, 20 अक्टूबर 2026)

**तरीका:**
- Protocol `logs/research_tf_edge_map/TFXS_PROTOCOL_PREREGISTERED.md` (`120c92b4…`), measurement से पहले lock।
- Round 1 (पढ़कर audit) में 10 findings मिले: A1–A10।
- Round 2 में S1–S7 नापे गए। Verifier `verify_tfx_saturation.py`: **6/6 PASS**।
- Round 3 और 4: integrate करके दोबारा audit।
- पूरा log: `logs/research_tf_edge_map/SATURATION_LOG.md`।
- Saturation का नियम: एक पूरे round में 0 material findings।

## 2.1 Round-वार findings (सार)

| Round | Material | Minor | मुख्य |
|---|---|---|---|
| 1 (पढ़कर) | 1 (+ 4 जिनकी जाँच Round 2 में हुई) | 1 | Maker वाला दावा ग़लत; CI, tails, cost, एक ही regime-switch, ρ और N_eff अनापे |
| 2 (मापकर) | 7 | 2 | नीचे 2.2–2.6 |
| 3 और 4 | 2.7 और 2.8 देखें | | |

## 2.2 महीने-वार (time-block) CI: पहले के STRICT दावे नहीं टिके

| Universe | Reading | Coin-year bootstrap (पहले) | Month-block bootstrap (अब) |
|---|---|---|---|
| U1 (10 बड़े coins) | COST-VIABLE-PERP | 25 | 22 |
| U1 (10 बड़े coins) | COST-VIABLE-PERP-STRICT | 14 | 0 |
| U1 (10 बड़े coins) | TIMING+ | 48 | 19 |
| U1 (10 बड़े coins) | TIMING+-STRICT | 16 | 2 |
| U1 (10 बड़े coins) | TIMING- | 26 | 16 |
| U1 (10 बड़े coins) | COST-VIABLE-2X (नया) | — | 21 |
| U1 (10 बड़े coins) | MAKER-VIABLE (नया) | — | 30 |
| U2 post-hoc (alts) | COST-VIABLE-PERP | 21 | 3 |
| U2 post-hoc (alts) | COST-VIABLE-PERP-STRICT | 11 | 0 |
| U2 post-hoc (alts) | TIMING+ | 40 | 12 |
| U2 post-hoc (alts) | TIMING+-STRICT | 24 | 5 |
| U2 post-hoc (alts) | TIMING- | 34 | 13 |
| U2 post-hoc (alts) | COST-VIABLE-2X (नया) | — | 3 |
| U2 post-hoc (alts) | MAKER-VIABLE (नया) | — | 5 |

(एक cell में COST-VIABLE-PERP-STRICT होने पर वह COST-VIABLE-PERP में भी गिना गया है।)

**पढ़ाई:**
- 10 बड़े coins पर 4h–1D के trend-long cells अब भी 95% CI पर positive हैं, और 2× taker खर्च पर भी। पर "STRICT" (Bonferroni) कोई नहीं बचा।
- Alts पर सिर्फ़ 3 cells बचे: 8h MACD long, 8h RSI long, 12h RSI long।

## 2.3 Trend की बढ़त tail से आती है (robust आँकड़े)

U1 dev, % प्रति trade:

| Cell | Mean excess | Median excess | 5%-trimmed excess | Trimmed net | Top 1% trades का हिस्सा (कुल net में) |
|---|---|---|---|---|---|
| 12h DONCH long | +2.85 | -6.16 | -1.96 | +1.08 | 50% |
| 1D DONCH long | +9.84 | -7.73 | -1.96 | +4.73 | 31% |
| 4h DONCH long | +0.86 | -2.73 | -1.18 | -0.33 | 71% |
| 8h DONCH long | +2.12 | -3.96 | -1.72 | +0.20 | 58% |
| 12h MACD long | +1.31 | -2.83 | -1.03 | +0.35 | 57% |
| 1D MACD long | +2.56 | -4.69 | -1.23 | +1.64 | 49% |
| 4h MACD long | +0.21 | -1.44 | -0.59 | -0.24 | 94% |
| 8h MACD long | +1.30 | -1.87 | -0.33 | +0.50 | 51% |
| 12h RSI long | +0.59 | +2.76 | +1.19 | +4.12 | 15% |
| 1D RSI long | +0.86 | +5.24 | +2.39 | +9.94 | 11% |
| 4h RSI long | -0.46 | +1.32 | +0.14 | +0.91 | 64% |
| 8h RSI long | +0.14 | +1.86 | +0.70 | +2.50 | 17% |
| 12h TSMOM long | +1.01 | -1.75 | -1.59 | -0.80 | 87% |
| 1D TSMOM long | +2.93 | -2.62 | -2.37 | -0.64 | 78% |
| 4h TSMOM long | +0.34 | -0.83 | -0.70 | -0.53 | 121% |
| 8h TSMOM long | +0.94 | -1.18 | -0.94 | -0.49 | 82% |

**पढ़ाई:**
- Trend families (TSMOM/MACD/DONCH) में median और trimmed excess negative है, यानी आम trade random से बदतर है। पूरी बढ़त कुछ बड़े trends से आती है।
- RSI long (oversold ख़रीदना) अकेली family है जिसमें median और trimmed दोनों positive हैं और tail पर निर्भरता कम है।

## 2.4 साल-दर-साल: बढ़त regime पर टिकी है

Trend families (4) pooled, U1, perp taker net, % प्रति trade:

| TF | Side | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| 1D | long | +79.05 | +22.06 | -4.80 | +6.37 | +8.23 | -2.68 | -1.23 |
| 1D | short | -1.67 | -4.41 | +2.35 | -2.38 | -2.12 | -0.43 | +1.87 |
| 4h | long | +2.26 | +2.95 | -0.43 | +0.65 | +1.13 | -0.34 | -0.20 |
| 4h | short | -0.23 | -1.30 | +0.81 | -0.61 | -0.28 | -0.01 | -0.06 |
| 8h | long | +7.13 | +7.46 | -0.67 | +2.18 | +2.80 | -0.43 | -0.33 |
| 8h | short | -0.01 | -1.37 | +1.57 | -0.49 | -0.63 | +0.12 | +0.39 |

BTC साल का return: 2020: +302%, 2021: +60%, 2022: -64%, 2023: +156%, 2024: +121%, 2025: -6%, 2026: -5%।

Spearman (BTC साल का return, long−short net), 7 साल:

| Universe | 1h | 4h | 8h | 12h | 1D |
|---|---|---|---|---|---|
| U1 | 0.79 | 0.75 | 0.71 | 0.82 | 0.82 |
| U2X | 0.75 | 0.75 | 0.89 | 0.89 | 0.89 |

**पढ़ाई:** जिस साल BTC ऊपर गया उस साल long trend कमाया, और जिस साल नीचे गया उस साल short। Trend-long का excess (timing) भी 2022 और 2025 में negative था। इसलिए regime नियम (N2) अब सबसे अहम कदम है। साथ ही, market-timing AI 3 बार fail हुआ था, इसलिए N2 सिर्फ़ सरल नियम होगा।

## 2.5 Sleeves का correlation और N_eff (master brain का गणित)

Monthly realized P&L series, dev (2020-02 से 2025-09):

| Measure | मान |
|---|---|
| U1 के सभी 112 sleeves का N_eff | **4.3** |
| U1 trend sleeves 1h–1D (40) का N_eff | **3.9** |
| U2X सभी (103) / trend 1h–1D | 4.4 / 3.9 |
| एक ही family+side, अलग TF (4h–1D): median ρ | +0.57 (n = 216) |
| Long बनाम short (एक ही TF+family, 4h–1D): median ρ | -0.28 (n = 72) |
| Trend बनाम MR (एक ही TF+side, 4h–1D): median ρ | +0.21 (n = 192) |
| U1 trend-long बनाम alt trend-short (4h–1D): median ρ | -0.34 (n = 16) |

**Sleeve-स्तर (प्रति-coin इकाई, बिना sizing; annualised Sharpe / max drawdown):**
- U1 trend-long 4h–1D: Sharpe 0.53–1.46, MDD 0.26–0.80।
- RSI-long 8h–1D: U1 Sharpe 1.04–1.08, MDD 0.20–0.26; U2X Sharpe 0.59–0.79।
- Alt trend-short (U2X) 4h–1D: Sharpe -0.46 से 0.57, MDD 0.35–1.15।

**गणितीय निष्कर्ष:**
- 4h, 8h, 12h और 1D के trend sleeves लगभग एक ही दाँव हैं।
- ज़्यादा timeframes जोड़ने से Sharpe नहीं बढ़ता (4.2 का formula, ρ ≈ 0.57)।
- Master brain को risk "timeframes" में नहीं, **स्वतंत्र स्वभावों** में बाँटना चाहिए: trend-long, oversold-long, और regime-gated short।
- TFX के ~117 cells को आगे के DSR में N ≈ 5 गिनना होगा (spectral N_eff; Bailey & López de Prado DSR ⚠ secondary: correlated trials को clustering या eigenvalues से गिनना)।

## 2.6 Maker खर्च पर 5m–30m (A1 का निपटारा)

| Cell (U1) | Maker net dev | Month-block CI निचला | P3 maker net |
|---|---|---|---|
| 5m RSI long | +0.071% | +0.036% | -0.032% |
| 15m EMAX long | +0.149% | +0.033% | -0.080% |
| 15m RSI long | +0.128% | +0.005% | -0.031% |
| 15m BB long | +0.067% | +0.019% | -0.034% |
| 30m EMAX long | +0.344% | +0.068% | -0.188% |
| 30m BB long | +0.107% | +0.023% | -0.025% |

**पढ़ाई:**
- पहले संस्करण का "5m–30m सब घाटे में" सिर्फ़ taker खर्च पर सही था।
- Maker (entry और exit दोनों maker) पर कुछ long cells positive हैं, पर:
  - (1) आख़िरी साल में सब negative रहे।
  - (2) दोनों तरफ़ maker मानना आशावादी है।
  - (3) Binance पर live maker study ⚠ (arXiv 2502.18625: 4 लाख+ orders, BTC perp) के अनुसार जिन हालात में fill होने की संभावना ज़्यादा होती है, उन्हीं में fill के बाद का return ख़राब होता है (adverse selection)।
- इसलिए 5m–30m अलग sleeve नहीं बनेंगे। ये सिर्फ़ N3 (execution) के भीतर, असली demo fills के साथ परखे जाएँगे।

## 2.7 Round 3 (integrate के बाद audit)

- Report की हर संख्या files से मिलाई गई (S8)।
- 1 गलती मिली: tail share "49–122%" लिखा था, सही "31–122%" है। ठीक किया।
- 2 असंगतियाँ मिलीं: पुराने section 0 में "N4 = forward recorder" और section 8 में "N4 = alt shorts"; section 7 में "alt shorts regime-proof"। दोनों ठीक किए।
- इनमें से कोई निष्कर्ष नहीं बदलता, इसलिए तीनों **minor** हैं।

## 2.8 Saturation की स्थिति

**Saturation पहुँची (protocol नियम के अनुसार):**
- Round 3 (integrate के बाद पूरा audit) में **0 material** और 3 minor findings मिले, सब ठीक किए गए।
- Round 1: 1 material + 4 जिनकी जाँच Round 2 में हुई।
- Round 2: 7 material।

**Research से आगे क्या नहीं बताया जा सकता** (ये सवाल अब सिर्फ़ tests और forward data से सुलझेंगे, और research दोहराने से इनका जवाब नहीं बदलेगा):
1. तीनों sleeves मिलकर portfolio में stops, size और drawdown के साथ टिकेंगे या नहीं → N1।
2. सरल regime नियम सही समय पर long से short की ओर मुड़ेगा या नहीं → N2।
3. Maker execution से adverse selection के बाद कितनी बचत होगी → N3 + demo।
4. Survivorship (A9) और alts के असली spreads → forward recorder + cost snapshots।
5. साफ़ सबूत → 17 अक्टूबर 2026 के बाद का forward data।

## 2.9 सत्यापन (TFX-S)
- Code: `src/research/tfx_saturation.py`। Verifier: `src/audits/verify_tfx_saturation.py`, अपना code, न TFX code को import करता है न TFX-S को।
- **Verifier नतीजा: 6/6 PASS।**
  - महीने-वार CI अपने bootstrap से ±10% width के भीतर, और readings वही।
  - Robust आँकड़े exact (8e-15)।
  - BTC के सालाना returns और साल-वार means exact।
  - Sleeve Sharpe, MDD और correlations exact (7e-17)।
  - N_eff अपने eigen-decomposition से exact।
  - SHAs।
- Outputs: `S1_S4_cells_monthblock.csv`, `S5_trend_by_year.csv`, `S5_summary.csv`, `S6_sleeve_stats.csv`, `S6_correlations.csv`, `claims_tfxs.json`।

---

# भाग 3: Coverage audit — क्या छूटा था, और आज की discovery (DISC, 20 अक्टूबर 2026)

**आपकी बात सही थी।**
- भाग 2 एक *quality* audit था: जो लिखा है वह सही है या नहीं।
- आपने *coverage* audit माँगा था: कौन-सा indicator, strategy, timeframe, गणित, AI brain, training और testing छूट गया।
- यह भाग वही है।

**तरीका:**
- Protocol `logs/research_tf_edge_map/DISC_PROTOCOL_PREREGISTERED.md` (`a9f46d40…`), measurement से पहले lock।
- C0 = documented coverage matrix।
- D1–D6 = उन छूटी चीज़ों का माप जिनका data हमारे पास है।
- Verifier: `src/audits/verify_disc.py`। नतीजा 3.9 में है।
- एक code crash और उसका सुधार `CODE_NOTES.md` में दर्ज है।

## 3.1 Coverage matrix (C0): क्या परखा गया, क्या छूटा

स्थिति के निशान: ✅ परखा गया (file + नतीजा) · ◐ आंशिक · ❌ कभी नहीं परखा · 🆕 आज DISC में परखा।
सबूत का आधार: `src/` का code grep और reports। Priority (H/M/L) का कारण साथ में लिखा है।

### A. Indicators / features
| Item | स्थिति | सबूत / नतीजा | Priority, कारण |
|---|---|---|---|
| Returns (कई horizons), दूरी high/low से, ATR, range, wicks, volume ratio, trades ratio, taker buy ratio, realized vol, hour/weekday, BTC returns, cross-sectional rank | ✅ | Steps 13–25 के feature sets (R6/R24: 31 features); AI skill AUC 0.53–0.57 | — |
| RSI14, SMA50/200 दूरी, range position, high से drawdown, S/R दूरी, volume-at-price, HTF zigzag state (1D/1W/1M), F&G, OI change, top/global L-S ratio, taker L-S, funding | ✅ | A2 store (36 features); A3 FAIL, T14 FAIL | — |
| TSMOM, EMA cross, MACD, Donchian, RSI, Bollinger (rule के रूप में) | ✅ | TFX + TFX-S | — |
| Supertrend, Ichimoku, ADX/DI, Stochastic, Keltner squeeze, VWAP, OBV | 🆕 | DISC D2 (नीचे 3.3) | M: आम indicators; बड़ा सवाल यह है कि ये पुराने 6 से अलग कुछ जोड़ते हैं या नहीं |
| 15m/5m intrabar features | ✅ | Step 25: AUC +0.0008, पैसा घटा | — |
| Options IV (Deribit) | ◐ | M4 collector 17 अक्टूबर से live है, पर किसी model में इस्तेमाल नहीं; history बहुत छोटी | L: अभी data नहीं |
| Order book depth / imbalance | ◐ | Cost snapshots (spread) हैं, forward depth raw VM पर है; signal के रूप में कभी नहीं परखा | M: execution (N3) के लिए उपयोगी, alpha के लिए retail latency बाधा |
| Liquidations | ❌ | Historical data नहीं है; Binance public stream हर symbol पर 1 सेकंड में सिर्फ़ 1 liquidation भेजता है ⚠ | L: data अधूरा |
| On-chain (exchange flows, MVRV आदि) | ❌ | Data नहीं | L/M: मुफ़्त स्रोत सीमित; अलग research |
| Macro / events (FOMC, CPI, ETF flows, DXY) | ❌ | N2 macro-event gate सिर्फ़ प्रस्ताव था (16 अक्टूबर) | M: regime (N2) से जुड़ा |
| Stablecoin supply / Tether | ❌ (अस्वीकृत) | 16 अक्टूबर research में "rejected" | — |

### B. Strategy families
| Item | स्थिति | सबूत / नतीजा | Priority |
|---|---|---|---|
| Swing-following (ZigZag), ladder (S-LAD), breakouts (S-BRK/TRD), double top/bottom, S/R bounce/break | ✅ | Swing Anatomy, A1/A1c, A4, S/R studies | — |
| Test entry / scale-in | ✅ | Probe study (Part 5) | — |
| Trend/MR indicator rules, सभी TFs | ✅ | TFX/TFX-S | — |
| Cross-sectional selection (AI relative brains) | ✅ | Steps 13–24 (R5/R6/R24) | — |
| **Simple cross-sectional momentum rule (long top / short bottom quintile)** | 🆕 | DISC D4 | H: साहित्य में सबसे पक्का crypto factor (Liu–Tsyvinski–Wu); हमारा AI इसका रूप था, पर सरल नियम benchmark नहीं था |
| Long-short (AI top long + bottom short) | ✅ | F2, F7, E-series | — |
| Listing age, MAX/lottery | ✅ | E3, N1 | — |
| **Funding carry / cash-and-carry (delta-neutral)** | 🆕 | DISC D1 | **H:** एक बिल्कुल अलग (non-directional) return स्रोत; He–Manela–Ross–von Wachter ⚠ के अनुसार Binance के ऊँचे खर्च पर भी बड़ा Sharpe |
| **Derivatives-positioning rules (funding extreme, L-S crowding, premium, OI-trend)** | 🆕 | DISC D3 | M: AI feature के रूप में परखे गए थे, rule के रूप में नहीं |
| Pairs / statistical arbitrage (cointegration) | ❌ | code में नहीं | M: market-neutral; Fang et al. survey की श्रेणी; अगला discovery |
| Market making | ❌ (जानबूझकर) | Part 3: queue priority और latency नहीं | L |
| Session / weekday effects | ✅ | Ladder-sessions study (Part 4) | — |
| Event-driven (macro calendar) | ❌ | — | M (N2 के साथ) |
| Volatility breakout / squeeze | 🆕 | D2 KSQZ | — |
| Grid / DCA | ❌ | — | L: कोई edge-सिद्धांत नहीं; drift पर निर्भर |

### C. Timeframes
| Item | स्थिति | सबूत |
|---|---|---|
| 1m, 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1D, 1W, 1M | ✅ | TFX (11 TFs) |
| 1Y / 6M | ◐ | Swing Anatomy DE table (विवरण); 9 data points, model संभव नहीं |
| 2h, 6h, 3D, 2W | ❌ | L: N_eff सबूत (4h–1D ≈ एक ही दाँव) कहता है कि बीच के TFs नई जानकारी नहीं जोड़ेंगे |

### D. Mathematics / risk
| Item | स्थिति | सबूत | Priority |
|---|---|---|---|
| Calmar, MTM drawdown, DSR, PBO (CSCV), block bootstrap, Bonferroni, isotonic calibration | ✅ | A3/A4/T14/TFX | — |
| Volatility sizing / vol-target | ✅ | Step 28 FAIL; F7 RS | — |
| Inverse-vol weights | ✅ | E4 FAIL | — |
| Correlation, N_eff, combination math | ✅ | TFX-S (आज) | — |
| EVT tail monitor | ✅ | N3 live (monitor) | — |
| **White Reality Check / Hansen SPA** | 🆕 | DISC D5 | H: "सबसे अच्छा cell" का snooping-proof test |
| **Crisis stress** (सबसे बड़ी गिरावटें) | 🆕 | DISC D6 | H |
| Kelly sizing | ◐ | सिर्फ़ formula (आज का गणित); परखा नहीं | M: N1 में ¼–½ Kelly cap |
| Regime models: HMM / jump model | ◐ | Learned market brains 3× FAIL; persistent jump model कभी नहीं परखा (Shu–Yu–Mulvey में उसने B&H को हराया ⚠) | **H:** N2 के लिए सबसे अच्छा उम्मीदवार |
| GARCH / HAR volatility forecast | ❌ | — | M: sizing और stop के लिए; MIDAS/HAR साहित्य |
| Change-point / CUSUM | ❌ | — | M: regime (N2) और drift (L6) |
| Copula / tail dependence | ❌ | — | L: portfolio tail risk |
| CVaR / risk budgeting optimizer | ❌ | — | L: forecast-combination puzzle के कारण equal-risk पहले |
| Capacity / market impact by size | ◐ | Spread $1k–$30k (Step 2 snapshots) | M: 8,000 USDT पर छोटा, बाद में ज़रूरी |

### E. AI model classes
| Item | स्थिति | सबूत | Priority |
|---|---|---|---|
| Gradient boosting (HistGradientBoosting) | ✅ | सारे brains (Steps 7–26, A3, T14) | — |
| **Linear / logistic baseline** | ❌ | grep: 0 | **H:** हर AI को एक सरल baseline से हराना चाहिए; कम data पर linear अक्सर बराबर रहता है |
| Random forest / bagging | ◐ | Step 11 में bagging + time-decay (FAIL) | L |
| Neural nets (LSTM, TCN, transformer) | ❌ | grep: 0 | L/M: MDPI 2026 ⚠ (multi-TF ML, AUC ~0.6, खर्च के बाद नगण्य); हमारा data कम |
| Reinforcement learning | ❌ | — | L: HRPM-जैसे papers में खर्च सहित साफ़ OOS सबूत नहीं (Part 3) |
| Learning-to-rank (cross-sectional) | ❌ | — | M: relative brains ने classification इस्तेमाल किया |
| Ensembles of different model types | ❌ | — | M: M4/M5 का सबक |
| Online / incremental learning | ❌ (जानबूझकर) | Part 3: ARF blind spot ⚠ | L |
| Conformal prediction / abstain | ❌ | — | M: "confident-only" (Step 11) का गणितीय रूप |
| LLM | ❌ (अस्वीकृत) | Part 1: look-ahead, FINSABER ⚠ | — |

### F. Training methods
| Item | स्थिति | सबूत | Priority |
|---|---|---|---|
| Monthly walk-forward, purge/embargo, pooled coins, time-decay, bear-data training, more coins | ✅ | Steps 7–26, S2, T14 | — |
| Triple-barrier labels, meta-labeling | ✅ | Step 8, A3 | — |
| Sample-uniqueness weights | ❌ | grep: 0 | M: overlapping labels (López de Prado ch.4) |
| Trend-scanning labels | ❌ | — | L/M |
| Fractional differentiation | ❌ | grep: 0 | L |
| CUSUM event sampling | ❌ | grep: 0 | L/M |
| Hyper-parameter sensitivity | ❌ (जानबूझकर fixed) | Overfitting से बचाव | M: एक pre-registered sensitivity जाँच उपयोगी |
| Feature importance (MDA / SHAP) | ❌ | grep: 0 | M: AI क्यों fail हुआ, यह समझने के लिए |

### G. Testing methods
| Item | स्थिति | सबूत |
|---|---|---|
| Shuffled labels, random-skip, random-entry, planted signal, leak canary, 2018–19 OOS, unseen coins, cost stress, DSR, PBO, forward shadow, replay, tamper tests, chaos drill | ✅ | Steps / A-series / F6 |
| Month-block (time) bootstrap | ✅ | TFX-S (आज) |
| White RC / Hansen SPA | 🆕 | D5 |
| Crisis windows | 🆕 | D6 |
| Monte Carlo synthetic paths | ❌ | M: drawdown वितरण के लिए |
| Survivorship-free universe (delisted coins) | ❌ | **H:** U2 का long overstated और short understated हो सकता है; delisted coins का data जोड़ना |


## 3.2 D1 Funding carry (spot long + perp short, delta-neutral)

प्रति unit notional; per capital = ÷ 2।

| Universe | Variant | Period | सालाना return (notional) | Per capital | Sharpe (daily) | Max DD |
|---|---|---|---|---|---|---|
| U1 | a (हमेशा) | dev | +11.6% | +5.8% | 4.5 | 7.3% |
| U1 | a (हमेशा) | P1 | +13.0% | +6.5% | 4.3 | 7.3% |
| U1 | a (हमेशा) | P2 | +8.3% | +4.1% | 11.5 | 0.2% |
| U1 | a (हमेशा) | P3 | +1.2% | +0.6% | 2.5 | 0.8% |
| U1 | b (funding > 0.01%/8h) | dev | +14.5% | +7.2% | 8.0 | 1.9% |
| U1 | b (funding > 0.01%/8h) | P1 | +17.1% | +8.5% | 8.2 | 1.9% |
| U1 | b (funding > 0.01%/8h) | P2 | +8.6% | +4.3% | 11.4 | 0.2% |
| U1 | b (funding > 0.01%/8h) | P3 | +0.1% | +0.1% | 0.6 | 0.2% |
| U2X | a (हमेशा) | dev | +10.4% | +5.2% | 4.9 | 7.0% |
| U2X | a (हमेशा) | P1 | +12.7% | +6.3% | 5.1 | 7.0% |
| U2X | a (हमेशा) | P2 | +5.5% | +2.7% | 5.4 | 2.3% |
| U2X | a (हमेशा) | P3 | -12.0% | -6.0% | -8.5 | 12.4% |
| U2X | b (funding > 0.01%/8h) | dev | +15.3% | +7.6% | 7.6 | 1.6% |
| U2X | b (funding > 0.01%/8h) | P1 | +18.1% | +9.0% | 7.8 | 1.6% |
| U2X | b (funding > 0.01%/8h) | P2 | +9.0% | +4.5% | 8.6 | 0.6% |
| U2X | b (funding > 0.01%/8h) | P3 | +2.7% | +1.4% | 1.1 | 1.6% |

**Variant b, साल-दर-साल (notional पर सालाना %):**

| Universe | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| U1 | +21.3 | +38.6 | +2.3 | +6.6 | +12.9 | +2.3 | +0.0 |
| U2X | +22.4 | +40.6 | +2.1 | +7.7 | +13.9 | +1.7 | +3.9 |

**जोखिम:** spells में perp की सबसे बड़ी उलटी चाल का median 159% है, और 75th percentile 391%। यानी 1× isolated short perp कई spells में **liquidate हो जाता**। इसके लिए portfolio/cross margin या समय-समय पर rebalance चाहिए, जिसका खर्च इसमें शामिल नहीं है। सबसे बुरा 1-दिन basis move -3.5% था।

**Trend-long से correlation (monthly):** 0.63 (U1) / 0.63 (U2X)। Funding तेज़ी वाले बाज़ार में ऊँची होती है, इसलिए carry trend से जुड़ा है, स्वतंत्र नहीं।

**पढ़ाई:**
- Variant b हर साल ≥ 0 रहा, पर कमाई 2020–21 में केंद्रित थी (+21% से +41%)। 2025–26 में सिर्फ़ 0–4% रह गई।
- Always-on (a) 2022 और P3 में घाटे में रहा।
- साहित्य (He–Manela–Ross–von Wachter ⚠) भी कहता है कि ये mispricings समय के साथ घटती हैं।
- **Carry एक कम-जोखिम, कम-कमाई वाला "cash buffer" sleeve बन सकता है**, पर liquidation-margin का design पहले ज़रूरी है।

## 3.3 D2 सात नए indicators (U1, 15m–1D)

- Cells: 84। Month-block पर cost-viable: 25, सब long और 1h–1D पर।
- पुराने 6 families से max correlation का median (4h–1D long): 0.86।
- **N_eff:** पुराने 72 sleeves = 3.98; 84 नए जोड़कर 156 sleeves = **3.87**, यानी कोई नया स्वतंत्र दाँव नहीं जुड़ा।

| Cell (long, कम correlation वाले) | Net dev | Month CI निचला | P3 | Mean excess | Median excess | Max ρ (पुराने से) |
|---|---|---|---|---|---|---|
| 12h KSQZ | +6.46% | +2.80% | +0.39% | +4.83% | -2.64% | 0.64 |
| 1D ADXDI | +11.93% | +2.53% | -5.29% | +6.31% | -5.68% | 0.41 |
| 1D SUPERT | +34.76% | +12.42% | -10.54% | +17.85% | -11.08% | 0.37 |
| 8h SUPERT | +8.85% | +2.85% | -2.85% | +4.69% | -5.53% | 0.69 |

**पढ़ाई:**
- Supertrend, Ichimoku, ADX, VWAP और OBV वही trend-दाँव हैं जो पहले से है।
- Keltner squeeze (KSQZ) कुछ अलग है (ρ 0.6–0.8), और 4h–12h पर TIMING+ है। पर वह भी tail-driven है (median excess negative)।
- Stochastic (MR) में 4h+ पर कोई बढ़त नहीं। 15m पर reversal timing वही पुराना पैटर्न है।
- **सबक:** ज़्यादा indicators जोड़ना "ज़्यादा AI जानकारी" नहीं है; जानकारी वही रहती है।

## 3.4 D3 Derivatives-positioning नियम (1D, 30 coins, 5 दिन hold)

| Rule | Side | n | Net dev | Month CI निचला | P1 / P2 / P3 | Mean excess | Excess CI निचला | Reading |
|---|---|---|---|---|---|---|---|---|
| FUNDX | short | 1133 | -2.33% | -4.18% | -2.69 / -1.36 / -1.89 | -1.58% | -3.76% | none |
| FUNDX | long | 1581 | +0.68% | -0.45% | +0.28 / +1.34 / +0.12 | -0.30% | -1.50% | none |
| LSCON | short | 729 | +1.20% | -0.59% | +1.60 / +0.88 / +1.79 | +2.23% | +0.58% | TIMING+ |
| LSCON | long | 1258 | +0.84% | -0.54% | +0.69 / +1.01 / -0.00 | -0.12% | -1.67% | none |
| OITR | short | 3889 | -0.10% | -1.09% | +0.24 / -0.52 / +0.23 | +1.06% | +0.03% | TIMING+ |
| OITR | long | 3725 | +0.27% | -1.22% | +0.01 / +0.58 / -0.28 | -0.56% | -2.01% | none |
| PREMX | short | 1670 | -2.11% | -3.95% | -2.23 / -1.86 / -1.23 | -1.31% | -3.29% | none |
| PREMX | long | 2834 | +0.42% | -0.63% | +0.52 / +0.23 / +0.11 | -0.53% | -1.68% | none |
| TOPLS | short | 1047 | -0.39% | -2.74% | -3.23 / +0.22 / -0.58 | +0.19% | -2.13% | none |
| TOPLS | long | 448 | +1.57% | +0.52% | +0.96 / +2.19 / -0.66 | +0.44% | -0.68% | COST-VIABLE-PERP |

**पढ़ाई:**
- **"Crowded" retail longs (global long/short ratio ऊँचा) पर short** का timing random से बेहतर है (TIMING+), और P1, P2 और P3 तीनों में positive रहा। पर month-block CI पर net-viable नहीं है।
- Funding या premium extreme पर contrarian short **बुरी तरह fail** हुआ: ऊँची funding के बाद कीमत अक्सर और ऊपर जाती है। इसलिए "funding ऊँची है तो short करो" वाला आम विचार हमारे data में ग़लत निकला।
- Top-trader position ratio नीचा होने पर long, net cost-viable निकला (n 448), पर P3 negative था।

## 3.5 D4 Cross-sectional momentum (U2X, top/bottom quintile, 5-bar hold)

| TF | dev Sharpe | dev MDD | P1 | P2 | P3 (Sharpe) | Trend-long से ρ |
|---|---|---|---|---|---|---|
| 4h | 0.80 | 1.19 | 1.18 | -0.28 | 0.58 | 0.28 |
| 8h | 0.70 | 0.61 | 1.19 | -0.40 | 2.25 | 0.31 |
| 1D | 0.40 | 0.86 | 0.45 | 0.29 | 0.98 | 0.16 |

**1D पर हर साल positive रहा** (2020: 0.63, 2021: 0.50, 2022: 0.25, 2023: 0.47, 2024: 0.43, 2025: 0.82, 2026: 0.57)। Trend-long से correlation सिर्फ़ 0.16 है। पर Sharpe छोटा (0.40) है और drawdown बड़ा। Long leg ने कमाया, और short leg ने सिर्फ़ P3 में।

**पढ़ाई:** साल-दर-साल स्थिरता और कम correlation के कारण यह **diversifier उम्मीदवार** है (साहित्य का सबसे पक्का crypto factor)। 4h और 8h अस्थिर हैं, P2 में negative।

## 3.6 D5 Data-snooping-proof test (White Reality Check + Hansen SPA, joint month bootstrap)

| Universe | Statistic | Cells | Best cell | T_max | p (RC) | p (SPA) |
|---|---|---|---|---|---|---|
| U1 | excess | 117 | 5m RSI long | 4.68 | 0.0035 | 0.0035 |
| U1 | net_taker | 117 | 8h MACD long | 3.32 | 0.0580 | 0.0455 |
| U2X | excess | 107 | 5m RSI long | 4.69 | 0.0000 | 0.0000 |
| U2X | net_taker | 107 | 12h RSI long | 3.09 | 0.0665 | 0.0560 |

**पढ़ाई (बहुत अहम):**
- **Timing (excess) की बढ़त snooping के बाद भी असली है** (p < 0.005)। सबसे मज़बूत cell 5m RSI long है, यानी तेज़ reversal, जो खर्च के बाद पैसा नहीं बनाता।
- **खर्च के बाद पैसा (net taker):**
  - U1 में सबसे अच्छा cell 8h MACD long है: RC p 0.058, SPA p 0.046। यह सीमा पर है, 5% की रेखा को मुश्किल से छूता है।
  - U2X में 12h RSI long: p 0.067 / 0.056, यानी साबित नहीं।
- **Verifier की टिप्पणी:** independent verifier (4,000 draws, अलग seed) में U1 net-taker के p RC 0.036 और SPA 0.030 आए, यानी ±0.02 की सीमा से बाहर, और check 5 **FAIL** हुआ।
- Post-hoc जाँच (`src/audits/diag_d5_seed_stability.py`, 10 seeds × 2,000 और 4,000 draws) में:
  - RC p 0.037–0.054
  - SPA p 0.032–0.045
  - Timing (excess) हर run में p ≤ 0.005
- यानी अंतर Monte Carlo शोर और SE के अनुमान से आया है, code की गलती से नहीं। पर नतीजा साफ़ है: **U1 का खर्च-के-बाद सबसे अच्छा cell p ≈ 0.03–0.06 पर, ठीक 5% की रेखा पर है।** इसे "साबित" नहीं कहा जा सकता।
- मतलब: 117 cells में से "सबसे अच्छे" का पैसा, snooping का हिसाब करके, पक्का नहीं है। इसलिए N1 के protocol में DSR/SPA का N पूरे search पर गिना जाएगा, और forward data ही निर्णायक रहेगा।

## 3.7 D6 सबसे बड़ी 8 गिरावटें (BTC, 7 दिन): किस sleeve ने क्या किया

प्रति-coin इकाई, net taker; carry = notional पर।

| Window | BTC 7d | U1 trend-long | U1 RSI-long | Alt trend-short | Carry (U1, b) |
|---|---|---|---|---|---|
| 2020-03-05 → 2020-03-12 | -47% | -0.46 | -0.08 | +1.21 | +0.75% |
| 2022-06-11 → 2022-06-18 | -33% | -0.31 | -0.04 | +1.14 | +0.00% |
| 2022-05-04 → 2022-05-11 | -27% | -0.49 | -0.07 | +1.31 | +0.14% |
| 2021-05-12 → 2021-05-19 | -26% | +0.30 | -0.01 | +0.62 | +0.07% |
| 2026-01-29 → 2026-02-05 | -26% | -0.23 | -0.13 | +0.78 | +0.00% |
| 2021-06-14 → 2021-06-21 | -22% | -0.42 | -0.00 | +0.49 | +0.09% |
| 2022-11-06 → 2022-11-13 | -22% | -0.43 | +0.02 | +0.80 | +0.00% |
| 2021-02-21 → 2021-02-28 | -21% | +2.50 | +0.01 | +0.11 | +0.44% |

**पढ़ाई:**
- 8 में से 6 crashes में trend-long ने खोया।
- Oversold-long (RSI) ने ज़्यादातर crashes में हल्का खोया।
- **Alt trend-short ने हर crash में कमाया।**
- Carry लगभग 0 रहा (b ज़्यादातर बंद था)।
- **गणितीय सबक:** alt trend-short का औसत return कमज़ोर है, पर यह **tail hedge** है, यानी crash में बीमा। इसलिए N1(c) को "regime-gated short" के साथ-साथ "छोटा, हमेशा-चालू crash hedge" के रूप में भी परखा जाए (pre-registered दो variants)।

## 3.8 Coverage audit के बाद: क्या बचा है और कैसे मिलेगा (H priority)

| # | छूटी चीज़ | क्यों ज़रूरी | कैसे मिलेगा | प्रकार |
|---|---|---|---|---|
| G1 | **Linear/logistic baseline** हर AI के सामने | HGB की विफलता model की है या data की, यह पता चलेगा | N5 के protocol में अनिवार्य baseline | Trial का हिस्सा |
| G2 | **Persistent jump model / HMM regime** | N2 सबसे अहम है; Shu–Yu–Mulvey ⚠ में jump model ने B&H को हराया | N2 में सरल नियम बनाम jump model (दो pre-registered variants) | Trial |
| G3 | **Survivorship-free universe** (delisted coins) | U2 का long overstated, short understated | Binance data archive से delisted symbols download करना | Data |
| G4 | **XS momentum 1D** sleeve | हर साल positive, ρ 0.16 | N1 में चौथा sleeve (pre-registered) | Trial |
| G5 | **Alt short = crash hedge** | D6 | N1(c) के दो variants | Trial |
| G6 | **Carry margin design** | Liquidation risk | Portfolio margin / rebalance नियम + demo | Research + demo |
| G7 | Pairs / stat-arb | Market-neutral, अनपरखा | अगला discovery (descriptive) | Research |
| G8 | GARCH/HAR volatility, change-point | Sizing और regime | N2/N1 के sizing variants | Research |
| G9 | Feature importance (SHAP) + sample-uniqueness weights | AI fail होने का कारण | N5 diagnostics | Research |
| G10 | Order-book imbalance (execution) | N3 adverse selection | VM पर depth recorder + demo fills | Data |

**ऐसी चीज़ें जो data न होने से अभी संभव नहीं:**
- Liquidation history (public feed अधूरा है)
- On-chain data
- Options IV का लंबा इतिहास (M4 collector अभी शुरू हुआ है)
- Macro event calendar

## 3.9 Coverage saturation की स्थिति

**Coverage round C1 (DISC):** H-priority छूटी चीज़ें जिनका data हमारे पास था, सब मापी गईं (D1–D6)।

**Coverage round C2 (survey taxonomy से दोबारा मिलान):** Fang et al., *Financial Innovation* 2022 ⚠ की श्रेणियाँ थीं: technical analysis, pairs trading, econometric, ML, portfolio, और market conditions (bubbles/crashes)। उनसे matrix को दोबारा मिलाया गया। 3 नई चीज़ें मिलीं, तीनों M/L priority:
1. Bubble/crash detection (LPPLS, explosive-root tests): ❌, M। Step 21 का AI crash brain INVALID था।
2. Social-media/news sentiment: ❌, L। Data नहीं है; LLM रास्ता पहले अस्वीकृत हुआ।
3. Portfolio optimisers (mean-variance, HRP): ◐। HRP 16 अक्टूबर को अस्वीकृत हुआ था; equal-risk पहले।

इनमें से कोई H-priority नहीं है जिसे मौजूदा data पर मापा जा सके। **Coverage saturation पहुँची:** C2 में ऐसी कोई नई H चीज़ नहीं मिली जो आज मापी जा सके।

बचा काम 3.8 की सूची (G1–G10) है। ये सब trials (N1, N2, N5), नया data (G3, G10) या demo (G6) माँगते हैं, research दोहराने से नहीं मिलेंगे।

## 3.10 सत्यापन (DISC)
- Code: `src/research/disc_study.py`। Verifier: `src/audits/verify_disc.py`, अपना code।
- **Verifier नतीजा: 7 में से 6 PASS, 1 FAIL:**
  - D1 carry: 10 coins का daily portfolio अपने loop से दोबारा बना, अंतर 2e-16।
  - D2: 300 नए-indicator trades अपने indicator code से, 0 mismatch।
  - D3: 100 derivative-rule trades, 0 mismatch।
  - D4: 3 rebalances (अपनी liquidity, ranks, legs), 0 mismatch।
  - D6: crisis windows exact।
  - SHAs।
  - **D5 FAIL:** net-taker p-values ±0.02 की सीमा से बाहर। ऊपर 3.6 में post-hoc seed जाँच के साथ समझाया गया है। Verifier की सीमा बाद में ढीली नहीं की गई; FAIL जैसा है वैसा दर्ज है।
- Run-1 crash (सिर्फ़ claims step) और उसका finalize: `CODE_NOTES.md`।
- Outputs: `logs/research_tf_edge_map/disc/` (D1–D6 CSVs, `claims_disc.json`, `D5_seed_stability_POSTHOC.csv`) और `data/derived/disc_trades/`।
