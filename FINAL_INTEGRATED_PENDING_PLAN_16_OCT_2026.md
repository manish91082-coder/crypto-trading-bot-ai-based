# अंतिम एकीकृत योजना: क्या हो चुका, क्या बाकी है, step by step (16 अक्टूबर 2026, 12:30 IST)

---

## A. कल और आज क्या पूरा हुआ (सब verify किया हुआ)

| काम | नतीजा |
|---|---|
| S1 overfit audit | PBO 65%, DSR < 0.95 |
| F1 futures data + F2 long-short | PASS: $110k, सबसे बड़ी गिरावट 30% |
| S2 (मंदी वाला data) और S3 (futures features) | सब FAIL; दिमाग पहले जैसे ही रहे |
| **F7 risk नियम** (stop ×1.5, 30-दिन cooldown) | **PASS: $88.4k, गिरावट 21.4%, 0 liquidation** |
| **F4 long-short paper log** | बना, test PASS, रोज़ का task चालू |
| **F6 futures testnet executor** | Code तैयार; plan mode चला; order अभी नहीं |
| **पूरा audit** (training, data, code) | कोई look-ahead या hard-coding नहीं; 13 verifiers PASS |
| Audit के सुधार | F4/F6 का `.asof` bug, F6 stop-sync, 16B log, scale-gate जाँच |
| Performance summary | Spot: win rate 47%, RR 1.57; LS: win rate 52%, RR 1.10 |
| Research | Long-short mix (E1–E10); बाकी instruments (options/quarterly ही उपयोगी) |

## B. आज सुबह क्या गड़बड़ हुई और क्या ठीक किया
- **गड़बड़:** PC 10:20 IST तक sleep में था।
  - सारे tasks एक साथ चले।
  - 16B और F4 fail हुए, और cost study का round गलत समय पर हुआ।
- **ठीक किया:**
  1. 16B और F4 हाथ से चलाए। as-of 15 अक्टूबर दर्ज हुआ, पर **LATE (on_time=False)**। यह on-time forward सबूत में नहीं गिना जाएगा।
  2. F4 verifier पहले असली दिन पर **V1–V5 PASS**।
  3. Code: 16B अब देर से चलने पर भी सही चलता है, क्योंकि सारा data as-of पर कटता है।
  4. 16B अब Step 16 के लिए, और F4 अब 16B के लिए, 90 मिनट तक इंतज़ार करते हैं।
  5. सब बदलाव `CODE_CHANGES_AFTER_LOCK.md` में दर्ज हैं।
- **पर असली इलाज आपके हाथ में है** (नीचे U1)। अगर PC 05:00–09:30 IST के बीच sleep में रहा, तो cost study के rounds और on-time दिन खोते रहेंगे।

---

## C. बाकी काम: क्रम से

### आपके काम (ये न हों तो आगे रुकेगा)

| # | काम | क्यों ज़रूरी | कब तक |
|---|---|---|---|
| **U1** | **Windows "Allow wake timers" को "Enable" करें** (अभी "Important only" है), या PC को 05:00–09:30 IST चालू रखें | आज इसी से पूरा दिन late हुआ। Cost study (S7) और 90-दिन का forward log इसी पर टिके हैं। | **आज ही** |
| **U2** | Futures testnet account (testnet.binancefuture.com) और API key बनाएँ। Keys अपने PC के environment में डालें: `BINANCE_FUT_TESTNET_KEY` / `_SECRET`। One-way mode रखें। | F6 का testnet operations test | जब चाहें |
| **U3** | Spot testnet के tasks (`CryptoBot1D_Testnet_Swing`, `HealthCheck`) **13 अक्टूबर से Disabled** हैं। इन्हें फिर चालू करना है या नहीं, बताएँ। मैंने इन्हें नहीं छुआ। ETH position वैसी ही है। | पुराने testnet bot की स्थिति साफ करनी है | जब चाहें |
| **U4** | Binance का असली account, KYC, और futures की उपलब्धता (F5) | असली पैसे से पहले | जनवरी 2027 के फैसले से पहले |
| **U5** | E1–E4 experiments और options-data collector पर "हाँ" या "ना" | अगला research | जब चाहें |
| **U6** | (क) कितना % पैसा लगाना है: पहले से तय नियम की सिफारिश 50% (Step 27)। (ख) असली account में BNB से fee भरना है या नहीं (0.10% → 0.075%, Binance का official fee page) | असली पैसे की तैयारी | जनवरी 2027 से पहले |

### मेरे काम (क्रम से)

