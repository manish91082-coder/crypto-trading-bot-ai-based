# हर timeframe पर कौन-सा formula कितना "बैठता" है: project की शुरुआत से आज तक की सारी R&D की ranking (28 अक्टूबर 2026)

> **यह file क्या है:**
> - Project की शुरुआत (13 अक्टूबर) से आज तक की सभी verified studies के नतीजे यहाँ timeframe के हिसाब से रखे गए हैं। Direction, entry, exit, coin-selection और risk को अलग-अलग rank किया गया है।
> - **कोई study दोबारा नहीं चलाई गई**, और कोई नया backtest या fit नहीं किया गया। सिर्फ़ stored result files पढ़कर उन्हें ठीक से सजाया और rank किया गया है।
>
> **Discipline:**
> - Protocol कोई भी नंबर निकालने से **पहले** lock हुआ: `logs/tf_atlas_2026_10_28/ATLAS_PROTOCOL_PREREGISTERED.md`, SHA `92683aad…`, 2026-10-28 06:50 UTC।
> - Study inventory (कौन-सी study शामिल, कौन-सी नहीं, और क्यों) भी उसी समय lock हुई।
> - Builder: `src/research/tf_atlas.py`। हर नंबर के साथ उसका source file और exact field दर्ज है।
> - Independent verifier `src/audits/verify_tf_atlas.py` ने हर नंबर अपनी files से दोबारा पढ़ा। Tier और rank भी उसने खुद दोबारा गिने। नतीजा §9 में है।
> - Build के दौरान मिली कमियाँ और उनके सुधार `CODE_NOTES.md` में दर्ज हैं (§9)।
>
> मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research का सार है, निवेश सलाह नहीं।

---

## 0. सीधा जवाब

1. **आपकी बात सही है कि हर timeframe का अपना गणित है।** Atlas ने यह नापकर दिखाया।
   - छोटे timeframe पर fee "दीवार" है। 1 मिनट पर 100% सही दिशा भी घाटा देती है।
   - Profit के लिए ज़रूरी सही दिशा: 5 मिनट पर 89.7%, 1 घंटे पर 61.8%, 4 घंटे पर 55.7%, 1 दिन पर 52.2%, और 1 हफ़्ते पर 50.7%।
2. **पूरी R&D में 4,044 नतीजे-rows बनीं** (59 studies, 97 source files)। एक भी row tier **E1** ("पूरी तरह साबित") तक नहीं पहुँची। Tiers:
   - E2 505;
   - E3 136;
   - E4 538;
   - E5 2,865।

   E1 के सबसे करीब 1h/4h के AI brains पहुँचे थे। पर उनका 2018–19 का अनदेखा दौर भारी घाटे का निकला (§5)।
3. **Timeframe के हिसाब से जहाँ सच में कुछ "बैठता" है (ईमानदार ranking):**

   | Timeframe | सबसे अच्छी चीज़ | कितना बैठता है | स्थिति |
   |---|---|---|---|
   | 1s–15m | कुछ नहीं | Indicator grids में fee से पहले की कमाई सिर्फ़ ~49% configs में positive (सिक्का = 50%) | बंद |
   | 1h | **Coin चुनना** (R24 brain) | AUC 0.565। 2021–26 में CAGR +68.7%, पर 2018–19 में -48.3% | Skill असली, पैसा सिर्फ़ bull दौर में |
   | 4h | **Coin चुनना** (R6), **N1 trend sleeves**, order-book/OI संकेत | R6 AUC 0.568। N1 2018–19 में +10.5%, पर पिछले साल (P3) Calmar -0.39। Non-price संकेत fee का ~56% | मिला-जुला |
   | 8h–12h | **RSI < 30 पर long** (oversold खरीदना) | Median trade positive: 12h बड़े coins पर +4.8%। Liquid alts पर पिछले साल भी positive (+0.2%) | Atlas की सबसे मज़बूत direction formula। N1 में पहले से live है (sleeve B) |
   | 1d | **Coin चुनना + long-short + stops** (F7 RS) | Calmar 2.16, DD 21%। 2018–19 में +2.6%, पिछले साल +15.0% | **Atlas का सबसे अच्छा-सबूत वाला system**। ECO में live है |
   | 3d–1M | कुछ साबित नहीं | Samples कम, grids सिक्के जैसे (45%) | खुला |

4. **एक बड़ी चेतावनी: "औसत" अक्सर झूठ बोलता है।**
   - उदाहरण: 1d पर EMA-crossover long का औसत trade +99.1% था।
   - पर उसका **median trade -6.5%** था, और पिछले साल (P3) -9.4%।
   - यानी कुछ बड़े bull trades ने औसत खींचा। आम trade घाटे का था। इसलिए हर table में median और "random से बेहतर?" वाला column भी दिया है।

---

## 1. "कितना बैठता है" कैसे नापा (protocol §5–§7)

| माप | मतलब | 100% का मतलब |
|---|---|---|
| **Fee-कवरेज** = gross ÷ fee | Fee से पहले की औसत कमाई, fee का कितना गुना है | 100% = बराबरी। 50% = आधी fee भी नहीं निकलती। Fee = `deploy/fees.json` futures taker 0.092% round trip |
| **सही %** बनाम **ज़रूरी %** | दिशा कितनी बार सही थी, और profit के लिए कितनी बार ज़रूरी थी | ज़रूरी % से ऊपर = profit |
| **"ज़रूरी बढ़त का कितना % मिला"** | (सही − 50%) ÷ (ज़रूरी − 50%) | 100% = ठीक बराबरी |
| **AUC** | Coin या turn पहचानने की skill (0.5 = सिक्का) | 0.55+ crypto में अच्छी skill मानी जाती है। पर पैसा अलग से जाँचना पड़ता है |

**Tiers (mechanical; verifier ने हर row पर दोबारा गिने):**

| Tier | मतलब |
|---|---|
| **E1** | Study PASS + अनदेखे data पर net > 0 और CI > 0 + random/control से बेहतर + हर अनदेखा दौर positive |
| **E2** | अनदेखे data (या बिना fit वाले grid) पर net > 0, पर कोई शर्त टूटी |
| **E3** | असर असली है (AUC/IC या random से बेहतर), पर fee के बाद पैसा नहीं |
| **E4** | सिर्फ़ चुनाव वाले data पर positive (hypothesis) |
| **E5** | कोई skill नहीं, या fee के बाद घाटा |

**ज़रूरी:**
- E2 ≠ साबित। Grids में E2 वाली rows अक्सर किस्मत होती हैं (§6)।
- "Modifier" rows (stops, hedge, sizing, regime gate वगैरह) में "OOS नतीजा" का मतलब उनके base system के मुकाबले Calmar का बदलाव है। यह `CODE_NOTES` note 3 में दर्ज है।

---

## 2. Timeframe की "physics": गणित क्या इजाज़त देता है (fee map, root cause, green candle, TURN, swing anatomy)

| Timeframe | BTC की औसत चाल | ज़रूरी सही दिशा (taker) | ज़रूरी सही दिशा (maker) | random entry net (10 coins, taker) | अगली candle भी green? (Jan 2026) | variance ratio (1 = random, < 1 = पलटता, > 1 = चलता रहता) | पुष्ट swing follow करने पर औसत (ATR, fee से पहले): rally / decline |
|---|---|---|---|---|---|---|---|
| 1s-1m | 0.041% | 163.4% | 119.0% | — | — | sec q=20: 1.33 | — / — |
| 5m | 0.116% | 89.7% | 74.2% | -0.080% | 48.9% | 0.94 | +0.03 / +0.00 |
| 15m | 0.198% | 73.2% | 64.1% | -0.080% | 46.0% | 0.95 | +0.10 / +0.05 |
| 30m | 0.276% | 66.7% | 60.1% | — | 47.3% | 0.89 | +0.18 / +0.08 |
| 1h | 0.391% | 61.8% | 57.2% | -0.078% | 47.1% | 0.84 | +0.29 / +0.11 |
| 4h | 0.805% | 55.7% | 53.5% | -0.085% | 45.2% | 0.80 | +0.69 / +0.16 |
| 8h | — | — | — | — | — | 0.80 | +1.05 / +0.18 |
| 12h | — | — | — | — | — | — | +1.34 / +0.17 |
| 1d | 2.117% | 52.2% | 51.3% | -0.091% | 73.3% | 1.04 | +1.81 / +0.04 |
| 3d | 3.855% | 51.2% | 50.7% | — | — | — | — / — |
| 1w | 6.177% | 50.7% | 50.5% | — | — | — | +3.15 / -1.14 |
| 1M | 13.463% | 50.3% | 50.2% | — | — | — | +5.08 / -3.55 |

