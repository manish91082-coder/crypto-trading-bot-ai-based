# 📅 1-Day (1D) Timeframe — विस्तृत ऑडिट रिपोर्ट

**तारीख:** 11 अक्टूबर 2026
**दायरा:** 1D से जुड़ी हर चीज़:
- `src/pipeline_1d/ai_1d_master_pipeline.py`
- `src/pipeline_1d/ai_final_aggressive_1d_system.py`
- `archive/research_archive/ai_1d_*.py` (6 scripts)
- `data/raw/*_1d_*`, `data/processed/*_1d_*` (30 files)
- `models/1d_standard/` (40 models), `models/1d_aggressive/` (40 models)
- `logs/ai_final_aggressive_1d_*.csv`
- `src/analytics/analyze_logs.py`
- दोनों PDF

**तरीका:**
- प्रोजेक्ट का कोई कोड नहीं बदला गया।
- हर backtest scratchpad में चलाया गया, इसलिए `logs/` की कोई फाइल overwrite नहीं हुई।
- `pypdf` install करके दोनों PDF पढ़े गए।

**नोट:** यह तकनीकी ऑडिट है, निवेश सलाह नहीं।

> पहली रिपोर्ट: [AUDIT_REPORT_HINDI_11_OCT_2026.md](AUDIT_REPORT_HINDI_11_OCT_2026.md)। यह रिपोर्ट सिर्फ 1D पर गहराई से जाती है।

---

## 0. सीधा जवाब: "क्या 1D models ठीक से train हुए हैं?"

**नहीं।** तीन स्वतंत्र सबूत:

1. **Models ने training डेटा याद कर लिया है (overfit)।** Aggressive models का AUC training पर **0.952** और अनदेखे डेटा पर **0.504** है। 0.5 का मतलब है सिक्का उछालने जितनी accuracy।
2. **"$231,778" ज़्यादातर in-sample (training) अवधि से आया है।** उसी सिस्टम को सिर्फ training cutoff (2024-04-05) के बाद चलाया तो:

   **$120 → $53.26 (−55.6%), Max DD 77.2%**
3. **Features में ही स्थिर edge नहीं है।** Purged walk-forward test में (सही तरीके से train करने पर भी) OOS AUC fold-दर-fold **0.37 से 0.66** के बीच झूलता है। Long side पर यह ज़्यादातर 0.5 से नीचे या आसपास रहता है।

यानी समस्या सिर्फ "गलत training" नहीं है। **मौजूदा 7 features 1D पर लगातार काम करने वाला signal नहीं दे रहे।**

---

## 1. 1D सिस्टम असल में कैसे बना (Archive scripts से पूरी कहानी)

| क्रम | Script | क्या किया | OOS रखा? |
|---|---|---|---|
| 1 | `ai_1d_master_pipeline.py` | TP 3× / SL 2× / 60 दिन labels, standard models, 0.65 threshold | ✅ 20% OOS पर test |
| 2 | `ai_1d_explorer.py` | TP/SL के 4 combinations (4/1.5, 5/1.5, 6/2, 8/2) का grid search; हर बार retrain करके **उसी** फाइल को overwrite किया | OOS पर simulate, पर **OOS से ही parameter चुने** |
| 3 | `ai_1d_in_depth_research.py` | threshold और risk का grid search | OOS पर, फिर से parameter tuning |
| 4 | `ai_1d_macro_filter_test.py` | BTC के SMA-50 पर regime filter, risk 5% | OOS पर |
| 5 | `ai_1d_5year_backtest.py` | **यहाँ OOS split हटा दिया गया**, पूरा data | ❌ |
| 6 | `ai_1d_5year_ultimate_backtest.py` | BTC SMA-200 regime, max 4 trades | ❌ |
| 7 | `ai_1d_5year_aggressive_v2.py` | Pyramiding | ❌ |
| 8 | `ai_final_aggressive_1d_system.py` (src) | Trailing, breakeven, 7-दिन exit | ❌ पूरा data |

**दो बुनियादी गलतियाँ:**
- **(क) OOS पर बार-बार tuning:** कदम 2 से 4 में OOS हिस्से पर TP/SL, threshold और risk का grid search हुआ। इससे OOS "देखा हुआ" बन गया (multiple-testing bias)।
- **(ख) Split हटाना:** कदम 5 से split ही हटा दिया गया, इसलिए headline result में 80% अवधि in-sample है।

---

## 2. ✅ 1D में क्या सही है (Verified)

