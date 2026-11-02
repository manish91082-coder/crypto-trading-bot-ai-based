# पूरा हिसाब: 24–27 अक्टूबर की सारी research + VM पर चल रहा ecosystem: क्या करना है, क्यों, फ़ायदा क्या (28 अक्टूबर 2026)

> **यह file क्या है:**
> - यह नई research नहीं है। 17 verified reports और VM की आज की ज़मीनी हालत को एक जगह जोड़ा गया है।
> - हर बात के साथ उसका source और नंबर दिया गया है।
> - कोई नया backtest, कोई fit या नई parameter choice नहीं की गई। कोई holdout नहीं खोला गया, और VM पर कुछ भी लिखा, बदला या deploy नहीं किया गया।
>
> **Discipline:**
> - Protocol यह report लिखने और VM snapshot लेने से **पहले** lock हुआ: `logs/consolidation_2026_10_28/CONSOL_PROTOCOL_PREREGISTERED.md`, SHA `c9f7432e…`, 2026-10-28 05:55 UTC।
> - सभी 29 source files के SHA `source_manifest.csv` में दर्ज हैं।
> - इस report का हर नंबर `claims.json` में अपने source की exact पंक्ति से जुड़ा है।
> - अलग verifier `src/audits/verify_consolidation.py` हर नंबर को source में दोबारा ढूँढता है। नतीजा §9 में है।
>
> मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research का सार है, निवेश सलाह नहीं।

---

## 0. एक नज़र में (सबसे ज़रूरी बातें)

1. **VM पर पूरा ecosystem ठीक चल रहा है** (आज 05:57 UTC का read-only snapshot):
   - पिछले 48 घंटों में किसी भी job का exit non-zero नहीं रहा;
   - installed crontab का SHA `13443469f4ec…` record से मेल खाता है;
   - ECO demo 74 cycles से चल रहा है, अब तक का max DD **1.775%**।
2. **पिछले 4 दिनों में हज़ारों नियम test हुए। BTC पर कोई भी "कब खरीदें / कब बेचें" वाला नियम fee के बाद नहीं टिका।** इनमें शामिल हैं:
   - 990 + 567 + 972 indicator / AI configs;
   - 9 महीने का oracle;
   - non-price (OI, order book, funding);
   - green candle, 1-second momentum, और turn detection।
3. **इसकी वजह गणित में है** (fee-hurdle map):
   - 1 घंटे पर profit के लिए **61.8%** बार सही दिशा चाहिए, जबकि 1 दिन पर **52.2%** और 7 दिन पर **50.7%** काफ़ी है;
   - 1 मिनट पर 100% सही दिशा भी घाटा देती है;
   - project में जो skill साबित हुई है (कई coins की 1–7 दिन की तुलना), वह ECO में पहले से live है।
4. **असली खुला सवाल नया indicator नहीं, ECO का पिछला साल (P3) है:**
   - ECO **−0.3%**;
   - N1 **−12.5%** (BTC से correlation 0.71);
   - 1D **+15.6%**।

   इसका फ़ैसला backtest से नहीं, पहले से lock forward gates से होगा: TC gate ~9 नवंबर और Sleeve A।
5. **अभी "जोड़ने" लायक चीज़ें सिर्फ़ safety/निगरानी वाली हैं, कोई नई trading नहीं।** पहला काम: DDX का पीला/लाल drawdown alarm (A1)। यह चेतावनी देता है, trade नहीं रोकता।
6. **इसी जाँच में दो नई ज़मीनी बातें मिलीं:**
   - **(a) Log-ship v7 का record अधूरा है।** v7 आपकी हाँ के बाद 25 अक्टूबर को deploy हुआ और ठीक चल रहा है। पर record में अब भी "Not deployed" लिखा है। यह मेरी चूक थी (§5.1)।
   - **(b) 1D का P3 "अनदेखा" नहीं था।** 1D (F7) के नियम 2021-01-01..2026-09-30 के data पर चुने गए थे (§5.2)।

---

## 1. Classes (protocol §6 में पहले से तय)

