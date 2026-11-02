# 1D Swing: Step 6 (exit permutations), Step 7 (लगातार सीखने वाला AI), 6.4 (survivorship) — रिपोर्ट

**तारीख:** 13 अक्टूबर 2026 | **GitHub:** कुछ नहीं किया गया | **Mode:** Spot, long-only, $10,000, fee 0.075% + slippage 0.05% हर fill पर

**Protocol पहले लिखा गया:** `logs/strategy_1d_step6/STEP6_7_PROTOCOL_PREREGISTERED.md` कोई भी नतीजा देखने से पहले लिखा गया। फैसले उसी के नियमों से हुए।

---

## 0. सबसे ज़रूरी बातें (सीधी भाषा में)

1. **पिछला headline नंबर ($38,677, Calmar 0.866) अब नहीं टिकता।**
   - ZigZag की गलती ठीक की गई, और pre-registered तरीके से (20% reserve के साथ, लगातार account) पूरा walk-forward दोबारा चला।
   - Rules वाले system का ईमानदार OOS नतीजा: **$29,276, CAGR 20.6%, Max DD 42.3%, Calmar 0.486।**
   - पहले हर साल "ZZ4" चुना जाना छोटे बदलावों पर टिका था। 2025 और 2026 में अब दूसरे नियम चुने गए।
2. **Step 6 के नए exit नियम** (अलग K पर exit, swing-low stop, breakeven, structure trailing, आपका 75/25 runner) walk-forward में **एक बार भी नहीं चुने गए**।
   - Union = baseline, इसलिए Step 6 **REJECT** (pre-registered नियम)।
3. **AI (Step 7)** pre-registered नियम पर **पास** हुआ:
   - $42,117, CAGR 28.4%, Calmar 0.568 (rules के 0.486 से बेहतर), और 6 में से 3 साल rules से बेहतर।
   - पर **Max DD 50.1%** है, जो 2024-12-08 से 2026-06-30 तक चला, और 30-09-2026 तक **recover नहीं हुआ**।
4. **AI की असली ताकत छोटी है।** Random labels पर सिखाए गए "नकली AI" ने भी Calmar 0.474 दिया।
   - यानी ज़्यादातर नतीजा "हर swing confirmation पर entry" से आता है। सीखने वाला हिस्सा थोड़ा ही जोड़ता है।
5. **Survivorship check (6.4) सबसे बड़ा झटका है।**
   - हर साल उस समय के top-10 coins (volume से, 30 coins में से, डूबे हुए LUNA, FTT, EOS, MATIC भी शामिल) लेने पर वही AI: **$18,719, CAGR 11.5%, DD 57.2%, Calmar 0.20।**
   - 10 पक्के coins वाला नतीजा इसलिए अच्छा दिखता है कि वे 2026 की नज़र से चुने गए हैं, खासकर SOL।
6. **असली पैसे के लिए: तैयार नहीं।** Testnet पर AI system चालू है, उसमें असली पैसा नहीं है।

---

## 1. Step 6.0: ZigZag fix

- **गलती:** confirm हुआ swing फेल हो जाए तो system की दिशा पुरानी ही बनी रहती थी।
- **Fix:** फेल होने के पल पर नई दिशा का "flip" event लिखा जाता है।
- **सबूत:**

| Audit | नतीजा |
|---|---|
| R1 | Fix बंद करने पर नया engine पुराने (frozen) engine जैसा ही: 66 configs × 2 reserves, **35,194 trades** और सारी equity rows एक जैसी |
| R2 | पुराने Step 4b के yearly नतीजे हूबहू दोबारा बने |
| R3 | Fix चालू करने पर swing table (pivots) वही रही; नए events की गिनती = failed confirmations की गिनती |
| T1–T5 | पुराने strategy audits fix के साथ फिर पास |

## 2. Step 6: exit/stop/capital permutations

**Engine में नए नियम** (हर position अपना exit plan entry के समय तय करती है):
- exit का अलग swing पैमाना (K2/K3/K4);
- swing low (×0.995) पर stop;
- breakeven;
- K2 higher-low पर structure trailing;
- आंशिक profit, runner lock और runner trail;
- inactivity exit।

**`config.py` का "Law #6" (75/25):** 75% profit +3 ATR पर, 25% runner 2 ATR trailing पर, BE 1.5 ATR, 14 दिन inactivity। इसे बिल्कुल लिखे हुए नियम के मुताबिक test किया गया।
- यह नियम पहले वाले नए 1D system में **था ही नहीं**। पिछली रिपोर्टों में इसका ज़िक्र न होना एक कमी थी।

