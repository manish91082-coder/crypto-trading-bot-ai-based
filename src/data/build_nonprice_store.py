"""Build clean Parquet tables from the checksum-verified Binance public zips (data/external/binance_public/<dataset>/*.zip)
and write a quality report (rows, range, duplicates, gaps, cross-checks against the older local copies).
Output: data/external/binance_public/clean/{funding,premium5m,fut5m,metrics5m}.parquet + QC_REPORT.md
Usage: python src/data/build_nonprice_store.py"""
import glob
import hashlib
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
R = P / "data/external/binance_public"
OUT = R / "clean"
KL = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def read_zip(f, names=None):
    z = zipfile.ZipFile(f)
    raw = z.read(z.namelist()[0]).decode()
    first = raw.split("\n", 1)[0]
    has_header = not first[:1].isdigit()
    df = pd.read_csv(io.StringIO(raw), header=0 if has_header else None)
    if names is not None and not has_header:
        df.columns = names
    return df


def to_time(v):
    v = pd.to_numeric(v)
    unit = "us" if v.max() > 10 ** 14 else "ms"            # Binance moved some files to microseconds in 2025
    return pd.to_datetime(v, unit=unit)


def gaps(t, freq):
    full = pd.date_range(t.min(), t.max(), freq=freq)
    miss = full.difference(t)
    return len(miss), miss


