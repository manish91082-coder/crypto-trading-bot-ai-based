"""
Independent verifier for F7 (logs/strategy_f7_risk).
V1 protocol and trade-file hashes; G0 re-checked against the F2 claims file.
V2 stop exits, re-derived from the raw perp 1h files with plain loops (bars of the sleeve built by hand):
   every D1 and H4 stop, and 150 H1 stops.
   - entry price = the perp open of the entry bar;
   - no bar from the entry bar up to the bar before the exit touched the stop (high >= entry x 1.5);
   - the exit bar did: fill = open x 1.01 if the open gapped over the stop, else stop x 1.01;
   - funding re-summed with a plain loop;
   - trade P&L re-derived.
V3 no missed stop: for 100 rebalance exits per sleeve, no bar in [entry bar, exit bar) had high >= entry x 1.5.
V4 cooldown: no coin is shorted again within 30 days after its stop / liquidation exit (all three sleeves).
V5 liquidations and stops counted from the trade files; mix = mean of sleeves; MaxDD, Calmar, 2022 and K1 events
   re-derived with plain loops from the equity files; gates re-derived.
"""
import sys
import json
import math
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import f7_run as R
from config import LOGS_DIR

C = json.loads((R.OUT / "claims.json").read_text())
NAMES = pd.read_csv(LOGS_DIR / "futures_um_download" / "perp_names.csv").set_index("symbol").perp
BAR = {"D1": pd.Timedelta(days=1), "H4": pd.Timedelta(hours=4), "H1": pd.Timedelta(hours=1)}
CS = 0.0010
_P = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def perp(sym):
    if sym not in _P:
        p = NAMES[sym]
        scale = 1e6 if p.startswith("1000000") else 1e3 if p.startswith("1000") and not sym.startswith("1000") else 1.0
        d = pd.read_csv(R.F2R.FUM / f"{sym}_perp_1h.csv.gz", parse_dates=["timestamp"])
        rows = [(r.timestamp, r.open / scale, r.high / scale, r.close / scale) for r in d.itertuples()]
        ff = R.F2R.FUM / f"{sym}_funding.csv"
        fr = pd.read_csv(ff, parse_dates=["time"]) if ff.exists() else None
        _P[sym] = (rows, {r[0]: r[3] for r in rows}, fr, {r[0]: (r[1], r[2]) for r in rows})
    return _P[sym]


def bar(sym, t0, L):
    """open / high of the sleeve bar [t0, t0+L) from the hourly rows, by hand (open = first hour present)."""
    hours = perp(sym)[3]
    o, h = None, -math.inf
    for i in range(int(L / pd.Timedelta(hours=1))):
        r = hours.get(t0 + pd.Timedelta(hours=i))
        if r is not None:
            if o is None:
                o = r[0]
            h = max(h, r[1])
    return o, (h if o is not None else None)


def funding_sum(sym, units, t_in, t_out):
    _, close, fr, _h = perp(sym)
    s = 0.0
    if fr is None:
        return s
    for e in fr.itertuples():
        if t_in <= e.time < t_out:
            key = e.time.floor("h") - pd.Timedelta(hours=1)
            if key in close and np.isfinite(close[key]):
                s += units * close[key] * e.funding_rate
    return s


def no_touch(sym, entry, t_in, t_out, L):
    t = t_in
    while t < t_out:
        o, h = bar(sym, t, L)
        if h is not None and h >= entry * 1.5:
            return False
        t += L
    return True


