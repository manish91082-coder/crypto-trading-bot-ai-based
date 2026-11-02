"""Independent verifier for A3 (logs/r2_4h_a3/A3_PROTOCOL_PREREGISTERED.md). Own implementation; does not import the A3 module.
1 refit 6 random test months; p == study p (1e-9)      2 AUC, G-B diff, take rate, tail share recomputed from the OOS file
3 own MTM portfolio for AI and baseline: final equity and MTM DD == claims (1e-6)      4 claims / gates / SHAs
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score

R_ = Path(__file__).resolve().parents[2]
A3, ST = R_ / "logs" / "r2_4h_a3", R_ / "data" / "derived" / "r2_a2"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


S = pd.read_parquet(ST / "feature_store.parquet")
feats = json.loads((ST / "feature_list.json").read_text())
T = pd.read_parquet(R_ / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet")[
    ["signal", "coin", "side", "entry_time", "exit_idx", "net_x1_5", "R_price", "entry_px", "exit_px"]].rename(columns={"side": "side_str"})
S = S.merge(T, on=["signal", "coin", "side_str", "entry_time"], how="left")
S = S[S.perp_ok].sort_values(["entry_time", "signal_type", "coin"]).reset_index(drop=True)
S["exit_time"] = S.entry_time + pd.to_timedelta((S.exit_idx + 1) * 4, unit="h")
S["month"] = S.entry_time.dt.to_period("M").dt.to_timestamp()
O = pd.read_parquet(A3 / "oos_predictions.parquet")
cl = json.loads((A3 / "claims_a3.json").read_text())

# 1 refit
rng = np.random.default_rng(99)
months = rng.choice(O.month.unique(), 6, replace=False)
mx = 0.0
for M in months:
    M = pd.Timestamp(M)
    tr = S[(S.entry_time >= "2020-02-01") & (S.exit_time < M - pd.Timedelta(days=1))].sort_values("entry_time")
    te = S[S.month == M]
    k = int(len(tr) * 0.8)
    m = HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0,
                                       early_stopping=False, random_state=20261019, categorical_features=[feats.index("signal_type")])
    m.fit(tr[feats].values[:k], tr.label.values[:k])
    iso = IsotonicRegression(out_of_bounds="clip").fit(m.predict_proba(tr[feats].values[k:])[:, 1], tr.label.values[k:])
    p = iso.predict(m.predict_proba(te[feats].values)[:, 1])
    mine = pd.Series(p, index=te.index)
    theirs = O[O.month == M].set_index("idx").p
    mx = max(mx, float(np.abs(mine.loc[theirs.index] - theirs).max()))
ok("1", mx < 1e-9, f"6 random test months refitted with own code: max |p diff| {mx:.1e}")

# 2 stats
S["p"] = np.nan; S["take"] = False; S["m"] = 1.0
S.loc[O.idx, "p"] = O.p.values; S.loc[O.idx, "take"] = O["take"].values; S.loc[O.idx, "m"] = O.m.values
dev = S[(S.entry_time >= "2021-01-01") & (S.entry_time < "2025-10-01") & S.p.notna()]
auc = roc_auc_score(dev.label, dev.p)
gb = dev[dev["take"]].net_base.mean() - dev.net_base.mean()
top = dev[dev.net_base >= dev.net_base.quantile(0.9)]
c2 = (abs(auc - cl["auc_dev"]) < 1e-12 and abs(gb - cl["gb_diff"]) < 1e-12 and abs(dev["take"].mean() - cl["take_rate"]) < 1e-12
      and abs(top["take"].mean() - cl["tail_share"]) < 1e-12)
ok("2", c2, f"AUC {auc:.4f}, take rate {dev["take"].mean():.3f}, G-B diff {gb:+.4f}, tail share {top["take"].mean():.3f} == claims")

# 3 own MTM portfolio
bars = {}
def b4(c):
    if c not in bars:
        x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{c}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
        x["timestamp"] = pd.to_datetime(x["timestamp"]); x = x.set_index("timestamp").sort_index()
        g = x.groupby(x.index.floor("4h"))
        bars[c] = pd.DataFrame(dict(low=g.low.min(), high=g.high.max())).dropna()
    return bars[c]


def run(take, mult):
    t0, t1 = pd.Timestamp("2021-01-01"), pd.Timestamp("2025-10-01")
    d = S[take & (S.entry_time >= t0) & (S.entry_time < t1)]
    by_t = {}
    for i in d.index:
        by_t.setdefault(d.at[i, "entry_time"], []).append(i)
    E, op, curve = 8000.0, [], []
    for t in pd.date_range(t0, t1 - pd.Timedelta(hours=4), freq="4h"):
        for o in [o for o in op if o[2] <= t]:
            E += o[3]; op.remove(o)
        for i in by_t.get(t, []):
            r = S.loc[i]
            if any(o[0] == r.coin for o in op) or len(op) >= 6:
                continue
            rp = r.R_price / r.entry_px
            N = 0.005 * mult[i] * E / (rp + 0.01 + 0.0009)
            if sum(o[1] for o in op) + N > 3 * E or N < {"BTCUSDT": 50, "ETHUSDT": 20, "LINKUSDT": 20}.get(r.coin, 5) or \
                    (r.coin == "BTCUSDT" and N / r.entry_px < 0.001):
                continue
            op.append((r.coin, N, r.exit_time, N * r.net_base * rp, r.entry_time, r.side, r.entry_px, r.exit_px, int(r.exit_idx)))
        u = 0.0
        for o in op:
            k = int((t - o[4]) / pd.Timedelta(hours=4))
            if k == o[8]:
                u += o[1] * o[5] * (o[7] - o[6]) / o[6]
            else:
                bb = b4(o[0]).loc[t]
                u += o[1] * o[5] * ((bb.low if o[5] > 0 else bb.high) - o[6]) / o[6]
        curve.append(E + u)
    for o in op:
        E += o[3]
    curve.append(E)
    c = np.array(curve)
    return E, float((1 - c / np.maximum.accumulate(c)).max())


allr = S.p.notna().values
Ea, dda = run((S["take"] & S.p.notna()).values, S.m.values)
Eb, ddb = run(allr, np.ones(len(S)))
c3 = (abs(Ea - cl["ai"]["final"]) < 1e-6 and abs(dda - cl["ai"]["mtm_dd"]) < 1e-6 and abs(Eb - cl["baseline"]["final"]) < 1e-6
      and abs(ddb - cl["baseline"]["mtm_dd"]) < 1e-6)
ok("3", c3, f"own MTM portfolio: AI {Ea:.2f} / DD {dda:.4f}; baseline {Eb:.2f} / DD {ddb:.4f} == claims")

g = pd.read_csv(A3 / "A3_gates.csv")
c4 = (cl["protocol_sha"] == sha(A3 / "A3_PROTOCOL_PREREGISTERED.md") == (A3 / "A3_PROTOCOL_SHA256.txt").read_text().split()[0]
      and cl["store_sha"] == sha(ST / "feature_store.parquet") and cl["oos_sha"] == sha(A3 / "oos_predictions.parquet")
      and all(bool(r.pass_) == cl["gates"][r.gate] for r in g.itertuples())
      and cl["verdict"] == ("A3 provisional PASS" if all(cl["gates"].values()) else "A3 FAIL"))
ok("4", c4, f"claims / gates / verdict ('{cl['verdict']}') / SHAs consistent")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
(A3 / "verify_log.txt").write_text(f"verify_r2_a3: {len(res)} checks, FAIL {res.count(False)}\n")
sys.exit(1 if False in res else 0)