| Class | मतलब |
|---|---|
| **A** | करें, आपकी हाँ के बाद। सिर्फ़ safety, निगरानी या record का काम, जिससे कोई trading फ़ैसला नहीं बदलता |
| **W** | इंतज़ार। पहले से lock forward gate चल रहा है, उसकी तारीख पर पढ़ना है |
| **T** | नया pre-registered test, आपकी हाँ पर। तब तक उस पर कोई trade नहीं |
| **S** | रोकें / न जोड़ें। Data fee के बाद या random control के सामने इसके ख़िलाफ़ है |
| **U** | आपकी तरफ़ का फ़ैसला या काम |

**सख़्त नियम:** trading logic, capital या weights बदलने वाली कोई भी चीज़ सिर्फ़ backtest के आधार पर A नहीं हो सकती।

---

## 2. आज VM पर क्या चल रहा है (ज़मीनी snapshot, 2026-10-28 05:57 UTC)

Source: `logs/consolidation_2026_10_28/vm_snapshot.txt` (SHA `57242386…`)। यह सिर्फ़ पढ़ा गया, कुछ लिखा नहीं गया।

| हिस्सा | आज की स्थिति |
|---|---|
| VM | Uptime 11 दिन; disk 36% भरी; memory 3,288 MB खाली |
| Crontab | `crontab -l` SHA `13443469f4ec…` = `deploy/crontab.txt` |
| Cron jobs (48 घंटे) | 31 status files; हर job का non-zero exit **0**। F6_DemoOps 24 अक्टूबर से बंद है (cut-over पर retire, जैसा तय था) |
| **ECO demo** (Binance DEMO, हर घंटे) | 74 cycles। Eco equity 9,997 → **9,933.6** (अंदरूनी 10k scale पर), peak 10,062, max DD **1.775%**। Halted नहीं |
| ECO shadow | 74 cycles, max DD 1.78%। Demo के लगभग बराबर |
| **TC tracking** (demo बनाम shadow) | 2 पूरे दिन। Cumulative फ़र्क **−1.25** USDT eco (सीमा ±100), दोनों दिन रोज़ की सीमा के अंदर। Fills 11 और 14; slippage 2.6 और 1.2 bps। Rejected 0। Gate अभी नहीं (14 दिन चाहिए) |
| **Sleeve A forward** | F1 = **consistent** (23 closes, fidelity 2/2 PASS)। Verdict **pending**; पहले 3 eligible windows चाहिए |
| PaperN1 | 43 records, equity **9,764.7** (शुरुआत 10,000) |
| PaperSpotS1 (BTC > SMA200, 1,000 USDT) | 3 records, BTC में; equity **1,008.57** |
| **MK1** (maker बनाम market) | **39** orders, फ़ैसला 300 पर। अभी कोई नतीजा नहीं: W15 fill 84.6%, फ़र्क −1.47 bps, CI −8.2…+5.2 |
| FWD-WATCH | FW1 (ConnorsRSI 4h): **5** closed, फ़ैसला 80 पर। FW2 (NP3 ridge): **10** closed, फ़ैसला 200 पर |
| Liquidation collector | Process चल रहा है। 26 अक्टूबर 7,455 lines, 27 अक्टूबर **28,973** lines, MANIFEST में SHA के साथ |
| Log-ship | VM पर v7 code (`aca75629…`)। 25 अक्टूबर 13:36 UTC से **64** runs, non-zero 0 |
| Fees | `deploy/fees.json` VM = laptop (`b76c0495…`) |

---

## 3. पूरा action ledger

### 3A. करें, आपकी हाँ के बाद (safety / निगरानी / record; trading नहीं बदलती)

