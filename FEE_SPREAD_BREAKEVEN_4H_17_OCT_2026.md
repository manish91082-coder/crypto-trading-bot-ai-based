# Binance fee, spread और break-even: एक trade को profit में आने के लिए price कितना चलना चाहिए (17 अक्टूबर 2026)

**तरीका:** कोई order नहीं डाला गया। Fees तीन जगह से ली गईं:
1. Binance की official fee page।
2. Binance का official FAQ।
3. हमारे demo account का API (`/fapi/v1/commissionRate`, सिर्फ़ पढ़ने के लिए)।

Spread और slippage आज के **live mainnet order book** से नापे गए: 21 coins, spot और perp दोनों, 07:38–07:44 UTC के बीच 5 rounds।
- Code: `src/research_r2/fee_spread_check.py`
- Raw data और उसका SHA256: `logs/research_r2/fee_spread_check/`

## 1. Binance fee (Regular user, VIP 0)
| जगह | Maker | Taker | BNB से भरने पर | स्रोत |
|---|---|---|---|---|
| **Spot** | 0.100% | 0.100% | **0.075%** (25% छूट) | binance.com/en/fee/schedule (आज पढ़ा) |
| **USDT-M Futures** | 0.020% | **0.040%** | 0.018% / **0.036%** (10% छूट) | हमारे demo account का API (आज) |
| Futures (FAQ में) | 0.020% | 0.050% | 0.018% / 0.045% | Binance FAQ |

- **एक फ़र्क अभी खुला है।** Demo API taker fee 0.040% बताता है, जबकि Binance FAQ के उदाहरण में 0.050% है। Live futures fee page पर table खाली दिखी। असली account की दर उसी account के `commissionRate` से पक्की होगी, इसलिए नीचे दोनों हिसाब दिए हैं।
- **Futures पर BNB छूट की शर्त:** BNB **futures wallet** में रखना होगा, spot wallet में रखने से छूट नहीं मिलती।

## 2. एक पूरे trade (buy + sell) की fee
| तरीका | BNB के बिना | **BNB के साथ** |
|---|---|---|
| Spot, market order से entry और exit | 0.200% | **0.150%** |
| Futures, market order (taker 0.04%) | 0.080% | **0.072%** |
| Futures, market order (taker 0.05%, FAQ) | 0.100% | 0.090% |
| Futures, limit order (maker, दोनों तरफ़) | 0.040% | **0.036%** |
| Futures, limit से entry और market से exit | 0.060% | 0.054% |

## 3. Spread और slippage (आज नापा गया, buy + sell दोनों मिलाकर)
| Trade size | Perp (median / सबसे खराब 10%) | Spot (median / सबसे खराब 10%) |
|---|---|---|
| $333 | 0.010% / 0.023% | 0.019% / 0.045% |
| $1,000 | 0.012% / 0.029% | 0.020% / 0.052% |
| $3,333 | 0.017% / 0.045% | 0.027% / 0.066% |
| $10,000 | 0.027% / 0.056% | 0.040% / 0.092% |

- **BTC, ETH, BNB, SOL, XRP और DOGE** पर spread लगभग शून्य है (0.000–0.012%)।
- **सबसे महँगे coins:** ADA, FET, XLM spot और QNT, जहाँ $1,000 के trade पर 0.045–0.06% लगता है।

## 4. Break-even: profit के लिए price को कम से कम कितना चलना चाहिए ($1,000 का trade, BNB के साथ)
| तरीका | Fee | Spread + slippage (median) | **कुल = कम से कम इतनी चाल** | $1,000 पर $ में | खराब हालत (p90) |
|---|---|---|---|---|---|
| **Futures, maker (limit)** | 0.036% | ~0 (limit fill) | **~0.04%** | ~$0.40 | fill न होने का खतरा |
| **Futures, taker (0.04%)** | 0.072% | 0.012% | **~0.085%** | ~$0.85 | ~0.10% |
| Futures, taker (0.05% हो तो) | 0.090% | 0.012% | ~0.10% | ~$1.00 | ~0.12% |
| **Spot, market** | 0.150% | 0.020% | **~0.17%** | ~$1.70 | ~0.20% |

