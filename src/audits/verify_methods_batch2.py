"""Independent verifier of methods bench Batch 2 (logs/research_methods_bench/BATCH2_PROTOCOL_PREREGISTERED.md + master protocol + amendment 1).
Own loop code for scale aggregation, 12 indicators, info bars, reversal exits, reports, ranking, random control. numpy/pandas only to read
files and for seeded draws. W1 manifest + lock  W2 300 signal values  W3 X3 trades of 5 configs  W4 daily->monthly->yearly of 5 configs
W5 ranking  W6 random control for one X1, X2, X3 config  W7 stress / delay of 3 configs  W8 lookahead on 5 new cutoffs"""
import bisect
import csv
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "research_methods_bench"
sys.path.insert(0, str(R_ / "src" / "research"))
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


man = list(csv.DictReader(open(OUT / "batch2_input_manifest.csv", encoding="utf-8")))
rep = json.loads((OUT / "BATCH2_RESULTS.json").read_text(encoding="utf-8"))
bad = [m["path"] for m in man if sha(R_ / m["path"]) != m["sha256"]]
lock = sha(OUT / "BATCH2_PROTOCOL_PREREGISTERED.md") == (OUT / "BATCH2_PROTOCOL_SHA256.txt").read_text().split()[0] == rep["protocol_sha256"]
ok("W1", not bad and lock and sha(OUT / "batch2_input_manifest.csv") == rep["manifest_sha256"]
   and (OUT / "BATCH2_RESULTS_SHA256.txt").read_text().split()[0] == sha(OUT / "BATCH2_RESULTS.json"),
   f"{len(man)} inputs; mismatches {bad}; protocol lock {lock}")

import methods_bench_b2 as M2                                           # code under test
import methods_bench as MB
import btc_entry_study as B
d = B.load()
gpar = json.loads((OUT / "batch2_garch_params.json").read_text(encoding="utf-8"))
S = M2.batch2_signals(d, gpar)
O, H, L, C, V = (d[c].values.tolist() for c in ("open", "high", "low", "close", "volume"))
TB, QV, NT = (d[c].values.tolist() for c in ("taker_buy_base", "quote_volume", "trades"))
N = len(O)
nan = math.isnan


def scale_bars(minutes):
    """own aggregation: bucket [T - s, T) of open times, value known at bar index b0 + k."""
    k = minutes // 5
    out = []
    for b0 in range(0, N, k):
        idx = [i for i in range(b0, min(N, b0 + k)) if not nan(O[i])]
        if not idx:
            continue
        out.append(dict(known=b0 + k, o=O[idx[0]], h=max(H[i] for i in idx), l=min(L[i] for i in idx), c=C[idx[-1]],
                        v=sum(V[i] for i in idx), tb=sum(TB[i] for i in idx), qv=sum(QV[i] for i in idx)))
    return out


def latest_before(bars, i):
    lo, hi = 0, len(bars) - 1
    if bars[0]["known"] > i + 1:
        return None
    while lo < hi:
        m = (lo + hi + 1) // 2
        if bars[m]["known"] <= i + 1:
            lo = m
        else:
            hi = m - 1
    return lo


