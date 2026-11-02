"""Builds deploy/paper_n1_config.json from the verified research outputs (no hand-typed numbers).
core10 / u2x = the N1 universes; perp names = the F1 list; k_hold = median hold hours of all A/B trades per TF (N3_fills);
safety = the T19 choice in logs/research_n6_safety_sizing/claims_n6.json."""
import json, sys
from pathlib import Path
import pandas as pd
R_ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R_ / "src" / "research"))
import r2_t14_universe as U
import tf_edge_map as M
u2x = [c for c in U.candidates() if (M.HF / f"{c}_5m_full.csv.gz").exists() and c not in ("LUNAUSDT", "STRAXUSDT")]
pn = pd.read_csv(R_ / "logs" / "futures_um_download" / "perp_names.csv").set_index("symbol").perp.to_dict()
F = pd.read_parquet(R_ / "logs" / "research_n3_execution" / "N3_fills.parquet")
kh = {f"{s}|{tf}": float(g.hold_h.median()) for (s, tf), g in F[F.sleeve.isin(["A", "B"])].groupby(["sleeve", "tf"])}
n6 = json.loads((R_ / "logs" / "research_n6_safety_sizing" / "claims_n6.json").read_text())
ch = n6["t19"]["choice"]
safety = {"stop_pct": 0.35 if ch in ("S1", "S3") else None, "coin_cap": 0.20 if ch in ("S2", "S3") else None, "t19_choice": ch}
cfg = dict(core10=M.CORE10, u2x=u2x, perp_names={c: pn.get(c, c) for c in sorted(set(u2x) | set(M.CORE10))}, k_hold_hours=kh, safety=safety,
           ai_sizing=False, source=dict(n1_claims="logs/research_n1_portfolio/claims_n1.json", n3_claims="logs/research_n3_execution/claims_n3.json",
                                        n6_claims="logs/research_n6_safety_sizing/claims_n6.json"))
(R_ / "deploy" / "paper_n1_config.json").write_text(json.dumps(cfg, indent=1))
print(len(u2x), kh, safety)
