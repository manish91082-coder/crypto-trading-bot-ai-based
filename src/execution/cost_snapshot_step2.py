"""
Step 2 cost study (protocol: logs/cost_study_step2/STEP2_COST_PROTOCOL_PREREGISTERED.md).
NO ORDERS. Reads the PUBLIC Binance spot order book (GET /api/v3/depth, limit 1000) for the forward universe and
measures, per coin and notional, the cost of a market buy / sell against the mid price by walking the real book.
Usage: pythonw cost_snapshot_step2.py        (scheduled: one snapshot round, around the 00:00 UTC rebalance)
       python  cost_snapshot_step2.py --now  (one round at any time; tagged as off-schedule)
"""
import sys
import gzip
import json
import time
import hashlib
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import LOGS_DIR, DATA_DIR

LOG = LOGS_DIR / "cost_study_step2"
RAW = DATA_DIR / "forward" / "depth_raw"
FM_PRED = LOGS_DIR / "forward_multi_16b" / "predictions"
FM_TEST = LOGS_DIR / "forward_multi_16b" / "test" / "predictions"
DEPTH = "https://api.binance.com/api/v3/depth"
NOTIONALS = (100, 333, 1000, 3333, 10000, 30000)
SESSION = requests.Session()


def log(msg):
    LOG.mkdir(parents=True, exist_ok=True)
    line = f"[{pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}"
    with open(LOG / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line, flush=True)
    except Exception:
        pass


def universe():
    """Symbols of the latest Step 16B day (production first, else the technical test day) + BTCUSDT."""
    for d in (FM_PRED, FM_TEST):
        fs = sorted(d.glob("d1_*.csv")) if d.exists() else []
        if fs:
            day = fs[-1].stem.split("_", 1)[1]
            syms = set()
            for k in ("d1", "h4_r6", "h1_r24"):
                f = d / f"{k}_{day}.csv"
                if f.exists():
                    syms |= set(pd.read_csv(f).symbol)
            return sorted(syms | {"BTCUSDT"}), f"{d.parent.name}/{day}"
    raise RuntimeError("no Step 16B prediction file yet")


def walk(levels, notional):
    """Average fill price for spending `notional` USDT through `levels` [(price, qty)...]; NaN if the book is too thin."""
    left, qty = notional, 0.0
    for p, q in levels:
        take = min(left, p * q)
        qty += take / p
        left -= take
        if left <= 1e-9:
            return notional / qty
    return np.nan


def measure(sym, book):
    bids = [(float(p), float(q)) for p, q in book["bids"]]
    asks = [(float(p), float(q)) for p, q in book["asks"]]
    bb, ba = bids[0][0], asks[0][0]
    mid = (bb + ba) / 2
    row = dict(symbol=sym, best_bid=bb, best_ask=ba, mid=mid, half_spread_bps=(ba - mid) / mid * 1e4,
               depth_bid_1pct_usd=sum(p * q for p, q in bids if p >= mid * 0.99),
               depth_ask_1pct_usd=sum(p * q for p, q in asks if p <= mid * 1.01))
    for n in NOTIONALS:
        buy = walk(asks, n)
        # selling: units worth `n` at mid, walked down the bids
        units, got, left = n / mid, 0.0, n / mid
        for p, q in bids:
            t = min(left, q)
            got += t * p
            left -= t
            if left <= 1e-12:
                break
        sell = got / units if left <= 1e-12 else np.nan
        row[f"buy_bps_{n}"] = (buy / mid - 1) * 1e4
        row[f"sell_bps_{n}"] = (1 - sell / mid) * 1e4
    return row


def main(now_flag=False):
    t = pd.Timestamp.now("UTC").tz_localize(None)
    syms, src = universe()
    raw, rows = {}, []
    for s in syms:
        for k in range(5):
            try:
                r = SESSION.get(DEPTH, params=dict(symbol=s, limit=1000), timeout=20)
                if r.status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(2 * (k + 1))
        else:
            log(f"{s}: depth not available")
            continue
        b = r.json()
        raw[s] = dict(t_utc=str(pd.Timestamp.now("UTC")), book=b)
        rows.append(dict(t_utc=raw[s]["t_utc"], **measure(s, b)))
        time.sleep(0.25)                      # weight 50 per call at limit 1000; ~20 calls stay far below 6000/min
    RAW.mkdir(parents=True, exist_ok=True)
    blob = gzip.compress(json.dumps(raw).encode())
    rp = RAW / f"depth_{t.strftime('%Y%m%dT%H%M%S')}.json.gz"
    rp.write_bytes(blob)
    df = pd.DataFrame(rows).assign(round_utc=str(t), off_schedule=now_flag, universe_source=src,
                                   raw_file=rp.name, raw_sha256=hashlib.sha256(blob).hexdigest())
    out = LOG / "snapshots.csv"
    df.to_csv(out, mode="a", index=False, header=not out.exists())
    log(f"round {t} ({'off-schedule' if now_flag else 'scheduled'}): {len(df)} coins from {src}; raw {rp.name}")


if __name__ == "__main__":
    try:
        main(now_flag="--now" in sys.argv)
    except Exception:
        log("ROUND FAILED:\n" + traceback.format_exc())
        sys.exit(1)
