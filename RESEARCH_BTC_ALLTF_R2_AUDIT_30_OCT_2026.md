# BTC-ALLTF R2: पूरे 28.8 GB study की जाँच, गलतियाँ, सुधार और अंतिम निष्कर्ष — 30 Oct 2026

**Protocol (पहले से lock):** `logs/btc_alltf_r2_2026_10_29/R2_PROTOCOL_PREREGISTERED.md` (SHA `b32fb9d2…`, 2026-10-29T03:42:30Z)

| | फ़ाइल |
|---|---|
| Audit | `logs/btc_alltf_r2_2026_10_29/AUDIT_FINDINGS.md` |
| Lock के बाद के बदलाव (कारण सहित) | `R2_CODE_CHANGES_AFTER_LOCK.md` (entries 1–7) |
| Run | `logs/btc_alltf_r2_2026_10_29/RUN_R2_2026-10-29T0343Z/` |
| Tables | `report/r2_tables.md` |
| Tests | `tests/*.csv` |

---

## 0. सीधा जवाब
1. **पहला निष्कर्ष ("लगभग कुछ भी काम नहीं करता") गलत था,** क्योंकि pass/fail के gates टूटे हुए थे। 70% सटीक "भविष्य जानने वाला" oracle भी उनसे पास नहीं होता।
2. **"सब कुछ काम करता है" भी गलत है।**
   - BTC पर पुराने data में जो "best" दिखा, वह आगे नहीं चला: walk-forward 2021–26 में 24 में से 0 pools significant।
   - हर indicator को अकेले, सैकड़ों coins पर, सबसे सख़्त test में: 0 confirm (S2 atlas)।
3. **3 strategy-families** BTC से चुनी गईं और फिर सैकड़ों दूसरे coins पर out-of-sample confirm हुईं (CONFIRMED_SKILL)। Independent verifier ने हर trade दोबारा मिलाया। इनकी ताक़त **मध्यम** है: सालाना ~14–19%, drawdown ~8–12%। ये buy-and-hold से ज़्यादा कमाई का वादा नहीं करतीं; इनका फ़ायदा बहुत कम drawdown है (नीचे 4.3)।
4. **1 घंटे से छोटे timeframe पर fee की दीवार असली है।** Stop-loss छोटे timeframe पर फ़ायदा नहीं देता। रोज़ 10% जैसा कोई रास्ता इस data में नहीं है।
5. **अगला कदम:** इन 3 families का forward paper test, फिर testnet, फिर आपकी हाँ से छोटा live।

## 1. मूल study (28 Oct)
- **Data:** BTC spot (2017–2026) और futures (2020–2026), Binance का official 1m data; 11 timeframes, 1m से 1y तक।
- **क्या चलाया:**
  - 111 नियम, हर नियम long और short;
  - 9 exit/stop तरीके;
  - 5 filters, 276 जोड़ियाँ, voting।
- **कुल:** 1,38,931 configs और 2,24,84,31,178 trades (28.8 GB)। हर trade पर fee और funding। Verifier 971/971।
- **पहला verdict:** 1 PASS (spot 15m)।

## 2. Audit: क्या गलत निकला (सबूत: `AUDIT_FINDINGS.md`, `audit_*_output.txt`)
| # | गलती | सबूत |
|---|---|---|
| F1 | ≥ ~50 trades की शर्त ने धीमी पर फ़ायदेमंद strategies बाहर कीं | spot 1d EMA20/50: ×38.7, DD 40% (buy-and-hold ×19.6, DD 83%), फिर भी "INSUFFICIENT" |
| F2 | DSR gate का null threshold टूटा था | per-trade Sharpe 0.24–1.21 माँगा गया। 1m पर 98% configs fee से negative होकर variance फुला रहे थे |
| F3 | 1.4 लाख configs पर एक साथ correction, और कोई positive control नहीं | **70% सटीक oracle भी 0% PASS हुआ** (r1_poscontrol), जबकि नया daily test 55% वाले को भी पकड़ता है |
| F4–F8 | per-trade statistics; "0 PASS" को "no profit" पढ़ना; stop के बाद re-entry न होना; DD सिर्फ़ बंद trades पर; सिर्फ़ BTC | spot 1d पर 66% configs fee के बाद profitable थे |

**जो सही था:**
- Engine, data और fees: एक अलग pandas code ने exact वही trades दिए।
- Stop/target का "एक ही candle में दोनों" वाला मामला सिर्फ़ 0.01–0.15% trades में आया।

## 3. नया तरीका (R2)
- **एक पैमाना:** हर config की रोज़ की mark-to-market equity, ताकि हर timeframe एक ही पैमाने पर नापा जाए।
- **Test 1, walk-forward:** BTC पर "सबसे अच्छा चुनो" वाला तरीका आगे के data पर कैसा चला।
- **Test 2, cross-coin:** BTC पर चुने configs, सैकड़ों दूसरे coins पर।
  - **Coins:** spot 521 coins (5m–30m पर 278, 1m पर 9); futures 120।
  - **शर्तें:** liquid coins; delisted coins भी शामिल।
  - **दो जाँचें:** (A) profit, और (B) उसी समय coin पकड़े रहने से बेहतर timing।
  - **हर बार:** 2× fee की जाँच और 3 sub-periods।
