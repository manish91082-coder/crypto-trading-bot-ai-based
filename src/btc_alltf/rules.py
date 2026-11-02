"""BTC-ALLTF study (2026-10-28): every rule as a pair of causal state arrays (A, B), int8 0/1, computed on ONE timeframe's bars.
  A = the rule's bullish reading is "on", B = its bearish reading is "on" (both latched: on at the entry condition, off at the
  exit condition, carried forward in between). Value at bar t uses bars 0..t only.
  Configs built from one rule (study.py): long@A (natural long), short@B (natural short), long@B and short@A (contra).
  Spot can only be long: long@A, long@B.
Rule kinds:
  state  : A = up, B = dn                                        (e.g. close > SMA50 / close < SMA50)
  osc    : A = latch(oversold, x > mid), B = latch(overbought, x < mid)   (fade long = long@A; follow long = long@B)
  event  : A = latch(bull_event, bear_event), B = latch(bear_event, bull_event)
Project rules (tag PRJ) reproduce the definitions used before: TFX families (src/research/tf_edge_map.py conditions: TSMOM20,
EMAX20/50, MACD, DONCH20/10, RSI 30/50/70, BB20 sample sd), Spot S1 (close > SMA200), the user's green-candle rule, the
micro-momentum rule, the Batch 2 low-vol + TS20 cluster, ConnorsRSI, the TURN Bollinger fade, double bottom/top, swing follow."""
import ctypes
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
_L = ctypes.CDLL(str(HERE / "ind.dll"))
_D = ctypes.POINTER(ctypes.c_double)
for _fn, _args in (("wma", [ctypes.c_int, _D, ctypes.c_int, _D]), ("mad", [ctypes.c_int, _D, ctypes.c_int, _D]),
                   ("ext_age", [ctypes.c_int, _D, ctypes.c_int, ctypes.c_int, _D]), ("pct_rank", [ctypes.c_int, _D, ctypes.c_int, _D]),
                   ("psar", [ctypes.c_int, _D, _D, ctypes.c_double, ctypes.c_double, _D]),
                   ("supertrend", [ctypes.c_int, _D, _D, _D, _D, ctypes.c_double, _D]),
                   ("kama", [ctypes.c_int, _D, _D, ctypes.c_int, _D]), ("fisher", [ctypes.c_int, _D, _D]),
                   ("streak", [ctypes.c_int, _D, _D]), ("zigzag", [ctypes.c_int, _D, _D, ctypes.c_double, _D]),
                   ("structure", [ctypes.c_int, _D, _D, _D, _D, ctypes.c_double, _D, _D])):
    getattr(_L, _fn).argtypes = _args
    getattr(_L, _fn).restype = None


def _p(a):
    return a.ctypes.data_as(_D)


def _arr(x):
    return np.ascontiguousarray(np.asarray(x, dtype=np.float64))


def cfun(name, *args, nout=1):
    """call a C indicator: args are arrays or scalars; returns nout new float64 arrays of length N"""
    arrs = [_arr(a) if isinstance(a, (np.ndarray, pd.Series)) else a for a in args]
    N = len(next(a for a in arrs if isinstance(a, np.ndarray)))
    outs = [np.empty(N) for _ in range(nout)]
    cargs = [N] + [(_p(a) if isinstance(a, np.ndarray) else a) for a in arrs] + [_p(o) for o in outs]
    getattr(_L, name)(*cargs)
    return outs[0] if nout == 1 else outs


# ------------------------------------------------------------------ indicator helpers (pandas, causal)
def sma(s, n):
    return s.rolling(n, min_periods=n).mean()


def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def wma(s, n):
    return pd.Series(cfun("wma", s.values, n), index=s.index)


def rsi(c, n=14):
    dl = c.diff()
    au, ad = wilder(dl.clip(lower=0), n), wilder((-dl).clip(lower=0), n)
    return 100 - 100 / (1 + au / ad)


def true_range(b):
    pc = b.close.shift(1)
    return pd.concat([b.high - b.low, (b.high - pc).abs(), (b.low - pc).abs()], axis=1).max(axis=1)


def atr(b, n=14):
    return wilder(true_range(b), n)


