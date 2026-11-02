"""Master test bench + Batch 1 (A1 trend, A2 oscillators) on BTC
(logs/research_methods_bench/MASTER_BENCH_PROTOCOL_PREREGISTERED.md, locked before results).
Run: python src/research/methods_bench.py batch1"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ / "src" / "research"))
import btc_entry_study as B                                    # verified engine: load, outcomes cache, simulate, stats, controls

OUT = PROJ / "logs" / "research_methods_bench"
PROTO = OUT / "MASTER_BENCH_PROTOCOL_PREREGISTERED.md"
SCALES = {"15m": "15min", "1h": "1h", "4h": "4h"}
EXITS = {"X1": "V2", "X2": "A1_1", "X3": "REV"}
CAP = B.CAP


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


assert sha(PROTO) == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"


# ------------------------------------------------------------------ scale aggregation (no lookahead)
def agg(d, rule):
    a = d.resample(rule, label="right", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last",
                                                             "volume": "sum", "taker_buy_base": "sum"})
    return a.dropna(subset=["open", "high", "low", "close"])


def to5m(x, d):
    """scale series indexed by its completion time T -> value at every 5m decision bar whose close (open + 5m) is >= T."""
    x = pd.Series(x)
    return x.reindex(d.index + pd.Timedelta(minutes=5), method="ffill").set_axis(d.index).values


# ------------------------------------------------------------------ indicator primitives
def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def wma(s, n):
    w = np.arange(1, n + 1, dtype=float)
    return s.rolling(n, min_periods=n).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)


def wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(c, n=14):
    dl = c.diff()
    au, ad = wilder(dl.clip(lower=0), n), wilder((-dl).clip(lower=0), n)
    return 100 - 100 / (1 + au / ad)


def atr(a, n):
    pc = a.close.shift(1)
    tr = pd.concat([a.high - a.low, (a.high - pc).abs(), (a.low - pc).abs()], axis=1).max(axis=1)
    return wilder(tr, n), tr


def kama(c, n=10, fast=2, slow=30):
    ch = (c - c.shift(n)).abs()
    vol = c.diff().abs().rolling(n).sum()
    er = (ch / vol).fillna(0).values
    sc = (er * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    cv = c.values
    out = np.full(len(cv), np.nan)
    k = n
    if len(cv) > n:
        out[k] = cv[k]
        for i in range(k + 1, len(cv)):
            out[i] = out[i - 1] + sc[i] * (cv[i] - out[i - 1])
    return pd.Series(out, index=c.index)


def psar(a, step=0.02, mx=0.2):
    h, l = a.high.values, a.low.values
    n = len(h)
    sar = np.full(n, np.nan); up = True; af = step; ep = h[0]; s = l[0]
    for i in range(1, n):
        s = s + af * (ep - s)
        if up:
            s = min(s, l[i - 1], l[i - 2] if i >= 2 else l[i - 1])
            if l[i] < s:
                up, s, ep, af = False, ep, l[i], step
            elif h[i] > ep:
                ep, af = h[i], min(mx, af + step)
        else:
            s = max(s, h[i - 1], h[i - 2] if i >= 2 else h[i - 1])
            if h[i] > s:
                up, s, ep, af = True, ep, h[i], step
            elif l[i] < ep:
                ep, af = l[i], min(mx, af + step)
        sar[i] = s
    return pd.Series(sar, index=a.index)


def supertrend(a, n=10, m=3.0):
    at, _ = atr(a, n)
    hl2 = (a.high + a.low) / 2
    ub, lb = (hl2 + m * at).values, (hl2 - m * at).values
    c = a.close.values
    fu, fl = ub.copy(), lb.copy()
    dirn = np.zeros(len(c))
    for i in range(1, len(c)):
        if np.isnan(ub[i]):
            continue
        fu[i] = ub[i] if (np.isnan(fu[i - 1]) or ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (np.isnan(fl[i - 1]) or lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        prev = dirn[i - 1] if dirn[i - 1] != 0 else 1
        dirn[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else prev) if not np.isnan(fu[i - 1]) else 0
    return pd.Series(dirn, index=a.index)


def heikin(a):
    hc = ((a.open + a.high + a.low + a.close) / 4).values
    ho = np.full(len(hc), np.nan)
    ho[0] = (a.open.values[0] + a.close.values[0]) / 2
    for i in range(1, len(hc)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    g = hc > ho
    return pd.Series(np.where(g & np.r_[False, g[:-1]], 1, np.where(~g & np.r_[False, ~g[:-1]], -1, 0)), index=a.index)


def fisher(a, n=10):
    med = ((a.high + a.low) / 2)
    hh, ll = med.rolling(n).max(), med.rolling(n).min()
    x = (2 * ((med - ll) / (hh - ll) - 0.5)).values
    v, f = np.zeros(len(x)), np.zeros(len(x))
    for i in range(1, len(x)):
        xi = 0.0 if np.isnan(x[i]) else x[i]
        v[i] = min(0.999, max(-0.999, 0.33 * xi + 0.67 * v[i - 1]))
        f[i] = 0.5 * np.log((1 + v[i]) / (1 - v[i])) + 0.5 * f[i - 1]
    f = pd.Series(f, index=a.index)
    f[hh.isna().values] = np.nan
    return f


def connors(c):
    st = np.zeros(len(c)); dc = c.diff().values
    for i in range(1, len(c)):
        st[i] = (st[i - 1] + 1 if st[i - 1] > 0 else 1) if dc[i] > 0 else ((st[i - 1] - 1 if st[i - 1] < 0 else -1) if dc[i] < 0 else 0)
    roc = c.pct_change()
    pr = roc.rolling(100).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
    return (rsi(c, 3) + rsi(pd.Series(st, index=c.index), 2) + pr) / 3


def renko_dir(c5, brick):
    """direction of the last completed Renko brick on 5m closes (bricks of `brick` x the last brick price)."""
    cv = c5.values
    out = np.zeros(len(cv)); ref = np.nan; dirn = 0
    for i in range(len(cv)):
        x = cv[i]
        if np.isnan(x):
            out[i] = dirn; continue
        if np.isnan(ref):
            ref = x
        while x >= ref * (1 + brick):
            ref *= (1 + brick); dirn = 1
        while x <= ref * (1 - brick):
            ref *= (1 - brick); dirn = -1
        out[i] = dirn
    return out


def zs(s, n=500):
    return (s - s.rolling(n, min_periods=n // 2).mean()) / s.rolling(n, min_periods=n // 2).std()


def sgn(x):
    return np.where(np.isfinite(x), np.sign(x), 0)


# ------------------------------------------------------------------ Batch 1 rules on one scale frame
def batch1_rules(a):
    c, h, l, o, v = a.close, a.high, a.low, a.open, a.volume
    R = {}
    for nm, ma in (("SMA", c.rolling(50, min_periods=50).mean()), ("EMA", ema(c, 50)),
                   ("HMA", wma(2 * wma(c, 25) - wma(c, 50), 7)), ("KAMA", kama(c))):
        R[f"A1.01_{nm}50"] = np.where(ma.notna(), np.where(c > ma, 1, -1), 0)
    e20, e50 = ema(c, 20), ema(c, 50)
    R["A1.02_EMA20x50"] = np.where(e50.notna(), np.where(e20 > e50, 1, -1), 0)
    macd = ema(c, 12) - ema(c, 26); sig = macd.ewm(span=9, adjust=False, min_periods=9).mean()
    R["A1.03a_MACDhist"] = np.where(sig.notna(), np.where(macd > sig, 1, -1), 0)
    R["A1.03b_MACDline"] = np.where(macd.notna(), np.where(macd > 0, 1, -1), 0)
    at14, tr = atr(a, 14)
    upm, dnm = h.diff(), -l.diff()
    pdm = pd.Series(np.where((upm > dnm) & (upm > 0), upm, 0.0), index=a.index); mdm = pd.Series(np.where((dnm > upm) & (dnm > 0), dnm, 0.0), index=a.index)
    pdi, mdi = 100 * wilder(pdm, 14) / at14, 100 * wilder(mdm, 14) / at14
    adx = wilder(100 * (pdi - mdi).abs() / (pdi + mdi), 14)
    R["A1.04_ADX"] = np.where(adx > 25, np.where(pdi > mdi, 1, np.where(mdi > pdi, -1, 0)), 0)
    hi_age = h.rolling(26).apply(lambda x: 25 - np.argmax(x), raw=True); lo_age = l.rolling(26).apply(lambda x: 25 - np.argmin(x), raw=True)
    au, ad = 100 * (25 - hi_age) / 25, 100 * (25 - lo_age) / 25
    R["A1.05_Aroon"] = np.where((au > 70) & (ad < 30), 1, np.where((ad > 70) & (au < 30), -1, 0))
    sar = psar(a)
    R["A1.06_PSAR"] = np.where(sar.notna(), np.where(c > sar, 1, -1), 0)
    R["A1.07_Supertrend"] = supertrend(a).values
    tenk = (h.rolling(9).max() + l.rolling(9).min()) / 2; kij = (h.rolling(26).max() + l.rolling(26).min()) / 2
    sa = ((tenk + kij) / 2).shift(26); sb = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    R["A1.08_Ichimoku"] = np.where((c > top) & (tenk > kij), 1, np.where((c < bot) & (tenk < kij), -1, 0))
    R["A1.09_Donchian20"] = np.where(c > h.shift(1).rolling(20).max(), 1, np.where(c < l.shift(1).rolling(20).min(), -1, 0))
    at10, _ = atr(a, 10)
    R["A1.10_Keltner"] = np.where(c > e20 + 2 * at10, 1, np.where(c < e20 - 2 * at10, -1, 0))
    tt = pd.Series(np.arange(len(c), dtype=float), index=a.index)
    slope = c.rolling(20).cov(tt) / tt.rolling(20).var()
    R["A1.11_LinRegSlope20"] = sgn(slope.values)
    vmp, vmm = (h - l.shift(1)).abs(), (l - h.shift(1)).abs()
    vip, vim = vmp.rolling(14).sum() / tr.rolling(14).sum(), vmm.rolling(14).sum() / tr.rolling(14).sum()
    R["A1.13_Vortex"] = np.where(vip.notna(), np.where(vip > vim, 1, -1), 0)
    trix = ema(ema(ema(c, 15), 15), 15).pct_change() * 100
    R["A1.14a_TRIX"] = sgn(trix.values)
    roc = lambda n: c.pct_change(n) * 100
    kst = roc(10).rolling(10).mean() + 2 * roc(15).rolling(10).mean() + 3 * roc(20).rolling(10).mean() + 4 * roc(30).rolling(15).mean()
    R["A1.14b_KST"] = np.where(kst.notna(), np.where(kst > kst.rolling(9).mean(), 1, -1), 0)
    R["A1.15_HeikinAshi"] = heikin(a).values
    R["A1.17_TSMOM20"] = sgn((c / c.shift(20) - 1).values)
    er = (c - c.shift(10)).abs() / c.diff().abs().rolling(10).sum()
    R["A1.18_KaufmanER"] = np.where(er > 0.5, sgn((c - c.shift(10)).values), 0)
    chop = 100 * np.log10(tr.rolling(14).sum() / (h.rolling(14).max() - l.rolling(14).min())) / np.log10(14)
    R["A1.19_Choppiness"] = np.where(chop < 38.2, sgn(e20.diff().values), 0)
    # ---- A2 (fade as defined; follow added by the caller)
    r14 = rsi(c, 14)
    R["A2.01a_RSI14"] = np.where(r14 < 30, 1, np.where(r14 > 70, -1, 0))
    crsi = connors(c)
    R["A2.01b_ConnorsRSI"] = np.where(crsi < 10, 1, np.where(crsi > 90, -1, 0))
    k_raw = 100 * (c - l.rolling(14).min()) / (h.rolling(14).max() - l.rolling(14).min())
    K = k_raw.rolling(3).mean(); D = K.rolling(3).mean()
    R["A2.02a_Stoch"] = np.where((K < 20) & (K > D) & (K.shift(1) <= D.shift(1)), 1, np.where((K > 80) & (K < D) & (K.shift(1) >= D.shift(1)), -1, 0))
    srsi = (r14 - r14.rolling(14).min()) / (r14.rolling(14).max() - r14.rolling(14).min())
    sk = srsi.rolling(3).mean()
    R["A2.02b_StochRSI"] = np.where(sk < 0.2, 1, np.where(sk > 0.8, -1, 0))
    wr = -100 * (h.rolling(14).max() - c) / (h.rolling(14).max() - l.rolling(14).min())
    R["A2.03_WilliamsR"] = np.where(wr < -80, 1, np.where(wr > -20, -1, 0))
    tp = (h + l + c) / 3
    mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - tp.rolling(20).mean()) / (0.015 * mad)
    R["A2.04_CCI20"] = np.where(cci < -100, 1, np.where(cci > 100, -1, 0))
    dc = c.diff(); su, sd = dc.clip(lower=0).rolling(14).sum(), (-dc).clip(lower=0).rolling(14).sum()
    cmo = 100 * (su - sd) / (su + sd)
    R["A2.05a_CMO"] = np.where(cmo < -50, 1, np.where(cmo > 50, -1, 0))
    pc = c.shift(1)
    bp = c - np.fmin(l, pc); trr = np.fmax(h, pc) - np.fmin(l, pc)
    uo = 100 * (4 * bp.rolling(7).sum() / trr.rolling(7).sum() + 2 * bp.rolling(14).sum() / trr.rolling(14).sum() + bp.rolling(28).sum() / trr.rolling(28).sum()) / 7
    R["A2.05b_UltOsc"] = np.where(uo < 30, 1, np.where(uo > 70, -1, 0))
    rf = tp * v; pos = rf.where(tp > tp.shift(1), 0.0).rolling(14).sum(); neg = rf.where(tp < tp.shift(1), 0.0).rolling(14).sum()
    mfi = 100 - 100 / (1 + pos / neg)
    R["A2.06a_MFI"] = np.where(mfi < 20, 1, np.where(mfi > 80, -1, 0))
    bop = ((c - o) / (h - l)).replace([np.inf, -np.inf], np.nan).rolling(14).mean()
    R["A2.06b_BOP"] = -sgn(bop.values)                                  # "fade" = opposite of pressure; follow = pressure
    rz = zs(c.pct_change(10))
    R["A2.07_ROCz"] = np.where(rz < -2, 1, np.where(rz > 2, -1, 0))
    m20, s20 = c.rolling(20).mean(), c.rolling(20).std(ddof=0)
    R["A2.08_Bollinger"] = np.where(c < m20 - 2 * s20, 1, np.where(c > m20 + 2 * s20, -1, 0))
    fs = fisher(a)
    R["A2.11_Fisher"] = np.where((fs < -1.5) & (fs > fs.shift(1)), 1, np.where((fs > 1.5) & (fs < fs.shift(1)), -1, 0))
    dz = zs(c - c.rolling(20).mean().shift(11))
    R["A2.12_DPO"] = np.where(dz < -2, 1, np.where(dz > 2, -1, 0))
    med = (h + l) / 2
    ao = med.rolling(5).mean() - med.rolling(34).mean()
    R["A2.13_AwesomeOsc"] = -sgn(ao.values)                             # fade = opposite of the momentum reading
    e13 = ema(c, 13)
    R["A2.14a_ElderRay"] = -np.where((h - e13 > 0) & (e13 > e13.shift(1)), 1, np.where((l - e13 < 0) & (e13 < e13.shift(1)), -1, 0))
    fi = ema(c.diff() * v, 13)
    R["A2.14b_ForceIndex"] = -sgn(fi.values)
    cop = wma(c.pct_change(14) * 100 + c.pct_change(11) * 100, 10)
    R["A2.15a_Coppock"] = -sgn(cop.values)
    dd_ = c.diff()
    tsi = 100 * ema(ema(dd_, 25), 13) / ema(ema(dd_.abs(), 25), 13)
    R["A2.15b_TSI"] = -np.where(tsi.notna(), np.where(tsi > ema(tsi, 7), 1, -1), 0)
    vw = (tp * v).rolling(20).sum() / v.rolling(20).sum()
    vz = zs(c - vw)
    R["A2.17_VWAPz"] = np.where(vz < -2, 1, np.where(vz > 2, -1, 0))
    return {k: np.nan_to_num(np.asarray(x, dtype=float)).astype(np.int8) for k, x in R.items()}


def batch1_signals(d):
    S = {}
    for sn, rule in SCALES.items():
        a = agg(d, rule)
        R = batch1_rules(a)
        for k, x in R.items():
            s5 = to5m(pd.Series(x, index=a.index), d)
            s5 = np.nan_to_num(s5).astype(np.int8)
            if k.startswith("A2"):
                S[f"{k}_fade_{sn}"] = s5
                S[f"{k}_follow_{sn}"] = (-s5).astype(np.int8)
            else:
                S[f"{k}_{sn}"] = s5
    for br in (0.005, 0.01, 0.02):
        S[f"A1.16_Renko{br * 100:g}pct"] = renko_dir(d.close, br).astype(np.int8)
    return S


# ------------------------------------------------------------------ X3 signal-reversal exit
def sim_reversal(dirn, d, cost, cum_f, rng_, longs_only=False):
    i0, i1 = rng_
    O, C = d.open.values, pd.Series(d.close.values).ffill().values
    N = len(O)
    nxt = {}
    for s in (1, -1):                                                  # next bar index (>= i) where dirn == s
        idx = np.where(dirn == s, np.arange(N), N)
        nxt[s] = np.minimum.accumulate(idx[::-1])[::-1]
    t_, d_, g_, x_ = [], [], [], []
    t = i0; free = i0
    cand = np.flatnonzero(dirn[i0:i1] != 0) + i0
    if longs_only:
        cand = cand[dirn[cand] > 0]
    for t in cand:
        if t < free:
            continue
        dd = int(dirn[t])
        e = O[t + 1] if t + 1 < N else np.nan
        if not np.isfinite(e):
            continue
        k = nxt[-dd][t + 1] if t + 1 < N else N
        if k < N and k <= t + CAP:
            xbar = k + 1 if k + 1 < N else k
            px = O[xbar] if np.isfinite(O[xbar]) else C[k]
            ex = k
        else:
            ex = min(N - 1, t + CAP); px = C[ex]
        g = dd * (px / e - 1)
        t_.append(t); d_.append(dd); g_.append(g); x_.append(ex)
        free = ex
    t = np.array(t_, dtype=np.int64); dr = np.array(d_, dtype=np.int8); g = np.array(g_); x = np.array(x_, dtype=np.int64)
    fund = (cum_f[x] - cum_f[t]) * dr if (cum_f is not None and len(t)) else np.zeros(len(t))
    return dict(t=t, dir=dr, gross=g, net=g - cost - fund, exit=x, why=np.zeros(len(t)))


# ------------------------------------------------------------------ equity and reports
def equity_reports(tr, d, start, end):
    days = pd.date_range(start, end, freq="D")
    if len(tr["t"]) == 0:
        e = pd.Series(10_000.0, index=days)
        return e, pd.DataFrame(dict(n=0, net_sum=0.0), index=days)
    xt = d.index[np.minimum(tr["exit"], len(d) - 1)].normalize()
    df = pd.DataFrame(dict(day=xt, net=tr["net"]))
    g = df.groupby("day").net
    fac = g.apply(lambda x: float(np.prod(1 + x.values)))
    daily = pd.DataFrame(dict(n=g.size(), net_sum=g.sum())).reindex(days).fillna(0)
    e = 10_000.0 * fac.reindex(days).fillna(1.0).cumprod()
    return e, daily


def metrics(tr, d, e):
    net = tr["net"]
    if len(net) < 2:
        return dict(n=int(len(net)))
    st = B.week_stats(net, tr["t"], d.index)
    pf = float(net[net > 0].sum() / -net[net < 0].sum()) if (net < 0).any() else np.inf
    m = e.resample("ME").last(); mr = m.pct_change().dropna()
    if len(m):
        mr = pd.concat([pd.Series([m.iloc[0] / 10_000.0 - 1], index=[m.index[0]]), mr])
    yrs = max((e.index[-1] - e.index[0]).days / 365.25, 1e-9)
    return dict(**st, pf=pf, cagr=float((e.iloc[-1] / 10_000.0) ** (1 / yrs) - 1), maxdd=float((e / e.cummax() - 1).min()),
                pos_months=float((mr > 0).mean()), worst_month=float(mr.min()), tp_rate=float((tr["why"] == 1).mean()))


# ------------------------------------------------------------------ fast random control (CODE_NOTES 1, 2)
def fast_control(n, p_long, i0, i1, cost, cum_f, seeds=200, oc=None, holds=None, d=None, chunk=4000):
    """oc given: barrier exits (X1/X2), identical to btc_entry_study.random_control. holds given: X3 control (CODE_NOTES 2)."""
    if oc is not None:
        rl, rs, xl, xs = oc["ret_long"], oc["ret_short"], oc["exit_long"], oc["exit_short"]
    else:
        O, C = d.open.values, pd.Series(d.close.values).ffill().values
    means = []
    bars = np.arange(i0, i1)
    for sd in range(seeds):
        rng = np.random.default_rng(sd)
        order = rng.permutation(bars)
        if holds is not None:
            hp = rng.permutation(np.asarray(holds, dtype=np.int64))
        occ = np.zeros(len(cum_f) + CAP + 2, dtype=np.int32)          # occupied bars of accepted trades
        nets, pos = [], 0
        while len(nets) < n and pos < len(order):
            ts = order[pos:pos + chunk]
            u = rng.random(len(ts))                                   # the same stream as one draw per candidate
            dd = np.where(u < p_long, 1, -1)
            if oc is not None:
                g = np.where(dd > 0, rl[ts], rs[ts]); x = np.where(dd > 0, xl[ts], xs[ts])
            else:
                hh = hp[(np.arange(pos, pos + len(ts))) % len(hp)]
                x = np.minimum(ts + hh, len(C) - 1).astype(float)
                e = O[np.minimum(ts + 1, len(O) - 1)]
                g = dd * (C[x.astype(np.int64)] / e - 1)
            ok = np.isfinite(g)
            xi = np.where(ok, x, 0).astype(np.int64)
            cs = np.r_[0, np.cumsum(occ)]
            free = ok & ((cs[xi] - cs[ts]) == 0)                       # half-open [t, x): no accepted trade inside (a trade may start at a previous exit bar)
            acc_iv = []
            for j in np.flatnonzero(free):
                if len(nets) >= n:
                    break
                t, xx = int(ts[j]), int(xi[j])
                if any(not (xx <= a or t >= b) for a, b in acc_iv):
                    continue
                acc_iv.append((t, xx)); occ[t:xx] = 1
                f = (cum_f[xx] - cum_f[t]) * dd[j] if cum_f is not None else 0.0
                nets.append(float(g[j]) - cost - f)
            pos += len(ts)
        means.append(float(np.mean(nets)) if nets else np.nan)
    return np.array(means)


# ------------------------------------------------------------------ batch runner
PERIOD_DATES = dict(D=("2020-01-01", "2023-12-31"), V=("2024-01-01", "2024-12-31"), H=("2025-01-01", "2026-09-30"), FULL=("2020-01-01", "2026-09-30"))


def run_one(dirn, xn, ocs, d, cost, cum_f, rg, lo):
    return sim_reversal(dirn, d, cost, cum_f, rg, lo) if xn == "X3" else B.simulate(dirn, ocs[xn], cost, cum_f, rg, longs_only=lo)


def run_batch(name, S, d, P, log, n_prior):
    cum_f = B.cum_funding(d)
    ocs = {k: B.load_oc(v) for k, v in EXITS.items() if v != "REV"}
    P = dict(P, FULL=(0, len(d) - 1))
    rows, rep = [], []
    keepH = {}
    for cfg, dirn in S.items():
        delayed = np.r_[np.int8(0), dirn[:-1]].astype(np.int8)
        for xn in EXITS:
            for cm, cost, lo in (("fut", B.FUT_RT, False), ("spot", B.SPOT_RT, True)):
                rec = dict(batch=name, cfg=cfg, exit=xn, cost=cm)
                cf = cum_f if cm == "fut" else None
                for pn in ("D", "V", "H", "FULL"):
                    tr = run_one(dirn, xn, ocs, d, cost, cf, P[pn], lo)
                    e, daily = equity_reports(tr, d, *PERIOD_DATES[pn])
                    rec.update({f"{pn}_{k}": v for k, v in metrics(tr, d, e).items()})
                    rep.append(daily.assign(equity=e.values, cfg=cfg, exit=xn, cost=cm, period=pn).reset_index().rename(columns={"index": "date"}))
                    if cm == "fut" and pn == "H":
                        keepH[(cfg, xn)] = tr
                    if cm == "fut" and pn == "FULL" and len(tr["net"]):
                        yy = pd.Series(tr["net"]).groupby(d.index[tr["t"]].year).mean()
                        rec.update({f"Y{y}_mean": float(v) for y, v in yy.items()})
                        rec["pos_years"] = float((yy > 0).mean())
                if cm == "fut":
                    for pn in ("H", "FULL"):
                        ts_ = run_one(dirn, xn, ocs, d, 2 * cost, cf, P[pn], lo)
                        td_ = run_one(delayed, xn, ocs, d, cost, cf, P[pn], lo)
                        rec[f"{pn}_stress_mean"] = float(ts_["net"].mean()) if len(ts_["net"]) else np.nan
                        rec[f"{pn}_delay_mean"] = float(td_["net"].mean()) if len(td_["net"]) else np.nan
                rows.append(rec)
        log(f"{name}: {cfg} done")
    M = pd.DataFrame(rows)
    M.to_csv(OUT / f"{name}_metrics.csv", index=False)
    Dly = pd.concat(rep, ignore_index=True)
    Dly.to_parquet(OUT / f"{name}_daily.parquet", index=False)
    key = ["cfg", "exit", "cost", "period"]
    for unit, col in (("monthly", pd.to_datetime(Dly.date).dt.to_period("M").astype(str)), ("yearly", pd.to_datetime(Dly.date).dt.year)):
        T = Dly.assign(unit=col).groupby(key + ["unit"]).agg(n=("n", "sum"), net_sum=("net_sum", "sum"), equity_end=("equity", "last")).reset_index()
        T["ret"] = T.groupby(key).equity_end.transform(lambda s: s / s.shift(1).fillna(10_000.0) - 1)
        T.to_csv(OUT / f"{name}_{unit}.csv", index=False)
    log(f"{name}: reports written ({len(Dly)} daily rows)")
    # ---- gates for every primary configuration (amendment 1 §3)
    F = M[M.cost == "fut"].copy()
    N = n_prior + len(F)
    sr_d = (F.D_mean / (F.D_se * np.sqrt(F.D_n))).replace([np.inf, -np.inf], np.nan)
    sr_var = float(sr_d.dropna().var())
    G = []
    for r in F.itertuples():
        tr = keepH[(r.cfg, r.exit)]
        n = len(tr["net"])
        g = dict(cfg=r.cfg, exit=r.exit, H_n=n)
        if n >= 2:
            p_long = float((tr["dir"] > 0).mean())
            if r.exit == "X3":
                ctl = fast_control(n, p_long, P["H"][0], P["H"][1], B.FUT_RT, cum_f, holds=tr["exit"] - tr["t"], d=d)
            else:
                ctl = fast_control(n, p_long, P["H"][0], P["H"][1], B.FUT_RT, cum_f, oc=ocs[r.exit])
            ci = B.boot_ci(tr["net"], tr["t"], d.index) if n >= 10 else [np.nan, np.nan]
            y26 = d.index[tr["t"]] >= pd.Timestamp("2026-01-01")
            g.update(H_mean=float(tr["net"].mean()), H_ci_lo=ci[0], ctrl_p95=float(np.nanpercentile(ctl, 95)), ctrl_median=float(np.nanmedian(ctl)),
                     m25=float(tr["net"][~y26].mean()) if (~y26).any() else np.nan, m26=float(tr["net"][y26].mean()) if y26.any() else np.nan,
                     dsr=B.dsr(tr["net"], N, sr_var)[0] if np.isfinite(sr_var) and tr["net"].std() > 0 else np.nan)
            g["G1"] = bool(g["H_ci_lo"] > 0); g["G2"] = n >= 100; g["G3"] = bool(g["H_mean"] >= g["ctrl_p95"])
            g["G4"] = bool(g["m25"] > 0 and g["m26"] > 0); g["G5"] = bool(g["dsr"] > 0.95)
            g["G6"] = bool(r.H_stress_mean > 0 and r.H_delay_mean > 0)
            g["edge"] = all(g[k] for k in ("G1", "G2", "G3", "G4", "G5", "G6"))
        G.append(g)
    G = pd.DataFrame(G)
    F = F.merge(G[["cfg", "exit", "H_ci_lo", "ctrl_p95", "edge"] + [c for c in G.columns if c.startswith("G")]], on=["cfg", "exit"], how="left")
    F["consistency"] = sum((F[c].fillna(0) > 0).astype(int) for c in ("D_mean", "V_mean", "H_mean"))
    F["delay_agree"] = (np.sign(F.H_delay_mean.fillna(0)) == np.sign(F.H_mean.fillna(0))).astype(int)
    ranks = pd.concat([F.H_mean.rank(ascending=False), F.H_ci_lo.rank(ascending=False), F.H_pos_months.rank(ascending=False),
                       F.H_maxdd.rank(ascending=False), F.H_pf.rank(ascending=False), F.consistency.rank(ascending=False),
                       F.H_stress_mean.rank(ascending=False), F.delay_agree.rank(ascending=False)], axis=1)
    F["rank_score"] = ranks.mean(axis=1)
    F = F.sort_values(["rank_score", "cfg", "exit"]).reset_index(drop=True)
    F["rank"] = np.arange(1, len(F) + 1)
    F.to_csv(OUT / f"{name}_ranking.csv", index=False)
    G.to_csv(OUT / f"{name}_gates_all.csv", index=False)
    for r in F.head(20).itertuples():
        tr = keepH[(r.cfg, r.exit)]
        pd.DataFrame(dict(t=tr["t"], time=d.index[tr["t"]], dir=tr["dir"], gross=tr["gross"], net=tr["net"], exit=tr["exit"])).to_csv(
            OUT / f"{name}_H_trades_{r.cfg}_{r.exit}.csv", index=False)
    return F, G, N, sr_var


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "batch1"
    assert sha(OUT / "MASTER_BENCH_AMENDMENT_1_PREREGISTERED.md") == (OUT / "AMENDMENT_1_SHA256.txt").read_text().split()[0], "amendment changed"
    logf = open(OUT / "run_log.txt", "a", encoding="utf-8")

    def log(m):
        s = f"[{pd.Timestamp.now('UTC'):%Y-%m-%d %H:%M:%S}] {m}"; print(s, flush=True); logf.write(s + "\n"); logf.flush()
    d = B.load(); P = B.periods(d)
    if stage == "controltest":                                         # CODE_NOTES 1 pre-run test, no Batch 1 number
        cum_f = B.cum_funding(d)
        R = json.loads((B.OUT / "BTC_ENTRY_RESULTS.json").read_text(encoding="utf-8"))
        bad = []
        for f in R["finals"]:
            oc = B.load_oc(f["set"])
            ctl = fast_control(f["H_n"], f["H_long_share"], P["H"][0], P["H"][1], B.FUT_RT, cum_f, oc=oc)
            ok_ = abs(float(np.nanpercentile(ctl, 95)) - f["H_ctrl_p95"]) < 1e-12 and abs(float(np.nanmedian(ctl)) - f["H_ctrl_median"]) < 1e-12
            log(f"controltest {f['cfg']} {f['set']}: fast p95 {np.nanpercentile(ctl, 95):.10f} vs stored {f['H_ctrl_p95']:.10f} -> {ok_}")
            bad += [] if ok_ else [f["cfg"]]
        log(f"controltest: {10 - len(bad)}/10 identical")
        return
    pd.DataFrame([(str(B.PX.relative_to(PROJ)).replace("\\", "/"), sha(B.PX)), (str(B.FUND.relative_to(PROJ)).replace("\\", "/"), sha(B.FUND)),
                  ("deploy/fees.json", sha(PROJ / "deploy" / "fees.json")),
                  ("logs/research_btc_entry/cache/out_V2.npz", sha(B.CACHE / "out_V2.npz")),
                  ("logs/research_btc_entry/cache/out_A1_1.npz", sha(B.CACHE / "out_A1_1.npz"))], columns=["path", "sha256"]).to_csv(OUT / "input_manifest.csv", index=False)
    if stage == "batch1":
        t0 = time.time()
        S = batch1_signals(d)
        log(f"batch1 signals: {len(S)} configs in {time.time() - t0:.0f} s")
        prior = json.loads((B.OUT / "BTC_ENTRY_RESULTS.json").read_text(encoding="utf-8"))["N_trials"]
        F, G, N, sr_var = run_batch("batch1", S, d, P, log, prior)
        res = dict(protocol_sha256=sha(PROTO), amendment_sha256=sha(OUT / "MASTER_BENCH_AMENDMENT_1_PREREGISTERED.md"), code_sha256=sha(__file__),
                   manifest_sha256=sha(OUT / "input_manifest.csv"), n_signal_configs=len(S), n_primary=len(F), N_for_dsr=N, sr_var=sr_var,
                   n_edges=int(G.edge.fillna(False).sum()), edges=G[G.edge.fillna(False)].to_dict("records"),
                   top20=F.head(20)[["rank", "cfg", "exit", "H_n", "H_mean", "H_ci_lo", "H_pos_months", "H_maxdd", "H_pf", "consistency",
                                     "H_stress_mean", "H_delay_mean", "pos_years", "edge"]].to_dict("records"))
        f = OUT / "BATCH1_RESULTS.json"
        f.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        (OUT / "BATCH1_RESULTS_SHA256.txt").write_text(sha(f) + "  BATCH1_RESULTS.json\n")
        log(f"batch1 done: {len(F)} primary configs; edges {res['n_edges']}")


if __name__ == "__main__":
    main()