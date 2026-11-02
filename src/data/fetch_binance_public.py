"""Download Binance public historical files (data.binance.vision, the official Binance bucket) for BTCUSDT USD-M futures.
Every zip is checked against Binance's own .CHECKSUM file (sha256). Zips are kept compressed. Manifest: <dataset>/MANIFEST.csv.
User permission for this download: 2026-10-26 ("yes karo sab jo jo research ke goal tak leke jaye").
Usage: python src/data/fetch_binance_public.py <dataset> [<dataset> ...]   datasets: see DATASETS"""
import csv
import hashlib
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

P = Path(__file__).resolve().parents[2]
ROOT = P / "data/external/binance_public"
LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix={p}&marker={m}"
FILE = "https://data.binance.vision/{k}"
DATASETS = {
    "fundingRate": "data/futures/um/monthly/fundingRate/BTCUSDT/",
    "premiumIndex5m": "data/futures/um/monthly/premiumIndexKlines/BTCUSDT/5m/",
    "klines5m": "data/futures/um/monthly/klines/BTCUSDT/5m/",
    "metrics": "data/futures/um/daily/metrics/BTCUSDT/",
    "bookDepth": "data/futures/um/daily/bookDepth/BTCUSDT/",
}
LAST = "2026-09"                          # same end as the study window (2026-09-30)


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as e:                # noqa: BLE001  (network retry)
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def list_keys(prefix):
    keys, marker = [], ""
    while True:
        x = get(LIST.format(p=prefix, m=marker)).decode()
        ks = re.findall(r"<Key>([^<]+)</Key>", x)
        keys += ks
        if "<IsTruncated>true" not in x:
            return keys
        marker = ks[-1]


def in_window(key):
    m = re.search(r"(\d{4}-\d{2})(-\d{2})?\.zip$", key)
    return m is not None and m.group(1) <= LAST


def fetch(key, outdir):
    dst = outdir / key.rsplit("/", 1)[1]
    want = get(FILE.format(k=key + ".CHECKSUM")).decode().split()[0]
    if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() == want:
        return key, dst.stat().st_size, want, True, "kept"
    data = get(FILE.format(k=key))
    got = hashlib.sha256(data).hexdigest()
    if got == want:
        dst.write_bytes(data)
    return key, len(data), got, got == want, "downloaded"


def main():
    for ds in sys.argv[1:]:
        outdir = ROOT / ds
        outdir.mkdir(parents=True, exist_ok=True)
        keys = sorted(k for k in list_keys(DATASETS[ds]) if k.endswith(".zip") and in_window(k))
        print(f"{ds}: {len(keys)} files listed", flush=True)
        with ThreadPoolExecutor(6) as ex:
            res = list(ex.map(lambda k: fetch(k, outdir), keys))
        with open(outdir / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["key", "bytes", "sha256", "checksum_ok", "action", "checked_utc"])
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for r in res:
                w.writerow(list(r) + [now])
        bad = [r[0] for r in res if not r[3]]
        print(f"{ds}: ok {len(res) - len(bad)}, checksum FAIL {len(bad)} {bad[:5]}; bytes {sum(r[1] for r in res if r[3]):,}", flush=True)


if __name__ == "__main__":
    main()
