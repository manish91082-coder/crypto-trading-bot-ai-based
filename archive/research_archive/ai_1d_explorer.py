import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import warnings
warnings.filterwarnings('ignore')

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT']
CAPITAL = 120.0
RISK_PER_TRADE = 0.02
FEE_RATE = 0.00075

def generate_labels(tp_mult, sl_mult):
    look_ahead_periods = 90 # 90 days lookahead for big trends
    for symbol in SYMBOLS:
        df = pd.read_csv(f'{symbol}_1d_ML_Features.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        df['Next_Open'] = df['open'].shift(-1)
        
        labels_long = np.zeros(len(df))
        labels_short = np.zeros(len(df))
        
        highs = df['high'].values
        lows = df['low'].values
        atrs = df['ATR_14'].values
        next_opens = df['Next_Open'].values
        
        for i in range(len(df) - look_ahead_periods):
            entry_price = next_opens[i]
            atr = atrs[i]
            
            long_tp = entry_price + (tp_mult * atr)
            long_sl = entry_price - (sl_mult * atr)
            short_tp = entry_price - (tp_mult * atr)
            short_sl = entry_price + (sl_mult * atr)
            
            long_hit = 0
            short_hit = 0
            
            for j in range(1, look_ahead_periods + 1):
                fh = highs[i + j]
                fl = lows[i + j]
                if long_hit == 0:
                    if fl <= long_sl: long_hit = 0; break
                    elif fh >= long_tp: long_hit = 1; break
                    
            for j in range(1, look_ahead_periods + 1):
                fh = highs[i + j]
                fl = lows[i + j]
                if short_hit == 0:
                    if fh >= short_sl: short_hit = 0; break
                    elif fl <= short_tp: short_hit = 1; break
                    
            labels_long[i] = long_hit
            labels_short[i] = short_hit

        df['Label_Long'] = labels_long
        df['Label_Short'] = labels_short
        df.dropna(subset=['Next_Open'], inplace=True)
        df = df.iloc[:-look_ahead_periods]
        df.to_csv(f'{symbol}_1d_Temp_Labeled.csv')

def train_all_models():
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    for symbol in SYMBOLS:
        df = pd.read_csv(f'{symbol}_1d_Temp_Labeled.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        for direction in ['Long', 'Short']:
            label_col = 'Label_Long' if direction == 'Long' else 'Label_Short'
            df_clean = df.dropna(subset=features + [label_col]).copy()
            X = df_clean[features]
            y = df_clean[label_col]
            
            split_idx = int(len(df_clean) * 0.8)
            X_train = X.iloc[:split_idx]
            y_train = y.iloc[:split_idx]
            
            ratio = float(y_train.value_counts().get(0, 1)) / max(1, y_train.value_counts().get(1, 1))
            
            model = xgb.XGBClassifier(n_estimators=100, learning_rate=0.02, max_depth=3, scale_pos_weight=ratio, random_state=42, n_jobs=-1)
            model.fit(X_train, y_train)
            joblib.dump(model, f'{symbol}_1d_Temp_XGB_{direction}.pkl')
            
            primary_probs = model.predict_proba(X_train)[:, 1]
            meta_X = pd.DataFrame({'Primary_Confidence': primary_probs, 'Vol_Z_Score': X_train['Vol_Z_Score'], 'Dist_SMA_200': X_train['Dist_SMA_200']})
            
            meta_model = xgb.XGBClassifier(n_estimators=50, learning_rate=0.05, max_depth=2, scale_pos_weight=ratio, random_state=99, n_jobs=-1)
            meta_model.fit(meta_X, y_train)
            joblib.dump(meta_model, f'{symbol}_1d_Temp_Meta_{direction}.pkl')

def simulate(tp_mult, sl_mult):
    all_signals = []
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    
    for symbol in SYMBOLS:
        df = pd.read_csv(f'{symbol}_1d_ML_Features.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        split_idx = int(len(df) * 0.8)
        df = df.iloc[split_idx:].copy()
        df = df.dropna(subset=features)
        
        X = df[features]
        
        for direction in ['Long', 'Short']:
            model = joblib.load(f'{symbol}_1d_Temp_XGB_{direction}.pkl')
            meta = joblib.load(f'{symbol}_1d_Temp_Meta_{direction}.pkl')
            
            p = model.predict_proba(X)[:, 1]
            m_prob = meta.predict_proba(pd.DataFrame({'Primary_Confidence': p, 'Vol_Z_Score': df['Vol_Z_Score'], 'Dist_SMA_200': df['Dist_SMA_200']}))[:, 1]
            df[f'Meta_{direction}'] = m_prob
            
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
    # Target trades where meta confidence > 0.60
    signal_df = master_df[(master_df['Meta_Long'] > 0.60) | (master_df['Meta_Short'] > 0.60)].copy()
    
    open_trades = []
    trade_history = []
    current_capital = CAPITAL
    max_capital = CAPITAL
    max_dd = 0.0
    
    for t in unique_times:
        # Check Exits
        for trade in open_trades[:]:
            sym = trade['symbol']
            if t not in prices_high[sym]: continue
            h, l = prices_high[sym][t], prices_low[sym][t]
            
            closed = False
            pnl = 0
            
            if trade['direction'] == 'Long':
                if l <= trade['sl']: pnl = -trade['risk_amount']; exit_price = trade['sl']; closed = True
                elif h >= trade['tp']: pnl = trade['risk_amount'] * (tp_mult / sl_mult); exit_price = trade['tp']; closed = True
            else:
                if h >= trade['sl']: pnl = -trade['risk_amount']; exit_price = trade['sl']; closed = True
                elif l <= trade['tp']: pnl = trade['risk_amount'] * (tp_mult / sl_mult); exit_price = trade['tp']; closed = True
                
            if closed:
                exit_value = trade['position_size'] * exit_price
                net_pnl = pnl - (exit_value * FEE_RATE)
                current_capital += net_pnl
                if current_capital > max_capital: max_capital = current_capital
                dd = (max_capital - current_capital) / max_capital
                if dd > max_dd: max_dd = dd
                trade_history.append({'net_pnl': net_pnl})
                open_trades.remove(trade)
                
        # Check Entries
        if t in signal_df.index:
            rows = signal_df.loc[[t]]
            for _, row in rows.iterrows():
                sym = row['Symbol']
                if any(tr['symbol'] == sym for tr in open_trades): continue
                
                sym_times = list(prices_open[sym].keys())
                try:
                    next_t = sym_times[sym_times.index(t)+1]
                    entry_price = prices_open[sym][next_t]
                except: continue
                
                atr = row['ATR_14']
                if row['Meta_Long'] > 0.60:
                    dir = 'Long'; tp = entry_price + (tp_mult * atr); sl = entry_price - (sl_mult * atr)
                elif row['Meta_Short'] > 0.60:
                    dir = 'Short'; tp = entry_price - (tp_mult * atr); sl = entry_price + (sl_mult * atr)
                else: continue
                
                risk_amount = current_capital * RISK_PER_TRADE
                sl_dist = abs(entry_price - sl)
                if sl_dist == 0: continue
                position_size = risk_amount / sl_dist
                
                current_capital -= (position_size * entry_price * FEE_RATE)
                
                open_trades.append({
                    'symbol': sym, 'direction': dir, 'entry_price': entry_price, 
                    'tp': tp, 'sl': sl, 'risk_amount': risk_amount, 'position_size': position_size
                })
                
    wins = [t for t in trade_history if t['net_pnl'] > 0]
    total_trades = len(trade_history)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    return current_capital, total_trades, win_rate, max_dd

if __name__ == '__main__':
    print("==========================================================")
    print("1-DAY TIMEFRAME EXPLORER: FINDING THE PERFECT TREND TRADES")
    print("==========================================================")
    
    # Let's test combinations that make trades go "lambe" (long trends)
    combinations = [
        (4.0, 1.5), # RR 1:2.66
        (5.0, 1.5), # RR 1:3.33
        (6.0, 2.0), # RR 1:3.0
        (8.0, 2.0)  # RR 1:4.0 (Huge trends)
    ]
    
    for tp, sl in combinations:
        print(f"\nTesting Possibility: TP={tp}x ATR, SL={sl}x ATR (RR 1:{tp/sl:.2f})")
        generate_labels(tp, sl)
        train_all_models()
        final_cap, trades, wr, dd = simulate(tp, sl)
        
        print(f"  -> Total Trades: {trades}")
        print(f"  -> Win Rate: {wr:.2f}% (Breakeven is {100 / (1 + (tp/sl)):.2f}%)")
        print(f"  -> Max Drawdown: {dd*100:.2f}%")
        print(f"  -> Final Capital: ${final_cap:.2f}")
