"""Independent verifier for BTC-ALLTF-R2 (protocol logs/btc_alltf_r2_2026_10_29/R2_PROTOCOL_PREREGISTERED.md, section 9).
Written separately from src/btc_alltf_r2/*.py: own bar loading / resampling, own liquidity rule, own funding, own day-by-day
mark-to-market loop, own Newey-West / BH / walk-forward; the trade replay and the core indicator loops are the ones of the
independent BTC-ALLTF verifier (src/audits/verify_btc_alltf.py, written from the protocol text, never calling engine.run).
Rules outside that core set take their states from src/btc_alltf/rules.py (reported as such: that part is not independent).
Usage:
  python src/audits/verify_btc_alltf_r2.py --run <R2 RUN dir> --part xcoin --job spot:1h:S1 [--configs 3] [--coins all|N]
  python src/audits/verify_btc_alltf_r2.py --run <R2 RUN dir> --part mtm|tests|wf|reentry|r1pos|inputs|mutation|all"""
import argparse
import hashlib
import json
import math
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ / "src/audits"))
sys.path.insert(0, str(PROJ / "src/btc_alltf"))
import verify_btc_alltf as V1                                                 # noqa: E402  (independent replay + core loops)

R2 = PROJ / "logs/btc_alltf_r2_2026_10_29"
RCFG = json.loads((R2 / "R2_CONFIG.json").read_text(encoding="utf-8"))
FEES = json.loads((PROJ / "deploy/fees.json").read_text(encoding="utf-8"))["rules"]
FEE = {"spot": FEES["paper_spot_per_side"], "futures": FEES["paper_futures_taker_per_side"]}
DAY = 86_400_000
XG = RCFG["xcoin"]
LO = int(pd.Timestamp(XG["grid_start"], tz="UTC").value // 10 ** 6)
HI = int(pd.Timestamp(XG["grid_end"], tz="UTC").value // 10 ** 6)
D0 = LO // DAY
NDAYS = (HI - LO) // DAY
CORE = {"T_SMA50", "T_EMAX20_50", "T_MACD12_26_9sig", "O_RSI14_30_70", "O_BB20_2", "T_DONCH20_10", "T_TSMOM20", "T_PSAR", "T_SUPER10_3",
        "P_GREEN"}
RES = []
XD = ["xcoin_v2"]


def check(part, name, cond, msg=""):
    RES.append((part, name, bool(cond), msg))
    print(f"[{'PASS' if cond else 'FAIL'}] {part} {name}: {msg}", flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ own data loading (not common.py)
def to_ms(col):
    s = col.astype(str)
    long_ = s.str.match(r"^\d{5,}-")                                            # a 5+ digit year = the corrupt archive 1m rows
    out = np.zeros(len(s), np.int64)
    if (~long_).any():
        out[~long_.values] = pd.to_datetime(s[~long_], format="ISO8601", utc=True).values.astype("datetime64[ms]").astype("int64")
    if long_.any():                                                           # the archive 1m microsecond rows: seconds count = real ms
        out[long_.values] = np.array(s[long_].str.replace(" ", "T").values, dtype="datetime64[s]").astype("int64")
    return out


def own_source(coin, market, base):
    if market == "futures":
        return PROJ / "data" / "futures_um" / f"{coin}_perp_1h.csv.gz"
    return {"1d": PROJ / "data" / "universe_all" / "1d" / f"{coin}_1d.csv", "1h": PROJ / "data" / "universe_all" / "1h" / f"{coin}_1h_full.csv.gz",
            "15m": PROJ / "data" / "universe_hf" / "15m" / f"{coin}_15m_full.csv.gz", "5m": PROJ / "data" / "universe_hf" / "5m" / f"{coin}_5m_full.csv.gz",
            "1m": PROJ / "archive" / "cleanup_2026_10_15" / "data" / "raw" / f"{coin}_1m_Raw_5Years.csv.gz"}[base]


def own_bars(coin, market, tf, lo, hi):
    base = "1h" if market == "futures" else {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "15m", "1h": "1h", "4h": "1h", "8h": "1h",
                                              "1d": "1d", "1w": "1d"}[tf]
    d = pd.read_csv(own_source(coin, market, base))
    d["t"] = to_ms(d.timestamp)
    d = d.drop_duplicates("t", keep="first").sort_values("t")
    d = d[(d.t >= lo) & (d.t < hi)]
    size = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000, "4h": 14_400_000, "8h": 28_800_000, "1d": DAY}
    if tf == "1w":
        key = (d.t // DAY + 3) // 7                                           # 1970-01-01 was a Thursday: +3 days -> Monday starts
        start = key * 7 * DAY - 3 * DAY
    else:
        key = d.t // size[tf]
        start = key * size[tf]
    if market == "futures":
        d["taker_buy_base"] = (d.taker_buy_quote * d.volume / d.quote_volume.replace(0, np.nan)).fillna(0.0)
    if "quote_volume" not in d:
        d["quote_volume"] = d.volume * d.close
    if "taker_buy_base" not in d:
        d["taker_buy_base"] = np.nan
    g = d.assign(k=key.values, s=start.values).groupby("k")
    out = pd.DataFrame({"ts": g.s.first(), "open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                        "volume": g.volume.sum(), "quote_volume": g.quote_volume.sum(), "taker_buy_base": g.taker_buy_base.sum(min_count=1)})
    return out.reset_index(drop=True)


def own_daily(coin, market):
    if market == "futures":
        d = pd.read_csv(own_source(coin, market, "1h"))
        d["t"] = to_ms(d.timestamp)
        d = d.drop_duplicates("t").sort_values("t")
        d = d[(d.t >= LO) & (d.t < HI)]
        g = d.groupby(d.t // DAY)
        cl, qv = g.close.last(), g.quote_volume.sum()
    else:
        d = pd.read_csv(own_source(coin, market, "1d"))
        d["t"] = to_ms(d.timestamp)
        d = d.drop_duplicates("t").sort_values("t")
        d = d[(d.t >= LO) & (d.t < HI)]
        cl = pd.Series(d.close.values, index=d.t.values // DAY)
        qv = pd.Series(d.quote_volume.values, index=d.t.values // DAY)
    days = np.arange(D0, D0 + NDAYS)
    return cl.reindex(days).values.astype(float), qv.reindex(days).values.astype(float)


def own_liquid(cl, qv):
    w, mn = XG["liquidity_window_days"], XG["liquidity_min_usd"]
    out = np.zeros(len(qv), bool)
    for d in range(w, len(qv)):
        win = qv[d - w:d]
        if np.isfinite(win).all() and win.mean() >= mn and np.isfinite(cl[d]):
            out[d] = True
    return out


def own_funding(coin, lo, hi):
    f = pd.read_csv(PROJ / "data" / "futures_um" / f"{coin}_funding.csv")
    tau = pd.to_datetime(f.time, utc=True).values.astype("datetime64[ms]").astype("int64")
    h = pd.read_csv(own_source(coin, "futures", "1h"))
    h["t"] = to_ms(h.timestamp)
    h = h.drop_duplicates("t").sort_values("t")
    h = h[(h.t >= lo) & (h.t < hi)]
    op = dict(zip(h.t.values, h.open.values))
    tl, cl = h.t.values, h.close.values
    ev = []
    for t_, r_ in zip(tau, f.funding_rate.values):
        if t_ < tl[0] or t_ >= HI:
            continue
        hr = t_ // 3_600_000 * 3_600_000
        if hr in op:
            p = op[hr]
        else:
            i = np.searchsorted(tl, hr, side="right") - 1
            p = cl[i]
        ev.append((t_, r_ * p))
    ev.sort()
    return ev


# ------------------------------------------------------------------ own mark-to-market (day loop)
def own_mtm(trades_ms, close):
    """trades_ms: list of (t_in, t_fill_out, px_in, net, d). returns daily log returns and days in position"""
    cf = close.copy()
    for i in range(1, len(cf)):
        if not np.isfinite(cf[i]):
            cf[i] = cf[i - 1]
    L = np.zeros(NDAYS)
    X = np.zeros(NDAYS)
    for (ti, to, px, net, d) in trades_ms:
        a = ti // DAY - D0
        b = min(to // DAY - D0, NDAYS - 1)
        a = min(a, b)
        prev = 1.0
        for day in range(a, b):
            v = max(1.0 + d * (cf[day] / px - 1.0), 1e-6)
            L[day] += math.log(v) - math.log(prev)
            prev = v
        L[b] += math.log1p(max(net, -0.999999)) - math.log(prev)
        t = ti
        while t < to:
            e = min(to, (t // DAY + 1) * DAY)
            X[t // DAY - D0] += (e - t) / DAY
            t = e
    return L, X


def name_parts(nm):
    layer, rr, ds, ex, gate = nm.split("|")
    dl, side = ds.split("_")
    d = 1 if dl == "long" else -1
    return layer, rr.split("+"), d, side, ex, gate


def own_atr(h, l, c, n=14):
    """Wilder ATR(14) written from the definition (true range, first TR = high - low, smoothing 1/14 from the 14th value)"""
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    return V1.l_ema(tr, alpha=1 / n, minp=n)


def own_states(nm, b, tf, cache):
    """state + filter gate of a config. Core rules: verifier loops; others: rules.py (flagged)"""
    layer, rr, d, side, ex, gate = name_parts(nm)
    arr = 0 if (d > 0) == (side == "nat") else 1
    o, h, l, c = (b[x].tolist() for x in ("open", "high", "low", "close"))
    indep = True
    if "atr" not in cache:
        cache["atr"] = own_atr(h, l, c)
    if "core" not in cache and any(r in CORE for r in rr):
        cache["core"], _ = V1.core_states(o, h, l, c)
    sts = []
    for r in rr:
        if layer == "L4":
            indep = False
            break
        if r in CORE:
            mine = np.array(cache["core"][r][arr], dtype=np.int8)
            if "rules" not in cache:
                import rules as RR
                cache["rules"] = RR.compute(cache["full"], tf)[0]
            theirs = cache["rules"][r][arr]
            diff = np.nonzero(mine != theirs)[0]
            if len(diff):
                marg = np.asarray(cache["core"][r][2], float)[diff]
                if (marg < 1e-9).all():                                       # floating-point ties only (e.g. 50 equal closes = SMA50)
                    cache["ties"] = cache.get("ties", 0) + len(diff)
                    mine = theirs
                else:
                    cache["real_diff"] = cache.get("real_diff", 0) + int((marg >= 1e-9).sum())
            sts.append(mine)
        else:
            indep = False
            if "rules" not in cache:
                import rules as RR
                cache["rules"] = RR.compute(cache["full"], tf)[0]
            sts.append(cache["rules"][r][arr])
    if layer == "L4":
        import rules as RR
        if "rules" not in cache:
            cache["rules"] = RR.compute(cache["full"], tf)[0]
        name, k = rr[0].rsplit("_k", 1)
        k = int(k.split("of")[0])
        mem = {"VOTE_TREND": RR.VOTE_TREND, "VOTE_OSC": RR.VOTE_OSC, "VOTE_ALL24": RR.REPS}[name]
        st = (sum(cache["rules"][m][arr].astype(int) for m in mem) >= k).astype(np.int8)
    else:
        st = sts[0] if len(sts) == 1 else (sts[0] & sts[1]).astype(np.int8)
    g = None
    if gate != "-":
        if gate == "F1_TREND200":
            s200 = V1.l_sma(c, 200)
            g = np.array([(ci > si) if (si == si and d > 0) else ((ci < si) if si == si else False) for ci, si in zip(c, s200)], dtype=np.int8)
            import rules as RR
            if "gates" not in cache:
                cache["gates"] = RR.gates(RR.Ctx(cache["full"]))
            theirs = cache["gates"]["F1_TREND200"][0 if d > 0 else 1]
            diff = np.nonzero(g != theirs)[0]
            if len(diff):
                marg = np.array([abs(c[i] - s200[i]) / c[i] for i in diff])
                if (marg < 1e-9).all():                                       # close == SMA200 up to rounding: a tie
                    cache["ties"] = cache.get("ties", 0) + len(diff)
                    g = theirs
                else:
                    cache["real_diff"] = cache.get("real_diff", 0) + int((marg >= 1e-9).sum())
        else:
            indep = False
            import rules as RR
            if "gates" not in cache:
                cache["gates"] = RR.gates(RR.Ctx(cache["full"]))
            g = cache["gates"][gate][0 if d > 0 else 1]
    return st, g, d, ex, indep


def ctrl_state(name, o, key):
    """controls, written again from protocol 7: NEG = runs flipped with probability 1/L per bar; POS = block oracle"""
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    n = len(o)
    p = name.split("|")
    if p[0] == "NEG":
        L = int(p[1][1:])
        u = rng.random(n)
        st = np.zeros(n, np.int8)
        s = 0
        for i in range(n):
            if u[i] < 1.0 / L:
                s = 1 - s
            st[i] = s
        return st
    acc, B = float(p[1][3:]), int(p[2][1:])
    st = np.zeros(n, np.int8)
    j = 0
    while (j + 1) * B + 1 < n:
        up = o[(j + 1) * B + 1] > o[j * B + 1]
        st[j * B:(j + 1) * B] = int(up) if rng.random() < acc else int(not up)
        j += 1
    return st


def segs_of(market, tf, coin):
    if not (market == "spot" and tf == "1m"):
        return [(LO, HI)]
    m = pd.read_csv(R2 / "universe_1m_months.csv")
    out = []
    for mo in sorted(m[(m.coin == coin) & m.use].month):
        a = int(pd.Timestamp(mo + "-01", tz="UTC").value // 10 ** 6)
        b = int((pd.Timestamp(mo + "-01", tz="UTC") + pd.DateOffset(months=1)).value // 10 ** 6)
        if out and out[-1][1] == a:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


FIX = [True]                                                                   # amendment 1 on (xcoin_v2); --nofix checks the locked xcoin


def own_refine(segs, cl, gap=7):
    """amendment 1 written again: keep only runs of days that have a daily close; a run ends where two consecutive such days are
    more than 7 days apart"""
    have = [i for i in range(len(cl)) if cl[i] == cl[i]]
    if not have:
        return []
    runs, start, prev = [], have[0], have[0]
    for d in have[1:]:
        if d - prev > gap:
            runs.append((start, prev)); start = d
        prev = d
    runs.append((start, prev))
    out = []
    for lo, hi in segs:
        for a, b in runs:
            x, y = max(lo, (D0 + a) * DAY), min(hi, (D0 + b + 1) * DAY)
            if x < y:
                out.append((x, y))
    return out


ties_all, real_all = 0, 0


def replay_coin(nm, market, tf, coin, fee):
    """one (config, coin): own bars -> states -> V1.replay -> net -> own MTM. returns L, X, n, indep"""
    cl, qv = own_daily(coin, market)
    liq = own_liquid(cl, qv)
    trades, indep_all, n_all = [], True, 0
    global ties_all, real_all
    mmr = 0.004 if market == "futures" else 0.0
    sg = segs_of(market, tf, coin)
    if FIX[0]:
        sg = own_refine(sg, cl)
    for (s_lo, s_hi) in sg:
        b = own_bars(coin, market, tf, s_lo, s_hi)
        if len(b) < XG["min_bars"]:
            continue
        ts = b.ts.values.astype(np.int64)
        lb = np.array([liq[min(max(t // DAY - D0, 0), NDAYS - 1)] for t in ts], dtype=np.int8)
        cache = {}
        if nm.startswith(("NEG", "POS")):
            o = b.open.values
            st = ctrl_state(nm, o, f"{nm}|{coin}|{market}|{tf}|{s_lo}")
            g, d, ex, indep = None, 1, "X0_SIG", True
            atr = own_atr(b.high.tolist(), b.low.tolist(), b.close.tolist())
        else:
            cache["full"] = b
            st, g, d, ex, indep = own_states(nm, b, tf, cache)
            atr = cache["atr"]
            ties_all += cache.get("ties", 0)
            real_all += cache.get("real_diff", 0)
        gate = lb if g is None else (lb & g).astype(np.int8)
        tr = V1.replay(b.open.values, b.high.values, b.low.values, b.close.values, np.asarray(atr, float), st.tobytes(), gate.tobytes(), d, ex, mmr)
        nxt = np.r_[ts[1:], s_hi]
        ev = own_funding(coin, s_lo, s_hi) if market == "futures" else []
        evt = np.array([e[0] for e in ev], np.int64)
        evv = np.array([e[1] for e in ev])
        for (eb, xb, r, px, x) in tr:
            R = x / px
            gross = d * (R - 1)
            fe = fee * (1 + R)
            t_in, t_out = int(ts[eb]), int(ts[xb])
            t_f = t_out + (nxt[xb] - ts[xb] if r == 10 else 0)
            fu = 0.0
            if len(evt):
                sel = (evt > t_in) & (evt <= t_f)
                fu = d * evv[sel].sum() / px
            net = gross - fe - fu
            if r == 9:
                net = -1 - fee - fu
            fill = t_out + ((nxt[xb] - ts[xb]) // 2 if r in (3, 5, 7, 9, 11) else ((nxt[xb] - ts[xb]) - 1 if r == 10 else 0))
            trades.append((t_in, fill, px, net, d, fe))
        indep_all &= indep
    return trades, cl, liq, indep_all


def part_xcoin(run, market, tf, family, n_cfg, coins_opt, names_opt=""):
    P = f"xcoin {market} {tf} {family}"
    job = Path(run) / XD[0] / f"{market}_{tf}_{family}"
    A = np.load(job / "acc.npz", allow_pickle=False)
    names = [str(x) for x in A["names"]]
    pc = pd.read_parquet(job / "per_coin.parquet")
    if not len(pc):
        pc = pd.DataFrame(columns=["k", "coin", "n", "equity", "equity_2xfee"])
    coins_run = pd.read_csv(job / "coins.csv").coin.tolist()
    done = json.loads((job / "DONE.json").read_text())
    for f_, h_ in done.items():
        if f_.endswith((".npz", ".parquet", ".csv")):
            check(P, f"sha {f_}", sha(job / f_) == h_, h_[:12])
    fee = FEE[market]
    # configs: core-rule configs first (fully independent), then the others, controls as they come; deterministic
    order = sorted(range(len(names)), key=lambda k: (not all(r in CORE for r in names[k].split("|")[1].split("+")) and
                                                      not names[k].startswith(("NEG", "POS")), k))
    pick = order[:n_cfg]
    if names_opt:
        want = names_opt.split(";")
        pick = [k for k in range(len(names)) if names[k] in want] + [k for k in order[:n_cfg] if names[k] not in want]
    coins = coins_run if coins_opt == "all" else coins_run[:int(coins_opt)]
    full = coins_opt == "all"
    # equal-weight buy-and-hold benchmark of the liquid coins: recomputed from all coins of the run
    if full:
        BHS, BHD = np.zeros(NDAYS), np.zeros(NDAYS)
        for coin in coins_run:
            cl, qv = own_daily(coin, market)
            liq = own_liquid(cl, qv)
            m = np.r_[0.0, cl[1:] / cl[:-1] - 1]
            ok = liq & np.isfinite(m) & np.r_[False, np.isfinite(cl[:-1])]
            BHS += np.where(ok, m, 0.0); BHD += ok
        check(P, "EW buy-and-hold sums (all coins)", np.allclose(BHS, A["BHS"], atol=1e-9) and np.array_equal(BHD, A["BHD"]),
              f"max diff {np.abs(BHS - A['BHS']).max():.2e}")
    for k in pick:
        nm = names[k]
        SR, SR2, SEX, DEN = np.zeros(NDAYS), np.zeros(NDAYS), np.zeros(NDAYS), np.zeros(NDAYS)
        bad, indep_all, cnt = [], True, 0
        global ties_all, real_all
        ties_all, real_all = 0, 0
        for coin in coins:
            trades, cl, liq, indep = replay_coin(nm, market, tf, coin, fee)
            indep_all &= indep
            row = pc[(pc.k == k) & (pc.coin == coin)]
            if not trades:
                if len(row):
                    bad.append(f"{coin}: run has {int(row.n.iloc[0])} trades, replay 0")
                continue
            L, X = own_mtm([t[:5] for t in trades], cl)
            L2, _ = own_mtm([(t[0], t[1], t[2], t[3] - t[5], t[4]) for t in trades], cl)
            n = len(trades)
            if not len(row):
                bad.append(f"{coin}: replay {n} trades, run none"); continue
            r = row.iloc[0]
            eq, eq2 = math.exp(L.sum()), math.exp(L2.sum())
            if r.n != n or abs(eq / r.equity - 1) > 1e-6 or abs(eq2 / r.equity_2xfee - 1) > 1e-6:
                bad.append(f"{coin}: n {int(r.n)}/{n} eq {r.equity:.8g}/{eq:.8g}")
            cnt += 1
            m = np.r_[0.0, cl[1:] / cl[:-1] - 1]
            m[~np.isfinite(m)] = 0.0
            den = liq | (X > 0)
            e = X.sum() / max(den.sum(), 1)
            d = 1 if "|long_" in nm or nm.startswith(("NEG", "POS")) else -1
            rr = np.expm1(L)
            SR += rr; SR2 += np.expm1(L2); SEX += np.where(den, rr - e * d * m, 0.0); DEN += den
        check(P, f"core states = rules.py except floating-point ties, {nm}", real_all == 0, f"tie bars {ties_all}, real differences {real_all}")
        check(P, f"per-coin trades + equity, {nm}", not bad, f"{cnt} coins equal" + ("" if indep_all else " (states from rules.py)") +
              ("; " + "; ".join(bad[:5]) if bad else ""))
        if full:
            ok = np.allclose(SR, A["SR"][k], atol=1e-7) and np.allclose(SR2, A["SR2"][k], atol=1e-7) and \
                np.allclose(SEX, A["SEX"][k], atol=1e-7) and np.array_equal(DEN, A["DEN"][k])
            check(P, f"portfolio sums SR/SR2/SEX/DEN, {nm}", ok, f"max diff SR {np.abs(SR - A['SR'][k]).max():.2e}, "
                  f"SEX {np.abs(SEX - A['SEX'][k]).max():.2e}, DEN {np.abs(DEN - A['DEN'][k]).max():.0f}")


# ------------------------------------------------------------------ V1 inputs
def part_inputs(run):
    P = "inputs"
    lock = (R2 / "R2_PROTOCOL_SHA256.txt").read_text().split("\n")
    lk = {ln.split()[1].lstrip("*").split("/")[-1]: ln.split()[0] for ln in lock if ln and not ln.startswith("locked")}
    for f in ("R2_PROTOCOL_PREREGISTERED.md", "R2_CONFIG.json", "universe_manifest.csv", "universe_1m_months.csv"):
        check(P, f"lock sha {f}", sha(R2 / f) == lk[f], lk[f][:12])
    info = json.loads((Path(run) / "RUN_INFO.json").read_text())
    check(P, "RUN_INFO protocol / config sha = lock", info["protocol_sha256"] == lk["R2_PROTOCOL_PREREGISTERED.md"] and
          info["config_sha256"] == lk["R2_CONFIG.json"], "")
    M = pd.read_csv(R2 / "universe_manifest.csv")
    bad, n = [], 0
    for _, r in M[M.use_1d_1h == True].iterrows():                               # noqa: E712
        for col, base in (("sha_1d", "1d"), ("sha_1h", "1h"), ("sha_15m", "15m"), ("sha_5m", "5m")):
            if col in r and isinstance(r[col], str):
                f = own_source(r.coin, r.market, base if r.market == "spot" else "1h")
                n += 1
                if sha(f) != r[col]:
                    bad.append(f"{r.coin} {base}")
        if r.market == "futures":
            n += 1
            if sha(PROJ / "data" / "futures_um" / f"{r.coin}_funding.csv") != r.sha_funding:
                bad.append(f"{r.coin} funding")
    check(P, "every used coin file = manifest sha", not bad, f"{n} files" + (", bad " + ", ".join(bad[:5]) if bad else ""))
    for d in sorted((Path(run) / XD[0]).glob("*")):
        if (d / "DONE.json").exists():
            fe = json.loads((d / "DONE.json").read_text())["fee_per_side"]
            m = d.name.split("_")[0]
            check(P, f"fee in {d.name} = fees.json", abs(fe - FEE[m]) < 1e-15, f"{fe}")


# ------------------------------------------------------------------ V2 BTC daily MTM
def part_mtm(sample):
    P = "mtm"
    r1 = PROJ / RCFG["r1_run"]
    import pyarrow.parquet as pq
    for market in ("spot", "futures"):
        for tf in RCFG["r1_jobs"][market]:
            Z = np.load(PROJ / "data" / "derived" / "btc_alltf_r2" / "mtm" / f"{market}_{tf}.npz")
            C = pd.read_parquet(r1 / market / tf / "configs.parquet", columns=["cfg", "n", "equity_end", "dir"]).set_index("cfg").loc[Z["cfg"]]
            s = Z["L"].astype(np.float64).sum(1)
            ref = np.log(np.maximum(C.equity_end.values, 1e-300))
            tol = 2e-6 * np.maximum(C.n.fillna(0).values, 1) + 1e-5
            ok = (np.abs(s - ref) <= tol) | (C.equity_end.values <= 1e-6)
            check(P, f"{market} {tf} every config: sum of daily log returns = log equity_end", ok.all(), f"{int(ok.sum())}/{len(ok)}")
            b = pd.read_parquet(PROJ / "data" / "derived" / "btc_alltf" / "bars" / f"{market}_{tf}.parquet", columns=["ts", "open"])
            d1 = pd.read_parquet(PROJ / "data" / "derived" / "btc_alltf" / "bars" / f"{market}_1d.parquet", columns=["ts", "close"])
            day0, nd = int(Z["day0"]), int(Z["nd"])
            cl = pd.Series(d1.close.values, index=d1.ts.values // DAY - day0).reindex(np.arange(nd)).values
            for i in range(1, nd):
                if not np.isfinite(cl[i]):
                    cl[i] = cl[i - 1]
            tsv = b.ts.values
            opv = b.open.values
            rng = np.random.default_rng(zlib.crc32(f"{market}{tf}".encode()))
            nz = np.nonzero((C.n.fillna(0).values > 0) & (C.n.fillna(0).values <= 200_000))[0]
            pickk = rng.choice(nz, size=min(sample, len(nz)), replace=False)
            gend = int(pd.Timestamp(RCFG["btc_grid_end"], tz="UTC").value // 10 ** 6)
            for k in pickk:
                cfg = int(Z["cfg"][k])
                T = pq.read_table(r1 / market / tf / "trades.parquet", columns=["cfg", "t_in", "t_out", "reason", "net"],
                                  filters=[("cfg", "=", cfg)]).to_pandas()
                d = float(C.dir.values[k])
                L = np.zeros(nd)
                tin_ms = T.t_in.values.astype("datetime64[ms]").astype("int64")    # unit-safe (pandas keeps ms or ns depending on version)
                tout_ms = T.t_out.values.astype("datetime64[ms]").astype("int64")
                for ti, to, rs, net in zip(tin_ms, tout_ms, T.reason, T.net.astype(float)):
                    j = np.searchsorted(tsv, to)
                    bl = (tsv[j + 1] if j + 1 < len(tsv) else gend) - tsv[j]
                    fill = to + (bl // 2 if rs in (3, 5, 7, 9, 11) else (bl - 1 if rs == 10 else 0))
                    a_, b_ = ti // DAY - day0, min(fill // DAY - day0, nd - 1)
                    px = opv[np.searchsorted(tsv, ti)]
                    prev = 1.0
                    for day in range(a_, b_):
                        v = max(1.0 + d * (cl[day] / px - 1.0), 1e-6)
                        L[day] += math.log(v) - math.log(prev); prev = v
                    L[b_] += math.log1p(max(net, -0.999999)) - math.log(prev)
                check(P, f"{market} {tf} cfg {cfg}: daily series by loop = stored", np.allclose(L, Z["L"][k].astype(np.float64), atol=2e-6),
                      f"{len(T)} trades, max diff {np.abs(L - Z['L'][k]).max():.1e}")


# ------------------------------------------------------------------ V5 tests
def own_nw(x):
    x = np.asarray(x, float)
    T = len(x)
    lag = int(math.floor(4 * (T / 100.0) ** (2 / 9)))
    u = x - x.mean()
    G = [float(np.dot(u[j:], u[:T - j])) / T for j in range(lag + 1)]
    lrv = G[0] + sum(2 * (1 - j / (lag + 1)) * G[j] for j in range(1, lag + 1))
    t = x.mean() / math.sqrt(lrv / T)
    from scipy.stats import t as td
    return t, float(td.sf(t, T - 1))


def own_bh(p):
    p = list(p)
    n = len(p)
    order = sorted(range(n), key=lambda i: (p[i], i))
    q = [0.0] * n
    run = 1.0
    for rank in range(n, 0, -1):
        i = order[rank - 1]
        run = min(run, p[i] * n / rank)
        q[i] = min(run, 1.0)
    return np.array(q)


def own_perf(r):
    eq = np.cumprod(1 + r)
    dd = 1 - eq / np.maximum.accumulate(np.r_[1.0, eq])[1:]
    sd = r.std(ddof=1)
    return eq[-1] ** (365 / len(r)) - 1 if eq[-1] > 0 else -1.0, (r.mean() / sd * math.sqrt(365)) if sd > 0 else float("nan"), dd.max()


def close_enough(a, b):
    if isinstance(a, float) and isinstance(b, float) and (math.isnan(a) or math.isnan(b)):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= 1e-9 * max(1.0, abs(b))


def part_tests(run):
    P = "tests"
    tdir = Path(run) / "tests"
    subs = [(int(pd.Timestamp(a, tz="UTC").value // 10 ** 6), int(pd.Timestamp(b, tz="UTC").value // 10 ** 6)) for a, b in XG["subperiods"]]
    for fam in ("S1", "S2", "CTRL"):
        f = tdir / f"tests_{fam}.csv"
        if not f.exists():
            continue
        D = pd.read_csv(f)
        bad = []
        for (m, tf), g in D.groupby(["market", "tf"]):
            Z = np.load(Path(run) / XD[0] / f"{m}_{tf}_{fam}" / "acc.npz", allow_pickle=False)
            A = {k: Z[k] for k in Z.files}                                    # read once (Z[k] re-reads the npz each time)
            valid = A["BHD"] > 0
            days = (np.arange(len(valid)) + int(A["day0"]))[valid] * DAY
            bh = (A["BHS"] / np.maximum(A["BHD"], 1))[valid]
            bc, bs, bd = own_perf(bh)
            for _, r in g.iterrows():
                k = int(r.k)
                den = A["DEN"][k]
                rp = np.where(den > 0, A["SR"][k] / np.maximum(den, 1), 0.0)[valid]
                rp2 = np.where(den > 0, A["SR2"][k] / np.maximum(den, 1), 0.0)[valid]
                ex = np.where(den > 0, A["SEX"][k] / np.maximum(den, 1), 0.0)[valid]
                cg, shp, md = own_perf(rp)
                cg2 = own_perf(rp2)[0]
                if rp.std() > 0:
                    tA, pA = own_nw(rp)
                    tB, pB = own_nw(ex)
                else:
                    tA = pA = tB = pB = float("nan")
                sp = [float(np.prod(1 + rp[(days >= a) & (days < b)]) - 1) for a, b in subs]
                want = dict(cagr=cg, sharpe=shp, maxdd=md, cagr_2xfee=cg2, sub1=sp[0], sub2=sp[1], sub3=sp[2], bh_sharpe=bs, bh_maxdd=bd)
                if rp.std() > 0:
                    want.update(tA=tA, pA=pA, tB=tB, pB=pB)
                for c_, v in want.items():
                    if not close_enough(float(r[c_]), float(v)):
                        bad.append(f"{m} {tf} {r['name']} {c_} {r[c_]} vs {v}")
        check(P, f"{fam}: metrics, Newey-West t/p, sub-periods recomputed", not bad, f"{len(D)} rows" + ("; " + "; ".join(bad[:3]) if bad else ""))
        if fam == "S1":
            qa, qb = own_bh(D.pA), own_bh(D.pB)
        elif fam == "S2":
            qa, qb = np.zeros(len(D)), np.zeros(len(D))
            for _, g in D.groupby(["market", "tf"]):
                qa[g.index] = own_bh(g.pA); qb[g.index] = own_bh(g.pB)
        else:
            S1 = pd.read_csv(tdir / "tests_S1.csv")
            qa = np.array([own_bh(list(S1.pA) + [x])[-1] for x in D.pA])
            qb = np.array([own_bh(list(S1.pB) + [x])[-1] for x in D.pB])
        check(P, f"{fam}: BH q recomputed", np.allclose(qa, D.qA, atol=1e-12) and np.allclose(qb, D.qB, atol=1e-12), "")
        rob = (D.subs_pos >= 2) & (D.cagr_2xfee > 0)
        cp = (qa <= 0.05) & rob
        cs = cp & (qb <= 0.05)
        bb = (D.sharpe > D.bh_sharpe) & (D.maxdd < D.bh_maxdd)
        check(P, f"{fam}: labels recomputed", (cp == D.CONFIRMED_PROFIT).all() and (cs == D.CONFIRMED_SKILL).all() and (bb == D.BEATS_BH).all(),
              f"CONFIRMED_PROFIT {int(cp.sum())}, CONFIRMED_SKILL {int(cs.sum())}, BEATS_BH {int(bb.sum())}")


# ------------------------------------------------------------------ V6 walk-forward (primary setting), own implementation
def part_wf(run):
    P = "wf"
    W = RCFG["walk_forward"]
    pr = W["primary"]
    Ofull = pd.read_parquet(Path(run) / "wf" / "wf_oos.parquet")
    O = Ofull[Ofull.setting == "primary"]
    picks = pd.read_csv(Path(run) / "wf" / "wf_picks.csv")
    picks = picks[picks.setting == "primary"]
    o_lo = pd.Timestamp(W["oos_start"], tz="UTC")
    o_hi = pd.Timestamp(W["oos_end"], tz="UTC")
    qs = [q for q in pd.date_range(o_lo, o_hi, freq="QS", tz="UTC") if q < o_hi]
    od0 = int(o_lo.value // 10 ** 6 // DAY)
    for market in ("spot", "futures"):
        cands = {qi: [] for qi in range(len(qs))}
        for tf in RCFG["r1_jobs"][market]:
            Z = np.load(PROJ / "data" / "derived" / "btc_alltf_r2" / "mtm" / f"{market}_{tf}.npz")
            day0 = int(Z["day0"])
            cfg = Z["cfg"]
            names = pd.read_parquet(PROJ / RCFG["r1_run"] / market / tf / "configs.parquet", columns=["cfg", "name"]).set_index("cfg").loc[cfg, "name"].values
            ser = np.zeros((o_hi - o_lo).days)
            prev, mism = {}, 0
            for qi, q in enumerate(qs):
                R = int(q.value // 10 ** 6 // DAY) - day0
                nx = int((qs[qi + 1] if qi + 1 < len(qs) else o_hi).value // 10 ** 6 // DAY) - day0
                a0 = max(R - pr["lookback_days"], 0)
                sel = []
                if R - a0 >= pr["min_lookback_days"]:
                    w = np.expm1(Z["L"][:, a0:R].astype(np.float64))
                    ent = Z["N"][:, a0:R].astype(np.int64).sum(1)
                    mu = w.mean(1); sd = w.std(1, ddof=1)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        sc = mu / sd
                    ok = (ent >= pr["min_entries_in_lookback"]) & (sd > 0) & np.isfinite(sc)
                    cand = sorted([(-sc[i], int(cfg[i]), i) for i in np.nonzero(ok)[0]])[:pr["k"]]
                    sel = [c[2] for c in cand]
                    for c in cand:
                        cands[qi].append((c[0], tf, c[1], np.expm1(Z["L"][c[2], R:nx].astype(np.float64))))
                o0, o1 = R + day0 - od0, nx + day0 - od0
                if sel:
                    ser[o0:o1] = np.expm1(Z["L"][sel, R:nx].astype(np.float64)).mean(0)
                new = {int(cfg[i]): 1 / len(sel) for i in sel}
                turn = sum(abs(new.get(c, 0) - prev.get(c, 0)) for c in set(new) | set(prev))
                ser[o0] = (1 + ser[o0]) * (1 - FEE[market] * turn) - 1
                prev = new
                row = picks[(picks.pool == f"{market}_{tf}") & (picks.quarter == q.strftime("%Y-%m-%d"))]
                want = ";".join(names[i] for i in sel)
                got = row.picks.iloc[0] if len(row) and isinstance(row.picks.iloc[0], str) else ""
                mism += want != got
            g = O[O.pool == f"{market}_{tf}"].sort_values("date").ret.values
            check(P, f"{market} {tf}: picks and OOS series (primary)", mism == 0 and np.allclose(g, ser, atol=1e-12),
                  f"{len(qs)} quarters, pick mismatches {mism}, max diff {np.abs(g - ser).max():.1e}")
        ser = np.zeros((o_hi - o_lo).days)
        prev = {}
        for qi, q in enumerate(qs):
            c = sorted(cands[qi], key=lambda x: (x[0], x[1], x[2]))[:pr["k"]]
            o0 = (q - o_lo).days
            o1 = ((qs[qi + 1] if qi + 1 < len(qs) else o_hi) - o_lo).days
            if c:
                ser[o0:o1] = np.mean([x[3] for x in c], axis=0)
            new = {(x[1], x[2]): 1 / len(c) for x in c}
            turn = sum(abs(new.get(k, 0) - prev.get(k, 0)) for k in set(new) | set(prev))
            ser[o0] = (1 + ser[o0]) * (1 - FEE[market] * turn) - 1
            prev = new
        g = O[O.pool == f"{market}_all"].sort_values("date").ret.values
        check(P, f"{market} all TFs: OOS series (primary)", np.allclose(g, ser, atol=1e-12), f"max diff {np.abs(g - ser).max():.1e}")
    T = pd.read_csv(Path(run) / "tests" / "tests_WF.csv")
    B = pd.read_parquet(Path(run) / "wf" / "wf_btc_series.parquet").set_index("date")
    bad = []
    for _, r in T.iterrows():
        g = Ofull[(Ofull.pool == r.pool) & (Ofull.setting == r.setting)].sort_values("date")
        x = g.ret.values
        bt = np.nan_to_num(B.loc[g.date, "btc_futures" if r.pool.startswith("futures") else "btc_spot"].values)
        if x.std() == 0:
            continue
        tA, pA = own_nw(x)
        tB, pB = own_nw(x - g.expo.values.mean() * bt)
        cg, shp, md = own_perf(x)
        for c_, v in dict(tA=tA, pA=pA, tB=tB, pB=pB, cagr=cg, sharpe=shp, maxdd=md).items():
            if not close_enough(float(r[c_]), float(v)):
                bad.append(f"{r.pool} {r.setting} {c_}")
    prm = T[T.setting == "primary"]
    qa, qb = own_bh(prm.pA), own_bh(prm.pB)
    lab = (qa <= 0.05) & (prm.subs_pos.values >= 2)
    check(P, "WF tests + BH + labels recomputed", not bad and np.allclose(qa, prm.qA) and np.allclose(qb, prm.qB) and
          (lab == prm.WF_PROFIT.values).all() and ((lab & (qb <= 0.05)) == prm.WF_SKILL.values).all(),
          f"{len(T)} rows; WF_PROFIT {int(lab.sum())}, WF_SKILL {int((lab & (qb <= 0.05)).sum())}" + ("; " + "; ".join(bad[:3]) if bad else ""))


# ------------------------------------------------------------------ V7 re-entry, own loop
def replay_reentry(o, h, l, c, atr, st, d, exit_name):
    """written again from protocol section 8 (onset or re-entry after a stop / target / trail exit while the state is still on)"""
    use_sig, slk, tpk, trk, mh = V1.EXITS[exit_name]
    N = len(o)
    out, pos, rebar = [], False, -10
    eb = px = stop = tp = ext = a0 = liq = None
    trail = False
    for t in range(1, N):
        if pos and t > eb and use_sig and st[t - 1] == 0:
            out.append((eb, t, 1, px, o[t])); pos = False
        if not pos:
            s_ = t - 1
            if s_ >= 1 and st[s_] == 1 and (st[s_ - 1] == 0 or s_ == rebar):
                a0 = atr[s_]
                if a0 == a0 and a0 > 0:
                    pos, eb, px = True, t, o[t]
                    stop = px - d * slk * a0 if slk else None
                    tp = px + d * tpk * a0 if tpk else None
                    trail = False
                    if trk:
                        tl = px - d * trk * a0
                        if stop is None or (tl > stop if d > 0 else tl < stop):
                            stop, trail = tl, True
                    ext = px
                    liq = 2 * px / 1.004 if d < 0 else None
        if not pos:
            continue
        op, hi, lo = o[t], h[t], l[t]
        r, x = 0, None
        if d > 0:
            if stop is not None and op <= stop and t > eb:
                r, x = (8 if trail else 4), op
            elif tp is not None and op >= tp and t > eb:
                r, x = 6, op
            elif stop is not None and lo <= stop:
                r, x = (7 if trail else (11 if (tp is not None and hi >= tp) else 3)), stop
            elif tp is not None and hi >= tp:
                r, x = 5, tp
        else:
            if liq is not None and op >= liq and t > eb:
                r, x = 9, op
            elif stop is not None and op >= stop and t > eb:
                r, x = (8 if trail else 4), op
            elif tp is not None and op <= tp and t > eb:
                r, x = 6, op
            elif liq is not None and hi >= liq and (stop is None or stop >= liq):
                r, x = 9, liq
            elif stop is not None and hi >= stop:
                r, x = (7 if trail else (11 if (tp is not None and lo <= tp) else 3)), stop
            elif tp is not None and lo <= tp:
                r, x = 5, tp
        if r:
            out.append((eb, t, r, px, x)); pos = False
            rebar = t if r != 9 else -10
            continue
        if trk:
            if d > 0:
                ext = max(ext, hi); nt = ext - trk * a0
                if nt > stop:
                    stop, trail = nt, True
            else:
                ext = min(ext, lo); nt = ext + trk * a0
                if nt < stop:
                    stop, trail = nt, True
    if pos:
        out.append((eb, N - 1, 10, px, c[N - 1]))
    return out


def part_reentry(run, sample):
    P = "reentry"
    import rules as RR
    for f in sorted((Path(run) / "reentry").glob("reentry_*.parquet")):
        D = pd.read_parquet(f)
        m, tf = f.stem.split("_")[1:3]
        if tf in ("1m", "5m", "15m"):
            continue                                                          # pure-python loop too slow there; same code checked on the other TFs
        b = pd.read_parquet(PROJ / "data" / "derived" / "btc_alltf" / "bars" / f"{m}_{tf}.parquet")
        o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
        core, atr = V1.core_states(o.tolist(), h.tolist(), l.tolist(), c.tolist())
        rr = RR.compute(b, tf)[0]
        fee = FEE[m]
        rng = np.random.default_rng(zlib.crc32(f.name.encode()))
        cand = D[D.rule.isin(CORE) & (D.n_re > 0)]
        sel = cand.iloc[rng.choice(len(cand), size=min(sample, len(cand)), replace=False)]
        fund = None
        if m == "futures":
            f_ = pd.read_parquet(PROJ / "data" / "external" / "binance_public" / "clean" / "funding.parquet")
            tau = f_.time.values.astype("datetime64[ms]").astype("int64")
            m1 = pd.read_parquet(PROJ / "data" / "derived" / "btc_alltf" / "bars" / "futures_1m.parquet", columns=["ts", "open"]).set_index("ts").open
            fund = (tau, f_.funding_rate.values * m1.reindex((tau // 60_000) * 60_000).values)
        ts = b.ts.values
        bad, ties = [], 0
        for _, r in sel.iterrows():
            d = 1 if r.dlabel == "long" else -1
            arr = 0 if (d > 0) == (r.side == "nat") else 1
            st = np.array(core[r.rule][arr], dtype=np.int8)
            diff = np.nonzero(st != rr[r.rule][arr])[0]
            if len(diff):
                if (np.asarray(core[r.rule][2], float)[diff] < 1e-9).all():
                    ties += len(diff); st = rr[r.rule][arr]
                else:
                    bad.append(f"{r['name']}: real state difference")
                    continue
            tr = replay_reentry(o, h, l, c, atr, st, d, r.exit)
            lg = 0.0
            for (eb, xb, rs, px, x) in tr:
                R = x / px
                net = d * (R - 1) - fee * (1 + R)
                if fund is not None:
                    t_f = ts[xb] + ((ts[-1] - ts[-2]) if rs == 10 else 0)
                    msk = (fund[0] > ts[eb]) & (fund[0] <= t_f)
                    net -= d * fund[1][msk].sum() / px
                if rs == 9:
                    net = -1 - fee - (d * fund[1][(fund[0] > ts[eb]) & (fund[0] <= ts[xb])].sum() / px if fund is not None else 0)
                lg += math.log1p(max(net, -0.999999))
            if len(tr) != r.n_re or abs(math.expm1(lg) - r.total_re) > 1e-6 * max(1, abs(r.total_re)):
                bad.append(f"{r['name']}: n {r.n_re}/{len(tr)} total {r.total_re:.6g}/{math.expm1(lg):.6g}")
        check(P, f"{m} {tf}: re-entry replay by own loop", not bad, f"{len(sel)} configs, tie bars {ties}" + ("; " + "; ".join(bad[:3]) if bad else ""))


# ------------------------------------------------------------------ V8 R1 positive control
def part_r1pos(run, sample):
    P = "r1pos"
    D = pd.read_csv(Path(run) / "r1pos" / "r1_poscontrol.csv")
    rng = np.random.default_rng(11)
    sel = D.iloc[rng.choice(len(D), size=min(sample, len(D)), replace=False)]
    bad = []
    S1cfg = json.loads((PROJ / "logs" / "btc_alltf_2026_10_28" / "STUDY_CONFIG.json").read_text())
    PV = int(pd.Timestamp(S1cfg["periods"]["V_start"], tz="UTC").value // 10 ** 6)
    PH = int(pd.Timestamp(S1cfg["periods"]["H_start"], tz="UTC").value // 10 ** 6)
    for _, r in sel.iterrows():
        b = pd.read_parquet(PROJ / "data" / "derived" / "btc_alltf" / "bars" / f"{r.market}_{r.tf}.parquet")
        o, h, l, c = (b[x].values for x in ("open", "high", "low", "close"))
        nm = f"POS|acc{r.acc:.2f}|B{RCFG['controls']['pos_block_bars']}|s{int(r.seed)}"
        st = ctrl_state(nm, o, f"R1POS|{nm}|{r.market}|{r.tf}")
        tr = V1.replay(o, h, l, c, np.ones(len(o)), st.tobytes(), None, 1, "X0_SIG", 0.0)
        fee = FEE[r.market]
        nets = np.array([(x / px - 1) - fee * (1 + x / px) for (_, _, _, px, x) in tr])
        tin = np.array([b.ts.values[t[0]] for t in tr])
        nD, nV, nH = (tin < PV).sum(), ((tin >= PV) & (tin < PH)).sum(), (tin >= PH).sum()
        G1 = bool(nD >= S1cfg["gates"]["G1_nD"] and nV >= S1cfg["gates"]["G1_nV"] and nH >= S1cfg["gates"]["G1_nH"])
        G2 = bool(nets[tin < PV].mean() > 0 and nets[(tin >= PV) & (tin < PH)].mean() > 0 and nets[tin >= PH].mean() > 0)
        if len(nets) != r.n or abs(nets.mean() - r["mean"]) > 1e-9 or G1 != bool(r.G1) or G2 != bool(r.G2):
            bad.append(f"{r.tf} acc {r.acc} s{r.seed}: n {r.n}/{len(nets)} mean {r['mean']:.6g}/{nets.mean():.6g} G1 {r.G1}/{G1} G2 {r.G2}/{G2}")
    gl = ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]
    verdict_ok = (np.where(~D.G1, "INSUFFICIENT", np.where(D[gl].all(1), "PASS", "FAIL")) == D.verdict).all()
    check(P, "oracle trades, mean, G1, G2 by own replay; verdicts from gates", not bad and verdict_ok, f"{len(sel)} sampled" +
          ("; " + "; ".join(bad[:3]) if bad else ""))


def part_mutation(run):
    """a changed number must be caught: copy, change, re-check"""
    import shutil
    import tempfile
    P = "mutation"
    tmp = Path(tempfile.mkdtemp())
    (tmp / "tests").mkdir()
    (tmp / XD[0]).mkdir()
    shutil.copy(Path(run) / "tests" / "tests_S1.csv", tmp / "tests" / "tests_S1.csv")
    T = pd.read_csv(tmp / "tests" / "tests_S1.csv")
    for (m, tf) in T[["market", "tf"]].drop_duplicates().itertuples(index=False):
        shutil.copytree(Path(run) / XD[0] / f"{m}_{tf}_S1", tmp / XD[0] / f"{m}_{tf}_S1")
    T.loc[0, "sharpe"] += 1e-3
    T.to_csv(tmp / "tests" / "tests_S1.csv", index=False)
    n0 = len(RES)
    part_tests(tmp)
    caught = any(not r[2] for r in RES[n0:])
    del RES[n0:]
    check(P, "a changed Sharpe in tests_S1.csv is caught", caught, "")
    T.loc[0, "sharpe"] -= 1e-3
    T.to_csv(tmp / "tests" / "tests_S1.csv", index=False)
    j = tmp / XD[0] / f"{T.market[0]}_{T.tf[0]}_S1" / "acc.npz"
    A = dict(np.load(j, allow_pickle=False))
    A["SR"][int(T.k[0]), 1000] += 0.01
    np.savez(j, **A)
    n0 = len(RES)
    part_tests(tmp)
    caught = any(not r[2] for r in RES[n0:])
    del RES[n0:]
    check(P, "a changed portfolio sum in acc.npz is caught", caught, "")
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--part", default="all")
    ap.add_argument("--job", default="")
    ap.add_argument("--configs", type=int, default=3)
    ap.add_argument("--coins", default="all")
    ap.add_argument("--xdir", default="xcoin_v2")
    ap.add_argument("--names", default="", help="';'-separated config names to verify first")
    ap.add_argument("--nofix", action="store_true")
    a = ap.parse_args()
    XD[0] = a.xdir
    FIX[0] = not a.nofix
    if a.part == "xcoin":
        m, tf, fam = a.job.split(":")
        part_xcoin(a.run, m, tf, fam, a.configs, a.coins, a.names)
    if a.part in ("inputs", "all"):
        part_inputs(a.run)
    if a.part in ("mtm", "all"):
        part_mtm(a.configs)
    if a.part in ("tests", "all"):
        part_tests(a.run)
    if a.part in ("wf", "all"):
        part_wf(a.run)
    if a.part in ("reentry", "all"):
        part_reentry(a.run, a.configs)
    if a.part in ("r1pos", "all"):
        part_r1pos(a.run, a.configs)
    if a.part in ("mutation", "all"):
        part_mutation(a.run)
    n_ok = sum(r[2] for r in RES)
    print(f"\n{n_ok}/{len(RES)} PASS")
    sys.exit(0 if n_ok == len(RES) else 1)


if __name__ == "__main__":
    main()
