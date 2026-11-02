"""
Step 7: swing permutation matrix (every swing entry x every exit plan) + continuously re-trained learner.
Protocol: logs/strategy_1d_step6/STEP6_7_PROTOCOL_PREREGISTERED.md (written before any result).

1. Candidates  : every real-time ZigZag UP event (K = 2, 3, 4; incl. flip-ups) per coin; one row per coin-day.
                 Entry = next day's open. Swing reference low = the ref of the largest K that fired.
2. Exit menu   : 13 plans (stop atr1.5/swing x exit_k 2/3/4 x breakeven off/2 ATR, + config.py Law #6 runner).
3. Matrix      : each candidate x plan is simulated as a standalone trade with the SAME position functions as the
                 portfolio engine (E.open_position / E.intraday / E.close_exit_reason) -> net return, exit date.
4. Features    : causal swing structure only (see FEATURES).
5. Learner     : one HistGradientBoostingRegressor per plan, target log(1+net return), re-trained on the 1st of
                 every month from candidates whose outcome (for that plan) was complete BEFORE that day.
6. Decision    : plan = argmax prediction; trade only if prediction > 0; candidates ranked by prediction.
                 Portfolio = same engine, 20% reserve, 8 slots, 2% risk cap, 15% DD pause; one continuous run.
7. Control     : identical pipeline with shuffled training labels.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_strategy_1d as E
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step7_ai"
DATA_END = pd.Timestamp("2026-09-30")
OOS_START = pd.Timestamp("2021-01-01")
RESERVE = 0.20
MIN_TRAIN = 150
KS = (2.0, 3.0, 4.0)


def _plan(**kw):
    base = E.Config("ZZ", 4.0, False, 1.5, None, True, None).exit_plan()
    base.update(kw)
    return base


PLANS = {}
for sm in ("atr", "swing"):
    for xk in KS:
        for be in (None, 2.0):
            PLANS[f"{sm}|x{xk:g}|be{be}"] = _plan(stop_mode=sm, stop_atr=1.5, exit_k=xk, be_atr=be)
PLANS["law6_runner"] = _plan(stop_mode="atr", stop_atr=1.5, exit_k=4.0, be_atr=1.5, partial_atr=3.0, partial_frac=0.75,
                             runner_lock_atr=1.0, runner_trail_atr=2.0, inact_days=14)

FEATURES = ["fired_k2", "fired_k3", "fired_k4", "is_flip", "rise_pct", "rise_atr", "k3_prev_down_pct", "k3_prev_up_pct",
            "k3_higher_low", "k3_dist_prev_high_pct", "wave_k2_in_k4", "coin_k4_state", "coin_k4_age",
            "btc_k3_state", "btc_k3_age", "btc_k4_state", "breadth_k3_up", "breadth_new_up10", "ret20_pct", "atr_pct",
            "k3_flip_rate_2y"]


# ----------------------------------------------------------------------------------------------
# Causal swing features
# ----------------------------------------------------------------------------------------------
def _state_age(state):
    age = np.zeros(len(state), int)
    for i in range(1, len(state)):
        age[i] = age[i - 1] + 1 if state[i] == state[i - 1] else 0
    return age


def k3_structure(df):
    """Per day (causal): last confirmed swing high, latest and previous swing lows, from K=3 events up to that day."""
    z = E.zz(df, 3.0)
    n = len(df)
    last_hi, last_lo, prev_lo, prev_hi = (np.full(n, np.nan) for _ in range(4))
    flips = np.zeros(n)
    evs = np.zeros(n)
    by_day = {}
    for e in sorted(z["events"], key=lambda e: e["seq"]):
        by_day.setdefault(e["confirm_idx"], []).append(e)
    hi = lo = plo = phi = np.nan
    for i in range(n):
        for e in by_day.get(i, []):
            if e["kind"] == "H":
                phi, hi = hi, e["ref_price"]
            else:
                plo, lo = lo, e["ref_price"]
            evs[i] += 1
            flips[i] += e["flip"]
        last_hi[i], last_lo[i], prev_lo[i], prev_hi[i] = hi, lo, plo, phi
    roll = lambda a: pd.Series(a).rolling(730, min_periods=1).sum().values
    rate = roll(flips) / np.maximum(roll(evs), 1)
    return last_hi, last_lo, prev_lo, prev_hi, rate


def build_candidates(data, include_last=False):
    btc = data["BTCUSDT"]
    b3, b4 = E.zz(btc, 3.0)["state"], E.zz(btc, 4.0)["state"]
    btc_tab = pd.DataFrame(dict(btc_k3_state=b3, btc_k3_age=_state_age(b3), btc_k4_state=b4), index=btc["timestamp"])
    # market breadth from every coin's K3 state / K3 up events (causal per day)
    st = pd.DataFrame({s: pd.Series(E.zz(df, 3.0)["state"] == 1, index=df["timestamp"]) for s, df in data.items()})
    upev = pd.DataFrame({s: pd.Series(E.zz(df, 3.0)["up"], index=df["timestamp"]) for s, df in data.items()})
    avail = pd.DataFrame({s: pd.Series(True, index=df["timestamp"]) for s, df in data.items()}).fillna(False)
    breadth = (st.fillna(False).sum(axis=1) / avail.sum(axis=1)).rename("breadth_k3_up")
    new10 = (upev.fillna(False).astype(int).rolling(10, min_periods=1).max().sum(axis=1) / avail.sum(axis=1)).rename("breadth_new_up10")
    rows = []
    for s, df in data.items():
        z = {k: E.zz(df, k) for k in KS}
        c4 = z[4.0]["state"]
        c4age = _state_age(c4)
        last_hi, last_lo, prev_lo, prev_hi, frate = k3_structure(df)
        k2_since_k4 = np.zeros(len(df), int)
        cnt = 0
        for i in range(len(df)):
            if z[4.0]["up"][i]:
                cnt = 0
            cnt += int(z[2.0]["up"][i])
            k2_since_k4[i] = cnt
        cl, atr = df["close"].values, df["ATR_14"].values
        ts = df["timestamp"]
        for i in range(len(df) - (0 if include_last else 1)):     # live: the last closed day is a candidate too
            fired = [k for k in KS if z[k]["up"][i]]
            if not fired or np.isnan(atr[i]) or i < 20:
                continue
            ref = z[max(fired)]["up_ref"][i]
            d = ts.iloc[i]
            rows.append(dict(symbol=s, signal_date=d, signal_idx=i, ref_low=ref,
                             fired_k2=int(2.0 in fired), fired_k3=int(3.0 in fired), fired_k4=int(4.0 in fired),
                             is_flip=int(any(z[k]["up_flip"][i] for k in fired)),
                             rise_pct=cl[i] / ref - 1, rise_atr=(cl[i] - ref) / atr[i],
                             k3_prev_down_pct=last_lo[i] / last_hi[i] - 1 if last_hi[i] > 0 else np.nan,
                             k3_prev_up_pct=last_hi[i] / prev_lo[i] - 1 if prev_lo[i] > 0 else np.nan,
                             k3_higher_low=float(last_lo[i] > prev_lo[i]) if prev_lo[i] > 0 else np.nan,
                             k3_dist_prev_high_pct=cl[i] / last_hi[i] - 1 if last_hi[i] > 0 else np.nan,
                             wave_k2_in_k4=k2_since_k4[i], coin_k4_state=c4[i], coin_k4_age=c4age[i],
                             **btc_tab.loc[d].to_dict(), breadth_k3_up=breadth.loc[d], breadth_new_up10=new10.loc[d],
                             ret20_pct=cl[i] / cl[i - 20] - 1, atr_pct=atr[i] / cl[i], k3_flip_rate_2y=frate[i]))
    return pd.DataFrame(rows).sort_values(["signal_date", "symbol"]).reset_index(drop=True)


# ----------------------------------------------------------------------------------------------
# Permutation matrix: standalone trade per candidate x plan (same position code as the portfolio engine)
# ----------------------------------------------------------------------------------------------
def standalone(df, sig_i, ref, plan, dn, k2ref, end_i):
    o, h, l, c, a = (df[x].values for x in ("open", "high", "low", "close", "ATR_14"))
    e = sig_i + 1
    if e > end_i:
        return None
    p = E.open_position("", df["timestamp"].iloc[sig_i], df["timestamp"].iloc[e], o[e], a[sig_i], ref, plan,
                        units=1.0 / o[e], cost=(1.0 + E.FRICTION))
    if p is None:
        return dict(ret=np.nan, exit_idx=e, reason="invalid_stop", mfe=np.nan)
    hi = o[e]
    for j in range(e, end_i + 1):
        hi = max(hi, h[j])
        for kind, raw, q in E.intraday(p, o[j], h[j], l[j], c[j], k2ref[j]):
            p["proceeds"] += q * raw * (1 - E.FRICTION)
            if kind == "partial":
                p["units"] -= q
            else:
                return dict(ret=p["proceeds"] / p["cost"] - 1, exit_idx=j, reason=kind, mfe=hi / o[e] - 1)
        why = E.close_exit_reason(p, c[j], dn, j)
        if why and j + 1 <= end_i:
            p["proceeds"] += p["units"] * o[j + 1] * (1 - E.FRICTION)
            return dict(ret=p["proceeds"] / p["cost"] - 1, exit_idx=j + 1, reason=why, mfe=max(hi, h[j + 1]) / o[e] - 1)
    return dict(ret=np.nan, exit_idx=None, reason="open_at_data_end", mfe=hi / o[e] - 1)   # outcome not known yet


def build_matrix(data, cands, end=None):
    end = DATA_END if end is None else pd.Timestamp(end)
    end_idx = {s: min(int(np.searchsorted(df["timestamp"].values, np.datetime64(end), side="right")) - 1, len(df) - 1)
               for s, df in data.items()}
    aux = {s: dict(dn={k: E.zz(df, k)["dn"] for k in KS},
                   k2=np.where(E.zz(df, 2.0)["up"], E.zz(df, 2.0)["up_ref"], np.nan)) for s, df in data.items()}
    out = cands.copy()
    for name, plan in PLANS.items():
        rets, exits, reasons, mfes = [], [], [], []
        for r in cands.itertuples():
            df = data[r.symbol]
            res = standalone(df, r.signal_idx, r.ref_low, plan, aux[r.symbol]["dn"], aux[r.symbol]["k2"], end_idx[r.symbol])
            if res is None:
                res = dict(ret=np.nan, exit_idx=None, reason="no_entry_day", mfe=np.nan)
            rets.append(res["ret"])
            exits.append(df["timestamp"].iloc[res["exit_idx"]] if res["exit_idx"] is not None else pd.NaT)
            reasons.append(res["reason"])
            mfes.append(res["mfe"])
        out[f"ret::{name}"] = rets
        out[f"exit::{name}"] = exits
        out[f"why::{name}"] = reasons
        out[f"mfe::{name}"] = mfes
    return out


# ----------------------------------------------------------------------------------------------
# Continuous (monthly) walk-forward learner
# ----------------------------------------------------------------------------------------------
def fit_models(mx, T, shuffle_rng=None):
    """One model per exit plan, trained ONLY on outcomes completed before T (used by the backtest AND the live engine)."""
    T = pd.Timestamp(T)
    models, log = {}, []
    for name in PLANS:
        tr = mx[(mx[f"exit::{name}"] < T) & mx[f"ret::{name}"].notna()]
        assert (tr["signal_date"] < T).all() and (tr[f"exit::{name}"] < T).all()   # no outcome from the future
        if len(tr) < MIN_TRAIN:
            models[name] = None
            continue
        y = np.log1p(tr[f"ret::{name}"].values)
        if shuffle_rng is not None:
            y = shuffle_rng.permutation(y)
        m = HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=40,
                                          l2_regularization=1.0, random_state=0)
        m.fit(tr[FEATURES].values, y)
        models[name] = m
        log.append(dict(retrain=T.date(), plan=name, n_train=len(tr), train_mean_logret=y.mean()))
    return models, log


def predict(models, rows):
    P = pd.DataFrame(index=rows.index)
    for name in PLANS:
        P[name] = models[name].predict(rows[FEATURES].values) if models.get(name) is not None else np.nan
    return P


def walk_forward_predictions(mx, shuffle=False, seed=0):
    rng = np.random.default_rng(seed)
    months = pd.date_range(OOS_START, DATA_END, freq="MS")
    preds, log = [], []
    for T in months:
        nxt = T + pd.offsets.MonthBegin(1)
        test = mx[(mx.signal_date >= T) & (mx.signal_date < nxt)]
        if test.empty:
            continue
        models, mlog = fit_models(mx, T, rng if shuffle else None)
        log += mlog
        preds.append(predict(models, test))
    P = pd.concat(preds)
    best = P.idxmax(axis=1, skipna=True)
    out = mx.loc[P.index, ["symbol", "signal_date", "signal_idx", "ref_low"]].copy()
    out["best_plan"] = best
    out["best_pred"] = P.max(axis=1, skipna=True)
    for c in P.columns:
        out[f"pred::{c}"] = P[c]
    return out, pd.DataFrame(log)


def portfolio(data, pred):
    cfg = E.Config("ZZ", 4.0, False, 1.5, None, True, None, 8, 0.15, False)
    sigs = E.build_signals(data, cfg)
    for s in data:                                    # swing stop reference = the candidate's own swing low
        ref = np.full(len(data[s]), np.nan)
        sub = pred[pred.symbol == s]
        ref[sub.signal_idx.values] = sub.ref_low.values
        sigs[s]["ref"] = ref
    table = {(r.symbol, r.signal_idx): r for r in pred.itertuples()}

    def policy(s, i, d):
        r = table.get((s, i))
        if r is None or pd.isna(r.best_pred) or r.best_pred <= 0:
            return None
        return float(r.best_pred), PLANS[r.best_plan]

    tr, eq, cash, _ = E.simulate_state(data, cfg, str(OOS_START.date()), str(DATA_END.date()), signals=sigs,
                                       reserve=RESERVE, policy=policy)
    return tr, eq, cash


def summarize(tr, eq, cash, label):
    curve = np.concatenate([[E.INITIAL_CAPITAL], eq["equity"].values[:-1], [cash]])
    peak = np.maximum.accumulate(curve)
    dd = (peak - curve) / peak
    years = (eq["date"].iloc[-1] - OOS_START).days / 365.25
    cagr = (cash / E.INITIAL_CAPITAL) ** (1 / years) - 1
    r = pd.Series(curve).pct_change().dropna()
    ye = eq.set_index("date")["equity"].resample("YE").last()
    ye.iloc[-1] = cash
    yr = (ye / ye.shift(1).fillna(E.INITIAL_CAPITAL) - 1) * 100
    return dict(run=label, final=round(cash, 2), total_return_pct=round((cash / E.INITIAL_CAPITAL - 1) * 100, 2),
                cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd.max() * 100, 2), calmar=round(cagr / dd.max(), 3),
                sharpe=round(r.mean() / r.std() * np.sqrt(365), 3), trades=len(tr),
                win_rate=round((tr.pnl > 0).mean() * 100, 2) if len(tr) else 0,
                profit_factor=round(tr.loc[tr.pnl > 0, "pnl"].sum() / -tr.loc[tr.pnl <= 0, "pnl"].sum(), 3) if len(tr) else np.nan,
                **{f"ret_{y.year}": round(v, 2) for y, v in yr.items()})


def describe(mx):
    """Right/wrong entries and exits across the whole permutation matrix (descriptive, includes hindsight)."""
    R = mx[[f"ret::{n}" for n in PLANS]]
    full = mx[R.notna().all(axis=1)].copy()
    Rf = full[[f"ret::{n}" for n in PLANS]]
    full["oracle_best_ret_HINDSIGHT"] = Rf.max(axis=1)
    full["oracle_best_plan_HINDSIGHT"] = Rf.idxmax(axis=1).str.replace("ret::", "")
    full["any_exit_profitable_HINDSIGHT"] = Rf.max(axis=1) > 0
    full["entry_type"] = (full.fired_k4.map({1: "K4"}).fillna("") + full.fired_k3.map({1: "K3"}).fillna("") +
                          full.fired_k2.map({1: "K2"}).fillna("") + full.is_flip.map({1: "+flip", 0: ""}) +
                          full.btc_k3_state.map({1: "|BTCup", -1: "|BTCdown", 0: "|BTCnone"}))
    ent = full.groupby("entry_type").agg(candidates=("symbol", "size"),
                                         pct_with_a_profitable_exit=("any_exit_profitable_HINDSIGHT", "mean"),
                                         **{f"mean_{n}": (f"ret::{n}", "mean") for n in PLANS}).round(4)
    ex = pd.DataFrame([dict(plan=n, trades=Rf[f"ret::{n}"].size, mean_ret=Rf[f"ret::{n}"].mean(),
                            median_ret=Rf[f"ret::{n}"].median(), win_rate=(Rf[f"ret::{n}"] > 0).mean(),
                            best_plan_share_HINDSIGHT=(full.oracle_best_plan_HINDSIGHT == n).mean(),
                            median_capture_of_mfe=(full[f"ret::{n}"] / full[f"mfe::{n}"]).replace([np.inf, -np.inf], np.nan)
                            [full[f"ret::{n}"] > 0].median())
                       for n in PLANS]).round(4)
    return full, ent, ex


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    data = E.load_universe()
    cands = build_candidates(data)
    print(f"candidates: {len(cands)} ({cands.signal_date.min().date()}..{cands.signal_date.max().date()})", flush=True)
    mx = build_matrix(data, cands)
    mx.to_csv(OUT / "swing_permutation_matrix.csv", index=False)
    print(f"matrix: {len(mx)} entries x {len(PLANS)} exits built in {time.time() - t0:.0f}s", flush=True)
    full, ent, ex = describe(mx)
    ent.to_csv(OUT / "entry_types_right_wrong.csv")
    ex.to_csv(OUT / "exit_plans_right_wrong.csv", index=False)
    print(ex.to_string(index=False), flush=True)

    res = []
    for label, shuffle in (("AI_monthly_retrain", False), ("CONTROL_shuffled_labels", True)):
        pred, log = walk_forward_predictions(mx, shuffle=shuffle)
        pred.to_csv(OUT / f"{label}_predictions.csv", index=False)
        log.to_csv(OUT / f"{label}_training_log.csv", index=False)
        tr, eq, cash = portfolio(data, pred)
        tr.drop(columns=["plan"], errors="ignore").to_csv(OUT / f"{label}_trades.csv", index=False)
        eq.to_csv(OUT / f"{label}_equity.csv", index=False)
        assert abs(E.INITIAL_CAPITAL + tr["pnl"].sum() - cash) < 1e-6
        s = summarize(tr, eq, cash, label)
        res.append(s)
        print(pd.Series(s).to_string(), f"\n({time.time() - t0:.0f}s)", flush=True)
    pd.DataFrame(res).to_csv(OUT / "oos_summary.csv", index=False)


if __name__ == "__main__":
    main()
