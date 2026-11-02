"""Independent verifier for the BTC-ALLTF study (protocol logs/btc_alltf_2026_10_28/BTC_ALLTF_PROTOCOL_PREREGISTERED.md, §8).
Written separately from src/btc_alltf/engine.c and study.py: the core indicators and the trade replay are plain Python loops
written from the protocol text; nothing here calls engine.run.
Usage: python src/audits/verify_btc_alltf.py --run <RUN dir> [--jobs spot:1d futures:4h ...] [--sample 40] [--mutation]
Checks per job:
  V1 inputs: bar file SHA = BARS_MANIFEST, fees in summary = deploy/fees.json, RUN_INFO protocol/config SHA = lock files
  V2 core states (SMA50, EMAX20/50, MACD sig, RSI 30/70, BB20 fade, Donchian 20/10, TSMOM20, PSAR, Supertrend 10/3, green, ATR14)
     recomputed by loops = stored states (a difference only counts as explained if it is a floating-point near-tie)
  V3 replay of a stratified sample of configs (all layers, exits, directions, gates): every trade equal to trades.parquet
     (times, reason, px_in, px_out exact; net |diff| <= 2e-6 after float32 storage)
  V4 every config's n / wins / sum / mean / D-V-H / years / max DD recomputed from trades.parquet (streamed) = configs.parquet
  V5 gates G1-G7, BH q, DSR and verdicts recomputed from the metrics = stored
  V6 daily_groups and monthly totals = trade totals
  V7 every duplicate pair has the same state, gate, direction and exit
  V8 every_bar returns and pass flags recomputed from the bars
  V9 control mean reproduced with the same xorshift64* stream for configs with <= 300k draws"""
import argparse
import array
import hashlib
import json
import math
import random
import shutil
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import norm, t as tdist

PROJ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ / "src/btc_alltf"))
import query as Q                                                             # noqa: E402  (column rebuild; itself checked by V3)

