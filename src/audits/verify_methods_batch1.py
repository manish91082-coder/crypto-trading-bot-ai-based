"""Independent verifier of methods bench Batch 1 (logs/research_methods_bench/MASTER_BENCH_PROTOCOL_PREREGISTERED.md + amendment 1).
Own loop code for indicators, aggregation, reversal exits, reports, ranking. numpy/pandas only for reading files and seeded draws.
W1 manifest  W2 300 signal values (loop indicators incl. scale aggregation + carry)  W3 X3 trades of 5 configs  W4 daily->monthly->yearly
of 5 configs (all periods, both costs)  W5 ranking order  W6 random control for one X1, X2, X3 config  W7 stress / delay of 3 configs"""
import csv
import hashlib
import json
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "research_methods_bench"
sys.path.insert(0, str(R_ / "src" / "research"))
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


man = list(csv.DictReader(open(OUT / "input_manifest.csv", encoding="utf-8")))
rep = json.loads((OUT / "BATCH1_RESULTS.json").read_text(encoding="utf-8"))
bad = [m["path"] for m in man if hashlib.sha256((R_ / m["path"]).read_bytes()).hexdigest() != m["sha256"]]
ok("W1", not bad and hashlib.sha256((OUT / "input_manifest.csv").read_bytes()).hexdigest() == rep["manifest_sha256"], f"{len(man)} inputs; mismatches {bad}")

import methods_bench as MB                                               # code under test (signals, sims)
import btc_entry_study as B
d = B.load()
S = MB.batch1_signals(d)
T0 = datetime(2020, 1, 1)
O, H, L, C, V = (d[c].values.tolist() for c in ("open", "high", "low", "close", "volume"))
N = len(O)


def scale_bars(minutes):
    """own aggregation: bucket [T - s, T) of open times, value known at T."""
    k = minutes // 5
    out = []
    for b0 in range(0, N, k):
        idx = [i for i in range(b0, min(N, b0 + k)) if not math.isnan(O[i])]
        if not idx:
            continue
        out.append((b0 + k, O[idx[0]], max(H[i] for i in idx), min(L[i] for i in idx), C[idx[-1]], sum(V[i] for i in idx)))
    return out                                                          # (bar index at which the value is known, o, h, l, c, v)


def latest_before(bars, i):
    """index of the last scale bar known at the close of 5m bar i (known index <= i + 1)."""
    lo, hi = 0, len(bars) - 1
    if bars[0][0] > i + 1:
        return None
    while lo < hi:
        m = (lo + hi + 1) // 2
        if bars[m][0] <= i + 1:
            lo = m
        else:
            hi = m - 1
    return lo


random.seed(5)
sb = {nm: scale_bars(mn) for nm, mn in (("15m", 15), ("1h", 60), ("4h", 240))}
bad2 = []
checked = 0
while checked < 300:
    sc = random.choice(list(sb))
    rule = random.choice(["A1.02_EMA20x50", "A1.09_Donchian20", "A2.01a_RSI14", "A2.08_Bollinger", "A2.03_WilliamsR", "A1.17_TSMOM20"])
    i = random.randrange(20000, N - 10)
    bars = sb[sc]; j = latest_before(bars, i)
    if j is None or j < 400:
        continue
    cl = [b[4] for b in bars[:j + 1]]; hi_ = [b[2] for b in bars[:j + 1]]; lo_ = [b[3] for b in bars[:j + 1]]
    if rule == "A1.02_EMA20x50":
        def ema_last(x, n):
            a = 2 / (n + 1); e = None
            for k_, v in enumerate(x):
                e = v if e is None else e + a * (v - e)
            return e
        e20, e50 = ema_last(cl, 20), ema_last(cl, 50); exp = 1 if e20 > e50 else -1
    elif rule == "A1.09_Donchian20":
        exp = 1 if cl[-1] > max(hi_[-21:-1]) else (-1 if cl[-1] < min(lo_[-21:-1]) else 0)
    elif rule == "A2.01a_RSI14":
        au = ad = None                                                   # Wilder smoothing seeded at the first change (alpha 1/14, recursive)
        for k_ in range(1, len(cl)):
            ch = cl[k_] - cl[k_ - 1]; u, dn = max(ch, 0.0), max(-ch, 0.0)
            au = u if au is None else au + (u - au) / 14
            ad = dn if ad is None else ad + (dn - ad) / 14
        r = 100 - 100 / (1 + au / ad) if ad else 100.0
        exp = 1 if r < 30 else (-1 if r > 70 else 0)
    elif rule == "A2.08_Bollinger":
        w = cl[-20:]; m = sum(w) / 20; sd = math.sqrt(sum((x - m) ** 2 for x in w) / 20)
        exp = 1 if cl[-1] < m - 2 * sd else (-1 if cl[-1] > m + 2 * sd else 0)
    elif rule == "A2.03_WilliamsR":
        hh, ll = max(hi_[-14:]), min(lo_[-14:]); wr = -100 * (hh - cl[-1]) / (hh - ll)
        exp = 1 if wr < -80 else (-1 if wr > -20 else 0)
    else:
        exp = 1 if cl[-1] > cl[-21] else (-1 if cl[-1] < cl[-21] else 0)
    key = f"{rule}_fade_{sc}" if rule.startswith("A2") else f"{rule}_{sc}"
    got = int(S[key][i])
    checked += 1
    if exp != got:
        bad2.append((key, i, exp, got))
