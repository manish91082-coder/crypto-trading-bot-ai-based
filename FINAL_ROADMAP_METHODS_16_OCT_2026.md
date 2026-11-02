# अंतिम roadmap: नए तरीके कब, कैसे, और क्या फायदा (16 अक्टूबर 2026)

**आधार (दो reports):**
- `RESEARCH_TRADING_METHODS_BEYOND_SWING_16_OCT_2026.md` (14 तरीके + गणित)
- `RESEARCH_NEW_METHODS_LOSS_MIN_PROFIT_MAX_16_OCT_2026.md` (13 नए तरीके)

यह `FINAL_INTEGRATED_PENDING_PLAN_16_OCT_2026.md` के साथ जुड़ा है।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। असली पैसे का हर फैसला आपका है।

---

## 1. एक लाइन में तस्वीर
**"मज़बूत core + कुछ कम-मेल वाले sleeves + risk परत"**

| परत | क्या है |
|---|---|
| **Core** | AI relative long-short (F7)। अभी paper forward में चल रहा है। |
| **सुधार** | Short book सस्ता और सुरक्षित (E1–E4), खर्च कम (E11), lottery coins से बचना (N1)। |
| **Sleeves** | Funding-gated carry (E9), BTC trend से long घटाना (E7); बाद में options बीमा। |
| **Risk परत** | Stops, inverse-vol, धीरे-धीरे de-risking (E6), macro-event gate (N2), EVT monitor (N3), kill switch। |

## 2. हर काम का एक ही तरीका (अनुशासन, कभी नहीं बदलेगा)
1. **Protocol लिखना:** परिकल्पना, सटीक नियम, gates, control, ज़्यादा से ज़्यादा 2 variants। फिर **SHA lock।**
2. Code, अलग **verifier**, और नकली (random/shuffled) control।
3. Gates **F7 के मुकाबले और control के मुकाबले**, दोनों से पास होने चाहिए।
4. DSR हमेशा **अब तक के कुल trials** पर (पहले से ~85)।
5. पास हुआ variant सिर्फ **F4 में shadow line** बनेगा, और उसका भी **90 दिन** का forward सबूत चाहिए। तभी असली system में आएगा।
6. Lock के बाद हर बदलाव `CODE_CHANGES_AFTER_LOCK.md` में।
7. **कुछ भी पास न हो, तो F7 ही रहेगा।** यह भी सही नतीजा है।
8. **हर protocol में stop का fill gap-aware होगा:** max(trigger, open) + slippage। बड़े liquidation cascade के बाद order book की गहराई महीनों तक 1/4 से 1/3 कम रहती है, इसलिए slippage का अनुमान ऊँचा रखा जाएगा।
9. **Exchange और collateral का जोखिम:** USDe, wBETH, BNSOL जैसे yield-bearing collateral नहीं (अक्टूबर 2025 का depeg)। Futures wallet में पर्याप्त buffer रहेगा।
10. **1x से ज़्यादा leverage कभी नहीं।**

---

## 3. समय-रेखा: कब, क्या, कैसे, क्या फायदा

### चरण 0: रोज़, अभी से (बिना रुके)

| काम | कैसे | फायदा |
|---|---|---|
| 16B (spot) + F4 (long-short) paper log | Scheduled tasks। मैं रोज़ verifier चलाकर जाँचूँगा। | 90 दिन का असली सबूत, जो सबसे ज़रूरी है |
| **U1 (आप): wake timers चालू करें** | Windows Power Options → "Allow wake timers" = Enable | बिना इसके दिन late होते हैं। F4 में सिर्फ 4 और दिन खो सकते हैं। |

### चरण 1: Round 1 experiments (आपकी "हाँ" के बाद, ~17–23 अक्टूबर)
एक-एक करके, इसी क्रम में:

