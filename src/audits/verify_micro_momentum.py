"""Independent verifier for the micro-momentum study (protocol §8, checks M1-M7).

Reads the Binance zips itself with zipfile + csv, builds its own second grid in array('d') and recomputes with plain loops.
Imports nothing from src/research/micro_momentum.py; pandas is used only to read the main script's outputs.
Run: python src/audits/verify_micro_momentum.py
"""
import csv, gzip, hashlib, io, json, math, zipfile
from array import array
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "micro_momentum_2026"
DATA = ROOT / "data" / "external" / "binance_1s"
WARM, TAIL, CAP = 3900, 601, 1800
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def close_enough(a, b, tol=1e-9):
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        return (a is None or math.isnan(a)) and (b is None or math.isnan(b))
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def month_bounds(month):
    y, m = int(month[:4]), int(month[5:7])
    s = int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp())
    e = int(datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=timezone.utc).timestamp())
    return s, e


class Grid:
    """Own second grid of one month: close (ffill), volume, taker; plus own 5m OHLC from the real rows."""

    def __init__(self, month):
        self.month = month
        self.start, end = month_bounds(month)
        self.N = N = end - self.start
        self.P = array("d", [float("nan")]) * N
        self.V = array("d", [0.0]) * N
        self.T = array("d", [0.0]) * N
        self.five = {}
        seen = bytearray(N)
        first_open = None
        with zipfile.ZipFile(DATA / "spot_1s" / f"BTCUSDT-1s-{month}.zip") as z:
            with z.open(z.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh, "ascii")):
                    if not row[0].isdigit():
                        continue
                    ot = int(row[0])
                    s = ot // 1_000_000 if ot > 10**14 else ot // 1000
                    i = s - self.start
                    if i < 0 or i >= N or seen[i]:
                        continue
                    seen[i] = 1
                    o, h, l, c, v, tb = float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]), float(row[9])
                    if first_open is None or i == 0:
                        first_open = o if first_open is None else first_open
                    self.P[i], self.V[i], self.T[i] = c, v, tb
                    b = i // 300
                    f = self.five.get(b)
                    if f is None:
                        self.five[b] = [i, o, h, l, i, c, v]
                    else:
                        if i < f[0]:
                            f[0], f[1] = i, o
                        f[2] = max(f[2], h)
                        f[3] = min(f[3], l)
                        if i > f[4]:
                            f[4], f[5] = i, c
                        f[6] += v
        if math.isnan(self.P[0]):
            self.P[0] = first_open
        for i in range(1, N):
            if math.isnan(self.P[i]):
                self.P[i] = self.P[i - 1]

    # ---- features by plain loops, at one second t
    def r(self, t, W):
        return self.P[t] / self.P[t - W] - 1

    def minrun(self, t, up):
        n = 0
        while n < 10 and t - 60 * (n + 1) >= 0:
            a, b = self.P[t - 60 * n], self.P[t - 60 * (n + 1)]
            if (a > b) if up else (a < b):
                n += 1
            else:
                break
        return n

    def rhythm(self, t, W):
        u = d = 0
        for s in range(t - W + 1, t + 1):
            x = self.P[s] - self.P[s - 1]
            u += x > 0
            d += x < 0
        return u / (u + d) if u + d else float("nan")

    def straight(self, t, W):
        path = sum(abs(self.P[s] - self.P[s - 1]) for s in range(t - W + 1, t + 1))
        return abs(self.P[t] - self.P[t - W]) / path if path > 0 else float("nan")

    def volr(self, t, W):
        vw = sum(self.V[t - W + 1:t + 1])
        prior = sum(self.V[t - W - 3600 + 1:t - W + 1])
        return vw / (W * prior / 3600) if prior > 0 else float("nan")

    def taker(self, t, W):
        vw = sum(self.V[t - W + 1:t + 1])
        return sum(self.T[t - W + 1:t + 1]) / vw if vw > 0 else float("nan")

    def fut(self, t, h):
        return self.P[t + 1 + h] / self.P[t + 1] - 1

    # ---- full-month signal arrays by rolling loops (for trades)
    def signal_arrays(self):
        N, P, V, T = self.N, self.P, self.V, self.T
        upmin = bytearray(N)
        dnmin = bytearray(N)
        for t in range(N):
            upmin[t] = self.minrun(t, True) if t >= 60 else 0
            dnmin[t] = self.minrun(t, False) if t >= 60 else 0
        volr60 = array("d", [float("nan")]) * N
        tak60 = array("d", [float("nan")]) * N
        rh60 = array("d", [float("nan")]) * N
        vw = sum(V[1:61])            # window (t-60, t] for t = 60
        tw = sum(T[1:61])
        pr = 0.0
        u = d = 0
        for s in range(1, 61):
            x = P[s] - P[s - 1]
            u += x > 0
            d += x < 0
        for t in range(60, N):
            if t > 60:
                vw += V[t] - V[t - 60]
                tw += T[t] - T[t - 60]
                x = P[t] - P[t - 1]
                u += x > 0
                d += x < 0
                y = P[t - 60] - P[t - 61]
                u -= y > 0
                d -= y < 0
            if t >= 3660:
                if t == 3660:
                    pr = sum(V[1:3601])  # (t-60-3600, t-60]
                else:
                    pr += V[t - 60] - V[t - 3660]
                volr60[t] = vw / (60 * pr / 3600) if pr > 0 else float("nan")
            tak60[t] = tw / vw if vw > 0 else float("nan")
            rh60[t] = u / (u + d) if u + d else float("nan")
        return upmin, dnmin, volr60, tak60, rh60


