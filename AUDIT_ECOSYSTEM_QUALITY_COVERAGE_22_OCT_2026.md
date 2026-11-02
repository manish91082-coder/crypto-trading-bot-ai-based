# पूरे ECO ecosystem का गहरा audit: quality, coverage, गलतियाँ, कमियाँ और सुधार (22 अक्टूबर 2026)

**सवाल (user):**
- क्या ecosystem पूरा है?
- क्या छूटा है, और कौन-सी गलतियाँ रह गईं (logical, strategic, coverage, mathematical)?
- Profit %, मौकों की गिनती, profit maximization, loss minimization और losing trades की गिनती, इन सब पर क्या कर सकते हैं?
- हर बात सबूत के साथ।

**तरीका:** इस audit में कोई code नहीं बदला। हर finding नीचे की किसी जाँच से निकली है, और हर एक के साथ उसका सबूत लिखा है:
- (a) ECO का पूरा code दोबारा पढ़ा: `src/eco/*.py`, line numbers के साथ;
- (b) VM के live ledgers पढ़े (22-10, 05:16–06:10 UTC);
- (c) research files से गणना दोबारा की: `trades_K1.parquet`, `e2_daily_series.parquet`, claims;
- (d) पुरानी reports।

---

## 0. सीधा जवाब

| सवाल | जवाब |
|---|---|
| Plan/demo के लिए ecosystem पूरा है? | **हाँ।** Data → brains → एक हिसाब → stops → ledger → verifier → Drive। Live cycles में attribution का जोड़ हर बार 0.000 तक मिलता है, और सारे jobs exit 0 पर हैं |
| Real money के लिए पूरा है? | **नहीं।** 6 ज़रूरी कमियाँ हैं (§5, P0)। सबसे बड़ी: backtest नंबरों में hindsight से चुने coins का असर (§1.2), और कोई alert system नहीं (§2.8) |
| क्या कोई बड़ी गलती मिली? | **2 logic bugs** (kill switch से जुड़े, §2.1–2.2), **1 बड़ा statistical bias** (survivorship, §1.2), **1 methodology कमज़ोरी** (DSR का SR-variance, §1.1)। बाकी छोटी कमियाँ हैं |
| Profit बढ़ाने का सबसे भरोसेमंद रास्ता? | **Real account पर spot routing वापस लाना** (N3 में Calmar 3.26 → 3.65)। इसके बाद size का फ़ैसला (आपका risk चुनाव, §4.1) |
| Losing trades घटाना? | **इसे लक्ष्य नहीं बनाना चाहिए।** हमारे सबसे मज़बूत sleeve (A) में 66% trades हारते हैं, फिर भी वही सबसे ज़्यादा कमाता है। Losers काटने की हर कोशिश ने कमाई घटाई (§4.5) |

---

## 1. Statistical और mathematical findings

### 1.1 DSR "1.00" जितना मज़बूत दिखता है, उतना नहीं है (methodology की कमज़ोरी)

- **सबूत:** E-2 का DSR `e2_daily_series.parquet` से दोबारा गिना।
  - Trials की गिनती का असर लगभग नहीं: N = 27, 110 या 200 पर DSR 1.00; N = 1000 पर 0.9996।
  - पर **SR variance** (सारे trials में Sharpe कितना फैला है) पर यह बहुत निर्भर है:

    | SR variance | DSR (N = 110) |
    |---|---|
    | 0.0097 (E-2 में इस्तेमाल हुआ) | 1.00 |
    | 0.05 | **0.47** |
    | 0.10 | **0.0005** |

- **कारण:** E-2 में यह variance सिर्फ़ 3 लगभग एक जैसी series (W1, W2, N1 alone) से निकाला गया। N1, N2, N6 और T4 में भी यही तरीका रहा (sr_var 0.0008–0.0011), यानी हर बार "एक ही family के variants" से। पूरे project में आज़माए गए 100+ अलग-अलग तरीकों का असली फैलाव इससे कहीं ज़्यादा है।
- **एक और गिनती की कमी:** combined system में 1D system शामिल है, जो खुद 83 trials से चुना गया था (`f7_run.py` line 29: `DSR_N = 83`)। E-2 के N = 27 में ये नहीं गिने गए।
- **असर:** "skill साबित है" कहना ज़्यादा भरोसा जताना है। सही बयान: "backtest अच्छा है, पर overfitting का खतरा DSR से पूरी तरह ख़ारिज नहीं होता।" साफ़ परीक्षा सिर्फ़ forward data है।
- **सुधार:**
  - आगे हर DSR के साथ sensitivity table (SR variance 0.01 / 0.05 / 0.10) भी report करें।
  - N में सारे परिवार गिनें: A0 के 20 + ECO के 3 + 1D के 83 + TFX N_eff 5 ≈ 111।

### 1.2 Survivorship और hindsight से चुने coins (सबसे बड़ा bias)

- **सबूत (N1, `trades_K1.parquet`, dev 2020-02 … 2025-09, sleeves A+B, Σ w × gross):**

  | | DOGE + SOL का हिस्सा |
  |---|---|
  | पूरी A+B कमाई में | **42%** (1.394 + 0.911 = 2.305, कुल 5.472 में से) |
  | 2021 की कमाई में | **57%** |

  - DOGE पहली बार 2020-07-17 को trade हुआ और SOL 2020-09-14 को। यानी 2020 की शुरुआत में ये "top-10" नहीं थे।
  - `core10` (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LINK, LTC) **आज की नज़र से** चुनी गई list है। 2021 में जो coins डूबे (LUNA, FTT, EOS वगैरह), वे इसमें नहीं हैं।
- **1D system पर यह पहले नापा जा चुका है** (`REPORT_1D_STEP6_7_AI_13_OCT_2026.md` line 148)। उसी AI पर हर साल उस समय के top-10 (डूबे coins समेत) लेने से:
  - नतीजा **$42,117 → $18,719**;
  - **Calmar 0.57 → 0.20**;
  - **Max DD 57%**।
- **N1 और F7 LS के लिए यह जाँच कभी नहीं हुई।** यह DISC की बची list में "G3 survivorship-free data" के नाम से दर्ज है।
- **असर:** N1 के backtest नंबर (dev Calmar 4.16, CAGR 99%) और combined 5.98 **ऊपर की तरफ़ झुके** होने की पूरी संभावना है। कितना, यह अभी अज्ञात है।
- **सुधार (P0, एक trial):** point-in-time universe। हर महीने उस समय के volume के हिसाब से top-10, डूबे coins समेत। उस पर N1 A/B और 1D LS दोबारा चलाएँ। नतीजा शायद कम आएगा, पर **सच्चा** होगा।

### 1.3 In-sample combination और आख़िरी साल

- **सबूत (`E2_results.csv`):**

  | P3 (2025-10 … 2026-09) | Return | Max DD |
  |---|---|---|
  | मिलाकर (W2) | **−0.3%** | 18.8% |
  | N1 अकेला | −12.5% | — |
  | 1D अकेला | +15.0% | — |

- दोनों systems और उनका बँटवारा उसी 2021–25 data को देखकर चुने गए थे।
- **असर:** dev वाले 65.9% CAGR की उम्मीद रखना ग़लत होगा। आख़िरी साल, जो सबसे साफ़ data है, लगभग शून्य रहा।

### 1.4 एक साल पर निर्भरता

- **सबूत:** N1 में 2021 अकेले +495% (N1 report), और ECO-W2 में 2021 +255% (`claims_eco_e2.json` years)।
- बाकी साल:

  | | 2022 | 2023 | 2024 | 2025 (जनवरी–सितंबर) |
  |---|---|---|---|---|
  | ECO-W2 | +16% | +28% | +73% | +21% |

- **असर:** लंबे समय का औसत एक असाधारण bull साल से फूला हुआ है।

### 1.5 Daily बनाम hourly drawdown

- **सबूत:** E-2 ने DD daily values से नापा (CODE_NOTES 1)। N1 FINAL का DD hourly पर 23.7% था और daily पर 22.2%।
- **असर:** combined DD 11.0% असल में (hourly पर) थोड़ा ज़्यादा होगा।
- **सुधार:** forward में DD hourly marks से नापें। ECO ledger हर घंटे पहले से लिखता है।

### 1.6 पहले से दर्ज FAILs (याद के लिए)

- **R2 tracking 1.20%:** N1 हिस्सा 0.01%, 1D हिस्सा timing और cost की वजह से। Forward TC test lock है।
- **T4 profit lock:** FAIL।
- **5 AI trials:** सब FAIL (A3, T14, N2, N5, T20)।

---

## 2. Code और logic findings (ECO)

### 2.1 Bug: kill switch frozen symbol को बंद नहीं करता

- **सबूत:** `eco_orchestrator.py` lines 142–155।
  - Kill होने पर `ct = {}` होता है, पर `plan_orders` को `frozen_syms` (reconcile mismatch या guard_fired वाले symbols) दिया जाता है।
  - `plan_orders` उन symbols को छोड़ देता है (`eco_core.plan_orders`: "symbol frozen")।
- **असर:** अगर उसी समय किसी symbol पर mismatch हो, तो **halt के बाद भी वह position खुली रहेगी**, और halt के बाद कोई cycle उसे नहीं छुएगा।
- **सुधार:** kill के समय frozen symbols को भी exchange की असली position के हिसाब से बंद करें, और ज़ोरदार alert दें। Test T7 में एक नया case जोड़ें।

### 2.2 Bug: kill switch एक cycle में सिर्फ़ 40 orders भेजता है

- **सबूत:** line 156, `orders = orders[: cfg["max_orders"]]` (40)।
- **असर:** 40 से ज़्यादा symbols पर positions हों, तो halt होते ही बाकी positions बंद नहीं होतीं, और अगला cycle halted होने से कुछ भेजता ही नहीं। आज 21 symbols हैं, इसलिए अभी असर नहीं, पर N1 के C/D sleeves 40+ coins तक जा सकते हैं।
- **सुधार:** kill के समय सीमा हटाएँ, या halt के बाद भी "सिर्फ़ बंद करने वाले" orders की इजाज़त दें।

### 2.3 Pending 1D short का stop आधार खिसकता है

- **सबूत:** `eco_core.allocate_fill`। हर बार position उसी दिशा में बढ़ने पर `entry_px` = आख़िरी fill price हो जाता है।
- Pending short का stop = 1.5 × `entry_px` (`check_stops` और `desired_stops`)।
- F7 का नियम है original entry × 1.5।
- **असर:** छोटा। F4 अगले दिन अपना stop दे देता है, तब वही इस्तेमाल होता है। पर पहले दिन stop ऊपर-नीचे खिसक सकता है।
- **सुधार:** pending component के लिए पहली fill price को स्थिर रखें।