| # | बात | सबूत |
|---|---|---|
| 1 | Valid 1D raw data साफ है | सभी 10 coins में OHLC या volume की कोई गड़बड़ी नहीं (high ≥ max(open, close), low ≤ min, volume > 0); 0 violations |
| 2 | Features causal हैं (भविष्य का डेटा नहीं देखते) | सिग्नल दिन D के close पर, entry D+1 के open पर |
| 3 | `1d_ML_Labeled` बिल्कुल TP 3× / SL 2× / 60 दिन से बना है | BTC के labels recompute किए, **100% match** |
| 4 | Same-day TP और SL दोनों लगें तो पहले SL माना जाता है (pessimistic) | `ai_1d_master_pipeline.py:99,107` |
| 5 | Standard models के params कोड से मेल खाते हैं | 200 trees, lr 0.01, depth 3; meta: 100 trees, lr 0.05, depth 2 |
| 6 | Fee 0.075% entry, exit और partial exit तीनों पर लगती है | aggressive `:116,146,172,214` |
| 7 | Breakeven, 50% partial, trailing और 7-दिन exit का logic कोड में वैसा ही है जैसा doc बताता है | `:99-164` |
| 8 | Logs reproducible हैं | दोबारा चलाने पर वही 550 trades और $231,778.87 आए |
| 9 | 1D पर fee का असर 15m से बहुत कम है (doc का सामान्य निष्कर्ष सही है) | 1d std OOS: $120 → $118.79, जबकि 15m: $120 → $31.63 |

---

## 3. 🔴 1D की Critical गलतियाँ (सबूत के साथ)

### D1. Headline result in-sample है, और OOS में भारी नुकसान
Aggressive system के 4 variants scratchpad में चलाए गए। सिर्फ entry की तारीख और position limits बदले, बाकी पूरा logic वही रखा:

| Variant | Trades | Win% | Max DD | Final Capital |
|---|---|---|---|---|
| जैसा है (पूरी अवधि) | 550 | 54.55% | 77.97% | **$231,778.87** |
| जैसा है, सिर्फ cutoff 2024-04-05 के बाद की entries | 176 | 40.91% | 77.20% | **$53.26** |
| Spot-realistic (सिर्फ long, कुल position ≤ 1× capital), पूरी अवधि | 295 | 50.85% | 47.51% | **$462.43** |
| Spot-realistic, cutoff के बाद | 104 | 44.23% | 43.68% | **$96.33** |

**मतलब:**
- असली spot account में in-sample अवधि के साथ भी यह $231k नहीं, बल्कि **$462** होता।
- अनदेखे डेटा पर पैसा **घटा** है।

Trade log को training cutoff से बाँटने पर (per-trade R = PnL ÷ शुरुआती risk):

| | Trades | Win% | औसत R/trade |
|---|---|---|---|
| In-Sample, Long | 269 | 56.5% | **+0.505R** |
| In-Sample, Short | 99 | 72.7% | **+0.906R** |
| OOS, Long | 152 | 39.5% | **−0.028R** |
| OOS, Short | 30 | 53.3% | **−0.001R** |

- OOS में expectancy लगभग **शून्य या नकारात्मक** है।
- Partial TP (3×ATR) लगने की दर In-Sample में **24.2%** थी और OOS में **11.0%** रह गई।
- साल-दर-साल औसत R: 2022 में 0.511, 2023 में 0.655, 2024 में **0.147**।

**महीनों का पैटर्न (`analyze_logs.py` चलाकर):**
- 2024-02 में **+$170,728** और 2024-03 में **+$260,450**। यह ठीक training खत्म होने से पहले का हिस्सा है।
- उसके बाद 2024-04 में **−$157,075**, 2024-05 में −$51,745, 2024-06 में **−$130,171**, 2024-12 में −$69,993।

### D2. Overfitting: बहुत कम डेटा पर बहुत जटिल model
| Model set | Train AUC | OOS AUC | Meta > threshold सही होने की दर (Train → OOS) |
|---|---|---|---|
| 1d aggressive (0.80) | 0.952 | 0.504 | 74.0% → **15.5%** |
| 1d standard (0.65) | 0.897 | 0.588 | 82.6% → **46.1%** |

