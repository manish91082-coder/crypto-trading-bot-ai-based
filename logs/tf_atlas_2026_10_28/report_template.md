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
   - Profit के लिए ज़रूरी सही दिशा: 5 मिनट पर {{p5}}, 1 घंटे पर {{p1h}}, 4 घंटे पर {{p4h}}, 1 दिन पर {{p1d}}, और 1 हफ़्ते पर {{p1w}}।
2. **पूरी R&D में {{nrows}} नतीजे-rows बनीं** ({{ninc}} studies, {{nsrc}} source files)। एक भी row tier **E1** ("पूरी तरह साबित") तक नहीं पहुँची। Tiers:
   - E2 {{nE2}};
   - E3 {{nE3}};
   - E4 {{nE4}};
   - E5 {{nE5}}।

   E1 के सबसे करीब 1h/4h के AI brains पहुँचे थे। पर उनका 2018–19 का अनदेखा दौर भारी घाटे का निकला (§5)।
3. **Timeframe के हिसाब से जहाँ सच में कुछ "बैठता" है (ईमानदार ranking):**

   | Timeframe | सबसे अच्छी चीज़ | कितना बैठता है | स्थिति |
   |---|---|---|---|
   | 1s–15m | कुछ नहीं | Indicator grids में fee से पहले की कमाई सिर्फ़ ~{{g15}} configs में positive (सिक्का = 50%) | बंद |
   | 1h | **Coin चुनना** (R24 brain) | AUC {{r24auc}}। 2021–26 में CAGR {{r24cagr}}, पर 2018–19 में {{r24pre}} | Skill असली, पैसा सिर्फ़ bull दौर में |
   | 4h | **Coin चुनना** (R6), **N1 trend sleeves**, order-book/OI संकेत | R6 AUC {{r6auc}}। N1 2018–19 में {{n1pre}}, पर पिछले साल (P3) Calmar {{n1p3}}। Non-price संकेत fee का ~{{np4med}} | मिला-जुला |
   | 8h–12h | **RSI < 30 पर long** (oversold खरीदना) | Median trade positive: 12h बड़े coins पर {{rsi12med}}। Liquid alts पर पिछले साल भी positive ({{rsi12altp3}}) | Atlas की सबसे मज़बूत direction formula। N1 में पहले से live है (sleeve B) |
   | 1d | **Coin चुनना + long-short + stops** (F7 RS) | Calmar {{f7cal}}, DD {{f7dd}}। 2018–19 में {{f7pre}}, पिछले साल {{f7p3}} | **Atlas का सबसे अच्छा-सबूत वाला system**। ECO में live है |
   | 3d–1M | कुछ साबित नहीं | Samples कम, grids सिक्के जैसे ({{g1w}}) | खुला |

4. **एक बड़ी चेतावनी: "औसत" अक्सर झूठ बोलता है।**
   - उदाहरण: 1d पर EMA-crossover long का औसत trade {{ema1dmean}} था।
   - पर उसका **median trade {{ema1dmed}}** था, और पिछले साल (P3) {{ema1dp3}}।
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

{{PHYS}}

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

{{CARDS}}

---

## 4. हर timeframe की पूरी ranking (ऊपर की rows; पूरी सूची `atlas_ranked.csv` में)

हर table अपने अंदर rank है: tier पहले, फिर fee-कवरेज / AUC / सही % / Calmar। अलग तरह के मापों को आपस में नहीं मिलाया गया।

**Columns:**
- **"उसी grid में gross > 0":** उस study के उस timeframe के सारे configs में से कितनों का fee से पहले का औसत positive था। ~50% = सिक्का, यानी grid में दिशा की जानकारी नहीं।
- **"आगे की जाँच":** P3 (पिछला साल) या 2018–19 जैसे अनदेखे दौर।

{{TABLES}}

---

## 5. सबसे करीब पहुँचे systems: E1 क्यों नहीं मिला

