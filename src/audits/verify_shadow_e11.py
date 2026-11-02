"""
Independent verifier for the E11 shadow ledger (logs/forward_ls_f4/shadow_e11). Usage: python verify_shadow_e11.py
V1 protocol hash; ledger hash chain (every line_sha256 re-computed, prev links); equity / positions file hashes.
V2 every shadow line is tied to the F4 ledger line of the same as-of day (f4_line_sha256) and its LS_RS equals it;
   E11 == the last M_AI3 of the shadow equity file.
V3 open perp longs of the last day: entry price == the stored F4 perp 1h open of the entry bar (scaled); at most 5 longs
   and 5 shorts per sleeve; no coin long and short in the same sleeve.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import shadow_e11_f4 as SH


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert sha(SH.PROTO) == (SH.PROTO.parent / "E11_SHADOW_PROTOCOL_SHA256.txt").read_text().split()[0]
    L = pd.read_csv(SH.LEDGER)
    prev = "GENESIS"
    for r in L.to_dict("records"):
        line = {}
        for k, v in r.items():
            if k == "line_sha256":
                continue
            line[k] = bool(v) if isinstance(v, np.bool_) else int(v) if isinstance(v, np.integer) else float(v) if isinstance(v, np.floating) else v
        assert r["prev_sha256"] == prev, (r["asof"], "chain")
        assert hashlib.sha256(json.dumps(line, sort_keys=True).encode()).hexdigest() == r["line_sha256"], (r["asof"], "line hash")
        prev = r["line_sha256"]
        assert sha(SH.OUT / f"equity_{r['asof']}.csv") == r["equity_sha256"] and sha(SH.OUT / f"positions_{r['asof']}.csv") == r["positions_sha256"]
        assert r["protocol_sha256"] == sha(SH.PROTO)
    print(f"[V1 PASS] {len(L)} shadow ledger lines: chain, line hashes, equity / positions files, protocol")
    L4 = pd.read_csv(SH.Q.LEDGER).set_index("asof")
    for r in L.itertuples():
        l4 = L4.loc[r.asof]
        assert l4.line_sha256 == r.f4_line_sha256 and abs(float(l4.LS_RS) - r.LS_RS) < 0.005, r.asof
        e = pd.read_csv(SH.OUT / f"equity_{r.asof}.csv")
        assert abs(round(float(e.M_AI3.iloc[-1]), 2) - r.E11) < 0.005, r.asof
    print(f"[V2 PASS] every shadow line tied to its F4 line; LS_RS equal; E11 == shadow equity file")
    last = L["asof"].iloc[-1]
    try:
        P = pd.read_csv(SH.OUT / f"positions_{last}.csv")
    except pd.errors.EmptyDataError:
        P = pd.DataFrame()
    n = 0
    if len(P):
        for sl, g in P.groupby("sleeve"):
            assert (g.side == "short").sum() <= 5 and (g.side == "long").sum() <= 5, sl
            assert not set(g[g.side == "short"].symbol) & set(g[g.side == "long"].symbol), sl
        names = SH.Q.perp_names(set(P.symbol))
        for x in P[(P.side == "long") & (P.venue == "perp")].itertuples():
            d = pd.read_csv(SH.Q.PERP_DIR / f"{x.symbol}_perp_1h.csv", parse_dates=["timestamp"]).set_index("timestamp")
            o = float(d.open.loc[pd.Timestamp(x.entry)]) / names[x.symbol][1]
            assert abs(o - x.entry_px) < 1e-9 * o, (x.symbol, x.entry, o, x.entry_px)
            n += 1
    print(f"[V3 PASS] open positions of {last}: limits, no overlap; {n} perp-long entry prices == stored perp opens")


if __name__ == "__main__":
    main()
