# दिशा, entry और exit के हर संभव तरीके: पूरा catalog (26 अक्टूबर 2026)

> **यह file data को छुए बिना बनी है:** सिर्फ़ तरीकों की सूची, कोई नतीजा नहीं। Testing इसके बाद एक-एक करके, lock किए गए protocol से होगी।
>
> **Saturation कैसे पक्का किया:** सूची 4 rounds में तीन स्वतंत्र स्रोतों से मिलाई गई (§8):
> - TA-Lib की पूरी function list;
> - Fang et al. (2022) का crypto trading survey;
> - López de Prado और Kaufman की taxonomy।
>
> आखिरी round में कुछ नया नहीं जुड़ा।
>
> **हर तरीके के साथ "Data" कॉलम:**
> - **✅** हमारे पास data है, अभी test हो सकता है;
> - **🟡** data है, पर library या थोड़ा काम चाहिए;
> - **❌** data हमारे पास नहीं है (download करना पड़ेगा, आपकी अनुमति से)।
>
> **हमारा data:**
> - BTC 5m spot OHLCV + taker-buy volume (2020-01 → 2026-09);
> - BTC perp 1h + funding;
> - BTC daily OI, long/short ratios, premium (basis);
> - दूसरे coins के bars (cross-asset के लिए)।
>
> Fee: `deploy/fees.json`।

---

## भाग A: दिशा पहचानने के तरीके (market ऊपर जाएगा या नीचे)

### A1. Trend-following (trend के साथ चलना)
| ID | तरीका | Data |
|---|---|---|
| A1.01 | Moving averages: SMA, EMA, WMA, DEMA, TEMA, TRIMA, T3, KAMA, MAMA, HMA, ALMA, VWMA, ZLEMA। Price बनाम MA, MA का slope | ✅ |
| A1.02 | दो MA का crossover (fast/slow), MA ribbon (कई MA एक क्रम में) | ✅ |
| A1.03 | MACD (line, signal, histogram), MACDEXT, MACDFIX, PPO, APO | ✅ |
| A1.04 | ADX, +DI/−DI, DX, ADXR (trend की ताकत और दिशा) | ✅ |
| A1.05 | Aroon, Aroon oscillator | ✅ |
| A1.06 | Parabolic SAR, SAREXT | ✅ |
| A1.07 | Supertrend (ATR band) | ✅ |
| A1.08 | Ichimoku: Tenkan/Kijun cross, cloud के ऊपर/नीचे, Chikou | ✅ |
| A1.09 | Donchian channel breakout (N-period high/low) | ✅ |
| A1.10 | Keltner channel breakout | ✅ |
| A1.11 | Linear regression: slope, angle, TSF forecast, R² | ✅ |
| A1.12 | Hilbert transform trendline / trend-vs-cycle mode | ✅ (खुद लिखना होगा) |
| A1.13 | Vortex indicator | ✅ |
| A1.14 | TRIX, KST (Know Sure Thing) | ✅ |
| A1.15 | Heikin-Ashi candle का रंग और क्रम | ✅ |
| A1.16 | **बिना timeframe वाले bars:** Renko, Kagi, Point & Figure, range bars। Price के तय move पर नई bar बनती है | ✅ |
| A1.17 | Time-series momentum: पिछले N का return positive → long | ✅ |
| A1.18 | Kaufman efficiency ratio (trend कितना साफ़ है) | ✅ |
| A1.19 | Choppiness index (trend बनाम sideways) | ✅ |
| A1.20 | Hurst exponent / DFA (trend टिकेगा या पलटेगा) | ✅ (खुद लिखना होगा) |

