# BTC: हर timeframe पर हर strategy की historical paper trading (spot और futures अलग), 28 अक्टूबर 2026

> **यह file क्या है:**
> - BTCUSDT के पूरे data पर 1 मिनट से 1 साल तक के 11 timeframes का test।
> - इसमें शामिल है:
>   - आज तक की हमारी सारी strategies, सारे आम indicators, और उनके combinations;
>   - stop-loss के तरीके;
>   - BNB वाली fees;
>   - spot और futures, अलग-अलग।
> - हर trade (सही या गलत) दर्ज है।
> - Results और analysis इसी file में हैं, timeframe दर timeframe।
>
> **Discipline:**
> - Protocol P&L का कोई भी नंबर निकलने से **पहले** lock हुआ: `logs/btc_alltf_2026_10_28/BTC_ALLTF_PROTOCOL_PREREGISTERED.md`, SHA `51a40b1d…`, 2026-10-28 17:03 UTC।
> - Settings `STUDY_CONFIG.json` (`aa8f2a70…`) भी उसी समय lock हुईं।
> - Run: `logs/btc_alltf_2026_10_28/RUN_2026-10-28T1705Z/`। हर file का SHA उसकी `DONE.json` में है।
> - Engine और rules के tests run से पहले हुए (§2)। Independent verifier ने run के बाद हर नंबर दोबारा जाँचा (§9)।
> - यह पुरानी किसी study में नहीं मिलाया गया: code `src/btc_alltf/`, data `data/derived/btc_alltf/`, नतीजे `logs/btc_alltf_2026_10_28/`।
>
> मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।

---

## 0. सीधा जवाब

1. **पूरा test हुआ, कुछ नहीं छोड़ा।**
   - 11 timeframes (1m → 1y), spot और futures अलग-अलग: **22 jobs**।
   - **1,38,931 unique configs** (111 rules × दिशाएँ × 9 exits/stop-loss, साथ में 5 filters, 276 जोड़े और 7 votes)।
   - **2,24,84,31,178 trades** (करीब 225 करोड़)। हर trade अपने pass/fail के साथ दर्ज है।
   - हर दिन का हिसाब अलग file में है, बिना trade वाले दिन भी।
2. **नतीजा, lock किए gates के हिसाब से: 1,38,931 में से सिर्फ़ 1 config PASS।**
   - वह config: spot 15m, "EMA50 के EMA200 के नीचे जाने पर, जब भाव अभी SMA200 के ऊपर हो, तब खरीदना"।
   - 55 trades, 81.8% सही, fee के बाद +0.49% प्रति trade।
   - पर वह **किनारे पर** पास हुआ (q 0.046 बनाम सीमा 0.05)।
   - पूरे study की गिनती (post-hoc) में वह नहीं टिकता (q 0.16)।
   - पड़ोसी timeframes (5m, 30m, 1h, 1m) पर वह घाटे में है, और 2 ATR stop लगाते ही भी घाटे में चला जाता है।
   - **दर्जा:** forward paper-tracking का candidate। असली पैसे लायक नहीं।
3. **बाकी हर timeframe पर 0 PASS।** हर timeframe पर अलग कारण से:
   - **1m–30m: fee की दीवार।**
     - हर candle पर आँख बंद करके long लेने पर fee के बाद profit सिर्फ़ इतनी बार हुआ: 1m पर 3.3%, 5m पर 11.4%, 15m पर 20.6% (spot)।
     - 90–99.8% configs fee के बाद घाटे में हैं।
     - Fee से पहले की कमाई (gross) सिक्के जैसी है (42–67% configs positive)।
   - **1h–8h: fee अब भी बड़ी है, दिशा कमज़ोर।**
     - Spot 1h पर सिर्फ़ 20.6% configs net positive हैं।
     - 8h पर 62.7%, पर ये positive ज़्यादातर BTC की चढ़ाई (beta) से हैं। Random entry से साफ़ बेहतर (z ≥ 2) सिर्फ़ 3–5% configs।
   - **1d / 1w: बाज़ार की चढ़ाई सब पर हावी।**
     - BTC 2017→2026 में ~20 गुना हुआ। Long configs का औसत positive है, पर random से साफ़ बेहतर बहुत कम हैं।
     - Trades कम होने से हफ़्ते पर लगभग सब INSUFFICIENT हैं।
   - **1mo / 1y:** candles ही 110 / 10 हैं। हर config INSUFFICIENT; कुछ भी साबित नहीं हो सकता।
4. **सबसे मज़बूत "pattern" (साबित नहीं): high volatility में गिरावट या oversold पर खरीदना।**
   - 1d, 8h और 4h पर, दोनों markets में, ranking में सबसे ऊपर यही है। सही होने की दर 70–100% है, और random से z 2.7–5.5।
   - Futures 1d पर "Williams %R oversold + high-vol" पूरे study की गिनती के बाद भी टिकता है (q 0.021, DSR 0.994)। पर सिर्फ़ 31 trades हैं, इसलिए INSUFFICIENT।
   - **कमज़ोरी:** यह stop के बिना "BTC वापस आएगा" पर टिका है।
5. **Stop-loss:**
   - Spot पर हर timeframe में stops ने ज़्यादातर नियम **बिगाड़े** (बेहतर सिर्फ़ 0–40% rules)।
   - Futures पर असर लगभग शून्य है।
   - किसी timeframe पर stop ने हारे नियम को जीतने वाला नहीं बनाया।
6. **Short:** हर timeframe पर shorts हारे (futures में 0–32% configs positive)।
7. **पुरानी project strategies** (TSMOM, EMA, MACD, Donchian, RSI, Bollinger, आपका green-candle नियम, micro-momentum वगैरह):
   - सिर्फ़ BTC पर, कोई भी timeframe पर PASS नहीं।
   - छोटे timeframes पर सब ठीक fee जितने घाटे में हैं।
   - इससे ECO/N1 पर कोई नया सवाल नहीं उठता, क्योंकि उनकी ताकत कई coins में से चुनना है, जो इस BTC-only test में शामिल नहीं था।
8. **सब कुछ independent verifier ने ज़मीनी स्तर पर दोबारा जाँचा** (§9):
   - सारे 22 jobs, हर config के metrics, लाखों trades का अलग replay, और जानबूझकर डाली गई गलतियाँ।
   - **कोई check fail नहीं हुआ।**

---

## 1. क्या किया गया

### 1.1 Data: असली candles, कुछ भी नकली नहीं
- **Spot BTCUSDT:** 2017-08-17 से 2026-09-30 तक, 47,89,278 मिनट।
- **Futures BTCUSDT (USD-M perpetual):** 2020-01-01 से 2026-09-30 तक, 35,49,600 मिनट। इसमें एक भी मिनट कम नहीं है।
- **Source:** Binance का official public data (data.binance.vision)।
  - 1m files आज आपकी इजाज़त से download कीं: 173 zips, हर एक Binance की अपनी CHECKSUM file से मिलाया गया, 0 fail।
  - 2026 का spot 1m पहले से मौजूद 1-second data से बना।
- बाकी हर timeframe (5m, 15m, 30m, 1h, 4h, 8h, 1d, 1w, 1mo, 1y) इसी 1m से बना।
- **कोई candle बनाई नहीं गई:** Binance के outage वाले minute ख़ाली ही छोड़े गए।
- **ज़मीनी जाँच** (`src/btc_alltf/verify_bars.py`):
  - पहले से मौजूद independent files से मिलाया।
  - 2021-10 → 2025-12 तक हर timeframe पर हर candle **बिल्कुल बराबर** निकली।
  - फ़र्क सिर्फ़ तीन जगह मिला:
    - दिसंबर 2017 के दो हफ़्ते, जब Binance के अपने data में timestamps कुछ सेकंड खिसके हुए हैं;
    - 2026 के 1-second से बने bars, जिनमें ~4% minutes का open 1 tick (0.01 USDT) अलग है;
    - futures के 7.1 लाख 5m bars में से 4–5 bars, Binance की चार glitch वाली घड़ियों पर।

### 1.2 Fees: पहले से तय, `deploy/fees.json` से (हाथ से नहीं लिखी)
| Market | हर तरफ़ (entry या exit) | Round trip | किससे बनी |
|---|---|---|---|
| Spot | 0.085% | 0.170% | BNB fee 0.075% + impact 0.01% |
| Futures | 0.046% | 0.092% | BNB taker 0.036% + impact 0.01% |

- Futures पर funding भी असली लगी: हर 8 घंटे की असली funding rate, 7,395 events।
- Futures leverage 1x है। सिर्फ़ short liquidate हो सकता है (भाव ~2 गुना होने पर), और तब पूरा margin जाता है।

### 1.3 Strategies: 111 rules, हर एक की दोनों दिशाएँ
**Rules की गिनती, श्रेणी के हिसाब से:**

| श्रेणी | Rules | उदाहरण |
|---|---|---|
| Trend | 50 | SMA/EMA 20–200, crossovers, MACD, ADX, Aroon, PSAR, Supertrend, Ichimoku, Donchian, Keltner, Bollinger breakout, regression, Vortex, TRIX, KST, Heikin-Ashi, TSMOM 1–100, ribbon, VWAP |
| Oscillators | 21 | RSI (14, 2), ConnorsRSI, Stochastic, StochRSI, Williams %R, CCI, CMO, Ultimate, MFI, Bollinger fade, Z-score, Fisher, ROC-z, VWAP-z, DPO, Keltner fade |
| Momentum | 6 | Awesome, Elder Ray, Force Index, Coppock, TSI, BOP |
| Volume / flow | 7 | OBV, CMF, Chaikin, VPT, EOM, taker-buy ratio, volume spike |
| Volatility | 6 | Squeeze, NR7, volatility breakout, ATR expansion, low-vol + TS20, high-vol trend |
| Candle / price patterns | 15 | Engulfing, hammer, 3 soldiers, star, inside/outside bar, swing structure, double bottom/top, streaks, green candle, micro-momentum, ZigZag, S/R bounce, RSI divergence |
| Statistics | 2 | R² trend, autocorrelation regime |
| Calendar | 4 | Asia/Europe/US session, weekday |

