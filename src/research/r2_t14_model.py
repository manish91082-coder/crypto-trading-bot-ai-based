"""T14 stage 2: the UNCHANGED A3 pipeline (functions imported from r2_a3_brain) on the expanded-universe store.
Only differences (T14 protocol): data paths, N trials = 14 in the DSR, output names. main_t14 is a verbatim copy of
r2_a3_brain.main with those substitutions (generated mechanically; see logs/r2_4h_t14/CODE_NOTES.md)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_a3_brain as A3
from r2_a3_brain import (fit_predict, block_boot, Paths, portfolio, dsr, sha, SEED, NSHUF, NRAND, DEV0, DEV1, P1END, P3END)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "r2_4h_t14"
STORE = ROOT / "data" / "derived" / "r2_t14"
A3.STORE, A3.A1C, A3.OUT = STORE, STORE / "a1c_trades.parquet", OUT
load = A3.load


def main_t14():
    proto = OUT / "T14_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "T14_PROTOCOL_SHA256.txt").read_text().split()[0], "T14 protocol changed"
    assert sha(ROOT / "logs" / "r2_4h_a3" / "A3_PROTOCOL_PREREGISTERED.md") == "49bd3f5eb8368ec7e35dbe3c1099451d464e72561c5ba743cea8a92342991c4c"
    S, feats = load()
    rng = np.random.default_rng(SEED)
    O = fit_predict(S, feats)
    O.to_parquet(OUT / "oos_predictions.parquet", index=False)
    S["p"] = np.nan; S["take"] = False; S["m"] = 1.0
    S.loc[O.idx, "p"] = O.p.values; S.loc[O.idx, "take"] = O["take"].values; S.loc[O.idx, "m"] = O.m.values
    dev = S[(S.entry_time >= DEV0) & (S.entry_time < DEV1) & S.p.notna()]
    auc = roc_auc_score(dev.label, dev.p)
    auc_ci = block_boot(dev, lambda x: roc_auc_score(x.label, x.p) - 0.5 if x.label.nunique() == 2 else None, rng)
    shuf = []
    for s in range(NSHUF):
        Os = fit_predict(S, feats, shuffle_seed=SEED + s)
        Ss = S.copy(); Ss["take"] = False; Ss["m"] = 1.0; Ss["p"] = np.nan
        Ss.loc[Os.idx, "p"] = Os.p.values; Ss.loc[Os.idx, "take"] = Os["take"].values; Ss.loc[Os.idx, "m"] = Os.m.values
        dv = Ss[(Ss.entry_time >= DEV0) & (Ss.entry_time < DEV1) & Ss.p.notna()]
        shuf.append(dict(seed=SEED + s, auc=roc_auc_score(dv.label, dv.p), _S=Ss))
        print("shuffle", s, round(shuf[-1]["auc"], 4), flush=True)
    sh_p95 = float(np.percentile([x["auc"] for x in shuf], 95))
    pd.DataFrame([{k: v for k, v in x.items() if k != "_S"} for x in shuf]).to_csv(OUT / "shuffled_auc.csv", index=False)
    # G-B, G-D, G-G
    tk = dev[dev["take"]]
    gb = tk.net_base.mean() - dev.net_base.mean()
    def diffstat(col):
        return lambda x: (x[x["take"]][col].mean() - x[col].mean()) if x["take"].any() else None
    gb_ci = block_boot(dev, diffstat("net_base"), rng)
    gb15_ci = block_boot(dev, diffstat("net_x1_5"), rng)
    top = dev[dev.net_base >= dev.net_base.quantile(0.9)]
    take_rate = dev["take"].mean(); tail_share = top["take"].mean()
    # portfolios
    paths = Paths(S)
    allrows = S.p.notna().values
    ai = portfolio(S, (S["take"] & allrows).values, S.m.values, paths)
    base = portfolio(S, allrows, np.ones(len(S)), paths)
    rnd = []
    for i in range(NRAND):
        rr = np.random.default_rng(SEED + i)
        take = np.zeros(len(S), bool); mult = np.ones(len(S))
        for M, g in S[allrows].groupby("month"):
            n_ai = int(g["take"].sum())
            if n_ai == 0:
                continue
            pick = rr.choice(g.index.values, n_ai, replace=False)
            take[pick] = True
            mult[pick] = rr.permutation(g.loc[g["take"], "m"].values)
        rnd.append(portfolio(S, take, mult, paths)["calmar"])
    rnd_p95 = float(np.percentile(rnd, 95))
    per = {}
    for name, a, b in (("P1", DEV0, P1END), ("P2", P1END, DEV1)):
        x = dev[(dev.entry_time >= a) & (dev.entry_time < b)]
        pa = portfolio(S, (S["take"] & allrows).values, S.m.values, paths, a, b)
        pb = portfolio(S, allrows, np.ones(len(S)), paths, a, b)
        per[name] = dict(net_taken=float(x[x["take"]].net_base.mean()), calmar_ai=pa["calmar"], calmar_base=pb["calmar"])
    p3 = S[(S.entry_time >= DEV1) & S.p.notna()]
    p3ai = portfolio(S, (S["take"] & allrows).values, S.m.values, paths, DEV1, P3END)
    p3b = portfolio(S, allrows, np.ones(len(S)), paths, DEV1, P3END)
    # G-H: 1D system
    sl = pd.read_csv(ROOT / "logs" / "strategy_1d_step27_combine" / "sleeves_MAIN_f50.csv", parse_dates=["date"]).set_index("date")
    one_d = (sl[["D1", "H4", "H1"]] / sl[["D1", "H4", "H1"]].iloc[0]).mean(axis=1)
    one_d = one_d[(one_d.index >= DEV0) & (one_d.index < DEV1)]
    r1d = one_d.resample("MS").last().pct_change().dropna()
    rai = ai["monthly"]
    j = pd.concat([rai.rename("ai"), r1d.rename("d1")], axis=1).dropna()
    corr = float(j.ai.corr(j.d1))
    comb = (1 + 0.5 * j.ai + 0.5 * j.d1).cumprod()
    def calm(c):
        yrs = len(c) / 12
        cg = c.iloc[-1] ** (1 / yrs) - 1
        dd = float((1 - c / c.cummax()).max())
        return cg / dd if dd > 0 else np.nan
    cal_comb, cal_ai_m, cal_1d = calm(comb), calm((1 + j.ai).cumprod()), calm((1 + j.d1).cumprod())
    # DSR
    sh_srs = []
    for x in shuf:
        pr = portfolio(x["_S"], (x["_S"]["take"] & x["_S"].p.notna()).values, x["_S"].m.values, paths)["monthly"]
        sh_srs.append(pr.mean() / pr.std(ddof=1))
    dsr_v, sr_ai, sr0 = dsr(rai, float(np.var(sh_srs, ddof=1)), 14)
    gates = {
        "G-A": bool(auc > sh_p95 and auc_ci[0] > 0),
        "G-B": bool(gb_ci[0] > 0 and gb15_ci[0] > 0),
        "G-C": bool(ai["calmar"] > base["calmar"] and ai["calmar"] > rnd_p95),
        "G-D": bool(tail_share >= take_rate),
        "G-E": bool(all(v["net_taken"] > 0 and v["calmar_ai"] > v["calmar_base"] for v in per.values())),
        "G-G": bool(tk.net_x1_5.mean() > 0 and tk.net_x2.mean() > 0),
        "G-H": bool(corr <= 0.70 or cal_comb > max(cal_ai_m, cal_1d)),
        "DSR": bool(dsr_v >= 0.95),
    }
    verdict = "T14 provisional PASS" if all(gates.values()) else "T14 FAIL"
    rows = [dict(gate=k, pass_=v) for k, v in gates.items()]
    pd.DataFrame(rows).to_csv(OUT / "A3_gates.csv", index=False)
    port = pd.DataFrame([dict(name=n, **{k: v for k, v in p.items() if k not in ("monthly", "eq")}) for n, p in
                         (("AI", ai), ("baseline", base), ("AI_P3", p3ai), ("baseline_P3", p3b))])
    port.to_csv(OUT / "A3_portfolio.csv", index=False)
    claims = dict(protocol_sha=sha(proto), store_sha=sha(STORE / "feature_store.parquet"), oos_sha=sha(OUT / "oos_predictions.parquet"),
                  n_dev=int(len(dev)), auc_dev=float(auc), auc_ci_minus_half=[float(x) for x in auc_ci], shuffled_auc_p95=sh_p95,
                  take_rate=float(take_rate), net_all=float(dev.net_base.mean()), net_taken=float(tk.net_base.mean()), gb_diff=float(gb),
                  gb_ci=[float(x) for x in gb_ci], gb15_ci=[float(x) for x in gb15_ci], tail_share=float(tail_share),
                  net_taken_x1_5=float(tk.net_x1_5.mean()), net_taken_x2=float(tk.net_x2.mean()),
                  ai=dict(final=ai["final"], cagr=ai["cagr"], mtm_dd=ai["mtm_dd"], real_dd=ai["real_dd"], calmar=ai["calmar"], taken=ai["taken"]),
                  baseline=dict(final=base["final"], cagr=base["cagr"], mtm_dd=base["mtm_dd"], real_dd=base["real_dd"], calmar=base["calmar"], taken=base["taken"]),
                  random_skip_calmar_p95=rnd_p95, periods=per, corr_1d=corr, calmar_comb=cal_comb, calmar_ai_monthly=cal_ai_m, calmar_1d=cal_1d,
                  dsr=dsr_v, sr_ai_monthly=sr_ai, sr0=sr0, gates=gates, verdict=verdict,
                  p3=dict(auc=float(roc_auc_score(p3.label, p3.p)), net_all=float(p3.net_base.mean()),
                          net_taken=float(p3[p3["take"]].net_base.mean()), ai_calmar=p3ai["calmar"], base_calmar=p3b["calmar"],
                          ai_final=p3ai["final"], base_final=p3b["final"]),
                  deferred=["PBO (needs >=4 configs; A5)", "G-I 2018-19 (once, on the frozen A5 config)"])
    (OUT / "claims_t14.json").write_text(json.dumps(claims, indent=1, default=float))
    print(json.dumps(claims, indent=1, default=float))


if __name__ == "__main__":
    main_t14()
