import sys
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import warnings
warnings.filterwarnings('ignore')

# Dynamically resolve SRC directory for relative imports
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, DATA_PROCESSED_DIR, MODELS_1D_DIR, SYMBOLS

# ==========================================
# STEP 1: FEATURE ENGINEERING (1D TIMEFRAME)
# ==========================================
def step1_features_1d(symbol):
    raw_path = DATA_RAW_DIR / f'{symbol}_1d_Raw_5Years.csv'
    df = pd.read_csv(raw_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.dropna(subset=['timestamp'], inplace=True)
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    
    # Basic Returns
    df['Ret_1'] = df['close'].pct_change(1)
    df['Ret_3'] = df['close'].pct_change(3)
    df['Ret_5'] = df['close'].pct_change(5)
    
    # ATR (14)
    df['H-L'] = df['high'] - df['low']
    df['H-Cp'] = np.abs(df['high'] - df['close'].shift(1))
    df['L-Cp'] = np.abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-Cp', 'L-Cp']].max(axis=1)
    df['ATR_14'] = df['TR'].rolling(14).mean()
    
    # Synthetic Order Flow
    df['Synthetic_Order_Flow'] = (df['close'] - df['open']) / (df['high'] - df['low'] + 1e-8)
    
    # Volatility Z-Score
    df['Vol_14'] = df['Ret_1'].rolling(14).std()
    df['Vol_Mean_50'] = df['Vol_14'].rolling(50).mean()
    df['Vol_Std_50'] = df['Vol_14'].rolling(50).std()
    df['Vol_Z_Score'] = (df['Vol_14'] - df['Vol_Mean_50']) / (df['Vol_Std_50'] + 1e-8)
    
    # Trend Features
    df['SMA_50'] = df['close'].rolling(50).mean()
    df['SMA_200'] = df['close'].rolling(200).mean()
    df['Dist_SMA_50'] = (df['close'] - df['SMA_50']) / df['SMA_50']
    df['Dist_SMA_200'] = (df['close'] - df['SMA_200']) / df['SMA_200']
    
    out_feat = DATA_PROCESSED_DIR / f'{symbol}_1d_ML_Features.csv'
    df.to_csv(out_feat)
    return df

# ==========================================
# STEP 2: TRIPLE-BARRIER LABELING (1D)
# ==========================================
def step2_labeling_1d(symbol):
    feat_path = DATA_PROCESSED_DIR / f'{symbol}_1d_ML_Features.csv'
    df = pd.read_csv(feat_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    df['Next_Open'] = df['open'].shift(-1)
    look_ahead_periods = 60 # Look up to 60 days ahead
    
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
        
        long_tp = entry_price + (TP_MULT * atr)
        long_sl = entry_price - (SL_MULT * atr)
        short_tp = entry_price - (TP_MULT * atr)
        short_sl = entry_price + (SL_MULT * atr)
        
        long_hit = 0
        short_hit = 0
        
        for j in range(1, look_ahead_periods + 1):
            future_high = highs[i + j]
            future_low = lows[i + j]
            
            if long_hit == 0:
                if future_low <= long_sl: long_hit = 0; break
                elif future_high >= long_tp: long_hit = 1; break
                
        for j in range(1, look_ahead_periods + 1):
            future_high = highs[i + j]
            future_low = lows[i + j]
            
            if short_hit == 0:
                if future_high >= short_sl: short_hit = 0; break
                elif future_low <= short_tp: short_hit = 1; break
                
        labels_long[i] = long_hit
        labels_short[i] = short_hit

    df['Label_Long'] = labels_long
    df['Label_Short'] = labels_short
    
    df.dropna(subset=['Next_Open'], inplace=True)
    df = df.iloc[:-look_ahead_periods]
    out_label = DATA_PROCESSED_DIR / f'{symbol}_1d_ML_Labeled.csv'
    df.to_csv(out_label)

# ==========================================
# STEP 3 & 4: MODEL TRAINING (1D)
# ==========================================
def train_models_1d(symbol, direction):
    label_path = DATA_PROCESSED_DIR / f'{symbol}_1d_ML_Labeled.csv'
    df = pd.read_csv(label_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    label_col = 'Label_Long' if direction == 'Long' else 'Label_Short'
    
    df = df.dropna(subset=features + [label_col])
    X = df[features]
    y = df[label_col]
    
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    # Primary Model
    ratio = float(y_train.value_counts().get(0, 1)) / max(1, y_train.value_counts().get(1, 1))
    model = xgb.XGBClassifier(n_estimators=200, learning_rate=0.01, max_depth=3, scale_pos_weight=ratio, random_state=42)
    model.fit(X_train, y_train)
    joblib.dump(model, MODELS_1D_DIR / f'{symbol}_1d_XGBoost_{direction}.pkl')
    
    # Meta Model
    primary_probs_train = model.predict_proba(X_train)[:, 1]
    meta_X_train = pd.DataFrame({'Primary_Confidence': primary_probs_train, 'Vol_Z_Score': X_train['Vol_Z_Score'], 'Dist_SMA_200': X_train['Dist_SMA_200']})
    
    meta_model = xgb.XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=2, scale_pos_weight=ratio, random_state=99)
    meta_model.fit(meta_X_train, y_train)
    joblib.dump(meta_model, MODELS_1D_DIR / f'{symbol}_1d_MetaModel_{direction}.pkl')

# ==========================================
# STEP 5: 1D CHRONOLOGICAL OOS BACKTEST
# ==========================================
def backtest_1d():
    print("\n[STARTING 1D BACKTEST SIMULATION]")
    CAPITAL = 120.0
    RISK_PER_TRADE = 0.02
    FEE_RATE = 0.00075
    
    all_signals = []
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    
    for symbol in SYMBOLS:
        feat_path = DATA_PROCESSED_DIR / f'{symbol}_1d_ML_Features.csv'
        df = pd.read_csv(feat_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        split_idx = int(len(df) * 0.8)
        df = df.iloc[split_idx:].copy() # STRICT OOS
        df = df.dropna(subset=features)
        
        X = df[features]
        
        # Load models from models/1d_standard/
        mL = joblib.load(MODELS_1D_DIR / f'{symbol}_1d_XGBoost_Long.pkl')
        metaL = joblib.load(MODELS_1D_DIR / f'{symbol}_1d_MetaModel_Long.pkl')
        pL = mL.predict_proba(X)[:, 1]
        mL_prob = metaL.predict_proba(pd.DataFrame({'Primary_Confidence': pL, 'Vol_Z_Score': df['Vol_Z_Score'], 'Dist_SMA_200': df['Dist_SMA_200']}))[:, 1]
        
        mS = joblib.load(MODELS_1D_DIR / f'{symbol}_1d_XGBoost_Short.pkl')
        metaS = joblib.load(MODELS_1D_DIR / f'{symbol}_1d_MetaModel_Short.pkl')
        pS = mS.predict_proba(X)[:, 1]
        mS_prob = metaS.predict_proba(pd.DataFrame({'Primary_Confidence': pS, 'Vol_Z_Score': df['Vol_Z_Score'], 'Dist_SMA_200': df['Dist_SMA_200']}))[:, 1]
        
        df['Meta_L'] = mL_prob
        df['Meta_S'] = mS_prob
        df['Symbol'] = symbol
        all_signals.append(df)
        
    master_df = pd.concat(all_signals)
    master_df.reset_index(inplace=True)
    master_df.sort_values('timestamp', inplace=True)
    
    unique_times = master_df['timestamp'].unique()
    
    prices_high, prices_low, prices_open = {}, {}, {}
    for sym in SYMBOLS:
        df_sym = master_df[master_df['Symbol'] == sym].set_index('timestamp')
        prices_high[sym] = df_sym['high'].to_dict()
        prices_low[sym] = df_sym['low'].to_dict()
        prices_open[sym] = df_sym['open'].to_dict()
        
    master_df.set_index('timestamp', inplace=True)
    signal_df = master_df[(master_df['Meta_L'] > 0.65) | (master_df['Meta_S'] > 0.65)].copy()
    
    open_trades = []
    trade_history = []
    current_capital = CAPITAL
    max_capital = CAPITAL
    max_dd = 0.0
    
    print("Processing tick-by-tick (1D)...")
    for t in unique_times:
        # Check Exits
        for trade in open_trades[:]:
            sym = trade['symbol']
            if t not in prices_high[sym]: continue
            
            h = prices_high[sym][t]
            l = prices_low[sym][t]
            
            closed = False
            pnl = 0
            
            if trade['direction'] == 'Long':
                if l <= trade['sl']: pnl = -trade['risk_amount']; exit_price = trade['sl']; closed = True
                elif h >= trade['tp']: pnl = trade['risk_amount'] * 1.5; exit_price = trade['tp']; closed = True
            else:
                if h >= trade['sl']: pnl = -trade['risk_amount']; exit_price = trade['sl']; closed = True
                elif l <= trade['tp']: pnl = trade['risk_amount'] * 1.5; exit_price = trade['tp']; closed = True
                
            if closed:
                exit_value = trade['position_size'] * exit_price
                exit_fee = exit_value * FEE_RATE
                net_pnl = pnl - exit_fee
                current_capital += net_pnl
                
                if current_capital > max_capital: max_capital = current_capital
                dd = (max_capital - current_capital) / max_capital
                if dd > max_dd: max_dd = dd
                
                trade['net_pnl'] = net_pnl
                trade['exit_time'] = t
                trade_history.append(trade)
                open_trades.remove(trade)
                
        # Check Entries
        if t in signal_df.index:
            rows = signal_df.loc[[t]]
            for _, row in rows.iterrows():
                sym = row['Symbol']
                if any(tr['symbol'] == sym for tr in open_trades): continue
                
                sym_times = list(prices_open[sym].keys())
                try:
                    idx = sym_times.index(t)
                    next_t = sym_times[idx+1]
                    entry_price = prices_open[sym][next_t]
                except: continue
                
                atr = row['ATR_14']
                if row['Meta_L'] > 0.65:
                    dir = 'Long'
                    tp = entry_price + (3.0 * atr)
                    sl = entry_price - (2.0 * atr)
                elif row['Meta_S'] > 0.65:
                    dir = 'Short'
                    tp = entry_price - (3.0 * atr)
                    sl = entry_price + (2.0 * atr)
                else: continue
                
                risk_amount = current_capital * RISK_PER_TRADE
                sl_dist = abs(entry_price - sl)
                if sl_dist == 0: continue
                position_size = risk_amount / sl_dist
                
                entry_fee = position_size * entry_price * FEE_RATE
                current_capital -= entry_fee
                
                open_trades.append({
                    'symbol': sym, 'direction': dir, 'entry_price': entry_price, 
                    'tp': tp, 'sl': sl, 'risk_amount': risk_amount, 'position_size': position_size
                })
                
    wins = [t for t in trade_history if t['net_pnl'] > 0]
    total_trades = len(trade_history)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    print(f"--- 1-DAY TIMEFRAME RESULTS ---")
    print(f"Initial Capital: $120.00")
    print(f"Final Capital: ${current_capital:.2f}")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")

if __name__ == '__main__':
    print("Executing 1D Pipeline (Steps 1 to 5)...")
    for sym in SYMBOLS:
        print(f"[{sym}] Step 1 & 2: Features and Labels...")
        step1_features_1d(sym)
        step2_labeling_1d(sym)
        print(f"[{sym}] Step 3 & 4: Training Models...")
        train_models_1d(sym, 'Long')
        train_models_1d(sym, 'Short')
        
    backtest_1d()