def main():
    OUT.mkdir(exist_ok=True)
    rep = ["# Non-price store QC report", ""]
    # funding
    fd = pd.concat([read_zip(f) for f in sorted(glob.glob(str(R / "fundingRate/*.zip")))])
    fd["time"] = to_time(fd.calc_time)
    fd = fd.sort_values("time").drop_duplicates("time")[["time", "funding_interval_hours", "last_funding_rate"]].rename(columns={"last_funding_rate": "funding_rate"})
    fd.to_parquet(OUT / "funding.parquet", index=False)
    old = pd.read_csv(P / "data/futures_um/BTCUSDT_funding.csv", parse_dates=["time"])
    m = fd.assign(k=fd.time.dt.floor("min")).merge(old.assign(k=old.time.dt.floor("min")), on="k", suffixes=("", "_old"))
    rep += ["## funding (8h)", f"- rows {len(fd)}, {fd.time.min()} … {fd.time.max()}; interval hours {fd.funding_interval_hours.value_counts().to_dict()}",
            f"- cross-check vs data/futures_um/BTCUSDT_funding.csv: matched {len(m)} of {len(old)} old rows, max |diff| {float((m.funding_rate - m.funding_rate_old).abs().max()):.3e}", ""]
    # 5m klines-type
    for ds, name in (("premiumIndex5m", "premium5m"), ("klines5m", "fut5m")):
        df = pd.concat([read_zip(f, KL) for f in sorted(glob.glob(str(R / ds / "*.zip")))])
        df["time"] = to_time(df.open_time)
        n0 = len(df)
        df = df.sort_values("time").drop_duplicates("time")
        cols = ["time", "open", "high", "low", "close"] + (["volume", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume"] if name == "fut5m" else [])
        df = df[cols]
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        ng, miss = gaps(df.time, "5min")
        rep += [f"## {name} (5m)", f"- rows {len(df)} (duplicates dropped {n0 - len(df)}), {df.time.min()} … {df.time.max()}; missing 5m bars {ng}",
                f"- missing by year: {pd.Series(miss.year).value_counts().sort_index().to_dict() if ng else {}}"]
        if name == "fut5m":
            old = pd.read_csv(P / "data/futures_um/BTCUSDT_perp_1h.csv.gz", parse_dates=["timestamp"]).set_index("timestamp")
            h = df.set_index("time").resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
            j = h.index.intersection(old.index)
            d = (h.loc[j, ["open", "high", "low", "close"]] - old.loc[j, ["open", "high", "low", "close"]]).abs().max().max()
            rep += [f"- cross-check: 1h aggregate vs data/futures_um/BTCUSDT_perp_1h.csv.gz on {len(j)} common hours: max |OHLC diff| {d}"]
        rep += [""]
    # metrics
    fs = sorted(glob.glob(str(R / "metrics/*.zip")))
    mt = pd.concat([read_zip(f) for f in fs])
    mt["time"] = pd.to_datetime(mt.create_time)
    n0 = len(mt)
    mt = mt.sort_values("time").drop_duplicates("time")
    keep = ["sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
            "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
    for k in keep:
        mt[k] = pd.to_numeric(mt[k], errors="coerce")
    mt = mt[["time"] + keep]
    mt.to_parquet(OUT / "metrics5m.parquet", index=False)
    ng, miss = gaps(mt.time, "5min")
    nan = mt[keep].isna().sum().to_dict()
    per_day = mt.time.dt.floor("D").value_counts()
    rep += ["## metrics5m", f"- files {len(fs)}, rows {len(mt)} (duplicates dropped {n0 - len(mt)}), {mt.time.min()} … {mt.time.max()}; missing 5m stamps {ng}",
            f"- missing by year: {pd.Series(miss.year).value_counts().sort_index().to_dict() if ng else {}}",
            f"- NaN per column: {nan}", f"- days with < 288 rows: {int((per_day < 288).sum())} of {len(per_day)}", ""]
    rep += ["## output SHA256"] + [f"- {f.name}: {hashlib.sha256(f.read_bytes()).hexdigest()}" for f in sorted(OUT.glob('*.parquet'))]
    (OUT / "QC_REPORT.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))


def depth():
    """bookDepth snapshots (~30 s, cumulative depth within +-1..5 % of mid) -> mean per 5m bar [t, t+5m) of bid / ask notional
    within 1 % and 5 %, and the imbalances (bid - ask) / (bid + ask). Appends to QC_REPORT.md."""
    rows = []
    fs = sorted(glob.glob(str(R / "bookDepth/*.zip")))
    for f in fs:
        d = read_zip(f)
        d["timestamp"] = pd.to_datetime(d.timestamp)
        d["percentage"] = pd.to_numeric(d.percentage)
        w = d.pivot_table(index="timestamp", columns="percentage", values="notional", aggfunc="last")
        x = pd.DataFrame({"bid1": w.get(-1.0), "ask1": w.get(1.0), "bid5": w.get(-5.0), "ask5": w.get(5.0)})
        x = x.resample("5min").mean()
        x["n_snap"] = w[-1.0].resample("5min").count() if -1.0 in w else 0
        rows.append(x)
    dp = pd.concat(rows).sort_index()
    dp = dp[~dp.index.duplicated()]
    dp["imb1"] = (dp.bid1 - dp.ask1) / (dp.bid1 + dp.ask1)
    dp["imb5"] = (dp.bid5 - dp.ask5) / (dp.bid5 + dp.ask5)
    dp = dp.reset_index().rename(columns={"timestamp": "time"})
    dp.to_parquet(OUT / "depth5m.parquet", index=False)
    ok = dp.dropna(subset=["imb1"])
    ng, miss = gaps(ok.time, "5min")
    rep = ["", "## depth5m (from bookDepth)", f"- files {len(fs)}, 5m rows with data {len(ok)}, {ok.time.min()} … {ok.time.max()}; missing 5m bars {ng}",
           f"- missing by year: {pd.Series(miss.year).value_counts().sort_index().to_dict() if ng else {}}",
           f"- snapshots per 5m bar: median {ok.n_snap.median()}, min {ok.n_snap.min()}",
           f"- depth5m.parquet SHA256 {hashlib.sha256((OUT / 'depth5m.parquet').read_bytes()).hexdigest()}"]
    with open(OUT / "QC_REPORT.md", "a", encoding="utf-8") as fh:
        fh.write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    import sys
    depth() if sys.argv[1:] == ["depth"] else main()
