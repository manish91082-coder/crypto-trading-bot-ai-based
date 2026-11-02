"""A4 (rule-only): exits, entry variants and sizing for S-LAD long. Protocol logs/r2_4h_a4/A4_PROTOCOL_PREREGISTERED.md
(trials T06-T13). Historical simulation only."""
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_scalein as P
import master_audit_portfolio as MA
import r2_a1_edge_map as A1

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "r2_4h_a4"
A1C = ROOT / "logs" / "r2_4h_a1" / "correction" / "a1c_trades.parquet"
FEE, SEED, NRAND = 0.00054, 20261019, 100
H4 = pd.Timedelta(hours=4)
T0, DEV1, P1END, T1 = pd.Timestamp("2020-02-01"), pd.Timestamp("2025-10-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2026-10-01")
GRID = [(3, 60), (3, 120), (3, 1000), (4, 60), (4, 120), (4, 1000)]
MIN_NOT = {"BTCUSDT": 50.0, "ETHUSDT": 20.0, "LINKUSDT": 20.0}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def exit_sim(O, H, L, C, e, stop0, A, k, tmax):
    n = min(tmax, len(O) - e)
    o, h, l, c = O[e:e + n], H[e:e + n], L[e:e + n], C[e:e + n]
    prevmax = np.concatenate([[-np.inf], np.maximum.accumulate(h)[:-1]])
    trail = np.maximum(stop0, prevmax - k * A)
    hit = np.where(l <= trail)[0]
    if len(hit):
        i = int(hit[0]); return i, float(min(o[i], trail[i])), True, False
    return n - 1, float(c[n - 1]), False, n < tmax


def v2_fills(O, H, e, ex_i, by_stop, E, A):
    """S6 V2 rule: 0.25 at entry, +0.25 at E+1A, +0.5 at E+2A; fill = max(open of trigger bar, level); an add on the stop
    bar (or later) is skipped; with a time exit, adds up to the last bar are allowed (probe_scalein.simulate)."""
    fills = [(0.25, E, 0)]
    for kk, u in ((1.0, 0.25), (2.0, 0.5)):
        lvl = E + kk * A
        trg = np.where(H[e:e + ex_i + 1] >= lvl)[0]
        if not len(trg):
            continue
        ti = int(trg[0])
        if by_stop and ti >= ex_i:
            continue
        fills.append((u, float(max(O[e + ti], lvl)), ti))
    return fills


def costs(fills, ex_px, R, fee_e, fee_x):
    return sum(u * (fe * px + fee_x * ex_px) for (u, px, i), fe in zip(fills, fee_e)) / R


class Data:
    def __init__(self):
        t = pd.read_parquet(A1C)
        t = t[(t.signal == "S-LAD") & (t.side == "long") & t.perp_ok].sort_values(["entry_time", "coin"]).reset_index(drop=True)
        self.t = t
        self.bars = {c: P.bars(c, "4h") for c in t.coin.unique()}
        self.fund = MA.load_funding(sorted(t.coin.unique()))


