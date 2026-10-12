from pathlib import Path
import os

# Base Project Root directory (dynamically resolved relative to this config file)
# src/config.py -> parent is 'src', parent.parent is project root
ROOT_DIR = Path(__file__).resolve().parent.parent

# Core Directories
DATA_DIR = ROOT_DIR / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"

MODELS_DIR = ROOT_DIR / "models"
MODELS_15M_DIR = MODELS_DIR / "15m"
MODELS_1D_DIR = MODELS_DIR / "1d_standard"
MODELS_1D_POOLED_DIR = MODELS_DIR / "1d_pooled"
MODELS_1D_AGGRESSIVE_DIR = MODELS_DIR / "1d_aggressive"
MODELS_4H_POOLED_DIR = MODELS_DIR / "4h_pooled"

LOGS_DIR = ROOT_DIR / "logs"
DOCS_DIR = ROOT_DIR / "docs"
ARCHIVE_DIR = ROOT_DIR / "archive"
SRC_DIR = ROOT_DIR / "src"

# Auto-ensure all operational directories exist
for p in [DATA_RAW_DIR, DATA_PROCESSED_DIR, MODELS_15M_DIR, MODELS_1D_DIR, MODELS_1D_AGGRESSIVE_DIR, MODELS_1D_POOLED_DIR, MODELS_4H_POOLED_DIR, LOGS_DIR, DOCS_DIR, ARCHIVE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# Standard Universal 10-Coin Universe
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT']

# =====================================================================
# UNIFIED QUANT MASTER RULES & EXECUTION PARAMETERS (MASTER LOCKS)
# =====================================================================
INITIAL_CAPITAL = 120.0
BINANCE_TAKER_FEE = 0.00075  # 0.075% taker fee with BNB discount

# Barrier Multipliers (ATR-based)
TP_ATR_MULT = 3.0       # Target 1: Bank 75% profit at +3.0x ATR
SL_ATR_MULT = 1.5       # Initial Stop Loss at 1.5x ATR
BE_ATR_MULT = 1.5       # Move Stop Loss to Breakeven once price reaches +1.5x ATR

# Swing Runner Architecture (Law #6)
PARTIAL_TP_PCT = 0.75   # 75% profit secured at TP_ATR_MULT
RUNNER_PCT = 0.25       # 25% Runner position size rides trend
RUNNER_TRAILING_ATR = 2.0  # Dynamic Trailing Stop for 25% Runner (rides until trend reversal)
RUNNER_SL_LOCK_ATR = 1.0   # Runner SL locked at Entry + 1.0x ATR upon partial TP

# Inactivity Timeout (ONLY for unhit/unsecured trades - Runners NEVER killed by calendar time!)
MAX_INACTIVITY_DAYS = 14  # Max days an unhit trade is allowed to drift before exit

# Purge & Embargo Window (Matches MAX_INACTIVITY_DAYS for zero lookahead)
PURGE_WINDOW_DAYS = 14

# Macro Trend Filter (Law #9)
MACRO_BTC_EMA_PERIOD = 20

# Certified Stationary Feature Set (15 Quant Features)
FEATURE_COLS = [
    'Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow',
    'Upper_Wick_Ratio', 'Lower_Wick_Ratio', 'Vol_Z_Score',
    'ATR_Pct', 'Dist_EMA_20_ATR', 'Rel_Mom_vs_BTC',
    'SL_Dist_Ratio', 'Pullback_Depth', 'Vol_Accum_Ratio',
    'Regime_Z_Score', 'Volatility_Compression'
]


def get_raw_csv(symbol: str, interval: str) -> Path:
    """Return path to raw 5-year data CSV."""
    return DATA_RAW_DIR / f"{symbol}_{interval}_Raw_5Years.csv"

def get_processed_csv(symbol: str, interval: str, kind: str) -> Path:
    """Return path to processed feature/label CSV."""
    return DATA_PROCESSED_DIR / f"{symbol}_{interval}_{kind}.csv"

def get_model_path(symbol: str, timeframe: str, model_type: str, direction: str) -> Path:
    """Return path to trained model (.pkl)."""
    if timeframe == '15m':
        return MODELS_15M_DIR / f"{symbol}_{model_type}_{direction}.pkl"
    elif timeframe == '1d':
        return MODELS_1D_DIR / f"{symbol}_1d_{model_type}_{direction}.pkl"
    elif timeframe == '1d_pooled':
        return MODELS_1D_POOLED_DIR / f"Pooled_1d_XGB_{direction}.pkl"
    elif timeframe == '1d_aggressive':
        prefix = 'Temp_XGB' if model_type == 'XGBoost' else 'Temp_Meta'
        return MODELS_1D_AGGRESSIVE_DIR / f"{symbol}_1d_{prefix}_{direction}.pkl"
    else:
        raise ValueError(f"Unknown timeframe: {timeframe}")

def get_log_path(filename: str) -> Path:
    """Return path to log file in logs directory."""
    return LOGS_DIR / filename

