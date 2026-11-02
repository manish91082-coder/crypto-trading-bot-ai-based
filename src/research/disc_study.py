"""DISC discovery measurements D1-D6 (protocol logs/research_tf_edge_map/DISC_PROTOCOL_PREREGISTERED.md).
Descriptive; reuses the verified TFX helpers. Usage: python src/research/disc_study.py [d1|d2|d3|d4|d5|d6|all]"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tf_edge_map as M

OUT = M.OUT / "disc"
TRD = M.TR.parent / "disc_trades"
SEED = 20261022
EXCL = ("LUNAUSDT", "STRAXUSDT")
TF2 = ["15m", "1h", "4h", "8h", "12h", "1D"]
FAM2 = ["SUPERT", "ICHI", "ADXDI", "STOCH", "KSQZ", "VWAP20", "OBV"]
TREND = ["TSMOM", "EMAX", "MACD", "DONCH"]
TFD = {"15m": pd.Timedelta(minutes=15), "1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4), "8h": pd.Timedelta(hours=8),
       "12h": pd.Timedelta(hours=12), "1D": pd.Timedelta(days=1), "1W": pd.Timedelta(days=7), "5m": pd.Timedelta(minutes=5),
       "30m": pd.Timedelta(minutes=30), "1m": pd.Timedelta(minutes=1), "1M": pd.Timedelta(days=30.4375)}
DEV_MONTHS = [str(p) for p in pd.period_range("2020-02", "2025-09", freq="M")]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def u2x_coins():
    import r2_t14_universe as U
    return [c for c in U.candidates() if (M.HF / f"{c}_5m_full.csv.gz").exists() and c not in EXCL]


def load5mv(coin):
    d = pd.read_csv(M.HF / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close", "volume"], parse_dates=["timestamp"])
    return d.set_index("timestamp").sort_index()


def resv(d, tf):
    if tf == "5m":
        return d
    return d.resample(M.RULE[tf], label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def mboot(x, blocks, rng, ncell, nb=2000):
    codes, inv = np.unique(blocks, return_inverse=True)
    s = np.bincount(inv, weights=x); c = np.bincount(inv).astype(float)
    W = rng.multinomial(len(codes), np.full(len(codes), 1 / len(codes)), size=nb)
    mb = (W @ s) / np.maximum(W @ c, 1)
    m, se = x.mean(), mb.std(ddof=1)
    z = norm.ppf(1 - 0.05 / max(ncell, 1) / 2)
    return m, np.quantile(mb, .025), np.quantile(mb, .975), m - z * se, m + z * se


def ann(series, per_year):
    s = series.fillna(0.0)
    cum = s.cumsum()
    return dict(mean_ann=float(s.mean() * per_year), sharpe=float(np.sqrt(per_year) * s.mean() / s.std(ddof=1)) if s.std(ddof=1) > 0 else np.nan,
                mdd=float((cum.cummax() - cum).max()))


# ======================= D1 carry =======================
def daily_close(coin, kind):
    if kind == "spot":
        d = M.load5m(coin)
    else:
        d = pd.read_csv(M.FUM / f"{coin}_perp_1h.csv.gz", usecols=["timestamp", "open", "high", "low", "close"], parse_dates=["timestamp"]).set_index("timestamp").sort_index()
    return d.close.resample("1D", label="left", closed="left").last().dropna()


def carry_coin(coin, liq):
    s, p = daily_close(coin, "spot"), daily_close(coin, "perp")
    f = pd.read_csv(M.FUM / f"{coin}_funding.csv"); f["time"] = pd.to_datetime(f["time"]); f = f.sort_values("time")
    idx = s.index.intersection(p.index)
    idx = idx[(idx >= M.START) & (idx < M.END)]
    if len(idx) < 30:
        return None
    rs, rp = s.reindex(idx).pct_change(), p.reindex(idx).pct_change()
    # funding received on day d (position held from close d-1 to close d): rates with time in (close d-1, close d] = (d, d+1] in left-labels
    ft, fr = f.time.values, f.funding_rate.values
    cum = np.r_[0.0, np.cumsum(fr)]
    end = (idx + pd.Timedelta(days=1)).values
    start = idx.values
    fund_day = cum[np.searchsorted(ft, end, side="right")] - cum[np.searchsorted(ft, start, side="right")]
    # trailing 7-day mean rate at decision time = start of day d+1 (= close of day d) -> state for day d+1
    tr7 = np.array([fr[(ft > e - np.timedelta64(7, "D")) & (ft <= e)].mean() if ((ft > e - np.timedelta64(7, "D")) & (ft <= e)).any() else np.nan for e in end])
    D = pd.DataFrame(dict(rs=rs.values, rp=rp.values, fund=fund_day, tr7=tr7), index=idx)
    first_f = f.time.iloc[0]
    D["perp_ok"] = D.index >= first_f.floor("D") + pd.Timedelta(days=1)
    D["liq"] = True if liq is None else D.index.isin(liq)
    D["pclose"] = p.reindex(idx).values
    # states: state for day d decided at close of day d-1 (use tr7 of day d-1)
    on_a, on_b, sb = [], [], False
    sa = False
    for k, (ok, lq, t7) in enumerate(zip(D.perp_ok.values, D.liq.values, np.r_[np.nan, D.tr7.values[:-1]])):
        elig = ok and lq
        sa = elig
        if not elig:
            sb = False
        elif np.isfinite(t7):
            sb = True if t7 > 0.0001 else (False if t7 <= 0 else sb)
        on_a.append(sa); on_b.append(sb)
    D["on_a"], D["on_b"] = on_a, on_b
    for v in ("a", "b"):
        on = D[f"on_{v}"].values.astype(bool)
        prev = np.r_[False, on[:-1]]
        sw = (on != prev).astype(float)
        pnl = np.where(on, D.fund.values + D.rs.fillna(0).values - D.rp.fillna(0).values, 0.0) - sw * 0.00139
        D[f"pnl_{v}"] = pnl
    return D


def run_d1():
    out, port, extra = [], {}, []
    for uni, coins in (("U1", M.CORE10), ("U2X", u2x_coins())):
        per = {}
        for c in coins:
            liq = None if uni == "U1" else M.liq_days(c)
            D = carry_coin(c, liq)
            if D is None:
                continue
            per[c] = D
            for v in ("b",):
                on = D[f"on_{v}"].values
                spell = (on & ~np.r_[False, on[:-1]]).cumsum() * on
                adv = []
                for sid in np.unique(spell[spell > 0]):
                    pc = D.pclose.values[spell == sid]
                    adv.append(pc.max() / pc[0] - 1)
                extra.append(dict(uni=uni, coin=c, variant=v, worst_basis_day=float((D.rs - D.rp)[D[f"on_{v}"]].min()) if D[f"on_{v}"].any() else np.nan,
                                  max_perp_adverse=float(max(adv)) if adv else np.nan, p99_perp_adverse=float(np.quantile(adv, .99)) if adv else np.nan,
                                  time_on=float(on.mean())))
        for v in ("a", "b"):
            P = pd.DataFrame({c: D[f"pnl_{v}"] for c, D in per.items()})
            O = pd.DataFrame({c: D[f"on_{v}"] for c, D in per.items()}).fillna(False)
            daily = (P.fillna(0).sum(axis=1) / O.sum(axis=1).replace(0, np.nan)).fillna(0.0)
            port[(uni, v)] = daily
            for pn, sel in (("dev", daily.index < M.DEV_END), ("P1", daily.index < M.P1_END), ("P2", (daily.index >= M.P1_END) & (daily.index < M.DEV_END)), ("P3", daily.index >= M.DEV_END)):
                r = ann(daily[sel], 365)
                out.append(dict(uni=uni, variant=v, period=pn, **r, mean_ann_per_capital=r["mean_ann"] / 2, active_coin_days=int(O[sel].values.sum())))
            for y, g in daily.groupby(daily.index.year):
                out.append(dict(uni=uni, variant=v, period=str(y), **ann(g, 365), mean_ann_per_capital=ann(g, 365)["mean_ann"] / 2))
    R = pd.DataFrame(out); R.to_csv(OUT / "D1_carry.csv", index=False)
    pd.DataFrame(extra).to_csv(OUT / "D1_carry_risk.csv", index=False)
    pd.DataFrame({f"{u}_{v}": s for (u, v), s in port.items()}).to_csv(OUT / "D1_carry_daily.csv")
    return port


# ======================= D2 extra families =======================
def wilder(x, n):
    return x.ewm(alpha=1 / n, adjust=False).mean()


def cond2(b, fam):
    c, h, l, v = b.close, b.high, b.low, b.volume
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    if fam == "SUPERT":
        atr = wilder(tr, 10).values; hl2 = ((h + l) / 2).values; cc = c.values; n = len(cc)
        up, lo = hl2 + 3 * atr, hl2 - 3 * atr
        fu, fl, d = up.copy(), lo.copy(), np.zeros(n)
        for i in range(1, n):
            fu[i] = up[i] if (up[i] < fu[i - 1] or cc[i - 1] > fu[i - 1]) else fu[i - 1]
            fl[i] = lo[i] if (lo[i] > fl[i - 1] or cc[i - 1] < fl[i - 1]) else fl[i - 1]
            d[i] = 1 if cc[i] > fu[i - 1] else (-1 if cc[i] < fl[i - 1] else d[i - 1])
        d = pd.Series(d, index=b.index); d.iloc[:10] = 0
        return d == 1, d == -1, d == -1, d == 1
    if fam == "ICHI":
        t = (h.rolling(9).max() + l.rolling(9).min()) / 2; k = (h.rolling(26).max() + l.rolling(26).min()) / 2
        return t > k, t <= k, t < k, t >= k
    if fam == "ADXDI":
        upm, dnm = h.diff(), -l.diff()
        pdm = pd.Series(np.where((upm > dnm) & (upm > 0), upm, 0.0), index=b.index)
        mdm = pd.Series(np.where((dnm > upm) & (dnm > 0), dnm, 0.0), index=b.index)
        atr = wilder(tr, 14)
        pdi, mdi = 100 * wilder(pdm, 14) / atr, 100 * wilder(mdm, 14) / atr
        adx = wilder(100 * (pdi - mdi).abs() / (pdi + mdi), 14)
        return (adx > 25) & (pdi > mdi), (adx < 20) | (pdi <= mdi), (adx > 25) & (mdi > pdi), (adx < 20) | (mdi <= pdi)
    if fam == "STOCH":
        k = (100 * (c - l.rolling(14).min()) / (h.rolling(14).max() - l.rolling(14).min())).rolling(3).mean()
        return k < 20, k > 50, k > 80, k < 50
    if fam == "KSQZ":
        m = c.rolling(20).mean(); s = c.rolling(20).std()
        bu, bl = m + 2 * s, m - 2 * s
        e = M.ema(c, 20); a = tr.rolling(20).mean()
        ku, kl = e + 1.5 * a, e - 1.5 * a
        sq = (bu < ku) & (bl > kl)
        rel = sq.shift(1, fill_value=False) & ~sq
        return rel & (c > bu), c < m, rel & (c < bl), c > m
    if fam == "VWAP20":
        tp = (h + l + c) / 3
        vw = (tp * v).rolling(20).sum() / v.rolling(20).sum()
        return c > vw, c <= vw, c < vw, c >= vw
    if fam == "OBV":
        obv = (np.sign(c.diff()).fillna(0) * v).cumsum(); e = M.ema(obv, 20)
        return obv > e, obv <= e, obv < e, obv >= e
    raise ValueError(fam)


def trades_generic(coin, b, fams, condf, rng, liq=None, fund=None):
    O = b.open.values; ts = b.index.values; n = len(O)
    fts = pd.DatetimeIndex(ts)
    elig = (fts >= M.START) & (fts < M.END)
    if liq is not None:
        elig &= fts.floor("D").isin(liq)
    per_all = M.period_of(fts)
    pools = {p: np.flatnonzero(elig & (per_all == p)) for p in (0, 1, 2)}
    rows = []
    for fi, fam in enumerate(fams):
        le, lx, se, sx = condf(b, fam)
        for side, (en, ex) in ((1, (le, lx)), (-1, (se, sx))):
            t, u = M.state_trades(en, ex)
            e, x = t + 1, u + 1
            k = x < n; e, x = e[k], x[k]
            k = elig[e] if len(e) else np.array([], bool); e, x = e[k], x[k]
            if not len(e):
                continue
            gross = side * (O[x] - O[e]) / O[e]; h = x - e; per = per_all[e]
            ctrl = np.full(len(e), np.nan)
            for p in (0, 1, 2):
                sel = np.flatnonzero(per == p)
                if not len(sel):
                    continue
                pool = pools[p]; lim = np.searchsorted(pool, n - h[sel])
                r = rng.random((len(sel), M.NCTRL))
                j = pool[np.minimum((r * lim[:, None]).astype(np.int64), np.maximum(lim[:, None] - 1, 0))]
                g = side * (O[np.minimum(j + h[sel][:, None], n - 1)] - O[j]) / O[j]
                g[lim == 0] = np.nan
                ctrl[sel] = g.mean(axis=1)
            if fund is not None:
                ft, cum = fund
                a = np.searchsorted(ft, ts[e], side="right"); z = np.searchsorted(ft, ts[x], side="right")
                fs = np.where(ts[e] >= ft[0], side * (cum[z] - cum[a]), np.nan)
            else:
                fs = np.full(len(e), np.nan)
            rows.append(pd.DataFrame(dict(coin=coin, fam=fam, side=np.int8(side), e=e.astype(np.int32), x=x.astype(np.int32), entry_time=ts[e],
                                          hold=h.astype(np.int32), gross=gross, fund=fs, ctrl=ctrl, period=per, year=fts[e].year.astype(np.int16))))
    return pd.concat(rows, ignore_index=True) if rows else None


def eligible_u1_months():
    out = {}
    for c in M.CORE10:
        for m in pd.read_csv(M.HF / f"{c}_5m_full.csv.gz", usecols=["timestamp"]).timestamp.str[:7].unique():
            out[m] = out.get(m, 0) + 1
    return out


def monthly_series(D, tf, em):
    D = D.dropna(subset=["fund"]).copy()
    D["xm"] = (pd.to_datetime(D.entry_time) + D.hold * TFD[tf]).dt.strftime("%Y-%m")
    D["nt"] = D.gross - M.C_TAKER - D.fund
    s = D.groupby("xm").nt.sum()
    return pd.Series({m: s.get(m, 0.0) / em[m] if m in em else 0.0 for m in DEV_MONTHS})


def cell_rows(D, keycols, rng, ncell, extra=None):
    out = []
    for key, g in D.groupby(keycols):
        dev = g[g.period < 2]
        r = dict(zip(keycols, key if isinstance(key, tuple) else (key,)))
        r.update(extra or {})
        r["n_dev"] = len(dev)
        if len(dev) < 30:
            r["reading_month"] = "too few"; out.append(r); continue
        dev = dev.assign(nt=dev.gross - M.C_TAKER - dev.fund, ex=dev.gross - dev.ctrl, ns=dev.gross - M.C_SPOT,
                         m=pd.to_datetime(dev.entry_time).dt.strftime("%Y-%m"), cy=dev.coin + "_" + dev.year.astype(str))
        lab = []
        for col in ("nt", "ex"):
            v = dev[col].values; ok = ~np.isnan(v)
            m_, lo, hi, blo, bhi = mboot(v[ok], dev.m.values[ok], rng, ncell)
            _, clo, chi, _, _ = mboot(v[ok], dev.cy.values[ok], rng, ncell)
            r.update({f"{col}_mean": m_, f"{col}_mlo": lo, f"{col}_mhi": hi, f"{col}_mblo": blo, f"{col}_cylo": clo, f"{col}_cyhi": chi})
        for pn, pi in (("P1", 0), ("P2", 1), ("P3", 2)):
            q = g[g.period == pi]
            r[f"nt_{pn}"] = (q.gross - M.C_TAKER - q.fund).mean()
        r["ex_median"] = float(np.nanmedian(dev.ex)); r["gross_mean"] = dev.gross.mean()
        if r["nt_mlo"] > 0 and r["nt_P1"] > 0 and r["nt_P2"] > 0:
            lab.append("COST-VIABLE-PERP" + ("-STRICT" if r["nt_mblo"] > 0 else ""))
        if r["ex_mlo"] > 0:
            lab.append("TIMING+")
        if r["ex_mhi"] < 0:
            lab.append("TIMING-")
        r["reading_month"] = ";".join(lab) if lab else "none"
        out.append(r)
    return out


def run_d2():
    rng = np.random.default_rng(SEED)
    em = eligible_u1_months()
    allD = []
    for c in M.CORE10:
        d = load5mv(c); fund = M.funding_cum(c)
        for tf in TF2:
            b = resv(d, tf)
            D = trades_generic(c, b, FAM2, cond2, rng, None, fund)
            if D is not None:
                allD.append(D.assign(tf=tf))
        print("D2", c, flush=True)
    D = pd.concat(allD, ignore_index=True)
    (TRD).mkdir(parents=True, exist_ok=True)
    D.to_parquet(TRD / "D2_trades_U1.parquet", index=False)
    ncell = int((D[D.period < 2].groupby(["tf", "fam", "side"]).size() >= 30).sum())
    C = pd.DataFrame(cell_rows(D, ["tf", "fam", "side"], rng, ncell))
    # monthly series + correlations with the 6 TFX families (same TF, side)
    ser_new = {(tf, fam, s): monthly_series(g, tf, em) for (tf, fam, s), g in D.groupby(["tf", "fam", "side"])}
    ser_old = {}
    for tf in TF2:
        for fi, fam in enumerate(M.FAM):
            files = sorted((M.TR / "U1" / tf).glob("*.parquet"))
            g = pd.concat([pd.read_parquet(f, filters=[("fam", "==", fi)]) for f in files], ignore_index=True)
            for s, gg in g.groupby("side"):
                ser_old[(tf, fam, int(s))] = monthly_series(gg, tf, em)
    cor = []
    for (tf, fam, s), sn in ser_new.items():
        for (tf2, fam2, s2), so in ser_old.items():
            if tf2 == tf and s2 == s:
                cor.append(dict(tf=tf, new=fam, side=s, old=fam2, rho=float(np.corrcoef(sn, so)[0, 1]) if sn.std() > 0 and so.std() > 0 else np.nan))
    COR = pd.DataFrame(cor)
    C = C.merge(COR.groupby(["tf", "new", "side"]).rho.max().rename("max_rho_with_old").reset_index().rename(columns={"new": "fam"}), on=["tf", "fam", "side"], how="left")
    C.to_csv(OUT / "D2_cells.csv", index=False); COR.to_csv(OUT / "D2_correlations.csv", index=False)

    # N_eff with vs without (all U1 TFX sleeves with >= 24 nonzero dev months, every TF, + new)
    def neff(S):
        X = pd.DataFrame(S); R = X.corr().values
        lam = np.clip(np.linalg.eigvalsh(R), 0, None); return float(lam.sum() ** 2 / (lam ** 2).sum()), X.shape[1]
    base = {f"{k}": v for k, v in ser_old.items() if (v != 0).sum() >= 24}
    plus = dict(base); plus.update({f"new{k}": v for k, v in ser_new.items() if (v != 0).sum() >= 24})
    ne = dict(old_TF2=neff(base), old_plus_new_TF2=neff(plus))
    return C, ne, ser_old


# ======================= D3 derivatives rules =======================
def run_d3():
    rng = np.random.default_rng(SEED + 3)
    coins = sorted({p.name.split("_")[0] for p in (M.ROOT / "data" / "futures_info").glob("*_metrics_daily.csv")})
    rows = []
    for c in coins:
        p = pd.read_csv(M.FUM / f"{c}_perp_1h.csv.gz", usecols=["timestamp", "open", "close"], parse_dates=["timestamp"]).set_index("timestamp").sort_index()
        db = p.resample("1D", label="left", closed="left").agg({"open": "first", "close": "last"}).dropna()
        met = pd.read_csv(M.ROOT / "data" / "futures_info" / f"{c}_metrics_daily.csv", parse_dates=["date"]).set_index("date")
        pr = pd.read_csv(M.ROOT / "data" / "futures_info" / f"{c}_premium_1d.csv", parse_dates=["timestamp"]).set_index("timestamp")
        f = pd.read_csv(M.FUM / f"{c}_funding.csv"); f["time"] = pd.to_datetime(f["time"]); f = f.sort_values("time")
        fd = f.set_index("time").funding_rate.resample("1D", label="left", closed="left").mean()
        X = pd.DataFrame(index=db.index)
        X["f3"] = fd.reindex(X.index).rolling(3, min_periods=3).mean()
        X["gls"] = met.global_ls.reindex(X.index); X["tls"] = met.top_ls_pos.reindex(X.index)
        X["prem"] = pr.prem_close.reindex(X.index)
        X["r7"] = db.close / db.close.shift(7) - 1; X["oi7"] = met.oi_value.reindex(X.index) / met.oi_value.reindex(X.index).shift(7) - 1

        def pct(s):
            return s.rolling(365, min_periods=180).apply(lambda w: (w[:-1] < w[-1]).mean() + 0.5 * (w[:-1] == w[-1]).mean() if np.isfinite(w[-1]) else np.nan, raw=True)
        sig = {}
        for name, col in (("FUNDX", "f3"), ("LSCON", "gls"), ("TOPLS", "tls"), ("PREMX", "prem")):
            q = pct(X[col])
            sig[name] = (q <= 0.10, q >= 0.90)
        sig["OITR"] = ((X.r7 > 0) & (X.oi7 > 0), (X.r7 < 0) & (X.oi7 < 0))
        O = db.open.values; ts = db.index.values; n = len(O); fts = pd.DatetimeIndex(ts)
        elig = (fts >= M.START) & (fts < M.END); per_all = M.period_of(fts)
        ft, cum = f.time.values, np.r_[0.0, np.cumsum(f.funding_rate.values)]
        for name, (lg, sh) in sig.items():
            for side, s_ in ((1, lg), (-1, sh)):
                s_ = s_.fillna(False).values
                last_exit, es = -1, []
                for t in np.flatnonzero(s_):
                    e = t + 1
                    if e <= last_exit or e + 5 >= n or not elig[e]:
                        continue
                    es.append(e); last_exit = e + 5
                if not es:
                    continue
                e = np.array(es); x = e + 5
                gross = side * (O[x] - O[e]) / O[e]
                a_ = np.searchsorted(ft, ts[e], side="right"); z_ = np.searchsorted(ft, ts[x], side="right")
                fs = side * (cum[z_] - cum[a_])
                per = per_all[e]; ctrl = np.full(len(e), np.nan)
                for pp in (0, 1, 2):
                    sel = np.flatnonzero(per == pp)
                    pool = np.flatnonzero(elig & (per_all == pp) & (np.arange(n) + 5 < n))
                    if len(sel) and len(pool):
                        j = pool[rng.integers(0, len(pool), (len(sel), 20))]
                        ctrl[sel] = (side * (O[j + 5] - O[j]) / O[j]).mean(axis=1)
                rows.append(pd.DataFrame(dict(coin=c, rule=name, side=side, e=e, x=x, entry_time=ts[e], hold=5, gross=gross, fund=fs, ctrl=ctrl,
                                              period=per, year=fts[e].year)))
        print("D3", c, flush=True)
    D = pd.concat(rows, ignore_index=True); D.to_parquet(TRD / "D3_trades.parquet", index=False)
    ncell = int((D[D.period < 2].groupby(["rule", "side"]).size() >= 30).sum())
    C = pd.DataFrame(cell_rows(D, ["rule", "side"], rng, ncell)); C.to_csv(OUT / "D3_cells.csv", index=False)
    return C


# ======================= D4 cross-sectional momentum =======================
def run_d4(ser_trend_long_u1):
    coins = u2x_coins()
    liq = {c: M.liq_days(c) for c in coins}
    out, mser = [], {}
    rs = {tf: ({}, {}) for tf in ("4h", "8h", "1D")}
    for c in coins:                                      # one coin in memory at a time
        d = M.load5m(c)
        for tf in rs:
            b = M.resample(d, tf); rs[tf][0][c] = b.open; rs[tf][1][c] = b.close
        del d
    for tf in ("4h", "8h", "1D"):
        Op = pd.DataFrame(rs[tf][0]); Cl = pd.DataFrame(rs[tf][1])
        idx = Op.index; Op = Op.reindex(idx); Cl = Cl.reindex(idx)
        L = pd.DataFrame({c: idx.floor("D").isin(liq[c]) for c in coins}, index=idx)
        hist = Cl.notna().cumsum()
        mom = Cl / Cl.shift(20) - 1
        fund = {c: M.funding_cum(c) for c in coins}
        recs, prevw = [], pd.Series(0.0, index=coins)
        start = int(np.searchsorted(idx, M.START))
        for t in range(start, len(idx) - 6, 5):
            el = L.iloc[t] & (hist.iloc[t] >= 25) & mom.iloc[t].notna() & Op.iloc[t + 1].notna() & Op.iloc[t + 6].notna()
            m_ = mom.iloc[t][el]
            if len(m_) < 10:
                continue
            q = len(m_) // 5
            lg, sh = m_.sort_values().index[-q:], m_.sort_values().index[:q]
            r = Op.iloc[t + 6] / Op.iloc[t + 1] - 1
            t0, t1 = idx[t + 1].to_datetime64(), idx[t + 6].to_datetime64()

            def fsum(cs, sd):
                v = []
                for c in cs:
                    ft, cum = fund[c]
                    v.append(sd * (cum[np.searchsorted(ft, t1, side="right")] - cum[np.searchsorted(ft, t0, side="right")]) if t0 >= ft[0] else 0.0)
                return float(np.mean(v))
            w = pd.Series(0.0, index=coins); w[lg] = 1 / len(lg); w[sh] = -1 / len(sh)
            turn = float((w - prevw).abs().sum()); prevw = w
            ret = r[lg].mean() - r[sh].mean() - fsum(lg, 1) - fsum(sh, -1) - 0.00054 * turn
            recs.append(dict(tf=tf, t=idx[t + 6], ret=ret, long=r[lg].mean(), short=-r[sh].mean(), turnover=turn, n=len(m_)))
        R = pd.DataFrame(recs)
        R["m"] = pd.to_datetime(R.t).dt.strftime("%Y-%m")
        ms = R.groupby("m").ret.sum().reindex(DEV_MONTHS).fillna(0.0)
        mser[tf] = ms
        R.to_csv(OUT / f"D4_periods_{tf}.csv", index=False)
        for pn, sel in (("dev", R.t < M.DEV_END), ("P1", R.t < M.P1_END), ("P2", (R.t >= M.P1_END) & (R.t < M.DEV_END)), ("P3", R.t >= M.DEV_END)):
            g = R[sel]
            out.append(dict(tf=tf, period=pn, n_periods=len(g), mean_period_ret=g.ret.mean(), long_leg=g.long.mean(), short_leg=g.short.mean(),
                            **{k: v for k, v in ann(g.groupby("m").ret.sum(), 12).items()}))
        for y, g in R.groupby(pd.to_datetime(R.t).dt.year):
            out.append(dict(tf=tf, period=str(y), n_periods=len(g), mean_period_ret=g.ret.mean(), **ann(g.groupby("m").ret.sum(), 12)))
        out.append(dict(tf=tf, period="corr_with_U1_trend_long_pooled", mean_period_ret=float(np.corrcoef(ms, ser_trend_long_u1)[0, 1])))
        print("D4", tf, flush=True)
    pd.DataFrame(out).to_csv(OUT / "D4_xsmom.csv", index=False)


# ======================= D5 RC / SPA =======================
def run_d5():
    rng = np.random.default_rng(SEED + 5)
    res = []
    for uni in ("U1", "U2X"):
        src = "U2" if uni == "U2X" else uni
        tfs = M.TF_U1 if uni == "U1" else M.TF_U2
        cells = []
        for tf in tfs:
            files = [f for f in sorted((M.TR / src / M.DIRN.get(tf, tf)).glob("*.parquet")) if not (uni == "U2X" and f.stem in EXCL)]
            for fi in range(6):
                D = pd.concat([pd.read_parquet(f, columns=["fam", "side", "period", "entry_time", "gross", "ctrl", "fund"], filters=[("fam", "==", fi)]) for f in files])
                D = D[D.period < 2]
                D["m"] = pd.to_datetime(D.entry_time).dt.strftime("%Y-%m")
                for s, g in D.groupby("side"):
                    if len(g) < 30:
                        continue
                    for stat, v in (("excess", g.gross - g.ctrl), ("net_taker", g.gross - M.C_TAKER - g.fund)):
                        ok = v.notna().values
                        mi = g.m.values[ok]
                        sm = pd.Series(v.values[ok]).groupby(mi).agg(["sum", "count"]).reindex(DEV_MONTHS).fillna(0.0)
                        cells.append(dict(tf=tf, fam=M.FAM[fi], side=int(s), stat=stat, S=sm["sum"].values, N=sm["count"].values))
        nm = len(DEV_MONTHS)
        W = rng.multinomial(nm, np.full(nm, 1 / nm), size=2000).astype(float)
        thr = -np.sqrt(2 * np.log(np.log(nm)))
        for stat in ("excess", "net_taker"):
            cs = [c for c in cells if c["stat"] == stat]
            Sm = np.array([c["S"] for c in cs]); Nm = np.array([c["N"] for c in cs])
            m = Sm.sum(1) / Nm.sum(1)
            mb = (W @ Sm.T) / np.maximum(W @ Nm.T, 1)
            se = mb.std(axis=0, ddof=1)
            T = m / se
            Tmax = max(T.max(), 0.0)
            Zrc = ((mb - m) / se).max(axis=1)
            mu_c = np.where(T <= thr, m, 0.0)
            Zspa = ((mb - m + mu_c) / se).max(axis=1)
            best = int(np.argmax(T))
            res.append(dict(uni=uni, stat=stat, n_cells=len(cs), T_max=float(T.max()), best_cell=f"{cs[best]['tf']} {cs[best]['fam']} {'long' if cs[best]['side'] == 1 else 'short'}",
                            p_RC=float((Zrc >= Tmax).mean()), p_SPA=float((np.maximum(Zspa, 0) >= Tmax).mean()),
                            n_cells_T_gt_2=int((T > 2).sum())))
        print("D5", uni, flush=True)
    pd.DataFrame(res).to_csv(OUT / "D5_rc_spa.csv", index=False)


# ======================= D6 crisis windows =======================
def run_d6(carry_port):
    btc = M.resample(M.load5m("BTCUSDT"), "1D").close
    btc = btc[(btc.index >= "2020-02-01") & (btc.index < "2026-10-01")]
    r7 = (btc / btc.shift(7) - 1).dropna().sort_values()
    wins = []
    for d, v in r7.items():
        s = d - pd.Timedelta(days=7)
        if all(d <= a or s >= b for a, b, _ in wins):
            wins.append((s, d, v))
        if len(wins) == 8:
            break
    em1 = eligible_u1_months()
    em2 = {}
    for c in u2x_coins():
        for m in {pd.Timestamp(x).strftime("%Y-%m") for x in M.liq_days(c)}:
            em2[m] = em2.get(m, 0) + 1

    def sleeve(uni, fams, tfs, side):
        src = "U2" if uni == "U2X" else uni
        parts = []
        for tf in tfs:
            files = [f for f in sorted((M.TR / src / tf).glob("*.parquet")) if not (uni == "U2X" and f.stem in EXCL)]
            for fam in fams:
                D = pd.concat([pd.read_parquet(f, filters=[("fam", "==", M.FAM.index(fam))]) for f in files])
                D = D[D.side == side].dropna(subset=["fund"])
                D["st"] = pd.to_datetime(D.entry_time); D["en"] = D.st + D.hold * TFD[tf]
                D["nt"] = D.gross - M.C_TAKER - D.fund
                parts.append(D[["st", "en", "nt"]])
        return pd.concat(parts)
    S = {"U1_trend_long_4h_1D": sleeve("U1", TREND, ["4h", "8h", "12h", "1D"], 1),
         "U1_RSI_long_8h_1D": sleeve("U1", ["RSI"], ["8h", "12h", "1D"], 1),
         "U2X_trend_short_4h_1D": sleeve("U2X", TREND, ["4h", "8h", "12h", "1D"], -1)}
    out = []
    for s, d, v in wins:
        row = dict(start=s.date(), end=d.date(), btc_7d=v)
        for k, D in S.items():
            ov = (np.minimum(D.en, d) - np.maximum(D.st, s)).dt.total_seconds().clip(lower=0)
            frac = ov / (D.en - D.st).dt.total_seconds()
            em = em1 if k.startswith("U1") else em2
            row[k] = float((D.nt * frac).sum() / em.get(d.strftime("%Y-%m"), np.nan))
        cp = carry_port[("U1", "b")]; row["U1_carry_b"] = float(cp[(cp.index > s) & (cp.index <= d)].sum())
        cp = carry_port[("U2X", "b")]; row["U2X_carry_b"] = float(cp[(cp.index > s) & (cp.index <= d)].sum())
        out.append(row)
    pd.DataFrame(out).to_csv(OUT / "D6_crisis.csv", index=False)


def recompute_neff_d2():
    """N_eff with vs without the D2 families from the saved D2 trades (same definitions as run_d2)."""
    em = eligible_u1_months()
    D = pd.read_parquet(TRD / "D2_trades_U1.parquet")
    ser_new = {(tf, fam, int(s)): monthly_series(g, tf, em) for (tf, fam, s), g in D.groupby(["tf", "fam", "side"])}
    ser_old = {}
    for tf in TF2:
        for fi, fam in enumerate(M.FAM):
            files = sorted((M.TR / "U1" / tf).glob("*.parquet"))
            g = pd.concat([pd.read_parquet(f, filters=[("fam", "==", fi)]) for f in files], ignore_index=True)
            for s, gg in g.groupby("side"):
                ser_old[(tf, fam, int(s))] = monthly_series(gg, tf, em)

    def neff(S):
        X = pd.DataFrame(S); R = X.corr().values
        lam = np.clip(np.linalg.eigvalsh(R), 0, None); return float(lam.sum() ** 2 / (lam ** 2).sum()), X.shape[1]
    base = {f"{k}": v for k, v in ser_old.items() if (v != 0).sum() >= 24}
    plus = dict(base); plus.update({f"new{k}": v for k, v in ser_new.items() if (v != 0).sum() >= 24})
    return dict(old_TF2=neff(base), old_plus_new_TF2=neff(plus))


def main():
    proto = M.OUT / "DISC_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (M.OUT / "DISC_PROTOCOL_SHA256.txt").read_text().split()[0], "DISC protocol changed"
    OUT.mkdir(parents=True, exist_ok=True); TRD.mkdir(parents=True, exist_ok=True)
    finalize = len(sys.argv) > 1 and sys.argv[1] == "finalize"   # CODE_NOTES: re-run only the claims step after the run-1 crash
    if not finalize:
        port = run_d1(); print("D1 done", flush=True)
        C2, ne, ser_old = run_d2(); print("D2 done", flush=True)
    else:
        dd = pd.read_csv(OUT / "D1_carry_daily.csv", index_col=0, parse_dates=True)
        port = {tuple(c.rsplit("_", 1)): dd[c].astype(float) for c in dd.columns}
        ne = recompute_neff_d2()
    em = eligible_u1_months()
    tl = []
    for tf in ("4h", "8h", "12h", "1D"):
        for fi, fam in enumerate(M.FAM):
            if fam not in TREND:
                continue
            files = sorted((M.TR / "U1" / tf).glob("*.parquet"))
            g = pd.concat([pd.read_parquet(f, filters=[("fam", "==", fi)]) for f in files])
            tl.append(monthly_series(g[g.side == 1], tf, em))
    trend_long = pd.concat(tl, axis=1).mean(axis=1)
    if not finalize:
        run_d3(); print("D3 done", flush=True)
        run_d4(trend_long); print("D4 done", flush=True)
        run_d5()
        run_d6(port)
    cm = {}
    for (u, v), s in port.items():
        ms = s[s.index < M.DEV_END].groupby(s[s.index < M.DEV_END].index.strftime("%Y-%m")).sum().reindex(DEV_MONTHS).fillna(0.0)
        cm[f"{u}_{v}"] = float(np.corrcoef(ms.values.astype(float), trend_long.values.astype(float))[0, 1])
    files = sorted(OUT.glob("*.csv"))
    claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), n_eff_D2=ne, carry_corr_with_U1_trend_long=cm,
                  files={f.name: sha(f) for f in files}, d2_trades_sha=sha(TRD / "D2_trades_U1.parquet"), d3_trades_sha=sha(TRD / "D3_trades.parquet"))
    (OUT / "claims_disc.json").write_text(json.dumps(claims, indent=1, default=str))
    print(json.dumps({k: v for k, v in claims.items() if k != "files"}, indent=1, default=str))


if __name__ == "__main__":
    main()
