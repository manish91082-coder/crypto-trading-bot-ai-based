"""NP1 (logs/research_nonprice/NP1_PROTOCOL_PREREGISTERED.md, SHA 9addc94b...): non-price features vs forward BTC futures returns.
Stage 1 information test (monthly Spearman IC, D then V), Stage 2 quintile trading rule for S1-confirmed features (D info, V gate).
H (2025-01-01 .. 2026-09-30) rows are built into the feature table but never enter Stage 1 / 2 here.
Usage: python src/research/nonprice_np1.py"""
import bisect
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
CL = P / "data/external/binance_public/clean"
OUT = P / "logs/research_nonprice"
FEES = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
COST_RT = 2 * FEES["rules"]["paper_futures_taker_per_side"]
F5 = pd.Timedelta(minutes=5)
FEATS = ["FUND_LVL", "FUND_Z", "PREM_1H", "PREM_Z", "BASIS", "OI_CHG_1H", "OI_CHG_24H", "OI_RET_4H", "TOP_LS_Z", "RETAIL_LS_Z",
         "TOP_MINUS_RETAIL", "TAKER_LS_1H", "FUT_TAKER_1H", "SPOT_TAKER_1H", "DEPTH_IMB1_1H", "DEPTH_IMB5_1H", "CTRL_RET_1H", "CTRL_RET_24H"]
HS = {"1h": 1, "4h": 4, "24h": 24}
DEPTH = {"DEPTH_IMB1_1H", "DEPTH_IMB5_1H"}


