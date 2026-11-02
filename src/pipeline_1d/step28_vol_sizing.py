"""
Step 28: volatility -> position size for the M_AI3 portfolio.
Protocol: logs/strategy_1d_step28_volsize/STEP28_PROTOCOL_PREREGISTERED.md (SHA256 locked before any result).
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step28_volsize"
PROTO = "STEP28_PROTOCOL_PREREGISTERED.md"
S27 = LOGS_DIR / "strategy_1d_step27_combine"
CAP, COST, SEED, NPERM = 10_000.0, 0.0025, 28, 1000
WIN, BAND, MIN_SIG, BASE_W = 20, 0.10, 60, 0.5
REF_F50 = dict(MAIN=53883.75, PRE=6546.09)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mix_returns(per, cols=("D1", "H4", "H1")):
    s = pd.read_csv(S27 / f"sleeves_{per}_f100.csv", parse_dates=["date"]).set_index("date")
    m = s[list(cols)].mean(axis=1)
    return m.pct_change().iloc[1:], m.index[0]


def target_weights(r, win=WIN):
    """w*_t from data up to t-1 only: sigma over the last `win` returns, k = 0.5 x median of the sigmas known so far."""
    sig = r.rolling(win, min_periods=win).std().shift(1)          # sigma_{t-1}: returns up to t-1
    known = sig.dropna()
    med = known.expanding().median()
    cnt = known.expanding().count()
    k = (BASE_W * med).where(cnt >= MIN_SIG).reindex(sig.index)
    w = (k / sig).clip(0, 1)
    return w.fillna(BASE_W), sig


def run(r, w_target, band=BAND):
    """Equity with the no-trade band and |dw| x cost. Returns equity Series (incl. the start value) and held w."""
    rv, wt = r.values, w_target.values
    E, w_prev, eq, held = CAP, BASE_W, [CAP], []
    for i in range(len(rv)):
        w = wt[i] if abs(wt[i] - w_prev) > band else w_prev
        c = abs(w - w_prev) * COST * E
        E = E * (1 + w * rv[i]) - c
        eq.append(E)
        held.append(w)
        w_prev = w
    return np.array(eq), np.array(held)


def stats(eq, start, end):
    pk = np.maximum.accumulate(eq)
    dd = float(((pk - eq) / pk).max())
    final = float(eq[-1])
    cagr = (final / CAP) ** (365.25 / (end - start).days) - 1
    return dict(final=round(final, 2), cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd * 100, 2),
                calmar=round(cagr / dd, 4) if dd > 0 else None)


def yearly(eq, idx):
    s = pd.Series(eq[1:], index=idx)
    ye = s.groupby(s.index.year).last()
    return {int(y): round(float(v), 2) for y, v in ((ye / ye.shift(1).fillna(CAP) - 1) * 100).items()}


def period(per, rng):
    r, d0 = mix_returns(per)
    start, end = d0, r.index[-1]
    wT, sig = target_weights(r)
    res = {}
    eq_v, held = run(r, wT)
    res["VOL"] = stats(eq_v, start, end) | dict(w_mean=round(float(held.mean()), 4), w_min=round(float(held.min()), 4),
                                                w_max=round(float(held.max()), 4), changes=int((np.diff(np.r_[BASE_W, held]) != 0).sum()),
                                                years=yearly(eq_v, r.index))
    wm = float(held.mean())
    for name, w in (("FIXED_050", BASE_W), ("FIXED_MEAN", wm)):
        e, _ = run(r, pd.Series(w, index=r.index), band=-1)
        res[name] = stats(e, start, end) | dict(w=round(w, 4), years=yearly(e, r.index))
    res["FIXED_050"]["approx_error_vs_step27_f50_pct"] = round((res["FIXED_050"]["final"] / REF_F50[per] - 1) * 100, 3)
    sh_cal, sh_fin = [], []
    for _ in range(NPERM):
        e, _ = run(r, pd.Series(rng.permutation(held), index=r.index))
        s = stats(e, start, end)
        sh_cal.append(s["calmar"] if s["calmar"] is not None else np.nan)
        sh_fin.append(s["final"])
    res["SHUFFLED"] = dict(calmar_p50=round(float(np.nanpercentile(sh_cal, 50)), 4), calmar_p95=round(float(np.nanpercentile(sh_cal, 95)), 4),
                           final_p50=round(float(np.percentile(sh_fin, 50)), 2), final_p95=round(float(np.percentile(sh_fin, 95)), 2),
                           share_vol_calmar_better=round(float(np.mean(np.array(sh_cal) < res["VOL"]["calmar"])), 4),
                           share_vol_final_better=round(float(np.mean(np.array(sh_fin) < res["VOL"]["final"])), 4))
    # report-only variants
    var = {}
    for win in (10, 20, 60):
        for band in (0.0, 0.05, 0.10):
            e, h = run(r, target_weights(r, win)[0], band)
            var[f"win{win}_band{band}"] = stats(e, start, end) | dict(w_mean=round(float(h.mean()), 4))
    rb, _ = mix_returns(per, ("BTC",))
    e, h = run(rb, target_weights(rb)[0])
    eb, _ = run(rb, pd.Series(float(h.mean()), index=rb.index), band=-1)
    var["BTC_VOL"] = stats(e, start, end) | dict(w_mean=round(float(h.mean()), 4))
    var["BTC_FIXED_SAME_MEAN"] = stats(eb, start, end)
    res["report_only"] = var
    pd.DataFrame(dict(date=r.index, ret=r.values, sigma_prev=sig.values, w_target=wT.values, w_held=held, equity=eq_v[1:])).to_csv(
        OUT / f"vol_path_{per}.csv", index=False)
    return res


def main():
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    claims = dict(protocol_sha256=h_, inputs={f: sha(S27 / f) for f in ("sleeves_MAIN_f100.csv", "sleeves_PRE_f100.csv")})
    rng = np.random.default_rng(SEED)
    for per in ("MAIN", "PRE"):
        claims[per] = period(per, rng)
        print(per, json.dumps({k: v for k, v in claims[per].items() if k != "report_only"}, default=str), flush=True)
    M, P = claims["MAIN"], claims["PRE"]
    g = dict(MAIN_G1=M["VOL"]["calmar"] > M["FIXED_MEAN"]["calmar"] and M["VOL"]["calmar"] > M["FIXED_050"]["calmar"],
             MAIN_G2=M["VOL"]["max_dd_pct"] < M["FIXED_MEAN"]["max_dd_pct"],
             MAIN_G3=M["VOL"]["calmar"] > M["SHUFFLED"]["calmar_p95"],
             PRE_G1=P["VOL"]["final"] > P["FIXED_MEAN"]["final"] and P["VOL"]["final"] > P["FIXED_050"]["final"],
             PRE_G2=P["VOL"]["max_dd_pct"] < P["FIXED_MEAN"]["max_dd_pct"],
             PRE_G3=P["VOL"]["final"] > P["SHUFFLED"]["final_p95"])
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = "PASS" if all(g.values()) else "FAIL"
    claims["gates"] = g
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("report-only MAIN", json.dumps(M["report_only"]))
    print("report-only PRE", json.dumps(P["report_only"]))
    print("GATES", json.dumps(g))


if __name__ == "__main__":
    main()
