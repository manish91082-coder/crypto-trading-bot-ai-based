# DDX: 1–7 दिन की relative strength में drawdown control (27 अक्टूबर 2026)

**आपका आदेश:** "जो suggestion दिया है वो करो, same discipline, सब ground verify करके।"

## सबूत

| चीज़ | जगह / SHA |
|---|---|
| Protocol (run से पहले lock, 10:12:55 UTC) | `logs/drawdown_ddx/DDX_PROTOCOL_PREREGISTERED.md`, SHA `12d2c5a2…` |
| Main code | `src/research/drawdown_ddx.py` (`9d2243b8…`) |
| Final-gap जाँच (run के बाद, दर्ज) | `src/research/drawdown_ddx_final_gap.py` → `final_gap_investigation.csv` |
| Independent verifier | `src/audits/verify_drawdown_ddx.py` (`51f8992b…`): अलग code, सादे loops, अपना bootstrap (seed 777) |
| Verifier नतीजा | `verify_output.txt` (`a03244ae…`): **11/11 PASS** |
| Code notes (run से पहले और बाद की हर बात) | `logs/drawdown_ddx/CODE_NOTES.md` |

---

## 0. पहले एक ज़रूरी सुधार: मेरा suggestion पुराने आँकड़े पर टिका था

पिछली report (fee-hurdle map, §5) में मैंने लिखा था कि Step 19 का drawdown 73% है और यही खुली समस्या है। Protocol लिखने से पहले मैंने project के सारे records पढ़े। उनमें दिखा:

- **73% वाला आँकड़ा पुराना है।** उसी relative-strength परिवार का drawdown बाद के trials में पहले ही घट चुका था:
  - long-short (F2): 30%;
  - stops (F7): 21%;
  - N1 के साथ जोड़ (ECO-W2): dev में 11%। यही configuration अभी demo पर live है।
- **मैंने जो तरीक़े सुझाए थे (position size, vol target, BTC hedge), वे सब पहले ही test हो चुके हैं,** और कई और भी। उसी 2021–26 data पर वे फिर से test करना data snooping होता, क्योंकि उस data पर पहले ही PBO 65% मापा जा चुका है।

**इसलिए इस study में historical data पर कुछ भी नया fit या चुना नहीं गया।** इसकी जगह दो काम किए गए:
- **(A)** पहले के 16 drawdown trials का ledger। हर आँकड़ा उनकी अपनी files से दोबारा निकाला गया।
- **(B)** live ECO के लिए आगे की drawdown band और alarm की सीमा। आगे का (forward) data ही अब साफ़ test है।

---

## 1. Part A: पहले के drawdown trials, दोबारा verify किए गए

**Verification की स्थिति:**
- **सभी 16 studies के protocol SHA मिले** (17/17 files)। Claims files में दर्ज SHA से भी मिले।
- **Equity files से दोबारा निकाले गए सभी 24 drawdown claims से मिले** (0.01 pp के अंदर)। ECO के आँकड़े 1e-9 तक मिले।
- **Final equity में 19 rows पर 0.09–0.25% का फ़र्क मिला।** जाँच में वजह पक्की हुई:
  - claims का "final" आख़िरी दिन की बिक्री fee कटने के बाद का cash है, जबकि equity file उससे पहले का mark-to-market है;
  - 14 rows यह हिसाब लगाकर 0.01 USDT तक हूबहू मिलीं;
  - 5 rows की trades file नहीं है, इसलिए वहाँ सिर्फ़ सीमा दिखाई जा सकी (फ़र्क ≤ 0.25%);
  - कोई result बदला नहीं गया।
- **Code SHA (सिर्फ़ report):**
  - F2 का code बदलाव `CODE_CHANGES_AFTER_LOCK.md` में दर्ज SHA से हूबहू मिला।
  - Step 17/18 का code lock के बाद बदला है। उसके 2 bug-fix (किसी result से पहले) दर्ज हैं, पर SHA दर्ज नहीं है, इसलिए यह कड़ी SHA से साबित नहीं हो सकती।

### कौन-सा तरीक़ा drawdown घटा सका (backtest 2021-01 … 2026-09, $10k से)

