"""BTC-ALLTF-R2 (2026-10-29): the other-coin universe for the cross-coin confirmation, decided by name and data only (no P&L).
  spot:    data/universe_all 1d + 1h (and data/universe_hf 15m + 5m for 5m/15m/30m), USDT pairs, not BTCUSDT, not stable / fiat /
           wrapped / gold / tokenized stock (list copied from step13), not leveraged tokens, >= min_days daily candles inside the
           grid, not pegged (median |daily close return| >= 0.3 %)
  futures: data/futures_um perp 1h + funding, same name / data rules
  spot 1m: the 9 archive raw 1m coins; every hour of the repaired 1m file is aggregated and compared with universe_all 1h;
           only months where every hour matches (OHLC within 1e-8 relative, volume within 1e-6 relative) are used
Writes logs/btc_alltf_r2_2026_10_29/universe_manifest.csv (+ universe_1m_months.csv) with the sha256 of every source file.
Usage: python src/btc_alltf_r2/universe.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K                                                           # noqa: E402

X = K.CFG["xcoin"]
LO, HI = K.ms(X["grid_start"]), K.ms(X["grid_end"])


def name_ok(c):
    return c.endswith("USDT") and not c.endswith(K.LEV) and c not in K.NOT_CRYPTO and c not in X["exclude"]


def day_stats(kind, coin):
    close, qv = K.daily(coin, kind, LO, HI)
    ok = np.isfinite(close)
    r = close[1:] / close[:-1] - 1
    r = r[np.isfinite(r)]
    return int(ok.sum()), float(np.median(np.abs(r))) if len(r) else np.nan


def main():
    rows = []
    spot = sorted(p.name[:-7] for p in (K.PROJ / "data/universe_all/1d").glob("*_1d.csv"))
    hf = set(p.name.split("_")[0] for p in (K.PROJ / "data/universe_hf/15m").glob("*_15m_full.csv.gz"))
    hf5 = set(p.name.split("_")[0] for p in (K.PROJ / "data/universe_hf/5m").glob("*_5m_full.csv.gz"))
    for c in spot:
        f1d, f1h = K.src_file(c, "spot", "1d"), K.src_file(c, "spot", "1h")
        why = ""
        if not name_ok(c):
            why = "name rule (not a crypto USDT pair / leveraged / BTCUSDT)"
        elif not f1h.exists():
            why = "no 1h file"
        if why:
            rows.append(dict(market="spot", coin=c, use_1d_1h=False, use_hf=False, why=why))
            continue
        nd, med = day_stats("spot", c)
        if nd < X["min_days"]:
            why = f"only {nd} days in the grid"
        elif not med >= X["peg_median_abs_daily_ret"]:
            why = f"pegged (median |daily ret| {med:.4f})"
        use = why == ""
        r = dict(market="spot", coin=c, use_1d_1h=use, use_hf=use and c in hf and c in hf5, why=why, days=nd, med_abs_ret=med,
                 sha_1d=K.sha(f1d), sha_1h=K.sha(f1h))
        if r["use_hf"]:
            r["sha_15m"] = K.sha(K.src_file(c, "spot", "15m"))
            r["sha_5m"] = K.sha(K.src_file(c, "spot", "5m"))
        rows.append(r)
        print(c, use, why, flush=True)
    fut = sorted(p.name.split("_perp")[0] for p in (K.PROJ / "data/futures_um").glob("*_perp_1h.csv.gz"))
    for c in fut:
        why = "" if name_ok(c) else "name rule (not a crypto USDT pair / leveraged / BTCUSDT)"
        ff = K.PROJ / f"data/futures_um/{c}_funding.csv"
        if not why and not ff.exists():
            why = "no funding file"
        if why:
            rows.append(dict(market="futures", coin=c, use_1d_1h=False, why=why))
            continue
        nd, med = day_stats("futures", c)
        if nd < X["min_days"]:
            why = f"only {nd} days in the grid"
        elif not med >= X["peg_median_abs_daily_ret"]:
            why = f"pegged (median |daily ret| {med:.4f})"
        rows.append(dict(market="futures", coin=c, use_1d_1h=why == "", why=why, days=nd, med_abs_ret=med,
                         sha_1h=K.sha(K.src_file(c, "futures", "1h")), sha_funding=K.sha(ff)))
        print("fut", c, why == "", why, flush=True)
    # spot 1m: hour-by-hour check of the repaired archive file against universe_all 1h
    mrows = []
    for c in X["spot_1m_coins"]:
        f = K.src_file(c, "spot", "1m")
        m1 = K.read_raw1m(c)
        m1 = m1[(m1.ts >= LO) & (m1.ts < HI)]
        h = K.agg(m1.assign(k=m1.ts // K.TF_MS["1h"]), "k")
        h["ts"] = (h.ts // K.TF_MS["1h"]) * K.TF_MS["1h"]
        h["n1m"] = m1.groupby(m1.ts // K.TF_MS["1h"]).size().values
        ref = K._read(K.src_file(c, "spot", "1h")).set_index("ts")
        h = h.set_index("ts")
        j = h.index.intersection(ref.index)
        bad = np.zeros(len(j), bool)
        for col in ("open", "high", "low", "close"):
            a, b = h.loc[j, col].values, ref.loc[j, col].values.astype(float)
            bad |= np.abs(a - b) > 1e-8 * np.abs(b)
        va, vb = h.loc[j, "volume"].values, ref.loc[j, "volume"].values.astype(float)
        bad |= np.abs(va - vb) > 1e-6 * np.maximum(np.abs(vb), 1e-12)
        only_ours = h.index.difference(ref.index)
        mo = pd.to_datetime(pd.Index(j), unit="ms", utc=True).strftime("%Y-%m")
        mo_only = pd.to_datetime(only_ours, unit="ms", utc=True).strftime("%Y-%m")
        ref_in = ref.index[(ref.index >= h.index.min()) & (ref.index <= h.index.max())]
        missing = ref_in.difference(h.index)
        mo_miss = pd.to_datetime(missing, unit="ms", utc=True).strftime("%Y-%m")
        g = pd.DataFrame({"month": mo, "bad": bad}).groupby("month").agg(hours=("bad", "size"), bad=("bad", "sum"))
        g["only_in_1m"] = pd.Series(mo_only).value_counts().reindex(g.index).fillna(0).astype(int)
        g["missing_in_1m"] = pd.Series(mo_miss).value_counts().reindex(g.index).fillna(0).astype(int)
        g["use"] = (g.bad == 0) & (g.only_in_1m == 0)
        g = g.reset_index().assign(coin=c, sha_1m=K.sha(f))
        mrows.append(g)
        print("1m", c, f"months {len(g)}, used {int(g.use.sum())}, bad hours {int(g.bad.sum())}", flush=True)
    M = pd.DataFrame(rows)
    M.to_csv(K.R2 / "universe_manifest.csv", index=False)
    pd.concat(mrows, ignore_index=True).to_csv(K.R2 / "universe_1m_months.csv", index=False)
    s = M[M.market == "spot"]
    print(f"spot coins: {len(s)} files, used 1d/1h {int(s.use_1d_1h.sum())}, used hf {int(s.use_hf.fillna(False).sum())}; "
          f"futures: {int((M.market == 'futures').sum())} files, used {int(M[M.market == 'futures'].use_1d_1h.sum())}")


if __name__ == "__main__":
    main()
