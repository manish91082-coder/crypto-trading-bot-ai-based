import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT']
CAPITAL = 120.0
RISK_PER_TRADE = 0.05
FEE_RATE = 0.00075
TP_MULT = 5.0
SL_MULT = 1.5
META_THRESHOLD = 0.80

def run_5year_backtest():
    all_signals = []
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    
    print("Loading 5-Year Data and Pre-calculating predictions for all 10 coins...")
    for symbol in SYMBOLS:
        df = pd.read_csv(f'{symbol}_1d_ML_Features.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
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
    signal_df = master_df[(master_df['Meta_Long'] > META_THRESHOLD) | (master_df['Meta_Short'] > META_THRESHOLD)].copy()
    
    open_trades = []
    trade_history = []
    current_capital = CAPITAL
    max_capital = CAPITAL
    max_dd = 0.0
    
    monthly_logs = []
    current_month = None
    
    print("Running Day-by-Day Simulation...")
    for t in unique_times:
        month_str = pd.to_datetime(t).strftime('%Y-%m')
        if current_month is None:
            current_month = month_str
        elif month_str != current_month:
            # End of month, log capital
            monthly_logs.append({
                'Month': current_month,
                'Capital': current_capital
            })
            current_month = month_str
            
        # Check Exits
        for trade in open_trades[:]:
            sym = trade['symbol']
            if t not in prices_high[sym]: continue
            h, l = prices_high[sym][t], prices_low[sym][t]
            
            closed = False
            pnl = 0
            
            if trade['direction'] == 'Long':
                if l <= trade['sl']: pnl = -trade['risk_amount']; exit_price = trade['sl']; closed = True
                elif h >= trade['tp']: pnl = trade['risk_amount'] * (TP_MULT / SL_MULT); exit_price = trade['tp']; closed = True
            else:
                if h >= trade['sl']: pnl = -trade['risk_amount']; exit_price = trade['sl']; closed = True
                elif l <= trade['tp']: pnl = trade['risk_amount'] * (TP_MULT / SL_MULT); exit_price = trade['tp']; closed = True
                
            if closed:
                exit_value = trade['position_size'] * exit_price
                net_pnl = pnl - (exit_value * FEE_RATE)
                current_capital += net_pnl
                if current_capital > max_capital: max_capital = current_capital
                dd = (max_capital - current_capital) / max_capital
                if dd > max_dd: max_dd = dd
                trade_history.append({'net_pnl': net_pnl, 'exit_time': t})
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
                if row['Meta_Long'] > META_THRESHOLD:
                    dir = 'Long'; tp = entry_price + (TP_MULT * atr); sl = entry_price - (SL_MULT * atr)
                elif row['Meta_Short'] > META_THRESHOLD:
                    dir = 'Short'; tp = entry_price - (TP_MULT * atr); sl = entry_price + (SL_MULT * atr)
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
                
    # Log the last month
    if current_month:
        monthly_logs.append({
            'Month': current_month,
            'Capital': current_capital
        })
                
    wins = [t for t in trade_history if t['net_pnl'] > 0]
    total_trades = len(trade_history)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    print("\n==========================================================")
    print("5-YEAR FULL BACKTEST COMPLETE (1-DAY TIMEFRAME)")
    print("==========================================================")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")
    print(f"Final Capital: ${current_capital:.2f}")
    print("\n--- MONTHLY CAPITAL BREAKDOWN ---")
    for log in monthly_logs:
        print(f"[{log['Month']}] Capital: ${log['Capital']:.2f}")

if __name__ == '__main__':
    run_5year_backtest()
