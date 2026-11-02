# अंतिम योजना: 1D पर Spot पूरा करना + Futures (long-short) जोड़ना

**तारीख:** 15 अक्टूबर 2026 | **GitHub:** कुछ नहीं

**आधार** (कोई नई संख्या नहीं; सब इन्हीं files से):
- `REPORT_STEPS_0_TO_8_EXECUTION_15_OCT_2026.md`
- `RESEARCH_1D_WHAT_REMAINS_15_OCT_2026.md`
- `RESEARCH_FUTURES_LONGSHORT_PRIORITY_15_OCT_2026.md`

---

## आपके सवाल का सीधा जवाब: पहले futures जोड़ें, या पहले spot पर दूसरे timeframes?
**पहले futures (long-short), spot पर नए timeframes नहीं।** वजह (सबूत के साथ):

| Timeframe (spot) | स्थिति |
|---|---|
| 4h | **हो चुका:** R6, PASS (AUC 0.568) |
| 1h | **हो चुका:** R24, PASS (AUC 0.565) |
| 1W | **हो चुका:** Step 15 में R5/R10 (AUC 0.545/0.541)। Phase 1 में 1W की हालत का असर नहीं मिला |
| 1M | 2020 से हर coin के सिर्फ ~81 candles, इसलिए AI के लिए data बहुत कम |
| 5m–30m | दिशा का अनुमान ~0; खर्च भारी |

**सबसे बड़ी समस्या मंदी और 49–81% की गिरावट है।** Timeframe बदलने से यह नहीं सुलझती; पाँच कोशिशें fail हो चुकी हैं।
- **Long-short (market-neutral)** इसे सुलझा **सकता** है:
  - 2021–26 में gross +0.50%/दिन, मंदी वाले 2022 में भी +0.63%/दिन;
  - पर 2018–19 में सिर्फ +0.10 से +0.15% (पक्का नहीं)।
- और इसकी पहली परीक्षा **सबसे सस्ती** है: training नहीं चाहिए, पहले से मौजूद predictions काफी हैं।

---

## पहले से चल रहा है (इसे छुआ नहीं जाएगा)
| क्या | कब तक | Pass की शर्त |
|---|---|---|
| Step 16B forward log: spot M_AI3-50% का paper portfolio, कोई order नहीं | 90 दिन, ~14 जनवरी 2027 | ≥ 90 दिन; ≤ 3 समझाए गए alarms; R6 या R24 का forward AUC > 0.50 |
| Step 2: असली खर्च का नाप (mainnet की public order book) | 30 rounds, ~15 दिन | पहले से तय फैसले का नियम |

**नियम:**
- कोई भी नया सुधार इस log को **नहीं** बदलेगा।
- सुधार सिर्फ **shadow** (साथ-साथ, अलग log में) चलेंगे, ताकि 90 दिन की घड़ी शून्य से न शुरू करनी पड़े।

---

## Phase S: Spot (1D) पूरा करना
| # | काम | फायदा | Pass की शर्त | खर्च |
|---|---|---|---|---|
| S1 | **Overfitting का हिसाब** (Deflated Sharpe + PBO), सारे पुराने trials पर | पता चलेगा कि हमारे अच्छे नतीजों में किस्मत कितनी है | माप है, pass/fail नहीं; असली पैसे के फैसले में साथ जाएगा | कम |
| S2 | **2017–19 मंदी का data training में** (D1, R6, R24) | AI पहली बार पूरी मंदी देखेगा | Paired walk-forward 2021–26: AUC बढ़े (CI > 0), पैसा बढ़े, 2022 बेहतर | मध्यम |
| S3 | **Futures data को feature बनाना** (funding, basis, OI, long/short ratio); पहले बचे coins का data download और SHA-verify | Basis, coins के बीच सबसे मज़बूत संकेत (Chi et al. 2023) | S2 जैसा। **पैसे वाली शर्त ज़रूरी** (Steps 25/29 में AUC बढ़ा पर पैसा घटा था) | मध्यम |
| S4 | **Label "बड़ा winner"** (top 20%) | कमाई बड़ी चालों से आती है | S2 जैसा | मध्यम |
| S5 | **तीनों दिमागों के scores जोड़ना** | सस्ता; छोटा फायदा अपेक्षित (आपसी मेल 0.89–0.95) | Portfolio Calmar बेहतर हो | कम |
| S6 | **Attention data** (Wikipedia pageviews): सिर्फ इकट्ठा करना | भविष्य का feature | Data verify; test बाद में | कम |
| S7 | **असली खर्च पर research दोबारा गिनना** (30 rounds के बाद) | सही उम्मीद; शायद ज़्यादा कमाई (0.11% बनाम माना गया 0.25%) | पहले से lock किया नियम | कम |

