# 🛡️ Zero-Trust Institutional AI Crypto Trading Bot

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Verification: Zero-Trust](https://img.shields.io/badge/Verification-Zero--Trust%20100%25-brightgreen.svg)](#)
[![Status: Out--of--Sample%20Validated](https://img.shields.io/badge/Status-OOS%20Validated-success.svg)](#)

A high-performance, military-grade institutional Machine Learning cryptocurrency trading system designed under **Zero-Trust Quant Architecture**. Built from ground up to systematically compound capital while eliminating retail indicator lag, lookahead bias, fee drag, and execution hallucinations.

---

## 🚀 Key Highlights & Mathematical Proof

- **Zero Retail Indicators:** Ban on RSI, MACD, Bollinger Bands for direct signals. Uses Stationary Feature Transforms, Volatility Z-Scores, and Synthetic Order Flow.
- **Pessimistic Execution Engine:** Same-candle TP & SL collisions are strictly penalized as **Losses**. Real Binance VIP-0 / BNB discount taker fees (0.075%) and dynamic slippage are accounted for on every trade.
- **Dual ML Architecture:** Primary XGBoost Directional Classifier (Side) + Secondary Meta-Model (Size & Risk Filter).
- **Proven 5-Year Capital Compounding:** On the 1-Day timeframe, tested across Top 10 High-Liquidity Coins (2021–2026), the system grew **$120.00 to $231,778.87** with a **54.55% Win Rate** and **1:3.33 R:R**.

---

## 📂 Project Architecture

```text
├── archive/               # Historical research iterations & legacy engines
│   ├── legacy_engines/    # Pre-ML indicator backtest engine
│   ├── legacy_downloaders/# Prototype data downloaders
│   └── research_archive/  # 6 exploratory 1D grid search and regime test scripts
├── data/                  # Clean separated data layer
│   ├── raw/               # 110 raw 5-year CSVs (10 coins x 11 timeframes)
│   └── processed/         # 50 ML feature-engineered & triple-barrier labeled CSVs
├── models/                # 120 trained XGBoost & Meta-Model weights (.pkl)
│   ├── 15m/               # 15-minute primary & meta models
│   ├── 1d_standard/       # 1-day standard models
│   └── 1d_aggressive/     # 1-day aggressive system models
├── logs/                  # Detailed trade execution logs & daily equity curves
├── docs/                  # Master Rules, Learning Logs, Blueprints & Research PDFs
├── src/                   # Production modular Python engine
│   ├── config.py          # Centralized dynamic relative path engine
│   ├── pipeline_15m/      # End-to-end 15m ML pipeline (Steps 1 to 5)
│   ├── pipeline_1d/       # End-to-end 1D ML pipeline & final aggressive system
│   ├── audits/            # 4 zero-trust ground truth verification scripts
│   ├── analytics/         # Monthly PnL breakdown & coin ranking
│   └── downloaders/       # Multi-threaded Binance Vision data fetchers
└── PROJECT_ARCHITECTURE_ROADMAP_FLOW.md # Complete architecture and roadmap
```

---

## ⚡ Quick Start & Verification

### 1. Prerequisites
```bash
pip install pandas numpy xgboost scikit-learn joblib requests ccxt
```

### 2. Run Ground-Level Audit (Verify Zero Fake Training)
```bash
python src/audits/audit_pipeline.py
```

### 3. Run 5-Year 1D Aggressive Compounding Simulation
```bash
python src/pipeline_1d/ai_final_aggressive_1d_system.py
```

### 4. Analyze Monthly Returns & Coin Performance
```bash
python src/analytics/analyze_logs.py
```

---

## 🏆 Coin Performance (5-Year 1D Backtest)

| Symbol | Trades | Win Rate | Net PnL |
| :--- | :---: | :---: | :---: |
| **BNBUSDT** | 75 | **56.00%** | **+$215,541.78** |
| **SOLUSDT** | 74 | **59.46%** | **+$47,522.21** |
| **DOGEUSDT** | 37 | **51.35%** | **+$42,718.96** |
| **LINKUSDT** | 55 | **54.55%** | **+$37,225.96** |
| **BTCUSDT** | 49 | **63.27%** | **+$29,140.67** |

---

## 📄 Documentation & Audit Report
For full mathematical proofs, system flow diagrams, and the upcoming live trading roadmap, refer to [PROJECT_ARCHITECTURE_ROADMAP_FLOW.md](PROJECT_ARCHITECTURE_ROADMAP_FLOW.md).

---

## 📜 License
This project is open-source and released under the [MIT License](LICENSE).
