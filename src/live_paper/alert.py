"""LPT-1 price alerts (2026-10-29): polls the live Binance spot best bid/ask every 10 s and prints one line when a condition is met
(each condition fires once), then exits when all fired or after --minutes. Read-only.
Usage: python src/live_paper/alert.py "BTCUSDT>=80200" "ETHUSDT<=2290" [--minutes 120]"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mins = 120
    if "--minutes" in sys.argv:
        mins = float(sys.argv[sys.argv.index("--minutes") + 1])
        args = [a for a in args if a != str(sys.argv[sys.argv.index("--minutes") + 1])]
    conds = []
    for a in args:
        m = re.match(r"([A-Z0-9]+)(>=|<=)([0-9.]+)$", a)
        if m:
            conds.append([m.group(1), m.group(2), float(m.group(3)), False])
    t_end = time.time() + mins * 60
    while time.time() < t_end and not all(c[3] for c in conds):
        for c in conds:
            if c[3]:
                continue
            try:
                b, a_, _ = lpt.top("spot", c[0])
            except Exception:                                                # noqa: BLE001
                continue
            mid = (b + a_) / 2
            if (c[1] == ">=" and mid >= c[2]) or (c[1] == "<=" and mid <= c[2]):
                c[3] = True
                print(f"ALERT {lpt.iso()} {c[0]} {c[1]} {c[2]} (mid {mid:.6g})", flush=True)
        time.sleep(10)
    print(f"ALERTS_END {lpt.iso()}", flush=True)


if __name__ == "__main__":
    main()