### 2.4 Plan mode reconcile और journal को असली में test नहीं करता

- **सबूत:** `LiveEnv.positions()` plan mode में अपनी ही state को "exchange" मानता है (lines ~244)। इसलिए mismatch कभी नहीं बन सकता।
- **असर:** live verifier का L5 (reconcile 0) plan mode में अपने-आप PASS है।
- **सुधार:** यह सिर्फ़ demo में साबित होगा, इसलिए cut-over के पहले हफ़्ते reconcile को मुख्य gate मानें।

### 2.5 छोटे targets कभी खुलते ही नहीं (band का systematic असर)

- **सबूत (live ledger, 13 cycles):** ASTER, BCH, INJ, TIA के targets (−13.7, −22.5, −8.8, −21.9 USDT eco) हर cycle "inside band" रहे और **कभी नहीं खुले**।
- कुल ~67 USDT, यानी gross 7,088 का ~0.9%। ज़्यादातर N1 के C (crash-hedge) sleeve के छोटे shorts।
- **असर:** crash hedge थोड़ा कमज़ोर, और tracking error। Demo में k ≈ 0.5 पर यह और बढ़ेगा।
- **सुधार:** band को "खोलने" और "adjust करने" के लिए अलग रखें। नई position तब खुले जब target ≥ min_notional हो; adjust करने पर band लगे। यह छोटा, test करने लायक बदलाव है।

### 2.6 Exchange stops और guard demo पर साबित नहीं

- **सबूत:** CODE_NOTES 3। MARK_PRICE और एक symbol पर कई reduceOnly stop orders, ये F6 ने कभी नहीं चलाए।
- **सुधार:** cut-over के पहले cycle का पक्का check: हर stop order "NEW" status में मिले, कोई reject न हो।

### 2.7 चले हुए stop का दाम अंदाज़न दर्ज होता है

- **सबूत:** `book_triggered` fill को trigger price पर दर्ज करता है।
- **असर:** असली fill अलग होगा, जिससे eco equity और account में छोटा फ़र्क आएगा।
- **सुधार:** demo में `/fapi/v1/userTrades` से असली fill लेकर ठीक करें।

### 2.8 कोई alert system नहीं (operations की बड़ी कमी)

- **सबूत:** VM पर `src` और `deploy` में `smtplib|telegram|sendmail|webhook|twilio|pushover` का grep करने पर **एक भी नतीजा नहीं**।
- सारी जाँचें (verifiers, M10) सिर्फ़ files में लिखती हैं। Kill switch, halt, freeze या job failure की ख़बर आप तक **अपने-आप नहीं पहुँचती**।
- **असर:** demo या real में कुछ गड़बड़ हो तो कई घंटे या दिन किसी को पता नहीं चलेगा।
- **सुधार (P0):** एक alert channel। उदाहरण: Telegram bot या email, जिसकी keys आप `.env` में डालें। Kill, halt, freeze, failed cycle, verifier FAIL और "2 घंटे से कोई cycle नहीं", इन सब पर तुरंत संदेश।

### 2.9 Delisted coin universe में

- **सबूत:** PaperN1 के 7 cycles में से 6 में SXPUSDT error (`/fapi/v1/klines SXPUSDT: HTTP 400`)। Coin delist हो चुका है, पर U2X list में है।
- **असर:** आज नुकसान नहीं है (SXP liquid नहीं है, इसलिए trade नहीं होता)। पर अगर कोई **held** coin delist हुआ, तो N1 paper उसे बंद नहीं कर पाएगा, और ECO में वह perp filters से गायब होकर "no exchange filters" में फँस जाएगा।
- **सुधार:** delisting का नियम: Binance का delist notice या `status != TRADING` → position बंद, और universe से बाहर।

### 2.10 Monitoring की छोटी कमियाँ

- M10 daily status में ECO, PaperN1 और LogShip jobs नहीं दिखते (19-10 से दर्ज)।
- LogShip verifier W4 की list में F6 की state file है, जिसका नाम cut-over पर बदलेगा (दर्ज)।

### 2.11 जो सही मिला (सबूत)

- Attribution identity: live 13/13 cycles में 0.000; replay में 8e-10।
- 25/25 mock tests, जिनमें crash recovery, lock, stale और छेड़ा हुआ producer शामिल हैं।
- 15 jobs, 0 failures। Drive bundles verified।
- Delete सिर्फ़ verified copy के बाद होता है (पिछला audit)।

---

## 3. Coverage audit: क्या है, क्या नहीं

| क्षेत्र | Covered | नहीं / अधूरा | सबूत |
|---|---|---|---|
| **Timeframes** | 4h, 8h, 12h, 1D (trade) | 5m–1h (cost के बाद घाटा), 1W/1M (data कम) | TFX, master audit N18 |
| **Instruments** | USDT-M perps | **Spot execution** (X2 का फ़ायदा demo में नहीं), options, margin | N3: X2+X3 से Calmar 3.26 → 3.65 |
| **Strategy families** | Trend (4 नियम), RSI oversold, XS momentum, AI long-short (1D) | Funding carry (कमज़ोर, DISC D1: 2025 से 0–4%/साल), pairs, vol forecasting (GARCH/HAR), order book | DISC G-list |
| **Universe** | core10 + liquid alts | **Point-in-time / survivorship-free** | §1.2 |
| **AI** | 1D brains (monthly retrain) | 4H/1h/meta/sizing AI: सब FAIL | T05, T14, T18, T20 |
| **Risk** | Caps, kill switch, 1D-short stops, outage guard | Alerting; kill switch bugs (§2.1–2.2) | §2 |
| **Execution** | Taker, netting, band | Maker (FAIL); spot; exit timing | N3 X1 |
| **Validation** | Backtest, replay, mock, plan forward | **Demo forward (TC test), real-money pilot** | Amendment 1 §5 |
| **Operations** | Cron, ledgers, Drive, verifiers | Alerts, दूसरा VM (failover), delisting नियम | §2.8–2.9 |
| **Costs** | Fee मान्यता conservative (0.054%/side बनाम नापा perp ~0.036–0.045% fee + 0.005–0.01% spread) | Real account का commissionRate, futures wallet में BNB (आपके काम) | `FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md` |
| **Tax** | — | India 30% VDA tax, loss set-off नहीं (आपने parked रखा है) | `RESEARCH_1D_WINDUP_SPOT_FUTURES_15_OCT_2026.md` |
| **Data use** | FR2 forward data जमा | **FR2 data अभी किसी research में इस्तेमाल नहीं** | — |

---

## 4. Profit, मौके, loss: क्या करें और क्या नहीं (सबूत के साथ)

### 4.1 Profit % बढ़ाना

| उपाय | सबूत | अनुमानित असर | खतरा |
|---|---|---|---|
| **Real account में spot routing (X2)** | N3: Calmar 3.26 → 3.65 (X2+X3); ~39% long entries spot पर | सबसे भरोसेमंद सुधार | Spot और futures wallet के बीच internal transfer का code और test चाहिए |
| **Size बढ़ाना** (gross cap 1.5× के अंदर) | dev DD 11%, पर P3 DD 18.8%। 1.5× पर P3 DD ≈ 28%, जो kill switch (30%) के बहुत पास है | Return लगभग size के अनुपात में | **आपका risk चुनाव।** मेरी सलाह: survivorship test (§1.2) के नतीजे से पहले नहीं |
| **Sleeve-स्तर पर बँटवारा** (7 sleeves, inverse-vol) | Test नहीं हुआ। 2-strategy स्तर पर DD आधा हुआ था | अनुमान: DD और कम | 1 trial (ECO का आख़िरी) |
| **1D के फ़ैसले जल्दी लागू करना** (00:00 के पास) | Replay में timing का असर एक महीने में ~85 USDT था, पर दिशा अज्ञात | पहले forward में नापें | Pipeline (Step16 → 16B → F4) का समय बदलना 1D system को छूता है |
| **Fees** | Futures wallet में BNB से 10% छूट | ~0.004%/side | आपका काम |

### 4.2 मौकों (trades) की गिनती बढ़ाना

**सबूत कहता है कि "उसी edge के और मौके" जोड़ने से कमाई घटती है:**
- 120 coins पर take-all: **−56%** (T14);
- 5m–30m: हर cell cost के बाद negative (TFX);
- 1h नियम जोड़ने पर DD 12% → 28% (master audit)।

**इसलिए मौके सिर्फ़ नए, अलग (कम correlation वाले) edge से बढ़ने चाहिए।** उम्मीदवार, हर एक नए trial में:
- (a) survivorship-free universe पर वही नियम (यह मौके बदलेगा, शायद घटाएगा);
- (b) pairs/relative value;
- (c) funding carry, कम उम्मीद के साथ।

**अभी के मौके:** N1 ~21,700 trades/साल (A 4,749, B 145, C 15,914, D 878) और 1D brains रोज़। मौकों की कमी नहीं है।

### 4.3 Profit maximization

सबसे बड़ा lever **diversification** साबित हुआ:

| | Calmar | DD |
|---|---|---|
| N1 अकेला | 3.36 | 22% |
| 1D + N1 मिलाकर | 5.98 | 11% |
| Daily correlation | 0.05 | |

अगला कदम इसी दिशा में है: तीसरा अलग edge, या sleeve-स्तर का बँटवारा। Exits और stops को tune करना नहीं।

### 4.4 Loss minimization (DD घटाना)

| आज़माया गया | नतीजा | सबूत |
|---|---|---|
| 3×ATR stop | Calmar 3.26 → 2.74 | N1 K0 |
| 35% catastrophe stop | 4.16 → 2.90 | T19 S1 |
| Heat cap 6% | DD 28.6 → 22.4%, पर Calmar 3.26 → 2.50 | N1 K2 |
| Correlation dampener, inverse-vol per coin | Calmar गिरा | K3, K6 |
| AI से trade छोड़ना | Calmar गिरा | T18 |
| Profit lock | 4.16 → 3.62 | T4 |
| **दो अलग systems मिलाना** | **DD 22% → 11%, Calmar बढ़ा** | **E-2** ✅ |
| Per-coin cap 20% | DD 27% → 24%, Calmar 3.65 → 4.16 | T19 S2 ✅ |

**निचोड़:** loss घटाने वाले जो तरीके काम करते हैं, वे portfolio-स्तर के हैं: diversification और concentration cap। Trade-स्तर के stops, filters और locks नहीं।

### 4.5 Losing trades की गिनती घटाना: क्यों यह ग़लत लक्ष्य है

**सबूत (`trades_K1`, dev, fee और funding के बाद):**

