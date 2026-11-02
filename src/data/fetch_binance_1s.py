"""Download the micro-momentum study files from data.binance.vision (official Binance bucket).
Files: spot BTCUSDT 1s klines and USD-M futures BTCUSDT 1m klines, 2026-01 ... 2026-09.
Every zip is streamed to disk, its sha256 checked against Binance's own .CHECKSUM, and kept only if it matches.
User permission for this download: 2026-10-27 (answer "Jan-Sep 2026 पूरा (Recommended)").
Protocol: logs/micro_momentum_2026/MICRO_MOMENTUM_PROTOCOL_PREREGISTERED.md §2.1.
Usage: python src/data/fetch_binance_1s.py"""
import csv
import hashlib
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

P = Path(__file__).resolve().parents[2]
ROOT = P / "data/external/binance_1s"
FILE = "https://data.binance.vision/{k}"
MONTHS = [f"2026-{m:02d}" for m in range(1, 10)]
KEYS = [f"data/spot/monthly/klines/BTCUSDT/1s/BTCUSDT-1s-{m}.zip" for m in MONTHS] + \
       [f"data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-{m}.zip" for m in MONTHS]


def get_small(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:                      # noqa: BLE001  (network retry)
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def stream(url, dst, tries=4):
    for i in range(tries):
        try:
            h = hashlib.sha256()
            n = 0
            tmp = dst.with_suffix(".part")
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                for b in iter(lambda: r.read(1 << 20), b""):
                    h.update(b)
                    f.write(b)
                    n += len(b)
            return tmp, n, h.hexdigest()
        except Exception:                      # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def main():
    rows = []
    for key in KEYS:
        sub = "spot_1s" if "/spot/" in key else "futures_1m"
        outdir = ROOT / sub
        outdir.mkdir(parents=True, exist_ok=True)
        dst = outdir / key.rsplit("/", 1)[1]
        want = get_small(FILE.format(k=key + ".CHECKSUM")).decode().split()[0]
        tmp, n, got = stream(FILE.format(k=key), dst)
        ok = got == want
        if ok:
            tmp.replace(dst)
        else:
            tmp.unlink()
        rows.append([key, n, got, want, ok, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")])
        print(f"{key} {n} bytes checksum_ok={ok}", flush=True)
    with open(ROOT / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["key", "bytes", "sha256", "binance_checksum", "checksum_ok", "checked_utc"])
        w.writerows(rows)
    print(f"done: {sum(r[4] for r in rows)}/{len(rows)} ok", flush=True)


if __name__ == "__main__":
    main()
