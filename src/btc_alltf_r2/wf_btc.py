"""BTC-ALLTF-R2 (2026-10-29): walk-forward test of the SELECTION PROCEDURE on BTC (protocol section 5). At every quarter start
R the procedure ranks every config of the pool by its daily mark-to-market score over the lookback window [R - lookback, R)
(data before R only), keeps configs with >= min entries in that window, holds the top k equally weighted (daily rebalanced)
until the next quarter start, and pays the fee once per side on every weight change (conservative: as if every switched
config were in a position). The out-of-sample (OOS) daily returns of the procedure are what a trader using this research
in real time would have had.
Pools: each of the 22 BTC jobs, all spot TFs together, all futures TFs together (the all-TF pick is the exact top k of the
union, built from each job's own top k). Settings: the primary one plus the sensitivity list of R2_CONFIG.json.
Outputs (logs/btc_alltf_r2_2026_10_29/<RUN>/wf/): wf_oos.parquet (daily OOS returns per pool x setting), wf_picks.csv
(every quarter's picks), wf_btc_series.parquet (BTC close-to-close and the procedure's daily signed exposure).
Usage: python src/btc_alltf_r2/wf_btc.py --run <R2 RUN dir>"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402

W = K.CFG["walk_forward"]
BARS = K.PROJ / "data/derived/btc_alltf/bars"


def settings():
    p = dict(W["primary"])
    out = [("primary", p)]
    for s in W["sensitivity"]:
        q = dict(p); q.update(s)
        out.append(("+".join(f"{k}={v}" for k, v in s.items()), q))
    return out


def quarters(lo, hi):
    q = pd.date_range(lo, hi, freq="QS", tz="UTC")
    return [int(x.value // 10 ** 6) for x in q if x.value // 10 ** 6 < K.ms(hi)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    out = Path(a.run) / "wf"
    out.mkdir(parents=True, exist_ok=True)
    oos_lo, oos_hi = K.ms(W["oos_start"]), K.ms(W["oos_end"])
    od0, odn = oos_lo // K.DAY, (oos_hi - oos_lo) // K.DAY
    Rs = quarters(W["oos_start"], W["oos_end"])
    SET = settings()
    fee = K.E.fees()
    series, picks = {}, []
    # union candidates for the all-TF pools: per market, setting, quarter -> list of (score, tf, cfg, oos returns, signed exposure)
    union = {}
    for market in ("spot", "futures"):
        for tf in K.CFG["r1_jobs"][market]:
            Z = np.load(K.DER / "mtm" / f"{market}_{tf}.npz")
            day0, nd = int(Z["day0"]), int(Z["nd"])
            r = np.expm1(Z["L"].astype(np.float64))
            X = Z["X"].astype(np.float32)
            N = Z["N"].astype(np.int32)
            cfg = Z["cfg"]
            C = pd.read_parquet(K.R1RUN / market / tf / "configs.parquet", columns=["cfg", "name", "dir"]).set_index("cfg").loc[cfg]
            dirs = C.dir.values.astype(float)
            for sname, s in SET:
                ser = np.zeros(odn)
                expo = np.zeros(odn)
                w_old = {}
                for qi, R in enumerate(Rs):
                    Rd = R // K.DAY - day0
                    nxt = (Rs[qi + 1] if qi + 1 < len(Rs) else oos_hi) // K.DAY - day0
                    a0 = max(Rd - s["lookback_days"], 0)
                    span = Rd - a0
                    sel = []
                    if span >= s["min_lookback_days"]:
                        ent = N[:, a0:Rd].sum(1)
                        w = r[:, a0:Rd]
                        m = w.mean(1)
                        sd = w.std(1, ddof=1)
                        if s["metric"] == "sharpe":
                            sc = np.where(sd > 0, m / np.where(sd > 0, sd, 1), np.nan)
                        else:
                            sc = np.exp(np.log1p(w).sum(1) * 365.0 / span) - 1
                        ok = (ent >= s["min_entries_in_lookback"]) & (sd > 0) & np.isfinite(sc)
                        idx = np.nonzero(ok)[0]
                        sel = idx[np.lexsort((cfg[idx], -sc[idx]))][:s["k"]]
                        key = (market, sname, qi)
                        union.setdefault(key, [])
                        for i in sel:
                            union[key].append((float(sc[i]), tf, int(cfg[i]), r[i, Rd:nxt].copy(), (dirs[i] * X[i, Rd:nxt]).astype(float)))
                    o0, o1 = Rd + day0 - od0, nxt + day0 - od0
                    w_new = {int(cfg[i]): 1.0 / len(sel) for i in sel} if len(sel) else {}
                    if len(sel):
                        ser[o0:o1] = r[sel, Rd:nxt].mean(0)
                        expo[o0:o1] = (dirs[sel][:, None] * X[sel, Rd:nxt]).mean(0)
                    turn = sum(abs(w_new.get(c, 0) - w_old.get(c, 0)) for c in set(w_new) | set(w_old))
                    ser[o0] -= fee[market] * turn * (1 + ser[o0]) if turn else 0.0
                    w_old = w_new
                    picks.append(dict(pool=f"{market}_{tf}", setting=sname, quarter=pd.Timestamp(R, unit="ms").strftime("%Y-%m-%d"),
                                      picks=";".join(C.name.values[i] for i in sel), turnover=turn))
                series[(f"{market}_{tf}", sname)] = (ser, expo)
            print(f"wf {market} {tf} done", flush=True)
            del r, X, N
        # all-TF pool of this market: exact global top k = top k of the union of the per-job top k
        for sname, s in SET:
            ser = np.zeros(odn)
            expo = np.zeros(odn)
            w_old = {}
            for qi, R in enumerate(Rs):
                cand = union.get((market, sname, qi), [])
                cand = sorted(cand, key=lambda x: (-x[0], x[1], x[2]))[:s["k"]]
                Rd = R // K.DAY - od0
                nxt = (Rs[qi + 1] if qi + 1 < len(Rs) else oos_hi) // K.DAY - od0
                w_new = {(c[1], c[2]): 1.0 / len(cand) for c in cand} if cand else {}
                if cand:
                    ser[Rd:nxt] = np.mean([c[3] for c in cand], axis=0)
                    expo[Rd:nxt] = np.mean([c[4] for c in cand], axis=0)
                turn = sum(abs(w_new.get(c, 0) - w_old.get(c, 0)) for c in set(w_new) | set(w_old))
                ser[Rd] -= fee[market] * turn * (1 + ser[Rd]) if turn else 0.0
                w_old = w_new
                picks.append(dict(pool=f"{market}_all", setting=sname, quarter=pd.Timestamp(R, unit="ms").strftime("%Y-%m-%d"),
                                  picks=";".join(f"{c[1]}:{c[2]}" for c in cand), turnover=turn))
            series[(f"{market}_all", sname)] = (ser, expo)
        union = {k: v for k, v in union.items() if k[0] != market}
    dates = pd.date_range(W["oos_start"], periods=odn, freq="D", tz="UTC")
    rows = []
    for (pool, sname), (ser, expo) in series.items():
        rows.append(pd.DataFrame({"date": dates, "pool": pool, "setting": sname, "ret": ser, "expo": expo}))
    pd.concat(rows, ignore_index=True).to_parquet(out / "wf_oos.parquet", index=False)
    pd.DataFrame(picks).to_csv(out / "wf_picks.csv", index=False)
    bt = {}
    for market in ("spot", "futures"):
        d1 = pd.read_parquet(BARS / f"{market}_1d.parquet", columns=["ts", "close"])
        c = pd.Series(d1.close.values, index=d1.ts.values // K.DAY)
        bt[market] = (c / c.shift(1) - 1).reindex(np.arange(od0, od0 + odn)).values
    pd.DataFrame({"date": dates, "btc_spot": bt["spot"], "btc_futures": bt["futures"]}).to_parquet(out / "wf_btc_series.parquet", index=False)
    print(f"wf written: {len(series)} pool x setting series, {len(Rs)} quarters")


if __name__ == "__main__":
    main()
