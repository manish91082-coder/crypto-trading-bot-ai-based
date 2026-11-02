"""BTC-ALLTF-R2 (2026-10-29): daily mark-to-market returns of EVERY unique config of the locked BTC-ALLTF run, from its
trades.parquet (nothing is re-simulated). Per job writes data/derived/btc_alltf_r2/mtm/<market>_<tf>.npz:
  cfg [nk], L [nk, nd] float32 daily log return, X [nk, nd] float16 days in position, N [nk, nd] int16 entries, day0, nd
and checks for every config that the sum of its daily log returns equals log(equity_end) of configs.parquet
(-> logs/btc_alltf_r2_2026_10_29/mtm_check.csv).
Usage: python src/btc_alltf_r2/mtm_btc.py [--jobs spot/1d,futures/4h]"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402

BARS = K.PROJ / "data/derived/btc_alltf/bars"
OUT = K.DER / "mtm"


def job(market, tf):
    t0 = time.time()
    run = K.R1RUN / market / tf
    C = pd.read_parquet(run / "configs.parquet", columns=["cfg", "dir", "n", "equity_end"]).sort_values("cfg").reset_index(drop=True)
    b = pd.read_parquet(BARS / f"{market}_{tf}.parquet", columns=["ts", "open"])
    ts, op = b.ts.values.astype(np.int64), b.open.values
    d1 = pd.read_parquet(BARS / f"{market}_1d.parquet", columns=["ts", "close"])
    day0 = int(d1.ts.iloc[0] // K.DAY)
    nd = int(K.ms(K.CFG["btc_grid_end"]) // K.DAY - day0)
    close = pd.Series(d1.close.values, index=d1.ts.values // K.DAY - day0).reindex(np.arange(nd)).values
    nxt = np.r_[ts[1:], K.ms(K.CFG["btc_grid_end"])]
    barlen = nxt - ts
    nk = len(C)
    row = np.full(int(C.cfg.max()) + 1, -1, np.int64)
    row[C.cfg.values] = np.arange(nk)
    dirc = C.dir.values.astype(np.float64)
    L = np.zeros((nk, nd), np.float64)
    X = np.zeros((nk, nd), np.float32)
    N = np.zeros((nk, nd), np.int32)
    f = pq.ParquetFile(run / "trades.parquet")
    ntr = 0
    for g in range(f.metadata.num_row_groups):
        T = f.read_row_group(g, columns=["cfg", "t_in", "t_out", "reason", "net"])
        k = row[T.column("cfg").to_numpy().astype(np.int64)]
        if (k < 0).any():
            raise RuntimeError("trade of an unknown config")
        t_in = T.column("t_in").cast("int64").to_numpy()
        t_out = T.column("t_out").cast("int64").to_numpy()
        rs = T.column("reason").to_numpy()
        net = T.column("net").to_numpy().astype(np.float64)
        i_in = np.searchsorted(ts, t_in)
        i_out = np.searchsorted(ts, t_out)
        if not (np.array_equal(ts[i_in], t_in) and np.array_equal(ts[i_out], t_out)):
            raise RuntimeError("trade time not on a bar open")
        add = np.where(np.isin(rs, (3, 5, 7, 9, 11)), barlen[i_out] // 2, np.where(rs == 10, barlen[i_out] - 1, 0))
        k0, k1 = int(k.min()), int(k.max())
        l_, x_, n_ = K.mtm(k - k0, t_in, t_out + add, op[i_in], net, dirc[k], close, day0, k1 - k0 + 1, nd)
        L[k0:k1 + 1] += l_
        X[k0:k1 + 1] += x_
        N[k0:k1 + 1] += n_
        ntr += len(k)
    if ntr != int(C.n.fillna(0).sum()):
        raise RuntimeError(f"trade count {ntr} != configs n {int(C.n.sum())}")
    s = L.sum(1)
    ref = np.log(np.maximum(C.equity_end.values, 1e-300))
    n = C.n.fillna(0).values
    err = np.abs(s - ref)
    tol = 1e-6 * np.maximum(n, 1) + 1e-6
    ok = (err <= tol) | (C.equity_end.values <= 1e-6)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez(OUT / f"{market}_{tf}.npz", cfg=C.cfg.values.astype(np.int32), L=L.astype(np.float32), X=np.minimum(X, 1.0).astype(np.float16),
             N=np.minimum(N, 32767).astype(np.int16), day0=day0, nd=nd)
    print(f"{market} {tf}: {nk} configs, {ntr:,} trades, sum-check {int(ok.sum())}/{nk} ok, max err {err.max():.2e}, "
          f"{time.time() - t0:.0f}s", flush=True)
    return dict(market=market, tf=tf, configs=nk, trades=ntr, check_ok=int(ok.sum()), max_abs_err=float(err.max()),
                worst_cfg=int(C.cfg.values[np.argmax(err - tol)]), seconds=round(time.time() - t0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="")
    a = ap.parse_args()
    jobs = [j.split("/") for j in a.jobs.split(",")] if a.jobs else \
        [(m, tf) for m in ("spot", "futures") for tf in K.CFG["r1_jobs"][m]]
    rows = [job(m, tf) for m, tf in jobs]
    out = K.R2 / "mtm_check.csv"
    old = pd.read_csv(out) if out.exists() else pd.DataFrame()
    new = pd.DataFrame(rows)
    if len(old):
        old = old[~old.set_index(["market", "tf"]).index.isin(new.set_index(["market", "tf"]).index)]
    pd.concat([old, new], ignore_index=True).to_csv(out, index=False)


if __name__ == "__main__":
    main()
