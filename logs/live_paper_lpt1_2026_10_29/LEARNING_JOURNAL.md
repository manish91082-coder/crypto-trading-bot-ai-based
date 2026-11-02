# LPT-1 learning journal (live AI paper desk). हर दिन जोड़ा जाता है; सबूत logs में (decisions / fills / contexts / signals / pred1)

## दिन 1: 2026-10-29 (desk 04:23Z से)

**Market**
- **कल रात:** FOMC (28 Oct 18:00Z) के बाद risk-off; breadth सिर्फ़ 7–20% coins ऊपर।
- **सुबह (Asia):** BTC 81.4k से 79.7k, फिर पूरा दिन 79.7k–80.5k की range।
- **12:30Z:** US GDP/PCE पर सिर्फ़ छोटा spike।
- **13:30Z:** US open पर दोनों तरफ़ whipsaw।

**फ़ैसले** (17 decision records, 1 trade):

| समय (UTC) | फ़ैसला | सीख |
|---|---|---|
| 04:2x | NO_TRADE: risk-off, Asia, setup नहीं | low पर chase नहीं किया; बाद में market 79.7k के आसपास ही रहा |
| 04:37–05:33 | VWAP / EMA20 short plans, trigger नहीं | bounce EMA20 से 4 points पहले मुड़ा; trigger नहीं आया, इसलिए trade नहीं |
| 06:05 | **RULE MISS:** BTC VWAP retest, wick 32% < 40% | trade लेते तो ~+0.6R होता। 40% wick की शर्त शायद ज़्यादा सख़्त है; बदलाव सिर्फ़ protocol amendment से, आगे के trades पर |
| 06:45 | ETH trigger आया, पर R:R 1.15 < 1.5 → skip | stop को खिसकाकर trade "बना" लेना ख़ुद को धोखा होता; नियम माना |
| 07:04 | NEAR breakdown (6× volume) skip: 1.7 ATR देर | पीछे भागने (chase) से बचा |
| 12:00–13:00 | US macro blackout | नियम ने काम किया; spike छोटा रहा |
| 14:13 | **TRADE P0001:** ETH short @ 2328.42, stop 2337, target 2304 | order के समय price 3 points ऊपर गया, stop पास आ गया और size बढ़ गई (2.4x) |

**System की सीख**
- **Network timeouts** (data-api.binance.vision) दिन में कई बार आए। Predictor और forward tracker ठीक से recover करते हैं; छूटे मिनट log में दर्ज हैं।
- **Context engine** ने macro, news और cross-asset एक साथ दिखाया: ECB presser, Nasdaq futures −1%, Fear & Greed 68 से 51।
- **Research से (R2) एक data bug पकड़ा:** LUNA जैसे relisted symbols। Live system में भी यही नियम लागू है: नया listing = नई series।

**Execution की सीख**
- Signal आने से order भेजने तक की देरी (मिनट भर) ने entry बिगाड़ी।
- **सुधार का विचार:** signal पर limit order, या "price signal close से ≤ 0.3×ATR5m दूर हो" की शर्त। (अभी लागू नहीं। अगर लागू हुआ तो LPT-1 amendment से, कारण सहित।)
| 14:33 | **P0001 STOP:** ETH spike 2328 → 2342.7 in one 5m (taker 0.70, 7× volume); filled at 2341.34 vs stop 2337 | Loss −151.67 = **−1.52R** (risk was 1R): 4.3 points of slippage on the fast move plus fees. The thesis ("trend down, the EMA20 holds") broke when BTC broke out of the 79.7k–80.56k range at the same time. Lessons: (1) in a range regime the EMA20 rejection is weak; check the higher-TF range edges before entering; (2) on fast moves the stop slips by about 0.5 R, so size for ~1.5R of real loss |

