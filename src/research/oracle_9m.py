"""9-month BTC 2026 study (logs/oracle_9m_2026/ORACLE_9M_PROTOCOL_PREREGISTERED.md, SHA 2c68bbc4...).
Part A: hindsight oracle tables (A1 extreme, A2 close-to-close, A3 max-run DP, A4 trades + MAE/MFE, A5 day descriptors, A6 sweep events).
Part B: frozen test of the 10-day formula v1 (H2'-c) on 2026, variants V1-A/B/C/AC/S, random control.
Separate from the methods bench: no import from it, own output folder. Usage: python src/research/oracle_9m.py [A|B|all]"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
OUT = P / "logs/oracle_9m_2026"
FEES = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
C_FUT = FEES["rules"]["paper_futures_taker_per_side"]
C_SPOT = FEES["rules"]["paper_spot_per_side"]
C_MAKER = FEES["futures_usdm"]["bnb_maker"] + FEES["impact_per_side"]
MODES = {"FUT": (C_FUT, True), "SPOT": (C_SPOT, False), "FUT_MAKER": (C_MAKER, True)}
TFS = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
START, END = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-09-30")
STUDY_DAY = pd.Timestamp("2026-02-13")          # manual-study Day 10: excluded from all statistics
INPUTS = ["data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", "data/universe_hf/15m/BTCUSDT_15m_full.csv.gz",
          "data/universe_all/1h/BTCUSDT_1h_full.csv.gz", "data/universe_all/1d/BTCUSDT_1d.csv", "deploy/fees.json"]
C4 = ["open", "high", "low", "close"]
AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}


def log(msg):
    line = f"{pd.Timestamp.now("UTC"):%Y-%m-%dT%H:%M:%SZ} {msg}"
    print(line, flush=True)
    with open(OUT / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    d5 = pd.read_csv(P / INPUTS[0], parse_dates=["timestamp"]).drop_duplicates("timestamp").set_index("timestamp").sort_index()
    d5 = d5.loc["2025-12-01":"2026-09-30 23:55", C4 + ["volume"]]
    d1 = d5.resample("1D").agg(AGG)
    return d5, d1


def day_bars(d5, day, tf):
    x = d5.loc[day:day + pd.Timedelta(hours=23, minutes=55)]
    return x if tf == 5 else x.resample(f"{tf}min").agg(AGG)


# ---------------- Part A ----------------
def best_pair(lo_or_p, hi_or_p, long):
    """max over i<j of hi[j]/lo[i]-1 (long) or 1-lo[j]/hi[i] (short); first j, then first i on ties."""
    if long:
        cm = np.minimum.accumulate(lo_or_p)[:-1]
        v = hi_or_p[1:] / cm - 1
    else:
        cm = np.maximum.accumulate(hi_or_p)[:-1]
        v = 1 - lo_or_p[1:] / cm
    j = int(np.argmax(v)) + 1
    i = int(np.argmin(lo_or_p[:j])) if long else int(np.argmax(hi_or_p[:j]))
    return i, j, float(v[j - 1])


def max_run(p, c, allow_short):
    """Exact interval DP over price points p: max sum of non-overlapping trade values (long p_b/p_a-1-2c, short 1-p_b/p_a-2c)."""
    m = len(p)
    V = np.zeros(m)
    ch = [None] * m
    for b in range(1, m):
        V[b], ch[b] = V[b - 1], None
        r = p[b] / p[:b] - 1
        lv = r - 2 * c
        sv = -r - 2 * c if allow_short else np.full(b, -np.inf)
        best = np.maximum(lv, sv)
        tot = V[:b] + best
        a = int(np.argmax(tot))
        if tot[a] > V[b]:
            V[b], ch[b] = tot[a], (a, "long" if lv[a] >= sv[a] else "short")
    trades, b = [], m - 1
    while b > 0:
        if ch[b] is None:
            b -= 1
        else:
            a, side = ch[b]
            trades.append((a, b, side))
            b = a
    return float(V[-1]), trades[::-1]


def levels_for(d1, day):
    prev = d1.loc[:day - pd.Timedelta(days=1)]
    return dict(pdh=float(prev.high.iloc[-1]), pdl=float(prev.low.iloc[-1]), pdc=float(prev.close.iloc[-1]),
                d7h=float(prev.high.tail(7).max()), d7l=float(prev.low.tail(7).min()))


def sweep_levels(lo, hi, close, lv, bullish):
    """levels L with lo<L<close (bullish) or close<L<hi (bearish): round thousands + pdh/pdl/7dh/7dl."""
    a, b = (lo, close) if bullish else (close, hi)
    out = [("round", float(k * 1000)) for k in range(int(np.floor(a / 1000)) + 1, int(np.ceil(b / 1000)))]
    out += [(t, lv[t]) for t in ("pdh", "pdl", "d7h", "d7l") if a < lv[t] < b]
    return out


def new_ext_flags(lo, hi):
    n = len(lo)
    nl = np.array([k == 0 or lo[k] < lo[:k].min() for k in range(n)])
    nh = np.array([k == 0 or hi[k] > hi[:k].max() for k in range(n)])
    return nl, nh


def confirm(o, h, l, c, s, bullish):
    """first of s+1,s+2 with close>open (bullish) / close<open (bearish); the sweep extreme must hold through it."""
    n = len(c)
    for k in (s + 1, s + 2):
        if k >= n:
            return None
        if (c[k] > o[k]) if bullish else (c[k] < o[k]):
            seg = slice(s + 1, k + 1)
            ok = (l[seg] >= l[s]).all() if bullish else (h[seg] <= h[s]).all()
            return k if ok else None
    return None


def part_a(d5, d1, days):
    rows_day, rows_tf, rows_tr, rows_ev = [], [], [], []
    for day in days:
        x5 = day_bars(d5, day, 5)
        o5, h5, l5, c5 = (x5[k].to_numpy() for k in C4)
        t5 = x5.index
        lv = levels_for(d1, day)
        # A1
        i, j, v = best_pair(l5, h5, True)
        si, sj, sv = best_pair(l5, h5, False)
        O, H, L, C = o5[0], h5.max(), l5.min(), c5[-1]
        th, tl = t5[int(np.argmax(h5))], t5[int(np.argmin(l5))]
        f8 = x5.loc[:day + pd.Timedelta(hours=7, minutes=55)]
        body = abs(C - O) / (H - L)
        r = dict(date=day, open=O, high=H, low=L, close=C, ret_pct=(C / O - 1) * 100, range_pct=(H / L - 1) * 100,
                 volume=float(x5.volume.sum()), t_high=th, t_low=tl, low_first=bool(tl < th), body_ratio=body,
                 day_type="TREND" if body >= 0.6 else ("RANGE" if body <= 0.3 else "MIXED"),
                 first8h_range_pct=(f8.high.max() / f8.low.min() - 1) * 100,
                 prior_close_pos=(lv["pdc"] - lv["pdl"]) / (lv["pdh"] - lv["pdl"]),
                 a1_long_entry_t=t5[i], a1_long_entry=l5[i], a1_long_exit_t=t5[j], a1_long_exit=h5[j], a1_long_gross_pct=v * 100,
                 a1_long_net_fut_pct=(v - 2 * C_FUT) * 100, a1_long_net_spot_pct=(v - 2 * C_SPOT) * 100,
                 a1_short_entry_t=t5[si], a1_short_entry=h5[si], a1_short_exit_t=t5[sj], a1_short_exit=l5[sj],
                 a1_short_gross_pct=sv * 100, a1_short_net_fut_pct=(sv - 2 * C_FUT) * 100, **lv)
        for nm, px in (("low", L), ("high", H)):
            r[f"dist_{nm}_round_pct"] = abs(px - round(px / 1000) * 1000) / px * 100
            for t in ("pdh", "pdl", "d7h", "d7l"):
                r[f"dist_{nm}_{t}_pct"] = abs(px - lv[t]) / lv[t] * 100
        rows_day.append(r)
        # A2 / A3 / A4
        for tfn, tf in TFS.items():
            xb = day_bars(d5, day, tf)
            p = np.concatenate([[xb.open.iloc[0]], xb.close.to_numpy()])
            pt = [day] + [t + pd.Timedelta(minutes=tf) for t in xb.index]
            a, b, lg = best_pair(p, p, True)
            sa, sb, sg = best_pair(p, p, False)
            row = dict(date=day, tf=tfn, n_points=len(p), a2_long_gross_pct=lg * 100, a2_long_entry_t=pt[a], a2_long_exit_t=pt[b],
                       a2_short_gross_pct=sg * 100, a2_short_entry_t=pt[sa], a2_short_exit_t=pt[sb])
            for mode, (c, sh) in MODES.items():
                tot, trs = max_run(p, c, sh)
                row[f"a3_{mode}_total_pct"] = tot * 100
                row[f"a3_{mode}_n_trades"] = len(trs)
                if mode == "FUT_MAKER":
                    continue
                for (ea, eb, side) in trs:
                    w = x5.loc[(t5 >= pt[ea]) & (t5 < pt[eb])]
                    e, xp = p[ea], p[eb]
                    g = xp / e - 1 if side == "long" else 1 - xp / e
                    mae = (e - w.low.min()) / e if side == "long" else (w.high.max() - e) / e
                    mfe = (w.high.max() - e) / e if side == "long" else (e - w.low.min()) / e
                    rows_tr.append(dict(date=day, tf=tfn, mode=mode, side=side, entry_time=pt[ea], entry_px=e, exit_time=pt[eb],
                                        exit_px=xp, bars=eb - ea, gross_pct=g * 100, net_pct=(g - 2 * c) * 100,
                                        mae_pct=mae * 100, mfe_pct=mfe * 100))
            rows_tf.append(row)
        # A6 (15m)
        x15 = day_bars(d5, day, 15)
        o, h, l, c = (x15[k].to_numpy() for k in C4)
        nl, nh = new_ext_flags(l, h)
        n = len(c)
        for s in range(n):
            for bull in (True, False):
                for (lt, L_) in sweep_levels(l[s], h[s], c[s], lv, bull):
                    ext = (nl[s] or (s > 0 and nl[s - 1])) if bull else (nh[s] or (s > 0 and nh[s - 1]))
                    k = confirm(o, h, l, c, s, bull)
                    rest_h, rest_l = h[s + 1:], l[s + 1:]
                    if bull:
                        mfe = (rest_h.max() - c[s]) / c[s] * 100 if s < n - 1 else np.nan
                        mae = (c[s] - rest_l.min()) / c[s] * 100 if s < n - 1 else np.nan
                        rc = (c[-1] / c[s] - 1) * 100
                        held = bool(s == n - 1 or l[s] <= rest_l.min())
                        isx = bool(l[s] == l.min())
                        depth = (L_ - l[s]) / L_ * 100
                    else:
                        mfe = (c[s] - rest_l.min()) / c[s] * 100 if s < n - 1 else np.nan
                        mae = (rest_h.max() - c[s]) / c[s] * 100 if s < n - 1 else np.nan
                        rc = (1 - c[-1] / c[s]) * 100
                        held = bool(s == n - 1 or h[s] >= rest_h.max())
                        isx = bool(h[s] == h.max())
                        depth = (h[s] - L_) / L_ * 100
                    rows_ev.append(dict(date=day, bar_time=x15.index[s], side="bull" if bull else "bear", level_type=lt, level=L_,
                                        depth_pct=depth, new_extreme=bool(ext), confirmed=k is not None,
                                        confirm_time=x15.index[k] if k is not None else pd.NaT, mfe_to_eod_pct=mfe,
                                        mae_to_eod_pct=mae, ret_to_close_pct=rc, extreme_held=held, is_day_extreme=isx))
    return pd.DataFrame(rows_day), pd.DataFrame(rows_tf), pd.DataFrame(rows_tr), pd.DataFrame(rows_ev)


# ---------------- Part B ----------------
VARIANTS = {"V1-A": dict(q1=False, dt=False, long_only=False, c=C_FUT),
            "V1-B": dict(q1=True, dt=False, long_only=False, c=C_FUT),
            "V1-C": dict(q1=True, dt=True, long_only=False, c=C_FUT),
            "V1-AC": dict(q1=False, dt=True, long_only=False, c=C_FUT),
            "V1-S": dict(q1=True, dt=False, long_only=True, c=C_SPOT)}
T8 = pd.Timedelta(hours=8)


def signals(x15, lv):
    """H2'-c signals of one day: list of (sweep_time, entry_time, side, sweep_extreme)."""
    o, h, l, c = (x15[k].to_numpy() for k in C4)
    nl, nh = new_ext_flags(l, h)
    out = []
    for s in range(len(c)):
        got = {}
        for bull in (True, False):
            if not sweep_levels(l[s], h[s], c[s], lv, bull):
                continue
            if not ((nl[s] or (s > 0 and nl[s - 1])) if bull else (nh[s] or (s > 0 and nh[s - 1]))):
                continue
            k = confirm(o, h, l, c, s, bull)
            if k is not None and k + 1 < len(c):
                got["long" if bull else "short"] = (k + 1, l[s] if bull else h[s])
        if len(got) == 2:                       # both sides from one sweep bar -> skip (protocol §4)
            continue
        for side, (e, ext) in got.items():
            out.append((x15.index[s], x15.index[e], side, ext))
    return sorted(out, key=lambda z: (z[1], z[0]))