| # | Experiment | कैसे (सटीक नियम) | फायदा (लक्ष्य) |
|---|---|---|---|
| **E3** | Diagnostic: short की कमाई AI से है या सिर्फ नए listed coins के गिरने से | F7 के short P&L को listing-age के हिसाब से बाँटना। सिर्फ "नए coins short करो" (बिना AI) वाला नियम, और listing-age के बराबर shuffled control। | **सच्चाई पहले।** अगर कमाई AI की नहीं, तो short book का design बदलना होगा। |
| **E1** | Short book का एक हिस्सा BTC hedge | Short notional का w = 0.5 या 1.0 हिस्सा BTC perp short में, बाकी AI के bottom-5 में | Alt squeeze और alt funding का खतरा घटे, crash-बचाव बना रहे। **नुकसान ↓** |
| **E2** | Alt shorts पर filters | 3 दिन की औसत funding बहुत negative न हो, listing-age ≥ 60 दिन, liquidity पर्याप्त। फ़िल्टर से छूटी जगह BTC short में। | Squeeze और liquidation वाले shorts कम। **नुकसान ↓** |
| **E4** | हर leg के अंदर inverse-volatility weight + per-coin cap | weight ∝ 1/σ₆₀, cap = leg का 30% | एक coin पूरे portfolio को न डुबाए। **नुकसान ↓** |
| **N1** | Lottery (MAX) filter | पिछले 7 दिन का सबसे बड़ा daily return; top-20% MAX वाले coins long से बाहर (variant A); short में उन्हें प्राथमिकता (variant B) | Long में "फूले हुए" coins से बचना। **नुकसान ↓, फायदा ↑**। ⚠ pattern पहले देखा जा चुका है, यह protocol में लिखा जाएगा। |
| **E11** | Long leg भी USDT-M perps पर | Spot (0.25%) की जगह perp fee; long को funding चुकानी होगी, उसे भी गिनें | खर्च कम। **फायदा ↑** (खर्च हमारा सबसे बड़ा lever है) |

**चरण 1 का नतीजा:** जो पास हो, उसे F4 में shadow line बनाना। उसकी 90 दिन की घड़ी वहीं से शुरू होगी (~फरवरी 2027 के अंत तक)।

### चरण 2: साथ-साथ चलने वाले काम (trials नहीं गिने जाते)

| काम | कब | कैसे | फायदा |
|---|---|---|---|
| **N3: EVT tail-risk monitor** | Round 1 के साथ | रोज़ portfolio का 99% / 99.9% tail-loss अनुमान (peaks-over-threshold), F4 के साथ log | Kill switch और per-coin cap सही आकार के हों। **नुकसान ↓** (trading नहीं बदलता) |
| **M10: रोज़ का alert + local backup** | इस हफ्ते | रोज़ का सार (चला या नहीं, on_time, C1) + logs की local copy | Fail हुआ दिन तुरंत पता चले, data सुरक्षित रहे |
| **M4: Options/DVOL + quarterly basis data** | आपकी हाँ पर, इस हफ्ते | Public API से रोज़; कोई key नहीं, कोई order नहीं | 3–6 महीने बाद options बीमा का असली test मुमकिन होगा |
| **M3: F6 futures testnet** | **U2 (आपकी keys)** के बाद | 2–3 दिन, O1–O4 की जाँच, एक kill drill, stop को mark price बनाम last price पर परखना | Order, stop और kill switch मशीन की तरह सही चलें |
| **M9: Limit बनाम market order** | **U3 (spot testnet का फैसला)** के बाद | Testnet पर असली fills | खर्च कम। **फायदा ↑** |

### चरण 3: ~31 अक्टूबर से नवंबर

