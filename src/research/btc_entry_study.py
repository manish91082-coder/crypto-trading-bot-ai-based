"""BTC direction -> entry -> exit study (logs/research_btc_entry/BTC_ENTRY_PROTOCOL_PREREGISTERED.md, locked before results).
Run: python src/research/btc_entry_study.py [stage]   stages: outcomes, signals, select, ai, holdout, all (default)"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
OUT = PROJ / "logs" / "research_btc_entry"
CACHE = OUT / "cache"
PX = PROJ / "data" / "universe_hf" / "5m" / "BTCUSDT_5m_full.csv.gz"
FUND = PROJ / "data" / "futures_um" / "BTCUSDT_funding.csv"
FEES = json.loads((PROJ / "deploy" / "fees.json").read_text())["rules"]
SPOT_RT = 2 * FEES["paper_spot_per_side"]
FUT_RT = 2 * FEES["paper_futures_taker_per_side"]
FEE_F = json.loads((PROJ / "deploy" / "fees.json").read_text())
MAKER_RT = 2 * (FEE_F["futures_usdm"]["bnb_maker"] + FEE_F["impact_per_side"])
CAP = 2016
D_END, V_END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")
ABS_SETS = [(0.005, 0.005), (0.01, 0.01), (0.02, 0.02), (0.04, 0.04), (0.01, 0.005), (0.02, 0.01), (0.04, 0.02), (0.005, 0.01), (0.01, 0.02)]
VOL_K = [1, 2, 3]
SETS = [f"A{a * 100:g}_{b * 100:g}" for a, b in ABS_SETS] + [f"V{k}" for k in VOL_K]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


assert sha(OUT / "BTC_ENTRY_PROTOCOL_PREREGISTERED.md") == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"


# ------------------------------------------------------------------ data
def load():
    d = pd.read_csv(PX, parse_dates=["timestamp"]).drop_duplicates("timestamp").set_index("timestamp").sort_index()
    g = pd.date_range("2020-01-01", "2026-09-30 23:55", freq="5min")
    d = d.reindex(g)
    return d


def sigma24(d):
    lr = np.log(d.close).diff()
    return (lr.rolling(288, min_periods=240).std() * np.sqrt(288)).values


# ------------------------------------------------------------------ barrier outcomes
def outcomes(d, a_arr, b_arr, chunk=800):
    """For every decision bar t (entry at the open of t+1): long and short first-touch outcome within CAP bars.
    Returns dict with ret_long, ret_short (gross, direction-signed), exit_long, exit_short (bar index of the exit bar), why codes
    (1 TP, -1 SL, 0 time). Invalid (no entry price / barrier) -> nan."""
    O, H, L, C = (d[c].values.astype("float64") for c in ("open", "high", "low", "close"))
    N = len(O)
    Cff = pd.Series(C).ffill().values
    res = {k: np.full(N, np.nan) for k in ("ret_long", "ret_short", "exit_long", "exit_short", "why_long", "why_short")}
    for s0 in range(0, N - 1, chunk):
        s1 = min(N - 1, s0 + chunk)
        t = np.arange(s0, s1)
        e = O[t + 1]
        a, b = a_arr[t], b_arr[t]
        ok = np.isfinite(e) & np.isfinite(a) & np.isfinite(b)
        idx = (t + 1)[:, None] + np.arange(CAP)[None, :]
        valid_col = idx < N
        idx = np.minimum(idx, N - 1)
        o, h, l_ = O[idx] / e[:, None], H[idx] / e[:, None], L[idx] / e[:, None]
        o[:, 0] = 1.0                                                       # the entry bar opens at the entry price
        for side in ("long", "short"):
            if side == "long":
                tp_lvl, sl_lvl = 1 + a[:, None], 1 - b[:, None]
                g_sl, g_tp = o <= sl_lvl, o >= tp_lvl
                i_sl, i_tp = l_ <= sl_lvl, h >= tp_lvl
            else:
                tp_lvl, sl_lvl = 1 - a[:, None], 1 + b[:, None]
                g_sl, g_tp = o >= sl_lvl, o <= tp_lvl
                i_sl, i_tp = h >= sl_lvl, l_ <= tp_lvl
            g_sl &= valid_col; g_tp &= valid_col; i_sl &= valid_col; i_tp &= valid_col
            ev = g_sl | g_tp | i_sl | i_tp
            has = ev.any(1)
            j = np.where(has, ev.argmax(1), CAP - 1)
            r = np.arange(len(t))
            sgn = 1.0 if side == "long" else -1.0
            # priority inside the event bar: gap SL, gap TP, intrabar SL (conservative), intrabar TP
            px_gap = o[r, j]
            ret = np.where(g_sl[r, j], sgn * (px_gap - 1), np.where(g_tp[r, j], sgn * (px_gap - 1),
                           np.where(i_sl[r, j], -b, np.where(i_tp[r, j], a, np.nan))))
            why = np.where(g_sl[r, j] | i_sl[r, j], -1, np.where(g_tp[r, j] | i_tp[r, j], 1, 0))
            last = np.minimum(t + CAP, N - 1)
            ret_time = sgn * (Cff[last] / e - 1)
            ret = np.where(has, ret, ret_time)
            why = np.where(has, why, 0)
            ex = np.where(has, idx[r, j], last)
            res[f"ret_{side}"][t] = np.where(ok, ret, np.nan)
            res[f"exit_{side}"][t] = np.where(ok, ex, np.nan)
            res[f"why_{side}"][t] = np.where(ok, why, np.nan)
    return res


def stage_outcomes(d):
    CACHE.mkdir(parents=True, exist_ok=True)
    s24 = sigma24(d)
    N = len(d)
    for name, (a, b) in zip(SETS, ABS_SETS + [(None, None)] * 3):
        f = CACHE / f"out_{name}.npz"
        if f.exists():
            continue
        if name.startswith("A"):
            aa, bb = np.full(N, a), np.full(N, b)
        else:
            k = int(name[1:]); aa = bb = k * s24
        t0 = time.time()
        r = outcomes(d, aa, bb)
        np.savez_compressed(f, a=aa, b=bb, **r)
        print("outcomes", name, round(time.time() - t0), "s", flush=True)


# ------------------------------------------------------------------ features and signals
def rsi(close, n=14):
    dl = close.diff()
    up, dn = dl.clip(lower=0), (-dl).clip(lower=0)
    au = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + au / ad)


def features(d):
    c, v, tb = d.close, d.volume, d.taker_buy_base
    F = {}
    W90 = 90 * 288
    for nm, L in (("1h", 12), ("4h", 48), ("24h", 288), ("72h", 864), ("7d", 2016)):
        r = c / c.shift(L) - 1
        F[f"r_{nm}"] = r
        F[f"sd_{nm}"] = r.rolling(W90, min_periods=W90 // 2).std()
    for N in (12, 48, 288, 2016):
        F[f"hi_{N}"] = d.high.shift(1).rolling(N, min_periods=N).max()
        F[f"lo_{N}"] = d.low.shift(1).rolling(N, min_periods=N).min()
    for N in (48, 288, 2016):
        F[f"z_{N}"] = (c - c.rolling(N, min_periods=N).mean()) / c.rolling(N, min_periods=N).std()
    F["rsi_5m"] = rsi(c)
    for nm, rule in (("1h", "1h"), ("4h", "4h")):
        cr = c.resample(rule, label="right", closed="left").last()                  # bucket [T-1h, T) of open times: complete at T
        F[f"rsi_{nm}"] = rsi(cr).reindex(c.index + pd.Timedelta(minutes=5), method="ffill").set_axis(c.index)  # known at bar close
    s24 = pd.Series(sigma24(d), index=d.index)
    F["s24"] = s24
    F["s24_pct"] = s24.rolling(W90, min_periods=W90 // 2).rank(pct=True)
    for nm, W in (("1h", 12), ("4h", 48), ("24h", 288)):
        tbr = tb.rolling(W, min_periods=W).sum() / v.rolling(W, min_periods=W).sum()
        F[f"tbr_{nm}"] = tbr
        F[f"tbrz_{nm}"] = (tbr - tbr.rolling(W90, min_periods=W90 // 2).mean()) / tbr.rolling(W90, min_periods=W90 // 2).std()
    v1h = v.rolling(12, min_periods=12).sum()
    F["vshock"] = v1h / v1h.rolling(7 * 288, min_periods=7 * 200).mean()
    fu = pd.read_csv(FUND, parse_dates=["time"]).set_index("time").funding_rate.astype(float).sort_index()
    fu = fu[~fu.index.duplicated()]
    fr = fu.reindex(d.index + pd.Timedelta(minutes=5), method="ffill").set_axis(d.index)          # latest settled by bar close
    F["fund"] = fr
    F["fund_pct"] = fr.rolling(W90, min_periods=W90 // 2).rank(pct=True)
    F["hour"] = pd.Series(d.index.hour, index=d.index)
    F["dow"] = pd.Series(d.index.dayofweek, index=d.index)
    return pd.DataFrame(F)


def signals(F, d):
    """{config name: int8 array of direction (+1 long, -1 short, 0 none)} decided at the close of each bar."""
    S = {}
    n = len(F)
    rng = np.random.default_rng(2026)
    S["F0_random"] = rng.choice(np.array([-1, 1], dtype=np.int8), size=n)
    S["F1_long"] = np.ones(n, np.int8); S["F1_short"] = -np.ones(n, np.int8)
    for nm in ("1h", "4h", "24h", "72h", "7d"):
        r, sd = F[f"r_{nm}"].values, F[f"sd_{nm}"].values
        for k in (0, 1, 2):
            m = np.abs(r) > k * sd
            dirn = np.where(m & np.isfinite(r) & np.isfinite(sd), np.sign(r), 0).astype(np.int8)
            S[f"F2_mom_{nm}_k{k}"] = dirn
            S[f"F3_rev_{nm}_k{k}"] = (-dirn).astype(np.int8)
    c = d.close.values
    for N in (12, 48, 288, 2016):
        up, dn = c > F[f"hi_{N}"].values, c < F[f"lo_{N}"].values
        dirn = np.where(up, 1, np.where(dn, -1, 0)).astype(np.int8)
        S[f"F4_brk_follow_{N}"] = dirn; S[f"F4_brk_fade_{N}"] = (-dirn).astype(np.int8)
    for N in (48, 288, 2016):
        z = F[f"z_{N}"].values
        for k in (2, 3):
            dirn = np.where(z <= -k, 1, np.where(z >= k, -1, 0)).astype(np.int8)
            S[f"F5_z_fade_{N}_k{k}"] = dirn; S[f"F5_z_follow_{N}_k{k}"] = (-dirn).astype(np.int8)
    for nm in ("5m", "1h", "4h"):
        x = F[f"rsi_{nm}"].values
        for lo, hi in ((30, 70), (20, 80)):
            dirn = np.where(x < lo, 1, np.where(x > hi, -1, 0)).astype(np.int8)
            S[f"F6_rsi_fade_{nm}_{lo}"] = dirn; S[f"F6_rsi_follow_{nm}_{lo}"] = (-dirn).astype(np.int8)
    sq = F["s24_pct"].values <= 0.10
    S["F7_squeeze"] = np.where(sq & np.isfinite(F["r_4h"].values), np.sign(F["r_4h"].values), 0).astype(np.int8)
    for nm in ("1h", "4h", "24h"):
        z = F[f"tbrz_{nm}"].values
        for k in (1.5, 2.5):
            dirn = np.where(z >= k, 1, np.where(z <= -k, -1, 0)).astype(np.int8)
            S[f"F8_flow_follow_{nm}_k{k}"] = dirn; S[f"F8_flow_fade_{nm}_k{k}"] = (-dirn).astype(np.int8)
    vs = F["vshock"].values >= 3
    dirn = np.where(vs & np.isfinite(F["r_1h"].values), np.sign(F["r_1h"].values), 0).astype(np.int8)
    S["F9_vshock_follow"] = dirn; S["F9_vshock_fade"] = (-dirn).astype(np.int8)
    fp = F["fund_pct"].values
    dirn = np.where(fp > 0.9, -1, np.where(fp < 0.1, 1, 0)).astype(np.int8)
    S["F11_fund_fade"] = dirn; S["F11_fund_follow"] = (-dirn).astype(np.int8)
    return S


# ------------------------------------------------------------------ trade simulation
def simulate(dirn, oc, cost, cum_f, idx_range, longs_only=False):
    """Greedy non-overlapping trades over decision bars in idx_range [i0, i1). Returns arrays (entry_bar, dir, net, gross, why, exit_bar)."""
    i0, i1 = idx_range
    cand = np.flatnonzero(dirn[i0:i1] != 0) + i0
    if longs_only:
        cand = cand[dirn[cand] > 0]
    rl, rs, xl, xs, wl, ws = oc["ret_long"], oc["ret_short"], oc["exit_long"], oc["exit_short"], oc["why_long"], oc["why_short"]
    out_t, out_d, out_g, out_x, out_w = [], [], [], [], []
    free = i0
    for t in cand:
        if t < free:
            continue
        dd = int(dirn[t])
        g, x, w = (rl[t], xl[t], wl[t]) if dd > 0 else (rs[t], xs[t], ws[t])
        if not np.isfinite(g):                                          # no valid outcome
            continue
        out_t.append(t); out_d.append(dd); out_g.append(g); out_x.append(int(x)); out_w.append(w)
        free = int(x)                                                 # next decision at the close of the exit bar
    t = np.array(out_t, dtype=np.int64); dr = np.array(out_d, dtype=np.int8); g = np.array(out_g); x = np.array(out_x, dtype=np.int64)
    fund = (cum_f[x] - cum_f[t]) * dr if cum_f is not None and len(t) else np.zeros(len(t))   # events in (close of t, close of x]; long pays positive funding
    net = g - cost - fund
    return dict(t=t, dir=dr, gross=g, net=net, exit=x, why=np.array(out_w))


def week_stats(net, t_idx, index):
    n = len(net)
    if n == 0:
        return dict(n=0)
    wk = pd.Series(index[t_idx]).dt.to_period("W").values
    m = float(net.mean())
    dev = pd.Series(net - m).groupby(wk).sum().values
    se = float(np.sqrt((dev ** 2).sum()) / n) if n > 1 else np.nan
    return dict(n=n, mean=m, se=se, t=m / se if se and se > 0 else np.nan, win=float((net > 0).mean()), sum=float(net.sum()))


def boot_ci(net, t_idx, index, B=2000, seed=7):
    wk = pd.Series(index[t_idx]).dt.to_period("W").values
    df = pd.DataFrame(dict(w=wk, x=net))
    g = df.groupby("w").x
    sums, cnts = g.sum().values, g.count().values
    rng = np.random.default_rng(seed)
    k = len(sums)
    bs = []
    for _ in range(B):
        j = rng.integers(0, k, k)
        bs.append(sums[j].sum() / cnts[j].sum())
    return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def cum_funding(d):
    fu = pd.read_csv(FUND, parse_dates=["time"]).set_index("time").funding_rate.astype(float).sort_index()
    fu = fu[~fu.index.duplicated()]
    close_t = d.index + pd.Timedelta(minutes=5)
    cs = np.r_[0.0, np.cumsum(fu.values)]
    return cs[np.searchsorted(fu.index.values, close_t.values, side="left")]   # events with time < bar close


def periods(d):
    i_d = int(d.index.searchsorted(D_END)); i_v = int(d.index.searchsorted(V_END))
    return dict(D=(0, i_d), V=(i_d, i_v), H=(i_v, len(d) - 1))


def load_oc(name):
    z = np.load(CACHE / f"out_{name}.npz")
    return {k: z[k] for k in z.files}


def pstar(oc, cost):
    a, b = oc["a"], oc["b"]
    return float(np.nanmedian((b + cost) / (a + b)))


# ------------------------------------------------------------------ calendar family (time exit, not barriers)
def calendar(d, P):
    O, C = d.open.values, d.close.values
    hstart = np.flatnonzero((d.index.minute == 55))                   # decision bar :55 -> entry at the next hour's open
    hstart = hstart[hstart + 12 < len(d)]
    e, x = O[hstart + 1], C[hstart + 12]
    r = x / e - 1
    key = (d.index[hstart + 1].dayofweek * 24 + d.index[hstart + 1].hour).values
    ok = np.isfinite(r)
    per = np.where(hstart < P["D"][1], "D", np.where(hstart < P["V"][1], "V", "H"))
    Dm = pd.Series(r[ok & (per == "D")]).groupby(key[ok & (per == "D")]).mean()
    sign = np.sign(Dm.reindex(range(168)).fillna(0).values)
    rows, single = {}, []
    for pname in ("D", "V", "H"):
        m = ok & (per == pname)
        dirn = sign[key[m]]
        net = dirn * r[m] - FUT_RT
        traded = dirn != 0
        rows[pname] = week_stats(net[traded], hstart[m][traded], d.index)
    for b in range(168):
        out = {}
        for pname in ("D", "V", "H"):
            m = ok & (per == pname) & (key == b)
            net = sign[b] * r[m] - FUT_RT
            out[pname] = week_stats(net, hstart[m], d.index) if sign[b] != 0 else dict(n=0)
        single.append(dict(bucket=int(b), dow=int(b // 24), hour=int(b % 24), sign=int(sign[b]), **{f"{k}_{s}": v.get(s) for k, v in out.items() for s in ("n", "mean", "t")}))
    S = pd.DataFrame(single)
    sunday = {p: week_stats(np.concatenate([sign[b] * r[ok & (per == p) & (key == b)] - FUT_RT for b in range(144, 168) if sign[b] != 0]),
                            np.concatenate([hstart[ok & (per == p) & (key == b)] for b in range(144, 168) if sign[b] != 0]), d.index) for p in ("D", "V", "H")}
    sun_raw = {p: dict(mean_1h_return=float(np.nanmean(r[ok & (per == p) & (key >= 144)])), all_days=float(np.nanmean(r[ok & (per == p)]))) for p in ("D", "V", "H")}
    return dict(all_buckets=rows, sunday_traded=sunday, sunday_raw=sun_raw), S


# ------------------------------------------------------------------ AI family
def ai_features(F, d):
    X = pd.DataFrame(index=F.index)
    for c in F.columns:
        if c.startswith(("hi_", "lo_")):
            X[f"dist_{c}"] = d.close / F[c] - 1
        elif c not in ("fund",):
            X[c] = F[c]
    X["fund"] = F["fund"]
    return X.astype("float32")


def stage_ai(F, d, P, log):
    from sklearn.ensemble import HistGradientBoostingClassifier
    X = ai_features(F, d)
    dec = np.arange(0, len(d) - 1, 6)
    months = pd.period_range("2021-01", "2026-09", freq="M")
    out = {}
    for setn in ("A1_1", "V2"):
        oc = load_oc(setn)
        pl, ps = np.full(len(d), np.nan), np.full(len(d), np.nan)
        yl = (oc["why_long"][dec] == 1).astype(int); ys = (oc["why_short"][dec] == 1).astype(int)
        known = oc["exit_long"][dec]; known_s = oc["exit_short"][dec]
        Xd = X.values[dec]
        okr = np.isfinite(oc["ret_long"][dec]) & np.isfinite(oc["ret_short"][dec])
        for mth in months:
            m0 = int(d.index.searchsorted(mth.start_time)); m1 = int(d.index.searchsorted((mth + 1).start_time))
            tr = okr & (dec < m0) & (known < m0) & (known_s < m0)
            te = (dec >= m0) & (dec < m1)
            if tr.sum() < 5000 or te.sum() == 0:
                continue
            for y, dst in ((yl, pl), (ys, ps)):
                mdl = HistGradientBoostingClassifier(max_depth=3, max_iter=300, learning_rate=0.05, min_samples_leaf=200, random_state=0)
                mdl.fit(Xd[tr], y[tr])
                dst[dec[te]] = mdl.predict_proba(Xd[te])[:, 1]
        a, b = oc["a"], oc["b"]
        out[setn] = (pl, ps, a, b)
        np.savez_compressed(CACHE / f"ai_{setn}.npz", pl=pl, ps=ps)
        log(f"ai {setn} done")
    return out


def ai_signals(ai, cost):
    S = {}
    for setn, (pl, ps, a, b) in ai.items():
        ps_ = (b + cost) / (a + b)
        for mm in (0.0, 0.02, 0.05):
            el, es = pl - ps_ - mm, ps - ps_ - mm
            dirn = np.where((el >= 0) & ((el >= es) | ~np.isfinite(es)), 1, np.where(es >= 0, -1, 0))
            dirn = np.where(np.isfinite(pl) & np.isfinite(ps), dirn, 0).astype(np.int8)
            S[f"F12_ai_{setn}_m{mm}"] = (setn, dirn)
    return S


# ------------------------------------------------------------------ random control, DSR
def random_control(oc, n, p_long, i0, i1, cost, cum_f, seeds=200):
    import bisect
    means = []
    for sd in range(seeds):
        rng = np.random.default_rng(sd)
        order = rng.permutation(np.arange(i0, i1))
        starts, ends, nets = [], [], []
        for t in order:
            if len(nets) >= n:
                break
            dd = 1 if rng.random() < p_long else -1
            g, x = (oc["ret_long"][t], oc["exit_long"][t]) if dd > 0 else (oc["ret_short"][t], oc["exit_short"][t])
            if not np.isfinite(g):
                continue
            x = int(x)
            k = bisect.bisect_left(starts, t)
            if (k > 0 and ends[k - 1] > t) or (k < len(starts) and starts[k] < x):
                continue
            starts.insert(k, t); ends.insert(k, x)
            f = (cum_f[x] - cum_f[t]) * dd if cum_f is not None else 0.0
            nets.append(g - cost - f)
        means.append(float(np.mean(nets)) if nets else np.nan)
    return np.array(means)


def dsr(net, n_trials, sr_var):
    from scipy.stats import norm, skew, kurtosis
    sr = net.mean() / net.std(ddof=1)
    g3, g4 = skew(net), kurtosis(net, fisher=False)
    em = 0.5772156649
    sr0 = np.sqrt(sr_var) * ((1 - em) * norm.ppf(1 - 1 / n_trials) + em * norm.ppf(1 - 1 / (n_trials * np.e)))
    z = (sr - sr0) * np.sqrt(len(net) - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return float(norm.cdf(z)), float(sr), float(sr0)


# ------------------------------------------------------------------ main
def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(parents=True, exist_ok=True); CACHE.mkdir(parents=True, exist_ok=True)
    logf = open(OUT / "run_log.txt", "a", encoding="utf-8")

    def log(m):
        s = f"[{pd.Timestamp.now('UTC'):%Y-%m-%d %H:%M:%S}] {m}"; print(s, flush=True); logf.write(s + "\n"); logf.flush()
    d = load()
    P = periods(d)
    pd.DataFrame([(str(PX.relative_to(PROJ)).replace("\\", "/"), sha(PX)), (str(FUND.relative_to(PROJ)).replace("\\", "/"), sha(FUND)),
                  ("deploy/fees.json", sha(PROJ / "deploy" / "fees.json"))], columns=["path", "sha256"]).to_csv(OUT / "input_manifest.csv", index=False)
    log(f"start stage {stage}; bars {len(d)}; periods {P}; costs fut {FUT_RT} spot {SPOT_RT} maker {MAKER_RT}")
    if stage in ("outcomes", "all"):
        stage_outcomes(d)
    F = features(d)
    cum_f = cum_funding(d)
    S = signals(F, d)
    if stage in ("ai", "all"):
        ai = stage_ai(F, d, P, log)
    else:
        ai = {s: tuple(np.load(CACHE / f"ai_{s}.npz")[k] for k in ("pl", "ps")) + (load_oc(s)["a"], load_oc(s)["b"]) for s in ("A1_1", "V2")}
    if stage not in ("select", "all", "ai"):
        return
    # ---- break-even table
    ocs = {s: load_oc(s) for s in SETS}
    be = {s: dict(fut=pstar(ocs[s], FUT_RT), spot=pstar(ocs[s], SPOT_RT), maker=pstar(ocs[s], MAKER_RT)) for s in SETS}
    # ---- evaluate every config on D and V
    rows = []
    AI_S = ai_signals(ai, FUT_RT)
    for cfg, dirn in list(S.items()) + [(k, v) for k, v in AI_S.items()]:
        if isinstance(dirn, tuple):
            sets_, dirn = [dirn[0]], dirn[1]
        else:
            sets_ = SETS
        for s in sets_:
            oc = ocs[s]
            for cm, cost, lo in (("fut", FUT_RT, False), ("spot", SPOT_RT, True)):
                rec = dict(cfg=cfg, family=cfg.split("_")[0], set=s, cost=cm)
                for pn in ("D", "V"):
                    i0 = int(d.index.searchsorted(pd.Timestamp("2021-02-01"))) if cfg.startswith("F12") and pn == "D" else P[pn][0]
                    tr = simulate(dirn, oc, cost, cum_f if cm == "fut" else None, (i0, P[pn][1]), longs_only=lo)
                    st = week_stats(tr["net"], tr["t"], d.index)
                    rec.update({f"{pn}_{k}": v for k, v in st.items()})
                    if pn == "D" and st.get("n", 0) > 1:
                        rec["D_sr"] = float(tr["net"].mean() / tr["net"].std(ddof=1)) if tr["net"].std(ddof=1) > 0 else np.nan
                        rec["D_tp_rate"] = float((tr["why"] == 1).mean())
                rows.append(rec)
        log(f"evaluated {cfg}")
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "all_configs_D_V.csv", index=False)
    cal, calS = calendar(d, P)
    calS.to_csv(OUT / "calendar_buckets.csv", index=False)
    # ---- selection (primary cost = fut)
    Rf = R[R.cost == "fut"].copy()
    N_trials = int(len(Rf)) + 168 + 1
    sel = Rf[(Rf.D_n >= 200) & (Rf.D_mean > 0)].sort_values("D_t", ascending=False)
    top = sel.groupby("family").head(3)
    cal_top = calS[(calS.sign != 0) & (calS.D_n >= 200) & (calS.D_mean > 0)].sort_values("D_t", ascending=False).head(3)
    v_ok = top[(top.V_n >= 50) & (top.V_mean > 0)]
    cal_v = cal_top[(cal_top.V_n >= 50) & (cal_top.V_mean > 0)]
    finals = v_ok.sort_values("D_t", ascending=False).head(10)
    sr_var = float(Rf.D_sr.dropna().var())
    log(f"selection: {len(Rf)} fut configs on D, {len(sel)} positive with n>=200, top3/family {len(top)}, V-pass {len(v_ok)}, finals {len(finals)}; "
        f"calendar top {len(cal_top)} V-pass {len(cal_v)}")
    # ---- holdout (opened once, finals only)
    H = []
    i0, i1 = P["H"]
    for _, f in finals.iterrows():
        dirn = AI_S[f.cfg][1] if f.cfg.startswith("F12") else S[f.cfg]
        oc = ocs[f.set]
        tr = simulate(dirn, oc, FUT_RT, cum_f, (i0, i1))
        st = week_stats(tr["net"], tr["t"], d.index)
        rec = dict(cfg=f.cfg, set=f.set, D_mean=f.D_mean, D_t=f.D_t, D_n=f.D_n, V_mean=f.V_mean, V_n=f.V_n, **{f"H_{k}": v for k, v in st.items()})
        if st["n"] >= 2:
            rec["H_ci95"] = boot_ci(tr["net"], tr["t"], d.index)
            y26 = d.index[tr["t"]] >= pd.Timestamp("2026-01-01")
            rec["H_mean_2025"] = float(tr["net"][~y26].mean()) if (~y26).any() else None
            rec["H_mean_2026"] = float(tr["net"][y26].mean()) if y26.any() else None
            p_long = float((tr["dir"] > 0).mean())
            ctl = random_control(oc, st["n"], p_long, i0, i1, FUT_RT, cum_f)
            rec["H_ctrl_p95"] = float(np.nanpercentile(ctl, 95)); rec["H_ctrl_median"] = float(np.nanmedian(ctl))
            rec["H_dsr"], rec["H_sr"], rec["sr0"] = dsr(tr["net"], N_trials, sr_var)
            rec["H_tp_rate"] = float((tr["why"] == 1).mean()); rec["H_pstar"] = be[f.set]["fut"]
            rec["H_median_hold_h"] = float(np.median(tr["exit"] - tr["t"]) * 5 / 60); rec["H_long_share"] = p_long
            for cm, cost, lo in (("spot", SPOT_RT, True), ("maker", MAKER_RT, False)):
                t2 = simulate(dirn, oc, cost, None if cm == "spot" else cum_f, (i0, i1), longs_only=lo)
                rec[f"H_{cm}"] = week_stats(t2["net"], t2["t"], d.index)
            g = dict(G1=rec["H_mean"] > 0 and rec["H_ci95"][0] > 0, G2=st["n"] >= 100, G3=rec["H_mean"] >= rec["H_ctrl_p95"],
                     G4=(rec["H_mean_2025"] or -1) > 0 and (rec["H_mean_2026"] or -1) > 0, G5=rec["H_dsr"] > 0.95)
            rec["gates"] = g; rec["edge"] = bool(all(g.values()))
            pd.DataFrame(dict(t=tr["t"], time=d.index[tr["t"]], dir=tr["dir"], gross=tr["gross"], net=tr["net"], exit=tr["exit"], why=tr["why"])).to_csv(
                OUT / f"H_trades_{f.cfg}_{f.set}.csv", index=False)
        H.append(rec)
        log(f"holdout {f.cfg} {f.set}: {rec.get('H_n')} trades mean {rec.get('H_mean')} edge {rec.get('edge')}")
    cal_H = [dict(bucket=int(b.bucket), dow=int(b.dow), hour=int(b.hour), H_n=b.H_n, H_mean=b.H_mean, H_t=b.H_t) for _, b in cal_v.iterrows()]
    base = {}
    for cfg in ("F0_random", "F1_long", "F1_short"):
        for s in ("A1_1", "A2_2", "V2"):
            for pn in ("D", "V", "H"):
                tr = simulate(S[cfg], ocs[s], FUT_RT, cum_f, P[pn])
                base[f"{cfg}|{s}|{pn}"] = week_stats(tr["net"], tr["t"], d.index)
    res = dict(protocol_sha256=sha(OUT / "BTC_ENTRY_PROTOCOL_PREREGISTERED.md"), code_sha256=sha(__file__), manifest_sha256=sha(OUT / "input_manifest.csv"),
               costs=dict(fut=FUT_RT, spot=SPOT_RT, maker=MAKER_RT), breakeven=be, N_trials=N_trials, sr_var=sr_var,
               counts=dict(fut_configs=len(Rf), positive_D=len(sel), top3=len(top), v_pass=len(v_ok), finals=len(finals)),
               finals=H, calendar=cal, calendar_finals_H=cal_H, baselines=base,
               top3_per_family=top[["cfg", "set", "D_n", "D_mean", "D_t", "V_n", "V_mean"]].to_dict("records"))
    f = OUT / "BTC_ENTRY_RESULTS.json"
    f.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (OUT / "RESULTS_SHA256.txt").write_text(sha(f) + "  BTC_ENTRY_RESULTS.json\n")
    log("done; edges: " + str([(h["cfg"], h["set"]) for h in H if h.get("edge")]))


if __name__ == "__main__":
    main()