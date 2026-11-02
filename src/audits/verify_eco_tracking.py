"""Independent verifier of the ECO tracking check (src/eco/eco_tracking.py; amendment 1 §5). No code shared: plain loops on the raw
ledger lines. Usage: python verify_eco_tracking.py [demo_root] [shadow_root]
K1 ledger SHAs in the report == files on disk   K2 diff / d_day / d_cum per finished UTC day within 1e-6, day_ok flags equal
K3 fills, notional-weighted slippage (bps), rejected, band skips per day equal   K4 gate (only once 14 full days exist) equal"""
import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
demo = R_ / (sys.argv[1] if len(sys.argv) > 1 else "data/eco_demo")
shadow = R_ / (sys.argv[2] if len(sys.argv) > 2 else "data/eco_shadow")
OUT = R_ / "logs" / "eco" / "tracking"
E0 = 10_000.0
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def lines(root):
    out = []
    with open(root / "ledger.jsonl", encoding="utf-8") as f:
        for l in f:
            if l.strip():
                r = json.loads(l)
                if r.get("mode") != "reset":
                    out.append(r)
    return out


rep = json.loads((OUT / "tc_report.json").read_text(encoding="utf-8"))
rows = list(csv.DictReader(open(OUT / "tc_daily.csv", encoding="utf-8")))
ok("K1", rep["demo_ledger_sha256"] == hashlib.sha256((demo / "ledger.jsonl").read_bytes()).hexdigest()
   and rep["shadow_ledger_sha256"] == hashlib.sha256((shadow / "ledger.jsonl").read_bytes()).hexdigest(),
   "report ledger SHAs == ledgers on disk (the report was made from these exact ledgers)")
D, S = lines(demo), lines(shadow)
cut = date.fromisoformat(D[0]["T"][:10])
now_day = date.fromisoformat(rep["now"][:10])
ld, ls = {}, {}
for r in D:
    if r.get("ok") and r.get("eco_equity") is not None:
        ld[date.fromisoformat(r["T"][:10])] = float(r["eco_equity"])
for r in S:
    if r.get("ok") and r.get("eco_equity") is not None:
        ls[date.fromisoformat(r["T"][:10])] = float(r["eco_equity"])
exp, prev = [], 0.0
for d in sorted(set(ld) | set(ls)):
    if d >= now_day:
        continue
    if d in ld and d in ls:
        diff = ld[d] - ls[d]
        exp.append((str(d), diff, diff - prev, d > cut, abs(diff - prev) <= 0.003 * E0)); prev = diff
    else:
        exp.append((str(d), None, None, d > cut, None))
bad = []
if len(exp) != len(rows):
    bad.append(("n_rows", len(exp), len(rows)))
for (d, diff, dd, full, dok), r in zip(exp, rows):
    if r["date"] != d or (r["full_day"] == "True") != full:
        bad.append((d, "date/full")); continue
    if diff is None:
        if r["diff"] != "":
            bad.append((d, "diff should be empty"))
        continue
    if abs(float(r["diff"]) - diff) > 1e-6 or abs(float(r["d_day"]) - dd) > 1e-6 or abs(float(r["d_cum"]) - diff) > 1e-6 or (r["day_ok"] == "True") != dok:
        bad.append((d, diff, dd, r["diff"], r["d_day"], r["day_ok"]))
ok("K2", not bad, f"{len(exp)} finished UTC days recomputed (diff, d_day, d_cum, day_ok): mismatches {bad[:3]}")
st = {}
for r in D:
    if not r.get("ok"):
        continue
    d = r["T"][:10]
    s = st.setdefault(d, [0, 0.0, 0.0, 0, 0])
    for o in r.get("orders", []):
        m = r["price"].get(o["perp"])
        if m:
            n = abs(o["qty"]) * m
            sign = 1.0 if o["qty"] > 0 else -1.0
            s[0] += 1; s[1] += n; s[2] += n * sign * (o["px"] / m - 1) * 10000
    for n_ in r.get("notes") or []:
        if n_.startswith("order ") and " failed: " in n_ and "unconfirmed" not in n_:
            s[3] += 1
    for x in r.get("skipped", []):
        if "inside band" in str(x[1]):
            s[4] += 1
bad3 = []
for r in rows:
    s = st.get(r["date"], [0, 0.0, 0.0, 0, 0])
    slip = s[2] / s[1] if s[1] else None
    rs = None if r["slip_bps"] == "" else float(r["slip_bps"])
    if int(r["fills"]) != s[0] or int(r["rejected"]) != s[3] or int(r["band_skips"]) != s[4] or \
            ((slip is None) != (rs is None)) or (slip is not None and abs(slip - rs) > 1e-6):
        bad3.append((r["date"], s, r["fills"], r["slip_bps"], r["rejected"], r["band_skips"]))
ok("K3", not bad3, f"execution stats per day (fills, slippage bps, rejected, band skips) recomputed: mismatches {bad3[:2]}")
full = [e for e in exp if e[3]][:14]
if len(full) == 14:
    n_ok = sum(1 for e in full if e[4])
    passed = n_ok >= 12 and full[-1][1] is not None and abs(full[-1][1]) <= 0.01 * E0
    g = rep["gate"]
    ok("K4", g is not None and g["n_day_ok"] == n_ok and g["passed"] == passed, f"gate recomputed: {n_ok}/14 days ok, d_cum {full[-1][1]}, passed {passed}")
else:
    ok("K4", rep["gate"] is None, f"{len(full)} full days < 14: no gate yet (report gate = {rep['gate']})")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
