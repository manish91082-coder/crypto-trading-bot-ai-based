"""Independent verifier for CONSOL-2026-10-28 (protocol logs/consolidation_2026_10_28/CONSOL_PROTOCOL_PREREGISTERED.md).

Uses only the stdlib. Does not import any project module. Exits 1 on any FAIL.
K1 source SHAs = manifest          K2 study verifier outputs: SHA + 0-FAIL total; manual-day checks BAD 0
K3 claim substrings in sources (+ numeric match)   K4 claim values in the report
K5 the 17 report names in the report               K6 every ledger item has one class + a source
K7 VM snapshot SHA, crontab SHA line, no non-zero exits in 48 h
"""
import csv, hashlib, json, re, sys
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
D = PROJ / "logs/consolidation_2026_10_28"
REPORT = PROJ / "CONSOLIDATED_ACTION_PLAN_28_OCT_2026.md"
results = []

def check(name, ok, msg):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {msg}")

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def text(p):
    return Path(p).read_text(encoding="utf-8")

def rows(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

# K0 protocol lock
lock = text(D / "PROTOCOL_SHA256.txt").split()[0]
check("K0 protocol SHA", lock == sha(D / "CONSOL_PROTOCOL_PREREGISTERED.md"), lock[:12])

# K1 sources
man = rows(D / "source_manifest.csv")
bad = [r["path"] for r in man if sha(PROJ / r["path"]) != r["sha256"]]
check("K1 source SHAs", not bad and len(man) == 29, f"{len(man)} files, mismatches {bad}")

# K2 verifier outputs
vm = rows(D / "verifier_manifest.csv")
bad = []
for r in vm:
    p = PROJ / r["path"]
    t = p.read_text(encoding="utf-8", errors="replace")
    # totals come as "FAIL 0" or "N PASS, 0 FAIL"; a stray "0 FAIL" elsewhere must not hide a non-zero total
    tot = re.findall(r"TOTAL[^\n]*", t)
    zero = (tot and all(re.search(r"(FAIL 0\b|\b0 FAIL\b)", x) for x in tot)) or "RESULT: ALL PASS" in t
    if sha(p) != r["sha256"] or not zero:
        bad.append(r["path"])
for extra in ("verify_monthly_outlook_rerun.txt", "verify_1d_true_fee_rerun.txt"):
    t = text(D / extra)
    if not re.search(r"TOTAL \d+ checks, FAIL 0", t):
        bad.append(extra)
man_days = []
for i in range(1, 11):
    t = text(PROJ / f"logs/manual_day_study/day_{i:02d}_check.txt").strip().splitlines()[-1]
    m = re.match(r"TOTAL (\d+) claims, BAD 0$", t)
    if not m:
        bad.append(f"day_{i:02d}")
    else:
        man_days.append(int(m.group(1)))
check("K2 study verifiers", not bad, f"{len(vm)} stored + 2 re-runs, manual claims {sum(man_days)}, bad {bad}")
check("K2b manual-day total 258", sum(man_days) == 258, str(sum(man_days)))

# K3 / K4 claims
claims = json.loads(text(D / "claims.json"))
rep = text(REPORT)
srcset = {r["path"] for r in man} | {"logs/consolidation_2026_10_28/vm_snapshot.txt"}

def nums(s):
    s = s.replace("−", "-")
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", s)]

bad3, bad4 = [], []
for c in claims:
    src = c["source"]
    if src not in srcset:
        bad3.append((c["id"], "source not locked"))
        continue
    t = (PROJ / src).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    if c["substr"] not in t:
        bad3.append((c["id"], "substr"))
    elif c["num"] is not None:
        tol = max(c["tol"], 1e-9)
        if not any(abs(x - c["num"]) <= tol for x in nums(c["substr"])):
            bad3.append((c["id"], "num"))
    if c["value"] not in rep:
        bad4.append(c["id"])
check("K3 claim substrings + numbers in sources", not bad3, f"{len(claims)} claims, bad {bad3}")
check("K4 claim values in report", not bad4, f"bad {bad4}")

# K5 coverage
names = [r["path"] for r in man if r["path"].startswith("RESEARCH_")]
miss = [n for n in names if n not in rep]
check("K5 17 reports covered", len(names) == 17 and not miss, f"{len(names)} names, missing {miss}")

# K6 ledger items: every ID row in section 3 has a valid class letter and points to a source
sec3 = rep.split("## 3. पूरा action ledger")[1].split("## 4.")[0]
ids = re.findall(r"^\| \*\*([AWUTS])(\d+)\*\* \|", sec3, flags=re.M)
seen = {}
for cls, n in ids:
    seen.setdefault(f"{cls}{n}", 0)
    seen[f"{cls}{n}"] += 1
dups = [k for k, v in seen.items() if v > 1]
blocks = {"A": "### 3A.", "W": "### 3W.", "U": "### 3U.", "T": "### 3T.", "S": "### 3S."}
wrong = []
for cls, head in blocks.items():
    part = sec3.split(head)[1].split("\n### ")[0]
    for c2, n in re.findall(r"^\| \*\*([AWUTS])(\d+)\*\* \|", part, flags=re.M):
        if c2 != cls:
            wrong.append(f"{c2}{n}")
# coverage table must cite only defined IDs
cov = rep.split("## 8.")[1].split("**Studies")[0]
cited = set(re.findall(r"\b([AWUTS]\d+)\b", cov))
undefined = sorted(cited - set(seen))
check("K6 ledger classes", ids and not dups and not wrong and not undefined,
      f"{len(seen)} items (A {sum(k[0]=='A' for k in seen)}, W {sum(k[0]=='W' for k in seen)}, U {sum(k[0]=='U' for k in seen)}, "
      f"T {sum(k[0]=='T' for k in seen)}, S {sum(k[0]=='S' for k in seen)}); dups {dups}; wrong block {wrong}; undefined in coverage {undefined}")

# K7 VM snapshot
lines = text(D / "vm_snapshot_SHA256.txt").split("\n")
snap_sha = lines[0].split()[0]
snap = (D / "vm_snapshot.txt").read_text(encoding="utf-8", errors="replace")
ok_sha = snap_sha == sha(D / "vm_snapshot.txt")
m = re.search(r"crontab_l_sha256 ([0-9a-f]{64})", snap)
cron_ok = bool(m) and m.group(1) == sha(PROJ / "deploy/crontab.txt")
nz = re.findall(r"^(\S+): runs48h=(\d+) nonzero48h=(\d+)", snap, flags=re.M)
bad_nz = [j for j, _, z in nz if z != "0"]
check("K7 VM snapshot", ok_sha and cron_ok and len(nz) == 31 and not bad_nz,
      f"sha ok {ok_sha}, crontab == deploy/crontab.txt {cron_ok}, {len(nz)} jobs, non-zero {bad_nz}")

n_fail = results.count(False)
print(f"\nTOTAL {len(results)} checks, {len(results) - n_fail} PASS, {n_fail} FAIL -> {'ALL PASS' if n_fail == 0 else 'FAIL'}")
sys.exit(1 if n_fail else 0)
