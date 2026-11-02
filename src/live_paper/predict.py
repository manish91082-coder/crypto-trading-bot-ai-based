"""PRED-1 (2026-10-29): live price forecasts of the next 10 bar closes on several timeframes, written BEFORE those bars exist.
Protocol: logs/live_paper_lpt1_2026_10_29/pred1/PRED1_PROTOCOL_PREREGISTERED.md. Read-only public data (Binance spot mirror data-api.binance.vision).
At every bar close of every timeframe, for every symbol, from the CLOSED bars only (log closes c, log returns r):
  M0 naive        c_T                                             (random walk: the benchmark)
  M1 drift        c_T + h * mean(r over the last 100 bars)
  M2 ema_trend    c_T + 0.5 * h * slope, slope = (EMA10_T - EMA10_{T-5}) / 5      (log scale, damped)
  M3 mean_rev     c_T + (EMA20_T - c_T) * (1 - 0.9^h)
  M4 ar1          OLS r_t = a + b r_{t-1} on the last 500 returns, iterated h steps
  M5 ensemble     mean of M1..M4 (log scale)
  M6 selector     the model M0..M5 with the lowest squared error over the last 200 MATURED forecasts of that symbol, timeframe
                  and horizon (its own record); M0 until 30 have matured  (an online "learning" model, scored out of sample)
  interval        95 % band c_T +- 1.96 * sd(r over the last 100 bars) * sqrt(h)  (around M0)
Each forecast is one line of predictions.jsonl (hash-chained: 'prev' = sha256 of the previous line) with the data sha of the closes used.
Usage: python src/live_paper/predict.py [--syms BTCUSDT,ETHUSDT,...] [--tfs 1m,5m,15m,1h,4h,1d]"""
import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402

OUT = lpt.LOG / "pred1"
TFMS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
H = 10
MODELS = ["M0_naive", "M1_drift", "M2_ema_trend", "M3_mean_rev", "M4_ar1", "M5_ensemble", "M6_selector"]
VERSION = "PRED1-v1"


def ema(x, n):
    a = 2.0 / (n + 1)
    y = np.empty(len(x))
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = a * x[i] + (1 - a) * y[i - 1]
    return y


def forecasts(c):
    """c: log closes of CLOSED bars (oldest first). returns dict model -> array of H log forecasts, and sigma"""
    r = np.diff(c)
    cT = c[-1]
    h = np.arange(1, H + 1)
    out = {"M0_naive": np.full(H, cT)}
    out["M1_drift"] = cT + h * r[-100:].mean()
    e10 = ema(c[-200:], 10)
    out["M2_ema_trend"] = cT + 0.5 * h * (e10[-1] - e10[-6]) / 5
    e20 = ema(c[-300:], 20)
    out["M3_mean_rev"] = cT + (e20[-1] - cT) * (1 - 0.9 ** h)
    y, x = r[-500:][1:], r[-500:][:-1]
    X = np.c_[np.ones(len(x)), x]
    a, b = np.linalg.lstsq(X, y, rcond=None)[0]
    path, last = [], r[-1]
    for _ in range(H):
        last = a + b * last
        path.append(last)
    out["M4_ar1"] = cT + np.cumsum(path)
    out["M5_ensemble"] = np.mean([out[m] for m in ("M1_drift", "M2_ema_trend", "M3_mean_rev", "M4_ar1")], axis=0)
    sig = float(r[-100:].std(ddof=1))
    return out, sig, dict(ar1_a=float(a), ar1_b=float(b))


