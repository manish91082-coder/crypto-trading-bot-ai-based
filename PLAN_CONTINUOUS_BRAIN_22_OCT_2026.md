# लगातार चलने वाला brain: मौजूदा ECO में scan, entry, size, exit, stop और trailing कैसे होंगे, और दो फ़ैसलों पर सलाह (22 अक्टूबर 2026)

**स्थिति:**
- सिर्फ़ योजना। कोई code नहीं लिखा गया, और VM पर कुछ नहीं बदला।
- हर बात के साथ लिखा है कि उसका सबूत कहाँ से है। जहाँ सबूत नहीं है, वहाँ साफ़ "अभी साबित नहीं" लिखा है।

---

## 0. सबसे ज़रूरी सच (पहले यह)

"लगातार चलने वाला brain" दो अलग चीज़ें हैं, और दोनों को अलग रखना ज़रूरी है:

| चीज़ | मतलब | हमारे पास |
|---|---|---|
| **लगातार देखना और फ़ैसला करना** (scan → decide → act) | हर closed candle पर सारे coins देखना, नए target बनाना, stop/exit जाँचना, order भेजना | ✅ **ECO यही करता है, हर घंटे।** 4 producers + ECO मिलकर |
| **लगातार सीखना** (model ख़ुद बदले) | हर दिन या हर घंटे model फिर से train हो | ⚠️ सिर्फ़ तय समय पर: 1D brains हर महीने re-train होते हैं, और weights हर महीने बदलते हैं। **हर घंटे सीखना हमारे data पर नुकसानदेह साबित हुआ।** |

**हर घंटे सीखना क्यों नहीं:**
- **हमारे सारे AI tests fail हुए:**
  - 4H entry AI: AUC 0.514;
  - 120 coins पर AI: 0.505;
  - trade छोड़ने वाला AI: AUC 0.54, पर पैसा घटा;
  - AI sizing: random से कम।
- **कारण:** signal बहुत कमज़ोर है और noise बहुत ज़्यादा। ऐसे में model जितनी बार बदलेगा, उतना ज़्यादा noise सीखेगा।
- **सही तरीका:** हर पल देखना और लिखना, पर तय समय पर, gate के साथ सीखना। यही साहित्य और हमारे नतीजे, दोनों कहते हैं (MASTER_INTEGRATED भाग 2, "निरंतर सीखना का ईमानदार मतलब")।

---

## 1. Brain की ताल (cadence): क्या, कब, किस timeframe पर

| ताल | क्या होता है | किस data से | अभी है? |
|---|---|---|---|
| **हर घंटे (:50 IST)** | सारे producers पढ़ना → हर coin का target → caps/trim → stops और trailing जाँच → kill switch → orders → हिसाब | 1h closed bars + producers | ✅ ECO (plan mode) |
| **हर 4 घंटे** | N1 के 4h/8h/12h/1D नियम नए signal बनाते हैं (entry/exit) | 4h…1D candles, ~130 coins | ✅ PaperN1 |
| **हर दिन** | 1D brains (D1/H4/H1) score करते हैं → top-5 long / bottom-5 short; liquidity list (≥ 50M volume) ताज़ा | 1d/4h/1h | ✅ Step16 → 16B → F4 |
| **हर महीने** | 1D brains re-train; 1D और N1 का बँटवारा (inverse-vol); E_m (sizing base) | पिछले 126 दिन के returns | ✅ |
| **हर तिमाही** | Forward data पर नए pre-registered tests। यही असली "सीखना" है | FR2 recorder + ledgers | योजना |
| **5m / 15m** | सिर्फ़ data जमा। Trade नहीं। | FR2 | ✅ (data) |

**5m पर scan क्यों नहीं:**
- Signal 4h या उससे बड़ी candle बंद होने पर ही बदलता है।
- 5m/15m/30m के हर नियम ने cost के बाद पैसा खोया (TFX)।
- हर 5 मिनट जागने से सिर्फ़ API calls और fees बढ़ेंगी, फ़ायदा नहीं।

5m का एक ही सही भविष्य का काम है: बेहतर fill (execution timing)। वह भी तभी, जब नया test पास करे। Maker entry का test पहले fail हो चुका है।

---

## 2. हर फ़ैसला कैसे होता है, और उसका सबूत

### 2.1 कहाँ trade लेना है (coin चुनना)

- **N1 A और B** (trend-long, oversold-long): 10 बड़े coins।
  - सबूत: 120 coins पर take-all ने 56% गँवाया (T14), और edge सिर्फ़ बड़े coins पर है।
