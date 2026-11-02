"""Spot graded entry + averaging down + take profit (no stop) and spot + perp combinations.
Protocol: logs/research_spot_dca/SPOT_DCA_PROTOCOL_PREREGISTERED.md (locked before any result). Notes: CODE_NOTES.md.
Run: python src/research/spot_dca_study.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
D1 = PROJ / "data" / "universe_all" / "1d"
FUT = PROJ / "data" / "futures_um"
OUT = PROJ / "logs" / "research_spot_dca"
DATA_END = pd.Timestamp("2026-09-30")
STABLE = {"USDC", "BUSD", "TUSD", "FDUSD", "USDP", "DAI", "PAX", "USDS", "USDSB", "SUSD", "UST", "USTC", "EUR", "GBP", "AUD", "BRL",
          "TRY", "AEUR", "EURI", "XUSD", "USD1", "BFUSD", "RLUSD"}
LEV = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")
FEE = 0.00085


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


proto = OUT / "SPOT_DCA_PROTOCOL_PREREGISTERED.md"
assert sha(proto) == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"


# ---------------- data ----------------
def load_panel():
    files = sorted(D1.glob("*_1d.csv"))
    syms, man = [], []
    for f in files:
        s = f.name[:-7]
        if not s.endswith("USDT") or s.endswith(LEV) or s[:-4] in STABLE:
            continue
        syms.append(s); man.append((str(f.relative_to(PROJ)).replace("\\", "/"), sha(f)))
    dates = pd.date_range("2020-01-01", DATA_END, freq="D")
    n, m = len(dates), len(syms)
    O, Hh, L, C, QV = (np.full((n, m), np.nan) for _ in range(5))
    last = np.full(m, -1)
    for j, s in enumerate(syms):
        d = pd.read_csv(D1 / f"{s}_1d.csv", usecols=["timestamp", "open", "high", "low", "close", "quote_volume"], parse_dates=["timestamp"])
        d = d.drop_duplicates("timestamp").set_index("timestamp").sort_index()
        d = d[(d.index >= dates[0]) & (d.index <= DATA_END)]
        if d.empty:
            continue
        ix = dates.get_indexer(d.index)
        O[ix, j], Hh[ix, j], L[ix, j], C[ix, j], QV[ix, j] = d.open, d.high, d.low, d.close, d.quote_volume
        last[j] = ix.max()
    pd.DataFrame(man, columns=["path", "sha256"]).to_csv(OUT / "input_manifest.csv", index=False)
    return dates, syms, O, Hh, L, C, QV, last


def features(H_, C, QV):
    Cdf, Hdf, Q = pd.DataFrame(C), pd.DataFrame(H_), pd.DataFrame(QV)
    nbar = Cdf.notna().cumsum().values
    mh90 = Hdf.rolling(90, min_periods=1).max().values
    dd90 = C / mh90 - 1
    dlt = Cdf.diff()
    up, dn = dlt.clip(lower=0), (-dlt).clip(lower=0)
    au = up.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    ad = dn.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rsi = (100 - 100 / (1 + au / ad)).values
    rsi = np.where((ad.values == 0) & (au.values > 0), 100.0, rsi)
    rev = C > np.vstack([np.full((1, C.shape[1]), np.nan), H_[:-1]])          # close_t > high_{t-1}
    medqv = Q.rolling(30, min_periods=20).median().values
    elig = (nbar >= 200) & (medqv >= 10e6) & ~np.isnan(C)
    gA = (dd90 <= -0.30) & (rsi <= 35) & rev
    gB = (dd90 <= -0.15) & (rsi <= 45) & rev & ~gA
    return dict(dd90=dd90, rsi=rsi, rev=rev, elig=elig, gA=gA, gB=gB)


# ---------------- simulation ----------------
def simulate(P, F, i0, i1, tp=0.10, regime_tp=False, max_adds=4, fee=FEE, stop=None, entries=None, seed=None, btc_bear=None):
    """entries: None = graded (P); or {day: [grade,...]} for the random control (coins drawn at random)."""
    dates, syms, O, H_, L, C, last = P
    m = len(syms)
    rng = np.random.default_rng(seed) if seed is not None else None
    cash, pos, eq, trades, pend, ent_log, lastpx = 10_000.0, {}, [], [], [], {}, np.full(m, np.nan)
    for i in range(i0, i1 + 1):
        # 1) fills at the open of day i
        for (j, notional, kind, grade) in pend:
            o = O[i, j]
            if np.isnan(o) or notional <= 0:
                continue
            cost = notional * (1 + fee)
            if cost > cash + 1e-9:
                continue
            q = notional / o
            cash -= cost
            p = pos.get(j)
            if p is None:
                p = pos[j] = dict(q=0.0, cost=0.0, n_add=-1, last_buy=o, t0=i, buys=[])
            p["q"] += q; p["cost"] += q * o; p["n_add"] += 1; p["last_buy"] = o
            p["buys"].append((str(dates[i].date()), o, notional, grade))
            bear = bool(btc_bear[i - 1]) if btc_bear is not None else False
            p["tp"] = (0.05 if bear else 0.10) if regime_tp else tp
        pend = []
        # 2) exits on day i: stop (variant) then TP; delisting at the last bar
        for j in list(pos):
            p = pos[j]
            avg = p["cost"] / p["q"]
            o, h, lo, c = O[i, j], H_[i, j], L[i, j], C[i, j]
            px, why = None, None
            if not np.isnan(o):
                if stop is not None:
                    sp = avg * (1 - stop)
                    if o <= sp:
                        px, why = o, "stop"
                    elif lo <= sp:
                        px, why = sp, "stop"
                if px is None:
                    tpx = avg * (1 + p["tp"])
                    if o >= tpx:
                        px, why = o, "tp"
                    elif h >= tpx:
                        px, why = tpx, "tp"
            if px is None and last[j] == i and dates[i] < DATA_END:
                px, why = c, "delisted"
            if px is not None:
                cash += p["q"] * px * (1 - fee)
                trades.append(dict(sym=syms[j], entry=dates[p["t0"]].date(), exit=dates[i].date(), why=why, n_buys=len(p["buys"]),
                                   invested=sum(b[2] for b in p["buys"]), avg=avg, exit_px=px,
                                   pnl=p["q"] * px * (1 - fee) - sum(b[2] for b in p["buys"]) * (1 + fee), days=i - p["t0"], buys=p["buys"]))
                del pos[j]
        # 3) mark at the close
        ok = ~np.isnan(C[i]); lastpx[ok] = C[i, ok]
        expo = sum(p["q"] * lastpx[j] for j, p in pos.items())
        equity = cash + expo
        eq.append((dates[i], equity, cash, expo, len(pos)))
        if i == i1:
            break
        # 4) decisions at the close of day i -> fills at the open of i+1
        avail = cash
        adds = []
        for j, p in pos.items():
            if np.isnan(C[i, j]) or p["n_add"] >= max_adds:
                continue
            if C[i, j] <= 0.85 * p["last_buy"] and F["rev"][i, j]:
                adds.append((j, 0.05 if (F["dd90"][i, j] <= -0.30 and F["rsi"][i, j] <= 35) else 0.02))
        for j, w in adds:
            nt = w * equity
            if nt * (1 + fee) <= avail:
                pend.append((j, nt, "add", "add")); avail -= nt * (1 + fee)
        free = F["elig"][i] & ~np.isin(np.arange(m), list(pos))
        if entries is None:
            cand = [(0, F["dd90"][i, j], syms[j], j, "A") for j in np.flatnonzero(free & F["gA"][i])] + \
                   [(1, F["dd90"][i, j], syms[j], j, "B") for j in np.flatnonzero(free & F["gB"][i])]
            cand.sort()
            todays = [(j, g) for _, _, _, j, g in cand]
            ent_log[i] = [g for _, g in todays]
        else:
            gl = entries.get(i, [])
            pool = np.flatnonzero(free)
            pick = rng.choice(pool, size=min(len(gl), len(pool)), replace=False) if len(gl) and len(pool) else []
            todays = list(zip(pick, sorted(gl)))
        for j, g in todays:
            nt = (0.05 if g == "A" else 0.02) * equity
            if nt * (1 + fee) <= avail:
                pend.append((j, nt, "new", g)); avail -= nt * (1 + fee)
    E = pd.DataFrame(eq, columns=["date", "equity", "cash", "expo", "n_pos"]).set_index("date")
    open_pos = [dict(sym=syms[j], entry=dates[p["t0"]].date(), n_buys=len(p["buys"]), invested=sum(b[2] for b in p["buys"]),
                     value=p["q"] * lastpx[j], unreal=p["q"] * lastpx[j] - sum(b[2] for b in p["buys"]) * (1 + fee), days=i1 - p["t0"],
                     buys=json.dumps(p["buys"]))
                for j, p in pos.items()]
    return E, pd.DataFrame(trades), pd.DataFrame(open_pos), ent_log


def metrics(E, T, OP):
    e = E.equity
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    mo = e.resample("ME").last().pct_change().dropna()
    out = dict(final=float(e.iloc[-1]), cagr=float((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1), maxdd=float((e / e.cummax() - 1).min()),
               sharpe=float(r.mean() / r.std() * np.sqrt(365)) if r.std() > 0 else 0.0, worst_month=float(mo.min()) if len(mo) else None,
               max_deployed=float((E.expo / E.equity).max()), avg_deployed=float((E.expo / E.equity).mean()), max_positions=int(E.n_pos.max()))
    if len(T):
        out.update(round_trips=int(len(T)), by_exit=T.why.value_counts().to_dict(), tp_days_median=float(T[T.why == "tp"].days.median()) if (T.why == "tp").any() else None,
                   tp_days_max=int(T[T.why == "tp"].days.max()) if (T.why == "tp").any() else None,
                   delisted_loss=float(T[T.why == "delisted"].pnl.sum()), worst_trade=float(T.pnl.min()), best_trade=float(T.pnl.max()),
                   win_share=float((T.pnl > 0).mean()), realized=float(T.pnl.sum()))
    if len(OP):
        out.update(open_at_end=int(len(OP)), open_unreal=float(OP.unreal.sum()), open_worst=float(OP.unreal.min()), open_longest_days=int(OP.days.max()))
    return out


def main():
    P = load_panel()
    dates, syms, O, H_, L, C, QV, last = P
    F = features(H_, C, QV)
    PS = (dates, syms, O, H_, L, C, last)
    jb = syms.index("BTCUSDT")
    sma = pd.Series(C[:, jb]).rolling(200).mean().values
    bear = C[:, jb] < sma
    idx = lambda s: int(dates.get_indexer([pd.Timestamp(s)])[0])
    periods = dict(full=(idx("2020-07-01"), idx("2026-09-30")), dev=(idx("2020-07-01"), idx("2023-12-31")), holdout=(idx("2024-01-01"), idx("2026-09-30")))
    res = dict(protocol_sha256=sha(proto), code_sha256=sha(__file__), manifest_sha256=None, n_symbols=len(syms))
    res["manifest_sha256"] = sha(OUT / "input_manifest.csv")
    runs = {}
    for per, (a, b) in periods.items():
        E, T, OP, ent = simulate(PS, F, a, b, btc_bear=bear)
        runs[per] = (E, T, OP, ent)
        res[f"P_{per}"] = metrics(E, T, OP)
        E.to_csv(OUT / f"P_{per}_equity.csv"); T.to_json(OUT / f"P_{per}_trades.json", orient="records", date_format="iso", default_handler=str, double_precision=15)
        OP.to_csv(OUT / f"P_{per}_open_at_end.csv", index=False)
        print(per, json.dumps(res[f"P_{per}"], default=str), flush=True)
        for nm, kw in dict(tp3=dict(tp=0.03), tp5=dict(tp=0.05), tp20=dict(tp=0.20), regime_tp=dict(regime_tp=True), adds0=dict(max_adds=0),
                           adds_unlimited=dict(max_adds=10_000), fee_stress=dict(fee=0.002), stop50=dict(stop=0.50)).items():
            Ev, Tv, OPv, _ = simulate(PS, F, a, b, btc_bear=bear, **kw)
            res[f"V_{nm}_{per}"] = metrics(Ev, Tv, OPv)
        ctl = []
        for sd in range(100):
            Ec, Tc, OPc, _ = simulate(PS, F, a, b, btc_bear=bear, entries=ent, seed=sd)
            mc = metrics(Ec, Tc, OPc); ctl.append((mc["cagr"], mc["maxdd"], mc["final"]))
        ctl = np.array(ctl)
        res[f"control_{per}"] = dict(cagr_median=float(np.median(ctl[:, 0])), cagr_p5=float(np.percentile(ctl[:, 0], 5)), cagr_p95=float(np.percentile(ctl[:, 0], 95)),
                                     maxdd_median=float(np.median(ctl[:, 1])), P_cagr_percentile=float((ctl[:, 0] < res[f"P_{per}"]["cagr"]).mean()),
                                     P_maxdd_percentile=float((ctl[:, 1] < res[f"P_{per}"]["maxdd"]).mean()))
        for c in ("BTCUSDT", "ETHUSDT"):
            k = syms.index(c); x = pd.Series(C[a:b + 1, k], index=dates[a:b + 1]).ffill()
            yrs = (x.index[-1] - x.index[0]).days / 365.25
            res[f"bh_{c}_{per}"] = dict(cagr=float((x.iloc[-1] / x.iloc[0]) ** (1 / yrs) - 1), maxdd=float((x / x.cummax() - 1).min()))
        print(per, "variants and controls done", flush=True)
    # ---------------- Q2 ----------------
    fund = {c: pd.read_csv(FUT / f"{c}_funding.csv", parse_dates=["time"]).set_index("time").funding_rate.astype(float) for c in ("BTCUSDT", "ETHUSDT")}
    for c, f in fund.items():
        f = f[(f.index >= "2020-07-01") & (f.index < "2026-10-01")]
        per_year = {int(y): dict(net_pct=float(g.sum() * 100), neg_share=float((g < 0).mean()), n=int(len(g))) for y, g in f.groupby(f.index.year)}
        daily = f.groupby(f.index.floor("D")).sum()
        m7 = f.rolling("7D").mean().groupby(f.index.floor("D")).last()
        state = (m7 > 0).shift(1).fillna(False)                         # decided at the prior day's close
        daily = daily.reindex(state.index).fillna(0)
        sw = state.astype(int).diff().abs().fillna(state.iloc[0]).astype(int)
        filt = daily.where(state, 0.0) - 0.002 * sw
        k = syms.index(c); px = pd.Series(C[:, k], index=dates); hi = pd.Series(H_[:, k], index=dates)
        rise = {n: float((hi.rolling(n).max().shift(-n) / px - 1).max()) for n in (7, 30)}
        res[f"B1_{c}"] = dict(per_year=per_year, total_always_pct=float(f.sum() * 100 - 0.2), total_filter_pct=float(filt.sum() * 100),
                              filter_days_in=float(state.mean()), switches=int(sw.sum()), max_rise_7d=rise[7], max_rise_30d=rise[30])
        if c == "BTCUSDT":
            carry_daily = filt / 2.0                                    # CODE_NOTES 2: capital = 2 x notional
    Ef = runs["full"][0]
    k = syms.index("BTCUSDT"); btc = pd.Series(C[:, k], index=dates).reindex(Ef.index)
    fb = fund["BTCUSDT"]; fbd = fb.groupby(fb.index.floor("D")).sum().reindex(Ef.index).fillna(0)
    bear_s = pd.Series(bear, index=dates).reindex(Ef.index)
    notional = (Ef.expo.shift(1) * bear_s.shift(1).fillna(False)).fillna(0)
    hedge = -notional * btc.pct_change().fillna(0) + notional * fbd - 0.0005 * notional.diff().abs().fillna(notional)
    H = Ef.equity + hedge.cumsum()
    res["B2"] = dict(P=metrics(Ef, runs["full"][1], runs["full"][2]), hedged=dict(final=float(H.iloc[-1]), maxdd=float((H / H.cummax() - 1).min()),
                     cagr=float((H.iloc[-1] / H.iloc[0]) ** (365.25 / (H.index[-1] - H.index[0]).days) - 1)),
                     hedge_pnl=float(hedge.sum()), max_hedge_notional=float(notional.max()), max_hedge_over_cash=float((notional / Ef.cash.shift(1)).replace(np.inf, np.nan).max()))
    b3 = []
    for c in ("BTCUSDT", "ETHUSDT"):
        k = syms.index(c); f = fund[c]; i = 30
        while i < len(dates) - 31:
            if dates[i] >= pd.Timestamp("2020-07-01") and C[i, k] / C[i - 30, k] - 1 > 0.30:
                e0, e1 = O[i + 1, k], O[i + 31, k]
                fr = f[(f.index > dates[i + 1]) & (f.index <= dates[i + 31])].sum()
                b3.append(dict(coin=c, signal=str(dates[i].date()), ret=float(-(e1 / e0 - 1) + fr - 0.001)))
                i += 31
            else:
                i += 1
    b3 = pd.DataFrame(b3)
    res["B3"] = dict(trades=b3.to_dict("records"), n=int(len(b3)), mean=float(b3.ret.mean()), win_share=float((b3.ret > 0).mean()),
                     worst=float(b3.ret.min()), sum=float(b3.ret.sum()))
    # ---------------- Q3 ----------------
    eco = pd.read_parquet(PROJ / "data" / "derived" / "eco" / "e2_daily_series.parquet")
    er = pd.concat([eco[c].dropna().pct_change().dropna() for c in eco.columns if c.endswith("|ECO-W2") and not c.startswith("P1|") and not c.startswith("P2|")])
    er = er[~er.index.duplicated()].sort_index()
    rp = Ef.equity.pct_change()
    R = pd.concat([er.rename("eco"), rp.rename("dca"), carry_daily.rename("carry")], axis=1, sort=True).dropna()
    mixes = {"100/0/0": (1, 0, 0), "80/20/0": (.8, .2, 0), "70/15/15": (.7, .15, .15), "60/20/20": (.6, .2, .2), "50/25/25": (.5, .25, .25),
             "0/100/0": (0, 1, 0), "0/0/100": (0, 0, 1)}
    q3 = {}
    for nm, w in mixes.items():
        w = np.array(w, float); val, hold, out = 10_000.0, None, []
        for t, row in R.iterrows():
            if hold is None or t.month != prev:
                hold = val * w; prev = t.month
            hold = hold * (1 + row.values); val = hold.sum(); out.append((t, val))
        s = pd.Series(dict(out)); r = s.pct_change().dropna(); yrs = (s.index[-1] - s.index[0]).days / 365.25
        q3[nm] = dict(final=float(s.iloc[-1]), cagr=float((s.iloc[-1] / 10_000) ** (1 / yrs) - 1), maxdd=float((s / s.cummax() - 1).min()),
                      sharpe=float(r.mean() / r.std() * np.sqrt(365)))
    res["Q3"] = dict(period=[str(R.index[0].date()), str(R.index[-1].date())], days=int(len(R)), corr=R.corr().round(4).to_dict(), mixes=q3)
    f = OUT / "SPOT_DCA_RESULTS.json"
    f.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (OUT / "SPOT_DCA_RESULTS_SHA256.txt").write_text(sha(f) + "  SPOT_DCA_RESULTS.json\n")
    print(json.dumps({k: v for k, v in res.items() if not k.startswith("V_")}, default=str)[:4000])


if __name__ == "__main__":
    main()
