"""Micro-momentum study on BTC spot 1-second data: "price rising 1-3 minutes with volume -> enter".

Protocol: logs/micro_momentum_2026/MICRO_MOMENTUM_PROTOCOL_PREREGISTERED.md (SHA in PROTOCOL_SHA256.txt).
Stages:
  python src/research/micro_momentum.py disc_val   # QC + Part A (DISC) + Part B (DISC, VAL) + §7 steps 1-2
  python src/research/micro_momentum.py hold       # §7 step 3, only if decision.json picked a config
This script shares no code with earlier studies.
"""
import hashlib, io, json, math, sys, time, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "micro_momentum_2026"
DATA = ROOT / "data" / "external" / "binance_1s"
PROTO = OUT / "MICRO_MOMENTUM_PROTOCOL_PREREGISTERED.md"
PROTO_SHA = "dc0b48c42e7be118c7973dae9f1fd82b0f737ce01c9c0fafb3b4c1df6667b2a8"
FIVE_MIN = ROOT / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz"
FEES = ROOT / "deploy" / "fees.json"
PERIODS = {"DISC": ["2026-01"], "VAL": ["2026-02", "2026-03", "2026-04", "2026-05"],
           "HOLD": ["2026-06", "2026-07", "2026-08", "2026-09"]}
WS = [60, 120, 180, 300]
HS = [30, 60, 120, 180, 300, 600]
NS, KS, SS = [1, 2, 3], [1.0, 1.5, 2.0, 3.0], [0.0, 0.55, 0.60]
EXITS = ["XT60", "XT180", "XT300", "XT600", "XU"]
WARM = 3600 + max(WS)          # first usable feature second
TAIL = 1 + max(HS)             # seconds lost at the end for Part A
CAP = 1800
N_BOOT, BOOT_SEED, N_RAND, SAMPLE_SEED, N_SAMPLE = 2000, 7, 1000, 99, 3000
LOG = OUT / "run_log.txt"


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def costs():
    f = json.loads(FEES.read_text())
    return {"fut": f["rules"]["paper_futures_taker_per_side"], "spot": f["rules"]["paper_spot_per_side"],
            "fut_maker": f["futures_usdm"]["bnb_maker"] + f["impact_per_side"]}


def cfg_name(N, k, s, x):
    return f"N{N}_k{k:g}_s{s:g}_{x}"


def read_zip_csv(path, ncol):
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        raw = z.read(name)
    first = raw[:200].decode().splitlines()[0].split(",")[0]
    header = 0 if not first.strip().lstrip("-").isdigit() else None
    d = pd.read_csv(io.BytesIO(raw), header=header)
    d = d.iloc[:, :ncol]
    d.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
                 "taker_buy_base", "taker_buy_quote", "ignore"][:ncol]
    return d


def ts_unit(v):
    return "us" if v > 1e14 else "ms"


