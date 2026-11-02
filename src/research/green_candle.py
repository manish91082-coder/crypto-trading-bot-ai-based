"""Green-candle study: BTC January 2026 on all timeframes, plus the user's red->green / green->red rule.

Protocol: logs/green_candle_2026/GREEN_CANDLE_PROTOCOL_PREREGISTERED.md (SHA in PROTOCOL_SHA256.txt).
This script shares no code with the methods bench or the oracle study.
Run: python src/research/green_candle.py
"""
import hashlib, json, math, sys, time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "green_candle_2026"
PROTO = OUT / "GREEN_CANDLE_PROTOCOL_PREREGISTERED.md"
PROTO_SHA = "fe70c33091bec342c757cf7f88d2fbc7a77dc8810dec0cbac6f7064eac396d7d"
INPUTS = {
    "5m": "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz",
    "15m": "data/universe_hf/15m/BTCUSDT_15m_full.csv.gz",
    "1h": "data/universe_all/1h/BTCUSDT_1h_full.csv.gz",
    "1d": "data/universe_all/1d/BTCUSDT_1d.csv",
}
FEES = ROOT / "deploy" / "fees.json"
TFS = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D"}
TF_MIN = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
START, END = pd.Timestamp("2020-01-01"), pd.Timestamp("2026-10-01")
PERIODS = {"JAN": ("2026-01-01", "2026-02-01"), "FS26": ("2026-02-01", "2026-10-01")}
for _y in range(2020, 2026):
    PERIODS[f"Y{_y}"] = (f"{_y}-01-01", f"{_y + 1}-01-01")
YEARS = [f"Y{y}" for y in range(2020, 2026)]
RULES = ["R1", "R2"]
N_BOOT, BOOT_SEED, N_RAND = 10_000, 7, 1000
BONF = 1 - 0.05 / 12

LOG = OUT / "run_log.txt"


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def costs():
    f = json.loads(FEES.read_text())
    return {
        "spot": f["rules"]["paper_spot_per_side"],
        "fut": f["rules"]["paper_futures_taker_per_side"],
        "fut_maker": f["futures_usdm"]["bnb_maker"] + f["impact_per_side"],
    }


def read_bars(rel):
    d = pd.read_csv(ROOT / rel)
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    dup = int(d["timestamp"].duplicated().sum())
    d = d.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    return d.loc[(d.index >= START) & (d.index < END), ["open", "high", "low", "close"]], dup


def aggregate(d5, tf):
    if tf == "5m":
        a = d5.copy()
        a["n5"] = 1
        return a
    g = d5.resample(TFS[tf], label="left", closed="left")
    a = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last(), "n5": g["open"].count()})
    return a[a["n5"] > 0]


def colour(o, c):
    return np.sign(c - o).astype(int)  # 1 G, -1 R, 0 D


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (mid - half, mid + half)


def green_runs(col):
    """List of (start, length) of maximal blocks of col == 1."""
    runs, k, n = [], 0, len(col)
    while k < n:
        if col[k] == 1:
            j = k
            while j + 1 < n and col[j + 1] == 1:
                j += 1
            runs.append((k, j - k + 1))
            k = j + 1
        else:
            k += 1
    return runs


