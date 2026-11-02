"""Independent verifier for N1 (logs/research_n1_portfolio/N1_PROTOCOL_PREREGISTERED.md, section 8). Own code: does NOT import
n1_portfolio. Bars come straight from the raw 5m files (groupby-floor, not the N1 1h cache).
V1 300 random A/B/C sub-trades: own TF bars, ATR, 1h stop scan, fill, funding -> gross / fsum / exit to 1e-9 (+ TFX gross without stop)
V2 FINAL dev equity rebuilt event-by-event from the trade ledger + own D turnover costs + own weights -> final equity, MTM-DD
V3 50 random D rebalances from own 1D bars + own liquidity -> leg sets and prices
V4 selection rule, PBO, DSR, bootstrap CI from the saved matrices
V5 SHAs: protocol lock, TFX manifest, claims files, registry T15"""
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_n1_portfolio"
DR = R_ / "data" / "derived" / "n1"
HF = R_ / "data" / "universe_hf" / "5m"
FU = R_ / "data" / "futures_um"
E0 = 10_000.0
HRS = {"4h": 4, "8h": 8, "12h": 12, "1D": 24}
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


_c5 = {}


def raw5(coin):
    if coin not in _c5:
        x = pd.read_csv(HF / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
        x["timestamp"] = pd.to_datetime(x.timestamp)
        _c5.clear(); _c5[coin] = x.sort_values("timestamp").reset_index(drop=True)
    return _c5[coin]


def agg(x, key):
    g = x.groupby(key)
    return pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last()))


def tfbars(x, tf):
    return agg(x, x.timestamp.dt.floor("D") if tf == "1D" else x.timestamp.dt.floor(f"{HRS[tf]}h"))


def own_atr(b):
    h, l, c = b.high.values, b.low.values, b.close.values
    out = np.empty(len(b)); v = None
    for i in range(len(b)):
        tr = h[i] - l[i] if i == 0 else max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        v = tr if v is None else v + (tr - v) / 14.0
        out[i] = v
    return out


def funding(coin):
    f = pd.read_csv(FU / f"{coin}_funding.csv")
    f["time"] = pd.to_datetime(f.time)
    return f.sort_values("time")


cl = json.loads((O_ / "claims_n1.json").read_text())
fname = cl["final_name"]
fcfg = cl["final_cfg"]
stop_on = fcfg.get("stop", True)
L = pd.read_parquet(DR / f"trades_{fname}.parquet")
L["entry_time"] = pd.to_datetime(L.entry_time)

# ---------------- V1 ----------------
rng = np.random.default_rng(777)
abc = L[L.sleeve.isin(["A", "B", "C"])].reset_index(drop=True)
pick = abc.iloc[rng.choice(len(abc), 300, replace=False)].sort_values("coin")
bad, tfxbad = [], 0
for r in pick.assign(e=pick.e.astype(int), hold=pick.hold.astype(int)).itertuples():
    x = raw5(r.coin)
    b = tfbars(x, r.tf)
    assert b.index[r.e] == r.entry_time
    A = own_atr(b)
    en = float(b.open.values[r.e]); xt = b.index[r.e + r.hold]; xs = float(b.open.values[r.e + r.hold])
    stp = en - r.side * 3.0 * A[r.e - 1]
    h1 = agg(x, x.timestamp.dt.floor("h"))
    seg = h1[(h1.index >= r.entry_time) & (h1.index < xt)]
    X, ext, hit = xs, xt, False
    if stop_on:
        for t, o, hi, lo in zip(seg.index, seg.open.values, seg.high.values, seg.low.values):
            if (r.side == 1 and lo <= stp) or (r.side == -1 and hi >= stp):
                X = min(o, stp) if r.side == 1 else max(o, stp); ext, hit = t, True
                break
    f = funding(r.coin)
    fs = r.side * f.funding_rate[(f.time > r.entry_time) & (f.time <= ext)].sum()
    g = r.side * (X - en) / en
    if not (abs(g - r.gross) < 1e-9 and abs(fs - r.fsum) < 1e-9 and hit == r.stopped and abs(en - r.entry) < 1e-12):
        bad.append(f"{r.sleeve} {r.coin} {r.tf} {r.entry_time} g {g:.6f}/{r.gross:.6f} f {fs:.6f}/{r.fsum:.6f} hit {hit}/{r.stopped}")
    uni = "U1" if r.sleeve in "AB" else "U2"
    tq = pd.read_parquet(R_ / "data" / "derived" / "tf_edge_map" / uni / r.tf / f"{r.coin}.parquet")
    tq = tq[(tq.fam == r.fam) & (tq.side == r.side) & (tq.e == r.e)]
    tfxbad += int(len(tq) != 1 or abs(tq.gross.iloc[0] - r.side * (xs - en) / en) > 1e-12)
