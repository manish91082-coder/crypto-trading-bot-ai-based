"""LIVE-AI strategy signals (2026-10-29): the strategies that passed the R2 cross-coin confirmation (CONFIRMED_SKILL, logs/btc_alltf_r2_2026_10_29)
evaluated on LIVE closed bars with the LOCKED rule code (src/btc_alltf/rules.py + study.enumerate_configs: the same definition, nothing re-fitted).
For every strategy and coin it reports whether the rule's entry fired on the last closed bar (onset + filter), whether its exit fired, and the
current state. Read-only; it places nothing (the desk decides). Written to logs/live_paper_lpt1_2026_10_29/signals.jsonl (hash-chained).
Strategies (name exactly as in R2 tests_S1.csv):
  SA spot 15m      L2|T_DONCH55_20|long_con|X0_SIG|F1_TREND200      buy a 55-bar low break while price is above SMA200 (dip in an uptrend)
  SB futures 8h    L2|O_RSI14_20_80|long_con|X0_SIG|F2_ADX20         long when RSI14 > 80 with ADX > 20 (momentum), exit when RSI < 50
  SB2 futures 8h   L1|O_RSI14_20_80|long_con|X0_SIG|-                same without the ADX filter
  SC futures 1d    L2|T_CHOP14|long_nat|X0_SIG|F5_VOLUME             CHOP14 trend state on, entry on above-average volume
Bars: spot from data-api.binance.vision; futures from Bybit linear (8h built from 1h, UTC-aligned, like the R2 bars).
Usage: python src/live_paper/signals.py [--top 30]"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402

sys.path.insert(0, str(lpt.PROJ / "src/btc_alltf"))
import rules                                                                  # noqa: E402
import study                                                                  # noqa: E402

STRATS = [("SA", "spot", "15m", "L2|T_DONCH55_20|long_con|X0_SIG|F1_TREND200"),
          ("SB", "futures", "8h", "L2|O_RSI14_20_80|long_con|X0_SIG|F2_ADX20"),
          ("SB2", "futures", "8h", "L1|O_RSI14_20_80|long_con|X0_SIG|-"),
          ("SC", "futures", "1d", "L2|T_CHOP14|long_nat|X0_SIG|F5_VOLUME")]


def spot_bars(sym, tf, n=1000):
    k = lpt.klines("spot", sym, tf, n).iloc[:-1]                             # closed bars only
    return pd.DataFrame(dict(ts=k.t.values, open=k.o.values, high=k.h.values, low=k.l.values, close=k.c.values, volume=k.v.values,
                             taker_buy_base=k.tbv.values.astype(float)))


def bybit_1h(sym, pages=3):
    out, end = [], None
    for _ in range(pages):
        p = dict(category="linear", symbol=sym, interval="60", limit=1000)
        if end:
            p["end"] = end
        d = lpt.get(f"{lpt.BYB}/kline", p)["result"]["list"]
        if not d:
            break
        out += d
        end = int(d[-1][0]) - 1
    k = pd.DataFrame(out, columns=["t", "o", "h", "l", "c", "v", "qv"]).astype(float).drop_duplicates("t").sort_values("t")
    return k


def fut_bars(sym, tf):
    if tf == "1d":
        d = lpt.get(f"{lpt.BYB}/kline", dict(category="linear", symbol=sym, interval="D", limit=1000))["result"]["list"][::-1]
        k = pd.DataFrame(d, columns=["t", "o", "h", "l", "c", "v", "qv"]).astype(float)
    else:
        h = bybit_1h(sym)
        g = h.groupby(h.t // 28_800_000)
        k = pd.DataFrame(dict(t=g.t.first() // 28_800_000 * 28_800_000, o=g.o.first(), h=g.h.max(), l=g.l.min(), c=g.c.last(), v=g.v.sum(),
                              qv=g.qv.sum(), n=g.t.size())).reset_index(drop=True)
        k = k[k.n == 8]                                                      # complete 8h bars only
    now = lpt.now_ms()
    ms = 86_400_000 if tf == "1d" else 28_800_000
    k = k[k.t + ms <= now]                                                   # closed bars only
    return pd.DataFrame(dict(ts=k.t.values.astype(np.int64), open=k.o.values, high=k.h.values, low=k.l.values, close=k.c.values, volume=k.v.values,
                             taker_buy_base=np.full(len(k), np.nan)))


def evaluate(b, tf, market, name):
    out, x = rules.compute(b, tf)
    g = rules.gates(x)
    rows = [f"{r}|{s}" for r in out for s in "AB"] + [f"{k}|{s}" for k in g for s in "LS"]
    mm = np.empty((len(rows), len(b)), np.int8)
    i = 0
    for r in out:
        mm[i], mm[i + 1] = out[r]; i += 2
    for k_ in g:
        mm[i], mm[i + 1] = g[k_]; i += 2
    C = {c["name"]: c for c in study.enumerate_configs(market, dict(rows=rows), {r["id"]: r for r in rules.REG})}
    c = C[name]
    study._LAST.clear()
    st = np.asarray(study.state_of(c, mm))
    gate = None if c["gate"] == "-" else np.asarray(mm[c["grow"]])
    onset = bool(st[-1] == 1 and st[-2] == 0 and (gate is None or gate[-1] == 1))
    exit_ = bool(st[-1] == 0 and st[-2] == 1)
    atr = float(x.atr(14).values[-1])
    return dict(state=int(st[-1]), entry=onset, exit=exit_, gate_now=None if gate is None else int(gate[-1]), atr=atr, close=float(b.close.iloc[-1]),
                bar_open=pd.Timestamp(int(b.ts.iloc[-1]), unit="ms").isoformat())


def universe(n):
    """top n crypto USDT spot pairs by 24h quote volume (same exclusions as lpt.universe), with a longer timeout for the large ticker list"""
    import requests
    sys.path.insert(0, str(lpt.PROJ / "src/btc_alltf_r2"))
    from common import NOT_CRYPTO, LEV
    for i in range(4):
        try:
            t = requests.get(f"{lpt.BIN}/ticker/24hr", timeout=40).json()
            break
        except Exception:                                                    # noqa: BLE001
            if i == 3:
                raise
    rows = [(x["symbol"], float(x["quoteVolume"])) for x in t if x["symbol"].endswith("USDT") and x["symbol"][:-4] not in lpt.STABLE
            and x["symbol"] not in NOT_CRYPTO and not x["symbol"].endswith(LEV)]
    rows.sort(key=lambda r: -r[1])
    return [s for s, _ in rows[:n]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    syms = universe(a.top)
    res = []
    for sid, market, tf, name in STRATS:
        if a.only and sid not in a.only.split(","):
            continue
        for s in syms:
            try:
                b = spot_bars(s, tf) if market == "spot" else fut_bars(s, tf)
                if len(b) < 300:
                    continue
                r = evaluate(b, tf, market, name)
                r.update(strategy=sid, market=market, tf=tf, sym=s, name=name)
                res.append(r)
            except Exception as e:                                           # noqa: BLE001  (no perp for that coin, etc.)
                res.append(dict(strategy=sid, sym=s, error=f"{type(e).__name__}: {str(e)[:80]}"))
    lpt.append_chain(lpt.LOG / "signals.jsonl", dict(utc=lpt.iso(), results=res))
    D = pd.DataFrame(res)
    ok = D[D.get("error").isna()] if "error" in D else D
    print(f"SIGNALS {lpt.iso()}  coins {len(syms)}  evaluated {len(ok)}  errors {len(D) - len(ok)}")
    for sid in ok.strategy.unique():
        g = ok[ok.strategy == sid]
        ent = g[g.entry]
        ex = g[g.exit]
        on = g[g.state == 1]
        print(f" {sid} {g.tf.iloc[0]:3s} {g.market.iloc[0]:7s} in-state {len(on):2d}/{len(g)}  ENTRY now: {', '.join(ent.sym) or '-'}  EXIT now: {', '.join(ex.sym) or '-'}"
              f"  (last closed bar {g.bar_open.max()})")


if __name__ == "__main__":
    main()
