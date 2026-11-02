"""ECO trial registry (logs/eco/trial_registry_eco.csv), hash-chained; genesis links to the A0 registry's last line.
Usage: python eco_registry.py genesis | register <ECO-ID> <step> <json-config> | result <ECO-ID> <claims-file> | verify"""
import base64
import datetime
import hashlib
import json
import sys
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
REG = R_ / "logs" / "eco" / "trial_registry_eco.csv"
A0 = R_ / "logs" / "r2_4h_a0" / "trial_registry.csv"
PROTO = R_ / "logs" / "eco" / "ECO_PROTOCOL_PREREGISTERED.md"
HEAD = "trial_id,registered_utc,step,config,config_sha256,protocol_sha256,result_sha256,prev_sha256,line_sha256"
BUDGET = 4


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rows():
    return [l.split(",") for l in REG.read_text().strip().splitlines()[1:]] if REG.exists() else []


def append(tid, step, cfg, result_sha=""):
    rs = rows()
    prev = rs[-1][-1] if rs else A0.read_text().strip().splitlines()[-1].split(",")[-1]
    raw = json.dumps(cfg, sort_keys=True).encode()
    r = [tid, datetime.datetime.now(datetime.timezone.utc).isoformat(), step, "b64:" + base64.b64encode(raw).decode(),
         hashlib.sha256(raw).hexdigest(), sha(PROTO), result_sha, prev]
    r.append(hashlib.sha256(",".join(r).encode()).hexdigest())
    if not REG.exists():
        REG.write_text(HEAD + "\n")
    with open(REG, "a") as fh:
        fh.write(",".join(r) + "\n")
    print("appended", tid, step)


def verify():
    rs = rows()
    prev, ok = A0.read_text().strip().splitlines()[-1].split(",")[-1], True
    for r in rs:
        ok &= r[7] == prev and hashlib.sha256(",".join(r[:-1]).encode()).hexdigest() == r[8]
        ok &= hashlib.sha256(base64.b64decode(r[3][4:])).hexdigest() == r[4]
        prev = r[8]
    trials = [r[0] for r in rs if r[2] not in ("GENESIS",) and not r[2].endswith("-RESULT")]
    ok &= len(set(trials)) == len(trials) <= BUDGET
    print(f"[ECO-REG {'PASS' if ok else 'FAIL'}] {len(rs)} lines, trials {len(trials)}/{BUDGET}, chain linked to A0 registry")
    return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "genesis":
        assert not REG.exists()
        append("ECO-0", "GENESIS", dict(budget=BUDGET, mandate="user 2026-10-21: single 10k USDT ecosystem, Claude decides"))
    elif a[0] == "register":
        assert a[1] not in [r[0] for r in rows()]
        append(a[1], a[2], json.loads(a[3]))
    elif a[0] == "result":
        assert any(r[0] == a[1] for r in rows()) and not any(r[0] == a[1] and r[2].endswith("-RESULT") for r in rows())
        cl = json.loads(Path(a[2]).read_text())
        append(a[1], [r[2] for r in rows() if r[0] == a[1]][0] + "-RESULT", dict(verdict=cl.get("verdict")), sha(a[2]))
    else:
        sys.exit(0 if verify() else 1)
