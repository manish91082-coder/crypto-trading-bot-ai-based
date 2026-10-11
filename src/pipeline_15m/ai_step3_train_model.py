import sys
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib

# Dynamically resolve SRC directory for relative imports
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_PROCESSED_DIR, MODELS_15M_DIR, SYMBOLS

def train_primary_model(symbol, direction):
    print(f"[{symbol}] STEP 3: Starting Primary Model Training ({direction})...")
    
    labeled_file = DATA_PROCESSED_DIR / f'{symbol}_15m_ML_Labeled.csv'
    try:
        df = pd.read_csv(labeled_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
    except Exception as e:
        print(f"Error loading {symbol} from {labeled_file}: {e}")
        return
        
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    label_col = 'Label_Long' if direction == 'Long' else 'Label_Short'
    
    df = df.dropna(subset=features + [label_col])
    
    X = df[features]
    y = df[label_col]
    
    # 80% Train, 20% Out-Of-Sample
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    ratio = float(y_train.value_counts().get(0, 1)) / max(1, y_train.value_counts().get(1, 1))
    
    model = xgb.XGBClassifier(
        n_estimators=300,
        learning_rate=0.01,
        max_depth=4,
        scale_pos_weight=ratio,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    model_file = MODELS_15M_DIR / f'{symbol}_XGBoost_{direction}.pkl'
    joblib.dump(model, model_file)
    print(f"[{symbol}] Model saved to {model_file}")

if __name__ == '__main__':
    for sym in SYMBOLS:
        train_primary_model(sym, 'Long')
        train_primary_model(sym, 'Short')
    print("\n==================================================")
    print("STEP 3 COMPLETELY EXECUTED FOR ALL 10 COINS (LONG & SHORT).")
    print("==================================================")