**Audits (सब PASS):**
- S1: 75/25 runner का हाथ से किया हिसाब cent तक मिला।
- S2: inactivity exit सही दिन पर हुआ।
- S3: 203 trades में swing stop = swing low × 0.995 पाया गया; 182 trades Step-2 की swing table से मिलान हुए।
- S4: भविष्य का data बिगाड़ने पर पहले के trades नहीं बदले।
- S5: साल-दर-साल carry = एक लगातार run।
- W1–W3: selection सिर्फ पिछले data से हुआ; 230 OOS trades raw CSV से दोबारा जाँचे गए।

**Walk-forward नतीजा (लगातार account, 2021-01-01 → 2026-09-30):**

| | Rules (baseline, 9,072 configs) | Step 6 (+128 नए exit configs) |
|---|---|---|
| चुने गए configs | 2021 ZZ3 · 2022 BO20 · 2023–24 ZZ4 · 2025 PB2 · 2026 PB1 | **हूबहू वही** |
| Final | $29,276 | $29,276 |
| CAGR / Max DD / Calmar | 20.6% / 42.3% / 0.486 | वही |

**फैसला:** नए exit नियम पिछले data (IS) पर कभी सबसे अच्छे नहीं निकले, इसलिए Step 6 **REJECT**।

## 3. Step 7: swing permutation matrix + हर महीने सीखने वाला AI

**Entry × exit permutation matrix:**
- **1,877 entries:** हर coin पर हर K2/K3/K4 up-confirmation, flip भी शामिल।
- **13 exit plans:** stop {1.5 ATR, swing low} × exit {K2, K3, K4} × breakeven {नहीं, 2 ATR}, + 75/25 runner।
- हर cell एक अलग trade है, उसी engine code से।
- File: `logs/strategy_1d_step7_ai/swing_permutation_matrix.csv`

**कौन सी entry सही, कौन सी गलत** (पूरे इतिहास पर, hindsight, सिर्फ समझ के लिए)

| Entry | BTC | संख्या | किसी exit से profit संभव था | swing-stop + K4 exit: औसत / जीत% |
|---|---|---|---|---|
| K2 | नीचे | 624 | 56% | +17.5% / 38% |
| K2 | ऊपर | 490 | 55% | +28.2% / 34% |
| K3 | नीचे | 159 | 60% | +15.9% / 41% |
| K3 | ऊपर | 283 | 61% | +24.4% / 47% |
| K4 | नीचे | 77 | 61% | **+1.9% / 30%** |
| K4 | ऊपर | 194 | **68%** | **+35.6% / 47%** |

- सबसे साफ बात: K4 entry तभी अच्छी है जब BTC ऊपर हो। BTC नीचे हो तो K4 entry लगभग बेकार है।

**कौन सा exit सही, कौन सा गलत** (1,827 पूरे trades)

