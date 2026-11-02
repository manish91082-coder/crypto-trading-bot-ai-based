# Live AI Decision System: design (refined), factors और मौजूदा desk में integration — 29 Oct 2026

## 1. आपकी माँग (refined रूप में)
एक ऐसा system जो live market पर लगातार चले और:
1. **हर timeframe का पूरा data पढ़े:** 1m से 1d तक price, volume, order book, futures positioning।
2. **Market के बाहर की दुनिया भी देखे:** macro calendar (US data, Fed, ECB, BOJ), news, बाकी बाज़ार (stocks, dollar, yields, gold) और crypto का mood (Fear & Greed)।
3. **"अभी कौन सी स्थिति है" पहचाने:** trend, range, high-vol, event-risk, panic या euphoria।
4. **उस स्थिति के लिए सही strategy चुने,** या "आज चुप बैठो" कहे।
5. **हर trade का पूरा plan बनाए:**
   - spot या futures, long या short;
   - entry, stop-loss, target, trailing stop, time stop;
   - position size, leverage, risk %।
6. **Entry के बाद लगातार देखे:** exit, trail, या news आने पर बचाव।
7. **पुरानी learning और current स्थिति,** दोनों से फ़ैसला ले। सिर्फ़ fixed formula नहीं।

## 2. सबसे ज़रूरी सिद्धांत (सबूत पर आधारित)
- **AI को मनमाना trader नहीं, "निर्णायक + पहरेदार" बनाना है।**
  - Numbers से सीधे "अगला price" निकालने में LLM अच्छे नहीं हैं, और यह project बार-बार दिखा चुका है कि छोटे timeframe पर price-only edge fee से छोटा है।
  - LLM की असली ताक़त context समझना है: news, calendar, और कई signals का आपस में टकराना।
  - इसलिए **trade की "बढ़त" verified strategies से आती है,** और AI तय करता है कि इस स्थिति में कौन सी चलानी है, कौन सी नहीं, और कितने size पर।
- **Hard risk rules code में होंगे, AI की बात से ऊपर।** AI इन्हें तोड़ नहीं सकता:
  - 1% risk per trade, −3% per day;
  - leverage stop से निकलता है, AI की मर्ज़ी से नहीं;
  - बड़ी news से पहले blackout।
- **हर AI फ़ैसला result से पहले लिखा जाएगा।** फिर उसकी तुलना होगी:
  - (a) सिर्फ़ rules वाले system से;
  - (b) random से।
  - AI तभी "skill" कहलाएगा जब वह इन दोनों को statistically हराए।

## 3. Factors (सब live, सब log में)
| Block | Factors | Source (इस laptop से जाँचे गए) |
|---|---|---|
| Price structure, हर TF (5m 15m 1h 4h 1d) | trend (EMA20/50), RSI, ATR %, 1 और 10 bar का return, VWAP, prior-day high/low, day high/low, swing levels | Binance spot (data-api.binance.vision) |
| Flow | volume ratio, taker-buy share, order book imbalance, spread | Binance spot |
| Derivatives positioning | funding rate, OI बदलाव (1h, 24h), long/short ratio, basis | Bybit linear (Binance futures API यहाँ से blocked है) |
| Macro calendar | अगला high-impact event और उसमें बचे मिनट (US, ECB, BOJ…), forecast vs previous, blackout ±30 min | ForexFactory weekly JSON |
| बाकी बाज़ार | S&P 500, Nasdaq futures, DXY, US 10Y, gold | Yahoo chart API |
| Crypto-wide | कुल market cap 24h, BTC dominance, Fear & Greed (आज / कल / 7 दिन) | CoinGecko, alternative.me |
| News | CoinDesk, Cointelegraph, Bybit announcements (12h), keyword tags (risk-off / risk-on / macro / regulation); मतलब AI खुद पढ़ता है | RSS / API |
| Regime | TREND_UP / TREND_DOWN / RANGE × LOW / NORMAL / HIGH vol (लिखा हुआ नियम) | context engine |
| Strategy signals | R2-confirmed strategies की live स्थिति: entry / exit / in-state | signal engine (locked rules) |
| Forecasts | PRED-1 models की live verified skill | PRED-1 verifier |
| अपना account | equity, आज का P&L, खुली positions, लगातार losses | LPT-1 ledger |

## 4. Architecture
```
 [Data layer]  live klines हर TF, book, futures, calendar, cross-asset, news, sentiment
       │  (हर run पर sha256 के साथ save)
 [Context engine]  src/live_paper/context.py  ─▶ एक structured state (JSON)
       │
 [Strategy engines]  verified strategies (locked rules)  ─▶ candidate signals
       │             src/live_paper/signals.py
 [AI decision layer]  state + candidates + news + calendar ─▶ फ़ैसला (JSON):
       │   regime, कौन सी strategy, या STAND ASIDE; market (spot/futures), दिशा,
       │   entry, stop, target, trailing नियम, size (risk %), कारण
 [Risk manager]  code: hard limits, blackout, max positions, gross leverage → veto
       │
 [Execution]  paper (अभी) → testnet → छोटा live (हर step आपकी हाँ से)
       │
 [Journal + verifier]  hash-chained logs, official data से fills की जाँच
       │
 [Learning loop]  हफ़्ते का review: कौन सी strategy किस regime में चली,
                  AI ने rules से बेहतर किया या नहीं। बदलाव सिर्फ़ नए
                  pre-registered protocol से, कभी चुपचाप नहीं।
```

