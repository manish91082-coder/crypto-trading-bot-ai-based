"""Tests for src/execution/risk_rules_l4.py (hand-computed values + consistency with the N1 K2 heat rule).
T1 liquidation prices (hand values)   T2 anti-liquidation boundary cases   T3 max leverage
T4 heat scale cases                   T5 same heat result as N1 apply_overlays(heat) on a synthetic trade list
T6 the current F6 short book (1x isolated, stop +50%) evaluated by the rule (information)"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "execution")); sys.path.insert(0, str(R_ / "src" / "research"))
import risk_rules_l4 as RR

res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


# T1: long 100, 10x, mmr 0.5% -> 100*(1-0.1+0.005)=90.5 ; short -> 100*(1+0.1-0.005)=109.5 ; 1x long -> 0.5
ok("T1", abs(RR.liquidation_price(100, 1, 10, 0.005) - 90.5) < 1e-12 and abs(RR.liquidation_price(100, -1, 10, 0.005) - 109.5) < 1e-12
   and abs(RR.liquidation_price(100, 1, 1, 0.005) - 0.5) < 1e-12, "liquidation prices 90.5 / 109.5 / 0.5")
# T2: long 100 at 10x: liq distance 9.5 -> 0.4*9.5 = 3.8; stop 96.2 ok, 96.19 not; stop above entry not ok
ok("T2", RR.anti_liq_ok(100, 96.2, 1, 10, 0.005) and not RR.anti_liq_ok(100, 96.19, 1, 10, 0.005) and not RR.anti_liq_ok(100, 101, 1, 10, 0.005)
   and RR.anti_liq_ok(100, 103.8, -1, 10, 0.005) and not RR.anti_liq_ok(100, 99, -1, 10, 0.005), "boundary at 0.4 x liquidation distance")
# T3: stop 5% below: need 0.05 <= 0.4*(1/lev - 0.005) -> 1/lev >= 0.13 -> lev <= 7.69 -> 7
ok("T3", RR.max_leverage(100, 95, 1, 0.005) == 7 and RR.max_leverage(100, 40, 1, 0.005) == 0, "max leverage 7 for a 5% stop; 0 for a 60% stop")
# T4
ok("T4", RR.heat_scale(0, 100, 10_000) == 1.0 and abs(RR.heat_scale(550, 100, 10_000) - 0.5) < 1e-12 and RR.heat_scale(600, 1, 10_000) == 0.0,
   "heat scale 1 / 0.5 / 0")
# T5: consistency with N1 K2 (fractions of equity, same order, same exit rule)
import n1_portfolio as N
rng = np.random.default_rng(5)
n = 400
L = pd.DataFrame(dict(sleeve=rng.choice(list("ABC"), n), coin=rng.choice(["X", "Y", "Z"], n), tf=rng.choice(N.TFS, n), fam=rng.integers(0, 4, n),
                      a=np.sort(rng.integers(0, 2000, n)), dist=rng.uniform(0.02, 0.2, n)))
L["E"] = L.a + rng.integers(1, 300, n)
L["entry_time"] = pd.Timestamp("2021-01-01") + pd.to_timedelta(L.a, unit="h")
w0 = rng.uniform(0.002, 0.03, n)
wN = N.apply_overlays(L, w0.copy(), {"heat": True}, None)
order = L.assign(_t=L.tf.map(N.TFI), _s=L.sleeve.map(N.SLEEVE_ORDER)).sort_values(["a", "_s", "coin", "_t", "fam"], kind="mergesort").index
openp, wR = [], w0.copy()
for i in order:
    openp = [(e, r) for e, r in openp if e > L.a[i]]
    sc = RR.heat_scale(sum(r for _, r in openp), w0[i] * L.dist[i], 1.0)
    wR[i] = w0[i] * sc
    if wR[i] > 0:
        openp.append((L.E[i], wR[i] * L.dist[i]))
ok("T5", float(np.abs(wN - wR).max()) < 1e-12, f"heat_scale reproduces N1 K2 weights on {n} synthetic trades (max diff {np.abs(wN - wR).max():.1e})")
# T7 combined check: 5% stop at 10x fails anti-liq; at 5x passes; heat full -> not ok
a = RR.check_order(100, 95, 1, 10, 0.005, 1000, 0, 10_000); b = RR.check_order(100, 95, 1, 5, 0.005, 1000, 0, 10_000)
c = RR.check_order(100, 95, 1, 5, 0.005, 1000, 600, 10_000)
ok("T7", (not a["ok"]) and b["ok"] and b["scale"] == 1.0 and (not c["ok"]) and c["scale"] == 0.0, "check_order: 10x reject, 5x accept, heat full reject")
# T6 information: F6 shorts 1x isolated with stop at +50% (STOP_X 1.5)
f6 = RR.anti_liq_ok(100, 150, -1, 1, 0.005)
liq = RR.liquidation_price(100, -1, 1, 0.005)
print(f"[T6 INFO] F6 short 1x: liquidation ~{liq:.1f} (+{liq - 100:.1f}%), stop +50% -> anti_liq_ok(k=0.4) = {f6}; "
      f"the stop still triggers {liq - 150:.1f}% of price before liquidation")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
