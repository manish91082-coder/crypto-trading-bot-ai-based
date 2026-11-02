"""
Step 25 data: 15m and 5m spot klines for the coins that are ever in the Step 23/24 TRAIN or TEST universes (2020-01..2026-09)
and for the Step 22 2018-19 universe coins (2017-08..2019-12). Same evidence rules as download_universe_all_usdt.py
(S3 listing, SHA256 vs Binance .CHECKSUM, per-row ms/us detection, rows inside their month, first continuous run of
months, atomic writes, resume); only the file name (<SYM>_<tf>_full.csv.gz) and the gap step differ.
Timestamps are written with a FIXED format (ms) so mixed formats can never occur (lesson of Step 22).
Outputs: data/universe_hf/{15m,5m}/, data/universe_pre2020_hf/{15m,5m}/, logs/hf_download/
"""
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "downloaders", SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import download_universe_all_usdt as D
from config import DATA_DIR, LOGS_DIR

LOG = LOGS_DIR / "hf_download"
STEP = {"15m": pd.Timedelta(minutes=15), "5m": pd.Timedelta(minutes=5)}


def do_symbol(sym, tf, out_dir, pool, tag):
    target = out_dir / f"{sym}_{tf}_full.csv.gz"
    if target.exists():
        return None, []
    ms = D.list_months(sym, tf)
    if not ms:
        return dict(symbol=sym, tf=tf, range=tag, status="no files in range", months_listed=0, months_kept=0, first="", last="",
                    rows=0, gaps=0, ohlc_inconsistent_rows=0), []
    keep = D.consecutive_months(ms)
    res = list(pool.map(lambda m: D.fetch(sym, tf, m), keep))
    flog = [dict(symbol=sym, tf=tf, range=tag, month=m, sha256=sha, rows=len(df)) for m, (df, sha) in zip(keep, res)]
    d = pd.concat([df for df, _ in res]).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    gaps = int((d.timestamp.diff().dropna() != STEP[tf]).sum())
    bad = int(((d.high < d[["open", "close"]].max(axis=1)) | (d.low > d[["open", "close"]].min(axis=1))).sum())
    tmp = target.with_suffix(target.suffix + ".tmp")
    d.to_csv(tmp, index=False, compression="gzip", date_format="%Y-%m-%d %H:%M:%S.%f")
    tmp.replace(target)
    return dict(symbol=sym, tf=tf, range=tag, status="OK", months_listed=len(ms), months_kept=len(keep),
                first=str(d.timestamp.iloc[0]), last=str(d.timestamp.iloc[-1]), rows=len(d), gaps=gaps,
                ohlc_inconsistent_rows=bad), flog


def coin_lists():
    import core_rows_1d as CR
    import step13_unseen_coins_1d as S13
    import step15_slow_relative_1d as S15
    import step23_4h_brain as S23
    split = pd.read_csv(S15.SPLIT)
    A, B = set(split[split.half == "A_design"].symbol), set(split[split.half == "B_confirm"].symbol)
    dk, lk, dn, ln, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", S23.END)
    data, last = {**dk, **dn}, {**lk, **ln}
    te = S23.daily_members(data, last, list(dk) + sorted(B & set(data)), 20, pd.Timestamp("2020-12-31"), S23.END)
    tr = sorted(A & set(data))
    trm = S23.daily_members(data, last, list(dk) + tr, 30, pd.Timestamp("2020-01-01"), S23.END)
    main = sorted(set(te.symbol) | set(trm.symbol))
    pre = sorted(pd.read_csv(LOGS_DIR / "strategy_1d_step22_pre2020" / "U_pre2020_predictions.csv").symbol.unique())
    return main, pre


def main():
    LOG.mkdir(parents=True, exist_ok=True)
    main_coins, pre_coins = coin_lists()
    pd.DataFrame(dict(symbol=main_coins)).to_csv(LOG / "coins_2020_26.csv", index=False)
    pd.DataFrame(dict(symbol=pre_coins)).to_csv(LOG / "coins_2017_19.csv", index=False)
    print(f"coins 2020-26: {len(main_coins)}, coins 2017-19: {len(pre_coins)}", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(D.THREADS) as pool:
        for tag, first, last, coins, root in (("2020_26", "2020-01", "2026-09", main_coins, DATA_DIR / "universe_hf"),
                                              ("2017_19", "2017-08", "2019-12", pre_coins, DATA_DIR / "universe_pre2020_hf")):
            D.FIRST, D.LAST = first, last
            for tf in ("15m", "5m"):
                out_dir = root / tf
                out_dir.mkdir(parents=True, exist_ok=True)
                for k, s in enumerate(coins):
                    info, flog = do_symbol(s, tf, out_dir, pool, tag)
                    if flog:
                        fp = LOG / f"files_log_{tag}_{tf}.csv"
                        pd.DataFrame(flog).to_csv(fp, mode="a", index=False, header=not fp.exists())
                    if info:
                        sp = LOG / f"symbols_{tag}_{tf}.csv"
                        pd.DataFrame([info]).to_csv(sp, mode="a", index=False, header=not sp.exists())
                    if k % 20 == 0:
                        print(f"[{tag} {tf}] {k + 1}/{len(coins)} {s} ({time.time() - t0:.0f}s)", flush=True)
                print(f"[{tag} {tf}] done ({time.time() - t0:.0f}s)", flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
