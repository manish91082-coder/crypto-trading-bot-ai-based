"""BTC-ALLTF-R2 (2026-10-29): family S1 = for every cross-coin job, the top-k configs of the BTC run by full-period daily
mark-to-market Sharpe (n >= min trades), as fixed in the protocol. Written BEFORE any other coin is traded; its sha256 goes into
RUN_INFO.json. Output: logs/btc_alltf_r2_2026_10_29/selection_S1.csv
Usage: python src/btc_alltf_r2/select_s1.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402

S = K.CFG["selection"]


def main():
    rows = []
    for market, tfs in K.CFG["xcoin"]["jobs"].items():
        for tf in tfs:
            Z = np.load(K.DER / "mtm" / f"{market}_{tf}.npz")
            r = np.expm1(Z["L"].astype(np.float64))
            C = pd.read_parquet(K.R1RUN / market / tf / "configs.parquet", columns=["cfg", "name", "n"]).set_index("cfg").loc[Z["cfg"]]
            mu, sd = r.mean(1), r.std(1, ddof=1)
            sh = np.where(sd > 0, mu / np.where(sd > 0, sd, 1) * np.sqrt(365), np.nan)
            ok = (C.n.fillna(0).values >= S["S1_min_trades"]) & np.isfinite(sh)
            idx = np.nonzero(ok)[0]
            o = idx[np.lexsort((Z["cfg"][idx], -sh[idx]))][:S["S1_top_k"]]
            for rank, i in enumerate(o, 1):
                P = K.perf(r[i])
                rows.append(dict(market=market, tf=tf, sel_rank=rank, cfg=int(Z["cfg"][i]), name=C.name.values[i], n=int(C.n.values[i]),
                                 btc_sharpe=float(sh[i]), btc_cagr=P["cagr"], btc_maxdd=P["maxdd"], btc_total=P["total"]))
            print(f"{market} {tf}: {ok.sum()} eligible, top {len(o)} selected", flush=True)
    pd.DataFrame(rows).to_csv(K.R2 / "selection_S1.csv", index=False)


if __name__ == "__main__":
    main()