def simulate(x5, entry_t, side, sl, tp, dt, r8, pdh, pdl, day):
    """5m execution from the entry bar's open; SL first; TP removed by the day-type rule. Returns (exit_px, exit_t, reason)."""
    o, h, l, c = (x5[k].to_numpy() for k in C4)
    t = x5.index
    k0 = int(np.searchsorted(t, entry_t))
    pd_break = False
    for k in range(k0, len(t)):
        tp_on = not (dt and (pd_break or (t[k] >= day + T8 and r8 >= 3.0)))
        if side == "long":
            if o[k] <= sl: return o[k], t[k], "SL_gap"
            if l[k] <= sl: return sl, t[k] + pd.Timedelta(minutes=5), "SL"
            if tp_on and o[k] >= tp: return o[k], t[k], "TP_gap"
            if tp_on and h[k] >= tp: return tp, t[k] + pd.Timedelta(minutes=5), "TP"
            if h[k] > pdh: pd_break = True
        else:
            if o[k] >= sl: return o[k], t[k], "SL_gap"
            if h[k] >= sl: return sl, t[k] + pd.Timedelta(minutes=5), "SL"
            if tp_on and o[k] <= tp: return o[k], t[k], "TP_gap"
            if tp_on and l[k] <= tp: return tp, t[k] + pd.Timedelta(minutes=5), "TP"
            if l[k] < pdl: pd_break = True
    return c[-1], t[-1] + pd.Timedelta(minutes=5), "EOD"


