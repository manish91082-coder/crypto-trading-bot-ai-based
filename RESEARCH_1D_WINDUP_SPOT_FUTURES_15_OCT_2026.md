# 1D (spot + futures): पूरा करने के लिए क्या बचा है (deep research, 15 अक्टूबर 2026)

हर दावे के साथ उसका सबूत लिखा है। जो पक्का नहीं है, उसे "पक्का नहीं" लिखा है। मैं लाइसेंसशुदा वित्तीय या tax सलाहकार नहीं हूँ।

---

## 1. सवाल: "2017 से futures का data भी तो होगा?" जवाब: नहीं, futures 2019 के आखिर में शुरू हुए

**सबूत: Binance का अपना API (`fapi.binance.com/fapi/v1/klines`), आज जाँचा।**

| Perpetual | पहला दिन (Binance API) |
|---|---|
| BTCUSDT | 8 सितंबर 2019 (पहली funding 10 सितंबर 2019) |
| ETHUSDT | 27 नवंबर 2019 |
| BCHUSDT | 19 दिसंबर 2019 |
| XRPUSDT | 6 जनवरी 2020 |
| LINKUSDT | 17 जनवरी 2020 |

- Binance की monthly archive (`data.binance.vision`) में 2019 की files हैं ही नहीं (2019-08 से 2019-12 तक सब 404)। इसीलिए हमारा F1 data जनवरी 2020 से है।
- **हमारे पास (`data/futures_um`):** 135 coins के perpetual हैं। कितने coins का perpetual किस साल शुरू हुआ:

  | साल | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
  |---|---|---|---|---|---|---|
  | Coins | 41 | 23 | 9 | 28 | 12 | 22 |

  Data 30 सितंबर 2026 तक का है।
- **मतलब:**
  - 2017–19 का असली futures data दुनिया में है ही नहीं। उस दौर के लिए सिर्फ "spot कीमत पर नकली short" बन सकता है, जो F2 के PRE test में पहले ही किया जा चुका है ($11,438, सबसे बड़ी गिरावट 18.8%)।
  - Sept–Dec 2019 का data API से मिल सकता है, पर सिर्फ BTC और ETH का। Long-short के लिए 5 coins short चाहिए, इसलिए **यह किसी काम का नहीं। नहीं करेंगे।**

---

## 2. India का crypto tax ⚠️ (आपके निर्देश, 15 अक्टूबर: **अभी लागू नहीं, रोका गया।** T1/T2 फिलहाल प्राथमिकता में नहीं हैं। हिसाब सिर्फ रिकॉर्ड के लिए रखा है।)

(मान रहा हूँ कि आप India के tax resident हैं। अगर नहीं, तो यह हिस्सा बदल जाएगा।)

### कानून: मूल पाठ, सरकारी साइट से
Income Tax Department की साइट (incometaxindia.gov.in/w/section-115bbh) पर Section 115BBH:
- VDA (crypto) के transfer की कमाई पर **30% tax**।
- खरीद की कीमत के सिवा **कोई खर्च घटा नहीं सकते, कोई नुकसान set-off नहीं।**
- VDA का नुकसान किसी और आय से set-off **नहीं**, और **आगे carry-forward भी नहीं।**
- Finance Act 2022 में clause (b) से "other" शब्द हटाया गया। इसका मतलब: **एक coin का नुकसान दूसरे coin की कमाई से भी नहीं कटता।** (Taxmann और ICAI-WIRC की टिप्पणियाँ; Gazette का पाठ मैंने खुद नहीं देखा।)

### इसका हमारे system पर असर: हमारे अपने F2 trades से हिसाब
- **तरीका:** हर साल (अप्रैल–मार्च) के जीतने वाले trades की कमाई पर 30% tax, और हारने वाले trades का नुकसान नहीं घटाया।
- **सीमा:** यह सिर्फ report के लिए मोटा अनुमान है। Tax चुकाने से compounding और घटती, वह इसमें नहीं गिना। यानी असली हाल इससे भी बुरा होगा।

