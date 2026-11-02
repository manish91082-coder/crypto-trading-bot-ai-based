"""Minimal rclone stand-in for LAPTOP tests of deploy/ship_logs_drive.py (the remote is a local folder).
Subset: lsjson -R --hash --files-only PATH | copy SRC DST --files-from F [--no-traverse] | copyto SRC DST
Env STUB_CORRUPT=<substring>: after copy/copyto, flip the content of matching remote files (tests a checksum mismatch).
The real rclone binary is tested separately on the VM (T5, T6)."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


def corrupt(p):
    s = os.environ.get("STUB_CORRUPT")
    if s and s in p.as_posix():
        p.write_bytes(p.read_bytes() + b"X")


a = sys.argv[1:]
cmd = a[0]
if cmd == "lsjson":
    root = Path(a[-1])
    if not root.exists():
        sys.stderr.write("directory not found"); sys.exit(3)
    out = []
    for f in sorted(x for x in root.rglob("*") if x.is_file()):
        out.append(dict(Path=f.relative_to(root).as_posix(), Size=f.stat().st_size, IsDir=False,
                        Hashes=dict(md5=hashlib.md5(f.read_bytes()).hexdigest())))
    print(json.dumps(out))
elif cmd == "copy":
    src, dst = Path(a[1]), Path(a[2])
    lst = Path(a[a.index("--files-from") + 1]).read_text().split()
    for r in lst:
        t = dst / r
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / r, t)
        corrupt(t)
elif cmd == "copyto":
    t = Path(a[2])
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a[1], t)
    corrupt(t)
else:
    sys.stderr.write(f"unsupported {cmd}"); sys.exit(2)
