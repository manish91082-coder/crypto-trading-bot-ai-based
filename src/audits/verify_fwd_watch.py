"""Independent verifier of FWD-WATCH (logs/fwd_watch/FWD_WATCH_PROTOCOL_PREREGISTERED.md). Imports nothing from src/forward or src/research.
V1 protocol + seed SHAs; V2 every daily zip passes its stored checksum record and the file SHA; V3 FW1 forward trades recomputed with
plain loops (own 4h aggregation, Wilder RSI, streak, percent rank, 5m mapping, reversal simulation, funding); V4 FW2 forward trades
recomputed (own features, percentiles, score, XM fills); V5 daily / monthly tables. Usage: python verify_fwd_watch.py [root]"""
import bisect
import csv
import hashlib
import io
import json
import math
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
ROOT = P / (sys.argv[1] if len(sys.argv) > 1 else "data/fwd_watch")
FAIL = []


def check(n, ok, msg=""):
    print(f"[{n} {'PASS' if ok else 'FAIL'}] {msg}", flush=True)
    if not ok:
        FAIL.append(n)


def h(b):
    return hashlib.sha256(b).hexdigest()


pr = P / "logs/fwd_watch/FWD_WATCH_PROTOCOL_PREREGISTERED.md"
check("V1a", h(pr.read_bytes()) == (P / "logs/fwd_watch/PROTOCOL_SHA256.txt").read_text().split()[0], "protocol matches its lock")
man = list(csv.DictReader(open(ROOT / "SEED_MANIFEST.csv", encoding="utf-8")))
check("V1b", all(h((ROOT / "seed" / r["file"]).read_bytes()) == r["sha256"] for r in man) and len(man) == 4, "seed files match SEED_MANIFEST")
fees = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
FUT_RT = 2 * fees["rules"]["paper_futures_taker_per_side"]; MK = fees["futures_usdm"]["bnb_maker"]; TK = fees["rules"]["paper_futures_taker_per_side"]
bad = []
for ds in ("spot", "fut", "metrics"):
    mf = ROOT / "daily" / ds / "MANIFEST.csv"
    rows = list(csv.DictReader(open(mf, encoding="utf-8"))) if mf.exists() else []
    for r in rows:
        f = ROOT / "daily" / ds / r["key"].rsplit("/", 1)[1]
        if r["checksum_ok"] != "True" or not f.exists() or h(f.read_bytes()) != r["sha256"]:
            bad.append(r["key"])
    files = {f.name for f in (ROOT / "daily" / ds).glob("*.zip")}
    if files != {r["key"].rsplit("/", 1)[1] for r in rows if r["checksum_ok"] == "True"}:
        bad.append(f"{ds}: files on disk != manifest")
check("V2", not bad, f"daily zips: checksum record + file SHA; problems {bad[:5]}")

SEED_END = datetime(2026, 9, 30, 23, 55)
FWD0 = datetime(2026, 10, 1)
M5 = timedelta(minutes=5)


def zrows(f):
    z = zipfile.ZipFile(f); raw = z.read(z.namelist()[0]).decode().splitlines()
    if raw and not raw[0][:1].isdigit():
        hdr = raw[0].split(","); raw = raw[1:]
    else:
        hdr = None
    return hdr, [l.split(",") for l in raw if l]


def ms(v):
    v = int(v)
    return datetime(1970, 1, 1) + (timedelta(microseconds=v) if v > 10 ** 14 else timedelta(milliseconds=v))


# spot bars dict t -> (o,h,l,c,v,tbb)
spot = {}
sd = pd.read_csv(ROOT / "seed/spot5m_seed.csv.gz", usecols=["timestamp", "open", "high", "low", "close", "volume", "taker_buy_base"])
for r in sd.itertuples(index=False):
    t = datetime.strptime(r.timestamp[:19], "%Y-%m-%d %H:%M:%S")
    if t <= SEED_END and t not in spot:
        spot[t] = (r.open, r.high, r.low, r.close, r.volume, r.taker_buy_base)
for f in sorted((ROOT / "daily/spot").glob("*.zip")):
    _, rows = zrows(f)
    for x in rows:
        t = ms(x[0])
        if t > SEED_END and t not in spot:
            spot[t] = (float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5]), float(x[9]))
fut = {}
fp = pd.read_parquet(ROOT / "seed/fut5m_seed.parquet")
for t, o, hh, ll, c in zip(fp.time, fp.open, fp.high, fp.low, fp.close):
    if t <= SEED_END:
        fut[t.to_pydatetime()] = (o, hh, ll, c)
for f in sorted((ROOT / "daily/fut").glob("*.zip")):
    _, rows = zrows(f)
    for x in rows:
        t = ms(x[0])
        if t > SEED_END and t not in fut:
            fut[t] = (float(x[1]), float(x[2]), float(x[3]), float(x[4]))