def run_variant(d5, d1, days, cfg):
    trades = []
    for day in days:
        x5 = day_bars(d5, day, 5)
        x15 = day_bars(d5, day, 15)
        lv = levels_for(d1, day)
        f8 = x5.loc[:day + pd.Timedelta(hours=7, minutes=55)]
        r8 = (f8.high.max() / f8.low.min() - 1) * 100
        if cfg["q1"] and r8 < 1.0:
            continue
        last_exit = day
        for (st, et, side, ext) in signals(x15, lv):
            if cfg["long_only"] and side == "short":
                continue
            if cfg["q1"] and et < day + T8:
                continue
            if et < last_exit:
                continue
            e = float(x5.loc[et, "open"])
            sl = ext * (1 - 0.0025) if side == "long" else ext * (1 + 0.0025)
            R = abs(e - sl)
            tp = e + 2 * R if side == "long" else e - 2 * R
            xp, xt, why = simulate(x5, et, side, sl, tp, cfg["dt"], r8, lv["pdh"], lv["pdl"], day)
            g = xp / e - 1 if side == "long" else 1 - xp / e
            trades.append(dict(date=day, sweep_time=st, entry_time=et, side=side, entry_px=e, sl=sl, tp=tp, R_pct=R / e * 100,
                               exit_time=xt, exit_px=xp, reason=why, gross_pct=g * 100, net_pct=(g - 2 * cfg["c"]) * 100))
            last_exit = xt
    return pd.DataFrame(trades)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    ph = k / n
    d = 1 + z * z / n
    mid = (ph + z * z / (2 * n)) / d
    hw = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (mid - hw, mid + hw)


