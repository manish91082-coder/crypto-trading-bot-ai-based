"""
Step 8: Entry brain + Exit brain that must PROVE skill out-of-sample.
Protocol: logs/strategy_1d_step8_ai/STEP8_PROTOCOL_PREREGISTERED.md (+ PROTOCOL_CLARIFICATIONS_BEFORE_RUN.md),
SHA256 in PROTOCOL_SHA256.txt -- written before any result.

Survivorship-free: 30 coins, trade only the point-in-time top 10 by trailing 365-day USDT volume.
Both brains are re-trained on the 1st of every month on labels known before that day.
Every reported number is written to claims.json; audits/verify_step8_claims.py recomputes them from the outputs.
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_strategy_1d as E
import step7_swing_ai_1d as S7
from step6_4_survivorship_1d import load_all, universe
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step8_ai"
OOS_START, DATA_END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30")
RESERVE = 0.20
ENTRY_UP, ENTRY_DN, ENTRY_DAYS = 2.0, 1.5, 30
EXIT_UP, EXIT_DN, EXIT_DAYS = 1.5, 1.0, 20
MAX_HOLD_ROWS = 60
STOP_ATR = 1.5
BASE_PLAN = E.Config("ZZ", 4.0, False, STOP_ATR, None, True, None, 8, 0.15, False, exit_k=4.0).exit_plan()
CFG = E.Config("ZZ", 4.0, False, STOP_ATR, None, True, None, 8, 0.15, False, exit_k=4.0)

DAILY = ["r1", "r5", "r10", "r20", "r60", "dist_hi20_atr", "dist_lo20_atr", "dist_hi55_atr", "dist_lo55_atr",
         "vol_ratio30", "body_atr", "upwick_atr", "lowick_atr", "range_atr", "atr_pct",
         "k2_state", "k2_age", "k3_state", "k3_age", "k4_state", "k4_age", "btc_r5", "btc_r20"]
ENTRY_FEATURES = sorted(set(S7.FEATURES) | set(DAILY))
EXIT_FEATURES = DAILY + ["btc_k3_state_t", "breadth_k3_up_t", "gain_atr", "best_atr", "giveback_atr", "days_held",
                         "dn_event_k2_today", "dn_event_k3_today"]
MODEL_KW = dict(max_depth=3, max_iter=300, learning_rate=0.05, min_samples_leaf=100, l2_regularization=1.0,
                random_state=0)


# ----------------------------------------------------------------------------------------------
# Causal daily features per coin
# ----------------------------------------------------------------------------------------------
def daily_features(data):
    btc = data["BTCUSDT"].set_index("timestamp")["close"]
    b5, b20 = btc.pct_change(5), btc.pct_change(20)
    btc_k3 = pd.Series(E.zz(data["BTCUSDT"], 3.0)["state"], index=data["BTCUSDT"]["timestamp"])
    st = pd.DataFrame({s: pd.Series(E.zz(df, 3.0)["state"] == 1, index=df["timestamp"]) for s, df in data.items()})
    av = pd.DataFrame({s: pd.Series(True, index=df["timestamp"]) for s, df in data.items()})
    breadth = st.fillna(False).sum(axis=1) / av.fillna(False).sum(axis=1)
    out = {}
    for s, df in data.items():
        c, o, h, l, v, a = (df[x] for x in ("close", "open", "high", "low", "volume", "ATR_14"))
        f = pd.DataFrame(index=df.index)
        for n in (1, 5, 10, 20, 60):
            f[f"r{n}"] = c.pct_change(n)
        f["dist_hi20_atr"] = (c - h.rolling(20).max()) / a
        f["dist_lo20_atr"] = (c - l.rolling(20).min()) / a
        f["dist_hi55_atr"] = (c - h.rolling(55).max()) / a
        f["dist_lo55_atr"] = (c - l.rolling(55).min()) / a
        f["vol_ratio30"] = v / v.rolling(30).mean()
        f["body_atr"] = (c - o) / a
        f["upwick_atr"] = (h - np.maximum(o, c)) / a
        f["lowick_atr"] = (np.minimum(o, c) - l) / a
        f["range_atr"] = (h - l) / a
        f["atr_pct"] = a / c
        for k in (2.0, 3.0, 4.0):
            st = E.zz(df, k)["state"]
            f[f"k{int(k)}_state"] = st
            f[f"k{int(k)}_age"] = S7._state_age(st)
        f["btc_r5"] = df["timestamp"].map(b5).values
        f["btc_r20"] = df["timestamp"].map(b20).values
        f["btc_k3_state_t"] = df["timestamp"].map(btc_k3).values
        f["breadth_k3_up_t"] = df["timestamp"].map(breadth).values
        f["dn_event_k2_today"] = E.zz(df, 2.0)["dn"].astype(int)
        f["dn_event_k3_today"] = E.zz(df, 3.0)["dn"].astype(int)
        out[s] = f.replace([np.inf, -np.inf], np.nan)
    return out


# ----------------------------------------------------------------------------------------------
# Labels (triple barrier, conservative same-day rule) and exit rows
# ----------------------------------------------------------------------------------------------
def barrier(h, l, start, up, dn, days, last_ok):
    """First touch from day `start`: returns (label_up_first, known_idx) or (nan, None) if the window is not complete.
    dn touched (even together with up) -> 0; up only -> 1; none within `days` -> 0."""
    for j in range(start, start + days):
        if j > last_ok:
            return np.nan, None
        if l[j] <= dn:
            return 0, j
        if h[j] >= up:
            return 1, j
    return 0, start + days - 1


def build_sets(data, real_last, feats):
    cands = S7.build_candidates(data)
    cands = cands[[d < real_last[s] for s, d in zip(cands.symbol, cands.signal_date)]].reset_index(drop=True)
    erows, xrows = [], []
    xcols = DAILY + ["btc_k3_state_t", "breadth_k3_up_t", "dn_event_k2_today", "dn_event_k3_today"]
    xcache = {s: f[xcols].to_dict("records") for s, f in feats.items()}
    for r in cands.itertuples():
        df = data[r.symbol]
        o, h, l, c, a = (df[x].values for x in ("open", "high", "low", "close", "ATR_14"))
        ts = df["timestamp"]
        last_ok = min(int(np.searchsorted(ts.values, np.datetime64(min(real_last[r.symbol], DATA_END)), side="right")) - 1,
                      len(df) - 1)
        i, e = r.signal_idx, r.signal_idx + 1
        if e > last_ok:
            continue
        atr, entry = a[i], o[e]
        lab, kj = barrier(h, l, e, entry + ENTRY_UP * atr, entry - ENTRY_DN * atr, ENTRY_DAYS, last_ok)
        row = dict(cand_id=r.Index, symbol=r.symbol, signal_date=r.signal_date, signal_idx=i, entry_price=entry,
                   atr_sig=atr, label=lab, known_date=ts.iloc[kj] if kj is not None else pd.NaT)
        row.update({k: getattr(r, k) for k in S7.FEATURES})
        row.update(feats[r.symbol].iloc[i][DAILY].to_dict())
        erows.append(row)
        # exit rows: every day the trade is alive under the catastrophic stop (max 60 days)
        stop = entry - STOP_ATR * atr
        best = entry
        frec = xcache[r.symbol]
        for t in range(e, min(e + MAX_HOLD_ROWS, last_ok + 1)):
            if l[t] <= stop:
                break
            best = max(best, h[t])
            if t + 1 > last_ok:
                break
            xl, xj = barrier(h, l, t + 1, o[t + 1] + EXIT_UP * a[t], o[t + 1] - EXIT_DN * a[t], EXIT_DAYS, last_ok)
            xr = dict(cand_id=r.Index, symbol=r.symbol, signal_idx=i, day_idx=t, date=ts.iloc[t], label=xl,
                      known_date=ts.iloc[xj] if xj is not None else pd.NaT,
                      gain_atr=(c[t] - entry) / atr, best_atr=(best - entry) / atr, giveback_atr=(best - c[t]) / atr,
                      days_held=t - e + 1)
            xr.update(frec[t])
            xrows.append(xr)
    return pd.DataFrame(erows), pd.DataFrame(xrows)


# ----------------------------------------------------------------------------------------------
# Monthly walk-forward learning
# ----------------------------------------------------------------------------------------------
def walk_forward(ent, ext, shuffle=False, seed=0):
    rng = np.random.default_rng(seed)
    pe, px, log = [], [], []
    for T in pd.date_range(OOS_START, DATA_END, freq="MS"):
        nxt = T + pd.offsets.MonthBegin(1)
        for name, D, feats, key in (("entry", ent, ENTRY_FEATURES, "signal_date"), ("exit", ext, EXIT_FEATURES, "date")):
            tr = D[(D.known_date < T) & D.label.notna()]
            assert (tr[key] < T).all() and (tr.known_date < T).all()          # nothing from the future
            y = tr.label.values.astype(int)
            if shuffle:
                y = rng.permutation(y)
            m = HistGradientBoostingClassifier(**MODEL_KW).fit(tr[feats].values, y)
            base = y.mean()
            te = D[(D[key] >= T) & (D[key] < nxt)]
            if len(te):
                pr = pd.DataFrame(dict(prob=m.predict_proba(te[feats].values)[:, 1], base_rate=base), index=te.index)
                (pe if name == "entry" else px).append(pr)
            log.append(dict(retrain=T.date(), brain=name, n_train=len(tr), base_rate=round(base, 4)))
    return pd.concat(pe), pd.concat(px), pd.DataFrame(log)


# ----------------------------------------------------------------------------------------------
# Skill measurement
# ----------------------------------------------------------------------------------------------
def skill(df, seed=1):
    d = df[df.label.notna()]
    y, p = d.label.values.astype(int), d.prob.values
    auc = roc_auc_score(y, p)
    months = d["month"].values
    um = np.unique(months)
    rng = np.random.default_rng(seed)
    idx_by_m = {m: np.where(months == m)[0] for m in um}
    boots = []
    for _ in range(1000):
        pick = np.concatenate([idx_by_m[m] for m in rng.choice(um, len(um), replace=True)])
        if len(np.unique(y[pick])) == 2:
            boots.append(roc_auc_score(y[pick], p[pick]))
    q = pd.qcut(pd.Series(p).rank(method="first"), 5, labels=False)
    qr = pd.Series(y).groupby(q.values).mean()
    return dict(n=int(len(d)), auc=float(auc), ci_low=float(np.percentile(boots, 2.5)),
                ci_high=float(np.percentile(boots, 97.5)), base_rate=float(y.mean()),
                quintile_rates=[float(x) for x in qr.values])


# ----------------------------------------------------------------------------------------------
# Portfolio
# ----------------------------------------------------------------------------------------------
def run_portfolio(data, ent, ext, members, entry_mode, use_ai_exit):
    sigs = E.build_signals(data, CFG)
    erow = {(r.symbol, r.signal_idx): r for r in ent.itertuples()}
    xprob = {(r.symbol, r.signal_idx, r.day_idx): (r.prob, r.base_rate) for r in ext.itertuples() if not pd.isna(r.prob)}
    mom = {s: data[s]["close"].pct_change(20).values for s in data}

    def policy(s, i, d):
        r = erow.get((s, i))
        if r is None or (d.year, s) not in members or r.signal_date < OOS_START:
            return None
        if entry_mode == "all":
            m = mom[s][i]
            return (m if not np.isnan(m) else -9), BASE_PLAN
        if pd.isna(r.prob) or r.prob < r.base_rate:
            return None
        return float(r.prob), BASE_PLAN

    def exit_fn(s, i, p):
        si = int(np.searchsorted(data[s]["timestamp"].values, np.datetime64(p["signal_date"])))
        v = xprob.get((s, si, i))
        return v is not None and v[0] >= max(0.5, v[1])

    tr, eq, cash, _ = E.simulate_state(data, CFG, str(OOS_START.date()), str(DATA_END.date()), signals=sigs,
                                       reserve=RESERVE, policy=policy, exit_fn=exit_fn if use_ai_exit else None)
    return tr, eq, cash


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    proto_hash = hashlib.sha256((OUT / "STEP8_PROTOCOL_PREREGISTERED.md").read_bytes()).hexdigest()
    assert proto_hash == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    data, real_last = load_all()
    uni = universe(data, real_last)
    members = {(y, s) for y, m in zip(uni.year, uni.members) for s in m.split(";")}
    feats = daily_features(data)
    ent, ext = build_sets(data, real_last, feats)
    print(f"entry rows {len(ent)} (labelled {ent.label.notna().sum()}), exit rows {len(ext)} "
          f"(labelled {ext.label.notna().sum()}) in {time.time() - t0:.0f}s", flush=True)
    ent["member"] = [(d.year, s) in members for s, d in zip(ent.symbol, ent.signal_date)]
    ext = ext.merge(ent[["cand_id", "member", "signal_date"]], on="cand_id", how="left")

    claims = dict(protocol_sha256=proto_hash, coins=len(data), entry_rows=int(len(ent)), exit_rows=int(len(ext)))
    runs = {}
    for label, shuffle in (("AI", False), ("CONTROL_shuffled", True)):
        pe, px, log = walk_forward(ent, ext, shuffle=shuffle)
        E_ = ent.join(pe, how="inner")
        X_ = ext.join(px, how="inner")
        E_["month"] = E_.signal_date.dt.to_period("M").astype(str)
        X_["month"] = X_.date.dt.to_period("M").astype(str)
        E_.to_csv(OUT / f"{label}_entry_predictions.csv", index=False)
        X_.to_csv(OUT / f"{label}_exit_predictions.csv", index=False)
        log.to_csv(OUT / f"{label}_training_log.csv", index=False)
        claims[f"{label}_entry_skill_members"] = skill(E_[E_.member])
        claims[f"{label}_exit_skill_members"] = skill(X_[X_.member == True])
        claims[f"{label}_entry_skill_allcoins"] = skill(E_)
        runs[label] = (E_, X_)
        print(label, json.dumps({k: v for k, v in claims.items() if k.startswith(label)}, default=float)[:600], flush=True)

    E_, X_ = runs["AI"]
    Ec, Xc = runs["CONTROL_shuffled"]
    port = {}
    for name, (en, ex, mode, aix) in {"BASELINE_all_swings": (E_, X_, "all", False),
                                      "AI_entry_only": (E_, X_, "ai", False),
                                      "AI_exit_only": (E_, X_, "all", True),
                                      "AI_full": (E_, X_, "ai", True),
                                      "CONTROL_full": (Ec, Xc, "ai", True)}.items():
        tr, eq, cash = run_portfolio(data, en, ex, members, mode, aix)
        assert abs(E.INITIAL_CAPITAL + tr["pnl"].sum() - cash) < 1e-6
        tr.drop(columns=["plan"], errors="ignore").to_csv(OUT / f"{name}_trades.csv", index=False)
        eq.to_csv(OUT / f"{name}_equity.csv", index=False)
        port[name] = S7.summarize(tr, eq, cash, name)
        port[name]["exit_reasons"] = tr.exit_reason.value_counts().to_dict()
        print(pd.Series(port[name]).to_string(), flush=True)
    claims["portfolio"] = port

    def gate_skill(k):
        a, c = claims[f"AI_{k}_skill_members"], claims[f"CONTROL_shuffled_{k}_skill_members"]
        return dict(auc_ge_055=a["auc"] >= 0.55, ci_low_gt_050=a["ci_low"] > 0.50, beats_control=a["auc"] > c["auc"],
                    top_q_gt_bottom_q=a["quintile_rates"][-1] > a["quintile_rates"][0])
    g1, g2 = gate_skill("entry"), gate_skill("exit")
    cal = {k: v["calmar"] for k, v in port.items()}
    g3_full = cal["AI_full"] > cal["BASELINE_all_swings"] and cal["AI_full"] > cal["CONTROL_full"]
    g3_entry = cal["AI_entry_only"] > cal["BASELINE_all_swings"] and cal["AI_entry_only"] > cal["CONTROL_full"]
    if all(g1.values()) and all(g2.values()) and g3_full:
        decision = "DEPLOY_AI_FULL"
    elif all(g1.values()) and g3_entry:
        decision = "DEPLOY_AI_ENTRY_ONLY"
    else:
        decision = "FAIL_NOTHING_DEPLOYED"
    claims["gates"] = dict(G1_entry=g1, G2_exit=g2, G3_full=g3_full, G3_entry_only=g3_entry, decision=decision)
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=float))
    print("\nGATES:", json.dumps(claims["gates"], indent=1, default=str), flush=True)


if __name__ == "__main__":
    main()
