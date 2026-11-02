"""Methods bench Batch 2 (A3 volatility, A4 volume / order flow) on BTC
(logs/research_methods_bench/BATCH2_PROTOCOL_PREREGISTERED.md, locked before results; bench = master protocol + amendment 1).
Run: python src/research/methods_bench_b2.py lookahead | batch2"""
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.signal import lfilter

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ / "src" / "research"))
import btc_entry_study as B                                    # verified engine
import methods_bench as MB                                     # bench: agg carry, exits, reports, gates

OUT = MB.OUT
PROTO2 = OUT / "BATCH2_PROTOCOL_PREREGISTERED.md"
assert MB.sha(PROTO2) == (OUT / "BATCH2_PROTOCOL_SHA256.txt").read_text().split()[0], "batch 2 protocol changed"
D_END = pd.Timestamp("2024-01-01")
N_PRIOR = 1726                                                 # Batch 1 N_for_dsr (BATCH1_RESULTS.json)
ema, sgn, zs, atr = MB.ema, MB.sgn, MB.zs, MB.atr


# ------------------------------------------------------------------ scale aggregation (bench agg + qv, nt)
def agg2(d, rule):
    a = d.resample(rule, label="right", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
                                                             "taker_buy_base": "sum", "quote_volume": "sum", "trades": "sum"})
    return a.dropna(subset=["open", "high", "low", "close"])


# ------------------------------------------------------------------ GARCH family (protocol §3), fitted on D bars of the scale, standardized eps
def _garch_var(p, e2, neg, kind):
    w, a, b = p[0], p[1], p[2]
    g = p[3] if kind == "GJR" else 0.0
    x = w + (a + g * neg) * e2
    return lfilter([1.0], [1.0, -b], x, zi=[b * 1.0])[0]       # f_t = x_t + b f_{t-1}, f_{-1} = 1 (D variance of standardized eps)


def _egarch_var(p, e):
    w, a, b, g = p
    lf = np.empty(len(e)); prev = 0.0                          # ln f_{-1} = ln 1
    c0 = np.sqrt(2 / np.pi)
    for i in range(len(e)):
        z = e[i] / np.exp(0.5 * prev)
        prev = w + b * prev + a * (abs(z) - c0) + g * z
        lf[i] = prev
    return np.exp(lf)


def _nll(p, e, kind):
    f = _egarch_var(p, e) if kind == "EGARCH" else _garch_var(p, e * e, (e < 0).astype(float), kind)
    s2 = np.r_[1.0, f[:-1]]                                    # variance of e_t = forecast made at t-1
    if not np.all(np.isfinite(s2)) or np.any(s2 <= 0):
        return 1e18
    return 0.5 * float(np.sum(np.log(s2) + e * e / s2))


START = {"GARCH": [0.05, 0.05, 0.90], "GJR": [0.05, 0.03, 0.90, 0.04], "EGARCH": [0.0, 0.10, 0.95, 0.0]}
BOUNDS = {"GARCH": [(1e-8, 10), (0, 1), (0, 0.9999)], "GJR": [(1e-8, 10), (0, 1), (0, 0.9999), (-1, 1)],
          "EGARCH": [(-10, 10), (-5, 5), (-0.999, 0.999), (-5, 5)]}
CONS = {"GARCH": [{"type": "ineq", "fun": lambda p: 0.9999 - p[1] - p[2]}],
        "GJR": [{"type": "ineq", "fun": lambda p: 0.9999 - p[1] - p[2] - p[3] / 2}, {"type": "ineq", "fun": lambda p: p[1] + p[3]}], "EGARCH": []}


def eps_std(a, mu=None, sd=None):
    """eps standardized by the D-period mean / std of r (passed in when fixed, e.g. in the lookahead test)."""
    r = np.log(a.close).diff()
    if mu is None:
        rd = r[(a.index < D_END)].dropna(); mu, sd = float(rd.mean()), float(rd.std())
    return ((r - mu) / sd).fillna(0.0).values, (a.index < D_END), mu, sd