def load_month(month):
    """Second grid for one month: P (close), O/H/L kept only for real rows, vol, taker, flags."""
    d = read_zip_csv(DATA / "spot_1s" / f"BTCUSDT-1s-{month}.zip", 12)
    unit = ts_unit(float(d["open_time"].iloc[0]))
    sec = (d["open_time"].to_numpy(np.int64) // (1_000_000 if unit == "us" else 1000))
    start = int(pd.Timestamp(month + "-01").timestamp())
    end = int((pd.Timestamp(month + "-01") + pd.offsets.MonthBegin(1)).timestamp())
    N = end - start
    idx = sec - start
    inside = (idx >= 0) & (idx < N)
    order = np.argsort(idx[inside], kind="stable")
    ii = idx[inside][order]
    keep = np.ones(len(ii), bool)
    keep[1:] = ii[1:] != ii[:-1]
    dup = int((~keep).sum())
    sel = np.flatnonzero(inside)[order][keep]
    ii = ii[keep]
    close = np.full(N, np.nan)
    close[ii] = d["close"].to_numpy(float)[sel]
    present = np.zeros(N, bool)
    present[ii] = True
    first_open = float(d["open"].to_numpy(float)[sel][0])
    if np.isnan(close[0]):
        close[0] = first_open
    # forward fill
    m = np.where(~np.isnan(close), np.arange(N), 0)
    np.maximum.accumulate(m, out=m)
    close = close[m]
    vol = np.zeros(N)
    vol[ii] = d["volume"].to_numpy(float)[sel]
    tak = np.zeros(N)
    tak[ii] = d["taker_buy_base"].to_numpy(float)[sel]
    real = pd.DataFrame({"i": ii, "open": d["open"].to_numpy(float)[sel], "high": d["high"].to_numpy(float)[sel],
                         "low": d["low"].to_numpy(float)[sel], "close": d["close"].to_numpy(float)[sel],
                         "volume": vol[ii]})
    return {"month": month, "start": start, "N": N, "P": close, "vol": vol, "tak": tak, "present": present,
            "dup": dup, "unit": unit, "rows": len(d), "real": real}


def qc_month(g, five):
    N, start = g["N"], g["start"]
    days = N // 86400
    miss_day = [int((~g["present"][d * 86400:(d + 1) * 86400]).sum()) for d in range(days)]
    r = g["real"]
    b = r["i"].to_numpy() // 300
    agg = r.groupby(b).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                           close=("close", "last"), volume=("volume", "sum"))
    agg.index = pd.to_datetime(start + agg.index * 300, unit="s")
    f = five.loc[(five.index >= agg.index.min()) & (five.index <= agg.index.max())]
    j = agg.join(f, how="outer", rsuffix="_f")
    both = j.dropna()
    bad = np.zeros(len(both), bool)
    for c in ("open", "high", "low", "close"):
        bad |= ~np.isclose(both[c], both[c + "_f"], rtol=1e-9, atol=0)
    vbad = ~np.isclose(both["volume"], both["volume_f"], rtol=1e-6, atol=0)
    # spot vs futures 1m
    fu = read_zip_csv(DATA / "futures_1m" / f"BTCUSDT-1m-{g['month']}.zip", 12)
    fu_t = fu["open_time"].to_numpy(np.int64) // (1_000_000 if ts_unit(float(fu["open_time"].iloc[0])) == "us" else 1000)
    fser = pd.Series(fu["close"].to_numpy(float), index=fu_t).sort_index()
    fser = fser[~fser.index.duplicated()]
    mins = np.arange(N // 60)
    spot_close = pd.Series(g["P"][mins * 60 + 59], index=start + mins * 60)
    a = np.log(spot_close).diff()
    bb = np.log(fser).diff()
    jj = pd.concat([a.rename("s"), bb.rename("f")], axis=1).dropna()
    jj = jj[jj.index.isin(spot_close.index)]
    return {"month": g["month"], "rows": g["rows"], "unit": g["unit"], "duplicates": g["dup"],
            "missing_seconds": int(sum(miss_day)), "max_missing_day": int(max(miss_day)),
            "days_over_1pct_missing": int(sum(m > 864 for m in miss_day)),
            "five_min_bars_compared": len(both), "five_min_only_one_side": int(len(j) - len(both)),
            "five_min_ohlc_mismatch": int(bad.sum()), "five_min_volume_mismatch": int(vbad.sum()),
            "spot_fut_1m_corr": float(np.corrcoef(jj["s"], jj["f"])[0, 1]),
            "spot_fut_1m_mean_abs_diff": float((jj["s"] - jj["f"]).abs().mean()),
            "spot_fut_1m_sign_differs": float((np.sign(jj["s"]) != np.sign(jj["f"])).mean()),
            "spot_fut_minutes": len(jj)}, miss_day


def shift(a, k, fill=np.nan):
    """b[t] = a[t-k] (k>0 looks back, k<0 looks forward)."""
    b = np.full(len(a), fill, dtype=float)
    if k > 0:
        b[k:] = a[:-k]
    elif k < 0:
        b[:k] = a[-k:]
    else:
        b[:] = a
    return b


def wsum(cs, W):
    """sum over (t-W, t] from a cumulative sum cs (cs[t] = sum up to t)."""
    out = np.full(len(cs), np.nan)
    out[W:] = cs[W:] - cs[:-W]
    return out


class Features:
    """Features of §3, computed on demand. Only the ones the rules need are cached (memory)."""
    KEEP = {"UPMIN", "DOWNMIN", "VOLR_60", "TAKER_60", "RHYTHM_60"}

    def __init__(self, g):
        self.P, N = g["P"], g["N"]
        dP = np.zeros(N)
        dP[1:] = np.diff(self.P)
        self.cu = np.cumsum(dP > 0)
        self.cd = np.cumsum(dP < 0)
        self.ca = np.cumsum(np.abs(dP))
        self.cv = np.cumsum(g["vol"])
        self.ct = np.cumsum(g["tak"])
        self.cache = {}

    def __getitem__(self, name):
        if name in self.cache:
            return self.cache[name]
        v = self._compute(name)
        if name in self.KEEP:
            self.cache[name] = v
        return v

    def _compute(self, name):
        P = self.P
        N = len(P)
        if name in ("UPMIN", "DOWNMIN"):
            base = np.zeros(N, bool)
            base[60:] = (P[60:] > P[:-60]) if name == "UPMIN" else (P[60:] < P[:-60])
            cnt = np.zeros(N, np.int8)
            alive = np.ones(N, bool)
            for k in range(10):
                sh = np.zeros(N, bool)
                sh[60 * k:] = base[:N - 60 * k] if k else base
                alive &= sh
                cnt += alive
            return cnt
        kind, W = name.rsplit("_", 1)
        W = int(W)
        with np.errstate(invalid="ignore", divide="ignore"):
            if kind == "R":
                return P / shift(P, W) - 1
            if kind == "RHYTHM":
                u, d_ = wsum(self.cu, W), wsum(self.cd, W)
                return np.where(u + d_ > 0, u / (u + d_), np.nan)
            if kind == "STRAIGHT":
                path = wsum(self.ca, W)
                return np.where(path > 0, np.abs(P - shift(P, W)) / path, np.nan)
            vw = wsum(self.cv, W)
            if kind == "VOLR":
                prior = shift(self.cv, W) - shift(self.cv, W + 3600)
                return np.where(prior > 0, vw / (W * prior / 3600), np.nan)
            if kind == "TAKER":
                return np.where(vw > 0, wsum(self.ct, W) / vw, np.nan)
        raise KeyError(name)


def future(P, h):
    return shift(P, -(1 + h)) / shift(P, -1) - 1


def day_boot(sums, cnts, rng_seed=BOOT_SEED, n=N_BOOT, level=0.95):
    """Day-block bootstrap of a ratio mean: sums/cnts per day."""
    sums, cnts = np.asarray(sums, float), np.asarray(cnts, float)
    D = len(sums)
    if cnts.sum() == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, D, size=(n, D))
    s, c = sums[idx].sum(1), cnts[idx].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = s / c
    m = m[np.isfinite(m)]
    a = (1 - level) / 2
    return (float(np.quantile(m, a)), float(np.quantile(m, 1 - a)))


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (mid - half, mid + half)