- **N1 C और D** (trend-short, momentum): हर दिन वे coins जिनका 30-दिन median perp volume ≥ 50M USDT हो। लगभग 25–40 coins।
- **1D brains:** ~30 coins में से हर sleeve के top-5 long और bottom-5 short।
- **नए coin अपने-आप आते-जाते हैं:** liquidity rule से। कोई hard-coded list नहीं है, बस 10 बड़े coins A/B के लिए तय हैं।

### 2.2 कितना पैसा

**फ़ॉर्मूला:** हर coin का target = Σ (strategy का हिस्सा × महीने की शुरुआत की equity × उस sleeve का अपना हिस्सा)।
- अक्टूबर 2026 में strategy का हिस्सा: 1D 53.9%, N1 46.1%।
- उदाहरण: N1 का एक A-signal = 0.5% × 46.1% × 10,000 ≈ **23 USDT**।
- जितने ज़्यादा timeframes और नियम एक साथ "हाँ" कहें, उतना बड़ा target।

**सीमाएँ (हर घंटे लगती हैं):**

| सीमा | नियम |
|---|---|
| एक coin | ≤ 20% |
| कुल exposure | ≤ 1.5× |
| Kill switch | equity peak से 30% नीचे → सब बंद |

**N1 और ECO में फ़र्क (नया, ज़रूरी):**
- N1 paper में 20% cap सिर्फ़ entry पर लगता था, इसलिए कीमत बढ़ने पर एक coin 37% तक जा सकता था।
- **ECO में cap हर घंटे पूरे target पर लगता है।** यानी कोई coin 20% से ऊपर गया तो अपने-आप trim होगा। इससे पहले बताई "position trim" वाली कमी live में बंद हो जाती है।
- **ईमानदारी से:** backtest (E-2) ने इस हर-घंटे trim का असर नहीं नापा। Replay में cap कभी नहीं लगा, क्योंकि 46% weight पर N1 का सबसे बड़ा coin ~17% रहता है। इसका असर forward ledger में दिखेगा, क्योंकि `caps` field हर cycle में दर्ज होती है।

**जो sizing तरीके test होकर हारे (इसलिए नहीं जोड़े):**

| तरीका | dev Calmar (base 3.26) | नतीजा |
|---|---|---|
| Inverse-vol per coin (K6) | 2.48 | ❌ |
| Correlation dampener (K3) | 2.73 | ❌ |
| Heat cap 6% (K2) | 2.50 | ❌ DD 28.6% से 22.4% घटा, पर Calmar गिरा |
| AI sizing (T20) | — | ❌ random से कम |

### 2.3 Entry

- Signal वाली candle बंद होते ही, अगले hourly cycle में market order।
- 4h signal पर देरी ≤ ~70 मिनट। 1D brains पर ~02:20 UTC।
- Maker (limit) entry fail हुई: भरे orders +0.9% पर रहे, न भरे +2.0%। यानी जो अच्छे थे, वही छूटे।

### 2.4 Exit, stop loss, trailing, take profit: हर sleeve का अपना नियम

| Sleeve | Exit | Stop loss | Trailing | Take profit | सबूत |
|---|---|---|---|---|---|
| N1 A (trend-long, 4 नियम × 4 TF) | नियम पलटे: TSMOM ≤ 0, EMA20 ≤ EMA50, MACD ≤ signal, close < 10-bar low | **नहीं** | **है, नियम के अंदर:** Donchian का 10-bar low कीमत के साथ ऊपर खिसकता है; EMA/MACD का पलटना भी trailing exit है | नहीं | 3×ATR stop: Calmar 3.26 → 2.74 (K0)। 35% stop: 4.16 → 2.90 (T19)। Top 10% trades = ~60% कमाई, target उन्हें काट देता |
| N1 B (oversold-long) | RSI > 50 | नहीं | — | **हाँ:** RSI 50 ही target है | TFX-S: सबसे robust cell |
| N1 C (trend-short) | A का उल्टा | नहीं | नियम के अंदर (10-bar high) | नहीं | Crash hedge |
| N1 D (momentum) | हर 5 दिन rebalance | नहीं | — | — | market-neutral |
| 1D long (top-5) | rank 10 से बाहर गिरे | नहीं | — | — | F7 |
| 1D short (bottom-5) | rank 10 से बाहर | **हाँ:** entry × 1.50 | नहीं | — | F7 (pre-registered PASS): DD 21%, 0 liquidation |

