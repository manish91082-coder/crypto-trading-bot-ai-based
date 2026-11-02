"""Append an N-series RESULT line to logs/r2_4h_a0/trial_registry.csv (hash-chained). Usage: python registry_append_result.py T15 N1"""
import base64, datetime, hashlib, json, sys
from pathlib import Path
R_ = Path(__file__).resolve().parents[2]
D = {"N1": ("research_n1_portfolio", "claims_n1.json", "N1_PROTOCOL_PREREGISTERED.md"), "N2": ("research_n2_regime", "claims_n2.json", "N2_PROTOCOL_PREREGISTERED.md"),
     "N3": ("research_n3_execution", "claims_n3.json", "N3_PROTOCOL_PREREGISTERED.md"), "N5": ("research_n5_ai", "claims_n5.json", "N5_PROTOCOL_PREREGISTERED.md"),
     "N6S": ("research_n6_safety_sizing", "claims_n6.json", "N6_PROTOCOL_PREREGISTERED.md"), "N6A": ("research_n6_safety_sizing", "claims_n6.json", "N6_PROTOCOL_PREREGISTERED.md")}
tid, step = sys.argv[1], sys.argv[2]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
d, cf, pf = D[step]
cl = json.loads((R_ / "logs" / d / cf).read_text())
reg = R_ / "logs" / "r2_4h_a0" / "trial_registry.csv"
rows = reg.read_text().strip().splitlines()
assert any(l.startswith(f"{tid},") and l.split(",")[2] == step for l in rows), "trial not registered"
assert not any(l.startswith(f"{tid},") and l.split(",")[2] == f"{step}-RESULT" for l in rows), "result already registered"
cfg = json.dumps(dict(verdict=cl["verdict"], gates=cl.get("gates") if step == "N1" else None), sort_keys=True, default=str).encode()
r = [tid, datetime.datetime.now(datetime.timezone.utc).isoformat(), f"{step}-RESULT", "b64:" + base64.b64encode(cfg).decode(), hashlib.sha256(cfg).hexdigest(),
     "", sha(R_ / "logs" / d / pf), "", sha(R_ / "logs" / d / cf), rows[-1].split(",")[-1]]
r.append(hashlib.sha256(",".join(r).encode()).hexdigest())
with open(reg, "a") as fh:
    fh.write(",".join(r) + "\n")
print("appended", tid, step, cl["verdict"])