**हमारी अपनी पुरानी strategies** उसी परिभाषा से शामिल हैं (tag PRJ):
- N1 के TFX families (TSMOM20, EMA 20/50, MACD, Donchian 20/10, RSI 30/50/70, Bollinger fade);
- Spot S1 (SMA200);
- आपका green-candle नियम;
- micro-momentum;
- Batch 2 का low-vol cluster;
- ConnorsRSI;
- double bottom/top;
- swing follow;
- S/R bounce।

**हर rule को किन दिशाओं में चलाया:**
- Spot: "natural long" (जैसे भाव SMA के ऊपर → खरीदो) और "contra long" (उल्टा: भाव SMA के नीचे → खरीदो)।
- Futures: इन दोनों के साथ natural short और contra short भी।

**शामिल नहीं:**
- कई coins वाली strategies (ECO की RS, coin-selection brains), क्योंकि यह सिर्फ़ BTC का test है।
- Trained AI models (इनके लिए अलग training protocol चाहिए)।
- OI, order-book, options या on-chain जैसे non-price signals।

### 1.4 Exits और stop-loss: हर rule पर 9 तरीके
ATR = उसी timeframe का 14-bar ATR, signal वाली candle पर।

| Exit | मतलब |
|---|---|
| X0 | सिर्फ़ signal से exit |
| X1 / X2 / X3 | signal + stop-loss 1 / 2 / 3 ATR |
| X4 | signal + 3 ATR trailing stop |
| X5 | signal + stop 1.5 ATR + target 3 ATR |
| X6 | signal + stop 2 ATR + target 2 ATR |
| X7 | ठीक 1 candle hold |
| X8 | 10 candles hold + 2 ATR stop |

**Fill के नियम:**
- अगर stop और target दोनों एक ही candle में छू जाएँ, तो **stop माना गया** (बुरी स्थिति वाला अनुमान)।
- अगर candle stop के पार खुले (gap), तो fill उस candle के open पर।

### 1.5 Combinations
| Layer | क्या | Exits |
|---|---|---|
| L1 | हर rule × हर दिशा | सभी 9 |
| L2 | हर rule + 5 filters में से एक: trend (SMA200), ADX > 20, कम volatility, ज़्यादा volatility, volume ज़्यादा | X0, X2 |
| L3 | 24 प्रतिनिधि rules के सभी 276 जोड़े (दोनों एक साथ हाँ कहें तभी trade) | X0, X2, X4 |
| L4 | voting: 10 trend rules में से 6/8/10, 5 oscillators में से 3/5, सभी 24 में से 15/18 | सभी 9 |

- एक जैसे configs सिर्फ़ एक बार चलाए गए। हर copy `duplicates.csv` में दर्ज है कि वह किसके बराबर है।
- **कुल:** 1,38,931 unique configs और **2,24,84,31,178 trades** (करीब 225 करोड़)।

### 1.6 Trade का समय: भविष्य नहीं देखा गया
- Signal candle के **close** पर बनता है, और entry **अगली candle के open** पर होती है।
- Look-ahead test (§2) से पक्का किया कि कोई rule आगे का data नहीं देखता।

### 1.7 हर trade कैसे दर्ज है (कम जगह, पर कुछ नहीं छूटा)
**`trades.parquet` (हर job में) की हर row = एक trade:**
- config number;
- entry time और exit time (UTC);
- exit का कारण (signal / stop / target / trailing / time / liquidation / end);
- stop/target वाला fill price;
- net नतीजा (fee और funding के बाद);
- **pass/fail** (net > 0 = PASS, नहीं तो FAIL)।

**जगह:**
- एक trade ≈ 7.8 bytes (पूरी चौड़ी row होती तो 21.5 bytes)।
- बाकी columns (entry price, gross, fee, funding, MAE/MFE) candles से हूबहू वापस बनते हैं: `python src/btc_alltf/query.py`। यह वापस बनाना verifier ने जाँचा।

**हर दिन का हिसाब:**
- `daily_overview.csv`: हर कैलेंडर दिन की एक row, बिना trade वाले दिन भी। उस दिन कितने trades बंद हुए, कितने सही, कितने गलत, net कितना।
- `daily_groups.parquet`: यही हिसाब layer × श्रेणी × दिशा × exit के हिसाब से।

**किसी एक दिन के सारे trades:**
```bash
python src/btc_alltf/query.py --run logs/btc_alltf_2026_10_28/RUN_2026-10-28T1705Z --market spot --tf 1h --date 2024-03-12
```

### 1.8 Pass / fail और ranking के नियम (lock किए गए)
**हर trade:** net > 0 → PASS, नहीं तो FAIL।

**हर config:** पहले से तय 7 gates, उसी market और timeframe के अंदर।

**तीन दौर:**
- **D (सीखने वाला):** शुरू → 2022;
- **V (जाँच):** 2023–2024;
- **H (आख़िरी):** 2025-01 → 2026-09।

| Gate | शर्त |
|---|---|
| G1 | काफ़ी trades: D ≥ 30, V ≥ 10, H ≥ 10। न हों तो नतीजा **INSUFFICIENT** |
| G2 | तीनों दौर में औसत net > 0 |
| G3 | आँकड़ों से पक्का (t-test, हज़ारों configs की गिनती के बाद भी, BH q ≤ 0.05) |
| G4 | random entry से बेहतर (z ≥ 2) |
| G5 | H में 2 गुना fee पर भी profit, और 1 candle देर से entry पर भी profit |
| G6 | कम से कम ⅔ साल positive |
| G7 | Deflated Sharpe ≥ 0.95, यानी इतने configs में से किस्मत से निकला हुआ नहीं |

- **PASS** = सारे gates। **FAIL** = trades काफ़ी थे, पर कोई gate टूटा। **INSUFFICIENT** = trades ही कम।
- **Ranking:** PASS पहले, फिर कितने gates पास हुए, फिर t-statistic।

**ईमानदार सीमाएँ (पहले से लिखी):**
- H का data पुरानी studies ने दूसरे नियमों के लिए देखा है। इसलिए यहाँ का PASS "forward जाँच का candidate" होगा, साबित edge नहीं।
- 1y पर spot के सिर्फ़ 10 और futures के 7 candles हैं, और 1mo पर 110 / 81। वहाँ ज़्यादातर नतीजे INSUFFICIENT आएँगे। यह data की सच्चाई है।

---

## 2. Run से पहले की ज़मीनी जाँच

| जाँच | नतीजा | Evidence |
|---|---|---|
| 1m download checksum | 173/173 PASS | `data/external/binance_1m/*/MANIFEST.csv` |
| Bars vs पुरानी independent files | 2021-10 → 2025-12 हर candle बराबर; फ़र्क सिर्फ़ §1.1 वाली तीन जगह | `logs/btc_alltf_2026_10_28/bars_check.csv` |
| Engine unit tests: हाथ से बनाई candles, जवाब पहले से हाथ से गिना हुआ | **19/19 PASS** (signal exit, stop, gap, target, एक candle में दोनों, trailing, time, liquidation, end, delay, filter, fee, funding window, MAE/MFE, control) | `test_engine_output.txt` |
| Look-ahead test: हर rule और filter को पूरे data और कटे data पर चलाकर मिलाया | **4,630 comparisons, 0 फ़र्क**। जानबूझकर डाला गया "कल का भाव देखने वाला" नकली rule पकड़ा गया | `test_lookahead_output.txt` |
| Smoke run (spot 1w, futures 1w) + verifier | सब PASS। दोनों mutations (बदला हुआ trade, बदली हुई state) पकड़े गए। दो छोटे code bugs मिले और ठीक किए (protocol §6b) | protocol §6b |
| Lock के बाद code बदलाव | 1: daily file अब 2026-09-30 तक हर दिन दिखाती है। Trades पर कोई असर नहीं | `CODE_CHANGES_AFTER_LOCK.md` |

---

## 3. हर timeframe के नतीजे

**हर timeframe की पूरी tables** (top 10, हर exit, हर दिशा, हर श्रेणी, project rules, layers) यहाँ हैं: `logs/btc_alltf_2026_10_28/RUN_2026-10-28T1705Z/report/<market>_<tf>.md`। नीचे उनका सार है।

**तुलना के लिए buy-and-hold** (वही candles, वही fee, futures पर funding भी):

| दौर | Spot long | Futures long (1x) | Futures short (1x) |
|---|---|---|---|
| पूरा (spot 2017-08 → 2026-09, futures 2020-01 → 2026-09) | +1,860.6% | +554.1% | −555.3% |
| D (spot 2017-08 / futures 2020-01 → 2022) | +287.8% | −132.6%* | +132.3%* |
| V (2023–2024) | +465.1% | +401.0% | −401.6% |
| H (2025-01 → 2026-09) | −10.8% | −18.2% | +18.0% |

