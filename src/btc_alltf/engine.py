"""BTC-ALLTF study (2026-10-28): Python side of engine.c (see its header for the exact fill rules).
run(): one config -> raw trades (entry/exit bar, reason, prices, MAE/MFE prices).  pnl(): gross / fee / funding / net.
Fees come only from deploy/fees.json (rules.paper_spot_per_side, rules.paper_futures_taker_per_side)."""
import ctypes
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
_E = ctypes.CDLL(str(HERE / "engine.dll"))
_D = ctypes.POINTER(ctypes.c_double)
_I8 = ctypes.POINTER(ctypes.c_int8)
_I32 = ctypes.POINTER(ctypes.c_int32)
_I64 = ctypes.POINTER(ctypes.c_int64)
_E.bt.argtypes = [ctypes.c_int, _D, _D, _D, _D, _D, _I8, _I8, ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_double,
                  ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                  _I32, _I32, _I8, _D, _D, _D, _D]
_E.bt.restype = ctypes.c_int
_E.ctrl.argtypes = [ctypes.c_int, _D, _D, ctypes.c_int, ctypes.c_int, ctypes.c_int, _I32, ctypes.c_int, ctypes.c_int,
                    ctypes.c_uint64, ctypes.c_double, _D, _D, _I64]
_E.ctrl.restype = None
REASONS = {1: "SIG", 2: "TIME", 3: "SL", 4: "SL_GAP", 5: "TP", 6: "TP_GAP", 7: "TRAIL", 8: "TRAIL_GAP", 9: "LIQ", 10: "END",
           11: "SL_AMBIG"}
# exits: name -> (use_sig, sl_k, tp_k, trail_k, max_hold)   (k = multiples of ATR(14) at the signal bar)
EXITS = {"X0_SIG": (1, 0, 0, 0, 0), "X1_SIG_SL1": (1, 1, 0, 0, 0), "X2_SIG_SL2": (1, 2, 0, 0, 0), "X3_SIG_SL3": (1, 3, 0, 0, 0),
         "X4_SIG_TRAIL3": (1, 0, 0, 3, 0), "X5_SIG_SL1.5_TP3": (1, 1.5, 3, 0, 0), "X6_SIG_SL2_TP2": (1, 2, 2, 0, 0),
         "X7_HOLD1": (0, 0, 0, 0, 1), "X8_HOLD10_SL2": (0, 2, 0, 0, 10)}


def fees():
    f = json.loads((PROJ / "deploy" / "fees.json").read_text(encoding="utf-8"))
    return {"spot": float(f["rules"]["paper_spot_per_side"]), "futures": float(f["rules"]["paper_futures_taker_per_side"])}


class Bars:
    """contiguous float64 arrays of one market/timeframe"""

    def __init__(self, ts, o, h, l, c, atr):
        self.ts = np.ascontiguousarray(ts, dtype=np.int64)
        self.o, self.h, self.l, self.c = (np.ascontiguousarray(a, dtype=np.float64) for a in (o, h, l, c))
        self.atr = np.ascontiguousarray(atr, dtype=np.float64)
        self.n = len(self.o)


def _p(a, t):
    return a.ctypes.data_as(t)


def run(B, state, dirn, exit_name, gate=None, mmr=0.0, start=0, end=None, delay=0):
    use_sig, sl, tp, tr, mh = EXITS[exit_name]
    end = B.n if end is None else end
    state = np.ascontiguousarray(state, dtype=np.int8)
    g = None if gate is None else np.ascontiguousarray(gate, dtype=np.int8)
    cap = int(state.sum() // 1 + 16)                                         # trades <= onsets <= bars in state
    cap = min(cap, B.n + 16)
    ei = np.empty(cap, np.int32); xi = np.empty(cap, np.int32); rs = np.empty(cap, np.int8)
    pin = np.empty(cap); pout = np.empty(cap); mae = np.empty(cap); mfe = np.empty(cap)
    k = _E.bt(B.n, _p(B.o, _D), _p(B.h, _D), _p(B.l, _D), _p(B.c, _D), _p(B.atr, _D), _p(state, _I8),
              None if g is None else _p(g, _I8), int(dirn), use_sig, float(sl), float(tp), float(tr), int(mh), float(mmr),
              int(start), int(end), int(delay), cap, _p(ei, _I32), _p(xi, _I32), _p(rs, _I8), _p(pin, _D), _p(pout, _D),
              _p(mae, _D), _p(mfe, _D))
    if k < 0:
        raise RuntimeError("trade buffer overflow")
    return dict(ei=ei[:k], xi=xi[:k], reason=rs[:k], px_in=pin[:k], px_out=pout[:k], worst=mae[:k], best=mfe[:k])


def pnl(T, dirn, fee, fund=None, t_in=None, t_out=None):
    """gross = dir*(R-1), fee = f*(1+R), funding = dir * sum(rate*P_tau)/px_in over tau in (t_in, t_out], net = gross-fee-funding;
    liquidation: net = -1 - f - funding (the whole 1x isolated margin is lost, the entry fee was paid on top)."""
    R = T["px_out"] / T["px_in"]
    gross = dirn * (R - 1.0)
    fe = fee * (1.0 + R)
    fu = np.zeros(len(R))
    if fund is not None and len(R):
        tau, cum = fund                                                      # cum[k] = sum_{j<k} rate_j * P_j
        i0 = np.searchsorted(tau, t_in, side="right")
        i1 = np.searchsorted(tau, t_out, side="right")
        fu = dirn * (cum[i1] - cum[i0]) / T["px_in"]
    net = gross - fe - fu
    liq = T["reason"] == 9
    if liq.any():
        fe = np.where(liq, fee, fe)
        net = np.where(liq, -1.0 - fee - fu, net)
    mae = dirn * (T["worst"] / T["px_in"] - 1.0)
    mfe = dirn * (T["best"] / T["px_in"] - 1.0)
    return gross, fe, fu, net, mae, mfe


def control(B, cf, lo, hi, dirn, holds, reps, seed, fee):
    m = len(holds)
    h = np.ascontiguousarray(holds, dtype=np.int32)
    mu, sd, n = ctypes.c_double(), ctypes.c_double(), ctypes.c_int64()
    _E.ctrl(B.n, _p(B.o, _D), _p(cf, _D), int(lo), int(hi), int(dirn), _p(h, _I32), m, int(reps), ctypes.c_uint64(seed), float(fee),
            ctypes.byref(mu), ctypes.byref(sd), ctypes.byref(n))
    return mu.value, sd.value, n.value
