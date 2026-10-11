import os
import requests
import zipfile
import pandas as pd
from datetime import datetime
from io import BytesIO

SYMBOLS = ['BTCUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT']
# Note: ETHUSDT is skipped as we already have its 5-year data
INTERVALS = ['15m', '4h']

# Last 5 Years (Oct 2021 to Sep 2026)
START_YEAR = 2021
START_MONTH = 10
END_YEAR = 2026
END_MONTH = 9

BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"

def generate_months():
    months = []
    y, m = START_YEAR, START_MONTH
    while y < END_YEAR or (y == END_YEAR and m <= END_MONTH):
        months.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months

def download_data():
    months = generate_months()
    print(f"Total months to download per coin: {len(months)}")
    
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            print(f"Processing {symbol} - {interval}...")
            dfs = []
            for month in months:
                url = f"{BASE_URL}/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"
                try:
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200:
                        with zipfile.ZipFile(BytesIO(r.content)) as z:
                            filename = z.namelist()[0]
                            with z.open(filename) as f:
                                df = pd.read_csv(f, header=None)
                                dfs.append(df)
                    else:
                        print(f"  [!] Missing data for {symbol} {interval} {month}")
                except Exception as e:
                    print(f"  [X] Error downloading {url}: {e}")
            
            if dfs:
                final_df = pd.concat(dfs, ignore_index=True)
                final_df = final_df.iloc[:, 0:6]
                final_df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                final_df['timestamp'] = pd.to_datetime(final_df['timestamp'], unit='ms')
                final_df.to_csv(f"{symbol}_{interval}_Raw_5Years.csv", index=False)
                print(f"[*] Successfully saved {symbol}_{interval}_Raw_5Years.csv ({len(final_df)} rows).")

if __name__ == "__main__":
    download_data()