- हर coin और direction के लिए सिर्फ **~718 training rows** हैं (कुल 898 का 80%)।
- Labels 60 या 90 दिन आगे देखते हैं, इसलिए लगातार rows के labels लगभग एक जैसे होते हैं। **स्वतंत्र samples बहुत कम हैं:** 90 दिन के horizon पर मोटे तौर पर 718 ÷ 90 ≈ **8 पूरी तरह स्वतंत्र खिड़कियाँ**।
- **Feature importance (aggressive primary, औसत):** `Dist_SMA_200` 0.285, `Vol_Z_Score` 0.206, `Dist_SMA_50` 0.206। यानी model मुख्य रूप से यह सीख रहा है कि उस दौर में price SMA से ऊपर था या नीचे (बाज़ार का दौर, जिसे regime कहते हैं)। यह training अवधि (2022 bear, 2023 bull) को याद करना है।
- **Meta-model 86.1% सिर्फ `Primary_Confidence` पर टिका है।** यह confidence training डेटा पर निकाली गई है, इसलिए वहाँ बढ़ी हुई होती है (पहली रिपोर्ट का C6)।

### D3. Labels का base rate बदल गया (Regime shift)
TP 8× labels (aggressive models इन्हीं पर train हुए): Long label = 1 वाली rows का प्रतिशत, train से test तक:

| Coin | Train | Test |
|---|---|---|
| BTC | 28% | 12% |
| BNB | 30% | 11% |
| SOL | 27% | **5%** |
| XRP | 28% | 6% |
| ETH | 25% | 10% |

- Model ने सीखा कि "हर 4 में से 1 setup जीतता है", जबकि test अवधि में हर 10 से 20 में से 1 जीता। Model का confidence इस बदलाव के हिसाब से adjust नहीं होता।

### D4. Model, label और execution तीनों अलग-अलग नियमों पर हैं
| | Model किस label पर train हुआ | Execution में असल नियम |
|---|---|---|
| Aggressive | **TP 8× / SL 2× / 90 दिन** (100% match से verify; explorer का आखिरी loop फाइलें overwrite कर गया) | SL 1.5×, 3× पर 50% partial, 2× trailing, **7 दिन** exit |
| Standard | TP 3× / SL 2× / 60 दिन | TP 3× / SL 2×, **कोई timeout नहीं** |
| Doc में लिखा | TP 5× / SL 1.5× (1:3.33) | — |

- Model "90 दिन में 8× ATR का बड़ा trend आएगा या नहीं" पढ़ता है, पर trade 7 दिन में बंद हो जाता है। **Prediction और trade अलग-अलग सवालों के हैं।**

### D5. Spot में असंभव exposure और Short
- एक साथ खुली positions का कुल notional **9.69× capital** तक पहुँचा। 988 में से 752 दिन यह 1× से ऊपर रहा।
- 129 Short trades spot डेटा पर लिए गए।
- Sizing को spot के हिसाब से सीमित करते ही नतीजा $231k से **$462** पर आ जाता है (D1 की तालिका देखें)।

### D6. सही तरीके से train करने पर भी features में स्थिर edge नहीं है (Walk-forward सबूत)
**तरीका:**
- 10 coins का डेटा मिलाकर (pooled) test किया गया।
- Expanding window: हर test खिड़की से पहले का सारा डेटा train में लिया।
- Label horizon के बराबर purge रखा (60 या 90 दिन), ताकि train के labels test अवधि में न घुसें।
- दो models आज़माए: shallow XGBoost (depth 2) और Logistic Regression।

Test अवधि का AUC (0.5 = कोई edge नहीं):

| Label | Side | 2023 H1 | 2023 H2 | 2024 H1 | 2024 H2 |
|---|---|---|---|---|---|
| TP3/SL2/60d | Long (xgb / lr) | 0.487 / 0.561 | 0.424 / 0.372 | 0.411 / 0.508 | 0.519 / 0.449 |
| TP3/SL2/60d | Short | 0.453 / 0.585 | 0.478 / 0.535 | 0.472 / 0.461 | 0.616 / 0.614 |
| TP8/SL2/90d | Long | 0.565 / 0.392 | 0.428 / 0.388 | 0.516 / 0.597 | 0.499 / 0.435 |
| TP8/SL2/90d | Short | 0.579 / 0.650 | 0.606 / 0.864 | 0.660 / 0.562 | 0.542 / 0.565 |

- **Long:** लगातार 0.5 के आसपास या नीचे। कोई भरोसेमंद edge नहीं।
- **Short (TP8):** कुछ folds में 0.5 से ऊपर है, पर base rate सिर्फ 4 से 11% है (बहुत कम positive samples) और नतीजे अस्थिर हैं। इसे edge कहना अभी जल्दबाज़ी होगी, यह सिर्फ आगे जाँचने लायक संकेत है।
- **निष्कर्ष:** सिर्फ hyperparameters बदलने से 1D ठीक नहीं होगा। **Features और label design पर दोबारा काम चाहिए।**

