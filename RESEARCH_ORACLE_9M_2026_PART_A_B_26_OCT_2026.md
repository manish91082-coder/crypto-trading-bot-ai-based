# BTC 2026 के 9 महीने (1 जनवरी – 30 सितंबर): हर दिन का ground-truth oracle, और 10 दिनों वाले formula की पहली असली जाँच (26 अक्टूबर 2026)

> **सार:**
> - **Part A:** 273 दिनों का oracle dataset बन गया है। हर दिन, हर timeframe और हर profitable trade दर्ज है। Independent verifier की सभी जाँचें पास हुईं।
> - **Part B:** 10 दिनों से बना formula (H2′-c) 2026 के 272 नए दिनों पर **फ़ेल** हुआ। पाँचों variants घाटे में रहे।
> - **10 दिनों का "round number पर पलटाव" वाला अंदाज़ा 9 महीनों के data में नहीं टिका।**
> - पूरी तरह random entries इससे भी बुरी रहीं। इससे एक नया, test करने लायक संकेत मिला (§5)।
>
> **Evidence:**
> - Protocol `logs/oracle_9m_2026/ORACLE_9M_PROTOCOL_PREREGISTERED.md`, SHA `2c68bbc4…`, कोई नतीजा देखने से पहले lock किया गया।
> - Code `src/research/oracle_9m.py` (SHA e1e44e3e…)।
> - Verifier `src/audits/verify_oracle_9m.py` (SHA aa5c6706…): **ALL PASS** (`verify_output.txt`)।
> - Output SHAs: `OUTPUT_SHA256.txt`।
> - यह काम Batch 1 (methods bench) से पूरी तरह अलग है।

## 1. Data (ज़मीन पर जाँचा)

- **273 दिन:** 5m के 78,624 bars, कोई missing या duplicate नहीं।
- 5m से बने 15m, 1h और 1d, अपनी-अपनी files से **हूबहू मिले** (verifier K1)।
- **2026 का 1m data नहीं है** (raw 1m के timestamps 2024 के बाद खराब हैं), इसलिए सबसे छोटा timeframe 5m है।
- **Fees** सिर्फ़ `deploy/fees.json` से:
  - futures 0.046% प्रति side, यानी 0.092% round trip;
  - spot 0.085% प्रति side, यानी 0.17% round trip।
- **2026-02-13** (10 दिनों वाली study का Day 10) हर आँकड़े से बाहर रखा गया। इसलिए आँकड़े **272 दिनों** पर हैं।

## 2. Part A: Oracle (hindsight का माप; यह strategy नहीं है)

> यह सिर्फ़ यह नापता है कि बाज़ार में **कितना था**। Real time में इतना पकड़ना असंभव है।

### 2a. प्रति दिन उपलब्ध move (median, 272 दिन)

| Timeframe | सबसे अच्छा 1 long (gross) | सबसे अच्छा 1 short (gross) | **Maximum possible run** (futures, fees के बाद, कई trades) | उस run में trades | Spot, सिर्फ़ long (fees के बाद) |
|---|---|---|---|---|---|
| 5m | 1.87% | 1.94% | **14.5%** | 60 | 5.4% |
| 15m | 1.77% | 1.81% | **9.9%** | 30 | 3.9% |
| 30m | 1.68% | 1.68% | 7.6% | 17 | 3.0% |
| 1h | 1.51% | 1.53% | 5.6% | 10 | 2.3% |
| 4h | 1.11% | 1.18% | 2.8% | 3 | 1.1% |

- **5m extremes पर** (दिन के low पर खरीद, high पर बिक्री): median **2.04% net**। Long और short में से बेहतर लें तो median 2.83% net।
- **"Maximum possible run":** fees घटाकर पूरे दिन के optimal trades का कुल। यह exact DP से निकला।
  - Verifier ने इसे plain-loop DP से दोबारा गिना।
  - 300 छोटे हिस्सों पर हर संभव combination गिनकर भी जाँचा: 0 mismatch।
- Optimal set के **43,863 trades** (हर trade का entry, exit, MAE, MFE) `oracle_trades.parquet` में हैं।
  - 15m पर एक आम optimal trade: gross 0.32%, 2 bars, MAE 0.05%।
  - मतलब "perfect" trades बहुत छोटे और तुरंत सही होने वाले हैं। Real time में इन्हें पहचानना ही असली समस्या है।
- **Day-type:** TREND 76, MIXED 105, RANGE 91 दिन।
  - पहले 8 घंटे की range का median 1.40%, पूरे दिन का 2.95%।
  - 48% दिनों में low पहले बना और high बाद में।