### A2. Mean-reversion / oscillators (हद से ज़्यादा ऊपर या नीचे → वापसी)
| ID | तरीका | Data |
|---|---|---|
| A2.01 | RSI (Wilder), Connors RSI, RSI divergence | ✅ |
| A2.02 | Stochastic (slow/fast), StochRSI | ✅ |
| A2.03 | Williams %R | ✅ |
| A2.04 | CCI (Commodity Channel Index) | ✅ |
| A2.05 | CMO (Chande), Ultimate Oscillator | ✅ |
| A2.06 | MFI (Money Flow Index), BOP (Balance of Power) | ✅ |
| A2.07 | ROC / ROCP / ROCR / MOM (rate of change) | ✅ |
| A2.08 | Bollinger %B, bandwidth, band touch | ✅ |
| A2.09 | Z-score (price बनाम rolling mean) | ✅ |
| A2.10 | MACD / RSI divergence (price नया high, indicator नहीं) | ✅ |
| A2.11 | Fisher transform, inverse Fisher | ✅ |
| A2.12 | DPO (Detrended Price Oscillator) | ✅ |
| A2.13 | Awesome / Accelerator oscillator (Bill Williams) | ✅ |
| A2.14 | Elder Ray (bull/bear power), Force index | ✅ |
| A2.15 | Coppock curve, TSI (True Strength Index) | ✅ |
| A2.16 | Ornstein-Uhlenbeck fit: half-life, Bertram की optimal bands | ✅ (खुद लिखना होगा) |
| A2.17 | VWAP से दूरी (z), anchored VWAP | ✅ |

### A3. Volatility regime (market कितना हिल रहा है)
| ID | तरीका | Data |
|---|---|---|
| A3.01 | ATR, NATR, True Range | ✅ |
| A3.02 | Realized vol, EWMA vol | ✅ |
| A3.03 | Range-based estimators: Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang | ✅ |
| A3.04 | GARCH(1,1) / EGARCH / GJR forecast | 🟡 (scipy से खुद लिखना होगा) |
| A3.05 | Squeeze: Bollinger, Keltner के अंदर, फिर बाहर निकलना | ✅ |
| A3.06 | NR4 / NR7 (सबसे छोटी range), inside bar के बाद breakout | ✅ |
| A3.07 | Volatility breakout (Larry Williams: open ± k × पिछली range) | ✅ |
| A3.08 | Vol of vol, realized skewness / kurtosis | ✅ |
| A3.09 | Jump detection (bipower variation, BNS test) | ✅ (खुद लिखना होगा) |

### A4. Volume और order flow (कौन ज़्यादा ज़ोर से खरीद या बेच रहा है)
| ID | तरीका | Data |
|---|---|---|
| A4.01 | OBV, Chaikin A/D line, A/D oscillator, CMF | ✅ |
| A4.02 | VPT (Volume Price Trend), Ease of Movement, Klinger | ✅ |
| A4.03 | NVI / PVI (negative/positive volume index) | ✅ |
| A4.04 | Taker-buy ratio / buy-sell imbalance (CVD proxy) | ✅ |
| A4.05 | Trade count intensity (trades per bar) | ✅ |
| A4.06 | Volume shock / relative volume | ✅ |
| A4.07 | Volume profile: POC, value area (high/low) | ✅ (5m से approximate) |
| A4.08 | VPIN (toxic flow) | ✅ (bars से approximate) |
| A4.09 | Kyle's lambda, Amihud illiquidity, Roll spread estimator | ✅ |
| A4.10 | **बिना timeframe वाले bars:** volume bars, dollar bars, imbalance / run bars (López de Prado) | ✅ |
| A4.11 | Order book imbalance, queue imbalance (L2) | ❌ इतिहास नहीं है (हमारा collector सिर्फ़ forward snapshots लेता है) |
| A4.12 | Trade-by-trade aggressor flow (aggTrades) | ❌ (Binance से download हो सकता है) |

### A5. Market structure / price action
| ID | तरीका | Data |
|---|---|---|
| A5.01 | Swing structure: HH/HL (uptrend), LH/LL (downtrend), break of structure | ✅ |
| A5.02 | Support/resistance: pivot points (classic, Fibonacci, Camarilla, Woodie), पिछले swing levels | ✅ |
| A5.03 | Round numbers (60k, 65k...) पर बर्ताव | ✅ |
| A5.04 | Fibonacci retracement / extension | ✅ |
| A5.05 | Trendline break (swings से automatic) | ✅ |
| A5.06 | SMC: order blocks, fair value gaps, liquidity sweep (stop hunt) | ✅ |
| A5.07 | Inside / outside bar, pin bar | ✅ |
| A5.08 | Opening range breakout (UTC दिन / session की शुरुआत) | ✅ |
| A5.09 | Candlestick patterns: TA-Lib के सभी 61 (engulfing, hammer, doji, morning star, three soldiers...) | ✅ (खुद लिखना होगा) |
| A5.10 | Chart patterns: head & shoulders, double top/bottom, triangle, flag, wedge, cup & handle | ✅ (algorithm से पहचान) |
| A5.11 | Harmonic patterns (Gartley, Bat, Butterfly, Crab) | ✅ |
| A5.12 | Elliott wave (automatic counting) | 🟡 (subjective, सीमित परिभाषा से) |
| A5.13 | Wyckoff phases (accumulation/distribution) | 🟡 (परिभाषा से) |
| A5.14 | CME gap fill | ❌ (CME data नहीं है) |

