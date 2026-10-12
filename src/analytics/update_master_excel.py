import pandas as pd
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = SRC_DIR.parent / "logs"

out_excel = LOGS_DIR / "MARKET_SWINGS_MASTER_5YEARS_2021_2026.xlsx"
df_tr = pd.read_csv(LOGS_DIR / "full_5year_spot_trades.csv")
df_mo = pd.read_csv(LOGS_DIR / "full_5year_spot_monthly_performance.csv")

with pd.ExcelWriter(out_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    df_tr.to_excel(writer, sheet_name='Production_Spot_Trades_5Y', index=False)
    df_mo.to_excel(writer, sheet_name='Production_Monthly_Audit_5Y', index=False)

print(f"Successfully updated Excel workbook: {out_excel.name} with Production Backtest sheets!")
