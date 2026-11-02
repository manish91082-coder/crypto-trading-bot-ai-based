"""Independent verifier for hourly log shipping v2 (protocol + V2 amendment in logs/log_ship).
W1 ledger chain + line hashes; local manifest SHA == ledger; no duplicate (hour, tag) (v7); protocol and amendment SHA == locks
W2 up to N random verified hours: bundle + manifest downloaded from the remote; bundle MD5 == ledger; every tar member's md5
   == manifest (a member whose local file changed since is reported, not failed)
W3 every freed file (rotated .out, deleted backup file) is in a verified bundle manifest with its md5 and that bundle is on the
   remote with the ledger MD5
W4 essential live files still exist
Usage: python verify_log_ship.py --remote R [--root DIR] [--protocol-dir DIR] [--hours 3]   (env RCLONE_CMD as for the shipper)
"""
import argparse
import hashlib
import json
import os
import random
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ESSENTIAL = ["data/emotion/ledger.jsonl", "logs/forward_ls_f4/ledger.csv", "logs/forward_multi_16b/ledger.csv", "logs/strategy_1d_step16_forward/ledger.csv",
             "logs/monitor_n3_evt/ledger.csv", "logs/collector_m4_options/ledger.csv", "logs/cost_study_step2/snapshots.csv",
             "logs/forward_ls_f4/shadow_e11/ledger.csv", "logs/futures_testnet_f6/state_demo_retired_2026-10-25.json", "deploy/crontab.txt",
             "data/eco/ledger.jsonl", "data/eco/state.json", "data/paper_n1/ledger.jsonl", "data/paper_n1/state.json",  # these 4: v3
             "data/eco_demo/ledger.jsonl", "data/eco_demo/state.json", "data/eco_shadow/ledger.jsonl"]  # v6 (F6 state renamed at the cut-over)
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def h(p, algo="sha256"):
    return hashlib.new(algo, Path(p).read_bytes()).hexdigest()


ap = argparse.ArgumentParser()
ap.add_argument("--remote", required=True)
ap.add_argument("--root", default=None)
ap.add_argument("--protocol-dir", default=None)
ap.add_argument("--hours", type=int, default=3)
a = ap.parse_args()
PROJ = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) > 2 else None
root = Path(a.root or PROJ)
pdir = Path(a.protocol_dir or (PROJ / "logs" / "log_ship"))
remote, cmd = a.remote.rstrip("/"), shlex.split(os.environ.get("RCLONE_CMD", "rclone"))


