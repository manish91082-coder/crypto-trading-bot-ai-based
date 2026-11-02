"""
Synthetic unit tests for the Round 1 engine (no real data, so no result is seen before the runs).
Each test builds a tiny hand-made market and checks one mechanic against hand-computed numbers.
T0 hooks off: r1_engine == f7_risk on 3 random synthetic markets (exact equality of finals, equity and trades).
T1 E1 hedge: opened at the next open with notional = w x invest_short x equity; stop x1.5 (+1 %) fills as specified;
   positive funding is credited to the hedge margin; re-opened at the next decision; P&L arithmetic.
T2 E2 freed slots: a filter that removes every short candidate sends the whole short notional to the hedge.
T3 N1 long block: a blocked top-ranked coin is not bought, the next rank is.
T4 E4 weights: a NEW long gets invest x equity x w.
T5 E11 perp long: cost_short on entry and exit, positive funding is PAID (margin falls), P&L arithmetic; liquidation on the low.
T6 short_order: the short picks follow the hook order and the keep rule uses the hook order.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC / "pipeline_1d"))
import r1_engine as E
import f7_risk as F

CL, CS = 0.0025, 0.0010


def market(syms, closes, grid, highs=None, lows=None):
    """spot (o, c, last) with o = previous close; perp (o, h, c, first, last) with the same prices (and given highs)."""
    spot, perp, low = {}, {}, {}
    for s in syms:
        c = np.asarray(closes[s], float)
        o = np.r_[c[0], c[:-1]]
        h = np.asarray(highs[s], float) if highs and s in highs else np.maximum(o, c)
        lo = np.asarray(lows[s], float) if lows and s in lows else np.minimum(o, c)
        spot[s] = (o, c, grid[-1])
        perp[s] = (o, h, c, grid[0], grid[-1])
        low[s] = lo
    return spot, perp, low


def rows_const(grid, order):
    """the same ranking at every decision: order[0] best."""
    return pd.DataFrame([dict(symbol=s, t=t, score=float(len(order) - i)) for t in grid for i, s in enumerate(order)])


def t0():
    rng = np.random.default_rng(0)
    for seed in range(3):
        rng = np.random.default_rng(seed)
        grid = pd.date_range("2022-01-01", periods=120, freq="D")
        syms = [f"C{i}" for i in range(12)] + ["BTCUSDT"]
        closes = {s: 100 * np.exp(np.cumsum(rng.normal(0, 0.05, len(grid)))) for s in syms}
        spot, perp, _ = market(syms, closes, grid)
        rows = pd.DataFrame([dict(symbol=s, t=t, score=rng.random()) for t in grid for s in syms])
        decide = np.arange(len(grid)) % 5 == 0
        fund = {s: (grid.values[::3].astype("datetime64[ns]"), rng.normal(0.0001, 0.0003, len(grid[::3])), closes[s][::3]) for s in syms}
        kw = dict(stop=1.5, stop_slip=0.01, cooldown_days=30)
        a = F.sim_ls(rows, grid, decide, spot, perp, fund, 0.5, 0.5, 5, 10, CL, CS, **kw)
        b = E.sim_ls(rows, grid, decide, spot, perp, fund, 0.5, 0.5, 5, 10, CL, CS, **kw)
        assert a["final"] == b["final"] and np.array_equal(a["eq"].values, b["eq"].values), seed
        assert len(a["trades"]) == len(b["trades"]) and np.allclose(a["trades"].pnl.values, b["trades"].pnl.values, rtol=0, atol=0)
    print("[T0 PASS] hooks off: r1_engine == f7_risk exactly on 3 random synthetic markets (finals, equity, trades)")


def t1():
    grid = pd.date_range("2022-01-01", periods=6, freq="D")
    syms = ["L1", "L2", "S1", "BTCUSDT"]
    closes = {"L1": [100] * 6, "L2": [100] * 6, "S1": [100] * 6, "BTCUSDT": [100, 100, 100, 100, 100, 100]}
    highs = {"BTCUSDT": [100, 100, 160, 100, 100, 100]}                 # bar 2 touches 1.6 x entry -> stop at 150 x 1.01
    spot, perp, _ = market(syms, closes, grid, highs)
    rows = rows_const(grid, ["L1", "L2", "BTCUSDT", "S1"])             # S1 is the AI bottom (alt short), not BTC
    decide = np.array([True, False, False, True, False, False])
    ev = np.array([grid[1] + pd.Timedelta(hours=8)], dtype="datetime64[ns]")
    fund = {"BTCUSDT": (ev, np.array([0.001]), np.array([100.0]))}
    # invest_long 0.3 so that cash is not the binding limit (with 0.5 + 0.5 the last fill is cash-limited by fees, as in F7)
    r = E.sim_ls(rows, grid, decide, spot, perp, fund, 0.3, 0.5, 1, 1, CL, CS, stop=1.5, stop_slip=0.01, cooldown_days=30,
                 hedge_w=0.5, hedge_sym="BTCUSDT")
    h = r["trades"][r["trades"].side == "hedge"].reset_index(drop=True)
    assert len(h) >= 2, h
    # first hedge: opened bar 1 at 100 with notional 0.5 x 0.5 x e0 (e0 = 10,000 at bar 1 before any fill)
    a = 0.5 * 0.5 * 10_000
    units = a / 100
    assert h.entry_time[0] == grid[1] and h.reason[0] == "stop" and h.exit_time[0] == grid[2]
    assert abs(h.exit_px[0] - 150 * 1.01) < 1e-9
    funding = units * 100 * 0.001
    assert abs(h.funding[0] - funding) < 1e-9
    value = a + funding + units * (100 - 151.5)
    pnl = value - units * 151.5 * CS - a - a * CS
    assert abs(h.pnl[0] - pnl) < 1e-6, (h.pnl[0], pnl)
    assert h.entry_time[1] == grid[4], h                                # re-opened after the next decision (bar 3) at bar 4
    print(f"[T1 PASS] hedge: notional {a:.0f}, stop fill {h.exit_px[0]:.2f}, funding +{funding:.2f}, P&L {pnl:.2f}, re-opened at the next decision")


def t2():
    grid = pd.date_range("2022-01-01", periods=4, freq="D")
    syms = ["L1", "S1", "S2", "BTCUSDT"]
    spot, perp, _ = market(syms, {s: [100] * 4 for s in syms}, grid)
    rows = rows_const(grid, ["L1", "S1", "S2", "BTCUSDT"])
    decide = np.array([True, False, False, False])
    r = E.sim_ls(rows, grid, decide, spot, perp, {}, 0.3, 0.5, 2, 2, CL, CS, stop=1.5, cooldown_days=30,
                 hedge_w=0.0, freed_to_hedge=True, short_order=lambda t, s_, rk, k: [])
    tr = r["trades"]
    assert (tr.side == "short").sum() == 0
    h = tr[tr.side == "hedge"]
    assert len(h) == 1 and abs(h.cost.iloc[0] - 0.5 * 10_000 * (1 + CS)) < 1e-6, h
    print("[T2 PASS] freed slots: all short candidates filtered -> the full 50 % short notional went to the BTC hedge")


def t3():
    grid = pd.date_range("2022-01-01", periods=3, freq="D")
    syms = ["A", "B", "C"]
    spot, perp, _ = market(syms, {s: [100] * 3 for s in syms}, grid)
    rows = rows_const(grid, ["A", "B", "C"])
    decide = np.array([True, False, False])
    r = E.sim_ls(rows, grid, decide, spot, perp, {}, 0.5, 0.0, 1, 1, CL, CS, long_block=lambda t, rk, k: {"A"})
    longs = r["trades"][r["trades"].side == "long"]
    assert list(longs.symbol) == ["B"] and r["long_blocked"] == 1, longs
    print("[T3 PASS] long block: top-ranked A blocked, next rank B bought; blocked count 1")


def t4():
    grid = pd.date_range("2022-01-01", periods=3, freq="D")
    syms = ["A", "B"]
    spot, perp, _ = market(syms, {s: [100] * 3 for s in syms}, grid)
    rows = rows_const(grid, ["A", "B"])
    decide = np.array([True, False, False])
    r = E.sim_ls(rows, grid, decide, spot, perp, {}, 0.5, 0.0, 2, 2, CL, CS,
                 weight_fn=lambda side, t, tg, k: {"A": 0.7, "B": 0.3})
    lt = r["trades"].set_index("symbol")
    assert abs(lt.cost["A"] - 0.5 * 10_000 * 0.7 * (1 + CL)) < 1e-6 and abs(lt.cost["B"] - 0.5 * 10_000 * 0.3 * (1 + CL)) < 1e-6
    print("[T4 PASS] weights: A got 0.5 x 10,000 x 0.7, B got 0.5 x 10,000 x 0.3 (+ cost)")


def t5():
    grid = pd.date_range("2022-01-01", periods=4, freq="D")
    syms = ["A", "B"]
    closes = {"A": [100, 100, 110, 110], "B": [100] * 4}
    spot, perp, low = market(syms, closes, grid)
    rows = rows_const(grid, ["A", "B"])
    decide = np.array([True, False, False, False])
    ev = np.array([grid[1] + pd.Timedelta(hours=8)], dtype="datetime64[ns]")
    fund = {"A": (ev, np.array([0.001]), np.array([100.0]))}
    r = E.sim_ls(rows, grid, decide, spot, perp, fund, 0.5, 0.0, 1, 1, CL, CS,
                 long_perp_ok=lambda s, t, k: True, perp_low=low)
    t = r["trades"].iloc[0]
    a = 0.5 * 10_000
    units = a / 100
    paid = units * 100 * 0.001
    value = a - paid + units * (110 - 100)
    pnl = value - units * 110 * CS - a - a * CS
    assert t.venue == "perp" and abs(t.funding + paid) < 1e-9 and abs(t.pnl - pnl) < 1e-6, (t, pnl)
    # liquidation on the low: a 1x long is liquidated only when price ~ 0
    grid2 = pd.date_range("2022-01-01", periods=3, freq="D")
    spot2, perp2, low2 = market(["A"], {"A": [100, 100, 100]}, grid2, lows={"A": [100, 100, 0.4]})
    r2 = E.sim_ls(rows_const(grid2, ["A"]), grid2, np.array([True, False, False]), spot2, perp2, {}, 0.5, 0.0, 1, 1, CL, CS,
                  long_perp_ok=lambda s, t, k: True, perp_low=low2)
    # a 1x isolated long: margin = units x entry, so margin + units x (low - entry) = units x low > 0.005 x units x low
    # for any low > 0 -> it is never liquidated (Binance's isolated long liquidation price at 1x is 0)
    assert (r2["trades"].reason == "liquidation").sum() == 0 and r2["liquidations"] == 0
    print(f"[T5 PASS] perp long: funding paid {paid:.2f}, P&L {pnl:.2f} (cost_short both legs); a 1x long is NOT liquidated "
          f"even at a low of 0.4 (entry 100), as the margin rule implies")


def t6():
    grid = pd.date_range("2022-01-01", periods=3, freq="D")
    syms = ["A", "B", "C", "D"]
    spot, perp, _ = market(syms, {s: [100] * 3 for s in syms}, grid)
    rows = rows_const(grid, ["A", "B", "C", "D"])
    decide = np.array([True, False, False])
    r = E.sim_ls(rows, grid, decide, spot, perp, {}, 0.5, 0.5, 1, 1, CL, CS,
                 short_order=lambda t, s_, rk, k: ["B", "C", "D"])          # default would pick D (lowest rank)
    shorts = r["trades"][r["trades"].side == "short"]
    assert list(shorts.symbol) == ["B"], shorts
    print("[T6 PASS] short_order: the hook order [B, C, D] was used (default order would have shorted D)")


if __name__ == "__main__":
    for f in (t0, t1, t2, t3, t4, t5, t6):
        f()
    print("ALL SYNTHETIC TESTS PASS")


def t7():
    """short-side mark-to-market P&L per bar sums to the realized P&L of all short + hedge trades."""
    for seed in range(3):
        rng = np.random.default_rng(seed + 10)
        grid = pd.date_range("2022-01-01", periods=90, freq="D")
        syms = [f"C{i}" for i in range(10)] + ["BTCUSDT"]
        closes = {s: 100 * np.exp(np.cumsum(rng.normal(0, 0.06, len(grid)))) for s in syms}
        spot, perp, _ = market(syms, closes, grid)
        rows = pd.DataFrame([dict(symbol=s, t=t, score=rng.random()) for t in grid for s in syms])
        fund = {s: (grid.values[::2].astype("datetime64[ns]"), rng.normal(0.0001, 0.0003, len(grid[::2])), closes[s][::2]) for s in syms}
        r = E.sim_ls(rows, grid, np.arange(len(grid)) % 5 == 0, spot, perp, fund, 0.3, 0.5, 3, 6, CL, CS,
                     stop=1.5, stop_slip=0.01, cooldown_days=30, hedge_w=0.5)
        tr = r["trades"]
        realized = tr[tr.side.isin(["short", "hedge"])].pnl.sum()
        assert abs(r["short_pnl"].sum() - realized) < 1e-6 * max(1.0, abs(realized)), (seed, r["short_pnl"].sum(), realized)
    print("[T7 PASS] short-side daily mark-to-market P&L sums exactly to the realized short + hedge trade P&L (3 random markets)")


if __name__ == "__main__":
    t7()


def t8():
    """E4 cap (CODE_CHANGES 6): every weight <= 0.30; with n <= 3 all weights are 0.30 and the rest stays cash;
    n = 5 hand-computed redistribution; the engine spends leg budget x w (no renormalisation)."""
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(SRC / "analytics"))
    sys.path.insert(0, str(SRC / "research"))
    sys.path.insert(0, str(SRC / "execution"))
    import r1_run as R
    for w in ([1, 1], [5, 1], [1, 2, 3], [0.9, 0.05, 0.05]):
        c = R.cap_weights(np.array(w, float))
        assert np.allclose(c, 0.30, atol=1e-12) and abs(c.sum() - 0.30 * len(w)) < 1e-12, (w, c)
    c = R.cap_weights(np.array([0.5, 0.2, 0.1, 0.1, 0.1]))
    assert np.allclose(c, [0.30, 0.28, 0.14, 0.14, 0.14], atol=1e-12), c
    rng = np.random.default_rng(8)
    for _ in range(2000):
        n = int(rng.integers(1, 11))
        c = R.cap_weights(rng.random(n) + 1e-3)
        assert (c <= 0.30 + 1e-12).all() and abs(c.sum() - min(1.0, 0.30 * n)) < 1e-9, (n, c)
    grid = pd.date_range("2022-01-01", periods=3, freq="D")
    spot, perp, _ = market(["A", "B"], {s: [100] * 3 for s in ("A", "B")}, grid)
    r = E.sim_ls(rows_const(grid, ["A", "B"]), grid, np.array([True, False, False]), spot, perp, {}, 0.5, 0.0, 2, 2, CL, CS,
                 weight_fn=lambda side, t, tg, k: dict(zip(tg, R.cap_weights(np.ones(len(tg))))))
    lt = r["trades"].set_index("symbol")
    assert all(abs(lt.cost[s] - 0.5 * 10_000 * 0.30 * (1 + CL)) < 1e-6 for s in ("A", "B")), lt.cost
    print("[T8 PASS] cap: n<=3 -> all 0.30 (rest cash); n=5 hand case; 2,000 random sets <= 0.30 with sum min(1, 0.3n); engine spends budget x 0.30")


if __name__ == "__main__" and "T8" in sys.argv:
    t8()
