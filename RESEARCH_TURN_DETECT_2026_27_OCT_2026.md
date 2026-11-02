# TURN-2026: क्या दिशा (turn) को "पुष्टि" से पहले पकड़ा जा सकता है? BTC, जनवरी–सितंबर 2026 (27 अक्टूबर 2026)

**आपका सवाल:**
- Indicators और candles दिशा देर से बताते हैं; market पहले ही मुड़ चुका होता है।
- तो दिशा पहले कैसे पकड़ें? सिर्फ़ 9 महीने के data पर देखें।
- सारे timeframes, seconds और minutes के बीच का "छिपा" timeframe, spot, futures, order book, long/short, सब देखें।

**Data की मेरी समझ:**
- आपने "2022" कहा, पर साथ में "जनवरी से अभी सितंबर तक" और "9 महीने" भी कहा। इसलिए यह study **2026-01 … 2026-09** पर है।
- 2022 चाहिए हो तो बताइए, उसका अलग protocol बनेगा।

> **एक पंक्ति में नतीजा:**
> - BTC पर turn को पुष्टि से पहले पकड़ने का कोई ऐसा तरीका नहीं मिला जो fee के बाद कमाई दे।
> - Jan–May में तरीके खोजे गए (DISC)। Jun–Sep (HOLD) पर भेजने लायक एक भी candidate नहीं निकला।
> - तीन असली, पर छोटी, चीज़ें मिलीं:
>   - **(1)** seconds में momentum (1–20 सेकंड);
>   - **(2)** 5 मिनट से 8 घंटे तक हल्का उल्टा चलना (mean reversion);
>   - **(3)** 0.5% वाले छोटे turns में 6 features का स्थिर असर, जो HOLD पर भी वैसा ही रहा।
>
>   तीनों fee (round trip 0.092% taker / 0.056% maker) से बहुत छोटी हैं।

## सबूत (discipline)

| चीज़ | जगह / SHA |
|---|---|
| Protocol (कोई भी नंबर देखने से पहले lock, 11:59:39 UTC) | `logs/turn_detect_2026/TURN_PROTOCOL_PREREGISTERED.md`, SHA `0d2fece2…` |
| Code | `src/research/turn_2026.py` (`f405ad51…`) |
| Code notes (run से पहले की सारी परिभाषाएँ + run के बाद की 2 बातें) | `logs/turn_detect_2026/CODE_NOTES.md` |
| Independent verifier | `src/audits/verify_turn_2026.py`: **DISC 13/13, HOLD 14/14 PASS** (`verify_disc_output.txt`, `verify_hold_output.txt`) |
| HOLD सिर्फ़ एक बार खोला | `HOLD_OPENED.txt`: 13:44:03 UTC, candidates file (`hold_candidates.json`, 13:39:16 UTC) बनने के बाद, और उसका SHA मिलता है |
| रोज़ और महीने का हिसाब (हर दिन, 151/151) | `daily_disc.csv`, `monthly_disc.csv` |

**Verifier ने अपने अलग code से क्या दोबारा किया:**
- ZigZag pivots: हूबहू मिले।
- T1 events और completion: हूबहू मिले। अपना null 0.5552 बनाम main 0.5556 आया।
- Raw files से 300 feature values: 0 mismatch।
- 14 detector configs के trades अपने loops से: 0 mismatch।
- VR और AC1: मिले।
- Daily → monthly: पूरा मिलान।

**Run में आई दो बातें (छिपाई नहीं गईं):**
- पहला DISC run T2 में crash हुआ। जब turn का low पिछले महीने में हो, तो 1-second window खाली हो जाती थी (CODE_NOTES 18)। उसे ठीक करके पूरा DISC शुरू से दोबारा चलाया। T0/T1 के नंबर दोनों बार एक जैसे आए।
- CODE_NOTES 18 में लिखा समय UTC नहीं, IST था। यह note 19 में सुधारा गया है, और note 18 को बदला नहीं गया।

