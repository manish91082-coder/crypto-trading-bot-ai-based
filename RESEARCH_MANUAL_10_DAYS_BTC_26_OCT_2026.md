# BTC के 10 random दिन: हाथ से (AI दिमाग से) perfect entry, exit और दिशा, फिर उनसे formula (26 अक्टूबर 2026)

> **Discipline:**
> - तरीका दिन चुनने से पहले lock किया गया: `logs/manual_day_study/MANUAL_DAY_STUDY_PROTOCOL.md`, SHA `4ad5f71f…`।
> - दिन seed 20261026 से random चुने गए (`selected_days.txt`)।
> - Analysis पूरी तरह मेरा अपना reasoning है, कोई strategy script नहीं। Code सिर्फ़ तीन कामों में लगा:
>   - candles दिखाने में (`src/tools/print_day_candles.py`);
>   - हर लिखे गए नंबर की calculator जैसी जाँच में (`src/tools/check_claims.py`);
>   - एक बार दिन की ranges पढ़ने में (`first8h_ranges_lookup.txt`)।
> - **हर दिन का पूरा log:** `logs/manual_day_study/day_XX_<date>.md` (step 1 से 6 तक), उसके claims (`day_XX_claims.json`) और जाँच (`day_XX_check.txt`)।
> - **Data की जाँच:**
>   - हर दिन का 1d data दो स्रोतों में बराबर निकला (diff 0.0);
>   - 2022–24 के 5 दिनों का 1m data verified 5m से हूबहू मिला (288/288 bars, diff 0.0)।
> - **कुल 258 नंबरों की जाँच हुई, आखिर में सब सही।** जाँच ने मेरी 7 गलतियाँ पकड़ीं (§7), जिन्हें सुधारकर हर दिन के log में दर्ज किया गया।
> - **ज़रूरी:** 10 दिनों से निकला हर formula सिर्फ़ एक **hypothesis** है। सैकड़ों अनदेखे दिनों पर test होने तक इसे साबित नहीं माना जाएगा (§6)।
> - मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## 1. दस दिन एक नज़र में

| # | दिन | प्रकार | Perfect दिशा (hindsight) | Perfect gross | 00:00 का bias सही था? | पहले 8 घंटे की range |
|---|---|---|---|---|---|---|
| 1 | 2020-02-25 मंगल | trend down | Short | 4.39% | ✅ (short) | 1.95% |
| 2 | 2020-09-06 रवि | range, 10k sweep | Long | 3.52% | ❌ (short था) | 2.55% |
| 3 | 2022-05-30 सोम | **trend up** | Long | 9.97% | ✅ (long) | 5.56% |
| 4 | 2022-07-02 शनि | range, 19k sweep | Long | 2.58% | ❌ (short था) | 1.70% |
| 5 | 2022-07-31 रवि | 24k fake breakout → down | Short | 4.00% | ✅ (short) | 1.56% |
| 6 | 2023-03-01 बुध | prior-low sweep → up | Long | 4.26% | ❌ (short था) | 3.59% |
| 7 | 2024-01-29 सोम | 42k chop → trend up | Long | 3.66% | ✅ (long) | 1.50% |
| 8 | 2024-03-30 शनि | **बहुत शांत** (70k chop) | Short (1.1%) | 1.11% | ~ (neutral) | **0.88%** |
| 9 | 2025-04-18 शुक्र (US holiday) | **बहुत शांत** | Short (0.97%) | 0.97% | ~ (neutral) | **0.85%** |
| 10 | 2026-02-13 शुक्र | 66k sweep → trend up | Long | 5.48% | ❌ (short था) | 1.43% |

**पहली बड़ी सीख:**
- पिछले दिनों के ढाँचे (lower highs, कमज़ोर close) से निकला "दिशा का bias" **8 में से सिर्फ़ 4 दिन सही रहा** (2 दिन neutral)। यानी सिक्के जितना।
- **दिशा पहले से तय करना भरोसेमंद नहीं है।** Turn **levels पर हुए reaction** से पहचाना गया।

## 2. Perfect turn कहाँ बने (ground evidence)