| ID | काम | क्यों (source और नंबर) | फ़ायदा | कैसे |
|---|---|---|---|---|
| **A1** | ECO alerts में **पीला/लाल drawdown alarm** | DDX (`RESEARCH_DRAWDOWN_DDX_27_OCT_2026.md` §2): 10,000 bootstrap रास्तों से live उम्र के हिसाब से सीमाएँ: ≤ 30 दिन 7.4% / 9.4%, ≤ 90 दिन 11.1% / 14.7%, ≤ 180 दिन 14.1% / 18.0%, ≤ 1 साल 17.5% / 22.1%। Kill switch 30% पर ही रहेगा | अगर live drawdown पुराने इतिहास के 95% / 99% दायरे से बाहर जाए, तो **kill switch से बहुत पहले** आपको पता चल जाएगा। अभी live DD 1.775% है, यानी सामान्य | `eco_alerts.py` में एक नया check, सिर्फ़ चेतावनी। पहले laptop test (synthetic ledger पर पीला/लाल/सामान्य), फिर verifier, फिर deploy। क्रम: amendment lock → code → test → deploy |
| **A2** | **Log-ship v7 deploy का record entry** लिखना | `logs/log_ship/CODE_CHANGES_AFTER_LOCK.md` की आख़िरी पंक्ति अब भी "Not deployed" कहती है। पर VM पर v7 code है (25 अक्टूबर 13:36:32 UTC), v6 का backup `backups/logship_v6_20261025/` में है, और 64 runs में non-zero 0। यह deploy 25 अक्टूबर को आपकी हाँ ("ये तीनों काम कर दो") के बाद हुआ था, और Drive verifier 4/4 PASS था | Record और ज़मीन फिर से मेल खाएँगे। आगे कोई इसे "deploy बाकी" समझकर दोबारा deploy नहीं करेगा | Laptop और VM, दोनों के CODE_CHANGES में entry 9 (append-only): समय, SHA, backup, verifier का नतीजा। Code में कोई बदलाव नहीं |
| **A3** | **Forward gates का कैलेंडर** हर हफ़्ते पढ़ना (§6) | TC gate, Sleeve A, MK1, FWD-WATCH, PaperSpotS1 और PaperN1, सबके अपने locked नियम हैं | कोई gate अपनी तारीख पर बिना पढ़े न छूटे | हर हफ़्ते एक read-only snapshot, जैसे आज का, और उसकी Hindi summary |

### 3W. इंतज़ार: पहले से lock forward gates (कोई नया काम नहीं)

| ID | Gate | नियम (पहले से lock) | आज | फ़ायदा / असर |
|---|---|---|---|---|
| **W1** | **TC tracking gate** (demo बनाम shadow) | 14 पूरे दिन (26 अक्टूबर से): कम से कम 12 दिन रोज़ का फ़र्क ≤ 0.30%, और कुल फ़र्क ≤ 1.0%। FAIL होने पर real money का कोई protocol नहीं | 2 / 14 दिन, कुल −1.25 USDT | पास होने पर साबित होगा कि demo execution plan जैसा ही चलता है। यही real money की पहली शर्त है (`RESEARCH_ECO_MONTHLY_OUTLOOK_25_OCT_2026.md` §3) |
| **W2** | **Sleeve A forward** (N1 का हिस्सा) | पहले 3 eligible windows (हर window 72 घंटे की, ≥ 20 closes) में से ≥ 2 "not consistent" निकलें, तो sleeve A को N1 से हटाने का amendment बनेगा | F1 consistent; अगले 2 eligible windows बाकी | P3 में N1 ने ECO की कमाई खाई (`RESEARCH_ROOT_CAUSE_25_OCT_2026.md`: N1 −12.5%)। यह gate बिना P3 को दोबारा snoop किए उस सवाल का ईमानदार हिस्सा जाँचता है |
| **W3** | **MK1 maker** | फ़ैसला ≥ 300 orders पर | 39 orders, CI 0 के दोनों तरफ़ | पास हुआ तो futures round trip 0.092% से घटकर ~0.056% होगा, और हर timeframe पर ज़रूरी accuracy घटेगी (fee-hurdle map: 1 दिन पर 52.2% की जगह 51.3%) |
| **W4** | **FWD-WATCH** FW1 / FW2 | FW1 का फ़ैसला 80 trades पर, FW2 का 200 पर | 5 और 10 closed | ये bench के "सबसे consistent" दिखे नियमों की साफ़ forward जाँच है। Edge नहीं माने जा रहे |
| **W5** | **PaperSpotS1** | Day 90 (2027-01-23) process gate। अकेले यह कभी real money authorise नहीं करेगा | Equity 1,008.57 | S1 का G2 सिर्फ़ 78.5% था, जबकि 90% चाहिए था (`RESEARCH_SPOT_SLEEVE_24_OCT_2026.md`)। Forward ही बताएगा |
| **W6** | **PaperN1 / F4 / 16B / Step16** forward logs | Day-90 reviews | सब रोज़ exit 0 | 1D और N1, दोनों हिस्सों का अलग-अलग forward रिकॉर्ड बन रहा है। P3 वाले सवाल का आगे का सबूत यही है |
| **W7** | **Liquidation collector** | सिर्फ़ data इकट्ठा करना | 7,455 + 28,973 lines | Binance liquidation का इतिहास public नहीं देता (`RESEARCH_NONPRICE_NP1_NP3_26_OCT_2026.md`)। आगे किसी non-price test के लिए यही अकेला source होगा |
| **W8** | **ECO demo के महीने बनाम P3 table** | सिर्फ़ तुलना | पहला पूरा महीना नवंबर | P3 का median महीना **9,985** (10k पर), सबसे बुरा 9,132, सबसे अच्छा 10,714, positive महीने 12 में 6। Demo का महीना इसी दायरे में होना चाहिए |

