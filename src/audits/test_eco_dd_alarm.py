"""Tests D1-D12 of ECO amendment 3 (logs/eco/ECO_AMENDMENT_3_PREREGISTERED.md §3): DDX drawdown alarm + job coverage.
Synthetic ledgers in a temp dir; nothing in data/ or logs/ is touched (D12 runs test_eco_core.py, which cleans up its own
temp dirs). Usage: python src/audits/test_eco_dd_alarm.py  -> TOTAL n checks, FAIL k; exit 1 on any FAIL."""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "eco"))
import eco_alerts as AL

res = []
CFG = json.loads((R_ / "deploy" / "eco_dd_alarm.json").read_text(encoding="utf-8"))
START = pd.Timestamp(CFG["start_utc"])


def ok(t, c, m):
    res.append(bool(c))
    print(f"[{'PASS' if c else 'FAIL'}] {t}: {m}")


def ledger(path, t0=START - pd.Timedelta(hours=4), end=None):
    """path: list of (hours after t0, equity) knots, linear between knots, one record per hour up to `end`."""
    end = end or t0 + pd.Timedelta(hours=path[-1][0])
    L, i, t = [], 0, t0
    while t <= end:
        h = (t - t0) / pd.Timedelta(hours=1)
        while i + 1 < len(path) and path[i + 1][0] <= h:
            i += 1
        if i + 1 < len(path):
            (h0, e0), (h1, e1) = path[i], path[i + 1]
            e = e0 + (e1 - e0) * (h - h0) / (h1 - h0)
        else:
            e = path[-1][1]
        L.append(dict(T=str(t), mode="demo", ok=True, eco_equity=e, peak=None))
        t += pd.Timedelta(hours=1)
    return L


def at(days, hours=1):
    return START + pd.Timedelta(days=days, hours=hours)


def dd_kinds(L, now, cfg_path=AL.DD_CFG):
    return sorted((k, v) for (k, v) in AL.conditions(L, Path(tempfile.gettempdir()) / "no_cron_here", now, cfg_path) if k.startswith("dd_"))


def ledger_to(dd, now):
    """10k flat until the start (t0 + 4 h), falls to 10k*(1-dd) at day 5, recovers to 10k at day 8, flat until now."""
    return ledger([(0, 10_000.0), (4, 10_000.0), (4 + 24 * 5, 10_000.0 * (1 - dd)), (4 + 24 * 8, 10_000.0)], end=now)


# D1 - D4: levels and bands
for t, dd, days, want in (("D1", 0.05, 10, []), ("D2", 0.08, 10, [("dd_yellow", "H30")]), ("D3", 0.10, 10, [("dd_red", "H30")]),
                          ("D4", 0.10, 45, [])):
    now = at(days)
    got = dd_kinds(ledger_to(dd, now), now)
    s = AL.dd_status(ledger_to(dd, now), now, CFG)
    ok(t, got == want and abs(s["dd"] - dd) < 1e-9, f"dd {s['dd']:.4%} at a={s['a']} (H* {s['H']}) -> {got} (expected {want})")

# D5: a fall before the start does not count; the base is the last pre-start equity
now = at(10)
L5 = ledger([(0, 10_000.0), (3, 8_000.0), (300, 8_000.0)], t0=START - pd.Timedelta(hours=4), end=now)
s5 = AL.dd_status(L5, now, CFG)
ok("D5", dd_kinds(L5, now) == [] and s5["dd"] == 0.0 and s5["base_T"] == str(START - pd.Timedelta(hours=1)) and s5["eq"] == 8_000.0,
   f"20% fall before start, flat after: dd {s5['dd']}, base {s5['base_T']} -> no dd condition")

# D6: dedup, then a deeper fall gives red as a new alert
d = Path(tempfile.mkdtemp())
try:
    now = at(10)
    for r in ledger_to(0.08, now):
        (d / "ledger.jsonl").open("a", encoding="utf-8").write(json.dumps(r) + "\n")
    (d / "cron").mkdir()
    sent = []
    o1, _ = AL.run(d, d, d / "cron", now, send=lambda m: sent.append(m) or "test")
    o2, _ = AL.run(d, d, d / "cron", now + pd.Timedelta(minutes=5), send=lambda m: sent.append(m) or "test")
    (d / "ledger.jsonl").open("a", encoding="utf-8").write(json.dumps(dict(T=str(now + pd.Timedelta(hours=1)), mode="demo", ok=True,
                                                                       eco_equity=9_000.0)) + "\n")
    o3, c3 = AL.run(d, d, d / "cron", now + pd.Timedelta(hours=1, minutes=5), send=lambda m: sent.append(m) or "test")
    k1, k3 = [a["kind"] for a in o1], [a["kind"] for a in o3]
    ok("D6", k1 == ["dd_yellow"] and o2 == [] and k3 == ["dd_red"] and not any(k[0] == "dd_yellow" for k in c3)
       and "warning only" in o1[0]["msg"] and len(sent) == 2,
       f"run1 {k1}, run2 {len(o2)} new, after a 10% fall {k3}; messages sent {len(sent)}; msg: {o1[0]['msg'][:150]}")