def trades_for(D, k, tmax, variant="V0", fee=FEE, slip=0.0, maker=None, scale=1.0):
    rows = []
    for r in D.t.itertuples():
        b = D.bars[r.coin]
        O, H, L, C = (b[x].values.astype("float64") for x in ("open", "high", "low", "close"))
        e = b.index.get_loc(r.entry_time)
        stop0 = r.entry_px - r.R_price
        fee = FEE * scale if fee == FEE else fee
        E, fe = float(O[e]), fee
        if maker is not None:
            E, filled = maker[(r.coin, r.entry_time)]
            fe = (0.00018 if filled else FEE) * scale
        R = E - stop0
        if not R > 0:
            rows.append(dict(i=r.Index, skip=True)); continue
        ex_i, ex_px, by_stop, trunc = exit_sim(O, H, L, C, e, stop0, r.atr, k, tmax)
        if by_stop and slip:
            ex_px *= (1 - slip)
        fills = [(1.0, E, 0)] if variant == "V0" else v2_fills(O, H, e, ex_i, by_stop, E, r.atr)
        gross = sum(u * (ex_px - px) for u, px, i in fills) / R
        fee_e = [fe] + [fee] * (len(fills) - 1)
        c_fee = costs(fills, ex_px, R, fee_e, fee)
        fund = MA.fund_R(D.fund, r.coin, "long", fills, r.entry_time, ex_i, "4h", R)
        lows = L[e:e + ex_i + 1].copy()
        units_by_bar = np.zeros(ex_i + 1); pxw = np.zeros(ex_i + 1)
        for u, px, i in fills:
            units_by_bar[i:] += u; pxw[i:] += u * px
        adv = (units_by_bar * lows - pxw) / E
        adv[-1] = (units_by_bar[-1] * ex_px - pxw[-1]) / E
        rows.append(dict(i=r.Index, coin=r.coin, entry_time=r.entry_time, exit_time=r.entry_time + (ex_i + 1) * H4, exit_idx=ex_i,
                         E=E, R=R, gross=gross, fee=c_fee, funding=fund, net=gross - c_fee - fund, by_stop=by_stop, truncated=trunc,
                         units=sum(u for u, _, _ in fills), path=adv, year=r.entry_time.year, skip=False))
    return pd.DataFrame(rows)


def portfolio(T, f=0.005, t0=T0, t1=DEV1):
    d = T[(~T.skip) & (T.entry_time >= t0) & (T.entry_time < t1)].sort_values(["entry_time", "coin"])
    by_t = {}
    for j in d.index:
        by_t.setdefault(d.at[j, "entry_time"], []).append(j)
    E, op, curve, idx = 8000.0, [], [], []
    for t in pd.date_range(t0, t1 - H4, freq="4h"):
        for o in [o for o in op if o["end"] <= t]:
            E += o["pnl"]; op.remove(o)
        for j in by_t.get(t, []):
            r = d.loc[j]
            if any(o["coin"] == r.coin for o in op) or len(op) >= 6:
                continue
            N = f * E / (r.R / r.E + 0.01 + 0.0009)
            if sum(o["N"] for o in op) + N > 3 * E or N < MIN_NOT.get(r.coin, 5.0) or (r.coin == "BTCUSDT" and N / r.E < 0.001):
                continue
            op.append(dict(coin=r.coin, N=N, pnl=N * r.net * r.R / r.E, end=r.exit_time, start=t, path=r.path))
        u = 0.0
        for o in op:
            kbar = int((t - o["start"]) / H4)
            if kbar < len(o["path"]):
                u += o["N"] * o["path"][kbar]
        curve.append(E + u); idx.append(t)
    for o in op:
        E += o["pnl"]
    curve.append(E); idx.append(t1)
    eq = pd.Series(curve, index=idx)
    yrs = (t1 - t0).days / 365.25
    cagr = (eq.iloc[-1] / 8000) ** (1 / yrs) - 1
    dd = float((1 - eq / eq.cummax()).max())
    return dict(final=float(eq.iloc[-1]), cagr=float(cagr), mtm_dd=dd, calmar=float(cagr / dd) if dd > 0 else np.nan,
                monthly=eq.resample("MS").last().pct_change().dropna())


def pbo(M):
    """CSCV on a (months x configs) return matrix, 16 contiguous blocks."""
    blocks = np.array_split(np.arange(len(M)), 16)
    logits = []
    for comb in itertools.combinations(range(16), 8):
        is_ = np.concatenate([blocks[i] for i in comb]); oos = np.concatenate([blocks[i] for i in range(16) if i not in comb])
        sr_is = (M.iloc[is_].mean() / M.iloc[is_].std(ddof=1)).round(12)        # change 3: tie-robust ranking
        sr_oos = (M.iloc[oos].mean() / M.iloc[oos].std(ddof=1)).round(12)
        best = sr_is.idxmax()
        rank = sr_oos.rank(method="average")[best]
        w = rank / (len(M.columns) + 1)
        logits.append(np.log(w / (1 - w)))
    logits = np.array(logits)
    return float((logits < 0).mean()), logits


