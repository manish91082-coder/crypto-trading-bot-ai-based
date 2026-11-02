"""Write a release manifest on the laptop (2026-10-28, deploy/RELEASES.md). Laptop only; the VM only checks (version_check.py).
  deploy/release_manifest.json      the current release (copied to the VM with the release)
  deploy/releases/<id>.json         the same content, kept for every release (history; never overwritten)
Usage:
  first (baseline) release, from a "path,bytes,sha256" listing of the VM's src/ + deploy/ (read-only hash run):
    python deploy/make_release.py --id R-2026.10.28-1 --from-vm-csv vm_hash.csv
  every later release, from the current manifest: re-hash its files on the laptop, plus/minus named paths:
    python deploy/make_release.py --id R-2026.10.28-2 [--add PATH ...] [--remove PATH ...]
The crontab SHA is that of deploy/crontab.txt (the installed crontab must equal it; version_check.py checks on the VM).
A path whose laptop copy differs from the VM listing is refused in --from-vm-csv mode: the baseline must be a shared state."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUR = ROOT / "deploy" / "release_manifest.json"
HIST = ROOT / "deploy" / "releases"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--from-vm-csv")
    ap.add_argument("--add", nargs="*", default=[])
    ap.add_argument("--remove", nargs="*", default=[])
    a = ap.parse_args()
    out = HIST / f"{a.id}.json"
    if out.exists():
        raise SystemExit(f"{out} exists: a release id is used once")
    vm_only = {}
    if a.from_vm_csv:
        files, differ = {}, []
        for path, _, h in csv.reader(open(a.from_vm_csv, encoding="utf-8")):
            lp = ROOT / path
            if not lp.is_file():
                vm_only[path] = h
            elif sha(lp) == h:
                files[path] = h
            else:
                differ.append(path)
        if differ:
            raise SystemExit(f"laptop and VM differ on {len(differ)} files: {differ[:10]}")
        parent = None
    else:
        base = json.loads(CUR.read_text(encoding="utf-8"))
        files = {p: sha(ROOT / p) for p in base["files"] if p not in a.remove}
        vm_only = {p: h for p, h in base.get("vm_only", {}).items() if p not in a.remove}
        parent = base["release"]
    for p in a.add:
        files[p] = sha(ROOT / p)
    m = dict(release=a.id, parent=parent, utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             crontab_sha256=sha(ROOT / "deploy" / "crontab.txt"),
             files=dict(sorted(files.items())), vm_only=dict(sorted(vm_only.items())))
    HIST.mkdir(exist_ok=True)
    txt = json.dumps(m, indent=1) + "\n"
    out.write_text(txt, encoding="utf-8", newline="\n")
    CUR.write_text(txt, encoding="utf-8", newline="\n")
    print(f"release {a.id} (parent {parent}): {len(files)} files, {len(vm_only)} vm_only, crontab {m['crontab_sha256'][:12]}; "
          f"manifest sha256 {hashlib.sha256(txt.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