**Data की ईमानदार स्थिति:**
- 2026 के 1m/5m data पर पहले भी studies हुई थीं (oracle, green candle, fee map)। पर ये सवाल पहले कभी नहीं पूछे गए थे।
- Jun–Sep का 1-second data इसी study में पहली बार खुला।

## 0. "Null" क्या है, और यह क्यों ज़रूरी है (गणित का पैमाना)

- **तरीका:** हर 1-मिनट return का size वही रखा और उसकी दिशा (+/−) random कर दी। इससे वह BTC बनता है जिसकी volatility बिल्कुल असली है, पर दिशा की कोई जानकारी नहीं है।
- **इस null पर कोई भी तरीका दिशा पहले नहीं जान सकता।** इसलिए कोई तरीका तभी असली माना गया जब वह **असली BTC पर null से बेहतर** करे।
- **यह पैमाना ज़रूरी क्यों है:** unit test में pure random walk पर भी 0.5% के turn में "bounce के बाद turn पूरा होने" की दर 37% आई, जबकि सीधे गणित से 25% होनी चाहिए। वजह यह है कि 1-मिनट candle threshold से आगे निकल जाती है।
  - अगर हम 25% से तुलना करते, तो random walk भी "edge" दिखाता।
  - Null से तुलना करने पर यह धोखा पकड़ में आ जाता है।

## 1. T0: "देर से पुष्टि" की असली कीमत (Jan–May)

**Turn की पहचान:** ZigZag से। जब price अपने extreme से θ% उल्टा चल जाए, तब turn की "पुष्टि" मानी गई।

| θ (turn का size) | Turns | पुष्टि में देर (median) | पुष्टि तक चाल का कितना हिस्सा जा चुका (median) | पुष्टि के बाद turn follow करने वाला system, fee के बाद प्रति trade |
|---|---|---|---|---|
| 0.5% | 2,236 | 19 मिनट | 53% | −0.09% |
| 1% | 705 | 62 मिनट | 57% | −0.15% |
| 2% | 181 | 220 मिनट | 55% | −0.00% |
| 4% | 52 | ~21 घंटे | 53% | −0.19% |
| 8% | 14 | ~55 घंटे | 61% | −0.20% |

**आपकी बात सही है:** हर size के turn में, पुष्टि होने तक आधी से ज़्यादा चाल निकल चुकी होती है। उसके बाद बचा हिस्सा लगभग random है, इसलिए पुष्टि के बाद follow करना fee के बाद घाटा देता है।

## 2. T1: क्या bounce शुरू होने के बाद पता चलता है कि turn पूरा होगा?

**सवाल:** low से f × θ का bounce हो चुका है। अब price पूरा θ ऊपर जाएगा (turn पूरा), या पहले नया low बनाएगा?

| θ | f | DISC events | DISC: असली | DISC: null | DISC: p | HOLD: असली | HOLD: null | HOLD: p |
|---|---|---|---|---|---|---|---|---|
| 0.5% | 0.25 | 5,873 | 37.3% | 37.7% | 0.73 | 35.7% | 36.2% | 0.73 |
| 0.5% | 0.5 | 3,769 | 57.1% | 57.8% | 0.81 | 57.0% | 57.2% | 0.54 |
| 1% | 0.25 | 2,065 | 34.0% | 33.2% | 0.16 | 32.9% | 32.0% | 0.23 |
| 1% | 0.5 | 1,237 | 56.6% | 55.6% | 0.26 | 55.0% | 54.8% | 0.48 |
| 2% | 0.5 | 359 | 49.9% | 53.2% | 0.90 | 51.9% | 52.8% | 0.61 |
| 4% | 0.25 | 184 | 27.7% | 28.3% | 0.57 | **38.8%** | 27.5% | **0.00** |
| 4% | 0.5 | 95 | 53.7% | 52.7% | 0.42 | **65.5%** | 51.5% | **0.02** |
| 4% | 0.75 | 68 | 75.0% | 76.9% | 0.65 | **88.4%** | 75.8% | **0.00** |
| 8% | 0.5 | 29 | 44.8% | 49.7% | 0.66 | 29.4% | 50.8% | 0.94 |

