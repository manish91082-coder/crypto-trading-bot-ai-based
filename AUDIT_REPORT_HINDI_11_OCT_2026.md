# 🔍 संपूर्ण प्रोजेक्ट ऑडिट रिपोर्ट — Zero-Trust AI Crypto Trading Bot

**ऑडिट तारीख:** 11 अक्टूबर 2026
**ऑडिट का तरीका:** हर `.py` फाइल लाइन-बाय-लाइन पढ़ी गई। Raw data, processed data, 120 models और logs पर असली Python चलाकर हर दावा चेक किया गया। Backtest scratchpad में दोबारा चलाया गया, इसलिए प्रोजेक्ट की कोई फाइल overwrite नहीं हुई।
**कोड में बदलाव:** शून्य। सिर्फ यह रिपोर्ट फाइल नई बनी है।
**Environment:** Python 3.12.3, pandas 3.0.5, xgboost 3.4.1, scikit-learn 1.9.0
**नोट:** यह तकनीकी ऑडिट है, निवेश सलाह नहीं। मैं licensed financial advisor नहीं हूँ।

---

## 0. एक लाइन में निष्कर्ष

> **अभी इस प्रोजेक्ट में ऐसा कोई सिस्टम नहीं है जो सच्चे Out-of-Sample (अनदेखे) डेटा पर profitable साबित हुआ हो।**
> "$120 → $231,778.87" वाला result मुख्य रूप से **in-sample (ट्रेनिंग डेटा पर ही टेस्ट)** का नतीजा है। जिस हिस्से को मॉडल ने कभी नहीं देखा था, उस पर इसी सिस्टम ने **−$227,408 का नुकसान** किया। उस दौरान **Max Drawdown 77.97%** रहा, जिसका डॉक्यूमेंट्स में कहीं ज़िक्र नहीं है।
> साथ ही **2025-01 से 2026-09 तक का पूरा डेटा (लगभग 35%) एक timestamp bug की वजह से चुपचाप डिलीट हो रहा है।**

---

## 1. प्रोजेक्ट असल में क्या कर रहा है (Verified Flow)

```
Binance Vision (spot monthly zip)
   └─ src/downloaders/download_all_timeframes.py → data/raw/{COIN}_{TF}_Raw_5Years.csv
        └─ 15m: ai_step1_features → ai_step2_labeling → ai_step3_train_model → ai_step4_meta_model → ai_step5_execution
        └─ 1d : ai_1d_master_pipeline.py (features+labels+train+backtest, standard models)
        └─ 1d : ai_final_aggressive_1d_system.py  ← "$231k" वाला सिस्टम
                (इसके models 'archive/research_archive/ai_1d_explorer.py' ने train किए थे, src में इनकी training का कोई कोड नहीं है)
```

**"AI Brain" असल में ऐसे काम करता है:**
1. **Features (7):** `Ret_1, Ret_3, Ret_5, Synthetic_Order_Flow, Vol_Z_Score, Dist_SMA_50, Dist_SMA_200`। ये सब सिर्फ पिछले डेटा से बनते हैं, यानी lookahead नहीं है ✅
2. **Label:** Triple-barrier। Entry अगली candle के open पर, TP/SL ATR के गुणक में। Timeout होने पर label = 0 (loss)।
3. **Primary model:** हर coin और हर direction (Long/Short) के लिए अलग XGBoost। कुल 10 coins × 2 = 20 models।
4. **"Meta-model":** एक और XGBoost जिसे 3 inputs मिलते हैं (`Primary_Confidence, Vol_Z_Score, Dist_SMA_200`) और जो **वही label** predict करता है।
5. **Execution:** meta-probability threshold (15m: 0.70, 1d std: 0.65, aggressive: 0.80) से ऊपर हो तो trade लिया जाता है। Risk 2% या 5%। Fee 0.075% हर तरफ।

कोड में ये चीज़ें **नहीं हैं**: कोई live trading, ccxt, Binance API, Telegram, cron, LSTM या fractional differentiation (grep से पुष्टि की गई)। यानी यह अभी पूरी तरह **सिर्फ backtest/research** प्रोजेक्ट है, "fully automated bot" नहीं।

