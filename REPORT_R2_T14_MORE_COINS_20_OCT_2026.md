# T14: ज़्यादा coins पर AI की दोबारा जाँच (20 अक्टूबर 2026)

**सवाल:**
- A3 में AI सिर्फ़ 10 coins और लगभग 7,000 rows पर FAIL हुआ था।
- तो क्या ज़्यादा coins और ज़्यादा data देने से AI को कोई असली बढ़त मिलती है?

**जवाब: नहीं। "T14 FAIL"** (pre-registered नियम)।
- Independent verifier: **6/6 PASS।**
- Trial registry: 5/5 PASS। 20 में से 14 trials इस्तेमाल हुए; सबके नतीजे दर्ज हैं और कोई pending नहीं है।

**अनुशासन:**
- Protocol `856eee90…` store बनने और model चलने से पहले lock किया गया।
- Model, gates और portfolio हूबहू A3 वाले रखे गए। सिर्फ़ DSR में N = 14 बदला।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

## 1. Data
- **Candidates:** 135 coins। ये वे coins हैं जिनकी 5m, 1h, 1d, funding और perp files, पाँचों मौजूद हैं।
- **Liquidity filter:** signal से पहले के 30 दिनों में perp volume का median ≥ 50M USDT होना चाहिए। यह filter हर row पर उसी समय के data से लगाया गया।
- **नतीजा:** 90,131 में से **30,889 rows** बचीं, **120 coins** से। Dev (P1 + P2) में 26,217 rows हैं, यानी A3 से लगभग 3.7 गुना।
- **Regression check:** पुराने 10 coins की सभी 9,740 rows A2 store से हूबहू मिलीं।

## 2. Gates
| Gate | नतीजा | पास? |
|---|---|---|
| G-A skill | AUC 0.505। CI (AUC − 0.5) −0.004 से +0.013 है, यानी 0 को छूता है। Shuffled p95 0.500 | ❌ |
| G-B प्रति trade | AI ने जो trades लिए, वे सब signals से +0.020 R बेहतर थे, CI 0.009 से 0.030 (1.5× खर्च पर भी) | ✅ |
| G-C portfolio | AI Calmar −0.04। Baseline −0.26, random-skip p95 −0.08 | ✅ (सभी घाटे में) |
| G-D tail | सबसे अच्छे 10% trades में से 73% लिए (कुल take rate 72%) | ✅ |
| G-E stability | P1 और P2 दोनों में AI baseline से बेहतर रहा | ✅ |
| G-G खर्च | 1.5× / 2× खर्च पर net +0.040 / +0.031 R | ✅ |
| G-H diversification | 1D system के साथ correlation −0.14 | ✅ |
| **DSR** | **0.15** (चाहिए ≥ 0.95) | ❌ |

## 3. Portfolio (8,000 USDT, 0.5% risk, mark-to-market, P1 + P2)
| | Final | CAGR | MTM DD | Calmar |
|---|---|---|---|---|
| सारे signals (baseline) | **3,537** | −15.8% | **60%** | −0.26 |
| AI filter | 7,689 | −0.8% | 20% | −0.04 |

**P3 (आख़िरी साल, सिर्फ़ report):**
- AUC 0.528।
- AI 8,181 पर रहा, baseline 8,564 पर। यानी इस साल AI baseline से पीछे रहा।

## 4. इसका मतलब
1. **AI के पास कोई भरोसेमंद अनुमान-क्षमता नहीं है**, 3.7 गुना data के बाद भी। AUC 0.505 और DSR 0.15 है, इसलिए 4H AI sleeve नहीं बनेगा।
2. **सबसे बड़ी सीख: signals छोटे और नए coins पर काम नहीं करते।**
   - 10 बड़े coins पर signals में कमाई थी। 120 coins पर सब signals लेने वाला portfolio −56% गिरा।
   - AI ने कुछ बुरे trades हटाए (G-B), पर पैसा फिर भी नहीं बना।
   - इसलिए **universe को बड़े, पुराने coins तक सीमित रखना** ही सही है।
3. **अब तक की सबसे मज़बूत चीज़ बिना AI वाला सीढ़ी-long signal है, 10 बड़े coins पर** (A4 report देखें)। पर उसका भी आख़िरी साल (P3) कमज़ोर था।

## 5. रास्ते में पकड़ी गई गलतियाँ
1. **मेरी एक शुरुआती अनौपचारिक गिनती गलत थी।**
   - मैंने AUC 0.497 बताया था। Model rows का क्रम बदलता है और मैंने गलत index पर labels जोड़ दिए थे।
   - सही AUC 0.505 है। फ़ैसला नहीं बदला।
2. **Verifier पहली बार crash हुआ।**
   - नए listed coin में signal के समय 2 से कम legs थीं, और verifier यह case नहीं संभालता था।
   - उसे A2 store वाले नियम पर लाया: ऐसे में NaN।
   - Study code या नतीजे में कोई बदलाव नहीं हुआ। दर्ज: `logs/r2_4h_t14/CODE_NOTES.md`; crash output `verify_t14_stdout_run1_crash.txt`।

## 6. Files
- **Protocol:** `logs/r2_4h_t14/T14_PROTOCOL_PREREGISTERED.md`
- **Claims और verifier output:** `logs/r2_4h_t14/claims_t14.json`, `verify_t14_stdout.txt`
- **Store:** `data/derived/r2_t14/feature_store.parquet` (`0698d718…`)
- **Registry:** `logs/r2_4h_a0/trial_registry.csv`, T14-RESULT लाइन

## 7. आगे के विकल्प (फ़ैसला आपका)
- **(a)** 4H पर AI का काम यहीं रोक दें। सीढ़ी-long rule signal को forward recorder data के साथ सिर्फ़ paper पर देखते रहें।
- **(b)** बचे 6 trials किसी नए विचार पर लगाएँ, जैसे दूसरा timeframe या दूसरी तरह के features।
- **F6 testnet "operations ready" की जाँच** आज 10:30 IST के run के बाद होगी।
