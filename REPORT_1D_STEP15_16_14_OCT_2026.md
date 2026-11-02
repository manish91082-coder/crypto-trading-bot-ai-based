# 1D Step 15 (धीमा सवाल) + Step 16 (forward dry-run) — रिपोर्ट

**तारीख:** 14 अक्टूबर 2026 | **GitHub:** कुछ नहीं | **Trading:** spot, 1D, long-only, $10k | **कोई order नहीं, कोई पैसा नहीं**

---

## Step 15: "अगले 5 / 10 दिन में यह coin 30 बड़े coins के median से बेहतर करेगा?"

**Protocol:** `logs/strategy_1d_step15_slow/STEP15_PROTOCOL_PREREGISTERED.md`
- Protocol SHA256 `4f053355...` और code SHA256 `9b5d40a6...`, दोनों training से पहले lock हुए।

**Verifier:** `src/audits/verify_step15_claims.py` → V1–V4 PASS।
- Labels raw कीमतों से दोबारा बने, जिसमें 30 बड़े coins का median भी शामिल है।
- AUC दोबारा निकाले।
- 8 portfolios अलग code से दोबारा simulate हुए।
- Verifier में मेरा एक indexing bug था, जो ठीक किया। Pipeline का code नहीं बदला।

**Setup:**
- **Training:** 30 पुराने coins और A-हिस्से के 265 coins, कुल 2.41 लाख rows।
- **परीक्षा:** B-हिस्से के 266 coins (1.78 लाख rows)। ये coins training में कभी नहीं थे।
- **Trading नियम:** पहले से तय एक ही नियम, कोई grid नहीं। हर 5/10 दिन पर top-10 खरीदो, और coin तब तक रखो जब तक वह top-20 में रहे।
- **खर्च:** 0.25% प्रति fill।

### नतीजे

| जाँच | R5 (5 दिन) | R10 (10 दिन) |
|---|---|---|
| Pipeline जाँच (planted / leak) | 0.607 / 1.000 ✓ | (साझा) |
| **Skill AUC (Bonferroni CI)** | **0.545 (0.532–0.558)** ✓ | **0.541 (0.522–0.559)** ✓ |
| नकली AI AUC | 0.510 | 0.517 |
| Portfolio final ($10k) | $22,617 | $16,004 |
| CAGR / Max DD | 15.3% / **86.2%** | 8.5% / **90.1%** |
| हर trade, खर्च से पहले / बाद | +1.96% / +1.45% | +2.67% / +2.16% |
| Trade-औसत का CI (खर्च के बाद) | −0.62% … | −1.03% … ✗ |
| फायदे वाले साल | 2 / 6 ✗ | 2 / 6 ✗ |
| नकली AI / सरल momentum | $1,015 / $117 | $705 / $239 |
| 0.40% खर्च पर | $13,480 ✓ | $11,986 ✓ |

**फैसला: `PARTIAL_SKILL_RULE_FAILS`। कुछ deploy नहीं हुआ।**

### क्या सीखा (सबूत के साथ)
1. **धीमे सवाल से skill बढ़ी:** 1-दिन वाले दिमाग की 0.530 के मुकाबले अब 0.545 है। हर trade की कमाई भी अब खर्च से साफ बड़ी है (+1.96% बनाम 0.50% खर्च)। Step 14 वाली खर्च की समस्या हल हो गई।
2. **AI के चुने coins हर साल बेहतर रहे:** B-हिस्से में AI के top-10 हर साल, सभी 6 सालों में, बाकी coins से आगे रहे। 5 दिन का औसत return:
   - 2021: +4.55% बनाम +2.10%
   - 2022: −0.59% बनाम −2.00%
   - 2025: −1.27% बनाम −1.99%
3. **नई असली समस्या है पूरे market का गिरना:**
   - जब पूरा altcoin market गिरता है (2022, 2025), तो अच्छे चुने coins भी गिरते हैं, बस कम।
   - Spot long-only में हम सिर्फ खरीद सकते हैं, इसलिए portfolio मार्च 2024 के $1,19,799 से 86% गिरा।
   - पूरी कमाई का बड़ा हिस्सा सिर्फ 2021 के altcoin boom (+777%) से आया। एक साल पर इतनी निर्भरता भरोसे लायक नहीं है।
4. **अगला कदम:** AI को यह भी तय करना है कि **कब market से बाहर रहना है।** यह coin चुनने से कठिन सवाल है: हर दिन सिर्फ एक market होता है, इसलिए सीखने के उदाहरण बहुत कम हैं। इसे भी पहले लिखे नियमों के साथ test करना होगा।

---

## Step 16: Forward dry-run (live data, कोई order नहीं)

**Protocol:** `logs/strategy_1d_step16_forward/STEP16_PROTOCOL_PREREGISTERED.md`, SHA256 `224f8958...`

**रोज़ क्या होता है:**
- Scheduled task `CryptoBot1D_ForwardDryRun` रोज़ 05:50 IST पर चलता है, और 06:50 पर एक retry होता है।
- यह Binance से कल तक की बंद candles लाता है, और हर liquid coin के लिए B1 (1-दिन) और R5 (5-दिन) के scores लिखता है।
- हर run की एक line hash-chain ledger में जाती है, ताकि बाद में कोई बदलाव छिप न सके।

**सबूत कि live system वही करता है जो research में था:**

| जाँच | नतीजा |
|---|---|
| B1 replay 15-09-2026 | 98/98 coins हूबहू (अंतर 5.6e-17) |
| B1 replay 15-03-2023 | 185/185 हूबहू; Step 13 की "120 दिन" वाली कमी पकड़ी गई (Step 13 addendum: असर AUC 0.5299 → 0.5304) |
| R5 replay 15-09-2026 | 44/44 B-coins हूबहू (अंतर 5.6e-17) |
| REST API बनाम Binance Vision daily files (SHA256) | 324 coin-day candles, सभी 9 fields बराबर, 0 mismatch |
| Fear & Greed इतिहास बनाम locked file | 0 अंतर |

**ईमानदार सीमा (data से नापी गई):**
- 1-दिन वाली skill इतनी पतली है कि forward test उसे 6 महीने में भी अकेले साबित नहीं कर पाता: 180-दिन की सिर्फ 21% खिड़कियों में CI 0.50 से ऊपर गया।
- इसलिए forward test का काम "सबूत" देना नहीं है। उसका काम है:
  - integrity (live system research जैसा ही है);
  - alarm (30/60/90/180 दिन पर पहले से तय सीमाएँ)।

**पहला असली forward दिन:** as-of 13-10-2026, जो 14-10-2026 को 05:50 IST पर लिखा जाएगा। 1–12 अक्टूबर backfill नहीं होंगे।
