"""BTC-ALLTF-R2 (2026-10-29): the pre-registered tests and labels (protocol section 6) from the cross-coin accumulators and the
walk-forward series. Nothing here trades; it only reads <RUN>/xcoin/*/acc.npz, per_coin.parquet and <RUN>/wf/*.
Portfolio of a config on a TF = equal weight over the coins of the day (liquid, or holding a position): r_p = SR / DEN.
  Test A (profit):   Newey-West t of mean(r_p) > 0, one-sided p
  Test B (skill):    Newey-West t of mean(SEX / DEN) > 0 (return above the same time-in-market of the coin itself)
  robustness:        compounded r_p > 0 in >= 2 of the 3 sub-periods; with 2x fee the full-period CAGR > 0
  BEATS_BH:          Sharpe(r_p) > Sharpe(EW buy-and-hold) and max DD(r_p) < max DD(EW buy-and-hold)   (descriptive)
  CONFIRMED_PROFIT = q_A <= 0.05 & robustness;  CONFIRMED_SKILL = CONFIRMED_PROFIT & q_B <= 0.05
  BH families: F_A = all S1 configs of all cross-coin jobs together; S2: each job separately; controls: each control's p is
  added alone to F_A (its q is the q it would have had there).
  Walk-forward: per pool x setting the same Test A / B on the OOS series (B against BTC with the procedure's mean signed exposure),
  OOS sub-periods 2021-22 / 2023-24 / 2025-26.09; BH over the 24 pools of the primary setting -> WF_PROFIT / WF_SKILL.
Outputs: <RUN>/tests/*.csv
Usage: python src/btc_alltf_r2/tests_r2.py --run <R2 RUN dir>"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402

X = K.CFG["xcoin"]
T = K.CFG["tests"]
LO = K.ms(X["grid_start"])
SUBS = [(K.ms(a), K.ms(b)) for a, b in X["subperiods"]]
XDIR = ["xcoin_v2"]                                                            # amendment 1: the patched cross-coin outputs


def port_stats(SR, SR2, SEX, DEN, BHS, BHD, day0):
    """one config: its portfolio series and every number of the tests"""
    valid = BHD > 0
    rp = np.where(DEN > 0, SR / np.maximum(DEN, 1), 0.0)[valid]
    rp2 = np.where(DEN > 0, SR2 / np.maximum(DEN, 1), 0.0)[valid]
    ex = np.where(DEN > 0, SEX / np.maximum(DEN, 1), 0.0)[valid]
    bh = (BHS / np.maximum(BHD, 1))[valid]
    days = (np.arange(len(BHD)) + day0)[valid] * K.DAY
    P, P2, PB = K.perf(rp), K.perf(rp2), K.perf(bh)
    tA, pA, lag = K.nw_t(rp)
    tB, pB, _ = K.nw_t(ex)
    sub = []
    for a, b in SUBS:
        m = (days >= a) & (days < b)
        sub.append(float(np.prod(1 + rp[m]) - 1) if m.any() else np.nan)
    return dict(days=int(valid.sum()), total=P["total"], cagr=P["cagr"], sharpe=P["sharpe"], maxdd=P["maxdd"], cagr_2xfee=P2["cagr"],
                tA=tA, pA=pA, tB=tB, pB=pB, nw_lag=lag, sub1=sub[0], sub2=sub[1], sub3=sub[2],
                subs_pos=int(sum(x > 0 for x in sub if np.isfinite(x))), bh_cagr=PB["cagr"], bh_sharpe=PB["sharpe"], bh_maxdd=PB["maxdd"],
                mean_coins=float(DEN[valid].mean()))


def job_table(run, market, tf, family):
    d = Path(run) / XDIR[0] / f"{market}_{tf}_{family}"
    if not (d / "DONE.json").exists():
        return None
    Z = np.load(d / "acc.npz", allow_pickle=False)
    A = {k: Z[k] for k in Z.files}                                            # read every array ONCE (Z[k] re-reads the npz on each access)
    pc = pd.read_parquet(d / "per_coin.parquet")
    br = pc.groupby("k").agg(coins_traded=("coin", "size"), coins_profit=("equity", lambda e: int((e > 1).sum())), trades=("n", "sum"))
    rows = []
    for k, nm in enumerate(A["names"]):
        s = port_stats(A["SR"][k], A["SR2"][k], A["SEX"][k], A["DEN"][k], A["BHS"], A["BHD"], int(A["day0"]))
        s.update(market=market, tf=tf, family=family, k=k, name=str(nm))
        if k in br.index:
            s.update(coins_traded=int(br.loc[k, "coins_traded"]), coins_profit=int(br.loc[k, "coins_profit"]), trades=int(br.loc[k, "trades"]))
        rows.append(s)
    return pd.DataFrame(rows)


def label(D, qA, qB):
    D["qA"], D["qB"] = qA, qB
    robust = (D.subs_pos >= T["subperiods_positive_min"]) & (D.cagr_2xfee > 0)
    D["CONFIRMED_PROFIT"] = (D.qA <= T["alpha_q"]) & robust
    D["CONFIRMED_SKILL"] = D.CONFIRMED_PROFIT & (D.qB <= T["alpha_q"])
    D["BEATS_BH"] = (D.sharpe > D.bh_sharpe) & (D.maxdd < D.bh_maxdd)
    return D


def wf_tests(run):
    w = Path(run) / "wf"
    if not (w / "wf_oos.parquet").exists():
        return None
    O = pd.read_parquet(w / "wf_oos.parquet")
    B = pd.read_parquet(w / "wf_btc_series.parquet")
    subs = [(pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2023-01-01", tz="UTC")),
            (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
            (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp(K.CFG["walk_forward"]["oos_end"], tz="UTC"))]
    rows = []
    for (pool, sname), g in O.groupby(["pool", "setting"], sort=False):
        g = g.sort_values("date")
        r = g.ret.values
        bt = B.set_index("date").loc[g.date, "btc_futures" if pool.startswith("futures") else "btc_spot"].values
        bt = np.nan_to_num(bt)
        e = g.expo.values.mean()
        P, PB = K.perf(r), K.perf(bt)
        tA, pA, _ = K.nw_t(r)
        tB, pB, _ = K.nw_t(r - e * bt)
        sp = [float(np.prod(1 + r[(g.date >= a) & (g.date < b)]) - 1) for a, b in subs]
        rows.append(dict(pool=pool, setting=sname, total=P["total"], cagr=P["cagr"], sharpe=P["sharpe"], maxdd=P["maxdd"], tA=tA, pA=pA,
                         tB=tB, pB=pB, mean_expo=e, sub1=sp[0], sub2=sp[1], sub3=sp[2], subs_pos=sum(x > 0 for x in sp),
                         btc_total=PB["total"], btc_cagr=PB["cagr"], btc_sharpe=PB["sharpe"], btc_maxdd=PB["maxdd"]))
    D = pd.DataFrame(rows)
    pr = D.setting == "primary"
    D["qA"], D["qB"] = np.nan, np.nan
    D.loc[pr, "qA"] = K.bh(D.loc[pr, "pA"].values)
    D.loc[pr, "qB"] = K.bh(D.loc[pr, "pB"].values)
    D["WF_PROFIT"] = pr & (D.qA <= T["alpha_q"]) & (D.subs_pos >= 2)
    D["WF_SKILL"] = D.WF_PROFIT & (D.qB <= T["alpha_q"])
    D["BEATS_BTC_BH"] = (D.sharpe > D.btc_sharpe) & (D.maxdd < D.btc_maxdd)
    return D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--xdir", default="xcoin_v2")
    a = ap.parse_args()
    XDIR[0] = a.xdir
    out = Path(a.run) / ("tests" if a.xdir == "xcoin_v2" else f"tests_{a.xdir}")
    out.mkdir(exist_ok=True)
    jobs = [(m, tf) for m, tfs in X["jobs"].items() for tf in tfs]
    S1 = pd.concat([t for m, tf in jobs if (t := job_table(a.run, m, tf, "S1")) is not None], ignore_index=True)
    S1 = label(S1, K.bh(S1.pA.values), K.bh(S1.pB.values))
    sel = pd.read_csv(K.R2 / "selection_S1.csv")
    S1 = S1.merge(sel[["market", "tf", "name", "sel_rank", "btc_sharpe", "btc_cagr", "btc_maxdd", "n"]].rename(columns={"n": "btc_n"}),
                  on=["market", "tf", "name"], how="left")
    S1.to_csv(out / "tests_S1.csv", index=False)
    s2 = []
    for m, tf in jobs:
        t = job_table(a.run, m, tf, "S2")
        if t is not None:
            s2.append(label(t, K.bh(t.pA.values), K.bh(t.pB.values)))
    if s2:
        pd.concat(s2, ignore_index=True).to_csv(out / "tests_S2.csv", index=False)
    cr = []
    pa, pb = S1.pA.values, S1.pB.values
    for m, tf in jobs:
        t = job_table(a.run, m, tf, "CTRL")
        if t is None:
            continue
        qa = [K.bh(np.r_[pa, x])[-1] for x in t.pA.values]
        qb = [K.bh(np.r_[pb, x])[-1] for x in t.pB.values]
        cr.append(label(t, np.array(qa), np.array(qb)))
    if cr:
        C = pd.concat(cr, ignore_index=True)
        C["ctrl"] = C.name.str.split("|").str[:2].str.join("|")
        C.to_csv(out / "tests_CTRL.csv", index=False)
    W = wf_tests(a.run)
    if W is not None:
        W.to_csv(out / "tests_WF.csv", index=False)
    print(f"tests written to {out}")


if __name__ == "__main__":
    main()
