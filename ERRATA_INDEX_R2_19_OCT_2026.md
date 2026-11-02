# Errata index: पुरानी research files में कौन-सी बात अब बदल गई (क्रम 1, 19 अक्टूबर 2026)

**पुरानी files को जानबूझकर नहीं बदला गया।**
- उनके SHA master (भाग 0) और audit verifier (`verify_master_audit.py`, A0 checks) में दर्ज हैं।
- किसी file में "सुधार देखें" का नोट जोड़ने से उसका SHA बदल जाता, और सबूत की chain टूट जाती।
- इसलिए यह अलग index file है। **किसी भी पुरानी file को पढ़ने से पहले यहाँ देखें।** जहाँ दोनों में अंतर हो, वहाँ इस index वाला मान ही मान्य है।

**आधार:**
- `MASTER_INTEGRATED_RESEARCH_17_OCT_2026.md`: भाग 9 (errata), भाग 11 (audit के सुधार); अभी का SHA `07892372…`।
- `REPORT_MASTER_AUDIT_18_OCT_2026.md`: §3.1 और §3.2।

| File (पुरानी, SHA) | पुरानी बात | अब मान्य | स्रोत |
|---|---|---|---|
| S4 `RESEARCH_AI_ARCHITECTURE_MULTI_TF_17_OCT_2026.md` (`b7b18af2…`), भाग 1–2 | Exit AI "AUC 0.505–0.526, असफल" | Step 26 में AUC 0.672 था, पर पैसे में fail (Calmar 0.623 बनाम 0.920) | Master भाग 9 |
| S4 भाग 2 | "1h ≈ 0, खर्च से पहले" | 1h gross +0.33% ≈ taker का 3.9 गुना; median नकारात्मक | Master भाग 9 |
| S4 भाग 1 | "5m/15m maker खर्च से भी कम" | सिर्फ़ 5m; 15m ≈ maker खर्च | Master भाग 9 |
| S2 `RESEARCH_4H_TRADING_LONG_SHORT_17_OCT_2026.md` (`0476ce8f…`), S4 भाग 1–2 | Sealed holdout = 2025-10..2026-09 | साफ़ holdout सिर्फ़ forward data है (17-10-2026 से) | Master भाग 9, D15 |
| Steps 13–27 reports | खर्च 0.25%/fill (0.5% round trip) | Futures ~0.108% (taker 0.05% + BNB, असली account से पुष्टि होने तक), spot ~0.17% | Master भाग 9, audit E4 |
| S3 `FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md` (`0531b065…`) | Futures taker 0.04% (demo API), round trip 0.085% | **Base taker 0.05%**, यानी ~0.108%; 0.085% सिर्फ़ आशावादी scenario | Audit E4 |
| S2, S4 भाग 1 | Trial budget 16–20 या 20–25 | **20** | Master भाग 9 |
| S4 भाग 2 | Risk 40 USDT → notional 1,333 | 1% slippage के साथ ~979 | Master भाग 9 |
| S4 भाग 1 | F7 = exchange पर रखा stop | F7 = 1D shorts पर entry ×1.5 (+1% slippage, 30 दिन cooldown); catastrophe stop नया design है | Master भाग 9 |
| S5 `REPORT_LADDER_PATTERNS_SESSIONS_17_OCT_2026.md` (`a6244819…`) | Fibonacci clustering (pre-registered verdict) | Density से मिलाई गई जाँच में कोई असर नहीं | Master भाग 9 |
| S5 B3 | Daily high/low "Asia में ज़्यादा" | Arcsine null से: Asia सामान्य, असली असर US में | Master भाग 9 |
| S5 | "4h सीढ़ी का अगला कदम ~52% बनाम 48.7%" | **सिर्फ़ UP सीढ़ी में।** DOWN में कोई फ़ायदा नहीं (43.3%, 31.5% बनाम 43.6%) | Audit E5 |
| S6 `REPORT_PROBE_SCALEIN_LADDER_17_OCT_2026.md` (`68cda951…`) | 4h short +0.054 R; 1D long +0.23 R; 1D short +0.105 R (माना हुआ funding) | असली funding पर: 4h short **+0.074**, 4h long +0.101, 1D long +0.213 (spot पर +0.245), 1D short +0.148 | Audit E2, E3 |
| S6 / master 3.4 | 4h long p05 −0.91 | **−0.90** | Audit E1 |
| S6 / master D5 | Test entry: "कमाई ~20–30% कम" | Portfolio पर final −14%, Calmar −18%, DD −9% (trade-off) | Audit E7 |
| Master §6.1 L4 | "DD पर risk घटाना" | **हटाया गया।** Pre-registered test में नुकसानदेह (DD 11.4% → 13.1%) | Audit E6 |
| Master 3.4 | 4h का P3 नहीं दिखाया | 4h long P3 −0.12 R; 4h short P3 +0.12 R (असली funding) | Audit E8 |
| S4 भाग 1–2 citations | Shu et al., Lopez-Lira, Gu-Kelly-Xiu, Alpha Arena, Lo & Remorov | S4 भाग 3 की तालिका के अनुसार | Master भाग 9 |