### A6. Statistics और econometrics
| ID | तरीका | Data |
|---|---|---|
| A6.01 | AR(p) / ARIMA forecast | ✅ (OLS से खुद लिखना होगा) |
| A6.02 | Variance ratio, autocorrelation, runs test (random walk से फ़र्क) | ✅ |
| A6.03 | Kalman filter (trend और slope) | ✅ |
| A6.04 | Hidden Markov Model: 2–3 regimes (bull/bear/sideways) | ✅ (EM खुद लिखना होगा) |
| A6.05 | Markov switching regression | 🟡 |
| A6.06 | Change-point detection: CUSUM, Bayesian online | ✅ |
| A6.07 | Fourier / spectral cycles, Hilbert dominant cycle | ✅ |
| A6.08 | Wavelet decomposition | 🟡 (pywt नहीं है, खुद लिखना होगा) |
| A6.09 | Entropy: sample, approximate, permutation (predictability का माप) | ✅ |
| A6.10 | Fractal dimension, Hurst / DFA | ✅ |
| A6.11 | Cointegration / pairs: BTC–ETH spread | ✅ (ETH bars से) |
| A6.12 | VAR / Granger: ETH या altcoins BTC से पहले चलते हैं? | ✅ |
| A6.13 | Bubble tests: LPPLS, SADF/GSADF (explosive root) | ✅ (खुद लिखना होगा) |
| A6.14 | Quantile regression, extreme value (EVT tail) | ✅ |

### A7. Derivatives और positioning
| ID | तरीका | Data |
|---|---|---|
| A7.01 | Funding rate: level, बदलाव, extremes | ✅ |
| A7.02 | Open interest का बदलाव, OI बनाम price divergence | ✅ (BTC daily metrics) |
| A7.03 | Basis / premium (perp − spot) | ✅ (daily premium + perp 1h बनाम spot) |
| A7.04 | Long/short ratio: global accounts, top traders | ✅ (daily) |
| A7.05 | Taker long/short ratio (futures) | ✅ (daily metrics) |
| A7.06 | Liquidation data (बड़े liquidation के बाद पलटाव) | ❌ |
| A7.07 | Options: IV, 25-delta skew, put/call ratio, term structure, max pain | ❌ इतिहास नहीं है (सिर्फ़ forward collector) |
| A7.08 | CME basis / CME COT positioning | ❌ |

### A8. Cross-asset / lead-lag
| ID | तरीका | Data |
|---|---|---|
| A8.01 | ETH/BTC ratio trend | ✅ |
| A8.02 | Altcoin breadth (% coins अपने MA के ऊपर), दूसरे coins का momentum | ✅ |
| A8.03 | BTC dominance (proxy: BTC बनाम बाकी coins का volume/marketcap) | 🟡 (marketcap data नहीं, volume proxy) |
| A8.04 | Stocks (S&P 500, Nasdaq), DXY, gold, US yields, VIX | ❌ |
| A8.05 | Coinbase premium, Kimchi premium, exchanges के बीच spread | ❌ |
| A8.06 | Stablecoin supply / flows | ❌ |

### A9. On-chain
| ID | तरीका | Data |
|---|---|---|
| A9.01 | Exchange net flows, whale transfers | ❌ |
| A9.02 | MVRV, SOPR, NUPL, realized price | ❌ |
| A9.03 | Hash rate, miner flows, Puell multiple | ❌ |
| A9.04 | Active addresses, NVT | ❌ |

### A10. Sentiment / attention
| ID | तरीका | Data |
|---|---|---|
| A10.01 | Fear & Greed index | ❌ (public API, download हो सकता है) |
| A10.02 | Google Trends | ❌ |
| A10.03 | Twitter/X, Reddit sentiment | ❌ |
| A10.04 | News NLP / LLM headline scoring | ❌ |

