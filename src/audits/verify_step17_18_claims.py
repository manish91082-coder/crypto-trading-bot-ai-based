"""
Independent verifier for logs/strategy_1d_step17_18/claims.json.
V1 protocol / input hashes as locked.
V2 veto labels (5-day return < -0.5 %) and the B market labels (median 5-day return of eligible B coins > 0)
   re-derived from RAW opens; both AUCs (AI + CONTROL) recomputed with the rank formula.
V3 market gate and veto decisions re-derived from the saved predictions and the claimed monthly base rates.
V4 R5_ONLY, FULL, CONTROL_FULL, FULL_cost040, both ablations re-simulated with separate code.
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

D = S13.OUT.parent / "strategy_1d_step17_18"
C = json.loads((D / "claims.json").read_text())
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def auc(y, p):
    r = rankdata(p)
    n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def run(rows, gate, opn, cls, last, cost):
    day = {d: g for d, g in rows.groupby("date")}
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
            if s in held or len(held) >= 10 or d > last[s]:
                continue
            a = min(0.8 * e0 / 10, cash / (1 + cost))
            if a < 10:
                continue
            cash -= a * (1 + cost)
            held[s] = (a / opn[s][d], a * (1 + cost), d)
        curve.append(cash + sum(u * cls[s][d] for s, (u, c, ed) in held.items()))
        ps, pb = [], []
        if k % 5:
            continue
        if gate is not None and not gate.get(d, False):
            ps = list(held)
            continue
        g = day.get(d)
        r = [] if g is None else list(g[~g.vetoed].sort_values(["score", "symbol"], ascending=[False, True]).symbol)
        pos = {s: i + 1 for i, s in enumerate(r)}
        kept = [s for s in held if pos.get(s, 10 ** 9) <= 20]
        ps = [s for s in held if s not in kept]
        pb = [s for s in r[:10] if s not in held][:10 - len(kept)]
    for s in list(held):
        out(s, cls[s][min(END, last[s])])
    eq = np.r_[10000.0, curve]
    dd = float(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max())
    ser = pd.Series(curve, index=pd.date_range(START, END))
    ye = ser.resample("YE").last()
    yr = (ye / ye.shift(1).fillna(10000.0) - 1) * 100
    cagr = (cash / 10000) ** (365.25 / (END - START).days) - 1
    return dict(final=cash, dd=dd * 100, cagr=cagr * 100, calmar=cagr / dd, trades=len(rets), rets=np.array(rets),
                months=np.array(months), years_pos=int((yr > 0).sum()))


def main():
    lock = (D / "PROTOCOL_SHA256.txt").read_text().split()
    assert sha(D / "STEP17_18_PROTOCOL_PREREGISTERED.md") == lock[0] == C["protocol_sha256"]
    r5_file = S13.OUT.parent / "strategy_1d_step15_slow" / "R5_AI_test_predictions.csv"
    assert sha(r5_file) == C["r5_file_sha256"] and C["r5_file_sha256"] in lock
    print("[V1 PASS] protocol and R5 input hashes as locked")

    _, _, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", END)
    raw_o = {}
    for lab in ("AI", "CONTROL"):
        V = pd.read_csv(D / f"veto_{lab}_predictions.csv", parse_dates=["date"])
        Mk = pd.read_csv(D / f"market_{lab}_predictions.csv", parse_dates=["date"])
        f = np.full(len(V), np.nan)
        for s, g in V.groupby("symbol"):
            if s not in raw_o:
                r = pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"])
                raw_o[s] = (r.open.values, int(np.searchsorted(r.timestamp.values, np.datetime64(min(last_n[s], END)), side="right")) - 1)
            o, lo = raw_o[s]
            i = g.idx.values
            ok = i + 6 <= lo
            v = np.full(len(i), np.nan)
            v[ok] = o[i[ok] + 6] / o[i[ok] + 1] - 1
            f[V.index.get_indexer(g.index)] = v
        assert np.allclose(f, V.fwd5.values, equal_nan=True, rtol=1e-12, atol=0), lab
        bad = np.where(np.isnan(f), np.nan, (f < -0.005).astype(float))
        m = ~np.isnan(bad)
        a = auc(bad[m].astype(int), V.p_bad.values[m])
        assert abs(a - C[f"veto_{lab}_skill"]["auc"]) < 1e-9 and int(m.sum()) == C[f"veto_{lab}_skill"]["n"], (lab, a)
        med = pd.Series(f, index=V.index).groupby(V.date).median()
        bl = (med > 0).astype(float).where(med.notna()).reindex(Mk.date.values)
        assert np.array_equal(np.nan_to_num(bl.values, nan=-1), np.nan_to_num(Mk.B_label.values, nan=-1)), lab
        mm = Mk.B_label.notna()
        am = auc(Mk.B_label[mm].values.astype(int), Mk.p_mkt[mm].values)
        assert abs(am - C[f"market_{lab}_skill"]["auc"]) < 1e-9, (lab, am)
        assert all(abs(b - C[f"market_{lab}_base"][mth]) < 1e-15 for mth, b in zip(Mk.date.dt.strftime("%Y-%m"), Mk.base))
        assert all(abs(b - C[f"veto_{lab}_base"][mth]) < 1e-15 for mth, b in zip(V.date.dt.strftime("%Y-%m"), V.base))
        print(f"[V2 PASS] {lab}: veto labels re-derived ({int(m.sum())} rows) AUC {a:.4f}; market B labels re-derived "
              f"({int(mm.sum())} days) AUC {am:.4f}")
    print("[V3 PASS] monthly base rates in the prediction files equal the claimed ones (gate/veto inputs)")

    r5 = pd.read_csv(r5_file, usecols=["symbol", "date", "score"], parse_dates=["date"])
    opn = {s: data_n[s].set_index("timestamp").open.to_dict() for s in r5.symbol.unique()}
    cls = {s: data_n[s].set_index("timestamp").close.to_dict() for s in r5.symbol.unique()}
    res = {}
    for name, lab, um, uv, cost in (("R5_ONLY", "AI", False, False, 0.0025), ("FULL", "AI", True, True, 0.0025),
                                    ("CONTROL_FULL", "CONTROL", True, True, 0.0025), ("FULL_cost040", "AI", True, True, 0.0040),
                                    ("ABL_R5_MARKET", "AI", True, False, 0.0025), ("ABL_R5_VETO", "AI", False, True, 0.0025)):
        V = pd.read_csv(D / f"veto_{lab}_predictions.csv", parse_dates=["date"])
        Mk = pd.read_csv(D / f"market_{lab}_predictions.csv", parse_dates=["date"])
        rows = r5.merge(V[["symbol", "date", "p_bad", "base"]], on=["symbol", "date"])
        assert len(rows) == len(r5)
        rows["vetoed"] = (rows.p_bad > rows.base) if uv else False
        gate = dict(zip(Mk.date, Mk.p_mkt >= Mk.base)) if um else None
        r = run(rows, gate, opn, cls, last_n, cost)
        c = C["portfolio"][name]
        assert abs(r["final"] - c["final"]) < 0.01 and abs(r["dd"] - c["max_dd_pct"]) < 0.01 and r["trades"] == c["trades"], (name, r["final"], c["final"])
        if r["trades"]:
            lo, _ = S11.block_ci(r["rets"], r["months"])
            assert abs(lo * 100 - c["trade_ci_low_pct"]) < 1e-9
        res[name] = r
        print(f"[V4 PASS] {name}: final {r['final']:.2f}, MaxDD {r['dd']:.2f}%, trades {r['trades']}, positive years {r['years_pos']}")
    f = res["FULL"]
    rec = dict(G1=C["G1"],
               G2a_market=C["market_AI_skill"]["ci_low"] > 0.5 and C["market_AI_skill"]["auc"] > C["market_CONTROL_skill"]["auc"],
               G2b_veto=C["veto_AI_skill"]["ci_low"] > 0.5 and C["veto_AI_skill"]["auc"] > C["veto_CONTROL_skill"]["auc"],
               G3a_cagr=f["cagr"] > 0, G3b_calmar=f["calmar"] > res["R5_ONLY"]["calmar"] and f["calmar"] > res["CONTROL_FULL"]["calmar"],
               G3c_trade_ci=C["portfolio"]["FULL"]["trade_ci_low_pct"] > 0, G3d_years=f["years_pos"] >= 4,
               G3e_cost040=res["FULL_cost040"]["cagr"] > 0, G3f_maxdd=f["dd"] < 50)
    g = C["gates"]
    assert all(bool(rec[k]) == g[k] for k in rec), {k: (rec[k], g[k]) for k in rec}
    g1 = C["market_sanity_planted"]["auc"] >= 0.55 and C["market_sanity_leak"]["auc"] > 0.95 and \
        C["veto_sanity_planted"]["auc"] >= 0.55 and C["veto_sanity_leak"]["auc"] > 0.95
    assert g1 == C["G1"]
    g3 = all(v for k, v in rec.items() if k.startswith("G3"))
    want = ("INVALID_PIPELINE_CHECK_FAILED" if not g1 else "PASS_FULL_SYSTEM" if g3 and rec["G2a_market"] and rec["G2b_veto"]
            else "SYSTEM_PASSES_BUT_BRAIN_UNPROVEN" if g3 else "FAIL")
    assert g["decision"] == want
    print(f"[V5 PASS] gates recomputed -> {g['decision']}")


if __name__ == "__main__":
    main()
