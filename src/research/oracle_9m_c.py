"""Part C (and later Part D) of the 9-month study: logs/oracle_9m_2026/AMENDMENT_1_PART_C_PREREGISTERED.md (SHA e68da96c...).
C1 direction methods, C2 entry triggers (first passage +-1% in 4h), C3 whole rules (6 slots x direction x R x geometry, 4h windows).
Usage: python src/research/oracle_9m_c.py C            -> 2026 window, out logs/oracle_9m_2026/part_c
       python src/research/oracle_9m_c.py D <configs>  -> defined by Amendment 2 (not used before it is locked)"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle_9m as A  # noqa: E402  (shared loaders / sweep definitions of the locked protocol)

P = A.P
C_FUT, C_SPOT = A.C_FUT, A.C_SPOT
SLOTS = [0, 4, 8, 12, 16, 20]
W4 = 48                                   # 4h in 5m bars
RS = {"R05": 0.005, "R08": 0.008, "R12": 0.012, "RVOL": None}
GEOS = {"G12": (1.0, 2.0), "G11": (1.0, 1.0), "G21": (2.0, 1.0), "G051": (0.5, 1.0), "G1N": (1.0, None)}
DIRS = ["L", "S", "FADE", "FOLLOW", "RAND"]
FP_X = 0.01
PSTAR = (1 + 2 * C_FUT * 100) / 2         # break-even share of a symmetric +-1% first passage (0.546)


class Grid:
    """complete 5m grid over [t0, t1]; missing bars are NaN."""

    def __init__(self, d5, t0, t1):
        idx = pd.date_range(t0, t1, freq="5min")
        g = d5.reindex(idx)
        self.t = idx
        self.O, self.H, self.L, self.C = (g[k].to_numpy(dtype=float) for k in A.C4)
        self.pos0 = {d: i for i, d in enumerate(idx) if d.hour == 0 and d.minute == 0}

    def day_ok(self, day):
        p = self.pos0.get(day)
        return p is not None and p + 288 <= len(self.t) and not np.isnan(self.O[p:p + 288]).any()


def log(out, msg):
    line = f"{pd.Timestamp.now('UTC'):%Y-%m-%dT%H:%M:%SZ} {msg}"
    print(line, flush=True)
    with open(out / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def first_passage(G, pos, side, X=FP_X, n=W4):
    e = G.O[pos]
    up, dn = e * (1 + X), e * (1 - X)
    end = min(pos + n, len(G.t))
    for k in range(pos, end):
        if side == "long":
            if G.L[k] <= dn: return "adv", e
            if G.H[k] >= up: return "fav", e
        else:
            if G.H[k] >= up: return "adv", e
            if G.L[k] <= dn: return "fav", e
    return "none", e


def sim_window(G, pos, side, R, tp_m, sl_m):
    """trade inside one 4h window from the open of bar pos. Returns gross, exit reason, mfe (fractions)."""
    e = G.O[pos]
    tp = e * (1 + tp_m * R) if side == "long" else e * (1 - tp_m * R)
    sl = None if sl_m is None else (e * (1 - sl_m * R) if side == "long" else e * (1 + sl_m * R))
    best = 0.0
    for k in range(pos, pos + W4):
        o, h, l = G.O[k], G.H[k], G.L[k]
        if side == "long":
            best = max(best, h / e - 1)
            if sl is not None and o <= sl: return o / e - 1, "SL_gap", best
            if sl is not None and l <= sl: return sl / e - 1, "SL", best
            if o >= tp: return o / e - 1, "TP_gap", best
            if h >= tp: return tp / e - 1, "TP", best
        else:
            best = max(best, 1 - l / e)
            if sl is not None and o >= sl: return 1 - o / e, "SL_gap", best
            if sl is not None and h >= sl: return 1 - sl / e, "SL", best
            if o <= tp: return 1 - o / e, "TP_gap", best
            if l <= tp: return 1 - tp / e, "TP", best
    return G.C[pos + W4 - 1] / e - 1 if side == "long" else 1 - G.C[pos + W4 - 1] / e, "TIME", best


def wilson(k, n, z=1.96):
    return A.wilson(k, n, z)


def binom_p(k, n):
    """exact two-sided binomial test vs 0.5 (sum of the probabilities <= P(k))."""
    if n == 0:
        return np.nan
    from math import comb
    pk = comb(n, k)
    tot = sum(comb(n, i) for i in range(n + 1) if comb(n, i) <= pk)       # exact integers (no float overflow for large n)
    return min(1.0, tot / 2 ** n)


def cluster_ci(daily):
    """daily: DataFrame date, net -> mean per day, SE by ISO-week clusters."""
    D = len(daily)
    m = daily.net.sum() / D
    wk = daily.assign(w=daily.date.map(lambda d: tuple(d.isocalendar())[:2])).groupby("w").net.agg(["sum", "size"])
    nw = len(wk)
    se = np.sqrt(nw / (nw - 1) * ((wk["sum"] - m * wk["size"]) ** 2).sum()) / D
    return m, se


def day_context(G, d1, day):
    p = G.pos0[day]
    lv = A.levels_for(d1, day)
    prev = d1.loc[:day - pd.Timedelta(days=1)].iloc[-1]
    return p, lv, float((prev.high / prev.low - 1))


def run_c1(G, d1, days, events):
    rows = []
    for day in days:
        p, lv, _ = day_context(G, d1, day)
        cl = G.C[p + 287]
        prev = d1.loc[:day - pd.Timedelta(days=1)].iloc[-1]
        pr = prev.close / prev.open - 1
        calls = {"DIR_LONG": (0, 1), "DIR_PD_FOLLOW": (0, np.sign(pr)), "DIR_PD_FADE": (0, -np.sign(pr)),
                 "DIR_CLOSEPOS": (0, 1 if (lv["pdc"] - lv["pdl"]) / (lv["pdh"] - lv["pdl"]) > 0.5 else -1),
                 "DIR_7D_MID": (0, 1 if lv["pdc"] > (lv["d7h"] + lv["d7l"]) / 2 else -1),
                 "DIR_H1_FOLLOW": (12, np.sign(G.C[p + 11] - G.O[p])),
                 "DIR_ASIA_FOLLOW": (96, np.sign(G.C[p + 95] - G.O[p])),
                 "DIR_ASIA_FADE": (96, -np.sign(G.C[p + 95] - G.O[p]))}
        for mid, (off, sg) in calls.items():
            if sg == 0:
                continue
            px = G.O[p + off]
            tgt = np.sign(cl - px)
            if tgt == 0:
                continue
            rows.append(dict(method=mid, date=day, tau=G.t[p + off], call=int(sg), price=px, hit=bool(sg == tgt), signed_ret_pct=sg * (cl / px - 1) * 100))
        ev = events[(events.date == day) & events.new_extreme & events.confirmed]
        if len(ev):
            first_bar = ev.bar_time.min()
            e0 = ev[ev.bar_time == first_bar]
            if e0.side.nunique() == 1:
                sg = 1 if e0.side.iloc[0] == "bull" else -1
                ct = e0.confirm_time.iloc[0]
                px = G.C[G.t.get_loc(ct) + 2]                 # close of the 15m confirm bar = close of its last 5m bar
                tgt = np.sign(cl - px)
                if tgt != 0:
                    rows.append(dict(method="DIR_SWEEP", date=day, tau=ct + pd.Timedelta(minutes=15), call=sg, price=px, hit=bool(sg == tgt),
                                     signed_ret_pct=sg * (cl / px - 1) * 100))
    calls = pd.DataFrame(rows)
    base = calls[calls.method == "DIR_LONG"].hit.mean()
    summ = []
    for mid, g in calls.groupby("method"):
        n, k = len(g), int(g.hit.sum())
        lo, hi = wilson(k, n)
        summ.append(dict(method=mid, calls=n, hits=k, hit_rate=k / n, wilson_lo=lo, wilson_hi=hi, binom_p=binom_p(k, n),
                         mean_signed_ret_pct=g.signed_ret_pct.mean(), vs_long=(k / n - base) if mid != "DIR_LONG" else 0.0))
    return calls, pd.DataFrame(summ).sort_values("wilson_lo", ascending=False)


def run_c2(G, d1, days, events, a1):
    rows = []
    rng = np.random.default_rng(0)
    for day in days:
        p, lv, _ = day_context(G, d1, day)
        last = p + 287
        trig = []
        for s in SLOTS:
            q = p + s * 12
            mv = G.C[q - 1] - G.O[q - W4]
            if mv != 0 and not np.isnan(mv):
                trig.append(("ENT_SLOT_FADE", q, "short" if mv > 0 else "long"))
                trig.append(("ENT_SLOT_FOLLOW", q, "long" if mv > 0 else "short"))
        ev = events[events.date == day]
        for (bt, side), g in ev.groupby(["bar_time", "side"]):
            sd = "long" if side == "bull" else "short"
            q = G.t.get_loc(bt) + 3
            if q <= last:
                trig.append(("ENT_SWEEP_ALL", q, sd))
            gc = g[g.new_extreme & g.confirmed]
            if len(gc):
                q2 = G.t.get_loc(gc.confirm_time.iloc[0]) + 3
                if q2 <= last:
                    trig.append(("ENT_SWEEP_CONF", q2, sd))
        hh, hl = G.H[p:p + 12].max(), G.L[p:p + 12].min()
        for k in range(p + 12, last):
            if G.C[k] > hh or G.C[k] < hl:
                sd = "long" if G.C[k] > hh else "short"
                trig.append(("ENT_H1_BREAK", k + 1, sd))
                trig.append(("ENT_H1_BREAK_FADE", k + 1, "short" if sd == "long" else "long"))
                break
        done = set()
        for k in range(p + 96, last):
            if "long" not in done and G.C[k] < G.L[p:k].min():
                trig.append(("ENT_EXT_FADE", k + 1, "long")); done.add("long")
            if "short" not in done and G.C[k] > G.H[p:k].max():
                trig.append(("ENT_EXT_FADE", k + 1, "short")); done.add("short")
        bars = rng.integers(288, size=6)
        sides = rng.integers(2, size=6)
        for b, sd in zip(bars, sides):
            trig.append(("ENT_RANDOM", p + int(b), "long" if sd == 0 else "short"))
        for mid, q, sd in trig:
            res, e = first_passage(G, q, sd)
            endk = min(q + W4 - 1, len(G.t) - 1)
            r4 = (G.C[endk] / e - 1) * (1 if sd == "long" else -1) * 100
            ref = a1.loc[day, "a1_long_entry" if sd == "long" else "a1_short_entry"]
            rows.append(dict(trigger=mid, date=day, entry_time=G.t[q], side=sd, entry_px=e, result=res, ret4h_pct=r4,
                             dist_a1_pct=abs(e - ref) / ref * 100))
    evs = pd.DataFrame(rows)
    summ = []
    for mid, g in evs.groupby("trigger"):
        f, a, nn = int((g.result == "fav").sum()), int((g.result == "adv").sum()), int((g.result == "none").sum())
        lo, hi = wilson(f, f + a)
        summ.append(dict(trigger=mid, events=len(g), fav=f, adv=a, none=nn, p=f / (f + a) if f + a else np.nan, wilson_lo=lo, wilson_hi=hi,
                         p_minus_pstar=(f / (f + a) - PSTAR) if f + a else np.nan, mean_ret4h_pct=g.ret4h_pct.mean(),
                         median_dist_a1_pct=g.dist_a1_pct.median()))
    return evs, pd.DataFrame(summ).sort_values("wilson_lo", ascending=False)


def rand_sides(days):
    rng = np.random.default_rng(0)
    return {(d, s): ("long" if rng.integers(2) == 0 else "short") for d in days for s in SLOTS}


def run_c3(G, d1, days, configs):
    """configs: list of (dir, rid, gid, mode). Returns trades DataFrame."""
    rs = rand_sides(days)
    ctx = {d: day_context(G, d1, d) for d in days}
    rows = []
    for (dr, rid, gid, mode) in configs:
        c = C_FUT if mode == "FUT" else C_SPOT
        tp_m, sl_m = GEOS[gid]
        for day in days:
            p, lv, prev_rng = ctx[day]
            R = RS[rid] if RS[rid] is not None else 0.33 * prev_rng
            for s in SLOTS:
                q = p + s * 12
                if dr in ("L", "S", "RAND"):
                    sd = {"L": "long", "S": "short"}.get(dr) or rs[(day, s)]
                else:
                    mv = G.C[q - 1] - G.O[q - W4]
                    if mv == 0 or np.isnan(mv):
                        continue
                    up = mv > 0
                    sd = ("short" if up else "long") if dr == "FADE" else ("long" if up else "short")
                g, why, mfe = sim_window(G, q, sd, R, tp_m, sl_m)
                rows.append((dr, rid, gid, mode, day, s, sd, R, g * 100, (g - 2 * c) * 100, why, mfe * 100))
    return pd.DataFrame(rows, columns=["dir", "rid", "gid", "mode", "date", "slot", "side", "R", "gross_pct", "net_pct", "reason", "mfe_pct"])


def c3_tables(tr, days, n_tests=100):
    tr = tr.assign(cfg=tr["mode"] + "|" + tr["dir"] + "|" + tr.rid + "|" + tr.gid)
    dd = pd.DataFrame({"date": days})
    daily_all, summ, monthly = [], [], []
    for cfg, g in tr.groupby("cfg", sort=False):
        d = dd.merge(g.groupby("date").agg(net=("net_pct", "sum"), n=("net_pct", "size")).reset_index(), on="date", how="left").fillna({"net": 0.0, "n": 0})
        d["cfg"] = cfg
        daily_all.append(d)
        m, se = cluster_ci(d)
        mo = d.assign(month=d.date.dt.to_period("M").astype(str)).groupby("month").net.sum()
        yr = d.assign(year=d.date.dt.year).groupby("year").net.sum()
        cum = d.net.cumsum()
        mdd = float((cum.cummax() - cum).max())
        n, k = len(g), int((g.net_pct > 0).sum())
        lo, hi = wilson(k, n)
        cap = g[g.mfe_pct > 0]
        mode, dr, rid, gid = cfg.split("|")
        summ.append(dict(cfg=cfg, mode=mode, dir=dr, rid=rid, gid=gid, trades=n, wins=k, win_rate=k / n, wilson_lo=lo, wilson_hi=hi,
                         mean_net_trade_pct=g.net_pct.mean(), total_net_pct=g.net_pct.sum(), mean_net_day_pct=m, se_day=se,
                         lb95=m - 1.96 * se, lb_bonf=m - 3.48 * se, months_pos=int((mo > 0).sum()), months=len(mo),
                         worst_month_pct=float(mo.min()), years_pos=int((yr > 0).sum()), years=len(yr), max_dd_pct=mdd,
                         mfe_captured=float((cap.gross_pct / cap.mfe_pct).mean()) if len(cap) else np.nan,
                         exits=json.dumps(g.reason.value_counts().to_dict())))
        monthly.append(mo.rename("net_pct").reset_index().assign(cfg=cfg))
    S = pd.DataFrame(summ)
    rnd = S[S.dir == "RAND"].set_index(["mode", "rid", "gid"]).total_net_pct
    S["vs_rand_total"] = [r.total_net_pct - rnd.get((r.mode, r.rid, r.gid), np.nan) for r in S.itertuples()]
    return S.sort_values("lb95", ascending=False), pd.concat(daily_all), pd.concat(monthly)


def sweep_events_min(G, d1, days):
    """the A6 sweep events (same definitions as oracle_9m.part_a), only the columns Part C / D use."""
    rows = []
    for day in days:
        p = G.pos0[day]
        lv = A.levels_for(d1, day)
        o = np.array([G.O[p + 3 * j] for j in range(96)])
        h = np.array([G.H[p + 3 * j:p + 3 * j + 3].max() for j in range(96)])
        l = np.array([G.L[p + 3 * j:p + 3 * j + 3].min() for j in range(96)])
        c = np.array([G.C[p + 3 * j + 2] for j in range(96)])
        nl, nh = A.new_ext_flags(l, h)
        for s in range(96):
            for bull in (True, False):
                for (lt, L_) in A.sweep_levels(l[s], h[s], c[s], lv, bull):
                    ext = (nl[s] or (s > 0 and nl[s - 1])) if bull else (nh[s] or (s > 0 and nh[s - 1]))
                    k = A.confirm(o, h, l, c, s, bull)
                    rows.append(dict(date=day, bar_time=G.t[p + 3 * s], side="bull" if bull else "bear", level_type=lt, level=L_,
                                     new_extreme=bool(ext), confirmed=k is not None,
                                     confirm_time=G.t[p + 3 * k] if k is not None else pd.NaT))
    return pd.DataFrame(rows)


def a1_min(G, days):
    rows = []
    for day in days:
        p = G.pos0[day]
        h, l = G.H[p:p + 288], G.L[p:p + 288]
        i, _, _ = A.best_pair(l, h, True)
        si, _, _ = A.best_pair(l, h, False)
        rows.append(dict(date=day, a1_long_entry=l[i], a1_short_entry=h[si]))
    return pd.DataFrame(rows).set_index("date")


def part_d():
    """Amendment 2: the locked rule selected no config; the pre-declared lead FUT|RAND|R08|G12 + top C1 / C2 as context."""
    out = A.OUT / "part_d"
    out.mkdir(exist_ok=True)
    log(out, "Part D start (Amendment 2)")
    d5 = pd.read_csv(P / A.INPUTS[0], parse_dates=["timestamp"]).drop_duplicates("timestamp").set_index("timestamp").sort_index()
    d5 = d5.loc["2020-01-01":"2025-12-31 23:55", A.C4 + ["volume"]]
    d1 = d5.resample("1D").agg(A.AGG)
    G = Grid(d5, pd.Timestamp("2020-01-01"), pd.Timestamp("2025-12-31 23:55"))
    manual = [pd.Timestamp(x.strip()) for x in (P / "logs/manual_day_study/selected_days.txt").read_text().splitlines()[1:] if x.strip()]
    cand = list(pd.date_range("2020-01-08", "2025-12-31", freq="D"))
    incomplete = [d for d in pd.date_range("2020-01-01", "2025-12-31", freq="D") if not G.day_ok(d)]
    days = [d for d in cand if d not in manual and G.day_ok(d) and G.day_ok(d - pd.Timedelta(days=1))]
    excl = dict(manual=[str(d.date()) for d in manual if d in cand], incomplete=[str(d.date()) for d in incomplete],
                prior_incomplete=[str(d.date()) for d in cand if G.day_ok(d) and not G.day_ok(d - pd.Timedelta(days=1))])
    log(out, f"days {len(days)} of {len(cand)}; excluded {json.dumps({k: len(v) for k, v in excl.items()})}")
    tr = run_c3(G, d1, days, [("RAND", "R08", "G12", "FUT")])
    tr.to_parquet(out / "d_trades.parquet", compression="zstd", index=False)
    S, daily, monthly = c3_tables(tr, days)
    daily.to_parquet(out / "d_daily.parquet", compression="zstd", index=False)
    monthly.to_csv(out / "d_monthly.csv", index=False)
    s = S.iloc[0].to_dict()
    mo_share = s["months_pos"] / s["months"]
    gates = dict(g1_lb95_pos=bool(s["lb95"] > 0), g2_months_60=bool(mo_share >= 0.6), g3_years_4of6=bool(s["years_pos"] >= 4),
                 g4_vs_rand="not applied (the lead is RAND)", g5_days_excluded=excl)
    s["passes"] = gates["g1_lb95_pos"] and gates["g2_months_60"] and gates["g3_years_4of6"]
    yearly = daily.assign(year=daily.date.dt.year).groupby("year").net.sum().round(4).to_dict()
    events = sweep_events_min(G, d1, days)
    calls, s1 = run_c1(G, d1, days, events)
    evs, s2 = run_c2(G, d1, days, events, a1_min(G, days))
    s1 = s1[s1.method == "DIR_CLOSEPOS"]
    s2 = s2[s2.trigger == "ENT_SWEEP_ALL"]
    s1.to_csv(out / "d_c1_context.csv", index=False)
    s2.to_csv(out / "d_c2_context.csv", index=False)
    res = dict(lead=s, gates=gates, yearly_net_pct=yearly, c1_context=s1.to_dict("records"), c2_context=s2.to_dict("records"))
    (out / "D_RESULTS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    log(out, f"lead {s['cfg']}: trades {s['trades']} mean/day {s['mean_net_day_pct']:.4f} lb95 {s['lb95']:.4f} months+ {s['months_pos']}/{s['months']} "
             f"years+ {s['years_pos']}/{s['years']} passes {s['passes']}")
    outs = sorted(f for f in out.iterdir() if f.suffix in (".parquet", ".csv", ".json"))
    (out / "OUTPUT_SHA256.txt").write_text("".join(f"{A.sha(f)}  {f.name}\n" for f in outs), encoding="utf-8")
    log(out, "output SHA written")


def main():
    stage = sys.argv[1]
    if stage == "D":
        return part_d()
    if stage != "C":
        raise SystemExit("usage: C | D")
    out = A.OUT / "part_c"
    out.mkdir(exist_ok=True)
    log(out, "Part C start (Amendment 1 SHA e68da96c)")
    d5, d1 = A.load()
    days = [d for d in pd.date_range(A.START, A.END, freq="D") if d != A.STUDY_DAY]
    G = Grid(d5, pd.Timestamp("2025-12-01"), pd.Timestamp("2026-09-30 23:55"))
    bad = [d for d in days if not G.day_ok(d)]
    log(out, f"days {len(days)}; days with missing 5m bars {len(bad)}")
    assert not bad
    events = pd.read_parquet(A.OUT / "sweep_events.parquet")
    a1 = pd.read_parquet(A.OUT / "oracle_day.parquet").set_index("date")
    t0 = time.time()
    calls, s1 = run_c1(G, d1, days, events)
    calls.to_csv(out / "c1_calls.csv", index=False); s1.to_csv(out / "c1_ranking.csv", index=False)
    log(out, f"C1 done: {len(calls)} calls ({time.time() - t0:.0f}s)")
    t0 = time.time()
    evs, s2 = run_c2(G, d1, days, events, a1)
    evs.to_parquet(out / "c2_events.parquet", compression="zstd", index=False); s2.to_csv(out / "c2_ranking.csv", index=False)
    log(out, f"C2 done: {len(evs)} events ({time.time() - t0:.0f}s)")
    t0 = time.time()
    cfgs = [(dr, rid, gid, "FUT") for dr in DIRS for rid in RS for gid in GEOS] + [("L", rid, gid, "SPOT") for rid in RS for gid in GEOS]
    tr = run_c3(G, d1, days, cfgs)
    tr.to_parquet(out / "c3_trades.parquet", compression="zstd", index=False)
    S, daily, monthly = c3_tables(tr, days)
    S.to_csv(out / "c3_ranking.csv", index=False)
    daily.to_parquet(out / "c3_daily.parquet", compression="zstd", index=False)
    monthly.to_csv(out / "c3_monthly.csv", index=False)
    F = S[S["mode"] == "FUT"]
    ex = F.groupby("gid").mean_net_trade_pct.mean().sort_values(ascending=False).rename("mean_of_cell_means_pct").reset_index()
    ex.to_csv(out / "c3_exit_ranking.csv", index=False)
    sel = F[(F.lb95 > 0) & (F.months_pos >= 6)].head(3).cfg.tolist()
    res = dict(c3_configs=len(S), fut_configs=len(F), fut_lb95_pos=int((F.lb95 > 0).sum()), fut_lbbonf_pos=int((F.lb_bonf > 0).sum()),
               partD_selected_by_rule=sel, partD_lead="FUT|RAND|R08|G12", top_c1=s1.method.iloc[0], top_c2=s2.trigger.iloc[0])
    (out / "C_RESULTS.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    log(out, f"C3 done: {len(tr)} trades, {len(S)} configs ({time.time() - t0:.0f}s); {res}")
    outs = sorted(f for f in out.iterdir() if f.suffix in (".parquet", ".csv", ".json"))
    (out / "OUTPUT_SHA256.txt").write_text("".join(f"{A.sha(f)}  {f.name}\n" for f in outs), encoding="utf-8")
    log(out, "output SHA written")


if __name__ == "__main__":
    main()
