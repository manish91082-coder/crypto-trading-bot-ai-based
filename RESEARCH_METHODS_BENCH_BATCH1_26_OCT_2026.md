# Methods bench, Batch 1: trend (A1) और oscillator (A2) indicators, BTC 2020 – 2026-09 (26 अक्टूबर 2026)

> **सार:**
> - 189 signal configs × 3 exits = **567 primary configs** test हुए, futures fees के साथ।
> - **एक भी config "edge" के gates पास नहीं कर सका (0/567)।**
> - Holdout (2025-01 – 2026-09) के mean का 95% दायरा, हर config के लिए 0 से नीचे तक गया (G1: 0/567)।
> - Multiple-testing को सुधारने वाली Sharpe कसौटी (DSR) भी 0/567 ने पास की।
>
> **Evidence:**
> - Protocol `logs/research_methods_bench/MASTER_BENCH_PROTOCOL_PREREGISTERED.md` (SHA `0ee7aff8…`) और Amendment 1 (`626f670a…`), दोनों run से पहले lock।
> - Code SHA `46b16cd6…`।
> - Verifier `src/audits/verify_methods_batch1.py`: **7/7 PASS**।
>   - 300 random signals अपने code से दोबारा बनाए;
>   - trades loop से replay किए;
>   - daily → monthly → yearly का मिलान;
>   - ranking दोबारा गिनी;
>   - random control, stress और delay जाँचे।
> - यह काम 9 महीने वाली study और non-price study से पूरी तरह अलग है।

## 1. क्या test हुआ

- **Methods:** A1 (trend: SMA/EMA, crossovers, ADX, KST, linear-regression slope, Renko, …) और A2 (oscillators: RSI-variants, Stoch-RSI, Connors RSI, MFI, Fisher, Ultimate, Awesome, Coppock, TSI, Force Index, …)।
  - हर method 15m, 1h और 4h scale पर चला।
  - Oscillators के दो रूप थे: "fade" (उल्टा) और "follow" (साथ)।
- **Exits:**
  - **X1:** ±2σ (दिन की volatility) triple barrier, 7 दिन की सीमा;
  - **X2:** ±1% triple barrier;
  - **X3:** उल्टा signal आने पर reversal।
- **Periods:** D 2020–2023, V 2024, H 2025-01 – 2026-09।
  - H सभी configs के लिए एक साथ, एक बार खुला।
  - हर दिन की entry `batch1_daily.parquet` में है (5,590,620 rows, कोई दिन skip नहीं)। साथ में `batch1_monthly.csv` और `batch1_yearly.csv` हैं।
- **Edge कहलाने के gates** (सब पास होने चाहिए):

| Gate | शर्त | कितने पास (567 में) |
|---|---|---|
| G1 | H mean के 95% CI की निचली सीमा > 0 | **0** |
| G2 | H में ≥ 100 trades | 537 |
| G3 | H mean ≥ random-entry control का 95th percentile (top 20 पर) | 12 |
| G4 | 2025 और 2026, दोनों में mean > 0 | 18 |
| G5 | DSR > 0.95 (N = 1,726, यानी अब तक test हुए सारे configs) | **0** |
| G6 | 2× fees और 1-bar देरी पर भी H mean > 0 | 53 |

## 2. Family का सार (प्रति trade औसत net, % में)

| Family | Configs | D | V | H | पूरा 2020–2026 |
|---|---|---|---|---|---|
| A1 trend | 207 | +0.040 | −0.002 | −0.108 | **−0.006** |
| A2 oscillators | 360 | −0.096 | −0.093 | −0.093 | **−0.095** |

- 567 में से सिर्फ़ 26% configs पूरे दौर में positive रहे।
- 19 configs तीनों periods (D, V, H) में positive रहे।
  - अगर हर period में positive या negative होना संयोग जितना (50–50) होता, तो लगभग 567 / 8 ≈ 71 configs ऐसे दिखते।
  - यानी यह संख्या संयोग से भी **कम** है, क्योंकि fees हर config को नीचे खींचती हैं।

## 3. Top 20 (protocol की ranking: H mean, CI, positive महीने, drawdown, PF, consistency, stress, delay)

सभी नंबर प्रति trade औसत net % में हैं। "H+ महीने" 21 में से हैं।

