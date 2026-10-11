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
MODELS_1D_AGGRESSIVE_DIR = MODELS_DIR / "1d_aggressive"

LOGS_DIR = ROOT_DIR / "logs"
DOCS_DIR = ROOT_DIR / "docs"
ARCHIVE_DIR = ROOT_DIR / "archive"
SRC_DIR = ROOT_DIR / "src"

# Auto-ensure all operational directories exist
for p in [DATA_RAW_DIR, DATA_PROCESSED_DIR, MODELS_15M_DIR, MODELS_1D_DIR, MODELS_1D_AGGRESSIVE_DIR, LOGS_DIR, DOCS_DIR, ARCHIVE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# Standard Universal 10-Coin Universe
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT']

def get_raw_csv(symbol: str, interval: str) -> Path:
    """Return path to raw 5-year data CSV."""
    return DATA_RAW_DIR / f"{symbol}_{interval}_Raw_5Years.csv"

def get_processed_csv(symbol: str, interval: str, kind: str) -> Path:
    """Return path to processed feature/label CSV."""
    # kind can be 'ML_Features', 'ML_Labeled', 'Temp_Labeled'
    return DATA_PROCESSED_DIR / f"{symbol}_{interval}_{kind}.csv"

def get_model_path(symbol: str, timeframe: str, model_type: str, direction: str) -> Path:
    """Return path to trained model (.pkl)."""
    # timeframe: '15m', '1d', '1d_aggressive'
    # model_type: 'XGBoost', 'MetaModel'
    # direction: 'Long', 'Short'
    if timeframe == '15m':
        return MODELS_15M_DIR / f"{symbol}_{model_type}_{direction}.pkl"
    elif timeframe == '1d':
        return MODELS_1D_DIR / f"{symbol}_1d_{model_type}_{direction}.pkl"
    elif timeframe == '1d_aggressive':
        prefix = 'Temp_XGB' if model_type == 'XGBoost' else 'Temp_Meta'
        return MODELS_1D_AGGRESSIVE_DIR / f"{symbol}_1d_{prefix}_{direction}.pkl"
    else:
        raise ValueError(f"Unknown timeframe: {timeframe}")

def get_log_path(filename: str) -> Path:
    """Return path to log file in logs directory."""
    return LOGS_DIR / filename
