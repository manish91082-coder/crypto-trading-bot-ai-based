"""BTC-ALLTF-R2 (2026-10-29): stop-loss exits re-tested WITH re-entry (protocol section 8, audit F6). For every L1 config of every
BTC job whose exit has a stop / target / trail (X1..X6), the same rule, direction and exit are run with engine_r2.bt2(reentry=1):
after a stop / target / trail exit the position is re-opened at the next open if the rule state is still on. Compared on daily
mark-to-market with (a) the locked run without re-entry and (b) the same rule's X0 (signal exit, no stop).
--selftest: bt2(reentry=0) must equal the locked engine.bt trade for trade on a sample (code check, no result read).
Output: <RUN>/reentry/reentry.parquet
Usage: python src/btc_alltf_r2/reentry.py --run <R2 RUN dir> [--jobs spot/1d,...] [--selftest]"""
import argparse
import ctypes
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402
import rules                                                                  # noqa: E402
import study                                                                  # noqa: E402

E = K.E
_R = ctypes.CDLL(str(Path(__file__).resolve().parent / "engine_r2.dll"))
_D, _I8, _I32 = ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_int8), ctypes.POINTER(ctypes.c_int32)
_R.bt2.argtypes = [ctypes.c_int, _D, _D, _D, _D, _D, _I8, _I8, ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_double,
                   ctypes.c_double, ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                   _I32, _I32, _I8, _D, _D, _D, _D]
_R.bt2.restype = ctypes.c_int


def run2(B, state, dirn, exit_name, gate=None, mmr=0.0, reentry=1):
    use_sig, sl, tp, tr, mh = E.EXITS[exit_name]
    state = np.ascontiguousarray(state, dtype=np.int8)
    g = None if gate is None else np.ascontiguousarray(gate, dtype=np.int8)
    cap = B.n + 16
    ei = np.empty(cap, np.int32); xi = np.empty(cap, np.int32); rs = np.empty(cap, np.int8)
    pin = np.empty(cap); pout = np.empty(cap); mae = np.empty(cap); mfe = np.empty(cap)
    p = lambda a, t: a.ctypes.data_as(t)                                    # noqa: E731
    k = _R.bt2(B.n, p(B.o, _D), p(B.h, _D), p(B.l, _D), p(B.c, _D), p(B.atr, _D), p(state, _I8), None if g is None else p(g, _I8),
               int(dirn), use_sig, float(sl), float(tp), float(tr), int(mh), float(mmr), 0, B.n, 0, int(reentry), cap,
               p(ei, _I32), p(xi, _I32), p(rs, _I8), p(pin, _D), p(pout, _D), p(mae, _D), p(mfe, _D))
    if k < 0:
        raise RuntimeError("trade buffer overflow")
    return dict(ei=ei[:k], xi=xi[:k], reason=rs[:k], px_in=pin[:k], px_out=pout[:k], worst=mae[:k], best=mfe[:k])


def load(market, tf):
    b = study.load_bars(market, tf)
    mm, ix = study.build_states(market, tf, b)
    atr = np.load(study.STATES / f"{market}_{tf}_atr14.npy")
    B = E.Bars(b.ts.values, b.open.values, b.high.values, b.low.values, b.close.values, atr)
    rule_meta = {r["id"]: r for r in rules.REG}
    C = study.enumerate_configs(market, ix, rule_meta)
    return B, mm, ix, C