### A11. Calendar / events
| ID | तरीका | Data |
|---|---|---|
| A11.01 | Hour of day, day of week (Sunday), month, weekend | ✅ |
| A11.02 | Session opens: Asia, Europe, US, और US stock market का open/close | ✅ |
| A11.03 | Funding settlement के आसपास (00/08/16 UTC) | ✅ |
| A11.04 | Options expiry (Deribit, हर शुक्रवार 08:00 UTC; महीने का आखिरी शुक्रवार) | ✅ (तारीखें गणना से) |
| A11.05 | Month-end / quarter-end | ✅ |
| A11.06 | FOMC, CPI जैसे macro events | ❌ (event calendar चाहिए) |
| A11.07 | Halving cycle phase | ✅ (तारीखें ज्ञात हैं) |

### A12. AI: supervised machine learning
| ID | तरीका | Data / library |
|---|---|---|
| A12.01 | Logistic regression (L1/L2), LDA, QDA, Naive Bayes | ✅ sklearn |
| A12.02 | kNN, SVM (linear/RBF) | ✅ sklearn |
| A12.03 | Decision tree, Random Forest, Extra Trees | ✅ sklearn |
| A12.04 | Gradient boosting: sklearn HGB, XGBoost | ✅ |
| A12.05 | LightGBM, CatBoost | 🟡 (install चाहिए) |
| A12.06 | AdaBoost | ✅ |
| A12.07 | MLP (simple neural network) | ✅ sklearn |
| A12.08 | LSTM, GRU, 1D-CNN, TCN | 🟡 (torch install चाहिए) |
| A12.09 | Transformer / Temporal Fusion Transformer, N-BEATS | 🟡 (torch चाहिए) |
| A12.10 | Stacking / voting ensemble | ✅ |
| A12.11 | Meta-labeling: primary signal + second model तय करे कि trade लें या नहीं | ✅ |
| A12.12 | Labeling के तरीके: triple barrier, trend scanning, fixed horizon | ✅ |
| A12.13 | Validation के तरीके: purged k-fold, walk-forward, combinatorial purged CV | ✅ |
| A12.14 | Feature selection: permutation importance, SHAP-जैसा, mutual information | ✅ |

### A13. AI: बाकी
| ID | तरीका | Data / library |
|---|---|---|
| A13.01 | Unsupervised regimes: k-means, Gaussian mixture | ✅ sklearn |
| A13.02 | PCA factors, autoencoder anomaly | ✅ / 🟡 |
| A13.03 | Genetic programming: rules का evolution | ✅ (खुद लिखना होगा) |
| A13.04 | Reinforcement learning: DQN, PPO, A2C | 🟡 (torch/gym चाहिए) |
| A13.05 | Bayesian models (online updating) | ✅ |
| A13.06 | LLM agents (news और chart पढ़कर फ़ैसला) | ❌ |

### A14. Combinations
| ID | तरीका |
|---|---|
| A14.01 | कई indicators की voting (majority / weighted) |
| A14.02 | Regime-switch: trend regime में trend-following, sideways regime में mean-reversion |
| A14.03 | Multi-horizon confluence (कई horizons एक ही दिशा में) |
| A14.04 | Filters: volatility / liquidity / funding filter लगाकर पुराना signal |

---

## भाग B: Entry के तरीके (दिशा तय होने के बाद, "कब और कैसे घुसें")

| ID | तरीका | Data |
|---|---|---|
| B.01 | Signal पर तुरंत market order (अगली bar का open) | ✅ |
| B.02 | Pullback limit: MA, VWAP या x% / k×ATR नीचे (long के लिए) | ✅ (fill की शर्त low ≤ limit) |
| B.03 | Breakout stop-entry: पिछले high के ऊपर buy-stop | ✅ |
| B.04 | Confirmation: level के पार close, या 2 bars की पुष्टि | ✅ |
| B.05 | Retest entry: breakout के बाद level पर लौटने पर | ✅ |
| B.06 | Scale-in / pyramiding: profit में आने पर और जोड़ना | ✅ |
| B.07 | Averaging down / DCA / grid | ✅ |
| B.08 | TWAP: कई हिस्सों में entry | ✅ |
| B.09 | Volatility-gated: ATR फैलने या सिकुड़ने का इंतज़ार | ✅ |
| B.10 | Liquidity-sweep entry: stop-hunt wick के बाद | ✅ |
| B.11 | Band-touch entry (mean reversion: Bollinger/Keltner को छूना) | ✅ |
| B.12 | Maker-only (post-only limit, कम fee; fill न होने का खतरा) | ✅ (bars से approximate, असली queue नहीं) |
| B.13 | Order-book-timed entry (queue imbalance) | ❌ |
| B.14 | SPRT / Bayesian confirmation (संभावना threshold पार होने पर) | ✅ |

