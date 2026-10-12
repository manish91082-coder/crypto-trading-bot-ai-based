# AI QUANT TRADING BOT - ZERO TRUST MASTER RULES & LOCKS
**Date:** October 10, 2026
**Framework:** Institutional Machine Learning / Quant Architecture
**Status:** Absolute Lockdown (No Technical Indicators allowed)

## 1. THE ABSOLUTE LAWS (Locks)
1.  **NO RETAIL INDICATORS:** RSI, MACD, Bollinger Bands, EMA crossovers are strictly BANNED for direct signal generation. The market edge is 0%.
2.  **NO LOOKAHEAD BIAS:** All data features MUST be strictly lagged by at least 1 period before feeding into the ML model. The model must never see future prices.
3.  **STRICT BLIND OUT-OF-SAMPLE TESTING (Sealed Vault):** 
    - At least 20% of data (2025–2026) is locked in a sealed vault.
    - Research scripts and hyperparameter tuning MUST NEVER touch this data.
    - The model is tested on OOS exactly once. If OOS Expectancy <= 0, the model is permanently discarded.
4.  **FEES & SLIPPAGE ARE KING:** Binance BNB discount taker fee of 0.075% per trade plus dynamic ATR slippage must be deducted on entries, exits, and partial exits.
5.  **NO RUBBER-STAMPING AUDITS (Adversarial Audit Rule):**
    - Verifying only syntax or whether code runs without crashing is STRICTLY FORBIDDEN.
    - Every audit must actively attempt to invalidate the strategy by checking:
      a) Train AUC vs Test AUC (Overfit gap).
      b) In-Sample vs Out-of-Sample PnL separation.
      c) Data boundary sanity (no year 56971+, no missing months).
      d) Label-Execution exact mathematical match.
6.  **LABEL-EXECUTION EQUIVALENCE & RUNNER LAW:**
    - The initial evaluation horizon must match execution rules, but execution MUST NEVER artificially kill winning swing trades with an arbitrary calendar timeout.
    - At +3.0x ATR, 75% of profit is secured, Stop Loss is moved to break-even, and the remaining 25% "Runner" rides with a dynamic Trailing Stop (2.0x ATR) until the trend physically reverses.
7.  **PHYSICAL ACCOUNT REALITY:**
    - Spot models: Strictly Long-Only, and Total Notional <= 1.0x Capital.
    - Shorting models: Require Futures margin, funding rate drag, and borrow cost accounting.
8.  **PRE-FLIGHT DATA INTEGRITY CERTIFICATION:**
    - No model training or backtesting script is permitted to run until data integrity (completeness, timestamp continuity, gap-free series) has passed automated certification.
9.  **MACRO REGIME CONFLUENCE LAW:**
    - Long swing trades in altcoins are strictly barred unless Bitcoin (BTC) is trading above its 20-period EMA (Macro Bullish Regime). Never buy altcoins into a macro-falling market.

## 2. THE AI / ML PIPELINE RULES
*   **Step 1: Stationary Feature Engineering:** Raw price data must be made stationary without losing memory (Fractional Differentiation or Volatility Z-Scores, Normalized Order Flow).
*   **Step 2: Pooled Low-Capacity Models:** To prevent memorizing regimes, models must be pooled across all coins with shallow tree depth (1–2), strong regularization, and evaluated against a linear Logistic Regression baseline.
*   **Step 3: Triple-Barrier Labeling:** Target multiples and time horizons must mirror execution rules exactly.
*   **Step 4: Purged Walk-Forward with Embargo:** Training and validation folds must enforce purging windows equal to label horizon + embargo.
*   **Step 5: Out-of-Fold Meta-Labeling:** 
    *   Meta-models must ONLY be trained on primary model out-of-fold predictions.
    *   Never train Meta-models on primary in-sample confidences.

## 3. CAPITAL & EXECUTION RULES
*   **Risk Per Trade:** Fixed 2%–5% with active Drawdown Damping (Institutional Risk Governor).
*   **Drawdown Ceiling:** If portfolio drawdown exceeds 20%, risk must scale down to defense floor.
*   **Compounding:** Only valid if Out-of-Sample Expectancy > 0.15R.
*   **Execution Timeframes:** 1D for macro swing regime, 15m for entry precision (once 1D is certified).
*   **Asset Universe:** 10 High-Liquidity Coins dynamically loaded from config.

## 4. THE ANTI-DRIFT & ZERO-HALLUCINATION PROTOCOL (एंटी-ड्रिफ्ट और अचूक शार्पनेस कानून)
*   **Rule 4.1: Strict Goal & Prompt Anchoring (लक्ष्य और प्रॉम्प्ट का पूर्ण बंधन):**
    - The AI agent must never drift, wander, or invent auxiliary tasks outside the user's exact prompt.
    - Every proposed step must be tied directly to the core goal: verified institutional quantitative trading edge.
*   **Rule 4.2: Zero Self-Invented Assumptions (मनमाने बदलावों पर पूर्ण रोक):**
    - Changing parameters, modifying labels, altering exit logic, or dropping assets without mathematical proof and explicit user confirmation is STRICTLY FORBIDDEN.
    - Silent error suppression (`bare except:`, `except: pass`, silent fallback to 0) is classified as a Critical System Malpractice. Every exception must raise full traceback.
*   **Rule 4.3: Pre-Flight Assertion Gates (कोड से पहले डेटा और गणित की कठोर जाँच):**
    - Every production and research script must enforce Pre-Flight Assertions:
      a) Timestamp validation: Ensure `min_date`, `max_date` are sane (no year > 2030, no timestamps > 1e13).
      b) Continuity validation: Gaps > 1 day must trigger hard errors.
      c) Finite numbers: Zero NaN, zero Inf across all features before passing to models.
*   **Rule 4.4: Dual-Source Triangulation of Evidence (दोहरे स्वतंत्र स्रोतों से सत्यापन):**
    - A metric is NEVER true simply because a terminal printed it.
    - Every evidence claim must be triangulated from two independent sources:
      1. Raw written CSV on disk.
      2. Independent script re-computing the metric from ground principles.
*   **Rule 4.5: Adversarial Red-Team Mindset (शत्रुतापूर्ण परीक्षण मानसिकता):**
    - The default assumption for any strategy is "IT IS OVERFIT AND BROKEN UNTIL PROVEN INNOCENT".
    - If a backtest shows abnormal profits, the agent must actively search for leakage, bugs, lookahead, and in-sample contamination before presenting it.
*   **Rule 4.6: Pure Devanagari Hindi Communication Standard (शुद्ध देवनागरी हिंदी संवाद):**
    - All conversations and technical reporting must be in clear, natural Devanagari Hindi script. Hinglish and Romanized text are prohibited.

*Any agent, code, or execution that violates these rules must be immediately aborted and rectified.*


