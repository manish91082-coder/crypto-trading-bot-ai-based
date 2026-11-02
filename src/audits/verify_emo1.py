"""Independent verifier of the EMO-1 panel and portfolio (protocol §S "Verifier"). Usage: python src/audits/verify_emo1.py [dev|holdout]
V1 300 random (t, symbol) rows: every feature, the next return and the funding recomputed from the raw zips by a separate,
   row-by-row method (no shared code with the study's vectorized build) -> |diff| <= 1e-9 (relative for ratios)
V2 the panel SHA == the one in the report; V3 30 random rebalances: weights, hedge and period return recomputed -> 1e-9
V4 the point-in-time rules: no feature uses data at or after t (checked on the V1 rows from the raw timestamps)"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
RAW = R_ / "data" / "emotion" / "emo1_raw"
OUT = R_ / "data" / "emotion" / "emo1"
LOG = R_ / "logs" / "emotion"
tag = sys.argv[1] if len(sys.argv) > 1 else "dev"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def csv_rows(z):
    with zipfile.ZipFile(z) as f:
        return [l.split(",") for l in f.read(f.namelist()[0]).decode().splitlines() if l and l[0].isdigit()]


def fl(x):
    try:
        v = float(x)
        return v if v > 0 else np.nan                                       # same missing-value rule as the study (<= 0 -> missing)
    except ValueError:
        return np.nan


def metric_rows(s, day_from, day_to):
    out = []
    for d in pd.date_range(day_from.normalize(), day_to.normalize()):
        z = RAW / "daily" / "metrics" / s / f"{s}-metrics-{d.date()}.zip"
        if z.exists():
            out += [(pd.Timestamp(r[0]), fl(r[3]), fl(r[5]), fl(r[6]), fl(r[7])) for r in csv_rows(z)]
    return sorted(out)


def kl_rows(s, iv, t0, t1):
    out = {}
    for m in pd.period_range(t0, t1, freq="M"):
        z = RAW / "monthly" / "klines" / s / iv / f"{s}-{iv}-{m}.zip"
        if z.exists():
            for r in csv_rows(z):
                out[pd.Timestamp(int(r[0]), unit="ms")] = [float(x) for x in r[1:8]]
    return out


def fund_rows(s, t0, t1):
    out = []
    for m in pd.period_range(t0, t1, freq="M"):
        z = RAW / "monthly" / "fundingRate" / s / f"{s}-fundingRate-{m}.zip"
        if z.exists():
            out += [(pd.Timestamp(int(r[0]), unit="ms"), float(r[2])) for r in csv_rows(z)]
    return out


def recompute(s, t):
    M = metric_rows(s, t - pd.Timedelta(days=4), t)
    before = [x for x in M if x[0] < t]
    last = before[-1]
    def oiv_before(x):
        b = [y for y in before if y[0] < x]
        return b[-1][1] if b else np.nan
    tk = [np.log(x[4]) for x in before if x[0] > t - pd.Timedelta(days=1) and x[0] <= t - pd.Timedelta(minutes=1) and np.isfinite(np.log(x[4]))]
    f = dict(oi_1d=last[1] / oiv_before(t - pd.Timedelta(days=1)) - 1, oi_3d=last[1] / oiv_before(t - pd.Timedelta(days=3)) - 1,
             retail=np.log(last[3]), smart=np.log(last[2]) - np.log(last[3]), taker_1d=np.mean(tk) if len(tk) >= 200 else np.nan)
    F = fund_rows(s, t - pd.Timedelta(days=4), t + pd.Timedelta(days=2))
    fz = [v for ts, v in F if t - pd.Timedelta(days=3) < ts <= t]
    f["fund_3d"] = np.mean(fz) if fz else np.nan
    K = kl_rows(s, "1h", t - pd.Timedelta(days=9), t + pd.Timedelta(days=2))
    bars = [K[k] for k in sorted(K) if k <= t - pd.Timedelta(hours=1)]
    b24 = bars[-24:]
    w = [((h - l) - abs(c - o)) / (h - l) for o, h, l, c, *_ in b24 if h > l]
    f["wick_1d"] = np.mean(w)
    f["qv_surprise"] = sum(b[6] for b in bars[-24:]) / sum(b[6] for b in bars[-48:-24]) - 1
    lc = np.log([b[3] for b in bars[-168:]])
    lr = np.diff(lc)
    f["rv_change"] = np.std(lr[-24:], ddof=1) / np.std(lr[-167:], ddof=1) - 1
    o1, o5 = K[t + pd.Timedelta(hours=1)][0], K[t + pd.Timedelta(hours=5)][0]
    f["ret"] = o5 / o1 - 1
    f["fund_next"] = sum(v for ts, v in F if t + pd.Timedelta(hours=1) < ts <= t + pd.Timedelta(hours=5))
    used = [k for k in sorted(K) if k <= t - pd.Timedelta(hours=1)][-168:]
    pit = last[0] < t and max(used) <= t - pd.Timedelta(hours=1)
    return f, pit


rep = json.loads((LOG / f"EMO1_{tag.upper()}_REPORT.json").read_text())
P = pd.read_parquet(OUT / "panel.parquet")
win = (pd.Timestamp(rep["window_dates"][0]), pd.Timestamp(rep["window_dates"][1]))
P = P[(P.t >= win[0]) & (P.t <= win[1])]
ok("V2", hashlib.sha256((OUT / "panel.parquet").read_bytes()).hexdigest() == rep["panel_sha256"], "panel SHA == report")
rng = np.random.default_rng(2026)
S = P.dropna(subset=["oi_1d", "retail", "taker_1d", "fund_3d", "ret", "wick_1d", "rv_change"]).sample(300, random_state=2026)
bad, pit_bad = [], []
for r in S.itertuples():
    f, pit = recompute(r.sym, r.t)
    for k, v in f.items():
        a = getattr(r, k)
        if not (np.isclose(a, v, rtol=1e-9, atol=1e-12) or (np.isnan(a) and np.isnan(v))):
            bad.append((str(r.t), r.sym, k, a, v))
    if not pit:
        pit_bad.append((str(r.t), r.sym))
ok("V1", not bad, f"300 rows x 13 values recomputed row by row from the raw zips: mismatches {len(bad)} {bad[:3]}")
ok("V4", not pit_bad, f"point in time (last metrics snapshot < t, bars closed by t): violations {pit_bad[:3]}")
# V3: rebalance math on 30 random rebalances (weights from ranks, hedge, gross 1, period return)
reb = pd.read_csv(OUT / f"{tag}_rebalances_P.csv", parse_dates=["t"]).set_index("t")
sys.path.insert(0, str(R_ / "src" / "research"))
kb = {}
for m in pd.period_range(win[0], win[1] + pd.Timedelta(days=2), freq="M"):
    z = RAW / "monthly" / "klines" / "BTCUSDT" / "1h" / f"BTCUSDT-1h-{m}.zip"
    if z.exists():
        kb.update({pd.Timestamp(int(x[0]), unit="ms"): float(x[1]) for x in csv_rows(z)})
ts_all = sorted(reb.index)
pick = sorted(rng.choice(len(ts_all) - 1, 30, replace=False) + 1)
bad3 = []
cols = ["oi_1d", "retail", "taker_1d", "fund_3d"]
def weights(t):
    g = P[P.t == t].dropna(subset=cols + ["ret", "fund_next", "beta"])
    sc = g[cols].rank(pct=True).mean(axis=1).values
    q = max(1, int(len(g) * 0.2)); o = np.argsort(sc, kind="stable")
    w = np.zeros(len(g)); w[o[:q]] = 0.5 / q; w[o[-q:]] = -0.5 / q
    hd = -float(np.sum(w * g.beta.values)); gr = np.abs(w).sum() + abs(hd)
    return g, w / gr, hd / gr
for i in pick:
    t, tp = ts_all[i], ts_all[i - 1]
    g, w, hd = weights(t)
    gp, wp, hp = weights(tp)
    new = dict(zip(g.sym, w)); new["__BTC"] = hd
    old = dict(zip(gp.sym, wp)); old["__BTC"] = hp
    turn = sum(abs(new.get(k, 0) - old.get(k, 0)) for k in new.keys() | old.keys())
    rb = kb[t + pd.Timedelta(hours=5)] / kb[t + pd.Timedelta(hours=1)] - 1
    r = float(np.sum(w * g.ret.values) + hd * rb - np.sum(w * g.fund_next.values) - 0.00054 * turn)
    if not np.isclose(r, reb.loc[t, "r"], rtol=1e-9, atol=1e-12) or abs(np.abs(w).sum() + abs(hd) - 1) > 1e-12:
        bad3.append((str(t), r, reb.loc[t, "r"]))
ok("V3", not bad3, f"30 random rebalances: weights / hedge / gross 1 / period return recomputed: mismatches {bad3[:3]}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