---

## 2. ✅ क्या सही है (Verified)

| # | बात | सबूत |
|---|---|---|
| 1 | Features में lookahead नहीं है (pct_change, rolling, ewm सब पीछे देखते हैं) | कोड पढ़ा गया; `audit_step1.py` PASS |
| 2 | Entry T+1 open पर होती है और same-candle पर पहले SL माना जाता है (pessimistic) | `ai_step2_labeling.py:28,60-84` |
| 3 | Fee (0.075%/side) हर backtest में लगी है | तीनों execution फाइलें |
| 4 | Train/test split chronological है (shuffle नहीं) | `iloc[:split_idx]` |
| 5 | `config.py` relative paths ठीक काम करते हैं | सारी scripts root से चलीं |
| 6 | Logs reproducible हैं: aggressive backtest दोबारा चलाने पर **बिल्कुल वही** 550 trades, 54.55%, $231,778.87 आए | scratchpad re-run, PnL `np.allclose` = True |
| 7 | 15m का "FAILED" result ईमानदारी से माना गया है | `Step5_Trade_Log.csv`: 757 trades, 41.61%, $31.63 ✅ |
| 8 | चारों audit scripts सच में PASS होती हैं | चलाकर देखा गया |

---

## 3. 🔴 CRITICAL गलतियाँ (सबूत के साथ)

### C1. 2025 और 2026 का पूरा डेटा चुपचाप फेंका जा रहा है (Timestamp Bug)
- **कारण:** Binance Vision ने 2025-01-01 से spot kline timestamps **microseconds** में देने शुरू किए, जबकि `download_all_timeframes.py:55` उन्हें `unit='ms'` मानकर पढ़ता है। इससे साल **56971 से 58718** जैसे बन जाते हैं।
- **सबूत (BTCUSDT 15m):** कुल 175,291 rows में से **61,248 rows** का timestamp `56971-10-25 ...` जैसा है। `pd.to_datetime(errors='coerce')` इन्हें NaT बना देता है और `dropna` इन्हें हटा देता है।
- **असर:** सभी 10 coins का valid डेटा सिर्फ **2021-10-01 → 2024-12-31** तक है।
  - "5-Year" असल में **3.25 साल** है।
  - Aggressive trades **2022-04-19 → 2024-12-24** के बीच हुए (SMA-200 warm-up के कारण), यानी लगभग 2.7 साल।
  - "15m Tested Period 2025–2026" **गलत** है। असली OOS अवधि **2024-05-08 → 2024-12-31** है।
  - Master Rule #3 ("Train 2021–2024, Test 2025–2026") **कभी लागू हुआ ही नहीं**।
- **फिक्स:** downloader में unit auto-detect करें (`ts > 1e14` हो तो `'us'`, नहीं तो `'ms'`)। फिर 2025-01 के बाद का डेटा दोबारा download करें। मौजूदा CSV की गलत dates से असली dates आसानी से वापस नहीं मिलतीं, इसलिए re-download ही सुरक्षित रास्ता है।

### C2. "$231,778.87" मुख्य रूप से in-sample result है
- `ai_final_aggressive_1d_system.py` **पूरे** dataset पर चलता है (`:31`, कोई split नहीं)। पर इसके models (`models/1d_aggressive/`) डेटा के **पहले 80%** पर train हुए थे (`archive/.../ai_1d_explorer.py:78-93`)।
- हर coin के training की आखिरी तारीख: ज़्यादातर coins की **2024-04-04**, SOL की 2024-03-10, DOT की 2024-03-11।
- **Trade log को इन तारीखों से बाँटने पर:**

| हिस्सा | Trades | Win Rate | PnL |
|---|---|---|---|
| In-Sample (मॉडल ने यह डेटा देखा था) | 368 | **60.87%** | **+$486,158** |
| Out-of-Sample (अनदेखा डेटा) | 182 | **41.76%** | **−$227,408** |