| दिन | Turn | किस level पर |
|---|---|---|
| 2 | Low 9,994.86 | **10,000 के ठीक नीचे**: wick, फिर close ऊपर (prior low 9,825 नहीं टूटा) |
| 4 | Low 18,977.01 | **19,000 के नीचे**: wick, close ऊपर (prior low 18,975 से $2 ऊपर) |
| 5 | High 24,194.82 | **24,000 के ऊपर**: close ऊपर, अगली candle में वापस नीचे (fake breakout) |
| 6 | Low 23,020.03 | **पिछले दिन के low से $0.94 नीचे**; high **ठीक 24,000.00** |
| 7 | Low 41,804.88 | **42,000 के आसपास 15 घंटे की chop** का सबसे गहरा sweep |
| 8 | n/a | 70,000 लगभग 30 बार पार: **noise** |
| 9 | High 85,132.08 | **85,000 के ऊपर** (पहली candle की wick 85k के पार) |
| 10 | Low 65,872.46 | **66,000 के नीचे**: wick, अगली candle close ऊपर |
| 1 | High 9,675 | **पिछले दिन का close/open zone** (9,650–9,656) से rejection |
| 3 | Low 29,299.62 | पिछले close के थोड़ा नीचे; फिर पिछले दिन के high का breakout |

**10 में से 8 दिनों में कोई एक extreme किसी round thousand के ~0.6% के अंदर बना।**

> **ईमानदार चेतावनी (base rate):**
> - BTC का भाव हमेशा किसी न किसी thousand के पास होता है। 85k पर किसी thousand से अधिकतम दूरी 0.6% है, 20k पर 2.5%।
> - इसलिए "पास होना" अपने-आप में सबूत नहीं है।
> - असली संकेत **reaction** था: wick level के पार गई और close वापस आया। इसका base rate सैकड़ों दिनों पर नापना होगा (§6)।

## 3. Rules जो ज़मीन पर test हुए (सिर्फ़ बंद candles; futures net %)

| Rule | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | Trades | जीते | **कुल net** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1: bias + prior-close rejection | +1.370 | n/a | n/a | — | — | — | n/a | n/a | n/a | n/a | 1 | 1 | +1.37 |
| **H2 (strict):** key level / round thousand का sweep, उसी candle में close वापस, अगली candle पुष्टि; SL wick −0.25%; TP 2R | — | **+2.054** | — | **+1.356** | — | **+1.651** | −0.659, +1.256 | **−0.580** | **+0.377** | — (miss) | 7 | 5 | **+5.455** |
| **H2′:** H2 + "sweep candle या उससे पहली candle नया day low/high बनाए" | — | +2.054 | — | +1.356 | — | +1.651 | +1.256 | **0 (कोई trade नहीं)** | +0.377 | — | 5 | 5 | **+6.694** |
| **H2′-c:** H2′ + पुष्टि अगली **2** candles में | — | +2.054 | — | +1.356 | — | +1.651 | +1.256 | 0 | +0.377 | **+1.914** | 6 | 6 | **+8.608** |
| H2′-c + **Q1** (पहले 8 घंटे की range < 1% हो तो दिन छोड़ो) | — | +2.054 | — | +1.356 | — | +1.651 | +1.256 | skip | skip | +1.914 | 5 | 5 | **+8.231** |
| F1: failed breakout (close पार, अगली candle वापस) | n/a | n/a | n/a | n/a | **+1.508** | n/a | n/a | n/a | n/a | n/a | 1 | 1 | +1.51 |
| K1: round thousand पर > 50% wick rejection | n/a | n/a | n/a | — | n/a | **+1.508** | n/a | — | — | n/a | 1 | 1 | +1.51 |
| H3: long bias + prior-high breakout, exit day close | n/a | n/a | **+6.863** | n/a | n/a | n/a | +0.727 | n/a | n/a | n/a | 2 | 2 | +7.59 |
| **फँसाने वाले:** naive breakout / उल्टे bias में stop-entry | −1.09 (D1) | | | −0.474 (D4, S1′) | −1.09 (D5) | | | | | | 3 | 0 | −2.65 |

("—" = rule ने trade नहीं लिया; "n/a" = rule उस दिन लागू नहीं था। हर नंबर उस दिन के log और check में है।)

## 4. Exit की सीख