| काम | शर्त | कैसे | फायदा |
|---|---|---|---|
| **S7: असली खर्च पर दोबारा गिनना** | 30 सही-समय वाले cost rounds (U1 पर टिका) | पहले से lock किया नियम | सारी उम्मीदें असली खर्च पर; Round 2 भी उसी खर्च पर |
| **Round 2** (≤ 4 experiments): | Round 1 के नतीजों के बाद | | |
| **E9** funding-gated carry sleeve | | BTC/ETH spot long + perp short, सिर्फ जब 3 दिन की औसत funding किसी सीमा से ऊपर हो; सिर्फ खाली पड़ा USDT | कम-मेल वाली कमाई (F7 से correlation 0.08)। 2025–26 में funding सिर्फ 2–5% थी, इसलिए फायदा छोटा। **विविधता** |
| **E5** hysteresis / धीमा rebalance | | Position तभी बदले जब rank top-8 (या bottom-8) से बाहर जाए | Turnover और खर्च घटे; rebalancing premium से संतुलन। **फायदा ↑** |
| **E7** BTC trend overlay | | BTC के 20/60/120/250 दिन के returns के signs का औसत < 0 हो, तो long book ×0.5; shorts में बदलाव नहीं | धीमी मंदी में long का नुकसान घटे। **नुकसान ↓** |
| **E1b** BTC hedge का आकार shrunk/DCC beta से (E1 पास होने पर) | | Hedge = β̂·notional, जहाँ β̂ = 0.5·rolling-DCC beta + 0.5·1 (shrinkage) | Hedge का सही आकार। **नुकसान ↓** |
| **N2** macro-event gate | | सरकारी FOMC/CPI तारीखों पर नए shorts नहीं (variant A), या gross ×0.5 (variant B); control: random तारीखें; primary metric: सबसे बुरे 5% दिन | घोषणा वाले दिन के झटके से बचाव। **नुकसान ↓** |

### चरण 4: बाद में (Round 3, दिसंबर 2026 से आगे)

| काम | कैसे | फायदा |
|---|---|---|
| **E6** धीरे-धीरे de-risking + vol target | Gross = clip(1 − DD/0.30, 0.4, 1.0) | बड़ी गिरावट में अपने-आप हल्का होना। **नुकसान ↓** |
| **E8** confidence-gated shorts (+ conformal का विचार) | सिर्फ बहुत पक्के bottom-ranks पर short | Short की गुणवत्ता बढ़े। **फायदा ↑** |
| Shorts पर trailing stop | पहले से lock किया gate | **नुकसान ↓** (सबूत कमज़ोर) |
| **Options बीमा / covered-call overlay** | M4 के 3–6 महीने के data के बाद | बड़े crash का बीमा। **नुकसान ↓** |
| **E10** Learning-to-rank (lambdarank) | मौजूदा features पर, वही walk-forward + shuffled control | Ranking की गुणवत्ता। **फायदा ↑** (सबूत सिर्फ equity, खर्च के बिना) |
| Token-unlock filter | पहले भरोसेमंद, मुफ्त ऐतिहासिक data का स्रोत verify हो | Unlock से पहले के दबाव से बचाव |

### चरण 5: फैसले (पहले से lock)

| कब | क्या |
|---|---|
| ~14 जनवरी 2027 | Spot (16B) का 90-दिन का फैसला |
| as-of 12 जनवरी 2027 | Long-short (F4) का 90-दिन का फैसला (D1–D3) |
| ~फरवरी–मार्च 2027 | Round 1 के shadow lines का अपना 90-दिन का फैसला |
| उसके बाद | **छोटी असली रकम** (U4 account + U6 % + आपकी keys और आपका फैसला) |
| असली पैसे के समय | **Position का आकार ½ या ¼ Kelly से**, forward (out-of-sample) Sharpe पर, backtest पर नहीं; BNB से fee (0.10% → 0.075%, U6) |

---

## 4. क्या **नहीं** करेंगे (दोनों reports से, ताकि दोबारा समय न लगे)
- **पहले से fail:** mean reversion, breakout, swing।
- **सबूत कमज़ोर या out-of-sample fail:** pairs, on-chain संकेत, calendar, low-vol (सबूत टकराते हैं), Tether, liquidation-signal।
- **हमारे लिए अनुपयुक्त:** HFT, arbitrage, grid, RL, बड़े neural networks, HRP, 1D पर lead-lag, Almgren–Chriss ($10k पर)।
- **बंद या रोके गए:** leveraged tokens, prediction markets (India में block), COIN-M, perp DEX।
- HMM / regime classifier (out-of-sample सबूत कमज़ोर)। Sentiment का अलग signal नहीं (Fear & Greed पहले से D1 दिमाग में है; S6 रुका)।
- Market timing की छठी कोशिश।
- Leverage।