**इस table को कैसे पढ़ें:**
- **"ज़रूरी सही दिशा" 100% से ऊपर** (1 मिनट और उससे छोटे) = 100% सही दिशा पर भी fee के बाद घाटा।
- **Variance ratio:**
  - seconds पर 1 से ऊपर (1.33): भाव कुछ सेकंड एक दिशा में चलता रहता है;
  - 5 मिनट से 8 घंटे पर 1 से नीचे (0.80–0.95): हल्का उलटना (reversal)।
  - दोनों असर fee से छोटे हैं।
- **1d पर "अगली candle भी green" का ऊँचा आँकड़ा** सिर्फ़ जनवरी 2026 के 31 दिनों का है। Green-candle study में यह दूसरे सालों में नहीं टिका।
- **पुष्ट swing follow करना:** rally पकड़ने का औसत 4h से ऊपर बढ़ता है (1d पर +1.81 ATR, fee से पहले)। Decline follow करने का औसत लगभग 0 है।

---

## 3. हर timeframe का "formula card": Direction / Entry / Exit

| Timeframe | दिशा (Direction) | Entry | Exit / Risk / Selection | फ़ैसला |
|---|---|---|---|---|
| **1s–1m** | Seconds में momentum असली है (20 सेकंड पर variance ratio 1.33), पर औसत चाल 0.041% fee से छोटी है। ज़रूरी सही दिशा 163.4%, यानी असंभव। सबसे अच्छा नियम: 1m Bollinger fade, fee-कवरेज 24% | लागू नहीं | लागू नहीं | **बंद** |
| **5m** | ज़रूरी 89.7%। Simple momentum / reversal सही: 47.2% / 48.9%। Double bottom के बाद higher high 55.7%, जबकि आधार 46.9% है: असली, पर सिर्फ़ descriptive, पैसे का test नहीं | Swing support पर bounce 46.7%, control 48.4%, यानी control से कम। Probe/scale-in सब घाटे में | — | **कोई formula नहीं** |
| **15m** | ज़रूरी 73.2%। Bench grid में gross > 0 सिर्फ़ 49% (सिक्का)। 10 दिनों वाला hand formula 272 नए दिनों पर fee-कवरेज -52% | S/R bounce control से कम | — | **कोई formula नहीं** |
| **30m** | ज़रूरी 66.7%। कुछ साबित नहीं | — | — | **कोई formula नहीं** |
| **1h** | ज़रूरी 61.8%। Order flow / OI / order book संकेत असली हैं (NP1), पर grid का median fee-कवरेज 8% | — | Exit brain AUC 0.672: यह volatility पहचानता है, दिशा नहीं। पैसे में FAIL। **Selection:** R24 AUC 0.565, पर long-only 2018–19 में -48.3% | **Selection में skill है, timing में नहीं** |
| **4h** | ज़रूरी 55.7%। N1 trend sleeves: 2018–19 में +10.5%, पर पिछले साल Calmar -0.39। Non-price composites: 90% configs gross-positive, median fee-कवरेज 56% | Maker / limit entry का फ़ायदा छोटा है (N3 X1 FAIL: adverse selection)। Swing-rally AI AUC 0.546 | A4 exit tuning noise है (PBO 0.84)। Profit lock (ECO-T4) FAIL। **Selection:** R6 AUC 0.568, long-only 2018–19 में -50.8% | **मिला-जुला।** Trend हिस्से का फ़ैसला forward जाँच (Sleeve A) से |
| **8h / 12h** | **RSI < 30 long**: बड़े coins पर median trade 8h +3.4%, 12h +4.8%। Liquid alts पर पिछले साल भी positive: 8h +0.8%, 12h +0.2%। Trend (EMA / Donchian) long का औसत ऊँचा है, पर median negative (8h EMA -3.6%), यानी कुछ बड़े trades पर टिका | Swing-rally AI 8h AUC 0.550 | — | **सबसे मज़बूत direction formula।** N1 sleeve B में live |
| **1d** | ज़रूरी 52.2%। RSI long median +9.4%, पर पिछले साल -5.7%। Double top के बाद lower low 63.8%, आधार 45.0% (n 58)। Spot S1 (BTC > SMA200) का Sharpe hold से सिर्फ़ +0.01 ज़्यादा। DCA बिना stop: holdout -46.5% | Perp पर long (E11) Calmar बढ़ाता है | **F7 RS:** Calmar 2.16, 2018–19 में +2.6%, पिछले साल +15.0%। Stops से ΔCalmar +0.45। Vol sizing -0.05 (FAIL)। "कब बाहर रहना है" वाले brains fail (market brain AUC निचली सीमा 0.494) | **Project का सबसे मज़बूत timeframe।** ECO में live |
| **3d / 1w / 1M** | ज़रूरी 51.2% / 50.7% / 50.3%। BTC-entry grid में gross > 0: 49% / 45%। Weekly trend long का औसत कुछ बड़े trades पर टिका | — | — | **गणित आसान है, पर सबूत कम** |
| **Event bars / दिन के अंदर turns** | Renko / volume bars grid में gross > 0: 41%। 1% turn की पुष्टि तक 57% चाल निकल चुकी होती है (62 मिनट) | Early-turn features: AUC ≤ 0.553 | — | **बंद** |

---

## 4. हर timeframe की पूरी ranking (ऊपर की rows; पूरी सूची `atlas_ranked.csv` में)

हर table अपने अंदर rank है: tier पहले, फिर fee-कवरेज / AUC / सही % / Calmar। अलग तरह के मापों को आपस में नहीं मिलाया गया।

**Columns:**
- **"उसी grid में gross > 0":** उस study के उस timeframe के सारे configs में से कितनों का fee से पहले का औसत positive था। ~50% = सिक्का, यानी grid में दिशा की जानकारी नहीं।
- **"आगे की जाँच":** P3 (पिछला साल) या 2018–19 जैसे अनदेखे दौर।


### 1s-1m — 1 सेकंड – 1 मिनट

कुल rows: 219; tiers: E1 0, E2 0, E3 2, E4 1, E5 216


**दिशा (Direction)**


*trade नियम*: 219 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E3 | T3 P11_BollFade | turn_detect_2026 |  BTC | 5,003 | 24% | -0.070% | — | — | हाँ | — | — |
| 2 | E3 | TFX RSI | research_tf_edge_map | long 10 big coins | 93,498 | 19% | -0.090% | +0.110% | — | हाँ | — | — |
| 3 | E4 | T3 P7_CUSUMh8 | turn_detect_2026 |  BTC | 185 | 269% | +0.155% | — | — | नहीं | — | — |
| 4 | E5 | T3 P7_CUSUMh4 | turn_detect_2026 |  BTC | 1,067 | 6% | -0.086% | — | — | नहीं | — | — |
| 5 | E5 | micro N1_k1.5_s0_XT600 | micro_momentum_2026 | long BTC | 9,155 | 4% | -0.088% | — | — | — | — | 35% of 180 |

### 5m — 5 मिनट

कुल rows: 124; tiers: E1 0, E2 9, E3 8, E4 11, E5 96


**दिशा (Direction)**


*trade नियम*: 109 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | F6_rsi_fade_5m_20 V3 | research_btc_entry |  BTC | 70 | 735% | +0.585% | — | — | — | — | 46% of 48 |
| 2 | E2 | F6_rsi_fade_5m_30 V3 | research_btc_entry |  BTC | 76 | 336% | +0.217% | — | — | — | — | 46% of 48 |
| 3 | E2 | F6_rsi_fade_5m_20 V2 | research_btc_entry |  BTC | 96 | 256% | +0.144% | — | — | — | — | 46% of 48 |
| 4 | E2 | F6_rsi_fade_5m_20 A4_4 | research_btc_entry |  BTC | 132 | 204% | +0.095% | — | — | — | — | 46% of 48 |
| 5 | E2 | F6_rsi_follow_5m_20 A2_1 | research_btc_entry |  BTC | 320 | 194% | +0.086% | — | — | — | — | 46% of 48 |

*सही दिशा %*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | double_bottom -> HH | research_ladder_sessions | 55.7% | 46.9% | — | 25,009 | हाँ |
| 2 | E3 | double_top -> LL | research_ladder_sessions | 55.5% | 47.2% | — | 27,958 | हाँ |
| 3 | E5 | simple REV (10 coins) | research_root_cause | 48.9% | 70.8% | -5% | 5,648,886 | — |
| 4 | E5 | simple MOM (10 coins) | research_root_cause | 47.2% | 70.8% | -14% | 5,648,886 | — |

**Entry**


