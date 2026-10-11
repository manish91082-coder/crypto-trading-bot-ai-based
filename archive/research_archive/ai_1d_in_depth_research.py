import pandas as pd
import numpy as np
import joblib

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT']
CAPITAL = 120.0
FEE_RATE = 0.00075

def simulate_advanced(tp_mult, sl_mult, meta_threshold, risk_per_trade):
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
            except Exception as e:
                df[f'Meta_{direction}'] = 0.0
            
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
    signal_df = master_df[(master_df['Meta_Long'] > meta_threshold) | (master_df['Meta_Short'] > meta_threshold)].copy()
    
    open_trades = []
    trade_history = []
    current_capital = CAPITAL
    max_capital = CAPITAL
    max_dd = 0.0
    
    max_concurrent_trades = 0
    
    for t in unique_times:
        # Track max concurrent trades
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
                if row['Meta_Long'] > meta_threshold:
                    dir = 'Long'; tp = entry_price + (tp_mult * atr); sl = entry_price - (sl_mult * atr)
                elif row['Meta_Short'] > meta_threshold:
                    dir = 'Short'; tp = entry_price - (tp_mult * atr); sl = entry_price + (sl_mult * atr)
                else: continue
                
                risk_amount = current_capital * risk_per_trade
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
    print("IN-DEPTH RESEARCH: PROFIT MAXIMIZATION & LOSS MINIMIZATION (1D)")
    print("===============================================================")
    
    # We use the (5.0, 1.5) model which had RR 1:3.33, as it was highly balanced.
    tp = 5.0
    sl = 1.5
    print(f"Base Model: Target {tp}x ATR, Stop Loss {sl}x ATR (RR 1:{tp/sl:.2f})")
    
    # 1. LOSS MINIMIZATION: Testing Strict Meta-Model Thresholds
    print("\n[PART 1] LOSS MINIMIZATION (Finding Perfect Trades via Confidence Thresholds)")
    print("Risk = 2% per trade")
    for threshold in [0.60, 0.65, 0.70, 0.75, 0.80]:
        cap, trades, wr, dd, max_con = simulate_advanced(tp, sl, meta_threshold=threshold, risk_per_trade=0.02)
        print(f"Threshold: {threshold*100}% | Trades: {trades} | Win Rate: {wr:.2f}% | Max Drawdown: {dd*100:.2f}%")
        
    # 2. PROFIT MAXIMIZATION: Capital Allocation Research
    print("\n[PART 2] PROFIT MAXIMIZATION (Capital Allocation / Risk Per Trade)")
    print("Using optimal strict threshold of 75%")
    for risk in [0.02, 0.05, 0.10, 0.15]:
        cap, trades, wr, dd, max_con = simulate_advanced(tp, sl, meta_threshold=0.75, risk_per_trade=risk)
        print(f"Risk Per Trade: {risk*100}% | Max Concurrent Trades: {max_con} | Max Drawdown: {dd*100:.2f}% | Final Capital: ${cap:.2f}")

    print("\n[PART 3] THE PERFECT COMBINATION FOR 1-DAY")
    cap, trades, wr, dd, max_con = simulate_advanced(tp, sl, meta_threshold=0.75, risk_per_trade=0.10)
    print(f"If we use 75% Confidence Filter + 10% Risk Allocation:")
    print(f"-> Total Trades: {trades}")
    print(f"-> Win Rate: {wr:.2f}%")
    print(f"-> Max Concurrent Portfolio Exposure: {max_con * 10}%")
    print(f"-> Final Capital: ${cap:.2f}")
