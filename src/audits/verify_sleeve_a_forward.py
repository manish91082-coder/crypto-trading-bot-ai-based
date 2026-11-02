"""Independent verifier of the sleeve A forward investigation (logs/paper_n1/SLEEVE_A_FORWARD_PROTOCOL_PREREGISTERED.md).
Plain loops (csv / json), no code shared with sleeve_a_forward.py. Usage: python verify_sleeve_a_forward.py [ledger]
Per evaluated window: Q1 live n / wins / mean r from the ledger lines; Q2 spot file SHA, M_live, the comparable set (100 nearest
eligible backtest windows), p_wr, p_ret, verdict (with the fidelity rc); Q3 the summary verdict from the window files."""
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "paper_n1" / "sleeve_a_forward"
ledger = R_ / (sys.argv[1] if len(sys.argv) > 1 else "data/paper_n1/ledger.jsonl")
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def h(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


rows = []
with open(R_ / "logs" / "paper_n1" / "sleeve_a_check" / "all_windows.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["M"] != "" and int(r["n"]) >= 20:
            rows.append((datetime.fromisoformat(r["start"]), float(r["win_rate"]), float(r["mean_r"]), float(r["M"])))
recs = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
files = sorted(OUT.glob("F*.json"), key=lambda p: int(p.stem[1:]))
for fp in files:
    d = json.loads(fp.read_text(encoding="utf-8"))
    t0, t1 = datetime.fromisoformat(d["start"]), datetime.fromisoformat(d["end"])
    rs = []
    for r in recs:
        T = datetime.fromisoformat(r["T"])
        if t0 < T <= t1:
            for a in r["actions"]:
                if a["k"][:2] == "A|" and a["a"] == "close":
                    rs.append(a["px"] / a["entry"] - 1)
    wins = sum(1 for x in rs if x > 0)
    ok("Q1", len(rs) == d["n"] and wins == d["wins"] and (len(rs) < 20) == (not d["eligible"]),
       f"{d['window']}: live closes {len(rs)}, wins {wins} (file {d['n']}, {d['wins']}), eligible {d['eligible']}")
    if not d["eligible"]:
        ok("Q2", d["verdict"] == "too few trades", f"{d['window']}: < 20 closes -> 'too few trades' ({d['verdict']})")
        continue
    wr, mr = wins / len(rs), sum(rs) / len(rs)
    sp = OUT / f"spot_{d['window']}.json"
    data = json.loads(sp.read_text())["data"]
    M = sum(data[c][str(t1).replace("T", " ")] / data[c][str(t0).replace("T", " ")] - 1 for c in data) / len(data)
    near = sorted(((abs(x[3] - M), x[0], x[1], x[2]) for x in rows), key=lambda z: (z[0], z[1]))
    m = max(30, math.ceil(0.2 * len(rows)))
    comp = near[:m]
    p_wr = sum(1 for z in comp if z[2] <= wr) / m
    p_ret = sum(1 for z in comp if z[3] <= mr) / m
    v = "records suspect" if d["fidelity_rc"] != 0 else ("consistent" if p_wr >= 0.05 and p_ret >= 0.05 else "not consistent")
    ok("Q2", h(sp) == d["spot_sha256"] and abs(M - d["M_live"]) < 1e-12 and abs(wr - d["win_rate"]) < 1e-12 and abs(mr - d["mean_r"]) < 1e-12
       and m == d["n_comparable"] and abs(p_wr - d["p_wr"]) < 1e-12 and abs(p_ret - d["p_ret"]) < 1e-12 and v == d["verdict"],
       f"{d['window']}: M {M:.6f} win rate {wr:.4f} mean r {mr:.5f} comparable {m} p_wr {p_wr:.3f} p_ret {p_ret:.3f} -> {v} (file {d['verdict']})")
S = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
done = [json.loads(p.read_text(encoding="utf-8")) for p in files]
el = [d for d in done if d["eligible"]][:3]
if len(el) == 3:
    exp = "confirmed inconsistent" if (sum(d["verdict"] != "consistent" for d in el) >= 2 or any(d["verdict"] == "records suspect" for d in el)) \
        else "W1 was an extreme draw"
else:
    exp = "insufficient" if len(done) == 6 else "pending"
ok("Q3", S["verdict"] == exp and all(S["files"][d["window"]] == h(OUT / f"{d['window']}.json") for d in done),
   f"summary verdict {S['verdict']} == recomputed {exp}; window file SHAs match")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
