import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Dynamically resolve SRC directory for relative imports
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_PROCESSED_DIR, SYMBOLS

def generate_triple_barrier_labels(symbol):
    print(f"[{symbol}] STEP 2: Starting Triple-Barrier Labeling...")
    
    # Load Feature Data from data/processed/
    feature_file = DATA_PROCESSED_DIR / f'{symbol}_15m_ML_Features.csv'
    try:
        df = pd.read_csv(feature_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
    except Exception as e:
        print(f"Error loading {symbol} from {feature_file}: {e}")
        return None

    # RULE: Execution happens at the NEXT candle's OPEN (T+1 Open) to account for slippage.
    df['Next_Open'] = df['open'].shift(-1)
    
    # Look ahead up to 48 periods (12 hours)
    look_ahead_periods = 48
    
    # Targets: 3.0x ATR for TP, 2.0x ATR for SL (1:1.5 RR)
    TP_MULT = 3.0
    SL_MULT = 2.0
    
    labels_long = np.zeros(len(df))
    labels_short = np.zeros(len(df))
    
    highs = df['high'].values
    lows = df['low'].values
    atrs = df['ATR_14'].values
    next_opens = df['Next_Open'].values
    
    for i in range(len(df) - look_ahead_periods):
        entry_price = next_opens[i]
        atr = atrs[i]
        
        # LONG BARRIERS
        long_tp = entry_price + (TP_MULT * atr)
        long_sl = entry_price - (SL_MULT * atr)
        
        # SHORT BARRIERS
        short_tp = entry_price - (TP_MULT * atr)
        short_sl = entry_price + (SL_MULT * atr)
        
        long_hit = 0 # 0=Loss/Timeout, 1=Win
        short_hit = 0 # 0=Loss/Timeout, 1=Win
        
        # Check Long (Pessimistic: Check SL first)
        for j in range(1, look_ahead_periods + 1):
            future_high = highs[i + j]
            future_low = lows[i + j]
            
            if long_hit == 0:
                if future_low <= long_sl:
                    long_hit = 0
                    break
                elif future_high >= long_tp:
                    long_hit = 1
                    break
                    
        # Check Short (Pessimistic: Check SL first)
        for j in range(1, look_ahead_periods + 1):
            future_high = highs[i + j]
            future_low = lows[i + j]
            
            if short_hit == 0:
                if future_high >= short_sl:
                    short_hit = 0
                    break
                elif future_low <= short_tp:
                    short_hit = 1
                    break
                    
        labels_long[i] = long_hit
        labels_short[i] = short_hit

    df['Label_Long'] = labels_long
    df['Label_Short'] = labels_short
    
    # Drop rows at the end where future is unavailable
    df.dropna(subset=['Next_Open'], inplace=True)
    df = df.iloc[:-look_ahead_periods]
    
    print(f"[{symbol}] STEP 2: Labeling Completed. Total Valid Rows: {len(df)}")
    
    win_rate_long = df['Label_Long'].mean() * 100
    win_rate_short = df['Label_Short'].mean() * 100
    print(f"[{symbol}] Natural Long Win Rate (Random Entry): {win_rate_long:.2f}%")
    print(f"[{symbol}] Natural Short Win Rate (Random Entry): {win_rate_short:.2f}%")
    
    # Save the labeled dataset to data/processed/
    output_file = DATA_PROCESSED_DIR / f'{symbol}_15m_ML_Labeled.csv'
    df.to_csv(output_file)
    print(f"[{symbol}] Saved labeled set to {output_file}")
    
    return df

if __name__ == '__main__':
    for sym in SYMBOLS:
        generate_triple_barrier_labels(sym)
    print("\n==================================================")
    print("STEP 2 COMPLETELY EXECUTED FOR ALL 10 COINS.")
    print("==================================================")
