# अगला target: कौन-सा timeframe पहले (17 अक्टूबर 2026)

**स्थिति:** यह सिर्फ़ योजना है। आपकी "हाँ" से पहले कोई research शुरू नहीं होगी। Cloud VM और laptop के 1D system को कोई नहीं छुएगा।

## 1. जो चल रहा है, वह सुरक्षित है
| क्या | कहाँ | स्थिति |
|---|---|---|
| 1D system (spot + perps, F4, E11 shadow, F6 demo) | Cloud VM `cryptobot-1d-mumbai` | रोज़ चल रहा है। R2 के दौरान VM पर कुछ नहीं बदलेगा |
| Laptop की copy | `E:\crypto trading bot ai based 9 oct 2026` | Production files नहीं बदलेंगे |
| Frozen snapshot (आज) | `E:\cryptobot_snapshots\2026-10-17_1D_frozen\` | tar.gz और हर file का SHA256 manifest |
| पिछला bundle (16 अक्टूबर) | `E:\cryptobot_bundle\` | वही, जो VM पर गया |
| Ledger backups | `backups\2026-10-16\` | M10 रोज़ बनाता है |

**नियम:**
- R2 का सारा code सिर्फ़ `src/research_r2/` में और नतीजे सिर्फ़ `logs/research_r2/` में जाएँगे।
- हर R2 run से पहले और बाद में production files का SHA snapshot manifest से मिलाया जाएगा। कोई भी फ़र्क मिला तो run FAIL माना जाएगा।

## 2. हमारे अपने सबूत (verified reports से)
1. **AI को skill हर timeframe पर दिखी:**
   - 1D: AUC 0.559
   - 4H R6: 0.568
   - 1h R24: 0.565
2. **Holding period छोटा हुआ तो खर्च ने कमाई खा ली:**
   - 1h R4 (4 घंटे hold): AUC 0.545 असली था, फिर भी नतीजा $10k → $49 (gross edge लगभग +0.3%, round-trip खर्च लगभग 0.5%)।
   - Step 14 (1.8 दिन hold): भी fail हुआ।
3. **Timeframes को मिलाने से जोखिम नहीं बँटा।** एक ही सवाल ("कल कौन आगे") पूछा जाए तो 1D, 4H और 1h का मेल 0.89–0.95 रहा (Step 27)।
4. **H4 और H1 दिमाग पहले से चल रहे system में हैं।** M_AI3 के तीन हिस्से D1, H4 और H1 हैं, पर फ़ैसला दिन में एक बार होता है।

**निष्कर्ष:** "अगला timeframe" तभी फ़ायदा देगा, जब वह **नया सवाल** पूछे या **नए मौके** दे। वही ranking किसी और candle size पर दोहराने से नया पैसा नहीं आएगा। इसलिए हर नए timeframe को एक gate पास करना होगा: चल रहे 1D system के साथ मेल ≤ 0.70, या मिलाने पर Calmar बढ़े।

## 3. हर timeframe कहाँ खड़ा है
2021-01 से 2026-09 के बीच हर timeframe पर इतने फ़ैसले मिलते हैं:

| Timeframe | फ़ैसलों की गिनती | खर्च का खतरा | सांख्यिकीय ताकत | Data |
|---|---|---|---|---|
| 1h | ~50,000 | **सबसे ज़्यादा** (R4 डूबा) | बहुत | ✓ 699 coins |
| **4H** | ~12,600 | मध्यम (R6 ~1 दिन hold में बचा) | **अच्छी** | ✓ (verified 1h से) |
| 12h | ~4,200 | कम | ठीक | ✓ (1h से) |
| 1W | ~300 | बहुत कम | **कमज़ोर** (DSR मुश्किल) | ✓ (1d से) |
| 1M | ~69 | नगण्य | **नाकाफ़ी**: 69 महीनों पर अलग system साबित नहीं हो सकता | ✓ |

**Monthly पर अलग system नहीं बनेगा।** सिर्फ़ 69 नमूनों पर सच्ची और overfit होड़ में फ़र्क करना संभव नहीं है। Monthly और weekly का इस्तेमाल "market का मौसम" बताने वाली परत के रूप में होगा (कितना long, कितना short), अलग trading system के रूप में नहीं।

## 4. सिफ़ारिश: R2 = 4H long-short (spot + perps)
**साफ़ बात:** अब तक का पूरा system दिन में एक बार trade करता है। H4 और H1 दिमाग सिर्फ़ बारीक candles पढ़ते हैं, उन पर trade नहीं होता। R2 पहली बार **असली 4H trading** होगी, यानी हर 4 घंटे पर फ़ैसला।
1h trading पर तभी काम होगा, जब (a) R2 पास हो और (b) S7 के असली cost data से round-trip खर्च लगभग 0.2% या उससे कम साबित हो। 1h R4 का gross edge लगभग +0.3% था, जबकि उसमें खर्च 0.5% माना गया था।

**4H क्यों:**
- Trades और नमूने सबसे ज़्यादा मिलते हैं, जबकि खर्च अभी भी काबू में रहता है।
- Skill पहले से सबसे मज़बूत है (0.568, और 2018–19 में 0.546)।
- Data verified है।
- R1 engine (perps, funding, liquidation, stops) सीधे काम आ जाता है।

**नया सवाल (ताकि यह 1D की नकल न बने):**
- **A. हर coin की अपनी दिशा।** अगले 4–24 घंटे में यह coin ऊपर जाएगा या नीचे, यानी time-series सवाल। Ranking वाला cross-sectional सवाल नहीं। Long spot या perp पर, short perp पर।
- **B. 4H पर फ़ैसला, पर hold कम से कम ~1 दिन।** Buffer और "कब न बदलें" का नियम होगा, ताकि turnover खर्च न खाए।
- **C. BTC/ETH perps पर अलग trend sleeve।** Long और short दोनों, खर्च कम, liquidity सबसे ज़्यादा।

**Gates (protocol में पहले से lock होंगे):**
- Skill: AUC CI > 0.5, और नकली दिमाग से बेहतर।
- खर्च:
  - दोगुने खर्च पर भी net > 0।
  - Maker/taker और BNB discount की असली दरें S7 से ली जाएँगी।
- **मेल:** चल रहे F4 LS_RS से ≤ 0.70, या मिलाने पर Calmar बढ़े।
- हर साल और 2018–19 (frozen) पर जाँच होगी, साथ में PBO/DSR।
- सबसे बुरा 5% (bootstrap) नियम भी लागू होगा।

**उसके बाद का क्रम:**
- **R3:** 12h, सिर्फ़ तब जब R2 से कोई सबक मिले।
- **R4:** Weekly/monthly "मौसम" परत।
- **Swing के अलावा:**
  - Funding/basis carry: spot long + perp short, market-neutral। M4 और funding data जमा हो रहा है।
  - Maker orders से खर्च घटाना। यह हर timeframe की कमाई बढ़ाता है।

## 5. Real money से पहले (बदला नहीं)
- 4H system सिर्फ़ paper/forward और demo पर रहेगा।
- असली पैसे से पहले हर 4 घंटे पर चलने वाला intraday executor बनेगा, और फिर 90 दिन का forward test होगा।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
