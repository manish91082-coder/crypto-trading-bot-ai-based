import gzip
import shutil
from pathlib import Path
import sys

# Dynamically resolve SRC directory for relative imports
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR

def decompress_1m_files():
    """Extract .csv.gz files to .csv if they don't already exist."""
    gz_files = list(DATA_RAW_DIR.glob('*_1m_Raw_5Years.csv.gz'))
    print(f"Found {len(gz_files)} compressed 1m data files.")
    for gz in gz_files:
        csv_file = gz.with_suffix('')
        if not csv_file.exists():
            print(f"Decompressing {gz.name} -> {csv_file.name}...")
            with gzip.open(gz, 'rb') as f_in, open(csv_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            print(f"  -> Extracted: {csv_file.name}")
        else:
            print(f"[SKIP] {csv_file.name} already exists.")
    print("Done! All 1m files are available in data/raw/.")

if __name__ == '__main__':
    decompress_1m_files()
