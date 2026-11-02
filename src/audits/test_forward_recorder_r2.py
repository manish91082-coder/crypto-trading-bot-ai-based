"""Local tests T2-T4 of the R2 forward recorder protocol (T1 = first real run + verifier, done before this).
T2 second run right after -> only new rows, 2nd chained ledger line, verifier all PASS
T3 tamper on a COPY: flip a byte in a raw file -> V2 FAIL; delete a ledger line -> V1 FAIL; edit state.json -> V7 FAIL
T4 lock: a run while RUNNING.lock exists writes nothing
Usage: python test_forward_recorder_r2.py <root> <scratch_dir>
"""
import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
REC = PROJ / "src" / "execution" / "forward_recorder_r2.py"
VER = PROJ / "src" / "audits" / "verify_forward_recorder_r2.py"
out = []


def run(args):
    p = subprocess.run([sys.executable] + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def check(name, cond, msg):
    out.append(cond); print(f"[{name} {'PASS' if cond else 'FAIL'}] {msg}", flush=True)


root, scratch = Path(sys.argv[1]), Path(sys.argv[2])
# T2
n_before = len((root / "ledger.csv").read_text().splitlines())
rc, txt = run([REC, "--root", root])
print(txt.strip())
rc_v, vtxt = run([VER, root, "--replay", "60"])
print(vtxt.strip())
n_after = len((root / "ledger.csv").read_text().splitlines())
check("T2", rc == 0 and n_after == n_before + 1 and rc_v == 0 and "FAIL" not in vtxt.replace("FAIL 0", ""),
      f"second run: ledger lines {n_before - 1} -> {n_after - 1}; verifier exit {rc_v} (V1-V7 incl. 60-row replay)")

# T3 on copies
def fresh(tag):
    d = scratch / f"tamper_{tag}"
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(root, d)
    return d

d = fresh("byte")
f = sorted((d / "raw").rglob("K_spot_klines_BTCUSDT_1h_p0.json.gz"))[0]
raw = bytearray(gzip.decompress(f.read_bytes()))
i = raw.index(b"1") ; raw[i] = ord("2")
with gzip.GzipFile(f, "wb", mtime=0) as g:
    g.write(bytes(raw))
rc, t = run([VER, d])
check("T3a", rc != 0 and "[V2 FAIL]" in t, "one byte changed in a raw file -> verifier V2 FAIL")

d = fresh("line")
lines = (d / "ledger.csv").read_text().splitlines()
(d / "ledger.csv").write_text("\n".join([lines[0]] + lines[2:]) + "\n")
rc, t = run([VER, d])
check("T3b", rc != 0 and "[V1 FAIL]" in t, "first ledger data line deleted -> verifier V1 FAIL")

d = fresh("state")
st = json.loads((d / "state.json").read_text())
k = sorted(st)[0]; st[k] = st[k] - 300_000
(d / "state.json").write_text(json.dumps(st, indent=1, sort_keys=True))
rc, t = run([VER, d])
check("T3c", rc != 0 and "[V7 FAIL]" in t, f"state.json edited ({k}) -> verifier V7 FAIL")

# T4 lock (on a copy so the real chain is untouched)
d = fresh("lock")
(d / "RUNNING.lock").write_text("test")
n_runs = len(list((d / "raw").iterdir()))
rc, t = run([REC, "--root", d])
check("T4", "exit without writing" in t and len(list((d / "raw").iterdir())) == n_runs and (d / "RUNNING.lock").exists(),
      "run with a fresh lock file present -> exits, no new run folder, lock kept")
print(f"TOTAL {len(out)} tests, FAIL {out.count(False)}")
sys.exit(1 if False in out else 0)
