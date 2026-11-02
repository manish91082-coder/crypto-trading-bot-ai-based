"""BTC-ALLTF-R2 (2026-10-29): tables for the Hindi report, read only from the finished outputs (no trading, no new numbers).
Writes <RUN>/report/*.md and *.csv.
Usage: python src/btc_alltf_r2/report_r2.py --run <R2 RUN dir>"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402

BARS = K.PROJ / "data/derived/btc_alltf/bars"


def pc(x, d=1):
    return "—" if x is None or not np.isfinite(x) else f"{100 * x:+.{d}f}%"


def md_table(D, cols, fmt):
    L = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in D.iterrows():
        L.append("| " + " | ".join(fmt.get(c, str)(r[c]) for c in cols) + " |")
    return "\n".join(L)


def btc_insample(out):
    rows = []
    for market in ("spot", "futures"):
        d1 = pd.read_parquet(BARS / f"{market}_1d.parquet", columns=["ts", "close"])
        for tf in K.CFG["r1_jobs"][market]:
            Z = np.load(K.DER / "mtm" / f"{market}_{tf}.npz")
            day0, nd = int(Z["day0"]), int(Z["nd"])
            c = pd.Series(d1.close.values, index=d1.ts.values // K.DAY - day0).reindex(np.arange(nd))
            bh = (c / c.shift(1) - 1).fillna(0).values
            PB = K.perf(bh)
            r = np.expm1(Z["L"].astype(np.float64))
            eq = np.exp(Z["L"].astype(np.float64).sum(1))
            sd = r.std(1, ddof=1)
            sh = np.where(sd > 0, r.mean(1) / np.where(sd > 0, sd, 1) * np.sqrt(365), np.nan)
            e = np.cumprod(1 + r, axis=1)
            dd = (1 - e / np.maximum.accumulate(e, axis=1)).max(1)
            dd = np.maximum(dd, 1 - e.min(1).clip(max=1))
            names = pd.read_parquet(K.R1RUN / market / tf / "configs.parquet", columns=["cfg", "name", "n"]).set_index("cfg").loc[Z["cfg"]]
            act = names.n.fillna(0).values > 0
            beat = act & (sh > PB["sharpe"]) & (dd < PB["maxdd"])
            i = int(np.nanargmax(np.where(act, sh, np.nan)))
            rows.append(dict(market=market, tf=tf, configs=int(act.sum()), profit=int((act & (eq > 1)).sum()), profit_share=float((eq[act] > 1).mean()),
                             beat_bh=int(beat.sum()), median_sharpe=float(np.nanmedian(sh[act])), bh_sharpe=PB["sharpe"], bh_maxdd=PB["maxdd"],
                             bh_total=PB["total"], best=names.name.values[i], best_sharpe=float(sh[i]), best_total=float(eq[i] - 1), best_dd=float(dd[i])))
            print("insample", market, tf, flush=True)
    D = pd.DataFrame(rows)
    D.to_csv(out / "btc_insample.csv", index=False)
    return D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--skip-insample", action="store_true")
    a = ap.parse_args()
    run = Path(a.run)
    out = run / "report"
    out.mkdir(exist_ok=True)
    L = []
    f2 = lambda x: "—" if not np.isfinite(x) else f"{x:.2f}"                 # noqa: E731
    if not a.skip_insample:
        D = btc_insample(out)
        L.append("## BTC in-sample (descriptive, daily MTM, full period)\n")
        L.append(md_table(D, ["market", "tf", "configs", "profit", "profit_share", "beat_bh", "median_sharpe", "bh_sharpe", "bh_maxdd", "best", "best_sharpe",
                              "best_total", "best_dd"],
                          dict(profit_share=lambda x: f"{100 * x:.1f}%", median_sharpe=f2, bh_sharpe=f2, bh_maxdd=lambda x: f"{100 * x:.0f}%",
                               best=lambda x: f"`{x}`", best_sharpe=f2, best_total=pc, best_dd=lambda x: f"{100 * x:.0f}%")))
    T = run / "tests"
    if (T / "tests_WF.csv").exists():
        W = pd.read_csv(T / "tests_WF.csv")
        P = W[W.setting == "primary"]
        L.append("\n## Walk-forward, primary setting (OOS 2021-01-01 .. 2026-09-30)\n")
        L.append(md_table(P, ["pool", "total", "cagr", "sharpe", "maxdd", "tA", "qA", "tB", "qB", "sub1", "sub2", "sub3", "WF_PROFIT", "WF_SKILL",
                              "btc_total", "btc_sharpe", "btc_maxdd", "BEATS_BTC_BH"],
                          dict(total=pc, cagr=pc, sharpe=f2, maxdd=lambda x: f"{100 * x:.0f}%", tA=f2, tB=f2, qA=lambda x: f"{x:.3f}",
                               qB=lambda x: f"{x:.3f}", sub1=pc, sub2=pc, sub3=pc, btc_total=pc, btc_sharpe=f2, btc_maxdd=lambda x: f"{100 * x:.0f}%")))
        S = W[W.setting != "primary"].pivot_table(index="pool", columns="setting", values="sharpe")
        S.to_csv(out / "wf_sensitivity_sharpe.csv")
        L.append("\n**Walk-forward sensitivity: OOS Sharpe per setting**\n")
        L.append(S.round(2).to_markdown())
    if (T / "tests_S1.csv").exists():
        S1 = pd.read_csv(T / "tests_S1.csv")
        g = S1.groupby(["market", "tf"], sort=False).agg(configs=("name", "size"), profit_pos=("cagr", lambda x: int((x > 0).sum())),
                                                          confirmed_profit=("CONFIRMED_PROFIT", "sum"), confirmed_skill=("CONFIRMED_SKILL", "sum"),
                                                          beats_bh=("BEATS_BH", "sum"), median_sharpe=("sharpe", "median"),
                                                          median_tB=("tB", "median"), bh_sharpe=("bh_sharpe", "first"), bh_cagr=("bh_cagr", "first"),
                                                          coins=("mean_coins", "median")).reset_index()
        g.to_csv(out / "s1_by_job.csv", index=False)
        L.append("\n## Cross-coin S1 (BTC top 20 per job on every other coin): per job\n")
        L.append(g.to_markdown(index=False, floatfmt=".3f"))
        C = S1[S1.CONFIRMED_PROFIT].sort_values("tB", ascending=False)
        L.append(f"\n**S1 CONFIRMED_PROFIT: {len(C)} configs, of which CONFIRMED_SKILL {int(C.CONFIRMED_SKILL.sum())}**\n")
        L.append(md_table(C.head(60), ["market", "tf", "name", "cagr", "sharpe", "maxdd", "tA", "qA", "tB", "qB", "sub1", "sub2", "sub3", "cagr_2xfee",
                                       "coins_profit", "coins_traded", "bh_sharpe", "BEATS_BH", "CONFIRMED_SKILL", "btc_sharpe"],
                          dict(name=lambda x: f"`{x}`", cagr=pc, sharpe=f2, maxdd=lambda x: f"{100 * x:.0f}%", tA=f2, tB=f2,
                               qA=lambda x: f"{x:.4f}", qB=lambda x: f"{x:.4f}", sub1=pc, sub2=pc, sub3=pc, cagr_2xfee=pc, bh_sharpe=f2, btc_sharpe=f2,
                               coins_profit=lambda x: str(int(x)) if np.isfinite(x) else "—", coins_traded=lambda x: str(int(x)) if np.isfinite(x) else "—")))
    if (T / "tests_S2.csv").exists():
        S2 = pd.read_csv(T / "tests_S2.csv")
        p = S2.name.str.split("|", expand=True)
        S2["rule"], S2["dirside"], S2["exit"] = p[1], p[2], p[3]
        g = S2.groupby(["market", "tf"], sort=False).agg(configs=("name", "size"), profit_pos=("cagr", lambda x: int((x > 0).sum())),
                                                          confirmed_profit=("CONFIRMED_PROFIT", "sum"), confirmed_skill=("CONFIRMED_SKILL", "sum"),
                                                          beats_bh=("BEATS_BH", "sum"), bh_sharpe=("bh_sharpe", "first")).reset_index()
        g.to_csv(out / "s2_by_job.csv", index=False)
        L.append("\n## Cross-coin S2 (every L1 config on every coin): per job\n")
        L.append(g.to_markdown(index=False, floatfmt=".3f"))
        sk = S2[S2.CONFIRMED_SKILL].sort_values(["market", "tf", "tB"], ascending=[True, True, False])
        sk.to_csv(out / "s2_confirmed_skill.csv", index=False)
        top = S2.sort_values("tB", ascending=False).groupby(["market", "tf"], sort=False).head(8)
        L.append("\n**S2: the 8 configs with the highest skill t (test B) per job**\n")
        L.append(md_table(top, ["market", "tf", "name", "cagr", "sharpe", "maxdd", "tA", "qA", "tB", "qB", "sub1", "sub2", "sub3", "cagr_2xfee",
                                "CONFIRMED_PROFIT", "CONFIRMED_SKILL", "BEATS_BH"],
                          dict(name=lambda x: f"`{x}`", cagr=pc, sharpe=f2, maxdd=lambda x: f"{100 * x:.0f}%", tA=f2, tB=f2, qA=lambda x: f"{x:.4f}",
                               qB=lambda x: f"{x:.4f}", sub1=pc, sub2=pc, sub3=pc, cagr_2xfee=pc)))
        fam = S2.groupby(["market", "tf", "exit"]).agg(n=("name", "size"), skill=("CONFIRMED_SKILL", "sum"), profit=("CONFIRMED_PROFIT", "sum"),
                                                        median_tB=("tB", "median")).reset_index()
        fam.to_csv(out / "s2_by_exit.csv", index=False)
        rl = S2.groupby(["rule", "dirside"]).agg(jobs=("tf", "size"), skill=("CONFIRMED_SKILL", "sum"), profit=("CONFIRMED_PROFIT", "sum"),
                                                 median_tB=("tB", "median")).reset_index().sort_values("skill", ascending=False)
        rl.to_csv(out / "s2_by_rule.csv", index=False)
        L.append("\n**S2: rules with the most CONFIRMED_SKILL configs over all jobs and exits (top 25)**\n")
        L.append(rl.head(25).to_markdown(index=False, floatfmt=".2f"))
    if (T / "tests_CTRL.csv").exists():
        Cc = pd.read_csv(T / "tests_CTRL.csv")
        g = Cc.groupby(["ctrl"]).agg(n=("name", "size"), profit=("CONFIRMED_PROFIT", "mean"), skill=("CONFIRMED_SKILL", "mean"),
                                     median_tA=("tA", "median"), median_tB=("tB", "median"), median_sharpe=("sharpe", "median")).reset_index()
        g.to_csv(out / "ctrl_summary.csv", index=False)
        g2 = Cc.groupby(["ctrl", "market", "tf"]).agg(skill=("CONFIRMED_SKILL", "mean"), profit=("CONFIRMED_PROFIT", "mean"),
                                                       median_tB=("tB", "median")).reset_index()
        g2.to_csv(out / "ctrl_by_job.csv", index=False)
        L.append("\n## Controls through the same tests (share labelled)\n")
        L.append(g.to_markdown(index=False, floatfmt=".3f"))
        L.append("\n" + g2.pivot_table(index="ctrl", columns=["market", "tf"], values="skill").round(2).to_markdown())
    R1 = run / "r1pos" / "r1_poscontrol.csv"
    if R1.exists():
        D = pd.read_csv(R1)
        g = D.groupby(["tf", "acc"]).agg(n_trades=("n", "median"), mean=("mean", "median"), G1=("G1", "mean"), G2=("G2", "mean"), G3=("G3", "mean"),
                                         G4=("G4", "mean"), G5=("G5", "mean"), G6=("G6", "mean"), G7=("G7", "mean"),
                                         PASS=("verdict", lambda v: (v == "PASS").mean()), daily_sharpe=("daily_sharpe", "median"),
                                         nw_t=("nw_t", "median"), nw_p_le_005=("nw_p", lambda p: (p <= 0.05).mean())).reset_index()
        g.to_csv(out / "r1pos_summary.csv", index=False)
        L.append("\n## R1 positive control: share of noisy oracles passing each LOCKED gate (BTC spot)\n")
        L.append(g.to_markdown(index=False, floatfmt=".3f"))
    RE = sorted((run / "reentry").glob("reentry_*.parquet"))
    if RE:
        D = pd.concat([pd.read_parquet(f) for f in RE], ignore_index=True)
        D = D[D.n_re > 0]
        g = D.groupby(["market", "tf"], sort=False).apply(lambda x: pd.Series(dict(
            configs=len(x), re_better_sharpe=float((x.sharpe_re > x.sharpe_no).mean()), med_dsharpe=float((x.sharpe_re - x.sharpe_no).median()),
            re_better_total=float((x.total_re > x.total_no).mean()), stop_no_beats_x0=float((x.sharpe_no > x.sharpe_x0).mean()),
            stop_re_beats_x0=float((x.sharpe_re > x.sharpe_x0).mean()), re_lower_dd_than_x0=float((x.maxdd_re < x.maxdd_x0).mean()),
            expo_no=float(x.expo_no.median()), expo_re=float(x.expo_re.median()), expo_x0=float(x.expo_x0.median())))).reset_index()
        g.to_csv(out / "reentry_summary.csv", index=False)
        L.append("\n## Stops with re-entry vs without, and vs X0 (L1, X1..X6; shares of configs)\n")
        L.append(g.to_markdown(index=False, floatfmt=".3f"))
        ge = D.groupby("exit").apply(lambda x: pd.Series(dict(re_better_sharpe=float((x.sharpe_re > x.sharpe_no).mean()),
                                                               stop_re_beats_x0=float((x.sharpe_re > x.sharpe_x0).mean()),
                                                               stop_no_beats_x0=float((x.sharpe_no > x.sharpe_x0).mean())))).reset_index()
        L.append("\n" + ge.to_markdown(index=False, floatfmt=".3f"))
    (out / "r2_tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("written", out / "r2_tables.md")


if __name__ == "__main__":
    main()
