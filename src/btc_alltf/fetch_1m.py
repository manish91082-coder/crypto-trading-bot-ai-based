"""BTC-ALLTF study (2026-10-28): download BTCUSDT 1m klines from data.binance.vision (the official Binance bucket).
User permission, in chat 2026-10-28: spot 1m 2017-08 .. 2025-12 and USD-M futures 1m 2020-01 .. 2025-12 (~430 MB).
2026-01..09: spot 1m is built from the 1s files already in data/external/binance_1s, futures 1m is already there.
Every zip is checked against Binance's own .CHECKSUM (sha256); a file is written only if the two match.
Usage: python src/btc_alltf/fetch_1m.py spot futures   -> data/external/binance_1m/<market>/ + MANIFEST.csv"""
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
ROOT = P / "data/external/binance_1m"
LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix={p}&marker={m}"
FILE = "https://data.binance.vision/{k}"
SETS = {"spot": ("data/spot/monthly/klines/BTCUSDT/1m/", "2017-08", "2025-12"),
        "futures": ("data/futures/um/monthly/klines/BTCUSDT/1m/", "2020-01", "2025-12")}


def get(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return r.read()
        except Exception:                     # noqa: BLE001  (network retry)
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def list_keys(prefix):
    keys, marker = [], ""
    while True:
        x = get(LIST.format(p=prefix, m=marker)).decode()
        ks = re.findall(r"<Key>([^<]+)</Key>", x)
        keys += ks
        if "<IsTruncated>true" not in x:
            return keys
        marker = ks[-1]


def fetch(key, outdir):
    dst = outdir / key.rsplit("/", 1)[1]
    want = get(FILE.format(k=key + ".CHECKSUM")).decode().split()[0]
    if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() == want:
        return key, dst.stat().st_size, want, want, True, "kept"
    data = get(FILE.format(k=key))
    got = hashlib.sha256(data).hexdigest()
    if got == want:
        dst.write_bytes(data)
    return key, len(data), got, want, got == want, "downloaded"


def main():
    for mk in sys.argv[1:]:
        prefix, first, last = SETS[mk]
        outdir = ROOT / mk
        outdir.mkdir(parents=True, exist_ok=True)
        keys = []
        for k in list_keys(prefix):
            m = re.search(r"-(\d{4}-\d{2})\.zip$", k)
            if m and first <= m.group(1) <= last:
                keys.append(k)
        keys.sort()
        print(f"{mk}: {len(keys)} files listed ({keys[0][-11:-4]} .. {keys[-1][-11:-4]})", flush=True)
        with ThreadPoolExecutor(6) as ex:
            res = list(ex.map(lambda k: fetch(k, outdir), keys))
        with open(outdir / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["key", "bytes", "sha256", "binance_checksum", "checksum_ok", "action", "checked_utc"])
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for r in res:
                w.writerow(list(r) + [now])
        bad = [r[0] for r in res if not r[4]]
        print(f"{mk}: ok {len(res) - len(bad)}, checksum FAIL {len(bad)} {bad[:5]}; bytes {sum(r[1] for r in res if r[4]):,}", flush=True)


if __name__ == "__main__":
    main()