def part_a(g, F):
    P, N = g["P"], g["N"]
    use = np.zeros(N, bool)
    use[WARM:N - TAIL] = True
    day = np.arange(N) // 86400
    D = N // 86400
    fut = {h: future(P, h) for h in HS}
    res = {"A1": {}, "A3": {}}
    for h in HS:
        x = fut[h][use]
        res["A1"][h] = {"mean": float(x.mean()), "std": float(x.std()), "p5": float(np.percentile(x, 5)),
                        "p50": float(np.percentile(x, 50)), "p95": float(np.percentile(x, 95)),
                        "share_abs_gt_fut_rt": float((np.abs(x) > 0.00092).mean()),
                        "share_abs_gt_spot_rt": float((np.abs(x) > 0.0017).mean()), "n": int(use.sum())}
    rows = []
    for fname in [f"{t}_{W}" for t in ("R", "RHYTHM", "STRAIGHT", "VOLR", "TAKER") for W in WS]:
        f = F[fname]
        ok = use & np.isfinite(f)
        cuts = np.quantile(f[ok], np.linspace(0.1, 0.9, 9))
        dec = np.searchsorted(cuts, f, side="right")
        for h in HS:
            fh = fut[h]
            okh = ok & np.isfinite(fh)
            overall = float(fh[okh].mean())
            for q in range(10):
                m = okh & (dec == q)
                sums = np.bincount(day[m], weights=fh[m], minlength=D)
                cnts = np.bincount(day[m], minlength=D)
                lo, hi = day_boot(sums, cnts)
                rows.append({"feature": fname, "h": h, "decile": q + 1, "lo_cut": float(cuts[q - 1]) if q else -np.inf,
                             "hi_cut": float(cuts[q]) if q < 9 else np.inf, "n": int(cnts.sum()),
                             "mean_F": float(sums.sum() / cnts.sum()), "ci_lo": lo, "ci_hi": hi,
                             "minus_overall": float(sums.sum() / cnts.sum() - overall)})
    dec_df = pd.DataFrame(rows)
    for name in ("UPMIN", "DOWNMIN"):
        res["A3"][name] = {}
        v = F[name]
        for n_ in range(6):
            m0 = use & ((v == n_) if n_ < 5 else (v >= 5))
            cell = {"n_seconds": int(m0.sum())}
            for h in HS:
                fh = fut[h]
                m = m0 & np.isfinite(fh)
                sums = np.bincount(day[m], weights=fh[m], minlength=D)
                cnts = np.bincount(day[m], minlength=D)
                cell[h] = {"mean": float(sums.sum() / cnts.sum()) if cnts.sum() else float("nan"),
                           "ci": day_boot(sums, cnts)}
            res["A3"][name][str(n_) if n_ < 5 else "5+"] = cell
    ev = []
    for side in ("up", "down"):
        for N_ in NS:
            for k in KS:
                for s in SS:
                    c = signal(F, N_, k, s, side)
                    st = starts(c)
                    m = st & use
                    row = {"side": side, "N": N_, "k": k, "s": s, "n_events": int(m.sum())}
                    for h in HS:
                        fh = fut[h]
                        mm = m & np.isfinite(fh)
                        sums = np.bincount(day[mm], weights=fh[mm], minlength=D)
                        cnts = np.bincount(day[mm], minlength=D)
                        row[f"mean_F{h}"] = float(sums.sum() / cnts.sum()) if cnts.sum() else float("nan")
                        lo, hi = day_boot(sums, cnts)
                        row[f"ci_lo_F{h}"], row[f"ci_hi_F{h}"] = lo, hi
                    ev.append(row)
    return res, dec_df, pd.DataFrame(ev)


