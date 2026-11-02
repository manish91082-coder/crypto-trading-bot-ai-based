"""
Swings (verified ZigZag) vs Support/Resistance + Volume (protocol: logs/research_swing_vs_sr/SWING_SR_PROTOCOL_PREREGISTERED.md).
Part A: where do swing turns sit relative to active S/R levels and volume-at-price?  Part B: does an S/R(+volume) touch
become a swing turn more often than a control touch?
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "research", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import DATA_DIR, LOGS_DIR, SYMBOLS
import swing_study_1d as SS
import sr_levels_study as S
import sr_volume_study as V

OUT = LOGS_DIR / "research_swing_vs_sr"
PROTO = "SWING_SR_PROTOCOL_PREREGISTERED.md"
COINS = list(SYMBOLS)
WARM, EV_START, END = pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"), pd.Timestamp("2026-10-01")
KS, K_PRIMARY, KF, SEED = (2.0, 3.0, 4.0), 3.0, 3, 13
NEAR, BAND = 0.5, 0.25
VAP_W = {"1h": pd.Timedelta(days=7), "4h": pd.Timedelta(days=30), "1d": pd.Timedelta(days=90)}
TFL_FOR = {"1h": ["1h", "4h", "1d", "1w"], "4h": ["4h", "1d", "1w"], "1d": ["1d", "1w"]}


def with_atr(d):
    d = d.reset_index(drop=True).copy()
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    d["ATR_14"] = tr.rolling(14).mean()
    return d


def clip_wicks(d):
    bl, bh = d[["open", "close"]].min(axis=1), d[["open", "close"]].max(axis=1)
    bad_lo = (1 - d.low / bl) * 100 > SS.ANOMALY_WICK_PCT
    bad_hi = (d.high / bh - 1) * 100 > SS.ANOMALY_WICK_PCT
    d.loc[bad_lo, "low"] = bl[bad_lo]
    d.loc[bad_hi, "high"] = bh[bad_hi]
    return d, int(bad_lo.sum() + bad_hi.sum())


def load_bars(coin):
    h = pd.read_csv(DATA_DIR / "universe_all" / "1h" / f"{coin}_1h_full.csv.gz",
                    usecols=["timestamp", "open", "high", "low", "close", "quote_volume"], parse_dates=["timestamp"])
    assert h.timestamp.dtype.kind == "M"
    h = h.sort_values("timestamp")
    h = h[(h.timestamp >= WARM) & (h.timestamp < END)].reset_index(drop=True)
    h, nclip = clip_wicks(h)
    g = h.set_index("timestamp").resample("4h", label="left", closed="left")
    h4 = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last())).dropna().reset_index()
    d1 = SS.load_1d(coin)                                       # exactly the swing-study bars (clip + ATR)
    d1 = d1[d1.timestamp < END].reset_index(drop=True)
    g = d1.set_index("timestamp").resample("W-MON", label="left", closed="left")
    w1 = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last())).dropna().reset_index()
    return {"1h": with_atr(h), "4h": with_atr(h4), "1d": d1, "1w": w1}, h, nclip


def fractal_levels(b, k=KF):
    hi, lo, ts = b.high.values, b.low.values, b.timestamp.values
    n = len(b)
    idx = np.arange(n)
    inside = (idx >= k) & (idx < n - k - 1)
    ph = inside & (hi == pd.Series(hi).rolling(2 * k + 1, center=True).max().values)
    pl = inside & (lo == pd.Series(lo).rolling(2 * k + 1, center=True).min().values)
    out = {}
    for side, m, price in (("resistance", ph, hi), ("support", pl, lo)):
        ii = idx[m]
        out[side] = (price[ii], ts[ii + k + 1])                  # level, time it becomes known
    return out, ph | pl


def activate(levels, sw):
    """Map levels to swing-timeframe bars: activation index and index of the first close crossing (n if never)."""
    ts, cl, n = sw.timestamp.values, sw.close.values, len(sw)
    smin, smax = S.sparse(cl, np.inf, np.minimum), S.sparse(cl, -np.inf, np.maximum)
    res = {}
    for side, (L, ct) in levels.items():
        a = np.searchsorted(ts, ct, "left")
        ok = a < n
        L, a = L[ok], a[ok]
        if side == "support":
            brk = S.first_reach(smin, a, np.nextafter(L, -np.inf), False)
        else:
            brk = S.first_reach(smax, a, np.nextafter(L, np.inf), True)
        res[side] = (L, a, brk)
    return res


def near_active(p, x, side, atr_p, act):
    L, a, brk = act[side]
    m = (a <= p) & (brk >= p) & (np.abs(L - x) <= NEAR * atr_p)
    return bool(m.any())


def vap(h1, t, x, band, W):
    return V.vap_share(h1, pd.Timestamp(t), x, band, W)


def run_coin(coin, rng, g0rows):
    bars, h1raw, nclip = load_bars(coin)
    H1 = dict(ts=h1raw.timestamp.values, lo=h1raw.low.values, hi=h1raw.high.values, qv=h1raw.quote_volume.values)
    legs = pd.read_csv(OUT.parent / "swing_study_1d" / "swing_legs_1d.csv", parse_dates=["start_date"])
    lv = {tf: fractal_levels(bars[tf]) for tf in ("1h", "4h", "1d", "1w")}
    A_rows, B_rows = [], []
    for stf in ("1h", "4h", "1d"):
        sw = bars[stf]
        ts, atr, hi, lo = sw.timestamp.values, sw.ATR_14.values, sw.high.values, sw.low.values
        acts = {tfl: activate(lv[tfl][0], sw) for tfl in TFL_FOR[stf]}
        first = int(np.searchsorted(ts, EV_START.to_datetime64(), "left"))
        for K in KS:
            piv = SS.zigzag_pivots(sw, K)
            if stf == "1d":                                     # G0: reproduce the stored swing study exactly
                st = legs[(legs.symbol == coin) & (legs.K == K)].sort_values(["start_date", "start_price"])
                mine = pd.DataFrame(dict(d=[pd.Timestamp(ts[q["idx"]]) for q in piv[:-1]],
                                         p=[q["price"] for q in piv[:-1]])).sort_values(["d", "p"])   # same-day L+H pivots: order-free
                ok = len(st) == len(mine) and (st.start_date.values == mine.d.values).all() and \
                    np.allclose(st.start_price.values, mine.p.values, rtol=1e-9, atol=0)
                g0rows.append(dict(coin=coin, K=K, stored=len(st), recomputed=len(mine), identical=bool(ok)))
            P = [q for q in piv if q["idx"] >= max(first, 15)]
            nxt = {q["idx"]: piv[z + 1]["price"] for z, q in enumerate(piv[:-1])}
            # ---------- Part A ----------
            kinds = np.array([q["kind"] for q in P])
            cidx = np.sort(rng.choice(np.arange(max(first, 15), len(sw)), size=len(P), replace=False))
            ckind = rng.permutation(kinds)
            for grp, items in (("SWING", [(q["idx"], q["kind"], q["price"]) for q in P]),
                               ("CONTROL", [(int(i), kd, lo[i] if kd == "L" else hi[i]) for i, kd in zip(cidx, ckind)])):
                for p_, kd, x in items:
                    side = "support" if kd == "L" else "resistance"
                    a_ = atr[p_ - 1]
                    row = dict(coin=coin, swing_tf=stf, K=K, group=grp, idx=p_, kind=kd, price=x, atr=a_,
                               touch_time=pd.Timestamp(ts[p_]))
                    hits = {tfl: near_active(p_, x, side, a_, acts[tfl]) for tfl in TFL_FOR[stf]}
                    row.update({f"sr_{tfl}": float(h) for tfl, h in hits.items()})
                    row["sr_any"] = float(any(hits.values()))
                    row["vap"] = vap(H1, ts[p_], x, BAND * a_, VAP_W[stf])
                    if grp == "SWING" and p_ in nxt:
                        row["leg_atr"] = abs(nxt[p_] - x) / atr[p_]
                    A_rows.append(row)
            # ---------- Part B (same-timeframe levels, K = primary only) ----------
            if K != K_PRIMARY:
                continue
            pidx = {kd: np.array([q["idx"] for q in piv if q["kind"] == kd]) for kd in ("L", "H")}
            pprc = {kd: np.array([q["price"] for q in piv if q["kind"] == kd]) for kd in ("L", "H")}
            plegs = {kd: np.array([abs(nxt[q["idx"]] - q["price"]) / atr[q["idx"]] if q["idx"] in nxt else np.nan
                                   for q in piv if q["kind"] == kd]) for kd in ("L", "H")}
            levels_real, ispiv = fractal_levels(sw)
            idx = np.arange(len(sw))
            inside = (idx >= KF) & (idx < len(sw) - KF - 1)
            smax, smin = S.sparse(hi, -np.inf, np.maximum), S.sparse(lo, np.inf, np.minimum)
            for kind_lvl in ("REAL", "CONTROL"):
                for side, price in (("resistance", hi), ("support", lo)):
                    if kind_lvl == "REAL":
                        mask = inside & (hi == pd.Series(hi).rolling(7, center=True).max().values) if side == "resistance" \
                            else inside & (lo == pd.Series(lo).rolling(7, center=True).min().values)
                        ii = idx[mask]
                    else:
                        non = idx[inside & ~ispiv]
                        nreal = len(levels_real[side][0])
                        ii = np.sort(rng.choice(non, size=min(nreal, len(non)), replace=False))
                    L = price[ii]
                    a = ii + KF + 1
                    ok = (L > sw.close.values[a - 1]) if side == "resistance" else (L < sw.close.values[a - 1])
                    L, a = L[ok], a[ok]
                    j = S.first_reach(smax if side == "resistance" else smin, a, L, side == "resistance")
                    t = (j < len(sw)) & (j >= max(first, 15))
                    L, j = L[t], j[t]
                    kd = "H" if side == "resistance" else "L"
                    for lv_, jj in zip(L, j):
                        a_ = atr[jj - 1]
                        lo_i, hi_i = np.searchsorted(pidx[kd], jj, "left"), np.searchsorted(pidx[kd], jj + 2, "right")
                        cand = np.arange(lo_i, hi_i)
                        hit = cand[np.abs(pprc[kd][cand] - lv_) <= NEAR * a_] if len(cand) else cand
                        row = dict(coin=coin, swing_tf=stf, kind=kind_lvl, side=side, level=lv_, touch_i=int(jj), atr=a_,
                                   touch_time=pd.Timestamp(ts[jj]), turn=float(len(hit) > 0),
                                   leg_atr=float(plegs[kd][hit[0]]) if len(hit) else np.nan)
                        if kind_lvl == "REAL":
                            row["vap"] = vap(H1, ts[jj], lv_, BAND * a_, VAP_W[stf])
                        B_rows.append(row)
    return pd.DataFrame(A_rows), pd.DataFrame(B_rows), nclip


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = hashlib.sha256((OUT / PROTO).read_bytes()).hexdigest()
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    g0rows, A, B, clips = [], [], [], {}
    for coin in COINS:
        a, b, nc = run_coin(coin, rng, g0rows)
        A.append(a)
        B.append(b)
        clips[coin] = nc
        print(coin, len(a), len(b), f"({time.time()-t0:.0f}s)", flush=True)
    G0 = pd.DataFrame(g0rows)
    G0.to_csv(OUT / "G0_reproduce_swing_study.csv", index=False)
    A, B = pd.concat(A, ignore_index=True), pd.concat(B, ignore_index=True)
    claims = dict(protocol_sha256=h_, G0_all_identical=bool(G0.identical.all()), G0=G0.to_dict("records"), clipped_1h_wicks=clips)
    print("G0 identical:", claims["G0_all_identical"], flush=True)

    # VAP_high threshold: 2/3 quantile of CONTROL VAP per (swing_tf, K)
    A["vap_high"] = np.nan
    for (stf, K), g in A.groupby(["swing_tf", "K"]):
        thr = g[g.group == "CONTROL"].vap.quantile(2 / 3)
        A.loc[g.index, "vap_high"] = np.where(g.vap.isna(), np.nan, (g.vap > thr).astype(float))
    A["sr_and_vap"] = np.where(A.vap_high.isna(), np.nan, A.sr_any * A.vap_high)
    A.to_csv(OUT / "partA_pivots_and_control.csv.gz", index=False, compression="gzip")
    TA = []
    for (stf, K), g in A.groupby(["swing_tf", "K"]):
        for col in ["sr_any", "vap_high", "sr_and_vap"] + [f"sr_{t}" for t in TFL_FOR[stf]]:
            r = V.boot(g, col, "group", "SWING", "CONTROL")
            if r:
                TA.append(dict(swing_tf=stf, K=K, measure=col, **r))
        s = g[g.group == "SWING"].assign(combo=lambda x: np.where(x.sr_and_vap == 1, "YES", "NO"))
        r = V.boot(s.dropna(subset=["leg_atr"]), "leg_atr", "combo", "YES", "NO")
        if r:
            TA.append(dict(swing_tf=stf, K=K, measure="leg_atr_combo_yes_minus_no", **r))
    TA = pd.DataFrame(TA)
    TA.to_csv(OUT / "partA_table.csv", index=False)

    R = B[B.kind == "REAL"].copy()
    R["vap_t"] = ""
    for stf, g in R.groupby("swing_tf"):
        q1, q2 = g.vap.dropna().quantile([1 / 3, 2 / 3]).values
        R.loc[g.index, "vap_t"] = np.where(g.vap.isna(), "", np.where(g.vap <= q1, "low", np.where(g.vap <= q2, "mid", "high")))
    B = B.join(R[["vap_t"]])
    B.to_csv(OUT / "partB_events.csv.gz", index=False, compression="gzip")
    TB = []
    for stf, g in B.groupby("swing_tf"):
        for side in ("support", "resistance", "both"):
            s = g[(g.side == side) | (side == "both")]
            for name, d, grp, a_, b_ in (("REAL_vs_CONTROL", s, "kind", "REAL", "CONTROL"),
                                         ("REALhighVAP_vs_CONTROL", s[(s.kind == "CONTROL") | (s.vap_t == "high")], "kind", "REAL", "CONTROL"),
                                         ("REAL_highVAP_vs_lowVAP", s[s.kind == "REAL"], "vap_t", "high", "low")):
                r = V.boot(d, "turn", grp, a_, b_)
                if r:
                    TB.append(dict(swing_tf=stf, side=side, comparison=name, **r))
            lt = s[(s.kind == "REAL") & (s.turn == 1)]
            TB.append(dict(swing_tf=stf, side=side, comparison="median_leg_atr_after_REAL_turn", mean_a=float(lt.leg_atr.median()),
                           n_a=int(lt.leg_atr.notna().sum())))
    TB = pd.DataFrame(TB)
    TB.to_csv(OUT / "partB_table.csv", index=False)
    claims["partA"] = TA.to_dict("records")
    claims["partB"] = TB.to_dict("records")
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    print(G0.groupby("K").identical.all().to_dict())
    print(TA.to_string(index=False))
    print(TB.to_string(index=False))
    print(f"done ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
