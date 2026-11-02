# 1D Step 17 (कब market से बाहर रहना है) + Step 18 (trade कहाँ नहीं लेना है) — रिपोर्ट

**तारीख:** 14 अक्टूबर 2026 | **GitHub:** कुछ नहीं | **Trading:** spot, 1D, long-only, $10k | **कुछ deploy नहीं हुआ**

**Protocol:** `logs/strategy_1d_step17_18/STEP17_18_PROTOCOL_PREREGISTERED.md`
- Protocol SHA256 `e3dfd6b4...`, code SHA256 `c5bcf4e1...`, दोनों training से पहले lock हुए।
- Step 15 के R5 predictions भी lock में थे, और बिना बदले इस्तेमाल हुए।

**Lock के बाद 2 bug fixes हुए** (दर्ज: `CODE_CHANGES_AFTER_LOCK.md`):
1. **पहला:** तारीख वाली helper में crash, किसी भी नतीजे से पहले।
2. **दूसरा:** **G1 जाँच ने एक असली bug पकड़ा।**
   - Veto का leak test 0.504 आया, जबकि उसे ~1.0 होना चाहिए था।
   - वजह: AUC निकालते समय predictions और labels अलग-अलग क्रम में जोड़े जा रहे थे।
   - Run वहीं रोका गया। तब तक किसी दिमाग की skill का कोई नतीजा नहीं बना था।
   - Fix के बाद leak test **1.000** आया।

**Verifier:** `src/audits/verify_step17_18_claims.py` → V1–V5 PASS।
- Labels raw कीमतों से दोबारा बने।
- 6 portfolios अलग code से दोबारा simulate हुए।
- Verifier में मेरी एक NaN-handling गलती थी, जो ठीक की।

## Design
- **Step 17, market दिमाग:** "अगले 5 दिन में आम altcoin ऊपर जाएगा?" यह हर दिन एक जवाब देता है, 18 market features से (median returns, BTC, breadth, Fear & Greed, dispersion आदि)।
- **Step 18, veto दिमाग:** "क्या इस coin में 5 दिन में खर्च के बाद नुकसान होगा?" यह coin के 47 features और market के 18 features से सीखता है।
- **दोनों के साथ R5:** Step 15 का 5-दिन वाला दिमाग, बिना बदले।
- **एक साथ run:** दोनों एक ही run में चले, ताकि B हिस्से पर बार-बार नज़र न पड़े। हर दिमाग का अलग skill gate था।

## नतीजे (B हिस्से के 266 अनदेखे coins, 2021-01 → 2026-09)

| दिमाग | AUC | भरोसे की सीमा (95%) | नकली AI | Skill साबित? |
|---|---|---|---|---|
| Market (Step 17) | 0.523 | 0.494 – 0.554 | 0.503 | ✗ |
| Veto (Step 18) | **0.529** | **0.506 – 0.552** | 0.501 | **✓** |

| System ($10k, 0.25% खर्च) | Final | CAGR | Max DD | Market में दिन |
|---|---|---|---|---|
| R5 अकेला (Step 15) | $22,617 | 15.3% | 86.2% | 100% |
| **FULL (R5 + market + veto)** | **$4,758** | **−12.1%** | 74.3% | 40% |
| नकली दिमागों के साथ FULL | $12,908 | 4.5% | 72.4% | 50% |
| R5 + सिर्फ market (सिर्फ जानकारी के लिए) | $4,831 | −11.9% | 79.5% | 45% |
| R5 + सिर्फ veto (सिर्फ जानकारी के लिए) | $11,418 | 2.3% | 74.3% | 65% |

**फैसला: `FAIL`। कुछ deploy नहीं हुआ।** G1 और veto skill ✓; market skill और सारे trading gates ✗।

## क्यों fail हुआ (सबूत)
1. **Market दिमाग उल्टा चला।** Rebalance वाले दिनों पर:
   - जब उसने "market में रहो" कहा, तब आम B-coin का 5 दिन का औसत **−1.77%** था।
   - जब "बाहर रहो" कहा, तब **−0.87%**।
   - यानी उसकी skill नहीं है, और उसने बचाने के बजाय नुकसान बढ़ाया।
2. **Veto दिमाग सही है, पर R5 के ऊपर फालतू है।**
   - सारे coins पर: veto वाले rows औसत −0.42% (नुकसान 54.4% बार), बाकी +0.23% (51.4%)।
   - पर R5 के top-10 picks के अंदर: veto वाले +1.13%, बाकी +1.07%, यानी कोई फर्क नहीं।
   - Veto वही पहचानता है जो R5 पहले से जानता है। ~45% picks हटने से निचले rank वाले coins खरीदे गए, इसलिए नुकसान हुआ।
3. **बड़ी सच्चाई:** B-हिस्से का आम altcoin 5 दिन में औसतन गिरता है। Rebalance दिनों पर सिर्फ ~42% बार median ऊपर गया। Long-only spot में छोटे altcoins के साथ हम एक गिरती धारा के खिलाफ तैर रहे हैं।

## Steps 7–18 का सार (सब verified)
| क्या साबित हुआ | क्या साबित नहीं हुआ |
|---|---|
| Coin चुनने की skill: B1 0.530 (Step 13), **R5 0.545** (Step 15) | Market में कब रहना है (Step 17: 0.523, सीमा 0.494) |
| "खराब trade" पहचानने की skill: veto 0.529 (Step 18) | एक ऐसा long-only नियम जो खर्च के बाद हर साल टिके |
| Live system = research system (replay हूबहू) | — |
