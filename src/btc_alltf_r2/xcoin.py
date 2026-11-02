"""BTC-ALLTF-R2 (2026-10-29): cross-coin confirmation. The configs chosen on BTC (family S1), every L1 config (family S2) or
the controls (family CTRL) are paper-traded on every other coin of the R2 universe with the LOCKED BTC-ALLTF engine and rules
(src/btc_alltf/engine.dll, rules.py, study.enumerate_configs: nothing about a config is changed), same fees (fees.json),
real funding for futures. Entries are only allowed on liquid days (trailing 30-day mean quote volume >= 2 M USDT, causal).
Each (config, coin) gives daily mark-to-market returns (common.mtm); per config they are summed over coins day by day:
  SR  sum of daily returns            SR2 the same with 2x fee          DEN number of coins in the portfolio that day
  SEX sum of excess returns r - e*dir*m (e = the config's time in position on that coin, m = the coin's close-to-close return)
plus the equal-weight buy-and-hold benchmark of the liquid coins (BHS / BHD) and one summary row per (config, coin).
Usage: python src/btc_alltf_r2/xcoin.py --run <R2 RUN dir> --market spot --tf 1h --family S1 [--max-coins N]"""
import argparse
import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402
import rules                                                                  # noqa: E402  (src/btc_alltf, via common)
import study                                                                  # noqa: E402

E = K.E
X = K.CFG["xcoin"]
LO, HI = K.ms(X["grid_start"]), K.ms(X["grid_end"])
DAY0 = LO // K.DAY
ND = (HI - LO) // K.DAY


def coins_for(market, tf):
    M = pd.read_csv(K.R2 / "universe_manifest.csv")
    if market == "spot" and tf == "1m":
        return list(X["spot_1m_coins"])
    if market == "spot" and tf in ("5m", "15m", "30m"):
        return sorted(M[(M.market == "spot") & (M.use_hf == True)].coin)                  # noqa: E712
    return sorted(M[(M.market == market) & (M.use_1d_1h == True)].coin)                   # noqa: E712


