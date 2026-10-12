"""
Calibrated Model Threshold & Trade Frequency Analyzer (2021 - 2026)
Tests how trade count, profit factor, and net return scale across:
threshold_long in [0.44, 0.46, 0.48, 0.50, 0.52]
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline_1d.step7_full_5year_governed_backtest import load_data_and_features, run_simulation
from config import LOGS_DIR

def run_threshold_grid():
    master_df, prices_ohlc, btc_bullish_map = load_data_and_features()
    
    thresholds = [0.44, 0.46, 0.48, 0.50, 0.52]
    results = []
    
    print("==========================================================================")
    print("CALIBRATING MODEL THRESHOLD: TRADE COUNT & RETURN SCALING (5 YEARS)")
    print("==========================================================================")
    
    for th in thresholds:
        summary, df_tr, df_daily = run_simulation(
            master_df=master_df,
            prices_ohlc=prices_ohlc,
            btc_bullish_map=btc_bullish_map,
            mode='spot',
            threshold_long=th,
            threshold_short=th,
            max_concurrent=3
        )
        
        n_tr = len(df_tr)
        if n_tr == 0:
            continue
            
        wins = df_tr[df_tr['realized_pnl'] > 0]
        losses = df_tr[df_tr['realized_pnl'] <= 0]
        wr = (len(wins) / n_tr) * 100.0
        
        gross_win = wins['realized_pnl'].sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses['realized_pnl'].sum()) if len(losses) > 0 else 1e-8
        pf = gross_win / gross_loss
        total_pnl = df_tr['realized_pnl'].sum()
        roi_pct = (total_pnl / 120.0) * 100.0
        
        max_dd = df_daily['drawdown'].max() * 100.0
        
        results.append({
            'Threshold': th,
            'Total_Trades': n_tr,
            'Trades_Per_Year': round(n_tr / 5.0, 1),
            'Trades_Per_Month': round(n_tr / 60.0, 1),
            'Win_Rate_Pct': round(wr, 2),
            'Profit_Factor': round(pf, 2),
            'Final_Capital': round(120.0 + total_pnl, 2),
            'Net_Return_Pct': round(roi_pct, 2),
            'Max_DD_Pct': round(max_dd, 2)
        })
        
        print(f"Threshold: {th:.2f} | Trades: {n_tr:>3} ({n_tr/5.0:.1f}/yr, {n_tr/60.0:.1f}/mo) | Win Rate: {wr:.1f}% | PF: {pf:.2f} | Capital: ${120.0+total_pnl:.2f} ({roi_pct:+.1f}%) | Max DD: {max_dd:.1f}%")
        
    df_res = pd.DataFrame(results)
    out_csv = LOGS_DIR / "threshold_trade_scaling_analysis.csv"
    df_res.to_csv(out_csv, index=False)
    print(f"\n[+] Saved Threshold Scaling Analysis to: {out_csv.name}")

if __name__ == '__main__':
    run_threshold_grid()