def signal(F, N_, k, s, side="up"):
    with np.errstate(invalid="ignore"):
        if side == "up":
            return (F["UPMIN"] >= N_) & (F["VOLR_60"] >= k) & (F["TAKER_60"] >= s)
        return (F["DOWNMIN"] >= N_) & (F["VOLR_60"] >= k) & (F["TAKER_60"] <= 1 - s)


def starts(c):
    st = c.copy()
    st[1:] = c[1:] & ~c[:-1]
    st[0] = False
    return st


def exit_signal(F):
    with np.errstate(invalid="ignore"):
        return (F["DOWNMIN"] >= 1) & (F["RHYTHM_60"] < 0.5) & (F["VOLR_60"] >= 1)


def simulate(P, start_secs, exit_secs, xname, L):
    """Greedy one-position simulation. Returns arrays (entry_sec, exit_sec, forced)."""
    N = len(P)
    last = N - 1
    E, X, FO = [], [], []
    i = 0
    ns = len(start_secs)
    while i < ns:
        t = start_secs[i]
        e = t + L
        if e > last:
            break
        if xname == "XU":
            j = np.searchsorted(exit_secs, e, side="right")
            if j < len(exit_secs) and exit_secs[j] <= e + CAP:
                x = exit_secs[j] + L
                if x > e + CAP:
                    x = e + CAP
            else:
                x = e + CAP
        else:
            x = e + int(xname[2:])
        forced = x > last
        if forced:
            x = last
        E.append(e)
        X.append(x)
        FO.append(forced)
        i = np.searchsorted(start_secs, x, side="right")
    return np.array(E, np.int64), np.array(X, np.int64), np.array(FO, bool)