\* Futures D = 2020-01 → 2022-12। इस दौर में भाव 2.30 गुना हुआ (+130%)। पर हर 8 घंटे की funding का कुल खर्च शुरुआती notional का **261.8%** था, क्योंकि 2021 में funding rates ऊँची थीं और bull में notional भी बढ़ गया था। इसलिए 1x long बिना rebalance के −132.6% पर पहुँचता। असल में उससे पहले ही margin ख़त्म होकर position liquidate हो जाती।
  - यह आँकड़ा एक अलग तरीके से दोबारा जाँचा गया: funding file × daily open, Σ rate·P/P₀ = 2.618।
  - **मतलब:** futures पर लंबे समय तक long रखने में funding बहुत बड़ा खर्च है।

**इसका मतलब:**
- BTC 2017 से 2026 में ~20 गुना हुआ। इसलिए spot पर लगभग कोई भी "long" नियम औसत में positive दिख सकता है, सिर्फ़ बाज़ार की चढ़ाई की वजह से।
- इसीलिए gate G4 हर config को उसी दिशा और उसी holding वाली **random entry** से मिलाता है। Random entry को भी वही चढ़ाई मिलती है।

### 3.1 1 साल (1y) और 1 महीना (1mo): data बहुत कम

| | spot 1y | futures 1y | spot 1mo | futures 1mo |
|---|---|---|---|---|
| Candles | 10 | 7 | 110 | 81 |
| Unique configs | 168 | 270 | 2,730 | 4,926 |
| Trades | 40 | 63 | 8,837 | 10,947 |
| PASS / FAIL / INSUFFICIENT | 0 / 0 / 168 | 0 / 0 / 270 | 0 / 0 / 2,730 | 0 / 0 / 4,926 |

**सीधी बात:**
- यहाँ **हर config INSUFFICIENT** है। 10 या 81 candles में D, V और H, तीनों दौर में ज़रूरी trades बन ही नहीं सकते।
- यह code की गलती नहीं, data की सच्चाई है। 1y पर BTC के 9 साल = 9 candles।
- **दिखने वाले बड़े % भ्रम हैं।** उदाहरण: 1y spot पर "green candle → long" के 2 trades, दोनों सही, औसत +118%। यह बस BTC के बड़े bull साल हैं (2017 +221%, 2020 +302%)। 2 trades से कोई नियम साबित नहीं होता।
- **1mo spot पर** 81.9% configs net positive हैं, क्योंकि spot पर सिर्फ़ long है और BTC चढ़ा। Futures 1mo पर shorts का median −10% से −14% है, और कुल मिलाकर सिर्फ़ 45.8% configs positive हैं (सिक्के से भी कम)।

**हर संभव trade** (हर candle पर long या short, 1 candle hold, fee के बाद):

| Timeframe | औसत चाल | Long PASS | Short PASS |
|---|---|---|---|
| 1mo spot | ±15.9% | 52.3% | 46.8% |
| 1mo futures | ±14.6% | 53.8% | 46.2% |

यानी इतने बड़े timeframe पर fee कोई रुकावट नहीं है। पर दिशा का पता लगाना उतना ही मुश्किल है (~50%), और samples बहुत कम हैं।

### 3.2 1 हफ़्ता (1w)

| | spot 1w | futures 1w |
|---|---|---|
| Candles | 477 | 353 |
| Unique configs / trades | 4,275 / 51,251 | 8,305 / 69,490 |
| PASS / FAIL / INSUFFICIENT | **0** / 105 / 4,170 | **0** / 60 / 8,245 |
| Gross > 0 वाले configs | 80.1% | 54.0% |
| Net > 0 वाले configs | 79.1% | 53.1% |
| Gates (G1 / G2 / G3 / G4 / G5 / G6 / G7) | 105 / 845 / 0 / 51 / 0 / 107 / 0 | 60 / 619 / 0 / 450 / 0 / 82 / 0 |

**दिशा के हिसाब से (L1, median config):**
- **Spot:** natural long +10.9% प्रति trade (86.6% configs positive); contra long +2.5%।
- **Futures:** natural long +8.1%, contra long +1.4%, natural short −2.0%, contra short −5.2% (सिर्फ़ 13.7% positive)।
- **मतलब:** हफ़्ते के timeframe पर जो "कमाई" दिखती है, वह लगभग पूरी BTC की चढ़ाई है। Short हर तरह से हारा।

**सबसे ऊपर:**
- **Spot:** `L3 SMA50 + green candle, long, X0`। 75 trades, सिर्फ़ 32% सही, औसत +3.4%। D, V, H तीनों positive। पर random से बेहतर नहीं (z 0.75), और DSR 0.016। **FAIL।**
- **Futures:** `L2 TSMOM1 contra-long + ADX>20`। 80 trades, 70% सही, +1.25%। z −0.18। **FAIL।**

**Stop-loss का असर (spot, एक ही rule पर paired तुलना):**
- 1 / 2 / 3 ATR stop ने 65–95% rules का औसत **घटाया**। Weekly candles पर stop अक्सर बढ़ती चाल से पहले ही बाहर निकाल देता है।
- सिर्फ़ X8 (10 हफ़्ते hold + stop) ने 70% rules में X0 से बेहतर किया। फिर भी कोई PASS नहीं।

**नतीजा:** 1w पर कोई formula PASS नहीं है। Trades कम हैं (G1 सिर्फ़ 105/60 configs में पूरा), और जो दिखता है वह trend-beta है।

### 3.3 1 दिन (1d)

| | spot 1d | futures 1d |
|---|---|---|
| Candles | 3,332 | 2,465 |
| Unique configs / trades | 4,841 / 4,52,449 | 9,632 / 6,45,904 |
| PASS / FAIL / INSUFFICIENT | **0** / 2,309 / 2,532 | **0** / 2,691 / 6,941 |
| Gross > 0 / net > 0 वाले configs | 79.4% / 74.6% | 54.9% / 52.4% |
| Trade win rate (सारे trades) | 46.4% | 44.8% |
| Gates (G1 / G2 / G3 / G4 / G5 / G6 / G7) | 2,309 / 1,456 / 2 / 88 / 0 / 1,043 / 0 | 2,691 / 1,267 / 8 / 415 / 0 / 1,309 / 1 |
| Funnel G1 → +G2 → +G4 → +G6 | 2,309 → 735 → 28 → 25 | 2,691 → 393 → 22 → 18 |

**हर संभव trade** (हर दिन long या short, fee के बाद PASS):

| Market | 1 दिन hold: long / short | 16 दिन hold: long / short |
|---|---|---|
| Spot | 47.7% / 44.6% | 53.3% / 45.1% |
| Futures | 48.3% / 47.3% | 51.7% / 47.3% |

यानी हर दिन आँख बंद करके long लेने पर 52% से कम दिन fee के बाद profit में थे।

**दिशा (L1, median config):**
- **Spot:** natural long +1.40% (83.6% positive), contra long +0.09%।
- **Futures:** natural long +1.10%, contra long +0.22%, natural short −0.39%, contra short −0.50%।

**Stop-loss का असर (paired, एक ही rule पर X0 से तुलना):**
- **Spot:** हर stop ने ज़्यादातर rules का औसत घटाया।
  - 1 / 2 / 3 ATR stop के बाद सिर्फ़ 40 / 30 / 39% rules बेहतर रहे।
  - Trailing (X4) और target वाले exits (X5, X6) में सिर्फ़ 8–14% rules बेहतर रहे।
- **Futures:** stop थोड़ा मदद करता है। 1 ATR stop के बाद 62% rules बेहतर रहे (median +0.17%)। पर इससे कोई PASS नहीं बना।

**Project की पुरानी strategies (natural, हर rule का सबसे अच्छा exit):**

| Rule | Spot 1d | Futures 1d |
|---|---|---|
| TFX TSMOM20 | 168 trades, +3.38%/trade, पर H −0.03% → FAIL | 134 trades, +1.86%, H −0.05% → FAIL |
| TFX MACD | 120, +3.89%, H −0.13% → FAIL | 88, +2.56%, H +0.20% → FAIL |
| TFX Donchian 20/10 | 44, +4.09%, H +1.52% → INSUFFICIENT | 34, +11.15% → INSUFFICIENT |
| TFX RSI 30/50 (N1 sleeve B) | 21, +4.50%, H −2.29% → INSUFFICIENT | 15, +5.37%, H −2.42% → INSUFFICIENT |
| Spot S1 (SMA200) | 33, +13.4% → INSUFFICIENT | 27, +8.9% → INSUFFICIENT |
| आपका green-candle नियम | 325, +0.65%, H +0.03% → FAIL | 237, +0.52%, H −0.02% → FAIL |

ये सब बड़े-औसत वाले trend नियम हैं। इनका **median trade negative** है (जैसे TSMOM20 spot: सिर्फ़ 33.9% trades सही)। यानी कुछ बड़े bull trades औसत खींचते हैं, जो Atlas की पुरानी चेतावनी जैसा ही है।

**सबसे लगातार दिखने वाला pattern: "high volatility में dip/oversold पर खरीदना"**
- यह pattern 1d और 8h पर, spot और futures दोनों में, ranking में सबसे ऊपर आता है। सबसे अच्छे उदाहरण:

| Config | n | सही % | औसत net | D / V / H | random से z | DSR | फ़ैसला |
|---|---|---|---|---|---|---|---|
| futures 1d `Williams %R oversold long + high-vol filter, X0` | 31 | 87.1% | +5.01% | +8.0 / +3.1 / +3.5% | 5.45 | **0.999** | INSUFFICIENT (D में 30 से कम trades) |
| spot 1d वही rule | 45 | 88.9% | +4.18% | +4.8 / +3.2 / +3.5% | 3.34 | 0.68 | INSUFFICIENT |
| spot 1d `EMA200 के नीचे गिरने पर long + high-vol, X0` | 26 | **100%** | +3.73% | — | 4.63 | — | INSUFFICIENT |
| spot 8h `EMA 9/21 contra long + high-vol, X0` | 90 | 77.8% | +2.32% | +3.1 / +2.0 / +1.0% | 3.04 | 0.49 | FAIL (G3, G5, G7) |
| futures 8h `Chaikin contra long + high-vol, X0` | 183 | 70.5% | +1.11% | +1.8 / +0.8 / +0.5% | 3.31 | 0.06 | FAIL |

- **यह pattern क्यों दिलचस्प है:**
  - कई timeframes, दोनों markets, और कई अलग indicators पर (Williams %R, EMA, Chaikin, KAMA) यही बात बार-बार आती है।
  - सही होने की दर ऊँची है (70–100%), और random entry से साफ़ बेहतर है (z 3–5)।
- **यह साबित क्यों नहीं है:**
  1. Lock किए गए gates पूरे नहीं हुए: trades कम हैं, या हज़ारों configs की गिनती के बाद (G3, G7) संयोग से अलग नहीं।
  2. High-vol filter को 500 candles का इतिहास चाहिए। इसलिए 1d पर 2017–2018 का bear market इसमें आया ही नहीं।
  3. Exit "भाव वापस आने" पर है, stop नहीं है। अब तक BTC हर गिरावट से उबरा, इसलिए यह बात survivorship पर टिकी है। अगर कोई गिरावट वापस न आए, तो नुकसान बड़ा होगा।
  4. इसी pattern के बाकी configs का median भी देखा। Spot 1d पर high-vol long configs का median +1.22% है, जबकि सारे L1 long का +0.62%। पर random से z ≥ 2 सिर्फ़ 2.9% configs में है।
- **पूरे study की गिनती के बाद भी** (post-hoc, सारे 1,38,931 configs): futures 1d `Williams %R oversold + high-vol` अकेला config है जो study-wide q ≤ 0.05 (0.021) और DSR ≥ 0.95 (0.994, job का V) दोनों पर टिकता है। पर 31 trades में से D दौर में 30 से कम हैं, इसलिए lock नियम में INSUFFICIENT।
- **ईमानदार दर्जा:** यह "forward जाँच का सबसे अच्छा candidate" है, edge नहीं। अगर आप चाहें, तो इसे बिना पैसे के forward track किया जा सकता है।

### 3.4 8 घंटे (8h)

| | spot 8h | futures 8h |
|---|---|---|
| Candles | 9,993 | 7,395 |
| Unique configs / trades | 4,882 / 13,82,394 | 9,673 / 20,32,791 |
| PASS / FAIL / INSUFFICIENT | **0** / 4,039 / 843 | **0** / 6,932 / 2,741 |
| Gross > 0 / net > 0 configs | 76.6% / 62.7% | 52.9% / 44.6% |
| Gates (G1 / G2 / G3 / G4 / G5 / G6 / G7) | 4,039 / 1,172 / 0 / 264 / 0 / 1,257 / 0 | 6,932 / 1,255 / 0 / 314 / 0 / 1,679 / 0 |
| Funnel G1 → +G2 → +G4 → +G6 | 4,039 → 962 → 109 → 106 | 6,932 → 879 → 84 → 70 |
| हर संभव 1-candle trade: long / short PASS | 43.7% / 40.8% | 46.8% / 44.7% |

**मुख्य बातें:**
- 8h पर कोई config G3 (BH q ≤ 0.05) पास नहीं करता। Spot का सबसे छोटा q 0.065, futures का 0.385। सबसे ऊँचा DSR spot पर 0.73 और futures पर 0.57 है।
- **दिशा (futures):** natural long का median +0.23%। Shorts में सिर्फ़ 11–20% configs positive।
- **Stop:** spot पर हर stop ने ज़्यादातर rules को बिगाड़ा (बेहतर सिर्फ़ 10–34%)। Futures पर असर लगभग शून्य (बेहतर 44–57%)।
- **Project rules:**
  - TFX RSI 30 long (N1 sleeve B, 8h पर live) spot 8h पर X8 exit के साथ: 71 trades, +1.60%/trade, H +1.33%। फिर भी FAIL, क्योंकि gates पूरे नहीं।
  - Atlas में इसका median trade positive था। यहाँ भी औसत positive है, पर पक्का नहीं।
- **"High-vol dip-buy" pattern** यहाँ भी top पर है (ऊपर §3.3 की table)।

### 3.5 4 घंटे (4h)

| | spot 4h | futures 4h |
|---|---|---|
| Candles | 19,974 | 14,790 |
| Unique configs / trades | 4,936 / 29,35,333 | 9,799 / 43,43,058 |
| PASS / FAIL / INSUFFICIENT | **0** / 4,577 / 359 | **0** / 8,615 / 1,184 |
| Gross > 0 / net > 0 configs | 76.2% / 52.5% | 51.7% / 35.8% |
| Trade win rate | 41.8% | 42.5% |
| Funnel G1 → +G2 → +G4 → +G6 | 4,577 → 589 → 103 → 97 | 8,615 → 678 → 45 → 37 |
| सबसे छोटा BH q / सबसे ऊँचा DSR | 0.087 / 0.74 | 0.975 / 0.76 |
| हर संभव 1-candle trade: long / short PASS | 41.2% / 38.2% | 45.2% / 42.8% |

**मुख्य बातें:**
- **Fee का असर दिखने लगता है:**
  - Spot पर 76% configs fee से पहले positive हैं, पर fee के बाद सिर्फ़ 52.5%।
  - Futures पर fee से पहले 51.7% (लगभग सिक्का), fee के बाद 35.8%।
- **Shorts (futures):** natural और contra, दोनों में सिर्फ़ ~11–12% configs positive।
- **Stop (futures):** stop का असर लगभग शून्य है (हर exit 42–56% rules में X0 से बेहतर)।
- **Top configs:** फिर से "contra long + high-vol filter" ऊपर है।
  - उदाहरण futures: MACD(5,35,5) contra long + high vol, 446 trades, 74.7% सही, +0.50%/trade, z 3.03।
  - फिर भी DSR 0.000, क्योंकि हज़ारों configs में से इतना संयोग से भी निकल सकता है। FAIL।
- **Project rules (futures 4h, natural long):**
  - TFX EMA 20/50: 141 trades, +1.57%, H +0.65% → FAIL।
  - TSMOM20: 749 trades, +0.24%, H −0.02% → FAIL।
  - RSI 30 long: 104 trades, 60.6% सही, +0.19%, H +0.52% → FAIL।
  - आपका green-candle नियम: 1,453 trades, −0.01% → FAIL।

### 3.6 1 घंटा (1h)

| | spot 1h | futures 1h |
|---|---|---|
| Candles | 79,837 | 59,160 |
| Unique configs / trades | 4,945 / 1,16,25,383 | 9,893 / 1,71,61,168 |
| PASS / FAIL / INSUFFICIENT | **0** / 4,845 / 100 | **0** / 9,625 / 268 |
| Gross > 0 / net > 0 configs | 70.1% / **20.6%** | 49.8% / **15.5%** |
| Trade win rate | 35.9% | 39.2% |
| Funnel G1 → +G2 → +G4 → +G6 | 4,845 → 123 → 38 → 33 | 9,625 → 205 → 34 → 30 |
| सबसे छोटा BH q / सबसे ऊँचा DSR | 0.72 / 0.35 | 1.00 / 0.94 |
| हर संभव 1-candle trade: long / short PASS | **32.2% / 30.8%** | 39.2% / 38.1% |

**मुख्य बातें:**
- **1h पर fee "दीवार" बन जाती है।** हर घंटे आँख बंद करके long लेने पर spot में सिर्फ़ 32% घंटे fee के बाद profit में थे।
  - Fee से पहले spot के 70% configs positive हैं, पर fee के बाद सिर्फ़ 20.6%।
  - Futures पर fee से पहले ठीक सिक्का (49.8%), और fee के बाद 15.5%।
- **Shorts (futures):** सिर्फ़ 2.9–4.9% configs positive।
- **Stop:** spot पर हर stop ने 73–96% rules को बिगाड़ा। Futures पर असर शून्य (37–52% बेहतर)।
- **Project rules (spot 1h, natural long, सबसे अच्छा exit):**
  - TSMOM20: 4,442 trades, −0.04%/trade;
  - MACD: 3,045 trades, −0.05%;
  - green candle: 7,781 trades, −0.15%;
  - RSI 30 long: 555 trades, 60.4% सही, फिर भी −0.15%।
  - सब FAIL।
- **Top configs:** फिर से contra long (spot: RSI 20/80 contra long, 166 trades, +1.07%, z 2.99, DSR 0.07)। FAIL।

### 3.7 30 मिनट (30m)

| | spot 30m | futures 30m |
|---|---|---|
| Candles | 1,59,654 | 1,18,320 |
| Unique configs / trades | 4,951 / 2,33,38,139 | 9,902 / 3,43,61,791 |
| PASS / FAIL / INSUFFICIENT | **0** / 4,897 / 54 | **0** / 9,709 / 193 |
| Gross > 0 / net > 0 configs | 67.3% / **10.0%** | 46.9% / **7.9%** |
| Trade win rate | 31.8% | 36.6% |
| Funnel G1 → +G2 → +G4 → +G6 | 4,897 → 62 → 37 → 30 | 9,709 → 115 → 52 → 50 |
| सबसे छोटा BH q / सबसे ऊँचा DSR | 0.88 / 0.33 | 1.00 / 0.51 |
| हर संभव 1-candle trade: long / short PASS | **26.7% / 25.8%** | 35.3% / 34.3% |