*trade नियम*: 7 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E5 | ladder probe/scale-in V3 | research_probe_scalein | long 10 coins | 35,779 | 20% (R) | -0.07 R | — | -0.09 R | — | — | — |
| 2 | E5 | ladder probe/scale-in V1 | research_probe_scalein | long 10 coins | 51,219 | 14% (R) | -0.08 R | — | -0.11 R | — | — | — |
| 3 | E5 | ladder probe/scale-in V2 | research_probe_scalein | long 10 coins | 51,219 | 14% (R) | -0.07 R | — | -0.10 R | — | — | — |
| 4 | E5 | ladder probe/scale-in V1 | research_probe_scalein | short 10 coins | 51,564 | 11% (R) | -0.09 R | — | -0.10 R | — | — | — |
| 5 | E5 | ladder probe/scale-in V3 | research_probe_scalein | short 10 coins | 36,892 | 11% (R) | -0.08 R | — | -0.09 R | — | — | — |

*सही दिशा %*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E5 | buy/sell at swing resistance (bounce) | research_sr_levels | 47.6% | 48.5% | — | 711,839 | नहीं |
| 2 | E5 | buy/sell at swing both (bounce) | research_sr_levels | 47.2% | 48.4% | — | 1,415,790 | नहीं |
| 3 | E5 | buy/sell at swing support (bounce) | research_sr_levels | 46.7% | 48.4% | — | 703,951 | नहीं |

*विवरण*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E3 | Fibonacci retracement levels | research_ladder_sessions | share of turns at fib levels minus control |

### 15m — 15 मिनट

कुल rows: 586; tiers: E1 0, E2 64, E3 30, E4 77, E5 415


**दिशा (Direction)**


*trade नियम*: 570 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | batch2 A3.03b_GarmanKlass20_LOW_fade_15m X1 | research_methods_bench |  BTC | 112 | 948% | +0.781% | — | +0.8%, +0.8% | हाँ | नहीं | 49% of 504 |
| 2 | E2 | batch2 A3.03a_Parkinson20_LOW_fade_15m X1 | research_methods_bench |  BTC | 114 | 899% | +0.735% | — | +0.3%, +1.2% | हाँ | नहीं | 49% of 504 |
| 3 | E2 | batch2 A3.03d_YangZhang20_HIGH_follow_15m X1 | research_methods_bench |  BTC | 168 | 706% | +0.557% | — | -0.0%, +1.4% | हाँ | नहीं | 49% of 504 |
| 4 | E2 | batch2 A4.09b_Amihud20_HIGH_fade_15m X1 | research_methods_bench |  BTC | 137 | 654% | +0.510% | — | +0.7%, +0.3% | हाँ | नहीं | 49% of 504 |
| 5 | E2 | batch2 A3.03d_YangZhang20_LOW_fade_15m X1 | research_methods_bench |  BTC | 114 | 605% | +0.465% | — | +0.5%, +0.4% | नहीं | नहीं | 49% of 504 |

*सही दिशा %*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | double_bottom -> HH | research_ladder_sessions | 56.0% | 47.1% | — | 7,480 | हाँ |
| 2 | E3 | double_top -> LL | research_ladder_sessions | 55.1% | 46.8% | — | 8,589 | हाँ |
| 3 | E5 | simple REV (10 coins) | research_root_cause | 50.5% | 62.0% | 4% | 1,924,752 | — |
| 4 | E5 | simple MOM (10 coins) | research_root_cause | 47.3% | 62.0% | -22% | 1,924,752 | — |

*विवरण*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | 10-day hand analysis -> formula H2'-c (in-sample hypothesis) | manual_day_study | no machine table of the in-sample trades; the formula's OOS test = oracle_9m_2026 'H2'-c' rows |

**Entry**


*trade नियम*: 7 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E5 | ladder probe/scale-in V3 | research_probe_scalein | long 10 coins | 11,143 | 48% (R) | -0.02 R | — | -0.01 R | — | — | — |
| 2 | E5 | ladder probe/scale-in V2 | research_probe_scalein | long 10 coins | 15,865 | 45% (R) | -0.02 R | — | -0.01 R | — | — | — |
| 3 | E5 | ladder probe/scale-in V1 | research_probe_scalein | long 10 coins | 15,865 | 39% (R) | -0.03 R | — | -0.02 R | — | — | — |
| 4 | E5 | ladder probe/scale-in V1 | research_probe_scalein | short 10 coins | 16,091 | 26% (R) | -0.04 R | — | -0.05 R | — | — | — |
| 5 | E5 | ladder probe/scale-in V3 | research_probe_scalein | short 10 coins | 11,574 | 22% (R) | -0.04 R | — | -0.04 R | — | — | — |

*सही दिशा %*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E5 | buy/sell at swing resistance (bounce) | research_sr_levels | 45.9% | 48.3% | — | 218,354 | नहीं |
| 2 | E5 | buy/sell at swing both (bounce) | research_sr_levels | 45.3% | 48.2% | — | 434,802 | नहीं |
| 3 | E5 | buy/sell at swing support (bounce) | research_sr_levels | 44.6% | 48.1% | — | 216,448 | नहीं |

*विवरण*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E3 | Fibonacci retracement levels | research_ladder_sessions | share of turns at fib levels minus control |

### 30m — 30 मिनट

कुल rows: 69; tiers: E1 0, E2 4, E3 5, E4 5, E5 55


**दिशा (Direction)**


*trade नियम*: 65 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | F12_ai_V2_m0.05 V2 | research_btc_entry |  BTC | 76 | 611% | +0.470% | — | — | — | — | 50% of 6 |
| 2 | E2 | F12_ai_V2_m0.02 V2 | research_btc_entry |  BTC | 84 | 511% | +0.379% | — | — | — | — | 50% of 6 |
| 3 | E2 | TFX EMAX | research_tf_edge_map | long 10 big coins | 9,595 | 474% | +0.276% | -0.833% | -0.3% | नहीं | — | — |
| 4 | E2 | F12_ai_V2_m0.0 V2 | research_btc_entry |  BTC | 87 | 171% | +0.065% | — | — | — | — | 50% of 6 |
| 5 | E3 | TFX BB | research_tf_edge_map | short liquid alts | 58,455 | 69% | -0.038% | +0.721% | -0.1% | हाँ | — | — |

**Entry**


*trade नियम*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E5 | support-bounce trade EV | research_sr_levels |  10 coins | — | -91% | -0.284% | — | — | — | — | — |

*सही दिशा %*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E5 | buy/sell at swing resistance (bounce) | research_sr_levels | 44.9% | 47.9% | — | 104,806 | नहीं |
| 2 | E5 | buy/sell at swing both (bounce) | research_sr_levels | 44.3% | 47.9% | — | 210,272 | नहीं |
| 3 | E5 | buy/sell at swing support (bounce) | research_sr_levels | 43.7% | 47.8% | — | 105,466 | नहीं |

### 1h — 1 घंटा

कुल rows: 870; tiers: E1 0, E2 119, E3 29, E4 127, E5 595


**दिशा (Direction)**


*trade नियम*: 802 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | TFX EMAX | research_tf_edge_map | long 10 big coins | 4,596 | 1244% | +0.910% | -1.141% | -0.5% | नहीं | — | — |
| 2 | E2 | F6_rsi_fade_1h_20 V2 | research_btc_entry |  BTC | 37 | 1013% | +0.840% | — | — | — | — | 47% of 216 |
| 3 | E2 | F2_mom_1h_k1 V3 | research_btc_entry |  BTC | 79 | 989% | +0.818% | — | — | — | — | 47% of 216 |
| 4 | E2 | F3_rev_1h_k2 V3 | research_btc_entry |  BTC | 72 | 910% | +0.745% | — | — | — | — | 47% of 216 |
| 5 | E2 | batch1 A1.14b_KST_1h X1 | research_methods_bench |  BTC | 178 | 604% | +0.464% | — | +0.1%, +1.0% | हाँ | नहीं | 52% of 504 |

*सही दिशा %*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | double_top -> LL | research_ladder_sessions | 54.4% | 45.5% | — | 1,929 | हाँ |
| 2 | E3 | double_bottom -> HH | research_ladder_sessions | 53.7% | 47.3% | — | 1,793 | हाँ |
| 3 | E5 | simple REV (10 coins) | research_root_cause | 52.1% | 56.1% | 35% | 486,684 | — |
| 4 | E5 | simple MOM (10 coins) | research_root_cause | 46.7% | 56.1% | -54% | 486,684 | — |

*skill (AUC / IC)*: 12 rows; ऊपर के 4:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | NP1 IC OI_CHG_1H | research_nonprice | — | — | हाँ | — |
| 2 | E3 | NP1 IC OI_CHG_24H | research_nonprice | — | — | हाँ | — |
| 3 | E3 | NP1 IC FUT_TAKER_1H | research_nonprice | — | — | हाँ | — |
| 4 | E3 | NP1 IC SPOT_TAKER_1H | research_nonprice | — | — | हाँ | — |

*विवरण*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | forward return after support break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |
| 2 | E5 | forward return after resistance break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |

**Entry**


