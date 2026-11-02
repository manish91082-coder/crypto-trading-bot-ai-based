"""Fee amendment 2, test K3 (logs/fees/FEE_AMENDMENT_2_1D_RECORDERS_PREREGISTERED.md). In memory, nothing written.
On the real logged as-of: (a) old-fee 16B paper and F4 lines == the logged equity files (harness proof); (b) new-fee C1;
(c) old vs new equities. Usage: python k3_fee2_check.py 2026-10-24"""
import sys
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import forward_ls_f4 as Q                                       # noqa: E402  (sets the new F2R costs on import)
import forward_multi_16b as FB                                  # noqa: E402

asof = pd.Timestamp(sys.argv[1])
NEW = (Q.F2R.C_LONG, Q.F2R.C_SHORT, FB.COST)
rows, _ = Q.rows_16b(asof)
data_k, last_k, data_n, last_n, _ = Q.CR.load_folder(Q.FD.LIVE1D, Q.FD.LIVE1H, asof)
data, last = {**data_k, **data_n}, {**last_k, **last_n}
syms = sorted(set().union(*[set(r.symbol) for r in rows.values()]))
names = Q.perp_names(syms)
perp_h, fund = Q.load_perp_dir(Q.PERP_DIR, names)
spot1h = {s: Q.S24.bars_1h(Q.FD.LIVE1H / f"{s}_1h_full.csv.gz").close.astype("float64") for s in perp_h if (Q.FD.LIVE1H / f"{s}_1h_full.csv.gz").exists()}
gate = Q.gate_table(perp_h, spot1h, list(pd.date_range(Q.PAPER_START, asof, freq="D")))
sc = {k: FB.load_scores(k, asof, FB.PRED)[0] for k in ("d1", "h4_r6", "h1_r24")}


def run(c_long, c_short, cost16):
    Q.F2R.C_LONG, Q.F2R.C_SHORT, FB.COST = c_long, c_short, cost16
    lines, _ = Q.build_lines(Q.PAPER_START, asof, rows, data, last, Q.FD.LIVE1H, perp_h, fund, gate)
    p16, _ = FB.paper_from_rows(FB.PAPER_START, asof, sc["d1"], sc["h4_r6"], sc["h1_r24"], data, last, Q.FD.LIVE1H)
    return lines, p16.set_index("date")


old_l, old_p = run(0.0025, 0.0010, 0.0025)
logF = pd.read_csv(Q.LOG / "paper" / f"equity_{asof.date()}.csv", parse_dates=["date"]).set_index("date")
log16 = pd.read_csv(FB.PAPER / f"equity_{asof.date()}.csv", parse_dates=["date"]).set_index("date")
dF = max(abs(float(old_l[ln].loc[d, k]) - float(logF.loc[d, f"{ln}_{k}"])) for ln in old_l for d in logF.index for k in ("D1", "H4", "H1", "M_AI3"))
d16 = max(abs(float(old_p.loc[d, k]) - float(log16.loc[d, k])) for d in log16.index for k in ("D1", "H4", "H1", "M_AI3"))
print(f"[K3a {'PASS' if dF < 0.01 and d16 < 0.01 else 'FAIL'}] old fee reproduces the logged {asof.date()} files: F4 max diff {dF:.2e}, 16B max diff {d16:.2e}")
new_l, new_p = run(*NEW)
c1 = max(abs(float(new_l["LO"].loc[d, k]) - float(new_p.loc[d, k])) for d in new_p.index for k in ("D1", "H4", "H1"))
print(f"[K3b {'PASS' if c1 < 0.01 else 'FAIL'}] new fee C1 (F4 LO == 16B paper): max diff {c1:.2e}")
for ln in ("LS_RS", "LS_F2", "LO"):
    print(f"[K3c] {ln} M_AI3 {asof.date()}: old {float(old_l[ln].M_AI3.iloc[-1]):.2f}  new {float(new_l[ln].M_AI3.iloc[-1]):.2f}")
print(f"[K3c] 16B M_AI3 {asof.date()}: old {float(old_p.M_AI3.iloc[-1]):.2f}  new {float(new_p.M_AI3.iloc[-1]):.2f}; costs new {NEW}")
