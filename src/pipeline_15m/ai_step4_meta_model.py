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

def train_meta_model(symbol, direction):
    print(f"[{symbol}] STEP 4: Training Meta-Model (Risk Manager) for {direction}s...")
    
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
    
    # Load Primary Model from models/15m/
    primary_model_path = MODELS_15M_DIR / f'{symbol}_XGBoost_{direction}.pkl'
    primary_model = joblib.load(primary_model_path)
    
    # 2. Get Primary Model Predictions for the entire dataset
    primary_probs = primary_model.predict_proba(X)[:, 1]
    
    # 3. Create Meta-Features
    meta_X = pd.DataFrame({
        'Primary_Confidence': primary_probs,
        'Vol_Z_Score': df['Vol_Z_Score'].values,
        'Dist_SMA_200': df['Dist_SMA_200'].values
    }, index=df.index)
    
    meta_y = y
    
    # 4. Strict Out-Of-Sample Split
    split_idx = int(len(df) * 0.8)
    X_train, X_test = meta_X.iloc[:split_idx], meta_X.iloc[split_idx:]
    y_train, y_test = meta_y.iloc[:split_idx], meta_y.iloc[split_idx:]
    
    # 5. Train Meta-Model (XGBoost)
    ratio = float(y_train.value_counts().get(0, 1)) / max(1, y_train.value_counts().get(1, 1))
    
    meta_model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=3,
        scale_pos_weight=ratio,
        random_state=99,
        n_jobs=-1
    )
    
    meta_model.fit(X_train, y_train)
    
    # 6. Save Meta-Model to models/15m/
    model_file = MODELS_15M_DIR / f'{symbol}_MetaModel_{direction}.pkl'
    joblib.dump(meta_model, model_file)
    print(f"[{symbol}] Meta-Model saved to {model_file}")
    
    # 7. Audit on Test Data
    meta_probs = meta_model.predict_proba(X_test)[:, 1]
    high_conf = meta_probs > 0.70
    num_trades = high_conf.sum()
    if num_trades > 0:
        win_rate = (y_test[high_conf].sum() / num_trades) * 100
        print(f"[{symbol}] Meta-Model > 70% Confidence -> Trades: {num_trades}, Win Rate: {win_rate:.2f}%")
    else:
        print(f"[{symbol}] Meta-Model > 70% Confidence -> No trades taken.")

if __name__ == '__main__':
    for sym in SYMBOLS:
        train_meta_model(sym, 'Long')
        train_meta_model(sym, 'Short')
    print("\n==================================================")
    print("STEP 4 COMPLETELY EXECUTED FOR ALL 10 COINS (META-MODELS).")
    print("==================================================")