finally:
    shutil.rmtree(d)

# D7: reset records, eco_equity None / missing / bool / NaN are ignored
now = at(10)
L7 = ledger_to(0.08, now)
junk = [dict(T=str(at(6, 0)), mode="reset", eco_equity=1.0), dict(T=str(at(6, 0)), mode="demo", ok=True, eco_equity=None),
        dict(T=str(at(6, 0)), mode="demo", ok=False, error="x"), dict(T=str(at(6, 0)), mode="demo", ok=True, eco_equity=True),
        dict(T=str(at(6, 0)), mode="demo", ok=True, eco_equity=float("nan"))]
L7j = L7[:150] + junk + L7[150:]
s7, s7j = AL.dd_status(L7, now, CFG), AL.dd_status(L7j, now, CFG)
ok("D7", s7j["dd"] == s7["dd"] and s7j["n"] == s7["n"] and dd_kinds(L7j, now) == [("dd_yellow", "H30")],
   f"with 5 junk records: dd {s7j['dd']:.6f} = {s7['dd']:.6f}, n {s7j['n']} = {s7['n']}")

# D8: missing config -> dd_alarm_off
now = at(10)
got = dd_kinds(ledger_to(0.08, now), now, Path(tempfile.gettempdir()) / "no_such_eco_dd_alarm.json")
ok("D8", got == [("dd_alarm_off", "-")], f"missing config -> {got}")

# D9: band choice at the edges, and no level before the start
hs = [AL.dd_status(ledger_to(0.01, at(a, 0)), at(a, 0), CFG)["H"] for a in (30, 31, 400)]
pre = AL.dd_status(ledger([(0, 10_000.0), (10, 10_000.0)]), START - pd.Timedelta(hours=1) + pd.Timedelta(hours=8), CFG)
early = AL.dd_status(ledger([(0, 10_000.0), (5, 9_000.0)], t0=START - pd.Timedelta(days=2)), START - pd.Timedelta(hours=1), CFG)
ok("D9", hs == [30, 90, 365] and pre["a"] == 0 and pre["H"] == 30 and early is None,
   f"a = 30 / 31 / 400 -> H* {hs}; a=0 -> H* {pre['H']}; only pre-start records -> {early}")

# D10: the deployed thresholds are the DDX CSV rows, exactly
src = R_ / CFG["source"]
if src.exists():
    rows = [dict(H=int(r["H"]), yellow_dd=float(r["yellow_dd"]), red_dd=float(r["red_dd"])) for r in csv.DictReader(open(src, encoding="utf-8"))]
    h = hashlib.sha256(src.read_bytes()).hexdigest()
    ok("D10", rows == CFG["bands"] and h == CFG["source_sha256"] and CFG["start_utc"] == "2026-10-26T00:00:00",
       f"bands equal the CSV ({len(rows)} rows); CSV sha {h[:12]} = file {CFG['source_sha256'][:12]}; start {CFG['start_utc']}")
else:
    ok("D10", False, f"source CSV {src} not found")

# D11: every crontab job is covered; MK1 failed -> alert, PaperSpotS1 ok -> none
d = Path(tempfile.mkdtemp())
try:
    (d / "MK1.csv").write_text("start_utc,end_utc,exit_code\n2026-10-28T06:20:01Z,2026-10-28T06:20:09Z,1\n")
    (d / "PaperSpotS1.csv").write_text("start_utc,end_utc,exit_code\n2026-10-28T00:45:01Z,2026-10-28T00:45:09Z,0\n")
    now = at(2)
    jf = sorted(k for k in AL.conditions(ledger_to(0.01, now), d, now) if k[0].startswith("job_fail"))
    names = set()
    for l in (R_ / "deploy" / "crontab.txt").read_text().splitlines():
        if not l.startswith("#"):
            names |= {p.split()[0] for p in l.split("run_job.sh ")[1:]}
    ok("D11", jf == [("job_fail_MK1", "2026-10-28T06:20:01Z")] and set(AL.JOBS) == names and len(AL.JOBS) == 29,
       f"job_fail -> {jf}; JOBS {len(AL.JOBS)} = crontab run_job.sh names {len(names)}: {set(AL.JOBS) == names}")
finally:
    shutil.rmtree(d)

# D12: regression - the full ECO core test suite (A2-18 alerts included)
p = subprocess.run([sys.executable, str(R_ / "src" / "audits" / "test_eco_core.py")], capture_output=True, text=True, cwd=R_)
tot = [l for l in p.stdout.splitlines() if l.startswith("TOTAL")]
a218 = [l for l in p.stdout.splitlines() if "A2-18" in l]
ok("D12", p.returncode == 0 and tot and tot[-1].endswith("FAIL 0") and a218 and a218[0].startswith("[A2-18 PASS]"),       # test_eco_core prints "[<id> PASS]"
   f"test_eco_core.py exit {p.returncode}: {tot[-1] if tot else p.stderr[-300:]}; {a218[0][:60] if a218 else 'A2-18 missing'}")

print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
