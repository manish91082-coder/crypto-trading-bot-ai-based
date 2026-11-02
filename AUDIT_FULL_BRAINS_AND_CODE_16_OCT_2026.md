# पूरा audit: AI दिमाग, training, data और code (16 अक्टूबर 2026)

**सवाल:** कहीं कुछ नकली, हवा में, hard-coded, नियम तोड़कर, या भविष्य का data (look-ahead) तो इस्तेमाल नहीं हुआ?

**तरीका:** हर जाँच script से हुई, और उसका output `logs/audit_full_16oct/` में रखा है। नई जाँचें:
- `src/audits/audit_brains_noleak.py`
- `src/audits/replay_d1_known_vs_step19.py`

---

## सार (ईमानदारी से)
- **Training और data में कोई धोखा या look-ahead नहीं मिला।** हर दिमाग की predictions दोबारा बनाने पर हूबहू मिलीं।
- **Code में कोई hard-coded नतीजा नहीं मिला, और कोई gate जबरन PASS नहीं करवाया गया।**
- **Lock के बाद हुए बदलाव:** 13 code files बदली गईं। सब `CODE_CHANGES_AFTER_LOCK.md` में दर्ज हैं, और जहाँ "बाद का" SHA लिखा था, वहाँ आज की files हूबहू मिलती हैं।
- **छोटी कमियाँ मिलीं (नीचे "कमियाँ" वाले हिस्से में)।** कोई भी नतीजा नहीं बदलती।
- **सबसे बड़ा खतरा code में नहीं, आँकड़ों में है:** एक ही 2021–26 data पर बहुत सारे tests हुए हैं। PBO 65% है, और DSR 0.95 से नीचे है। इसका इलाज सिर्फ forward log है, और वह चल रहा है।

---

## Audit 1: Protocol locks (क्या lock के बाद कुछ बदला?)
- **जाँच:** 35 lock files की 172 lines (protocol + code) के SHA दोबारा गिने।
- **Protocols:** सारे protocol files बिना बदलाव के हैं।
- **Code files:** 13 बदली गईं, और सब दर्ज हैं:

  | Step | बदलाव |
  |---|---|
  | Step 13, 17/18, 23 | Pehle run में crash या जाँच का bug था, model बनने से पहले |
  | Step 16 | Ledger reader |
  | Step 22 | Verifier |
  | S2 | `half` column |
  | S3 | Verifier |
  | SR study, Phase 2 | — |
  | 16B | Verifier |
  | F2 | Funding → isolated margin |

- **दर्ज SHA से मिलान:** S2 (ba93bb…), Step 23 (d63de7…), F2 (638346…) और Phase 2 (78ef41…) में आज की file = दर्ज "बाद का" SHA।
- **समय से मिलान:** File बदलने के समय (mtime) भी दर्ज crash-fix के समय से मेल खाते हैं।
- **बाकी "MISSING" lines:** वे files नहीं, lock की तारीख वाली lines हैं।

## Audit 2: सारे verifiers आज दोबारा चलाए (आज का code + आज का data)

| Verifier | नतीजा |
|---|---|
| Step 13, 15, 19 (D1 दिमाग) | PASS (फैसले वही: "skill है, अकेला trading नियम fail") |
| Step 22 (2018–19 exam) | PASS |
| Step 23 (R6), Step 24 (R24) | PASS |
| Step 27 (mix) | PASS |
| S1 (overfit, PBO 0.65) | PASS |
| F2 (long-short) | PASS |
| F7 (risk नियम) | PASS |
| S2 (R6/R24/D1) | PASS, R6 का 2022-06 model दोबारा train करने पर 3,600 predictions बराबर |
| S3 (R6) | PASS |
| 16B forward | V1–V5 सब PASS। V2 PASS (सितंबर के models दोबारा train किए, research scores मिले); V3 PASS (production अक्टूबर models = research के frozen दिमाग, 2018–19 की 2,57,425 rows, फर्क 5.6e-17); V4 PASS (paper engine = Step 27: D1 $43,151.15, H4 $49,365.87, H1 $69,134.22); V5 PASS (test run के hash और chain सही) |

## Audit 3: Hard-coding, gate bypass, look-ahead की खोज
**खोजे गए patterns:**
- `decision = "PASS"`
- `G = True`
- `except: pass`
- `bfill`
- `shift(-…)`
- `center=True`

