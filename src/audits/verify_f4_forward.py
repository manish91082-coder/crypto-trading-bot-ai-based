"""
Independent verifier for the F4 long-short paper log (logs/forward_ls_f4).
V1 ledger hash chain (every line_sha256 re-computed, prev links), protocol hash, equity / positions file hashes.
V2 link to 16B: the d1 / h4 / h1 hashes in each F4 line equal the 16B ledger line of that day and the files on disk.
V3 C1 re-checked from files: the LO columns equal the 16B paper sleeves for every date (|diff| < $0.01).
V4 stored perp klines re-fetched from the public API for 30 random (coin, hour) pairs: open / high / low / close equal.
V5 open positions of the last day: at most 5 shorts and 5 longs per (line, sleeve); no coin long and short in the same
   (line, sleeve); every open LS_RS short has had no perp high >= entry x 1.5 since its entry hour (stop not missed).
Usage: python verify_f4_forward.py
"""
import sys
import json
import hashlib
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import forward_ls_f4 as Q
import forward_multi_16b as FB


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    L = pd.read_csv(Q.LEDGER)
    prev = "GENESIS"
    for r in L.to_dict("records"):
        line = {k: v for k, v in r.items() if k != "line_sha256"}
        for k, v in line.items():                                    # csv round-trip: restore the json types used when hashing
            if isinstance(v, (np.bool_,)):
                line[k] = bool(v)
            elif isinstance(v, np.integer):
                line[k] = int(v)
            elif isinstance(v, np.floating):
                line[k] = float(v)
        assert r["prev_sha256"] == prev, (r["asof"], "broken chain")
        h = hashlib.sha256(json.dumps(line, sort_keys=True).encode()).hexdigest()
        assert h == r["line_sha256"], (r["asof"], "line hash")
        prev = r["line_sha256"]
        assert r["protocol_sha256"] == sha(Q.PROTO) == (Q.LOG / "F4_PROTOCOL_SHA256.txt").read_text().split()[0]
        assert sha(Q.LOG / "paper" / f"equity_{r['asof']}.csv") == r["equity_sha256"]
        assert sha(Q.LOG / "paper" / f"positions_{r['asof']}.csv") == r["positions_sha256"]
        assert sha(Q.LOG / "paper" / f"orders_{r['asof']}.json") == r["orders_sha256"]
    for r in L.itertuples():                                         # V1b (E2E 2026-10-16): ledger numbers == the equity file
        e = pd.read_csv(Q.LOG / "paper" / f"equity_{r.asof}.csv")
        for ln in ("LS_RS", "LS_F2", "LO"):
            assert abs(round(float(e[f"{ln}_M_AI3"].iloc[-1]), 2) - float(getattr(r, ln))) < 0.005, (r.asof, ln)
    print(f"[V1 PASS] {len(L)} ledger lines: chain, line hashes, protocol, equity / positions files; LS_RS / LS_F2 / LO == equity file")

    L16 = pd.read_csv(FB.LEDGER)
    L16 = L16[~L16.test.astype(bool)].set_index("asof")
    for r in L.itertuples():
        l16 = L16.loc[r.asof]
        assert l16.line_sha256 == r.ledger16b_line_sha256
        for kind, col in (("d1", "d1_sha256"), ("h4_r6", "h4_sha256"), ("h1_r24", "h1_sha256")):
            assert getattr(r, col) == l16[col] == sha(FB.PRED / f"{kind}_{r.asof}.csv"), (r.asof, kind)
    print(f"[V2 PASS] every F4 line is tied to the 16B ledger line and prediction files of its day")

    nc = 0
    for r in L.itertuples():
        e = pd.read_csv(Q.LOG / "paper" / f"equity_{r.asof}.csv", parse_dates=["date"]).set_index("date")
        p = pd.read_csv(FB.PAPER / f"equity_{r.asof}.csv", parse_dates=["date"]).set_index("date")
        ok = all(abs(e.loc[d, f"LO_{k}"] - p.loc[d, k]) < 0.01 for d in p.index for k in ("D1", "H4", "H1"))
        assert ok == bool(r.C1), (r.asof, ok, r.C1)
        nc += ok
    print(f"[V3 PASS] C1 re-checked from files: {nc} of {len(L)} days LO == 16B paper")

    files = sorted(Q.PERP_DIR.glob("*_perp_1h.csv"))
    rng = np.random.default_rng(17)
    n4 = 0
    for f in rng.choice(files, size=min(30, len(files)), replace=len(files) < 30):
        d = pd.read_csv(f, parse_dates=["timestamp"])
        x = d.iloc[int(rng.integers(len(d)))]
        url = f"{Q.API}/fapi/v1/klines?symbol={x.perp}&interval=1h&startTime={Q.ms(x.timestamp)}&limit=1"
        k = json.loads(urllib.request.urlopen(url, timeout=30).read().decode())[0]
        assert pd.Timestamp(k[0], unit="ms") == x.timestamp and [float(v) for v in k[1:5]] == [x.open, x.high, x.low, x.close], (f.name, x.timestamp)
        n4 += 1
    print(f"[V4 PASS] {n4} stored perp hours re-fetched from the public API and equal")

    last = L["asof"].iloc[-1]
    try:
        P = pd.read_csv(Q.LOG / "paper" / f"positions_{last}.csv")
    except pd.errors.EmptyDataError:                                  # PAPER_START day: no position yet (empty file)
        P = pd.DataFrame()
    if len(P):
        for (ln, sl), g in P.groupby(["line", "sleeve"]):
            assert (g.side == "short").sum() <= 5 and (g.side == "long").sum() <= 5, (ln, sl)
            assert not set(g[g.side == "short"].symbol) & set(g[g.side == "long"].symbol), (ln, sl)
        names = Q.perp_names(set(P[P.side == "short"].symbol))
        for r in P[(P.line == "LS_RS") & (P.side == "short")].itertuples():
            d = pd.read_csv(Q.PERP_DIR / f"{r.symbol}_perp_1h.csv", parse_dates=["timestamp"])
            hi = d[d.timestamp >= pd.Timestamp(r.entry)].high.max() / names[r.symbol][1]
            assert hi < r.entry_px * 1.5, (r.symbol, r.entry, hi, r.entry_px)
    print(f"[V5 PASS] open positions of {last}: limits, no long+short overlap, no missed stop on open LS_RS shorts")


if __name__ == "__main__":
    main()