| # | तरीक़ा | Max DD: पहले → बाद | Final: पहले → बाद | Study का अपना फ़ैसला |
|---|---|---|---|---|
| A01 | Step 19 base (top-20 में RS, 80% invested) | 73.2% (BTC hold 69.3%) | $65.3k (BTC $25.1k) | PARTIAL |
| A02 | Market + veto brain (Step 17/18) | 86.2% → 74.3% | $22.6k → **$4.8k** | FAIL |
| A03 | Large-cap market gate (Step 20) | 73.2% → 73.0% | $65.3k → $10.2k | FAIL |
| A04 | Crash brain (Step 21) | 73.2% → 52.7% (random control 57.5%) | $65.3k → $121k (control $70k) | **INVALID** (luck) |
| A05 | Exit / tail brain (Step 26) | 74.7% → 75.6% | $201.5k → $91.9k | FAIL |
| A06 | **कम exposure** (D1 sleeve, f = 1 / 0.75 / 0.5 / 0.3) | 81.3 / 70.6 / 54.4 / **36.8%** | $74.5k / 62.2k / 43.2k / 27.4k | table (कोई gate नहीं) |
| A07 | Vol sizing (Step 28), fixed 50% से तुलना | 48.4% → 59.1% | $53.9k → $66.0k | FAIL |
| A08 | **Long-short** (F2), long-only से तुलना | 49.0% → **30.3%** | $53.9k → **$110.5k** | **PASS** |
| A09 | **Stop rules** (F7) | 30.3% → **21.4%** | $110.5k → $88.4k | **PASS** |
| A10 | BTC hedge (E1a / E1b) | 21.4% → 13.6% / 27.8% | $88.4k → $58.9k / $33.2k | FAIL |
| A11 | Inverse-vol weights (E4) | 21.4% → 20.0% | $88.4k → $60.5k | FAIL |
| A12 | **N1 के साथ जोड़ (ECO-W2, live)**, dev 2021-01 … 2025-09 | 1D 21.4%, N1 22.2% → **11.0%** | 1D $73.6k, N1 $141k → **$110.5k** | **अपनाया गया** |
| A13 | Profit lock (ECO-T4) | 11.0% → 10.4% | Calmar 5.98 → 5.96 | FAIL |
| A14 | DD-halving loss rule (R2, दूसरा system) | 11.4% → 13.1% | $14.6k → $12.4k | "does not help" |
| A15 | Regime gate N2 (N1 system) | 28.6% → 27.3% / 36.9% | — | FAIL |
| A16 | T19 safety (N1 system) | (claims में DD नहीं है) | Calmar 3.65 → 4.16 | S2 cap अपनाया गया |

### इस ledger से सबक
1. **चार चीज़ों ने drawdown घटाया:**
   - (a) कम exposure: DD लगभग उसी अनुपात में घटता है, और मुनाफ़ा भी;
   - (b) shorts जोड़ना (long-short);
   - (c) per-trade stops;
   - (d) एक कम correlation वाला दूसरा system जोड़ना (N1, daily correlation 0.05)।

   ये चारों अभी live ECO में मौजूद हैं।
2. **"कब बाहर रहना है" का अंदाज़ा लगाने वाला हर तरीक़ा fail हुआ, 6 बार।** इनमें market brain, market gate, crash brain, exit brain, regime gate और loss rules शामिल हैं। या तो मुनाफ़ा बहुत घटा, या नतीजा luck निकला। BTC hedge और inverse-vol weights ने भी मुनाफ़ा बहुत घटाया।
3. **आज की असली कमज़ोरी 73% drawdown नहीं, पिछला एक साल (P3: 2025-10 … 2026-09) है:**

   | P3 (सिर्फ़ report, किसी चुनाव में इस्तेमाल नहीं) | Return | Max DD |
   |---|---|---|
   | सिर्फ़ 1D (LS_RS) | +15.6% | 12.6% |
   | सिर्फ़ N1 | −12.5% | 31.3% |
   | **ECO-W2 (live)** | **−0.3%** | **18.7%** |

   P3 में N1 ने 1D की कमाई खा ली। इसे P3 देखकर अब ठीक करना (जैसे N1 का weight घटाना) फिर वही snooping होगा। इस पर फ़ैसला forward data से होगा: Sleeve A की forward जाँच और TC gate (~9 Nov) पहले से चल रहे हैं।

---

## 2. Part B: live ECO से आगे क्या उम्मीद रखें (drawdown band)

**तरीक़ा:**
- ECO-W2 की daily returns पर stationary bootstrap किया गया: 10,000 रास्ते, औसत block 20 दिन।
- **ALL** (2021-01 … 2026-09, 2,099 दिन) मुख्य band है। **P3** (सिर्फ़ पिछला साल) stress band है।
- Verifier ने अपना अलग bootstrap चलाया। सबसे बड़ा फ़र्क 0.59 pp रहा, सीमा 1.0 pp थी।

| अवधि | Band | Max DD: median / 95% / 99% | Return: 5% / median | Return < 0 की संभावना |
|---|---|---|---|---|
| 30 दिन | ALL | 3.1% / 7.4% / 9.4% | −4.6% / +2.1% | 31% |
| 30 दिन | P3 | 3.5% / 8.2% / 9.8% | −7.0% / 0.0% | 50% |
| 90 दिन | ALL | 5.6% / 11.1% / 14.7% | −6.1% / +7.7% | 19% |
| 90 दिन | P3 | 6.2% / 14.4% / 17.6% | −12.2% / +0.1% | 49% |
| 180 दिन | ALL | 7.2% / 14.1% / 18.0% | −4.4% / +18.0% | 10% |
| 180 दिन | P3 | 9.7% / 20.5% / 25.2% | −16.8% / −0.1% | 50% |
| 1 साल | ALL | 9.2% / 17.5% / 22.1% | +3.2% / +46% | 3.3% |
| 1 साल | **P3** | **14.6% / 28.1% / 33.9%** | **−22.7% / −0.1%** | **50%** |

