# एक single 10,000 USDT ecosystem: क्या बना, क्या verify हुआ, आगे की test योजना (22 अक्टूबर 2026)

**आपका आदेश (21-10-2026):**
- एक ही ecosystem, 10,000 USDT budget पर।
- Binance का एक ही account, अंदर से हिसाब (internal management)।
- 90 दिन का इंतज़ार नहीं।
- तरीका मैं तय करूँ, पर उसी discipline में।

**सबूत:**

| चीज़ | जगह |
|---|---|
| Protocol | `logs/eco/ECO_PROTOCOL_PREREGISTERED.md` (SHA `15a3c837…`, lock करके) |
| Registry | `logs/eco/trial_registry_eco.csv` |
| Verifier output | `logs/eco/verify_eco_stdout.txt` |
| Results | `logs/eco/E3_E4_RESULTS.md` |
| Deploy log | `logs/R2_CLOUD_DEPLOY_LOG_19_OCT_2026.md` का ECO हिस्सा |

---

## 1. अब ढाँचा कैसा है (एक जगह, एक clock, एक हिसाब)

```
 Producers (code नहीं बदला, सिर्फ़ पढ़े जाते हैं)          ECO (नया, VM पर हर घंटे :50 IST)
 ┌───────────────────────────────┐                  ┌──────────────────────────────────────────────────┐
 │ 1D AI system: Step16 → 16B → F4│── orders JSON ──►│ 1. Lock (दो run एक साथ नहीं)                     │
 │   (D1, H4, H1 brains; LS_RS)   │   + ledger hash  │ 2. Producers verify: hash chain, SHA, staleness  │
 │ PAPER-N1: 4 नियम-sleeves       │── state+ledger ─►│ 3. Weights: 1D vs N1 (inverse-vol, हर महीने)     │
 │   (4h, 8h, 12h, 1D)            │                  │ 4. हर coin का एक net target (सब sleeves का जोड़)  │
 └───────────────────────────────┘                  │ 5. 1D shorts के stops (हर घंटे जाँच)              │
                                                    │ 6. Caps: coin 20%, कुल 1.5×; kill switch 30% DD   │
                                                    │ 7. Reconcile: exchange == हमारा book?             │
                                                    │ 8. Orders: सिर्फ़ फ़र्क (netting), band 0.25%      │
                                                    │ 9. Attribution: हर fill किस brain का               │
                                                    │10. Hash-chained ledger + रोज़ verifier            │
                                                    └──────────────────────────────────────────────────┘
```

- **एक account, अंदर से हिसाब:** हर coin पर exchange के पास एक ही net position रहती है। अंदर हर sleeve (D1, H4, H1, N1 के A/B/C/D) का अपना हिस्सा, fee और funding अलग दर्ज होते हैं।
  - Replay में sleeves का जोड़ account के बराबर निकला, अंतर 8×10⁻¹⁰ USDT।
- **Internal transfer:** अगर एक brain BTC बेचे और दूसरा उतना ही ख़रीदे, तो exchange पर कोई order नहीं जाता। हिसाब अंदर ही बदल जाता है, और fee बचती है।
- **Capital:** 10,000 USDT। हर महीने की शुरुआत में बँटवारा होता है।
  - **अक्टूबर 2026:** 1D system 53.9%, N1 46.1%।
  - यह नियम (ECO-W2, inverse-vol) pre-registered test से चुना गया है।
- **Mainnet का कोई रास्ता code में नहीं है।** Orders सिर्फ़ `demo-fapi.binance.com` पर जा सकते हैं, और वह भी तभी जब config में `demo_enabled` हो, जो आपकी हाँ के बाद ही होगा।

## 2. क्यों मिलाना फ़ायदेमंद निकला (E-2, backtest, pre-registered)

| 2021-01 … 2025-09 (dev) | CAGR | Max DD | Calmar |
|---|---|---|---|
| सिर्फ़ N1 | 74.6% | 22.2% | 3.36 |
| सिर्फ़ 1D (LS_RS) | 53.7% | 21.4% | 2.51 |
| **मिलाकर, ECO-W2 (चुना गया)** | **65.9%** | **11.0%** | **5.98** |
| मिलाकर, ECO-W1 (50/50) | 64.9% | 11.6% | 5.57 |

| P3 (2025-10 … 2026-09, सिर्फ़ report) | Return | Max DD |
|---|---|---|
| सिर्फ़ N1 | −12.5% | 31.3% |
| सिर्फ़ 1D | +15.0% | 12.3% |
| **मिलाकर (W2)** | **≈ 0%** (−0.3%) | **18.8%** |