---

## 4. 🟠 1D की High/Medium गलतियाँ (फाइल:लाइन के साथ)

1. **2025 और 2026 का डेटा गायब है।** 1D में भी 1,826 में से 638 rows का timestamp साल 56971+ जैसा है (microseconds को milliseconds मान लिया गया)। 1D का valid डेटा सिर्फ 2021-10 → 2024-12 है, जबकि 2025-01 → 2026-09 को सबसे साफ holdout होना चाहिए था।
2. **डेटा में gaps हैं:** SOL में 2024-10 और DOT में 2024-11 का पूरा महीना गायब है। Rolling ATR और SMA इन gaps के आर-पार जुड़ जाते हैं। Gap के दौरान खुला trade `continue` की वजह से "जम" जाता है (aggressive `:92`)।
3. **Exit reason का नाम भ्रामक है:** trailing stop से बंद हुए मुनाफे वाले trades भी "Stop Loss" लिखे जाते हैं। In-sample "Stop Loss" exits का औसत **+0.962R** है (`:107-110`)।
4. **Intrabar क्रम आशावादी है:** जिस दिन partial TP लगा, उसी दिन के high से SL ऊपर किया जाता है, पर उसी दिन का low नए SL से नहीं जाँचा जाता (`:113-130`)।
5. **Time exit हमेशा open price पर होता है**, भले उसी दिन पहले SL लग चुका हो। Time exit की जाँच SL से पहले होती है (`:100-103`)।
6. **Equity और DD सिर्फ बंद trades पर गिने जाते हैं।** Unrealized नुकसान नहीं गिना जाता (`:78,177-179`)।
7. **Daily log और print में फर्क:** daily log आखिरी दिन के exits से पहले लिखा जाता है ($229,749 बनाम $231,778.87)।
8. **Long को हमेशा प्राथमिकता:** एक ही दिन Long और Short दोनों signals हों तो Long चुना जाता है (`:200`)।
9. **Errors चुपचाप दब जाते हैं:** model load fail होने पर `Meta=0` हो जाता है (`:45-46`), और कई जगह bare `except:` है (`:196`, master `:264`)।
10. **Aggressive models की training का कोड `src/` में नहीं है।** Explorer फाइलें current folder में लिखता है, इसलिए `src` से पूरा सिस्टम reproduce नहीं होता।
11. **Standard pipeline में ATR = SMA(TR, 14)** है (`master:38`), जबकि 15m में EWM है। 1D का `Vol_Z_Score` return-std से बनता है, ATR से नहीं। Doc दोनों को एक जैसा बताता है।
12. **Features file में शुरुआती ~199 NaN rows रहती हैं** (`master:55`)। Backtest का 80% split इन्हें मिलाकर होता है जबकि training का बिना इनके, इसलिए OOS की शुरुआत थोड़ी अलग होती है।
13. **Purge/embargo नहीं है।** आखिरी training labels 60 या 90 दिन आगे तक देखते हैं, जो test अवधि में घुस जाते हैं।
14. **Coin-wise ranking (BNB सबसे ऊपर, ETH सबसे नीचे) in-sample पर आधारित है।** OOS में BNB का औसत +0.36R, ETH का −0.576R, BTC का +0.161R है। Win% IS से OOS तक: ETH 68.4 → 22.2, LTC 63.9 → 31.6। Top-5 coins चुनना selection bias है।
15. **Archive scripts `pd.read_csv('BTCUSDT_1d_ML_Features.csv')` जैसे cwd-relative paths इस्तेमाल करती हैं**, जो नए folder structure में नहीं चलेंगी।

---

## 5. 📄 PDFs में क्या है (pypdf से पढ़े गए)

- दोनों PDF (76-76 पेज) **Gemini chat के exports** हैं।
- `रिसर्च फ्रेमवर्क.pdf`: 5m पर V1–V11 (Bollinger, EMA, VWAP, RSI, sweep traps)।
- `V12 ब्रेनस्टॉर्मिंग 2.pdf`: 5m/15m पर V12–V24 (sessions, order blocks, ADX regime)।
- **1D ML system का इन PDFs में कोई हिस्सा नहीं है।** 1D का सारा काम बाद में repo scripts में हुआ।
- **एक अहम सबूत:** PDF के logs में `"Data Loaded: 114,043 Candles"` (ETH 15m) और `"342,128 Valid"` (5m) लिखा है।
  - 114,043 बिल्कुल वही संख्या है जहाँ timestamp bug डेटा काटता है (2024-12-31 23:45 तक)।
  - 5m का 342,128 भी 2021-10 → 2024-12 की अवधि (लगभग 3.25 साल) से मेल खाता है।
  - **यानी "5 साल" का डेटा शुरू से ही असल में ~3.25 साल का था।**
