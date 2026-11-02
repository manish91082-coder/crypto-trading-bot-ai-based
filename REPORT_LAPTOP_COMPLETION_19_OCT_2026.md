# Laptop पर आज के सारे काम की पूरी जाँच (19 अक्टूबर 2026)

**आपका निर्देश:** पहले laptop पर code, testing, verification और check का बचा हुआ सारा काम पूरा करना; cloud और Drive बाद में एक साथ। उसी discipline से, बिना rubber-stamping के।

**नतीजा:**
- **Laptop का हिस्सा पूरा है।** Final regression में हर verifier और test PASS हुआ। अपवाद सिर्फ़ master audit के 2 rounding FAIL हैं, जो पहले से दर्ज हैं।
- इस जाँच में **5 असली कमियाँ** मिलीं। सब ठीक की गईं और दर्ज हुईं।
- **Cloud और Drive पर कुछ नहीं बदला।** अपवाद: VM पर Ubuntu के repo से rclone install हुआ था (पिछले कदम में)।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

## 1. आज की जाँच में मिली कमियाँ (सब ठीक, सब दर्ज)
| # | कहाँ | कमी | कैसे पकड़ी | सुधार और सबूत |
|---|---|---|---|---|
| 1 | Recorder | अगर run बीच में रुक जाए (VM reboot), तो अनाथ folder बचता, verifier हमेशा FAIL देता, और state में ऐसा data गिना जाता जो chain में नहीं है | Code review | `state_after.json` → ledger → फिर state.json (atomic)। अगला run अनाथ folder अलग करता है और state पिछले पक्के run से वापस लाता है। **T6, T7 PASS** |
| 2 | Recorder | Code का SHA run के अंत में लिया जाता था | Code review | अब शुरुआत में |
| 3 | Recorder | 29 दिन से ज़्यादा बंद रहने पर खोया data ledger में दर्ज नहीं होता था | Code review | "LOST" नोट (**T8 PASS**) |
| 4 | Recorder verifier | Network एक पल टूटा तो verifier crash हो गया | Test run (T2 rerun) | 3 retries। फिर भी न चले तो check **FAIL** होता है, कभी PASS नहीं |
| 5 | Master audit verifier | FAIL होने पर भी exit code 0 देता था | Regression | अब FAIL पर exit 1 |

**मेरी अपनी test-design गलती, जो पकड़ी गई:**
- T5 (3 दिन बंद रहने के बाद फिर शुरू होना) के पहले design में 6 में से 5 endpoints असल में परखे ही नहीं गए थे, क्योंकि Binance 30 दिन से पुराना data नहीं देता और वहाँ HTTP 400 आया।
- यह "10 http errors" की जाँच से पकड़ा गया। Test ठीक किया: अब पहले run में 0 errors हैं और 12/12 series में data है।
- पुराना log सबूत के तौर पर रखा गया है।

## 2. Final regression (`logs/r2_4h_a0/REGRESSION_19_OCT_2026.txt`)
| जाँच | नतीजा |
|---|---|
| 13 Python files compile | OK |
| Master audit verifier | 64/66 (2 ज्ञात rounding FAIL); अब exit 1, जैसा होना चाहिए |
| A1 verifier | **5/5** |
| Trial registry verifier (नया) | **5/5**। जानबूझकर की गई 3 छेड़छाड़ें (नाम बदलना, आँकड़ा बदलना, एक line हटाना) तीनों पकड़ी गईं |
| Recorder verifier (मुख्य local root, 3 chained runs) | **9/9**, 40 rows live API से दोबारा लाकर हूबहू मिलीं |
| Recorder robustness (T5–T9) | **5/5**: 3 दिन का resume (सभी 6 endpoints, 3 pages तक), crash से पहले और बाद, LOST नोट, test-option guard |
| Recorder पुराने tests (T2–T4, नए code पर) | T3a/b/c, T4 PASS; T2 verifier 9/9 (retry सुधार के बाद) |
| Log ship laptop tests | **5/5** (T1–T4 + verifier) |

## 3. Cloud और Drive के लिए तैयार (अभी चलाया नहीं गया)
`deploy/R2_CLOUD_DEPLOY_PLAN.md` में हर कदम और उसकी जाँच लिखी है:
1. Files copy और SHA मिलान।
2. Recorder का पहला run, फिर verifier 9/9, फिर crontab में 6 lines।
3. **आपका एक बार का Google login** (rclone, scope सिर्फ़ drive.file), फिर T6 (असली Drive), फिर verifier W1–W4, फिर crontab में हर घंटे की 1 line।
4. एक ज्ञात बात: crontab file बदलने पर master audit का एक पुराना SHA check जानबूझकर FAIL होगा। इसे deploy log में दर्ज करना है।

## 4. अभी भी बाकी (बदला नहीं)
- **Cloud + Drive deployment**, आपके साथ एक साथ।
- **A2 से आगे:** A2, A3, A4, A5, A6, A7, A8, फिर A9 (आपका फ़ैसला)।
- 1D के साथ combination study।
- असली account का commissionRate (आपकी key चाहिए)।
- F6 drill-kill।
- S7 (~30 अक्टूबर)।
- Day-90 (~12 जनवरी)।