- **Controls:**
  - random strategies (negative control);
  - भविष्य जानने वाला oracle (positive control)।
- **Stop-loss दोबारा:** re-entry के साथ।
- **जाँच के दौरान 2 data bugs पकड़े और ठीक किए** (amendment 1; देखें `R2_CODE_CHANGES_AFTER_LOCK.md` 4–5):
  - LUNA जैसे relisted symbols पर नकली छलाँग;
  - delisted coins की खुली position का गलत गिना जाना।

## 4. नतीजे
**4.1 तरीका भरोसे लायक है (controls)**

| Control | झूठा/सही PASS |
|---|---|
| Random (NEG, 260) | **0%** |
| Oracle 52% / 55% / 60% / 70% | 11% / 62% / 77% / **92%** |

**4.2 Walk-forward (BTC, 2021–2026 out-of-sample):**
- 24 में से **0** pools significant; ज़्यादातर घाटे में।
- इसी दौरान BTC buy-and-hold +189% (Sharpe 0.61)।
- Sensitivity वाले 5 और settings के 110 cells में सिर्फ़ 2 BTC के Sharpe 0.61 से ऊपर गए (दोनों spot 1mo: 0.65 और 0.69)। वही pool primary setting में 0.38 है, इसलिए यह टिकाऊ बढ़त नहीं है।
- **मतलब:** पुराने BTC data पर optimize करके winner चुनना किस्मत है।

**4.3 Cross-coin: BTC के 260 top configs → 13 profitable, उनमें 5 CONFIRMED_SKILL**

| Strategy | timeframe | CAGR | Sharpe | Max DD | t (skill) | Coins |
|---|---|---|---|---|---|---|
| SA: 55-bar low टूटने पर ख़रीद, SMA200 के ऊपर | spot 15m | 18.8% | 2.10 | 12% | 5.67 | 278 में से 203 profit |
| SB: RSI14 > 80 momentum long (+ADX / –/ +SMA200 के 3 variants) | futures 8h | 15–18% | 1.45–1.58 | 8–9% | 3.2–3.5 | 118–119 में से 64–68 profit |
| SC: CHOP14 trend + volume | futures 1d | 14% | 1.55 | 9% | 3.25 | 119 में से 69 profit |

**Buy-and-hold से तुलना (उसी coin pool का equal-weight):**

| Strategy | Strategy CAGR | Buy-and-hold CAGR | Strategy Max DD | Buy-and-hold Max DD | 2× fee पर CAGR |
|---|---|---|---|---|---|
| SA | 18.8% | 10.4% | 12% | 94% | **10.3%** |
| SB (3 variants) | 15.4–18.3% | **21.5%** | 8–9% | 90% | 15.2–18.0% |
| SC | 14.2% | **21.5%** | 9% | 90% | 13.8% |

- **SB और SC की सालाना कमाई buy-and-hold से कम है।** इनकी बढ़त जोखिम में है: drawdown लगभग दसवाँ हिस्सा, Sharpe दोगुने से ज़्यादा (1.45–1.58 बनाम 0.67)।
- **SA fee के प्रति नाज़ुक है:** 37,904 trades, इसलिए 2× fee पर CAGR 18.8% से 10.3% हो जाता है, यानी buy-and-hold के बराबर। असली slippage सबसे पहले इसी को नुकसान देगी।
- **SB के trades बहुत कम हैं:** ~119 coins पर 6 साल में कुल ~1,000।
- **हर एक पर:** 3 के 3 sub-periods positive।
- **Tie test:** SA में close = SMA200 वाले floating-point ties को दूसरे तरीके से गिनने पर भी नतीजा वही (`tie_sensitivity_spot_15m_S1.csv`)।

**4.4 S2 atlas: हर indicator अकेले, हर timeframe पर**

- **Confirmed:** 0 configs (हर timeframe के 2–4 हज़ार configs पर BH correction के बाद)।
- **Futures shorts (4h, 8h, 1d):** 1,018 configs में timing skill का संकेत (qB ≤ 0.05, tB 2.5–5.6), और इनमें 98% shorts हैं (MACD, TSI, KST वगैरह)। पर absolute profit कहीं significant नहीं (qA हर जगह ≥ 0.20), और सबसे ऊपर वालों का drawdown 32–43% है।
- **जो patterns बार-बार ऊपर आए** (promising, साबित नहीं): RSI 20/80, high-vol trend long, VWAP/DPO z-score mean-reversion।
- **ताक़त का सबक:** SB का L1 नियम atlas के बड़े family में profit test पर qA 0.23 पर आ जाता है, जबकि skill test (qB 0.006) पास रहता है। S1 का confirmation BTC की pre-selection पर टिका है। इसलिए ताक़त मध्यम है, और forward test ज़रूरी है।

