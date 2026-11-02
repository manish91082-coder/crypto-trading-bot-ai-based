"""N1 (trial T15): rule-only 4-sleeve portfolio. Protocol logs/research_n1_portfolio/N1_PROTOCOL_PREREGISTERED.md,
implementation choices in logs/research_n1_portfolio/CODE_NOTES.md. Historical simulation only (no orders, no money).
Usage: python src/research/n1_portfolio.py"""
import hashlib
import heapq
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tf_edge_map as M

ROOT = M.ROOT
OUT = ROOT / "logs" / "research_n1_portfolio"
DER = ROOT / "data" / "derived" / "n1"
B1H = DER / "bars1h"
PRE = ROOT / "data" / "universe_pre2020" / "1h"
E0, FEE, FEE_SPOT, KATR, HEAT = 10_000.0, 0.00054, 0.00085, 3.0, 0.06
SEED, NRAND, NB = 20261024, 100, 2000
TFS, TFS_B = ["4h", "8h", "12h", "1D"], ["8h", "12h", "1D"]
TFI = {tf: i for i, tf in enumerate(TFS)}
EXCL = ("LUNAUSDT", "STRAXUSDT")
STABLE = {"BUSDUSDT", "PAXUSDT", "TUSDUSDT", "USDCUSDT", "USDSUSDT", "USDSBUSDT"}
WIN = {"dev": ("2020-02-01", "2025-10-01"), "P1": ("2020-02-01", "2024-01-01"), "P2": ("2024-01-01", "2025-10-01"),
       "P3": ("2025-10-01", "2026-10-01")}
G7W = ("2018-04-17", "2020-01-01")
SLEEVES = "ABCD"
CONFIGS = {"K0": {}, "K1": {"stop": False}, "K2": {"heat": True}, "K3": {"corr": True}, "K4": {"noD": True}, "K5": {"noC": True},
           "K6": {"vol": True}}
SLEEVE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s); print(s, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------- bars ----------------
def bars1h(coin):
    f = B1H / f"{coin}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    d = M.load5m(coin)
    b = d.resample("1h", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    B1H.mkdir(parents=True, exist_ok=True)
    b.to_parquet(f)
    return b


def atr14(b):
    h, l, c = b.high.values, b.low.values, b.close.values
    pc = np.r_[np.nan, c[:-1]]
    tr = np.where(np.isnan(pc), h - l, np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))))
    return pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values


def read_funding(coin):
    f = M.FUM / f"{coin}_funding.csv"
    if not f.exists():
        return None
    x = pd.read_csv(f)
    x["time"] = pd.to_datetime(x["time"])
    x = x.sort_values("time")
    return x.time.values, x.funding_rate.values.astype(float)


class Coin:
    def __init__(self, name, grid, h1, fund):
        n = len(grid)
        pos = grid.get_indexer(h1.index)
        ok = pos >= 0
        self.name = name
        self.O, self.H, self.L = (np.full(n, np.nan) for _ in range(3))
        C = np.full(n, np.nan)
        for arr, col in ((self.O, "open"), (self.H, "high"), (self.L, "low"), (C, "close")):
            arr[pos[ok]] = h1[col].values[ok]
        self.Cf = pd.Series(C).ffill().values
        self.tf = {}
        for tf in TFS:
            b = M.resample(h1, tf)
            self.tf[tf] = (b.index, b.open.values, b.high.values, b.low.values, b.close.values, atr14(b))
        self.tfh = {tf: grid.get_indexer(self.tf[tf][0]) for tf in TFS}
        self.rate = np.zeros(n)
        self.f0 = None
        if fund is not None:
            ft, r = fund
            self.f0 = ft[0]
            kk = grid.searchsorted(ft, side="left")              # CODE_NOTES 3: active iff a < kk <= E
            v = (ft >= grid[0].to_datetime64()) & (kk < n)
            np.add.at(self.rate, kk[v], r[v])
        self.cumrate = np.r_[0.0, np.cumsum(self.rate)]

    def dC(self, h0, h1):
        prev = self.Cf[h0 - 1:h1 - 1] if h0 > 0 else np.r_[np.nan, self.Cf[:h1 - 1]]
        return np.nan_to_num(self.Cf[h0:h1] - prev)


def sparse(v, fn):
    t, k = [v], 1
    while 2 * k <= len(v):
        p = t[-1]; t.append(fn(p[:-k], p[k:])); k *= 2
    return t


def first_hit(tab, a, b, thr, below):
    """first index h in [a, b) with v[h] <= thr (below) / v[h] >= thr (above); returns b when none."""
    pos = a.copy()
    for j in range(len(tab) - 1, -1, -1):
        st = 1 << j
        c = np.flatnonzero(pos + st <= b)
        if not len(c):
            continue
        v = tab[j][pos[c]]
        skip = v > thr[c] if below else v < thr[c]
        pos[c[skip]] += st
    return pos


# ---------------- trades ----------------
def load_tfx(sleeve):
    uni, fams, tfs, side = {"A": ("U1", (0, 1, 2, 3), TFS, 1), "B": ("U1", (4,), TFS_B, 1), "C": ("U2", (0, 1, 2, 3), TFS, -1)}[sleeve]
    rows = []
    for tf in tfs:
        for f in sorted((M.TR / uni / M.DIRN.get(tf, tf)).glob("*.parquet")):
            if f.stem in EXCL:
                continue
            q = pd.read_parquet(f, columns=["coin", "fam", "side", "e", "x", "hold", "entry_time", "gross", "fund", "year"])
            q = q[q.fam.isin(fams) & (q.side == side) & q.fund.notna()]
            q["tf"] = tf
            rows.append(q)
    T = pd.concat(rows, ignore_index=True)
    T["sleeve"] = sleeve
    T["entry_time"] = pd.to_datetime(T.entry_time)
    return T


