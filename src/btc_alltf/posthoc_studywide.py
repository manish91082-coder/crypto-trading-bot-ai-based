"""BTC-ALLTF study (2026-10-28): POST-HOC (not pre-registered) study-wide multiple-testing view, written down so that a PASS
under the per-job gates can be read honestly. The locked verdicts are NOT changed by this script.
  - BH over the p-values of ALL unique configs of ALL finished jobs (not per job)
  - DSR with N = all unique configs of all jobs, and the per-trade Sharpe variance V of the job (as locked) and of all jobs
  - for every locked PASS: its study-wide q and DSR, and the same rule/direction/exit/filter on every other job (replication)
Usage: python src/btc_alltf/posthoc_studywide.py --run <RUN dir>  -> <RUN>/report/posthoc_studywide.md"""
import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(q, 1)
    return out


def dsr(mean, sd, n, sk, ku, N, V):
    sr = mean / sd
    em = 0.5772156649
    sr0 = np.sqrt(V) * ((1 - em) * norm.ppf(1 - 1 / N) + em * norm.ppf(1 - 1 / (N * np.e)))
    den = 1 - sk * sr + (ku - 1) / 4 * sr ** 2
    return norm.cdf((sr - sr0) * np.sqrt(n - 1) / np.sqrt(np.where(den > 0, den, np.nan)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    run = Path(a.run)
    parts = []
    for f in glob.glob(str(run / "*" / "*" / "configs.parquet")):
        m, tf = Path(f).parts[-3:-1]
        if not (Path(f).parent / "DONE.json").exists():
            continue
        c = pd.read_parquet(f, columns=["cfg", "name", "n", "mean", "sd", "skew", "kurt", "p", "q_bh", "dsr", "verdict", "mean_D", "mean_V", "mean_H",
                                        "ctrl_z", "winrate"])
        c["market"], c["tf"] = m, tf
        parts.append(c)
    A = pd.concat(parts, ignore_index=True)
    A["q_study"] = bh(A.p.fillna(1).values)
    ok = (A.n >= 30) & (A.sd > 0)
    V_all = float(np.var((A["mean"] / A.sd)[ok]))
    N_all = len(A)
    A["dsr_study"] = np.where(ok, dsr(A["mean"].values, A.sd.values, A.n.values, A["skew"].fillna(0).values, A["kurt"].fillna(3).values, N_all, V_all), np.nan)
    # per-job V (as locked) with N = all configs of the study: only the number of trials changes
    Vj = A[ok].assign(sr=lambda d: d["mean"] / d.sd).groupby(["market", "tf"]).sr.var(ddof=0)
    vj = A.set_index(["market", "tf"]).index.map(lambda k: Vj.get(k, np.nan)).values.astype(float)
    A["dsr_studyN"] = np.where(ok, dsr(A["mean"].values, A.sd.values, A.n.values, A["skew"].fillna(0).values, A["kurt"].fillna(3).values, N_all, vj), np.nan)
    L = [f"## Post-hoc study-wide check (NOT pre-registered; the locked verdicts are unchanged)\n",
         f"- Jobs: {A.groupby(['market', 'tf']).ngroups}; unique configs N = {N_all:,}; per-trade Sharpe variance over configs with n >= 30: V = {V_all:.6f}",
         f"- Configs with study-wide BH q <= 0.05: {int((A.q_study <= 0.05).sum())}; with study-wide DSR >= 0.95: {int((A.dsr_study >= 0.95).sum())}",
         f"- Configs with both: {int(((A.q_study <= 0.05) & (A.dsr_study >= 0.95)).sum())}",
         f"- DSR with the job's own V (as locked) and N = all {N_all:,} configs: >= 0.95 in {int((A.dsr_studyN >= 0.95).sum())} configs; "
         f"study q <= 0.05 and that DSR >= 0.95: {int(((A.q_study <= 0.05) & (A.dsr_studyN >= 0.95)).sum())}\n"]
    top = A.sort_values("q_study").head(15)
    L.append("| market | tf | config | n | win % | mean net | job q | study q | job DSR | DSR (job V, N all) | DSR (pooled V, N all) | locked verdict |\n"
             "|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in top.iterrows():
        L.append(f"| {r.market} | {r.tf} | `{r['name']}` | {int(r.n)} | {100 * r.winrate:.1f} | {100 * r['mean']:+.3f}% | {r.q_bh:.4f} | {r.q_study:.4f} | "
                 f"{r.dsr:.3f} | {r.dsr_studyN:.3f} | {r.dsr_study:.3f} | {r.verdict} |")
    for _, r in A[A.verdict == "PASS"].iterrows():
        core = r["name"].split("|")
        same = A[A["name"] == r["name"]].sort_values(["market", "tf"])
        L.append(f"\n**Locked PASS `{r['name']}` ({r.market} {r.tf}): the identical config on every job**\n")
        L.append("| market | tf | n | win % | mean net | D | V | H | z | verdict |\n|---|---|---|---|---|---|---|---|---|---|")
        for _, s in same.iterrows():
            L.append(f"| {s.market} | {s.tf} | {int(s.n)} | {100 * s.winrate:.1f} | {100 * s['mean']:+.3f}% | {100 * s.mean_D:+.3f}% | {100 * s.mean_V:+.3f}% | "
                     f"{100 * s.mean_H:+.3f}% | {s.ctrl_z:.2f} | {s.verdict} |" if s.n else f"| {s.market} | {s.tf} | 0 | — | — | — | — | — | — | {s.verdict} |")
    out = run / "report" / "posthoc_studywide.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    A[["market", "tf", "cfg", "name", "q_bh", "q_study", "dsr", "dsr_studyN", "dsr_study", "verdict"]].to_parquet(run / "report" / "posthoc_studywide.parquet", index=False)
    print("\n".join(L[:4]))


if __name__ == "__main__":
    main()
