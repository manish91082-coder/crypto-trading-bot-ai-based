"""Independent verifier for N6 (logs/research_n6_safety_sizing/N6_PROTOCOL_PREREGISTERED.md). Own code; does not import n6/n1.
V1 200 random S1 (35%) stop outcomes from raw 5m   V2 S2 cap weights: full sequential recomputation for 6 random coins (own 1h closes)
V3 T20 multipliers of 300 random trades from N5_predictions   V4 acceptance / gate booleans from result files   V5 SHAs + registry"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_n6_safety_sizing"
DR = R_ / "data" / "derived" / "n1"
HRS = {"4h": 4, "8h": 8, "12h": 12, "1D": 24}
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def raw5(coin):
    x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
    x["timestamp"] = pd.to_datetime(x.timestamp)
    return x


def agg(x, key):
    g = x.groupby(key)
    return pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last()))


cl = json.loads((O_ / "claims_n6.json").read_text())
rng = np.random.default_rng(66)
# V1
S1 = pd.read_parquet(DR / "n6_S1_trades.parquet")
S1["entry_time"] = pd.to_datetime(S1.entry_time)
pick = S1.iloc[rng.choice(len(S1), 200, replace=False)].sort_values("coin")
bad, cur = [], None
for r in pick.assign(e=pick.e.astype(int), hold=pick.hold.astype(int)).itertuples():
    if r.coin != cur:
        x = raw5(r.coin); cur = r.coin
        h1 = agg(x, x.timestamp.dt.floor("h"))
        tfb = {}
    if r.tf not in tfb:
        tfb[r.tf] = agg(x, x.timestamp.dt.floor("D") if r.tf == "1D" else x.timestamp.dt.floor(f"{HRS[r.tf]}h"))
    b = tfb[r.tf]
    en = float(b.open.iloc[r.e]); xt = b.index[r.e + r.hold]
    stp = en * (1 - r.side * 0.35)
    seg = h1[(h1.index >= r.entry_time) & (h1.index < xt)]
    X, hit = float(b.open.iloc[r.e + r.hold]), False
    for o, hi, lo in zip(seg.open.values, seg.high.values, seg.low.values):
        if (r.side == 1 and lo <= stp) or (r.side == -1 and hi >= stp):
            X = min(o, stp) if r.side == 1 else max(o, stp); hit = True
            break
    if not (hit == r.stopped and abs(X - r.X) < 1e-9 * max(1, X)):
        bad.append(f"{r.coin} {r.tf} {r.entry_time}: hit {hit}/{r.stopped} X {X}/{r.X}")
ok("V1", not bad, f"200 S1 35% stop outcomes from raw 5m: mismatches {len(bad)} {bad[:2]}; stopped share in file {S1.stopped.mean():.4f}")

# V2
L = pd.read_parquet(DR / "n6_S2_dev_weights.parquet")
hours = pd.date_range("2020-02-01", "2026-10-02", freq="h")
coins = rng.choice(sorted(L[L.w < L.w_base - 1e-15].coin.unique()), 3, replace=False).tolist() + \
        rng.choice(sorted(L.coin.unique()), 3, replace=False).tolist()
maxd = 0.0
for c in coins:
    x = raw5(c)
    cf = agg(x, x.timestamp.dt.floor("h")).close.reindex(hours).ffill().values
    g = L[L.coin == c].copy()
    g["_so"] = g.sleeve.map({"D": -1, "A": 0, "B": 1, "C": 2}); g["_t"] = g.tf.map({"4h": 0, "8h": 1, "12h": 2, "1D": 3})
    g = g.sort_values(["a", "_so", "_t", "fam"], kind="mergesort")
    act, w_own = [], {}
    for r in g.itertuples():
        act = [(E, u) for E, u in act if E > r.a]
        w = r.w_base
        if r.sleeve != "D" and w > 0:
            net = sum(u for _, u in act) * cf[int(r.a)]
            bound = 0.20 - net if r.side == 1 else 0.20 + net
            w = min(max(min(w, bound), 0.0), r.w_base)
        w_own[r.Index] = w
        if w > 0:
            act.append((r.E, r.side * w / r.entry))
    d = np.abs(np.array([w_own[i] for i in g.index]) - g.w.values)
    maxd = max(maxd, float(d.max()))
ok("V2", maxd < 1e-12, f"S2 cap weights recomputed sequentially for coins {coins}: max |diff| {maxd:.1e}")

# V3
P = pd.read_parquet(R_ / "logs" / "research_n5_ai" / "N5_predictions.parquet")
P["entry_time"] = pd.to_datetime(P.entry_time)
P = P[P.p_E.notna()].sort_values("entry_time").reset_index(drop=True)
P["month"] = P.entry_time.dt.to_period("M")
Mm = pd.read_parquet(O_ / "N6_multipliers.parquet")
months = sorted(P.month.unique())
bad3 = 0
for i in rng.choice(len(P), 300, replace=False):
    M = P.month.iloc[i]
    k = months.index(M)
    if k < 3:
        m = 1.0
    else:
        prior = P.p_E.values[(P.month < M).values]
        med, sd = np.median(prior), prior.std()
        m = np.clip(1 + (P.p_E.iloc[i] - med) / (2 * sd), 0.5, 1.5) / np.clip(1 + (prior - med) / (2 * sd), 0.5, 1.5).mean()
    bad3 += int(abs(m - Mm.m.iloc[i]) > 1e-12)
ok("V3", bad3 == 0, f"300 T20 multipliers recomputed from N5 predictions: mismatches {bad3}")

# V4
R = pd.read_csv(O_ / "N6_results.csv")
cal = {(r.trial, r.variant, r.window): r.calmar for r in R.itertuples()}
ex = cl["t19"]["exposure"]
acc = {v: (cal[("T19", v, "dev")] >= 0.9 * cal[("T19", "base", "dev")] and cal[("T19", v, "P1")] >= 0.9 * cal[("T19", "base", "P1")]
           and cal[("T19", v, "P2")] >= 0.9 * cal[("T19", "base", "P2")] and ex[v][0] < ex["base"][0]) for v in ("S1", "S2", "S3")}
choice = "S3" if acc["S3"] else (max([v for v in ("S1", "S2") if acc[v]], key=lambda v: cal[("T19", v, "dev")]) if (acc["S1"] or acc["S2"]) else None)
RS = pd.read_csv(O_ / "N6_random_sizing.csv")
g = cl["t20"]["gates"]
g_ok = g["dev>base"] == bool(cal[("T20", "AI_sizing", "dev")] > cal[("T20", "base_T20", "dev")]) and \
       g["dev>random_p95"] == bool(cal[("T20", "AI_sizing", "dev")] > np.percentile(RS.calmar, 95)) and \
       g["P1_P2>base"] == bool(cal[("T20", "AI_sizing", "P1")] > cal[("T20", "base_T20", "P1")] and cal[("T20", "AI_sizing", "P2")] > cal[("T20", "base_T20", "P2")])
n3 = json.loads((R_ / "logs" / "research_n3_execution" / "claims_n3.json").read_text())
ok("V4", acc == cl["t19"]["acceptable"] and choice == cl["t19"]["choice"] and g_ok and abs(cal[("T19", "base", "dev")] - n3["combo"]["dev"]) < 1e-9,
   f"T19 acceptance {acc} -> {choice}; T20 gate booleans consistent; base == N3 FINAL")
# V5
proto = O_ / "N6_PROTOCOL_PREREGISTERED.md"
reg = [l.split(",") for l in (R_ / "logs" / "r2_4h_a0" / "trial_registry.csv").read_text().splitlines() if l.startswith(("T19,", "T20,"))]
ok("V5", cl["protocol_sha"] == sha(proto) == (O_ / "N6_PROTOCOL_SHA256.txt").read_text().split()[0] and len(reg) >= 2 and all(r[6] == sha(proto) for r in reg)
   and all(cl["files"][k] == sha(O_ / k) for k in cl["files"]) and cl["code_sha"] == sha(R_ / "src" / "research" / "n6_safety_sizing.py"),
   "protocol lock, registry T19/T20, file SHAs, code SHA")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
