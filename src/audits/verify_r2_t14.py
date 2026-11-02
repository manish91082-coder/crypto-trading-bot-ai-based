"""Independent verifier for T14 (logs/r2_4h_t14/T14_PROTOCOL_PREREGISTERED.md). Own code paths.
1 300 random liquid rows rebuilt from data truncated at T (A2-verifier method: own truncation + ORIGINAL legs_for with a
  synthetic final pivot) -> swing features equal; F7 funding equal
2 liquidity flag recomputed for 300 random rows (liquid and not) from the raw perp 1h files
3 4 random months refitted with own code -> p equal
4 AUC / G-B / take rate / tail share recomputed from the OOS file
5 own MTM portfolio (AI + baseline) == claims;  6 claims / SHAs
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
sys.path.insert(0, str(R_ / "src" / "research"))
import swing_anatomy_phase1 as SA
import ladder_sessions as L

OUT, ST = R_ / "logs" / "r2_4h_t14", R_ / "data" / "derived" / "r2_t14"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def eq(a, b):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    return (np.isnan(a) and np.isnan(b)) or bool(np.isclose(a, b, rtol=1e-9, atol=1e-12))


S = pd.read_parquet(ST / "feature_store.parquet")
ALL = pd.read_parquet(ST / "t14_rows_all.parquet")
feats = json.loads((ST / "feature_list.json").read_text())
cl = json.loads((OUT / "claims_t14.json").read_text())
ccols = [c for c in S.columns if c.startswith("c_")]

# 1 truncated rebuild
orig = SA.SS.zigzag_pivots


def with_tail(df, k, events=None):
    piv = orig(df, k, events)
    if piv:
        piv = piv + [dict(idx=len(df) - 1, tick=4 * len(df) - 1, kind="L" if piv[-1]["kind"] == "H" else "H",
                          price=float(df.close.values[-1]), confirm_idx=len(df) - 1, ev=-1)]
    return piv


cache, bad, fng_full = {}, {}, SA.fng_table()
pick = np.random.default_rng(11).choice(S[S.available_at >= "2020-06-01"].index.values, 300, replace=False)
for n, i in enumerate(pick):
    r = S.loc[i]; T, coin = pd.Timestamp(r.available_at), r.coin
    for c in (coin, "BTCUSDT"):
        if c not in cache:
            cache[c] = (SA.load_spliced(c, "1h", []), SA.load_spliced(c, "1d", []))
    h = cache[coin][0]; h = h[h.timestamp + pd.Timedelta(hours=1) <= T].reset_index(drop=True)
    d = cache[coin][1]; d = d[d.timestamp + pd.Timedelta(days=1) <= T].reset_index(drop=True)
    SA.E._ZZ_CACHE.clear()
    b = SA.clip_atr(SA.agg(h, "4h"))[0]
    hb = {"1D": SA.clip_atr(d)[0], "1W": SA.clip_atr(SA.agg(d, "W-MON"))[0], "1M": SA.clip_atr(SA.agg(d, "MS"))[0]}
    htf = {k: (SA.end_times(k, v.timestamp.values), SA.E.zz(v, SA.KP)["state"]) for k, v in hb.items()}
    btc = None
    if coin != "BTCUSDT":
        bh = cache["BTCUSDT"][0]; bh = bh[bh.timestamp + pd.Timedelta(hours=1) <= T]
        bb = SA.clip_atr(SA.agg(bh, "4h"))[0]
        btc = (bb.timestamp.values, SA.base_factors(bb).ret20.values, SA.E.zz(bb, SA.KP)["state"], SA.end_times("4h", bb.timestamp.values))
    sup, rs = SA.sr_nearest(b)
    SA.SS.zigzag_pivots = with_tail
    try:
        Lg = SA.legs_for(coin, "4h", b, 3.0, SA.base_factors(b), sup, rs, (h.timestamp.values, h.low.values, h.high.values, h.quote_volume.values),
                         htf, btc, fng_full[fng_full.index < T.normalize()]).reset_index(drop=True)
    finally:
        SA.SS.zigzag_pivots = orig
    # newly listed coins can have < 2 legs at T (never happened on the 10 A2 coins): then the store, like A2, has NaN
    x = {c: Lg[c].iloc[-1] if len(Lg) else np.nan for c in ccols}
    x["last_leg_move_atr"], x["last_leg_bars"] = (Lg.move_atr.iloc[-2], Lg.bars.iloc[-2]) if len(Lg) >= 2 else (np.nan, np.nan)
    f = pd.read_csv(R_ / "data" / "futures_um" / f"{coin}_funding.csv"); f["time"] = pd.to_datetime(f["time"])
    ff = f[f.time <= T]; x["funding_last"] = ff.funding_rate.iloc[-1] if len(ff) else np.nan
    for c, v in x.items():
        if not eq(r[c], v):
            bad[c] = bad.get(c, 0) + 1
    if n % 50 == 0:
        print(f"  rebuild {n}/300", flush=True)
ok("1", not bad, f"300 liquid rows rebuilt from data truncated at T (own code): mismatching features {bad}")

# 2 liquidity
pk = np.random.default_rng(12).choice(ALL.index.values, 300, replace=False)
vols, lb = {}, 0
for i in pk:
    r = ALL.loc[i]
    if r.coin not in vols:
        v = pd.read_csv(R_ / "data" / "futures_um" / f"{r.coin}_perp_1h.csv.gz", usecols=["timestamp", "quote_volume"])
        v["day"] = pd.to_datetime(v.timestamp).dt.floor("D")
        vols[r.coin] = v.groupby("day").quote_volume.sum()
    dd = vols[r.coin]; day = pd.Timestamp(r.entry_time).floor("D")
    w = dd[(dd.index >= day - pd.Timedelta(days=30)) & (dd.index < day)]
    mine = bool(len(w) >= 20 and w.median() >= 50e6)
    lb += mine != bool(r.liq_ok)
ok("2", lb == 0, f"liquidity flag recomputed from raw perp 1h for 300 rows: mismatches {lb}")

# 3-5 model + portfolio (same method as verify_r2_a3)
T = pd.read_parquet(ST / "a1c_trades.parquet")[["signal", "coin", "side", "entry_time", "exit_idx", "R_price", "entry_px", "exit_px"]].rename(columns={"side": "side_str"})
S2 = S.merge(T, on=["signal", "coin", "side_str", "entry_time"], how="left")
S2 = S2[S2.perp_ok].sort_values(["entry_time", "signal_type", "coin"]).reset_index(drop=True)
S2["exit_time"] = S2.entry_time + pd.to_timedelta((S2.exit_idx + 1) * 4, unit="h")
S2["month"] = S2.entry_time.dt.to_period("M").dt.to_timestamp()
O = pd.read_parquet(OUT / "oos_predictions.parquet")
mx = 0.0
for M in np.random.default_rng(13).choice(O.month.unique(), 4, replace=False):
    M = pd.Timestamp(M)
    tr = S2[(S2.entry_time >= "2020-02-01") & (S2.exit_time < M - pd.Timedelta(days=1))].sort_values("entry_time")
    te = S2[S2.month == M]; k = int(len(tr) * 0.8)
    m = HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0,
                                       early_stopping=False, random_state=20261019, categorical_features=[feats.index("signal_type")])
    m.fit(tr[feats].values[:k], tr.label.values[:k])
    iso = IsotonicRegression(out_of_bounds="clip").fit(m.predict_proba(tr[feats].values[k:])[:, 1], tr.label.values[k:])
    p = pd.Series(iso.predict(m.predict_proba(te[feats].values)[:, 1]), index=te.index)
    th = O[O.month == M].set_index("idx").p
    mx = max(mx, float(np.abs(p.loc[th.index] - th).max()))
ok("3", mx < 1e-9, f"4 random months refitted with own code: max |p diff| {mx:.1e}")
S2["p"] = np.nan; S2["take"] = False; S2["m"] = 1.0
S2.loc[O.idx, "p"] = O.p.values; S2.loc[O.idx, "take"] = O["take"].values; S2.loc[O.idx, "m"] = O.m.values
dev = S2[(S2.entry_time >= "2021-01-01") & (S2.entry_time < "2025-10-01") & S2.p.notna()]
top = dev[dev.net_base >= dev.net_base.quantile(0.9)]
c4 = (abs(roc_auc_score(dev.label, dev.p) - cl["auc_dev"]) < 1e-12 and abs(dev["take"].mean() - cl["take_rate"]) < 1e-12
      and abs(dev[dev["take"]].net_base.mean() - dev.net_base.mean() - cl["gb_diff"]) < 1e-12 and abs(top["take"].mean() - cl["tail_share"]) < 1e-12)
ok("4", c4, f"AUC {roc_auc_score(dev.label, dev.p):.4f}, take {dev['take'].mean():.3f}, tail {top['take'].mean():.3f} == claims")

bars = {}
def low4(c):
    if c not in bars:
        x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{c}_5m_full.csv.gz", usecols=["timestamp", "low", "high"])
        x["timestamp"] = pd.to_datetime(x["timestamp"]); x = x.set_index("timestamp").sort_index()
        g = x.groupby(x.index.floor("4h")); bars[c] = pd.DataFrame(dict(low=g.low.min(), high=g.high.max())).dropna()
    return bars[c]


def run(take, mult):
    t0, t1 = pd.Timestamp("2021-01-01"), pd.Timestamp("2025-10-01")
    d = S2[take & (S2.entry_time >= t0) & (S2.entry_time < t1)]
    by = {}
    for i in d.index:
        by.setdefault(d.at[i, "entry_time"], []).append(i)
    E, op, cur = 8000.0, [], []
    for t in pd.date_range(t0, t1 - pd.Timedelta(hours=4), freq="4h"):
        for o in [o for o in op if o[2] <= t]:
            E += o[3]; op.remove(o)
        for i in by.get(t, []):
            r = S2.loc[i]
            if any(o[0] == r.coin for o in op) or len(op) >= 6:
                continue
            rp = r.R_price / r.entry_px; N = 0.005 * mult[i] * E / (rp + 0.0109)
            if sum(o[1] for o in op) + N > 3 * E or N < {"BTCUSDT": 50, "ETHUSDT": 20, "LINKUSDT": 20}.get(r.coin, 5) or \
                    (r.coin == "BTCUSDT" and N / r.entry_px < 0.001):
                continue
            op.append((r.coin, N, r.exit_time, N * r.net_base * rp, r.entry_time, r.side, r.entry_px, r.exit_px, int(r.exit_idx)))
        u = 0.0
        for o in op:
            kb = int((t - o[4]) / pd.Timedelta(hours=4))
            if kb == o[8]:
                u += o[1] * o[5] * (o[7] - o[6]) / o[6]
            else:
                bb = low4(o[0]); j = bb.index.get_loc(o[4]) + kb
                u += o[1] * o[5] * ((bb.low.values[j] if o[5] > 0 else bb.high.values[j]) - o[6]) / o[6]
        cur.append(E + u)
    for o in op:
        E += o[3]
    cur.append(E); c = np.array(cur)
    return E, float((1 - c / np.maximum.accumulate(c)).max())


Ea, da = run((S2["take"] & S2.p.notna()).values, S2.m.values)
Eb, db = run(S2.p.notna().values, np.ones(len(S2)))
ok("5", abs(Ea - cl["ai"]["final"]) < 1e-6 and abs(da - cl["ai"]["mtm_dd"]) < 1e-6 and abs(Eb - cl["baseline"]["final"]) < 1e-6
   and abs(db - cl["baseline"]["mtm_dd"]) < 1e-6, f"own MTM portfolio: AI {Ea:.2f}/{da:.4f}, baseline {Eb:.2f}/{db:.4f} == claims")
c6 = (cl["protocol_sha"] == sha(OUT / "T14_PROTOCOL_PREREGISTERED.md") == (OUT / "T14_PROTOCOL_SHA256.txt").read_text().split()[0]
      and cl["store_sha"] == sha(ST / "feature_store.parquet") and cl["oos_sha"] == sha(OUT / "oos_predictions.parquet")
      and cl["verdict"] == ("T14 provisional PASS" if all(cl["gates"].values()) else "T14 FAIL"))
ok("6", c6, f"claims / verdict ('{cl['verdict']}') / SHAs consistent")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