def zs(s, n=500):
    return (s - s.rolling(n, min_periods=n // 2).mean()) / s.rolling(n, min_periods=n // 2).std()


def latch(on, off):
    """1 from a bar where `on` is true until a bar where `off` is true (on wins if both); NaN conditions count as false"""
    on = np.asarray(on, dtype=bool)
    off = np.asarray(off, dtype=bool)
    ev = np.where(on, 1.0, np.where(off, 0.0, np.nan))
    return pd.Series(ev).ffill().fillna(0.0).values.astype(np.int8)


def st(up, dn):
    return np.asarray(up, dtype=bool).astype(np.int8), np.asarray(dn, dtype=bool).astype(np.int8)


def osc(x, lo, hi, mid):
    """fade-type latches: A = from x < lo until x > mid, B = from x > hi until x < mid"""
    x = pd.Series(x)
    return latch(x < lo, x > mid), latch(x > hi, x < mid)


def evt(bull, bear):
    bull, bear = np.asarray(bull, dtype=bool), np.asarray(bear, dtype=bool)
    return latch(bull, bear), latch(bear, bull)


# ------------------------------------------------------------------ rules
class Ctx:
    """bars of one timeframe + cached shared indicators"""

    def __init__(self, b):
        self.b = b.reset_index(drop=True)
        self.c, self.o, self.h, self.l, self.v = self.b.close, self.b.open, self.b.high, self.b.low, self.b.volume
        self._m = {}

    def get(self, k, f):
        if k not in self._m:
            self._m[k] = f()
        return self._m[k]

    def atr(self, n=14):
        return self.get(("atr", n), lambda: atr(self.b, n))

    def rsi(self, n):
        return self.get(("rsi", n), lambda: rsi(self.c, n))

    def ema(self, n):
        return self.get(("ema", n), lambda: ema(self.c, n))

    def sma(self, n):
        return self.get(("sma", n), lambda: sma(self.c, n))


def r_ma(kind, n):
    def f(x):
        m = x.sma(n) if kind == "SMA" else x.ema(n) if kind == "EMA" else None
        if kind == "DEMA":
            e1 = x.ema(n); m = 2 * e1 - ema(e1, n)
        if kind == "TEMA":
            e1 = x.ema(n); e2 = ema(e1, n); m = 3 * e1 - 3 * e2 + ema(e2, n)
        return st(x.c > m, x.c < m)
    return f


def r_cross(kind, f_, s_):
    def f(x):
        a, b = (x.ema(f_), x.ema(s_)) if kind == "EMA" else (x.sma(f_), x.sma(s_))
        return st(a > b, a < b)
    return f


def r_hma(n):
    def f(x):
        hm = wma(2 * wma(x.c, n // 2) - wma(x.c, n), int(round(np.sqrt(n))))
        return st(hm > hm.shift(1), hm < hm.shift(1))
    return f


def r_kama(x):
    c = x.c
    ch = (c - c.shift(10)).abs()
    vol = c.diff().abs().rolling(10).sum()
    er = (ch / vol).fillna(0).values
    sc = (er * (2 / 3 - 2 / 31) + 2 / 31) ** 2
    k = pd.Series(cfun("kama", c.values, sc, 10))
    return st(c > k, c < k)


def r_macd(f_, s_, g_, mode):
    def f(x):
        m = ema(x.c, f_) - ema(x.c, s_)
        sg = ema(m, g_)
        return st(m > sg, m < sg) if mode == "sig" else st(m > 0, m < 0)
    return f


def _dmi(x, n=14):
    def calc():
        h, l = x.h, x.l
        upm, dnm = h.diff(), -l.diff()
        pdm = pd.Series(np.where((upm > dnm) & (upm > 0), upm, 0.0))
        mdm = pd.Series(np.where((dnm > upm) & (dnm > 0), dnm, 0.0))
        at = wilder(true_range(x.b), n)
        pdi, mdi = 100 * wilder(pdm, n) / at, 100 * wilder(mdm, n) / at
        adx = wilder(100 * (pdi - mdi).abs() / (pdi + mdi), n)
        return pdi, mdi, adx
    return x.get(("dmi", n), calc)


def r_adx(th):
    def f(x):
        pdi, mdi, adx = _dmi(x)
        return st((adx > th) & (pdi > mdi), (adx > th) & (mdi > pdi))
    return f


def r_aroon(x, n=25):
    au = 100 * (n - pd.Series(cfun("ext_age", x.h.values, n + 1, 1))) / n
    ad = 100 * (n - pd.Series(cfun("ext_age", x.l.values, n + 1, -1))) / n
    return st((au > 70) & (ad < 30), (ad > 70) & (au < 30))


def r_psar(x):
    s = pd.Series(cfun("psar", x.h.values, x.l.values, 0.02, 0.2))
    return st(x.c > s, x.c < s)


def r_super(n, m):
    def f(x):
        d = cfun("supertrend", x.h.values, x.l.values, x.c.values, atr(x.b, n).values, float(m))
        return st(d == 1, d == -1)
    return f


def _ichi(x):
    def calc():
        h, l = x.h, x.l
        ten = (h.rolling(9).max() + l.rolling(9).min()) / 2
        kij = (h.rolling(26).max() + l.rolling(26).min()) / 2
        sa = ((ten + kij) / 2).shift(26)
        sb = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
        return ten, kij, np.fmax(sa, sb), np.fmin(sa, sb)
    return x.get("ichi", calc)


def r_ichi_cloud(x):
    ten, kij, top, bot = _ichi(x)
    return st((x.c > top) & (ten > kij), (x.c < bot) & (ten < kij))


def r_ichi_tk(x):
    ten, kij, _, _ = _ichi(x)
    return st(ten > kij, ten < kij)


def r_donch(n, m):
    """turtle / TFX DONCH: long on close > prior n-high, exit on close < prior m-low (mirror for short)"""
    def f(x):
        hn, ln = x.h.rolling(n).max().shift(1), x.l.rolling(n).min().shift(1)
        hm, lm = x.h.rolling(m).max().shift(1), x.l.rolling(m).min().shift(1)
        return latch(x.c > hn, x.c < lm), latch(x.c < ln, x.c > hm)
    return f


def r_keltner_brk(x):
    e, a = x.ema(20), x.atr(10)
    return latch(x.c > e + 2 * a, x.c < e), latch(x.c < e - 2 * a, x.c > e)


def r_bb_brk(x):
    m, s = x.sma(20), x.c.rolling(20).std()
    return latch(x.c > m + 2 * s, x.c < m), latch(x.c < m - 2 * s, x.c > m)


def _linreg(x, n):
    def calc():
        t = pd.Series(np.arange(len(x.c), dtype=float))
        cov = x.c.rolling(n).cov(t)
        slope = cov / t.rolling(n).var()
        r2 = x.c.rolling(n).corr(t) ** 2
        return slope, r2
    return x.get(("linreg", n), calc)


def r_linreg(n):
    def f(x):
        s, _ = _linreg(x, n)
        return st(s > 0, s < 0)
    return f


def r_r2trend(x):
    s, r2 = _linreg(x, 50)
    return st((r2 > 0.5) & (s > 0), (r2 > 0.5) & (s < 0))


def r_vortex(x):
    h, l = x.h, x.l
    tr = true_range(x.b)
    vp, vm = (h - l.shift(1)).abs().rolling(14).sum() / tr.rolling(14).sum(), (l - h.shift(1)).abs().rolling(14).sum() / tr.rolling(14).sum()
    return st(vp > vm, vm > vp)


def r_trix(x):
    t = ema(ema(ema(x.c, 15), 15), 15).pct_change() * 100
    return st(t > 0, t < 0)


def r_kst(x):
    c = x.c
    roc = lambda n: c.pct_change(n) * 100                                     # noqa: E731
    k = roc(10).rolling(10).mean() + 2 * roc(15).rolling(10).mean() + 3 * roc(20).rolling(10).mean() + 4 * roc(30).rolling(15).mean()
    s = k.rolling(9).mean()
    return st(k > s, k < s)


def _ha(x):
    def calc():
        hc = (x.o + x.h + x.l + x.c) / 4
        y = hc.shift(1)
        y.iloc[0] = (x.o.iloc[0] + x.c.iloc[0]) / 2
        ho = y.ewm(alpha=0.5, adjust=False).mean()                           # ho[t] = (ho[t-1] + hc[t-1]) / 2
        return hc, ho
    return x.get("ha", calc)


def r_ha(k):
    def f(x):
        hc, ho = _ha(x)
        g, r = (hc > ho), (hc < ho)
        if k == 2:
            g, r = g & g.shift(1, fill_value=False), r & r.shift(1, fill_value=False)
        return st(g, r)
    return f


def r_tsmom(n):
    def f(x):
        m = x.c / x.c.shift(n) - 1
        return st(m > 0, m < 0)
    return f


def r_tsmom_tfx(x):
    """TFX TSMOM exactly: long m > 0, exit m <= 0; short m < 0, exit m >= 0 (same as state rule)"""
    return r_tsmom(20)(x)


def r_er(x):
    ch = x.c - x.c.shift(10)
    er = ch.abs() / x.c.diff().abs().rolling(10).sum()
    return st((er > 0.5) & (ch > 0), (er > 0.5) & (ch < 0))


def r_chop(x):
    tr = true_range(x.b)
    ch = 100 * np.log10(tr.rolling(14).sum() / (x.h.rolling(14).max() - x.l.rolling(14).min())) / np.log10(14)
    e = x.ema(20)
    return st((ch < 38.2) & (e > e.shift(1)), (ch < 38.2) & (e < e.shift(1)))


def r_ribbon(x):
    a, b, c, d = x.ema(10), x.ema(20), x.ema(50), x.ema(100)
    return st((a > b) & (b > c) & (c > d), (a < b) & (b < c) & (c < d))


def r_vwap_trend(x):
    tp = (x.h + x.l + x.c) / 3
    vw = (tp * x.v).rolling(50).sum() / x.v.rolling(50).sum()
    return st(x.c > vw, x.c < vw)


# ---- oscillators (fade latches)
def r_rsi(n, lo, hi):
    return lambda x: osc(x.rsi(n), lo, hi, 50)


def r_rsi50(x):
    r = x.rsi(14)
    return st(r > 50, r < 50)


def r_connors(x):
    c = x.c
    s = pd.Series(cfun("streak", c.values))
    pr = pd.Series(cfun("pct_rank", c.pct_change().values, 100))             # rank of today's ROC among the previous 99 (as Batch 1)
    cr = (rsi(c, 3) + rsi(s, 2) + pr) / 3
    return osc(cr, 10, 90, 50)


def r_stoch(x):
    k = 100 * (x.c - x.l.rolling(14).min()) / (x.h.rolling(14).max() - x.l.rolling(14).min())
    K = k.rolling(3).mean()
    D = K.rolling(3).mean()
    up = (K < 20) & (K > D) & (K.shift(1) <= D.shift(1))
    dn = (K > 80) & (K < D) & (K.shift(1) >= D.shift(1))
    return latch(up, K > 50), latch(dn, K < 50)


def r_stochrsi(x):
    r = x.rsi(14)
    s = (r - r.rolling(14).min()) / (r.rolling(14).max() - r.rolling(14).min())
    return osc(s.rolling(3).mean(), 0.2, 0.8, 0.5)


def r_willr(x):
    w = -100 * (x.h.rolling(14).max() - x.c) / (x.h.rolling(14).max() - x.l.rolling(14).min())
    return osc(w, -80, -20, -50)


def r_cci(th):
    def f(x):
        tp = (x.h + x.l + x.c) / 3
        md = pd.Series(cfun("mad", tp.values, 20))
        cci = (tp - tp.rolling(20).mean()) / (0.015 * md)
        return osc(cci, -th, th, 0)
    return f


def r_cmo(x):
    d = x.c.diff()
    su, sd = d.clip(lower=0).rolling(14).sum(), (-d).clip(lower=0).rolling(14).sum()
    return osc(100 * (su - sd) / (su + sd), -50, 50, 0)


def r_uo(x):
    c, h, l = x.c, x.h, x.l
    pc = c.shift(1)
    bp = c - np.fmin(l, pc)
    trr = np.fmax(h, pc) - np.fmin(l, pc)
    uo = 100 * (4 * bp.rolling(7).sum() / trr.rolling(7).sum() + 2 * bp.rolling(14).sum() / trr.rolling(14).sum()
                + bp.rolling(28).sum() / trr.rolling(28).sum()) / 7
    return osc(uo, 30, 70, 50)


def r_mfi(x):
    tp = (x.h + x.l + x.c) / 3
    rf = tp * x.v
    pos = rf.where(tp > tp.shift(1), 0.0).rolling(14).sum()
    neg = rf.where(tp < tp.shift(1), 0.0).rolling(14).sum()
    return osc(100 - 100 / (1 + pos / neg), 20, 80, 50)


def r_bb_fade(k):
    """TFX BB (k=2): long close < m - 2s, exit close >= m; short close > m + 2s, exit close <= m (sample sd)"""
    def f(x):
        m, s = x.sma(20), x.c.rolling(20).std()
        return latch(x.c < m - k * s, x.c >= m), latch(x.c > m + k * s, x.c <= m)
    return f


def r_z(n):
    def f(x):
        z = (x.c - x.sma(n)) / x.c.rolling(n).std()
        return osc(z, -2, 2, 0)
    return f


def r_fisher(x):
    med = (x.h + x.l) / 2
    hh, ll = med.rolling(10).max(), med.rolling(10).min()
    fs = pd.Series(cfun("fisher", (2 * ((med - ll) / (hh - ll) - 0.5)).values))
    fs[hh.isna().values] = np.nan
    return latch((fs < -1.5) & (fs > fs.shift(1)), fs > 0), latch((fs > 1.5) & (fs < fs.shift(1)), fs < 0)


def r_rocz(x):
    return osc(zs(x.c.pct_change(10)), -2, 2, 0)


def r_vwapz(x):
    tp = (x.h + x.l + x.c) / 3
    vw = (tp * x.v).rolling(20).sum() / x.v.rolling(20).sum()
    return osc(zs(x.c - vw), -2, 2, 0)


def r_dpoz(x):
    return osc(zs(x.c - x.sma(20).shift(11)), -2, 2, 0)


def r_kelt_fade(x):
    e, a = x.ema(20), x.atr(10)
    return latch(x.c < e - 2 * a, x.c > e), latch(x.c > e + 2 * a, x.c < e)


# ---- momentum / flow sign rules (state)
def r_ao(x):
    med = (x.h + x.l) / 2
    ao = med.rolling(5).mean() - med.rolling(34).mean()
    return st(ao > 0, ao < 0)


def r_elder(x):
    e = ema(x.c, 13)
    return st((x.h - e > 0) & (e > e.shift(1)), (x.l - e < 0) & (e < e.shift(1)))


def r_force(x):
    fi = ema(x.c.diff() * x.v, 13)
    return st(fi > 0, fi < 0)


def r_coppock(x):
    cp = wma(x.c.pct_change(14) * 100 + x.c.pct_change(11) * 100, 10)
    return st(cp > 0, cp < 0)


def r_tsi(x):
    d = x.c.diff()
    t = 100 * ema(ema(d, 25), 13) / ema(ema(d.abs(), 25), 13)
    s = ema(t, 7)
    return st(t > s, t < s)


def r_bop(x):
    bop = ((x.c - x.o) / (x.h - x.l)).replace([np.inf, -np.inf], np.nan).rolling(14).mean()
    return st(bop > 0, bop < 0)


def r_obv(x):
    obv = (np.sign(x.c.diff()).fillna(0) * x.v).cumsum()
    e = ema(obv, 20)
    return st(obv > e, obv < e)


def _clv(x):
    rng = (x.h - x.l).replace(0, np.nan)
    return (((x.c - x.l) - (x.h - x.c)) / rng).fillna(0)


def r_cmf(x):
    mfv = _clv(x) * x.v
    cmf = mfv.rolling(20).sum() / x.v.rolling(20).sum()
    return st(cmf > 0.05, cmf < -0.05)


def r_chaikin(x):
    adl = (_clv(x) * x.v).cumsum()
    co = ema(adl, 3) - ema(adl, 10)
    return st(co > 0, co < 0)


def r_vpt(x):
    vpt = (x.c.pct_change().fillna(0) * x.v).cumsum()
    e = ema(vpt, 20)
    return st(vpt > e, vpt < e)


def r_eom(x):
    mid = (x.h + x.l) / 2
    box = (x.v / 1e6) / (x.h - x.l).replace(0, np.nan)
    eom = ((mid - mid.shift(1)) / box).rolling(14).mean()
    return st(eom > 0, eom < 0)


def r_taker(x):
    tbr = x.b.taker_buy_base / x.v.replace(0, np.nan)
    z = zs(tbr, 100)
    return st(z > 1, z < -1)


def r_relvol(x):
    spike = x.v > 3 * x.v.rolling(20).mean().shift(1)
    return evt(spike & (x.c > x.o), spike & (x.c < x.o))


# ---- volatility
def r_squeeze(x):
    m, s = x.sma(20), x.c.rolling(20).std()
    e, a = x.ema(20), x.atr(20)
    sq = (m + 2 * s < e + 1.5 * a) & (m - 2 * s > e - 1.5 * a)
    rel = sq.shift(1, fill_value=False) & ~sq
    return latch(rel & (x.c > m), x.c < m), latch(rel & (x.c < m), x.c > m)


def r_nr7(x):
    rg = x.h - x.l
    nr7 = (rg == rg.rolling(7).min()).shift(1, fill_value=False)
    return evt(nr7 & (x.c > x.h.shift(1)), nr7 & (x.c < x.l.shift(1)))


def r_lwvb(x):
    pr = (x.h - x.l).shift(1)
    return evt(x.c > x.o + 0.5 * pr, x.c < x.o - 0.5 * pr)


def r_atrexp(x):
    big = true_range(x.b) > 2 * x.atr(14).shift(1)
    return evt(big & (x.c > x.o), big & (x.c < x.o))


def _yz(x, n=20):
    o, h, l, c = np.log(x.o), np.log(x.h), np.log(x.l), np.log(x.c)
    co = o - c.shift(1)
    oc = c - o
    rs = (h - c) * (h - o) + (l - c) * (l - o)
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    return np.sqrt(co.rolling(n).var() + k * oc.rolling(n).var() + (1 - k) * rs.rolling(n).mean())


def r_lowvol_ts20(x):
    """Batch 2 cluster: low range-based (Yang-Zhang) vol vs its 200-bar median + TS20 follow"""
    yz = _yz(x)
    low = yz < yz.rolling(200, min_periods=200).median()
    m = x.c / x.c.shift(20) - 1
    return st(low & (m > 0), low & (m < 0))


def r_hivol_trend(x):
    natr = x.atr(14) / x.c
    hv = natr > natr.rolling(200, min_periods=200).median()
    a, b = x.ema(20), x.ema(50)
    return st(hv & (a > b), hv & (a < b))


# ---- price action / patterns (events unless noted)
def r_engulf(x):
    o, c = x.o, x.c
    po, pc = o.shift(1), c.shift(1)
    bull = (pc < po) & (c > o) & (o <= pc) & (c >= po)
    bear = (pc > po) & (c < o) & (o >= pc) & (c <= po)
    return evt(bull, bear)


def r_hammer(x):
    o, c, h, l = x.o, x.c, x.h, x.l
    body = (c - o).abs()
    lw, uw = np.fmin(o, c) - l, h - np.fmax(o, c)
    m = x.sma(20)
    return evt((lw >= 2 * body) & (uw <= body) & (c < m), (uw >= 2 * body) & (lw <= body) & (c > m))


def r_soldiers(x):
    o, c = x.o, x.c
    g = (c > o) & (c > c.shift(1))
    r = (c < o) & (c < c.shift(1))
    return evt(g & g.shift(1, fill_value=False) & g.shift(2, fill_value=False), r & r.shift(1, fill_value=False) & r.shift(2, fill_value=False))


def r_star(x):
    o, c = x.o, x.c
    b = (c - o).abs()
    b1, b2 = b.shift(1), b.shift(2)
    small = b1 < 0.3 * b2
    bull = (c.shift(2) < o.shift(2)) & small & (c > o) & (c > (o.shift(2) + c.shift(2)) / 2)
    bear = (c.shift(2) > o.shift(2)) & small & (c < o) & (c < (o.shift(2) + c.shift(2)) / 2)
    return evt(bull, bear)


def r_inside(x):
    ib = (x.h.shift(1) < x.h.shift(2)) & (x.l.shift(1) > x.l.shift(2))
    return evt(ib & (x.c > x.h.shift(1)), ib & (x.c < x.l.shift(1)))


def r_outside(x):
    ob = (x.h > x.h.shift(1)) & (x.l < x.l.shift(1))
    return evt(ob & (x.c > x.o), ob & (x.c < x.o))


def _struct(x):
    return x.get("struct", lambda: cfun("structure", x.h.values, x.l.values, x.c.values, x.atr(14).values, 0.5, nout=2))


def r_swing_struct(x):
    s, _ = _struct(x)
    return st(s == 1, s == -1)


def r_double(x):
    _, d = _struct(x)
    return evt(d == 1, d == -1)


def r_streak(k):
    def f(x):
        s = pd.Series(cfun("streak", x.c.values))
        return evt(s == k, s == -k)                                            # the k-th consecutive rising / falling close
    return f


def r_green(x):
    """user's rule: green candle after red -> long, green -> red exit (A); mirror for short (B). Doji keeps the state."""
    return latch(x.c > x.o, x.c < x.o), latch(x.c < x.o, x.c > x.o)


def r_micro(x):
    """micro-momentum: 3 rising closes with volume > 1.5 x 20-bar mean -> long, exit at the first falling close"""
    s = pd.Series(cfun("streak", x.c.values))
    vr = x.v > 1.5 * x.v.rolling(20).mean().shift(1)
    return latch((s >= 3) & vr, x.c < x.c.shift(1)), latch((s <= -3) & vr, x.c > x.c.shift(1))


def r_zigzag(x):
    d = cfun("zigzag", x.c.values, x.atr(14).values, 3.0)
    return st(d == 1, d == -1)


def r_srbounce(x):
    lo50, hi50 = x.l.rolling(50).min(), x.h.rolling(50).max()
    a = x.atr(14)
    return evt((x.c - lo50 < 0.5 * a) & (x.c > x.o), (hi50 - x.c < 0.5 * a) & (x.c < x.o))


def r_rsidiv(x):
    r, c = x.rsi(14), x.c
    newlo = c <= c.rolling(20).min()
    newhi = c >= c.rolling(20).max()
    return evt(newlo & (r > r.shift(1).rolling(19).min() + 5), newhi & (r < r.shift(1).rolling(19).max() - 5))


# ---- statistics
def r_ac_regime(x):
    r = x.c.pct_change()
    ac = r.rolling(50).corr(r.shift(1))
    last = np.sign(r)
    sig = np.where(ac.isna() | last.isna(), 0.0, np.where(ac > 0, last, -last))
    return st(pd.Series(sig) > 0, pd.Series(sig) < 0)


# ---- calendar (by bar open time, UTC)
def r_session(h0, h1):
    def f(x):
        hr = pd.to_datetime(x.b.ts, unit="ms", utc=True).dt.hour
        on = (hr >= h0) & (hr < h1)
        return st(on, on)                                                      # A = B = "inside the session"
    return f


def r_weekday(x):
    wd = pd.to_datetime(x.b.ts, unit="ms", utc=True).dt.dayofweek
    return st(wd < 5, wd < 5)


# ------------------------------------------------------------------ registry: (id, category, kind, tags, function, applicable)
INTRA = ("1m", "5m", "15m", "30m", "1h", "4h")
DAYUP = INTRA + ("8h", "1d")
REG = []


def add(rid, cat, kind, fn, tags="", tfs=None):
    REG.append(dict(id=rid, cat=cat, kind=kind, fn=fn, tags=tags, tfs=tfs))


for n in (20, 50, 100, 200):
    add(f"T_SMA{n}", "trend", "state", r_ma("SMA", n), "PRJ:SpotS1" if n == 200 else "")
for n in (20, 50, 100, 200):
    add(f"T_EMA{n}", "trend", "state", r_ma("EMA", n))
add("T_DEMA50", "trend", "state", r_ma("DEMA", 50))
add("T_TEMA50", "trend", "state", r_ma("TEMA", 50))
for f_, s_ in ((9, 21), (20, 50), (50, 200)):
    add(f"T_EMAX{f_}_{s_}", "trend", "state", r_cross("EMA", f_, s_), "PRJ:TFX_EMAX" if (f_, s_) == (20, 50) else "")
for f_, s_ in ((10, 30), (50, 200)):
    add(f"T_SMAX{f_}_{s_}", "trend", "state", r_cross("SMA", f_, s_))
for n in (21, 55):
    add(f"T_HMA{n}slope", "trend", "state", r_hma(n))
add("T_KAMA10", "trend", "state", r_kama)
add("T_MACD12_26_9sig", "trend", "state", r_macd(12, 26, 9, "sig"), "PRJ:TFX_MACD")
add("T_MACD12_26zero", "trend", "state", r_macd(12, 26, 9, "zero"))
add("T_MACD5_35_5sig", "trend", "state", r_macd(5, 35, 5, "sig"))
add("T_ADX25", "trend", "state", r_adx(25))
add("T_ADX20", "trend", "state", r_adx(20))
add("T_AROON25", "trend", "state", r_aroon)
add("T_PSAR", "trend", "state", r_psar)
add("T_SUPER10_3", "trend", "state", r_super(10, 3))
add("T_SUPER20_4", "trend", "state", r_super(20, 4))
add("T_ICHI_CLOUD", "trend", "state", r_ichi_cloud)
add("T_ICHI_TK", "trend", "state", r_ichi_tk)
add("T_DONCH20_10", "trend", "latch", r_donch(20, 10), "PRJ:TFX_DONCH")
add("T_DONCH55_20", "trend", "latch", r_donch(55, 20))
add("T_KELT_BRK", "trend", "latch", r_keltner_brk)
add("T_BB_BRK", "trend", "latch", r_bb_brk)
for n in (20, 50):
    add(f"T_LINREG{n}", "trend", "state", r_linreg(n))
add("T_VORTEX14", "trend", "state", r_vortex)
add("T_TRIX15", "trend", "state", r_trix)
add("T_KST", "trend", "state", r_kst)
add("T_HA1", "trend", "state", r_ha(1))
add("T_HA2", "trend", "state", r_ha(2))
for n in (1, 3, 10, 20, 50, 100):
    add(f"T_TSMOM{n}", "trend", "state", r_tsmom(n), "PRJ:TFX_TSMOM" if n == 20 else "")
add("T_ER10", "trend", "state", r_er)
add("T_CHOP14", "trend", "state", r_chop)
add("T_RIBBON", "trend", "state", r_ribbon)
add("T_VWAP50", "trend", "state", r_vwap_trend)
add("O_RSI14_30_70", "osc", "osc", r_rsi(14, 30, 70), "PRJ:TFX_RSI(N1 sleeve B)")
add("O_RSI14_20_80", "osc", "osc", r_rsi(14, 20, 80))
add("O_RSI2_10_90", "osc", "osc", r_rsi(2, 10, 90))
add("O_RSI14_50", "osc", "state", r_rsi50)
add("O_CONNORS", "osc", "osc", r_connors, "PRJ:Batch1_ConnorsRSI")
add("O_STOCH14", "osc", "osc", r_stoch)
add("O_STOCHRSI", "osc", "osc", r_stochrsi)
add("O_WILLR14", "osc", "osc", r_willr)
add("O_CCI100", "osc", "osc", r_cci(100))
add("O_CCI200", "osc", "osc", r_cci(200))
add("O_CMO14", "osc", "osc", r_cmo)
add("O_ULTOSC", "osc", "osc", r_uo)
add("O_MFI14", "osc", "osc", r_mfi)
add("O_BB20_2", "osc", "osc", r_bb_fade(2), "PRJ:TFX_BB+TURN_BollFade")
add("O_BB20_3", "osc", "osc", r_bb_fade(3))
add("O_Z50", "osc", "osc", r_z(50))
add("O_FISHER10", "osc", "osc", r_fisher)
add("O_ROCZ10", "osc", "osc", r_rocz)
add("O_VWAPZ20", "osc", "osc", r_vwapz)
add("O_DPOZ20", "osc", "osc", r_dpoz)
add("O_KELT_FADE", "osc", "osc", r_kelt_fade)
add("M_AO", "momentum", "state", r_ao)
add("M_ELDER13", "momentum", "state", r_elder)
add("M_FORCE13", "momentum", "state", r_force)
add("M_COPPOCK", "momentum", "state", r_coppock)
add("M_TSI", "momentum", "state", r_tsi)
add("M_BOP14", "momentum", "state", r_bop)
add("F_OBV", "flow", "state", r_obv)
add("F_CMF20", "flow", "state", r_cmf)
add("F_CHAIKIN", "flow", "state", r_chaikin)
add("F_VPT", "flow", "state", r_vpt)
add("F_EOM14", "flow", "state", r_eom)
add("F_TAKERZ100", "flow", "state", r_taker)
add("F_RELVOL3", "flow", "event", r_relvol)
add("V_SQUEEZE", "vol", "latch", r_squeeze)
add("V_NR7", "vol", "event", r_nr7)
add("V_LWVB", "vol", "event", r_lwvb)
add("V_ATREXP", "vol", "event", r_atrexp)
add("V_LOWVOL_TS20", "vol", "state", r_lowvol_ts20, "PRJ:Batch2_lowvol_cluster")
add("V_HIVOL_TREND", "vol", "state", r_hivol_trend)
add("P_ENGULF", "pattern", "event", r_engulf)
add("P_HAMMER", "pattern", "event", r_hammer)
add("P_3SOLDIERS", "pattern", "event", r_soldiers)
add("P_STAR", "pattern", "event", r_star)
add("P_INSIDE", "pattern", "event", r_inside)
add("P_OUTSIDE", "pattern", "event", r_outside)
add("P_SWING_STRUCT", "pattern", "state", r_swing_struct)
add("P_DOUBLE", "pattern", "event", r_double, "PRJ:double_bottom_top")
add("P_STREAK3", "pattern", "event", r_streak(3))
add("P_STREAK5", "pattern", "event", r_streak(5))
add("P_GREEN", "pattern", "latch", r_green, "PRJ:user_green_candle")
add("P_MICRO3", "pattern", "latch", r_micro, "PRJ:micro_momentum")
add("P_ZIGZAG3", "pattern", "state", r_zigzag, "PRJ:swing_follow")
add("P_SRBOUNCE", "pattern", "event", r_srbounce, "PRJ:SR_bounce")
add("P_RSIDIV", "pattern", "event", r_rsidiv)
add("S_R2TREND50", "stat", "state", r_r2trend)
add("S_ACREGIME50", "stat", "state", r_ac_regime)
add("C_ASIA", "calendar", "state", r_session(0, 8), tfs=INTRA)
add("C_EUROPE", "calendar", "state", r_session(8, 16), tfs=INTRA)
add("C_US", "calendar", "state", r_session(16, 24), tfs=INTRA)
add("C_WEEKDAY", "calendar", "state", r_weekday, tfs=DAYUP)

# pair-layer representatives (one per family) and vote groups
REPS = ["T_SMA50", "T_EMAX20_50", "T_MACD12_26_9sig", "T_ADX25", "T_PSAR", "T_SUPER10_3", "T_ICHI_CLOUD", "T_DONCH20_10",
        "T_TSMOM20", "T_HA1", "O_RSI14_30_70", "O_STOCH14", "O_CCI100", "O_BB20_2", "O_Z50", "F_OBV", "F_CMF20", "F_TAKERZ100",
        "M_AO", "V_SQUEEZE", "V_LOWVOL_TS20", "P_ENGULF", "P_SWING_STRUCT", "P_GREEN"]
VOTE_TREND = REPS[:10]
VOTE_OSC = REPS[10:15]


def compute(b, tf):
    """all applicable rules on bars b -> dict rule_id -> (A, B) int8 arrays"""
    x = Ctx(b)
    out = {}
    for r in REG:
        if r["tfs"] is not None and tf not in r["tfs"]:
            continue
        a, bb = r["fn"](x)
        out[r["id"]] = (np.ascontiguousarray(a, dtype=np.int8), np.ascontiguousarray(bb, dtype=np.int8))
    return out, x


def gates(x):
    """entry filters for the filter layer: name -> (gate for long, gate for short), int8"""
    c = x.c
    s200 = x.sma(200)
    _, _, adx = _dmi(x)
    natr = x.atr(14) / c
    med = natr.rolling(500, min_periods=500).median()
    vol = x.v > x.v.rolling(20).mean()
    g = {"F1_TREND200": (c > s200, c < s200), "F2_ADX20": (adx > 20, adx > 20), "F3_LOWVOL": (natr < med, natr < med),
         "F4_HIGHVOL": (natr > med, natr > med), "F5_VOLUME": (vol, vol)}
    return {k: (np.asarray(a, dtype=bool).astype(np.int8), np.asarray(b_, dtype=bool).astype(np.int8)) for k, (a, b_) in g.items()}