*trade नियम*: 31 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E4 | ladder probe/scale-in V2 | research_probe_scalein | long 10 coins | 4,018 | 222% (R) | +0.03 R | — | -0.03 R | — | — | — |
| 2 | E4 | ladder probe/scale-in V3 | research_probe_scalein | long 10 coins | 2,889 | 215% (R) | +0.03 R | — | -0.05 R | — | — | — |
| 3 | E4 | ladder probe/scale-in V1 | research_probe_scalein | long 10 coins | 4,018 | 204% (R) | +0.03 R | — | -0.05 R | — | — | — |
| 4 | E4 | ladder probe/scale-in V3 | research_probe_scalein | short 10 coins | 2,833 | 113% (R) | +0.00 R | — | -0.02 R | — | — | — |
| 5 | E4 | ladder probe/scale-in V1 | research_probe_scalein | short 10 coins | 3,929 | 110% (R) | +0.00 R | — | -0.02 R | — | — | — |

*सही दिशा %*: 6 rows; ऊपर के 4:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | S/R touch (resistance) -> becomes a swing turn | research_swing_vs_sr | 8.2% | 4.7% | — | 52,041 | हाँ |
| 2 | E3 | S/R touch (both) -> becomes a swing turn | research_swing_vs_sr | 8.0% | 4.9% | — | 104,320 | हाँ |
| 3 | E3 | S/R touch (support) -> becomes a swing turn | research_swing_vs_sr | 7.8% | 5.1% | — | 52,279 | हाँ |
| 4 | E5 | buy/sell at swing resistance (bounce) | research_sr_levels | 44.0% | 47.3% | — | 51,234 | नहीं |

*विवरण*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E3 | Fibonacci retracement levels | research_ladder_sessions | share of turns at fib levels minus control |
| 2 | E5 | high- vs low-volume level (support): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 3 | E5 | high- vs low-volume level (resistance): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 4 | E5 | high- vs low-volume level (both): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |

**Exit**


*skill (AUC / IC)*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | exit brain P(fall>5% in 24h) | strategy_1d_step26_exit | 0.672 | 0.644 | हाँ | — |

**Coin चुनना (Selection)**


*skill (AUC / IC)*: 6 rows; ऊपर के 4:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | R24 + S/R + volume features (skill) | strategy_1d_step29_srv | 0.566 | 0.560 | हाँ | — |
| 2 | E3 | R24 + 15m/5m features (skill) | strategy_1d_step25_hf | 0.566 | 0.560 | हाँ | — |
| 3 | E3 | R24 1h relative brain (skill) | strategy_1d_step24_1h | 0.565 | 0.558 | हाँ | हाँ |
| 4 | E3 | R4 4-hour-horizon brain (skill) | strategy_1d_step24_1h | 0.545 | 0.541 | हाँ | — |

*portfolio*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | R24 1h portfolio | strategy_1d_step24_1h | 68.7% | +0.92 | 75% | — | -48.3% | हाँ | हाँ |
| 2 | E5 | R4 4-hour-horizon portfolio | strategy_1d_step24_1h | -60.4% | -0.60 | 100% | — | — | — | — |

### 4h — 4 घंटे

कुल rows: 1,044; tiers: E1 0, E2 195, E3 20, E4 167, E5 662


**दिशा (Direction)**


*trade नियम*: 952 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | TFX EMAX | research_tf_edge_map | long 10 big coins | 1,131 | 5765% | +4.740% | -2.721% | -2.1% | नहीं | — | — |
| 2 | E2 | TFX DONCH | research_tf_edge_map | long 10 big coins | 1,687 | 2468% | +1.849% | -1.848% | -0.7% | नहीं | — | — |
| 3 | E2 | F3_rev_4h_k0 V3 | research_btc_entry |  BTC | 78 | 1516% | +1.303% | — | — | — | — | 47% of 240 |
| 4 | E2 | F6_rsi_follow_4h_20 V3 | research_btc_entry |  BTC | 13 | 1482% | +1.271% | — | — | — | — | 47% of 240 |
| 5 | E2 | batch1 A2.05b_UltOsc_fade_4h X1 | research_methods_bench |  BTC | 39 | 1213% | +1.024% | — | +0.6%, +1.7% | नहीं | नहीं | 49% of 504 |

*सही दिशा %*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | double_top -> LL | research_ladder_sessions | 50.2% | 43.6% | — | 428 | हाँ |
| 2 | E3 | double_bottom -> HH | research_ladder_sessions | 51.3% | 48.7% | — | 446 | हाँ |
| 3 | E5 | simple REV (10 coins) | research_root_cause | 52.6% | 53.1% | 84% | 122,163 | — |
| 4 | E5 | simple MOM (10 coins) | research_root_cause | 46.8% | 53.1% | -104% | 122,163 | — |

*skill (AUC / IC)*: 11 rows; ऊपर के 4:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | NP1 IC OI_CHG_24H | research_nonprice | — | — | हाँ | — |
| 2 | E3 | NP1 IC SPOT_TAKER_1H | research_nonprice | — | — | हाँ | — |
| 3 | E3 | NP1 IC DEPTH_IMB1_1H | research_nonprice | — | — | हाँ | — |
| 4 | E3 | NP1 IC DEPTH_IMB5_1H | research_nonprice | — | — | हाँ | — |

*portfolio*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | N1 multi-TF trend sleeves (4h-1D) | research_n1_portfolio | 10.5% | +0.40 | 26% | 93.3% | -0.39 (Calmar) | हाँ | हाँ |
| 2 | E4 | rule signals 4h+1D, 0.5% risk, K=6 | research_master_audit | +0.83 (Calmar) | +0.83 | 11% | — | — | — | — |
| 3 | E4 | N1 alone inside ECO | eco | -12.5% | -0.40 | 31% | 74.6% | — | — | — |

*विवरण*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | forward return after support break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |
| 2 | E5 | forward return after resistance break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |

**Entry**


*trade नियम*: 32 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | NP3 4h|ALL|RIDGE|0.95|XT | research_nonprice |  BTC | 85 | 210% | +0.129% | — | — | — | — | 90% of 41 |
| 2 | E2 | NP3 4h|ALL|RIDGE|0.95|XM | research_nonprice |  BTC | 85 | 207% | +0.154% | — | — | — | — | 90% of 41 |
| 3 | E2 | NP3 4h|NODEPTH|EQ|0.2|XT | research_nonprice |  BTC | 862 | 84% | +0.014% | — | — | — | — | 90% of 41 |
| 4 | E2 | NP3 4h|ALL|RIDGE|0.8|XT | research_nonprice |  BTC | 355 | 84% | +0.013% | — | — | — | — | 90% of 41 |
| 5 | E2 | NP3 4h|ALL|RIDGE|0.8|XM | research_nonprice |  BTC | 355 | 80% | +0.037% | — | — | — | — | 90% of 41 |

*सही दिशा %*: 15 rows; ऊपर के 4:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | S/R touch (resistance) -> becomes a swing turn | research_swing_vs_sr | 8.2% | 5.1% | — | 12,309 | हाँ |
| 2 | E3 | S/R touch (both) -> becomes a swing turn | research_swing_vs_sr | 8.0% | 5.2% | — | 24,766 | हाँ |
| 3 | E3 | S/R touch (support) -> becomes a swing turn | research_swing_vs_sr | 7.8% | 5.3% | — | 12,457 | हाँ |
| 4 | E5 | C2 ENT_H1_BREAK | oracle_9m_2026 | 53.8% | 54.6% | 82% | 271 | नहीं |

*skill (AUC / IC)*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | swing-rally AI 4h | research_swing_ai_phase2 | 0.546 | 0.516 | हाँ | — |
| 2 | E5 | A3 AI take/skip on 4h signals | r2_4h_a3 | 0.514 | 0.497 | नहीं | नहीं |
| 3 | E5 | T14 AI take/skip on 120 coins | r2_4h_t14 | 0.505 | 0.496 | नहीं | नहीं |

*portfolio*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | N3 X2 spot/perp routing | research_n3_execution | +0.00 (ΔCalmar) | -0.39 | — | +0.39 | — | — | हाँ |
| 2 | E2 | N3 X1 maker entry | research_n3_execution | +0.00 (ΔCalmar) | -0.39 | — | +0.02 | — | — | नहीं |

*विवरण*: 5 rows; ऊपर के 4:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E3 | Fibonacci retracement levels | research_ladder_sessions | share of turns at fib levels minus control |
| 2 | E5 | high- vs low-volume level (support): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 3 | E5 | high- vs low-volume level (resistance): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 4 | E5 | high- vs low-volume level (both): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |

**Exit**


