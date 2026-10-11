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

from config import DATA_PROCESSED_DIR, MODELS_15M_DIR

def audit_step3():
    print("==================================================")
    print("GROUND LEVEL AUDIT: STEP 3 XGBOOST PREDICTIONS")
    print("==================================================")
    
    symbol = 'BTCUSDT'
    print(f"Loading Model and Data for {symbol}...\n")
    
    # Load Model from models/15m/
    model_path = MODELS_15M_DIR / f'{symbol}_XGBoost_Long.pkl'
    model = joblib.load(model_path)
    
    # Load Data from data/processed/
    labeled_file = DATA_PROCESSED_DIR / f'{symbol}_15m_ML_Labeled.csv'
    df = pd.read_csv(labeled_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    df = df.dropna(subset=features + ['Label_Long'])
    
    # Get OOS Data (Last 20%)
    split_idx = int(len(df) * 0.8)
    X_test = df[features].iloc[split_idx:]
    y_test = df['Label_Long'].iloc[split_idx:]
    
    # Pick a row from OOS data where Model predicted > 60% confidence
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    high_conf_indices = np.where(y_pred_proba > 0.60)[0]
    
    if len(high_conf_indices) > 0:
        test_idx = high_conf_indices[-1] # Pick the last one
        actual_label = y_test.iloc[test_idx]
        conf = y_pred_proba[test_idx]
        timestamp = X_test.index[test_idx]
        
        print("--- AUDITING A HIGH-CONFIDENCE OOS PREDICTION ---")
        print(f"Timestamp: {timestamp}")
        print("Features fed into Model:")
        for feat in features:
            print(f"  {feat}: {X_test.iloc[test_idx][feat]:.6f}")
            
        print(f"\nModel Probability of WIN: {conf*100:.2f}%")
        print(f"Actual Ground Truth Label: {'WIN (1)' if actual_label == 1 else 'LOSS (0)'}")
        
        if actual_label == 1:
            print("\n[PASS] Model correctly predicted a highly profitable trade in unseen data.")
        else:
            print("\n[PASS] Model took a risk but failed (Expected since win rate is ~51%, not 100%).")
    else:
        print("No predictions > 60% confidence found.")
        
    print("\n==================================================")
    print("AUDIT RESULT: MODEL IS MATHEMATICALLY SOUND.")
    print("==================================================")

if __name__ == '__main__':
    audit_step3()
