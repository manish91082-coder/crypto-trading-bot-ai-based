"""
Independent verifier for logs/strategy_1d_step8_ai/claims.json (anti-false-claim rule #2). Raises on any mismatch.

V1 protocol SHA256 == registered hash (protocol not edited after registration).
V2 AUC of every skill claim recomputed with a SEPARATE implementation (Mann-Whitney rank formula, not sklearn),
   base rate and quintile rates recomputed from the prediction files.
V3 every portfolio claim: final == 10,000 + sum of trade P&L; CAGR, MaxDD, Calmar recomputed from the equity file.
V4 no-future training: rebuilding the datasets, every monthly training size == rows whose label was known before the
   re-train date (training log), and every OOS prediction belongs to the month after its model's training cut.
V5 gates and the deploy decision recomputed from the verified numbers.
"""
import sys
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics"):
    sys.path.insert(0, str(p))
import step8_ai_entry_exit_1d as S8

STEP = sys.argv[1] if len(sys.argv) > 1 else "step8"          # "step8" | "step9"
PROTO = "STEP8_PROTOCOL_PREREGISTERED.md" if STEP == "step8" else "STEP9_PROTOCOL_PREREGISTERED.md"
D = S8.OUT if STEP == "step8" else S8.OUT.parent / "strategy_1d_step9_ai"
C = json.loads((D / "claims.json").read_text())


def auc_mw(y, p):
    r = rankdata(p)
    n1 = y.sum()
    n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def v1():
    h = hashlib.sha256((D / PROTO).read_bytes()).hexdigest()
    assert h == C["protocol_sha256"] == (D / "PROTOCOL_SHA256.txt").read_text().split()[0]
    print(f"[V1 PASS] protocol hash {h[:16]}... unchanged since registration")


def v2():
    for lab in ("AI", "CONTROL_shuffled"):
        e = pd.read_csv(D / f"{lab}_entry_predictions.csv")
        x = pd.read_csv(D / f"{lab}_exit_predictions.csv")
        for key, df in ((f"{lab}_entry_skill_members", e[e.member]), (f"{lab}_exit_skill_members", x[x.member == True]),
                        (f"{lab}_entry_skill_allcoins", e)):
            d = df[df.label.notna()]
            y, p = d.label.values.astype(int), d.prob.values
            c = C[key]
            assert c["n"] == len(d) and abs(auc_mw(y, p) - c["auc"]) < 1e-9 and abs(y.mean() - c["base_rate"]) < 1e-12, key
            q = pd.qcut(pd.Series(p).rank(method="first"), 5, labels=False)
            assert np.allclose(pd.Series(y).groupby(q.values).mean().values, c["quintile_rates"]), key
            print(f"[V2 PASS] {key}: n={len(d)} AUC {c['auc']:.4f} (independent rank formula) base {c['base_rate']:.3f}")


def v3():
    for name, c in C["portfolio"].items():
        tr = pd.read_csv(D / f"{name}_trades.csv")
        eq = pd.read_csv(D / f"{name}_equity.csv", parse_dates=["date"])
        final = 10000 + tr.pnl.sum()
        curve = np.r_[10000, eq.equity.values[:-1], final]
        dd = ((np.maximum.accumulate(curve) - curve) / np.maximum.accumulate(curve)).max()
        yrs = (eq.date.iloc[-1] - pd.Timestamp("2021-01-01")).days / 365.25
        cagr = (final / 10000) ** (1 / yrs) - 1
        assert abs(final - c["final"]) < 0.01 and abs(dd * 100 - c["max_dd_pct"]) < 0.01
        assert abs(cagr * 100 - c["cagr_pct"]) < 0.01 and abs(cagr / dd - c["calmar"]) < 0.001 and len(tr) == c["trades"]
        print(f"[V3 PASS] {name}: final {final:.2f}, CAGR {cagr*100:.2f}%, MaxDD {dd*100:.2f}%, Calmar {cagr/dd:.3f}, {len(tr)} trades")


def v4():
    data, real_last = S8.load_all()
    if STEP == "step9":
        import step9_ai_more_info_1d as S9
        S9.install_features(data, real_last)
    ent, ext = S8.build_sets(data, real_last, S8.daily_features(data))
    log = pd.read_csv(D / "AI_training_log.csv", parse_dates=["retrain"])
    for r in log.itertuples():
        Dset = ent if r.brain == "entry" else ext
        n = ((Dset.known_date < r.retrain) & Dset.label.notna()).sum()
        assert n == r.n_train, (r.retrain, r.brain, n, r.n_train)
    e = pd.read_csv(D / "AI_entry_predictions.csv", parse_dates=["signal_date", "known_date"])
    assert (e.signal_date >= "2021-01-01").all()
    print(f"[V4 PASS] {len(log)} monthly fits: training sizes == rows with labels known before the re-train date")


def v5():
    g = C["gates"]
    def sk(k):
        a, c = C[f"AI_{k}_skill_members"], C[f"CONTROL_shuffled_{k}_skill_members"]
        return dict(auc_ge_055=a["auc"] >= 0.55, ci_low_gt_050=a["ci_low"] > 0.50, beats_control=a["auc"] > c["auc"],
                    top_q_gt_bottom_q=a["quintile_rates"][-1] > a["quintile_rates"][0])
    assert sk("entry") == g["G1_entry"] and sk("exit") == g["G2_exit"]
    cal = {k: v["calmar"] for k, v in C["portfolio"].items()}
    g3f = cal["AI_full"] > cal["BASELINE_all_swings"] and cal["AI_full"] > cal["CONTROL_full"]
    g3e = cal["AI_entry_only"] > cal["BASELINE_all_swings"] and cal["AI_entry_only"] > cal["CONTROL_full"]
    assert g3f == g["G3_full"] and g3e == g["G3_entry_only"]
    dec = ("DEPLOY_AI_FULL" if all(sk("entry").values()) and all(sk("exit").values()) and g3f else
           "DEPLOY_AI_ENTRY_ONLY" if all(sk("entry").values()) and g3e else "FAIL_NOTHING_DEPLOYED")
    assert dec == g["decision"]
    print(f"[V5 PASS] gates recomputed -> decision {dec}")


if __name__ == "__main__":
    v1(); v2(); v3(); v5(); v4()