*portfolio*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | A4 S-LAD long, exit 3 ATR / 60 bars | r2_4h_a4 | 7.6% | +0.80 | 10% | — | — | — | नहीं |
| 2 | E2 | ECO-T4 profit lock (break-even after +3 ATR) | eco | +0.08 (ΔCalmar) | -0.31 | — | -0.54 | — | — | नहीं |

*exit की तुलना (औसत)*: 5 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E5 | exit G1N | oracle_9m_2026 |  BTC | — | 8% | -0.085% | — | — | — | — | — |
| 2 | E5 | exit G051 | oracle_9m_2026 |  BTC | — | 7% | -0.086% | — | — | — | — | — |
| 3 | E5 | exit G12 | oracle_9m_2026 |  BTC | — | 5% | -0.087% | — | — | — | — | — |
| 4 | E5 | exit G11 | oracle_9m_2026 |  BTC | — | -1% | -0.093% | — | — | — | — | — |
| 5 | E5 | exit G21 | oracle_9m_2026 |  BTC | — | -8% | -0.100% | — | — | — | — | — |

**Coin चुनना (Selection)**


*skill (AUC / IC)*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | R6 4H relative brain (skill) | strategy_1d_step23_4h | 0.568 | 0.560 | हाँ | हाँ |
| 2 | E5 | R6: add 2017-19 bear data to training | research_s2_bear_training | — | — | नहीं | नहीं |
| 3 | E5 | R6: add funding + basis features | research_s3_futures_features | — | — | नहीं | नहीं |

*portfolio*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | R6 4H portfolio | strategy_1d_step23_4h | 49.0% | +0.62 | 78% | — | -50.8% | — | हाँ |

**Risk / drawdown**


*portfolio*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | N2 regime gate R1 | research_n2_regime | +0.46 (ΔCalmar) | +0.07 | — | -0.44 | — | — | नहीं |
| 2 | E2 | T20 AI sizing | research_n6_safety_sizing | +0.14 (ΔCalmar) | -0.25 | — | -0.51 | — | — | नहीं |
| 3 | E5 | loss rule L1 (DD halving / pause) | research_master_audit | -30.9% | +0.52 | — | — | — | — | — |

*विवरण*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | T19 per-coin cap 0.20 (S2) | research_n6_safety_sizing |  |

### 8h — 8 घंटे

कुल rows: 87; tiers: E1 0, E2 12, E3 5, E4 27, E5 43


**दिशा (Direction)**


*trade नियम*: 82 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | TFX EMAX | research_tf_edge_map | long 10 big coins | 546 | 15816% | +13.540% | -3.554% | -3.9% | नहीं | — | — |
| 2 | E2 | TFX DONCH | research_tf_edge_map | long 10 big coins | 826 | 5468% | +4.352% | -2.388% | -1.8% | नहीं | — | — |
| 3 | E2 | TFX MACD | research_tf_edge_map | long 10 big coins | 2,236 | 2883% | +2.326% | -1.176% | -0.9% | नहीं | — | — |
| 4 | E2 | TFX RSI | research_tf_edge_map | long 10 big coins | 433 | 2520% | +2.319% | +3.447% | -2.0% | नहीं | — | — |
| 5 | E2 | TFX RSI | research_tf_edge_map | long liquid alts | 1,534 | 2151% | +1.952% | +3.172% | +0.8% | नहीं | — | — |

**Entry**


*trade नियम*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E5 | support-bounce trade EV | research_sr_levels |  10 coins | — | -484% | -0.645% | — | — | — | — | — |

*सही दिशा %*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E5 | buy/sell at swing resistance (bounce) | research_sr_levels | 42.6% | 45.6% | — | 5,904 | नहीं |
| 2 | E5 | buy/sell at swing both (bounce) | research_sr_levels | 42.7% | 46.4% | — | 11,866 | नहीं |
| 3 | E5 | buy/sell at swing support (bounce) | research_sr_levels | 42.8% | 47.2% | — | 5,962 | नहीं |

*skill (AUC / IC)*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | swing-rally AI 8h | research_swing_ai_phase2 | 0.550 | 0.513 | हाँ | — |

### 12h — 12 घंटे

कुल rows: 63; tiers: E1 0, E2 6, E3 3, E4 34, E5 20


**दिशा (Direction)**


*trade नियम*: 58 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | TFX EMAX | research_tf_edge_map | long 10 big coins | 348 | 28895% | +25.185% | -4.564% | -6.6% | हाँ | — | — |
| 2 | E2 | TFX DONCH | research_tf_edge_map | long 10 big coins | 560 | 8410% | +6.730% | -3.566% | -4.0% | नहीं | — | — |
| 3 | E2 | TFX RSI | research_tf_edge_map | long 10 big coins | 283 | 4412% | +3.892% | +4.800% | -2.2% | नहीं | — | — |
| 4 | E2 | TFX RSI | research_tf_edge_map | long liquid alts | 1,004 | 4128% | +3.793% | +5.323% | +0.2% | हाँ | — | — |
| 5 | E2 | TFX MACD | research_tf_edge_map | long 10 big coins | 1,491 | 3717% | +2.988% | -1.871% | -1.0% | नहीं | — | — |

**Entry**


*trade नियम*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E5 | support-bounce trade EV | research_sr_levels |  10 coins | — | -559% | -0.714% | — | — | — | — | — |

*सही दिशा %*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E5 | buy/sell at swing resistance (bounce) | research_sr_levels | 41.9% | 44.7% | — | 3,844 | नहीं |
| 2 | E5 | buy/sell at swing both (bounce) | research_sr_levels | 42.7% | 46.4% | — | 7,828 | नहीं |
| 3 | E5 | buy/sell at swing support (bounce) | research_sr_levels | 43.5% | 47.9% | — | 3,984 | नहीं |

*skill (AUC / IC)*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E5 | swing-rally AI 12h | research_swing_ai_phase2 | 0.522 | 0.475 | नहीं | — |

### 1d — 1 दिन

कुल rows: 359; tiers: E1 0, E2 54, E3 19, E4 65, E5 221


**दिशा (Direction)**


*trade नियम*: 271 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | TFX EMAX | research_tf_edge_map | long 10 big coins | 181 | 107666% | +98.863% | -6.484% | -9.4% | नहीं | — | — |
| 2 | E2 | TFX DONCH | research_tf_edge_map | long 10 big coins | 274 | 22411% | +18.990% | -2.593% | -5.7% | नहीं | — | — |
| 3 | E2 | TFX RSI | research_tf_edge_map | long 10 big coins | 113 | 11092% | +9.900% | +9.406% | -5.7% | नहीं | — | — |
| 4 | E2 | TFX MACD | research_tf_edge_map | long 10 big coins | 708 | 7524% | +6.217% | -2.945% | -3.9% | नहीं | — | — |
| 5 | E2 | TFX TSMOM | research_tf_edge_map | long 10 big coins | 1,024 | 6907% | +5.772% | -1.660% | -0.9% | नहीं | — | — |

*सही दिशा %*: 14 rows; ऊपर के 4:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | double_top -> LL | research_ladder_sessions | 63.8% | 45.0% | — | 58 | हाँ |
| 2 | E3 | double_bottom -> HH | research_ladder_sessions | 56.8% | 52.1% | — | 81 | हाँ |
| 3 | E4 | simple REV (10 coins) | research_root_cause | 53.2% | 51.2% | 270% | 20,207 | — |
| 4 | E5 | C1 DIR_CLOSEPOS | oracle_9m_2026 | 53.3% | 50.0% | — | 272 | नहीं |

*skill (AUC / IC)*: 5 rows; ऊपर के 4:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | NP1 IC PREM_Z | research_nonprice | — | — | हाँ | — |
| 2 | E5 | NP1 IC FUND_LVL | research_nonprice | — | — | नहीं | — |
| 3 | E5 | NP1 IC PREM_1H | research_nonprice | — | — | नहीं | — |
| 4 | E5 | NP1 IC BASIS | research_nonprice | — | — | नहीं | — |

*portfolio*: 6 rows; ऊपर के 6:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | spot timing S1 | research_spot_sleeve | +0.01 (ΔSharpe vs hold) | — | -32% | +0.18 | +30.8% | नहीं | नहीं |
| 2 | E4 | spot timing S2 | research_spot_sleeve | -0.01 (ΔSharpe vs hold) | — | -30% | +0.46 | -0.8% | नहीं | नहीं |
| 3 | E4 | spot timing S3 | research_spot_sleeve | -0.22 (ΔSharpe vs hold) | — | -40% | +0.13 | +31.3% | नहीं | नहीं |
| 4 | E4 | spot timing S4 | research_spot_sleeve | -0.11 (ΔSharpe vs hold) | — | -34% | +0.08 | +31.1% | नहीं | नहीं |
| 5 | E4 | spot timing S5 | research_spot_sleeve | -0.68 (ΔSharpe vs hold) | — | -72% | +0.40 | — | — | नहीं |
| 6 | E5 | spot timing S6 | research_spot_sleeve | -0.17 (ΔSharpe vs hold) | — | -14% | -0.91 | +57.1% | नहीं | नहीं |

