"""T2-CARRY pre-lock history (2026-11-02). Runs BEFORE the protocol is locked, on data that is already open, and fixes the numbers the protocol quotes:
the identity with the Spot-DCA study (B1 per-year funding), rolling 90-day net carry on capital for the primary mix, and the Bybit-for-Binance proxy
check on 2026. No forward data is used. Output: logs/carry_t2_2026_11_02/PRELOCK_HISTORY.json
Usage: python src/research/carry_t2_prelock.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src/live_paper"))
import lpt                                                                    # noqa: E402

OUT = R_ / "logs/carry_t2_2026_11_02"
COINS = ("BTCUSDT", "ETHUSDT")
FEES = json.loads((R_ / "deploy/fees.json").read_text(encoding="utf-8"))["rules"]
RT = 2 * (FEES["paper_spot_per_side"] + FEES["paper_futures_taker_per_side"])  # two legs, in and out, on notional


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bybit_funding(sym, t0, t1):
    rows, end = [], t1
    while True:
        r = lpt.get(f"{lpt.BYB}/funding/history", dict(category="linear", symbol=sym, startTime=t0, endTime=end, limit=200))["result"]["list"]
        if not r:
            break
        rows += r
        low = min(int(x["fundingRateTimestamp"]) for x in r)
        if low <= t0 or len(r) < 200:
            break
        end = low - 1
    s = pd.Series({pd.Timestamp(int(x["fundingRateTimestamp"]), unit="ms"): float(x["fundingRate"]) for x in rows})
    return s.sort_index()


def main():
    OUT.mkdir(exist_ok=True)
    src = {c: R_ / f"data/futures_um/{c}_funding.csv" for c in COINS}
    F = {c: pd.read_csv(p, parse_dates=["time"]).set_index("time").funding_rate.astype(float) for c, p in src.items()}
    res = dict(round_trip_on_notional=RT, fees_sha256=sha(R_ / "deploy/fees.json"), inputs={c: sha(p) for c, p in src.items()}, funding_end=str(F["BTCUSDT"].index[-1]))
    study = json.loads((R_ / "logs/research_spot_dca/SPOT_DCA_RESULTS.json").read_text(encoding="utf-8"))
    res["identity"] = {}
    for c, f in F.items():
        g = f[(f.index >= "2020-07-01") & (f.index < "2026-10-01")]
        mine = {str(y): float(x.sum() * 100) for y, x in g.groupby(g.index.year)}
        theirs = {str(y): v["net_pct"] for y, v in study[f"B1_{c}"]["per_year"].items()}
        res["identity"][c] = dict(per_year=mine, equal=all(abs(mine[y] - theirs[y]) < 1e-9 for y in theirs) and set(mine) == set(theirs))
    d = pd.concat([f.groupby(f.index.floor("D")).sum().rename(c) for c, f in F.items()], axis=1).fillna(0).mean(axis=1)
    res["roll90"] = {}
    for name, per in (("2020-07", "2020-07-01"), ("2023", "2023-01-01"), ("2025", "2025-01-01"), ("2026", "2026-01-01")):
        net = (d[d.index >= per].rolling(90).sum().dropna() - RT) / 2 * 100     # % of capital, capital = 2 x notional
        res["roll90"][name] = dict(n=len(net), p5=float(np.percentile(net, 5)), p25=float(np.percentile(net, 25)), p50=float(np.median(net)),
                                   p75=float(np.percentile(net, 75)), p95=float(np.percentile(net, 95)), share_le_0=float((net <= 0).mean()))
    hurdle = res["roll90"]["2025"]["p50"] / 2
    res["hurdle_pct_of_capital"] = round(hurdle, 3)
    res["base_rate_ge_hurdle"] = {}
    for name, per in (("2025", "2025-01-01"), ("2026", "2026-01-01")):
        net = (d[d.index >= per].rolling(90).sum().dropna() - RT) / 2 * 100
        res["base_rate_ge_hurdle"][name] = float((net >= res["hurdle_pct_of_capital"]).mean())
    x = (d[d.index >= "2023-01-01"] / 2).cumsum()
    res["funding_only_max_dd_pct_since_2023"] = float((x - x.cummax()).min() * 100)
    t0, t1 = int(pd.Timestamp("2026-01-01").value // 10 ** 6), int(pd.Timestamp("2026-10-01").value // 10 ** 6)
    res["proxy_2026"] = {}
    for c in COINS:
        a = F[c][F[c].index >= "2026-01-01"].copy()
        a.index = a.index.floor("h")
        j = pd.concat([a.rename("bin"), bybit_funding(c, t0, t1).rename("byb")], axis=1).dropna()
        res["proxy_2026"][c] = dict(n=len(j), binance_sum_pct=float(j.bin.sum() * 100), bybit_sum_pct=float(j.byb.sum() * 100), corr=float(j.bin.corr(j.byb)),
                                    sign_agree=float((np.sign(j.bin) == np.sign(j.byb)).mean()))
    (OUT / "PRELOCK_HISTORY.json").write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("round_trip_on_notional", "roll90", "hurdle_pct_of_capital", "base_rate_ge_hurdle", "funding_only_max_dd_pct_since_2023", "proxy_2026")}, indent=1))
    print("identity", {c: v["equal"] for c, v in res["identity"].items()})


if __name__ == "__main__":
    main()
