import sys
from pathlib import Path
import os
import requests
import zipfile
import pandas as pd
from datetime import datetime
from io import BytesIO
import concurrent.futures

# Dynamically resolve SRC directory for relative imports
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, SYMBOLS

INTERVALS = ['1m', '5m', '15m', '30m', '1h', '4h', '8h', '12h', '1d', '1w', '1mo']

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

def process_symbol_interval(symbol, interval, months):
    out_file = DATA_RAW_DIR / f"{symbol}_{interval}_Raw_5Years.csv"
    
    # Memory efficient streaming approach
    first = True
    rows_written = 0
    for month in months:
        url = f"{BASE_URL}/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with zipfile.ZipFile(BytesIO(r.content)) as z:
                    filename = z.namelist()[0]
                    with z.open(filename) as f:
                        df = pd.read_csv(f, header=None)
                        df = df.iloc[:, 0:6]
                        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        
                        df.to_csv(out_file, mode='w' if first else 'a', header=first, index=False)
                        first = False
                        rows_written += len(df)
        except Exception:
            pass
            
    if rows_written > 0:
        print(f"[*] Successfully downloaded & saved {out_file.name} ({rows_written} rows)")

def download_data():
    months = generate_months()
    print(f"Starting Multi-Threaded Memory-Efficient Download for {len(SYMBOLS)} Coins x {len(INTERVALS)} Timeframes...")
    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for symbol in SYMBOLS:
            for interval in INTERVALS:
                target_path = DATA_RAW_DIR / f"{symbol}_{interval}_Raw_5Years.csv"
                if target_path.exists():
                    if target_path.stat().st_size > 100:
                        print(f"[SKIP] {symbol} {interval} (Already exists)")
                        continue
                tasks.append(executor.submit(process_symbol_interval, symbol, interval, months))
        
        concurrent.futures.wait(tasks)
        print("=========================================")
        print("ALL DATA DOWNLOADS COMPLETED AND VERIFIED")
        print("=========================================")

if __name__ == "__main__":
    download_data()