**सीधे शब्दों में:** हमारे trend नियमों में trailing पहले से बना है। Donchian और EMA वाले exits ही trailing stop हैं, जो trend के साथ चलते हैं और trend टूटते ही बाहर निकालते हैं।

**ऊपर से एक और trailing stop जोड़ना हमारे tests में नुकसानदेह रहा:**
- A4 में 6 exit variants का PBO 0.84 था, यानी exit tuning noise है।
- 3×ATR stop ने Calmar गिराया।

### 2.5 Stop को हर घंटे "adjust" करना: क्या जोड़ा जा सकता है

| विचार | सबूत | सलाह |
|---|---|---|
| Profit lock (break-even): +X ATR पर stop entry पर ले जाना | हमारे data पर test नहीं हुआ। मिलते-जुलते tests (3×ATR trail, exit grid) हारे | सिर्फ़ 1 pre-registered trial में, कम उम्मीद के साथ |
| Chandelier trail (high − 3 ATR) | A4 में V0 trail3ATR का exit grid noise निकला | ❌ अभी नहीं |
| Volatility बढ़ने पर size घटाना | K6 / K2 हारे | ❌ |
| **Catastrophe stop, सिर्फ़ exchange पर, VM बंद होने के लिए** | 35% stop backtest में नुकसानदेह, क्योंकि वह trigger होता है | नीचे §3.1 देखें (बीच का रास्ता) |

---

## 3. ईमानदार कमियाँ: हर एक पर मेरी सलाह और कारण

### 3.1 Exchange पर stop orders नहीं (VM बंद हो तो कोई सुरक्षा नहीं)

**सलाह (दो परतें):**
1. **1D shorts:** F6 की तरह exchange पर STOP_MARKET (reduceOnly, उसी component की मात्रा), entry × 1.50 पर। यह पहले से backtest और F6 demo में चला हुआ नियम है।
   - One-way mode का नियम: stop तभी लगे जब उस coin की net position भी short हो और कम से कम उतनी बड़ी हो। नहीं तो hourly virtual check ही रहे।
2. **N1 और 1D longs:** कोई exchange stop नहीं, क्योंकि backtest में हर stop ने कमाई घटाई। VM बंद होने का खतरा इन तरीकों से घटाएँ:
   - (a) GCP VM uptime पहले से 5+ दिन स्थिर है;
   - (b) एक "dead-man" जाँच: अगर 3 घंटे ECO न चले, तो अगला run सबसे पहले reconcile और kill-check करे। यह पहले से है।
   - (c) **बहुत दूर का एक "आपदा" stop**, liquidation से पहले की आख़िरी सुरक्षा: per-coin net position पर ~60% दूर। आम दिनों में यह कभी trigger नहीं होगा।

   (c) को पहले backtest पर नापना होगा, एक trial। सलाह: पहले नापें, फिर जोड़ें।

**कारण:** सुरक्षा उतनी ही जोड़ें जितनी backtest में Calmar न गिराए। 35% stop गिरा चुका है, इसलिए दूरी और बढ़ानी होगी, और उसे नापना होगा।

### 3.2 Demo में spot legs भी perp पर

- **सबूत:** N3 में X2 (spot/perp routing) से Calmar 3.26 से बढ़कर 3.65 हुआ, और लगभग 39% long entries spot पर गईं।
- **मतलब:** spot routing हटाने से असली पैसे में फ़र्क पड़ेगा।
- **सलाह:**
  - **Demo phase:** perp ही ठीक है। Demo का मकसद plumbing और fills नापना है।
  - **Real-money protocol:** spot execution ज़रूरी। एक ही Binance account में spot wallet और USDT-M wallet के बीच internal transfer होगा। इसे demo-spot (जिसका public endpoint चलता है, HTTP 200) पर अलग से test करना होगा।

### 3.3 Demo wallet ~5,000 (k ≈ 0.5)

- **सलाह:** अगर Binance demo में balance reset या बढ़ाने की सुविधा है, तो आप उसे 10,000+ USDT कर दें (आपके हाथ का काम)। नहीं तो k = 0.5 ठीक है।
- **कारण:** k = 0.5 पर छोटे orders min notional से छूटेंगे, जिससे tracking बिगड़ेगा। 10,000 पर असली real-money हालत की नक़ल होगी।

### 3.4 5m से 1M तक सारे timeframes

