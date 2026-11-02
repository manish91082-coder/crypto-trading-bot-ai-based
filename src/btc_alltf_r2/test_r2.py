"""BTC-ALLTF-R2 (2026-10-29): ground-level tests of the R2 helpers, on synthetic data with hand-computable answers, run
before the protocol lock. Output: logs/btc_alltf_r2_2026_10_29/test_r2_output.txt (via stdout redirect).
Usage: python src/btc_alltf_r2/test_r2.py"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402

RES = []


def check(name, ok, detail=""):
    RES.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def brute_mtm(trades, C, day0, nd):
    """day-by-day valuation written independently: equity of the trade marked at every day close, the exit day takes the rest"""
    L = np.zeros(nd)
    X = np.zeros(nd)
    N = np.zeros(nd)
    Cf = C.copy()
    for i in range(1, nd):
        if not np.isfinite(Cf[i]):
            Cf[i] = Cf[i - 1]
    for (t_in, t_out, px, net, d) in trades:
        a, b = t_in // K.DAY - day0, t_out // K.DAY - day0
        N[a] += 1
        prev = 1.0
        for day in range(a, b):
            v = max(1 + d * (Cf[day] / px - 1), 1e-6)
            L[day] += np.log(v) - np.log(prev)
            prev = v
        L[b] += np.log1p(max(net, -0.999999)) - np.log(prev)
        # exposure: walk minute by minute would be slow; split exactly by day boundaries
        t = t_in
        while t < t_out:
            e = min(t_out, (t // K.DAY + 1) * K.DAY)
            X[t // K.DAY - day0] += (e - t) / K.DAY
            t = e
    return L, X, N


def t_mtm():
    rng = np.random.default_rng(7)
    day0, nd = 20000, 60
    C = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, nd)))
    C[17] = np.nan                                                            # a missing day close
    for d in (1, -1):
        trades = []
        t = (day0 + 1) * K.DAY + 3_600_000
        while t < (day0 + nd - 8) * K.DAY:
            hold = int(rng.integers(1, 6 * K.DAY))
            px = 100 * np.exp(rng.normal(0, 0.2))
            net = float(rng.normal(0.01, 0.1))
            trades.append((t, t + hold, px, net, d))
            t = t + hold + int(rng.integers(0, 2 * K.DAY))
        k = np.zeros(len(trades), np.int64)
        ti = np.array([x[0] for x in trades]); to = np.array([x[1] for x in trades])
        px = np.array([x[2] for x in trades]); net = np.array([x[3] for x in trades]); dr = np.full(len(trades), float(d))
        L, X, N = K.mtm(k, ti, to, px, net, dr, C, day0, 1, nd)
        Lb, Xb, Nb = brute_mtm(trades, C, day0, nd)
        check(f"mtm dir {d:+d}: daily log returns equal the brute force ({len(trades)} trades)", np.allclose(L[0], Lb, atol=1e-12),
              f"max diff {np.abs(L[0] - Lb).max():.2e}")
        check(f"mtm dir {d:+d}: sum equals sum log(1+net)", abs(L[0].sum() - np.log1p(net).sum()) < 1e-10)
        check(f"mtm dir {d:+d}: time in position per day equals the brute force", np.allclose(X[0], Xb, atol=1e-12))
        check(f"mtm dir {d:+d}: entries per day", np.array_equal(N[0], Nb))
    # two configs interleaved in one call
    k = np.array([0, 1, 0, 1])
    ti = (day0 + np.array([1, 2, 5, 9])) * K.DAY
    to = ti + np.array([3, 1, 2, 0]) * K.DAY + 1000
    L, X, N = K.mtm(k, ti, to, np.full(4, 100.0), np.array([0.1, -0.05, 0.02, 0.03]), np.ones(4), np.full(nd, 100.0), day0, 2, nd)
    check("mtm: two configs kept apart", abs(L[0].sum() - np.log(1.1 * 1.02)) < 1e-12 and abs(L[1].sum() - np.log(0.95 * 1.03)) < 1e-12)


def t_fill_time():
    r = np.array([1, 2, 3, 4, 5, 9, 10, 11])
    f = K.fill_time(np.zeros(8, np.int64), r, 3_600_000)
    check("fill_time: open fills at the open, touches mid-bar, END at the bar end",
          list(f) == [0, 0, 1_800_000, 0, 1_800_000, 1_800_000, 3_599_999, 1_800_000])


def t_nw():
    rng = np.random.default_rng(3)
    x = np.convolve(rng.normal(0.05, 1, 3000), np.ones(5) / 5, mode="valid")
    t, p, lag = K.nw_t(x)
    # independent: long-run variance from the Bartlett-weighted autocovariance matrix form
    T = len(x)
    u = x - x.mean()
    G = np.array([u[j:] @ u[:T - j] / T for j in range(lag + 1)])
    w = np.r_[1.0, 2 * (1 - np.arange(1, lag + 1) / (lag + 1))]
    lrv = (w * G).sum()
    t2 = x.mean() / np.sqrt(lrv / T)
    check("nw_t equals the matrix-form Newey-West", abs(t - t2) < 1e-10, f"t={t:.4f} lag={lag}")
    check("nw lag rule floor(4*(T/100)^(2/9))", K.nw_lag(2465) == 8 and K.nw_lag(100) == 4)
    # under the null, the NW t keeps ~5 % one-sided size on autocorrelated data (not a proof, a sanity check)
    rej = 0
    for s in range(400):
        z = np.convolve(np.random.default_rng(100 + s).normal(0, 1, 1504), np.ones(5) / 5, mode="valid")
        rej += K.nw_t(z)[1] <= 0.05
    check("nw_t size under the null about 5 %", 0.02 <= rej / 400 <= 0.09, f"{rej}/400")


def t_bh():
    p = np.array([0.01, 0.04, 0.03, 0.005, 0.5, 0.2])
    q = K.bh(p)
    # by hand: sorted 0.005,0.01,0.03,0.04,0.2,0.5 -> *6/rank: 0.03,0.03,0.06,0.06,0.24,0.5 -> monotone from the top
    exp = {0.005: 0.03, 0.01: 0.03, 0.03: 0.06, 0.04: 0.06, 0.2: 0.24, 0.5: 0.5}
    check("bh by hand", all(abs(q[i] - exp[p[i]]) < 1e-12 for i in range(len(p))), str(np.round(q, 4)))


def t_perf():
    r = np.r_[np.full(365, 0.001), -0.5, np.full(10, 0.0)]
    P = K.perf(r)
    eq = 1.001 ** 365 * 0.5
    check("perf total / maxdd", abs(P["total"] - (eq - 1)) < 1e-12 and abs(P["maxdd"] - 0.5) < 1e-12)
    check("perf cagr", abs(P["cagr"] - (eq ** (365 / 376) - 1)) < 1e-12)


def main():
    t_mtm()
    t_fill_time()
    t_nw()
    t_bh()
    t_perf()
    print(f"\n{sum(RES)}/{len(RES)} PASS")
    sys.exit(0 if all(RES) else 1)


if __name__ == "__main__":
    main()
