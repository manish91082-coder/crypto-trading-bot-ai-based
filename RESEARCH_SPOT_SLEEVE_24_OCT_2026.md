# Spot sleeve: 10–20–30% capital से spot पर "turn up पर खरीदो, hold करो, फिर बेचो" की verified research (24 अक्टूबर 2026)

> **Discipline:**
> - Protocol नतीजों से पहले lock किया गया: `logs/research_spot_sleeve/SPOT_SLEEVE_PROTOCOL_PREREGISTERED.md`, SHA `0fe62438…`।
> - Code `src/research/spot_sleeve_study.py` (`021d5756…`) है।
> - अलग verifier `src/audits/verify_spot_sleeve.py` (`be11b16c…`) के **4/4 PASS**।
> - नतीजे: `logs/research_spot_sleeve/SPOT_SLEEVE_RESULTS.json` (`4d2c422f…`)।
> - सिर्फ़ historical simulation। कोई order या deploy नहीं हुआ।
> - मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। Mix table research scenarios हैं, सलाह नहीं।

---

## 0. एक नज़र में

| सवाल | Verified जवाब |
|---|---|
| Spot पर खरीदकर hold करने का कोई ऐसा नियम है जिसने **हर तरह के market** में (2018 का bear, 2020–23, 2024–26) buy-and-hold से बेहतर risk-adjusted नतीजा दिया, **और** जो random timing से साफ़ बेहतर साबित हुआ? | **नहीं।** 6 में से **किसी भी** strategy ने तीनों pre-registered gates पास नहीं किए |
| सबसे भरोसेमंद नियम कौन सा निकला? | **S1: BTC तभी रखो जब price उसके 200 दिन के average से ऊपर हो, वरना USDT।** इसने G1 (हर अवधि में BTC hold जितना या बेहतर Sharpe, और कम से कम 10 points कम drawdown) और G3 (हर अवधि में profit) **पास** किए। G2 में random timing से बेहतर होने का percentile **78.5%** रहा, जबकि ज़रूरत ≥ 90% की थी। इसलिए इसे "साबित edge" नहीं कह सकते |
| इसमें profit कहाँ से आता है? | **कुछ बड़े trend legs से।** 27 trades में सिर्फ़ 26% जीते, पर **औसत जीत +70% और औसत हार सिर्फ़ −3.5%**। सबसे बड़ी हार −8.9% थी। यह पिछली study के DCA का बिल्कुल उल्टा है (वहाँ 97% जीत थी, पर हारें विनाशकारी थीं) |
| असली फ़ायदा? | **गिरावट से बचाव।** 2018–19 में BTC hold ने −19.7% सालाना दिया (drawdown −70%), जबकि S1 ने **+5.4%** (drawdown −42%)। 2024–26 में drawdown −53% की जगह **−32%** रहा |
| आपका "बड़ी गिरावट के बाद turn up पर खरीदो" (S6) वाला विचार? | **सबसे कमज़ोर।** 2020–26 में CAGR सिर्फ़ +2.4%, random timing से भी नीचे (33वाँ percentile) |
| Top 5 momentum coins (S5)? | 2020–23 में बहुत अच्छा (+125% सालाना), पर **2024–26 में −17.4% सालाना, drawdown −72%**। भरोसे लायक नहीं |
| 10/20/30% हिस्सा ECO के साथ जोड़ें तो? | ECO (backtest) के साथ S1 को 10–30% पर जोड़ने से drawdown थोड़ा घटा (−18.7% से −17.2%), पर CAGR और Sharpe भी घटे। यानी **return के लिए नहीं, सिर्फ़ थोड़ी सुरक्षा के लिए** (§4) |

---

## 1. Rules कहाँ से आए (literature, नतीजे देखने से पहले तय)

- **Detzel, Liu, Strauss, Zhou & Zhu (2021), Financial Management:** Bitcoin का price उसके moving average के मुकाबले कहाँ है, इससे in-sample और out-of-sample दोनों में future return का अनुमान लगता है। MA timing rule ने buy-and-hold से बेहतर Sharpe दिया।
- **Liu & Tsyvinski (2021), Review of Financial Studies:** crypto में मज़बूत time-series momentum है, यानी जो ऊपर जा रहा है वह कुछ समय और ऊपर जाता है।
- **Liu, Tsyvinski & Wu (2022), Journal of Finance:** crypto returns को market, size और **momentum** factors समझाते हैं।
- **Survivorship की चेतावनी:** 2026 के एक paper (Grobys et al.) के मुताबिक़ सिर्फ़ टिके रहे coins पर momentum नहीं दिखता। इसीलिए हमारे S5 test में **delisted coins भी** शामिल किए गए।
- Windows वही रखे जो आम तौर पर इस्तेमाल होते हैं (200, 50/200, 28 दिन, top 5 of 20)। **कोई parameter खोजा या optimize नहीं किया गया।**

