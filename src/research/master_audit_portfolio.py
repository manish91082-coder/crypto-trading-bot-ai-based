"""Master audit Part B: real funding, portfolio grids, loss rules, cost levers, profit descriptives.

Protocol: logs/research_master_audit/MASTER_AUDIT_PROTOCOL_PREREGISTERED.md (SHA in PROTOCOL_SHA256.txt).
Research only: no orders, no training, archive/ not used.
"""
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "research_master_audit"
TRADES = ROOT / "logs" / "research_probe_scalein" / "trades.parquet"
FUND_DIR = ROOT / "data" / "futures_um"
TF_H = {"1h": 1.0, "4h": 4.0, "1D": 24.0}
TF_ORDER = {"1D": 0, "4h": 1, "1h": 2}
SIDE_FEE, FUND_ASSUMED = 0.00045, 0.0001
START_EQ, LEV_CAP, YEARS = 8000.0, 3.0, None
MIN_NOT = {"BTCUSDT": 50.0, "ETHUSDT": 20.0, "LINKUSDT": 20.0}
P_EDGES = [("P1", "2020-02-01", "2024-01-01"), ("P2", "2024-01-01", "2025-10-01"), ("P3", "2025-10-01", "2026-10-01")]
T0, T1 = pd.Timestamp("2020-02-01"), pd.Timestamp("2026-10-01")
YEARS = (T1 - T0).days / 365.25


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_funding(coins):
    f = {}
    for c in coins:
        d = pd.read_csv(FUND_DIR / f"{c}_funding.csv")
        d["time"] = pd.to_datetime(d["time"])
        d = d.sort_values("time")
        f[c] = (d["time"].values.astype("datetime64[us]"), d["funding_rate"].values.astype("float64"))
    return f


def fund_R(fund, coin, side, fills, entry_time, exit_idx, tf, R):
    """Real funding paid in R units (positive = cost)."""
    t, r = fund[coin]
    bar = np.timedelta64(int(TF_H[tf] * 3600), "s")
    end = np.datetime64(entry_time) + (exit_idx + 1) * bar
    sign = 1.0 if side == "long" else -1.0
    tot = 0.0
    for u, px, i in fills:
        st = np.datetime64(entry_time) + int(i) * bar
        lo, hi = np.searchsorted(t, st, "right"), np.searchsorted(t, end, "left")
        tot += u * sign * px * r[lo:hi].sum() / R
    return tot


def assumed_R(fills, exit_idx, tf, R):
    return sum(u * FUND_ASSUMED * abs(px) * (exit_idx - i + 1) * TF_H[tf] / 8 for u, px, i in fills) / R


def fee_R(fills, exit_px, R, e_fee, x_fee):
    return sum(u * (e_fee * abs(px) + x_fee * abs(exit_px)) for u, px, i in fills) / R


def prepare():
    t = pd.read_parquet(TRADES)
    t = t[t.tf.isin(list(TF_H))].reset_index(drop=True)
    fund = load_funding(sorted(t.coin.unique()))
    first = {c: pd.Timestamp(fund[c][0][0]) for c in fund}
    t["perp_ok"] = [et >= first[c] for et, c in zip(t.entry_time, t.coin)]
    for v in ("V0", "V2"):
        fl = [ast.literal_eval(s) for s in t[f"{v}_fills"]]
        t[f"{v}_fundA"] = [assumed_R(f, x, tf, R) for f, x, tf, R in zip(fl, t.exit_idx, t.tf, t.R_price)]
        t[f"{v}_fundR"] = [fund_R(fund, c, s, f, et, x, tf, R) for c, s, f, et, x, tf, R in
                           zip(t.coin, t.side, fl, t.entry_time, t.exit_idx, t.tf, t.R_price)]
        fee = np.array([fee_R(f, xp, R, SIDE_FEE, SIDE_FEE) for f, xp, R in zip(fl, t.exit_px, t.R_price)])
        chk = np.abs(fee + t[f"{v}_fundA"] - t[f"{v}_base_cost"]).max()
        assert chk < 1e-9, (v, chk)
        t[f"{v}_fee"] = fee
        t[f"{v}_real"] = t[f"{v}_base"] + t[f"{v}_fundA"] - t[f"{v}_fundR"]
        for name, e, x in (("maker", 0.00018, 0.00045), ("faq", 0.00054, 0.00054), ("nobnb", 0.00049, 0.00049),
                           ("x15", 0.000675, 0.000675)):
            fee2 = np.array([fee_R(f, xp, R, e, x) for f, xp, R in zip(fl, t.exit_px, t.R_price)])
            t[f"{v}_{name}"] = t[f"{v}_gross"] - fee2 - t[f"{v}_fundR"]
        if v == "V0":
            fee_s = np.array([fee_R(f, xp, R, 0.00085, 0.00085) for f, xp, R in zip(fl, t.exit_px, t.R_price)])
            t["V0_spot_real"] = t["V0_gross"] - fee_s
    bar_s = t.tf.map(lambda x: int(TF_H[x] * 3600))
    t["end_time"] = t.entry_time + pd.to_timedelta((t.exit_idx + 1) * bar_s, unit="s")
    t["R_pct"] = t.R_price / t.entry_px
    return t, fund, first


