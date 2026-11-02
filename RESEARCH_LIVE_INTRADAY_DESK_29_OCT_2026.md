# Live Intraday Desk (LPT-1): research और live paper trading — 29 Oct 2026

**आपका सवाल (संक्षेप):** अगर कोई master crypto trader या AI सीधे live market पर 10,000 USDT से trade करे और हर दिन intraday 10–15% compounding का लक्ष्य हो, तो वह क्या करेगा? कौन सा market, कौन से factors, कौन सा method, कितना risk, win/loss के बाद क्या, और top intraday traders कैसे सीखते हैं? फिर अपने roles तय करके live data पर paper trade करना और logs रखना।

**Protocol (पहले से lock):** `logs/live_paper_lpt1_2026_10_29/LPT1_PROTOCOL_PREREGISTERED.md` (SHA `bd9d630e…`, 04:23:07Z)। कोई भी असली order कहीं नहीं भेजा जाता।

---

## 0. सीधा जवाब पहले
1. **10–15% रोज़ लगातार compounding** गणित, इतिहास और हमारे अपने data, तीनों के हिसाब से टिकाऊ लक्ष्य नहीं है। इसका कारण नीचे है, आँकड़ों के साथ। यह राय नहीं, गिनती है।
2. **एक master trader का असली काम** लक्ष्य से उल्टा शुरू होता है: पहले "कितना खो सकता हूँ" तय करना, फिर ऐसे trades चुनना जिनमें fee के बाद भी बढ़त हो, और बाकी समय कुछ न करना।
3. **फिर भी desk चलाया गया** (live data, live order book पर paper fills, सख़्त risk rules)। हर दिन का नतीजा 10% के लक्ष्य के सामने ईमानदारी से लिखा जाएगा (§7, रोज़ update)।

## 1. 10–15% रोज़ का गणित (`logs/live_paper_lpt1_2026_10_29/research_math_output.txt`)
| रोज़ | 30 दिन | 60 दिन | 1 साल |
|---|---|---|---|
| 10% | 10k → 1.74 लाख | 30 लाख | ~1.3 × 10¹⁹ USDT (दुनिया की कुल दौलत से अरबों गुना ज़्यादा) |
| 15% | 10k → 6.6 लाख | 4.4 करोड़ | — |

**God mode** (कोई trader जिसे हर candle का भविष्य पता हो, BTC futures, 1x, fee के बाद, 2024–2026):

| Candle | Median दिन | ≥ 10% वाले दिन |
|---|---|---|
| 5m | +8.9% | 44% |
| 1h | +5.4% | 13% |
| 1d | +1.1% | 0.4% |

यानी पूरा भविष्य जानकर भी 1h trading से आधे से ज़्यादा दिन 10% नहीं बनता। इंसान या AI के पास भविष्य नहीं होता, तो बाकी फ़र्क leverage से भरना पड़ता है, और leverage नुकसान को भी उतना ही बढ़ाता है।

**Monte Carlo** (30 दिन, रोज़ 5 trades, +1R / −1R, fee 0.1R):

| Win rate | Risk / trade | 10%/दिन औसत की संभावना | −50% गिरावट की संभावना |
|---|---|---|---|
| 55% (पहले से बहुत अच्छी edge) | 10% | 0.14% | 74% |
| 60% | 10% | 3.8% | 35% |
| 50–60% में कुछ भी | 1% (professional risk) | 0% | 0% |

