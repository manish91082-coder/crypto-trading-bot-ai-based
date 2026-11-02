"""Audit (2026-10-16), REPORT ONLY: the F2/F7 scale gate used the full-period (2020-26) median perp/spot ratio, i.e. it
knew the future. Here the F7 RS run is repeated with a NO-look-ahead gate (the F4 forward rule): a coin is shortable on a
day only if the median perp/spot close ratio over the 7 days ending that day (>= 24 h) lies in [0.98, 1.02].
All coins with a perpetual are loaded, including the 3 the full-period gate excluded. Not a gate, no decision."""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import f7_run as R
import f7_risk as F
from config import LOGS_DIR

I = R.load("MAIN")
F2R = R.F2R
names = pd.read_csv(LOGS_DIR / "futures_um_download" / "perp_names.csv")
perp_h = {}
for r in names.itertuples():
    f = F2R.FUM / f"{r.symbol}_perp_1h.csv.gz"
    if not isinstance(r.perp, str) or not f.exists():
        continue
    d = pd.read_csv(f, parse_dates=["timestamp"]).set_index("timestamp")
    scale = 1e6 if r.perp.startswith("1000000") else 1e3 if r.perp.startswith("1000") and not r.symbol.startswith("1000") else 1.0
    for c in ("open", "high", "low", "close"):
        d[c] = d[c] / scale
    perp_h[r.symbol] = d
ok_day = {}
for s, d in perp_h.items():
    fp = F2R.S24.UNI1H / f"{s}_1h_full.csv.gz"
    if not fp.exists():
        continue
    sc = F2R.S24.bars_1h(fp).close.astype("float64")
    ratio = (d.close.reindex(sc.index) / sc).where(sc > 0)
    med = ratio.rolling("7D", min_periods=24).median()          # window ends at each hour (inclusive)
    day_end = med[med.index.hour == 23]
    day_end.index = day_end.index.normalize()
    ok_day[s] = ((day_end >= 0.98) & (day_end <= 1.02))
perp = {k: F2R.perp_arrays(perp_h, I["grids"][k], F2R.STEP[k]) for k in I["grids"]}
fund = F2R.funding_events(perp_h)
res = {}
for k in ("D1", "H4", "H1"):
    pa, gidx = perp[k], {t: i for i, t in enumerate(I["grids"][k])}

    def shortable(s, t, pa=pa, gidx=gidx):
        g = ok_day.get(s)
        return s in pa and np.isfinite(pa[s][2][gidx[t]]) and g is not None and bool(g.get(t.normalize(), False))
    res[k] = F.sim_ls(I["rows"]["AI"][k], I["grids"][k], I["decide"][k], I["spot"][k], pa, fund, R.F50, R.F50, R.N_HOLD, R.KEEP,
                      R.C_LONG, R.C_SHORT, shortable=shortable, **R.RS)
eqd = pd.DataFrame({k: F2R.daily_eq(v["eq"], k) for k, v in res.items()})
mix = eqd.mean(axis=1)
st = R.S27.stats(float(np.mean([v["final"] for v in res.values()])), mix, I["start"], I["end"])
C = json.loads((R.OUT / "claims.json").read_text())["MAIN"]["RS"]
out = dict(no_lookahead_gate=dict(mix=st, sleeves={k: round(v["final"], 2) for k, v in res.items()},
                                  liquidations=int(sum(v["liquidations"] for v in res.values())), stops=int(sum(v["stops"] for v in res.values()))),
           F7_RS_full_period_gate=dict(mix=C["mix"], sleeves={k: v["final"] for k, v in C["sleeves"].items()}))
(LOGS_DIR / "audit_full_16oct" / "scale_gate_lookahead.json").write_text(json.dumps(out, indent=2, default=str))
print(json.dumps(out, default=str))
