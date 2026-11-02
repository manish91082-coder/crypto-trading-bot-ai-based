# BTC पर दिशा → entry → exit: timeframe के बिना, ज़मीनी जाँच (25 अक्टूबर 2026)

> **Discipline:**
> - Protocol नतीजों से पहले lock किया गया: `logs/research_btc_entry/BTC_ENTRY_PROTOCOL_PREREGISTERED.md`, SHA `f903dc19…`।
> - Code `src/research/btc_entry_study.py` है।
> - अलग verifier `src/audits/verify_btc_entry.py` के **6/6 PASS**। उसने raw data से loop चलाकर 500 barrier नतीजे, 300 signal values, हर final का हर holdout trade, और random control, सब दोबारा गिने।
> - नतीजे: `logs/research_btc_entry/BTC_ENTRY_RESULTS.json`।
> - **पुराना project reference में नहीं लिया गया।** इस्तेमाल हुए सिर्फ़ ये inputs:
>   - BTC का 5 मिनट data: 2020-01 → 2026-09, 7.1 लाख bars, SHA `65784492…`;
>   - BTC funding;
>   - fee की एक ही table: `deploy/fees.json`।
> - मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।

---

## 0. एक नज़र में (सीधा, ईमानदार जवाब)

| सवाल | Verified जवाब |
|---|---|
| BTC पर कोई ऐसा entry और दिशा का नियम है जो fee के बाद, **नए data पर** भी profit दे? | **नहीं मिला।** 12 families की **990** configurations test हुईं: momentum, reversal, breakout, z-score, RSI, squeeze, order flow, volume shock, funding, calendar और AI। Dev data पर सबसे अच्छी चुनी गई 10 में से **एक भी** holdout (2025–26) पर gates पास नहीं कर सकी |
| AI (gradient boosting, walk-forward) ने? | **खराब।** 1%/1% barrier पर dev में −0.064% प्रति trade, t = −4.3, यानी fee से भी नीचे |
| "Market हमेशा fee से ज़्यादा हिलता है" वाली बात? | हिलता ज़रूर है, पर दिशा **सिक्का उछालने जैसी** है। Random entry का नतीजा हर जगह लगभग −fee रहा |
| Sunday? | Sunday का औसत 1-घंटे का return बाकी दिनों से थोड़ा कम है (dev में 0.0017% बनाम 0.0077%), पर यह fee (0.092%) का 1/50 है। **Trade करने लायक नहीं** |
| "Perfect entry" का गणित? | Entry तभी profit देती है जब सही दिशा की संभावना p > p* हो (§1)। BTC पर किसी भी तरीके ने नए data पर p* पार नहीं किया |

---

## 1. गणित: कितना सही होना ज़रूरी है (break-even)

**Exit price-based है** (triple barrier), इसलिए timeframe का कोई मतलब नहीं रहता:
- TP: +a;
- SL: −b;
- अधिकतम 7 दिन।

Profit के लिए TP पहले लगने की संभावना कम से कम **p\* = (b + cost) / (a + b)** होनी चाहिए।

**Round-trip cost:**
- futures taker: 0.092%;
- spot: 0.17%;
- futures maker: 0.056%।

| TP / SL | Futures taker पर p\* | Spot पर p\* | Maker पर p\* |
|---|---|---|---|
| 0.5% / 0.5% | **59.2%** | 67.0% | 55.6% |
| 1% / 1% | **54.6%** | 58.5% | 52.8% |
| 2% / 2% | 52.3% | 54.3% | 51.4% |
| 4% / 4% | 51.2% | 52.1% | 50.7% |
| 2% / 1% (TP दोगुना) | 36.4% | 39.0% | 35.2% |
| 1% / 2% (SL दोगुना) | 69.7% | 72.3% | 68.5% |
| Volatility × 1 / × 2 / × 3 | 51.9% / 51.0% / 50.6% | 53.5% / 51.8% / 51.2% | n/a |

**मतलब:**
- **छोटा target** (0.5%, जो 5–15 मिनट में मिलता है) चाहिए, तो **10 में से 6 बार** सही दिशा पकड़नी पड़ेगी।
- **बड़ा target** (2–4%) चाहिए, तो सिर्फ़ 51–52%। पर नीचे दिखेगा कि BTC पर वह 1–2% की बढ़त भी नए data पर नहीं टिकती।