| # | काम | शर्त | अनुमानित समय |
|---|---|---|---|
| **M1** | **रोज़ की जाँच:** 16B और F4 ledger, `verify_f4_forward.py`, on_time, C1। Fail हो तो कारण ढूँढकर ठीक करना। | हर session में | रोज़ |
| **M2** | **E1–E4** (long-short mix सुधार), हर एक पर protocol + SHA lock + verifier। Trial budget: ≤ 2 variants हर experiment। | U5 "हाँ" | 2–3 दिन |
|  | E1: BTC hedge वाला short book | | |
|  | E2: alt shorts पर filters (funding, listing-age, liquidity) | | |
|  | E3: short की कमाई AI से या सिर्फ नए listed coins के गिरने से (diagnostic) | | |
|  | E4: volatility के हिसाब से position size + per-coin cap | | |
| **M3** | **F6 testnet operations test:** 2–3 दिन, O1–O4, और एक kill drill | U2 keys | 3 दिन |
| **M4** | Options/quarterly data collector: public API, रोज़, बिना key और बिना order | U5 "हाँ" | 1 दिन बनाना, फिर 3–6 महीने data |
| **M5** | **S7:** असली खर्च पर research दोबारा गिनना (≥ 30 सही-समय rounds के बाद) | U1, ताकि rounds 00:00 UTC पर हों | **सबसे जल्दी ~31 अक्टूबर**; PC sleep में रहा तो आगे खिसकेगा |
| **M6** | E1–E4 में जो variant पास हो, उसे F4 में shadow line की तरह जोड़ना | M2 PASS | — |
| **M8** | **E11 (नया, कल के F2 plan का design (b), कभी test नहीं हुआ):** long book भी USDT-M perps पर (spot 0.25% की जगह perp fee + long को funding चुकानी) | U5 "हाँ", E1–E4 के साथ trial budget में | 1 दिन |
| **M9** | **Limit बनाम market order का असली खर्च** (execution timing; कल की scanner research का Option 3)। Spot testnet पर नापना होगा | U3 (spot testnet tasks का फैसला); ETH position नहीं छूनी | 2–3 दिन |
| **M10** | **रोज़ का alert/सार** (16B + F4 + cost: चला या नहीं, on_time, C1) और logs का **local backup** (GitHub नहीं) | — | आधा दिन |
| **M11** | Dashboard (`dashboard/index.html`, बना हुआ) को रोज़ अपडेट करना + "probability map" (सिर्फ जानकारी, हर अनुमान forward log में) | वैकल्पिक, कम प्राथमिकता | 1 दिन |
| **M7** | Memory और reports को अद्यतन रखना | लगातार | — |

**रोके गए (अभी नहीं):**
- S4/S5: DSR और गिरते, फायदा छोटा।
- S6 (attention data)।
- Tax (आपके निर्देश से)।
- 2017–19 का futures data: मौजूद ही नहीं।
- और नए features: S2/S3 FAIL।
- RL, pairs, arbitrage, grid, perp DEX, prediction markets: research के अनुसार अनुपयुक्त।

---

## D. फैसले की तारीखें (पहले से lock)

| System | 90वाँ as-of दिन | फैसले की शर्तें |
|---|---|---|
| Spot (16B paper) | as-of 12 जनवरी 2027 (~14 जनवरी को आकलन) | 16B protocol के अनुसार |
| Long-short (F4 paper) | as-of 12 जनवरी 2027 | D1: ≥ 85/90 दिन on-time + C1; D2: गिरावट ≤ 30%; D3: backtest के 5वें percentile से ऊपर |

⚠️ **आज का दिन (as-of 15 अक्टूबर) late है।** 90 में से 85 on-time दिन चाहिए, यानी अब सिर्फ 4 और दिन खो सकते हैं। U1 सबसे ज़रूरी है।

**असली पैसा:** सिर्फ इन फैसलों के बाद, छोटी रकम से, आपकी keys और आपके फैसले से। मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## E. रोज़ की स्वचालित दिनचर्या (IST)

| समय | Task | काम |
|---|---|---|
| 05:28, 05:32 | CryptoBot_Step2_CostSnapshot | Order book की गहराई (cost study) |
| 05:50 | CryptoBot1D_ForwardDryRun | Step 16: data update + D1 scores |
| 07:30, 08:00 | CryptoBot16B_ForwardMulti | R6/R24 scores + spot paper |
| 08:30, 09:00 | CryptoBot_F4_LSPaper | Long-short paper |