def sim(T, C, stop=True, slip=0.0):
    """per-trade hour mapping, fixed 3-ATR stop scanned on 1h bars, exit price, gross, funding sum (side x rates)."""
    n_ = len(T)
    a_, E_, en_, X_, hit_, dist_, fs_, gr_ = (np.zeros(n_, dtype=t) for t in (np.int64, np.int64, float, float, bool, float, float, float))
    for coin, idx in T.groupby("coin").indices.items():
        cd = C[coin]
        sub = T.iloc[idx]
        tabs = {}
        for side in np.unique(sub.side.values):
            if stop:
                tabs[side] = sparse(np.where(np.isnan(cd.L), np.inf, cd.L), np.minimum) if side == 1 else \
                    sparse(np.where(np.isnan(cd.H), -np.inf, cd.H), np.maximum)
        for tf, jj in sub.groupby("tf").indices.items():
            ii = idx[jj]
            ts, O, H, L, Cl, A = cd.tf[tf]
            th = cd.tfh[tf]
            e, x, s = T.e.values[ii], T.x.values[ii], T.side.values[ii]
            a, b = th[e], th[x]
            assert (a >= 0).all() and (b > a).all(), (coin, tf)
            en, xs = O[e], O[x]
            dist = KATR * A[e - 1]
            stp = en - s * dist
            E = b.copy(); X = xs.copy(); hit = np.zeros(len(ii), bool)
            if stop:
                for side in (1, -1):
                    q = np.flatnonzero(s == side)
                    if not len(q):
                        continue
                    p = first_hit(tabs[side], a[q], b[q], stp[q], side == 1)
                    h = p < b[q]
                    qq = q[h]
                    E[qq] = p[h]
                    fill = np.minimum(cd.O[p[h]], stp[qq]) if side == 1 else np.maximum(cd.O[p[h]], stp[qq])
                    X[qq] = fill * (1 - side * slip)
                    hit[qq] = True
            a_[ii], E_[ii], en_[ii], X_[ii], hit_[ii], dist_[ii] = a, E, en, X, hit, dist / en
            fs_[ii] = s * (cd.cumrate[E + 1] - cd.cumrate[a + 1])
            gr_[ii] = s * (X - en) / en
    L = T[["sleeve", "coin", "tf", "fam", "side", "entry_time", "hold", "e"]].copy()
    L["a"], L["E"], L["entry"], L["X"], L["stopped"], L["dist"], L["fsum"], L["gross"] = a_, E_, en_, X_, hit_, dist_, fs_, gr_
    L["nofund"] = False
    L["fee"] = FEE
    return L


# ---------------- D sleeve (DISC D4 code path) ----------------
class DCtx:
    def __init__(self, C, coins, liq, fund_f0, grid):
        self.coins = coins
        Op = pd.DataFrame({c: pd.Series(C[c].tf["1D"][1], index=C[c].tf["1D"][0]) for c in coins})
        Cl = pd.DataFrame({c: pd.Series(C[c].tf["1D"][4], index=C[c].tf["1D"][0]) for c in coins})
        idx = Op.index
        self.idx, self.Op, self.Cl = idx, Op.reindex(idx), Cl.reindex(idx)
        self.L = pd.DataFrame({c: idx.floor("D").isin(liq[c]) for c in coins}, index=idx)
        self.hist = self.Cl.notna().cumsum()
        self.mom = self.Cl / self.Cl.shift(20) - 1
        self.f0 = fund_f0
        self.gpos = grid.get_indexer(idx)


def build_D(dc, C, rng=None, cost_split=False, start_time=M.START):
    idx = dc.idx
    trades, costs, periods = [], [], []
    prevw = pd.Series(0.0, index=dc.coins)
    start = int(np.searchsorted(idx, start_time))
    for t in range(start, len(idx) - 6, 5):
        el = dc.L.iloc[t] & (dc.hist.iloc[t] >= 25) & dc.mom.iloc[t].notna() & dc.Op.iloc[t + 1].notna() & dc.Op.iloc[t + 6].notna()
        m_ = dc.mom.iloc[t][el]
        if len(m_) < 10:
            continue
        q = len(m_) // 5
        if rng is None:
            lg, sh = m_.sort_values().index[-q:], m_.sort_values().index[:q]
        else:
            pm = rng.permutation(np.array(m_.index))
            lg, sh = pd.Index(pm[:q]), pd.Index(pm[q:2 * q])
        w = pd.Series(0.0, index=dc.coins); w[lg] = 1 / len(lg); w[sh] = -1 / len(sh)
        if cost_split:
            tl = float((w.clip(lower=0) - prevw.clip(lower=0)).abs().sum()); tsh = float((w.clip(upper=0) - prevw.clip(upper=0)).abs().sum())
            cost = 0.2 * (FEE_SPOT * tl + FEE * tsh)
        else:
            cost = 0.2 * FEE * float((w - prevw).abs().sum())
        prevw = w
        a, b = dc.gpos[t + 1], dc.gpos[t + 6]
        t0 = idx[t + 1].to_datetime64()
        for cs, sd in ((lg, 1), (sh, -1)):
            for c in cs:
                f0 = dc.f0.get(c)
                trades.append((c, sd, idx[t + 1], a, b, float(dc.Op[c].iloc[t + 1]), float(dc.Op[c].iloc[t + 6]), 0.2 / len(cs),
                               bool(f0 is None or t0 < f0)))
        costs.append((idx[t + 1], a, cost))
        periods.append((idx[t + 6], len(trades) - len(lg) - len(sh), len(trades), cost))
    D = pd.DataFrame(trades, columns=["coin", "side", "entry_time", "a", "E", "entry", "X", "w", "nofund"])
    D["sleeve"] = "D"; D["tf"] = "1D"; D["fam"] = -1; D["stopped"] = False; D["dist"] = 0.0
    fs = np.zeros(len(D))
    for coin, ii in D.groupby("coin").indices.items():
        cd = C[coin]
        fs[ii] = D.side.values[ii] * (cd.cumrate[D.E.values[ii] + 1] - cd.cumrate[D.a.values[ii] + 1])
    D["fsum"] = np.where(D.nofund, 0.0, fs)
    D["fee"] = 0.0
    D["gross"] = D.side * (D.X - D.entry) / D.entry
    Cst = pd.DataFrame(costs, columns=["entry_time", "a", "cost"])
    return D, Cst, periods


