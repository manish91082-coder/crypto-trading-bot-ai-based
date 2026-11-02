"""
Independent verifier for logs/strategy_1d_step13_unseen/claims.json. Raises on any mismatch.

V0 data: for the 30 training coins, the freshly downloaded data/universe_all 1D files equal (OHLCV) the files the
   brains were trained on (two independent downloads must agree); the unseen-coin list contains none of the 30.
V1 protocol + Fear&Greed SHA256 unchanged.
V2 B1/B3 AUCs on unseen coins recomputed (Mann-Whitney rank formula) with labels re-derived from RAW opens.
V3 every cut-off = quantile of predictions from strictly EARLIER months; BUY = member & votes >= 2.
V4 shadow returns re-derived from raw opens (open d+1 -> open d+4 - 0.50 %).
V5 AI and CONTROL portfolios re-simulated with separate code (0.25 % per fill).
V6 gates and decision recomputed from the claims.
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
import step13_unseen_coins_1d as S13
import step11_ai_confident_1d as S11
from step6_4_survivorship_1d import load_all

D = S13.OUT
C = json.loads((D / "claims.json").read_text())
F = S13.NEW_FRICTION
RT = S13.NEW_ROUND_TRIP


def auc(y, p):
    r = rankdata(p)
    n1 = y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def main():
    data_k, _ = load_all()
    sel = pd.read_csv(D / "unseen_coin_selection.csv")
    assert not set(sel[sel.used].symbol) & set(data_k)
    worst = 0.0
    for s, dk in data_k.items():
        raw = pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"]).set_index("timestamp")
        k = dk.set_index("timestamp")
        k = k[k.volume > 0]                                        # padded (delisted) days are not real candles
        common = k.index.intersection(raw.index)
        assert len(common) >= 0.99 * len(k), (s, len(common), len(k))
        for c in ("open", "close", "volume"):
            rel = np.abs(raw.loc[common, c].values / k.loc[common, c].values - 1)
            worst = max(worst, float(np.nanmax(rel)))
            assert np.nanmax(rel) < 1e-9, (s, c, np.nanmax(rel))
    print(f"[V0 PASS] 30 training coins: new download == training data (open/close/volume, max rel diff {worst:.1e}); "
          f"{int(sel.used.sum())} unseen coins, none of them a training coin")

    h = hashlib.sha256((D / S13.PROTO_NAME).read_bytes()).hexdigest()
    assert h == C["protocol_sha256"] == (D / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256(S11.FNG_FILE.read_bytes()).hexdigest() == C["fng_sha256"]
    print("[V1 PASS] protocol and Fear&Greed hashes unchanged")

    data_n, last_n, _ = S13.load_new(set(data_k))
    raw_open = {s: pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv").open.values for s in data_n}
    ts = {s: df.timestamp for s, df in data_n.items()}
    for lab in ("AI", "CONTROL"):
        S = pd.read_csv(D / f"{lab}_signals_unseen.csv", parse_dates=["date", "known_3"])
        for k, hh, col in (("B1", 1, "p1"), ("B3", 3, "p3")):
            ok = [i + 1 + hh < len(raw_open[s]) and ts[s].iloc[i + 1 + hh] <= min(last_n[s], S13.DATA_END)
                  for s, i in zip(S.symbol, S.idx)]
            m = S[ok]
            y = np.array([raw_open[s][i + 1 + hh] / raw_open[s][i + 1] - 1 - 0.0025 > 0 for s, i in zip(m.symbol, m.idx)]).astype(int)
            a = auc(y, m[col].values)
            assert abs(a - C[f"{lab}_{k}_unseen"]["auc"]) < 1e-9 and len(y) == C[f"{lab}_{k}_unseen"]["n"], (lab, k, a)
        print(f"[V2 PASS] {lab}: unseen B1 AUC {C[f'{lab}_B1_unseen']['auc']:.4f}, B3 AUC {C[f'{lab}_B3_unseen']['auc']:.4f} "
              f"(n {C[f'{lab}_B1_unseen']['n']}, raw-open labels, rank formula)")
        mon = S.date.dt.to_period("M")
        for col, thr in (("p1", "thr1"), ("p3", "thr3")):
            for mth in mon.unique():
                past = S.loc[mon < mth, col]
                want = past.quantile(0.9) if len(past) else np.nan
                got = S.loc[mon == mth, thr].iloc[0]
                assert (np.isnan(want) and np.isnan(got)) or abs(want - got) < 1e-12, (lab, col, mth)
        assert (S.buy == (S.member & (S.votes >= 2))).all()
        print(f"[V3 PASS] {lab}: every cut-off = quantile of earlier months only; BUY = member & votes>=2")
        b = S[S.buy & S.shadow_ret.notna()]
        sr = np.array([raw_open[s][i + 4] / raw_open[s][i + 1] - 1 - RT for s, i in zip(b.symbol, b.idx)])
        assert np.allclose(sr, b.shadow_ret.values)
        if len(sr):
            assert abs(sr.mean() * 100 - C[f"{lab}_shadow"]["mean_net_pct"]) < 1e-9
        print(f"[V4 PASS] {lab}: {len(b)} shadow trades, mean net {sr.mean() * 100 if len(sr) else float('nan'):.3f}% from raw opens")

        px = {s: df.set_index("timestamp") for s, df in data_n.items()}
        buys = S[S.buy].sort_values(["date", "rank_score", "symbol"], ascending=[True, False, True])
        sig = {d: list(g.symbol) for d, g in buys.groupby("date")}
        sh = buys[["known_3", "shadow_ret"]].dropna().sort_values("known_3")
        cash, pos, pend, eqs, peak, ddu = 10000.0, {}, [], [], 10000.0, None
        for d in pd.date_range(S13.OOS_START, S13.DATA_END, freq="D"):
            for s in list(pos):
                if d > last_n[s]:
                    cash += pos.pop(s)[0] * px[s].at[last_n[s], "close"] * (1 - F)
            for s in list(pos):
                if pos[s][3] <= d:
                    cash += pos.pop(s)[0] * px[s].at[d, "open"] * (1 - F)
            e0 = cash + sum(v[0] * px[s].at[d, "open"] for s, v in pos.items())
            for s, sd in pend:
                if s in pos or len(pos) >= 4 or d > last_n[s] or d not in px[s].index:
                    continue
                o = px[s].at[d, "open"]
                n = min(0.2 * e0, cash / (1 + F))
                if n < 10:
                    continue
                cash -= n * (1 + F)
                pos[s] = [n / o, o, o - 2.0 * px[s].at[sd, "ATR_14"], d + pd.Timedelta(days=3)]
            pend = []
            for s in list(pos):
                lo, op = px[s].at[d, "low"], px[s].at[d, "open"]
                if lo <= pos[s][2]:
                    u, _, st, _ = pos.pop(s)
                    cash += u * (op if op <= st else st) * (1 - F)
            eq = cash + sum(v[0] * px[s].at[d, "close"] for s, v in pos.items())
            eqs.append(eq)
            if ddu is not None and d >= ddu:
                ddu, peak = None, eq
            peak = max(peak, eq)
            if ddu is None and (peak - eq) / peak >= 0.15:
                ddu = d + pd.Timedelta(days=30)
            kn = sh[sh.known_3 <= d].shadow_ret.values[-40:]
            mp = len(kn) >= 40 and kn.mean() < 0
            for s in sig.get(d, []):
                if s in pos:
                    pos[s][3] = max(pos[s][3], d + pd.Timedelta(days=4))
            if ddu is None and not mp:
                pend = [(s, d) for s in sig.get(d, []) if s not in pos]
        for s in list(pos):
            cash += pos.pop(s)[0] * px[s].at[min(S13.DATA_END, last_n[s]), "close"] * (1 - F)
        c = C[f"{lab}_portfolio"]
        curve = np.r_[10000, eqs]
        dd = ((np.maximum.accumulate(curve) - curve) / np.maximum.accumulate(curve)).max()
        assert abs(cash - c["final"]) < 0.01 and abs(dd * 100 - c["max_dd_pct"]) < 0.01, (lab, cash, c["final"])
        print(f"[V5 PASS] {lab}: independent re-simulation final {cash:.2f}, MaxDD {dd * 100:.2f}%")

    g = C["gates"]
    ai, ct, bl = C["AI_portfolio"], C["CONTROL_portfolio"], C["BASELINE_portfolio"]
    bp = {k: C[f"AI_{k}_unseen"]["ci_low"] > 0.50 and C[f"AI_{k}_unseen"]["auc"] > C[f"CONTROL_{k}_unseen"]["auc"] for k in ("B1", "B3")}
    rec = dict(G1_pipeline=C["sanity_planted_unseen"]["auc"] >= 0.55 and C["sanity_leak_unseen"]["auc"] > 0.95,
               G2_skill_B1=bp["B1"], G2_skill_B3=bp["B3"], G2_skill=bp["B1"] or bp["B3"],
               G3_shadow=C["AI_shadow"]["ci_low_pct"] > 0,
               G3_portfolio=ai["cagr_pct"] > 0 and ai["calmar"] > ct["calmar"] and ai["calmar"] > bl["calmar"],
               G3_years=sum(ai.get(f"ret_{y}", 0.0) > 0 for y in range(2021, 2027)) >= 4)
    assert all(bool(rec[k]) == g[k] for k in rec), {k: (rec[k], g[k]) for k in rec}
    g3 = rec["G3_shadow"] and rec["G3_portfolio"] and rec["G3_years"]
    want = ("PASS_BRAIN_GENERALISES" if rec["G1_pipeline"] and rec["G2_skill"] and g3 else
            "PARTIAL_SKILL_BUT_TRADING_RULE_FAILS" if rec["G1_pipeline"] and rec["G2_skill"] else
            "INVALID_PIPELINE_CHECK_FAILED" if not rec["G1_pipeline"] else "FAIL_NO_TRANSFERABLE_SKILL")
    assert g["decision"] == want
    print(f"[V6 PASS] gates recomputed -> {g['decision']}")


if __name__ == "__main__":
    main()
