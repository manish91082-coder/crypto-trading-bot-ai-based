"""EMO-1 stage D: byte-exact download of public data.binance.vision files (protocol logs/emotion/EMO1_PROTOCOL_PREREGISTERED.md §D).
Records SHA256 + row count per zip; looks at no study result. Resumable (a zip already on disk with its manifest SHA is skipped).
  python src/research/emo_download.py --stage liq       monthly 1d klines 2021-11..2026-09, every USDT perp in exchangeInfo
  python src/research/emo_download.py --stage eligible  30-day median quote volume >= 50 M on any day in the window -> eligible.json
  python src/research/emo_download.py --stage metrics   daily metrics zips 2021-12-01..2026-09-30, eligible symbols
  python src/research/emo_download.py --stage perp      monthly 1h klines + fundingRate, eligible symbols
Options: --root (default data/emotion/emo1_raw), --symbols A,B (test subset), --start/--end (test window), --workers 16"""
import argparse
import csv
import hashlib
import io
import json
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
BASE = "https://data.binance.vision/data/futures/um"
LOCK = threading.Lock()


def fetch(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "emo1"}), timeout=60) as r:
                return 200, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, b""
            err = e.code
        except Exception:                                                    # noqa: BLE001 - network: retry
            err = -1
        time.sleep(2 * (k + 1))
    return err, b""


def rows_of(blob):
    z = zipfile.ZipFile(io.BytesIO(blob))
    t = z.read(z.namelist()[0]).decode()
    return sum(1 for l in t.splitlines() if l and l[0].isdigit())             # data rows (header lines start with a letter)


def job(root, rel, man):
    p = root / rel
    if rel in man and p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == man[rel]["sha256"]:
        return None
    if rel in man and man[rel]["status"] == "404":
        return None
    st, blob = fetch(f"{BASE}/{rel}")
    rec = dict(path=rel, status=str(st), sha256="", rows=0, utc=pd.Timestamp.now("UTC").isoformat())
    if st == 200:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)
        rec.update(sha256=hashlib.sha256(blob).hexdigest(), rows=rows_of(blob))
    return rec


def load_man(root):
    f = root / "manifest.csv"
    return {r["path"]: r for r in csv.DictReader(open(f, newline=""))} if f.exists() else {}


def run_jobs(root, rels, workers):
    man = load_man(root)
    f = root / "manifest.csv"
    new = not f.exists()
    n = {"200": 0, "404": 0, "err": 0, "skip": 0}
    with open(f, "a", newline="") as fh, ThreadPoolExecutor(workers) as ex:
        w = csv.DictWriter(fh, fieldnames=["path", "status", "sha256", "rows", "utc"])
        if new:
            w.writeheader()
        for rec in ex.map(lambda r: job(root, r, man), rels):
            if rec is None:
                n["skip"] += 1; continue
            with LOCK:
                w.writerow(rec); fh.flush()
            n[rec["status"] if rec["status"] in ("200", "404") else "err"] += 1
    return n


def months(a, b):
    return [str(m) for m in pd.period_range(a, b, freq="M")]


def symbols(root, subset):
    if subset:
        return subset.split(",")
    f = root / "symbols.json"
    if not f.exists():
        info = json.loads(urllib.request.urlopen("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=60).read())
        syms = sorted(s["symbol"] for s in info["symbols"] if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT")
        f.write_text(json.dumps(dict(utc=pd.Timestamp.now("UTC").isoformat(), n=len(syms), symbols=syms)))
    return json.loads(f.read_text())["symbols"]


def eligible(root, syms, start, end):
    out = {}
    for s in syms:
        rows = []
        for z in sorted((root / "monthly" / "klines" / s / "1d").glob("*.zip")):
            t = zipfile.ZipFile(z).read(zipfile.ZipFile(z).namelist()[0]).decode()
            rows += [l.split(",") for l in t.splitlines() if l and l[0].isdigit()]
        if not rows:
            continue
        d = pd.Series({pd.Timestamp(int(r[0]), unit="ms").normalize(): float(r[7]) for r in rows}).sort_index()
        med = d.rolling(30, min_periods=20).median().shift(1)                # days before the day (point in time)
        w = med[(med.index >= start) & (med.index <= end)]
        if (w >= 50e6).any():
            out[s] = str(w[w >= 50e6].index[0].date())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["liq", "eligible", "metrics", "perp"])
    ap.add_argument("--root", default="data/emotion/emo1_raw")
    ap.add_argument("--symbols", default="")
    ap.add_argument("--start", default="2021-12-01")
    ap.add_argument("--end", default="2026-09-30")
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    root = PROJ / a.root
    root.mkdir(parents=True, exist_ok=True)
    proto = PROJ / "logs" / "emotion" / "EMO1_PROTOCOL_PREREGISTERED.md"
    assert hashlib.sha256(proto.read_bytes()).hexdigest() == (proto.parent / "EMO1_PROTOCOL_SHA256.txt").read_text().split()[0], "EMO-1 protocol changed"
    syms = symbols(root, a.symbols)
    if a.stage == "liq":
        ms = months(pd.Timestamp(a.start) - pd.offsets.MonthBegin(1), a.end)
        n = run_jobs(root, [f"monthly/klines/{s}/1d/{s}-1d-{m}.zip" for s in syms for m in ms], a.workers)
    elif a.stage == "eligible":
        el = eligible(root, syms, pd.Timestamp(a.start), pd.Timestamp(a.end))
        (root / "eligible.json").write_text(json.dumps(dict(utc=pd.Timestamp.now("UTC").isoformat(), n=len(el), first_eligible_day=el), indent=1))
        n = {"eligible": len(el)}
    else:
        el = sorted(json.loads((root / "eligible.json").read_text())["first_eligible_day"]) if not a.symbols else syms
        if a.stage == "metrics":
            days = [d.strftime("%Y-%m-%d") for d in pd.date_range(a.start, a.end, freq="D")]
            rels = [f"daily/metrics/{s}/{s}-metrics-{d}.zip" for s in el for d in days]
        else:
            ms = months(a.start, a.end)
            rels = [f"monthly/klines/{s}/1h/{s}-1h-{m}.zip" for s in el for m in ms] + [f"monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip" for s in el for m in ms]
        n = run_jobs(root, rels, a.workers)
    print(f"emo_download {a.stage}: {n}")


if __name__ == "__main__":
    main()
