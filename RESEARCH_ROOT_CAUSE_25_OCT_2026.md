# गलती कहाँ है? ज़मीनी root-cause research (25 अक्टूबर 2026)

> **Discipline:**
> - Protocol नतीजों से पहले lock किया गया: `logs/research_root_cause/ROOT_CAUSE_PROTOCOL_PREREGISTERED.md`, SHA `522e0a93…`।
> - Code `src/research/root_cause_study.py` है।
> - अलग verifier `src/audits/verify_root_cause.py` के **5/5 PASS**। उसने सभी 10 coins पर 1h और 4h की गिनती अपने loops से दोबारा की।
> - नतीजे: `logs/research_root_cause/ROOT_CAUSE_RESULTS.json`।
> - Data: 10 बड़े coins (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LINK, LTC) का 5 मिनट data, 2020-01 से 2026-09। Period A = 2020-01 → 2025-09, और B = पिछला एक साल (2025-10 → 2026-09)।
> - मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## 0. जवाब एक नज़र में

| शक | ज़मीनी नतीजा |
|---|---|
| "Market हमेशा fee से ज़्यादा हिलता है, कहीं भी खरीदो-बेचो, profit होगा" | **गलत साबित।** 1 घंटे में 94% बार market maker fee (0.04%) से ज़्यादा हिलता है, पर **हमारी दिशा में** सिर्फ़ 47% बार (taker 0.08% पर: 88% बनाम 44%)। Random entry हर timeframe और हर fee पर ठीक fee जितना घाटा देती है (§2) |
| Fee का हिसाब गलत? | असली fee: **futures maker 0.02%, taker 0.04%** (हमारे demo account के API से) और spot BNB के साथ 0.075%। N1 का अनुमान लगभग सही है। **1D/F4 spot की fill 0.25% मानता है, जो असली (~0.085–0.10%) से 2.5 गुना है।** यह गलती है, पर **यह system को कमज़ोर नहीं, ज़्यादा सावधान दिखाती है**, और P3 के घाटे की वजह नहीं (§1) |
| Backtest या implementation गलत? | Live engine ने backtest की entries और exits **100%** दोहराईं (पिछली verified जाँचें)। गलती code में नहीं मिली |
| **असली blunder** | **N1 (4h multi-TF system, ECO में ~46% हिस्सा) पिछले साल fail हुआ:** dev में +74.6% सालाना, P3 में **−12.5% सालाना**, drawdown 31%। इसके profit मुख्य रूप से bull market के साथ चलने से आए थे (साल-दर-साल BTC से correlation 0.71) |
| 1D का क्या? | **1D पिछले साल भी profit में रहा:** +15.6% सालाना, drawdown सिर्फ़ 12.6%, उस साल में जब BTC −27% गिरा। साल-दर-साल BTC से correlation **−0.09**, यानी market की दिशा पर निर्भर नहीं |
| फिर ECO zero क्यों? | ECO = 54% 1D + 46% N1। **1D का profit N1 के घाटे ने खा लिया** |
| रोज़ profit मुमकिन है? | ECO के 2021–25 में सिर्फ़ 53% दिन, और पिछले साल 48% दिन positive थे। रोज़ positive रहने वाली अकेली चीज़ funding carry है (79–89% दिन), पर उसकी कमाई पिछले साल **कुल 3.4%** थी |

---

## 1. Fee: असली बनाम हमने क्या माना

| | असली (ground truth) | हमने माना | फ़र्क |
|---|---|---|---|
| Futures maker | **0.020%** (demo API `commissionRate`, BTC/ETH/SOL) | n/a | n/a |
| Futures taker | **0.040%** | N1 और ECO: 0.054% | थोड़ा ज़्यादा माना, सुरक्षित तरफ़ |
| Spot | 0.100% (BNB से 0.075%), impact ~0.01% | N1: 0.085% | सही |
| Spot long fill (1D/F4) | ~0.085–0.10% | **0.25%** | **2.5 गुना ज़्यादा** |
| Stop slippage (1D/F4) | n/a | 1% | बहुत conservative |

- **Round trip (आना और जाना):** futures maker 0.04%, futures taker 0.08%, spot BNB 0.17%।
- सितंबर 2026 के replay में 1D के fees और stop slippage मिलाकर ~0.4% महीना बनते थे।
- Protocol का नियम था: cost को P3 की कमज़ोरी की वजह तभी माना जाएगा, जब वह dev और P3 के फ़र्क का कम से कम 50% हो।
- Dev और P3 का फ़र्क ~4% महीना है। Cost उसका 10% भी नहीं है। **Cost blunder नहीं है।**