**ऊपर की लागत:**
- **Funding (सिर्फ़ futures):** हर 8 घंटे पर (00, 08, 16 UTC) सामान्य दर लगभग 0.01% है। 4H के trade में ज़्यादा से ज़्यादा एक बार लगती है, और funding उल्टी हो तो कमाई भी होती है। कुछ coins पर funding हर 4 घंटे या हर 1 घंटे पर होती है, यह API से पढ़ना होगा।
- **Short केवल futures पर।** Spot पर short के लिए margin से borrow करना पड़ता है।

## 5. 4H पर market कितना चलता है (हमारा verified 1h data, अक्टूबर 2025 से सितंबर 2026, 4H candles)
| Coin | एक 4H candle में open से close (median) | High से low (median) | High से low (सबसे शांत 25% candles) |
|---|---|---|---|
| BTC | 0.42% | 1.10% | 0.71% |
| ETH | 0.52% | 1.51% | 0.99% |
| SOL | 0.65% | 1.71% | 1.16% |
| XRP | 0.60% | 1.59% | 1.05% |
| DOGE | 0.62% | 1.77% | 1.19% |
| LINK | 0.70% | 1.85% | 1.29% |
| AVAX | 0.67% | 1.87% | 1.29% |
| SUI | 0.84% | 2.23% | 1.55% |

**मतलब:**
- Futures taker का break-even लगभग 0.085% है। BTC की आम 4H चाल (0.42%) इसका लगभग **5 गुना** है, और altcoins की चाल 7–10 गुना।
- Spot (0.17%) पर यह फ़र्क आधा रह जाता है, इसलिए 4H trading futures पर ज़्यादा सस्ती पड़ती है।
- **4H पर market हिलता काफ़ी है, खर्च समस्या नहीं।** असली सवाल यह है कि AI **दिशा** कितनी बार सही पकड़ता है। अगर ~0.5% की चाल पर दिशा सिर्फ़ 50% बार सही हो, तो खर्च के बाद नुकसान ही होगा।

## 6. ज़रूरी सुधार: पुरानी research में खर्च का अनुमान ज़्यादा था
- Steps 13–27 में खर्च **0.25% प्रति fill** माना गया था, यानी trade के आने-जाने पर 0.50%। 1h R4 इसी 0.50% पर डूबा था।
- आज की नाप से असली खर्च **futures पर ~0.085% और spot पर ~0.17%** है, यानी पुराने अनुमान का **3 से 6 गुना कम**।
- यह नतीजा अभी सिर्फ़ एक समय की 5 snapshots का है। Crash के समय spread बहुत चौड़ा होता है (2023 और 10 अक्टूबर 2025 के उदाहरण)।
- इसलिए R2 में खर्च का model **S7** (30 से ज़्यादा rounds, cloud पर रोज़ जमा हो रहे हैं) और 4H closes पर ली गई snapshots से बनेगा, और उसे 1.5× और 2× के stress पर भी परखा जाएगा।
- R4 का पुराना नतीजा नए खर्च पर दोबारा देखना बाद में **पहले से register किया गया एक नया trial** होगा। इसे पुराने fail को "बचाने" की तरह नहीं गिना जाएगा।

## Sources
- [Binance spot fee schedule](https://www.binance.com/en/fee/schedule)
- [Binance Futures Fee Structure & Fee Calculations (FAQ)](https://www.binance.com/en-IN/support/faq/binance-futures-fee-structure-fee-calculations-360033544231)
- [What Fees are Generated in Binance Futures Trading?](https://www.binance.com/en/support/faq/what-fees-are-generated-in-binance-futures-trading-98488a516eb84e3eb34605683dffd554)
- Demo API: `GET demo-fapi.binance.com/fapi/v1/commissionRate` (BTC, ETH, SOL, DOGE: maker 0.0002, taker 0.0004), file `logs/research_r2/fee_spread_check/commission_demo.json`

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