def random_control(d5, d1, tr, cfg, seeds=200):
    """same days, same side and R %, same exit logic; random entry 15m bar (>=08:00 when Q1 applies); share of seeds with sum >= real."""
    real = tr.net_pct.sum()
    ctx = {}
    for day in tr.date.unique():
        x5 = day_bars(d5, day, 5)
        lv = levels_for(d1, day)
        f8 = x5.loc[:day + pd.Timedelta(hours=7, minutes=55)]
        bars15 = day_bars(d5, day, 15).index
        allowed = [t for t in bars15[1:] if (not cfg["q1"] or t >= day + T8)]
        ctx[day] = (x5, lv, (f8.high.max() / f8.low.min() - 1) * 100, allowed)
    sums = []
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        s = 0.0
        for row in tr.itertuples():
            x5, lv, r8, allowed = ctx[row.date]
            et = allowed[int(rng.integers(len(allowed)))]
            e = float(x5.loc[et, "open"])
            R = e * row.R_pct / 100
            sl, tp = (e - R, e + 2 * R) if row.side == "long" else (e + R, e - 2 * R)
            xp, _, _ = simulate(x5, et, row.side, sl, tp, cfg["dt"], r8, lv["pdh"], lv["pdl"], row.date)
            g = xp / e - 1 if row.side == "long" else 1 - xp / e
            s += (g - 2 * cfg["c"]) * 100
        sums.append(s)
    sums = np.array(sums)
    return float((sums >= real).mean()), sums


