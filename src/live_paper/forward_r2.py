"""FWD-R2 (2026-10-29): forward paper test of the R2-confirmed strategies with EXACTLY the research semantics (locked engine.dll + rules.py:
entry at the open of the bar after the signal bar, X0 signal exit at the open after the exit bar, fees from deploy/fees.json, futures funding).
The coin list is FROZEN at the start (forward_r2_universe.json) so nothing can be re-selected later. Only trades whose ENTRY bar opens at or
after FORWARD_START count. Each run recomputes from the live bars and appends the complete trade list to forward_r2.jsonl (hash-chained),
so a later edit of an earlier result would break the chain.
Usage: python src/live_paper/forward_r2.py            (first run freezes the universe)"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402
import signals as SG                                                          # noqa: E402

E = SG.study.E
FORWARD_START = "2026-10-29T13:30:00Z"
UNI = lpt.LOG / "forward_r2_universe.json"


def funding_table(sym, t0):
    h = SG.bybit_1h(sym, pages=1)
    fr = lpt.get(f"{lpt.BYB}/funding/history", dict(category="linear", symbol=sym, startTime=t0, endTime=lpt.now_ms(), limit=200))["result"]["list"]
    if not fr:
        return None
    tau = np.array(sorted(int(x["fundingRateTimestamp"]) for x in fr), np.int64)
    rate = {int(x["fundingRateTimestamp"]): float(x["fundingRate"]) for x in fr}
    op = dict(zip(h.t.astype(np.int64), h.o))
    px = np.array([op.get((t // 3_600_000) * 3_600_000, np.nan) for t in tau])
    ok = np.isfinite(px)
    tau, px = tau[ok], px[ok]
    r = np.array([rate[t] for t in tau])
    return tau, np.r_[0.0, np.cumsum(r * px)]


def main():
    t0 = int(pd.Timestamp(FORWARD_START).value // 10 ** 6)
    if not UNI.exists():
        UNI.write_text(json.dumps(dict(frozen_utc=lpt.iso(), forward_start=FORWARD_START, coins=SG.universe(30)), indent=1))
    coins = json.loads(UNI.read_text())["coins"]
    fees = E.fees()
    trades, errs = [], []
    for sid, market, tf, name in SG.STRATS:
        for s in coins:
            try:
                b = SG.spot_bars(s, tf) if market == "spot" else SG.fut_bars(s, tf)
                if len(b) < 300:
                    continue
                out, x = SG.rules.compute(b, tf)
                g = SG.rules.gates(x)
                rows = [f"{r}|{q}" for r in out for q in "AB"] + [f"{k}|{q}" for k in g for q in "LS"]
                mm = np.empty((len(rows), len(b)), np.int8)
                i = 0
                for r in out:
                    mm[i], mm[i + 1] = out[r]; i += 2
                for k_ in g:
                    mm[i], mm[i + 1] = g[k_]; i += 2
                C = {c["name"]: c for c in SG.study.enumerate_configs(market, dict(rows=rows), {r["id"]: r for r in SG.rules.REG})}
                c = C[name]
                SG.study._LAST.clear()
                st = SG.study.state_of(c, mm)
                gate = None if c["gate"] == "-" else np.asarray(mm[c["grow"]])
                B = E.Bars(b.ts.values, b.open.values, b.high.values, b.low.values, b.close.values, x.atr(14).values)
                T = E.run(B, st, c["dir"], c["exit"], gate=gate)
                ts = B.ts
                keep = ts[T["ei"]] >= t0
                if not keep.any():
                    continue
                T = {k: v[keep] for k, v in T.items()}
                t_in, t_out = ts[T["ei"]], ts[T["xi"]]
                fund = funding_table(s, t0) if market == "futures" else None
                _, fe, fu, net, _, _ = E.pnl(T, c["dir"], fees[market], fund, t_in, t_out)
                last_px = float(lpt.top(market, s)[0])                       # live bid: mark of a still-open trade
                for j in range(len(t_in)):
                    open_ = int(T["reason"][j]) == 10                        # END = still open at the last closed bar
                    m_net = (last_px / T["px_in"][j] - 1) - fees[market] * (1 + last_px / T["px_in"][j]) if open_ else float(net[j])
                    trades.append(dict(strategy=sid, market=market, tf=tf, sym=s, entry_utc=pd.Timestamp(int(t_in[j]), unit="ms").isoformat(),
                                       entry_px=float(T["px_in"][j]), exit_utc=None if open_ else pd.Timestamp(int(t_out[j]), unit="ms").isoformat(),
                                       exit_px=None if open_ else float(T["px_out"][j]), status="OPEN" if open_ else "CLOSED", net=m_net,
                                       funding=float(fu[j]), mark_px=last_px if open_ else None))
            except Exception as e:                                           # noqa: BLE001
                errs.append(f"{sid} {s}: {type(e).__name__}: {str(e)[:60]}")
    lpt.append_chain(lpt.LOG / "forward_r2.jsonl", dict(utc=lpt.iso(), forward_start=FORWARD_START, trades=trades, errors=errs))
    D = pd.DataFrame(trades)
    print(f"FWD-R2 {lpt.iso()}  since {FORWARD_START}  trades {len(D)}  errors {len(errs)}")
    if len(D):
        for sid, g in D.groupby("strategy"):
            cl, op = g[g.status == "CLOSED"], g[g.status == "OPEN"]
            print(f" {sid}: closed {len(cl)} (sum net {100 * cl.net.sum():+.2f}%, wins {(cl.net > 0).sum()}), open {len(op)} "
                  f"(mark {100 * op.net.sum():+.2f}%): " + ", ".join(f"{r.sym} {100 * r.net:+.2f}%" for r in op.itertuples()))


if __name__ == "__main__":
    main()