- Capital का सफर: **2024-03-30 को peak $540,358** → **2024-09-14 को $125,597**। यह **77.97% Max Drawdown** है और ठीक OOS अवधि में आया। Script यह संख्या print करती है, पर README या Architecture doc में इसे नहीं लिखा गया।
- OOS में capital ~$413k से ~$230k पर आया, यानी अनदेखे डेटा पर लगभग **−44%**।

### C3. Models भारी Overfit हैं (AUC = 0.5 मतलब सिक्का उछालने जितना)
सभी 20 models (10 coins × Long/Short) का औसत, असली data और saved `.pkl` पर निकाला गया:

| Model set | Train AUC | OOS AUC | Meta>thr precision (Train → OOS) |
|---|---|---|---|
| 1d **aggressive** (thr 0.80) | **0.952** | **0.504** | **74.0% → 15.5%** |
| 1d standard (thr 0.65) | 0.897 | 0.588 | 82.6% → 46.1% |
| 15m (thr 0.70) | 0.578 | 0.526 | 70.8% → 40.9% |

- सिर्फ ~900 daily rows पर 100 trees (depth 3) train हुए हैं, इसलिए मॉडल ने डेटा याद कर लिया।
- OOS में "80% confidence" वाले signals असल में **सिर्फ 15.5%** सही निकले।

### C4. Models किसी और setup के लिए train हुए, trade किसी और setup पर होते हैं
- `*_1d_Temp_Labeled.csv` के labels **TP 8.0×ATR / SL 2.0×ATR / 90 दिन** से **100% match** करते हैं (4 combinations recompute करके जाँचा गया: 4/1.5 → 88.6%, 5/1.5 → 92.4%, 6/2 → 97.8%, **8/2 → 100%**)। Explorer का आखिरी loop iteration (8,2) ही फाइलें overwrite करके छोड़ गया।
- Aggressive system trade करता है: SL 1.5×ATR, 3×ATR पर 50% partial exit, 2×ATR trailing stop, 7-दिन time exit।
- Docs लिखते हैं: "TP 5.0x ATR, SL 1.5x ATR (1:3.33)"। यह **कोड और models दोनों से मेल नहीं खाता**।
- असली realized R: औसत win **+1.28R**, औसत loss **−0.66R**। 291 trades time-exit से बंद हुए और 259 stop-loss से।

### C5. Spot account में असंभव Leverage और Short
- Position size = risk ÷ SL distance निकाला जाता है, पर कुल exposure पर कोई सीमा नहीं है।
- **सबूत (aggressive log):** एक trade का notional capital का median **0.68×** और max **2.45×** है। एक साथ खुले trades का कुल notional **9.69× capital** तक पहुँचा (2023-01-09)। **988 में से 752 दिन** यह 1× से ऊपर रहा। सबसे बड़ी position **$362,165** की थी।
- 15m में एक trade का notional max **10.93×** capital तक गया।
- **129 Short trades** spot डेटा पर लिए गए हैं। Spot में short margin या futures के बिना संभव नहीं है, और futures में funding fee और liquidation का कोई model नहीं है।
- **नतीजा:** यह backtest किसी असली spot account में दोहराया नहीं जा सकता।

### C6. "Meta-Labeling" सही तरह implement नहीं है
- de Prado की meta-labeling में meta-model यह सीखता है कि primary का signal **सही निकला या नहीं**, और वह सिर्फ उन rows पर train होता है जहाँ primary ने signal दिया था।
- यहाँ meta-model (क) **सभी rows** पर, (ख) primary वाले **उसी label** पर, (ग) primary की **in-sample (ट्रेनिंग पर) probabilities** को feature बनाकर train होता है (`ai_step4_meta_model.py:41,54`, `ai_1d_master_pipeline.py:148`, `ai_1d_explorer.py:88`)। Training में primary की confidence बढ़ी हुई होती है, live में नहीं होगी।
- **सबूत:** 15m में OOS meta AUC **0.524** है, जो primary के 0.526 से भी कम है। यानी meta-model कुछ भी नया नहीं जोड़ रहा।

