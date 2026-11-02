"""Independent verifier for A4 (logs/r2_4h_a4/A4_PROTOCOL_PREREGISTERED.md). Own code; does not import the A4 module.
1 200 random S-LAD long trades x 3 exit configs re-simulated (exit idx, gross, fee) with an own bar loop
2 exit grid mean net R recomputed (own sims for all 6 configs) and the plateau selection re-derived from A4_exit_grid.csv
3 PBO recomputed with own CSCV code from own monthly returns? -> recomputed from the grid's Calmar inputs is not enough, so the
  verifier rebuilds the 6 configs' dev MTM monthly returns with its own portfolio loop and recomputes PBO
4 own MTM portfolio for the final config: final equity and MTM DD == claims (1e-6)
5 claims / SHAs
"""
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
A4 = R_ / "logs" / "r2_4h_a4"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


t = pd.read_parquet(R_ / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet")
t = t[(t.signal == "S-LAD") & (t.side == "long") & t.perp_ok].sort_values(["entry_time", "coin"]).reset_index(drop=True)
bars = {}
for c in t.coin.unique():
    x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{c}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
    x["timestamp"] = pd.to_datetime(x["timestamp"]); x = x.set_index("timestamp").sort_index()
    g = x.groupby(x.index.floor("4h"))
    bars[c] = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last())).dropna()
fund = {}
for c in t.coin.unique():
    f = pd.read_csv(R_ / "data" / "futures_um" / f"{c}_funding.csv"); f["time"] = pd.to_datetime(f["time"]); fund[c] = f


def sim(r, k, tmax):
    b = bars[r.coin]
    e = b.index.get_loc(r.entry_time)
    o, h, l, c = b.open.values, b.high.values, b.low.values, b.close.values
    stop0 = r.entry_px - r.R_price
    best = -np.inf
    n = min(tmax, len(o) - e)
    for j in range(n):
        if j > 0:
            best = max(best, h[e + j - 1])
        tr = max(stop0, best - k * r.atr)
        if l[e + j] <= tr:
            return j, min(o[e + j], tr)
    return n - 1, c[e + n - 1]


def net_of(r, j, px):
    E = r.entry_px; R = r.R_price
    ff = fund[r.coin]
    end = r.entry_time + pd.Timedelta(hours=4) * (j + 1)
    fr = ff[(ff.time > r.entry_time) & (ff.time < end)].funding_rate.sum() * E / R
    return (px - E) / R - 0.00054 * (E + px) / R - fr


claims = json.loads((A4 / "claims_a4.json").read_text())
G = pd.read_csv(A4 / "A4_exit_grid.csv")
# 1 + 2: own sims for all 6 configs
own = {}
for k, tm in [(3, 60), (3, 120), (3, 1000), (4, 60), (4, 120), (4, 1000)]:
    rows = []
    for r in t.itertuples():
        j, px = sim(r, k, tm)
        rows.append(dict(coin=r.coin, entry_time=r.entry_time, j=j, px=px, net=net_of(r, j, px), E=r.entry_px, R=r.R_price))
    own[(k, tm)] = pd.DataFrame(rows)
dev_mean = {kt: d[d.entry_time < "2025-10-01"].net.mean() for kt, d in own.items()}
c2 = all(abs(dev_mean[(r.trail, r.tstop)] - r.mean_net) < 1e-9 for r in G.itertuples())
ok("1-2", c2, "6 exit configs re-simulated with own loop: dev mean net R equal to A4_exit_grid.csv for all 6: "
              + str({f'{k}_{tm}': round(v, 4) for (k, tm), v in dev_mean.items()}))
cal = {(r.trail, r.tstop): r.calmar for r in G.itertuples()}
best = max(cal, key=cal.get); tms = [60, 120, 1000]
nb = [(best[0], tms[j]) for j in (tms.index(best[1]) - 1, tms.index(best[1]) + 1) if 0 <= j < 3] + [(7 - best[0], best[1])]
sel = best if all(cal[n] >= 0.8 * cal[best] for n in nb) else (3, 60)
ok("2b", list(sel) == claims["selected_exit"], f"plateau rule re-derived: best {best}, neighbours {[round(cal[n] / cal[best], 3) for n in nb]} -> selected {sel}")


def port(d, k_t, t0="2020-02-01", t1="2025-10-01"):
    t0, t1 = pd.Timestamp(t0), pd.Timestamp(t1)
    d = d[(d.entry_time >= t0) & (d.entry_time < t1)].sort_values(["entry_time", "coin"])
    by = {}
    for i in d.index:
        by.setdefault(d.at[i, "entry_time"], []).append(i)
    E, op, cur, idx = 8000.0, [], [], []
    for ts in pd.date_range(t0, t1 - pd.Timedelta(hours=4), freq="4h"):
        for o in [o for o in op if o["end"] <= ts]:
            E += o["pnl"]; op.remove(o)
        for i in by.get(ts, []):
            r = d.loc[i]
            if any(o["coin"] == r.coin for o in op) or len(op) >= 6:
                continue
            N = 0.005 * E / (r.R / r.E + 0.0109)
            if sum(o["N"] for o in op) + N > 3 * E or N < {"BTCUSDT": 50, "ETHUSDT": 20, "LINKUSDT": 20}.get(r.coin, 5) or \
                    (r.coin == "BTCUSDT" and N / r.E < 0.001):
                continue
            op.append(dict(coin=r.coin, N=N, pnl=N * r.net * r.R / r.E, end=r.entry_time + pd.Timedelta(hours=4) * (r.j + 1),
                           st=r.entry_time, j=r.j, px=r.px, E0=r.E))
        u = 0.0
        for o in op:
            kb = int((ts - o["st"]) / pd.Timedelta(hours=4))
            # bar-index convention (as S6 / A1 / A4): the k-th bar after entry, not the timestamp; differs only on the single
            # missing 4h bar (2020-02-19 16:00 UTC, Binance outage), which 1 S-LAD long trade (ETH) spans
            bb = bars[o["coin"]]
            v = o["px"] if kb == o["j"] else bb.low.values[bb.index.get_loc(o["st"]) + kb]
            u += o["N"] * (v - o["E0"]) / o["E0"]
        cur.append(E + u); idx.append(ts)
    for o in op:
        E += o["pnl"]
    cur.append(E); idx.append(t1)
    eq = pd.Series(cur, index=idx)
    return E, float((1 - eq / eq.cummax()).max()), eq.resample("MS").last().pct_change().dropna()


