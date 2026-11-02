"""BTC-ALLTF study (2026-10-28): read the compact trade log and rebuild every column exactly from the bars, fees.json and funding.
Usage:
  python src/btc_alltf/query.py --run <RUN dir> --market spot --tf 1h --date 2024-03-12            all trades that closed that day
  python src/btc_alltf/query.py --run <RUN dir> --market futures --tf 4h --cfg 1234 [--csv out.csv]  all trades of one config
Rebuilt: px_in (open of the entry bar), px_out (stored for stop/target/trail/liquidation/end fills, else the open of the exit
bar), bars, dir, gross, fee, funding, mae, mfe, plus the config name and the pass/fail word."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as E                                                            # noqa: E402

PROJ = Path(__file__).resolve().parents[2]
CFG = json.loads((PROJ / "logs/btc_alltf_2026_10_28/STUDY_CONFIG.json").read_text(encoding="utf-8"))


def bars(market, tf):
    return pd.read_parquet(PROJ / f"data/derived/btc_alltf/bars/{market}_{tf}.parquet", columns=["ts", "open", "high", "low", "close"])


def funding(market):
    if market != "futures":
        return None
    f = pd.read_parquet(PROJ / CFG["inputs"]["funding"])
    tau = f.time.values.astype("datetime64[ms]").astype("int64")
    m1 = pd.read_parquet(PROJ / "data/derived/btc_alltf/bars/futures_1m.parquet", columns=["ts", "open"]).set_index("ts").open
    px = m1.reindex((tau // 60_000) * 60_000).values
    return tau, np.r_[0.0, np.cumsum(f.funding_rate.values * px)]


def expand(tr, market, tf, cfgs, b=None, fund=None):
    """tr: rows of trades.parquet (cfg, t_in, t_out, reason, px_out, net, win) -> all columns"""
    b = bars(market, tf) if b is None else b
    ts = b.ts.values
    o, h, l, c = b.open.values, b.high.values, b.low.values, b.close.values
    t_in = tr.t_in.values.astype("datetime64[ms]").astype("int64")
    t_out = tr.t_out.values.astype("datetime64[ms]").astype("int64")
    ei = np.searchsorted(ts, t_in)
    xi = np.searchsorted(ts, t_out)
    if not (np.array_equal(ts[ei], t_in) and np.array_equal(ts[xi], t_out)):
        raise RuntimeError("a trade time is not a bar open of this timeframe")
    d = cfgs.set_index("cfg").loc[tr.cfg.values, "dir"].values.astype(int)
    px_in = o[ei]
    stored = tr.px_out.notna().values
    px_out = np.where(stored, tr.px_out.fillna(0).values, o[xi])
    R = px_out / px_in
    fee = E.fees()[market]
    gross = d * (R - 1)
    fe = fee * (1 + R)
    fu = np.zeros(len(tr))
    fund = funding(market) if fund is None else fund
    if fund is not None:
        tau, cum = fund
        t_f = np.where(tr.reason.values == 10, t_out + (ts[-1] - ts[-2]), t_out)
        fu = d * (cum[np.searchsorted(tau, t_f, side="right")] - cum[np.searchsorted(tau, t_in, side="right")]) / px_in
    liq = tr.reason.values == 9
    fe = np.where(liq, fee, fe)
    worst, best = np.empty(len(tr)), np.empty(len(tr))
    for k in range(len(tr)):
        a, z, r = ei[k], xi[k], tr.reason.values[k]
        hi_end = z + 1 if r == 10 else z                                       # END: the last bar was fully held
        lo_ = l[a:hi_end].min() if hi_end > a else np.inf
        hi_ = h[a:hi_end].max() if hi_end > a else -np.inf
        if d[k] > 0:
            worst[k] = min(px_in[k], lo_, px_out[k]); best[k] = max(px_in[k], hi_, px_out[k])
        else:
            worst[k] = max(px_in[k], hi_, px_out[k]); best[k] = min(px_in[k], lo_, px_out[k])
    out = tr.copy()
    out["name"] = cfgs.set_index("cfg").loc[tr.cfg.values, "name"].values
    out["dir"] = d
    out["bars"] = xi - ei
    out["px_in"], out["px_out"] = px_in, px_out
    out["gross"], out["fee"], out["funding"] = gross, fe, fu
    out["net_rebuilt"] = np.where(liq, -1 - fee - fu, gross - fe - fu)
    out["mae"], out["mfe"] = d * (worst / px_in - 1), d * (best / px_in - 1)
    out["exit_reason"] = [E.REASONS[int(x)] for x in tr.reason.values]
    out["result"] = np.where(tr.win.values == 1, "PASS (profit)", "FAIL (loss)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--market", required=True)
    ap.add_argument("--tf", required=True)
    ap.add_argument("--date")
    ap.add_argument("--cfg", type=int)
    ap.add_argument("--csv")
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args()
    job = Path(a.run) / a.market / a.tf
    cfgs = pd.read_parquet(job / "configs.parquet", columns=["cfg", "name", "dir"])
    dset = ds.dataset(job / "trades.parquet")
    flt = None
    if a.cfg is not None:
        flt = ds.field("cfg") == a.cfg
    if a.date:
        d0 = pd.Timestamp(a.date, tz="UTC")
        f2 = (ds.field("t_out") >= d0) & (ds.field("t_out") < d0 + pd.Timedelta(days=1))
        flt = f2 if flt is None else flt & f2
    tr = dset.to_table(filter=flt).to_pandas()
    x = expand(tr, a.market, a.tf, cfgs)
    print(f"{len(x):,} trades; wins {int(x.win.sum()):,}, losses {int((x.win == 0).sum()):,}, sum net {x.net.sum():+.4f}")
    if a.csv:
        x.to_csv(a.csv, index=False); print(f"written {a.csv}")
    else:
        with pd.option_context("display.width", 250, "display.max_columns", 30):
            print(x.head(a.limit).to_string(index=False))


if __name__ == "__main__":
    main()