def fit_garch(d):
    par = {}
    for sn, rule in MB.SCALES.items():
        e, md, mu, sd = eps_std(agg2(d, rule))
        for kind in ("GARCH", "GJR", "EGARCH"):
            ed = e[md]                                         # objective = mean NLL (same argmin; total NLL gave gradients ~3e5 and SLSQP stopped at the start, CODE_CHANGES)
            res = minimize(lambda p: _nll(p, ed, kind) / len(ed), START[kind], method="SLSQP", bounds=BOUNDS[kind], constraints=CONS[kind],
                           options=dict(maxiter=1000, ftol=1e-12))
            par[f"{kind}_{sn}"] = dict(params=[float(x) for x in res.x], nll=float(res.fun * len(ed)), success=bool(res.success), nit=int(res.nit),
                                       n_D=int(md.sum()), mu=mu, sd=sd)
    return par


def garch_sigma(a, gp, kind):
    e = eps_std(a, gp["mu"], gp["sd"])[0]
    p = gp["params"]
    f = _egarch_var(p, e) if kind == "EGARCH" else _garch_var(p, e * e, (e < 0).astype(float), kind)
    return pd.Series(np.sqrt(f), index=a.index)


# ------------------------------------------------------------------ Batch 2 rules on one scale frame: {name: (follow array, kind)}
def volume_profile(h, l, c, v, n=100, bins=50):
    out = np.zeros(len(c), dtype=np.int8)
    tp = (h + l + c) / 3
    for t in range(n - 1, len(c)):
        lo, hi = l[t - n + 1:t + 1].min(), h[t - n + 1:t + 1].max()
        if not hi > lo:
            continue
        w = (hi - lo) / bins
        idx = np.clip(np.floor((tp[t - n + 1:t + 1] - lo) / w).astype(int), 0, bins - 1)
        vol = np.bincount(idx, weights=v[t - n + 1:t + 1], minlength=bins)
        poc = int(np.argmax(vol)); a_, b_ = poc, poc; tot = vol[poc]; V = vol.sum()
        while tot < 0.7 * V:
            up = vol[b_ + 1] if b_ < bins - 1 else None
            dn = vol[a_ - 1] if a_ > 0 else None
            if dn is None or (up is not None and up >= dn):
                b_ += 1; tot += up
            else:
                a_ -= 1; tot += dn
        vah, val = lo + (b_ + 1) * w, lo + a_ * w
        out[t] = 1 if c[t] > vah else (-1 if c[t] < val else 0)
    return out


def klinger(a):
    h, l, c, v = a.high.values, a.low.values, a.close.values, a.volume.values
    hlc = h + l + c; dm = h - l
    n = len(c); trend = np.ones(n); cm = np.empty(n); cm[0] = dm[0]
    for i in range(1, n):
        trend[i] = 1.0 if hlc[i] > hlc[i - 1] else -1.0
        cm[i] = cm[i - 1] + dm[i] if trend[i] == trend[i - 1] else dm[i - 1] + dm[i]
    vf = np.where(cm > 0, v * np.abs(2 * dm / np.where(cm > 0, cm, 1.0) - 1) * trend, 0.0)
    vf = pd.Series(vf, index=a.index)
    ko = ema(vf, 34) - ema(vf, 55); sg = ema(ko, 13)
    return np.where(sg.notna(), np.where(ko > sg, 1, -1), 0)


def above_ema(x, n):
    m = ema(x, n)
    return np.where(m.notna(), np.where(x > m, 1, -1), 0)