*विवरण*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E3 | forward return after resistance break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |
| 2 | E5 | forward return after support break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |

**Entry**


*trade नियम*: 7 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E4 | ladder probe/scale-in V3 | research_probe_scalein | long 10 coins | 105 | 1846% (R) | +0.28 R | — | -0.00 R | — | — | — |
| 2 | E4 | ladder probe/scale-in V2 | research_probe_scalein | long 10 coins | 153 | 1574% (R) | +0.24 R | — | -0.15 R | — | — | — |
| 3 | E4 | ladder probe/scale-in V1 | research_probe_scalein | long 10 coins | 153 | 1544% (R) | +0.27 R | — | -0.09 R | — | — | — |
| 4 | E4 | ladder probe/scale-in V1 | research_probe_scalein | short 10 coins | 152 | 260% (R) | +0.05 R | — | +0.33 R | — | — | — |
| 5 | E4 | ladder probe/scale-in V2 | research_probe_scalein | short 10 coins | 152 | 248% (R) | +0.04 R | — | +0.32 R | — | — | — |

*सही दिशा %*: 6 rows; ऊपर के 4:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | S/R touch (resistance) -> becomes a swing turn | research_swing_vs_sr | 7.0% | 3.3% | — | 1,938 | हाँ |
| 2 | E3 | S/R touch (both) -> becomes a swing turn | research_swing_vs_sr | 7.5% | 4.4% | — | 4,040 | हाँ |
| 3 | E3 | S/R touch (support) -> becomes a swing turn | research_swing_vs_sr | 8.1% | 5.4% | — | 2,102 | हाँ |
| 4 | E5 | buy/sell at swing resistance (bounce) | research_sr_levels | 42.0% | 45.6% | — | 1,866 | नहीं |

*skill (AUC / IC)*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E5 | 1D AI entry + 1h flow | strategy_1d_step9_ai | 0.539 | 0.495 | नहीं | — |
| 2 | E5 | 1D AI entry classifier | strategy_1d_step8_ai | 0.534 | 0.490 | नहीं | — |
| 3 | E5 | swing-rally AI 1D | research_swing_ai_phase2 | 0.446 | 0.380 | नहीं | — |

*portfolio*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | E11 longs on USDT-M perps instead of spot | research_r1 | +0.20 (ΔCalmar) | +2.36 | 22% | — | — | — | — |
| 2 | E5 | spot DCA, averaging down, TP 10%, no stop | research_spot_dca | -46.5% | — | -91% | -7.2% | — | — | — |

*विवरण*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | Fibonacci retracement levels | research_ladder_sessions | share of turns at fib levels minus control |
| 2 | E5 | high- vs low-volume level (support): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 3 | E5 | high- vs low-volume level (resistance): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 4 | E5 | high- vs low-volume level (both): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |

**Exit**


*skill (AUC / IC)*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E5 | 1D AI exit classifier | strategy_1d_step8_ai | 0.526 | 0.487 | नहीं | — |
| 2 | E5 | 1D AI exit + 1h flow | strategy_1d_step9_ai | 0.522 | 0.484 | नहीं | — |

**Coin चुनना (Selection)**


*skill (AUC / IC)*: 9 rows; ऊपर के 4:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | R5 in top-20 liquid coins (skill) | strategy_1d_step19_largecap | 0.559 | 0.549 | हाँ | — |
| 2 | E3 | R5 5-day relative brain | strategy_1d_step15_slow | 0.545 | 0.532 | हाँ | — |
| 3 | E3 | R10 10-day relative brain | strategy_1d_step15_slow | 0.541 | 0.522 | हाँ | — |
| 4 | E3 | B1 1-day relative (535 unseen coins) | strategy_1d_step13_unseen | 0.530 | 0.511 | हाँ | नहीं |

*portfolio*: 13 rows; ऊपर के 6:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | F7 RS at true fee (M_AI3 mix) | research_1d_true_fee | 63.5% | +3.09 | -21% | — | +23.8% | — | — |
| 2 | E2 | F2 long-short (AI top long spot / bottom short perp) | strategy_f2_longshort | 51.9% | +1.71 | 30% | — | — | — | हाँ |
| 3 | E2 | 1D alone (LS_RS) inside ECO | eco | 15.0% | +1.22 | 12% | 53.7% | — | — | — |
| 4 | E2 | M_AI3 (1D+4H+1h sleeves) f=1.0 | strategy_1d_step27_combine | 55.2% | +0.72 | 77% | — | -47.2% | — | — |
| 5 | E2 | M_AI3 f=0.5 (Step 27 pick) | strategy_1d_step27_combine | 34.1% | +0.69 | 49% | — | -19.9% | — | — |
| 6 | E2 | R5 top-20 portfolio (80% invested) | strategy_1d_step19_largecap | 38.6% | +0.53 | 73% | — | -31.1% | हाँ | — |

*विवरण*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | overfit audit of the 1D research (PBO / DSR) | research_overfit_s1 | PBO 0.65 = 65% chance the chosen config is overfit |
| 2 | E5 | EMO-1 candle-emotion cross-section | emotion | dev Sharpe CI fully negative; closed FAIL |

**Risk / drawdown**


*skill (AUC / IC)*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | large-cap market gate | strategy_1d_step20_largecap_gate | 0.540 | 0.505 | हाँ | — |
| 2 | E5 | market brain (when to be out) | strategy_1d_step17_18 | 0.523 | 0.494 | नहीं | — |
| 3 | E5 | crash brain | strategy_1d_step21_crash | 0.472 | 0.399 | नहीं | — |

*portfolio*: 6 rows; ऊपर के 6:

| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | E1a BTC hedge of the short book | research_r1 | +0.50 (ΔCalmar) | +2.66 | 14% | — | — | — | — |
| 2 | E2 | F7 stops x1.5 + 30d cooldown (RS) | strategy_f7_risk | +0.45 (ΔCalmar) | +2.16 | 21% | — | +2.6%, +15.0% | हाँ | हाँ |
| 3 | E4 | ECO-W2: 1D LS_RS + N1, inverse-vol (live) | eco | -0.3% | -0.02 | 19% | 65.9% | — | — | हाँ |
| 4 | E5 | E4 inverse-vol weights + 30% cap | research_r1 | -0.32 (ΔCalmar) | +1.84 | 20% | — | — | — | — |
| 5 | E5 | E1b BTC hedge (full) | research_r1 | -1.32 (ΔCalmar) | +0.83 | 28% | — | — | — | — |
| 6 | E5 | volatility sizing | strategy_1d_step28_volsize | -0.05 (ΔCalmar) | +0.66 | 59% | — | — | — | नहीं |

*विवरण*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | exposure D1 f=1.0 (D1 sleeve) | drawdown_ddx | lower exposure cuts DD about proportionally (and profit) |
| 2 | E5 | exposure D1 f=0.75 (D1 sleeve) | drawdown_ddx | lower exposure cuts DD about proportionally (and profit) |
| 3 | E5 | exposure D1 f=0.5 (D1 sleeve) | drawdown_ddx | lower exposure cuts DD about proportionally (and profit) |
| 4 | E5 | exposure D1 f=0.3 (D1 sleeve) | drawdown_ddx | lower exposure cuts DD about proportionally (and profit) |

### 3d — 3 दिन

कुल rows: 72; tiers: E1 0, E2 15, E3 0, E4 3, E5 54


**दिशा (Direction)**


*trade नियम*: 72 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | F3_rev_72h_k0 V3 | research_btc_entry |  BTC | 78 | 1120% | +0.938% | — | — | — | — | 49% of 72 |
| 2 | E2 | F2_mom_72h_k2 V2 | research_btc_entry |  BTC | 38 | 890% | +0.727% | — | — | — | — | 49% of 72 |
| 3 | E2 | F2_mom_72h_k1 A4_4 | research_btc_entry |  BTC | 148 | 490% | +0.359% | — | — | — | — | 49% of 72 |
| 4 | E2 | F3_rev_72h_k1 V3 | research_btc_entry |  BTC | 66 | 454% | +0.326% | — | — | — | — | 49% of 72 |
| 5 | E2 | F2_mom_72h_k1 V1 | research_btc_entry |  BTC | 190 | 423% | +0.297% | — | — | — | — | 49% of 72 |

### 1w — 1 हफ़्ता

कुल rows: 175; tiers: E1 0, E2 23, E3 3, E4 18, E5 131


**दिशा (Direction)**


