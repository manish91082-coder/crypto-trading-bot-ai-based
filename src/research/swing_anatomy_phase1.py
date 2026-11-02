"""
Swing Anatomy 2017-2026, all timeframes -- Phase 1 (data + swing catalog + causal factors + descriptive analysis).
Protocol: logs/research_swing_anatomy/PHASE1_PROTOCOL_PREREGISTERED.md (SHA256 locked before any result).
Usage: python swing_anatomy_phase1.py          (build + analyse)
"""
import sys
import json
import time
import bisect
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "research", SRC_DIR / "analytics", SRC_DIR / "pipeline_1d"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import DATA_DIR, LOGS_DIR, SYMBOLS
import swing_study_1d as SS
import swing_strategy_1d as E

OUT = LOGS_DIR / "research_swing_anatomy"
DER = DATA_DIR / "derived" / "swing_anatomy"
PROTO = "PHASE1_PROTOCOL_PREREGISTERED.md"
COINS = list(SYMBOLS)
END = pd.Timestamp("2026-10-01")
KS, KP = (2.0, 3.0, 4.0), 3.0
SWING_TFS = ["1M", "1W", "1D", "12h", "8h", "4h", "1h", "30m", "15m", "5m"]
HTF_LIST = ["1M", "1W", "1D", "4h", "1h"]
ORDER = {tf: i for i, tf in enumerate(SWING_TFS)}
STEP = {"5m": "5min", "15m": "15min", "1h": "1h", "1d": "1D"}
DUR = {"5m": pd.Timedelta(minutes=5), "15m": pd.Timedelta(minutes=15), "30m": pd.Timedelta(minutes=30), "1h": pd.Timedelta(hours=1),
       "4h": pd.Timedelta(hours=4), "8h": pd.Timedelta(hours=8), "12h": pd.Timedelta(hours=12), "1D": pd.Timedelta(days=1),
       "1W": pd.Timedelta(days=7)}
VAP_W = {"5m": pd.Timedelta(days=1), "15m": pd.Timedelta(days=1), "30m": pd.Timedelta(days=1), "1h": pd.Timedelta(days=7),
         "4h": pd.Timedelta(days=30), "8h": pd.Timedelta(days=30), "12h": pd.Timedelta(days=30), "1D": pd.Timedelta(days=90),
         "1W": pd.Timedelta(days=365), "1M": pd.Timedelta(days=365)}
COLS = ["timestamp", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"]
FACTORS = ["ret5", "ret20", "dist_sma50_atr", "dist_sma200_atr", "rsi14", "atr_pct", "atr_ratio100", "vol_ratio20", "taker_ratio",
           "range_pos50", "dd_from_high200", "sup_dist_atr", "res_dist_atr", "vap_at_price"] + \
          [f"htf_state_{h}" for h in HTF_LIST] + ["btc_ret20", "btc_state_same_tf", "fng", "fng_chg7", "hour", "weekday"]


# ----------------------------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------------------------
def paths(coin, src):
    if src == "1d":
        return DATA_DIR / "universe_pre2020" / "1d" / f"{coin}_1d.csv", DATA_DIR / "universe_all" / "1d" / f"{coin}_1d.csv"
    if src == "1h":
        return DATA_DIR / "universe_pre2020" / "1h" / f"{coin}_1h_full.csv.gz", DATA_DIR / "universe_all" / "1h" / f"{coin}_1h_full.csv.gz"
    return (DATA_DIR / "universe_pre2020_hf" / src / f"{coin}_{src}_full.csv.gz", DATA_DIR / "universe_hf" / src / f"{coin}_{src}_full.csv.gz")


def regrid(d, step):
    """Floor off-grid candles (Feb-2018 outage) to the grid and aggregate duplicates."""
    d["timestamp"] = d.timestamp.dt.floor(step)
    if d.timestamp.is_unique:
        return d
    g = d.groupby("timestamp", sort=True)
    return pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last(),
                             quote_volume=g.quote_volume.sum(), taker_buy_quote=g.taker_buy_quote.sum())).reset_index()


