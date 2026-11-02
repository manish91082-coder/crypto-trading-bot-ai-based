"""POST-HOC (after R2 FAIL): decompose the 1D tracking gap. Same F4 build_lines for as-of 2026-09-30 with
(a) the deployed cost model, (b) perp taker 0.054% on both sides, (c) (b) + no stop slippage. Writes nothing in the project."""
import sys
from pathlib import Path
import pandas as pd
PROJ = Path(r"E:\crypto trading bot ai based 9 oct 2026")
for p in ("src", "src/pipeline_1d", "src/analytics", "src/execution", "src/research"):
    sys.path.insert(0, str(PROJ / p))
import forward_ls_f4 as F4
start, end = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-30")
I = F4.F7R.load("MAIN")
rows = {k: r[(r.t >= start) & (r.t <= end + pd.Timedelta(hours=23))].reset_index(drop=True) for k, r in I["rows"]["AI"].items()}
del I
dk, lk, dn, ln_, _ = F4.CR.load_folder(F4.F2R.S13.UNI / "1d", F4.F2R.S13.UNI / "1h", end)
data, last = {**dk, **dn}, {**lk, **ln_}
syms = sorted(set().union(*[set(r.symbol) for r in rows.values()]))
names = F4.perp_names(syms)
ph, fu = F4.arch(names)
spot1h = {s: F4.S24.bars_1h(F4.F2R.S24.UNI1H / f"{s}_1h_full.csv.gz").close.astype("float64") for s in syms
          if (F4.F2R.S24.UNI1H / f"{s}_1h_full.csv.gz").exists()}
gate = F4.gate_table(ph, spot1h, list(pd.date_range(start, end, freq="D")))
base_rs = dict(F4.LINES["LS_RS"][1])
for name, cl, cs, rs in (("a deployed", F4.F2R.C_LONG, F4.F2R.C_SHORT, base_rs),
                         ("b perp 0.054% both", 0.00054, 0.00054, base_rs),
                         ("c b + no stop slip", 0.00054, 0.00054, dict(base_rs, stop_slip=0.0))):
    F4.F2R.C_LONG, F4.F2R.C_SHORT = cl, cs
    F4.LINES = dict(LS_RS=(F4.F2R.F50, rs))
    lines, _ = F4.build_lines(start, end, rows, data, last, F4.F2R.S24.UNI1H, ph, fu, gate)
    e = lines["LS_RS"][["D1", "H4", "H1"]].iloc[-1].sum()
    print(f"{name}: 3-sleeve equity {e:.2f}, Sept return {e / 30000 - 1:.5f}", flush=True)
