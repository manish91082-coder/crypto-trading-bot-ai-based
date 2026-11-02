"""Spot long-only sleeve study (logs/research_spot_sleeve/SPOT_SLEEVE_PROTOCOL_PREREGISTERED.md, locked before results).
Run: python src/research/spot_sleeve_study.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
OUT = PROJ / "logs" / "research_spot_sleeve"
sys.path.insert(0, str(PROJ / "src" / "research"))
STABLE = {"USDC", "BUSD", "TUSD", "FDUSD", "USDP", "DAI", "PAX", "USDS", "USDSB", "SUSD", "UST", "USTC", "EUR", "GBP", "AUD", "BRL",
          "TRY", "AEUR", "EURI", "XUSD", "USD1", "BFUSD", "RLUSD"}
LEV = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")
END = pd.Timestamp("2026-09-30")
PER = dict(P0=("2018-03-06", "2019-12-31"), dev=("2020-07-01", "2023-12-31"), holdout=("2024-01-01", "2026-09-30"), full=("2020-07-01", "2026-09-30"))
MAN = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


proto = OUT / "SPOT_SLEEVE_PROTOCOL_PREREGISTERED.md"
assert sha(proto) == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"


def read(f):
    MAN.append((str(f.relative_to(PROJ)).replace("\\", "/"), sha(f)))
    d = pd.read_csv(f, usecols=["timestamp", "open", "high", "low", "close", "quote_volume"], parse_dates=["timestamp"])
    return d.drop_duplicates("timestamp").set_index("timestamp").sort_index()


def major(s):
    a = read(PROJ / "data" / "universe_pre2020" / "1d" / f"{s}_1d.csv")
    b = read(PROJ / "data" / "universe_all" / "1d" / f"{s}_1d.csv")
    d = pd.concat([a[a.index < "2020-01-01"], b[b.index >= "2020-01-01"]])
    d = d[d.index <= END]
    return d.asfreq("D")                                            # calendar grid (NaN on a missing day)


def metrics(eq, trades=None, inmkt=None):
    r = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    out = dict(final=float(eq.iloc[-1]), cagr=float((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1), maxdd=float((eq / eq.cummax() - 1).min()),
               sharpe=float(r.mean() / r.std() * np.sqrt(365)) if r.std() > 0 else 0.0)
    if inmkt is not None:
        out["time_in_market"] = float(np.mean(inmkt))
    if trades is not None:
        t = np.array([x["ret"] for x in trades]) if trades else np.array([])
        out.update(trades=int(len(t)), win_share=float((t > 0).mean()) if len(t) else None, avg_win=float(t[t > 0].mean()) if (t > 0).any() else None,
                   avg_loss=float(t[t <= 0].mean()) if (t <= 0).any() else None, best=float(t.max()) if len(t) else None, worst=float(t.min()) if len(t) else None)
    return out


def single(d, state, a, b, fee):
    """state: bool Series on the calendar grid, decided at the close; position for day t = state[t-1]; fills at the open."""
    idx = d.loc[a:b].index
    cash, units, eq, trades, entry, inm = 10_000.0, 0.0, [], [], None, []
    lastc = d.close.ffill()
    prev = state.astype(float).shift(1)
    for t in idx:
        w_ = prev.get(t, np.nan)
        want = bool(w_) if not pd.isna(w_) else False
        o = d.open.get(t)
        if not pd.isna(o):
            if want and units == 0:
                units = cash * (1 - fee) / o; cash = 0.0; entry = (t, o)
            elif not want and units > 0:
                cash = units * o * (1 - fee); trades.append(dict(entry=str(entry[0].date()), exit=str(t.date()), ret=float(o / entry[1] * (1 - fee) ** 2 - 1)))
                units = 0.0
        eq.append(cash + units * lastc[t]); inm.append(units > 0)
    if units > 0:                                                          # open at the end: valued, counted as an open trade
        trades.append(dict(entry=str(entry[0].date()), exit="open", ret=float(lastc[idx[-1]] / entry[1] * (1 - fee) - 1)))
    return pd.Series(eq, index=idx), trades, inm


def spells_control(state, d, a, b, fee, seeds=200):
    s = state.loc[a:b].astype(bool).values
    runs, cur, n = [], s[0], 0
    for x in s:
        if x == cur:
            n += 1
        else:
            runs.append((cur, n)); cur, n = x, 1
    runs.append((cur, n))
    ins, outs = [r[1] for r in runs if r[0]], [r[1] for r in runs if not r[0]]
    sh = []
    for sd in range(seeds):
        rng = np.random.default_rng(sd)
        i_, o_ = list(rng.permutation(ins)), list(rng.permutation(outs))
        seq, st = [], runs[0][0]
        while i_ or o_:
            src = i_ if st else o_
            if src:
                seq += [st] * src.pop()
            st = not st
        ser = pd.Series(seq[:len(s)], index=state.loc[a:b].index)
        full = state.copy(); full.loc[a:b] = ser
        e, _, _ = single(d, full, a, b, fee)
        r = e.pct_change().dropna(); sh.append(r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else 0)
    return np.array(sh)


def main():
    BTC, ETH = major("BTCUSDT"), major("ETHUSDT")
    sma = lambda d, n: d.close.rolling(n, min_periods=n).mean()
    st = {}
    st["S1"] = BTC.close > sma(BTC, 200)
    st["S3"] = sma(BTC, 50) > sma(BTC, 200)
    mon = BTC.index.dayofweek == 0
    mom = (BTC.close / BTC.close.shift(28) > 1)
    st["S4"] = pd.Series(np.where(mon, mom, np.nan), index=BTC.index).ffill().fillna(0).astype(bool)
    hi365 = BTC.high.rolling(365, min_periods=200).max()
    s50 = sma(BTC, 50)
    cross = (BTC.close.shift(1) <= s50.shift(1)) & (BTC.close > s50)
    entry6 = (BTC.close <= 0.70 * hi365) & cross
    s6, cur = [], False
    for t in BTC.index:
        if not cur and bool(entry6.get(t, False)):
            cur = True
        elif cur and BTC.close.get(t) < s50.get(t):
            cur = False
        s6.append(cur)
    st["S6"] = pd.Series(s6, index=BTC.index)
    eth_s1 = ETH.close > sma(ETH, 200)
    res = dict(protocol_sha256=sha(proto), code_sha256=sha(__file__))
    daily = {}
    for fee_tag, fee in (("base", 0.001), ("stress", 0.0025)):
        for per, (a, b) in PER.items():
            R = {}
            e0, _, _ = single(BTC, pd.Series(True, index=BTC.index), a, b, fee); R["B0"] = metrics(e0)
            # B1 50/50 monthly rebalance
            idx = BTC.loc[a:b].index; ub = ue = 0.0; cash = 10_000.0; eq = []
            for t in idx:
                ob, oe = BTC.open.get(t), ETH.open.get(t)
                if (t == idx[0] or t.day == 1) and not (pd.isna(ob) or pd.isna(oe)):
                    v = cash + ub * ob + ue * oe
                    tb, te = 0.5 * v / ob, 0.5 * v / oe
                    cost = (abs(tb - ub) * ob + abs(te - ue) * oe) * fee
                    ub, ue, cash = tb, te, -cost
                eq.append(cash + ub * BTC.close.ffill()[t] + ue * ETH.close.ffill()[t])
            R["B1"] = metrics(pd.Series(eq, index=idx))
            for k in ("S1", "S3", "S4", "S6"):
                e, tr, inm = single(BTC, st[k], a, b, fee); R[k] = metrics(e, tr, inm)
                if fee_tag == "base":
                    daily[(k, per)] = e; R[k]["trade_list"] = tr
            eb, trb, ib = single(BTC, st["S1"], a, b, fee); ee, tre, ie = single(ETH, eth_s1, a, b, fee)
            e2 = eb * 0.5 + ee * 0.5
            R["S2"] = metrics(e2, trb + tre, [x or y for x, y in zip(ib, ie)])
            if fee_tag == "base":
                daily[("S2", per)] = e2
            if per != "P0":
                e5, tr5, h5 = s5_run(BTC, sma(BTC, 200), a, b, fee)
                R["S5"] = metrics(e5, tr5, [len(x) > 0 for x in h5.values()])
                if fee_tag == "base":
                    daily[("S5", per)] = e5
                    pd.Series({str(k.date()): v for k, v in h5.items()}).to_json(OUT / f"S5_holdings_{per}.json")
            res[f"{fee_tag}_{per}"] = R
            print(fee_tag, per, {k: (round(v["final"]), round(v["cagr"], 3), round(v["maxdd"], 3), round(v["sharpe"], 2)) for k, v in R.items()}, flush=True)
    # controls (base fee, full period)
    a, b = PER["full"]
    ctl = {}
    for k in ("S1", "S3", "S4", "S6"):
        sh = spells_control(st[k], BTC, a, b, 0.001)
        ctl[k] = dict(rule_sharpe=res["base_full"][k]["sharpe"], ctrl_median=float(np.median(sh)), percentile=float((sh < res["base_full"][k]["sharpe"]).mean()))
    shb = spells_control(st["S1"], BTC, a, b, 0.001); she = spells_control(eth_s1, ETH, a, b, 0.001)
    ctl["S2"] = dict(rule_sharpe=res["base_full"]["S2"]["sharpe"], note="BTC and ETH legs controlled separately",
                     btc_leg_percentile=float((shb < metrics(single(BTC, st["S1"], a, b, 0.001)[0])["sharpe"]).mean()),
                     eth_leg_percentile=float((she < metrics(single(ETH, eth_s1, a, b, 0.001)[0])["sharpe"]).mean()))
    res["controls_full"] = ctl
    print("controls", ctl, flush=True)
    # DSR (information)
    import n1_portfolio as N
    rets = {k: daily[(k, "full")].pct_change().dropna() for k in ("S1", "S2", "S3", "S4", "S5", "S6")}
    srs = np.array([r.mean() / r.std() for r in rets.values()])
    res["dsr_full"] = {k: N.dsr(r, float(srs.var()), 6)[0] for k, r in rets.items()}
    # gates
    gates = {}
    for k in ("S1", "S2", "S3", "S4", "S5", "S6"):
        g1 = all(res[f"base_{p}"][k]["sharpe"] >= res[f"base_{p}"]["B0"]["sharpe"] and res[f"base_{p}"][k]["maxdd"] >= res[f"base_{p}"]["B0"]["maxdd"] + 0.10
                 for p in ("dev", "holdout"))
        if k == "S5":
            g2 = res["base_full"]["S5"]["sharpe"] > res["base_full"]["S1"]["sharpe"]
        elif k == "S2":
            g2 = ctl["S2"]["btc_leg_percentile"] >= 0.9 and ctl["S2"]["eth_leg_percentile"] >= 0.9
        else:
            g2 = ctl[k]["percentile"] >= 0.9
        g3 = all(res[f"base_{p}"][k]["cagr"] > 0 for p in (("dev", "holdout") if k == "S5" else ("P0", "dev", "holdout")))
        gates[k] = dict(G1=bool(g1), G2=bool(g2), G3=bool(g3), candidate=bool(g1 and g2 and g3))
    res["gates"] = gates
    # mix with ECO-W2 (backtest)
    eco = pd.read_parquet(PROJ / "data" / "derived" / "eco" / "e2_daily_series.parquet")
    MAN.append(("data/derived/eco/e2_daily_series.parquet", sha(PROJ / "data" / "derived" / "eco" / "e2_daily_series.parquet")))
    er = pd.concat([eco[c].dropna().pct_change().dropna() for c in eco.columns if c.endswith("|ECO-W2") and not c.startswith("P1|") and not c.startswith("P2|")])
    er = er[~er.index.duplicated()].sort_index()
    mix = {}
    for k in ("B0", "S1", "S2", "S3", "S4", "S5", "S6"):
        sl = (daily[(k, "full")] if k != "B0" else single(BTC, pd.Series(True, index=BTC.index), *PER["full"], 0.001)[0]).pct_change()
        J = pd.concat([er.rename("eco"), sl.rename("s")], axis=1, sort=True).dropna()
        mix[k] = dict(corr_with_eco=float(J.corr().iloc[0, 1]))
        for s in (0.0, 0.1, 0.2, 0.3):
            val, hold, out, prev = 10_000.0, None, [], None
            for t, row in J.iterrows():
                if hold is None or t.month != prev:
                    hold = val * np.array([1 - s, s]); prev = t.month
                hold = hold * (1 + row.values); val = hold.sum(); out.append((t, val))
            ser = pd.Series(dict(out)); mix[k][f"share_{int(s * 100)}"] = metrics(ser)
        mix[k]["period"] = [str(J.index[0].date()), str(J.index[-1].date())]
    res["mix"] = mix
    pd.DataFrame(MAN, columns=["path", "sha256"]).drop_duplicates().to_csv(OUT / "input_manifest.csv", index=False)
    res["manifest_sha256"] = sha(OUT / "input_manifest.csv")
    for (k, per), e in daily.items():
        e.to_csv(OUT / f"equity_{k}_{per}.csv")
    f = OUT / "SPOT_SLEEVE_RESULTS.json"
    f.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (OUT / "SPOT_SLEEVE_RESULTS_SHA256.txt").write_text(sha(f) + "  SPOT_SLEEVE_RESULTS.json\n")
    print("gates", gates)


def s5_run(BTC, btc_sma, a, b, fee):
    files = sorted((PROJ / "data" / "universe_all" / "1d").glob("*_1d.csv"))
    C, O, QV = {}, {}, {}
    for f in files:
        s = f.name[:-7]
        if not s.endswith("USDT") or s.endswith(LEV) or s[:-4] in STABLE:
            continue
        d = read(f)
        d = d[d.index <= END].asfreq("D")
        C[s], O[s], QV[s] = d.close, d.open, d.quote_volume
    C, O, QV = pd.DataFrame(C), pd.DataFrame(O), pd.DataFrame(QV)
    nb = C.notna().cumsum()
    medqv = QV.rolling(30, min_periods=20).median()
    r28 = C / C.shift(28) - 1
    lastbar = C.apply(lambda x: x.last_valid_index())
    idx = C.loc[a:b].index
    cash, units, eq, trades, hold_log, cost_basis = 10_000.0, {}, [], [], {}, {}
    lastc = C.ffill()
    target = None
    for t in idx:
        # fills at the open: rebalance to the target chosen at the previous Monday close
        if target is not None:
            v_open = cash + sum(q * (O.at[t, s] if not pd.isna(O.at[t, s]) else lastc.at[t, s]) for s, q in units.items())
            for s in list(units):
                if s not in target and not pd.isna(O.at[t, s]):
                    px = O.at[t, s]; cash += units[s] * px * (1 - fee)
                    trades.append(dict(sym=s, exit=str(t.date()), ret=float(px / cost_basis[s] * (1 - fee) ** 2 - 1))); del units[s]
            w = v_open / len(target) if target else 0                      # equal weight: trim first, then buy
            for s in target:
                px = O.at[t, s]
                if s in units and not pd.isna(px) and units[s] * px > w:
                    q = (units[s] * px - w) / px; units[s] -= q; cash += q * px * (1 - fee)
            for s in target:
                px = O.at[t, s]
                if pd.isna(px):
                    continue
                have = units.get(s, 0.0) * px
                buy = min(w - have, cash / (1 + fee))
                if buy > 0:
                    q = buy / px; cash -= buy * (1 + fee)
                    cost_basis[s] = (cost_basis.get(s, px) * units.get(s, 0.0) + px * q) / (units.get(s, 0.0) + q)
                    units[s] = units.get(s, 0.0) + q
            target = None
        # delisting: sold at the last close
        for s in list(units):
            if lastbar[s] == t and t < END:
                px = C.at[t, s]; cash += units[s] * px * (1 - fee)
                trades.append(dict(sym=s, exit=str(t.date()), ret=float(px / cost_basis[s] * (1 - fee) ** 2 - 1), why="delisted")); del units[s]
        eq.append(cash + sum(q * lastc.at[t, s] for s, q in units.items()))
        # Monday close: choose the target
        if t.dayofweek == 0 and t < idx[-1]:
            if BTC.close.get(t) > btc_sma.get(t):
                el = (nb.loc[t] >= 200) & medqv.loc[t].notna() & r28.loc[t].notna() & C.loc[t].notna()
                top20 = medqv.loc[t][el].sort_values(ascending=False).head(20).index
                target = list(r28.loc[t, top20].sort_values(ascending=False).head(5).index)
            else:
                target = []
            hold_log[t] = list(target)
    return pd.Series(eq, index=idx), trades, hold_log


if __name__ == "__main__":
    main()