ok("V1", not bad and tfxbad == 0, f"300 sub-trades recomputed from raw 5m (own TF bars/ATR/1h stop scan/funding): mismatches {len(bad)} {bad[:2]}; "
                                  f"no-stop gross vs TFX file mismatches {tfxbad}")

# ---------------- own weights ----------------
core = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "DOTUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
cands = sorted({p.name.split("_")[0] for p in HF.glob("*_5m_full.csv.gz")} & {p.name.split("_")[0] for p in (R_ / "data" / "universe_all" / "1h").glob("*_1h_full.csv.gz")}
               & {p.name.split("_")[0] for p in (R_ / "data" / "universe_all" / "1d").glob("*_1d.csv")} & {p.name.split("_")[0] for p in FU.glob("*_funding.csv")}
               & {p.name.split("_")[0] for p in FU.glob("*_perp_1h.csv.gz")})
u2x = [c for c in cands if c not in ("LUNAUSDT", "STRAXUSDT")]


def liq_set(coin):
    v = pd.read_csv(FU / f"{coin}_perp_1h.csv.gz", usecols=["timestamp", "quote_volume"])
    v["d"] = pd.to_datetime(v.timestamp).dt.floor("D")
    dly = v.groupby("d").quote_volume.sum()
    full = dly.reindex(pd.date_range(dly.index.min(), dly.index.max(), freq="D"))
    out = set()
    vals = full.values
    for i in range(1, len(full)):
        w = vals[max(0, i - 30):i]
        w = w[~np.isnan(w)]
        if len(w) >= 20 and np.median(w) >= 50e6:
            out.add(full.index[i])
    return out


liq = {c: liq_set(c) for c in u2x}
nliq = pd.Series({d: n for d, n in pd.Series([d for s in liq.values() for d in s]).value_counts().items()})
ex = L.copy()
w_own = np.where(ex.sleeve == "A", 0.005, np.where(ex.sleeve == "B", 0.4 / 30, np.nan))
cm = ex.sleeve.values == "C"
w_own[cm] = 0.4 / (16 * np.maximum(10, nliq.reindex(ex.entry_time[cm].dt.floor("D")).fillna(0).values))
dm = ex.sleeve.values == "D"
dl = ex[dm].groupby(["entry_time", "side"]).coin.transform("count")
w_own[dm] = 0.2 / dl.values
if fcfg.get("corr") or fcfg.get("vol"):
    cls = {}
    for c in sorted(set(core) | set(u2x)):
        x = raw5(c); cls[c] = agg(x, x.timestamp.dt.floor("D")).close
    R = pd.DataFrame(cls).pct_change(fill_method=None)
    day = ex.entry_time.dt.floor("D")
    if fcfg.get("corr"):
        rc = R[core]; rho = {}
        for i in range(len(rc)):
            wv = rc.iloc[max(0, i - 59):i + 1]
            if len(wv) < 40:
                continue
            m_ = wv.corr(min_periods=40).values[~np.eye(len(core), dtype=bool)]
            m_ = m_[np.isfinite(m_)]
            if len(m_):
                rho[rc.index[i]] = m_.mean()
        rho = pd.Series(rho); ref = rho.expanding(min_periods=180).median()
        mc = np.minimum(1, np.sqrt((1 + 9 * ref) / np.maximum(1 + 9 * rho, 1e-9))).dropna()
        mult = mc.reindex(day - pd.Timedelta(days=1)).fillna(1.0).values
        w_own = np.where(~dm, w_own * mult, w_own)
    if fcfg.get("vol"):
        sg = R.rolling(60, min_periods=40).std().shift(1)
        lm = pd.DataFrame({c: sg.index.isin(liq[c]) for c in u2x}, index=sg.index)
        mcore, mu2 = sg[core].median(axis=1), sg[u2x].where(lm).median(axis=1)
        sc = np.array([sg.at[d, c] if c in sg.columns and d in sg.index else np.nan for d, c in zip(day, ex.coin)])
        md = np.where(ex.sleeve == "C", mu2.reindex(day).values, mcore.reindex(day).values)
        mult = np.where(np.isfinite(sc) & np.isfinite(md) & (sc > 0), np.clip(md / sc, 0.5, 2.0), 1.0)
        w_own = np.where(~dm, w_own * mult, w_own)
