# Testing पूरी: Round 1 (6 experiments) + पूरे system का End-to-End integration (16 अक्टूबर 2026)

- **कुल समय:** 09:42 से ~14:01 UTC (15:12 से 19:31 IST), यानी लगभग **4 घंटे 20 मिनट**। पहले अनुमान 12–13 घंटे का था; असली runs 43–61 मिनट के बीच निकले।
- **Computer जगा रहा:** session के दौरान keep-awake चालू रखा गया।
- **कोई GitHub action नहीं, कोई असली order नहीं, कोई key नहीं डाली।** Testnet पर रखी ETH position (#1903401) को छुआ तक नहीं।

---

## भाग 1: Round 1 के नतीजे (pre-registered gates, हर एक का स्वतंत्र verifier PASS)

| Exp | क्या जाँचा | Final ($10k से) | Max DD | 2022 | फ़ैसला | Report |
|---|---|---|---|---|---|---|
| (base) F7 RS | — | $88,401 | 21.37% | +36.5% | — | — |
| **E3** | AI short skill बनाम listing age | (diagnostic) | — | — | **"AI short skill not shown beyond listing age"** | `REPORT_R1_E3_LISTING_AGE_16_OCT_2026.md` |
| **E1a** | आधे shorts की जगह BTC hedge | $58,888 | **13.58%** | +9.3% | **FAIL** (G2: final) | `REPORT_R1_E1_BTC_HEDGE_16_OCT_2026.md` |
| **E1b** | पूरे shorts की जगह BTC hedge | $33,155 | 27.82% | +3.4% | **FAIL** | (वही) |
| **E2** | Short filters (funding, उम्र, volume) | $70,738 | 19.74% | +33.7% | **FAIL** (G1: short PF) | `REPORT_R1_E2_SHORT_FILTERS_16_OCT_2026.md` |
| **E4** | Inverse-vol weights + 30% cap | $60,451 | 20.03% | +20.8% | **FAIL** (G2, G3) | `REPORT_R1_E4_INVVOL_WEIGHTS_16_OCT_2026.md` |
| **N1a / N1b** | MAX (lottery) filter | $66,365 / $62,602 | 19.65 / 22.98% | +28.7 / +26.5% | **FAIL** | `REPORT_R1_N1_MAX_LOTTERY_16_OCT_2026.md` |
| **E11** | Long leg perp पर (cost 0.10%) | **$110,573** | 21.98% | **+64.2%** | **PASS** (DSR 0.93) | `REPORT_R1_E11_PERP_LONGS_16_OCT_2026.md` |

**सीधी बात:**
1. **एक ही variant पास हुआ: E11, यानी longs perps पर।** इसका फ़ायदा trade-दर-trade जाँच से समझ आता है: cost की बचत +0.30%, funding −0.17%, यानी हर trade पर शुद्ध +0.15%। यह कोई छिपा हुआ "जादू" नहीं है।
   - Protocol के अनुसार यह सिर्फ़ **F4 shadow line का candidate** है, आपकी "हाँ" पर, अपनी अलग 90 दिन की forward घड़ी के साथ।
   - सावधानियाँ: DSR 0.93 (0.95 से कम), funding का ख़तरा, cost का अनुमान (S7 के बाद दोबारा हिसाब), और tax (CA से राय)।
2. **नुकसान घटाने वाले तरीके (hedge, filters, vol weights) सब fail हुए।** DD घटता है, लेकिन मुनाफ़ा उससे कहीं ज़्यादा घटता है। BTC hedge 2021–26 में खुद पैसा खोता है।
3. **E3 की अहम सीख:** AI short की ज़्यादातर बढ़त "नए listed perps गिरते हैं" वाले असर में है। फिर भी उसी उम्र के random coins से AI बेहतर है। जो भी Round 2 में इस पर काम करे, उसे यह बात ध्यान में रखनी है।
4. **F7 RS जैसा है वैसा ही रहता है** (protocol: "If nothing passes, F7 stays"; E11 सिर्फ़ candidate है)।

---

## भाग 2: पूरे system का End-to-End integration test

**Script:** `src/audits/e2e_integration_test.py`। असली ledgers सिर्फ़ पढ़े जाते हैं; जो कुछ लिखा जाता है वह temp sandbox में जाता है।

**आख़िरी नतीजा:** A+B (final run `e2e_20261016T134042.json`) 13/13, और C+D (rerun `e2e_20261016T140033.json`) 38/38। **कुल 51/51 PASS।**

| हिस्सा | क्या जाँचा | नतीजा |
|---|---|---|
| A1 | src के सभी 108 Python files compile | ✅ |
| A2 | सभी 38 protocol locks अपने SHA से मिलते हैं; lock के बाद बदली हर code file का बदलाव दर्ज | ✅ |
| A3 | सभी 9 scheduled tasks के script और python मौजूद (wake, triggers, last result दर्ज) | ✅ |
| A4 | Order सुरक्षा: daily scripts में कोई order call नहीं; F6 सिर्फ़ दो test hosts जानता है | ✅ |
| B1–B6 | असली ledgers पर verifiers: 16B (V1, V5, नया V6 forward ledger), F4 (V1–V5 + नया V1b), N3, M4, नया Step 16 verifier, 16B का पूरा V2–V4 (live code = research scores, models, paper engine) | ✅ |
| C1–C8 | Sandbox chain: 16B paper → F4 (2 दिन) → F4 verifier → F6 plan → N3 → N3 verifier → M4 (live) → M4 verifier → M10 (गायब दिन और LATE दिन, दोनों मामले) | ✅ |
| C9 | छहों experiments पर R1 verifier, असली नतीजों की copy पर | ✅ |
| D1–D7 | **हेराफेरी पकड़ने के tests:** F4 ledger में $1 (hash दोबारा बनाने के बाद भी), F4 orders file, N3 का VaR (hash दोबारा बनाने के बाद भी), M4 file में 1 bit, Step 16 का n_coins, R1 का DD ±0.5, flipped decision/reading। हर बार check ने fail किया, जो इन tests में सही नतीजा है। | ✅ |

**F6 mock exchange test:** `src/audits/test_f6_mock_exchange.py`, **15/15 PASS।** Keys के बिना live code के सारे paths जाँचे गए:
- order के साथ ×1.5 पर stop;
- दोबारा चलाने पर कोई नया order नहीं (idempotent);
- stop trigger होना, stop cancel होना;
- drill kill और K1 + HALT;
- hedge mode में मना करना, order reject होना, host guard।

**Synthetic tests (R1 engine):** T0–T8 सब PASS। T8 नया है (cap)।

---

## भाग 3: Testing में पकड़ी गई और सुधारी गई गलतियाँ (सब दर्ज)

| # | कहाँ | गलती | सुधार / दर्ज कहाँ |
|---|---|---|---|
| 1 | **E4 runner** | 2–3 coins होने पर 30% cap चुपचाप टूटा (154 फ़ैसले) | Cap सही किया, T8 test जोड़ा, E4 दोबारा चलाया; पहला run **अमान्य** घोषित किया (R1 CODE_CHANGES §6)। फ़ैसला FAIL ही रहा |
| 2 | **F6** (testnet executor) | Exchange पर stop लगने के बाद वही coin फिर से short हो जाता (F7 का 30 दिन वाला नियम टूटता) | Exchange-side 30 दिन का cooldown जोड़ा (F6 CODE_CHANGES §3); अभी तक कोई testnet order नहीं हुआ |
| 3 | 16B | Lock के बाद हुए बदलावों की SHA दर्ज नहीं थी; forward ledger का कोई verifier नहीं था | SHA दर्ज की, V6 जोड़ा (16B CODE_CHANGES §6–7) |
| 4 | F4 verifier | Ledger के आँकड़े equity file से नहीं मिलाए जाते थे | V1b जोड़ा (F4 CODE_CHANGES) |
| 5 | Step 16 | Ledger का कोई verifier नहीं था | `verify_step16_ledger.py` लिखा, साथ में tamper test |
| 6 | M4 verifier | Live IV की तुलना असल में market को परख रही थी, data को नहीं | V3 को Deribit DVOL history और futures mark klines पर आधारित किया; options IV दोबारा verify नहीं हो सकता, यह साफ़ लिखा (M4 CODE_CHANGES §1–3) |
| 7 | R1 verifier | G5, decision और reading की जाँच नहीं थी; `startswith("E1")` E11 को भी पकड़ लेता था | जोड़ा और सुधारा (R1 CODE_CHANGES §5) |

**कोई भी नियम (gate, threshold, protocol) नतीजा देखने के बाद नहीं बदला गया।**

---

## भाग 4: आपके हिस्से में बाकी
| # | काम |
|---|---|
| U1 | **Wake timers चालू करें** (16B का "last result 1" आज सुबह के देर से जागने का असर है; F4 D1 के लिए सिर्फ़ 4 और late दिन की गुंजाइश है) |
| U2 | Futures testnet keys (F6 के लिए)। **अलग testnet account** इस्तेमाल करें, क्योंकि K1 और drill account की सारी positions बंद कर देते हैं |
| U3 | Spot testnet के बंद पड़े tasks का फ़ैसला |
| U5 | **E11 को F4 shadow line बनाना है या नहीं, यह आपकी "हाँ/ना" पर है** |

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये backtest और test नतीजे हैं, भविष्य की गारंटी नहीं।
