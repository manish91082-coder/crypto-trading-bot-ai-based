"""Independent verifier of NP2 DV stage (NP2_PROTOCOL_PREREGISTERED.md, SHA b6d8d754...). Imports nothing from src/research.
Recomputes past-only percentiles, EQ scores, ridge beta (own normal equations via np.linalg.inv), every DV trade, the summaries and the selection."""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
O = P / "logs/research_nonprice"
FAIL = []


def check(n, ok, msg=""):
    print(f"[{n} {'OK' if ok else 'FAIL'}] {msg}", flush=True)
    if not ok:
        FAIL.append(n)


def close(a, b, tol=1e-8):
    if (a != a) and (b != b):
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


h = (O / "NP2_PROTOCOL_SHA256.txt").read_text().split()[0]
check("P0", hashlib.sha256((O / "NP2_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == h, "NP2 protocol matches its SHA")
COST = 2 * json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))["rules"]["paper_futures_taker_per_side"]
X = pd.read_parquet(O / "np1_features_1h.parquet")
X = X[X.t < pd.Timestamp("2025-01-01")]
S1 = {"1h": ["OI_CHG_1H", "OI_CHG_24H", "FUT_TAKER_1H", "SPOT_TAKER_1H", "DEPTH_IMB1_1H", "DEPTH_IMB5_1H", "CTRL_RET_1H", "CTRL_RET_24H"],
      "4h": ["OI_CHG_24H", "SPOT_TAKER_1H", "DEPTH_IMB1_1H", "DEPTH_IMB5_1H", "CTRL_RET_24H"]}
s1D = pd.read_csv(O / "s1_D.csv")
s1V = pd.read_csv(O / "s1_V.csv")
conf = set(map(tuple, s1V[s1V.s1_confirmed][["feature", "h"]].to_numpy()))
check("P1", all((f, hh) in conf for hh in S1 for f in S1[hh]) and len([c for c in conf if c[1] in S1]) == 13,
      "feature sets equal the NP1 S1-confirmed features for 1h / 4h")
SIGN = {(r.feature, r.h): (1 if r.mean_monthly_ic > 0 else -1) for r in s1D.itertuples()}


def pct(t, x):
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        lo = int(np.searchsorted(t, t[i] - np.timedelta64(90, "D"), side="left"))
        past = x[lo:i]
        if len(past) >= 30:
            out[i] = float((past < x[i]).sum()) / len(past)
    return out


dv = pd.read_csv(O / "np2_dv_summary.csv")
trs = pd.read_parquet(O / "np2_dv_trades.parquet")
bad_tr = bad_s = 0
mine_sum = []
for hh in ("1h", "4h"):
    n = 1 if hh == "1h" else 4
    S = X[X.t.dt.hour % n == 0]
    for setname in ("ALL", "NODEPTH"):
        feats = [f for f in S1[hh] if setname == "ALL" or not f.startswith("DEPTH")]
        cols = {}
        for f in feats:
            d = S[["t", f]].dropna()
            cols[f] = pd.Series(pct(d.t.to_numpy(), d[f].to_numpy()), index=d.t.to_numpy())
        U = pd.DataFrame(cols).dropna() - 0.5
        r = S.set_index("t")[f"r_{hh}"]
        U["r"] = r.reindex(U.index).to_numpy()
        U = U.dropna()
        ds = pd.Timestamp("2023-01-01") if setname == "ALL" else pd.Timestamp("2020-09-01")
        U = U[U.index >= ds]
        U["per"] = np.where(U.index < pd.Timestamp("2024-01-01"), "D", "V")
        Xm = U[feats].to_numpy()
        sg = np.array([SIGN[(f, hh)] for f in feats])
        Dm = U.per.to_numpy() == "D"
        A = Xm[Dm]
        beta = np.linalg.inv(A.T @ A + 0.1 * Dm.sum() * np.eye(len(feats))) @ (A.T @ U.r.to_numpy()[Dm])
        for kind, pars in (("EQ", [0.15, 0.2, 0.25]), ("RIDGE", [0.8, 0.9, 0.95])):
            for par in pars:
                if kind == "EQ":
                    sc = (Xm * sg).mean(axis=1)
                    side = np.where(sc >= par, 1, np.where(sc <= -par, -1, 0))
                else:
                    pr = Xm @ beta
                    thr = np.quantile(np.abs(pr[Dm]), par)
                    side = np.where(np.abs(pr) >= thr, np.sign(pr), 0)
                cfg = f"{hh}|{setname}|{kind}|{par}"
                net = (side * U.r.to_numpy() - COST) * 100
                k = side != 0
                g = trs[trs.cfg == cfg]
                if not (len(g) == int(k.sum()) and np.allclose(g.net.to_numpy(), net[k], rtol=0, atol=1e-9)
                        and (g.side.to_numpy() == side[k]).all()):
                    bad_tr += 1
                for per in ("D", "V"):
                    m = k & (U.per.to_numpy() == per)
                    v = net[m]; tt = U.index[m]
                    mean = v.mean()
                    wk = {}
                    for ti, x in zip(tt, v):
                        kk = tuple(pd.Timestamp(ti).isocalendar())[:2]; w = wk.setdefault(kk, [0.0, 0]); w[0] += x; w[1] += 1
                    se = math.sqrt(len(wk) / (len(wk) - 1) * sum((w[0] - mean * w[1]) ** 2 for w in wk.values())) / len(v)
                    row = dv[(dv.cfg == cfg) & (dv.period == per)].iloc[0]
                    if not (row.trades == len(v) and close(row.mean_net_pct, mean) and close(row.t_cluster, mean / se, 1e-7)):
                        bad_s += 1
                    mine_sum.append((cfg, per, mean, mean / se))
check("P2", bad_tr == 0, f"24 configs: every DV trade recomputed (own percentiles, scores, ridge beta); {bad_tr} configs differ")
check("P3", bad_s == 0, f"48 D / V summaries (trades, mean net, weekly-cluster t) recomputed; {bad_s} differ")
d = {c: (m, t) for c, p, m, t in mine_sum if p == "D"}
v = {c: m for c, p, m, t in mine_sum if p == "V"}
cand = [c for c in d if d[c][0] > 0 and d[c][1] >= 2.0 and v[c] > 0]
sel = json.loads((O / "np2_selection.json").read_text(encoding="utf-8"))
check("P4", sorted(cand, key=lambda c: -d[c][1])[:3] == sel["selected"], f"selection by the locked rule: candidates {cand}, selected {sel['selected']}")
check("P5", not (trs.period == "H").any(), "no H row in the DV stage")
src = (P / "src/research/nonprice_np2.py").read_text(encoding="utf-8")
check("P6", not re.findall(r"(?<![\w.])0\.0*(?:46|85|92|4|17|18|036|075)\b", src), "no fee literal in NP2 code")
print("\nRESULT:", "ALL PASS" if not FAIL else f"FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
