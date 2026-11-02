"""Independent verifier of the root-cause study (logs/research_root_cause/ROOT_CAUSE_PROTOCOL_PREREGISTERED.md).
Plain loops on the raw csv rows (numpy only for the same seeded coin flips). Q1 manifest SHAs  Q2 R2 random entries, 1h and 4h,
CORE10 pooled: end-exit and TP/SL (m = 2, conservative) for every cost and period  Q3 R3 E|r| and the MOM hit rate (1h, 4h)
Q4 R5 Spearman values  Q5 R7 ECO share of positive days"""
import csv
import gzip
import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "research_root_cause"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


rep = json.loads((OUT / "ROOT_CAUSE_RESULTS.json").read_text(encoding="utf-8"))
man = list(csv.DictReader(open(OUT / "input_manifest.csv", encoding="utf-8")))
bad = [m["path"] for m in man if hashlib.sha256((R_ / m["path"]).read_bytes()).hexdigest() != m["sha256"]]
ok("Q1", not bad and hashlib.sha256((OUT / "input_manifest.csv").read_bytes()).hexdigest() == rep["manifest_sha256"], f"{len(man)} inputs, mismatches {bad}")
CORE10 = json.loads((R_ / "deploy" / "paper_n1_config.json").read_text())["core10"]
COST = {"C1_fut_maker": 0.0004, "C2_fut_taker": 0.0008, "C3_spot_bnb": 0.0017}
T0, TEND, B0 = datetime(2020, 1, 1), datetime(2026, 9, 30, 23, 55), datetime(2025, 10, 1)
NG = int((TEND - T0).total_seconds() // 300) + 1
acc = {}
for coin in CORE10:
    bars = {}
    with gzip.open(R_ / "data" / "universe_hf" / "5m" / f"{coin}_5m_full.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            t = datetime.fromisoformat(r["timestamp"][:19])
            i = int((t - T0).total_seconds() // 300)
            if 0 <= i < NG and i not in bars:
                bars[i] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
    for hn, h in (("1h", 12), ("4h", 48)):
        n = NG // h
        s = np.random.default_rng(2026).choice(np.array([-1.0, 1.0]), size=n)
        prev_r = None
        for b in range(n):
            idx = range(b * h, b * h + h)
            if any(i not in bars for i in idx):
                prev_r = None
                continue
            o = bars[b * h][0]; c = bars[b * h + h - 1][3]
            r = c / o - 1
            P = "B" if T0 + timedelta(minutes=5 * b * h) >= B0 else "A"
            for cn, C in COST.items():
                k = (hn, P, cn)
                a = acc.setdefault(k, dict(n=0, s_end=0.0, w_end=0, s_tp=0.0, w_tp=0, n_mom=0, hit_mom=0, sabs=0.0))
                g = s[b] * r
                a["n"] += 1; a["s_end"] += g - C; a["w_end"] += (g - C) > 0; a["sabs"] += abs(r)
                d = 2 * C
                out = None
                for i in idx:
                    hi, lo = bars[i][1] / o - 1, bars[i][2] / o - 1
                    tp = hi >= d if s[b] > 0 else lo <= -d
                    sl = lo <= -d if s[b] > 0 else hi >= d
                    if sl:
                        out = -d; break
                    if tp:
                        out = d; break
                if out is None:
                    out = g
                a["s_tp"] += out - C; a["w_tp"] += (out - C) > 0
                if prev_r is not None and prev_r != 0:
                    a["n_mom"] += 1; a["hit_mom"] += ((1 if prev_r > 0 else -1) * r) > 0
            prev_r = r
    print("read", coin, flush=True)
R2 = rep["R2"]; R3 = rep["R3"]
bad2, bad3 = [], []
for (hn, P, cn), a in acc.items():
    e = [x for x in R2 if x["h"] == hn and x["period"] == P and x["cost"] == cn and x["exit"] == "end"][0]
    t = [x for x in R2 if x["h"] == hn and x["period"] == P and x["cost"] == cn and x["exit"] == "tp_sl_cons" and x["m"] == 2][0]
    if e["n"] != a["n"] or abs(e["mean_net"] - a["s_end"] / a["n"]) > 1e-9 or abs(e["win"] - a["w_end"] / a["n"]) > 1e-12 \
            or abs(t["mean_net"] - a["s_tp"] / a["n"]) > 1e-9 or abs(t["win"] - a["w_tp"] / a["n"]) > 1e-12:
        bad2.append((hn, P, cn, e["n"], a["n"], e["mean_net"], a["s_end"] / a["n"], t["mean_net"], a["s_tp"] / a["n"]))
    m = [x for x in R3 if x["h"] == hn and x["period"] == P and x["cost"] == cn and x["rule"] == "MOM"][0]
    if abs(m["E_abs_r"] - a["sabs"] / a["n"]) > 1e-12 or m["n"] != a["n_mom"] or abs(m["hit"] - a["hit_mom"] / a["n_mom"]) > 1e-12:
        bad3.append((hn, P, cn, m["n"], a["n_mom"], m["hit"], a["hit_mom"] / max(1, a["n_mom"])))
ok("Q2", not bad2, f"R2 1h/4h x A/B x 3 costs: end-exit and TP/SL (m=2, SL first) mean net and win rate by loops: mismatches {bad2[:2]}")
ok("Q3", not bad3, f"R3 1h/4h: E|r| and MOM hit rate by loops: mismatches {bad3[:2]}")
rows = list(csv.DictReader(open(OUT / "R5_months.csv", encoding="utf-8")))


def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spear(x, y):
    a, b = rank(x), rank(y); ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    return cov / (sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b)) ** 0.5


eco = [float(r["eco"]) for r in rows]
s1, s2 = spear(eco, [float(r["btc_abs"]) for r in rows]), spear(eco, [float(r["btc_er"]) for r in rows])
ok("Q4", abs(s1 - rep["R5"]["spearman_eco_vs_btc_abs"]) < 1e-9 and abs(s2 - rep["R5"]["spearman_eco_vs_btc_er"]) < 1e-9,
   f"R5 Spearman ECO month vs |BTC month| {s1:.4f}, vs BTC efficiency ratio {s2:.4f}")
import pandas as pd                                                       # parquet reading only
E = pd.read_parquet(R_ / "data" / "derived" / "eco" / "e2_daily_series.parquet")
bad5 = []
for w in ("dev", "P3"):
    v = [x for x in E[f"{w}|ECO-W2"].tolist() if x == x]
    d = [v[i] / v[i - 1] - 1 for i in range(1, len(v))]
    sp = sum(1 for x in d if x > 0) / len(d)
    if abs(sp - rep["R7"][f"eco_{w}"]["share_pos"]) > 1e-12:
        bad5.append((w, sp))
ok("Q5", not bad5, f"R7 ECO share of positive days dev {rep['R7']['eco_dev']['share_pos']:.4f}, P3 {rep['R7']['eco_P3']['share_pos']:.4f}: mismatches {bad5}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
