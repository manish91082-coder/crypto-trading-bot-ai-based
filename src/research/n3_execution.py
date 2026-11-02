"""N3 (trial T17): execution layer on the base portfolio. Protocol logs/research_n3_execution/N3_PROTOCOL_PREREGISTERED.md.
X1 maker entry (strict trade-through on 5m, fallback taker at the 12th bar close), X1s stress (>= 0.05% through),
X2 spot/perp routing for longs (PIT trailing funding x PIT median hold), X3 funding-guard count.
Reuses the N1 simulator (and the N2 regime hook when the base includes a regime). Historical simulation only."""
import hashlib
import heapq
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n1_portfolio as N
import n2_regime as Q

OUT = N.ROOT / "logs" / "research_n3_execution"
MAKER, SEED, THR = 0.00018, 20261026, 0.00062
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def maker_fills(L, through=0.0):
    """per A/B/C trade: filled?, fill price, entry fee. Window = the 12 five-minute bars starting at entry_time."""
    filled = np.zeros(len(L), bool); px = L.entry.values.copy(); first = np.full(len(L), np.nan)
    for coin, idx in L.groupby("coin").indices.items():
        d = pd.read_csv(N.M.HF / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"], parse_dates=["timestamp"]).sort_values("timestamp")
        ts = d.timestamp.values; lo, hi, cl, op = d.low.values, d.high.values, d.close.values, d.open.values
        et = L.entry_time.values[idx].astype("datetime64[ns]")
        i0 = np.searchsorted(ts, et, side="left")
        i1 = np.searchsorted(ts, et + np.timedelta64(60, "m"), side="left")
        for k, j in enumerate(idx):
            a, b = i0[k], min(i1[k], i0[k] + 12)
            lim = L.entry.values[j]
            first[j] = op[a]
            s = L.side.values[j]
            if s == 1:
                f = (lo[a:b] < lim * (1 - through)).any() if through else (lo[a:b] < lim).any()
            else:
                f = (hi[a:b] > lim * (1 + through)).any() if through else (hi[a:b] > lim).any()
            filled[j] = f
            px[j] = lim if f else cl[b - 1]
    return filled, px, first


def route(L, C):
    """X2: spot for A/B longs when trailing-7d mean funding x (PIT median hold hours / 8) > THR."""
    spot = np.zeros(len(L), bool)
    tr7 = np.full(len(L), np.nan); kh = np.full(len(L), np.nan)
    ab = L.sleeve.isin(["A", "B"]).values
    fcache = {}
    for coin, idx in L[ab].groupby("coin").indices.items():
        f = N.read_funding(coin)
        fcache[coin] = f
    sub = L[ab]
    pos = np.flatnonzero(ab)
    for j, coin, t in zip(pos, sub.coin.values, sub.entry_time.values.astype("datetime64[ns]")):
        ft, r = fcache[coin]
        a, b = np.searchsorted(ft, t - np.timedelta64(7, "D"), side="left"), np.searchsorted(ft, t, side="left")
        tr7[j] = r[a:b].mean() if b > a else np.nan
    grid = N_GRID[0]
    exit_t = grid[np.minimum(L.E.values, len(grid) - 1)]
    hold_h = (L.E.values - L.a.values).astype(float)
    for (sl, tf), idx in L[ab].groupby(["sleeve", "tf"]).indices.items():
        ii = pos[idx]
        ent = L.entry_time.values[ii].astype("datetime64[ns]"); ex = exit_t[ii].values.astype("datetime64[ns]")
        order_e = np.argsort(ent, kind="mergesort"); order_x = np.argsort(ex, kind="mergesort")
        lo, hi = [], []                     # running median: max-heap lo, min-heap hi
        p = 0
        for k in order_e:
            while p < len(order_x) and ex[order_x[p]] < ent[k]:
                v = hold_h[ii[order_x[p]]]
                if lo and v > -lo[0]:
                    heapq.heappush(hi, v)
                else:
                    heapq.heappush(lo, -v)
                if len(lo) > len(hi) + 1:
                    heapq.heappush(hi, -heapq.heappop(lo))
                elif len(hi) > len(lo):
                    heapq.heappush(lo, -heapq.heappop(hi))
                p += 1
            n = len(lo) + len(hi)
            if n >= 30:
                kh[ii[k]] = (-lo[0] if n % 2 else (-lo[0] + hi[0]) / 2) / 8.0
    spot = ab & np.isfinite(tr7) & np.isfinite(kh) & (tr7 * kh > THR)
    return spot, tr7, kh


N_GRID = [None]


def x3_flags(L):
    """per trade: funding guard trigger (next funding within 15 min after entry, last rate adverse > 0.02%) and that next rate."""
    flag = np.zeros(len(L), bool); rate = np.zeros(len(L))
    for coin, idx in L[L.sleeve.isin(["A", "B", "C"])].groupby("coin").indices.items():
        f = N.read_funding(coin)
        if f is None:
            continue
        ft, r = f
        et = L.entry_time.values[idx].astype("datetime64[ns]")
        k = np.searchsorted(ft, et, side="right")
        ok = k < len(ft)
        nxt = ft[np.minimum(k, len(ft) - 1)]
        last = np.where(k - 1 >= 0, r[np.maximum(k - 1, 0)], 0.0)
        fl = ok & ((nxt - et) < np.timedelta64(15, "m")) & (L.side.values[idx] * last > 0.0002)
        flag[idx] = fl
        rate[idx] = np.where(fl, r[np.minimum(k, len(ft) - 1)], 0.0)
    return flag, rate


def x3_count(L, C):
    n = 0
    for coin, idx in L[L.sleeve.isin(["A", "B", "C"])].groupby("coin").indices.items():
        f = N.read_funding(coin)
        if f is None:
            continue
        ft, r = f
        et = L.entry_time.values[idx].astype("datetime64[ns]")
        k = np.searchsorted(ft, et, side="right")                # next funding strictly after entry
        ok = k < len(ft)
        nxt = np.where(ok, ft[np.minimum(k, len(ft) - 1)], np.datetime64("NaT"))
        within = ok & ((nxt - et) < np.timedelta64(15, "m"))
        last = np.where(k - 1 >= 0, r[np.maximum(k - 1, 0)], 0.0)
        adverse = L.side.values[idx] * last > 0.0002
        n += int((within & adverse).sum())
    return n


class Ctx:
    pass


def setup():
    """base config (N1 FINAL + N2 regime if chosen), world, ledgers, maker fills, routing decisions."""
    x = Ctx()
    n1 = json.loads((N.OUT / "claims_n1.json").read_text())
    n2 = json.loads((Q.OUT / "claims_n2.json").read_text())
    x.n1, x.n2 = n1, n2
    x.report_only = n1["verdict"] != "N1 PASS"
    x.base_cfg = n1["final_cfg"] if not x.report_only else {}
    x.gname = n2["chosen"] if (not x.report_only and n2["verdict"].startswith("N2 PASS")) else None
    x.g = None
    if x.gname:
        st = pd.read_csv(Q.OUT / "N2_states.csv", header=[0, 1], index_col=0, parse_dates=True)
        x.g = st[x.gname]
    Wd = N.load_world()
    N_GRID[0] = Wd.grid
    Wd.led_nostop = {s: N.sim(Wd.T[s], Wd.C, stop=False) for s in "ABC"}
    Wd.led_stop = {s: N.sim(Wd.T[s], Wd.C, stop=True) for s in "ABC"}
    Wd.D, Wd.Dcost, _ = N.build_D(Wd.dc, Wd.C)
    x.Wd = Wd
    led0 = Wd.led_stop if x.base_cfg.get("stop", True) else Wd.led_nostop
    x.allL = pd.concat([led0[s] for s in "ABC"], ignore_index=True)
    x.fil, x.px, first = maker_fills(x.allL)
    x.fil_s, x.px_s, _ = maker_fills(x.allL, through=0.0005)
    assert np.allclose(first, x.allL.entry.values, rtol=0, atol=0), "TF open != first 5m open"
    x.spot, x.tr7, x.kh = route(x.allL, Wd.C)
    x.x3flag, x.x3rate = x3_flags(x.allL)
    return x


def variant(x, maker=None, routing=False, keep=None, guard=False):
    """A/B/C ledgers with the execution options; keep = optional bool mask over x.allL (False = trade skipped)."""
    out = {}
    for s in "ABC":
        m = (x.allL.sleeve == s).values
        Ls = x.allL[m].copy()
        reb = np.zeros(len(Ls))
        if maker is not None:
            f, p = maker[0][m], maker[1][m]
            Ls["entry"] = p
            reb = np.where(f, N.FEE - MAKER, 0.0)
        if routing:
            sp = x.spot[m]
            Ls.loc[Ls.index[sp], "fee"] = N.FEE_SPOT; Ls.loc[Ls.index[sp], "nofund"] = True
            reb = np.where(sp, 0.0, reb)                     # spot-routed trades: spot taker fee, no maker
        Ls["_reb"] = reb
        # X3 (CODE_CHANGES 1): entry delayed to just after the next funding f -> that funding is not paid (rebate side x rate x w)
        Ls["_freb"] = np.where(x.x3flag[m] & ~Ls.nofund.values.astype(bool), x.allL.side.values[m] * x.x3rate[m], 0.0) if guard else 0.0
        if keep is not None:
            Ls = Ls[keep[m]]
        out[s] = Ls.reset_index(drop=True)
    return out


def runv(x, led, t0, t1, want=False):
    Wd = x.Wd
    Q.CUR["g"] = x.g
    try:
        L = N.assemble(Wd, x.base_cfg, led, Wd.D, t0, t1)
        reb = L["_reb"].fillna(0.0).values * L.w.values
        frb = L["_freb"].fillna(0.0).values * L.w.values if "_freb" in L else np.zeros(len(L))
        extra = pd.concat([pd.DataFrame(dict(a=L.a.values[reb > 0], cost=-reb[reb > 0])),
                           pd.DataFrame(dict(a=np.minimum(L.a.values[frb != 0] + 1, len(Wd.grid) - 1), cost=-frb[frb != 0]))], ignore_index=True)
        costs = pd.concat([Wd.Dcost[["a", "cost"]], extra], ignore_index=True) if not x.base_cfg.get("noD") else extra
        h0, h1 = Wd.grid.get_loc(pd.Timestamp(t0)), Wd.grid.get_loc(pd.Timestamp(t1))
        r = N.run_pf(L, Wd.C, Wd.grid, h0, h1, costs=costs, want=want)
        r["n_trades"] = int((L.w > 0).sum())
        if want:
            r["L"] = L
        return r
    finally:
        Q.CUR["g"] = None


def main():
    proto = OUT / "N3_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "N3_PROTOCOL_SHA256.txt").read_text().split()[0], "N3 protocol changed"
    x = setup()
    n1, report_only, base_cfg, gname, Wd, allL = x.n1, x.report_only, x.base_cfg, x.gname, x.Wd, x.allL
    fil, px, fil_s, px_s, spot, tr7, kh = x.fil, x.px, x.fil_s, x.px_s, x.spot, x.tr7, x.kh
    log("base", base_cfg, "regime", gname, "report_only", report_only)
    nx3 = x3_count(allL, Wd.C)
    log("fills", round(fil.mean(), 4), "stress fills", round(fil_s.mean(), 4), "spot share (A/B)", round(spot[allL.sleeve.isin(['A', 'B']).values].mean(), 4), "X3 count", nx3)
    V = {"base": variant(x), "X1": variant(x, (fil, px)), "X1s": variant(x, (fil_s, px_s)), "X2": variant(x, routing=True)}
    if nx3 > 0:
        V["X3"] = variant(x, guard=True)
    rows, cal, monthly = [], {}, {}
    for name, led in V.items():
        for wn, (t0, t1) in N.WIN.items():
            r = runv(x, led, t0, t1, want=(wn == "dev"))
            cal[(name, wn)] = r["calmar"]
            if wn == "dev":
                monthly[name] = r.pop("monthly"); r.pop("curve"); r.pop("Em"); r.pop("L")
            rows.append(dict(variant=name, window=wn, **r))
        log(name, {wn: round(cal[(name, wn)], 3) for wn in N.WIN})
    # shortfall (X1) on dev entries
    side = allL.side.values
    sf = side * (px - allL.entry.values) / allL.entry.values            # positive = worse than the TF open
    fee_used = np.where(fil, MAKER, N.FEE)
    short = sf + fee_used - N.FEE
    dev = (allL.entry_time >= pd.Timestamp(N.WIN["dev"][0])) & (allL.entry_time < pd.Timestamp(N.WIN["dev"][1]))
    sd = pd.Series(short[dev.values], index=allL.entry_time[dev].dt.to_period("M").astype(str).values)
    mon = sd.groupby(level=0).agg(["sum", "count"])
    rng = np.random.default_rng(SEED)
    Wm = rng.multinomial(len(mon), np.full(len(mon), 1 / len(mon)), size=2000)
    bm = (Wm @ mon["sum"].values) / (Wm @ mon["count"].values)
    ci = (float(np.quantile(bm, .025)), float(np.quantile(bm, .975)))
    netR = allL.gross.values - 2 * N.FEE - allL.fsum.values
    F = pd.DataFrame(dict(sleeve=allL.sleeve, coin=allL.coin, tf=allL.tf, fam=allL.fam, side=side, entry_time=allL.entry_time,
                          exit_time=Wd.grid[np.minimum(allL.E.values, len(Wd.grid) - 1)], hold_h=(allL.E - allL.a).values, limit=allL.entry, filled=fil,
                          fill_px=px, filled_stress=fil_s, fill_px_stress=px_s, shortfall=short, base_net=netR, spot=spot, trailing7=tr7, k_hold=kh))
    F.to_parquet(OUT / "N3_fills.parquet", index=False)
    adv = dict(net_filled=float(netR[dev.values & fil].mean()), net_unfilled=float(netR[dev.values & ~fil].mean()),
               fill_rate=float(fil[dev.values].mean()), fill_rate_stress=float(fil_s[dev.values].mean()),
               shortfall_mean=float(sd.mean()), shortfall_ci=ci)
    ab = allL.sleeve.isin(["A", "B"]).values & dev.values
    routing = dict(spot_share=float(spot[ab].mean()), funding_saved_sum=float(allL.fsum.values[ab & spot].sum()),
                   n_spot=int((ab & spot).sum()))
    pd.DataFrame([routing]).to_csv(OUT / "N3_routing.csv", index=False)
    Mx1 = pd.read_csv(N.OUT / "N1_monthly_dev.csv", index_col=0)
    Mx2 = pd.read_csv(Q.OUT / "N2_monthly_dev.csv", index_col=0)
    Mx = pd.DataFrame(monthly); Mx.index = Mx.index.astype(str); Mx.to_csv(OUT / "N3_monthly_dev.csv")
    ncfg = 3 + (1 if nx3 > 0 else 0)
    srs = [Mx1[k].mean() / Mx1[k].std(ddof=1) for k in Mx1.columns] + [Mx2[k].mean() / Mx2[k].std(ddof=1) for k in ("R1", "R2")] + \
          [Mx[k].mean() / Mx[k].std(ddof=1) for k in ("X1", "X1s", "X2", "X3") if k in Mx]
    sr_var = float(np.var(srs, ddof=1))
    n_tr = 14 + 5 + n1["n_configs"] + 2 + ncfg
    res = {}
    for name in [k for k in ("X1", "X1s", "X2", "X3") if k in V]:
        dsr_v, sr, sr0 = N.dsr(pd.Series(Mx[name].values), sr_var, n_tr)
        q = {"Q1_dev": cal[(name, "dev")] > cal[("base", "dev")], "Q2_P1_P2": cal[(name, "P1")] > cal[("base", "P1")] and cal[(name, "P2")] > cal[("base", "P2")],
             "Q4_DSR>=0.95": dsr_v >= 0.95}
        if name == "X1":
            q["Q3_shortfall_ci_hi<0"] = ci[1] < 0
        res[name] = dict(gates=q, dsr=dsr_v, passed=all(q.values()))
    x1_ok = res["X1"]["passed"] and res["X1s"]["gates"]["Q1_dev"] and res["X1s"]["gates"]["Q2_P1_P2"]
    adopted = [k for k, ok in (("X1", x1_ok), ("X2", res["X2"]["passed"]), ("X3", res.get("X3", {}).get("passed", False))) if ok]
    combo = None
    if len(adopted) >= 2:                                  # CODE_CHANGES 1: the X1+X2 combination rule extended to every passing variant
        led = variant(x, (fil, px) if "X1" in adopted else None, routing="X2" in adopted, guard="X3" in adopted)
        combo = {wn: runv(x, led, *N.WIN[wn])["calmar"] for wn in N.WIN}
        if not (combo["dev"] > cal[("base", "dev")] and combo["P1"] > cal[("base", "P1")] and combo["P2"] > cal[("base", "P2")]):
            adopted = [max(adopted, key=lambda k: cal[(k, "dev")])]
    verdict = "N3 report only (N1 failed)" if report_only else (f"N3 PASS (provisional, historical fills): {'+'.join(adopted)}" if adopted else "N3 FAIL")
    pd.DataFrame(rows).to_csv(OUT / "N3_results.csv", index=False)
    claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), base_cfg=base_cfg, regime=gname, report_only=report_only,
                  calmar={f"{k[0]}|{k[1]}": v for k, v in cal.items()}, adverse_selection=adv, routing=routing, x3_count=nx3, results=res,
                  x1_stress_ok=x1_ok, combo=combo, adopted=adopted, verdict=verdict, n_trials_dsr=n_tr,
                  files={f.name: sha(f) for f in sorted(OUT.glob("N3_*")) if f.is_file()})
    (OUT / "claims_n3.json").write_text(json.dumps(claims, indent=1, default=float))
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        log(pd.DataFrame(rows).round(4).to_string())
    log(json.dumps({k: v for k, v in claims.items() if k != "files"}, indent=1, default=float))
    (OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
