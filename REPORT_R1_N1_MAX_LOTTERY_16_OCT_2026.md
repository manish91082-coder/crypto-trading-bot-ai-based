# Round 1, N1: "lottery" (MAX) filter (16 अक्टूबर 2026)

**फ़ैसला: N1a FAIL, N1b FAIL।** इसे अपनाया नहीं जाएगा।

⚠ **Disclosure (protocol में पहले से दर्ज):** यह pattern 16 अक्टूबर को एक descriptive जाँच में पहले ही देखा जा चुका था। इसलिए यहाँ PASS होना भी कमज़ोर सबूत होता। नतीजा FAIL आया है।

## सबूत
- **Run:** `python src/pipeline_1d/r1_run.py N1` (3,662 सेकंड), stdout `run_N1_stdout.txt`
- **Claims:** `claims_N1.json`
- **फ़ैसलों का record:** `decisions_N1a.csv`, `decisions_N1b.csv`
- **Verifier** (`verify_N1_stdout.txt`):
  - V1 PASS: protocol, engine और runner के hash मिलते हैं।
  - V2 PASS: सारे आँकड़े और G1–G5 दोबारा निकाले गए।
  - V3 PASS:
    - जो coin रोका गया, वह उस दिन नया ख़रीदा नहीं गया (4,332 longs जाँचे)।
    - "रोका गया" होना ठीक उसी हालत में है जब coin MAX7 के top 20% में हो (percentile > 0.8)।
    - 40 rows का MAX7 raw daily closes से दोबारा निकाला गया।

## नियम
- **N1a:** हर फ़ैसले पर, ranked coins में से जो पिछले 7 दिनों की सबसे बड़ी एक-दिनी तेज़ी (MAX7) के top 20% में हैं, उन्हें नया long नहीं मिलता; अगली rank वाला coin उसकी जगह लेता है। Shorts वही रहते हैं।
- **N1b:** N1a के साथ, short के लिए AI की सबसे नीची 10 ranks में से top-MAX वाले coins पहले चुने जाते हैं।

## नतीजे
| | F7 RS (baseline) | **N1a** | **N1b** |
|---|---|---|---|
| Final ($10k से) | **$88,401** | $66,365 | $62,602 |
| Max DD | 21.37% | **19.65%** | 22.98% |
| 2022 | **+36.54%** | +28.65% | +26.49% |
| Long PF / payoff | 1.22 / **1.57** | 1.23 / 1.537 | 1.24 / 1.537 |
| Short PF / payoff | 1.07 / 0.81 | 1.07 / 0.813 | 1.091 / 0.769 |
| Short P&L (sleeves का औसत) | **$26,227** | $18,095 | $19,533 |
| रोकी गई long entries | — | 1,254 | 1,254 |
| सबसे बुरा हफ़्ता | −9.63% | **−8.96%** | −9.60% |
| DSR (N = 91) | — | 0.755 | 0.707 |

**10 controls (उतनी ही long entries random रोकी गईं):** long PF 1.209 से 1.250 के बीच, median 1.2385।

## Gates
| Gate | शर्त | N1a | N1b |
|---|---|---|---|
| G1 | Long PF > 1.22 **और** payoff > 1.57 | ❌ (payoff 1.537) | ❌ (payoff 1.537) |
| G2 | DD ≤ 21.37% | ✅ | ❌ |
| G3 | Final ≥ F7 (N1a) / > F7 (N1b) | ❌ | ❌ |
| G4 | 2022 > 0 | ✅ | ✅ |
| G5 | Long PF > control median | ❌ (1.23 < 1.2385) | ✅ |
| **फ़ैसला** | | **FAIL** | **FAIL** |

## मेरी व्याख्या
1. **Descriptive pattern पैसे में नहीं बदला।** High-MAX coins को रोकने से long PF लगभग वही रहा (1.22 से 1.23) और payoff घटा। Random तरीके से उतनी ही entries रोकने पर भी long PF इसी के आसपास (1.21–1.25) रहता है, यानी MAX filter random रोक से बेहतर नहीं निकला।
2. **AI पहले से इस असर का ज़्यादातर हिस्सा पकड़ता है।** पहले की जाँच में AI score और MAX7 का correlation −0.38 था। इसलिए filter लगाने पर ज़्यादातर अच्छे trend वाले coins भी कट जाते हैं।
3. **पूरे system पर नुकसान:** final $88k से गिरकर $62–66k।
4. **ईमानदार निष्कर्ष:** हमारे 1D system में "lottery effect" अलग से कोई फ़ायदा नहीं जोड़ता। शोध-पत्रों का monthly-frequency नतीजा हमारे AI ranking के ऊपर लागू नहीं होता।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये backtest नतीजे हैं।