class Selector:
    """M6: per (sym, tf, h) keeps the squared errors of the last 200 matured forecasts of M0..M5 from its own record"""

    def __init__(self):
        self.pending = defaultdict(list)                                     # (sym, tf) -> [(target_open, h, {model: logpred})]
        self.err = defaultdict(lambda: deque(maxlen=200))                    # (sym, tf, h) -> deque of {model: sq err}

    def update(self, sym, tf, closed_open_ms, closed_logc):
        idx = {t: v for t, v in zip(closed_open_ms, closed_logc)}
        keep = []
        for (t, h, p) in self.pending[(sym, tf)]:
            if t in idx:
                self.err[(sym, tf, h)].append({m: (p[m] - idx[t]) ** 2 for m in p})
            elif t > closed_open_ms[-1]:
                keep.append((t, h, p))
        self.pending[(sym, tf)] = keep

    def pick(self, sym, tf, h):
        d = self.err[(sym, tf, h)]
        if len(d) < 30:
            return "M0_naive", len(d)
        tot = {m: sum(x[m] for x in d) for m in d[0]}
        return min(tot, key=lambda m: (tot[m], m)), len(d)

    def add(self, sym, tf, target_opens, preds):
        for h in range(1, H + 1):
            self.pending[(sym, tf)].append((target_opens[h - 1], h, {m: float(preds[m][h - 1]) for m in MODELS[:6]}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--syms", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT")
    ap.add_argument("--tfs", default="1m,5m,15m,1h,4h,1d")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    syms, tfs = a.syms.split(","), a.tfs.split(",")
    sel = Selector()
    done = {}
    print(f"PRED start {lpt.iso()} syms {syms} tfs {tfs}", flush=True)
    while True:
        now = lpt.now_ms()
        for tf in tfs:
            ms = TFMS[tf]
            last_closed_open = (now // ms) * ms - ms                        # open time of the most recent closed bar
            if now - (last_closed_open + ms) < 2_000:
                continue                                                     # wait 2 s after the close so the bar is final
            for sym in syms:
                if done.get((tf, sym)) == last_closed_open:
                    continue
                try:
                    k = lpt.klines("spot", sym, tf, 600)
                    k = k[k.t <= last_closed_open]                           # CLOSED bars only (the open bar is dropped)
                    if not len(k) or int(k.t.iloc[-1]) != last_closed_open:
                        continue
                    c = np.log(k.c.values.astype(float))
                    sel.update(sym, tf, k.t.values.astype(np.int64), c)
                    preds, sig, par = forecasts(c)
                    picks, n_m = [], 0
                    m6 = np.empty(H)
                    for h in range(1, H + 1):
                        m, n_m = sel.pick(sym, tf, h)
                        picks.append(m)
                        m6[h - 1] = preds[m][h - 1]
                    preds["M6_selector"] = m6
                    tg = [last_closed_open + ms * h for h in range(1, H + 1)]
                    if lpt.now_ms() >= tg[0] + ms - 1_000:                   # PRED-1 change 3: too late (network), the next bar is closed -> skip
                        print(f"SKIP {lpt.iso()} {sym} {tf} late forecast not written", flush=True)
                        done[(tf, sym)] = last_closed_open
                        continue
                    sel.add(sym, tf, tg, preds)
                    rec = dict(utc=lpt.iso(), version=VERSION, sym=sym, tf=tf, base_open_ms=last_closed_open, base_close=float(k.c.iloc[-1]),
                               target_open_ms=tg, pred={m: [float(np.exp(v)) for v in preds[m]] for m in MODELS},
                               band95=[[float(np.exp(c[-1] - 1.96 * sig * np.sqrt(h))), float(np.exp(c[-1] + 1.96 * sig * np.sqrt(h)))]
                                       for h in range(1, H + 1)],
                               sigma=sig, params=par, m6_picks=picks, m6_matured=n_m,
                               data_sha=hashlib.sha256(k.c.values.astype(float).tobytes()).hexdigest()[:16], n_bars=len(k))
                    lpt.append_chain(OUT / "predictions.jsonl", rec)
                    done[(tf, sym)] = last_closed_open
                except Exception as e:                                       # noqa: BLE001
                    print(f"WARN {lpt.iso()} {sym} {tf} {type(e).__name__}: {str(e)[:120]}", flush=True)
        time.sleep(2)


if __name__ == "__main__":
    main()
