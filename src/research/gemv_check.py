"""GEMV: re-implementation of the Gemini notebook's evaluate_real_candle_path + three fill models on our verified data
(protocol logs/research_gemini_review/GEMV_PROTOCOL_PREREGISTERED.md). The notebook itself is NOT executed."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "research_gemini_review"
CORE10 = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "DOTUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
C_MAKER, C_SL, H = 0.00051, 0.00085, 20


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def path_r(p_en, d, one_r, sl_p, hs, ls, cs, be_trig_r=0.70, c_maker_rt=C_MAKER, c_sl_rt=C_SL):
    """line-for-line port of the notebook's evaluate_real_candle_path (Step 11.R2 cell)."""
    rem_w, realized_r = 1.0, 0.0
    tp1_done = tp2_done = be_locked = False
    curr_sl = (p_en - one_r) if d == 1 else (p_en + one_r)
    tp1_p, tp2_p, tp3_p = p_en + d * 1.20 * one_r, p_en + d * 2.30 * one_r, p_en + d * 3.60 * one_r
    ext_p = p_en
    fm, fs = c_maker_rt / (sl_p + 1e-8), c_sl_rt / (sl_p + 1e-8)
    for k in range(len(hs)):
        h_k, l_k = hs[k], ls[k]
        if d == 1:
            fav_k = (h_k - p_en) / (one_r + 1e-12); sl_t = l_k <= curr_sl
        else:
            fav_k = (p_en - l_k) / (one_r + 1e-12); sl_t = h_k >= curr_sl
        if sl_t:
            return realized_r + rem_w * (d * ((curr_sl - p_en) / (one_r + 1e-12)) - (fm if be_locked else fs))
        ext_p = max(ext_p, h_k) if d == 1 else min(ext_p, l_k)
        if (not be_locked) and fav_k >= be_trig_r:
            be_locked = True; curr_sl = p_en + d * 0.15 * one_r
        if (not tp1_done) and ((h_k >= tp1_p) if d == 1 else (l_k <= tp1_p)):
            realized_r += 0.35 * (1.20 - fm); rem_w -= 0.35; tp1_done = True; be_locked = True; curr_sl = p_en + d * 0.25 * one_r
        if tp1_done and (not tp2_done) and ((h_k >= tp2_p) if d == 1 else (l_k <= tp2_p)):
            realized_r += 0.35 * (2.30 - fm); rem_w -= 0.35; tp2_done = True; curr_sl = p_en + d * 1.25 * one_r
        if tp2_done and ((h_k >= tp3_p) if d == 1 else (l_k <= tp3_p)):
            return realized_r + rem_w * (3.60 - fm)
        if be_locked and fav_k >= 1.35:
            tr = (ext_p - 0.95 * one_r) if d == 1 else (ext_p + 0.95 * one_r)
            curr_sl = max(curr_sl, tr) if d == 1 else min(curr_sl, tr)
    if rem_w > 0:
        realized_r += rem_w * (d * ((cs[-1] - p_en) / (one_r + 1e-12)) - fm)
    return realized_r


def bars1h(coin):
    d = pd.read_csv(ROOT / "data" / "universe_hf" / "5m" / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"], parse_dates=["timestamp"])
    d = d.set_index("timestamp").sort_index()
    b = d.resample("1h", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return b[(b.index >= "2021-01-01") & (b.index < "2026-10-01")]


def rows_for(coin):
    b = bars1h(coin)
    o, h, l, c = (b[k].values.astype(float) for k in ("open", "high", "low", "close"))
    pc = np.r_[o[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values
    natr = np.clip(atr / c, 0.002, 0.15)
    slp = np.clip(1.15 * natr, 0.005, 0.022)
    out = []
    n = len(c)
    for i in range(50, n - H - 1):
        sp = slp[i]; R = c[i] * sp
        for d in (1, -1):
            # A notebook verbatim
            if d == 1:
                pA = max(l[i + 1], c[i] - 0.18 * R) if l[i + 1] <= c[i] else c[i]
            else:
                pA = min(h[i + 1], c[i] + 0.18 * R) if h[i + 1] >= c[i] else c[i]
            rA = path_r(pA, d, R, sp, h[i + 1:i + H + 1], l[i + 1:i + H + 1], c[i + 1:i + H + 1])
            # B realistic limit
            lim = c[i] - d * 0.18 * R
            filled = (l[i + 1] <= lim) if d == 1 else (h[i + 1] >= lim)
            if filled:
                stop_same = (l[i + 1] <= lim - R) if d == 1 else (h[i + 1] >= lim + R)
                rB = (-1.0 - C_SL / (sp + 1e-8)) if stop_same else path_r(lim, d, R, sp, h[i + 2:i + H + 1], l[i + 2:i + H + 1], c[i + 2:i + H + 1])
            else:
                rB = np.nan
            # C taker at next open
            rC = path_r(o[i + 1], d, R, sp, h[i + 1:i + H + 1], l[i + 1:i + H + 1], c[i + 1:i + H + 1]) - (0.00045 - 0.00018) / sp
            out.append((coin, b.index[i], d, sp, rA, rB, rC, filled))
    return pd.DataFrame(out, columns=["coin", "t", "side", "sl_pct", "rA", "rB", "rC", "filledB"])


def mboot_ci(x, months, rng, nb=2000):
    codes, inv = np.unique(months, return_inverse=True)
    s = np.bincount(inv, weights=x); cnt = np.bincount(inv).astype(float)
    W = rng.multinomial(len(codes), np.full(len(codes), 1 / len(codes)), size=nb)
    mb = (W @ s) / np.maximum(W @ cnt, 1)
    return float(np.quantile(mb, .025)), float(np.quantile(mb, .975))


def main():
    proto = OUT / "GEMV_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "GEMV_PROTOCOL_SHA256.txt").read_text().split()[0], "GEMV protocol changed"
    D = pd.concat([rows_for(c) for c in CORE10], ignore_index=True)
    D.to_parquet(OUT / "gemv_rows.parquet", index=False)
    rng = np.random.default_rng(20261023)
    rep = []
    for sd, g in D.groupby("side"):
        for m in ("rA", "rB", "rC"):
            v = g[m].dropna()
            rep.append(dict(side="long" if sd == 1 else "short", model=m[1], n=len(v), fill_rate=float(g.filledB.mean()) if m == "rB" else 1.0,
                            mean_R=float(v.mean()), median_R=float(v.median()), label1_share=float((v > 0.10).mean())))
        f = g[g.filledB]
        diff = (f.rA - f.rB).values
        lo, hi = mboot_ci(diff, pd.to_datetime(f.t).dt.strftime("%Y-%m").values, rng)
        rep.append(dict(side="long" if sd == 1 else "short", model="A-B paired (B-filled bars)", n=len(f), mean_R=float(diff.mean()), ci_lo=lo, ci_hi=hi))
    R = pd.DataFrame(rep); R.to_csv(OUT / "GEMV_summary.csv", index=False)
    Y = D.assign(year=pd.to_datetime(D.t).dt.year).groupby(["year", "side"])[["rA", "rB", "rC"]].mean().reset_index()
    Y.to_csv(OUT / "GEMV_by_year.csv", index=False)
    claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), rows_sha=sha(OUT / "gemv_rows.parquet"), summary_sha=sha(OUT / "GEMV_summary.csv"),
                  n_rows=len(D))
    (OUT / "claims_gemv.json").write_text(json.dumps(claims, indent=1))
    print(R.round(4).to_string(index=False)); print(Y.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