**इतिहास के असली rolling windows (bootstrap नहीं):**
- 1 साल का सबसे बुरा DD 18.75% था (2025-10 … 2026-09)।
- 90 दिन का सबसे बुरा DD 16.7% था (2025-12-25 … 2026-03-24)।
- 2021–26 में कभी भी 30% का DD नहीं आया।

### Protocol में पहले से तय वाक्य (आँकड़ों से)
- **Kill switch (30% DD):** 1 साल में इसके लगने की संभावना ALL band पर 0.06% और P3 band पर 3.2% है, यानी यह **tail event (≤ 10%)** है।
- **पिछले साल जैसा बाज़ार रहा तो live system की median उम्मीद "कोई कमाई नहीं" है** (P3 पर 1 साल का median −0.1%)।
- **ध्यान देने वाली बात:** पिछले साल का असली DD (18.75%) ALL band की 1-साल 95% सीमा (17.5%) से ऊपर है। मतलब हाल का बाज़ार 5 साल के औसत से बुरा रहा है। इसलिए ALL band शायद आशावादी है, और P3 band को भी साथ देखना चाहिए।

### Alarm की सीमा (प्रस्ताव; अभी लागू नहीं)
2026-10-26 से गिनी गई live उम्र के हिसाब से, peak से गिरावट:

| Live उम्र | पीला (ALL 95%) | लाल (ALL 99%) |
|---|---|---|
| ≤ 30 दिन | 7.4% | 9.4% |
| ≤ 90 दिन | 11.1% | 14.7% |
| ≤ 180 दिन | 14.1% | 18.0% |
| ≤ 1 साल | 17.5% | 22.1% |

इसे `eco_alerts.py` में जोड़ने के लिए आपकी हाँ चाहिए, और उसका अपना test भी होगा। यह सिर्फ़ चेतावनी है, कोई trade नहीं रोकेगी। Kill switch 30% पर ही रहेगा।

## 3. Part C: live demo अभी कहाँ है (VM पर सिर्फ़ पढ़ा, कुछ लिखा नहीं)
- **Data:** 55 hourly cycles, 2026-10-25 04:21 से 10-27 10:20 UTC तक।
- **Eco equity:** 9,997 → 9,958 (अंदरूनी 10k scale पर)। Peak 10,064।
- **अब तक का max DD:** 1.78% (10-26 15:20 UTC)। 30-दिन की पीली सीमा 7.4% है, यानी सामान्य दायरे में है। System halted नहीं है।
- 7 दिन से कम का data है, इसलिए यह **सिर्फ़ जानकारी** है, सबूत नहीं।

---

## 4. ईमानदार निष्कर्ष: direction, entry, exit के सवाल पर
1. **Drawdown के लिए जो काम करता है, वह पहले से live है:**
   - exposure की सीमा (`deploy/eco_config.json`: हर coin अधिकतम 20%, कुल 1.5×);
   - long-short;
   - stops;
   - दो अलग systems का जोड़।

   "कब बाहर रहें" का अंदाज़ा 6 बार fail हुआ है। उसे फिर आज़माने का कोई सबूत-आधारित कारण नहीं है।
2. **असली खुला सवाल यह है कि पिछले साल ECO लगभग 0% पर रहा।** इसका जवाब नया backtest नहीं दे सकता। यह आगे के data से तय होगा:
   - TC gate (~9 Nov);
   - Sleeve A की forward जाँच;
   - इस report की band से live की तुलना।
3. **Backtest की सीमा:** ये bands उन systems के backtest हैं जो 2021–26 को देखकर ही बने थे। Live cost और tracking (E-3 में 1.20%) इनमें शामिल नहीं हैं। इसलिए असली नतीजे इनसे बुरे भी हो सकते हैं।

## 5. आगे (हर कदम पर आपकी हाँ चाहिए)
1. **पीला/लाल alarm** (§2) को ECO alerts में जोड़ना: code, test, फिर deploy।
2. **TC gate (~9 Nov) और Sleeve A के फ़ैसले** का इंतज़ार। ये पहले से तय protocols हैं।
3. **Batch 2 (methods bench):** अभी laptop पर चल रहा है (10:20 UTC पर 972 में से 950 पूरे)। पूरा होने पर verifier और report आएँगे।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये backtest और forward-जाँच के नतीजे हैं, भविष्य का वादा नहीं।