**मुख्य बातें:**
- 30 मिनट पर fee के बाद सिर्फ़ 8–10% configs positive हैं।
  - Spot पर 67% configs की fee से पहले की कमाई (gross) positive है, पर fee उसे खा जाती है।
  - Futures पर gross ही सिक्के से नीचे है (46.9%)।
- **Shorts (futures):** 1.5–2.2% configs positive।
- **Stop:** spot पर stop/target वाले exits (X1–X6) 75–97% rules को बिगाड़ते हैं। Futures पर असर शून्य।
- **Top:** "RSI 20/80 contra long" (oversold पर नहीं, overbought पर long; X6 exit), futures 225 trades, z 3.98। फिर भी DSR 0.20 → FAIL।

### 3.8 15 मिनट (15m): यहाँ इस पूरे run का **एकमात्र PASS** मिला

| | spot 15m | futures 15m |
|---|---|---|
| Candles | 3,19,294 | 2,36,640 |
| Unique configs / trades | 4,951 / 4,64,94,936 | 9,937 / 6,86,48,793 |
| PASS / FAIL / INSUFFICIENT | **1** / 4,912 / 38 | **0** / 9,843 / 94 |
| Gross > 0 / net > 0 configs | 61.4% / **3.2%** | 44.5% / **3.1%** |
| Trade win rate | 27.1% | 33.4% |
| Funnel G1 → +G2 → +G4 → +G6 | 4,913 → 17 → 8 → 8 | 9,843 → 37 → 18 → 18 |
| हर संभव 1-candle trade: long / short PASS | **20.6% / 20.1%** | 30.3% / 29.8% |

**आम तस्वीर:**
- 15m पर fee सबसे बड़ी रुकावट है। हर 15 मिनट पर आँख बंद करके long लेने पर spot में सिर्फ़ 20.6% बार fee के बाद profit हुआ।
- 97% configs fee के बाद घाटे में हैं।
- Project की हर पुरानी strategy (natural long, X0) यहाँ घाटे में है। उदाहरण:
  - green candle: 83,785 trades, −0.17%/trade;
  - TSMOM20: −0.17%;
  - RSI 30: 61% सही होकर भी −0.05%।
  - अपवाद सिर्फ़ S/R bounce है (spot +0.45%, futures +1.09%)। पर वह random से बेहतर नहीं (z −0.28 / 0.84), इसलिए FAIL।

**एकमात्र PASS: `L2 | T_EMAX50_200 | long contra | X0 | F1_TREND200` (spot 15m)**

**नियम** (सीधी भाषा में):
- 15-मिनट chart पर जैसे ही EMA50, EMA200 के **नीचे** जाए ("death cross"), और उसी candle का close SMA200 के **ऊपर** हो (यानी गिरावट हल्की है, बड़ा trend अभी ऊपर), तब अगली candle के open पर **खरीदो**।
- EMA50 वापस EMA200 के ऊपर जाए, तब बेचो। कोई stop नहीं।

| माप | मान |
|---|---|
| Trades (2017-09 → 2026-08) | 55 (45 सही, 10 गलत), हर 2 महीने में ~1 |
| औसत net (fee 0.17% round trip के बाद) / median | **+0.488%** / +0.360% |
| D / V / H | +0.533% / +0.251% / +0.706% |
| H में 2 गुना fee पर / 1 candle देर से entry पर | +0.535% / +0.777% |
| हर साल (2017–2026) | 10 में से 10 साल positive (5 eligible साल, 5/5) |
| Random entry से बेहतर | z = 5.47 |
| t / BH q (job के अंदर) / DSR | 4.69 / **0.046** (सीमा 0.05) / **0.958** (सीमा 0.95) |
| Max drawdown (trade क्रम में) / 9 साल का कुल | 1.6% / +30.5% (≈ 3%/साल, समय का सिर्फ़ 1% बाज़ार में) |

**ज़मीनी जाँच:**
- Verifier के अलग pure-Python replay ने **55/55 trades हूबहू** मिलाए (समय बराबर, net का फ़र्क ≤ 1.7e-9)।
- Look-ahead test पहले से PASS था।
- सारे 55 trades: `RUN_…/pass_check/spot_15m_cfg2240_trades.csv`।

**ईमानदार फ़ैसला: यह "साबित edge" नहीं है। कारण:**
1. **यह किनारे पर पास हुआ।** q 0.046 (सीमा 0.05) और DSR 0.958 (सीमा 0.95)।
2. **पूरे study के हिसाब से** (post-hoc, lock किया हुआ नहीं; सारे 22 jobs के 1,38,931 configs एक साथ): q = **0.162**, और DSR = 0.854 (job का V और N = सारे configs; pooled V से 0.002)। यानी पूरे study की गिनती में यह PASS **नहीं** रहता (`report/posthoc_studywide.md`)।
3. **पड़ोसी timeframes पर नहीं टिका:**
   - spot 30m: 28 trades, −0.15%, H −2.19%;
   - spot 1h: 11 trades, −0.33%;
   - futures 30m: 23 trades, −0.25%;
   - spot 5m: 121 trades, −0.17%;
   - spot 1m: 763 trades, −0.09%।
4. **Futures 15m पर दोहराव अच्छा है:** 46 trades, 91.3% सही, +0.37%, D/V/H सब positive, z 3.49। पर futures का data 2020 से है, इसलिए वहाँ INSUFFICIENT।
5. **Stop लगाते ही घाटा:** यही नियम 2 ATR stop के साथ spot पर −0.11% (41.8% सही) और futures पर −0.13% देता है।
   - यानी profit इस पर टिका है कि गिरावट को झेलो और BTC के वापस आने का इंतज़ार करो। यह §3.3 वाला "dip खरीदो" pattern ही है, छोटे timeframe पर।
6. **पैसे के हिसाब से छोटा है:** ~3% सालाना, जबकि buy-and-hold ~38% सालाना था।

**दर्जा:** lock किए नियमों के हिसाब से PASS। पर पूरे study की गिनती के बाद यह "forward paper tracking का candidate" है, असली पैसे का नहीं।

### 3.9 5 मिनट (5m)

| | spot 5m | futures 5m |
|---|---|---|
| Candles | 9,57,865 | 7,09,920 |
| Unique configs / trades | 4,970 / 13,86,89,610 | 9,978 / 20,53,44,878 |
| PASS / FAIL / INSUFFICIENT | **0** / 4,940 / 30 | **0** / 9,915 / 63 |
| Gross > 0 / net > 0 configs | 50.2% / **0.8%** | 42.0% / **0.9%** |
| Trade win rate | **19.4%** | 27.0% |
| Funnel G1 → +G2 → +G4 → +G6 | 4,940 → 4 → 0 → 0 | 9,915 → 12 → 4 → 4 |
| सबसे ऊँचा DSR | 0.000 | 0.013 |
| हर संभव 1-candle trade: long / short PASS | **11.4% / 11.3%** | 20.5% / 20.3% |

**मुख्य बातें:**
- **5 मिनट पर fee से पहले की कमाई ही सिक्का है।** Spot पर 50.2% configs gross positive, futures पर 42.0%।
- **Fee के बाद 99% से ज़्यादा configs घाटे में हैं।** हर 5 मिनट पर long लेने पर spot में सिर्फ़ 11.4% बार fee निकलती है।
- **Spot 15m का PASS config यहाँ:** spot 5m पर 121 trades, −0.17%; futures 5m पर 80 trades, +0.15%, z 1.73। दोनों FAIL।
- **Top (futures):** "EMA 50/200 contra short + trend filter", 116 trades, 84.5% सही, +0.18%, z 2.62। यह 15m वाले PASS का short रूप है। FAIL (DSR 0.013)।

### 3.10 1 मिनट (1m)

| | spot 1m | futures 1m |
|---|---|---|
| Candles | 47,89,278 | 35,49,600 |
| Unique configs / trades | 4,989 / **67,81,69,780** | 9,978 / **1,01,26,64,143** |
| PASS / FAIL / INSUFFICIENT | **0** / 4,978 / 11 | **0** / 9,940 / 38 |
| Gross > 0 / net > 0 configs | 54.7% / **0.2%** | 49.5% / **0.2%** |
| Trade win rate (सारे trades) | **9.3%** | **15.8%** |
| Funnel G1 → +G2 → +G4 → +G6 | 4,978 → 1 → 0 → 0 | 9,940 → 4 → 0 → 0 |
| सबसे ऊँचा DSR | 0.000 | 0.000 |
| हर संभव 1-candle trade: long / short PASS | **3.3% / 3.2%** | **7.7% / 7.7%** |

**Spot 1m की सच्चाई:**
- **औसत 1-मिनट चाल 0.058% है, जबकि spot की round-trip fee 0.17%।** यानी एक मिनट की औसत चाल fee का एक-तिहाई भी नहीं।
  - हर मिनट long लेने पर सिर्फ़ 3.3% बार fee निकली।
  - 16 मिनट hold करने पर भी सिर्फ़ 20.8% बार।
- **Gross बिल्कुल सिक्का है:** configs का median gross +0.0004% (शून्य) और median net −0.17% (ठीक fee जितना)।
  - यानी 1m पर किसी भी indicator में दिशा की कोई ऐसी जानकारी नहीं है जो fee का छोटा-सा हिस्सा भी निकाल सके।
