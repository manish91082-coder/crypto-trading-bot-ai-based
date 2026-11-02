"""Independent verifier of Part D (AMENDMENT_2_PART_D_PREREGISTERED.md, SHA 4c46612c...). Plain loops; imports nothing from src/research.
Recomputes the day set, every lead trade (FUT|RAND|R08|G12), daily / monthly / yearly sums, gates, and the C1 / C2 context rows."""
import csv
import gzip
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
O = P / "logs/oracle_9m_2026"
D_ = O / "part_d"
FAIL = []


def check(name, ok, msg=""):
    print(f"[{name} {'OK' if ok else 'FAIL'}] {msg}", flush=True)
    if not ok:
        FAIL.append(name)


def close(a, b, tol=1e-8):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


h = (O / "AMENDMENT_2_SHA256.txt").read_text().split()[0]
check("D0", hashlib.sha256((O / "AMENDMENT_2_PART_D_PREREGISTERED.md").read_bytes()).hexdigest() == h, "Amendment 2 matches its SHA")
fees = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
CF = fees["rules"]["paper_futures_taker_per_side"]

raw = {}
with gzip.open(P / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", "rt", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        t = datetime.strptime(r["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
        if datetime(2020, 1, 1) <= t <= datetime(2025, 12, 31, 23, 55):
            raw[t] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
BYDAY = {}
for t, v in raw.items():
    BYDAY.setdefault(datetime(t.year, t.month, t.day), {})[t] = v


def complete(d):
    return len(BYDAY.get(d, {})) == 288


manual = [datetime.strptime(x.strip(), "%Y-%m-%d") for x in (P / "logs/manual_day_study/selected_days.txt").read_text().splitlines()[1:] if x.strip()]
days = []
d = datetime(2020, 1, 8)
while d <= datetime(2025, 12, 31):
    if d not in manual and complete(d) and complete(d - timedelta(days=1)):
        days.append(d)
    d += timedelta(days=1)
check("D1", len(days) == 2146, f"Part D day set recomputed: {len(days)} days")


def bars(d):
    x = BYDAY[d]
    return [(t, *x[t]) for t in sorted(x)]


# lead: RAND sides, R 0.8%, TP 1R, SL 2R, 4h windows
rng = np.random.default_rng(0)
mine = []
for d in days:
    b = bars(d)
    for s in (0, 4, 8, 12, 16, 20):
        side = "long" if rng.integers(2) == 0 else "short"
        w = b[s * 12:s * 12 + 48]
        e = w[0][1]; R = 0.008
        tp = e * (1 + R) if side == "long" else e * (1 - R)
        sl = e * (1 - 2 * R) if side == "long" else e * (1 + 2 * R)
        g = None
        for (_, o, hh, ll, cc) in w:
            if side == "long":
                if o <= sl: g = o / e - 1; break
                if ll <= sl: g = sl / e - 1; break
                if o >= tp: g = o / e - 1; break
                if hh >= tp: g = tp / e - 1; break
            else:
                if o >= sl: g = 1 - o / e; break
                if hh >= sl: g = 1 - sl / e; break
                if o <= tp: g = 1 - o / e; break
                if ll <= tp: g = 1 - tp / e; break
        if g is None:
            g = w[-1][4] / e - 1 if side == "long" else 1 - w[-1][4] / e
        mine.append((d, s, side, (g - 2 * CF) * 100))
tr = pd.read_parquet(D_ / "d_trades.parquet")
ok = len(tr) == len(mine) and all(a[0] == r.date and a[1] == r.slot and a[2] == r.side and close(a[3], r.net_pct) for a, r in zip(mine, tr.itertuples()))
check("D2", ok, f"lead trades recomputed: mine {len(mine)}, stored {len(tr)}")

daily = {d: 0.0 for d in days}
for a in mine:
    daily[a[0]] += a[3]
N = len(days); m = sum(daily.values()) / N
weeks = {}
for d, v in daily.items():
    k = tuple(d.isocalendar())[:2]; w = weeks.setdefault(k, [0.0, 0]); w[0] += v; w[1] += 1
nw = len(weeks)
se = math.sqrt(nw / (nw - 1) * sum((w[0] - m * w[1]) ** 2 for w in weeks.values())) / N
months, years = {}, {}
for d, v in daily.items():
    months[d.strftime("%Y-%m")] = months.get(d.strftime("%Y-%m"), 0.0) + v
    years[d.year] = years.get(d.year, 0.0) + v
mp, yp = sum(v > 0 for v in months.values()), sum(v > 0 for v in years.values())
res = json.loads((D_ / "D_RESULTS.json").read_text(encoding="utf-8"))
L = res["lead"]
passes = (m - 1.96 * se > 0) and (mp / len(months) >= 0.6) and (yp >= 4)
check("D3", close(m, L["mean_net_day_pct"]) and close(m - 1.96 * se, L["lb95"]) and mp == L["months_pos"] and len(months) == L["months"]
      and yp == L["years_pos"] and passes == L["passes"],
      f"mean/day {m:.4f}, lb95 {m - 1.96 * se:.4f}, months+ {mp}/{len(months)}, years+ {yp}/6, passes {passes}")
dl = pd.read_parquet(D_ / "d_daily.parquet")
check("D4", len(dl) == N and all(close(daily[r.date.to_pydatetime()], r.net) for r in dl.itertuples()), f"daily entries {len(dl)} rows, every day, sums equal")
check("D5", all(close(years[int(k)], v, 1e-6) for k, v in res["yearly_net_pct"].items()), f"yearly sums: { {k: round(v, 2) for k, v in years.items()} }")


# C1 context: DIR_CLOSEPOS
def dhl(d):
    b = bars(d)
    return max(x[2] for x in b), min(x[3] for x in b), b[-1][4]


k1 = n1 = 0
for d in days:
    ph, pl, pc = dhl(d - timedelta(days=1))
    call = 1 if (pc - pl) / (ph - pl) > 0.5 else -1
    b = bars(d)
    tgt = (b[-1][4] > b[0][1]) - (b[-1][4] < b[0][1])
    if tgt == 0:
        continue
    n1 += 1; k1 += call == tgt
c1 = res["c1_context"][0]
check("D6", c1["calls"] == n1 and c1["hits"] == k1, f"DIR_CLOSEPOS on 2020-2025: {k1}/{n1} = {k1 / n1:.4f}")

# C2 context: ENT_SWEEP_ALL first passage +-1% in 4h (fav / adv counts)
seq = sorted(raw)
IX = {t: i for i, t in enumerate(seq)}
Hs = [raw[t][1] for t in seq]; Ls = [raw[t][2] for t in seq]; Os = [raw[t][0] for t in seq]
fav = adv = 0
for d in days:
    b = bars(d)
    x = [(b[3 * j][0], b[3 * j][1], max(q[2] for q in b[3 * j:3 * j + 3]), min(q[3] for q in b[3 * j:3 * j + 3]), b[3 * j + 2][4]) for j in range(96)]
    prev = [dhl(d - timedelta(days=k)) if (d - timedelta(days=k)) in BYDAY else None for k in range(1, 8)]
    pdh, pdl = prev[0][0], prev[0][1]
    d7h = max(p[0] for p in prev if p); d7l = min(p[1] for p in prev if p)
    for s in range(95):
        for bull in (True, False):
            a_, b_ = (x[s][3], x[s][4]) if bull else (x[s][4], x[s][2])
            lv = [k * 1000 for k in range(int(a_ // 1000), int(b_ // 1000) + 2) if a_ < k * 1000 < b_] + [v for v in (pdh, pdl, d7h, d7l) if a_ < v < b_]
            if not lv:
                continue
            q = IX[x[s + 1][0]]
            e = Os[q]; up, dn = e * 1.01, e * 0.99
            r = "none"
            for k in range(q, q + 48):
                if k >= len(seq) or seq[k] - seq[q] >= timedelta(hours=4):
                    break
                if bull:
                    if Ls[k] <= dn: r = "adv"; break
                    if Hs[k] >= up: r = "fav"; break
                else:
                    if Hs[k] >= up: r = "adv"; break
                    if Ls[k] <= dn: r = "fav"; break
            fav += r == "fav"; adv += r == "adv"
c2 = res["c2_context"][0]
check("D7", c2["fav"] == fav and c2["adv"] == adv, f"ENT_SWEEP_ALL on 2020-2025: fav {fav}, adv {adv}, p {fav / (fav + adv):.4f}")
print("\nRESULT:", "ALL PASS" if not FAIL else f"FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