def run_rules(g, F, c, L=1, only=None):
    """Compact trade table for one month (net columns are derived later as gross - 2c)."""
    P = g["P"]
    xs = np.flatnonzero(exit_signal(F))
    out = []
    for N_ in NS:
        for k in KS:
            for s in SS:
                st = np.flatnonzero(starts(signal(F, N_, k, s)))
                st = st[st >= WARM]
                for x in EXITS:
                    name = cfg_name(N_, k, s, x)
                    if only is not None and name not in only:
                        continue
                    E, X, FO = simulate(P, st, xs, x, L)
                    out.append(pd.DataFrame({"config": name, "entry_sec": E.astype(np.int32), "exit_sec": X.astype(np.int32),
                                             "entry_px": P[E], "exit_px": P[X], "forced": FO, "gross": P[X] / P[E] - 1}))
    T = pd.concat(out, ignore_index=True)
    T["config"] = pd.Categorical(T["config"], categories=all_configs())
    T["month"] = pd.Categorical([g["month"]] * len(T), categories=[m for v in PERIODS.values() for m in v])
    T["L"] = np.int8(L)
    return T


def maxdd(net):
    eq = np.concatenate([[1.0], np.cumprod(1 + net)])
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def period_days(months):
    days = []
    for m in months:
        days += list(pd.date_range(m + "-01", pd.Timestamp(m + "-01") + pd.offsets.MonthEnd(0), freq="D").strftime("%Y-%m-%d"))
    return days


def day_pos(T, months):
    """Position of each trade's exit day in period_days(months)."""
    off, pos = 0, np.zeros(len(T), np.int64)
    mcol = T["month"].astype(str).to_numpy()
    for m in months:
        nd = pd.Timestamp(m + "-01").days_in_month
        sel = mcol == m
        pos[sel] = off + T["exit_sec"].to_numpy()[sel] // 86400
        off += nd
    return pos


def metrics_for(T, period, months, c, names=None):
    """Metrics rows and daily rows for every config of the grid (configs without trades included)."""
    days = period_days(months)
    D = len(days)
    pos_all = day_pos(T, months)
    month_of_day = np.array([d[:7] for d in days])
    rows, daily = [], []
    codes = T["config"].cat.codes.to_numpy()
    cats = list(T["config"].cat.categories)
    order = np.argsort(codes, kind="stable")
    bounds = np.searchsorted(codes[order], np.arange(len(cats) + 1))
    gross_all = T["gross"].to_numpy()
    hold_all = (T["exit_sec"].to_numpy() - T["entry_sec"].to_numpy())
    forced_all = T["forced"].to_numpy()
    for ci, name in enumerate(cats):
        if names is not None and name not in names:
            continue
        idx = order[bounds[ci]:bounds[ci + 1]]
        g = gross_all[idx]
        pos = pos_all[idx]
        n = len(g)
        cnt = np.bincount(pos, minlength=D)
        drow = {"config": name, "period": period, "day": days, "n": cnt}
        for m, cc in c.items():
            nt = g - 2 * cc
            sums = np.bincount(pos, weights=nt, minlength=D)
            drow[f"net_{m}"] = sums
            lo, hi = day_boot(sums, cnt)
            mon = pd.Series(sums).groupby(month_of_day).sum().reindex(months, fill_value=0)
            w = int((nt > 0).sum())
            rows.append({"config": name, "period": period, "cost": m, "n": n, "wins": w,
                         "win_rate": w / n if n else np.nan, "wilson_lo": wilson(w, n)[0], "wilson_hi": wilson(w, n)[1],
                         "mean_net": float(nt.mean()) if n else np.nan, "median_net": float(np.median(nt)) if n else np.nan,
                         "sum_net": float(nt.sum()), "compounded": float(np.prod(1 + nt) - 1), "maxdd": maxdd(nt),
                         "ci95_lo": lo, "ci95_hi": hi, "trades_per_day": n / D,
                         "avg_hold_s": float(hold_all[idx].mean()) if n else np.nan, "forced": int(forced_all[idx].sum()),
                         "months_pos": int((mon > 0).sum()), "months": len(months)})
        daily.append(pd.DataFrame(drow))
    return rows, pd.concat(daily, ignore_index=True)



def all_configs():
    return [cfg_name(N_, k, s, x) for N_ in NS for k in KS for s in SS for x in EXITS]


def random_control(g_list, T, name, c_fut):
    """Per seed: each trade of `name` replaced by a long of the same hold at a random usable second of its month."""
    tr = T[T.config == name]
    sums = np.zeros(N_RAND)
    for g in g_list:
        t = tr[tr.month == g["month"]]
        if len(t) == 0:
            continue
        h = (t["exit_sec"].to_numpy() - t["entry_sec"].to_numpy()).astype(np.int64)
        P = g["P"]
        lo = WARM + 1
        hi = len(P) - h  # entry u in [lo, hi)
        for sd in range(1, N_RAND + 1):
            u = np.random.default_rng(sd * 1000 + int(g["month"][-2:])).integers(lo, hi)
            sums[sd - 1] += (P[u + h] / P[u] - 1 - 2 * c_fut).sum()
    return sums / len(tr)