---

## 4. 🟠 HIGH गलतियाँ

### H1. सच्चे OOS नतीजे, जो docs में नहीं हैं
| सिस्टम | अवधि | नतीजा |
|---|---|---|
| 15m pipeline | 2024-05-09 → 2024-12-31 | $120 → **$31.63** |
| 1d standard (`backtest_1d()`, जिसे मैंने चलाया) | ~2024-04 → 2024-12 | $120 → **$118.79**, 146 trades, 41.10%, DD 32.79% |
| 1d aggressive (सिर्फ OOS हिस्सा) | 2024-03 → 2024-12 | **−$227,408**, win 41.76% |

### H2. Docs के गलत दावे (हर एक को कोड या डेटा से जाँचा गया)
| दावा (doc) | असलियत |
|---|---|
| 15m tested 2025–2026 | 2024-05-08 → 2024-12-31 |
| 1D "2021–2026 5-Year" | trades 2022-04-19 → 2024-12-24 |
| "Fee drag < $15 total" | सिर्फ entry fees ≈ **$26,966** (exit fee अलग) |
| 15m "$150+ fees" | ≈ **$130.91** |
| R:R 1:3.33 (TP 5x / SL 1.5x) | कोड में fixed TP है ही नहीं; models 8x/2x के लिए train हुए; realized 1.28R / −0.66R |
| "Fractional Diff — done" (roadmap) | कोड में कहीं नहीं है |
| "Dynamic slippage accounted" (README) | slippage बिल्कुल नहीं है |
| Meta-model = LSTM (Master Rules) | XGBoost है |
| Label −1 = time expiry | कोड में 0 है (loss के बराबर माना जाता है) |
| Sample-uniqueness weighting | implement नहीं है |
| Fee ccxt से live खींची जाएगी / `FEE_SLIPPAGE = 0.0015` हर कोड में (Mistakes Log) | दोनों नहीं हैं; hardcoded 0.00075 है |
| Risk 2% (Master Rules) | aggressive में 5% |
| "110 raw CSVs" | 1m के `.csv` और `.csv.gz` दोनों मिलाकर 120 files |
| Swing Blueprint में `backtest_stacked_sniper.py` | फाइल मौजूद नहीं है, और यह RSI/BB आधारित है, जिस पर खुद के rules में ban है |
| "100% Ground-Level Verified" | audits C1 से C6 में से एक भी पकड़ नहीं पाए (नीचे H8 देखें) |

### H3. "XRP/LTC/ETH हटाओ, Top-5 रखो" = selection bias
- यह ranking उसी backtest से निकली है जो ज़्यादातर in-sample है।
- **सबूत:** सिर्फ **Top 10 trades = कुल net profit का 135.7%** हैं, यानी बाकी 540 trades मिलकर नुकसान में हैं। Top trade अकेला BNB का +$77,188 है (2024-03-06)।
- पीछे देखकर coins चुनना future performance की कोई गारंटी नहीं है।

### H4. Downloader errors चुपचाप निगल जाता है, इसलिए डेटा में gaps हैं
- `download_all_timeframes.py:60-61` में `except Exception: pass` है और timeout 15 सेकंड का है।
- **सबूत:** SOLUSDT का **2024-10** (1d में 32 दिन का gap) और DOTUSDT का **2024-11** (31 दिन) पूरा महीना गायब है। BNB और DOGE के 2025 वाले हिस्से में भी कम rows हैं।
- असर: इन gaps के आर-पार ATR और SMA गलत बनते हैं। Aggressive में gap के दौरान खुला trade "जमा" रहता है (`if t not in prices_high: continue`)।

### H5. Drawdown और equity सिर्फ बंद हुए trades पर गिने जाते हैं
- खुले trades का unrealized नुकसान (mark-to-market) न daily capital log में है, न max DD में। असली DD **77.97% से भी ज़्यादा** हो सकता है।

