# क्रिप्टो USDT-M perpetual पर SHORT जोखिम नियंत्रण और long-short पोर्टफोलियो का tail-risk hedge

> स्रोत-स्थिति (ज़रूरी चेतावनी): इस सत्र में binance.com (FAQ/announcement पेज) WebFetch से नहीं खुल सका ("Unable to verify if domain www.binance.com is safe to fetch")। इसलिए Binance की यांत्रिकी केवल (a) आधिकारिक API docs (developers.binance.com, जो खुला) और (b) तृतीय-पक्ष/समाचार स्रोतों से सत्यापित है। जहाँ आधिकारिक पुष्टि नहीं है, वहाँ साफ़ "असत्यापित" लिखा है। कोई संख्या गढ़ी नहीं गई है।
> हमारा संदर्भ: short book = AI-rank के bottom-5 coins, हर एक 10%, 1x isolated; stop (entry x1.5) + 30-दिन cooldown से पहले 69 liquidations; short P&L कुछ 2025-26 new listings में केंद्रित; shorts ने net funding चुकाई।

## 1. क्रिप्टो में short squeeze / pump-and-dump: प्रकरण और आवृत्ति

### Takeaway
Pump-and-dump (P&D) अल्प/मध्य-cap coins में संगठित और बार-बार होने वाली घटना है (Telegram समूह औसतन लगभग रोज़ 2 बार)। इनमें कीमत, volume और volatility में अल्पकालिक उछाल आता है, फिर तेज़ reversal होता है। Short के लिए असली ख़तरा उछाल वाला हिस्सा है: 1x isolated short उसी दौरान liquidate हो सकता है, reversal आने से पहले। "Large/mid-cap coin एक दिन/सप्ताह में कितनी बार +50% चढ़ता है", इसकी कोई प्रकाशित, survivorship-aware संख्या नहीं मिली। यह संख्या हमें अपने डेटा से गिननी होगी।