| 2021–26 (तीनों sleeves का औसत, $10k से) | कुल शुद्ध कमाई (tax से पहले) | जीते trades की कमाई | 30% tax (नुकसान घटाए बिना) |
|---|---|---|---|
| Long हिस्सा | $57,157 | $326,072 | **$97,822** |
| Short हिस्सा | $43,322 | $475,450 | **$142,635** |
| कुल long-short | ~$100,479 | ~$801,522 | **~$240,457** |

- **कारण:** हमारे system में ~9,000 trades हैं और सिर्फ 52–54% जीतते हैं। हर जीत पर tax लगता है, पर हर हार का नुकसान पूरा हमारा।
- **नतीजा:** इस कानून के सीधे पाठ के हिसाब से **tax, कुल कमाई से ज़्यादा बनता है**। यह spot (long-only) और long-short दोनों पर लागू है।
  - **हर साल अलग-अलग:** D1 sleeve में सिर्फ पहले साल (FY2021) tax के बाद थोड़ा फायदा बचता है। बाकी हर साल tax के बाद घाटा है।
  - **H4 और H1 sleeves:** H4 के हर साल tax के बाद घाटा है। H1 का FY2021 लगभग बराबर रहा (+$47), बाकी सब साल घाटे में।
- **तुलना:** BTC खरीद कर रख लेते (2021-01-01 → 2026-09-30) तो $10k → $28,510 होता। एक बार 30% tax के बाद ≈ **$22,957** बचता।
- **ईमानदार बात:** इन backtests को आज तक **tax के बाद के हिसाब से किसी ने नहीं जाँचा।** यह हमारी सबसे बड़ी कमी थी।

### जो पक्का नहीं है
**Futures (USDT perpetual) पर tax:** स्रोतों में मतभेद है।
- कुछ इसे business income मानते हैं (slab rate, नुकसान set-off हो सकता है)।
- कई इसे VDA मानते हैं (30%, कोई set-off नहीं)।
- अगस्त 2026 की एक CA forum राय भी 30% वाली है।
- **CBDT का कोई circular या अदालती फैसला नहीं है।**

**1% TDS (194S):** हर बिक्री पर लग सकता है। हमारे जैसे ज़्यादा trades वाले system में यह पूँजी को बहुत रोकेगा (बाद में credit मिलता है)। Foreign exchange पर इसकी ज़िम्मेदारी किसकी है, यह भी साफ नहीं है।

**Binance India:** Binance FIU-IND में registered है। यह Binance की legal page और BusinessToday (अगस्त 2024) से पक्का है। लेकिन Indian account में futures खुलेंगे या नहीं, यह किसी आधिकारिक स्रोत से पक्का **नहीं** हुआ। Indian users के लिए INR जमा करने का रास्ता ज़्यादातर P2P बताया जाता है, जो पक्का नहीं है और उसमें खाता freeze होने जैसे खतरे हैं।

➡️ **असली पैसे से पहले यह आपका काम है:** किसी Chartered Accountant से लिखित राय लें। Binance support से पूछें कि आपके account में कौन से futures मिलेंगे।

---

## 3. "2–3 दिन सीधे live market पर चलाएँ": इससे क्या पता चलेगा, क्या नहीं

| 2–3 दिन में पता चलेगा ✅ | 2–3 दिन में पता नहीं चलेगा ❌ |
|---|---|
| Orders सही भरते हैं या नहीं, API और scheduler ठीक है या नहीं | Strategy कमाती है या नहीं |
| असली slippage और fees बनाम मान्यता | 2022 जैसी मंदी में क्या होगा |
| Kill switch और stop काम करते हैं या नहीं | Liquidation का असली खतरा |

- **कारण:** D1 हर 5 दिन में एक फैसला लेता है। 2–3 दिन में 0 या 1 फैसला होगा, जो सिक्का उछालने जितना है।
- **मेरी सलाह:** 2–3 दिन का "operations test" बिल्कुल करें, पर
  - spot का **testnet** पर (पहले से चल रहा है; ETH वाली position नहीं छूनी);
  - futures का **futures testnet** पर (F6 code बनने के बाद)।
