"""Replay gate for the PAPER-N1 recorder (logs/paper_n1/PAPER_N1_PROTOCOL_PREREGISTERED.md): the live engine run in replay mode
(2025-03-01 .. 2025-10-01) vs the N1 FINAL backtest ledger (data/derived/n1/trades_K1.parquet).
P1 ledger hash chain   P2 A/B/C entries: backtest -> replay >= 95% (same time, price 1e-9), replay -> backtest >= 95%
P3 exit times agree >= 95% of matched trades closed inside the window   P4 D leg sets agree >= 90% of rebalances   (info: routing flags)"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
root = R_ / "logs" / "paper_n1" / "replay"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


L = [json.loads(l) for l in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
prev, chain = "GENESIS", True
for r in L:
    body = {k: v for k, v in r.items() if k != "line_sha256"}
    chain &= r["prev_sha256"] == prev and hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == r["line_sha256"]
    prev = r["line_sha256"]
ok("P1", chain, f"{len(L)} cycles, hash chain intact; config SHA constant: {len({r['config_sha256'] for r in L}) == 1}")

opens, closes = [], []
for r in L:
    for a in r["actions"]:
        (opens if a["a"] == "open" else closes).append(dict(T=pd.Timestamp(r["T"]), **a))
O = pd.DataFrame(opens); Cx = pd.DataFrame(closes)
t0, t1 = pd.Timestamp("2025-03-15"), pd.Timestamp("2025-10-01")
rep = O[(O.why == "signal") & (O["T"] >= t0) & ~O.k.str.startswith("D|")].copy()
rep["key"] = rep.k + "|" + rep["T"].astype(str)
B = pd.read_parquet(R_ / "data" / "derived" / "n1" / "trades_K1.parquet")
B["entry_time"] = pd.to_datetime(B.entry_time)
grid0 = pd.Timestamp("2020-02-01")
B["exit_time"] = grid0 + pd.to_timedelta(B.E.astype(int), unit="h")
bt = B[B.sleeve.isin(["A", "B", "C"]) & (B.entry_time >= t0) & (B.entry_time < t1)].copy()
bt["key"] = bt.sleeve + "|" + bt.coin + "|" + bt.tf + "|" + bt.fam.astype(int).astype(str) + "|" + bt.entry_time.astype(str)
m = bt.merge(rep[["key", "px", "venue"]], on="key", how="left")
found = m.px.notna()
pxok = (np.abs(m.px[found] - m.entry[found]) <= 1e-9 * m.entry[found]).mean() if found.any() else 0
back_in = rep.key.isin(set(bt.key)).mean()
miss = m[~found].groupby(["sleeve", "tf"]).size().to_dict()
extra = rep[~rep.key.isin(set(bt.key))].k.str.split("|").str[:3].str.join("|").value_counts().head(8).to_dict()
ok("P2", found.mean() >= 0.95 and back_in >= 0.95 and pxok == 1.0,
   f"backtest entries found in replay {found.mean():.4f} ({found.sum()}/{len(m)}), replay entries in backtest {back_in:.4f} ({len(rep)}), "
   f"entry price match {pxok:.4f}; missing by sleeve/tf {miss}; extra (top) {extra}")

Cx["entry_T"] = pd.to_datetime(Cx.t_entry)
cl = Cx[Cx.why == "signal"].copy()
cl["key"] = cl.k + "|" + cl.entry_T.astype(str)
mm = bt[bt.exit_time < t1].merge(cl[["key", "T"]], on="key", how="inner")
ex_ok = (mm["T"] == mm.exit_time).mean() if len(mm) else 0
ok("P3", ex_ok >= 0.95, f"exit time agreement {ex_ok:.4f} on {len(mm)} matched trades closed inside the window")

Dr = O[O.k.str.startswith("D|") & (O["T"] >= t0)]
Db = B[(B.sleeve == "D") & (B.entry_time >= t0) & (B.entry_time < t1)]
agree, n = 0, 0
for T, g in Db.groupby("entry_time"):
    rs = set(Dr[Dr["T"] == T].k.str.split("|").str[1] + Dr[Dr["T"] == T].side.astype(int).astype(str))
    bs = set(g.coin + g.side.astype(int).astype(str))
    n += 1; agree += int(rs == bs)
ok("P4", n > 0 and agree / n >= 0.90, f"D rebalances with identical leg sets {agree}/{n}")
F = pd.read_parquet(R_ / "logs" / "research_n3_execution" / "N3_fills.parquet")
F["key"] = F.sleeve + "|" + F.coin + "|" + F.tf + "|" + F.fam.astype(int).astype(str) + "|" + pd.to_datetime(F.entry_time).astype(str)
rv = rep[rep.k.str[0].isin(["A", "B"])].merge(F[["key", "spot"]], on="key", how="inner")
print(f"[INFO] routing agreement with N3 (A/B, {len(rv)} matched): {((rv.venue == 'spot') == rv.spot).mean():.4f}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
