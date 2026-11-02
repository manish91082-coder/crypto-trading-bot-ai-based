"""Daily check of the EMO meter ledger (protocol logs/emotion/EMO_METER_PROTOCOL_PREREGISTERED.md §3).
Usage: python verify_emotion_live.py [root=data/emotion]
M1 chain  M2 hourly cadence (gaps > 90 min; FAIL in the last 24 h)  M3 crowding recomputed from recorded features == recorded
M4 no record with > 20 % symbols in error in the last 24 h  M5 protocol SHA constant == file"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "eco"))
import emotion_meter as M

root = Path(sys.argv[1]) if len(sys.argv) > 1 else R_ / "data" / "emotion"
root = root if root.is_absolute() else R_ / root
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


L = [json.loads(l) for l in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
prev, chain = "GENESIS", True
for r in L:
    body = {k: v for k, v in r.items() if k != "line_sha256"}
    chain &= r["prev_sha256"] == prev and hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == r["line_sha256"]
    prev = r["line_sha256"]
ok("M1", chain, f"{len(L)} records, hash chain intact")
T = pd.to_datetime([r["T"] for r in L])
gaps = [(str(a), str(b)) for a, b in zip(T[:-1], T[1:]) if b - a > pd.Timedelta(minutes=90)]
g24 = [g for g in gaps if pd.Timestamp(g[1]) >= T[-1] - pd.Timedelta(hours=24)]
ok("M2", not g24, f"hourly cadence; gaps > 90 min: {gaps[-5:]}")
bad = []
for r in L:
    sc, temp = M.scores(r["features"])
    if set(sc) != set(r["crowding"]) or any(abs(sc[s] - r["crowding"][s]) > 1e-12 for s in sc) \
            or any(abs(temp[k] - r["temperature"][k]) > 1e-12 for k in temp):
        bad.append(r["T"])
ok("M3", not bad, f"crowding scores and temperature recomputed from the recorded features: mismatches {bad[:3]}")
last24 = [r for r, t in zip(L, T) if t >= T[-1] - pd.Timedelta(hours=24)]
hi_err = [(r["T"], r["n_symbols"] - r["n_ok"]) for r in last24 if r["n_symbols"] and (r["n_symbols"] - r["n_ok"]) / r["n_symbols"] > 0.20]
ok("M4", not hi_err, f"records with > 20% symbols in error (last 24 h): {hi_err[:3]}")
psha = hashlib.sha256(M.PROTO.read_bytes()).hexdigest()
ok("M5", {r["protocol_sha256"] for r in L if "protocol_sha256" in r} == {psha}, f"protocol {psha[:12]} constant")
last = L[-1]
print(f"[INFO] {last['T']}: {last['n_ok']}/{last['n_symbols']} symbols; temperature {last['temperature']}; most crowded long {last['most_crowded_long']}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