- **असली पैसा:** सिर्फ बहुत छोटी रकम से, सिर्फ execution जाँचने के लिए, और वह भी आपके फैसले, आपकी keys और आपकी CA राय के बाद। मैं असली पैसे का कोई order नहीं डालूँगा, keys नहीं डालूँगा।

---

## 4. 1D को पूरा (wind-up) करने के लिए बचे काम: प्राथमिकता के साथ

### A. Research (सब पहले से lock किए protocol, अलग verifier और पैसे वाली शर्त के साथ)

| # | काम | क्यों | फायदा | प्राथमिकता |
|---|---|---|---|---|
| T1 | **Tax के बाद का simulator** (India 115BBH: हर जीत पर 30%, हार पर कुछ नहीं, tax हर साल equity से कटे; 1% TDS से पूँजी रुके) | ऊपर का अनुमान बताता है कि tax के बाद strategy घाटे में हो सकती है | सच्चा जवाब कि यह system tax के बाद BTC रखने से बेहतर है या नहीं | **सबसे ऊपर** |
| T2 | **कम trades वाला रूप** (हफ्ते या महीने में फैसला, ज़्यादा देर रखना, "बड़ा winner" वाला label यहीं जुड़ता है = S4) | 115BBH में हर trade पर tax का नुकसान होता है | Tax का बोझ बहुत घट सकता है | T1 के बाद |
| S7 | असली खर्च पर दोबारा गिनना | 30 rounds ~31 अक्टूबर तक | सही उम्मीद | ज़रूरी, सस्ता |
| F7 | Short के risk नियम (हर short की सीमा, नए listed coins पर नियम, भागते coin से निकलना) | Short की कमाई नए coins पर टिकी है, 69 liquidations | सबसे बड़ा खतरा कम | ज़रूरी |
| S5 | तीनों दिमागों के scores जोड़ना | छोटा फायदा | — | वैकल्पिक |
| ✗ | 2017–19 futures data | मौजूद नहीं है | — | **नहीं करेंगे** |
| ✗ | और नए features | S2 और S3 FAIL, AUC ~0.56 पर अटका है | — | **नहीं करेंगे** (हर नया test DSR और गिराता है) |

### B. Engineering (code)

| # | काम | स्थिति |
|---|---|---|
| E1 | Spot forward paper log (16B) | ✅ रोज़ चल रहा है |
| E2 | Cost study | ✅ चल रहा है |
| F4 | Long-short paper log (बिना order) | बनाना है |
| F6 | Futures testnet code (1x, isolated, reduce-only, kill switch) | बनाना है। Testnet keys आप env में डालेंगे |
| E3 | Alert (रोज़ का सार), reconciliation (हिसाब बनाम exchange), log backup | बनाना है |
| E4 | Tax ledger: हर trade की खरीद-बिक्री, INR value और TDS का हिसाब, CA के लिए | T1 के साथ बनाना है |

### C. आपके काम

| # | काम |
|---|---|
| U1 | **CA से लिखित tax राय:** spot VDA और USDT perpetual दोनों पर, 1% TDS समेत |
| U2 | Binance account, KYC, futures की उपलब्धता और INR जमा का सुरक्षित रास्ता |
| U3 | Wake timers चालू करें; scheduled समय पर PC बंद न करें |
| U4 | असली पैसे का अंतिम फैसला |

---

## 5. सुझाया गया क्रम
1. **T1:** tax के बाद का सच। यह न हुआ तो बाकी सब बेमानी है।
2. **T2 / S4:** कम trades वाला रूप। सिर्फ T1 का नतीजा देखकर, नया protocol lock करके।
3. **S7:** ~31 अक्टूबर।
4. **F4 paper log + F7 risk नियम + F6 testnet code।** सिर्फ तब, जब T1/T2 में long-short tax के बाद भी जिंदा रहे।
5. 2–3 दिन का operations test, testnet पर।
6. **फैसला:**
   - spot: forward log के ~90 दिन बाद (~14 जनवरी 2027);
   - long-short: उसके paper log के 90 दिन बाद।
   - दोनों सिर्फ **tax के बाद** के forward सबूत पर।

