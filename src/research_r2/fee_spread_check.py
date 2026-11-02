"""
R2 fee + spread check (2026-10-17). NO ORDERS.
1) Futures commission: signed GET /fapi/v1/commissionRate on the DEMO host (read-only; keys from env, never printed).
2) Live MAINNET public order books, spot (/api/v3/depth) and USDT-M perps (/fapi/v1/depth), N rounds:
   half-spread and walk-the-book cost (bps vs mid) for buy and sell of $333 / $1,000 / $3,333 / $10,000.
Raw JSON is gzip-saved with SHA256 in logs/research_r2/fee_spread_check/.
Usage: python fee_spread_check.py <rounds> <seconds_between>
"""
import os
import sys
import json
import gzip
import time
import hmac
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
import datetime as dt

OUT = Path(__file__).resolve().parents[2] / "logs" / "research_r2" / "fee_spread_check"
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT",
         "TRXUSDT", "LTCUSDT", "BCHUSDT", "NEARUSDT", "UNIUSDT", "HBARUSDT", "XLMUSDT", "FETUSDT", "WLDUSDT", "ONDOUSDT", "QNTUSDT"]
NOTIONALS = [333, 1000, 3333, 10000]


def get(url, headers=None):
    for i in range(5):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except Exception as e:
            if i == 4:
                raise
            time.sleep(2 + 2 * i)


def commission():
    key, sec = os.environ.get("BINANCE_FUT_DEMO_KEY", ""), os.environ.get("BINANCE_FUT_DEMO_SECRET", "")
    rows = []
    for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"):
        q = urllib.parse.urlencode(dict(symbol=s, timestamp=int(time.time() * 1000), recvWindow=10000))
        sig = hmac.new(sec.encode(), q.encode(), hashlib.sha256).hexdigest()
        try:
            d = json.loads(get(f"https://demo-fapi.binance.com/fapi/v1/commissionRate?{q}&signature={sig}", {"X-MBX-APIKEY": key}))
        except Exception as e:
            d = {"symbol": s, "error": str(e)[:200]}
        rows.append(d)
    return rows


def walk(levels, usd):
    """average fill price for a market order of `usd` notional walking the levels [(px, qty)]."""
    left, cost_q, got = usd, 0.0, 0.0
    for px, qty in levels:
        take = min(left, px * qty)
        got += take / px
        left -= take
        if left <= 1e-9:
            return usd / got
    return float("nan")


def one(venue, sym, tag):
    url = (f"https://api.binance.com/api/v3/depth?symbol={sym}&limit=1000" if venue == "spot"
           else f"https://fapi.binance.com/fapi/v1/depth?symbol={sym}&limit=1000")
    raw = get(url)
    f = OUT / "raw" / f"{tag}_{venue}_{sym}.json.gz"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(gzip.compress(raw))
    d = json.loads(raw)
    bids = [(float(p), float(q)) for p, q in d["bids"]]
    asks = [(float(p), float(q)) for p, q in d["asks"]]
    mid = (bids[0][0] + asks[0][0]) / 2
    row = dict(t_utc=tag, venue=venue, symbol=sym, mid=mid, half_spread_bps=(asks[0][0] - mid) / mid * 1e4,
               raw_file=f.name, raw_sha256=hashlib.sha256(raw).hexdigest())
    for n in NOTIONALS:
        row[f"buy_bps_{n}"] = (walk(asks, n) / mid - 1) * 1e4
        sp = walk(bids, n)
        row[f"sell_bps_{n}"] = (1 - sp / mid) * 1e4 if sp == sp else float("nan")
    return row


def main(rounds, gap):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "commission_demo.json").write_text(json.dumps(commission(), indent=1))
    rows = []
    for r in range(rounds):
        tag = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for v in ("spot", "perp"):
            for s in COINS:
                try:
                    rows.append(one(v, s, tag))
                except Exception as e:
                    rows.append(dict(t_utc=tag, venue=v, symbol=s, error=str(e)[:200]))
        print(f"round {r + 1}/{rounds} {tag} done", flush=True)
        if r < rounds - 1:
            time.sleep(gap)
    import csv
    keys = sorted({k for x in rows for k in x}, key=lambda k: (k not in ("t_utc", "venue", "symbol"), k))
    with open(OUT / "books.csv", "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        if fh.tell() == 0:
            w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
