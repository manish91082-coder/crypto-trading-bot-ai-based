"""NP2 (logs/research_nonprice/NP2_PROTOCOL_PREREGISTERED.md, SHA b6d8d754...): EQ / RIDGE composites of the NP1-confirmed signals.
Stage DV: D in-sample + V filter -> np2_selection.json (H rows are never read). Stage H: the selected configs, once, on 2025-01..2026-09.
Usage: python src/research/nonprice_np2.py DV | H"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nonprice_np1 import COST_RT, OUT, cluster_t, log, sample, trailing_pct  # noqa: E402

SETS = {("1h", "ALL"): {"OI_CHG_1H": -1, "OI_CHG_24H": -1, "FUT_TAKER_1H": -1, "SPOT_TAKER_1H": -1, "DEPTH_IMB1_1H": 1, "DEPTH_IMB5_1H": 1,
                        "CTRL_RET_1H": -1, "CTRL_RET_24H": -1},
        ("4h", "ALL"): {"OI_CHG_24H": -1, "SPOT_TAKER_1H": -1, "DEPTH_IMB1_1H": 1, "DEPTH_IMB5_1H": 1, "CTRL_RET_24H": -1}}
for h in ("1h", "4h"):
    SETS[(h, "NODEPTH")] = {k: v for k, v in SETS[(h, "ALL")].items() if not k.startswith("DEPTH")}
THETAS = [0.15, 0.20, 0.25]
QS = [0.80, 0.90, 0.95]
H0 = pd.Timestamp("2025-01-01")


def d_start(setname):
    return pd.Timestamp("2023-01-01") if setname == "ALL" else pd.Timestamp("2020-09-01")


def per(t, setname):
    return np.where(t < d_start(setname), "-", np.where(t < pd.Timestamp("2024-01-01"), "D", np.where(t < H0, "V", "H")))


def panel(X, h, setname, upto):
    """past-only percentiles of every feature of the set on the sampled rows with t < upto; rows where all are present."""
    S = sample(X, h)
    S = S[S.t < upto]
    feats = SETS[(h, setname)]
    cols = {}
    for f in feats:
        d = S[["t", f]].dropna().reset_index(drop=True)
        cols[f] = pd.Series(trailing_pct(d.t.to_numpy(), d[f].to_numpy()), index=d.t)
    U = pd.DataFrame(cols).dropna() - 0.5
    U = U.join(S.set_index("t")[f"r_{h}"]).dropna()
    U["period"] = per(U.index, setname)
    return U[U.period != "-"]


def configs():
    for (h, s) in SETS:
        for th in THETAS:
            yield (h, s, "EQ", th)
        for q in QS:
            yield (h, s, "RIDGE", q)


def ridge_fit(U, feats):
    D = U[U.period == "D"]
    Xd, y = D[feats].to_numpy(), D.iloc[:, len(feats)].to_numpy()
    n = len(D)
    beta = np.linalg.solve(Xd.T @ Xd + 0.1 * n * np.eye(len(feats)), Xd.T @ y)
    return beta, np.abs(Xd @ beta)


def trades_for(U, h, s, kind, par, frozen=None):
    feats = list(SETS[(h, s)])
    sg = np.array([SETS[(h, s)][f] for f in feats])
    X = U[feats].to_numpy()
    if kind == "EQ":
        score = (X * sg).mean(axis=1)
        side = np.where(score >= par, 1, np.where(score <= -par, -1, 0))
        extra = {}
    else:
        if frozen is None:
            beta, absd = ridge_fit(U, feats)
            thr = float(np.quantile(absd, par))
        else:
            beta, thr = np.array(frozen["beta"]), frozen["thr"]
        pred = X @ beta
        side = np.where(np.abs(pred) >= thr, np.sign(pred), 0)
        extra = {"beta": beta.tolist(), "thr": thr}
    T = U[side != 0].assign(side=side[side != 0])
    T["net"] = (T.side * T[f"r_{h}"] - COST_RT) * 100
    T = T.reset_index().rename(columns={"index": "t"})
    return T[["t", "period", "side", f"r_{h}", "net"]].rename(columns={f"r_{h}": "ret"}), extra


def summ(T, cfg, period):
    g = T[T.period == period]
    mo = g.groupby(g.t.dt.to_period("M")).net.sum()
    return dict(cfg=cfg, period=period, trades=len(g), win=float((g.net > 0).mean()) if len(g) else np.nan,
                mean_net_pct=g.net.mean() if len(g) else np.nan, t_cluster=cluster_t(g) if len(g) > 2 else np.nan, total_pct=g.net.sum(),
                months_pos=int((mo > 0).sum()), months_traded=len(mo), worst_month_pct=float(mo.min()) if len(mo) else np.nan,
                long_mean=g[g.side > 0].net.mean(), short_mean=g[g.side < 0].net.mean())


def stage_dv():
    X = pd.read_parquet(OUT / "np1_features_1h.parquet")
    X = X[X.t < H0]                                         # H rows never read in this stage
    rows, alltr, frozen = [], [], {}
    panels = {k: panel(X, k[0], k[1], H0) for k in SETS}
    for (h, s, kind, par) in configs():
        cfg = f"{h}|{s}|{kind}|{par}"
        T, extra = trades_for(panels[(h, s)], h, s, kind, par)
        frozen[cfg] = extra
        alltr.append(T.assign(cfg=cfg))
        rows += [summ(T, cfg, "D"), summ(T, cfg, "V")]
    S = pd.DataFrame(rows)
    S.to_csv(OUT / "np2_dv_summary.csv", index=False)
    pd.concat(alltr).to_parquet(OUT / "np2_dv_trades.parquet", compression="zstd", index=False)
    d, v = S[S.period == "D"].set_index("cfg"), S[S.period == "V"].set_index("cfg")
    cand = d[(d.mean_net_pct > 0) & (d.t_cluster >= 2.0) & (v.mean_net_pct > 0)].sort_values("t_cluster", ascending=False)
    sel = cand.index[:3].tolist()
    sha = hashlib.sha256((OUT / "np2_dv_summary.csv").read_bytes()).hexdigest()
    (OUT / "np2_selection.json").write_text(json.dumps(dict(selected=sel, frozen={c: frozen[c] for c in sel}, dv_summary_sha256=sha,
                                                            candidates=cand[["mean_net_pct", "t_cluster"]].round(5).reset_index().to_dict("records")), indent=1), encoding="utf-8")
    log(f"NP2 DV: {len(S) // 2} configs; candidates {len(cand)}; selected {sel}")
    log("NP2 DV D/V: " + json.dumps(S[["cfg", "period", "trades", "mean_net_pct", "t_cluster", "months_pos"]].round(4).to_dict("records")))


def stage_h():
    sel = json.loads((OUT / "np2_selection.json").read_text(encoding="utf-8"))
    if not sel["selected"]:
        log("NP2 H: nothing selected, H stays sealed")
        return
    X = pd.read_parquet(OUT / "np1_features_1h.parquet")
    res, alltr, daily_all, mon_all = [], [], [], []
    days = pd.DataFrame({"date": pd.date_range(H0, "2026-09-30", freq="D")})
    for cfg in sel["selected"]:
        h, s, kind, par = cfg.split("|")
        U = panel(X, h, s, pd.Timestamp("2026-10-01"))
        T, _ = trades_for(U, h, s, kind, float(par), sel["frozen"][cfg] if kind == "RIDGE" else None)
        TH = T[T.period == "H"].assign(cfg=cfg)
        alltr.append(TH)
        sm = summ(T, cfg, "H")
        se = sm["mean_net_pct"] / sm["t_cluster"]
        dl = days.merge(TH.assign(date=TH.t.dt.floor("D")).groupby("date").net.sum().reset_index(), on="date", how="left").fillna({"net": 0.0})
        mo = dl.groupby(dl.date.dt.to_period("M")).net.sum()
        y25, y26 = dl[dl.date.dt.year == 2025].net.sum(), dl[dl.date.dt.year == 2026].net.sum()
        sm.update(lb_239=sm["mean_net_pct"] - 2.39 * se, h_months_pos=int((mo > 0).sum()), h_months=len(mo), sum_2025=y25, sum_2026=y26)
        sm["passes"] = bool(sm["mean_net_pct"] > 0 and sm["lb_239"] > 0 and sm["h_months_pos"] >= 13 and y25 > 0 and y26 > 0)
        res.append(sm)
        daily_all.append(dl.assign(cfg=cfg))
        mon_all.append(mo.rename("net_pct").reset_index().assign(cfg=cfg))
    pd.concat(alltr).to_parquet(OUT / "np2_h_trades.parquet", compression="zstd", index=False)
    pd.concat(daily_all).to_csv(OUT / "np2_h_daily.csv", index=False)
    pd.concat(mon_all).to_csv(OUT / "np2_h_monthly.csv", index=False)
    pd.DataFrame(res).to_csv(OUT / "np2_h_summary.csv", index=False)
    log("NP2 H: " + json.dumps(pd.DataFrame(res).round(4).to_dict("records"), default=str))


if __name__ == "__main__":
    {"DV": stage_dv, "H": stage_h}[sys.argv[1]]()
    outs = sorted(f for f in OUT.iterdir() if f.name.startswith("np2_") and f.suffix in (".parquet", ".csv", ".json"))
    (OUT / "NP2_OUTPUT_SHA256.txt").write_text("".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in outs), encoding="utf-8")
