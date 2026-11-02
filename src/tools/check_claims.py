"""CALCULATOR ONLY for the manual day study: checks numbers written in a day log against the raw verified 5m data.
No rule search, no analysis. Usage: python check_claims.py claims.json   (list of claims)
claim kinds:
  {"k":"bar","tf":"15min","t":"2020-02-25 12:00","f":"close","v":9612.93}       candle field of a UTC-aggregated bar
  {"k":"ext","f":"high"|"low","a":"start","b":"end","v":x}                       max high / min low of 5m bars with open time in [a, b]
  {"k":"ret","side":"long"|"short","e":x,"x":y,"v":pct}                           gross % return
  {"k":"net","gross":pct,"cost":pct,"v":pct}                                      net = gross - cost
  {"k":"first","f":"low_le"|"high_ge","lvl":x,"a":"start","b":"end","v":"bar time"} first 5m bar with low <= lvl (or high >= lvl)"""
import json
import sys
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parents[2]
d5 = pd.read_csv(P / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", parse_dates=["timestamp"]).drop_duplicates("timestamp").set_index("timestamp").sort_index()
agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
claims = json.loads(Path(sys.argv[1]).read_text())
bad = 0
for c in claims:
    k = c["k"]
    if k == "bar":
        t = pd.Timestamp(c["t"]); w = d5.loc[t:t + pd.Timedelta(c["tf"]) - pd.Timedelta(minutes=5)]
        x = dict(open=w.open.iloc[0], high=w.high.max(), low=w.low.min(), close=w.close.iloc[-1])[c["f"]]
        okk = abs(x - c["v"]) < 0.005
    elif k == "ext":
        w = d5.loc[pd.Timestamp(c["a"]):pd.Timestamp(c["b"])]; x = w.high.max() if c["f"] == "high" else w.low.min()
        okk = abs(x - c["v"]) < 0.005
    elif k == "ret":
        x = (c["x"] / c["e"] - 1) * 100 if c["side"] == "long" else (c["e"] / c["x"] - 1) * 100 if False else (c["e"] - c["x"]) / c["e"] * 100
        okk = abs(x - c["v"]) < 0.0015
    elif k == "net":
        x = c["gross"] - c["cost"]; okk = abs(x - c["v"]) < 0.0015
    elif k == "first":
        w = d5.loc[pd.Timestamp(c["a"]):pd.Timestamp(c["b"])]
        m = w.low <= c["lvl"] if c["f"] == "low_le" else w.high >= c["lvl"]
        x = str(m.idxmax()) if m.any() else "none"; okk = x == c["v"]
    bad += not okk
    print(f"[{'OK ' if okk else 'BAD'}] {json.dumps(c)} -> computed {x if not isinstance(x, float) else round(x, 4)}")
print(f"TOTAL {len(claims)} claims, BAD {bad}")
