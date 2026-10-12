import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, LOGS_DIR, SYMBOLS, MACRO_BTC_EMA_PERIOD

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Wilder's True Range and 14-period rolling ATR."""
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean().bfill()

def detect_market_swings(
    df: pd.DataFrame,
    symbol: str = 'BTCUSDT',
    reversal_atr_mult: float = 2.5,
    btc_sma200: pd.Series = None
) -> pd.DataFrame:
    """
    Mathematical Dynamic ATR Reversal Swing Decomposition Engine.
    Identifies exact Turning Points (Pivots), Up-Swing Legs, Down-Swing Legs,
    Spreads, Durations, and Macro Stepping Behaviors.
    """
    df = df.copy()
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)

    if 'atr' not in df.columns:
        df['atr'] = compute_atr(df, 14)

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    dates = df['timestamp'].values
    atrs = df['atr'].values
    volumes = df['volume'].values
    n = len(df)

    is_up = highs[2] >= highs[0]
    direction = 1 if is_up else -1

    trough_idx, peak_idx = 0, 0
    trough_val, peak_val = lows[0], highs[0]
    trough_date, peak_date = dates[0], dates[0]

    swings = []
    swing_id = 1

    for i in range(1, n):
        curr_atr = atrs[i]
        thresh = reversal_atr_mult * curr_atr

        if direction == 1:
            # UP-SWING (Bullish Leg)
            if highs[i] > peak_val:
                peak_val = highs[i]
                peak_idx = i
                peak_date = dates[i]
            elif lows[i] <= (peak_val - thresh):
                # Turning Point Confirmed
                start_dt = pd.to_datetime(trough_date)
                end_dt = pd.to_datetime(peak_date)
                days = (end_dt - start_dt).days
                spread_usd = peak_val - trough_val
                spread_pct = (spread_usd / trough_val) * 100.0

                # Macro regime based on SMA 200 at start of swing
                regime = "BULL"
                if btc_sma200 is not None and trough_idx < len(btc_sma200) and not pd.isna(btc_sma200.iloc[trough_idx]):
                    regime = "BULL" if closes[trough_idx] >= btc_sma200.iloc[trough_idx] else "BEAR"

                vol_leg = volumes[trough_idx:peak_idx + 1].sum() if peak_idx >= trough_idx else volumes[trough_idx]

                role = "Bull Market Impulse" if regime == "BULL" else "Bear Relief Bounce"

                swings.append({
                    'Swing_ID': swing_id,
                    'Symbol': symbol,
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
                    'Volume_Total': round(vol_leg, 2),
                    'Start_Month': start_dt.strftime('%Y-%m'),
                    'End_Month': end_dt.strftime('%Y-%m')
                })
                swing_id += 1

                direction = -1
                trough_val = lows[i]
                trough_idx = i
                trough_date = dates[i]

        else:
            # DOWN-SWING (Bearish Leg)
            if lows[i] < trough_val:
                trough_val = lows[i]
                trough_idx = i
                trough_date = dates[i]
            elif highs[i] >= (trough_val + thresh):
                # Turning Point Confirmed
                start_dt = pd.to_datetime(peak_date)
                end_dt = pd.to_datetime(trough_date)
                days = (end_dt - start_dt).days
                spread_usd = peak_val - trough_val
                spread_pct = -((spread_usd / peak_val) * 100.0)

                regime = "BEAR"
                if btc_sma200 is not None and peak_idx < len(btc_sma200) and not pd.isna(btc_sma200.iloc[peak_idx]):
                    regime = "BULL" if closes[peak_idx] >= btc_sma200.iloc[peak_idx] else "BEAR"

                vol_leg = volumes[peak_idx:trough_idx + 1].sum() if trough_idx >= peak_idx else volumes[peak_idx]

                role = "Bull Market Pullback (Dip)" if regime == "BULL" else "Bear Market Impulse (Dump)"

                swings.append({
                    'Swing_ID': swing_id,
                    'Symbol': symbol,
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
                    'Volume_Total': round(vol_leg, 2),
                    'Start_Month': start_dt.strftime('%Y-%m'),
                    'End_Month': end_dt.strftime('%Y-%m')
                })
                swing_id += 1

                direction = 1
                peak_val = highs[i]
                peak_idx = i
                peak_date = dates[i]

    return pd.DataFrame(swings)

