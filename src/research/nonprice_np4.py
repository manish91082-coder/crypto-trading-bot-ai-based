"""NP4 (logs/research_nonprice/NP4_PROTOCOL_PREREGISTERED.md, SHA 9ef4dd3e...): PREM_Z 24h rule on the sealed H, once.
P1 = NP1 S2 rule (top quintile short, bottom quintile long); P2 = bottom quintile long only (post-hoc, flagged). Usage: python src/research/nonprice_np4.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nonprice_np1 import FEES, OUT, cluster_t, log, trailing_pct  # noqa: E402

FUT_RT = 2 * FEES["rules"]["paper_futures_taker_per_side"]
SPOT_RT = 2 * FEES["rules"]["paper_spot_per_side"]
H0, H1 = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-09-30")


def main():
    log("NP4 start (H opened once for P1 / P2)")
    X = pd.read_parquet(OUT / "np1_features_1h.parquet")
    S = X[X.t.dt.hour == 0][["t", "PREM_Z", "r_24h"]].dropna(subset=["PREM_Z"]).reset_index(drop=True)
    S["p"] = trailing_pct(S.t.to_numpy(), S.PREM_Z.to_numpy())
    H = S[(S.t >= H0) & (S.t <= H1)].dropna(subset=["p", "r_24h"])
    cfgs = {"P1": (np.where(H.p >= 0.8, -1, np.where(H.p <= 0.2, 1, 0)), FUT_RT),
            "P2": (np.where(H.p <= 0.2, 1, 0), FUT_RT),
            "P2_SPOT_INFO": (np.where(H.p <= 0.2, 1, 0), SPOT_RT)}
    days = pd.DataFrame({"date": pd.date_range(H0, H1, freq="D")})
    trades, daily, monthly, summ = [], [], [], []
    for c, (side, cost) in cfgs.items():
        T = H[side != 0].assign(side=side[side != 0], cfg=c)
        T["net"] = (T.side * T.r_24h - cost) * 100
        trades.append(T)
        d = days.merge(T.assign(date=T.t.dt.floor("D")).groupby("date").net.sum().reset_index(), on="date", how="left").fillna({"net": 0.0})
        mo = d.groupby(d.date.dt.to_period("M")).net.sum()
        y25, y26 = d[d.date.dt.year == 2025].net.sum(), d[d.date.dt.year == 2026].net.sum()
        m, t = T.net.mean(), cluster_t(T)
        lb = m - 2.24 * (m / t)
        s = dict(cfg=c, trades=len(T), win=float((T.net > 0).mean()), mean_net_pct=m, t_cluster=t, lb_224=lb, total_pct=T.net.sum(),
                 months_pos=int((mo > 0).sum()), months=len(mo), worst_month_pct=float(mo.min()), sum_2025=y25, sum_2026=y26,
                 long_n=int((T.side > 0).sum()), long_mean=T[T.side > 0].net.mean(), short_n=int((T.side < 0).sum()), short_mean=T[T.side < 0].net.mean())
        s["passes"] = bool(m > 0 and lb > 0 and s["months_pos"] >= 13 and y25 > 0 and y26 > 0) if c != "P2_SPOT_INFO" else None
        summ.append(s)
        daily.append(d.assign(cfg=c))
        monthly.append(mo.rename("net_pct").reset_index().assign(cfg=c))
    pd.concat(trades)[["cfg", "t", "PREM_Z", "p", "side", "r_24h", "net"]].to_csv(OUT / "np4_trades.csv", index=False)
    pd.concat(daily).to_csv(OUT / "np4_daily.csv", index=False)
    pd.concat(monthly).to_csv(OUT / "np4_monthly.csv", index=False)
    pd.DataFrame(summ).to_csv(OUT / "np4_summary.csv", index=False)
    log("NP4 H: " + json.dumps(pd.DataFrame(summ).round(4).to_dict("records"), default=str))
    outs = sorted(f for f in OUT.iterdir() if f.name.startswith("np4_"))
    (OUT / "NP4_OUTPUT_SHA256.txt").write_text("".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in outs), encoding="utf-8")


if __name__ == "__main__":
    main()