### Cited Findings
- Li, Shin और Wang, "Cryptocurrency Pump-and-Dump Schemes", Journal of Financial and Quantitative Analysis (JFQA) में प्रकाशित (Cambridge पर online 4 अप्रैल 2025)। यह *Quantitative Finance* में नहीं है। निष्कर्ष: P&D से कीमत, volume और volatility में अल्पकालिक spike आता है, फिर तेज़ reversal होता है। scheme शुरू होने से पहले की price run-up से insiders की ओर धन-हस्तांतरण का संकेत मिलता है। — [Cambridge/JFQA abstract](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/cryptocurrency-pumpanddump-schemes/97149DCD519BAF838F269F98DC76D682); [JFQA PDF](https://jfqa.org/wp-content/uploads/2025/01/24639_Cryptocurrency-Pump-and-Dump.pdf)
- उसी पेपर के natural experiments: दो exchanges ने अपनी P&D नीति बदली (जैसे Bittrex ने 24 नवम्बर 2017 को P&D पर ban लगाया)। difference-in-differences के अनुसार P&D से coin की liquidity और कीमत दोनों गिरती हैं। — [ABFER working paper](https://abfer.org/media/abfer-events-2019/annual-conference/investment-finance/AC19P3078_Cryptocurrency_Pump-and-Dump_Schemes.pdf); [CLS Blue Sky Blog](https://clsbluesky.law.columbia.edu/2019/01/07/cryptocurrency-pump-and-dump-schemes/)
- Xu और Livshits, "The Anatomy of a Cryptocurrency Pump-and-Dump Scheme" (USENIX Security 2019): Telegram पर 17 जून 2018 से 26 फ़रवरी 2019 के बीच 412 P&D घटनाएँ। पहले के arXiv v1 में 21 जुलाई से 18 नवम्बर 2018 के बीच 220 घटनाएँ थीं, यानी दोनों versions के आँकड़े अलग हैं। — [USENIX](https://www.usenix.org/conference/usenixsecurity19/presentation/xu-jiahua); [arXiv](https://arxiv.org/pdf/1811.10109)
- दिसम्बर 2018 की news के अनुसार 100 से ज़्यादा channels औसतन लगभग रोज़ दो pump करते थे, जिससे हर महीने लगभग $7M की कृत्रिम trading volume बनती थी। (यह preprint की news-रिपोर्टिंग है, USENIX पेपर की संख्या नहीं।) — [The Next Web](https://thenextweb.com/news/ai-pump-dump-predictor-telegram)
- Altcoin short squeeze का उदाहरण: अगस्त 2023 में LPT और BLZ लगभग 150% चढ़े और funding rates बहुत ऊँचे स्तर पर पहुँचे (शीर्षक के अनुसार "2000%" annualized)। यह news स्रोत है। — [FXStreet](https://www.fxstreet.com/cryptocurrencies/news/short-squeezes-for-lpt-blz-send-the-altcoins-almost-150-north-with-funding-rates-hitting-2000-202308142359)
- Altcoins के return tails भारी हैं: sample के सभी altcoins में kurtosis 3 से अधिक है, और power-law tails stylized fact हैं। — [Grobys 2024 (Osuva)](https://osuva.uwasa.fi/bitstream/10024/17187/2/Osuva_Grobys_2024.pdf)
- डिजिटल assets में daily और high-frequency दोनों स्तरों पर extreme returns अक्सर होते हैं। — [arXiv 2110.09429](https://arxiv.org/pdf/2110.09429)
- बाज़ार परिपक्व होने के साथ बड़े coins (BTC, LTC, ETH, XRP) के tails हल्के हुए हैं। — [Teesside/Huddersfield EVT study](https://research.tees.ac.uk/en/publications/an-application-of-autoregressive-extreme-value-theory-to-cryptocu/)
- Kamps और Kleinberg (Crime Science 2018) P&D detection पर काम करते हैं। उनका PDF मिला है, पर इस सत्र में उसके निष्कर्ष पढ़े नहीं गए। — [Crime Science PDF](https://crimesciencejournal.biomedcentral.com/track/pdf/10.1186/s40163-018-0093-5)

### Inferences
- P&D पैटर्न (spike के बाद reversal) बताता है कि "कमज़ोर" coins को short करने का औसत edge हो सकता है। लेकिन path risk बहुत बड़ा है: 1x isolated short लगभग +90 से +100% mark-price उछाल पर liquidate होता है (गणना section 2 में)। इसलिए reversal का लाभ मिलने से पहले ही position बंद हो सकती है। हमारे 69 liquidations इसी पैटर्न से मेल खाते हैं।
- Li-Shin-Wang के अनुसार P&D से liquidity घटती है। यानी पंप के बाद stop/exit पर slippage बढ़ेगा।
- BTC/ETH जैसे बड़े coins के tails हल्के होने का मतलब है कि squeeze-जोखिम मुख्यतः छोटे, नए और कम-liquidity coins में है। हमारा bottom-5 rank स्वभावतः इन्हीं की ओर झुकता है।

### Gaps
- Large/mid-cap coins में +50% प्रति दिन या प्रति सप्ताह की आवृत्ति का कोई प्रकाशित, सत्यापित आँकड़ा नहीं मिला। सुझाव: `data/universe_all` (1d) पर गिनें कि कितने coin-days में close-to-close या high/prev-close +50% है। इसे market-cap bucket के हिसाब से बाँटें, और delisted coins भी शामिल करें।
- Kamps और Kleinberg के विशिष्ट निष्कर्ष इस सत्र में नहीं पढ़े गए।

## 2. Binance USDT-M यांत्रिकी जो shorts के लिए प्रासंगिक है

### Takeaway
आधिकारिक API docs से पुष्टि हुई है कि conditional (algo) STOP_MARKET का `workingType` default रूप से **CONTRACT_PRICE** (last price) है, MARK_PRICE नहीं। `priceProtect` default रूप से **false** है। जबकि liquidation mark price पर होता है। यानी default stop और liquidation अलग-अलग कीमतों पर चलते हैं। Maintenance-margin tiers, liquidation fee, insurance fund और ADL के लिए आधिकारिक Binance FAQ इस सत्र में नहीं खुल सका, इसलिए वे विवरण तृतीय-पक्ष स्रोतों से हैं।

### Cited Findings
- **Algo/conditional order (आधिकारिक API):** New Algo Order endpoint `/fapi/v1/algoOrder` से TP/SL और trailing stop लगते हैं। `workingType` के मान MARK_PRICE या CONTRACT_PRICE हैं, और default CONTRACT_PRICE है। — [Binance USDⓈ-M Trade REST API](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api)
- **priceProtect (आधिकारिक API):** यह STOP_MARKET और TAKE_PROFIT_MARKET के साथ इस्तेमाल होता है, default `false` है। चालू होने पर MARK_PRICE और CONTRACT_PRICE का अंतर symbol के price-protection threshold से अधिक नहीं होना चाहिए। — [Binance Trade REST API](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api)
- **Trigger नियम (आधिकारिक API):** BUY STOP_MARKET (short का stop) तब trigger होता है जब latest price (MARK या CONTRACT) >= triggerPrice हो। `closePosition=true` से सारी short position बंद होती है। इसे `quantity` या `reduceOnly` के साथ नहीं भेज सकते। — [Binance Trade REST API](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api)
- **Order filters (आधिकारिक API):** PERCENT_PRICE filter BUY/SELL कीमतों को mark price के सापेक्ष सीमित करता है। MIN_NOTIONAL market orders का मूल्य mark price से आँकता है। STOP_MARKET, MAX_NUM_ALGO_ORDERS filter के अंतर्गत आता है। — [Binance Common Definition](https://developers.binance.com/docs/derivatives/usds-margined-futures/common-definition)
- **Mark price और maintenance margin (तृतीय-पक्ष):** Mark price index price और funding घटक से बनता है, ताकि अल्पकालिक spikes से अनुचित liquidation न हो। Isolated mode में margin equity गिरकर maintenance margin के स्तर पर पहुँचे तो liquidation होता है। Margin rate position size के हिसाब से tiered है। — [Binance Square explainer](https://www.binance.com/sv/square/post/43087); [Picol docs](https://intercom.help/picol/en/articles/16537710-liquidation)
- **Liquidation/clearance fee (असत्यापित, स्रोतों में टकराव):** एक explainer के अनुसार Level-1 (500k USDT से कम) पर notional का 0.5% शुल्क है। Chaos Labs की तुलनात्मक समीक्षा के अनुसार यह शेष collateral का 0.75% से 2.25% तक है, जो market पर निर्भर है। — [Binance Square](https://www.binance.com/sv/square/post/43087); विरोधाभास: [Chaos Labs review](https://chaos-labs.notion.site/EXT-Competitive-Review-of-Liquidation-Fees-7484ac341b3d473eb4a9c108cd24f18c)
- **ADL (सामान्य उद्योग यांत्रिकी, Binance का आधिकारिक पाठ नहीं):** यदि liquidated position bankruptcy price पर या उससे बेहतर कीमत पर बंद नहीं होती, तो नुकसान insurance fund उठाता है। fund कम पड़े तो ADL मुनाफ़े वाले, ऊँचे leverage वाले विपरीत traders को bankruptcy price पर ज़बरन बंद करता है। ranking = unrealized PnL% × effective leverage, और queue position "lights" indicator पर दिखती है। — [BitMEX support](https://support.bitmex.com/hc/en-gb/articles/18589621443357); [BingX ADL](https://bingx.com/en/support/articles/11263299764495)
- **Insurance fund का इतिहास:** 19 मई 2021 के crash के दौरान Binance ने retail trading रोकी। back-filled transactions Benford's Law से मेल नहीं खाते थे, और Binance तथा दूसरे exchanges के बीच BTC futures price gap संदर्भ-अवधि से लगभग 7 गुना था। लेखकों ने इसे insurance fund के नुकसान को सीमित करने के हित से जोड़ा। (यह working paper है, peer-reviewed नहीं।) — [IWH Discussion Paper 2022-25](https://www.iwh-halle.de/en/publications/detail/bitcoin-flash-crash-on-may-19-2021-what-did-really-happen-on-binance); [Baumgartner PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/686754/6b-Tim-Baumgartner-May19.pdf)
- **10–11 अक्टूबर 2025 crash:** 24 घंटे में लगभग $19B के liquidations हुए, जो पिछले किसी भी एक-दिन रिकॉर्ड से लगभग 9 गुना थे। trigger 100% China tariffs की घोषणा थी। BTC लगभग 14% गिरा, SOL intraday 40% से अधिक गिरा, और ATOM ने कुछ समय के लिए लगभग शून्य की कीमत print की। कई platforms ने ADL का सहारा लिया। — [FTI Consulting](https://fticonsulting.com/insights/articles/crypto-crash-october-2025-leverage-met-liquidity); [CoinGecko](https://www.coingecko.com/learn/october-10-crypto-crash-explained); [Insights4VC](https://insights4vc.substack.com/p/inside-the-19b-flash-crash)
- **Binance की अक्टूबर 2025 क्षतिपूर्ति:** लगभग $283M उन users को दिए गए जिनकी positions USDe, BNSOL या WBETH collateral के depeg के दौरान liquidate हुईं (10-10-2025, 21:36 से 22:16 UTC)। Binance पर USDe कुछ समय के लिए $0.66 से नीचे गया। Binance ने कहा कि ATOM जैसे tokens पर सालों पुराने limit orders ने भी गिरावट बढ़ाई। Binance ने ADL या insurance fund के इस्तेमाल पर कोई आधिकारिक आँकड़ा नहीं दिया। "Binance ने internal ADL इस्तेमाल किया" वाला दावा केवल एक research पेपर में है और असत्यापित है। — [The Block](https://theblock.co/post/374295/binance-pays-283-million-in-compensation-following-fridays-depegs-covering-user-losses); [Decrypt](https://decrypt.co/344026/binance-reimburses-283m-after-market-crash-and-asset-depegging-issues); [Research Square](https://www.researchsquare.com/article/rs-9459584/v1)
- **Funding interval और caps (समाचार/repost, आधिकारिक पेज नहीं खुला):** 12 अक्टूबर 2023 से कुछ contracts का settlement 8h से 4h हुआ। 2025 में ORCAUSDT 4h से 2h हुआ। 2025 के एक नियम के अनुसार hourly interval वाला contract, लगातार 36 cycles तक rate ±0.002% के भीतर रहने पर, 4h पर लौटता है (प्रभावी 1 सितम्बर 2025)। इससे संकेत मिलता है कि 1h interval मौजूद है, पर इसकी सीधी आधिकारिक पुष्टि नहीं मिली। Caps contract-विशेष हैं, जैसे ALPACAUSDT ±4.00% और TACUSDT ±2.00% (price-protection event में अस्थायी रूप से ±0.005%)। — [TechFlow repost](https://www.techflowpost.com/en-US/newsletter/75976); [U.Today](https://u.today/binance-releases-important-funding-update)
- **Funding formula (तृतीय-पक्ष):** Funding = Premium Index + clamp(Interest − Premium, ±0.05%), जहाँ interest = 0.01% प्रति 8h (0.03% प्रति दिन)। positive rate पर longs shorts को भुगतान करते हैं, negative rate पर shorts longs को। — [TradingView script description](https://kr.tradingview.com/script/9oo2FQD5-Binance-Funding-Rate-Inverted)

### Inferences
- **1x isolated short का liquidation स्तर (गणित, स्रोत नहीं):** entry P0, margin = P0·Q। liquidation तब होगा जब P0·Q − (P−P0)·Q = mmr·P·Q, यानी P_liq = 2·P0/(1+mmr)। mmr 1% पर यह लगभग 1.98·P0 है, mmr 5% पर लगभग 1.90·P0। fee/clearance इसे थोड़ा नीचे लाएँगे। अर्थात 1x short लगभग +90 से +98% mark-price उछाल पर मरता है। entry x1.5 का stop इससे पहले, लगभग +50% पर, कटता है। यह हमारी पिछली व्यवस्था से संगत है।
- default `workingType=CONTRACT_PRICE` पर पतली book वाले coin का last-price wick stop trigger कर सकता है, भले mark price वहाँ न पहुँचा हो। उलटे, `MARK_PRICE` पर stop देर से लगता है पर wick से बचता है। liquidation mark price पर होता है, इसलिए stop को liquidation से पहले लगने की गारंटी के लिए MARK_PRICE trigger अधिक संगत है। `priceProtect=true` से असामान्य mark/last अंतर पर trigger रुकता है। यह suspicious wick से बचाता है, पर असली squeeze में stop न लगने का जोखिम भी पैदा करता है। इस trade-off को backtest/testnet पर जाँचना होगा।
- STOP_MARKET trigger होने के बाद market order है, इसलिए gap/squeeze में slippage असीमित है। daily-bar backtest में stop को "ठीक x1.5 पर fill" मानना आशावादी है। fill को max(trigger, उस bar का open/high-आधारित gap) से model करना चाहिए।
- ADL से shorts को सीधा नुकसान नहीं होता (उल्टा मुनाफ़े वाला short ADL से ज़बरन बंद हो सकता है)। अक्टूबर 2025 जैसी घटना में मुनाफ़े वाले shorts bankruptcy price पर बंद हुए, यानी hedge टूटता है और long book बिना hedge के रह जाता है।
- Funding interval 4h/1h होने पर short की funding लागत दिन में 6 से 24 बार लगती है। squeeze के दौरान, जब cap ±2% से ±4% हो, यह बहुत तेज़ी से जमा हो सकती है।

### Gaps
- आधिकारिक Binance FAQ से maintenance margin tiers (symbol-wise), liquidation/clearance fee की सटीक दर, insurance fund का आकार, ADL ranking formula, और "price protection" threshold के मान इस सत्र में सत्यापित नहीं हुए, क्योंकि binance.com fetch नहीं हुआ। सुझाव: API `GET /fapi/v1/leverageBracket` (maintMarginRatio tiers), `GET /fapi/v1/fundingInfo` (cap, floor, interval), और `GET /fapi/v1/exchangeInfo` (triggerProtect) से सीधे मान लें और उन्हें SHA-lock करें।
- 1h funding interval की आधिकारिक घोषणा का URL नहीं मिला।

## 3. Funding: shorts ने ऐतिहासिक रूप से कितना चुकाया/कमाया

### Takeaway
BTC/ETH पर basis/funding औसतन positive रहा है (BIS के अनुसार carry औसतन 10% प्रति वर्ष से अधिक)। यानी BTC/ETH के shorts औसतन funding कमाते हैं। Altcoins पर negative funding (shorts भुगतान करते हैं) अपेक्षाकृत सामान्य है, ख़ासकर भारी-short वाले coins में, और ऐसे दौर squeeze-जोखिम से जुड़े पाए गए हैं। Altcoin बनाम BTC के लिए सटीक ऐतिहासिक औसत किसी विश्वसनीय स्रोत से नहीं मिला।

### Cited Findings
- BIS Working Paper 1087, "Crypto carry" (Schmeling, Schrimpf, Todorov; अप्रैल 2023, संशोधित अक्टूबर 2025): crypto carry औसतन 10% प्रति वर्ष से अधिक है, जो equities, bonds, FX और commodities से कहीं अधिक है। ब्याज-दर अंतर इसे बहुत कम समझाते हैं। (perpetual-विशिष्ट औसत PDF में हैं, जो पढ़े नहीं गए।) — [BIS WP 1087](https://www.bis.org/publ/work1087.htm); [PDF](https://www.bis.org/publ/work1087.pdf)
- "Fundamentals of Perpetual Futures" (arXiv 2212.06888): funding आमतौर पर हर 8h; 2020–2022 के BTC perpetual funding के annualized 7-दिन औसत दिखाए गए हैं। — [arXiv](https://arxiv.org/pdf/2212.06888)
- Levolytics study: altcoins के लिए negative funding "अपेक्षाकृत सामान्य" है, और अकेले negative funding long करने का पर्याप्त कारण नहीं है। (Substack, peer-reviewed नहीं।) — [Levolytics](https://levolytics.substack.com/p/crypto-funding-rates-study)
- Santiment ने बड़े exchanges पर गहरे negative funding वाले altcoins को चिह्नित किया और liquidation-जनित pumps की बढ़ी संभावना बताई। — [Informer Post (Santiment)](https://theinformerpost.beehiiv.com/p/cardano-and-two-other-altcoins-enjoying-higher-chances-of-a-pump-according-to-analytics-firm-santime)
- K33 (Bloomberg के माध्यम से): 20 अगस्त 2024 को BTC का 7-दिन annualized funding मार्च 2023 के बाद सबसे कम था, जिसे short-squeeze जोखिम का संकेत माना गया। — [Bloomberg](https://www.bloomberg.com/news/articles/2024-08-21/crowded-bitcoin-btc-derivatives-bets-spur-warning-of-short-squeeze)
- LPT/BLZ squeeze (अगस्त 2023) में funding चरम स्तर पर था। — [FXStreet](https://www.fxstreet.com/cryptocurrencies/news/short-squeezes-for-lpt-blz-send-the-altcoins-almost-150-north-with-funding-rates-hitting-2000-202308142359)

### Inferences
- "Shorts ने net funding चुकाई" वाला हमारा परिणाम साहित्य से संगत है। bottom-ranked alts भीड़ वाले shorts हैं, उनकी funding negative रहती है, और यही भीड़ squeeze का ईंधन है। इसलिए गहरी negative funding को short entry का **filter/penalty** बनाना तर्कसंगत है (जैसे funding < −X% प्रति 8h पर entry नहीं)। X को pre-registered protocol में तय करें और shuffled control से जाँचें।
- Long-short book में hedge के रूप में BTC short रखने पर औसतन positive funding मिलती है (carry), जबकि alt short पर funding लागत लगती है। यह BTC-आधारित hedge के पक्ष में एक संरचनात्मक तर्क है।

### Gaps
- Binance alts बनाम BTC की वर्ष-वार औसत funding (shorts के नज़रिए से) का कोई सत्यापित प्रकाशित आँकड़ा नहीं मिला। Kaiko/Coinglass के पेज इस सत्र में नहीं मिले। सुझाव: `/fapi/v1/fundingRate` history से अपने universe पर गणना करें।

## 4. New listings: listing के बाद की कीमत (drift) और उन्हें short करने का जोखिम/लाभ

### Takeaway
अध्ययन लगातार बताते हैं कि listing-day पर तेज़ उछाल आता है, फिर हफ़्तों-महीनों में गिरावट (fade) होती है। यानी नई listings short करने का औसत edge वास्तविक लगता है। लेकिन शुरुआती दिनों का उछाल और ऊँची volatility short के लिए सबसे ख़तरनाक समय है। अधिकतर स्रोत उद्योग/मीडिया हैं, केवल एक peer-reviewed (AFT 2025) है। Perpetual listings पर विशिष्ट अध्ययन नहीं मिला।

### Cited Findings
- 22 exchanges का event study: listing-day पर औसत abnormal return 7.4%, Binance पर 14.7%। — [Blockchain Research Lab](https://www.blockchainresearchlab.org/?p=3721)
- Ren और Heinrich (26 Binance listings): day-1 पर औसत +41%, day-3 तक +24%। लगभग 2 सप्ताह में लगभग आधे tokens ने अपनी बढ़त गँवा दी। — [Informer Post](https://theinformerpost.beehiiv.com/p/binance-listings-cause-crypto-assets-to-spike-an-average-of-41-new-research); [Yahoo](https://malaysia.news.yahoo.com/binance-effect-means-41-price-173526978.html)
- 2024 के 31 Binance listings में से केवल 5 छह महीने बाद listing price से ऊपर थे। — [FXStreet](https://www.fxstreet.com/cryptocurrencies/news/binance-effect-fades-less-than-20-tokens-are-profitable-six-months-after-listing-202405201006)
- 389 tokens (6 exchanges) पर CryptoNinjas/Storible: Binance tokens listing पर औसत +87%, फिर listing price से औसतन −70%। (small-cap sample, फ़रवरी 2025 का एक ही data pull।) — [BitPinas](https://bitpinas.com/cryptocurrency/binance-token-listing-dump/)
- Animoca Research: CEX listing के बाद औसत −49%, venue के हिसाब से बड़ा अंतर। RockawayX के अपने regressions 30/60 दिन पर दिशा में bullish थे पर सांख्यिकीय रूप से महत्वपूर्ण नहीं। — [RockawayX](https://rockawayx.com/insights/bullish-or-bearish-what-really-happens-when-tokens-list-on-a-cex)
- AFT 2025 (peer-reviewed): Binance और Coinbase दोनों पर listing के बाद अल्पकालिक positive abnormal returns। Binance के venture arm के निवेश वाले tokens के fundamentals कमज़ोर पाए गए। — [Dagstuhl LIPIcs AFT 2025](https://drops.dagstuhl.de/storage/00lipics/lipics-vol354-aft2025/html/LIPIcs.AFT.2025.11/LIPIcs.AFT.2025.11.html)
- 2026 की listing प्रभावशीलता पर The Tie का विश्लेषण उपलब्ध है (पढ़ा नहीं गया)। — [The Tie](https://www.thetie.io/insights/what-does-an-exchange-listing-actually-deliver-in-2026)
- **Delistings:** Binance delisting घोषणा के बाद spot में दो-अंकीय गिरावट आम है। उदाहरण: अप्रैल 2026 में IDEX −33% (दैनिक), A2Z −16.19%, FORTH −16.34%; 2023 में WABI −53%; 2024 में XMR 3 घंटे में −15%। कुछ में लगभग कोई असर नहीं हुआ (ANT +0.2%)। delisting से पहले futures positions बंद की जाती हैं। — [Tangem](https://tangem.com/en/news/markets/18619-binance-delists-tokens-triggers-sharp-price-drops/); [Forklog XMR](https://forklog.com/en/monero-price-drops-15-following-binance-delisting-announcement/amp); [Forklog WABI](https://forklog.com/en/binance-announces-delisting-of-wabi-as-token-plunges-53/amp); [Cointelegraph](https://cointelegraph.com/news/binance-delist-five-tokens-triggers-price-crash)

### Inferences
- हमारा "short P&L कुछ 2025-26 new listings में केंद्रित" होना listing-fade साहित्य से मेल खाता है। लेकिन इसका मतलब है कि edge कुछ ही घटनाओं पर टिका है। इसे "AI skill" का दावा करने से पहले listing-age-matched shuffled control से अलग करना ज़रूरी है (क्या केवल "age < N दिन वाले को short करो" नियम वही लाभ देता है?)।
- जोखिम-संतुलित नियम का विचार (साहित्य से अनुमानित, परीक्षण आवश्यक): पहले कुछ दिन/सप्ताह (उछाल-चरण) short न करें, उसके बाद छोटे आकार और volatility-scaled आकार के साथ करें। fade 2 सप्ताह से 6 महीने में दिखा है।
- Delisting घोषणा short के पक्ष में घटना है, पर futures contract बंद होने/settlement का जोखिम है। position settlement की तारीख़ से पहले बंद होनी चाहिए।
- Survivorship: listing-fade अध्ययनों में बाद में delist हुए tokens शामिल हैं या नहीं, यह स्पष्ट नहीं है। हमारे backtest में delisted perpetuals शामिल होने चाहिए।

### Gaps
- Perpetual-futures listing (Binance USDT-M पर नया contract) के बाद के returns पर कोई peer-reviewed अध्ययन नहीं मिला।
- Listing-fade अध्ययनों के sample छोटे हैं और methods मिश्रित हैं।

## 5. Position-level controls: stop, caps, volatility scaling, liquidity, cooldown

### Takeaway
सबसे मज़बूत शैक्षणिक प्रमाण **volatility scaling** के पक्ष में है। क्रिप्टो momentum में अकेला coin पूरे portfolio को crash कर सकता है, और volatility-managed portfolios crash कम करते हैं। Stop-loss पर सिद्धांत कहता है कि random walk में stops हमेशा expected return घटाते हैं, और momentum/regime-switching वाले बाज़ार में मूल्य जोड़ सकते हैं। क्रिप्टो shorts पर fixed-% बनाम ATR stop की सीधी तुलना करने वाला कोई अध्ययन नहीं मिला।

### Cited Findings
- Grobys, Kolari, Sandretto, Shahzad, Äijö (2025), *Financial Markets and Portfolio Management*: large-cap crypto momentum गंभीर crashes के अधीन है, एक अकेला coin portfolio की significance मिटा सकता है, और volatility management crashes घटाता है। लेखकों ने volatility scaling की कमियों (जैसे look-ahead bias) का भी उल्लेख किया है। — [Springer](https://link.springer.com/article/10.1007/s11408-025-00474-9)
- Sandretto (2025, Turku dissertation): सादा momentum व्यक्तिगत coins के crashes के कारण significant returns नहीं देता, जबकि volatility scaling से पर्याप्त लाभ मिलता है (factor adjustment के साथ और बिना)। — [UniTo/IRIS record](https://iris.unito.it/handle/2318/2108656); [Osuva](https://osuva.uwasa.fi/handle/11111/18877)
- Zancu (student project, peer-reviewed नहीं): GARCH-आधारित volatility scaling cross-sectional momentum को बेहतर बनाता है। — [RCAP record](https://oasisbr.ibict.br/vufind/Record/RCAP_d7bb213a57fd75819661e51bbab30106)
- Kaminski और Lo, "When Do Stop-Loss Rules Stop Losses?", Journal of Financial Markets 18 (2014): random walk में 0/1 stop-loss हमेशा expected return घटाता है, जबकि momentum होने पर मूल्य जोड़ सकता है। 1950–2004 के डेटा में stop-out अवधियों के दौरान 50 से 100 bps प्रति माह जुड़े (US long bonds में शरण लेने पर)। — [MIT DSpace](https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee)
- Li-Shin-Wang: pump के दौरान liquidity घटती है (इसलिए stop का slippage बढ़ता है)। — [Cambridge/JFQA](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/cryptocurrency-pumpanddump-schemes/97149DCD519BAF838F269F98DC76D682)
- अक्टूबर 2025 crash में पतली altcoin liquidity प्रमुख amplifier थी (ATOM जैसे coins में लगभग शून्य के wicks)। — [FTI Consulting](https://fticonsulting.com/insights/articles/crypto-crash-october-2025-leverage-met-liquidity)

### Inferences
- Short के लिए return distribution दाईं ओर skewed (squeeze) है। इसलिए Kaminski-Lo तर्क के अनुसार, जब squeeze में momentum होता है (pump जारी रहता है), तब stop-loss short के लिए मूल्यवान है। हमारा x1.5 stop + cooldown इसका व्यावहारिक रूप है। Cooldown का औचित्य: P&D के बाद reversal आता है, पर उसी coin पर दोबारा squeeze का जोखिम ऊँचा रहता है। 30-दिन cooldown के इष्टतम होने का कोई प्रकाशित प्रमाण नहीं मिला, इसे sensitivity test (7/14/30/60 दिन) से जाँचें।
- Fixed-% stop (x1.5) सभी coins के लिए समान है। volatility-scaled stop (जैसे entry + k×ATR या k×σ) ऊँचे-vol नए coins पर चौड़ा और कम-vol coins पर तंग होगा। साहित्य volatility scaling को **position size** पर लागू करने का समर्थन करता है (stop पर नहीं)। सुझाव: पहले "10% बराबर" की जगह inverse-vol sizing (per-coin risk budget) आज़माएँ और उसे stop के साथ संयोजित करें।
- Concentration: "एक coin portfolio मिटा सकता है" वाला निष्कर्ष short book पर और भी लागू है, क्योंकि short का नुकसान असीमित है। प्रति-coin cap (जैसे gross का 5%) और per-coin vol-cap तर्कसंगत हैं।
- Liquidity filter: न्यूनतम 30-दिन औसत quote volume / OI, साथ ही listing-age filter। ये squeeze और slippage दोनों घटाते हैं (अनुमान, परीक्षण आवश्यक)।
- Funding filter (section 3) भी एक position-level control है।

### Gaps
- Crypto shorts पर fixed-% बनाम ATR stop, cooldown अवधि, या per-coin cap का tail-loss बनाम return trade-off मापने वाला कोई सत्यापित अध्ययन नहीं मिला। यह हमारे अपने pre-registered backtest से तय करना होगा।

## 6. Portfolio tail hedges: BTC/ETH puts, BTC perp hedge, ऊँची volatility में gross घटाना

### Takeaway
BTC puts (Deribit/IBIT) पर downside protection महँगी है: put skew ऊँचा है, और 2026 में लगभग आधे समय short-dated IV long-dated से अधिक रहा। Put की लागत का कोई पूरा, दिनांकित मॉडल किसी स्रोत में नहीं मिला, इसलिए लाइव DVOL/chain से गणना करनी होगी। Altcoin shorts के squeeze-जोखिम (idiosyncratic, ऊपर की ओर) के विरुद्ध BTC puts कोई hedge नहीं देते। BTC puts long book के systemic crash के लिए हैं। BTC perp hedge सस्ता है (औसतन positive funding कमाता है), पर ADL से टूट सकता है।

### Cited Findings
- Anchorage (Cointelegraph के माध्यम से): Deribit और IBIT दोनों पर put skew ऊँचा है, यानी traders downside protection के लिए premium दे रहे हैं। 2026 में BTC options ने लगभग आधे समय अगले सप्ताह के लिए अगले महीने से अधिक IV price किया (inverted term structure)। — [Cointelegraph](https://cointelegraph.com/news/bitcoin-options-traders-hedge-downside-as-uncertainty-lingers-anchorage-says)
- Deribit पर put OI spot के निकट strikes ($75k–$85k, एक expiry के लिए) पर केंद्रित है, यानी गहरी tail-protection के बजाय निकट-spot bands। — [CryptoSlate](https://cryptoslate.com/bitcoin-options-downside-insurance-75k-85k-june-2026/)
- Deribit के अनुसार institutions ने $60k या उससे नीचे के 6-महीने और 1-वर्ष के puts portfolio insurance के रूप में खरीदे (लेख की तारीख़ अस्पष्ट है)। — [Unlock BC](https://unlock-bc.com/en/bitcoin-etf-investors-hedge-against-potential-60k-crash)
- 30-दिन IV के आँकड़े स्रोतों में अलग हैं: एक स्रोत में Deribit DVOL लगभग 24% (दो साल का निचला स्तर), दूसरे में 45%। दोनों अलग समय के हैं और तारीख़ें अस्पष्ट हैं। — [Forklog](https://forklog.com/en/news/derivatives-traders-hedge-against-bitcoin-sliding-below-85000); [Boorghani/Deribit](https://rss.boorghani.com/?p=348914)
- BIS: BTC/ETH carry औसतन 10% प्रति वर्ष से अधिक है, इसलिए BTC perp short hedge औसतन funding कमाता है। — [BIS WP 1087](https://www.bis.org/publ/work1087.htm)
- Volatility-managed portfolios crypto crashes घटाते हैं (ऊँची vol में exposure कम करना)। — [Grobys et al. 2025](https://link.springer.com/article/10.1007/s11408-025-00474-9)
- अक्टूबर 2025: BTC लगभग −14%, SOL intraday 40% से अधिक नीचे, alts में लगभग शून्य के wicks। ADL से कई exchanges पर मुनाफ़े वाली (hedge) positions बंद हुईं। — [CoinGecko](https://www.coingecko.com/learn/october-10-crypto-crash-explained); [FTI](https://fticonsulting.com/insights/articles/crypto-crash-october-2025-leverage-met-liquidity)

### Inferences
- हमारे long-short book में दो अलग tail-जोखिम हैं: (a) systemic crash, जो long book को चोट देता है (shorts इसे आंशिक रूप से hedge करते हैं), और (b) idiosyncratic alt squeeze, जो short book को चोट देता है। BTC puts केवल (a) के लिए हैं। (b) का hedge stop, sizing और filters हैं, options नहीं (alt options लगभग मौजूद ही नहीं हैं)।
- 1x isolated पर एक short का अधिकतम नुकसान उसकी margin (10% NAV) तक सीमित है। यानी 1x isolated ख़ुद एक "built-in" tail-cap है। लेकिन पाँचों shorts के एक साथ squeeze होने (alt-season/short-squeeze rally) पर नुकसान 50% NAV तक जा सकता है। Gross cap, BTC-beta hedge, या regime-आधारित short exposure घटाना इस सहसंबद्ध squeeze के विरुद्ध हैं।
- BTC perp hedge (long book का beta-neutralization) options से सस्ता है (positive carry), पर (i) ADL से hedge बंद हो सकता है, (ii) अक्टूबर 2025 जैसी घटनाओं में alts BTC से कहीं अधिक गिरे (SOL −40% बनाम BTC −14%), इसलिए beta अस्थिर है।
- Inverted IV term structure (short-dated महँगे) के दौरान rolling short-dated puts महँगे हैं। puts केवल पोर्टफोलियो की सबसे बड़ी जोखिम-अवधि में ही रखना लागत-कुशल हो सकता है। यह अनुमान है, कोई सत्यापित backtest नहीं मिला।

### Gaps
- BTC put protection की वास्तविक लागत (जैसे 30-दिन 10% OTM put का premium, NAV का % प्रति वर्ष) का कोई दिनांकित, सत्यापित आँकड़ा नहीं मिला। Deribit Insights, Glassnode या Kaiko के मूल पेज इस सत्र में नहीं मिले। सुझाव: Deribit public API (DVOL और option chain) से गणना करें।
- Binance Options की तरलता/लागत पर कोई स्रोत नहीं मिला।
- क्रिप्टो long-short portfolio पर put-hedge बनाम BTC-perp hedge बनाम vol-targeting की तुलना करने वाला कोई अध्ययन नहीं मिला।
