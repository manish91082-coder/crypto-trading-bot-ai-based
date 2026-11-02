# Round 1, E4: inverse-volatility weights + हर coin पर 30% की सीमा (16 अक्टूबर 2026)

**फ़ैसला: FAIL** (G2, G3 fail)। इसे अपनाया नहीं जाएगा।

## ⚠ पहला run अमान्य था (verifier ने पकड़ा)
- **क्या हुआ:** पहले run में verifier V3 fail हुआ। जिन फ़ैसलों में किसी leg में सिर्फ़ 2–3 coins थे (5,284 में से 154), वहाँ 30% की सीमा गणित से संभव नहीं थी, और code ने चुपचाप बराबर weights (33% या 50%) दे दिए। यह protocol के नियम "हर weight ≤ 30%" का उल्लंघन था।
- **सुधार:** protocol के शब्दों के हिसाब से अब हर weight 30% पर रुकता है, और बचा हुआ हिस्सा cash में रहता है। यह सुधार दोबारा run करने से पहले `CODE_CHANGES_AFTER_LOCK.md` §6 में लिखा गया।
- **Test से पुष्टि:** synthetic test T8 पुराने code पर fail हुआ और नए पर PASS है।
- **पुराना नतीजा:** final $61,379, FAIL। इसे `claims_E4_INVALID_cap_deviation.json` में सिर्फ़ record के लिए रखा गया है, इस्तेमाल नहीं होगा।
- **दोनों runs का फ़ैसला एक ही (FAIL) रहा।**

## सबूत (सुधरा हुआ run)
- **Run:** `python src/pipeline_1d/r1_run.py E4` (runner SHA 0d898580…), stdout `run_E4_stdout.txt`
- **Claims:** `claims_E4.json`
- **फ़ैसलों का record:** `decisions_E4.csv` (5,276 weight sets; इनमें से 155 में 30% cap की वजह से कुछ हिस्सा cash में रहा)
- **Verifier** (`verify_E4_stdout.txt`):
  - V1 PASS: protocol, engine और runner के hash मिलते हैं।
  - V2 PASS: सारे आँकड़े और G1–G5 दोबारा निकाले गए।
  - V3 PASS:
    - हर set में weights का जोड़ = min(1, 0.3 × n) है, और हर weight ≤ 30%।
    - 60 rows का σ60 raw daily closes से दोबारा निकाला गया।
    - 20 weight sets एक अलग loop से σ से दोबारा निकाले गए।

## नतीजे
| | F7 RS (baseline) | **E4 (सुधरा हुआ)** |
|---|---|---|
| Final ($10k से) | **$88,401** | $60,451 |
| Max DD | 21.37% | **20.03%** |
| 2022 | **+36.54%** | +20.81% |
| सबसे बुरा हफ़्ता | **−9.63%** | −9.87% |
| सबसे बुरा short दिन | −$6,454 | **−$4,383** |
| Long PF / Short PF | 1.22 / 1.07 | 1.247 / 1.062 |
| DSR (N = 91) | — | 0.815 |

**10 controls (random Dirichlet weights, उसी cap के साथ):** max DD 18.26% से 25.68% के बीच, median 21.105%।

## Gates
| Gate | शर्त | नतीजा |
|---|---|---|
| G1 | DD < 21.37% | ✅ 20.03 |
| G2 | सबसे बुरा हफ़्ता > −9.63% | ❌ −9.87 |
| G3 | Final ≥ 85% × F7 ($75,141) | ❌ $60,451 |
| G4 | 2022 > 0 | ✅ |
| G5 | DD < control median (21.105%) | ✅ |
| **फ़ैसला** | | **FAIL** |

## मेरी व्याख्या
1. **कम volatility वाले coins को ज़्यादा पैसा देने से DD थोड़ा घटा, पर मुनाफ़ा बहुत घटा।** हमारी AI ranking की कमाई ज़्यादा volatile coins से आती है, और यह नियम उन्हीं का हिस्सा कम कर देता है।
2. **सबसे बुरा हफ़्ता भी बेहतर नहीं हुआ,** इसलिए "नुकसान घटाने" का मुख्य लक्ष्य पूरा नहीं हुआ।
3. **यह शोध-साहित्य से मेल खाता है।** Crypto में low-volatility का असर विवादित है (पहले की research report में भी यही लिखा था)।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये backtest नतीजे हैं।
