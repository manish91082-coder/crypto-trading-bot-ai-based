# एक ही coin पर लॉन्ग + शॉर्ट: basis / cash-and-carry, funding arbitrage, delta-neutral, pairs trading (1D फोकस)

> नोट: शोध तारीख 2026-10-16। हर तथ्य के साथ स्रोत है। Single-source या आपस में टकराने वाले दावे साफ़ चिह्नित हैं (⚠)। इन notes में मैंने खुद कोई backtest नहीं चलाया, इसलिए हमारे data पर इनमें से कुछ भी verified नहीं है।

## 1. Cash-and-carry / funding arbitrage (spot long + USDT-M perp short): yield, negative funding, peer-reviewed सबूत

### Takeaway
Peer-reviewed और BIS सबूत यह दिखाते हैं कि crypto carry ऐतिहासिक रूप से औसतन ~8–10%+ सालाना रहा। 2021 में यह सबसे ऊँचा था, 2022–23 में बहुत कम (कुछ स्थितियों में funding हिस्सा negative), 2024 Q1 में फिर ऊँचा हुआ और 2025 में तेज़ी से दबा। एक survey के अनुसार 2025 में strategy का Sharpe negative रहा। Funding लगभग 16–18% दिनों में negative रहती है। Binance पर, high-fee tier में "random-maturity" arbitrage ने BTC पर ~6.4%/yr excess return दिया (2020–Mar 2024) और position सिर्फ ~20% समय ही खुली रही।

