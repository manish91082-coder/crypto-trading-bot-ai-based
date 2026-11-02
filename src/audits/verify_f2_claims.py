"""
Independent verifier for F1 + F2 (logs/strategy_f2_longshort).
V1 protocol hash; every downloaded zip status in the files log is OK or 404; the scale gate re-derived for 10 coins.
V2 150 random MAIN short trades (H1 sleeve: the hourly grid needs no aggregation): entry / exit prices = perp 1h open
   at the trade times (scaled), funding re-summed with a plain loop over the funding file, liquidation rule, and the
   trade P&L arithmetic re-derived.
V3 G0 and the gates re-derived from claims and the stored equity files (mix = mean of sleeves).
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
import f2_run as R
from config import LOGS_DIR

C = json.loads((R.OUT / "claims.json").read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert sha(R.OUT / R.PROTO) == (R.OUT / "F2_PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    flog = pd.read_csv(LOGS_DIR / "futures_um_download" / "files_log.csv")
    assert flog.status.isin(["OK", "404"]).all()
    gate = pd.read_csv(R.OUT / "F1_G2_scale_gate.csv")
    names = pd.read_csv(LOGS_DIR / "futures_um_download" / "perp_names.csv").set_index("symbol").perp
    for r in gate[gate.status != "no perpetual"].sample(10, random_state=5).itertuples():
        d = pd.read_csv(R.FUM / f"{r.symbol}_perp_1h.csv.gz", parse_dates=["timestamp"]).set_index("timestamp")
        sp = R.S24.bars_1h(R.S24.UNI1H / f"{r.symbol}_1h_full.csv.gz").close
        p = names[r.symbol]
        scale = 1e6 if p.startswith("1000000") else 1e3 if p.startswith("1000") and not r.symbol.startswith("1000") else 1.0
        j = (d.close / scale).reindex(sp.index)
        m = j.notna() & sp.notna() & (sp > 0)
        ratio = float((j[m] / sp[m]).median())
        assert abs(ratio - r.median_ratio) < 1e-12 and ((0.98 <= ratio <= 1.02) == (r.status == "ok")), r.symbol
    print(f"[V1 PASS] protocol; {len(flog)} files OK/404; scale gate re-derived for 10 coins")

    T = pd.read_csv(R.OUT / "trades_MAIN_H1_AI_LS.csv", parse_dates=["entry_time", "exit_time"])
    S = T[(T.side == "short") & (T.reason != "end_of_test")].sample(150, random_state=11)
    for t in S.itertuples():
        p = names[t.symbol]
        scale = 1e6 if p.startswith("1000000") else 1e3 if p.startswith("1000") and not t.symbol.startswith("1000") else 1.0
        d = pd.read_csv(R.FUM / f"{t.symbol}_perp_1h.csv.gz", parse_dates=["timestamp"]).set_index("timestamp")
        o, h, c = d.open / scale, d.high / scale, d.close / scale
        entry = float(o.loc[t.entry_time])
        margin = t.cost / (1 + 0.0010)
        units = margin / entry
        # funding: every event in [entry bar start, exit bar start), price = last close before the event
        fsum = 0.0
        ff = R.FUM / f"{t.symbol}_funding.csv"
        if ff.exists():
            fr = pd.read_csv(ff, parse_dates=["time"])
            for e in fr.itertuples():
                if t.entry_time <= e.time < t.exit_time:
                    key = e.time.floor("h") - pd.Timedelta(hours=1)
                    if key in c.index and np.isfinite(c.loc[key]):
                        fsum += units * float(c.loc[key]) * e.funding_rate
        assert abs(fsum - t.funding) < 1e-9 * max(1.0, abs(t.funding)) + 1e-9, (t.symbol, fsum, t.funding)
        if t.reason == "liquidation":
            hi = float(h.loc[t.exit_time])
            assert margin + fsum + units * (entry - hi) <= 0.005 * units * hi
            pnl = -margin - margin * 0.0010
        else:
            if t.reason == "data_end":
                exitp = float(c.loc[c.index[c.index <= t.exit_time].max()])
            else:
                exitp = float(o.loc[t.exit_time])
            value = margin + fsum + units * (entry - exitp)          # isolated margin holds the funding
            fee = units * exitp * 0.0010 if value > 0 else 0.0
            pnl = max(value, 0.0) - fee - margin - margin * 0.0010
        assert abs(pnl - t.pnl) < 1e-6 * max(1.0, abs(t.pnl)) + 1e-6, (t.symbol, t.entry_time, pnl, t.pnl)
    print(f"[V2 PASS] 150 H1 short trades: prices, funding (plain loop), liquidation rule and P&L re-derived")

    ref = json.loads((R.S27.OUT / "claims.json").read_text())["sleeve_finals"]
    for per in ("MAIN", "PRE"):
        lo = C[per]["AI_LO"]["sleeves"]
        assert all(abs(lo[k]["final"] - ref[f"{per}_f50"][k]) < 0.01 for k in ("D1", "H4", "H1")), per
        e = pd.read_csv(R.OUT / f"equity_{per}_AI_LS.csv").set_index("date")
        assert np.allclose(e[["D1", "H4", "H1"]].mean(axis=1), e.M_AI3)
    M, P = C["MAIN"], C["PRE"]
    lo, ls = M["AI_LO"]["mix"], M["AI_LS"]["mix"]
    g = dict(G1=ls["final"] > lo["final"] and ls["calmar"] > lo["calmar"], G2=ls["max_dd_pct"] < lo["max_dd_pct"],
             G3=ls.get("ret_2022", -1) > 0, G4=ls["final"] > M["CONTROL_LS"]["mix"]["final"],
             G5=P["AI_LS"]["mix"]["final"] > P["AI_LO"]["mix"]["final"], G6=M["AI_LS_cost020"]["mix"]["final"] > lo["final"])
    assert all(C["gates"][k] == v for k, v in g.items())
    print(f"[V3 PASS] G0 (both periods) and gates re-derived: {C['gates']}")


if __name__ == "__main__":
    main()
