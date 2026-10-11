import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Dynamically resolve SRC directory for relative imports
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import LOGS_DIR

def analyze_logs():
    trade_log_file = LOGS_DIR / 'ai_final_aggressive_1d_trade_log.csv'
    daily_log_file = LOGS_DIR / 'ai_final_aggressive_1d_daily_capital.csv'
    
    try:
        trades = pd.read_csv(trade_log_file)
        daily = pd.read_csv(daily_log_file)
    except Exception as e:
        print("Error loading CSV files from logs directory:", e)
        return

    # Process daily capital to find monthly PNL
    daily['Date'] = pd.to_datetime(daily['Date'])
    daily.set_index('Date', inplace=True)
    
    monthly_stats = daily['Capital'].resample('ME').last()
    
    print("=== MONTHLY PNL ANALYSIS ===")
    prev_cap = 120.0
    monthly_returns = []
    
    for date, cap in monthly_stats.items():
        if pd.isna(cap): continue
        pnl_abs = cap - prev_cap
        pnl_pct = (pnl_abs / prev_cap) * 100
        monthly_returns.append({'Month': date.strftime('%Y-%m'), 'Absolute': pnl_abs, 'Pct': pnl_pct, 'Capital': cap})
        prev_cap = cap
        
    df_months = pd.DataFrame(monthly_returns)
    
    best_month_pct = df_months.loc[df_months['Pct'].idxmax()]
    worst_month_pct = df_months.loc[df_months['Pct'].idxmin()]
    
    best_month_abs = df_months.loc[df_months['Absolute'].idxmax()]
    worst_month_abs = df_months.loc[df_months['Absolute'].idxmin()]
    
    print(f"\n[+] BEST MONTH (By % Return): {best_month_pct['Month']} (+{best_month_pct['Pct']:.2f}% | +${best_month_pct['Absolute']:.2f})")
    print(f"[-] WORST MONTH (By % Return): {worst_month_pct['Month']} ({worst_month_pct['Pct']:.2f}% | -${abs(worst_month_pct['Absolute']):.2f})")
    
    print(f"\n[+] BEST MONTH (By Absolute $): {best_month_abs['Month']} (+${best_month_abs['Absolute']:.2f})")
    print(f"[-] WORST MONTH (By Absolute $): {worst_month_abs['Month']} (-${abs(worst_month_abs['Absolute']):.2f})")
    
    print("\n=== TOP 5 MOST PROFITABLE MONTHS ===")
    top_5 = df_months.sort_values(by='Absolute', ascending=False).head(5)
    for _, row in top_5.iterrows():
        print(f" - {row['Month']}: +${row['Absolute']:.2f} (+{row['Pct']:.2f}%)")
        
    print("\n=== TOP 5 WORST LOSING MONTHS ===")
    worst_5 = df_months.sort_values(by='Absolute', ascending=True).head(5)
    for _, row in worst_5.iterrows():
        print(f" - {row['Month']}: -${abs(row['Absolute']):.2f} ({row['Pct']:.2f}%)")
        
    print("\n=== COIN PERFORMANCE (WIN RATE & PNL) ===")
    coin_group = trades.groupby('symbol').agg(
        Total_Trades=('symbol', 'count'),
        Wins=('realized_pnl', lambda x: (x > 0).sum()),
        Total_PNL=('realized_pnl', 'sum')
    )
    coin_group['Win_Rate'] = (coin_group['Wins'] / coin_group['Total_Trades']) * 100
    coin_group = coin_group.sort_values(by='Total_PNL', ascending=False)
    
    for sym, row in coin_group.iterrows():
        print(f"{sym}: {row['Total_Trades']} Trades | {row['Win_Rate']:.2f}% Win Rate | PNL: ${row['Total_PNL']:.2f}")

if __name__ == '__main__':
    analyze_logs()
