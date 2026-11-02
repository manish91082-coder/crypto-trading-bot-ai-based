"""
Independent verifier for Step 28 (logs/strategy_1d_step28_volsize).
V1 protocol + input hashes. V2 mix returns, sigma (statistics.stdev), causal median scale, target weights, band and
equity re-derived with plain Python loops for MAIN and PRE; VOL / FIXED claims recomputed. V3 gates re-derived.
"""
import sys
import json
import csv
import hashlib
import statistics
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC))
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step28_volsize"
S27 = LOGS_DIR / "strategy_1d_step27_combine"
C = json.loads((OUT / "claims.json").read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plain(per):
    rows = list(csv.DictReader(open(S27 / f"sleeves_{per}_f100.csv")))
    m = [(float(r["D1"]) + float(r["H4"]) + float(r["H1"])) / 3 for r in rows]
    dates = [r["date"] for r in rows]
    r = [m[i] / m[i - 1] - 1 for i in range(1, len(m))]
    sig = [None] * len(r)
    for t in range(len(r)):
        if t >= 20:
            sig[t] = statistics.stdev(r[t - 20:t])          # returns t-20..t-1
    known, wt = [], []
    for t in range(len(r)):
        if sig[t] is not None:
            known.append(sig[t])
        if sig[t] is not None and len(known) >= 60:
            k = 0.5 * statistics.median(known)
            wt.append(min(1.0, max(0.0, k / sig[t])))
        else:
            wt.append(0.5)
    E, wp, eq, held = 10000.0, 0.5, [10000.0], []
    for t in range(len(r)):
        w = wt[t] if abs(wt[t] - wp) > 0.10 else wp
        E = E * (1 + w * r[t]) - abs(w - wp) * 0.0025 * E
        eq.append(E)
        held.append(w)
        wp = w
    return dates, eq, held


def st(eq, d0, d1):
    from datetime import date
    days = (date.fromisoformat(d1) - date.fromisoformat(d0)).days
    pk, dd = eq[0], 0.0
    for e in eq:
        pk = max(pk, e)
        dd = max(dd, (pk - e) / pk)
    cagr = (eq[-1] / 10000) ** (365.25 / days) - 1
    return eq[-1], dd * 100, cagr / dd


def main():
    lock = (OUT / "PROTOCOL_SHA256.txt").read_text().split()
    assert sha(OUT / "STEP28_PROTOCOL_PREREGISTERED.md") == lock[0] == C["protocol_sha256"]
    for f, h in C["inputs"].items():
        assert sha(S27 / f) == h
    print("[V1 PASS] protocol and input hashes")
    for per in ("MAIN", "PRE"):
        dates, eq, held = plain(per)
        f, dd, cal = st(eq, dates[0], dates[-1])
        v = C[per]["VOL"]
        assert abs(f - v["final"]) < 0.01 and abs(dd - v["max_dd_pct"]) < 0.01 and abs(cal - v["calmar"]) < 1e-4, (per, f, dd, cal, v)
        assert abs(sum(held) / len(held) - v["w_mean"]) < 1e-4
        for name, w in (("FIXED_050", 0.5), ("FIXED_MEAN", C[per]["FIXED_MEAN"]["w"])):
            rows = list(csv.DictReader(open(S27 / f"sleeves_{per}_f100.csv")))
            m = [(float(x["D1"]) + float(x["H4"]) + float(x["H1"])) / 3 for x in rows]
            E, e2 = 10000.0, [10000.0]
            wexact = sum(held) / len(held) if name == "FIXED_MEAN" else 0.5
            for i in range(1, len(m)):
                E = E * (1 + wexact * (m[i] / m[i - 1] - 1)) - (abs(wexact - 0.5) * 0.0025 * E if i == 1 else 0.0)
                e2.append(E)
            f2, dd2, _ = st(e2, dates[0], dates[-1])
            assert abs(f2 - C[per][name]["final"]) < 0.01 and abs(dd2 - C[per][name]["max_dd_pct"]) < 0.01, (per, name, f2, dd2)
        print(f"[V2 PASS] {per}: VOL final {f:,.2f}, maxDD {dd:.2f} %, Calmar {cal:.4f}; FIXED_050 / FIXED_MEAN re-derived")
    M, P = C["MAIN"], C["PRE"]
    g = dict(MAIN_G1=M["VOL"]["calmar"] > M["FIXED_MEAN"]["calmar"] and M["VOL"]["calmar"] > M["FIXED_050"]["calmar"],
             MAIN_G2=M["VOL"]["max_dd_pct"] < M["FIXED_MEAN"]["max_dd_pct"], MAIN_G3=M["VOL"]["calmar"] > M["SHUFFLED"]["calmar_p95"],
             PRE_G1=P["VOL"]["final"] > P["FIXED_MEAN"]["final"] and P["VOL"]["final"] > P["FIXED_050"]["final"],
             PRE_G2=P["VOL"]["max_dd_pct"] < P["FIXED_MEAN"]["max_dd_pct"], PRE_G3=P["VOL"]["final"] > P["SHUFFLED"]["final_p95"])
    assert all(C["gates"][k] == v for k, v in g.items()) and C["gates"]["decision"] == ("PASS" if all(g.values()) else "FAIL")
    print(f"[V3 PASS] gates re-derived: {C['gates']['decision']}")


if __name__ == "__main__":
    main()