def part_a(b, c):
    o, cl = b["open"].to_numpy(), b["close"].to_numpy()
    col = colour(o, cl)
    r = cl / o - 1
    n = len(col)
    nG, nR, nD = int((col == 1).sum()), int((col == -1).sum()), int((col == 0).sum())
    pG = nG / n
    out = {"n_bars": n, "incomplete_bars": int((b["n5"] < b["n5"].max()).sum()) if n else 0,
           "G": nG, "R": nR, "D": nD, "G_share": pG, "G_share_wilson95": wilson(nG, n)}
    for name, m in (("G", col == 1), ("R", col == -1)):
        x = r[m]
        out[f"r_{name}"] = {"mean": float(x.mean()), "median": float(np.median(x)),
                            "p25": float(np.percentile(x, 25)), "p75": float(np.percentile(x, 75))}
    out["G_share_r_gt_spot_rt"] = float((r[col == 1] > 2 * c["spot"]).mean())
    out["G_share_r_gt_fut_rt"] = float((r[col == 1] > 2 * c["fut"]).mean())
    # transitions
    lab = {1: "G", -1: "R", 0: "D"}
    tc = {f"{lab[a]}{lab[bb]}": int(((col[:-1] == a) & (col[1:] == bb)).sum()) for a in (1, -1, 0) for bb in (1, -1, 0)}
    out["transition_counts"] = tc
    tp = {}
    for a in "GRD":
        tot = sum(tc[a + x] for x in "GRD")
        for x in "GRD":
            tp[f"P({x}|{a})"] = tc[a + x] / tot if tot else float("nan")
    out["transition_probs"] = tp
    # runs test G vs not-G
    g = (col == 1).astype(int)
    n1, n2 = int(g.sum()), int(n - g.sum())
    nruns = 1 + int((g[1:] != g[:-1]).sum())
    mu = 2 * n1 * n2 / n + 1
    var = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n * n * (n - 1))
    z = (nruns - mu) / math.sqrt(var)
    out["runs_test"] = {"runs": nruns, "expected": mu, "z": z, "p_two_sided": math.erfc(abs(z) / math.sqrt(2))}
    out["lag1_autocorr_r"] = float(np.corrcoef(r[:-1], r[1:])[0, 1])
    # green runs
    runs = green_runs(col)
    rows = []
    for k, L in runs:
        last = k + L - 1
        gross = cl[last] / o[k] - 1
        rows.append({"start": b.index[k], "L": L, "open_first": o[k], "close_last": cl[last], "gross": gross,
                     "net_spot": gross - 2 * c["spot"], "net_fut": gross - 2 * c["fut"],
                     "g1": r[k], "rest": cl[last] / cl[k] - 1,
                     "after": r[last + 1] if last + 1 < n else np.nan,
                     "after_col": int(col[last + 1]) if last + 1 < n else np.nan})
    rr = pd.DataFrame(rows)
    nr = len(rr)
    obs = {str(k): int((rr["L"] == k).sum()) for k in (1, 2, 3, 4)}
    obs["5+"] = int((rr["L"] >= 5).sum())
    exp = {str(k): nr * (1 - pG) * pG ** (k - 1) for k in (1, 2, 3, 4)}
    exp["5+"] = nr * pG ** 4
    out["run_lengths_observed"], out["run_lengths_expected_indep"] = obs, exp
    out["mean_run_length"] = float(rr["L"].mean())
    out["oracle"] = {"n_runs": nr, "sum_gross": float(rr["gross"].sum()),
                     "sum_net_spot": float(rr["net_spot"].sum()), "sum_net_fut": float(rr["net_fut"].sum()),
                     "runs_net_spot_pos": int((rr["net_spot"] > 0).sum()),
                     "runs_net_fut_pos": int((rr["net_fut"] > 0).sum()),
                     "sum_r_all_green_candles": float(r[col == 1].sum())}
    out["anatomy_means"] = {"g1": float(rr["g1"].mean()), "rest": float(rr["rest"].mean()),
                            "after": float(rr["after"].mean()),
                            "after_is_R_share": float((rr["after_col"] == -1).mean())}
    out["unconditional_mean_r"] = float(r.mean())
    return out, rr, col, r


def run_rule(b, rule, tf):
    """Trades for one period. Prices P = opens + [last close]; entry/exit are indices into P."""
    o, cl = b["open"].to_numpy(), b["close"].to_numpy()
    t = b.index
    col = colour(o, cl)
    n = len(col)
    P = np.append(o, cl[-1])
    trades, pos, e = [], False, -1
    for k in range(n):
        if not pos:
            if rule == "R1":
                sig = k >= 1 and col[k] == 1 and col[k - 1] != 1
            else:
                sig = k >= 2 and col[k] == 1 and col[k - 1] == 1 and col[k - 2] != 1
            if sig and k + 1 < n:
                pos, e = True, k + 1
            continue
        if k >= e and col[k] == -1:
            x = k + 1 if k + 1 < n else n
            trades.append((e, x, x == n))
            pos = False
    if pos:
        trades.append((e, n, True))
    rows = []
    for e, x, forced in trades:
        rows.append({"entry_i": e, "exit_i": x, "entry_time": t[e],
                     "exit_time": t[x] if x < n else t[-1] + pd.Timedelta(minutes=TF_MIN[tf]),
                     "attr_time": t[x] if x < n else t[-1],
                     "entry_px": P[e], "exit_px": P[x], "bars": x - e, "forced": forced,
                     "gross": P[x] / P[e] - 1})
    return pd.DataFrame(rows), P


def maxdd(net):
    eq = np.concatenate([[1.0], np.cumprod(1 + net)])
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1).min())