- **1W/1M:** trades बहुत कम हैं (1M पर हर cell n < 30)।
- **5m–30m:** cost के बाद हर जगह घाटा।
- **1h नियम:** DD 12% से 28%।
- **सलाह:** अभी नहीं जोड़ना। भविष्य के लिए दो अलग, छोटे tests:
  - (a) 1W trend को "context" की तरह (long का हिस्सा घटाना या बढ़ाना)। N2 regime fail हुआ था, इसलिए उम्मीद कम है।
  - (b) 5m/15m से entry timing। Maker fail हुआ था, इसलिए taker के साथ "VWAP-जैसा" बाँटकर भरना।

  दोनों नए trial budget में ही होंगे।

### 3.5 Tracking FAIL (R2) और 1D का timing

यह नीचे फ़ैसला 1 में है।

---

## 4. आपके दो फ़ैसले: मेरी सलाह और क्यों

### फ़ैसला 1: R2 tracking FAIL (1.20%)

**सलाह: (b), पर एक सुधार के साथ।**
- E-5/E-6 के forward data पर एक नया, पहले से lock किया गया tracking test चलाएँ।
- यह test executor की तुलना **"उसी timing और उसी cost वाले paper"** से करे, न कि F4 के 00:00 वाले paper से।

**क्यों:**
1. **(a) चुनना rubber-stamping होगा।** नतीजा देखकर gate ढीला करना वही गलती है जिससे हम अब तक बचते आए हैं।
2. **Post-hoc जाँच ने दिखाया कि फ़र्क executor की गलती नहीं है।**
   - Attribution identity 1e-9 तक सही है, और N1 हिस्सा 0.01% पर।
   - 1D के फ़र्क में ~41 USDT paper की cost मान्यताएँ हैं, और ~85 असली timing (paper 00:00 पर, ECO ~02:20 UTC पर भरता है)।
   - Timing असली दुनिया का हिस्सा है, उसे हटाया नहीं जा सकता। इसलिए सही पैमाना है: "executor = timing-adjusted paper ± छोटा error", और "timing का औसत असर ≈ 0?" अलग से नापा जाए।
3. **नया test बिना नया trial खर्च किए हो सकता है।** यह implementation check है, strategy search नहीं। ECO registry में इसे "check" के रूप में दर्ज करें।

### फ़ैसला 2: Demo पर असली orders (E-6) और F6 बंद करना

**सलाह: हाँ, पर इसी क्रम में, बिना जल्दबाज़ी के:**
1. E-5 plan mode के ≥ 3 दिन साफ़ हों: verifier रोज़ 7/7, कोई अनचाहा freeze नहीं।
2. Adopt tool बने और उसका test हो (mock + plan)। यह F6 के 7 shorts को ECO के 1D components में अपनाएगा और F6 के exchange stop orders रद्द करेगा। तभी cut-over होगा, वरना F6 के stop ECO की net position काट सकते हैं।
3. 1D shorts के exchange stops (§3.1-1) उसी cut-over के साथ।
4. Cut-over उस घंटे करें जब F4 या N1 का बड़ा rebalance न हो (जैसे 12:50 IST)।

**क्यों:**
1. **Demo में पैसे का खतरा शून्य है।** असली fills, slippage, funding और rejections सिर्फ़ असली exchange पर ही नापे जा सकते हैं। Paper या plan यह नहीं बता सकते।
2. **F6 बंद करने से कुछ खोता नहीं।** F6 जो 1D shorts करता था, वही अब ECO करेगा (उसी F4 फ़ैसले से), और साथ में N1 भी।
3. **दो executors एक account पर साथ नहीं चल सकते** (one-way mode), इसलिए cut-over ज़रूरी है।
4. **Real money अलग फ़ैसला रहेगा,** demo के 2–4 हफ़्ते के सबूत के बाद, नए protocol के साथ।

---

## 5. आगे का क्रम (हर कदम पर आपकी हाँ)

| # | काम | Trial? |
|---|---|---|
| 1 | E-5 plan mode 3 दिन (चल रहा है) | — |
| 2 | Tracking test protocol (timing-adjusted) lock | check, trial नहीं |
| 3 | Adopt tool + 1D-short exchange stops: code + mock tests | — |
| 4 | E-6 demo cut-over | आपकी हाँ |
| 5 | Catastrophe stop (~60%) का backtest | ECO trial 3 |
| 6 | (वैकल्पिक) Profit-lock trailing, एक variant | ECO trial 4 (कम उम्मीद) |
| 7 | Demo 2–4 हफ़्ते → real-money protocol (spot execution के साथ) | नया protocol |

ECO budget में 4 में से 2 trials बचे हैं। चरण 5 और 6 उन्हीं में होंगे। इससे आगे की research के लिए आपसे नया budget चाहिए।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
