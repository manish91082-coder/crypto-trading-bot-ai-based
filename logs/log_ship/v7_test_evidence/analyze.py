"""Print every ledger row of a test scratch, flag same (hour, tag) collisions and check each row's manifest/bundle."""
import hashlib, json, sys
from collections import Counter
from pathlib import Path
s = Path(sys.argv[1]); fake, remote = s / "fake_vm", s / "fake_drive"
L = (fake / "logs/log_ship/ledger.csv").read_text().strip().splitlines()
rows = [dict(zip(L[0].split(","), l.split(","))) for l in L[1:]]
cnt = Counter((r["hour"], r["tag"]) for r in rows)
for i, r in enumerate(rows, 1):
    mp = fake / "logs/log_ship/manifests" / f"{r['hour']}_{r['tag']}.json"
    man_ok = mp.exists() and hashlib.sha256(mp.read_bytes()).hexdigest() == r["manifest_sha256"]
    b = remote / "hourly" / r["hour"] / f"bundle_{r['tag']}.tar.gz"
    b_ok = b.exists() and hashlib.md5(b.read_bytes()).hexdigest() == r["bundle_md5"] if r["verified"] == "True" else None
    print(f"row{i} {r['run_utc']} tag={r['tag']} n={r['n_files_in_bundle']} verified={r['verified']} rotated={r['n_rotated']} "
          f"same_tag_rows={cnt[(r['hour'], r['tag'])]} local_manifest_sha_ok={man_ok} remote_bundle_md5_ok={b_ok}")
print("COLLISIONS", {k: v for k, v in cnt.items() if v > 1})
