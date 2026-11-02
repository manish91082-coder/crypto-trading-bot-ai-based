"""A2: knowledge store + replay test + leak canary.
Protocol logs/r2_4h_a2/A2_PROTOCOL_PREREGISTERED.md, with A0 amendments 1 (b89f0a82) and 2 (1b49a9de): swing features come from
the REAL-TIME pivot list at T; rows = corrected A1 trades (logs/r2_4h_a1/correction/a1c_trades.parquet).
Store: features computed on FULL data with causal rules. Replay: the ORIGINAL legs_for on data truncated at T (with a synthetic
final pivot so the in-progress leg exists). No model on real features is trained here.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ladder_sessions as L
import probe_scalein as P
import swing_anatomy_phase1 as SA
import r2_realtime_pivots as RT

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "r2_4h_a2"
STORE = ROOT / "data" / "derived" / "r2_a2"
A1T = ROOT / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet"
SIG = {"S-LAD": 0, "S-BRK": 1, "S-TRD": 2, "S-DTB": 3}
F6 = ["oi_chg1", "oi_chg7", "top_ls_acc", "top_ls_pos", "global_ls", "taker_ls_vol"]
SEED, NREP = 20261019, 200


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def context(coin, b, h1raw, btc_b, fng, upto=None):
    """factor inputs for 4h bars b (already truncated if upto is set)."""
    d1 = SA.load_spliced(coin, "1d", [])
    if upto is not None:
        d1 = d1[d1.timestamp + pd.Timedelta(days=1) <= upto].reset_index(drop=True)
    hb = {"1D": SA.clip_atr(d1)[0], "1W": SA.clip_atr(SA.agg(d1, "W-MON"))[0], "1M": SA.clip_atr(SA.agg(d1, "MS"))[0]}
    htf = {hh: (SA.end_times(hh, hb[hh].timestamp.values), SA.E.zz(hb[hh], SA.KP)["state"]) for hh in hb}
    btc = None
    if btc_b is not None:
        btc = (btc_b.timestamp.values, SA.base_factors(btc_b).ret20.values, SA.E.zz(btc_b, SA.KP)["state"],
               SA.end_times("4h", btc_b.timestamp.values))
    h1 = (h1raw.timestamp.values, h1raw.low.values, h1raw.high.values, h1raw.quote_volume.values)
    sup, res = SA.sr_nearest(b)
    return dict(fac=SA.base_factors(b), sup=sup, res=res, h1=h1, htf=htf, btc=btc, fng=fng)


def cblock(i, b, cx, ccols):
    """the c_* block of swing_anatomy_phase1.legs_for, evaluated at bar index i (copied logic, causal)."""
    ts, cl, atr = b.timestamp.values, b.close.values, b.ATR_14.values
    et = SA.end_times("4h", ts)
    out = {f"c_{f}": cx["fac"][f].values[i] for f in cx["fac"].columns}
    price, a_ = cl[i], atr[i]
    out["c_sup_dist_atr"] = (price - cx["sup"][i]) / a_
    out["c_res_dist_atr"] = (cx["res"][i] - price) / a_
    tend = et[i]
    out["c_vap_at_price"] = SA.vap_at(cx["h1"], tend, price, 0.25 * a_, SA.VAP_W["4h"].to_timedelta64())
    for hh in SA.HTF_LIST:
        out[f"c_htf_state_{hh}"] = float(SA.state_lookup(cx["htf"][hh], np.array([tend]))[0]) if SA.ORDER[hh] < SA.ORDER["4h"] else np.nan
    if cx["btc"] is not None:
        bts, bret, bst, bet = cx["btc"]
        j = np.searchsorted(bet, tend, "right") - 1
        out["c_btc_ret20"], out["c_btc_state_same_tf"] = (bret[j], bst[j]) if j >= 0 else (np.nan, np.nan)
    else:
        out["c_btc_ret20"], out["c_btc_state_same_tf"] = np.nan, np.nan
    day = (pd.Timestamp(tend) - pd.Timedelta(microseconds=1)).normalize() - pd.Timedelta(days=1)
    out["c_fng"] = cx["fng"]["fng"].get(day, np.nan)
    out["c_fng_chg7"] = cx["fng"]["fng_chg7"].get(day, np.nan)
    st = pd.Timestamp(ts[i])
    out["c_hour"], out["c_weekday"] = st.hour, st.weekday()
    return {c: out.get(c, np.nan) for c in ccols}


def swing_feats_from_list(cur, b, cx, ccols):
    atr = b.ATR_14.values
    x = {c: np.nan for c in ccols}
    x.update(last_leg_move_atr=np.nan, last_leg_bars=np.nan, ladder_k=np.nan, retr_last=np.nan)
    if not cur:
        return x
    x.update(cblock(cur[-1]["ci"], b, cx, ccols))
    if len(cur) >= 2:
        p1, p2 = cur[-1], cur[-2]
        x["last_leg_move_atr"] = abs(p1["price"] - p2["price"]) / atr[p2["idx"]]
        x["last_leg_bars"] = p1["idx"] - p2["idx"]
    s = cur[-1]["state"]
    k = 0
    if s in ("UP", "DOWN"):
        step = "H" if s == "UP" else "L"
        for p in reversed(cur):
            if p["state"] != s:
                break
            k += int(p["kind"] == step)
    x["ladder_k"] = k
    if len(cur) >= 3:
        m1, m0 = abs(cur[-1]["price"] - cur[-2]["price"]), abs(cur[-2]["price"] - cur[-3]["price"])
        x["retr_last"] = m1 / m0 if m0 else np.nan
    return x


def live_lists(tl, Ts):
    """live pivot list (each pivot carries the state at its own confirmation) after all events <= T, for sorted Ts."""
    cur, i, out = [], 0, []
    for T in Ts:
        t64 = np.datetime64(T)
        while i < len(tl.ev) and tl.times[i] <= t64:
            e = tl.ev[i]
            if e["flip"]:
                cur.pop()
            else:
                cur.append(dict(idx=e["pivot_idx"], kind=e["kind"], price=e["ref_price"], ci=e["confirm_idx"],
                                label=RT.label_of(cur, e["kind"], e["ref_price"])))
                cur[-1]["state"] = RT.state_now(cur)
            i += 1
        out.append([dict(p) for p in cur[-80:]])
    return out


def metric_feats(m, T):
    d = pd.Timestamp(T).floor("D")
    v = lambda day, col: m[col].get(day, np.nan)
    o1, o2, o8 = v(d - pd.Timedelta(days=1), "oi"), v(d - pd.Timedelta(days=2), "oi"), v(d - pd.Timedelta(days=8), "oi")
    return dict(oi_chg1=o1 / o2 - 1 if np.isfinite(o1) and np.isfinite(o2) and o2 else np.nan,
                oi_chg7=o1 / o8 - 1 if np.isfinite(o1) and np.isfinite(o8) and o8 else np.nan,
                **{c: v(d - pd.Timedelta(days=1), c) for c in ["top_ls_acc", "top_ls_pos", "global_ls", "taker_ls_vol"]})


def funding_feat(f, T):
    i = np.searchsorted(f.time.values, np.datetime64(T), "right") - 1
    return dict(funding_last=f.funding_rate.values[i] if i >= 0 else np.nan)


def load_aux(coin):
    m = pd.read_csv(ROOT / "data" / "futures_info" / f"{coin}_metrics_daily.csv", parse_dates=["date"]).set_index("date")
    f = pd.read_csv(ROOT / "data" / "futures_um" / f"{coin}_funding.csv")
    f["time"] = pd.to_datetime(f["time"])
    return m, f.sort_values("time").reset_index(drop=True)


def build_store(ccols):
    t = pd.read_parquet(A1T)
    fng = SA.fng_table()
    btc_b, _ = RT.bars4h("BTCUSDT")
    rows = []
    for coin, tc in t.groupby("coin"):
        b, h = RT.bars4h(coin)
        cx = context(coin, b, h, None if coin == "BTCUSDT" else btc_b, fng)
        tl = RT.Timeline(b)
        tc = tc.sort_values("entry_time")
        lists = live_lists(tl, list(pd.to_datetime(tc.entry_time)))
        m, f = load_aux(coin)
        pb = P.bars(coin, "4h")
        idx = {ts: i for i, ts in enumerate(pb.index)}
        O, C = pb.open.values, pb.close.values
        for r, cur in zip(tc.itertuples(index=False), lists):
            T = pd.Timestamp(r.entry_time)
            x = dict(signal=r.signal, coin=coin, side_str=r.side, entry_time=T, available_at=T, perp_ok=r.perp_ok, period=r.period,
                     net_base=r.net_base, label=int(r.net_base > 0), signal_type=SIG[r.signal], side=1 if r.side == "long" else -1)
            x.update(swing_feats_from_list(cur, b, cx, ccols)); x.update(metric_feats(m, T)); x.update(funding_feat(f, T))
            e = idx[T]
            x["canary_next_ret"] = C[e + 5] / O[e] - 1 if e + 5 < len(C) else np.nan
            rows.append(x)
        print(coin, len(rows), flush=True)
    return pd.DataFrame(rows)


def rebuild(coin, T, cache, ccols):
    """replay: ORIGINAL legs_for on data truncated at T, with a synthetic final pivot appended (in-progress leg)."""
    def raw(c):
        if c not in cache:
            cache[c] = SA.load_spliced(c, "1h", [])
        h = cache[c]
        return h[h.timestamp + pd.Timedelta(hours=1) <= T].reset_index(drop=True)
    SA.E._ZZ_CACHE.clear()
    h_tr = raw(coin)
    b = SA.clip_atr(SA.agg(h_tr, "4h"))[0]
    btc_b = None if coin == "BTCUSDT" else SA.clip_atr(SA.agg(raw("BTCUSDT"), "4h"))[0]
    fng = SA.fng_table()
    fng = fng[fng.index < T.normalize()]
    cx = context(coin, b, h_tr, btc_b, fng, upto=T)
    orig = SA.SS.zigzag_pivots

    def patched(df, k, events=None):
        piv = orig(df, k, events)
        if piv:
            last = piv[-1]
            piv = piv + [dict(idx=len(df) - 1, tick=4 * len(df) - 1, kind="L" if last["kind"] == "H" else "H",
                              price=float(df.close.values[-1]), confirm_idx=len(df) - 1, ev=-1)]
        return piv
    SA.SS.zigzag_pivots = patched
    try:
        Lg = SA.legs_for(coin, "4h", b, 3.0, cx["fac"], cx["sup"], cx["res"], cx["h1"], cx["htf"], cx["btc"], cx["fng"])
    finally:
        SA.SS.zigzag_pivots = orig
    Lg = Lg.reset_index(drop=True)            # keep pivot order (no sort: same-candle ties)
    x = {c: np.nan for c in ccols}
    x.update(last_leg_move_atr=np.nan, last_leg_bars=np.nan, ladder_k=np.nan, retr_last=np.nan)
    if len(Lg) == 0:
        return x
    last = Lg.iloc[-1]                         # in-progress leg: starts at the latest confirmed pivot
    for c in ccols:
        x[c] = last[c]
    if len(Lg) >= 2:
        x["last_leg_move_atr"], x["last_leg_bars"] = Lg.move_atr.iloc[-2], Lg.bars.iloc[-2]
    pt = L.points(Lg)
    kn = pt[pt.known_time.notna() & (pd.to_datetime(pt.known_time) <= T)]
    if len(kn):
        p = kn.index[-1]
        s = pt.state.values[p]
        k = 0
        if s in ("UP", "DOWN"):
            step = "H" if s == "UP" else "L"
            i = p
            while i >= 0 and pt.state.values[i] == s:
                k += int(pt.typ.values[i] == step); i -= 1
        x["ladder_k"] = k
        prev = pt.move.values[p - 1] if p >= 1 else np.nan
        x["retr_last"] = pt.move.values[p] / prev if p >= 1 and prev else np.nan
    return x


def same(a, b):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if np.isnan(a) and np.isnan(b):
        return True
    return bool(np.isclose(a, b, rtol=1e-9, atol=1e-12))


def replay(S, ccols):
    rng = np.random.default_rng(SEED)
    cand = S[S.available_at >= "2020-06-01"].index.values
    pick = rng.choice(cand, size=NREP, replace=False)
    feats = ccols + ["last_leg_move_atr", "last_leg_bars", "ladder_k", "retr_last"] + F6 + ["funding_last", "canary_next_ret"]
    cache, aux, out = {}, {}, []
    for n, i in enumerate(pick):
        r = S.loc[i]
        T, coin = pd.Timestamp(r.available_at), r.coin
        x = rebuild(coin, T, cache, ccols)
        if coin not in aux:
            aux[coin] = load_aux(coin)
        m, f = aux[coin]
        x.update(metric_feats(m[m.index < T.floor("D")], T))
        x.update(funding_feat(f[f.time <= T].reset_index(drop=True), T))
        hb = cache[coin]
        b4 = SA.agg(hb[hb.timestamp + pd.Timedelta(hours=1) <= T], "4h")
        e = np.searchsorted(b4.timestamp.values, np.datetime64(T))
        x["canary_next_ret"] = b4.close.values[e + 5] / b4.open.values[e] - 1 if e + 5 < len(b4) else np.nan
        row = dict(row=int(i), coin=coin, T=T, signal=r.signal)
        for c in feats:
            row[c] = int(not same(r[c], x[c]))
        out.append(row)
        if n % 20 == 0:
            print(f"replay {n}/{NREP}", flush=True)
    return pd.DataFrame(out), feats


def main():
    OUT.mkdir(parents=True, exist_ok=True); STORE.mkdir(parents=True, exist_ok=True)
    a0 = ROOT / "logs" / "r2_4h_a0"
    for f, s in (("A0_4H_PROTOCOL_PREREGISTERED.md", "A0_PROTOCOL_SHA256.txt"), ("A0_AMENDMENT_1.md", "A0_AMENDMENT_1_SHA256.txt"),
                 ("A0_AMENDMENT_2.md", "A0_AMENDMENT_2_SHA256.txt")):
        assert sha(a0 / f) == (a0 / s).read_text().split()[0], f
    proto = OUT / "A2_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "A2_PROTOCOL_SHA256.txt").read_text().split()[0]
    ccols = [c for c in pd.read_parquet(L.LEGS, columns=None).columns if c.startswith("c_")] if False else \
        [c for c in pd.read_parquet(L.LEGS).columns if c.startswith("c_")]
    S = build_store(ccols)
    R, feats = replay(S, ccols)
    R.to_csv(OUT / "A2_replay_mismatch.csv", index=False)
    drop = [c for c in feats if c != "canary_next_ret" and R[c].sum() >= 2]
    canary_flag = float(R["canary_next_ret"].mean())
    from sklearn.metrics import roc_auc_score
    dev = S[(S.period != "P3") & S.canary_next_ret.notna()]
    can_auc = float(roc_auc_score(dev.label, dev.canary_next_ret * dev.side))
    allnan = [c for c in ccols if S[c].isna().all()]
    final = [c for c in ccols + ["last_leg_move_atr", "last_leg_bars", "signal_type", "side", "ladder_k", "retr_last"] + F6 + ["funding_last"]
             if c not in drop and c not in allnan]
    S.to_parquet(STORE / "feature_store.parquet", index=False)
    (STORE / "feature_list.json").write_text(json.dumps(final, indent=1))
    claims = dict(a2_protocol_sha=sha(proto), a0_sha=sha(a0 / "A0_4H_PROTOCOL_PREREGISTERED.md"), amend1_sha=sha(a0 / "A0_AMENDMENT_1.md"),
                  amend2_sha=sha(a0 / "A0_AMENDMENT_2.md"), a1c_trades_sha=sha(A1T), store_sha=sha(STORE / "feature_store.parquet"),
                  feature_list_sha=sha(STORE / "feature_list.json"), rows=len(S), n_features=len(final), dropped_replay=drop,
                  dropped_all_nan=allnan, mismatch_counts={c: int(R[c].sum()) for c in feats}, canary_mismatch_share=canary_flag,
                  canary_pass=canary_flag >= 0.99, canary_auc_dev=can_auc, replay_rows=NREP)
    (OUT / "claims_a2.json").write_text(json.dumps(claims, indent=1, default=str))
    print(json.dumps({k: v for k, v in claims.items() if k != "mismatch_counts"}, indent=1, default=str))
    print("mismatch counts (non-zero):", {c: int(R[c].sum()) for c in feats if R[c].sum()})


if __name__ == "__main__":
    main()
