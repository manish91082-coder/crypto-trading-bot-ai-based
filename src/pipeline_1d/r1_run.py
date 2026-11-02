"""
Round 1 runner. Protocol: logs/research_r1/R1_PROTOCOL_PREREGISTERED.md (+ CODE_CHANGES_AFTER_LOCK.md clarifications).
Usage: python r1_run.py g0        engine with hooks off == F7 (RS, OFF_LO, OFF_LS) sleeve finals within $0.01
       python r1_run.py check     features re-derived for random samples with plain loops (no strategy result)
       python r1_run.py E3|E1|E2|E4|N1|E11     one experiment (runs + controls + gates -> claims_<EXP>.json)
Every output goes to logs/research_r1/.
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import f7_run as F7R
import r1_engine as E
from config import LOGS_DIR

F2R, CR, S13, S19, S23, S24, S27, S1 = F7R.F2R, F7R.CR, F7R.S13, F7R.S19, F7R.S23, F7R.S24, F7R.S27, F7R.S1
OUT = LOGS_DIR / "research_r1"
PROTO = "R1_PROTOCOL_PREREGISTERED.md"
RS = F7R.RS
N, KEEP, F50, CL, CS = F7R.N_HOLD, F7R.KEEP, F7R.F50, F7R.C_LONG, F7R.C_SHORT
SLEEVES = ("D1", "H4", "H1")
SEEDS = range(10)
DSR_N = 91
BASE = dict(final=88400.87, max_dd_pct=21.37, ret_2022=36.54, short_pf=1.07, short_payoff=0.81, long_pf=1.22, long_payoff=1.57)
DAY = pd.Timedelta(days=1)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------ inputs and daily features
def load_r1():
    I = F7R.load("MAIN")
    start, end = I["start"], I["end"]
    dk, lk, dn, ln, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", end)
    data, last = {**dk, **dn}, {**lk, **ln}
    syms = sorted(set().union(*[set(r.symbol) for b in I["rows"].values() for r in b.values()]))
    bars1 = {s: S24.bars_1h(S24.UNI1H / f"{s}_1h_full.csv.gz").astype("float64") for s in syms if (S24.UNI1H / f"{s}_1h_full.csv.gz").exists()}
    perp_h, gate = F2R.load_perp({s: b.close for s, b in bars1.items()})
    del bars1
    I["perp_low"] = {}
    for k in SLEEVES:
        lows = {}
        for s, d in perp_h.items():
            a = d[["low"]] if F2R.STEP[k] == "h" else d.low.resample(F2R.STEP[k], label="left", closed="left").min().to_frame("low")
            lows[s] = a.low.reindex(I["grids"][k]).values
        I["perp_low"][k] = lows
    feats = {}
    for s in syms:
        f = {}
        if s in data:
            c = data[s].set_index("timestamp").close
            c = c[c.index <= last[s]]
            r = c.pct_change(fill_method=None)
            f["max7"] = r.rolling(7, min_periods=7).max()
            f["sig_spot"] = r.rolling(60, min_periods=60).std()
        if s in perp_h:
            d = perp_h[s]
            pc = d.close.resample("1D").last()
            f["sig_perp"] = pc.pct_change(fill_method=None).rolling(60, min_periods=60).std()
            f["qv30"] = d.quote_volume.resample("1D").sum().rolling(30, min_periods=30).mean()
            f["first_perp"] = d.index.min()
        feats[s] = f
    I["feats"], I["perp_h_syms"] = feats, set(perp_h)
    raw_f = {}
    for s in perp_h:
        ff = F2R.FUM / f"{s}_funding.csv"
        if ff.exists():
            fr = pd.read_csv(ff, parse_dates=["time"]).sort_values("time")
            raw_f[s] = (fr.time.values.astype("datetime64[ns]"), fr.funding_rate.values.astype(float))
    I["raw_fund"] = raw_f                        # every published funding rate (protocol: "the mean of its last 9 funding rates")
    return I


def fval(I, s, key, day):
    v = I["feats"].get(s, {}).get(key)
    if v is None:
        return np.nan
    x = v.get(day, np.nan)
    return float(x) if x is not None else np.nan


def age_days(I, s, t):
    f = I["feats"].get(s, {}).get("first_perp")
    return np.nan if f is None else (t.normalize() + DAY - f) / DAY


def fund_mean9(I, s, t):
    if s not in I["raw_fund"]:
        return np.nan
    et, rate = I["raw_fund"][s]
    j = np.searchsorted(et, np.datetime64(t.normalize() + DAY), "right")
    return float(rate[max(0, j - 9):j].mean()) if j >= 9 else np.nan


def bucket(a):
    return np.nan if not np.isfinite(a) else 0 if a < 60 else 1 if a < 180 else 2 if a < 365 else 3


# ------------------------------------------------------------------ hooks
class Log:
    def __init__(self):
        self.rows = []


def h_e3b(I):
    def order(t, sh_, ranked, k):
        ages = {s: age_days(I, s, t) for s in sh_}
        return sorted(sh_, key=lambda s: (ages[s] if np.isfinite(ages[s]) else 1e9))        # stable: AI order on ties
    return order


def h_e3c(I, seed):
    rng = np.random.default_rng(seed)

    def order(t, sh_, ranked, k):
        b = {s: bucket(age_days(I, s, t)) for s in sh_}
        chosen = []
        for s in sh_[:N]:
            pool = [x for x in sh_ if b[x] == b[s] and x not in chosen]
            if pool:
                chosen.append(pool[int(rng.integers(len(pool)))])
        return chosen + [x for x in sh_ if x not in chosen]
    return order


def h_e2(I, sleeve, log, counts):
    def order(t, sh_, ranked, k):
        day = t.normalize()
        qv = {s: fval(I, s, "qv30", day) for s in sh_}
        med = np.nanmedian([v for v in qv.values() if np.isfinite(v)]) if any(np.isfinite(v) for v in qv.values()) else np.nan
        out = []
        for s in sh_:
            fm, ag = fund_mean9(I, s, t), age_days(I, s, t)
            ok = (np.isfinite(fm) and fm >= -0.0003) and (np.isfinite(ag) and ag >= 60) and (np.isfinite(qv[s]) and np.isfinite(med) and qv[s] >= 0.25 * med)
            log.rows.append(dict(sleeve=sleeve, t=t, symbol=s, fund_mean9=fm, age=ag, qv30=qv[s], qv30_median=med, ok=ok))
            if ok:
                out.append(s)
        counts[(sleeve, t)] = len(sh_) - len(out)
        return out
    return order


def h_drop_random(counts, sleeve, seed):
    rng = np.random.default_rng(seed)

    def order(t, sh_, ranked, k):
        m = counts.get((sleeve, t), 0)
        if m <= 0:
            return sh_
        drop = set(rng.choice(len(sh_), size=min(m, len(sh_)), replace=False).tolist())
        return [s for i, s in enumerate(sh_) if i not in drop]
    return order


def h_perm(seed):
    rng = np.random.default_rng(seed)

    def order(t, sh_, ranked, k):
        return [sh_[i] for i in rng.permutation(len(sh_))]
    return order


def cap_weights(w, cap=0.30):
    w = np.asarray(w, float)
    w = w / w.sum()
    for _ in range(50):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        free = ~over & (w < cap)
        if not free.any():                     # every weight at the cap: the rest stays unallocated (cash), CODE_CHANGES 6
            break
        w[free] += excess * w[free] / w[free].sum()
    return w


def h_e4(I, log, sleeve):
    def wf(side, t, targets, k):
        day = t.normalize()
        key = "sig_spot" if side == "long" else "sig_perp"
        sig = np.array([fval(I, s, key, day) for s in targets])
        if np.isfinite(sig).any():
            sig = np.where(np.isfinite(sig), sig, np.nanmedian(sig))
        else:
            sig = np.ones(len(targets))
        w = cap_weights(1.0 / sig)
        for s, x, sg in zip(targets, w, sig):
            log.rows.append(dict(sleeve=sleeve, t=t, side=side, symbol=s, sigma=sg, w=x))
        return dict(zip(targets, w))
    return wf


def h_dirichlet(seed):
    rng = np.random.default_rng(seed)

    def wf(side, t, targets, k):
        return dict(zip(targets, cap_weights(rng.dirichlet(np.ones(len(targets))))))
    return wf


def n1_blocked(I, t, ranked):
    day = t.normalize()
    mx = pd.Series({s: fval(I, s, "max7", day) for s in ranked}).dropna()
    if mx.empty:
        return set()
    return set(mx[mx.rank(pct=True) > 0.80].index)


def h_n1_block(I, log, sleeve, counts):
    def block(t, ranked, k):
        b = n1_blocked(I, t, ranked)
        counts[(sleeve, t)] = len(b)
        for s in ranked:
            log.rows.append(dict(sleeve=sleeve, t=t, symbol=s, max7=fval(I, s, "max7", t.normalize()), blocked=s in b))
        return b
    return block


def h_n1b_order(I):
    def order(t, sh_, ranked, k):
        b = n1_blocked(I, t, ranked)
        c = sh_[:10]
        return [s for s in c if s in b] + [s for s in c if s not in b] + sh_[10:]
    return order


def h_block_random(counts, sleeve, seed):
    rng = np.random.default_rng(seed)

    def block(t, ranked, k):
        m = counts.get((sleeve, t), 0)
        return set(rng.choice(ranked, size=min(m, len(ranked)), replace=False).tolist()) if m > 0 and ranked else set()
    return block


# ------------------------------------------------------------------ runs and metrics
def run(I, name, hooks_by_sleeve, inv_s=F50, rules=RS, save=False):
    sl = {}
    for k in SLEEVES:
        kw = dict(rules)
        kw.update(hooks_by_sleeve.get(k, {}) if isinstance(hooks_by_sleeve, dict) and k in hooks_by_sleeve else {})
        sl[k] = E.sim_ls(I["rows"]["AI"][k], I["grids"][k], I["decide"][k], I["spot"][k], I["perp"][k], I["fund"], F50, inv_s,
                         N, KEEP, CL, CS, **kw)
    eqd = pd.DataFrame({k: F2R.daily_eq(v["eq"], k) for k, v in sl.items()})
    mix = eqd.mean(axis=1)
    fin = float(np.mean([v["final"] for v in sl.values()]))
    st = S27.stats(fin, mix, I["start"], I["end"])
    tr = pd.concat([v["trades"].assign(sleeve=k) for k, v in sl.items()], ignore_index=True)
    tr["ret"] = tr.pnl / tr.cost

    def side_stats(t):
        if not len(t):
            return dict(n=0)
        w, l = t[t.pnl > 0], t[t.pnl <= 0]
        return dict(n=int(len(t)), pf=round(float(w.pnl.sum() / -l.pnl.sum()), 3) if len(l) else None,
                    payoff=round(float(w.ret.mean() / -l.ret.mean()), 3) if len(w) and len(l) else None, pnl_mix=round(float(t.pnl.sum()) / 3, 2))
    spd = pd.concat([v["short_pnl"].groupby(v["short_pnl"].index.normalize()).sum() for v in sl.values()], axis=1).sum(axis=1) / 3
    wk = mix.resample("W").last()
    wk_ret = (wk / wk.shift(1).fillna(10_000.0) - 1)
    out = dict(mix=st, sleeves={k: round(v["final"], 2) for k, v in sl.items()}, long=side_stats(tr[tr.side == "long"]),
               short=side_stats(tr[tr.side == "short"]), hedge=side_stats(tr[tr.side == "hedge"]),
               worst_short_day=round(float(spd.min()), 2), worst_week_pct=round(float(wk_ret.min() * 100), 3),
               liquidations=int(sum(v["liquidations"] for v in sl.values())), stops=int(sum(v["stops"] for v in sl.values())),
               hedge_stops=int(sum(v["hedge_stops"] for v in sl.values())), long_blocked=int(sum(v["long_blocked"] for v in sl.values())),
               perp_longs=int(sum(v["perp_longs"] for v in sl.values())), spot_longs=int(sum(v["spot_longs"] for v in sl.values())),
               long_funding_mix=round(float(tr[(tr.side == "long") & (tr["venue"] == "perp")].funding.sum()) / 3, 2) if "venue" in tr else 0.0)
    if save:
        eqd.assign(M_AI3=mix).to_csv(OUT / f"equity_{name}.csv", index_label="date")
        tr.to_csv(OUT / f"trades_{name}.csv", index=False)
        spd.to_csv(OUT / f"short_pnl_daily_{name}.csv", header=["short_pnl_mix"])
    print(name, json.dumps(st), "short", out["short"], "long", out["long"], flush=True)
    return out


def dsr(name):
    import scipy.stats as ss
    c1 = json.loads((S1.OUT / "claims.json").read_text())
    e = pd.read_csv(OUT / f"equity_{name}.csv", parse_dates=["date"]).set_index("date").M_AI3
    r = e.pct_change().dropna().values
    srv = float(r.mean() / r.std(ddof=1))
    return dict(sr_annual_365=srv * np.sqrt(365), N=DSR_N,
                dsr=S1.dsr(srv, len(r), float(ss.skew(r)), float(ss.kurtosis(r, fisher=False)), DSR_N, c1["V_daily_sr"])[1])


def ctrl(I, name, make_hooks):
    res = [run(I, f"{name}_ctrl{sd}", make_hooks(sd)) for sd in SEEDS]
    return res


def med(vals):
    v = [x for x in vals if x is not None]
    return float(np.median(v)) if v else None


# ------------------------------------------------------------------ experiments
def exp_E3(I):
    """E3a from the stored F7 RS trades; E3b AGE rule; E3c age-matched random (10 seeds)."""
    tr = pd.concat([pd.read_csv(F7R.OUT / f"trades_MAIN_{k}_AI_RS.csv", parse_dates=["entry_time"]).assign(sleeve=k) for k in SLEEVES])
    sh = tr[tr.side == "short"].copy()
    sh["age"] = [age_days(I, s, t - DAY) for s, t in zip(sh.symbol, sh.entry_time)]       # age at the decision (one bar earlier)
    sh["bucket"] = sh.age.map(bucket)
    tot = sh.pnl.sum()
    a = {str(b): dict(n=int(len(g)), pnl_share=round(float(g.pnl.sum() / tot), 3),
                      pf=round(float(g.pnl[g.pnl > 0].sum() / -g.pnl[g.pnl <= 0].sum()), 3) if (g.pnl <= 0).any() else None)
         for b, g in sh.groupby("bucket")}
    f7_short = float(tot) / 3
    b_ = run(I, "E3b_AGE", {k: dict(short_order=h_e3b(I)) for k in SLEEVES}, save=True)
    c_ = [run(I, f"E3c_seed{sd}", {k: dict(short_order=h_e3c(I, sd * 10 + i)) for i, k in enumerate(SLEEVES)}) for sd in SEEDS]
    c_med = med([x["short"].get("pnl_mix") for x in c_])
    reading = ("AI short skill not shown beyond listing age" if (b_["short"]["pnl_mix"] >= 0.8 * f7_short or (c_med is not None and c_med >= 0.8 * f7_short))
               else "AI short adds beyond listing age")
    return dict(E3a_buckets_lt60_60_180_180_365_ge365=a, F7_short_pnl_mix=round(f7_short, 2), E3b=b_, E3b_dsr=dsr("E3b_AGE"),
                E3c_short_pnl_mix=[x["short"].get("pnl_mix") for x in c_], E3c_median=c_med, reading=reading)


def exp_E1(I):
    out = {}
    for tag, w in (("E1a", 0.5), ("E1b", 1.0)):
        r = run(I, tag, {k: dict(hedge_w=w) for k in SLEEVES}, save=True)
        base_wsd = BASE_WORST_SHORT_DAY
        g = dict(G1=r["mix"]["max_dd_pct"] <= BASE["max_dd_pct"], G2=r["mix"]["final"] >= 0.80 * BASE["final"],
                 G3=r["mix"].get("ret_2022", -1) > 0, G4=r["worst_short_day"] >= base_wsd)
        if w < 1.0:
            cs = [run(I, f"{tag}_ctrl{sd}", {k: dict(hedge_w=w, short_order=h_perm(sd * 10 + i)) for i, k in enumerate(SLEEVES)})
                  for sd in SEEDS]
            g["G5"] = r["mix"]["final"] > med([c["mix"]["final"] for c in cs])
            r["control_finals"] = [c["mix"]["final"] for c in cs]
        else:
            g["G5"] = "n/a (CODE_CHANGES 1a)"
        g = {k: (bool(v) if isinstance(v, (bool, np.bool_)) else v) for k, v in g.items()}
        g["decision"] = "PASS" if all(v is True or v == "n/a (CODE_CHANGES 1a)" for v in g.values()) else "FAIL"
        out[tag] = dict(result=r, gates=g, dsr=dsr(tag), baseline_worst_short_day=base_wsd)
    return out


def exp_E2(I):
    log, counts = Log(), {}
    r = run(I, "E2", {k: dict(short_order=h_e2(I, k, log, counts), freed_to_hedge=True) for k in SLEEVES}, save=True)
    pd.DataFrame(log.rows).to_csv(OUT / "decisions_E2.csv", index=False)
    cs = [run(I, f"E2_ctrl{sd}", {k: dict(short_order=h_drop_random(counts, k, sd * 10 + i), freed_to_hedge=True) for i, k in enumerate(SLEEVES)})
          for sd in SEEDS]
    g = dict(G1=(r["short"]["pf"] or 0) > BASE["short_pf"] and (r["short"]["payoff"] or 0) > BASE["short_payoff"],
             G2=r["mix"]["max_dd_pct"] <= BASE["max_dd_pct"], G3=r["mix"]["final"] >= 0.80 * BASE["final"],
             G4=r["mix"].get("ret_2022", -1) > 0, G5=(r["short"]["pf"] or 0) > med([c["short"].get("pf") for c in cs]))
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = "PASS" if all(g.values()) else "FAIL"
    return dict(E2=dict(result=r, gates=g, dsr=dsr("E2"), control_short_pf=[c["short"].get("pf") for c in cs],
                        filtered_total=int(sum(counts.values()))))


def exp_E4(I):
    log = Log()
    r = run(I, "E4", {k: dict(weight_fn=h_e4(I, log, k)) for k in SLEEVES}, save=True)
    pd.DataFrame(log.rows).to_csv(OUT / "decisions_E4.csv", index=False)
    cs = [run(I, f"E4_ctrl{sd}", {k: dict(weight_fn=h_dirichlet(sd * 10 + i)) for i, k in enumerate(SLEEVES)}) for sd in SEEDS]
    g = dict(G1=r["mix"]["max_dd_pct"] < BASE["max_dd_pct"], G2=r["worst_week_pct"] > BASE_WORST_WEEK,
             G3=r["mix"]["final"] >= 0.85 * BASE["final"], G4=r["mix"].get("ret_2022", -1) > 0,
             G5=r["mix"]["max_dd_pct"] < med([c["mix"]["max_dd_pct"] for c in cs]))
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = "PASS" if all(g.values()) else "FAIL"
    return dict(E4=dict(result=r, gates=g, dsr=dsr("E4"), baseline_worst_week_pct=BASE_WORST_WEEK,
                        control_dd=[c["mix"]["max_dd_pct"] for c in cs]))


def exp_N1(I):
    out = {}
    for tag in ("N1a", "N1b"):
        log, counts = Log(), {}
        hooks = {k: dict(long_block=h_n1_block(I, log, k, counts)) for k in SLEEVES}
        if tag == "N1b":
            for k in SLEEVES:
                hooks[k]["short_order"] = h_n1b_order(I)
        r = run(I, tag, hooks, save=True)
        pd.DataFrame(log.rows).to_csv(OUT / f"decisions_{tag}.csv", index=False)
        cs = [run(I, f"{tag}_ctrl{sd}", {k: dict(long_block=h_block_random(counts, k, sd * 10 + i)) for i, k in enumerate(SLEEVES)}) for sd in SEEDS]
        g = dict(G1=(r["long"]["pf"] or 0) > BASE["long_pf"] and (r["long"]["payoff"] or 0) > BASE["long_payoff"],
                 G2=r["mix"]["max_dd_pct"] <= BASE["max_dd_pct"],
                 G3=(r["mix"]["final"] >= BASE["final"]) if tag == "N1a" else (r["mix"]["final"] > BASE["final"]),
                 G4=r["mix"].get("ret_2022", -1) > 0, G5=(r["long"]["pf"] or 0) > med([c["long"].get("pf") for c in cs]))
        g = {k: bool(v) for k, v in g.items()}
        g["decision"] = "PASS" if all(g.values()) else "FAIL"
        out[tag] = dict(result=r, gates=g, dsr=dsr(tag), control_long_pf=[c["long"].get("pf") for c in cs])
    return out


def exp_E11(I):
    r = run(I, "E11", {k: dict(long_perp_ok=(lambda s, t, k_: s in I["perp_h_syms"]), perp_low=I["perp_low"][k]) for k in SLEEVES}, save=True)
    g = dict(G1=r["mix"]["final"] > BASE["final"], G2=r["mix"]["max_dd_pct"] <= BASE["max_dd_pct"] + 2.0, G3=r["mix"].get("ret_2022", -1) > 0)
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = "PASS" if all(g.values()) else "FAIL"
    return dict(E11=dict(result=r, gates=g, dsr=dsr("E11")))


BASE_WORST_SHORT_DAY, BASE_WORST_WEEK = None, None


def baseline(I):
    """F7 RS through the R1 engine (hooks off): the worst short-side day and worst week used by E1 G4 / E4 G2."""
    global BASE_WORST_SHORT_DAY, BASE_WORST_WEEK
    f = OUT / "baseline_F7_RS.json"
    if f.exists():
        b = json.loads(f.read_text())
    else:
        r = run(I, "BASE_F7_RS", {}, save=True)
        assert abs(r["mix"]["final"] - BASE["final"]) < 0.02, r["mix"]["final"]
        b = dict(final=r["mix"]["final"], worst_short_day=r["worst_short_day"], worst_week_pct=r["worst_week_pct"])
        f.write_text(json.dumps(b, indent=2))
    BASE_WORST_SHORT_DAY, BASE_WORST_WEEK = b["worst_short_day"], b["worst_week_pct"]
    return b


def g0(I):
    C = json.loads((F7R.OUT / "claims.json").read_text())["MAIN"]
    res = {}
    for name, inv_s, rules in (("OFF_LO", 0.0, {}), ("OFF_LS", F50, {}), ("RS", F50, RS)):
        for k in SLEEVES:
            r = E.sim_ls(I["rows"]["AI"][k], I["grids"][k], I["decide"][k], I["spot"][k], I["perp"][k], I["fund"], F50, inv_s, N, KEEP, CL, CS, **rules)
            res[f"{name}_{k}"] = bool(abs(r["final"] - C[name]["sleeves"][k]["final"]) < 0.01)
    (OUT / "G0.json").write_text(json.dumps(res, indent=2))
    print("G0", res, "PASS" if all(res.values()) else "FAIL")
    assert all(res.values())


def check(I):
    """Re-derive the daily features for random (coin, day) samples with plain loops from the raw files (no strategy run)."""
    rng = np.random.default_rng(5)
    syms = [s for s in I["feats"] if "max7" in I["feats"][s] and "qv30" in I["feats"][s]]
    n_ok = 0
    for s in rng.choice(syms, 15, replace=False):
        d1 = pd.read_csv(S13.UNI / "1d" / f"{s}_1d.csv", parse_dates=["timestamp"])
        cl = dict(zip(d1.timestamp, d1.close))
        days = sorted(cl)
        lastd = I["feats"][s]["max7"].index.max()
        cand = [d for d in days[70:] if d <= lastd]
        for day in rng.choice(cand, 4, replace=False):
            day = pd.Timestamp(day)
            i = days.index(day)
            rets = [cl[days[j]] / cl[days[j - 1]] - 1 for j in range(i - 6, i + 1)]
            assert abs(max(rets) - fval(I, s, "max7", day)) < 1e-12, (s, day, "max7")
            r60 = [cl[days[j]] / cl[days[j - 1]] - 1 for j in range(i - 59, i + 1)]
            m = sum(r60) / 60
            sd = (sum((x - m) ** 2 for x in r60) / 59) ** 0.5
            assert abs(sd - fval(I, s, "sig_spot", day)) < 1e-10, (s, day, "sig")
            n_ok += 1
    print(f"[check PASS] MAX7 and spot sigma60 re-derived with plain loops for {n_ok} coin-days")
    n2 = 0
    psyms = [s for s in syms if s in I["raw_fund"]]
    for s in rng.choice(psyms, 10, replace=False):
        fr = pd.read_csv(F2R.FUM / f"{s}_funding.csv", parse_dates=["time"]).sort_values("time")
        ph = pd.read_csv(F2R.FUM / f"{s}_perp_1h.csv.gz", parse_dates=["timestamp"])
        first = ph.timestamp.min()
        for t in pd.date_range("2021-03-01", "2026-09-01", freq="97D"):
            ev = [x.funding_rate for x in fr.itertuples() if x.time <= t + DAY]
            want = sum(ev[-9:]) / 9 if len(ev) >= 9 else np.nan
            got = fund_mean9(I, s, t)
            # the engine's funding table keeps events with a known price (F2 rule); compare where both exist
            assert (np.isnan(want) and np.isnan(got)) or abs(want - got) < 1e-12, (s, t, want, got)
            assert abs(age_days(I, s, t) - (t + DAY - first) / DAY) < 1e-9
            day = t.normalize()
            q = ph[(ph.timestamp >= day - pd.Timedelta(days=29)) & (ph.timestamp < day + DAY)]
            qd = q.groupby(q.timestamp.dt.normalize()).quote_volume.sum()
            got_q = fval(I, s, "qv30", day)
            if len(qd) == 30 and np.isfinite(got_q):
                assert abs(qd.mean() - got_q) < 1e-6 * max(1.0, got_q), (s, day, qd.mean(), got_q)
            n2 += 1
    print(f"[check PASS] funding mean-9, perp age and 30-day perp quote volume re-derived for {n2} coin-dates")


def main():
    what = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "R1_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    I = load_r1()
    if what == "g0":
        return g0(I)
    if what == "check":
        return check(I)
    baseline(I)
    res = dict(E3=exp_E3, E1=exp_E1, E2=exp_E2, E4=exp_E4, N1=exp_N1, E11=exp_E11)[what](I)
    claims = dict(protocol_sha256=h_, experiment=what, results=res, baseline=dict(BASE, worst_short_day=BASE_WORST_SHORT_DAY,
                  worst_week_pct=BASE_WORST_WEEK), engine_sha256=sha(E.__file__), runner_sha256=sha(__file__),
                  seconds=round(time.time() - t0))
    (OUT / f"claims_{what}.json").write_text(json.dumps(claims, indent=2, default=str))
    print("DONE", what, json.dumps({k: (v.get("gates") if isinstance(v, dict) else None) for k, v in res.items()}, default=str))


if __name__ == "__main__":
    main()