**नतीजे:**
- **Gate:** "PASS" सिर्फ `all(gates)` की शर्त से बनता है (Step 28, 30)। कहीं भी जबरन True नहीं।
- **Errors छिपाना / भविष्य से भरना:** कोई `except: pass` नहीं, कोई `bfill` नहीं, और कोई negative shift नहीं।
- **`center=True` (आगे देखने वाली rolling):** 4 research files में है:
  - sr_levels
  - sr_volume
  - swing_anatomy
  - swing_vs_sr

  हर जगह pivot सिर्फ अपनी पुष्टि के बाद इस्तेमाल हुआ (`i+K`, `i+k+1`)। ये files live दिमागों में इस्तेमाल भी नहीं होतीं।
- **Labels:** `open(t+1+h)/open(t+1) − 1`। "Known" = उस आखिरी open का समय।
- **Training:** हर महीने सिर्फ `known < महीने की शुरुआत` वाली rows, और साथ में `assert bar < T`। D1, R6 और R24 तीनों में यही है।

## Audit 4: दिमागों में भविष्य का data? (सबसे पक्के सबूत, नई जाँच)

| जाँच | नतीजा |
|---|---|
| **A: Feature truncation** (R6, R24) | 40 + 40 stored rows। Raw 1h file को bar के अंत पर काटकर features दोबारा बनाए। **सारे 24 features हूबहू वही (फर्क 0)।** कोई feature आगे नहीं देखता। |
| **B: पुराने महीने का model शुरू से** (जून 2022) | R6: 1,34,053 training rows, सबके label 1 जून 2022 से पहले पता थे। **3,600 predictions research से बराबर (फर्क 5.6e-17)।** R24: 1,78,363 rows, **14,400 predictions बराबर।** साथ में जाँचा कि "known" ≥ bar + 28h (R6) / 25h (R24)। |
| **C: D1, नए coins** | Production D1 file (Step 19) की 9,799 rows Step 15 R5 से हूबहू मिलीं (फर्क 0)। Replay (data को as-of दिन पर काटकर, उस महीने का model शुरू से): **15 जून 2022 को 98/98 और 15 सितंबर 2026 को 44/44 coins बराबर।** |
| **C2: D1, 30 पुराने known coins** (पहले कभी नहीं जाँचे गए थे) | उसी तरह replay: **2022 में 17/17 और 2026 में 15/15 बराबर (फर्क 5.6e-17)।** |
| **नकली दिमाग से तुलना** | D1 AUC 0.559 (CI 0.549–0.571) बनाम shuffled 0.494; R6 0.568 बनाम 0.501; R24 0.565 बनाम 0.501। Skill असली है, पर छोटी है। |

## Audit 5: Data (दो अलग स्रोत)
- **Spot 1d:** 40 random coin-days, archive (data.binance.vision) बनाम live Binance REST API: **40/40 हूबहू।**
- **Spot 1h:** 60 random hours (2025 से पहले के 25 + 2025–26 के 35): **60/60 हूबहू।** 20 hours छोड़े गए, क्योंकि वे coins delisted हैं और API पर उनका data नहीं है।
- **Futures:** F4 test में API बनाम archive, 24,864 hours और 4,097 funding events: **0 फर्क।**
- **Futures checksum log:** 12,912 OK, 8,958 404 (coin उस महीने था ही नहीं), 0 खराब।

## Audit 6: Execution code (असली पैसे की सुरक्षा)
- **Order भेजने वाले code:**
  - spot: `live_1d_ai_engine`, `live_1d_swing_engine`, जो testnet पर मजबूर (sandbox assert) हैं;
  - futures: `futures_testnet_f6`, जिसमें सिर्फ testnet और demo hosts हैं, और बाकी host पर assert।
  - **कहीं भी mainnet order का रास्ता नहीं है।**
- **Mainnet hosts:** सिर्फ public data पढ़ने में (F4 की कीमतें, dryrun klines, cost study)। उनमें न key है, न order।
- **Keys:** code में कोई key लिखी हुई नहीं है। सिर्फ environment variables से आती हैं।

---

## कमियाँ जो मिलीं (कोई भी नतीजा नहीं बदलती)
1. **Verifiers की पुरानी कमी (अब भर दी):**
   - Step 19/23/24 के verifiers labels, AUC और portfolio दोबारा गिनते थे, पर features का truncation और पुराने महीने का retrain नहीं करते थे।
   - D1 के 30 known coins की predictions कभी replay नहीं हुई थीं।
   - **अब तीनों हो गए, PASS** (Audit 4)।
2. **F2/F7 scale gate:** किसी coin का perp/spot अनुपात पूरे समय (2020–26) के median से जाँचा गया। इससे 3 coins (IDEX, RAY, STRAX) बाहर हुए।
   - यह "भविष्य जानकर" छाँटना है, पर छोटा: इन coins का perp दूसरी इकाई (scale) में था, उन्हें रखना गलत data होता।
   - F4 forward में यह जाँच सिर्फ पिछले 7 दिन से होती है, यानी कोई look-ahead नहीं।
