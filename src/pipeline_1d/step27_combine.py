"""
Step 27: combine the verified timeframe sleeves (1D, 4H R6, 1h R24, BTC) + position-size table + 1-year outcome ranges.
Protocol: logs/strategy_1d_step27_combine/STEP27_PROTOCOL_PREREGISTERED.md (SHA256 locked before any combined result).
"""
import sys
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core_rows_1d as CR
import step13_unseen_coins_1d as S13
import step19_large_caps_1d as S19
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import step24_1h_brain as S24
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step27_combine"
PROTO_NAME = "STEP27_PROTOCOL_PREREGISTERED.md"
CAP, COST = 10_000.0, 0.0025
FS = (1.0, 0.75, 0.5, 0.3)
PER = {"MAIN": (pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30")), "PRE": (pd.Timestamp("2018-02-01"), pd.Timestamp("2019-12-31"))}
REF = {"MAIN": dict(D1=74452.43, H4=98734.89, H1=201548.26, BTC=28767.66), "PRE": dict(D1=3423.80, H1=2836.59, BTC=6960.89)}
MIXES = {"M_AI3": dict(D1=1 / 3, H4=1 / 3, H1=1 / 3), "M_AI3_BTC": dict(D1=0.25, H4=0.25, H1=0.25, BTC=0.25),
         "D1": dict(D1=1.0), "H4": dict(H4=1.0), "H1": dict(H1=1.0), "BTC": dict(BTC=1.0)}


def daily(series_or_df):
    if isinstance(series_or_df, pd.DataFrame):
        return series_or_df.set_index("date").equity
    s = series_or_df
    s = s[s.index.hour == s.index.hour.max()]
    s.index = s.index.normalize()
    return s


def btc(px, start, end, f):
    o = px["BTCUSDT"]
    units = f * CAP / (1 + COST) / o.at[start, "open"]
    cash = CAP - f * CAP
    dates = pd.date_range(start, end, freq="D")
    eq = pd.Series([cash + units * o.at[d, "close"] for d in dates], index=dates)
    return cash + units * o.at[end, "close"] * (1 - COST), eq


def stats(final, eq, start, end):
    a = np.r_[CAP, eq.values]
    pk = np.maximum.accumulate(a)
    dd = float(((pk - a) / pk).max())
    cagr = (final / CAP) ** (365.25 / (end - start).days) - 1
    ye = eq.groupby(eq.index.year).last()
    yr = (ye / ye.shift(1).fillna(CAP) - 1) * 100
    return dict(final=round(float(final), 2), cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd * 100, 2),
                calmar=round(cagr / dd, 3) if dd > 0 else None, **{f"ret_{y}": round(float(v), 2) for y, v in yr.items()})


def monthly_multiples(eq):
    me = eq.groupby(eq.index.to_period("M")).last()
    return (me / me.shift(1).fillna(CAP)).values


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = S23.sha_file(OUT / PROTO_NAME)
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_)
    sleeves = {}           # (period, f) -> {name: (final, daily Series)}

    # ---------- MAIN 2021-26 ----------
    start, end = PER["MAIN"]
    dk, lk, dn, ln, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", end)
    data, last = {**dk, **dn}, {**lk, **ln}
    rows19 = pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    px1 = {s: data[s].set_index("timestamp")[["open", "low", "close"]] for s in set(rows19.symbol) | {"BTCUSDT"}}
    p4 = pd.read_csv(S23.OUT / "test_predictions_4h.csv", usecols=["symbol", "bar", "R6_AI"], parse_dates=["bar"]).rename(columns={"R6_AI": "score"})
    p1 = pd.read_csv(S24.OUT / "test_predictions_1h.csv", usecols=["symbol", "bar", "R24_AI"], parse_dates=["bar"]).rename(columns={"R24_AI": "score"})
    px4 = {s: S23.bars_4h(S23.UNI1H / f"{s}_1h_full.csv.gz")[["open", "close"]] for s in p4.symbol.unique()}
    pxh = {s: S24.bars_1h(S24.UNI1H / f"{s}_1h_full.csv.gz")[["open", "close"]] for s in p1.symbol.unique()}
    S23.START, S23.END_BAR = start, end + pd.Timedelta(hours=20)
    S24.START, S24.END_BAR = start, end + pd.Timedelta(hours=23)
    for f in FS:
        r = S22.simulate(rows19, start, end, px1, last, f, 5, 10)
        r4 = S23.sim4h(p4, 6, px4, COST, invest=f)
        rh = S24.sim1h(p1, 24, pxh, COST, invest=f)
        fb, eb = btc(px1, start, end, f)
        sleeves[("MAIN", f)] = dict(D1=(r["final"], daily(r["eq"])), H4=(r4["final"], daily(r4["eq"])),
                                    H1=(rh["final"], daily(rh["eq"])), BTC=(fb, eb))
        print("MAIN", f, {k: round(v[0], 2) for k, v in sleeves[("MAIN", f)].items()}, f"({time.time()-t0:.0f}s)", flush=True)
    del data, px1, px4, pxh

    # ---------- PRE 2018-19 ----------
    start, end = PER["PRE"]
    dk, lk, dn, ln, _ = S22.load_pre(S22.PRE / "1d", S22.PRE / "1h", S22.ASOF_PRE)
    data, last = {**dk, **dn}, {**lk, **ln}
    u22 = pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    px1 = {s: data[s].set_index("timestamp")[["open", "low", "close"]] for s in set(u22.symbol) | {"BTCUSDT"}}
    q4 = pd.read_csv(S23.OUT / "pre2020_predictions_4h.csv", usecols=["symbol", "bar", "R6_FROZEN"], parse_dates=["bar"]).rename(columns={"R6_FROZEN": "score"})
    q1 = pd.read_csv(S24.OUT / "pre2020_predictions_1h.csv", usecols=["symbol", "bar", "R24_FROZEN"], parse_dates=["bar"]).rename(columns={"R24_FROZEN": "score"})
    px4 = {s: S23.bars_4h(S23.PRE1H / f"{s}_1h_full.csv.gz")[["open", "close"]] for s in q4.symbol.unique()}
    pxh = {s: S24.bars_1h(S24.PRE1H / f"{s}_1h_full.csv.gz")[["open", "close"]] for s in q1.symbol.unique()}
    S23.START, S23.END_BAR = start, end + pd.Timedelta(hours=20)
    S24.START, S24.END_BAR = start, end + pd.Timedelta(hours=23)
    for f in FS:
        r = S22.simulate(u22, start, end, px1, last, f, 5, 10)
        r4 = S23.sim4h(q4, 6, px4, COST, invest=f)
        rh = S24.sim1h(q1, 24, pxh, COST, invest=f)
        fb, eb = btc(px1, start, end, f)
        sleeves[("PRE", f)] = dict(D1=(r["final"], daily(r["eq"])), H4=(r4["final"], daily(r4["eq"])),
                                   H1=(rh["final"], daily(rh["eq"])), BTC=(fb, eb))
        print("PRE", f, {k: round(v[0], 2) for k, v in sleeves[("PRE", f)].items()}, f"({time.time()-t0:.0f}s)", flush=True)

    # ---------- G0 ----------
    g0 = {f"{per}_{k}": abs(sleeves[(per, 1.0)][k][0] - v) < 0.01 for per, d in REF.items() for k, v in d.items()}
    claims["G0"] = g0
    claims["G0_all"] = all(g0.values())
    for (per, f), d in sleeves.items():
        pd.DataFrame({k: v[1] for k, v in d.items()}).to_csv(OUT / f"sleeves_{per}_f{int(f*100)}.csv", index_label="date")
    claims["sleeve_finals"] = {f"{per}_f{int(f*100)}": {k: v[0] for k, v in d.items()} for (per, f), d in sleeves.items()}

    # ---------- correlation ----------
    M = pd.DataFrame({k: v[1] for k, v in sleeves[("MAIN", 1.0)].items()})
    claims["corr_daily_returns_MAIN_f100"] = M.pct_change().corr().round(3).to_dict()

    # ---------- mixes ----------
    rng = np.random.default_rng(27)
    table = []
    for f in FS:
        for mix, w in MIXES.items():
            row = dict(f=f, mix=mix)
            mm = []
            for per in ("MAIN", "PRE"):
                start, end = PER[per]
                d = sleeves[(per, f)]
                eq = sum(wt * d[k][1] for k, wt in w.items())
                final = sum(wt * d[k][0] for k, wt in w.items())
                s = stats(final, eq, start, end)
                row.update({f"{per}_{k}": v for k, v in s.items()})
                mm.append(monthly_multiples(eq))
            pool = np.concatenate(mm)
            draws = np.prod(pool[rng.integers(0, len(pool), size=(10_000, 12))], axis=1)
            row.update({f"y1_p{q}": round(float(np.percentile(draws, q)), 3) for q in (5, 25, 50, 75, 95)})
            row["y1_P_loss_gt30"] = round(float(np.mean(draws < 0.70)), 4)
            row["pooled_months"] = int(len(pool))
            table.append(row)
    T = pd.DataFrame(table)
    T.to_csv(OUT / "decision_table.csv", index=False)
    claims["decision_table"] = table
    ok = T[T.mix.isin(["M_AI3", "M_AI3_BTC"]) & (T.y1_p5 >= 0.50)]
    if len(ok):
        best_f = ok.f.max()
        pick = ok[ok.f == best_f].sort_values("y1_p50", ascending=False).iloc[0]
        claims["recommendation"] = dict(mix=pick.mix, f=float(pick.f), y1_p5=float(pick.y1_p5), y1_p50=float(pick.y1_p50))
    else:
        claims["recommendation"] = "none of the mixes has a 5th-percentile 1-year multiple >= 0.50"
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    cols = ["f", "mix", "MAIN_final", "MAIN_max_dd_pct", "MAIN_calmar", "PRE_final", "PRE_max_dd_pct", "y1_p5", "y1_p50", "y1_p95", "y1_P_loss_gt30"]
    print(T[cols].to_string(index=False))
    print("G0", claims["G0_all"], g0)
    print("corr", claims["corr_daily_returns_MAIN_f100"])
    print("RECOMMENDATION", claims["recommendation"], f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