def parse_cfg(name):
    a = name.split("_")
    return int(a[0][1:]), float(a[1][1:]), float(a[2][1:]), a[3]


def own_trades(g, arrs, name, L=1):
    upmin, dnmin, volr60, tak60, rh60 = arrs
    Nn, k, s, xn = parse_cfg(name)
    N = g.N

    def sig(t):
        return upmin[t] >= Nn and volr60[t] >= k and tak60[t] >= s   # NaN compares False

    def xsig(t):
        return dnmin[t] >= 1 and rh60[t] < 0.5 and volr60[t] >= 1

    trades = []
    prev = sig(WARM - 1)
    t = WARM
    pos = None
    last_exit = -1
    while t < N:
        cur = sig(t)
        if pos is None and cur and not prev and t > last_exit:
            e = t + L
            if e > N - 1:
                break
            if xn == "XU":
                x = None
                for tt in range(e + 1, min(e + CAP, N - 1) + 1):
                    if xsig(tt):
                        x = min(tt + L, e + CAP)
                        break
                if x is None:
                    x = e + CAP
            else:
                x = e + int(xn[2:])
            forced = x > N - 1
            x = min(x, N - 1)
            trades.append((e, x, forced))
            last_exit = x
            # skip to x; the start test at x+1 needs sig(x)
            if x + 1 >= N:
                break
            prev = sig(x)
            t = x + 1
            continue
        prev = cur
        t += 1
    return trades


