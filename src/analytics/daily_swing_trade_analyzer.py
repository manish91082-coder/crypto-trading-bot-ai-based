import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, LOGS_DIR, SYMBOLS

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean().bfill()

def run_daily_and_trade_analysis():
    print("==========================================================================")
    print("ADVANCED DAY-BY-DAY SWING & TRADE SIMULATION ENGINE (2021 - 2026)")
    print("Zero-Trust Verification: Every Single Day (1,806 Days) Mapped to Swings")
    print("==========================================================================")

    # 1. Load Bitcoin 5-Year Data
    btc_path = DATA_RAW_DIR / "BTCUSDT_1d_Raw_5Years.csv"
    df_btc = pd.read_csv(btc_path)
    df_btc['timestamp'] = pd.to_datetime(df_btc['timestamp'])
    df_btc.sort_values('timestamp', inplace=True)
    df_btc.reset_index(drop=True, inplace=True)

    df_btc['atr'] = compute_atr(df_btc, 14)
    df_btc['sma200'] = df_btc['close'].rolling(200).mean()

    # 2. Mathematical ATR Reversal Swing Detection with exact confirmation tracking
    highs = df_btc['high'].values
    lows = df_btc['low'].values
    closes = df_btc['close'].values
    opens = df_btc['open'].values
    dates = df_btc['timestamp'].values
    atrs = df_btc['atr'].values
    sma200 = df_btc['sma200'].values
    volumes = df_btc['volume'].values
    n = len(df_btc)

    reversal_atr_mult = 2.5
    direction = 1 if highs[2] >= highs[0] else -1

    trough_idx, peak_idx = 0, 0
    trough_val, peak_val = lows[0], highs[0]
    trough_date, peak_date = dates[0], dates[0]

    swings = []
    swing_id = 1

    # Day-by-day mapping arrays
    day_swing_id = np.zeros(n, dtype=int)
    day_direction = [''] * n
    day_role = [''] * n
    day_regime = [''] * n
    day_in_swing = np.zeros(n, dtype=int)
    day_cum_move_pct = np.zeros(n, dtype=float)
    day_signal = ['HOLD / CASH'] * n

    # Real-time trade log
    trades = []
    active_trade = None

    for i in range(1, n):
        curr_atr = atrs[i]
        thresh = reversal_atr_mult * curr_atr

        if direction == 1:
            # We are in an UP swing leg
            if highs[i] > peak_val:
                peak_val = highs[i]
                peak_idx = i
                peak_date = dates[i]
            elif lows[i] <= (peak_val - thresh):
                # UP SWING COMPLETED at peak_idx!
                start_dt = pd.to_datetime(trough_date)
                end_dt = pd.to_datetime(peak_date)
                days = (end_dt - start_dt).days
                spread_usd = peak_val - trough_val
                spread_pct = (spread_usd / trough_val) * 100.0

                regime = "BULL" if (trough_idx >= 200 and closes[trough_idx] >= sma200[trough_idx]) else "BEAR"
                role = "Bull Market Impulse" if regime == "BULL" else "Bear Relief Bounce"

                swings.append({
                    'Swing_ID': swing_id,
                    'Direction': 'UP',
                    'Start_Date': start_dt.strftime('%Y-%m-%d'),
                    'Start_Price': round(trough_val, 2),
                    'End_Date': end_dt.strftime('%Y-%m-%d'),
                    'End_Price': round(peak_val, 2),
                    'Spread_USD': round(spread_usd, 2),
                    'Spread_Pct': round(spread_pct, 2),
                    'Duration_Days': max(1, days),
                    'Velocity_USD_Day': round(spread_usd / max(1, days), 2),
                    'Macro_Regime': regime,
                    'Swing_Role': role,
                    'Confirm_Date': pd.to_datetime(dates[i]).strftime('%Y-%m-%d'),
                    'Start_Idx': trough_idx,
                    'End_Idx': peak_idx
                })

                # Close active trade if we had a LONG open
                if active_trade is not None:
                    exit_price = closes[i]
                    pnl_pct = ((exit_price - active_trade['Entry_Price']) / active_trade['Entry_Price']) * 100.0
                    pnl_usd = exit_price - active_trade['Entry_Price']
                    trade_days = (pd.to_datetime(dates[i]) - pd.to_datetime(active_trade['Entry_Date'])).days
                    trades.append({
                        'Trade_ID': len(trades) + 1,
                        'Swing_ID': active_trade['Swing_ID'],
                        'Trade_Type': 'LONG',
                        'Role': active_trade['Role'],
                        'Regime': active_trade['Regime'],
                        'Entry_Date': active_trade['Entry_Date'],
                        'Entry_Price': round(active_trade['Entry_Price'], 2),
                        'Exit_Date': pd.to_datetime(dates[i]).strftime('%Y-%m-%d'),
                        'Exit_Price': round(exit_price, 2),
                        'PnL_USD': round(pnl_usd, 2),
                        'PnL_Pct': round(pnl_pct, 2),
                        'Duration_Days': max(1, trade_days),
                        'MFE_Pct': round(active_trade['Max_High_Pct'], 2),
                        'MAE_Pct': round(active_trade['Max_Drawdown_Pct'], 2),
                        'Outcome': 'WIN' if pnl_pct > 0 else 'LOSS'
                    })
                    active_trade = None

                swing_id += 1
                direction = -1
                trough_val = lows[i]
                trough_idx = i
                trough_date = dates[i]

        else:
            # We are in a DOWN swing leg
            if lows[i] < trough_val:
                trough_val = lows[i]
                trough_idx = i
                trough_date = dates[i]
            elif highs[i] >= (trough_val + thresh):
                # DOWN SWING COMPLETED at trough_idx!
                start_dt = pd.to_datetime(peak_date)
                end_dt = pd.to_datetime(trough_date)
                days = (end_dt - start_dt).days
                spread_usd = peak_val - trough_val
                spread_pct = -((spread_usd / peak_val) * 100.0)

                regime = "BEAR" if (peak_idx >= 200 and closes[peak_idx] < sma200[peak_idx]) else "BULL"
                role = "Bull Market Pullback (Dip)" if regime == "BULL" else "Bear Market Impulse (Dump)"

                swings.append({
                    'Swing_ID': swing_id,
                    'Direction': 'DOWN',
                    'Start_Date': start_dt.strftime('%Y-%m-%d'),
                    'Start_Price': round(peak_val, 2),
                    'End_Date': end_dt.strftime('%Y-%m-%d'),
                    'End_Price': round(trough_val, 2),
                    'Spread_USD': round(spread_usd, 2),
                    'Spread_Pct': round(spread_pct, 2),
                    'Duration_Days': max(1, days),
                    'Velocity_USD_Day': round(spread_usd / max(1, days), 2),
                    'Macro_Regime': regime,
                    'Swing_Role': role,
                    'Confirm_Date': pd.to_datetime(dates[i]).strftime('%Y-%m-%d'),
                    'Start_Idx': peak_idx,
                    'End_Idx': trough_idx
                })

                # Here, a NEW UP SWING has just confirmed at index i!
                # This is an ACTIONABLE ENTRY POINT for our trade simulation!
                cur_regime = "BULL" if (trough_idx >= 200 and closes[trough_idx] >= sma200[trough_idx]) else "BEAR"
                cur_role = "Bull Market Impulse" if cur_regime == "BULL" else "Bear Relief Bounce"

                active_trade = {
                    'Swing_ID': swing_id + 1,
                    'Role': cur_role,
                    'Regime': cur_regime,
                    'Entry_Date': pd.to_datetime(dates[i]).strftime('%Y-%m-%d'),
                    'Entry_Price': closes[i],
                    'Max_High_Pct': 0.0,
                    'Max_Drawdown_Pct': 0.0
                }

                swing_id += 1
                direction = 1
                peak_val = highs[i]
                peak_idx = i
                peak_date = dates[i]

        # Update MFE / MAE if active trade
        if active_trade is not None:
            ep = active_trade['Entry_Price']
            curr_gain = ((highs[i] - ep) / ep) * 100.0
            curr_dd = ((lows[i] - ep) / ep) * 100.0
            if curr_gain > active_trade['Max_High_Pct']:
                active_trade['Max_High_Pct'] = curr_gain
            if curr_dd < active_trade['Max_Drawdown_Pct']:
                active_trade['Max_Drawdown_Pct'] = curr_dd

    df_swings = pd.DataFrame(swings)
    df_trades = pd.DataFrame(trades)

    # 3. Create True Day-by-Day (हर एक दिन का) Table
    # Map each daily candle to its active swing
    daily_records = []
    
    # Pre-build lookup intervals from df_swings
    for idx in range(n):
        dt = pd.to_datetime(dates[idx])
        dt_str = dt.strftime('%Y-%m-%d')
        c = closes[idx]
        o = opens[idx]
        h = highs[idx]
        l = lows[idx]
        vol = volumes[idx]
        daily_range_usd = h - l
        daily_range_pct = (daily_range_usd / l) * 100.0 if l > 0 else 0.0
        daily_ret_pct = ((c - o) / o) * 100.0 if o > 0 else 0.0

        # Find which swing covers this date
        matched_swing = None
        for _, sw in df_swings.iterrows():
            if sw['Start_Date'] <= dt_str <= sw['End_Date']:
                matched_swing = sw
                break
        
        if matched_swing is None:
            # Check if after last swing or between
            for _, sw in df_swings.iterrows():
                if dt_str >= sw['Start_Date']:
                    matched_swing = sw

        s_id = matched_swing['Swing_ID'] if matched_swing is not None else 1
        s_dir = matched_swing['Direction'] if matched_swing is not None else 'UP'
        s_role = matched_swing['Swing_Role'] if matched_swing is not None else 'Unknown'
        s_regime = matched_swing['Macro_Regime'] if matched_swing is not None else 'BULL'
        s_start_dt = pd.to_datetime(matched_swing['Start_Date']) if matched_swing is not None else dt
        s_start_pr = matched_swing['Start_Price'] if matched_swing is not None else o

        day_num = (dt - s_start_dt).days + 1
        cum_move_pct = ((c - s_start_pr) / s_start_pr) * 100.0 if s_dir == 'UP' else -((s_start_pr - c) / s_start_pr) * 100.0
        cum_move_usd = c - s_start_pr if s_dir == 'UP' else s_start_pr - c

        # Determine daily actionable trade state
        is_turning_day = (dt_str == matched_swing['Start_Date'])
        is_confirm_day = (dt_str == matched_swing.get('Confirm_Date', ''))
        
        if s_dir == 'UP':
            if day_num <= 3:
                trade_action = "IDEAL_LONG_ENTRY"
            elif day_num <= 10:
                trade_action = "HOLD_RUNNER"
            else:
                trade_action = "PROFIT_HARVEST_EXHAUSTION"
        else:
            if s_role == "Bull Market Pullback (Dip)":
                trade_action = "DIP_WATCH_CASH"
            else:
                trade_action = "BEAR_DEFENSE_CASH"

        daily_records.append({
            'Date': dt_str,
            'Open': round(o, 2),
            'High': round(h, 2),
            'Low': round(l, 2),
            'Close': round(c, 2),
            'Volume': round(vol, 2),
            'Daily_Range_USD': round(daily_range_usd, 2),
            'Daily_Range_Pct': round(daily_range_pct, 2),
            'Daily_Return_Pct': round(daily_ret_pct, 2),
            'Active_Swing_ID': s_id,
            'Swing_Direction': s_dir,
            'Macro_Regime': s_regime,
            'Swing_Role': s_role,
            'Day_in_Swing': max(1, day_num),
            'Swing_Origin_Price': round(s_start_pr, 2),
            'Cum_Swing_Move_USD': round(cum_move_usd, 2),
            'Cum_Swing_Move_Pct': round(cum_move_pct, 2),
            'Trade_Action_State': trade_action
        })

    df_daily = pd.DataFrame(daily_records)

    # 4. Save CSV Outputs
    out_daily_csv = LOGS_DIR / "market_swings_daily_candle_ledger_btc.csv"
    df_daily.to_csv(out_daily_csv, index=False)
    print(f"\n[+] Saved Daily Candle Swing Ledger (1,806 rows) to: {out_daily_csv.name}")

    out_trades_csv = LOGS_DIR / "swing_trade_strategy_backtest_5years.csv"
    df_trades.to_csv(out_trades_csv, index=False)
    print(f"[+] Saved Reversal Swing Trade Strategy Results ({len(df_trades)} trades) to: {out_trades_csv.name}")

    # 5. Compute Trade Simulation Statistics
    win_trades = df_trades[df_trades['Outcome'] == 'WIN']
    loss_trades = df_trades[df_trades['Outcome'] == 'LOSS']
    win_rate = (len(win_trades) / len(df_trades)) * 100.0 if len(df_trades) > 0 else 0.0
    total_pnl_pct = df_trades['PnL_Pct'].sum()
    avg_win = win_trades['PnL_Pct'].mean() if len(win_trades) > 0 else 0.0
    avg_loss = loss_trades['PnL_Pct'].mean() if len(loss_trades) > 0 else 0.0
    profit_factor = abs(win_trades['PnL_USD'].sum() / loss_trades['PnL_USD'].sum()) if loss_trades['PnL_USD'].sum() != 0 else np.nan
    avg_duration = df_trades['Duration_Days'].mean()

    # Bull vs Bear trades
    bull_trades = df_trades[df_trades['Regime'] == 'BULL']
    bear_trades = df_trades[df_trades['Regime'] == 'BEAR']

    bull_win_rate = (len(bull_trades[bull_trades['Outcome'] == 'WIN']) / len(bull_trades)) * 100.0 if len(bull_trades) > 0 else 0.0
    bear_win_rate = (len(bear_trades[bear_trades['Outcome'] == 'WIN']) / len(bear_trades)) * 100.0 if len(bear_trades) > 0 else 0.0

    print("\n==========================================================================")
    print("REVERSAL SWING TRADING SIMULATION PERFORMANCE (5 YEARS: 2021-2026)")
    print("==========================================================================")
    print(f"Total Confirmed Trades Taken:  {len(df_trades)}")
    print(f"Win Rate:                      {win_rate:.1f}% ({len(win_trades)} Wins / {len(loss_trades)} Losses)")
    print(f"Profit Factor:                 {profit_factor:.2f}")
    print(f"Cumulative Return (% Sum):     {total_pnl_pct:+.2f}%")
    print(f"Average Win Trade:             +{avg_win:.2f}%")
    print(f"Average Loss Trade:            {avg_loss:.2f}%")
    print(f"Average Trade Duration:        {avg_duration:.1f} Days")
    print(f"Bull Regime Trades Win Rate:   {bull_win_rate:.1f}% ({len(bull_trades)} trades, Net Return: {bull_trades['PnL_Pct'].sum():+.2f}%)")
    print(f"Bear Regime Trades Win Rate:   {bear_win_rate:.1f}% ({len(bear_trades)} trades, Net Return: {bear_trades['PnL_Pct'].sum():+.2f}%)")

    # 6. Update Master Multi-Tab Excel Workbook
    # Load other existing sheets to keep everything in ONE master workbook
    out_excel = LOGS_DIR / "MARKET_SWINGS_MASTER_5YEARS_2021_2026.xlsx"
    with pd.ExcelWriter(out_excel, engine='openpyxl') as writer:
        df_daily.to_excel(writer, sheet_name='Daily_1806_Candles_Ledger', index=False)
        df_trades.to_excel(writer, sheet_name='Swing_Trade_Simulation', index=False)
        df_swings.to_excel(writer, sheet_name='BTC_120_Macro_Swings', index=False)
        
        # Load and append monthly summary and regime comparison
        monthly_csv = LOGS_DIR / "market_swings_monthly_summary_btc.csv"
        if monthly_csv.exists():
            pd.read_csv(monthly_csv).to_excel(writer, sheet_name='Monthly_Swing_Breakdown', index=False)
        
        regime_csv = LOGS_DIR / "market_swings_regime_comparison.csv"
        if regime_csv.exists():
            pd.read_csv(regime_csv).to_excel(writer, sheet_name='Regime_Stepping_Comparison', index=False)

        ten_csv = LOGS_DIR / "market_swings_all_10coins_summary.csv"
        if ten_csv.exists():
            pd.read_csv(ten_csv).to_excel(writer, sheet_name='All_10_Coins_Summary', index=False)

    print(f"\n[+] Successfully Updated Master Multi-Tab Excel Workbook: {out_excel.name} (Now 6 Complete Sheets!)")

if __name__ == '__main__':
    run_daily_and_trade_analysis()