| Sleeve | Win rate | Avg win / avg loss | Top 10% trades का कमाई में हिस्सा |
|---|---|---|---|
| A (trend-long) | **34%** | **4.37×** | **155%** (बाकी 90% trades मिलकर negative) |
| B (oversold) | 70% | 1.05× | 70% |
| C (trend-short) | 37% | 1.81× | कुल लगभग 0; crash hedge |
| D (momentum) | 50% | 1.06× | — |

- Trend system की बनावट ही ऐसी है: बहुत से छोटे losses और कुछ बहुत बड़े winners।
- Losers घटाने की हर कोशिश (stop, filter, AI skip, profit lock) ने बड़े winners भी काटे, और कमाई गिरी।
- **सही लक्ष्य:** "expected profit प्रति trade × trades" और portfolio DD। Win rate नहीं।

---

## 5. Priority सूची (क्या, क्यों, फ़ायदा)

| # | काम | क्यों (सबूत) | फ़ायदा | ज़रूरत |
|---|---|---|---|---|
| **P0-1** | Kill switch के 2 bugs ठीक करना + tests | §2.1, §2.2 | Halt के बाद कोई position खुली न रहे | Code + mock tests |
| **P0-2** | Alert system (Telegram/email) | §2.8 | गड़बड़ की ख़बर तुरंत | आप keys `.env` में डालें |
| **P0-3** | Survivorship-free test: N1 + 1D LS, point-in-time universe | §1.2 (DOGE+SOL 42%; 1D पर Calmar 0.57 → 0.20) | सच्चे नंबर, real money से पहले ज़रूरी | 1 trial (ECO का आख़िरी) या नया budget |
| **P0-4** | Delisting नियम + SXP हटाना | §2.9 | Delisted coin में फँसी position नहीं | Code + test |
| **P0-5** | Demo cut-over + 14-दिन TC test | §2.4, §2.6, amendment 1 | Reconcile, stops और fills का असली सबूत | आपकी हाँ (gate ~25-10) |
| **P0-6** | commissionRate, futures wallet BNB, tax फ़ैसला | §3 | Real profit का सही हिसाब | आप |
| P1-1 | Spot execution protocol | §4.1 | Calmar में सबसे भरोसेमंद सुधार | Code + demo-spot test |
| P1-2 | Band: खोलना ≠ adjust करना | §2.5 | Crash hedge पूरा, tracking बेहतर | छोटा code |
| P1-3 | DSR sensitivity हर report में | §1.1 | ईमानदार भरोसा | Verifier में जोड़ना |
| P1-4 | Pending-short stop का स्थिर आधार; असली stop fill (userTrades) | §2.3, §2.7 | सही हिसाब | छोटा code |
| P1-5 | M10 में नए jobs; W4 list | §2.10 | पूरा monitoring | छोटा code |
| P2 | Sleeve-स्तर बँटवारा; नया uncorrelated edge (pairs/carry); FR2 data पर research | §4.2–4.3 | Diversification से DD घटे | Trials, नया budget |

**ECO trial budget:** 4 में से 3 इस्तेमाल हुए। P0-3 बचे 1 trial में होना चाहिए, क्योंकि वह सबसे ज़रूरी है।

---

## 6. अंतिम निष्कर्ष

- **Plumbing (data → फ़ैसले → हिसाब → logs) पूरा और verified है।** Live cycles में हिसाब 0.000 तक सही है, कोई failure नहीं, Drive backup चालू है।
- **Strategy के नंबर उम्मीद से कम भरोसेमंद हैं।** मुख्य कारण: hindsight से चुने coins (§1.2), एक बड़े साल पर निर्भरता (§1.4), कमज़ोर DSR आधार (§1.1), और आख़िरी साल का लगभग 0 (§1.3)।
- **Profit बढ़ाने का सही क्रम:** पहले सच्चे नंबर (P0-3), फिर spot routing (P1-1), फिर size का फ़ैसला (आपका)। Win rate या trades की गिनती बढ़ाना लक्ष्य नहीं होना चाहिए।
- **Real money से पहले P0 के 6 काम ज़रूरी हैं।**

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---
---

# भाग 2: दूसरा और गहरा audit (22 अक्टूबर 2026, pass 2)

**सवाल (user):** भाग 1 के अलावा और क्या audit बाकी है? हर code path, coverage, quality, errors, gaps, enhancements देखो, और research भी करो।

**इस pass में क्या नया किया गया** (कोई code नहीं बदला, VM पर कोई file नहीं बदली):

| # | जाँच | सबूत कहाँ |
|---|---|---|
| a | `eco_core.py`, `eco_orchestrator.py`, `eco_exchange.py`, `eco_cutover.py` का हर function line-by-line दोबारा पढ़ा, हर branch (error path समेत) पर "क्या होगा अगर…" | नीचे हर finding के साथ line numbers |
| b | VM पर 2 read-only probes (`/tmp/probe2.py`, `/tmp/probe3.py`; सिर्फ़ पढ़ते हैं): job की अवधि, ECO ledger, state का आकार, N1 बनाम ECO tracking, F6 के demo order responses, November weight की dry-run | §9, §10 |
| c | Laptop पर एक असली test: नकली (scratch) ledger में kill-switch halt डालकर live verifier चलाया | §7.1 |
| d | Binance का live public `exchangeInfo` (22-10 06:35 UTC) उतारकर universe जाँचा | §8 |
| e | Web research: Binance API docs (algo order status, market order response), delisting प्रक्रिया, funding intervals; survivorship पर academic study; DSR; Gârleanu–Pedersen | §11 |
| f | Mock tests (`test_eco_core.py`, 25 checks) की coverage: कौन-सा path test है, कौन-सा नहीं | §12 |

---

## 7. नए bugs और logic की गलतियाँ (सबूत के साथ)

### 7.1 Bug (असली test से साबित): kill switch के बाद live verifier ख़ुद crash हो जाता है

- **सबूत:** scratch में 2 lines का ledger बनाया (एक normal cycle, फिर एक halted cycle, ठीक वैसा जैसा `cycle()` line 59–61 लिखता है) और `verify_eco_live.py` चलाया।
  - L1–L7 सब **PASS** छपे।
  - फिर line 67 पर `KeyError: 'eco_equity'` से crash, क्योंकि halted record में `eco_equity` नहीं होता।
- **असर (दोहरा):**
  1. सबसे गंभीर घटना (halt) पर verifier "FAIL: halted" नहीं कहता, बल्कि traceback देता है।
  2. Halt verifier की किसी check में FAIL नहीं गिना जाता, सिर्फ़ INFO line में छपता है।
- **सुधार:** नई check L8 "halted = FAIL" (साफ़ संदेश के साथ), और INFO line halted record पर न टूटे। Alert system (P0-2) इसी check से जुड़े।

### 7.2 Bug: एक भी held symbol का दाम न मिले, तो पूरे ecosystem की equity और kill switch जम जाते हैं

- **सबूत:** `eco_orchestrator.py` lines 103–106:
  - `acct_pnl` सिर्फ़ तब गिना जाता है जब **हर** held symbol का दाम मौजूद हो;
  - वरना पिछला `last_acct_pnl` ही दोहराया जाता है;
  - line 183 पर भी यही होता है।
- **कब होगा:** कोई held coin delist / settle हो जाए, या `premiumIndex` से उसका दाम गायब हो (`prices()` सिर्फ़ `m[s] > 0` वाले लौटाता है, `eco_exchange.py` line 97)।
- **असर:**
  - उस दिन से eco equity हर cycle वही रहेगी, तो **kill switch अंधा हो जाएगा**, भले बाकी 20 symbols गिर रहे हों।
  - हर cycle बस एक note बनेगा, जो कोई नहीं पढ़ता।
- **सुधार:** गायब symbol को उसके आख़िरी ज्ञात दाम पर mark करें (साफ़ note के साथ), बाकी सबको असली दाम पर। 2 cycle से ज़्यादा गायब रहे तो alert।

### 7.3 Logic गलती: algo (stop) order के status की व्याख्या अधूरी है (सिर्फ़ demo/real पर असर)

- **सबूत:**
  - Binance docs के अनुसार algo order के 7 status हैं: NEW, **TRIGGERING**, TRIGGERED, **FINISHED**, CANCELED, REJECTED, EXPIRED।
  - FINISHED का मतलब "triggered order fill **या cancel** हुआ" है, इसलिए fill पक्का करने के लिए executed quantity देखनी पड़ती है।
  - ECO code (`eco_orchestrator.py` lines 74–80) ऐसा करता है:
    - TRIGGERED / FINISHED → `book_triggered`, यानी पूरी quantity trigger price पर "filled" दर्ज;
    - NEW / OPEN / WORKING के अलावा कुछ भी → "dropped, will be re-placed"।
- **असर:**
  - (a) **TRIGGERING** (order matching engine की तरफ़ जा रहा है) को ECO "dropped" मानकर **दूसरा stop लगा देगा**। दोनों चल सकते हैं।
  - (b) **FINISHED पर बिना fill के** (engine में cancel) भी ECO position को बंद मान लेगा। Ledger और exchange अलग हो जाएँगे → अगले cycle में reconcile mismatch → symbol frozen।
- **सुधार:**
  - TRIGGERING को "रुको" माना जाए।
  - FINISHED / TRIGGERED पर असली executed qty और avg price `/fapi/v1/userTrades` या order query से लें (भाग 1 का §2.7 भी इसी से ठीक होगा)।
  - S-tests में इन statuses के mock cases जोड़ें।

### 7.4 कमी: market order के जवाब की जाँच नहीं होती (demo से पहले ज़रूरी)

- **सबूत 1 (code):** `LiveEnv.execute` (lines 289–294) सीधे `executedQty` और `avgPrice` पढ़ता है। `status == FILLED` की कोई जाँच नहीं।
- **सबूत 2 (VM, F6 के असली demo जवाब):**

  | F6 order | `newOrderRespType` | जवाब |
  |---|---|---|
  | Short खोलना (3 runs) | RESULT | **45/45 FILLED** |
  | Ops drill 16-10 में close | default (ACK) | **11/11 `status NEW`, `executedQty 0`, `avgPrice` नहीं** |
  | Kill drill 19-10 में close | default (ACK) | **7/7 वैसा ही** |

- **निष्कर्ष:**
  - ECO RESULT माँगता है, और सबूत कहता है कि RESULT पर demo FILLED देता है। इसलिए रोज़ के हालात में ख़तरा कम है।
  - पर अगर कभी NEW लौटा, तो दो में से एक होगा:
    - `avgPrice` न हो → `float(None)` → cycle crash। Journal recovery अगले cycle में संभाल लेगी, पर उस cycle के बाकी orders नहीं जाएँगे।
    - `avgPrice "0"` हो → `filled 0` → `allocate_fill` इसे internal transfer मानकर **दाम 0 पर** components के बीच crossing दर्ज करेगा। Strategy-wise हिसाब बिगड़ेगा और असली fill दर्ज नहीं होगा।