def job(run, market, tf, selftest):
    t0 = time.time()
    B, mm, ix, C = load(market, tf)
    ts = B.ts
    fee = E.fees()[market]
    mmr = study.CFG["futures_mmr"] if market == "futures" else 0.0
    fund, _ = study.funding_tables(market, ts)
    d1 = pd.read_parquet(K.PROJ / f"data/derived/btc_alltf/bars/{market}_1d.parquet", columns=["ts", "close"])
    Z = None if selftest else np.load(K.DER / "mtm" / f"{market}_{tf}.npz")
    day0 = int(d1.ts.iloc[0] // K.DAY)
    nd = int(K.ms(K.CFG["btc_grid_end"]) // K.DAY - day0)
    close = pd.Series(d1.close.values, index=d1.ts.values // K.DAY - day0).reindex(np.arange(nd)).values
    row = {} if selftest else {int(c): i for i, c in enumerate(Z["cfg"])}
    allc = pd.read_parquet(K.R1RUN / market / tf / "all_configs.parquet", columns=["cfg", "name", "dup_of"])
    canon = dict(zip(allc.cfg, np.where(allc.dup_of >= 0, allc.dup_of, allc.cfg)))
    byname = dict(zip(allc.name, allc.cfg))
    nxt = np.r_[ts[1:], K.ms(K.CFG["btc_grid_end"])]
    barlen = nxt - ts
    ex_set = set(K.CFG["reentry"]["exits"])
    cfgs = [c for c in C if c["layer"] == "L1" and c["exit"] in ex_set]
    if selftest:
        cfgs = cfgs[::max(1, len(cfgs) // 40)]
    rows, bad = [], 0
    for c in cfgs:
        st = study.state_of(c, mm)
        if selftest:
            a_ = E.run(B, st, c["dir"], c["exit"], mmr=mmr)
            b_ = run2(B, st, c["dir"], c["exit"], mmr=mmr, reentry=0)
            same = all(np.array_equal(a_[x], b_[x]) for x in a_)
            bad += not same
            continue
        T = run2(B, st, c["dir"], c["exit"], mmr=mmr, reentry=1)
        n = len(T["ei"])
        rec = dict(market=market, tf=tf, cfg=c["cfg"], name=c["name"], rule=c["rule"], dlabel=c["dlabel"], side=c["side"], exit=c["exit"], n_re=n)
        if n:
            t_in, t_out = ts[T["ei"]], ts[T["xi"]]
            t_f = np.where(T["reason"] == 10, t_out + barlen[T["xi"]], t_out)
            _, _, _, net, _, _ = E.pnl(T, c["dir"], fee, fund, t_in, t_f)
            add = np.where(np.isin(T["reason"], (3, 5, 7, 9, 11)), barlen[T["xi"]] // 2, np.where(T["reason"] == 10, barlen[T["xi"]] - 1, 0))
            L, Xp, _ = K.mtm(np.zeros(n, np.int64), t_in, t_out + add, T["px_in"], net, np.full(n, float(c["dir"])), close, day0, 1, nd)
            P = K.perf(np.expm1(L[0]))
            rec.update({f"{k}_re": v for k, v in P.items() if k in ("total", "cagr", "sharpe", "maxdd")}, expo_re=float(Xp.sum() / nd),
                       reentries=int((np.isin(T["reason"][:-1], (3, 4, 5, 6, 7, 8, 11)) & (T["ei"][1:] == T["xi"][:-1] + 1)).sum()))
        for tag, nm in (("no", c["name"]), ("x0", c["name"].replace(f"|{c['exit']}|", "|X0_SIG|"))):
            cid = canon.get(byname.get(nm, -1), -1)
            if cid in row:
                i = row[cid]
                P = K.perf(np.expm1(Z["L"][i].astype(np.float64)))
                rec.update({f"{k}_{tag}": v for k, v in P.items() if k in ("total", "cagr", "sharpe", "maxdd")},
                           **{f"expo_{tag}": float(Z["X"][i].astype(np.float64).sum() / nd)})
        rows.append(rec)
    if selftest:
        print(f"selftest {market} {tf}: {len(cfgs)} configs, bt2(reentry=0) == engine.bt: {len(cfgs) - bad}/{len(cfgs)}", flush=True)
        return None, bad
    print(f"reentry {market} {tf}: {len(rows)} configs, {time.time() - t0:.0f}s", flush=True)
    return pd.DataFrame(rows), 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="")
    ap.add_argument("--jobs", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    jobs = [j.split("/") for j in a.jobs.split(",")] if a.jobs else [(m, tf) for m in ("spot", "futures") for tf in K.CFG["r1_jobs"][m]]
    outs, bad = [], 0
    for m, tf in jobs:
        D, b = job(a.run, m, tf, a.selftest)
        bad += b
        if D is not None:
            outs.append(D)
            od = Path(a.run) / "reentry"
            od.mkdir(parents=True, exist_ok=True)
            D.to_parquet(od / f"reentry_{m}_{tf}.parquet", index=False)
    if a.selftest:
        print("SELFTEST", "PASS" if bad == 0 else f"FAIL ({bad})")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
