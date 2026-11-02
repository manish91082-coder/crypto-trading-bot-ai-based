"""
Step 9 data: 1-hour klines with ALL 12 Binance columns (incl. trades count and taker-buy volume) for the 30-coin
universe, 2020-01..2026-09, from Binance Vision monthly files. Every zip is SHA256-verified against Binance's
.CHECKSUM; timestamps auto-detected (ms / us). Output: data/raw_1h_full/<SYMBOL>_1h_full.csv.gz (+ checksum log).
Months that 404 before the first listed month = not listed; after it = delisted/renamed (data ends there).
"""
import sys
import time
import hashlib
import zipfile
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from config import DATA_DIR, LOGS_DIR, SYMBOLS

BASE = "https://data.binance.vision/data/spot/monthly/klines"
EXTRA = ["LUNAUSDT", "FTTUSDT", "AVAXUSDT", "MATICUSDT", "UNIUSDT", "ATOMUSDT", "FILUSDT", "ETCUSDT", "XLMUSDT",
         "TRXUSDT", "BCHUSDT", "EOSUSDT", "ICPUSDT", "AXSUSDT", "SANDUSDT", "ALGOUSDT", "VETUSDT", "THETAUSDT",
         "NEARUSDT", "SHIBUSDT"]
MONTHS = [f"{y}-{m:02d}" for y in range(2020, 2027) for m in range(1, 13) if not (y == 2026 and m > 9)]
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"]
OUT = DATA_DIR / "raw_1h_full"


def get(url):
    err = None
    for k in range(5):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code in (200, 404):
                return r
            err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            err = str(e)
        time.sleep(2 * (k + 1))
    raise RuntimeError(f"{url}: {err}")


def fetch(sym, month):
    url = f"{BASE}/{sym}/1h/{sym}-1h-{month}.zip"
    r = get(url)
    if r.status_code == 404:
        return sym, month, None, "404"
    c = get(url + ".CHECKSUM")
    assert c.status_code == 200, f"{sym} {month}: no CHECKSUM"
    sha = hashlib.sha256(r.content).hexdigest()
    assert sha == c.text.split()[0].strip().lower(), f"{sym} {month}: SHA256 mismatch"
    with zipfile.ZipFile(BytesIO(r.content)) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), header=None)
    if not str(df.iloc[0, 0]).strip().isdigit():
        df = df.iloc[1:].reset_index(drop=True)
    df.columns = COLS
    ts = df["open_time"].astype("int64")
    df["timestamp"] = pd.to_datetime(ts, unit="us" if ts.iloc[0] > 1e14 else "ms")
    for col in COLS[1:6] + COLS[7:11]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    m0 = pd.Timestamp(month + "-01")
    assert ((df.timestamp >= m0) & (df.timestamp < m0 + pd.offsets.MonthBegin(1))).all(), f"{sym} {month}: rows outside month"
    return sym, month, df[["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades",
                           "taker_buy_base", "taker_buy_quote"]], "OK sha256 " + sha[:12]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    syms = SYMBOLS + EXTRA
    jobs = [(s, m) for s in syms for m in MONTHS]
    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda a: fetch(*a), jobs))
    print(f"fetched {len(jobs)} months in {time.time() - t0:.0f}s", flush=True)
    log = []
    for s in syms:
        parts, started, ended = [], False, False
        for sym, m, df, st in [r for r in res if r[0] == s]:
            if df is None:
                ended = ended or started
                log.append(dict(symbol=s, month=m, status="404"))
                continue
            if ended:
                log.append(dict(symbol=s, month=m, status="ignored: after data ended (relisting)"))
                continue
            started = True
            parts.append(df)
            log.append(dict(symbol=s, month=m, status=st, rows=len(df)))
        d = pd.concat(parts).sort_values("timestamp").drop_duplicates("timestamp")
        d.to_csv(OUT / f"{s}_1h_full.csv.gz", index=False, compression="gzip")
        print(f"[OK] {s}: {d.timestamp.min()} -> {d.timestamp.max()} ({len(d)} hours)", flush=True)
    pd.DataFrame(log).to_csv(LOGS_DIR / "download_1h_full_checksum_log.csv", index=False)


if __name__ == "__main__":
    main()