(पूरी table, सभी 15 settings के साथ: `T1_completion_disc.csv`, `HOLD_T1_report.csv`)

- **DISC में सभी 15 settings random walk जितनी निकलीं।**
- **Fee के बाद 15 में से 14 settings घाटे में रहीं** (taker −0.08% से −0.68% प्रति trade)।
  - अकेला अपवाद 8%, f 0.75 है: सिर्फ़ 16 trades, +0.35% प्रति trade, पर दायरा −1.3% तक जाता है।
- **HOLD में एक नई बात दिखी:**
  - 4% वाले turns Jun–Sep में null से ज़्यादा बार पूरे हुए।
  - Verifier के अपने loop से यह हूबहू मिला: 98 / 58 / 43 events।
  - पर इसके पीछे सिर्फ़ **38 असली turns** हैं, और तीनों f उन्हीं को share करती हैं।
  - Jan–May में यही setting बिल्कुल random थी।
  - इसलिए यह एक **"उस दौर का बाज़ार"** (trending regime) वाला संकेत है, साबित edge नहीं।
  - Protocol के हिसाब से यह candidate नहीं है, सिर्फ़ report है। चाहें तो इसे आगे के data पर एक अलग locked forward-watch hypothesis की तरह देखा जा सकता है।

## 3. T2: bounce के पल पर कोई "symptom" जो turn पहले बता दे?

**20 features जाँचे गए (सब उसी पल तक के data से):**
- bounce की रफ़्तार और समय;
- पिछली गिरावट का size;
- volume ratio;
- taker buy/sell;
- open interest (OI) का बदलाव;
- premium;
- funding;
- order book depth (±5%);
- 1h / 4h / 1d trend;
- 1-मिनट staircase (धीरे-धीरे ऊँचे lows, जैसा आपने बताया);
- पुराने low के retests;
- ETH का आगे चलना;
- **1-second staircase;**
- perp बनाम spot;
- 24 घंटे की volatility;
- top-trader long/short ratio।

**Screen:** 300 tests पर Bonferroni (सख़्त) कसौटी लगी।
- **6 features असली निकले।** सब 0.5% वाले turns (f = 0.25) में हैं, जहाँ data सबसे ज़्यादा है।
- **HOLD पर भी इनका असर लगभग वैसा ही रहा।** इसलिए ये असली हैं:

| Feature | DISC AUC | HOLD AUC | मतलब |
|---|---|---|---|
| पिछली गिरावट/चढ़ाई का size | 0.545 | 0.542 | बड़ी चाल के बाद turn थोड़ा ज़्यादा पूरा होता है |
| bounce की रफ़्तार | 0.534 | 0.535 | तेज़ bounce थोड़ा ज़्यादा पूरा होता है |
| **1-second staircase** | 0.530 | 0.532 | seconds में ऊँचे lows → थोड़ा ज़्यादा पूरा |
| bounce का समय (मिनट) | 0.466 | 0.465 | धीमा bounce कम पूरा होता है |
| retests | 0.469 | 0.468 | low का बार-बार test होना थोड़ा उल्टा असर देता है |
| ETH का आगे चलना | 0.447 | 0.441 | ETH पहले ज़्यादा उछल चुका हो → BTC का turn कम पूरा |

- **AUC पढ़ने का तरीका:** 0.50 = coin flip, 1.00 = perfect।
- **0.53–0.55 बहुत छोटा फ़र्क है।** सब 20 features को मिलाकर logistic model बनाया गया (महीना-छोड़-महीना जाँच):
  - AUC 0.50–0.57 रहा;
  - fee से पहले की कमाई (gross) लगभग 0 रही (0.5% पर +0.002%, 1% पर +0.001%);
  - fee के बाद हर setting में घाटा: −0.09% से −0.4% प्रति trade।
