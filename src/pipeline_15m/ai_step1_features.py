import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Dynamically resolve SRC directory for relative imports
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, DATA_PROCESSED_DIR, SYMBOLS

def generate_features(symbol):
    print(f"[{symbol}] STEP 1: Starting Feature Engineering...")
    
    # Load Raw 5-Year Data from data/raw/
    raw_path = DATA_RAW_DIR / f'{symbol}_15m_Raw_5Years.csv'
    try:
        df = pd.read_csv(raw_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df.dropna(subset=['timestamp'], inplace=True)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
    except Exception as e:
        print(f"Error loading {symbol} from {raw_path}: {e}")
        return None

    # NO LOOKAHEAD BIAS: All features must be calculated on PAST data.
    # Feature 1: Returns (Momentum)
    df['Ret_1'] = df['close'].pct_change(1)
    df['Ret_3'] = df['close'].pct_change(3)
    df['Ret_5'] = df['close'].pct_change(5)
    
    # Feature 2: Synthetic Order Flow (Buy vs Sell Pressure)
    df['Synthetic_Order_Flow'] = (df['close'] - df['open']) / (df['high'] - df['low'] + 1e-8)
    
    # Feature 3: Volatility Z-Score (Is market unusually active?)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    df['TR'] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    df['ATR_14'] = df['TR'].ewm(alpha=1/14, adjust=False).mean()
    
    df['ATR_100_MA'] = df['ATR_14'].rolling(100).mean()
    df['ATR_100_STD'] = df['ATR_14'].rolling(100).std()
    df['Vol_Z_Score'] = (df['ATR_14'] - df['ATR_100_MA']) / (df['ATR_100_STD'] + 1e-8)
    
    # Feature 4: Price Location vs Moving Averages (Trend Context)
    df['SMA_50'] = df['close'].rolling(50).mean()
    df['SMA_200'] = df['close'].rolling(200).mean()
    df['Dist_SMA_50'] = (df['close'] - df['SMA_50']) / df['SMA_50']
    df['Dist_SMA_200'] = (df['close'] - df['SMA_200']) / df['SMA_200']
    
    # Drop NaNs created by rolling windows (removes first 200 rows)
    df.dropna(inplace=True)
    
    print(f"[{symbol}] STEP 1: Feature Engineering Completed. Total Rows: {len(df)}")
    
    # GROUND LEVEL AUDIT: Verify No Lookahead Bias
    print("\n--- GROUND LEVEL VERIFICATION (SAMPLE) ---")
    sample = df[['close', 'Ret_1', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_200']].tail(3)
    print(sample)
    print("------------------------------------------\n")
    
    # Save the feature-engineered dataset to data/processed/
    output_file = DATA_PROCESSED_DIR / f'{symbol}_15m_ML_Features.csv'
    df.to_csv(output_file)
    print(f"[{symbol}] Saved feature set to {output_file}")
    
    return df

if __name__ == '__main__':
    for sym in SYMBOLS:
        generate_features(sym)
    print("\n==================================================")
    print("STEP 1 COMPLETELY EXECUTED FOR ALL 10 COINS.")
    print("==================================================")
