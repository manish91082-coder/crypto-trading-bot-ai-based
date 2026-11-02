"""LPT-1 helper (2026-10-29): after every closed 5m candle, test a written rejection rule at a resistance level (read-only, prints
one line per symbol per candle). Rule (setup A short trigger): the candle's high reached the level - 0.3 x ATR5m, it closed red,
its upper wick is >= 40 % of its range and its taker-buy share is < 0.45.
Usage: python src/live_paper/rejection_watch.py --minutes 30 ETHUSDT:2340.1 BTCUSDT:80700"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402
from levels import atr_abs                                                    # noqa: E402


def main():
    mins = float(sys.argv[sys.argv.index("--minutes") + 1]) if "--minutes" in sys.argv else 30
    pairs = [a.split(":") for a in sys.argv[1:] if ":" in a]
    end = time.time() + mins * 60
    seen = {}
    while time.time() < end:
        for sym, lvl in pairs:
            lvl = float(lvl)
            try:
                k = lpt.klines("spot", sym, "5m", 60)
            except Exception as e:                                           # noqa: BLE001  (network: try again next round)
                print(f"WARN {lpt.iso()} {sym} {type(e).__name__}", flush=True)
                continue
            c = k.iloc[-2]                                                    # last CLOSED candle
            if seen.get(sym) == c.t:
                continue
            seen[sym] = c.t
            a5 = atr_abs(k.iloc[:-1])
            rng = max(c.h - c.l, 1e-12)
            touched = c.h >= lvl - 0.3 * a5
            red = c.c < c.o
            wick = (c.h - max(c.o, c.c)) / rng
            tb = c.tbq / max(c.qv, 1e-9)
            sig = touched and red and wick >= 0.4 and tb < 0.45
            print(f"{'REJECT_SIGNAL' if sig else 'STATUS'} {lpt.iso()} {sym} 5m {pd.Timestamp(int(c.t), unit='ms'):%H:%M} o {c.o:.6g} h {c.h:.6g} "
                  f"l {c.l:.6g} c {c.c:.6g} level {lvl} touched {touched} red {red} wick {wick:.2f} taker {tb:.2f}", flush=True)
        time.sleep(15)
    print("WATCH_END", flush=True)


if __name__ == "__main__":
    main()