- **Project rules (natural long, X0):** सब ठीक fee जितने घाटे में हैं (−0.15% से −0.18%)।
  - Green-candle नियम ने 1m पर 11,43,618 trades लिए। सिर्फ़ 6.1% सही रहे, औसत −0.166%।
  - सबसे अच्छा S/R bounce है: gross +0.08%, फिर भी net −0.09%।
- **Futures 1m:** 1 अरब से ज़्यादा trades।
  - Configs का median gross ठीक 0.000%, और median net −0.092% (ठीक futures fee जितना)।
  - Green-candle नियम: 8,83,731 trades, 10.6% सही, −0.092%।
- 15m वाला PASS config 1m पर: spot 763 trades (−0.09%), futures 512 trades (−0.04%) → दोनों FAIL।
- पुराने micro-momentum (1s) और fee-hurdle map वाले नतीजे से पूरी तरह मेल खाता है: **1 मिनट पर trading fee के बाद असंभव है।**

---

## 4. सारे timeframes एक साथ

**4.0 हर timeframe × market का सार (22 jobs):**

| TF | Market | Configs | Trades | PASS | FAIL | INSUFF | Gross > 0 | Net > 0 | Trade win | हर-candle long PASS | सबसे ऊँचा DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1m | spot | 4,989 | 678,169,780 | **0** | 4,978 | 11 | 54.7% | 0.2% | 9.3% | 3.3% | 0.000 |
| 1m | futures | 9,978 | 1,012,664,143 | **0** | 9,940 | 38 | 49.5% | 0.2% | 15.8% | 7.7% | 0.000 |
| 5m | spot | 4,970 | 138,689,610 | **0** | 4,940 | 30 | 50.2% | 0.8% | 19.4% | 11.4% | 0.000 |
| 5m | futures | 9,978 | 205,344,878 | **0** | 9,915 | 63 | 42.0% | 0.9% | 27.0% | 20.5% | 0.013 |
| 15m | spot | 4,951 | 46,494,936 | **1** | 4,912 | 38 | 61.4% | 3.2% | 27.1% | 20.6% | 0.958 |
| 15m | futures | 9,937 | 68,648,793 | **0** | 9,843 | 94 | 44.5% | 3.1% | 33.4% | 30.3% | 0.801 |
| 30m | spot | 4,951 | 23,338,139 | **0** | 4,897 | 54 | 67.3% | 10.0% | 31.8% | 26.7% | 0.332 |
| 30m | futures | 9,902 | 34,361,791 | **0** | 9,709 | 193 | 46.9% | 7.9% | 36.6% | 35.3% | 0.514 |
| 1h | spot | 4,945 | 11,625,383 | **0** | 4,845 | 100 | 70.1% | 20.6% | 35.9% | 32.2% | 0.347 |
| 1h | futures | 9,893 | 17,161,168 | **0** | 9,625 | 268 | 49.8% | 15.5% | 39.2% | 39.2% | 0.938 |
| 4h | spot | 4,936 | 2,935,333 | **0** | 4,577 | 359 | 76.2% | 52.5% | 41.8% | 41.2% | 0.743 |
| 4h | futures | 9,799 | 4,343,058 | **0** | 8,615 | 1,184 | 51.7% | 35.8% | 42.5% | 45.2% | 0.760 |
| 8h | spot | 4,882 | 1,382,394 | **0** | 4,039 | 843 | 76.6% | 62.7% | 43.8% | 43.7% | 0.725 |
| 8h | futures | 9,673 | 2,032,791 | **0** | 6,932 | 2,741 | 52.9% | 44.6% | 43.7% | 46.8% | 0.572 |
| 1d | spot | 4,841 | 452,449 | **0** | 2,309 | 2,532 | 79.4% | 74.6% | 46.4% | 47.7% | 0.707 |
| 1d | futures | 9,632 | 645,904 | **0** | 2,691 | 6,941 | 54.9% | 52.4% | 44.8% | 48.3% | 0.999 |
| 1w | spot | 4,275 | 51,251 | **0** | 105 | 4,170 | 80.1% | 79.1% | 51.2% | 52.1% | 0.496 |
| 1w | futures | 8,305 | 69,490 | **0** | 60 | 8,245 | 54.0% | 53.1% | 46.2% | 50.9% | 0.086 |
| 1mo | spot | 2,730 | 8,837 | **0** | 0 | 2,730 | 82.1% | 81.9% | 58.6% | 52.3% | — |
| 1mo | futures | 4,926 | 10,947 | **0** | 0 | 4,926 | 48.0% | 45.8% | 44.6% | 53.8% | — |
| 1y | spot | 168 | 40 | **0** | 0 | 168 | 88.9% | 88.9% | 82.5% | 66.7% | — |
| 1y | futures | 270 | 63 | **0** | 0 | 270 | 47.8% | 45.7% | 47.6% | 66.7% | — |
| **कुल** | | **138,931** | **2,248,431,178** | **1** | 102,932 | 35,998 | | | | | |

**4.0b पुरानी project strategies: natural long, X0 (सिर्फ़ signal exit), औसत net प्रति trade**

*spot:*

| Rule | 1m | 5m | 15m | 30m | 1h | 4h | 8h | 1d | 1w | 1mo | 1y |
|---|---|---|---|---|---|---|---|---|---|---|---|
| O_BB20_2 | -0.16% | -0.14% | — | — | — | — | — | — | — | — | — |
| O_CONNORS | -0.16% | -0.14% | -0.13% | -0.05% | +0.02% | -0.37% | +0.13% | -0.00% | +1.93% | +13.81% | — |
| O_RSI14_30_70 | -0.15% | -0.09% | -0.05% | -0.18% | -0.15% | -0.51% | +0.80% | +4.50% | +25.96% | — | — |
| P_DOUBLE | -0.17% | -0.18% | -0.17% | -0.11% | -0.06% | +2.47% | +3.70% | +9.70% | +54.05% | +121.40% | — |
| P_GREEN | -0.17% | -0.17% | -0.17% | -0.18% | -0.18% | -0.17% | -0.07% | +0.07% | — | +23.49% | +118.32% |
| P_MICRO3 | -0.17% | -0.18% | -0.17% | -0.17% | -0.16% | +0.07% | +0.18% | +1.24% | +2.31% | +29.06% | — |
| P_SRBOUNCE | -0.09% | +0.31% | +0.45% | +1.71% | +1.58% | +14.85% | +5.83% | +46.60% | +306.18% | — | — |
| P_ZIGZAG3 | -0.18% | -0.17% | -0.12% | -0.00% | +0.30% | +1.58% | +3.93% | +13.60% | +89.72% | +54.70% | — |
| T_DONCH20_10 | -0.17% | -0.20% | -0.21% | -0.15% | +0.13% | +1.28% | +3.69% | +14.79% | +63.23% | +5.23% | — |
| T_EMAX20_50 | -0.17% | -0.16% | -0.05% | +0.14% | +0.60% | +2.56% | +7.14% | +28.23% | +117.21% | +90.59% | — |
| T_MACD12_26_9sig | -0.17% | -0.16% | -0.16% | -0.16% | -0.05% | +0.34% | +1.26% | +3.87% | +35.98% | +264.64% | — |
| T_SMA200 | -0.17% | -0.16% | -0.11% | +0.00% | +0.19% | +1.95% | +5.33% | +13.45% | +3.39% | — | — |
| T_TSMOM20 | -0.17% | -0.17% | -0.17% | -0.15% | -0.04% | +0.31% | +0.78% | +3.38% | +18.48% | +42.87% | — |
| V_LOWVOL_TS20 | -0.17% | -0.17% | -0.18% | -0.16% | -0.07% | +0.25% | +0.44% | +1.39% | +10.99% | — | — |

*futures:*

| Rule | 1m | 5m | 15m | 30m | 1h | 4h | 8h | 1d | 1w | 1mo | 1y |
|---|---|---|---|---|---|---|---|---|---|---|---|
| O_BB20_2 | -0.08% | -0.06% | -0.05% | — | — | — | — | — | — | — | — |
| O_CONNORS | -0.08% | -0.07% | -0.06% | -0.03% | +0.02% | -0.23% | +0.17% | +0.12% | -0.08% | — | — |
| O_RSI14_30_70 | -0.07% | -0.03% | -0.06% | -0.18% | -0.08% | -0.16% | -0.23% | +5.37% | +8.14% | — | — |
| P_DOUBLE | -0.10% | -0.11% | -0.06% | -0.08% | +0.04% | +1.67% | +2.42% | +17.20% | +19.04% | — | — |
| P_GREEN | -0.09% | -0.10% | -0.09% | -0.10% | -0.09% | -0.09% | +0.03% | -0.03% | +2.29% | +18.79% | +74.96% |
| P_MICRO3 | -0.10% | -0.10% | -0.09% | -0.08% | -0.08% | +0.18% | +0.17% | +1.60% | +5.23% | -5.44% | — |
| P_SRBOUNCE | -0.05% | +0.08% | +1.09% | +2.32% | +4.69% | +12.10% | +10.60% | -16.92% | +153.22% | — | — |
| P_ZIGZAG3 | -0.10% | -0.09% | -0.05% | +0.05% | +0.20% | +0.92% | +3.24% | +8.48% | +76.61% | -37.18% | — |
| T_DONCH20_10 | -0.11% | -0.12% | -0.11% | -0.07% | +0.06% | +1.11% | +2.63% | +9.92% | +34.64% | -11.48% | — |
| T_EMAX20_50 | -0.10% | -0.08% | +0.00% | +0.10% | +0.34% | +1.46% | +4.01% | +16.73% | +88.32% | +13.63% | — |
| T_MACD12_26_9sig | -0.10% | -0.09% | -0.08% | -0.08% | +0.01% | +0.16% | +0.96% | +2.67% | +24.92% | +159.12% | — |
| T_SMA200 | -0.09% | -0.08% | -0.04% | +0.03% | +0.20% | +1.39% | +4.04% | +8.93% | +11.14% | — | — |
| T_TSMOM20 | -0.09% | -0.09% | -0.09% | -0.07% | -0.01% | +0.22% | +0.49% | +1.86% | +15.49% | -29.14% | — |
| V_LOWVOL_TS20 | -0.09% | -0.09% | -0.10% | -0.08% | -0.04% | +0.21% | +0.19% | +0.50% | +1.44% | — | — |