if fcfg.get("heat"):
    o = ex[~dm].assign(_t=ex.tf.map({"4h": 0, "8h": 1, "12h": 2, "1D": 3}), _s=ex.sleeve.map({"A": 0, "B": 1, "C": 2}))
    o = o.sort_values(["a", "_s", "coin", "_t", "fam"], kind="mergesort")
    openp = []
    for ix in o.index:
        openp = [(E_, h) for E_, h in openp if E_ > ex.at[ix, "a"]]
        heat = sum(h for _, h in openp)
        hj = w_own[ix] * ex.at[ix, "dist"]
        room = 0.06 - heat
        if room <= 1e-15:
            w_own[ix] = 0.0; continue
        if hj > room:
            w_own[ix] *= room / hj; hj = room
        if hj > 0:
            openp.append((ex.at[ix, "E"], hj))
wdiff = float(np.nanmax(np.abs(w_own - ex.w.values) / np.maximum(ex.w.values, 1e-12)))

# ---------------- V2 ----------------
t0, t1 = pd.Timestamp("2020-02-01"), pd.Timestamp("2025-10-01")
hours = pd.date_range(t0, t1, freq="h", inclusive="left")
H = len(hours)
mstart = np.flatnonzero(np.r_[True, hours.month[1:] != hours.month[:-1]])
ex["m"] = np.searchsorted(mstart, ex.a.values - 0, side="right") - 1
grid0 = pd.Timestamp("2020-02-01")
off = int((t0 - grid0) / pd.Timedelta(hours=1))
tot = np.zeros(H); cst = np.zeros(H + 1)
cf = {}
for c in ex.coin.unique():
    x = raw5(c)
    h1 = agg(x, x.timestamp.dt.floor("h")).close.reindex(hours).ffill().values
    cf[c] = h1
fcache = {c: funding(c) for c in ex.coin.unique()}
dcost = []
dd_ = ex[dm].sort_values("entry_time")
prev = {}
for t, g in dd_.groupby("entry_time"):
    w = {c: s / (g.side == s).sum() for c, s in zip(g.coin, g.side)}
    keys = set(w) | set(prev)
    turn = sum(abs(w.get(k, 0.0) - prev.get(k, 0.0)) for k in keys)
    prev = w
    dcost.append((int(g.a.iloc[0]) - off, 0.2 * 0.00054 * turn))