def stage_disc_val():
    t0 = time.time()
    assert sha(PROTO) == PROTO_SHA and (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0] == PROTO_SHA
    log(f"stage disc_val start; protocol {PROTO_SHA[:12]}; code {sha(Path(__file__))[:12]}")
    c = costs()
    log(f"costs per side from deploy/fees.json: {c}")
    five = pd.read_csv(FIVE_MIN, usecols=["timestamp", "open", "high", "low", "close", "volume"])
    five["timestamp"] = pd.to_datetime(five["timestamp"])
    five = five[(five.timestamp >= "2026-01-01") & (five.timestamp < "2026-06-01")].set_index("timestamp")
    qc_rows, miss_rows, all_T, metrics, daily = [], [], {}, [], []
    gs = {}
    for period in ("DISC", "VAL"):
        Ts = []
        for month in PERIODS[period]:
            g = load_month(month)
            q, md = qc_month(g, five)
            qc_rows.append(q)
            miss_rows += [{"month": month, "day": i + 1, "missing_seconds": v} for i, v in enumerate(md)]
            log(f"QC {month}: {q}")
            F = Features(g)
            if period == "DISC":
                res, dec_df, ev_df = part_a(g, F)
                (OUT / "partA_disc.json").write_text(json.dumps(res, indent=1, default=str))
                dec_df.to_csv(OUT / "partA_deciles_disc.csv", index=False)
                ev_df.to_csv(OUT / "partA_events_disc.csv", index=False)
                log("Part A written")
                rng = np.random.default_rng(SAMPLE_SEED)
                secs = np.sort(rng.choice(np.arange(WARM, g["N"] - TAIL), N_SAMPLE, replace=False))
                smp = {"sec": secs, "time": pd.to_datetime(g["start"] + secs, unit="s")}
                for nm in ("R_60", "R_300", "UPMIN", "DOWNMIN", "RHYTHM_60", "STRAIGHT_60", "VOLR_60", "TAKER_60"):
                    smp[nm] = F[nm][secs].astype(float)
                smp["F_60"], smp["F_300"] = future(g["P"], 60)[secs], future(g["P"], 300)[secs]
                pd.DataFrame(smp).to_parquet(OUT / "features_sample_disc.parquet", index=False)
            T = run_rules(g, F, c, L=1)
            Ts.append(T)
            log(f"rules {month}: {len(T)} trades over 180 configs")
            gs[month] = {"month": month, "P": g["P"], "start": g["start"], "F": None}
            del F, g
        T = pd.concat(Ts, ignore_index=True)
        all_T[period] = T
        T.to_parquet(OUT / f"trades_{period}.parquet", index=False)
        rows, dly = metrics_for(T, period, PERIODS[period], c)
        metrics += rows
        daily.append(dly)
        log(f"metrics {period} done")
    pd.DataFrame(qc_rows).to_csv(OUT / "qc_months.csv", index=False)
    pd.DataFrame(miss_rows).to_csv(OUT / "qc_missing_by_day.csv", index=False)
    M = pd.DataFrame(metrics)
    M.to_csv(OUT / "metrics.csv", index=False)
    D = pd.concat(daily, ignore_index=True)
    D.to_csv(OUT / "daily.csv", index=False)
    D.assign(month=D["day"].str[:7]).groupby(["config", "period", "month"]).agg(
        n=("n", "sum"), net_fut=("net_fut", "sum"), net_spot=("net_spot", "sum")).reset_index().to_csv(OUT / "monthly.csv", index=False)

    # §7 step 1: shortlist on DISC
    md = M[(M.period == "DISC") & (M.cost == "fut")]
    sl = md[(md.n >= 30) & (md.mean_net > 0) & (md.ci95_lo > -0.0005)].sort_values("mean_net", ascending=False).head(10)
    shortlist = list(sl["config"])
    log(f"shortlist on DISC: {shortlist}")
    dec = {"shortlist": shortlist, "val": [], "pick": None,
           "disc_best": md.sort_values("mean_net", ascending=False).head(10)[["config", "n", "mean_net", "ci95_lo"]].to_dict("records")}
    rc_rows = []
    if shortlist:
        mval = M[(M.period == "VAL") & (M.cost == "fut")].set_index("config")
        m_ = len(shortlist)
        TV = all_T["VAL"]
        # latency 5 s sensitivity and Bonferroni CI on VAL
        lat_rows = []
        for name in shortlist:
            dv = D[(D.config == name) & (D.period == "VAL")]
            lo, _ = day_boot(dv["net_fut"].to_numpy(), dv["n"].to_numpy(), level=1 - 0.05 / m_)
            vgs = [gs[mm] for mm in PERIODS["VAL"]]
            rc = random_control(vgs, TV, name, c["fut"])
            act = float(mval.loc[name, "mean_net"]) if name in mval.index else float("nan")
            p = float((rc >= act).mean())
            rc_rows.append({"config": name, "period": "VAL", "actual_mean_net": act, "rand_median": float(np.median(rc)), "p": p})
            ok = bool(act > 0 and lo > 0 and p < 0.05 and mval.loc[name, "months_pos"] >= 3)
            dec["val"].append({"config": name, "val_mean_net": act, "val_bonf_lo": lo, "rand_p": p,
                               "val_months_pos": int(mval.loc[name, "months_pos"]), "pass": ok})
        passed = [v for v in dec["val"] if v["pass"]]
        if passed:
            dec["pick"] = max(passed, key=lambda v: v["val_mean_net"])["config"]
        # latency 5 s rows for the shortlist (DISC and VAL)
        for period in ("DISC", "VAL"):
            Ts = []
            for month in PERIODS[period]:
                g = load_month(month)
                F = Features(g)
                Ts.append(run_rules(g, F, c, L=5, only=set(shortlist)))
                del F, g
            T5 = pd.concat(Ts, ignore_index=True)
            for r in metrics_for(T5, period, PERIODS[period], {"fut": c["fut"]}, names=set(shortlist))[0]:
                r["L"] = 5
                lat_rows.append(r)
        pd.DataFrame(lat_rows).to_csv(OUT / "latency5_shortlist.csv", index=False)
    pd.DataFrame(rc_rows, columns=["config", "period", "actual_mean_net", "rand_median", "p"]).to_csv(OUT / "random_control.csv", index=False)
    (OUT / "decision.json").write_text(json.dumps(dec, indent=1, default=float))
    log(f"decision: pick {dec['pick']}")
    files = ["download_manifest.csv", "qc_months.csv", "qc_missing_by_day.csv", "features_sample_disc.parquet", "partA_disc.json",
             "partA_deciles_disc.csv", "partA_events_disc.csv", "trades_DISC.parquet", "trades_VAL.parquet", "metrics.csv",
             "daily.csv", "monthly.csv", "random_control.csv", "decision.json"]
    if shortlist:
        files.append("latency5_shortlist.csv")
    res = {"protocol_sha": PROTO_SHA, "code_sha": sha(Path(__file__)), "costs_per_side": c, "shortlist": shortlist,
           "pick": dec["pick"], "runtime_s": round(time.time() - t0, 1)}
    (OUT / "RESULTS.json").write_text(json.dumps(res, indent=1))
    files.append("RESULTS.json")
    (OUT / "OUTPUT_SHA256.txt").write_text("".join(f"{sha(OUT / f)}  {f}\n" for f in files))
    log(f"stage disc_val done in {time.time() - t0:.0f} s")


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "disc_val"
    if stage == "disc_val":
        # copy of the download manifest into the output folder (for the SHA list)
        (OUT / "download_manifest.csv").write_bytes((DATA / "MANIFEST.csv").read_bytes())
        stage_disc_val()
    elif stage == "hold":
        dec = json.loads((OUT / "decision.json").read_text())
        if not dec.get("pick"):
            print("no config picked in §7 step 2: HOLD stays sealed (protocol §1.2)")
            return
        raise SystemExit("HOLD stage: to be written only after a pick exists, as a time-stamped CODE_CHANGES entry")
    else:
        raise SystemExit(f"unknown stage {stage}")


if __name__ == "__main__":
    main()
