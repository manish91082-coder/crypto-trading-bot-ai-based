"""
Step 10: method sanity (10.0) + futures/dominance information (10.1) + Path 1 (swing entries) + Path 2 (every coin-day,
1- and 3-day question). Protocol: logs/strategy_1d_step10_ai/STEP10_PROTOCOL_PREREGISTERED.md (SHA256 locked).
Futures data is information only; trading stays spot long-only.
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

import swing_strategy_1d as E
import step7_swing_ai_1d as S7
import step8_ai_entry_exit_1d as S8
import step9_ai_more_info_1d as S9
from step6_4_survivorship_1d import load_all, universe
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step10_ai"
FI = DATA_DIR / "futures_info"
H1 = DATA_DIR / "raw_1h_full"
FUT = ["fund_1d", "fund_7d", "prem_close", "prem_7d", "oi_chg1", "oi_chg7", "top_ls_acc", "top_ls_pos", "global_ls",
       "taker_ls_vol", "btc_vol_share7", "btc_rel7", "btc_rel30"]
P2_KW = dict(max_depth=3, max_iter=300, learning_rate=0.05, min_samples_leaf=200, l2_regularization=1.0, random_state=0)
COST = 0.0025
HORIZONS = (1, 3)


# ----------------------------------------------------------------------------------------------
# 10.1 features
# ----------------------------------------------------------------------------------------------
def market_proxies(data, real_last):
    qv, r7, r30 = {}, {}, {}
    for s, df in data.items():
        h = pd.read_csv(H1 / f"{s}_1h_full.csv.gz", usecols=["timestamp", "quote_volume"], parse_dates=["timestamp"])
        h = h[h.timestamp <= real_last[s] + pd.Timedelta(hours=23)]
        qv[s] = h.groupby(h.timestamp.dt.normalize()).quote_volume.sum()
        c = df[df.timestamp <= real_last[s]].set_index("timestamp").close
        r7[s], r30[s] = c.pct_change(7), c.pct_change(30)
    qv, r7, r30 = pd.DataFrame(qv), pd.DataFrame(r7), pd.DataFrame(r30)
    share = qv["BTCUSDT"].rolling(7).sum() / qv.sum(axis=1, min_count=1).rolling(7).sum()
    alts = [c for c in r7.columns if c != "BTCUSDT"]
    return pd.DataFrame(dict(btc_vol_share7=share, btc_rel7=r7["BTCUSDT"] - r7[alts].mean(axis=1),
                             btc_rel30=r30["BTCUSDT"] - r30[alts].mean(axis=1)))


def futures_features(sym, dates, proxies):
    f = pd.DataFrame(index=pd.DatetimeIndex(dates))
    fp = FI / f"{sym}_funding.csv"
    if fp.exists():
        fu = pd.read_csv(fp, parse_dates=["time"])
        fu["day"] = (fu.time - pd.Timedelta(seconds=1)).dt.normalize()   # 00:00 settlement belongs to the closed day
        d = fu.groupby("day").funding_rate.sum()
        f["fund_1d"] = d.reindex(f.index)
        f["fund_7d"] = f.fund_1d.rolling(7, min_periods=5).sum()
    pp = FI / f"{sym}_premium_1d.csv"
    if pp.exists():
        pr = pd.read_csv(pp, parse_dates=["timestamp"]).set_index("timestamp").prem_close
        f["prem_close"] = pr.reindex(f.index)
        f["prem_7d"] = f.prem_close.rolling(7, min_periods=5).mean()
    mp = FI / f"{sym}_metrics_daily.csv"
    if mp.exists():
        m = pd.read_csv(mp, parse_dates=["date"]).set_index("date")
        m = m[m.n_rows >= 200]                                        # incomplete days are not used
        m = m.reindex(f.index)
        f["oi_chg1"] = m.oi / m.oi.shift(1) - 1
        f["oi_chg7"] = m.oi / m.oi.shift(7) - 1
        for c in ("top_ls_acc", "top_ls_pos", "global_ls", "taker_ls_vol"):
            f[c] = m[c]
    f = f.join(proxies, how="left")
    for c in FUT:
        if c not in f:
            f[c] = np.nan
    return f[FUT].replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def install_all_features(data, real_last):
    xstats = S9.install_features(data, real_last)            # Step 9 1h features
    proxies = market_proxies(data, real_last)
    base_fn = S8.daily_features
    cov = {}

    def daily_plus(data_):
        feats = base_fn(data_)
        for s, f in feats.items():
            ff = futures_features(s, data_[s].timestamp.values, proxies)
            ff.loc[(data_[s].timestamp > real_last[s]).values] = np.nan
            cov[s] = {c: round(float(ff[c].notna().mean()), 3) for c in ("fund_1d", "prem_close", "oi_chg1")}
            feats[s] = pd.concat([f, ff.set_index(f.index)], axis=1)
        return feats
    S8.DAILY = S8.DAILY + FUT
    S8.ENTRY_FEATURES = sorted(set(S7.FEATURES) | set(S8.DAILY))
    S8.EXIT_FEATURES = S8.EXIT_FEATURES + FUT
    S8.daily_features = daily_plus
    return xstats, cov


# ----------------------------------------------------------------------------------------------
# Path 2 dataset: every coin-day, label = profitable after cost over h days (open d+1 -> open d+1+h)
# ----------------------------------------------------------------------------------------------
def path2_rows(data, real_last, feats, members):
    rows = []
    for s, df in data.items():
        f = feats[s].copy()
        o = df.open.values
        last_ok = int(np.searchsorted(df.timestamp.values, np.datetime64(min(real_last[s], S8.DATA_END)), side="right")) - 1
        f["symbol"], f["date"], f["idx"] = s, df.timestamp.values, np.arange(len(df))
        for h in HORIZONS:
            fwd = np.full(len(df), np.nan)
            known = np.full(len(df), np.datetime64("NaT"), dtype="datetime64[ns]")
            i = np.arange(len(df))
            ok = i + 1 + h <= last_ok
            fwd[ok] = o[i[ok] + 1 + h] / o[i[ok] + 1] - 1
            known[ok] = df.timestamp.values[i[ok] + 1 + h]
            f[f"fwd_{h}"] = fwd
            f[f"label_{h}"] = np.where(np.isnan(fwd), np.nan, (fwd - COST > 0).astype(float))
            f[f"known_{h}"] = known
        f = f[(f.idx >= 60) & (f.idx <= last_ok)]
        rows.append(f)
    P = pd.concat(rows, ignore_index=True)
    P["member"] = [(d.year, s) in members for s, d in zip(P.symbol, pd.to_datetime(P.date))]
    P["date"] = pd.to_datetime(P.date)
    return P


def wf_path2(P, feats, h, shuffle=False, seed=0, extra=None):
    rng = np.random.default_rng(seed)
    cols = feats + (extra or [])
    out, log = [], []
    for T in pd.date_range(S8.OOS_START, S8.DATA_END, freq="MS"):
        nxt = T + pd.offsets.MonthBegin(1)
        tr = P[(P[f"known_{h}"] < T) & P[f"label_{h}"].notna()]
        assert (tr.date < T).all() and (tr[f"known_{h}"] < T).all()
        y = tr[f"label_{h}"].values.astype(int)
        if shuffle:
            y = rng.permutation(y)
        m = HistGradientBoostingClassifier(**P2_KW).fit(tr[cols].values, y)
        te = P[(P.date >= T) & (P.date < nxt)]
        out.append(pd.DataFrame(dict(prob=m.predict_proba(te[cols].values)[:, 1], base_rate=y.mean()), index=te.index))
        log.append(dict(retrain=T.date(), n_train=len(tr), base_rate=round(y.mean(), 4)))
    pr = pd.concat(out)
    R = P.loc[pr.index, ["symbol", "date", "idx", "member", f"label_{h}", f"fwd_{h}"]].join(pr)
    R = R.rename(columns={f"label_{h}": "label"})
    R["month"] = R.date.dt.to_period("M").astype(str)
    return R, pd.DataFrame(log)


def path2_portfolio(data, real_last, R, mode):
    """Daily re-evaluation: decide at the close of d, trade at the open of d+1, friction on traded notional."""
    px = {s: df.set_index("timestamp") for s, df in data.items()}
    dates = pd.date_range(S8.OOS_START, S8.DATA_END, freq="D")
    by_day = {d: g for d, g in R[R.member].groupby("date")}
    cash, units, rows, target = E.INITIAL_CAPITAL, {}, [], {}
    traded = 0.0
    for d in dates:
        # 1. open: liquidate coins whose data ended (at their last real close), then rebalance to target
        for s in list(units):
            if d > real_last[s]:
                cash += units.pop(s) * px[s].loc[real_last[s], "close"] * (1 - E.FRICTION)
        opens = {s: px[s].loc[d, "open"] for s in set(units) | set(target) if d in px[s].index and d <= real_last[s]}
        eq_open = cash + sum(u * opens[s] for s, u in units.items() if s in opens)
        want = {s: w * eq_open for s, w in target.items() if s in opens}
        for s in list(units):                                      # sells first
            cur = units[s] * opens.get(s, 0.0)
            tgt = want.get(s, 0.0)
            if s in opens and cur > tgt:
                q = (cur - tgt) / opens[s]
                cash += q * opens[s] * (1 - E.FRICTION)
                traded += q * opens[s]
                units[s] -= q
                if units[s] * opens[s] < 1e-9:
                    units.pop(s)
        for s, tgt in want.items():                                # then buys (never below zero cash)
            cur = units.get(s, 0.0) * opens[s]
            if tgt > cur:
                spend = min((tgt - cur) * (1 + E.FRICTION), cash)
                if spend > 1.0:
                    q = spend / (1 + E.FRICTION) / opens[s]
                    units[s] = units.get(s, 0.0) + q
                    cash -= spend
                    traded += q * opens[s]
        assert cash >= -1e-6
        # 2. close: equity, next target
        eq = cash + sum(u * px[s].loc[min(d, real_last[s]), "close"] for s, u in units.items())
        rows.append(dict(date=d, cash=cash, equity=eq, n_held=len(units)))
        g = by_day.get(d)
        target = {}
        if g is not None and len(g):
            if mode == "baseline":
                target = {s: 0.8 / len(g) for s in g.symbol}
            else:
                sel = g[g.prob >= np.maximum(0.5, g.base_rate)].sort_values(["prob", "symbol"], ascending=[False, True]).head(4)
                target = {s: 0.2 for s in sel.symbol}
    eqdf = pd.DataFrame(rows)
    final = eqdf.equity.iloc[-1]
    return eqdf, final, traded


def summarize_curve(eq, final, label, traded):
    curve = np.r_[E.INITIAL_CAPITAL, eq.equity.values]
    peak = np.maximum.accumulate(curve)
    dd = ((peak - curve) / peak).max()
    yrs = (eq.date.iloc[-1] - S8.OOS_START).days / 365.25
    cagr = (final / E.INITIAL_CAPITAL) ** (1 / yrs) - 1
    r = pd.Series(curve).pct_change().dropna()
    ye = eq.set_index("date").equity.resample("YE").last()
    yr = (ye / ye.shift(1).fillna(E.INITIAL_CAPITAL) - 1) * 100
    return dict(run=label, final=round(final, 2), cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd * 100, 2),
                calmar=round(cagr / dd, 3), sharpe=round(r.mean() / r.std() * np.sqrt(365), 3),
                turnover_x=round(traded / E.INITIAL_CAPITAL, 1), median_held=float(eq.n_held.median()),
                **{f"ret_{y.year}": round(v, 2) for y, v in yr.items()})


def gate(a, c, min_auc):
    return dict(auc_ge_min=a["auc"] >= min_auc, ci_low_gt_050=a["ci_low"] > 0.50, beats_control=a["auc"] > c["auc"],
                top_q_gt_bottom_q=a["quintile_rates"][-1] > a["quintile_rates"][0])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256((OUT / "STEP10_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest()
    assert h == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    data, real_last = load_all()
    xstats, cov = install_all_features(data, real_last)
    S8.OUT = OUT
    uni = universe(data, real_last)
    members = {(y, s) for y, m in zip(uni.year, uni.members) for s in m.split(";")}
    feats = S8.daily_features(data)
    claims = dict(protocol_sha256=h, futures_coverage=cov)
    pd.DataFrame(cov).T.to_csv(OUT / "futures_feature_coverage.csv")
    print("futures coverage (share of days with data):\n", pd.DataFrame(cov).T.to_string(), flush=True)

    # ---------------- Path 2 dataset + 10.0 sanity ----------------
    P = path2_rows(data, real_last, feats, members)
    F2 = S8.DAILY + ["btc_k3_state_t", "breadth_k3_up_t"]
    print(f"path2 rows {len(P)} ({time.time() - t0:.0f}s)", flush=True)
    rng = np.random.default_rng(42)
    P["planted"] = P["label_1"] + rng.normal(0, 2.79, len(P))
    P["leak"] = P["fwd_1"]
    sa, _ = wf_path2(P, F2, 1, extra=["planted"])
    sb, _ = wf_path2(P, F2, 1, extra=["leak"])
    sa.to_csv(OUT / "sanity_S_A_path2_predictions.csv", index=False)
    sb.to_csv(OUT / "sanity_S_B_path2_predictions.csv", index=False)
    claims["sanity_S_A_path2_planted"] = S8.skill(sa[sa.member])
    claims["sanity_S_B_path2_leak"] = S8.skill(sb[sb.member])
    print("S-A planted AUC", round(claims["sanity_S_A_path2_planted"]["auc"], 4), "| S-B leak AUC",
          round(claims["sanity_S_B_path2_leak"]["auc"], 4), flush=True)

    ent, ext = S8.build_sets(data, real_last, feats)
    ent["member"] = [(d.year, s) in members for s, d in zip(ent.symbol, ent.signal_date)]
    ext = ext.merge(ent[["cand_id", "member", "signal_date"]], on="cand_id", how="left")
    e2 = ent.copy()
    e2["planted"] = e2.label + np.random.default_rng(43).normal(0, 2.79, len(e2))
    old = S8.ENTRY_FEATURES
    # entry-only sanity walk-forward (same model settings as Step 8 entry brain)
    out = []
    for T in pd.date_range(S8.OOS_START, S8.DATA_END, freq="MS"):
        tr = e2[(e2.known_date < T) & e2.label.notna()]
        m = HistGradientBoostingClassifier(**S8.MODEL_KW).fit(tr[old + ["planted"]].values, tr.label.astype(int))
        te = e2[(e2.signal_date >= T) & (e2.signal_date < T + pd.offsets.MonthBegin(1))]
        if len(te):
            out.append(pd.DataFrame(dict(prob=m.predict_proba(te[old + ["planted"]].values)[:, 1]), index=te.index))
    sae = e2.join(pd.concat(out), how="inner")
    sae["month"] = sae.signal_date.dt.to_period("M").astype(str)
    sae[["symbol", "signal_date", "member", "label", "prob", "month"]].to_csv(OUT / "sanity_S_A_path1_predictions.csv", index=False)
    claims["sanity_S_A_path1_planted"] = S8.skill(sae[sae.member])
    sa_ok = all(0.57 <= claims[k]["auc"] <= 0.63 for k in ("sanity_S_A_path2_planted", "sanity_S_A_path1_planted"))
    sb_ok = claims["sanity_S_B_path2_leak"]["auc"] > 0.95
    claims["sanity_pass"] = dict(S_A=sa_ok, S_B=sb_ok)
    print("S-A path1 planted AUC", round(claims["sanity_S_A_path1_planted"]["auc"], 4), "->", claims["sanity_pass"], flush=True)
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=float))
    if not (sa_ok and sb_ok):
        print("METHOD SANITY FAILED -> stop (protocol)")
        return

    # ---------------- Path 1: swing entries + all new information ----------------
    runs = {}
    for label, shuffle in (("P1_AI", False), ("P1_CONTROL", True)):
        pe, px_, log = S8.walk_forward(ent, ext, shuffle=shuffle)
        E_, X_ = ent.join(pe, how="inner"), ext.join(px_, how="inner")
        E_["month"] = E_.signal_date.dt.to_period("M").astype(str)
        X_["month"] = X_.date.dt.to_period("M").astype(str)
        E_.to_csv(OUT / f"{label}_entry_predictions.csv", index=False)
        X_.to_csv(OUT / f"{label}_exit_predictions.csv", index=False)
        log.to_csv(OUT / f"{label}_training_log.csv", index=False)
        claims[f"{label}_entry_skill"] = S8.skill(E_[E_.member])
        claims[f"{label}_exit_skill"] = S8.skill(X_[X_.member == True])
        runs[label] = (E_, X_)
        print(label, round(claims[f"{label}_entry_skill"]["auc"], 4), round(claims[f"{label}_exit_skill"]["auc"], 4), flush=True)
    port1 = {}
    for name, (lab, mode, aix) in {"P1_BASELINE_all_swings": ("P1_AI", "all", False), "P1_AI_entry_only": ("P1_AI", "ai", False),
                                   "P1_AI_full": ("P1_AI", "ai", True), "P1_CONTROL_full": ("P1_CONTROL", "ai", True)}.items():
        en, ex = runs[lab]
        tr, eq, cash = S8.run_portfolio(data, en, ex, members, mode, aix)
        assert abs(E.INITIAL_CAPITAL + tr.pnl.sum() - cash) < 1e-6
        tr.drop(columns=["plan"], errors="ignore").to_csv(OUT / f"{name}_trades.csv", index=False)
        eq.to_csv(OUT / f"{name}_equity.csv", index=False)
        port1[name] = S7.summarize(tr, eq, cash, name)
        print(name, {k: port1[name][k] for k in ("final", "cagr_pct", "max_dd_pct", "calmar", "trades")}, flush=True)
    claims["path1_portfolio"] = port1
    g1 = gate(claims["P1_AI_entry_skill"], claims["P1_CONTROL_entry_skill"], 0.55)
    g2 = gate(claims["P1_AI_exit_skill"], claims["P1_CONTROL_exit_skill"], 0.55)
    cal = {k: v["calmar"] for k, v in port1.items()}
    g3f = cal["P1_AI_full"] > cal["P1_BASELINE_all_swings"] and cal["P1_AI_full"] > cal["P1_CONTROL_full"]
    g3e = cal["P1_AI_entry_only"] > cal["P1_BASELINE_all_swings"] and cal["P1_AI_entry_only"] > cal["P1_CONTROL_full"]
    claims["path1_gates"] = dict(G1=g1, G2=g2, G3_full=g3f, G3_entry_only=g3e,
                                 pass_full=all(g1.values()) and all(g2.values()) and g3f,
                                 pass_entry_only=all(g1.values()) and g3e)

    # ---------------- Path 2: every coin-day, 1 and 3 days ----------------
    port2, g_p2 = {}, {}
    for hh in HORIZONS:
        R, log = wf_path2(P, F2, hh)
        Rc, _ = wf_path2(P, F2, hh, shuffle=True)
        R.to_csv(OUT / f"P2_h{hh}_AI_predictions.csv", index=False)
        Rc.to_csv(OUT / f"P2_h{hh}_CONTROL_predictions.csv", index=False)
        log.to_csv(OUT / f"P2_h{hh}_training_log.csv", index=False)
        a, c = S8.skill(R[R.member]), S8.skill(Rc[Rc.member])
        claims[f"P2_h{hh}_AI_skill"], claims[f"P2_h{hh}_CONTROL_skill"] = a, c
        res = {}
        for name, RR, mode in ((f"P2_h{hh}_BASELINE", R, "baseline"), (f"P2_h{hh}_AI", R, "ai"), (f"P2_h{hh}_CONTROL", Rc, "ai")):
            eq, final, traded = path2_portfolio(data, real_last, RR, mode)
            eq.to_csv(OUT / f"{name}_equity.csv", index=False)
            res[name] = summarize_curve(eq, final, name, traded)
            print(name, {k: res[name][k] for k in ("final", "cagr_pct", "max_dd_pct", "calmar", "turnover_x")}, flush=True)
        port2.update(res)
        gs = gate(a, c, 0.53)
        g3 = res[f"P2_h{hh}_AI"]["calmar"] > res[f"P2_h{hh}_BASELINE"]["calmar"] and \
            res[f"P2_h{hh}_AI"]["calmar"] > res[f"P2_h{hh}_CONTROL"]["calmar"]
        g_p2[f"h{hh}"] = dict(skill=gs, G3=g3, pass_all=all(gs.values()) and g3)
        print(f"P2 h{hh} AUC {a['auc']:.4f} CI [{a['ci_low']:.3f},{a['ci_high']:.3f}] control {c['auc']:.4f} -> {g_p2[f'h{hh}']}", flush=True)
    claims["path2_portfolio"] = port2
    claims["path2_gates"] = g_p2

    passing = []
    if claims["path1_gates"]["pass_full"]:
        passing.append(("P1_AI_full", cal["P1_AI_full"]))
    elif claims["path1_gates"]["pass_entry_only"]:
        passing.append(("P1_AI_entry_only", cal["P1_AI_entry_only"]))
    for hh in HORIZONS:
        if g_p2[f"h{hh}"]["pass_all"]:
            passing.append((f"P2_h{hh}_AI", port2[f"P2_h{hh}_AI"]["calmar"]))
    claims["decision"] = max(passing, key=lambda x: x[1])[0] if passing else "FAIL_NOTHING_DEPLOYED"
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=float))
    print("\nDECISION:", claims["decision"], "| path1:", json.dumps(claims["path1_gates"], default=str),
          "| path2:", json.dumps(g_p2, default=str), flush=True)


if __name__ == "__main__":
    main()