*(— = उस timeframe पर trades नहीं, या वही config किसी दूसरे rule के बराबर निकला और एक बार चला; जैसे Bollinger fade = Bollinger breakout contra, 30m और ऊपर।)*

**4.0c सारे timeframes की overall ranking, top 15** (n ≥ 30; PASS पहले, फिर पास gates, फिर t)। पूरे 30: `report/cross_tf_overall_top30.csv`

| # | TF | Market | Config | फ़ैसला | Gates | n | सही % | औसत net | H | z | q | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 15m | spot | `L2|T_EMAX50_200|long_con|X0_SIG|F1_TREND200` | PASS | 7 | 55 | 81.8 | +0.488% | +0.706% | 5.47 | 0.046 | 0.958 |
| 2 | 8h | spot | `L2|T_EMAX9_21|long_con|X0_SIG|F4_HIGHVOL` | FAIL | 4 | 90 | 77.8 | +2.318% | +0.998% | 3.04 | 0.065 | 0.488 |
| 3 | 1d | spot | `L2|T_KAMA10|long_con|X0_SIG|F4_HIGHVOL` | FAIL | 4 | 95 | 82.1 | +2.130% | +1.666% | 2.67 | 0.079 | 0.209 |
| 4 | 8h | spot | `L2|T_VWAP50|long_con|X0_SIG|F4_HIGHVOL` | FAIL | 4 | 138 | 81.2 | +1.122% | +0.312% | 2.51 | 0.084 | 0.125 |
| 5 | 8h | futures | `L2|F_CHAIKIN|long_con|X0_SIG|F4_HIGHVOL` | FAIL | 4 | 183 | 70.5 | +1.110% | +0.487% | 3.31 | 0.385 | 0.061 |
| 6 | 4h | spot | `L2|T_KELT_BRK|long_nat|X2_SIG_SL2|F5_VOLUME` | FAIL | 4 | 188 | 44.7 | +1.932% | +0.109% | 2.92 | 0.087 | 0.007 |
| 7 | 4h | spot | `L3|T_EMAX20_50+V_SQUEEZE|long_nat|X2_SIG_SL2|-` | FAIL | 4 | 180 | 44.4 | +1.699% | +0.775% | 3.09 | 0.087 | 0.011 |
| 8 | 4h | spot | `L2|V_SQUEEZE|long_nat|X2_SIG_SL2|F1_TREND200` | FAIL | 4 | 140 | 46.4 | +2.019% | +0.290% | 3.05 | 0.087 | 0.053 |
| 9 | 8h | spot | `L1|T_BB_BRK|long_nat|X1_SIG_SL1|-` | FAIL | 4 | 169 | 36.1 | +2.560% | +0.302% | 2.76 | 0.084 | 0.000 |
| 10 | 8h | spot | `L4|VOTE_TREND_k8of10|long_nat|X0_SIG|-` | FAIL | 4 | 328 | 34.1 | +1.292% | +0.017% | 2.82 | 0.084 | 0.000 |
| 11 | 1d | spot | `L2|T_EMA20|long_con|X0_SIG|F4_HIGHVOL` | FAIL | 4 | 74 | 83.8 | +1.844% | +1.290% | 2.01 | 0.146 | 0.277 |
| 12 | 8h | spot | `L3|T_MACD12_26_9sig+T_DONCH20_10|long_nat|X0_SIG|-` | FAIL | 4 | 220 | 43.2 | +1.777% | +0.442% | 2.60 | 0.084 | 0.000 |
| 13 | 4h | spot | `L2|O_CMO14|long_con|X2_SIG_SL2|F5_VOLUME` | FAIL | 4 | 163 | 43.6 | +1.711% | +0.942% | 2.96 | 0.087 | 0.019 |
| 14 | 4h | spot | `L2|P_DOUBLE|long_nat|X0_SIG|F1_TREND200` | FAIL | 4 | 106 | 54.7 | +5.130% | +0.556% | 2.64 | 0.087 | 0.134 |
| 15 | 1d | futures | `L2|T_HA1|long_con|X0_SIG|F4_HIGHVOL` | FAIL | 4 | 103 | 67.0 | +1.417% | +0.905% | 2.66 | 0.253 | 0.015 |

### 4.1 "हर संभव trade" का fee map
- Table में हर timeframe के हर candle पर long और short, दोनों लेकर देखा गया है (1 candle hold)।
- यह "perfect knowledge" वाली छत नहीं है। यह बस बताता है कि बिना किसी नियम के कितने trades fee के बाद profit में होते हैं।

| Timeframe | Spot long PASS | Futures long PASS | औसत चाल (spot) |
|---|---|---|---|
| 1m | 3.3% | 7.7% | 0.058% |
| 5m | 11.4% | 20.5% | 0.131% |
| 15m | 20.6% | 30.3% | 0.223% |
| 30m | 26.7% | 35.3% | 0.314% |
| 1h | 32.2% | 39.2% | 0.440% |
| 4h | 41.2% | 45.2% | 0.881% |
| 8h | 43.7% | 46.8% | 1.262% |
| 1d | 47.7% | 48.3% | 2.316% |
| 1w | 52.1% | 50.9% | 6.636% |
| 1mo | 52.3% | 53.8% | 15.945% |

**मतलब:**
- Timeframe जितना छोटा, उतनी ज़्यादा fee खाती है।
- Spot की fee (0.17% round trip) futures (0.092%) से लगभग दोगुनी है। इसलिए छोटे timeframes पर futures के ज़्यादा trades पास होते हैं।
- 1 दिन और उससे ऊपर fee रुकावट नहीं रहती, पर वहाँ दिशा पहचानना सिक्के जैसा है।
- यह पुराने fee-hurdle map (27 अक्टूबर) से मेल खाता है।

### 4.2 Stop-loss: किस timeframe पर मदद करता है?
**Paired तुलना:** एक ही rule और दिशा के साथ, stop वाला exit बनाम सिर्फ़ signal वाला exit (X0)।

**Spot:**
- हर timeframe पर ज़्यादातर stops ने नतीजा **बिगाड़ा**।
- 1 / 2 / 3 ATR stop के बाद सिर्फ़ 5–40% rules बेहतर रहे।
- Trailing और target वाले exits में सिर्फ़ 0–18% rules बेहतर रहे।
- **कारण:** spot पर हर exit और re-entry पर 0.17% fee लगती है। Stop से trades टूटते हैं और fee बढ़ती है। साथ ही BTC की चढ़ाई में stop अक्सर वापसी से पहले बाहर निकाल देता है।

**Futures:**
- Stops का असर लगभग शून्य है (38–62% rules बेहतर)।
- Daily और weekly पर 1 ATR stop थोड़ा मदद करता है (62% / 77% rules बेहतर)।

**निचोड़:**
- Stop-loss से किसी भी timeframe पर कोई नियम "हार से जीत" में नहीं बदला।
- Stop का असली काम risk (drawdown) काबू करना है, edge बनाना नहीं। यह बात DDX study से भी मेल खाती है।

**Execution की मान्यताओं का असर:**
- "Stop और target एक ही candle में छुए" वाले trades हर timeframe पर ≤ 0.02% हैं। इसलिए "stop पहले" वाली मान्यता से नतीजे नहीं बदलते।
- Gap से stop के पार fill होना भी लगभग शून्य है (BTC 24×7 चलता है)।

### 4.3 Long बनाम short, natural बनाम contra
- **Shorts:** हर timeframe पर, futures में shorts के 0–32% configs ही positive हैं। BTC की 9 साल की चढ़ाई में short हमेशा हारा।
- **Natural long:** 4h और उससे ऊपर positive हैं, पर यह ज़्यादातर बाज़ार की चढ़ाई (beta) है।
  - Random-entry control से बेहतर (z ≥ 2) सिर्फ़ 1–4% configs हैं।
- **Contra long** (गिरावट या कमज़ोरी पर खरीदना) ने high-vol filter के साथ सबसे अच्छे नतीजे दिए। यह §3.3 वाला pattern है।

### 4.4 पुरानी project strategies (natural long, X0) हर timeframe पर
पूरी table ऊपर §4.0b में है।

**छोटे timeframes (5m–1h):** लगभग हर पुराना नियम घाटे में है।
- Green-candle नियम हर timeframe पर 1d से नीचे −0.07% से −0.18% प्रति trade है।
- RSI 30 (N1 sleeve B) सिर्फ़ 8h (+0.80%) और 1d (+4.50%) पर positive है, पर trades कम हैं।

**बड़े timeframes:** trend नियमों (EMA 20/50, Donchian, SMA200, MACD) का औसत positive है, पर median trade negative है। यानी कुछ बड़े bull trades औसत खींचते हैं।

**N1 / ECO में live नियम:**
- सिर्फ़ BTC पर, अकेले, कोई भी नियम gates पास नहीं करता।
- इससे live system पर कोई नया सवाल नहीं उठता। ECO की असली ताकत कई coins में से चुनना (cross-sectional selection) है, जो इस BTC-only test में शामिल ही नहीं है (§1.3)।

