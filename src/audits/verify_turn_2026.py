"""Independent verifier for TURN-2026 (protocol logs/turn_detect_2026/TURN_PROTOCOL_PREREGISTERED.md, §10 V1-V8).
Own code: zipfile + csv reading, plain loops, own null (random.Random), own detector loops. Does not import turn_2026.
Run: python src/audits/verify_turn_2026.py [disc|hold]"""
import csv, hashlib, io, json, math, random, sys, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd            # only to read the study's parquet outputs

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "turn_detect_2026"
res = []


def check(n, ok, d=""):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {n}  {d}", flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                return h.hexdigest()
            h.update(b)


def close(a, b, t=1e-9):
    if a is None or b is None:
        return False
    if isinstance(a, float) and math.isnan(a) and isinstance(b, float) and math.isnan(b):
        return True
    return abs(a - b) <= t * max(1.0, abs(a), abs(b))


def read_1m(months):
    rows = []
    for m in months:
        with zipfile.ZipFile(ROOT / f"data/external/binance_1s/futures_1m/BTCUSDT-1m-2026-0{m}.zip") as z:
            with z.open(z.namelist()[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh, "ascii"))
                next(rd)
                for r in rd:
                    rows.append((int(r[0]) // 1000, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[9])))
    rows.sort()
    out, seen = [], set()
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            out.append(r)
    return out          # (sec, o, h, l, c, v, tb)


def machine(c, th):
    """own ZigZag + event loop (written separately from the study code)."""
    piv, ev = [], []
    leg, ext, iext = 0, None, None
    hi, lo, ihi, ilo = c[0], c[0], 0, 0
    pending, done_f, prev = [], set(), None
    for t in range(1, len(c)):
        x = c[t]
        if leg == 0:
            if x > hi:
                hi, ihi = x, t
            if x < lo:
                lo, ilo = x, t
            if x >= lo * (1 + th):
                piv.append((ilo, lo, 1, t)); prev = lo; leg, ext, iext = 1, x, t
            elif x <= hi * (1 - th):
                piv.append((ihi, hi, -1, t)); prev = hi; leg, ext, iext = -1, x, t
            continue
        s = leg                      # -1: tracking a low, +1: tracking a high
        new_ext = (x < ext) if s == -1 else (x > ext)
        if new_ext:
            for p in pending:
                ev.append((p[0], -s, p[1], p[2], p[3], 0, t))
            pending, done_f = [], set()
            ext, iext = x, t
            continue
        turned = (x >= ext * (1 + th)) if s == -1 else (x <= ext * (1 - th))
        if turned:
            for p in pending:
                ev.append((p[0], -s, p[1], p[2], p[3], 1, t))
            piv.append((iext, ext, -s, t)); prev = ext
            pending, done_f = [], set()
            leg, ext, iext = -s, x, t
            continue
        for f in (0.25, 0.5, 0.75):
            lvl = ext * (1 + f * th) if s == -1 else ext * (1 - f * th)
            if f not in done_f and ((x >= lvl) if s == -1 else (x <= lvl)):
                done_f.add(f)
                pending.append((t, f, iext, ext))
    return piv, ev


def ema_list(x, n):
    a = 2 / (n + 1)
    out, e = [], x[0]
    for v in x:
        e = a * v + (1 - a) * e
        out.append(e)
    return out


def tf_bars(m1, tfm):
    bars, cur = [], None
    for (sec, o, h, l, c, v, tb) in m1:
        k = (sec // 60) // tfm
        if cur is None or k != cur[0]:
            if cur is not None:
                bars.append(cur)
            cur = [k, o, h, l, c, v, tb]
        else:
            cur[2] = max(cur[2], h); cur[3] = min(cur[3], l); cur[4] = c; cur[5] += v; cur[6] += tb
    bars.append(cur)
    return bars         # [k, o, h, l, c, v, tb]


def trades(bars, st, start_k=None):
    out, pos, ent, ient = [], 0.0, None, None
    n = len(bars)
    for t in range(1, n + 1):
        newpos = st[t - 1] if t < n + 1 else 0.0
        if t == n:                                  # close out at the last close
            if pos != 0:
                out.append((pos, ient, n, pos * (bars[-1][4] / ent - 1)))
            break
        if newpos != pos:
            if pos != 0:
                out.append((pos, ient, t, pos * (bars[t][1] / ent - 1)))
            if newpos != 0:
                ent, ient = bars[t][1], t
            pos = newpos
    if start_k is not None:
        out = [x for x in out if bars[x[1]][0] >= start_k]
    return out


def sgn(x):
    return 0.0 if x != x or x == 0 else (1.0 if x > 0 else -1.0)


def det_loops(name, b, tabs):
    c = [x[4] for x in b]
    n = len(c)
    st = [0.0] * n
    if name == "P1_EMAslope20":
        e = ema_list(c, 20)
        st = [0.0] + [sgn(e[t] - e[t - 1]) for t in range(1, n)]
    elif name == "P2_EMAx5_20":
        a, z = ema_list(c, 5), ema_list(c, 20)
        st = [sgn(a[t] - z[t]) for t in range(n)]
    elif name == "P9_MACDhist":
        a, z = ema_list(c, 12), ema_list(c, 26)
        m = [a[t] - z[t] for t in range(n)]
        s9 = ema_list(m, 9)
        st = [sgn(m[t] - s9[t]) for t in range(n)]
    elif name == "P10_RSI50":
        up = dn = 0.0
        for t in range(n):
            d = c[t] - c[t - 1] if t else 0.0
            up = up + (max(d, 0) - up) / 14 if t else max(d, 0)
            dn = dn + (max(-d, 0) - dn) / 14 if t else max(-d, 0)
            rsi = 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)
            st[t] = sgn(rsi - 50)
    elif name == "P8_Donchian20":
        cur = 0.0
        for t in range(n):
            if t >= 20:
                hh = max(x[2] for x in b[t - 20:t]); ll = min(x[3] for x in b[t - 20:t])
                if c[t] > hh:
                    cur = 1.0
                elif c[t] < ll:
                    cur = -1.0
            st[t] = cur
    elif name == "P11_BollFade":
        cur = 0.0
        for t in range(n):
            if t >= 19:
                w = c[t - 19:t + 1]
                m = sum(w) / 20
                sd = math.sqrt(sum((x - m) ** 2 for x in w) / 20)
                if sd > 0:
                    pb = (c[t] - (m - 2 * sd)) / (4 * sd)
                    if pb > 1:
                        cur = -1.0
                    elif pb < 0:
                        cur = 1.0
            st[t] = cur
    elif name == "P12_HeikinAshi":
        ho = (b[0][1] + b[0][4]) / 2
        for t in range(n):
            hc = (b[t][1] + b[t][2] + b[t][3] + b[t][4]) / 4
            if t:
                pb = b[t - 1]
                ho = (ho + (pb[1] + pb[2] + pb[3] + pb[4]) / 4) / 2
            st[t] = sgn(hc - ho)
    elif name == "P14_Fractal":
        ph, pl, cur = [], [], 0.0
        for t in range(n):
            if t >= 2:
                if b[t - 1][2] > b[t - 2][2] and b[t - 1][2] > b[t][2]:
                    ph.append(b[t - 1][2])
                if b[t - 1][3] < b[t - 2][3] and b[t - 1][3] < b[t][3]:
                    pl.append(b[t - 1][3])
                if len(ph) >= 2 and len(pl) >= 2:
                    if ph[-1] > ph[-2] and pl[-1] > pl[-2]:
                        cur = 1.0
                    elif ph[-1] < ph[-2] and pl[-1] < pl[-2]:
                        cur = -1.0
            st[t] = cur
    elif name == "P7_CUSUMh4":
        r = [0.0] + [math.log(c[t] / c[t - 1]) for t in range(1, n)]
        # ewm std (span 100, adjust False) of r, shifted by one
        a = 2 / 101                                  # pandas ewm(span=100, adjust=False).std(): bias-corrected
        mean = r[0]; var = 0.0; s2 = 1.0; sds = [float("nan")]
        for t in range(1, n):
            diff = r[t] - mean
            mean = mean + a * diff
            var = (1 - a) * (var + a * diff * diff)
            s2 = (1 - a) ** 2 * s2 + a * a
            sds.append(math.sqrt(var / (1 - s2)))
        sp = sm = 0.0; cur = 0.0
        for t in range(n):
            sd = sds[t - 1] if t >= 1 else float("nan")
            z = r[t] / sd if (sd == sd and sd > 0) else 0.0
            sp = max(0.0, sp + z - 0.5); sm = max(0.0, sm - z - 0.5)
            if sp > 4:
                cur, sp, sm = 1.0, 0.0, 0.0
            elif sm > 4:
                cur, sp, sm = -1.0, 0.0, 0.0
            st[t] = cur
    elif name == "Q1_TakerImbEMA5":
        x = [(bb[6] / bb[5] - 0.5) if bb[5] > 0 else 0.0 for bb in b]
        e = ema_list(x, 5)
        st = [sgn(v) for v in e]
    elif name == "Q4_DepthImb5":
        st = [sgn(asof(tabs["imb5"], (bb[0] + 1) * TFM_CUR[0] * 60)) for bb in b]
    return st


TFM_CUR = [60]


def asof(series, tsec):
    """series: sorted list of (usable_from_sec, value)."""
    lo, hi = 0, len(series)
    while lo < hi:
        mid = (lo + hi) // 2
        if series[mid][0] <= tsec:
            lo = mid + 1
        else:
            hi = mid
    return series[lo - 1][1] if lo else float("nan")


def load_tab(name, col):
    t = pd.read_parquet(ROOT / f"data/external/binance_public/clean/{name}.parquet")
    out = []
    for tm, v in zip(t["time"].astype("datetime64[ns]").astype("int64") // 10**9, t[col]):
        out.append((int(tm) + 300, float(v)))
    out.sort()
    ded = {}
    for k, v in out:
        ded.setdefault(k, v)
    return sorted(ded.items())


def main(stage):
    # V1
    check("V1 protocol SHA", sha(OUT / "TURN_PROTOCOL_PREREGISTERED.md") == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0])
    man = list(csv.DictReader(open(OUT / "input_manifest_disc.csv")))
    check("V1 DISC input SHAs", all(sha(ROOT / r["file"]) == r["sha256"] for r in man), f"{len(man)} files")
    hold_opened = (OUT / "HOLD_OPENED.txt").exists()
    if hold_opened:
        txt = (OUT / "HOLD_OPENED.txt").read_text().split()
        cj = json.loads((OUT / "hold_candidates.json").read_text())
        check("V1 HOLD opened after candidates, candidates unchanged",
              txt[3] == sha(OUT / "hold_candidates.json") and txt[1] > cj["created_utc"], f"{cj['created_utc']} -> {txt[1]}")
    else:
        check("V1 HOLD still sealed", True, "HOLD_OPENED.txt absent")
    od = [l.split() for l in (OUT / "OUTPUT_SHA256_disc.txt").read_text().splitlines()]
    check("V1 DISC output SHAs", all(sha(OUT / x[1]) == x[0] for x in od), f"{len(od)} files")
    m1 = read_1m(range(1, 6))
    c = [x[4] for x in m1]
    secs = [x[0] for x in m1]
    check("V1 1m continuity (DISC)", all(secs[i + 1] - secs[i] == 60 for i in range(len(secs) - 1)), f"{len(secs)} minutes")
    # V2 pivots
    for th in (0.01, 0.04):
        piv, ev = machine(c, th)
        P = list(csv.DictReader(open(OUT / f"pivots_disc_theta{th}.csv")))
        ok = len(P) == len(piv) and all(int(float(p["ext_idx"])) == q[0] and int(float(p["confirm_idx"])) == q[3] and int(float(p["kind"])) == q[2]
                                         and close(float(p["ext_price"]), q[1]) for p, q in zip(P, piv))
        check(f"V2 ZigZag pivots theta {th}", ok, f"{len(piv)} pivots")
    # V3 events theta 1% f 0.5
    piv, ev = machine(c, 0.01)
    e5 = [e for e in ev if e[2] == 0.5]
    T1 = {(float(r["theta"]), float(r["f"])): r for r in csv.DictReader(open(OUT / "T1_completion_disc.csv"))}
    r = T1[(0.01, 0.5)]
    pr = sum(e[5] for e in e5) / len(e5)
    check("V3 T1 events/outcomes theta 1% f 0.5", len(e5) == int(r["n_events"]) and close(pr, float(r["P_real"])), f"n {len(e5)}, P {pr:.4f}")
    rnd = random.Random(777)
    ps = []
    lr = [math.log(c[t] / c[t - 1]) for t in range(1, len(c))]
    for _ in range(50):
        x = math.log(c[0]); cn = [c[0]]
        for v in lr:
            x += v if rnd.random() < 0.5 else -v
            cn.append(math.exp(x))
        _, evn = machine(cn, 0.01)
        en = [e for e in evn if e[2] == 0.5]
        ps.append(sum(e[5] for e in en) / len(en))
    pn = sum(ps) / len(ps)
    check("V3 own null P within 2 pp", abs(pn - float(r["P_null_mean"])) <= 0.02, f"own {pn:.4f} vs main {float(r['P_null_mean']):.4f}")
    # V4 features
    F = pd.read_parquet(OUT / "T2_features_disc.parquet")
    oi = load_tab("metrics5m", "sum_open_interest")
    imb = load_tab("depth5m", "imb5")
    rnd2 = random.Random(4)
    feats = ["F01_bounce_min", "F02_prior_leg", "F03_vol_ratio", "F04_taker_bounce", "F06_oi_change", "F09_depth_imb5",
             "F13_stair_1m", "F14_retests", "F20_rv24h", "F18_speed"]
    bad, done = [], 0
    v = [m[5] for m in m1]; tb = [m[6] for m in m1]
    picks = [(rnd2.randrange(len(F)), rnd2.choice(feats)) for _ in range(300)]
    h1 = None
    for i, k in picks:
        row = F.iloc[i]
        th, e = float(row.theta), int(row.event_idx)
        dr = float(row.dir)
        # find L for this event via own machine on theta (cache)
        key = th
        if h1 is None or h1[0] != key:
            _, evk = machine(c, th)
            h1 = (key, {(x[0], x[2]): x for x in evk})
        x = h1[1].get((e, float(row.f)))
        if x is None:
            bad.append((i, k, "event not found")); continue
        L = x[3]
        Lp = c[L]
        if k == "F01_bounce_min":
            val = float(e - L)
        elif k == "F02_prior_leg":
            prevs = [p for p in machine_pivots_cache(c, th) if p[3] <= L]
            val = abs(math.log(Lp / prevs[-1][1])) / th if prevs else float("nan")
        elif k == "F03_vol_ratio":
            vb = sum(v[L + 1:e + 1]) / max(e - L, 1)
            p0 = max(L - 60, 0)
            vp = sum(v[p0:L]) / max(L - p0, 1)
            val = vb / vp if vp > 0 else float("nan")
        elif k == "F04_taker_bounce":
            val = dr * (sum(tb[L + 1:e + 1]) / max(sum(v[L + 1:e + 1]), 1e-12) - 0.5)
        elif k == "F06_oi_change":
            a1 = asof(oi, secs[e] + 60); a0 = asof(oi, secs[L] + 60)
            val = dr * (a1 / a0 - 1)
        elif k == "F09_depth_imb5":
            val = dr * asof(imb, secs[e] + 60)
        elif k == "F13_stair_1m":
            if dr > 0:
                cnt = sum(1 for t in range(L + 1, e + 1) if m1[t][3] > m1[t - 1][3])
            else:
                cnt = sum(1 for t in range(L + 1, e + 1) if m1[t][2] < m1[t - 1][2])
            val = cnt / max(e - L, 1)
        elif k == "F14_retests":
            val = float(sum(1 for t in range(max(L - 120, 0), L) if abs(c[t] / Lp - 1) <= 0.1 * th))
        elif k == "F18_speed":
            val = float(row.f) * th / max(e - L, 1)
        elif k == "F20_rv24h":
            s0 = max(e - 1440, 0)
            rr = [math.log(c[t] / c[t - 1]) for t in range(s0 + 1, e + 1)]
            mm = sum(rr) / len(rr)
            val = math.sqrt(max(sum(q * q for q in rr) / len(rr) - mm * mm, 0))
        got = float(row[k])
        done += 1
        if not ((math.isnan(val) and math.isnan(got)) or close(val, got, 1e-6)):
            bad.append((i, k, val, got))
    check("V4 300 feature values from raw", not bad, f"{done} checked, mismatches {bad[:3]}")
    # V5 detectors: trades replayed by own loops on 1h (12 detectors) and 15m (P1)
    TT = pd.read_parquet(OUT / "T3_trades_disc.parquet")
    tabs = {"imb5": imb}
    names = ["P1_EMAslope20", "P2_EMAx5_20", "P7_CUSUMh4", "P8_Donchian20", "P9_MACDhist", "P10_RSI50", "P11_BollFade",
             "P12_HeikinAshi", "P14_Fractal", "Q1_TakerImbEMA5", "Q4_DepthImb5"]
    bad = []
    for tf, tfm, dets in (("1h", 60, names), ("15m", 15, ["P1_EMAslope20", "P10_RSI50"]), ("4h", 240, ["P2_EMAx5_20"])):
        TFM_CUR[0] = tfm
        b = tf_bars(m1, tfm)
        for dn in dets:
            st = det_loops(dn, b, tabs)
            mine = trades(b, st)
            theirs = TT[(TT.tf == tf) & (TT.det == dn)].sort_values("i_in")
            ok = len(mine) == len(theirs) and all(int(a[1]) == int(bb.i_in) and close(a[3], float(bb.gross), 1e-7)
                                                  for a, bb in zip(mine, theirs.itertuples()))
            if not ok:
                bad.append((tf, dn, len(mine), len(theirs)))
    check("V5 detector trades replayed by own loops (14 configs)", not bad, f"mismatches {bad}")
    # V6 VR / AC1
    C4 = pd.read_csv(OUT / "T4_cells_disc.csv")
    lc = [math.log(x) for x in c]
    r1 = [lc[t] - lc[t - 1] for t in range(1, len(lc))]
    m_ = sum(r1) / len(r1)
    v1 = sum((x - m_) ** 2 for x in r1) / len(r1)
    bad = []
    for q in (5, 15, 60, 240):
        xs = lc[0::q]
        rq = [xs[i] - xs[i - 1] for i in range(1, len(xs))]
        mq = sum(rq) / len(rq)
        vq = sum((x - mq) ** 2 for x in rq) / len(rq)
        a, bq = rq[1:], rq[:-1]
        ma, mb = sum(a) / len(a), sum(bq) / len(bq)
        cov = sum((x - ma) * (y - mb) for x, y in zip(a, bq))
        ac = cov / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in bq))
        row = C4[(C4.unit == "min") & (C4.q == q) & (C4.phase == 0)].iloc[0]
        if not (close(vq / (q * v1), float(row.VR), 1e-6) and close(ac, float(row.AC1), 1e-6)):
            bad.append((q, vq / (q * v1), float(row.VR), ac, float(row.AC1)))
    check("V6 VR and AC1 (4 minute q)", not bad, f"{bad}")
    # V7 daily -> monthly + completeness
    D = list(csv.DictReader(open(OUT / "daily_disc.csv")))
    days = [r["day"][:10] for r in D]
    d0 = datetime(2026, 1, 1)
    want = [(d0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(151)]
    Mo = list(csv.DictReader(open(OUT / "monthly_disc.csv")))
    cols = [k for k in D[0] if k != "day"]
    okm = True
    for mrow in Mo:
        per = mrow[list(mrow)[0]]
        for k in cols:
            s = sum(float(r[k]) for r in D if r["day"][:7] == per)
            if not close(s, float(mrow[k]), 1e-9):
                okm = False
    T1t = pd.read_parquet(OUT / "T1_trades_disc.parquet")
    g = T1t[(T1t.theta == 0.01) & (T1t.f == 0.5)]
    okt = close(sum(float(r["T1_0.01_0.5_sum"]) for r in D), float(g.net_taker.sum()), 1e-9)
    check("V7 daily complete, monthly = sum of daily, daily = trades", days == want and okm and okt, f"{len(days)} days")
    # V8 HOLD decisions
    if hold_opened and stage == "hold":
        bad = []
        for kind in ("T1", "T2", "T3", "T4"):
            p = OUT / f"HOLD_{kind}.csv"
            if not p.exists() or p.stat().st_size < 5:
                continue
            for r in csv.DictReader(open(p)):
                n = int(float(r["n"]))
                if n == 0:
                    continue
                mean = float(r["mean_net"])
                passed = r["passed"] == "True"
                need = n >= 30 and mean > 0 and float(r["ci_lo_bonf"]) > 0 and int(float(r["pos_months"])) >= 3 and r.get("control_ok") == "True"
                if need != passed:
                    bad.append((kind, r))
        check("V8 HOLD pass decisions recomputed from rows", not bad, f"{len(bad)} disagreements")
    print(f"\nTOTAL {len(res)} checks, {sum(res)} PASS, {len(res) - sum(res)} FAIL -> {'ALL PASS' if all(res) else 'FAILURES'}")


_PC = {}


def machine_pivots_cache(c, th):
    if th not in _PC:
        _PC[th] = machine(c, th)[0]
    return _PC[th]


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "disc")