- **सुधार:**
  - `status != FILLED` या `executedQty == 0` → order query करके इंतज़ार करें, और fill पक्का होने तक journal रखें।
  - `allocate_fill` को `px <= 0` पर मना कर देना चाहिए।

### 7.5 गणित की गलती: funding cycle के **बाद** वाली positions पर गिनी जाती है

- **सबूत:** line 178 पर `env.funding(C.held_net(st["held"]), since, now)` orders के **बाद** चलता है, जबकि funding event (00/08/16 UTC या symbol का अपना interval) पिछले घंटे में हुआ था, जब positions पुरानी थीं।
- **असर:**
  - Plan mode में जिस cycle में position बदली, उसमें पिछले घंटे की funding नई quantity पर लगती है।
  - Demo असली income लेता है, इसलिए demo और shadow plan में फ़र्क आएगा, जो **TC tracking test में noise** बनेगा।
  - Live में अभी तक funding वाले 3 cycles का कुल सिर्फ़ 0.054 USDT है, यानी आकार छोटा है, पर हिसाब ग़लत है।
- **सुधार:** funding orders से **पहले** वाली positions (`exch_before` / पहले का `held`) पर गिनें।

### 7.6 Exchange पर "अनाथ" stop orders रह सकते हैं

- **सबूत:**
  - state सिर्फ़ `ok` होने पर लिखी जाती है (line 395–396)।
  - अगर `place_stop` सफल हो और उसके बाद cycle टूटे, तो exchange पर stop है पर state को पता नहीं।
  - `stop_status` (lines 296–309) सिर्फ़ state में दर्ज stops देखता है। Exchange के **सारे** open algo orders से मिलान कहीं नहीं होता।
- **असर:** अगला cycle वही stop दोबारा लगाएगा, तो दो stops होंगे। बाद में अनाथ stop चल गया तो बिना दर्ज fill के position घटेगी → mismatch → freeze।
- **सुधार:** हर cycle `openAlgoOrders` की पूरी list को state से मिलाएँ; अनजान ECO stops cancel करें (या alert दें)।

### 7.7 State और ledger की लिखाई atomic नहीं

- **सबूत:**
  - `state.json` सीधे `write_text` से लिखी जाती है (lines 282, 396)। temp file + rename नहीं।
  - State पढ़ना (line 381) `try` के **बाहर** है।
  - `append_ledger` आख़िरी line पढ़कर `json.loads` करता है (`eco_core.py` line 385)।
- **असर:** लिखते समय VM बंद हुआ या disk भरी, तो आधी file बचेगी। उसके बाद **हर cycle crash** होगा, और ledger में कोई record नहीं बनेगा (क्योंकि crash ledger लिखने से पहले है), जब तक कोई हाथ से ठीक न करे।
- **सुधार:** temp + `os.replace` + `fsync`, और पिछली अच्छी state की एक copy।

### 7.8 Frozen strategy की positions caps की वजह से trade हो सकती हैं

- **सबूत:** lines 126–130 frozen strategy की held qty को target बनाते हैं। उसके बाद line 140 `apply_caps` सबको scale कर सकता है।
- **असर:** protocol का नियम "frozen = जो है रखो, कुछ नया नहीं" कभी-कभी टूटेगा। Caps अब तक live में एक बार भी नहीं लगे (probe: 0/14 cycles), इसलिए असर कम है।
- **सुधार:** frozen components को cap scaling से बाहर रखें, या उसे दर्ज करें।

### 7.9 Orders की 40 वाली सीमा normal cycles में भी चुपचाप काटती है

- **सबूत:** line 156 `orders[:40]`, और orders symbol के नाम के क्रम में हैं (`plan_orders` में `sorted(want)`)। कटे orders का कोई note नहीं बनता।
- **असर:** 40 से ज़्यादा बदलाव वाले cycle में वर्णक्रम के आख़िरी symbols (XRP, ZEC…) पीछे रहेंगे, और ledger में इसका कोई निशान नहीं होगा। (भाग 1 §2.2 सिर्फ़ kill वाली स्थिति पर था।)
- **सुधार:** कटे orders `skipped` में दर्ज हों, और बड़े |delta| वाले पहले जाएँ।

### 7.10 Halt के बाद reset का कोई औज़ार नहीं

- **सबूत:**
  - `grep halted` करने पर कोई reset script नहीं मिली।
  - Halt का संदेश "until the user resets" कहता है, पर इसका रास्ता सिर्फ़ `state.json` को हाथ से बदलना है।
  - Halted cycles में equity mark भी नहीं होती (lines 59–61), इसलिए halt के बाद बची positions (भाग 1 §2.1) का हिसाब दिखता ही नहीं।
- **सुधार:**
  - एक `eco_reset.py` बनाएँ: पहले exchange की हालत दिखाए, फिर user की हाँ पर `halted = None` करे, और यह ledger में दर्ज हो।
  - Halted cycles में भी equity mark हो।

### 7.11 Live verifier जितना कहता है, उतना जाँचता नहीं

**सबूत:** `verify_eco_live.py` में चार कमियाँ हैं।
- Docstring में "code SHAs listed" लिखा है, पर code सिर्फ़ उन्हें **छापता** है (line 39); CODE_CHANGES से मिलान नहीं करता।
- L6 caps को **targets** पर जाँचता है (line 56), असली held positions पर नहीं। Frozen या band में फँसी कोई बड़ी position पकड़ी नहीं जाएगी।
- **Attribution identity** (components का जोड़ == account P&L) की कोई check नहीं है। भाग 1 का "13/13 में 0.000" मेरी हाथ की जाँच थी, cron की नहीं।
- Producer से tracking (ECO N1 हिस्सा बनाम PAPER-N1) की कोई check नहीं है।

**सुधार:**
- L8: halted = FAIL;
- L9: identity;
- L10: held-cap;
- L11: code SHA listed;
- L12: N1 tracking (§10)।

### 7.12 Cut-over की कमियाँ

- **Gate अधूरा:** `eco_cutover.py` lines 50 सिर्फ़ "≥ 72 plan cycles" जाँचती है। "3 दिन verify 7/7" वाली शर्त code में नहीं है, वह हाथ से देखनी होगी। सुधार: gate में ECO_Verify के पिछले 3 दिनों के नतीजे पढ़ें।
- **मिली-जुली margin settings:**
  - F6 की shorts **ISOLATED, leverage 1** पर खुली थीं (`futures_testnet_f6.py` line 258)।
  - ECO नए symbols को **CROSSED, leverage 2** पर रखता है।
  - पर `prepare_symbol` उन symbols पर नहीं चलता जिनमें पहले से position है (`demo_prepared`, line 331–332)।
  - Cut-over के बाद अपनाए गए symbols isolated रहेंगे। उनमें margin अलग से फँसेगा, और liquidation का हिसाब बाकी account से अलग होगा।
  - सुधार: cut-over note में यह दर्ज करें, और position बंद होने के बाद उसे cross पर बदलें।

### 7.13 November weight: path काम करता है, पर दोनों windows की तारीखें मेल नहीं खातीं

- **सबूत (VM dry-run, read-only):** `inv_vol_weight` November के लिए **a_1D = 0.5465** देता है (October 0.5394)। History SHA ठीक है और duplicate dates 0 हैं। यानी 1 नवंबर का पहला cycle इस रास्ते पर नहीं टूटेगा।
- **कमी:**
  - 1D की 126 returns 2026-10-21 तक जाती हैं (6 forward दिन)।
  - N1 की returns में 10-01…10-21 गायब हैं (1 forward दिन)।
  - इसलिए दोनों की volatility अलग-अलग समय की है।
- **असर:** आज के weight पर असर लगभग शून्य है, पर तेज़ बदलाव वाले महीने में बँटवारा थोड़ा ग़लत होगा।
- **सुधार:** दोनों series को साझा तारीखों पर काटें। यह CODE_CHANGES का विषय है।

---

## 8. Universe और delisting: भाग 1 के §2.9 का सुधार और विस्तार

**भाग 1 में ग़लती:** वहाँ सिर्फ़ SXP का ज़िक्र था। Live `exchangeInfo` (22-10 06:35 UTC) से पूरी जाँच की:

| जाँच | नतीजा |
|---|---|
| ECO config की `n1_perp_names` (133 perp नाम) में जो आज TRADING नहीं हैं | **28**, यानी 21%: 20 SETTLING (जैसे FTT, KLAY, LRC, TON, LINA, FLM…) और 8 ग़ायब (SXP, MATIC, RNDR, EOS, BTT, ANC, TOMO, YFII) |
| कुल USDT perps | 702: 567 TRADING, 134 SETTLING, 1 PENDING |
| **पहले से घोषित delisting वाले, अभी TRADING** | 3: MITO और PTB (settlement 2026-10-23 09:00 UTC), VELODROME (10-28 09:00 UTC) |

**मुख्य खोज: delisting की ख़बर API में machine-readable रूप में मौजूद है।**
- Perps का सामान्य `deliveryDate` 2100-12-25 होता है।
- Delisting घोषित होते ही यही field **settlement के समय** में बदल जाती है, जबकि status अभी TRADING ही रहता है।
- इसलिए announcement पढ़ने की ज़रूरत नहीं।

**Binance की प्रक्रिया (research, secondary sources):**
- Settlement आम तौर पर 09:00 UTC पर होता है, और उससे 30 मिनट पहले नई positions बंद हो जाती हैं।
- आख़िरी घंटे में insurance fund liquidation को support नहीं करता।
- बची positions "fair/mark price" पर अपने-आप settle होती हैं।

**ECO पर असर:** आज कोई नुकसान नहीं। 14 cycles के skip reasons में "no perp" एक बार भी नहीं आया, और कोई held symbol प्रभावित नहीं है। पर नियम ज़रूरी है।

**सुधार (P0-4 को ठोस बनाना):**
- (1) हर cycle `deliveryDate < 2100` वाला held या targeted symbol → target 0, और settlement से कम-से-कम 24 घंटे पहले बंद करें।
- (2) SETTLING / ग़ायब → universe से बाहर।
- (3) Alert।
- (4) N1 perp map को साफ़ करें, और renamed coins (MATIC→POL, RNDR→RENDER आदि) का फ़ैसला protocol के ज़रिए हो।
- **यही data survivorship test (P0-3) के लिए भी काम का है:** 134 settled perps की list डूबे coins की तैयार सूची है।

---