## 5. कुल अपेक्षित फायदा (ईमानदारी से)
- **सबसे पक्का फायदा, ढाँचे से:** long-short + stop ने backtest में गिरावट 49% → 21% की, और liquidations 69 → 0।
- **अगला सबसे बड़ा lever खर्च है:** S7, E11 और limit orders। खर्च 0.25% से 0.40% होने पर R24 $201k से $62k पर आ गया था।
- **नए तरीके (E1–E4, N1–N3):** ज़्यादातर नुकसान घटाते हैं, कमाई थोड़ी।
- **कोई जादू नहीं:**
  - Backtest की संख्याएँ ऊपरी अनुमान हैं (PBO 65%)।
  - असली उम्मीद forward log से ही तय होगी।

## 6. अभी आपसे चाहिए (बस इतना)

| # | क्या |
|---|---|
| **U1** | Wake timers (आज) |
| **U5** | Round 1 (E3, E1, E2, E4, N1, E11) + N3 + M4 के लिए "हाँ" |
| **U2** | Futures testnet keys (जब सुविधा हो) |
| **U3** | Spot testnet tasks का फैसला |

---

## 7. पूरा मिलान: दोनों reports का हर तरीका roadmap में कहाँ है

### Report 1: `RESEARCH_TRADING_METHODS_BEYOND_SWING`
| तरीका / औज़ार | Roadmap में |
|---|---|
| A. Relative long-short (core) | Core (F7), चरण 0 |
| B. Time-series trend | **E7** (Round 2), सिर्फ long घटाए |
| C. Mean reversion / support पर खरीदना | ❌ "नहीं" सूची |
| D. Breakout | ❌ "नहीं" सूची |
| E. Carry (spot long + perp short) | **E9** (Round 2) |
| F. Pairs / stat-arb | ❌ "नहीं" सूची |
| G. Options (बीमा / covered call) | **M4** data (चरण 2) → options overlay (चरण 4) |
| H. Event-driven: listing | **E3** (Round 1) |
| H. Event-driven: token unlock | चरण 4 (data verify के बाद) |
| I. On-chain | ❌ "नहीं" सूची |
| J. Sentiment | ❌ अलग signal नहीं (Fear & Greed पहले से D1 में) |
| K. Calendar / seasonality | ❌ "नहीं" सूची |
| L. Market making / HFT / arbitrage | ❌ "नहीं" सूची |
| M. Grid | ❌ "नहीं" सूची |
| N. RL | ❌ "नहीं" सूची |
| भाग 3: 1x, बिना leverage | स्थायी नियम 10 |
| भाग 3: Stop + cooldown | Core (F7) |
| भाग 3: Market-neutral ढाँचा | Core |
| भाग 3: कम-मेल वाले कई sleeves | E9, E7, options (भाग 1 की तस्वीर) |
| भाग 3: Inverse-vol + per-coin cap | **E4** (Round 1) |
| भाग 3: धीरे-धीरे de-risking | **E6** (Round 3) |
| भाग 3: Kill switch | F6 (M3) + N3 से उसका आकार |
| भाग 3: Mark-price stop | **M3** (F6 testnet) |
| भाग 3: Exchange / collateral जोखिम | स्थायी नियम 9 |
| भाग 3: Market timing से बचना | "नहीं" सूची |
| भाग 4: खर्च घटाना | **S7**, **E11**, **M9**, BNB fee (चरण 5) |
| भाग 4: Long leg perps पर | **E11** (Round 1) |
| भाग 4: Hysteresis / धीमा rebalance | **E5** (Round 2) |
| भाग 4: Confidence पर भार | **E8** (Round 3) |
| भाग 4: ½ या ¼ Kelly | चरण 5 (असली पैसे के समय) |
| भाग 5: AI ranking | Core |
| भाग 5: Meta-labeling | **E8** |
| भाग 5: Learning-to-rank | **E10** (Round 3) |
| भाग 5: HMM, RL, बड़े NN | ❌ "नहीं" सूची |
| भाग 7: E1, E2, E4 | Round 1 |

