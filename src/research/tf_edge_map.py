"""TFX: timeframe edge map 1m..1M (protocol logs/research_tf_edge_map/TFX_PROTOCOL_PREREGISTERED.md).
Descriptive only: 6 canonical timing families x long/short x 11 timeframes, spot/perp costs, funding, random-timing control.
Usage: python src/research/tf_edge_map.py [g1|stats|trades|cells|all]"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "research_tf_edge_map"
TR = ROOT / "data" / "derived" / "tf_edge_map"
HF = ROOT / "data" / "universe_hf" / "5m"
RAW1M = ROOT / "archive" / "cleanup_2026_10_15" / "data" / "raw"
FUM = ROOT / "data" / "futures_um"
CORE10 = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "DOTUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
PART3 = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "ADAUSDT"]
RULE = {"1m": None, "5m": None, "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "8h": "8h", "12h": "12h", "1D": "1D",
        "1W": "W-MON", "1M": "MS"}
HOURS = {"1m": 1 / 60, "5m": 5 / 60, "15m": 0.25, "30m": 0.5, "1h": 1, "4h": 4, "8h": 8, "12h": 12, "1D": 24, "1W": 168, "1M": 730.5}
TF_U1 = ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "12h", "1D", "1W", "1M"]
TF_U2 = ["5m", "15m", "30m", "1h", "4h", "8h", "12h", "1D", "1W"]
FAM = ["TSMOM", "EMAX", "MACD", "DONCH", "RSI", "BB"]
START, END, P1_END, DEV_END = (pd.Timestamp(x) for x in ("2020-02-01", "2026-10-01", "2024-01-01", "2025-10-01"))
C_SPOT, C_TAKER, C_MAKER = 0.0017, 0.00108, 0.0004
SEED, NCTRL, NBOOT = 20261020, 20, 2000
LIQ, LIQ_DAYS, LIQ_MIN = 50e6, 30, 20
DIRN = {"1m": "1min", "1M": "1mo"}                    # Windows paths are case-insensitive: 1m and 1M must not share a folder


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load5m(coin):
    d = pd.read_csv(HF / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"], parse_dates=["timestamp"])
    return d.set_index("timestamp").sort_index()


def resample(d, tf):
    if RULE.get(tf) is None:
        return d
    return d.resample(RULE[tf], label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


# ---------------- G1: 1m usability ----------------
def load1m_raw(coin):
    f = RAW1M / f"{coin}_1m_Raw_5Years.csv.gz"
    x = pd.read_csv(f, usecols=["timestamp", "open", "high", "low", "close"])
    x["ts"] = pd.to_datetime(x["timestamp"], errors="coerce")
    return x


def g1(coin):
    x = load1m_raw(coin)
    bad_ts = x.ts.isna()
    x["month"] = x.ts.dt.to_period("M")
    ref = load5m(coin)
    rows = []
    ok = x[~bad_ts].copy()
    dup = ok.ts.duplicated(keep=False)
    nonmono = ok.ts.diff() <= pd.Timedelta(0)
    for m, g in ok.groupby("month"):
        idx = g.index
        gg = g.set_index("ts").sort_index()
        k = gg.groupby(gg.index.floor("5min"))
        agg = pd.DataFrame(dict(open=k.open.first(), high=k.high.max(), low=k.low.min(), close=k.close.last(), n=k.open.size()))
        agg = agg[agg.n == 5]
        r = ref.reindex(agg.index).dropna()
        a = agg.loc[r.index]
        mism = int((~np.isclose(a[["open", "high", "low", "close"]].values, r[["open", "high", "low", "close"]].values, rtol=1e-9, atol=0)).any(axis=1).sum())
        usable = bool(mism == 0 and len(r) > 0 and not dup.loc[idx].any() and not nonmono.loc[idx].any())
        rows.append(dict(coin=coin, month=str(m), rows_1m=len(g), full_5m=len(agg), compared=len(r), mismatched=mism,
                         dup=int(dup.loc[idx].sum()), nonmono=int(nonmono.loc[idx].sum()), usable=usable))
    rows.append(dict(coin=coin, month="UNPARSEABLE", rows_1m=int(bad_ts.sum()), full_5m=0, compared=0, mismatched=0, dup=0, nonmono=0, usable=False))
    return rows


def load1m(coin, usable_months):
    x = load1m_raw(coin)
    x = x[x.ts.notna()]
    x = x[x.ts.dt.to_period("M").astype(str).isin(usable_months)]
    return x.set_index("ts")[["open", "high", "low", "close"]].sort_index()


# ---------------- TF statistics ----------------
def tf_stats(coin):
    d = load5m(coin)
    d = d[(d.index >= "2020-01-01") & (d.index < "2026-10-01")]
    out = []
    for tf in ["5m", "15m", "30m", "1h", "4h", "8h", "12h", "1D", "1W", "1M"]:
        b = resample(d, tf)
        r = b.close.pct_change()
        rr = r[b.index >= "2024-10-01"]
        v1 = r.var()
        vr = {q: (b.close / b.close.shift(q) - 1).var() / (q * v1) for q in (2, 4, 8)}
        body = ((b.close - b.open).abs() / b.open).median()
        out.append(dict(coin=coin, tf=tf, bars=len(b), body=100 * body, range=100 * ((b.high - b.low) / b.open).median(),
                        ac1=r.autocorr(1), ac1_recent=rr.autocorr(1), vr2=vr[2], vr4=vr[4], vr8=vr[8], cost_ratio=0.00085 / body))
    return out


# ---------------- families ----------------
def ema(x, n):
    return x.ewm(span=n, adjust=False).mean()


def conditions(b, fam):
    c, h, l = b.close, b.high, b.low
    if fam == "TSMOM":
        m = c / c.shift(20) - 1
        return m > 0, m <= 0, m < 0, m >= 0
    if fam == "EMAX":
        e1, e2 = ema(c, 20), ema(c, 50)
        return e1 > e2, e1 <= e2, e1 < e2, e1 >= e2
    if fam == "MACD":
        mac = ema(c, 12) - ema(c, 26); sg = ema(mac, 9)
        return mac > sg, mac <= sg, mac < sg, mac >= sg
    if fam == "DONCH":
        hi20, lo20 = h.rolling(20).max().shift(1), l.rolling(20).min().shift(1)
        hi10, lo10 = h.rolling(10).max().shift(1), l.rolling(10).min().shift(1)
        return c > hi20, c < lo10, c < lo20, c > hi10
    if fam == "RSI":
        dlt = c.diff()
        g = dlt.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
        ls = (-dlt.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
        rsi = 100 - 100 / (1 + g / ls)
        return rsi < 30, rsi > 50, rsi > 70, rsi < 50
    if fam == "BB":
        m = c.rolling(20).mean(); s = c.rolling(20).std()          # sample sd (ddof=1), pandas default
        return c < m - 2 * s, c >= m, c > m + 2 * s, c <= m
    raise ValueError(fam)


def state_trades(entry, exit_):
    """bar-close state machine -> list of (signal bar t, exit-signal bar u). Entry and exit conditions are mutually exclusive."""
    e = entry.fillna(False).values.astype(bool); x = exit_.fillna(False).values.astype(bool)
    ev = np.where(e, 1.0, np.where(x, 0.0, np.nan))
    st = pd.Series(ev).ffill().fillna(0.0).values
    prev = np.r_[0.0, st[:-1]]
    t = np.flatnonzero((st == 1) & (prev == 0))
    u = np.flatnonzero((st == 0) & (prev == 1))
    u = u[np.searchsorted(u, t[0]) :] if len(t) else u
    k = min(len(t), len(u))
    return t[:k], u[:k]


def period_of(ts):
    return np.where(ts < P1_END, 0, np.where(ts < DEV_END, 1, 2)).astype(np.int8)


def funding_cum(coin):
    f = FUM / f"{coin}_funding.csv"
    if not f.exists():
        return None
    x = pd.read_csv(f); x["time"] = pd.to_datetime(x["time"]); x = x.sort_values("time")
    return x.time.values, np.r_[0.0, np.cumsum(x.funding_rate.values)]


def liq_days(coin):
    v = pd.read_csv(FUM / f"{coin}_perp_1h.csv.gz", usecols=["timestamp", "quote_volume"], parse_dates=["timestamp"])
    dly = v.set_index("timestamp").quote_volume.resample("1D").sum(min_count=1)
    full = dly.reindex(pd.date_range(dly.index.min(), dly.index.max(), freq="1D"))
    med = full.rolling(LIQ_DAYS, min_periods=LIQ_MIN).median().shift(1)
    return set(med[med >= LIQ].index)


def coin_trades(coin, tf, b, uni, liq, fund, rng):
    O = b.open.values; ts = b.index.values; n = len(O)
    fill_ts = pd.DatetimeIndex(ts)
    elig = (fill_ts >= START) & (fill_ts < END)
    if uni == "U2":
        elig &= fill_ts.floor("D").isin(liq)
    per_all = period_of(fill_ts)
    pools = {p: np.flatnonzero(elig & (per_all == p)) for p in (0, 1, 2)}
    rows = []
    for fi, fam in enumerate(FAM):
        le, lx, se, sx = conditions(b, fam)
        for side, (en, ex) in ((1, (le, lx)), (-1, (se, sx))):
            t, u = state_trades(en, ex)
            e, x = t + 1, u + 1
            keep = x < n
            e, x = e[keep], x[keep]
            if len(e) == 0:
                continue
            keep = elig[e]
            if tf == "1m":                                    # both fills inside usable (contiguous-month) data
                keep &= (fill_ts[x] - fill_ts[e]) == pd.to_timedelta((x - e), unit="m")
            e, x = e[keep], x[keep]
            if len(e) == 0:
                continue
            gross = side * (O[x] - O[e]) / O[e]
            h = x - e
            per = per_all[e]
            ctrl = np.full(len(e), np.nan)
            for p in (0, 1, 2):
                sel = np.flatnonzero(per == p)
                if not len(sel):
                    continue
                pool = pools[p]
                lim = np.searchsorted(pool, n - h[sel])            # pool entries j with j + h < n
                r = rng.random((len(sel), NCTRL))
                j = pool[np.minimum((r * lim[:, None]).astype(np.int64), np.maximum(lim[:, None] - 1, 0))]
                jj = j + h[sel][:, None]
                g = side * (O[np.minimum(jj, n - 1)] - O[j]) / O[j]
                g[lim == 0] = np.nan
                ctrl[sel] = g.mean(axis=1)
            if fund is not None:
                ft, cum = fund
                a = np.searchsorted(ft, ts[e], side="right"); z = np.searchsorted(ft, ts[x], side="right")
                fsum = side * (cum[z] - cum[a])
                perp_ok = ts[e] >= ft[0]
            else:
                fsum = np.full(len(e), np.nan); perp_ok = np.zeros(len(e), bool)
            rows.append(pd.DataFrame(dict(coin=coin, fam=np.int8(fi), side=np.int8(side), e=e.astype(np.int32), x=x.astype(np.int32),
                                          entry_time=ts[e], hold=h.astype(np.int32), gross=gross, fund=np.where(perp_ok, fsum, np.nan),
                                          ctrl=ctrl, period=per, year=fill_ts[e].year.astype(np.int16))))
    return pd.concat(rows, ignore_index=True) if rows else None


def run_trades():
    TR.mkdir(parents=True, exist_ok=True)
    import r2_t14_universe as U
    cands = [c for c in U.candidates() if (HF / f"{c}_5m_full.csv.gz").exists()]
    g1t = pd.read_csv(OUT / "G1_1m_usability.csv")
    use1m = {c: set(g.month[g.usable]) for c, g in g1t.groupby("coin")}
    elig_years = []
    only = sys.argv[2] if len(sys.argv) > 2 else None
    old = pd.read_csv(OUT / "eligible_coin_years.csv") if only and (OUT / "eligible_coin_years.csv").exists() else None
    if old is not None:
        elig_years = old[old.uni != only].to_dict("records")
    for uni, coins, tfs in (("U1", CORE10, TF_U1), ("U2", cands, TF_U2)):
        if only and uni != only:
            continue
        rng = np.random.default_rng(SEED)
        for ci, coin in enumerate(coins):
            liq = liq_days(coin) if uni == "U2" else None
            fund = funding_cum(coin)
            d5 = load5m(coin)
            for tf in tfs:
                if tf == "1m":
                    if not use1m.get(coin):
                        continue
                    b = load1m(coin, use1m[coin])
                else:
                    b = resample(d5, tf)
                fts = b.index
                el = (fts >= START) & (fts < END)
                if uni == "U2":
                    el &= fts.floor("D").isin(liq)
                for p in (0, 1, 2):
                    m = el & (period_of(fts) == p)
                    elig_years.append(dict(uni=uni, tf=tf, coin=coin, period=p, coin_years=float(m.sum() * HOURS[tf] / 8766)))
                D = coin_trades(coin, tf, b, uni, liq, fund, rng)
                if D is not None:
                    p = TR / uni / DIRN.get(tf, tf)
                    p.mkdir(parents=True, exist_ok=True)
                    D.to_parquet(p / f"{coin}.parquet", index=False)
            print(f"{uni} {ci + 1}/{len(coins)} {coin}", flush=True)
    pd.DataFrame(elig_years).to_csv(OUT / "eligible_coin_years.csv", index=False)


# ---------------- cell statistics ----------------
def boot(x, blocks, rng, ncell):
    """mean CI by coin-year block bootstrap; Bonferroni CI by normal approx with the bootstrap SE (2,000 draws cannot reach 1-0.05/N quantiles)."""
    from scipy.stats import norm
    codes, inv = np.unique(blocks, return_inverse=True)
    s = np.bincount(inv, weights=x); c = np.bincount(inv).astype(float)
    W = rng.multinomial(len(codes), np.full(len(codes), 1 / len(codes)), size=NBOOT)
    mb = (W @ s) / np.maximum(W @ c, 1)
    m = x.mean(); se = mb.std(ddof=1)
    z = norm.ppf(1 - 0.05 / max(ncell, 1) / 2)
    return m, np.quantile(mb, 0.025), np.quantile(mb, 0.975), m - z * se, m + z * se


def run_cells(excl=(), outname="TFX_cells.csv"):
    ey = pd.read_csv(OUT / "eligible_coin_years.csv")
    ey = ey[~ey.coin.isin(excl)]
    out = []
    for uni, tfs in (("U1", TF_U1), ("U2", TF_U2)):
        cnt = []
        for tf in tfs:
            for f in sorted((TR / uni / DIRN.get(tf, tf)).glob("*.parquet")):
                if f.stem in excl:
                    continue
                q = pd.read_parquet(f, columns=["fam", "side", "period"])
                cnt.append(q[q.period < 2].assign(tf=tf).groupby(["tf", "fam", "side"]).size())
        cnt = pd.concat(cnt).groupby(level=[0, 1, 2]).sum()
        ncell = int((cnt >= 30).sum())
        rng = np.random.default_rng(SEED)

        def recs():                                       # one (tf, family) at a time: memory-bounded
            for tf in tfs:
                files = sorted((TR / uni / DIRN.get(tf, tf)).glob("*.parquet"))
                for fi in range(len(FAM)):
                    D = pd.concat([pd.read_parquet(f, filters=[("fam", "==", fi)]) for f in files if f.stem not in excl], ignore_index=True)
                    for side, g in D.groupby("side"):
                        yield tf, fi, side, g
                    del D
        for tf, fi, side, g in recs():
            dev = g[g.period < 2]
            cy = ey[(ey.uni == uni) & (ey.tf == tf) & (ey.period < 2)].coin_years.sum()
            r = dict(uni=uni, tf=tf, family=FAM[fi], side="long" if side == 1 else "short", n_dev=len(dev), n_P3=int((g.period == 2).sum()),
                     trades_per_coin_year=len(dev) / cy if cy else np.nan,
                     hold_bars_mean=dev.hold.mean(), hold_bars_median=dev.hold.median(), hold_hours_median=dev.hold.median() * HOURS[tf])
            if len(dev) < 30:
                r["reading"] = "too few"; out.append(r); continue
            nt = dev.gross - C_TAKER - dev.fund
            nm = dev.gross - C_MAKER - dev.fund
            ns = dev.gross - C_SPOT
            ex = dev.gross - dev.ctrl
            blk = (dev.coin + "_" + dev.year.astype(str)).values
            r.update(gross_mean=dev.gross.mean(), gross_median=dev.gross.median(), gross_over_taker_cost=dev.gross.mean() / C_TAKER,
                     ctrl_mean=dev.ctrl.mean(), excess_mean=ex.mean())
            pm = nt.notna().values
            m, lo, hi, blo, bhi = boot(nt[pm].values, blk[pm], rng, ncell)
            r.update(net_taker_dev=m, net_taker_ci_lo=lo, net_taker_ci_hi=hi, net_taker_bonf_lo=blo, net_taker_bonf_hi=bhi,
                     net_maker_dev=nm[pm].mean(), perp_rows_dev=int(pm.sum()))
            for pn, pi in (("P1", 0), ("P2", 1)):
                q = (dev.period == pi).values & pm
                r[f"net_taker_{pn}"] = nt[q].mean() if q.any() else np.nan
                r[f"net_spot_{pn}"] = ns[(dev.period == pi).values].mean()
            g3 = g[g.period == 2]
            r["net_taker_P3"] = (g3.gross - C_TAKER - g3.fund).mean() if len(g3) else np.nan
            cyr = pd.DataFrame(dict(b=blk[pm], v=nt[pm].values)).groupby("b").v.mean()
            r["pos_coin_year_share"] = float((cyr > 0).mean())
            if side == 1:
                m2, lo2, hi2, blo2, bhi2 = boot(ns.values, blk, rng, ncell)
                r.update(net_spot_dev=m2, net_spot_ci_lo=lo2, net_spot_bonf_lo=blo2)
            em = ex.notna().values
            m3, lo3, hi3, blo3, bhi3 = boot(ex[em].values, blk[em], rng, ncell)
            r.update(excess_ci_lo=lo3, excess_ci_hi=hi3, excess_bonf_lo=blo3, excess_bonf_hi=bhi3)
            lab = []
            if lo > 0 and r["net_taker_P1"] > 0 and r["net_taker_P2"] > 0:
                lab.append("COST-VIABLE-PERP" + ("-STRICT" if blo > 0 else ""))
            if side == 1 and r["net_spot_ci_lo"] > 0 and r["net_spot_P1"] > 0 and r["net_spot_P2"] > 0:
                lab.append("COST-VIABLE-SPOT" + ("-STRICT" if r["net_spot_bonf_lo"] > 0 else ""))
            if lo3 > 0:
                lab.append("TIMING+" + ("-STRICT" if blo3 > 0 else ""))
            if hi3 < 0:
                lab.append("TIMING-" + ("-STRICT" if bhi3 < 0 else ""))
            r["reading"] = ";".join(lab) if lab else "none"
            r["n_cells_universe"] = ncell
            out.append(r)
        print(uni, "cells", ncell, flush=True)
    C = pd.DataFrame(out)
    C.to_csv(OUT / outname, index=False)
    return C


def g0():
    """replicate Part 3 per-coin TF table (research_notes/.../internal_tf_stats.md) at printed precision (+-1 last digit)."""
    md = (ROOT / "research_notes" / "AI ब्रेन टाइमफ्रेम सिंक अंतिम सत्यापन" / "internal_tf_stats.md").read_text(encoding="utf-8")
    part = md.split("## Per coin")[1]
    rows = [l.strip().strip("|").split("|") for l in part.splitlines() if l.startswith("| ") and "USDT" in l]
    cols = ["coin", "tf", "bars", "body", "range", "ac1", "ac1_recent", "vr4", "cost_ratio"]
    T = pd.DataFrame([[v.strip() for v in r] for r in rows], columns=cols)
    S = pd.read_csv(OUT / "TF_stats.csv")
    out = []
    for r in T.itertuples(index=False):
        m = S[(S.coin == r.coin) & (S.tf == r.tf)].iloc[0]
        for c in cols[2:]:
            txt = getattr(r, c); dec = len(txt.split(".")[1]) if "." in txt else 0
            tol = 10 ** (-dec) * 1.0 + 1e-12
            out.append(dict(coin=r.coin, tf=r.tf, col=c, part3=float(txt), ours=float(m[c]), match=abs(float(txt) - float(m[c])) <= tol))
    G = pd.DataFrame(out)
    G.to_csv(OUT / "G0_part3_replication.csv", index=False)
    return G


def main():
    proto = OUT / "TFX_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "TFX_PROTOCOL_SHA256.txt").read_text().split()[0], "TFX protocol changed"
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("g1", "all"):
        rows = sum((g1(c) for c in CORE10), [])
        pd.DataFrame(rows).to_csv(OUT / "G1_1m_usability.csv", index=False)
        print("G1 done", flush=True)
    if what in ("stats", "all"):
        S = pd.DataFrame(sum((tf_stats(c) for c in sorted(set(CORE10) | set(PART3))), []))
        S.to_csv(OUT / "TF_stats.csv", index=False)
        print("stats done", flush=True)
    if what in ("trades", "all"):
        run_trades()
    if what == "cells-excl":                            # POST-HOC sensitivity (CODE_NOTES): drop relaunched / gapped symbols
        run_cells(excl=("LUNAUSDT", "STRAXUSDT"), outname="TFX_cells_POSTHOC_excl_LUNA_STRAX.csv")
    if what in ("cells", "all"):
        C = run_cells()
        G0 = g0(); G = pd.read_csv(OUT / "G1_1m_usability.csv")
        claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), cells_sha=sha(OUT / "TFX_cells.csv"),
                      stats_sha=sha(OUT / "TF_stats.csv"), g1_sha=sha(OUT / "G1_1m_usability.csv"),
                      g1_usable_months=int(G.usable.sum()), g1_months=int((G.month != "UNPARSEABLE").sum()),
                      g1_unparseable_rows=int(G[G.month == "UNPARSEABLE"].rows_1m.sum()),
                      g0_match_by_tf_col=G0.groupby(["tf", "col"]).match.all().unstack().to_dict(),
                      g0_values_matched=int(G0.match.sum()), g0_values=len(G0),
                      n_cells=C.groupby("uni").n_cells_universe.max().to_dict(),
                      readings=C.groupby(["uni", "reading"]).size().reset_index().values.tolist())
        (OUT / "claims_tfx.json").write_text(json.dumps(claims, indent=1, default=str))
        print(json.dumps(claims, indent=1, default=str))


if __name__ == "__main__":
    main()
