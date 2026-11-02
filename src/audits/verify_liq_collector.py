"""Daily check of the live liquidation collector (logs/live_collect/LIQ_COLLECTOR_RECORD.md). Imports nothing from src/collect.
C1 every closed day in MANIFEST.csv: file SHA256 and line count match; C2 every line of the closed days and of today's open file is
JSON with m.e == forceOrder; C3 heartbeat younger than 30 min; C4 disconnect gaps per day from sessions.log (information).
Usage: python src/audits/verify_liq_collector.py"""
import csv
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parents[2] / "data/live_collect/liq"
res = []


def ok(name, good, msg):
    res.append(bool(good))
    print(f"[{name} {'PASS' if good else 'FAIL'}] {msg}", flush=True)


rows = list(csv.DictReader(open(R / "MANIFEST.csv", encoding="utf-8"))) if (R / "MANIFEST.csv").exists() else []
bad = [r["day"] for r in rows if not (R / r["file"]).exists() or hashlib.sha256((R / r["file"]).read_bytes()).hexdigest() != r["sha256"]
       or sum(1 for _ in gzip.open(R / r["file"], "rt", encoding="utf-8")) != int(r["lines"])]
ok("C1", not bad, f"{len(rows)} closed days: SHA + line count; bad {bad}")
badl, n = 0, 0
for f in [R / r["file"] for r in rows] + sorted(R.glob("*.jsonl")):
    op = gzip.open if f.suffix == ".gz" else open
    for line in op(f, "rt", encoding="utf-8"):
        n += 1
        try:
            x = json.loads(line)
            badl += x["m"]["e"] != "forceOrder"
        except Exception:                                   # noqa: BLE001
            badl += 1
ok("C2", badl == 0, f"{n} stored messages parsed, {badl} bad")
hb = R / "heartbeat.txt"
age = (datetime.now(timezone.utc) - datetime.strptime(hb.read_text().strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds() / 60 if hb.exists() else None
ok("C3", age is not None and age < 30, f"heartbeat age {None if age is None else round(age, 1)} min")
gaps = {}
last_dis = None
for line in open(R / "sessions.log", encoding="utf-8") if (R / "sessions.log").exists() else []:
    ts, ev = line.split(" ", 1)
    t = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
    if ev.startswith("DISCONNECT") or ev.startswith("STOP"):
        last_dis = t
    elif ev.startswith("CONNECT") and last_dis is not None:
        gaps[str(last_dis.date())] = gaps.get(str(last_dis.date()), 0) + (t - last_dis).total_seconds()
        last_dis = None
print(f"[C4 INFO] disconnect gap seconds per day: {gaps}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
