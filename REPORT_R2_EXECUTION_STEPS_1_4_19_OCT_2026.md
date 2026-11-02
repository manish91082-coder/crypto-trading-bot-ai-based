# R2: audit plan का ज़मीनी execution, क्रम 1 से 4 (19 अक्टूबर 2026, laptop पर)

**आधार:** `REPORT_MASTER_AUDIT_18_OCT_2026.md` और master भाग 7 + 11 का क्रम।

**हर क्रम एक ही तरीके से हुआ:**
1. पहले protocol लिखकर SHA lock;
2. फिर code;
3. फिर असली data पर run;
4. फिर अपने अलग code वाला independent verifier;
5. lock के बाद का हर बदलाव `CODE_CHANGES_AFTER_LOCK.md` में।

**क्या नहीं छुआ गया:**
- **Cloud VM: कुछ नहीं बदला।** आपने कहा था कि पहले यहाँ करें, test करें, फिर cloud।
- 1D system, laptop production, `archive/` और GitHub भी अछूते हैं।
- कोई order या key नहीं (सिर्फ़ public endpoints)।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

## सार
| क्रम | क्या हुआ | नतीजा |
|---|---|---|
| 1 | Errata index | ✅ `ERRATA_INDEX_R2_19_OCT_2026.md`। पुरानी files नहीं बदलीं, ताकि उनके SHA (सबूत) न टूटें |
| 2 | Forward recorder (local) | ✅ Protocol `3d9c9693…`। T1 में **एक असली bug पकड़ा गया और ठीक हुआ।** अब T1, T2, T3a/b/c, T4 सब PASS; verifier 8/8 |
| 3 | A0 (4H AI का master protocol) | ✅ Lock `4d49d411…` |
| 4 | A1 (बिना AI के signal माप) | ✅ Sub-protocol `8aad1f39…`; 9,721 trades; verifier 5/5 PASS। 8 में से 8 signal-sides gate पास, पर ईमानदार सीमाएँ नीचे हैं |

---

## क्रम 1: Errata index
- **File:** `ERRATA_INDEX_R2_19_OCT_2026.md` (`76f77628…`)। इसमें 18 पुरानी बातें हैं, और हर एक के साथ उसकी file और SHA, अब मान्य मान और स्रोत।
- **पुरानी files में नोट क्यों नहीं जोड़ा:** उनके SHA master के भाग 0 और audit verifier में दर्ज हैं। नोट जोड़ने से वे SHA बदल जाते और सबूत की chain टूट जाती।

## क्रम 2: Forward recorder (सबसे ज़रूरी, क्योंकि साफ़ holdout सिर्फ़ forward data है)
### ज़मीनी कारण, दो स्रोतों से पक्का
- **Binance docs:** `openInterestHist` पर लिखा है "Only the data of the latest 1 month is available"। Long/short ratio और basis के पन्नों पर भी 30 दिन की सीमा है।
- **Live test (आज):** open interest और taker ratio 29 दिन पीछे तक HTTP 200 देते हैं, और 40 दिन पीछे पर **HTTP 400**। यानी 30 दिन के अंदर दर्ज न हुआ data हमेशा के लिए खो जाता है।
- **Klines** 2020 तक की दोबारा मिलती हैं। फिर भी उन्हें दर्ज किया जाता है, ताकि "कब पता चला" (`available_at`) का सबूत रहे और exchange बाद में कुछ बदले तो वह पकड़ में आए।

### क्या दर्ज होता है
- **23 symbols:** 10 research coins और आज के top-20 perps।
- **Re-download हो सकने वाला data:** spot की 5m/15m/1h/4h/1d candles; perp और mark price की 1h/4h candles; funding।
- **30 दिन की सीमा वाला data (5m):** open interest, top trader account और position ratio, global ratio, taker ratio, basis।
- **Live snapshots** (जो कभी दोबारा नहीं मिलते): premium/mark, अभी का OI, perp depth (100 levels), spot best bid/ask, हर symbol का funding interval, exchangeInfo।
- **हर run के साथ:** byte-exact raw files, manifest (हर file का SHA), state और hash-chained ledger।

### एक असली bug पकड़ा और ठीक किया (बिना rubber-stamp के)
**कैसे पकड़ा गया:**
- पहले T1 में verifier की V1–V7 जाँचें PASS थीं, पर V4 ने **368 छूटे 5m timestamps** दिखाए।
- यह संख्या ठीक series की गिनती (368) के बराबर थी, इसलिए मैंने इसे संयोग न मानकर जाँचा।

**क्या निकला:**
- सारे gaps सिर्फ़ `takerlongshortRatio` में थे: हर symbol पर 16, और बाकी 5 endpoints में 0।
- **कारण** raw files से नापा गया: यह endpoint startTime से नीचे वाले 5m से rows देता है, जबकि बाकी endpoints ऊपर वाले से। इस वजह से हर page की सीमा पर 1 row छूट जाता था।

