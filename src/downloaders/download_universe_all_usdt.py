"""
Step 13 data: 1D and 1h klines (all 12 Binance columns) for EVERY USDT spot pair on Binance Vision, 2020-01..2026-09,
including pairs that were later delisted (survivorship-free). Leveraged tokens (*UP/*DOWN/*BULL/*BEAR) are skipped;
stable/fiat/wrapped pairs are downloaded but excluded later by the study (documented there).

Evidence rules (same as the earlier downloaders):
- the exact file list comes from the public S3 listing (no guessing), every zip is SHA256-checked against Binance's
  .CHECKSUM file; a mismatch crashes the run;
- timestamps auto-detected (ms / us); every row must lie inside its month;
- the kept history is the FIRST continuous run of months and, inside it, of candles (1d: daily, 1h: hourly gaps are
  allowed and logged because Binance has maintenance hours, but 1d is cut at the first missing day -- a later relisting
  under the same ticker is never glued to the old coin);
- per-symbol outputs are written atomically and re-used on restart (resume), every decision is logged.
Outputs: data/universe_all/1d/<SYM>_1d.csv, data/universe_all/1h/<SYM>_1h_full.csv.gz (same name/columns as raw_1h_full),
         logs/universe_all_download/{files_log.csv, symbols_1d.csv, symbols_1h.csv}
"""
import re
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
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from config import DATA_DIR, LOGS_DIR

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
BASE = "https://data.binance.vision/data/spot/monthly/klines"
FIRST, LAST = "2020-01", "2026-09"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"]
KEEP = ["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote"]
LEVERAGED = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")
OUT = DATA_DIR / "universe_all"
LOG = LOGS_DIR / "universe_all_download"
THREADS = 24
SESSION = requests.Session()
SESSION.mount("https://", requests.adapters.HTTPAdapter(pool_connections=THREADS, pool_maxsize=THREADS))


def get(url, params=None):
    err = None
    for k in range(12):
        try:
            r = SESSION.get(url, params=params, timeout=60)
            if r.status_code in (200, 404):
                return r
            err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            err = str(e)
        time.sleep(min(60, 2 * (k + 1)))
    raise RuntimeError(f"{url}: {err}")


def list_symbols():
    out, marker = [], ""
    while True:
        r = get(S3, {"delimiter": "/", "prefix": "data/spot/monthly/klines/", "marker": marker})
        t = r.text
        out += [p.split("/")[-2] for p in re.findall(r"<Prefix>([^<]+)</Prefix>", t) if p != "data/spot/monthly/klines/"]
        if "<IsTruncated>true</IsTruncated>" not in t:
            break
        marker = re.findall(r"<NextMarker>([^<]+)</NextMarker>", t)[0]
    return sorted(s for s in set(out) if s.endswith("USDT") and not s.endswith(LEVERAGED))


def list_months(sym, tf):
    r = get(S3, {"prefix": f"data/spot/monthly/klines/{sym}/{tf}/"})
    assert "<IsTruncated>true</IsTruncated>" not in r.text, f"{sym} {tf}: listing truncated"
    ms = re.findall(rf"{sym}-{tf}-(\d{{4}}-\d{{2}})\.zip</Key>", r.text)
    return sorted(m for m in set(ms) if FIRST <= m <= LAST)


def fetch(sym, tf, month):
    url = f"{BASE}/{sym}/{tf}/{sym}-{tf}-{month}.zip"
    r = get(url)
    c = get(url + ".CHECKSUM")
    assert r.status_code == 200 and c.status_code == 200, f"{sym} {tf} {month}: listed but HTTP {r.status_code}/{c.status_code}"
    sha = hashlib.sha256(r.content).hexdigest()
    assert sha == c.text.split()[0].strip().lower(), f"{sym} {tf} {month}: SHA256 mismatch"
    with zipfile.ZipFile(BytesIO(r.content)) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), header=None)
    if not str(df.iloc[0, 0]).strip().isdigit():
        df = df.iloc[1:].reset_index(drop=True)
    df.columns = COLS
    ts = df["open_time"].astype("int64")
    # unit decided PER ROW: Binance files can mix ms and us rows (e.g. KLAYUSDT-1d-2024-10 after delisting)
    df["timestamp"] = pd.to_datetime(ts.where(ts > 1e14, ts * 1000), unit="us")
    for col in KEEP[1:]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    m0 = pd.Timestamp(month + "-01")
    assert ((df.timestamp >= m0) & (df.timestamp < m0 + pd.offsets.MonthBegin(1))).all(), f"{sym} {tf} {month}: rows outside month"
    return df[KEEP], sha