## 2. क्या test किया (सब pre-registered)

- **Entry:** decision bar के close के बाद, अगली bar का open। Future data का इस्तेमाल नहीं, और यह loop से जाँचा गया।
- **Exit:** 12 barrier sets: 9 fixed (0.5–4%) और 3 volatility-scaled।
  - अगर एक ही bar में TP और SL दोनों छुएँ, तो SL माना गया (conservative)।
  - Gap आए, तो उस bar के open पर fill।
- **Futures पर funding** का असली खर्च या कमाई जोड़ी गई।
- **Families:**

| Family | क्या |
|---|---|
| F0 | Random (control) |
| F1 | हमेशा long / हमेशा short |
| F2 / F3 | Momentum / reversal: 1h, 4h, 24h, 72h, 7d |
| F4 | Breakout (follow और fade) |
| F5 | Z-score (fade और follow) |
| F6 | RSI 5m / 1h / 4h (30/70 और 20/80) |
| F7 | Volatility squeeze |
| F8 | Order flow (taker-buy ratio) |
| F9 | Volume shock |
| F10 | Calendar: हफ़्ते का दिन × घंटा, 168 buckets |
| F11 | Funding extremes |
| F12 | AI: दो HGB classifiers, monthly walk-forward, सारे features |

- **Data के हिस्से:**
  - dev: 2020–2023, यहीं से चुनाव;
  - validation: 2024;
  - holdout: 2025-01 → 2026-09, सिर्फ़ एक बार खोला गया।

## 3. नतीजे

### 3.1 Dev पर हर family का हाल (futures taker cost)

| Family | Configs | Dev में positive | सबसे अच्छा t | Median net प्रति trade |
|---|---|---|---|---|
| F0 Random | 12 | 1 | 0.16 | −0.101% |
| F1 Drift | 24 | 4 | 1.36 | −0.102% |
| F2 Momentum | 180 | 33 | 1.98 | −0.107% |
| F3 Reversal | 180 | 16 | 1.09 | −0.107% |
| F4 Breakout | 96 | 14 | 1.81 | −0.107% |
| F5 Z-score | 144 | 22 | 2.32 | −0.106% |
| F6 RSI | 144 | 27 | 2.23 | −0.112% |
| F7 Squeeze | 12 | 1 | 0.68 | −0.096% |
| F8 Order flow | 144 | 18 | 2.56 | −0.105% |
| F9 Volume shock | 24 | 3 | 2.32 | −0.122% |
| F11 Funding | 24 | 6 | 1.24 | −0.112% |
| F12 AI | 6 | **0** | −0.43 | −0.121% |

- 990 में से सिर्फ़ 6 का t > 2 था, और t > 3 एक का भी नहीं। 990 tries में इतना तो सिर्फ़ किस्मत (noise) से भी आ जाता है।
- हर family का median लगभग **−0.10%** है, यानी ठीक fee जितना। **Signal ने दिशा में कोई मदद नहीं की।**

### 3.2 Dev से चुने गए 10 finals का holdout (2025-01 → 2026-09)

**Futures taker, net % प्रति trade:**

