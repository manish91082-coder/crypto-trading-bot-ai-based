"""
Independent verifier for Round 1 (logs/research_r1). Usage: python verify_r1_claims.py E3|E1|E2|E4|N1|E11
V1 protocol hash; engine / runner hashes in the claims equal the files.
V2 for every run in the claims: mix final = mean of the sleeve finals; max DD, 2022 return and worst week re-derived with
   plain loops from the equity file; long / short PF and payoff re-derived from the trade file; worst short-side day from
   the short P&L file; every gate re-applied.
V3 mechanics, re-derived from the raw files:
   E2  every NEW short has ok=True in the decision log; for 40 random decision rows, funding mean-9, perp age and the
       30-day perp quote volume re-derived with plain loops from the raw files, and ok re-derived;
   N1  no NEW long entry was blocked at its decision; for 40 random rows MAX7 re-derived, and blocked == (pct rank > 0.8);
   E4  weights of each (sleeve, decision, side) sum to min(1, 0.3 n) and are <= 0.30 (CODE_CHANGES 6); sigma60 re-derived for 30 rows;
   E1  hedge stops filled at entry x 1.5 x 1.01 (or open x 1.01 on a gap), checked on the raw perp 1h bars (30 trades);
   E11 perp-long entry price = the raw perp open of the entry bar (30 trades); perp-long funding <= 0 where all rates > 0;
   E3  the E3a bucket shares re-derived from the F7 RS trades with a plain age computation.
"""
import sys
import json
import math
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import r1_run as R
from config import DATA_DIR

FUM, UNI1D = DATA_DIR / "futures_um", DATA_DIR / "universe_all" / "1d"
DAY = pd.Timedelta(days=1)
NAMES = pd.read_csv(R.LOGS_DIR / "futures_um_download" / "perp_names.csv").set_index("symbol").perp


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def scale(sym):
    p = NAMES[sym]
    return 1e6 if p.startswith("1000000") else 1e3 if p.startswith("1000") and not sym.startswith("1000") else 1.0


def plain_stats(name):
    e = pd.read_csv(R.OUT / f"equity_{name}.csv", parse_dates=["date"])
    a = [10_000.0] + list(e.M_AI3)
    pk, dd = a[0], 0.0
    for v in a:
        pk = max(pk, v)
        dd = max(dd, (pk - v) / pk)
    y21 = e[e.date.dt.year == 2021].M_AI3.iloc[-1]
    y22 = e[e.date.dt.year == 2022].M_AI3.iloc[-1]
    wk = e.set_index("date").M_AI3.resample("W").last()
    prev, worst = 10_000.0, math.inf
    for v in wk.values:
        worst = min(worst, v / prev - 1)
        prev = v
    return dict(dd=dd * 100, r22=(y22 / y21 - 1) * 100, worst_week=worst * 100)


def plain_side(name, side):
    t = pd.read_csv(R.OUT / f"trades_{name}.csv")
    t = t[t.side == side]
    wins = [x for x in t.itertuples() if x.pnl > 0]
    loss = [x for x in t.itertuples() if x.pnl <= 0]
    if not wins or not loss:
        return None, None
    pf = sum(x.pnl for x in wins) / -sum(x.pnl for x in loss)
    payoff = (sum(x.pnl / x.cost for x in wins) / len(wins)) / -(sum(x.pnl / x.cost for x in loss) / len(loss))
    return pf, payoff


def v2(name, r):
    st = plain_stats(name)
    assert abs(st["dd"] - r["mix"]["max_dd_pct"]) < 0.01 and abs(st["r22"] - r["mix"]["ret_2022"]) < 0.01, (name, st, r["mix"])
    assert abs(st["worst_week"] - r["worst_week_pct"]) < 0.001, (name, st["worst_week"], r["worst_week_pct"])
    assert abs(sum(r["sleeves"].values()) / 3 - r["mix"]["final"]) < 0.02, name
    for side in ("long", "short"):
        pf, pay = plain_side(name, side)
        if pf is not None:
            assert abs(pf - r[side]["pf"]) < 0.001 and abs(pay - r[side]["payoff"]) < 0.001, (name, side, pf, pay, r[side])
    sp = pd.read_csv(R.OUT / f"short_pnl_daily_{name}.csv")
    assert abs(sp.short_pnl_mix.min() - r["worst_short_day"]) < 0.01, name
    return st


