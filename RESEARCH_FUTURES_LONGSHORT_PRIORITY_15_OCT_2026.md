# Futures, long-short, मंदी वाला data और timeframes: क्या पहले करें (research)

**तारीख:** 15 अक्टूबर 2026 | **GitHub:** कुछ नहीं | **कोई trade नहीं**

**सबूत का स्तर:**
- यहाँ के अपने आँकड़े **सिर्फ विवरण** (descriptive) हैं। ये पहले से मौजूद, verified predictions से निकले हैं।
- ये pre-registered test **नहीं** हैं, और **खर्च व funding से पहले** (gross) के हैं।
- ये सिर्फ यह तय करने के लिए हैं कि आगे क्या परखना चाहिए।

---

## 1. एक ज़रूरी फर्क: futures **data** बनाम futures **trading**
| | क्या मिलता है | Short कर पाएँगे? |
|---|---|---|
| Futures **data** (funding, basis, OI) को AI के input में जोड़ना (पिछली file का #3) | AI को ज़्यादा जानकारी, ताकि ranking बेहतर हो | **नहीं।** Trading spot long-only ही रहेगी |
| Futures पर **trading** (perpetual contracts) | Short करना मुमकिन | **हाँ**, पर यह project का दायरा बदलना है: अभी नियम "SPOT long-only, futures सिर्फ जानकारी" है। **यह फैसला आपका है** |

**आपकी बात सही है, पर एक शर्त के साथ:** short के लिए futures trading चाहिए, सिर्फ data काफी नहीं।

**कौन-सा short?** हमारे दिमाग **relative** हैं: "कौन-सा coin बाकियों से बेहतर या बुरा करेगा"।
- "Market गिरेगा, इसलिए short करो" (direction) के 5 tests fail हुए थे।
- इसलिए सबूत सिर्फ **market-neutral long-short** के पक्ष में है:
  - top coins खरीदो, bottom coins short करो, बराबर पैसे से;
  - market ऊपर जाए या नीचे, फर्क नहीं पड़ना चाहिए।

## 2. पहले से मौजूद predictions पर तेज़ जाँच (विवरण, gross)
**तरीका:**
- हर दिन 23:00 (R24) या 20:00 (R6) पर दिमाग की ranking ली।
- Top 5 और bottom 5 का अगले 1 दिन का औसत return देखा।

**औसत प्रति दिन (%):**

| | Top 5 | Bottom 5 | सारे coins | **Long-short (top − bottom)** | t-stat | Long-short positive वाले दिन |
|---|---|---|---|---|---|---|
| R24, 2021–26 (2,097 दिन) | +0.300 | −0.199 | +0.085 | **+0.499** | 5.57 | 59% |
| R6, 2021–26 | +0.292 | −0.189 | +0.085 | **+0.481** | 5.96 | 59% |
| R24, 2018–19 (293 दिन*) | −0.046 | −0.199 | −0.118 | **+0.153** | 1.01 | 56% |
| R6, 2018–19 | −0.081 | −0.178 | −0.118 | **+0.097** | 0.66 | 53% |

\* 2018–19 में सिर्फ वे दिन गिने गए जब ≥ 15 coins मौजूद थे।

**R24 का long-short, साल-दर-साल (%/दिन):**

| 2021 | 2022 (मंदी) | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| 0.815 | **0.631** | 0.189 | 0.455 | 0.457 | 0.429 |

**क्या दिखता है:**
1. 2021–26 में **short वाला हिस्सा भी उतना ही काम का है जितना long वाला।** Bottom 5 बाज़ार से ~0.28%/दिन पीछे रहे; top 5 ~0.21%/दिन आगे।
2. **मंदी वाले 2022 में भी long-short positive रहा** (+0.63%/दिन), जबकि long-only नीचे गया (top 5 −0.19%/दिन)।
3. **2018–19 (कभी न देखा data) में फर्क positive है, पर छोटा और पक्का नहीं** (t = 0.7–1.0)। यह सबसे बड़ी चेतावनी है।

## 3. खर्च और funding (असली संख्याएँ)
**Futures fee:**
- USDⓈ-M, VIP 0: maker 0.02%, taker 0.05%।
- BNB से ~10% कम।
- Source: Binance का support article, और Finder।

**Funding (हमारे data से):** जिन bottom-5 coins पर short होता (50% coin-days का funding data है), उन पर short वाले को औसतन **+0.0155%/दिन मिलता**। पर साल-दर-साल बदलता है:

| 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| +0.091 | −0.036 | +0.009 | +0.039 | +0.006 | **−0.071** (short को चुकाना पड़ता) |

**मोटा हिसाब:**
- सबसे बुरा case: हर दिन दोनों तरफ पूरा बदलाव = 4 fills × 0.05% = 0.20%/दिन। तब भी gross 0.48–0.50% से कम है।
- पर असली turnover, slippage, और spot व futures की कीमत का फर्क, सिर्फ simulation से पता चलेगा।
- **यह अभी साबित नहीं है।**

## 4. खतरे (ईमानदारी से)
- **Short में नुकसान की कोई सीमा नहीं।** एक coin अचानक +100% भागे (short squeeze), तो short वाला हिस्सा बहुत नुकसान करेगा।
  - इसलिए leverage सिर्फ 1x होगा;
  - हर coin का हिस्सा छोटा होगा;
  - और सबसे बुरे दिनों का हिसाब अलग से होगा।
- **Liquidation:** leverage से account साफ हो सकता है। 1x और isolated margin से यह खतरा बहुत कम होता है, पर शून्य नहीं।
- **2018–19 में सबूत कमज़ोर है।** यानी मंदी में यह बचाएगा, यह अभी साबित नहीं।
- 2021–26 पर बहुत tests हो चुके हैं, इसलिए Deflated Sharpe और PBO से जाँच ज़रूरी है।
- **Futures खाता:** आपके देश में Binance futures की उपलब्धता और नियम आपको खुद जाँचने होंगे। मैं इस पर कुछ नहीं मान रहा।

## 5. Timeframes: क्या 4h, 1W, 1M, 1h spot पर पहले करें? [हमारा सबूत]
| Timeframe | स्थिति |
|---|---|
| **4h** | **हो चुका**: R6 (Step 23), PASS, AUC 0.568 |
| **1h** | **हो चुका**: R24 (Step 24), PASS, AUC 0.565 |
| **1W** | असल में हो चुका: R5/R10 (Step 15), AUC 0.545/0.541। Phase 1 में 1W की हालत का कोई असर नहीं |
| **1M** | 2020 से हर coin के ~81 monthly candles, 2017 से ~110। Relative AI के लिए बहुत कम samples; 1M swings सिर्फ 26–33 |
| 5m–30m | दिशा का अनुमान ~0, खर्च भारी (scanner research) |

**मतलब:** spot पर नए timeframes से बड़ा फायदा मिलने का सबूत **नहीं** है। सबसे बड़ी समस्या (मंदी और गिरावट) timeframe से नहीं सुलझती; वह long-short (market-neutral) से सुलझ **सकती** है।

## 6. Priority (मेरा फैसला, सबूत के आधार पर)
| क्रम | काम | फायदा | खर्च / समय | शर्त |
|---|---|---|---|---|
| **1** | **Long-short का pre-registered simulation**, पहले से मौजूद predictions पर (कोई नई training नहीं) | सबसे बड़ा संभावित फायदा: मंदी में भी कमाई की उम्मीद, और long-only की गिरावट (49–81%) का सीधा इलाज | कम | Futures fee, funding (हमारा data), 1x, keep-rank buffer, shuffled control। 2021–26 **और** 2018–19 दोनों। Deflated Sharpe |
| **2** | **मंदी वाला data (2017–19) training में** | Ranking मंदी में बेहतर हो सकती है, जो long और short दोनों के काम आएगा | मध्यम | Paired walk-forward। 2022 अलग से। उसके बाद 2018–19 exam नहीं रहेगा |
| **3** | **Futures data (funding, basis, OI) features में** | Paper (Chi et al. 2023) में basis सबसे मज़बूत relative संकेत। Long और short दोनों के काम आएगा | मध्यम | पहले बचे coins का data download। Paired test, जिसमें पैसे वाली शर्त भी pass होनी ज़रूरी |
| 4 | Pass हुआ और आप futures की हाँ दें, तो long-short का **paper forward log** (shadow) | असली सबूत | कम | कोई order नहीं |
| 5 | फिर testnet futures पर तकनीकी जाँच | Orders का तरीका सही है या नहीं | कम | Testnet पर testnet के खर्च की कोई कीमत नहीं |
| — | नए spot timeframes (1W, 1M) | सबूत कम | — | **नहीं** |

**1 पहले क्यों:**
- यह सबसे सस्ता है (training नहीं), और सबसे बड़े सवाल का जवाब देता है।
- 2 और 3 का फायदा long-only और long-short, दोनों को मिलेगा।
- इसलिए पहले यह जानना ज़रूरी है कि short वाला रास्ता खुला है या नहीं।

## Sources
- Binance USDⓈ-M futures fee (VIP 0: 0.02% / 0.05%): [Binance support article 360033544231](https://www.binance.com/es/support/articles/360033544231) · [Finder](https://www.finder.com/cryptocurrency/trading/binance-futures-fees)
- Chi, Hao, Hu & Ran, Journal of Futures Markets 43(8) 2023: [IDEAS/RePEc](https://ideas.repec.org/a/wly/jfutmk/v43y2023i8p1161-1180.html)
- Liu, Tsyvinski & Wu, Journal of Finance 2022 (long-short crypto factors): [SSRN](https://papers.ssrn.com/abstract=3379131)
- Cakici et al., IRFA 2024 (crypto alpha का ज़्यादातर हिस्सा long leg से): [repository](https://open.icm.edu.pl/handle/123456789/25543)
  - **ध्यान:** हमारे बड़े coins वाले data में short leg भी उतना ही मज़बूत दिखा। यह paper से अलग है; simulation में जाँचना होगा।
- हमारे आँकड़े:
  - `logs/strategy_1d_step24_1h/{test,pre2020}_predictions_1h.csv`
  - `logs/strategy_1d_step23_4h/{test,pre2020}_predictions_4h.csv`
  - `data/futures_info/*_funding.csv`