*trade नियम*: 163 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | TFX DONCH | research_tf_edge_map | long 10 big coins | 43 | 342967% | +302.749% | +2.248% | — | नहीं | — | — |
| 2 | E2 | TFX TSMOM | research_tf_edge_map | long 10 big coins | 130 | 160708% | +144.483% | -3.158% | -9.8% | नहीं | — | — |
| 3 | E2 | TFX MACD | research_tf_edge_map | long 10 big coins | 97 | 142612% | +128.853% | +3.554% | -21.9% | नहीं | — | — |
| 4 | E2 | F5_z_fade_2016_k3 V3 | research_btc_entry |  BTC | 41 | 1479% | +1.269% | — | — | — | — | 45% of 144 |
| 5 | E2 | F5_z_fade_2016_k2 V3 | research_btc_entry |  BTC | 68 | 554% | +0.418% | — | — | — | — | 45% of 144 |

*सही दिशा %*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | double_top -> LL | research_ladder_sessions | 77.8% | 44.1% | — | 9 | हाँ |
| 2 | E5 | double_bottom -> HH | research_ladder_sessions | 44.4% | 66.3% | — | 9 | नहीं |

*विवरण*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E3 | forward return after resistance break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |
| 2 | E5 | forward return after support break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |

**Entry**


*trade नियम*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E4 | support-bounce trade EV | research_sr_levels |  10 coins | — | 1963% | +1.606% | — | — | — | — | — |

*सही दिशा %*: 3 rows; ऊपर के 3:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E5 | buy/sell at swing support (bounce) | research_sr_levels | 54.0% | 54.7% | — | 252 | नहीं |
| 2 | E5 | buy/sell at swing both (bounce) | research_sr_levels | 45.0% | 46.8% | — | 467 | नहीं |
| 3 | E5 | buy/sell at swing resistance (bounce) | research_sr_levels | 34.4% | 37.2% | — | 215 | नहीं |

*विवरण*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | Fibonacci retracement levels | research_ladder_sessions | share of turns at fib levels minus control |
| 2 | E5 | high- vs low-volume level (support): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 3 | E5 | high- vs low-volume level (resistance): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 4 | E5 | high- vs low-volume level (both): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |

### 1M — 1 महीना

कुल rows: 9; tiers: E1 0, E2 0, E3 1, E4 0, E5 8


**दिशा (Direction)**


*trade नियम*: 1 rows; ऊपर के 1:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E5 | TFX TSMOM | research_tf_edge_map | long 10 big coins | 31 | -17473% | -19.916% | -19.241% | -6.1% | नहीं | — | — |

*सही दिशा %*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |
|---|---|---|---|---|---|---|---|---|
| 1 | E3 | double_top -> LL | research_ladder_sessions | 50.0% | 37.5% | — | 4 | हाँ |
| 2 | E5 | double_bottom -> HH | research_ladder_sessions | 75.0% | 82.6% | — | 4 | नहीं |

*विवरण*: 2 rows; ऊपर के 2:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | forward return after resistance break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |
| 2 | E5 | forward return after support break | research_sr_volume | gross forward return after the break (no cost); skill = CI-low > 0 |

**Entry**


*विवरण*: 4 rows; ऊपर के 4:

| # | Tier | तरीका | study | नोट |
|---|---|---|---|---|
| 1 | E5 | Fibonacci retracement levels | research_ladder_sessions | share of turns at fib levels minus control |
| 2 | E5 | high- vs low-volume level (support): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 3 | E5 | high- vs low-volume level (resistance): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |
| 4 | E5 | high- vs low-volume level (both): break-rate difference | research_sr_volume | negative = high-volume levels break LESS |

### event — बिना घड़ी वाले bars (Renko / volume / dollar / imbalance)

कुल rows: 27; tiers: E1 0, E2 4, E3 1, E4 2, E5 20


**दिशा (Direction)**


*trade नियम*: 27 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E2 | batch2 A4.10_ImbalanceBars_follow X1 | research_methods_bench |  BTC | 178 | 302% | +0.186% | — | -0.2%, +0.7% | नहीं | नहीं | 41% of 27 |
| 2 | E2 | batch2 A4.10_VolumeBars_follow X1 | research_methods_bench |  BTC | 178 | 272% | +0.158% | — | -0.1%, +0.5% | नहीं | नहीं | 41% of 27 |
| 3 | E2 | batch1 A1.16_Renko1pct X1 | research_methods_bench |  BTC | 178 | 193% | +0.086% | — | -0.2%, +0.5% | नहीं | नहीं | 41% of 27 |
| 4 | E2 | batch2 A4.10_DollarBars_follow X1 | research_methods_bench |  BTC | 178 | 110% | +0.010% | — | -0.4%, +0.5% | नहीं | नहीं | 41% of 27 |
| 5 | E3 | batch2 A4.10_ImbalanceBars_fade X3 | research_methods_bench |  BTC | 1,487 | 70% | -0.027% | — | +0.0%, -0.1% | हाँ | नहीं | 41% of 27 |

### intraday-turn — दिन के अंदर के turns (आकार θ से, bar से नहीं)

कुल rows: 320; tiers: E1 0, E2 0, E3 6, E4 1, E5 313


**Entry**


*trade नियम*: 20 rows; ऊपर के 5:

| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E4 | T1 enter at bounce theta=0.08 f=0.75 | turn_detect_2026 |  BTC | 16 | 483% | +0.352% | — | — | नहीं | — | — |
| 2 | E5 | T0 follow confirmed turn theta=0.02 | turn_detect_2026 |  BTC | 180 | 98% | -0.001% | — | — | — | — | — |
| 3 | E5 | T1 enter at bounce theta=0.04 f=0.5 | turn_detect_2026 |  BTC | 95 | 17% | -0.076% | — | — | नहीं | — | — |
| 4 | E5 | T1 enter at bounce theta=0.01 f=0.5 | turn_detect_2026 |  BTC | 1,237 | 8% | -0.085% | — | — | नहीं | — | — |
| 5 | E5 | T1 enter at bounce theta=0.01 f=0.75 | turn_detect_2026 |  BTC | 869 | 3% | -0.089% | — | — | नहीं | — | — |

*skill (AUC / IC)*: 300 rows; ऊपर के 4:

| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |
|---|---|---|---|---|---|---|---|
| 1 | E3 | T2 F15_eth_lead theta=0.005 f=0.25 | turn_detect_2026 | 0.553 | 0.520 | हाँ | — |
| 2 | E3 | T2 F02_prior_leg theta=0.005 f=0.25 | turn_detect_2026 | 0.544 | 0.518 | हाँ | — |
| 3 | E3 | T2 F14_retests theta=0.005 f=0.25 | turn_detect_2026 | 0.531 | 0.507 | हाँ | — |
| 4 | E3 | T2 F01_bounce_min theta=0.005 f=0.25 | turn_detect_2026 | 0.534 | 0.505 | हाँ | — |

---

## 5. सबसे करीब पहुँचे systems: E1 क्यों नहीं मिला

| System | Timeframe | Skill (AUC) | 2021–26 (test window) | अनदेखा 2018–19 | पिछला साल (P3) |
|---|---|---|---|---|---|
| R24 relative brain (long-only portfolio) | 1h | 0.565 | CAGR +68.7% | **-48.3%** | — |
| R6 relative brain (long-only) | 4h | 0.568 | CAGR +49.0% | **-50.8%** | — |
| R5 top-20 (long-only, 80%) | 1d | 0.559 | CAGR +38.6% | **-31.1%** | — |
| N1 trend sleeves | 4h–1D | — | dev CAGR +93.3% | +10.5% | Calmar **-0.39** |
| F7 RS (long-short + stops) | 1d | — | Calmar 2.16, DD 21% | **+2.6%** | **+15.0%** |
| 1D alone inside ECO | 1d | — | dev CAGR +53.7% | — | **+15.0%** |
| ECO-W2 (live = 1D + N1) | 1d | — | dev CAGR +65.9% | — | **-0.3%** |

**पढ़ने का तरीका:**
- **Coin चुनने की skill असली है।** यह अनदेखे coins (AUC 0.530) और 2018–19 (AUC 0.526) पर भी टिकी।
- **पर long-only portfolios bear market में डूबे** (2018–19: −31% से −51% सालाना)।
- **Long-short + stops (F7 RS)** ही अकेला ऐसा है जो **दोनों अनदेखे दौरों में positive** रहा: 2018–19 और पिछला साल।
  - E1 फिर भी नहीं: उसके अनदेखे दौरों का CI नहीं है, और उसके नियम 2021–26 के data पर चुने गए थे।
  - इसका असली फ़ैसला अब सिर्फ़ forward data देगा: TC gate (~9 नवंबर) और ECO demo।
- **ECO = 1D + N1:** पिछले साल N1 (-12.5%) ने 1D (+15.0%) की कमाई खा ली, और ECO -0.3% पर रहा।
  - Sleeve A forward जाँच इसी का जवाब देगी।
  - इसे P3 देखकर बदलना snooping होगा।