def segments(market, tf, coin):
    """[lo, hi) ms ranges of usable data; for spot 1m only the months whose every hour matched universe_all 1h"""
    if not (market == "spot" and tf == "1m"):
        return [(LO, HI)]
    m = pd.read_csv(K.R2 / "universe_1m_months.csv")
    m = m[(m.coin == coin) & m.use].month.sort_values().tolist()
    segs = []
    for mo in m:
        a = K.ms(mo + "-01")
        b = K.ms((pd.Timestamp(mo + "-01") + pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d"))
        if segs and segs[-1][1] == a:
            segs[-1] = (segs[-1][0], b)
        else:
            segs.append((a, b))
    return segs


def refine_segments(segs, close, max_gap_days=7):
    """R2 amendment 1 (after the lock, see R2_CODE_CHANGES_AFTER_LOCK.md): trade a coin only inside runs of days that HAVE a daily
    close, and split a run where two consecutive days with a close are more than max_gap_days apart. Some symbols were relisted
    as a new token (LUNA 2022-05-31 and others): their 1h/15m/5m files continue under the old symbol while the 1d file stops, so
    the intraday bars belong to another asset and a position must never be marked or held across that break."""
    days = np.nonzero(np.isfinite(close))[0]
    if not len(days):
        return []
    runs, a = [], days[0]
    for x, y in zip(days[:-1], days[1:]):
        if y - x > max_gap_days:
            runs.append((a, x)); a = y
    runs.append((a, days[-1]))
    out = []
    for lo, hi in segs:
        for ra, rb in runs:
            a_, b_ = max(lo, (DAY0 + ra) * K.DAY), min(hi, (DAY0 + rb + 1) * K.DAY)
            if a_ < b_:
                out.append((a_, b_))
    return out


def family_names(market, tf, family):
    if family == "S1":
        s = pd.read_csv(K.R2 / "selection_S1.csv")
        return s[(s.market == market) & (s.tf == tf)].sort_values("sel_rank").name.tolist()
    if family == "S2":
        a = pd.read_parquet(K.R1RUN / market / tf / "all_configs.parquet", columns=["layer", "name"])
        return a[a.layer == "L1"].name.tolist()
    if family == "TEST":                                                       # code test before the lock (no result is read)
        t = ["L1|T_EMAX20_50|long_nat|X0_SIG|-", "L1|T_SMA50|long_con|X2_SIG_SL2|-", "L1|O_RSI14_30_70|long_nat|X5_SIG_SL1.5_TP3|-",
             "L1|T_DONCH20_10|long_nat|X4_SIG_TRAIL3|-", "L1|T_TSMOM20|long_nat|X8_HOLD10_SL2|-", "L1|P_GREEN|long_nat|X7_HOLD1|-",
             "L2|T_SUPER10_3|long_nat|X0_SIG|F1_TREND200", "L3|T_SMA50+T_EMAX20_50|long_nat|X2_SIG_SL2|-",
             "L1|O_WILLR14|long_con|X0_SIG|-", "L2|T_PSAR|long_nat|X2_SIG_SL2|F4_HIGHVOL", "L4|VOTE_TREND_k6of10|long_nat|X6_SIG_SL2_TP2|-"]
        if market == "futures":
            t += ["L1|T_PSAR|short_nat|X6_SIG_SL2_TP2|-", "L1|T_MACD12_26_9sig|short_con|X3_SIG_SL3|-",
                  "L3|T_SMA50+T_TSMOM20|short_nat|X4_SIG_TRAIL3|-"]
        return t
    if family == "CTRL":
        C = K.CFG["controls"]
        neg = [f"NEG|L{L}|s{s}" for L in C["neg_mean_run_bars"] for s in range(C["neg_seeds"])]
        pos = [f"POS|acc{a:.2f}|B{C['pos_block_bars']}|s{s}" for a in C["pos_acc"] for s in range(C["pos_seeds"])]
        return neg + pos
    raise ValueError(family)


def ctrl_state(name, o, seed_key):
    """NEG: random 0/1 runs (geometric, mean L bars). POS: a deliberately look-ahead oracle: blocks of B bars, the block is 'in'
    when its realised trade (open of the bar after the block start -> open of the bar after the block end) goes up, flipped
    with probability 1 - acc. Both use a seed fixed by name, coin and job."""
    rng = np.random.default_rng(zlib.crc32(seed_key.encode()))
    n = len(o)
    p = name.split("|")
    if p[0] == "NEG":
        L = int(p[1][1:])
        flips = rng.random(n) < 1.0 / L
        return (np.cumsum(flips) % 2).astype(np.int8)
    acc, B = float(p[1][3:]), int(p[2][1:])
    st = np.zeros(n, np.int8)
    for j in range(n // B):
        a, b = j * B + 1, (j + 1) * B + 1
        if b >= n:
            break
        up = o[b] > o[a]
        st[j * B:(j + 1) * B] = up if rng.random() < acc else (not up)
    return st


def funding(coin, ts_h, op_h, cl_h):
    f = pd.read_csv(K.PROJ / f"data/futures_um/{coin}_funding.csv")
    tau = pd.to_datetime(f.time, utc=True).values.astype("datetime64[ms]").astype("int64")
    rate = f.funding_rate.values.astype(float)
    keep = (tau >= ts_h[0]) & (tau < HI)
    tau, rate = tau[keep], rate[keep]
    hr = (tau // 3_600_000) * 3_600_000
    i = np.searchsorted(ts_h, hr, side="right") - 1                         # the 1h bar at tau (or the last bar before it)
    exact = ts_h[i] == hr
    px = np.where(exact, op_h[i], np.nan)
    if (~exact).any():                                                      # hour missing: the last close before tau
        px = np.where(exact, px, cl_h[i])
    o = np.argsort(tau, kind="mergesort")
    tau, rate, px = tau[o], rate[o], px[o]
    return (tau, np.r_[0.0, np.cumsum(rate * px)]), int((~exact).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--market", required=True)
    ap.add_argument("--tf", required=True)
    ap.add_argument("--family", required=True)
    ap.add_argument("--max-coins", type=int, default=0)
    ap.add_argument("--coins", default="", help="comma list: only these coins (used to patch a finished job, amendment 1)")
    ap.add_argument("--fix", action="store_true", help="amendment 1: refine_segments (default off = the locked behaviour)")
    ap.add_argument("--xdir", default="xcoin", help="output sub-folder of the run")
    a = ap.parse_args()
    out = Path(a.run) / a.xdir / f"{a.market}_{a.tf}_{a.family}"
    out.mkdir(parents=True, exist_ok=True)
    if (out / "DONE.json").exists():
        print("DONE already"); return
    t0 = time.time()
    names = family_names(a.market, a.tf, a.family)
    nk = len(names)
    coins = coins_for(a.market, a.tf)
    if a.max_coins:
        coins = coins[:a.max_coins]
    if a.coins:
        coins = [c for c in coins if c in set(a.coins.split(","))]
    fee = E.fees()[a.market]
    mmr = study.CFG["futures_mmr"] if a.market == "futures" else 0.0
    rule_meta = {r["id"]: r for r in rules.REG}
    SR = np.zeros((nk, ND)); SR2 = np.zeros((nk, ND)); SEX = np.zeros((nk, ND)); DEN = np.zeros((nk, ND), np.int32)
    BHS = np.zeros(ND); BHD = np.zeros(ND, np.int32)
    rows, crow = [], []
    for ci, coin in enumerate(coins):
        tc = time.time()
        close, qv = K.daily(coin, a.market, LO, HI)
        liq_day = K.liquid_days(qv, X["liquidity_min_usd"], X["liquidity_window_days"]) & np.isfinite(close)
        m = np.zeros(ND)
        m[1:] = close[1:] / close[:-1] - 1
        m[~np.isfinite(m)] = 0.0
        mk = liq_day & np.isfinite(np.r_[np.nan, close[:-1]]) & np.isfinite(close)
        BHS += np.where(mk, m, 0.0); BHD += mk
        segs = segments(a.market, a.tf, coin)
        if a.fix:
            segs = refine_segments(segs, close)
        Lc = np.zeros((nk, ND)); L2c = np.zeros((nk, ND)); Xc = np.zeros((nk, ND))
        st_n = np.zeros(nk, np.int64); st_w = np.zeros(nk, np.int64); st_s = np.zeros(nk); st_first = np.full(nk, np.iinfo(np.int64).max)
        st_last = np.zeros(nk, np.int64); st_dir = np.ones(nk)
        nbars, skipped = 0, []
        fund_missing = 0
        for (s_lo, s_hi) in segs:
            b = K.bars(coin, a.market, a.tf, s_lo, s_hi)
            if len(b) < X["min_bars"]:
                skipped.append(f"{pd.Timestamp(s_lo, unit='ms'):%Y-%m}: {len(b)} bars")
                continue
            nbars += len(b)
            fund = None
            if a.market == "futures":
                h = K.bars(coin, "futures", "1h", s_lo, s_hi)
                fund, fm = funding(coin, h.ts.values, h.open.values, h.close.values)
                fund_missing += fm
            ts = b.ts.values.astype(np.int64)
            o = b.open.values
            liq_bar = liq_day[np.clip(ts // K.DAY - DAY0, 0, ND - 1)].astype(np.int8)
            if a.family != "CTRL":
                out_, x = rules.compute(b, a.tf)
                g = rules.gates(x)
                rows_ = [f"{r}|{s}" for r in out_ for s in "AB"] + [f"{k}|{s}" for k in g for s in "LS"]
                mm = np.empty((len(rows_), len(b)), np.int8)
                i = 0
                for r in out_:
                    mm[i], mm[i + 1] = out_[r]; i += 2
                for k_ in g:
                    mm[i], mm[i + 1] = g[k_]; i += 2
                cfgs = {c["name"]: c for c in study.enumerate_configs(a.market, dict(rows=rows_), rule_meta)}
                atr = x.atr(14).values
                del out_, g
            else:
                atr = rules.atr(b, 14).values
            B = E.Bars(ts, o, b.high.values, b.low.values, b.close.values, atr)
            nxt = np.r_[ts[1:], s_hi]
            barlen = nxt - ts
            study._LAST.clear()
            for k, nm in enumerate(names):
                if a.family == "CTRL":
                    st, gate, dirn, ex = ctrl_state(nm, o, f"{nm}|{coin}|{a.market}|{a.tf}|{s_lo}"), liq_bar, 1, "X0_SIG"
                else:
                    c = cfgs.get(nm)
                    if c is None:                                              # rule not defined on this timeframe
                        continue
                    st = study.state_of(c, mm)
                    gate = liq_bar if c["gate"] == "-" else (np.asarray(mm[c["grow"]]) & liq_bar).astype(np.int8)
                    dirn, ex = c["dir"], c["exit"]
                st_dir[k] = dirn
                T = E.run(B, st, dirn, ex, gate=gate, mmr=mmr)
                n_ = len(T["ei"])
                if not n_:
                    continue
                t_in, t_out = ts[T["ei"]], ts[T["xi"]]
                t_fund = np.where(T["reason"] == 10, t_out + barlen[T["xi"]], t_out)
                gross, fe, fu, net, _, _ = E.pnl(T, dirn, fee, fund, t_in, t_fund)
                add = np.where(np.isin(T["reason"], (3, 5, 7, 9, 11)), barlen[T["xi"]] // 2, np.where(T["reason"] == 10, barlen[T["xi"]] - 1, 0))
                t_oe = t_out + add
                L, Xp, _ = K.mtm(np.zeros(n_, np.int64), t_in, t_oe, T["px_in"], net, np.full(n_, float(dirn)), close, DAY0, 1, ND)
                do = np.minimum(t_oe // K.DAY - DAY0, ND - 1)
                Lc[k] += L[0]; Xc[k] += Xp[0]
                L2c[k] += L[0] + np.bincount(do, weights=np.log1p(np.maximum(net - fe, -0.999999)) - np.log1p(np.maximum(net, -0.999999)),
                                             minlength=ND)
                st_n[k] += n_; st_w[k] += int((net > 0).sum()); st_s[k] += float(net.sum())
                st_first[k] = min(st_first[k], int(t_in.min())); st_last[k] = max(st_last[k], int(t_oe.max()))
        for k in np.nonzero(st_n)[0]:
            r, r2, Xp, dirn = np.expm1(Lc[k]), np.expm1(L2c[k]), Xc[k], st_dir[k]
            den = liq_day | (Xp > 0)
            e = Xp.sum() / max(den.sum(), 1)
            exr = np.where(den, r - e * dirn * m, 0.0)
            SR[k] += r; SR2[k] += r2; SEX[k] += exr; DEN[k] += den
            rd = r[den]
            sd = rd.std(ddof=1) if len(rd) > 1 else np.nan
            rows.append(dict(k=int(k), coin=coin, n=int(st_n[k]), wins=int(st_w[k]), sum_net=float(st_s[k]), equity=float(np.exp(Lc[k].sum())),
                             equity_2xfee=float(np.exp(L2c[k].sum())), expo=float(e), den_days=int(den.sum()),
                             sharpe=float(rd.mean() / sd * np.sqrt(365)) if sd and sd > 0 else np.nan,
                             bh=float(np.prod(1 + m[den]) - 1), first_in=int(st_first[k]), last_out=int(st_last[k])))
        del Lc, L2c, Xc
        crow.append(dict(coin=coin, bars=nbars, segments=len(segs), skipped="; ".join(skipped), funding_px_fallback=fund_missing,
                         liquid_days=int(liq_day.sum()), seconds=round(time.time() - tc, 1)))
        print(f"[{pd.Timestamp.now('UTC'):%H:%M:%S}] {a.market} {a.tf} {a.family}: coin {ci + 1}/{len(coins)} {coin} bars {nbars} "
              f"({time.time() - tc:.1f}s)", flush=True)
    np.savez(out / "acc.npz", names=np.array(names), SR=SR, SR2=SR2, SEX=SEX, DEN=DEN, BHS=BHS, BHD=BHD, day0=DAY0, nd=ND)
    pd.DataFrame(rows).assign(name=lambda d: np.array(names)[d.k.values] if len(d) else []).to_parquet(out / "per_coin.parquet", index=False)
    pd.DataFrame(crow).to_csv(out / "coins.csv", index=False)
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "DONE.json")
    (out / "DONE.json").write_text(json.dumps({p.name: K.sha(p) for p in files} | {
        "finished_utc": pd.Timestamp.now("UTC").isoformat(), "configs": nk, "coins": len(coins), "seconds": round(time.time() - t0),
        "fee_per_side": fee, "fix_amendment1": bool(a.fix), "coins_arg": a.coins}, indent=1))
    print(f"DONE {a.market} {a.tf} {a.family}: {nk} configs x {len(coins)} coins, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