def main():
    assert sha(R.OUT / R.PROTO) == (R.OUT / "F7_PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    for k in ("D1", "H4", "H1"):
        assert sha(R.OUT / f"trades_MAIN_{k}_AI_RS.csv") == C["trades_sha256"][k]
    f2 = json.loads(R.F2_CLAIMS.read_text())["MAIN"]
    for k in ("D1", "H4", "H1"):
        assert abs(C["MAIN"]["OFF_LS"]["sleeves"][k]["final"] - f2["AI_LS"]["sleeves"][k]["final"]) < 0.01
        assert abs(C["MAIN"]["OFF_LO"]["sleeves"][k]["final"] - f2["AI_LO"]["sleeves"][k]["final"]) < 0.01
    print("[V1 PASS] hashes; G0: rules-off reproduces the F2 LS and LO sleeve finals within $0.01")

    T = {k: pd.read_csv(R.OUT / f"trades_MAIN_{k}_AI_RS.csv", parse_dates=["entry_time", "exit_time"]) for k in BAR}
    n2 = 0
    for k, L in BAR.items():
        st = T[k][T[k].reason == "stop"]
        if k == "H1" and len(st) > 150:
            st = st.sample(150, random_state=7)
        for t in st.itertuples():
            o_in, _ = bar(t.symbol, t.entry_time, L)
            assert abs(o_in - t.entry_px) < 1e-9 * t.entry_px, (k, t.symbol, o_in, t.entry_px)
            assert no_touch(t.symbol, t.entry_px, t.entry_time, t.exit_time, L), (k, t.symbol, t.entry_time, "earlier touch")
            o, h = bar(t.symbol, t.exit_time, L)
            sp = t.entry_px * 1.5
            fill = o * 1.01 if o >= sp else sp * 1.01
            assert h >= sp and abs(fill - t.exit_px) < 1e-9 * fill, (k, t.symbol, o, h, sp, t.exit_px)
            margin = t.cost / (1 + CS)
            units = margin / t.entry_px
            fs = funding_sum(t.symbol, units, t.entry_time, t.exit_time)
            assert abs(fs - t.funding) < 1e-9 * max(1.0, abs(t.funding)) + 1e-9, (k, t.symbol, fs, t.funding)
            value = margin + fs + units * (t.entry_px - fill)
            fee = units * fill * CS if value > 0 else 0.0
            pnl = max(value, 0.0) - fee - margin - margin * CS
            assert abs(pnl - t.pnl) < 1e-6 * max(1.0, abs(t.pnl)) + 1e-6, (k, t.symbol, pnl, t.pnl)
            n2 += 1
    print(f"[V2 PASS] {n2} stop exits re-derived from raw 1h perp files (entry, no earlier touch, fill, funding, P&L)")

    n3 = 0
    for k, L in BAR.items():
        rb = T[k][(T[k].side == "short") & (T[k].reason == "rebalance_exit")].sample(100, random_state=3)
        for t in rb.itertuples():
            assert no_touch(t.symbol, t.entry_px, t.entry_time, t.exit_time, L), (k, t.symbol, t.entry_time, "missed stop")
            n3 += 1
    print(f"[V3 PASS] {n3} rebalance exits: no bar touched the stop while the short was open")

    n4 = 0
    for k in BAR:
        s = T[k][T[k].side == "short"]
        bad = s[s.reason.isin(["stop", "liquidation", "liquidation_gap"])]
        for b in bad.itertuples():
            again = s[(s.index != b.Index) & (s.symbol == b.symbol) & (s.entry_time > b.exit_time - pd.Timedelta(seconds=1))
                      & (s.entry_time < b.exit_time + pd.Timedelta(days=30))]
            assert again.empty, (k, b.symbol, b.exit_time, again.entry_time.tolist())
            n4 += 1
    print(f"[V4 PASS] cooldown: {n4} stop / liquidation exits, none re-shorted within 30 days")

    M = C["MAIN"]
    liq = sum(int(T[k].reason.isin(["liquidation", "liquidation_gap"]).sum()) for k in BAR)
    stops = sum(int((T[k].reason == "stop").sum()) for k in BAR)
    assert liq == M["RS"]["liquidations"] and stops == M["RS"]["stops"], (liq, stops)

    def plain_stats(name, final):
        e = pd.read_csv(R.OUT / f"equity_MAIN_{name}.csv", parse_dates=["date"])
        for r in e.itertuples():
            assert abs((r.D1 + r.H4 + r.H1) / 3 - r.M_AI3) < 1e-6
        a = [10000.0] + list(e.M_AI3)
        pk, dd = a[0], 0.0
        for v in a:
            pk = max(pk, v)
            dd = max(dd, (pk - v) / pk)
        days = (pd.Timestamp("2026-09-30") - pd.Timestamp("2021-01-01")).days
        cagr = (final / 10000.0) ** (365.25 / days) - 1
        y21 = e[e.date.dt.year == 2021].M_AI3.iloc[-1]
        y22 = e[e.date.dt.year == 2022].M_AI3.iloc[-1]
        pk, fired, nk1 = a[0], False, 0
        for v in a:
            if v > pk:
                pk, fired = v, False
            if not fired and v <= 0.65 * pk:
                nk1, fired = nk1 + 1, True
        return dict(dd=dd * 100, calmar=cagr / dd, r22=(y22 / y21 - 1) * 100, k1=nk1)

    out = {}
    for key, name in (("RS", "AI_RS"), ("OFF_LO", "AI_OFF_LO"), ("RS_cost020", "AI_RS_cost020"), ("RS_CONTROL", "CONTROL_RS")):
        m = M[key]
        fin = sum(m["sleeves"][k]["final"] for k in BAR) / 3
        assert abs(fin - m["mix"]["final"]) < 0.02, (key, fin, m["mix"]["final"])
        ps = plain_stats(name, m["mix"]["final"])
        assert abs(ps["dd"] - m["mix"]["max_dd_pct"]) < 0.01 and abs(ps["calmar"] - m["mix"]["calmar"]) < 0.002, (key, ps, m["mix"])
        assert abs(ps["r22"] - m["mix"]["ret_2022"]) < 0.01 and ps["k1"] == m["K1_events"]["mix"], (key, ps)
        out[key] = ps
    lo, rs = M["OFF_LO"]["mix"], M["RS"]["mix"]
    g = dict(G1=liq <= 7, G2=out["RS"]["dd"] <= C["F2_reference"]["LS"]["max_dd_pct"] + 1e-9,
             G3=rs["final"] > lo["final"] and out["RS"]["calmar"] > out["OFF_LO"]["calmar"], G4=out["RS"]["r22"] > 0,
             G5=M["RS_cost020"]["mix"]["final"] > lo["final"], G6=rs["final"] > M["RS_CONTROL"]["mix"]["final"])
    assert all(C["gates"][k] == v for k, v in g.items()), (g, C["gates"])
    print(f"[V5 PASS] liquidations {liq}, stops {stops}; RS final {rs['final']} MaxDD {out['RS']['dd']:.2f}% Calmar {out['RS']['calmar']:.3f} "
          f"2022 {out['RS']['r22']:+.2f}% K1 {out['RS']['k1']}; LO final {lo['final']}; gates {C['gates']}")


if __name__ == "__main__":
    main()
