"""DISPLAY ONLY (manual day study, logs/manual_day_study/MANUAL_DAY_STUDY_PROTOCOL.md): prints raw BTC candles of one UTC day on every
timeframe + the context known before the day. No signal, no rule, no analysis. Usage: python print_day_candles.py 2022-05-30 [--m1 HH:MM]"""
import sys
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parents[2]
day = pd.Timestamp(sys.argv[1])
pd.set_option("display.width", 200); pd.set_option("display.max_rows", 400)
d5 = pd.read_csv(P / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", parse_dates=["timestamp"]).drop_duplicates("timestamp").set_index("timestamp").sort_index()
d1 = pd.read_csv(P / "data/raw/BTCUSDT_1d_Raw_5Years.csv", parse_dates=["timestamp"]).set_index("timestamp").sort_index()
u1 = pd.read_csv(P / "data/universe_all/1d/BTCUSDT_1d.csv", parse_dates=["timestamp"]).set_index("timestamp").sort_index()
c = ["open", "high", "low", "close"]
chk = (d1.loc[day - pd.Timedelta(days=400):day, c] - u1.loc[day - pd.Timedelta(days=400):day, c]).abs().max().max()
print(f"[check] data/raw 1d vs universe_all 1d over the 400 days to {day.date()}: max |diff| = {chk}")
agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
fmt = lambda x: x[c + ["volume"]].round(2).to_string()


def chg(x):
    return x.assign(chg_pct=((x.close / x.open - 1) * 100).round(2), range_pct=((x.high / x.low - 1) * 100).round(2))


hist = d1.loc[:day - pd.Timedelta(days=1)]
print("\n=== CONTEXT known at", day, "UTC ===")
print("-- last 7 daily candles"); print(chg(hist.tail(7))[c + ["volume", "chg_pct", "range_pct"]].round(2).to_string())
wk = hist.resample("W-MON", label="left", closed="left").agg(agg)
print("-- last 4 weekly candles (Mon start; the last one may be partial up to the day before)"); print(chg(wk.tail(4))[c + ["chg_pct", "range_pct"]].round(2).to_string())
mo = hist.resample("MS").agg(agg)
print("-- last 3 monthly candles (the last one partial up to the day before)"); print(chg(mo.tail(3))[c + ["chg_pct", "range_pct"]].round(2).to_string())
yr = hist.loc[str(day.year)]
if len(yr):
    print(f"-- year {day.year} so far: open {yr.open.iloc[0]:.2f} high {yr.high.max():.2f} low {yr.low.min():.2f} last close {yr.close.iloc[-1]:.2f} ({(yr.close.iloc[-1] / yr.open.iloc[0] - 1) * 100:.2f}%)")
print(f"-- prior day high {hist.high.iloc[-1]:.2f} low {hist.low.iloc[-1]:.2f} close {hist.close.iloc[-1]:.2f}; 7-day high {hist.high.tail(7).max():.2f} low {hist.low.tail(7).min():.2f}; 30-day high {hist.high.tail(30).max():.2f} low {hist.low.tail(30).min():.2f}")
day5 = d5.loc[day:day + pd.Timedelta(hours=23, minutes=55)]
print(f"\n=== THE DAY {day.date()} ({day.day_name()}) ===  5m bars: {len(day5)}")
print("-- 1d:"); print(chg(day5.resample("1D").agg(agg))[c + ["volume", "chg_pct", "range_pct"]].round(2).to_string())
for rule in ("12h", "8h", "4h", "2h", "1h"):
    print(f"-- {rule}:"); print(chg(day5.resample(rule, origin="start_day").agg(agg))[c + ["volume", "chg_pct", "range_pct"]].round(2).to_string())
print("-- 30m:"); print(day5.resample("30min").agg(agg)[c].round(2).to_string())
print("-- 15m:"); print(day5.resample("15min").agg(agg)[c].round(2).to_string())
hi_t, lo_t = day5.high.idxmax(), day5.low.idxmin()
print(f"-- day high {day5.high.max():.2f} in 5m bar {hi_t}; day low {day5.low.min():.2f} in 5m bar {lo_t}")
nxt = d1.loc[day + pd.Timedelta(days=1):day + pd.Timedelta(days=1)]
print("-- next day (for exits that run past midnight):"); print(fmt(nxt))
if pd.Timestamp("2021-10-01") <= day <= pd.Timestamp("2024-12-31"):
    m1 = pd.read_csv(P / "archive/cleanup_2026_10_15/data/raw/BTCUSDT_1m_Raw_5Years.csv", dtype={"timestamp": str})
    m1 = m1[m1.timestamp.str.startswith(str(day.date()))].copy()            # later rows have corrupt timestamps: filter as text first
    m1["timestamp"] = pd.to_datetime(m1.timestamp); m1 = m1.set_index("timestamp").sort_index()
    a5 = m1.resample("5min").agg(agg)
    j = a5.index.intersection(day5.index)
    diff = (a5.loc[j, c] - day5.loc[j, c]).abs().max().max() if len(j) else None
    print(f"\n[check] 1m rows {len(m1)}; 1m aggregated to 5m vs verified 5m: {len(j)} bars, max |diff| = {diff}")
    for t0 in (lo_t, hi_t):
        w = m1.loc[t0 - pd.Timedelta(minutes=10):t0 + pd.Timedelta(minutes=15)]
        print(f"-- 1m around the 5m bar {t0}:"); print(w[c].round(2).to_string())
else:
    print("\n[1m] not used for this day (raw 1m timestamps are corrupt after 2024 / file starts 2021-10)")
