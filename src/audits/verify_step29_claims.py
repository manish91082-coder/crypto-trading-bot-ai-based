"""
Independent verifier for Step 29 (logs/strategy_1d_step29_srv).
V1 protocol hash. V2 for 60 random test rows: the 6 SRV features re-derived with plain code (brute-force unbroken
fractal levels, plain VAP filter, plain higher-timeframe state scan). V3 AUCs and the paired difference recomputed
from the stored predictions (plain Mann-Whitney). V4 gates re-derived.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import step24_1h_brain as S24
import step29_srv_features as S29
import swing_anatomy_phase1 as P
import swing_strategy_1d as E

C = json.loads((S29.OUT / "claims.json").read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def close(a, b, tol=1e-9):
    return (np.isnan(a) and np.isnan(b)) or abs(a - b) <= tol * max(1.0, abs(b))


def main():
    assert sha(S29.OUT / S29.PROTO_NAME) == (S29.OUT / "PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    assert sha(S29.OUT / "test_predictions_srv.csv") == C["test_predictions_sha256"]
    print("[V1 PASS] protocol and prediction hashes")

    T = pd.read_csv(S29.OUT / "test_predictions_srv.csv", parse_dates=["bar"])
    smp = T.sample(60, random_state=29)
    for s, g in smp.groupby("symbol"):
        d = pd.read_csv(S24.UNI1H / f"{s}_1h_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close", "quote_volume"], parse_dates=["timestamp"])
        d = d.sort_values("timestamp")
        d["timestamp"] = d.timestamp.dt.floor("h")
        gg = d.groupby("timestamp", sort=True)
        d = pd.DataFrame(dict(open=gg.open.first(), high=gg.high.max(), low=gg.low.min(), close=gg.close.last(),
                              quote_volume=gg.quote_volume.sum())).reset_index()
        d["taker_buy_quote"] = 0.0
        b, _ = P.clip_atr(d)
        hi, lo, cl, atr, ts = b.high.values, b.low.values, b.close.values, b.ATR_14.values, b.timestamp.values
        st1 = E.zz(b, 3.0)["state"]
        hb = {tf: P.clip_atr(P.agg(d, tf))[0] for tf in ("4h", "1D")}
        hst = {tf: (P.end_times(tf, x.timestamp.values), E.zz(x, 3.0)["state"]) for tf, x in hb.items()}
        feats = S29.coin_srv(S24.UNI1H / f"{s}_1h_full.csv.gz", pd.DatetimeIndex(g.bar.values))
        for t in g.bar.values:
            c = int(np.searchsorted(ts, t))
            assert ts[c] == t
            sup, res = np.nan, np.nan
            for i in range(3, c - 2):
                if i + 3 > c:
                    continue
                if lo[i] == lo[i - 3:i + 4].min() and lo[i] <= cl[c] and (cl[i + 3:c + 1] >= lo[i]).all():
                    sup = lo[i] if np.isnan(sup) else max(sup, lo[i])
                if hi[i] == hi[i - 3:i + 4].max() and hi[i] >= cl[c] and (cl[i + 3:c + 1] <= hi[i]).all():
                    res = hi[i] if np.isnan(res) else min(res, hi[i])
            f = feats.loc[t]
            assert close(f.sup_dist_atr_1h, (cl[c] - sup) / atr[c], 1e-7), (s, t, "sup")
            assert close(f.res_dist_atr_1h, (res - cl[c]) / atr[c], 1e-7), (s, t, "res")
            assert f.zz_state_1h == st1[c]
            tend = t + np.timedelta64(1, "h")
            for tf in ("4h", "1D"):
                et, st = hst[tf]
                known = [st[j] for j in range(len(et)) if et[j] <= tend]
                assert f[f"zz_state_{tf}"] == (known[-1] if known else 0), (s, t, tf)
            w = d[(d.timestamp >= tend - np.timedelta64(7, "D")) & (d.timestamp < tend)]
            if len(w) >= 10 and w.quote_volume.sum() > 0 and np.isfinite(atr[c]):
                m = (w.low <= cl[c] + 0.25 * atr[c]) & (w.high >= cl[c] - 0.25 * atr[c])
                assert close(f.vap_7d, w.quote_volume[m].sum() / w.quote_volume.sum()), (s, t, "vap")
    print(f"[V2 PASS] {len(smp)} rows: S/R distances, VAP and the three swing states re-derived with plain code")

    m = T.label24.notna() & T.R24_SRV.notna()
    y = T.label24[m].values.astype(int)
    a_new, a_old = roc_auc_score(y, T.R24_SRV[m].values), roc_auc_score(y, T.R24_base[m].values)
    assert abs(a_new - a_old - C["paired_auc_diff"]["diff"]) < 1e-12
    assert abs(a_new - C["R24_SRV_skill"]["auc"]) < 1e-12 and abs(a_old - C["R24_base_skill_same_rows"]["auc"]) < 1e-12
    print(f"[V3 PASS] AUC new {a_new:.4f}, base {a_old:.4f}, diff {a_new - a_old:+.4f}")

    g = C["gates"]
    r = C["portfolio"]["R24_SRV"]
    re_ = dict(G2_added_skill=C["paired_auc_diff"]["ci_low"] > 0, G3a_calmar=r["calmar"] > 0.92, G3b_trade_ci=r["trade_ci_low_pct"] > 0,
               G3c_cost040=C["portfolio"]["R24_SRV_cost040"]["cagr_pct"] > 0,
               G4_pre2020=C["pre2020_SRV"]["auc"] > C["pre2020_base"]["auc"] and C["pre2020_SRV"]["ci_low"] > 0.5)
    assert all(g[k] == v for k, v in re_.items())
    print(f"[V4 PASS] gates re-derived: {g['decision']}")


if __name__ == "__main__":
    main()