def build_monthly_swing_summary(df_swings: pd.DataFrame, df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Computes rigorous month-by-month swing statistics:
    - Number of Up Swings, Down Swings, Total Swings
    - Average Up Spread (%), Average Down Spread (%)
    - Maximum Up Swing (%), Maximum Down Swing (%)
    - Month Opening Price, Closing Price, Net Price Change (%)
    - Stepping Activity Index (Total Swings per Month)
    """
    df_raw = df_raw.copy()
    df_raw['month'] = pd.to_datetime(df_raw['timestamp']).dt.strftime('%Y-%m')
    all_months = sorted(df_raw['month'].unique())

    monthly_stats = []

    for m in all_months:
        m_raw = df_raw[df_raw['month'] == m]
        m_open = m_raw['open'].iloc[0]
        m_close = m_raw['close'].iloc[-1]
        m_ret_pct = ((m_close - m_open) / m_open) * 100.0
        m_high = m_raw['high'].max()
        m_low = m_raw['low'].min()
        m_range_pct = ((m_high - m_low) / m_low) * 100.0

        # Find swings starting in this month
        m_swings = df_swings[df_swings['Start_Month'] == m]
        up_swings = m_swings[m_swings['Direction'] == 'UP']
        down_swings = m_swings[m_swings['Direction'] == 'DOWN']

        n_up = len(up_swings)
        n_down = len(down_swings)
        n_total = len(m_swings)

        avg_up_spread = up_swings['Spread_Pct'].mean() if n_up > 0 else 0.0
        max_up_spread = up_swings['Spread_Pct'].max() if n_up > 0 else 0.0
        avg_down_spread = down_swings['Spread_Pct'].mean() if n_down > 0 else 0.0
        max_down_spread = down_swings['Spread_Pct'].min() if n_down > 0 else 0.0

        avg_duration = m_swings['Duration_Days'].mean() if n_total > 0 else 0.0

        period_tag = "Research" if m <= "2024-12" else "Vault Holdout"

        monthly_stats.append({
            'Month': m,
            'Period': period_tag,
            'Total_Swings': n_total,
            'Up_Swings': n_up,
            'Down_Swings': n_down,
            'Avg_Up_Spread_Pct': round(avg_up_spread, 2),
            'Max_Up_Spread_Pct': round(max_up_spread, 2),
            'Avg_Down_Spread_Pct': round(avg_down_spread, 2),
            'Max_Down_Spread_Pct': round(max_down_spread, 2),
            'Avg_Duration_Days': round(avg_duration, 1),
            'Month_Open_USD': round(m_open, 2),
            'Month_Close_USD': round(m_close, 2),
            'Net_Monthly_Return_Pct': round(m_ret_pct, 2),
            'Monthly_Range_Pct': round(m_range_pct, 2)
        })

    return pd.DataFrame(monthly_stats)

def build_regime_comparison(df_swings: pd.DataFrame) -> pd.DataFrame:
    """
    Deconstructs Bull Market vs Bear Market Stepping Mechanics:
    - Bullish Impulses vs Bullish Pullbacks
    - Bearish Impulses vs Bearish Relief Bounces
    """
    groups = df_swings.groupby('Swing_Role')
    summary_rows = []

    for role, group in groups:
        summary_rows.append({
            'Swing_Role': role,
            'Count': len(group),
            'Avg_Spread_USD': round(group['Spread_USD'].mean(), 2),
            'Avg_Spread_Pct': round(group['Spread_Pct'].abs().mean(), 2),
            'Max_Spread_Pct': round(group['Spread_Pct'].abs().max(), 2),
            'Avg_Duration_Days': round(group['Duration_Days'].mean(), 1),
            'Avg_Velocity_USD_Day': round(group['Velocity_USD_Day'].mean(), 2)
        })

    return pd.DataFrame(summary_rows)

def run_cross_asset_analysis(btc_sma200: pd.Series):
    """Computes swing structure across all 10 universal crypto assets."""
    records = []
    for sym in SYMBOLS:
        raw_p = DATA_RAW_DIR / f"{sym}_1d_Raw_5Years.csv"
        df = pd.read_csv(raw_p)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        df.reset_index(drop=True, inplace=True)

        swings = detect_market_swings(df, symbol=sym, reversal_atr_mult=2.5, btc_sma200=btc_sma200)
        up_s = swings[swings['Direction'] == 'UP']
        down_s = swings[swings['Direction'] == 'DOWN']

        records.append({
            'Symbol': sym,
            'Total_Swings': len(swings),
            'Up_Swings': len(up_s),
            'Down_Swings': len(down_s),
            'Avg_Up_Spread_Pct': round(up_s['Spread_Pct'].mean(), 2),
            'Avg_Down_Spread_Pct': round(down_s['Spread_Pct'].abs().mean(), 2),
            'Avg_Swing_Duration_Days': round(swings['Duration_Days'].mean(), 1),
            'Max_Single_Up_Swing_Pct': round(up_s['Spread_Pct'].max(), 2),
            'Max_Single_Down_Swing_Pct': round(down_s['Spread_Pct'].abs().max(), 2),
            'Starting_Price': round(df['open'].iloc[0], 4),
            'Ending_Price': round(df['close'].iloc[-1], 4),
            'Total_5Yr_Price_Change_Pct': round(((df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0]) * 100.0, 2)
        })
    return pd.DataFrame(records)

def main():
    print("==========================================================================")
    print("INSTITUTIONAL QUANTITATIVE MARKET SWING & TURNING POINT RESEARCH (2021-2026)")
    print("Data-Driven Stepping Structure Analysis across 5 Full Years (1,826 Daily Candles)")
    print("==========================================================================")

    # 1. Load Bitcoin 5-Year Data & Precompute Macro 20-period EMA
    btc_file = DATA_RAW_DIR / "BTCUSDT_1d_Raw_5Years.csv"
    df_btc = pd.read_csv(btc_file)
    df_btc['timestamp'] = pd.to_datetime(df_btc['timestamp'])
    df_btc.sort_values('timestamp', inplace=True)
    df_btc.reset_index(drop=True, inplace=True)

    df_btc['atr'] = compute_atr(df_btc, 14)
    df_btc['ema20'] = df_btc['close'].ewm(span=MACRO_BTC_EMA_PERIOD, adjust=False).mean()
    df_btc['sma200'] = df_btc['close'].rolling(200).mean()

    # 2. Extract Complete Bitcoin Daily Swings (2.5x ATR Reversal Threshold)
    btc_swings = detect_market_swings(
        df_btc, symbol='BTCUSDT', reversal_atr_mult=2.5, btc_sma200=df_btc['sma200']
    )
    print(f"\n[*] Total Bitcoin Swings Detected (2021-10 to 2026-09): {len(btc_swings)} Swings")
    up_swings = btc_swings[btc_swings['Direction'] == 'UP']
    down_swings = btc_swings[btc_swings['Direction'] == 'DOWN']
    print(f"    - Bullish Up-Swings (Rallies / Bounces):  {len(up_swings)} (Avg Spread: +{up_swings['Spread_Pct'].mean():.2f}%, Avg Days: {up_swings['Duration_Days'].mean():.1f}d)")
    print(f"    - Bearish Down-Swings (Pullbacks / Drops): {len(down_swings)} (Avg Spread: -{down_swings['Spread_Pct'].abs().mean():.2f}%, Avg Days: {down_swings['Duration_Days'].mean():.1f}d)")

    # 3. Monthly Aggregated Stepping Summary
    btc_monthly = build_monthly_swing_summary(btc_swings, df_btc)

    # 4. Regime Stepping Comparison (Bull Market vs Bear Market)
    regime_comp = build_regime_comparison(btc_swings)

    # 5. Cross-Asset 10-Coin Swings Summary
    ten_coin_summary = run_cross_asset_analysis(df_btc['sma200'])

    # 6. Save CSV Files
    out_swings = LOGS_DIR / "market_swings_5years_btc.csv"
    btc_swings.to_csv(out_swings, index=False)
    print(f"\n[+] Saved Complete BTC Swing Ledger to: {out_swings.name}")

    out_monthly = LOGS_DIR / "market_swings_monthly_summary_btc.csv"
    btc_monthly.to_csv(out_monthly, index=False)
    print(f"[+] Saved BTC Monthly Swing Summary to: {out_monthly.name}")

    out_regime = LOGS_DIR / "market_swings_regime_comparison.csv"
    regime_comp.to_csv(out_regime, index=False)
    print(f"[+] Saved Regime Stepping Comparison to: {out_regime.name}")

    out_ten = LOGS_DIR / "market_swings_all_10coins_summary.csv"
    ten_coin_summary.to_csv(out_ten, index=False)
    print(f"[+] Saved 10-Coin Cross-Asset Summary to: {out_ten.name}")

    # 7. Save Master Multi-Tab Excel Workbook
    out_excel = LOGS_DIR / "MARKET_SWINGS_MASTER_5YEARS_2021_2026.xlsx"
    with pd.ExcelWriter(out_excel, engine='openpyxl') as writer:
        btc_swings.to_excel(writer, sheet_name='BTC_Daily_Swings_Ledger', index=False)
        btc_monthly.to_excel(writer, sheet_name='BTC_Monthly_Summary', index=False)
        regime_comp.to_excel(writer, sheet_name='Regime_Stepping_Mechanics', index=False)
        ten_coin_summary.to_excel(writer, sheet_name='10_Coins_Comparison', index=False)
    print(f"[+] Saved Master Multi-Tab Excel Workbook to: {out_excel.name}")

    # Print Key Insights
    print("\n==========================================================================")
    print("TOP 10 LARGEST BITCOIN SWINGS IN 5 YEARS (TURNING POINT TO TURNING POINT)")
    print("==========================================================================")
    top_swings = btc_swings.sort_values('Spread_USD', ascending=False).head(10)
    for _, s in top_swings.iterrows():
        sign = "+" if s['Direction'] == 'UP' else "-"
        print(f"  Swing #{s['Swing_ID']:>2} [{s['Direction']:>4}] {s['Start_Date']} (${s['Start_Price']:>9.2f}) -> {s['End_Date']} (${s['End_Price']:>9.2f}) | {sign}${s['Spread_USD']:>9.2f} ({s['Spread_Pct']:>+6.2f}%) | {s['Duration_Days']:>2} Days | {s['Swing_Role']}")

    print("\n==========================================================================")
    print("BULL MARKET VS BEAR MARKET STEPPING MECHANICS (MATHEMATICAL PROOF)")
    print("==========================================================================")
    for _, r in regime_comp.iterrows():
        print(f"  {r['Swing_Role']:<25} | Count: {r['Count']:>2} | Avg Spread: {r['Avg_Spread_Pct']:>5.2f}% (${r['Avg_Spread_USD']:>8.2f}) | Avg Days: {r['Avg_Duration_Days']:>4.1f}d | Max: {r['Max_Spread_Pct']:>6.2f}%")

if __name__ == '__main__':
    main()