def boot_mean_ci(x, levels):
    n = len(x)
    rng = np.random.default_rng(BOOT_SEED)
    chunk = max(1, 4_000_000 // max(n, 1))
    means = np.empty(N_BOOT)
    i = 0
    while i < N_BOOT:
        m = min(chunk, N_BOOT - i)
        idx = rng.integers(0, n, size=(m, n))
        means[i:i + m] = x[idx].mean(axis=1)
        i += m
    return {lv: (float(np.quantile(means, (1 - lv) / 2)), float(np.quantile(means, 1 - (1 - lv) / 2))) for lv in levels}


def main():
    t0 = time.time()
    assert sha(PROTO) == PROTO_SHA, "protocol SHA mismatch"
    assert (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0] == PROTO_SHA
    log(f"start; protocol {PROTO_SHA[:12]}; code {sha(Path(__file__))[:12]}")
    c = costs()
    log(f"costs per side from deploy/fees.json: {c}")
    man = [{"file": v, "sha256": sha(ROOT / v), "bytes": (ROOT / v).stat().st_size} for v in INPUTS.values()]
    man.append({"file": "deploy/fees.json", "sha256": sha(FEES), "bytes": FEES.stat().st_size})
    pd.DataFrame(man).to_csv(OUT / "input_manifest.csv", index=False)

    d5, dup5 = read_bars(INPUTS["5m"])
    full5 = pd.date_range(START, END - pd.Timedelta(minutes=5), freq="5min")
    miss5 = full5.difference(d5.index)
    log(f"5m rows {len(d5)}, duplicates dropped {dup5}, missing 5m bars {len(miss5)} "
        f"(JAN missing {int(((miss5 >= '2026-01-01') & (miss5 < '2026-02-01')).sum())})")
    bars = {tf: aggregate(d5, tf) for tf in TFS}
    checks = {}
    for tf in ("15m", "1h", "1d"):
        f, dup = read_bars(INPUTS[tf])
        a = bars[tf]
        j = a.join(f, how="outer", rsuffix="_f")
        only_a = int(j["open_f"].isna().sum())
        only_f = int(j["open"].isna().sum())
        jj = j.dropna()
        ohlc = ["open", "high", "low", "close"]
        bad = np.zeros(len(jj), dtype=bool)
        for x in ohlc:
            bad |= ~np.isclose(jj[x], jj[x + "_f"], rtol=1e-9, atol=0)
        nbad = int(bad.sum())
        jan = jj[(jj.index >= "2026-01-01") & (jj.index < "2026-02-01")]
        jan_bad = int(sum(int((~np.isclose(jan[x], jan[x + "_f"], rtol=1e-9, atol=0)).sum()) for x in ohlc))
        checks[tf] = {"both": len(jj), "only_aggregate": only_a, "only_file": only_f, "ohlc_mismatch_bars": nbad,
                      "jan_ohlc_mismatch_values": jan_bad, "file_duplicates": dup}
        log(f"aggregate check {tf}: {checks[tf]}")

    # ---- Part A (JAN)
    pa, runs_all, bars_jan = {}, [], []
    for tf in TFS:
        b = bars[tf]
        bj = b[(b.index >= "2026-01-01") & (b.index < "2026-02-01")]
        res, rr, col, r = part_a(bj, c)
        pa[tf] = res
        rr.insert(0, "tf", tf)
        runs_all.append(rr)
        x = bj.copy()
        x["colour"], x["r"], x["tf"] = col, r, tf
        bars_jan.append(x.reset_index().rename(columns={"index": "timestamp"}))
        log(f"partA {tf}: n {res['n_bars']} G {res['G']} R {res['R']} D {res['D']} P(G|G) {res['transition_probs']['P(G|G)']:.4f} "
            f"runs z {res['runs_test']['z']:.2f} oracle net fut {res['oracle']['sum_net_fut']:.4f}")
    pd.concat(bars_jan).to_parquet(OUT / "bars_jan2026.parquet", index=False)
    pd.concat(runs_all).to_csv(OUT / "runs_jan2026.csv", index=False)
    (OUT / "partA_jan2026.json").write_text(json.dumps(pa, indent=1, default=str))

    # ---- Part B: rules on all periods
    trades, metrics, rc_rows = [], [], []
    rand_store = {}  # (rule, tf, period) -> per-seed gross sums
    for tf in TFS:
        b = bars[tf]
        for per, (s, e) in PERIODS.items():
            bp = b[(b.index >= s) & (b.index < e)]
            bh = float(bp["close"].iloc[-1] / bp["open"].iloc[0] - 1)
            for rule in RULES:
                tr, P = run_rule(bp, rule, tf)
                tr.insert(0, "period", per)
                tr.insert(0, "tf", tf)
                tr.insert(0, "rule", rule)
                for m, cc in c.items():
                    tr[f"net_{m}"] = tr["gross"] - 2 * cc
                trades.append(tr)
                # random control
                h = tr["bars"].to_numpy()
                hi = len(P) - h  # u in [0, hi)
                sums = np.empty(N_RAND)
                for sd in range(1, N_RAND + 1):
                    u = np.random.default_rng(sd).integers(0, hi)
                    sums[sd - 1] = (P[u + h] / P[u] - 1).sum()
                rand_store[(rule, tf, per)] = (sums, len(tr))
                act = float(tr["gross"].mean())
                rc_rows.append({"rule": rule, "tf": tf, "period": per, "n": len(tr), "actual_mean_gross": act,
                                "rand_mean_gross_median": float(np.median(sums / len(tr))),
                                "p": float((sums / len(tr) >= act).mean())})
                ci = boot_mean_ci(tr["gross"].to_numpy(), (0.95, BONF))
                for m, cc in c.items():
                    nt = tr[f"net_{m}"].to_numpy()
                    w = int((nt > 0).sum())
                    metrics.append({"rule": rule, "tf": tf, "period": per, "cost": m, "n": len(tr), "wins": w,
                                    "win_rate": w / len(tr), "wilson_lo": wilson(w, len(tr))[0], "wilson_hi": wilson(w, len(tr))[1],
                                    "mean_net": float(nt.mean()), "median_net": float(np.median(nt)), "sum_net": float(nt.sum()),
                                    "compounded": float(np.prod(1 + nt) - 1), "maxdd": maxdd(nt),
                                    "ci95_lo": ci[0.95][0] - 2 * cc, "ci95_hi": ci[0.95][1] - 2 * cc,
                                    "ciB_lo": ci[BONF][0] - 2 * cc, "ciB_hi": ci[BONF][1] - 2 * cc,
                                    "time_in_market": float(tr["bars"].sum() / len(bp)), "avg_bars": float(tr["bars"].mean()),
                                    "forced": int(tr["forced"].sum()), "buy_hold": bh, "n_bars_period": len(bp)})
            log(f"rules {tf} {per}: R1 n {metrics[-6]['n']} mean fut {metrics[-5]['mean_net']:.5f} | "
                f"R2 n {metrics[-3]['n']} mean fut {metrics[-2]['mean_net']:.5f}")
    T = pd.concat(trades, ignore_index=True)
    # pooled P2025
    for tf in TFS:
        for rule in RULES:
            tp = T[(T.rule == rule) & (T.tf == tf) & (T.period.isin(YEARS))]
            g = tp["gross"].to_numpy()
            ci = boot_mean_ci(g, (0.95, BONF))
            sums = sum(rand_store[(rule, tf, y)][0] for y in YEARS)
            act = float(g.mean())
            rc_rows.append({"rule": rule, "tf": tf, "period": "P2025", "n": len(tp), "actual_mean_gross": act,
                            "rand_mean_gross_median": float(np.median(sums / len(tp))), "p": float((sums / len(tp) >= act).mean())})
            for m, cc in c.items():
                nt = tp[f"net_{m}"].to_numpy()
                w = int((nt > 0).sum())
                metrics.append({"rule": rule, "tf": tf, "period": "P2025", "cost": m, "n": len(tp), "wins": w,
                                "win_rate": w / len(tp), "wilson_lo": wilson(w, len(tp))[0], "wilson_hi": wilson(w, len(tp))[1],
                                "mean_net": float(nt.mean()), "median_net": float(np.median(nt)), "sum_net": float(nt.sum()),
                                "compounded": float(np.prod(1 + nt) - 1), "maxdd": maxdd(nt),
                                "ci95_lo": ci[0.95][0] - 2 * cc, "ci95_hi": ci[0.95][1] - 2 * cc,
                                "ciB_lo": ci[BONF][0] - 2 * cc, "ciB_hi": ci[BONF][1] - 2 * cc,
                                "time_in_market": float("nan"), "avg_bars": float(tp["bars"].mean()),
                                "forced": int(tp["forced"].sum()), "buy_hold": float("nan"), "n_bars_period": float("nan")})
    M = pd.DataFrame(metrics)
    RC = pd.DataFrame(rc_rows)
    T.to_parquet(OUT / "trades_all.parquet", index=False)
    M.to_csv(OUT / "metrics.csv", index=False)
    RC.to_csv(OUT / "random_control.csv", index=False)

    # daily (JAN, every day), monthly, yearly; attributed by attr_time
    T["day"] = T["attr_time"].dt.strftime("%Y-%m-%d")
    T["month"] = T["attr_time"].dt.strftime("%Y-%m")
    T["year"] = T["attr_time"].dt.year
    days = pd.date_range("2026-01-01", "2026-01-31", freq="D").strftime("%Y-%m-%d")
    TJ = T[T.period == "JAN"]
    drows = []
    for rule in RULES:
        for tf in TFS:
            x = TJ[(TJ.rule == rule) & (TJ.tf == tf)].groupby("day")
            for dd in days:
                if dd in x.groups:
                    gg = x.get_group(dd)
                    drows.append({"rule": rule, "tf": tf, "day": dd, "n": len(gg), "net_fut": gg["net_fut"].sum(),
                                  "net_spot": gg["net_spot"].sum(), "gross": gg["gross"].sum()})
                else:
                    drows.append({"rule": rule, "tf": tf, "day": dd, "n": 0, "net_fut": 0.0, "net_spot": 0.0, "gross": 0.0})
    pd.DataFrame(drows).to_csv(OUT / "daily_jan2026.csv", index=False)
    months = pd.period_range("2020-01", "2026-09", freq="M").strftime("%Y-%m")
    mrows = []
    for rule in RULES:
        for tf in TFS:
            x = T[(T.rule == rule) & (T.tf == tf)].groupby("month")
            for mm in months:
                gg = x.get_group(mm) if mm in x.groups else T.iloc[0:0]
                mrows.append({"rule": rule, "tf": tf, "month": mm, "n": len(gg), "net_fut": float(gg["net_fut"].sum()),
                              "net_spot": float(gg["net_spot"].sum()), "gross": float(gg["gross"].sum())})
    MO = pd.DataFrame(mrows)
    MO.to_csv(OUT / "monthly.csv", index=False)
    Y = T.groupby(["rule", "tf", "year"]).agg(n=("gross", "size"), net_fut=("net_fut", "sum"),
                                                net_spot=("net_spot", "sum"), gross=("gross", "sum")).reset_index()
    Y.to_csv(OUT / "yearly.csv", index=False)

    # ---- Part C decision
    dec = []
    for rule in RULES:
        for tf in TFS:
            mp = M[(M.rule == rule) & (M.tf == tf) & (M.cost == "fut")].set_index("period")
            c1 = bool(mp.loc["P2025", "ciB_lo"] > 0)
            c2 = bool(mp.loc["FS26", "mean_net"] > 0)
            mm = MO[(MO.rule == rule) & (MO.tf == tf)]
            share = float((mm["net_fut"] > 0).mean())
            c3 = share >= 0.60
            pr = float(RC[(RC.rule == rule) & (RC.tf == tf) & (RC.period == "P2025")]["p"].iloc[0])
            c4 = pr < 0.05
            dec.append({"rule": rule, "tf": tf, "P2025_ciB_lo": float(mp.loc["P2025", "ciB_lo"]), "C1": c1,
                        "FS26_mean": float(mp.loc["FS26", "mean_net"]), "C2": c2, "months_pos_share": share,
                        "months": len(mm), "C3": c3, "P2025_rand_p": pr, "C4": c4, "candidate": c1 and c2 and c3 and c4})
    D = pd.DataFrame(dec)
    (OUT / "decision.json").write_text(json.dumps(dec, indent=1))
    log(f"decision: candidates {int(D['candidate'].sum())} of {len(D)}")

    res = {"protocol_sha": PROTO_SHA, "code_sha": sha(Path(__file__)), "costs_per_side": c,
           "missing_5m_total": len(miss5), "aggregate_checks": checks, "n_trades_total": len(T),
           "candidates": int(D["candidate"].sum()), "runtime_s": round(time.time() - t0, 1)}
    (OUT / "RESULTS.json").write_text(json.dumps(res, indent=1))
    files = ["input_manifest.csv", "bars_jan2026.parquet", "partA_jan2026.json", "runs_jan2026.csv", "trades_all.parquet",
             "metrics.csv", "daily_jan2026.csv", "monthly.csv", "yearly.csv", "random_control.csv", "decision.json", "RESULTS.json"]
    (OUT / "OUTPUT_SHA256.txt").write_text("".join(f"{sha(OUT / f)}  {f}\n" for f in files))
    log(f"done in {time.time() - t0:.0f} s; outputs hashed")


if __name__ == "__main__":
    main()