## भाग C: Exit के तरीके

| ID | तरीका | Data |
|---|---|---|
| C.01 | Fixed % TP / SL | ✅ |
| C.02 | ATR-multiple TP / SL | ✅ |
| C.03 | Volatility-scaled (σ) TP / SL | ✅ |
| C.04 | Risk-reward ratios (1:1, 1:2, 2:1, 1:3) | ✅ |
| C.05 | Trailing stop: %, ATR, chandelier, Parabolic SAR, MA trailing, Donchian low | ✅ |
| C.06 | Breakeven stop: +x पर SL को entry पर ले आना | ✅ |
| C.07 | Time stop (N घंटे या दिन बाद) | ✅ |
| C.08 | Signal-reversal exit (उल्टा signal आने पर) | ✅ |
| C.09 | Partial profit / scale-out | ✅ |
| C.10 | Indicator exit (जैसे RSI वापस 50 पर) | ✅ |
| C.11 | Volatility-contraction exit | ✅ |
| C.12 | MAE/MFE-आधारित stop और target (पुराने trades के adverse excursion से) | ✅ |
| C.13 | Profit lock (peak से x% गिरने पर) | ✅ |
| C.14 | Support/resistance target | ✅ |
| C.15 | Optimal stopping: Bertram OU bands, dynamic programming | ✅ (खुद लिखना होगा) |

## भाग D: फ़ैसले के गणितीय सूत्र (सभी तरीकों पर लागू)

| ID | सूत्र | काम |
|---|---|---|
| D.01 | Expected value: E = p·W − (1−p)·L − c | हर trade की कमाई |
| D.02 | Break-even: p* = (L + c) / (W + L) | कितनी accuracy चाहिए |
| D.03 | Kelly: f* = p/L − (1−p)/W; fractional Kelly | position size |
| D.04 | Risk of ruin, optimal f | डूबने का खतरा |
| D.05 | Sharpe, Sortino, Calmar, profit factor, expectancy | ranking |
| D.06 | Deflated Sharpe (DSR), PBO (overfitting की संभावना) | कई tries के बाद भी असली? |
| D.07 | Bootstrap CI (week blocks), random-entry control | किस्मत बनाम skill |
| D.08 | SPRT (sequential test) | Live में जल्दी पहचानना कि edge है या नहीं |

---

## Testing के लिए गिनती

*ये नंबर file की rows को program से गिनकर निकाले गए हैं।*
- पहले version में यह table गिने बिना लिखी गई थी (136 / 101 / 12 / 23)। वह गलत थी, और 26 अक्टूबर को ही सुधारी गई।
- एक row में कई indicators हो सकते हैं: A1.01 में 13 moving averages हैं, और A5.09 में 61 candlestick patterns।

| श्रेणी | कुल rows | ✅ अभी test हो सकते हैं | 🟡 library/काम चाहिए | ❌ data नहीं |
|---|---|---|---|---|
| A दिशा | 139 | 109 (105 + A14 के 4 combinations) | 11 (A13.02 आधा ✅) | 19 |
| B entry | 14 | 13 | 0 | 1 |
| C exit | 15 | 15 | 0 | 0 |
| D गणित | 8 | सभी पर लागू (tags नहीं) | n/a | n/a |

**(✅ + 🟡) वाले सारे तरीके test होंगे।**
- 🟡 वाले numpy/sklearn से या मंज़ूर install के बाद।
- ❌ वाले data download की आपकी अनुमति के बाद, अलग batch में।

---

## 8. Saturation log

