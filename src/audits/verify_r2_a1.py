"""Independent verifier for A1 (logs/r2_4h_a1/A1_PROTOCOL_PREREGISTERED.md). Own loops; does not import the A1 module.
1 S-BRK / S-TRD signal sets re-derived for 3 coins     2 200 random trades re-simulated (gross, fee, funding to 1e-9)
3 gate table recomputed from the trades file          4 claims JSON + protocol / A0 / data SHAs
5 S-LAD trades == S6 4h V0 gross R, trade by trade
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
A1 = R_ / "logs" / "r2_4h_a1"
res = []


def ok(tag, c, m):
    res.append(bool(c)); print(f"[{tag} {'PASS' if c else 'FAIL'}] {m}")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bars4h(coin):
    d = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    d = d.sort_values("timestamp").set_index("timestamp")
    g = d.groupby(d.index.floor("4h"))
    return pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last())).dropna()


def my_sim(o, h, l, c, stop0, A):
    best = -np.inf
    for k in range(60):
        if k > 0:
            best = max(best, h[k - 1])
        tr = max(stop0, best - 3 * A)
        if l[k] <= tr:
            return k, min(o[k], tr)
    return 59, c[59]


D = pd.read_parquet(A1 / "a1_trades.parquet")
# 1 signals
start, end = pd.Timestamp("2020-02-01"), pd.Timestamp("2026-10-01")
all_ok = True
for coin in ("BTCUSDT", "SOLUSDT", "LINKUSDT"):
    b = bars4h(coin)
    c, h, l, o = b.close.values, b.high.values, b.low.values, b.open.values
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    tr[0] = h[0] - l[0]
    atr = np.full(len(c), np.nan)
    for i in range(13, len(c)):
        atr[i] = tr[i - 13:i + 1].mean()
    ema = np.empty(len(c)); ema[0] = c[0]
    for i in range(1, len(c)):
        ema[i] = ema[i - 1] + 2 / 51 * (c[i] - ema[i - 1])
    for sig in ("S-BRK", "S-TRD"):
        got = set()
        busy = {"long": -1, "short": -1}
        for i in range(len(c)):
            side = None
            if sig == "S-BRK" and i >= 20:
                if c[i] > h[i - 20:i].max():
                    side = "long"
                elif c[i] < l[i - 20:i].min():
                    side = "short"
            if sig == "S-TRD" and i >= 6:
                if c[i - 1] <= ema[i - 1] and c[i] > ema[i] and ema[i] > ema[i - 6]:
                    side = "long"
                elif c[i - 1] >= ema[i - 1] and c[i] < ema[i] and ema[i] < ema[i - 6]:
                    side = "short"
            if side is None:
                continue
            e = i + 1
            if i <= busy[side] or e + 60 > len(c) or not np.isfinite(atr[i]) or not (start <= b.index[e] < end):
                continue
            A = atr[i]
            sg = 1 if side == "long" else -1
            oo, hh, lo, cc = (sg * o[e:e + 60], sg * (h if sg > 0 else l)[e:e + 60], sg * (l if sg > 0 else h)[e:e + 60], sg * c[e:e + 60])
            stop0 = oo[0] - 2 * A
            k, px = my_sim(oo, hh, lo, cc, stop0, A)
            got.add((b.index[e], side))
            busy[side] = e + k
        theirs = set(zip(D[(D.signal == sig) & (D.coin == coin)].entry_time, D[(D.signal == sig) & (D.coin == coin)].side))
        all_ok &= got == theirs
        if got != theirs:
            print("   diff", coin, sig, len(got), len(theirs), list(got ^ theirs)[:3])
ok("1", all_ok, "S-BRK / S-TRD signal sets (with the one-open rule) re-derived for BTC, SOL, LINK: equal")

# 2 re-simulate 200 random trades
fund = {}
for cn in D.coin.unique():
    f = pd.read_csv(R_ / "data" / "futures_um" / f"{cn}_funding.csv"); f["time"] = pd.to_datetime(f["time"]); fund[cn] = f
smp = D.sample(200, random_state=11)
cache, mg = {}, 0.0
for x in smp.itertuples():
    if x.coin not in cache:
        cache[x.coin] = bars4h(x.coin)
    b = cache[x.coin]
    e = b.index.get_loc(x.entry_time)
    sg = 1 if x.side == "long" else -1
    o, h, l, c = b.open.values, b.high.values, b.low.values, b.close.values
    oo, hh, lo, cc = (sg * o[e:e + 60], sg * (h if sg > 0 else l)[e:e + 60], sg * (l if sg > 0 else h)[e:e + 60], sg * c[e:e + 60])
    stop0 = oo[0] - x.R_price
    k, px = my_sim(oo, hh, lo, cc, stop0, x.atr)
    gross = (px - oo[0]) / x.R_price
    fee = 0.00054 * (abs(oo[0]) + abs(px)) / x.R_price
    f = fund[x.coin]
    endt = x.entry_time + pd.Timedelta(hours=4) * (k + 1)
    fr = f[(f.time > x.entry_time) & (f.time < endt)].funding_rate.sum() * sg * abs(oo[0]) / x.R_price
    mg = max(mg, abs(gross - x.gross), abs(fee - x.fee_base), abs(fr - x.funding_R), abs(k - x.exit_idx))
ok("2", mg < 1e-9, f"200 random trades re-simulated with own loop: max |diff| gross/fee/funding/exit {mg:.2e}")

# 3 gate recompute
G = pd.read_csv(A1 / "A1_gate.csv")
g_ok = True
for r in G.itertuples():
    d = D[(D.signal == r.signal) & (D.side == r.side) & D.perp_ok]
    dev = d[d.entry_time < "2025-10-01"]
    cost = dev.fee_base.mean() + max(dev.funding_R.mean(), 0)
    p1 = d[d.entry_time < "2024-01-01"].net_base.mean()
    p2 = dev[dev.entry_time >= "2024-01-01"].net_base.mean()
    want = bool(dev.gross.mean() >= 2 * cost and p1 > 0 and p2 > 0)
    g_ok &= want == bool(r.PASS) and abs(dev.net_base.mean() - r.mean_net) < 1e-12 and len(dev) == r.n_dev
ok("3", g_ok, f"gate table ({len(G)} signal-sides) recomputed from trades: PASS flags and means equal")

# 4 claims + SHAs
cl = json.loads((A1 / "claims_a1.json").read_text())
a0 = R_ / "logs" / "r2_4h_a0" / "A0_4H_PROTOCOL_PREREGISTERED.md"
c4 = (cl["a1_protocol_sha"] == sha(A1 / "A1_PROTOCOL_PREREGISTERED.md") == (A1 / "A1_PROTOCOL_SHA256.txt").read_text().split()[0]
      and cl["a0_sha"] == sha(a0) == (a0.parent / "A0_PROTOCOL_SHA256.txt").read_text().split()[0]
      and cl["trades_sha"] == sha(A1 / "a1_trades.parquet")
      and cl["legs_sha"] == sha(R_ / "data" / "derived" / "swing_anatomy" / "legs_all.parquet")
      and all(cl["gate"][f"{r.signal}|{r.side}"]["PASS"] == bool(r.PASS) for r in G.itertuples()))
ok("4", c4, "claims JSON == CSV; A1 / A0 protocol SHAs == locks; trades and legs SHAs")

# 5 S-LAD == S6
s6 = pd.read_parquet(R_ / "logs" / "research_probe_scalein" / "trades.parquet")
s6 = s6[s6.tf == "4h"][["coin", "side", "entry_time", "V0_gross"]]
m = D[D.signal == "S-LAD"].merge(s6, on=["coin", "side", "entry_time"], how="outer", indicator=True)
c5 = (m._merge == "both").all() and np.abs(m.gross - m.V0_gross).max() < 1e-12
ok("5", c5, f"S-LAD = S6 4h: {int((m._merge == 'both').sum())} trades matched, unmatched {int((m._merge != 'both').sum())}, "
            f"max gross diff {np.abs(m.gross - m.V0_gross).max():.1e}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
(A1 / "verify_log.txt").write_text(f"verify_r2_a1: {len(res)} checks, FAIL {res.count(False)}\n")
sys.exit(1 if False in res else 0)