| Final | Dev (n, mean) | 2024 (n, mean) | **Holdout (n, mean)** | Holdout 95% CI | Random का 95वाँ % | TP-first दर बनाम p* |
|---|---|---|---|---|---|---|
| Z-score follow 48, k2, vol×3 | 289, +0.93% | 75, +0.45% | **127, −0.51%** | −1.56 … +0.48 | +0.68 | 26% बनाम 50.6% |
| Volume shock follow, vol×2 | 314, +0.74% | 87, +0.35% | **153, +0.28%** | −0.31 … +0.88 | +0.49 | 43% बनाम 50.9% |
| Z-score follow 48, k2, vol×2 | 410, +0.53% | 104, +0.32% | **171, −0.01%** | −0.65 … +0.62 | +0.46 | 39% बनाम 50.9% |
| Order flow follow 24h, 4%/4% | 535, +0.27% | 117, +0.30% | **138, −0.32%** | −0.85 … +0.25 | +0.45 | 38% बनाम 51.1% |
| RSI 4h follow, vol×1 | 397, +0.29% | 104, +0.20% | **148, −0.03%** | −0.50 … +0.38 | +0.29 | 51% बनाम 51.9% |
| RSI 5m follow, vol×2 | 407, +0.45% | 105, +0.34% | **179, −0.26%** | −0.89 … +0.31 | +0.44 | 37% बनाम 50.9% |
| Z-score follow 48, k3, vol×3 | 288, +0.71% | 74, +0.31% | **120, +0.12%** | −0.82 … +0.99 | +0.64 | 28% बनाम 50.6% |
| Volume shock follow, vol×3 | 241, +0.64% | 61, +0.97% | **107, −0.19%** | −1.24 … +0.87 | +0.72 | 28% बनाम 50.6% |
| हमेशा long, vol×3 | 288, +0.62% | 78, +1.03% | **127, −0.14%** | −1.10 … +0.80 | +0.09 | 24% बनाम 50.6% |
| Momentum 1h, vol×2 | 407, +0.34% | 105, +0.20% | **178, −0.08%** | −0.74 … +0.60 | +0.41 | 39% बनाम 50.9% |

- **एक भी final edge के सारे gates पास नहीं कर सका:**
  - G1: CI 0 से ऊपर;
  - G3: random से बेहतर;
  - G4: 2025 और 2026, दोनों में positive;
  - G5: DSR।
- **Maker fee पर भी** (जो fill की गारंटी नहीं देता) सबसे अच्छा volume shock +0.32% रहा, पर CI फिर भी 0 पार करता है।
- **Spot पर** (सिर्फ़ long) सारे 10 negative रहे।
- **ध्यान देने वाली बात:** dev पर ऊँचा दिखने वाला हर नियम 2024 में आधा हुआ, और 2025–26 में शून्य या negative। यही overfitting की पहचान है: पुराने data पर बहुत अच्छा, नए data पर ढेर।

### 3.3 Baselines (1%/1% barrier, futures taker)

| | Dev | 2024 | Holdout |
|---|---|---|---|
| Random दिशा | −0.113% (16,108 trades) | −0.101% | −0.092% |
| हमेशा long | −0.104% | −0.084% | −0.099% |
| हमेशा short | −0.098% | −0.103% | −0.087% |

यह साफ़ गणित है: बिना किसी edge के हर trade लगभग **fee जितना** घाटा देता है।

### 3.4 AI (F12)

| AI config | Dev n, mean, t | 2024 mean |
|---|---|---|
| 1%/1%, margin 0 | 5,346, −0.064%, **t −4.27** | −0.098% |
| 1%/1%, margin 0.05 | 2,419, −0.067%, t −3.20 | −0.159% |
| vol×2, margin 0 | 260, −0.168%, t −0.47 | +0.065% |

AI ने fee से ऊपर कोई दिशा नहीं पहचानी। जहाँ trades ज़्यादा थे, वहाँ नतीजा साफ़ negative रहा।

### 3.5 Calendar / Sunday (F10, 1 घंटे की entry और exit)

- 168 में से किसी भी (दिन, घंटा) bucket का dev में t > 2 नहीं था। Dev के सबसे अच्छे 3 buckets 2024 और holdout में negative हो गए।
- Dev की दिशा से सारे buckets trade करें, तो dev में भी −0.053% प्रति trade (t −9.6), और holdout में −0.087%।
- **Sunday:** trade करने पर हर अवधि में negative रहा (dev −0.052%, holdout −0.091%)।
- यह Baur et al. की peer-reviewed study से मेल खाता है: BTC में समय वाले patterns स्थिर नहीं रहते।

## 4. इसका मतलब (शांत दिमाग से)

1. **BTC की अकेले timing**, यानी "कब खरीदें, कब बेचें", fee के बाद **किसी भी तरीके से नए data पर साबित नहीं हुई।** इनमें 990 indicator और AI तरीके, और 5 मिनट से 7 दिन तक के holds शामिल थे।
   - यह किसी code की गलती नहीं है। 500 random barrier नतीजे और हर trade loop से दोबारा गिने गए, और सब मेल खाए।
   - **यह market की हक़ीक़त है:** BTC बहुत liquid है, लाखों लोग और bots यही signals देखते हैं, इसलिए आसान दिशा वाला edge टिकता नहीं।
