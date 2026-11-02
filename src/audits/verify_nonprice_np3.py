"""Independent verifier of NP3 DV (NP3_PROTOCOL_PREREGISTERED.md, SHA 8e4488b4...). Imports nothing from src/research.
Signals must equal the (already verified) NP2 DV signal list; fills / exits / nets are recomputed from raw 5m bars with plain loops."""
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parents[2]
O = P / "logs/research_nonprice"
FAIL = []


def check(n, ok, msg=""):
    print(f"[{n} {'OK' if ok else 'FAIL'}] {msg}", flush=True)
    if not ok:
        FAIL.append(n)


h = (O / "NP3_PROTOCOL_SHA256.txt").read_text().split()[0]
check("Q0", hashlib.sha256((O / "NP3_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == h, "NP3 protocol matches its SHA")
fees = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
MK, TK = fees["futures_usdm"]["bnb_maker"], fees["rules"]["paper_futures_taker_per_side"]
f = pd.read_parquet(P / "data/external/binance_public/clean/fut5m.parquet")
bar = {t: (hh, ll, cc) for t, hh, ll, cc in zip(f.time, f.high, f.low, f.close)}
M = pd.Timedelta(minutes=5)
sig = pd.read_parquet(O / "np2_dv_trades.parquet")
tr = pd.read_parquet(O / "np3_dv_trades.parquet")
mine = []
for r in sig.itertuples():
    hrs = 1 if r.cfg.startswith("1h") else 4
    for mode in ("XT", "XM"):
        P_ = bar[r.t - M][2]
        fill = None
        for k in range(3):
            b = bar[r.t + k * M]
            if (r.side > 0 and b[1] < P_) or (r.side < 0 and b[0] > P_):
                fill = k; break
        if fill is None:
            continue
        te = r.t + pd.Timedelta(hours=hrs)
        Q = bar[te - M][2]
        if mode == "XT":
            x, xc = Q, TK
        else:
            ok = any((r.side > 0 and bar[te + k * M][0] > Q) or (r.side < 0 and bar[te + k * M][1] < Q) for k in range(3))
            x, xc = (Q, MK) if ok else (bar[te + 2 * M][2], TK)
        g = r.side * (x / P_ - 1)
        mine.append((f"{r.cfg}|{mode}", r.t, int(r.side), (g - MK - xc) * 100))
key = lambda z: (z[0], z[1])
a = sorted(mine, key=key)
b = sorted([(r.cfg, r.t, int(r.side), r.net) for r in tr.itertuples()], key=key)
same = len(a) == len(b) and all(x[0] == y[0] and x[1] == y[1] and x[2] == y[2] and abs(x[3] - y[3]) < 1e-9 for x, y in zip(a, b))
check("Q1", same, f"NP3 trades recomputed from raw bars: mine {len(a)}, stored {len(b)} (signals {len(sig)} x 2 exit modes)")
S = pd.read_csv(O / "np3_dv_summary.csv")
bad = 0
for (cfg, per), g in pd.DataFrame(a, columns=["cfg", "t", "side", "net"]).assign(
        per=lambda d: (d.t < pd.Timestamp("2024-01-01")).map({True: "D", False: "V"})).groupby(["cfg", "per"]):
    m = g.net.mean(); wk = {}
    for t, v in zip(g.t, g.net):
        k = tuple(t.isocalendar())[:2]; w = wk.setdefault(k, [0.0, 0]); w[0] += v; w[1] += 1
    se = math.sqrt(len(wk) / (len(wk) - 1) * sum((w[0] - m * w[1]) ** 2 for w in wk.values())) / len(g)
    row = S[(S.cfg == cfg) & (S.period == per)].iloc[0]
    bad += not (row.trades == len(g) and abs(row.mean_net_pct - m) < 1e-9 and abs(row.t_cluster - m / se) < 1e-6)
check("Q2", bad == 0, f"96 D / V summaries recomputed; {bad} differ")
d = S[S.period == "D"].set_index("cfg"); v = S[S.period == "V"].set_index("cfg")
cand = d[(d.mean_net_pct > 0) & (d.t_cluster >= 2.0) & (v.mean_net_pct > 0)].index.tolist()
sel = json.loads((O / "np3_selection.json").read_text(encoding="utf-8"))
check("Q3", cand == [] and sel["selected"] == [] or sorted(cand, key=lambda c: -d.t_cluster[c])[:3] == sel["selected"], f"selection: candidates {cand}, selected {sel['selected']}")
check("Q4", not (tr.period == "H").any(), "no H row in NP3 DV")
print("\nRESULT:", "ALL PASS" if not FAIL else f"FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
