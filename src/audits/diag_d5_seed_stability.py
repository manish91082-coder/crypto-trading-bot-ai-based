"""POST-HOC diagnostic (after verify_disc check 5 FAILED): seed / draw-count stability of the D5 RC and SPA p-values for
U1 net_taker and excess. Same statistic definitions as the DISC protocol; 10 seeds x {2,000, 4,000} draws."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
TR6 = R_ / "data" / "derived" / "tf_edge_map" / "U1"
DEVM = [str(p) for p in pd.period_range("2020-02", "2025-09", freq="M")]
cells = {"excess": [], "net_taker": []}
for d in sorted(TR6.iterdir()):
    A = pd.concat([pd.read_parquet(f, columns=["fam", "side", "period", "entry_time", "gross", "ctrl", "fund"]) for f in d.glob("*.parquet")])
    A = A[A.period < 2]; A["m"] = pd.to_datetime(A.entry_time).dt.strftime("%Y-%m")
    for (fi, sd), g in A.groupby(["fam", "side"]):
        if len(g) < 30:
            continue
        for st, v in (("excess", g.gross - g.ctrl), ("net_taker", g.gross - 0.00108 - g.fund)):
            k = v.notna().values
            agg = pd.DataFrame(dict(m=g.m.values[k], v=v.values[k])).groupby("m").v.agg(["sum", "count"]).reindex(DEVM).fillna(0.0)
            cells[st].append((agg["sum"].values, agg["count"].values))
nm = len(DEVM); thr = -np.sqrt(2 * np.log(np.log(nm)))
rows = []
for st in ("excess", "net_taker"):
    Sm = np.array([a for a, b in cells[st]]); Nm = np.array([b for a, b in cells[st]]); m = Sm.sum(1) / Nm.sum(1)
    for nb in (2000, 4000):
        for seed in range(10):
            W = np.random.default_rng(1000 + seed).multinomial(nm, np.full(nm, 1 / nm), size=nb).astype(float)
            mb = (W @ Sm.T) / np.maximum(W @ Nm.T, 1); se = mb.std(axis=0, ddof=1)
            T = m / se; Tm = max(T.max(), 0.0)
            rc = ((mb - m) / se).max(axis=1); spa = ((mb - m + np.where(T <= thr, m, 0.0)) / se).max(axis=1)
            rows.append(dict(stat=st, draws=nb, seed=seed, T_max=float(T.max()), p_RC=float((rc >= Tm).mean()), p_SPA=float((np.maximum(spa, 0) >= Tm).mean())))
D = pd.DataFrame(rows)
out = R_ / "logs" / "research_tf_edge_map" / "disc" / "D5_seed_stability_POSTHOC.csv"
D.to_csv(out, index=False)
print(D.groupby(["stat", "draws"])[["T_max", "p_RC", "p_SPA"]].agg(["min", "median", "max"]).round(4).to_string())
