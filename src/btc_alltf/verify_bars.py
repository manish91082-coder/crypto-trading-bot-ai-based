"""BTC-ALLTF study (2026-10-28): check the bars built by build_bars.py against every independent BTC file we already have.
References (none of them was built from the new 1m download):
  spot   5m/15m  data/universe_pre2020_hf + data/universe_hf          (SHA-verified project files)
  spot   1h/1d   data/universe_pre2020   + data/universe_all
  spot   30m/4h/8h/1w/1mo  archive/cleanup_2026_10_15/data/raw/*_Raw_5Years.csv (CLAUDE.md exception; rows with a corrupt
                 2025+ timestamp, year > 2030, are skipped and counted)
  futures 5m     data/external/binance_public/klines5m/*.zip (Binance futures 5m klines, checksum-verified 2026-10-26)
  futures 1h     data/futures_um/BTCUSDT_perp_1h.csv.gz
  spot   1m 2025-01..2026-09  the same archive raw 1m file, its corrupt timestamps repaired: the file wrote microsecond open
                 times as if they were milliseconds, so the real open time in ms = the seconds count of the written datetime
For each pair: rows matched on open time, rows only in ours / only in the reference, and bars whose open, high, low or close
differ by more than 1e-8, and volume relative difference > 1e-6. Output: logs/btc_alltf_2026_10_28/bars_check.csv"""
import glob
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parents[2]
B = P / "data/derived/btc_alltf/bars"
RAW = P / "archive/cleanup_2026_10_15/data/raw"


def ours(m, tf):
    d = pd.read_parquet(B / f"{m}_{tf}.parquet")
    return d.set_index("ts")


def ref_csv(files, tcol="timestamp"):
    parts = []
    for f in files:
        d = pd.read_csv(f)
        t = pd.to_datetime(d[tcol].astype(str).str.slice(0, 19), errors="coerce", format="mixed")
        bad = int(((t.dt.year > 2030) | t.isna()).sum())
        d = d[(t.dt.year <= 2030) & t.notna()].copy()
        d["ts"] = t[(t.dt.year <= 2030) & t.notna()].values.astype("datetime64[ms]").astype("int64")
        d.attrs["bad"] = bad
        parts.append((d, bad))
    bad = sum(b for _, b in parts)
    d = pd.concat([p for p, _ in parts]).drop_duplicates("ts").set_index("ts").sort_index()
    return d, bad


def ref_fut5m():
    parts = []
    for f in sorted(glob.glob(str(P / "data/external/binance_public/klines5m/*.zip"))):
        with zipfile.ZipFile(f) as z:
            raw = z.read(z.namelist()[0])
        skip = 1 if raw[:9] == b"open_time" else 0
        d = pd.read_csv(io.BytesIO(raw), header=None, skiprows=skip,
                        names=["ts", "open", "high", "low", "close", "volume", "ct", "quote_volume", "trades", "tbb", "tbq", "ig"])
        parts.append(d)
    d = pd.concat(parts).drop_duplicates("ts").set_index("ts").sort_index()
    return d, 0


def ref_raw1m_fixed():
    r = pd.read_csv(RAW / "BTCUSDT_1m_Raw_5Years.csv.gz")
    big = r.timestamp.str.len() > 19
    sec = np.array(r.timestamp[big].str.replace(" ", "T").values, dtype="datetime64[s]").astype("int64")
    return r[big].assign(ts=sec).set_index("ts").sort_index(), 0


def compare(name, a, r, bad, lo=None, hi=None, show=False):
    if lo is not None:
        r = r[(r.index >= lo) & (r.index <= hi)]
        a = a[(a.index >= lo) & (a.index <= hi)]
    j = a.index.intersection(r.index)
    out = dict(check=name, ours=len(a), ref=len(r), matched=len(j), only_ours=len(a.index.difference(r.index)),
               only_ref=len(r.index.difference(a.index)), ref_rows_bad_ts=bad)
    for c in ("open", "high", "low", "close"):
        dd = np.abs(a.loc[j, c].values - r.loc[j, c].astype(float).values)
        out[f"{c}_mismatch"] = int((dd > 1e-8).sum())
        out[f"{c}_maxdiff"] = float(dd.max()) if len(dd) else 0.0
        m = dd > 1e-8
        yrs = pd.Series(pd.to_datetime(pd.Index(j[m]), unit="ms").year).value_counts().sort_index()
        out[f"{c}_mismatch_by_year"] = " ".join(f"{y}:{n}" for y, n in yrs.items())
        out[f"{c}_mismatch_1tick_share"] = round(float((np.round(dd[m], 2) == 0.01).mean()), 4) if m.any() else None
        if show and m.any():
            print(f"   {c} mismatches at", [str(pd.to_datetime(x, unit='ms')) for x in j[m][:10]])
    va, vr = a.loc[j, "volume"].values, r.loc[j, "volume"].astype(float).values
    rel = np.abs(va - vr) / np.maximum(np.abs(vr), 1e-12)
    out["volume_rel_gt_1e-6"] = int(((rel > 1e-6) & (np.abs(va - vr) > 1e-9)).sum())
    out["volume_maxrel"] = float(np.where(np.abs(va - vr) > 1e-9, rel, 0).max()) if len(rel) else 0.0
    print(" ".join(f"{k}={v}" for k, v in out.items()), flush=True)
    return out


def main():
    rows = []
    for tf, sub in (("5m", "hf"), ("15m", "hf")):
        r, bad = ref_csv([P / f"data/universe_pre2020_{sub}/{tf}/BTCUSDT_{tf}_full.csv.gz", P / f"data/universe_{sub}/{tf}/BTCUSDT_{tf}_full.csv.gz"])
        rows.append(compare(f"spot {tf} vs universe_pre2020_{sub}+universe_{sub}", ours("spot", tf), r, bad))
    r, bad = ref_csv([P / "data/universe_pre2020/1h/BTCUSDT_1h_full.csv.gz", P / "data/universe_all/1h/BTCUSDT_1h_full.csv.gz"])
    rows.append(compare("spot 1h vs universe_pre2020+universe_all", ours("spot", "1h"), r, bad))
    r, bad = ref_csv([P / "data/universe_pre2020/1d/BTCUSDT_1d.csv", P / "data/universe_all/1d/BTCUSDT_1d.csv"])
    rows.append(compare("spot 1d vs universe_pre2020+universe_all", ours("spot", "1d"), r, bad))
    for tf in ("30m", "4h", "8h", "1w", "1mo", "1h", "15m", "5m", "1m"):
        f = RAW / f"BTCUSDT_{tf}_Raw_5Years.csv"
        if tf == "1m":
            f = RAW / "BTCUSDT_1m_Raw_5Years.csv.gz"
        r, bad = ref_csv([f])
        rows.append(compare(f"spot {tf} vs archive raw {f.name}", ours("spot", tf), r, bad, r.index.min(), r.index.max()))
    r, bad = ref_fut5m()
    rows.append(compare("futures 5m vs binance_public klines5m", ours("futures", "5m"), r, bad, show=True))
    r, bad = ref_csv([P / "data/futures_um/BTCUSDT_perp_1h.csv.gz"])
    rows.append(compare("futures 1h vs futures_um perp_1h", ours("futures", "1h"), r, bad, show=True))
    r, bad = ref_raw1m_fixed()
    rows.append(compare("spot 1m 2025-01..2026-09 vs archive raw 1m (timestamps repaired)", ours("spot", "1m"), r, bad, r.index.min(), r.index.max()))
    out = P / "logs/btc_alltf_2026_10_28/bars_check.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"written {out}")


if __name__ == "__main__":
    main()