---

## 5. ईमानदार सीमाएँ (जो इस test से साबित नहीं होता)

1. **H (2025-01 → 2026-09) पूरी तरह अनदेखा नहीं था।**
   - पुरानी studies ने यह दौर दूसरे नियमों के लिए देखा था।
   - इसलिए यहाँ का कोई भी PASS "आगे forward जाँचने लायक" है, साबित नहीं।
2. **Multiple testing बहुत बड़ा है:** 1,38,931 configs।
   - Gates G3 (BH) और G7 (DSR) हर job के अंदर लगे, जैसा lock हुआ था।
   - पूरे study की गिनती (post-hoc) में spot 15m का PASS नहीं टिकता (§3.8)।
3. **Execution की मान्यताएँ:**
   - entry candle के open पर taker fill, impact 0.01%;
   - candle के अंदर stop/target में "stop पहले" (ऐसे trades ≤ 0.02%);
   - 2026 के spot 1m bars 1-second data से बने हैं (~4% minutes में open 1 tick अलग)।
4. **Futures liquidation (1x, सिर्फ़ short):** मिली हुई funding margin में नहीं जोड़ी गई।
   - इसका असर सिर्फ़ उन बहुत लंबे shorts पर है जो 2020–21 में रखे गए (1w/1mo/1y पर कुछ सौ trades)।
   - वे सब configs पहले से INSUFFICIENT या FAIL हैं।
5. **Holding "candles" में गिना गया।** Spot में Binance के outage वाले minutes नहीं हैं, इसलिए वहाँ एक candle थोड़ी लंबी हो जाती है।
6. **शामिल नहीं:**
   - कई coins वाली strategies (ECO की असली ताकत);
   - trained AI models;
   - OI / order-book / options जैसे non-price data;
   - limit/maker entries और DCA/scale-in।
7. **Storage का अनुमान गलत निकला।**
   - Lock से पहले 1h पर नापकर 7.8 bytes/trade (~17.5 GB) का अनुमान लगाया था। असली आकार 10.7–13.1 bytes/trade निकला (छोटे timeframes पर ज़्यादा), यानी कुल ~29 GB।
   - कोई trade नहीं छोड़ा गया। सिर्फ़ जगह ज़्यादा लगी।
8. **एक ही rule के कुछ configs आपस में बराबर निकले** और एक ही बार चलाए गए। उदाहरण: Bollinger fade long = Bollinger breakout contra long, 30m और ऊपर। हर ऐसा जोड़ा `duplicates.csv` में दर्ज है।

---

## 6. Files: क्या कहाँ है

| चीज़ | जगह |
|---|---|
| Protocol (lock) + settings + lock SHA | `logs/btc_alltf_2026_10_28/BTC_ALLTF_PROTOCOL_PREREGISTERED.md`, `STUDY_CONFIG.json`, `BTC_ALLTF_PROTOCOL_SHA256.txt` |
| Lock के बाद code बदलाव | `logs/btc_alltf_2026_10_28/CODE_CHANGES_AFTER_LOCK.md` |
| Run (time-stamped) | `logs/btc_alltf_2026_10_28/RUN_2026-10-28T1705Z/` (RUN_INFO.json में हर code/input का SHA) |
| Spot / futures (अलग folders) | `RUN_…/spot/<tf>/` और `RUN_…/futures/<tf>/` |
| हर trade | `RUN_…/<market>/<tf>/trades.parquet` (हर trade pass/fail के साथ) |
| हर दिन | `RUN_…/<market>/<tf>/daily_overview.csv` (हर कैलेंडर दिन), `daily_groups.parquet` |
| हर config: metrics, gates, verdict, rank | `RUN_…/<market>/<tf>/configs.parquet`, top 100: `ranking_top100.csv` |
| हर संभव trade (हर candle) | `RUN_…/<market>/<tf>/every_bar.parquet` |
| इस report की tables | `RUN_…/report/*.md`, `cross_tf.md`, `baselines.csv`, `posthoc_studywide.md` |
| एकमात्र PASS के 55 trades | `RUN_…/pass_check/spot_15m_cfg2240_trades.csv` |
| Verifier की outputs | `RUN_…/verify_part*_output.txt` |
| Data की जाँच | `logs/btc_alltf_2026_10_28/bars_check.csv`, `test_engine_output.txt`, `test_lookahead_output.txt` |

**किसी दिन या config के सारे trades पूरे columns के साथ देखने के लिए:**
```bash
python src/btc_alltf/query.py --run logs/btc_alltf_2026_10_28/RUN_2026-10-28T1705Z --market futures --tf 1h --date 2025-03-10
```

---

## 9. Verification: हर नंबर दोबारा, अलग code से

**Verifier:** `src/audits/verify_btc_alltf.py`, final SHA `4f831b5e…` (`RUN_…/verifier_final_sha256.txt`)।
- यह engine (C code) को call **नहीं** करता।
- Indicators और trades plain Python loops से, protocol के text से अलग लिखे गए हैं।
- सारे 22 jobs इसी final version से जाँचे गए।

| Check | क्या जाँचा | नतीजा |
|---|---|---|
| V1 | Protocol lock SHA, settings SHA, fees.json SHA, हर bar file का SHA = manifest; results में fee = fees.json | सब PASS |
| V2 | 11 मुख्य indicators को अलग loops से दोबारा बनाया, stored states से हर candle पर मिलाया: SMA50, EMA 20/50, MACD, RSI 30/70, Bollinger fade, Donchian 20/10, TSMOM20, PSAR, Supertrend, green candle, ATR14 | हर job पर 0 फ़र्क (5m/1m पर पहले 4 लाख candles) |
| V3 | हर job के 40–46 configs (हर layer, हर exit, हर दिशा, filters) का अलग bar-by-bar replay; हर trade का समय, कारण, entry/exit price और net मिलाया। Futures funding अलग loop से दोबारा गिनी | हर trade बराबर। उदाहरण: spot 1m पर 42 लाख, futures 1m पर 38.8 लाख, futures 5m पर 12 लाख trades replay, 0 mismatch |
| V4 | हर config के n, wins, sum, mean, D/V/H, हर साल और max DD सीधे `trades.parquet` से दोबारा गिने (1m पर 67.8 करोड़ और 1 अरब rows stream करके) | हर job पर 0 mismatch |
| V5 | p-value, BH q, DSR, G1–G7 और verdict अलग code से दोबारा | सब बराबर |
| V6 | Daily, monthly और trade totals का मिलान; daily file में 2026-09-30 तक हर कैलेंडर दिन | सब PASS |
| V7 | हर duplicate config की state, filter, दिशा और exit उसके "original" के बराबर | सब PASS |
| V8 | "हर संभव trade" वाली file candles से दोबारा गिनी | सब PASS |
| V9 | Random-entry control उसी RNG से Python में हूबहू दोबारा बना | सब PASS |
| Mutation | एक trade का net बदला → V4 ने पकड़ा। एक signal बदला → V3 ने पकड़ा | दोनों पकड़े गए |
| अलग मिलान | Lock से पहले के count pass के कुल trades (2,24,84,31,178) = असली run के कुल trades | बिल्कुल बराबर |

**कुल नतीजा (final verifier, सारे 22 jobs): 971 checks, 0 FAIL।**

| Verifier output | Jobs | Checks | FAIL |
|---|---|---|---|
| `verify_final_parts1to3_output.txt` (+ mutation) | 17 (1y … 30m, spot 15m) | 744 | 0 |
| `verify_part4_output.txt` | futures 15m, spot 5m, futures 5m | 134 | 0 |
| `verify_part5_spot1m_output.txt` | spot 1m | 46 | 0 |
| `verify_part6_futures1m_output.txt` | futures 1m | 47 | 0 |

- Final version से पहले का verifier भी parts 1–3 पर 750/750 PASS था। फ़र्क सिर्फ़ एक loop की गति का है (`CODE_CHANGES_AFTER_LOCK.md` entry 2)।
- Futures 1m पर: 38.8 लाख trades replay हुए; 1,01,26,64,143 stored trades से 9,968 configs के metrics दोबारा गिने गए; daily total trades के total से बराबर निकला।

**Run से पहले के tests (§2):** engine 19/19, look-ahead 4,630/4,630 (canary पकड़ा गया), data checksum 173/173।

**Files:** हर job की `DONE.json` में उसकी हर file का SHA है, और `RUN_…/RUN_MANIFEST.csv` में सारे 22 jobs की सूची (कुल 28.8 GB)।

---

## 10. आगे क्या (सिर्फ़ विकल्प; फ़ैसला आपका)

1. **Forward paper tracking, बिना पैसे के:**
   - (a) spot 15m का PASS config;
   - (b) 1d "high-vol dip-buy" family (Williams %R oversold + high-vol, और EMA/SMA200 के नीचे गिरने पर खरीदना)।
   - दोनों के नियम पूरी तरह तय हैं, इसलिए आज से आने वाला data इनके लिए सच में "अनदेखा" होगा।
   - इसमें VM पर एक छोटा recorder और crontab बदलना होगा, जिसके लिए आपकी इजाज़त चाहिए।
2. **इसी ढाँचे को कई coins पर चलाना।** ECO की असली ताकत वहीं है। यह एक नया study होगा, अपने protocol के साथ।
3. **छोटे timeframes (1m–30m) को अब बंद मानना।** इस study ने 1.7 अरब से ज़्यादा 1m trades से दिखा दिया कि fee के बाद वहाँ कुछ नहीं बचता।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।
