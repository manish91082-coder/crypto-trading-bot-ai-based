"""LPT-1 analyst helper (2026-10-29): key price levels of a few symbols from LIVE public data (read-only; uses lpt.py's data functions).
Prints per symbol: price, 1h EMA20/EMA50, today's VWAP, today's high/low, prior-day high/low, 12h swing high/low, ATR(14) 1h and 5m (absolute),
the last 6 closed 15m candles, and the futures funding / OI context.
Usage: python src/live_paper/levels.py BTCUSDT ETHUSDT ..."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402


def atr_abs(k, n=14):
    pc = k.c.shift(1)
    tr = pd.concat([k.h - k.l, (k.h - pc).abs(), (k.l - pc).abs()], axis=1).max(axis=1)
    return float(tr.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])


def main():
    for s in sys.argv[1:]:
        h1 = lpt.klines("spot", s, "1h", 300)
        m5 = lpt.klines("spot", s, "5m", 400)
        m15 = lpt.klines("spot", s, "15m", 20)
        d1 = lpt.klines("spot", s, "1d", 5)
        p = float(m5.c.iloc[-1])
        day0 = lpt.now_ms() // 86_400_000 * 86_400_000
        t = m5[m5.t >= day0]
        vwap = t.qv.sum() / t.v.sum() if t.v.sum() else np.nan
        e20, e50 = lpt.ema(h1.c.values, 20)[-1], lpt.ema(h1.c.values, 50)[-1]
        print(f"\n{s} price {p:.6g} | 1h EMA20 {e20:.6g} EMA50 {e50:.6g} | VWAP {vwap:.6g} | today H {t.h.max():.6g} L {t.l.min():.6g} | "
              f"PDH {d1.h.iloc[-2]:.6g} PDL {d1.l.iloc[-2]:.6g} | 12h swing H {h1.h.iloc[-12:].max():.6g} L {h1.l.iloc[-12:].min():.6g} | "
              f"ATR1h {atr_abs(h1):.5g} ATR5m {atr_abs(m5):.5g}")
        print("  last 15m candles (open time UTC, o h l c, quote vol, taker buy share):")
        for _, r in m15.iloc[-7:-1].iterrows():
            print(f"   {pd.Timestamp(int(r.t), unit='ms'):%H:%M}  {r.o:.6g} {r.h:.6g} {r.l:.6g} {r.c:.6g}  {r.qv:,.0f}  {r.tbq / max(r.qv, 1e-9):.2f}")


if __name__ == "__main__":
    main()