| दिन का प्रकार | 2R target | Day-close (time) exit |
|---|---|---|
| **Trend दिन** (3, 7, 10) | Day 3: 2.90%; Day 10: 1.91% | Day 3: **6.86%**; Day 10: **3.57%** |
| **Range दिन** (2, 4, 6, 9) | ✅ target सही (2.05, 1.36, 1.65) | Day 9: target पहुँचा ही नहीं → time exit +0.38 |

- **एक ही fixed exit दोनों तरह के दिनों में गलत होगा।**
- **Exit का फ़ैसला day-type से होना चाहिए।** संकेत: पहले 8 घंटे की range बड़ी हो (Day 3: 5.6%), या पिछले दिन का extreme जल्दी टूटे।
- **Day 4 की सीख:** target **level से थोड़ा पहले** रखना चाहिए। Exact level वाला target $2 से चूक गया।

## 5. Formula: hypothesis (अभी साबित नहीं)

**"Level reaction" formula (H2′-c + Q1 + day-type exit):**
1. **Q1 (कब trade नहीं करना):** 00:00–08:00 UTC की range < 1% हो, तो उस दिन trade नहीं।
2. **Levels:** round thousands (BTC/USDT के हर 1,000 USDT वाले level, जैसे 66,000 या 70,000), पिछले दिन का high/low, 7-दिन का high/low।
3. **Long entry:**
   - एक 15m candle level के **नीचे wick** करे और **उसी candle में level के ऊपर बंद** हो;
   - वह candle, या उससे ठीक पहले वाली, **दिन का नया low** हो;
   - अगली **2** candles में एक bullish close आए;
   - तब अगली candle के open पर entry।
4. **Short:** इसका mirror (level के ऊपर wick, close नीचे, नया day high)।
5. **SL:** sweep का extreme ∓ 0.25%।
6. **Exit:**
   - पहले 8 घंटे की range ≥ 3% हो, या entry के बाद पिछले दिन का extreme टूटे → trend दिन → **दिन के close तक hold**;
   - वरना **2R target**, level से 0.1% पहले।
7. **दिशा:** level reaction से तय होती है, पहले से तय bias से नहीं।

**10 दिनों पर (in-sample, यानी इन्हीं दिनों को देखकर बना):** 5 trades, 5 जीत, कुल **+8.2% net**।

## 6. यह अभी साबित क्यों नहीं, और आगे क्या (ईमानदारी से)

1. **Overfitting का खतरा:**
   - H2′, H2′-c और Q1, तीनों **इन्हीं 10 दिनों को देखकर** बने हैं।
   - Day 7 और Day 8 की हार देखकर H2′ बना, और Day 10 का miss देखकर H2′-c।
   - इन्हीं दिनों पर उनका 100% जीतना स्वाभाविक है। यह सबूत **नहीं** है।
2. **Round-number का base rate** नापना बाकी है (§2)।
3. **अगला कदम (आपकी हाँ पर):** इसी formula को शब्दशः pre-register करके lock करना, फिर सभी ~2,465 दिनों (2020–2026) पर चलाना:
   - ये 10 दिन बाहर रहेंगे;
   - D/V/H split होगा;
   - random control और bench के सारे gates लगेंगे;
   - daily, monthly और yearly reports बनेंगी।
4. Batch 1 वाला bench अभी चल रहा है। यह formula उसके बाद एक अलग batch ("manual-derived") के रूप में test होगा।

## 7. जाँच ने पकड़ी मेरी गलतियाँ (सब सुधारी गईं, हर दिन के log में दर्ज)

1. **Day 1:** Asia low का समय (07:15 → 07:20); R3 का "सुबह का high" (9,627.52 → 9,671.12)।
2. **Day 2:** TP वाली 5m bar का समय (12:05 → 12:10)।
3. **Day 3:** 01:30 से पहले का high (29,462.69 → 29,470.61)।
4. **Day 4:** entry के बाद का सबसे निचला भाव (19,134.10 → 19,067.57)।
5. **Day 5:** TP वाली bar का समय (18:35 → 18:30)।
6. **Day 8:** SL वाली bar का समय (19:05 → 19:10)।

किसी भी सुधार से किसी rule का नतीजा नहीं बदला। पर ये दिखाती हैं कि **हर नंबर की जाँच ज़रूरी है।**

*मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।*