def load_spliced(coin, src, gate):
    pre, post = paths(coin, src)
    parts = []
    for p in (pre, post):
        if p.exists():
            d = pd.read_csv(p, usecols=COLS, parse_dates=["timestamp"])
            assert d.timestamp.dtype.kind == "M", p
            parts.append(regrid(d.sort_values("timestamp").reset_index(drop=True), STEP[src]))
    if len(parts) == 2:
        a, b = parts
        ok = a.timestamp.iloc[-1] + pd.Timedelta(STEP[src]) == b.timestamp.iloc[0]
        gate.append(dict(coin=coin, src=src, pre_last=str(a.timestamp.iloc[-1]), post_first=str(b.timestamp.iloc[0]), contiguous=bool(ok)))
    d = pd.concat(parts, ignore_index=True)
    d = d[d.timestamp < END].reset_index(drop=True)
    assert d.timestamp.is_unique and d.timestamp.is_monotonic_increasing
    return d


def agg(d, rule):
    g = d.set_index("timestamp").resample(rule, label="left", closed="left")
    b = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last(),
                          quote_volume=g.quote_volume.sum(), taker_buy_quote=g.taker_buy_quote.sum()))
    return b.dropna(subset=["close"]).reset_index()


def clip_atr(d):
    d = d.copy()
    bl, bh = d[["open", "close"]].min(axis=1), d[["open", "close"]].max(axis=1)
    bad_lo = (1 - d.low / bl) * 100 > SS.ANOMALY_WICK_PCT
    bad_hi = (d.high / bh - 1) * 100 > SS.ANOMALY_WICK_PCT
    d.loc[bad_lo, "low"] = bl[bad_lo]
    d.loc[bad_hi, "high"] = bh[bad_hi]
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    d["ATR_14"] = tr.rolling(14).mean()
    return d, int(bad_lo.sum() + bad_hi.sum())


def crosscheck(fine, native, rule):
    a = agg(fine, rule).set_index("timestamp")
    b = native.set_index("timestamp")
    j = b.join(a, rsuffix="_a", how="inner")
    ok = (np.isclose(j.open, j.open_a, rtol=1e-9) & np.isclose(j.high, j.high_a, rtol=1e-9) &
          np.isclose(j.low, j.low_a, rtol=1e-9) & np.isclose(j.close, j.close_a, rtol=1e-9))
    return int(len(j)), int((~ok).sum())


def build_bars(coin, gate, xc, clips):
    n5, n15, n1h, n1d = (load_spliced(coin, s, gate) for s in ("5m", "15m", "1h", "1d"))
    for name, fine, nat, rule in (("1h_from_5m", n5, n1h, "1h"), ("1d_from_1h", n1h, n1d, "1D")):
        cnt, bad = crosscheck(fine, nat, rule)
        xc.append(dict(coin=coin, check=name, bars=cnt, mismatched=bad))
    raw = {"5m": n5, "15m": n15, "30m": agg(n5, "30min"), "1h": n1h, "4h": agg(n1h, "4h"), "8h": agg(n1h, "8h"),
           "12h": agg(n1h, "12h"), "1D": n1d, "1W": agg(n1d, "W-MON"), "1M": agg(n1d, "MS")}
    bars = {}
    for tf, d in raw.items():
        bars[tf], clips[(coin, tf)] = clip_atr(d)
    return bars, n1h, n1d


def end_times(tf, ts):
    if tf == "1M":
        return (pd.DatetimeIndex(ts) + pd.offsets.MonthBegin(1)).values
    return ts + DUR[tf].to_timedelta64()


