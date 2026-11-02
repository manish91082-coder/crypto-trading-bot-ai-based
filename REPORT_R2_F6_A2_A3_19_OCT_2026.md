# R2 report: F6 drill-kill, A1 correction, A2 knowledge store, A3 AI brain (19 अक्टूबर 2026, रात)

**तरीका वही रहा:** हर चरण से पहले protocol और SHA lock, फिर code, फिर अपने अलग code वाला independent verifier, और lock के बाद का हर बदलाव `CODE_CHANGES_AFTER_LOCK.md` में दर्ज।

**क्या छुआ नहीं गया:** 1D cloud system, laptop production, `archive/`, GitHub। असली पैसे का कोई order नहीं हुआ (F6 सिर्फ़ demo exchange पर)।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

## सार
| चरण | नतीजा | सबूत |
|---|---|---|
| **F6 drill-kill (O4)** | ✅ PASS | Drill से पहले O1/O2/O3/O5 PASS (15 shorts, हर एक पर सही stop)। Drill: 14 actions, उसके बाद 0 positions और 0 stop orders। HALT नहीं बना |
| **A0 में दो गलतियाँ मिलीं** (training से पहले) | ✅ सुधरीं (amendments 1, 2, lock किए गए) | नीचे §2 |
| **A1 correction** | ✅ verifier 4/4 | 20 hindsight-छूटे trades जुड़े, 14 timing गलतियाँ सुधरीं |
| **A2 knowledge store** | ✅ verifier 4/4 | 9,740 rows, 36 features; 500 replays में 0 leak; canary 100% पकड़ा गया |
| **A3 AI दिमाग (trial T05)** | ❌ **FAIL** (pre-registered gates) | Verifier 4/4 ने नतीजे की पुष्टि की |

## 1. F6
- **O4 PASS:** drill के बाद demo exchange पर 0 positions और 0 खुले stop orders।
- **"Operations ready" का औपचारिक फ़ैसला** कल (20 अक्टूबर) 10:30 के run के verifier के बाद होगा, क्योंकि protocol लगातार 2 runs माँगता है। HALT नहीं बना, इसलिए कल का run book फिर से खोलेगा।

## 2. A0 में मिली दो गलतियाँ (ज़मीनी जाँच से, किसी model के बनने से पहले)
1. **Look-ahead (amendment 1):**
   - A0 के feature list में "confirming leg" के `move_atr`, `bars` और `done_share` थे।
   - Data पर नापा: **73%** मामलों में उस leg का अंत signal के **बाद** आता है (median 28 घंटे बाद)।
   - इनकी जगह आख़िरी पूरी हुई leg के features लिए गए, जो 100% मामलों में signal से पहले ज्ञात होती है।
   - पुरानी Swing AI study (phase 2) ने ये features इस्तेमाल नहीं किए थे, इसलिए उस पर असर नहीं।
2. **Hindsight और same-candle बराबरी (amendment 2):**
   - ZigZag की "final" pivot list बाद में fail हुए pivots को हटा देती है: 4h पर 7,541 में से 102 (1.4%)।
   - एक ही candle पर दो pivots होने (4h legs का 1.5%) से labels और "कब पता चला" का समय गड़बड़ा जाता था।
   - **सुधार:** real-time pivot timeline (`src/research/r2_realtime_pivots.py`), जो confirm होने पर pivot जोड़ती है और fail होने पर हटाती है, ठीक वैसे जैसे live system देखता।

## 3. A1 correction (S-LAD, S-DTB)
| Signal | पहले net R | अब net R | अब 95% CI |
|---|---|---|---|
| S-LAD long | +0.134 | **+0.128** | 0.064–0.192 |
| S-LAD short | +0.062 | **+0.053** | **−0.008**–0.115 |
| S-DTB short | +0.070 | **+0.046** | — |

- 20 नए trades जुड़े। ये उन pivots के हैं जो live confirm हुए पर बाद में fail हुए। इनका औसत −0.6 से −0.9 R है, यानी पुराने नतीजे थोड़े फूले हुए थे।
- सारे 8 signal-sides अब भी A1 का (ढीला) gate पास करते हैं।
- पुरानी studies (S5, S6) पर असर ~1–3% rows का है। यह errata index में दर्ज है।