def sign(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


def ema_series(x, n, minp):
    a = 2 / (n + 1); out = []; e = None
    for k, v in enumerate(x):
        e = v if e is None else e + a * (v - e)
        out.append(e if k >= minp - 1 else None)
    return out


def prep(bars):
    """own full-series loops: ATR20 (Wilder), OBV + EMA20, NVI + EMA255, log returns."""
    c = [b["c"] for b in bars]
    tr, a20 = [], []
    e = None
    for j, b in enumerate(bars):
        t = b["h"] - b["l"] if j == 0 else max(b["h"] - b["l"], abs(b["h"] - c[j - 1]), abs(b["l"] - c[j - 1]))
        tr.append(t); e = t if e is None else e + (t - e) / 20
        a20.append(e if j >= 19 else None)
    obv = [0.0]
    for j in range(1, len(bars)):
        obv.append(obv[-1] + sign(c[j] - c[j - 1]) * bars[j]["v"])
    nvi = [1000.0]
    for j in range(1, len(bars)):
        nvi.append(nvi[-1] * (1 + (c[j] / c[j - 1] - 1)) if bars[j]["v"] < bars[j - 1]["v"] else nvi[-1])
    r = [None] + [math.log(c[j] / c[j - 1]) for j in range(1, len(bars))]
    return dict(c=c, a20=a20, obv=obv, obv_e=ema_series(obv, 20, 20), nvi=nvi, nvi_e=ema_series(nvi, 255, 255), r=r)


def qrank(vals, j):
    """pct rank of vals[j] among the last 500 (incl. j), non-missing, min 250; returns (q, near_tie)."""
    w = [x for x in vals[max(0, j - 499):j + 1] if x is not None and not nan(x)]
    x = vals[j]
    if x is None or nan(x) or len(w) < 250:
        return None, False
    lt = sum(1 for y in w if y < x); eq = sum(1 for y in w if y == x)
    near = any(y != x and abs(y - x) <= 1e-10 * abs(x) for y in w)
    return (lt + (eq + 1) / 2) / len(w), near


def vprofile(bars, j):
    w = bars[j - 99:j + 1]
    lo, hi = min(b["l"] for b in w), max(b["h"] for b in w)
    if not hi > lo:
        return 0, False
    wd = (hi - lo) / 50; vol = [0.0] * 50
    for b in w:
        k = int(math.floor(((b["h"] + b["l"] + b["c"]) / 3 - lo) / wd)); k = min(49, max(0, k))
        vol[k] += b["v"]
    poc = max(range(50), key=lambda k: (vol[k], -k)); a, z = poc, poc; tot = vol[poc]; tv = sum(vol)
    while tot < 0.7 * tv:
        up = vol[z + 1] if z < 49 else None; dn = vol[a - 1] if a > 0 else None
        if dn is None or (up is not None and up >= dn):
            z += 1; tot += up
        else:
            a -= 1; tot += dn
    vah, val = lo + (z + 1) * wd, lo + a * wd
    c = bars[j]["c"]
    near = min(abs(c - vah), abs(c - val)) <= 1e-9 * c
    return (1 if c > vah else (-1 if c < val else 0)), near


def dollar_bars_signal():
    """own loop: dollar bars with the prior-30-day threshold, TS20 on bar closes, carried."""
    days = {}
    for i in range(N):
        dk = i // 288
        days[dk] = days.get(dk, 0.0) + (QV[i] if not nan(QV[i]) else 0.0)
    sig = [0] * N; cum = 0.0; closes = []; cur = 0
    for i in range(N):
        dk = i // 288
        if dk >= 30:
            th = sum(days[q] for q in range(dk - 30, dk)) / 30 / 48
            if not nan(QV[i]):
                cum += QV[i]
                if cum >= th:
                    closes.append(C[i]); cum = 0.0
                    cur = sign(closes[-1] - closes[-21]) if len(closes) > 20 else 0
        sig[i] = cur
    return sig


random.seed(11)
sb = {nm: scale_bars(mn) for nm, mn in (("15m", 15), ("1h", 60), ("4h", 240))}
pp = {nm: prep(b) for nm, b in sb.items()}
dbs = dollar_bars_signal()
RULES = ["A3.06a_NR7", "A3.07_WilliamsVB", "A3.05_Squeeze", "A3.03a_Parkinson20_LOW", "A3.02a_RV20_HIGH", "A4.04a_CVD", "A4.06_RelVol",
         "A4.01a_OBV", "A4.03a_NVI", "A3.09_Jump", "A4.07_VolProfile", "A4.10_DollarBars"]
bad2, boundary, checked, per = [], [], 0, {}
while checked < 300:
    rule = random.choice(RULES)
    i = random.randrange(20000, N - 10)
    if rule == "A4.10_DollarBars":
        exp, near = dbs[i], False; key = "A4.10_DollarBars_follow"
    else:
        sc = random.choice(list(sb)); bars = sb[sc]; P_ = pp[sc]; j = latest_before(bars, i)
        if j is None or j < 600:
            continue
        b = bars[j]; c = P_["c"]; near = False
        if rule == "A3.06a_NR7":
            rg = [x["h"] - x["l"] for x in bars[j - 7:j]]
            exp = (1 if c[j] > bars[j - 1]["h"] else (-1 if c[j] < bars[j - 1]["l"] else 0)) if rg[-1] == min(rg) else 0
        elif rule == "A3.07_WilliamsVB":
            pr = bars[j - 1]["h"] - bars[j - 1]["l"]; up, dn = b["o"] + 0.5 * pr, b["o"] - 0.5 * pr
            exp = 1 if c[j] > up else (-1 if c[j] < dn else 0); near = min(abs(c[j] - up), abs(c[j] - dn)) <= 1e-9 * c[j]
        elif rule == "A3.05_Squeeze":
            def insq(q):
                w = c[q - 19:q + 1]; m = sum(w) / 20; sd = math.sqrt(sum((x - m) ** 2 for x in w) / 20)
                return 2 * sd < 1.5 * P_["a20"][q], abs(2 * sd - 1.5 * P_["a20"][q]) <= 1e-9 * P_["a20"][q], m
            s1, n1, _ = insq(j - 1); s0, n0, m = insq(j)
            exp = sign(c[j] - m) if (s1 and not s0) else 0; near = n1 or n0
        elif rule == "A3.03a_Parkinson20_LOW":
            vals = [None] * len(bars)
            for q in range(max(19, j - 520), j + 1):
                vals[q] = math.sqrt(sum(math.log(x["h"] / x["l"]) ** 2 for x in bars[q - 19:q + 1]) / 20 / (4 * math.log(2)))
            qq, near = qrank(vals, j)
            exp = sign(c[j] - c[j - 20]) if (qq is not None and qq < 0.2) else 0
        elif rule == "A3.02a_RV20_HIGH":
            vals = [None] * len(bars)
            for q in range(max(20, j - 520), j + 1):
                w = P_["r"][q - 19:q + 1]; m = sum(w) / 20; vals[q] = math.sqrt(sum((x - m) ** 2 for x in w) / 19)
            qq, near = qrank(vals, j)
            exp = sign(c[j] - c[j - 20]) if (qq is not None and qq > 0.8) else 0
        elif rule == "A4.04a_CVD":
            w = bars[j - 19:j + 1]; x = sum(2 * y["tb"] - y["v"] for y in w) / sum(y["v"] for y in w)
            exp = sign(x); near = abs(x) <= 1e-9
        elif rule == "A4.06_RelVol":
            m = sum(y["v"] for y in bars[j - 20:j]) / 20; x = b["v"] / m
            exp = sign(c[j] - b["o"]) if x > 2 else 0; near = abs(x - 2) <= 1e-9
        elif rule == "A4.01a_OBV":
            e = P_["obv_e"][j]; x = P_["obv"][j]
            exp = (1 if x > e else -1) if e is not None else 0; near = e is not None and abs(x - e) <= 1e-9 * max(abs(x), 1.0)
        elif rule == "A4.03a_NVI":
            e = P_["nvi_e"][j]; x = P_["nvi"][j]
            exp = (1 if x > e else -1) if e is not None else 0; near = e is not None and abs(x - e) <= 1e-9 * x
        elif rule == "A3.09_Jump":
            r = P_["r"]; bv = math.pi / 2 * sum(abs(r[q]) * abs(r[q - 1]) for q in range(j - 50, j)) / 50
            exp = sign(r[j]) if abs(r[j]) > 4 * math.sqrt(bv) else 0; near = abs(abs(r[j]) - 4 * math.sqrt(bv)) <= 1e-9 * abs(r[j])
        else:
            exp, near = vprofile(bars, j)
        key = f"{rule}_follow_{sc}"
    got = int(S[key][i]); checked += 1; per[rule] = per.get(rule, 0) + 1
    if exp != got:
        (boundary if near else bad2).append((key, i, exp, got))
ok("W2", not bad2, f"300 random (bar, rule, scale) signals by own aggregation + loops over {len(per)} rules {per}: mismatches {len(bad2)} {bad2[:3]}; boundary {len(boundary)} {boundary[:3]}")
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
            ex = k2; px = O[k2 + 1] if not nan(O[k2 + 1]) else C[k2]
        else:
            ex = min(N - 1, t + B.CAP); q = ex
            while nan(C[q]):
                q -= 1
            px = C[q]
        if t < free or ex != x or abs(dd * (px / O[t + 1] - 1) - g) > 1e-12 or dirn[t] != dd:
            bad3.append((k, t)); break
        free = x
ok("W3", not bad3, f"X3 reversal trades of 5 random configs (H) replayed by a loop: {keys}; mismatches {bad3}")
# W4 reports
Dly = pd.read_parquet(OUT / "batch2_daily.parquet", filters=[("cfg", "in", keys)])
mon = pd.read_csv(OUT / "batch2_monthly.csv"); yr = pd.read_csv(OUT / "batch2_yearly.csv")
mon, yr = mon[mon.cfg.isin(keys)], yr[yr.cfg.isin(keys)]
bad4 = []
for k in keys:
    for xn in ("X1", "X2", "X3"):
        for cm in ("fut", "spot"):
            for pn in ("D", "V", "H", "FULL"):
                sub = Dly[(Dly.cfg == k) & (Dly.exit == xn) & (Dly.cost == cm) & (Dly.period == pn)].sort_values("date")
                last_m, last_y, nm = {}, {}, {}
                days = pd.to_datetime(sub.date)
                if len(sub) != len(pd.date_range(*MB.PERIOD_DATES[pn], freq="D")):
                    bad4.append((k, xn, cm, pn, "days")); continue
                for dt, eqv, n_ in zip(days, sub.equity, sub.n):
                    last_m[dt.strftime("%Y-%m")] = eqv; last_y[dt.year] = eqv; nm[dt.strftime("%Y-%m")] = nm.get(dt.strftime("%Y-%m"), 0) + n_
                prev = 10_000.0
                Mo = mon[(mon.cfg == k) & (mon.exit == xn) & (mon.cost == cm) & (mon.period == pn)].sort_values("unit")
                for (u, e_), r in zip(sorted(last_m.items()), Mo.itertuples()):
                    if r.unit != u or abs(r.ret - (e_ / prev - 1)) > 1e-12 or r.n != nm[u]:
                        bad4.append((k, xn, cm, pn, u)); break
                    prev = e_
                prev = 10_000.0
                Yo = yr[(yr.cfg == k) & (yr.exit == xn) & (yr.cost == cm) & (yr.period == pn)].sort_values("unit")
                for (u, e_), r in zip(sorted(last_y.items()), Yo.itertuples()):
                    if int(r.unit) != u or abs(r.ret - (e_ / prev - 1)) > 1e-12:
                        bad4.append((k, xn, cm, pn, u)); break
                    prev = e_
ok("W4", not bad4, f"daily (every calendar day present) -> monthly -> yearly for 5 configs x 3 exits x 2 costs x 4 periods: mismatches {bad4[:3]}")
# W5 ranking
Rk = pd.read_csv(OUT / "batch2_ranking.csv")
cols = ["H_mean", "H_ci_lo", "H_pos_months", "H_maxdd", "H_pf", "consistency", "H_stress_mean", "delay_agree"]
sc_ = pd.concat([Rk[c].rank(ascending=False) for c in cols], axis=1).mean(axis=1)
order = Rk.assign(s=sc_).sort_values(["s", "cfg", "exit"]).index.tolist()
ok("W5", order == list(range(len(Rk))) and np.allclose(sc_.values, Rk.rank_score.values) and len(Rk) == 972,
   f"ranking order of {len(Rk)} configs recomputed from the 8 measures")
# W6 random control (own sequential loop) for one X1, X2, X3 config
G = pd.read_csv(OUT / "batch2_gates_all.csv")
bad6 = []
Cf = pd.Series(d.close.values).ffill().values
for xn in ("X1", "X2", "X3"):
    cand = G[(G.exit == xn) & (G.H_n >= 20)]
    if cand.empty:
        continue
    g = cand.sample(1, random_state=3).iloc[0]
    tr = MB.sim_reversal(S[g.cfg], d, B.FUT_RT, cum_f, P["H"]) if xn == "X3" else B.simulate(S[g.cfg], B.load_oc(MB.EXITS[xn]), B.FUT_RT, cum_f, P["H"])
    p_long = float((tr["dir"] > 0).mean()); n = len(tr["net"])
    oc = None if xn == "X3" else B.load_oc(MB.EXITS[xn])
    holds = (tr["exit"] - tr["t"]).astype(np.int64)
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
            x = int(x); kk = bisect.bisect_left(st, t)
            if (kk > 0 and en[kk - 1] > t) or (kk < len(st) and st[kk] < x):
                continue
            st.insert(kk, t); en.insert(kk, x)
            nets.append(gg - B.FUT_RT - (cum_f[x] - cum_f[t]) * dd)
        means.append(np.mean(nets))
    if abs(np.percentile(means, 95) - g.ctrl_p95) > 1e-12:
        bad6.append((xn, g.cfg, np.percentile(means, 95), g.ctrl_p95))
    print(f"  W6 {xn} {g.cfg}: own p95 {np.percentile(means, 95):.10f} stored {g.ctrl_p95:.10f}", flush=True)
ok("W6", not bad6, f"random control (own sequential loop, 200 seeds) for one X1, X2, X3 config: mismatches {bad6}")
# W7 stress / delay
Mt = pd.read_csv(OUT / "batch2_metrics.csv")
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
# W8 lookahead on 5 new cutoffs
rng = np.random.default_rng(777)
cuts = sorted(int(x) for x in rng.integers(int(d.index.searchsorted(pd.Timestamp("2021-01-01"))), N - 1, 5))
lb = M2.lookahead(d, gpar, S, cuts, lambda m: print("  " + m, flush=True))
ok("W8", not lb, f"lookahead: signals on data truncated at 5 new cutoffs equal the full-data signals before each cutoff; differing {sorted(set(lb))[:5]}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