# ----------------------------------------------------------------------------------------------
# Factors
# ----------------------------------------------------------------------------------------------
def base_factors(b):
    c, h, l, qv, tbq, atr = b.close, b.high, b.low, b.quote_volume, b.taker_buy_quote, b.ATR_14
    f = pd.DataFrame(index=b.index)
    f["ret5"], f["ret20"] = c.pct_change(5, fill_method=None), c.pct_change(20, fill_method=None)
    f["dist_sma50_atr"] = (c - c.rolling(50).mean()) / atr
    f["dist_sma200_atr"] = (c - c.rolling(200).mean()) / atr
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    f["rsi14"] = 100 - 100 / (1 + up / dn)
    f["atr_pct"] = atr / c
    f["atr_ratio100"] = atr / atr.rolling(100).mean().shift(1)
    f["vol_ratio20"] = qv / qv.rolling(20).mean().shift(1)
    f["taker_ratio"] = tbq / qv
    lo50, hi50 = l.rolling(50).min(), h.rolling(50).max()
    f["range_pos50"] = (c - lo50) / (hi50 - lo50)
    f["dd_from_high200"] = c / h.rolling(200).max() - 1
    return f.replace([np.inf, -np.inf], np.nan)


def sr_nearest(b, k=3):
    """Nearest UNBROKEN fractal support below / resistance above the close, at every bar close (exact sweep).
    A level (bar i) is known at the close of bar i+k; it is broken at the first later close beyond it."""
    hi, lo, cl = b.high.values, b.low.values, b.close.values
    n = len(b)
    rh = pd.Series(hi).rolling(2 * k + 1, center=True).max().values
    rl = pd.Series(lo).rolling(2 * k + 1, center=True).min().values
    idx = np.arange(n)
    inside = (idx >= k) & (idx < n - k)
    add_s = {t: [] for t in range(n)}
    add_r = {t: [] for t in range(n)}
    for i in idx[inside & (lo == rl)]:
        add_s[i + k].append(lo[i])
    for i in idx[inside & (hi == rh)]:
        add_r[i + k].append(hi[i])
    S, R = [], []
    sup, res = np.full(n, np.nan), np.full(n, np.nan)
    for t in range(n):
        for v in add_s[t]:
            bisect.insort(S, v)
        for v in add_r[t]:
            bisect.insort(R, v)
        c = cl[t]
        while S and S[-1] > c:
            S.pop()
        while R and R[0] < c:
            R.pop(0)
        if S:
            sup[t] = S[-1]
        if R:
            res[t] = R[0]
    return sup, res


def vap_at(h1, t_end, price, band, W):
    ts, lo, hi, qv = h1
    a = np.searchsorted(ts, (t_end - W), "left")
    z = np.searchsorted(ts, t_end, "left")
    if z - a < 10:
        return np.nan
    s = slice(a, z)
    tot = qv[s].sum()
    if tot <= 0:
        return np.nan
    hit = (lo[s] <= price + band) & (hi[s] >= price - band)
    return float(qv[s][hit].sum() / tot)


def state_lookup(states, t_end):
    """states: (end_time array, state array) of a higher timeframe; value known at t_end."""
    et, st = states
    j = np.searchsorted(et, t_end, "right") - 1
    return np.where(j >= 0, st[np.maximum(j, 0)], 0)