ok("W2", len(bad2) <= 0, f"300 random (bar, rule, scale) signals by own aggregation + loop indicators: mismatches {len(bad2)} {bad2[:3]}")
# W3 reversal exits
cum_f = B.cum_funding(d)
P = B.periods(d); P["FULL"] = (0, N - 1)
keys = random.sample(sorted(S), 5)
bad3 = []
for k in keys:
    dirn = S[k]
    tr = MB.sim_reversal(dirn, d, B.FUT_RT, cum_f, P["H"])
    free = P["H"][0]
    for t, dd, g, x in zip(tr["t"], tr["dir"], tr["gross"], tr["exit"]):
        t, dd, x = int(t), int(dd), int(x)
        k2 = next((q for q in range(t + 1, min(N, t + 1 + B.CAP)) if dirn[q] == -dd), None)
        if k2 is not None and k2 <= t + B.CAP:
            ex = k2; px = O[k2 + 1] if not math.isnan(O[k2 + 1]) else C[k2]
        else:
            ex = min(N - 1, t + B.CAP); q = ex
            while math.isnan(C[q]):
                q -= 1
            px = C[q]
        if t < free or ex != x or abs(dd * (px / O[t + 1] - 1) - g) > 1e-12 or dirn[t] != dd:
            bad3.append((k, t)); break
        free = x
ok("W3", not bad3, f"X3 reversal trades of 5 random configs (H) replayed by a loop: mismatches {bad3}")
# W4 reports
Dly = pd.read_parquet(OUT / "batch1_daily.parquet")
mon = pd.read_csv(OUT / "batch1_monthly.csv"); yr = pd.read_csv(OUT / "batch1_yearly.csv")
bad4 = []
for k in keys:
    for xn in ("X1", "X2", "X3"):
        for cm in ("fut", "spot"):
            for pn in ("D", "V", "H", "FULL"):
                sub = Dly[(Dly.cfg == k) & (Dly.exit == xn) & (Dly.cost == cm) & (Dly.period == pn)].sort_values("date")
                eq = 10_000.0; last_m = {}; last_y = {}; nm = {}
                days = pd.to_datetime(sub.date)
                exp_days = pd.date_range(*MB.PERIOD_DATES[pn], freq="D")
                if len(sub) != len(exp_days):
                    bad4.append((k, xn, cm, pn, "days")); continue
                for dt, eqv, n_ in zip(days, sub.equity, sub.n):
                    last_m[dt.strftime("%Y-%m")] = eqv; last_y[dt.year] = eqv; nm[dt.strftime("%Y-%m")] = nm.get(dt.strftime("%Y-%m"), 0) + n_
                prev = 10_000.0
                M = mon[(mon.cfg == k) & (mon.exit == xn) & (mon.cost == cm) & (mon.period == pn)].sort_values("unit")
                for (u, e_), r in zip(sorted(last_m.items()), M.itertuples()):
                    if r.unit != u or abs(r.ret - (e_ / prev - 1)) > 1e-12 or r.n != nm[u]:
                        bad4.append((k, xn, cm, pn, u)); break
                    prev = e_
                prev = 10_000.0
                Y = yr[(yr.cfg == k) & (yr.exit == xn) & (yr.cost == cm) & (yr.period == pn)].sort_values("unit")
                for (u, e_), r in zip(sorted(last_y.items()), Y.itertuples()):
                    if int(r.unit) != u or abs(r.ret - (e_ / prev - 1)) > 1e-12:
                        bad4.append((k, xn, cm, pn, u)); break
                    prev = e_
