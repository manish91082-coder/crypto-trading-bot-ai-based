"""
Independent verifier for logs/strategy_1d_step19_largecap/claims.json.
V1 protocol hash as locked; G0 reproduction claim present and < 1e-12.
V2 universe U re-derived from RAW 1d files (30-day mean USDT volume, liquidity >= $2M, >= 120 candles, top 20/day).
V3 relative 5-day labels re-derived from RAW opens (median of the 30 reference coins), AUCs recomputed.
V4 AI, CONTROL, EW_U and BTC_HOLD re-simulated with separate code.
V5 gates and decision recomputed.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics"):
    sys.path.insert(0, str(p))
import core_rows_1d as CR
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13

D = S13.OUT.parent / "strategy_1d_step19_largecap"
C = json.loads((D / "claims.json").read_text())
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30")


def auc(y, p):
    r = rankdata(p)
    n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def sim(rows, n, keep, opn, cls, last, cost):
    day = {d: list(g.sort_values(["score", "symbol"], ascending=[False, True]).symbol) for d, g in rows.groupby("date")}
    cash, held, ps, pb, curve, rets, months = 10000.0, {}, [], [], [], [], []

    def out(s, price):
        nonlocal cash
        u, c, ed = held.pop(s)
        v = u * price * (1 - cost)
        cash += v
        rets.append(v / c - 1)
        months.append(ed.strftime("%Y-%m"))

    for k, d in enumerate(pd.date_range(START, END, freq="D")):
        for s in [s for s in held if d > last[s]]:
            out(s, cls[s][last[s]])
        for s in ps:
            if s in held:
                out(s, opn[s][d])
        e0 = cash + sum(u * opn[s][d] for s, (u, c, ed) in held.items())
        for s in pb:
            if s in held or len(held) >= n or d > last[s]:
                continue
            a = min(0.8 * e0 / n, cash / (1 + cost))
            if a < 10:
                continue
            cash -= a * (1 + cost)
            held[s] = (a / opn[s][d], a * (1 + cost), d)
        curve.append(cash + sum(u * cls[s][d] for s, (u, c, ed) in held.items()))
        ps, pb = [], []
        if k % 5:
            continue
        r = day.get(d, [])
        pos = {s: i + 1 for i, s in enumerate(r)}
        kept = [s for s in held if pos.get(s, 10 ** 9) <= keep]
        ps = [s for s in held if s not in kept]
        pb = [s for s in r[:n] if s not in held][:n - len(kept)]
    for s in list(held):
        out(s, cls[s][min(END, last[s])])
    eq = np.r_[10000.0, curve]
    dd = float(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max())
    ser = pd.Series(curve, index=pd.date_range(START, END))
    ye = ser.resample("YE").last()
    yr = (ye / ye.shift(1).fillna(10000.0) - 1) * 100
    cagr = (cash / 10000) ** (365.25 / (END - START).days) - 1
    return dict(final=cash, dd=dd * 100, cagr=cagr * 100, calmar=cagr / dd, trades=len(rets), years_pos=int((yr > 0).sum()))


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / "STEP19_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    assert C["G0_max_diff_vs_step15"] < 1e-12
    print(f"[V1 PASS] protocol hash as locked; G0 reproduction of Step 15 B predictions: max diff {C['G0_max_diff_vs_step15']:.1e}")

    split = pd.read_csv(S13.OUT.parent / "strategy_1d_step14_rule" / "coin_split.csv")
    B = set(split[split.half == "B_confirm"].symbol)
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", END)
    last = {**last_k, **last_n}
    cand = list(data_k) + sorted(B)
    raw = {s: pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"]) for s in cand}
    rows = []
    for s in cand:
        d = raw[s][raw[s].timestamp <= min(last[s], END)].reset_index(drop=True)
        usd = (d.volume * d.close).rolling(30, min_periods=30).mean()
        i = np.arange(len(d))
        ok = (d.timestamp >= START) & (usd >= 2_000_000) & (i + 1 >= 120) & (i >= 60)
        rows.append(pd.DataFrame(dict(symbol=s, date=d.timestamp[ok], usd=usd[ok], idx=i[ok])))
    R = pd.concat(rows, ignore_index=True)
    R["rk"] = R.groupby("date").usd.rank(ascending=False, method="first")
    Uv = R[R.rk <= 20]
    U = pd.read_csv(D / "universe_U.csv", parse_dates=["date"])
    a = set(zip(Uv.symbol, Uv.date))
    b = set(zip(U.symbol, U.date))
    assert a == b, (len(a - b), len(b - a))
    print(f"[V2 PASS] universe re-derived from raw files: {len(a)} coin-days identical")

    ref = []
    for s in data_k:
        d = raw[s][raw[s].timestamp <= min(last_k[s], END)].reset_index(drop=True)
        o = d.open.values
        i = np.arange(len(d))
        ok = (i + 6 <= len(d) - 1) & (i >= 60)
        ref.append(pd.DataFrame(dict(date=d.timestamp.values[ok], f=o[i[ok] + 6] / o[i[ok] + 1] - 1)))
    med = pd.concat(ref).groupby("date").f.median()
    for lab in ("AI", "CONTROL"):
        P = pd.read_csv(D / f"U_{lab}_predictions.csv", parse_dates=["date"]).merge(Uv[["symbol", "date", "idx"]], on=["symbol", "date"])
        f = []
        for s, dd, i in zip(P.symbol, P.date, P.idx):
            d = raw[s]
            lo = int(np.searchsorted(d.timestamp.values, np.datetime64(min(last[s], END)), side="right")) - 1
            f.append(d.open.values[i + 6] / d.open.values[i + 1] - 1 if i + 6 <= lo else np.nan)
        P["f"] = f
        y = np.where(P.f.isna() | P.date.map(med).isna(), np.nan, (P.f - P.date.map(med) > 0).astype(float))
        same = (np.isnan(y) & P.label_r5.isna()) | (y == P.label_r5)
        assert same.all(), (lab, int((~same).sum()))
        m = ~np.isnan(y)
        av = auc(y[m].astype(int), P.score.values[m])
        assert abs(av - C[f"{lab}_skill_U"]["auc"]) < 1e-9, (lab, av)
        print(f"[V3 PASS] {lab}: labels re-derived from raw opens ({int(m.sum())} rows), AUC in U {av:.4f}")

    opn = {s: raw[s].set_index("timestamp").open.to_dict() for s in set(U.symbol) | {"BTCUSDT"}}
    cls = {s: raw[s].set_index("timestamp").close.to_dict() for s in set(U.symbol) | {"BTCUSDT"}}
    for s in opn:                                         # frozen price after delisting (same rule as the pipeline)
        if last[s] < END:
            c = cls[s][last[s]]
            for d in pd.date_range(last[s] + pd.Timedelta(days=1), END):
                opn[s][d], cls[s][d] = c, c
    res = {}
    for name, n, keep, cost in (("AI", 5, 10, 0.0025), ("CONTROL", 5, 10, 0.0025), ("EW_U", 20, 20, 0.0025)):
        src = "AI" if name in ("AI", "EW_U") else "CONTROL"
        P = pd.read_csv(D / f"U_{src}_predictions.csv", parse_dates=["date"])[["symbol", "date", "score"]]
        if name == "EW_U":
            P["score"] = 1.0
        r = sim(P, n, keep, opn, cls, last, cost)
        c = C["portfolio"][name]
        assert abs(r["final"] - c["final"]) < 0.01 and abs(r["dd"] - c["max_dd_pct"]) < 0.01 and r["trades"] == c["trades"], (name, r["final"], c["final"])
        res[name] = r
        print(f"[V4 PASS] {name}: final {r['final']:.2f}, MaxDD {r['dd']:.2f}%, trades {r['trades']}, positive years {r['years_pos']}")
    b0 = opn["BTCUSDT"][START]
    units = 8000 / b0
    cash = 10000 - 8000 * 1.0025
    curve = np.array([cash + units * cls["BTCUSDT"][d] for d in pd.date_range(START, END)])
    final = cash + units * cls["BTCUSDT"][END] * (1 - 0.0025)
    eq = np.r_[10000.0, curve]
    dd = float(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max()) * 100
    assert abs(final - C["portfolio"]["BTC_HOLD"]["final"]) < 0.01 and abs(dd - C["portfolio"]["BTC_HOLD"]["max_dd_pct"]) < 0.01
    print(f"[V4 PASS] BTC_HOLD: final {final:.2f}, MaxDD {dd:.2f}%")

    pf = C["portfolio"]
    ai = pf["AI"]
    rec = dict(G0=C["G0_max_diff_vs_step15"] < 1e-12,
               G1_skill=C["AI_skill_U"]["ci_low"] > 0.5 and C["AI_skill_U"]["auc"] > C["CONTROL_skill_U"]["auc"],
               G2a_cagr=res["AI"]["cagr"] > 0,
               G2b_calmar=all(ai["calmar"] > pf[k]["calmar"] for k in ("EW_U", "BTC_HOLD", "CONTROL", "SIMPLE")),
               G2c_trade_ci=ai["trade_ci_low_pct"] > 0, G2d_years=res["AI"]["years_pos"] >= 4,
               G2e_cost040=pf["AI_cost040"]["cagr_pct"] > 0, G2f_maxdd=res["AI"]["dd"] < 50)
    g = C["gates"]
    assert all(bool(rec[k]) == g[k] for k in rec), {k: (rec[k], g[k]) for k in rec}
    g2 = all(v for k, v in rec.items() if k.startswith("G2"))
    want = "INVALID" if not rec["G0"] else "PASS" if rec["G1_skill"] and g2 else "PARTIAL_SKILL_RULE_FAILS" if rec["G1_skill"] else "FAIL"
    assert g["decision"] == want
    print(f"[V5 PASS] gates recomputed -> {g['decision']}")


if __name__ == "__main__":
    main()
