"""Hand-number tests of forward_carry.py (T2-CARRY, 2026-11-02). Every expected value below is worked out by hand from the protocol's accounting section.
Usage: python src/audits/test_forward_carry.py   -> TOTAL n checks, FAIL k."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live_paper"))
import forward_carry as F                                                     # noqa: E402

H = F.HOUR
FAIL = []
n_ = 0


def ok(name, a, b, tol=1e-9):
    global n_
    n_ += 1
    good = abs(a - b) <= tol if isinstance(b, float) else a == b
    print(f"[{name} {'PASS' if good else 'FAIL'}] got {a}, expected {b}")
    if not good:
        FAIL.append(name)


def bars(px):
    return {i * H: (o, o, o, o) for i, o in enumerate(px)}


fs, ff = 0.001, 0.0005
# T1 flat prices, one funding event of +0.01% at t = 1h: N 2500, q 25, funding 0.01% x 25 x 100 = 0.25; entry 3.75, exit 3.75
r = F.coin_rows(bars([100.0, 100.0]), bars([100.0, 100.0]), {H: 0.0001}, fs, ff, 0, 2 * H)
ok("T1 funding", r[0]["funding"], 0.25)
ok("T1 pnl", r[0]["pnl"], 0.25 - 7.5)
ok("T1 events", r[-1]["n_funding"], 1)
# T2 event exactly at a bar close is counted on that bar and not before; event 2h counts on the second row only
r = F.coin_rows(bars([100.0, 100.0, 100.0]), bars([100.0, 100.0, 100.0]), {2 * H: 0.001}, fs, ff, 0, 3 * H)
ok("T2 before", r[0]["funding"], 0.0)
ok("T2 at close", r[1]["funding"], 2.5)
# T3 negative funding is a cost to the short: -0.1% x 25 x 100 = -2.5
r = F.coin_rows(bars([100.0, 100.0]), bars([100.0, 100.0]), {H: -0.001}, fs, ff, 0, 2 * H)
ok("T3 negative", r[0]["funding"], -2.5)
# T4 both legs +10%: basis 0, exit cost on 2750 notional = 2.75 + 1.375, entry 3.75, pnl -7.875
r = F.coin_rows(bars([100.0, 100.0]), bars([100.0, 100.0]), {}, fs, ff, 0, 2 * H)
r2 = F.coin_rows({0: (100.0, 110.0, 100.0, 110.0)}, {0: (100.0, 110.0, 100.0, 110.0)}, {}, fs, ff, 0, H)
ok("T4 basis", r2[0]["basis"], 0.0, 1e-9)
ok("T4 pnl", r2[0]["pnl"], -7.875)
# T5 perp lags spot: spot +1, perp +0.5 at q 25: basis +12.5
r = F.coin_rows({0: (100.0, 101.0, 100.0, 101.0)}, {0: (100.0, 100.5, 100.0, 100.5)}, {}, fs, ff, 0, H)
ok("T5 basis", r[0]["basis"], 12.5)
# T6 margin on the hour high: high 160, (2500 - 25 x 60) / (25 x 160) = 1000 / 4000 = 0.25
r = F.coin_rows({0: (100.0, 100.0, 100.0, 100.0)}, {0: (100.0, 160.0, 100.0, 100.0)}, {}, fs, ff, 0, H)
ok("T6 margin", r[0]["margin"], 0.25)
# T7 a missing bar raises, nothing is filled in
try:
    F.coin_rows({0: (1.0,) * 4, 2 * H: (1.0,) * 4}, {0: (1.0,) * 4, 2 * H: (1.0,) * 4}, {}, fs, ff, 0, 3 * H)
    ok("T7 gap raises", False, True)
except KeyError:
    ok("T7 gap raises", True, True)
# T8 combine: drawdown from the peak, the worst margin of the two coins
A = [dict(t=H, pnl=100.0, margin=0.9), dict(t=2 * H, pnl=-100.0, margin=0.8)]
B = [dict(t=H, pnl=0.0, margin=0.7), dict(t=2 * H, pnl=0.0, margin=0.95)]
m = F.combine({"BTCUSDT": A, "ETHUSDT": B})
ok("T8 dd", m[1]["dd"], 9900.0 / 10100.0 - 1)
ok("T8 margin", m[1]["margin"], 0.8)
# T9 the first bar below capital counts as drawdown from the starting capital
m = F.combine({"BTCUSDT": [dict(t=H, pnl=-50.0, margin=1.0)], "ETHUSDT": [dict(t=H, pnl=0.0, margin=1.0)]})
ok("T9 dd", m[0]["dd"], -0.005)
# T10 verdict branches
base = dict(min_margin=0.9, n_funding={"BTCUSDT": 270, "ETHUSDT": 270}, hours=2160, net_pct=0.2, max_dd_pct=1.0)
ok("T10 interim", F.verdict(base, False), "INTERIM")
ok("T10 pass", F.verdict(base, True), "PASS")
ok("T10 hurdle", F.verdict(dict(base, net_pct=0.187), True), "FAIL")
ok("T10 hurdle edge", F.verdict(dict(base, net_pct=0.188), True), "PASS")
ok("T10 negative", F.verdict(dict(base, net_pct=-0.5), True), "FAIL")
ok("T10 dd", F.verdict(dict(base, max_dd_pct=2.0), True), "FAIL")
ok("T10 margin early", F.verdict(dict(base, min_margin=0.249), False), "FAIL (margin)")
ok("T10 margin edge", F.verdict(dict(base, min_margin=0.25), True), "PASS")
ok("T10 gap", F.verdict(dict(base, n_funding={"BTCUSDT": 269, "ETHUSDT": 270}), True), "INCONCLUSIVE")
ok("T10 hours", F.verdict(dict(base, hours=2159), True), "INCONCLUSIVE")
# T12 an event at the last close is priced at the open of the next perp bar, which adds no row: 0.1% x 25 x 200 = 5
r = F.coin_rows(bars([100.0]), bars([100.0, 200.0]), {H: 0.001}, fs, ff, 0, 5 * H)
ok("T12 rows", len(r), 1)
ok("T12 funding", r[0]["funding"], 5.0)
ok("T11 hours in window", (F.ms(F.END) - F.ms(F.START)) // F.HOUR, 2160)
ok("T11 events in window", (F.ms(F.END) - F.ms(F.START)) // F.FUNDING_STEP, F.N_EVENTS)
print("TOTAL", n_, "checks, FAIL", len(FAIL))
sys.exit(1 if FAIL else 0)
