# T2-CARRY: cash-and-carry का forward paper test, 2 नवंबर 2026

**यह क्या है:** spot long + perp short की paper position। इसमें कीमत की दिशा से फ़र्क नहीं पड़ना चाहिए; कमाई सिर्फ़ funding से आती है। कोई असली order नहीं जाता।

**सबसे ज़रूरी बात:** 2026 में carry लागत के बाद लगभग शून्य है। इसलिए FAIL या शून्य के पास का नतीजा काफ़ी संभव है, और यह बात forward data आने से पहले लिखी गई है।

## क्या लॉक हुआ

| चीज़ | मान |
|---|---|
| Protocol | `logs/carry_t2_2026_11_02/T2_PROTOCOL_PREREGISTERED.md` |
| SHA | 89fe2f46…, लॉक 2026-11-02 05:57:43Z |
| Position | 10,000 पूँजी: 2,500 BTC + 2,500 ETH notional, 5,000 margin |
| शुरुआत | 2 नवंबर 08:00Z; पहला गिना जाने वाला funding 16:00Z |
| फ़ैसला | **31 जनवरी 2027, 08:00Z**, उससे पहले कोई फ़ैसला नहीं |
| Fees | `deploy/fees.json` से, round trip 0.262% notional पर |

## PASS की शर्तें (सब ज़रूरी)

1. दोनों coins पर 270 funding events, बिना गैप। वरना INCONCLUSIVE।
2. कुल कमाई > 0।
3. 90 दिन में पूँजी पर कम से कम +0.188%।
4. Max drawdown 2.0% से कम।
5. Margin ratio कभी 0.25 से नीचे नहीं। नीचे गया तो test वहीं FAIL होकर ख़त्म।

+0.188% की हद जानबूझकर कम है: यह साल में लगभग 0.76% ही है। PASS का मतलब सिर्फ़ अगला pre-registered कदम है (ECO + carry mix या demo), कमाई का दावा या real money की अनुमति नहीं।

## पुराना इतिहास: 90 दिन की शुद्ध कमाई, पूँजी पर

| दौर | Median | ≤ 0 का हिस्सा |
|---|---|---|
| 2023 से | +0.586% | 7.6% |
| 2025 से | +0.376% | 17.7% |
| सिर्फ़ 2026 | **−0.010%** | **50.5%** |

हद पार होने की पुरानी दर: 2025 से 74%, और 2026 में सिर्फ़ 40%। ये windows एक-दूसरे पर चढ़ी हुई हैं, इसलिए ये नंबर सिर्फ़ तस्वीर दिखाते हैं।

## जाँच

- **Research से मिलान:** funding के साल-दर-साल नंबर Spot-DCA study से हूबहू मिले।
- **Hand tests:** 28/28 PASS।
- **Verifier:** forward से पहले वाली 4/4 जाँच PASS।
- **Dry-run, 1 अक्टूबर से 2 नवंबर (पुराना data, forward नहीं):** दोनों स्वतंत्र code paths में 760 घंटों पर फ़र्क 0.0। इस दौर में शुद्ध नतीजा +0.03% रहा: funding 15.84 USDT, लागत 12.41 USDT, basis −0.49 USDT।
- **लॉक के बाद:** code लॉक के बाद लिखा गया, और एक bug पहली run से पहले पकड़ा गया। दोनों `T2_CODE_CHANGES_AFTER_LOCK.md` में दर्ज हैं। Accounting का नियम नहीं बदला।

## सीमाएँ

- **Funding Bybit का है, Binance का नहीं,** क्योंकि laptop से Binance futures नहीं खुलता। 2026 में कुल funding: BTC 2.20% बनाम 1.82%, ETH 1.45% बनाम 1.80%। कुल जोड़ के लिए यह ठीक है, एक-एक event के लिए नहीं (correlation 0.58 और 0.68)।
- **दोनों legs अलग exchange पर हैं:** spot Binance का, perp Bybit का। असली carry में margin और transfer की दिक्कत आएगी, जो यहाँ नहीं गिनी गई।
- **Exchange का खतरा नहीं गिना गया।** Binance hack जैसी घटना carry का सबसे बड़ा जोखिम है।
- **यह laptop पर चलता है,** पर laptop बंद रहने से data नहीं खोता, क्योंकि हर run सब कुछ public history से दोबारा निकालता है।
- **Live verifier अभी बाकी है:** पहला forward record 09:05Z पर आएगा।