**मिलाने का असली फ़ायदा: DD आधा हुआ।** दोनों systems की daily correlation सिर्फ़ 0.05 है (monthly 0.08)।
- **पहले के आँकड़े पर सुधार:** पहले लिखा "0.63" अलग series से था: N1 बनाम 1D की spot long-only D1 sleeve। जो system सच में मिलाया जा रहा है (LS_RS), उसके साथ correlation 0.05 है।
- **Gates:** चारों gates पास हुए।
  - DSR 1.00 (N = 27);
  - P1 और P2 दोनों में Calmar > 0।
- **Independent verifier:** V1, V2, V5 PASS। N1 FINAL का दोबारा बनाया curve N6 के claims से 1e-16 तक मिला।

**सावधानी:**
- दोनों systems उसी 2021–26 data को देखकर बने थे।
- P3 में मिलाकर भी लगभग 0 रहा।
- Backtest की ये संख्याएँ भविष्य का वादा नहीं हैं।

## 3. Replay (E-3): सितंबर 2026, 719 hourly cycles, simulated fills

| Gate | नतीजा |
|---|---|
| Targets independent code से (200 cycles) | ✅ 0 mismatch |
| Sleeve-हिसाब = account (R1) | ✅ 8×10⁻¹⁰ USDT |
| Caps (R3), order minimums (R5) | ✅ 0 violation |
| F4 के 9 stops (R4) | ✅ 9/9 उसी bar में या पहले बंद |
| दो replays हूबहू (R6) | ✅ एक ही hash |
| **Tracking ≤ 1% (R2)** | **❌ 1.20%** |

**R2 FAIL की जाँच (post-hoc, ईमानदारी से):**
- **N1 हिस्सा:** paper से फ़र्क सिर्फ़ 1.07 USDT (0.01%)।
- **1D हिस्सा:** 125 USDT का फ़र्क। इसकी वजहें:
  - ~20.5: F4 paper की ऊँची fee मान्यता (spot 0.25%);
  - ~20.4: stop slippage 1%;
  - **~85: execution timing।** Executor paper से ~3 घंटे बाद भरता है, और stop अगले घंटे के open पर।
- इस महीने यह फ़र्क फ़ायदे में गया, दूसरे महीने नुकसान में भी जा सकता है।
- Gate नहीं बदला गया। FAIL दर्ज है।

## 4. Failure tests (E-4): 17/17 PASS

- Crash के बाद recovery, दोहरा order नहीं।
- Lock: दो run एक साथ नहीं चल सकते।
- पुराना (stale) या छेड़ा हुआ producer → freeze।
- एक symbol पर error → बाकी चलते रहते हैं।
- हाथ से बदली position → सिर्फ़ वह symbol freeze।
- Kill switch → सब बंद, और फिर कुछ नहीं भेजता।
- **असली demo endpoints पर finding:** demo के filters mainnet से अलग हैं (जैसे LINK/LTC का minimum 5 बनाम 20)। Demo mode demo के filters ही लेता है।

## 5. VM पर अभी (E-5, plan mode: कोई order नहीं)

- **Files:** VM पर 7/7 SHA मिले।
- **पहला manual cycle:** दोनों producers verify होकर load हुए। 25 symbols पर target, 20 paper fills, 5 band के अंदर। Verifier 7/7।
- **Crontab:** सिर्फ़ 3 lines जुड़ीं (ECO_Plan हर घंटे :50 IST, ECO_Verify रोज़ 07:25 IST)। कुल 21 jobs, SHA मिलान ✅।
- **1D system, F6 और PaperN1 वैसे ही चल रहे हैं।**

## 6. आगे की test योजना

| चरण | क्या | Pass की शर्त | कौन तय करेगा |
|---|---|---|---|
| **E-5** (चल रहा) | Plan mode ≥ 3 दिन (≥ 72 cycles) | रोज़ `verify_eco_live` 7/7; ≤ 2 failed cycles/दिन; reconcile mismatch 0; producers freeze सिर्फ़ असली staleness पर | अपने-आप, मैं जाँचूँगा |
| **R2 फ़ैसला** | Tracking का नियम | (a) per-strategy पढ़ाई मानें, या (b) forward data पर नया pre-registered tracking test (E-5 का data इसी काम आएगा) | **आप** |
| **E-6** | Demo cut-over (असली demo orders) | F6 cron बंद → F6 के 7 shorts और उनके exchange stop orders ECO अपनाए → पहला cycle reconcile 0 → हर घंटे verifier | **आपकी हाँ** |
| **E-6 के बाद** | Demo पर ≥ 2–4 हफ़्ते | Slippage/fill, tracking बनाम plan, stops, kill switch drill | मैं report करूँगा |
| **Real money** | 10,000 USDT असली account | नया protocol, spot execution, mainnet keys सिर्फ़ आप डालेंगे | **सिर्फ़ आप** |