**4.5 Timeframe के हिसाब से**

| Timeframe | निष्कर्ष |
|---|---|
| 1m–30m | fee की दीवार: atlas में 0–3% configs fee के बाद profitable; walk-forward ज़्यादातर घाटे में; सिर्फ़ SA (15m) अपवाद |
| 1h | spot पर कुछ नहीं; futures पर 2 CONFIRMED_PROFIT, पर skill कोई नहीं |
| 4h–1d | असली edge यहीं है (SB, SC); 1d पर stop से drawdown घटता है |
| 1w–1y | बहुत कम data; descriptive ही |

**4.6 Stop-loss (re-entry के साथ):**
- **Exposure:** re-entry से market में रहने का समय वापस आता है (0.20 से 0.46)।
- **≤ 8h:** Sharpe ज़्यादातर गिरता है (re-entry सिर्फ़ 20–38% configs में बेहतर), और stop + re-entry, signal-exit को लगभग कभी नहीं हराता।
- **1d, 1w:** लगभग आधे configs में drawdown घटता है, Sharpe लगभग वही।

## 5. Independent verification (अलग code, `src/audits/verify_btc_alltf_r2.py`)
**Cross-coin (हर confirmed config, हर coin पर replay; सबमें हर per-coin trade, equity और portfolio sum बराबर):**

| Job | Checks |
|---|---|
| futures 8h | 25/25 |
| futures 1d | 13/13 |
| controls | 10/10 |
| spot 1d | 10/10 |
| spot 15m | पहली बार 8/10; कारण F1 gate के floating-point ties (`R2_CODE_CHANGES_AFTER_LOCK.md` entry 6)। Tie handling के बाद 10/10 (1,122 tie bars, असली फ़र्क 0) |

**बाकी parts:**

| Part | Checks |
|---|---|
| tests | 9/9 |
| walk-forward | 25/25 |
| R1 positive control | 1/1 |
| re-entry | 16/16 |
| inputs (हर coin file का SHA) | 45/45 |
| mutation (जानबूझकर डाली गलतियाँ पकड़ी गईं) | 2/2 |
| BTC MTM (हर config का sum-check और sampled configs का loop-check) | 88/88 |

**Pre-lock code tests:** 566/566।

## 6. हमें क्या करना चाहिए
1. **SA, SB, SC का forward paper test 4–8 हफ़्ते चलाएँ** (FWD-R2 शुरू है; exact नियम, 30 coins frozen)।
   - Pass/fail lock है (`logs/live_paper_lpt1_2026_10_29/FWD_R2_PASSFAIL_PREREGISTERED.md`): ≥ 30 closed trades, forward CAGR > 0, Sharpe backtest के आधे से ऊपर, drawdown < 2× backtest। फ़ैसला 2026-12-24 को।
   - **Lock की देरी:** यह पहले forward trade (SB2 TRX) के दिखने के बाद lock हुआ, पहले नहीं। Thresholds उस trade से पहले ही इसी report में लिखे जा चुके थे; सिर्फ़ तारीख़ और 30 trades की शर्त नई है।
   - उसके बाद testnet, फिर आपकी हाँ से छोटा live (VM / ECO framework में)।
2. **Portfolio बनाएँ:** 10k account के लिए 20–30 liquid coins पर, हर trade पर 1% risk; spot (SA) और futures (SB, SC) अलग sleeves।
3. **ये दिशाएँ बंद करें:**
   - 1 घंटे से छोटे price-only नियम;
   - BTC पर parameter optimize करके winner चुनना;
   - रोज़ 10–15% का लक्ष्य।
4. **आगे की research (आपकी हाँ पर):**
   - futures short-timing (4h–1d) को एक pre-registered study में confirm करना;
   - promising patterns (RSI 20/80, VWAP-z mean-reversion) का forward test।

## 7. ईमानदार सीमाएँ
- **Coins पूरे नए नहीं हैं:** project पहले भी alt-coin trend देख चुका है। असली pristine सबूत सिर्फ़ forward data से आएगा।
- **Equal-weight portfolio सिर्फ़ एक नापने का तरीका है:** सैकड़ों coins एक साथ नहीं चलाए जा सकते, इसलिए per-coin breadth साथ में दी गई है।
- **Execution:** taker fill और 0.01% impact माने गए। छोटे coins पर slippage ज़्यादा होगा; इसीलिए 2× fee की जाँच की गई।
- **Futures data:** सिर्फ़ Binance perps (`data/futures_um`); किसी दूसरे exchange से मिलान नहीं किया गया। Forward test Bybit के bars पर चलता है, जहाँ दाम और funding थोड़ा अलग होंगे।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।
