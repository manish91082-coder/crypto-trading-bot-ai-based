"""Independent verifier for N3 (logs/research_n3_execution/N3_PROTOCOL_PREREGISTERED.md). Own code; does not import n3_execution.
X1 300 random entries: maker fill (strict trade-through) + stress fill + prices from raw 5m   X2 200 random routing decisions: trailing-7d
funding, PIT median hold, spot flag   X3 shortfall mean / CI and gate booleans from the files   X4 SHAs + registry T17"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_n3_execution"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


cl = json.loads((O_ / "claims_n3.json").read_text())
F = pd.read_parquet(O_ / "N3_fills.parquet")
F["entry_time"] = pd.to_datetime(F.entry_time); F["exit_time"] = pd.to_datetime(F.exit_time)
rng = np.random.default_rng(33)
pick = F.iloc[rng.choice(len(F), 300, replace=False)].sort_values("coin")
bad, cur, x = [], None, None
for r in pick.itertuples():
    if r.coin != cur:
        x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{r.coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
        x["timestamp"] = pd.to_datetime(x.timestamp); x = x.sort_values("timestamp").reset_index(drop=True); cur = r.coin
    w = x[(x.timestamp >= r.entry_time) & (x.timestamp < r.entry_time + pd.Timedelta(minutes=60))].head(12)
    lim = r.limit
    f = bool((w.low < lim).any()) if r.side == 1 else bool((w.high > lim).any())
    fs = bool((w.low < lim * (1 - 0.0005)).any()) if r.side == 1 else bool((w.high > lim * (1 + 0.0005)).any())
    p = lim if f else float(w.close.iloc[-1]); ps = lim if fs else float(w.close.iloc[-1])
    if not (f == r.filled and fs == r.filled_stress and abs(p - r.fill_px) < 1e-12 and abs(ps - r.fill_px_stress) < 1e-12
            and abs(float(w.open.iloc[0]) - lim) < 1e-12):
        bad.append(f"{r.coin} {r.entry_time} {r.side}: {f}/{r.filled} {fs}/{r.filled_stress} {p}/{r.fill_px}")
ok("X1", not bad, f"300 maker fills / stress fills / prices from raw 5m: mismatches {len(bad)} {bad[:2]}")

ab = F[F.sleeve.isin(["A", "B"])].reset_index(drop=True)
sel = ab.iloc[rng.choice(len(ab), 200, replace=False)]
bad2, fc = [], {}
for r in sel.itertuples():
    if r.coin not in fc:
        f = pd.read_csv(R_ / "data" / "futures_um" / f"{r.coin}_funding.csv"); f["time"] = pd.to_datetime(f.time); fc[r.coin] = f.sort_values("time")
    f = fc[r.coin]
    t7 = f.funding_rate[(f.time >= r.entry_time - pd.Timedelta(days=7)) & (f.time < r.entry_time)]
    tr7 = t7.mean() if len(t7) else np.nan
    prior = ab[(ab.sleeve == r.sleeve) & (ab.tf == r.tf) & (ab.exit_time < r.entry_time)].hold_h
    kh = float(np.median(prior)) / 8.0 if len(prior) >= 30 else np.nan
    sp = bool(np.isfinite(tr7) and np.isfinite(kh) and tr7 * kh > 0.00062)
    e1 = (np.isnan(tr7) and np.isnan(r.trailing7)) or abs(tr7 - r.trailing7) < 1e-15
    e2 = (np.isnan(kh) and np.isnan(r.k_hold)) or abs(kh - r.k_hold) < 1e-12
    if not (e1 and e2 and sp == r.spot):
        bad2.append(f"{r.coin} {r.entry_time}: tr7 {tr7}/{r.trailing7} kh {kh}/{r.k_hold} spot {sp}/{r.spot}")
ok("X2", not bad2, f"200 routing decisions (trailing funding, PIT median hold, spot flag): mismatches {len(bad2)} {bad2[:2]}")

dev = (F.entry_time >= "2020-02-01") & (F.entry_time < "2025-10-01")
sf = F.side * (F.fill_px - F.limit) / F.limit + np.where(F.filled, 0.00018, 0.00054) - 0.00054
sd = pd.Series(sf[dev].values, index=F.entry_time[dev].dt.to_period("M").astype(str).values)
mon = sd.groupby(level=0).agg(["sum", "count"])
W = np.random.default_rng(20261026).multinomial(len(mon), np.full(len(mon), 1 / len(mon)), size=2000)
bm = (W @ mon["sum"].values) / (W @ mon["count"].values)
ci = (float(np.quantile(bm, .025)), float(np.quantile(bm, .975)))
Rr = pd.read_csv(O_ / "N3_results.csv")
cal = {(q.variant, q.window): q.calmar for q in Rr.itertuples()}
gk = True
for v in [k for k in ("X1", "X1s", "X2", "X3") if k in cl["results"]]:
    g = cl["results"][v]["gates"]
    gk &= g["Q1_dev"] == bool(cal[(v, "dev")] > cal[("base", "dev")])
    gk &= g["Q2_P1_P2"] == bool(cal[(v, "P1")] > cal[("base", "P1")] and cal[(v, "P2")] > cal[("base", "P2")])
ad = cl["adverse_selection"]
ok("X3", abs(sd.mean() - ad["shortfall_mean"]) < 1e-15 and max(abs(ci[0] - ad["shortfall_ci"][0]), abs(ci[1] - ad["shortfall_ci"][1])) < 1e-15 and gk
   and cl["results"]["X1"]["gates"]["Q3_shortfall_ci_hi<0"] == (ci[1] < 0) and abs(F.filled[dev].mean() - ad["fill_rate"]) < 1e-15,
   f"shortfall mean {sd.mean():.6f}, CI {ci}; fill rate {F.filled[dev].mean():.4f}; gate booleans re-derived")
proto = O_ / "N3_PROTOCOL_PREREGISTERED.md"
reg = [l.split(",") for l in (R_ / "logs" / "r2_4h_a0" / "trial_registry.csv").read_text().splitlines() if l.startswith("T17,")]
ok("X4", cl["protocol_sha"] == sha(proto) == (O_ / "N3_PROTOCOL_SHA256.txt").read_text().split()[0] and reg and reg[0][6] == sha(proto)
   and all(cl["files"][k] == sha(O_ / k) for k in cl["files"] if "stdout" not in k.lower()) and cl["code_sha"] == sha(R_ / "src" / "research" / "n3_execution.py"),
   "protocol lock, registry T17, file SHAs, code SHA")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