---

## स्रोत
- Binance Futures API (सीधा data): `fapi.binance.com/fapi/v1/klines`, `/fapi/v1/fundingRate` (15 अक्टूबर 2026 को जाँचा)
- Binance data archive: `data.binance.vision/data/futures/um/monthly/klines/...` (2019 files 404)
- [Income Tax Department: Section 115BBH (मूल पाठ)](https://www.incometaxindia.gov.in/w/section-115bbh)
- [Taxmann: Finance Act 2022 के बदलाव](https://www.taxmann.com/post/blog/changes-made-in-finance-act-2022-as-passed-by-the-lok-sabha/)
- [ICAI-WIRC: Finance Act 2022 provisions (PDF)](https://old.wirc-icai.org/images/material/DT-PROVISIONS-ENACTED-FINANCE-ACT-2022-Pankaj.pdf)
- [Binance: Licenses and registrations](https://www.binance.com/en/legal/licenses)
- [Binance blog: India में registration](https://www.binance.com/en/blog/regulation/binance-achieves-its-19th-global-regulatory-milestone-with-registration-in-india-3022489348045738409)
- [BusinessToday: Binance FIU registration (2024)](https://www.businesstoday.in/technology/news/story/crypto-exchange-binance-achieves-legal-status-in-india-registers-with-financial-intelligence-unit-441692-2024-08-16)
- Futures tax पर मतभेद:
  - [Mudrex](https://mudrex.com/learn/crypto-tax-on-futures-trading-india/)
  - [CoinSwitch](https://coinswitch.co/switch/crypto-futures-derivatives/crypto-futures-options-tax/)
  - [Giottus](https://www.giottus.com/blog/crypto-futures-tax-in-india-complete-guide-for-traders)
  - [OpenAlgo](https://openalgo.in/taxation/crypto-fno-tax)
  - [CAclubindia](https://www.caclubindia.com/experts/-taxability-and-tds-treatment-on-crypto-futures-2962319.asp)
  - (ये सब exchanges या blogs हैं, आधिकारिक नहीं)
- Futures launch का संदर्भ: [Finance Magnates](https://www.financemagnates.com/cryptocurrency/news/binance-futures-launches-btc-margined-perpetual-futures-contracts/)

---

## 6. अंतिम integration (आपके निर्देश के बाद: tax अभी लागू नहीं)
**ढाँचा:** एक रोज़ का pipeline।
1. Data update
2. तीनों दिमागों के scores (D1, R6, R24)
3. Spot: top-5 long। Futures: bottom-5 short (1x isolated)।
4. Paper log या testnet order
5. Exchange से हिसाब का मिलान
6. Dashboard और alert
- हर कदम पर kill switch।

| क्रम | काम | कौन | कब (अनुमान) |
|---|---|---|---|
| 1 | F7: short के risk नियम, पहले lock, फिर backtest जाँच | मैं | अभी |
| 2 | F4: long-short paper forward log (बिना order, public data से) | मैं | F7 के बाद |
| 3 | F6: futures testnet code (1x, isolated, reduce-only, kill switch) | मैं (testnet keys आप env में) | F4 के बाद |
| 4 | 2–3 दिन का operations test, testnet पर (spot + futures) | मैं चलाऊँ, आप देखें | F6 के बाद |
| 5 | S7: असली खर्च पर दोबारा गिनना | मैं | ~31 अक्टूबर |
| 6 | Futures account और KYC (F5) | आप | कभी भी |
| 7 | S4/S5 | रोका गया (छोटा फायदा, DSR गिरता है) | — |
| 8 | फैसला: spot ~14 जनवरी 2027; long-short F4 के 90 दिन बाद | आप | forward सबूत पर |