def dsr(ret, sr_var, n):
    sr = ret.mean() / ret.std(ddof=1)
    g = 0.5772156649
    sr0 = np.sqrt(sr_var) * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e)))
    z = (sr - sr0) * np.sqrt(len(ret) - 1) / np.sqrt(1 - ret.skew() * sr + (ret.kurt() + 2) / 4 * sr ** 2)
    return float(norm.cdf(z)), float(sr), float(sr0)


def maker_fills(D):
    out, rows = {}, []
    for coin, g in D.t.groupby("coin"):
        x = pd.read_csv(ROOT / "data" / "universe_hf" / "5m" / f"{coin}_5m_full.csv.gz", usecols=["timestamp", "open", "low", "close"],
                        parse_dates=["timestamp"]).set_index("timestamp").sort_index()
        for r in g.itertuples():
            w = x.loc[r.entry_time: r.entry_time + pd.Timedelta(minutes=55)]
            lim = float(D.bars[coin].open.loc[r.entry_time])
            filled = bool(len(w) and (w.low.values < lim).any())
            px = lim if filled else float(w.close.values[-1]) if len(w) else lim
            out[(coin, r.entry_time)] = (px, filled)
            rows.append(dict(coin=coin, entry_time=r.entry_time, filled=filled, fill_px=px, limit=lim, n5m=len(w)))
    return out, pd.DataFrame(rows)


def random_entry(D, k, tmax, seed):
    rng = np.random.default_rng(seed)
    rows = []
    for (coin, yr), g in D.t.groupby(["coin", D.t.entry_time.dt.year]):
        b = D.bars[coin]
        O, H, L, C = (b[x].values.astype("float64") for x in ("open", "high", "low", "close"))
        atr = A1.atr14(b)
        ok = np.where((b.index.year == yr) & (np.arange(len(b)) + 60 <= len(b)) & (b.index >= T0) & (b.index < T1))[0]
        ok = ok[ok >= 1]
        ok = ok[np.isfinite(atr[ok - 1])]
        for e in rng.choice(ok, size=min(len(g), len(ok)), replace=False):
            A = atr[e - 1]; E = float(O[e]); stop0 = E - 2 * A
            ex_i, ex_px, _, _ = exit_sim(O, H, L, C, e, stop0, A, k, tmax)
            R = E - stop0
            fund = MA.fund_R(D.fund, coin, "long", [(1.0, E, 0)], b.index[e], ex_i, "4h", R)
            net = (ex_px - E) / R - FEE * (E + ex_px) / R - fund
            path = (L[e:e + ex_i + 1] - E) / E; path[-1] = (ex_px - E) / E
            rows.append(dict(coin=coin, entry_time=b.index[e], exit_time=b.index[e] + (ex_i + 1) * H4, E=E, R=R, net=net, path=path, skip=False))
    return pd.DataFrame(rows)