met = []
mp = pd.read_parquet(ROOT / "seed/metrics5m_seed.parquet")
met = [(t.to_pydatetime(), v) for t, v in zip(mp.time, mp.sum_open_interest_value) if t <= SEED_END]
for f in sorted((ROOT / "daily/metrics").glob("*.zip")):
    hdr, rows = zrows(f)
    ci, vi = hdr.index("create_time"), hdr.index("sum_open_interest_value")
    for x in rows:
        t = datetime.strptime(x[ci][:19], "%Y-%m-%d %H:%M:%S")
        if t > SEED_END:
            try:
                met.append((t, float(x[vi])))
            except ValueError:
                met.append((t, float("nan")))
met = sorted({t: v for t, v in met}.items())
fu = pd.read_parquet(ROOT / "seed/funding_seed.parquet")
fund = [(t.to_pydatetime(), r) for t, r in zip(fu.time, fu.funding_rate)]
api = ROOT / "funding_api.json"
if api.exists():
    last = max(t for t, _ in fund)
    fund += [(ms(x["fundingTime"]), float(x["fundingRate"])) for x in json.loads(api.read_text(encoding="utf-8")) if ms(x["fundingTime"]) > last]
fund = sorted(dict(fund).items())

# ---------------- FW1 ----------------
last_spot = max(spot)
grid = []
t = datetime(2020, 1, 1)
while t <= last_spot:
    grid.append(t); t += M5
