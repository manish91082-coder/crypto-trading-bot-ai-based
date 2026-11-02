"""BTC-ALLTF study (2026-10-28): buy-and-hold baselines for the report (same bars, same fees.json, same funding).
Usage: python src/btc_alltf/baselines.py --run <RUN dir>   -> <RUN>/report/baselines.csv
Spot: buy at the first 1d open, sell at the last close, one round-trip fee. Futures 1x long (and short): the same, plus every
funding payment from the funding file at the 1m open price. Per period D / V / H and per calendar year as well."""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as E                                                            # noqa: E402
import query as Q                                                             # noqa: E402

PROJ = Path(__file__).resolve().parents[2]


def hold(b, fee, fund, d, t0, t1):
    s = b[(b.ts >= t0) & (b.ts < t1)]
    if len(s) < 2:
        return np.nan, np.nan
    pi, po = s.open.iloc[0], s.close.iloc[-1]
    R = po / pi
    fu = 0.0
    if fund is not None:
        tau, cum = fund
        fu = d * (cum[np.searchsorted(tau, t1 - 1, side="right")] - cum[np.searchsorted(tau, s.ts.iloc[0], side="right")]) / pi
    net = d * (R - 1) - fee * (1 + R) - fu
    eq = s.close / pi if d > 0 else 2 - s.close / pi
    mdd = float((1 - eq / eq.cummax()).max())
    return net, mdd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    F = E.fees()
    rows = []
    edges = {"ALL": ("2000-01-01", "2026-10-01"), "D": ("2000-01-01", "2023-01-01"), "V": ("2023-01-01", "2025-01-01"),
             "H": ("2025-01-01", "2026-10-01")}
    edges.update({str(y): (f"{y}-01-01", f"{y + 1}-01-01") for y in range(2017, 2027)})
    for m in ("spot", "futures"):
        b = pd.read_parquet(PROJ / f"data/derived/btc_alltf/bars/{m}_1d.parquet", columns=["ts", "open", "close"])
        fund = Q.funding(m)
        for d in ((1,) if m == "spot" else (1, -1)):
            for k, (s0, s1) in edges.items():
                t0, t1 = (int(pd.Timestamp(x, tz="UTC").value // 10 ** 6) for x in (s0, s1))
                net, mdd = hold(b, F[m], fund, d, t0, t1)
                rows.append(dict(market=m, side="long" if d > 0 else "short", period=k, net=net, max_dd=mdd))
    out = Path(a.run) / "report" / "baselines.csv"
    out.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(pd.DataFrame(rows).pivot_table(index="period", columns=["market", "side"], values="net").round(4).to_string())


if __name__ == "__main__":
    main()
