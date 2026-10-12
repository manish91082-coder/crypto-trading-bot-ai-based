import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, LOGS_DIR, SYMBOLS
from analytics.market_swing_4h_analyzer import (
    detect_4h_market_swings,
    build_candle_ledger_4h,
    build_monthly_4h_summary,
    run_cross_asset_4h_analysis,
    compute_spread_distribution_buckets,
    compute_strategy_vs_market_gap
)

def run():
    print("[*] Generating all 4H natural swing files & Master Excel...")
    df_btc = pd.read_csv(DATA_RAW_DIR / "BTCUSDT_4h_Raw_5Years.csv")
    df_btc['ema50'] = df_btc['close'].ewm(span=50, adjust=False).mean()

    # Swings & Daily Frequency
    btc_swings = detect_4h_market_swings(df_btc, symbol='BTCUSDT', reversal_atr_mult=2.0, btc_ema50=df_btc['ema50'])
    btc_swings.to_csv(LOGS_DIR / "market_swings_4h_btc_ledger.csv", index=False)
    print("  -> Saved market_swings_4h_btc_ledger.csv")

    daily_csv = LOGS_DIR / "market_swings_4h_daily_frequency.csv"
    btc_daily = pd.read_csv(daily_csv)
    print("  -> Loaded market_swings_4h_daily_frequency.csv")

    # Candle ledger
    btc_candle = build_candle_ledger_4h(btc_swings, df_btc)
    btc_candle.to_csv(LOGS_DIR / "market_swings_4h_candle_ledger_btc.csv", index=False)
    print("  -> Saved market_swings_4h_candle_ledger_btc.csv")

    # Monthly summary
    btc_monthly = build_monthly_4h_summary(btc_swings, btc_daily)
    btc_monthly.to_csv(LOGS_DIR / "market_swings_4h_monthly_summary.csv", index=False)
    print("  -> Saved market_swings_4h_monthly_summary.csv")

    # 10 Coins Analysis
    ten_coin, all_swings_dict = run_cross_asset_4h_analysis(df_btc['ema50'])
    ten_coin.to_csv(LOGS_DIR / "market_swings_4h_all_10coins_summary.csv", index=False)
    print("  -> Saved market_swings_4h_all_10coins_summary.csv")

    # Buckets & Strategy Gap
    buckets = compute_spread_distribution_buckets(all_swings_dict)
    gap = compute_strategy_vs_market_gap(all_swings_dict)

    # Multi-tab Excel
    out_excel = LOGS_DIR / "MARKET_SWINGS_4H_MASTER_5YEARS_2021_2026.xlsx"
    with pd.ExcelWriter(out_excel, engine='openpyxl') as writer:
        btc_swings.to_excel(writer, sheet_name='BTC_4H_Swings_Ledger', index=False)
        btc_daily.to_excel(writer, sheet_name='Per_Day_Frequency_Analysis', index=False)
        btc_monthly.to_excel(writer, sheet_name='Monthly_4H_Summary', index=False)
        ten_coin.to_excel(writer, sheet_name='All_10_Coins_4H_Summary', index=False)
        buckets.to_excel(writer, sheet_name='Spread_Distribution_Buckets', index=False)
        gap.to_excel(writer, sheet_name='Strategy_vs_Market_Gap', index=False)
    print(f"  -> Saved Master Excel Workbook ({out_excel.name}) successfully!")

if __name__ == '__main__':
    run()