# ---------------- weights ----------------
class WCtx:
    def __init__(self, C, core, u2x, liq):
        cl = pd.DataFrame({c: pd.Series(C[c].tf["1D"][4], index=C[c].tf["1D"][0]) for c in sorted(set(core) | set(u2x)) if c in C})
        r = cl.pct_change(fill_method=None)
        rc = r[[c for c in core if c in r]]
        rho = {}
        for i in range(len(rc)):
            w = rc.iloc[max(0, i - 59):i + 1]
            if len(w) < 40:
                continue
            cm = w.corr(min_periods=40).values
            off = cm[~np.eye(len(cm), dtype=bool)]
            off = off[np.isfinite(off)]
            if len(off):
                rho[rc.index[i]] = off.mean()
        rho = pd.Series(rho)
        ref = rho.expanding(min_periods=180).median()
        self.mcorr = np.minimum(1.0, np.sqrt((1 + 9 * ref) / np.maximum(1 + 9 * rho, 1e-9))).dropna()
        self.sig = r.rolling(60, min_periods=40).std()
        days = self.sig.index
        self.liqmask = pd.DataFrame({c: days.isin(liq[c]) if c in liq else np.zeros(len(days), bool) for c in self.sig.columns}, index=days)
        S1 = self.sig.shift(1)                                            # value at D = sigma of day D-1
        self.med_core = S1[[c for c in core if c in S1]].median(axis=1)
        self.med_u2x = S1[[c for c in u2x if c in S1]].where(self.liqmask[[c for c in u2x if c in S1]]).median(axis=1)
        self.S1s = S1.stack()
        self.nliq = self.liqmask[[c for c in u2x if c in self.liqmask]].sum(axis=1)


def base_w(L, wc, nliq_floor=10):
    w = np.zeros(len(L))
    s = L.sleeve.values
    w[s == "A"] = 0.8 / 160; w[s == "B"] = 0.4 / 30
    c = s == "C"
    if c.any():
        n = wc.nliq.reindex(pd.DatetimeIndex(L.entry_time.values[c]).floor("D")).fillna(0).values
        w[c] = 0.4 / (16 * np.maximum(nliq_floor, n))
    d = s == "D"
    if d.any():                                   # CODE_CHANGES 1: L has no 'w' column when D is excluded (K4)
        w[d] = L.w.values[d]
    return w


def apply_overlays(L, w, cfg, wc):
    abc = L.sleeve.isin(["A", "B", "C"]).values
    day = pd.DatetimeIndex(L.entry_time.values).floor("D")
    if cfg.get("corr"):
        m = wc.mcorr.reindex(day - pd.Timedelta(days=1)).fillna(1.0).values
        w = np.where(abc, w * m, w)
    if cfg.get("vol"):
        sc = wc.S1s.reindex(pd.MultiIndex.from_arrays([day, L.coin.values])).values.astype(float)
        med = np.where(L.sleeve.values == "C", wc.med_u2x.reindex(day).values, wc.med_core.reindex(day).values)
        mult = np.where(np.isfinite(sc) & np.isfinite(med) & (sc > 0), np.clip(med / sc, 0.5, 2.0), 1.0)
        w = np.where(abc, w * mult, w)
    if cfg.get("heat"):
        w = w.copy()
        sub = L[abc].assign(_tfi=L.tf.map(TFI), _so=L.sleeve.map(SLEEVE_ORDER))
        order = sub.sort_values(["a", "_so", "coin", "_tfi", "fam"], kind="mergesort").index.values
        pos = {ix: k for k, ix in enumerate(L.index.values)}
        heap, heat = [], 0.0
        for ix in order:
            k = pos[ix]
            a = L.a.values[k]
            while heap and heap[0][0] <= a:
                heat -= heapq.heappop(heap)[1]
            hj = w[k] * L.dist.values[k]
            room = HEAT - heat
            if room <= 1e-15 or hj <= 0:
                w[k] = 0.0 if room <= 1e-15 else w[k]
                continue
            if hj > room:
                w[k] *= room / hj; hj = room
            heat += hj
            heapq.heappush(heap, (L.E.values[k], hj))
    return w


# ---------------- portfolio ----------------
def month_starts(grid, h0, h1):
    t = grid[h0:h1]
    ms = np.flatnonzero(np.r_[True, t.month[1:] != t.month[:-1]])
    return ms


