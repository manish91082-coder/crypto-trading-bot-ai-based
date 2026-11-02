"""EMO-1 stage S (protocol logs/emotion/EMO1_PROTOCOL_PREREGISTERED.md §S; interpretation details logs/emotion/CODE_NOTES.md 1).
Written before any result.
  python src/research/emo1_study.py build      panel from the stage-D zips -> data/emotion/emo1/panel.parquet (+ SHA)
  python src/research/emo1_study.py dev        dev window only -> logs/emotion/EMO1_DEV_REPORT.json (+ SHA file)
  python src/research/emo1_study.py holdout    only after the dev report SHA is recorded; once"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ / "src" / "research"))
RAW = PROJ / "data" / "emotion" / "emo1_raw"
OUT = PROJ / "data" / "emotion" / "emo1"
LOG = PROJ / "logs" / "emotion"
FEE = 0.00054
DEV = (pd.Timestamp("2021-12-01"), pd.Timestamp("2024-12-31 23:59"))
HOLD = (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-09-30 23:59"))
SCORE = ["oi_1d", "retail", "taker_1d", "fund_3d"]
CANDLE = ["wick_1d", "qv_surprise", "rv_change"]
H = pd.Timedelta(hours=1)


def zrows(z):
    with zipfile.ZipFile(z) as f:
        t = f.read(f.namelist()[0]).decode()
    return [l.split(",") for l in t.splitlines() if l and l[0].isdigit()]


def load_metrics(s):
    rows = [r for f in sorted((RAW / "daily" / "metrics" / s).glob("*.zip")) for r in zrows(f)]
    if not rows:
        return None
    d = pd.DataFrame([r[:8] for r in rows], columns=["ts", "sym", "oi", "oiv", "top_acct", "top_pos", "glob_acct", "taker"])
    d.index = pd.to_datetime(d.ts)
    d = d[~d.index.duplicated()].sort_index()
    d = d[["oiv", "top_pos", "glob_acct", "taker"]].apply(pd.to_numeric, errors="coerce")
    return d.where(d > 0)                                                   # CODE_NOTES 1: values <= 0 are missing (OI 0 rows in early files)


def load_kl(s, iv):
    rows = [r[:8] for f in sorted((RAW / "monthly" / "klines" / s / iv).glob("*.zip")) for r in zrows(f)]
    if not rows:
        return None
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v", "ct", "qv"]).astype(float)
    d.index = pd.to_datetime(d.t.astype("int64"), unit="ms")
    return d[~d.index.duplicated()].sort_index()


def load_fund(s):
    rows = [r for f in sorted((RAW / "monthly" / "fundingRate" / s).glob("*.zip")) for r in zrows(f)]
    if not rows:
        return pd.Series(dtype=float)
    x = pd.Series([float(r[2]) for r in rows], index=pd.to_datetime([int(r[0]) for r in rows], unit="ms"))
    return x[~x.index.duplicated()].sort_index()


def last_before(idx, t):
    """position of the last index entry strictly before each t (-1 if none)."""
    return np.searchsorted(idx.values, t.values, side="left") - 1


def window_sum(ts, vals, a, b):
    """sum of vals with a < ts <= b, vectorized."""
    c = np.r_[0.0, np.cumsum(vals)]
    return c[np.searchsorted(ts, b, side="right")] - c[np.searchsorted(ts, a, side="right")]


def symbol_panel(s, grid, btc_d):
    m, k1, kd, fu = load_metrics(s), load_kl(s, "1h"), load_kl(s, "1d"), load_fund(s)
    if m is None or k1 is None or kd is None or len(m) < 300:
        return None
    g = pd.DataFrame(index=grid)
    # liquidity: 30-day median daily quote volume of the days BEFORE t's day (point in time)
    med = kd.qv.rolling(30, min_periods=20).median().shift(1)
    g["liq"] = med.reindex(grid.normalize()).values
    # metrics: last snapshot strictly before t; 1 d / 3 d earlier; taker mean over (t - 1 d, t)
    i0 = last_before(m.index, grid)
    i1 = last_before(m.index, grid - pd.Timedelta(days=1))
    i3 = last_before(m.index, grid - pd.Timedelta(days=3))
    ok = (i0 >= 0) & (i1 >= 0) & (i3 >= 0)
    oiv, gl, tp = m.oiv.values, m.glob_acct.values, m.top_pos.values
    lt = np.log(m.taker.values)
    nan = np.full(len(grid), np.nan)
    g["oi_1d"] = np.where(ok, oiv[i0] / oiv[np.maximum(i1, 0)] - 1, nan)
    g["oi_3d"] = np.where(ok, oiv[i0] / oiv[np.maximum(i3, 0)] - 1, nan)
    g["retail"] = np.where(ok, np.log(gl[i0]), nan)
    g["smart"] = np.where(ok, np.log(tp[i0]) - np.log(gl[i0]), nan)
    ts = m.index.values
    fin = np.isfinite(lt)
    n_tk = window_sum(ts[fin], np.ones(fin.sum()), (grid - pd.Timedelta(days=1)).values, (grid - pd.Timedelta(minutes=1)).values)
    s_tk = window_sum(ts[fin], lt[fin], (grid - pd.Timedelta(days=1)).values, (grid - pd.Timedelta(minutes=1)).values)
    g["taker_1d"] = np.where(n_tk >= 200, s_tk / np.maximum(n_tk, 1), nan)              # >= 200 of 288 five-minute rows
    fts, fv = fu.index.values, fu.values
    nf = window_sum(fts, np.ones(len(fv)), (grid - pd.Timedelta(days=3)).values, grid.values)
    g["fund_3d"] = np.where(nf > 0, window_sum(fts, fv, (grid - pd.Timedelta(days=3)).values, grid.values) / np.maximum(nf, 1), nan)
    # candles: 1 h bars that closed by t (open <= t - 1 h)
    rng = (k1.h - k1.l)
    wick = ((rng - (k1.c - k1.o).abs()) / rng).where(rng > 0)
    lr = np.log(k1.c).diff()
    cols = pd.DataFrame(dict(wick=wick.rolling(24, min_periods=12).mean(), qv24=k1.qv.rolling(24).sum(),
                             qv48=k1.qv.rolling(48).sum(), sd24=lr.rolling(24).std(), sd167=lr.rolling(167).std()))
    j = np.searchsorted(k1.index.values, (grid - H).values, side="right") - 1
    jok = j >= 168
    cv = cols.values[np.maximum(j, 0)]
    g["wick_1d"] = np.where(jok, cv[:, 0], nan)
    g["qv_surprise"] = np.where(jok, cv[:, 1] / (cv[:, 2] - cv[:, 1]) - 1, nan)
    g["rv_change"] = np.where(jok, cv[:, 3] / cv[:, 4] - 1, nan)
    # next-period returns (fills at the 1 h open after t) and funding paid in the holding window
    o = k1.o
    for name, hold in (("ret", 4), ("ret_1d", 24)):
        a, b = o.reindex(grid + H).values, o.reindex(grid + H * (1 + hold)).values
        g[name] = b / a - 1
        g["fund_" + ("next" if hold == 4 else "1d")] = window_sum(fts, fv, (grid + H).values, (grid + H * (1 + hold)).values)
    # 60-day beta to BTC from daily returns of the days before t's day
    dr = kd.c.pct_change()
    jj = pd.concat([dr.rename("x"), btc_d.rename("b")], axis=1).dropna()
    beta = (jj.x.rolling(60, min_periods=40).cov(jj.b) / jj.b.rolling(60, min_periods=40).var()).shift(1)
    g["beta"] = beta.reindex(grid.normalize()).values
    g["sym"] = s
    return g[g.liq >= 50e6].reset_index(names="t")


def build():
    el = sorted(json.loads((RAW / "eligible.json").read_text())["first_eligible_day"])
    grid = pd.date_range(DEV[0], HOLD[1], freq="4h")
    btc_d = load_kl("BTCUSDT", "1d").c.pct_change()
    parts = []
    for i, s in enumerate(el):
        p = symbol_panel(s, grid, btc_d)
        if p is not None and len(p):
            parts.append(p)
        print(f"{i + 1}/{len(el)} {s}: {0 if p is None else len(p)} rows", flush=True)
    P = pd.concat(parts, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    P.to_parquet(OUT / "panel.parquet")
    h = hashlib.sha256((OUT / "panel.parquet").read_bytes()).hexdigest()
    (OUT / "panel_sha256.txt").write_text(h)
    print("panel", len(P), "rows,", P.sym.nunique(), "symbols, sha", h[:12])


def prepare(P, step, cols):
    """list of per-rebalance arrays (fast; also used by the shuffle control)."""
    rcol, fcol, hold = ("ret", "fund_next", 4) if step == "4h" else ("ret_1d", "fund_1d", 24)
    Q = P.dropna(subset=cols + [rcol, fcol, "beta"])
    if step == "1d":
        Q = Q[Q.t.dt.hour == 0]
    out = []
    for t, g in Q.groupby("t"):
        if len(g) >= 10:
            out.append((t, g.sym.values, g[cols].rank(pct=True).mean(axis=1).values, g[rcol].values, g[fcol].values, g.beta.values))
    return out, hold


def run_portfolio(blocks, hold, kb, rng=None):
    """long least crowded 20 %, short most crowded 20 % (0.5 gross each), BTC beta hedge, total gross 1.0; taker fee on turnover."""
    res, prev = [], {}
    for t, syms, sc, r, fn, beta in blocks:
        if rng is not None:
            sc = rng.permutation(sc)
        q = max(1, int(len(sc) * 0.2))
        o = np.argsort(sc, kind="stable")
        w = np.zeros(len(sc)); w[o[:q]] = 0.5 / q; w[o[-q:]] = -0.5 / q
        hedge = -float(np.sum(w * beta))
        gross = np.abs(w).sum() + abs(hedge)
        w, hedge = w / gross, hedge / gross
        rb = kb.get(t + H * (1 + hold), np.nan) / kb.get(t + H, np.nan) - 1
        new = dict(zip(syms, w)); new["__BTC"] = hedge
        turn = sum(abs(new.get(k, 0.0) - prev.get(k, 0.0)) for k in new.keys() | prev.keys())
        res.append((t, float(np.sum(w * r) + hedge * (0.0 if np.isnan(rb) else rb) - np.sum(w * fn) - FEE * turn), len(sc)))
        prev = new
    return pd.DataFrame(res, columns=["t", "r", "n"]).set_index("t")


def daily(r):
    return (1 + r.r).groupby(r.index.normalize()).prod() - 1


def stats(d):
    eq = (1 + d).cumprod()
    dd = float((1 - eq / eq.cummax()).max())
    yrs = len(d) / 365.25
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
    sh = float(d.mean() / d.std(ddof=1) * np.sqrt(365.25))
    return dict(sharpe=sh, cagr=cagr, maxdd=dd, calmar=cagr / dd if dd > 0 else float("nan"), days=len(d))


def block_ci(d, n=2000, block=20, seed=7):
    """stationary bootstrap (mean block 20 days) 95 % CI of the annualized Sharpe."""
    rng, x = np.random.default_rng(seed), d.values
    L, out = len(x), []
    for _ in range(n):
        idx = np.empty(L, dtype=int); i = rng.integers(L)
        for k in range(L):
            idx[k] = i
            i = (i + 1) % L if rng.random() > 1 / block else rng.integers(L)
        y = x[idx]
        out.append(y.mean() / y.std(ddof=1) * np.sqrt(365.25))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def evaluate(win, tag):
    import n1_portfolio as N                                              # the project's DSR (monthly returns), as in E-2
    P = pd.read_parquet(OUT / "panel.parquet")
    P = P[(P.t >= win[0]) & (P.t <= win[1])]
    kb = load_kl("BTCUSDT", "1h").o
    bP, h4 = prepare(P, "4h", SCORE)
    b1, h24 = prepare(P, "1d", SCORE)
    rp, r1 = run_portfolio(bP, h4, kb), run_portfolio(b1, h24, kb)
    dP, d1 = daily(rp), daily(r1)
    eco = pd.read_parquet(PROJ / "data" / "derived" / "eco" / "e2_daily_series.parquet")
    er = pd.concat([eco[c].dropna().pct_change().dropna() for c in eco.columns if c.endswith("|ECO-W2") and not c.startswith("P1|") and not c.startswith("P2|")])
    er = er[~er.index.duplicated()].sort_index()
    j = pd.concat([dP.rename("emo"), er.rename("eco")], axis=1).dropna()
    corr = float(j.corr().iloc[0, 1])
    sP, sE, sM = stats(dP), stats(j.eco), stats(0.8 * j.eco + 0.2 * j.emo)
    lo, hi = block_ci(dP)
    mo = (1 + dP).groupby(dP.index.to_period("M")).prod() - 1
    ds = {str(v): N.dsr(mo, v, 114)[0] for v in (0.01, 0.05, 0.10)}
    rng = np.random.default_rng(11)
    shuf = [stats(daily(run_portfolio(bP, h4, kb, rng)))["sharpe"] for _ in range(200)]
    p95 = float(np.percentile(shuf, 95))
    ic = {}
    for c in CANDLE:
        v = P.dropna(subset=[c, "ret"]).groupby("t")[[c, "ret"]].apply(lambda g: g[c].rank().corr(g.ret.rank()) if len(g) >= 10 else np.nan).dropna()
        ic[c] = dict(mean_ic=float(v.mean()), t_stat=float(v.mean() / v.std() * np.sqrt(len(v))), n=len(v))
    gates = dict(G1=bool(sP["sharpe"] > 0 and lo > 0), G2=bool(corr < 0.3), G3=bool(sM["calmar"] > sE["calmar"]), G4=bool(ds["0.05"] > 0.95),
                 G5=bool(sP["sharpe"] > p95))
    rep = dict(window=tag, window_dates=[str(win[0]), str(win[1])], P=sP, R1_daily=stats(d1), R2_note="R2 (positioning only) = P: the score has no candle term",
               sharpe_ci95=[lo, hi], corr_eco_w2=corr, eco_w2=sE, mix_80_20=sM, dsr_monthly=ds, shuffle_sharpe_p95=p95,
               shuffle_sharpe_median=float(np.median(shuf)), candle_rank_ic=ic, gates=gates, all_pass=all(gates.values()),
               n_rebalances=len(rp), median_symbols=float(rp.n.median()), panel_sha256=(OUT / "panel_sha256.txt").read_text().strip(),
               code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    f = LOG / f"EMO1_{tag.upper()}_REPORT.json"
    f.write_text(json.dumps(rep, indent=1, default=float))
    dP.rename("r").to_csv(LOG / f"EMO1_{tag.upper()}_daily_P.csv")
    rp.to_csv(OUT / f"{tag}_rebalances_P.csv")
    print(json.dumps(rep, indent=1, default=float))
    return f


def main():
    a = sys.argv[1]
    proto = LOG / "EMO1_PROTOCOL_PREREGISTERED.md"
    assert hashlib.sha256(proto.read_bytes()).hexdigest() == (LOG / "EMO1_PROTOCOL_SHA256.txt").read_text().split()[0], "EMO-1 protocol changed"
    if a == "build":
        build()
    elif a == "dev":
        f = evaluate(DEV, "dev")
        (LOG / "EMO1_DEV_REPORT_SHA256.txt").write_text(hashlib.sha256(f.read_bytes()).hexdigest() + "  " + f.name + "\n")
    elif a == "holdout":
        assert (LOG / "EMO1_DEV_REPORT_SHA256.txt").exists(), "the dev report SHA must be recorded first"
        assert not (LOG / "EMO1_HOLDOUT_REPORT.json").exists(), "the holdout was opened already (once only)"
        evaluate(HOLD, "holdout")


if __name__ == "__main__":
    main()
