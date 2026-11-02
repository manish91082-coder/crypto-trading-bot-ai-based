"""
Step 10.1 data (INFORMATION ONLY, no futures trading): Binance USD-M futures public data from Binance Vision for the
30-coin universe, 2020-01 .. 2026-09. Every zip SHA256-verified against its .CHECKSUM.
  * fundingRate      monthly files  -> data/futures_info/<SYM>_funding.csv
  * premiumIndexKlines 1d monthly   -> data/futures_info/<SYM>_premium_1d.csv
  * metrics          daily files    -> data/futures_info/<SYM>_metrics_daily.csv (last 5-min row of each day + day means)
A 404 = that data did not exist for that symbol/period (logged, never filled).
"""
import sys
import time
import hashlib
import zipfile
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "downloaders"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import DATA_DIR, LOGS_DIR, SYMBOLS
from download_1h_full_columns import EXTRA, MONTHS

B = "https://data.binance.vision/data/futures/um"
PERP = {s: s for s in SYMBOLS + EXTRA}
PERP["SHIBUSDT"] = "1000SHIBUSDT"
OUT = DATA_DIR / "futures_info"
DAYS = [d.strftime("%Y-%m-%d") for d in pd.date_range("2020-01-01", "2026-09-30", freq="D")]
_S = requests.Session()


def get(url):
    err = None
    for k in range(12):                                   # survives short internet / DNS outages (~10 min)
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
        return None, "404"
    c = get(url + ".CHECKSUM")
    assert c.status_code == 200, f"no CHECKSUM {url}"
    sha = hashlib.sha256(r.content).hexdigest()
    assert sha == c.text.split()[0].strip().lower(), f"SHA256 mismatch {url}"
    with zipfile.ZipFile(BytesIO(r.content)) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), header=None)
    return df, "OK " + sha[:12]


def _num_header(df):
    if not str(df.iloc[0, 0]).strip().lstrip("-").replace(".", "").isdigit():
        df.columns = [str(x).strip() for x in df.iloc[0]]
        df = df.iloc[1:].reset_index(drop=True)
    return df


def ts(x):
    x = pd.to_numeric(x).astype("int64")
    return pd.to_datetime(x, unit="us" if x.iloc[0] > 1e14 else "ms")


def job(kind, sym, period):
    p = PERP[sym]
    if kind == "funding":
        url = f"{B}/monthly/fundingRate/{p}/{p}-fundingRate-{period}.zip"
    elif kind == "premium":
        url = f"{B}/monthly/premiumIndexKlines/{p}/1d/{p}-1d-{period}.zip"
    else:
        url = f"{B}/daily/metrics/{p}/{p}-metrics-{period}.zip"
    cache = OUT / "_cache" / f"{kind}_{sym}_{period}.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    df, st = fetch(url)
    if kind in ("funding", "premium") and df is not None:      # normalise per file (some files have a header row)
        if not str(df.iloc[0, 0]).strip().isdigit():
            df = df.iloc[1:].reset_index(drop=True)
        if kind == "funding":
            df = pd.DataFrame(dict(time=ts(df.iloc[:, 0]), funding_rate=pd.to_numeric(df.iloc[:, -1])))
        else:
            df = pd.DataFrame(dict(timestamp=ts(df.iloc[:, 0]), prem_open=pd.to_numeric(df.iloc[:, 1]),
                                   prem_high=pd.to_numeric(df.iloc[:, 2]), prem_low=pd.to_numeric(df.iloc[:, 3]),
                                   prem_close=pd.to_numeric(df.iloc[:, 4])))
    if kind == "metrics" and df is not None:              # aggregate in the worker (74k daily files -> 1 row each)
        df = _num_header(df)
        df.columns = [c.strip() for c in df.columns]
        for c in df.columns[2:]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        last = df.iloc[-1]
        df = dict(date=period, oi=last["sum_open_interest"], oi_value=last["sum_open_interest_value"],
                  top_ls_acc=df["count_toptrader_long_short_ratio"].mean(),
                  top_ls_pos=df["sum_toptrader_long_short_ratio"].mean(),
                  global_ls=df["count_long_short_ratio"].mean(),
                  taker_ls_vol=df["sum_taker_long_short_vol_ratio"].mean(), n_rows=len(df))
    out = (kind, sym, period, df, st)
    cache.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(out, cache)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    syms = SYMBOLS + EXTRA
    jobs = [("funding", s, m) for s in syms for m in MONTHS] + [("premium", s, m) for s in syms for m in MONTHS] + \
           [("metrics", s, d) for s in syms for d in DAYS]
    t0 = time.time()
    with ThreadPoolExecutor(16) as ex:
        res = list(ex.map(lambda a: job(*a), jobs))
    print(f"{len(jobs)} files checked in {time.time() - t0:.0f}s", flush=True)
    log = [dict(kind=k, symbol=s, period=p, status=st) for k, s, p, _, st in res]
    pd.DataFrame(log).to_csv(LOGS_DIR / "download_futures_info_checksum_log.csv", index=False)
    for s in syms:
        f = [df for k, s2, _, df, _ in res if k == "funding" and s2 == s and df is not None]
        if f:
            d = pd.concat(f)
            assert d.notna().all().all(), f"{s}: NaN in funding"
            d.sort_values("time").drop_duplicates("time").to_csv(OUT / f"{s}_funding.csv", index=False)
        pr = [df for k, s2, _, df, _ in res if k == "premium" and s2 == s and df is not None]
        if pr:
            d = pd.concat(pr)
            assert d.notna().all().all(), f"{s}: NaN in premium index"
            d.sort_values("timestamp").drop_duplicates("timestamp").to_csv(OUT / f"{s}_premium_1d.csv", index=False)
        rows = [df for k, s2, p, df, _ in res if k == "metrics" and s2 == s and df is not None]
        if rows:
            pd.DataFrame(rows).sort_values("date").to_csv(OUT / f"{s}_metrics_daily.csv", index=False)
        print(f"[{s}] funding files {len(f)}, premium files {len(pr)}, metrics days {len(rows)}", flush=True)


if __name__ == "__main__":
    main()
