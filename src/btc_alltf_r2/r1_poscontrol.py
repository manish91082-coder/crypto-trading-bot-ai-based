"""BTC-ALLTF-R2 (2026-10-29): POSITIVE CONTROL for the LOCKED BTC-ALLTF gates (audit F3). A deliberately look-ahead "noisy
oracle" (blocks of 10 bars, the block is 'in' when its realised trade goes up, flipped with probability 1 - acc) is traded on
BTC spot with the locked engine and judged by exactly the locked gates G1..G7 of that job (its p is added to the job's p list
for BH; DSR with the job's N and V; control, years, 2x fee and delay as in study.py). If the gates rarely pass even an oracle
with a real, known edge, a "0 PASS" from them says little. The daily mark-to-market Newey-West t of the same oracle on BTC is
written next to it.
Output: <RUN>/r1pos/r1_poscontrol.csv
Usage: python src/btc_alltf_r2/r1_poscontrol.py --run <R2 RUN dir>"""
import argparse
import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402
import study                                                                  # noqa: E402
from xcoin import ctrl_state                                                  # noqa: E402

E = K.E
C = K.CFG["controls"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    out = Path(a.run) / "r1pos"
    out.mkdir(parents=True, exist_ok=True)
    g = study.CFG["gates"]
    rows = []
    for market, tf in C["r1_poscontrol_jobs"]:
        b = study.load_bars(market, tf)
        atr = np.load(study.STATES / f"{market}_{tf}_atr14.npy")
        B = E.Bars(b.ts.values, b.open.values, b.high.values, b.low.values, b.close.values, atr)
        ts, nbars = B.ts, B.n
        fee = E.fees()[market]
        fund, cfb = study.funding_tables(market, ts)
        span_years = (ts[-1] - ts[0]) / (365.25 * K.DAY)
        years = list(range(pd.Timestamp(int(ts[0]), unit="ms").year, 2027))
        J = pd.read_parquet(K.R1RUN / market / tf / "configs.parquet", columns=["p"])
        S = json.loads((K.R1RUN / market / tf / "summary.json").read_text())
        pj = J.p.fillna(1.0).values
        d1 = pd.read_parquet(K.PROJ / f"data/derived/btc_alltf/bars/{market}_1d.parquet", columns=["ts", "close"])
        day0 = int(d1.ts.iloc[0] // K.DAY)
        nd = int(K.ms(K.CFG["btc_grid_end"]) // K.DAY - day0)
        close = pd.Series(d1.close.values, index=d1.ts.values // K.DAY - day0).reindex(np.arange(nd)).values
        nxt = np.r_[ts[1:], K.ms(K.CFG["btc_grid_end"])]
        for acc in C["pos_acc"]:
            for seed in range(C["r1_poscontrol_seeds"]):
                nm = f"POS|acc{acc:.2f}|B{C['pos_block_bars']}|s{seed}"
                st = ctrl_state(nm, B.o, f"R1POS|{nm}|{market}|{tf}")
                T = E.run(B, st, 1, "X0_SIG")
                t_in, t_out = ts[T["ei"]], ts[T["xi"]]
                gross, fe, fu, net, mae, mfe = E.pnl(T, 1, fee, fund, t_in, t_out)
                bars_held = (T["xi"] - T["ei"]).astype(np.int32)
                r = study.metrics(net, gross, fe, fu, t_in, bars_held, T["reason"], mae, mfe, nbars, span_years, years)
                n = r["n"]
                cm, cs, cn = E.control(B, cfb, 0, nbars, 1, np.maximum(bars_held, 1), int(min(study.CFG["control"]["max_reps"], max(
                    study.CFG["control"]["min_reps"], np.ceil(study.CFG["control"]["target_draws"] / max(n, 1))))), zlib.crc32(nm.encode()), fee)
                z = (r["mean"] - cm) / np.sqrt(r["sd"] ** 2 / n + cs ** 2 / cn) if n > 1 else np.nan
                G1 = r["n_D"] >= g["G1_nD"] and r["n_V"] >= g["G1_nV"] and r["n_H"] >= g["G1_nH"]
                G2 = r["mean_D"] > 0 and r["mean_V"] > 0 and r["mean_H"] > 0
                q = K.bh(np.r_[pj, r["p"]])[-1]
                G3 = q <= g["G3_q"]
                G4 = z >= g["G4_z"]
                yn = np.array([r[f"n_{y}"] for y in years]); ys = np.array([r[f"sum_{y}"] for y in years])
                el = yn >= g["G6_min_trades_year"]
                G6 = el.sum() >= g["G6_min_years"] and ((ys > 0) & el).sum() >= np.ceil(g["G6_share"] * el.sum())
                dsr = float(study.dsr(r["mean"], r["sd"], n, r["skew"], r["kurt"], S["N_for_dsr"], S["sr_var"])) if n >= 30 and r["sd"] > 0 else np.nan
                G7 = dsr >= g["G7_dsr"]
                T1 = E.run(B, st, 1, "X0_SIG", delay=1)
                _, _, _, n1, _, _ = E.pnl(T1, 1, fee, fund, ts[T1["ei"]], ts[T1["xi"]])
                h1 = ts[T1["ei"]] >= study.P_H
                G5 = r["mean_H_2xfee"] > 0 and (n1[h1].mean() if h1.any() else -1) > 0
                gates = dict(G1=G1, G2=G2, G3=G3, G4=G4, G5=G5, G6=G6, G7=G7)
                add = np.where(np.isin(T["reason"], (3, 5, 7, 9, 11)), (nxt - ts)[T["xi"]] // 2, np.where(T["reason"] == 10, (nxt - ts)[T["xi"]] - 1, 0))
                L, _, _ = K.mtm(np.zeros(n, np.int64), t_in, t_out + add, T["px_in"], net, np.ones(n), close, day0, 1, nd)
                dr = np.expm1(L[0])
                tt, pp, _ = K.nw_t(dr)
                P = K.perf(dr)
                rows.append(dict(market=market, tf=tf, acc=acc, seed=seed, n=n, mean=r["mean"], winrate=r["winrate"], equity=r["equity_end"],
                                 q=q, ctrl_z=z, dsr=dsr, **gates, verdict="INSUFFICIENT" if not G1 else ("PASS" if all(gates.values()) else "FAIL"),
                                 daily_sharpe=P["sharpe"], daily_cagr=P["cagr"], nw_t=tt, nw_p=pp))
            print(f"r1pos {market} {tf} acc {acc}: done", flush=True)
    D = pd.DataFrame(rows)
    D.to_csv(out / "r1_poscontrol.csv", index=False)


if __name__ == "__main__":
    main()