3. **16B verifier का log:** जाँच के दौरान train हुए models की lines वह असली forward `run_log.txt` में लिख देता है। Models temp folder में बनते हैं और ledger नहीं छुआ जाता। सिर्फ log में अतिरिक्त lines हैं, कोई गलत नतीजा नहीं।
4. **बहुत सारे tests एक ही data पर (data snooping), यही असली खतरा है:**
   - PBO 65% है।
   - DSR: M_AI3 0.44, F2 0.875, F7 0.879, सब 0.95 से नीचे।
   - F7 के नियम F2 के trades देखने के बाद बने (protocol में दर्ज)।
   - **Code सही है, पर backtest का फायदा आँकड़ों से साबित नहीं है।** फैसला सिर्फ forward log (16B और F4) से होगा।

## नतीजा
- **कोई नकली, hard-coded या bypass किया हुआ नतीजा नहीं मिला।**
- **दिमागों की training में भविष्य का data नहीं है।** यह तीन तरह से साबित हुआ:
  1. features का truncation test;
  2. पुराने महीने का retrain;
  3. as-of दिन पर data काटकर replay।
- **ईमानदार सीमा:**
  - दिमागों की skill छोटी है (AUC ~0.56)।
  - Backtest की कमाई पर overfitting का खतरा है (PBO 65%)।
  - असली जज सिर्फ forward सबूत है।

---

## सुधार (16 अक्टूबर, audit के बाद): जो गलतियाँ मिलीं और ठीक कीं

| # | क्या मिला | कितना गंभीर | सुधार और सबूत |
|---|---|---|---|
| 1 | **F4 में असली bug:** `L16.asof` pandas का built-in `asof` method है, column नहीं। तुलना हमेशा False निकलती, यानी **आज 08:30 का F4 का पहला run fail हो जाता।** यही गलती F4 verifier और F6 में भी थी। | ऊँचा (forward log का पहला दिन छूट जाता) | `["asof"]` से ठीक किया। **Sandbox pre-flight** (`src/audits/preflight_f4.py`): 2 दिन बिना error चले, chain सही, C1 True, orders file बनी। F4 verifier भी उसी sandbox पर **V1–V5 PASS**। दर्ज: `logs/forward_ls_f4/CODE_CHANGES_AFTER_LOCK.md` (2)। |
| 2 | **F6 stop-sync:** stop order "CANCELED" या "EXPIRED" होने पर भी code मान लेता कि stop लग गया, और position हटा देता। Short बिना सुरक्षा के खुला रह जाता। | ऊँचा (testnet पर भी गलत आदत) | अब position सिर्फ TRIGGERED/FINISHED पर हटती है। बाकी हालत में stop दोबारा लगता है, और stop न लगे तो चेतावनी आती है। Status values Binance के official SDK से लिए। दर्ज: `logs/futures_testnet_f6/CODE_CHANGES_AFTER_LOCK.md`। |
| 3 | **16B verifier** अपनी जाँच की lines असली forward `run_log.txt` में लिखता था। | कम (सिर्फ log) | अब `verify_run_log.txt` में लिखता है। पुरानी lines (5–8) की पहचान दर्ज की, log edit नहीं किया। दर्ज: `logs/forward_multi_16b/CODE_CHANGES_AFTER_LOCK.md` (3)। |
| 4 | **F2/F7 scale gate** पूरे 2020–26 के median से (look-ahead) | कम | **सिर्फ report के लिए दोबारा run**, बिना look-ahead वाले gate (हर दिन पिछले 7 दिन) से: $94,759, गिरावट 18.7%, 0 liquidations। दर्ज F7 में $88,401 और 21.4% है। **यानी look-ahead ने नतीजा नहीं फुलाया।** Official F7 फैसला वही रहेगा जो lock हुआ था। Script: `src/audits/audit_scale_gate_lookahead.py`। |
| 5 | **Verifiers का पुराना gap** (truncation, पुराने महीने का retrain, D1 के known coins) | मध्यम (सबूत अधूरा था) | नई जाँचें बनीं, सब PASS (Audit 4)। |

**F6 plan mode (बिना keys, बिना order):** sandbox के फैसले पर 15 planned shorts बने, हर एक पर ×1.50 का stop।
- Testnet और demo की कीमतें असली market से ~0.03% के अंदर हैं (BTC, DOGE, BCH, SUI, BNB)।
- Testnet की liquidity असली नहीं होती, इसलिए वहाँ का slippage सिर्फ इशारा है।

**कुछ भी जो बदला नहीं:**
- किसी दिमाग की training, कोई research नतीजा, कोई gate या protocol।
- 16B का ledger।
- F4 का कोई forward data (pre-flight सिर्फ temp folder में चला)।
