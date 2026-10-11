import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT']
CAPITAL = 120.0
FEE_RATE = 0.00075
META_THRESHOLD = 0.80

def run_5year_aggressive_v2_backtest():
    all_signals = []
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    
    print("Loading 5-Year Data for Aggressive V2 Simulation...")
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
    
    print("Running Aggressive V2 Day-by-Day Simulation...")
    for t in unique_times:
        month_str = pd.to_datetime(t).strftime('%Y-%m')
        if current_month is None:
            current_month = month_str
        elif month_str != current_month:
            monthly_logs.append({'Month': current_month, 'Capital': current_capital})
            current_month = month_str
            
        # Check Exits & Pyramiding
        for trade in open_trades[:]:
            sym = trade['symbol']
            if t not in prices_high[sym]: continue
            h, l, o = prices_high[sym][t], prices_low[sym][t], prices_open[sym][t]
            
            days_open = (t - trade['entry_time']).days
            closed = False
            exit_price = 0
            
            # Loss Minimization: Time-Based Exit (7 days)
            if days_open >= 7 and not trade['secured']:
                exit_price = o 
                closed = True
                trade['exit_reason'] = 'Time-Based Exit'
            
            if not closed:
                # 1. PULLBACK PYRAMIDING CHECK
                if not trade['secured'] and not trade['pyramided']:
                    if trade['direction'] == 'Long' and l <= trade['base_entry'] - 1.0 * trade['atr']:
                        # Add second bullet
                        pyramid_price = trade['base_entry'] - 1.0 * trade['atr']
                        pyramid_sl_dist = abs(pyramid_price - trade['sl'])
                        if pyramid_sl_dist > 0:
                            # Apply Anti-Drawdown compounding dynamically
                            dd_current = (max_capital - current_capital) / max_capital
                            dyn_bullet_risk = trade['bullet_risk_pct'] if dd_current < 0.20 else (trade['bullet_risk_pct'] / 2)
                            
                            pyramid_risk_amount = current_capital * dyn_bullet_risk
                            pyramid_pos = pyramid_risk_amount / pyramid_sl_dist
                            
                            entry_fee = pyramid_pos * pyramid_price * FEE_RATE
                            current_capital -= entry_fee
                            
                            total_value = (trade['entry_price'] * trade['position_size']) + (pyramid_price * pyramid_pos)
                            total_pos = trade['position_size'] + pyramid_pos
                            trade['entry_price'] = total_value / total_pos
                            trade['position_size'] = total_pos
                            trade['risk_amount'] += pyramid_risk_amount
                            trade['pyramided'] = True
                            
                    elif trade['direction'] == 'Short' and h >= trade['base_entry'] + 1.0 * trade['atr']:
                        # Add second bullet
                        pyramid_price = trade['base_entry'] + 1.0 * trade['atr']
                        pyramid_sl_dist = abs(pyramid_price - trade['sl'])
                        if pyramid_sl_dist > 0:
                            dd_current = (max_capital - current_capital) / max_capital
                            dyn_bullet_risk = trade['bullet_risk_pct'] if dd_current < 0.20 else (trade['bullet_risk_pct'] / 2)
                            
                            pyramid_risk_amount = current_capital * dyn_bullet_risk
                            pyramid_pos = pyramid_risk_amount / pyramid_sl_dist
                            
                            entry_fee = pyramid_pos * pyramid_price * FEE_RATE
                            current_capital -= entry_fee
                            
                            total_value = (trade['entry_price'] * trade['position_size']) + (pyramid_price * pyramid_pos)
                            total_pos = trade['position_size'] + pyramid_pos
                            trade['entry_price'] = total_value / total_pos
                            trade['position_size'] = total_pos
                            trade['risk_amount'] += pyramid_risk_amount
                            trade['pyramided'] = True

                # 2. EXIT CHECKS
                if trade['direction'] == 'Long':
                    if l <= trade['sl']:
                        exit_price = trade['sl']
                        closed = True
                        trade['exit_reason'] = 'Stop Loss'
                    else:
                        if not trade['secured'] and h >= trade['entry_price'] + 3.0 * trade['atr']:
                            exit_price_partial = trade['entry_price'] + 3.0 * trade['atr']
                            pnl_partial = (exit_price_partial - trade['entry_price']) * (trade['position_size'] / 2)
                            fee_partial = exit_price_partial * (trade['position_size'] / 2) * FEE_RATE
                            net_pnl_partial = pnl_partial - fee_partial
                            current_capital += net_pnl_partial
                            trade['realized_pnl'] += net_pnl_partial
                            
                            trade['position_size'] /= 2
                            trade['risk_amount'] /= 2
                            trade['secured'] = True
                            trade['sl'] = max(trade['sl'], trade['entry_price'] + 1.0 * trade['atr'])
                            
                        if trade['secured']:
                            trade['sl'] = max(trade['sl'], h - 2.0 * trade['atr'])
                            
                        if not trade['secured'] and h >= trade['entry_price'] + 2.0 * trade['atr']:
                            trade['sl'] = max(trade['sl'], trade['entry_price'])
                            
                else: # Short
                    if h >= trade['sl']:
                        exit_price = trade['sl']
                        closed = True
                        trade['exit_reason'] = 'Stop Loss'
                    else:
                        if not trade['secured'] and l <= trade['entry_price'] - 3.0 * trade['atr']:
                            exit_price_partial = trade['entry_price'] - 3.0 * trade['atr']
                            pnl_partial = (trade['entry_price'] - exit_price_partial) * (trade['position_size'] / 2)
                            fee_partial = exit_price_partial * (trade['position_size'] / 2) * FEE_RATE
                            net_pnl_partial = pnl_partial - fee_partial
                            current_capital += net_pnl_partial
                            trade['realized_pnl'] += net_pnl_partial
                            
                            trade['position_size'] /= 2
                            trade['risk_amount'] /= 2
                            trade['secured'] = True
                            trade['sl'] = min(trade['sl'], trade['entry_price'] - 1.0 * trade['atr'])
                            
                        if trade['secured']:
                            trade['sl'] = min(trade['sl'], l + 2.0 * trade['atr'])
                            
                        if not trade['secured'] and l <= trade['entry_price'] - 2.0 * trade['atr']:
                            trade['sl'] = min(trade['sl'], trade['entry_price'])
                            
            if closed:
                if trade['direction'] == 'Long':
                    pnl = (exit_price - trade['entry_price']) * trade['position_size']
                else:
                    pnl = (trade['entry_price'] - exit_price) * trade['position_size']
                    
                exit_fee = exit_price * trade['position_size'] * FEE_RATE
                final_pnl = pnl - exit_fee
                current_capital += final_pnl
                trade['realized_pnl'] += final_pnl
                
                if current_capital > max_capital: max_capital = current_capital
                dd = (max_capital - current_capital) / max_capital
                if dd > max_dd: max_dd = dd
                
                trade['exit_time'] = t
                trade_history.append(trade)
                open_trades.remove(trade)
                
        # 3. Check Entries
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
                sl_mult_initial = 1.5
                if row['Meta_Long'] > META_THRESHOLD:
                    dir = 'Long'
                    sl = entry_price - (sl_mult_initial * atr)
                elif row['Meta_Short'] > META_THRESHOLD:
                    dir = 'Short'
                    sl = entry_price + (sl_mult_initial * atr)
                else: continue
                
                # ANTI-DRAWDOWN COMPOUNDING RULE
                dd_current = (max_capital - current_capital) / max_capital
                risk_pct = 0.05 if dd_current < 0.20 else 0.025
                bullet_risk = risk_pct / 2.0  # Split into 2 bullets for pyramiding
                
                initial_risk_amount = current_capital * bullet_risk
                sl_dist = abs(entry_price - sl)
                if sl_dist == 0: continue
                position_size = initial_risk_amount / sl_dist
                
                entry_fee = position_size * entry_price * FEE_RATE
                current_capital -= entry_fee
                
                open_trades.append({
                    'symbol': sym, 'direction': dir, 'entry_time': next_t, 
                    'base_entry': entry_price, 'entry_price': entry_price, 
                    'sl': sl, 'risk_amount': initial_risk_amount, 'position_size': position_size,
                    'atr': atr, 'secured': False, 'realized_pnl': 0.0,
                    'pyramided': False, 'bullet_risk_pct': bullet_risk
                })
                
    if current_month:
        monthly_logs.append({'Month': current_month, 'Capital': current_capital})
                
    wins = [t for t in trade_history if t['realized_pnl'] > 0]
    total_trades = len(trade_history)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    print("\n==========================================================")
    print("AGGRESSIVE V2 5-YEAR BACKTEST (Anti-Drawdown & Pyramiding)")
    print("==========================================================")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")
    print(f"Initial Capital: ${CAPITAL:.2f}")
    print(f"Final Capital: ${current_capital:.2f}")
    
    print("\n--- MONTHLY CAPITAL BREAKDOWN ---")
    for log in monthly_logs:
        print(f"[{log['Month']}] Capital: ${log['Capital']:.2f}")

if __name__ == '__main__':
    run_5year_aggressive_v2_backtest()