def batch2_rules(a, gpar, sn):
    c, h, l, o, v, tb, qv, nt = a.close, a.high, a.low, a.open, a.volume, a.taker_buy_base, a.quote_volume, a.trades
    r = np.log(c).diff()
    R = {}
    # ---- §3 regime measures
    at14, tr = atr(a, 14)
    rv20 = r.rolling(20).std()
    lhl, lco = np.log(h / l), np.log(c / o)
    rs = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    k = 0.34 / (1.34 + 21 / 19)
    M = {"A3.01_NATR14": at14 / c, "A3.02a_RV20": rv20,
         "A3.02b_EWMA": np.sqrt((r * r).ewm(alpha=0.06, adjust=False, min_periods=20).mean()),
         "A3.03a_Parkinson20": np.sqrt((lhl ** 2).rolling(20).mean() / (4 * np.log(2))),
         "A3.03b_GarmanKlass20": np.sqrt((0.5 * lhl ** 2 - (2 * np.log(2) - 1) * lco ** 2).rolling(20).mean()),
         "A3.03c_RogersSatchell20": np.sqrt(rs.rolling(20).mean()),
         "A3.03d_YangZhang20": np.sqrt(np.log(o / c.shift(1)).rolling(20).var() + k * lco.rolling(20).var() + (1 - k) * rs.rolling(20).mean())}
    for kind, nm in (("GARCH", "A3.04a_GARCH"), ("GJR", "A3.04b_GJR"), ("EGARCH", "A3.04c_EGARCH")):
        M[nm] = garch_sigma(a, gpar[f"{kind}_{sn}"], kind)
    M["A3.08a_VoV20"] = np.log(rv20).rolling(20).std()
    M["A3.08c_Kurt50"] = r.rolling(50).kurt()
    x = 2 * tb - v
    M["A4.08_VPIN50"] = x.abs().rolling(50).sum() / v.rolling(50).sum()
    M["A4.09a_Kyle50"] = r.rolling(50).cov(x) / x.rolling(50).var()
    M["A4.09b_Amihud20"] = (r.abs() / qv.replace(0, np.nan)).rolling(20).mean()
    dc = c.diff()
    M["A4.09c_Roll50"] = 2 * np.sqrt(np.maximum(0.0, -dc.rolling(50).cov(dc.shift(1)))) / c
    ts20 = sgn((c - c.shift(20)).values)
    for nm, m in M.items():
        q = pd.Series(np.asarray(m, dtype=float), index=a.index).replace([np.inf, -np.inf], np.nan).rolling(500, min_periods=250).rank(pct=True).values
        R[f"{nm}_LOW"] = (np.where(q < 0.2, ts20, 0), "regime")
        R[f"{nm}_HIGH"] = (np.where(q > 0.8, ts20, 0), "regime")
    # ---- §4 directional A3
    co = sgn((c - o).values)
    R["A3.01x_ATRexp"] = (np.where(tr > 2 * at14.shift(1), co, 0), "dir")
    m20, s20 = c.rolling(20).mean(), c.rolling(20).std(ddof=0)
    at20, _ = atr(a, 20)
    insq = (m20 + 2 * s20 < m20 + 1.5 * at20) & (m20 - 2 * s20 > m20 - 1.5 * at20)
    rel = insq.shift(1, fill_value=False) & ~insq
    R["A3.05_Squeeze"] = (np.where(rel, sgn((c - m20).values), 0), "dir")
    rng = h - l
    brk = np.where(c > h.shift(1), 1, np.where(c < l.shift(1), -1, 0))
    for nn in (7, 4):
        nr = (rng == rng.rolling(nn).min()).shift(1, fill_value=False)
        R[f"A3.06{'a' if nn == 7 else 'b'}_NR{nn}"] = (np.where(nr, brk, 0), "dir")
    ib = ((h < h.shift(1)) & (l > l.shift(1))).shift(1, fill_value=False)
    R["A3.06c_InsideBar"] = (np.where(ib, brk, 0), "dir")
    pr = rng.shift(1)
    R["A3.07_WilliamsVB"] = (np.where(c > o + 0.5 * pr, 1, np.where(c < o - 0.5 * pr, -1, 0)), "dir")
    sk = r.rolling(50).skew()
    R["A3.08b_Skew50"] = (np.where(sk > 0.5, 1, np.where(sk < -0.5, -1, 0)), "dir")      # follow; the standard reading is its fade
    bv = (np.pi / 2) * (r.abs() * r.abs().shift(1)).rolling(50).mean().shift(1)
    R["A3.09_Jump"] = (np.where(r.abs() > 4 * np.sqrt(bv), sgn(r.values), 0), "dir")
    # ---- §5 directional A4
    R["A4.01a_OBV"] = (above_ema((np.sign(c.diff()).fillna(0) * v).cumsum(), 20), "dir")
    mfm = (((c - l) - (h - c)) / (h - l)).where(h > l, 0.0)
    adl = (mfm * v).cumsum()
    R["A4.01b_ChaikinOsc"] = (sgn((ema(adl, 3) - ema(adl, 10)).values), "dir")
    cmf = (mfm * v).rolling(20).sum() / v.rolling(20).sum()
    R["A4.01c_CMF20"] = (np.where(cmf > 0.05, 1, np.where(cmf < -0.05, -1, 0)), "dir")
    R["A4.02a_VPT"] = (above_ema((v * c.pct_change()).fillna(0).cumsum(), 20), "dir")
    emv = (((h + l) / 2).diff() * (h - l) / v).replace([np.inf, -np.inf], np.nan)
    R["A4.02b_EMV14"] = (sgn(emv.rolling(14).mean().values), "dir")
    R["A4.02c_Klinger"] = (klinger(a), "dir")
    pc = c.pct_change().fillna(0)
    R["A4.03a_NVI"] = (above_ema(1000 * (1 + pc.where(v < v.shift(1), 0.0)).cumprod(), 255), "dir")
    R["A4.03b_PVI"] = (above_ema(1000 * (1 + pc.where(v > v.shift(1), 0.0)).cumprod(), 255), "dir")
    cvd = x.rolling(20).sum() / v.rolling(20).sum()
    R["A4.04a_CVD"] = (sgn(cvd.values), "dir")
    cz = zs(cvd)
    R["A4.04b_CVDz"] = (np.where(cz > 2, 1, np.where(cz < -2, -1, 0)), "dir")
    R["A4.05_TradesZ"] = (np.where(zs(nt) > 2, co, 0), "dir")
    R["A4.06_RelVol"] = (np.where(v / v.rolling(20).mean().shift(1) > 2, co, 0), "dir")
    R["A4.07_VolProfile"] = (volume_profile(h.values, l.values, c.values, v.values), "dir")
    return {kk: (np.nan_to_num(np.asarray(xx, dtype=float)).astype(np.int8), kd) for kk, (xx, kd) in R.items()}


