"""Independent verifier for logs/oracle_9m_2026 (protocol ORACLE_9M_PROTOCOL_PREREGISTERED.md, SHA 2c68bbc4...).
Plain Python loops; imports nothing from src/research/oracle_9m.py. Checks K1..K7 of protocol §8. Exit code 1 on any failure."""
import csv
import gzip
import hashlib
import itertools
import json
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
O = P / "logs/oracle_9m_2026"
FAIL = []
TOL = 1e-9


def check(name, ok, msg=""):
    print(f"[{name} {'OK' if ok else 'FAIL'}] {msg}", flush=True)
    if not ok:
        FAIL.append(name)


def close(a, b, tol=TOL):
    if a is None or b is None:
        return a is b
    if isinstance(a, float) and isinstance(b, float) and a != a and b != b:
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


fees = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
CF = fees["rules"]["paper_futures_taker_per_side"]
CS = fees["rules"]["paper_spot_per_side"]
CM = fees["futures_usdm"]["bnb_maker"] + fees["impact_per_side"]


def read_bars(path, t0, t1):
    op = gzip.open if str(path).endswith(".gz") else open
    out = {}
    with op(path, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ts = r["timestamp"][:19]
            if len(ts) == 10:
                ts += " 00:00:00"
            t = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            if t0 <= t <= t1:
                out[t] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"]))
    return out


def agg(bars, minutes):
    """aggregate sorted (t,o,h,l,c,v) lists into buckets [t, t+minutes) aligned to the UTC day."""
    out = {}
    for t, (o, h, l, c, v) in sorted(bars.items()):
        mins = t.hour * 60 + t.minute
        k = datetime(t.year, t.month, t.day) + timedelta(minutes=(mins // minutes) * minutes) if minutes < 1440 else datetime(t.year, t.month, t.day)
        if k not in out:
            out[k] = [o, h, l, c, v]
        else:
            b = out[k]
            b[1] = max(b[1], h); b[2] = min(b[2], l); b[3] = c; b[4] += v
    return out


# ---------------- K1 ----------------
man = list(csv.DictReader(open(O / "input_manifest.csv", encoding="utf-8")))
ok = all(hashlib.sha256((P / r["path"]).read_bytes()).hexdigest() == r["sha256"] for r in man)
check("K1a", ok and len(man) == 5, f"input SHAs match manifest ({len(man)} files)")
T0, T1 = datetime(2025, 12, 1), datetime(2026, 9, 30, 23, 55)
b5 = read_bars(P / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", T0, T1)
b5_26 = {t: v for t, v in b5.items() if t >= datetime(2026, 1, 1)}
check("K1b", len(b5_26) == 273 * 288, f"2026 5m bars {len(b5_26)}")
for name, path, mins in (("15m", "data/universe_hf/15m/BTCUSDT_15m_full.csv.gz", 15), ("1h", "data/universe_all/1h/BTCUSDT_1h_full.csv.gz", 60),
                         ("1d", "data/universe_all/1d/BTCUSDT_1d.csv", 1440)):
    f = read_bars(P / path, datetime(2026, 1, 1), T1)
    a = agg(b5_26, mins)
    bad = sum(1 for t in a if t not in f or any(abs(a[t][i] - f[t][i]) > 1e-9 for i in range(4)))
    check(f"K1c_{name}", len(a) == len(f) and bad == 0, f"5m aggregate vs {name} file: {len(a)} vs {len(f)} bars, OHLC mismatches {bad}")

daily = agg(b5, 1440)
DAYS = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(273)]
STUDY = datetime(2026, 2, 13)


def bars_of(day, mins):
    x = {t: v for t, v in b5.items() if day <= t < day + timedelta(days=1)}
    a = agg(x, mins) if mins > 5 else {t: list(v) for t, v in x.items()}
    return [(t, *a[t]) for t in sorted(a)]


def levels(day):
    prev = [d for d in sorted(daily) if d < day]
    p1 = daily[prev[-1]]
    last7 = [daily[d] for d in prev[-7:]]
    return dict(pdh=p1[1], pdl=p1[2], pdc=p1[3], d7h=max(x[1] for x in last7), d7l=min(x[2] for x in last7))


print("building per-day bars ...", flush=True)
BYDAY = {}
for t, v in b5.items():
    BYDAY.setdefault(datetime(t.year, t.month, t.day), []).append((t, *v))
for d in BYDAY:
    BYDAY[d].sort()


def tf_bars(day, mins):
    x = BYDAY[day]
    if mins == 5:
        return [list(r) for r in x]
    out = []
    for r in x:
        mm = r[0].hour * 60 + r[0].minute
        k = day + timedelta(minutes=(mm // mins) * mins)
        if out and out[-1][0] == k:
            b = out[-1]; b[2] = max(b[2], r[2]); b[3] = min(b[3], r[3]); b[4] = r[4]; b[5] += r[5]
        else:
            out.append([k, r[1], r[2], r[3], r[4], r[5]])
    return out


# ---------------- K2: A1 / A2 by double loops ----------------
od = pd.read_parquet(O / "oracle_day.parquet")
otf = pd.read_parquet(O / "oracle_tf.parquet")
otr = pd.read_parquet(O / "oracle_trades.parquet")
check("K2a", len(od) == 273 and len(otf) == 273 * 5, f"rows oracle_day {len(od)}, oracle_tf {len(otf)}")
odi = {r.date.to_pydatetime(): r for r in od.itertuples()}
otfi = {(r.date.to_pydatetime(), r.tf): r for r in otf.itertuples()}


def best_long(lo, hi):
    best, bi, bj = -1e18, None, None
    for j in range(1, len(hi)):
        for i in range(j):
            v = hi[j] / lo[i] - 1
            if v > best:
                best, bi, bj = v, i, j
    return best, bi, bj


def best_short(lo, hi):
    best, bi, bj = -1e18, None, None
    for j in range(1, len(lo)):
        for i in range(j):
            v = 1 - lo[j] / hi[i]
            if v > best:
                best, bi, bj = v, i, j
    return best, bi, bj


bad_a1 = bad_a2 = bad_desc = 0
TFM = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
POINTS = {}
for day in DAYS:
    x = tf_bars(day, 5)
    t = [r[0] for r in x]; o = [r[1] for r in x]; h = [r[2] for r in x]; l = [r[3] for r in x]; c = [r[4] for r in x]
    r = odi[day]
    v, i, j = best_long(l, h)
    sv, si, sj = best_short(l, h)
    if not (close(v * 100, r.a1_long_gross_pct) and t[i] == r.a1_long_entry_t and t[j] == r.a1_long_exit_t
            and close(sv * 100, r.a1_short_gross_pct) and t[si] == r.a1_short_entry_t and t[sj] == r.a1_short_exit_t
            and close((v - 2 * CF) * 100, r.a1_long_net_fut_pct) and close((v - 2 * CS) * 100, r.a1_long_net_spot_pct)):
        bad_a1 += 1
    H, L = max(h), min(l)
    body = abs(c[-1] - o[0]) / (H - L)
    typ = "TREND" if body >= 0.6 else ("RANGE" if body <= 0.3 else "MIXED")
    f8 = [q for q in x if q[0] < day + timedelta(hours=8)]
    r8 = (max(q[2] for q in f8) / min(q[3] for q in f8) - 1) * 100
    lv = levels(day)
    if not (typ == r.day_type and close(r8, r.first8h_range_pct) and close(lv["pdh"], r.pdh) and close(lv["d7l"], r.d7l)
            and close((c[-1] / o[0] - 1) * 100, r.ret_pct) and close((H / L - 1) * 100, r.range_pct)):
        bad_desc += 1
    for tfn, mins in TFM.items():
        xb = tf_bars(day, mins)
        p = [xb[0][1]] + [q[4] for q in xb]
        pt = [day] + [q[0] + timedelta(minutes=mins) for q in xb]
        POINTS[(day, tfn)] = (p, pt)
        rr = otfi[(day, tfn)]
        lg, a, b = best_long(p, p)
        sg, sa, sb = best_short(p, p)
        if not (close(lg * 100, rr.a2_long_gross_pct) and pt[a] == rr.a2_long_entry_t and pt[b] == rr.a2_long_exit_t
                and close(sg * 100, rr.a2_short_gross_pct) and pt[sa] == rr.a2_short_entry_t and pt[sb] == rr.a2_short_exit_t):
            bad_a2 += 1
check("K2b", bad_a1 == 0, f"A1 extreme oracle recomputed by double loop: {bad_a1} mismatching days of 273")
check("K2c", bad_a2 == 0, f"A2 close-to-close oracle, 5 TFs: {bad_a2} mismatches of {273 * 5}")
check("K2d", bad_desc == 0, f"day descriptors (type, first-8h range, levels, ret, range): {bad_desc} mismatches")


# ---------------- K3: DP ----------------
def tv(p, a, b, c, short):
    lv = p[b] / p[a] - 1 - 2 * c
    if not short:
        return lv
    return max(lv, 1 - p[b] / p[a] - 2 * c)


def dp(p, c, short):
    m = len(p)
    V = [0.0] * m
    for b in range(1, m):
        best = V[b - 1]
        for a in range(b):
            q = V[a] + tv(p, a, b, c, short)
            if q > best:
                best = q
        V[b] = best
    return V[-1]


def brute(p, c, short):
    """exhaustive: every set of non-overlapping intervals (a<b, next a >= previous b)."""
    m = len(p)
    best = 0.0

    def rec(start, acc):
        nonlocal best
        best = max(best, acc)
        for a in range(start, m):
            for b in range(a + 1, m):
                rec(b, acc + tv(p, a, b, c, short))
    rec(0, 0.0)
    return best


MODES = {"FUT": (CF, True), "SPOT": (CS, False), "FUT_MAKER": (CM, True)}
bad_dp = bad_sum = 0
trg = otr.groupby(["date", "tf", "mode"])
for (day, tfn), (p, pt) in POINTS.items():
    rr = otfi[(day, tfn)]
    for mode, (c, sh) in MODES.items():
        tot = dp(p, c, sh) * 100
        if not close(tot, getattr(rr, f"a3_{mode}_total_pct"), 1e-8):
            bad_dp += 1
        if mode != "FUT_MAKER":
            key = (pd.Timestamp(day), tfn, mode)
            s = trg.get_group(key).net_pct.sum() if key in trg.groups else 0.0
            n = len(trg.get_group(key)) if key in trg.groups else 0
            if not (close(s, tot, 1e-8) and n == getattr(rr, f"a3_{mode}_n_trades")):
                bad_sum += 1
check("K3a", bad_dp == 0, f"A3 max-run recomputed by plain-loop interval DP: {bad_dp} mismatches of {len(POINTS) * 3}")
check("K3b", bad_sum == 0, f"stored optimal trades sum to the DP total and count matches: {bad_sum} mismatches")
random.seed(9)
keys = list(POINTS)
bad_bf = 0
for _ in range(300):
    p, _pt = POINTS[random.choice(keys)]
    if len(p) < 9:
        continue
    s0 = random.randrange(len(p) - 8)
    w = p[s0:s0 + 9]
    for mode, (c, sh) in MODES.items():
        if not close(dp(w, c, sh), brute(w, c, sh), 1e-12):
            bad_bf += 1
check("K3c", bad_bf == 0, f"DP == exhaustive enumeration on 300 random 9-point windows x 3 modes: {bad_bf} mismatches")

# ---------------- K4: MAE / MFE ----------------
bad_m = 0
for r in otr.itertuples():
    day = r.date.to_pydatetime()
    w = [q for q in BYDAY[day] if r.entry_time <= q[0] < r.exit_time]
    e = r.entry_px
    hi, lo = max(q[2] for q in w), min(q[3] for q in w)
    mae = (e - lo) / e * 100 if r.side == "long" else (hi - e) / e * 100
    mfe = (hi - e) / e * 100 if r.side == "long" else (e - lo) / e * 100
    g = (r.exit_px / e - 1) * 100 if r.side == "long" else (1 - r.exit_px / e) * 100
    if not (close(mae, r.mae_pct) and close(mfe, r.mfe_pct) and close(g, r.gross_pct)):
        bad_m += 1
check("K4", bad_m == 0, f"MAE/MFE/gross of {len(otr)} stored trades: {bad_m} mismatches")


# ---------------- K5: sweep events ----------------
def lvls_in(a, b, lv):
    out = []
    k = 0
    while k * 1000 <= b:
        if a < k * 1000 < b:
            out.append(("round", float(k * 1000)))
        k += 1
    for nm in ("pdh", "pdl", "d7h", "d7l"):
        if a < lv[nm] < b:
            out.append((nm, lv[nm]))
    return out


def newlow(l, k):
    return k == 0 or l[k] < min(l[:k])


def newhigh(h, k):
    return k == 0 or h[k] > max(h[:k])


def conf(o, h, l, c, s, bull):
    for k in (s + 1, s + 2):
        if k >= len(c):
            return None
        if (bull and c[k] > o[k]) or (not bull and c[k] < o[k]):
            for q in range(s + 1, k + 1):
                if (bull and l[q] < l[s]) or (not bull and h[q] > h[s]):
                    return None
            return k
    return None


ev = pd.read_parquet(O / "sweep_events.parquet")
mine = set()
for day in DAYS:
    x = tf_bars(day, 15)
    t = [q[0] for q in x]; o = [q[1] for q in x]; h = [q[2] for q in x]; l = [q[3] for q in x]; c = [q[4] for q in x]
    lv = levels(day)
    for s in range(len(c)):
        for bull in (True, False):
            for lt, L in (lvls_in(l[s], c[s], lv) if bull else lvls_in(c[s], h[s], lv)):
                ext = (newlow(l, s) or (s > 0 and newlow(l, s - 1))) if bull else (newhigh(h, s) or (s > 0 and newhigh(h, s - 1)))
                k = conf(o, h, l, c, s, bull)
                mine.add((day, t[s], "bull" if bull else "bear", lt, round(L, 6), bool(ext), k is not None))
theirs = {(r.date.to_pydatetime(), r.bar_time.to_pydatetime(), r.side, r.level_type, round(r.level, 6), bool(r.new_extreme), bool(r.confirmed))
          for r in ev.itertuples()}
check("K5", mine == theirs and len(ev) == len(theirs), f"sweep events: mine {len(mine)}, stored {len(theirs)} (rows {len(ev)}), "
      f"only-mine {len(mine - theirs)}, only-stored {len(theirs - mine)}")

# ---------------- K6: Part B re-implemented ----------------
VAR = {"V1-A": (False, False, False, CF), "V1-B": (True, False, False, CF), "V1-C": (True, True, False, CF),
       "V1-AC": (False, True, False, CF), "V1-S": (True, False, True, CS)}


def sigs(day):
    x = tf_bars(day, 15)
    t = [q[0] for q in x]; o = [q[1] for q in x]; h = [q[2] for q in x]; l = [q[3] for q in x]; c = [q[4] for q in x]
    lv = levels(day)
    res = []
    for s in range(len(c)):
        cand = []
        if lvls_in(l[s], c[s], lv) and (newlow(l, s) or (s > 0 and newlow(l, s - 1))):
            k = conf(o, h, l, c, s, True)
            if k is not None and k + 1 < len(c):
                cand.append(("long", t[k + 1], l[s]))
        if lvls_in(c[s], h[s], lv) and (newhigh(h, s) or (s > 0 and newhigh(h, s - 1))):
            k = conf(o, h, l, c, s, False)
            if k is not None and k + 1 < len(c):
                cand.append(("short", t[k + 1], h[s]))
        if len(cand) == 1:
            res.append((t[s],) + cand[0])
    res.sort(key=lambda z: (z[2], z[0]))
    return res


def run5(day, entry_t, side, sl, tp, dtx, r8, lv):
    x = BYDAY[day]
    brk = False
    for q in x:
        if q[0] < entry_t:
            continue
        on = True
        if dtx and (brk or (q[0] >= day + timedelta(hours=8) and r8 >= 3.0)):
            on = False
        oo, hh, ll = q[1], q[2], q[3]
        if side == "long":
            if oo <= sl: return oo, q[0], "SL_gap"
            if ll <= sl: return sl, q[0] + timedelta(minutes=5), "SL"
            if on and oo >= tp: return oo, q[0], "TP_gap"
            if on and hh >= tp: return tp, q[0] + timedelta(minutes=5), "TP"
            if hh > lv["pdh"]: brk = True
        else:
            if oo >= sl: return oo, q[0], "SL_gap"
            if hh >= sl: return sl, q[0] + timedelta(minutes=5), "SL"
            if on and oo <= tp: return oo, q[0], "TP_gap"
            if on and ll <= tp: return tp, q[0] + timedelta(minutes=5), "TP"
            if ll < lv["pdl"]: brk = True
    return x[-1][4], x[-1][0] + timedelta(minutes=5), "EOD"


def r8_of(day):
    f8 = [q for q in BYDAY[day] if q[0] < day + timedelta(hours=8)]
    return (max(q[2] for q in f8) / min(q[3] for q in f8) - 1) * 100


SIG = {d: sigs(d) for d in DAYS}
vt = pd.read_csv(O / "v1_trades.csv", parse_dates=["date", "sweep_time", "entry_time", "exit_time"])
vd = pd.read_csv(O / "v1_daily.csv", parse_dates=["date"])
vm = pd.read_csv(O / "v1_monthly.csv")
res = json.loads((O / "V1_RESULTS.json").read_text(encoding="utf-8"))
resi = {r["variant"]: r for r in res}
for name, (q1, dtx, lo_only, cost) in VAR.items():
    mine = []
    for day in DAYS:
        r8 = r8_of(day)
        if q1 and r8 < 1.0:
            continue
        lv = levels(day)
        last = day
        for (st, side, et, ext) in SIG[day]:
            if lo_only and side == "short":
                continue
            if q1 and et < day + timedelta(hours=8):
                continue
            if et < last:
                continue
            e = next(q[1] for q in BYDAY[day] if q[0] == et)
            sl = ext * (1 - 0.0025) if side == "long" else ext * (1 + 0.0025)
            tp = e + 2 * (e - sl) if side == "long" else e - 2 * (sl - e)
            xp, xt, why = run5(day, et, side, sl, tp, dtx, r8, lv)
            g = (xp / e - 1) if side == "long" else (1 - xp / e)
            mine.append((day, st, et, side, e, xp, xt, why, (g - 2 * cost) * 100, abs(e - sl) / e * 100))
            last = xt
    st_ = vt[vt.variant == name]
    same = len(st_) == len(mine) and all(
        a[0] == b.date and a[1] == b.sweep_time and a[2] == b.entry_time and a[3] == b.side and close(a[4], b.entry_px)
        and close(a[5], b.exit_px) and a[6] == b.exit_time and a[7] == b.reason and close(a[8], b.net_pct, 1e-8)
        for a, b in zip(mine, st_.itertuples()))
    check(f"K6a_{name}", same, f"trade list re-implemented: mine {len(mine)}, stored {len(st_)}")
    stat = [m for m in mine if m[0] != STUDY]
    dsum = {}
    for m in stat:
        dsum[m[0]] = dsum.get(m[0], 0.0) + m[8]
    d_ = vd[vd.variant == name]
    okd = len(d_) == 272 and all(close(dsum.get(r.date.to_pydatetime(), 0.0), r.net_pct, 1e-8) for r in d_.itertuples())
    msum = {}
    for m in stat:
        k = m[0].strftime("%Y-%m")
        msum[k] = msum.get(k, 0.0) + m[8]
    m_ = vm[vm.variant == name]
    okm = all(close(msum.get(r.month, 0.0), r.net_pct, 1e-8) for r in m_.itertuples()) and len(m_) == 9
    rr = resi[name]
    k = sum(1 for m in stat if m[8] > 0)
    oks = rr["trades"] == len(stat) and rr["wins"] == k and close(rr["sum_net_pct"], sum(m[8] for m in stat), 1e-8)
    check(f"K6b_{name}", okd and okm and oks, f"daily (272 rows, every day) / monthly (9) / summary sums equal; trades {len(stat)} wins {k}")
    # random control re-run with the same draws
    allow, ctx = {}, {}
    for m in stat:
        day = m[0]
        if day not in allow:
            al = [q[0] for q in tf_bars(day, 15)][1:]
            allow[day] = [a for a in al if a >= day + timedelta(hours=8)] if q1 else al
            ctx[day] = (r8_of(day), levels(day), {q[0]: q[1] for q in BYDAY[day]})
    sums = []
    for seed in range(200):
        rng = np.random.default_rng(seed)
        s = 0.0
        for m in stat:
            day = m[0]
            allowed = allow[day]
            et = allowed[int(rng.integers(len(allowed)))]
            r8d, lvd, opens = ctx[day]
            e = opens[et]
            R = e * m[9] / 100
            sl, tp = (e - R, e + 2 * R) if m[3] == "long" else (e + R, e - 2 * R)
            xp, _, _ = run5(day, et, m[3], sl, tp, dtx, r8d, lvd)
            g = (xp / e - 1) if m[3] == "long" else (1 - xp / e)
            s += (g - 2 * cost) * 100
        sums.append(s)
    real = sum(m[8] for m in stat)
    share = sum(1 for s in sums if s >= real) / 200
    check(f"K6c_{name}", close(share, rr["rc_share"], 1e-12), f"random-control share re-run: mine {share:.3f}, stored {rr['rc_share']:.3f}")
    surv = rr["sum_net_pct"] > 0 and rr["wilson_lo"] > rr["breakeven_p"] and rr["months_positive"] >= 5 and rr["rc_share"] <= 0.05
    check(f"K6d_{name}", surv == rr["survives"], f"survival verdict recomputed from the stored figures: {surv}")

# ---------------- K7 ----------------
src = (P / "src/research/oracle_9m.py").read_text(encoding="utf-8")
lits = re.findall(r"(?<![\w.])0\.0*(?:46|85|4|92|17|18|28|036|075)\b", src)
check("K7", not lits and "fees.json" in src, f"no fee literal in the main code (found {lits})")

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
