# 1D Rebuild — Step 5 रिपोर्ट: Live / Testnet Engine

**तारीख:** 12 अक्टूबर 2026
**GitHub:** कुछ नहीं किया गया।
**Code:**

| फाइल | काम |
|---|---|
| `src/execution/live_1d_swing_engine.py` | नया live/testnet engine |
| `src/audits/audit_live_1d_replay.py` | replay audit |

**पुराना `paper_engine.py` नहीं छुआ गया।** पिछले audit में उसकी गंभीर कमियाँ मिली थीं, इसलिए उसे इस्तेमाल न करें।

---

## 1. Engine में क्या है

**System:** Step 4b का final system।
- Entry: ZigZag K=4 up-leg confirm हो, और BTC का K=3 leg ऊपर हो।
- Stop: 1.5 × ATR।
- Exit: coin का K=4 down-leg confirm होने पर।
- Risk: अधिकतम 8 positions, **20% USDT reserve**, slot = 80% equity ÷ 8, 2% risk cap, 15% drawdown पर 30 दिन तक नई entries बंद।

**Modes**

| Mode | क्या करता है |
|---|---|
| `dryrun` (default) | Binance का public live data, **कोई order नहीं**, simulated fills |
| `testnet` | Binance **SPOT TESTNET** पर असली orders, `.env` की testnet keys से |
| mainnet | **मौजूद ही नहीं।** Code में sandbox mode forced है, और testnet URL का assert है |

**पुराने `paper_engine.py` की कमियाँ और यहाँ उनका इलाज**

| पुरानी कमी (पिछले audit से) | नए engine में |
|---|---|
| Exit पर exchange को sell order नहीं जाता था | Exit पर stop-order cancel होकर **market sell** |
| Exchange पर stop-loss नहीं लगता था | हर buy के बाद **STOP_LOSS_LIMIT** sell order (limit, stop से 1% नीचे) |
| Gap में stop-limit न भरे तो position बिना सुरक्षा के रह जाती | Fallback: price ≤ stop और order खुला हो, तो **cancel करके market sell** |
| Lot-size या min-notional rounding नहीं थी | `amount_to_precision`, `price_to_precision`, exchange का min-cost check |
| Live features backtest से अलग थे (100 candles बनाम 200) | Live signals **उन्हीं backtest functions** से बनते हैं, और पूरा verified इतिहास + live बंद candles इस्तेमाल होती हैं |
| Equity में सिर्फ free USDT गिना जाता था | Equity = cash + holdings की value |
| अधूरी (बन रही) candle पर फैसला | आज की बन रही candle हटाई जाती है; फैसला सिर्फ बंद daily candle पर |
| एक ही दिन को दो बार process करना | State में `last_processed` रखा जाता है; दूसरी बार "already processed" |

---

## 2. Verification

| Test | नतीजा |
|---|---|
| **L1 replay** | Live engine का daily cycle इतिहास पर दिन-ब-दिन चलाया गया: 2021–22 में 729 cycles और 2023–26 में 1,368 cycles। सारे **32 + 124 trades** backtest engine से **हूबहू** मिले: signal/entry/exit dates, prices, units, exit reason, P&L |
| **Mutation test** | Test खुद असली है या नहीं, यह जाँचा। Live engine में जानबूझकर (a) reserve 10% और (b) stop 1.6 ATR डाला गया। दोनों बार audit ने फर्क **पकड़ा** (124 की जगह 116 और 121 trades) |
| **L2 safety** | सिर्फ `dryrun` और `testnet` modes मौजूद हैं; testnet client sandbox-forced और URL-asserted है |
| **Dryrun live run** | Binance public API से 2026-10-01 → 2026-10-11 की बंद candles fetch हुईं। Local इतिहास से जोड़ते समय continuity assert पास हुआ। 2026-10-11 की close पर कोई entry signal नहीं था, कोई order नहीं गया |
| **Idempotency** | दूसरी बार चलाने पर "already processed -- nothing to do" आया |

**आज कोई signal क्यों नहीं आया (data से)**
- BTC का K3 leg UP है। कई coins पहले से K4 up-leg में हैं, जैसे XRP (confirm 2026-09-22), ADA (09-23), DOT (09-26)।
- पर engine आज fresh शुरू हुआ है, और नियम सिर्फ **confirmation वाले दिन** entry लेता है।
- इसलिए नई entry अगले नए confirmation पर होगी। यह design के मुताबिक है, कोई bug नहीं।

---

## 3. ⚠️ जो अभी VERIFY नहीं हुआ (ईमानदारी से)

1. **Testnet पर असली order flow मैंने नहीं चलाया।** यह किसी exchange पर orders भेजना है, इसलिए यह आपको खुद चलाना है। ये चीज़ें पहली testnet run में ही पक्की होंगी:
   - market buy
   - STOP_LOSS_LIMIT order लगना
   - cancel
   - market sell
   - balance fetch
2. **Testnet की कीमतें और liquidity mainnet से अलग होती हैं।** Testnet fills से slippage का अनुमान भरोसेमंद नहीं है।
3. **Testnet पर engine का अंदरूनी cash, exchange के balance से अपने-आप reconcile नहीं होता** (शुरुआत में free USDT लिया जाता है)। हफ्ते में एक बार हाथ से मिलान करें।
4. **Stop-limit की सीमा:** बहुत बड़े gap (जैसे 2025-10-10 जैसा crash) में stop-limit नहीं भरेगा। तब fallback अगली run पर market sell करेगा। तब तक नुकसान stop से बड़ा हो सकता है।

---

## 4. चलाने का तरीका

```bash
python src/execution/live_1d_swing_engine.py --mode dryrun
```

```bash
python src/execution/live_1d_swing_engine.py --mode testnet
```

- **रोज़ एक बार चलाएँ:** daily candle 00:00 UTC (05:30 IST) पर बंद होती है, इसलिए लगभग **05:35 IST** पर (Windows Task Scheduler से)।
- State और logs `logs/live_1d/` में बनते हैं:
  - `state_<mode>.json`
  - `<mode>_decisions.csv`
- **Dryrun और testnet की state फाइलें अलग हैं।**

---

## 5. असली पैसे से पहले (सुझाव)

1. कम से कम **8–12 हफ्ते** testnet चलाएँ।
2. हर हफ्ते मिलान करें:
   - testnet पर हुए trades;
   - उसी अवधि का replay (`audit_live_1d_replay.py` वाले function से)।
   - दोनों के फैसले (entry/exit के दिन) एक जैसे होने चाहिए।
3. यह याद रखें: 1D system **कम trades** लेता है (2023–26 के बीच साल में ~35)। ज़्यादातर समय capital USDT में रहता है (OOS में median invested सिर्फ 12%)। कुछ हफ्तों में एक भी trade न होना सामान्य है।
4. Backtest का सच: OOS 2021–26 में CAGR 26.6%, **Max DD 30.7%**, और 2026-09-30 पर equity peak से 22.5% नीचे थी। असली पैसा लगाने का फैसला इसी जोखिम को समझकर करें।