def log(msg):
    line = f"{pd.Timestamp.now('UTC'):%Y-%m-%dT%H:%M:%SZ} {msg}"
    print(line, flush=True)
    with open(OUT / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def period(t):
    return np.where(t < pd.Timestamp("2024-01-01"), "D", np.where(t < pd.Timestamp("2025-01-01"), "V", "H"))


def grid5(df, cols, t0, t1):
    """reindex a 5m bar table (open time) to the full grid; index shifted to availability time (open + 5 min)."""
    g = df.set_index("time")[cols].reindex(pd.date_range(t0, t1, freq="5min"))
    g.index = g.index + F5
    return g


def build():
    t0, t1 = pd.Timestamp("2020-07-01"), pd.Timestamp("2026-09-30 23:55")
    T = pd.date_range("2020-09-01", "2026-09-30 23:00", freq="1h").as_unit("ns")
    fut = grid5(pd.read_parquet(CL / "fut5m.parquet"), ["close", "volume", "taker_buy_volume"], t0, t1)
    prem = grid5(pd.read_parquet(CL / "premium5m.parquet"), ["close"], t0, t1)
    sp = pd.read_csv(P / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", usecols=["timestamp", "close", "volume", "taker_buy_base"], parse_dates=["timestamp"])
    sp = grid5(sp.drop_duplicates("timestamp").rename(columns={"timestamp": "time"}), ["close", "volume", "taker_buy_base"], t0, t1)
    dep = grid5(pd.read_parquet(CL / "depth5m.parquet"), ["imb1", "imb5"], t0, t1)
    X = pd.DataFrame(index=T)
    fc = fut.close
    X["px"] = fc.reindex(T).to_numpy()
    for h, n in HS.items():
        X[f"r_{h}"] = fc.reindex(T + pd.Timedelta(hours=n)).to_numpy() / X.px - 1
    # funding: settled at s, usable for t >= s
    fd = pd.read_parquet(CL / "funding.parquet").sort_values("time")
    fd["time"] = fd.time.dt.as_unit("ns")
    fd["z"] = (fd.funding_rate - fd.funding_rate.rolling(90, min_periods=90).mean()) / fd.funding_rate.rolling(90, min_periods=90).std()
    a = pd.merge_asof(pd.DataFrame({"t": T}), fd.rename(columns={"time": "t"})[["t", "funding_rate", "z"]], on="t", direction="backward")
    X["FUND_LVL"], X["FUND_Z"] = a.funding_rate.to_numpy(), a.z.to_numpy()
    p1 = prem.close.rolling(12, min_periods=1).mean()
    X["PREM_1H"] = p1.reindex(T).to_numpy()
    X["PREM_Z"] = ((X.PREM_1H - X.PREM_1H.rolling(720, min_periods=600).mean()) / X.PREM_1H.rolling(720, min_periods=600).std())
    X["BASIS"] = X.px / sp.close.reindex(T).to_numpy() - 1
    # metrics: row at create_time c usable for t >= c + 5 min
    mt = pd.read_parquet(CL / "metrics5m.parquet").sort_values("time")
    mt["avail"] = (mt.time + F5).dt.as_unit("ns")
    mt["taker12"] = mt.sum_taker_long_short_vol_ratio.rolling(12, min_periods=1).mean()
    cols = ["sum_open_interest_value", "sum_toptrader_long_short_ratio", "count_long_short_ratio", "taker12"]

    def m_at(times):
        return pd.merge_asof(pd.DataFrame({"t": times}), mt[["avail"] + cols].rename(columns={"avail": "t"}), on="t", direction="backward")
    m0, m1, m4, m24 = m_at(T), m_at(T - pd.Timedelta(hours=1)), m_at(T - pd.Timedelta(hours=4)), m_at(T - pd.Timedelta(hours=24))
    oi = m0.sum_open_interest_value.to_numpy()
    X["OI_CHG_1H"] = np.log(oi / m1.sum_open_interest_value.to_numpy())
    X["OI_CHG_24H"] = np.log(oi / m24.sum_open_interest_value.to_numpy())
    ret4 = X.px / fc.reindex(T - pd.Timedelta(hours=4)).to_numpy() - 1
    X["OI_RET_4H"] = np.log(oi / m4.sum_open_interest_value.to_numpy()) * np.sign(ret4)
    for nm, c in (("TOP_LS_Z", "sum_toptrader_long_short_ratio"), ("RETAIL_LS_Z", "count_long_short_ratio")):
        s = pd.Series(m0[c].to_numpy(), index=T)
        X[nm] = (s - s.rolling(720, min_periods=600).mean()) / s.rolling(720, min_periods=600).std()
    X["TOP_MINUS_RETAIL"] = X.TOP_LS_Z - X.RETAIL_LS_Z
    X["TAKER_LS_1H"] = np.log(m0.taker12.to_numpy())
    X["FUT_TAKER_1H"] = (fut.taker_buy_volume.rolling(12, min_periods=12).sum() / fut.volume.rolling(12, min_periods=12).sum()).reindex(T).to_numpy() - 0.5
    X["SPOT_TAKER_1H"] = (sp.taker_buy_base.rolling(12, min_periods=12).sum() / sp.volume.rolling(12, min_periods=12).sum()).reindex(T).to_numpy() - 0.5
    X["DEPTH_IMB1_1H"] = dep.imb1.rolling(12, min_periods=1).mean().reindex(T).to_numpy()
    X["DEPTH_IMB5_1H"] = dep.imb5.rolling(12, min_periods=1).mean().reindex(T).to_numpy()
    X["CTRL_RET_1H"] = X.px / fc.reindex(T - pd.Timedelta(hours=1)).to_numpy() - 1
    X["CTRL_RET_24H"] = X.px / fc.reindex(T - pd.Timedelta(hours=24)).to_numpy() - 1
    X = X.replace([np.inf, -np.inf], np.nan)
    X.loc[X.index < pd.Timestamp("2023-01-01"), list(DEPTH)] = np.nan
    X.index.name = "t"
    X = X.reset_index()
    X["period"] = period(X.t)
    return X


def sample(X, h):
    n = HS[h]
    return X[(X.t.dt.hour % n == 0)] if n < 24 else X[X.t.dt.hour == 0]


def monthly_ic(d, f, h):
    d = d[[f, f"r_{h}", "t"]].dropna()
    ics = []
    for _, g in d.groupby(d.t.dt.to_period("M")):
        if len(g) >= 10 and g[f].nunique() > 1:
            ics.append(g[f].rank().corr(g[f"r_{h}"].rank()))
    ics = np.array(ics)
    t = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics))) if len(ics) > 2 else np.nan
    return len(d), len(ics), ics.mean() if len(ics) else np.nan, t, d


def stage1(X, per):
    rows = []
    for h in HS:
        S = sample(X, h)
        S = S[S.period == per]
        for f in FEATS:
            n, nm, mic, t, d = monthly_ic(S, f, h)
            pooled = d[f].rank().corr(d[f"r_{h}"].rank()) if n > 10 else np.nan
            q = pd.qcut(d[f].rank(method="first"), 5, labels=False) if n >= 50 else None
            spread = (d[f"r_{h}"][q == 4].mean() - d[f"r_{h}"][q == 0].mean()) * 100 if q is not None else np.nan
            rows.append(dict(feature=f, h=h, period=per, n=n, months=nm, mean_monthly_ic=mic, t_ic=t, pooled_ic=pooled, q5_minus_q1_pct=spread))
    return pd.DataFrame(rows)


def trailing_pct(t, x, days=90, min_past=30):
    """percentile of x[i] among the sampled values in [t_i - 90 days, t_i) (past only)."""
    out = np.full(len(x), np.nan)
    win, j = [], 0
    for i in range(len(x)):
        while j < i and t[j] < t[i] - np.timedelta64(days, "D"):
            win.pop(bisect.bisect_left(win, x[j])); j += 1
        if len(win) >= min_past:
            out[i] = bisect.bisect_left(win, x[i]) / len(win)
        bisect.insort(win, x[i])
    return out


