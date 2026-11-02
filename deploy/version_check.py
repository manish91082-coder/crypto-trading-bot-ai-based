"""Release check (2026-10-28, deploy/RELEASES.md). Answers "which release is this copy, and does every file still match it?"
on the laptop and on the VM with the same code.
Reads deploy/release_manifest.json:
  release, utc, files {path: sha256}   - must be identical on laptop and VM
  vm_only {path: sha256}               - VM-only files (old bundle manifest, crontab backups): checked only on the VM
  crontab_sha256                       - `crontab -l` must match it (checked only on the VM)
Files under src/ and deploy/ that are not in the manifest are listed as "extra" (laptop research code is expected there,
none is expected on the VM); they do not change the verdict on the laptop, but they do on the VM.
Usage: python deploy/version_check.py [--vm | --laptop]   (default: --vm on Linux, --laptop otherwise). Exit 0 = OK."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = {"deploy/release_manifest.json", "deploy/RELEASES.md"}          # the release records themselves


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tree():
    for top in ("src", "deploy"):
        for d, dirs, fs in os.walk(ROOT / top):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in fs:
                yield (Path(d) / f).relative_to(ROOT).as_posix()


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--vm", action="store_true")
    g.add_argument("--laptop", action="store_true")
    a = ap.parse_args()
    vm = a.vm or (not a.laptop and sys.platform.startswith("linux"))
    m = json.loads((ROOT / "deploy" / "release_manifest.json").read_text(encoding="utf-8"))
    bad = []
    for p, h in m["files"].items():
        f = ROOT / p
        if not f.is_file():
            bad.append(f"missing {p}")
        elif sha(f) != h:
            bad.append(f"differs {p} {sha(f)[:12]} (release {h[:12]})")
    if vm:
        for p, h in m.get("vm_only", {}).items():
            f = ROOT / p
            if not f.is_file() or sha(f) != h:
                bad.append(f"vm_only {'missing' if not f.is_file() else 'differs'} {p}")
        cr = subprocess.run(["crontab", "-l"], capture_output=True).stdout
        if hashlib.sha256(cr).hexdigest() != m["crontab_sha256"]:
            bad.append(f"crontab differs {hashlib.sha256(cr).hexdigest()[:12]} (release {m['crontab_sha256'][:12]})")
    known = set(m["files"]) | set(m.get("vm_only", {})) | SELF
    extra = sorted(p for p in tree() if p not in known and not p.startswith("deploy/releases/"))
    if vm and extra:
        bad.append(f"extra on VM {len(extra)}: {extra[:10]}")
    where = "VM" if vm else "laptop"
    for b in bad:
        print("  ", b)
    print(f"[{'VERSION OK' if not bad else 'VERSION DRIFT'}] {where}: release {m['release']} ({m['utc']}); "
          f"{len(m['files'])} files{' + ' + str(len(m.get('vm_only', {}))) + ' vm_only + crontab' if vm else ''} checked; "
          f"problems {len(bad)}; extra (not in release) {len(extra)}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