### 3U. आपकी तरफ़ के फ़ैसले / काम

| ID | फ़ैसला | क्यों | सुझाव |
|---|---|---|---|
| **U1** | A1 (alarm) और A2 (record) की हाँ | दोनों से trading नहीं बदलती | हाँ |
| **U2** | **लक्ष्य बदलना:** "रोज़ profit" की जगह "हर quarter positive, drawdown 15% से कम" | Root cause §4–5: ECO के पिछले साल सिर्फ़ 48% दिन positive थे। Directional trading में रोज़ profit गणित से मुमकिन नहीं | हाँ। यह मापने लायक लक्ष्य है |
| **U3** | **Real money कब** | Monthly outlook §6: TC gate पास होने के बाद भी कम से कम 2–3 महीने demo चलाना है। Execution gap का पुराना replay 1.2% पर FAIL था | TC gate + 2–3 महीने के demo महीनों की P3 table से तुलना, फिर छोटी रकम से एक नया protocol |
| **U4** | **Real account पर BNB** | Fees record: futures fee 10% → 0.018% / 0.036% तभी, जब BNB futures wallet में हो और fee burn on हो। Demo में BNB नहीं है, इसलिए वहाँ 0.040% कटता है | Real money के समय ही |
| **U5** | T-items में से क्या चलाना है (नीचे) | हर एक नया protocol माँगता है | मेरी प्राथमिकता §7 में |

### 3T. नए pre-registered tests (सिर्फ़ आपकी हाँ पर; तब तक कोई trade नहीं)

| ID | Test | Source और कारण | अपेक्षित फ़ायदा (ईमानदार) |
|---|---|---|---|
| **T1** | **ECO + cash-and-carry का मिश्रण** | Spot DCA report §5 और §9: carry अकेला CAGR ~4.6%, DD ~1%, ECO से correlation 0.12। "ECO + carry" pre-registered नहीं था, इसलिए उसका नंबर दिया ही नहीं गया | कम DD वाली स्थिर कमाई। पर carry घट रहा है: 2026 (सितंबर तक) +2.2% notional पर |
| **T2** | **Cash-and-carry का forward paper test** | वही report §9.2। Margin का खतरा: BTC 30 दिन में +133% | असली funding की forward पुष्टि। छोटा पर दिशा-मुक्त |
| **T3** | **"ECO बिना N1" या N1 का कम weight**, सिर्फ़ forward comparison rule के रूप में | Root cause §5.1 ने shadow सुझाया था। DDX: P3 देखकर weight बदलना snooping है। F4 (1D) और PaperN1 पहले से अलग-अलग forward रिकॉर्ड हो रहे हैं | पहले से लिखा तुलना-नियम: कब और किस सबूत पर weight बदलेगा। W2 के नतीजे के बाद ही सोचें |
| **T4** | **TURN: "4% turns ज़्यादा पूरे हुए"** को forward-watch बनाना | TURN §7a: सिर्फ़ HOLD में दिखा, DISC में नहीं। 4 महीने में ~40 turns | कई महीनों बाद हाँ या ना। कम उम्मीद |
| **T5** | Random BTC पर 1,000 combinations वाला demo | TURN §7b; आपका "हर permutation" वाला सवाल | सिर्फ़ समझाने के लिए: "best" combination का धोखा दिखेगा। Trading में कोई फ़ायदा नहीं |
| **T6** | Methods bench Batches 3–7 | Batch 2 §6: 1,539 configs, 0 edge। DSR सबसे ऊँचा 0.35, ज़रूरत 0.95 | **कम उम्मीद।** Fee-hurdle map के हिसाब से 15m–4h BTC rules से edge की संभावना कम है |
| **T7** | Oracle Part E (40 manual दिन) | Oracle A/B §7 | सिर्फ़ नई hypotheses; 10 दिनों वाले formula का हाल (§3S) देखते हुए कम उम्मीद |
| **T8** | Green candle का short (mirror) rule | Green candle §9: short side test नहीं हुई | कम उम्मीद। वही गणित: रंग अगला रंग नहीं बताता (P(G\|G) 45–49%) |
| **T9** | BTC/ETH पर averaging down + TP | Spot DCA §9.3 | कम उम्मीद। DCA का मूल गणित (छोटी जीत, असीमित हार) वही रहता है |