## 2. आपका premise: "fee से ऊपर हिला, तो profit"

**Random entry** (सिक्का उछालकर long या short), 10 coins, हर block अलग, fee काटकर। Mean net % प्रति trade:

| Timeframe | market fee से ज़्यादा हिला (taker 0.08%) | **हमारी दिशा में** fee से ज़्यादा | Net (maker 0.04%) | Net (taker 0.08%) | Net (spot 0.17%) |
|---|---|---|---|---|---|
| 5m | 63% | 31% | −0.040 | −0.080 | −0.170 |
| 15m | 78% | 39% | −0.040 | −0.080 | −0.170 |
| 1h | **88%** | **44%** | −0.038 | −0.078 | −0.168 |
| 4h | 94% | 47% | −0.045 | −0.085 | −0.175 |
| 1d | 98% | 48% | −0.051 | −0.091 | −0.181 |

*(Period A। Period B में भी हर cell negative है।)*

- **TP/SL** (fee के 1, 2 या 5 गुना पर) लगाने से भी हर combination negative रहा, conservative और optimistic, दोनों तरह।
- Fee के ठीक ऊपर TP रखने पर net हमेशा ≤ 0 आता है, क्योंकि TP की कमाई = fee।

**गणित (असली formula):**

> प्रति trade कमाई = (2p − 1) × E|move| − cost, जहाँ p = दिशा सही होने की संभावना।
>
> Profit के लिए ज़रूरी: **p > 0.5 + cost / (2 × E|move|)**

**कितनी accuracy चाहिए** (10 coins का औसत move, period A):

| Timeframe | औसत move | Maker (0.04%) पर ज़रूरी p | Taker (0.08%) पर ज़रूरी p | Simple rules ने असल में दिया |
|---|---|---|---|---|
| 5m | 0.19% | **60%** | **71%** | 47–49% |
| 15m | 0.33% | 56% | 62% | 47–50% |
| 1h | 0.66% | 53% | 56% | 47–52% |
| 4h | 1.31% | 51.5% | 53% | 47–53% |
| 1d | 3.40% | 50.6% | 51.2% | 47–53% |

**मतलब:**
- 5–15 मिनट पर "छोटा spread पकड़ने" के लिए **60–80% सही दिशा** चाहिए। दुनिया में कोई भी indicator या AI यह स्थिर रूप से नहीं देता। **यही वजह है कि छोटे timeframe पर scalping fee में डूबती है।**
- बड़े timeframe पर ज़रूरी accuracy 51–53% है। वहीं edge मिलने की गुंजाइश है।
- एक और बात: 1d पर "पलटाव" (REV) वाला rule period A में profit में था, पर B में "trend" (MOM) वाला। **यानी जो rule काम करता है, वह market के mood के साथ बदल जाता है।**

**Perfect दिशा का ज्ञान हो** (सिर्फ़ ऊपरी सीमा), तो taker पर: 1h +0.58%, 4h +1.23%, 1d +3.3% प्रति trade। **पैसा prediction में है, fee के गणित में नहीं।**

## 3. असली blunder: N1 out-of-sample fail

**Dev पर** system चुना गया था। **P3** = पिछला साल, जिसे ECO बनाते समय सिर्फ़ report किया गया था।

| Strategy | Dev सालाना (CAGR) | P3 सालाना | P3/dev | P3 drawdown |
|---|---|---|---|---|
| **N1 अकेला** | +74.6% | **−12.5%** | **−0.17** | 31.3% |
| **1D अकेला** | +53.7% | **+15.0%** | 0.28 | 12.3% |
| 1D combo | +52.3% | +15.6% | 0.30 | 12.6% |
| ECO-W2 (deployed) | +65.9% | −0.3% | −0.005 | 18.7% |
| ECO-W1 | +64.9% | +1.3% | 0.02 | 17.2% |

**साल-दर-साल बनाम BTC का साल:**