def main():
    proto = OUT / "A4_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "A4_PROTOCOL_SHA256.txt").read_text().split()[0], "A4 protocol changed"
    D = Data()
    # sanity: (3, 60) must reproduce the corrected A1 S-LAD long gross exactly
    base = trades_for(D, 3, 60)
    chk = float(np.abs(base.gross.values - D.t.gross.values).max())
    assert chk < 1e-9, f"(3,60) does not reproduce A1c gross: {chk}"
    s6 = pd.read_parquet(ROOT / "logs" / "research_probe_scalein" / "trades.parquet", columns=["tf", "coin", "side", "entry_time", "V2_gross"])
    s6 = s6[(s6.tf == "4h") & (s6.side == "long")]
    v2c = trades_for(D, 3, 60, variant="V2")
    mv = v2c.merge(s6, on=["coin", "entry_time"])
    chk_v2 = float(np.abs(mv.gross - mv.V2_gross).max())
    print(f"V2 (3,60) vs S6 V2_gross on {len(mv)} matched trades: max diff {chk_v2:.1e}", flush=True)
    assert chk_v2 < 1e-9, "V2 rule does not reproduce S6"
    grid, monthly, keep = [], {}, {}
    for k, tm in GRID:
        T = base if (k, tm) == (3, 60) else trades_for(D, k, tm)
        keep[(k, tm)] = T
        pf = portfolio(T)
        per = {p: portfolio(T, t0=a, t1=b_) for p, a, b_ in (("P1", T0, P1END), ("P2", P1END, DEV1))}
        p3 = portfolio(T, t0=DEV1, t1=T1)
        dev = T[T.entry_time < DEV1]
        monthly[f"{k}_{tm}"] = pf["monthly"]
        grid.append(dict(trail=k, tstop=tm, n=len(dev), mean_net=dev.net.mean(), median_net=dev.net.median(), win=(dev.net > 0).mean(),
                         mean_bars=dev.exit_idx.mean(), share_truncated=dev.truncated.mean(), final=pf["final"], cagr=pf["cagr"],
                         mtm_dd=pf["mtm_dd"], calmar=pf["calmar"], calmar_P1=per["P1"]["calmar"], calmar_P2=per["P2"]["calmar"],
                         calmar_P3=p3["calmar"], net_P3=T[T.entry_time >= DEV1].net.mean()))
        print("grid", k, tm, round(pf["calmar"], 3), flush=True)
    G = pd.DataFrame(grid)
    G.to_csv(OUT / "A4_exit_grid.csv", index=False)
    cal = {(r.trail, r.tstop): r.calmar for r in G.itertuples()}
    best = max(cal, key=cal.get)
    tms = [60, 120, 1000]
    nb = [(best[0], tms[j]) for j in (tms.index(best[1]) - 1, tms.index(best[1]) + 1) if 0 <= j < 3] + [(7 - best[0], best[1])]
    plateau = all(cal[n] >= 0.8 * cal[best] for n in nb)
    sel = best if plateau else (3, 60)
    # entry variants on the selected exit
    v2 = trades_for(D, *sel, variant="V2")
    mk, mkrows = maker_fills(D)
    mkt = trades_for(D, *sel, maker=mk)
    mkrows = mkrows.merge(mkt[["coin", "entry_time", "net"]], on=["coin", "entry_time"])
    mkrows.to_csv(OUT / "A4_maker_fills.csv", index=False)
    selT = keep[sel]
    psel = {p: portfolio(selT, t0=a, t1=b_)["calmar"] for p, a, b_ in (("dev", T0, DEV1), ("P1", T0, P1END), ("P2", P1END, DEV1))}
    ent = []
    for name, T in (("V2", v2), ("maker", mkt)):
        pc = {p: portfolio(T, t0=a, t1=b_)["calmar"] for p, a, b_ in (("dev", T0, DEV1), ("P1", T0, P1END), ("P2", P1END, DEV1))}
        dv = T[(T.entry_time < DEV1) & ~T.skip]
        ent.append(dict(variant=name, mean_net=dv.net.mean(), calmar_dev=pc["dev"], calmar_P1=pc["P1"], calmar_P2=pc["P2"],
                        adopt=all(pc[p] > psel[p] for p in pc), skipped=int(T.skip.sum())))
    ent.append(dict(variant="selected V0 taker", mean_net=selT[selT.entry_time < DEV1].net.mean(), calmar_dev=psel["dev"],
                    calmar_P1=psel["P1"], calmar_P2=psel["P2"], adopt=None, skipped=0))
    E_ = pd.DataFrame(ent); E_.to_csv(OUT / "A4_entry_variants.csv", index=False)
    final_name = next((r.variant for r in E_.itertuples() if r.adopt is True), "V0 taker")
    F = {"V2": v2, "maker": mkt}.get(final_name, selT)
    # gates
    Mx = pd.DataFrame(monthly).dropna()
    pbo_v, logits = pbo(Mx)
    rnd = [portfolio(random_entry(D, *sel, SEED + i))["calmar"] for i in range(NRAND)]
    rnd_p95 = float(np.percentile(rnd, 95))
    pd.DataFrame(dict(calmar=rnd)).to_csv(OUT / "A4_random_entry.csv", index=False)
    pfF = portfolio(F)
    devF = F[(F.entry_time < DEV1) & ~F.skip]
    fkw = dict(variant="V2") if final_name == "V2" else dict(maker=mk) if final_name == "maker" else {}
    c15 = trades_for(D, *sel, scale=1.5, **fkw)       # change 1 after lock: stresses apply to the FINAL config, all fees scaled
    c20 = trades_for(D, *sel, scale=2.0, **fkw)
    sl3 = trades_for(D, *sel, slip=0.003, **fkw)
    cost_ok = all(x[(x.entry_time < DEV1) & ~x.skip].net.mean() > 0 for x in (c15, c20, sl3))
    pP = {p: portfolio(F, t0=a, t1=b_)["calmar"] for p, a, b_ in (("P1", T0, P1END), ("P2", P1END, DEV1))}
    sr_var = float(np.var([Mx[c].mean() / Mx[c].std(ddof=1) for c in Mx.columns], ddof=1))
    dsr_v, sr, sr0 = dsr(pfF["monthly"], sr_var, 13)
    gates = {"PBO<0.30": pbo_v < 0.30, "beats_random_entry_p95": pfF["calmar"] > rnd_p95, "cost_1.5x_2x_slip": cost_ok,
             "P1_P2_calmar>0": all(v > 0 for v in pP.values()), "DSR>=0.95": dsr_v >= 0.95}
    verdict = "A4 rule sleeve provisional PASS" if all(gates.values()) else "A4 FAIL"
    json.dump(dict(pbo=pbo_v, n_combinations=len(logits), logit_mean=float(logits.mean())), open(OUT / "A4_pbo.json", "w"), indent=1)
    sz = [dict(f=f, **{k_: v for k_, v in portfolio(F, f=f).items() if k_ != "monthly"}) for f in (0.0025, 0.005, 0.0075, 0.01)]
    pd.DataFrame(sz).to_csv(OUT / "A4_sizing.csv", index=False)
    F.drop(columns=["path"]).to_parquet(OUT / "a4_final_trades.parquet", index=False)
    claims = dict(protocol_sha=sha(proto), a1c_sha=sha(A1C), repro_check_max_diff=chk, v2_vs_s6_max_diff=chk_v2, best_grid=list(best), plateau=plateau,
                  selected_exit=list(sel), entry_final=final_name, maker_fill_rate=float(mkrows.filled.mean()),
                  maker_net_filled=float(mkrows[mkrows.filled].net.mean()), maker_net_unfilled=float(mkrows[~mkrows.filled].net.mean()),
                  final=dict(final=pfF["final"], cagr=pfF["cagr"], mtm_dd=pfF["mtm_dd"], calmar=pfF["calmar"], n_dev=int(len(devF)),
                             mean_net=float(devF.net.mean())),
                  pbo=pbo_v, random_entry_p95=rnd_p95, calmar_P1=pP["P1"], calmar_P2=pP["P2"],
                  net_x1_5=float(c15[(c15.entry_time < DEV1) & ~c15.skip].net.mean()),
                  net_x2=float(c20[(c20.entry_time < DEV1) & ~c20.skip].net.mean()),
                  net_slip=float(sl3[(sl3.entry_time < DEV1) & ~sl3.skip].net.mean()),
                  dsr=dsr_v, sr_monthly=sr, sr0=sr0, gates=gates, verdict=verdict,
                  deferred=["G-I 2018-19 (A5, once)", "1D correlation (A5)"])
    (OUT / "claims_a4.json").write_text(json.dumps(claims, indent=1, default=float))
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(G.round(3).to_string()); print(E_.round(3).to_string()); print(pd.DataFrame(sz).round(3).to_string())
    print(json.dumps(claims, indent=1, default=float))


if __name__ == "__main__":
    main()
