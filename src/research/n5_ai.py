"""N5 (trial T18): AI meta-label filter (logistic L, HGB H, ensemble E) on the base portfolio trades.
Protocol logs/research_n5_ai/N5_PROTOCOL_PREREGISTERED.md. Walk-forward monthly from 2021-01, purge + 1-day embargo, no tuning.
Reuses the N1/N2/N3 pipeline for the portfolio. Historical simulation only."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n1_portfolio as N
import n2_regime as Q
import n3_execution as X

OUT = N.ROOT / "logs" / "research_n5_ai"
FI = N.ROOT / "data" / "futures_info"
SEED, NSH, NRS, NB = 20261027, 20, 100, 2000
LOG = []
FEATS = ["sleeve_c", "tf_c", "fam", "side", "ret1", "ret5", "ret20", "atrp", "rsi", "d_ema20", "d_ema50", "donch", "vol_z", "whale",
         "btc_r1", "btc_r7", "btc_r30", "btc_trend", "btc_sig20", "fund_last", "fund_7d", "oi_ch1", "oi_ch7", "top_ls_pos", "global_ls", "taker_ls"]


def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------- features (all at the signal bar = entry bar - 1) ----------------
def load5(coin):
    return pd.read_csv(N.M.HF / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades"],
                       parse_dates=["timestamp"]).set_index("timestamp").sort_index()


def tf_feature_table(d, tf):
    b = d.resample(N.M.RULE[tf], label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
                                                                   "quote_volume": "sum", "trades": "sum"}).dropna(subset=["open", "high", "low", "close"])
    c = b.close
    A = pd.Series(N.atr14(b), index=b.index)
    dl = c.diff()
    g = dl.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); ls = (-dl.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    hi20, lo20 = b.high.rolling(20).max(), b.low.rolling(20).min()
    wr = b.quote_volume / b.trades.replace(0, np.nan)
    F = pd.DataFrame(dict(ret1=c / c.shift(1) - 1, ret5=c / c.shift(5) - 1, ret20=c / c.shift(20) - 1, atrp=A / c, rsi=100 - 100 / (1 + g / ls),
                          d_ema20=(c - c.ewm(span=20, adjust=False).mean()) / A, d_ema50=(c - c.ewm(span=50, adjust=False).mean()) / A,
                          donch=(c - lo20) / (hi20 - lo20), vol_z=(b.volume - b.volume.rolling(20).mean()) / b.volume.rolling(20).std(),
                          whale=wr / wr.rolling(20).mean()))
    return F


def build_features(T):
    rows = np.full((len(T), len(FEATS)), np.nan)
    col = {f: i for i, f in enumerate(FEATS)}
    rows[:, col["sleeve_c"]] = T.sleeve.map({"A": 0, "B": 1, "C": 2}).values
    rows[:, col["tf_c"]] = T.tf.map(N.TFI).values
    rows[:, col["fam"]] = T.fam.values
    rows[:, col["side"]] = T.side.values
    tfc = ["ret1", "ret5", "ret20", "atrp", "rsi", "d_ema20", "d_ema50", "donch", "vol_z", "whale"]
    for coin, idx in T.groupby("coin").indices.items():
        d5 = load5(coin)
        for tf in sorted(set(T.tf.values[idx])):
            ii = idx[T.tf.values[idx] == tf]
            F = tf_feature_table(d5, tf)
            e = T.e.values[ii]
            assert (F.index[e] == T.entry_time.values[ii]).all()
            for f in tfc:
                rows[ii, col[f]] = F[f].values[e - 1]
        del d5
        fr = N.read_funding(coin)
        et = T.entry_time.values[idx].astype("datetime64[ns]")
        if fr is not None:
            ft, r = fr
            k = np.searchsorted(ft, et, side="left")                    # records strictly before entry
            rows[idx, col["fund_last"]] = np.where(k > 0, r[np.maximum(k - 1, 0)], np.nan)
            k7 = np.searchsorted(ft, et - np.timedelta64(7, "D"), side="left")
            cs = np.r_[0.0, np.cumsum(r)]
            n7 = k - k7
            rows[idx, col["fund_7d"]] = np.where(n7 > 0, (cs[k] - cs[k7]) / np.maximum(n7, 1), np.nan)
        mf = FI / f"{coin}_metrics_daily.csv"
        if mf.exists():
            m = pd.read_csv(mf, parse_dates=["date"]).set_index("date").sort_index()
            m = m.reindex(pd.date_range(m.index.min(), m.index.max(), freq="D"))
            m["oi_ch1"] = m.oi_value / m.oi_value.shift(1) - 1
            m["oi_ch7"] = m.oi_value / m.oi_value.shift(7) - 1
            day = pd.DatetimeIndex(T.entry_time.values[idx]).floor("D") - pd.Timedelta(days=1)   # day d-1 values, usable from day d
            mm = m.reindex(day)
            for f, src in (("oi_ch1", "oi_ch1"), ("oi_ch7", "oi_ch7"), ("top_ls_pos", "top_ls_pos"), ("global_ls", "global_ls"), ("taker_ls", "taker_ls_vol")):
                rows[idx, col[f]] = mm[src].values
    c = Q.btc_daily()
    br = pd.DataFrame(dict(btc_r1=c / c.shift(1) - 1, btc_r7=c / c.shift(7) - 1, btc_r30=c / c.shift(30) - 1, btc_trend=Q.r1_states(c).astype(float),
                           btc_sig20=c.pct_change().rolling(20).std()))
    day = pd.DatetimeIndex(T.entry_time.values).floor("D") - pd.Timedelta(days=1)
    bb = br.reindex(day)
    for f in br.columns:
        rows[:, col[f]] = bb[f].values
    rows[~np.isfinite(rows)] = np.nan                       # CODE_NOTES 1: +-inf (zero denominators) = missing
    return pd.DataFrame(rows, columns=FEATS)


# ---------------- models ----------------
def fit_predict(Xtr, ytr, Xte, kind):
    if kind == "L":
        med = np.nanmedian(Xtr, axis=0); med = np.where(np.isfinite(med), med, 0.0)
        def prep(Z):
            miss = np.isnan(Z).astype(float)
            Z = np.where(np.isnan(Z), med, Z)
            return np.hstack([Z, miss])
        A, B = prep(Xtr), prep(Xte)
        mu, sd = A.mean(0), A.std(0); sd[sd == 0] = 1.0
        m = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000)
        m.fit((A - mu) / sd, ytr)
        return m.predict_proba((B - mu) / sd)[:, 1], m.predict_proba((A - mu) / sd)[:, 1], m
    m = HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0,
                                       early_stopping=False, random_state=20261019)
    m.fit(Xtr, ytr)
    return m.predict_proba(Xte)[:, 1], m.predict_proba(Xtr)[:, 1], m


def walk_forward(T, Xf, y, months, shuffle_seed=None):
    """returns dict kind -> (p array (NaN outside test), take bool array)."""
    p = {k: np.full(len(T), np.nan) for k in "LHE"}
    take = {k: np.zeros(len(T), bool) for k in "LHE"}
    ym = T.entry_time.dt.to_period("M").astype(str).values
    yy = y.copy()
    if shuffle_seed is not None:
        rng = np.random.default_rng(shuffle_seed)
        key = T.coin.values + "|" + ym
        for _, ii in pd.Series(np.arange(len(T))).groupby(key).indices.items():
            yy[ii] = yy[ii][rng.permutation(len(ii))]
    last = None
    for ms in months:
        t0 = pd.Timestamp(ms); t1 = t0 + pd.offsets.MonthBegin(1)
        tr = (T.exit_time < t0 - pd.Timedelta(days=1)).values
        te = ((T.entry_time >= t0) & (T.entry_time < t1)).values
        if not te.any():
            continue
        Xtr, Xte = Xf[tr], Xf[te]
        pL, pLtr, mL = fit_predict(Xtr, yy[tr], Xte, "L")
        pH, pHtr, mH = fit_predict(Xtr, yy[tr], Xte, "H")
        for k, pt, ptr in (("L", pL, pLtr), ("H", pH, pHtr), ("E", (pL + pH) / 2, (pLtr + pHtr) / 2)):
            p[k][te] = pt
            take[k][te] = pt >= np.median(ptr)
        last = (mL, mH, Xtr, yy[tr])
    return p, take, last


def auc_boot(y, p, blocks, rng):
    codes, inv = np.unique(blocks, return_inverse=True)
    out = []
    for _ in range(NB):
        w = rng.multinomial(len(codes), np.full(len(codes), 1 / len(codes)))[inv]
        s = w > 0
        if len(np.unique(y[s])) < 2:
            continue
        out.append(roc_auc_score(y[s], p[s], sample_weight=w[s]))
    return float(np.quantile(out, .025)), float(np.quantile(out, .975))


def mean_boot(x, blocks, rng):
    codes, inv = np.unique(blocks, return_inverse=True)
    s = np.bincount(inv, weights=x); c = np.bincount(inv).astype(float)
    W = rng.multinomial(len(codes), np.full(len(codes), 1 / len(codes)), size=NB)
    mb = (W @ s) / np.maximum(W @ c, 1)
    return float(np.quantile(mb, .025)), float(np.quantile(mb, .975))


def main():
    proto = OUT / "N5_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "N5_PROTOCOL_SHA256.txt").read_text().split()[0], "N5 protocol changed"
    x = X.setup()
    n3 = json.loads((X.OUT / "claims_n3.json").read_text())
    adopted = n3["adopted"] if not x.report_only else []
    maker = (x.fil, x.px) if "X1" in adopted else None
    routing = "X2" in adopted
    log("base", x.base_cfg, "regime", x.gname, "execution", adopted, "report_only", x.report_only)
    guard = "X3" in adopted
    led = X.variant(x, maker, routing, guard=guard)
    T = pd.concat([led[s] for s in "ABC"], ignore_index=True)
    fee_e = T.fee.values - T._reb.values
    T["net"] = T.side * (T.X - T.entry) / T.entry - fee_e - T.fee * T.X / T.entry - np.where(T.nofund, 0.0, T.fsum) + T._freb
    T["exit_time"] = x.Wd.grid[np.minimum(T.E.values, len(x.Wd.grid) - 1)]
    y = (T.net > 0).astype(int).values
    Xf = build_features(T).values
    months = [str(p) for p in pd.period_range("2021-01", "2026-09", freq="M")]
    p, take, last = walk_forward(T, Xf, y, months)
    dev_te = ((T.entry_time >= "2021-01-01") & (T.entry_time < "2025-10-01")).values
    blocks = (T.coin + "_" + T.entry_time.dt.year.astype(str)).values
    rng = np.random.default_rng(SEED)
    # shuffled controls
    sh = []
    for i in range(NSH):
        ps, _, _ = walk_forward(T, Xf, y, months, shuffle_seed=SEED + i)
        sh.append({k: roc_auc_score(y[dev_te], ps[k][dev_te]) for k in "LHE"})
        log("shuffle", i, {k: round(v, 4) for k, v in sh[-1].items()})
    S = pd.DataFrame(sh); S.to_csv(OUT / "N5_shuffled.csv", index=False)
    # portfolios
    def pf(keep, t0, t1):
        return X.runv(x, X.variant(x, maker, routing, keep=keep, guard=guard), t0, t1, want=True)
    base = {w: pf(None, *w_) for w, w_ in (("dev", N.WIN["dev"]), ("P1", ("2021-01-01", "2024-01-01")), ("P2", N.WIN["P2"]), ("P3", N.WIN["P3"]))}
    Mx = {}
    gates_rows, rs_rows = [], []
    allm = T.entry_time.dt.to_period("M").astype(str).values
    for k in "LHE":
        keep = np.ones(len(T), bool)
        tested = ~np.isnan(p[k])
        keep[tested] = take[k][tested]
        res = {w: pf(keep, *w_) for w, w_ in (("dev", N.WIN["dev"]), ("P1", ("2021-01-01", "2024-01-01")), ("P2", N.WIN["P2"]), ("P3", N.WIN["P3"]))}
        Mx[k] = res["dev"]["monthly"]
        auc = roc_auc_score(y[dev_te], p[k][dev_te])
        ci = auc_boot(y[dev_te], p[k][dev_te], blocks[dev_te], rng)
        tk = take[k][dev_te]; nt = T.net.values[dev_te]
        gb = nt[tk].mean() - nt.mean()
        # block bootstrap of (taken mean - all mean)
        codes, inv = np.unique(blocks[dev_te], return_inverse=True)
        s_all = np.bincount(inv, weights=nt); c_all = np.bincount(inv).astype(float)
        s_tk = np.bincount(inv, weights=nt * tk); c_tk = np.bincount(inv, weights=tk.astype(float))
        W = rng.multinomial(len(codes), np.full(len(codes), 1 / len(codes)), size=NB)
        dd = (W @ s_tk) / np.maximum(W @ c_tk, 1) - (W @ s_all) / np.maximum(W @ c_all, 1)
        gb_ci = (float(np.quantile(dd, .025)), float(np.quantile(dd, .975)))
        top = nt >= np.quantile(nt, 0.9)
        tail_share = float(tk[top].mean())
        rate = float(tk.mean())
        # random skip with the same monthly take counts
        rcal = []
        mt = allm[dev_te]
        idx_dev = np.flatnonzero(dev_te)
        for i in range(NRS):
            r_ = np.random.default_rng(SEED + 1000 + i)
            kk = np.ones(len(T), bool)
            for m_ in np.unique(mt):
                ii = idx_dev[mt == m_]
                ntk = int(take[k][ii].sum())
                kk[ii] = False
                kk[r_.choice(ii, ntk, replace=False)] = True
            rcal.append(pf(kk, *N.WIN["dev"])["calmar"])
            rs_rows.append(dict(model=k, i=i, calmar=rcal[-1]))
        rp95 = float(np.percentile(rcal, 95))
        gates_rows.append(dict(model=k, auc=auc, auc_ci_lo=ci[0], auc_ci_hi=ci[1], shuffled_p95=float(np.percentile(S[k], 95)), take_rate=rate,
                               gb=float(gb), gb_ci_lo=gb_ci[0], gb_ci_hi=gb_ci[1], tail_share=tail_share,
                               calmar_dev=res["dev"]["calmar"], base_calmar_dev=base["dev"]["calmar"], random_skip_p95=rp95,
                               calmar_P1=res["P1"]["calmar"], base_P1=base["P1"]["calmar"], calmar_P2=res["P2"]["calmar"], base_P2=base["P2"]["calmar"],
                               calmar_P3=res["P3"]["calmar"], base_P3=base["P3"]["calmar"]))
        log("model", k, {kk_: (round(v, 4) if isinstance(v, float) else v) for kk_, v in gates_rows[-1].items()})
    G = pd.DataFrame(gates_rows)
    pd.DataFrame(rs_rows).to_csv(OUT / "N5_random_skip.csv", index=False)
    # DSR
    n1 = x.n1
    srs = []
    for f in (N.OUT / "N1_monthly_dev.csv", Q.OUT / "N2_monthly_dev.csv", X.OUT / "N3_monthly_dev.csv"):
        M_ = pd.read_csv(f, index_col=0)
        srs += [M_[c].mean() / M_[c].std(ddof=1) for c in M_.columns if c != "base"]
    srs += [Mx[k].mean() / Mx[k].std(ddof=1) for k in "LHE"]
    sr_var = float(np.var(srs, ddof=1))
    n_tr = 14 + 5 + n1["n_configs"] + 2 + (3 + (1 if n3["x3_count"] > 0 else 0)) + 3
    out = {}
    for r in G.itertuples():
        dsr_v, sr, sr0 = N.dsr(pd.Series(Mx[r.model].values), sr_var, n_tr)
        g = {"G-A": r.auc > r.shuffled_p95 and r.auc_ci_lo > 0.5, "G-B": r.gb_ci_lo > 0,
             "G-C": r.calmar_dev > r.base_calmar_dev and r.calmar_dev > r.random_skip_p95, "G-D": r.tail_share >= r.take_rate,
             "G-E": r.calmar_P1 > r.base_P1 and r.calmar_P2 > r.base_P2, "G-F": dsr_v >= 0.95}
        out[r.model] = dict(gates=g, passed=all(g.values()), dsr=dsr_v)
    G["dsr"] = [out[k]["dsr"] for k in G.model]
    G.to_csv(OUT / "N5_gates.csv", index=False)
    passing = [k for k in "LHE" if out[k]["passed"]]
    chosen = max(passing, key=lambda k: float(G[G.model == k].calmar_dev.iloc[0])) if passing else None
    verdict = "N5 report only (N1 failed)" if x.report_only else (f"N5 PASS ({chosen})" if chosen else "N5 FAIL")
    # diagnostics
    mL, mH, Xtr, ytr = last
    from sklearn.inspection import permutation_importance
    pi = permutation_importance(mH, Xtr[-20000:], ytr[-20000:], n_repeats=5, random_state=0, scoring="roc_auc")
    imp = pd.DataFrame(dict(feature=FEATS, perm_importance_auc=pi.importances_mean)).sort_values("perm_importance_auc", ascending=False)
    imp.to_csv(OUT / "N5_importance.csv", index=False)
    coef = pd.DataFrame(dict(feature=FEATS + [f"miss_{f}" for f in FEATS], coef=mL.coef_[0]))
    coef.to_csv(OUT / "N5_logistic_coef.csv", index=False)
    P = T[["sleeve", "coin", "tf", "fam", "side", "entry_time", "e", "net"]].copy()
    P[FEATS] = Xf
    P["y"] = y
    for k in "LHE":
        P[f"p_{k}"] = p[k]; P[f"take_{k}"] = take[k]
    P.to_parquet(OUT / "N5_predictions.parquet", index=False)
    claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), base=dict(cfg=x.base_cfg, regime=x.gname, execution=adopted),
                  report_only=x.report_only, gates=out, chosen=chosen, verdict=verdict, n_trials_dsr=n_tr, sr_var=sr_var,
                  n_trades=int(len(T)), n_dev_test=int(dev_te.sum()), label_rate=float(y[dev_te].mean()),
                  files={f.name: sha(f) for f in sorted(OUT.glob("N5_*")) if f.is_file() and "stdout" not in f.name.lower()})
    (OUT / "claims_n5.json").write_text(json.dumps(claims, indent=1, default=float))
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        log(G.round(4).to_string()); log(imp.head(12).round(5).to_string())
    log(json.dumps({k: v for k, v in claims.items() if k != "files"}, indent=1, default=float))
    (OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