## 9. Timing और operations (VM पर नापा गया)

| Job (cron_status, पिछले ≤ 30 runs) | अवधि (sec): min / median / max | Exit |
|---|---|---|
| ECO_Plan (:20 UTC) | 6 / 8 / 12 | 12/12 = 0 |
| PaperN1 (4h close + 11 min) | 149 / 170 / **217** | 7/7 = 0 |
| F4_LSPaper (02:15 UTC) | 2 / 34 / 70 | 0 |
| Step16 | 3 / 592 / **1307** | 0 |
| LogShip (:25 UTC) | 42 / 170 / 287 | 30/30 = 0 |
| FR2_Recorder | 198 / 212 / 223 | 0 |

**क्या ठीक है:**
- ECO (:20) और LogShip (:25) एक-दूसरे से नहीं टकराते।
- VM की घड़ी NTP से synced है, यानी signed requests का `recvWindow` 5 s सुरक्षित है।
- RAM 3.3 GB free है, disk 26.8% भरी।
- `.env` की permission 600 है।
- **State सीमित रहती है:** 239 component keys हैं, जिनमें सिर्फ़ 4 cash-only हैं। N1 की keys (`sleeve|coin|tf|rule`) दोबारा इस्तेमाल होती हैं, इसलिए state हर trade के साथ नहीं बढ़ेगी।
- Ledger ~4.7 KB प्रति cycle बढ़ता है, यानी ~41 MB प्रति साल।

**ख़तरा: time-based chaining।**
- PaperN1 :11 पर शुरू होता है और सबसे लंबा run 3 min 37 s चला। ECO :20 पर चलता है, यानी बीच में **सिर्फ़ ~5.4 मिनट की गुंजाइश** है।
- अगर N1 कभी 9 मिनट से ज़्यादा ले (Binance धीमा हो, retries हों), तो दो में से एक होगा:
  - ECO 4 घंटे पुराने N1 फ़ैसले पर चलेगा, यानी एक पूरा घंटा देर;
  - या ECO बीच में लिखी हुई N1 files पढ़ेगा, state ≠ ledger → N1 "Frozen"। यह सुरक्षित है, पर मौका छूटता है।
- **सुधार:** 4h-close वाले घंटों में ECO को PaperN1 के ख़त्म होने से जोड़ें (एक ही cron line में `PaperN1 && ECO`)। साथ में ECO में जाँच हो कि "N1 का T = अभी का 4h close", वरना note या alert। इससे देरी 20 min से घटकर ~4 min भी होगी।

---

## 10. Live tracking का नया सबूत: ECO का N1 हिस्सा बनाम PAPER-N1

**सबूत (VM ledgers):**
- ECO का N1 attribution, उन्हीं 4h windows में PAPER-N1 equity के बदलाव × a_N1 × E_m / N1 equity से मिलाया।
- दोनों windows का ECO N1 हिस्सा ≈ 4,600 USDT था।

| Window (UTC) | ECO N1 हिस्सा | PAPER-N1, scaled | फ़र्क | % |
|---|---|---|---|---|
| 10-21 20:20 → 10-22 00:20 | −8.61 | −11.60 | +2.99 | 0.065% |
| 10-22 00:20 → 04:20 | −18.95 | −13.70 | −5.25 | 0.11% |

**कारण (ledgers से):**
- 10-22 00:00 पर N1 ने **57 positions खोलीं**, कुल 970 USDT notional, यानी औसत ~17 USDT की।
- ECO ने 00:20 पर सिर्फ़ **3 orders** किए (ADA, BTC, XLM; ~167 USDT)। बाकी या तो आपस में netting में कट गए, या band (25 USDT) के अंदर रहे।
- साथ में 20 मिनट का समय अंतर है: N1 4h-open पर गिनता है, ECO :20 के mark पर।

**मतलब:**
- यह फ़र्क **कोई bug नहीं**, design से आता है (band + netting)।
- पर TC test की सीमा (|d_day| ≤ 0.30%) के सामने यह 4 घंटे में ही 0.1% तक पहुँचा। यह **noise का बड़ा स्रोत** है।
- N1 का C sleeve (~15.9k trades/साल, छोटे positions) ECO में आधा-अधूरा ही दोहराया जाता है।

**सुधार:**
- live verifier में यह tracking check जोड़ें (§7.11, L12);
- भाग 1 का P1-2 (खोलना ≠ adjust करना);
- research सवाल: क्या N1-C को ECO के band पर चलाने से उसका crash-hedge मक़सद बचता है? इसे replay में नापें।

**1D हिस्सा:** ECO 1D attribution आज 02:20 → 06:20 में −39 से +74.5 पहुँचा, intraday चाल की वजह से। F4 ledger सिर्फ़ रोज़ एक बार लिखता है, इसलिए intraday पर तुलना संभव नहीं। अगले दिन की as-of तुलना TC/R2 तरीके से ही करनी होगी।

---

## 11. Research के नतीजे (बाहरी सबूत) और हमारे लिए मतलब

| विषय | क्या मिला | हमारे लिए मतलब |
|---|---|---|
| **Survivorship bias, crypto** | Stöckl & Liebi (St. Gallen, 2022): 3,904 coins, 2014–2021 पर survivorship bias **value-weighted पर 0.93%/साल, equal-weighted पर 62%/साल**। Size premium ~50% बढ़ा हुआ मिला। Fix: point-in-time universe | हमारे sleeves coins को लगभग बराबर (inverse-vol) weight देते हैं, यानी हम EW वाले ख़तरे के पास हैं। P0-3 और ज़रूरी हो जाता है। (मैंने पूरा paper नहीं पढ़ा, सिर्फ़ abstract; पक्का करने को paper पढ़ना बाकी) |
| **DSR (Bailey & López de Prado 2014)** | Hurdle = N independent "zero-skill" trials में से सबसे अच्छी Sharpe की उम्मीद। उसमें **trials के बीच Sharpe का variance** सीधे जाता है। Correlated trials के लिए effective N clustering से निकालने की सलाह | भाग 1 §1.1 सही था। सुधार: project की **सारी trial registries** की असली Sharpe values से variance और clustering से effective N निकालें; एक family के variants से नहीं |
| **Gârleanu & Pedersen (J. Finance 2013)** | Cost होने पर सबसे अच्छा नियम है "aim portfolio की तरफ़ **थोड़ा-थोड़ा** बढ़ो", और धीमे signals को ज़्यादा वज़न | हमारा band per-symbol vol या cost नहीं देखता (हर symbol पर 0.25% × E)। सुधार उम्मीदवार: partial adjustment या per-symbol band। **Trial चाहिए, बिना test के लागू नहीं** |
| **Binance funding interval** | Symbols के हिसाब से 1h / 2h / 4h / 8h, और Binance इसे बदलता रहता है (जैसे 1h से 4h, 4h से 2h) | ✅ सही मिला: PAPER-N1 (line 204) और ECO plan (line 345–349) दोनों funding को **event-by-event** API से लेते हैं, 8h मानकर नहीं |
| **Algo order statuses** | 7 statuses; FINISHED ≠ ज़रूरी fill | §7.3 |
| **Market order response** | RESULT पर MARKET order "final FILLED result" देता है (docs); default ACK है | §7.4: ECO का RESULT चुनना सही है, पर जाँच ज़रूरी |
| **Delisting** | 09:00 UTC settlement; insurance fund आख़िरी घंटे में नहीं | §8 |

