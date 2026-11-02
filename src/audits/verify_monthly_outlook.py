"""Independent verifier of the ECO monthly outlook (logs/eco/monthly_outlook/MONTHLY_OUTLOOK_PROTOCOL_PREREGISTERED.md).
Plain loops on the parquet rows (pandas only to read the file). O1 SHAs  O2 monthly returns  O3 percentiles (numpy linear vs own
linear interpolation)  O4 rolling 30-day min / max  O5 max DD vs the E-2 claims (dev)  O6 live numbers from the ledger snapshot"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "eco" / "monthly_outlook"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def h(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pct(xs, q):                                                  # linear interpolation between closest ranks (numpy default)
    s = sorted(xs)
    pos = (len(s) - 1) * q / 100.0
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


rep = json.loads((OUT / "MONTHLY_OUTLOOK_RESULTS.json").read_text(encoding="utf-8"))
par = R_ / "data" / "derived" / "eco" / "e2_daily_series.parquet"
ok("O1", h(par) == rep["parquet_sha256"] and h(OUT / "RESULTS_SHA256.txt".replace("RESULTS_SHA256.txt", "MONTHLY_OUTLOOK_RESULTS.json")) ==
   (OUT / "RESULTS_SHA256.txt").read_text().split()[0] and h(OUT / "live" / "eco_plan_ledger_snapshot.jsonl") == rep["live_snapshot_sha256"],
   "parquet, results and live snapshot SHAs")
E = pd.read_parquet(par)
for w in ("P3", "dev"):
    col = E[f"{w}|ECO-W2"]
    rows = [(t.year, t.month, float(v)) for t, v in col.items() if v == v]
    last_of = {}
    for y, m, v in rows:
        last_of[(y, m)] = v
    keys = sorted(last_of)
    prev = rows[0][2]
    mr = []
    for k in keys:
        mr.append(last_of[k] / prev - 1); prev = last_of[k]
    got = rep[w]["month_list"]
    same = len(mr) == len(got) and all(abs(a - b) < 1e-12 for a, b in zip(mr, got.values()))
    ok("O2", same, f"{w}: {len(mr)} calendar-month returns recomputed by a loop; worst {min(mr):.6f} best {max(mr):.6f}")
    M = rep[w]["months"]
    qs = {f"p{q}": pct(mr, q) for q in (10, 25, 50, 75, 90)}
    ok("O3", all(abs(qs[k] - M[k]) < 1e-12 for k in qs) and abs(sum(mr) / len(mr) - M["mean"]) < 1e-12
       and abs(min(mr) - M["worst"]) < 1e-15 and abs(max(mr) - M["best"]) < 1e-15,
       f"{w}: percentiles / mean / worst / best by own interpolation: p50 {qs['p50']:.6f} (report {M['p50']:.6f})")
    v = [x for _, _, x in rows]
    r30 = [v[i + 30] / v[i - 1] - 1 for i in range(1, len(v) - 30)]
    peak, mdd = v[0], 0.0
    for x in v:
        peak = max(peak, x); mdd = min(mdd, x / peak - 1)
    ok("O4", abs(min(r30) - rep[w]["rolling30"]["worst"]) < 1e-12 and abs(max(r30) - rep[w]["rolling30"]["best"]) < 1e-12 and len(r30) == rep[w]["rolling30"]["n"]
       and abs(mdd - rep[w]["max_dd"]) < 1e-12, f"{w}: rolling 30-day n {len(r30)} worst {min(r30):.6f} best {max(r30):.6f}; max DD {mdd:.6f}")
cl = json.loads((R_ / "logs" / "eco" / "claims_eco_e2.json").read_text())
ok("O5", abs(-cl["results"]["dev|ECO-W2"]["mtm_dd"] - rep["dev"]["max_dd"]) < 1e-9,
   f"dev max DD {rep['dev']['max_dd']:.6f} == E-2 claims MTM-DD {cl['results']['dev|ECO-W2']['mtm_dd']:.6f} (independent source)")
L = [json.loads(l) for l in (OUT / "live" / "eco_plan_ledger_snapshot.jsonl").read_text().splitlines() if l.strip()]
eq = [r["eco_equity"] for r in L if r.get("ok") and r.get("eco_equity") is not None and r.get("mode") != "reset"]
lp = rep["live_plan"]
ok("O6", len(eq) == lp["n_ok"] and eq[-1] == lp["last"] and min(eq) == lp["min"] and max(eq) == lp["max"],
   f"live plan: {len(eq)} ok cycles, last {eq[-1]:.2f}, min {min(eq):.2f}, max {max(eq):.2f}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