| # | Config | Exit | D | V | H | H trades | H CI निचली सीमा | H+ महीने | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Fisher fade 4h | X3 | −0.17 | −1.25 | +0.76 | 134 | −0.02 | 15 | −0.92 | +0.68 | +0.47 | −1.24 | −1.25 | +1.00 | +0.53 |
| 2 | ConnorsRSI follow 4h | X3 | +0.44 | +1.00 | +0.75 | 81 | −0.44 | 13 | +1.05 | −0.72 | +0.20 | +1.18 | +1.00 | +0.34 | +1.48 |
| 3 | KST 1h | X1 | +0.18 | −0.25 | +0.46 | 178 | −0.16 | 12 | −0.08 | −0.63 | +1.36 | +0.01 | −0.22 | −0.02 | +1.03 |
| 4 | Ultimate Osc fade 4h | X1 | −0.28 | +0.26 | +1.02 | 39 | −0.46 | 13 | −1.60 | +1.34 | +1.30 | −1.52 | +0.26 | +0.62 | +1.67 |
| 5 | ConnorsRSI follow 4h | X2 | −0.09 | −0.11 | +0.02 | 409 | −0.07 | 14 | −0.06 | −0.16 | −0.08 | −0.01 | −0.11 | −0.06 | +0.11 |
| 6 | StochRSI follow 4h | X3 | −0.07 | +0.25 | +0.16 | 220 | −0.25 | 12 | +0.13 | −0.91 | +0.58 | +0.07 | +0.25 | −0.15 | +0.55 |
| 7 | LinReg slope 20, 1h | X1 | +0.14 | −0.16 | +0.31 | 178 | −0.33 | 11 | +0.50 | −0.68 | +0.48 | +0.20 | −0.19 | −0.30 | +0.84 |
| 8 | EMA 20×50, 4h | X3 | +0.03 | +0.13 | +0.26 | 134 | −0.45 | 10 | +0.57 | −0.52 | −0.32 | +0.44 | +0.22 | −0.10 | +0.85 |
| 9 | Awesome Osc follow 1h | X1 | +0.04 | −0.01 | +0.25 | 178 | −0.40 | 13 | +0.38 | −0.44 | −0.05 | +0.24 | −0.04 | −0.19 | +0.79 |
| 10 | MFI follow 15m | X1 | +0.39 | +0.09 | +0.28 | 171 | −0.38 | 13 | +0.21 | +0.45 | +0.89 | +0.08 | +0.06 | −0.45 | +1.48 |
| 11 | MFI fade 1h | X1 | −0.78 | −0.55 | +0.44 | 147 | −0.37 | 13 | −0.71 | −1.90 | −0.34 | −0.18 | −0.55 | +0.74 | +0.12 |
| 12 | Coppock fade 4h | X1 | −0.46 | −0.33 | +0.40 | 178 | −0.25 | 11 | −1.28 | −0.51 | +0.62 | −0.64 | −0.36 | +0.74 | −0.15 |
| 13 | Force Index follow 1h | X1 | +0.23 | −0.11 | +0.15 | 178 | −0.50 | 12 | +0.70 | −0.36 | +0.51 | +0.05 | −0.08 | −0.06 | +0.38 |
| 14 | Coppock follow 1h | X1 | +0.21 | −0.27 | +0.27 | 178 | −0.37 | 11 | +0.58 | −0.69 | +0.65 | +0.28 | −0.31 | −0.34 | +0.81 |
| 15 | ADX 4h | X3 | +0.02 | −0.07 | +0.25 | 124 | −0.54 | 11 | +0.68 | −1.81 | −0.17 | +1.26 | −0.07 | +0.23 | +0.27 |
| 16 | TSI fade 15m | X1 | −0.40 | +0.28 | +0.17 | 178 | −0.44 | 12 | −1.13 | −0.47 | +0.04 | −0.05 | +0.26 | +0.70 | −0.46 |
| 17 | Ultimate Osc follow 1h | X1 | +0.52 | −0.60 | +0.14 | 105 | −0.67 | 13 | +1.34 | +0.48 | +0.68 | −0.63 | −0.60 | +0.36 | −0.21 |
| 18 | SMA 50, 1h | X1 | +0.21 | +0.19 | +0.09 | 178 | −0.54 | 11 | +0.29 | +0.16 | +0.18 | +0.21 | +0.16 | −0.16 | +0.49 |
| 19 | ConnorsRSI follow 1h | X3 | +0.13 | +0.42 | +0.13 | 252 | −0.26 | 10 | +0.35 | +0.12 | +0.17 | −0.11 | +0.42 | +0.02 | +0.22 |
| 20 | Awesome Osc fade 4h | X1 | −0.29 | −0.28 | +0.38 | 178 | −0.27 | 11 | −1.37 | −0.59 | +1.00 | −0.20 | −0.31 | +0.75 | −0.19 |

**कैसे पढ़ें:**
- Ranking H पर हुई है, इसलिए top 20 वे configs हैं जो **2025–26 में अच्छे दिखे।**
- ज़्यादातर D (2020–23) या V (2024) में negative थे, जैसे #1 Fisher fade: D −0.17, V −1.25।
- यानी इनका ऊपर होना "किस्मत से सही दौर" जैसा है, स्थिर edge नहीं।
- **#2 ConnorsRSI follow 4h (X3)** तीनों periods में positive रहा: +0.44, +1.00, +0.75। फिर भी:
  - H में सिर्फ़ 81 trades थे;
  - CI की निचली सीमा −0.44 है;
  - 2021 में −0.72 रहा;
  - DSR (1,726 tests के बाद) fail हुआ।
  - इसलिए यह **साबित edge नहीं** है। इसे ज़्यादा से ज़्यादा forward (paper) पर देखने लायक कहा जा सकता है।

**पूरी जानकारी:** पूरी ranking `batch1_ranking.csv` में है। Top 20 के H trades `batch1_H_trades_*.csv` में हैं, और सारे gates `batch1_gates_all.csv` में।

## 4. आज की चारों studies का एक साथ नतीजा

| Study | कितने नियम | Fees के बाद साबित edge |
|---|---|---|
| Methods bench, Batch 1 (indicators) | 567 | 0 |
| 9 महीने का oracle + v1 + Part C/D | 5 + 120 + 1 | 0 |
| Non-price NP1–NP3 | 14 + 24 + 48 | 0 |
| NP4 (24h premium, holdout) | 2 | 0 |

**ईमानदार निष्कर्ष:**
- BTC पर public data (भाव, indicators, funding, OI, order book) से बने short और medium अवधि के trading नियमों में, हमारी fee level पर, **अब तक कोई साबित edge नहीं मिला।**
- Batch 2–7 (catalog के बाकी methods) अभी बाकी हैं। उनमें हर batch का अपना protocol lock होगा।
- पर 2025–26 का holdout अब Batch 1 और NP4 में इस्तेमाल हो चुका है। आगे के batches के लिए **forward (नया) data** ही सबसे साफ़ test होगा।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