STUDY = PROJ / "logs/btc_alltf_2026_10_28"
CFG = json.loads((STUDY / "STUDY_CONFIG.json").read_text(encoding="utf-8"))
FEES = json.loads((PROJ / "deploy/fees.json").read_text(encoding="utf-8"))["rules"]
FEE = {"spot": FEES["paper_spot_per_side"], "futures": FEES["paper_futures_taker_per_side"]}
DAY = 86_400_000
P_V = int(pd.Timestamp(CFG["periods"]["V_start"], tz="UTC").value // 10 ** 6)
P_H = int(pd.Timestamp(CFG["periods"]["H_start"], tz="UTC").value // 10 ** 6)
EXITS = {"X0_SIG": (1, 0, 0, 0, 0), "X1_SIG_SL1": (1, 1, 0, 0, 0), "X2_SIG_SL2": (1, 2, 0, 0, 0), "X3_SIG_SL3": (1, 3, 0, 0, 0),
         "X4_SIG_TRAIL3": (1, 0, 0, 3, 0), "X5_SIG_SL1.5_TP3": (1, 1.5, 3, 0, 0), "X6_SIG_SL2_TP2": (1, 2, 2, 0, 0),
         "X7_HOLD1": (0, 0, 0, 0, 1), "X8_HOLD10_SL2": (0, 2, 0, 0, 10)}       # written again from protocol §4, not imported
RES = []


def check(job, name, cond, msg):
    RES.append((job, name, bool(cond), msg))
    print(f"[{'PASS' if cond else 'FAIL'}] {job} {name}: {msg}", flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ V2: core indicators as loops
def l_sma(x, n):
    out = [math.nan] * len(x)
    s = 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def l_ema(x, n=None, alpha=None, minp=None):
    a = alpha if alpha is not None else 2.0 / (n + 1)
    minp = minp if minp is not None else n
    out = [math.nan] * len(x)
    y, cnt = None, 0
    for i, v in enumerate(x):
        if v != v:                                                             # NaN: keep the previous value, count nothing
            continue
        y = v if y is None else (1 - a) * y + a * v
        cnt += 1
        if cnt >= minp:
            out[i] = y
    return out


def l_std(x, n):
    out = [math.nan] * len(x)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        m = sum(w) / n
        out[i] = math.sqrt(sum((v - m) ** 2 for v in w) / (n - 1))
    return out


def l_latch(on, off):
    out, s = [], 0
    for a, b in zip(on, off):
        if a:
            s = 1
        elif b:
            s = 0
        out.append(s)
    return out


def gt(a, b):
    return [(x > y) if (x == x and y == y) else False for x, y in zip(a, b)]


def core_states(o, h, l, c):
    """returns {rule: (A, B, margin)} where margin = per-bar |distance to the decision threshold| (near-tie detector)"""
    N = len(c)
    R = {}
    s50 = l_sma(c, 50)
    R["T_SMA50"] = (gt(c, s50), gt(s50, c), [abs(x - y) / x if y == y else 1 for x, y in zip(c, s50)])
    e20, e50 = l_ema(c, 20), l_ema(c, 50)
    R["T_EMAX20_50"] = (gt(e20, e50), gt(e50, e20), [abs(x - y) / c[i] if (x == x and y == y) else 1 for i, (x, y) in enumerate(zip(e20, e50))])
    m = [a - b if (a == a and b == b) else math.nan for a, b in zip(l_ema(c, 12), l_ema(c, 26))]
    sg = l_ema(m, 9)
    R["T_MACD12_26_9sig"] = (gt(m, sg), gt(sg, m), [abs(x - y) / c[i] if (x == x and y == y) else 1 for i, (x, y) in enumerate(zip(m, sg))])
    up = [math.nan] + [max(c[i] - c[i - 1], 0.0) for i in range(1, N)]
    dn = [math.nan] + [max(c[i - 1] - c[i], 0.0) for i in range(1, N)]
    au, ad = l_ema(up, alpha=1 / 14, minp=14), l_ema(dn, alpha=1 / 14, minp=14)
    rsi = [100 - 100 / (1 + a / b) if (a == a and b == b and b != 0) else (100.0 if (a == a and a > 0 and b == 0) else math.nan)
           for a, b in zip(au, ad)]
    A = l_latch([r < 30 for r in rsi], [r > 50 for r in rsi])
    B = l_latch([r > 70 for r in rsi], [r < 50 for r in rsi])
    R["O_RSI14_30_70"] = (A, B, [min(abs(r - 30), abs(r - 50), abs(r - 70)) / 100 if r == r else 1 for r in rsi])
    s20, sd20 = l_sma(c, 20), l_std(c, 20)
    lo2 = [c[i] < s20[i] - 2 * sd20[i] if s20[i] == s20[i] else False for i in range(N)]
    hi2 = [c[i] > s20[i] + 2 * sd20[i] if s20[i] == s20[i] else False for i in range(N)]
    A = l_latch(lo2, [c[i] >= s20[i] if s20[i] == s20[i] else False for i in range(N)])
    B = l_latch(hi2, [c[i] <= s20[i] if s20[i] == s20[i] else False for i in range(N)])
    R["O_BB20_2"] = (A, B, [min(abs(c[i] - s20[i] + 2 * sd20[i]), abs(c[i] - s20[i] - 2 * sd20[i]), abs(c[i] - s20[i])) / c[i]
                            if s20[i] == s20[i] else 1 for i in range(N)])
    def roll(x, n, f, i):
        return f(x[i - n:i]) if i >= n else math.nan
    hn = [roll(h, 20, max, i) for i in range(N)]
    ln = [roll(l, 20, min, i) for i in range(N)]
    hm = [roll(h, 10, max, i) for i in range(N)]
    lm = [roll(l, 10, min, i) for i in range(N)]
    A = l_latch(gt(c, hn), gt(lm, c))
    B = l_latch(gt(ln, c), gt(c, hm))
    R["T_DONCH20_10"] = (A, B, [1] * N)
    mo = [c[i] / c[i - 20] - 1 if i >= 20 else math.nan for i in range(N)]
    R["T_TSMOM20"] = ([x > 0 for x in mo], [x < 0 for x in mo], [abs(x) if x == x else 1 for x in mo])
    # PSAR (Wilder), written from the definition with the same start: up trend, af 0.02 step 0.02 max 0.2, ep = high[0], sar = low[0]
    sar = [math.nan] * N
    upt, af, ep, s = True, 0.02, h[0], l[0]
    for i in range(1, N):
        s = s + af * (ep - s)
        if upt:
            s = min(s, l[i - 1], l[i - 2] if i >= 2 else l[i - 1])
            if l[i] < s:
                upt, s, ep, af = False, ep, l[i], 0.02
            elif h[i] > ep:
                ep, af = h[i], min(0.2, af + 0.02)
        else:
            s = max(s, h[i - 1], h[i - 2] if i >= 2 else h[i - 1])
            if h[i] > s:
                upt, s, ep, af = True, ep, h[i], 0.02
            elif l[i] < ep:
                ep, af = l[i], min(0.2, af + 0.02)
        sar[i] = s
    R["T_PSAR"] = (gt(c, sar), gt(sar, c), [abs(x - y) / x if y == y else 1 for x, y in zip(c, sar)])
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, N)]
    a10 = l_ema(tr, alpha=1 / 10, minp=10)
    d = [0] * N
    fu_p = fl_p = math.nan
    for i in range(N):
        hl2 = (h[i] + l[i]) / 2
        ub, lb = hl2 + 3 * a10[i], hl2 - 3 * a10[i]
        if i == 0 or ub != ub:
            fu_p, fl_p, d[i] = ub, lb, 0
            continue
        fu = ub if (fu_p != fu_p or ub < fu_p or c[i - 1] > fu_p) else fu_p
        fl = lb if (fl_p != fl_p or lb > fl_p or c[i - 1] < fl_p) else fl_p
        prev = d[i - 1] if d[i - 1] != 0 else 1
        d[i] = 0 if fu_p != fu_p else (1 if c[i] > fu_p else (-1 if c[i] < fl_p else prev))
        fu_p, fl_p = fu, fl
    R["T_SUPER10_3"] = ([x == 1 for x in d], [x == -1 for x in d], [1] * N)
    R["P_GREEN"] = (l_latch([c[i] > o[i] for i in range(N)], [c[i] < o[i] for i in range(N)]),
                    l_latch([c[i] < o[i] for i in range(N)], [c[i] > o[i] for i in range(N)]), [1] * N)
    atr14 = l_ema(tr, alpha=1 / 14, minp=14)
    return R, atr14


# ------------------------------------------------------------------ V3: replay written from protocol §5
def replay(o, h, l, c, atr, st, gate, d, exit_name, mmr):
    use_sig, slk, tpk, trk, mh = EXITS[exit_name]
    N = len(o)
    sa = np.frombuffer(st, dtype=np.uint8)
    on_ = np.nonzero((sa[1:] == 1) & (sa[:-1] == 0))[0] + 1
    if gate is not None:
        on_ = on_[np.frombuffer(gate, dtype=np.uint8)[on_] == 1]
    onset = on_.tolist()
    ons = set(onset)
    trades = []
    pos = False
    t = 1
    oi = 0
    while t < N:
        if not pos:
            while oi < len(onset) and onset[oi] + 1 < t:
                oi += 1
            if oi >= len(onset):
                break
            t = max(t, onset[oi] + 1)
            if t >= N:
                break
        # exits at this open
        if pos and t > eb:
            r = 0
            if use_sig and st[t - 1] == 0:
                r = 1
            elif mh and t - eb >= mh:
                r = 2
            if r:
                trades.append((eb, t, r, px, o[t])); pos = False
        if not pos and (t - 1) in ons:
            a0 = atr[t - 1]
            if not ((slk or tpk or trk) and not (a0 == a0 and a0 > 0)):
                pos, eb, px = True, t, o[t]
                stop = px - d * slk * a0 if slk else None
                tp = px + d * tpk * a0 if tpk else None
                trail_flag = False
                if trk:
                    tl = px - d * trk * a0
                    if stop is None or (tl > stop if d > 0 else tl < stop):
                        stop, trail_flag = tl, True
                ext = px
                liq = 2 * px / (1 + mmr) if (d < 0 and mmr > 0) else None
        if not pos:
            t += 1
            continue
        op, hi, lo = o[t], h[t], l[t]
        r, x = 0, None
        if d > 0:
            if stop is not None and op <= stop and t > eb:
                r, x = (8 if trail_flag else 4), op
            elif tp is not None and op >= tp and t > eb:
                r, x = 6, op
            elif stop is not None and lo <= stop:
                r, x = (7 if trail_flag else (11 if (tp is not None and hi >= tp) else 3)), stop
            elif tp is not None and hi >= tp:
                r, x = 5, tp
        else:
            if liq is not None and op >= liq and t > eb:
                r, x = 9, op
            elif stop is not None and op >= stop and t > eb:
                r, x = (8 if trail_flag else 4), op
            elif tp is not None and op <= tp and t > eb:
                r, x = 6, op
            elif liq is not None and hi >= liq and (stop is None or stop >= liq):
                r, x = 9, liq
            elif stop is not None and hi >= stop:
                r, x = (7 if trail_flag else (11 if (tp is not None and lo <= tp) else 3)), stop
            elif tp is not None and lo <= tp:
                r, x = 5, tp
        if r:
            trades.append((eb, t, r, px, x)); pos = False
            t += 1
            continue
        if trk:
            if d > 0:
                ext = max(ext, hi)
                nt = ext - trk * a0
                if nt > stop:
                    stop, trail_flag = nt, True
            else:
                ext = min(ext, lo)
                nt = ext + trk * a0
                if nt < stop:
                    stop, trail_flag = nt, True
        t += 1
    if pos:
        trades.append((eb, N - 1, 10, px, c[N - 1]))
    return trades


def xorshift_ctrl(o, cf, lo_, hi_, d, holds, reps, seed, f):
    M = (1 << 64) - 1
    x = seed if seed else 88172645463325252
    s = s2 = 0.0
    cnt = 0
    for _ in range(reps):
        for hj in holds:
            hj = max(1, int(hj))
            span = hi_ - hj - lo_
            if span <= 0:
                continue
            x ^= x >> 12; x ^= (x << 25) & M; x ^= x >> 27
            z = (x * 2685821657736338717) & M
            e = lo_ + z % span
            R = o[e + hj] / o[e]
            v = d * (R - 1) - f - f * R - d * (cf[e + hj] - cf[e])
            s += v; s2 += v * v; cnt += 1
    mu = s / cnt
    return mu, math.sqrt((s2 - cnt * mu * mu) / (cnt - 1)), cnt


# ------------------------------------------------------------------ helpers
def load_job(run, m, tf):
    job = run / m / tf
    cf = pd.read_parquet(job / "configs.parquet")
    b = pd.read_parquet(PROJ / f"data/derived/btc_alltf/bars/{m}_{tf}.parquet", columns=["ts", "open", "high", "low", "close"])
    ix = json.loads((PROJ / f"data/derived/btc_alltf/states/{m}_{tf}.json").read_text())
    mm = np.memmap(PROJ / f"data/derived/btc_alltf/states/{m}_{tf}.int8", dtype=np.int8, mode="r", shape=(len(ix["rows"]), len(b)))
    return job, cf, b, ix, mm


def cfg_state(row, ix, mm):
    rows = {r: k for k, r in enumerate(ix["rows"])}
    arr = "A" if (row.dir > 0) == (row.side == "nat") else "B"
    if row.layer == "L3":
        return (np.asarray(mm[rows[f"{row.rule}|{arr}"]]) & np.asarray(mm[rows[f"{row.rule2}|{arr}"]])).astype(np.int8)
    if row.layer == "L4":
        name, k = row.rule.rsplit("_k", 1)
        k = int(k.split("of")[0])
        import rules as RR                                                     # only the member lists
        mem = {"VOTE_TREND": RR.VOTE_TREND, "VOTE_OSC": RR.VOTE_OSC, "VOTE_ALL24": RR.REPS}[name]
        tot = sum(np.asarray(mm[rows[f"{r}|{arr}"]]).astype(int) for r in mem)
        return (tot >= k).astype(np.int8)
    return np.asarray(mm[rows[f"{row.rule}|{arr}"]])


def gate_of(row, ix, mm):
    if row.gate == "-":
        return None
    rows = {r: k for k, r in enumerate(ix["rows"])}
    return np.asarray(mm[rows[f"{row.gate}|{'L' if row.dir > 0 else 'S'}"]])


def stream_cfg_groups(path, cols):
    """yield (cfg, DataFrame of its trades) in file order; trades of one cfg are contiguous"""
    pf = pq.ParquetFile(path)
    carry = None
    for i in range(pf.num_row_groups):
        t = pf.read_row_group(i, columns=cols).to_pandas()
        if carry is not None:
            t = pd.concat([carry, t], ignore_index=True)
        last = t.cfg.iloc[-1]
        carry = t[t.cfg == last]
        t = t[t.cfg != last]
        for k, g in t.groupby("cfg", sort=False):
            yield k, g
    if carry is not None and len(carry):
        yield carry.cfg.iloc[0], carry


# ------------------------------------------------------------------ per job
def verify_job(run, m, tf, sample, rng):
    J = f"{m}:{tf}"
    job, cf, b, ix, mm = load_job(run, m, tf)
    S = json.loads((job / "summary.json").read_text())
    man = pd.read_csv(PROJ / "data/derived/btc_alltf/bars/BARS_MANIFEST.csv")
    want = man[(man.market == m) & (man.tf == tf)].sha256.iloc[0]
    check(J, "V1 bars sha", sha(PROJ / f"data/derived/btc_alltf/bars/{m}_{tf}.parquet") == want, want[:12])
    check(J, "V1 fee", abs(S["fee_per_side"] - FEE[m]) < 1e-15, f"{S['fee_per_side']} vs fees.json {FEE[m]}")
    o, h, l, c = (array.array("d", b[k].values.astype(float)) for k in ("open", "high", "low", "close"))   # compact Python arrays
    N = len(c)
    # ---- V2
    lim = N if N <= 400_000 else 400_000                                       # long series (5m, 1m): the first 400k bars (RAM / time)
    R, atr14 = core_states(o[:lim].tolist(), h[:lim].tolist(), l[:lim].tolist(), c[:lim].tolist())
    rows = {r: k for k, r in enumerate(ix["rows"])}
    for rid, (A, B, marg) in R.items():
        if f"{rid}|A" not in rows:
            continue
        for side, arr in (("A", A), ("B", B)):
            st = np.asarray(mm[rows[f"{rid}|{side}"]][:lim])
            mine = np.asarray(arr, dtype=np.int8)
            diff = np.nonzero(st != mine)[0]
            # a difference is explained only if the decision bar where the two first part is a floating-point near-tie
            unexpl = []
            for i in diff[:200]:
                j = i
                while j > 0 and (st[j - 1] != mine[j - 1]):
                    j -= 1
                if not (marg[j] < 1e-9):
                    unexpl.append(int(i))
            check(J, f"V2 {rid}|{side}", len(unexpl) == 0, f"{lim:,} bars, differences {len(diff)}, unexplained {len(unexpl)} {unexpl[:3]}")
    atr_s = np.load(PROJ / f"data/derived/btc_alltf/states/{m}_{tf}_atr14.npy")[:lim]
    a2 = np.array(atr14)
    okm = np.isfinite(a2) & np.isfinite(atr_s)
    check(J, "V2 ATR14", np.array_equal(np.isfinite(a2), np.isfinite(atr_s)) and (np.abs(a2[okm] - atr_s[okm]) <= 1e-9 * np.abs(a2[okm]) + 1e-12).all(),
          f"max rel diff {np.max(np.abs(a2[okm] - atr_s[okm]) / np.abs(a2[okm])) if okm.any() else 0:.2e}")
    # ---- V3 replay (stratified sample: every layer x exit x direction present, then random)
    cf_run = cf[cf.n > 0]
    strata = cf_run.groupby(["layer", "exit", "dir"], sort=False)
    pick = [g.sample(1, random_state=rng.randint(0, 10 ** 6)).cfg.iloc[0] for _, g in strata]
    rest = cf_run[~cf_run.cfg.isin(pick)]
    pick += list(rest.sample(min(len(rest), max(0, sample - len(pick))), random_state=rng.randint(0, 10 ** 6)).cfg)
    bmin = pd.read_parquet(PROJ / f"data/derived/btc_alltf/bars/{m}_{tf}.parquet", columns=["ts", "open", "high", "low", "close"])
    fund = Q.funding(m)
    atr_full = array.array("d", np.load(PROJ / f"data/derived/btc_alltf/states/{m}_{tf}_atr14.npy"))
    mmr = CFG["futures_mmr"] if m == "futures" else 0.0
    n_tr, bad = 0, []
    import pyarrow.dataset as ds
    dset = ds.dataset(job / "trades.parquet")
    for cid in pick:
        row = cf[cf.cfg == cid].iloc[0]
        st = bytes(cfg_state(row, ix, mm).astype(np.uint8))
        g = gate_of(row, ix, mm)
        mine = replay(o, h, l, c, atr_full, st, None if g is None else bytes(g.astype(np.uint8)), int(row.dir), row.exit, mmr)
        tr = dset.to_table(filter=ds.field("cfg") == int(cid)).to_pandas()
        x = Q.expand(tr, m, tf, cf[["cfg", "name", "dir"]], b=bmin, fund=fund)
        n_tr += len(mine)
        ts = bmin.ts.values
        if len(mine) != len(x):
            bad.append((int(cid), "count", len(mine), len(x))); continue
        TI = x.t_in.values.astype("datetime64[ms]").astype("int64")              # arrays once, not inside the loop
        TO = x.t_out.values.astype("datetime64[ms]").astype("int64")
        RS, PI, PO = x.reason.values, x.px_in.values, x.px_out.values
        FU, NT, WN = x.funding.values, x.net.values, x.win.values
        for k, (eb, xb, r, pi, po) in enumerate(mine):
            if ts[eb] != TI[k] or ts[xb] != TO[k] or r != RS[k] or pi != PI[k] or abs(po - PO[k]) > 1e-9 * po:
                bad.append((int(cid), k, "trade", (eb, xb, r, pi, po), (TI[k], TO[k], RS[k], PI[k], PO[k])))
                break
            # net from first principles: gross - fee*(1+R) - funding (liquidation: -1 - fee - funding)
            R_ = po / pi
            fu = float(FU[k])
            net = (-1 - FEE[m] - fu) if r == 9 else int(row.dir) * (R_ - 1) - FEE[m] * (1 + R_) - fu
            if abs(net - float(NT[k])) > 2e-6 or (WN[k] == 1) != (NT[k] > 0):
                bad.append((int(cid), k, "net", net, float(NT[k]))); break
    check(J, "V3 replay", not bad, f"{len(pick)} configs, {n_tr:,} trades replayed, mismatches {bad[:2]}")
    # funding itself, recomputed by a direct loop for a few futures trades
    if m == "futures" and fund is not None:
        fr = pd.read_parquet(PROJ / CFG["inputs"]["funding"])
        m1 = pd.read_parquet(PROJ / "data/derived/btc_alltf/bars/futures_1m.parquet", columns=["ts", "open"]).set_index("ts").open
        tau = fr.time.values.astype("datetime64[ms]").astype("int64")
        tr = dset.to_table(filter=ds.field("cfg") == int(pick[0])).to_pandas().head(300)
        x = Q.expand(tr, m, tf, cf[["cfg", "name", "dir"]], b=bmin, fund=fund)
        errs = 0
        for k in range(len(x)):
            ti = int(x.t_in.values.astype("datetime64[ms]").astype("int64")[k]); to = int(x.t_out.values.astype("datetime64[ms]").astype("int64")[k])
            if x.reason.values[k] == 10:
                to += int(bmin.ts.values[-1] - bmin.ts.values[-2])
            sel = (tau > ti) & (tau <= to)
            fu = int(x.dir.values[k]) * float((fr.funding_rate.values[sel] * m1.loc[(tau[sel] // 60000) * 60000].values).sum()) / x.px_in.values[k]
            errs += abs(fu - x.funding.values[k]) > 1e-12
        check(J, "V3 funding loop", errs == 0, f"{len(x)} trades, errors {errs}")
    # ---- V4 metrics from the stored trades (streamed), V6 daily / monthly totals
    stored = cf.set_index("cfg")
    tot_net, mism, nseen = 0.0, [], 0
    years = sorted(int(cn[2:]) for cn in cf.columns if cn.startswith("n_2"))
    for cid, g in stream_cfg_groups(job / "trades.parquet", ["cfg", "t_in", "net", "win"]):
        nseen += 1
        net = g.net.values.astype(np.float64)
        ti = g.t_in.values.astype("datetime64[ms]").astype("int64")
        tot_net += net.sum()
        s = stored.loc[cid]
        n = len(net)
        tol = 2e-6 * n + 1e-9
        eq = np.cumprod(np.maximum(1 + net, 0))
        mdd = float((1 - eq / np.maximum.accumulate(np.r_[1.0, eq])[1:]).max())
        yr = pd.to_datetime(ti, unit="ms", utc=True).year.values
        dv = ti < P_V
        hv = ti >= P_H
        vv = ~dv & ~hv
        conds = [s.n == n, s.wins == int((net > 0).sum()), int(g.win.sum()) == int((net > 0).sum()), abs(s["sum"] - net.sum()) <= tol,
                 abs(s["mean"] - net.mean()) <= 2e-6, s.n_D == dv.sum(), s.n_V == vv.sum(), s.n_H == hv.sum(),
                 abs(s.sum_D - net[dv].sum()) <= tol, abs(s.sum_H - net[hv].sum()) <= tol, abs(s.max_dd - mdd) <= 1e-4]
        conds += [s[f"n_{y}"] == (yr == y).sum() and abs(s[f"sum_{y}"] - net[yr == y].sum()) <= tol for y in years]
        if not all(conds):
            mism.append((int(cid), [i for i, v in enumerate(conds) if not v]))
    nz = int((cf.n > 0).sum())
    check(J, "V4 metrics from trades", not mism and nseen == nz, f"{nseen:,} configs with trades (table {nz:,}), mismatches {len(mism)} {mism[:3]}")
    dg = pd.read_parquet(job / "daily_groups.parquet")
    check(J, "V6 daily_groups total = trades", abs(dg.sum_net.sum() - tot_net) <= 1e-6 * max(1, abs(tot_net)) + 1e-3 and dg.n_closed.sum() == int(cf.n.sum())
          and dg.n_opened.sum() == int(cf.n.sum()), f"daily {dg.sum_net.sum():.4f} vs trades {tot_net:.4f}; n {dg.n_closed.sum():,} vs {int(cf.n.sum()):,}")
    mo = pd.read_parquet(job / "monthly.parquet")
    msum = mo.groupby("cfg").sum_net.sum()
    s2 = stored.loc[msum.index, "sum"]
    check(J, "V6 monthly = configs", len(msum) == nz and np.allclose(msum.values, s2.values, atol=1e-6, rtol=1e-9) and mo.n.sum() == int(cf.n.sum()),
          f"{len(msum):,} configs")
    dov = pd.read_csv(job / "daily_overview.csv")
    nd = (pd.Timestamp(dov.date.iloc[-1]) - pd.Timestamp(dov.date.iloc[0])).days + 1
    check(J, "V6 daily_overview every calendar day", len(dov) == nd and dov.date.iloc[-1] == CFG["periods"]["H_end"] and dov.n_closed.sum() == int(cf.n.sum()),
          f"{len(dov)} rows, {nd} days, {dov.date.iloc[0]} .. {dov.date.iloc[-1]}")
    # ---- V5 gates
    gc = CFG["gates"]
    g1 = (cf.n_D >= gc["G1_nD"]) & (cf.n_V >= gc["G1_nV"]) & (cf.n_H >= gc["G1_nH"])
    g2 = (cf.mean_D > 0) & (cf.mean_V > 0) & (cf.mean_H > 0)
    p = cf.p.fillna(1.0).values
    order = np.argsort(p)
    q = np.empty(len(p))
    run_min = 1.0
    for rank_i in range(len(p) - 1, -1, -1):
        idx = order[rank_i]
        run_min = min(run_min, p[idx] * len(p) / (rank_i + 1))
        q[idx] = min(run_min, 1.0)
    g3 = q <= gc["G3_q"]
    tt = cf["mean"] / (cf.sd / np.sqrt(cf.n))
    pp = np.where(np.isfinite(tt) & (cf.n > 1), tdist.sf(tt, cf.n - 1), 1.0)
    g4 = cf.ctrl_z >= gc["G4_z"]
    yn = cf[[f"n_{y}" for y in years]].values
    ys = cf[[f"sum_{y}" for y in years]].values
    el = yn >= gc["G6_min_trades_year"]
    g6 = (el.sum(1) >= gc["G6_min_years"]) & (((ys > 0) & el).sum(1) >= np.ceil(gc["G6_share"] * el.sum(1)))
    ok30 = (cf.n >= 30) & (cf.sd > 0)
    V = float(np.var((cf["mean"] / cf.sd)[ok30], ddof=0))
    Nt = len(cf)
    sr = cf["mean"] / cf.sd
    em = 0.5772156649
    sr0 = math.sqrt(V) * ((1 - em) * norm.ppf(1 - 1 / Nt) + em * norm.ppf(1 - 1 / (Nt * math.e)))
    den = 1 - cf["skew"].fillna(0) * sr + (cf["kurt"].fillna(3) - 1) / 4 * sr ** 2
    dsr = pd.Series(np.where(ok30 & (den > 0), norm.cdf((sr - sr0) * np.sqrt(cf.n - 1) / np.sqrt(den.where(den > 0))), np.nan))
    g7 = dsr >= gc["G7_dsr"]
    g5 = (cf.mean_H_2xfee > 0) & (cf.mean_H_delay1 > 0)
    allg = g1 & g2 & g3 & g4 & g5 & g6 & g7
    verdict = np.where(~g1, "INSUFFICIENT", np.where(allg, "PASS", "FAIL"))
    check(J, "V5 p-values", np.allclose(pp, cf.p.fillna(1.0).values, atol=1e-9), "")
    check(J, "V5 BH q", np.allclose(q, cf.q_bh.values, atol=1e-12), "")
    check(J, "V5 DSR", np.allclose(dsr.values, cf.dsr.values, atol=1e-9, equal_nan=True), "")
    for nm_, mine in (("G1", g1), ("G2", g2), ("G3", g3), ("G4", g4), ("G5", g5), ("G6", g6), ("G7", g7)):
        check(J, f"V5 {nm_}", np.array_equal(np.asarray(mine, bool), cf[nm_].values.astype(bool)), f"{int(np.sum(mine))} pass")
    check(J, "V5 verdict", np.array_equal(verdict, cf.verdict.values), str(pd.Series(verdict).value_counts().to_dict()))
    cand = g1 & g2 & g3 & g4 & (cf.mean_H_2xfee > 0)
    check(J, "V5 delay re-run only for candidates", cf.mean_H_delay1.notna().sum() <= int(cand.sum()), f"{int(cand.sum())} candidates")
    # ---- V7 duplicates: rebuild both states (and gates) from all_configs.parquet and compare
    dup = pd.read_csv(job / "duplicates.csv")
    if len(dup):
        allc = pd.read_parquet(job / "all_configs.parquet").set_index("cfg")
        bad7 = []
        for _, r in dup.sample(min(len(dup), 300), random_state=1).iterrows():
            a_, b_ = allc.loc[r.cfg], allc.loc[r.same_as_cfg]
            sa, sb = cfg_state(a_, ix, mm), cfg_state(b_, ix, mm)
            ga, gb = gate_of(a_, ix, mm), gate_of(b_, ix, mm)
            same_g = (ga is None and gb is None) or (ga is not None and gb is not None and np.array_equal(ga, gb))
            if not (np.array_equal(sa, sb) and same_g and a_.dir == b_.dir and a_.exit == b_.exit and r.same_as_cfg in stored.index):
                bad7.append(int(r.cfg))
        check(J, "V7 duplicates identical", not bad7, f"{len(dup)} duplicates, checked {min(len(dup), 300)}, bad {bad7[:3]}")
    # ---- V8 every bar
    eb = pd.read_parquet(job / "every_bar.parquet")
    oo = b.open.values
    cfb = np.zeros(N)
    if m == "futures":
        fr = pd.read_parquet(PROJ / CFG["inputs"]["funding"])
        tau = fr.time.values.astype("datetime64[ms]").astype("int64")
        cr = np.r_[0.0, np.cumsum(fr.funding_rate.values)]
        cfb = cr[np.searchsorted(tau, b.ts.values, side="right")]
    ok8 = True
    for hh in CFG["every_bar_holds"]:
        if N <= hh:
            continue
        Rr = oo[hh:] / oo[:-hh]
        fl = cfb[hh:] - cfb[:-hh]
        ok8 &= np.allclose(eb[f"r{hh}"].values[:-hh], (Rr - 1).astype(np.float32), atol=1e-7)
        ok8 &= np.array_equal(eb[f"pass_long{hh}"].values[:-hh], ((Rr - 1) - FEE[m] * (1 + Rr) - fl > 0).astype(np.int8))
        ok8 &= np.array_equal(eb[f"pass_short{hh}"].values[:-hh], ((1 - Rr) - FEE[m] * (1 + Rr) + fl > 0).astype(np.int8))
    check(J, "V8 every_bar", ok8 and len(eb) == N, f"{N:,} bars")
    # ---- V9 control (configs with small draw counts)
    small = cf[(cf.n > 0) & (cf.ctrl_n <= 300_000)]
    if len(small):
        cfb_full = cfb
        if m == "futures":
            pass
        rr = small.sample(min(3, len(small)), random_state=2)
        ok9 = True
        for _, row in rr.iterrows():
            tr = dset.to_table(filter=ds.field("cfg") == int(row.cfg)).to_pandas()
            x = Q.expand(tr, m, tf, cf[["cfg", "name", "dir"]], b=bmin, fund=fund)
            reps = int(min(CFG["control"]["max_reps"], max(CFG["control"]["min_reps"], math.ceil(CFG["control"]["target_draws"] / len(x)))))
            seed = zlib.crc32(f"{m}|{tf}|{row['name']}".encode())
            mu, sd, cn = xorshift_ctrl(oo, cfb_full, 0, N, int(row.dir), np.maximum(x.bars.values, 1), reps, seed, FEE[m])
            ok9 &= abs(mu - row.ctrl_mean) <= 1e-9 and cn == row.ctrl_n
        check(J, "V9 control reproduced", ok9, f"{len(rr)} configs")
    return tot_net


def mutation(run, m, tf):
    """a changed net in a copy of the trade log must be caught by V4; a flipped state bar must be caught by V3"""
    job = run / m / tf
    tmp = Path(tempfile.mkdtemp())
    try:
        t = pq.read_table(job / "trades.parquet").to_pandas()
        k = len(t) // 2
        t.loc[k, "net"] = np.float32(t.loc[k, "net"] + 0.01)
        cf = pd.read_parquet(job / "configs.parquet").set_index("cfg")
        g = t[t.cfg == t.cfg.iloc[k]].net.astype(np.float64)
        caught4 = abs(cf.loc[t.cfg.iloc[k], "sum"] - g.sum()) > 2e-6 * len(g) + 1e-9
        check(f"{m}:{tf}", "MUTATION net changed -> V4 catches", caught4, f"cfg {t.cfg.iloc[k]}")
        _, cfx, b, ix, mm = load_job(run, m, tf)
        row = cfx[(cfx.n > 5) & (cfx.layer == "L1") & (cfx.exit == "X0_SIG")].iloc[0]
        st = np.array(cfg_state(row, ix, mm))
        on = np.nonzero((st[1:] == 1) & (st[:-1] == 0))[0] + 1
        st[on[0]] = 0
        st[on[0] + 1:on[0] + 2] = 0
        o, h, l, c = (array.array("d", b[k_].values.astype(float)) for k_ in ("open", "high", "low", "close"))
        atr = array.array("d", np.load(PROJ / f"data/derived/btc_alltf/states/{m}_{tf}_atr14.npy"))
        mine = replay(o, h, l, c, atr, bytes(st.astype(np.uint8)), None, int(row.dir), row.exit, 0.004 if m == "futures" else 0)
        import pyarrow.dataset as ds
        tr = ds.dataset(job / "trades.parquet").to_table(filter=ds.field("cfg") == int(row.cfg)).to_pandas()
        caught3 = len(mine) != len(tr) or b.ts.values[mine[0][0]] != tr.t_in.values.astype("datetime64[ms]").astype("int64")[0]
        check(f"{m}:{tf}", "MUTATION state changed -> V3 catches", caught3, f"cfg {row.cfg}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--jobs", nargs="*")
    ap.add_argument("--sample", type=int, default=40)
    ap.add_argument("--mutation", action="store_true")
    a = ap.parse_args()
    run = Path(a.run)
    info = json.loads((run / "RUN_INFO.json").read_text())
    lock = (STUDY / "BTC_ALLTF_PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0]
    check("run", "V1 protocol lock", info["protocol_lock"] == lock == sha(STUDY / "BTC_ALLTF_PROTOCOL_PREREGISTERED.md"), lock[:12])
    check("run", "V1 config sha", info["sha256"]["logs/btc_alltf_2026_10_28/STUDY_CONFIG.json"] == sha(STUDY / "STUDY_CONFIG.json"), "")
    check("run", "V1 fees.json sha", info["sha256"]["deploy/fees.json"] == sha(PROJ / "deploy/fees.json"), "")
    jobs = [tuple(j.split(":")) for j in a.jobs] if a.jobs else [(m, tf) for tf in CFG["timeframes"] for m in CFG["markets"]]
    rng = random.Random(20261028)
    for m, tf in jobs:
        if not (run / m / tf / "DONE.json").exists():
            check(f"{m}:{tf}", "job finished", False, "no DONE.json"); continue
        verify_job(run, m, tf, a.sample, rng)
    if a.mutation:
        mutation(run, *jobs[0])
    n_f = sum(1 for r in RES if not r[2])
    print(f"TOTAL {len(RES)} checks, FAIL {n_f}")
    pd.DataFrame(RES, columns=["job", "check", "pass", "detail"]).to_csv(run / f"verify_{'_'.join(f'{m}-{tf}' for m, tf in jobs[:3])}.csv", index=False)
    sys.exit(1 if n_f else 0)


if __name__ == "__main__":
    main()