# ------------------------------------------------------------------ §6 information-driven bars on 5m data
def info_bars(d):
    idx = d.index
    day = idx.normalize()
    out = {}
    v = d.volume.values; qv = d.quote_volume.values; s = (2 * d.taker_buy_base - d.volume).values; c = d.close.values
    dsum = lambda x: pd.Series(x, index=idx).groupby(day).sum(min_count=0)
    for nm, x in (("Volume", v), ("Dollar", qv)):
        ds = dsum(x)
        th = (ds.rolling(30, min_periods=30).mean().shift(1) / 48).reindex(day).values
        cum = 0.0; closes = []; sig = np.zeros(len(c), dtype=np.int8); cur = 0
        for i in range(len(c)):
            xi = x[i]
            if np.isfinite(xi) and np.isfinite(th[i]):
                cum += xi
                if cum >= th[i]:
                    closes.append(c[i]); cum = 0.0
                    cur = int(np.sign(closes[-1] - closes[-21])) if len(closes) > 20 else 0
            sig[i] = cur
        out[f"A4.10_{nm}Bars"] = sig
    hr = pd.Series(s, index=idx).groupby(idx.floor("h")).sum(min_count=0).abs()
    hm = hr.groupby(hr.index.normalize()).sum() / 24                                  # mean |hourly signed volume| per day
    th = (2 * hm.rolling(30, min_periods=30).mean().shift(1)).reindex(day).values
    cum = 0.0; sig = np.zeros(len(c), dtype=np.int8); cur = 0
    for i in range(len(c)):
        if np.isfinite(s[i]) and np.isfinite(th[i]):
            cum += s[i]
            if abs(cum) >= th[i]:
                cur = int(np.sign(cum)); cum = 0.0
        sig[i] = cur
    out["A4.10_ImbalanceBars"] = sig
    return out


