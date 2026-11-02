"""
Step 17 (market brain: when to stay out) + Step 18 (veto brain: where NOT to trade), tested on unseen half B.
Protocol: logs/strategy_1d_step17_18/STEP17_18_PROTOCOL_PREREGISTERED.md (SHA256 locked before any training).
R5 scores are the frozen Step 15 predictions.
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core_rows_1d as CR
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
import step14_trading_rule_1d as S14
import step15_slow_relative_1d as S15
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step17_18"
PROTO_NAME = "STEP17_18_PROTOCOL_PREREGISTERED.md"
R5_FILE = LOGS_DIR / "strategy_1d_step15_slow" / "R5_AI_test_predictions.csv"
ASOF, OOS_START = S15.ASOF, S15.OOS_START
H = 5
BAD_CUT = -0.005
COST, COST_STRESS = 0.0025, 0.0040
KW_M = dict(max_depth=2, max_iter=200, learning_rate=0.05, min_samples_leaf=50, l2_regularization=1.0)
MED_COLS = ["r1", "r5", "r20", "r60", "vol_ratio30", "atr_pct", "dist_hi55_atr", "dist_lo55_atr", "taker_buy_ratio"]
MKT = [f"m_med_{c}" for c in MED_COLS] + ["m_std_r5", "m_share_hi20", "m_btc_r5", "m_btc_r20", "m_btc_k3", "m_breadth",
                                          "m_fng", "m_fng_chg7", "m_fng_z30"]


def market_features(T):
    g = T.groupby("date")
    M = pd.DataFrame({f"m_med_{c}": g[c].median() for c in MED_COLS})
    M["m_std_r5"] = g.r5.std()
    hi = T.dropna(subset=["dist_hi20_atr"])
    M["m_share_hi20"] = (hi.dist_hi20_atr >= 0).groupby(hi.date).mean()
    btc = T[T.symbol == "BTCUSDT"].set_index("date")
    M["m_btc_r5"], M["m_btc_r20"], M["m_btc_k3"] = btc.r5, btc.r20, btc.k3_state
    M["m_breadth"] = g.breadth_k3_up_t.median()
    for c in ("fng", "fng_chg7", "fng_z30"):
        M[f"m_{c}"] = g[c].first()
    assert len(M.columns) == 18
    return M


def wf(D, feats, label, known, kw, shuffle=False, seed=0):
    """Monthly walk-forward on D (rows with `date`); returns predictions for test-month rows + exact monthly base rate."""
    rng = np.random.default_rng(seed)
    preds, base = [], {}
    for k, T in enumerate(pd.date_range(OOS_START, ASOF, freq="MS")):
        tr = D["train"][(D["train"][known] < T) & D["train"][label].notna()]
        assert (tr.date < T).all() and (tr[known] < T).all()
        y = tr[label].values.astype(int)
        if shuffle:
            y = rng.permutation(y)
        te = D["test"][(D["test"].date >= T) & (D["test"].date < T + pd.offsets.MonthBegin(1))]
        base[T.strftime("%Y-%m")] = float(y.mean())
        if te.empty:
            continue
        m = HistGradientBoostingClassifier(random_state=0, **kw).fit(tr[feats].values, y)
        preds.append(pd.Series(m.predict_proba(te[feats].values)[:, 1], index=te.index))
    return pd.concat(preds), base


def auc_ci(y, p, dates):
    """y, p, dates are pandas Series; predictions are aligned to the label rows BY INDEX (not by position)."""
    p = p.reindex(y.index)
    assert p.notna().all() and dates.index.equals(y.index)
    return S13.auc_ci(np.asarray(y).astype(int), np.asarray(p), pd.DatetimeIndex(pd.to_datetime(np.asarray(dates))).to_period("M").astype(str).values)


def simulate_full(rows, mkt_ok, px, last, cost):
    """Step 15 R5 rule + optional market gate (dict date->bool) + optional veto (rows.veto bool)."""
    by_day = {d: g for d, g in rows.groupby("date")}
    cash, pos, trades, out, traded = S14.CAPITAL, {}, [], [], 0.0
    sell_orders, buy_orders = [], []

    def sell(s, price, d, why):
        nonlocal cash, traded
        p = pos.pop(s)
        cash += p["units"] * price * (1 - cost)
        traded += p["units"] * price
        trades.append(dict(symbol=s, entry_date=p["entry_date"], entry=p["entry"], exit_date=d, exit=price, reason=why,
                           cost=p["cost"], pnl=p["units"] * price * (1 - cost) - p["cost"]))

    for k, d in enumerate(pd.date_range(OOS_START, ASOF, freq="D")):
        for s in [s for s in pos if d > last[s]]:
            sell(s, px[s].at[last[s], "close"], d, "data_end")
        for s in sell_orders:
            if s in pos:
                sell(s, px[s].at[d, "open"], d, "rebalance_exit")
        eq_open = cash + sum(p["units"] * px[s].at[d, "open"] for s, p in pos.items())
        for s in buy_orders:
            if s in pos or len(pos) >= S15.N or d > last[s]:
                continue
            o = px[s].at[d, "open"]
            notional = min(S14.INVEST * eq_open / S15.N, cash / (1 + cost))
            if notional < 10:
                continue
            cash -= notional * (1 + cost)
            traded += notional
            pos[s] = dict(units=notional / o, entry=o, cost=notional * (1 + cost), entry_date=d)
        assert cash >= -1e-6
        out.append(dict(date=d, equity=cash + sum(p["units"] * px[s].at[d, "close"] for s, p in pos.items()), n_held=len(pos)))
        sell_orders, buy_orders = [], []
        if k % H != 0:
            continue
        if mkt_ok is not None and not mkt_ok.get(d, False):
            sell_orders = list(pos)
            continue
        g = by_day.get(d)
        if g is None:
            ranked = []
        else:
            g = g[~g.veto] if "veto" in g else g
            ranked = list(g.dropna(subset=["score"]).sort_values(["score", "symbol"], ascending=[False, True]).symbol)
        rank = {s: i + 1 for i, s in enumerate(ranked)}
        keep = [s for s in pos if rank.get(s, 10 ** 9) <= S15.KEEP_RANK]
        sell_orders = [s for s in pos if s not in keep]
        buy_orders = [s for s in ranked[:S15.N] if s not in pos][:S15.N - len(keep)]
    for s in list(pos):
        sell(s, px[s].at[min(ASOF, last[s]), "close"], ASOF, "end_of_test")
    tr, eq = pd.DataFrame(trades), pd.DataFrame(out)
    assert abs(S14.CAPITAL + (tr.pnl.sum() if len(tr) else 0.0) - cash) < 1e-6
    return tr, eq, cash, traded


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = hashlib.sha256((OUT / PROTO_NAME).read_bytes()).hexdigest()
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_, r5_file_sha256=hashlib.sha256(R5_FILE.read_bytes()).hexdigest())
    split = pd.read_csv(S15.SPLIT)
    assert hashlib.sha256(S15.SPLIT.read_bytes()).hexdigest() == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    half = dict(zip(split.symbol, split.half))
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", ASOF)
    data_n = {s: data_n[s] for s in half}
    last_n = {s: last_n[s] for s in half}
    Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, S13.UNI / "1h", S13.UNI / "1h", ASOF, S11.fng_table())
    Pn["half"] = Pn.symbol.map(half)
    Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= S15.MIN_HIST)
    Pk["fwd5"], Pk["known5"] = S15.add_relative(Pk, data_k, last_k, H)
    Pn["fwd5"], Pn["known5"] = S15.add_relative(Pn, data_n, last_n, H)
    train = pd.concat([Pk, Pn[Pn.eligible & (Pn.half == "A_design")]]).reset_index(drop=True)
    testB = Pn[Pn.eligible & (Pn.half == "B_confirm")].reset_index(drop=True)
    print(f"train rows {len(train)}, B eligible rows {len(testB)} ({time.time()-t0:.0f}s)", flush=True)

    # ---------------- market table ----------------
    M = market_features(train)
    lab_tr = train.dropna(subset=["fwd5"]).groupby("date").agg(med=("fwd5", "median"), known=("known5", "max"))
    lab_B = testB.dropna(subset=["fwd5"]).groupby("date").fwd5.median()
    M["m_label"] = (lab_tr.med > 0).astype(float).reindex(M.index)
    M["m_known"] = lab_tr.known.reindex(M.index)
    M["m_med_fwd5"] = lab_tr.med.reindex(M.index)
    M["B_label"] = (lab_B > 0).astype(float).reindex(M.index)
    M["B_med_fwd5"] = lab_B.reindex(M.index)
    M = M.reset_index().rename(columns={"index": "date"})
    Mtest = M[M.date >= OOS_START].copy()
    claims["market_days_test"] = int(Mtest.B_label.notna().sum())

    # ---------------- veto rows ----------------
    mk = M.set_index("date")[MKT]
    tr_v = train.join(mk, on="date")
    te_v = testB[testB.date >= OOS_START].join(mk, on="date")
    for D in (tr_v, te_v):
        D["bad"] = np.where(D.fwd5.isna(), np.nan, (D.fwd5 < BAD_CUT).astype(float))
    FV = F + MKT

    # ---------------- G1 sanity ----------------
    rng = np.random.default_rng(42)
    Mp = M.copy()
    Mp["planted"] = Mp.m_label + rng.normal(0, 2.79, len(Mp))
    Mp["leak"] = Mp.m_med_fwd5
    Dm = dict(train=Mp, test=Mp[Mp.date >= OOS_START])
    sp, _ = wf(Dm, MKT + ["planted"], "m_label", "m_known", KW_M)
    sl, _ = wf(Dm, MKT + ["leak"], "m_label", "m_known", KW_M)
    t = Dm["test"]
    ok = t.B_label.notna()
    claims["market_sanity_planted"] = auc_ci(t.m_label[ok & t.m_label.notna()], sp[ok & t.m_label.notna()], t.date[ok & t.m_label.notna()])
    claims["market_sanity_leak"] = auc_ci(t.m_label[ok & t.m_label.notna()], sl[ok & t.m_label.notna()], t.date[ok & t.m_label.notna()])
    tv, ttv = tr_v.copy(), te_v.copy()
    tv["planted"] = tv.bad + rng.normal(0, 2.79, len(tv))
    ttv["planted"] = ttv.bad + rng.normal(0, 2.79, len(ttv))
    tv["leak"], ttv["leak"] = tv.fwd5, ttv.fwd5
    Dv = dict(train=tv, test=ttv)
    vp, _ = wf(Dv, FV + ["planted"], "bad", "known5", S11.KW)
    vl, _ = wf(Dv, FV + ["leak"], "bad", "known5", S11.KW)
    okv = ttv.bad.notna()
    claims["veto_sanity_planted"] = auc_ci(ttv.bad[okv], vp[okv], ttv.date[okv])
    claims["veto_sanity_leak"] = auc_ci(ttv.bad[okv], vl[okv], ttv.date[okv])
    g1 = all(claims[f"{b}_sanity_planted"]["auc"] >= 0.55 and claims[f"{b}_sanity_leak"]["auc"] > 0.95 for b in ("market", "veto"))
    claims["G1"] = bool(g1)
    print("G1", {k: round(claims[k]["auc"], 4) for k in claims if "sanity" in k}, g1, f"({time.time()-t0:.0f}s)", flush=True)
    del tv, ttv, Dv, Mp
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))

    # ---------------- brains ----------------
    Dm = dict(train=M, test=Mtest)
    Dv = dict(train=tr_v, test=te_v)
    brains = {}
    for lab, sh in (("AI", False), ("CONTROL", True)):
        pm, bm = wf(Dm, MKT, "m_label", "m_known", KW_M, sh, 17)
        pv, bv = wf(Dv, FV, "bad", "known5", S11.KW, sh, 18)
        okm = Mtest.B_label.notna()
        claims[f"market_{lab}_skill"] = auc_ci(Mtest.B_label[okm], pm[okm], Mtest.date[okm])
        claims[f"veto_{lab}_skill"] = auc_ci(te_v.bad[okv], pv[okv], te_v.date[okv])
        claims[f"market_{lab}_base"], claims[f"veto_{lab}_base"] = bm, bv
        mo = Mtest[["date", "B_label", "B_med_fwd5"]].assign(p_mkt=pm)
        mo["base"] = mo.date.dt.strftime("%Y-%m").map(bm)
        mo.to_csv(OUT / f"market_{lab}_predictions.csv", index=False)
        vo = te_v[["symbol", "date", "idx", "fwd5", "bad"]].assign(p_bad=pv)
        vo["base"] = vo.date.dt.strftime("%Y-%m").map(bv)
        vo.to_csv(OUT / f"veto_{lab}_predictions.csv", index=False)
        brains[lab] = (mo, vo)
        print(lab, "market", {k: round(v, 4) for k, v in claims[f"market_{lab}_skill"].items()},
              "veto", {k: round(v, 4) for k, v in claims[f"veto_{lab}_skill"].items()}, f"({time.time()-t0:.0f}s)", flush=True)
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))

    # ---------------- trading ----------------
    r5 = pd.read_csv(R5_FILE, usecols=["symbol", "date", "score"], parse_dates=["date"])
    px = {s: df.set_index("timestamp")[["open", "close"]] for s, df in data_n.items()}
    runs = {}

    def system(lab_brains, use_mkt, use_veto, cost, name):
        mo, vo = brains[lab_brains]
        rows = r5.merge(vo[["symbol", "date", "p_bad", "base"]], on=["symbol", "date"], how="left")
        assert rows.p_bad.notna().all(), "veto prediction missing for an R5 row"
        if use_veto:
            rows["veto"] = rows.p_bad > rows.base
        gate = {d: bool(p >= b) for d, p, b in zip(mo.date, mo.p_mkt, mo.base)} if use_mkt else None
        tr, eq, final, traded = simulate_full(rows, gate, px, last_n, cost)
        tr.to_csv(OUT / f"{name}_trades.csv", index=False)
        eq.to_csv(OUT / f"{name}_equity.csv", index=False)
        s = S14.summarize(tr, eq, final, traded, name)
        s["days_invested_pct"] = float((eq.n_held > 0).mean() * 100)
        runs[name] = s
        print(name, {k: s[k] for k in ("final", "cagr_pct", "max_dd_pct", "calmar", "trades", "avg_trade_pct",
                                       "trade_ci_low_pct", "days_invested_pct")}, flush=True)

    system("AI", False, False, COST, "R5_ONLY")
    assert abs(runs["R5_ONLY"]["final"] - 22617.34) < 0.01, "R5_ONLY does not reproduce Step 15 (internal check)"
    system("AI", True, True, COST, "FULL")
    system("CONTROL", True, True, COST, "CONTROL_FULL")
    system("AI", True, True, COST_STRESS, "FULL_cost040")
    system("AI", True, False, COST, "ABL_R5_MARKET")
    system("AI", False, True, COST, "ABL_R5_VETO")
    claims["portfolio"] = runs
    f = runs["FULL"]
    gates = dict(G1=g1,
                 G2a_market=claims["market_AI_skill"]["ci_low"] > 0.50 and claims["market_AI_skill"]["auc"] > claims["market_CONTROL_skill"]["auc"],
                 G2b_veto=claims["veto_AI_skill"]["ci_low"] > 0.50 and claims["veto_AI_skill"]["auc"] > claims["veto_CONTROL_skill"]["auc"],
                 G3a_cagr=f["cagr_pct"] > 0,
                 G3b_calmar=f["calmar"] > runs["R5_ONLY"]["calmar"] and f["calmar"] > runs["CONTROL_FULL"]["calmar"],
                 G3c_trade_ci=f["trade_ci_low_pct"] > 0,
                 G3d_years=sum(f.get(f"ret_{y}", 0.0) > 0 for y in range(2021, 2027)) >= 4,
                 G3e_cost040=runs["FULL_cost040"]["cagr_pct"] > 0,
                 G3f_maxdd=f["max_dd_pct"] < 50)
    gates = {k: bool(v) for k, v in gates.items()}
    g3 = all(v for k, v in gates.items() if k.startswith("G3"))
    gates["decision"] = ("INVALID_PIPELINE_CHECK_FAILED" if not gates["G1"] else
                         "PASS_FULL_SYSTEM" if g3 and gates["G2a_market"] and gates["G2b_veto"] else
                         "SYSTEM_PASSES_BUT_BRAIN_UNPROVEN" if g3 else "FAIL")
    claims["gates"] = gates
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
