"""
Independent verifier for logs/strategy_1d_step20_largecap_gate/claims.json.
V1 hashes as locked. V2 market label (equal-weight mean 5-day return of the Step 19 universe U coins > 0) re-derived
from RAW opens for every test day; both AUCs recomputed. V3 UNGATED, GATED, GATED_CONTROL re-simulated with separate
code from the saved gate predictions + base rates. V4 gates and decision recomputed.
"""
import sys, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "audits"):
    sys.path.insert(0, str(p))
import core_rows_1d as CR
import step13_unseen_coins_1d as S13
import verify_step19_claims as V19

D = S13.OUT.parent / "strategy_1d_step20_largecap_gate"
C = json.loads((D / "claims.json").read_text())
START, END = V19.START, V19.END


def auc(y, p):
    r = rankdata(p); n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / "STEP20_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    u19p = S13.OUT.parent / "strategy_1d_step19_largecap" / "U_AI_predictions.csv"
    assert hashlib.sha256(u19p.read_bytes()).hexdigest() == C["u19_pred_sha256"] and C["u19_pred_sha256"] in lock
    print("[V1 PASS] protocol and Step 19 input hashes as locked")
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", END)
    last = {**last_k, **last_n}
    U = pd.read_csv(S13.OUT.parent / "strategy_1d_step19_largecap" / "universe_U.csv", parse_dates=["date"])
    raw = {s: pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"]) for s in set(U.symbol) | {"BTCUSDT"}}
    f = []
    for s, d in zip(U.symbol, U.date):
        r = raw[s]
        i = int(np.searchsorted(r.timestamp.values, np.datetime64(d)))
        lo = int(np.searchsorted(r.timestamp.values, np.datetime64(min(last[s], END)), side="right")) - 1
        f.append(r.open.values[i + 6] / r.open.values[i + 1] - 1 if i + 6 <= lo else np.nan)
    U["f"] = f
    mean = U.dropna(subset=["f"]).groupby("date").f.mean()
    for lab in ("AI", "CONTROL"):
        M = pd.read_csv(D / f"market_{lab}_predictions.csv", parse_dates=["date"])
        y = (mean > 0).astype(float).where(mean.notna()).reindex(M.date.values).values
        same = (np.isnan(y) & M.m_label.isna().values) | (y == M.m_label.values)
        assert same.all(), (lab, int((~same).sum()))
        m = ~np.isnan(y)
        a = auc(y[m].astype(int), M.p_mkt.values[m])
        assert abs(a - C[f"{lab}_skill"]["auc"]) < 1e-9, (lab, a)
        assert all(abs(b - C[f"{lab}_base"][k]) < 1e-15 for k, b in zip(M.date.dt.strftime("%Y-%m"), M.base))
        print(f"[V2 PASS] {lab}: market labels re-derived from raw opens ({int(m.sum())} days), AUC {a:.4f}")
    opn = {s: raw[s].set_index("timestamp").open.to_dict() for s in raw}
    cls = {s: raw[s].set_index("timestamp").close.to_dict() for s in raw}
    for s in opn:
        if last[s] < END:
            c = cls[s][last[s]]
            for d in pd.date_range(last[s] + pd.Timedelta(days=1), END):
                opn[s][d], cls[s][d] = c, c
    P = pd.read_csv(u19p, usecols=["symbol", "date", "score"], parse_dates=["date"])
    res = {}
    for name, lab in (("UNGATED", None), ("GATED", "AI"), ("GATED_CONTROL", "CONTROL")):
        rows = P.copy()
        if lab:
            M = pd.read_csv(D / f"market_{lab}_predictions.csv", parse_dates=["date"])
            ok = dict(zip(M.date, M.p_mkt >= M.base))
            reb = [d for k, d in enumerate(pd.date_range(START, END)) if k % 5 == 0]
            closed = {d for d in reb if not ok.get(d, False)}
            rows = rows[~rows.date.isin(closed)]                     # no ranking on a closed day -> everything sold
        r = V19.sim(rows, 5, 10, opn, cls, last, 0.0025)
        c = C["portfolio"][name]
        assert abs(r["final"] - c["final"]) < 0.01 and abs(r["dd"] - c["max_dd_pct"]) < 0.01 and r["trades"] == c["trades"], (name, r["final"], c["final"])
        res[name] = r
        print(f"[V3 PASS] {name}: final {r['final']:.2f}, MaxDD {r['dd']:.2f}%, trades {r['trades']}, positive years {r['years_pos']}")
    pf = C["portfolio"]; g = pf["GATED"]
    rec = dict(G1=C["sanity_planted"]["auc"] >= 0.55 and C["sanity_leak"]["auc"] > 0.95,
               G2_skill=C["AI_skill"]["ci_low"] > 0.5 and C["AI_skill"]["auc"] > C["CONTROL_skill"]["auc"],
               G3a_cagr=g["cagr_pct"] > 0, G3b_calmar=all(g["calmar"] > pf[k]["calmar"] for k in ("UNGATED", "GATED_CONTROL", "BTC_HOLD")),
               G3c_trade_ci=g["trade_ci_low_pct"] > 0, G3d_years=res["GATED"]["years_pos"] >= 4,
               G3e_cost040=pf["GATED_cost040"]["cagr_pct"] > 0, G3f_maxdd=res["GATED"]["dd"] < 50)
    gt = C["gates"]
    assert all(bool(rec[k]) == gt[k] for k in rec), {k: (rec[k], gt[k]) for k in rec}
    g3 = all(v for k, v in rec.items() if k.startswith("G3"))
    want = "INVALID" if not rec["G1"] else "PASS" if g3 and rec["G2_skill"] else "SYSTEM_PASSES_BUT_BRAIN_UNPROVEN" if g3 else "FAIL"
    assert gt["decision"] == want
    print(f"[V4 PASS] gates recomputed -> {gt['decision']}")


if __name__ == "__main__":
    main()
