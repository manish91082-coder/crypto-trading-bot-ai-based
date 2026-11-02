# 9 महीने की study, Part C (methods की ranking, 2026) और Part D (अनदेखे 2020–2025 पर अंतिम जाँच): 26 अक्टूबर 2026

> **सीधा नतीजा:**
> - **एक भी method fees के बाद profit नहीं देता।** इनमें 9 direction methods, 8 entry triggers और 100 पूरे नियम (entry × direction × SL × exit) शामिल हैं।
> - 2026 पर 100 में से 0 नियम पास हुए।
> - Locked नियम के हिसाब से 2020–2025 पर भेजा गया एकमात्र config भी 6 में से 6 साल घाटे में रहा।
> - पिछली report का "mirror trade" वाला संकेत मेरे random-control design की lookahead गलती निकला। मैंने उसे वापस ले लिया है (§2)।
>
> **Evidence:**
> - **Amendment 1** (SHA `e68da96c…`): methods की सूची, ranking के नियम और Part D के gates, सब Part C चलने से पहले lock।
> - **Amendment 2** (SHA `4c46612c…`): Part D का record, 2020–2025 का कोई नतीजा देखने से पहले lock।
> - **Lock के बाद एक code बदलाव:** binomial test का overflow ठीक किया। यह `AMENDMENT_2_CODE_CHANGES_AFTER_LOCK.md` में दर्ज है, और इसके बाद Part C के outputs byte-for-byte वही रहे।
> - **Verifiers, सब ALL PASS** (independent, plain loops):
>   - `verify_oracle_9m_c.py`: 2,421 calls, 13,647 events, 195,840 trades दोबारा बनाए;
>   - `verify_oracle_9m_d.py`: 12,876 trades दोबारा बनाए, और हर दिन, महीने और साल का जोड़ मिलाया।

## 1. Part C: 2026 पर ranking (in-sample, 272 दिन)

### C1. Direction: "दिन किस तरफ़ जाएगा", पहले से बताने के तरीके

| Rank | Method | फ़ैसले का समय (UTC) | सही % | 95% दायरा | p (50% के मुकाबले) |
|---|---|---|---|---|---|
| 1 | पिछले दिन का close उसकी range के ऊपरी आधे में → long | 00:00 | 53.3% | 47.4–59.2 | 0.30 |
| 2 | पिछले दिन की दिशा follow करो | 00:00 | 51.8% | 45.9–57.7 | 0.59 |
| 3 | पिछला close 7-दिन के बीच से ऊपर → long | 00:00 | 50.7% | 44.8–56.6 | 0.86 |
| 4 | Asia session (00–08) की दिशा follow करो | 08:00 | 50.4% | 44.5–56.3 | 0.95 |
| 5 | Asia session को fade करो | 08:00 | 49.6% | 43.7–55.5 | 0.95 |
| 6 | पहले घंटे की दिशा follow करो | 01:00 | 49.3% | 43.4–55.2 | 0.86 |
| 7 | हमेशा long | 00:00 | 48.9% | 43.0–54.8 | 0.76 |
| 8 | पिछले दिन को fade करो | 00:00 | 48.2% | 42.3–54.1 | 0.59 |
| 9 | Sweep-reclaim (10 दिनों वाला) | पुष्टि के बाद | 47.8% | 41.6–54.0 | 0.52 |

**नतीजा:** किसी भी method का दायरा 50% से साफ़ ऊपर नहीं गया। इन 9 में से कोई तरीका दिन की दिशा का coin-flip से बेहतर अंदाज़ा नहीं देता।

### C2. Entry का पल: entry के बाद पहले +1% आता है या −1%? (4 घंटे के अंदर)

Fees के बाद बराबरी के लिए 54.6% चाहिए।

| Rank | Trigger | Events | पहले +1% (%) | 95% दायरा | Perfect entry से दूरी (median) |
|---|---|---|---|---|---|
| 1 | हर sweep, अगली candle पर | 7,219 | 49.7% | 48.0–51.4 | 1.30% |
| 2 | हर 4 घंटे, पिछले 4 घंटे की दिशा में | 1,632 | 50.7% | 46.7–54.7 | 1.26% |
| 3 | हर 4 घंटे, पिछले 4 घंटे के उल्टे | 1,632 | 49.2% | 45.2–53.2 | 0.83% |
| 4 | पहले घंटे की range का breakout | 271 | 53.8% | 42.9–64.3 | 1.16% |
| 5 | Sweep + पुष्टि (v1 वाला) | 673 | 48.0% | 42.3–53.7 | 0.94% |
| 6 | Random | 1,632 | 46.1% | 42.2–50.0 | 1.05% |
| 7 | 08:00 के बाद नए day extreme को fade करो | 317 | 49.7% | 41.6–57.8 | 0.48% |
| 8 | पहले घंटे के breakout को fade करो | 271 | 46.3% | 35.8–57.1 | 0.73% |

**नतीजा:** एक भी trigger 54.6% की बराबरी तक नहीं पहुँचा। सबके नतीजे लगभग 50%, यानी coin-flip, के आसपास रहे।