def rc(*args):
    p = subprocess.run(cmd + list(args), capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def rhash(path):
    out = rc("lsjson", "-R", "--hash", "--files-only", path)
    return {} if out is None else {e["Path"]: (e.get("Hashes") or {}).get("md5") for e in json.loads(out or "[]")}


locks = all(h(pdir / f) == (pdir / s).read_text().split()[0] for f, s in
            (("LOG_SHIP_PROTOCOL_PREREGISTERED.md", "LOG_SHIP_PROTOCOL_SHA256.txt"),
             ("LOG_SHIP_PROTOCOL_V2_AMENDMENT.md", "LOG_SHIP_V2_AMENDMENT_SHA256.txt"),
             ("LOG_SHIP_PROTOCOL_V3_AMENDMENT.md", "LOG_SHIP_V3_AMENDMENT_SHA256.txt"),
             ("LOG_SHIP_PROTOCOL_V4_AMENDMENT.md", "LOG_SHIP_V4_AMENDMENT_SHA256.txt"),
             ("LOG_SHIP_PROTOCOL_V5_AMENDMENT.md", "LOG_SHIP_V5_AMENDMENT_SHA256.txt"),
             ("LOG_SHIP_PROTOCOL_V6_AMENDMENT.md", "LOG_SHIP_V6_AMENDMENT_SHA256.txt"),
             ("LOG_SHIP_PROTOCOL_V7_AMENDMENT.md", "LOG_SHIP_V7_AMENDMENT_SHA256.txt")))
lines = (root / "logs" / "log_ship" / "ledger.csv").read_text().strip().splitlines()
head, rows = lines[0].split(","), [dict(zip(lines[0].split(","), l.split(","))) for l in lines[1:]]
prev, chain = "GENESIS", True
mandir = root / "logs" / "log_ship" / "manifests"
for l, d in zip(lines[1:], rows):
    v = l.split(",")
    chain &= d["prev_sha256"] == prev and hashlib.sha256(",".join(v[:-1]).encode()).hexdigest() == d["line_sha256"]
    mp = mandir / f"{d['hour']}_{d['tag']}.json"
    chain &= mp.exists() and h(mp) == d["manifest_sha256"]
    prev = d["line_sha256"]
dup = len(rows) - len({(d["hour"], d["tag"]) for d in rows})     # v7: a reused (hour, tag) overwrote an earlier run's files
ok("W1", chain and locks and rows and not dup, f"{len(rows)} ledger line(s): chain, line hashes, manifest SHA intact={chain}; "
                                               f"duplicate (hour, tag) {dup}; protocol + v2..v7 amendments == locks={locks}")

ver = [d for d in rows if d["verified"] == "True"]
pick = random.Random(7).sample(ver, min(a.hours, len(ver)))
bad, changed, checked = [], 0, 0
with tempfile.TemporaryDirectory() as td:
    for d in pick:
        src = f"{remote}/hourly/{d['hour']}/bundle_{d['tag']}"
        b, m = Path(td) / f"{d['tag']}.tar.gz", Path(td) / f"{d['tag']}.json"
        if rc("copyto", src + ".tar.gz", str(b)) is None or rc("copyto", src + "_manifest.json", str(m)) is None:
            bad.append(f"download {d['hour']} {d['tag']}"); continue
        if h(b, "md5") != d["bundle_md5"] or h(m, "md5") != d["manifest_md5"]:
            bad.append(f"md5 {d['hour']} {d['tag']}"); continue
        man = {x["path"]: x for x in json.loads(m.read_text())["members"]}
        with tarfile.open(b, "r:gz") as tar:
            names = tar.getnames()
            if sorted(names) != sorted(man):
                bad.append(f"members {d['tag']}")
            for n in names:
                data = tar.extractfile(n).read()
                checked += 1
                if hashlib.md5(data).hexdigest() != man[n]["md5"]:
                    bad.append(n)
                lp = root / n
                if lp.exists() and h(lp, "md5") != man[n]["md5"]:
                    changed += 1
ok("W2", not bad and (pick or not ver), f"{len(pick)} verified hour(s) downloaded: bundle/manifest MD5 == ledger, {checked} tar members md5 == manifest; "
                                       f"changed locally since (reported) {changed}; problems {bad[:3]}")

miss = []
for d in rows:
    r = mandir / f"{d['hour']}_{d['tag']}.result.json"
    if not r.exists():
        continue
    res_ = json.loads(r.read_text())
    if not (res_["rotated_out"] or res_["freed_backups"]):
        continue
    if d["verified"] != "True" and res_["rotated_out"]:
        miss.append(f"rotated without verified bundle {d['tag']}")
    mem = {x["path"]: x["md5"] for x in res_["members"]}
    for p in res_["rotated_out"]:
        if p not in mem:
            miss.append(p)
    if res_["rotated_out"]:
        rem = rhash(f"{remote}/hourly/{d['hour']}")
        if rem.get(f"bundle_{d['tag']}.tar.gz") != d["bundle_md5"]:
            miss.append(f"bundle {d['tag']} not on remote")
    for e in res_["freed_backups"]:          # must be inside SOME verified bundle manifest with the same md5
        found = False
        for d2 in ver:
            m2 = mandir / f"{d2['hour']}_{d2['tag']}.json"
            if any(x["path"] == e["file"] and x["md5"] == e["md5"] for x in json.loads(m2.read_text())["members"]):
                found = True; break
        if not found:
            miss.append(e["file"])
ok("W3", not miss, f"every freed file is inside a verified bundle on the remote with its md5; problems {miss[:3]}")
gone = [p for p in ESSENTIAL if not (root / p).exists()]
ok("W4", not gone, f"essential live files present ({len(ESSENTIAL) - len(gone)}/{len(ESSENTIAL)}) {gone}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