def cluster_t(trades):
    if len(trades) < 3:
        return np.nan
    m = trades.net.mean()
    wk = trades.assign(w=trades.t.map(lambda d: tuple(d.isocalendar())[:2])).groupby("w").net.agg(["sum", "size"])
    nw = len(wk)
    se = np.sqrt(nw / (nw - 1) * ((wk["sum"] - m * wk["size"]) ** 2).sum()) / len(trades)
    return m / se


def stage2(X, conf, s1D):
    allt, summ, mon = [], [], []
    for r in conf.itertuples():
        f, h = r.feature, r.h
        sign = np.sign(s1D[(s1D.feature == f) & (s1D.h == h)].mean_monthly_ic.iloc[0])
        S = sample(X, h)
        S = S[S.period.isin(["D", "V"])][["t", "period", f, f"r_{h}"]].dropna().reset_index(drop=True)
        pct = trailing_pct(S.t.to_numpy(), S[f].to_numpy())
        side = np.where(pct >= 0.8, sign, np.where(pct <= 0.2, -sign, 0))
        side[np.isnan(pct)] = 0
        T = S[side != 0].assign(side=side[side != 0])
        T["net"] = (T.side * T[f"r_{h}"] - COST_RT) * 100
        T["feature"], T["h"] = f, h
        allt.append(T[["feature", "h", "t", "period", "side", f"r_{h}", "net"]].rename(columns={f"r_{h}": "ret"}))
        for per in ("D", "V"):
            g = T[T.period == per]
            mo = g.groupby(g.t.dt.to_period("M")).net.sum()
            summ.append(dict(feature=f, h=h, period=per, trades=len(g), win=(g.net > 0).mean() if len(g) else np.nan,
                             mean_net_pct=g.net.mean() if len(g) else np.nan, t_cluster=cluster_t(g), total_pct=g.net.sum(),
                             months_pos=int((mo > 0).sum()), months_traded=len(mo), worst_month_pct=mo.min() if len(mo) else np.nan,
                             long_mean=g[g.side > 0].net.mean(), short_mean=g[g.side < 0].net.mean()))
            mon.append(mo.rename("net_pct").reset_index().assign(feature=f, h=h, period=per))
    if not summ:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    S2 = pd.DataFrame(summ)
    v = S2[S2.period == "V"]
    S2["s2_pass"] = False
    S2.loc[v.index, "s2_pass"] = (v.mean_net_pct > 0) & (v.t_cluster >= 2.0) & (v.months_pos >= 7)
    return pd.concat(allt), S2, pd.concat(mon)


def main():
    log("NP1 start")
    X = build()
    X.to_parquet(OUT / "np1_features_1h.parquet", compression="zstd", index=False)
    log(f"features rows {len(X)}; non-NaN per feature (D+V only): " + json.dumps({f: int(X.loc[X.period != 'H', f].notna().sum()) for f in FEATS}))
    s1D = stage1(X, "D")
    s1D.to_csv(OUT / "s1_D.csv", index=False)
    surv = s1D[s1D.t_ic.abs() >= 3.0][["feature", "h", "t_ic", "mean_monthly_ic"]]
    log(f"S1 D survivors (|t_IC|>=3): {len(surv)} of {len(s1D)}: {surv.round(3).to_dict('records')}")
    s1V = stage1(X, "V")
    s1V = s1V.merge(surv[["feature", "h", "t_ic"]].rename(columns={"t_ic": "t_ic_D"}), on=["feature", "h"], how="inner")
    s1V["s1_confirmed"] = (np.sign(s1V.t_ic) == np.sign(s1V.t_ic_D)) & (s1V.t_ic.abs() >= 2.0)
    s1V.to_csv(OUT / "s1_V.csv", index=False)
    conf = s1V[s1V.s1_confirmed]
    log(f"S1 confirmed in V: {len(conf)}: {conf[['feature', 'h', 't_ic_D', 't_ic']].round(3).to_dict('records')}")
    tr, S2, mon = stage2(X, conf, s1D)
    if len(S2):
        tr.to_parquet(OUT / "s2_trades.parquet", compression="zstd", index=False)
        S2.to_csv(OUT / "s2_summary.csv", index=False)
        mon.to_csv(OUT / "s2_monthly.csv", index=False)
        log(f"S2: {S2[S2.period == 'V'][['feature', 'h', 'trades', 'mean_net_pct', 't_cluster', 'months_pos', 's2_pass']].round(3).to_dict('records')}")
    else:
        log("S2: nothing to test (no S1-confirmed feature)")
    outs = sorted(f for f in OUT.iterdir() if f.suffix in (".parquet", ".csv"))
    (OUT / "OUTPUT_SHA256.txt").write_text("".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in outs), encoding="utf-8")
    log("output SHA written")


if __name__ == "__main__":
    main()
