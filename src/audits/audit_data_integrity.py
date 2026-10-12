import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, SYMBOLS

def certify_1d_data_integrity() -> bool:
    print("=================================================================")
    print("ZERO-TRUST PRE-FLIGHT AUDIT: 1D DATA INTEGRITY & BOUNDARY PROOF")
    print("=================================================================")
    
    all_passed = True
    summary_report = []

    for symbol in SYMBOLS:
        csv_file = DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv"
        print(f"\nChecking {symbol} ({csv_file.name})...")
        
        if not csv_file.exists():
            print(f"  [FAIL] File does not exist: {csv_file}")
            all_passed = False
            continue
            
        df = pd.read_csv(csv_file)
        
        # 1. Total Rows
        total_rows = len(df)
        print(f"  Total Rows: {total_rows}")
        
        # 2. Timestamp Parsing & Year 56971 Bug Check
        dt_series = pd.to_datetime(df['timestamp'], errors='coerce')
        invalid_ts_count = dt_series.isna().sum()
        future_corrupt_count = (dt_series > '2030-01-01').sum()
        
        print(f"  Unparseable Timestamps: {invalid_ts_count}")
        print(f"  Corrupted Future Timestamps (>2030): {future_corrupt_count}")
        
        if invalid_ts_count > 0 or future_corrupt_count > 0:
            print(f"  -> [FAIL] Timestamps corrupted by microsecond bug!")
            all_passed = False
            continue
            
        # 3. Date Boundaries
        min_date = dt_series.min()
        max_date = dt_series.max()
        print(f"  Start Date: {min_date.strftime('%Y-%m-%d')}")
        print(f"  End Date:   {max_date.strftime('%Y-%m-%d')}")
        
        # We expect data to reach into 2026
        if max_date < pd.to_datetime('2026-08-01'):
            print(f"  -> [FAIL] End date cut off prematurely! (Expected >= 2026-08, got {max_date.strftime('%Y-%m-%d')})")
            all_passed = False
            
        # 4. Continuity & Gap Check
        df['dt'] = dt_series
        df = df.sort_values('dt').reset_index(drop=True)
        diffs = df['dt'].diff()
        large_gaps = df[diffs > pd.Timedelta(days=1)]
        
        if len(large_gaps) > 0:
            print(f"  -> [FAIL] Found {len(large_gaps)} calendar gaps > 1 day:")
            for _, g in large_gaps.head(5).iterrows():
                print(f"       Gap before: {g['dt'].strftime('%Y-%m-%d')}")
            all_passed = False
        else:
            print(f"  Calendar Continuity: 100% PERFECT (0 gaps)")
            
        # 5. Price Sanity & NaNs
        nan_counts = df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum()
        price_sanity_errors = ((df['high'] < df['open']) | (df['high'] < df['close']) | (df['low'] > df['open']) | (df['low'] > df['close'])).sum()
        
        print(f"  NaN Count: {nan_counts}")
        print(f"  Price Geometry Errors: {price_sanity_errors}")
        
        if nan_counts > 0 or price_sanity_errors > 0:
            print(f"  -> [FAIL] Price data contains NaNs or geometry violations!")
            all_passed = False
            
        is_clean = (invalid_ts_count == 0 and future_corrupt_count == 0 and max_date >= pd.to_datetime('2026-08-01') and len(large_gaps) == 0 and nan_counts == 0)
        status_str = "CERTIFIED PASS" if is_clean else "FAILED"
        print(f"  Status: [{status_str}]")
        
        summary_report.append({
            'symbol': symbol,
            'rows': total_rows,
            'start': min_date.strftime('%Y-%m-%d'),
            'end': max_date.strftime('%Y-%m-%d'),
            'gaps': len(large_gaps),
            'status': status_str
        })
        
    print("\n=================================================================")
    print("PRE-FLIGHT DATA INTEGRITY CERTIFICATION SUMMARY")
    print("=================================================================")
    for r in summary_report:
        print(f"  {r['symbol']:<10} | Rows: {r['rows']:<5} | Range: {r['start']} to {r['end']} | Gaps: {r['gaps']} | {r['status']}")
    print("=================================================================")
    print(f"OVERALL CERTIFICATION: {'100% PASSED' if all_passed else 'FAILED - ACTION REQUIRED'}")
    print("=================================================================")
    return all_passed

if __name__ == '__main__':
    certify_1d_data_integrity()
