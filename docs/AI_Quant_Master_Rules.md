# AI QUANT TRADING BOT - ZERO TRUST MASTER RULES & LOCKS
**Date:** October 10, 2026
**Framework:** Institutional Machine Learning / Quant Architecture
**Status:** Absolute Lockdown (No Technical Indicators allowed)

## 1. THE ABSOLUTE LAWS (Locks)
1.  **NO RETAIL INDICATORS:** RSI, MACD, Bollinger Bands, EMA crossovers are strictly BANNED for direct signal generation. The market edge is 0%.
2.  **NO LOOKAHEAD BIAS:** All data features MUST be strictly lagged by at least 1 period before feeding into the ML model. The model must never see future prices.
3.  **STRICT OUT-OF-SAMPLE TESTING:** The model must be trained on 2021-2024 data and tested strictly on 2025-2026 data. If it fails Out-of-Sample (OOS), the model is discarded.
4.  **FEES ARE KING:** Binance BNB discount fee of 0.075% per trade must be hardcoded into every single backtest.
5.  **NO HALLUCINATION:** Every feature, every model output, and every trade execution must be dumped to a CSV and verified manually (Ground Level Verification).

## 2. THE AI / ML PIPELINE RULES
*   **Step 1: Fractional Differentiation:** Raw price data must be made stationary without losing memory (d=0.45).
*   **Step 2: Feature Engineering:** We will feed the model Volatility Z-Scores, Wick Analytics, Order Book Imbalances (if available), and Cross-Coin correlations.
*   **Step 3: Triple-Barrier Labeling:** The target is 1:1.5 RR (Target: 3.0x ATR, SL: 2.0x ATR). Label 1 (Hit TP first), Label 0 (Hit SL first), Label -1 (Time expiration).
*   **Step 4: Sample Weighting:** To prevent overfitting during multi-coin flash crashes, concurrent trades must be inversely weighted (Sample Uniqueness Weighting).
*   **Step 5: Meta-Labeling (Ensemble):** 
    *   Primary Model (XGBoost) predicts direction (Side).
    *   Secondary Model (LSTM Risk Manager) predicts the probability of the Primary Model being correct (Size).
    *   Only take trades where the Meta-Model confidence is > 75%.

## 3. CAPITAL & EXECUTION RULES
*   **Risk Per Trade:** Fixed 2% of Current Capital.
*   **Compounding:** 100% Daily Re-compounding. NO MONTHLY WITHDRAWALS. The goal is maximum compounding.
*   **Execution Timeframes:** 15m for entry precision, 4H for macro trend/volatility context. 
*   **Asset Universe:** Top 10 High-Liquidity Coins (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LTC, LINK).

*Any agent, code, or execution that violates these rules must be immediately aborted and rectified.*
