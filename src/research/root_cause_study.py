"""Root-cause study (logs/research_root_cause/ROOT_CAUSE_PROTOCOL_PREREGISTERED.md, locked before results).
Run: python src/research/root_cause_study.py"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
OUT = PROJ / "logs" / "research_root_cause"
CORE10 = json.loads((PROJ / "deploy" / "paper_n1_config.json").read_text())["core10"]
H = {"5m": 1, "15m": 3, "1h": 12, "4h": 48, "1d": 288}
COST = {"C1_fut_maker": 0.0004, "C2_fut_taker": 0.0008, "C3_spot_bnb": 0.0017}
MS = (1, 2, 5)
B0 = pd.Timestamp("2025-10-01")
MAN = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


assert sha(OUT / "ROOT_CAUSE_PROTOCOL_PREREGISTERED.md") == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"


def blocks(coin, h):
    f = PROJ / "data" / "universe_hf" / "5m" / f"{coin}_5m_full.csv.gz"
    if (str(f), ) not in [(m[0],) for m in MAN]:
        MAN.append((str(f.relative_to(PROJ)).replace("\\", "/"), sha(f)))
    d = pd.read_csv(f, usecols=["timestamp", "open", "high", "low", "close"], parse_dates=["timestamp"]).drop_duplicates("timestamp").set_index("timestamp")
    g = pd.date_range("2020-01-01", "2026-09-30 23:55", freq="5min")
    d = d.reindex(g)
    n = len(g) // h
    a = {c: d[c].values[: n * h].reshape(n, h) for c in ("open", "high", "low", "close")}
    t0 = g[: n * h : h]
    ok = ~(np.isnan(a["open"]).any(1) | np.isnan(a["close"]).any(1) | np.isnan(a["high"]).any(1) | np.isnan(a["low"]).any(1))
    return t0, a, ok


def first_touch(a, s, d):
    """gross outcome for TP = +d / SL = -d (SL first if one bar touches both); returns (conservative, optimistic)."""
    e = a["open"][:, :1]
    up = a["high"] / e - 1 >= d
    dn = a["low"] / e - 1 <= -d
    tp = np.where(s[:, None] > 0, up, dn)
    sl = np.where(s[:, None] > 0, dn, up)
    big = a["open"].shape[1] + 1
    it = np.where(tp.any(1), tp.argmax(1), big)
    isl = np.where(sl.any(1), sl.argmax(1), big)
    r_end = s * (a["close"][:, -1] / a["open"][:, 0] - 1)
    cons = np.where((isl <= it) & (isl < big), -d, np.where(it < big, d, r_end))
    opt = np.where((it <= isl) & (it < big), d, np.where(isl < big, -d, r_end))
    return cons, opt


def stats(net, gross_signed, absr, C):
    n = len(net)
    m, sd = float(net.mean()), float(net.std(ddof=1))
    return dict(n=n, mean_net=m, ci95=[m - 1.96 * sd / np.sqrt(n), m + 1.96 * sd / np.sqrt(n)], win=float((net > 0).mean()),
                p_abs_gt_cost=float((absr > C).mean()), p_signed_gt_cost=float((gross_signed > C).mean()))


def main():
    res = dict(protocol_sha256=sha(OUT / "ROOT_CAUSE_PROTOCOL_PREREGISTERED.md"), code_sha256=sha(__file__))
    R2, R3, R4 = [], [], []
    for hn, h in H.items():
        pool = {}
        for coin in CORE10:
            t0, a, ok = blocks(coin, h)
            r = a["close"][:, -1] / a["open"][:, 0] - 1
            rng = np.random.default_rng(2026)
            s = rng.choice(np.array([-1.0, 1.0]), size=len(r))
            prev = np.r_[np.nan, r[:-1]]
            prev_ok = np.r_[False, ok[:-1]]
            per = np.where(t0 >= B0, "B", "A")
            tp = {}
            for C in COST.values():
                for m in MS:
                    tp[(C, m)] = first_touch(a, s, m * C)
            for P in ("A", "B"):
                sel = ok & (per == P)
                pool.setdefault(P, dict(r=[], s=[], prev=[], prev_ok=[], tp={k: ([], []) for k in tp}))
                pool[P]["r"].append(r[sel]); pool[P]["s"].append(s[sel]); pool[P]["prev"].append(prev[sel]); pool[P]["prev_ok"].append(prev_ok[sel])
                for k, (c_, o_) in tp.items():
                    pool[P]["tp"][k][0].append(c_[sel]); pool[P]["tp"][k][1].append(o_[sel])
        for P, z in pool.items():
            r = np.concatenate(z["r"]); s = np.concatenate(z["s"]); pv = np.concatenate(z["prev"]); pok = np.concatenate(z["prev_ok"])
            Er = float(np.abs(r).mean())
            for cn, C in COST.items():
                g = s * r
                R2.append(dict(h=hn, period=P, cost=cn, exit="end", m=None, **stats(g - C, g, np.abs(r), C)))
                for m in MS:
                    cons = np.concatenate(z["tp"][(C, m)][0]); opt = np.concatenate(z["tp"][(C, m)][1])
                    R2.append(dict(h=hn, period=P, cost=cn, exit="tp_sl_cons", m=m, **stats(cons - C, cons, np.abs(r), C)))
                    R2.append(dict(h=hn, period=P, cost=cn, exit="tp_sl_opt", m=m, **stats(opt - C, opt, np.abs(r), C)))
                use = pok & ~np.isnan(pv) & (pv != 0)
                for nm, sg in (("MOM", np.sign(pv[use])), ("REV", -np.sign(pv[use]))):
                    gg = sg * r[use]
                    R3.append(dict(h=hn, period=P, cost=cn, rule=nm, n=int(use.sum()), E_abs_r=Er, p_star=0.5 + C / (2 * Er),
                                   hit=float((gg > 0).mean()), mean_net=float((gg - C).mean())))
                R4.append(dict(h=hn, period=P, cost=cn, E_abs_r=Er, oracle_mean_net=float((np.abs(r) - C).mean())))
        print("done", hn, flush=True)
    res["R2"], res["R3"], res["R4"] = R2, R3, R4
    # ---- R5 regime
    btc = pd.read_csv(PROJ / "data" / "universe_all" / "1d" / "BTCUSDT_1d.csv", parse_dates=["timestamp"]).drop_duplicates("timestamp").set_index("timestamp").close
    MAN.append(("data/universe_all/1d/BTCUSDT_1d.csv", sha(PROJ / "data" / "universe_all" / "1d" / "BTCUSDT_1d.csv")))
    dr = btc.pct_change()
    mo = json.loads((PROJ / "logs" / "eco" / "monthly_outlook" / "MONTHLY_OUTLOOK_RESULTS.json").read_text())
    MAN.append(("logs/eco/monthly_outlook/MONTHLY_OUTLOOK_RESULTS.json", sha(PROJ / "logs" / "eco" / "monthly_outlook" / "MONTHLY_OUTLOOK_RESULTS.json")))
    rows = []
    for w in ("dev", "P3"):
        for k, v in mo[w]["month_list"].items():
            p = pd.Period(k)
            seg = btc[(btc.index >= p.start_time - pd.Timedelta(days=1)) & (btc.index <= p.end_time)]
            mret = seg.iloc[-1] / seg.iloc[0] - 1
            er = abs(mret) / dr[(dr.index >= p.start_time) & (dr.index <= p.end_time)].abs().sum()
            rows.append(dict(month=k, window=w, eco=v, btc=mret, btc_abs=abs(mret), btc_er=er))
    M = pd.DataFrame(rows)
    M.to_csv(OUT / "R5_months.csv", index=False)
    sp = lambda x, y: float(pd.Series(x).rank().corr(pd.Series(y).rank()))
    res["R5"] = dict(n_months=len(M), spearman_eco_vs_btc_abs=sp(M.eco.values, M.btc_abs.values), spearman_eco_vs_btc_er=sp(M.eco.values, M.btc_er.values),
                     spearman_eco_vs_btc_signed=sp(M.eco.values, M.btc.values))
    E = pd.read_parquet(PROJ / "data" / "derived" / "eco" / "e2_daily_series.parquet")
    MAN.append(("data/derived/eco/e2_daily_series.parquet", sha(PROJ / "data" / "derived" / "eco" / "e2_daily_series.parquet")))
    yr = []
    for comp in ("ECO-W2", "N1_alone", "1D_alone_combo"):
        s = E[f"dev|{comp}"].dropna()
        ye = s.groupby(s.index.year).last()
        base = pd.concat([pd.Series([s.iloc[0]], index=[ye.index[0] - 1]), ye])
        for y, v in (base / base.shift(1) - 1).dropna().items():
            yr.append(dict(comp=comp, seg=str(y), ret=float(v)))
        s3 = E[f"P3|{comp}"].dropna()
        yr.append(dict(comp=comp, seg="P3", ret=float(s3.iloc[-1] / s3.iloc[0] - 1)))
    Y = pd.DataFrame(yr)
    bt = {}
    for seg in Y.seg.unique():
        if seg == "P3":
            a_, b_ = pd.Timestamp("2025-09-30"), pd.Timestamp("2026-09-30")
        else:
            a_, b_ = pd.Timestamp(f"{int(seg) - 1}-12-31"), min(pd.Timestamp(f"{seg}-12-31"), pd.Timestamp("2025-09-30"))
        bt[seg] = float(btc.asof(b_) / btc.asof(a_) - 1)
    Y["btc"] = Y.seg.map(bt)
    Y.to_csv(OUT / "R5_years.csv", index=False)
    res["R5"]["years"] = Y.to_dict("records")
    res["R5"]["spearman_year_vs_btc"] = {c: sp(g.ret.values, g.btc.values) for c, g in Y.groupby("comp")}
    # ---- R6
    cl = json.loads((PROJ / "logs" / "eco" / "claims_eco_e2.json").read_text())
    MAN.append(("logs/eco/claims_eco_e2.json", sha(PROJ / "logs" / "eco" / "claims_eco_e2.json")))
    res["R6"] = {c: dict(dev=cl["results"][f"dev|{c}"], P3=cl["results"][f"P3|{c}"], p3_over_dev_cagr=cl["results"][f"P3|{c}"]["cagr"] / cl["results"][f"dev|{c}"]["cagr"])
                 for c in ("ECO-W1", "ECO-W2", "N1_alone", "1D_alone_combo", "1D_alone")}
    # ---- R7
    r7 = {}
    for w in ("dev", "P3"):
        s = E[f"{w}|ECO-W2"].dropna().pct_change().dropna()
        r7[f"eco_{w}"] = dict(days=int(len(s)), share_pos=float((s > 0).mean()), share_neg=float((s < 0).mean()), median_day=float(s.median()))
    fu = pd.read_csv(PROJ / "data" / "futures_um" / "BTCUSDT_funding.csv", parse_dates=["time"]).set_index("time").funding_rate.astype(float)
    MAN.append(("data/futures_um/BTCUSDT_funding.csv", sha(PROJ / "data" / "futures_um" / "BTCUSDT_funding.csv")))
    fd = fu.groupby(fu.index.floor("D")).sum()
    for P, sel in (("A", fd.index < B0), ("B", (fd.index >= B0) & (fd.index < "2026-10-01"))):
        x = fd[sel]
        r7[f"funding_carry_{P}"] = dict(days=int(len(x)), share_pos=float((x > 0).mean()), mean_day_pct=float(x.mean() * 100), sum_pct=float(x.sum() * 100))
    res["R7"] = r7
    # ---- R1 (read from code and records; no computation)
    res["R1"] = dict(truth=dict(fut_maker=0.0002, fut_taker=0.0004, spot=0.001, spot_bnb=0.00075, spot_impact_median=0.0001),
                     assumed=dict(N1_perp=0.00054, N1_spot=0.00085, ECO_fee=json.loads((PROJ / "deploy" / "eco_config.json").read_text())["fee"],
                                  F4_long_fill=0.0025, F4_short_fill=0.0010, F4_stop_slip=0.01),
                     E3_measured_1D_cost_effect_eco_units_month=dict(fees=20.5, stop_slippage=20.4, unexplained_timing=84.6, source="logs/eco/E3_E4_RESULTS.md"))
    pd.DataFrame(MAN, columns=["path", "sha256"]).drop_duplicates().to_csv(OUT / "input_manifest.csv", index=False)
    res["manifest_sha256"] = sha(OUT / "input_manifest.csv")
    pd.DataFrame(R2).to_csv(OUT / "R2_random_entries.csv", index=False)
    pd.DataFrame(R3).to_csv(OUT / "R3_accuracy.csv", index=False)
    f = OUT / "ROOT_CAUSE_RESULTS.json"
    f.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (OUT / "RESULTS_SHA256.txt").write_text(sha(f) + "  ROOT_CAUSE_RESULTS.json\n")
    print("R5", {k: v for k, v in res["R5"].items() if k != "years"})
    print("R6", {k: round(v["p3_over_dev_cagr"], 3) for k, v in res["R6"].items()})
    print("R7", res["R7"])


if __name__ == "__main__":
    main()