## 4. A2 knowledge store
- **9,740 rows** (corrected trades) और **36 features।** हर row के साथ `available_at` दर्ज है।
- **Replay:** 200 rows (study में) + 300 rows (verifier में, अलग seed से) के features **सिर्फ़ उस समय तक के data** से दोबारा बनाए गए। मूल swing code से: **एक भी mismatch नहीं।**
- **Leak canary:** जानबूझकर डाला गया भविष्य का feature 200 में से 200 replays में पकड़ा गया। अकेले उसका AUC 0.83 था, यानी असली leak होता तो वह भी पकड़ा जाता।

## 5. A3: 4h AI दिमाग (B2-fast) — **FAIL**
| Gate | शर्त | नतीजा | पास? |
|---|---|---|---|
| G-A skill | AUC > shuffled p95, और CI(AUC − 0.5) > 0 | AUC **0.514**; shuffled p95 0.512; CI **−0.003…+0.030** | ❌ |
| G-B प्रति trade | लिए गए − सारे: CI > 0 (base और 1.5×) | +0.018 R (CI 0.003–0.034) | ✅ |
| G-C portfolio | AI Calmar > baseline, और > random-skip p95 | AI **0.50**, baseline 0.17, **random-skip p95 0.58** | ❌ |
| G-D tail | बड़े winners का हिस्सा ≥ take rate | 78% ≥ 75% | ✅ |
| G-E स्थिरता | P1 और P2 दोनों में | ✅ | ✅ |
| G-G खर्च | 1.5× और 2× पर net > 0 | 0.065 / 0.053 | ✅ |
| G-H 1D से जुड़ाव | correlation ≤ 0.70 | **−0.08** | ✅ |
| DSR | ≥ 0.95 | **0.82** | ❌ |

**सीधी भाषा में:**
- AI वाले portfolio (8,000 से 10,142; MTM DD 10%) ने "सारे signals लो" (9,887; DD 27%) को हराया।
- **पर उतने ही trades random तरीके से छोड़ने पर भी लगभग इतना ही या बेहतर नतीजा मिलता है।** यानी फ़ायदा trades घटाने से आया, AI के सही trades चुनने से नहीं।
- AUC 0.514 बहुत कमज़ोर है, और उसका CI शून्य को छूता है।

**ईमानदार टिप्पणियाँ:**
- Protocol के threshold नियम से take rate ~50% अपेक्षित था, असल में **75%** रहा (calibration slice के median की वजह से)। यह नियम lock था, इसलिए बदला नहीं गया।
- आख़िरी साल (P3) में AI −4% (7,653) रहा, जबकि baseline −21% (6,292)। P3 gate में नहीं है।
- 4 signals का "सारे लो" baseline dev अवधि में **घाटे में** रहा (MTM DD 27%)। यह audit के S-LAD-only portfolio से कमज़ोर है, क्योंकि K = 6 की सीमा में चारों signals आपस में जगह के लिए टकराते हैं।
- Trial budget: 20 में से **5** इस्तेमाल हुए।

**Protocol का नियम (A3 FAIL):** कोई AI sleeve नहीं बनेगी। आगे क्या करना है, वह फ़ैसला आपका है।

## 6. बाकी काम और फ़ैसले
| काम | हालत |
|---|---|
| F6 "operations ready" | कल 10:30 के run के verifier के बाद |
| Drive token rotate करना | **आपका काम** (Google account की security setting; मैं नहीं बदल सकता) |
| असली account का `commissionRate` | आपकी असली key चाहिए |
| S7 recost | ~30 अक्टूबर (30 rounds पूरे होने पर) |
| Day-90 evaluation | ~12 जनवरी 2027 |
| **A3 के बाद क्या?** | **आपका फ़ैसला।** विकल्प: (a) AI 4h sleeve पर रुक जाएँ; recorder का forward data जमा होता रहे। (b) A4 बिना AI के, सिर्फ़ S-LAD long (सबसे मज़बूत signal) के exits और sizing पर; बचे 15 trials में से। (c) Universe expansion trial (T06): ज़्यादा coins पर वही AI, क्योंकि कम data (~7k rows) भी एक कारण हो सकता है। हर विकल्प नया trial है और pre-register होगा |