| Round | स्रोत | जोड़ा गया |
|---|---|---|
| **R1** | अपनी सूची: trend, MR, vol, volume, structure, stats, derivatives, cross-asset, on-chain, sentiment, calendar, ML, AI, combinations, entry, exit, गणित | ~140 items |
| **R2** | TA-Lib की पूरी function list (Overlap 17, Momentum 30, Volume 3, Volatility 3, Cycle 5, Price transform 4, Patterns 61, Statistic 9) | MAMA, T3, MAVP, MIDPOINT/MIDPRICE, SAREXT, APO, BOP, ROCR/ROCR100, MACDEXT/MACDFIX, ULTOSC, HT_* (5 cycle indicators), BETA/CORREL, TSF, सभी 61 candlestick patterns (A5.09 में) |
| **R3** | Fang et al. 2022 survey (6 groups: systematic/TA, pairs, econometrics, ML, portfolio/comovement, market condition/bubbles/crashes) + López de Prado (information-driven bars, triple barrier, meta-labeling, purged CV, DSR/PBO) + Kaufman (efficiency ratio, adaptive systems) | Pairs/cointegration (A6.11), bubble tests LPPLS/SADF (A6.13), volume/dollar/imbalance bars (A4.10), meta-labeling (A12.11), purged CV (A12.13), PBO (D.06), adaptive MA KAMA (A1.01 में पहले से) |
| **R4** | पूरी सूची दोबारा: entry/exit के बाकी आम तरीके (MAE/MFE, profit lock, SPRT, Bertram), time-free bars, regime-switch combinations | MAE/MFE (C.12), profit lock (C.13), SPRT (B.14/D.08), Bertram OU (A2.16/C.15) |
| **R5** | सभी 6 survey groups और सभी TA-Lib groups का दोबारा मिलान | **0 नया → saturated** |

**Sources:**
- TA-Lib function list: https://ta-lib.github.io/ta-lib-python/funcs.html
- Fang et al., "Cryptocurrency Trading: A Comprehensive Survey", Financial Innovation 2022: https://arxiv.org/pdf/2003.11352
- pandas-ta (130+ indicators, same families): https://pandas-ta.dev/api/ta

---

## 9. Testing का plan (Phase 2 में इस पर अलग protocol lock होगा)

1. **एक ही test bench सब पर:**
   - BTC 5m data;
   - entry अगली bar के open पर;
   - exit के तरीके भाग C से;
   - fee `deploy/fees.json` से।
   - Exit engine आज की BTC study वाला ही है (verifier के हिसाब से 500/500 सही)।
2. **Periods:** dev 2020–2023, validation 2024, holdout 2025-01 → 2026-09 (सिर्फ़ एक बार)।
3. **हर तरीके का "perfection score":**
   - holdout mean net;
   - 95% CI;
   - सही दिशा की दर बनाम p*;
   - profit factor;
   - महीनों में positive का हिस्सा;
   - सबसे बुरा महीना;
   - random entry पर percentile;
   - DSR।
   - इन सबसे एक **ranking** बनेगी।
4. **हर तरीके की reports:**
   - **daily** (हर दिन के trades और P&L);
   - **monthly**;
   - **yearly**।
   - सब CSV में, साथ में Hindi summary।
5. **Batches** (आसान से कठिन):
   1. A1 + A2 (trend + oscillators);
   2. A3 + A4 (vol + volume/flow);
   3. A5 (structure + candlestick + chart patterns);
   4. A6 (statistics);
   5. A7 + A8 + A11 (derivatives, cross-asset, calendar);
   6. A12 + A13 + A14 (AI और combinations);
   7. B entries और C exits, सबसे अच्छे दिशा-तरीकों के ऊपर।
6. **हर batch:** protocol lock → code → अलग verifier → Hindi report। पिछली BTC study के 990 configs की ranking भी इसी ढाँचे में जुड़ेगी।
7. **"कोई shortcut नहीं" (user, 26 अक्टूबर; amendment 1, `626f670a…`):**
   - **हर configuration के लिए:**
     - D, V, H के अलावा पूरी अवधि (2020 → 2026) की **लगातार daily, monthly और yearly reports**;
     - हर कैलेंडर दिन दर्ज होगा, बिना trade वाले दिन भी;
     - futures और spot, दोनों fees पर।
   - **Random-entry control हर configuration पर** चलेगा, सिर्फ़ top 20 पर नहीं।
   - **Testing के अतिरिक्त तरीके:**
     - 2 गुना fee (stress);
     - 1 bar देर से entry (delay);
     - हर साल का अलग नतीजा।
   - **नया gate G6:** stress और delay, दोनों में भी profit।

*मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ। यह research है, निवेश सलाह नहीं।*