### 3S. रोकें / न जोड़ें (data इनके ख़िलाफ़ है)

| ID | क्या | सबूत (source) |
|---|---|---|
| **S1** | Spot DCA: averaging down, बिना stop loss | 10,000 → **2,617**, max DD **−89.9%**। 97% trades जीते, फिर भी account डूबा। Holdout में random से भी बुरा (2nd percentile) (`RESEARCH_SPOT_DCA_SPOT_FUTURES_24_OCT_2026.md`) |
| **S2** | "+30% उछाल के बाद short" | औसत **−13.1%** प्रति trade (वही report) |
| **S3** | Spot S6 "बड़ी गिरावट के बाद turn up पर खरीदो" और S5 top-5 momentum | S6 का CAGR +2.4% (random से नीचे); S5 holdout में −17.4% सालाना (`RESEARCH_SPOT_SLEEVE_24_OCT_2026.md`) |
| **S4** | BTC की अकेले timing (indicator और AI) | 990 configs, 10 finals में से 0 पास; AI t = −4.3 (`RESEARCH_BTC_DIRECTION_ENTRY_EXIT_25_OCT_2026.md`) |
| **S5** | 5m/15m scalping | Root cause §2: 5m पर ज़रूरी accuracy maker पर 60% और taker पर 71%; simple rules 47–49% देते हैं |
| **S6** | 10 दिनों से बना "level reaction" formula (H2′-c) | 10 दिन in-sample पर +8.2%। 272 नए दिनों पर पाँचों variants फ़ेल: V1-A −82.5%, V1-B −27.1% (`RESEARCH_MANUAL_10_DAYS_BTC_26_OCT_2026.md`, `RESEARCH_ORACLE_9M_2026_PART_A_B_26_OCT_2026.md`) |
| **S7** | Price-only दिन-के-नियम (direction, entry, exit) | 100 FUT configs का औसत gross **+0.002%**; lead config 2020–25 में 0/6 साल; "mirror edge" वापस लिया गया (`RESEARCH_ORACLE_9M_2026_PART_C_D_26_OCT_2026.md`) |
| **S8** | Non-price signals पर सीधा trading (OI, order book, taker, premium) | NP1: 18 में से 14 संकेत असली, पर IC 0.04–0.08 का असर fee से छोटा। NP2/NP3 0 पास; NP4 premium z holdout पर −0.123% (`RESEARCH_NONPRICE_NP1_NP3_26_OCT_2026.md`) |
| **S9** | Trend / oscillator / volatility / volume indicator rules (BTC 15m–4h) | Batch 1 0/567 (`RESEARCH_METHODS_BENCH_BATCH1_26_OCT_2026.md`); Batch 2 0/972, जिसका low-vol cluster नाज़ुक है (`RESEARCH_METHODS_BENCH_BATCH2_27_OCT_2026.md`) |
| **S10** | Red→green entry, green→red exit | 12 में से 0 पास; 5m–4h पर P(G\|G) 45–49% (`RESEARCH_GREEN_CANDLE_JAN_2026_27_OCT_2026.md`) |
| **S11** | 1–3 मिनट की चढ़ाई + volume / rhythm (1-second data) | 0 / 180। Rhythm का असर **+0.0019%**, fee से ~50 गुना छोटा (`RESEARCH_MICRO_MOMENTUM_1S_2026_27_OCT_2026.md`) |
| **S12** | 1 घंटे से छोटी अवधि पर नई direction research | 1 मिनट पर 100% सही दिशा भी घाटा; 1 घंटे पर 61.8% चाहिए (`RESEARCH_FEE_HURDLE_MAP_27_OCT_2026.md`) |
| **S13** | Turn को पुष्टि से पहले पकड़ना (BTC) | 1% turn की पुष्टि में 62 मिनट, तब तक 57% चाल निकल चुकी। 296 setups, 0 candidates; 6 असली features का AUC 0.53–0.55, fee से छोटा (`RESEARCH_TURN_DETECT_2026_27_OCT_2026.md`) |
| **S14** | "कब बाहर रहना है" वाले drawdown तरीके, BTC hedge, inverse-vol | DDX: 6 बार fail; जो काम करता है (कम exposure, long-short, stops, दो systems), वह पहले से live है |
| **S15** | Sunday / घंटे / calendar timing | 168 buckets में से dev में किसी का t > 2 नहीं; Sunday हर अवधि में negative (`RESEARCH_BTC_DIRECTION_ENTRY_EXIT_25_OCT_2026.md` §3.5) |

