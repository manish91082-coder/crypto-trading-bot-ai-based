"""BTC-ALLTF study (2026-10-28): historical paper trading of every rule x exit x stop x direction x filter / pair / vote on
ONE market (spot | futures) and ONE timeframe. Protocol: logs/btc_alltf_2026_10_28/BTC_ALLTF_PROTOCOL_PREREGISTERED.md,
settings: logs/btc_alltf_2026_10_28/STUDY_CONFIG.json (both SHA-locked before the first P&L number).
Usage: python src/btc_alltf/study.py --market spot --tf 1h --run <RUN dir> [--count]
Writes into <RUN>/<market>/<tf>/ : trades.parquet (EVERY trade), configs.parquet (every config: params, metrics, gates, verdict,
rank), monthly.parquet, daily_groups.parquet, daily_overview.csv, every_bar.parquet, top_daily.parquet, ranking_top100.csv,
duplicates.csv, summary.json, job_log.txt, DONE.json (sha256 of every file)."""
import argparse
import hashlib
import json
import sys
import time
import zlib
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import norm, t as tdist, skew, kurtosis

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as E                                                            # noqa: E402
import rules                                                                  # noqa: E402

PROJ = Path(__file__).resolve().parents[2]
STUDY = PROJ / "logs/btc_alltf_2026_10_28"
CFG = json.loads((STUDY / "STUDY_CONFIG.json").read_text(encoding="utf-8"))
BARS = PROJ / "data/derived/btc_alltf/bars"
STATES = PROJ / "data/derived/btc_alltf/states"
DAY = 86_400_000
TS_ = lambda s: int(pd.Timestamp(s, tz="UTC").value // 10 ** 6)             # noqa: E731
P_V, P_H = TS_(CFG["periods"]["V_start"]), TS_(CFG["periods"]["H_start"])
# Compact, lossless trade log (7.8 bytes/trade measured on spot 1h vs 21.5 for the wide form). Not stored because they follow
# exactly from the bars + fees.json + funding (query.py rebuilds them, the verifier checks it): px_in (= open of the t_in bar),
# px_out when the fill is an open (SIG, TIME and gap exits), bars, dir (from the config), gross, fee, funding, mae, mfe.
SCHEMA = pa.schema([("cfg", pa.uint32()), ("t_in", pa.timestamp("ms", tz="UTC")), ("t_out", pa.timestamp("ms", tz="UTC")),
                    ("reason", pa.int8()), ("px_out", pa.float64()), ("net", pa.float32()), ("win", pa.int8())])
STORED_PX = (3, 5, 7, 9, 10, 11)                                              # SL, TP, TRAIL, LIQ, END (last close), SL_AMBIG


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ inputs
def load_bars(market, tf):
    b = pd.read_parquet(BARS / f"{market}_{tf}.parquet", columns=["ts", "open", "high", "low", "close", "volume", "taker_buy_base"])
    return b


def funding_tables(market, ts):
    """futures: (tau ms, cum rate*P) for trades and cumulative rate at bar opens for the control; spot: None, zeros"""
    if market != "futures":
        return None, np.zeros(len(ts))
    f = pd.read_parquet(PROJ / CFG["inputs"]["funding"])
    tau = f.time.values.astype("datetime64[ms]").astype("int64")
    m1 = pd.read_parquet(BARS / "futures_1m.parquet", columns=["ts", "open"]).set_index("ts").open
    px = m1.reindex((tau // 60_000) * 60_000).values
    if np.isnan(px).any():
        raise RuntimeError(f"funding price missing for {int(np.isnan(px).sum())} events")
    rate = f.funding_rate.values
    cum = np.r_[0.0, np.cumsum(rate * px)]
    cumrate = np.r_[0.0, np.cumsum(rate)]
    cfb = cumrate[np.searchsorted(tau, ts, side="right")]
    return (tau, cum), np.ascontiguousarray(cfb)


def build_states(market, tf, b):
    """rule states -> int8 memmap (2 rows per rule: A, B) + index; computed once per market/tf, reused after"""
    STATES.mkdir(parents=True, exist_ok=True)
    fmm, fix = STATES / f"{market}_{tf}.int8", STATES / f"{market}_{tf}.json"
    if fix.exists():
        ix = json.loads(fix.read_text())
        if ix.get("n") == len(b) and ix.get("rules_sha") == sha(Path(rules.__file__)):
            return np.memmap(fmm, dtype=np.int8, mode="r", shape=(len(ix["rows"]), len(b))), ix
    out, x = rules.compute(b, tf)
    g = rules.gates(x)
    rows = [f"{r}|{s}" for r in out for s in "AB"] + [f"{k}|{s}" for k in g for s in "LS"]
    mm = np.memmap(fmm, dtype=np.int8, mode="w+", shape=(len(rows), len(b)))
    i = 0
    for r in out:
        mm[i], mm[i + 1] = out[r]
        i += 2
    for k in g:
        mm[i], mm[i + 1] = g[k]
        i += 2
    mm.flush()
    atr = x.atr(14).values
    np.save(STATES / f"{market}_{tf}_atr14.npy", atr)
    ix = dict(n=len(b), rows=rows, rules_sha=sha(Path(rules.__file__)))
    fix.write_text(json.dumps(ix))
    del out, x, mm
    return np.memmap(fmm, dtype=np.int8, mode="r", shape=(len(rows), len(b))), ix


# ------------------------------------------------------------------ configs
def enumerate_configs(market, ix, rule_meta):
    rows = {r: k for k, r in enumerate(ix["rows"])}
    rids = [r.split("|")[0] for r in ix["rows"][::2] if r.endswith("|A") and r.split("|")[0] in rule_meta]
    dirs = [("A", 1, "long", "nat"), ("B", 1, "long", "con")] if market == "spot" else \
           [("A", 1, "long", "nat"), ("B", -1, "short", "nat"), ("B", 1, "long", "con"), ("A", -1, "short", "con")]
    C = []
    ex_all, ex_f, ex_p = list(E.EXITS), CFG["layers"]["L2_exits"], CFG["layers"]["L3_exits"]
    for rid in rids:
        for arr, d, dl, side in dirs:
            for ex in ex_all:
                C.append(dict(layer="L1", rule=rid, rule2="", src=(rows[f"{rid}|{arr}"],), dir=d, dlabel=dl, side=side, exit=ex, gate="-"))
    for rid in rids:
        for gk in CFG["layers"]["L2_filters"]:
            for arr, d, dl, side in dirs:
                for ex in ex_f:
                    gr = rows[f"{gk}|{'L' if d > 0 else 'S'}"]
                    C.append(dict(layer="L2", rule=rid, rule2="", src=(rows[f"{rid}|{arr}"],), dir=d, dlabel=dl, side=side, exit=ex,
                                  gate=gk, grow=gr))
    nat = [("A", 1, "long", "nat")] if market == "spot" else [("A", 1, "long", "nat"), ("B", -1, "short", "nat")]
    reps = [r for r in rules.REPS if r in rids]
    for r1, r2 in combinations(reps, 2):
        for arr, d, dl, side in nat:
            for ex in ex_p:
                C.append(dict(layer="L3", rule=r1, rule2=r2, src=(rows[f"{r1}|{arr}"], rows[f"{r2}|{arr}"]), dir=d, dlabel=dl,
                              side=side, exit=ex, gate="-", op="and"))
    for vname, members, ks in (("VOTE_TREND", rules.VOTE_TREND, CFG["layers"]["L4_trend_k"]),
                               ("VOTE_OSC", rules.VOTE_OSC, CFG["layers"]["L4_osc_k"]),
                               ("VOTE_ALL24", rules.REPS, CFG["layers"]["L4_all_k"])):
        mem = [r for r in members if r in rids]
        if len(mem) < len(members):
            continue
        for k in ks:
            for arr, d, dl, side in nat:
                for ex in ex_all:
                    C.append(dict(layer="L4", rule=f"{vname}_k{k}of{len(mem)}", rule2="", src=tuple(rows[f"{r}|{arr}"] for r in mem),
                                  dir=d, dlabel=dl, side=side, exit=ex, gate="-", op=f"vote{k}"))
    for i, c in enumerate(C):
        c["cfg"] = i
        meta = rule_meta.get(c["rule"], {})
        c["cat"] = meta.get("cat", "pair" if c["layer"] == "L3" else "vote")
        c["tags"] = meta.get("tags", "")
        c["name"] = f"{c['layer']}|{c['rule']}{('+' + c['rule2']) if c['rule2'] else ''}|{c['dlabel']}_{c['side']}|{c['exit']}|{c['gate']}"
    return C


_LAST = {}


def state_of(c, mm):
    """state array of a config; the last combined (pair / vote) array is kept, since consecutive configs share it"""
    s = c["src"]
    if len(s) > 1:
        k = s + (c.get("op", ""),)
        if k not in _LAST:
            _LAST.clear()
            _LAST[k] = _state(c, mm)
        return _LAST[k]
    return np.asarray(mm[s[0]])


def _state(c, mm):
    s = c["src"]
    if len(s) == 1:
        return np.asarray(mm[s[0]])
    if c.get("op") == "and":
        return (np.asarray(mm[s[0]]) & np.asarray(mm[s[1]])).astype(np.int8)
    k = int(c["op"][4:])
    tot = np.zeros(mm.shape[1], np.int16)
    for r in s:
        tot += np.asarray(mm[r])
    return (tot >= k).astype(np.int8)


# ------------------------------------------------------------------ metrics
def basic(x):
    n = len(x)
    if n == 0:
        return dict(n=0, wins=0, mean=np.nan, median=np.nan, sd=np.nan, sum=0.0, t=np.nan, p=1.0, pf=np.nan)
    m, sd = float(x.mean()), float(x.std(ddof=1)) if n > 1 else np.nan
    t = m / (sd / np.sqrt(n)) if n > 1 and sd > 0 else np.nan
    p = float(tdist.sf(t, n - 1)) if np.isfinite(t) else 1.0
    w, lo = x[x > 0].sum(), -x[x <= 0].sum()
    return dict(n=n, wins=int((x > 0).sum()), mean=m, median=float(np.median(x)), sd=sd, sum=float(x.sum()), t=t, p=p,
                pf=float(w / lo) if lo > 0 else np.nan)


def metrics(net, gross, fe, fu, t_in, bars, reason, mae, mfe, nbars, span_years, years):
    r = {}
    for k, v in basic(net).items():
        r[k] = v
    r["winrate"] = r["wins"] / r["n"] if r["n"] else np.nan
    for pn, msk in (("D", t_in < P_V), ("V", (t_in >= P_V) & (t_in < P_H)), ("H", t_in >= P_H)):
        b = basic(net[msk])
        r[f"n_{pn}"], r[f"mean_{pn}"], r[f"sum_{pn}"], r[f"winrate_{pn}"] = b["n"], b["mean"], b["sum"], (b["wins"] / b["n"] if b["n"] else np.nan)
    h = t_in >= P_H
    r["mean_H_2xfee"] = float((net[h] - fe[h]).mean()) if h.any() else np.nan
    r["mean_gross"] = float(gross.mean()) if len(net) else np.nan
    r["mean_fee"] = float(fe.mean()) if len(net) else np.nan
    r["mean_funding"] = float(fu.mean()) if len(net) else np.nan
    r["gross_pos"] = bool(r["mean_gross"] > 0) if len(net) else False
    r["avg_bars"] = float(bars.mean()) if len(net) else np.nan
    r["exposure"] = float(bars.sum() / nbars)
    r["mae_mean"] = float(mae.mean()) if len(net) else np.nan
    r["mfe_mean"] = float(mfe.mean()) if len(net) else np.nan
    r["skew"] = float(skew(net)) if len(net) > 2 else np.nan
    r["kurt"] = float(kurtosis(net, fisher=False)) if len(net) > 3 else np.nan
    if len(net):
        eq = np.cumprod(np.maximum(1.0 + net.astype(np.float64), 0.0))
        r["equity_end"] = float(eq[-1])
        r["max_dd"] = float((1 - eq / np.maximum.accumulate(np.r_[1.0, eq])[1:]).max())
        r["ruined"] = bool((eq <= 0).any())
        r["cagr"] = float(eq[-1] ** (1 / span_years) - 1) if eq[-1] > 0 else -1.0
    else:
        r.update(equity_end=1.0, max_dd=0.0, ruined=False, cagr=0.0)
    yr = pd.to_datetime(t_in, unit="ms", utc=True).year.values if len(net) else np.array([], int)
    for y in years:
        m = yr == y
        r[f"n_{y}"] = int(m.sum())
        r[f"sum_{y}"] = float(net[m].sum())
    for code, nm in E.REASONS.items():
        r[f"x_{nm}"] = int((reason == code).sum())
    return r


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(q, 1.0)
    return out


def dsr(mean, sd, n, sk, ku, N, V):
    sr = mean / sd
    em = 0.5772156649
    sr0 = np.sqrt(V) * ((1 - em) * norm.ppf(1 - 1 / N) + em * norm.ppf(1 - 1 / (N * np.e)))
    den = 1 - sk * sr + (ku - 1) / 4 * sr ** 2
    z = (sr - sr0) * np.sqrt(n - 1) / np.sqrt(np.where(den > 0, den, np.nan))
    return norm.cdf(z)


# ------------------------------------------------------------------ main job
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", required=True)
    ap.add_argument("--tf", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--count", action="store_true")
    a = ap.parse_args()
    out = Path(a.run) / a.market / a.tf
    out.mkdir(parents=True, exist_ok=True)
    if (out / "DONE.json").exists() and not a.count:
        print(f"{a.market} {a.tf}: DONE already"); return
    logf = open(out / ("count_log.txt" if a.count else "job_log.txt"), "a", encoding="utf-8")

    def log(m):
        s = f"[{pd.Timestamp.now('UTC'):%Y-%m-%d %H:%M:%S}] {a.market} {a.tf}: {m}"
        print(s, flush=True); logf.write(s + "\n"); logf.flush()
    t0 = time.time()
    b = load_bars(a.market, a.tf)
    mm, ix = build_states(a.market, a.tf, b)
    atr = np.load(STATES / f"{a.market}_{a.tf}_atr14.npy")
    B = E.Bars(b.ts.values, b.open.values, b.high.values, b.low.values, b.close.values, atr)
    ts = B.ts
    nbars = B.n
    del b
    fee = E.fees()[a.market]
    mmr = CFG["futures_mmr"] if a.market == "futures" else 0.0
    fund, cfb = funding_tables(a.market, ts)
    span_years = (ts[-1] - ts[0]) / (365.25 * DAY) if nbars > 1 else 1.0
    years = list(range(pd.Timestamp(int(ts[0]), unit="ms").year, 2027))
    rule_meta = {r["id"]: r for r in rules.REG}
    C = enumerate_configs(a.market, ix, rule_meta)
    log(f"bars {nbars}, rules {len(ix['rows']) // 2 - 5}, configs {len(C)}, states built in {time.time() - t0:.0f}s")
    # duplicates: identical (state, gate, dir, exit) -> run once, the copy points to the first
    seen, dup = {}, {}
    hcache, gcache = {}, {}
    for c in C:
        hk = c["src"] + (c.get("op", ""),)
        if hk not in hcache:
            hcache[hk] = hashlib.sha1(state_of(c, mm).tobytes()).hexdigest()
        if c["gate"] != "-" and c["grow"] not in gcache:
            gcache[c["grow"]] = hashlib.sha1(np.asarray(mm[c["grow"]]).tobytes()).hexdigest()
        gh = "-" if c["gate"] == "-" else gcache[c["grow"]]
        key = (hcache[hk], gh, c["dir"], c["exit"])
        if key in seen:
            dup[c["cfg"]] = seen[key]
        else:
            seen[key] = c["cfg"]
    log(f"unique configs {len(seen)}, duplicates {len(dup)}")
    G = {}
    groups = []
    day0 = (ts[0] // DAY) * DAY
    ND = int((TS_(CFG["periods"]["H_end"]) - day0) // DAY) + 1               # every calendar day up to the data end (2026-09-30)
    if not a.count:
        writer = pq.ParquetWriter(out / "trades.parquet", SCHEMA, compression="zstd")
        buf, nbuf = [], 0
        monthly = []
        gid = {}
        dn = {k: np.zeros((ND, 1), np.int64) for k in ("n", "w", "o")}
        dsum = {k: np.zeros((ND, 1)) for k in ("net", "gross")}
    rows_out = []
    cnt = []
    tl = time.time()
    for j, c in enumerate(C):
        if c["cfg"] in dup:
            continue
        st = state_of(c, mm)
        gate = None if c["gate"] == "-" else np.asarray(mm[c["grow"]])
        T = E.run(B, st, c["dir"], c["exit"], gate=gate, mmr=mmr)
        n = len(T["ei"])
        if a.count:
            cnt.append((c["cfg"], c["layer"], c["exit"], n))
            if j % 2000 == 0:
                log(f"count {j}/{len(C)}")
            continue
        t_in = ts[T["ei"]]
        t_out = ts[T["xi"]].copy()
        tf_last = ts[-1] - ts[-2] if nbars > 1 else 0
        t_fund = np.where(T["reason"] == 10, t_out + tf_last, t_out)
        gross, fe, fu, net, mae, mfe = E.pnl(T, c["dir"], fee, fund, t_in, t_fund)
        bars_held = (T["xi"] - T["ei"]).astype(np.int32)
        r = dict(cfg=c["cfg"])
        r.update(metrics(net, gross, fe, fu, t_in, bars_held, T["reason"], mae, mfe, nbars, span_years, years))
        if n:
            seed = zlib.crc32(f"{a.market}|{a.tf}|{c['name']}".encode())
            reps = int(min(CFG["control"]["max_reps"], max(CFG["control"]["min_reps"], np.ceil(CFG["control"]["target_draws"] / n))))
            cm, cs, cn = E.control(B, cfb, 0, nbars, c["dir"], np.maximum(bars_held, 1), reps, seed, fee)
            r.update(ctrl_mean=cm, ctrl_sd=cs, ctrl_n=cn)
            se = np.sqrt((r["sd"] ** 2 / n if n > 1 else np.nan) + (cs ** 2 / cn if cn > 1 else np.nan))
            r["ctrl_z"] = (r["mean"] - cm) / se if se and np.isfinite(se) and se > 0 else np.nan
            keep = np.isin(T["reason"], STORED_PX)
            buf.append(pa.table({"cfg": np.full(n, c["cfg"], np.uint32), "t_in": pa.array(t_in, pa.timestamp("ms", tz="UTC")),
                                 "t_out": pa.array(t_out, pa.timestamp("ms", tz="UTC")), "reason": T["reason"],
                                 "px_out": pa.array(np.where(keep, T["px_out"], 0.0), mask=~keep), "net": net.astype(np.float32),
                                 "win": (net > 0).astype(np.int8)}, schema=SCHEMA))
            nbuf += n
            if nbuf >= CFG["io"]["flush_rows"]:
                writer.write_table(pa.concat_tables(buf)); buf, nbuf = [], 0
            mo = pd.to_datetime(t_out, unit="ms", utc=True)
            mk = (mo.year * 100 + mo.month).values
            um, inv = np.unique(mk, return_inverse=True)
            monthly.append(pd.DataFrame({"cfg": c["cfg"], "month": um, "n": np.bincount(inv), "wins": np.bincount(inv, weights=(net > 0)).astype(int),
                                         "sum_net": np.bincount(inv, weights=net), "sum_gross": np.bincount(inv, weights=gross)}))
            gk = (c["layer"], c["cat"], c["dlabel"], c["side"], c["exit"])
            if gk not in gid:
                gid[gk] = len(gid)
                if gid[gk] >= dn["n"].shape[1]:
                    for d_ in (dn, dsum):
                        for k in d_:
                            d_[k] = np.concatenate([d_[k], np.zeros_like(d_[k])], axis=1)
            g = gid[gk]
            dx = ((t_out - day0) // DAY).astype(np.int64)
            di = ((t_in - day0) // DAY).astype(np.int64)
            dn["n"][:, g] += np.bincount(dx, minlength=ND)
            dn["w"][:, g] += np.bincount(dx, weights=(net > 0), minlength=ND).astype(np.int64)
            dn["o"][:, g] += np.bincount(di, minlength=ND)
            dsum["net"][:, g] += np.bincount(dx, weights=net, minlength=ND)
            dsum["gross"][:, g] += np.bincount(dx, weights=gross, minlength=ND)
        rows_out.append(r)
        if j % 1000 == 0:
            log(f"{j}/{len(C)} configs, {time.time() - tl:.0f}s")
    if a.count:
        df = pd.DataFrame(cnt, columns=["cfg", "layer", "exit", "n"])
        df.to_csv(out / "counts.csv", index=False)
        log(f"COUNT done: unique {len(df)}, trades {int(df.n.sum()):,} (L1 {int(df[df.layer == 'L1'].n.sum()):,}, L2 {int(df[df.layer == 'L2'].n.sum()):,}, "
            f"L3 {int(df[df.layer == 'L3'].n.sum()):,}, L4 {int(df[df.layer == 'L4'].n.sum()):,}), {time.time() - t0:.0f}s")
        return
    if buf:
        writer.write_table(pa.concat_tables(buf))
    writer.close()
    log(f"all configs run, {time.time() - t0:.0f}s; gates next")
    # ---------------- configs table, gates, verdict, rank
    M = pd.DataFrame(rows_out)
    meta = pd.DataFrame([{k: v for k, v in c.items() if k not in ("src", "grow", "op")} for c in C])
    meta["dup_of"] = meta.cfg.map(dup).fillna(-1).astype(int)
    meta.to_parquet(out / "all_configs.parquet", index=False)                 # every config incl. duplicates (V7 rebuilds both)
    pd.DataFrame(sorted(dup.items()), columns=["cfg", "same_as_cfg"]).to_csv(out / "duplicates.csv", index=False)
    M = meta[meta.dup_of < 0].merge(M, on="cfg", how="left")
    gcfg = CFG["gates"]
    M["G1"] = (M.n_D >= gcfg["G1_nD"]) & (M.n_V >= gcfg["G1_nV"]) & (M.n_H >= gcfg["G1_nH"])
    M["G2"] = (M.mean_D > 0) & (M.mean_V > 0) & (M.mean_H > 0)
    M["q_bh"] = bh(M.p.fillna(1.0).values)
    M["G3"] = M.q_bh <= gcfg["G3_q"]
    M["G4"] = M.ctrl_z >= gcfg["G4_z"]
    ycols = [y for y in years]
    yn = M[[f"n_{y}" for y in ycols]].values
    ys = M[[f"sum_{y}" for y in ycols]].values
    elig = yn >= gcfg["G6_min_trades_year"]
    npos = ((ys > 0) & elig).sum(1)
    nel = elig.sum(1)
    M["years_eligible"], M["years_positive"] = nel, npos
    M["G6"] = (nel >= gcfg["G6_min_years"]) & (npos >= np.ceil(gcfg["G6_share"] * nel))
    ok30 = (M.n >= 30) & (M.sd > 0)
    V = float(np.nanvar((M["mean"] / M.sd)[ok30])) if ok30.sum() > 1 else np.nan
    Ntr = int(len(M))
    M["dsr"] = np.where(ok30, dsr(M["mean"].values, M.sd.values, M.n.values, M["skew"].fillna(0).values, M["kurt"].fillna(3).values,
                                  max(Ntr, 2), V if np.isfinite(V) and V > 0 else 1e-12), np.nan)
    M["G7"] = M.dsr >= gcfg["G7_dsr"]
    M["G5a"] = M.mean_H_2xfee > 0
    M["mean_H_delay1"] = np.nan
    cand = M.G1 & M.G2 & M.G3 & M.G4 & M.G5a
    for cid in M.cfg[cand].values:
        c = C[cid]
        st = state_of(c, mm)
        gate = None if c["gate"] == "-" else np.asarray(mm[c["grow"]])
        T = E.run(B, st, c["dir"], c["exit"], gate=gate, mmr=mmr, delay=1)
        t_in = ts[T["ei"]]
        t_out = ts[T["xi"]]
        _, _, _, net, _, _ = E.pnl(T, c["dir"], fee, fund, t_in, t_out)
        h = t_in >= P_H
        M.loc[M.cfg == cid, "mean_H_delay1"] = float(net[h].mean()) if h.any() else np.nan
    M["G5"] = M.G5a & (M.mean_H_delay1 > 0)
    gl = ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]
    M["gates_passed"] = M[gl].sum(1)
    M["verdict"] = np.where(~M.G1, "INSUFFICIENT", np.where(M[gl].all(1), "PASS", "FAIL"))
    M = M.sort_values(["verdict", "gates_passed", "t"], ascending=[True, False, False], key=lambda s: s.map({"PASS": 0, "FAIL": 1, "INSUFFICIENT": 2}) if s.name == "verdict" else s)
    M["rank"] = np.arange(1, len(M) + 1)
    M = M.sort_values("cfg")
    M.to_parquet(out / "configs.parquet", index=False)
    top = M.sort_values("rank").head(100)
    top.to_csv(out / "ranking_top100.csv", index=False)
    # ---------------- monthly, daily
    pd.concat(monthly, ignore_index=True).to_parquet(out / "monthly.parquet", index=False) if monthly else None
    gk_list = sorted(gid, key=gid.get)
    dates = pd.to_datetime(day0 + np.arange(ND) * DAY, unit="ms", utc=True).date
    dg = []
    for gk in gk_list:
        g = gid[gk]
        m = (dn["n"][:, g] > 0) | (dn["o"][:, g] > 0)
        if m.any():
            dg.append(pd.DataFrame({"date": dates[m], "layer": gk[0], "cat": gk[1], "dir": gk[2], "side": gk[3], "exit": gk[4],
                                    "n_closed": dn["n"][m, g], "wins": dn["w"][m, g], "losses": dn["n"][m, g] - dn["w"][m, g],
                                    "sum_net": dsum["net"][m, g], "sum_gross": dsum["gross"][m, g], "n_opened": dn["o"][m, g]}))
    if dg:
        pd.concat(dg, ignore_index=True).to_parquet(out / "daily_groups.parquet", index=False)
    o_day = pd.DataFrame({"date": dates, "n_closed": dn["n"].sum(1), "wins": dn["w"].sum(1), "losses": dn["n"].sum(1) - dn["w"].sum(1),
                          "sum_net": dsum["net"].sum(1), "sum_gross": dsum["gross"].sum(1), "n_opened": dn["o"].sum(1)})
    o_day["avg_net_per_trade"] = o_day.sum_net / o_day.n_closed.replace(0, np.nan)
    o_day.to_csv(out / "daily_overview.csv", index=False)
    # ---------------- every bar: all possible next-1/4/16-bar trades (open -> open), long and short, after fee (+ funding)
    o = B.o
    eb = {"ts": pd.to_datetime(ts, unit="ms", utc=True)}
    for h in CFG["every_bar_holds"]:
        R = np.full(nbars, np.nan)
        R[:-h] = o[h:] / o[:-h]
        fl = np.full(nbars, np.nan)
        fl[:-h] = cfb[h:] - cfb[:-h]
        eb[f"r{h}"] = (R - 1).astype(np.float32)
        eb[f"pass_long{h}"] = ((R - 1) - fee * (1 + R) - fl > 0).astype(np.int8)
        eb[f"pass_short{h}"] = ((1 - R) - fee * (1 + R) + fl > 0).astype(np.int8)
    pd.DataFrame(eb).to_parquet(out / "every_bar.parquet", index=False)
    # ---------------- top configs: daily realized P&L and equity
    sel = M[(M.verdict == "PASS") | (M["rank"] <= CFG["top_daily_n"])].cfg.values
    td = []
    for cid in sel:
        c = C[cid]
        st = state_of(c, mm)
        gate = None if c["gate"] == "-" else np.asarray(mm[c["grow"]])
        T = E.run(B, st, c["dir"], c["exit"], gate=gate, mmr=mmr)
        if not len(T["ei"]):
            continue
        t_in = ts[T["ei"]]
        t_out = ts[T["xi"]]
        t_fund = np.where(T["reason"] == 10, t_out + (ts[-1] - ts[-2] if nbars > 1 else 0), t_out)
        _, _, _, net, _, _ = E.pnl(T, c["dir"], fee, fund, t_in, t_fund)
        d = pd.Series(net, index=pd.to_datetime(t_out, unit="ms", utc=True).date).groupby(level=0).agg(["sum", "count"])
        full = pd.DataFrame(index=pd.Index(dates, name="date")).join(d).fillna(0)
        lr = np.log1p(np.maximum(net, -0.999999))
        eqd = pd.Series(lr, index=pd.to_datetime(t_out, unit="ms", utc=True).date).groupby(level=0).sum().reindex(dates).fillna(0).cumsum()
        td.append(pd.DataFrame({"cfg": cid, "date": dates, "n_closed": full["count"].values.astype(int), "sum_net": full["sum"].values,
                                "equity": np.exp(eqd.values)}))
    if td:
        pd.concat(td, ignore_index=True).to_parquet(out / "top_daily.parquet", index=False)
    S = dict(market=a.market, tf=a.tf, bars=nbars, first=str(pd.Timestamp(int(ts[0]), unit="ms")), last=str(pd.Timestamp(int(ts[-1]), unit="ms")),
             fee_per_side=fee, configs=len(C), unique=len(M), duplicates=len(dup), trades=int(M.n.fillna(0).sum()),
             verdict=M.verdict.value_counts().to_dict(), gates_pass={g_: int(M[g_].sum()) for g_ in gl + ["G5a"]},
             gross_positive_share=float(M.gross_pos.mean()), net_positive_share=float((M["mean"] > 0).mean()),
             N_for_dsr=Ntr, sr_var=V, seconds=round(time.time() - t0))
    (out / "summary.json").write_text(json.dumps(S, indent=1, default=str))
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name not in ("DONE.json",))
    (out / "DONE.json").write_text(json.dumps({p.name: sha(p) for p in files} | {"finished_utc": pd.Timestamp.now("UTC").isoformat()}, indent=1))
    log(f"DONE {S['trades']:,} trades, verdicts {S['verdict']}, {S['seconds']}s")


if __name__ == "__main__":
    main()