def fund9_plain(sym, t):
    fr = pd.read_csv(FUM / f"{sym}_funding.csv", parse_dates=["time"])
    ev = sorted((x.time, x.funding_rate) for x in fr.itertuples() if x.time <= t.normalize() + DAY)
    return sum(r for _, r in ev[-9:]) / 9 if len(ev) >= 9 else float("nan")


def perp_first(sym):
    return pd.read_csv(FUM / f"{sym}_perp_1h.csv.gz", usecols=["timestamp"], parse_dates=["timestamp"]).timestamp.min()


def qv30_plain(sym, day):
    ph = pd.read_csv(FUM / f"{sym}_perp_1h.csv.gz", usecols=["timestamp", "quote_volume"], parse_dates=["timestamp"])
    tot = {}
    for x in ph.itertuples():
        d = x.timestamp.normalize()
        if day - pd.Timedelta(days=29) <= d <= day:
            tot[d] = tot.get(d, 0.0) + x.quote_volume
    return sum(tot.values()) / 30 if len(tot) == 30 else float("nan")


def daily_ret_plain(sym, day, n):
    """the last n daily close-to-close returns up to `day`, or None if the history is too short / day missing."""
    d = pd.read_csv(UNI1D / f"{sym}_1d.csv", parse_dates=["timestamp"])
    cl = dict(zip(d.timestamp, d.close))
    days = sorted(cl)
    if day not in cl or days.index(day) < n:
        return None
    i = days.index(day)
    return [cl[days[j]] / cl[days[j - 1]] - 1 for j in range(i - n + 1, i + 1)]


def entries(name, side):
    t = pd.read_csv(R.OUT / f"trades_{name}.csv", parse_dates=["entry_time", "exit_time"])
    return t[t.side == side]


def decision_time(sleeve, entry_time):
    """fills happen at the bar after the decision: D1 -> previous day; H4 -> previous 4h bar; H1 -> previous hour."""
    return entry_time - {"D1": DAY, "H4": pd.Timedelta(hours=4), "H1": pd.Timedelta(hours=1)}[sleeve]


