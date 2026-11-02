# Round 1, E1: short book का हिस्सा BTC hedge में (16 अक्टूबर 2026)

**फ़ैसला: E1a FAIL, E1b FAIL।** इनमें से कुछ भी अपनाया नहीं जाएगा।

## सबूत
- **Run:** `python src/pipeline_1d/r1_run.py E1`, stdout `logs/research_r1/run_E1_stdout.txt`
- **Claims:** `claims_E1.json`
- **Verifier** (`verify_E1_stdout.txt`):
  - V1 PASS: protocol, engine और runner के hash मिलते हैं।
  - V2 PASS: सारे आँकड़े और G1–G5 सादे loops से दोबारा निकाले गए; G5 control की list से दोबारा लगाया गया।
  - V3 PASS: E1a के 5 और E1b के 8 hedge stops, हर एक की fill कीमत raw BTC perp bars से entry × 1.5 × 1.01 (gap पर open × 1.01) के रूप में दोबारा निकाली गई।

## नियम (protocol में पहले से तय)
- Short book के notional का w हिस्सा BTCUSDT perp short (hedge) में जाता है:
  - **E1a:** w = 0.5
  - **E1b:** w = 1.0, यानी कोई alt short नहीं
- Hedge का weight 25% से ज़्यादा भटके तो rebalance होता है, और hedge पर भी ×1.5 stop लगता है।

## नतीजे
| | F7 RS (baseline) | **E1a** (w = 0.5) | **E1b** (w = 1.0) |
|---|---|---|---|
| Final ($10k से) | **$88,401** | $58,888 | $33,155 |
| Max DD | 21.37% | **13.58%** | 27.82% |
| Calmar | 2.159 | **2.662** | 0.834 |
| 2022 | **+36.54%** | +9.28% | +3.43% |
| सबसे बुरा short-side दिन | −$6,454 | **−$3,110** | −$4,340 |
| सबसे बुरा हफ़्ता | **−9.63%** | −10.37% | −12.04% |
| Alt short P&L (sleeves का औसत) | $26,227 | $13,135 | — |
| BTC hedge P&L | — | **−$11,008** (PF 0.70) | **−$17,931** (PF 0.70) |
| DSR (N = 91) | — | 0.863 | 0.363 |

**10 controls (E1a, short ranking random):** final $24.8k–$33.2k, median ≈ $28.3k।

## Gates
| Gate | शर्त | E1a | E1b |
|---|---|---|---|
| G1 | DD ≤ 21.37% | ✅ 13.58 | ❌ 27.82 |
| G2 | Final ≥ 80% × F7 ($70,721) | ❌ $58,888 | ❌ $33,155 |
| G3 | 2022 > 0 | ✅ | ✅ |
| G4 | सबसे बुरा short दिन ≥ −$6,454 | ✅ | ✅ |
| G5 | Final > control median | ✅ | n/a (CODE_CHANGES 1a) |
| **फ़ैसला** | | **FAIL** (G2) | **FAIL** (G1, G2) |

## मेरी व्याख्या
1. **BTC hedge खुद पैसा खोता है।** 2021–2026 में BTC ज़्यादातर ऊपर गया, इसलिए BTC short का P&L −$11k से −$18k रहा। Hedge से drawdown घटता है (E1a में 21.4% से 13.6%), लेकिन वृद्धि का एक-तिहाई चला जाता है।
2. **E1a का drawdown तो काफ़ी कम हुआ, पर सबसे बुरा हफ़्ता थोड़ा बिगड़ गया** (−10.37% बनाम −9.63%)। तेज़ उछाल वाले हफ़्तों में BTC short भी नुकसान करता है।
3. **Alt shorts को random ranking से बदलने पर नतीजा बहुत बिगड़ता है:** controls का median ≈ $28.3k बनाम E1a का $58.9k। इससे फिर दिखता है कि AI की short ranking random से बेहतर है (E3 से मेल खाता है)।
4. **ईमानदार निष्कर्ष:** जो व्यक्ति कम drawdown के लिए कम मुनाफ़ा स्वीकार करे, उसके लिए E1a जैसा विकल्प सोचा जा सकता है, लेकिन pre-registered gate (≥ 80% final) में यह fail है। नियम बदलकर इसे पास नहीं किया जाएगा। आप यह trade-off चाहें तो वह आपका अलग, नया pre-registered फ़ैसला होगा।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये backtest नतीजे हैं।
