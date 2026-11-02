"""Independent verifier + scorer for PRED-1 (protocol logs/live_paper_lpt1_2026_10_29/pred1/PRED1_PROTOCOL_PREREGISTERED.md, section 4).
Written separately from src/live_paper/predict.py: it fetches the market data itself (plain requests to data-api.binance.vision), recomputes
a sample of forecasts with its own formulas (no look-ahead check), and scores every matured forecast against the official kline closes.
Outputs (logs/live_paper_lpt1_2026_10_29/pred1/): outcomes.csv (one row per forecast x model x horizon), metrics.csv, verify_output.txt
Usage: python src/audits/verify_pred1.py [--recompute 30]"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.stats import binomtest, norm

PROJ = Path(__file__).resolve().parents[2]
P = PROJ / "logs" / "live_paper_lpt1_2026_10_29" / "pred1"
URL = "https://data-api.binance.vision/api/v3/klines"
TF = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
FEE_RT = 2 * json.loads((PROJ / "deploy" / "fees.json").read_text())["rules"]["paper_spot_per_side"]   # spot round trip, deploy/fees.json
RES = []


def check(name, ok, msg=""):
    RES.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {msg}", flush=True)


def fetch(sym, tf, start, end):
    """official klines with open time in [start, end] (paged)"""
    out = []
    t = start
    while t <= end:
        r = requests.get(URL, params=dict(symbol=sym, interval=tf, startTime=t, endTime=end, limit=1000), timeout=15)
        r.raise_for_status()
        d = r.json()
        if not d:
            break
        out += d
        t = d[-1][0] + TF[tf]
        if len(d) < 1000:
            break
    return {int(x[0]): (float(x[4]), int(x[6])) for x in out}                 # open -> (close, close_time)


def own_forecasts(c):
    """the PRED-1 formulas written again from the protocol (log closes c, oldest first)"""
    r = [c[i] - c[i - 1] for i in range(1, len(c))]
    cT = c[-1]

    def ema_(x, n):
        a = 2.0 / (n + 1)
        y = x[0]
        out = [y]
        for v in x[1:]:
            y = a * v + (1 - a) * y
            out.append(y)
        return out
    m100 = sum(r[-100:]) / 100
    e10 = ema_(c[-200:], 10)
    e20 = ema_(c[-300:], 20)
    rr = r[-500:]
    x, y = rr[:-1], rr[1:]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    b = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / sum((xi - mx) ** 2 for xi in x)
    a = my - b * mx
    f = {}
    for h in range(1, 11):
        f.setdefault("M0_naive", []).append(cT)
        f.setdefault("M1_drift", []).append(cT + h * m100)
        f.setdefault("M2_ema_trend", []).append(cT + 0.5 * h * (e10[-1] - e10[-6]) / 5)
        f.setdefault("M3_mean_rev", []).append(cT + (e20[-1] - cT) * (1 - 0.9 ** h))
    last, s, path = r[-1], 0.0, []
    for _ in range(10):
        last = a + b * last
        s += last
        path.append(cT + s)
    f["M4_ar1"] = path
    f["M5_ensemble"] = [(f["M1_drift"][i] + f["M2_ema_trend"][i] + f["M3_mean_rev"][i] + f["M4_ar1"][i]) / 4 for i in range(10)]
    return f


def dm_test(d, lag):
    """Diebold-Mariano: mean of loss differential d (M0 loss - model loss) > 0, Newey-West variance with the given lag"""
    d = np.asarray(d, float)
    T = len(d)
    if T < 30:
        return float("nan"), 1.0
    u = d - d.mean()
    s = u @ u / T
    for j in range(1, lag + 1):
        s += 2 * (1 - j / (lag + 1)) * (u[j:] @ u[:-j]) / T
    if s <= 0:
        return float("nan"), 1.0
    t = d.mean() / math.sqrt(s / T)
    return t, float(norm.sf(t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recompute", type=int, default=30)
    a = ap.parse_args()
    lines = (P / "predictions.jsonl").read_bytes().splitlines()
    prev, ok_chain = "GENESIS", True
    recs = []
    for ln in lines:
        r = json.loads(ln)
        ok_chain &= r["prev"] == prev
        prev = hashlib.sha256(ln).hexdigest()
        recs.append(r)
    check("V1 hash chain of predictions.jsonl", ok_chain, f"{len(recs)} forecasts")
    bad_t = 0
    for r in recs:
        made = pd.Timestamp(r["utc"]).value // 10 ** 6
        bad_t += not (made >= r["base_open_ms"] + TF[r["tf"]] and all(t > r["base_open_ms"] for t in r["target_open_ms"]) and made < r["target_open_ms"][0] + TF[r["tf"]])
    check("V1 every forecast made after its base bar closed (no input from the future)", all(pd.Timestamp(r["utc"]).value // 10 ** 6 >= r["base_open_ms"] + TF[r["tf"]] for r in recs), "")
    print(f"[INFO] forecasts written after their first target had closed (network delay): {bad_t}; those target horizons are NOT scored")
    # V2: recompute a sample from independently fetched closed bars
    rng = np.random.default_rng(7)
    smp = rng.choice(len(recs), size=min(a.recompute, len(recs)), replace=False) if recs else []
    worst, nbad = 0.0, 0
    for i in smp:
        r = recs[i]
        k = fetch(r["sym"], r["tf"], r["base_open_ms"] - TF[r["tf"]] * (r["n_bars"] - 1), r["base_open_ms"])
        c = [math.log(k[t][0]) for t in sorted(k)]
        if len(c) != r["n_bars"]:
            nbad += 1
            continue
        f = own_forecasts(c)
        for m, v in f.items():
            e = max(abs(math.exp(x) / y - 1) for x, y in zip(v, r["pred"][m]))
            worst = max(worst, e)
            nbad += e > 1e-9
    check("V2 sampled forecasts recomputed from independently fetched closed bars", nbad == 0, f"{len(smp)} forecasts, max rel diff {worst:.1e}")
    # V3 outcomes
    now = pd.Timestamp.now(tz="UTC").value // 10 ** 6
    rows = []
    for (sym, tf), g in pd.DataFrame(recs).groupby(["sym", "tf"]):
        tmin = min(min(t) for t in g.target_open_ms)
        tmax = max(max(t) for t in g.target_open_ms)
        k = fetch(sym, tf, tmin, min(tmax, now))
        for _, r in g.iterrows():
            made = pd.Timestamp(r.utc).value // 10 ** 6
            for h, t in enumerate(r.target_open_ms, 1):
                if t not in k or k[t][1] > now:
                    continue
                if t + TF[tf] <= made:                                        # target already closed when the forecast was written: not scored
                    continue
                act = k[t][0]
                base = r.base_close
                lo, hi = r.band95[h - 1]
                for m in r.pred:
                    p = r.pred[m][h - 1]
                    rows.append(dict(sym=sym, tf=tf, base_open_ms=r.base_open_ms, h=h, model=m, base=base, pred=p, actual=act,
                                     err_bps=1e4 * math.log(act / p), dir_pred=0 if abs(p / base - 1) < 1e-9 else np.sign(p - base), dir_act=np.sign(act - base),
                                     in_band=int(lo <= act <= hi)))
    O = pd.DataFrame(rows)
    O.to_csv(P / "outcomes.csv", index=False)
    if not len(O):
        print("no matured forecast yet"); return
    M = []
    for (tf, m, h), g in O.groupby(["tf", "model", "h"]):
        base = O[(O.tf == tf) & (O.model == "M0_naive") & (O.h == h)].set_index(["sym", "base_open_ms"]).err_bps
        e = g.set_index(["sym", "base_open_ms"]).err_bps
        j = e.index.intersection(base.index)
        d = (base.loc[j] ** 2 - e.loc[j] ** 2).values
        dm_t, dm_p = dm_test(d, h) if m != "M0_naive" else (float("nan"), 1.0)
        dd = g[(g.dir_pred != 0) & (g.dir_act != 0)]
        hits = int((dd.dir_pred == dd.dir_act).sum())
        M.append(dict(tf=tf, model=m, h=h, n=len(g), mae_bps=g.err_bps.abs().mean(), rmse_bps=math.sqrt((g.err_bps ** 2).mean()),
                      skill_vs_M0=1 - (e.loc[j] ** 2).mean() / (base.loc[j] ** 2).mean() if len(j) else float("nan"), dm_t=dm_t, dm_p=dm_p,
                      dir_n=len(dd), dir_hit=hits / len(dd) if len(dd) else float("nan"),
                      dir_p=binomtest(hits, len(dd), 0.5, alternative="greater").pvalue if len(dd) else 1.0,
                      band_coverage=g.in_band.mean(),
                      # direction accuracy a trade on this forecast would need to beat the round-trip fee: p* = 0.5 + fee / (2 E|move|)
                      fee_hurdle=min(1.0, 0.5 + FEE_RT / (2 * (np.abs(np.log(g.actual / g.base)).mean() + 1e-12)))))
    M = pd.DataFrame(M)
    t = M.model != "M0_naive"
    M["dm_q"] = np.nan
    M.loc[t, "dm_q"] = bh(M.loc[t, "dm_p"].fillna(1).values)
    M["USEFUL"] = t & (M.n >= 300) & (M.skill_vs_M0 > 0) & (M.dm_q <= 0.05) &         (M.dir_hit > M.fee_hurdle)
    M.to_csv(P / "metrics.csv", index=False)
    s_ = M[M.h.isin([1, 5, 10])].pivot_table(index=["tf", "model"], columns="h", values=["skill_vs_M0", "dir_hit"]).round(3)
    print(s_.to_string())
    print("band coverage by tf:", M[M.model == "M0_naive"].groupby("tf").band_coverage.mean().round(3).to_dict())
    print(f"matured outcome rows {len(O)}; USEFUL models: {int(M.USEFUL.sum())}")
    print(f"\n{sum(RES)}/{len(RES)} integrity checks PASS")


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(q, 1)
    return out


if __name__ == "__main__":
    main()
