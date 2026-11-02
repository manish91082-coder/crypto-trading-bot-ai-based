"""
Ladder (staircase) structure + trading-session study -- descriptive, no trading rule.
Protocol: logs/research_ladder_sessions/LADDER_SESSIONS_PROTOCOL_PREREGISTERED.md (SHA256 locked before any result).
Inputs: data/derived/swing_anatomy/legs_all.parquet (Phase 1, verified) and data/universe_all/1h (10 coins).
Usage: python ladder_sessions.py
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "research_ladder_sessions"
LEGS = DATA_DIR / "derived" / "swing_anatomy" / "legs_all.parquet"
LEGS_SHA = "bbe7a4fda260be36a3c8015c07436088e3b680bbbb42e5e4a51d6d141fdc8f0f"
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "LTCUSDT", "LINKUSDT"]
TFS = ["5m", "15m", "1h", "4h", "1D", "1W", "1M"]
INFER_TFS = ["5m", "15m", "1h", "4h", "1D", "1W"]
BINS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
FIB, CTRL, W = [0.382, 0.5, 0.618], [0.30, 0.44, 0.56, 0.70], 0.02
SESS = {"Asia": range(0, 8), "Europe": range(8, 13), "US": range(13, 21), "LateUS": range(21, 24)}
HOUR2S = {h: s for s, r in SESS.items() for h in r}
UNIFORM = {s: len(r) / 24 for s, r in SESS.items()}
SEED, NBOOT = 20261017, 2000


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def state_of(hl, ll):
    if hl is None or ll is None:
        return None
    return {("HH", "HL"): "UP", ("LH", "LL"): "DOWN", ("LH", "HL"): "CONTRACTION", ("HH", "LL"): "EXPANSION"}[(hl, ll)]


def points(g):
    """g: legs of one (coin, tf, K) sorted by start_time -> swing-point table with labels and state."""
    g = g.reset_index(drop=True)
    rows, last_h, last_l, lab_h, lab_l = [], None, None, None, None
    for j, x in g.iterrows():
        typ = "H" if x.direction == "Rally" else "L"
        p = x.end_price
        if typ == "H":
            lab = None if last_h is None else ("HH" if p > last_h else "LH")
            last_h, lab_h = p, lab if lab is not None else lab_h
        else:
            lab = None if last_l is None else ("HL" if p > last_l else "LL")
            last_l, lab_l = p, lab if lab is not None else lab_l
        known = g.confirm_time.iloc[j + 1] if j + 1 < len(g) else pd.NaT   # end point known when next leg confirms
        rows.append(dict(j=j, typ=typ, price=p, label=lab, state=state_of(lab_h, lab_l), end_i=x.end_i, end_time=x.end_time,
                         known_time=known, move=abs(x.end_price - x.start_price), move_atr=x.move_atr, atr_start=x.atr_start))
    return pd.DataFrame(rows)


def runs(pt, which):
    """maximal blocks of consecutive points with state == which -> list of index arrays."""
    out, cur = [], []
    for i, s in enumerate(pt.state.values):
        if s == which:
            cur.append(i)
        else:
            if cur:
                out.append((cur, i))
            cur = []
    if cur:
        out.append((cur, None))
    return out


def analyse_group(pt, legs):
    res = dict(state_count={}, state_bars={}, runs=[], retr=[], cont=[], dbl=[], ends=[])
    st = pt.dropna(subset=["state"])
    for s in ("UP", "DOWN", "CONTRACTION", "EXPANSION"):
        res["state_count"][s] = int((st.state == s).sum())
    dur = pt.end_i.shift(-1) - pt.end_i
    for s in ("UP", "DOWN", "CONTRACTION", "EXPANSION"):
        res["state_bars"][s] = float(dur[pt.state == s].sum())
    for which, step_t, retr_t in (("UP", "H", "L"), ("DOWN", "L", "H")):
        for idx, nxt in runs(pt, which):
            sub = pt.iloc[idx]
            steps = int((sub.typ == step_t).sum())
            r_list, l_list = [], []
            for i in idx:
                if pt.typ.iloc[i] == retr_t and i - 1 >= 0 and pt.move.iloc[i - 1] > 0:
                    r_list.append(pt.move.iloc[i] / pt.move.iloc[i - 1])
                if pt.typ.iloc[i] == step_t:
                    l_list.append(pt.move_atr.iloc[i])
            res["retr"] += [(which, r) for r in r_list]
            style = "V_IMPULSE" if steps <= 1 else ("SHORT" if steps == 2 else "NA")
            if steps >= 3 and len(r_list) >= 2 and len(l_list) >= 2:
                h1, h2 = len(r_list) // 2, (len(r_list) + 1) // 2
                r1, r2 = np.mean(r_list[:h1]), np.mean(r_list[h2:])
                k1, k2 = len(l_list) // 2, (len(l_list) + 1) // 2
                a1, a2 = np.mean(l_list[:k1]), np.mean(l_list[k2:])
                dr, dl = r2 / r1 - 1, a2 / a1 - 1
                style = ("STEADY" if abs(dr) <= 0.1 and abs(dl) <= 0.1 else "ACCELERATING" if dr < 0 and dl > 0
                         else "DECELERATING" if dr > 0 and dl < 0 else "MIXED")
            end_by = None if nxt is None else pt.label.iloc[nxt]
            res["runs"].append(dict(kind=which, steps=steps, style=style, end_by=end_by))
            # continuation: at each step point k inside run, is the next same-type point a continuation label?
            k = 0
            for i in idx:
                if pt.typ.iloc[i] == step_t:
                    k += 1
                    n2 = i + 2
                    if n2 < len(pt) and pt.typ.iloc[n2] == step_t:
                        cont = pt.label.iloc[n2] == ("HH" if which == "UP" else "LL")
                        res["cont"].append((which, min(k, 5), bool(cont)))
    # double tops / bottoms
    for typ, nxt_lab in (("H", "LL"), ("L", "HH")):
        ii = np.where(pt.typ.values == typ)[0]
        for a, b in zip(ii[:-1], ii[1:]):
            if abs(pt.price.iloc[b] - pt.price.iloc[a]) <= 0.5 * pt.atr_start.iloc[b]:
                n = b + 1
                if n < len(pt) and pt.label.iloc[n] is not None:
                    res["dbl"].append((typ, pt.label.iloc[n] == nxt_lab))
    return res


def boot_ci(vals_by_block, stat, rng, n=NBOOT):
    keys = list(vals_by_block)
    bs = []
    for _ in range(n):
        pick = rng.choice(len(keys), len(keys), replace=True)
        bs.append(stat([vals_by_block[keys[i]] for i in pick]))
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def part_a(legs):
    rng = np.random.default_rng(SEED)
    st_rows, run_rows, retr_rows, cont_rows, dbl_rows, fib_rows, rob_rows = [], [], [], [], [], [], []
    for K in (3.0, 2.0, 4.0):
        for tf in TFS:
            agg = dict(sc={}, sb={}, runs=[], retr=[], cont=[], dbl=[])
            fib_blocks = {}
            for coin in COINS:
                g = legs[(legs.coin == coin) & (legs.tf == tf) & (legs.K == K)].sort_values("start_time")
                if len(g) < 4:
                    continue
                pt = points(g)
                r = analyse_group(pt, g)
                for s, v in r["state_count"].items():
                    agg["sc"][s] = agg["sc"].get(s, 0) + v
                for s, v in r["state_bars"].items():
                    agg["sb"][s] = agg["sb"].get(s, 0) + v
                agg["runs"] += [dict(coin=coin, **x) for x in r["runs"]]
                agg["cont"] += r["cont"]
                agg["dbl"] += r["dbl"]
                # retracements with coin-year block for the fib bootstrap
                yrs = []
                for which in ("UP", "DOWN"):
                    pass
                rr = r["retr"]
                agg["retr"] += rr
                if K == 3.0 and rr:
                    # block = coin x year of the retracement leg end
                    retr_pts = []
                    for which, step_t, retr_t in (("UP", "H", "L"), ("DOWN", "L", "H")):
                        for idx, _ in runs(pt, which):
                            for i in idx:
                                if pt.typ.iloc[i] == retr_t and i - 1 >= 0 and pt.move.iloc[i - 1] > 0:
                                    retr_pts.append((pt.end_time.iloc[i].year, pt.move.iloc[i] / pt.move.iloc[i - 1]))
                    for y, v in retr_pts:
                        fib_blocks.setdefault((coin, y), []).append(v)
            tot = sum(agg["sc"].values())
            totb = sum(agg["sb"].values())
            if tot == 0:
                continue
            ret = np.array([v for _, v in agg["retr"]])
            ret = ret[(ret > 0) & (ret < 1)]
            if K == 3.0:
                for s in ("UP", "DOWN", "CONTRACTION", "EXPANSION"):
                    st_rows.append(dict(tf=tf, state=s, share_count=agg["sc"].get(s, 0) / tot, share_time=agg["sb"].get(s, 0) / totb, n=tot))
                rd = pd.DataFrame(agg["runs"])
                for kind in ("UP", "DOWN"):
                    x = rd[rd.kind == kind]
                    if not len(x):
                        continue
                    row = dict(tf=tf, kind=kind, runs=len(x), median_steps=float(x.steps.median()), mean_steps=float(x.steps.mean()))
                    for s in (1, 2, 3, 4):
                        row[f"steps_{s}"] = float((x.steps == s).mean())
                    row["steps_5plus"] = float((x.steps >= 5).mean())
                    for sty in ("V_IMPULSE", "SHORT", "STEADY", "ACCELERATING", "DECELERATING", "MIXED", "NA"):
                        row[f"style_{sty}"] = float((x["style"] == sty).mean())
                    e = x.end_by.dropna()
                    first = "LH" if kind == "UP" else "HL"
                    row[f"end_first_{first}"] = float((e == first).mean()) if len(e) else np.nan
                    row["end_first_break"] = float((e == ("LL" if kind == "UP" else "HH")).mean()) if len(e) else np.nan
                    run_rows.append(row)
                for kind in ("UP", "DOWN"):
                    rk = np.array([v for w, v in agg["retr"] if w == kind])
                    rk = rk[(rk > 0) & (rk < 1)]
                    if not len(rk):
                        continue
                    row = dict(tf=tf, kind=kind, n=len(rk), median=float(np.median(rk)), q25=float(np.percentile(rk, 25)), q75=float(np.percentile(rk, 75)),
                               share_ge1=float(np.mean(np.array([v for w, v in agg["retr"] if w == kind]) >= 1)))
                    for a, b in zip(BINS[:-1], BINS[1:]):
                        row[f"bin_{a}_{b}"] = float(((rk >= a) & (rk < b)).mean())
                    retr_rows.append(row)
                cd = pd.DataFrame(agg["cont"], columns=["kind", "k", "cont"])
                for (kind, k), x in cd.groupby(["kind", "k"]):
                    cont_rows.append(dict(tf=tf, kind=kind, k=int(k), n=len(x), p_continue=float(x.cont.mean())))
                dd = pd.DataFrame(agg["dbl"], columns=["typ", "follow"])
                for typ, x in dd.groupby("typ"):
                    lab_all = "LL" if typ == "H" else "HH"
                    dbl_rows.append(dict(tf=tf, pattern="double_top" if typ == "H" else "double_bottom", n=len(x), p_follow=float(x.follow.mean()),
                                         follow_label=lab_all))
                # fib test
                def fshare(vs):
                    a = np.concatenate([np.asarray(v) for v in vs]) if vs else np.array([])
                    a = a[(a > 0) & (a < 1)]
                    if not len(a):
                        return 0.0
                    f = np.mean([np.mean(np.abs(a - c) <= W) for c in FIB])
                    c_ = np.mean([np.mean(np.abs(a - c) <= W) for c in CTRL])
                    return f - c_
                diff = fshare(list(fib_blocks.values()))
                lo, hi = boot_ci(fib_blocks, fshare, rng, 1000)
                fib_rows.append(dict(tf=tf, fib_minus_control=diff, ci_lo=lo, ci_hi=hi,
                                     fib_share=float(np.mean([np.mean(np.abs(ret - c) <= W) for c in FIB])),
                                     control_share=float(np.mean([np.mean(np.abs(ret - c) <= W) for c in CTRL]))))
            rob_rows.append(dict(K=K, tf=tf, up_share=agg["sc"].get("UP", 0) / tot, down_share=agg["sc"].get("DOWN", 0) / tot,
                                 retr_median=float(np.median(ret)) if len(ret) else np.nan,
                                 median_steps_up=float(pd.DataFrame(agg["runs"]).query("kind=='UP'").steps.median()) if agg["runs"] else np.nan))
    # unconditional LL share after a high / HH share after a low (for double top/bottom comparison)
    return (pd.DataFrame(st_rows), pd.DataFrame(run_rows), pd.DataFrame(retr_rows), pd.DataFrame(cont_rows),
            pd.DataFrame(dbl_rows), pd.DataFrame(fib_rows), pd.DataFrame(rob_rows))


def uncond_labels(legs):
    rows = []
    for tf in TFS:
        lab = []
        for coin in COINS:
            g = legs[(legs.coin == coin) & (legs.tf == tf) & (legs.K == 3.0)].sort_values("start_time")
            if len(g) < 4:
                continue
            pt = points(g)
            lab += list(pt.label.dropna())
        lab = pd.Series(lab)
        rows.append(dict(tf=tf, p_LL_among_lows=float((lab == "LL").sum() / lab.isin(["LL", "HL"]).sum()),
                         p_HH_among_highs=float((lab == "HH").sum() / lab.isin(["HH", "LH"]).sum())))
    return pd.DataFrame(rows)


def daily_state(legs, coin):
    """causal 1D K=3 structure state for each UTC day: only swing points known (next leg confirmed) by day start."""
    g = legs[(legs.coin == coin) & (legs.tf == "1D") & (legs.K == 3.0)].sort_values("start_time")
    pt = points(g).dropna(subset=["known_time"]).sort_values("known_time")
    return pt[["known_time", "state"]]


def part_b(legs):
    rng = np.random.default_rng(SEED)
    per = []
    hl_rows = []
    for coin in COINS:
        d = pd.read_csv(DATA_DIR / "universe_all" / "1h" / f"{coin}_1h_full.csv.gz", parse_dates=["timestamp"])
        d = d[(d.timestamp >= "2020-01-01") & (d.timestamp < "2026-10-01")].set_index("timestamp").sort_index()
        r = np.log(d.close).diff()
        x = pd.DataFrame(dict(r=r, hour=d.index.hour, day=d.index.normalize())).dropna()
        x["sess"] = x.hour.map(HOUR2S)
        s = x.groupby(["day", "sess"]).r.sum().unstack()
        a = x.assign(ar=x.r.abs()).groupby(["day", "sess"]).ar.sum().unstack()
        ds = daily_state(legs, coin)
        st = pd.merge_asof(pd.DataFrame(dict(day=s.index)), ds.rename(columns={"known_time": "day"}), on="day", direction="backward")
        st.index = s.index
        for sname in SESS:
            per.append(pd.DataFrame(dict(coin=coin, day=s.index, sess=sname, ret=s[sname].values, absr=a[sname].values,
                                         abs_total=a.sum(axis=1).values, state=st.state.values)))
        # daily high / low hour
        dd = d.assign(day=d.index.normalize(), hour=d.index.hour)
        hi_h = dd.loc[dd.groupby("day").high.idxmax(), ["day", "hour"]]
        lo_h = dd.loc[dd.groupby("day").low.idxmin(), ["day", "hour"]]
        for kind, t in (("high", hi_h), ("low", lo_h)):
            hl_rows.append(pd.DataFrame(dict(coin=coin, day=t.day.values, kind=kind, sess=t.hour.map(HOUR2S).values)))
    P = pd.concat(per, ignore_index=True)
    P["period"] = np.where(P.day < "2024-01-01", "2020-2023", "2024-2026")
    P["weekend"] = P.day.dt.dayofweek >= 5
    HL = pd.concat(hl_rows, ignore_index=True)
    out = []

    def summarise(sub, label):
        for sname in SESS:
            q = sub[sub.sess == sname]
            m = q.groupby("day").ret.mean() * 1e4                  # pooled across coins, bps per session-day
            if len(m) < 30:
                continue
            arr = m.values
            idx = rng.integers(0, len(arr), (NBOOT, len(arr)))
            bs = arr[idx].mean(axis=1)
            out.append(dict(split=label, sess=sname, days=len(m), mean_bps=float(arr.mean()), ci_lo=float(np.percentile(bs, 2.5)),
                            ci_hi=float(np.percentile(bs, 97.5)), median_abs_bps=float(q.absr.median() * 1e4),
                            share_abs_move=float(q.absr.sum() / sub.groupby(["coin", "day"]).abs_total.first().sum())))
    summarise(P, "all")
    for p in ("2020-2023", "2024-2026"):
        summarise(P[P.period == p], p)
    summarise(P[~P.weekend], "weekday")
    summarise(P[P.weekend], "weekend")
    for sname in ("UP", "DOWN"):
        summarise(P[P.state == sname], f"daily_{sname}")
    summarise(P[~P.state.isin(["UP", "DOWN"])], "daily_other")
    S = pd.DataFrame(out)
    # consistency rule
    cons = []
    for sname in SESS:
        a = S[(S.split == "all") & (S.sess == sname)].iloc[0]
        p1 = S[(S.split == "2020-2023") & (S.sess == sname)].iloc[0]
        p2 = S[(S.split == "2024-2026") & (S.sess == sname)].iloc[0]
        ok = (a.ci_lo > 0 or a.ci_hi < 0) and np.sign(p1.mean_bps) == np.sign(p2.mean_bps) == np.sign(a.mean_bps)
        cons.append(dict(sess=sname, mean_bps=a.mean_bps, ci=(a.ci_lo, a.ci_hi), p2020_23=p1.mean_bps, p2024_26=p2.mean_bps,
                         verdict="consistent" if ok else "not proven"))
    H = HL.groupby(["kind", "sess"]).size().unstack(0)
    H = (H / H.sum()).rename_axis(None).reset_index().rename(columns={"index": "sess"})
    H["uniform"] = H.sess.map(UNIFORM)
    H2 = HL.assign(period=np.where(HL.day < "2024-01-01", "2020-2023", "2024-2026")).groupby(["period", "kind", "sess"]).size()
    H2 = (H2 / H2.groupby(level=[0, 1]).transform("sum")).rename("share").reset_index()
    # 1h K=3 swing extremes by session
    g = legs[(legs.tf == "1h") & (legs.K == 3.0)]
    ex = g.assign(kind=np.where(g.direction == "Rally", "swing_high", "swing_low"), sess=g.end_time.dt.hour.map(HOUR2S))
    E = ex.groupby(["kind", "sess"]).size().unstack(0)
    E = (E / E.sum()).rename_axis(None).reset_index().rename(columns={"index": "sess"})
    E["uniform"] = E.sess.map(UNIFORM)
    return S, pd.DataFrame(cons), H, H2, E


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    proto = OUT / "LADDER_SESSIONS_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after lock"
    assert sha(LEGS) == LEGS_SHA, "legs parquet changed"
    legs = pd.read_parquet(LEGS, columns=["coin", "tf", "K", "direction", "start_time", "start_price", "end_time", "end_price",
                                          "end_i", "confirm_time", "atr_start", "move_atr"])
    st, rn, rt, ct, db, fb, rb = part_a(legs)
    un = uncond_labels(legs)
    S, C, H, H2, E = part_b(legs)
    for name, df in (("A1_state_shares", st), ("A2_ladder_runs", rn), ("A3_retracements", rt), ("A4_step_continuation", ct),
                     ("A5_double_top_bottom", db), ("A5b_unconditional_labels", un), ("A6_fibonacci_test", fb), ("A7_robust_K", rb),
                     ("B1_session_returns", S), ("B2_session_consistency", C), ("B3_daily_high_low_session", H),
                     ("B3b_daily_high_low_by_period", H2), ("B4_1h_swing_extremes_session", E)):
        df.to_csv(OUT / f"{name}.csv", index=False)
    fib_claim = int(((fb.tf.isin(INFER_TFS)) & (fb.ci_lo > 0)).sum())
    claims = dict(protocol_sha256=sha(proto), legs_sha256=LEGS_SHA, code_sha256=sha(__file__),
                  fibonacci_clustering=bool(fib_claim >= 4), fib_tfs_positive=fib_claim,
                  session_verdicts={r.sess: r.verdict for r in C.itertuples()},
                  up_share_K3={r.tf: round(r.share_count, 4) for r in st[st.state == "UP"].itertuples()},
                  down_share_K3={r.tf: round(r.share_count, 4) for r in st[st.state == "DOWN"].itertuples()},
                  retr_median_UP={r.tf: round(r.median, 4) for r in rt[rt.kind == "UP"].itertuples()},
                  retr_median_DOWN={r.tf: round(r.median, 4) for r in rt[rt.kind == "DOWN"].itertuples()},
                  median_steps={f"{r.tf}_{r.kind}": r.median_steps for r in rn.itertuples()})
    (OUT / "claims_ladder_sessions.json").write_text(json.dumps(claims, indent=1, default=float))
    print(json.dumps(claims, indent=1, default=float))


if __name__ == "__main__":
    main()
