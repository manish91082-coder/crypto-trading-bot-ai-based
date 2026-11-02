"""
Extend the 1D raw files backwards with 2020-01 .. 2021-09 from Binance Vision public monthly klines
(https://data.binance.vision/data/spot/monthly/klines/<SYMBOL>/1d/). No API keys are used.

Zero-trust rules enforced here (the script stops on any violation):
  1. Every monthly zip is checked against Binance's own published SHA256 (<zip>.CHECKSUM).
  2. Timestamps are parsed with auto unit detection (ms / us) and must fall inside the file's month.
  3. Existing rows (2021-10-01 onward) are never modified -- verified value-by-value after the merge.
  4. The merged file must be strictly daily-continuous from the coin's first Binance day to 2026-09-30.
  5. A 404 is accepted only for months before the coin's first available month (listing date);
     any missing month after the first available one is a hard failure.
"""
import sys
import hashlib
import time
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, SYMBOLS

BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"
MONTHS = [f"{y}-{m:02d}" for y in (2020, 2021) for m in range(1, 13) if not (y == 2021 and m > 9)]
EXISTING_START = pd.Timestamp("2021-10-01")


def get(url: str) -> requests.Response:
    last_err = None
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code in (200, 404):
                return r
            last_err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Download failed after retries: {url} ({last_err})")


def fetch_month(symbol: str, month: str):
    url = f"{BASE_URL}/{symbol}/1d/{symbol}-1d-{month}.zip"
    r = get(url)
    if r.status_code == 404:
        return None
    chk = get(url + ".CHECKSUM")
    assert chk.status_code == 200, f"{symbol} {month}: CHECKSUM file missing"
    expected = chk.text.split()[0].strip().lower()
    actual = hashlib.sha256(r.content).hexdigest()
    assert actual == expected, f"{symbol} {month}: SHA256 mismatch ({actual} != {expected})"
    with zipfile.ZipFile(BytesIO(r.content)) as z:
        names = z.namelist()
        assert len(names) == 1, f"{symbol} {month}: unexpected zip contents {names}"
        with z.open(names[0]) as f:
            df = pd.read_csv(f, header=None)
    # Some Binance files carry a header row; drop it if present
    if not str(df.iloc[0, 0]).strip().isdigit():
        df = df.iloc[1:].reset_index(drop=True)
    df = df.iloc[:, 0:6]
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    ts = df["timestamp"].astype("int64")
    unit = "us" if ts.iloc[0] > 1e14 else "ms"
    df["timestamp"] = pd.to_datetime(ts, unit=unit)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="raise")
    m_start = pd.Timestamp(month + "-01")
    m_end = m_start + pd.offsets.MonthBegin(1)
    assert ((df["timestamp"] >= m_start) & (df["timestamp"] < m_end)).all(), f"{symbol} {month}: rows outside month"
    return df, actual


def extend_symbol(symbol: str):
    path = DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv"
    existing = pd.read_csv(path)
    existing["timestamp"] = pd.to_datetime(existing["timestamp"])
    assert existing["timestamp"].min() == EXISTING_START, f"{symbol}: existing file does not start at {EXISTING_START.date()}"

    new_parts, log = [], []
    first_available = None
    for month in MONTHS:
        res = fetch_month(symbol, month)
        if res is None:
            assert first_available is None, f"{symbol}: month {month} missing AFTER data started ({first_available})"
            log.append((month, "404 (not listed yet)", 0, ""))
            continue
        df, sha = res
        if first_available is None:
            first_available = month
        new_parts.append(df)
        log.append((month, "OK sha256 verified", len(df), sha[:12]))

    if not new_parts:
        return dict(symbol=symbol, added=0, first=None, log=log)

    new = pd.concat(new_parts, ignore_index=True)
    new = new[new["timestamp"] < EXISTING_START]
    merged = pd.concat([new, existing], ignore_index=True).sort_values("timestamp").reset_index(drop=True)

    # --- Zero-trust post-merge assertions ---
    assert merged["timestamp"].is_unique, f"{symbol}: duplicate timestamps after merge"
    gaps = merged["timestamp"].diff().dropna()
    assert (gaps == pd.Timedelta(days=1)).all(), f"{symbol}: gap after merge at {merged.loc[gaps[gaps != pd.Timedelta(days=1)].index, 'timestamp'].tolist()[:3]}"
    assert merged["timestamp"].max() == pd.Timestamp("2026-09-30"), f"{symbol}: end date changed"
    assert (merged["high"] >= merged[["open", "close"]].max(axis=1)).all(), f"{symbol}: geometry error (high)"
    assert (merged["low"] <= merged[["open", "close"]].min(axis=1)).all(), f"{symbol}: geometry error (low)"
    assert (merged["volume"] >= 0).all(), f"{symbol}: negative volume"
    old_part = merged[merged["timestamp"] >= EXISTING_START].reset_index(drop=True)
    pd.testing.assert_frame_equal(old_part, existing.reset_index(drop=True), check_dtype=False)

    out = merged.copy()
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)
    return dict(symbol=symbol, added=len(new), first=merged["timestamp"].min().date(),
                last=merged["timestamp"].max().date(), rows=len(merged), log=log)


def main():
    print(f"Extending 1D history: months {MONTHS[0]} .. {MONTHS[-1]} from {BASE_URL}")
    results = []
    for sym in SYMBOLS:
        res = extend_symbol(sym)
        results.append(res)
        print(f"[OK] {sym:<9} +{res['added']:>4} days | now {res.get('first')} -> {res.get('last')} ({res.get('rows')} rows)")
    log_rows = [dict(symbol=r["symbol"], month=m, status=s, rows=n, sha256_prefix=h) for r in results for (m, s, n, h) in r["log"]]
    log_path = DATA_RAW_DIR.parent.parent / "logs" / "download_1d_2020_2021_checksum_log.csv"
    pd.DataFrame(log_rows).to_csv(log_path, index=False)
    print(f"Checksum log: {log_path}")


if __name__ == "__main__":
    main()
