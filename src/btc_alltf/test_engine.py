"""BTC-ALLTF study (2026-10-28): ground-level tests of engine.c / engine.py on hand-made bars whose correct trades are
worked out by hand below (no market data). Usage: python src/btc_alltf/test_engine.py   -> TOTAL n, FAIL k"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as E                                                            # noqa: E402

res = []


def ok(name, cond, msg=""):
    res.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {msg}")


def bars(rows, atr=1.0):
    a = np.array(rows, dtype=float)                                           # columns o h l c
    n = len(a)
    return E.Bars(np.arange(n) * 60_000, a[:, 0], a[:, 1], a[:, 2], a[:, 3], np.full(n, atr))


def S(*v):
    return np.array(v, dtype=np.int8)


flat = [[100, 100.5, 99.5, 100]] * 3
# T1 signal exit, long: onset at bar 1 -> enter open[2]; state 0 at bar 3 -> exit open[4]
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 102, 100, 101], [102, 103, 101, 102], [104, 105, 103, 104], [105, 106, 104, 105]])
T = E.run(B, S(0, 1, 1, 0, 0, 0), 1, "X0_SIG")
ok("T1 signal exit", list(T["ei"]) == [2] and list(T["xi"]) == [4] and T["px_in"][0] == 101 and T["px_out"][0] == 104 and T["reason"][0] == 1)
# T2 stop inside a bar: entry 101 (bar 2), stop = 101 - 2*1 = 99; bar 3 low 98.5 -> fill 99, reason SL
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 101.5, 100, 101], [100.5, 101, 98.5, 99.5], [99, 100, 98, 99]])
T = E.run(B, S(0, 1, 1, 1, 1), 1, "X2_SIG_SL2")
ok("T2 stop intrabar", list(T["xi"]) == [3] and T["px_out"][0] == 99 and T["reason"][0] == 3, f"{T}")
# T3 gap through the stop: bar 3 opens at 97 (< stop 99) -> fill at 97, reason SL_GAP
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 101.5, 100, 101], [97, 98, 96, 97], [97, 98, 96, 97]])
T = E.run(B, S(0, 1, 1, 1, 1), 1, "X2_SIG_SL2")
ok("T3 gap stop", T["px_out"][0] == 97 and T["reason"][0] == 4 and T["xi"][0] == 3)
# T4 take profit: X6 stop 2, target 2 -> tp 103; bar 3 high 103.5, low 100 -> fill 103 reason TP
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 101.5, 100, 101], [101, 103.5, 100, 103], [103, 104, 102, 103]])
T = E.run(B, S(0, 1, 1, 1, 1), 1, "X6_SIG_SL2_TP2")
ok("T4 take profit", T["px_out"][0] == 103 and T["reason"][0] == 5)
# T5 stop and target in the same bar -> stop assumed (SL_AMBIG), fill 99
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 101.5, 100, 101], [101, 103.5, 98, 101], [101, 102, 100, 101]])
T = E.run(B, S(0, 1, 1, 1, 1), 1, "X6_SIG_SL2_TP2")
ok("T5 ambiguous bar = stop", T["px_out"][0] == 99 and T["reason"][0] == 11)
# T6 trailing 3*ATR: entry 101, trail starts 98; bar 2 high 101.5 -> trail 98.5 (from bar 3); bar 3 high 106 -> 103 from bar 4;
#    bar 3 low 99 > 98.5 no hit; bar 4 low 102.5 <= 103 -> fill 103 reason TRAIL
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 101.5, 100, 101], [101, 106, 99, 105], [105, 105.5, 102.5, 103], [103, 104, 102, 103]])
T = E.run(B, S(0, 1, 1, 1, 1, 1), 1, "X4_SIG_TRAIL3")
ok("T6 trailing", T["px_out"][0] == 103 and T["reason"][0] == 7 and T["xi"][0] == 4, f"{T}")
# T7 hold 1 bar: onset bar 1 -> enter open[2], exit open[3]; then the state stays 1 -> no re-entry (needs a new onset)
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 102, 100, 101], [102, 103, 101, 102], [103, 104, 102, 103], [104, 105, 103, 104]])
T = E.run(B, S(0, 1, 1, 1, 1, 1), 1, "X7_HOLD1")
ok("T7 hold1, no re-entry", list(T["ei"]) == [2] and list(T["xi"]) == [3] and T["reason"][0] == 2)
# T8 short liquidation at 1x (mmr 0.004): entry 100, liq = 200/1.004 = 199.2032; bar 3 high 210 -> LIQ fill at liq
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [100, 120, 99, 118], [150, 210, 149, 205], [205, 206, 204, 205]])
T = E.run(B, S(0, 1, 1, 1, 1), -1, "X0_SIG", mmr=0.004)
g, fe, fu, net, mae, mfe = E.pnl(T, -1, 0.00046)
ok("T8 short liquidation", T["reason"][0] == 9 and abs(T["px_out"][0] - 200 / 1.004) < 1e-9 and abs(net[0] - (-1 - 0.00046)) < 1e-12, f"{T} net {net}")
# T9 still open at the end -> exit at the last close, reason END
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 102, 100, 101], [102, 103, 101, 102.5]])
T = E.run(B, S(0, 1, 1, 1), 1, "X0_SIG")
ok("T9 end of data", T["reason"][0] == 10 and T["px_out"][0] == 102.5 and T["xi"][0] == 3)
# T10 delay 1: onset at bar 1 -> entry at open[3] instead of open[2]
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 102, 100, 101], [102, 103, 101, 102], [103, 104, 102, 103], [104, 105, 103, 104]])
T = E.run(B, S(0, 1, 1, 1, 0, 0), 1, "X0_SIG", delay=1)
ok("T10 delay", list(T["ei"]) == [3] and T["px_in"][0] == 102 and list(T["xi"]) == [5])
# T11 gate: onset at bar 1 with gate 0 -> skipped; next onset bar 4 with gate 1 -> entry open[5]
B = bars([[100, 101, 99, 100]] * 8)
T = E.run(B, S(0, 1, 1, 0, 1, 1, 0, 0), 1, "X0_SIG", gate=S(1, 0, 1, 1, 1, 1, 1, 1))
ok("T11 gate", list(T["ei"]) == [5] and list(T["xi"]) == [7])
# T12 short stop: entry 100, stop 100 + 1*ATR = 101 (X1); bar 3 high 101.2 -> fill 101; gross = -(1.01-1) = -0.01
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [100, 100.5, 99, 100], [100, 101.2, 99.5, 101], [101, 102, 100, 101]])
T = E.run(B, S(0, 1, 1, 1, 1), -1, "X1_SIG_SL1")
g, fe, fu, net, mae, mfe = E.pnl(T, -1, 0.001)
ok("T12 short stop + fee", T["px_out"][0] == 101 and abs(g[0] + 0.01) < 1e-12 and abs(fe[0] - 0.001 * 2.01) < 1e-15
   and abs(net[0] - (-0.01 - 0.00201)) < 1e-12)
# T13 funding: long held from ts 120000 (entry bar 2) to 240000 (exit bar 4); events at 120000 (not paid: entry at that open),
#     180000 (paid), 240000 (paid: still held at that open), 300000 (not held). rate*P/px_in = 0.0001*100/101 + 0.0002*100/101
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 102, 100, 101], [102, 103, 101, 102], [104, 105, 103, 104], [105, 106, 104, 105]])
T = E.run(B, S(0, 1, 1, 0, 0, 0), 1, "X0_SIG")
tau = np.array([120000, 180000, 240000, 300000]); rp = np.array([0.0005, 0.0001, 0.0002, 0.0003]) * 100
cum = np.r_[0, np.cumsum(rp)]
g, fe, fu, net, mae, mfe = E.pnl(T, 1, 0.0, (tau, cum), B.ts[T["ei"]], B.ts[T["xi"]])
ok("T13 funding window (t_in, t_out]", abs(fu[0] - (0.0001 + 0.0002) * 100 / 101) < 1e-15, f"fu {fu}")
# T14 MAE / MFE: long entry 101 bar 2 (low 100, high 101.5), bar 3 (low 99, high 106), exit open[4] = 105
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [101, 101.5, 100, 101], [101, 106, 99, 105], [105, 107, 95, 106]])
T = E.run(B, S(0, 1, 1, 0, 0), 1, "X0_SIG")
g, fe, fu, net, mae, mfe = E.pnl(T, 1, 0.0)
ok("T14 MAE/MFE", abs(T["worst"][0] - 99) < 1e-12 and abs(T["best"][0] - 106) < 1e-12 and T["px_out"][0] == 105)
# T15 time exit then re-entry at the same open when a new onset is the bar before (HOLD10 not used: hold1 + state 0,1,0,1)
B = bars([[100, 101, 99, 100]] * 6)
T = E.run(B, S(0, 1, 0, 1, 0, 0), 1, "X7_HOLD1")
ok("T15 exit+entry same open", list(T["ei"]) == [2, 4] and list(T["xi"]) == [3, 5])
# T16 control: prices grow 1% per bar exactly -> every random long hold-1 net = 0.01 - f - f*1.01, sd 0
o = 100 * 1.01 ** np.arange(200)
B = E.Bars(np.arange(200), o, o, o, o, np.ones(200))
mu, sd, n = E.control(B, np.zeros(200), 0, 200, 1, np.ones(50, np.int32), 4, 12345, 0.001)
ok("T16 control exact", abs(mu - (0.01 - 0.001 - 0.00101)) < 1e-12 and sd < 1e-9 and n == 200, f"mu {mu} sd {sd} n {n}")
# T17 no ATR at the signal bar -> no entry when an ATR exit is used, entry when it is not
B = bars([[100, 101, 99, 100]] * 5)
B.atr[1] = np.nan
ok("T17 ATR NaN", len(E.run(B, S(0, 1, 1, 0, 0), 1, "X2_SIG_SL2")["ei"]) == 0 and len(E.run(B, S(0, 1, 1, 0, 0), 1, "X0_SIG")["ei"]) == 1)
# T18 short take-profit gap: X5 (stop 1.5, target 3) entry 100 -> tp 97; bar 3 opens 96 -> fill 96 TP_GAP
B = bars([[100, 101, 99, 100], [100, 101, 99, 100], [100, 100.5, 99.5, 100], [96, 97, 95, 96], [96, 97, 95, 96]])
T = E.run(B, S(0, 1, 1, 1, 1), -1, "X5_SIG_SL1.5_TP3")
ok("T18 short TP gap", T["px_out"][0] == 96 and T["reason"][0] == 6)
# T19 fees.json values are read, not typed: spot 0.00085, futures 0.00046
f = E.fees()
ok("T19 fees from deploy/fees.json", f == {"spot": 0.00085, "futures": 0.00046}, f"{f}")
print(f"TOTAL {len(res)}, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
