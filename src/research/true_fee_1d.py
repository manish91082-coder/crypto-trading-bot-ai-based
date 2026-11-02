"""1D (F7 RS) re-run with the true Binance fee (logs/research_1d_true_fee/TRUE_FEE_1D_PROTOCOL_PREREGISTERED.md).
Imports the F7 engine unchanged; output folder redirected so the locked F7 files are never written.
Run: python src/research/true_fee_1d.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ / "src" / "pipeline_1d"))
sys.path.insert(0, str(PROJ / "src"))
import f7_run as F7                                            # noqa: E402

OUT = PROJ / "logs" / "research_1d_true_fee"
FEES = json.loads((PROJ / "deploy" / "fees.json").read_text())["rules"]
C_LONG_TRUE, C_SHORT_TRUE = FEES["paper_spot_per_side"], FEES["paper_futures_taker_per_side"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


assert sha(OUT / "TRUE_FEE_1D_PROTOCOL_PREREGISTERED.md") == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"


def stats(e):
    e = e.dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    base = 10_000.0
    out = dict(final=float(e.iloc[-1]), cagr=float((e.iloc[-1] / base) ** (1 / yrs) - 1), maxdd=float((e / e.cummax() - 1).min()))
    out["calmar"] = out["cagr"] / abs(out["maxdd"]) if out["maxdd"] < 0 else None
    ye = e.groupby(e.index.year).last()
    prev = pd.concat([pd.Series([base], index=[ye.index[0] - 1]), ye])
    out["years"] = {str(y): float(v) for y, v in (prev / prev.shift(1) - 1).dropna().items()}
    p3 = e[e.index >= "2025-09-30"]
    out["p3_2025_10_on"] = float(p3.iloc[-1] / p3.iloc[0] - 1)
    p3d = p3 / p3.cummax() - 1
    out["p3_maxdd"] = float(p3d.min())
    return out


def main():
    F7.OUT = OUT                                                # redirect every write of run()
    I = F7.load("MAIN")
    res = dict(protocol_sha256=sha(OUT / "TRUE_FEE_1D_PROTOCOL_PREREGISTERED.md"), engine_sha256=dict(f7_run=sha(PROJ / "src/pipeline_1d/f7_run.py"),
               f7_risk=sha(PROJ / "src/pipeline_1d/f7_risk.py")), costs=dict(R0=[F7.C_LONG, F7.C_SHORT], R1=[C_LONG_TRUE, C_SHORT_TRUE]))
    assert (F7.C_LONG, F7.C_SHORT) == (0.0025, 0.0010)
    F7.run(I, "MAIN", "AI", "R0_RS", F7.F50, F7.C_SHORT, F7.RS)
    ref = pd.read_csv(PROJ / "logs" / "strategy_f7_risk" / "equity_MAIN_AI_RS.csv", parse_dates=["date"]).set_index("date")
    r0 = pd.read_csv(OUT / "equity_MAIN_AI_R0_RS.csv", parse_dates=["date"]).set_index("date")
    dmax = float((r0[ref.columns] - ref).abs().max().max())
    res["R0_reproduction_max_abs_diff"] = dmax
    assert r0.shape == ref.shape and dmax < 1e-6, f"R0 does not reproduce the locked F7 equity (max diff {dmax}) -> INVALID"
    F7.run(I, "MAIN", "AI", "R0_LO", 0.0, F7.C_SHORT, {})
    F7.C_LONG = C_LONG_TRUE                                      # run() reads the module constant for the long side
    F7.run(I, "MAIN", "AI", "R1_RS", F7.F50, C_SHORT_TRUE, F7.RS)
    F7.run(I, "MAIN", "AI", "R1_LO", 0.0, C_SHORT_TRUE, {})
    for nm in ("R0_RS", "R1_RS", "R0_LO", "R1_LO"):
        e = pd.read_csv(OUT / f"equity_MAIN_AI_{nm}.csv", parse_dates=["date"]).set_index("date")
        res[nm] = {c: stats(e[c]) for c in ("M_AI3", "D1", "H4", "H1")}
        res[nm]["file_sha256"] = sha(OUT / f"equity_MAIN_AI_{nm}.csv")
    res["cost_effect_final_mix"] = dict(RS=res["R1_RS"]["M_AI3"]["final"] - res["R0_RS"]["M_AI3"]["final"],
                                        LO=res["R1_LO"]["M_AI3"]["final"] - res["R0_LO"]["M_AI3"]["final"])
    f = OUT / "TRUE_FEE_1D_RESULTS.json"
    f.write_text(json.dumps(res, indent=1), encoding="utf-8")
    (OUT / "RESULTS_SHA256.txt").write_text(sha(f) + "  TRUE_FEE_1D_RESULTS.json\n")
    for nm in ("R0_RS", "R1_RS", "R0_LO", "R1_LO"):
        m = res[nm]["M_AI3"]
        print(nm, "final", round(m["final"]), "cagr", round(m["cagr"], 4), "maxdd", round(m["maxdd"], 4), "calmar", round(m["calmar"] or 0, 3),
              "P3", round(m["p3_2025_10_on"], 4), "P3dd", round(m["p3_maxdd"], 4), "years", {k: round(v, 3) for k, v in m["years"].items()})
    print("R0 reproduction max diff", dmax)


if __name__ == "__main__":
    main()