**सुधार:**
- Paging को cursor वाला बनाया: अगला request आख़िरी रखे गए timestamp के 1 ms बाद से शुरू होता है।
- Verifier में **नई V8 जाँच** जोड़ी: हर छूटे timestamp को Binance से दोबारा माँगा जाता है, और अगर वह वहाँ मौजूद है तो FAIL।
- **पुराने bug वाले run पर V8 = FAIL** हुआ: sample किए गए 60 में से 60 timestamps Binance पर मौजूद थे। यानी वे gaps "बिना trade वाली अवधि" नहीं थे, recorder की गलती थे।
- पुराना run सबूत के तौर पर रखा गया है (`logs/forward_recorder_r2_localtest_T1_bugged_kept_as_evidence/`), मिटाया नहीं गया।

### सुधार के बाद के tests (सब PASS)
| Test | नतीजा |
|---|---|
| **T1** पहला run | 2,808 files, 11,80,101 rows, 2,812 requests, **0 HTTP errors, 0 gaps**; घड़ी का अंतर −1.2 s |
| T1 verifier | V1 chain, V2 SHA, V3 **60/60 rows live API से दोबारा लाकर हूबहू**, V4 207 kline series बिना gap, V5 कोई look-ahead नहीं, V6 कोई duplicate नहीं, V7 state, V8 **0 छूटे**: **8/8 PASS** |
| **T2** तुरंत दूसरा run | सिर्फ़ नए rows (1,012), ledger की 2 lines जुड़ी chain में; verifier 8/8 |
| **T3a** raw file में 1 byte बदला | Verifier **V2 FAIL** (जैसा होना चाहिए) |
| **T3b** ledger की एक line हटाई | **V1 FAIL** |
| **T3c** state.json बदला | **V7 FAIL** |
| **T4** lock file मौजूद रहते run | कुछ नहीं लिखा, lock वैसा ही रहा |

**आकार:**
- पहला (bootstrap) run 25 MB, आगे हर run ~1–2 MB, यानी 90 दिन में लगभग 1–1.5 GB।
- VM पर 36 GB ख़ाली है।

## क्रम 3: A0 protocol (lock `4d49d411…`)
`logs/r2_4h_a0/A0_4H_PROTOCOL_PREREGISTERED.md`। Audit की सारी बातें इसमें शामिल हैं:
- **Costs:**
  - **base taker 0.05% (0.054% प्रति तरफ़ spread सहित)**;
  - **असली funding**;
  - 1.5×, 2×, आशावादी और बिना BNB वाले scenarios।
- **Portfolio simulator:** 8,000 USDT; 0.5% risk; K = 6; ≤ 3× isolated; min notional; **realised और mark-to-market दोनों DD**।
- **क्या नहीं होगा:** DD-halving, हार के बाद रुकना, एक दिशा की cap (audit E6, N17)।
- **Gates:**
  - shuffled control और bootstrap CI;
  - random-skip के 95th percentile से बेहतर;
  - **tail gate** (AI बड़े winners को सिक्का उछालने से ज़्यादा बार न छोड़े);
  - P1 और P2 दोनों में;
  - DSR ≥ 0.95, PBO < 0.30 (≥ 4 configs होने पर ही, पहले "गणना संभव नहीं");
  - 1D से correlation;
  - 2018–19 पर जाँच।
- **Kill switch:** backtest DD के 2× पर review। हार की लड़ी पर कोई alarm नहीं।
- **L6 alarms:** BNB balance, funding interval, perp status।
- **Global risk:** 4h sleeve पर 3%। 1D के साथ साझा सीमा आप A9 से पहले तय करेंगे।
- **Trial budget 20:** A1 में 4, A3 में 2, A4 में 8, A6 में 1, reserve 5। Registry hash-chained है (`logs/r2_4h_a0/trial_registry.csv`, 8 lines)।
- **नियम:** हर चरण का verifier PASS होने और **आपके report देखने** के बाद ही अगला चरण।

**Code पढ़कर जाँचा:** पुराने swing features (`c_htf_state_*`) causal हैं। ZigZag की हालत confirm वाले bar पर ही लिखी जाती है, और बड़े TF की हालत सिर्फ़ बंद candle से ली जाती है। इसे A2 में असली data पर leak canary से भी परखा जाएगा।

## क्रम 4: A1, बिना AI के signal माप (4 trials इस्तेमाल हुए, 20 में से)
**Setup:**
- 10 coins, 4h, 2020-02 से 2026-09।
- Exit S6 वाला (3 ATR trailing, 60 bar)।
- **Base cost 0.054% प्रति तरफ़ + असली funding।**
- Perp listing से पहले के 84 trades बाहर।
- Gate: gross ≥ 2 × खर्च, और P1 व P2 दोनों में net > 0।