## 2. असली traders के बारे में evidence
- **Brazil:** regulator data, 19,646 नए day traders। जिन्होंने 300+ दिन trade किया, उनमें 97% घाटे में रहे; ~1% ही minimum wage से ज़्यादा कमा पाए ([Chague, De-Losso, Giovannetti, "Day Trading for a Living?"](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101); [FGV repository](https://repositorio.fgv.br/items/e87d04fc-4b4c-4a56-ab5a-1c84c1afde1b/full))।
- **Taiwan** (1992–2006, पूरा exchange data):
  - ज़्यादातर day traders घाटे में; कुल मिलाकर performance negative।
  - 97% के भविष्य में भी घाटे में रहने की संभावना; 75%+ दो साल में छोड़ देते हैं ([Barber, Lee, Liu, Odean](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/day%20trading%20and%20learning%20110217.pdf); [published version, RePEc](https://ideas.repec.org/a/oup/rasset/v10y2020i1p61-93..html))।
- **Crypto futures:** BitMEX के perpetual में रोज़ open interest का 3.51% (long) / 1.89% (short) जबरन liquidate होता था, और liquidate होने वालों का औसत leverage ~60x था ([arXiv 2102.04591](https://arxiv.org/abs/2102.04591v1))।
- **इतिहास का सबसे सफल quant fund (Renaissance Medallion):** ~66% प्रति **साल** gross, 1988–2018 ([Quantt](https://www.quantt.co.uk/resources/medallion-fund-history); [Institutional Investor](https://www.institutionalinvestor.com/article/2bswzoz7x91fqht87wvsw/portfolio/the-famed-medallion-fund-is-crushing-it-other-rentech-funds-not-so-much))। 10% रोज़ उससे करोड़ों गुना ज़्यादा है।
- **इस project का अपना evidence (पहले के verified studies):**
  - 1 घंटे से छोटे timeframe पर कोई price-only नियम fee नहीं निकाल पाता;
  - funding, OI, liquidation जैसे non-price signals असली हैं पर fee से छोटे हैं;
  - सिर्फ़ 8h–1d trend formulas fee के बाद टिकते हैं।

## 3. एक master trader असल में कैसे सोचता और करता है
**Market चुनना**
- **Spot:** liquidation risk नहीं, पर सिर्फ़ long।
- **Futures:** short भी, fee कम (0.036% vs 0.075%), funding और liquidation का risk।
- **Pro तरीका:** दोनों use करना, पर futures में कम leverage (1–3x)। Leverage position size का औज़ार है, कमाई का नहीं।

**Factors (desk के snapshot में सब live हैं)**
1. **Regime:** BTC का trend (4h/1h), breadth (कितने coins ऊपर हैं), volatility (ATR)। BTC के ख़िलाफ़ altcoin trade कम ही सफल होते हैं।
2. **Levels:** VWAP, पिछले दिन का high/low, आज का high/low, 1h EMA20/50, swing highs/lows।
3. **Flow:** volume ratio, taker buy share, order book imbalance, spread।
4. **Positioning (futures):** funding rate, OI का बदलाव, long/short ratio। भीड़ एक तरफ़ हो तो उल्टा झटका (squeeze/flush) आ सकता है।
5. **Time:** Asia/Europe/US session, weekend की कम liquidity, बड़ी macro announcements (CPI, FOMC)।

**Method**
- बहुत कम setups, हर एक पहले से लिखा हुआ:
  - trend pullback;
  - level breakout (volume के साथ);
  - liquidation flush reversal।
- कोई साफ़ setup नहीं, तो कोई trade नहीं।
- हर trade में entry से पहले stop और target तय होता है, और reward/risk ≥ 1.5।

**Risk (सबसे ज़रूरी)**
- **हर trade:** equity का 0.5–1%।
- **दिन की सीमा:** −2/−3% पर बंद।
- **Leverage:** कुल exposure 3x से कम।
- **ध्यान रखें:** 10% risk-per-trade वाला trader कुछ हफ़्तों में ख़त्म हो जाता है (§1)।

**Win/loss के बाद**
- **Loss:** नियम के अनुसार ही — 2 लगातार loss पर ब्रेक; बदले में बड़ा trade कभी नहीं।
- **Win:** size वही रहता है; overconfidence सबसे बड़ा ख़तरा है।
- **हर trade:** journal में "क्यों लिया, क्या हुआ, नियम माना या नहीं"।

**Top traders कैसे सीखते हैं**
- Journal, statistics (R-multiple, win rate, expectancy), छोटे size पर लंबी practice, और एक ही edge पर महारत।
- Studies दिखाती हैं कि ज़्यादातर लोग सीखते नहीं: घाटे के बावजूद लगे रहते हैं (Taiwan: 74% volume घाटे वाले traders का)। इसलिए measurement ज़रूरी है, एहसास नहीं।

## 4. मेरे roles (desk)
| Role | काम |
|---|---|
| Data engineer | live snapshot, sha256 के साथ save |
| Market analyst | regime, levels, flow, positioning |
| Strategist | सिर्फ़ playbook A/B/C, कारण पहले लिखा जाता है |
| Risk manager | code में hard rules; नियम तोड़ने वाला order reject |
| Execution | live order book पर fill; stop/target live bid/ask पर |
| Auditor | hash-chained logs; बाद में official 1m data से हर fill की जाँच |

## 5. Data स्रोत और सीमाएँ
- **Spot:** Binance official public mirror (data-api.binance.vision)।
- **Futures:** Bybit linear perps के live prices, सिर्फ़ proxy के तौर पर। Binance futures API इस laptop से नहीं खुलता (timeout, जाँचा गया); fees Binance की हैं।
- **Paper fills:** असली book पर, पर book को हिलाते नहीं।
- **Laptop sleep / network गड़बड़:** उस दौरान desk काम नहीं करता; ऐसे gaps report में दर्ज होंगे।

## 6. Evaluation (पहले से तय)
- **रोज़:** लक्ष्य के सामने नतीजा।
- **हर 20 trades पर:**
  - net P&L, win rate, औसत R, fees का हिस्सा;
  - BTC buy-and-hold से तुलना;
  - random-entry baseline से तुलना।
- **"Skill" का दावा:** सिर्फ़ ≥ 60 trades के बाद, औसत R > 0 और p ≤ 0.05, और random से बेहतर।

## 7. Live log (रोज़ update)
| UTC दिन | शुरू | अंत | दिन का % | 10% लक्ष्य | trades | नोट |
|---|---|---|---|---|---|---|
| 2026-10-29 | 10,000.00 | (चल रहा है) | | 11,000.00 | 0 | 04:23Z desk शुरू; 04:2xZ पहला फ़ैसला: NO_TRADE (risk-off, Asia session, setup नहीं) |

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research और paper trading है, निवेश सलाह नहीं।