### H6. Label और execution के नियम आपस में मेल नहीं खाते
- 15m label: 48 candles में TP नहीं लगा तो 0। Execution: कोई timeout नहीं, trade अनिश्चित समय तक खुला रहता है।
- 1d std label: 60 दिन। Execution: कोई timeout नहीं।
- Aggressive label: 90 दिन, TP 8x। Execution: 7 दिन।

### H7. Train और Test के बीच purge/embargo नहीं है
- Training की आखिरी rows के labels भविष्य के 48 candles / 60 / 90 दिन देखते हैं, जो test अवधि में घुस जाते हैं। इससे थोड़ा leakage होता है।

### H8. Audits कमज़ोर हैं, इसलिए ऊपर की गलतियाँ पकड़ में नहीं आईं
- हर audit सिर्फ **1 row** और ज़्यादातर सिर्फ 1-2 features चेक करता है (Order Flow, Ret_1)।
- `audit_step3.py:61-64`: label 0 हो या 1, दोनों हालत में "[PASS]" छपता है।
- `audit_pipeline.py:111`: "100% SECURE" हमेशा छपता है, कोई condition नहीं है।
- कोई audit यह नहीं जाँचता: data completeness या timestamps, aggressive system, IS/OOS split, leverage।
- कोई भी audit fail होने पर non-zero exit code नहीं देता।

---

## 5. 🟡 MEDIUM / छोटी-छोटी Corrections (फाइल:लाइन के साथ)

1. `ai_step5_execution.py:98`: `all_signals[SYMBOLS.index(sym)]`। अगर कोई coin load होने में fail हुआ तो index खिसक जाएगा और गलत coin का price इस्तेमाल होगा।
2. तीनों execution फाइलों में `sym_times = list(prices_open[sym].keys()); .index(t)` हर signal पर O(n) है, इसलिए 15m बहुत धीमा चलता है। एक बार पहले से `next_time` map बना लें।
3. `ai_final_aggressive_1d_system.py:45-46`: model load fail होने पर चुपचाप `Meta=0` हो जाता है और error नहीं छपता। `ai_1d_master_pipeline.py:264` और aggressive `:196` में bare `except:` है।
4. Aggressive `:113-130`: जिस candle में partial TP हुआ, उसी candle के `high` से trailing SL ऊपर कर दिया जाता है, पर उसी candle का `low` नए SL से नहीं जाँचा जाता। Intrabar क्रम optimistic है।
5. SL हमेशा exact SL price पर fill माना जाता है (gap या slippage नहीं)। 15m में PnL fixed `±R` से गिना जाता है, असली exit price से नहीं (`ai_step5_execution.py:123,128`)।
6. एक ही candle पर Long और Short दोनों threshold के ऊपर हों तो हमेशा Long चुना जाता है (`:183`)।
7. Backtest के अंत में खुले trades ignore हो जाते हैं, उनका PnL कहीं नहीं गिना जाता।
8. 15m और 1d के features अलग तरह बने हैं: ATR 15m में EWM और 1d में SMA से; `Vol_Z_Score` 15m में ATR-based और 1d में return-std-based। Docs दोनों को एक जैसा बताते हैं।
9. `ai_1d_master_pipeline.py:55` features में पहली ~199 NaN rows छोड़ देता है। Split अलग-अलग लंबाई के frames पर होता है (features पर 80% बनाम labeled पर 80%), इसलिए OOS की शुरुआत थोड़ी खिसक जाती है।
10. Daily capital log का आखिरी value **$229,749** है, जबकि print **$231,778.87** होता है, क्योंकि log आखिरी दिन के exits से पहले लिखा जाता है (`:78`)।
11. Aggressive models की training का कोड `src/` में नहीं है। वह सिर्फ archive explorer में है, जो फाइलें current folder (cwd) में लिखता है। इसलिए `src` से पूरा सिस्टम reproduce नहीं होता।
12. `requirements.txt` नहीं है, और versions pin नहीं हैं। README में `ccxt` install करने को कहा गया है पर कोड में इस्तेमाल नहीं होता।
13. `config.py:24` import होते ही folders बना देता है (side-effect)। यह छोटी बात है।
14. `ai_step5_execution.py:21`: `START_DATE = '2025-01-01'` define है पर कहीं इस्तेमाल नहीं होता। इससे भ्रम होता है।
15. `ai_step3_train_model.py`: `X_test` और `y_test` बनते हैं पर कोई OOS metric नहीं निकाला जाता।
16. Flowchart में "Confidence > 80%" और "Risk 5%" सिर्फ aggressive पर लागू होते हैं। 15m में 70% और 2% है।