---

## 4. पहले से हो चुका (इन दिनों के सुझावों में से, ताकि कुछ दोहराया न जाए)

| काम | सबूत |
|---|---|
| Fee की एक ही table `deploy/fees.json` (BNB: spot 0.075%, futures maker 0.018%, taker 0.036%, + impact 0.01%) | `logs/fees/FEES_RECORD.md`; VM पर वही SHA |
| 1D/F4/16B recorders 0.25% से असली fee पर (root cause §5.2) | Fee amendment 2: VM deploy 2026-10-25 14:20 UTC, सारे verifiers PASS (`logs/fees/FEE_AMENDMENT_2_RESULTS.md`) |
| 1D का true-fee re-run | `logs/research_1d_true_fee/`: verifier दोबारा चलाया, 3/3 PASS। True fee पर 1D (M_AI3) का P3 0.1499 से 0.2377 (यानी +15.0% से +23.8%)। यह in-sample है (§5.2) |
| S1 का forward paper (spot sleeve §5.3) | PaperSpotS1 cron में, verifier रोज़ exit 0 |
| FWD-WATCH, liquidation collector, MK1 | 26 अक्टूबर को deploy; crontab `13443469f4ec…` |
| Log-ship v7 | 25 अक्टूबर को deploy; record entry बाकी (A2) |
| ECO demo cut-over, TC tracking | 25 अक्टूबर; आज 74 cycles |

---

## 5. इसी जाँच में मिली दो नई बातें (छिपाई नहीं)

### 5.1 Log-ship v7: record और ज़मीन अलग
- **Record कहता है:** v7 अभी deploy नहीं हुआ (`logs/log_ship/CODE_CHANGES_AFTER_LOCK.md` की आख़िरी पंक्ति, laptop और VM दोनों पर)।
- **ज़मीन कहती है:**
  - VM पर v7 की exactly 6 files 2026-10-25 13:36:32 UTC पर आईं: shipper, verifier, test, amendment, amendment SHA और CODE_CHANGES;
  - v6 का backup `backups/logship_v6_20261025/` में है;
  - उसके बाद 64 hourly runs में non-zero 0 रहा।
- **Session का record:** आपने 25 अक्टूबर 13:34 UTC पर "ये तीनों काम कर दो" कहा। 14:05 UTC पर v7 live था और Drive verifier 4/4 PASS था।
- **गलती:** deploy के बाद CODE_CHANGES में entry नहीं जोड़ी गई, और मेरी अपनी notes में भी "not deployed" रह गया। यह मेरी चूक है।
- **असर:** system पर कोई असर नहीं, सिर्फ़ record अधूरा है। सुधार A2 में है।

