"""BTC-ALLTF study (2026-10-28): numbers for the Hindi report, read only from a finished job's files (no new computation of
trades). Usage: python src/btc_alltf/report_tables.py --run <RUN dir> [--jobs spot:1d ...]
Writes <RUN>/report/<market>_<tf>.md (tables) and <RUN>/report/cross_tf.csv (one row per job)."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
CFG = json.loads((PROJ / "logs/btc_alltf_2026_10_28/STUDY_CONFIG.json").read_text(encoding="utf-8"))


def pct(x, d=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{100 * x:+.{d}f}%"


def job_tables(run, m, tf):
    job = run / m / tf
    S = json.loads((job / "summary.json").read_text())
    cf = pd.read_parquet(job / "configs.parquet")
    eb = pd.read_parquet(job / "every_bar.parquet")
    L = []
    L.append(f"### {m} {tf}\n")
    L.append(f"- Bars {S['bars']:,} ({S['first']} → {S['last']}); fee per side {S['fee_per_side'] * 100:.3f}%")
    L.append(f"- Configs {S['configs']:,} (unique {S['unique']:,}, duplicates {S['duplicates']:,}); **trades {S['trades']:,}**")
    v = S["verdict"]
    L.append(f"- Verdict: PASS {v.get('PASS', 0):,} / FAIL {v.get('FAIL', 0):,} / INSUFFICIENT {v.get('INSUFFICIENT', 0):,}")
    L.append(f"- Gate passes: " + ", ".join(f"{k} {n:,}" for k, n in S["gates_pass"].items()))
    act = cf[cf.n > 0]
    L.append(f"- Configs with trades {len(act):,}: gross > 0 in {100 * (act.mean_gross > 0).mean():.1f}%, net > 0 in "
             f"{100 * (act['mean'] > 0).mean():.1f}%; trade win rate overall {100 * act.wins.sum() / max(1, act.n.sum()):.1f}%")
    rows = []
    for h in CFG["every_bar_holds"]:
        if f"r{h}" in eb and eb[f"r{h}"].notna().any():
            r = eb[f"r{h}"].dropna()
            rows.append((h, len(r), r.abs().mean(), eb[f"pass_long{h}"][r.index].mean(), eb[f"pass_short{h}"][r.index].mean()))
    if rows:
        L.append("\n| हर संभव trade: hold (bars) | trades | औसत |चाल| | long fee के बाद PASS | short fee के बाद PASS |\n|---|---|---|---|---|")
        for h, n, a, pl, ps in rows:
            L.append(f"| {h} | {n:,} | {100 * a:.3f}% | {100 * pl:.1f}% | {100 * ps:.1f}% |")
    top = cf.sort_values("rank").head(10)
    if len(top):
        L.append("\n| rank | config | verdict | gates | n | win % | mean net | median | D | V | H | H 2×fee | H delay | ctrl z | DSR | max DD |"
                 "\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in top.iterrows():
            L.append(f"| {r['rank']} | `{r['name']}` | {r.verdict} | {r.gates_passed} | {int(r.n):,} | {100 * r.winrate:.1f} | {pct(r['mean'])} | "
                     f"{pct(r['median'])} | {pct(r.mean_D)} | {pct(r.mean_V)} | {pct(r.mean_H)} | {pct(r.mean_H_2xfee)} | {pct(r.mean_H_delay1)} | "
                     f"{r.ctrl_z:.2f} | {r.dsr:.3f} | {100 * r.max_dd:.1f}% |")
    # exits / stops: median of config mean net per exit, L1 only
    l1 = act[act.layer == "L1"]
    if len(l1):
        g = l1.groupby("exit").agg(configs=("cfg", "size"), med_mean=("mean", "median"), med_gross=("mean_gross", "median"),
                                   share_net_pos=("mean", lambda s: (s > 0).mean()), trades=("n", "sum"))
        L.append("\n| exit (L1) | configs | trades | median config mean net | median mean gross | net > 0 configs |\n|---|---|---|---|---|---|")
        for ex, r in g.iterrows():
            L.append(f"| {ex} | {int(r.configs):,} | {int(r.trades):,} | {pct(r.med_mean)} | {pct(r.med_gross)} | {100 * r.share_net_pos:.1f}% |")
        g2 = l1.groupby(["dlabel", "side"]).agg(configs=("cfg", "size"), med_mean=("mean", "median"), share=("mean", lambda s: (s > 0).mean()))
        L.append("\n| direction | side | configs | median mean net | net > 0 |\n|---|---|---|---|---|")
        for (dl, sd), r in g2.iterrows():
            L.append(f"| {dl} | {sd} | {int(r.configs):,} | {pct(r.med_mean)} | {100 * r.share:.1f}% |")
        g3 = l1.groupby("cat").agg(configs=("cfg", "size"), med_mean=("mean", "median"), best=("mean", "max"), share=("mean", lambda s: (s > 0).mean()))
        L.append("\n| category (L1) | configs | median mean net | best mean net | net > 0 |\n|---|---|---|---|---|")
        for cat, r in g3.iterrows():
            L.append(f"| {cat} | {int(r.configs):,} | {pct(r.med_mean)} | {pct(r.best)} | {100 * r.share:.1f}% |")
    # stop-loss effect, paired: same rule / direction / side, exit Xk minus X0 (signal only), rules with >= 30 trades in X0
    if len(l1):
        base = l1[(l1.exit == "X0_SIG") & (l1.n >= 30)].set_index(["rule", "dlabel", "side"])["mean"]
        if len(base):
            L.append("\n| stop / exit vs X0 (paired, same rule) | pairs | median change of mean net | exit better than X0 |\n|---|---|---|---|")
            for ex in ["X1_SIG_SL1", "X2_SIG_SL2", "X3_SIG_SL3", "X4_SIG_TRAIL3", "X5_SIG_SL1.5_TP3", "X6_SIG_SL2_TP2", "X7_HOLD1", "X8_HOLD10_SL2"]:
                oth = l1[l1.exit == ex].set_index(["rule", "dlabel", "side"])["mean"]
                j = base.index.intersection(oth.index)
                if len(j):
                    dlt = oth.loc[j] - base.loc[j]
                    L.append(f"| {ex} | {len(j):,} | {pct(float(dlt.median()))} | {100 * (dlt > 0).mean():.1f}% |")
    prj = act[act.tags.fillna("").str.startswith("PRJ") & (act.layer == "L1") & (act.side == "nat")]
    if len(prj):
        best = prj.sort_values("t", ascending=False).groupby("rule").head(1)
        L.append("\n| project rule (best exit, natural) | config | n | win % | mean net | H | verdict |\n|---|---|---|---|---|---|---|")
        for _, r in best.iterrows():
            L.append(f"| {r.rule} | `{r['name']}` | {int(r.n):,} | {100 * r.winrate:.1f} | {pct(r['mean'])} | {pct(r.mean_H)} | {r.verdict} |")
    lay = act.groupby("layer").agg(configs=("cfg", "size"), med=("mean", "median"), share=("mean", lambda s: (s > 0).mean()), best=("mean", "max"))
    L.append("\n| layer | configs | median mean net | net > 0 | best mean net |\n|---|---|---|---|---|")
    for ly, r in lay.iterrows():
        L.append(f"| {ly} | {int(r.configs):,} | {pct(r.med)} | {100 * r.share:.1f}% | {pct(r.best)} |")
    cross = dict(market=m, tf=tf, bars=S["bars"], configs=S["unique"], trades=S["trades"], PASS=v.get("PASS", 0), FAIL=v.get("FAIL", 0),
                 INSUFFICIENT=v.get("INSUFFICIENT", 0), gross_pos_share=float((act.mean_gross > 0).mean()) if len(act) else np.nan,
                 net_pos_share=float((act["mean"] > 0).mean()) if len(act) else np.nan,
                 win_rate=float(act.wins.sum() / max(1, act.n.sum())), best_name=top.iloc[0]["name"] if len(top) else "",
                 best_verdict=top.iloc[0].verdict if len(top) else "", best_mean=float(top.iloc[0]["mean"]) if len(top) else np.nan,
                 best_H=float(top.iloc[0].mean_H) if len(top) else np.nan, best_gates=int(top.iloc[0].gates_passed) if len(top) else 0,
                 **{f"pass_{g}": S["gates_pass"].get(g, 0) for g in ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]})
    return "\n".join(L) + "\n", cross


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--jobs", nargs="*")
    a = ap.parse_args()
    run = Path(a.run)
    (run / "report").mkdir(exist_ok=True)
    jobs = [tuple(j.split(":")) for j in a.jobs] if a.jobs else [(m, tf) for tf in CFG["timeframes"] for m in CFG["markets"]]
    cr = []
    for m, tf in jobs:
        if not (run / m / tf / "DONE.json").exists():
            continue
        md, c = job_tables(run, m, tf)
        (run / "report" / f"{m}_{tf}.md").write_text(md, encoding="utf-8")
        cr.append(c)
        print(f"{m} {tf}: tables written")
    if cr:
        old = run / "report" / "cross_tf.csv"
        df = pd.DataFrame(cr)
        if old.exists():
            prev = pd.read_csv(old)
            df = pd.concat([prev[~prev.set_index(["market", "tf"]).index.isin(df.set_index(["market", "tf"]).index)], df], ignore_index=True)
        df.to_csv(old, index=False)


if __name__ == "__main__":
    main()