- **नतीजा:** अच्छे symptoms भी 0.5% के turn पर इतने कमज़ोर हैं कि fee निकालना संभव नहीं।

## 4. T3: 9 timeframes पर 296 indicator setups (single, multiple, multi-timeframe, flow)

- **Timeframes:** 1m, 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1d।
- **Indicators:**
  - price-based: EMA, Hull, ZLEMA, Kalman, linear-regression t, CUSUM, Donchian, MACD, RSI, Bollinger, Heikin-Ashi, curvature (रफ़्तार का मुड़ना), fractal structure, Ehlers SuperSmoother;
  - multi-timeframe agreement;
  - 7 indicators का vote;
  - flow: taker imbalance, OI×price, premium, order-book imbalance, funding, ETH lead, top-trader long/short।

| TF | Setups | औसत सही दिशा % | null से सबसे बड़ा z | ≥ 30 trades में fee के बाद positive |
|---|---|---|---|---|
| 1m | 27 | 48.7% | **3.93** (Bollinger fade) | 1 |
| 5m | 33 | 48.7% | 1.01 | 1 |
| 15m | 33 | 48.3% | 1.84 | 2 |
| 30m | 33 | 48.6% | 2.07 | 1 |
| 1h | 34 | 48.6% | 1.79 | 5 |
| 4h | 34 | 48.8% | 1.96 | 15 |
| 8h | 34 | 49.8% | 1.79 | 12 |
| 12h | 34 | 48.6% | 2.93 | 14 |
| 1d | 34 | 51.9% | 1.65 | 7 |

- **Null से साफ़ बेहतर (z > 3.5) सिर्फ़ 1 setup निकला:** 1m Bollinger fade, जो छोटे mean-reversion पर चलता है। Fee से पहले उसकी कमाई +0.022% प्रति trade है, और fee के बाद **−0.07%**।
- **ऊँचे timeframes के "positive" setups (4h–1d) भरोसे लायक नहीं:**
  - इन्हें null से अलग नहीं किया जा सका (z < 3);
  - trades कम हैं (36–328);
  - DISC में BTC 87.6k → 73.7k गिरा, इसलिए कुछ नियम बस उस दौर की चाल पर सवार थे।
- **z की गिनती:** 296 में से z > 1.5 वाले 13 और z < −1.5 वाले 33 निकले (संयोग से लगभग 20–20 की उम्मीद थी)। Trend-follow वाले setups random से थोड़ा **बुरा** करते हैं, जो नीचे के mean-reversion से मेल खाता है।
- **कोई भी setup shortlist की सारी शर्तें पूरी नहीं कर सका:** z > 3.5, fee के बाद positive, और ≥ 30 trades। इसलिए HOLD पर कुछ नहीं गया।

## 5. T4: "छिपा timeframe": seconds और minutes के बीच कुछ है क्या?

**Grid:**
- 1 सेकंड से 1 दिन तक 30 अलग-अलग bar sizes;
- हर minute bar के लिए 60 तक अलग start-offsets (जैसे candle :07 पर शुरू हो);
- कुल 701 cells, null की 100 copies से तुलना।

- **Seconds (1–20 सेकंड): साफ़ momentum मिला,** यानी price कुछ seconds तक उसी दिशा में चलता रहता है:

  | Bar | AC1 | Null से दूरी (z) |
  |---|---|---|
  | 1 सेकंड | 0.091 | 77 |
  | 10 सेकंड | 0.035 | 9.6 |
  | 20 सेकंड | 0.024 | 6.3 |

  20 सेकंड पर variance ratio 1.33 है। **यही वह "धीरे-धीरे एक दिशा में" वाली चीज़ है जो आपने महसूस की।** यह असली है।
  - **पर पैसा नहीं बनता।** 10 सेकंड की औसत चाल 0.014% है, और fee 0.092%। 100% सही दिशा पर भी fee नहीं निकलती (fee-hurdle map)।
  - यह असर ज़्यादातर बड़े orders के टुकड़ों में भरने से आता है।
