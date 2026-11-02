"""
Hourly proof that the 1D testnet bot is REALLY alive and consistent (anti-false-claim rule #3).
Read-only: never places or cancels orders.

H1 process : a pythonw/python process whose command line runs the configured live engine with --daemon
H2 heartbeat: last '[heartbeat ...]' line in the daemon log is younger than 30 minutes
H3 exchange : for every open position in the bot state, the testnet wallet holds the coin (free+locked >= 99% of
              units) and the stop order exists, is open and covers the units
Writes one row per run to logs/health/health_log.csv and prints OK / ALERT lines.
"""
import os
import re
import sys
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
ENGINE = "live_1d_ai_engine.py"
LIVE_DIR = ROOT / "logs" / "live_1d_ai"
HEALTH = ROOT / "logs" / "health"


def check():
    import psutil
    res = dict(time_utc=str(pd.Timestamp.now("UTC").tz_localize(None)))
    procs = [p for p in psutil.process_iter(["pid", "cmdline"])
             if p.info["cmdline"] and any(ENGINE in c for c in p.info["cmdline"]) and "--daemon" in p.info["cmdline"]]
    res["H1_process"] = "OK pid " + ",".join(str(p.info["pid"]) for p in procs) if procs else "ALERT no daemon process"
    log = LIVE_DIR / "daemon_testnet.log"
    beats = re.findall(r"\[heartbeat ([0-9\- :\.]+)\]", log.read_text(encoding="utf-8")) if log.exists() else []
    if beats:
        age = (pd.Timestamp.now("UTC").tz_localize(None) - pd.Timestamp(beats[-1])).total_seconds() / 60
        res["H2_heartbeat"] = f"{'OK' if age < 30 else 'ALERT'} last {beats[-1]} ({age:.0f} min ago)"
    else:
        res["H2_heartbeat"] = "ALERT no heartbeat in log"
    st_file = LIVE_DIR / "state_testnet.json"
    try:
        import ccxt
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        ex = ccxt.binance({"apiKey": os.getenv("BINANCE_API_KEY", ""), "secret": os.getenv("BINANCE_API_SECRET", ""),
                           "options": {"defaultType": "spot", "fetchMarkets": ["spot"]}})   # never touch futures endpoints
        ex.set_sandbox_mode(True)
        assert "testnet" in ex.urls["api"]["public"]
        st = json.loads(st_file.read_text()) if st_file.exists() else {"positions": {}}
        bal = ex.fetch_balance()
        probs = []
        for s, p in st["positions"].items():
            coin = s[:-4]
            held = float(bal["total"].get(coin) or 0.0)
            if held < 0.99 * p["units"]:
                probs.append(f"{s} wallet {held} < units {p['units']}")
            if p.get("stop_id"):
                o = ex.fetch_order(p["stop_id"], f"{coin}/USDT")
                if o["status"] != "open" or float(o["amount"]) < 0.99 * float(ex.amount_to_precision(f"{coin}/USDT", p["units"])):
                    probs.append(f"{s} stop {p['stop_id']} status {o['status']} amount {o['amount']}")
            else:
                probs.append(f"{s} has no stop order id")
        res["H3_exchange"] = ("ALERT " + "; ".join(probs)) if probs else f"OK {len(st['positions'])} positions reconciled"
    except Exception as e:
        res["H3_exchange"] = f"ALERT {type(e).__name__}: {e}"
    res["status"] = "ALERT" if any(str(v).startswith("ALERT") for k, v in res.items() if k.startswith("H")) else "OK"
    return res


if __name__ == "__main__":
    HEALTH.mkdir(parents=True, exist_ok=True)
    r = check()
    f = HEALTH / "health_log.csv"
    pd.DataFrame([r]).to_csv(f, mode="a", index=False, header=not f.exists())
    for k, v in r.items():
        print(f"{k}: {v}")
    sys.exit(0)
