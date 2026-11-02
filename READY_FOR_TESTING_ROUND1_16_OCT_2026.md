# ✅ Testing के लिए तैयार: Round 1 + N3 + M4 + M10 का integration (16 अक्टूबर 2026)

Roadmap (`FINAL_ROADMAP_METHODS_16_OCT_2026.md`) के **मेरे हिस्से के सारे काम** code में जोड़ दिए गए हैं और ground-level पर जाँचे गए हैं।
- **आपके हिस्से के काम छुए नहीं गए:** F6 testnet (keys), limit orders (spot testnet का फैसला), wake timers, account।
- **कोई experiment का नतीजा अभी नहीं देखा गया।** Testing आपके कहने पर होगी।

---

## 1. क्या-क्या बना (एक-एक करके)

| # | काम | Files | सबूत |
|---|---|---|---|
| 1 | **Round 1 protocol** (E3, E1, E2, E4, N1, E11): नियम, gates, controls, trials (N = 91) | `logs/research_r1/R1_PROTOCOL_PREREGISTERED.md` | **SHA lock af95f224…, 2026-10-16 08:36 UTC**, किसी भी run से पहले |
| 2 | **नया engine**: F7 engine की copy + hooks (BTC hedge, short order/filter, long block, weights, perp longs, short-side रोज़ का P&L)। `f7_risk.py` नहीं छुआ, क्योंकि F4 उसी पर चलता है। | `src/pipeline_1d/r1_engine.py` | **G0 PASS:** hooks बंद → F7 के RS / OFF_LO / OFF_LS के सभी 9 sleeves $0.01 तक हूबहू (`G0.json`) |
| 3 | **Synthetic unit tests** (हाथ से गिने आँकड़ों पर, बिना असली data) | `src/audits/test_r1_engine_synthetic.py` | **T0–T7 सब PASS** (`synthetic_tests_stdout.txt`) |
| 4 | **Runner**: सारे experiments + 10-seed controls + gates + हर फैसले का record | `src/pipeline_1d/r1_run.py` | **Feature check PASS:** MAX7, σ60 (60 coin-days), funding-9, perp age, quote volume (210 coin-dates), सब plain loops से (`check_stdout.txt`)। **Pipeline PASS:** `run()` ने F7 baseline हूबहू दोबारा बनाया (`baseline_pipeline_check.txt`) |
| 5 | **R1 verifier** (स्वतंत्र) | `src/audits/verify_r1_claims.py` | V2 हिस्सा F7 baseline पर पहले ही PASS। V1/V3 असली runs के बाद चलेंगे |
| 6 | **N3 EVT monitor** | `src/execution/n3_evt_monitor.py` + protocol (lock c43f93c8…) | **Synthetic validation PASS:** Student-t पर VaR99 2.1%, VaR99.9 1.1%, ES99 1.3% के अंदर; ES सूत्र = numerical integration। **पहला असली run + verifier V1–V3 PASS** (अलग optimizer से 1% के अंदर) |
| 7 | **M4 options/IV/basis collector** (public, बिना key) | `src/execution/m4_options_collector.py` + protocol | **पहला run: 14/14 endpoints OK**; verifier V1–V3 PASS (3 options live दोबारा मिलाए) |
| 8 | **M10 रोज़ का status + local backup** | `src/execution/m10_daily_status.py` | **पहला run:** आज सुबह की असली दिक्कतें (16B/F4 late) **खुद पकड़ीं**; 33 files का backup, हर copy का SHA मिलाया |
| 9 | **Scheduled tasks** (wake-to-run) | Windows Task Scheduler | M4 05:40/06:10, N3 09:30/10:00, M10 10:15 IST, कल (17 अक्टूबर) से |

**Lock के बाद के सारे स्पष्टीकरण और सुधार** (कोई run होने से पहले): `logs/research_r1/CODE_CHANGES_AFTER_LOCK.md`। मुख्य बातें:
- E1b का control लागू नहीं होता (w = 1 पर alt shorts ही नहीं)।
- σ न मिले तो उस दिन का median σ।
- 1x long व्यवहार में liquidate नहीं होता (गणित से साबित)।
- Verifier में एक rubber-stamp (`or True`) पकड़कर हटाया।

---

## 2. इस काम में पकड़ी गई और सुधारी गई गलतियाँ (ईमानदारी से)
1. **मेरे synthetic tests की गलत अपेक्षाएँ:**
   - Cash की सीमा (F7 जैसा व्यवहार), जिसे engine का bug समझ लिया था।
   - 1x long का liquidation, जो गणित से संभव ही नहीं।
   - दोनों में engine सही निकला, tests सुधारे।
2. **Runner:**
   - Funding का औसत engine की price-filtered table से लिया जा रहा था, अब raw files से।
   - G0 का JSON लिखते समय crash हुआ।
3. **Verifier:** `or True` वाला rubber-stamp हटाया।
4. **पुरानी report में गलत आँकड़ा:** Deribit DVOL "~45–48" लिखा था, जो अक्टूबर 2025 के timestamp से आया था। आज का असली मान 36.9 है। Report ठीक कर दी।

---

## 3. Testing कैसे होगी (आपकी "हाँ" पर, इसी क्रम में, एक-एक करके)
हर experiment का run और फिर verifier:

| क्रम | Command | समय (अनुमान) |
|---|---|---|
| 1 | `python src/pipeline_1d/r1_run.py E3` → `python src/audits/verify_r1_claims.py E3` | ~2 घंटे (21 runs) |
| 2 | `... r1_run.py E1` → `verify_r1_claims.py E1` | ~2 घंटे |
| 3 | `... r1_run.py E2` → `verify ... E2` | ~2 घंटे |
| 4 | `... r1_run.py E4` → `verify ... E4` | ~2 घंटे |
| 5 | `... r1_run.py N1` → `verify ... N1` | ~4 घंटे |
| 6 | `... r1_run.py E11` → `verify ... E11` | ~20 मिनट |

- हर नतीजे का Hindi report।
- PASS वाले variants F4 में shadow line बनेंगे, आपकी हाँ पर।

**ध्यान:**
- पहली बार असली runs में runner या verifier का कोई अनदेखा bug निकल सकता है। वह ठीक करके दर्ज किया जाएगा, और नियम कभी नहीं बदलेंगे।
- N1 का pattern पहले देखा जा चुका है, यह protocol में दर्ज है।

---

## 4. आपके हिस्से (बाकी)
| # | काम |
|---|---|
| U1 | Wake timers चालू करें (आज सुबह इसी से दिन late हुआ; M10 ने खुद पकड़ा) |
| U2 | Futures testnet keys (F6) |
| U3 | Spot testnet के बंद tasks का फैसला (limit-order test के लिए) |

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