def run_pf(L, C, grid, h0, h1, costs=None, fee_scale=1.0, want=False):
    """L needs coin, side, a, E, entry, X, w, fee (per side), nofund. Returns stats (+ curve)."""
    H = h1 - h0
    ms = month_starts(grid, h0, h1)
    Mn = len(ms)
    P = np.zeros((Mn, H))
    L = L[L.w > 0].astype({"a": np.int64, "E": np.int64, "nofund": bool, "fee": float})   # CODE_CHANGES 2: concat dtypes
    for coin, idx in L.groupby("coin").indices.items():
        cd = C[coin]
        a = L.a.values[idx] - h0; E = L.E.values[idx] - h0
        s = L.side.values[idx].astype(float); w = L.w.values[idx]; en = L.entry.values[idx]; X = L.X.values[idx]
        fee = L.fee.values[idx] * fee_scale; nf = L.nofund.values[idx]
        mm = np.searchsorted(ms, a, side="right") - 1
        u = s * w / en
        Ec = np.minimum(E, H)
        lo = a + 1; hi = np.maximum(Ec, lo)
        D2 = np.zeros((Mn, H + 1))
        np.add.at(D2, (mm, lo), u); np.add.at(D2, (mm, hi), -u)
        P += np.cumsum(D2[:, :H], axis=1) * cd.dC(h0, h1)
        same = E == a
        cfa = cd.Cf[a + h0]
        np.add.at(P, (mm, a), np.where(same, s * w * (X - en) / en, s * w * (cfa - en) / en))
        ex = (~same) & (E < H)
        cfe = cd.Cf[np.clip(E + h0 - 1, 0, len(cd.Cf) - 1)]
        np.add.at(P, (mm[ex], E[ex]), (s * w * (X - cfe) / en)[ex])
        np.add.at(P, (mm, a), -w * fee)
        np.add.at(P, (mm[E < H], E[E < H]), -(w * fee * X / en)[E < H])
        fd = ~nf
        if fd.any():
            D3 = np.zeros((Mn, H + 1))
            np.add.at(D3, (mm[fd], (a + 1)[fd]), (s * w)[fd]); np.add.at(D3, (mm[fd], np.minimum(E + 1, H)[fd]), -(s * w)[fd])
            P -= np.cumsum(D3[:, :H], axis=1) * cd.rate[h0:h1]
    if costs is not None and len(costs):
        cc = costs[(costs.a >= h0) & (costs.a < h1)]
        ca = cc.a.values - h0
        np.add.at(P, (np.searchsorted(ms, ca, side="right") - 1, ca), -cc.cost.values * fee_scale)
    CP = np.cumsum(P, axis=1)
    Em = np.zeros(Mn)
    for k, s0 in enumerate(ms):
        Em[k] = E0 + (Em[:k] @ CP[:k, s0 - 1] if s0 > 0 else 0.0)
    curve = E0 + Em @ CP
    return stats(curve, grid[h0:h1], grid[h0], grid[h1] if h1 < len(grid) else grid[-1] + pd.Timedelta(hours=1), want, Em)


def stats(curve, t, t0, t1, want, Em):
    yrs = (t1 - t0).days / 365.25
    final = float(curve[-1])
    cagr = (final / E0) ** (1 / yrs) - 1 if final > 0 else -1.0
    run = np.maximum.accumulate(np.r_[E0, curve])
    dd = float((1 - np.r_[E0, curve] / run).max())
    me = pd.Series(curve, index=t).groupby(t.to_period("M")).last()
    mret = me / me.shift(1).fillna(E0) - 1
    out = dict(final=final, cagr=float(cagr), mtm_dd=dd, calmar=float(cagr / dd) if dd > 0 else np.nan,
               mean_month=float(mret.mean()), sharpe_month=float(mret.mean() / mret.std(ddof=1)) if mret.std(ddof=1) > 0 else np.nan,
               months=len(mret))
    if want:
        out["monthly"] = mret; out["curve"] = curve; out["Em"] = Em
    return out


def pbo(Mx):
    """CSCV on a (months x configs) return matrix, 16 contiguous blocks (A4 code)."""
    blocks = np.array_split(np.arange(len(Mx)), 16)
    logits = []
    for comb in itertools.combinations(range(16), 8):
        is_ = np.concatenate([blocks[i] for i in comb]); oos = np.concatenate([blocks[i] for i in range(16) if i not in comb])
        sr_is = (Mx.iloc[is_].mean() / Mx.iloc[is_].std(ddof=1)).round(12)
        sr_oos = (Mx.iloc[oos].mean() / Mx.iloc[oos].std(ddof=1)).round(12)
        best = sr_is.idxmax()
        rank = sr_oos.rank(method="average")[best]
        wv = rank / (len(Mx.columns) + 1)
        logits.append(np.log(wv / (1 - wv)))
    logits = np.array(logits)
    return float((logits < 0).mean()), logits


def dsr(ret, sr_var, n):
    sr = ret.mean() / ret.std(ddof=1)
    g = 0.5772156649
    sr0 = np.sqrt(sr_var) * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e)))
    z = (sr - sr0) * np.sqrt(len(ret) - 1) / np.sqrt(1 - ret.skew() * sr + (ret.kurt() + 2) / 4 * sr ** 2)
    return float(norm.cdf(z)), float(sr), float(sr0)


# ---------------- assembly ----------------
class World:
    pass


def assemble(Wd, cfg, ledgers, D, t0, t1, scale=1.0, only=None):
    parts = []
    for sl in "ABC":
        if sl == "C" and cfg.get("noC"):
            continue
        if only and sl not in only:
            continue
        parts.append(ledgers[sl])
    if not cfg.get("noD") and (not only or "D" in only):
        parts.append(D)
    L = pd.concat(parts, ignore_index=True)
    L = L[(L.entry_time >= pd.Timestamp(t0)) & (L.entry_time < pd.Timestamp(t1))].reset_index(drop=True)
    w = base_w(L, Wd.wc)
    w = apply_overlays(L, w, cfg, Wd.wc)
    L["w"] = w * scale
    assert L.fee.notna().all()
    return L