## Addendum (19 October evening): two swing-pivot errors found during A2
| File | Old | Valid now | Source |
|---|---|---|---|
| S5 ladder study, S6 probe/scale-in, A1 S-LAD/S-DTB (and every study on `legs_all` + `ladder_sessions.points`) | Pivots were taken from the **final** ZigZag list | **Hindsight:** 1.4% of real-time pivot confirmations (102/7,541, 4h) were removed later. Their signals (15 S-LAD + 5 S-DTB in A1) are missing; mean about −0.6 to −0.9 R | A0 amendment 2; `logs/r2_4h_a1/correction/` |
| Same | `points()` ordered legs by `start_time` | **Same-candle ties** (4h 1.5%, 1h 1.6%, 15m 1.1%, 5m 1.1%, 1D 3.3% of legs) mis-ordered labels and known times. In A1: 6 timing errors, 1 spurious signal, 1 changed result | Same |
| A1 S-LAD long | +0.134 R | **+0.128 R** (CI 0.064–0.192) | `A1c_vs_A1.csv` |
| A1 S-LAD short | +0.062 R | **+0.053 R** (CI −0.008–0.115: now touches 0) | Same |
| A1 S-DTB short | +0.070 R | **+0.046 R** | Same |
| A0 §5 features | `move_atr`, `bars`, `done_share_at_confirm` of the "confirming leg" | **Look-ahead** (that leg ends after the signal in 73% of cases) → replaced by the last completed leg; `done_share` removed | A0 amendment 1 |

The S5/S6 descriptive tables were not re-run; the expected effect is small, of the order of 1–3% of rows. From now on, all 4h work uses the real-time timeline (`src/research/r2_realtime_pivots.py`).

- 2026-10-21: `MASTER_INTEGRATED_RESEARCH_17_OCT_2026.md` में भाग 12 जोड़ा गया (सिर्फ़ जोड़, पुराना कुछ नहीं बदला)। भाग 1–11 वाले पहले के bytes का SHA अब भी `07892372…` है, जो A0 protocol में दर्ज है। जाँच: file के शुरू के उतने bytes का SHA। पूरी नई file का SHA `8fba204e…` है।
- 2026-10-21 (बाद में): उसी file में 12.9 जोड़ा गया (सिर्फ़ जोड़)। नया SHA ऊपर दिया गया है। शुरू के bytes का SHA अब भी 07892372… है।
- 2026-10-22: `MASTER_INTEGRATED_RESEARCH_17_OCT_2026.md` line 133 कहती है "Day trading ~97% घाटे में (Taiwan, Brazil)"। सही: 97% Brazil (Chague et al. 2020, 300+ दिन trade करने वाले) का है; Taiwan (Barber, Lee, Liu, Odean) में 1% से कम लगातार कमाते हैं और हर साल ~80% हारते हैं। मूल file नहीं बदली; सुधार `RESEARCH_CROWD_EMOTION_CANDLES_22_OCT_2026.md` §9 A3 में।