def batch2_signals(d, gpar):
    S = {}
    for sn, rule in MB.SCALES.items():
        a = agg2(d, rule)
        for kk, (x, kd) in batch2_rules(a, gpar, sn).items():
            s5 = np.nan_to_num(MB.to5m(pd.Series(x, index=a.index), d)).astype(np.int8)
            S[f"{kk}_follow_{sn}"] = s5; S[f"{kk}_fade_{sn}"] = (-s5).astype(np.int8)
    for kk, x in info_bars(d).items():
        S[f"{kk}_follow"] = x; S[f"{kk}_fade"] = (-x).astype(np.int8)
    return S


# ------------------------------------------------------------------ lookahead test (protocol §10, W8)
def lookahead(d, gpar, S, cuts, log):
    bad = []
    for cut in cuts:
        dt = d.iloc[:cut]
        St = batch2_signals(dt, gpar)
        diff = [k for k in S if not np.array_equal(S[k][:cut - 1], St[k][:cut - 1])]
        log(f"lookahead cut {d.index[cut]}: {len(diff)} configs differ {diff[:5]}")
        bad += diff
    return bad


# ------------------------------------------------------------------ parallel gate phase (protocol §9): same functions, fixed seeds per configuration
_W = {}


def _winit():
    d = B.load()
    _W.update(d=d, P=B.periods(d), cum_f=B.cum_funding(d), ocs={k: B.load_oc(v) for k, v in MB.EXITS.items() if v != "REV"})


def _gate(job):
    cfg, xn, tr, N, sr_var, stress_mean, delay_mean = job
    d, P, cum_f, ocs = _W["d"], _W["P"], _W["cum_f"], _W["ocs"]
    n = len(tr["net"])
    g = dict(cfg=cfg, exit=xn, H_n=n)
    if n >= 2:
        p_long = float((tr["dir"] > 0).mean())
        if xn == "X3":
            ctl = MB.fast_control(n, p_long, P["H"][0], P["H"][1], B.FUT_RT, cum_f, holds=tr["exit"] - tr["t"], d=d)
        else:
            ctl = MB.fast_control(n, p_long, P["H"][0], P["H"][1], B.FUT_RT, cum_f, oc=ocs[xn])
        ci = B.boot_ci(tr["net"], tr["t"], d.index) if n >= 10 else [np.nan, np.nan]
        y26 = d.index[tr["t"]] >= pd.Timestamp("2026-01-01")
        g.update(H_mean=float(tr["net"].mean()), H_ci_lo=ci[0], ctrl_p95=float(np.nanpercentile(ctl, 95)), ctrl_median=float(np.nanmedian(ctl)),
                 m25=float(tr["net"][~y26].mean()) if (~y26).any() else np.nan, m26=float(tr["net"][y26].mean()) if y26.any() else np.nan,
                 dsr=B.dsr(tr["net"], N, sr_var)[0] if np.isfinite(sr_var) and tr["net"].std() > 0 else np.nan)
        g["G1"] = bool(g["H_ci_lo"] > 0); g["G2"] = n >= 100; g["G3"] = bool(g["H_mean"] >= g["ctrl_p95"])
        g["G4"] = bool(g["m25"] > 0 and g["m26"] > 0); g["G5"] = bool(g["dsr"] > 0.95)
        g["G6"] = bool(stress_mean > 0 and delay_mean > 0)
        g["edge"] = all(g[k] for k in ("G1", "G2", "G3", "G4", "G5", "G6"))
    return g