def run_cfg(Wd, cfg, t0, t1, ledgers=None, D=None, costs=None, fee_scale=1.0, scale=1.0, want=False, only=None):
    led = ledgers or (Wd.led_stop if cfg.get("stop", True) else Wd.led_nostop)
    D = Wd.D if D is None else D
    costs = Wd.Dcost if costs is None else costs
    L = assemble(Wd, cfg, led, D, t0, t1, scale=scale, only=only)
    use_costs = None if (cfg.get("noD") or (only and "D" not in only)) else costs.assign(cost=costs.cost * scale)
    h0, h1 = Wd.grid.get_loc(pd.Timestamp(t0)), Wd.grid.get_loc(pd.Timestamp(t1))
    r = run_pf(L, Wd.C, Wd.grid, h0, h1, costs=use_costs, fee_scale=fee_scale, want=want)
    r["n_trades"] = int((L.w > 0).sum())
    if want:
        r["L"] = L
    return r


def relocate(T, C, rng, liq, t0, t1):
    out = T.copy()
    keep = np.ones(len(T), bool)
    ne = T.e.values.copy()
    nt = T.entry_time.values.copy()
    t0, t1 = pd.Timestamp(t0), pd.Timestamp(t1)
    for (coin, tf, sl), idx in T.groupby(["coin", "tf", "sleeve"]).indices.items():
        cd = C[coin]
        ts = cd.tf[tf][0]
        n = len(ts)
        yrs = ts.year.values
        base = (ts >= t0) & (ts < t1) & (np.arange(n) >= 1)
        if cd.f0 is not None:
            base &= ts.values >= cd.f0
        if sl == "C":
            base &= ts.floor("D").isin(liq[coin])
        ey = T.year.values[idx]
        for y in np.unique(ey):
            q = idx[ey == y]
            pool = np.flatnonzero(base & (yrs == y))
            lim = np.searchsorted(pool, n - T.hold.values[q])
            ok = lim > 0
            pick = pool[np.minimum((rng.random(len(q)) * lim).astype(np.int64), np.maximum(lim - 1, 0))] if len(pool) else np.zeros(len(q), int)
            ne[q] = np.where(ok, pick, 0); keep[q] &= ok
            nt[q] = ts.values[ne[q]]
    out["e"] = ne
    out["x"] = ne + T.hold.values
    out["entry_time"] = nt
    out = out[keep].reset_index(drop=True)
    return out, int((~keep).sum())


def load_world():
    t = time.time()
    Wd = World()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import r2_t14_universe as U
    u2x = [c for c in U.candidates() if (M.HF / f"{c}_5m_full.csv.gz").exists() and c not in EXCL]
    T = {s: load_tfx(s) for s in "ABC"}
    coins = sorted(set(M.CORE10) | set(u2x) | set(T["C"].coin))
    h1s = {c: bars1h(c) for c in coins}
    gend = max(b.index[-1] for b in h1s.values()) + pd.Timedelta(hours=1)
    grid = pd.date_range("2020-02-01", gend, freq="h")
    log("coins", len(coins), "grid", grid[0], grid[-1], len(grid), f"{time.time() - t:.0f}s")
    C = {c: Coin(c, grid, h1s[c], read_funding(c)) for c in coins}
    del h1s
    liq = {c: M.liq_days(c) for c in u2x}
    Wd.grid, Wd.C, Wd.T, Wd.liq, Wd.u2x = grid, C, T, liq, u2x
    Wd.wc = WCtx(C, M.CORE10, u2x, liq)
    Wd.dc = DCtx(C, u2x, liq, {c: C[c].f0 for c in u2x}, grid)
    log("world loaded", f"{time.time() - t:.0f}s")
    return Wd


# ---------------- G7 (2018-19, spot) ----------------
def g7(final_cfg):
    files = sorted(PRE.glob("*_1h_full.csv.gz"))
    coins = [f.name.split("_")[0] for f in files if f.name.split("_")[0] not in STABLE]
    raw = {}
    for c in coins:
        x = pd.read_csv(PRE / f"{c}_1h_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close", "quote_volume"], parse_dates=["timestamp"])
        raw[c] = x.set_index("timestamp").sort_index()
    gend = max(b.index[-1] for b in raw.values()) + pd.Timedelta(hours=1)
    grid = pd.date_range(min(b.index[0] for b in raw.values()).floor("D"), gend, freq="h")
    C = {c: Coin(c, grid, raw[c][["open", "high", "low", "close"]], None) for c in coins}
    liq = {}
    for c in coins:
        dly = raw[c].quote_volume.resample("1D").sum(min_count=1)
        full = dly.reindex(pd.date_range(dly.index.min(), dly.index.max(), freq="1D"))
        med = full.rolling(M.LIQ_DAYS, min_periods=M.LIQ_MIN).median().shift(1)
        liq[c] = set(med[med >= M.LIQ].index)
    t0, t1 = pd.Timestamp(G7W[0]), pd.Timestamp(G7W[1])
    rows = []
    core = [c for c in M.CORE10 if c in C]
    for sl, cs, fams, tfs, side in (("A", core, (0, 1, 2, 3), TFS, 1), ("B", core, (4,), TFS_B, 1), ("C", coins, (0, 1, 2, 3), TFS, -1)):
        for c in cs:
            for tf in tfs:
                ts, O, H, L, Cl, A = C[c].tf[tf]
                b = pd.DataFrame(dict(open=O, high=H, low=L, close=Cl), index=ts)
                n = len(b)
                for fi in fams:
                    le, lx, se, sx = M.conditions(b, M.FAM[fi])
                    en, ex = (le, lx) if side == 1 else (se, sx)
                    tt, uu = M.state_trades(en, ex)
                    e, x = tt + 1, uu + 1
                    k = x < n
                    e, x = e[k], x[k]
                    k = (ts[e] >= t0) & (ts[e] < t1)
                    if sl == "C":
                        k &= ts[e].floor("D").isin(liq[c])
                    e, x = e[k], x[k]
                    for ei, xi in zip(e, x):
                        rows.append((sl, c, tf, fi, side, int(ei), int(xi), int(xi - ei), ts[ei]))
    T = pd.DataFrame(rows, columns=["sleeve", "coin", "tf", "fam", "side", "e", "x", "hold", "entry_time"])
    led = sim(T, C, stop=final_cfg.get("stop", True))
    led["fee"] = np.where(led.sleeve == "C", FEE, FEE_SPOT)
    dc = DCtx(C, coins, liq, {}, grid)
    D, Dc, _ = build_D(dc, C, cost_split=True, start_time=t0)
    Wg = World(); Wg.wc = WCtx(C, core, coins, liq)
    parts = [led[led.sleeve != "C"] if final_cfg.get("noC") else led]
    if not final_cfg.get("noD"):
        parts.append(D)
    L = pd.concat(parts, ignore_index=True)
    L = L[(L.entry_time >= t0) & (L.entry_time < t1)].reset_index(drop=True)
    w = apply_overlays(L, base_w(L, Wg.wc), final_cfg, Wg.wc)
    L["w"] = w
    h0, h1 = grid.get_loc(t0), grid.get_loc(t1)
    r = run_pf(L, C, grid, h0, h1, costs=None if final_cfg.get("noD") else Dc, want=True)
    per = {s: int(((L.sleeve == s) & (L.w > 0)).sum()) for s in SLEEVES}
    btc = C["BTCUSDT"]
    bh = float(btc.Cf[h1 - 1] / btc.O[h0] - 1)
    return r, per, bh, int(len(D)), int((Dc.a >= h0).sum())


