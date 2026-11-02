"""BTC-ALLTF study (2026-10-28): cross-timeframe tables for the report, read only from the finished jobs' configs / summary /
every_bar files. Usage: python src/btc_alltf/cross_tf.py --run <RUN dir>  -> <RUN>/report/cross_tf.md + cross_tf_*.csv"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
CFG = json.loads((PROJ / "logs/btc_alltf_2026_10_28/STUDY_CONFIG.json").read_text(encoding="utf-8"))
TFS = CFG["timeframes"]
PRJ = ["T_TSMOM20", "T_EMAX20_50", "T_MACD12_26_9sig", "T_DONCH20_10", "O_RSI14_30_70", "O_BB20_2", "T_SMA200", "P_GREEN", "P_MICRO3",
       "V_LOWVOL_TS20", "O_CONNORS", "P_DOUBLE", "P_ZIGZAG3", "P_SRBOUNCE"]


def f(x, d=3):
    return "—" if x is None or not np.isfinite(x) else f"{100 * x:+.{d}f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    run = Path(a.run)
    out = run / "report"
    out.mkdir(exist_ok=True)
    rows, prj, stops, dirs, fam = [], [], [], [], []
    for tf in TFS:
        for m in CFG["markets"]:
            job = run / m / tf
            if not (job / "DONE.json").exists():
                continue
            S = json.loads((job / "summary.json").read_text())
            c = pd.read_parquet(job / "configs.parquet")
            eb = pd.read_parquet(job / "every_bar.parquet", columns=["r1", "pass_long1", "pass_short1"])
            act = c[c.n > 0]
            top = c.sort_values("rank").iloc[0]
            g1 = c[c.G1]
            rows.append(dict(tf=tf, market=m, bars=S["bars"], configs=S["unique"], trades=S["trades"], PASS=S["verdict"].get("PASS", 0),
                             FAIL=S["verdict"].get("FAIL", 0), INSUFFICIENT=S["verdict"].get("INSUFFICIENT", 0),
                             gross_pos=(act.mean_gross > 0).mean(), net_pos=(act["mean"] > 0).mean(), trade_win=act.wins.sum() / max(1, act.n.sum()),
                             every_bar_move=eb.r1.abs().mean(), every_bar_long_pass=eb.pass_long1[eb.r1.notna()].mean(),
                             every_bar_short_pass=eb.pass_short1[eb.r1.notna()].mean(), G1=len(g1), G12=int(g1.G2.sum()),
                             G124=int((g1.G2 & g1.G4).sum()), G1246=int((g1.G2 & g1.G4 & g1.G6).sum()), min_q=c.q_bh.min(), max_dsr=c.dsr.max(),
                             top=top["name"], top_verdict=top.verdict, top_gates=int(top.gates_passed), top_n=int(top.n), top_mean=top["mean"],
                             top_H=top.mean_H, top_z=top.ctrl_z))
            l1 = act[(act.layer == "L1")]
            for r in PRJ:
                x = l1[(l1.rule == r) & (l1.side == "nat") & (l1.dlabel == "long") & (l1.exit == "X0_SIG")]
                if len(x):
                    x = x.iloc[0]
                    prj.append(dict(rule=r, tf=tf, market=m, n=int(x.n), mean=x["mean"], H=x.mean_H, win=x.winrate, verdict=x.verdict))
            base = l1[(l1.exit == "X0_SIG") & (l1.n >= 30)].set_index(["rule", "dlabel", "side"])["mean"]
            for ex in ["X1_SIG_SL1", "X2_SIG_SL2", "X3_SIG_SL3", "X4_SIG_TRAIL3", "X5_SIG_SL1.5_TP3", "X6_SIG_SL2_TP2", "X7_HOLD1", "X8_HOLD10_SL2"]:
                o = l1[l1.exit == ex].set_index(["rule", "dlabel", "side"])["mean"]
                j = base.index.intersection(o.index)
                if len(j):
                    stops.append(dict(tf=tf, market=m, exit=ex, pairs=len(j), better=float(((o.loc[j] - base.loc[j]) > 0).mean()),
                                      median_change=float((o.loc[j] - base.loc[j]).median())))
            for (dl, sd), g in l1.groupby(["dlabel", "side"]):
                dirs.append(dict(tf=tf, market=m, dir=dl, side=sd, configs=len(g), median=g["mean"].median(), pos=(g["mean"] > 0).mean()))
            hv = act[(act.gate == "F4_HIGHVOL") & (act.dlabel == "long")]
            al = act[(act.layer == "L1") & (act.dlabel == "long")]
            fam.append(dict(tf=tf, market=m, highvol_long_configs=len(hv), highvol_median=hv["mean"].median(), highvol_z2=(hv.ctrl_z >= 2).mean(),
                            l1_long_median=al["mean"].median(), l1_long_z2=(al.ctrl_z >= 2).mean()))
    R = pd.DataFrame(rows)
    R.to_csv(out / "cross_tf_jobs.csv", index=False)
    P = pd.DataFrame(prj)
    P.to_csv(out / "cross_tf_project_rules.csv", index=False)
    St = pd.DataFrame(stops)
    St.to_csv(out / "cross_tf_stops.csv", index=False)
    D = pd.DataFrame(dirs)
    D.to_csv(out / "cross_tf_directions.csv", index=False)
    Fm = pd.DataFrame(fam)
    Fm.to_csv(out / "cross_tf_highvol_family.csv", index=False)
    L = ["## Cross-timeframe tables (generated)\n"]
    L.append("| TF | market | candles | configs | trades | PASS | FAIL | INSUFF | gross>0 | net>0 | trade win | every-bar |move| | every-bar long PASS | G1 | +G2 | +G4 | +G6 | min q | max DSR |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in R.iterrows():
        L.append(f"| {r.tf} | {r.market} | {r.bars:,} | {r.configs:,} | {r.trades:,} | {r.PASS} | {r.FAIL:,} | {r.INSUFFICIENT:,} | {100 * r.gross_pos:.1f}% | "
                 f"{100 * r.net_pos:.1f}% | {100 * r.trade_win:.1f}% | {100 * r.every_bar_move:.3f}% | {100 * r.every_bar_long_pass:.1f}% | {r.G1:,} | {r.G12:,} | "
                 f"{r.G124:,} | {r.G1246:,} | {r.min_q:.3f} | {r.max_dsr:.3f} |")
    L.append("\n| TF | market | top-ranked config | verdict | gates | n | mean net | H | z |\n|---|---|---|---|---|---|---|---|---|")
    for _, r in R.iterrows():
        L.append(f"| {r.tf} | {r.market} | `{r.top}` | {r.top_verdict} | {r.top_gates} | {r.top_n:,} | {f(r.top_mean)} | {f(r.top_H)} | {r.top_z:.2f} |")
    if len(P):
        piv = P.pivot_table(index="rule", columns=["market", "tf"], values="mean", aggfunc="first")
        cols = [(m, tf) for m in CFG["markets"] for tf in TFS if (m, tf) in piv.columns]
        L.append("\n**Project rules, natural long, X0 (signal exit): mean net per trade**\n")
        L.append("| rule | " + " | ".join(f"{m[:3]} {tf}" for m, tf in cols) + " |")
        L.append("|---|" + "---|" * len(cols))
        for rule, r in piv.iterrows():
            L.append(f"| {rule} | " + " | ".join(f(r.get(cc), 2) for cc in cols) + " |")
    if len(St):
        pv = St.pivot_table(index="exit", columns=["market", "tf"], values="better")
        cols = [(m, tf) for m in CFG["markets"] for tf in TFS if (m, tf) in pv.columns]
        L.append("\n**Stops / exits: share of rules where the exit beats X0 (paired, same rule, X0 n >= 30)**\n")
        L.append("| exit | " + " | ".join(f"{m[:3]} {tf}" for m, tf in cols) + " |")
        L.append("|---|" + "---|" * len(cols))
        for ex, r in pv.iterrows():
            L.append(f"| {ex} | " + " | ".join("—" if not np.isfinite(r.get(cc, np.nan)) else f"{100 * r.get(cc):.0f}%" for cc in cols) + " |")
    if len(D):
        L.append("\n**Directions (L1): median config mean net, share of configs > 0**\n")
        L.append("| TF | market | long nat | long con | short nat | short con |\n|---|---|---|---|---|---|")
        for (tf, m), g in D.groupby(["tf", "market"], sort=False):
            def cell(dl, sd):
                x = g[(g.dir == dl) & (g.side == sd)]
                return "—" if not len(x) else f"{f(x['median'].iloc[0])} ({100 * x.pos.iloc[0]:.0f}%)"
            L.append(f"| {tf} | {m} | {cell('long', 'nat')} | {cell('long', 'con')} | {cell('short', 'nat')} | {cell('short', 'con')} |")
    if len(Fm):
        L.append("\n**High-volatility long family vs all L1 longs**\n")
        L.append("| TF | market | high-vol long configs | median mean net | z >= 2 share | all L1 long median | z >= 2 share |\n|---|---|---|---|---|---|---|")
        for _, r in Fm.iterrows():
            L.append(f"| {r.tf} | {r.market} | {r.highvol_long_configs:,} | {f(r.highvol_median)} | {100 * r.highvol_z2:.1f}% | {f(r.l1_long_median)} | {100 * r.l1_long_z2:.1f}% |")
    # overall ranking across all jobs: verdict, gates passed, then t (the locked per-job rank rule, applied to the pooled list)
    allc = []
    for tf in TFS:
        for m in CFG["markets"]:
            job = run / m / tf
            if (job / "DONE.json").exists():
                c = pd.read_parquet(job / "configs.parquet", columns=["name", "n", "winrate", "mean", "mean_D", "mean_V", "mean_H", "ctrl_z", "q_bh",
                                                                      "dsr", "verdict", "gates_passed", "t"])
                c["tf"], c["market"] = tf, m
                allc.append(c[c.n >= 30])
    if allc:
        A = pd.concat(allc, ignore_index=True)
        A["vk"] = A.verdict.map({"PASS": 0, "FAIL": 1, "INSUFFICIENT": 2})
        A = A.sort_values(["vk", "gates_passed", "t"], ascending=[True, False, False]).head(30)
        A.to_csv(out / "cross_tf_overall_top30.csv", index=False)
        L.append("\n**Overall top 30 across all timeframes and markets (n >= 30; PASS first, then gates passed, then t)**\n")
        L.append("| # | TF | market | config | verdict | gates | n | win % | mean net | D | V | H | z | q | DSR |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for i, (_, r) in enumerate(A.iterrows(), 1):
            L.append(f"| {i} | {r.tf} | {r.market} | `{r['name']}` | {r.verdict} | {r.gates_passed} | {int(r.n):,} | {100 * r.winrate:.1f} | {f(r['mean'])} | "
                     f"{f(r.mean_D)} | {f(r.mean_V)} | {f(r.mean_H)} | {r.ctrl_z:.2f} | {r.q_bh:.3f} | {r.dsr:.3f} |")
    (out / "cross_tf.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"written {out / 'cross_tf.md'} ({len(R)} jobs)")


if __name__ == "__main__":
    main()
