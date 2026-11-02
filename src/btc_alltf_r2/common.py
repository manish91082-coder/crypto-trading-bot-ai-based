"""BTC-ALLTF-R2 (2026-10-29): shared helpers for the corrected evaluation of the BTC-ALLTF study.
Protocol: logs/btc_alltf_r2_2026_10_29/R2_PROTOCOL_PREREGISTERED.md, settings: logs/btc_alltf_r2_2026_10_29/R2_CONFIG.json.
  - coin universe (other coins = out-of-sample for the BTC-selected configs) and their bars, built like src/btc_alltf/build_bars.py
  - daily mark-to-market (MTM) returns of a list of trades
  - Newey-West t, Benjamini-Hochberg, performance numbers"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ / "src/btc_alltf"))
import engine as E                                                            # noqa: E402

R2 = PROJ / "logs/btc_alltf_r2_2026_10_29"
CFG = json.loads((R2 / "R2_CONFIG.json").read_text(encoding="utf-8"))
R1RUN = PROJ / CFG["r1_run"]
DER = PROJ / "data/derived/btc_alltf_r2"
DAY = 86_400_000
MIN = 60_000
TF_MS = {"1m": MIN, "5m": 5 * MIN, "15m": 15 * MIN, "30m": 30 * MIN, "1h": 60 * MIN, "4h": 240 * MIN, "8h": 480 * MIN, "1d": 1440 * MIN}
BASE = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "15m", "1h": "1h", "4h": "1h", "8h": "1h", "1d": "1d", "1w": "1d"}


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10 ** 6)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ coin universe (rules fixed in the protocol, by name / data only)
# copied from src/pipeline_1d/step13_unseen_coins_1d.py (decided there before any result of that study)
NOT_CRYPTO = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "PAXUSDT", "SUSDUSDT", "USDSBUSDT",
    "USDSUSDT", "USTUSDT", "USTCUSDT", "EURUSDT", "GBPUSDT", "AUDUSDT", "BKRWUSDT", "AEURUSDT", "EURIUSDT",
    "USD1USDT", "XUSDUSDT", "RLUSDUSDT", "BFUSDUSDT", "PYUSDUSDT", "USDEUSDT", "TRYUSDT", "BRLUSDT", "ZARUSDT",
    "UAHUSDT", "NGNUSDT", "RUBUSDT", "IDRTUSDT", "BIDRUSDT", "BVNDUSDT", "WBTCUSDT", "WBETHUSDT", "BETHUSDT",
    "PAXGUSDT", "XAUTUSDT", "USDTUSDT", "FRAXUSDT", "USDSOLDUSDT", "KGSTUSDT", "BNSOLUSDT"}
NOT_CRYPTO |= {f"{t}BUSDT" for t in (
    "AAOI", "AAPL", "ADBE", "AGPU", "ALAB", "AMAT", "AMC", "AMD", "AMZN", "ARM", "ASML", "ASTS", "AVGO", "AXTI", "BABA",
    "BMNR", "BNC", "CBRS", "COHR", "COIN", "CRCL", "CRDO", "CRM", "CRWD", "CRWV", "CYPH", "DELL", "DJT", "DRAM", "EWY",
    "FLNC", "FWDI", "GLW", "GME", "GOOGL", "GPRO", "HIMS", "HOOD", "HPE", "IBM", "INTC", "INTW", "IREN", "KORU", "LITE",
    "META", "MRNA", "MRVL", "MSFT", "MSTR", "MUU", "MVLL", "NBIS", "NFLX", "NOK", "NVDA", "ORCL", "PDD", "PLTR", "PYPL",
    "QCOM", "QNT", "QQQ", "RDDT", "RKLB", "SHAZ", "SKHY", "SMCI", "SMH", "SNDK", "SNXX", "SOXL", "SOXS", "SPCX", "SPY",
    "SQQQ", "STX", "TQQQ", "TSLA", "TSM", "USAR", "WDC", "WEN")}
LEV = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")


def _read(p):
    d = pd.read_csv(p)
    d["ts"] = pd.to_datetime(d.timestamp, utc=True).values.astype("datetime64[ms]").astype("int64")
    d = d.sort_values("ts", kind="mergesort").drop_duplicates("ts", keep="first").reset_index(drop=True)
    return d


def read_raw1m(coin):
    """archive raw 1m (CLAUDE.md exception): from 2025 the file wrote microsecond open times as if they were milliseconds, so
    the real open time in ms = the seconds count of the written datetime (same repair as src/btc_alltf/verify_bars.py).
    The file has no quote volume and no taker volume: quote_volume = volume * close (only used for nothing but the bar),
    taker_buy_base = NaN (taker-flow rules then never fire on these coins; disclosed)."""
    r = pd.read_csv(src_file(coin, "spot", "1m"))
    s = r.timestamp.astype(str)
    big = s.str.len() > 19
    ts = np.empty(len(r), np.int64)
    ts[~big.values] = pd.to_datetime(s[~big], utc=True).values.astype("datetime64[ms]").astype("int64")
    ts[big.values] = np.array(s[big].str.replace(" ", "T").values, dtype="datetime64[s]").astype("int64")
    r["ts"] = ts
    r = r.sort_values("ts", kind="mergesort").drop_duplicates("ts", keep="first").reset_index(drop=True)
    r["quote_volume"] = r.volume * r.close
    r["taker_buy_base"] = np.nan
    return r


def src_file(coin, kind, base):
    """kind: 'spot' (universe_all 1d/1h, universe_hf 15m/5m, archive raw 1m) or 'futures' (data/futures_um perp 1h)"""
    if kind == "futures":
        return PROJ / f"data/futures_um/{coin}_perp_1h.csv.gz"
    if base == "1d":
        return PROJ / f"data/universe_all/1d/{coin}_1d.csv"
    if base == "1h":
        return PROJ / f"data/universe_all/1h/{coin}_1h_full.csv.gz"
    if base in ("15m", "5m"):
        return PROJ / f"data/universe_hf/{base}/{coin}_{base}_full.csv.gz"
    if base == "1m":
        return PROJ / f"archive/cleanup_2026_10_15/data/raw/{coin}_1m_Raw_5Years.csv.gz"
    raise ValueError(base)


def agg(d, key):
    g = d.groupby(key, sort=True)
    return pd.DataFrame({"ts": g.ts.first(), "open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                         "volume": g.volume.sum(), "quote_volume": g.quote_volume.sum(), "taker_buy_base": g.taker_buy_base.sum()}).reset_index(drop=True)


def bars(coin, kind, tf, lo_ms, hi_ms):
    """bars of one coin in [lo_ms, hi_ms) for tf; resampled from the base file with the build_bars.py calendar
    (UTC-aligned fixed bars, Monday weeks). Futures files carry no taker_buy_base: taker_buy_quote * volume / quote_volume."""
    base = "1h" if kind == "futures" else BASE[tf]
    d = read_raw1m(coin) if base == "1m" else _read(src_file(coin, kind, base))
    if kind == "futures":
        d["taker_buy_base"] = d.taker_buy_quote * d.volume / d.quote_volume.replace(0, np.nan)
        d["taker_buy_base"] = d.taker_buy_base.fillna(0.0)
    d = d[(d.ts >= lo_ms) & (d.ts < hi_ms)][["ts", "open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base"]]
    d = d.reset_index(drop=True)
    if base == tf:
        return d
    if tf in TF_MS:
        o = agg(d.assign(k=d.ts // TF_MS[tf]), "k")
        o["ts"] = (o.ts // TF_MS[tf]) * TF_MS[tf]
        return o
    if tf == "1w":
        wk = (d.ts // DAY - 4) // 7
        o = agg(d.assign(k=wk), "k")
        o["ts"] = ((o.ts // DAY - 4) // 7 * 7 + 4) * DAY
        return o
    raise ValueError(tf)


def daily(coin, kind, lo_ms, hi_ms):
    """per calendar day of the grid [lo_ms, hi_ms): close (NaN where the coin has no data) and quote volume"""
    if kind == "futures":
        d = _read(src_file(coin, kind, "1h"))
        d = d[(d.ts >= lo_ms) & (d.ts < hi_ms)]
        g = d.groupby(d.ts // DAY)
        dd = pd.DataFrame({"close": g.close.last(), "qv": g.quote_volume.sum()})
    else:
        d = _read(src_file(coin, kind, "1d"))
        d = d[(d.ts >= lo_ms) & (d.ts < hi_ms)]
        dd = pd.DataFrame({"close": d.close.values, "qv": d.quote_volume.values}, index=d.ts.values // DAY)
    nd = (hi_ms - lo_ms) // DAY
    idx = np.arange(lo_ms // DAY, lo_ms // DAY + nd)
    dd = dd.reindex(idx)
    return dd.close.values.astype(float), dd.qv.values.astype(float)


def liquid_days(qv, min_usd, window):
    """eligible on day d if the mean quote volume of days d-window .. d-1 (all present) is >= min_usd (causal)"""
    s = pd.Series(qv)
    m = s.shift(1).rolling(window, min_periods=window).mean()
    return (m >= min_usd).values


# ------------------------------------------------------------------ daily mark-to-market
def mtm(k, t_in, t_out_eff, px_in, net, dirn, C, day0, nk, nd):
    """daily log-return matrix [nk, nd] of the trades (one position at a time per k), plus time in position [nk, nd] (days)
    and entries [nk, nd].
    k: row of each trade; t_in / t_out_eff ms (fill times); px_in entry price; net the trade's net return; dirn +-1 per trade;
    C: close of each grid day (NaN = no data, forward-filled here); day d of the grid = calendar day day0 + d.
    Day d's value: the position is marked at C[d] for every day close strictly inside the trade; the last day carries the
    rest, so that the sum over the trade equals log(1 + net) exactly (fees and funding land on the exit day)."""
    Cf = pd.Series(C).ffill().values
    k = np.asarray(k, np.int64)
    di = (np.asarray(t_in, np.int64) // DAY) - day0
    do = (np.asarray(t_out_eff, np.int64) // DAY) - day0
    do = np.minimum(do, nd - 1)
    di = np.minimum(di, do)
    lr = np.log1p(np.maximum(np.asarray(net, np.float64), -0.999999))
    L = np.bincount(k * nd + do, weights=lr, minlength=nk * nd)
    multi = np.nonzero(do > di)[0]
    if len(multi):
        km, a, b = k[multi], di[multi], do[multi]
        p0, dr = np.asarray(px_in, np.float64)[multi], np.asarray(dirn, np.float64)[multi]
        cnt = b - a                                                          # day closes inside the trade: days a .. b-1
        rep = np.repeat(np.arange(len(multi)), cnt)
        off = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        dd = a[rep] + off
        v = 1.0 + dr[rep] * (Cf[dd] / p0[rep] - 1.0)
        lv = np.log(np.maximum(v, 1e-6))
        prev = np.r_[0.0, lv[:-1]]
        first = off == 0
        prev[first] = 0.0
        seg = lv - prev
        L += np.bincount(km[rep] * nd + dd, weights=seg, minlength=nk * nd)
        last_lv = lv[np.cumsum(cnt) - 1]
        L -= np.bincount(km * nd + b, weights=last_lv, minlength=nk * nd)
    # time in position per day
    ti = np.asarray(t_in, np.int64)
    to = np.maximum(np.asarray(t_out_eff, np.int64), ti)
    X = np.zeros(nk * nd)
    same = do == di
    X += np.bincount(k[same] * nd + do[same], weights=(to[same] - ti[same]) / DAY, minlength=nk * nd)
    if len(multi):
        X += np.bincount(km * nd + a, weights=((a + day0 + 1) * DAY - ti[multi]) / DAY, minlength=nk * nd)
        X += np.bincount(km * nd + b, weights=(to[multi] - (b + day0) * DAY) / DAY, minlength=nk * nd)
        mid = cnt - 1
        if mid.sum():
            rep2 = np.repeat(np.arange(len(multi)), mid)
            off2 = np.arange(mid.sum()) - np.repeat(np.cumsum(mid) - mid, mid)
            X += np.bincount(km[rep2] * nd + a[rep2] + 1 + off2, minlength=nk * nd).astype(float)
    N = np.bincount(k * nd + di, minlength=nk * nd)
    return L.reshape(nk, nd), X.reshape(nk, nd), N.reshape(nk, nd)


def fill_time(t_out, reason, tf_ms):
    """time of the exit fill: an open fill (SIG, TIME, gaps) at the bar open; a touch inside the bar (SL, TP, TRAIL, LIQ,
    SL_AMBIG) at the middle of the bar; END (last close) at the bar end"""
    r = np.asarray(reason)
    add = np.where(np.isin(r, (3, 5, 7, 9, 11)), tf_ms // 2, np.where(r == 10, tf_ms - 1, 0))
    return np.asarray(t_out, np.int64) + add


# ------------------------------------------------------------------ statistics
def nw_lag(T):
    return int(np.floor(4 * (T / 100.0) ** (2.0 / 9.0)))


def nw_t(x, lag=None):
    """Newey-West (Bartlett) t of mean(x) > 0; returns (t, one-sided p with T-1 df, lag)"""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    T = len(x)
    if T < 30:
        return np.nan, 1.0, 0
    lag = nw_lag(T) if lag is None else lag
    u = x - x.mean()
    s = u @ u / T
    for j in range(1, lag + 1):
        s += 2 * (1 - j / (lag + 1)) * (u[j:] @ u[:-j]) / T
    if s <= 0:
        return np.nan, 1.0, lag
    t = x.mean() / np.sqrt(s / T)
    return float(t), float(tdist.sf(t, T - 1)), lag


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    if n == 0:
        return p
    o = np.argsort(p, kind="mergesort")
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(q, 1.0)
    return out


def perf(r):
    """r: daily simple returns (NaN = not in the window). CAGR (365-day years), annualised Sharpe (sqrt 365), max DD, total"""
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return dict(days=len(r), total=np.nan, cagr=np.nan, sharpe=np.nan, vol=np.nan, maxdd=np.nan)
    eq = np.cumprod(1 + r)
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    sd = r.std(ddof=1)
    return dict(days=len(r), total=float(eq[-1] - 1), cagr=float(eq[-1] ** (365.0 / len(r)) - 1) if eq[-1] > 0 else -1.0,
                sharpe=float(r.mean() / sd * np.sqrt(365)) if sd > 0 else np.nan, vol=float(sd * np.sqrt(365)),
                maxdd=float((1 - eq / peak).max()))
