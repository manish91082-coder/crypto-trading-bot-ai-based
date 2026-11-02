# 1D Rebuild — Step 1 और Step 2 रिपोर्ट (Data + Swing Study)

**तारीख:** 12 अक्टूबर 2026 (2020–21 data जोड़ने के बाद update)
**GitHub:** कुछ नहीं किया गया।

**Code:**
| फाइल | काम |
|---|---|
| `src/downloaders/extend_1d_history_2020.py` (नई) | 2020-01 → 2021-09 का data, checksum जाँच के साथ |
| `src/analytics/swing_study_1d.py` (नई) | swing study |

**Outputs:**
- `logs/swing_study_1d/`
- `logs/download_1d_2020_2021_checksum_log.csv`

---

## Step 1 — Data

**कहाँ से और कैसे जोड़ा गया**
- 2020-01 → 2021-09 का 1D data **Binance Vision की public monthly files** से लिया गया।
- यह `data/raw/*_1d_Raw_5Years.csv` की मौजूदा फाइलों की शुरुआत में जोड़ा गया। File का नाम वही रखा गया है।
- कोई API key इस्तेमाल नहीं हुई।

**Zero-trust जाँच**
- **196 monthly zips, हर एक का SHA256** Binance की अपनी `.CHECKSUM` file से मिलाया गया। सब मेल खाए।
- SOL और DOT के लिए 2020-01 → 2020-07 पर Binance ने 404 दिया, क्योंकि उस समय ये listed नहीं थे। Code में नियम है कि listing के बाद एक भी महीना गायब मिले तो script रुक जाए।
- Merge के बाद script ने value-by-value जाँचा कि पुरानी rows (2021-10 के बाद) नहीं बदलीं।
- **Git diff से अलग से पुष्टि:** हर फाइल में सिर्फ नई lines जुड़ीं, **0 lines हटीं या बदलीं।**
- `audit_data_integrity.py` फिर से चलाया: **100% PASS, 0 gaps।**

**अब data की अवधि**
| Coins | शुरुआत | अंत | Days |
|---|---|---|---|
| 8 coins | 2020-01-01 | 2026-09-30 | 2,465 |
| SOL | **2020-08-11** | 2026-09-30 | 2,242 |
| DOT | **2020-08-18** | 2026-09-30 | 2,235 |

**Data की असामान्य बातें (raw file में कोई बदलाव नहीं)**
- **LINKUSDT 2020-03-12: low = $0.0001**, जबकि उस दिन open $3.82 और close $1.99 था। यह 99.99% की wick है, यानी नामुमकिन print।
  - सिर्फ swing study में इसे body तक सीमित किया गया।
  - दर्ज: `data_anomalies_clipped_1d.csv`
- **2025-10-10:** 6 coins (XRP, ADA, DOGE, DOT, LTC, LINK) में एक साथ 45–78% की नीचे वाली wick।
  - कई coins में एक साथ ऐसा होना असली market crash का संकेत है, इसलिए इसे वैसा ही रखा गया।
  - Backtest में इस दिन stop-loss बहुत खराब कीमत पर भरेगा, यह Step 3 में गिना जाएगा।
- **BTC 2020-03-13: low $3,782.13** (COVID crash), data में दर्ज है।

**ध्यान दें:** पुरानी script `src/pipeline_1d/step2_lock_vault.py` research rows की गिनती 1,188 मानकर assert करती है। Data बढ़ने के बाद वह fail होगी। वह पुरानी pipeline का हिस्सा है, और नई pipeline में research/vault की सीमाएँ नए data के हिसाब से तय होंगी।

---

## Step 2 — Swing की परिभाषा

**1. Candle को ticks में बदलना**
- हर daily candle को 4 ticks की एक लाइन माना गया:
  - Green candle: O → L → H → C
  - Red candle: O → H → L → C

**2. ATR ZigZag**
- Swing तब confirm होता है जब price उस swing point से K × ATR_14 उलटा चले।
- K = 2, 3, 4 पर study की गई। मुख्य table K = 3 पर है।
- Confirm होने के बाद अगर price उस swing के शुरुआती pivot को तोड़ दे, तो वह confirmation "FAILED" दर्ज होता है।

**3. Verification**
- हर leg पर जाँचा गया कि:
  - swing high = उस leg का सबसे ऊँचा tick, swing low = सबसे नीचा tick;
  - pivots बारी-बारी (high, low, high...) आते हैं;
  - confirmation pivot के बाद आता है।
