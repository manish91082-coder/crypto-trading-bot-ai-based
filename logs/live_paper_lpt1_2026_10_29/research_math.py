"""LPT-1 research (2026-10-29): compounding arithmetic, perfect-foresight upper bound on BTC futures, Monte Carlo of the 10 %/day goal.
Run from the project root: python logs/live_paper_lpt1_2026_10_29/research_math.py"""
import numpy as np
import pandas as pd
import json
f = json.load(open("deploy/fees.json"))["rules"]["paper_futures_taker_per_side"]
for g in (0.10, 0.15):
    for d in (5, 20, 30, 60, 90, 180, 365):
        print(f"{g:.0%}/day x {d:3d} days: 10k -> {10000 * (1 + g) ** d:,.0f} USDT")
print(f"\nPERFECT FORESIGHT, BTC futures, 1x, right side of every bar whose |move| > 2 x fee ({f}), 2024-01..2026-09")
for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]:
    b = pd.read_parquet(f"data/derived/btc_alltf/bars/futures_{tf}.parquet", columns=["ts", "open"])
    b = b[b.ts >= 1704067200000]
    r = b.open.shift(-1) / b.open - 1
    g = np.maximum(np.abs(r) - 2 * f, 0).fillna(0)
    d = np.log1p(g).groupby(b.ts // 86400000).sum()
    print(f"{tf:3s} median day {np.expm1(d.median()) * 100:8.2f}%  share of days >= 10%: {(np.expm1(d) >= 0.10).mean() * 100:5.1f}%")
rng = np.random.default_rng(1)
print("\nMONTE CARLO 30 days, 5 trades/day, +1R / -1R, fee 0.1R per trade, 20,000 paths")
for wr in (0.50, 0.55, 0.60):
    for risk in (0.01, 0.03, 0.05, 0.10):
        w = rng.random((20000, 150)) < wr
        eq = np.cumprod(1 + risk * (np.where(w, 1.0, -1.0) - 0.1), axis=1)
        print(f"win {wr:.0%} risk {risk:4.0%}/trade: median 30-day x{np.median(eq[:, -1]):6.2f}  P(avg 10%/day) {100 * (eq[:, -1] >= 1.1 ** 30).mean():6.3f}%"
              f"  P(-50% drawdown) {100 * (eq.min(1) <= 0.5).mean():5.1f}%")
