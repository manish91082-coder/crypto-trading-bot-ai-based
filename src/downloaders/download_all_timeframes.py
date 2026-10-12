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

def process_symbol_interval(symbol: str, interval: str, months: list, force: bool = False):
    out_file = DATA_RAW_DIR / f"{symbol}_{interval}_Raw_5Years.csv"
    if out_file.exists() and not force and out_file.stat().st_size > 100:
        print(f"[SKIP] {symbol} {interval} (Already exists, force=False)")
        return
    
    first = True
    rows_written = 0
    missing_months = []
    
    for month in months:
        url = f"{BASE_URL}/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"
        downloaded = False
        
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=20)
                if r.status_code == 200:
                    with zipfile.ZipFile(BytesIO(r.content)) as z:
                        filename = z.namelist()[0]
                        with z.open(filename) as f:
                            df = pd.read_csv(f, header=None)
                            df = df.iloc[:, 0:6]
                            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                            
                            # CRITICAL FIX: Auto-detect microseconds vs milliseconds
                            first_val = float(df['timestamp'].iloc[0])
                            if first_val > 1e14:  # 16 digits -> microseconds
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='us')
                            else:  # 13 digits -> milliseconds
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            
                            # Drop any corrupted future dates
                            df = df[df['timestamp'] < '2030-01-01']
                            
                            df.to_csv(out_file, mode='w' if first else 'a', header=first, index=False)
                            first = False
                            rows_written += len(df)
                            downloaded = True
                            break
                elif r.status_code == 404:
                    # File not yet published on Binance Vision
                    break
            except Exception as e:
                time.sleep(1)
                
        if not downloaded and r.status_code != 404:
            missing_months.append(month)
            
    if missing_months:
        print(f"[WARN] {symbol} {interval}: Failed to download months {missing_months}")
    elif rows_written > 0:
        print(f"[*] Successfully downloaded & verified {out_file.name} ({rows_written} clean rows)")

def download_data(intervals_to_run=None, force: bool = False):
    months = generate_months()
    target_intervals = intervals_to_run or INTERVALS
    print(f"Starting Multi-Threaded Download for {len(SYMBOLS)} Coins x {len(target_intervals)} Intervals...")
    print(f"Date Range: {months[0]} to {months[-1]} | Force Overwrite: {force}")
    
    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for symbol in SYMBOLS:
            for interval in target_intervals:
                tasks.append(executor.submit(process_symbol_interval, symbol, interval, months, force))
        
        concurrent.futures.wait(tasks)
        print("=========================================")
        print("DATA DOWNLOAD PROCESS COMPLETED")
        print("=========================================")

if __name__ == "__main__":
    import argparse
    import time
    parser = argparse.ArgumentParser(description="Binance Vision Clean Data Downloader")
    parser.add_argument('--interval', type=str, default='1d', help="Interval to download (default: 1d)")
    parser.add_argument('--force', action='store_true', help="Force re-download and overwrite existing files")
    args = parser.parse_args()
    
    selected_intervals = [args.interval] if args.interval else INTERVALS
    download_data(intervals_to_run=selected_intervals, force=args.force)

