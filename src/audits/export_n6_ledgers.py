"""Exports the N6 ledgers the verifier needs, regenerated with the SAME locked n6 code (code SHA checked against claims_n6):
n6_S1_trades.parquet (A/B/C trades with the 35% stop) and n6_S2_dev_weights.parquet (dev ledger with the S2 cap weights)."""
import hashlib, json, sys
from pathlib import Path
R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "research"))
cl = json.loads((R_ / "logs" / "research_n6_safety_sizing" / "claims_n6.json").read_text())
assert cl["code_sha"] == hashlib.sha256((R_ / "src" / "research" / "n6_safety_sizing.py").read_bytes()).hexdigest()
import n6_safety_sizing as S
N = S.N
Wd = N.load_world()
Wd.led_nostop = {s: N.sim(Wd.T[s], Wd.C, stop=False) for s in "ABC"}
Wd.D, Wd.Dcost, _ = N.build_D(Wd.dc, Wd.C)
import pandas as pd
S1 = pd.concat([S.sim_pct(Wd.T[s], Wd.C) for s in "ABC"], ignore_index=True)
S1.to_parquet(N.DER / "n6_S1_trades.parquet", index=False)
S.HOOK["C"] = Wd.C
L0 = N.assemble(Wd, {"stop": False}, Wd.led_nostop, Wd.D, *N.WIN["dev"])
S.HOOK["cap"] = True
L1 = N.assemble(Wd, {"stop": False}, Wd.led_nostop, Wd.D, *N.WIN["dev"])
L1["w_base"] = L0.w.values
L1.to_parquet(N.DER / "n6_S2_dev_weights.parquet", index=False)
print("exported", len(S1), len(L1), "capped", int((L1.w < L1.w_base - 1e-15).sum()), "skipped", int(((L1.w == 0) & (L1.w_base > 0)).sum()))
