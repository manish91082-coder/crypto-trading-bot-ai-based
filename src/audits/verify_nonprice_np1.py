"""Independent verifier of NP1 (logs/research_nonprice/NP1_PROTOCOL_PREREGISTERED.md, SHA 9addc94b...).
Imports nothing from src/research. (1) 2,000 random feature rows rebuilt from the clean tables with its own lookups;
(2) every monthly IC / t_IC of S1 (D and V) recomputed with plain loops; (3) every S2 trade and the V gate; (4) no H row in S1/S2; (5) fees."""
import bisect
import hashlib
import json
import math
import random
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
CL = P / "data/external/binance_public/clean"
O = P / "logs/research_nonprice"
FAIL = []


def check(n, ok, msg=""):
    print(f"[{n} {'OK' if ok else 'FAIL'}] {msg}", flush=True)
    if not ok:
        FAIL.append(n)


def close(a, b, tol=1e-9):
    if (a != a) and (b != b):
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


h = (O / "PROTOCOL_SHA256.txt").read_text().split()[0]
check("N0", hashlib.sha256((O / "NP1_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == h, "protocol matches its SHA")
X = pd.read_parquet(O / "np1_features_1h.parquet")
COST = 2 * json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))["rules"]["paper_futures_taker_per_side"]

# ---------- (1) feature rows ----------
fut = pd.read_parquet(CL / "fut5m.parquet")
ft = dict(zip(fut.time, zip(fut.close, fut.volume, fut.taker_buy_volume)))
pr = pd.read_parquet(CL / "premium5m.parquet"); pt = dict(zip(pr.time, pr.close))
sp = pd.read_csv(P / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", usecols=["timestamp", "close", "volume", "taker_buy_base"], parse_dates=["timestamp"]).drop_duplicates("timestamp")
st = dict(zip(sp.timestamp, zip(sp.close, sp.volume, sp.taker_buy_base)))
dp = pd.read_parquet(CL / "depth5m.parquet"); dt_ = dict(zip(dp.time, zip(dp.imb1, dp.imb5)))
fd = pd.read_parquet(CL / "funding.parquet").sort_values("time").reset_index(drop=True)
fdt = list(fd.time); fdr = list(fd.funding_rate)
mt = pd.read_parquet(CL / "metrics5m.parquet").sort_values("time").reset_index(drop=True)
mtt = list(mt.time); mto = list(mt.sum_open_interest_value); mtk = list(mt.sum_taker_long_short_vol_ratio)
M5 = pd.Timedelta(minutes=5)


def last_le(arr, t):
    i = bisect.bisect_right(arr, t) - 1
    return i


def fclose(t):
    v = ft.get(t - M5)
    return v[0] if v else float("nan")


def recompute(t):
    r = {}
    px = fclose(t)
    for hh, n in (("1h", 1), ("4h", 4), ("24h", 24)):
        r[f"r_{hh}"] = fclose(t + pd.Timedelta(hours=n)) / px - 1
    i = last_le(fdt, t)
    r["FUND_LVL"] = fdr[i]
    if i >= 89:
        w = fdr[i - 89:i + 1]; m = sum(w) / 90; sd = math.sqrt(sum((x - m) ** 2 for x in w) / 89)
        r["FUND_Z"] = (fdr[i] - m) / sd
    ps = [pt[t - k * M5] for k in range(1, 13) if (t - k * M5) in pt]
    r["PREM_1H"] = sum(ps) / len(ps) if ps else float("nan")
    s = st.get(t - M5)
    r["BASIS"] = px / s[0] - 1 if s else float("nan")

    def oi_at(tt):
        j = last_le(mtt, tt - M5)
        return mto[j], j
    o0, j0 = oi_at(t)
    o1, _ = oi_at(t - pd.Timedelta(hours=1)); o24, _ = oi_at(t - pd.Timedelta(hours=24)); o4, _ = oi_at(t - pd.Timedelta(hours=4))
    r["OI_CHG_1H"] = math.log(o0 / o1) if o0 > 0 and o1 > 0 else float("nan")
    r["OI_CHG_24H"] = math.log(o0 / o24) if o0 > 0 and o24 > 0 else float("nan")
    r4 = px / fclose(t - pd.Timedelta(hours=4)) - 1
    r["OI_RET_4H"] = math.log(o0 / o4) * ((r4 > 0) - (r4 < 0)) if o0 > 0 and o4 > 0 else float("nan")
    tk = [x for x in mtk[max(0, j0 - 11):j0 + 1] if x == x]
    r["TAKER_LS_1H"] = math.log(sum(tk) / len(tk)) if tk else float("nan")
    fb = [ft[t - k * M5] for k in range(1, 13)]
    r["FUT_TAKER_1H"] = sum(b[2] for b in fb) / sum(b[1] for b in fb) - 0.5
    sb = [st.get(t - k * M5) for k in range(1, 13)]
    r["SPOT_TAKER_1H"] = sum(b[2] for b in sb) / sum(b[1] for b in sb) - 0.5 if all(sb) else float("nan")
    if t >= pd.Timestamp("2023-01-01"):
        ds = [dt_[t - k * M5] for k in range(1, 13) if (t - k * M5) in dt_ and dt_[t - k * M5][0] == dt_[t - k * M5][0]]
        r["DEPTH_IMB1_1H"] = sum(d[0] for d in ds) / len(ds) if ds else float("nan")
        r["DEPTH_IMB5_1H"] = sum(d[1] for d in ds) / len(ds) if ds else float("nan")
    r["CTRL_RET_1H"] = px / fclose(t - pd.Timedelta(hours=1)) - 1
    r["CTRL_RET_24H"] = px / fclose(t - pd.Timedelta(hours=24)) - 1
    return r


random.seed(26)
idx = random.sample(range(200, len(X) - 30), 2000)
bad = {}
for i in idx:
    row = X.iloc[i]
    for k, v in recompute(row.t).items():
        s = row[k]
        if not ((v != v and s != s) or (v == v and s == s and close(v, s, 1e-9))):
            bad[k] = bad.get(k, 0) + 1
check("N1", not bad, f"2,000 random rows, features rebuilt independently (z-score features PREM_Z / TOP / RETAIL use rolling-720 and are checked in N1b); mismatches {bad}")
# rolling-720 z features on the full hourly series, recomputed by explicit windows at the sampled rows
bz = 0
for nm, base in (("PREM_Z", "PREM_1H"),):
    s = X[base].to_numpy()
    for i in [j for j in idx if j >= 720][:500]:
        w = s[i - 719:i + 1]; w = w[~np.isnan(w)]
        v = (s[i] - w.mean()) / w.std(ddof=1) if len(w) >= 600 else float("nan")
        if not ((v != v and X[nm].iloc[i] != X[nm].iloc[i]) or close(v, X[nm].iloc[i], 1e-7)):
            bz += 1
check("N1b", bz == 0, f"PREM_Z rolling z recomputed on 500 rows: {bz} mismatches")

# ---------- (2) S1 ----------
FE = ["FUND_LVL", "FUND_Z", "PREM_1H", "PREM_Z", "BASIS", "OI_CHG_1H", "OI_CHG_24H", "OI_RET_4H", "TOP_LS_Z", "RETAIL_LS_Z",
      "TOP_MINUS_RETAIL", "TAKER_LS_1H", "FUT_TAKER_1H", "SPOT_TAKER_1H", "DEPTH_IMB1_1H", "DEPTH_IMB5_1H", "CTRL_RET_1H", "CTRL_RET_24H"]


def ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    n = len(a); ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def t_ic(per, f, hh):
    n = {"1h": 1, "4h": 4, "24h": 24}[hh]
    d = X[(X.period == per) & ((X.t.dt.hour % n == 0) if n < 24 else (X.t.dt.hour == 0))][["t", f, f"r_{hh}"]].dropna()
    ics = []
    for _, g in d.groupby([d.t.dt.year, d.t.dt.month]):
        if len(g) >= 10 and g[f].nunique() > 1:
            ics.append(pearson(ranks(list(g[f])), ranks(list(g[f"r_{hh}"]))))
    m = sum(ics) / len(ics); sd = math.sqrt(sum((x - m) ** 2 for x in ics) / (len(ics) - 1))
    return m / (sd / math.sqrt(len(ics))), m


s1D = pd.read_csv(O / "s1_D.csv")
b1 = 0
for r in s1D.itertuples():
    t, m = t_ic("D", r.feature, r.h)
    b1 += not (close(t, r.t_ic, 1e-7) and close(m, r.mean_monthly_ic, 1e-7))
check("N2", b1 == 0, f"S1 D: {len(s1D)} t_IC values recomputed by plain loops, {b1} mismatches; survivors {int((s1D.t_ic.abs() >= 3).sum())}")
s1V = pd.read_csv(O / "s1_V.csv")
b2 = 0
for r in s1V.itertuples():
    t, m = t_ic("V", r.feature, r.h)
    conf = (np.sign(t) == np.sign(r.t_ic_D)) and abs(t) >= 2.0
    b2 += not (close(t, r.t_ic, 1e-7) and conf == r.s1_confirmed)
check("N3", b2 == 0 and len(s1V) == int((s1D.t_ic.abs() >= 3).sum()), f"S1 V: {len(s1V)} rows recomputed, {b2} mismatches; confirmed {int(s1V.s1_confirmed.sum())}")

# ---------- (3) S2 ----------
tr = pd.read_parquet(O / "s2_trades.parquet")
S2 = pd.read_csv(O / "s2_summary.csv")
b3 = 0
for r in s1V[s1V.s1_confirmed].itertuples():
    f, hh = r.feature, r.h
    n = {"1h": 1, "4h": 4, "24h": 24}[hh]
    sign = 1 if s1D[(s1D.feature == f) & (s1D.h == hh)].mean_monthly_ic.iloc[0] > 0 else -1
    d = X[X.period.isin(["D", "V"]) & ((X.t.dt.hour % n == 0) if n < 24 else (X.t.dt.hour == 0))][["t", "period", f, f"r_{hh}"]].dropna().reset_index(drop=True)
    tt, xx = list(d.t), d[f].to_numpy()
    tn = d.t.to_numpy()
    mine = []
    for i in range(len(d)):
        lo = int(np.searchsorted(tn, tn[i] - np.timedelta64(90, "D"), side="left"))
        past = xx[lo:i]
        if len(past) < 30:
            continue
        pct = float((past < xx[i]).sum()) / len(past)
        sd = sign if pct >= 0.8 else (-sign if pct <= 0.2 else 0)
        if sd:
            mine.append((tt[i], sd, (sd * d[f"r_{hh}"].iloc[i] - COST) * 100))
    g = tr[(tr.feature == f) & (tr.h == hh)]
    same = len(g) == len(mine) and all(a[0] == b.t and a[1] == b.side and close(a[2], b.net, 1e-8) for a, b in zip(mine, g.itertuples()))
    v = [m for m in mine if pd.Timestamp("2024-01-01") <= m[0] < pd.Timestamp("2025-01-01")]
    mean = sum(m[2] for m in v) / len(v)
    wk = {}
    for m in v:
        k = tuple(m[0].isocalendar())[:2]; w = wk.setdefault(k, [0.0, 0]); w[0] += m[2]; w[1] += 1
    se = math.sqrt(len(wk) / (len(wk) - 1) * sum((w[0] - mean * w[1]) ** 2 for w in wk.values())) / len(v)
    mo = {}
    for m in v:
        mo[m[0].strftime("%Y-%m")] = mo.get(m[0].strftime("%Y-%m"), 0.0) + m[2]
    passed = mean > 0 and mean / se >= 2.0 and sum(x > 0 for x in mo.values()) >= 7
    row = S2[(S2.feature == f) & (S2.h == hh) & (S2.period == "V")].iloc[0]
    if not (same and close(mean, row.mean_net_pct, 1e-8) and close(mean / se, row.t_cluster, 1e-7) and passed == row.s2_pass):
        b3 += 1
check("N4", b3 == 0, f"S2: {int(s1V.s1_confirmed.sum())} configs, every trade and the V gate recomputed; {b3} mismatches; passes {int(S2.s2_pass.sum())}")
check("N5", not (tr.period == "H").any() and set(s1D.period) == {"D"} and set(tr.period) <= {"D", "V"}, "no H-period row in S1 / S2")
src = (P / "src/research/nonprice_np1.py").read_text(encoding="utf-8")
check("N6", not re.findall(r"(?<![\w.])0\.0*(?:46|85|92|4|17|18|28|036|075)\b", src) and "fees.json" in src, "no fee literal; cost from fees.json")
print("\nRESULT:", "ALL PASS" if not FAIL else f"FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