M, fin, fdiff = {}, None, {}
for kt, d in own.items():
    E_, dd, mon = port(d, kt)
    M[f"{kt[0]}_{kt[1]}"] = mon
    gf = G[(G.trail == kt[0]) & (G.tstop == kt[1])].iloc[0]
    fdiff[f"{kt[0]}_{kt[1]}"] = (round(E_ - gf.final, 6), round(dd - gf.mtm_dd, 8))
    if list(kt) == claims["selected_exit"]:
        fin = (E_, dd)
M = pd.DataFrame(M).dropna()
M.to_csv(A4 / "verify_monthly_matrix.csv")
blocks = np.array_split(np.arange(len(M)), 16)
lg = []
for comb in itertools.combinations(range(16), 8):
    a = np.concatenate([blocks[i] for i in comb]); b = np.concatenate([blocks[i] for i in range(16) if i not in comb])
    s_is = (M.iloc[a].mean() / M.iloc[a].std(ddof=1)).round(12); s_oos = (M.iloc[b].mean() / M.iloc[b].std(ddof=1)).round(12)
    w = s_oos.rank()[s_is.idxmax()] / (M.shape[1] + 1)
    lg.append(np.log(w / (1 - w)))
pbo = float((np.array(lg) < 0).mean())
print("   per-config (final diff, MTM-DD diff) own vs A4_exit_grid.csv:", fdiff, flush=True)
ok("3a", all(abs(a) < 1e-6 and abs(b) < 1e-6 for a, b in fdiff.values()), "all 6 exit-config portfolios (final, MTM DD) == A4_exit_grid.csv")
ok("3", abs(pbo - claims["pbo"]) < 1e-9, f"PBO recomputed with own portfolio + CSCV: {pbo:.4f} vs claims {claims['pbo']:.4f}")
if claims["entry_final"] == "V0 taker":
    ok("4", abs(fin[0] - claims["final"]["final"]) < 1e-6 and abs(fin[1] - claims["final"]["mtm_dd"]) < 1e-6,
       f"own MTM portfolio for the final config: {fin[0]:.2f} / DD {fin[1]:.4f} == claims")
elif claims["entry_final"] == "maker":
    k, tm = claims["selected_exit"]
    rows, nf = [], 0
    for c, g in t.groupby("coin"):
        x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{c}_5m_full.csv.gz", usecols=["timestamp", "low", "close"])
        x["timestamp"] = pd.to_datetime(x["timestamp"]); x = x.set_index("timestamp").sort_index()
        for r in g.itertuples():
            w = x[(x.index >= r.entry_time) & (x.index < r.entry_time + pd.Timedelta(hours=1))]
            lim = float(bars[c].open.loc[r.entry_time])
            filled = bool((w.low.values < lim).any())
            E = lim if filled else float(w.close.values[-1])
            nf += filled
            stop0 = r.entry_px - r.R_price
            R = E - stop0
            j, px = sim(r, k, tm)
            ff = fund[c]
            end = r.entry_time + pd.Timedelta(hours=4) * (j + 1)
            fr = ff[(ff.time > r.entry_time) & (ff.time < end)].funding_rate.sum() * E / R
            net = (px - E) / R - ((0.00018 if filled else 0.00054) * E + 0.00054 * px) / R - fr
            rows.append(dict(coin=c, entry_time=r.entry_time, j=j, px=px, net=net, E=E, R=R))
    mk = pd.DataFrame(rows).sort_values(["entry_time", "coin"]).reset_index(drop=True)
    Em, ddm, _ = port(mk, (k, tm))
    ok("4", abs(Em - claims["final"]["final"]) < 1e-6 and abs(ddm - claims["final"]["mtm_dd"]) < 1e-6
       and abs(nf / len(mk) - claims["maker_fill_rate"]) < 1e-12,
       f"own maker fills (rate {nf / len(mk):.4f}) + own MTM portfolio: {Em:.2f} / DD {ddm:.4f} == claims")
else:
    ok("4", False, "final config V2: extend the verifier before accepting")
c5 = (claims["protocol_sha"] == sha(A4 / "A4_PROTOCOL_PREREGISTERED.md") == (A4 / "A4_PROTOCOL_SHA256.txt").read_text().split()[0]
      and claims["a1c_sha"] == sha(R_ / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet")
      and claims["verdict"] == ("A4 rule sleeve provisional PASS" if all(claims["gates"].values()) else "A4 FAIL"))
ok("5", c5, f"claims / verdict ('{claims['verdict']}') / SHAs consistent")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
