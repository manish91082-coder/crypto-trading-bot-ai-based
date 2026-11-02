"""
Ladder entries: test (probe) entry + scale-in vs full entry, after Binance costs (BNB fees). Historical simulation only.
Protocol: logs/research_probe_scalein/PROBE_SCALEIN_PROTOCOL_PREREGISTERED.md (SHA256 locked before any result).
Usage: python probe_scalein.py
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ladder_sessions as L                      # verified swing-point labelling (points/state), same 10 coins

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "research_probe_scalein"
HF = ROOT / "data" / "universe_hf" / "5m"
TFS = {"5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1D": "1D"}
HOURS = {"5m": 5 / 60, "15m": 0.25, "1h": 1.0, "4h": 4.0, "1D": 24.0}
T, TRAIL, BUF = 60, 3.0, 0.5
START, END = pd.Timestamp("2020-02-01"), pd.Timestamp("2026-10-01")
COST = dict(base=(0.00045, 0.0001), stress=(0.0009, 0.0002), spot=(0.00085, 0.0))   # (per side, funding per 8h)
VARIANTS = {"V0": [(0.0, 1.0)], "V1": [(0.0, 0.25), (1.0, 0.75)], "V2": [(0.0, 0.25), (1.0, 0.25), (2.0, 0.5)], "V3": [(1.0, 1.0)]}
SEED, NBOOT = 20261017, 2000


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def bars(coin, tf):
    d = pd.read_csv(HF / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"], parse_dates=["timestamp"])
    d = d.set_index("timestamp").sort_index()
    if tf != "5m":
        d = d.resample(TFS[tf], label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return d


def simulate(o, h, l, c, stop0, A, bar_h):
    """long-side engine on (possibly sign-flipped) price arrays. Returns per-variant list of fills
    [(units, fill_px, fill_idx)], exit_px, exit_idx."""
    n = len(o)
    prevmax = np.concatenate([[-np.inf], np.maximum.accumulate(h)[:-1]])
    trail = np.maximum(stop0, prevmax - TRAIL * A)
    hit = np.where(l <= trail)[0]
    th = int(hit[0]) if len(hit) else None
    if th is not None:
        ex_i, ex_px = th, float(min(o[th], trail[th]))
    else:
        ex_i, ex_px = n - 1, float(c[n - 1])
    E = float(o[0])
    out = {}
    for v, legs in VARIANTS.items():
        fills = []
        for k, u in legs:
            if k == 0.0:
                fills.append((u, E, 0))
                continue
            lvl = E + k * A
            trg = np.where(h >= lvl)[0]
            if not len(trg):
                continue
            ti = int(trg[0])
            if th is not None and ti >= th:          # stop first in the same bar, or stop came earlier
                continue
            fills.append((u, float(max(o[ti], lvl)), ti))
        out[v] = fills
    return out, ex_px, ex_i


def pnl(fills, ex_px, ex_i, R, bar_h, cost):
    side, fund = cost
    g = c_ = 0.0
    for u, px, i in fills:
        g += u * (ex_px - px) / R
        c_ += u * (side * (abs(px) + abs(ex_px)) + fund * abs(px) * (ex_i - i + 1) * bar_h / 8) / R
    return g, c_


def signals(legs, coin, tf):
    g = legs[(legs.coin == coin) & (legs.tf == tf) & (legs.K == 3.0)].sort_values("start_time")
    pt = L.points(g)
    nxt_atr = g.atr_confirm.values
    pt["atr_next"] = np.append(nxt_atr[1:], np.nan)
    sig = []
    for i, x in pt.iterrows():
        if x.state == "UP" and x.typ == "L" and x.label == "HL":
            sig.append(("long", x.known_time, x.price, x.atr_next))
        elif x.state == "DOWN" and x.typ == "H" and x.label == "LH":
            sig.append(("short", x.known_time, x.price, x.atr_next))
    return [s for s in sig if pd.notna(s[1]) and START <= s[1] < END and np.isfinite(s[3]) and s[3] > 0]


def run():
    legs = pd.read_parquet(L.LEGS, columns=["coin", "tf", "K", "direction", "start_time", "start_price", "end_time", "end_price",
                                            "end_i", "confirm_time", "atr_start", "atr_confirm", "move_atr"])
    rows = []
    for tf in TFS:
        for coin in L.COINS:
            b = bars(coin, tf)
            idx = {t: i for i, t in enumerate(b.index)}
            O, H, Lo, C = (b[k].values.astype("float64") for k in ("open", "high", "low", "close"))
            for side, kt, piv, A in signals(legs, coin, tf):
                e = idx.get(pd.Timestamp(kt))
                if e is None or e + T > len(O):
                    continue
                s = slice(e, e + T)
                if side == "long":
                    o, h, l, c, stop0 = O[s], H[s], Lo[s], C[s], piv - BUF * A
                else:
                    o, h, l, c, stop0 = -O[s], -Lo[s], -H[s], -C[s], -(piv + BUF * A)
                R = o[0] - stop0
                if not R > 0:
                    continue
                res, ex_px, ex_i = simulate(o, h, l, c, stop0, A, HOURS[tf])
                rec = dict(tf=tf, coin=coin, side=side, entry_time=b.index[e], year=b.index[e].year, R_price=R, atr=A,
                           exit_idx=ex_i, exit_px=abs(ex_px), entry_px=abs(o[0]))
                for v, fills in res.items():
                    rec[f"{v}_units"] = sum(u for u, _, _ in fills)
                    rec[f"{v}_fills"] = json.dumps([(u, abs(px), i) for u, px, i in fills])
                    for cn, cs in COST.items():
                        gg, cc = pnl(fills, ex_px, ex_i, R, HOURS[tf], cs)
                        rec[f"{v}_gross"] = gg
                        rec[f"{v}_{cn}"] = gg - cc
                        rec[f"{v}_{cn}_cost"] = cc
                rows.append(rec)
        print(f"{tf} done: {sum(r['tf'] == tf for r in rows)} trades", flush=True)
    return pd.DataFrame(rows)


def mdd(x):
    cum = np.cumsum(x)
    return float(np.max(np.maximum.accumulate(np.concatenate([[0], cum]))[1:] - cum)) if len(x) else 0.0


def summarise(D):
    rng = np.random.default_rng(SEED)
    S, Dff = [], []
    D = D.sort_values("entry_time")
    D["period"] = np.where(D.entry_time < "2024-01-01", "P1", np.where(D.entry_time < "2025-10-01", "P2", "P3"))
    for (tf, side), g in D.groupby(["tf", "side"], sort=False):
        for cn in ("base", "stress", "spot"):
            if cn == "spot" and side == "short":
                continue
            for v in VARIANTS:
                x = g[f"{v}_{cn}"].values
                entered = g[f"{v}_units"].values > 0
                row = dict(tf=tf, side=side, cost=cn, variant=v, signals=len(x), entered=int(entered.sum()),
                           win_rate=float((x[entered] > 0).mean()) if entered.any() else np.nan,
                           mean_R=float(x.mean()), median_R=float(np.median(x)), p05_R=float(np.percentile(x, 5)),
                           sum_R=float(x.sum()), mean_gross_R=float(g[f"{v}_gross"].mean()), mean_cost_R=float(g[f"{v}_{cn}_cost"].mean()),
                           share_gain_below_cost=float((np.abs(g[f"{v}_gross"].values[entered]) < g[f"{v}_{cn}_cost"].values[entered]).mean()) if entered.any() else np.nan,
                           max_dd_R=mdd(x))
                for p in ("P1", "P2", "P3"):
                    row[f"mean_R_{p}"] = float(g.loc[g.period == p, f"{v}_{cn}"].mean())
                S.append(row)
            base = g["V0_" + cn].values
            blocks = {}
            for (coin, yr), gb in g.groupby(["coin", "year"]):
                blocks[(coin, yr)] = gb
            keys = list(blocks)
            for v in ("V1", "V2", "V3"):
                d = g[f"{v}_{cn}"].values - base
                bsum = np.array([(blocks[k][f"{v}_{cn}"] - blocks[k]["V0_" + cn]).sum() for k in keys])
                bcnt = np.array([len(blocks[k]) for k in keys])
                pick = rng.integers(0, len(keys), (NBOOT, len(keys)))
                bs = bsum[pick].sum(axis=1) / bcnt[pick].sum(axis=1)
                lo, hi = np.percentile(bs, [2.5, 97.5])
                p05v = np.percentile(g[f"{v}_{cn}"].values, 5)
                p05b = np.percentile(base, 5)
                verdict = "earns more" if lo > 0 else ("costs profit" if hi < 0 else ("cuts losses" if p05v > p05b else "no difference"))
                Dff.append(dict(tf=tf, side=side, cost=cn, variant=v, diff_mean_R=float(d.mean()), ci_lo=float(lo), ci_hi=float(hi),
                                p05_variant=float(p05v), p05_V0=float(p05b), verdict=verdict))
    return pd.DataFrame(S), pd.DataFrame(Dff)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    proto = OUT / "PROBE_SCALEIN_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after lock"
    assert sha(L.LEGS) == L.LEGS_SHA
    D = run()
    D.to_parquet(OUT / "trades.parquet", index=False)
    S, Dff = summarise(D)
    S.to_csv(OUT / "S1_summary.csv", index=False)
    Dff.to_csv(OUT / "S2_diff_vs_full.csv", index=False)
    overall = {}
    for cn in ("base", "stress"):
        for side in ("long", "short"):
            for v in ("V1", "V2"):
                q = Dff[(Dff.cost == cn) & (Dff.side == side) & (Dff.variant == v)]
                overall[f"{cn}_{side}_{v}_earns_more_tfs"] = int((q.verdict == "earns more").sum())
    rec = {side: any(overall[f"base_{side}_{v}_earns_more_tfs"] >= 3 and overall[f"stress_{side}_{v}_earns_more_tfs"] >= 3
                     for v in ("V1", "V2")) for side in ("long", "short")}
    claims = dict(protocol_sha256=sha(proto), legs_sha256=L.LEGS_SHA, code_sha256=sha(__file__), trades=int(len(D)),
                  counts=overall, scale_in_recommended=rec,
                  verdicts={f"{r.tf}_{r.side}_{r.cost}_{r.variant}": r.verdict for r in Dff.itertuples()})
    (OUT / "claims_probe_scalein.json").write_text(json.dumps(claims, indent=1))
    print(json.dumps(dict(trades=len(D), counts=overall, rec=rec), indent=1))


if __name__ == "__main__":
    main()
