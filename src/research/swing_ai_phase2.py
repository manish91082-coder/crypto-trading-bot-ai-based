"""
Swing Anatomy Phase 2: AI filter for real-time rally confirmations (4h / 8h / 12h / 1D, 10 coins, 2017-2026).
Protocol: logs/research_swing_ai_phase2/PHASE2_PROTOCOL_PREREGISTERED.md (SHA256 locked before any model).
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
for p in (SRC_DIR, SRC_DIR / "research", SRC_DIR / "analytics", SRC_DIR / "pipeline_1d"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import DATA_DIR, LOGS_DIR
import swing_strategy_1d as E
import swing_anatomy_phase1 as P
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13

OUT = LOGS_DIR / "research_swing_ai_phase2"
DER = DATA_DIR / "derived" / "swing_ai_phase2"
PROTO = "PHASE2_PROTOCOL_PREREGISTERED.md"
TFS = ("4h", "8h", "12h", "1D")
TF_CODE = {tf: i for i, tf in enumerate(TFS)}
COST, KP = 0.0025, 3.0
FEATS_ALL = [f"c_{f}" for f in P.FACTORS] + ["tf_code"]
assert len(P.FACTORS) == 25
STRUCT_NAN = ["c_htf_state_4h", "c_htf_state_1h"]     # never a HIGHER timeframe of 4h / 8h / 12h / 1D -> always NaN
FEATS = [f for f in FEATS_ALL if f not in STRUCT_NAN]
WF_START, WF_END = pd.Timestamp("2019-01-01"), pd.Timestamp("2026-09-01")
P1 = (pd.Timestamp("2019-01-01"), pd.Timestamp("2021-01-01"))
P2 = (pd.Timestamp("2021-01-01"), pd.Timestamp("2026-10-01"))
CONTROL_SEED = 2


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def coin_bars(coin, gate):
    """Exactly Phase 1 build_bars for the timeframes needed here (1h / 1d sources only)."""
    n1h, n1d = P.load_spliced(coin, "1h", gate), P.load_spliced(coin, "1d", gate)
    raw = {"1h": n1h, "4h": P.agg(n1h, "4h"), "8h": P.agg(n1h, "8h"), "12h": P.agg(n1h, "12h"), "1D": n1d,
           "1W": P.agg(n1d, "W-MON"), "1M": P.agg(n1d, "MS")}
    return {tf: P.clip_atr(d)[0] for tf, d in raw.items()}, n1h


def factors_at(ii, tf, b, fac, sup, res, h1, htf_states, btc, fng):
    """The Phase 1 legs_for `c_` block, for an arbitrary index array (same code lines)."""
    ts, cl, atr = b.timestamp.values, b.close.values, b.ATR_14.values
    et = P.end_times(tf, ts)
    L = pd.DataFrame(index=range(len(ii)))
    pre = "c_"
    for f in fac.columns:
        L[pre + f] = fac[f].values[ii]
    price = cl[ii]
    a_ = atr[ii]
    L[pre + "sup_dist_atr"] = (price - sup[ii]) / a_
    L[pre + "res_dist_atr"] = (res[ii] - price) / a_
    tend = et[ii]
    L[pre + "vap_at_price"] = [P.vap_at(h1, t, p_, 0.25 * x, P.VAP_W[tf].to_timedelta64()) for t, p_, x in zip(tend, price, a_)]
    for h in P.HTF_LIST:
        L[pre + f"htf_state_{h}"] = P.state_lookup(htf_states[h], tend) if P.ORDER[h] < P.ORDER[tf] else np.nan
    if btc is not None:
        bts, bret, bst, bet = btc
        j = np.searchsorted(bet, tend, "right") - 1
        ok = j >= 0
        L[pre + "btc_ret20"] = np.where(ok, bret[np.maximum(j, 0)], np.nan)
        L[pre + "btc_state_same_tf"] = np.where(ok, bst[np.maximum(j, 0)], np.nan)
    else:
        L[pre + "btc_ret20"], L[pre + "btc_state_same_tf"] = np.nan, np.nan
    day = (pd.to_datetime(tend) - pd.Timedelta(microseconds=1)).normalize() - pd.Timedelta(days=1)
    L[pre + "fng"] = fng["fng"].reindex(day).values
    L[pre + "fng_chg7"] = fng["fng_chg7"].reindex(day).values
    st = pd.to_datetime(ts[ii])
    L[pre + "hour"] = st.hour if tf not in ("1D", "1W", "1M") else np.nan
    L[pre + "weekday"] = st.weekday if tf not in ("1W", "1M") else np.nan
    return L


def events_for(state):
    """Entry bars (state becomes +1) and the first later bar with state -1 (-1 = still open at data end)."""
    n = len(state)
    nxt = np.full(n, -1)
    k = -1
    for t in range(n - 1, -1, -1):
        nxt[t] = k
        if state[t] == -1:
            k = t
    ent = [i for i in range(n) if state[i] == 1 and (i == 0 or state[i - 1] != 1)]
    return np.array(ent, dtype=int), np.array([nxt[i] for i in ent], dtype=int)


def build():
    fng = P.fng_table()
    gate, rows, btc_ctx, n_open = [], [], {}, 0
    for coin in ["BTCUSDT"] + [c for c in P.COINS if c != "BTCUSDT"]:
        bars, n1h = coin_bars(coin, gate)
        h1 = (n1h.timestamp.values, n1h.low.values, n1h.high.values, n1h.quote_volume.values)
        htf_states = {h: (P.end_times(h, bars[h].timestamp.values), E.zz(bars[h], KP)["state"]) for h in P.HTF_LIST}
        for tf in TFS:
            b = bars[tf]
            fac = P.base_factors(b)
            st = E.zz(b, KP)["state"]
            if coin == "BTCUSDT":
                btc_ctx[tf] = (b.timestamp.values, fac.ret20.values, st, P.end_times(tf, b.timestamp.values))
            sup, res = P.sr_nearest(b)
            ent, ex = events_for(st)
            n_open += int((ex < 0).sum())
            ent, ex = ent[ex >= 0], ex[ex >= 0]
            if not len(ent):
                continue
            F = factors_at(ent, tf, b, fac, sup, res, h1, htf_states, None if coin == "BTCUSDT" else btc_ctx[tf], fng)
            cl, atr, et = b.close.values, b.ATR_14.values, P.end_times(tf, b.timestamp.values)
            gross = cl[ex] / cl[ent]
            F = F.assign(coin=coin, tf=tf, tf_code=TF_CODE[tf], i=ent, j=ex, entry_end=et[ent], exit_end=et[ex],
                         entry_close=cl[ent], exit_close=cl[ex], gross=gross - 1, net=gross * (1 - COST) / (1 + COST) - 1,
                         ret_atr=(cl[ex] - cl[ent]) / atr[ent])
            F["label"] = (F.net > 0).astype(int)
            rows.append(F)
            print(coin, tf, len(F), flush=True)
    return pd.concat(rows, ignore_index=True), gate, n_open


def g0(Ev):
    L = pd.read_parquet(P.DER / "legs_all.parquet")
    L = L[(L.K == KP) & (L.direction == "Rally") & L.tf.isin(TFS)]
    m = Ev.merge(L, left_on=["coin", "tf", "i"], right_on=["coin", "tf", "confirm_i"], how="left", suffixes=("", "_p1"), indicator=True)
    hit = m._merge == "both"
    worst = 0.0
    for f in P.FACTORS:
        a, b = m.loc[hit, f"c_{f}"].values.astype(float), m.loc[hit, f"c_{f}_p1"].values.astype(float)
        both_nan = np.isnan(a) & np.isnan(b)
        d = np.where(both_nan, 0.0, np.abs(a - b))
        worst = max(worst, float(np.nanmax(np.where(np.isnan(d), np.inf, d))))
    return dict(events=len(Ev), matched=int(hit.sum()), matched_share=float(hit.mean()), max_abs_diff=worst,
                pass_=bool(hit.mean() >= 0.95 and worst < 1e-9))


def fit(X, y):
    return HistGradientBoostingClassifier(random_state=0, **S11.KW).fit(X, y)


def wf(Ev, feats, shuffle=False, seed=0):
    rng = np.random.default_rng(seed)
    p, thr = pd.Series(np.nan, index=Ev.index), pd.Series(np.nan, index=Ev.index)
    for T in pd.date_range(WF_START, WF_END, freq="MS"):
        nxt = T + pd.offsets.MonthBegin(1)
        tr = Ev[Ev.exit_end < T]
        te = Ev[(Ev.entry_end >= T) & (Ev.entry_end < nxt)]
        if not len(te):
            continue
        assert (tr.entry_end < T).all()
        y = tr.label.values
        if shuffle:
            y = rng.permutation(y)
        m = fit(tr[feats].values, y)
        p.loc[te.index] = m.predict_proba(te[feats].values)[:, 1]
        thr.loc[te.index] = float(np.median(m.predict_proba(tr[feats].values)[:, 1]))
    return p, thr


def months(d):
    return pd.to_datetime(d.entry_end).dt.to_period("M").astype(str).values


def auc_block(d, p):
    return S13.auc_ci(d.label.values, p.values, months(d))


def diff_ci(d, sel, reps=2000, seed=4):
    """Mean net of SELECTED minus mean net of ALL, with a month-block bootstrap CI."""
    mo = months(d)
    um = np.unique(mo)
    idx = {m: np.where(mo == m)[0] for m in um}
    net, s = d.net.values, sel.values
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(reps):
        k = np.concatenate([idx[m] for m in rng.choice(um, len(um))])
        if s[k].any():
            bs.append(net[k][s[k]].mean() - net[k].mean())
    return dict(n_all=int(len(d)), n_sel=int(s.sum()), mean_all_pct=round(float(net.mean() * 100), 4),
                mean_sel_pct=round(float(net[s].mean() * 100), 4), mean_rej_pct=round(float(net[~s].mean() * 100), 4) if (~s).any() else None,
                diff_pct=round(float((net[s].mean() - net.mean()) * 100), 4),
                diff_ci_low_pct=round(float(np.percentile(bs, 2.5) * 100), 4), diff_ci_high_pct=round(float(np.percentile(bs, 97.5) * 100), 4),
                win_all=round(float((net > 0).mean()), 4), win_sel=round(float((net[s] > 0).mean()), 4))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DER.mkdir(parents=True, exist_ok=True)
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "PHASE2_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    Ev, gate, n_open = build()
    Ev = Ev.sort_values(["entry_end", "coin", "tf"]).reset_index(drop=True)
    assert Ev[STRUCT_NAN].isna().all().all(), "structurally-NaN columns are not all NaN"
    Ev.to_parquet(DER / "events.parquet", index=False)
    claims = dict(protocol_sha256=h_, events=len(Ev), open_excluded=n_open, events_by_tf=Ev.groupby("tf").size().to_dict(),
                  splice_contiguous=bool(all(g["contiguous"] for g in gate)), events_sha256=sha(DER / "events.parquet"))
    claims["G0"] = g0(Ev)
    print("G0", claims["G0"], f"({time.time()-t0:.0f}s)", flush=True)

    T = Ev[(Ev.entry_end >= WF_START) & (Ev.entry_end < P2[1])]
    rng = np.random.default_rng(42)
    Evp = Ev.copy()
    Evp["planted"] = Evp.label + rng.normal(0, 2.79, len(Evp))
    Evp["leak"] = Evp.net
    pp, _ = wf(Evp, FEATS + ["planted"])
    pl, _ = wf(Evp, FEATS + ["leak"])
    claims["sanity_planted"] = auc_block(T, pp.loc[T.index])
    claims["sanity_leak"] = auc_block(T, pl.loc[T.index])
    print("G1", round(claims["sanity_planted"]["auc"], 4), round(claims["sanity_leak"]["auc"], 4), flush=True)

    pa, thr = wf(Ev, FEATS)
    pc, _ = wf(Ev, FEATS, shuffle=True, seed=CONTROL_SEED)
    T = T.assign(p_ai=pa.loc[T.index], thr=thr.loc[T.index], p_control=pc.loc[T.index])
    assert T.p_ai.notna().all()
    T["selected"] = T.p_ai >= T.thr
    T.to_csv(OUT / "test_predictions.csv", index=False)
    claims["AI_all"] = auc_block(T, T.p_ai)
    claims["CONTROL_all"] = auc_block(T, T.p_control)
    for name, (a, b) in (("P1", P1), ("P2", P2)):
        d = T[(T.entry_end >= a) & (T.entry_end < b)]
        claims[f"AI_{name}"] = auc_block(d, d.p_ai)
        claims[f"money_{name}"] = diff_ci(d, d.selected)
    claims["money_all"] = diff_ci(T, T.selected)
    claims["per_tf"] = {tf: dict(auc=auc_block(d, d.p_ai), money=diff_ci(d, d.selected)) for tf, d in T.groupby("tf")}
    # report-only: time-reversed frozen check
    tr = Ev[(Ev.entry_end >= pd.Timestamp("2021-01-01")) & (Ev.exit_end < pd.Timestamp("2026-10-01"))]
    te = Ev[Ev.entry_end < pd.Timestamp("2021-01-01")]
    m = fit(tr[FEATS].values, tr.label.values)
    claims["report_time_reversed"] = auc_block(te, pd.Series(m.predict_proba(te[FEATS].values)[:, 1], index=te.index))

    g = dict(G0=claims["G0"]["pass_"],
             G1=claims["sanity_planted"]["auc"] >= 0.55 and claims["sanity_leak"]["auc"] > 0.95,
             G2=claims["AI_all"]["ci_low"] > 0.50 and claims["AI_all"]["auc"] > claims["CONTROL_all"]["auc"],
             G3=claims["AI_P1"]["ci_low"] > 0.50 and claims["AI_P2"]["ci_low"] > 0.50,
             G4=claims["money_all"]["diff_ci_low_pct"] > 0 and claims["money_P1"]["diff_pct"] > 0 and claims["money_P2"]["diff_pct"] > 0)
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = ("INVALID_G0" if not g["G0"] else "INVALID" if not g["G1"] else
                     "PASS" if all(g[k] for k in ("G2", "G3", "G4")) else "FAIL")
    claims["gates"] = g
    claims["test_predictions_sha256"] = sha(OUT / "test_predictions.csv")
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    for k in ("AI_all", "CONTROL_all", "AI_P1", "AI_P2", "money_all", "money_P1", "money_P2", "report_time_reversed"):
        print(k, claims[k], flush=True)
    for tf, v in claims["per_tf"].items():
        print(tf, round(v["auc"]["auc"], 4), v["money"], flush=True)
    print("GATES", json.dumps(g), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
