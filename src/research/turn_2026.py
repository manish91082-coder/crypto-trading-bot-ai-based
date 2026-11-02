"""TURN-2026: can a BTC turn be caught before the usual confirmation? Protocol logs/turn_detect_2026/TURN_PROTOCOL_PREREGISTERED.md,
conventions logs/turn_detect_2026/CODE_NOTES.md.
Run: python src/research/turn_2026.py disc      (Jan-May only; writes hold_candidates.json)
     python src/research/turn_2026.py hold      (opens Jun-Sep once)"""
import hashlib, io, json, sys, time, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "turn_detect_2026"
PROTO_SHA = (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0]
F1M = [ROOT / f"data/external/binance_1s/futures_1m/BTCUSDT-1m-2026-0{m}.zip" for m in range(1, 10)]
F1S = [ROOT / f"data/external/binance_1s/spot_1s/BTCUSDT-1s-2026-0{m}.zip" for m in range(1, 10)]
CLEAN = ROOT / "data/external/binance_public/clean"
ETH5 = ROOT / "data/universe_hf/5m/ETHUSDT_5m_full.csv.gz"
FEES = json.loads((ROOT / "deploy/fees.json").read_text())
C_TAKER = 2 * FEES["rules"]["paper_futures_taker_per_side"]
C_MAKER = 2 * (FEES["futures_usdm"]["bnb_maker"] + FEES["impact_per_side"])
THETAS = (0.005, 0.01, 0.02, 0.04, 0.08)
FS = (0.25, 0.5, 0.75)
TFS = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "8h": 480, "12h": 720, "1d": 1440}
TFL = list(TFS)
DISC = ("2026-01-01", "2026-06-01")
HOLD = ("2026-06-01", "2026-10-01")
T0 = time.time()


def log(*a):
    s = f"[{time.strftime('%H:%M:%S')} +{time.time() - T0:7.0f}s] " + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(OUT / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(s + "\n")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ data
def load_1m(months):
    parts = []
    for m in months:
        with zipfile.ZipFile(F1M[m - 1]) as z:
            d = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
        parts.append(d[["open_time", "open", "high", "low", "close", "volume", "taker_buy_volume"]])
    d = pd.concat(parts, ignore_index=True)
    d["t"] = pd.to_datetime(d.open_time, unit="ms").astype("datetime64[ns]")
    d = d.drop_duplicates("t").set_index("t").sort_index()
    full = pd.date_range(d.index[0], d.index[-1], freq="1min")
    assert len(full) == len(d), f"1m gaps: {len(full) - len(d)}"
    return d.rename(columns={"taker_buy_volume": "tb", "volume": "v"})[["open", "high", "low", "close", "v", "tb"]]


def load_5m_tables():
    met = pd.read_parquet(CLEAN / "metrics5m.parquet").set_index("time").sort_index()
    pre = pd.read_parquet(CLEAN / "premium5m.parquet").set_index("time").sort_index()
    dep = pd.read_parquet(CLEAN / "depth5m.parquet").set_index("time").sort_index()
    fun = pd.read_parquet(CLEAN / "funding.parquet")
    fun["time"] = pd.to_datetime(fun.time).dt.floor("s")
    fun = fun.set_index("time").sort_index()
    eth = pd.read_csv(ETH5, usecols=["timestamp", "close"])
    eth["timestamp"] = pd.to_datetime(eth.timestamp)
    eth = eth[(eth.timestamp >= "2025-12-01") & (eth.timestamp < "2026-10-01")].drop_duplicates("timestamp").set_index("timestamp")
    tabs = {"oi": met["sum_open_interest"], "lsr": met["sum_toptrader_long_short_ratio"], "prem": pre["close"],
            "imb5": dep["imb5"], "eth": eth["close"]}
    out = {}
    for k, s in tabs.items():                     # usable from stamp + 5 min (CODE_NOTES 10)
        s = s.copy()
        s.index = s.index + pd.Timedelta(minutes=5)
        out[k] = s[~s.index.duplicated()].sort_index()
    out["fund"] = fun["funding_rate"]
    return out


def asof_vals(s, times):
    """value of series s (index = usable-from time) at each time in `times` (last usable <= time)."""
    i = np.searchsorted(s.index.values.astype("datetime64[ns]"), np.asarray(times, dtype="datetime64[ns]"), side="right") - 1
    v = np.where(i >= 0, s.values[np.clip(i, 0, None)], np.nan)
    return v.astype(float)


# ------------------------------------------------------------------ null path (CODE_NOTES 1)
def null_bars(d, seed):
    c = d.close.to_numpy()
    r = np.diff(np.log(c))
    s = np.random.default_rng(seed).choice(np.array([-1.0, 1.0]), size=len(r))
    lc = np.log(c[0]) + np.r_[0.0, np.cumsum(s * r)]
    a = np.log(d.high.to_numpy() / c)
    b = np.log(d.low.to_numpy() / c)
    o = np.log(d.open.to_numpy() / c)
    ss = np.r_[1.0, s]                             # first bar kept as is
    C = np.exp(lc)
    H = C * np.exp(np.where(ss > 0, a, -b))
    L = C * np.exp(np.where(ss > 0, b, -a))
    O = C * np.exp(np.where(ss > 0, o, -o))
    n = d.copy()
    n["open"], n["high"], n["low"], n["close"] = O, H, L, C
    return n


def null_closes(c, seed):
    r = np.diff(np.log(c))
    s = np.random.default_rng(seed).choice(np.array([-1.0, 1.0]), size=len(r))
    return np.exp(np.log(c[0]) + np.r_[0.0, np.cumsum(s * r)])


# ------------------------------------------------------------------ ZigZag + T1 machine (CODE_NOTES 2)
def turn_machine(c, theta, fs=FS):
    """one pass over closes. Returns pivots list and events list.
    pivots: (ext_idx, ext_price, kind(+1 low / -1 high), confirm_idx)
    events: (event_idx, dir, f, L_idx, L_price, prev_pivot_price, outcome(1/0), outcome_idx)"""
    n = len(c)
    piv, ev = [], []
    dirn = 0
    mx = mn = c[0]
    imx = imn = 0
    pend = []                    # pending events for current extreme: [event_idx, f, ext_idx, ext_price, prev_pivot_price]
    fired = set()
    prev_piv_price = np.nan
    for t in range(1, n):
        x = c[t]
        if dirn == 0:
            if x > mx:
                mx, imx = x, t
            if x < mn:
                mn, imn = x, t
            if x >= mn * (1 + theta):
                dirn, ext, iext = 1, x, t
                piv.append((imn, mn, 1, t))
                prev_piv_price = mn
                fired = set()
            elif x <= mx * (1 - theta):
                dirn, ext, iext = -1, x, t
                piv.append((imx, mx, -1, t))
                prev_piv_price = mx
                fired = set()
            continue
        if dirn == -1:                                   # down leg, ext = running low L
            if x < ext:
                for e in pend:                           # new low: pending UP events fail
                    ev.append((e[0], 1, e[1], e[2], e[3], e[4], 0, t))
                pend, fired = [], set()
                ext, iext = x, t
                continue
            if x >= ext * (1 + theta):                   # turn up confirmed
                for e in pend:
                    ev.append((e[0], 1, e[1], e[2], e[3], e[4], 1, t))
                piv.append((iext, ext, 1, t))
                prev_piv_price = ext
                pend, fired = [], set()
                dirn, ext, iext = 1, x, t
                continue
            for f in fs:
                if f not in fired and x >= ext * (1 + f * theta):
                    fired.add(f)
                    pend.append([t, f, iext, ext, prev_piv_price])
        else:                                            # up leg, ext = running high H
            if x > ext:
                for e in pend:
                    ev.append((e[0], -1, e[1], e[2], e[3], e[4], 0, t))
                pend, fired = [], set()
                ext, iext = x, t
                continue
            if x <= ext * (1 - theta):
                for e in pend:
                    ev.append((e[0], -1, e[1], e[2], e[3], e[4], 1, t))
                piv.append((iext, ext, -1, t))
                prev_piv_price = ext
                pend, fired = [], set()
                dirn, ext, iext = -1, x, t
                continue
            for f in fs:
                if f not in fired and x <= ext * (1 - f * theta):
                    fired.add(f)
                    pend.append([t, f, iext, ext, prev_piv_price])
    return piv, ev, len(pend)


# ------------------------------------------------------------------ bootstrap helpers
def day_boot(vals, days, fn=np.mean, B=2000, seed=7):
    vals = np.asarray(vals, float)
    days = np.asarray(days)
    ud, inv = np.unique(days, return_inverse=True)
    groups = [np.where(inv == k)[0] for k in range(len(ud))]
    rng = np.random.default_rng(seed)
    out = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, len(ud), len(ud))
        idx = np.concatenate([groups[k] for k in pick])
        out[b] = fn(vals[idx])
    return out


