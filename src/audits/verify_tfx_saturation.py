"""Independent verifier for TFX-S (logs/research_tf_edge_map/TFXS_PROTOCOL_PREREGISTERED.md). Own code; imports neither
tf_edge_map nor tfx_saturation.
1 S1: 3 random cells, own month-block bootstrap -> CI within +-10% of the CI width, same month-block reading parts, exact means
2 S2/S3: 5 random cells: median/trimmed/top1% share/break-even/net_2x mean exact (1e-12)
3 S5: 3 random (uni, tf, side, year) trend-pooled means exact; BTC yearly returns from own 1D closes
4 S6: 3 random sleeves' monthly series -> Sharpe/MDD exact; 3 random correlations; N_eff own eigen-decomposition
5 SHAs / protocol lock"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_tf_edge_map"
TR = R_ / "data" / "derived" / "tf_edge_map"
FAM = ["TSMOM", "EMAX", "MACD", "DONCH", "RSI", "BB"]
TREND = FAM[:4]
DIR = {"1m": "1min", "1M": "1mo"}
DT = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "8h": "8h", "12h": "12h", "1D": "1D", "1W": "7D"}
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def trades(uni, tf, fam):
    src = "U2" if uni == "U2X" else uni
    ex = {"LUNAUSDT", "STRAXUSDT"} if uni == "U2X" else set()
    fs = [f for f in sorted((TR / src / DIR.get(tf, tf)).glob("*.parquet")) if f.stem not in ex]
    D = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    D = D[D.fam == FAM.index(fam)].copy()
    D["entry_time"] = pd.to_datetime(D.entry_time)
    step = pd.Timedelta(days=30.4375) if tf == "1M" else pd.Timedelta(DT[tf])
    D["xm"] = (D.entry_time + D.hold * step).dt.strftime("%Y-%m")
    D["m"] = D.entry_time.dt.strftime("%Y-%m")
    D["nt"] = D.gross - 0.00108 - D.fund
    D["ex"] = D.gross - D.ctrl
    return D


cl = json.loads((O_ / "claims_tfxs.json").read_text())
C = pd.read_csv(O_ / "S1_S4_cells_monthblock.csv")
rng = np.random.default_rng(4242)

# 1
msg, good = [], True
for r in C[C.n_dev >= 300].sample(3, random_state=8).itertuples():
    D = trades(r.uni, r.tf, r.family); D = D[(D.side == (1 if r.side == "long" else -1)) & (D.period < 2)]
    for col, own in (("net_taker", D.nt), ("excess", D.ex)):
        v = own.values; k = ~np.isnan(v); v = v[k]; b = D.m.values[k]
        mons = np.unique(b); idx = {m: np.flatnonzero(b == m) for m in mons}
        boots = []
        for _ in range(2000):
            pick = rng.choice(mons, len(mons), replace=True)
            ii = np.concatenate([idx[m] for m in pick]); boots.append(v[ii].mean())
        lo, hi = np.quantile(boots, [.025, .975])
        slo, shi = getattr(r, f"{col}_mlo"), getattr(r, f"{col}_mhi")
        w = shi - slo
        good &= abs(v.mean() - getattr(r, f"{col}_mean")) < 1e-12 and abs(lo - slo) < 0.1 * w and abs(hi - shi) < 0.1 * w and (lo > 0) == (slo > 0) and (hi < 0) == (shi < 0)
        msg.append(f"{r.uni} {r.tf} {r.family} {r.side} {col}: own [{lo:.5f},{hi:.5f}] vs [{slo:.5f},{shi:.5f}]")
ok("1", good, "S1 month-block CIs re-bootstrapped: " + "; ".join(msg))

# 2
mx = 0.0
for r in C[C.n_dev >= 30].sample(5, random_state=9).itertuples():
    D = trades(r.uni, r.tf, r.family); D = D[(D.side == (1 if r.side == "long" else -1)) & (D.period < 2)]
    ex = np.sort(D.ex.dropna().values); nt = np.sort(D.nt.dropna().values)
    k1, k2 = int(np.floor(.05 * len(ex))), int(np.floor(.05 * len(nt)))
    top = nt[::-1][:max(1, int(np.ceil(.01 * len(nt))))].sum() / nt.sum()
    vals = [(np.median(ex), r.excess_median), (ex[k1:len(ex) - k1].mean(), r.excess_trim5), (nt[k2:len(nt) - k2].mean(), r.net_taker_trim5),
            (top, r.top1pct_share), ((D.gross - D.fund).dropna().mean(), r.breakeven_cost), ((D.gross - 0.00216 - D.fund).dropna().mean(), r.net_2x_mean)]
    mx = max(mx, max(abs(a - b) for a, b in vals))
ok("2", mx < 1e-12, f"S2/S3 for 5 random cells recomputed from trade files: max |diff| {mx:.1e}")

# 3
T = pd.read_csv(O_ / "S5_trend_by_year.csv")
x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / "BTCUSDT_5m_full.csv.gz", usecols=["timestamp", "open", "close"])
x["timestamp"] = pd.to_datetime(x.timestamp)
dc = x.groupby(x.timestamp.dt.floor("D")).close.last()
bt = {}
for y in range(2020, 2027):
    p = dc[dc.index < f"{y}-01-01"]
    bt[y] = dc[dc.index < f"{y + 1}-01-01"].iloc[-1] / (p.iloc[-1] if len(p) else x.open.iloc[0]) - 1
c3 = all(abs(bt[y] - cl["btc_year_ret"][str(y)]) < 1e-12 for y in bt)
for r in T.sample(3, random_state=10).itertuples():
    s = n = 0.0
    for fam in TREND:
        D = trades(r.uni, r.tf, fam); D = D[(D.side == (1 if r.side == "long" else -1)) & (D.year == r.year)]
        s += D.nt.sum(skipna=True); n += D.nt.notna().sum()
    c3 &= abs(s / n - r.net_mean) < 1e-12
ok("3", c3, f"S5: BTC yearly returns {[round(v, 3) for v in bt.values()]} and 3 random trend-pooled year means recomputed")

# 4
ST = pd.read_csv(O_ / "S6_sleeve_stats.csv")
P = pd.read_csv(O_ / "S6_correlations.csv")
dev = [str(p) for p in pd.period_range("2020-02", "2025-09", freq="M")]


def elig(uni):
    out = {}
    if uni == "U1":
        for c in ["ADAUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "DOTUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]:
            t = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{c}_5m_full.csv.gz", usecols=["timestamp"]).timestamp.str[:7].unique()
            for m in t:
                out[m] = out.get(m, 0) + 1
        return out
    raise NotImplementedError


E1 = elig("U1")


def series(uni, tf, fam, side):
    D = trades(uni, tf, fam); D = D[D.side == (1 if side == "long" else -1)].dropna(subset=["nt"])
    s = D.groupby("xm").nt.sum()
    return pd.Series({m: s.get(m, 0.0) / E1[m] if m in E1 else 0.0 for m in dev})


mx4 = 0.0
for r in ST[(ST.uni == "U1") & (ST.months_nonzero >= 24)].sample(3, random_state=11).itertuples():
    s = series("U1", r.tf, r.family, r.side)
    cum = s.cumsum()
    mx4 = max(mx4, abs(np.sqrt(12) * s.mean() / s.std(ddof=1) - r.sharpe_ann), abs((cum.cummax() - cum).max() - r.mdd))
pp = P[P.a.str.startswith("U1|") & P.b.str.startswith("U1|")].sample(3, random_state=12)
for r in pp.itertuples():
    a, b = r.a.split("|"), r.b.split("|")
    mx4 = max(mx4, abs(np.corrcoef(series(*a), series(*b))[0, 1] - r.rho))
ok("4a", mx4 < 1e-9, f"S6: 3 U1 sleeves' Sharpe/MDD and 3 U1 correlations rebuilt from trade files: max |diff| {mx4:.1e}")
keys = ST[(ST.uni == "U1") & (ST.months_nonzero >= 24)]
X = pd.DataFrame({f"{r.tf}|{r.family}|{r.side}": series("U1", r.tf, r.family, r.side) for r in keys.itertuples()})
lam = np.clip(np.linalg.eigvalsh(X.corr().values), 0, None)
ne = lam.sum() ** 2 / (lam ** 2).sum()
ok("4b", abs(ne - cl["n_eff"]["all_U1"][0]) < 1e-9 and len(keys) == cl["n_eff"]["all_U1"][1], f"N_eff all U1 sleeves own eigen-decomposition {ne:.3f} vs claims {cl['n_eff']['all_U1'][0]:.3f} (n={len(keys)})")

# 5
c5 = (cl["protocol_sha"] == sha(O_ / "TFXS_PROTOCOL_PREREGISTERED.md") == (O_ / "TFXS_PROTOCOL_SHA256.txt").read_text().split()[0]
      and cl["cells_sha"] == sha(O_ / "S1_S4_cells_monthblock.csv") and cl["s5_sha"] == sha(O_ / "S5_trend_by_year.csv")
      and cl["s6_sha"] == sha(O_ / "S6_sleeve_stats.csv") and cl["corr_sha"] == sha(O_ / "S6_correlations.csv")
      and cl["tfx_cells_sha"] == sha(O_ / "TFX_cells.csv") and cl["code_sha"] == sha(R_ / "src" / "research" / "tfx_saturation.py"))
ok("5", c5, "claims / SHAs / protocol lock consistent")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