### Report 2: `RESEARCH_NEW_METHODS_LOSS_MIN_PROFIT_MAX`
| तरीका | Roadmap में |
|---|---|
| 1.1 Lottery (MAX) effect | **N1** (Round 1) |
| 1.2 Low-volatility anomaly | ❌ "नहीं" (सबूत टकराते हैं) |
| 1.3 BTC → alts lead-lag | ❌ "नहीं" (1D पर नहीं) |
| 1.4 Tether issuance | ❌ "नहीं" |
| 1.5 Macro events (FOMC/CPI) | **N2** (Round 2) |
| 1.6 Liquidation cascade | Signal ❌; सीख → **स्थायी नियम 8** (gap-aware stop, ऊँचा slippage) |
| 2.1 HRP | ❌ "नहीं" |
| 2.2 Rebalancing premium | **E5** में संतुलन |
| 2.3 DCC / shrunk beta hedge | **E1b** (Round 2, E1 पास होने पर) |
| 3.1 EVT tail monitor | **N3** (चरण 2) |
| 3.2 Exit design (trailing stop) | चरण 4 |
| 4.1 Conformal / अनिश्चितता gate | **E8** के साथ (चरण 4) |
| 5.1 Almgren–Chriss | ❌ "नहीं" ($10k पर); limit orders **M9** |

**नतीजा:** दोनों reports का हर तरीका अब roadmap में अपनी जगह पर है: या तो किसी चरण में, या किसी स्थायी नियम में, या कारण सहित "नहीं" सूची में। कुछ भी छूटा नहीं है।

---

## 8. नए तरीकों का पूरा ब्योरा (N1, N2, N3, E1b): सबूत, नियम, शर्त, control, कब, फायदा
स्रोत: `RESEARCH_NEW_METHODS_LOSS_MIN_PROFIT_MAX_16_OCT_2026.md` (उसी report का हर उपयोगी हिस्सा)।

### N1: Lottery (MAX) filter ★ (Round 1, पाँचवाँ test)
**सबूत:**
- Grobys & Junttila (JIFMIM 2021): सबसे कम और सबसे ज़्यादा MAX वाले समूहों के बीच हर हफ्ते 1.5% से ज़्यादा का अंतर। Intraday पर भी पुष्टि।
- **[हमारा]:** 41,824 coin-days (2021–26) में:

  | MAX समूह | सबसे कम | 2 | 3 | 4 | सबसे ज़्यादा |
  |---|---|---|---|---|---|
  | अगले 5 दिन median से आगे | 52.6% | 51.9% | 49.0% | 45.9% | 41.5% |

  यह pattern हर साल 2021–2026 में दिखा।
- **AI score से correlation −0.38**, यानी दिमाग इसका कुछ हिस्सा पहले से पकड़ता है।

**नियम:**
- MAX = पिछले 7 दिनों का सबसे बड़ा एक-दिन का return, जो उस दिन के बंद होने तक पता होता है।
- **Variant A:** उस दिन के top-20% MAX वाले coins long के लिए अयोग्य, अगला rank लिया जाए; short में कोई बदलाव नहीं।
- **Variant B:** A + short में top-MAX वाले coins को प्राथमिकता। Short पर F7 वाला stop ×1.5 रहेगा, क्योंकि यही coins squeeze भी करते हैं।

**Pass की शर्तें (F7 के मुकाबले):** long side का payoff > 1.57 और PF > F7; कुल max DD ≤ 21.4%; 2022 > 0; DSR कुल trials पर।

**Control:** उसी दिन उतने ही coins random तरीके से हटाना (shuffled exclusion)।

**खुलासा (protocol में लिखा जाएगा):** यह pattern 16 अक्टूबर को इसी data पर देखा जा चुका है। इसलिए backtest का पास होना कमज़ोर सबूत है। असली जज F4 shadow के 90 दिन होंगे।

