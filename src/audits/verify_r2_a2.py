"""Independent verifier for A2 (logs/r2_4h_a2 + A0 amendments 1, 2).
V1 rows == corrected A1 trades (keys), available_at == entry_time, label == (net_base > 0), signal_type / side
V2 300 random rows (seed 7, disjoint seed from the study's replay): own truncation at T + ORIGINAL legs_for with a synthetic
   final pivot -> c_*, last-leg move/bars; own ladder count from points; own F6/F7 from the CSVs; all equal (1e-9)
V3 replay CSV == claims counts; dropped features absent from feature_list.json; canary mismatch share >= 0.99
V4 SHAs (A0, amendments, A2 protocol, a1c trades, store, feature list); no '.asof(' in the A2 code
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "research"))
import swing_anatomy_phase1 as SA
import ladder_sessions as L

res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def eq(a, b):
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    return (np.isnan(a) and np.isnan(b)) or bool(np.isclose(a, b, rtol=1e-9, atol=1e-12))


A2, ST = R_ / "logs" / "r2_4h_a2", R_ / "data" / "derived" / "r2_a2"
S = pd.read_parquet(ST / "feature_store.parquet")
T1 = pd.read_parquet(R_ / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet")
key = ["signal", "coin", "entry_time"]
kS = sorted(map(tuple, S.assign(side_=S.side_str)[key + ["side_"]].astype(str).values))
kT = sorted(map(tuple, T1.assign(side_=T1.side)[key + ["side_"]].astype(str).values))
v1 = (kS == kT and (S.available_at == S.entry_time).all() and (S.label == (S.net_base > 0).astype(int)).all()
      and (S.side == np.where(S.side_str == "long", 1, -1)).all()
      and (S.signal_type == S.signal.map({"S-LAD": 0, "S-BRK": 1, "S-TRD": 2, "S-DTB": 3})).all())
ok("V1", v1, f"{len(S)} rows == corrected A1 trades; available_at == entry_time; label, side, signal_type consistent")

ccols = [c for c in S.columns if c.startswith("c_")]
cache, bad, rng = {}, {}, np.random.default_rng(7)
pick = rng.choice(S[S.available_at >= "2020-06-01"].index.values, 300, replace=False)
fng_full = SA.fng_table()
orig = SA.SS.zigzag_pivots


def with_tail(df, k, events=None):
    piv = orig(df, k, events)
    if piv:
        piv = piv + [dict(idx=len(df) - 1, tick=4 * len(df) - 1, kind="L" if piv[-1]["kind"] == "H" else "H",
                          price=float(df.close.values[-1]), confirm_idx=len(df) - 1, ev=-1)]
    return piv


for n, i in enumerate(pick):
    r = S.loc[i]
    T, coin = pd.Timestamp(r.available_at), r.coin
    for c in (coin, "BTCUSDT"):
        if c not in cache:
            cache[c] = (SA.load_spliced(c, "1h", []), SA.load_spliced(c, "1d", []))
    h = cache[coin][0]; h = h[h.timestamp + pd.Timedelta(hours=1) <= T].reset_index(drop=True)
    d = cache[coin][1]; d = d[d.timestamp + pd.Timedelta(days=1) <= T].reset_index(drop=True)
    SA.E._ZZ_CACHE.clear()
    b = SA.clip_atr(SA.agg(h, "4h"))[0]
    hb = {"1D": SA.clip_atr(d)[0], "1W": SA.clip_atr(SA.agg(d, "W-MON"))[0], "1M": SA.clip_atr(SA.agg(d, "MS"))[0]}
    htf = {k: (SA.end_times(k, v.timestamp.values), SA.E.zz(v, SA.KP)["state"]) for k, v in hb.items()}
    btc = None
    if coin != "BTCUSDT":
        bh = cache["BTCUSDT"][0]; bh = bh[bh.timestamp + pd.Timedelta(hours=1) <= T]
        bb = SA.clip_atr(SA.agg(bh, "4h"))[0]
        btc = (bb.timestamp.values, SA.base_factors(bb).ret20.values, SA.E.zz(bb, SA.KP)["state"], SA.end_times("4h", bb.timestamp.values))
    sup, rs = SA.sr_nearest(b)
    SA.SS.zigzag_pivots = with_tail
    try:
        Lg = SA.legs_for(coin, "4h", b, 3.0, SA.base_factors(b), sup, rs, (h.timestamp.values, h.low.values, h.high.values, h.quote_volume.values),
                         htf, btc, fng_full[fng_full.index < T.normalize()]).reset_index(drop=True)
    finally:
        SA.SS.zigzag_pivots = orig
    x = {c: Lg[c].iloc[-1] for c in ccols}
    x["last_leg_move_atr"], x["last_leg_bars"] = Lg.move_atr.iloc[-2], Lg.bars.iloc[-2]
    pt = L.points(Lg)
    kn = pt[pt.known_time.notna() & (pd.to_datetime(pt.known_time) <= T)]
    p = kn.index[-1]
    s_ = pt.state.values[p]; k = 0; j = p
    while s_ in ("UP", "DOWN") and j >= 0 and pt.state.values[j] == s_:
        k += int(pt.typ.values[j] == ("H" if s_ == "UP" else "L")); j -= 1
    x["ladder_k"] = k
    x["retr_last"] = pt.move.values[p] / pt.move.values[p - 1] if p >= 1 and pt.move.values[p - 1] else np.nan
    m = pd.read_csv(R_ / "data" / "futures_info" / f"{coin}_metrics_daily.csv", parse_dates=["date"]).set_index("date")
    dd = T.floor("D")
    g = lambda days, col: m[col].get(dd - pd.Timedelta(days=days), np.nan)
    x["oi_chg1"] = g(1, "oi") / g(2, "oi") - 1
    x["oi_chg7"] = g(1, "oi") / g(8, "oi") - 1
    for c in ["top_ls_acc", "top_ls_pos", "global_ls", "taker_ls_vol"]:
        x[c] = g(1, c)
    f = pd.read_csv(R_ / "data" / "futures_um" / f"{coin}_funding.csv"); f["time"] = pd.to_datetime(f["time"])
    ff = f[f.time <= T]
    x["funding_last"] = ff.funding_rate.iloc[-1] if len(ff) else np.nan
    for c, v in x.items():
        if not eq(r[c], v):
            bad[c] = bad.get(c, 0) + 1
    if n % 50 == 0:
        print(f"  {n}/300", flush=True)
ok("V2", not bad, f"300 rows rebuilt independently from data truncated at T: mismatching features {bad}")

R = pd.read_csv(A2 / "A2_replay_mismatch.csv")
cl = json.loads((A2 / "claims_a2.json").read_text())
fl = json.loads((ST / "feature_list.json").read_text())
v3 = (all(int(R[c].sum()) == v for c, v in cl["mismatch_counts"].items()) and not (set(cl["dropped_replay"]) & set(fl))
      and float(R.canary_next_ret.mean()) >= 0.99 and "canary_next_ret" not in fl)
ok("V3", v3, f"replay counts == claims; dropped {cl['dropped_replay']} absent from feature_list ({len(fl)} features); canary flagged {R.canary_next_ret.mean():.2%}")

a0 = R_ / "logs" / "r2_4h_a0"
v4 = (cl["a0_sha"] == sha(a0 / "A0_4H_PROTOCOL_PREREGISTERED.md") and cl["amend1_sha"] == sha(a0 / "A0_AMENDMENT_1.md")
      and cl["amend2_sha"] == sha(a0 / "A0_AMENDMENT_2.md") and cl["a2_protocol_sha"] == sha(A2 / "A2_PROTOCOL_PREREGISTERED.md")
      and cl["a1c_trades_sha"] == sha(R_ / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet")
      and cl["store_sha"] == sha(ST / "feature_store.parquet") and cl["feature_list_sha"] == sha(ST / "feature_list.json")
      and ".asof(" not in (R_ / "src" / "research" / "r2_a2_store.py").read_text() + (R_ / "src" / "research" / "r2_realtime_pivots.py").read_text())
ok("V4", v4, "claims SHAs == files and locks; no '.asof(' in the A2 code")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
