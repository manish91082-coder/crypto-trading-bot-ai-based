# User के फ़ैसले (16 अक्टूबर 2026, शाम)

| # | फ़ैसला | लागू कैसे होगा | स्थिति |
|---|---|---|---|
| D1 | **E11 shadow line: हाँ** | F4 के बाद रोज़ एक अलग shadow ledger लिखा जाएगा (`logs/forward_ls_f4/shadow_e11/`), जिसका अपना protocol lock (90deba31…) है और 90 दिन बाद पहले से तय नियमों पर परखा जाएगा | ✅ बन गया, कल से रोज़ चलेगा |
| D2 | **Tax और बाकी कानूनी बातें: बाद में** (पहले system सफल हो) | इन पर अभी कोई काम नहीं | Parked |
| D3 | **पुराना spot testnet system: ज़रूरत नहीं** | जाँच से पक्का हुआ कि आज का कोई active code `live_1d_ai_engine` / `live_1d_swing_engine` / `health_check_1d` को इस्तेमाल नहीं करता। उसके tasks बंद रहेंगे, वह cloud पर नहीं जाएगा, files नहीं मिटेंगी, और testnet ETH position को नहीं छुआ जाएगा | ✅ |
| D4 | **Capital: 80% trading में, 20% risk reserve** | Live execution में trading capital = account equity का 80%। दोनों legs (50% long + 50% short) इसी 80% पर लगेंगे। Backtest के $ आँकड़े इसी हिसाब से लगभग 0.8 गुना हो जाएँगे, जबकि % returns और DD का अनुपात वही रहेगा | असली पैसे वाला executor बनते समय लागू होगा (अभी F6 demo सिर्फ़ shorts का ops test है) |
| D5 | **BNB से fee discount: हाँ** | Fee discount की असली दरें (spot और futures) Binance के official pages से पहले verify करनी हैं। फिर S7 के cost हिसाब (≥ 30 cost rounds, लगभग 31 अक्टूबर) में शामिल होंगी, और account में BNB balance रखना होगा | Verify होना बाकी |
| D6 | **Google Cloud पर ले जाना: हाँ** (वही account जिससे पहले VM बना था) | मैं deployment bundle, setup script और cron तैयार करूँगा। आप Chrome में login करेंगे, फिर VM बनेगा, upload होगा, SHA से मिलान होगा, वहाँ E2E test चलेगा, और एक दिन की सीमा पर PC के tasks बंद करके cloud के tasks चालू होंगे | तैयारी चल रही है |

## एक बात अभी साफ़ नहीं है
- "मिस हुए ना सत्ताईस से चेक कर लो": "सत्ताईस" का मतलब पूछा गया है।
