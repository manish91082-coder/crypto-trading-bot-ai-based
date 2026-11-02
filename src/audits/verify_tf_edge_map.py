"""Independent verifier for TFX (logs/research_tf_edge_map/TFX_PROTOCOL_PREREGISTERED.md). Own code; does not import tf_edge_map.
1 G1: 1m->5m match recomputed for 3 coins x 3 random months
2 300 random trades per universe: own bars, own indicators, own state check (entry bar, flat before, first exit), gross, funding
3 every cell's dev gross mean / net-taker mean / n recomputed from the trade files (1e-12); 2 random cells' excess with own
  random draws (other seed): |study - own| < 3 SE
4 3 TF-stat rows recomputed with own code; G0 re-derived
5 claims / SHAs / protocol lock"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_tf_edge_map"
TR = R_ / "data" / "derived" / "tf_edge_map"
res = []
FAM = ["TSMOM", "EMAX", "MACD", "DONCH", "RSI", "BB"]
H = {"1m": 1 / 60, "5m": 5 / 60, "15m": .25, "30m": .5, "1h": 1, "4h": 4, "8h": 8, "12h": 12, "1D": 24, "1W": 168, "1M": 730.5}
MIN = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "8h": 480, "12h": 720, "1D": 1440}


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def raw5(c):
    x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{c}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
    x["timestamp"] = pd.to_datetime(x["timestamp"]); return x.sort_values("timestamp").reset_index(drop=True)


def own_bars(x, tf):
    t = x.timestamp
    if tf == "5m":
        k = t
    elif tf == "1W":
        k = (t - pd.to_timedelta(t.dt.weekday, unit="D")).dt.normalize()
    elif tf == "1M":
        k = t.dt.to_period("M").dt.to_timestamp()
    else:
        k = t.dt.floor(f"{MIN[tf]}min")
    g = x.groupby(k)
    return pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last()))


def own_ema(v, n):
    a = 2 / (n + 1); out = np.empty(len(v)); s = v[0]
    for i, z in enumerate(v):
        s = z if i == 0 else a * z + (1 - a) * s
        out[i] = s
    return out


def own_conds(b, fam):
    c, hh, ll = b.close.values, b.high.values, b.low.values
    n = len(c)
    if fam == "TSMOM":
        m = np.full(n, np.nan); m[20:] = c[20:] / c[:-20] - 1
        return m > 0, m <= 0, m < 0, m >= 0
    if fam in ("EMAX", "MACD"):
        if fam == "EMAX":
            a, s = own_ema(c, 20), own_ema(c, 50)
        else:
            a = own_ema(c, 12) - own_ema(c, 26); s = own_ema(a, 9)
        return a > s, a <= s, a < s, a >= s
    if fam == "DONCH":
        def roll(v, w, f):
            o = np.full(n, np.nan)
            for i in range(w, n):
                o[i] = f(v[i - w:i])
            return o
        hi20, lo20, hi10, lo10 = roll(hh, 20, np.max), roll(ll, 20, np.min), roll(hh, 10, np.max), roll(ll, 10, np.min)
        return c > hi20, c < lo10, c < lo20, c > hi10
    if fam == "RSI":
        g = np.full(n, np.nan); l_ = np.full(n, np.nan); a = 1 / 14
        for i in range(1, n):
            d = c[i] - c[i - 1]
            gi, li = max(d, 0), max(-d, 0)
            g[i] = gi if i == 1 else a * gi + (1 - a) * g[i - 1]
            l_[i] = li if i == 1 else a * li + (1 - a) * l_[i - 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            r = 100 - 100 / (1 + g / l_)
        return r < 30, r > 50, r > 70, r < 50
    if fam == "BB":
        m = np.full(n, np.nan); s = np.full(n, np.nan)
        for i in range(19, n):
            w = c[i - 19:i + 1]; m[i] = w.mean(); s[i] = w.std(ddof=1)
        return c < m - 2 * s, c >= m, c > m + 2 * s, c <= m


claims = json.loads((O_ / "claims_tfx.json").read_text())
rng = np.random.default_rng(777)

# 1 G1
G = pd.read_csv(O_ / "G1_1m_usability.csv")
g1ok, msg = True, []
for coin in rng.choice(sorted(G.coin.unique()), 3, replace=False):
    x = pd.read_csv(R_ / "archive" / "cleanup_2026_10_15" / "data" / "raw" / f"{coin}_1m_Raw_5Years.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
    x["ts"] = pd.to_datetime(x.timestamp, errors="coerce"); x = x[x.ts.notna()]
    ref = raw5(coin).set_index("timestamp")
    gc = G[(G.coin == coin) & (G.month != "UNPARSEABLE")]
    for m in rng.choice(gc.month.values, 3, replace=False):
        w = x[x.ts.dt.strftime("%Y-%m") == m]
        k = w.groupby(w.ts.dt.floor("5min"))
        a = pd.DataFrame(dict(open=k.open.first(), high=k.high.max(), low=k.low.min(), close=k.close.last(), n=k.open.count()))
        a = a[a.n == 5]; r = ref.reindex(a.index).dropna(); a = a.loc[r.index]
        mm = int((np.abs(a[["open", "high", "low", "close"]].values - r[["open", "high", "low", "close"]].values) > 1e-9 * np.abs(r[["open", "high", "low", "close"]].values)).any(axis=1).sum())
        row = gc[gc.month == m].iloc[0]
        g1ok &= (mm == row.mismatched) and (len(r) == row.compared)
        msg.append(f"{coin} {m}: {mm}/{len(r)} vs {row.mismatched}/{row.compared}")
ok("1", g1ok, "G1 1m->5m recomputed: " + "; ".join(msg))

# 2 trades
fund = {}


def fund_of(c):
    if c not in fund:
        f = pd.read_csv(R_ / "data" / "futures_um" / f"{c}_funding.csv"); f["time"] = pd.to_datetime(f["time"]); fund[c] = f.sort_values("time")
    return fund[c]


u1m = {c: set(g.month[g.usable]) for c, g in G.groupby("coin")}
for uni in ("U1", "U2"):
    files = sorted((TR / uni).glob("*/*.parquet"))
    picks = [files[i] for i in rng.integers(0, len(files), 300)]
    bad, done, cache = [], 0, {}
    for f in picks:
        tf, coin = {"1min": "1m", "1mo": "1M"}.get(f.parent.name, f.parent.name), f.stem
        D = pd.read_parquet(f)
        r = D.iloc[int(rng.integers(0, len(D)))]
        key = (coin, tf)
        if key not in cache:
            if tf == "1m":
                x = pd.read_csv(R_ / "archive" / "cleanup_2026_10_15" / "data" / "raw" / f"{coin}_1m_Raw_5Years.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
                x["timestamp"] = pd.to_datetime(x.timestamp, errors="coerce"); x = x[x.timestamp.notna()]
                x = x[x.timestamp.dt.strftime("%Y-%m").isin(u1m[coin])].sort_values("timestamp")
                b = x.set_index("timestamp")[["open", "high", "low", "close"]]
            else:
                b = own_bars(raw5(coin), tf)
            cache = {key: b}
        b = cache[key]
        fam = FAM[int(r.fam)]
        le, lx, se, sx = own_conds(b, fam)
        en, ex = (le, lx) if r.side == 1 else (se, sx)
        t, e, x_ = int(r.e) - 1, int(r.e), int(r.x)
        o = b.open.values
        cond_entry = bool(en[t])
        ev = np.flatnonzero(en[:t] | ex[:t])
        flat_before = len(ev) == 0 or bool(ex[ev[-1]])
        u = t + np.flatnonzero(ex[t:])
        first_exit = len(u) > 0 and u[0] + 1 == x_
        g = r.side * (o[x_] - o[e]) / o[e]
        ts = b.index
        same_t = ts[e] == r.entry_time
        ff = fund_of(coin)
        fs = r.side * ff[(ff.time > ts[e]) & (ff.time <= ts[x_])].funding_rate.sum()
        fok = np.isnan(r.fund) and ts[e] < ff.time.iloc[0] or abs(fs - r.fund) < 1e-12
        good = cond_entry and flat_before and first_exit and abs(g - r.gross) < 1e-12 and same_t and fok
        done += 1
        if not good:
            bad.append(f"{coin} {tf} {fam} {r.side} e{e}: entry {cond_entry} flat {flat_before} exit {first_exit} g {abs(g - r.gross):.1e} fund {fok}")
    ok(f"2-{uni}", not bad, f"{done} random {uni} trades rebuilt with own bars/indicators/state/funding; mismatches {len(bad)} {bad[:5]}")

# 3 cells from trade files
C = pd.read_csv(O_ / "TFX_cells.csv")
mx, nbad = 0.0, 0
for uni in ("U1", "U2"):
    for tfdir in sorted((TR / uni).iterdir()):
        files = sorted(tfdir.glob("*.parquet"))
        for fi in range(6):
            D = pd.concat([pd.read_parquet(f, columns=["fam", "side", "gross", "fund", "period"], filters=[("fam", "==", fi)]) for f in files])
            for side, g in D[D.period < 2].groupby("side"):
                row = C[(C.uni == uni) & (C.tf == {"1min": "1m", "1mo": "1M"}.get(tfdir.name, tfdir.name)) & (C.family == FAM[fi]) & (C.side == ("long" if side == 1 else "short"))]
                if len(row) != 1 or row.n_dev.iloc[0] != len(g):
                    nbad += 1; continue
                if len(g) >= 30:
                    nt = (g.gross - 0.00108 - g.fund).dropna()
                    mx = max(mx, abs(g.gross.mean() - row.gross_mean.iloc[0]), abs(nt.mean() - row.net_taker_dev.iloc[0]))
ok("3a", nbad == 0 and mx < 1e-12, f"all cells: n_dev, gross mean, net-taker mean recomputed from trade files: n mismatches {nbad}, max |diff| {mx:.1e}")
cc = C[(C.n_dev >= 300) & (C.tf != "1m")].sample(2, random_state=5)
msg, good = [], True
for r in cc.itertuples():
    files = sorted((TR / r.uni / {"1m": "1min", "1M": "1mo"}.get(r.tf, r.tf)).glob("*.parquet"))
    fi = FAM.index(r.family); sd = 1 if r.side == "long" else -1
    ex = []
    r2 = np.random.default_rng(99)
    for f in files:
        D = pd.read_parquet(f); D = D[(D.fam == fi) & (D.side == sd) & (D.period < 2)]
        if not len(D):
            continue
        b = own_bars(raw5(f.stem), r.tf)
        o = b.open.values; n = len(o); ft = b.index
        el = (ft >= "2020-02-01") & (ft < "2026-10-01")
        if r.uni == "U2":
            v = pd.read_csv(R_ / "data" / "futures_um" / f"{f.stem}_perp_1h.csv.gz", usecols=["timestamp", "quote_volume"])
            v["d"] = pd.to_datetime(v.timestamp).dt.floor("D"); dv = v.groupby("d").quote_volume.sum()
            days = pd.date_range(dv.index.min(), dv.index.max(), freq="D")
            liq = {d for d in days if (lambda w: len(w) >= 20 and w.median() >= 50e6)(dv[(dv.index >= d - pd.Timedelta(days=30)) & (dv.index < d)])}
            el &= np.array([d in liq for d in ft.floor("D")])
        per = np.where(ft < "2024-01-01", 0, np.where(ft < "2025-10-01", 1, 2))
        for q in D.itertuples():
            pool = np.flatnonzero(el & (per == q.period) & (np.arange(n) + q.hold < n))
            j = pool[r2.integers(0, len(pool), 20)]
            ctrl = (sd * (o[j + q.hold] - o[j]) / o[j]).mean()
            ex.append(q.gross - ctrl)
    ex = np.array(ex)
    se = ex.std(ddof=1) / np.sqrt(len(ex)) if len(ex) > 1 else np.inf
    d = abs(ex.mean() - r.excess_mean)
    good &= d < 3 * se
    msg.append(f"{r.uni} {r.tf} {r.family} {r.side}: study {r.excess_mean:.6f} own {ex.mean():.6f} (3SE {3 * se:.6f})")
ok("3b", good, "excess with own random draws: " + "; ".join(msg))

# 4 TF stats
S = pd.read_csv(O_ / "TF_stats.csv")
mx = 0.0
for r in S.sample(3, random_state=3).itertuples():
    x = raw5(r.coin); x = x[(x.timestamp >= "2020-01-01") & (x.timestamp < "2026-10-01")]
    b = own_bars(x, r.tf)
    ret = b.close.pct_change().dropna().values
    ac = np.corrcoef(ret[1:], ret[:-1])[0, 1]
    q4 = (b.close / b.close.shift(4) - 1).var() / (4 * b.close.pct_change().var())
    body = float(np.median(np.abs(b.close - b.open) / b.open)) * 100
    mx = max(mx, abs(ac - r.ac1), abs(q4 - r.vr4), abs(body - r.body), abs(len(b) - r.bars))
ok("4a", mx < 1e-9, f"3 TF-stat rows recomputed with own code: max |diff| {mx:.1e}")
G0 = pd.read_csv(O_ / "G0_part3_replication.csv")
ok("4b", int(G0.match.sum()) == claims["g0_values_matched"] and len(G0) == claims["g0_values"],
   f"G0 replication file consistent with claims: {int(G0.match.sum())}/{len(G0)} Part 3 values matched")

# 5 claims
c5 = (claims["protocol_sha"] == sha(O_ / "TFX_PROTOCOL_PREREGISTERED.md") == (O_ / "TFX_PROTOCOL_SHA256.txt").read_text().split()[0]
      and claims["cells_sha"] == sha(O_ / "TFX_cells.csv") and claims["stats_sha"] == sha(O_ / "TF_stats.csv")
      and claims["g1_sha"] == sha(O_ / "G1_1m_usability.csv") and claims["code_sha"] == sha(R_ / "src" / "research" / "tf_edge_map.py"))
ok("5", c5, "claims / SHAs / protocol lock consistent")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
