"""
Step 11: "confident-only" multi-brain AI with self-monitoring (spot, 1D, free data only).
Protocol: logs/strategy_1d_step11_ai/STEP11_PROTOCOL_PREREGISTERED.md (SHA256 locked before any result).
Reuses the verified Step 8/9/10 data + feature code; adds Fear & Greed + cross-sectional rank features.
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
import step8_ai_entry_exit_1d as S8
import step10_ai_1d as S10
from step6_4_survivorship_1d import load_all, universe
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step11_ai"
FNG_FILE = DATA_DIR / "sentiment" / "fear_greed_raw.json"
FNG_SHA = "29b2ca42e5a227bfee6ace870084718ecd86a3808b62facc8b39283c767eb1c0"
RANK_COLS = ["r1", "r5", "r20", "vol_ratio30", "taker_buy_ratio", "fund_1d", "oi_chg1", "dist_hi20_atr"]
FNG_COLS = ["fng", "fng_chg7", "fng_z30"]
KW = dict(max_depth=3, max_iter=300, learning_rate=0.05, min_samples_leaf=200, l2_regularization=1.0)
SEEDS = (0, 1, 2)
HOLD = 3
STOP_ATR = 2.0
SLOT = 0.20
MAX_POS = 4
SHADOW_N = 40
ROUND_TRIP = 0.0025
OOS_START, DATA_END = S8.OOS_START, S8.DATA_END
PROTO_NAME = "STEP11_PROTOCOL_PREREGISTERED.md"
BAG, DECAY = True, True              # Step 12 sets both False (plain Step-10 training)
KW_SWING = KW                        # Step 12: Step 8 entry-brain settings


# ----------------------------------------------------------------------------------------------
# Features
# ----------------------------------------------------------------------------------------------
def fng_table():
    raw = FNG_FILE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FNG_SHA, "Fear & Greed file changed"
    d = pd.DataFrame(json.loads(raw)["data"])
    d["date"] = pd.to_datetime(d.timestamp, format="%d-%m-%Y")
    s = d.set_index("date").value.astype(float).sort_index()
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))      # missing days stay NaN
    return pd.DataFrame(dict(fng=s, fng_chg7=s - s.shift(7),
                             fng_z30=(s - s.rolling(30, min_periods=20).mean()) / s.rolling(30, min_periods=20).std()))


def add_features(P, fng):
    P = P.join(fng, on="date")
    for c in RANK_COLS:
        P[f"xr_{c}"] = P.groupby("date")[c].rank(pct=True)
    return P


# ----------------------------------------------------------------------------------------------
# Bagged, time-decayed, monthly walk-forward brain
# ----------------------------------------------------------------------------------------------
def fit_predict_bag(Xtr, ytr, age_days, Xte, seed_base=0, kw=None):
    kw = kw or KW
    w = 0.5 ** (age_days / 365.0) if DECAY else np.ones(len(ytr))
    if not BAG:
        m = HistGradientBoostingClassifier(random_state=0, **kw).fit(Xtr, ytr, sample_weight=w if DECAY else None)
        return m.predict_proba(Xte)[:, 1]
    preds = []
    for s in SEEDS:
        rng = np.random.default_rng(seed_base * 100 + s)
        idx = rng.choice(len(ytr), int(0.8 * len(ytr)), replace=True)
        m = HistGradientBoostingClassifier(random_state=s, **kw).fit(Xtr[idx], ytr[idx], sample_weight=w[idx])
        preds.append(m.predict_proba(Xte)[:, 1])
    return np.mean(preds, axis=0)


def walk_forward(D, feats, label, known, datecol, shuffle=False, seed=0, kw=None):
    rng = np.random.default_rng(seed)
    out, log = [], []
    for k, T in enumerate(pd.date_range(OOS_START, DATA_END, freq="MS")):
        nxt = T + pd.offsets.MonthBegin(1)
        tr = D[(D[known] < T) & D[label].notna()]
        assert (tr[datecol] < T).all() and (tr[known] < T).all()
        te = D[(D[datecol] >= T) & (D[datecol] < nxt)]
        if te.empty:
            continue
        y = tr[label].values.astype(int)
        if shuffle:
            y = rng.permutation(y)
        age = (T - tr[datecol]).dt.days.values.astype(float)
        p = fit_predict_bag(tr[feats].values, y, age, te[feats].values, seed_base=k, kw=kw)
        out.append(pd.Series(p, index=te.index))
        log.append(dict(retrain=T.date(), n_train=len(tr), base_rate=round(y.mean(), 4)))
    return pd.concat(out), pd.DataFrame(log)


def causal_pct_threshold(dates, probs, q):
    """For each row: q-quantile of all predictions from EARLIER calendar months (NaN in the first month)."""
    s = pd.DataFrame(dict(m=pd.to_datetime(dates).dt.to_period("M"), p=probs))
    thr = {}
    for m in sorted(s.m.unique()):
        past = s.p[s.m < m]
        thr[m] = past.quantile(q) if len(past) else np.nan
    return s.m.map(thr).values


def pct_rank_vs_past(dates, probs):
    """Percentile of each prediction within all predictions of earlier months (for ranking only)."""
    s = pd.DataFrame(dict(m=pd.to_datetime(dates).dt.to_period("M"), p=probs))
    out = np.full(len(s), np.nan)
    for m in sorted(s.m.unique()):
        past = np.sort(s.p[s.m < m].values)
        cur = s.m == m
        if len(past):
            out[cur.values] = np.searchsorted(past, s.p[cur].values, side="right") / len(past)
    return out


# ----------------------------------------------------------------------------------------------
# Signals and portfolio
# ----------------------------------------------------------------------------------------------
def build_signals(P, b1, b3, ent, bs):
    S = P.loc[b1.index, ["symbol", "date", "idx", "member", "fwd_3", "known_3"]].copy()
    S["p1"], S["p3"] = b1.values, b3.loc[b1.index].values
    S["thr1"] = causal_pct_threshold(S.date, S.p1, 0.90)
    S["thr3"] = causal_pct_threshold(S.date, S.p3, 0.90)
    e = ent.loc[bs.index, ["symbol", "signal_date"]].copy()
    e["ps"] = bs.values
    e["thrs"] = causal_pct_threshold(e.signal_date, e.ps, 0.80)
    e["voteS"] = e.ps >= e.thrs
    S = S.merge(e.rename(columns={"signal_date": "date"})[["symbol", "date", "ps", "voteS"]], on=["symbol", "date"], how="left")
    S["vote1"], S["vote3"] = S.p1 >= S.thr1, S.p3 >= S.thr3
    S["voteS"] = S.voteS.fillna(False).astype(bool)
    S["votes"] = S.vote1.astype(int) + S.vote3.astype(int) + S.voteS.astype(int)
    S["rank_score"] = np.nanmean(np.c_[pct_rank_vs_past(S.date, S.p1), pct_rank_vs_past(S.date, S.p3)], axis=1)
    S["buy"] = S.member & (S.votes >= 2)
    S["shadow_ret"] = S.fwd_3 - ROUND_TRIP
    return S


def simulate(data, real_last, S, friction=E.FRICTION, use_monitor=True):
    px = {s: df.set_index("timestamp") for s, df in data.items()}
    atr = {s: df.set_index("timestamp").ATR_14 for s, df in data.items()}
    buys = S[S.buy].sort_values(["date", "rank_score", "symbol"], ascending=[True, False, True])
    by_day = {d: g for d, g in buys.groupby("date")}
    shadow = buys[["date", "known_3", "shadow_ret"]].dropna().sort_values("known_3")
    cash, pos, pending, trades, rows = E.INITIAL_CAPITAL, {}, [], [], []
    peak, dd_until, n_monitor_pause_days = E.INITIAL_CAPITAL, None, 0
    for d in pd.date_range(OOS_START, DATA_END, freq="D"):
        def sell(s, raw, why):
            nonlocal cash
            p = pos.pop(s)
            cash += p["units"] * raw * (1 - friction)
            trades.append(dict(symbol=s, entry_date=p["entry_date"], entry=p["entry"], exit_date=d, exit=raw, reason=why,
                               cost=p["cost"], pnl=p["units"] * raw * (1 - friction) - p["cost"]))
        for s in [s for s in pos if d > real_last[s]]:                          # delisted: last real close
            sell(s, px[s].at[real_last[s], "close"], "data_end")
        for s in [s for s, p in pos.items() if p["exit_date"] <= d]:            # scheduled exits at the open
            sell(s, px[s].at[d, "open"], "hold_done")
        eq_open = cash + sum(p["units"] * px[s].at[d, "open"] for s, p in pos.items())
        for s, sig_d in pending:                                                # entries at the open
            if s in pos or len(pos) >= MAX_POS or d > real_last[s] or d not in px[s].index:
                continue
            o = px[s].at[d, "open"]
            notional = min(SLOT * eq_open, cash / (1 + friction))
            if notional < 10:
                continue
            cost = notional * (1 + friction)
            cash -= cost
            pos[s] = dict(units=notional / o, entry=o, cost=cost, entry_date=d, stop=o - STOP_ATR * atr[s].at[sig_d],
                          exit_date=d + pd.Timedelta(days=HOLD))
        pending = []
        for s in list(pos):                                                     # stop, gap aware, checked first
            row = px[s].loc[d]
            if row.low <= pos[s]["stop"]:
                sell(s, row.open if row.open <= pos[s]["stop"] else pos[s]["stop"], "stop")
        eq = cash + sum(p["units"] * px[s].at[d, "close"] for s, p in pos.items())
        assert cash >= -1e-6
        # drawdown pause
        if dd_until is not None and d >= dd_until:
            dd_until, peak = None, eq
        peak = max(peak, eq)
        if dd_until is None and (peak - eq) / peak >= 0.15:
            dd_until = d + pd.Timedelta(days=30)
        # self-monitor on shadow outcomes known by today
        known = shadow[shadow.known_3 <= d].shadow_ret.values[-SHADOW_N:]
        mon_pause = use_monitor and len(known) >= SHADOW_N and known.mean() < 0
        n_monitor_pause_days += int(mon_pause)
        g = by_day.get(d)
        if g is not None:
            for s in g.symbol:                                                  # signal while held -> hold 3 more days
                if s in pos:
                    pos[s]["exit_date"] = max(pos[s]["exit_date"], d + pd.Timedelta(days=1 + HOLD))
            if dd_until is None and not mon_pause:
                pending = [(s, d) for s in g.symbol if s not in pos]
        rows.append(dict(date=d, cash=cash, equity=eq, n_pos=len(pos), dd_pause=dd_until is not None, monitor_pause=mon_pause))
    for s in list(pos):
        last = min(DATA_END, real_last[s])
        p = pos.pop(s)
        raw = px[s].at[last, "close"]
        cash += p["units"] * raw * (1 - friction)
        trades.append(dict(symbol=s, entry_date=p["entry_date"], entry=p["entry"], exit_date=DATA_END, exit=raw,
                           reason="end_of_test", cost=p["cost"], pnl=p["units"] * raw * (1 - friction) - p["cost"]))
    tr, eq = pd.DataFrame(trades), pd.DataFrame(rows)
    assert abs(E.INITIAL_CAPITAL + tr.pnl.sum() - cash) < 1e-6, "cash conservation failed"
    return tr, eq, cash, n_monitor_pause_days


def summary(tr, eq, final, label):
    s = S10.summarize_curve(eq.assign(n_held=eq.n_pos), final, label, 0.0)
    s.pop("turnover_x", None)
    s.update(trades=len(tr), win_rate=round((tr.pnl > 0).mean() * 100, 2) if len(tr) else 0.0,
             avg_trade_pct=round((tr.pnl / tr.cost).mean() * 100, 3) if len(tr) else 0.0,
             exit_reasons=tr.reason.value_counts().to_dict() if len(tr) else {})
    return s


def block_ci(vals, months, seed=1):
    rng = np.random.default_rng(seed)
    um = np.unique(months)
    by = {m: vals[months == m] for m in um}
    bs = [np.mean(np.concatenate([by[m] for m in rng.choice(um, len(um))])) for _ in range(2000)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256((OUT / PROTO_NAME).read_bytes()).hexdigest()
    assert h == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    data, real_last = load_all()
    S10.install_all_features(data, real_last)
    uni = universe(data, real_last)
    members = {(y, s) for y, m in zip(uni.year, uni.members) for s in m.split(";")}
    feats = S8.daily_features(data)
    fng = fng_table()
    P = add_features(S10.path2_rows(data, real_last, feats, members), fng)
    F = S8.DAILY + ["btc_k3_state_t", "breadth_k3_up_t"] + FNG_COLS + [f"xr_{c}" for c in RANK_COLS]
    ent, _ = S8.build_sets(data, real_last, feats)
    ent = ent.join(fng, on="signal_date")
    ent["member"] = [(d.year, s) in members for s, d in zip(ent.symbol, ent.signal_date)]
    FS = S8.ENTRY_FEATURES + FNG_COLS
    print(f"rows: path {len(P)}, swing {len(ent)}; features {len(F)} / {len(FS)} ({time.time() - t0:.0f}s)", flush=True)
    claims = dict(protocol_sha256=h, fng_sha256=FNG_SHA, rows_path=len(P), rows_swing=len(ent), n_features=len(F))

    # G-sanity: planted signal through the new (bagged, decayed) pipeline
    Pp = P.copy()
    Pp["planted"] = Pp.label_3 + np.random.default_rng(42).normal(0, 2.79, len(Pp))
    sp, _ = walk_forward(Pp, F + ["planted"], "label_3", "known_3", "date")
    m = Pp.loc[sp.index].member & Pp.loc[sp.index].label_3.notna()
    claims["sanity_planted_auc"] = float(roc_auc_score(Pp.loc[sp.index][m].label_3.astype(int), sp[m]))
    pd.DataFrame(dict(label=Pp.loc[sp.index][m].label_3, prob=sp[m])).to_csv(OUT / "sanity_planted_predictions.csv", index=False)
    print("sanity planted AUC", round(claims["sanity_planted_auc"], 4), flush=True)

    res = {}
    for lab, sh in (("AI", False), ("CONTROL", True)):
        b1, l1 = walk_forward(P, F, "label_1", "known_1", "date", shuffle=sh, seed=1)
        b3, l3 = walk_forward(P, F, "label_3", "known_3", "date", shuffle=sh, seed=3)
        bs, ls = walk_forward(ent, FS, "label", "known_date", "signal_date", shuffle=sh, seed=5, kw=KW_SWING)
        Sg = build_signals(P, b1, b3, ent, bs)
        Sg.to_csv(OUT / f"{lab}_signals.csv", index=False)
        pd.concat([l1.assign(brain="B1"), l3.assign(brain="B3"), ls.assign(brain="BS")]).to_csv(OUT / f"{lab}_training_log.csv", index=False)
        sh_ = Sg[Sg.buy & Sg.shadow_ret.notna()]
        lo, hi = block_ci(sh_.shadow_ret.values, sh_.date.dt.to_period("M").astype(str).values)
        claims[f"{lab}_shadow"] = dict(n=int(len(sh_)), mean_net_pct=float(sh_.shadow_ret.mean() * 100), ci_low_pct=lo * 100,
                                       ci_high_pct=hi * 100, hit_rate=float((sh_.shadow_ret > 0).mean()))
        for k, b, lab_ in (("B1", b1, "label_1"), ("B3", b3, "label_3")):
            mm = P.loc[b.index].member & P.loc[b.index][lab_].notna()
            claims[f"{lab}_{k}_auc"] = float(roc_auc_score(P.loc[b.index][mm][lab_].astype(int), b[mm]))
        tr, eq, cash, mp = simulate(data, real_last, Sg)
        tr.to_csv(OUT / f"{lab}_trades.csv", index=False)
        eq.to_csv(OUT / f"{lab}_equity.csv", index=False)
        claims[f"{lab}_portfolio"] = summary(tr, eq, cash, lab)
        claims[f"{lab}_portfolio"]["monitor_pause_days"] = mp
        if lab == "AI":
            tr2, eq2, cash2, _ = simulate(data, real_last, Sg, friction=2 * E.FRICTION)
            claims["AI_portfolio_double_friction"] = summary(tr2, eq2, cash2, "AI_double_friction")
        res[lab] = Sg
        print(lab, json.dumps({k: v for k, v in claims.items() if k.startswith(lab)}, default=str)[:900], flush=True)

    Rb = P[(P.date >= OOS_START)].assign(prob=0.0, base_rate=0.0)
    eqb, finb, trb = S10.path2_portfolio(data, real_last, Rb, "baseline")
    eqb.to_csv(OUT / "BASELINE_equity.csv", index=False)
    claims["BASELINE_portfolio"] = S10.summarize_curve(eqb, finb, "BASELINE", trb)

    ai, ct, bl = claims["AI_portfolio"], claims["CONTROL_portfolio"], claims["BASELINE_portfolio"]
    years = [ai.get(f"ret_{y}", 0.0) for y in range(2021, 2027)]
    gates = dict(G_sanity=0.57 <= claims["sanity_planted_auc"] <= 0.63,
                 G_skill=claims["AI_shadow"]["ci_low_pct"] > 0 and claims["AI_shadow"]["mean_net_pct"] > claims["CONTROL_shadow"]["mean_net_pct"],
                 G_port=ai["calmar"] > bl["calmar"] and ai["calmar"] > ct["calmar"] and claims["AI_portfolio_double_friction"]["cagr_pct"] > 0,
                 G_years=sum(r > 0 for r in years) >= 4)
    gates["decision"] = "PASS_GO_TO_FORWARD_TESTNET" if all(gates.values()) else "FAIL_NOTHING_DEPLOYED"
    claims["gates"] = gates
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=float))
    print("\nGATES:", json.dumps(gates, default=str), f"({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
