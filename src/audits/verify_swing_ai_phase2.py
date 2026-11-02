"""
Independent verifier for Swing Anatomy Phase 2 (logs/research_swing_ai_phase2).
V1 protocol / events / predictions hashes.
V2 for 4 random (coin, tf): rebuild bars, re-derive entry / exit bars from the causal state with a plain loop, and the
   net return arithmetic; must equal the stored events exactly (same set, same i/j, net within 1e-12).
V3 G0 re-derived with a plain dictionary join to the Phase 1 legs (match share, max factor diff).
V4 AUC (plain Mann-Whitney) for ALL / P1 / P2 / CONTROL, the selection flag (p >= thr) and the money means recomputed.
V5 gates re-derived.
"""
import sys
import json
import random
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "research", SRC / "analytics", SRC / "pipeline_1d"):
    sys.path.insert(0, str(p))
import swing_strategy_1d as E
import swing_anatomy_phase1 as P
import swing_ai_phase2 as Q

C = json.loads((Q.OUT / "claims.json").read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mw_auc(y, p):
    pos = [s for s, t in zip(p, y) if t == 1]
    neg = [s for s, t in zip(p, y) if t == 0]
    allv = sorted([(s, 1) for s in pos] + [(s, 0) for s in neg])
    ranks, k = {}, 0
    vals = [v for v, _ in allv]
    while k < len(vals):
        m = k
        while m + 1 < len(vals) and vals[m + 1] == vals[k]:
            m += 1
        ranks[vals[k]] = (k + m) / 2 + 1
        k = m + 1
    rs = sum(ranks[s] for s in pos)
    return (rs - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    assert sha(Q.OUT / Q.PROTO) == (Q.OUT / "PHASE2_PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    assert sha(Q.DER / "events.parquet") == C["events_sha256"]
    assert sha(Q.OUT / "test_predictions.csv") == C["test_predictions_sha256"]
    print("[V1 PASS] protocol, events and predictions hashes")

    Ev = pd.read_parquet(Q.DER / "events.parquet")
    random.seed(7)
    picks = random.sample([(c, tf) for c in P.COINS for tf in Q.TFS], 4)
    for coin, tf in picks:
        bars, _ = Q.coin_bars(coin, [])
        b = bars[tf]
        st = E.zz(b, Q.KP)["state"]
        cl = b.close.values
        mine = []
        for i in range(len(st)):
            if st[i] == 1 and (i == 0 or st[i - 1] != 1):
                j = next((t for t in range(i + 1, len(st)) if st[t] == -1), None)
                if j is not None:
                    mine.append((i, j, cl[j] / cl[i] * (1 - 0.0025) / (1 + 0.0025) - 1))
        got = Ev[(Ev.coin == coin) & (Ev.tf == tf)].sort_values("i")
        assert len(mine) == len(got), (coin, tf, len(mine), len(got))
        for (i, j, n), r in zip(mine, got.itertuples()):
            assert i == r.i and j == r.j and abs(n - r.net) < 1e-12, (coin, tf, i)
        print(f"   {coin} {tf}: {len(mine)} events re-derived")
    print("[V2 PASS] entry / exit / net re-derived with a plain loop")

    L = pd.read_parquet(P.DER / "legs_all.parquet")
    L = L[(L.K == Q.KP) & (L.direction == "Rally") & L.tf.isin(Q.TFS)]
    ref = {(r["coin"], r["tf"], int(r["confirm_i"])): r for r in L.to_dict("records")}
    hit, worst = 0, 0.0
    for r in Ev.to_dict("records"):
        q = ref.get((r["coin"], r["tf"], int(r["i"])))
        if q is None:
            continue
        hit += 1
        for f in P.FACTORS:
            a, b = r[f"c_{f}"], q[f"c_{f}"]
            if not (pd.isna(a) and pd.isna(b)):
                worst = max(worst, abs(float(a) - float(b)) if not (pd.isna(a) or pd.isna(b)) else float("inf"))
    assert hit == C["G0"]["matched"] and abs(worst - C["G0"]["max_abs_diff"]) < 1e-15
    print(f"[V3 PASS] G0: {hit}/{len(Ev)} events matched to Phase 1 legs ({hit/len(Ev):.4f}), max factor diff {worst}")

    T = pd.read_csv(Q.OUT / "test_predictions.csv", parse_dates=["entry_end"])
    assert ((T.p_ai >= T.thr) == T.selected).all()
    for name, d, col in (("AI_all", T, "p_ai"), ("CONTROL_all", T, "p_control"),
                         ("AI_P1", T[T.entry_end < Q.P1[1]], "p_ai"), ("AI_P2", T[T.entry_end >= Q.P2[0]], "p_ai")):
        a = mw_auc(d.label.tolist(), d[col].tolist())
        assert abs(a - C[name]["auc"]) < 1e-9, (name, a, C[name]["auc"])
        print(f"   {name}: AUC {a:.4f} (n {len(d)})")
    for name, d in (("money_all", T), ("money_P1", T[T.entry_end < Q.P1[1]]), ("money_P2", T[T.entry_end >= Q.P2[0]])):
        s = d.selected.values
        ma, msel = d.net.mean() * 100, d.net[s].mean() * 100
        assert abs(round(ma, 4) - C[name]["mean_all_pct"]) < 1e-9 and abs(round(msel, 4) - C[name]["mean_sel_pct"]) < 1e-9
        print(f"   {name}: all {ma:.3f} %, selected {msel:.3f} %, diff {msel - ma:.3f} %")
    print("[V4 PASS] AUCs, selection and money means recomputed")

    g = C["gates"]
    re_ = dict(G2=C["AI_all"]["ci_low"] > 0.5 and C["AI_all"]["auc"] > C["CONTROL_all"]["auc"],
               G3=C["AI_P1"]["ci_low"] > 0.5 and C["AI_P2"]["ci_low"] > 0.5,
               G4=C["money_all"]["diff_ci_low_pct"] > 0 and C["money_P1"]["diff_pct"] > 0 and C["money_P2"]["diff_pct"] > 0)
    assert all(g[k] == v for k, v in re_.items())
    print(f"[V5 PASS] gates re-derived: {g}")


if __name__ == "__main__":
    main()