### 5.2 1D का पिछला साल (P3) unseen नहीं था
- Root cause report ने यह जाँच अगला ज़रूरी कदम बताई थी (§5.4)।
- F7 protocol में लिखा है: "Runs (MAIN 2021-01-01..2026-09-30 …)"। यानी 1D के long-short और stop नियम ऐसे data पर चुने गए जिसमें P3 भी शामिल था।
- **मतलब:**
  - 1D का P3 +15.6% (root cause) भी उतना भरोसेमंद नहीं जितना "unseen" होता;
  - true-fee re-run का +23.8% भी in-sample है;
  - इसलिए 1D का भी साफ़ सबूत अब सिर्फ़ forward data (F4 / ECO demo) है।
- **सीमा:** brains की monthly walk-forward training इस बात से अलग है। यहाँ सिर्फ़ नियम चुनने वाले data की बात है।

---

## 6. Forward कैलेंडर (क्या, कब पढ़ना है)

| कब | क्या | क्या देखना है |
|---|---|---|
| हर दिन (अपने-आप) | सारे cron jobs और verifiers | Alerts; non-zero exit |
| ~30 अक्टूबर और ~2 नवंबर (04:00 UTC पर windows बंद) | Sleeve A F2, F3 | Eligible (≥ 20 closes) हों तो consistent / not |
| **~9 नवंबर** (14वाँ पूरा दिन 8 नवंबर) | **TC gate** | ≥ 12/14 दिन ठीक और कुल फ़र्क ≤ 1% |
| लगभग 3 हफ़्ते (अनुमान: पिछले दो दिनों में 11 और 14 fills; 39 से 300 orders तक) | MK1 फ़ैसला | Maker सस्ता है या नहीं |
| नवंबर का अंत | Demo का पहला पूरा महीना | P3 table के दायरे में? (9,132 … 10,714) |
| 2027-01-23 | PaperSpotS1 day 90 | Process gate |
| कई महीने / एक साल से ज़्यादा (अनुमान: 26 दिनों में 5 और 10 trades) | FW1 (80), FW2 (200) | Forward नियम पास या fail |

---

## 7. मेरी सिफ़ारिश, क्रम में (data के आधार पर)

1. **A2 (record entry) और A1 (alarm):** आपकी हाँ पर, आज ही। दोनों छोटे और सुरक्षित हैं, और trading नहीं बदलते।
2. **U2:** लक्ष्य को "हर quarter positive, DD < 15%" मानना।
3. **कोई नई BTC timing research नहीं (S1–S15)।** चार दिनों के हज़ारों tests का साफ़ जवाब यही है।
4. **W1/W2 का इंतज़ार:** ~9 नवंबर तक system को बिना छेड़े चलने दें। यही सबसे कीमती सबूत है।
5. **अगर कोई नया test चाहिए,** तो सबसे तर्कसंगत T1/T2 (carry) है, क्योंकि वह दिशा पर निर्भर नहीं। पर उसकी कमाई घट रही है, इसलिए उम्मीद छोटी रखें।
6. **T4–T9 कम प्राथमिकता के हैं।** T5 सिर्फ़ समझाने के लिए है।

---

## 8. 17 reports की coverage (हर report से क्या निकला)

