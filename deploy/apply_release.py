"""Apply a staged release on the VM (2026-10-28, deploy/RELEASES.md). Usage: venv/bin/python deploy/apply_release.py /tmp/rel_<id> [--root /opt/cryptobot]
(--root is needed only when this script is run from the staged dir, i.e. the first time it is installed.)
The staged dir is the release tar unpacked: the new deploy/release_manifest.json, deploy/releases/<id>.json, the files.
  1 time guard: refuses inside UTC minute :16-:33 (ECO cycle :20, alerts :22/:28, log-ship :25)
  2 pre-check: this VM == the parent release (deploy/releases/<parent>.json here: files + vm_only + crontab -l)
  3 backup: every file that will be replaced -> backups/release_<id>/<path> (refuses if that dir exists)
  4 install: copy to <path>.rel_tmp then os.replace (one complete file at any time), then SHA == staged for every file
  5 check: deploy/version_check.py --vm must say VERSION OK for the new release
Rollback: copy backups/release_<id>/ back and deploy/releases/<parent>.json to deploy/release_manifest.json."""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(st, root):
    st = Path(st)
    os.chdir(root)
    now = dt.datetime.now(dt.timezone.utc)
    if 16 <= now.minute <= 33:
        raise SystemExit(f"ABORT {now:%H:%M:%S}Z: inside the :16-:33 UTC window")
    new = json.loads((st / "deploy" / "release_manifest.json").read_text(encoding="utf-8"))
    rid, parent = new["release"], new["parent"]
    par = json.loads(Path(f"deploy/releases/{parent}.json").read_text(encoding="utf-8"))
    cur = json.loads(Path("deploy/release_manifest.json").read_text(encoding="utf-8"))["release"]
    bad = [] if cur == parent else [f"VM manifest says {cur}, the new release's parent is {parent}"]
    bad += [p for p, h in {**par["files"], **par["vm_only"]}.items() if not Path(p).is_file() or sha(p) != h]
    cr = hashlib.sha256(subprocess.run(["crontab", "-l"], capture_output=True).stdout).hexdigest()
    bad += [] if cr == par["crontab_sha256"] else [f"crontab {cr[:12]} != parent {par['crontab_sha256'][:12]}"]
    staged = sorted(p.relative_to(st).as_posix() for p in st.rglob("*") if p.is_file())
    replace = [p for p in staged if Path(p).exists()]
    print(f"{now:%Y-%m-%dT%H:%M:%S}Z release {rid} (parent {parent}); pre-check problems {len(bad)} {bad[:5]}; "
          f"staged {len(staged)}, replace {replace}")
    if bad:
        raise SystemExit("ABORT: this VM is not the parent release")
    bk = Path(f"backups/release_{rid}")
    if bk.exists():
        raise SystemExit(f"ABORT: {bk} exists")
    for p in replace:
        (bk / p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, bk / p)
    for p in staged:
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(st / p, p + ".rel_tmp")
        os.replace(p + ".rel_tmp", p)
    mis = [p for p in staged if sha(p) != sha(st / p)]
    print(f"backup {bk} ({len(replace)} files); installed {len(staged)}; sha mismatches {mis}")
    vc = subprocess.run([sys.executable, "deploy/version_check.py", "--vm"], capture_output=True, text=True)
    print(vc.stdout.strip())
    ok = not mis and vc.returncode == 0
    print(f"APPLY {'OK' if ok else 'FAIL'} {rid} {dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%S}Z")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("staged")
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args()
    main(a.staged, a.root)