- **Minutes (1 मिनट – 1 दिन): कोई "छिपा" timeframe या offset नहीं मिला।** 691 में से 0 cells सख़्त कसौटी पर निकले।
- **पर एक pattern लगातार दिखा:** 5 मिनट से 8 घंटे तक variance ratio 0.80–0.95 रहा (z −1.1 से −3.3, ज़्यादातर −2 के आसपास)। मतलब BTC intraday में थोड़ा **उल्टा लौटता** है। यह शोध-साहित्य से मेल खाता है (crypto में 15-मिनट reversal)। पर पहले की TFX study की तरह यह भी fee के बाद नहीं टिकता।

## 6. आपके सवाल का सीधा जवाब

1. **"Indicators देर से बताते हैं":** सही है, और नापा गया। 1% के turn में पुष्टि तक 62 मिनट और 57% चाल निकल जाती है (§1)।
2. **"पहले पकड़ने का कोई तरीका?":** 9 timeframes, 296 setups, 20 symptoms, और seconds से 1 दिन तक के bars देखे गए। BTC पर कोई भी तरीका turn को random walk से साफ़ पहले नहीं पकड़ता, जो fee के बाद कमाई दे।
   - 6 symptoms असली हैं और HOLD पर भी टिके। पर उनका असर इतना छोटा (AUC 0.53–0.55) है कि 0.5% के turn पर fee नहीं निकलती।
3. **गणित से यह क्यों है:** जिस बाज़ार में दिशा लगभग random हो, वहाँ "पुष्टि" को देर से ही आना है। Detection theory (Lorden 1971, Moustakides 1986) के अनुसार, false alarm की तय सीमा पर CUSUM से कम देरी कोई तरीका नहीं दे सकता। CUSUM भी इस study में शामिल था, और वह भी null से बेहतर नहीं निकला।
4. **कहाँ पैसा है, यह पहले के सबूतों से पता है:** "BTC कब मुड़ेगा" में नहीं, बल्कि "आने वाले 1–7 दिनों में कौन-सा coin बाक़ियों से बेहतर करेगा" में। यह skill अनदेखे coins और 2018–19 पर भी साबित हुई, और ECO में live है।

## 7. आगे क्या (हर कदम आपकी हाँ से)

- **(a)** HOLD में दिखे "4% turns ज़्यादा पूरे हुए" संकेत को एक locked forward-watch hypothesis बनाया जाए। यह Oct 2026 से आगे के data पर बिना छेड़े जाँचा जाएगा। इसमें 4 महीने में सिर्फ़ ~40 turns आते हैं, इसलिए जवाब आने में कई महीने लगेंगे।
- **(b)** Random BTC पर 1,000 combinations वाला demonstration, जिसका ज़िक्र पिछली बात में किया था: "best" combination backtest में कितना चमकता है और अनदेखे हिस्से पर क्या होता है।
- **(c)** कुछ नहीं: ECO के forward नतीजों (TC gate ~9 Nov) का इंतज़ार।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये ऐतिहासिक data के नतीजे हैं, भविष्य का वादा नहीं।

**Sources (शोध-साहित्य):**
- [Lorden/Moustakides: CUSUM की optimality (समीक्षा)](https://arxiv.org/pdf/2403.18782)
- [Astill et al.: Bitcoin पर real-time CUSUM monitoring](https://nottingham-repository.worktribe.com/output/5396026)
- [Crypto में 15-मिनट mean reversion (2026 preprint)](https://arxiv.org/pdf/2608.21888)
- [Order-flow imbalance और Bitcoin के seconds-स्तर returns](https://arxiv.org/pdf/2308.14235)
- [Bitcoin futures बनाम spot price discovery](https://ideas.repec.org/a/eee/finlet/v34y2020ics1544612319304714.html)
