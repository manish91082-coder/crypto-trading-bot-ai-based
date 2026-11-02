# एक single ecosystem: VM पर चारों हिस्सों को जोड़ने की योजना (21 अक्टूबर 2026)

**स्थिति:**
- यह सिर्फ़ योजना है। अभी कोई code नहीं लिखा गया और VM पर कुछ नहीं बदला।
- नीचे की हर "ज़मीनी जाँच" आज VM और laptop पर read-only चलाकर देखी गई है। Probe script: scratchpad का `vm_probe.py`, जो VM के `/tmp` में चलाकर हटा दिया गया।
- नियम वही रहेंगे: pre-registered protocol + SHA lock, independent verifier, CODE_CHANGES, Hindi report, और 1D system के चल रहे code में कोई बदलाव नहीं।

**User का फ़ैसला (21-10-2026):** 90 दिन का इंतज़ार नहीं करना है, अभी single ecosystem बनाना है।

**इसका ईमानदार असर:**
- Demo या paper पर जोड़ना ठीक है।
- पर दोनों systems का अलग-अलग forward सबूत अभी नहीं है (N1 के अभी सिर्फ़ 3 cycles हुए हैं)। इसलिए combined system के weights सिर्फ़ backtest से तय होंगे।
- इसकी भरपाई के लिए पुराने streams **shadow** में चलते रहेंगे (नीचे चरण E7)।
- Real money का फ़ैसला बाद में अलग से होगा।

---

## 1. ज़मीनी जाँच: अभी क्या है और जोड़ने में असल रुकावटें क्या हैं

| # | जाँच (आज) | नतीजा | मतलब |
|---|---|---|---|
| G1 | VM संसाधन | 2 vCPU, 3.9 GB RAM (3.3 GB खाली), disk 35 GB खाली, load 0.00 | एक orchestrator के लिए काफ़ी है; नई मशीन नहीं चाहिए |
| G2 | VM crontab | 19 jobs, चार अलग परतें, हर job अपना data ख़ुद download करता है | एक साझा data परत और एक scheduler चाहिए |
| G3 | F6 का code (`futures_testnet_f6.py`) | One-way mode की शर्त (`dualSidePosition False`), ISOLATED, 1× leverage। हर short अपनी sleeve के नाम पर रखा जाता है। Cover `reduceOnly` से होता है। Reconcile में "बाहर की positions" को अलग गिना जाता है | **उसी demo account पर दूसरा executor चलाना ग़लत होगा।** One-way mode में एक symbol की एक ही net position होती है, इसलिए F6 का cover N1 का हिस्सा भी बंद कर देगा |
| G4 | F6 की खुली positions (`state_demo.json`) | 7 symbols: FET, ONDO, SUI, UNI, WLD, NEAR, QNT | इनमें से 6 (FET, ONDO, SUI, UNI, NEAR, QNT) पर N1 की sleeve C भी अभी short है। **टकराव असली है, सैद्धांतिक नहीं** |
| G5 | N1 paper state (3 cycles) | 174 positions; perp gross 4,314 USDT, spot 423 USDT; equity 10,032.68 | ~91% exposure perp पर है |
| G6 | N1 legs बनाम Binance का min notional (असली exchangeInfo) | 169 perp legs में से **19 अकेले-अकेले minimum से छोटे** हैं। हर coin पर net करने के बाद 23 में से **0** छोटे | **Netting executor ज़रूरी है।** Leg-दर-leg orders संभव नहीं; coin-स्तर पर net करने से सब संभव |
| G7 | Combine backtest का data | 1D system: `logs/strategy_f7_risk/equity_MAIN_AI_RS.csv` (2021-01-01 … 2026-09-30, 2,099 दिन)। N1: `data/derived/n1/equity_K1.parquet` (hourly) | Data मौजूद है। **पर N1 FINAL (K1 + X2 + cap) की equity file नहीं है।** उसे locked code से दोबारा बनाना होगा और claims (dev Calmar 4.16) से मिलाना होगा |
| G8 | Combined performance | **जानबूझकर नहीं नापा** | Lock से पहले देखने पर weights चुनने में पक्षपात (bias) आ जाएगा। इसलिए पहले protocol lock होगा |

---

## 2. Single ecosystem का ढाँचा (6 परतें, एक clock)

