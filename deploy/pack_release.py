"""Pack a release for the VM (laptop, 2026-10-28, deploy/RELEASES.md).
Usage: python deploy/pack_release.py <out.tar> [--extra PATH ...]
The tar holds every file of the current release (deploy/release_manifest.json) whose SHA differs from, or is absent in,
its parent release, plus the release records (release_manifest.json, releases/<id>.json, RELEASES.md) and --extra paths
(append-only records / evidence, files or dirs). Then on the VM: unpack to /tmp/rel_<id>, run deploy/apply_release.py."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--extra", nargs="*", default=[])
    a = ap.parse_args()
    cur = json.loads((ROOT / "deploy" / "release_manifest.json").read_text(encoding="utf-8"))
    par = json.loads((ROOT / "deploy" / "releases" / f"{cur['parent']}.json").read_text(encoding="utf-8"))
    files = [p for p, h in cur["files"].items() if par["files"].get(p) != h]
    files += ["deploy/release_manifest.json", f"deploy/releases/{cur['release']}.json", "deploy/RELEASES.md"]
    for e in a.extra:
        q = ROOT / e
        files += [x.relative_to(ROOT).as_posix() for x in sorted(q.rglob("*")) if x.is_file()] if q.is_dir() else [e]
    files = sorted(set(files))
    with tarfile.open(a.out, "w") as t:
        for p in files:
            t.add(ROOT / p, arcname=p)
    print(f"release {cur['release']} (parent {cur['parent']}): {len(files)} files -> {a.out} "
          f"sha256 {hashlib.sha256(Path(a.out).read_bytes()).hexdigest()}")
    for p in files:
        print("  ", p)


if __name__ == "__main__":
    main()
