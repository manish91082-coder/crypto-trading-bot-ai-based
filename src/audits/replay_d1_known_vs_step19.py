"""Audit (2026-10-15): the Step 19 production D1 scores of the 30 KNOWN coins are reproduced by the forward way of
working (data cut at the as-of day, month model trained from scratch, fit_r5 + core_rows_1d).
Complements replay_r5_vs_step15.py, which covers the unseen (B) coins. Usage: python replay_d1_known_vs_step19.py 2022-06-15"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution"):
    sys.path.insert(0, str(p))
import core_rows_1d as CR
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
import step19_large_caps_1d as S19
import forward_dryrun_1d as FW

asof = pd.Timestamp(sys.argv[1])
d1, h1 = S13.UNI / "1d", S13.UNI / "1h"
data_k, last_k, data_n, last_n, _ = CR.load_folder(d1, h1, asof)
Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, h1, h1, asof, S11.fng_table())
Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= 120)
m5, ntr = FW.fit_r5(Pk, Pn, data_k, last_k, data_n, last_n, F, asof.replace(day=1), asof)
today = Pk[Pk.date == asof].copy()
today["p_replay"] = m5.predict_proba(today[F].values)[:, 1]
ref = pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
ref = ref[(ref.date == asof) & ref.symbol.isin(set(data_k))]
j = ref.merge(today[["symbol", "p_replay"]], on="symbol", how="left")
diff = np.abs(j.score - j.p_replay)
print(f"as-of {asof.date()}: train rows {ntr}; Step 19 known-coin rows {len(ref)}, found {int(j.p_replay.notna().sum())}; max |diff| {diff.max():.3e}")
assert len(ref) > 0 and j.p_replay.notna().all() and diff.max() < 1e-9, "known-coin D1 scores NOT reproduced"
print("[REPLAY D1-KNOWN PASS] Step 19 known-coin scores reproduced with data cut at the as-of day and a month model from scratch")