---

## 6. किस्मत की जाँच (multiple testing): grids में सिक्का कितना है

| study | timeframe | configs (OOS) | net > 0 वाले | **gross > 0 वाले** (50% = सिक्का) | सबसे अच्छा fee-कवरेज | median fee-कवरेज |
|---|---|---|---|---|---|---|
| micro_momentum_2026 | 1s-1m | 180 | 0% | 35% | 4% | -1% |
| oracle_9m_2026 | 15m | 5 | 0% | 0% | -27% | -53% |
| r2_4h_a1 | 4h | 8 | 100% | 100% | — | — |
| research_btc_entry | 1d | 204 | 17% | 48% | 1990% | -5% |
| research_btc_entry | 1h | 216 | 15% | 47% | 1013% | -3% |
| research_btc_entry | 1w | 144 | 14% | 45% | 1479% | -3% |
| research_btc_entry | 30m | 6 | 50% | 50% | 611% | 82% |
| research_btc_entry | 3d | 72 | 21% | 49% | 1120% | -3% |
| research_btc_entry | 4h | 240 | 16% | 47% | 1516% | -2% |
| research_btc_entry | 5m | 48 | 19% | 46% | 735% | -3% |
| research_btc_entry | 8h | 24 | 21% | 50% | 787% | -0% |
| research_methods_bench | 15m | 504 | 13% | 49% | 948% | -1% |
| research_methods_bench | 1h | 504 | 17% | 52% | 604% | 2% |
| research_methods_bench | 4h | 504 | 24% | 49% | 1213% | -2% |
| research_methods_bench | event | 27 | 15% | 41% | 302% | -7% |
| research_nonprice | 1h | 44 | 0% | 70% | 37% | 8% |
| research_nonprice | 4h | 41 | 34% | 90% | 210% | 56% |

**मतलब:**
- **BTC indicator grids** (bench, BTC entry, सभी timeframes) में fee से पहले की कमाई सिर्फ़ **41%–52%** configs में positive थी, यानी सिक्के जितनी।
  - इनमें जो "best" दिखते हैं (fee-कवरेज 302%–1,990%), वे बहुत छोटे n (13–178 trades) पर हैं।
  - वही grid बता रहा है कि यह संयोग है।
- **Non-price grid (NP2/NP3)** अलग है: 4h पर 90% configs gross-positive थे, 1h पर 70%।
  - **यह असली संकेत है।** पर median fee-कवरेज 4h पर 56% और 1h पर 8% है, यानी fee का आधा भी नहीं।
- **1-second grid** (35% gross-positive) सिक्के से भी नीचे है।

---

## 7. निष्कर्ष: timeframe-wise गणित

1. **< 1 घंटा:** दिशा, entry या exit का कोई भी formula fee पार नहीं करता। गणित इसकी इजाज़त ही नहीं देता: ज़रूरी सही दिशा 61.8%–163.4% है।
   - सबसे अच्छी चीज़ें (double top/bottom के बाद अगला leg, seconds-momentum, order-flow) असली हैं, पर fee के 1/10 से 1/2 तक।
2. **1h–4h:** "कौन-सा coin" (relative strength) में असली skill है (AUC 0.565–0.568)। "BTC किधर जाएगा" में नहीं।
   - Long-only होने पर bear market में घाटा हुआ।
   - Order book / OI संकेत असली हैं, पर fee का आधा ही कमाते हैं।
3. **8h–1d:** यहाँ दो चीज़ें टिकीं, और दोनों ECO में पहले से live हैं:
   - **(a) "RSI < 30 पर खरीदो, > 50 पर बेचो" (oversold long):** median trade positive। यह N1 का sleeve B है।
   - **(b) Coin चुनना + long-short + stops (F7 RS):** दोनों अनदेखे दौर positive रहे। यह ECO का 1D हिस्सा है।
4. **3d–1M:** ज़रूरी सही दिशा ~51% है (सबसे आसान), पर independent samples बहुत कम हैं। अभी कुछ साबित नहीं।
5. **Exit के बारे में:** हर study में exit बदलने से जीत % बदला, पर औसत कमाई नहीं बदली।
   - Oracle में 5 exits का फ़र्क 0.015% था। A4 का exit grid PBO 0.84 पर था, यानी noise।
   - Exit brain (AUC 0.672) गिरावट नहीं, सिर्फ़ volatility पहचानता है।
   - **Exit से profit नहीं बनता। Profit सही entry/selection से बनता है, और exit सिर्फ़ उसे बचाता है।**
6. **Risk के बारे में:** जो काम करता है, वह सब live है:
   - कम exposure;
   - long-short;
   - per-trade stops (F7: Calmar +0.45);
   - दो कम-जुड़े systems (ECO)।

   "कब बाहर रहना है" वाले सारे brains fail हुए।

**सीधी बात:** "हर timeframe का अपना formula" वाली खोज का जवाब यह है कि अलग formula मिले। पर fee के बाद टिकने वाले formulas सिर्फ़ 8h–1d पर हैं, और वे पहले से हमारे live system में हैं। नई timeframe-formula खोजने से ज़्यादा कीमती अब forward सबूत है।

---

## 8. आगे क्या (हर कदम आपकी हाँ से)

- **(a) कुछ नया नहीं जोड़ना।** Atlas की top formulas पहले से ECO में हैं (N1 sleeve A/B/D + 1D LS_RS)। TC gate (~9 नवंबर) और Sleeve A के फ़ैसले का इंतज़ार करें।
- **(b) Atlas को forward data से जोड़ना।** हर महीने ECO demo, PaperN1 और F4 के असली trades को इसी atlas की rows से मिलाया जाए: live में fee-कवरेज और सही % कितना है। यह read-only report होगी, जिसका protocol अलग से lock होगा।
- **(c) अगर नई research चाहिए:** सिर्फ़ वहाँ जहाँ गणित इजाज़त देता है, यानी 8h–1W पर, और नए (forward) data पर। पुराना 2020–26 data कई बार इस्तेमाल हो चुका है।

---

## 9. Discipline और verification

- **Inventory:** logs/ के सभी 97 folders जाँचे गए (atlas का अपना folder छोड़कर)। 59 studies शामिल हुईं (protocol + result files)।
  - 38 बाहर रहीं: operations, downloads, forward (बहुत नया data), बिना protocol वाली पुरानी studies, बाहरी Gemini notebook, और रुकी हुई Step 11।
  - हर एक का कारण `study_inventory.csv` में है। `archive/` नहीं पढ़ा गया।
- **Verifier** `verify_tf_atlas.py` → `verify_output.txt`। TOTAL 10 checks, 10 PASS, 0 FAIL -> ALL PASS (mutation test: `mutation_test_output.txt`)।
- **Build में पकड़ी गई गलतियाँ** (सब `CODE_NOTES.md` में):
  1. BTC-entry filter ने F11/F12 (30 configs) गलती से हटा दिए थे। ठीक किया गया।
  2. ECO, N1 और N-series में पहले चुनाव वाला data "OOS" मान लिया गया था। अब OOS = P3 या 2018–19।
  3. R24 1h portfolio एक बार E1 पर पहुँच गया था, क्योंकि उसका 2018–19 वाला घाटा row में जुड़ा नहीं था। जोड़ने के बाद **E1 = 0**।
  4. Modifier rows (stops, hedge, sizing) को उनके base से नापा गया, absolute CAGR से नहीं। Spot timing को BTC hold से नापा गया।
  5. Unfitted grids की बिना-CI positive rows को E4 पर रखा गया, E5 पर नहीं।
- **हर सुधार सावधानी की तरफ़ है।** इनमें से किसी से कोई row ऊपर नहीं गई। इन्हें तय करने से पहले कोई report text नहीं लिखा गया था।

## 10. सीमाएँ

- **अलग studies की fee अलग थी।** TFX 0.108% थी, पुरानी 1D alt studies 0.25–0.5%, और नई studies `fees.json` की। Fee-कवरेज 0.092% पर standardised है। Alt-coin studies के लिए असली fee ज़्यादा है।
- **एक ही data बार-बार इस्तेमाल हुआ।** 2020–26 BTC और वही 10 coins कई studies में आए। हर row का "OOS" वही है जो उसकी study ने घोषित किया था। 2025–26 का holdout कई बार खुल चुका है।
- **TFX और ladder studies descriptive हैं** (standard parameters, बिना fit)। उनमें कोई pre-registered trading फ़ैसला नहीं था, इसलिए वे E1 हो ही नहीं सकते थे।
- **Atlas सिर्फ़ stored नतीजों पर बना है।** जिस study ने कोई माप (जैसे median या CI) store नहीं किया, वह यहाँ भी नहीं है।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। ये पिछले data के नतीजे हैं, भविष्य का वादा नहीं।
