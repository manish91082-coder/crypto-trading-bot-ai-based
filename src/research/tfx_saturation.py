"""TFX-S saturation measurements S1-S7 (protocol logs/research_tf_edge_map/TFXS_PROTOCOL_PREREGISTERED.md).
Reads the verified TFX trade files; changes nothing in TFX. Usage: python src/research/tfx_saturation.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tf_edge_map as M

OUT = M.OUT
SEED, NB = 20261021, 2000
TFS = {"U1": M.TF_U1, "U2": M.TF_U2, "U2X": M.TF_U2}
EXCL = {"U2X": ("LUNAUSDT", "STRAXUSDT")}
TF_DELTA = {"1m": pd.Timedelta(minutes=1), "5m": pd.Timedelta(minutes=5), "15m": pd.Timedelta(minutes=15), "30m": pd.Timedelta(minutes=30),
            "1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4), "8h": pd.Timedelta(hours=8), "12h": pd.Timedelta(hours=12),
            "1D": pd.Timedelta(days=1), "1W": pd.Timedelta(days=7), "1M": pd.Timedelta(days=30.4375)}
TREND = ["TSMOM", "EMAX", "MACD", "DONCH"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(uni, tf, fi):
    src = "U2" if uni == "U2X" else uni
    files = sorted((M.TR / src / M.DIRN.get(tf, tf)).glob("*.parquet"))
    D = pd.concat([pd.read_parquet(f, filters=[("fam", "==", fi)]) for f in files if f.stem not in EXCL.get(uni, ())], ignore_index=True)
    D["entry_time"] = pd.to_datetime(D.entry_time)
    D["exit_time"] = D.entry_time + D.hold * TF_DELTA[tf]          # CODE_NOTES S-1: bar-count exit time (exact except across data gaps)
    D["month"] = D.entry_time.dt.to_period("M").astype(str)
    D["xmonth"] = D.exit_time.dt.to_period("M").astype(str)
    D["net_taker"] = D.gross - M.C_TAKER - D.fund
    D["net_maker"] = D.gross - M.C_MAKER - D.fund
    D["net_spot"] = D.gross - M.C_SPOT
    D["net_2x"] = D.gross - 2 * M.C_TAKER - D.fund
    D["excess"] = D.gross - D.ctrl
    return D


def mboot(x, blocks, rng, ncell):
    codes, inv = np.unique(blocks, return_inverse=True)
    s = np.bincount(inv, weights=x); c = np.bincount(inv).astype(float)
    W = rng.multinomial(len(codes), np.full(len(codes), 1 / len(codes)), size=NB)
    mb = (W @ s) / np.maximum(W @ c, 1)
    m, se = x.mean(), mb.std(ddof=1)
    z = norm.ppf(1 - 0.05 / max(ncell, 1) / 2)
    return m, np.quantile(mb, .025), np.quantile(mb, .975), m - z * se, m + z * se


def trimmed(x, q=0.05):
    x = np.sort(x); k = int(np.floor(q * len(x)))
    return x[k:len(x) - k].mean() if len(x) - 2 * k > 0 else np.nan


def eligible_months():
    """coins eligible per month: U1 = coin has 5m data in the month; U2/U2X = coin has >= 1 liquid day in the month."""
    import r2_t14_universe as U
    out = {}
    for c in M.CORE10:
        ts = pd.read_csv(M.HF / f"{c}_5m_full.csv.gz", usecols=["timestamp"], parse_dates=["timestamp"]).timestamp
        for m in ts.dt.to_period("M").astype(str).unique():
            out.setdefault(("U1", m), set()).add(c)
    cands = [c for c in U.candidates() if (M.HF / f"{c}_5m_full.csv.gz").exists()]
    for c in cands:
        for m in {pd.Timestamp(d).strftime("%Y-%m") for d in M.liq_days(c)}:
            out.setdefault(("U2", m), set()).add(c)
            if c not in EXCL["U2X"]:
                out.setdefault(("U2X", m), set()).add(c)
    return {k: len(v) for k, v in out.items()}


def main():
    proto = OUT / "TFXS_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "TFXS_PROTOCOL_SHA256.txt").read_text().split()[0], "TFX-S protocol changed"
    ncell_tfx = pd.read_csv(OUT / "TFX_cells.csv").groupby("uni").n_cells_universe.max().to_dict()
    ncell_tfx["U2X"] = int(pd.read_csv(OUT / "TFX_cells_POSTHOC_excl_LUNA_STRAX.csv").query("uni=='U2'").n_cells_universe.max())
    emon = eligible_months()
    dev_months = [str(p) for p in pd.period_range("2020-02", "2025-09", freq="M")]
    rng = np.random.default_rng(SEED)
    cells, years, series = [], [], {}
    for uni in ("U1", "U2", "U2X"):
        for tf in TFS[uni]:
            for fi, fam in enumerate(M.FAM):
                D = load(uni, tf, fi)
                for side, g in D.groupby("side"):
                    sd = "long" if side == 1 else "short"
                    dev = g[g.period < 2]
                    # S5 rows (trend group pooled later from these per-family rows)
                    for y, gy in g.groupby("year"):
                        years.append(dict(uni=uni, tf=tf, family=fam, side=sd, year=int(y), n=len(gy),
                                          sum_net=gy.net_taker.sum(skipna=True), n_net=int(gy.net_taker.notna().sum()), sum_ex=gy.excess.sum(), n_ex=int(gy.excess.notna().sum())))
                    # S6 monthly realized series (all months incl. P3; dev months used for stats)
                    pm = g.dropna(subset=["net_taker"]).groupby("xmonth").net_taker.sum()
                    idx = sorted(set(dev_months) | set(pm.index))
                    den = pd.Series({m: emon.get((uni if uni != "U2X" else "U2X", m), np.nan) for m in idx})
                    ser = (pm.reindex(idx).fillna(0.0) / den).fillna(0.0)
                    series[(uni, tf, fam, sd)] = ser
                    if len(dev) < 30:
                        cells.append(dict(uni=uni, tf=tf, family=fam, side=sd, n_dev=len(dev), reading_month="too few"))
                        continue
                    r = dict(uni=uni, tf=tf, family=fam, side=sd, n_dev=len(dev))
                    pmk = dev.net_taker.notna().values
                    for col in ("net_taker", "net_maker", "net_2x", "excess") + (("net_spot",) if side == 1 else ()):
                        v = dev[col].values; ok = ~np.isnan(v)
                        m, lo, hi, blo, bhi = mboot(v[ok], dev.month.values[ok], rng, ncell_tfx[uni])
                        r.update({f"{col}_mean": m, f"{col}_mlo": lo, f"{col}_mhi": hi, f"{col}_mblo": blo, f"{col}_mbhi": bhi})
                        for pn, pi in (("P1", 0), ("P2", 1), ("P3", 2)):
                            q = g[(g.period == pi)][col]
                            r[f"{col}_{pn}"] = q.mean()
                    ex = dev.excess.dropna().values; nt = dev.net_taker.dropna().values
                    r.update(excess_median=float(np.median(ex)), excess_trim5=trimmed(ex), net_taker_trim5=trimmed(nt),
                             net_taker_median=float(np.median(nt)),
                             top1pct_share=float(np.sort(nt)[::-1][:max(1, int(np.ceil(0.01 * len(nt))))].sum() / nt.sum()) if nt.sum() != 0 else np.nan,
                             breakeven_cost=float((dev.gross - dev.fund).dropna().mean()))
                    lab = []
                    if r["net_taker_mlo"] > 0 and r["net_taker_P1"] > 0 and r["net_taker_P2"] > 0:
                        lab.append("COST-VIABLE-PERP" + ("-STRICT" if r["net_taker_mblo"] > 0 else ""))
                    if side == 1 and r["net_spot_mlo"] > 0 and r["net_spot_P1"] > 0 and r["net_spot_P2"] > 0:
                        lab.append("COST-VIABLE-SPOT" + ("-STRICT" if r["net_spot_mblo"] > 0 else ""))
                    if r["excess_mlo"] > 0:
                        lab.append("TIMING+" + ("-STRICT" if r["excess_mblo"] > 0 else ""))
                    if r["excess_mhi"] < 0:
                        lab.append("TIMING-" + ("-STRICT" if r["excess_mbhi"] < 0 else ""))
                    if r["net_2x_mlo"] > 0 and r["net_2x_P1"] > 0 and r["net_2x_P2"] > 0:
                        lab.append("COST-VIABLE-2X")
                    if r["net_maker_mlo"] > 0 and r["net_maker_P1"] > 0 and r["net_maker_P2"] > 0:
                        lab.append("MAKER-VIABLE")
                    r["reading_month"] = ";".join(lab) if lab else "none"
                    cells.append(r)
                del D
            print(uni, tf, flush=True)
    C = pd.DataFrame(cells)
    # compare with TFX coin-year readings
    old = pd.concat([pd.read_csv(OUT / "TFX_cells.csv"),
                     pd.read_csv(OUT / "TFX_cells_POSTHOC_excl_LUNA_STRAX.csv").query("uni=='U2'").assign(uni="U2X")])
    C = C.merge(old[["uni", "tf", "family", "side", "reading"]].rename(columns={"reading": "reading_coinyear"}), on=["uni", "tf", "family", "side"], how="left")
    C.to_csv(OUT / "S1_S4_cells_monthblock.csv", index=False)
    Y = pd.DataFrame(years); Y.to_csv(OUT / "S5_year_rows.csv", index=False)
    # S5 trend-pooled per year
    d5 = M.resample(M.load5m("BTCUSDT"), "1D").close
    btc = {}
    for y in range(2020, 2027):
        prev = d5[d5.index < f"{y}-01-01"]
        start = prev.iloc[-1] if len(prev) else M.load5m("BTCUSDT").open.iloc[0]
        btc[y] = float(d5[d5.index < f"{y + 1}-01-01"].iloc[-1] / start - 1)
    T = Y[Y.family.isin(TREND) & Y.tf.isin(["30m", "1h", "4h", "8h", "12h", "1D"])].groupby(["uni", "tf", "side", "year"])[["sum_net", "n_net", "sum_ex", "n_ex", "n"]].sum().reset_index()
    T["net_mean"] = T.sum_net / T.n_net; T["ex_mean"] = T.sum_ex / T.n_ex; T["btc_year_ret"] = T.year.map(btc)
    T.to_csv(OUT / "S5_trend_by_year.csv", index=False)
    s5 = []
    for (uni, tf), g in T.groupby(["uni", "tf"]):
        p = g.pivot(index="year", columns="side", values="net_mean").dropna()
        e = g.pivot(index="year", columns="side", values="ex_mean")
        rho = spearmanr(p.index.map(btc), p["long"] - p["short"]).correlation if len(p) >= 4 else np.nan
        s5.append(dict(uni=uni, tf=tf, years=len(p), spearman_btc_vs_long_minus_short=rho,
                       ex_pos_share_long=float((e["long"] > 0).mean()), ex_pos_share_short=float((e["short"] > 0).mean())))
    S5 = pd.DataFrame(s5); S5.to_csv(OUT / "S5_summary.csv", index=False)
    # S6 / S7
    st, mats = [], {}
    for k, ser in series.items():
        dv = ser.reindex(dev_months).fillna(0.0)
        nz = int((dv != 0).sum())
        cum = dv.cumsum(); mdd = float((cum.cummax() - cum).max())
        st.append(dict(uni=k[0], tf=k[1], family=k[2], side=k[3], months_nonzero=nz, mean=dv.mean(), sd=dv.std(ddof=1),
                       sharpe_ann=float(np.sqrt(12) * dv.mean() / dv.std(ddof=1)) if dv.std(ddof=1) > 0 else np.nan, mdd=mdd))
    ST = pd.DataFrame(st); ST.to_csv(OUT / "S6_sleeve_stats.csv", index=False)
    devS = {k: v.reindex(dev_months).fillna(0.0) for k, v in series.items()}

    def neff(keys):
        X = pd.DataFrame({"|".join(k): devS[k] for k in keys})
        R = X.corr().values
        lam = np.clip(np.linalg.eigvalsh(R), 0, None)
        return float(lam.sum() ** 2 / (lam ** 2).sum()), len(keys)

    good = {k for k in devS if (devS[k] != 0).sum() >= 24}
    ne = {}
    for uni in ("U1", "U2", "U2X"):
        ne[f"all_{uni}"] = neff([k for k in good if k[0] == uni])
        ne[f"trend_1h_1D_{uni}"] = neff([k for k in good if k[0] == uni and k[2] in TREND and k[1] in ("1h", "4h", "8h", "12h", "1D")])
    pairs = []
    keys = sorted(good)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if a[0] != b[0] and not (a[0] == "U1" and b[0] == "U2X"):
                continue
            kind = None
            if a[0] == b[0] and a[2] == b[2] and a[3] == b[3] and a[1] != b[1]:
                kind = "a_same_family_side_across_TF"
            elif a[0] == b[0] and a[1] == b[1] and a[2] == b[2] and a[3] != b[3]:
                kind = "b_long_vs_short"
            elif a[0] == b[0] and a[1] == b[1] and a[3] == b[3] and ((a[2] in TREND) != (b[2] in TREND)):
                kind = "c_trend_vs_MR"
            elif {a[0], b[0]} == {"U1", "U2X"} and a[1] == b[1]:
                la, lb = (a, b) if a[0] == "U1" else (b, a)
                if la[2] in TREND and la[3] == "long" and lb[2] == la[2] and lb[3] == "short":
                    kind = "d_U1_trend_long_vs_U2X_trend_short"
            if kind:
                pairs.append(dict(kind=kind, a="|".join(a), b="|".join(b), rho=float(np.corrcoef(devS[a], devS[b])[0, 1])))
    P = pd.DataFrame(pairs); P.to_csv(OUT / "S6_correlations.csv", index=False)
    claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), tfx_cells_sha=sha(OUT / "TFX_cells.csv"),
                  cells_sha=sha(OUT / "S1_S4_cells_monthblock.csv"), s5_sha=sha(OUT / "S5_trend_by_year.csv"), s6_sha=sha(OUT / "S6_sleeve_stats.csv"),
                  corr_sha=sha(OUT / "S6_correlations.csv"), btc_year_ret=btc, n_eff=ne,
                  corr_summary=P.groupby("kind").rho.describe()[["count", "mean", "50%", "min", "max"]].round(3).to_dict("index"),
                  readings_month=C.groupby(["uni", "reading_month"]).size().reset_index().values.tolist())
    (OUT / "claims_tfxs.json").write_text(json.dumps(claims, indent=1, default=str))
    print(json.dumps({k: v for k, v in claims.items() if k != "readings_month"}, indent=1, default=str))


if __name__ == "__main__":
    main()
