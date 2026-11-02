"""
Build the cloud bundle (2026-10-16). Everything the daily system and its verifiers need, EXCLUDING:
archive/ (project rule), .git/, __pycache__/, venv/, backups/, data/universe_hf/ and data/universe_pre2020_hf/ (15m / 5m
data used only by research Step 25 / S2 / Step 29, not by any daily entry point - checked by import graph).
Writes <out>/cryptobot_bundle_<utc>.tar.gz and MANIFEST_<utc>.csv (path, bytes, sha256) - the manifest is also inside the tar.
Usage: python deploy/make_bundle.py <out_dir>
"""
import sys
import csv
import tarfile
import hashlib
from pathlib import Path
import datetime as dt

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"archive", ".git", "__pycache__", "venv", "backups", ".claude"}
SKIP_PATHS = {"data/universe_hf", "data/universe_pre2020_hf"}


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts) or any(rel == s or rel.startswith(s + "/") for s in SKIP_PATHS):
            continue
        if p.is_file() and p.name != ".env":
            yield p, rel


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tag = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    man = out / f"MANIFEST_{tag}.csv"
    rows = []
    for p, rel in files():
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        rows.append((rel, p.stat().st_size, h.hexdigest()))
    with open(man, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "bytes", "sha256"])
        w.writerows(rows)
    tar = out / f"cryptobot_bundle_{tag}.tar.gz"
    with tarfile.open(tar, "w:gz", compresslevel=6) as t:
        for rel, _, _ in rows:
            t.add(ROOT / rel, arcname=rel)
        t.add(man, arcname="deploy/BUNDLE_MANIFEST.csv")
    print(f"{len(rows)} files, {sum(r[1] for r in rows) / 1e9:.2f} GB raw -> {tar} ({tar.stat().st_size / 1e9:.2f} GB); manifest {man}")


if __name__ == "__main__":
    main(sys.argv[1])
