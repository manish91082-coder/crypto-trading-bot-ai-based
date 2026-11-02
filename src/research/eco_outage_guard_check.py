"""ECO amendment 1 §2: share of 1h perp bars (data/futures_um, all coins, 2020 .. 2026-09) with high >= (1+D) x previous close
or low <= (1-D) x previous close. D = 0.50 if share <= 1e-4, else D = 0.60. Writes logs/eco/A1_outage_guard.json."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
A1 = P / "logs" / "eco" / "ECO_AMENDMENT_1_PREREGISTERED.md"
assert hashlib.sha256(A1.read_bytes()).hexdigest() == (P / "logs" / "eco" / "ECO_AMENDMENT_1_SHA256.txt").read_text().split()[0]
files = sorted((P / "data" / "futures_um").glob("*_perp_1h.csv.gz"))
tot, cnt, ev = 0, {0.5: 0, 0.6: 0}, []
for f in files:
    d = pd.read_csv(f, usecols=["timestamp", "high", "low", "close"]).sort_values("timestamp")
    pc = d.close.shift(1).values
    ok = np.isfinite(pc) & (pc > 0)
    tot += int(ok.sum())
    for D in cnt:
        m = ok & ((d.high.values >= (1 + D) * pc) | (d.low.values <= (1 - D) * pc))
        cnt[D] += int(m.sum())
        if D == 0.5 and m.any():
            for i in np.flatnonzero(m):
                ev.append((f.name.split("_")[0], str(d.timestamp.iloc[i]), round(float(d.high.iloc[i] / pc[i] - 1), 3), round(float(d.low.iloc[i] / pc[i] - 1), 3)))
share = {str(D): c / tot for D, c in cnt.items()}
D = 0.5 if share["0.5"] <= 1e-4 else 0.6
out = dict(coins=len(files), coin_hours=tot, count=cnt, share=share, chosen_D=D, events_D050=ev,
           files_sha=hashlib.sha256("".join(hashlib.sha256(f.read_bytes()).hexdigest() for f in files).encode()).hexdigest(),
           amendment_sha=hashlib.sha256(A1.read_bytes()).hexdigest())
(P / "logs" / "eco" / "A1_outage_guard.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps({k: v for k, v in out.items() if k != "events_D050"}, default=str), "events", ev[:20])