def consecutive_months(ms):
    """First continuous run of months (a gap = delisted; anything after is a relisting and is ignored)."""
    keep = ms[:1]
    for m in ms[1:]:
        if (pd.Period(m, "M") - pd.Period(keep[-1], "M")).n != 1:
            break
        keep.append(m)
    return keep


assert consecutive_months(["2020-01", "2020-02", "2020-03", "2020-05"]) == ["2020-01", "2020-02", "2020-03"]
assert consecutive_months(["2020-12", "2021-01"]) == ["2020-12", "2021-01"]


def do_symbol(sym, tf, pool):
    out_dir = OUT / tf
    target = out_dir / (f"{sym}_1d.csv" if tf == "1d" else f"{sym}_1h_full.csv.gz")
    if target.exists():
        return None, []                                                    # resume: already done and verified
    ms = list_months(sym, tf)
    if not ms:
        return dict(symbol=sym, tf=tf, status="no files in range"), []
    keep = consecutive_months(ms)
    res = list(pool.map(lambda m: fetch(sym, tf, m), keep))
    flog = [dict(symbol=sym, tf=tf, month=m, sha256=sha, rows=len(df)) for m, (df, sha) in zip(keep, res)]
    d = pd.concat([df for df, _ in res]).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    step = pd.Timedelta(days=1) if tf == "1d" else pd.Timedelta(hours=1)
    gaps = d.timestamp.diff().dropna() != step
    note = ""
    if tf == "1d" and gaps.any():
        g = gaps[gaps].index[0]
        note = f"cut at first missing day before {d.at[g, 'timestamp'].date()}"
        d = d.iloc[:g]
    elif gaps.any():
        note = f"{int(gaps.sum())} hourly gaps (kept, logged)"
    bad = ((d.high < d[["open", "close"]].max(axis=1)) | (d.low > d[["open", "close"]].min(axis=1))).sum()
    tmp = target.with_suffix(target.suffix + ".tmp")
    if tf == "1d":
        d.assign(timestamp=d.timestamp.dt.strftime("%Y-%m-%d")).to_csv(tmp, index=False)
    else:
        d.to_csv(tmp, index=False, compression="gzip")
    tmp.replace(target)
    info = dict(symbol=sym, tf=tf, status="OK", months_listed=len(ms), months_kept=len(keep),
                months_ignored_after_gap=len(ms) - len(keep), first=str(d.timestamp.iloc[0]), last=str(d.timestamp.iloc[-1]),
                rows=len(d), ohlc_inconsistent_rows=int(bad), note=note)
    return info, flog


def main():
    tfs = sys.argv[1:] or ["1d", "1h"]
    for tf in tfs:
        (OUT / tf).mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)
    syms = list_symbols()
    print(f"USDT spot symbols (leveraged tokens excluded): {len(syms)}", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(THREADS) as pool:
        for tf in tfs:
            infos = []
            flog_path = LOG / f"files_log_{tf}.csv"
            for k, s in enumerate(syms):
                info, flog = do_symbol(s, tf, pool)
                if flog:
                    pd.DataFrame(flog).to_csv(flog_path, mode="a", index=False, header=not flog_path.exists())
                if info:
                    infos.append(info)
                    sp = LOG / f"symbols_{tf}.csv"
                    pd.DataFrame([info]).to_csv(sp, mode="a", index=False, header=not sp.exists())
                if k % 25 == 0:
                    print(f"[{tf}] {k + 1}/{len(syms)} {s} ({time.time() - t0:.0f}s)", flush=True)
            print(f"[{tf}] done: {len(syms)} symbols ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