dcost = pd.DataFrame(dcost, columns=["h", "cost"])
dcm = np.searchsorted(mstart, dcost.h.values, side="right") - 1
for m, s0 in enumerate(mstart):
    Em = E0 + (tot[s0 - 1] + cst[:s0].sum() if s0 > 0 else 0.0)
    for r in ex[(ex.m == m) & (ex.w > 0)].itertuples():
        N = r.w * Em
        a, E = int(r.a) - off, int(r.E) - off
        Ec = min(E, H)
        if Ec > a:
            tot[a:Ec] += r.side * N * (cf[r.coin][a:Ec] - r.entry) / r.entry
        if E < H:
            cst[E] += r.side * N * (r.X - r.entry) / r.entry
        cst[a] -= N * r.fee
        if E < H:
            cst[E] -= N * r.fee * r.X / r.entry
        if not r.nofund:
            f = fcache[r.coin]
            ev = f[(f.time > r.entry_time) & (f.time <= hours[0] + pd.Timedelta(hours=E))]
            for ft, rt in zip(ev.time, ev.funding_rate):
                k = int(np.ceil((ft - hours[0]) / pd.Timedelta(hours=1)))
                if k < H:
                    cst[k] -= r.side * N * rt
    for h, c in zip(dcost.h.values[dcm == m], dcost.cost.values[dcm == m]):
        cst[h] -= c * Em
curve = E0 + tot + np.cumsum(cst[:H])
eq = pd.read_parquet(DR / f"equity_{fname}.parquet").equity.values
run = np.maximum.accumulate(np.r_[E0, curve])
mdd = float((1 - np.r_[E0, curve] / run).max())
fin_rel = abs(curve[-1] - cl["final_dev"]["final"]) / cl["final_dev"]["final"]
ok("V2", fin_rel < 1e-6 and abs(mdd - cl["final_dev"]["mtm_dd"]) < 1e-6 and float(np.abs(curve - eq).max() / E0) < 1e-6 and wdiff < 1e-9,
   f"own event accounting: final {curve[-1]:.2f} vs {cl['final_dev']['final']:.2f} (rel {fin_rel:.1e}); MTM-DD {mdd:.6f} vs {cl['final_dev']['mtm_dd']:.6f}; "
   f"max |curve diff|/E0 {np.abs(curve - eq).max() / E0:.1e}; own weights max rel diff {wdiff:.1e}")

# ---------------- V3 ----------------
d1 = {}
for c in u2x:
    x = raw5(c); d1[c] = agg(x, x.timestamp.dt.floor("D"))
Op = pd.DataFrame({c: d1[c].open for c in u2x}); Cl = pd.DataFrame({c: d1[c].close for c in u2x})
mom = Cl / Cl.shift(20) - 1
hist = Cl.notna().cumsum()
per = list(dd_.groupby("entry_time"))
sel = rng.choice(len(per), min(50, len(per)), replace=False)
bad3 = 0
for k in sel:
    t, g = per[k]
    di = Op.index.get_loc(t) - 1
    el = [c for c in u2x if Op.index[di] in liq[c] and hist[c].iloc[di] >= 25 and np.isfinite(mom[c].iloc[di])
          and np.isfinite(Op[c].iloc[di + 1]) and np.isfinite(Op[c].iloc[di + 6])]
    mv = mom.iloc[di][el].sort_values()
    q = len(mv) // 5
    lg, sh = set(mv.index[-q:]), set(mv.index[:q])
    okk = set(g[g.side == 1].coin) == lg and set(g[g.side == -1].coin) == sh
    okk &= all(abs(Op[c].iloc[di + 1] - e_) < 1e-12 and abs(Op[c].iloc[di + 6] - x_) < 1e-12 for c, e_, x_ in zip(g.coin, g.entry, g.X))
    bad3 += int(not okk)
ok("V3", bad3 == 0, f"{len(sel)} random D rebalances: leg sets / prices from own 1D bars + own liquidity, mismatches {bad3}")