## रात 29→30 Oct: सबसे बड़ी सीख
- **Desk अंधा रहा:** 18:30–21:30Z और 21:30–02:15Z के बीच laptop या network बंद था (equity.csv में gaps)। उसी दौरान crypto की सबसे बड़ी news आई: Binance security breach, ~5.7B USD (CoinDesk, Cointelegraph)। BTC 81.4k से 77.2k, mcap −5.8%, Fear & Greed 51 से 30।
- **Context engine ने news पकड़ी थी, पर मेरे brief ने छिपा दी:** CoinDesk की "Binance confirms security breach" वाली live-updates story 10:41Z की थी, यानी context feed में दिन भर मौजूद रही। मेरा brief सिर्फ़ ताज़ा 8 headlines दिखाता था, इसलिए वह नज़र में नहीं आई।
  - **सुधार:** risk_off tag वाली हर headline और exchange का नाम (Binance / Bybit / OKX…) brief में हमेशा सबसे ऊपर दिखे।
  - **और:** जिस exchange का data हम पढ़ रहे हैं, उसी पर खबर = तुरंत event-risk mode।
- **Desk positions:** उस समय कोई position खुली नहीं थी, इसलिए नुकसान नहीं हुआ। पर अगर होती, तो कोई देखने वाला नहीं था। यही keep-awake / cloud चलाने की असली ज़रूरत है।
- **PRED-1 सीख (30 Oct 04:40Z):**
  - **Volatility band:** crash के दौरान 95% band की coverage 1h पर 57% और 4h पर 69% रह गई। पिछले 100 bars का σ झटके को कम आँकता है; news-shock में band कम से कम 2× चौड़ा मानें।
  - **5m EMA-trend की skill:** +15% (h=10) ज़्यादातर crash में चले trend से आई। BH के बाद significant नहीं, और दिशा-सटीकता 62% है जबकि fee के लिए 67.5% चाहिए। इसलिए trade नहीं।

## दिन 2: 2026-10-30 (laptop shutdown के बाद)
- **क्या हुआ:** laptop ~08:02Z पर बंद हुआ और 08:23Z पर boot हुआ। Desk 08:39Z पर वापस चालू हुआ, यानी ~37 मिनट अंधा रहा। कोई position खुली नहीं थी, इसलिए नुकसान नहीं हुआ।
- **`state.json` corrupt हुआ:** पूरी 259 bytes NUL निकलीं। `save_state` में `os.replace` से पहले fsync नहीं है, और बिजली कटने पर ऐसा हो सकता है।
- **सुधार:**
  - fills.jsonl और daily.jsonl से state दोबारा बनाया; rebuilt फ़ाइल भी ठीक 259 bytes की निकली।
  - corrupt फ़ाइल `state.json.corrupt_NUL_2026-10-30` नाम से रखी है।
  - सभी hash chains सही मिलीं।
  - `lpt.py` lock है, इसलिए उसे नहीं बदला।
- **सीख:** append-only hash-chained logs ने state बचा लिया। अगर position खुली होती, तो stop भी fills से नहीं, `state.json` से ही चलता; इसलिए `lpt.py` में fsync का बदलाव LPT-1 amendment का उम्मीदवार है।
- **Python:** PATH में 3.10 अब 3.12 से आगे है। Loops को Python312 के साथ चलाना है।
- **Market:** Binance hack की headlines 08:36Z तक आ रही हैं, इसलिए event-risk mode ~20:36Z तक बढ़ा।

## 30 Oct 08:53Z से 2 Nov: दूसरी बार laptop बंद
- **क्या हुआ:** पिछली बार restart के सिर्फ़ 14 मिनट बाद (30 Oct 08:53Z) laptop फिर बंद हो गया। Desk 2 Nov ~02:33Z तक, यानी करीब 2 दिन 17.7 घंटे, बंद रहा।
- **दिनों की गिनती:** 31 Oct और 1 Nov का कोई daily record नहीं है, क्योंकि desk चला ही नहीं। इन्हें ट्रेडिंग दिन न गिना जाए।
- **नुकसान:** `state.json` फिर NUL हुआ और `predictions.jsonl` के अंत में 11,471 NUL bytes आए। 4,784 forecasts की chain सही मिली, आख़िरी कुछ forecasts खो गए। कोई position खुली नहीं थी।
- **सुधार:** `src/live_paper/recover.py` बनाया। वह सिर्फ़ NUL वाला अंत हटाता है, और बीच की गड़बड़ी या खुली position मिले तो रुक जाता है।
- **सीख:** laptop पर 14 दिन का लगातार test असल में नहीं चल पा रहा। 4 कैलेंडर दिनों में desk करीब 1.4 दिन ही चला।
