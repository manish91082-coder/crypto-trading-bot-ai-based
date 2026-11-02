"""
Step 13: UNSEEN-COINS EXAM of the Step 12 brain design (spot, 1D, long-only, free data only).
Protocol: logs/strategy_1d_step13_unseen/STEP13_PROTOCOL_PREREGISTERED.md (SHA256 locked before any result).

The brains are trained ONLY on the 30 coins used in Steps 6-12 (monthly walk-forward, labels known before the re-train
date) and are then asked about coins they have never seen (every other USDT spot pair on Binance, incl. delisted ones).
Market-level inputs (breadth, cross-sectional ranks) for the unseen coins are measured against the same 30-coin
reference set the brains were trained with, so an unseen coin cannot change what the brain sees for other coins.
Futures-derived features are NOT used (futures data does not exist for every coin; having a perpetual is itself a
selection effect) -- this "core" brain is otherwise the Step 12 recipe.
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_study_1d as SS
import swing_strategy_1d as E
import step7_swing_ai_1d as S7
import step8_ai_entry_exit_1d as S8
import step9_ai_more_info_1d as S9
import step10_ai_1d as S10
import step11_ai_confident_1d as S11
from step6_4_survivorship_1d import load_all, universe
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step13_unseen"
PROTO_NAME = "STEP13_PROTOCOL_PREREGISTERED.md"
UNI = DATA_DIR / "universe_all"
H1_KNOWN, H1_NEW = DATA_DIR / "raw_1h_full", UNI / "1h"
OOS_START, DATA_END = S8.OOS_START, S8.DATA_END

# Step 12 recipe (plain training)
S11.BAG, S11.DECAY = False, False
KW = S11.KW
KW_SWING = dict(max_depth=3, max_iter=300, learning_rate=0.05, min_samples_leaf=100, l2_regularization=1.0)
RANK_CORE = ["r1", "r5", "r20", "vol_ratio30", "taker_buy_ratio", "dist_hi20_atr"]   # Step 11 ranks minus futures ones

# Unseen-coin test settings (pre-registered)
NEW_FRICTION = 0.0025            # per fill (2x the Step 12 assumption: smaller coins, more slippage)
NEW_ROUND_TRIP = 2 * NEW_FRICTION
LIQ_MIN_USD = 2_000_000          # trailing-30-day mean daily USDT volume, measured up to the row's day (causal)
MIN_DAYS = 120                   # a coin needs >= 120 daily candles in total
BONF_LO, BONF_HI = 0.625, 99.375  # 98.75% interval = 95% with Bonferroni for 2 brains
NOT_CRYPTO = {                    # stablecoins / fiat / wrapped / gold -- excluded by NAME, decided before any result
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "PAXUSDT", "SUSDUSDT", "USDSBUSDT",
    "USDSUSDT", "USTUSDT", "USTCUSDT", "EURUSDT", "GBPUSDT", "AUDUSDT", "BKRWUSDT", "AEURUSDT", "EURIUSDT",
    "USD1USDT", "XUSDUSDT", "RLUSDUSDT", "BFUSDUSDT", "PYUSDUSDT", "USDEUSDT", "TRYUSDT", "BRLUSDT", "ZARUSDT",
    "UAHUSDT", "NGNUSDT", "RUBUSDT", "IDRTUSDT", "BIDRUSDT", "BVNDUSDT", "WBTCUSDT", "WBETHUSDT", "BETHUSDT",
    "PAXGUSDT", "XAUTUSDT", "USDTUSDT", "FRAXUSDT", "USDSOLDUSDT", "KGSTUSDT", "BNSOLUSDT"}
# Binance tokenized stocks / ETFs (ticker + "B"): not crypto assets
STOCK_TOKENS = {f"{t}BUSDT" for t in (
    "AAOI", "AAPL", "ADBE", "AGPU", "ALAB", "AMAT", "AMC", "AMD", "AMZN", "ARM", "ASML", "ASTS", "AVGO", "AXTI", "BABA",
    "BMNR", "BNC", "CBRS", "COHR", "COIN", "CRCL", "CRDO", "CRM", "CRWD", "CRWV", "CYPH", "DELL", "DJT", "DRAM", "EWY",
    "FLNC", "FWDI", "GLW", "GME", "GOOGL", "GPRO", "HIMS", "HOOD", "HPE", "IBM", "INTC", "INTW", "IREN", "KORU", "LITE",
    "META", "MRNA", "MRVL", "MSFT", "MSTR", "MUU", "MVLL", "NBIS", "NFLX", "NOK", "NVDA", "ORCL", "PDD", "PLTR", "PYPL",
    "QCOM", "QNT", "QQQ", "RDDT", "RKLB", "SHAZ", "SKHY", "SMCI", "SMH", "SNDK", "SNXX", "SOXL", "SOXS", "SPCX", "SPY",
    "SQQQ", "STX", "TQQQ", "TSLA", "TSM", "USAR", "WDC", "WEN")}
NOT_CRYPTO |= STOCK_TOKENS
PEG_MEDIAN_ABS_RET = 0.003       # data rule: median |daily close-to-close return| below 0.3 % = pegged asset -> excluded


# ----------------------------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------------------------
def pad_to_end(df, real_last):
    """Same rule as step6_4.load_all: after the last real candle the price is frozen (flat candles, volume 0)."""
    if real_last >= DATA_END:
        return df
    pad_days = pd.date_range(real_last + pd.Timedelta(days=1), DATA_END, freq="D")
    c = float(df["close"].iloc[-1])
    pad = pd.DataFrame(dict(timestamp=pad_days, open=c, high=c, low=c, close=c, volume=0.0))
    df = pd.concat([df[["timestamp", "open", "high", "low", "close", "volume"]], pad], ignore_index=True)
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(), (df.low - df.close.shift()).abs()],
                   axis=1).max(axis=1)
    df["ATR_14"] = tr.rolling(14).mean()
    return df


def load_new(known):
    data, real_last, log = {}, {}, []
    for f in sorted((UNI / "1d").glob("*_1d.csv")):
        s = f.name.split("_")[0]
        why = None
        if s in known:
            why = "known coin (training set)"
        elif s in NOT_CRYPTO:
            why = "not a crypto asset (stable/fiat/wrapped/gold)"
        elif not (H1_NEW / f"{s}_1h_full.csv.gz").exists():
            why = "no 1h file"
        if why is None:
            df = SS.load_1d(s, f)
            df = df[df.timestamp <= DATA_END].reset_index(drop=True)
            if df.close.pct_change().abs().median() < PEG_MEDIAN_ABS_RET:
                why = "pegged price (median daily move < 0.3 %)"
            elif len(df) < MIN_DAYS:
                why = f"only {len(df)} days"
            elif df.timestamp.max() < OOS_START + pd.Timedelta(days=60):
                why = "data ends before the test period"
        if why:
            log.append(dict(symbol=s, used=False, reason=why))
            continue
        real_last[s] = df.timestamp.max()
        data[s] = pad_to_end(df, real_last[s])
        log.append(dict(symbol=s, used=True, first=df.timestamp.min().date(), last=real_last[s].date(), days=len(df)))
    return data, real_last, pd.DataFrame(log)


def reference_breadth(data_k):
    """30-coin market breadth exactly as S7.build_candidates / S8.daily_features compute it."""
    st = pd.DataFrame({s: pd.Series(E.zz(df, 3.0)["state"] == 1, index=df["timestamp"]) for s, df in data_k.items()})
    upev = pd.DataFrame({s: pd.Series(E.zz(df, 3.0)["up"], index=df["timestamp"]) for s, df in data_k.items()})
    avail = pd.DataFrame({s: pd.Series(True, index=df["timestamp"]) for s, df in data_k.items()}).fillna(False)
    breadth = st.fillna(False).sum(axis=1) / avail.sum(axis=1)
    new10 = upev.fillna(False).astype(int).rolling(10, min_periods=1).max().sum(axis=1) / avail.sum(axis=1)
    return breadth, new10


def liquid_flag(data, real_last):
    out = {}
    for s, df in data.items():
        usd = (df.volume * df.close).where(df.timestamp <= real_last[s])
        out[s] = pd.Series((usd.rolling(30, min_periods=30).mean() >= LIQ_MIN_USD).values, index=df.timestamp)
    return out


def rank_vs_reference(ref_vals, ref_dates, vals, dates):
    """pandas rank(pct=True, method='average') of each value inside {reference values of that date} + {the value}."""
    ref = pd.DataFrame(dict(d=ref_dates, v=ref_vals)).dropna().groupby("d").v.apply(lambda x: np.sort(x.values))
    out = np.full(len(vals), np.nan)
    for k, (v, d) in enumerate(zip(vals, dates)):
        if np.isnan(v) or d not in ref.index:
            continue
        r = ref.at[d]
        lo, hi = np.searchsorted(r, v, "left"), np.searchsorted(r, v, "right")
        out[k] = (lo + 1 + (hi - lo) / 2) / (len(r) + 1)
    return out


# ----------------------------------------------------------------------------------------------
# Train on known coins, predict known + unseen
# ----------------------------------------------------------------------------------------------
def wf_transfer(Dk, Dn, feats, label, known, datecol, shuffle=False, seed=0, kw=None):
    rng = np.random.default_rng(seed)
    pk, pn, log = [], [], []
    for k, T in enumerate(pd.date_range(OOS_START, DATA_END, freq="MS")):
        nxt = T + pd.offsets.MonthBegin(1)
        tr = Dk[(Dk[known] < T) & Dk[label].notna()]
        assert (tr[datecol] < T).all() and (tr[known] < T).all()
        y = tr[label].values.astype(int)
        if shuffle:
            y = rng.permutation(y)
        tk = Dk[(Dk[datecol] >= T) & (Dk[datecol] < nxt)]
        tn = Dn[(Dn[datecol] >= T) & (Dn[datecol] < nxt)]
        X = pd.concat([tk[feats], tn[feats]])
        if X.empty:
            continue
        p = S11.fit_predict_bag(tr[feats].values, y, np.zeros(len(y)), X.values, seed_base=k, kw=kw)
        pk.append(pd.Series(p[:len(tk)], index=tk.index))
        pn.append(pd.Series(p[len(tk):], index=tn.index))
        log.append(dict(retrain=T.date(), n_train=len(tr), base_rate=round(y.mean(), 4), n_pred_known=len(tk), n_pred_new=len(tn)))
    return pd.concat(pk), pd.concat(pn), pd.DataFrame(log)


def auc_ci(y, p, months, lo=2.5, hi=97.5, seed=1, reps=2000):
    um = np.unique(months)
    idx = {m: np.where(months == m)[0] for m in um}
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(reps):
        pick = np.concatenate([idx[m] for m in rng.choice(um, len(um))])
        if len(np.unique(y[pick])) == 2:
            bs.append(roc_auc_score(y[pick], p[pick]))
    return dict(n=int(len(y)), auc=float(roc_auc_score(y, p)), ci_low=float(np.percentile(bs, lo)),
                ci_high=float(np.percentile(bs, hi)), base_rate=float(y.mean()))


def skill(P, pred, label, rows_mask, lo=2.5, hi=97.5):
    d = P.loc[pred.index]
    m = rows_mask.loc[pred.index] & d[label].notna()
    return auc_ci(d[m][label].values.astype(int), pred[m].values, d[m].date.dt.to_period("M").astype(str).values, lo, hi)


# ----------------------------------------------------------------------------------------------
def main(smoke=False):
    OUT.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256((OUT / PROTO_NAME).read_bytes()).hexdigest()
    assert h == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h, fng_sha256=S11.FNG_SHA)

    # ---- data ----
    data_k, last_k = load_all()
    data_n, last_n, load_log = load_new(set(data_k))
    load_log.to_csv(OUT / "unseen_coin_selection.csv", index=False)
    if smoke:
        keep = sorted(data_n)[:12]
        data_n, last_n = {s: data_n[s] for s in keep}, {s: last_n[s] for s in keep}
    claims["coins_known"], claims["coins_unseen_used"] = len(data_k), len(data_n)
    claims["coins_unseen_excluded"] = load_log[~load_log.used].reason.value_counts().to_dict()
    print(f"known {len(data_k)} | unseen used {len(data_n)} | excluded {claims['coins_unseen_excluded']} ({time.time()-t0:.0f}s)", flush=True)

    # ---- features (Step 9 1h features installed, futures NOT installed) ----
    all_last = {**last_k, **last_n}
    xstats = S9.install_features({**data_k, **data_n}, all_last)
    S9.H1 = H1_KNOWN
    feats_k = S8.daily_features(data_k)
    S9.H1 = H1_NEW
    btc = {"BTCUSDT": data_k["BTCUSDT"]}
    feats_n = S8.daily_features({**btc, **data_n})
    feats_n.pop("BTCUSDT")
    S9.H1 = H1_KNOWN
    br, new10 = reference_breadth(data_k)
    chk = feats_k["ETHUSDT"]["breadth_k3_up_t"].values
    assert np.allclose(chk.astype(float), data_k["ETHUSDT"].timestamp.map(br).values.astype(float), equal_nan=True),         "reference breadth mismatch"
    for s, f in feats_n.items():
        f["breadth_k3_up_t"] = data_n[s].timestamp.map(br).values
    xs = pd.DataFrame(xstats).T
    xs.to_csv(OUT / "hourly_vs_daily_crosscheck.csv")
    claims["crosscheck_unseen"] = dict(matched=int(xs.loc[list(data_n)].matched.sum()),
                                       mismatched=int(xs.loc[list(data_n)].mismatched.sum()),
                                       no_hourly=int(xs.loc[list(data_n)].no_hourly.sum()))
    print("1h cross-check unseen:", claims["crosscheck_unseen"], f"({time.time()-t0:.0f}s)", flush=True)

    # ---- path rows ----
    uni_k, uni_n = universe(data_k, last_k), universe(data_n, last_n)
    uni_n.to_csv(OUT / "unseen_point_in_time_universe.csv", index=False)
    mem_k = {(y, s) for y, m in zip(uni_k.year, uni_k.members) for s in m.split(";")}
    mem_n = {(y, s) for y, m in zip(uni_n.year, uni_n.members) for s in m.split(";") if s}
    fng = S11.fng_table()
    Pk = S10.path2_rows(data_k, last_k, feats_k, mem_k).join(fng, on="date")
    Pn = S10.path2_rows(data_n, last_n, feats_n, mem_n).join(fng, on="date")
    for c in RANK_CORE:
        Pk[f"xr_{c}"] = Pk.groupby("date")[c].rank(pct=True)
        Pn[f"xr_{c}"] = rank_vs_reference(Pk[c].values, Pk.date.values, Pn[c].values, Pn.date.values)
    # self-test of the reference-rank formula against pandas on 200 random rows
    rs = np.random.default_rng(7).choice(len(Pn), min(200, len(Pn)), replace=False)
    for i in rs:
        v, d = Pn["r5"].iat[i], Pn.date.iat[i]
        if np.isnan(v):
            continue
        ser = pd.concat([Pk.loc[Pk.date == d, "r5"].dropna(), pd.Series([v])], ignore_index=True)
        assert abs(ser.rank(pct=True).iat[-1] - Pn["xr_r5"].iat[i]) < 1e-12
    liq = liquid_flag(data_n, last_n)
    Pn["liquid"] = [bool(liq[s].get(d, False)) for s, d in zip(Pn.symbol, Pn.date)]
    F = S8.DAILY + ["btc_k3_state_t", "breadth_k3_up_t"] + S11.FNG_COLS + [f"xr_{c}" for c in RANK_CORE]
    assert not any(c in F for c in S10.FUT), "futures features must not be used"
    claims.update(rows_known=len(Pk), rows_unseen=len(Pn), rows_unseen_liquid_oos=int((Pn.liquid & (Pn.date >= OOS_START)).sum()),
                  n_features=len(F), features=F)
    print(f"rows known {len(Pk)}, unseen {len(Pn)} (liquid OOS {claims['rows_unseen_liquid_oos']}); {len(F)} features "
          f"({time.time()-t0:.0f}s)", flush=True)

    # ---- swing candidates ----
    ent_k, _ = S8.build_sets(data_k, last_k, feats_k)
    ent_n, _ = S8.build_sets({**btc, **data_n}, {**{"BTCUSDT": last_k["BTCUSDT"]}, **last_n}, {**{"BTCUSDT": feats_k["BTCUSDT"]}, **feats_n})
    ent_n = ent_n[ent_n.symbol != "BTCUSDT"].copy()
    assert np.allclose(ent_k.breadth_k3_up.values.astype(float), ent_k.signal_date.map(br).values.astype(float))
    ent_n["breadth_k3_up"] = ent_n.signal_date.map(br).values
    ent_n["breadth_new_up10"] = ent_n.signal_date.map(new10).values
    ent_k, ent_n = ent_k.join(fng, on="signal_date"), ent_n.join(fng, on="signal_date")
    ent_n = ent_n[[bool(liq[s].get(d, False)) for s, d in zip(ent_n.symbol, ent_n.signal_date)]]
    FS = S8.ENTRY_FEATURES + S11.FNG_COLS
    claims.update(swing_rows_known=len(ent_k), swing_rows_unseen_liquid=len(ent_n))
    print(f"swing rows known {len(ent_k)}, unseen liquid {len(ent_n)} ({time.time()-t0:.0f}s)", flush=True)

    # ---- G1 pipeline checks on unseen coins ----
    rng = np.random.default_rng(42)
    Pk["planted"] = Pk.label_3 + rng.normal(0, 2.79, len(Pk))
    Pn["planted"] = Pn.label_3 + rng.normal(0, 2.79, len(Pn))
    Pk["leak"], Pn["leak"] = Pk.fwd_1, Pn.fwd_1
    liqmask = Pn.liquid & (Pn.date >= OOS_START)
    _, sp, _ = wf_transfer(Pk, Pn, F + ["planted"], "label_3", "known_3", "date")
    _, sl, _ = wf_transfer(Pk, Pn, F + ["leak"], "label_1", "known_1", "date")
    claims["sanity_planted_unseen"] = skill(Pn, sp, "label_3", liqmask)
    claims["sanity_leak_unseen"] = skill(Pn, sl, "label_1", liqmask)
    g1 = dict(planted_ge_055=claims["sanity_planted_unseen"]["auc"] >= 0.55, leak_gt_095=claims["sanity_leak_unseen"]["auc"] > 0.95)
    print("G1:", round(claims["sanity_planted_unseen"]["auc"], 4), round(claims["sanity_leak_unseen"]["auc"], 4), g1,
          f"({time.time()-t0:.0f}s)", flush=True)
    Pk, Pn = Pk.drop(columns=["planted", "leak"]), Pn.drop(columns=["planted", "leak"])
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))

    # ---- AI and shuffled CONTROL ----
    S11.ROUND_TRIP = NEW_ROUND_TRIP
    Pn_l = Pn[Pn.liquid].copy()
    res = {}
    for lab, sh in (("AI", False), ("CONTROL", True)):
        k1, n1, l1 = wf_transfer(Pk, Pn_l, F, "label_1", "known_1", "date", sh, 1, KW)
        k3, n3, l3 = wf_transfer(Pk, Pn_l, F, "label_3", "known_3", "date", sh, 3, KW)
        ks, ns, ls = wf_transfer(ent_k, ent_n, FS, "label", "known_date", "signal_date", sh, 5, KW_SWING)
        pd.concat([l1.assign(brain="B1"), l3.assign(brain="B3"), ls.assign(brain="BS")]).to_csv(OUT / f"{lab}_training_log.csv", index=False)
        all_n = pd.Series(True, index=Pn_l.index)
        for k, pk, pn, labl in (("B1", k1, n1, "label_1"), ("B3", k3, n3, "label_3")):
            claims[f"{lab}_{k}_unseen"] = skill(Pn_l, pn, labl, all_n, BONF_LO, BONF_HI)
            claims[f"{lab}_{k}_known_members_ref"] = skill(Pk, pk, labl, Pk.member)
        Sg = S11.build_signals(Pn_l, n1, n3, ent_n, ns)
        Sg.to_csv(OUT / f"{lab}_signals_unseen.csv", index=False)
        sh_ = Sg[Sg.buy & Sg.shadow_ret.notna()]
        if len(sh_):
            lo, hi = S11.block_ci(sh_.shadow_ret.values, sh_.date.dt.to_period("M").astype(str).values)
        else:
            lo = hi = float("nan")
        claims[f"{lab}_shadow"] = dict(n=int(len(sh_)), mean_net_pct=float(sh_.shadow_ret.mean() * 100) if len(sh_) else float("nan"),
                                       ci_low_pct=lo * 100, ci_high_pct=hi * 100,
                                       hit_rate=float((sh_.shadow_ret > 0).mean()) if len(sh_) else float("nan"))
        tr, eq, cash, mp = S11.simulate(data_n, last_n, Sg, friction=NEW_FRICTION)
        tr.to_csv(OUT / f"{lab}_trades_unseen.csv", index=False)
        eq.to_csv(OUT / f"{lab}_equity_unseen.csv", index=False)
        claims[f"{lab}_portfolio"] = S11.summary(tr, eq, cash, lab)
        claims[f"{lab}_portfolio"]["monitor_pause_days"] = mp
        print(lab, {k: v for k, v in claims.items() if k.startswith(lab)}, f"({time.time()-t0:.0f}s)", flush=True)
        (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))

    fr = E.FRICTION
    E.FRICTION = NEW_FRICTION
    try:
        Rb = Pn[Pn.date >= OOS_START].assign(prob=0.0, base_rate=0.0)
        eqb, finb, trb = S10.path2_portfolio(data_n, last_n, Rb, "baseline")
    finally:
        E.FRICTION = fr
    eqb.to_csv(OUT / "BASELINE_equity_unseen.csv", index=False)
    claims["BASELINE_portfolio"] = S10.summarize_curve(eqb, finb, "BASELINE", trb)

    def brain_pass(k):
        a, c = claims[f"AI_{k}_unseen"], claims[f"CONTROL_{k}_unseen"]
        return a["ci_low"] > 0.50 and a["auc"] > c["auc"]
    ai, ct, bl = claims["AI_portfolio"], claims["CONTROL_portfolio"], claims["BASELINE_portfolio"]
    gates = dict(G1_pipeline=all(g1.values()),
                 G2_skill_B1=brain_pass("B1"), G2_skill_B3=brain_pass("B3"),
                 G3_shadow=bool(claims["AI_shadow"]["ci_low_pct"] > 0),
                 G3_portfolio=bool(ai["cagr_pct"] > 0 and ai["calmar"] > ct["calmar"] and ai["calmar"] > bl["calmar"]),
                 G3_years=sum(ai.get(f"ret_{y}", 0.0) > 0 for y in range(2021, 2027)) >= 4)
    gates = {k: bool(v) for k, v in gates.items()}
    gates["G2_skill"] = gates["G2_skill_B1"] or gates["G2_skill_B3"]
    g3 = gates["G3_shadow"] and gates["G3_portfolio"] and gates["G3_years"]
    gates["decision"] = ("PASS_BRAIN_GENERALISES" if gates["G1_pipeline"] and gates["G2_skill"] and g3 else
                         "PARTIAL_SKILL_BUT_TRADING_RULE_FAILS" if gates["G1_pipeline"] and gates["G2_skill"] else
                         "INVALID_PIPELINE_CHECK_FAILED" if not gates["G1_pipeline"] else "FAIL_NO_TRANSFERABLE_SKILL")
    claims["gates"] = gates
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates, default=str), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main(smoke="--smoke" in sys.argv)
