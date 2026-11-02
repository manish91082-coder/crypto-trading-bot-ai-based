"""Evidence: the forward logger's R5 (fit_r5 + core_rows_1d, data cut at as-of) reproduces Step 15's research R5
predictions. Usage: python replay_r5_vs_step15.py 2026-09-15"""
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
import forward_dryrun_1d as FW

asof = pd.Timestamp(sys.argv[1])
d1, h1 = S13.UNI / "1d", S13.UNI / "1h"
data_k, last_k, data_n, last_n, _ = CR.load_folder(d1, h1, asof)
Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, h1, h1, asof, S11.fng_table())
Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= 120)
m5, ntr = FW.fit_r5(Pk, Pn, data_k, last_k, data_n, last_n, F, asof.replace(day=1), asof)
today = Pn[(Pn.date == asof) & Pn.eligible].copy()
today["p_replay"] = m5.predict_proba(today[F].values)[:, 1]
ref = pd.read_csv(S13.OUT.parent / "strategy_1d_step15_slow" / "R5_AI_test_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
ref = ref[ref.date == asof]
j = ref.merge(today[["symbol", "p_replay"]], on="symbol", how="left")
diff = np.abs(j.score - j.p_replay)
print(f"as-of {asof.date()}: train rows {ntr}; research B coins {len(ref)}, found in replay {int(j.p_replay.notna().sum())}; max |diff| {diff.max():.3e}")
assert j.p_replay.notna().all() and diff.max() < 1e-9, "R5 replay does NOT reproduce Step 15"
print("[REPLAY R5 PASS] forward logger R5 reproduces Step 15 research predictions exactly")
