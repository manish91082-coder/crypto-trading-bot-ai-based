"""BTC-ALLTF-R2 (2026-10-29): tie sensitivity of a confirmed config (found by the independent verifier: on a few coins close == SMA200 to
the last digit, so the F1 trend filter is decided by floating-point rounding, and pandas' rolling mean and a running sum round differently).
Re-runs ONE config on every coin of its job with the F1 filter computed by a cumulative-sum SMA (the other rounding), everything else exactly as
xcoin.py (amendment 1), and reports the portfolio tests next to the stored ones. Output: <RUN>/tests/tie_sensitivity_<job>.csv
Usage: python src/btc_alltf_r2/tie_sensitivity.py --run <RUN> --market spot --tf 15m --family S1 --name "L2|T_DONCH55_20|long_con|X0_SIG|F1_TREND200" """
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402
import xcoin as XC                                                            # noqa: E402
import tests_r2 as TR                                                         # noqa: E402

E, rules, study = XC.E, XC.rules, XC.study


def main():
    ap = argparse.ArgumentParser()
    for k in ("run", "market", "tf", "family", "name"):
        ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    ND, DAY0 = XC.ND, XC.DAY0
    fee = E.fees()[a.market]
    X_ = XC.X
    SR, SEX, DEN, SR2 = np.zeros(ND), np.zeros(ND), np.zeros(ND, np.int64), np.zeros(ND)
    flips = 0
    for coin in XC.coins_for(a.market, a.tf):
        close, qv = K.daily(coin, a.market, XC.LO, XC.HI)
        liq_day = K.liquid_days(qv, X_["liquidity_min_usd"], X_["liquidity_window_days"]) & np.isfinite(close)
        m = np.zeros(ND); m[1:] = close[1:] / close[:-1] - 1; m[~np.isfinite(m)] = 0.0
        Lc, L2c, Xc = np.zeros(ND), np.zeros(ND), np.zeros(ND)
        for (s_lo, s_hi) in XC.refine_segments(XC.segments(a.market, a.tf, coin), close):
            b = K.bars(coin, a.market, a.tf, s_lo, s_hi)
            if len(b) < X_["min_bars"]:
                continue
            ts = b.ts.values.astype(np.int64)
            liq_bar = liq_day[np.clip(ts // K.DAY - DAY0, 0, ND - 1)].astype(np.int8)
            out_, x = rules.compute(b, a.tf)
            g = rules.gates(x)
            rows_ = [f"{r}|{s}" for r in out_ for s in "AB"] + [f"{k}|{s}" for k in g for s in "LS"]
            mm = np.empty((len(rows_), len(b)), np.int8)
            i = 0
            for r in out_:
                mm[i], mm[i + 1] = out_[r]; i += 2
            for k_ in g:
                mm[i], mm[i + 1] = g[k_]; i += 2
            c = {cc["name"]: cc for cc in study.enumerate_configs(a.market, dict(rows=rows_), {r["id"]: r for r in rules.REG})}[a.name]
            study._LAST.clear()
            st = study.state_of(c, mm)
            cl = b.close.values
            cs = np.r_[0.0, np.cumsum(cl)]
            s200 = np.full(len(cl), np.nan)
            s200[199:] = (cs[200:] - cs[:-200]) / 200                        # the other rounding of SMA200
            alt = np.where(np.isfinite(s200), (cl > s200) if c["dir"] > 0 else (cl < s200), False).astype(np.int8)
            flips += int((alt != np.asarray(mm[c["grow"]])).sum())
            gate = (alt & liq_bar).astype(np.int8)
            B = E.Bars(ts, b.open.values, b.high.values, b.low.values, cl, x.atr(14).values)
            T = E.run(B, st, c["dir"], c["exit"], gate=gate)
            n_ = len(T["ei"])
            if not n_:
                continue
            barlen = np.r_[ts[1:], s_hi] - ts
            t_in, t_out = ts[T["ei"]], ts[T["xi"]]
            _, fe, _, net, _, _ = E.pnl(T, c["dir"], fee, None, t_in, t_out)
            add = np.where(np.isin(T["reason"], (3, 5, 7, 9, 11)), barlen[T["xi"]] // 2, np.where(T["reason"] == 10, barlen[T["xi"]] - 1, 0))
            L, Xp, _ = K.mtm(np.zeros(n_, np.int64), t_in, t_out + add, T["px_in"], net, np.full(n_, float(c["dir"])), close, DAY0, 1, ND)
            do = np.minimum((t_out + add) // K.DAY - DAY0, ND - 1)
            Lc += L[0]; Xc += Xp[0]
            L2c += L[0] + np.bincount(do, weights=np.log1p(np.maximum(net - fe, -0.999999)) - np.log1p(np.maximum(net, -0.999999)), minlength=ND)
        if not Lc.any() and not Xc.any():
            continue
        r = np.expm1(Lc)
        den = liq_day | (Xc > 0)
        e = Xc.sum() / max(den.sum(), 1)
        SR += r; SR2 += np.expm1(L2c); SEX += np.where(den, r - e * m, 0.0); DEN += den
    A = np.load(Path(a.run) / "xcoin_v2" / f"{a.market}_{a.tf}_{a.family}" / "acc.npz", allow_pickle=False)
    k = list(A["names"]).index(a.name)
    base = TR.port_stats(A["SR"][k], A["SR2"][k], A["SEX"][k], A["DEN"][k], A["BHS"], A["BHD"], int(A["day0"]))
    altS = TR.port_stats(SR, SR2, SEX, DEN, A["BHS"], A["BHD"], int(A["day0"]))
    D = pd.DataFrame([dict(version="stored (pandas rolling SMA200)", **base), dict(version="alternative rounding (cumsum SMA200)", gate_bars_flipped=flips, **altS)])
    D.to_csv(Path(a.run) / "tests" / f"tie_sensitivity_{a.market}_{a.tf}_{a.family}.csv", index=False)
    print(D[["version", "cagr", "sharpe", "maxdd", "tA", "pA", "tB", "pB", "sub1", "sub2", "sub3", "cagr_2xfee"]].round(4).to_string(index=False))
    print("gate bars flipped by the other rounding:", flips)


if __name__ == "__main__":
    main()