def auc(score, y):
    ok = np.isfinite(score)
    s, yy = score[ok], y[ok]
    n1, n0 = yy.sum(), (1 - yy).sum()
    if n1 == 0 or n0 == 0:
        return np.nan
    rk = pd.Series(s).rank().to_numpy()
    return float((rk[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def zq(alpha):
    from scipy.stats import norm
    return float(norm.ppf(1 - alpha / 2))


# ------------------------------------------------------------------ bars + indicators
def bars(d, tfm):
    """UTC-anchored TF bars from 1m frame (numpy reduceat). index = bar start."""
    mins = d.index.as_unit("ns").asi8 // 60_000_000_000
    bid = mins // tfm
    starts = np.r_[0, np.flatnonzero(np.diff(bid)) + 1]
    o = d.open.to_numpy()[starts]
    h = np.maximum.reduceat(d.high.to_numpy(), starts)
    l = np.minimum.reduceat(d.low.to_numpy(), starts)
    c = d.close.to_numpy()[np.r_[starts[1:] - 1, len(d) - 1]]
    v = np.add.reduceat(d.v.to_numpy(), starts)
    tb = np.add.reduceat(d.tb.to_numpy(), starts)
    t = pd.DatetimeIndex(pd.to_datetime(bid[starts] * tfm * 60, unit="s"))
    return pd.DataFrame(dict(open=o, high=h, low=l, close=c, v=v, tb=tb), index=t)


def ema(x, n):
    a = 2 / (n + 1)
    y, _ = lfilter([a], [1, -(1 - a)], x, zi=[(1 - a) * x[0]])
    return y


def wma(x, n):
    w = np.arange(1, n + 1, dtype=float)
    y = np.convolve(x, w[::-1] / w.sum(), mode="full")[:len(x)]
    y[:n - 1] = np.nan
    return y


def sgn(x):
    return np.sign(np.nan_to_num(x, nan=0.0))


def slope_sign(y):
    return np.r_[0.0, sgn(np.diff(y))]


def hold_fill(sig):
    """+1/-1 events, 0 = keep previous state."""
    s = pd.Series(np.where(sig == 0, np.nan, sig)).ffill().fillna(0.0)
    return s.to_numpy()


def kalman_slope(lc, q):
    d = np.diff(lc[:501])
    R = (np.median(np.abs(d - np.median(d))) / 0.6745) ** 2 or 1e-12
    Q = q * R
    lev, slo = lc[0], 0.0
    p11, p12, p22 = R, 0.0, R
    out = np.empty(len(lc))
    for t, z in enumerate(lc):
        lev, slo = lev + slo, slo                              # predict
        p11, p12, p22 = p11 + 2 * p12 + p22 + Q, p12 + p22, p22 + Q
        s = p11 + R
        k1, k2 = p11 / s, p12 / s
        e = z - lev
        lev, slo = lev + k1 * e, slo + k2 * e
        p11, p12, p22 = (1 - k1) * p11, (1 - k1) * p12, p22 - k2 * p12
        out[t] = slo
    return np.sign(out)


def linreg_t(lc, n):
    x = np.arange(n, dtype=float)
    xm = x.mean()
    sxx = ((x - xm) ** 2).sum()
    s = pd.Series(lc)
    ym = s.rolling(n).mean().to_numpy()
    w = (x - xm)                                   # rolling sum of (x - xm) * y via convolution
    sxy = np.convolve(lc, w[::-1], mode="full")[:len(lc)]
    sxy[:n - 1] = np.nan
    b = sxy / sxx
    syy = s.rolling(n).var(ddof=0).to_numpy() * n
    rss = np.maximum(syy - b ** 2 * sxx, 1e-30)
    se = np.sqrt(rss / (n - 2) / sxx)
    t = b / se
    return np.where(np.abs(t) > 2, np.sign(t), 0.0)


def cusum_state(r, h):
    sd = pd.Series(r).ewm(span=100, adjust=False).std().shift(1).to_numpy()
    sp = sm = 0.0
    st = 0.0
    out = np.zeros(len(r))
    for t in range(len(r)):
        z = r[t] / sd[t] if sd[t] and np.isfinite(sd[t]) and sd[t] > 0 else 0.0
        sp = max(0.0, sp + z - 0.5)
        sm = max(0.0, sm - z - 0.5)
        if sp > h:
            st, sp, sm = 1.0, 0.0, 0.0
        elif sm > h:
            st, sp, sm = -1.0, 0.0, 0.0
        out[t] = st
    return out


def donchian(b, n):
    hh = b.high.rolling(n).max().shift(1).to_numpy()
    ll = b.low.rolling(n).min().shift(1).to_numpy()
    c = b.close.to_numpy()
    return hold_fill(np.where(c > hh, 1.0, np.where(c < ll, -1.0, 0.0)))


def rsi_state(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean().to_numpy()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean().to_numpy()
    rsi = 100 - 100 / (1 + up / np.where(dn == 0, np.nan, dn))
    rsi = np.where(dn == 0, 100.0, rsi)
    return sgn(rsi - 50)


def boll_fade(c, n=20, k=2):
    s = pd.Series(c)
    m = s.rolling(n).mean().to_numpy()
    sd = s.rolling(n).std(ddof=0).to_numpy()
    pb = (c - (m - k * sd)) / (2 * k * sd)
    return hold_fill(np.where(pb > 1, -1.0, np.where(pb < 0, 1.0, 0.0)))


def heikin(b):
    o, h, l, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    hc = (o + h + l + c) / 4
    ho = np.empty(len(c))
    ho[0] = (o[0] + c[0]) / 2
    for t in range(1, len(c)):
        ho[t] = (ho[t - 1] + hc[t - 1]) / 2
    return sgn(hc - ho)


def fractal_state(b):
    h, l = b.high.to_numpy(), b.low.to_numpy()
    n = len(h)
    st = np.zeros(n)
    ph, pl = [], []
    cur = 0.0
    for t in range(2, n):
        if h[t - 1] > h[t - 2] and h[t - 1] > h[t]:
            ph.append(h[t - 1])
        if l[t - 1] < l[t - 2] and l[t - 1] < l[t]:
            pl.append(l[t - 1])
        if len(ph) >= 2 and len(pl) >= 2:
            if ph[-1] > ph[-2] and pl[-1] > pl[-2]:
                cur = 1.0
            elif ph[-1] < ph[-2] and pl[-1] < pl[-2]:
                cur = -1.0
        st[t] = cur
    return st


def supersmoother(x, p):
    a1 = np.exp(-1.414 * np.pi / p)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / p)
    c2, c3 = b1, -a1 * a1
    c1 = 1 - c2 - c3
    y = lfilter([c1 / 2, c1 / 2], [1, -c2, -c3], x - x[0]) + x[0]
    return y


def price_detectors(b):
    c = b.close.to_numpy()
    lc = np.log(c)
    r = np.r_[0.0, np.diff(lc)]
    D = {}
    for n in (5, 20, 50):
        D[f"P1_EMAslope{n}"] = slope_sign(ema(c, n))
    D["P2_EMAx5_20"] = sgn(ema(c, 5) - ema(c, 20))
    D["P2_EMAx20_50"] = sgn(ema(c, 20) - ema(c, 50))
    for n in (9, 21):
        hm = wma(2 * wma(c, n // 2) - wma(c, n), int(round(np.sqrt(n))))
        D[f"P3_Hull{n}"] = slope_sign(hm)
    for n in (10, 30):
        lag = (n - 1) // 2
        x = 2 * c - np.r_[np.full(lag, c[0]), c[:-lag]]
        D[f"P4_ZLEMA{n}"] = slope_sign(ema(x, n))
    for q, tag in ((1e-2, "1e-2"), (1e-3, "1e-3")):
        D[f"P5_Kalman{tag}"] = kalman_slope(lc, q)
    for n in (20, 50):
        D[f"P6_LinRegT{n}"] = linreg_t(lc, n)
    for h in (4, 8):
        D[f"P7_CUSUMh{h}"] = cusum_state(r, h)
    for n in (20, 55):
        D[f"P8_Donchian{n}"] = donchian(b, n)
    m = ema(c, 12) - ema(c, 26)
    D["P9_MACDhist"] = sgn(m - ema(m, 9))
    D["P10_RSI50"] = rsi_state(c)
    D["P11_BollFade"] = boll_fade(c)
    D["P12_HeikinAshi"] = heikin(b)
    e10 = ema(c, 10)
    D["P13_Curvature"] = np.r_[0.0, 0.0, sgn(e10[2:] - 2 * e10[1:-1] + e10[:-2])]
    D["P14_Fractal"] = fractal_state(b)
    for p in (10, 20):
        D[f"P15_SuperSmooth{p}"] = slope_sign(supersmoother(c, p))
    vote = sum(D[k] for k in ("P1_EMAslope20", "P3_Hull21", "P6_LinRegT20", "P9_MACDhist", "P10_RSI50", "P14_Fractal",
                              "P15_SuperSmooth20"))
    D["M2_Vote7"] = sgn(vote)
    return D


def htf_state_at(b_htf, times):
    """sign(EMA20_k - EMA20_{k-1}) of the last HTF bar closed at or before each time (bar close = start + tf)."""
    st = slope_sign(ema(b_htf.close.to_numpy(), 20))
    s = pd.Series(st, index=b_htf.index + (b_htf.index[1] - b_htf.index[0]) if len(b_htf) > 1 else b_htf.index)
    return asof_vals(s, times)


def flow_detectors(b, tabs, tfm):
    close_t = b.index + pd.Timedelta(minutes=tfm)
    D = {}
    imb = b.tb.to_numpy() / np.where(b.v.to_numpy() > 0, b.v.to_numpy(), np.nan) - 0.5
    D["Q1_TakerImbEMA5"] = sgn(ema(np.nan_to_num(imb), 5))
    oi = asof_vals(tabs["oi"], close_t)
    dp = np.r_[0.0, np.diff(b.close.to_numpy())]
    doi = np.r_[0.0, np.diff(oi)]
    D["Q2_OIxPrice"] = np.where(doi > 0, sgn(dp), 0.0)
    pr = asof_vals(tabs["prem"], close_t)
    D["Q3_PremChange"] = np.r_[0.0, sgn(np.diff(pr))]
    D["Q4_DepthImb5"] = sgn(asof_vals(tabs["imb5"], close_t))
    if tfm >= 60:
        D["Q5_FundContra"] = -sgn(asof_vals(tabs["fund"], close_t))
    eth = asof_vals(tabs["eth"], close_t)
    D["Q6_ETHlead"] = np.r_[0.0, sgn(np.diff(eth))]
    lsr = asof_vals(tabs["lsr"], close_t)
    D["Q7_TopLSRcontra"] = np.r_[0.0, -sgn(np.diff(lsr))]
    return D


def trades_from_state(b, d, start_t=None):
    """position during bar t+1 = d_t. returns arrays dir, entry_i, exit_i, gross (open to open; last at last close)."""
    o = b.open.to_numpy()
    c = b.close.to_numpy()
    pos = np.r_[0.0, d[:-1]]
    n = len(pos)
    chg = np.flatnonzero(np.diff(np.r_[0.0, pos]) != 0)
    ends = np.r_[chg[1:], n]
    dirs = pos[chg]
    m = dirs != 0
    st, en, dr = chg[m], ends[m], dirs[m]
    px_out = np.where(en < n, o[np.minimum(en, n - 1)], c[-1])
    T = pd.DataFrame(dict(dir=dr, i_in=st, i_out=en, gross=dr * (px_out / o[st] - 1)))
    if start_t is not None and len(T):
        T = T[b.index[T.i_in.to_numpy()] >= start_t]
    return T


def accuracy(b, d):
    o = b.open.to_numpy()
    nxt = np.r_[o[2:] / o[1:-1] - 1, np.nan, np.nan]          # open-to-open return of bar t+1
    m = (d != 0) & np.isfinite(nxt) & (nxt != 0)
    return float((np.sign(nxt[m]) == d[m]).mean()) if m.any() else np.nan


# ------------------------------------------------------------------ features (T2)
def build_features(ev, d1, tabs, theta, spot_close_at=None, stair_1s=None):
    """ev: DataFrame of events (on frame d1 indices). Returns DataFrame of F01..F21."""
    c, h, l, v, tb = (d1[k].to_numpy() for k in ("close", "high", "low", "v", "tb"))
    idx = d1.index
    cv = np.r_[0, np.cumsum(v)]
    ctb = np.r_[0, np.cumsum(tb)]
    lr = np.r_[0.0, np.diff(np.log(c))]
    clr2 = np.r_[0, np.cumsum(lr ** 2)]
    clr = np.r_[0, np.cumsum(lr)]
    up_low = np.r_[0, np.cumsum(np.r_[0, (l[1:] > l[:-1]).astype(int)])]
    dn_high = np.r_[0, np.cumsum(np.r_[0, (h[1:] < h[:-1]).astype(int)])]
    e = ev.event_idx.to_numpy()
    L = ev.L_idx.to_numpy()
    dr = ev.dir.to_numpy().astype(float)
    t_close_e = idx[e] + pd.Timedelta(minutes=1)
    t_close_L = idx[L] + pd.Timedelta(minutes=1)
    F = pd.DataFrame(index=ev.index)
    F["F01_bounce_min"] = (e - L).astype(float)
    F["F02_prior_leg"] = np.abs(np.log(ev.L_price.to_numpy() / ev.prev_piv.to_numpy())) / theta
    pre0 = np.clip(L - 60, 0, None)
    vb = (cv[e + 1] - cv[L + 1]) / np.maximum(e - L, 1)
    vp = (cv[L] - cv[pre0]) / np.maximum(L - pre0, 1)
    F["F03_vol_ratio"] = vb / np.where(vp > 0, vp, np.nan)
    F["F04_taker_bounce"] = dr * ((ctb[e + 1] - ctb[L + 1]) / np.maximum(cv[e + 1] - cv[L + 1], 1e-12) - 0.5)
    p15 = np.clip(L - 14, 0, None)
    F["F05_taker_into_ext"] = dr * ((ctb[L + 1] - ctb[p15]) / np.maximum(cv[L + 1] - cv[p15], 1e-12) - 0.5)
    for k, tag, sgnk in (("oi", "F06_oi_change", 1), ("prem", "F07_prem_change", 1), ("lsr", "F21_toplsr_contra", -1)):
        a1 = asof_vals(tabs[k], t_close_e)
        a0 = asof_vals(tabs[k], t_close_L)
        ch = (a1 / a0 - 1) if k in ("oi", "lsr") else (a1 - a0)
        F[tag] = sgnk * dr * ch
    F["F08_fund_contra"] = -dr * asof_vals(tabs["fund"], t_close_e)
    F["F09_depth_imb5"] = dr * asof_vals(tabs["imb5"], t_close_e)
    for tfm, tag in ((60, "F10_htf_1h"), (240, "F11_htf_4h"), (1440, "F12_htf_1d")):
        F[tag] = dr * htf_state_at(bars(d1, tfm), t_close_e)
    nb = np.maximum(e - L, 1)
    stair = np.where(dr > 0, up_low[e + 1] - up_low[L + 1], dn_high[e + 1] - dn_high[L + 1])
    F["F13_stair_1m"] = stair / nb
    ret = np.empty(len(e))
    for j, (Li, Lp) in enumerate(zip(L, ev.L_price.to_numpy())):
        w = c[max(Li - 120, 0):Li]
        ret[j] = np.sum(np.abs(w / Lp - 1) <= 0.1 * theta)
    F["F14_retests"] = ret
    eth1 = asof_vals(tabs["eth"], t_close_e)
    eth0 = asof_vals(tabs["eth"], t_close_L)
    F["F15_eth_lead"] = dr * ((eth1 / eth0 - 1) - (c[e] / c[L] - 1))
    if stair_1s is not None:
        F["F17_stair_1s"] = stair_1s
    else:
        F["F17_stair_1s"] = np.nan
    F["F18_speed"] = ev.f.to_numpy() * theta / nb
    if spot_close_at is not None:
        F["F19_perp_minus_spot"] = dr * ((c[e] / c[L] - 1) - (spot_close_at[:, 1] / spot_close_at[:, 0] - 1))
    else:
        F["F19_perp_minus_spot"] = np.nan
    s24 = np.clip(e - 1440, 0, None)
    m = e - s24
    F["F20_rv24h"] = np.sqrt(np.maximum((clr2[e + 1] - clr2[s24 + 1]) / np.maximum(m, 1) -
                                        ((clr[e + 1] - clr[s24 + 1]) / np.maximum(m, 1)) ** 2, 0))
    return F[sorted(F.columns)]


def spot_features(ev, d1, months):
    """F17 (1s staircase, last 10 min of bounce, 10-s windows) and spot closes at L and event minute ends (F19)."""
    st = np.full(len(ev), np.nan)
    sc = np.full((len(ev), 2), np.nan)
    idx = d1.index
    t_e = (idx[ev.event_idx.to_numpy()] + pd.Timedelta(minutes=1)).as_unit("ns").asi8 // 1_000_000_000
    t_L = (idx[ev.L_idx.to_numpy()] + pd.Timedelta(minutes=1)).as_unit("ns").asi8 // 1_000_000_000
    dr = ev.dir.to_numpy()
    for m in months:
        with zipfile.ZipFile(F1S[m - 1]) as z:
            a = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None, usecols=[0, 2, 3, 4]).to_numpy()
        sec = (a[:, 0] // 1_000_000).astype(np.int64)
        s0 = sec[0]
        n = sec[-1] - s0 + 1
        H = np.full(n, np.nan); Lw = np.full(n, np.nan); C = np.full(n, np.nan)
        H[sec - s0], Lw[sec - s0], C[sec - s0] = a[:, 1], a[:, 2], a[:, 3]
        C = pd.Series(C).ffill().to_numpy()
        H = np.where(np.isnan(H), C, H); Lw = np.where(np.isnan(Lw), C, Lw)
        del a
        inm = (t_e - 1 >= s0) & (t_e - 1 < s0 + n)
        for j in np.flatnonzero(inm):
            end = t_e[j] - s0                       # exclusive end (seconds index of minute end)
            beg = max(t_L[j] - s0, end - 600, 0)          # CODE_NOTES 18: L may lie in the previous month
            if t_L[j] - 1 - s0 >= 0:
                sc[j, 0] = C[t_L[j] - 1 - s0]
            sc[j, 1] = C[end - 1]
            k = (end - beg) // 10
            if k >= 2:
                w0 = end - k * 10
                if dr[j] > 0:
                    lows = Lw[w0:end].reshape(k, 10).min(axis=1)
                    st[j] = np.mean(lows[1:] > lows[:-1])
                else:
                    highs = H[w0:end].reshape(k, 10).max(axis=1)
                    st[j] = np.mean(highs[1:] < highs[:-1])
        log("  1s month", m, "events", int(inm.sum()))
    return st, sc


# ------------------------------------------------------------------ economics
def event_trades(ev, d1, t_lo, t_hi):
    o = d1.open.to_numpy()
    idx = d1.index
    ei, oi = ev.event_idx.to_numpy() + 1, ev.outcome_idx.to_numpy() + 1
    ok = (oi < len(o)) & (idx[np.minimum(ei, len(o) - 1)] >= t_lo) & (idx[np.minimum(oi, len(o) - 1)] < t_hi)
    T = ev[ok].copy()
    T["gross"] = T.dir.to_numpy() * (o[oi[ok]] / o[ei[ok]] - 1)
    T["entry_t"] = idx[ei[ok]]
    T["exit_t"] = idx[oi[ok]]
    return T, int((~ok).sum())


def daily_monthly(T, net_col, t_lo, t_hi, tag):
    days = pd.date_range(t_lo, pd.Timestamp(t_hi) - pd.Timedelta(days=1), freq="D")
    g = T.groupby(T.exit_t.dt.floor("D"))[net_col].agg(["count", "sum"]).reindex(days, fill_value=0)
    g.index.name = "day"
    g.columns = [f"{tag}_n", f"{tag}_sum"]
    return g


# ------------------------------------------------------------------ stages
def stage_disc():
    assert sha(OUT / "TURN_PROTOCOL_PREREGISTERED.md") == PROTO_SHA
    assert not (OUT / "hold_candidates.json").exists(), "DISC already ran (hold_candidates.json exists)"
    log("DISC start; protocol", PROTO_SHA[:12], "taker RT", C_TAKER, "maker RT", C_MAKER)
    man = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in F1M[:5] + F1S[:5] +
           [CLEAN / f for f in ("metrics5m.parquet", "premium5m.parquet", "depth5m.parquet", "funding.parquet")] + [ETH5, ROOT / "deploy/fees.json"]]
    pd.DataFrame(man).to_csv(OUT / "input_manifest_disc.csv", index=False)
    d1 = load_1m(range(1, 6))
    tabs = load_5m_tables()
    log("1m rows", len(d1), d1.index[0], d1.index[-1])
    c = d1.close.to_numpy()
    days = d1.index.floor("D")
    # ---------------- T0
    t0rows, allev = [], {}
    for th in THETAS:
        piv, ev, nopen = turn_machine(c, th)
        P = pd.DataFrame(piv, columns=["ext_idx", "ext_price", "kind", "confirm_idx"])
        lag = P.confirm_idx - P.ext_idx
        leg = np.abs(np.log(P.ext_price.shift(-1) / P.ext_price))
        # follow-confirmed system: always in direction of last confirmed pivot
        o = d1.open.to_numpy()
        ci = P.confirm_idx.to_numpy() + 1
        gr = []
        for k in range(len(ci) - 1):
            if ci[k + 1] < len(o):
                gr.append(P.kind.iloc[k] * (o[ci[k + 1]] / o[ci[k]] - 1))
        gr = np.array(gr)
        t0rows.append(dict(theta=th, pivots=len(P), median_lag_min=float(lag.median()), mean_lag_min=float(lag.mean()),
                           median_leg=float(leg.median()), share_leg_gone_at_confirm_median=float((np.log(1 + th) / leg).median()),
                           follow_trades=len(gr), follow_gross=float(gr.mean()) if len(gr) else np.nan,
                           follow_net_taker=float(gr.mean() - C_TAKER) if len(gr) else np.nan,
                           follow_win=float((gr > C_TAKER).mean()) if len(gr) else np.nan))
        P.to_csv(OUT / f"pivots_disc_theta{th}.csv", index=False)
        E = pd.DataFrame(ev, columns=["event_idx", "dir", "f", "L_idx", "L_price", "prev_piv", "outcome", "outcome_idx"])
        E["theta"] = th
        allev[th] = (E, nopen)
        log("T0 theta", th, "pivots", len(P), "events", len(E), "open at end", nopen)
    pd.DataFrame(t0rows).to_csv(OUT / "T0_lag_cost_disc.csv", index=False)
    # ---------------- T1 real vs null
    t1, null_store = [], {}
    nullP = {(th, f): [] for th in THETAS for f in FS}
    for s in range(1, 101):
        cn = null_closes(c, s)
        for th in THETAS:
            _, evn, _ = turn_machine(cn, th)
            En = np.array(evn, dtype=float) if evn else np.zeros((0, 8))
            for f in FS:
                m = En[:, 2] == f if len(En) else np.zeros(0, bool)
                nullP[(th, f)].append((En[m, 6].mean() if m.any() else np.nan, int(m.sum())))
        if s % 10 == 0:
            log("T1 null paths", s)
    T1trades = []
    for th in THETAS:
        E, _ = allev[th]
        for f in FS:
            e = E[E.f == f]
            pr = float(e.outcome.mean())
            bd = day_boot(e.outcome.to_numpy(), days[e.event_idx.to_numpy()])
            nv = np.array([x[0] for x in nullP[(th, f)]])
            nn = np.array([x[1] for x in nullP[(th, f)]])
            Tt, dropped = event_trades(e, d1, DISC[0], DISC[1])
            Tt["net_taker"] = Tt.gross - C_TAKER
            Tt["net_maker"] = Tt.gross - C_MAKER
            Tt["theta"], Tt["f"] = th, f
            T1trades.append(Tt)
            bn = day_boot(Tt.net_taker.to_numpy(), Tt.exit_t.dt.floor("D").to_numpy()) if len(Tt) else np.array([np.nan])
            bm = day_boot(Tt.net_maker.to_numpy(), Tt.exit_t.dt.floor("D").to_numpy()) if len(Tt) else np.array([np.nan])
            t1.append(dict(theta=th, f=f, n_events=len(e), P_real=pr, P_ci_lo=float(np.percentile(bd, 2.5)), P_ci_hi=float(np.percentile(bd, 97.5)),
                           P_null_mean=float(np.nanmean(nv)), P_null_sd=float(np.nanstd(nv)), n_null_mean=float(nn.mean()),
                           delta=pr - float(np.nanmean(nv)), p_null=float(np.mean(nv >= pr)),
                           p_star_taker=f + C_TAKER / th, p_star_maker=f + C_MAKER / th,
                           n_trades=len(Tt), dropped=dropped, gross=float(Tt.gross.mean()), net_taker=float(Tt.net_taker.mean()),
                           net_taker_lo=float(np.percentile(bn, 2.5)), net_taker_hi=float(np.percentile(bn, 97.5)),
                           net_maker=float(Tt.net_maker.mean()), net_maker_lo=float(np.percentile(bm, 2.5)), net_maker_hi=float(np.percentile(bm, 97.5))))
    T1 = pd.DataFrame(t1)
    T1.to_csv(OUT / "T1_completion_disc.csv", index=False)
    T1tr = pd.concat(T1trades, ignore_index=True)
    T1tr.to_parquet(OUT / "T1_trades_disc.parquet")
    log("T1 done\n" + T1[["theta", "f", "n_events", "P_real", "P_null_mean", "delta", "p_null", "net_taker", "net_taker_lo"]].round(4).to_string())
    # ---------------- T2 features
    T2auc, models, T2taken = [], {}, []
    from sklearn.linear_model import LogisticRegression
    feats_store = []
    for th in THETAS:
        E, _ = allev[th]
        E = E[(E.prev_piv.notna())].reset_index(drop=True)
        st1, sc = spot_features(E, d1, range(1, 6))
        F = build_features(E, d1, tabs, th, spot_close_at=sc, stair_1s=st1)
        F["theta"], F["f"], F["outcome"], F["event_idx"], F["dir"] = th, E.f, E.outcome, E.event_idx, E.dir
        F["day"] = days[E.event_idx.to_numpy()]
        F["month"] = d1.index[E.event_idx.to_numpy()].month
        feats_store.append(F)
        fcols = [k for k in F.columns if k.startswith("F")]
        for f in FS:
            G = F[F.f == f]
            y = G.outcome.to_numpy()
            for k in fcols:
                x = G[k].to_numpy(float)
                a = auc(x, y)
                ok = np.isfinite(x)
                bs = day_boot(np.c_[x[ok], y[ok]], G.day.to_numpy()[ok], fn=lambda z: auc(z[:, 0], z[:, 1]), B=500) if ok.sum() > 20 else np.array([np.nan])
                sd = float(np.nanstd(bs))
                zb = zq(0.05 / 300)
                T2auc.append(dict(theta=th, f=f, feature=k, n=int(ok.sum()), auc=a, boot_sd=sd, lo_bonf=a - zb * sd, hi_bonf=a + zb * sd,
                                  real=bool((a - zb * sd > 0.5) or (a + zb * sd < 0.5))))
            # combined logistic, leave-one-month-out
            Xall = G[fcols].astype(float)
            pstar = f + C_TAKER / th
            pred = np.full(len(G), np.nan)
            for mo in range(1, 6):
                tr, te = G.month != mo, G.month == mo
                if te.sum() == 0 or tr.sum() < 50 or G.outcome[tr].nunique() < 2:
                    continue
                med = Xall[tr].median()
                mu = Xall[tr].fillna(med).mean()
                sdv = Xall[tr].fillna(med).std().replace(0, 1).fillna(1)
                Xt = ((Xall[tr].fillna(med) - mu) / sdv).fillna(0).to_numpy()
                Xe = ((Xall[te].fillna(med) - mu) / sdv).fillna(0).to_numpy()
                lr = LogisticRegression(C=1.0, max_iter=1000).fit(Xt, G.outcome[tr].to_numpy())
                pred[te.to_numpy()] = lr.predict_proba(Xe)[:, 1]
            G = G.assign(p_hat=pred)
            take = G[G.p_hat > pstar]
            Et = E.loc[take.index]
            Tt, _ = event_trades(Et, d1, DISC[0], DISC[1])
            Tt["net_taker"], Tt["net_maker"] = Tt.gross - C_TAKER, Tt.gross - C_MAKER
            Tt["theta"], Tt["f"] = th, f
            T2taken.append(Tt)
            models[(th, f)] = dict(n_events=len(G), n_pred=int(np.isfinite(pred).sum()), n_taken=len(Tt), p_star=pstar,
                                   auc_lomo=auc(pred, G.outcome.to_numpy()),
                                   taken_complete=float(Tt.outcome.mean()) if len(Tt) else np.nan,
                                   net_taker=float(Tt.net_taker.mean()) if len(Tt) else np.nan,
                                   net_maker=float(Tt.net_maker.mean()) if len(Tt) else np.nan)
        log("T2 theta", th, "done")
    pd.concat(feats_store, ignore_index=True).to_parquet(OUT / "T2_features_disc.parquet")
    A = pd.DataFrame(T2auc)
    A.to_csv(OUT / "T2_auc_disc.csv", index=False)
    M = pd.DataFrame([dict(theta=k[0], f=k[1], **v) for k, v in models.items()])
    M.to_csv(OUT / "T2_models_lomo_disc.csv", index=False)
    T2t = pd.concat(T2taken, ignore_index=True) if T2taken else pd.DataFrame()
    T2t.to_parquet(OUT / "T2_taken_trades_disc.parquet")
    log("T2 real features:", int(A.real.sum()), "of", len(A))
    log("T2 models\n" + M.round(4).to_string())
    # ---------------- T3 detectors
    t3 = stage_t3(d1, tabs, period=DISC, seeds=range(1, 21), tag="disc")
    # ---------------- T4 hidden timeframe
    t4 = stage_t4(d1, months=range(1, 6), tag="disc")
    # ---------------- candidates (§8)
    cand = dict(created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), protocol_sha=PROTO_SHA, code_sha=sha(Path(__file__)))
    cand["T2"] = [dict(theta=r.theta, f=r.f) for r in M.itertuples() if r.n_taken >= 30 and r.net_taker > 0]
    cand["T3"] = [dict(tf=r.tf, det=r.det) for r in t3.itertuples() if r.z > 3.5 and r.net_taker > 0 and r.n_trades >= 30]
    cand["T1"] = [dict(theta=r.theta, f=r.f, cost=cst) for r in T1.itertuples() for cst, lo in (("taker", r.net_taker_lo), ("maker", r.net_maker_lo)) if lo > 0]
    cand["T4"] = [dict(q=r.q, unit=r.unit, rule=r.rule) for r in t4.itertuples() if r.flagged and r.net_taker > 0]
    cand["T2_real_features"] = [dict(theta=r.theta, f=r.f, feature=r.feature) for r in A.itertuples() if r.real]
    cand["n_candidates"] = len(cand["T2"]) + len(cand["T3"]) + len(cand["T1"]) + len(cand["T4"])
    # daily / monthly logs for DISC
    dm = [daily_monthly(T1tr[(T1tr.theta == th) & (T1tr.f == f)], "net_taker", *DISC, f"T1_{th}_{f}") for th in THETAS for f in FS]
    if len(T2t):
        dm += [daily_monthly(T2t[(T2t.theta == th) & (T2t.f == f)], "net_taker", *DISC, f"T2_{th}_{f}") for th in THETAS for f in FS]
    D = pd.concat(dm, axis=1)
    D.to_csv(OUT / "daily_disc.csv")
    D.groupby(D.index.to_period("M")).sum().to_csv(OUT / "monthly_disc.csv")
    json.dump(cand, open(OUT / "hold_candidates.json", "w"), indent=1, default=float)
    names = sorted(p.name for p in OUT.iterdir() if p.suffix in (".csv", ".parquet", ".json") and ("disc" in p.name or p.name == "hold_candidates.json"))
    (OUT / "OUTPUT_SHA256_disc.txt").write_text("".join(f"{sha(OUT / x)}  {x}\n" for x in names))
    log("DISC done; candidates", cand["n_candidates"], json.dumps({k: len(v) for k, v in cand.items() if isinstance(v, list)}))


def stage_t3(d1, tabs, period, seeds, tag, only=None):
    t_lo = pd.Timestamp(period[0])
    rows = []
    real_trades = {}
    nulls = {s: null_bars(d1, s) for s in seeds}
    for tf in TFL:
        tfm = TFS[tf]
        b = bars(d1, tfm)
        tf2 = TFL[min(TFL.index(tf) + 2, len(TFL) - 1)]

        def all_dets(bb, dd):
            D = price_detectors(bb)
            b2 = bars(dd, TFS[tf2])
            D["M1_MTF_agree"] = np.where(D["P1_EMAslope5"] == htf_state_at(b2, bb.index + pd.Timedelta(minutes=tfm)), D["P1_EMAslope5"], 0.0)
            if tfm >= 5:
                D.update(flow_detectors(bb, tabs, tfm))
            return D
        Dr = all_dets(b, d1)
        keys = [k for k in Dr if only is None or (tf, k) in only]
        if not keys:
            continue
        nullres = {k: [] for k in keys}
        for s in seeds:
            nb = bars(nulls[s], tfm)
            Dn = all_dets(nb, nulls[s])
            for k in keys:
                T = trades_from_state(nb, Dn[k], t_lo)
                nullres[k].append((T.gross.mean() if len(T) else np.nan, accuracy(nb, Dn[k])))
        for k in keys:
            T = trades_from_state(b, Dr[k], t_lo)
            T["exit_t"] = b.index[np.minimum(T.i_out.to_numpy(), len(b) - 1)]
            T["entry_t"] = b.index[T.i_in.to_numpy()]
            real_trades[(tf, k)] = T
            g = np.array([x[0] for x in nullres[k]], float)
            ac = np.array([x[1] for x in nullres[k]], float)
            gm = T.gross.mean() if len(T) else np.nan
            sd = np.nanstd(g)
            rows.append(dict(tf=tf, det=k, n_trades=len(T), gross=gm, net_taker=gm - C_TAKER, net_maker=gm - C_MAKER,
                             acc=accuracy(b, Dr[k]), null_gross_mean=np.nanmean(g), null_gross_sd=sd,
                             z=(gm - np.nanmean(g)) / sd if sd > 0 else np.nan, null_acc_mean=np.nanmean(ac),
                             mean_hold_bars=float((T.i_out - T.i_in).mean()) if len(T) else np.nan))
        log("T3", tag, tf, "configs", len(keys))
    R = pd.DataFrame(rows)
    R.to_csv(OUT / f"T3_detectors_{tag}.csv", index=False)
    allT = []
    for (tf, k), T in real_trades.items():
        T = T.assign(tf=tf, det=k)
        allT.append(T)
    pd.concat(allT, ignore_index=True).to_parquet(OUT / f"T3_trades_{tag}.parquet")
    return R


def stage_t4(d1, months, tag, only=None):
    rows = []
    qm = [1, 2, 3, 5, 7, 10, 13, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440]
    qs = [1, 2, 3, 5, 7, 10, 15, 20, 30, 45]
    lc = np.log(d1.close.to_numpy())
    r1 = np.diff(lc)
    v1 = r1.var()

    def cells(lcx, qlist, maxph=60):
        out = {}
        base = np.diff(lcx).var()
        for q in qlist:
            for ph in range(min(q, maxph)):
                x = lcx[ph::q]
                rq = np.diff(x)
                if len(rq) < 30:
                    continue
                ac = np.corrcoef(rq[1:], rq[:-1])[0, 1]
                out[(q, ph)] = (rq.var() / (q * base), ac, len(rq))
        return out
    real = cells(lc, qm)
    nullc = [cells(np.log(null_closes(d1.close.to_numpy(), s)), qm) for s in range(1, 101)]
    ncell = len(real)
    # seconds (spot 1s, month by month, pooled via concatenated per-month log prices with month boundaries kept)
    sec_real, sec_null = {}, []
    sec_series = []
    for m in months:
        with zipfile.ZipFile(F1S[m - 1]) as z:
            a = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None, usecols=[0, 4]).to_numpy()
        sec = (a[:, 0] // 1_000_000).astype(np.int64)
        C = np.full(sec[-1] - sec[0] + 1, np.nan)
        C[sec - sec[0]] = a[:, 1]
        sec_series.append(np.log(pd.Series(C).ffill().to_numpy()))
        del a
    for q in qs:
        vr_num = vr_den = 0.0
        rr = []
        for x in sec_series:
            rq = np.diff(x[::q])
            rr.append(rq)
        rq = np.concatenate(rr)
        base = np.concatenate([np.diff(x) for x in sec_series]).var()
        sec_real[q] = (rq.var() / (q * base), np.corrcoef(rq[1:], rq[:-1])[0, 1], len(rq))
    sec_null = {q: [] for q in qs}
    for s in range(1, 101):
        ser = []
        for i, x in enumerate(sec_series):
            r = np.diff(x)
            sg = np.random.default_rng(s * 100 + i).choice(np.array([-1.0, 1.0]), size=len(r))
            ser.append(np.r_[x[0], x[0] + np.cumsum(sg * r)])
        base = np.concatenate([np.diff(x) for x in ser]).var()
        for q in qs:
            rq = np.concatenate([np.diff(x[::q]) for x in ser])
            sec_null[q].append((rq.var() / (q * base), np.corrcoef(rq[1:], rq[:-1])[0, 1]))
        del ser
    del sec_series
    ntot = ncell + len(qs)
    zb = zq(0.05 / ntot)
    for (q, ph), (vr, ac, n) in real.items():
        nv = np.array([nc[(q, ph)][0] for nc in nullc if (q, ph) in nc])
        na = np.array([nc[(q, ph)][1] for nc in nullc if (q, ph) in nc])
        zac = (ac - na.mean()) / na.std()
        zvr = (vr - nv.mean()) / nv.std()
        rows.append(dict(unit="min", q=q, phase=ph, n=n, VR=vr, AC1=ac, null_VR_mean=nv.mean(), null_VR_sd=nv.std(),
                         null_AC1_mean=na.mean(), null_AC1_sd=na.std(), z_AC1=zac, z_VR=zvr, flag_cell=bool(abs(zac) > zb)))
    for q, (vr, ac, n) in sec_real.items():
        nv = np.array([x[0] for x in sec_null[q]]); na = np.array([x[1] for x in sec_null[q]])
        zac = (ac - na.mean()) / na.std()
        rows.append(dict(unit="sec", q=q, phase=0, n=n, VR=vr, AC1=ac, null_VR_mean=nv.mean(), null_VR_sd=nv.std(),
                         null_AC1_mean=na.mean(), null_AC1_sd=na.std(), z_AC1=zac, z_VR=(vr - nv.mean()) / nv.std(),
                         flag_cell=bool(abs(zac) > zb)))
    C4 = pd.DataFrame(rows)
    C4.to_csv(OUT / f"T4_cells_{tag}.csv", index=False)
    # summary per q + economic check for flagged q (phase 0, minutes only; seconds cannot beat a fee: printed)
    summ = []
    o = d1.open.to_numpy()
    for (unit, q), g in C4.groupby(["unit", "q"]):
        flagged = bool(g.flag_cell.any())
        rec = dict(unit=unit, q=q, AC1_phase0=float(g[g.phase == 0].AC1.iloc[0]), AC1_min=float(g.AC1.min()), AC1_med=float(g.AC1.median()),
                   AC1_max=float(g.AC1.max()), VR_phase0=float(g[g.phase == 0].VR.iloc[0]), max_abs_z=float(g.z_AC1.abs().max()),
                   flagged=flagged)
        for rule, sgnr in (("follow", 1.0), ("fade", -1.0)):
            r2 = dict(rec, rule=rule, n_trades=np.nan, gross=np.nan, net_taker=np.nan, net_maker=np.nan)
            if unit == "min" and flagged:
                b = bars(d1, q)
                st = sgnr * np.r_[0.0, sgn(np.diff(b.close.to_numpy()))]
                T = trades_from_state(b, st)
                r2.update(n_trades=len(T), gross=T.gross.mean(), net_taker=T.gross.mean() - C_TAKER, net_maker=T.gross.mean() - C_MAKER)
            summ.append(r2)
    S = pd.DataFrame(summ)
    S.to_csv(OUT / f"T4_summary_{tag}.csv", index=False)
    log("T4 cells", len(C4), "flagged", int(C4.flag_cell.sum()))
    return S


def stage_hold():
    assert sha(OUT / "TURN_PROTOCOL_PREREGISTERED.md") == PROTO_SHA
    cand = json.loads((OUT / "hold_candidates.json").read_text())
    assert not (OUT / "HOLD_OPENED.txt").exists(), "HOLD already opened once"
    (OUT / "HOLD_OPENED.txt").write_text(f"opened_utc {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\ncandidates_sha {sha(OUT / 'hold_candidates.json')}\n")
    log("HOLD start; candidates", cand["n_candidates"])
    man = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in F1M + F1S[5:]]
    pd.DataFrame(man).to_csv(OUT / "input_manifest_hold.csv", index=False)
    d1 = load_1m(range(1, 10))
    tabs = load_5m_tables()
    t_lo, t_hi = pd.Timestamp(HOLD[0]), pd.Timestamp(HOLD[1])
    i0 = int(np.searchsorted(d1.index.values, np.datetime64(t_lo)))
    dh = d1.iloc[i0:]
    c = dh.close.to_numpy()
    days = dh.index.floor("D")
    k = max(cand["n_candidates"], 1)
    zb = zq(0.05 / k)
    res = {"T1": [], "T2": [], "T3": [], "T4": [], "T1_report": [], "T2_feature_report": []}
    allev = {}
    for th in THETAS:
        _, ev, nopen = turn_machine(c, th)
        E = pd.DataFrame(ev, columns=["event_idx", "dir", "f", "L_idx", "L_price", "prev_piv", "outcome", "outcome_idx"])
        for col in ("event_idx", "L_idx", "outcome_idx"):
            E[col] = E[col] + i0                      # indices on the full frame d1
        allev[th] = E
    # report-only T1 completion real vs null on HOLD
    nullP = {(th, f): [] for th in THETAS for f in FS}
    for s in range(1, 101):
        cn = null_closes(c, s)
        for th in THETAS:
            _, evn, _ = turn_machine(cn, th)
            En = np.array(evn, dtype=float) if evn else np.zeros((0, 8))
            for f in FS:
                m = En[:, 2] == f if len(En) else np.zeros(0, bool)
                nullP[(th, f)].append(En[m, 6].mean() if m.any() else np.nan)
    for th in THETAS:
        for f in FS:
            e = allev[th][allev[th].f == f]
            nv = np.array(nullP[(th, f)])
            res["T1_report"].append(dict(theta=th, f=f, n=len(e), P_real=float(e.outcome.mean()), P_null=float(np.nanmean(nv)),
                                         p_null=float(np.mean(nv >= e.outcome.mean()))))
    rng = np.random.default_rng(20261027)

    def judge(T, extra):
        n = len(T)
        if n == 0:
            return dict(n=0, passed=False, **extra)
        bs = day_boot(T.net.to_numpy(), T.exit_t.dt.floor("D").to_numpy())
        mean = float(T.net.mean())
        lo = mean - zb * float(np.std(bs))
        mon = T.groupby(T.exit_t.dt.month).net.sum()
        pos_m = int((mon.reindex(range(6, 10), fill_value=0) > 0).sum())
        return dict(n=n, mean_net=mean, ci_lo_bonf=lo, pos_months=pos_m, **extra,
                    passed=bool(n >= 30 and mean > 0 and lo > 0 and pos_m >= 3 and extra.get("control_ok", False)))
    # T1 candidates
    for cnd in cand["T1"]:
        th, f, cost = cnd["theta"], cnd["f"], cnd["cost"]
        e = allev[th][allev[th].f == f]
        T, _ = event_trades(e, d1, t_lo, t_hi)
        cc = C_TAKER if cost == "taker" else C_MAKER
        T["net"] = T.gross - cc
        # random-take control (CODE_NOTES 6)
        cls = d1.close.to_numpy()
        o = d1.open.to_numpy()
        means = []
        for _ in range(1000):
            st = rng.integers(i0, len(cls) - 2, len(T))
            dr = rng.choice(np.array([-1, 1]), len(T))
            nets = []
            for s0, dd in zip(st, dr):
                p0 = cls[s0]
                tp, sl = p0 * (1 + dd * (1 - f) * th), p0 * (1 - dd * f * th)
                j = s0 + 1
                while j < len(cls) - 1:
                    x = cls[j]
                    if (dd > 0 and (x >= tp or x <= sl)) or (dd < 0 and (x <= tp or x >= sl)):
                        break
                    j += 1
                nets.append(dd * (o[min(j + 1, len(o) - 1)] / o[s0 + 1] - 1) - cc)
            means.append(np.mean(nets))
        p = float(np.mean(np.array(means) >= T.net.mean())) if len(T) else 1.0
        res["T1"].append(judge(T, dict(theta=th, f=f, cost=cost, control_p=p, control_ok=p < 0.05)))
        T.assign(theta=th, f=f, cost=cost).to_parquet(OUT / f"HOLD_trades_T1_{th}_{f}_{cost}.parquet")
    # T2 candidates (+ report-only real features)
    if cand["T2"] or cand["T2_real_features"]:
        from sklearn.linear_model import LogisticRegression
        FD = pd.read_parquet(OUT / "T2_features_disc.parquet")
        need = sorted({c_["theta"] for c_ in cand["T2"]} | {c_["theta"] for c_ in cand["T2_real_features"]})
        for th in need:
            E = allev[th]
            E = E[E.prev_piv.notna()].reset_index(drop=True)
            st1, sc = spot_features(E, d1, range(6, 10))
            F = build_features(E, d1, tabs, th, spot_close_at=sc, stair_1s=st1)
            F["f"], F["outcome"] = E.f, E.outcome
            fcols = [k_ for k_ in F.columns if k_.startswith("F")]
            for rf in [x for x in cand["T2_real_features"] if x["theta"] == th]:
                G = F[F.f == rf["f"]]
                res["T2_feature_report"].append(dict(theta=th, f=rf["f"], feature=rf["feature"], auc_hold=auc(G[rf["feature"]].to_numpy(float), G.outcome.to_numpy())))
            for cnd in [x for x in cand["T2"] if x["theta"] == th]:
                f = cnd["f"]
                GD = FD[(FD.theta == th) & (FD.f == f)]
                X = GD[fcols].astype(float)
                med = X.median(); mu = X.fillna(med).mean(); sdv = X.fillna(med).std().replace(0, 1).fillna(1)
                lr = LogisticRegression(C=1.0, max_iter=1000).fit(((X.fillna(med) - mu) / sdv).fillna(0).to_numpy(), GD.outcome.to_numpy())
                G = F[F.f == f]
                ph = lr.predict_proba(((G[fcols].astype(float).fillna(med) - mu) / sdv).fillna(0).to_numpy())[:, 1]
                take = G.index[ph > f + C_TAKER / th]
                T, _ = event_trades(E.loc[take], d1, t_lo, t_hi)
                Tall, _ = event_trades(E.loc[G.index], d1, t_lo, t_hi)
                T["net"] = T.gross - C_TAKER
                Tall["net"] = Tall.gross - C_TAKER
                means = [Tall.net.sample(len(T), random_state=int(s_)).mean() for s_ in rng.integers(0, 2**31, 1000)] if 0 < len(T) <= len(Tall) else [np.inf]
                p = float(np.mean(np.array(means) >= T.net.mean())) if len(T) else 1.0
                res["T2"].append(judge(T, dict(theta=th, f=f, control_p=p, control_ok=p < 0.05)))
                T.assign(theta=th, f=f).to_parquet(OUT / f"HOLD_trades_T2_{th}_{f}.parquet")
    # T3 candidates
    if cand["T3"]:
        only = {(x["tf"], x["det"]) for x in cand["T3"]}
        R = stage_t3(d1, tabs, period=HOLD, seeds=range(1, 21), tag="hold", only=only)
        TT = pd.read_parquet(OUT / "T3_trades_hold.parquet")
        for r in R.itertuples():
            T = TT[(TT.tf == r.tf) & (TT.det == r.det)].copy()
            T["net"] = T.gross - C_TAKER
            res["T3"].append(judge(T, dict(tf=r.tf, det=r.det, z=r.z, control_ok=bool(r.z > 2))))
    # T4 candidates
    for cnd in cand["T4"]:
        b = bars(d1, int(cnd["q"]))
        sg = 1.0 if cnd["rule"] == "follow" else -1.0
        T = trades_from_state(b, sg * np.r_[0.0, sgn(np.diff(b.close.to_numpy()))], t_lo)
        T["exit_t"] = b.index[np.minimum(T.i_out.to_numpy(), len(b) - 1)]
        T["net"] = T.gross - C_TAKER
        res["T4"].append(judge(T, dict(q=cnd["q"], rule=cnd["rule"], control_ok=True)))
    for k_, v in res.items():
        pd.DataFrame(v).to_csv(OUT / f"HOLD_{k_}.csv", index=False)
    summ = dict(protocol_sha=PROTO_SHA, code_sha=sha(Path(__file__)), k=k, z_bonf=zb,
                passed={k_: [x for x in v if x.get("passed")] for k_, v in res.items() if k_ in ("T1", "T2", "T3", "T4")})
    json.dump(summ, open(OUT / "HOLD_RESULTS.json", "w"), indent=1, default=float)
    names = sorted(p.name for p in OUT.iterdir() if p.name.startswith("HOLD") or "hold" in p.name)
    (OUT / "OUTPUT_SHA256_hold.txt").write_text("".join(f"{sha(OUT / x)}  {x}\n" for x in names if x != "OUTPUT_SHA256_hold.txt"))
    log("HOLD done", json.dumps({k_: len(v) for k_, v in summ["passed"].items()}))


if __name__ == "__main__":
    {"disc": stage_disc, "hold": stage_hold}[sys.argv[1]]()