def summarize(name, tr, days, cfg, oracle_tf, rc_share, rc_sums):
    stat_days = [d for d in days if d != STUDY_DAY]
    t = tr[tr.date != STUDY_DAY]
    daily = pd.DataFrame({"date": stat_days}).merge(
        t.groupby("date").agg(n_trades=("net_pct", "size"), net_pct=("net_pct", "sum"), wins=("net_pct", lambda v: int((v > 0).sum()))).reset_index(),
        on="date", how="left").fillna({"n_trades": 0, "net_pct": 0.0, "wins": 0})
    o15 = oracle_tf[oracle_tf.tf == "15m"].set_index("date")["a3_FUT_total_pct"]
    daily["oracle_fut15_pct"] = daily.date.map(o15)
    daily["variant"] = name
    daily["month"] = daily.date.dt.to_period("M").astype(str)
    monthly = daily.groupby("month").agg(trades=("n_trades", "sum"), wins=("wins", "sum"), net_pct=("net_pct", "sum"),
                                         oracle_fut15_pct=("oracle_fut15_pct", "sum")).reset_index()
    monthly["variant"] = name
    n, k = len(t), int((t.net_pct > 0).sum())
    lo, hi = wilson(k, n)
    Rm = t.R_pct.mean() if n else np.nan
    pstar = (1 + 2 * cfg["c"] * 100 / Rm) / 3 if n else np.nan
    streak, cur = 0, 0
    for v in t.net_pct:
        cur = cur + 1 if v <= 0 else 0
        streak = max(streak, cur)
    mpos = int((monthly.net_pct > 0).sum())
    s = dict(variant=name, days=len(stat_days), trades=n, wins=k, win_rate=k / n if n else np.nan, wilson_lo=lo, wilson_hi=hi,
             mean_net_pct=t.net_pct.mean() if n else np.nan, sum_net_pct=t.net_pct.sum(), mean_per_day_pct=daily.net_pct.mean(),
             months_positive=mpos, months=len(monthly), worst_month_pct=monthly.net_pct.min(), max_losing_streak=streak,
             mean_R_pct=Rm, breakeven_p=pstar, oracle_fut15_sum_pct=daily.oracle_fut15_pct.sum(),
             capture_pct=t.net_pct.sum() / daily.oracle_fut15_pct.sum() * 100,
             rc_share=rc_share, rc_mean=float(rc_sums.mean()), rc_p95=float(np.percentile(rc_sums, 95)),
             exits=t.reason.value_counts().to_dict())
    s["pass_sum"] = bool(s["sum_net_pct"] > 0)
    s["pass_wilson"] = bool(n > 0 and lo > pstar)
    s["pass_months"] = bool(mpos >= 5)
    s["pass_rc"] = bool(rc_share <= 0.05)
    s["survives"] = all([s["pass_sum"], s["pass_wilson"], s["pass_months"], s["pass_rc"]])
    return daily, monthly, s


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    pd.DataFrame([dict(path=p, sha256=sha(P / p), bytes=(P / p).stat().st_size) for p in INPUTS]).to_csv(OUT / "input_manifest.csv", index=False)
    log(f"start stage={stage}; costs FUT {C_FUT} SPOT {C_SPOT} MAKER {C_MAKER}")
    d5, d1 = load()
    days = list(pd.date_range(START, END, freq="D"))
    n5 = int(len(d5.loc["2026-01-01":"2026-09-30 23:55"]))
    log(f"loaded 5m 2026 bars {n5} (expected {273 * 288}); days {len(days)}")
    assert n5 == 273 * 288
    if stage in ("A", "all"):
        t0 = time.time()
        dd, dtf, dtr, dev = part_a(d5, d1, days)
        for nm, df in (("oracle_day", dd), ("oracle_tf", dtf), ("oracle_trades", dtr), ("sweep_events", dev)):
            df.to_parquet(OUT / f"{nm}.parquet", compression="zstd", index=False)
            log(f"A wrote {nm}.parquet rows {len(df)}")
        log(f"A done in {time.time() - t0:.0f}s")
    if stage in ("B", "all"):
        dtf = pd.read_parquet(OUT / "oracle_tf.parquet")
        alltr, alld, allm, sums = [], [], [], []
        for name, cfg in VARIANTS.items():
            t0 = time.time()
            tr = run_variant(d5, d1, days, cfg)
            tr.insert(0, "variant", name)
            stat = tr[tr.date != STUDY_DAY]
            share, rcs = random_control(d5, d1, stat, cfg)
            daily, monthly, s = summarize(name, tr, days, cfg, dtf, share, rcs)
            alltr.append(tr); alld.append(daily); allm.append(monthly); sums.append(s)
            log(f"B {name}: trades {s['trades']} wins {s['wins']} sum {s['sum_net_pct']:.3f}% months+ {s['months_positive']}/{s['months']} "
                f"rc_share {share:.3f} survives {s['survives']} ({time.time() - t0:.0f}s)")
        pd.concat(alltr).to_csv(OUT / "v1_trades.csv", index=False)
        pd.concat(alld).to_csv(OUT / "v1_daily.csv", index=False)
        pd.concat(allm).to_csv(OUT / "v1_monthly.csv", index=False)
        (OUT / "V1_RESULTS.json").write_text(json.dumps(sums, indent=1, default=str), encoding="utf-8")
        log("B wrote v1_trades.csv v1_daily.csv v1_monthly.csv V1_RESULTS.json")
    outs = sorted(f for f in OUT.iterdir() if f.suffix in (".parquet", ".csv", ".json") and f.name != "input_manifest.csv")
    (OUT / "OUTPUT_SHA256.txt").write_text("".join(f"{sha(f)}  {f.name}\n" for f in outs), encoding="utf-8")
    log("output SHA written")


if __name__ == "__main__":
    main()