def period_stats(eq_t, eq_v):
    out = {}
    s = pd.Series(eq_v, index=pd.DatetimeIndex(eq_t))
    for name, a, b in P_EDGES:
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        before = s[s.index < a]
        start = before.iloc[-1] if len(before) else START_EQ
        seg = pd.concat([pd.Series([start], index=[a]), s[(s.index >= a) & (s.index < b)]])
        yrs = (b - a).days / 365.25
        ret = seg.iloc[-1] / start - 1
        dd = float((1 - seg / seg.cummax()).max())
        cagr = (seg.iloc[-1] / start) ** (1 / yrs) - 1
        out[name] = dict(ret=ret, maxdd=dd, calmar=cagr / dd if dd > 0 else np.nan)
    return out


def simulate(t, tfs, sides=("long", "short"), variant="V0", col="real", f=0.005, K=None,
             dd_derisk=False, streak_pause=False, dir_cap=None, pauses=None):
    d = t[t.tf.isin(tfs) & t.side.isin(sides) & t.perp_ok].copy()
    d["o"] = d.tf.map(TF_ORDER)
    d = d.sort_values(["entry_time", "o", "coin"])
    netc = f"{variant}_{col}"
    E, peak = START_EQ, START_EQ
    opn = []  # (end, coin, tf, side, N, pnl)
    eq_t, eq_v = [T0], [START_EQ]
    skips = dict(same_tf=0, opposite=0, K=0, lev=0, min_not=0, paused=0, dir_cap=0)
    taken, wins, streak, maxstreak, maxlev, pause_until = 0, 0, 0, 0, 0.0, pd.Timestamp.min
    nots, n_pauses, mon = [], 0, {}
    pauses = sorted(pauses) if pauses is not None else None

    def close_until(ts):
        nonlocal E, peak, streak, maxstreak, wins, pause_until, n_pauses
        opn.sort(key=lambda x: x[0])
        while opn and opn[0][0] <= ts:
            end, c, tf_, s_, N, pnl = opn.pop(0)
            E += pnl
            peak = max(peak, E)
            eq_t.append(end); eq_v.append(E)
            m = end.strftime("%Y-%m")
            mon[m] = mon.get(m, 0.0) + pnl
            if pnl > 0:
                wins += 1; streak = 0
            else:
                streak += 1; maxstreak = max(maxstreak, streak)
                if streak_pause and streak >= 4:
                    pause_until = end + pd.Timedelta(hours=24); n_pauses += 1; streak = 0

    for r in d.itertuples(index=False):
        close_until(r.entry_time)
        if r.entry_time < pause_until or (pauses is not None and any(p <= r.entry_time < p + pd.Timedelta(hours=24) for p in pauses)):
            skips["paused"] += 1; continue
        if any(o[1] == r.coin and o[2] == r.tf for o in opn):
            skips["same_tf"] += 1; continue
        if any(o[1] == r.coin and o[3] != r.side for o in opn):
            skips["opposite"] += 1; continue
        if K is not None and len(opn) >= K:
            skips["K"] += 1; continue
        if dir_cap is not None and sum(o[3] == r.side for o in opn) >= dir_cap:
            skips["dir_cap"] += 1; continue
        ff = f / 2 if (dd_derisk and E <= 0.9 * peak) else f
        N = ff * E / (r.R_pct + 0.01 + 0.0009)
        if sum(o[4] for o in opn) + N > LEV_CAP * E:
            skips["lev"] += 1; continue
        if N < MIN_NOT.get(r.coin, 5.0) or (r.coin == "BTCUSDT" and N / r.entry_px < 0.001):
            skips["min_not"] += 1; continue
        pnl = N * getattr(r, netc) * r.R_pct
        opn.append((r.end_time, r.coin, r.tf, r.side, N, pnl))
        taken += 1; nots.append(N)
        maxlev = max(maxlev, sum(o[4] for o in opn) / E)
    close_until(pd.Timestamp.max)
    ev = np.array(eq_v)
    dd = float((1 - ev / np.maximum.accumulate(ev)).max())
    cagr = (ev[-1] / START_EQ) ** (1 / YEARS) - 1
    ms = pd.Series(mon)
    eq_month = None
    res = dict(final=ev[-1], cagr=cagr, maxdd=dd, calmar=cagr / dd if dd > 0 else np.nan, taken=taken,
               per_year=taken / YEARS, win_rate=wins / max(taken, 1), worst_month_usdt=float(ms.min()) if len(ms) else 0,
               max_loss_streak=maxstreak, max_lev=maxlev, n_streak_pauses=n_pauses,
               not_med=float(np.median(nots)) if nots else np.nan, not_p95=float(np.percentile(nots, 95)) if nots else np.nan,
               **{f"skip_{k}": v for k, v in skips.items()})
    for p, s in period_stats(eq_t[1:] if len(eq_t) > 1 else eq_t, eq_v[1:] if len(eq_v) > 1 else eq_v).items():
        for k, v in s.items():
            res[f"{p}_{k}"] = v
    res["_eq"] = (eq_t, eq_v)
    return res