N = len(grid)
IX = {t: i for i, t in enumerate(grid)}
O = [spot[t][0] if t in spot else float("nan") for t in grid]
Cc = [spot[t][3] if t in spot else float("nan") for t in grid]
# 4h aggregation, label = right edge, bucket [T-4h, T)
b4 = {}
for t in grid:
    if t not in spot:
        continue
    T = datetime(t.year, t.month, t.day, (t.hour // 4) * 4) + timedelta(hours=4)
    b4.setdefault(T, []).append(spot[t][3])
labels = sorted(b4)
c4 = [b4[T][-1] for T in labels]


def wilder_ser(x, n):
    a = 1 / n; out = [float("nan")] * len(x); y = None; cnt = 0
    for i, v in enumerate(x):
        if v != v:
            continue
        y = v if y is None else (1 - a) * y + a * v
        cnt += 1
        if cnt >= n:
            out[i] = y
    return out


def rsi_ser(c, n):
    dl = [float("nan")] + [c[i] - c[i - 1] for i in range(1, len(c))]
    up = [max(v, 0.0) if v == v else float("nan") for v in dl]
    dn = [max(-v, 0.0) if v == v else float("nan") for v in dl]
    au, ad = wilder_ser(up, n), wilder_ser(dn, n)
    out = []
    for u, d in zip(au, ad):
        if u != u or d != d:
            out.append(float("nan"))
        elif d == 0:
            out.append(100.0 if u > 0 else float("nan"))
        else:
            out.append(100 - 100 / (1 + u / d))
    return out


st = [0.0] * len(c4)
for i in range(1, len(c4)):
    dc = c4[i] - c4[i - 1]
    st[i] = (st[i - 1] + 1 if st[i - 1] > 0 else 1) if dc > 0 else ((st[i - 1] - 1 if st[i - 1] < 0 else -1) if dc < 0 else 0)
roc = [float("nan")] + [c4[i] / c4[i - 1] - 1 for i in range(1, len(c4))]
prk = [float("nan")] * len(c4)
for i in range(99, len(c4)):
    w = roc[i - 99:i + 1]
    if any(v != v for v in w):
        continue
    prk[i] = sum(1 for v in w[:-1] if v < w[-1]) / 99 * 100
r3, r2 = rsi_ser(c4, 3), rsi_ser(st, 2)
sig4 = []
for a, b, c in zip(r3, r2, prk):
    v = (a + b + c) / 3 if (a == a and b == b and c == c) else float("nan")
    sig4.append(-(1 if v < 10 else (-1 if v > 90 else 0)) if v == v else 0)       # follow = -fade
dirn = [0] * N
j = -1
for i, t in enumerate(grid):
    while j + 1 < len(labels) and labels[j + 1] <= t + M5:
        j += 1
    dirn[i] = sig4[j] if j >= 0 else 0
fts = [t for t, _ in fund]; cs = [0.0]
for _, r in fund:
    cs.append(cs[-1] + r)
cumf = [cs[bisect.bisect_left(fts, t + M5)] for t in grid]
Cf = []
lastc = float("nan")
for v in Cc:
    lastc = v if v == v else lastc
    Cf.append(lastc)
i0 = IX[FWD0] if FWD0 in IX else N
mine1 = []
free = i0
for t_ in range(i0, N - 1):
    if dirn[t_] == 0 or t_ < free:
        continue
    dd = dirn[t_]
    e = O[t_ + 1]
    if e != e:
        continue
    k = next((q for q in range(t_ + 1, N) if dirn[q] == -dd), N)
    if k < N and k <= t_ + 2016:
        xb = k + 1 if k + 1 < N else k
        px = O[xb] if O[xb] == O[xb] else Cf[k]
        ex, closed = k, k + 1 < N
    else:
        ex = min(N - 1, t_ + 2016); px = Cf[ex]; closed = t_ + 2016 <= N - 1
    g = dd * (px / e - 1)
    net = g - FUT_RT - (cumf[ex] - cumf[t_]) * dd
    mine1.append((grid[t_], dd, net * 100, closed))
    free = ex

# ---------------- FW2 ----------------
mt_t = [t for t, _ in met]; mt_v = [v for _, v in met]


def fclose_at(t):
    v = fut.get(t - M5)
    return v[3] if v else float("nan")


def oi_at(t):
    i = bisect.bisect_right(mt_t, t - M5) - 1
    return mt_v[i] if i >= 0 else float("nan")


end = min(max(fut), last_spot)
end = datetime(end.year, end.month, end.day, end.hour)
samples = []
t = datetime(2020, 9, 1)
while t <= end:
    if t.hour % 4 == 0:
        px = fclose_at(t); o0, o24 = oi_at(t), oi_at(t - timedelta(hours=24))
        f1 = math.log(o0 / o24) if (o0 == o0 and o24 == o24 and o0 > 0 and o24 > 0) else float("nan")
        sb = [spot.get(t - k * M5) for k in range(1, 13)]
        f2 = sum(b[5] for b in sb) / sum(b[4] for b in sb) - 0.5 if all(sb) else float("nan")
        p24 = fclose_at(t - timedelta(hours=24))
        f3 = px / p24 - 1 if (px == px and p24 == p24) else float("nan")
        samples.append((t, [f1, f2, f3]))
    t += timedelta(hours=1)
pcts = []
for fi in range(3):
    ser = [(t, v[fi]) for t, v in samples if v[fi] == v[fi]]
    tt = np.array([s[0] for s in ser], dtype="datetime64[us]"); xx = np.array([s[1] for s in ser])
    d = {}
    for i in range(len(ser)):
        lo = int(np.searchsorted(tt, tt[i] - np.timedelta64(90, "D"), side="left"))
        past = xx[lo:i]
        if len(past) >= 30:
            d[ser[i][0]] = float((past < xx[i]).sum()) / len(past)
    pcts.append(d)
BETA = [-8.449163524227228e-05, -0.00039878595881818915, -0.00011428329656457703]; THR = 0.00021482419836031948
mine2 = []
for t, _ in samples:
    if t < FWD0 or not all(t in d for d in pcts):
        continue
    u = [pcts[i][t] - 0.5 for i in range(3)]
    pred = sum(a * b for a, b in zip(u, BETA))
    if abs(pred) < THR:
        continue
    sd_ = 1 if pred > 0 else -1
    te = t + timedelta(hours=4)
    if (te + 2 * M5) not in fut:
        mine2.append((t, sd_, None, False)); continue
    P_ = fut[t - M5][3]
    if not any((fut[t + k * M5][2] < P_) if sd_ > 0 else (fut[t + k * M5][1] > P_) for k in range(3)):
        continue
    Q = fut[te - M5][3]
    fill = any((fut[te + k * M5][1] > Q) if sd_ > 0 else (fut[te + k * M5][2] < Q) for k in range(3))
    x, xc = (Q, MK) if fill else (fut[te + 2 * M5][3], TK)
    mine2.append((t, sd_, (sd_ * (x / P_ - 1) - MK - xc) * 100, True))

# ---------------- compare ----------------
T = pd.read_csv(ROOT / "out/fw_trades_all.csv", parse_dates=["time"])


def same(cand, mine):
    g = T[T.cand == cand]
    if len(g) != len(mine):
        return False, f"{cand}: stored {len(g)}, mine {len(mine)}"
    for a, b in zip(mine, g.itertuples()):
        if a[0] != b.time.to_pydatetime() or a[1] != b.side or bool(a[3]) != bool(b.closed):
            return False, f"{cand}: mismatch at {a[0]}"
        if a[3] and abs(a[2] - b.net_pct) > 1e-9:
            return False, f"{cand}: net mismatch at {a[0]}"
    return True, f"{cand}: {len(mine)} trades ({sum(1 for m in mine if m[3])} closed)"


ok, msg = same("FW1", mine1); check("V3", ok, msg)
ok, msg = same("FW2", mine2); check("V4", ok, msg)
dl = pd.read_csv(ROOT / "out/fw_daily.csv", parse_dates=["date"])
tc = T[T.closed].copy()
tc["day"] = pd.to_datetime(tc.exit_time).dt.normalize()
good = True
for cand in ("FW1", "FW2"):
    s = tc[tc.cand == cand].groupby("day").net_pct.sum()
    g = dl[dl.cand == cand]
    good &= g.date.is_unique and g.date.min() == pd.Timestamp(FWD0) and all(abs(s.get(r.date, 0.0) - r.net_pct) < 1e-9 for r in g.itertuples())
    good &= (g.date.diff().dropna() == pd.Timedelta(days=1)).all()
check("V5", good, f"daily tables: every day from 2026-10-01 present, sums equal ({len(dl)} rows)")
print("TOTAL", 7, "checks, FAIL", len(FAIL))
sys.exit(1 if FAIL else 0)
