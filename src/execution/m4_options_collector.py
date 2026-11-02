"""
M4 daily public collector: options, implied volatility, quarterly basis (protocol: logs/collector_m4_options/M4_PROTOCOL_PREREGISTERED.md).
Public endpoints only, no keys, no orders. Usage: pythonw m4_options_collector.py
"""
import sys
import gzip
import json
import time
import hashlib
import traceback
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from config import DATA_DIR, LOGS_DIR

LOG = LOGS_DIR / "collector_m4_options"
PROTO = LOG / "M4_PROTOCOL_PREREGISTERED.md"
LEDGER = LOG / "ledger.csv"
STORE = DATA_DIR / "collector_m4"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def get(url):
    last = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "m4-collector"}), timeout=60) as r:
                return r.status, r.read()
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    return None, str(last).encode()


def endpoints(now_ms):
    start = now_ms - 2 * 86_400_000
    eps = {}
    for c in ("BTC", "ETH"):
        eps[f"deribit_dvol_{c}"] = (f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={c}"
                                    f"&start_timestamp={start}&end_timestamp={now_ms}&resolution=3600")
        eps[f"deribit_options_{c}"] = f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={c}&kind=option"
        eps[f"deribit_index_{c}"] = f"https://www.deribit.com/api/v2/public/get_index_price?index_name={c.lower()}_usd"
    eps["binance_options_mark"] = "https://eapi.binance.com/eapi/v1/mark"
    eps["binance_options_ticker"] = "https://eapi.binance.com/eapi/v1/ticker"
    st, body = get("https://fapi.binance.com/fapi/v1/exchangeInfo")
    q = []
    if st == 200:
        q = [s["symbol"] for s in json.loads(body)["symbols"] if s.get("contractType") in ("CURRENT_QUARTER", "NEXT_QUARTER")
             and s.get("status") == "TRADING" and s["symbol"].split("_")[0] in ("BTCUSDT", "ETHUSDT")]
    for s in q + ["BTCUSDT", "ETHUSDT"]:
        eps[f"binance_premium_{s}"] = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={s}"
    return eps


def summarise(saved):
    out = {}
    for c in ("BTC", "ETH"):
        d = saved.get(f"deribit_dvol_{c}")
        if d:
            rows = d["result"]["data"]
            out[f"dvol_{c}_close"] = rows[-1][4] if rows else None
        o = saved.get(f"deribit_options_{c}")
        out[f"deribit_n_options_{c}"] = len(o["result"]) if o else None
    m = saved.get("binance_options_mark")
    out["binance_n_options"] = len(m) if isinstance(m, list) else None
    for k, v in saved.items():
        if k.startswith("binance_premium_") and "_" in k[len("binance_premium_"):]:
            mark, index = float(v["markPrice"]), float(v["indexPrice"])
            exp = pd.Timestamp("20" + k.split("_")[-1][:2] + "-" + k.split("_")[-1][2:4] + "-" + k.split("_")[-1][4:6] + " 08:00")
            days = max((exp - pd.Timestamp.now("UTC").tz_localize(None)) / pd.Timedelta(days=1), 1e-9)
            out[f"basis_ann_{k[len('binance_premium_'):]}"] = round((mark / index - 1) * 365 / days, 6)
    return out


def main():
    assert sha(PROTO.read_bytes()) == (LOG / "M4_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"
    now = pd.Timestamp.now("UTC").tz_localize(None)
    day = str(now.date())
    if LEDGER.exists() and (pd.read_csv(LEDGER).day == day).any():
        print(f"{day} already collected -> nothing to do")
        return
    folder = STORE / day
    folder.mkdir(parents=True, exist_ok=True)
    files, saved, status = {}, {}, {}
    for name, url in endpoints(int(now.value // 1_000_000)).items():
        st, body = get(url)
        status[name] = st
        if st == 200:
            f = folder / f"{name}.json.gz"
            f.write_bytes(gzip.compress(body))
            files[name] = dict(sha256=sha(f.read_bytes()), bytes=len(body))
            saved[name] = json.loads(body)
    line = dict(run_utc=str(now), day=day, n_ok=sum(1 for v in status.values() if v == 200), n_endpoints=len(status),
                status=json.dumps(status), files=json.dumps(files), summary=json.dumps(summarise(saved)),
                code_sha256=sha(Path(__file__).read_bytes()), protocol_sha256=sha(PROTO.read_bytes()))
    line["prev_sha256"] = pd.read_csv(LEDGER).line_sha256.iloc[-1] if LEDGER.exists() else "GENESIS"
    line["line_sha256"] = sha(json.dumps(line, sort_keys=True).encode())
    pd.DataFrame([line]).to_csv(LEDGER, mode="a", index=False, header=not LEDGER.exists())
    print(f"{day}: {line['n_ok']}/{line['n_endpoints']} endpoints OK; summary {line['summary']}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOG.mkdir(parents=True, exist_ok=True)
        with open(LOG / "run_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{pd.Timestamp.now('UTC')}] RUN FAILED\n{traceback.format_exc()}\n")
        sys.exit(1)