# ---------------- main ----------------
def main():
    proto = OUT / "N1_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "N1_PROTOCOL_SHA256.txt").read_text().split()[0], "N1 protocol changed"
    assert sha(DER / "input_manifest_tfx_trades.txt") == "63be8b3d39fa9ebb5e797481def1a015e83f4874c75654ccb9661cf87db3e10e"
    for l in (DER / "input_manifest_tfx_trades.txt").read_text(encoding="utf-8").splitlines():
        h, p = l.split("  ", 1)
        assert sha(ROOT / p) == h, p
    Wd = load_world()
    # reproduction asserts (CODE_NOTES 9)
    Wd.led_nostop = {s: sim(Wd.T[s], Wd.C, stop=False) for s in "ABC"}
    for s in "ABC":
        g = np.abs(Wd.led_nostop[s].gross.values - Wd.T[s].gross.values).max()
        f = np.abs(Wd.led_nostop[s].fsum.values - Wd.T[s].fund.values).max()
        log(f"repro {s}: n {len(Wd.T[s])} max|gross-TFX| {g:.1e} max|fund-TFX| {f:.1e}")
        assert g < 1e-12 and f < 1e-12
    miss = sum(int(np.isnan(Wd.C[c].O[Wd.led_nostop[s].a.values[Wd.led_nostop[s].coin.values == c]]).sum())
               for s in "ABC" for c in Wd.led_nostop[s].coin.unique())
    log("entries whose entry hour has no 1h bar (TF open taken from a later hour):", miss)
    Wd.led_stop = {s: sim(Wd.T[s], Wd.C, stop=True) for s in "ABC"}
    for s in "ABC":
        Ls = Wd.led_stop[s]
        log(f"stop {s}: stopped share {Ls.stopped.mean():.3f}")
    Wd.D, Wd.Dcost, periods = build_D(Wd.dc, Wd.C)
    d4 = pd.read_csv(M.OUT / "disc" / "D4_periods_1D.csv", parse_dates=["t"])
    unit = Wd.D.side * Wd.D.w * (Wd.D.X - Wd.D.entry) / Wd.D.entry - Wd.D.w * Wd.D.fsum
    mine = [(t, float(unit.iloc[i0:i1].sum() - c)) for t, i0, i1, c in periods]
    mm = pd.DataFrame(mine, columns=["t", "u"]).merge(d4[["t", "ret"]], on="t", how="outer")
    dmax = float(np.abs(mm.u - 0.2 * mm.ret).max())
    log(f"repro D: periods {len(mine)} vs D4 {len(d4)}, max|unit-0.2*ret| {dmax:.1e}, D4-rule zero-funding legs {int(Wd.D.nofund.sum())}")
    assert len(mine) == len(d4) and dmax < 1e-12
    # configurations
    rows, monthly, calm = [], {}, {}
    for k, cfg in CONFIGS.items():
        for wn, (t0, t1) in WIN.items():
            r = run_cfg(Wd, cfg, t0, t1, want=(wn == "dev"))
            calm[(k, wn)] = r["calmar"]
            if wn == "dev":
                monthly[k] = r.pop("monthly"); r.pop("curve"); r.pop("Em"); r.pop("L")
            rows.append(dict(config=k, window=wn, **r))
        log("config", k, {wn: round(calm[(k, wn)], 3) for wn in WIN})
    adopt = {k: all(calm[(k, w)] > calm[("K0", w)] for w in ("dev", "P1", "P2")) for k in CONFIGS if k != "K0"}
    final_cfg = {}
    for k, ad in adopt.items():
        if ad:
            final_cfg.update(CONFIGS[k])
    final_name = next((k for k, c in CONFIGS.items() if c == final_cfg), "FINAL")
    log("adopt", adopt, "final", final_name, final_cfg)
    if final_name == "FINAL":
        for wn, (t0, t1) in WIN.items():
            r = run_cfg(Wd, final_cfg, t0, t1, want=(wn == "dev"))
            calm[("FINAL", wn)] = r["calmar"]
            if wn == "dev":
                monthly["FINAL"] = r.pop("monthly"); r.pop("curve"); r.pop("Em"); r.pop("L")
            rows.append(dict(config="FINAL", window=wn, **r))
    G = pd.DataFrame(rows)
    G["adopted"] = G.config.map(adopt)
    G.to_csv(OUT / "N1_configs.csv", index=False)
    Mx = pd.DataFrame(monthly)
    Mx.index = Mx.index.astype(str)
    Mx.to_csv(OUT / "N1_monthly_dev.csv")
    n_cfg = len(Mx.columns)
    # FINAL dev, full detail
    t0, t1 = WIN["dev"]
    F = run_cfg(Wd, final_cfg, t0, t1, want=True)
    led = Wd.led_stop if final_cfg.get("stop", True) else Wd.led_nostop
    F["L"].to_parquet(DER / f"trades_{final_name}.parquet", index=False)
    pd.DataFrame(dict(t=Wd.grid[Wd.grid.get_loc(pd.Timestamp(t0)):Wd.grid.get_loc(pd.Timestamp(t1))], equity=F["curve"])).to_parquet(
        DER / f"equity_{final_name}.parquet", index=False)
    # G1 random entry
    rnd, dropped = [], []
    devT = {s: Wd.T[s][(Wd.T[s].entry_time >= t0) & (Wd.T[s].entry_time < t1)] for s in "ABC"}
    for i in range(NRAND):
        rng = np.random.default_rng(SEED + i)
        rl = {}
        for s in "ABC":
            Tr, dr = relocate(devT[s], Wd.C, rng, Wd.liq, t0, t1)
            dropped.append(dr)
            rl[s] = sim(Tr, Wd.C, stop=final_cfg.get("stop", True))
        Dr, Dcr, _ = build_D(Wd.dc, Wd.C, rng=rng)
        r = run_cfg(Wd, final_cfg, t0, t1, ledgers=rl, D=Dr, costs=Dcr)
        rnd.append(dict(i=i, calmar=r["calmar"], cagr=r["cagr"], mtm_dd=r["mtm_dd"], mean_month=r["mean_month"]))
        if i % 10 == 0:
            log("random", i, round(r["calmar"], 3))
    R = pd.DataFrame(rnd); R.to_csv(OUT / "N1_random_entry.csv", index=False)
    p95 = float(np.percentile(R.calmar, 95))
    # G2 cost
    c15 = run_cfg(Wd, final_cfg, t0, t1, fee_scale=1.5)
    c20 = run_cfg(Wd, final_cfg, t0, t1, fee_scale=2.0)
    led_slip = {s: sim(Wd.T[s], Wd.C, stop=True, slip=0.003) for s in "ABC"} if final_cfg.get("stop", True) else Wd.led_nostop
    csl = run_cfg(Wd, final_cfg, t0, t1, ledgers=led_slip)
    # G4 bootstrap
    rng = np.random.default_rng(SEED)
    fm = Mx[final_name].values
    bm = rng.choice(fm, size=(NB, len(fm)), replace=True).mean(axis=1)
    ci = (float(np.quantile(bm, 0.025)), float(np.quantile(bm, 0.975)))
    # G5 DSR, G6 PBO
    sr_var = float(np.var([Mx[c].mean() / Mx[c].std(ddof=1) for c in Mx.columns], ddof=1))
    n_trials = 14 + 5 + n_cfg
    dsr_v, sr, sr0 = dsr(pd.Series(fm), sr_var, n_trials)
    pbo_v, logits = pbo(Mx[list(CONFIGS)])
    # G7
    g7r, g7n, g7bh, g7d, g7dp = g7(final_cfg)
    pd.DataFrame([dict(window="2018-04-17..2019-12-31", **{k: v for k, v in g7r.items() if k not in ("monthly", "curve", "Em")},
                       trades=json.dumps(g7n), btc_buy_hold=g7bh, d_legs=g7d, d_periods=g7dp)]).to_csv(OUT / "N1_g7_pre2020.csv", index=False)
    cal = {wn: calm[(final_name, wn)] for wn in WIN}
    gates = {"G1_random_entry_p95": F["calmar"] > p95,
             "G2_cost_1.5x_2x_slip": all(x["mean_month"] > 0 for x in (c15, c20, csl)),
             "G3_P1_P2_calmar>0": cal["P1"] > 0 and cal["P2"] > 0,
             "G4_bootstrap_ci_lo>0": ci[0] > 0,
             "G5_DSR>=0.95": dsr_v >= 0.95,
             "G6_PBO<0.30": pbo_v < 0.30,
             "G7_2018_19_calmar>0": bool(g7r["calmar"] > 0)}
    verdict = "N1 PASS" if all(gates.values()) else "N1 FAIL"
    # report-only items
    years = []
    full = run_cfg(Wd, final_cfg, "2020-02-01", "2026-10-01", want=True)
    eq = pd.Series(full["curve"], index=Wd.grid[Wd.grid.get_loc(pd.Timestamp("2020-02-01")):Wd.grid.get_loc(pd.Timestamp("2026-10-01"))])
    btc = Wd.C["BTCUSDT"]
    for y, g in eq.groupby(eq.index.year):
        prev = eq[eq.index < g.index[0]]
        e_start = prev.iloc[-1] if len(prev) else E0
        run_ = np.maximum.accumulate(np.r_[e_start, g.values])
        hb0 = Wd.grid.get_loc(g.index[0]); hb1 = Wd.grid.get_loc(g.index[-1])
        years.append(dict(year=y, ret=float(g.iloc[-1] / e_start - 1), mtm_dd=float((1 - np.r_[e_start, g.values] / run_).max()),
                          btc=float(btc.Cf[hb1] / (btc.Cf[hb0 - 1] if hb0 > 0 else btc.O[hb0]) - 1)))
    pd.DataFrame(years).to_csv(OUT / "N1_years.csv", index=False)
    sl_rows, sl_m = [], {}
    for s in SLEEVES:
        if (s == "C" and final_cfg.get("noC")) or (s == "D" and final_cfg.get("noD")):
            continue
        r = run_cfg(Wd, final_cfg, t0, t1, want=True, only=(s,))
        sl_m[s] = r.pop("monthly"); r.pop("curve"); r.pop("Em"); r.pop("L")
        sl_rows.append(dict(sleeve=s, **r))
    S = pd.DataFrame(sl_rows)
    corr = pd.DataFrame(sl_m).corr()
    S.to_csv(OUT / "N1_sleeves.csv", index=False)
    corr.to_csv(OUT / "N1_sleeve_corr.csv")
    sizing = [dict(scale=sc, **{k: v for k, v in run_cfg(Wd, final_cfg, t0, t1, scale=sc).items()}) for sc in (0.5, 1.0, 1.5)]
    pd.DataFrame(sizing).to_csv(OUT / "N1_sizing.csv", index=False)
    d1 = pd.read_csv(ROOT / "logs" / "strategy_1d_step27_combine" / "sleeves_MAIN_f50.csv", parse_dates=["date"]).set_index("date").D1
    d1m = d1.groupby(d1.index.to_period("M")).last().pct_change().dropna()
    d1m.index = d1m.index.astype(str)
    jj = Mx[final_name].index.intersection(d1m.index)
    corr_1d = float(np.corrcoef(Mx[final_name].loc[jj], d1m.loc[jj])[0, 1])
    bh = {}
    for wn, (a_, b_) in WIN.items():
        h0, h1 = Wd.grid.get_loc(pd.Timestamp(a_)), Wd.grid.get_loc(pd.Timestamp(b_))
        cv = btc.Cf[h0:h1]
        cv = cv / btc.O[h0] * E0
        bh[wn] = stats(cv, Wd.grid[h0:h1], Wd.grid[h0], Wd.grid[h1], False, None)
    # exposure (FINAL dev)
    L = F["L"]; Em = F["Em"]
    h0, h1 = Wd.grid.get_loc(pd.Timestamp(t0)), Wd.grid.get_loc(pd.Timestamp(t1))
    ms = month_starts(Wd.grid, h0, h1)
    gross = np.zeros(h1 - h0); netmax = np.zeros(h1 - h0)
    sub = L[L.w > 0]
    for coin, idx in sub.groupby("coin").indices.items():
        a = sub.a.values[idx] - h0; E = np.minimum(sub.E.values[idx] - h0, h1 - h0)
        u = sub.side.values[idx] * sub.w.values[idx] / sub.entry.values[idx] * Em[np.searchsorted(ms, a, side="right") - 1]
        d = np.zeros(h1 - h0 + 1); np.add.at(d, a, u); np.add.at(d, E, -u)
        net = np.abs(np.cumsum(d[:-1]) * Wd.C[coin].Cf[h0:h1])
        gross += net; netmax = np.maximum(netmax, net)
    curve = F["curve"]
    expo = dict(max_gross=float((gross / curve).max()), mean_gross=float((gross / curve).mean()), max_coin_net=float((netmax / curve).max()))
    claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), notes_sha=sha(OUT / "CODE_NOTES.md"),
                  manifest_sha=sha(DER / "input_manifest_tfx_trades.txt"),
                  repro=dict(D_periods=len(mine), D_max_diff=dmax, entry_hour_missing=miss),
                  stopped_share={s: float(Wd.led_stop[s].stopped.mean()) for s in "ABC"},
                  adopt=adopt, final_name=final_name, final_cfg=final_cfg, n_configs=n_cfg, n_trials_dsr=n_trials,
                  final_dev={k: F[k] for k in ("final", "cagr", "mtm_dd", "calmar", "mean_month", "sharpe_month", "n_trades")},
                  calmar_windows=cal, random_p95=p95, random_dropped_trades=int(np.sum(dropped)),
                  cost=dict(x1_5=c15["mean_month"], x2=c20["mean_month"], slip=csl["mean_month"]),
                  boot_ci=ci, dsr=dsr_v, sr_month=sr, sr0=sr0, sr_var=sr_var, pbo=pbo_v, pbo_combinations=len(logits),
                  g7=dict(calmar=g7r["calmar"], cagr=g7r["cagr"], mtm_dd=g7r["mtm_dd"], trades=g7n, btc_bh=g7bh),
                  corr_1d_monthly=corr_1d, corr_1d_months=len(jj), btc_bh={k: {q: v[q] for q in ("cagr", "mtm_dd", "calmar")} for k, v in bh.items()},
                  exposure=expo, gates=gates, verdict=verdict,
                  files={f.name: sha(f) for f in sorted(OUT.glob("N1_*.csv"))},
                  trades_sha=sha(DER / f"trades_{final_name}.parquet"), equity_sha=sha(DER / f"equity_{final_name}.parquet"))
    (OUT / "claims_n1.json").write_text(json.dumps(claims, indent=1, default=float))
    (OUT / "N1_gates.json").write_text(json.dumps(dict(gates=gates, verdict=verdict), indent=1))
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        log(G.round(4).to_string()); log(S.round(4).to_string()); log(corr.round(3).to_string())
        log(pd.DataFrame(years).round(4).to_string())
    log(json.dumps({k: v for k, v in claims.items() if k != "files"}, indent=1, default=float))
    (OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