# ---------------- V4 ----------------
Mx = pd.read_csv(O_ / "N1_monthly_dev.csv", index_col=0)
G = pd.read_csv(O_ / "N1_configs.csv")
cal = {(r.config, r.window): r.calmar for r in G.itertuples()}
adopt = {k: all(cal[(k, w)] > cal[("K0", w)] for w in ("dev", "P1", "P2")) for k in ("K1", "K2", "K3", "K4", "K5", "K6")}
cfgs = ["K0", "K1", "K2", "K3", "K4", "K5", "K6"]
blocks = np.array_split(np.arange(len(Mx)), 16)
lg_ = []
for comb in itertools.combinations(range(16), 8):
    i_ = np.concatenate([blocks[i] for i in comb]); o_ = np.concatenate([blocks[i] for i in range(16) if i not in comb])
    X = Mx[cfgs].values
    sri = np.round(X[i_].mean(0) / X[i_].std(0, ddof=1), 12); sro = np.round(X[o_].mean(0) / X[o_].std(0, ddof=1), 12)
    b_ = int(np.argmax(sri))
    rk = (sro < sro[b_]).sum() + 0.5 * ((sro == sro[b_]).sum() - 1) + 1
    wv = rk / (len(cfgs) + 1)
    lg_.append(np.log(wv / (1 - wv)))
pbo_own = float((np.array(lg_) < 0).mean())
fm = Mx[fname].values
srs = [Mx[c].mean() / Mx[c].std(ddof=1) for c in Mx.columns]
srv = float(np.var(srs, ddof=1))
n = 14 + 5 + len(Mx.columns)
sr = fm.mean() / fm.std(ddof=1)
sk = pd.Series(fm).skew(); ku = pd.Series(fm).kurt()
g_ = 0.5772156649
sr0 = np.sqrt(srv) * ((1 - g_) * norm.ppf(1 - 1 / n) + g_ * norm.ppf(1 - 1 / (n * np.e)))
dsr_own = float(norm.cdf((sr - sr0) * np.sqrt(len(fm) - 1) / np.sqrt(1 - sk * sr + (ku + 2) / 4 * sr ** 2)))
bm = np.random.default_rng(20261024).choice(fm, size=(2000, len(fm)), replace=True).mean(axis=1)
ci = (float(np.quantile(bm, .025)), float(np.quantile(bm, .975)))
ok("V4", adopt == cl["adopt"] and abs(pbo_own - cl["pbo"]) < 1e-12 and abs(dsr_own - cl["dsr"]) < 1e-9 and n == cl["n_trials_dsr"]
   and max(abs(ci[0] - cl["boot_ci"][0]), abs(ci[1] - cl["boot_ci"][1])) < 1e-12,
   f"selection {adopt == cl['adopt']}; PBO {pbo_own:.4f}/{cl['pbo']:.4f}; DSR {dsr_own:.4f}/{cl['dsr']:.4f} (N {n}); CI {ci}")

# ---------------- V5 ----------------
proto = O_ / "N1_PROTOCOL_PREREGISTERED.md"
man = DR / "input_manifest_tfx_trades.txt"
mok = all(sha(R_ / l.split("  ", 1)[1]) == l.split("  ", 1)[0] for l in man.read_text(encoding="utf-8").splitlines())
reg = (R_ / "logs" / "r2_4h_a0" / "trial_registry.csv").read_text().splitlines()
t15 = [l.split(",") for l in reg if l.startswith("T15,") and l.split(",")[2] == "N1"]
ok("V5", cl["protocol_sha"] == sha(proto) == (O_ / "N1_PROTOCOL_SHA256.txt").read_text().split()[0] and mok and cl["manifest_sha"] == sha(man)
   and len(t15) == 1 and t15[0][6] == sha(proto) and t15[0][7] == sha(man)
   and all(cl["files"][k] == sha(O_ / k) for k in cl["files"]) and cl["trades_sha"] == sha(DR / f"trades_{fname}.parquet")
   and cl["equity_sha"] == sha(DR / f"equity_{fname}.parquet") and cl["code_sha"] == sha(R_ / "src" / "research" / "n1_portfolio.py"),
   "protocol lock, TFX manifest (every file), registry T15 line, claims file SHAs, code SHA")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
