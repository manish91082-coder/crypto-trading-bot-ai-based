"""
Independent verifier for logs/strategy_1d_step22_pre2020/claims.json.
V1 protocol hash as locked; frozen model SHA = Step 16 ledger SHA; G0 reproduction claims.
V2 coin selection and universe U re-derived from RAW 2017-19 1d files (30-day mean USDT volume >= $2M, >= 120 candles,
   top 20/day, 2018-02-01..2019-12-31).
V3 R5 labels re-derived from RAW opens (median of the reference coins), AUCs recomputed (Mann-Whitney).
V4 AI_100_none, AI_100_b10, CONTROL_100_b10 and BTC_HOLD re-simulated with separate code.
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
import step13_unseen_coins_1d as S13
from config import DATA_DIR, LOGS_DIR

D = LOGS_DIR / "strategy_1d_step22_pre2020"
PRE = DATA_DIR / "universe_pre2020"
C = json.loads((D / "claims.json").read_text())
START, END = pd.Timestamp("2018-02-01"), pd.Timestamp("2019-12-31")


def auc(y, p):
    r = rankdata(p)
    n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def sim(rows, invest, brk, opn, cls, last, cost=0.0025, n=5, keep=10):
    day = {d: list(g.sort_values(["score", "symbol"], ascending=[False, True]).symbol) for d, g in rows.groupby("date")}
    cash, held, ps, pb, curve, top, block, trip = 10000.0, {}, [], [], [], 10000.0, None, None
    trips = []
    for k, d in enumerate(pd.date_range(START, END, freq="D")):
        for s in [s for s in held if d > last[s]]:
            cash += held.pop(s) * cls[s][last[s]] * (1 - cost)
        for s in ps:
            if s in held:
                cash += held.pop(s) * opn[s][d] * (1 - cost)
        if trip is not None and not held:
            trips.append((1 - cash / trip) * 100)
            trip = None
        e0 = cash + sum(u * opn[s][d] for s, u in held.items())
        for s in pb:
            if s in held or len(held) >= n or d > last[s]:
                continue
            a = min(invest * e0 / n, cash / (1 + cost))
            if a < 10:
                continue
            cash -= a * (1 + cost)
            held[s] = a / opn[s][d]
        e = cash + sum(u * cls[s][d] for s, u in held.items())
        curve.append(e)
        ps, pb = [], []
        if block is not None and d >= block:
            block, top = None, e
        top = max(top, e)
        if brk and block is None and e <= top * (1 - brk):
            ps, block, trip = list(held), d + pd.Timedelta(days=30), top
            continue
        if block is not None or k % 5:
            continue
        r = day.get(d, [])
        pos = {s: i + 1 for i, s in enumerate(r)}
        kept = [s for s in held if pos.get(s, 10 ** 9) <= keep]
        ps = [s for s in held if s not in kept]
        pb = [s for s in r[:n] if s not in held][:n - len(kept)]
    for s in list(held):
        cash += held.pop(s) * cls[s][min(END, last[s])] * (1 - cost)
    eq = np.r_[10000.0, curve]
    dd = float(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max()) * 100
    return dict(final=cash, dd=dd, trips=len(trips), worst=max(trips) if trips else None)


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert hashlib.sha256((D / "STEP22_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest() == lock[0] == C["protocol_sha256"]
    sys.path.insert(0, str(SRC / "execution"))
    import forward_dryrun_1d as FD
    led = FD.read_ledger(LOGS_DIR / "strategy_1d_step16_forward" / "ledger.csv")
    fz = hashlib.sha256((DATA_DIR / "forward" / "models" / "r5_2026-10.joblib").read_bytes()).hexdigest()
    assert fz == C["frozen_model_sha256"] == led[led.model_r5_file == "r5_2026-10.joblib"].model_r5_sha256.iloc[0]
    print(f"[V1 PASS] protocol hash as locked; frozen brain SHA = ledger SHA; retrain vs frozen max diff "
          f"{C['G0b_max_abs_diff_frozen_vs_retrain']:.1e}")

    # V2: coin selection + universe from raw files
    raw, last, used, known = {}, {}, [], []
    for f in sorted((PRE / "1d").glob("*_1d.csv")):
        s = f.name.split("_")[0]
        d = pd.read_csv(f, parse_dates=["timestamp"])
        d = d[d.timestamp <= END].reset_index(drop=True)
        k = s in CR.KNOWN
        ok = (PRE / "1h" / f"{s}_1h_full.csv.gz").exists() and len(d) > 0
        if not k:
            ok = ok and s not in S13.NOT_CRYPTO and len(d) >= 120 and d.close.pct_change().abs().median() >= 0.003
        if ok:
            raw[s], last[s] = d, d.timestamp.max()
            used.append(s)
            if k:
                known.append(s)
    sel = pd.read_csv(D / "coin_selection_pre2020.csv")
    assert set(sel[sel.used].symbol) == set(used), set(sel[sel.used].symbol) ^ set(used)
    assert sorted(known) == sorted(C["reference_coins_present"])
    rows = []
    for s in used:
        d = raw[s]
        usd = (d.volume * d.close).rolling(30, min_periods=30).mean()
        i = np.arange(len(d))
        ok = (d.timestamp >= START) & (usd >= 2_000_000) & (i + 1 >= 120) & (i >= 60)
        rows.append(pd.DataFrame(dict(symbol=s, date=d.timestamp[ok], usd=usd[ok], idx=i[ok])))
    R = pd.concat(rows, ignore_index=True)
    R["rk"] = R.groupby("date").usd.rank(ascending=False, method="first")
    Uv = R[R.rk <= 20]
    U = pd.read_csv(D / "U_pre2020_predictions.csv", parse_dates=["date"])
    a, b = set(zip(Uv.symbol, Uv.date)), set(zip(U.symbol, U.date))
    assert a == b, (len(a - b), len(b - a))
    print(f"[V2 PASS] {len(used)} coins selected identically; universe re-derived from raw files: {len(a)} coin-days identical")

    # V3: labels + AUC
    ref = []
    for s in known:
        d = raw[s]
        o = d.open.values
        i = np.arange(len(d))
        ok = (i + 6 <= len(d) - 1) & (i >= 60)
        ref.append(pd.DataFrame(dict(date=d.timestamp.values[ok], f=o[i[ok] + 6] / o[i[ok] + 1] - 1)))
    med = pd.concat(ref).groupby("date").f.median()
    P = U.merge(Uv[["symbol", "date", "idx"]], on=["symbol", "date"])
    f = []
    for s, i in zip(P.symbol, P.idx):
        o = raw[s].open.values
        f.append(o[i + 6] / o[i + 1] - 1 if i + 6 <= len(o) - 1 else np.nan)
    P["f"] = f
    y = np.where(P.f.isna() | P.date.map(med).isna(), np.nan, (P.f - P.date.map(med) > 0).astype(float))
    same = (np.isnan(y) & P.label_r5.isna()) | (y == P.label_r5)
    assert same.all(), int((~same).sum())
    m = ~np.isnan(y)
    for lab, col in (("AI", "score"), ("CONTROL", "score_control")):
        av = auc(y[m].astype(int), P[col].values[m])
        assert abs(av - C[f"{lab}_skill_label_r5"]["auc"]) < 1e-9, (lab, av)
        print(f"[V3 PASS] {lab}: labels re-derived from raw opens ({int(m.sum())} rows), AUC {av:.4f}")

    # V4: portfolios
    opn = {s: raw[s].set_index("timestamp").open.to_dict() for s in set(U.symbol) | {"BTCUSDT"}}
    cls = {s: raw[s].set_index("timestamp").close.to_dict() for s in set(U.symbol) | {"BTCUSDT"}}
    for s in opn:
        if last[s] < END:
            c = cls[s][last[s]]
            for d in pd.date_range(last[s] + pd.Timedelta(days=1), END):
                opn[s][d], cls[s][d] = c, c
    res = {}
    for name, col, brk in (("AI_100_none", "score", None), ("AI_100_b10", "score", 0.10), ("CONTROL_100_b10", "score_control", 0.10)):
        r = sim(U[["symbol", "date"]].assign(score=U[col]), 1.0, brk, opn, cls, last)
        c = C["portfolio"][name]
        assert abs(r["final"] - c["final"]) < 0.01 and abs(r["dd"] - c["max_dd_pct"]) < 0.01 and r["trips"] == c["breaker_trips"], (name, r, c)
        res[name] = r
        print(f"[V4 PASS] {name}: final {r['final']:.2f}, MaxDD {r['dd']:.2f}%, breaker trips {r['trips']}")
    units = 10000 / 1.0025 / opn["BTCUSDT"][START]
    curve = np.array([units * cls["BTCUSDT"][d] for d in pd.date_range(START, END)])
    final = units * cls["BTCUSDT"][END] * (1 - 0.0025)
    eq = np.r_[10000.0, curve]
    dd = float(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max()) * 100
    assert abs(final - C["portfolio"]["BTC_HOLD"]["final"]) < 0.01 and abs(dd - C["portfolio"]["BTC_HOLD"]["max_dd_pct"]) < 0.01
    print(f"[V4 PASS] BTC_HOLD: final {final:.2f}, MaxDD {dd:.2f}%")

    # V5: gates
    pf, g = C["portfolio"], C["gates"]
    p, btc = res["AI_100_b10"], final
    rec = dict(G1_skill=C["AI_skill_label_r5"]["ci_low"] > 0.5 and C["AI_skill_label_r5"]["auc"] > C["CONTROL_skill_label_r5"]["auc"],
               G2a_maxdd=p["dd"] < 50, G2b_beats_btc=p["final"] > btc,
               G2c_beats_control_ew=p["final"] > res["CONTROL_100_b10"]["final"] and p["final"] > pf["EW_U_100_b10"]["final"],
               G2d_breaker_cuts_dd=p["dd"] < res["AI_100_none"]["dd"],
               G2e_cost040=pf["AI_100_b10_cost040"]["final"] > btc,
               G2f_neighbours=all(pf[k]["max_dd_pct"] < 50 and pf[k]["final"] > btc for k in ("AI_100_b08", "AI_100_b12")))
    assert all(bool(rec[k]) == g[k] for k in rec), {k: (rec[k], g[k]) for k in rec}
    g2 = all(v for k, v in rec.items() if k.startswith("G2"))
    want = ("INVALID" if not g["G0"] else "PASS" if rec["G1_skill"] and g2 else
            "SYSTEM_PASSES_SKILL_UNPROVEN" if g2 else "SKILL_HOLDS_PACKAGE_FAILS" if rec["G1_skill"] else "FAIL")
    assert g["decision"] == want
    print(f"[V5 PASS] gates recomputed -> {g['decision']}")


if __name__ == "__main__":
    main()