### Cited Findings
**Peer-reviewed / working papers**
- BIS WP 1087 (Schmeling, Schrimpf, Todorov, "Crypto carry", अप्रैल 2023, संशोधित अक्टूबर 2025): carry (futures−spot) का औसत 10% सालाना से ऊपर है, कभी-कभी 40% से ज़्यादा (summary page पर ~60% तक) पहुँचता है और समय के साथ बहुत बदलता है। Interest-rate अंतर इसके उतार-चढ़ाव का बहुत छोटा हिस्सा समझाते हैं। Carry के पीछे छोटे, trend-chasing निवेशकों की leveraged माँग है और arbitrage capital कम है (margin और regulatory friction की वजह से)। ऊँचा carry आगे के price crash की भविष्यवाणी करता है। Cash-and-carry करने वाला arbitrageur drawdown में margin spike और liquidation का जोखिम झेलता है। — [BIS WP 1087 page](https://bis.org/publ/work1087.htm); [BIS PDF](https://www.bis.org/publ/work1087.pdf); [CEPR DP20719](https://cepr.org/publications/dp20719)
- He, Manela, Ross, von Wachter ("Fundamentals of Perpetual Futures", arXiv 2212.06888 v5) का data: Binance spot और perp, 1-घंटे की frequency, 8 जनवरी 2020 से 11 मार्च 2024 तक; BTC, ETH, BNB, DOGE, ADA; funding 00/08/16 UTC पर। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
  - No-arbitrage price से औसत absolute deviation लगभग 60–90% सालाना है। Signed औसत ~0 है। Deviations सब coins में साथ-साथ चलते हैं और लगभग 11% प्रति वर्ष घटते हैं (पूरे sample में 44% से ज़्यादा)। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
  - Full-sample Sharpe (Table 5), high-cost tier (spot 6.75 bps, futures 1.44 bps): BTC 1.80, ETH 2.55, BNB 4.84, DOGE 3.58, ADA 2.68। No-fee tier में: BTC 3.53, ETH 4.83, BNB 12.31। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
  - Annualized excess return, high-cost tier: BTC 6.38%, ETH 9.59%, BNB 18.41%, DOGE 23.31%, ADA 12.03%। Strategy कितने समय active रही: BTC 20%, ETH 23%, BNB 35%, DOGE 29%, ADA 35%। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
  - BTC high-cost tier, साल-दर-साल (Table 6): return 2020 8.29%, 2021 14.81%, 2022 0.28%, 2023 1.11%, 2024 (मार्च तक) 11.97%। Sharpe क्रमशः 2.26, 2.39, 0.70, 1.32, 11.52। Active समय 2021 के 34% से गिरकर 2022 में 9% रह गया। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
  - BTC no-fee return 13.70% में से 8.64% price convergence से आया और 5.06% funding से। Funding का हिस्सा साल-दर-साल: 2020 +7.68%, 2021 +15.31%, 2022 −1.94%, 2023 −0.94%, 2024 +6.03%। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
  - Paper खुद लिखता है कि funding arbitrage "not risk-free" है, क्योंकि expiry तय नहीं है। Margin बनाए रखना पड़ता है और अस्थायी dislocation से liquidation हो सकता है। Spread और impact < 0.35 bps हैं, यानी fees से बहुत कम (यह सिर्फ़ 1 महीने के order-book data पर आधारित है)। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
  - ⚠ टकराव: उसी paper के v7 में Table 5 के साल-दर-साल return बहुत ऊँचे हैं (जैसे BTC 2021 64.81%, Sharpe 12.36; DOGE 2020 409%)। ये v5 के high-cost आँकड़ों (BTC 2021 14.81%) से मेल नहीं खाते। सम्भव है v7 में strategy या fee की परिभाषा अलग हो। मैं इसकी पुष्टि नहीं कर सका, इसलिए v7 के आँकड़े implementable return के रूप में इस्तेमाल न करें। — [arXiv v7](https://arxiv.org/html/2212.06888v7)
- Christin, Routledge, Soska, Zetlin-Jones ("The Crypto Carry Trade", draft अगस्त 2022): short futures + long spot, एक बड़े exchange पर। In-sample annual Sharpe 7–10 है। अलग से % return का आँकड़ा मुझे नहीं मिला। — [CMU PDF](https://www.andrew.cmu.edu/user/azj/files/CarryTrade.v1.0.pdf)
- Borri, Liu, Tsyvinski, Wu ("Cryptocurrency as an Investable Asset Class", arXiv 2510.14435): Binance BTC perp, 8 घंटे की frequency, अगस्त 2020 से मई 2025। Short perp + long spot का annualized Sharpe full sample में 6.45 है, 2024 से 4.06, और 2025 में negative। Funding का mean लगभग 8% है (paper साफ़ नहीं लिखता कि यह annualized है)। Profit का ज़्यादातर हिस्सा funding से आता है, और funding premia "neither guaranteed nor permanent" हैं। — [arXiv 2510.14435](https://arxiv.org/html/2510.14435)

**Practitioner data**
- Ethena docs (data 31 दिसंबर 2024 तक, लगभग 3 साल, Binance/Bybit-heavy, OI/volume-weighted): average annualized funding BTC 7.80% और ETH 9.15%। Negative funding वाले दिन BTC 15.9% और ETH 17.5%। सबसे लंबा negative streak 13 दिन, सबसे लंबा positive streak 176 दिन (2023 के अंत से 2024 की शुरुआत)। 3 साल में सिर्फ़ 1 quarter का औसत negative रहा (ETH PoW event)। Data provider का नाम नहीं दिया गया है। — [Ethena docs: funding risk](https://docs.ethena.fi/solution-overview/risks/funding-risk)
- **दो स्रोतों से cross-check (average yield):** Ethena docs का ~7.8–9% (लगभग 2022–2024) और Borri et al. का ~8% mean (Binance BTC, 2020–2025), साथ ही BIS का "औसत >10%" (dated futures basis सहित), आपस में मोटे तौर पर मेल खाते हैं। इसलिए "लंबे समय का औसत ~8–10%/yr" को दो से ज़्यादा स्रोतों से समर्थित माना जा सकता है।
- 2024 बनाम 2025 compression: BTC/ETH का aggregated funding 2024 में ~11% annualized था और 2025 में ~5%। sUSDe yield 2026 की शुरुआत में ~3.72% रहा। ⚠ यह secondary aggregator search snippet है और primary स्रोत verify नहीं हुआ। फिर भी दिशा Borri et al. के "2025 Sharpe negative" से मेल खाती है। — [Stablecoin Insider Q1 2026](https://stablecoininsider.org/ethena-usde-q1-2026-report/); [Borri et al.](https://arxiv.org/html/2510.14435)
- BitMEX Q3 2025 report: BitMEX पर BTC का mean funding लगभग 0.0081% प्रति 8 घंटे था (≈8.9% annualized), और rate अक्सर 0.01% baseline पर टिका रहा। Early bull market में funding 0.2% प्रति 8 घंटे से ऊपर गई। ⚠ यह search snippet से है; page fetch fail हुआ। — [BitMEX Q3 2025](https://www.bitmex.com/blog/2025q3-derivatives-report)
- Ethena sUSDe realized APY: 2024 में ~18% औसत, 2025 में 4–15% (secondary स्रोत)। अगस्त 2024 के funding inversion में yield 11 दिन में ~19% से ~4% पर आ गया। ⚠ ये secondary और single-source हैं। — [eco.com explainer](https://eco.com/support/en/articles/15254002-ethena-usde-and-susde-2026-delta-neutral-yield)
- Binance official funding formula: F = [P + clamp(0.01% − P, ±0.05%)] ÷ (8/N)। Default interest component 0.01%/8h है, यानी ≈10.95% annualized। जब premium −0.04% से +0.06% के बीच हो, तब funding ठीक 0.01% रहता है। 2025-05-02 से cap या floor छूने पर funding interval 1 घंटा हो जाता है। 2026-01-02 से, 16 लगातार settlements में |rate| ≤ 0.025% रहने पर interval 4 घंटे पर लौट आता है। BTCUSDT/ETHUSDT का cap/floor ±0.75 × MMR है, बाकी symbols का ±2%। — [Binance FAQ funding rates](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- Glassnode annualized funding को इस तरह परिभाषित करता है: 8h rate × 3 × 365। — [Glassnode chart](https://studio.glassnode.com/charts/futures-annualized-yield?a=BTC)

### Inferences
- Binance का default 0.01%/8h baseline (≈10.95%/yr) ही वह "छत" है जिसके पास शांत bull market में funding रहती है। इसलिए "~8–11%" का long-run औसत ज़्यादातर इसी interest component से आता है, असली premium से नहीं। Bear या choppy दौर (2022–23, 2025) में net yield gross से काफ़ी नीचे गिर जाती है।
- He et al. का BTC 2022 return (0.28%) दिखाता है कि bear साल में carry लगभग शून्य हो जाता है। Regime-switching (सिर्फ़ ऊँची funding में position खोलना) ज़रूरी लगता है। Paper की strategy भी सिर्फ़ 20–35% समय active रहती है।
- Altcoins (BNB/DOGE/ADA) पर yield और Sharpe ज़्यादा है, लेकिन वहाँ liquidation और depeg tail risk भी ज़्यादा है (section 2 देखें)।

### Gaps
- 2020–2026 के लिए हर साल का OI-weighted average funding (Coinglass या Kaiko table) किसी primary स्रोत से नहीं मिला। Kaiko research search में कुछ नहीं आया। साल-दर-साल आँकड़े अभी सिर्फ़ He et al. की strategy-level संख्याओं और aggregator snippets पर टिके हैं। सुझाव: हम Binance API (`/fapi/v1/fundingRate`) से 2020–2026 का पूरा history खुद निकालें, SHA-lock करें और per-year mean, %negative और max-negative streak निकालें। यह project के evidence नियम के अनुरूप है।
- 2026 YTD funding का कोई verified आँकड़ा नहीं मिला।
- BIS paper की BTC/ETH-wise तालिका (Sharpe, sample period) PDF से नहीं निकल पाई, सिर्फ़ summary मिली।

## 2. असली जोखिम: counterparty (FTX), basis blowout, short-leg liquidation, funding flip, wallet transfer, Binance portfolio margin

### Takeaway
Same-coin hedge price risk हटाता है, लेकिन venue, liquidation, ADL, collateral-depeg और funding-flip जोखिम बने रहते हैं। FTX (नवंबर 2022) में exchange पर रखा पूरा collateral फँस गया। 10 अक्टूबर 2025 को $19B+ liquidation, ADL और Binance पर USDe/wBETH/BNSOL का depeg (USDe ~$0.65) हुआ, जिससे साबित हुआ कि "hedged" खाता भी collateral pricing की वजह से liquidate हो सकता है।

### Cited Findings
- FTX collapse के बाद market-neutral funds का पैसा फँसा। Galois Capital की लगभग आधी capital FTX पर थी और Wintermute के $55M। एक fund ने अपने market-neutral और trend fund दोनों में FTX exposure write off किया। Binance पर BUSD-margined और USDT-margined BTC futures के बीच का gap हफ़्ते भर में औसतन ~15–17 pp annualized तक खुल गया। — [BNN Bloomberg](https://www.bnnbloomberg.ca/traders-flee-crypto-markets-after-ftx-collapse-1.1849179)
- He et al. के अनुसार FTX collapse के बाद solvent exchanges पर funding काफ़ी negative हो गई, और मार्च 2020 में भी लगभग सभी exchanges पर negative रही। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
- 10–11 अक्टूबर 2025 (Galaxy Research): लगभग 24 घंटे में $19B से ज़्यादा liquidation हुआ, जो रिकॉर्ड पर सबसे बड़ा है (पिछला ~$10B, 17 अप्रैल 2021)। BTC intraday ~−10% और ETH ~−13% गिरा। Binance पर USDe ~$0.65 तक गया जबकि दूसरे venues पर par के पास रहा। wBETH और BNSOL में peg से ~80–90% की गिरावट आई। ADL कई venues पर चला और "trims winners", यानी फ़ायदे वाली positions (जिनमें hedge की short leg भी हो सकती है) ज़बरदस्ती घटाई गईं। Binance उस समय इन assets की margin pricing को price-based से redemption-based पर ले जा रहा था, जो पूरा नहीं हुआ था। बाद में उसने ~$300M compensation दिया। — [Galaxy Research](https://www.galaxy.com/insights/research/cryptos-flash-crash-liquidation-binance-adl-auto-deleveraging)
  - ⚠ Galaxy यह नहीं बताता कि delta-neutral books पर ADL का असर ठीक-ठीक क्या हुआ। Galaxy की Binance और Hyperliquid में financial interest भी disclosed है।
- Unified Account की आलोचना: yield-bearing assets collateral के रूप में इस्तेमाल हो रहे थे और उनकी liquidation price Binance के अपने order book पर निर्भर थी। ⚠ यह opinion piece है, official finding नहीं। — [Wublock substack](https://wublock.substack.com/p/opinion-is-this-crash-an-attack-on)
- Binance Portfolio Margin: secondary स्रोतों के अनुसार unified maintenance margin ratio 105% से नीचे जाने पर liquidation शुरू होता है। Collateral ratio और leverage tiers में बार-बार बदलाव हुए (दिसंबर 2025, मार्च 2026)। ⚠ ये secondary हैं और official help page verify नहीं हुआ। — [MEXC news aggregator](https://www.mexc.com/news/590740)
- Funding cap अब dynamic है: cap छूने पर funding hourly हो जाती है। इसका मतलब spike में short leg को funding मिलती है (यह फ़ायदा है), लेकिन negative cap पर short को हर घंटे भुगतान करना पड़ता है। — [Binance FAQ](https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031)
- Ethena: reserve fund थोड़े समय की negative funding को सह लेता है, पर महीनों लंबी negative funding reserve को खा जाएगी। Reserve का आकार ~1.1–1.2% of supply है (secondary स्रोत आपस में टकराते हैं)। — [Stablecoin Insider](https://stablecoininsider.org/ethena-usde-q1-2026-report/); [bex.co](https://bex.co/blog/2026/03/13/ethena-usde-systemic-defi-collateral-concentration-risk)
- BIS के अनुसार carry arbitrage इसलिए सीमित है क्योंकि drawdown में margin spike और liquidation होते हैं। ऊँचा carry crash से पहले आता है। — [BIS WP 1087](https://bis.org/publ/work1087.htm)

### Inferences
- Short-leg liquidation की प्रक्रिया: spot (Spot wallet) और perp (USDT-M wallet) अलग-अलग हों और isolated 1x short हो, तो price के ~+100% spike पर short liquidate हो जाता है, जबकि spot का फ़ायदा दूसरे wallet में पड़ा रहता है। Daily rebalance में अगर समय पर margin transfer न हो, तो hedge टूट जाता है। Portfolio Margin या Unified Account यह समस्या हल करता है, लेकिन बदले में collateral haircut और depeg का जोखिम जोड़ता है, जैसा अक्टूबर 2025 में हुआ।
- Basis blowout (perp का spot से नीचे जाना) mark-to-market loss देता है, जो convergence होने पर वापस आ जाता है। लेकिन perp की expiry नहीं होती, इसलिए convergence की कोई guarantee नहीं है (He et al.)।
- Counterparty risk एक ही exchange पर केंद्रित रहता है। दोनों legs एक ही venue पर हों तो venue failure में दोनों डूबते हैं।

### Gaps
- Binance Portfolio Margin और Unified Account के official नियम (कौन-सा spot collateral है, कितना haircut, USDT-M short के साथ netting) primary स्रोत से verify नहीं हुए।
- 10 अक्टूबर 2025 को ADL से कितने hedged accounts की short leg कटी, इसकी कोई गिनती नहीं मिली।
- Binance पर small-cap altcoin delta-neutral positions के liquidation के आँकड़े नहीं मिले।

## 3. Pairs trading / cointegration stat-arb (crypto, daily, costs के बाद)

### Takeaway
Daily-frequency crypto pairs trading का सबूत कमज़ोर और मिला-जुला है। ज़्यादातर studies में costs के बाद return शून्य के पास या negative आता है, और hourly या intraday पर costs edge खत्म कर देते हैं। कुछ अच्छे नतीजे hyperparameter चुनने पर निर्भर हैं (data-snooping का खतरा)।

### Cited Findings
- Fil & Kristoufek (IEEE Access 2020): Binance के 26 liquid coins पर 5-minute, 1-hour और daily frequency की जाँच। Strategies classical benchmarks से कमज़ोर रहीं। सबसे आम daily distance method का return −0.07% प्रति माह रहा, जबकि 5-minute पर 11.61% प्रति माह। ⚠ यह साफ़ नहीं कि 11.61% net है या gross। — [IEEE 9200323](https://ieeexplore.ieee.org/document/9200323)
  - ⚠ टकराव: उसी काम के working-paper version (Charles University) में daily distance method "baseline real-life conditions" में 3% मासिक कमाता है, cointegration method हमेशा हल्का नुकसान देता है, और strategy execution और costs के प्रति "very sensitive" है। — [CUNI dspace](https://dspace.cuni.cz/handle/20.500.11956/109634)
- Leung & Nguyen (2019, Studies in Economics and Finance): Coinbase के daily data पर BTC/ETH/BCH/LTC के cointegrated portfolios (Johansen और Engle–Granger), जो कई configurations में "profitable" रहे। Secondary review के अनुसार 1.5σ threshold optimal रहा और stop-loss लगाने से return घटा। Exact return संख्याएँ full text न मिलने से verify नहीं हुईं। — [RePEc](https://ideas.repec.org/a/eme/sefpps/sef-08-2018-0264.html); [TDS review](https://towardsdatascience.com/constructing-cointegrated-cryptocurrency-portfolios-d0a27922891e/)
  - Dann & Kotsireas (2024) follow-up: backtest में 100% win rate, लेकिन live bot का benchmark पर excess return −0.4% से +8.1% के बीच रहा। — [IDEAS](https://ideas.repec.org/h/spr/lnopch/978-3-031-68974-1_16.html)
- Tadi & Witzany (Financial Innovation 2024, arXiv 2305.06961): copula + cointegration। एक cointegration strategy hourly पर gross 33.8% थी, लेकिन net −23.7% (Sharpe −0.87)। Reference-asset copula variant का net Sharpe hourly पर 1.45 और 5-minute पर 2.66 रहा। — [Springer Financial Innovation](https://link.springer.com/article/10.1186/s40854-024-00702-7); [arXiv](https://arxiv.org/abs/2305.06961v1)
- Pindza & Mba (QFE 2026): cointegration (ADF/KSS) + copula strategies costs के बाद net negative रहीं। Market overlay variant लगभग buy-and-hold जैसा चला। — [AIMS QFE 2026](https://www.aimspress.com/article/doi/10.3934/QFE.2026016)
- Univ. of Turku thesis (मार्च 2020 से 2022 के अंत तक): daily data पर costs के बाद सिर्फ़ cointegration method profitable रहा। Hourly पर costs के बाद सब methods घाटे में रहे। ⚠ यह thesis है, peer-reviewed नहीं। — [UTUPub](https://www.utupub.fi/handle/11111/24573)

### Inferences
- Daily पर turnover कम होने से costs का बोझ घटता है, पर edge भी पतला है। Studies आपस में टकराती हैं, इसलिए pairs trading को proven edge नहीं माना जा सकता।
- हमारी cross-sectional long-short (top-5 long, bottom-5 short) पहले से ही एक तरह का "basket stat-arb" है। Pairs layer जोड़ने से correlated bets बढ़ सकते हैं, edge नहीं।

### Gaps
- Crypto pairs-trading returns के समय के साथ घटने (2018 → 2025) का कोई rolling-window study नहीं मिला।
- Fil & Kristoufek के दो versions के बीच 3% और −0.07% के अंतर की वजह (cost assumption) verify नहीं हुई।

## 4. Long spot portfolio को BTC/ETH perp short से beta-hedge करना: drawdown और return पर असर

### Takeaway
Peer-reviewed सबूत नहीं मिला। Quantpedia (practitioner) के in-sample backtest में altcoin top-5 index को BTC से hedge करने पर max drawdown −77% से घटकर −22% से −37% रहा, जबकि return 57% से घटकर ~44–47% हुआ (2019–2023)। यह hindsight-designed है।

### Cited Findings
- Quantpedia "Systematic Hedging of the Cryptocurrency Portfolio": market-cap-weighted top-5 altcoin index (T5) पर, पूरे समय का in-sample OLS beta BTC पर ~0.97। 1:1 hedge के बाद T5−BTC spread की average yearly volatility 2015–2018 में 3.94% और 2019–2023 में 2.48% रही। Rolling regression की छोटी window slope कम दिखाती है, जिससे portfolio under-hedged रहता है। Trend-filter hedge (BTC high पर unhedged, बाकी समय 1:1 short) के 2019–2023 नतीजे: unhedged 57% return, 67% vol, −77% MDD; hedged ~44–47% return, 34–43% vol, −22% से −37% MDD। लेखक खुद मानते हैं कि नियम hindsight से बनाए गए। ⚠ यह practitioner और in-sample स्रोत है। — [Quantpedia](https://quantpedia.com/systematic-hedging-of-the-cryptocurrency-portfolio/)
- 10X Research (Markus Thielen, 2024) ने liquid altcoin perps की basket short करने की सलाह दी। यह analyst राय है, backtest नहीं। — [Decrypt](https://decrypt.co/245310/hedge-bitcoin-exposure-by-shorting-altcoins-during-murky-market-says-analyst)
- He et al. के अनुसार deviations सब coins में साथ चलते हैं, यानी crypto में common factor प्रभावी है। Beta hedge इसी common factor को हटाता है। — [arXiv v5](https://arxiv.org/html/2212.06888v5)

### Inferences
- हमारे सिस्टम में top-5 long spot और bottom-5 short perp वाला book पहले से ही मोटे तौर पर dollar-neutral है, लेकिन beta-neutral होना ज़रूरी नहीं। आमतौर पर bottom-5 "loser" coins का beta ज़्यादा होता है। यह hypothesis है, हमारे data पर verify करना होगा। एक तरीका: book के net beta (rolling 60–90 दिन, BTC पर) को BTC-perp की छोटी position से शून्य करना। इसकी लागत funding है: BTC short को आमतौर पर funding मिलती है (8–10% औसत), इसलिए hedge अक्सर कमाई भी देता है।
- Hedge short पर funding positive होती है, इसलिए यह overlay bull दौर में "carry" कमाता है, और bear दौर में (जब funding negative होती है) थोड़ा खर्च करता है लेकिन drawdown घटाता है।

### Gaps
- Crypto beta-hedge पर कोई peer-reviewed या out-of-sample study नहीं मिली।
- Short perp leg पर funding को शामिल करके hedged portfolio का net return किसी स्रोत में नहीं मिला।

## 5. Fees और funding के बाद net returns; capacity ($10k बनाम बड़े खाते); हमारे सिस्टम के साथ जोड़

### Takeaway
Binance high-fee tier पर BTC cash-and-carry लगभग 6%/yr excess (2020–Mar 2024) देता था, लेकिन 2022–23 में लगभग 0% और 2025 में (survey के अनुसार) negative risk-adjusted रहा। $10k खाते के लिए capacity कोई समस्या नहीं है। बड़े पैमाने पर capacity सीमित है: Ethena का $15B तक बढ़ना और फिर सिकुड़ना funding compression से जुड़ा माना जाता है।

### Cited Findings
- He et al. की fee tiers: high = spot 6.75 bps + futures 1.44 bps। Spread और impact < 0.35 bps। High-cost BTC return 6.38%/yr और ETH 9.59%/yr। — [arXiv v5](https://arxiv.org/html/2212.06888v5)
- USDe supply का peak ~$14.7–15B (सितंबर/अक्टूबर 2025) रहा, उसके बाद तेज़ गिरावट (2026 में ~$4–6B; स्रोत आपस में टकराते हैं)। Funding 2024 में ~11% से 2025 में ~5% पर आई। ⚠ ये secondary स्रोत हैं। — [Stablecoin Insider](https://stablecoininsider.org/ethena-usde-q1-2026-report/); [blockeden forum](https://blockeden.xyz/forum/t/ethena-usde-hit-12b-supply-and-offers-7-30-apy-is-this-sustainable-or-terra-2-0/357)
- BIS: arbitrage capital की कमी (margin और regulatory friction) carry को ऊँचा रखती है। — [BIS WP 1087](https://bis.org/publ/work1087.htm)
- He et al.: deviations ~11% प्रति वर्ष घट रहे हैं, यानी edge decay हो रहा है। — [arXiv v5](https://arxiv.org/html/2212.06888v5)

### Inferences
- $10k खाते के लिए: He et al. की "high" fee tier (6.75 bps spot) असल retail VIP0 taker fees से कम लगती है। Retail fees मैंने इस शोध में verify नहीं कीं, इसलिए छोटे खाते का net return paper के 6.4% से कम होने की संभावना है, खासकर अगर बार-बार entry और exit हो। Daily horizon पर, सिर्फ़ ऊँची funding में position खोलने और लंबे समय तक रखने से fee drag कम रहता है।
- 1x isolated short और spot के अलग-अलग wallets में daily margin top-up की ज़रूरत पड़ती है। $10k पर एक coin में 100% move के लिए buffer रखना होगा, जिससे capital efficiency घटती है (net yield पूरे capital पर कम बैठती है)।
- **हमारे cross-sectional सिस्टम के साथ जोड़ने के विकल्प** (सब hypotheses हैं; pre-registered backtest, SHA lock और verifier ज़रूरी):
  1. **Beta overlay:** book का rolling net beta निकालकर उसे BTC/ETH perp से शून्य करना। इससे market crash में drawdown घटना चाहिए (Quantpedia की दिशा)।
  2. **Idle-capital carry sleeve:** जो USDT capital इस्तेमाल नहीं हो रहा, उसे BTC/ETH spot + perp short में तभी लगाना जब funding threshold (जैसे > 0.01%/8h) से ऊपर हो। He et al. के अनुसार यह 20–35% समय ही active रहेगा।
  3. **Short-leg funding filter:** bottom-5 short perps में से उन coins को बाहर करना या कम weight देना जिनकी funding बहुत negative है (short को भुगतान करना पड़ता है)। Top-5 long को spot में रखने पर funding का असर नहीं पड़ता।
  4. **Tail guard:** Unified Account में yield-bearing collateral (USDe, wBETH) से बचना। अक्टूबर 2025 की घटना ने यह जोखिम दिखाया।

### Gaps
- Binance की retail VIP0 spot और futures maker/taker fees और BNB discount इस शोध में verify नहीं हुए।
- Small बनाम large account पर capacity या slippage का कोई मात्रात्मक study (जैसे $10k बनाम $10M पर alt perps) नहीं मिला।
- Cross-sectional long-short और carry/beta overlay को मिलाने पर कोई प्रकाशित study नहीं मिली। इसके लिए हमें अपना backtest करना होगा।
