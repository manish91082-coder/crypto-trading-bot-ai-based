"""
Independent verifier for logs/strategy_1d_step21_crash/claims.json.
V1 hashes. V2 crash10 label re-derived from RAW opens (U mean 10-day return < -10 %), AUCs recomputed.
V3 causal 80th-percentile alarm thresholds recomputed from earlier months only. V4 UNGATED, ALARM, ALARM_CONTROL
re-simulated with separate code. V5 gates/decision recomputed.
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
D = S13.OUT.parent / "strategy_1d_step21_crash"
C = json.loads((D / "claims.json").read_text())
START, END = V19.START, V19.END


def auc(y, p):
    r = rankdata(p); n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
assert hashlib.sha256((D / "STEP21_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
u19p = S13.OUT.parent / "strategy_1d_step19_largecap" / "U_AI_predictions.csv"
assert hashlib.sha256(u19p.read_bytes()).hexdigest() == C["u19_pred_sha256"] and C["u19_pred_sha256"] in lock
print("[V1 PASS] hashes as locked")
_, lk, _, ln, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", END)
last = {**lk, **ln}
U = pd.read_csv(S13.OUT.parent / "strategy_1d_step19_largecap" / "universe_U.csv", parse_dates=["date"])
raw = {s: pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"]) for s in set(U.symbol) | {"BTCUSDT"}}
f = []
for s, d in zip(U.symbol, U.date):
    r = raw[s]
    i = int(np.searchsorted(r.timestamp.values, np.datetime64(d)))
    lo = int(np.searchsorted(r.timestamp.values, np.datetime64(min(last[s], END)), side="right")) - 1
    f.append(r.open.values[i + 11] / r.open.values[i + 1] - 1 if i + 11 <= lo else np.nan)
U["f"] = f
mean = U.dropna(subset=["f"]).groupby("date").f.mean()
for lab in ("AI", "CONTROL"):
    M = pd.read_csv(D / f"crash_{lab}_predictions.csv", parse_dates=["date"])
    y = (mean < -0.10).astype(float).where(mean.notna()).reindex(M.date.values).values
    same = (np.isnan(y) & M.crash.isna().values) | (y == M.crash.values)
    assert same.all(), (lab, int((~same).sum()))
    m = ~np.isnan(y)
    a = auc(y[m].astype(int), M.p_crash.values[m])
    assert abs(a - C[f"{lab}_skill99"]["auc"]) < 1e-9, (lab, a)
    mon = M.date.dt.to_period("M")
    for mth in mon.unique():
        past = M.p_crash[mon < mth]
        want = past.quantile(0.8) if len(past) else np.nan
        got = M.thr[mon == mth].iloc[0]
        assert (np.isnan(want) and np.isnan(got)) or abs(want - got) < 1e-12
    print(f"[V2+V3 PASS] {lab}: crash labels re-derived ({int(m.sum())} days), AUC {a:.4f}; thresholds causal")
opn = {s: raw[s].set_index("timestamp").open.to_dict() for s in raw}
cls = {s: raw[s].set_index("timestamp").close.to_dict() for s in raw}
for s in opn:
    if last[s] < END:
        c = cls[s][last[s]]
        for d in pd.date_range(last[s] + pd.Timedelta(days=1), END):
            opn[s][d], cls[s][d] = c, c
P = pd.read_csv(u19p, usecols=["symbol", "date", "score"], parse_dates=["date"])
res = {}
for name, lab in (("UNGATED", None), ("ALARM", "AI"), ("ALARM_CONTROL", "CONTROL")):
    rows = P
    if lab:
        M = pd.read_csv(D / f"crash_{lab}_predictions.csv", parse_dates=["date"])
        alarm = set(M.date[M.p_crash >= M.thr])
        rows = P[~P.date.isin(alarm)]
    r = V19.sim(rows, 5, 10, opn, cls, last, 0.0025)
    c = C["portfolio"][name]
    assert abs(r["final"] - c["final"]) < 0.01 and abs(r["dd"] - c["max_dd_pct"]) < 0.01 and r["trades"] == c["trades"], (name, r["final"], c["final"])
    res[name] = r
    print(f"[V4 PASS] {name}: final {r['final']:.2f}, MaxDD {r['dd']:.2f}%, trades {r['trades']}, positive years {r['years_pos']}")
pf = C["portfolio"]; g = pf["ALARM"]
rec = dict(G1=C["sanity_planted"]["auc"] >= 0.55 and C["sanity_leak"]["auc"] > 0.95,
           G2_skill=C["AI_skill99"]["ci_low"] > 0.5 and C["AI_skill99"]["auc"] > C["CONTROL_skill99"]["auc"],
           G3a_cagr=g["cagr_pct"] > 0, G3b_calmar=all(g["calmar"] > pf[k]["calmar"] for k in ("UNGATED", "ALARM_CONTROL", "BTC_HOLD")),
           G3c_trade_ci=g["trade_ci_low_pct"] > 0, G3d_years=res["ALARM"]["years_pos"] >= 4,
           G3e_cost040=pf["ALARM_cost040"]["cagr_pct"] > 0, G3f_maxdd=res["ALARM"]["dd"] < 50)
gt = C["gates"]
assert all(bool(rec[k]) == gt[k] for k in rec), {k: (rec[k], gt[k]) for k in rec}
g3 = all(v for k, v in rec.items() if k.startswith("G3"))
assert gt["decision"] == ("INVALID" if not rec["G1"] else "PASS" if g3 and rec["G2_skill"] else "SYSTEM_PASSES_BUT_BRAIN_UNPROVEN" if g3 else "FAIL")
print(f"[V5 PASS] gates recomputed -> {gt['decision']}")