2. **"Perfect entry" कोई indicator नहीं देता।** Entry का गणित p > p* है, और BTC पर p ~ 50% रहता है।
3. **जहाँ अगली research करनी चाहिए** (हर एक के लिए नया pre-registered protocol, और कोई वादा नहीं):
   - **(a) Relative strength:** कई coins में "कौन ज़्यादा मज़बूत है" पर long/short, ताकि market की दिशा का अनुमान ही न लगाना पड़े। Academic सबूत: Liu, Tsyvinski & Wu (2022, Journal of Finance), cross-sectional momentum।
   - **(b) Structural कमाई, जिसमें दिशा नहीं चाहिए:** funding carry और basis। कमाई छोटी है, पर दिशा पर निर्भर नहीं।
   - **(c) Maker execution:** fee आधी से कम हो जाती है (p* 52.8% बनाम 54.6%)। इसके लिए live order-book data चाहिए, और fill न होने का खतरा मापना होगा।
   - **(d) BTC का इस्तेमाल दिशा के लिए नहीं, सिर्फ़ risk filter के रूप में।**

## 5. सीमाएँ

- **Futures का भाव spot data से लिया गया** (BTC perp और spot लगभग बराबर चलते हैं)। Funding असली है।
- **TP/SL ठीक level पर fill माने गए।** Gap आने पर open पर fill लिया गया। असली slippage थोड़ा और बुरा कर सकता है।
- **Random control:** लंबे hold (vol × 3) में holdout में उतने बिना-overlap वाले trades नहीं समाते, इसलिए control का औसत कम trades पर बना। Study और verifier में यह एक जैसा है, और नतीजा नहीं बदलता, क्योंकि G1 पहले ही fail है।
- **सिर्फ़ BTC।** Altcoins अलग चल सकते हैं।
- **Lookahead:** code लिखते समय 1h/4h RSI में एक lookahead गलती पकड़ी गई, जिसमें अधूरी bar शामिल हो सकती थी। उसे run से **पहले** ठीक किया गया (`closed="left"`)।

## 6. Verification

| Check | नतीजा |
|---|---|
| V1 | Inputs के SHA ✅ |
| V2 | 500 random (bar, barrier) long+short नतीजे bar loop से: 0 mismatch ✅। साथ में V2b: 100 bars पर σ24 ✅ |
| V3 | 300 random signal values (momentum, breakout, z-score, taker-buy ratio) loops से ✅ |
| V4 | 10 finals के holdout का हर trade दोबारा चलाया (outcome, exit, overlap, funding, net, n, mean, साल-दर-साल) ✅ |
| V5 | Random control (200 seeds) दोबारा: p95 0.006838 = report ✅ |
| Smoke test | Barrier engine बनाम सीधा loop: 400/400 मेल (study से पहले) |

Verifier की अपनी दो bugs (numpy int, और npz का बार-बार पढ़ा जाना) ठीक कीं। Study के किसी नतीजे पर इनका असर नहीं था।

## 7. Sources

- Baur, Cahill, Godfrey & Liu: *Bitcoin time-of-day, day-of-week and month-of-year effects*: https://research-repository.uwa.edu.au/en/publications/bitcoin-time-of-day-day-of-week-and-month-of-year-effects-in-retu/
- Shen, Urquhart & Wang (2022): *Bitcoin intraday time series momentum*: https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/
- De Nicola (2021, Ledger): BTC में 1–4 घंटे का mean reversion: https://ledger.pitt.edu/ojs/ledger/article/download/213/212/1232
- BTC order flow: https://arxiv.org/pdf/2108.09750
- Triple-barrier labeling (López de Prado का concept, secondary reference): https://mizarlabs.readthedocs.io/en/latest/mizarlabs.transformers.targets.html
- Liu, Tsyvinski & Wu: *Common Risk Factors in Cryptocurrency*: https://www.nber.org/papers/w25882.pdf

*मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।*
