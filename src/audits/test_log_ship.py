"""Laptop tests T1-T5 of deploy/ship_logs_drive.py v2 (bundle per hour) with the rclone stub.
Builds a fake VM root from a copy of real VM logs, plus old backups and idle / fresh .out files.
Usage: python test_log_ship.py <vm_logs_copy_dir> <scratch_dir> [<vm_extra_root>]
v3: the optional <vm_extra_root> holds copies of the v3 paths (data/eco, data/paper_n1, logs/eco, ...); T6 checks they ship.
v4: T7 checks that an idle .out still held open by a process (fake /proc via LOGSHIP_PROC_ROOT) is not rotated.
v7: T8 a run never reuses an existing (hour, tag); T9 (POSIX) simultaneous runs -> one ships; T8/T9-verify before the T5 tamper."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
SHIP, VER, STUB = PROJ / "deploy" / "ship_logs_drive.py", PROJ / "src" / "audits" / "verify_log_ship.py", PROJ / "src" / "audits" / "rclone_stub.py"
src, scratch = Path(sys.argv[1]), Path(sys.argv[2])
fake, remote = scratch / "fake_vm", scratch / "fake_drive"
for d in (fake, remote):
    if d.exists():
        shutil.rmtree(d)
(fake / "logs").mkdir(parents=True)
for d in src.iterdir():
    if d.is_dir():
        shutil.copytree(d, fake / "logs" / d.name)
(fake / "deploy").mkdir(); shutil.copy(PROJ / "deploy" / "crontab.txt", fake / "deploy" / "crontab.txt")
extra = Path(sys.argv[3]) if len(sys.argv) > 3 else None
if extra:                                                   # v3 paths, copied with their relative paths
    for f in extra.rglob("*"):
        if f.is_file():
            t = fake / f.relative_to(extra)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, t)
today = time.strftime("%Y-%m-%d", time.gmtime())
for day in ("2026-10-10", "2026-10-11", today):
    b = fake / "backups" / day / "sub"; b.mkdir(parents=True)
    (b / "ledger_copy.csv").write_text(f"backup {day}\n")
old = time.time() - 3600
for f in (fake / "logs" / "cron_status").glob("*.out"):
    os.utime(f, (old, old))
env = dict(os.environ, RCLONE_CMD=f'"{Path(sys.executable).as_posix()}" "{STUB.as_posix()}"', PYTHONIOENCODING="utf-8")
res = []


def run(script, *args, extra=None):
    p = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True, env=dict(env, **(extra or {})))
    return p.returncode, (p.stdout + p.stderr).strip()


def check(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def last():
    L = (fake / "logs" / "log_ship" / "ledger.csv").read_text().strip().splitlines()
    return dict(zip(L[0].split(","), L[-1].split(",")))


cs = fake / "logs" / "cron_status"
n_out = len(list(cs.glob("*.out")))
rc, out = run(SHIP, "--remote", remote, "--root", fake); print(out)
rv, vo = run(VER, "--remote", remote, "--root", fake); print(vo)
L1 = last()
bk = sorted(p.name for p in (fake / "backups").iterdir())
check("T1", rc == 0 and rv == 0 and L1["verified"] == "True" and int(L1["n_rotated"]) == n_out and not list(cs.glob("*.out*"))
      and bk == [today] and int(L1["n_files_in_bundle"]) > 100,
      f"first run: 1 bundle with {L1['n_files_in_bundle']} files verified, {n_out} idle .out rotated + freed, old backups freed (kept {bk}); verifier exit {rv}")

if extra:                                                   # T6 (v3): every v3 file is a member of the first verified bundle, md5 equal
    import hashlib
    man = json.loads(sorted((fake / "logs" / "log_ship" / "manifests").glob("*_??????.json"))[0].read_text())
    mem = {m["path"]: m["md5"] for m in man["members"]}
    v3 = [f for f in extra.rglob("*") if f.is_file()]
    miss = [f.relative_to(extra).as_posix() for f in v3 if mem.get(f.relative_to(extra).as_posix()) != hashlib.md5(f.read_bytes()).hexdigest()]
    check("T6", v3 and not miss and L1["verified"] == "True",
          f"v3 paths: {len(v3)} files (data/eco, data/paper_n1, logs/eco, logs/paper_n1, deploy configs) all in the first verified bundle with equal md5; missing {miss[:5]}")

rc, out = run(SHIP, "--remote", remote, "--root", fake); print(out)
L2 = last()
check("T2", rc == 0 and L2["verified"] == "True" and int(L2["n_files_in_bundle"]) <= 5 and L2["n_rotated"] == "0",
      f"second run: only {L2['n_files_in_bundle']} changed file(s) (the shipper's own ledger / manifests), rotated 0")

idx_before = (fake / "logs" / "log_ship" / "shipped_index.json").read_text()
o = cs / "TEST_JOB.out"; o.write_text("chunk to ship\n"); os.utime(o, (old, old))
rc, out = run(SHIP, "--remote", remote, "--root", fake, extra=dict(STUB_CORRUPT="hourly/")); print(out)
L3 = last()
check("T3", rc != 0 and L3["verified"] == "False" and (cs / "TEST_JOB.out.shipping").exists()
      and (fake / "logs" / "log_ship" / "shipped_index.json").read_text() == idx_before,
      "remote copy corrupted -> not verified, shipped index unchanged, .out chunk kept (.shipping), nothing freed")

rc, out = run(SHIP, "--remote", remote, "--root", fake); print(out)
L4 = last()
f2 = cs / "FRESH_JOB.out"; f2.write_text("being written\n")
rc2, out2 = run(SHIP, "--remote", remote, "--root", fake); print(out2)
check("T4", rc == 0 and L4["verified"] == "True" and L4["n_rotated"] == "1" and not (cs / "TEST_JOB.out.shipping").exists()
      and f2.exists() and rc2 == 0,
      "next run re-bundles the kept chunk, verifies and frees it; a .out modified < 15 min ago is NOT rotated")
rv, vo = run(VER, "--remote", remote, "--root", fake, "--hours", "10"); print(vo)
check("T4-verify", rv == 0, "verifier W1-W4 after all runs (all verified hours downloaded and checked)")

# T7 (v4): an idle .out that a process still holds open is not rotated; rotated once it is closed
o7 = cs / "RUNNING_JOB.out"; o7.write_text("silent long job\n"); os.utime(o7, (old, old))
proc = scratch / "fake_proc"; (proc / "4242" / "fd").mkdir(parents=True, exist_ok=True)
(proc / "4242" / "fd" / "1").write_text(str(o7.resolve()))
rc7, out7 = run(SHIP, "--remote", remote, "--root", fake, extra=dict(LOGSHIP_PROC_ROOT=str(proc))); print(out7)
res7 = json.loads(sorted((fake / "logs" / "log_ship" / "manifests").glob("*.result.json"))[-1].read_text())
held_ok = o7.exists() and "RUNNING_JOB.out" in res7.get("out_busy", [])
shutil.rmtree(proc / "4242")
rc8, out8 = run(SHIP, "--remote", remote, "--root", fake, extra=dict(LOGSHIP_PROC_ROOT=str(proc))); print(out8)
check("T7", rc7 == 0 and held_ok and rc8 == 0 and not o7.exists() and not (cs / "RUNNING_JOB.out.shipping").exists(),
      f"v4: .out held open by a process -> not rotated (out_busy {res7.get('out_busy')}); after it is closed -> rotated and freed")

# T8 (v7): a run never reuses the (hour, tag) of an earlier run. Placeholder manifests take the current and the next 2 seconds.
mand = fake / "logs" / "log_ship" / "manifests"
t0, held, mine = time.time(), {}, []
for k in range(3):
    t = time.gmtime(t0 + k)
    p = mand / f"{time.strftime('%Y-%m-%d_%H', t)}_{time.strftime('%H%M%S', t)}.json"
    if not p.exists():
        p.write_text("PLACEHOLDER\n"); mine.append(p)
    held[p] = p.read_bytes()
rc_t8, out_t8 = run(SHIP, "--remote", remote, "--root", fake); print(out_t8)
L8 = last()
kept = all(p.read_bytes() == b for p, b in held.items())
check("T8", rc_t8 == 0 and kept and f"{L8['hour']}_{L8['tag']}" not in {p.stem for p in held} and L8["verified"] == "True",
      f"v7: names held {sorted(p.stem for p in held)} -> new run {L8['hour']}_{L8['tag']}, held manifests unchanged {kept}")
for p in mine:
    p.unlink()

# T9 (v7, POSIX only): 4 runs started together, rclone slowed to 2 s per call -> exactly one ships (atomic lock)
if os.name == "posix":
    led = fake / "logs" / "log_ship" / "ledger.csv"
    n0 = len(led.read_text().strip().splitlines())
    slow = dict(env, RCLONE_CMD=f"sh -c 'sleep 2; exec \"$0\" \"$@\"' \"{sys.executable}\" \"{STUB}\"")
    ps = [subprocess.Popen([sys.executable, str(SHIP), "--remote", str(remote), "--root", str(fake)], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, env=slow) for _ in range(4)]
    outs = [p.communicate()[0].strip() for p in ps]; print("\n".join(outs))
    n_new, n_busy = len(led.read_text().strip().splitlines()) - n0, sum("another ship run is active" in o for o in outs)
    check("T9", n_new == 1 and n_busy == 3 and all(p.returncode == 0 for p in ps),
          f"v7: 4 simultaneous runs -> {n_new} ledger row(s) added, {n_busy} exited on the lock, exit codes {[p.returncode for p in ps]}")
rv, vo = run(VER, "--remote", remote, "--root", fake, "--hours", "10"); print(vo)
check("T8/T9-verify", rv == 0, "verifier W1-W4 after T7-T9, before the T5 tamper")

bundles = sorted((remote / "hourly").rglob("bundle_*.tar.gz"))
victim = bundles[0]
victim.write_bytes(victim.read_bytes()[:-10] + b"0123456789")
rv, vo = run(VER, "--remote", remote, "--root", fake, "--hours", "10"); print(vo)
check("T5", rv != 0 and "[W2 FAIL]" in vo, "a tampered bundle on the remote -> verifier W2 FAIL")
print(f"TOTAL {len(res)} tests, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
