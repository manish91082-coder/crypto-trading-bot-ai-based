"""DDX post-run investigation of the Part A final-equity mismatches (CODE_NOTES 6). The mismatch rows have
claimed final < last value of the equity file, while every drawdown matches. Hypothesis: the claimed final is the
cash after the end-of-test close-out (fee on the sale), and the equity file is mark-to-market before that sale.
Exact test where the trades file exists: claimed final == 10,000 + sum(pnl) (mix = mean of the D1/H4/H1 sleeves).
Step 19-type engines: MTM - sum(end-of-test exit value) x 0.25% == claimed final.
Run: python src/research/drawdown_ddx_final_gap.py"""
import hashlib, json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "drawdown_ddx"
CAP, C19 = 10_000.0, 0.0025


def main():
    T = pd.read_csv(OUT / "ledger.csv")
    bad = T[T.final_ok.astype(str) == "False"]
    rows = []
    for _, r in bad.iterrows():
        rec = dict(id=r.id, item=r["item"], claimed_final=r.claimed_final, mtm_last=r.recomputed_final,
                   gap=r.recomputed_final - r.claimed_final, gap_pct_of_mtm=(r.recomputed_final - r.claimed_final) / r.recomputed_final * 100,
                   test="", explained_final=np.nan, explained=False)
        f = Path(r.equity_file)
        d = ROOT / f.parent
        if r.id in ("A01", "A02", "A03", "A04"):                  # Step 15/19 rebalance engine: one trades file per run
            name = f.name.replace("_equity.csv", "")
            if name == "BTC_HOLD":                           # step19 btc_hold(): cash = CAP - 0.8 CAP (1 + c), fee on units x close
                cash = CAP - 0.80 * CAP * (1 + C19)
                fee = (r.recomputed_final - cash) * C19
                rec.update(test="btc_hold(): (MTM - cash) x 0.25%", explained_final=r.recomputed_final - fee,
                           explained=abs(r.recomputed_final - fee - r.claimed_final) <= 0.01)
                rows.append(rec)
                continue
            t = pd.read_csv(d / f"{name}_trades.csv")
            end = t[t.reason.isin(["end_of_test", "hold"])]
            fee = float((end.cost / (1 + C19) / end.entry * end.exit).sum() * C19)
            rec.update(test="MTM - end-of-test exit value x 0.25%", explained_final=r.recomputed_final - fee,
                       explained=abs(r.recomputed_final - fee - r.claimed_final) <= 0.01)
            rec["pnl_sum_final"] = CAP + float(t.pnl.sum())
        elif r.id == "A05":
            t = pd.read_csv(d / "MAIN_2021_26_AI_VETO_trades.csv")
            v = CAP + float(t.pnl.sum())
            rec.update(test="10,000 + sum(pnl)", explained_final=v, explained=abs(v - r.claimed_final) <= 0.01)
        elif r.id in ("A08", "A09", "A10", "A11"):
            tag = {"A08": None, "A09": None}.get(r.id)
            if "equity_MAIN_AI_LS" in f.name or "equity_MAIN_AI_LO" in f.name or "equity_MAIN_AI_OFF_LS" in f.name:
                if "_LO" in f.name:                          # no long-only trade files were saved
                    rec["test"] = "no trades file (LO)"
                    rows.append(rec)
                    continue
                src = ROOT / "logs/strategy_f2_longshort"
                parts = [pd.read_csv(src / f"trades_MAIN_{s}_AI_LS.csv") for s in ("D1", "H4", "H1")]
            elif "equity_MAIN_AI_RS" in f.name or "BASE_F7_RS" in f.name:
                src = ROOT / "logs/strategy_f7_risk"
                parts = [pd.read_csv(src / f"trades_MAIN_{s}_AI_RS.csv") for s in ("D1", "H4", "H1")]
            else:                                            # R1 runs: one trades file with a sleeve column
                name = f.name.replace("equity_", "").replace(".csv", "")
                t = pd.read_csv(d / f"trades_{name}.csv")
                parts = [t[t.sleeve == s] for s in ("D1", "H4", "H1")]
            v = float(np.mean([CAP + p.pnl.sum() for p in parts]))
            rec.update(test="mean over sleeves of 10,000 + sum(pnl)", explained_final=v,
                       explained=abs(v - r.claimed_final) <= 0.01)
        elif r.id == "A06":
            rec["test"] = "no trades file; bound only: gap <= 0.25% x MTM"
            rec["explained"] = "bound only" if 0 < rec["gap_pct_of_mtm"] <= 0.25 else False
        rows.append(rec)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "final_gap_investigation.csv", index=False)
    print(R.to_string())
    (OUT / "final_gap_investigation_SHA256.txt").write_text(
        f"{hashlib.sha256((OUT / 'final_gap_investigation.csv').read_bytes()).hexdigest()}  final_gap_investigation.csv\n"
        f"{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}  src/research/drawdown_ddx_final_gap.py\n")


if __name__ == "__main__":
    main()
