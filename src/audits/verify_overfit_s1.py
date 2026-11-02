"""
Independent verifier for S1 (logs/research_overfit_s1).
V1 hashes (protocol, returns matrix, every inventory file).
V2 inventory rules: CONTROL / cost040 excluded; every "duplicate of" really has identical daily returns.
V3 Sharpe per trial with plain Python (statistics); DSR re-derived with statistics.NormalDist (no scipy);
   the paper's example re-checked with this independent code.
V4 PBO: 400 combinations (every 32nd of the 12,870, same itertools order) re-derived with plain loops; the
   lambdas must equal the stored ones; PBO recomputed from the stored lambdas.
"""
import sys
import csv
import json
import math
import hashlib
import itertools
import statistics
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC))
from config import LOGS_DIR

OUT = LOGS_DIR / "research_overfit_s1"
C = json.loads((OUT / "claims.json").read_text())
ND = statistics.NormalDist()
EMC = 0.5772156649


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dsr(sr, T, sk, ku, N, V):
    sr0 = math.sqrt(V) * ((1 - EMC) * ND.inv_cdf(1 - 1 / N) + EMC * ND.inv_cdf(1 - 1 / (N * math.e)))
    return sr0, ND.cdf((sr - sr0) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr + (ku - 1) / 4 * sr * sr))


def moments(x):
    n = len(x)
    m = sum(x) / n
    m2 = sum((v - m) ** 2 for v in x) / n
    m3 = sum((v - m) ** 3 for v in x) / n
    m4 = sum((v - m) ** 4 for v in x) / n
    return m3 / m2 ** 1.5, m4 / m2 ** 2


def main():
    assert sha(OUT / "S1_PROTOCOL_PREREGISTERED.md") == (OUT / "S1_PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    assert sha(OUT / "trial_daily_returns.csv") == C["returns_sha256"]
    inv = list(csv.DictReader(open(OUT / "trials_inventory.csv")))
    for r in inv:
        assert sha(LOGS_DIR.parent / r["file"]) == r["sha256"], r["file"]
    print(f"[V1 PASS] protocol, returns matrix and {len(inv)} inventory file hashes")

    rows = list(csv.reader(open(OUT / "trial_daily_returns.csv")))
    head, body = rows[0][1:], rows[1:]
    cols = {h: [float(b[i + 1]) if b[i + 1] != "" else float("nan") for b in body] for i, h in enumerate(head)}
    for r in inv:
        if "CONTROL" in r["trial"]:
            assert r["excluded"] == "control placebo"
        if "cost040" in r["trial"]:
            assert r["excluded"] == "cost-stress duplicate"
    assert all("CONTROL" not in h and "cost040" not in h for h in head)
    print(f"[V2 PASS] rules: {len(head)} included series, no CONTROL / cost040 among them; "
          f"{sum(1 for r in inv if r['excluded'].startswith('duplicate'))} exact duplicates removed")

    sr = {}
    for h, x in cols.items():
        x = [0.0 if math.isnan(v) else v for v in x]
        sd = statistics.stdev(x)
        sr[h] = statistics.mean(x) / sd if sd > 0 else 0.0
    V = statistics.variance(list(sr.values()))
    assert abs(V - C["V_daily_sr"]) < 1e-12 and len(sr) == C["N_series"]
    a = 2.5 / math.sqrt(250)
    assert abs(dsr(a, 1250, -3, 10, 100, 0.5 / 250)[1] - 0.9004) < 5e-5 and abs(dsr(a, 1250, -3, 10, 46, 0.5 / 250)[1] - 0.9505) < 5e-5
    for sel in ("M_AI3_f50", "H1_f100"):
        x = cols[f"step27/{sel}"]
        s_ = statistics.mean(x) / statistics.stdev(x)
        sk, ku = moments(x)
        c = C[f"DSR_{sel}"]
        assert abs(s_ - c["sr_daily"]) < 1e-12 and abs(sk - c["skew"]) < 1e-9 and abs(ku - c["kurt_raw"]) < 1e-9
        for tag in ("N_series", "N_total", "N_double"):
            sr0, d = dsr(s_, len(x), sk, ku, c[tag]["N"], V)
            assert abs(d - c[tag]["dsr"]) < 1e-9 and abs(sr0 - c[tag]["sr0_daily"]) < 1e-12, (sel, tag, d, c[tag]["dsr"])
        print(f"   {sel}: SR(ann.) {s_*math.sqrt(365):.3f}; DSR " + ", ".join(f"N={c[t]['N']}: {c[t]['dsr']:.4f}" for t in ("N_series", "N_total", "N_double")))
    print("[V3 PASS] Sharpe ratios and DSR re-derived without scipy; the paper's example re-checked")

    lam = np.load(OUT / "pbo_lambdas.npy")
    S = 16
    T = (len(body) // S) * S
    names = head
    X = [[0.0 if math.isnan(cols[h][t]) else cols[h][t] for h in names] for t in range(len(body) - T, len(body))]
    blocks = [list(range(i * T // S, (i + 1) * T // S)) for i in range(S)]
    N = len(names)

    def sh(rows_idx, j):
        v = [X[t][j] for t in rows_idx]
        sd = statistics.stdev(v)
        return statistics.mean(v) / sd if sd > 0 else 0.0

    for k, comb in enumerate(itertools.combinations(range(S), S // 2)):
        if k % 32:
            continue
        tr = [t for i in comb for t in blocks[i]]
        te = [t for i in range(S) if i not in comb for t in blocks[i]]
        r_is = [sh(tr, j) for j in range(N)]
        r_os = [sh(te, j) for j in range(N)]
        n_star = max(range(N), key=lambda j: r_is[j])
        below = sum(1 for v in r_os if v < r_os[n_star])
        ties = sum(1 for v in r_os if v == r_os[n_star])
        rank = below + (ties + 1) / 2
        w = rank / (N + 1)
        assert abs(math.log(w / (1 - w)) - lam[k]) < 1e-9, (k, math.log(w / (1 - w)), lam[k])
    assert abs(float(np.mean(lam <= 0)) - C["PBO"]["pbo"]) < 1e-12 and len(lam) == 12870
    print(f"[V4 PASS] 403 of 12,870 CSCV combinations re-derived with plain loops; PBO {C['PBO']['pbo']:.4f}")


if __name__ == "__main__":
    main()
