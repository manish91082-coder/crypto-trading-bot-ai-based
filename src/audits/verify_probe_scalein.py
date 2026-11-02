"""
Independent verifier for the probe / scale-in study. Own bar building and a plain bar-by-bar loop (no import of the study).
 V1 300 random trades (seed 7): re-simulate all 4 variants, base cost, from raw 5m bars -> must match trades.parquet to 1e-9 R.
 V2 4h and 1D: S1_summary mean_R (base) recomputed from trades.parquet.
 V3 claims JSON vs S2 table; protocol SHA unchanged.
"""
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "research_probe_scalein"
RULE = {"5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1D": "1D"}
HRS = {"5m": 5 / 60, "15m": 0.25, "1h": 1.0, "4h": 4.0, "1D": 24.0}
PLAN = {"V0": [(0, 1.0)], "V1": [(0, 0.25), (1, 0.75)], "V2": [(0, 0.25), (1, 0.25), (2, 0.5)], "V3": [(1, 1.0)]}
SIDE_COST, FUND = 0.00045, 0.0001
_cache = {}


def get_bars(coin, tf):
    if (coin, tf) not in _cache:
        d = pd.read_csv(ROOT / "data" / "universe_hf" / "5m" / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
        d["timestamp"] = pd.to_datetime(d["timestamp"])
        d = d.set_index("timestamp").sort_index()
        if tf != "5m":
            d = d.resample(RULE[tf], label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        _cache[(coin, tf)] = d
    return _cache[(coin, tf)]


def one(tr):
    b = get_bars(tr.coin, tr.tf)
    e = b.index.get_loc(pd.Timestamp(tr.entry_time))
    w = b.iloc[e:e + 60]
    longp = tr.side == "long"
    E = w.open.iloc[0]
    A = tr.atr
    stop0 = E - tr.R_price if longp else E + tr.R_price
    best = None
    pending = {v: [list(x) for x in p] for v, p in PLAN.items()}
    fills = {v: [] for v in PLAN}
    exit_px, exit_i = None, None
    for v in PLAN:                                   # the planned-entry unit is filled at the open, before any stop check
        for leg in pending[v]:
            if leg[0] == 0:
                fills[v].append((leg[1], E, 0)); leg[1] = None
    for i in range(len(w)):
        o, h, l, c = w.open.iloc[i], w.high.iloc[i], w.low.iloc[i], w.close.iloc[i]
        if longp:
            stop = stop0 if best is None else max(stop0, best - 3 * A)
            if l <= stop:
                exit_px, exit_i = min(o, stop), i
                break
        else:
            stop = stop0 if best is None else min(stop0, best + 3 * A)
            if h >= stop:
                exit_px, exit_i = max(o, stop), i
                break
        for v in PLAN:
            for leg in pending[v]:
                k, u = leg
                if leg[1] is None:
                    continue
                if k > 0:
                    lvl = E + k * A if longp else E - k * A
                    if (longp and h >= lvl) or ((not longp) and l <= lvl):
                        fills[v].append((u, max(o, lvl) if longp else min(o, lvl), i)); leg[1] = None
        if longp:
            best = h if best is None else max(best, h)
        else:
            best = l if best is None else min(best, l)
    if exit_px is None:
        exit_px, exit_i = w.close.iloc[-1], len(w) - 1
    out = {}
    for v, fl in fills.items():
        r = 0.0
        for u, px, i in fl:
            g = (exit_px - px) if longp else (px - exit_px)
            r += u * (g - SIDE_COST * (px + exit_px) - FUND * px * (exit_i - i + 1) * HRS[tr.tf] / 8) / tr.R_price
        out[v] = r
    return out


def main():
    D = pd.read_parquet(OUT / "trades.parquet")
    ok = True
    smp = D.sample(300, random_state=7)
    bad = 0
    for tr in smp.itertuples():
        r = one(tr)
        for v in PLAN:
            if abs(r[v] - getattr(tr, f"{v}_base")) > 1e-9:
                bad += 1
                if bad <= 5:
                    print("V1 mismatch", tr.tf, tr.coin, tr.side, tr.entry_time, v, r[v], getattr(tr, f"{v}_base"))
    ok1 = bad == 0
    print("V1", "PASS" if ok1 else f"FAIL ({bad})")
    S = pd.read_csv(OUT / "S1_summary.csv")
    ok2 = True
    for tf in ("4h", "1D"):
        for side in ("long", "short"):
            g = D[(D.tf == tf) & (D.side == side)]
            for v in PLAN:
                ref = S[(S.tf == tf) & (S.side == side) & (S.cost == "base") & (S.variant == v)].mean_R.iloc[0]
                ok2 &= abs(g[f"{v}_base"].mean() - ref) < 1e-12
    print("V2", "PASS" if ok2 else "FAIL")
    c = json.loads((OUT / "claims_probe_scalein.json").read_text())
    Dff = pd.read_csv(OUT / "S2_diff_vs_full.csv")
    ok3 = c["protocol_sha256"] == hashlib.sha256((OUT / "PROBE_SCALEIN_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() \
        == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0]
    for r in Dff.itertuples():
        ok3 &= c["verdicts"][f"{r.tf}_{r.side}_{r.cost}_{r.variant}"] == r.verdict
    print("V3", "PASS" if ok3 else "FAIL")
    print("ALL PASS" if ok1 and ok2 and ok3 else "SOME FAIL")


if __name__ == "__main__":
    main()