- **10 coins × 3 K values, सब पास।**

**4. Columns का बँटवारा**
- `HS_` वाले columns भविष्य देखकर बने हैं। ये **सिर्फ study के लिए** हैं, model feature कभी नहीं बनेंगे।

---

## Tables (`SWING_STUDY_1D.xlsx`)

| Sheet | क्या है |
|---|---|
| `Daily_Ledger_All_Coins` | 2020 से 2026 तक हर coin का हर दिन: OHLC, ATR%, उस दिन confirm हुआ swing, आखिरी confirmed दिशा। Hindsight: leg, leg का कौन सा दिन, leg का आकार |
| `Daily_Market` | हर दिन 10 coins में कितने up/down leg में, कितने नए confirmations |
| `Swing_Legs` | हर swing leg (K = 2/3/4): move %, दिन, confirm lag, entry के बाद बचा हिस्सा, MAE, zigzag capture |
| `Confirmation_Events` | हर real-time confirmation और उसका नतीजा (held या FAILED) |
| `Summary` | K / coin / अवधि / दिशा के हिसाब से सारांश |

---

## मुख्य तथ्य (K = 3, data से निकले)

**Swings की गिनती और आकार**
- हर coin पर साल में औसतन **15.4 swing legs**।
- Research अवधि (2020–2024) में:

| | आकार (median) | अवधि | Confirm में देरी |
|---|---|---|---|
| Up legs | **52%** | ~27 दिन | **10.6 दिन** |
| Down legs | **30%** | ~21 दिन | **6.3 दिन** |

**Confirmation के बाद क्या बचता है**
- Confirm के बाद अगले दिन entry लेने पर median स्तर पर leg का सिर्फ **~49%** बचता है।
- 22% legs में confirmation आने तक leg पूरा हो चुका होता है (tradable 78.3%)।

**सबसे अहम खोज: औसत बनाम median**
"Confirm पर entry, उलटा confirm होने पर exit", fee के बाद, प्रति leg:

| अवधि | Long: औसत | Long: median | Long win% | Short: औसत | Short: median |
|---|---|---|---|---|---|
| Research 2020–2024 | **+21.2%** | **+3.5%** | 59% | +3.5% | −0.2% |
| 2025–2026 | **+2.8%** | **−0.4%** | 49% | +3.8% | −0.5% |

- Long legs के कुल मुनाफ़े का **81.7% सिर्फ top 10% legs** से आया।
- **मतलब:**
  - 1D swing मुनाफ़ा कुछ ही बड़े trends पर टिका है, जैसे 2020 (Up legs median +18.4%) और 2021।
  - एक सामान्य trade लगभग break-even है।
  - इसलिए **exit ऐसा चाहिए जो बड़े winners को लंबा चलने दे और छोटे losses जल्दी काटे।** Fixed TP बड़े trends को काट देगा।

**Coins के बीच अंतर (median capture प्रति leg)**
- सबसे ज़्यादा: DOGE +7.5%, SOL +5.1%।
- सबसे कम: BTC −2.1%, ETH −1.7%।
- ये पीछे देखकर निकले आँकड़े हैं। **इनसे coins चुनना selection bias होगा।**

**False signals**
- K = 3 पर 1,020 confirmations में से 17 (1.7%) बाद में FAILED हुए।

---

## अगला कदम: Step 3 (Entry/Exit permutation, spot long-only)

यह आपकी मंज़ूरी से तय है: **सिर्फ spot, futures नहीं।**

1. **Entry के प्रकार:** swing confirmation, confirmed up-leg में pullback, N-दिन breakout, और BTC regime filter, इनके combinations।
2. **Exit के प्रकार:** ATR stop-loss, ATR trailing, उलटा swing confirmation, partial + runner, time limit।
3. **चुनाव का तरीका:**
   - Anchored walk-forward: हर test साल के parameters सिर्फ उससे पहले के data पर चुने जाएँगे।
   - सिर्फ जोड़ा हुआ out-of-sample नतीजा ही दावा माना जाएगा।
   - Combinations की कुल गिनती report होगी।
4. **Realism:**
   - fee 0.075% + slippage;
   - gap पर stop-loss open price पर भरेगा;
   - कुल notional ≤ capital;
   - शुरुआती capital $10,000।
5. **AI model इसके बाद आएगा:** सिर्फ चुनी गई entries के लिए, purged walk-forward training के साथ।