---

## 6. 🛠️ सुधार का क्रम (Priority Roadmap)

हर कदम ऊपर के किसी सबूत से जुड़ा है।

1. **डेटा ठीक करें (C1, H4):** timestamp unit auto-detect करें। Failed months को log करें और retry करें। हर coin/TF के लिए "expected rows per month" वाला completeness check जोड़ें। फिर 2025-01 → 2026-09 का डेटा दोबारा download करें।
2. **सच्चा Holdout (C1, C2):** Master Rule #3 सच में लागू करें। 2021-10 → 2024-12 पर research और train करें, और **2025-01 → 2026-09 को बिल्कुल न छुएँ** जब तक final model तय न हो जाए।
3. **एक ही parameter source (C4, H6):** TP/SL/horizon को `config.py` में एक जगह रखें। Labeler और executor दोनों वहीं से पढ़ें। Aggressive training का कोड `src/` में लाएँ।
4. **Validation (C3, H7):** walk-forward या purged K-fold with embargo इस्तेमाल करें। हर model का OOS AUC और precision report करें। अगर OOS AUC ≈ 0.5 है तो model reject करें, जैसा आपके अपने नियम कहते हैं।
5. **Meta-labeling सही करें (C6):** primary की **out-of-fold** predictions इस्तेमाल करें। Meta को सिर्फ primary-signal rows पर train करें, label = "primary सही था या नहीं"।
6. **Portfolio सीमाएँ (C5):** spot के लिए Σ notional ≤ capital रखें और long-only चलाएँ। Short चाहिए तो futures डेटा लें और funding, fee, liquidation का model जोड़ें।
7. **Backtest realism (H5, M4, M5, M7):** mark-to-market equity और DD गिनें। Slippage जोड़ें। Intrabar पर conservative क्रम रखें। अंत में खुले trades बंद करके गिनें।
8. **Audits को सच्चे tests बनाएँ (H8):** `assert` या `pytest` इस्तेमाल करें, failure पर exit code ≠ 0 दें। Data completeness, IS/OOS split और leverage cap के tests जोड़ें।
9. **Docs सुधारें (H2):** README और Architecture doc से in-sample नंबर हटाएँ या साफ "in-sample" लिखें। Max DD 77.97% और OOS नतीजे साफ लिखें।
10. **इसके बाद ही** Paper trading (testnet) शुरू करें। मौजूदा models के साथ live या paper trading की सलाह **नहीं** दी जा सकती, क्योंकि OOS में कोई edge साबित नहीं हुई।

---

## 7. ऑडिट की सीमाएँ (ईमानदारी से)
- `docs/` के दोनों PDF (V12 Brainstorming, Research Framework) लाइन-बाय-लाइन ऑडिट नहीं किए गए (pypdf इंस्टॉल नहीं है)। बाकी सभी `.md` docs पढ़े गए।
- `archive/` में से `ai_1d_explorer.py` और `ai_1d_5year_backtest.py` विस्तार से पढ़े गए। बाकी archive scripts का सिर्फ structure देखा गया (वे `src` में इस्तेमाल नहीं होतीं)।
- 15m step5 को दोबारा नहीं चलाया गया (धीमा है)। उसका log विश्लेषण किया गया, और log के नंबर docs से मेल खाते हैं।

*यह रिपोर्ट कोड, डिस्क पर मौजूद डेटा, saved models और चलाए गए commands के आउटपुट पर आधारित है। हर संख्या दोबारा निकाली जा सकती है।*