# ----------------------------------------------------------------------------------------------
# Legs
# ----------------------------------------------------------------------------------------------
def legs_for(coin, tf, b, K, fac, sup, res, h1, htf_states, btc, fng):
    piv = SS.zigzag_pivots(b, K)
    ts, cl, atr = b.timestamp.values, b.close.values, b.ATR_14.values
    et = end_times(tf, ts)
    rows = []
    for a_, c_ in zip(piv, piv[1:]):
        down = a_["kind"] == "H"
        ci = a_["confirm_idx"]
        rows.append(dict(coin=coin, tf=tf, K=K, direction="Decline" if down else "Rally",
                         start_time=ts[a_["idx"]], start_price=a_["price"], end_time=ts[c_["idx"]], end_price=c_["price"],
                         start_i=a_["idx"], end_i=c_["idx"], confirm_i=ci, confirm_time=et[ci], confirm_close=cl[ci],
                         atr_start=atr[a_["idx"]], atr_confirm=atr[ci]))
    L = pd.DataFrame(rows)
    if L.empty:
        return L
    L["move_pct"] = (L.end_price / L.start_price - 1) * 100
    L["move_atr"] = (L.end_price - L.start_price).abs() / L.atr_start
    L["bars"] = L.end_i - L.start_i
    L["days"] = (pd.to_datetime(L.end_time) - pd.to_datetime(L.start_time)).dt.total_seconds() / 86400
    L["remaining_pct"] = (L.end_price / L.confirm_close - 1) * 100
    sign = np.where(L.direction == "Decline", -1.0, 1.0)
    L["rem_atr"] = sign * (L.end_price - L.confirm_close) / L.atr_confirm
    L["done_share_at_confirm"] = 1 - (L.end_price - L.confirm_close).abs() / (L.end_price - L.start_price).abs().replace(0, np.nan)
    if K != KP:                      # factors are only used by the K = 3 analyses (D-B, D-C, D-D); K = 2 / 4 feed D-A / D-F
        return L
    for pre, col in (("c_", "confirm_i"), ("p_", "start_i")):
        ii = L[col].values
        for f in fac.columns:
            L[pre + f] = fac[f].values[ii]
        price = cl[ii]
        a_ = atr[ii]
        L[pre + "sup_dist_atr"] = (price - sup[ii]) / a_
        L[pre + "res_dist_atr"] = (res[ii] - price) / a_
        tend = et[ii]
        L[pre + "vap_at_price"] = [vap_at(h1, t, p_, 0.25 * x, VAP_W[tf].to_timedelta64()) for t, p_, x in zip(tend, price, a_)]
        for h in HTF_LIST:
            L[pre + f"htf_state_{h}"] = state_lookup(htf_states[h], tend) if ORDER[h] < ORDER[tf] else np.nan
        if btc is not None:
            bts, bret, bst, bet = btc
            j = np.searchsorted(bet, tend, "right") - 1
            ok = j >= 0
            L[pre + "btc_ret20"] = np.where(ok, bret[np.maximum(j, 0)], np.nan)
            L[pre + "btc_state_same_tf"] = np.where(ok, bst[np.maximum(j, 0)], np.nan)
        else:
            L[pre + "btc_ret20"], L[pre + "btc_state_same_tf"] = np.nan, np.nan
        day = (pd.to_datetime(tend) - pd.Timedelta(microseconds=1)).normalize() - pd.Timedelta(days=1)
        L[pre + "fng"] = fng["fng"].reindex(day).values
        L[pre + "fng_chg7"] = fng["fng_chg7"].reindex(day).values
        st = pd.to_datetime(ts[ii])
        L[pre + "hour"] = st.hour if tf not in ("1D", "1W", "1M") else np.nan
        L[pre + "weekday"] = st.weekday if tf not in ("1W", "1M") else np.nan
    return L


def fng_table():
    raw = json.loads((DATA_DIR / "sentiment" / "fear_greed_raw.json").read_bytes())
    d = pd.DataFrame(raw["data"])
    d["date"] = pd.to_datetime(d.timestamp, format="%d-%m-%Y")
    s = d.set_index("date").value.astype(float).sort_index()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))
    return pd.DataFrame(dict(fng=s, fng_chg7=s - s.shift(7)))


def anatomy(coin, d1):
    rows = []
    d = d1.copy()
    d["year"] = d.timestamp.dt.year
    d["half"] = np.where(d.timestamp.dt.month <= 6, "H1", "H2")
    for per, keys in (("1Y", ["year"]), ("6M", ["year", "half"])):
        for k, g in d.groupby(keys):
            run_hi = g.high.cummax()
            dd = (g.low / run_hi - 1).min() * 100
            rows.append(dict(coin=coin, period=per, key=str(k), first=str(g.timestamp.iloc[0].date()), last=str(g.timestamp.iloc[-1].date()),
                             days=len(g), open=g.open.iloc[0], high=g.high.max(), high_date=str(g.timestamp[g.high.idxmax()].date()),
                             low=g.low.min(), low_date=str(g.timestamp[g.low.idxmin()].date()), close=g.close.iloc[-1],
                             change_pct=(g.close.iloc[-1] / g.open.iloc[0] - 1) * 100, max_drawdown_inside_pct=dd))
    return rows


