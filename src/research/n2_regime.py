"""N2 (trial T16): regime overlay R1 (rule) / R2 (statistical jump model) on the N1 base portfolio.
Protocol logs/research_n2_regime/N2_PROTOCOL_PREREGISTERED.md. Reuses the verified N1 simulator; the only hook is the regime
multiplier, applied after the N1 corr/vol overlays and before the heat cap. Historical simulation only."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n1_portfolio as N

OUT = N.ROOT / "logs" / "research_n2_regime"
GMIN, LAM, SEED, NRAND = 0.25, 50.0, 20261025, 100
CUR = {"g": None}                 # current regime table (DataFrame day -> gL, gS) or None for the base
LOG = []
_orig = N.apply_overlays


def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def overlays_with_regime(L, w, cfg, wc):
    w = _orig(L, w, {k: v for k, v in cfg.items() if k != "heat"}, wc)
    if CUR["g"] is not None:
        day = pd.DatetimeIndex(L.entry_time.values).floor("D") - pd.Timedelta(days=1)
        g = CUR["g"].reindex(day)
        gl, gs = g.gL.fillna(1.0).values, g.gS.fillna(1.0).values
        s = L.sleeve.values
        w = np.where(np.isin(s, ["A", "B"]), w * gl, np.where(s == "C", w * gs, w))
    if cfg.get("heat"):
        w = _orig(L, w, {"heat": True}, wc)
    return w


N.apply_overlays = overlays_with_regime


# ---------------- BTC daily ----------------
def btc_daily():
    a = pd.read_csv(N.PRE / "BTCUSDT_1h_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"], parse_dates=["timestamp"]).set_index("timestamp")
    b = N.bars1h("BTCUSDT")
    h = pd.concat([a[a.index < "2020-01-01"], b[b.index >= "2020-01-01"]]).sort_index()
    return h.resample("1D", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna().close


def mvol(c):
    r = c.pct_change()
    s = r.rolling(20).std()
    ref = s.expanding(min_periods=365).median()
    return np.minimum(1.0, ref / s).fillna(1.0)


def r1_states(c):
    tr = c.ewm(span=20, adjust=False).mean() - c.ewm(span=50, adjust=False).mean()
    return (tr > 0).astype(int)


def features(c):
    r = np.log(c).diff()
    F = {}
    for hl in (10, 21):
        dd = np.sqrt((np.minimum(r, 0) ** 2).ewm(halflife=hl).mean())
        F[f"dd{hl}"] = dd
        F[f"so{hl}"] = r.ewm(halflife=hl).mean() / dd
    return pd.DataFrame(F), r


def dp_path(X, mu, lam):
    cost = ((X[:, None, :] - mu[None, :, :]) ** 2).sum(-1)
    n = len(X)
    V = np.empty((n, 2)); B = np.zeros((n, 2), dtype=np.int8)
    V[0] = cost[0]
    for t in range(1, n):
        for k in (0, 1):
            stay, sw = V[t - 1, k], V[t - 1, 1 - k] + lam
            B[t, k] = k if stay <= sw else 1 - k
            V[t, k] = cost[t, k] + min(stay, sw)
    s = np.empty(n, dtype=np.int8); s[-1] = int(np.argmin(V[-1]))
    for t in range(n - 1, 0, -1):
        s[t - 1] = B[t, s[t]]
    return s, V, cost


def forward_V(X, mu, lam):
    cost = ((X[:, None, :] - mu[None, :, :]) ** 2).sum(-1)
    V = np.empty((len(X), 2)); V[0] = cost[0]
    for t in range(1, len(X)):
        V[t, 0] = cost[t, 0] + min(V[t - 1, 0], V[t - 1, 1] + lam)
        V[t, 1] = cost[t, 1] + min(V[t - 1, 1], V[t - 1, 0] + lam)
    return V


def kpp(X, rng):
    c0 = X[rng.integers(len(X))]
    d = ((X - c0) ** 2).sum(1)
    c1 = X[rng.choice(len(X), p=d / d.sum())]
    return np.vstack([c0, c1])


def fit_jm(X, seed):
    best = None
    for rs in range(10):
        rng = np.random.default_rng(seed + rs)
        mu = kpp(X, rng)
        for _ in range(20):
            s, V, cost = dp_path(X, mu, LAM)
            new = np.vstack([X[s == k].mean(0) if (s == k).any() else mu[k] for k in (0, 1)])
            if np.allclose(new, mu):
                break
            mu = new
        s, V, cost = dp_path(X, mu, LAM)
        obj = float(cost[np.arange(len(X)), s].sum() + LAM * (np.diff(s) != 0).sum())
        if best is None or obj < best[0]:
            best = (obj, mu.copy(), s.copy(), rs)
    return best


def r2_states(c):
    F, r = features(c)
    days = F.index
    t_start = pd.Timestamp("2017-09-15")
    months = pd.date_range("2018-04-01", "2026-10-01", freq="MS")
    st = pd.Series(np.nan, index=days)
    fits = []
    for ms in months:
        tr = (days >= t_start) & (days < ms)
        Xr = F[tr]
        mean, sd = Xr.mean(), Xr.std(ddof=0)
        Xs = ((F - mean) / sd)
        Xtr = Xs[tr].values
        obj, mu, s, rs = fit_jm(Xtr, SEED)
        bull = int(np.argmax([r[tr].values[s == k].mean() if (s == k).any() else -np.inf for k in (0, 1)]))
        upto = (days >= t_start) & (days < ms + pd.offsets.MonthBegin(1))
        V = forward_V(Xs[upto].values, mu, LAM)
        idx = np.flatnonzero(upto)
        inm = (days[idx] >= ms - pd.Timedelta(days=1)) & (days[idx] < ms + pd.offsets.MonthBegin(1) - pd.Timedelta(days=1))
        # day d's state uses the fit made at the start of the month containing d+1 (an entry on day d+1 reads day d):
        # the fit of month ms covers days ms-1 .. (next month start - 2)
        for j in np.flatnonzero(inm):
            st.iloc[idx[j]] = 1 if int(np.argmin(V[j])) == bull else 0
        fits.append(dict(month=str(ms.date()), obj=obj, restart=rs, bull=bull, mu=mu.tolist(), mean=mean.tolist(), sd=sd.tolist(),
                         n_train=int(tr.sum()), switches_train=int((np.diff(s) != 0).sum())))
    return st, pd.DataFrame(fits)


def gtable(state, mv):
    gL = np.where(state == 1, 1.0, GMIN) * mv
    gS = np.where(state == 1, GMIN, 1.0) * mv
    return pd.DataFrame(dict(gL=gL, gS=gS, state=state, mvol=mv), index=state.index)


def run(Wd, cfg, g, t0, t1, want=False, **kw):
    CUR["g"] = g
    try:
        return N.run_cfg(Wd, cfg, t0, t1, want=want, **kw)
    finally:
        CUR["g"] = None


def main():
    proto = OUT / "N2_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "N2_PROTOCOL_SHA256.txt").read_text().split()[0], "N2 protocol changed"
    n1 = json.loads((N.OUT / "claims_n1.json").read_text())
    base_cfg = n1["final_cfg"] if n1["verdict"] == "N1 PASS" else {}
    report_only = n1["verdict"] != "N1 PASS"
    log("N1 verdict", n1["verdict"], "base", base_cfg, "report_only", report_only)
    c = btc_daily()
    mv = mvol(c)
    s1 = r1_states(c)
    s2, fits = r2_states(c)
    fits.to_csv(OUT / "N2_fits.csv", index=False)
    G = {"R1": gtable(s1, mv), "R2": gtable(s2.dropna().astype(int), mv.reindex(s2.dropna().index))}
    pd.concat({k: v for k, v in G.items()}, axis=1).to_csv(OUT / "N2_states.csv")
    Wd = N.load_world()
    Wd.led_nostop = {s: N.sim(Wd.T[s], Wd.C, stop=False) for s in "ABC"}
    Wd.led_stop = {s: N.sim(Wd.T[s], Wd.C, stop=True) for s in "ABC"}
    Wd.D, Wd.Dcost, _ = N.build_D(Wd.dc, Wd.C)
    rows, monthly, cal, dd = [], {}, {}, {}
    for name, g in (("base", None), ("R1", G["R1"]), ("R2", G["R2"])):
        for wn, (t0, t1) in N.WIN.items():
            r = run(Wd, base_cfg, g, t0, t1, want=(wn == "dev"))
            cal[(name, wn)], dd[(name, wn)] = r["calmar"], r["mtm_dd"]
            if wn == "dev":
                monthly[name] = r.pop("monthly"); r.pop("curve"); r.pop("Em"); L = r.pop("L")
                if name != "base":
                    L.to_parquet(N.DER / f"n2_trades_{name}.parquet", index=False)
            rows.append(dict(variant=name, window=wn, **r))
        log(name, {wn: (round(cal[(name, wn)], 3), round(dd[(name, wn)], 3)) for wn in N.WIN})
    # Q3 random-regime control
    dev_days = (c.index >= pd.Timestamp("2020-01-31")) & (c.index < pd.Timestamp("2025-10-01"))
    rnd = []
    for name in ("R1", "R2"):
        g = G[name]
        sd = g.state.reindex(c.index[dev_days])
        nd = len(sd)
        for i in range(NRAND):
            off = int(np.random.default_rng(SEED + i).integers(30, nd - 30 + 1))
            sh = pd.Series(np.roll(sd.values, off), index=sd.index)
            gr = gtable(sh.astype(int), mv.reindex(sd.index))
            r = run(Wd, base_cfg, gr, *N.WIN["dev"])
            rnd.append(dict(variant=name, i=i, offset=off, calmar=r["calmar"], mtm_dd=r["mtm_dd"]))
        log("random done", name)
    R = pd.DataFrame(rnd); R.to_csv(OUT / "N2_random.csv", index=False)
    # Q4 DSR
    Mx1 = pd.read_csv(N.OUT / "N1_monthly_dev.csv", index_col=0)
    Mx = pd.DataFrame(monthly); Mx.index = Mx.index.astype(str)
    Mx.to_csv(OUT / "N2_monthly_dev.csv")
    srs = [Mx1[k].mean() / Mx1[k].std(ddof=1) for k in Mx1.columns] + [Mx[k].mean() / Mx[k].std(ddof=1) for k in ("R1", "R2")]
    sr_var = float(np.var(srs, ddof=1))
    n_tr = 14 + 5 + n1["n_configs"] + 2
    # Q5 G7
    g7 = {}
    for name, g in (("base", None), ("R1", G["R1"]), ("R2", G["R2"])):
        CUR["g"] = g
        try:
            r, per, bh, _, _ = N.g7(base_cfg)
        finally:
            CUR["g"] = None
        g7[name] = dict(calmar=r["calmar"], cagr=r["cagr"], mtm_dd=r["mtm_dd"])
    log("G7", g7)
    res = {}
    for name in ("R1", "R2"):
        p95 = float(np.percentile(R[R.variant == name].calmar, 95))
        dsr_v, sr, sr0 = N.dsr(pd.Series(Mx[name].values), sr_var, n_tr)
        q = {"Q1_dev_calmar_up_dd_down": cal[(name, "dev")] > cal[("base", "dev")] and dd[(name, "dev")] < dd[("base", "dev")],
             "Q2_P1_P2_calmar_up": cal[(name, "P1")] > cal[("base", "P1")] and cal[(name, "P2")] > cal[("base", "P2")],
             "Q3_random_regime_p95": cal[(name, "dev")] > p95,
             "Q4_DSR>=0.95": dsr_v >= 0.95,
             "Q5_2018_19": g7[name]["calmar"] > g7["base"]["calmar"]}
        res[name] = dict(gates=q, passed=all(q.values()), random_p95=p95, dsr=dsr_v, sr=sr, sr0=sr0,
                         bull_share=float(G[name].state.reindex(c.index[dev_days]).mean()),
                         switches_per_year=float((G[name].state.reindex(c.index[dev_days]).diff().abs() > 0).sum() / (dev_days.sum() / 365.25)))
    passing = [k for k in ("R1", "R2") if res[k]["passed"]]
    chosen = max(passing, key=lambda k: cal[(k, "dev")]) if passing else None
    verdict = "N2 report only (N1 failed)" if report_only else (f"N2 PASS ({chosen})" if chosen else "N2 FAIL")
    # years (full run 2020-02 .. 2026-10)
    yrs = []
    for name, g in (("base", None), ("R1", G["R1"]), ("R2", G["R2"])):
        f = run(Wd, base_cfg, g, "2020-02-01", "2026-10-01", want=True)
        h0 = Wd.grid.get_loc(pd.Timestamp("2020-02-01"))
        eq = pd.Series(f["curve"], index=Wd.grid[h0:h0 + len(f["curve"])])
        for y, gg in eq.groupby(eq.index.year):
            prev = eq[eq.index < gg.index[0]]
            e0 = prev.iloc[-1] if len(prev) else N.E0
            v = np.r_[e0, gg.values]
            yrs.append(dict(variant=name, year=y, ret=float(gg.iloc[-1] / e0 - 1), mtm_dd=float((1 - v / np.maximum.accumulate(v)).max())))
    Y = pd.DataFrame(yrs); Y.to_csv(OUT / "N2_years.csv", index=False)
    pd.DataFrame(rows).to_csv(OUT / "N2_results.csv", index=False)
    claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), n1_claims_sha=sha(N.OUT / "claims_n1.json"), n1_code_sha=sha(Path(N.__file__)),
                  base_cfg=base_cfg, report_only=report_only, calmar={f"{k[0]}|{k[1]}": v for k, v in cal.items()},
                  mtm_dd={f"{k[0]}|{k[1]}": v for k, v in dd.items()}, g7=g7, results=res, chosen=chosen, verdict=verdict, n_trials_dsr=n_tr,
                  sr_var=sr_var, files={f.name: sha(f) for f in sorted(OUT.glob("N2_*.csv"))})
    (OUT / "claims_n2.json").write_text(json.dumps(claims, indent=1, default=float))
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        log(pd.DataFrame(rows).round(4).to_string()); log(Y.pivot(index="year", columns="variant", values="ret").round(4).to_string())
    log(json.dumps({k: v for k, v in claims.items() if k != "files"}, indent=1, default=float))
    (OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