- **दिन का low किस घंटे (UTC) बना:**
  - सबसे ज़्यादा **00:00 वाले घंटे** में: 48 दिन;
  - फिर **13–15 UTC** (US session) में: 56 दिन।
  - High भी 00 UTC (31 दिन), 14–15 UTC (39) और 21–23 UTC (43) में ज़्यादा बना।

### 2b. 10 दिनों वाले अंदाज़े की जाँच (base rate)

| अंदाज़ा (10 दिनों से) | 9 महीनों का data | नतीजा |
|---|---|---|
| "दिन का low/high round thousand के पास बनता है" | Low की nearest thousand से दूरी का median 0.38%, high का 0.36%। अगर level का कोई असर न हो, तो उम्मीद 0.355% की होती | **कोई खिंचाव नहीं।** Round thousand के पास बनना संयोग जितना ही है |
| "Sweep-reclaim, दिन का turn दिखाता है" | 4,091 bullish sweep events में से सिर्फ़ 2.5% का low दिन का low बना। "नया low + पुष्टि" वाले 398 में से 23.4% | Filter से सुधार है, पर 4 में से 3 बार दिन का low बाद में और नीचे बना |

## 3. Part B: formula v1 (H2′-c) की frozen जाँच, 272 नए दिन

**नियम:** 10 दिनों वाली report §5 के अनुसार, बिना बदले। 15m sweep-reclaim, फिर नया day extreme, फिर 2 candles में पुष्टि। SL sweep extreme ∓ 0.25%, TP 2R, नहीं तो day close पर exit।

**मेरी पुरानी गलती, जो अब पकड़ी गई:**
- 10 दिनों वाली table में Q1 filter (पहले 8 घंटे की range < 1% हो तो skip) ने Day 9 का 00:30 वाला trade हटा दिया था।
- पर Q1 08:00 बजे ही पता चलता है।
- इसलिए वह "+8.23%" lookahead वाला था।
- यहाँ Q1 का real-time रूप test हुआ: 08:00 से पहले entry नहीं।

| Variant | Trades | जीत % (95% दायरा) | Break-even जीत % | प्रति trade net | **कुल net (9 महीने)** | Positive महीने | सबसे बुरा महीना | लगातार हार |
|---|---|---|---|---|---|---|---|---|
| V1-A (बुनियादी) | 465 | 33.8% (29.6–38.2) | 36.8% | −0.177% | **−82.5%** | 0/9 | −19.6% | 14 |
| V1-B (+ Q1 real-time) | 194 | 39.7% (33.1–46.7) | 36.3% | −0.139% | **−27.1%** | 2/9 | −11.2% | 11 |
| V1-C (+ Q1 + day-type exit) | 191 | 39.8% (33.1–46.9) | 36.3% | −0.141% | **−26.9%** | 2/9 | −11.2% | 11 |
| V1-AC (day-type exit, बिना Q1) | 441 | 32.4% (28.2–36.9) | 36.9% | −0.168% | **−74.3%** | 0/9 | −16.4% | 14 |
| V1-S (spot, सिर्फ़ long) | 110 | 40.0% (31.3–49.3) | 38.8% | −0.195% | **−21.4%** | 1/9 | −5.8% | 8 |

**पास होने की 4 शर्तें** (पहले से तय):
1. कुल net > 0;
2. जीत % के दायरे की निचली सीमा break-even से ऊपर;
3. 9 में से कम से कम 5 महीने positive;
4. random control share ≤ 0.05।

**फ़ैसला: पाँचों variants फ़ेल।** शर्तें 1, 2 और 3 तीनों टूटीं।

### महीने-दर-महीने (net %, futures)

| महीना | BTC का महीना | V1-A | V1-B | V1-C | V1-AC | V1-S |
|---|---|---|---|---|---|---|
| जनवरी | −9.9% | −8.36 | −3.29 | −3.29 | −6.52 | −0.44 |
| फ़रवरी | −17.6% | −4.18 | −7.84 | −8.51 | −0.58 | −5.53 |
| मार्च | +3.0% | −16.53 | −1.96 | −3.02 | −16.44 | −3.09 |
| अप्रैल | +11.7% | −3.12 | **+7.77** | **+7.77** | −8.02 | **+4.16** |
| मई | −3.3% | −7.14 | −2.30 | −0.39 | −5.84 | −4.51 |
| जून | −22.0% | −3.77 | **+0.51** | **+0.52** | −3.34 | −2.79 |
| जुलाई | +7.4% | −9.15 | −2.61 | −2.61 | −12.44 | −0.47 |
| अगस्त | +23.1% | −10.60 | −6.18 | −6.18 | −6.24 | −3.00 |
| सितंबर | +6.9% | −19.63 | −11.15 | −11.15 | −14.89 | −5.75 |

(BTC का महीना = उस महीने के दिनों के daily returns का जोड़, Day 10 को छोड़कर।)