```
            ┌──────────────── E0 Scheduler / Orchestrator (एक cron entry, flock, निर्भरता का क्रम) ────────────────┐
            │                                                                                                    │
  E1 Data hub ──► E2 Signal producers (brains/नियम, code वही) ──► E3 Target files (एक साझा schema) ──► E4 Allocator + Risk
  (एक बार download,     • 1D: Step16 → 16B → F4 (D1/H4/H1 AI)         {strategy, sleeve, coin, side,          (strategy-weights, कुल gross,
   SHA manifest)         • N1: A/B/C/D नियम (4h…1D)                    target_frac, venue, asof, sha}            per-coin cap 20% सब मिलाकर,
                         • FR2 recorder (सिर्फ़ data)                                                            DD kill-switch)
                                                                                                                    │
                                                    E6 Monitor + एक daily verifier ◄── E5 Netting executor (एक account, coin-स्तर net,
                                                    (M10 की जगह एक dashboard)             sleeve-attribution ledger, stops)
```

- **E0 Scheduler.**
  - 19 अलग-अलग समय वाले jobs की जगह एक orchestrator होगा, जिसे cron हर 4 घंटे जगाएगा (UTC 4h close के 11 मिनट बाद)।
  - वह निर्भरता के क्रम में steps चलाएगा: data → producers → allocator → executor → verifier।
  - `flock` से दो runs एक साथ नहीं चल पाएँगे।
  - कोई step fail हो तो आगे के steps पिछली मान्य targets पर टिके रहेंगे (कोई नया order नहीं), और alert जाएगा।
- **E1 Data hub.**
  - Klines, funding और exchangeInfo एक ही जगह, एक बार download होंगे, और हर cycle का SHA manifest बनेगा।
  - Producers इसी को पढ़ेंगे।
  - शुरुआत में पुराने 1D jobs अपना data ख़ुद लेते रहेंगे, ताकि उनका code न बदले। Hub उनके साथ मिलान (cross-check) करेगा।
- **E2 Producers.**
  - 1D brains और N1 नियम **बिना बदले**।
  - हर producer के लिए एक छोटा adapter बनेगा, जो उसके मौजूदा output को (F4 `orders_<asof>.json`, N1 state/ledger) साझा schema में बदलेगा।
  - Adapter सिर्फ़ पढ़ता है। Verifier जाँचेगा कि adapter का output = source (hash/मान)।
- **E3 Target schema.**
  - हर strategy यह बताएगी कि "मैं इस coin पर equity का इतना हिस्सा, इस side, इस venue पर चाहती हूँ"।
  - Orders की भाषा नहीं, targets की भाषा। इसी से timeframes का sync होता है: 4h वाले हर 4 घंटे target बदलते हैं, 1D वाले दिन में एक बार, और executor हर cycle में सबका जोड़ लेता है।
- **E4 Allocator + Risk.**
  - Strategy weights (1D system बनाम N1) **combine protocol से तय होंगे**, अंदाज़े से नहीं।
  - सब strategies मिलाकर per-coin cap, कुल gross cap और DD kill-switch लगेंगे।
  - `risk_rules_l4.py` यहीं आएगा, पर 1× के हिसाब से ठीक किए गए नियम के साथ: 0.4× liquidation वाला नियम सिर्फ़ leverage > 1 पर।
- **E5 Netting executor.** यह एक account चलाएगा और F6 की जगह लेगा (F6 का protocol और code इतिहास के लिए रहेंगे):
  - हर coin के लिए target net − exchange पर मौजूदा net = order। Min notional से छोटा फ़र्क हो तो अगले cycle तक रुका रहेगा, और वह फ़र्क ledger में दर्ज होगा।
  - **Attribution ledger:** हर fill किस sleeve का है। P&L sleeve-वार बँटेगा, ताकि हर brain का अपना हिसाब बना रहे।
  - **Stops:** one-way mode में exchange stop पूरी net position पर लगता है, इसलिए दो परतें होंगी:
    - (a) हर net position पर एक catastrophe stop, exchange पर;
    - (b) sleeve-स्तर के stops (जैसे 1D shorts का ×1.5) virtual, जिन्हें executor हर घंटे जाँचेगा।

    यह बदलाव F6 के मौजूदा "exchange stop per short" से अलग है, इसलिए replay में इसका असर नापा जाएगा (E3 का gate)।
  - **पहले से खुली positions:** F6 के 7 shorts executor अपना लेगा (adopt), नए सिरे से नहीं खोलेगा।
- **E6 Monitor.** एक daily verifier होगा: हर परत की hash chain, target = executed (min notional की छूट के साथ), attribution का जोड़ = account P&L, और data errors। M10 की जगह एक status page।

---

## 3. चरण (हर चरण का gate पास हुए बिना अगला नहीं)