### C3. पूरे नियम: 100 FUT configs और 20 spot configs

**Config के हिस्से:**
- **Entry:** दिन में 6 entries, हर 4 घंटे पर।
- **Direction (5 विकल्प):** हमेशा long, हमेशा short, पिछले 4 घंटे को fade करो, उसे follow करो, या random।
- **SL (4 विकल्प):** 0.5%, 0.8%, 1.2%, या पिछले दिन की range का 0.33 गुना।
- **TP/SL अनुपात (5 विकल्प):** 1:2, 1:1, 2:1, 0.5:1, या बिना SL।

**Best 5** (पूरी table: `logs/oracle_9m_2026/part_c/c3_ranking.csv`):

| Rank | Config | जीत % | प्रति trade net | 9 महीनों का कुल | Positive महीने |
|---|---|---|---|---|---|
| 1 | Fade, SL 0.5%, TP 1R / SL 2R | 56.4% | −0.064% | −104% | 1/9 |
| 2 | Fade, SL 0.5%, TP 1R, बिना SL | 58.8% | −0.063% | −102% | 1/9 |
| 3 | Fade, SL 1.2%, TP 0.5R / SL 1R | 53.7% | −0.068% | −111% | 1/9 |
| 4 | हमेशा short, SL 0.5%, TP 1R / SL 2R | 54.2% | −0.065% | −105% | 1/9 |
| 5 | Fade, SL 0.8%, TP 0.5R / SL 1R | 59.0% | −0.074% | −121% | 0/9 |

**सबसे अहम आँकड़ा:**
- 100 FUT configs का औसत **gross** (fees से पहले) प्रति trade सिर्फ़ **+0.002%** है, यानी लगभग शून्य।
- एक round trip की fee 0.092% है।
- इसलिए हर config का net लगभग "−fee" रहा: −0.06% से −0.12% प्रति trade।
- **कोई भी config 9 में से 2 से ज़्यादा महीने positive नहीं रहा।**
- 95% दायरे की निचली सीमा 100 में से **0** configs की > 0 रही।

**Exits की ranking** (20 cells का औसत net प्रति trade):

| Rank | Exit | Net प्रति trade |
|---|---|---|
| 1 | TP 1R, बिना SL | −0.085% |
| 2 | 0.5:1 | −0.086% |
| 3 | 1:2 | −0.087% |
| 4 | 1:1 | −0.093% |
| 5 | 2:1 | −0.100% |

- सबके बीच का फ़र्क सिर्फ़ 0.015% है।
- **Exit बदलने से जीत % बदलता है, पर औसत नहीं बदलता।** यह गणित का नियम है: अगर entry में दिशा की कोई जानकारी नहीं, तो कोई exit उसे profit में नहीं बदल सकता।

**Spot (सिर्फ़ long):** सारे 20 configs और खराब रहे, −0.17% से −0.20% प्रति trade, क्योंकि spot की fee ज़्यादा है।

## 2. मेरी एक गलती: "mirror trade" वाला संकेत वापस लिया

**पिछली बात:** मैंने पिछली report में कहा था कि random-time trades −0.26% gross देते हैं, इसलिए उल्टा trade +0.169% net देगा।

**असली वजह:**
- Part B के random control में हर trade की **दिशा v1 से ली गई थी।** v1 को वह दिशा दिन में बाद में होने वाले sweep से मिलती थी, जैसे "नया day low"।
- पर random entry का समय **उस sweep से पहले** भी हो सकता था।
- यानी random long ऐसे दिनों पर लगाए गए जिनके बारे में पहले से पता था कि आगे भाव गिरेगा। यह भविष्य की जानकारी थी।

**जाँच (20 seeds):**

| Random entry का समय | Trades | औसत gross |
|---|---|---|
| Sweep से पहले | 3,194 | **−0.715%** |
| Sweep के बाद | 6,106 | **−0.008%** (≈ 0) |

**नतीजा:**
- "Mirror edge" असल में था ही नहीं।
- Part B के random-control वाले आँकड़े भी अमान्य हैं।
- Part B का फ़ैसला (v1 फ़ेल) फिर भी वही है, क्योंकि बाकी 3 शर्तें अपने-आप टूटी थीं।
- यह सब `DIAGNOSTIC_RANDOM_BARRIER.md` (Diagnostic 3) में दर्ज है।

## 3. Part D: अनदेखे 2020–2025 पर अंतिम जाँच

**Data:**
- 2020-01-08 से 2025-12-31 तक, **2,146 दिन।**
- **बाहर रखे गए 39 दिन:**
  - 9 manual-study के दिन;
  - 15 दिन जिनमें 5m bars पूरे नहीं थे;
  - वे 15 दिन जिनसे पहले वाला दिन अधूरा था।

**Locked selection rule का नतीजा:** 2026 पर कोई भी config पास नहीं हुआ था, इसलिए कोई config नहीं चुना गया। सिर्फ़ पहले से घोषित "lead" (random दिशा, SL 0.8%, TP 1R / SL 2R) चला। Amendment 1 के अनुसार इसे हर हाल में चलना था।

