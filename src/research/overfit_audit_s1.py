"""
S1: Deflated Sharpe Ratio + Probability of Backtest Overfitting over all saved MAIN (2021-26) strategy trials.
Protocol: logs/research_overfit_s1/S1_PROTOCOL_PREREGISTERED.md (SHA256 locked before any S1 number).
"""
import sys
import json
import hashlib
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as ss

SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))
from config import LOGS_DIR

OUT = LOGS_DIR / "research_overfit_s1"
PROTO = "S1_PROTOCOL_PREREGISTERED.md"
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30")
EMC, S_BLOCKS, N_EXTRA = 0.5772156649, 16, 15


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def exp_max_sr(V, N):
    return np.sqrt(V) * ((1 - EMC) * ss.norm.ppf(1 - 1 / N) + EMC * ss.norm.ppf(1 - 1 / (N * np.e)))


def dsr(sr, T, skew, kurt, N, V):
    sr0 = exp_max_sr(V, N)
    return float(sr0), float(ss.norm.cdf((sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr ** 2)))


# the paper's own numerical example must be reproduced before anything else is computed
_sr = 2.5 / np.sqrt(250)
assert abs(dsr(_sr, 1250, -3, 10, 100, 0.5 / 250)[1] - 0.9004) < 5e-5
assert abs(dsr(_sr, 1250, -3, 10, 46, 0.5 / 250)[1] - 0.9505) < 5e-5
assert abs(dsr(_sr, 1250, 0, 3, 88, 0.5 / 250)[1] - 0.9505) < 5e-5


def daily_series(f):
    d = pd.read_csv(f)
    tcol = "date" if "date" in d.columns else "bar"
    d[tcol] = pd.to_datetime(d[tcol])
    s = d.set_index(tcol)["equity"].astype(float)
    if (s.index.hour != 0).any() and s.index.normalize().duplicated().any():     # intraday bars -> last bar of each day
        s = s.groupby(s.index.normalize()).last()
    s.index = s.index.normalize()
    return s[(s.index >= START) & (s.index <= END)]


def collect():
    files = sorted(LOGS_DIR.glob("strategy_1d_step*/*equity*.csv")) + [LOGS_DIR / "strategy_1d_step28_volsize" / "vol_path_MAIN.csv"]
    inv, series = [], {}
    for f in files:
        name = f"{f.parent.name}/{f.stem}"
        why = None
        if "CONTROL" in f.stem:
            why = "control placebo"
        elif "cost040" in f.stem:
            why = "cost-stress duplicate"
        s = daily_series(f) if why is None else None
        if s is not None and (len(s) < 2000 or s.index.min() > START + pd.Timedelta(days=1)):
            why, s = "not a MAIN 2021-26 series", None
        inv.append(dict(trial=name, file=str(f.relative_to(LOGS_DIR.parent)), sha256=sha(f), excluded=why or ""))
        if s is not None:
            series[name] = s
    for f in ("100", "75", "50", "30"):
        p = LOGS_DIR / "strategy_1d_step27_combine" / f"sleeves_MAIN_f{f}.csv"
        d = pd.read_csv(p, parse_dates=["date"]).set_index("date")
        for mix, cols in (("M_AI3", ["D1", "H4", "H1"]), ("M_AI3_BTC", ["D1", "H4", "H1", "BTC"]),
                          ("D1", ["D1"]), ("H4", ["H4"]), ("H1", ["H1"]), ("BTC", ["BTC"])):
            name = f"step27/{mix}_f{f}"
            series[name] = d[cols].mean(axis=1)
            inv.append(dict(trial=name, file=str(p.relative_to(LOGS_DIR.parent)), sha256=sha(p), excluded=""))
    # exact duplicates: keep the first (sorted) copy
    R = pd.DataFrame({k: v for k, v in series.items()}).sort_index()
    R = R[(R.index >= START) & (R.index <= END)].ffill()
    rets = R.pct_change().iloc[1:]
    keep, seen = [], {}
    for c in sorted(rets.columns):
        key = tuple(np.round(rets[c].fillna(0).values, 12))
        if key in seen:
            for row in inv:
                if row["trial"] == c:
                    row["excluded"] = f"duplicate of {seen[key]}"
            continue
        seen[key] = c
        keep.append(c)
    return rets[keep], R, pd.DataFrame(inv)


def sharpe(x, axis=0):
    sd = x.std(axis=axis, ddof=1)
    return np.where(sd > 0, x.mean(axis=axis) / np.where(sd > 0, sd, 1), 0.0)


def pbo(M, S=S_BLOCKS):
    T = (len(M) // S) * S
    X = M[-T:]
    blocks = np.array_split(np.arange(T), S)
    N = X.shape[1]
    lam, loss = [], []
    for c in itertools.combinations(range(S), S // 2):
        tr = np.concatenate([blocks[i] for i in c])
        te = np.concatenate([blocks[i] for i in range(S) if i not in c])
        r_is, r_os = sharpe(X[tr]), sharpe(X[te])
        n_star = int(np.argmax(r_is))
        rank = ss.rankdata(r_os)[n_star]                    # 1 = worst ... N = best
        w = rank / (N + 1)
        lam.append(np.log(w / (1 - w)))
        loss.append(r_os[n_star] < 0)
    lam = np.array(lam)
    return dict(S=S, T_used=int(T), combinations=len(lam), N=int(N), pbo=float(np.mean(lam <= 0)),
                prob_oos_loss=float(np.mean(loss)), lambda_median=float(np.median(lam))), lam


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "S1_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    rets, R, inv = collect()
    inv.to_csv(OUT / "trials_inventory.csv", index=False)
    rets.to_csv(OUT / "trial_daily_returns.csv", index_label="date")
    srs = pd.Series(sharpe(rets.fillna(0).values), index=rets.columns)
    V = float(srs.var(ddof=1))
    N_s = rets.shape[1]
    claims = dict(protocol_sha256=h_, N_series=N_s, N_extra=N_EXTRA, T=len(rets), V_daily_sr=V,
                  sr_daily_mean=float(srs.mean()), sr_daily_max=float(srs.max()), best_trial=srs.idxmax(),
                  returns_sha256=sha(OUT / "trial_daily_returns.csv"))
    srs.mul(np.sqrt(365)).sort_values(ascending=False).rename("sharpe_annual_365").to_csv(OUT / "trial_sharpes.csv")
    for sel in ("step27/M_AI3_f50", "step27/H1_f100"):
        r = rets[sel].values
        sr = float(r.mean() / r.std(ddof=1))
        sk, ku = float(ss.skew(r)), float(ss.kurtosis(r, fisher=False))
        out = dict(sr_daily=sr, sr_annual_365=sr * np.sqrt(365), skew=sk, kurt_raw=ku, T=len(r))
        for tag, N in (("N_series", N_s), ("N_total", N_s + N_EXTRA), ("N_double", 2 * (N_s + N_EXTRA))):
            sr0, d = dsr(sr, len(r), sk, ku, N, V)
            out[tag] = dict(N=N, sr0_daily=sr0, sr0_annual_365=sr0 * np.sqrt(365), dsr=d, significant_95=d >= 0.95)
        claims[f"DSR_{sel.split('/')[1]}"] = out
        print(sel, json.dumps(out), flush=True)
    p, lam = pbo(rets.fillna(0).values)
    np.save(OUT / "pbo_lambdas.npy", lam)
    claims["PBO"] = p
    print("PBO", p, flush=True)
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print(json.dumps({k: v for k, v in claims.items() if not k.startswith("DSR")}, default=str))


if __name__ == "__main__":
    main()
