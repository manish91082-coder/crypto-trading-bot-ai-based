"""
F1: Binance USD-M PERPETUAL public data (Binance Vision) for every coin of the research test universe (Step 19 U,
2021-26): 1h klines + funding rates, 2020-01 .. 2026-09. Every zip SHA256-verified against its .CHECKSUM.
Perp name per coin: the first of [SYM, 1000SYM, 1000000SYM] that has any monthly 1h kline file (404 = did not exist).
A price-scale check against the spot 1h close is done afterwards (gate F1-G2).
Outputs: data/futures_um/<SYM>_perp_1h.csv.gz, <SYM>_funding.csv, logs/futures_um_download/files_log.csv
"""
import sys
import time
import hashlib
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))
from config import DATA_DIR, LOGS_DIR

B = "https://data.binance.vision/data/futures/um/monthly"
OUT, LOG = DATA_DIR / "futures_um", LOGS_DIR / "futures_um_download"
MONTHS = [f"{y}-{m:02d}" for y in range(2020, 2027) for m in range(1, 13) if not (y == 2026 and m > 9)]
KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades",
         "taker_buy_base", "taker_buy_quote", "ignore"]
_S = requests.Session()


def get(url):
    err = None
    for k in range(12):
        try:
            r = _S.get(url, timeout=60)
            if r.status_code in (200, 404):
                return r
            err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            err = str(e)
        time.sleep(min(5 * (k + 1), 90))
    raise RuntimeError(f"{url}: {err}")


def fetch(url):
    r = get(url)
    if r.status_code == 404:
        return None, "404", ""
    c = get(url + ".CHECKSUM")
    assert c.status_code == 200, f"no CHECKSUM {url}"
    sha = hashlib.sha256(r.content).hexdigest()
    assert sha == c.text.split()[0].strip().lower(), f"SHA256 mismatch {url}"
    with zipfile.ZipFile(BytesIO(r.content)) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), header=None, dtype=str)
    if not str(df.iloc[0, 0]).strip().isdigit():          # some files carry a header row
        df = df.iloc[1:].reset_index(drop=True)
    return df, "OK", sha


def ts(x):
    x = pd.to_numeric(x).astype("int64")
    return pd.to_datetime(x, unit="us" if x.iloc[0] > 1e14 else "ms")


def kline_url(p, m):
    q = quote(p)
    return f"{B}/klines/{q}/1h/{q}-1h-{m}.zip"


def funding_url(p, m):
    q = quote(p)
    return f"{B}/fundingRate/{q}/{q}-fundingRate-{m}.zip"


def perp_name(sym):
    """First candidate with at least one monthly 1h kline file (probe a few months, then all)."""
    base = sym[:-4]
    for cand in (sym, f"1000{base}USDT", f"1000000{base}USDT"):
        for m in ("2026-08", "2025-06", "2024-06", "2023-06", "2022-06", "2021-06", "2020-06"):
            if get(kline_url(cand, m)).status_code == 200:
                return cand
        hits = [m for m in MONTHS if get(kline_url(cand, m)).status_code == 200]
        if hits:
            return cand
    return None


def job(sym, p, kind, m):
    cache = OUT / "_cache" / f"{kind}_{p}_{m}.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    url = kline_url(p, m) if kind == "kl" else funding_url(p, m)
    df, st, sha = fetch(url)
    if df is not None and kind == "kl":
        df = df.iloc[:, :12]
        df.columns = KCOLS
        out = pd.DataFrame(dict(timestamp=ts(df.open_time)))
        for c in ("open", "high", "low", "close", "volume", "quote_volume", "taker_buy_quote"):
            out[c] = pd.to_numeric(df[c])
        df = out
    elif df is not None:
        df = pd.DataFrame(dict(time=ts(df.iloc[:, 0]), funding_rate=pd.to_numeric(df.iloc[:, -1])))
    res = (sym, p, kind, m, df, st, sha, url)
    cache.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(res, cache)
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)
    U = pd.read_csv(LOGS_DIR / "strategy_1d_step19_largecap" / "universe_U.csv")
    syms = sorted(U.symbol.unique())
    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        names = dict(zip(syms, ex.map(perp_name, syms)))
    pd.DataFrame([dict(symbol=s, perp=names[s]) for s in syms]).to_csv(LOG / "perp_names.csv", index=False)
    print(f"perp names resolved ({time.time()-t0:.0f}s): {sum(v is not None for v in names.values())}/{len(syms)} have a perpetual", flush=True)
    jobs = [(s, names[s], k, m) for s in syms if names[s] for k in ("kl", "fr") for m in MONTHS]
    with ThreadPoolExecutor(16) as ex:
        res = list(ex.map(lambda a: job(*a), jobs))
    pd.DataFrame([dict(symbol=s, perp=p, kind=k, month=m, status=st, sha256=sha, url=u) for s, p, k, m, _, st, sha, u in res]).to_csv(
        LOG / "files_log.csv", index=False)
    for s in syms:
        p = names[s]
        if not p:
            continue
        kl = [df for s2, _, k, _, df, _, _, _ in res if s2 == s and k == "kl" and df is not None]
        fr = [df for s2, _, k, _, df, _, _, _ in res if s2 == s and k == "fr" and df is not None]
        if kl:
            d = pd.concat(kl).sort_values("timestamp").drop_duplicates("timestamp")
            assert d[["open", "high", "low", "close"]].notna().all().all() and (d.high >= d.low).all(), s
            d.assign(perp=p).to_csv(OUT / f"{s}_perp_1h.csv.gz", index=False, compression="gzip")
        if fr:
            d = pd.concat(fr).sort_values("time").drop_duplicates("time")
            assert d.notna().all().all(), s
            d.assign(perp=p).to_csv(OUT / f"{s}_funding.csv", index=False)
        print(f"[{s}] perp {p}: kline months {len(kl)}, funding months {len(fr)}", flush=True)
    print(f"done ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