| Exit plan | औसत | median | जीत% |
|---|---|---|---|
| swing stop + K4 exit | **+22.6%** | −6.2% | 39% |
| ATR 1.5 stop + K4 exit | +16.7% | −6.7% | 30% |
| swing stop + K3 exit | +11.2% | −3.0% | 43% |
| K2 exit (जल्दी exit) | +2% | −2.4% से −3.1% | 40–41% |
| **75/25 runner (Law #6)** | **+0.6%** | −0.25% | 35% |

- **75/25 नियम बड़े swings को काट देता है।** यह सबसे कमज़ोर exits में से है। AI ने इसे 1,577 में से सिर्फ 20 बार चुना।
- हर exit का median trade घाटे में है। कमाई कुछ बड़े swings से आती है।
- Hindsight ceiling: हर trade पर बाद में पता चला सबसे अच्छा exit = औसत +32.4%। यह पहले से पता नहीं चल सकता।

**AI कैसे काम करता है:**
- 21 swing-structure features, सब causal: कौन सा K fire हुआ, swing low से उछाल, पिछले swings का आकार, higher-low, wave count, BTC की swing state, market breadth आदि।
- हर exit plan का अपना model है। **हर महीने की 1 तारीख को** सिर्फ उन trades से दोबारा सीखता है जिनका नतीजा उससे पहले आ चुका हो (897 model fits)।
- सबसे अच्छी prediction > 0 हो तो trade लेता है, उसी exit plan के साथ।

**Audits (सब PASS):**
- A1: future data बिगाड़ने पर 916 candidates और 21 features नहीं बदले।
- A2: हर monthly fit में training rows की गिनती अलग code से दोबारा गिनी गई और मेल खाई। भविष्य का कोई नतीजा training में नहीं गया।
- A3: portfolio के 357 trades matrix cells से हूबहू मिले।
- A4: 2 plans × 300 trades raw CSV से अलग code के ज़रिए दोबारा बने।

**OOS नतीजे (लगातार account, 2021-01 → 2026-09):**

| | Rules (walk-forward) | **AI (हर महीने re-train)** | नकली AI (random labels) | BTC buy & hold |
|---|---|---|---|---|
| Final | $29,276 | **$42,117** | $39,344 | +188% |
| CAGR | 20.6% | **28.4%** | 26.9% | — |
| Max DD | 42.3% | **50.1%** | 56.8% | 76.6% |
| Calmar | 0.486 | **0.568** | 0.474 | — |
| Trades / जीत% / PF | 230 / 32% / 1.53 | 365 / 29% / 1.42 | 378 / 29% / 1.35 | — |
| 2021 | +79.2 | +206.4 | +229.8 | |
| 2022 | −21.9 | −30.6 | −41.3 | |
| 2023 | +64.3 | +77.3 | +77.8 | |
| 2024 | +28.2 | +46.8 | +71.8 | |
| 2025 | −12.8 | **−27.7** | −34.4 | |
| 2026 (Sep तक) | +13.9 | +5.2 | +1.4 | |

**Pre-registered फैसला:** AI का Calmar 0.568 दोनों (0.486) से ज़्यादा है, और 6 में से 3 साल वह आगे रहा। इसलिए **ACCEPT** (testnet के लिए)।

**AI की कड़वी सच्चाई:**
- **SOL अकेले +$27,136।** Net profit +$32,117 है, यानी ज़्यादातर कमाई SOL से (ज़्यादातर 2021 में)। Top-5 trades = net का 116%।
- XRP (−$6,219), LTC, DOT, ETH घाटे में रहे।
- Max DD 50.1% (peak 2024-12-08 → 2026-06-30), अभी तक recover नहीं हुआ। 69 में से 39 महीने घाटे के रहे।
- Capital का इस्तेमाल बढ़ा: median 50% पैसा लगा रहता है (rules में 12–18%)। आपकी "पैसा पड़ा न रहे" वाली माँग पूरी होती है, पर जोखिम भी बढ़ता है।

## 4. Step 6.4: survivorship check

- 20 बड़े coins का data Binance Vision से लिया गया, SHA256 checks के साथ: 1,444 files OK। LUNA, FTT, EOS और MATIC बाद में बंद या delist हुए।
- हर साल उस समय के top-10 coins लिए गए (365 दिन का USDT volume)।
- Point-in-time universe: SOL 2021 के top-10 में **नहीं** था (2022 से आया)।
- **नतीजा:** वही AI system = **$18,719, CAGR 11.5%, Max DD 57.2%, Calmar 0.20।**
- File: `logs/strategy_1d_step6_4_survivorship/`
- **मतलब:** भविष्य में असली नतीजा 10-coin backtest से काफ़ी कम हो सकता है।

## 5. Testnet bot (असली पैसा नहीं)

- पुराना task console window की वजह से बार-बार मर रहा था। 9:42 वाला run भी तुरंत 0xC000013A पर बंद हुआ और कोई log नहीं लिखा।
- अब task सीधे **`pythonw.exe`** चलाता है (कोई window नहीं), नए **AI engine** (`src/execution/live_1d_ai_engine.py`) के साथ।
- पहली run (2026-10-12 की close):
  - ETH के लिए candidate आया (plan swing|x3, predicted log-return 0.093 ≈ +9.8%);
  - **testnet पर असली market buy** हुआ: 0.3975 ETH @ 2515.5;
  - **STOP_LOSS_LIMIT order #1903401** @ 2394.08 लगा।
  - Testnet पर buy और stop order का पूरा flow पहली बार सच में चला।
- **Live engine audits:**
  - L1: day-by-day replay ने Step 7 के सारे 357 trades हूबहू दोहराए।
  - L2: live monthly training वही predictions देती है जो walk-forward ने दीं।
  - L3: सिर्फ dryrun और testnet modes हैं।
  - Mutation test: reserve 10% और plan swap, दोनों bugs audit ने **पकड़े**।
- Logs: `logs/live_1d_ai/`। हर महीने के models और training logs: `logs/live_1d_ai/models/`।
- **बाकी सीमाएँ:**
  - PC बंद हो या आप logoff करें, तो bot रुकेगा (watchdog हर घंटे फिर चालू करता है)।
  - Partial profit testnet में daily cycle पर market से बिकता है, backtest की target-price fill से थोड़ा अलग। यह 75/25 plan में ही होता है, जो बहुत कम चुना जाता है।
  - पुराना engine (`live_1d_swing_engine.py`) और उसकी state फाइल अब इस्तेमाल नहीं होती।

## 6. आगे क्या (ईमानदार राय)

1. **असली पैसा अभी नहीं।** OOS DD 42–57% है, और survivorship check में CAGR सिर्फ 11.5% आया।
2. Testnet पर AI को कम से कम 2–3 महीने चलने दें। हर महीने का नया model और उसका training log देखें।
3. अगर आगे सुधार करना है, तो वह भी नए pre-registered test से ही हो। Point-in-time universe को ही मुख्य पैमाना बनाया जाए, क्योंकि 10-coin backtest भरोसे लायक नहीं है।
4. Data साफ बताता है कि K4 entry सिर्फ BTC के ऊपर रहते अच्छी है, और जल्दी exit (K2) या 75/25 कमाई मारता है। ये विचार आगे के test के लिए हैं, पहले से पक्के दावे नहीं।

---

## 7. Addendum (13-10-2026): क्या AI ने सच में कुछ सीखा? Independent जाँच

**असली, सबूत के साथ:**
- **Data असली है।** Local CSV की 24 random candles (6 coins) को Binance API से सीधे मिलाया गया: 24/24 हूबहू मेल। 2020–21 के downloads में 196 files SHA256 verified हैं।
- **Models असली हैं।** `logs/live_1d_ai/models/models_2026-10.pkl` में 13 trained HistGradientBoosting models हैं; हर model में 200 trees और 21 features।
  - 200 candidates पर 200 अलग-अलग predictions आईं (−0.197 से +0.344), यानी output hardcoded नहीं है।
  - BTC की swing state बदलने पर prediction बदलती है।
- **Testnet order असली है।** Binance testnet API (testnet.binance.vision) से पढ़ा गया:
  - buy 0.3975 ETH @ 2515.5 (order 1903399);
  - stop order 1903401 खुला है (stop 2394.08, limit 2370.14);
  - bot की state से मेल खाता है।
- **Backtest का हिसाब असली है।** 10,000 + सारे 365 trades का P&L = $42,116.62। सबसे बड़ा trade (SOL 2021-01-05 → 2021-05-20, +$10,167) raw CSV की कीमतों से मेल खाता है।

**जो सही साबित नहीं हुआ (ईमानदारी से):**
- **अनदेखे data पर AI की predictions का असली नतीजों से कोई रिश्ता नहीं** (13 plans का औसत rank correlation −0.03)।
- Prediction के 5 हिस्सों (कम से ज़्यादा) में असली औसत return भी ऊपर-नीचे होता रहा: 10.5, 8.1, 14.6, 6.5, 13.2%। कोई साफ बढ़त नहीं।
- AI ने 95% candidates ले लिए, यानी लगभग हर swing पर entry। Random labels वाले नकली AI ने 100% लिए।
- AI के चुने exit का औसत +8.2% रहा, सारे exits का औसत +4.7%। पर नकली AI का भी +8.9% आया। यह फायदा features सीखने से नहीं आता, बस उन exits को चुनने से आता है जिनका औसत पहले से ऊँचा था।
- **निष्कर्ष:** code, models, data और orders असली हैं। पर "AI ने सही entry/exit पहचानना सीख लिया" वाला दावा data से **साबित नहीं** होता।
  - Rules से बेहतर नतीजा (Calmar 0.568 बनाम 0.486) ज़्यादातर "हर swing confirmation पर entry + ऊँचे औसत वाला exit" से आया है, सीखने से नहीं।
  - पहले "AI accepted" लिखा था। वह pre-registered नियम के हिसाब से सही था, पर यह गहरी जाँच दिखाती है कि वह नियम AI की असली समझ को परखने के लिए काफ़ी नहीं था।