| चरण | काम | Gate (PASS की शर्त) | कहाँ |
|---|---|---|---|
| **E-0** | Protocol `ECO_PROTOCOL_PREREGISTERED.md` + SHA lock; नया trial budget (प्रस्ताव: 6 trials, registry में ECO-1…6) | User की हाँ | laptop |
| **E-1** | N1 FINAL equity दोबारा बनाना (locked code से) | dev Calmar = 4.16 (claims से 1e-9 तक); verify_n6 5/5 | laptop |
| **E-2** | **Combine backtest** (trial): 1D RS + N1 FINAL, weights के 3 पहले से तय विकल्प (50/50 equity, inverse-vol, risk-parity), साझा per-coin cap के साथ | Combined Calmar > दोनों अकेले, P1 और P2 दोनों में; DSR ≥ 0.95; PBO < 0.30; P3 सिर्फ़ report। Fail हो तो सबसे अच्छा अकेला system चलेगा, combine नहीं | laptop |
| **E-3** | Adapters + allocator + netting executor, **plan mode** (कोई order नहीं), 7 महीने का replay (2025-03…10) | Netted P&L = sleeve-वार P&L का जोड़ (1e-9); min notional की वजह से छूटा हिस्सा < 1% gross; virtual-stop वाले 1D shorts का replay F7 नतीजे से ≤ तय सहनशीलता | laptop |
| **E-4** | Chaos tests: बीच cycle में crash, एक साथ दो runs, API 400 (जैसे SXP), पुराना data, exchange position ≠ state | सब पहले से लिखे expected व्यवहार पर; कोई दोहरा order नहीं | laptop |
| **E-5** | VM पर deploy, **plan mode** में 3 दिन (orders नहीं, सिर्फ़ "क्या भेजता") | Plan बनाम F6 असली actions का मिलान; daily verifier PASS | VM |
| **E-6** | Demo पर cut-over: F6 cron बंद, unified executor चालू (F6 के 7 shorts adopt) | पहला cycle: reconcile mismatch 0; stops मौजूद; verifier PASS | VM (demo) |
| **E-7** | Shadow: पुराने F4, 16B, PaperN1 ledgers चलते रहें; combined की तुलना रोज़ | सिर्फ़ report; मुख्य gate नहीं | VM |

**1D system के code के बारे में:** Step16, 16B और F4 वैसे ही चलते रहेंगे। सिर्फ़ उनका output पढ़ा जाएगा। F6 को बंद करना E-6 में होगा, और वह आपकी अलग हाँ से होगा।

---

## 4. Timeframes का sync कैसे होगा (एक clock)

- **Master clock:** हर 4h UTC close + 11 मिनट (IST 01:41, 05:41, 09:41, 13:41, 17:41, 21:41), यानी आज के PaperN1 वाला समय।
- **4h / 8h / 12h:** जिस cycle में उनकी candle बंद हुई, उसी cycle में उनके target बदलते हैं।
- **1D (N1 के 1D नियम):** 00:00 UTC वाली candle 05:41 IST cycle में।
- **1D brains (D1/H4/H1):** ये ~08:15 IST तक तैयार होते हैं (Step16 05:50, 16B 07:30, F4 07:45/08:15), इसलिए **09:41 IST cycle** में executor तक पहुँचेंगे। F6 आज 10:30 पर चलता है, यानी नया तरीका ~50 मिनट पहले होगा।
- **Virtual stops:** हर घंटे एक छोटा check (सिर्फ़ stop, कोई नई entry नहीं)।
- **5m / 15m:** सिर्फ़ data (FR2)। इन पर trade तभी होगा जब किसी भविष्य के protocol में execution timing पास हो।

---

## 5. आपसे चाहिए (आपके फ़ैसले / आपके हाथ के काम)

1. **नया trial budget** (प्रस्ताव 6 trials, ECO-1…6) और E-0 protocol lock की हाँ।
2. **Spot legs (~9% exposure) demo पर:** Binance demo के spot के लिए अलग keys लगेंगी, और keys आप ख़ुद `.env` में डालेंगे। विकल्प: demo phase में सब कुछ perp पर (यह फ़र्क protocol में लिखा जाएगा)।
3. **Demo account की capital:** अभी ~5,000 USDT है, जबकि N1 paper 10,000 मानता है। Executor equity के हिस्से में काम करता है, इसलिए यह चल जाएगा। पर छोटे account पर min notional की वजह से छूटा हिस्सा बढ़ेगा, जो E-3 में नापा जाएगा।
4. **E-6 पर F6 cron बंद करने की हाँ** (उस समय अलग से पूछूँगा)।

---

## 6. क्या नहीं पता (ईमानदारी से)

- Combined system अकेले system से बेहतर होगा या नहीं, यह E-2 से पहले कोई नहीं कह सकता। Backtest में monthly correlation 0.63 है, इसलिए diversification का फ़ायदा सीमित हो सकता है।
- Virtual stops (हर घंटे) बनाम exchange stops: अचानक gap में फ़र्क आएगा। E-3 इसे नापेगा।
- बिना 90 दिन के forward के, combined weights सिर्फ़ backtest पर टिके हैं, और N1 का P3 negative है।
