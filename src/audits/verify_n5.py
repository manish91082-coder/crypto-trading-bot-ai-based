"""Independent verifier for N5 (logs/research_n5_ai/N5_PROTOCOL_PREREGISTERED.md section 4). Own code; does not import n5_ai.
A1 PIT replay: features of 200 random trades rebuilt from raw data TRUNCATED at the entry time (signal bar close) == stored values
A2 leak canary: a feature equal to the trade's own net return must give out-of-time AUC > 0.9 with the same model class
A3 AUC / take rate / taken-minus-all / tail share recomputed from the prediction file; gate booleans consistent with N5_gates.csv
A4 SHAs + registry T18"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_n5_ai"
HRS = {"4h": 4, "8h": 8, "12h": 12, "1D": 24}
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


cl = json.loads((O_ / "claims_n5.json").read_text())
P = pd.read_parquet(O_ / "N5_predictions.parquet")
P["entry_time"] = pd.to_datetime(P.entry_time)
rng = np.random.default_rng(55)
pick = P.iloc[rng.choice(len(P), 200, replace=False)].sort_values("coin")
cur, x5 = None, None
btc_a = pd.read_csv(R_ / "data" / "universe_pre2020" / "1h" / "BTCUSDT_1h_full.csv.gz", usecols=["timestamp", "close"])
btc_a["d"] = pd.to_datetime(btc_a.timestamp).dt.floor("D")
btc_b = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / "BTCUSDT_5m_full.csv.gz", usecols=["timestamp", "close"])
btc_b["d"] = pd.to_datetime(btc_b.timestamp).dt.floor("D")
btc = pd.concat([btc_a[btc_a.d < "2020-01-01"].groupby("d").close.last(), btc_b.groupby("d").close.last()]).sort_index()
maxrel, worst = 0.0, None
for r in pick.itertuples():
    if r.coin != cur:
        x5 = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{r.coin}_5m_full.csv.gz",
                         usecols=["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades"])
        x5["timestamp"] = pd.to_datetime(x5.timestamp); cur = r.coin
    tr = x5[x5.timestamp < r.entry_time]                                  # truncated at the signal bar close
    key = tr.timestamp.dt.floor("D") if r.tf == "1D" else tr.timestamp.dt.floor(f"{HRS[r.tf]}h")
    g = tr.groupby(key)
    b = pd.DataFrame(dict(high=g.high.max(), low=g.low.min(), close=g.close.last(), volume=g.volume.sum(), qv=g.quote_volume.sum(), n=g.trades.sum()))
    c = b.close.values; h = b.high.values; l = b.low.values
    atr = None; A = []
    for i in range(len(b)):
        t_ = h[i] - l[i] if i == 0 else max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        atr = t_ if atr is None else atr + (t_ - atr) / 14; A.append(atr)
    A = np.array(A)
    up = np.r_[0, np.maximum(np.diff(c), 0)]; dn = np.r_[0, np.maximum(-np.diff(c), 0)]
    ag = ad = None
    for i in range(1, len(c)):
        ag = up[i] if ag is None else ag + (up[i] - ag) / 14; ad = dn[i] if ad is None else ad + (dn[i] - ad) / 14
    def ema(v, n):
        e = v[0]; k = 2 / (n + 1)
        for z in v[1:]:
            e = e + k * (z - e)
        return e
    wr = b.qv / b.n.replace(0, np.nan)
    vz = b.volume.iloc[-20:]
    n_ = len(c)
    nan = float("nan")
    with np.errstate(divide="ignore", invalid="ignore"):
        own = dict(ret1=c[-1] / c[-2] - 1 if n_ >= 2 else nan, ret5=c[-1] / c[-6] - 1 if n_ >= 6 else nan, ret20=c[-1] / c[-21] - 1 if n_ >= 21 else nan,
                   atrp=A[-1] / c[-1], rsi=(100 - 100 / (1 + ag / ad)) if (ag is not None and ad) else (100.0 if ag else nan),
                   d_ema20=(c[-1] - ema(c, 20)) / A[-1], d_ema50=(c[-1] - ema(c, 50)) / A[-1],
                   donch=(c[-1] - l[-20:].min()) / (h[-20:].max() - l[-20:].min()) if n_ >= 20 else nan,
                   vol_z=(vz.iloc[-1] - vz.mean()) / vz.std() if n_ >= 20 else nan,
                   whale=wr.iloc[-1] / wr.iloc[-20:].mean() if (n_ >= 20 and wr.iloc[-20:].notna().all()) else nan)
    bd = btc[btc.index < r.entry_time.floor("D")]
    own.update(btc_r1=bd.iloc[-1] / bd.iloc[-2] - 1, btc_r7=bd.iloc[-1] / bd.iloc[-8] - 1, btc_r30=bd.iloc[-1] / bd.iloc[-31] - 1,
               btc_sig20=bd.pct_change().iloc[-20:].std())
    for k, v in own.items():
        s = getattr(r, k)
        if not np.isfinite(v) and not np.isfinite(s):
            continue
        rel = abs(v - s) / max(1e-12, abs(v)) if (np.isfinite(v) and np.isfinite(s)) else np.inf   # one side missing = mismatch
        if rel > maxrel:
            maxrel, worst = rel, (r.coin, r.tf, str(r.entry_time), k, v, s)
ok("A1", maxrel < 1e-7, f"PIT replay of 14 features x 200 trades from data truncated at the entry time: max rel diff {maxrel:.1e} {worst if maxrel >= 1e-7 else ''}")

feats = [c for c in P.columns if c not in ("sleeve", "coin", "tf", "fam", "side", "entry_time", "e", "net", "y") and not c.startswith(("p_", "take_"))]
Pc = P.sort_values("entry_time").reset_index(drop=True)
Z = Pc[feats].values.copy()
canary = np.c_[Z, Pc.net.values]
cut = int(len(Pc) * 0.6)
m = HistGradientBoostingClassifier(max_iter=100, random_state=0).fit(canary[:cut], Pc.y.values[:cut])
auc_c = roc_auc_score(Pc.y.values[cut:], m.predict_proba(canary[cut:])[:, 1])
ok("A2", auc_c > 0.9, f"leak canary (own net return as a feature): out-of-time AUC {auc_c:.3f} > 0.9 -> the pipeline would expose a leak")

G = pd.read_csv(O_ / "N5_gates.csv")
dev = ((P.entry_time >= "2021-01-01") & (P.entry_time < "2025-10-01")).values
S = pd.read_csv(O_ / "N5_shuffled.csv")
gk, dmax = True, 0.0
for row in G.itertuples():
    k = row.model
    auc = roc_auc_score(P.y.values[dev], P[f"p_{k}"].values[dev])
    tk = P[f"take_{k}"].values[dev]; nt = P.net.values[dev]
    gb = nt[tk].mean() - nt.mean()
    tail = tk[nt >= np.quantile(nt, 0.9)].mean()
    dmax = max(dmax, abs(auc - row.auc), abs(tk.mean() - row.take_rate), abs(gb - row.gb), abs(tail - row.tail_share),
               abs(np.percentile(S[k], 95) - row.shuffled_p95))
    gg = cl["gates"][k]["gates"]
    gk &= gg["G-A"] == bool(row.auc > row.shuffled_p95 and row.auc_ci_lo > 0.5) and gg["G-B"] == bool(row.gb_ci_lo > 0)
    gk &= gg["G-C"] == bool(row.calmar_dev > row.base_calmar_dev and row.calmar_dev > row.random_skip_p95) and gg["G-D"] == bool(row.tail_share >= row.take_rate)
    gk &= gg["G-E"] == bool(row.calmar_P1 > row.base_P1 and row.calmar_P2 > row.base_P2) and gg["G-F"] == bool(row.dsr >= 0.95)
ok("A3", dmax < 1e-12 and gk, f"AUC / take rate / taken-minus-all / tail share / shuffled p95 recomputed (max diff {dmax:.1e}); gate booleans consistent")
proto = O_ / "N5_PROTOCOL_PREREGISTERED.md"
reg = [l.split(",") for l in (R_ / "logs" / "r2_4h_a0" / "trial_registry.csv").read_text().splitlines() if l.startswith("T18,")]
ok("A4", cl["protocol_sha"] == sha(proto) == (O_ / "N5_PROTOCOL_SHA256.txt").read_text().split()[0] and reg and reg[0][6] == sha(proto)
   and all(cl["files"][k] == sha(O_ / k) for k in cl["files"]) and cl["code_sha"] == sha(R_ / "src" / "research" / "n5_ai.py"),
   "protocol lock, registry T18, file SHAs, code SHA")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
