"""
Big-timeframe levels, volume at levels, and what happens after a break.
Protocol: logs/research_sr_volume/SRV_STUDY_PROTOCOL_PREREGISTERED.md (SHA256 locked before any result).
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import DATA_DIR, LOGS_DIR
import sr_levels_study as S          # sparse(), first_reach() (verified in the S/R study)

OUT = LOGS_DIR / "research_sr_volume"
PROTO = "SRV_STUDY_PROTOCOL_PREREGISTERED.md"
COINS = S.COINS
WARM, EV_START, END = pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"), pd.Timestamp("2026-10-01")
SEED, BAND = 11, 0.25
EVAL = {"1h": dict(H=48, F=24, W=pd.Timedelta(hours=168)), "1d": dict(H=30, F=10, W=pd.Timedelta(days=90))}
FAMILIES = [("P1h", "1h", "1h", 3), ("P4h", "4h", "1h", 3), ("P1d", "1d", "1d", 3), ("P1w", "1w", "1d", 3), ("P1M", "1M", "1d", 2)]
RANGES = [30, 90, 180, 365]


def load(coin, tf):
    if tf == "1h":
        d = pd.read_csv(DATA_DIR / "universe_all" / "1h" / f"{coin}_1h_full.csv.gz",
                        usecols=["timestamp", "open", "high", "low", "close", "quote_volume"], parse_dates=["timestamp"])
    else:
        d = pd.read_csv(DATA_DIR / "universe_all" / "1d" / f"{coin}_1d.csv",
                        usecols=["timestamp", "open", "high", "low", "close", "quote_volume"], parse_dates=["timestamp"])
    assert d.timestamp.dtype.kind == "M"
    d = d.sort_values("timestamp")
    return d[(d.timestamp >= WARM) & (d.timestamp < END)].reset_index(drop=True)


def agg(d, rule):
    g = d.set_index("timestamp").resample(rule, label="left", closed="left")
    b = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last()))
    return b.dropna().reset_index()


def level_bars(h1, d1, tf):
    return {"1h": h1, "4h": agg(h1, "4h"), "1d": d1, "1w": agg(d1, "W-MON"), "1M": agg(d1, "MS")}[tf]


def atr14(b):
    hi, lo, cl = b.high.values, b.low.values, b.close.values
    pc = np.r_[np.nan, cl[:-1]]
    tr = np.nanmax(np.c_[hi - lo, np.abs(hi - pc), np.abs(lo - pc)], axis=1)
    return pd.Series(tr).rolling(14).mean().values


def outcomes(E, side_res, L, j, H, F):
    """Touch outcome, break bar, aftermath and forward return for levels L first touched at eval bar j."""
    hi, lo, cl, atr, n = E["hi"], E["lo"], E["cl"], E["atr"], E["n"]
    smax, smin = E["smax"], E["smin"]
    A = atr[j - 1]
    if side_res:
        brk_bar = hi[j] >= L + A
        jb = S.first_reach(smax, j + 1, L + A, True)
        jr = S.first_reach(smin, j + 1, L - A, False)
    else:
        brk_bar = lo[j] <= L - A
        jb = S.first_reach(smin, j + 1, L - A, False)
        jr = S.first_reach(smax, j + 1, L + A, True)
    jb = np.where(jb <= j + H, jb, n)
    jr = np.where(jr <= j + H, jr, n)
    out = np.where(brk_bar, "BREAK", np.where((jb == n) & (jr == n), "TIMEOUT",
                   np.where(jb == jr, "AMBIGUOUS", np.where(jr < jb, "BOUNCE", "BREAK"))))
    b = np.where(brk_bar, j, jb)
    isb = out == "BREAK"
    bb = np.where(isb, b, 0)
    if side_res:
        cont_bar = hi[bb] >= L + 2 * A
        jc = S.first_reach(smax, bb + 1, L + 2 * A, True)
        jk = S.first_reach(smin, bb + 1, L, False)
    else:
        cont_bar = lo[bb] <= L - 2 * A
        jc = S.first_reach(smin, bb + 1, L - 2 * A, False)
        jk = S.first_reach(smax, bb + 1, L, True)
    jc = np.where(jc <= bb + H, jc, n)
    jk = np.where(jk <= bb + H, jk, n)
    aft = np.where(~isb, "", np.where(cont_bar, "CONTINUE", np.where((jc == n) & (jk == n), "TIMEOUT",
                   np.where(jc == jk, "AMBIGUOUS", np.where(jk < jc, "RECLAIM", "CONTINUE")))))
    okf = isb & (bb + F < n)
    fwd = np.where(okf, cl[np.minimum(bb + F, n - 1)] / cl[bb] - 1, np.nan)
    return A, out, np.where(isb, b, -1), aft, fwd


def vap_share(h1, t, L, band, W):
    ts, lo, hi, qv = h1["ts"], h1["lo"], h1["hi"], h1["qv"]
    a = np.searchsorted(ts, (t - W).to_datetime64(), "left")
    z = np.searchsorted(ts, t.to_datetime64(), "left")
    if z - a < 10:
        return np.nan
    s = slice(a, z)
    hit = (lo[s] <= L + band) & (hi[s] >= L - band)
    tot = qv[s].sum()
    return float(qv[s][hit].sum() / tot) if tot > 0 else np.nan


def run_coin(coin, rng):
    h1, d1 = load(coin, "1h"), load(coin, "1d")
    H1 = dict(ts=h1.timestamp.values, lo=h1.low.values, hi=h1.high.values, qv=h1.quote_volume.values)
    evals = {}
    for tf, b in (("1h", h1), ("1d", d1)):
        evals[tf] = dict(b=b, ts=b.timestamp.values, hi=b.high.values, lo=b.low.values, cl=b.close.values, n=len(b),
                         atr=atr14(b), smax=S.sparse(b.high.values, -np.inf, np.maximum), smin=S.sparse(b.low.values, np.inf, np.minimum))
    rows = []

    def emit(fam, kind, side, E, L, j, extra):
        prm = EVAL[E["tf"]]
        A, out, b, aft, fwd = outcomes(E, side == "resistance", L, j, prm["H"], prm["F"])
        t = pd.to_datetime(E["ts"][j])
        keep = (t >= EV_START) & np.isfinite(A) & (A > 0)
        df = pd.DataFrame(dict(coin=coin, family=fam, kind=kind, side=side, level=L, touch_i=j, touch_time=t, atr=A,
                               outcome=out, break_i=b, after=aft, fwd=fwd, **extra))[keep]
        if kind == "REAL" and len(df):
            df["vap"] = [vap_share(H1, pd.Timestamp(tt), lv, BAND * a, prm["W"]) for tt, lv, a in zip(df.touch_time, df.level, df.atr)]
        rows.append(df)

    for fam, ltf, etf, k in FAMILIES:
        E = dict(evals[etf], tf=etf)
        bl = level_bars(h1, d1, ltf)
        hi, lo = bl.high.values, bl.low.values
        n = len(bl)
        idx = np.arange(n)
        inside = (idx >= k) & (idx < n - k - 1)                 # bar i+k+1 must exist (its start = confirmation time)
        win = 2 * k + 1
        piv_h = inside & (hi == pd.Series(hi).rolling(win, center=True).max().values)
        piv_l = inside & (lo == pd.Series(lo).rolling(win, center=True).min().values)
        for side, piv, price in (("resistance", piv_h, hi), ("support", piv_l, lo)):
            real = idx[piv]
            non = idx[inside & ~piv]
            ctrl = np.sort(rng.choice(non, size=min(len(real), len(non)), replace=False))
            for kind, ii in (("REAL", real), ("CONTROL", ctrl)):
                L = price[ii]
                conf_t = bl.timestamp.values[ii + k + 1]
                a = np.searchsorted(E["ts"], conf_t, "left")
                ok = (a >= 1) & (a < E["n"])
                ii, L, a = ii[ok], L[ok], a[ok]
                ok = (L > E["cl"][a - 1]) if side == "resistance" else (L < E["cl"][a - 1])
                ii, L, a = ii[ok], L[ok], a[ok]
                j = S.first_reach(E["smax"] if side == "resistance" else E["smin"], a, L, side == "resistance")
                t = j < E["n"]
                emit(fam, kind, side, E, L[t], j[t], dict(level_bar_i=ii[t], active_i=a[t]))
    E = dict(evals["1d"], tf="1d")
    lo_s, hi_s = pd.Series(E["lo"]), pd.Series(E["hi"])
    for N in RANGES:
        pmin = lo_s.rolling(N).min().shift(1).values
        pmax = hi_s.rolling(N).max().shift(1).values
        jj = np.arange(1, E["n"])
        sup = jj[(E["lo"][jj] <= pmin[jj]) & (E["lo"][jj - 1] > pmin[jj - 1])]
        res = jj[(E["hi"][jj] >= pmax[jj]) & (E["hi"][jj - 1] < pmax[jj - 1])]
        emit(f"R{N}", "REAL", "support", E, pmin[sup], sup, dict(level_bar_i=-1, active_i=sup))
        emit(f"R{N}", "REAL", "resistance", E, pmax[res], res, dict(level_bar_i=-1, active_i=res))
    base = {}
    for tf in ("1h", "1d"):
        cl, F = evals[tf]["cl"], EVAL[tf]["F"]
        ts = evals[tf]["ts"]
        r = cl[F:] / cl[:-F] - 1
        m = ts[:-F] >= EV_START.to_datetime64()
        base[tf] = (float(r[m].sum()), int(m.sum()))
    return pd.concat(rows, ignore_index=True), base


def boot(df, val, grp=None, a=None, b=None, reps=2000, seed=1):
    """Mean of `val` (or difference of means grp==a minus grp==b) with a month-block bootstrap 95 % CI."""
    d = df.dropna(subset=[val]).assign(m=lambda x: pd.to_datetime(x.touch_time).dt.to_period("M").astype(str))
    if grp is None:
        g = d.groupby("m")[val].agg(["sum", "count"])
        s, c = g["sum"].values, g["count"].values
        if c.sum() == 0:
            return None
        rng = np.random.default_rng(seed)
        bs = [s[k].sum() / c[k].sum() for k in (rng.integers(0, len(g), len(g)) for _ in range(reps)) if c[k].sum()]
        return dict(n=int(c.sum()), mean=round(s.sum() / c.sum(), 4), ci_low=round(float(np.percentile(bs, 2.5)), 4),
                    ci_high=round(float(np.percentile(bs, 97.5)), 4))
    d = d[d[grp].isin([a, b])]
    g = d.groupby(["m", grp])[val].agg(["sum", "count"]).unstack(grp).fillna(0)
    if ("sum", a) not in g or ("sum", b) not in g:
        return None
    sa, ca, sb, cb = g[("sum", a)].values, g[("count", a)].values, g[("sum", b)].values, g[("count", b)].values
    if ca.sum() == 0 or cb.sum() == 0:
        return None
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(reps):
        k = rng.integers(0, len(g), len(g))
        if ca[k].sum() and cb[k].sum():
            bs.append(sa[k].sum() / ca[k].sum() - sb[k].sum() / cb[k].sum())
    return dict(n_a=int(ca.sum()), n_b=int(cb.sum()), mean_a=round(sa.sum() / ca.sum(), 4), mean_b=round(sb.sum() / cb.sum(), 4),
                diff=round(sa.sum() / ca.sum() - sb.sum() / cb.sum(), 4), ci_low=round(float(np.percentile(bs, 2.5)), 4),
                ci_high=round(float(np.percentile(bs, 97.5)), 4))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = hashlib.sha256((OUT / PROTO).read_bytes()).hexdigest()
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    parts, base = [], {"1h": [0.0, 0], "1d": [0.0, 0]}
    for coin in COINS:
        ev, bs = run_coin(coin, rng)
        parts.append(ev)
        for tf in bs:
            base[tf][0] += bs[tf][0]
            base[tf][1] += bs[tf][1]
        print(coin, len(ev), f"({time.time()-t0:.0f}s)", flush=True)
    E = pd.concat(parts, ignore_index=True)
    basemean = {tf: base[tf][0] / base[tf][1] for tf in base}
    fam_tf = {f: e for f, _, e, _ in FAMILIES} | {f"R{N}": "1d" for N in RANGES}
    E["fwd_excess"] = E.fwd - E.family.map(fam_tf).map(basemean)
    E["is_break"] = np.where(E.outcome.isin(["BREAK", "BOUNCE"]), (E.outcome == "BREAK").astype(float), np.nan)
    E["is_reclaim"] = np.where(E["after"].isin(["RECLAIM", "CONTINUE"]), (E["after"] == "RECLAIM").astype(float), np.nan)
    R = E[E.kind == "REAL"].copy()
    R["vap_t"] = ""
    for f_, g_ in R.groupby("family"):
        v_ = g_.vap.dropna()
        if len(v_) > 30:
            q1, q2 = v_.quantile([1 / 3, 2 / 3]).values
            R.loc[g_.index, "vap_t"] = np.where(g_.vap.isna(), "", np.where(g_.vap <= q1, "low", np.where(g_.vap <= q2, "mid", "high")))
    E.to_csv(OUT / "events.csv.gz", index=False, compression="gzip")
    R[["coin", "family", "side", "touch_i", "vap", "vap_t"]].to_csv(OUT / "real_vap_terciles.csv.gz", index=False, compression="gzip")
    claims = dict(protocol_sha256=h_, events=len(E), baseline_mean_fwd=basemean)
    A1, A2, A3, A4 = [], [], [], []
    fams = [f for f, *_ in FAMILIES] + [f"R{N}" for N in RANGES]
    for f in fams:
        for side in ("support", "resistance", "both"):
            sel = (E.family == f) & ((E.side == side) | (side == "both"))
            r = boot(E[sel & (E.kind == "REAL")], "is_break")
            if r:
                row = dict(family=f, side=side, **{f"real_{k}": v for k, v in r.items()})
                c = boot(E[sel], "is_break", "kind", "REAL", "CONTROL")
                if c:
                    row.update(real_minus_control=c["diff"], rc_ci_low=c["ci_low"], rc_ci_high=c["ci_high"], control_rate=c["mean_b"])
                A1.append(row)
            Rs = R[(R.family == f) & ((R.side == side) | (side == "both"))]
            v = boot(Rs, "is_break", "vap_t", "high", "low")
            if v:
                A2.append(dict(family=f, side=side, **v))
            rr = boot(Rs, "is_reclaim")
            vr = boot(Rs, "is_reclaim", "vap_t", "high", "low")
            if rr:
                A3.append(dict(family=f, side=side, **{f"reclaim_{k}": x for k, x in rr.items()},
                               **({f"hi_minus_lo_{k}": x for k, x in vr.items()} if vr else {})))
            if side != "both":
                Bk = Rs[Rs.outcome == "BREAK"]
                fa, fh = boot(Bk, "fwd_excess"), boot(Bk[Bk.vap_t == "high"], "fwd_excess")
                if fa:
                    A4.append(dict(family=f, side=side, **{f"all_{k}": x for k, x in fa.items()},
                                   **({f"highvap_{k}": x for k, x in fh.items()} if fh else {})))
    comps = {}
    for a, b in (("R365", "R30"), ("R180", "R30"), ("P1M", "P1d"), ("P1w", "P1d"), ("P1d", "P1h")):
        d = R[R.family.isin([a, b])]
        comps[f"{a}_minus_{b}_break_rate"] = boot(d, "is_break", "family", a, b)
        comps[f"{a}_minus_{b}_reclaim_rate"] = boot(d, "is_reclaim", "family", a, b)
    for name, T in (("A1_strength", A1), ("A2_volume_break", A2), ("A3_reclaim", A3), ("A4_fwd_after_break", A4)):
        pd.DataFrame(T).to_csv(OUT / f"{name}.csv", index=False)
        claims[name] = T
    claims["family_comparisons"] = comps
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 30)
    for name in ("A1_strength", "A2_volume_break", "A3_reclaim", "A4_fwd_after_break"):
        print("\n==", name)
        print(pd.read_csv(OUT / f"{name}.csv").to_string(index=False))
    print("\n== comparisons")
    for k, v in comps.items():
        print(k, v)
    print(f"done ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
