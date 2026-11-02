"""Independent verifier of Part C (logs/oracle_9m_2026/AMENDMENT_1_PART_C_PREREGISTERED.md, SHA e68da96c...).
Plain Python loops; imports nothing from src/research. Recomputes every C1 call, every C2 event, every C3 trade and the summaries."""
import csv
import gzip
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
O = P / "logs/oracle_9m_2026"
C = O / "part_c"
FAIL = []


def check(name, ok, msg=""):
    print(f"[{name} {'OK' if ok else 'FAIL'}] {msg}", flush=True)
    if not ok:
        FAIL.append(name)


def close(a, b, tol=1e-9):
    if (a != a) and (b != b):
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


am = (O / "AMENDMENT_1_SHA256.txt").read_text().split()[0]
check("V0", hashlib.sha256((O / "AMENDMENT_1_PART_C_PREREGISTERED.md").read_bytes()).hexdigest() == am, "Amendment 1 file matches its SHA")
fees = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
CF, CS = fees["rules"]["paper_futures_taker_per_side"], fees["rules"]["paper_spot_per_side"]

# ---- data: 5m as plain lists over a complete grid ----
T0, T1 = datetime(2025, 12, 1), datetime(2026, 9, 30, 23, 55)
raw = {}
with gzip.open(P / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", "rt", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        t = datetime.strptime(r["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
        if T0 <= t <= T1:
            raw[t] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
TT = []
t = T0
while t <= T1:
    TT.append(t); t += timedelta(minutes=5)
check("V1", all(t in raw for t in TT), f"complete 5m grid {len(TT)} bars")
IX = {t: i for i, t in enumerate(TT)}
Op = [raw[t][0] for t in TT]; Hp = [raw[t][1] for t in TT]; Lp = [raw[t][2] for t in TT]; Cp = [raw[t][3] for t in TT]
DAYS = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(273)]
DAYS = [d for d in DAYS if d != datetime(2026, 2, 13)]


def dayhl(d):
    p = IX[d]
    return max(Hp[p:p + 288]), min(Lp[p:p + 288]), Op[p], Cp[p + 287]


def prev_levels(d):
    ph, pl, po, pc = dayhl(d - timedelta(days=1))
    hs, ls = [], []
    for k in range(1, 8):
        h, l, _, _ = dayhl(d - timedelta(days=k))
        hs.append(h); ls.append(l)
    return dict(pdh=ph, pdl=pl, pdo=po, pdc=pc, d7h=max(hs), d7l=min(ls))


LV = {d: prev_levels(d) for d in DAYS}


# ---- sweep events (independent) ----
def bars15(d):
    p = IX[d]
    out = []
    for j in range(96):
        a = p + 3 * j
        out.append((TT[a], Op[a], max(Hp[a:a + 3]), min(Lp[a:a + 3]), Cp[a + 2]))
    return out