def main(exp):
    C = json.loads((R.OUT / f"claims_{exp}.json").read_text())
    assert sha(R.OUT / R.PROTO) == (R.OUT / "R1_PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    assert sha(R.E.__file__) == C["engine_sha256"], "engine changed after the run"
    if sha(R.__file__) == C["runner_sha256"]:
        how = "runner as run"
    else:                                   # a later runner change must list this run's runner hash as still valid for it
        ok = [ln for ln in (R.OUT / "CODE_CHANGES_AFTER_LOCK.md").read_text(encoding="utf-8").splitlines()
              if ln.startswith("- runner-valid:") and C["runner_sha256"] in ln and exp in ln.split(" for ")[-1].replace(",", " ").split()]
        assert ok, "runner changed after the run and this run's runner hash is not documented as valid for it"
        how = "documented earlier runner hash"
    print(f"[V1 PASS] {exp}: protocol, engine and runner hashes ({how})")
    base = C["baseline"]
    res = C["results"]
    runs = {"E3": [("E3b_AGE", res.get("E3b"))]}.get(exp) or [(k, v["result"]) for k, v in res.items()]
    for name, r in runs:
        st = v2(name, r)
        if exp == "E3":
            continue
        g = res[name]["gates"]
        if name in ("E1a", "E1b"):
            want = dict(G1=st["dd"] <= base["max_dd_pct"], G2=r["mix"]["final"] >= 0.80 * base["final"], G3=st["r22"] > 0,
                        G4=r["worst_short_day"] >= base["worst_short_day"])
        elif name == "E2":
            want = dict(G1=(r["short"]["pf"] or 0) > base["short_pf"] and (r["short"]["payoff"] or 0) > base["short_payoff"],
                        G2=st["dd"] <= base["max_dd_pct"], G3=r["mix"]["final"] >= 0.80 * base["final"], G4=st["r22"] > 0)
        elif name == "E4":
            want = dict(G1=st["dd"] < base["max_dd_pct"], G2=st["worst_week"] > base["worst_week_pct"],
                        G3=r["mix"]["final"] >= 0.85 * base["final"], G4=st["r22"] > 0)
        elif name.startswith("N1"):
            want = dict(G1=(r["long"]["pf"] or 0) > base["long_pf"] and (r["long"]["payoff"] or 0) > base["long_payoff"],
                        G2=st["dd"] <= base["max_dd_pct"], G4=st["r22"] > 0,
                        G3=(r["mix"]["final"] >= base["final"]) if name == "N1a" else (r["mix"]["final"] > base["final"]))
        else:
            assert name == "E11", name
            want = dict(G1=r["mix"]["final"] > base["final"], G2=st["dd"] <= base["max_dd_pct"] + 2.0, G3=st["r22"] > 0)
        # G5 (control) re-applied from the stored control lists with a plain median
        ctl = {"E1a": ("control_finals", lambda: r["mix"]["final"], ">"), "E2": ("control_short_pf", lambda: r["short"]["pf"] or 0, ">"),
               "E4": ("control_dd", lambda: st["dd"], "<"), "N1a": ("control_long_pf", lambda: r["long"]["pf"] or 0, ">"),
               "N1b": ("control_long_pf", lambda: r["long"]["pf"] or 0, ">")}.get(name)
        if ctl:
            src = res[name] if ctl[0] in res[name] else r
            vals = sorted(x for x in src[ctl[0]] if x is not None)
            assert len(vals) == 10, (name, len(vals))
            m = (vals[4] + vals[5]) / 2
            want["G5"] = ctl[1]() > m if ctl[2] == ">" else ctl[1]() < m
        elif name == "E1b":
            want["G5"] = "n/a (CODE_CHANGES 1a)"
        assert all(g[k] == v for k, v in want.items()), (name, g, want)
        dec = "PASS" if all(v is True or v == "n/a (CODE_CHANGES 1a)" for k, v in g.items() if k != "decision") else "FAIL"
        assert set(g) - {"decision"} == set(want) and g["decision"] == dec, (name, g, want, dec)
    if exp == "E3":
        tr = pd.concat([pd.read_csv(R.F7R.OUT / f"trades_MAIN_{k}_AI_RS.csv") for k in R.SLEEVES])
        f7s = sum(x.pnl for x in tr.itertuples() if x.side == "short") / 3
        cl = sorted(res["E3c_short_pnl_mix"])
        assert len(cl) == 10 and abs((cl[4] + cl[5]) / 2 - res["E3c_median"]) < 1e-6 and abs(f7s - res["F7_short_pnl_mix"]) < 0.01
        b_short = sum(x.pnl for x in entries("E3b_AGE", "short").itertuples()) / 3
        assert abs(b_short - res["E3b"]["short"]["pnl_mix"]) < 0.01, (b_short, res["E3b"]["short"])
        rd = ("AI short skill not shown beyond listing age" if (b_short >= 0.8 * f7s or res["E3c_median"] >= 0.8 * f7s)
              else "AI short adds beyond listing age")
        assert rd == res["reading"], (rd, res["reading"])
        print(f"[V2 PASS] E3: F7 short P&L {f7s:.2f}, E3b short P&L {b_short:.2f} and E3c median re-derived; reading rule re-applied")
    print(f"[V2 PASS] {exp}: statistics re-derived with plain loops from the equity / trade / short-P&L files; gates re-applied")

    rng = np.random.default_rng(11)
    if exp == "E2":
        D = pd.read_csv(R.OUT / "decisions_E2.csv", parse_dates=["t"])
        okmap = {(r.sleeve, r.t, r.symbol): r.ok for r in D.itertuples()}
        e = entries("E2", "short")
        for x in e.itertuples():
            assert okmap.get((x.sleeve, decision_time(x.sleeve, x.entry_time), x.symbol)) is True, (x.sleeve, x.entry_time, x.symbol)
        for r in D.sample(40, random_state=3).itertuples():
            fm, ag = fund9_plain(r.symbol, r.t), (r.t.normalize() + DAY - perp_first(r.symbol)) / DAY
            q = qv30_plain(r.symbol, r.t.normalize())
            assert (math.isnan(fm) and math.isnan(r.fund_mean9)) or abs(fm - r.fund_mean9) < 1e-12, (r.symbol, r.t)
            assert abs(ag - r.age) < 1e-9 and ((math.isnan(q) and math.isnan(r.qv30)) or abs(q - r.qv30) < 1e-6 * max(1, q))
            ok = (not math.isnan(fm) and fm >= -0.0003) and ag >= 60 and (not math.isnan(q) and q >= 0.25 * r.qv30_median)
            assert ok == r.ok, (r.symbol, r.t, ok, r.ok)
        print(f"[V3 PASS] E2: {len(e)} short entries all passed the filter; 40 decision rows re-derived from raw files")
    if exp == "N1":
        for tag in ("N1a", "N1b"):
            D = pd.read_csv(R.OUT / f"decisions_{tag}.csv", parse_dates=["t"])
            bl = {(r.sleeve, r.t, r.symbol) for r in D.itertuples() if r.blocked}
            e = entries(tag, "long")
            bad = [x for x in e.itertuples() if (x.sleeve, decision_time(x.sleeve, x.entry_time), x.symbol) in bl]
            assert not bad, bad[:3]
            for (sl, t), g in list(D.groupby(["sleeve", "t"]))[::997][:10]:
                pct = g.max7.rank(pct=True)
                assert ((pct > 0.80) == g.blocked).all(), (sl, t)
            for r in D.dropna(subset=["max7"]).sample(40, random_state=4).itertuples():
                rr = daily_ret_plain(r.symbol, r.t.normalize(), 7)
                assert rr is not None and abs(max(rr) - r.max7) < 1e-12, (r.symbol, r.t)
            print(f"[V3 PASS] {tag}: no blocked coin was newly bought ({len(e)} longs); blocked == pct > 0.8; MAX7 re-derived for 40 rows")
    if exp == "E4":
        D = pd.read_csv(R.OUT / "decisions_E4.csv", parse_dates=["t"])
        for _, g in D.groupby(["sleeve", "t", "side"]):
            assert abs(g.w.sum() - min(1.0, 0.30 * len(g))) < 1e-9 and (g.w <= 0.30 + 1e-9).all(), (g.sleeve.iloc[0], g.t.iloc[0], list(g.w))
        n_eq, n_short_hist = 0, 0
        for r in D[D.side == "long"].sample(60, random_state=5).itertuples():
            rets = daily_ret_plain(r.symbol, r.t.normalize(), 60)
            if rets is None:                                      # < 60 returns: replaced by the set median (CODE_CHANGES 1b)
                n_short_hist += 1
                continue
            m = sum(rets) / 60
            sd = (sum((x - m) ** 2 for x in rets) / 59) ** 0.5
            assert abs(sd - r.sigma) < 1e-10, (r.symbol, r.t, sd, r.sigma)
            n_eq += 1
        assert n_eq >= 30, n_eq
        # weights re-derived from the logged sigmas with an independent capped inverse-vol loop
        for _, g in list(D.groupby(["sleeve", "t", "side"]))[::503][:20]:
            inv = [1 / x for x in g.sigma]
            w = [x / sum(inv) for x in inv]
            for _ in range(50):                                   # cap 30 %, excess to uncapped pro rata; all capped -> rest is cash
                over = [x > 0.30 + 1e-12 for x in w]
                if not any(over):
                    break
                ex = sum(x - 0.30 for x, o in zip(w, over) if o)
                fr = sum(x for x, o in zip(w, over) if not o and x < 0.30)
                w = [0.30 if o else (x + ex * x / fr if (fr > 0 and x < 0.30) else x) for x, o in zip(w, over)]
            assert np.allclose(w, g.w.values, atol=1e-9), (g.w.values, w)
        print(f"[V3 PASS] E4: weights sum to min(1, 0.3 n) and are <= 30 %; sigma60 re-derived for {n_eq} rows ({n_short_hist} rows had < 60 days); "
              f"20 weight sets re-derived from the sigmas")
    if exp == "E1":
        ph = pd.read_csv(FUM / "BTCUSDT_perp_1h.csv.gz", parse_dates=["timestamp"]).set_index("timestamp")
        for tag in ("E1a", "E1b"):
            h = entries(tag, "hedge")
            st = h[h.reason == "stop"]
            for x in st.sample(min(30, len(st)), random_state=6).itertuples() if len(st) else []:
                L = {"D1": DAY, "H4": pd.Timedelta(hours=4), "H1": pd.Timedelta(hours=1)}[x.sleeve]
                w = ph[(ph.index >= x.exit_time) & (ph.index < x.exit_time + L)]
                o, hi, sp = float(w.open.iloc[0]), float(w.high.max()), x.entry_px * 1.5
                fill = o * 1.01 if o >= sp else sp * 1.01
                assert hi >= sp and abs(fill - x.exit_px) < 1e-9 * fill, (tag, x.exit_time, o, hi, sp, x.exit_px)
            print(f"[V3 PASS] {tag}: {len(h)} hedge trades; {min(30, len(st))} hedge stop fills re-derived from raw BTC perp bars")
    if exp == "E11":
        e = entries("E11", "long")
        pl = e[e.venue == "perp"]
        for x in pl.sample(min(30, len(pl)), random_state=7).itertuples():
            ph = pd.read_csv(FUM / f"{x.symbol}_perp_1h.csv.gz", parse_dates=["timestamp"]).set_index("timestamp")
            o = float(ph.open.loc[x.entry_time]) / scale(x.symbol)
            assert abs(o - x.entry_px) < 1e-9 * o, (x.symbol, x.entry_time, o, x.entry_px)
        print(f"[V3 PASS] E11: {len(pl)} perp longs, {len(e) - len(pl)} spot longs; 30 perp-long entry prices = raw perp opens")
    if exp == "E3":
        tr = pd.concat([pd.read_csv(R.F7R.OUT / f"trades_MAIN_{k}_AI_RS.csv", parse_dates=["entry_time"]).assign(sleeve=k) for k in R.SLEEVES])
        sh = tr[tr.side == "short"]
        firsts, b = {}, {}
        for x in sh.itertuples():
            if x.symbol not in firsts:
                firsts[x.symbol] = perp_first(x.symbol)
            a = (x.entry_time.normalize() - firsts[x.symbol]) / DAY            # = (decision day + 1 day) - first bar
            k = 0 if a < 60 else 1 if a < 180 else 2 if a < 365 else 3
            b[k] = b.get(k, 0.0) + x.pnl
        tot = sum(b.values())
        for k, v in res["E3a_buckets_lt60_60_180_180_365_ge365"].items():
            assert abs(b[int(float(k))] / tot - v["pnl_share"]) < 0.001, (k, b, v)
        print(f"[V3 PASS] E3: listing-age bucket P&L shares re-derived from the F7 trades with a plain age computation")


if __name__ == "__main__":
    main(sys.argv[1])
