"""Independent verifier of the BTC entry study (logs/research_btc_entry/BTC_ENTRY_PROTOCOL_PREREGISTERED.md).
Own code: plain loops on the raw csv rows (numpy only to read the cached arrays under test and for seeded draws).
V1 manifest SHAs  V2 500 random (bar, barrier set) outcomes by a bar loop  V3 300 random signal values by loops
V4 every final's holdout trade list replayed (outcome, non-overlap, funding, net, n, mean, halves)  V5 random control of one final"""
import bisect
import csv
import gzip
import hashlib
import json
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "research_btc_entry"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


rep = json.loads((OUT / "BTC_ENTRY_RESULTS.json").read_text(encoding="utf-8"))
man = list(csv.DictReader(open(OUT / "input_manifest.csv", encoding="utf-8")))
bad = [m["path"] for m in man if hashlib.sha256((R_ / m["path"]).read_bytes()).hexdigest() != m["sha256"]]
ok("V1", not bad and hashlib.sha256((OUT / "input_manifest.csv").read_bytes()).hexdigest() == rep["manifest_sha256"], f"{len(man)} inputs; mismatches {bad}")

T0 = datetime(2020, 1, 1)
NG = int((datetime(2026, 9, 30, 23, 55) - T0).total_seconds() // 300) + 1
O, H, L, C, V, TB = ([math.nan] * NG for _ in range(6))
with gzip.open(R_ / "data" / "universe_hf" / "5m" / "BTCUSDT_5m_full.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        i = int((datetime.fromisoformat(r["timestamp"][:19]) - T0).total_seconds() // 300)
        if 0 <= i < NG and math.isnan(O[i]):
            O[i], H[i], L[i], C[i], V[i], TB[i] = (float(r[k]) for k in ("open", "high", "low", "close", "volume", "taker_buy_base"))
CAP = 2016
fees = json.loads((R_ / "deploy" / "fees.json").read_text())["rules"]
FUT = 2 * fees["paper_futures_taker_per_side"]


def outcome(t, sg, a, b):
    e = O[t + 1]
    tp, sl = (e * (1 + a), e * (1 - b)) if sg > 0 else (e * (1 - a), e * (1 + b))
    for j in range(t + 1, min(NG, t + 1 + CAP)):
        o = e if j == t + 1 else O[j]
        if math.isnan(o):
            continue
        if (sg > 0 and o <= sl) or (sg < 0 and o >= sl):
            return sg * (o / e - 1), -1, j
        if (sg > 0 and o >= tp) or (sg < 0 and o <= tp):
            return sg * (o / e - 1), 1, j
        if (sg > 0 and L[j] <= sl) or (sg < 0 and H[j] >= sl):
            return -b, -1, j
        if (sg > 0 and H[j] >= tp) or (sg < 0 and L[j] <= tp):
            return a, 1, j
    last = min(NG - 1, t + CAP)
    k = last
    while math.isnan(C[k]):
        k -= 1
    return sg * (C[k] / e - 1), 0, last


SETS = {"A0.5_0.5": (0.005, 0.005), "A1_1": (0.01, 0.01), "A2_2": (0.02, 0.02), "A4_4": (0.04, 0.04), "A1_0.5": (0.01, 0.005),
        "A2_1": (0.02, 0.01), "A4_2": (0.04, 0.02), "A0.5_1": (0.005, 0.01), "A1_2": (0.01, 0.02)}
random.seed(11)
badv2 = []
cache = {}
for _ in range(500):
    s = random.choice(list(SETS) + ["V1", "V2", "V3"])
    z = cache.get(s) or cache.setdefault(s, np.load(OUT / "cache" / f"out_{s}.npz"))
    t = random.randrange(300, NG - 3000)
    if math.isnan(O[t + 1]):
        continue
    a, b = (float(z["a"][t]), float(z["b"][t]))
    if not (math.isfinite(a) and math.isfinite(b)):
        continue
    for sg, side in ((1, "long"), (-1, "short")):
        r, w, x = outcome(t, sg, a, b)
        if abs(r - float(z[f"ret_{side}"][t])) > 1e-12 or w != int(z[f"why_{side}"][t]) or x != int(z[f"exit_{side}"][t]):
            badv2.append((s, t, side, r, float(z[f"ret_{side}"][t])))
ok("V2", not badv2, f"500 random (bar, set) long+short outcomes by a bar loop: mismatches {len(badv2)} {badv2[:2]}")
# vol-scaled barrier value itself
bad_s = []
for _ in range(100):
    t = random.randrange(400, NG - 10)
    lr = [math.log(C[i] / C[i - 1]) for i in range(t - 287, t + 1) if not (math.isnan(C[i]) or math.isnan(C[i - 1]))]
    if len(lr) < 280:
        continue
    m = sum(lr) / len(lr); sd = math.sqrt(sum((x - m) ** 2 for x in lr) / (len(lr) - 1)) * math.sqrt(288)
    if abs(sd - float(cache.get("V1", np.load(OUT / "cache" / "out_V1.npz"))["a"][t])) > 1e-9 * sd:
        bad_s.append(t)
ok("V2b", not bad_s, f"sigma24 (V1 barrier) at 100 random bars recomputed: mismatches {bad_s[:3]}")
# V3 signals: recompute a few rule families by loops and compare with the study's own signal function
sys.path.insert(0, str(R_ / "src" / "research"))
import btc_entry_study as B                                               # signals under test
import pandas as pd
d = B.load(); F = B.features(d); S = B.signals(F, d)
badv3 = []
for _ in range(300):
    t = random.randrange(30 * 288 * 4, NG - 10)
    kind = random.choice(["mom", "brk", "z", "flow"])
    if kind == "mom":
        L_ = 288; r = C[t] / C[t - L_] - 1
        rs = [C[i] / C[i - L_] - 1 for i in range(t - 90 * 288 + 1, t + 1) if not (math.isnan(C[i]) or math.isnan(C[i - L_]))]
        if len(rs) < 90 * 144 or math.isnan(r):
            continue
        m = sum(rs) / len(rs); sd = math.sqrt(sum((x - m) ** 2 for x in rs) / (len(rs) - 1))
        exp = (1 if r > 0 else -1) if abs(r) > 1 * sd else 0
        got = int(S["F2_mom_24h_k1"][t])
    elif kind == "brk":
        hh = max(H[t - 288:t]); ll = min(L[t - 288:t])
        if any(math.isnan(x) for x in H[t - 288:t] + L[t - 288:t]) or math.isnan(C[t]):
            continue
        exp = 1 if C[t] > hh else (-1 if C[t] < ll else 0)
        got = int(S["F4_brk_follow_288"][t])
    elif kind == "z":
        w = C[t - 287:t + 1]
        if any(math.isnan(x) for x in w):
            continue
        m = sum(w) / 288; sd = math.sqrt(sum((x - m) ** 2 for x in w) / 287); z = (C[t] - m) / sd
        exp = 1 if z <= -2 else (-1 if z >= 2 else 0)
        got = int(S["F5_z_fade_288_k2"][t])
    else:
        w = range(t - 47, t + 1)
        if any(math.isnan(TB[i]) or math.isnan(V[i]) for i in w):
            continue
        tbr = sum(TB[i] for i in w) / sum(V[i] for i in w)
        exp_tbr = float(F["tbr_4h"].iloc[t])
        exp, got = round(tbr, 10), round(exp_tbr, 10)
    if exp != got:
        badv3.append((kind, t, exp, got))
ok("V3", not badv3, f"300 random signal values (24h momentum k1, 288-bar breakout, 288-bar z fade, 4h taker-buy ratio) by loops: mismatches {badv3[:3]}")
# V4 finals' holdout trades
fund = []
with open(R_ / "data" / "futures_um" / "BTCUSDT_funding.csv", newline="") as f:
    for r in csv.DictReader(f):
        fund.append((datetime.fromisoformat(r["time"][:19]), float(r["funding_rate"])))
fund.sort()
seen = set(); fund = [x for x in fund if not (x[0] in seen or seen.add(x[0]))]
ft = [x[0] for x in fund]; fc = [0.0]
for _, v in fund:
    fc.append(fc[-1] + v)


def cumf(i):                                                            # events strictly before the close of bar i
    return fc[bisect.bisect_left(ft, T0 + timedelta(minutes=5 * (i + 1)))]


bad4 = []
for fin in rep["finals"]:
    if not fin.get("H_n"):
        continue
    p = OUT / f"H_trades_{fin['cfg']}_{fin['set']}.csv"
    rows = list(csv.DictReader(open(p)))
    nets, free, y26 = [], 0, []
    zz = np.load(OUT / "cache" / f"out_{fin['set']}.npz")
    for r in rows:
        t, sg, x = int(r["t"]), int(r["dir"]), int(r["exit"])
        a, b = float(zz["a"][t]), float(zz["b"][t])
        g, w, xx = outcome(t, sg, a, b)
        f_ = (cumf(x) - cumf(t)) * sg
        net = g - FUT - f_
        if t < free or abs(g - float(r["gross"])) > 1e-12 or xx != x or abs(net - float(r["net"])) > 1e-12:
            bad4.append((fin["cfg"], t)); break
        free = x
        nets.append(net); y26.append(T0 + timedelta(minutes=5 * t) >= datetime(2026, 1, 1))
    m = sum(nets) / len(nets)
    m25 = [x for x, y in zip(nets, y26) if not y]; m26 = [x for x, y in zip(nets, y26) if y]
    if len(nets) != fin["H_n"] or abs(m - fin["H_mean"]) > 1e-12 or (m25 and abs(sum(m25) / len(m25) - fin["H_mean_2025"]) > 1e-12) \
            or (m26 and abs(sum(m26) / len(m26) - fin["H_mean_2026"]) > 1e-12):
        bad4.append((fin["cfg"], "stats"))
ok("V4", not bad4, f"{sum(1 for f in rep['finals'] if f.get('H_n'))} finals: every holdout trade replayed (outcome, exit, non-overlap, funding, net) and n / mean / halves: mismatches {bad4[:3]}")
fins = [f for f in rep["finals"] if f.get("H_n", 0) >= 2]
if fins:
    fin = fins[0]
    z0 = np.load(OUT / "cache" / f"out_{fin['set']}.npz")
    zz = {k: z0[k] for k in ("ret_long", "ret_short", "exit_long", "exit_short")}   # load once (an NpzFile re-reads on every access)
    i0 = int((datetime(2025, 1, 1) - T0).total_seconds() // 300); i1 = NG - 1
    means = []
    for sd in range(200):
        rng = np.random.default_rng(sd)
        order = rng.permutation(np.arange(i0, i1))
        st, en, nets = [], [], []
        for t in order:
            if len(nets) >= fin["H_n"]:
                break
            sg = 1 if rng.random() < fin["H_long_share"] else -1
            g = float(zz["ret_long" if sg > 0 else "ret_short"][t]); x = zz["exit_long" if sg > 0 else "exit_short"][t]
            if not math.isfinite(g):
                continue
            x = int(x); k = bisect.bisect_left(st, t)
            if (k > 0 and en[k - 1] > t) or (k < len(st) and st[k] < x):
                continue
            st.insert(k, t); en.insert(k, x)
            nets.append(g - FUT - (cumf(int(x)) - cumf(int(t))) * sg)
        means.append(sum(nets) / len(nets))
    p95 = float(np.percentile(means, 95))
    ok("V5", abs(p95 - fin["H_ctrl_p95"]) < 1e-9, f"random control of {fin['cfg']} {fin['set']} (200 seeds) recomputed: p95 {p95:.6f} vs report {fin['H_ctrl_p95']:.6f}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