PC इस पूरे समय (05:00–09:30) जागा रहना चाहिए।

---

## F. कल + आज: हर item का पूरा मिलान (कुछ भी छूटा नहीं)

**स्रोत:**
- कल: `MASTER_PLAN_STEP_BY_STEP`, `RESEARCH_1D_WHAT_REMAINS`, `FINAL_PLAN_1D_SPOT_AND_FUTURES`, `RESEARCH_FUTURES_LONGSHORT_PRIORITY`, `RESEARCH_OPPORTUNITY_SCANNER`, `INTEGRATED_CONCLUSION`, `RESEARCH_1D_WINDUP`
- आज: `AUDIT_FULL`, `PERFORMANCE_SUMMARY`, `RESEARCH_LONG_SHORT_MIX`, `RESEARCH_CRYPTO_OTHER_INSTRUMENTS`

| Item | कहाँ से | स्थिति |
|---|---|---|
| Step 0a: wake timers | Master plan | ⏳ **U1 (आप)** |
| Step 0b: forward logger की हाँ | Master plan | ✅ हो गया (16B चालू) |
| Step 0c: कितना % पैसा | Master plan | ⏳ **U6 (आप)**; सिफारिश 50% |
| Step 1: forward logger (16B) | Master plan | ✅ चालू; as-of 15 अक्टूबर late |
| Step 2: असली खर्च का नाप | Master plan / G | ⏳ चालू → **M5 (S7)** |
| Step 3: Step 28 (हलचल से size) | Master plan | ✅ किया: FAIL |
| Step 4: Phase 2 Swing AI | Master plan | ✅ किया: FAIL |
| Step 5: Step 29 (S/R + volume features) | Master plan | ✅ किया: SKILL_ADD_ONLY, अपनाया नहीं |
| Step 6: Step 30 (breakout + दौर) | Master plan | ✅ किया: FAIL |
| Step 7: Step 31 (हफ्ते वाला दिमाग) | Master plan | ✅ Step 15 के R5/R10 में पहले ही परखा (0.545/0.541)। "लंबा hold" वाला रूप **E5** में |
| Step 8: Dashboard | Master plan / scanner Opt. 4 | 🟡 बना, scheduled नहीं → **M11** (वैकल्पिक) |
| Step 9 / F8: असली पैसा | Master / Final plan | ⏳ जनवरी 2027 के फैसले के बाद, आपका |
| A / S1: overfitting का हिसाब | What-remains / Final | ✅ PBO 65%, DSR < 0.95 |
| B / S2: 2017–19 data training में | What-remains / Final | ✅ किया: FAIL |
| C / S3: futures features | What-remains / Final | ✅ किया: FAIL |
| D / S4: "बड़ा winner" label | What-remains / Final | ⏸ रोका गया (DSR, छोटा फायदा) |
| E / S5: scores जोड़ना | What-remains / Final | ⏸ रोका गया; shorts के लिए rank-ensemble **E8** में |
| F / S6: attention data | What-remains / Final | ⏸ रोका गया |
| G: खर्च घटाना | What-remains | ⏳ S7 (**M5**) + limit orders (**M9**) + BNB fee (**U6**) |
| H: खाली 50% पैसा | What-remains | ✖ earn/निवेश, आपके निर्देश से बाहर। Trading वाला रूप (carry sleeve) **E9** |
| F1: futures data | Final plan | ✅ हो गया |
| F2 (a): spot long + perp short | Final plan | ✅ PASS |
| **F2 (b): दोनों तरफ perps** | Final plan | ⏳ **कभी test नहीं हुआ → M8 (E11)** |
| F3: बेहतर दिमागों से long-short | Final plan | ✖ शर्त पूरी नहीं हुई (S2/S3 FAIL) |
| F4: long-short paper log | Final plan | ✅ चालू; as-of 15 अक्टूबर late, C1 True, verifier PASS |
| F5: futures account | Final plan | ⏳ **U4 (आप)** |
| F6: testnet code | Final plan | 🟡 code + plan mode हो गए; test → **M3** (U2 keys पर) |
| F7: risk नियम | Final plan | ✅ PASS |
| Scanner Opt. 1: volatility से size | Scanner | ✅ Step 28 FAIL; पर inverse-vol sizing का **E4** अलग रूप है (हर leg के अंदर weight) |
| Scanner Opt. 2: weekly | Scanner | ✅ Step 15 / **E5** |
| Scanner Opt. 3: execution timing | Scanner | ⏳ **M9** |
| Scanner Opt. 5: futures risk alarm | Scanner | ⏸ वैकल्पिक, सबूत नहीं |
| Scanner Opt. 6: 5m–1h directional trading | Scanner | ✖ नहीं (सबूत) |
| Wind-up: tax (T1/T2, tax ledger) | Wind-up | ⏸ आपके निर्देश से रोका |
| Wind-up: 2–3 दिन का operations test | Wind-up | ⏳ **M3** |
| Wind-up: alert, reconciliation, backup | Wind-up | ⏳ **M10** (reconciliation F6 में पहले से है) |
| Audit: look-ahead, hard-coding, verifiers | आज | ✅ PASS |
| Audit के सुधार | आज | ✅ हो गए (F4/F6 asof, F6 stop-sync, 16B log, late-run, इंतज़ार) |
| Performance summary (win rate, RR, महीने) | आज | ✅ सिर्फ जानकारी |
| Long-short mix research: E1–E4 | आज | ⏳ **M2** (U5 हाँ पर) |
| Long-short mix research: E5–E10 | आज | ⏸ अगला round (trial budget) |
| Mark-price stop (testnet पर MARK बनाम CONTRACT) | आज (mix research) | ⏳ **M3** के साथ |
| Gap-aware stop fill का backtest | आज (mix research) | ⏳ **E1–E4** के protocol में शामिल होगा |
| Options / quarterly data collector | आज (instruments research) | ⏳ **M4** (U5 हाँ पर) |
| Quarterly futures से funding के बिना BTC hedge | आज (instruments research) | ⏳ **E1** का एक variant (budget में) |
| Spot margin short | आज (instruments research) | ⏸ सिर्फ backup, ज़रूरत पड़ने पर |
| TradFi perps | आज (instruments research) | ⏸ बाद में |
| COIN-M, arbitrage, grid, leveraged tokens, perp DEX, prediction markets | आज (instruments research) | ✖ नहीं (सबूत / कानूनी / बंद) |
| Spot testnet tasks (Disabled 13 अक्टूबर से) | आज मिला | ⏳ **U3 (आप)** |

