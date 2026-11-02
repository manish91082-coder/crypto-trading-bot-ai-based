"""Which remote bundles hold the freed test chunks, and does each such bundle match a VERIFIED ledger row (md5)?"""
import hashlib, sys, tarfile
from pathlib import Path
for s in map(Path, sys.argv[1:]):
    fake, remote = s / "fake_vm", s / "fake_drive"
    L = (fake / "logs/log_ship/ledger.csv").read_text().strip().splitlines()
    rows = [dict(zip(L[0].split(","), l.split(","))) for l in L[1:]]
    print("==", s.name)
    for b in sorted((remote / "hourly").rglob("bundle_*.tar.gz")):
        with tarfile.open(b) as t:
            hit = [n for n in t.getnames() if "TEST_JOB" in n or "RUNNING_JOB" in n]
        if not hit: continue
        md5, tag = hashlib.md5(b.read_bytes()).hexdigest(), b.name[7:13]
        rws = [(r["verified"], r["bundle_md5"] == md5, r["n_rotated"]) for r in rows if r["tag"] == tag]
        print(f"  {b.parent.name}/{b.name} holds {hit}; ledger rows with this tag (verified, md5_match, n_rotated): {rws}")
