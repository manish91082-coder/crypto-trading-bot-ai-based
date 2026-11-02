"""
Step 6.4 survivorship reality check (pre-registered; reported as is, not an acceptance gate).

The 10-coin universe was chosen in 2026 (survivors). Here the Step 7 Swing-AI system is re-run on a POINT-IN-TIME
universe: each year Y the 10 coins with the highest trailing-365-day USDT volume (volume x close) on (Y-1)-12-31,
chosen from the 10 coins + 20 large 2020-2022 coins incl. later collapsed/delisted ones (data/raw_extended/).

Delisted coins: after the last real candle the price is frozen (flat candles, no new candidates) -- the position is
valued at the last traded price until the end and cannot be sold earlier (conservative).
Everything else (features, 13 plans, monthly re-training, decision rule, risk layer) is identical to Step 7.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_study_1d as SS
import swing_strategy_1d as E
import step7_swing_ai_1d as S7
from config import DATA_DIR, LOGS_DIR, SYMBOLS

OUT = LOGS_DIR / "strategy_1d_step6_4_survivorship"
EXT = DATA_DIR / "raw_extended"
YEARS = range(2021, 2027)


def load_all():
    data, real_last = {}, {}
    for s in SYMBOLS:
        data[s] = SS.load_1d(s)
    for f in sorted(EXT.glob("*_1d_extended.csv")):
        s = f.name.split("_")[0]
        data[s] = SS.load_1d(s, f)
    for s, df in data.items():
        real_last[s] = df["timestamp"].max()
        if real_last[s] < S7.DATA_END:
            pad_days = pd.date_range(real_last[s] + pd.Timedelta(days=1), S7.DATA_END, freq="D")
            c = float(df["close"].iloc[-1])
            pad = pd.DataFrame(dict(timestamp=pad_days, open=c, high=c, low=c, close=c, volume=0.0))
            df = pd.concat([df[["timestamp", "open", "high", "low", "close", "volume"]], pad], ignore_index=True)
            tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(), (df.low - df.close.shift()).abs()],
                           axis=1).max(axis=1)
            df["ATR_14"] = tr.rolling(14).mean()
            data[s] = df
    return data, real_last


def universe(data, real_last):
    rows = []
    for y in YEARS:
        cut = pd.Timestamp(f"{y - 1}-12-31")
        vol = {}
        for s, df in data.items():
            w = df[(df.timestamp > cut - pd.Timedelta(days=365)) & (df.timestamp <= cut) & (df.timestamp <= real_last[s])]
            if len(w) >= 180 and real_last[s] > cut:
                vol[s] = float((w.volume * w.close).sum())
        top = sorted(vol, key=vol.get, reverse=True)[:10]
        rows.append(dict(year=y, members=";".join(top), from_original_10=sum(t in SYMBOLS for t in top)))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, real_last = load_all()
    print("coins:", len(data), "| delisted/ended:", {s: str(d.date()) for s, d in real_last.items() if d < S7.DATA_END})
    uni = universe(data, real_last)
    uni.to_csv(OUT / "point_in_time_universe.csv", index=False)
    print(uni.to_string(index=False))
    member = {(y, s) for y, m in zip(uni.year, uni.members) for s in m.split(";")}

    cands = S7.build_candidates(data)
    cands = cands[cands.apply(lambda r: r.signal_date < real_last[r.symbol], axis=1)].reset_index(drop=True)
    mx = S7.build_matrix(data, cands)
    mx.to_csv(OUT / "swing_permutation_matrix_30coins.csv", index=False)
    pred, log = S7.walk_forward_predictions(mx)
    pred = pred[[(d.year, s) in member for s, d in zip(pred.symbol, pred.signal_date)]]   # trade only members
    pred.to_csv(OUT / "AI_point_in_time_predictions.csv", index=False)
    tr, eq, cash = S7.portfolio(data, pred)
    tr.drop(columns=["plan"], errors="ignore").to_csv(OUT / "AI_point_in_time_trades.csv", index=False)
    eq.to_csv(OUT / "AI_point_in_time_equity.csv", index=False)
    assert abs(E.INITIAL_CAPITAL + tr["pnl"].sum() - cash) < 1e-6
    s = S7.summarize(tr, eq, cash, "AI_point_in_time_universe")
    ref = pd.read_csv(S7.OUT / "oos_summary.csv").iloc[0].to_dict()
    pd.DataFrame([ref, s]).to_csv(OUT / "comparison.csv", index=False)
    print(pd.DataFrame([ref, s]).T.to_string())
    by = tr.groupby("symbol").pnl.agg(["size", "sum"]).sort_values("sum")
    by.to_csv(OUT / "pnl_by_coin.csv")
    print(by.to_string())


if __name__ == "__main__":
    main()