- PDF की strategies retail indicators पर हैं, जिन पर आपके अपने `AI_Quant_Master_Rules.md` में ban है। इसलिए वे `archive/legacy_engines/` में सही जगह पर हैं।

---

## 6. 🛠️ 1D के लिए क्या-क्या Update करना है (Priority क्रम में)

| # | काम | किस गलती से जुड़ा |
|---|---|---|
| 1 | Downloader में timestamp unit auto-detect करें (`ts > 1e14` हो तो microseconds)। 1D डेटा 2025-01 → 2026-09 तक दोबारा download करें। SOL 2024-10 और DOT 2024-11 भरें। Completeness check जोड़ें। | 4.1, 4.2 |
| 2 | **2025-01 → 2026-09 को locked holdout बनाएँ**। Research पूरा होने तक इसे बिल्कुल न छुएँ, और इस पर कोई grid search न करें। | D1, §1 |
| 3 | TP/SL/horizon/exit नियम `config.py` में एक जगह रखें। Labeler और executor दोनों वहीं से पढ़ें। Label horizon को execution से मिलाएँ: 7-दिन exit है तो label भी 7 दिन का हो। | D4 |
| 4 | Training और selection: purged walk-forward with embargo (≥ label horizon)। Grid search सिर्फ training खिड़कियों में करें। | D2, D6, 4.13 |
| 5 | Data बढ़ाएँ और model सरल रखें: coins को pool करके एक model बनाएँ (20 अलग models की जगह) और coin को feature बनाएँ। Depth 1–2, early stopping, Logistic Regression baseline से तुलना करें। | D2 |
| 6 | Features पर दोबारा काम करें। सिर्फ price-SMA दूरी (regime) पर निर्भरता हटाएँ। जो भी नया feature जोड़ें, उसे walk-forward AUC से साबित करें, नहीं तो छोड़ दें। | D2, D6 |
| 7 | Meta-labeling सही करें: primary की out-of-fold probabilities लें। Meta को सिर्फ primary-signal rows पर train करें, label = "primary सही था या नहीं"। | D2 |
| 8 | Probability calibration करें (isotonic/Platt, सिर्फ train खिड़की पर) और threshold को OOS-calibrated precision से तय करें। | D3 |
| 9 | Spot के लिए: long-only और Σ notional ≤ capital। Short चाहिए तो futures डेटा लें और funding fee व liquidation का model जोड़ें। | D5 |
| 10 | Backtest सुधारें: mark-to-market equity, slippage, intrabar का conservative क्रम, अलग "Trailing Stop" exit reason, और अंत में खुले trades बंद करके गिनें। | 4.3–4.7 |
| 11 | Aggressive training को `src/` में लाएँ और saved models के साथ उनकी training config भी save करें। | 4.10 |
| 12 | Docs सुधारें: $231k को "in-sample" लिखें। OOS नतीजे ($53.26, $96.33) और Max DD 77.97% साफ लिखें। | D1 |
| 13 | Paper trading तभी शुरू करें जब locked holdout पर (fee, slippage और spot sizing के साथ) नतीजा सकारात्मक हो। | — |

**पास होने की कसौटी (सुझाव):**
- Walk-forward के हर fold में OOS AUC लगातार 0.5 से ऊपर हो।
- Holdout पर fee और slippage के बाद expectancy > 0R हो।
- Max DD आपकी तय सीमा के अंदर हो।

कोई एक भी शर्त fail हो तो model को reject करें, जैसा आपका अपना Master Rule #3 कहता है।

---

## 7. सीमाएँ
- Walk-forward test में सिर्फ मौजूदा 7 features और 2 labels इस्तेमाल हुए। नए features पर कोई दावा नहीं किया गया।
- Scratchpad variants में सिर्फ entry की तारीख, short की अनुमति और notional cap बदले गए। बाकी logic मूल फाइल जैसा ही रखा गया (string replacement से, assertion के साथ)।
- 2025–2026 का डेटा उपलब्ध नहीं है (bug), इसलिए उस अवधि पर कोई नतीजा नहीं दिया गया।

*हर संख्या कोड, डिस्क पर मौजूद डेटा, saved models और चलाए गए commands से निकली है और दोबारा निकाली जा सकती है।*
