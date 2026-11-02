"""BTC-ALLTF study (2026-10-28): build every timeframe's BTCUSDT bars from official Binance 1m klines, for spot and USD-M futures.
Sources (all checksum-verified Binance public files, see MANIFEST.csv next to each):
  spot 1m    2017-08 .. 2025-12  data/external/binance_1m/spot/              (downloaded 2026-10-28, user permission)
  spot 1m    2026-01 .. 2026-09  built here from data/external/binance_1s/spot_1s/ (1s -> 1m)
  futures 1m 2020-01 .. 2025-12  data/external/binance_1m/futures/           (downloaded 2026-10-28, user permission)
  futures 1m 2026-01 .. 2026-09  data/external/binance_1s/futures_1m/
Bars: open/high/low/close/volume/quote_volume/trades/taker_buy_base + n_1m (number of 1m bars inside). No bar is invented:
a minute Binance does not have stays missing, and a higher bar is built from the minutes that exist.
TFs: 1m 5m 15m 30m 1h 4h 8h (UTC-aligned like Binance), 1d, 1w (Monday 00:00 UTC), 1mo, 1y (calendar).
Output: data/derived/btc_alltf/bars/<market>_<tf>.parquet + BARS_MANIFEST.csv (rows, first, last, sha256).
Usage: python src/btc_alltf/build_bars.py"""
import csv
import hashlib
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
OUT = P / "data/derived/btc_alltf/bars"
END_MS = int(pd.Timestamp("2026-10-01", tz="UTC").timestamp() * 1000)       # study data ends 2026-09-30 23:59 UTC
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"]
KEEP = ["open", "high", "low", "close", "volume", "quote_volume", "trades", "taker_buy_base"]
MIN = 60_000
TF_MS = {"5m": 5 * MIN, "15m": 15 * MIN, "30m": 30 * MIN, "1h": 60 * MIN, "4h": 240 * MIN, "8h": 480 * MIN, "1d": 1440 * MIN}
TFS = ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w", "1mo", "1y"]


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])
    first = raw[:200].decode(errors="replace")
    skip = 1 if first.startswith("open_time") else 0                      # 2026 futures files carry a header line
    d = pd.read_csv(io.BytesIO(raw), header=None, names=COLS, skiprows=skip, dtype={"open_time": "int64"})
    t = d.open_time.values
    if t.max() > 10 ** 14:                                                  # spot files from 2025-01 use microseconds
        t = t // 1000
    d["ts"] = t
    return d[["ts"] + KEEP]


def agg_key(d, key):
    g = d.groupby(key, sort=True)
    o = pd.DataFrame({"ts": g.ts.first(), "open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                      "volume": g.volume.sum(), "quote_volume": g.quote_volume.sum(), "trades": g.trades.sum(),
                      "taker_buy_base": g.taker_buy_base.sum(), "n_1m": g.n_1m.sum()})
    return o.reset_index(drop=True)


def spot_2026_from_1s():
    parts = []
    for f in sorted((P / "data/external/binance_1s/spot_1s").glob("BTCUSDT-1s-2026-*.zip")):
        d = read_zip(f)
        d["n_1m"] = 1
        d["k"] = d.ts // MIN
        m = agg_key(d, "k")
        m["ts"] = (m.ts // MIN) * MIN                                       # minute open time
        m["n_1m"] = 1
        parts.append(m)
        print(f"  1s -> 1m {f.name}: {len(d):,} s-bars -> {len(m):,} minutes", flush=True)
    return pd.concat(parts, ignore_index=True)


def load_1m(market):
    if market == "spot":
        files = sorted((P / "data/external/binance_1m/spot").glob("BTCUSDT-1m-*.zip"))
    else:
        files = sorted((P / "data/external/binance_1m/futures").glob("BTCUSDT-1m-*.zip")) + \
                sorted((P / "data/external/binance_1s/futures_1m").glob("BTCUSDT-1m-2026-*.zip"))
    parts = [read_zip(f) for f in files]
    d = pd.concat(parts, ignore_index=True)
    d["n_1m"] = 1
    if market == "spot":
        d = pd.concat([d, spot_2026_from_1s()], ignore_index=True)
    d = d[d.ts < END_MS]
    # Binance spot 1m files have two runs whose open_time is shifted by seconds (2017-12-04..18 +20.799 s, 2018-02-09..10
    # +14.789 s; real trading bars). They are floored to their minute; if that minute also exists as a regular bar, the
    # regular bar is kept and the shifted one dropped (counted in the manifest).
    irr = (d.ts % MIN) != 0
    bad = int(irr.sum())
    d = d.assign(ts=(d.ts // MIN) * MIN, irr=irr.astype(int)).sort_values(["ts", "irr"], kind="mergesort")
    dup = int(d.ts.duplicated().sum())
    d = d.drop_duplicates("ts", keep="first").drop(columns="irr").reset_index(drop=True)
    print(f"{market} 1m: {len(d):,} rows from {len(files)} files, shifted ts floored {bad}, duplicate minutes dropped {dup}", flush=True)
    return d, dup, bad


def resample(d1, tf):
    if tf in TF_MS:
        key = d1.ts // TF_MS[tf]
        o = agg_key(d1.assign(k=key), "k")
        o["ts"] = (o.ts // TF_MS[tf]) * TF_MS[tf]
        return o
    dt = pd.to_datetime(d1.ts, unit="ms", utc=True)
    if tf == "1w":
        day = d1.ts // (1440 * MIN)                                         # days since 1970-01-01 (a Thursday)
        wk = (day - 4) // 7                                                 # Monday-start week number
        o = agg_key(d1.assign(k=wk), "k")
        o["ts"] = ((o.ts // (1440 * MIN) - 4) // 7 * 7 + 4) * 1440 * MIN
        return o
    if tf == "1mo":
        k = dt.dt.year * 12 + dt.dt.month - 1
    else:
        k = dt.dt.year
    o = agg_key(d1.assign(k=k.values), "k")
    first = pd.to_datetime(o.ts, unit="ms", utc=True)
    start = pd.to_datetime(dict(year=first.dt.year, month=first.dt.month if tf == "1mo" else 1, day=1), utc=True)
    o["ts"] = start.values.astype("datetime64[ms]").astype("int64")
    return o


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for market in ("spot", "futures"):
        d1, dup, bad = load_1m(market)
        for tf in TFS:
            b = d1 if tf == "1m" else resample(d1, tf)
            b = b[["ts"] + KEEP + ["n_1m"]].astype({"ts": "int64", "trades": "int64", "n_1m": "int64"})
            f = OUT / f"{market}_{tf}.parquet"
            b.to_parquet(f, index=False, compression="zstd")
            t0 = pd.to_datetime(b.ts.iloc[0], unit="ms", utc=True)
            t1 = pd.to_datetime(b.ts.iloc[-1], unit="ms", utc=True)
            rows.append([market, tf, len(b), str(t0), str(t1), int(b.n_1m.sum()), dup, bad, f.relative_to(P).as_posix(), sha(f)])
            print(f"  {market} {tf}: {len(b):,} bars {t0} .. {t1}", flush=True)
        del d1
    with open(OUT / "BARS_MANIFEST.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["market", "tf", "rows", "first_open", "last_open", "minutes_inside", "dup_1m_dropped", "shifted_ts_floored", "file",
                    "sha256", "built_utc"])
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for r in rows:
            w.writerow(r + [now])


if __name__ == "__main__":
    main()