**Legend:**
- ✅ हो गया
- ⏳ बाकी (किसका काम, ऊपर लिखा है)
- 🟡 आधा
- ⏸ रोका गया
- ✖ नहीं करना (कारण सहित)

## G. अंतिम क्रम: एक नज़र में

| क्रम | काम |
|---|---|
| 1 | **U1 wake timers** (आज) |
| 2 | **M1** रोज़ की जाँच |
| 3 | **M10** रोज़ का alert + backup |
| 4 | **U5 हाँ →** M2 (E1–E4 + E11) |
| 5 | **U2 keys →** M3 (F6 testnet + mark-price stop) |
| 6 | **U3 →** M9 (limit orders) |
| 7 | ~31 अक्टूबर: **M5 (S7)** |
| 8 | **M4** options-data collector (हाँ पर) |
| 9 | पास हुए variants: **M6** (F4 में shadow) |
| 10 | **M11** dashboard (वैकल्पिक) |
| 11 | **जनवरी 2027:** फैसले → **U4/U6 →** छोटी असली रकम (आपका फैसला) |

---

## H. अपडेट (16 अक्टूबर, शाम): नए तरीकों का roadmap
- दोनों नई research (`RESEARCH_TRADING_METHODS_BEYOND_SWING`, `RESEARCH_NEW_METHODS_LOSS_MIN_PROFIT_MAX`) का कब, कैसे और क्या फायदा: **`FINAL_ROADMAP_METHODS_16_OCT_2026.md`**।
- **Round 1 अब:** E3 → E1 → E2 → E4 → N1 (lottery/MAX filter) → E11।
- **साथ-साथ:** N3 (EVT tail monitor), M10, M4, M3, M9।
- **Round 2 (~नवंबर, S7 के बाद):** E9, E5, E7, N2 (macro gate)।
- **Round 3:** E6, E8, trailing stop, options overlay, token-unlock filter।

---

## I. अपडेट (16 अक्टूबर, शाम): मेरे हिस्से का integration पूरा → **READY FOR TESTING**
- **Round 1 (E3, E1, E2, E4, N1, E11):** protocol lock, engine (G0 PASS), synthetic tests T0–T7 PASS, runner (feature check + pipeline PASS), verifier।
- **N3 EVT monitor, M4 options collector, M10 status/backup:** बने, पहला run हुआ, verifiers PASS, रोज़ के tasks बने।
- **विवरण:** `READY_FOR_TESTING_ROUND1_16_OCT_2026.md`।
