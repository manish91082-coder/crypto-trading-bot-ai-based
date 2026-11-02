"""Builds deploy/eco_config.json and deploy/eco_history_daily_returns.csv from the verified E-2 claims (logs/eco/claims_eco_e2.json).
The history holds exactly the E-2 inputs (1D: F7 RS M_AI3 daily returns; N1: N1 FINAL dev + P3 runs, returns per run)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "src" / "eco"))
import eco_core as C

cl = json.loads((P / "logs" / "eco" / "claims_eco_e2.json").read_text())
assert cl["e1_pass"] and cl["choice"] == "ECO-W2", cl["verdict"]
rs = pd.read_csv(P / "logs" / "strategy_f7_risk" / "equity_MAIN_AI_RS.csv", parse_dates=["date"]).set_index("date").M_AI3
r1 = (rs / rs.shift(1) - 1).dropna()
parts = []
for k in ("dev", "P3"):
    c = pd.read_parquet(P / "data" / "derived" / "eco" / f"n1_final_hourly_{k}.parquet").equity
    d = c.groupby(c.index.normalize()).last()
    parts.append(d / np.r_[C.E0, d.values[:-1]] - 1)
rn = pd.concat(parts).sort_index()
H = pd.DataFrame(dict(r_1D=r1, r_N1=rn)).rename_axis("date")
hf = P / "deploy" / "eco_history_daily_returns.csv"
H.to_csv(hf, float_format="%.17g")
Hr = pd.read_csv(hf, parse_dates=["date"]).set_index("date")
# check: the frozen file gives the E-2 weights (P3 window months) to 1e-12
w2 = pd.read_csv(P / "logs" / "eco" / "E2_weights_W2.csv")
md = max(abs(C.inv_vol_weight(Hr.r_1D.dropna(), Hr.r_N1.dropna(), pd.Timestamp(r.month + "-01")) - r.a_1D)
         for r in w2[w2.window == "P3"].itertuples())
assert md < 1e-12, md
a_oct = C.inv_vol_weight(Hr.r_1D.dropna(), Hr.r_N1.dropna(), pd.Timestamp("2026-10-01"))
n1cfg = json.loads((P / "deploy" / "paper_n1_config.json").read_text())
cfg = dict(capital=10_000.0, protocol_sha256=cl["protocol_sha"], e2_claims_sha256=hashlib.sha256((P / "logs" / "eco" / "claims_eco_e2.json").read_bytes()).hexdigest(),
           weights=dict(mode="inverse_vol", lookback=126, clip=[0.2, 0.8], history="deploy/eco_history_daily_returns.csv",
                        history_sha256=hashlib.sha256(hf.read_bytes()).hexdigest(), a_1D_2026_10_info=a_oct),
           coin_cap=0.20, gross_cap=1.50, band_frac=0.0025, fee=json.loads((P / "deploy" / "fees.json").read_text())["rules"]["eco_fee_per_side"],  # fee amendment 2d9d1485 (was 0.00054)
           max_orders=40, kill_K=cl["kill_K"],
           n1_root="data/paper_n1", n1_perp_names=n1cfg["perp_names"], demo_enabled="--demo" in sys.argv,   # --demo: cut-over (E-6), 2026-10-25
           # amendment 1 (0a448a79): outage guard D from logs/eco/A1_outage_guard.json; profit lock only if ECO-T4 was adopted
           amendment_1_sha256=hashlib.sha256((P / "logs" / "eco" / "ECO_AMENDMENT_1_PREREGISTERED.md").read_bytes()).hexdigest(),
           guard_on=True, guard_D=json.loads((P / "logs" / "eco" / "A1_outage_guard.json").read_text())["chosen_D"],
           profit_lock=json.loads((P / "logs" / "eco" / "claims_eco_t4.json").read_text())["verdict"] == "ECO-T4 ADOPTED")
(P / "deploy" / "eco_config.json").write_text(json.dumps(cfg, indent=1))
print("history rows", len(H), "E-2 P3 weights reproduced, max diff", md, "| a_1D for 2026-10:", round(a_oct, 4), "| kill K", cl["kill_K"])