**Sources (research):**
- [Stöckl & Liebi, survivorship bias in crypto (Uni St. Gallen)](https://alexandria.unisg.ch/handle/20.500.14171/108037)
- [CoinAPI: survivorship bias](https://www.coinapi.io/learn/glossary/survivorship-bias)
- [Deflated Sharpe Ratio (SSRN)](https://papers.ssrn.com/abstract=2460551)
- [Deflated Sharpe ratio (Wikipedia)](https://en.wikipedia.org/wiki/Deflated_Sharpe_ratio)
- [Gârleanu & Pedersen, NBER w15205](https://www.nber.org/papers/w15205)
- [Binance: Query All Algo Orders](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Query-All-Algo-Orders)
- [Binance: New Algo Order](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Algo-Order)
- [Binance: New UM Order (RESULT/ACK)](https://developers.binance.com/docs/derivatives/portfolio-margin/trade/New-UM-Order)
- [Delisting notice coverage (whale-alert)](https://whale-alert.io/stories/8f7cb4659d85/Binance-Futures-to-delist-BID-DMC-ZRC-and-TANSSI-final-settlements-set-for-Jan-21-after-citing-extreme-volatility-and-low-liquidity)
- [Binance funding update (u.today)](https://u.today/binance-releases-important-funding-update)

---

## 12. Test coverage: कौन-सा path test है, कौन-सा नहीं

| Path | Mock test? | टिप्पणी |
|---|---|---|
| Netting, attribution identity, band, internal transfer | ✅ U1–U5 | |
| Funding का signed बँटवारा | ✅ U6 | **समय** (§7.5) test नहीं |
| Caps | ✅ U7 | Frozen + caps (§7.8) नहीं |
| Virtual stop, suppression | ✅ U8–U9 | |
| Crash recovery, lock, stale producer, छेड़ा हुआ producer | ✅ T1–T4 | |
| Reconcile freeze | ✅ T6 | |
| Kill switch | ✅ T7, S6 | Frozen symbol के साथ kill (भाग 1 §2.1) और > 40 symbols (§2.2) नहीं |
| Exchange stops: place, keep, fire, guard, virtual | ✅ S1–S5 | **TRIGGERING / FINISHED-बिना-fill / REJECTED / cancel fail** नहीं (§7.3) |
| Cut-over adopt | ✅ X1–X2 | Gate का 3-दिन वाला हिस्सा नहीं |
| **Month rollover** (E_m, k_m, inverse-vol weight) | ❌ | आज VM dry-run से path ठीक है (§7.13) |
| **Market response NEW / 0 / partial** | ❌ | §7.4 |
| **Price missing** | ❌ | §7.2 |
| **Halted ledger पर verifier** | ❌ (मैंने आज हाथ से चलाया: crash) | §7.1 |
| **Atomic state / टूटी state file** | ❌ | §7.7 |
| **Delisting / deliveryDate** | ❌ | §8 |
| **अनाथ algo orders** | ❌ | §7.6 |

**Coverage का निचोड़:**
- "Happy path" और मुख्य हिसाब अच्छी तरह test हैं।
- **Failure paths, जो सिर्फ़ असली exchange पर आते हैं, लगभग test नहीं हैं।**
- Demo cut-over से पहले इन्हें mock में जोड़ना चाहिए।

---

## 13. नए enhancements: profit, मौके, loss (भाग 1 के अलावा)

| # | सुधार | किस सबूत से | फ़ायदा | ज़रूरत |
|---|---|---|---|---|
| E1 | ECO को PaperN1 के ठीक बाद चलाना (event chain) | §9 | N1 फ़ैसले 20 की जगह ~4 min में लागू; race ख़त्म | Cron + छोटा code |
| E2 | Delisting नियम `deliveryDate` से | §8 | Settlement और ADL के ख़तरे से बचाव | Code + test |
| E3 | Missing-price पर last-known mark | §7.2 | Kill switch हमेशा जागता रहे | छोटा code |
| E4 | Exchange fills और stops का असली हिसाब (userTrades), TRIGGERING या FINISHED की सही व्याख्या | §7.3–7.4 | Demo या real में ledger = wallet | Code + mock |
| E5 | Partial adjustment या per-symbol band | §11 (Gârleanu–Pedersen), §10 | Cost कम, tracking बेहतर | **नया trial** |
| E6 | N1-C sleeve: ECO में उसका असली असर नापना | §10 | या तो hedge बचे, या बेकार trades हटें | Replay research |
| E7 | DSR: सारे trials से SR variance और effective N | §11 | ईमानदार भरोसा | Verifier |
| E8 | Atomic writes + state backup | §7.7 | एक crash से system बंद न हो | छोटा code |
| E9 | Alerts की पूरी सूची | §7.1, 7.2, 7.6, 7.10, §8, §9 | Halt, verifier crash या rc≠0, गायब price, freeze > 2 cycles, held symbol का deliveryDate, अनाथ stop, N1 का T पुराना: सब पर तुरंत ख़बर | P0-2 के साथ |

---

## 14. नई priority सूची (भाग 1 + भाग 2 मिलाकर)

| # | काम | स्रोत | कब तक |
|---|---|---|---|
| **P0-1** | Kill switch: frozen symbol और 40 की सीमा (भाग 1) + **halt reset औज़ार + halted cycles में mark** | भाग 1 §2.1–2.2, §7.10 | Demo से पहले |
| **P0-2** | Alert system + **verifier: L8 halted=FAIL, crash-proof, L9 identity, L10 held-cap** | भाग 1 §2.8, §7.1, §7.11 | Demo से पहले |
| **P0-3** | Survivorship-free test (ECO का आख़िरी trial); settled perps की list (§8) मदद करेगी | भाग 1 §1.2, §11 | Real money से पहले |
| **P0-4** | Delisting नियम (`deliveryDate` / SETTLING) + N1 perp map की सफ़ाई | §8 | Demo से पहले |
| **P0-5** | **Missing-price से equity न जमे** | §7.2 | Demo से पहले |
| **P0-6** | **Exchange सच्चाई:** market response की जाँच, algo statuses, अनाथ stops, असली fills | §7.3, 7.4, 7.6 | Demo से पहले (ये सिर्फ़ demo/real में आते हैं) |
| **P0-7** | Demo cut-over + TC (gate में 3-दिन verify जोड़कर); margin mode note | भाग 1 P0-5, §7.12 | आपकी हाँ |
| **P0-8** | आपके काम: commissionRate, BNB, tax | भाग 1 | आप |
| P1-1 | Atomic state/ledger writes | §7.7 | |
| P1-2 | Funding का सही समय | §7.5 | TC से पहले बेहतर |
| P1-3 | ECO ↔ PaperN1 event chain | §9 | |
| P1-4 | Spot routing; band में खोलना ≠ adjust करना; pending-short stop आधार; M10 | भाग 1 P1 | |
| P1-5 | Orders की सीमा का note + priority; frozen-caps | §7.8–7.9 | |
| P2 | Partial adjustment / per-symbol band (trial); N1-C का असर; DSR effective N; sleeve-स्तर बँटवारा; नया uncorrelated edge | §11, §10, भाग 1 | नया budget |

**गिनती:**
- **P0 के code वाले काम (P0-1, 2, 4, 5, 6) कोई trial नहीं माँगते।** ये सब code, mock tests और CODE_CHANGES हैं, क्योंकि strategy नहीं बदलती, सिर्फ़ safety और हिसाब बदलते हैं।
- P0-3 और E5 ही trials हैं।

---

## 15. भाग 1 में सुधार (ईमानदार errata)

1. **§2.9** में सिर्फ़ SXP लिखा था। सही: N1 perp map के 133 में से **28 नाम** आज TRADING नहीं हैं (§8)। आज किसी held position पर असर नहीं।
2. **§2.11** में "attribution identity live 13/13 में 0.000" मेरी हाथ की जाँच थी। Cron वाला verifier यह check **नहीं** करता (§7.11)।
3. **§2.4** (plan mode reconcile untestable) सही है। अब उसमें §7.3, 7.4 और 7.6 भी जोड़ें: ये सब सिर्फ़ demo में दिखेंगे, इसलिए cut-over का पहला हफ़्ता सबसे नाज़ुक है।
4. **§2.2** सिर्फ़ kill वाली स्थिति पर था। 40 की सीमा normal cycles में भी चुपचाप लगती है (§7.9)।

## 16. अंतिम निष्कर्ष (भाग 2)

- **हिसाब का core (netting, attribution, caps, stops का design) फिर से सही पाया गया।** State सीमित है, timing आज ठीक है, जगह और घड़ी ठीक हैं, November का weight path चलता है।
- **कमज़ोरी error paths में है:**
  - halt पर verifier का टूटना (**test से साबित**);
  - एक गायब दाम से kill switch का अंधा होना;
  - exchange के जवाबों (NEW, TRIGGERING, FINISHED) की अधूरी व्याख्या;
  - अनाथ stops;
  - non-atomic files।

  ये सब plan mode में **कभी नहीं दिखेंगे** और demo या real में पहली बार आएँगे। इसलिए इन्हें demo cut-over से **पहले** ठीक करना चाहिए।
- **Profit की तरफ़:**
  - सबसे बड़ा अनिश्चय अब भी survivorship है। Research (EW पर 62%/साल bias) इसे और गंभीर बताती है।
  - Execution में सबसे सस्ता सुधार ECO ↔ N1 event chain है।
  - Band और partial adjustment का फ़ायदा सिर्फ़ trial से साबित होगा।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---
---

# भाग 3: audit → fix → दोबारा audit का loop (22 अक्टूबर 2026, pass 3–5)

**सवाल (user):** पूरे integrated ecosystem को audit → find → fix → फिर audit के loop में डालो, जब तक gap और गलतियाँ ख़त्म न हों, और हर बार इसी file में जोड़ो। भाग 1–2 के अलावा जो बचा है, वह भी देखो: logic, code, गणित, नतीजे, research।

**इस भाग का अनुशासन:**
- हर code बदलाव से **पहले** नियम lock किए गए:
  - `logs/eco/ECO_AMENDMENT_2_PREREGISTERED.md`, SHA `312a2c49…`, locked 2026-10-22 10:39 UTC;
  - `logs/log_ship/LOG_SHIP_PROTOCOL_V4_AMENDMENT.md`, SHA `e6f900d5…`, locked 10:58 UTC।
- Strategy का कोई input नहीं बदला (signals, weights, caps, band, fee, kill K, guard D, stops)। Trial budget जस का तस है: 4 में से 3।
- **VM पर कुछ deploy नहीं हुआ।** सारे बदलाव laptop पर हैं, tests के साथ। Deploy आपकी हाँ के बाद होगा (§23)।

---

## 17. Pass 3: वे हिस्से जो भाग 1–2 में नहीं पढ़े गए थे

इस pass में ये पूरे पढ़े गए:
- `paper_n1_portfolio.py` (359 lines);
- `forward_ls_f4.py` (419);
- `eco_replay.py` (172);
- `ship_logs_drive.py` (179);
- `test_eco_core.py` (383)।

साथ में VM पर N1 की live state देखी।

### 17.1 PAPER-N1 producer (locked forward test; code नहीं बदला)

| # | Finding | सबूत | असर |
|---|---|---|---|
| N-1 | **एक cycle छूटा, तो उस bar पर शुरू हुई entries हमेशा के लिए छूट जाती हैं** | Entry की शर्त है `s[-1] == 1 and (s[-2] == 0 or tf_init)` (line 250), यानी सिर्फ़ जिस bar पर signal बदला। Crontab में PaperN1 की **सिर्फ़ एक** line है (`41 1,5,9,13,17,21`), कोई retry नहीं, जबकि Step16, 16B, F4 और F6 की दो-दो lines हैं | अगर 4 घंटे वाला run fail हो (network, VM restart), तो उस bar की हर नई entry पूरी holding अवधि के लिए गायब रहेगी, जबकि backtest में वह होती। अभी 7/7 runs सफल हैं (`cron_status`) |
| N-2 | **D sleeve के rebalance में KeyError से पूरा cycle crash** | Line 281: `close_pos(..., cur_open[k.split("|")[1]], ...)`। अगर किसी held D coin का data उस T पर न मिले (network या delisting), तो `cur_open` में key नहीं होगी | हर 5वें दिन (D rebalance) पूरा N1 cycle टूटेगा, और ECO उसे "stale" मानकर freeze करेगा |
| N-3 | **Funding entry notional पर, आज के मूल्य पर नहीं** | Line 206: `fund_paid += side * r * p["notional"]` (`notional` = entry के समय का) | गणित की गलती। 50% बढ़ी position पर funding 1/3 कम गिनी जाती है। आकार छोटा है: funding ~0.01%/8h, और live 8 cycles में कुल funding 0.25 USDT |
| N-4 | **Ledger state से पहले लिखा जाता है, और atomic नहीं** | Lines 330–332: पहले ledger append, फिर `state.json` | दोनों के बीच crash हो तो: ledger का T ≠ state का `last_T` → ECO N1 को freeze करेगा (`load_n1`); N1 का अगला run पुरानी state से चलेगा |
| N-5 | **Spot पर route हुई positions ECO में perp पर चलती हैं** | VM state (22-10): 245 में से **12 positions spot पर** (A 10, B 2), यानी **751 / 5,178 USDT = N1 gross का 14.5%**। ECO हर position perp पर लेता है | ECO वही ऊँची funding देता है जिससे बचने के लिए X2 ने spot चुना था। यह N1 paper और ECO के बीच **लगातार एक दिशा में tracking फ़र्क** है। भाग 1 का P1-1 (spot execution) अब इस आँकड़े से नापा गया है |

### 17.2 F4 producer (locked forward test; code नहीं बदला)

| # | Finding | सबूत | असर |
|---|---|---|---|
| F-1 | **"हो गया" का निशान ledger से पहले लिखा जाता है** | `equity_{asof}.csv` line 297 पर लिखी जाती है, और line 245 इसी file को "already logged" मानती है। Ledger line 320 पर लिखी जाती है | बीच में crash हो तो दूसरा cron run "nothing to do" कहेगा, और **उस दिन की ledger line कभी नहीं बनेगी**। ECO 2 दिन तक पुराने orders पर चलेगा, फिर 1D freeze |
| F-2 | C1 = False (F4 ख़ुद कहे "आज के LS नंबर untrusted") होने पर भी ECO पहले उन्हीं orders पर चलता था | `load_f4` में C1 की कोई जाँच नहीं थी | ✅ **ठीक किया (ECO की तरफ़, A2 §7):** अब 1D freeze होता है। Test A2-14 |
| F-3 | Forward में LS_RS = LS_F2 (दोनों 9,968.27); RS नियमों ने अभी तक कुछ नहीं बदला (`stops_LS_RS` 0) | F4 ledger 22-10 | सिर्फ़ जानकारी: RS नियमों का असर अभी forward में नापा नहीं जा सकता |

### 17.3 E-3 replay की timing (errata)

- `eco_replay.py` line 18 में `N1_AVAIL = 41 min` है। Replay हर घंटे के **:50 UTC** पर चलता है।
- पर crontab IST में है:
  - PaperN1 :41 IST = **:11 UTC** पर चलता है (~3 मिनट लेता है);
  - ECO :50 IST = **:20 UTC** पर चलता है।
- यानी replay का समय live से **30 मिनट बाद** का है, और N1 के फ़ैसले replay में 50 मिनट बाद लागू होते हैं जबकि live में 20 मिनट बाद।
- Protocol (§4 line 91) "minute 50 (after PaperN1 at :41)" भी IST minutes में लिखा है।
- **असर:** E-3 plumbing का test (R1, R3–R6) वैध रहता है। R2 (1.20%) की timing वाली व्याख्या में यह 30 मिनट का फ़र्क भी शामिल है।
- **सुधार:** आगे हर दस्तावेज़ में समय UTC में और साफ़ लिखा जाए।

### 17.4 LogShip (✅ ठीक किया, v4)

- **गलती:**
  - `run_job.sh` job **शुरू होते ही** `.out` को `>>` से खोल लेता है।
  - F1 15 मिनट से चुप `.out` का नाम बदल देता है।
  - पर F4 16B का इंतज़ार 90 मिनट तक बिना कुछ print किए करता है (lines 257–261), और Step16 1,307 s तक चला है।
  - ऐसे चलते job का बाकी output नाम बदली हुई file में जाता है, और bundle verify होने के बाद वह file मिटा दी जाती है। यानी **output खो सकता था।**
- **सुधार (v4):** नाम तभी बदला जाता है जब कोई process उस file को खोले न हो (`/proc/*/fd`)।
- **Test:** नया T7 PASS; पुराने T1–T6 PASS; **8/8**।

---

## 18. Fix loop, round 1: amendment 2 के तहत क्या ठीक हुआ

| भाग 1–2 की finding | सुधार (code) | Test |
|---|---|---|
| भाग 1 §2.1: kill के समय frozen symbol खुला रह जाता था | Kill में **हर** held symbol exchange की quantity से reduce-only बंद होता है, frozen भी | A2-1 ✅ |
| भाग 1 §2.2: kill में सिर्फ़ 40 orders | Kill में कोई सीमा नहीं | A2-2 ✅ (45 symbols, एक cycle में flat) |
| §7.10: halt के बाद कुछ नहीं होता था, reset का औज़ार नहीं था | `halted_cycle`: equity mark होती है, बचे हुए positions बंद होते हैं, और journal recovery चलती है। नया `eco_reset.py` (`--show`, `--reset`, `--unfreeze`; peak भी reset; ledger record) | A2-3 ✅, A2-4 ✅ |
| §7.2: एक दाम गायब → पूरी equity जम जाती थी | `last_px` से mark होता है, `n_px_missing` गिनता है | A2-5 ✅ (BTC का दाम छुपा होने पर भी kill चला) |
| §8: delisting | `deliveryDate` < 2100 → target 0। SETTLING या गायब → note + alert | A2-6 ✅ |
| §7.4: market order का जवाब | FILLED, qty > 0 और price > 0 की जाँच; 3 बार query; पक्का न हो तो journal में रहे; price ≤ 0 पर fill मना | A2-7 ✅ |
| §7.3: algo statuses | TRIGGERING / बिना fill का TRIGGERED → रुको; FINISHED बिना fill → कुछ दर्ज नहीं; fill हो तो `actualQty` @ `actualPrice` | A2-8 ✅ |
| §7.6: अनाथ stops | `clientAlgoId = eco…`; अनजान eco stop cancel; दूसरों के stops की report | A2-9 ✅ |
| §7.7: atomic files | temp + fsync + `os.replace`, `state.prev.json`; टूटी state → failed record; टूटी ledger tail → साफ़ error | A2-10 ✅ |
| §7.5: funding का समय | Orders से **पहले**, उन्हीं components पर जिनके पास interval के दौरान position थी | A2-11 ✅ |
| §7.9: 40 की सीमा चुपचाप | सबसे बड़े orders पहले; बाकी `max_orders` के नाम से दर्ज | A2-12 ✅ |
| §7.8: frozen + caps | Frozen components caps से scale नहीं होते | A2-13 ✅ |
| F-2: C1 = False | 1D freeze | A2-14 ✅ |
| §7.1, §7.11: verifier | L8 (halt = FAIL, crash नहीं), L9 identity, L10 held-caps, L11 code SHAs | A2-15 ✅ |
| भाग 1 §2.8: alerts | `eco_alerts.py`: 10 शर्तें; हर alert एक बार (dedupe); `logs/eco/alerts/alerts.jsonl`; Telegram सिर्फ़ तब जब आप keys डालें | A2-18 ✅ |
| §7.12: cut-over gate | Gate में "ECO_Verify के पिछले 3 runs, 3 अलग दिन, सब exit 0" + margin type की report | (VM पर `--check` से) |

---

## 19. Fix loop, rounds 2–3: मेरे अपने fixes में मिली गलतियाँ (ईमानदार सूची)

हर round के बाद नया code फिर से पढ़ा गया और tests चलाए गए। **इन fixes में ख़ुद 8 गलतियाँ मिलीं**, और सब deploy से पहले ठीक हुईं:

| # | गलती | कैसे पकड़ी | सुधार |
|---|---|---|---|
| R-1 | **Order id टकराना:** unconfirmed order के बाद उसी millisecond में अगले order को वही `clientOrderId` मिलता था (`ms % 1e10 + len(fills)`), जिससे recovery ग़लत order को book करती। यह पुराने code में भी था (भाग 2 में छूट गया था) | Test A2-7 (mock में equity −3.99 M) | `eco<yymmddHHMM>n<i>`। नोट: Binance पर query में symbol भी जाता है, इसलिए वहाँ दो अलग symbols आपस में नहीं मिलते। असली ख़तरा कम था, पर अब शून्य |
| R-2 | **Caps में equity ≤ 0 पर positions उलटी हो जातीं** (cap % × नकारात्मक equity) | A2-4 का पहला draft | Equity ≤ 0 → सारे targets 0 |
| R-3 | **Funding का ग़लत बँटवारा:** amount orders से पहले की positions पर, पर बँटवारा orders के बाद वाले components में; net 0 हुआ तो amount छूट जाता | **E-3 replay regression:** R1 8e-10 से बढ़कर 1.88e-02 | Funding orders से पहले book |
| R-4 | **Kill वाले cycle के record में `halted` नहीं था** (सिर्फ़ अगले cycles में) | A2-18 (alert नहीं बना) | Record में `halted` |
| R-5 | Unconfirmed order अभी "NEW" हो तो अगला cycle उसी symbol पर **दूसरा order** भेज सकता था | Code दोबारा पढ़ने पर | वह symbol उस cycle में "busy"। A2-16 ✅ |
| R-6 | Kill पर ledger में ऐसी position जो exchange पर नहीं → ledger में "भूत" position रह जाती | Code दोबारा पढ़ने पर | Mark पर ledger में बंद, note। A2-17 ✅ |
| R-7 | Halted cycle में journal recovery नहीं होती थी | Round 3 | साझा `recover_journal` |
| R-8 | Plan mode में जिस symbol का मौजूदा दाम न हो, उस पर order → `KeyError` → cycle crash | Round 3 | "no current mark" → order नहीं, अगले cycle फिर कोशिश |

**एक जानबूझकर किया गया बदलाव (CODE_NOTES 4):**
- Amendment 2 §4 का text कहता है "TRIGGERED बिना fill → drop"।
- पर Binance docs में TRIGGERED का मतलब "matching engine में पहुँचा" है, ज़रूरी नहीं कि fill हुआ हो।
- इसलिए code इसे **रोक कर रखता है** और अगले cycle में देखता है। यह fill न खोने की तरफ़ ज़्यादा सख़्त है। CODE_CHANGES 6 में दर्ज।

---

## 20. Test और regression के नतीजे

| जाँच | नतीजा |
|---|---|
| `test_eco_core.py` | **43 checks:** पुराने 25 + नए 18 (A2-1…A2-18) |
| Laptop पर | 42/43 PASS। CODE_CHANGES 6 में SHAs लिखने के बाद A2-15 भी PASS हुआ। T8 नहीं चला: laptop से Binance तक network timeout (`curl` से भी 000) |
| **VM पर** (scratch copy `/tmp/ecoA2`, production को नहीं छुआ, बाद में मिटाई) | **43/43 PASS, T8 समेत** (demo 528, mainnet 524 TRADING perps; 18/18 mark prices) |
| **नया live verifier, असली VM ledger पर** (read-only) | **L1–L11, 11/11 PASS**: 18 cycles; **L9 identity 18/18 cycles पर** (अब cron वाली जाँच, हाथ वाली नहीं); L11: सारे 5 code SHAs listed; L10 पुराने records पर लागू नहीं (`held_net` नया field है) |
| `test_log_ship.py` | **8/8 PASS** (T7 नया) |
| E-3 replay regression (नए code पर, 2 बार) | Final code (SHAs 4813d881 / 95bccb3b / a29e8ecd): **R1 8.32e-10** (पहले जैसा; बीच में funding वाली गलती पर 1.88e-02 था, §19 R-3), R3 / R5 0, **R6 दोनों replay एक जैसे**, R4 9/9, R2 1.204% (पुराना ज्ञात E-3 FAIL, नहीं बदला; अंतिम equity 9,817.72 बनाम पहले 9,817.70, funding के समय का छोटा असर) |
| Alert job, scratch में halted ledger पर | पहला run: 2 alerts (halted, ECO_Verify fail); दूसरा run: 0 नए (dedupe); keys के बिना: सिर्फ़ file |

---

## 21. अब भी खुले मुद्दे (जो इस loop में जानबूझकर **नहीं** ठीक किए)

ये strategy या दूसरे locked experiments को छूते हैं। इन्हें बिना protocol या आपकी हाँ के बदलना अनुशासन तोड़ना होगा।

| # | मुद्दा | क्यों अभी नहीं | अगला कदम |
|---|---|---|---|
| O-1 | PAPER-N1: N-1 (छूटा cycle), N-2 (D KeyError), N-3 (funding notional), N-4 (atomic) | PAPER-N1 एक locked forward test है (`PAPER_N1_PROTOCOL_PREREGISTERED.md`)। बीच में code बदलने से experiment बदलता है | PAPER-N1 amendment 1: catch-up cycles (छूटे T को क्रम से चलाना), D पर `last_px`, mark-value funding, atomic files। **आपकी हाँ चाहिए** |
| O-2 | F4: F-1 (idempotency marker) | F4 भी locked है | F4 amendment: पहले ledger, या marker = ledger line। **आपकी हाँ** |
| O-3 | Survivorship test (भाग 1 P0-3) | ECO का आख़िरी trial | आपकी हाँ |
| O-4 | Spot execution (N-5: 14.5%) | नया execution path; protocol + demo-spot test चाहिए | P1 |
| O-5 | Band: खोलना ≠ adjust करना; partial adjustment (भाग 2 §11) | Tracking और cost बदलते हैं, trial चाहिए | P1/P2 |
| O-6 | Weight windows की तारीखें (भाग 2 §7.13) | Weight का नियम बदलता है | CODE_CHANGES + verifier |
| O-7 | ECO ↔ PaperN1 event chain (भाग 2 §9) | Cycle का समय बदलता है (protocol §4) | Amendment |
| O-8 | Demo पर असली सबूत: algo statuses, NEW जवाब, अनाथ stops | Plan में कभी नहीं दिखेंगे | Cut-over का पहला हफ़्ता |
| O-9 | DSR का effective N, sleeve-स्तर का बँटवारा, नया edge | Research | P2 |

**ईमानदार बयान:**
- इस loop के बाद ECO executor में **मुझे पता कोई खुली गलती नहीं बची**। सारी findings ठीक हुईं, और हर एक का test है।
- पर "zero gap, zero mistake" का दावा मैं **नहीं** कर सकता:
  - (a) ऊपर के 9 मुद्दे जानबूझकर खुले हैं;
  - (b) exchange वाले रास्ते (O-8) सिर्फ़ demo में साबित होंगे;
  - (c) हर round में मेरे अपने fixes में नई गलतियाँ मिलीं: round 2 में 6, round 3 में 2। इसलिए deploy के बाद live verifier (L1–L11) और alerts ही अगला loop हैं।

---

## 22. Changed files (laptop, deploy नहीं)

| File | बदलाव |
|---|---|
| `logs/eco/ECO_AMENDMENT_2_PREREGISTERED.md` + SHA | नया, locked |
| `src/eco/eco_core.py` | C1 freeze, frozen caps, equity ≤ 0, price ≤ 0 refuse, `book_triggered` (qty/px), corrupt-tail error, fsync, `write_json_atomic` |
| `src/eco/eco_exchange.py` | `delivery_ms`, `confirmed_fill`, `algo_fill`, `open_algo` |
| `src/eco/eco_orchestrator.py` | §18–19 के सारे बदलाव |
| `src/eco/eco_cutover.py` | Gate में 3-दिन verify + margin type; atomic write |
| `src/eco/eco_reset.py`, `src/eco/eco_alerts.py` | नए |
| `src/audits/verify_eco_live.py` | L8–L11, crash-proof |
| `src/audits/test_eco_core.py` | Mock को असली API के आकार में ढाला (stop status = status, actualQty, actualPrice) + A2-1…18 |
| `logs/eco/CODE_NOTES.md` | Note 4 |
| `deploy/ship_logs_drive.py`, `src/audits/verify_log_ship.py`, `src/audits/test_log_ship.py`, `logs/log_ship/LOG_SHIP_PROTOCOL_V4_AMENDMENT.md` + SHA | LogShip v4 |
| `deploy/crontab_proposed_A2.txt` | प्रस्तावित crontab: ECO_Alerts, हर घंटे :52 IST और 07:27 IST। `deploy/crontab.txt` = VM, नहीं बदला |

## 23. Deploy का प्रस्ताव (आपकी हाँ के बाद)

1. VM पर code की SHA के साथ copy, और पुरानी files का backup।
2. **Live ledger पर पहले नया verifier** (L1–L11)। पुराने records में `held_net` नहीं है, इसलिए L10 सिर्फ़ नए records पर चलेगा।
3. एक plan cycle, फिर verifier, फिर alert job। कोई false alert नहीं होना चाहिए।
4. Crontab में ECO_Alerts की 2 lines (backup के साथ)।
5. VM पर T8 (public endpoints) और पूरा `test_eco_core.py` एक scratch copy में।
6. आप चाहें तो Telegram bot के `ECO_TELEGRAM_TOKEN` और `ECO_TELEGRAM_CHAT` `.env` में डालें (मैं keys नहीं डालता)।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---
---

# भाग 4: emotion research का code + एक साथ deploy (22 अक्टूबर 2026, 12:38–13:35 UTC)

## 24. क्या बना (हर चीज़ से पहले protocol lock)

| चीज़ | Lock | Code | Test |
|---|---|---|---|
| **R-A: EMO meter** (भीड़ की हालत हर घंटे; सिर्फ़ जानकारी, कोई order नहीं) | `logs/emotion/EMO_METER_PROTOCOL_PREREGISTERED.md` e7a20dc2… | `src/eco/emotion_meter.py`, `verify_emotion_live.py` (M1–M5) | Offline E1–E5 5/5 (हर feature हाथ की गणना से मिलाया; खुला घंटा बाहर; ranks; error वाला symbol बाहर; छेड़ा score → M3 FAIL)। VM scratch पर असली data: 25/25 symbols, M1–M5 PASS |
| **EMO-1** (crowding study) | `EMO1_PROTOCOL_PREREGISTERED.md` b777c510… + trial registry (P, R1, R2) | `src/research/emo_download.py` (सिर्फ़ stage D, data) | VM scratch: resume, 404 दर्ज (FTT का halt), SHA की दोबारा जाँच 0 mismatch |
| LogShip v5 | 07a199f3… | Emotion ledger, manifests, logs/emotion → Drive; W4 में emotion ledger | T1–T7 8/8, W4 14/14 |
| Alerts | — (A2 §8) | EMO_Meter, EMO_Verify, LogShip की job failure भी | A2-18 PASS |

## 25. Deploy (VM, 12:48–12:50 UTC; ECO cycles के बीच)

1. Backup: `backups/2026-10-22/pre_A2_deploy.tgz` (बदली जाने वाली 11 पुरानी files) + `deploy/crontab_backup_before_A2_20261022.txt` (पुराना crontab, 29 lines)।
2. 31 files copy हुईं; **31/31 SHA = laptop**।
3. VM production tree पर tests: **test_eco_core 43/43 PASS** (T8 भी), test_emotion_meter 5/5।
4. Live ledger पर नया verifier: L1–L11 11/11।
5. Meter का पहला run: 25/25 symbols; emotion verifier 5/5। Alerts: 0 conditions।
6. Crontab: 6 नई lines (ECO_Alerts ×2, EMO_Meter, EMO_Verify + 2 comments), पुरानी 29 lines वैसी ही।

**ज़मीनी जाँच में पकड़ी गई गलती:**
- Windows पर लिखी `crontab.txt` में CRLF था, यानी हर line के आख़िर में `\r` जिससे हर cron command टूटता।
- Install के बाद `cmp` ने इसे पकड़ा। ~1 मिनट (12:49 UTC) में ठीक करके दोबारा install किया।
- उस मिनट में कोई cron job नहीं था, इसलिए कोई job नहीं टूटा।
- अब 0 CR हैं, और installed crontab == file (SHA f1e227909bc1…)।
- Python files में भी CRLF हैं (Windows writes)। Python पर इसका असर नहीं: 43/43 tests VM पर उन्हीं files से PASS हुए। यह दर्ज है।

## 26. नए code पर पहला live cycle (13:20 UTC) और उसके बाद

| जाँच | नतीजा |
|---|---|
| ECO_Plan 13:20 | exit 0, ok, code SHAs 4813d881 / 95bccb3b / a29e8ecd (v3), equity 10,032.06, `held_net` 24, halted None, कोई price fallback नहीं, कोई delisting नहीं |
| Live verifier | **11/11**: L10 पहली बार नए record पर PASS, L11 में सारे 8 code SHAs listed |
| ECO_Alerts 13:22 | exit 0 |
| EMO_Meter 13:23 | exit 0 (25 s); emotion verifier 5/5 |
| LogShip 13:25 | 39 files का bundle verified; verifier W1–W4 PASS (W1 v2..v5 locks, W4 14/14) |
| EMO-1 download | Liq stage पूरा (13:12); **eligible 484 symbols** (protocol का नियम: 30-दिन median ≥ 50 M किसी भी दिन); metrics stage चल रहा है (13:35 तक manifest में 154k entries; disk 29%) |

## 27. जो अभी बाकी है (ईमानदारी से)

| काम | क्यों बाकी |
|---|---|
| **EMO-1 stage S** (features, portfolio, gates, verifier) | Protocol lock है, data उतर रहा है। Study code, verifier और dev run अगले session में होंगे, quota बचाकर, बिना जल्दबाज़ी के। Holdout तभी खुलेगा जब dev report का SHA दर्ज हो जाए |
| EMO-1 download का आकार | 484 eligible × ~1,765 दिन ≈ 850k files (listing से पहले के दिन 404 होंगे), अनुमानित ~10 GB, कुछ घंटे। Disk 34 GB free। Alerts disk नहीं देखते, इसलिए अगले session में `df` देखना है |
| R-B (crowding sleeve), R-C (risk filter) | EMO-1 के gates पर निर्भर |
| PAPER-N1 और F4 के producer fixes | उनके अपने amendments; आपकी हाँ |
| Demo cut-over + TC | Gate (~25-10) + आपकी हाँ; exchange वाले रास्ते वहीं साबित होंगे |
| Telegram alerts | आप `.env` में `ECO_TELEGRAM_TOKEN` / `ECO_TELEGRAM_CHAT` डालें; तब तक alerts सिर्फ़ `logs/eco/alerts/alerts.jsonl` में |

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
