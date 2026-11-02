"""A3: B2-fast 4h meta-label brain (protocol logs/r2_4h_a3/A3_PROTOCOL_PREREGISTERED.md, trial T05). Research only."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_scalein as P

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "r2_4h_a3"
STORE = ROOT / "data" / "derived" / "r2_a2"
A1C = ROOT / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet"
SEED, NSHUF, NRAND, NBOOT = 20261019, 20, 100, 2000
DEV0, DEV1, P1END, P3END = pd.Timestamp("2021-01-01"), pd.Timestamp("2025-10-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2026-10-01")
MIN_NOT = {"BTCUSDT": 50.0, "ETHUSDT": 20.0, "LINKUSDT": 20.0}
H4 = pd.Timedelta(hours=4)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    S = pd.read_parquet(STORE / "feature_store.parquet")
    feats = json.loads((STORE / "feature_list.json").read_text())
    T = pd.read_parquet(A1C)[["signal", "coin", "side", "entry_time", "exit_idx", "net_x1_5", "net_x2", "R_price", "entry_px", "exit_px", "atr"]]
    S = S.merge(T.rename(columns={"side": "side_str"}), on=["signal", "coin", "side_str", "entry_time"], how="left", validate="one_to_one")
    S = S[S.perp_ok].copy()
    S["exit_time"] = S.entry_time + (S.exit_idx + 1) * H4
    S["month"] = S.entry_time.dt.to_period("M").dt.to_timestamp()
    S = S.sort_values(["entry_time", "signal_type", "coin"]).reset_index(drop=True)
    return S, feats


def model():
    return None


def fit_predict(S, feats, shuffle_seed=None):
    rng = np.random.default_rng(shuffle_seed) if shuffle_seed is not None else None
    cat = [feats.index("signal_type")]
    months = pd.date_range(DEV0, P3END - pd.Timedelta(days=1), freq="MS")
    out = []
    for M in months:
        te = S[S.month == M]
        if te.empty:
            continue
        tr = S[(S.entry_time >= "2020-02-01") & (S.exit_time < M - pd.Timedelta(days=1))].sort_values("entry_time")
        if len(tr) < 300:
            continue
        y = tr.label.values.copy()
        if rng is not None:
            g = tr.coin + "|" + tr.month.astype(str)
            for _, ix in tr.groupby(g.values).indices.items():
                y[ix] = rng.permutation(y[ix])
        n_fit = int(len(tr) * 0.8)
        clf = HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=40,
                                             l2_regularization=1.0, early_stopping=False, random_state=SEED, categorical_features=cat)
        clf.fit(tr[feats].values[:n_fit], y[:n_fit])
        iso = IsotonicRegression(out_of_bounds="clip").fit(clf.predict_proba(tr[feats].values[n_fit:])[:, 1], y[n_fit:])
        thr = float(np.median(iso.predict(clf.predict_proba(tr[feats].values[n_fit:])[:, 1])))
        p = iso.predict(clf.predict_proba(te[feats].values)[:, 1])
        out.append(pd.DataFrame(dict(idx=te.index.values, month=M, p=p, thr=thr, take=p >= thr, m=np.clip((p - 0.5) / 0.1, 0.5, 1.5),
                                     n_train=len(tr))))
    return pd.concat(out, ignore_index=True)


def block_boot(df, stat, rng, n=NBOOT):
    keys = df.coin + "|" + df.entry_time.dt.year.astype(str)
    groups = list(df.groupby(keys.values).indices.values())
    vals = []
    for _ in range(n):
        ix = np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        v = stat(df.iloc[ix])
        if v is not None and np.isfinite(v):
            vals.append(v)
    return np.percentile(vals, [2.5, 97.5])


class Paths:
    """per-trade adverse-extreme MTM fraction per 4h bar (k < exit_idx) and the gross exit fraction at k == exit_idx."""
    def __init__(self, S):
        self.p = {}
        bars = {c: P.bars(c, "4h") for c in S.coin.unique()}
        for i, r in S.iterrows():
            b = bars[r.coin]
            e = b.index.get_loc(r.entry_time)
            k = int(r.exit_idx)
            sl = b.iloc[e:e + k + 1]
            s = 1 if r.side == 1 else -1
            adv = (sl.low.values if s > 0 else sl.high.values)
            frac = s * (adv - r.entry_px) / r.entry_px
            frac[-1] = s * (r.exit_px - r.entry_px) / r.entry_px
            self.p[i] = (sl.index.values, frac)


def portfolio(S, take, mult, paths, t0=DEV0, t1=DEV1):
    """take: bool array over S rows; mult: size multiplier array. Returns dict with equity curves."""
    d = S[take & (S.entry_time >= t0) & (S.entry_time < t1)]
    mm = pd.Series(mult, index=S.index)[d.index]
    grid = pd.date_range(t0, t1 - H4, freq="4h")
    entries = {}
    for i in d.index:
        entries.setdefault(d.at[i, "entry_time"], []).append(i)
    E, peak = 8000.0, 8000.0
    open_, mtm, real = [], [], []
    taken = 0
    for t in grid:
        for o in [o for o in open_ if o["end"] <= t]:
            E += o["pnl"]; open_.remove(o)
        for i in entries.get(t, []):
            r = d.loc[i]
            if any(o["coin"] == r.coin for o in open_):
                continue
            if len(open_) >= 6:
                continue
            Rp = r.R_price / r.entry_px
            N = 0.005 * mm[i] * E / (Rp + 0.01 + 0.0009)
            if sum(o["N"] for o in open_) + N > 3 * E:
                continue
            if N < MIN_NOT.get(r.coin, 5.0) or (r.coin == "BTCUSDT" and N / r.entry_px < 0.001):
                continue
            ts, fr = paths.p[i]
            open_.append(dict(coin=r.coin, N=N, pnl=N * r.net_base * Rp, end=r.exit_time, ts=ts, fr=fr, k=0))
            taken += 1
        u = 0.0
        for o in open_:
            j = np.searchsorted(o["ts"], np.datetime64(t))
            if j < len(o["ts"]) and o["ts"][j] == np.datetime64(t):
                u += o["N"] * o["fr"][j]
        mtm.append(E + u); real.append(E)
    for o in open_:
        E += o["pnl"]
    mtm.append(E); real.append(E)
    idx = list(grid) + [t1]
    eq = pd.Series(mtm, index=idx); rq = pd.Series(real, index=idx)
    yrs = (t1 - t0).days / 365.25
    cagr = (eq.iloc[-1] / 8000) ** (1 / yrs) - 1
    dd = float((1 - eq / eq.cummax()).max()); rdd = float((1 - rq / rq.cummax()).max())
    mon = eq.resample("MS").last().pct_change().dropna()
    return dict(final=float(eq.iloc[-1]), cagr=cagr, mtm_dd=dd, real_dd=rdd, calmar=cagr / dd if dd > 0 else np.nan, taken=taken,
                monthly=mon, eq=eq)


def dsr(ret, sr_var, n_trials):
    sr = ret.mean() / ret.std(ddof=1)
    g3, g4 = ret.skew(), ret.kurt() + 3
    gamma = 0.5772156649
    sr0 = np.sqrt(sr_var) * ((1 - gamma) * norm.ppf(1 - 1 / n_trials) + gamma * norm.ppf(1 - 1 / (n_trials * np.e)))
    z = (sr - sr0) * np.sqrt(len(ret) - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return float(norm.cdf(z)), float(sr), float(sr0)


def main():
    proto = OUT / "A3_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "A3_PROTOCOL_SHA256.txt").read_text().split()[0], "A3 protocol changed"
    S, feats = load()
    rng = np.random.default_rng(SEED)
    O = fit_predict(S, feats)
    O.to_parquet(OUT / "oos_predictions.parquet", index=False)
    S["p"] = np.nan; S["take"] = False; S["m"] = 1.0
    S.loc[O.idx, "p"] = O.p.values; S.loc[O.idx, "take"] = O["take"].values; S.loc[O.idx, "m"] = O.m.values
    dev = S[(S.entry_time >= DEV0) & (S.entry_time < DEV1) & S.p.notna()]
    auc = roc_auc_score(dev.label, dev.p)
    auc_ci = block_boot(dev, lambda x: roc_auc_score(x.label, x.p) - 0.5 if x.label.nunique() == 2 else None, rng)
    shuf = []
    for s in range(NSHUF):
        Os = fit_predict(S, feats, shuffle_seed=SEED + s)
        Ss = S.copy(); Ss["take"] = False; Ss["m"] = 1.0; Ss["p"] = np.nan
        Ss.loc[Os.idx, "p"] = Os.p.values; Ss.loc[Os.idx, "take"] = Os["take"].values; Ss.loc[Os.idx, "m"] = Os.m.values
        dv = Ss[(Ss.entry_time >= DEV0) & (Ss.entry_time < DEV1) & Ss.p.notna()]
        shuf.append(dict(seed=SEED + s, auc=roc_auc_score(dv.label, dv.p), _S=Ss))
        print("shuffle", s, round(shuf[-1]["auc"], 4), flush=True)
    sh_p95 = float(np.percentile([x["auc"] for x in shuf], 95))
    pd.DataFrame([{k: v for k, v in x.items() if k != "_S"} for x in shuf]).to_csv(OUT / "shuffled_auc.csv", index=False)
    # G-B, G-D, G-G
    tk = dev[dev["take"]]
    gb = tk.net_base.mean() - dev.net_base.mean()
    def diffstat(col):
        return lambda x: (x[x["take"]][col].mean() - x[col].mean()) if x["take"].any() else None
    gb_ci = block_boot(dev, diffstat("net_base"), rng)
    gb15_ci = block_boot(dev, diffstat("net_x1_5"), rng)
    top = dev[dev.net_base >= dev.net_base.quantile(0.9)]
    take_rate = dev["take"].mean(); tail_share = top["take"].mean()
    # portfolios
    paths = Paths(S)
    allrows = S.p.notna().values
    ai = portfolio(S, (S["take"] & allrows).values, S.m.values, paths)
    base = portfolio(S, allrows, np.ones(len(S)), paths)
    rnd = []
    for i in range(NRAND):
        rr = np.random.default_rng(SEED + i)
        take = np.zeros(len(S), bool); mult = np.ones(len(S))
        for M, g in S[allrows].groupby("month"):
            n_ai = int(g["take"].sum())
            if n_ai == 0:
                continue
            pick = rr.choice(g.index.values, n_ai, replace=False)
            take[pick] = True
            mult[pick] = rr.permutation(g.loc[g["take"], "m"].values)
        rnd.append(portfolio(S, take, mult, paths)["calmar"])
    rnd_p95 = float(np.percentile(rnd, 95))
    per = {}
    for name, a, b in (("P1", DEV0, P1END), ("P2", P1END, DEV1)):
        x = dev[(dev.entry_time >= a) & (dev.entry_time < b)]
        pa = portfolio(S, (S["take"] & allrows).values, S.m.values, paths, a, b)
        pb = portfolio(S, allrows, np.ones(len(S)), paths, a, b)
        per[name] = dict(net_taken=float(x[x["take"]].net_base.mean()), calmar_ai=pa["calmar"], calmar_base=pb["calmar"])
    p3 = S[(S.entry_time >= DEV1) & S.p.notna()]
    p3ai = portfolio(S, (S["take"] & allrows).values, S.m.values, paths, DEV1, P3END)
    p3b = portfolio(S, allrows, np.ones(len(S)), paths, DEV1, P3END)
    # G-H: 1D system
    sl = pd.read_csv(ROOT / "logs" / "strategy_1d_step27_combine" / "sleeves_MAIN_f50.csv", parse_dates=["date"]).set_index("date")
    one_d = (sl[["D1", "H4", "H1"]] / sl[["D1", "H4", "H1"]].iloc[0]).mean(axis=1)
    one_d = one_d[(one_d.index >= DEV0) & (one_d.index < DEV1)]
    r1d = one_d.resample("MS").last().pct_change().dropna()
    rai = ai["monthly"]
    j = pd.concat([rai.rename("ai"), r1d.rename("d1")], axis=1).dropna()
    corr = float(j.ai.corr(j.d1))
    comb = (1 + 0.5 * j.ai + 0.5 * j.d1).cumprod()
    def calm(c):
        yrs = len(c) / 12
        cg = c.iloc[-1] ** (1 / yrs) - 1
        dd = float((1 - c / c.cummax()).max())
        return cg / dd if dd > 0 else np.nan
    cal_comb, cal_ai_m, cal_1d = calm(comb), calm((1 + j.ai).cumprod()), calm((1 + j.d1).cumprod())
    # DSR
    sh_srs = []
    for x in shuf:
        pr = portfolio(x["_S"], (x["_S"]["take"] & x["_S"].p.notna()).values, x["_S"].m.values, paths)["monthly"]
        sh_srs.append(pr.mean() / pr.std(ddof=1))
    dsr_v, sr_ai, sr0 = dsr(rai, float(np.var(sh_srs, ddof=1)), 5)
    gates = {
        "G-A": bool(auc > sh_p95 and auc_ci[0] > 0),
        "G-B": bool(gb_ci[0] > 0 and gb15_ci[0] > 0),
        "G-C": bool(ai["calmar"] > base["calmar"] and ai["calmar"] > rnd_p95),
        "G-D": bool(tail_share >= take_rate),
        "G-E": bool(all(v["net_taken"] > 0 and v["calmar_ai"] > v["calmar_base"] for v in per.values())),
        "G-G": bool(tk.net_x1_5.mean() > 0 and tk.net_x2.mean() > 0),
        "G-H": bool(corr <= 0.70 or cal_comb > max(cal_ai_m, cal_1d)),
        "DSR": bool(dsr_v >= 0.95),
    }
    verdict = "A3 provisional PASS" if all(gates.values()) else "A3 FAIL"
    rows = [dict(gate=k, pass_=v) for k, v in gates.items()]
    pd.DataFrame(rows).to_csv(OUT / "A3_gates.csv", index=False)
    port = pd.DataFrame([dict(name=n, **{k: v for k, v in p.items() if k not in ("monthly", "eq")}) for n, p in
                         (("AI", ai), ("baseline", base), ("AI_P3", p3ai), ("baseline_P3", p3b))])
    port.to_csv(OUT / "A3_portfolio.csv", index=False)
    claims = dict(protocol_sha=sha(proto), store_sha=sha(STORE / "feature_store.parquet"), oos_sha=sha(OUT / "oos_predictions.parquet"),
                  n_dev=int(len(dev)), auc_dev=float(auc), auc_ci_minus_half=[float(x) for x in auc_ci], shuffled_auc_p95=sh_p95,
                  take_rate=float(take_rate), net_all=float(dev.net_base.mean()), net_taken=float(tk.net_base.mean()), gb_diff=float(gb),
                  gb_ci=[float(x) for x in gb_ci], gb15_ci=[float(x) for x in gb15_ci], tail_share=float(tail_share),
                  net_taken_x1_5=float(tk.net_x1_5.mean()), net_taken_x2=float(tk.net_x2.mean()),
                  ai=dict(final=ai["final"], cagr=ai["cagr"], mtm_dd=ai["mtm_dd"], real_dd=ai["real_dd"], calmar=ai["calmar"], taken=ai["taken"]),
                  baseline=dict(final=base["final"], cagr=base["cagr"], mtm_dd=base["mtm_dd"], real_dd=base["real_dd"], calmar=base["calmar"], taken=base["taken"]),
                  random_skip_calmar_p95=rnd_p95, periods=per, corr_1d=corr, calmar_comb=cal_comb, calmar_ai_monthly=cal_ai_m, calmar_1d=cal_1d,
                  dsr=dsr_v, sr_ai_monthly=sr_ai, sr0=sr0, gates=gates, verdict=verdict,
                  p3=dict(auc=float(roc_auc_score(p3.label, p3.p)), net_all=float(p3.net_base.mean()),
                          net_taken=float(p3[p3["take"]].net_base.mean()), ai_calmar=p3ai["calmar"], base_calmar=p3b["calmar"],
                          ai_final=p3ai["final"], base_final=p3b["final"]),
                  deferred=["PBO (needs >=4 configs; A5)", "G-I 2018-19 (once, on the frozen A5 config)"])
    (OUT / "claims_a3.json").write_text(json.dumps(claims, indent=1, default=float))
    print(json.dumps(claims, indent=1, default=float))


if __name__ == "__main__":
    main()
