"""
Support/Resistance evidence study (protocol: logs/research_sr_levels/SR_STUDY_PROTOCOL_PREREGISTERED.md).
Do swing levels stop the price more often than ordinary levels? Per timeframe 5m..1w, by level age, with 1h-1d confluence.
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "research_sr_levels"
PROTO = "SR_STUDY_PROTOCOL_PREREGISTERED.md"
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT", "AVAXUSDT", "TRXUSDT"]
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-10-01")
K, M, H, SEED = 3, 1.0, 48, 7
TFS = ["5m", "15m", "30m", "1h", "4h", "8h", "12h", "1d", "1w"]
AGE_BINS = [(0, 50), (51, 500), (501, 10 ** 9)]


def load(path, cols=("timestamp", "open", "high", "low", "close")):
    d = pd.read_csv(path, usecols=list(cols), parse_dates=["timestamp"])
    assert d.timestamp.dtype.kind == "M", path
    d = d.sort_values("timestamp")
    return d[(d.timestamp >= START) & (d.timestamp < END)].reset_index(drop=True)


def agg(d, rule):
    g = d.set_index("timestamp").resample(rule, label="left", closed="left")
    b = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last()))
    return b.dropna().reset_index()


def bars(coin, tf):
    hf, ua = DATA_DIR / "universe_hf", DATA_DIR / "universe_all"
    if tf in ("5m", "15m"):
        return load(hf / tf / f"{coin}_{tf}_full.csv.gz")
    if tf == "30m":
        return agg(load(hf / "5m" / f"{coin}_5m_full.csv.gz"), "30min")
    if tf == "1h":
        return load(ua / "1h" / f"{coin}_1h_full.csv.gz")
    if tf in ("4h", "8h", "12h"):
        return agg(load(ua / "1h" / f"{coin}_1h_full.csv.gz"), tf)
    d = load(ua / "1d" / f"{coin}_1d.csv")
    return d if tf == "1d" else agg(d, "W-MON")          # weeks labelled by their Monday start (left edge)


def sparse(a, fill, op):
    """Sparse table st[k][i] = op(a[i .. i+2^k-1]); arrays padded with `fill`."""
    n = len(a)
    K_ = max(1, int(np.ceil(np.log2(n + 1))))
    pad = np.full(n + (1 << K_) + 1, fill)
    pad[:n] = a
    st = [pad]
    for k in range(1, K_ + 1):
        prev = st[-1]
        cur = np.full_like(prev, fill)
        h = 1 << (k - 1)
        cur[:-h] = op(prev[:-h], prev[h:])
        st.append(cur)
    return st


def first_reach(st, start, target, upward):
    """First index >= start where a >= target (upward) or a <= target (downward); len(a) if none. Vectorised."""
    n = len(st[0]) - (1 << (len(st) - 1)) - 1
    pos = start.astype(np.int64).copy()
    for k in range(len(st) - 1, -1, -1):
        p = np.minimum(pos, len(st[k]) - 1)
        blk = st[k][p]
        ok = (blk < target) if upward else (blk > target)
        ok &= pos < n
        pos = np.where(ok, pos + (1 << k), pos)
    return np.minimum(pos, n)


def events_for(b, coin, tf, rng):
    hi, lo, cl = b.high.values, b.low.values, b.close.values
    n = len(b)
    pc = np.r_[np.nan, cl[:-1]]
    tr = np.nanmax(np.c_[hi - lo, np.abs(hi - pc), np.abs(lo - pc)], axis=1)
    atr = pd.Series(tr).rolling(14).mean().values
    win = 2 * K + 1
    rh = pd.Series(hi).rolling(win, center=True).max().values
    rl = pd.Series(lo).rolling(win, center=True).min().values
    idx = np.arange(n)
    inside = (idx >= K) & (idx < n - K)
    piv_h = inside & (hi == rh)
    piv_l = inside & (lo == rl)
    st_hi_max, st_lo_min = sparse(hi, -np.inf, np.maximum), sparse(lo, np.inf, np.minimum)
    out = []
    for side, piv, price in (("resistance", piv_h, hi), ("support", piv_l, lo)):
        real_i = idx[piv]
        nonpiv = idx[inside & ~piv]
        ctrl_i = np.sort(rng.choice(nonpiv, size=min(len(real_i), len(nonpiv)), replace=False))
        for kind, ii in (("REAL", real_i), ("CONTROL", ctrl_i)):
            c = ii + K
            L = price[ii]
            ok = (L > cl[c]) if side == "resistance" else (L < cl[c])
            ii, c, L = ii[ok], c[ok], L[ok]
            j = first_reach(st_hi_max if side == "resistance" else st_lo_min, c + 1, L, side == "resistance")
            t = j < n
            ii, c, L, j = ii[t], c[t], L[t], j[t]
            a = atr[j - 1]
            good = np.isfinite(a) & (a > 0)
            ii, c, L, j, a = ii[good], c[good], L[good], j[good], a[good]
            if side == "resistance":
                brk_bar = hi[j] >= L + M * a
                jb = first_reach(st_hi_max, j + 1, L + M * a, True)          # break: high >= L + ATR
                jr = first_reach(st_lo_min, j + 1, L - M * a, False)         # bounce: low <= L - ATR
            else:
                brk_bar = lo[j] <= L - M * a
                jb = first_reach(st_lo_min, j + 1, L - M * a, False)
                jr = first_reach(st_hi_max, j + 1, L + M * a, True)
            lim = j + H
            jb = np.where(jb <= lim, jb, n)
            jr = np.where(jr <= lim, jr, n)
            res = np.where(brk_bar, "BREAK", np.where((jb == n) & (jr == n), "TIMEOUT",
                           np.where(jb == jr, "AMBIGUOUS", np.where(jr < jb, "BOUNCE", "BREAK"))))
            out.append(pd.DataFrame(dict(coin=coin, tf=tf, side=side, kind=kind, bar_i=ii, confirm_i=c, touch_i=j,
                                         level=L, atr=a, atr_pct=a / L * 100, age=j - c, outcome=res,
                                         touch_time=b.timestamp.values[j])))
    return pd.concat(out, ignore_index=True)


def boot_diff(E, n=2000, seed=1):
    E = E[E.outcome.isin(["BOUNCE", "BREAK"])]
    E = E.assign(m=pd.to_datetime(E.touch_time).dt.to_period("M").astype(str), y=(E.outcome == "BOUNCE").astype(float))
    g = E.groupby(["m", "kind"]).y.agg(["sum", "count"]).unstack("kind").fillna(0)
    if ("sum", "REAL") not in g or ("sum", "CONTROL") not in g:
        return None
    sr, cr, sc, cc = (g[("sum", "REAL")].values, g[("count", "REAL")].values, g[("sum", "CONTROL")].values, g[("count", "CONTROL")].values)
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(n):
        k = rng.integers(0, len(g), len(g))
        if cr[k].sum() and cc[k].sum():
            d.append(sr[k].sum() / cr[k].sum() - sc[k].sum() / cc[k].sum())
    pr, pcn = sr.sum() / cr.sum(), sc.sum() / cc.sum()
    return dict(n_real=int(cr.sum()), n_ctrl=int(cc.sum()), bounce_real=round(pr, 4), bounce_ctrl=round(pcn, 4),
                diff=round(pr - pcn, 4), ci_low=round(float(np.percentile(d, 2.5)), 4), ci_high=round(float(np.percentile(d, 97.5)), 4))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = hashlib.sha256((OUT / PROTO).read_bytes()).hexdigest()
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    allev = []
    for tf in TFS:
        for coin in COINS:
            b = bars(coin, tf)
            allev.append(events_for(b, coin, tf, rng))
        print(tf, "done", f"({time.time()-t0:.0f}s)", flush=True)
    E = pd.concat(allev, ignore_index=True)
    E.to_csv(OUT / "events.csv.gz", index=False, compression="gzip")
    claims = dict(protocol_sha256=h_, events=len(E), outcome_counts={f"{k[0]}|{k[1]}": v for k, v in E.groupby(["tf", "kind"]).outcome.value_counts().unstack().fillna(0).astype(int).to_dict("index").items()})

    rows = []
    for tf in TFS:
        for side in ("support", "resistance", "both"):
            S = E[(E.tf == tf) & ((E.side == side) | (side == "both"))]
            r = boot_diff(S)
            if r:
                rows.append(dict(tf=tf, side=side, part="all", **r, median_atr_pct=round(float(S[S.kind == "REAL"].atr_pct.median()), 3)))
            for lo_, hi_ in AGE_BINS:
                r = boot_diff(S[(S.age >= lo_) & (S.age <= hi_)])
                if r and side == "both":
                    rows.append(dict(tf=tf, side=side, part=f"age {lo_}-{hi_ if hi_ < 10**9 else 'inf'} bars", **r))
    T = pd.DataFrame(rows)
    sup = T[(T.side == "support") & (T.part == "all")].copy()
    sup["gross_ev_pct"] = ((2 * sup.bounce_real - 1) * sup.median_atr_pct).round(3)
    sup["ev_minus_020"] = (sup.gross_ev_pct - 0.20).round(3)
    sup["ev_minus_050"] = (sup.gross_ev_pct - 0.50).round(3)
    T.to_csv(OUT / "results_table.csv", index=False)
    sup.to_csv(OUT / "support_economics.csv", index=False)
    claims["results"] = rows
    claims["support_economics"] = sup.to_dict("records")

    # confluence: 1h REAL touches vs 1d REAL levels (same side, confirmed before touch, within 365 days, within 0.5 ATR(1h))
    conf = []
    for coin in COINS:
        b1 = bars(coin, "1h")
        bd = bars(coin, "1d")
        Eh = E[(E.tf == "1h") & (E.coin == coin) & (E.kind == "REAL")].copy()
        Ed = E[(E.tf == "1d") & (E.coin == coin) & (E.kind == "REAL")][["side", "confirm_i", "level"]].copy()
        Ed["ctime"] = bd.timestamp.values[Ed.confirm_i.values] + np.timedelta64(1, "D")      # known after the daily close
        for side in ("support", "resistance"):
            eh = Eh[Eh.side == side]
            ed = Ed[Ed.side == side]
            tt = pd.to_datetime(eh.touch_time).values
            flag = np.zeros(len(eh), bool)
            lv, ct = ed.level.values, ed.ctime.values
            for q, (t, L, a) in enumerate(zip(tt, eh.level.values, eh.atr.values)):
                m = (ct <= t) & (ct >= t - np.timedelta64(365, "D")) & (np.abs(lv - L) <= 0.5 * a)
                flag[q] = m.any()
            conf.append(eh.assign(confluence=flag))
    C = pd.concat(conf)
    C = C[C.outcome.isin(["BOUNCE", "BREAK"])]
    C2 = C.assign(kind=np.where(C.confluence, "REAL", "CONTROL"))           # reuse bootstrap: REAL=with, CONTROL=without
    claims["confluence_1h_with_vs_without_1d"] = boot_diff(C2)
    claims["confluence_share"] = float(C.confluence.mean())
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    pd.set_option("display.width", 250)
    print(T.to_string(index=False))
    print(sup[["tf", "bounce_real", "bounce_ctrl", "median_atr_pct", "gross_ev_pct", "ev_minus_020", "ev_minus_050"]].to_string(index=False))
    print("confluence 1h with 1d:", claims["confluence_1h_with_vs_without_1d"], "share", round(claims["confluence_share"], 3))
    print(f"done ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
