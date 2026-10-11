import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import LOGS_DIR

def run_detailed_metrics():
    trade_file = LOGS_DIR / 'ai_final_aggressive_1d_trade_log.csv'
    daily_file = LOGS_DIR / 'ai_final_aggressive_1d_daily_capital.csv'

    trades = pd.read_csv(trade_file)
    daily = pd.read_csv(daily_file)

    wins = trades[trades['realized_pnl'] > 0]
    losses = trades[trades['realized_pnl'] <= 0]

    gross_profit = wins['realized_pnl'].sum()
    gross_loss = abs(losses['realized_pnl'].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else np.nan

    avg_win = wins['realized_pnl'].mean()
    avg_loss = abs(losses['realized_pnl'].mean())
    payoff = avg_win / avg_loss if avg_loss > 0 else np.nan

    print("==================================================")
    print("DETAILED QUANTITATIVE EVIDENCE REPORT (1D AGGRESSIVE)")
    print("==================================================")
    print(f"Total Closed Trades: {len(trades)}")
    print(f"Winning Trades:      {len(wins)} ({len(wins)/len(trades)*100:.2f}%)")
    print(f"Losing Trades:       {len(losses)} ({len(losses)/len(trades)*100:.2f}%)")
    print(f"Gross Profit:        ${gross_profit:,.2f}")
    print(f"Gross Loss:          ${gross_loss:,.2f}")
    print(f"Profit Factor:       {pf:.3f}")
    print(f"Average Win:         ${avg_win:,.2f}")
    print(f"Average Loss:        ${avg_loss:,.2f}")
    print(f"Win/Loss Payoff:     {payoff:.3f}")

    print("\n--- PERFORMANCE BY DIRECTION ---")
    for d in ['Long', 'Short']:
        sub = trades[trades['direction'] == d]
        sub_w = sub[sub['realized_pnl'] > 0]
        sub_pnl = sub['realized_pnl'].sum()
        sub_wr = (len(sub_w) / len(sub) * 100) if len(sub) > 0 else 0
        print(f"  {d:<6} | Trades: {len(sub):>3} | Win Rate: {sub_wr:>5.2f}% | Net PnL: ${sub_pnl:>12,.2f}")

    print("\n--- EXIT REASONS BREAKDOWN ---")
    exit_counts = trades['exit_reason'].value_counts()
    for reason, count in exit_counts.items():
        sub = trades[trades['exit_reason'] == reason]
        sub_pnl = sub['realized_pnl'].sum()
        print(f"  {reason:<18} | Count: {count:>3} ({count/len(trades)*100:>5.1f}%) | Net PnL: ${sub_pnl:>12,.2f}")

    # Daily Return Statistics (Sharpe / Sortino)
    daily['Date'] = pd.to_datetime(daily['Date'])
    daily.drop_duplicates(subset=['Date'], keep='last', inplace=True)
    daily.set_index('Date', inplace=True)
    daily['Daily_Return'] = daily['Capital'].pct_change().fillna(0)

    trading_days = len(daily)
    mean_daily_return = daily['Daily_Return'].mean()
    std_daily_return = daily['Daily_Return'].std()
    downside_std = daily[daily['Daily_Return'] < 0]['Daily_Return'].std()

    ann_factor = 365 # Crypto trades 365 days a year
    cagr = ((daily['Capital'].iloc[-1] / daily['Capital'].iloc[0]) ** (365 / trading_days) - 1) * 100
    sharpe = (mean_daily_return / std_daily_return * np.sqrt(ann_factor)) if std_daily_return > 0 else np.nan
    sortino = (mean_daily_return / downside_std * np.sqrt(ann_factor)) if downside_std > 0 else np.nan

    # Peak & Drawdown Series
    daily['Peak'] = daily['Capital'].cummax()
    daily['Drawdown'] = (daily['Peak'] - daily['Capital']) / daily['Peak']
    max_dd = daily['Drawdown'].max() * 100

    print("\n--- RISK-ADJUSTED RETURN METRICS (CRYPTO 365-DAY ANNUALIZED) ---")
    print(f"Total Simulation Days: {trading_days} days (from {daily.index[0].strftime('%Y-%m-%d')} to {daily.index[-1].strftime('%Y-%m-%d')})")
    print(f"Initial Capital:       ${daily['Capital'].iloc[0]:,.2f}")
    print(f"Final Capital:         ${daily['Capital'].iloc[-1]:,.2f}")
    print(f"Total Net Return:      {((daily['Capital'].iloc[-1]-daily['Capital'].iloc[0])/daily['Capital'].iloc[0])*100:,.2f}%")
    print(f"CAGR (Annualized):     {cagr:.2f}%")
    print(f"Max Peak Capital:      ${daily['Peak'].max():,.2f} on {daily['Capital'].idxmax().strftime('%Y-%m-%d')}")
    print(f"Max Drawdown:          {max_dd:.2f}%")
    print(f"Daily Mean Return:     {mean_daily_return*100:.3f}%")
    print(f"Daily Volatility:      {std_daily_return*100:.3f}%")
    print(f"Annualized Sharpe:     {sharpe:.2f}")
    print(f"Annualized Sortino:    {sortino:.2f}")
    print(f"Calmar Ratio (CAGR/DD):{cagr / max_dd:.2f}")
    print("==================================================")

if __name__ == '__main__':
    run_detailed_metrics()
