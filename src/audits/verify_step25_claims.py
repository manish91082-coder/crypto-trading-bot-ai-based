"""
Independent verifier for logs/strategy_1d_step25_hf/claims.json.
V1 protocol hash as locked; predictions file SHA as claimed.
V2 30 random test rows: the 9 HF features recomputed from RAW 5m/15m files by direct time-window filtering (no rolling,
   no merge_asof), compared with the values the pipeline used (re-read through step25.add_hf for those rows).
V3 AUC of R24_HF and of the Step 24 baseline recomputed (Mann-Whitney); paired difference point estimate.
V4 R24_HF portfolio re-simulated with the Step 24 verifier's separate simulator.
V5 gates recomputed.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "audits", SRC / "pipeline_1d", SRC / "analytics", SRC / "execution"):
    sys.path.insert(0, str(p))
from config import DATA_DIR, LOGS_DIR
import verify_step24_claims as V24
import step25_hf_features as S25

D = LOGS_DIR / "strategy_1d_step25_hf"
HF = DATA_DIR / "universe_hf"
C = json.loads((D / "claims.json").read_text())


def direct(s, t):
    d5 = pd.read_csv(HF / "5m" / f"{s}_5m_full.csv.gz", parse_dates=["timestamp"]).set_index("timestamp").sort_index()
    d15 = pd.read_csv(HF / "15m" / f"{s}_15m_full.csv.gz", parse_dates=["timestamp"]).set_index("timestamp").sort_index()
    e = t + pd.Timedelta(hours=1)
    last5 = d5[(d5.index >= t) & (d5.index < e)]
    last15 = d15[(d15.index >= t) & (d15.index < e)]
    out = {k: np.nan for k in S25.HF_BASE}
    if len(last5):
        T = last5.index[-1]

        def win(hours):
            w = d5[(d5.index > T - pd.Timedelta(hours=hours)) & (d5.index <= T)]
            prev = d5[d5.index < w.index[0]].tail(1) if len(w) else w
            c = pd.concat([prev, w])
            r = (c.close / c.close.shift(1) - 1)[c.index.to_series().diff() == pd.Timedelta(minutes=5)]
            return w, r[r.index >= w.index[0]] if len(w) else r
        w1, r1 = win(1)
        w4, r4 = win(4)
        w24, _ = win(24)
        if r1.notna().sum() >= 8:
            out["rv5_1h"] = r1.std()
        if r4.notna().sum() >= 30:
            out["rv5_4h"] = r4.std()
        if len(w4) >= 30:
            out["maxdd5_4h"] = w4.close.iloc[-1] / w4.close.max() - 1
            out["maxup5_4h"] = w4.close.iloc[-1] / w4.close.min() - 1
            out["upshare5_4h"] = (w4.close > w4.open).mean()
        if len(w1) >= 8 and len(w24) >= 200:
            out["volburst5_1h"] = w1.volume.max() / w24.volume.mean()
    if len(last15):
        T = last15.index[-1]
        c = last15.iloc[-1]
        out["ret15_last"] = c.close / c.open - 1
        out["taker15_last"] = c.taker_buy_base / c.volume
        w = d15[(d15.index > T - pd.Timedelta(hours=24)) & (d15.index <= T)]
        prev = d15[d15.index < w.index[0]].tail(1)
        cc = pd.concat([prev, w])
        r = (cc.close / cc.close.shift(1) - 1)[cc.index.to_series().diff() == pd.Timedelta(minutes=15)]
        r = r[r.index >= w.index[0]]
        if r.notna().sum() >= 60:
            out["std15_24h"] = r.std()
    return out


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / "STEP25_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    assert hashlib.sha256((D / "test_predictions_hf.csv").read_bytes()).hexdigest() == C["test_predictions_sha256"]
    print("[V1 PASS] protocol hash as locked; predictions SHA as claimed")

    P = pd.read_csv(D / "test_predictions_hf.csv", parse_dates=["bar"])
    smp = P.sample(30, random_state=11)[["symbol", "bar"]].reset_index(drop=True)
    got, _, _ = S25.add_hf(smp.copy(), HF)
    for i, r in smp.iterrows():
        want = direct(r.symbol, r.bar)
        for k in S25.HF_BASE:
            a, b = float(got.at[i, k]), want[k]
            assert (np.isnan(a) and np.isnan(b)) or abs(a - b) <= 1e-5 * max(1.0, abs(b)), (r.symbol, r.bar, k, a, b)
    print("[V2 PASS] 30 random rows: 9 HF features recomputed by direct window filtering on raw 5m/15m files (float32 tolerance)")

    m = P.label24.notna()
    y = P.label24[m].values.astype(int)
    a_new, a_old = V24.auc(y, P.R24_HF[m].values), V24.auc(y, P.R24_base[m].values)
    assert abs(a_new - C["R24_HF_skill"]["auc"]) < 1e-9 and abs(a_old - C["R24_base_skill_same_rows"]["auc"]) < 1e-9
    assert abs((a_new - a_old) - C["paired_auc_diff"]["diff"]) < 1e-9
    print(f"[V3 PASS] AUC R24_HF {a_new:.4f}, baseline {a_old:.4f}, diff {a_new - a_old:+.4f}")

    V24.START, V24.END_BAR = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30 23:00")
    B = {s: V24.bars(s) for s in sorted(P.symbol.unique())}
    final, n = V24.sim(P, "R24_HF", 24, B)
    c = C["portfolio"]["R24_HF"]
    assert abs(final - c["final"]) < 0.01 and n == c["trades"], (final, c["final"], n, c["trades"])
    print(f"[V4 PASS] R24_HF re-simulated: final {final:.2f}, trades {n}")

    g, pf = C["gates"], C["portfolio"]
    rec = dict(G2_added_skill=C["paired_auc_diff"]["ci_low"] > 0, G3a_calmar=pf["R24_HF"]["calmar"] > 0.92,
               G3b_trade_ci=pf["R24_HF"]["trade_ci_low_pct"] > 0, G3c_cost040=pf["R24_HF_cost040"]["cagr_pct"] > 0,
               G4_pre2020=C["pre2020_HF"]["auc"] > C["pre2020_base"]["auc"] and C["pre2020_HF"]["ci_low"] > 0.5)
    assert all(rec[k] == g[k] for k in rec), (rec, g)
    print(f"[V5 PASS] gates recomputed -> {g['decision']}")


if __name__ == "__main__":
    main()