| | Trades | जीत % | प्रति trade net | Positive महीने | सालाना net (%) | फ़ैसला |
|---|---|---|---|---|---|---|
| Lead | 12,876 | 50.6% | −0.091% | 5/72 | 2020 −145, 2021 −166, 2022 −194, 2023 −269, 2024 −176, 2025 −218 | **फ़ेल** (0/6 साल) |

- **Gross ≈ 0** रहा (+0.001% प्रति trade)। 6 साल में भी नतीजा वही: fees ही पूरा घाटा हैं।

**संदर्भ के लिए:**
- **C1 का top method** (पिछले close की range में जगह): 2026 पर 53.3% सही था, पर 2020–2025 पर **45.9%** रहा।
  - यानी दिशा ही **पलट गई** (p = 0.0002)।
  - जो नियम एक दौर में ऊपर और दूसरे में नीचे जाए, वह भरोसे लायक formula नहीं है।
- **C2 का top trigger** (हर sweep): 2020–2025 पर 49.5%, यानी coin-flip।

## 4. 9 महीनों का पूरा हिसाब: क्या साबित हुआ

1. **Calculation सही है।** हर चरण का अलग verifier है, हर trade दोबारा बनाया गया, 0 mismatch।
2. **बाज़ार में move बहुत है, पर पहले से दिखता नहीं।**
   - Hindsight में 15m पर रोज़ ~9.9% उपलब्ध था।
   - पर सिर्फ़ भाव (price) पर बने नियमों का gross लगभग 0 रहा, 2026 में भी और 2020–2025 में भी।
3. **"ज़्यादा trades = ज़्यादा कमाई" उल्टा पड़ता है।**
   - Gross 0 हो, तो हर trade fees जितना घाटा जोड़ता है।
   - दिन में 6 trades × 0.09% = −0.55% रोज़।
4. **"Perfect" formula नहीं बन सकता।** इस data पर 9 direction, 8 entry, 5 exit और 100 पूरे नियम test हुए, साथ में पिछली study के 990 configs। BTC के भाव पर कोई ऐसा नियम नहीं मिला जो fees के बाद टिके।

## 5. फिर लक्ष्य कैसे पूरा होगा (ज़मीनी सच)

जो लोग लगातार कमाते हैं, वे ज़्यादातर chart pattern से नहीं कमाते। उनके पास इनमें से कोई एक चीज़ होती है:

| स्रोत | हमारे पास क्या है | अगला ज़मीनी कदम |
|---|---|---|
| **Fees कम करना** (maker orders, VIP या rebates) | Maker cost 0.028% प्रति side पर भी gross 0 वाला नियम घाटे में रहेगा | फ़ायदा तभी, जब पहले कोई ऐसी entry मिले जिसका gross > 0 हो |
| **भाव के अलावा जानकारी:** funding rate, open interest, liquidations, order-book flow, on-chain | अभी हमारे पास सिर्फ़ OHLCV है | Binance की public history download करनी होगी, **आपकी अनुमति से**। फिर उसी discipline (lock → 2026 ranking → sealed test) से जाँच होगी |
| **लंबे समय का trend / hold** (हफ़्ते या महीने) | पिछले 1D और ECO काम में यह पहले से है (demo पर चल रहा है) | ECO का TC gate (~09 नवंबर) और Sleeve A forward के नतीजे |
| **Structural carry** (funding, basis) | Spot + futures वाली पिछली research | उसी research को इसी discipline से re-test करना |

**अभी चल रहा काम:**
- Batch 1 (189 indicator configs, 2020–2026) अभी भी चल रहा है। Verifier पास होने पर उसकी report दूँगा।
- 40 manual दिनों (Part E) से अब सिर्फ़ नई hypotheses निकल सकती हैं। उनकी जाँच भी इसी तरह lock होकर होगी।

## 6. Files

| Path | क्या है |
|---|---|
| `logs/oracle_9m_2026/part_c/` | `c1_calls.csv`, `c1_ranking.csv`, `c2_events.parquet`, `c2_ranking.csv`, `c3_trades.parquet` (195,840 trades), `c3_daily.parquet` (120 configs × 272 दिन, हर दिन की entry), `c3_monthly.csv`, `c3_ranking.csv`, `c3_exit_ranking.csv`, `C_RESULTS.json`, `verify_output.txt`, `OUTPUT_SHA256.txt` |
| `logs/oracle_9m_2026/part_d/` | `d_trades.parquet`, `d_daily.parquet` (2,146 दिन), `d_monthly.csv`, `D_RESULTS.json`, `d_c1_context.csv`, `d_c2_context.csv`, `verify_output.txt`, `OUTPUT_SHA256.txt` |
| `logs/oracle_9m_2026/` | `AMENDMENT_1_*`, `AMENDMENT_2_*`, `DIAGNOSTIC_RANDOM_BARRIER.md` |

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
