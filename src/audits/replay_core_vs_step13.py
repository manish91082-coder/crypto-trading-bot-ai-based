"""
Evidence that the shared builder (core_rows_1d) + the live way of working (data cut at the as-of date, model of the
month) reproduce Step 13's research predictions. Usage: python replay_core_vs_step13.py 2026-09-15
Uses data/universe_all for ALL coins (as the forward dry-run does). Writes logs/strategy_1d_step16_forward/replay_<date>.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics"):
    sys.path.insert(0, str(p))
import core_rows_1d as CR
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13


def main(asof):
    asof = pd.Timestamp(asof)
    d1, h1 = S13.UNI / "1d", S13.UNI / "1h"
    data_k, last_k, data_n, last_n, _ = CR.load_folder(d1, h1, asof)
    Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, h1, h1, asof, S11.fng_table())
    m, ntr = CR.fit_b1(Pk, F, asof.replace(day=1))
    today = Pn[(Pn.date == asof) & Pn.liquid].copy()
    today["p1_replay"] = m.predict_proba(today[F].values)[:, 1]
    ref = pd.read_csv(S13.OUT / "AI_signals_unseen.csv", usecols=["symbol", "date", "p1"], parse_dates=["date"])
    ref = ref[ref.date == asof]
    j = ref.merge(today[["symbol", "p1_replay"]], on="symbol", how="outer", indicator=True)
    out = S13.OUT.parent / "strategy_1d_step16_forward"
    out.mkdir(parents=True, exist_ok=True)
    j.to_csv(out / f"replay_{asof.date()}.csv", index=False)
    both = j[j._merge == "both"]
    diff = np.abs(both.p1 - both.p1_replay)
    print(f"as-of {asof.date()}: train rows {ntr}; Step13 coins {len(ref)}, replay coins {len(today)}, "
          f"only-Step13 {int((j._merge == 'left_only').sum())}, only-replay {int((j._merge == 'right_only').sum())}; "
          f"max |p1 diff| {diff.max():.3e}, mean {diff.mean():.3e}")
    assert (j._merge == "both").all() and diff.max() < 1e-9, "replay does NOT reproduce Step 13"
    print("[REPLAY PASS] live-style pipeline reproduces Step 13 predictions exactly")


if __name__ == "__main__":
    main(sys.argv[1])