| Signal | Side | Trades (dev) | Gross/खर्च | Net R/trade | 95% CI | P1 | P2 | **P3** | Gate |
|---|---|---|---|---|---|---|---|---|---|
| **S-LAD** (सीढ़ी) | long | 883 | 5.1× | **+0.134** | **+0.071…+0.198** | +0.114 | +0.181 | **−0.127** | PASS |
| S-LAD | short | 767 | 4.7× | +0.062 | +0.001…+0.124 | +0.052 | +0.082 | +0.113 | PASS |
| S-BRK (breakout) | long | 2,215 | 2.7× | +0.084 | +0.024…+0.147 | +0.061 | +0.134 | **−0.146** | PASS |
| S-BRK | short | 1,787 | 2.6× | +0.044 | **−0.007…+0.097** | +0.002 | +0.132 | +0.011 | PASS |
| S-TRD (trend EMA50) | long | 1,071 | 2.8× | +0.093 | +0.010…+0.180 | +0.032 | +0.219 | **−0.035** | PASS |
| S-TRD | short | 1,042 | 2.4× | +0.051 | **−0.037…+0.137** | +0.037 | +0.076 | +0.100 | PASS |
| S-DTB (double bottom/top) | long | 163 | 3.2× | +0.068 | **−0.057…+0.205** | +0.077 | +0.043 | **−0.324** | PASS |
| S-DTB | short | 164 | 4.6× | +0.070 | **−0.094…+0.244** | +0.065 | +0.081 | −0.026 | PASS |

**Verifier** (`verify_r2_a1.py`, अपने अलग loops से): **5/5 PASS**।
- S-BRK और S-TRD के signals 3 coins पर दोबारा बनाए गए: हूबहू मिले।
- 200 random trades दोबारा simulate किए: gross, fee, funding और exit सब हूबहू।
- Gate table trades से दोबारा निकाली गई: मेल खाती है।
- SHAs मेल खाते हैं।
- **S-LAD के 1,976 trades S6 से trade-by-trade हूबहू मिले।**

**ईमानदार पढ़ाई (rubber-stamp नहीं):**
1. **Gate ढीला निकला।** सभी 8 पास हुए, पर **95% CI सिर्फ़ 4 का शून्य से ऊपर है** (S-LAD long, S-LAD short बाल-बाल, S-BRK long, S-TRD long)। बाकी 4 का CI शून्य को छूता है।
2. **आख़िरी साल (P3) में सारे longs घाटे में रहे**, जबकि shorts ज़्यादातर कमाई में। यह audit में मिली बात की पुष्टि करता है। P3 gate में नहीं है (पहले देखा जा चुका है), पर यह चेतावनी है।
3. **सबसे मज़बूत signal सीढ़ी (S-LAD) है।** Long में खर्च का 5 गुना, CI साफ़ शून्य से ऊपर।
4. **ये signals एक-दूसरे से जुड़े हैं** (एक ही coin पर एक ही समय)। A3 में इन्हें अलग-अलग नहीं जोड़ा जाएगा। AI एक साथ सबको देखेगा।
5. **Protocol के अनुसार** सभी 8 पास हुए signal-sides A3 में जा सकते हैं। पर A3 का gate (shuffled control, CI, random-skip, tail) कड़ा है, और वहीं असली परीक्षा होगी।

## आगे (आपकी मंज़ूरी पर)
1. **Cloud पर forward recorder शुरू करना (क्रम 2 का cloud वाला हिस्सा):**
   - VM पर अलग folder `data/forward_r2/`।
   - Crontab में 6 नई lines: हर 4h close के 7 मिनट बाद, यानी 05:37, 09:37, 13:37, 17:37, 21:37 और 01:37 IST।
   - 1D system की किसी file या job को नहीं छुआ जाएगा, सिर्फ़ crontab में lines जुड़ेंगी।
   - Cloud पर verifier रोज़ चलेगा।
   - **हर दिन की देरी, 30 दिन वाले data का एक दिन खोती है।**
2. **A2 (knowledge store + leak canary)** शुरू करना। A0 के नियम के अनुसार आपके यह report देखने के बाद ही।
3. F6 drill-kill (पिछला पूछा हुआ सवाल, अभी बाकी)।

## Files
| क्या | कहाँ |
|---|---|
| Recorder | `src/execution/forward_recorder_r2.py` (`557fa486…`) |
| Recorder verifier | `src/audits/verify_forward_recorder_r2.py` (`f5b17a12…`) |
| Recorder tests | `src/audits/test_forward_recorder_r2.py` |
| Recorder logs | `logs/forward_recorder_r2/` (protocol, lock, CODE_CHANGES, T1/T2–T4 logs) |
| Recorder का local data | `logs/forward_recorder_r2_localtest/` |
| A0 | `logs/r2_4h_a0/` (protocol, lock, trial_registry) |
| A1 | `logs/r2_4h_a1/` (protocol, lock, `a1_trades.parquet`, `A1_gate.csv`, claims, verify logs) |
| A1 code | `src/research/r2_a1_edge_map.py` |
| A1 verifier | `src/audits/verify_r2_a1.py` |