# ----------------------------------------------------------------------------------------------
# Analysis helpers
# ----------------------------------------------------------------------------------------------
def month_col(df):
    return pd.to_datetime(df.confirm_time).dt.to_period("M").astype(str)


def boot_mean_diff(a, b, ma, mb, reps=2000, seed=1):
    da = pd.DataFrame(dict(m=ma, v=a)).groupby("m").v.agg(["sum", "count"])
    db = pd.DataFrame(dict(m=mb, v=b)).groupby("m").v.agg(["sum", "count"])
    months = sorted(set(da.index) | set(db.index))
    da, db = da.reindex(months).fillna(0), db.reindex(months).fillna(0)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(reps):
        k = rng.integers(0, len(months), len(months))
        ca, cb = da["count"].values[k].sum(), db["count"].values[k].sum()
        if ca and cb:
            out.append(da["sum"].values[k].sum() / ca - db["sum"].values[k].sum() / cb)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def rank_corr_ci(x, y, m, reps=2000, seed=1):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, m = x[ok], y[ok], m[ok]
    if len(x) < 50:
        return None
    rx, ry = pd.Series(x).rank().values, pd.Series(y).rank().values
    g = pd.DataFrame(dict(m=m, x=rx, y=ry, xy=rx * ry, xx=rx * rx, yy=ry * ry)).groupby("m").agg(["sum", "count"])
    S = {c: g[(c, "sum")].values for c in ("x", "y", "xy", "xx", "yy")}
    N = g[("x", "count")].values

    def corr(k):
        n = N[k].sum()
        sx, sy, sxy, sxx, syy = (S[c][k].sum() for c in ("x", "y", "xy", "xx", "yy"))
        vx, vy = sxx - sx * sx / n, syy - sy * sy / n
        return (sxy - sx * sy / n) / np.sqrt(vx * vy) if vx > 0 and vy > 0 else np.nan
    full = corr(np.arange(len(N)))
    rng = np.random.default_rng(seed)
    bs = [corr(rng.integers(0, len(N), len(N))) for _ in range(reps)]
    bs = [v for v in bs if np.isfinite(v)]
    return dict(n=int(len(x)), rho=float(full), ci_low=float(np.percentile(bs, 2.5)), ci_high=float(np.percentile(bs, 97.5)))


