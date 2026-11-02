"""Independent verifier of the 1D true-fee re-run (logs/research_1d_true_fee/TRUE_FEE_1D_PROTOCOL_PREREGISTERED.md).
csv loops, no pandas. V1 R0 equity == the locked F7 equity (every cell, 1e-6)  V2 stats of R0/R1 RS and LO (final, CAGR, max DD,
year returns, P3) recomputed from the saved files  V3 output file SHAs"""
import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "research_1d_true_fee"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def load(p):
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    return [(date.fromisoformat(r["date"][:10]), {k: float(v) for k, v in r.items() if k != "date" and v != ""}) for r in rows]


rep = json.loads((OUT / "TRUE_FEE_1D_RESULTS.json").read_text(encoding="utf-8"))
a, b = load(R_ / "logs" / "strategy_f7_risk" / "equity_MAIN_AI_RS.csv"), load(OUT / "equity_MAIN_AI_R0_RS.csv")
mx = max(abs(x[1][k] - y[1][k]) for x, y in zip(a, b) for k in x[1])
ok("V1", len(a) == len(b) and all(x[0] == y[0] for x, y in zip(a, b)) and mx < 1e-6, f"R0 == locked F7 RS equity: {len(a)} days, max |diff| {mx:.2e}")
bad = []
for nm in ("R0_RS", "R1_RS", "R0_LO", "R1_LO"):
    rows = load(OUT / f"equity_MAIN_AI_{nm}.csv")
    for c in ("M_AI3", "D1", "H4", "H1"):
        s = [(d, v[c]) for d, v in rows if c in v]
        yrs = (s[-1][0] - s[0][0]).days / 365.25
        cagr = (s[-1][1] / 10_000.0) ** (1 / yrs) - 1
        pk, dd = s[0][1], 0.0
        for _, v in s:
            pk = max(pk, v); dd = min(dd, v / pk - 1)
        ye, prev = {}, 10_000.0
        for d, v in s:
            ye[d.year] = v
        yr = {}
        for y in sorted(ye):
            yr[str(y)] = ye[y] / prev - 1; prev = ye[y]
        p3 = [v for d, v in s if d >= date(2025, 9, 30)]
        R = rep[nm][c]
        if abs(R["final"] - s[-1][1]) > 1e-9 or abs(R["cagr"] - cagr) > 1e-12 or abs(R["maxdd"] - dd) > 1e-12 or abs(R["p3_2025_10_on"] - (p3[-1] / p3[0] - 1)) > 1e-12 \
                or any(abs(R["years"][k] - yr[k]) > 1e-12 for k in yr):
            bad.append((nm, c))
ok("V2", not bad, f"stats of 4 runs x 4 series recomputed by loops (final, CAGR, max DD, years, P3): mismatches {bad}")
shas = [rep[nm]["file_sha256"] == hashlib.sha256((OUT / f"equity_MAIN_AI_{nm}.csv").read_bytes()).hexdigest() for nm in ("R0_RS", "R1_RS", "R0_LO", "R1_LO")]
ok("V3", all(shas) and hashlib.sha256((OUT / "TRUE_FEE_1D_RESULTS.json").read_bytes()).hexdigest() == (OUT / "RESULTS_SHA256.txt").read_text().split()[0],
   "equity files and results SHAs")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