| System | Timeframe | Skill (AUC) | 2021–26 (test window) | अनदेखा 2018–19 | पिछला साल (P3) |
|---|---|---|---|---|---|
| R24 relative brain (long-only portfolio) | 1h | {{r24auc}} | CAGR {{r24cagr}} | **{{r24pre}}** | — |
| R6 relative brain (long-only) | 4h | {{r6auc}} | CAGR {{r6cagr}} | **{{r6pre}}** | — |
| R5 top-20 (long-only, 80%) | 1d | {{r5auc}} | CAGR {{r5cagr}} | **{{r5pre}}** | — |
| N1 trend sleeves | 4h–1D | — | dev CAGR {{n1dev}} | {{n1pre}} | Calmar **{{n1p3}}** |
| F7 RS (long-short + stops) | 1d | — | Calmar {{f7cal}}, DD {{f7dd}} | **{{f7pre}}** | **{{f7p3}}** |
| 1D alone inside ECO | 1d | — | dev CAGR {{eco1ddev}} | — | **{{eco1dp3}}** |
| ECO-W2 (live = 1D + N1) | 1d | — | dev CAGR {{ecodev}} | — | **{{ecop3}}** |

**पढ़ने का तरीका:**
- **Coin चुनने की skill असली है।** यह अनदेखे coins (AUC {{b1auc}}) और 2018–19 (AUC {{pre5auc}}) पर भी टिकी।
- **पर long-only portfolios bear market में डूबे** (2018–19: −31% से −51% सालाना)।
- **Long-short + stops (F7 RS)** ही अकेला ऐसा है जो **दोनों अनदेखे दौरों में positive** रहा: 2018–19 और पिछला साल।
  - E1 फिर भी नहीं: उसके अनदेखे दौरों का CI नहीं है, और उसके नियम 2021–26 के data पर चुने गए थे।
  - इसका असली फ़ैसला अब सिर्फ़ forward data देगा: TC gate (~9 नवंबर) और ECO demo।
- **ECO = 1D + N1:** पिछले साल N1 ({{n1ecop3}}) ने 1D ({{eco1dp3}}) की कमाई खा ली, और ECO {{ecop3}} पर रहा।
  - Sleeve A forward जाँच इसी का जवाब देगी।
  - इसे P3 देखकर बदलना snooping होगा।

---

## 6. किस्मत की जाँच (multiple testing): grids में सिक्का कितना है

{{CHANCE}}

**मतलब:**
- **BTC indicator grids** (bench, BTC entry, सभी timeframes) में fee से पहले की कमाई सिर्फ़ **{{glo}}–{{ghi}}** configs में positive थी, यानी सिक्के जितनी।
  - इनमें जो "best" दिखते हैं (fee-कवरेज {{bestlo}}–{{besthi}}), वे बहुत छोटे n (13–178 trades) पर हैं।
  - वही grid बता रहा है कि यह संयोग है।
- **Non-price grid (NP2/NP3)** अलग है: 4h पर {{np4pos}} configs gross-positive थे, 1h पर {{np1pos}}।
  - **यह असली संकेत है।** पर median fee-कवरेज 4h पर {{np4med}} और 1h पर {{np1med}} है, यानी fee का आधा भी नहीं।
- **1-second grid** ({{micropos}} gross-positive) सिक्के से भी नीचे है।

---

## 7. निष्कर्ष: timeframe-wise गणित

1. **< 1 घंटा:** दिशा, entry या exit का कोई भी formula fee पार नहीं करता। गणित इसकी इजाज़त ही नहीं देता: ज़रूरी सही दिशा {{p1h}}–{{p1m}} है।
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
   - Exit brain (AUC {{exitauc}}) गिरावट नहीं, सिर्फ़ volatility पहचानता है।
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

- **Inventory:** logs/ के सभी {{ninv}} folders जाँचे गए (atlas का अपना folder छोड़कर)। {{ninc}} studies शामिल हुईं (protocol + result files)।
  - {{nexc}} बाहर रहीं: operations, downloads, forward (बहुत नया data), बिना protocol वाली पुरानी studies, बाहरी Gemini notebook, और रुकी हुई Step 11।
  - हर एक का कारण `study_inventory.csv` में है। `archive/` नहीं पढ़ा गया।
- **Verifier** `verify_tf_atlas.py` → `verify_output.txt`। {{VERIFY}}
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