**पूरी जानकारी:**
- हर दिन की entry (बिना trade वाले दिन 0 के साथ): `v1_daily.csv`, 272 × 5 rows;
- हर trade: `v1_trades.csv`।
- Verifier ने हर trade, हर दिन और हर महीने का जोड़ अपने अलग code से दोबारा बनाकर मिलाया (K6)।
- Long और short दोनों तरफ़ घाटा रहा। उदाहरण के लिए V1-B: long −13.5%, short −13.6%।

## 4. 10 दिन में यह "5 में से 5 जीत" क्यों दिखा था?

1. **Formula उन्हीं 10 दिनों को देखकर बना था** (in-sample)। Day 7/8 की हार देखकर H2′ जोड़ा गया, Day 10 के miss पर H2′-c।
2. **हाथ वाले log में हर दिन सिर्फ़ पहला signal देखा गया।** मशीन ने वही नियम पूरे दिन लागू किया।
   - उदाहरण: Day 10 पर मशीन ने +1.914% वाला long हूबहू वैसा ही पकड़ा।
   - पर उसी दिन 16:00 का short भी लिया, जिसका नतीजा −0.33% रहा।
3. **Q1 में lookahead था** (§3)।

**सीख:** हाथ से 10 दिन देखकर बना "perfect" formula 272 नए दिनों पर नहीं टिका। इसीलिए हर formula को lock करके अनदेखे data पर जाँचना ज़रूरी है।

## 5. एक नया संकेत (अभी साबित नहीं; अगले चरण में test होगा)

- **Random control** में हर seed पर entry का समय random था, पर side, SL की दूरी (R%) और exit के नियम v1 जैसे ही थे।
- यह v1 से भी **बहुत बुरा** रहा। V1-A के बराबर trades पर random का औसत कुल **−164%** रहा, जबकि v1 का −82%।
- यानी v1 का entry timing random से बेहतर था (control share 0.000), पर इतना नहीं कि fees के बाद कमा सके।
- **Diagnostic** (lock नहीं, सिर्फ़ जाँच के लिए; seed 0):
  - असली 2026 BTC पर random entry, ~0.87% SL और 2R TP वाले trades ने औसतन **−0.22% gross** दिया, fees से पहले ही।
  - बिना drift वाले synthetic random walk पर यही simulation ≈ 0 (+0.07% ± 0.02) देता है।
  - इसलिए यह घाटा simulation की गलती नहीं है।
  - मतलब: **2026 के BTC में पास रखा SL (~0.9%) छूने के बाद भाव अक्सर वापस आता है, और 2R target तक कम पहुँचता है।** Exits: SL 264, TP 57, EOD 144।
- **Part C में test होने वाले सवाल:**
  - SL चौड़ा करने से क्या होता है?
  - SL हटाकर time exit रखने से?
  - "Stop-hunt के बाद उल्टी दिशा" वाली entry से?
- अभी यह सिर्फ़ एक संकेत है, कोई दावा नहीं।

## 6. Files (सब `logs/oracle_9m_2026/` में; column-by-column विवरण `SCHEMA.md` में)

| File | क्या है |
|---|---|
| `oracle_day.parquet` | 273 दिन: OHLC, timing, day-type, A1 perfect long/short, levels, level-distance |
| `oracle_tf.parquet` | दिन × 5 timeframes: A2 best single trade, A3 maximum run (FUT / SPOT / MAKER) |
| `oracle_trades.parquet` | Optimal sets के 43,863 trades, MAE/MFE के साथ |
| `sweep_events.parquet` | 8,150 sweep-reclaim events, forward labels के साथ |
| `v1_trades.csv`, `v1_daily.csv`, `v1_monthly.csv`, `V1_RESULTS.json` | Part B |
| `run_log.txt`, `verify_output.txt`, `CODE_NOTES.md`, `input_manifest.csv`, `OUTPUT_SHA256.txt` | Log और सबूत |

## 7. आगे का plan (protocol §5–§7)

1. **Part E:** हर हफ़्ते का एक दिन, कुल 40 दिन (`manual/selected_days.txt`, seed 20261027)। इनका हाथ से (AI reasoning) विश्लेषण पहले जैसे step log और calculator जाँच के साथ होगा। हर दिन के oracle trades भी साथ रहेंगे।
2. **Amendment 1 (SHA lock):** direction, entry और exit methods की पूरी सूची, उनकी exact परिभाषाओं के साथ। इसमें §5 वाले सवाल भी होंगे।
3. **Part C:** 2026 पर ranking: entry की दूरी, capture %, exit giveback, net प्रति दिन (95% दायरे की निचली सीमा से sort), random control, और daily/monthly entries।
4. **Part D:** top methods को sealed 2020–2025 पर एक बार चलाना। फ़ैसला वहीं होगा।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
