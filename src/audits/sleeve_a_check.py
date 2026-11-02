"""PAPER-N1 sleeve A live-vs-backtest consistency check (logs/paper_n1/SLEEVE_A_CHECK_PROTOCOL_PREREGISTERED.md).
T1 backtest trade stats, T2 comparable-window percentiles (the decision), T4 init/signal split. T3 is in verify_sleeve_a_check.py.
Run on the laptop: python src/audits/sleeve_a_check.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
LOG = R_ / "logs" / "paper_n1"
OUT = LOG / "sleeve_a_check"
CFG = json.loads((R_ / "deploy" / "paper_n1_config.json").read_text())
CORE10 = CFG["core10"]
TFH = {"4h": 4, "8h": 8, "12h": 12, "1D": 24}
L0, L1 = pd.Timestamp("2026-10-21 04:00"), pd.Timestamp("2026-10-24 04:00")
S0, SEND = pd.Timestamp("2020-03-01 04:00"), pd.Timestamp("2025-09-01 00:00")
W = pd.Timedelta(hours=72)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


proto = LOG / "SLEEVE_A_CHECK_PROTOCOL_PREREGISTERED.md"
assert sha(proto) == (LOG / "SLEEVE_A_CHECK_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"

# ---- live closes in L, with how each position was opened (T4)
recs = [json.loads(l) for l in (OUT / "ledger_snapshot.jsonl").read_text().splitlines() if l.strip()]
recs = [r for r in recs if pd.Timestamp(r["T"]) <= L1]
opened = {}
live = []
for r in recs:
    T = pd.Timestamp(r["T"])
    for a in r["actions"]:
        if not a["k"].startswith("A|"):
            continue
        if a["a"] == "open":
            opened[a["k"]] = a["why"]
        elif a["a"] == "close" and L0 < T <= L1:
            live.append(dict(k=a["k"], T=T, r=a["px"] / a["entry"] - 1, how=opened.get(a["k"], "before snapshot")))
live = pd.DataFrame(live)
wr_live, mr_live = float((live.r > 0).mean()), float(live.r.mean())


# ---- M_live from the paper engine's source (Binance spot 4h opens), fetched on the VM (the laptop cannot reach
#      api.binance.com) into spot_4h_live.json; its SHA goes into the report
SPOT = json.loads((OUT / "spot_4h_live.json").read_text())
assert "api.binance.com/api/v3/klines" in SPOT["source"]


def spot_open(sym, t):
    ms = int(t.timestamp() * 1000)
    k = [x for x in SPOT["data"][sym] if x[0] == ms]
    assert len(k) == 1, (sym, t)
    return float(k[0][1])


m_live_by = {c: spot_open(c, L1) / spot_open(c, L0) - 1 for c in CORE10}
M_live = float(np.mean(list(m_live_by.values())))

# ---- backtest
T_ = pd.read_parquet(R_ / "data" / "derived" / "n1" / "trades_K1.parquet")
A = T_[T_.sleeve == "A"].copy()
assert set(A.side) == {1} and set(A.coin) == set(CORE10)
A["r"] = A.X / A.entry - 1
A["exit"] = A.entry_time + pd.to_timedelta(A.hold * A.tf.map(TFH), unit="h")
t1 = dict(n=len(A), win_rate=float((A.r > 0).mean()), mean_r=float(A.r.mean()), median_r=float(A.r.median()),
          by_tf={tf: dict(n=int(len(g)), win_rate=float((g.r > 0).mean()), mean_r=float(g.r.mean())) for tf, g in A.groupby("tf")})
opens = {c: pd.read_parquet(R_ / "data" / "derived" / "n1" / "bars1h" / f"{c}.parquet").open for c in CORE10}
starts = []
s = S0
while s + W <= SEND:
    starts.append(s); s += W
A["win"] = np.ceil((A.exit - S0) / W).astype(int) - 1            # window j = (S0 + j W, S0 + (j+1) W]
A = A[(A.win >= 0) & (A.win < len(starts))]
rows = []
for j, st in enumerate(starts):
    g = A[A.win == j]
    M = float(np.mean([opens[c].get(st + W, np.nan) / opens[c].get(st, np.nan) - 1 for c in CORE10]))
    rows.append(dict(start=st, n=len(g), win_rate=float((g.r > 0).mean()) if len(g) else np.nan, mean_r=float(g.r.mean()) if len(g) else np.nan, M=M))
Wn = pd.DataFrame(rows)
el = Wn[(Wn.n >= 20) & Wn.M.notna()].copy()
el["dist"] = (el.M - M_live).abs()
m = max(30, int(np.ceil(0.2 * len(el))))
comp = el.sort_values(["dist", "start"]).head(m)
p_wr, p_ret = float((comp.win_rate <= wr_live).mean()), float((comp.mean_r <= mr_live).mean())
rep = dict(
    protocol_sha256=sha(proto), code_sha256=sha(__file__), ledger_snapshot_sha256=sha(OUT / "ledger_snapshot.jsonl"), spot_4h_live_sha256=sha(OUT / "spot_4h_live.json"),
    trades_K1_sha256=sha(R_ / "data" / "derived" / "n1" / "trades_K1.parquet"),
    live=dict(n=len(live), wins=int((live.r > 0).sum()), win_rate=wr_live, mean_r=mr_live, median_r=float(live.r.median()),
              worst_r=float(live.r.min()), best_r=float(live.r.max()), M_live=M_live, M_live_by_coin=m_live_by,
              T4_by_open=live.groupby("how").r.agg(["count", lambda x: int((x > 0).sum()), "mean"]).rename(
                  columns={"<lambda_0>": "wins"}).to_dict("index")),
    T1_backtest_all=t1,
    T2=dict(n_windows=len(Wn), n_eligible=len(el), n_comparable=len(comp), M_range=[float(comp.M.min()), float(comp.M.max())],
            comp_win_rate_median=float(comp.win_rate.median()), comp_mean_r_median=float(comp.mean_r.median()),
            comp_n_median=float(comp.n.median()), p_wr=p_wr, p_ret=p_ret,
            all_eligible=dict(p_wr=float((el.win_rate <= wr_live).mean()), p_ret=float((el.mean_r <= mr_live).mean()),
                              win_rate_median=float(el.win_rate.median())),
            min_win_rate_comparable=float(comp.win_rate.min()), windows_with_win_rate_le_live=comp[comp.win_rate <= wr_live].start.astype(str).tolist()),
    verdict="consistent" if (p_wr >= 0.05 and p_ret >= 0.05) else "not consistent",
)
OUT.mkdir(parents=True, exist_ok=True)
comp.to_csv(OUT / "comparable_windows.csv", index=False)
Wn.to_csv(OUT / "all_windows.csv", index=False)
live.to_csv(OUT / "live_closes.csv", index=False)
f = OUT / "SLEEVE_A_CHECK_REPORT.json"
f.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
(OUT / "SLEEVE_A_CHECK_REPORT_SHA256.txt").write_text(sha(f) + "  SLEEVE_A_CHECK_REPORT.json\n")
print(json.dumps(rep, indent=1, default=str))
sys.exit(0)