**फायदा:** long book "फूले हुए" coins से बचे, यानी नुकसान ↓। Variant B में short की कमाई ↑ हो सकती है।

### N2: Macro-event gate (Round 2)
**सबूत:**
- FOMC, CPI और NFP पर crypto की volatility, volume और spread उछलते हैं (Fed Board 2026 ⚠ secondary; Volmex)।
- 2022 के बीच से CPI surprise और BTC return में negative संबंध (BlockScholes)।
- **दिशा पर सबूत विवादित है** (NY Fed 2023: लगभग कोई असर नहीं)।

**नियम:**
- Fed (FOMC) और BLS (CPI, NFP) की सरकारी तारीखें, पहले से download करके SHA-lock।
- **Variant A:** घोषणा वाले दिन (UTC) नए shorts नहीं।
- **Variant B:** उस दिन gross ×0.5।

**Pass की शर्तें:**
- Primary: सबसे बुरे 5% दिनों (CVaR) में सुधार। Sharpe primary metric नहीं।
- CAGR ≥ F7 का ~95%।

**Control:** उतनी ही random तारीखें।

**फायदा:** घोषणा वाले दिनों के झटके से बचाव, यानी नुकसान ↓। दिशा का कोई अनुमान नहीं।

### N3: EVT tail-risk monitor (चरण 2, Round 1 के साथ; trading नहीं बदलता)
**सबूत:** Opala, Fischer & Svoboda (2022): BTC/ETH/LTC पर सिर्फ EVT (peaks-over-threshold) 99.9% के backtest में पास हुआ; normal distribution वाले तरीके early-2021 में fail रहे। Gkillas & Katsiampa (*Economics Letters* 2018) भी।

**तरीका:**
- रोज़ F4 के LS_RS और 16B के daily returns पर POT/GPD fit (threshold = 90वाँ percentile)।
- 99% और 99.9% का एक-दिन का tail-loss (VaR/ES) अनुमान F4 के साथ log।

**जाँच (90 दिन बाद):**
- Exceedances गिनना: 99% पर ~1% दिन अनुमान से बुरे होने चाहिए (Kupiec test)।
- फिर kill switch (35%) और per-coin cap को उस अनुमान से मिलाना।

**Trial:** नहीं गिना जाएगा, क्योंकि यह trading नियम नहीं।

**फायदा:** नुकसान की सीमाएँ "अंदाज़े" से नहीं, नापे हुए tail से तय होंगी, यानी नुकसान ↓।

### E1b: BTC hedge का आकार shrunk/DCC beta से (Round 2, सिर्फ अगर E1 पास हो)
**सबूत:**
- BTC futures से BTC का hedge: effectiveness 0.64 (*Frontiers* 2021)। Hedge ratio समय के साथ बदलता है।
- Crypto betas का अनुमान कमज़ोर है (R² ~20%), इसलिए shrinkage ज़रूरी है।
- Alt-coins पर DCC का सीधा सबूत कम है।

**नियम:** BTC hedge notional = β̂ × alt-short notional, जहाँ β̂ = 0.5 × (60-दिन DCC या rolling beta) + 0.5 × 1।

**Pass की शर्तें (E1 के मुकाबले):** short-side के सबसे बुरे दिन बेहतर; DD ≤ E1।

**Control:** तय अनुपात (E1 का ही variant)।

**फायदा:** Hedge न ज़्यादा, न कम, यानी नुकसान ↓।

### उसी report की बाकी सीखें, जो roadmap में ली गईं
- **Liquidation cascade:** gap-aware stop और ऊँचा slippage → स्थायी नियम 8।
- **Rebalancing premium:** E5 में turnover बनाम premium का संतुलन।
- **Trailing stop:** Round 3।
- **Conformal / अनिश्चितता gate:** E8 के साथ।
- **छोड़े गए (कारण report में):** low-vol, 1D पर lead-lag, Tether, HRP, liquidation-signal, Almgren–Chriss।