def analyse(L, A):
    res = {}
    # D-A (+ D-F): size / frequency per tf, K, direction
    L["year"] = pd.to_datetime(L.start_time).dt.year
    rows = []
    for (tf, K, dr), g in L.groupby(["tf", "K", "direction"]):
        mp = g.move_pct.abs()
        rows.append(dict(tf=tf, K=K, direction=dr, legs=len(g), coins=g.coin.nunique(),
                         legs_per_coin_year=round(len(g) / g.groupby("coin").year.nunique().sum(), 2),
                         move_pct_median=mp.median(), move_pct_p75=mp.quantile(.75), move_pct_p90=mp.quantile(.9), move_pct_max=mp.max(),
                         move_atr_median=g.move_atr.median(), move_atr_p90=g.move_atr.quantile(.9), days_median=g.days.median(),
                         rem_atr_median=g.rem_atr.median(), rem_pct_median=g.remaining_pct.abs().median(),
                         p_rem_ge_1atr=(g.rem_atr >= 1).mean(), done_share_at_confirm_median=g.done_share_at_confirm.median()))
    DA = pd.DataFrame(rows)
    DA["tf_order"] = DA.tf.map(ORDER)
    DA = DA.sort_values(["K", "direction", "tf_order"]).drop(columns="tf_order")
    DA.to_csv(OUT / "DA_size_frequency.csv", index=False)
    res["DA"] = DA
    P = L[L.K == KP].copy()
    P["m"] = month_col(P)
    yr = P.groupby(["tf", "direction", "year"]).size().unstack(fill_value=0)
    yr.to_csv(OUT / "DA_legs_per_year_K3.csv")
    # D-B: nesting by higher-timeframe state
    rows = []
    for (tf, dr), g in P.groupby(["tf", "direction"]):
        for h in HTF_LIST:
            if ORDER[h] >= ORDER[tf]:
                continue
            col = f"c_htf_state_{h}"
            up, dn = g[g[col] == 1], g[g[col] == -1]
            if len(up) < 20 or len(dn) < 20:
                continue
            lo_, hi_ = boot_mean_diff(dn.rem_atr.values, up.rem_atr.values, dn.m.values, up.m.values)
            rows.append(dict(tf=tf, direction=dr, htf=h, n_htf_down=len(dn), n_htf_up=len(up),
                             rem_atr_mean_htf_down=dn.rem_atr.mean(), rem_atr_mean_htf_up=up.rem_atr.mean(),
                             diff_down_minus_up=dn.rem_atr.mean() - up.rem_atr.mean(), ci_low=lo_, ci_high=hi_,
                             p_rem1_htf_down=(dn.rem_atr >= 1).mean(), p_rem1_htf_up=(up.rem_atr >= 1).mean()))
    DB = pd.DataFrame(rows)
    DB.to_csv(OUT / "DB_topdown_nesting.csv", index=False)
    res["DB"] = DB
    # D-C: factor associations at confirmation (rank corr + quintiles + split-period sign check)
    rows, qrows = [], []
    early = pd.to_datetime(P.confirm_time) < pd.Timestamp("2021-01-01")
    for (tf, dr), g in P.groupby(["tf", "direction"]):
        e = early.loc[g.index]
        for f in FACTORS:
            col = "c_" + f
            if col not in g or g[col].notna().sum() < 100 or g[col].nunique() < 3:
                continue
            r = rank_corr_ci(g[col].values.astype(float), g.rem_atr.values, g.m.values)
            if r is None:
                continue
            r1 = rank_corr_ci(g[col][e].values.astype(float), g.rem_atr[e].values, g.m[e].values, reps=200)
            r2 = rank_corr_ci(g[col][~e].values.astype(float), g.rem_atr[~e].values, g.m[~e].values, reps=200)
            rows.append(dict(tf=tf, direction=dr, factor=f, **r, rho_2017_2020=r1["rho"] if r1 else np.nan,
                             rho_2021_2026=r2["rho"] if r2 else np.nan,
                             robust=bool(r["ci_low"] > 0 or r["ci_high"] < 0) and r1 is not None and r2 is not None
                             and np.sign(r1["rho"]) == np.sign(r2["rho"]) == np.sign(r["rho"])))
            gg = g[[col, "rem_atr"]].dropna()
            if gg[col].nunique() >= 5:
                q = pd.qcut(gg[col].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
                for qi, s in gg.groupby(q, observed=True):
                    qrows.append(dict(tf=tf, direction=dr, factor=f, quintile=int(qi), n=len(s), factor_median=s[col].median(),
                                      rem_atr_median=s.rem_atr.median(), p_rem_ge_1atr=(s.rem_atr >= 1).mean()))
    DC = pd.DataFrame(rows)
    DC.to_csv(OUT / "DC_factor_rank_corr.csv", index=False)
    pd.DataFrame(qrows).to_csv(OUT / "DC_factor_quintiles.csv", index=False)
    res["DC"] = DC
    # D-D: case files
    cols = ["coin", "tf", "start_time", "start_price", "end_time", "end_price", "move_pct", "move_atr", "days", "confirm_time",
            "remaining_pct", "rem_atr"] + ["c_" + f for f in FACTORS if "c_" + f in P]
    dec = P[P.direction == "Decline"]
    dec.sort_values("move_pct").groupby("tf").head(30)[cols].to_csv(OUT / "DD_largest_declines_per_tf.csv", index=False)
    b = dec[(dec.coin == "BTCUSDT") & dec.tf.isin(["1D", "1W", "4h", "1h"])]
    b.assign(year=b.year).sort_values("move_pct").groupby(["tf", "year"]).head(1)[cols + ["year"]].to_csv(OUT / "DD_btc_largest_decline_per_year.csv", index=False)
    pd.DataFrame(A).to_csv(OUT / "DE_1Y_6M_anatomy.csv", index=False)
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DER.mkdir(parents=True, exist_ok=True)
    h_ = hashlib.sha256((OUT / PROTO).read_bytes()).hexdigest()
    assert h_ == (OUT / "PHASE1_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    fng = fng_table()
    gate, xc, clips, A, allL = [], [], {}, [], []
    btc_ctx = {}
    for coin in ["BTCUSDT"] + [c for c in COINS if c != "BTCUSDT"]:
        bars, n1h, n1d = build_bars(coin, gate, xc, clips)
        h1 = (n1h.timestamp.values, n1h.low.values, n1h.high.values, n1h.quote_volume.values)
        htf_states = {}
        for h in HTF_LIST:
            bh = bars[h]
            htf_states[h] = (end_times(h, bh.timestamp.values), E.zz(bh, KP)["state"])
        for tf in SWING_TFS:
            b = bars[tf]
            fac = base_factors(b)
            if coin == "BTCUSDT":
                btc_ctx[tf] = (b.timestamp.values, fac.ret20.values, E.zz(b, KP)["state"], end_times(tf, b.timestamp.values))
            sup, res = sr_nearest(b)
            btc = None if coin == "BTCUSDT" else btc_ctx[tf]
            for K in KS:
                Lk = legs_for(coin, tf, b, K, fac, sup, res, h1, htf_states, btc, fng)
                allL.append(Lk)
            print(coin, tf, len(b), f"({time.time()-t0:.0f}s)", flush=True)
        A += anatomy(coin, bars["1D"])
    L = pd.concat(allL, ignore_index=True)
    L.to_parquet(DER / "legs_all.parquet", index=False)
    G = pd.DataFrame(gate)
    X = pd.DataFrame(xc)
    G.to_csv(OUT / "gate_D1_splice.csv", index=False)
    X.to_csv(OUT / "gate_D2_crosscheck.csv", index=False)
    claims = dict(protocol_sha256=h_, legs=len(L), D1_all_contiguous=bool(G.contiguous.all()),
                  D2_mismatch_share={c: float(g.mismatched.sum() / max(g.bars.sum(), 1)) for c, g in X.groupby("check")},
                  clipped_wicks={f"{k[0]}|{k[1]}": v for k, v in clips.items() if v})
    claims["D2_pass"] = all(v < 0.01 for v in claims["D2_mismatch_share"].values())
    # D3: re-assert the 1D swing study for BTC (2020+ part of the spliced data) -- done in the verifier on the stored legs
    res = analyse(L, A)
    claims["legs_by_tf_K"] = L.groupby(["tf", "K"]).size().rename("n").reset_index().to_dict("records")
    claims["legs_parquet_sha256"] = hashlib.sha256((DER / "legs_all.parquet").read_bytes()).hexdigest()
    (OUT / "claims_phase1.json").write_text(json.dumps(claims, indent=2, default=str))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 400)
    pd.set_option("display.max_columns", 30)
    print("D1 contiguous:", claims["D1_all_contiguous"], "| D2:", claims["D2_mismatch_share"], claims["D2_pass"])
    print(res["DA"][res["DA"].K == KP].round(3).to_string(index=False))
    print(res["DB"].round(3).to_string(index=False))
    print(res["DC"][res["DC"].robust].round(3).sort_values(["direction", "tf", "rho"]).to_string(index=False))
    print(f"done ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