def lv_in(a, b, lv):
    r = [k * 1000 for k in range(int(a // 1000), int(b // 1000) + 2) if a < k * 1000 < b]
    return r + [lv[n] for n in ("pdh", "pdl", "d7h", "d7l") if a < lv[n] < b]


def sweeps(d):
    x = bars15(d)
    lv = LV[d]
    out = []                       # (bar_time, side, new_extreme, confirm_index or None, s)
    for s in range(96):
        for bull in (True, False):
            if not (lv_in(x[s][3], x[s][4], lv) if bull else lv_in(x[s][4], x[s][2], lv)):
                continue
            def newx(k):
                if k < 0: return False
                if k == 0: return True
                return x[k][3] < min(q[3] for q in x[:k]) if bull else x[k][2] > max(q[2] for q in x[:k])
            ne = newx(s) or newx(s - 1)
            ci = None
            for k in (s + 1, s + 2):
                if k >= 96: break
                if (x[k][4] > x[k][1]) if bull else (x[k][4] < x[k][1]):
                    ok = all((x[q][3] >= x[s][3]) if bull else (x[q][2] <= x[s][2]) for q in range(s + 1, k + 1))
                    ci = k if ok else None
                    break
            out.append((x[s][0], "bull" if bull else "bear", ne, ci, s))
    return out


SW = {d: sweeps(d) for d in DAYS}


def sgn(v):
    return (v > 0) - (v < 0)


# ---- C1 ----
mine = []
for d in DAYS:
    p = IX[d]; cl = Cp[p + 287]; lv = LV[d]
    pr = lv["pdc"] / lv["pdo"] - 1
    calls = [("DIR_LONG", 0, 1), ("DIR_PD_FOLLOW", 0, sgn(pr)), ("DIR_PD_FADE", 0, -sgn(pr)),
             ("DIR_CLOSEPOS", 0, 1 if (lv["pdc"] - lv["pdl"]) / (lv["pdh"] - lv["pdl"]) > 0.5 else -1),
             ("DIR_7D_MID", 0, 1 if lv["pdc"] > (lv["d7h"] + lv["d7l"]) / 2 else -1),
             ("DIR_H1_FOLLOW", 12, sgn(Cp[p + 11] - Op[p])), ("DIR_ASIA_FOLLOW", 96, sgn(Cp[p + 95] - Op[p])),
             ("DIR_ASIA_FADE", 96, -sgn(Cp[p + 95] - Op[p]))]
    for mid, off, s in calls:
        if s == 0: continue
        px = Op[p + off]
        if sgn(cl - px) == 0: continue
        mine.append((mid, d, s, s == sgn(cl - px)))
    q = [e for e in SW[d] if e[2] and e[3] is not None]
    if q:
        fb = min(e[0] for e in q)
        e0 = [e for e in q if e[0] == fb]
        if len({e[1] for e in e0}) == 1:
            s = 1 if e0[0][1] == "bull" else -1
            px = bars15(d)[e0[0][3]][4]
            if sgn(cl - px) != 0:
                mine.append(("DIR_SWEEP", d, s, s == sgn(cl - px)))
c1 = pd.read_csv(C / "c1_calls.csv", parse_dates=["date"])
theirs = [(r.method, r.date.to_pydatetime(), int(r.call), bool(r.hit)) for r in c1.itertuples()]
check("C1a", sorted(mine) == sorted(theirs), f"C1 calls recomputed: mine {len(mine)}, stored {len(theirs)}")


def wil(k, n, z=1.96):
    ph = k / n; dd = 1 + z * z / n
    mid = (ph + z * z / (2 * n)) / dd; hw = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / dd
    return mid - hw


r1 = pd.read_csv(C / "c1_ranking.csv")
ok = True
for r in r1.itertuples():
    xs = [m for m in mine if m[0] == r.method]
    k = sum(m[3] for m in xs)
    ok &= len(xs) == r.calls and k == r.hits and close(wil(k, len(xs)), r.wilson_lo)
check("C1b", ok and list(r1.wilson_lo) == sorted(r1.wilson_lo, reverse=True), "C1 ranking table (counts, Wilson, order)")

# ---- C2 ----
a1 = pd.read_parquet(O / "oracle_day.parquet").set_index("date")


def fp(q, side):
    e = Op[q]; up, dn = e * 1.01, e * 0.99
    for k in range(q, min(q + 48, len(TT))):
        if side == "long":
            if Lp[k] <= dn: return "adv"
            if Hp[k] >= up: return "fav"
        else:
            if Hp[k] >= up: return "adv"
            if Lp[k] <= dn: return "fav"
    return "none"


rng = np.random.default_rng(0)
mine2 = []
for d in DAYS:
    p = IX[d]; last = p + 287; tr = []
    for s in (0, 4, 8, 12, 16, 20):
        q = p + 12 * s; mv = Cp[q - 1] - Op[q - 48]
        if mv != 0:
            tr.append(("ENT_SLOT_FADE", q, "short" if mv > 0 else "long")); tr.append(("ENT_SLOT_FOLLOW", q, "long" if mv > 0 else "short"))
    seen = set()
    for (bt, side, ne, ci, s) in SW[d]:
        if (bt, side) in seen: continue
        seen.add((bt, side))
        sd = "long" if side == "bull" else "short"
        if p + 3 * (s + 1) <= last: tr.append(("ENT_SWEEP_ALL", p + 3 * (s + 1), sd))
        if ne and ci is not None and p + 3 * (ci + 1) <= last: tr.append(("ENT_SWEEP_CONF", p + 3 * (ci + 1), sd))
    hh, hl = max(Hp[p:p + 12]), min(Lp[p:p + 12])
    for k in range(p + 12, last):
        if Cp[k] > hh or Cp[k] < hl:
            sd = "long" if Cp[k] > hh else "short"
            tr.append(("ENT_H1_BREAK", k + 1, sd)); tr.append(("ENT_H1_BREAK_FADE", k + 1, "short" if sd == "long" else "long")); break
    dl = ds = False
    for k in range(p + 96, last):
        if not dl and Cp[k] < min(Lp[p:k]): tr.append(("ENT_EXT_FADE", k + 1, "long")); dl = True
        if not ds and Cp[k] > max(Hp[p:k]): tr.append(("ENT_EXT_FADE", k + 1, "short")); ds = True
    b = rng.integers(288, size=6); sdx = rng.integers(2, size=6)
    for bb, ss in zip(b, sdx):
        tr.append(("ENT_RANDOM", p + int(bb), "long" if ss == 0 else "short"))
    for mid, q, sd in tr:
        mine2.append((mid, d, TT[q], sd, fp(q, sd)))
c2 = pd.read_parquet(C / "c2_events.parquet")
th2 = [(r.trigger, r.date.to_pydatetime(), r.entry_time.to_pydatetime(), r.side, r.result) for r in c2.itertuples()]
check("C2a", sorted(mine2) == sorted(th2), f"C2 events recomputed: mine {len(mine2)}, stored {len(th2)}")
r2 = pd.read_csv(C / "c2_ranking.csv")
ok = True
for r in r2.itertuples():
    xs = [m for m in mine2 if m[0] == r.trigger]
    f = sum(m[4] == "fav" for m in xs); a = sum(m[4] == "adv" for m in xs)
    ok &= f == r.fav and a == r.adv and close(wil(f, f + a), r.wilson_lo)
check("C2b", ok and list(r2.wilson_lo) == sorted(r2.wilson_lo, reverse=True), "C2 ranking (fav/adv counts, Wilson, order)")

# ---- C3 ----
RS = {"R05": 0.005, "R08": 0.008, "R12": 0.012}
GE = {"G12": (1.0, 2.0), "G11": (1.0, 1.0), "G21": (2.0, 1.0), "G051": (0.5, 1.0), "G1N": (1.0, None)}
rr = np.random.default_rng(0)
RAND = {}
for d in DAYS:
    for s in (0, 4, 8, 12, 16, 20):
        RAND[(d, s)] = "long" if rr.integers(2) == 0 else "short"


def win(q, side, R, tpm, slm):
    e = Op[q]
    tp = e * (1 + tpm * R) if side == "long" else e * (1 - tpm * R)
    sl = None if slm is None else (e * (1 - slm * R) if side == "long" else e * (1 + slm * R))
    for k in range(q, q + 48):
        o, h, l = Op[k], Hp[k], Lp[k]
        if side == "long":
            if sl is not None and (o <= sl): return o / e - 1
            if sl is not None and l <= sl: return sl / e - 1
            if o >= tp: return o / e - 1
            if h >= tp: return tp / e - 1
        else:
            if sl is not None and o >= sl: return 1 - o / e
            if sl is not None and h >= sl: return 1 - sl / e
            if o <= tp: return 1 - o / e
            if l <= tp: return 1 - tp / e
    return Cp[q + 47] / e - 1 if side == "long" else 1 - Cp[q + 47] / e


cfgs = [(dr, rid, gid, "FUT") for dr in ("L", "S", "FADE", "FOLLOW", "RAND") for rid in ("R05", "R08", "R12", "RVOL") for gid in GE] + \
       [("L", rid, gid, "SPOT") for rid in ("R05", "R08", "R12", "RVOL") for gid in GE]
mine3 = {}
for (dr, rid, gid, mode) in cfgs:
    c = CF if mode == "FUT" else CS
    tpm, slm = GE[gid]
    lst = []
    for d in DAYS:
        p = IX[d]; lv = LV[d]
        R = RS[rid] if rid != "RVOL" else 0.33 * (lv["pdh"] / lv["pdl"] - 1)
        for s in (0, 4, 8, 12, 16, 20):
            q = p + 12 * s
            if dr == "L": sd = "long"
            elif dr == "S": sd = "short"
            elif dr == "RAND": sd = RAND[(d, s)]
            else:
                mv = Cp[q - 1] - Op[q - 48]
                if mv == 0: continue
                sd = ("short" if mv > 0 else "long") if dr == "FADE" else ("long" if mv > 0 else "short")
            g = win(q, sd, R, tpm, slm)
            lst.append((d, s, sd, (g - 2 * c) * 100))
    mine3[f"{mode}|{dr}|{rid}|{gid}"] = lst
c3 = pd.read_parquet(C / "c3_trades.parquet")
c3["cfg"] = c3["mode"] + "|" + c3["dir"] + "|" + c3.rid + "|" + c3.gid
bad = 0
for cfg, g in c3.groupby("cfg", sort=False):
    m = mine3[cfg]
    if len(m) != len(g) or not all(a[0] == b.date and a[1] == b.slot and a[2] == b.side and close(a[3], b.net_pct, 1e-8) for a, b in zip(m, g.itertuples())):
        bad += 1
check("C3a", bad == 0 and set(mine3) == set(c3.cfg), f"C3 trades of {len(mine3)} configs recomputed ({sum(map(len, mine3.values()))} trades): {bad} configs differ")

S = pd.read_csv(C / "c3_ranking.csv")
bad = 0
for r in S.itertuples():
    m = mine3[r.cfg]
    daily = {d: 0.0 for d in DAYS}
    for a in m: daily[a[0]] += a[3]
    D = len(DAYS); mean = sum(daily.values()) / D
    weeks = {}
    for d, v in daily.items():
        k = tuple(d.isocalendar())[:2]; w = weeks.setdefault(k, [0.0, 0]); w[0] += v; w[1] += 1
    nw = len(weeks)
    se = math.sqrt(nw / (nw - 1) * sum((w[0] - mean * w[1]) ** 2 for w in weeks.values())) / D
    months = {}
    for d, v in daily.items(): months[d.strftime("%Y-%m")] = months.get(d.strftime("%Y-%m"), 0.0) + v
    mp = sum(1 for v in months.values() if v > 0)
    if not (close(mean, r.mean_net_day_pct, 1e-8) and close(mean - 1.96 * se, r.lb95, 1e-8) and mp == r.months_pos
            and close(sum(a[3] for a in m), r.total_net_pct, 1e-8) and len(m) == r.trades):
        bad += 1
check("C3b", bad == 0 and list(S.lb95) == sorted(S.lb95, reverse=True), f"C3 ranking: mean/day, weekly-cluster lb95, months+, totals ({bad} rows differ)")
dl = pd.read_parquet(C / "c3_daily.parquet")
check("C3c", len(dl) == 120 * 272 and dl.groupby("cfg").size().eq(272).all(), f"daily entries: {len(dl)} rows = 120 configs x 272 days (no day skipped)")
res = json.loads((C / "C_RESULTS.json").read_text(encoding="utf-8"))
F = S[S["mode"] == "FUT"]
sel = F[(F.lb95 > 0) & (F.months_pos >= 6)].head(3).cfg.tolist()
check("C3d", sel == res["partD_selected_by_rule"], f"Part D selection by the locked rule: {sel}")
src = (P / "src/research/oracle_9m_c.py").read_text(encoding="utf-8")
lits = re.findall(r"(?<![\w.])0\.0*(?:46|85|4|92|17|18|28|036|075)\b", src)
check("C4", not lits, f"no fee literal in Part C code (found {lits})")
print("\nRESULT:", "ALL PASS" if not FAIL else f"FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
