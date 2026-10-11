import sys
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
from datetime import datetime

# Dynamically resolve SRC directory for relative imports
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_PROCESSED_DIR, MODELS_15M_DIR, LOGS_DIR, SYMBOLS

def run_execution_simulation():
    print("==================================================")
    print("STEP 5: ULTIMATE EXECUTION & COMPOUNDING BACKTEST")
    print("==================================================")
    
    START_DATE = '2025-01-01'
    CAPITAL = 120.0
    RISK_PER_TRADE = 0.02
    FEE_RATE = 0.00075
    
    # 1. Pre-calculate all predictions for OOS period
    print("Loading Models and Pre-Calculating OOS Predictions (2025+)...")
    all_signals = []
    
    features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
    
    for symbol in SYMBOLS:
        feat_path = DATA_PROCESSED_DIR / f'{symbol}_15m_ML_Features.csv'
        try:
            df = pd.read_csv(feat_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Use strict 80% split for Out-Of-Sample
            split_idx = int(len(df) * 0.8)
            df = df.iloc[split_idx:].copy()
            df = df.dropna(subset=features)
            
            X = df[features]
            
            # Predict Longs
            model_L = joblib.load(MODELS_15M_DIR / f'{symbol}_XGBoost_Long.pkl')
            meta_L = joblib.load(MODELS_15M_DIR / f'{symbol}_MetaModel_Long.pkl')
            prob_L = model_L.predict_proba(X)[:, 1]
            meta_X_L = pd.DataFrame({'Primary_Confidence': prob_L, 'Vol_Z_Score': df['Vol_Z_Score'], 'Dist_SMA_200': df['Dist_SMA_200']})
            meta_prob_L = meta_L.predict_proba(meta_X_L)[:, 1]
            
            # Predict Shorts
            model_S = joblib.load(MODELS_15M_DIR / f'{symbol}_XGBoost_Short.pkl')
            meta_S = joblib.load(MODELS_15M_DIR / f'{symbol}_MetaModel_Short.pkl')
            prob_S = model_S.predict_proba(X)[:, 1]
            meta_X_S = pd.DataFrame({'Primary_Confidence': prob_S, 'Vol_Z_Score': df['Vol_Z_Score'], 'Dist_SMA_200': df['Dist_SMA_200']})
            meta_prob_S = meta_S.predict_proba(meta_X_S)[:, 1]
            
            df['Prob_L'] = prob_L
            df['Meta_L'] = meta_prob_L
            df['Prob_S'] = prob_S
            df['Meta_S'] = meta_prob_S
            df['Symbol'] = symbol
            
            all_signals.append(df)
            print(f"  -> Processed {symbol}")
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            
    print("\nMerging and Sorting Timeline...")
    master_df = pd.concat(all_signals)
    master_df.reset_index(inplace=True)
    master_df.sort_values('timestamp', inplace=True)
    master_df.set_index('timestamp', inplace=True)
    
    # 2. Chronological Portfolio Simulation
    print(f"\nStarting Portfolio Simulation with ${CAPITAL} Capital...")
    
    open_trades = []
    trade_history = []
    current_capital = CAPITAL
    max_capital = CAPITAL
    max_drawdown = 0.0
    
    signal_mask = ((master_df['Meta_L'] > 0.70) | (master_df['Meta_S'] > 0.70))
    signal_df = master_df[signal_mask].copy()
    
    print(f"Total potential high-confidence signals across all coins: {len(signal_df)}")
    
    unique_times = master_df.index.unique().sort_values()
    
    prices_high = {}
    prices_low = {}
    prices_open = {}
    for sym in SYMBOLS:
        df_sym = all_signals[SYMBOLS.index(sym)] if sym in SYMBOLS else master_df[master_df['Symbol'] == sym]
        prices_high[sym] = df_sym['high'].to_dict()
        prices_low[sym] = df_sym['low'].to_dict()
        prices_open[sym] = df_sym['open'].to_dict()
    
    for t in unique_times:
        # 1. Update Open Trades (Check SL/TP)
        for trade in open_trades[:]:
            sym = trade['symbol']
            
            if t not in prices_high[sym]:
                continue
                
            h = prices_high[sym][t]
            l = prices_low[sym][t]
            
            # Pessimistic execution: Check SL first, then TP
            closed = False
            pnl = 0
            exit_price = 0
            reason = ""
            
            if trade['direction'] == 'Long':
                if l <= trade['sl']:
                    exit_price = trade['sl']
                    pnl = -trade['risk_amount']
                    reason = "SL Hit"
                    closed = True
                elif h >= trade['tp']:
                    exit_price = trade['tp']
                    pnl = trade['risk_amount'] * 1.5
                    reason = "TP Hit"
                    closed = True
            else: # Short
                if h >= trade['sl']:
                    exit_price = trade['sl']
                    pnl = -trade['risk_amount']
                    reason = "SL Hit"
                    closed = True
                elif l <= trade['tp']:
                    exit_price = trade['tp']
                    pnl = trade['risk_amount'] * 1.5
                    reason = "TP Hit"
                    closed = True
                    
            if closed:
                exit_value = trade['position_size'] * exit_price
                exit_fee = exit_value * FEE_RATE
                net_pnl = pnl - exit_fee
                
                current_capital += net_pnl
                
                if current_capital > max_capital:
                    max_capital = current_capital
                dd = (max_capital - current_capital) / max_capital
                if dd > max_drawdown:
                    max_drawdown = dd
                    
                trade['exit_time'] = t
                trade['exit_price'] = exit_price
                trade['net_pnl'] = net_pnl
                trade['capital_after'] = current_capital
                trade['reason'] = reason
                trade_history.append(trade)
                open_trades.remove(trade)
                
        # 2. Check for New Entries
        if t in signal_df.index:
            rows = signal_df.loc[[t]]
            for _, row in rows.iterrows():
                sym = row['Symbol']
                
                if any(tr['symbol'] == sym for tr in open_trades):
                    continue
                    
                sym_times = list(prices_open[sym].keys())
                try:
                    idx = sym_times.index(t)
                    next_t = sym_times[idx+1]
                    entry_price = prices_open[sym][next_t]
                except (ValueError, IndexError):
                    continue
                    
                atr = row['ATR_14']
                
                if row['Meta_L'] > 0.70:
                    dir = 'Long'
                    tp = entry_price + (3.0 * atr)
                    sl = entry_price - (2.0 * atr)
                elif row['Meta_S'] > 0.70:
                    dir = 'Short'
                    tp = entry_price - (3.0 * atr)
                    sl = entry_price + (2.0 * atr)
                else:
                    continue
                    
                risk_amount = current_capital * RISK_PER_TRADE
                sl_dist = abs(entry_price - sl)
                if sl_dist == 0: continue
                
                position_size = risk_amount / sl_dist
                entry_value = position_size * entry_price
                entry_fee = entry_value * FEE_RATE
                
                current_capital -= entry_fee
                
                new_trade = {
                    'symbol': sym,
                    'direction': dir,
                    'entry_time': next_t,
                    'entry_price': entry_price,
                    'tp': tp,
                    'sl': sl,
                    'risk_amount': risk_amount,
                    'position_size': position_size
                }
                open_trades.append(new_trade)
                
    print("\n==================================================")
    print("SIMULATION COMPLETE")
    print("==================================================")
    
    wins = [t for t in trade_history if t['net_pnl'] > 0]
    total_trades = len(trade_history)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    print(f"Initial Capital: $120.00")
    print(f"Final Capital: ${current_capital:.2f}")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Max Drawdown: {max_drawdown*100:.2f}%")
    
    # Save Trade History to logs/
    out_log = LOGS_DIR / "Step5_Trade_Log.csv"
    pd.DataFrame(trade_history).to_csv(out_log, index=False)
    print(f"Detailed Trade Log saved to {out_log}")

if __name__ == '__main__':
    run_execution_simulation()
