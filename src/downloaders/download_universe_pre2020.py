"""
Step 22 data: the SAME downloader as download_universe_all_usdt.py (same evidence rules: S3 listing, SHA256 vs Binance
.CHECKSUM, per-row ms/us detection, first continuous run of months, 1d cut at the first missing day, atomic writes,
resume), only the month range and output folders differ: 2017-08..2019-12 (data never used by any model so far).
Outputs: data/universe_pre2020/{1d,1h}/, logs/universe_pre2020_download/
"""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "downloaders"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import download_universe_all_usdt as D
from config import DATA_DIR, LOGS_DIR

D.FIRST, D.LAST = "2017-08", "2019-12"
D.OUT = DATA_DIR / "universe_pre2020"
D.LOG = LOGS_DIR / "universe_pre2020_download"

if __name__ == "__main__":
    D.main()