| # | Report | मुख्य नतीजा | Items |
|---|---|---|---|
| 1 | `RESEARCH_SPOT_DCA_SPOT_FUTURES_24_OCT_2026.md` | DCA डूबा; carry स्थिर पर घटता | S1, S2, T1, T2, T9 |
| 2 | `RESEARCH_SPOT_SLEEVE_24_OCT_2026.md` | S1 सबसे बचाव-लायक, पर साबित नहीं | W5, S3 |
| 3 | `RESEARCH_ECO_MONTHLY_OUTLOOK_25_OCT_2026.md` | P3 का median महीना ≈ 0 | W1, W8, U3 |
| 4 | `RESEARCH_ROOT_CAUSE_25_OCT_2026.md` | N1 P3 fail; fee गलती (ठीक हो चुकी) | W2, T3, U2, S5, §4, §5.2 |
| 5 | `RESEARCH_BTC_DIRECTION_ENTRY_EXIT_25_OCT_2026.md` | 990 configs, 0 | S4, S15 |
| 6 | `RESEARCH_METHODS_CATALOG_26_OCT_2026.md` | 139 दिशा-तरीकों की सूची, 7 batches | T6 |
| 7 | `RESEARCH_MANUAL_10_DAYS_BTC_26_OCT_2026.md` | Formula सिर्फ़ hypothesis | S6 |
| 8 | `RESEARCH_ORACLE_9M_2026_PART_A_B_26_OCT_2026.md` | Formula 272 दिनों पर फ़ेल | S6, T7 |
| 9 | `RESEARCH_ORACLE_9M_2026_PART_C_D_26_OCT_2026.md` | Gross ≈ 0; 0/6 साल | S7 |
| 10 | `RESEARCH_NONPRICE_NP1_NP3_26_OCT_2026.md` | संकेत असली, fee से छोटे | S8, W7 |
| 11 | `RESEARCH_METHODS_BENCH_BATCH1_26_OCT_2026.md` | 0/567 | S9, W4 |
| 12 | `RESEARCH_GREEN_CANDLE_JAN_2026_27_OCT_2026.md` | 0/12 | S10, T8 |
| 13 | `RESEARCH_MICRO_MOMENTUM_1S_2026_27_OCT_2026.md` | 0/180 | S11 |
| 14 | `RESEARCH_FEE_HURDLE_MAP_27_OCT_2026.md` | 1–7 दिन ही मैदान | S12, W3 |
| 15 | `RESEARCH_DRAWDOWN_DDX_27_OCT_2026.md` | Ledger + band + alarm | A1, S14 |
| 16 | `RESEARCH_METHODS_BENCH_BATCH2_27_OCT_2026.md` | 0/972 | S9, T6 |
| 17 | `RESEARCH_TURN_DETECT_2026_27_OCT_2026.md` | 0 candidates; 4% संकेत सिर्फ़ HOLD में | S13, T4, T5 |

**Studies के verifiers (सबके stored outputs में 0 FAIL):**
- spot DCA 7/7, spot sleeve 4/4;
- monthly outlook 9/9 (आज दोबारा चलाया);
- root cause 5/5, BTC entry 6/6;
- manual days: 258 claims, BAD 0;
- oracle A/B, C, D: ALL PASS;
- NP1, NP2, NP3, NP4: ALL PASS;
- Batch 1 7/7, Batch 2 8/8;
- green candle 109/109, micro 19/19, fee map 29/29;
- DDX 11/11;
- TURN 13/13 और 14/14।

---

## 9. इस report की अपनी जाँच

- `src/audits/verify_consolidation.py` → `logs/consolidation_2026_10_28/verify_output.txt`।
- **क्या जाँचा:**
  - source SHAs;
  - हर study verifier का 0-FAIL total;
  - हर claim की पंक्ति source में, और नंबर दोनों जगह मेल;
  - हर claim का value इस report में;
  - सभी 17 reports का नाम यहाँ;
  - हर item की एक class;
  - VM snapshot का SHA, crontab SHA, और 48 घंटे में non-zero exits 0।
- **नतीजा: 9 checks, 9 PASS, 0 FAIL।** 93 claims, 40 items (A 3, W 8, U 5, T 9, S 15)।
- **पहला run K2 पर FAIL हुआ था।** वजह verifier की अपनी गलती थी: छह studies "N PASS, 0 FAIL" लिखती हैं, और pattern सिर्फ़ "FAIL 0" पढ़ता था। Pattern ठीक किया गया; पहला output `verify_output_run1_regex_bug.txt` में रखा है (`CODE_NOTES.md` 3)।
- **Mutation test:** दो जानबूझकर गलत claims डालने पर verifier ने दोनों पकड़े (K3 और K4 FAIL, exit 1)। Output `mutation_test_output.txt` में है। फिर claims बहाल किए गए।
- Report का SHA `REPORT_SHA256.txt` में है।

## 10. सीमाएँ

- **ECO demo:** 74 cycles (3 दिन) कोई सबूत नहीं, सिर्फ़ यह कि system ठीक चल रहा है।
- **Bands और P3 table:** ये backtest पर बने हैं। Live cost और tracking उनमें शामिल नहीं हैं।
- **Classification:** यह मेरा है, पर protocol §6 के पहले से तय नियमों पर।
- **MK1 और FWD-WATCH की तारीखें:** ये सिर्फ़ मोटा अनुमान हैं, अब तक की दर पर।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये पिछले data और forward-जाँच के नतीजे हैं, भविष्य का वादा नहीं।
