import pandas as pd
import numpy as np
import joblib

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT']
CAPITAL = 120.0
FEE_RATE = 0.00075
RISK_PER_TRADE = 0.05 # Let's test 5% risk now that we are filtering

def simulate_with_macro_filter(tp_mult, sl_mult, meta_threshold):
    # 1. Load BTC Data to create the Macro Regime Filter
    btc_df = pd.read_csv('BTCUSDT_1d_ML_Features.csv')
    btc_df['timestamp'] = pd.to_datetime(btc_df['timestamp'])
    btc_df.set_index('timestamp', inplace=True)
    
    # Define Macro Regime: 1 = Bull (BTC > SMA_50), -1 = Bear (BTC < SMA_50)
    btc_df['Macro_Regime'] = np.where(btc_df['close'] > btc_df['SMA_50'], 1, -1)
    macro_series = btc_df['Macro_Regime'].to_dict()

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
            try:
                model = joblib.load(f'{symbol}_1d_Temp_XGB_{direction}.pkl')
                meta = joblib.load(f'{symbol}_1d_Temp_Meta_{direction}.pkl')
                
                p = model.predict_proba(X)[:, 1]
                m_prob = meta.predict_proba(pd.DataFrame({'Primary_Confidence': p, 'Vol_Z_Score': df['Vol_Z_Score'], 'Dist_SMA_200': df['Dist_SMA_200']}))[:, 1]
                df[f'Meta_{direction}'] = m_prob
            except:
                df[f'Meta_{direction}'] = 0.0
                
        df['Symbol'] = symbol
        # Apply Macro Regime map
        df['Macro'] = df.index.map(macro_series)
        
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
    
    # 2. FILTER SIGNALS: Only take Longs if Macro == 1, Shorts if Macro == -1
    # This is the Ground Level Evidence filter.
    mask_long = (master_df['Meta_Long'] > meta_threshold) & (master_df['Macro'] == 1)
    mask_short = (master_df['Meta_Short'] > meta_threshold) & (master_df['Macro'] == -1)
    
    signal_df = master_df[mask_long | mask_short].copy()
    
    print(f"Total potential signals BEFORE Macro Filter: {len(master_df[(master_df['Meta_Long'] > meta_threshold) | (master_df['Meta_Short'] > meta_threshold)])}")
    print(f"Total potential signals AFTER Macro Filter: {len(signal_df)}")
    
    open_trades = []
    trade_history = []
    current_capital = CAPITAL
    max_capital = CAPITAL
    max_dd = 0.0
    
    max_concurrent_trades = 0
    
    for t in unique_times:
        if len(open_trades) > max_concurrent_trades:
            max_concurrent_trades = len(open_trades)
            
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
                
                # Double-check the macro rule before entering
                if row['Meta_Long'] > meta_threshold and row['Macro'] == 1:
                    dir = 'Long'; tp = entry_price + (tp_mult * atr); sl = entry_price - (sl_mult * atr)
                elif row['Meta_Short'] > meta_threshold and row['Macro'] == -1:
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
    return current_capital, total_trades, win_rate, max_dd, max_concurrent_trades

if __name__ == '__main__':
    print("===============================================================")
    print("GROUND LEVEL MACRO TREND FILTER TEST (1D)")
    print("===============================================================")
    
    tp = 5.0
    sl = 1.5
    meta_threshold = 0.70
    
    print(f"Base Configuration: RR 1:{tp/sl:.2f}, Threshold {meta_threshold*100}%")
    print("Rule: NO LONGS if BTC < 50 SMA. NO SHORTS if BTC > 50 SMA.")
    
    print("\nSimulating with Macro Filter...")
    cap, trades, wr, dd, max_con = simulate_with_macro_filter(tp, sl, meta_threshold)
    
    print(f"\n[RESULTS AFTER MACRO FILTER]")
    print(f"Risk Per Trade: {RISK_PER_TRADE*100}%")
    print(f"-> Total Trades: {trades}")
    print(f"-> Win Rate: {wr:.2f}%")
    print(f"-> Max Drawdown: {dd*100:.2f}%")
    print(f"-> Max Concurrent Portfolio Exposure: {max_con * RISK_PER_TRADE * 100:.1f}%")
    print(f"-> Final Capital: ${cap:.2f}")
