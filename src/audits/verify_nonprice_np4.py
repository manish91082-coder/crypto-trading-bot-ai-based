"""Independent verifier of NP4 (NP4_PROTOCOL_PREREGISTERED.md, SHA 9ef4dd3e...). Imports nothing from src/research; plain loops."""
import hashlib
import json
import math
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parents[2]
O = P / "logs/research_nonprice"
FAIL = []


def check(n, ok, msg=""):
    print(f"[{n} {'OK' if ok else 'FAIL'}] {msg}", flush=True)
    if not ok:
        FAIL.append(n)


h = (O / "NP4_PROTOCOL_SHA256.txt").read_text().split()[0]
check("R0", hashlib.sha256((O / "NP4_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == h, "NP4 protocol matches its SHA")
fees = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
FUT, SPOT = 2 * fees["rules"]["paper_futures_taker_per_side"], 2 * fees["rules"]["paper_spot_per_side"]
X = pd.read_parquet(O / "np1_features_1h.parquet")
S = X[X.t.dt.hour == 0][["t", "PREM_Z", "r_24h"]]
S = S[S.PREM_Z.notna()]
tt, zz, rr = list(S.t), list(S.PREM_Z), list(S.r_24h)
H0, H1 = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-09-30")
rows = []
for i in range(len(tt)):
    if not (H0 <= tt[i] <= H1) or rr[i] != rr[i]:
        continue
    past = [zz[j] for j in range(i) if tt[j] >= tt[i] - timedelta(days=90)]
    if len(past) < 30:
        continue
    p = sum(1 for v in past if v < zz[i]) / len(past)
    rows.append((tt[i], p, rr[i]))
mine = {}
for c, cost in (("P1", FUT), ("P2", FUT), ("P2_SPOT_INFO", SPOT)):
    lst = []
    for t, p, r in rows:
        s = (-1 if p >= 0.8 else (1 if p <= 0.2 else 0)) if c == "P1" else (1 if p <= 0.2 else 0)
        if s:
            lst.append((t, s, (s * r - cost) * 100))
    mine[c] = lst
st = pd.read_csv(O / "np4_trades.csv", parse_dates=["t"])
ok = all(len(st[st.cfg == c]) == len(v) and all(a[0] == b.t and a[1] == b.side and abs(a[2] - b.net) < 1e-9 for a, b in zip(v, st[st.cfg == c].itertuples()))
         for c, v in mine.items())
check("R1", ok, f"every H trade recomputed: {[(c, len(v)) for c, v in mine.items()]}")
sm = pd.read_csv(O / "np4_summary.csv").set_index("cfg")
bad = 0
for c, v in mine.items():
    m = sum(x[2] for x in v) / len(v)
    wk = {}
    for t, s, n in v:
        k = tuple(t.isocalendar())[:2]; w = wk.setdefault(k, [0.0, 0]); w[0] += n; w[1] += 1
    se = math.sqrt(len(wk) / (len(wk) - 1) * sum((w[0] - m * w[1]) ** 2 for w in wk.values())) / len(v)
    mo = {}
    for t, s, n in v:
        mo[t.strftime("%Y-%m")] = mo.get(t.strftime("%Y-%m"), 0.0) + n
    mp = sum(1 for x in mo.values() if x > 0)
    y25 = sum(n for t, s, n in v if t.year == 2025); y26 = sum(n for t, s, n in v if t.year == 2026)
    passes = m > 0 and m - 2.24 * se > 0 and mp >= 13 and y25 > 0 and y26 > 0
    r = sm.loc[c]
    bad += not (abs(r.mean_net_pct - m) < 1e-9 and abs(r.lb_224 - (m - 2.24 * se)) < 1e-7 and r.months_pos == mp
                and abs(r.sum_2025 - y25) < 1e-7 and abs(r.sum_2026 - y26) < 1e-7 and (c == "P2_SPOT_INFO" or bool(r.passes) == passes))
check("R2", bad == 0, f"summaries, months+, yearly sums and gate verdicts recomputed: {bad} differ; P1 passes {sm.loc['P1', 'passes']}, P2 passes {sm.loc['P2', 'passes']}")
dl = pd.read_csv(O / "np4_daily.csv")
check("R3", dl.groupby("cfg").size().eq(638).all(), f"daily entries: every one of the 638 H days per config ({len(dl)} rows)")
print("\nRESULT:", "ALL PASS" if not FAIL else f"FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
