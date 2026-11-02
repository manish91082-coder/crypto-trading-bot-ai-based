"""Independent verifier for DISC (logs/research_tf_edge_map/DISC_PROTOCOL_PREREGISTERED.md). Own code; imports neither
tf_edge_map nor disc_study.
1 D1: two U1 coins' carry daily P&L and on/off states (1e-12)
2 D2: 300 random new-family trades: own indicators, entry condition, flat-before, first exit, gross, funding
3 D3: 100 random trades: signal (own percentile), exit = entry+5, gross, funding
4 D4: 3 random 1D rebalances: ranks, legs, period return
5 D5: own joint month bootstrap -> p-values within +-0.02, same reading
6 D6: windows recomputed (8 largest non-overlapping 7-day BTC declines)
7 SHAs / protocol lock"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_tf_edge_map"
D_ = O_ / "disc"
T_ = R_ / "data" / "derived" / "disc_trades"
CORE = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "DOTUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
RULE = {"15m": "15min", "1h": "1h", "4h": "4h", "8h": "8h", "12h": "12h", "1D": "1D"}
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def spot5(c, vol=False):
    cols = ["timestamp", "open", "high", "low", "close"] + (["volume"] if vol else [])
    x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{c}_5m_full.csv.gz", usecols=cols)
    x["timestamp"] = pd.to_datetime(x.timestamp); return x.sort_values("timestamp")


def fund(c):
    f = pd.read_csv(R_ / "data" / "futures_um" / f"{c}_funding.csv"); f["time"] = pd.to_datetime(f["time"]); return f.sort_values("time")


cl = json.loads((D_ / "claims_disc.json").read_text())
rng = np.random.default_rng(31337)

# 1 D1
daily = pd.read_csv(D_ / "D1_carry_daily.csv", index_col=0, parse_dates=True)
mx, msg = 0.0, []
per = {}
for c in CORE:
    s = spot5(c); sc = s.groupby(s.timestamp.dt.floor("D")).close.last()
    p = pd.read_csv(R_ / "data" / "futures_um" / f"{c}_perp_1h.csv.gz", usecols=["timestamp", "close"]); p["timestamp"] = pd.to_datetime(p.timestamp)
    pc = p.groupby(p.timestamp.dt.floor("D")).close.last()
    f = fund(c)
    idx = sc.index.intersection(pc.index); idx = idx[(idx >= "2020-02-01") & (idx < "2026-10-01")]
    rs, rp = sc.reindex(idx).pct_change().fillna(0), pc.reindex(idx).pct_change().fillna(0)
    rows = []
    sb = False
    first = f.time.iloc[0].floor("D") + pd.Timedelta(days=1)
    prev_on = False
    prev_t7 = np.nan
    for d in idx:
        fd = f[(f.time > d) & (f.time <= d + pd.Timedelta(days=1))].funding_rate.sum()
        w = f[(f.time > d - pd.Timedelta(days=7) + pd.Timedelta(days=1) - pd.Timedelta(days=1)) & (f.time <= d)]
        elig = d >= first
        if not elig:
            sb = False
        elif np.isfinite(prev_t7):
            sb = True if prev_t7 > 0.0001 else (False if prev_t7 <= 0 else sb)
        on = sb
        pnl = (fd + rs[d] - rp[d] if on else 0.0) - (0.00139 if on != prev_on else 0.0)
        rows.append((d, on, pnl)); prev_on = on
        w7 = f[(f.time > d + pd.Timedelta(days=1) - pd.Timedelta(days=7)) & (f.time <= d + pd.Timedelta(days=1))].funding_rate
        prev_t7 = w7.mean() if len(w7) else np.nan
    per[c] = pd.DataFrame(rows, columns=["d", "on", "pnl"]).set_index("d")
P = pd.DataFrame({c: v.pnl for c, v in per.items()}); Onn = pd.DataFrame({c: v.on for c, v in per.items()}).fillna(False)
mine = (P.fillna(0).sum(axis=1) / Onn.sum(axis=1).replace(0, np.nan)).fillna(0.0)
mx = float((mine - daily["U1_b"].reindex(mine.index)).abs().max())
ok("1", mx < 1e-12, f"D1 U1 carry (variant b) daily portfolio rebuilt with own loop for 10 coins: max |diff| {mx:.1e}")

# 2 D2
D2 = pd.read_parquet(T_ / "D2_trades_U1.parquet")


def wl(x, n):
    a = 1 / n; o = np.empty(len(x)); s = np.nan
    for i, v in enumerate(x):
        if np.isnan(v):
            o[i] = s; continue
        s = v if np.isnan(s) else a * v + (1 - a) * s
        o[i] = s
    return o


def own(b, fam):
    c, h, l, v = b.close.values, b.high.values, b.low.values, b.volume.values
    n = len(c)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    roll = lambda x, w, f: np.array([f(x[i - w + 1:i + 1]) if i >= w - 1 else np.nan for i in range(n)])
    if fam == "SUPERT":
        atr = wl(tr, 10); hl2 = (h + l) / 2; up, lo = hl2 + 3 * atr, hl2 - 3 * atr
        fu, fl, d = up.copy(), lo.copy(), np.zeros(n)
        for i in range(1, n):
            fu[i] = up[i] if (up[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
            fl[i] = lo[i] if (lo[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
            d[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else d[i - 1])
        d[:10] = 0
        return d == 1, d == -1, d == -1, d == 1
    if fam == "ICHI":
        t = (roll(h, 9, np.max) + roll(l, 9, np.min)) / 2; k = (roll(h, 26, np.max) + roll(l, 26, np.min)) / 2
        return t > k, t <= k, t < k, t >= k
    if fam == "ADXDI":
        upm, dnm = np.r_[np.nan, np.diff(h)], -np.r_[np.nan, np.diff(l)]
        pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0); mdm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
        atr = wl(tr, 14)
        pdi, mdi = 100 * wl(pdm, 14) / atr, 100 * wl(mdm, 14) / atr
        with np.errstate(invalid="ignore", divide="ignore"):
            adx = wl(100 * np.abs(pdi - mdi) / (pdi + mdi), 14)
        return (adx > 25) & (pdi > mdi), (adx < 20) | (pdi <= mdi), (adx > 25) & (mdi > pdi), (adx < 20) | (mdi <= pdi)
    if fam == "STOCH":
        lo14, hi14 = roll(l, 14, np.min), roll(h, 14, np.max)
        raw = 100 * (c - lo14) / (hi14 - lo14)
        k = np.array([raw[i - 2:i + 1].mean() if i >= 2 else np.nan for i in range(n)])
        return k < 20, k > 50, k > 80, k < 50
    if fam == "KSQZ":
        m = roll(c, 20, np.mean); s = roll(c, 20, lambda w: w.std(ddof=1))
        bu, bl = m + 2 * s, m - 2 * s
        a2 = 2 / 21; e = np.empty(n); e[0] = c[0]
        for i in range(1, n):
            e[i] = a2 * c[i] + (1 - a2) * e[i - 1]
        at = roll(tr, 20, np.mean)
        sq = (bu < e + 1.5 * at) & (bl > e - 1.5 * at)
        rel = np.r_[False, sq[:-1]] & ~sq
        return rel & (c > bu), c < m, rel & (c < bl), c > m
    if fam == "VWAP20":
        tp = (h + l + c) / 3
        vw = roll(tp * v, 20, np.sum) / roll(v, 20, np.sum)
        return c > vw, c <= vw, c < vw, c >= vw
    if fam == "OBV":
        obv = np.cumsum(np.r_[0.0, np.sign(np.diff(c))] * v)
        a2 = 2 / 21; e = np.empty(n); e[0] = obv[0]
        for i in range(1, n):
            e[i] = a2 * obv[i] + (1 - a2) * e[i - 1]
        return obv > e, obv <= e, obv < e, obv >= e


bad, cache = [], {}
pick = D2.sample(300, random_state=21)
for r in pick.sort_values(["coin", "tf"]).itertuples():
    key = (r.coin, r.tf)
    if key not in cache:
        x = spot5(r.coin, True)
        g = x.set_index("timestamp")
        b = g.resample(RULE[r.tf], label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
        cache = {key: (b, {})}
    b, cc = cache[key]
    if r.fam not in cc:
        cc[r.fam] = own(b, r.fam)
    le, lx, se, sx = cc[r.fam]
    en, ex = (le, lx) if r.side == 1 else (se, sx)
    t, e, x_ = r.e - 1, r.e, r.x
    evs = np.flatnonzero(np.asarray(en[:t]) | np.asarray(ex[:t]))
    flat = len(evs) == 0 or bool(ex[evs[-1]])
    u = t + np.flatnonzero(np.asarray(ex[t:]))
    first = len(u) > 0 and u[0] + 1 == x_
    o = b.open.values
    g_ = r.side * (o[x_] - o[e]) / o[e]
    ff = fund(r.coin); fs = r.side * ff[(ff.time > b.index[e]) & (ff.time <= b.index[x_])].funding_rate.sum()
    fok = (np.isnan(r.fund) and b.index[e] < ff.time.iloc[0]) or abs(fs - r.fund) < 1e-12
    if not (bool(en[t]) and flat and first and abs(g_ - r.gross) < 1e-12 and fok):
        bad.append(f"{r.coin} {r.tf} {r.fam} {r.side} e{e}: entry {bool(en[t])} flat {flat} exit {first} g {abs(g_ - r.gross):.1e} f {fok}")
ok("2", not bad, f"D2: 300 random new-family trades rebuilt with own indicator code: mismatches {len(bad)} {bad[:4]}")

# 3 D3
D3 = pd.read_parquet(T_ / "D3_trades.parquet")
bad3 = []
for r in D3.sample(100, random_state=22).itertuples():
    p = pd.read_csv(R_ / "data" / "futures_um" / f"{r.coin}_perp_1h.csv.gz", usecols=["timestamp", "open", "close"]); p["timestamp"] = pd.to_datetime(p.timestamp)
    db = p.groupby(p.timestamp.dt.floor("D")).agg(open=("open", "first"), close=("close", "last"))
    o = db.open.values
    g_ = r.side * (o[r.x] - o[r.e]) / o[r.e]
    ff = fund(r.coin); fs = r.side * ff[(ff.time > db.index[r.e]) & (ff.time <= db.index[r.x])].funding_rate.sum()
    sday = db.index[r.e - 1]
    if r.rule == "OITR":
        met = pd.read_csv(R_ / "data" / "futures_info" / f"{r.coin}_metrics_daily.csv", parse_dates=["date"]).set_index("date")
        r7 = db.close.iloc[r.e - 1] / db.close.iloc[r.e - 8] - 1
        oi = met.oi_value.reindex(db.index)
        oi7 = oi.iloc[r.e - 1] / oi.iloc[r.e - 8] - 1
        sig = (r7 > 0 and oi7 > 0) if r.side == 1 else (r7 < 0 and oi7 < 0)
    else:
        if r.rule == "FUNDX":
            ser = ff.set_index("time").funding_rate.resample("1D").mean().reindex(db.index).rolling(3, min_periods=3).mean()
        elif r.rule == "PREMX":
            ser = pd.read_csv(R_ / "data" / "futures_info" / f"{r.coin}_premium_1d.csv", parse_dates=["timestamp"]).set_index("timestamp").prem_close.reindex(db.index)
        else:
            met = pd.read_csv(R_ / "data" / "futures_info" / f"{r.coin}_metrics_daily.csv", parse_dates=["date"]).set_index("date")
            ser = met["global_ls" if r.rule == "LSCON" else "top_ls_pos"].reindex(db.index)
        w = ser.iloc[max(0, r.e - 1 - 364):r.e].values
        cur = w[-1]; hist = w[:-1]
        q = (hist < cur).mean() + 0.5 * (hist == cur).mean() if len(w) >= 180 and np.isfinite(cur) else np.nan
        sig = (q <= 0.10) if r.side == 1 else (q >= 0.90)
    if not (sig and r.x == r.e + 5 and abs(g_ - r.gross) < 1e-12 and abs(fs - r.fund) < 1e-12):
        bad3.append(f"{r.coin} {r.rule} {r.side} e{r.e}: sig {sig} g {abs(g_ - r.gross):.1e} f {abs(fs - r.fund):.1e}")
ok("3", not bad3, f"D3: 100 random derivative-rule trades recomputed (own percentile, prices, funding): mismatches {len(bad3)} {bad3[:4]}")

# 4 D4 (own rebuild of 3 random 1D rebalances: eligibility, ranks, quintile legs, leg returns)
sys.path.insert(0, str(R_ / "src" / "research"))
import r2_t14_universe as U                                    # candidate list only (data-file intersection)
coins = [c for c in U.candidates() if (R_ / "data" / "universe_hf" / "5m" / f"{c}_5m_full.csv.gz").exists() and c not in ("LUNAUSDT", "STRAXUSDT")]
Op, Cl, LQ = {}, {}, {}
for c in coins:
    x = spot5(c); g = x.groupby(x.timestamp.dt.floor("D"))
    Op[c], Cl[c] = g.open.first(), g.close.last()
    v = pd.read_csv(R_ / "data" / "futures_um" / f"{c}_perp_1h.csv.gz", usecols=["timestamp", "quote_volume"]); v["timestamp"] = pd.to_datetime(v.timestamp)
    dv = v.groupby(v.timestamp.dt.floor("D")).quote_volume.sum()
    full = dv.reindex(pd.date_range(dv.index.min(), dv.index.max(), freq="D"))
    med = full.rolling(30, min_periods=20).median().shift(1)
    LQ[c] = set(med[med >= 50e6].index)
Op, Cl = pd.DataFrame(Op), pd.DataFrame(Cl)
idx = Op.index.union(Cl.index); Op, Cl = Op.reindex(idx), Cl.reindex(idx)
hist = Cl.notna().cumsum(); mom = Cl / Cl.shift(20) - 1
Rp = pd.read_csv(D_ / "D4_periods_1D.csv", parse_dates=["t"])
bad4 = []
for r in Rp.sample(3, random_state=23).itertuples():
    t = idx.get_loc(r.t) - 6
    el = pd.Series({c: (idx[t].floor("D") in LQ[c]) and hist[c].iloc[t] >= 25 and np.isfinite(mom[c].iloc[t]) and np.isfinite(Op[c].iloc[t + 1]) and np.isfinite(Op[c].iloc[t + 6]) for c in coins})
    m_ = mom.iloc[t][el[el].index].sort_values()
    q = len(m_) // 5
    lg, sh = m_.index[-q:], m_.index[:q]
    rr = Op.iloc[t + 6] / Op.iloc[t + 1] - 1
    if not (len(m_) == r.n and abs(rr[lg].mean() - r.long) < 1e-12 and abs(-rr[sh].mean() - r.short) < 1e-12):
        bad4.append(f"{r.t.date()}: n {len(m_)} vs {r.n}, long {rr[lg].mean():.6f} vs {r.long:.6f}")
ok("4", not bad4, f"D4: 3 random 1D rebalances rebuilt (own liquidity, ranks, legs): mismatches {bad4}")

# 5 D5 (own joint month bootstrap, U1, both statistics; 4,000 draws)
FAM = ["TSMOM", "EMAX", "MACD", "DONCH", "RSI", "BB"]
DEVM = [str(p) for p in pd.period_range("2020-02", "2025-09", freq="M")]
S5 = pd.read_csv(D_ / "D5_rc_spa.csv")
TR6 = R_ / "data" / "derived" / "tf_edge_map" / "U1"
cells = {"excess": [], "net_taker": []}
for d in sorted(TR6.iterdir()):
    A = pd.concat([pd.read_parquet(f, columns=["fam", "side", "period", "entry_time", "gross", "ctrl", "fund"]) for f in d.glob("*.parquet")])
    A = A[A.period < 2]; A["m"] = pd.to_datetime(A.entry_time).dt.strftime("%Y-%m")
    for (fi, sd), g in A.groupby(["fam", "side"]):
        if len(g) < 30:
            continue
        for st, v in (("excess", g.gross - g.ctrl), ("net_taker", g.gross - 0.00108 - g.fund)):
            k = v.notna().values
            agg = pd.DataFrame(dict(m=g.m.values[k], v=v.values[k])).groupby("m").v.agg(["sum", "count"]).reindex(DEVM).fillna(0.0)
            cells[st].append((agg["sum"].values, agg["count"].values))
r5 = np.random.default_rng(777)
nm = len(DEVM); Wm = r5.multinomial(nm, np.full(nm, 1 / nm), size=4000).astype(float)
thr = -np.sqrt(2 * np.log(np.log(nm)))
msg5, good5 = [], True
for st in ("excess", "net_taker"):
    Sm = np.array([a for a, b in cells[st]]); Nm = np.array([b for a, b in cells[st]])
    m = Sm.sum(1) / Nm.sum(1); mb = (Wm @ Sm.T) / np.maximum(Wm @ Nm.T, 1); se = mb.std(axis=0, ddof=1)
    T = m / se; Tm = max(T.max(), 0.0)
    prc = ((mb - m) / se).max(axis=1); pspa = ((mb - m + np.where(T <= thr, m, 0.0)) / se).max(axis=1)
    p_rc, p_spa = float((prc >= Tm).mean()), float((np.maximum(pspa, 0) >= Tm).mean())
    row = S5[(S5.uni == "U1") & (S5.stat == st)].iloc[0]
    good5 &= len(Sm) == row.n_cells and abs(p_rc - row.p_RC) <= 0.02 and abs(p_spa - row.p_SPA) <= 0.02 and ((p_spa < 0.05) == (row.p_SPA < 0.05))
    msg5.append(f"U1 {st}: n {len(Sm)}/{row.n_cells}, RC {p_rc:.3f} vs {row.p_RC:.3f}, SPA {p_spa:.3f} vs {row.p_SPA:.3f}")
ok("5", good5, "D5 own joint bootstrap (4,000 draws): " + "; ".join(msg5))

# 6 D6
x = spot5("BTCUSDT"); bc = x.groupby(x.timestamp.dt.floor("D")).close.last()
bc = bc[(bc.index >= "2020-02-01") & (bc.index < "2026-10-01")]
r7 = (bc / bc.shift(7) - 1).dropna().sort_values()
wins = []
for d, v in r7.items():
    s = d - pd.Timedelta(days=7)
    if all(d <= a or s >= b for a, b, _ in wins):
        wins.append((s, d, v))
    if len(wins) == 8:
        break
W = pd.read_csv(D_ / "D6_crisis.csv")
ok("6", [str(w[1].date()) for w in wins] == list(W.end.astype(str)) and np.allclose([w[2] for w in wins], W.btc_7d, atol=1e-12),
   f"D6 windows recomputed: {[str(w[1].date()) for w in wins]}")

# 7
c7 = cl["protocol_sha"] == sha(O_ / "DISC_PROTOCOL_PREREGISTERED.md") == (O_ / "DISC_PROTOCOL_SHA256.txt").read_text().split()[0] \
     and all(cl["files"][f.name] == sha(f) for f in D_.glob("*.csv") if f.name in cl["files"]) \
     and cl["d2_trades_sha"] == sha(T_ / "D2_trades_U1.parquet") and cl["d3_trades_sha"] == sha(T_ / "D3_trades.parquet") \
     and cl["code_sha"] == sha(R_ / "src" / "research" / "disc_study.py")
ok("7", c7, "claims / SHAs / protocol lock consistent")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