## 5. फ़ैसले के नियम
**1. "चुप बैठो" के नियम (AI इन्हें override नहीं कर सकता):**
- macro blackout (±30 min high-impact US event);
- spread > 5 bps;
- ATR1h < 0.3%;
- दिन का −3%;
- 2 लगातार loss के बाद 60 min।

**2. Regime → strategy map** (शुरुआत; data से बदलेगा):

| Regime | Strategy |
|---|---|
| TREND_UP | SA dip-buy (15m, SMA200 के ऊपर), SB RSI momentum (8h), intraday trend pullback long (playbook A) |
| TREND_DOWN | futures short pullbacks (playbook A, short side); spot में कुछ नहीं |
| RANGE | सिर्फ़ range edges पर fade, या चुप बैठो |
| HIGH_VOL + news risk-off | size आधा, या चुप |

**3. Spot या futures:**
- **Spot:** लंबे hold, liquidation का डर नहीं।
- **Futures:** short चाहिए, या fee कम चाहिए (0.036% vs 0.075%)।

**4. Leverage:** AI नहीं चुनता। Size = (risk % × equity) / stop-distance। Leverage = notional / margin, और 3x की सीमा।

**5. Trailing:** strategy का अपना नियम (R2 में जाँचा गया: X4 trail 3×ATR या signal exit)। AI सिर्फ़ कस सकता है, ढीला नहीं कर सकता।

**6. News आने पर:** risk-off खबर (hack, ban, बड़ा liquidation) या surprise macro पर AI खुली positions का stop कस सकता है या बंद कर सकता है। नई entry अगली candle की पुष्टि तक नहीं।

## 6. अब तक का verified evidence (इसी पर system खड़ा होगा)
**कौन सी strategies confirm हुईं** (R2: BTC से चुनी गईं, फिर सैकड़ों दूसरे coins पर out-of-sample; controls साफ़: random 0% झूठे PASS, oracle 92% पकड़ा गया):

| Strategy | CAGR | Sharpe | DD | दूसरे coins पर |
|---|---|---|---|---|
| SA (spot 15m dip-buy) | 18.8% | 2.10 | 12% | 278 में से 203 पर profit |
| SB (futures 8h RSI > 80 momentum) | 15–18% | ~1.5 | 8–9% | — |
| SC (futures 1d CHOP + volume) | 14% | 1.55 | 9% | — |

ये सालाना 14–19% वाली हैं, रोज़ 10% वाली नहीं।

**Intraday price prediction (PRED-1):** अभी कोई model naive से बेहतर साबित नहीं हुआ। जाँच जारी है।

**ऊँचे timeframe पर in-sample winners:** walk-forward में आगे नहीं टिके। इसलिए "पिछले महीने जो चला वही चलाओ" का तरीका काम नहीं करता।

## 7. मौजूदा desk में integration (चरणबद्ध)
**Phase 1 (आज, बन गया)**
- **Context engine** (`context.py`): ऊपर के सारे factors, एक command में।
- **Signal engine** (`signals.py`): confirmed strategies live, locked rules से।
- **Forward tracker** (`forward_r2.py`, अगला): confirmed strategies के paper trades exact नियम से।
  - Entry अगले bar के open पर; कोई मनमानी नहीं।
  - यह R2 का असली forward test है।
- **AI decision layer अभी मैं हूँ** (इसी session में Claude)। हर फ़ैसले से पहले context + signals पढ़ता हूँ, और फ़ैसला कारण सहित hash-chained log में लिखता हूँ।

**Phase 2 (आपकी हाँ के बाद)**
- **कहाँ:** VM पर एक autonomous agent loop, हर 5–15 min; Claude API state पढ़कर JSON फ़ैसला देगा।
- **क्या चाहिए:**
  - आपकी API key (आप ख़ुद VM के .env में रखेंगे; मैं key नहीं छूऊँगा);
  - crontab / service की मंज़ूरी।
- **Shadow mode पहले:** AI के फ़ैसले, rules-only फ़ैसले और random, तीनों साथ में log होंगे।

**Phase 3 (सबूत के बाद)**
- ≥ 60 फ़ैसलों पर AI rules-only और random दोनों को हराए (p ≤ 0.05), तभी testnet, फिर छोटा live।
- हर step पर आपकी हाँ।

## 8. ईमानदार सीमाएँ
- **AI की समझ भी गलत हो सकती है;** news का असर अक्सर पहले ही price में आ चुका होता है। इसलिए measurement ज़रूरी है।
- **10–15% रोज़ का लक्ष्य** इस design से भी नहीं बदलता। गणित (§ research report) वही है। System का लक्ष्य टिकाऊ, verified, fee के बाद positive edge है।
- **Futures data Bybit से proxy है,** क्योंकि Binance futures endpoints इस laptop से blocked हैं।

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research और paper trading है, निवेश सलाह नहीं।