| साल | BTC | N1 | 1D combo | ECO-W2 |
|---|---|---|---|---|
| 2021 | +60% | +344% | +199% | +254% |
| 2022 | **−64%** | −7% | **+36%** | +16% |
| 2023 | +156% | +54% | +7% | +28% |
| 2024 | +121% | +91% | +39% | +73% |
| 2025 (सितंबर तक) | +22% | +15% | +22% | +21% |
| **P3 (अक्टूबर 2025 → सितंबर 2026)** | **−27%** | **−13%** | **+16%** | −0.1% |

- **N1** BTC के साथ चलता है (correlation 0.71): bull में बड़ा profit, गिरते market में घाटा। यानी इसका "AI edge" ज़्यादातर **market की दिशा** था।
- **1D** दोनों बड़े गिरते सालों (2022, P3) में भी profit में रहा (correlation −0.09)। Edge का असली सबूत यहीं है।
- Protocol का नियम था: P3/dev < 25% हो, तो overfit माना जाएगा। **ECO-W2 और N1 पर यह साबित है। 1D (0.28–0.30) सीमा के ऊपर है।**
- **महीने के स्तर पर:** ECO के महीने और BTC की "trendiness" का correlation 0.18 है (0.3 से कम), इसलिए महीने-दर-महीने का regime वाला अनुमान साबित नहीं हुआ। साल के स्तर पर साबित हुआ।

## 4. "रोज़ profit" की हक़ीक़त

| | Positive दिन | कुल कमाई |
|---|---|---|
| ECO 2021–25 | 53% | (in-sample) |
| ECO पिछला साल | 48% | ~0 |
| BTC funding carry 2020–25 | 89% | 75.8% (6 साल में) |
| BTC funding carry पिछला साल | 79% | **3.4%** |

**रोज़ profit देने वाली अकेली चीज़ (carry) की कमाई पिछले साल लगभग bank FD जितनी रही।** Directional trading में "रोज़ profit" गणित से मुमकिन नहीं है। हर हफ़्ते और महीने में घाटे वाले दिन आएँगे ही।

## 5. तो करना क्या है (प्रस्ताव, हर एक pre-registered test के बाद)

1. **N1 का हिस्सा घटाना या बंद करना (सबसे बड़ा असर):**
   - पिछले साल ECO को इसी ने डुबाया।
   - **ईमानदार चेतावनी:** यह फ़ैसला P3 देखकर लिया जा रहा है, इसलिए P3 अब "unseen" नहीं रहा।
   - इसलिए इसे सीधे live न करें। Pre-registered amendment बने, और demo पर N1 हटाने वाला एक **shadow** चले, जिसे आगे के महीनों से परखा जाए।
2. **1D का cost model असली fee पर लाना:** 0.25% की जगह ~0.10%, futures 0.04%। इससे 1D का हिसाब और सही होगा।
3. **5m/15m scalping न करें:** 60–80% accuracy की ज़रूरत गणित से असंभव है। अगर कभी करना हो, तो सिर्फ़ maker orders से और असली order-book data पर।
4. **पक्का करना कि 1D की अपनी research में P3 (2025-10 → 2026-09) कितना देखा गया था।** अगर वह भी उसी data पर tune हुआ था, तो 1D का +15.6% भी आशावादी है। **यह अगला ज़रूरी check है।**
5. **"Daily profit" का लक्ष्य बदलना:** मापने लायक लक्ष्य है "हर quarter positive, drawdown 15% से कम"। 1D ने dev और P3, दोनों में यह लगभग पूरा किया।

## 6. सीमाएँ

- 10 coins के pooled CI में coins का आपसी correlation नहीं गिना गया, और सब coins पर एक ही random sequence है (protocol: seed 2026)। इसलिए असली अनिश्चितता बड़ी है। पर हर cell negative है, इसलिए निष्कर्ष नहीं बदलता।
- TP/SL ठीक level पर fill माना गया। Gap आने पर असलियत और बुरी होती।
- Fee VIP 0 की है। बहुत बड़े volume पर fee घटती है, पर ऊपर की table दिखाती है कि fee शून्य भी हो, तो भी random entry का औसत 0 ही रहता है।

## 7. Sources

- Binance futures commission: हमारे demo account का `/fapi/v1/commissionRate` (2026-10-25)।
- Spot fee: `logs/cost_study_step2/STEP2_COST_PROTOCOL_PREREGISTERED.md` (Binance का official page)।
- पिछली verified research: `logs/research_tf_edge_map/SATURATION_LOG.md` (R2-M2: trend edge tail-driven; R2-M3: BTC के साल से correlation 0.71–0.89)।

*मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।*