## 2. क्या test किया

- **Data:** BTC और ETH का 2017-08 से 2026-09 तक का daily data (pre-2020 वाली files + universe_all)। S5 के लिए 679 spot coins, delisted समेत। सब files का SHA manifest में दर्ज है।
- **नियम:** फ़ैसला close पर, खरीद/बिक्री अगले दिन के open पर। Fee 0.1% प्रति तरफ़, stress test में 0.25%। Cash पर कोई ब्याज नहीं।

| नाम | नियम |
|---|---|
| B0 | BTC खरीदो और रखो (benchmark) |
| B1 | आधा BTC, आधा ETH, हर महीने rebalance |
| **S1** | BTC का close > 200-day average → BTC रखो, वरना USDT |
| S2 | आधे में S1 (BTC), आधे में वही नियम ETH पर |
| S3 | BTC: 50-day average > 200-day average (golden cross) → रखो |
| S4 | हर सोमवार: BTC पिछले 28 दिन में ऊपर गया → हफ़्ते भर रखो |
| S5 | हर सोमवार, अगर BTC > 200-day average: 20 सबसे liquid coins में से पिछले 28 दिन के top 5 बराबर हिस्से में रखो |
| S6 (आपका विचार) | BTC अपने 1 साल के high से ≥ 30% नीचे हो **और** 50-day average को ऊपर cross करे → खरीदो। Close < 50-day average → बेचो |

- **अवधियाँ:** P0 2018-03 → 2019-12 (bear market), dev 2020-07 → 2023-12, holdout 2024-01 → 2026-09, full 2020-07 → 2026-09।
- **Random control:** हर timing rule के अंदर और बाहर रहने वाले दिनों के टुकड़ों को 200 बार random क्रम में रखा, ताकि market में रहने का कुल समय और trades की संख्या वही रहें। इससे पता चलता है कि **timing का कमाल है या सिर्फ़ कम समय market में रहने का।**

## 3. नतीजे

### 3.1 हर अवधि में: 10,000 → final (CAGR, max drawdown, Sharpe)

| | P0 2018–19 (bear) | Dev 2020–23 | Holdout 2024–26 | Full 2020–26 |
|---|---|---|---|---|
| B0 BTC hold | 6,275 (−19.7%, −70%, 0.03) | 46,226 (54.5%, −77%, 1.00) | 19,757 (26.2%, −53%, 0.73) | 91,420 (42.3%, −77%, 0.90) |
| B1 BTC/ETH hold | 3,329 (−43.6%, −82%, −0.36) | 77,922 (79.0%, −76%, 1.18) | 16,115 (17.4%, −60%, 0.57) | 125,697 (49.6%, −76%, 0.95) |
| **S1 BTC SMA200** | **10,289 (+5.4%, −42%, 0.34)** | **48,560 (56.7%, −64%, 1.18)** | **18,147 (22.3%, −32%, 0.74)** | **88,208 (41.5%, −64%, 1.02)** |
| S2 BTC+ETH SMA200 | 8,210 (−7.4%, −44%, 0.02) | 109,202 (97.1%, −53%, 1.46) | 17,709 (21.5%, −30%, 0.71) | 190,926 (59.9%, −53%, 1.18) |
| S3 golden cross | 10,259 (+5.3%, −43%, 0.34) | 47,049 (55.3%, −57%, 1.13) | 14,562 (12.9%, −40%, 0.51) | 68,583 (35.9%, −57%, 0.91) |
| S4 28-day momentum | 10,122 (+4.5%, −53%, 0.34) | 40,933 (49.6%, −64%, 1.09) | 15,783 (16.3%, −34%, 0.62) | 64,670 (34.8%, −64%, 0.92) |
| S5 top 5 momentum | n/a | 171,865 (125.4%, −64%, 1.40) | **5,921 (−17.4%, −72%, 0.04)** | 109,832 (46.7%, −72%, 0.88) |
| S6 "turn up after fall" | 13,596 (+18.4%, −48%, 0.60) | 9,666 (−1.0%, −58%, 0.09) | 12,028 (7.0%, −14%, 0.55) | 11,627 (2.4%, −58%, 0.22) |

**Fee stress (0.25%) का असर:** S1 full 81,456, S2 180,447। Ranking नहीं बदली।

### 3.2 Gates (pre-registered)