**E-6 से पहले दो बातें बाकी हैं, और ये भी करनी होंगी:**
1. **F6 की positions अपनाने का एक छोटा tool।** इसमें F6 के exchange STOP orders रद्द करना भी शामिल है, नहीं तो वे ECO की net position का हिस्सा बंद कर सकते हैं।
2. **Demo wallet ~5,000 USDT है, जबकि budget 10,000 का है।** इसलिए k ≈ 0.5 होगा: orders आधे आकार के जाएँगे, और हिसाब 10,000 के पैमाने पर रिपोर्ट होगा। Binance demo में balance बढ़ाना आपके हाथ में है (अगर वह सुविधा हो)।

## 7. ईमानदारी से: क्या अभी नहीं है
- **Exchange पर stop orders:** अभी stops सिर्फ़ हर घंटे की जाँच से चलते हैं। VM बंद हुआ तो उस दौरान कोई stop नहीं।
- **Spot execution:** demo phase में सब कुछ perp पर है। N1 के spot legs और 1D longs भी perp पर। यह फ़र्क ledger में दर्ज होता है।
- **5m से 1M तक के सारे timeframes:** ecosystem में अभी 4h–1D ही हैं। छोटे या बड़े timeframes का कोई सिद्ध edge नहीं मिला।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## भाग 2 (22 अक्टूबर 2026, रात): योजना (PLAN_CONTINUOUS_BRAIN) का ecosystem में integration

**Amendment:** `logs/eco/ECO_AMENDMENT_1_PREREGISTERED.md` (SHA `0a448a79…`), कोई नतीजा निकालने से पहले lock किया गया।

| काम | नतीजा | सबूत |
|---|---|---|
| **ECO-T4 profit lock** (+3 ATR के बाद break-even), trial 3/4 | ❌ **FAIL, नहीं अपनाया।** N1 dev Calmar 4.16 → 3.62, P1 5.10 → 4.47, P2 3.22 → 2.94; मिलाकर 5.98 → 5.96 | Verifier V6: 200 trades raw 5m से, 0 mismatch |
| **Outage guard** (VM बंद होने पर सुरक्षा) | D = 50% चुना गया। ऐसे bars का हिस्सा 4.2e-5 है | V7 ने गिनती दोबारा की ✅ |
| **Flash crash की सीख** | 10-10-2025 को कई coins पर एक घंटे में 50–62% के wicks दिखे। इसलिए guard Binance के **mark price** पर लगेगा, last price पर नहीं | CODE_NOTES 2 (post-check फ़ैसला, दर्ज) |
| **1D shorts के exchange stops** | Entry × 1.5 पर, तभी लगेगा जब net position short हो। नहीं तो हर घंटे का virtual check | Mock tests S1–S6 ✅ |
| **Cut-over tool** (F6 के shorts अपनाना) | बन गया। सिर्फ़ जाँच वाला mode भी है | Mock tests X1–X2 ✅ |
| **Tracking test (TC)** | Demo बनाम shadow plan, 14 दिन: रोज़ ≤ 0.30%, कुल ≤ 1.0% | Amendment §5 |
| **Laptop पर सब tests** | `test_eco_core` 25/25। Verifier 8/9 (R2 वाला पुराना, दर्ज FAIL) | `logs/eco/verify_eco_stdout_A1.txt` |
| **Cloud पर deploy** (अब भी plan mode, कोई order नहीं) | 11/11 SHA, पुरानी files का backup, manual cycle ठीक, `verify_eco_live` 7/7। 35 would-be stops गिने गए | Deploy log |

**अब जो बाकी है, और किसके हाथ में:**
1. Plan mode के ≥ 72 cycles और लगातार 3 दिन verifier 7/7। यह अपने-आप होगा (~25 अक्टूबर)।
2. उसके बाद **आपकी हाँ** से demo cut-over: F6 cron बंद होगा, उसके shorts अपनाए जाएँगे, और demo orders शुरू होंगे।
3. Cut-over के 14 दिन बाद TC tracking test।