def main():
    lock = (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0]
    check("M1 protocol SHA", sha(OUT / "MICRO_MOMENTUM_PROTOCOL_PREREGISTERED.md") == lock, lock[:12])
    man = list(csv.DictReader(open(DATA / "MANIFEST.csv")))
    ok = all(r["checksum_ok"] == "True" and sha(DATA / ("spot_1s" if "/spot/" in r["key"] else "futures_1m") / r["key"].rsplit("/", 1)[1]) == r["binance_checksum"] for r in man)
    check("M1 downloads equal Binance CHECKSUM", ok and len(man) == 18, f"{len(man)} files")
    good = True
    for line in (OUT / "OUTPUT_SHA256.txt").read_text().splitlines():
        h, f = line.split()
        good &= sha(OUT / f) == h
    check("M1 output SHAs", good)
    fees = json.loads((ROOT / "deploy" / "fees.json").read_text())
    cf = fees["rules"]["paper_futures_taker_per_side"]

    g = Grid("2026-01")
    # M2 features at the sample seconds
    smp = pd.read_parquet(OUT / "features_sample_disc.parquet")
    bad = 0
    for r in smp.itertuples(index=False):
        t = int(r.sec)
        mine = {"R_60": g.r(t, 60), "R_300": g.r(t, 300), "UPMIN": float(g.minrun(t, True)), "DOWNMIN": float(g.minrun(t, False)),
                "RHYTHM_60": g.rhythm(t, 60), "STRAIGHT_60": g.straight(t, 60), "VOLR_60": g.volr(t, 60),
                "TAKER_60": g.taker(t, 60), "F_60": g.fut(t, 60), "F_300": g.fut(t, 300)}
        for k_, v in mine.items():
            if not close_enough(v, float(getattr(r, k_)), 1e-8):
                bad += 1
    check("M2 DISC features at sample seconds", bad == 0 and len(smp) == 3000, f"{len(smp)} seconds x 10 values, {bad} mismatches")

    # M3 5m OHLC vs file
    five = {}
    with gzip.open(ROOT / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", "rt") as f:
        rd = csv.reader(f)
        next(rd)
        for row in rd:
            if row[0].startswith("2026-01"):
                ts = int(datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
                five[(ts - g.start) // 300] = tuple(float(x) for x in row[1:6])
    mism = 0
    for b, f in g.five.items():
        ref = five.get(b)
        if ref is None or not all(close_enough(a, c_) for a, c_ in zip((f[1], f[2], f[3], f[5]), ref[:4])):
            mism += 1
    qc = pd.read_csv(OUT / "qc_months.csv").set_index("month")
    check("M3 DISC 5m OHLC vs file", mism == int(qc.loc["2026-01", "five_min_ohlc_mismatch"]) and len(g.five) == len(five),
          f"{len(g.five)} bars, mismatches mine {mism} / main {int(qc.loc['2026-01', 'five_min_ohlc_mismatch'])}")

    # M5 A3 UPMIN counts and mean F_60
    pa = json.loads((OUT / "partA_disc.json").read_text())
    cnt = [0] * 6
    sm = [0.0] * 6
    for t in range(WARM, g.N - TAIL):
        n = g.minrun(t, True)
        j = min(n, 5)
        cnt[j] += 1
        sm[j] += g.fut(t, 60)
    ok = True
    for j in range(6):
        key = str(j) if j < 5 else "5+"
        cell = pa["A3"]["UPMIN"][key]
        ok &= cell["n_seconds"] == cnt[j] and close_enough(sm[j] / cnt[j], cell["60"]["mean"], 1e-7)
    check("M5 DISC A3 UPMIN counts and mean F_60", ok, f"counts {cnt}")

    # M4 trades of 6 configs on DISC
    M = pd.read_csv(OUT / "metrics.csv")
    md = M[(M.period == "DISC") & (M.cost == "fut") & (M.n > 0)].sort_values("mean_net")
    cfgs = list(dict.fromkeys([md.iloc[-1]["config"], md.iloc[0]["config"], "N1_k1_s0_XT60", "N1_k1_s0_XU",
                               "N3_k2_s0.6_XT60", "N3_k2_s0.6_XU"]))
    arrs = g.signal_arrays()
    TD = pd.read_parquet(OUT / "trades_DISC.parquet")
    for name in cfgs:
        mine = own_trades(g, arrs, name)
        tm = TD[TD.config == name].sort_values("entry_sec")
        ok = len(mine) == len(tm)
        if ok:
            for (e, x, fo), r in zip(mine, tm.itertuples(index=False)):
                ok &= e == r.entry_sec and x == r.exit_sec and fo == bool(r.forced)
                ok &= g.P[e] == r.entry_px and g.P[x] == r.exit_px
                ok &= abs((g.P[x] / g.P[e] - 1 - 2 * cf) - (r.gross - 2 * cf)) <= 1e-12
        check(f"M4 DISC trades {name}", ok, f"{len(mine)} mine / {len(tm)} main")
    del g, arrs

    # M6 VAL count and sum net for the same configs
    sums = {n: [0, 0.0] for n in cfgs}
    for month in ("2026-02", "2026-03", "2026-04", "2026-05"):
        gv = Grid(month)
        av = gv.signal_arrays()
        for name in cfgs:
            tr = own_trades(gv, av, name)
            sums[name][0] += len(tr)
            sums[name][1] += sum(gv.P[x] / gv.P[e] - 1 - 2 * cf for e, x, _ in tr)
        del gv, av
    mv = M[(M.period == "VAL") & (M.cost == "fut")].set_index("config")
    for name in cfgs:
        ok = sums[name][0] == int(mv.loc[name, "n"]) and close_enough(sums[name][1], float(mv.loc[name, "sum_net"]), 1e-9)
        check(f"M6 VAL count+sum {name}", ok, f"{sums[name][0]} trades, sum net {sums[name][1]:.6f}")

    # M7 shortlist / decision per §7
    dec = json.loads((OUT / "decision.json").read_text())
    sl = md[(md.n >= 30) & (md.mean_net > 0) & (md.ci95_lo > -0.0005)].sort_values("mean_net", ascending=False).head(10)
    ok = list(sl["config"]) == dec["shortlist"]
    if dec["shortlist"]:
        rc = pd.read_csv(OUT / "random_control.csv").set_index("config")
        for v in dec["val"]:
            exp = v["val_mean_net"] > 0 and v["val_bonf_lo"] > 0 and v["rand_p"] < 0.05 and v["val_months_pos"] >= 3
            ok &= exp == v["pass"] and close_enough(v["rand_p"], float(rc.loc[v["config"], "p"]))
            ok &= close_enough(v["val_mean_net"], float(mv.loc[v["config"], "mean_net"]))
        passed = [v for v in dec["val"] if v["pass"]]
        ok &= dec["pick"] == (max(passed, key=lambda v: v["val_mean_net"])["config"] if passed else None)
    else:
        ok &= dec["pick"] is None and dec["val"] == []
    check("M7 shortlist and decision follow §7", ok, f"shortlist {dec['shortlist']} pick {dec['pick']}")

    nf = sum(1 for _, ok in results if not ok)
    print(f"\nTOTAL {len(results)} checks, {len(results) - nf} PASS, {nf} FAIL -> {'ALL PASS' if nf == 0 else 'FAILURES'}")


if __name__ == "__main__":
    main()