| Strategy | G1: हर अवधि में Sharpe ≥ BTC hold, और DD ≥ 10 points कम | G2: random timing से ≥ 90% बेहतर | G3: हर अवधि में profit | Candidate? |
|---|---|---|---|---|
| **S1** | ✅ | ❌ (78.5%) | ✅ | ❌ |
| S2 | ❌ (holdout Sharpe 0.71 < 0.73) | ❌ (BTC leg 78.5%; ETH leg 97.5%) | ❌ (2018–19 में घाटा) | ❌ |
| S3 | ❌ | ❌ (71.5%) | ✅ | ❌ |
| S4 | ❌ | ❌ (83%) | ✅ | ❌ |
| S5 | ❌ | ❌ | ❌ | ❌ |
| S6 | ❌ | ❌ (33%) | ❌ | ❌ |

- **Deflated Sharpe (जानकारी के लिए, 6 trials):** S2 0.974, S1 0.945, S4 0.910, S3 0.905, S5 0.892, S6 0.335।

### 3.3 Profit आता कैसे है: S1 के trades (2020-07 → 2026-09)

| माप | मूल्य |
|---|---|
| Trades | **27** |
| जीते | सिर्फ़ 7 (26%) |
| **औसत जीत** | **+70.3%** |
| **औसत हार** | **−3.5%** |
| सबसे बड़ी जीत | **+300%** (2020-07 → 2021-05) |
| सबसे बड़ी हार | −8.9% |
| Market में समय | 59% |

**बड़े legs:**

| अवधि | Return |
|---|---|
| जुलाई 2020 → मई 2021 | +300% |
| जनवरी → अगस्त 2023 | +33% |
| अक्टूबर 2023 → जुलाई 2024 | **+100%** |
| अक्टूबर 2024 → मार्च 2025 | +22% |
| अप्रैल → अक्टूबर 2025 | +14% |
| अगस्त 2026 से खुला | +20.5% |

**छोटी हारें (whipsaw):** जब price 200-day line के आसपास ऊपर-नीचे होता है, जैसे अगस्त–दिसंबर 2021 या मार्च 2025, तब 2–9% की कई छोटी हारें होती हैं।

**सीख:** spot में पैसा "हर trade जीतने" से नहीं आता। **बड़े uptrend को पूरा पकड़ने और downtrend में बाहर रहने** से आता है। पिछली study में देखा था कि 97% जीत वाला DCA इसीलिए डूबा क्योंकि उसमें हार की कोई सीमा नहीं थी। S1 में हार अपने-आप छोटी रहती है, क्योंकि price average के नीचे जाते ही बाहर निकल जाते हैं।

## 4. ECO के साथ 10/20/30% (2021-01 → 2026-09; ECO = backtest series)

**10,000 → final (CAGR, max DD, Sharpe):**

| Spot हिस्सा | Spot का ECO से correlation | 0% (सिर्फ़ ECO) | 10% | 20% | 30% |
|---|---|---|---|---|---|
| B0 BTC hold | 0.29 | 110,026 (51.0%, −18.7%, 2.10) | 103,095 (49.1%, −20.4%, 2.02) | 95,105 (46.9%, −22.9%, 1.83) | 86,360 (44.3%, −29.0%, 1.59) |
| **S1** | 0.29 | 110,026 | 100,441 (48.4%, **−18.0%**, 2.06) | 90,747 (45.7%, **−17.3%**, 1.94) | 81,121 (42.7%, **−17.2%**, 1.76) |
| S2 | 0.30 | 110,026 | 107,282 (50.2%, −19.1%, 2.08) | 103,641 (49.2%, −19.9%, 1.96) | 99,208 (47.9%, −24.9%, 1.78) |
| S5 | 0.21 | 110,026 | 118,085 (52.7%, −17.0%, 2.07) | 122,197 (53.5%, −16.6%, 1.86) | 122,216 (53.4%, −24.2%, 1.61) |
| S6 | 0.16 | 110,026 | 90,363 (46.0%, −17.3%, 2.08) | 73,775 (41.0%, −16.2%, 1.90) | 59,871 (36.0%, −17.5%, 1.90) |

