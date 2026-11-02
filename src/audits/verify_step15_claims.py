"""
Independent verifier for logs/strategy_1d_step15_slow/claims.json.
V1 protocol / code / split hashes as locked.
V2 relative labels re-derived from RAW opens (incl. the 30-coin reference median), AUCs recomputed (rank formula).
V3 every portfolio (AI, CONTROL, SIMPLE, AI at 0.40 %) re-simulated with separate code; finals, drawdowns, trade
   counts and the trade CI match.
V4 gates and decision recomputed.
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

D = S13.OUT.parent / "strategy_1d_step15_slow"
C = json.loads((D / "claims.json").read_text())
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def auc(y, p):
    r = rankdata(p)
    n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def raw(s):
    return pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"])


def fwd_table(sym_list, h, min_idx=60):
    """date -> {symbol: open(d+1+h)/open(d+1)-1} for rows with index >= min_idx (real candles only)."""
    out = []
    for s in sym_list:
        d = raw(s)
        d = d[d.timestamp <= END].reset_index(drop=True)
        o = d.open.values
        i = np.arange(len(d))
        ok = (i + 1 + h <= len(d) - 1) & (i >= min_idx)
        out.append(pd.DataFrame(dict(symbol=s, date=d.timestamp.values[ok], idx=i[ok], fwd=o[i[ok] + 1 + h] / o[i[ok] + 1] - 1)))
    return pd.concat(out, ignore_index=True)


def simulate(rows, h, opn, cls, last, cost):
    rank_day = {d: list(g.sort_values(["score", "symbol"], ascending=[False, True]).symbol)
                for d, g in rows.dropna(subset=["score"]).groupby("date")}
    cash, held, ps, pb, curve, rets, months = 10000.0, {}, [], [], [], [], []

    def close_pos(s, price):
        nonlocal cash
        u, c, ed = held.pop(s)
        v = u * price * (1 - cost)
        cash += v
        rets.append(v / c - 1)
        months.append(ed.strftime("%Y-%m"))

    for k, d in enumerate(pd.date_range(START, END, freq="D")):
        for s in [s for s in held if d > last[s]]:
            close_pos(s, cls[s][last[s]])
        for s in ps:
            if s in held:
                close_pos(s, opn[s][d])
        e_open = cash + sum(u * opn[s][d] for s, (u, c, ed) in held.items())
        for s in pb:
            if s in held or len(held) >= 10 or d > last[s]:
                continue
            amt = min(0.8 * e_open / 10, cash / (1 + cost))
            if amt < 10:
                continue
            cash -= amt * (1 + cost)
            held[s] = (amt / opn[s][d], amt * (1 + cost), d)
        curve.append(cash + sum(u * cls[s][d] for s, (u, c, ed) in held.items()))
        ps, pb = [], []
        if k % h:
            continue
        r = rank_day.get(d, [])
        pos = {s: i + 1 for i, s in enumerate(r)}
        kept = [s for s in held if pos.get(s, 10 ** 9) <= 20]
        ps = [s for s in held if s not in kept]
        pb = [s for s in r[:10] if s not in held][:10 - len(kept)]
    for s in list(held):
        close_pos(s, cls[s][min(END, last[s])])
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
    assert sha(D / "STEP15_PROTOCOL_PREREGISTERED.md") == lock[0] == C["protocol_sha256"]
    split_p = S13.OUT.parent / "strategy_1d_step14_rule" / "coin_split.csv"
    assert sha(split_p) == C["split_sha256"] == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    print("[V1 PASS] protocol and split hashes as locked")

    split = pd.read_csv(split_p)
    B = set(split[split.half == "B_confirm"].symbol)
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", END)
    for h in (5, 10):
        ref = fwd_table(CR.KNOWN, h)
        last_ok = {s: min(last_k[s], END) for s in CR.KNOWN}
        ref = ref[[d + pd.Timedelta(days=1 + h) <= last_ok[s] for s, d in zip(ref.symbol, ref.date)]]
        med = ref.groupby("date").fwd.median()
        for lab in ("AI", "CONTROL"):
            P = pd.read_csv(D / f"R{h}_{lab}_test_predictions.csv", parse_dates=["date"])
            assert set(P.symbol) <= B
            fw = []
            for s, g in P.groupby("symbol"):
                o = raw(s).open.values
                lo = int(np.searchsorted(raw(s).timestamp.values, np.datetime64(min(last_n[s], END)), side="right")) - 1
                i = g.idx.values
                f = np.where(i + 1 + h <= lo, o[np.minimum(i + 1 + h, len(o) - 1)] / o[np.minimum(i + 1, len(o) - 1)] - 1, np.nan)
                fw.append(pd.Series(f, index=g.index))
            P["fwd_v"] = pd.concat(fw)
            P["lab_v"] = np.where(P.fwd_v.isna() | P.date.map(med).isna(), np.nan, (P.fwd_v - P.date.map(med) > 0).astype(float))
            same = (P.lab_v.isna() & P[f"label_r{h}"].isna()) | (P.lab_v == P[f"label_r{h}"])
            assert same.all(), (h, lab, int((~same).sum()))
            m = P.lab_v.notna()
            a = auc(P.lab_v[m].values.astype(int), P.score[m].values)
            c = C[f"R{h}_{lab}_skill"]
            assert abs(a - c["auc"]) < 1e-9 and int(m.sum()) == c["n"], (h, lab, a, c["auc"])
            print(f"[V2 PASS] R{h} {lab}: labels re-derived from raw opens ({int(m.sum())} rows), AUC {a:.4f}")

    opn = {s: data_n[s].set_index("timestamp").open.to_dict() for s in B}
    cls = {s: data_n[s].set_index("timestamp").close.to_dict() for s in B}
    clser = {s: data_n[s].set_index("timestamp").close for s in B}
    rec_all = {}
    for h in (5, 10):
        P = pd.read_csv(D / f"R{h}_AI_test_predictions.csv", parse_dates=["date"])
        Pc = pd.read_csv(D / f"R{h}_CONTROL_test_predictions.csv", parse_dates=["date"])
        simple = P[["symbol", "date"]].copy()
        simple["score"] = [clser[s].get(d) / clser[s].get(d - pd.Timedelta(days=20)) - 1
                           if (d - pd.Timedelta(days=20)) in clser[s].index else np.nan for s, d in zip(P.symbol, P.date)]
        out = {}
        for lab, rows, cost in (("AI", P, 0.0025), ("CONTROL", Pc, 0.0025), ("SIMPLE", simple, 0.0025), ("AI_cost040", P, 0.0040)):
            r = simulate(rows[["symbol", "date", "score"]], h, opn, cls, last_n, cost)
            c = C[f"R{h}_portfolio"][lab]
            assert abs(r["final"] - c["final"]) < 0.01 and abs(r["dd"] - c["max_dd_pct"]) < 0.01 and r["trades"] == c["trades"], (h, lab, r["final"], c["final"])
            if r["trades"]:
                lo, _ = S11.block_ci(r["rets"], r["months"])
                assert abs(lo * 100 - c["trade_ci_low_pct"]) < 1e-9
            out[lab] = r
            print(f"[V3 PASS] R{h} {lab}: final {r['final']:.2f}, MaxDD {r['dd']:.2f}%, trades {r['trades']}, "
                  f"mean trade {r['rets'].mean() * 100 if r['trades'] else float('nan'):.3f}%, positive years {r['years_pos']}")
        a, cc = C[f"R{h}_AI_skill"], C[f"R{h}_CONTROL_skill"]
        rec = dict(G2_skill=a["ci_low"] > 0.50 and a["auc"] > cc["auc"], G3a_cagr=out["AI"]["cagr"] > 0,
                   G3b_beats=out["AI"]["calmar"] > out["CONTROL"]["calmar"] and out["AI"]["calmar"] > out["SIMPLE"]["calmar"],
                   G3c_trade_ci=C[f"R{h}_portfolio"]["AI"]["trade_ci_low_pct"] > 0, G3d_years=out["AI"]["years_pos"] >= 4,
                   G3e_cost040=out["AI_cost040"]["cagr"] > 0)
        rec["pass"] = all(rec.values())
        g = C[f"R{h}_gates"]
        assert all(bool(rec[k]) == g[k] for k in rec), (h, {k: (rec[k], g[k]) for k in rec})
        rec_all[h] = rec
    g1 = C["sanity_planted"]["auc"] >= 0.55 and C["sanity_leak"]["auc"] > 0.95
    passing = [h for h in (5, 10) if rec_all[h]["pass"]]
    want = ("INVALID_PIPELINE_CHECK_FAILED" if not g1 else
            f"PASS_R{max(passing, key=lambda h: C[f'R{h}_portfolio']['AI']['calmar'])}" if passing else
            "PARTIAL_SKILL_RULE_FAILS" if any(rec_all[h]["G2_skill"] for h in (5, 10)) else "FAIL_NO_SKILL")
    assert C["decision"] == want
    print(f"[V4 PASS] gates recomputed -> {C['decision']}")


if __name__ == "__main__":
    main()
