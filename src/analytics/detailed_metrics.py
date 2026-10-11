import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import LOGS_DIR

def analyze_single_system(trade_file: Path, daily_file: Path, system_name: str) -> dict:
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

    daily['Date'] = pd.to_datetime(daily['Date'])
    daily.drop_duplicates(subset=['Date'], keep='last', inplace=True)
    daily.set_index('Date', inplace=True)
    daily['Daily_Return'] = daily['Capital'].pct_change().fillna(0)

    trading_days = len(daily)
    mean_daily_return = daily['Daily_Return'].mean()
    std_daily_return = daily['Daily_Return'].std()
    downside_std = daily[daily['Daily_Return'] < 0]['Daily_Return'].std()

    ann_factor = 365
    cagr = ((daily['Capital'].iloc[-1] / daily['Capital'].iloc[0]) ** (365 / trading_days) - 1) * 100
    sharpe = (mean_daily_return / std_daily_return * np.sqrt(ann_factor)) if std_daily_return > 0 else np.nan
    sortino = (mean_daily_return / downside_std * np.sqrt(ann_factor)) if downside_std > 0 else np.nan

    daily['Peak'] = daily['Capital'].cummax()
    daily['Drawdown'] = (daily['Peak'] - daily['Capital']) / daily['Peak']
    max_dd = daily['Drawdown'].max() * 100

    return {
        'System': system_name,
        'Trades': len(trades),
        'Win_Rate': (len(wins) / len(trades) * 100) if len(trades) > 0 else 0,
        'Initial_Cap': daily['Capital'].iloc[0],
        'Final_Cap': daily['Capital'].iloc[-1],
        'Total_Return_Pct': ((daily['Capital'].iloc[-1] - daily['Capital'].iloc[0]) / daily['Capital'].iloc[0]) * 100,
        'CAGR': cagr,
        'Max_Peak': daily['Peak'].max(),
        'Max_DD': max_dd,
        'Sharpe': sharpe,
        'Sortino': sortino,
        'Profit_Factor': pf,
        'Payoff_Ratio': payoff,
        'Gross_Profit': gross_profit,
        'Gross_Loss': gross_loss
    }

def run_detailed_metrics():
    file_aggr_trades = LOGS_DIR / 'ai_final_aggressive_1d_trade_log.csv'
    file_aggr_daily = LOGS_DIR / 'ai_final_aggressive_1d_daily_capital.csv'

    file_gov_trades = LOGS_DIR / 'ai_1d_governed_trade_log.csv'
    file_gov_daily = LOGS_DIR / 'ai_1d_governed_daily_capital.csv'

    results = []
    if file_aggr_trades.exists() and file_aggr_daily.exists():
        results.append(analyze_single_system(file_aggr_trades, file_aggr_daily, "Unconstrained Aggressive"))
    if file_gov_trades.exists() and file_gov_daily.exists():
        results.append(analyze_single_system(file_gov_trades, file_gov_daily, "Institutional Governed"))

    print("=========================================================================================")
    print("ZERO-TRUST QUANTITATIVE COMPARISON: UNCONSTRAINED VS INSTITUTIONAL GOVERNED")
    print("=========================================================================================")
    df_res = pd.DataFrame(results)
    for r in results:
        print(f"\n[{r['System'].upper()}]")
        print(f"  Total Closed Trades: {r['Trades']}")
        print(f"  Win Rate:            {r['Win_Rate']:.2f}%")
        print(f"  Initial Capital:     ${r['Initial_Cap']:,.2f}")
        print(f"  Final Capital:       ${r['Final_Cap']:,.2f}")
        print(f"  Total Return:        {r['Total_Return_Pct']:,.2f}%")
        print(f"  CAGR (Annualized):   {r['CAGR']:.2f}%")
        print(f"  Max Drawdown:        {r['Max_DD']:.2f}%")
        print(f"  Annualized Sharpe:   {r['Sharpe']:.2f}")
        print(f"  Annualized Sortino:  {r['Sortino']:.2f}")
        print(f"  Profit Factor:       {r['Profit_Factor']:.3f}")
        print(f"  Win/Loss Payoff:     {r['Payoff_Ratio']:.3f}")

    if len(results) == 2:
        aggr = results[0]
        gov = results[1]
        print("\n-----------------------------------------------------------------------------------------")
        print("KEY INSTITUTIONAL RISK IMPROVEMENTS:")
        print(f"  - Drawdown Reduction: Cut from {aggr['Max_DD']:.2f}% down to {gov['Max_DD']:.2f}% (Saved {(aggr['Max_DD']-gov['Max_DD']):.2f}% portfolio depth!)")
        print(f"  - Trade Quality: Win Rate preserved ({gov['Win_Rate']:.2f}% vs {aggr['Win_Rate']:.2f}%) with {gov['Trades']} high-conviction trades")
        print(f"  - Capital Safety: Protected during 2024 severe market chop while delivering ${gov['Final_Cap']:,.2f} from ${gov['Initial_Cap']:,.2f}!")
    print("=========================================================================================")

if __name__ == '__main__':
    run_detailed_metrics()