**पढ़ने का तरीका (ईमानदारी से):**
- ECO का backtest बहुत अच्छा दिखता है (Sharpe 2.1)। इसलिए कोई भी spot हिस्सा जोड़ने पर कुल **Sharpe घटता है।** ध्यान रहे, ECO का live सबूत अभी कुछ ही दिनों का है।
- **S1** जोड़ने से drawdown थोड़ा सुधरता है (−18.7% से −17.2/−17.3%), पर return घटता है। यानी यह "बीमा" जैसा है, कमाई बढ़ाने वाला नहीं।
- **S5** जोड़ने पर return बढ़ता दिखता है, पर वह 2024–26 के holdout में बुरी तरह fail हुआ (−17% सालाना)। इसलिए यह फ़ायदा भरोसे लायक नहीं।
- **Overlap:** ECO में पहले से 1D trend sleeve (long और short) और N1 sleeve A (spot-जैसा long trend) मौजूद हैं, और correlation 0.29 है। S1 कुछ हद तक वही काम दोहराता है जो ECO पहले से कर रहा है।

## 5. तो spot पर क्या करना चाहिए? (evidence के हिसाब से, सलाह नहीं)

1. **Averaging down बिना stop loss (पिछली study) और "बड़ी गिरावट के बाद turn up पर खरीदो" (S6):** दोनों को **न अपनाएँ।** Data दोनों के खिलाफ़ है।
2. **अगर फिर भी spot हिस्सा चाहिए,** तो सबसे बचाव-लायक विकल्प **S1** है:
   - BTC तभी रखो जब वह 200-day average से ऊपर हो;
   - हिस्सा 10–20% रखें;
   - हर दिन UTC close पर देखें, अगले open पर trade करें।
   - **क्यों:** इसने 2018 के bear में पैसा बचाया और हर अवधि में profit दिया। हार छोटी रहती है (max −8.9%), और बड़े bull legs पकड़े जाते हैं।
   - **क्यों अभी live नहीं:**
     - Random timing से बेहतर होने का सबूत 90% की शर्त पर पूरा नहीं हुआ (78.5%)। इसका फ़ायदा काफ़ी हद तक "कम समय market में रहने" से भी समझाया जा सकता है।
     - ECO के साथ जोड़ने पर Sharpe घटता है।
3. **अगला ईमानदार कदम (आपकी हाँ पर):** S1 का 10% वाला **forward paper test**, बिल्कुल PaperN1 की तरह: नया protocol, SHA lock, VM पर रोज़ एक record, verifier, और day-90 review। तभी live पैसा।
   - S1 हर साल सिर्फ़ ~4 trades करता है। इसलिए 90 दिन में ज़्यादा trades नहीं आएँगे, और सबूत धीरे-धीरे बनेगा। यह बात पहले से पता होनी चाहिए।

## 6. सीमाएँ

- **Daily bars।** Spread या slippage अलग से नहीं जोड़ा, fee में ही माना गया (0.1%; stress 0.25%)।
- **ECO mix:** ECO की series backtest है।
- **P0 (2018–19):** BTC/ETH के अलावा coins का pre-2020 data इस्तेमाल नहीं किया, इसलिए S5 का P0 नहीं है।
- **Gate G2 सख़्त है (90%)।** S1 का 78.5% "कुछ संकेत" है, सबूत नहीं।
- **Grobys et al. 2026** का citation search summary से है, पूरा paper नहीं पढ़ा।

## 7. Verification

| Check | नतीजा |
|---|---|
| V1 | 682 input files के SHA मेल खाते हैं ✅ |
| V2 | S1, S3, S4, S6 × 4 अवधियाँ: अपने loops से दोबारा गिनी गईं। Final equity 1e-6 तक बराबर, trades की गिनती बराबर ✅ |
| V3 | S5 की holdings 20 random सोमवारों पर दोबारा गिनी गईं (11 पर असली holdings थीं), सब मेल ✅ |
| V4 | ECO 80% + S1 20% का mix loop से: 90,746.67 = report ✅ |

**Code notes:** `logs/research_spot_sleeve/CODE_NOTES.md`। S5 के पहले draft में एक "2% band" था जो protocol में नहीं था। उसे run से **पहले** हटा दिया गया।

## 8. Sources

- Detzel et al. (2021), "Learning and predictability via technical analysis: Evidence from bitcoin and stocks with hard-to-value fundamentals", Financial Management 50(1): https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html
- Liu & Tsyvinski (2021), "Risks and Returns of Cryptocurrency", RFS 34(6) (NBER w24877): https://www.nber.org/system/files/working_papers/w24877/w24877.pdf
- Liu, Tsyvinski & Wu (2022), "Common Risk Factors in Cryptocurrency" (NBER w25882): https://www.nber.org/papers/w25882.pdf
- CXO Advisory का SMA timing summary: https://www.cxoadvisory.com/currency-trading/timing-bitcoin-with-smas/
- Survivor momentum (Grobys et al.): https://osuva.uwasa.fi/handle/11111/20040

*मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।*