def row(name, r):
    return {"run": name, **{k: v for k, v in r.items() if not k.startswith("_")}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t, fund, first = prepare()
    log = [f"protocol_sha {sha(OUT / 'MASTER_AUDIT_PROTOCOL_PREREGISTERED.md')}", f"trades_sha {sha(TRADES)}",
           "fee term reproduces V0/V2 base_cost - assumed funding to < 1e-9: OK"]
    # B1 funding
    b1 = []
    for (tf, side), g in t.groupby(["tf", "side"]):
        gp = g[g.perp_ok]
        b1.append(dict(tf=tf, side=side, n=len(g), no_perp=int((~g.perp_ok).sum()),
                       fund_assumed_R=gp.V0_fundA.mean(), fund_real_R=gp.V0_fundR.mean(),
                       net_assumed_R=gp.V0_base.mean(), net_real_R=gp.V0_real.mean(),
                       net_real_P1=gp[gp.entry_time < "2024-01-01"].V0_real.mean(),
                       net_real_P2=gp[(gp.entry_time >= "2024-01-01") & (gp.entry_time < "2025-10-01")].V0_real.mean(),
                       net_real_P3=gp[gp.entry_time >= "2025-10-01"].V0_real.mean()))
    pd.DataFrame(b1).to_csv(OUT / "B1_real_funding.csv", index=False)
    # G1
    g1 = []
    for f in (0.0025, 0.005, 0.01):
        for K in (3, 6, 10, None):
            g1.append(row(f"4h_f{f}_K{K}", simulate(t, ["4h"], f=f, K=K)))
    pd.DataFrame(g1).to_csv(OUT / "G1_risk_concentration.csv", index=False)
    # G2
    g2 = []
    for name, tfs in (("4h", ["4h"]), ("1h", ["1h"]), ("1D", ["1D"]), ("4h+1h", ["4h", "1h"]), ("4h+1D", ["4h", "1D"]),
                      ("4h+1h+1D", ["4h", "1h", "1D"])):
        g2.append(row(name, simulate(t, tfs, f=0.005, K=10)))
    pd.DataFrame(g2).to_csv(OUT / "G2_trade_max.csv", index=False)
    tp = t[t.perp_ok].copy()
    tp["m"] = tp.end_time.dt.strftime("%Y-%m")
    mm = tp.pivot_table(index="m", columns="tf", values="V0_real", aggfunc="sum").fillna(0)
    mm.corr().to_csv(OUT / "G2_monthly_R_corr.csv")
    # G3
    base = simulate(t, ["4h"], f=0.005, K=6)
    runs = {"baseline": base,
            "L1_dd_derisk": simulate(t, ["4h"], f=0.005, K=6, dd_derisk=True),
            "L2_streak_pause": simulate(t, ["4h"], f=0.005, K=6, streak_pause=True),
            "L3_dir_cap3": simulate(t, ["4h"], f=0.005, K=6, dir_cap=3),
            "L4_V2_test_entry": simulate(t, ["4h"], variant="V2", f=0.005, K=6),
            "L5_long_only": simulate(t, ["4h"], sides=("long",), f=0.005, K=6),
            "R1_cost_x1.5": simulate(t, ["4h"], col="x15", f=0.005, K=6),
            "R2_faq_taker_0.05": simulate(t, ["4h"], col="faq", f=0.005, K=6),
            "R3_no_bnb": simulate(t, ["4h"], col="nobnb", f=0.005, K=6),
            "maker_entry": simulate(t, ["4h"], col="maker", f=0.005, K=6)}
    npz = runs["L2_streak_pause"]["n_streak_pauses"]
    ent = t[(t.tf == "4h") & t.perp_ok].entry_time.values
    rnd = []
    for i in range(50):
        rng = np.random.default_rng(20261018 + i)
        ps = [pd.Timestamp(x) for x in rng.choice(ent, size=npz, replace=False)]
        rnd.append(simulate(t, ["4h"], f=0.005, K=6, pauses=ps)["calmar"])
    rnd_p90 = float(np.percentile(rnd, 90))
    g3 = []
    for name, r in runs.items():
        x = row(name, r)
        if name.startswith("L"):
            full = r["maxdd"] < base["maxdd"] and r["calmar"] > base["calmar"]
            sub = sum(r[f"{p}_maxdd"] < base[f"{p}_maxdd"] and r[f"{p}_calmar"] > base[f"{p}_calmar"] for p in ("P1", "P2", "P3"))
            ok = full and sub >= 2 and (name != "L2_streak_pause" or r["calmar"] > rnd_p90)
            x["verdict"] = "helps" if ok else ("trade-off" if r["maxdd"] < base["maxdd"] else "does not help")
            x["sub_periods_better"] = sub
        g3.append(x)
    g3 = pd.DataFrame(g3)
    g3["random_pause_calmar_p90"] = rnd_p90
    g3.to_csv(OUT / "G3_loss_rules.csv", index=False)
    # B3 cost levers
    b3 = []
    for tf in ("4h", "1D"):
        for side in ("long", "short"):
            g = t[(t.tf == tf) & (t.side == side) & t.perp_ok]
            r = dict(tf=tf, side=side, n=len(g), gross=g.V0_gross.mean(), base=g.V0_real.mean(), maker_entry=g.V0_maker.mean(),
                     faq_taker=g.V0_faq.mean(), no_bnb=g.V0_nobnb.mean(), cost_x1_5=g.V0_x15.mean())
            if side == "long":
                r["spot_long"] = t[(t.tf == tf) & (t.side == side)].V0_spot_real.mean()
            b3.append(r)
    pd.DataFrame(b3).to_csv(OUT / "B3_cost_levers.csv", index=False)
    # B4 profit descriptives
    b4 = []
    for tf in ("4h", "1D"):
        for side in ("long", "short"):
            g = t[(t.tf == tf) & (t.side == side) & t.perp_ok]
            x = g.V0_real.sort_values(ascending=False).values
            pos = x[x > 0].sum()
            ts = g[g.exit_idx == 59]
            st = g[g.exit_idx != 59]
            w, l = g.V0_real[g.V0_real > 0], g.V0_real[g.V0_real <= 0]
            b4.append(dict(tf=tf, side=side, n=len(g), sum_R=x.sum(),
                           top5_share_of_gains=x[:max(1, int(len(x) * .05))].sum() / pos,
                           top10_share_of_gains=x[:max(1, int(len(x) * .10))].sum() / pos,
                           top20_share_of_gains=x[:max(1, int(len(x) * .20))].sum() / pos,
                           sum_R_without_top10pct=x[int(len(x) * .10):].sum(),
                           n_time_stop=len(ts), mean_R_time_stop=ts.V0_real.mean(), share_ts_gross_gt2=(ts.V0_gross > 2).mean(),
                           n_stop=len(st), mean_R_stop=st.V0_real.mean(), win_rate=(g.V0_real > 0).mean(),
                           avg_win_R=w.mean(), avg_loss_R=l.mean(), payoff=w.mean() / -l.mean()))
    pd.DataFrame(b4).to_csv(OUT / "B4_profit_descriptives.csv", index=False)
    claims = {"protocol_sha": sha(OUT / "MASTER_AUDIT_PROTOCOL_PREREGISTERED.md"), "trades_sha": sha(TRADES),
              "funding_sha": {c: sha(FUND_DIR / f"{c}_funding.csv") for c in sorted(t.coin.unique())},
              "G1_f0.005_K6": {k: base[k] for k in ("final", "maxdd", "calmar", "taken")},
              "L1": {k: runs["L1_dd_derisk"][k] for k in ("final", "maxdd", "calmar")},
              "random_pause_calmar_p90": rnd_p90}
    (OUT / "claims_master_audit.json").write_text(json.dumps(claims, indent=1, default=float))
    (OUT / "run_log.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        for n in ("B1_real_funding", "G1_risk_concentration", "G2_trade_max", "G2_monthly_R_corr", "G3_loss_rules",
                  "B3_cost_levers", "B4_profit_descriptives"):
            print("==", n); print(pd.read_csv(OUT / f"{n}.csv").round(4).to_string())


if __name__ == "__main__":
    main()