**Pass हुआ तो:** वह सुधार shadow line बनकर forward log में जुड़ेगा। Production तभी बदलेगा जब उसका अपना forward सबूत हो।

---

## Phase F: Futures (long-short, market-neutral)
**Short का मतलब:**
- AI के "सबसे कमज़ोर" coins short, और "सबसे मज़बूत" coins long, बराबर पैसे से।
- "Market गिरेगा" वाला short **नहीं**, क्योंकि वह 5 बार fail हुआ है।

| # | काम | कौन | ध्यान |
|---|---|---|---|
| F1 | **Futures data:** perpetual candles (Binance Vision, free, SHA-verify) + हर coin की perpetual listing की तारीख + बचे coins की funding और basis | मैं | सिर्फ perpetual वाले coins universe में |
| F2 | **Long-short simulator + पहले से lock किया test.** दो design: (a) spot में long + futures में short; (b) दोनों तरफ futures (fee 0.02/0.05% बनाम spot 0.10%) | मैं | 1x, isolated, हर 8 घंटे funding, liquidation की जाँच, हर coin की सीमा, सबसे बुरे दिनों का अलग हिसाब, नकली दिमाग, 2021–26 **और** 2018–19, Deflated Sharpe |
| F3 | S2/S3 में दिमाग बेहतर हुए, तो उन्हें long-short पर भी परखना | मैं | वही शर्तें |
| F4 | **Long-short का paper forward log** (shadow, कोई order नहीं) | मैं, **आपकी हाँ से** (scheduled task बदलेगा) | ≥ 90 दिन |
| F5 | **Futures account:** चालू करना, Binance quiz, आपके देश में उपलब्धता और नियम | **आप** | Password, API key और पैसा कभी मैं नहीं डालूँगा |
| F6 | **Execution code:** futures API, leverage 1x, isolated margin, reduce-only, kill switch; पहले **futures testnet** पर | मैं, आपकी हाँ से | Testnet पर सिर्फ तकनीकी जाँच (खर्च असली नहीं) |
| F7 | **Risk नियम** (protocol में lock): हर short का अधिकतम हिस्सा, account के नुकसान की सीमा, बहुत तेज़ भागते coin से निकलना | मैं | Short में नुकसान की कोई सीमा नहीं होती, इसलिए यह सबसे ज़रूरी है |
| F8 | **असली पैसा:** छोटी रकम से | **आपका फैसला** | F4 के ≥ 90 दिन + खर्च का नाप |

**Futures पर ज़रूरी बात:** futures data की training (S3) **spot में भी काम आएगी**, अगर pass हो। उसके लिए futures account ज़रूरी नहीं।

---

## पूरा क्रम (मेरा फैसला)
| क्रम | काम | क्यों इस क्रम में |
|---|---|---|
| 1 | **S1** Overfitting का हिसाब | पहले यह जानना ज़रूरी है कि नींव कितनी पक्की है |
| 2 | **F1 + F2** Long-short simulation | सबसे बड़ा संभावित फायदा (मंदी), training नहीं चाहिए, सबसे सस्ता |
| 3 | **S2** मंदी वाला data training में | इसका फायदा spot और long-short, दोनों को |
| 4 | **S3** Futures data features में (पहले download) | यह भी दोनों के काम आएगा |
| 5 | **S7** असली खर्च पर दोबारा गिनना | 30 rounds पूरे होते ही |
| 6 | **S4, S5** | छोटे सुधार |
| 7 | **F4** Long-short का paper log (आपकी हाँ के बाद) | 90 दिन का असली सबूत |
| 8 | **F5–F7** Account (आप), फिर testnet code और risk नियम | Paper log चलते-चलते |
| 9 | **फैसले:** spot ~14 जनवरी 2027; long-short अपने paper log के 90 दिन बाद | सिर्फ forward सबूत पर |
| लगातार | S6 attention data इकट्ठा करना | — |

## हर काम का अनुशासन (हमेशा)
- पहले protocol और SHA lock।
- अलग verifier।
- नकली (shuffled) दिमाग से तुलना।
- 2022 (मंदी) अलग से।
- पैसे वाली शर्त।
- Lock के बाद हर बदलाव `CODE_CHANGES_AFTER_LOCK.md` में दर्ज।
- Reports Hindi में; GitHub नहीं; archive नहीं (raw data वाला अपवाद छोड़कर); testnet ETH position को छूना नहीं।

## ईमानदार उम्मीद
- ज़्यादातर spot सुधार (S3–S5) छोटे निकल सकते हैं (Steps 25/29 जैसे)।
- **सबसे बड़ा फर्क long-short (F2) ला सकता है।** पर 2018–19 में उसका सबूत अभी कमज़ोर है, और short के खतरे असली हैं।
- **असली पैसे का हर फैसला आपका है**, forward सबूत देखकर।