def run_batch_par(name, S, d, P, log, n_prior, workers=3):
    """methods_bench.run_batch with the gate loop in worker processes; every other line identical."""
    cum_f = B.cum_funding(d)
    ocs = {k: B.load_oc(v) for k, v in MB.EXITS.items() if v != "REV"}
    P = dict(P, FULL=(0, len(d) - 1))
    rows, rep = [], []
    keepH = {}
    for cfg, dirn in S.items():
        delayed = np.r_[np.int8(0), dirn[:-1]].astype(np.int8)
        for xn in MB.EXITS:
            for cm, cost, lo in (("fut", B.FUT_RT, False), ("spot", B.SPOT_RT, True)):
                rec = dict(batch=name, cfg=cfg, exit=xn, cost=cm)
                cf = cum_f if cm == "fut" else None
                for pn in ("D", "V", "H", "FULL"):
                    tr = MB.run_one(dirn, xn, ocs, d, cost, cf, P[pn], lo)
                    e, daily = MB.equity_reports(tr, d, *MB.PERIOD_DATES[pn])
                    rec.update({f"{pn}_{k}": v for k, v in MB.metrics(tr, d, e).items()})
                    rep.append(daily.assign(equity=e.values, cfg=cfg, exit=xn, cost=cm, period=pn).reset_index().rename(columns={"index": "date"}))
                    if cm == "fut" and pn == "H":
                        keepH[(cfg, xn)] = tr
                    if cm == "fut" and pn == "FULL" and len(tr["net"]):
                        yy = pd.Series(tr["net"]).groupby(d.index[tr["t"]].year).mean()
                        rec.update({f"Y{y}_mean": float(v) for y, v in yy.items()})
                        rec["pos_years"] = float((yy > 0).mean())
                if cm == "fut":
                    for pn in ("H", "FULL"):
                        ts_ = MB.run_one(dirn, xn, ocs, d, 2 * cost, cf, P[pn], lo)
                        td_ = MB.run_one(delayed, xn, ocs, d, cost, cf, P[pn], lo)
                        rec[f"{pn}_stress_mean"] = float(ts_["net"].mean()) if len(ts_["net"]) else np.nan
                        rec[f"{pn}_delay_mean"] = float(td_["net"].mean()) if len(td_["net"]) else np.nan
                rows.append(rec)
        log(f"{name}: {cfg} done")
    M = pd.DataFrame(rows)
    M.to_csv(OUT / f"{name}_metrics.csv", index=False)
    Dly = pd.concat(rep, ignore_index=True)
    del rep
    Dly.to_parquet(OUT / f"{name}_daily.parquet", index=False)
    key = ["cfg", "exit", "cost", "period"]
    for unit, col in (("monthly", pd.to_datetime(Dly.date).dt.to_period("M").astype(str)), ("yearly", pd.to_datetime(Dly.date).dt.year)):
        T = Dly.assign(unit=col).groupby(key + ["unit"]).agg(n=("n", "sum"), net_sum=("net_sum", "sum"), equity_end=("equity", "last")).reset_index()
        T["ret"] = T.groupby(key).equity_end.transform(lambda s: s / s.shift(1).fillna(10_000.0) - 1)
        T.to_csv(OUT / f"{name}_{unit}.csv", index=False)
    log(f"{name}: reports written ({len(Dly)} daily rows)")
    del Dly
    F = M[M.cost == "fut"].copy()
    N = n_prior + len(F)
    sr_d = (F.D_mean / (F.D_se * np.sqrt(F.D_n))).replace([np.inf, -np.inf], np.nan)
    sr_var = float(sr_d.dropna().var())
    jobs = [(r.cfg, r.exit, keepH[(r.cfg, r.exit)], N, sr_var, r.H_stress_mean, r.H_delay_mean) for r in F.itertuples()]
    out = [None] * len(jobs)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_winit) as ex:
        fut = {ex.submit(_gate, j): i for i, j in enumerate(jobs)}
        for done, f in enumerate(as_completed(fut), 1):
            out[fut[f]] = f.result()
            if done % 25 == 0 or done == len(jobs):
                log(f"{name} gates: {done}/{len(jobs)} in {time.time() - t0:.0f} s")
    G = pd.DataFrame(out)
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
    stage = sys.argv[1] if len(sys.argv) > 1 else "batch2"
    logf = open(OUT / "run_log_batch2.txt", "a", encoding="utf-8")

    def log(m):
        s = f"[{pd.Timestamp.now('UTC'):%Y-%m-%d %H:%M:%S}] {m}"; print(s, flush=True); logf.write(s + "\n"); logf.flush()
    log(f"stage {stage}; code {MB.sha(__file__)[:12]}; protocol {MB.sha(PROTO2)[:12]}")
    d = B.load(); P = B.periods(d)
    gp = OUT / "batch2_garch_params.json"
    if not gp.exists():
        t0 = time.time()
        gpar = fit_garch(d)
        gp.write_text(json.dumps(gpar, indent=1), encoding="utf-8")
        log(f"garch fitted on D in {time.time() - t0:.0f} s: {json.dumps(gpar)}")
    gpar = json.loads(gp.read_text(encoding="utf-8"))
    t0 = time.time()
    S = batch2_signals(d, gpar)
    log(f"batch2 signals: {len(S)} configs in {time.time() - t0:.0f} s")
    if stage == "lookahead":
        rng = np.random.default_rng(20261027)
        lo_, hi_ = int(d.index.searchsorted(pd.Timestamp("2021-01-01"))), len(d) - 1
        cuts = sorted(int(x) for x in rng.integers(lo_, hi_, 20))
        bad = lookahead(d, gpar, S, cuts, log)
        nz = {k: int((v != 0).sum()) for k, v in S.items()}
        (OUT / "batch2_signal_counts.json").write_text(json.dumps(nz, indent=0), encoding="utf-8")
        log(f"lookahead: {len(set(bad))} configs with any difference over 20 cutoffs; zero-signal configs {[k for k, v in nz.items() if v == 0]}")
        return
    if stage == "batch2":
        pd.DataFrame([(str(B.PX.relative_to(PROJ)).replace("\\", "/"), MB.sha(B.PX)), (str(B.FUND.relative_to(PROJ)).replace("\\", "/"), MB.sha(B.FUND)),
                      ("deploy/fees.json", MB.sha(PROJ / "deploy" / "fees.json")),
                      ("logs/research_btc_entry/cache/out_V2.npz", MB.sha(B.CACHE / "out_V2.npz")),
                      ("logs/research_btc_entry/cache/out_A1_1.npz", MB.sha(B.CACHE / "out_A1_1.npz")),
                      ("logs/research_methods_bench/batch2_garch_params.json", MB.sha(gp))], columns=["path", "sha256"]).to_csv(OUT / "batch2_input_manifest.csv", index=False)
        F, G, N, sr_var = run_batch_par("batch2", S, d, P, log, N_PRIOR)
        res = dict(protocol_sha256=MB.sha(PROTO2), code_sha256=MB.sha(__file__), bench_code_sha256=MB.sha(MB.__file__),
                   manifest_sha256=MB.sha(OUT / "batch2_input_manifest.csv"), n_signal_configs=len(S), n_primary=len(F), N_for_dsr=N, sr_var=sr_var,
                   n_edges=int(G.edge.fillna(False).sum()), edges=G[G.edge.fillna(False)].to_dict("records"),
                   top20=F.head(20)[["rank", "cfg", "exit", "H_n", "H_mean", "H_ci_lo", "H_pos_months", "H_maxdd", "H_pf", "consistency",
                                     "H_stress_mean", "H_delay_mean", "pos_years", "edge"]].to_dict("records"))
        f = OUT / "BATCH2_RESULTS.json"
        f.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        (OUT / "BATCH2_RESULTS_SHA256.txt").write_text(MB.sha(f) + "  BATCH2_RESULTS.json\n")
        log(f"batch2 done: {len(F)} primary configs; edges {res['n_edges']}")


if __name__ == "__main__":
    main()
