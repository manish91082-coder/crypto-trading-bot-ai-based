"""On the VM, after unpacking into /opt/cryptobot: every file of deploy/BUNDLE_MANIFEST.csv exists with the same size and
SHA256. Usage: venv/bin/python deploy/verify_bundle.py"""
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
bad, n = [], 0
with open(ROOT / "deploy" / "BUNDLE_MANIFEST.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        p = ROOT / r["path"]
        n += 1
        if not p.is_file():
            bad.append(("missing", r["path"]))
            continue
        h = hashlib.sha256()
        with open(p, "rb") as g:
            for b in iter(lambda: g.read(1 << 20), b""):
                h.update(b)
        if p.stat().st_size != int(r["bytes"]) or h.hexdigest() != r["sha256"]:
            bad.append(("differs", r["path"]))
print(f"[{'BUNDLE PASS' if not bad else 'BUNDLE FAIL'}] {n} files checked; problems {len(bad)}: {bad[:10]}")
raise SystemExit(1 if bad else 0)
