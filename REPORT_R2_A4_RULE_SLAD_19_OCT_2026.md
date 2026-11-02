# A4 (बिना AI): सीढ़ी-long signal के exits, entry और position size (19 अक्टूबर 2026, रात)

**आपका चुनाव:** विकल्प (b), फिर (c)।
- **(b) यह report है।**
- **(c) ज़्यादा coins पर AI (T14) अभी background में चल रहा है।** 135 coins का store बन रहा है; उसके बाद model चलेगा।

**तरीका:**
- Protocol `caf7dcee…`, run से पहले lock।
- Trials T06–T13 run से पहले registry में दर्ज (20 में से 13 इस्तेमाल; T14 के साथ 14)।
- Independent verifier: **6/6 PASS।**

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

## 1. Exit grid (S-LAD long, 10 coins, 887 dev trades, mark-to-market drawdown)
| Trailing | Time stop | Net R/trade | MTM Calmar (dev) | P1 | P2 | P3 (सिर्फ़ report) |
|---|---|---|---|---|---|---|
| 3 ATR | 60 bar (default) | 0.128 | 0.79 | 0.71 | 1.72 | **−0.68** |
| 3 ATR | 120 | 0.135 | 0.95 | 0.94 | 1.38 | −0.68 |
| 3 ATR | कोई नहीं | 0.137 | 0.91 | 0.89 | 1.38 | −0.68 |
| **4 ATR** | **60** | **0.166** | **1.04** | 1.10 | 1.48 | +0.27 |
| 4 ATR | 120 | 0.160 | 0.86 | 0.96 | 0.92 | +0.22 |
| 4 ATR | कोई नहीं | 0.156 | 0.78 | 0.85 | 0.87 | +0.28 |

**Pre-registered plateau नियम:**
- सबसे अच्छा config (4, 60) तभी चुना जाता जब उसके हर पड़ोसी का Calmar उसके 80% से ऊपर होता।
- (3, 60) का Calmar 76% था, इसलिए **default (3, 60) ही रहा।**
- यह नियम एक अकेले "भाग्यशाली" नतीजे को चुनने से बचाने के लिए है।

## 2. Entry
| तरीका | Net R | Calmar dev / P1 / P2 | फ़ैसला |
|---|---|---|---|
| V0 taker (default) | 0.128 | 0.789 / 0.714 / 1.716 | — |
| V2 test entry (25/25/50) | 0.099 | 0.838 / 0.896 / 0.971 | ❌ (P2 में कमज़ोर) |
| **Maker entry** (1 घंटे का post-only) | 0.126 | 0.797 / 0.717 / 1.722 | ✅ (बहुत कम अंतर से) |

- **Maker fill rate: 96.6%।**
- जो order भरे, उनका net R 0.095 रहा; जो नहीं भरे, उनका 0.059। Adverse selection उलटी दिशा में है: न भरने वाले orders ज़्यादा ख़राब निकले।

## 3. Gates (final config: 3 ATR, 60 bar, maker)
| Gate | नतीजा | पास? |
|---|---|---|
| **PBO < 0.30** | **0.84** | ❌ |
| Random entry से बेहतर (p95) | Calmar 0.80 बनाम 0.45 | ✅ |
| खर्च 1.5× / 2× / stop slippage 0.3% | net +0.122 / +0.117 / +0.089 R | ✅ |
| P1 और P2 में Calmar > 0 | 0.72 / 1.72 | ✅ |
| DSR ≥ 0.95 | 0.99 | ✅ |

**Pre-registered फ़ैसला: A4 FAIL (PBO)।**

**ईमानदार पढ़ाई:**
- PBO 0.84 का मतलब है: 6 exits में से जो पिछले data पर सबसे अच्छा दिखता है, वह आगे के data पर ज़्यादातर बार median से नीचे चला जाता है। **Exit tuning शोर है।**
- **पर सीढ़ी-long signal खुद,** default exit के साथ, random entry से साफ़ बेहतर है (0.80 बनाम 0.45), खर्च बढ़ने पर भी टिकता है, और DSR 0.99 है। यानी signal में कुछ असली है। पर protocol का gate PBO भी माँगता है, इसलिए नियम के अनुसार FAIL।
- **आख़िरी साल (P3) में default config घाटे में रहा** (Calmar −0.68)। यह audit वाली चेतावनी दोहराता है।

## 4. Position size (सिर्फ़ जानकारी, आपका फ़ैसला)
| Risk/trade | Final (8,000 से) | CAGR | MTM DD | Calmar |
|---|---|---|---|---|
| 0.25% | 9,891 | 3.8% | 4.9% | 0.78 |
| **0.5%** | 12,117 | 7.6% | 9.5% | 0.80 |
| 0.75% | 14,712 | 11.4% | 14.0% | 0.81 |
| 1.0% | 17,709 | 15.1% | 18.3% | 0.82 |

Calmar लगभग स्थिर है। ज़्यादा risk लेने पर कमाई और DD दोनों लगभग अनुपात में बढ़ते हैं।

## 5. रास्ते में पकड़ी गई गलतियाँ (सब दर्ज: `logs/r2_4h_a4/CODE_CHANGES_AFTER_LOCK.md`)
1. Cost stress सिर्फ़ "V0 taker" के लिए लिखा था, जबकि final config maker निकला। इससे gate artefact की वजह से FAIL दिख रहा था। ठीक करके दोबारा चलाया: PASS।
2. Verifier timestamp से bar ढूँढ रहा था, और data के इकलौते gap (2020-02-19, Binance outage, सिर्फ़ 1 trade पर असर) पर अटक गया। उसे bar-index convention पर लाया।
3. **PBO floating-point ties:** दोनों तरफ़ की matrix 3e-16 तक बराबर थी, फिर भी नतीजा 0.870 बनाम 0.879 आया। Sharpe को 12 decimal पर round करके rank किया, अब दोनों तरफ़ 0.844। फ़ैसला नहीं बदला।
4. **Sanity checks जो पास हुए:**
   - (3, 60) A1c को हूबहू दोहराता है।
   - V2 पुरानी S6 study से 1,017 trades पर 1e-15 तक मेल खाता है।