ok("W4", not bad4, f"daily (every calendar day present) -> monthly -> yearly for 5 configs x 3 exits x 2 costs x 4 periods: mismatches {bad4[:3]}")
# W5 ranking
Rk = pd.read_csv(OUT / "batch1_ranking.csv")
cols = [("H_mean", False), ("H_ci_lo", False), ("H_pos_months", False), ("H_maxdd", False), ("H_pf", False), ("consistency", False), ("H_stress_mean", False), ("delay_agree", False)]
sc_ = pd.concat([Rk[c].rank(ascending=a) for c, a in cols], axis=1).mean(axis=1)
order = Rk.assign(s=sc_).sort_values(["s", "cfg", "exit"]).index.tolist()
ok("W5", order == list(range(len(Rk))) and np.allclose(sc_.values, Rk.rank_score.values), f"ranking order of {len(Rk)} configs recomputed from the 8 measures")
# W6 random control (own sequential loop) for one X1, X2, X3 config
G = pd.read_csv(OUT / "batch1_gates_all.csv")
import bisect
bad6 = []
for xn in ("X1", "X2", "X3"):
    cand = G[(G.exit == xn) & (G.H_n >= 20)]
    if cand.empty:
        continue
    g = cand.sample(1, random_state=3).iloc[0]
    tr = MB.sim_reversal(S[g.cfg], d, B.FUT_RT, cum_f, P["H"]) if xn == "X3" else B.simulate(S[g.cfg], B.load_oc(MB.EXITS[xn]), B.FUT_RT, cum_f, P["H"])
    p_long = float((tr["dir"] > 0).mean()); n = len(tr["net"])
    oc = None if xn == "X3" else B.load_oc(MB.EXITS[xn])
    if oc is not None:
        oc = {k: oc[k] for k in ("ret_long", "ret_short", "exit_long", "exit_short")}
    holds = (tr["exit"] - tr["t"]).astype(np.int64)
    Cf = pd.Series(d.close.values).ffill().values
    means = []
    for sd in range(200):
        rng = np.random.default_rng(sd)
        order_ = rng.permutation(np.arange(P["H"][0], P["H"][1]))
        hp = rng.permutation(holds) if xn == "X3" else None
        st, en, nets = [], [], []
        for j, t in enumerate(order_):
            if len(nets) >= n:
                break
            dd = 1 if rng.random() < p_long else -1
            if oc is not None:
                gg = oc["ret_long" if dd > 0 else "ret_short"][t]; x = oc["exit_long" if dd > 0 else "exit_short"][t]
            else:
                x = min(t + int(hp[j % len(hp)]), N - 1); gg = dd * (Cf[x] / O[t + 1] - 1)
            if not math.isfinite(gg):
                continue
            x = int(x); k = bisect.bisect_left(st, t)
            if (k > 0 and en[k - 1] > t) or (k < len(st) and st[k] < x):
                continue
            st.insert(k, t); en.insert(k, x)
            nets.append(gg - B.FUT_RT - (cum_f[x] - cum_f[t]) * dd)
        means.append(np.mean(nets))
    if abs(np.percentile(means, 95) - g.ctrl_p95) > 1e-12:
        bad6.append((xn, g.cfg, np.percentile(means, 95), g.ctrl_p95))
ok("W6", not bad6, f"random control (own sequential loop, 200 seeds) for one X1, X2, X3 config: mismatches {bad6}")
# W7 stress / delay
Mt = pd.read_csv(OUT / "batch1_metrics.csv")
bad7 = []
for k in keys[:3]:
    for xn in ("X1", "X3"):
        dirn = S[k]; dl = np.r_[np.int8(0), dirn[:-1]].astype(np.int8)
        run = (lambda dr, cst: MB.sim_reversal(dr, d, cst, cum_f, P["H"])) if xn == "X3" else (lambda dr, cst: B.simulate(dr, B.load_oc(MB.EXITS[xn]), cst, cum_f, P["H"]))
        s_ = run(dirn, 2 * B.FUT_RT)["net"]; de = run(dl, B.FUT_RT)["net"]
        r = Mt[(Mt.cfg == k) & (Mt.exit == xn) & (Mt.cost == "fut")].iloc[0]
        if (len(s_) and abs(s_.mean() - r.H_stress_mean) > 1e-12) or (len(de) and abs(de.mean() - r.H_delay_mean) > 1e-12):
            bad7.append((k, xn))
ok("W7", not bad7, f"stress (2x cost) and delay (+1 bar) H means of 3 configs x 2 exits recomputed: mismatches {bad7}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
