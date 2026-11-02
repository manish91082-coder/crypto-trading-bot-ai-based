"""
Step 6.4 data: 1D klines 2020-01..2026-09 for large 2020-2022 coins that are NOT in the 10-coin universe, including
coins that later collapsed or were delisted (survivorship check). Binance Vision public monthly files, SHA256-verified.
Written to data/raw_extended/ -- the main data/raw files are not touched.

Rules: a month that 404s before the first available month = not listed yet; after it = delisted/renamed (data ends).
A file whose rows are not daily-continuous is cut at the first gap (e.g. old LUNA delisted 2022-05 -> new LUNA listed
later under the same symbol: only the original, continuous history is kept). Everything is logged.
"""
import sys
from pathlib import Path
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "downloaders"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import DATA_DIR, LOGS_DIR
from extend_1d_history_2020 import fetch_month

EXTRA = ["LUNAUSDT", "FTTUSDT", "AVAXUSDT", "MATICUSDT", "UNIUSDT", "ATOMUSDT", "FILUSDT", "ETCUSDT", "XLMUSDT",
         "TRXUSDT", "BCHUSDT", "EOSUSDT", "ICPUSDT", "AXSUSDT", "SANDUSDT", "ALGOUSDT", "VETUSDT", "THETAUSDT",
         "NEARUSDT", "SHIBUSDT"]
MONTHS = [f"{y}-{m:02d}" for y in range(2020, 2027) for m in range(1, 13) if not (y == 2026 and m > 9)]
OUT_DIR = DATA_DIR / "raw_extended"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log = []
    for s in EXTRA:
        parts, started, ended = [], None, None
        for m in MONTHS:
            res = fetch_month(s, m)
            if res is None:
                log.append(dict(symbol=s, month=m, status="404"))
                if started is not None and ended is None:
                    ended = m
                continue
            df, sha = res
            if ended is not None:
                log.append(dict(symbol=s, month=m, status=f"OK but after data ended {ended} (relisting) -> ignored", sha256=sha[:12]))
                continue
            started = started or m
            parts.append(df)
            log.append(dict(symbol=s, month=m, status="OK sha256 verified", rows=len(df), sha256=sha[:12]))
        if not parts:
            print(f"[--] {s}: no data")
            continue
        d = pd.concat(parts, ignore_index=True).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
        gaps = d["timestamp"].diff().dropna() != pd.Timedelta(days=1)
        cut_note = ""
        if gaps.any():
            first_gap = gaps[gaps].index[0]
            cut_note = f" cut at first gap before {d.at[first_gap, 'timestamp'].date()}"
            d = d.iloc[:first_gap]
        assert (d["high"] >= d[["open", "close"]].max(axis=1)).all() and (d["low"] <= d[["open", "close"]].min(axis=1)).all()
        out = d.copy()
        out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%d")
        out.to_csv(OUT_DIR / f"{s}_1d_extended.csv", index=False)
        print(f"[OK] {s}: {d['timestamp'].min().date()} -> {d['timestamp'].max().date()} ({len(d)} days){cut_note}", flush=True)
    pd.DataFrame(log).to_csv(LOGS_DIR / "download_1d_extended_universe_checksum_log.csv", index=False)


if __name__ == "__main__":
    main()
