"""ECO exchange access. Hosts: PUBLIC market data (fapi.binance.com, read only), DEMO (demo-fapi.binance.com, keys from env
BINANCE_FUT_DEMO_KEY / _SECRET set by the user). There is NO mainnet order path. SimExchange = replay (laptop, local files)."""
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

PUBLIC = "https://fapi.binance.com"
DEMO = "https://demo-fapi.binance.com"
ALLOWED_ORDER_HOSTS = (DEMO,)
FAR_DELIVERY_MS = 4102444800000                 # 2100-01-01: a TRADING perp with an earlier deliveryDate has a delisting announced


def http(base, method, path, params=None, key="", secret=b"", signed=False, timeout=30):
    params = dict(params or {})
    if signed:
        assert base in ALLOWED_ORDER_HOSTS, "signed calls only to the demo host"
        assert key and secret, "demo keys missing: the user sets BINANCE_FUT_DEMO_KEY / _SECRET"
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        q = urllib.parse.urlencode(params)
        q += "&signature=" + hmac.new(secret, q.encode(), hashlib.sha256).hexdigest()
    else:
        q = urllib.parse.urlencode(params)
    req = urllib.request.Request(base + path + ("?" + q if q else ""), method=method,
                                 headers={"X-MBX-APIKEY": key, "User-Agent": "eco"} if signed else {"User-Agent": "eco"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return {"_error": True, "status": e.code, **json.loads(body)}
        except Exception:                                                  # noqa: BLE001
            return {"_error": True, "status": e.code, "msg": body[:300]}


def parse_filters(info):
    out = {}
    for s in info["symbols"]:
        if s.get("contractType") != "PERPETUAL" or s.get("status") != "TRADING" or s.get("quoteAsset") != "USDT":
            continue
        f = {x["filterType"]: x for x in s["filters"]}
        out[s["symbol"]] = dict(step=float(f["MARKET_LOT_SIZE"]["stepSize"]), min_qty=float(f["MARKET_LOT_SIZE"]["minQty"]),
                                max_qty=float(f["MARKET_LOT_SIZE"]["maxQty"]), tick=float(f["PRICE_FILTER"]["tickSize"]),
                                min_notional=float(f.get("MIN_NOTIONAL", {}).get("notional", 0)),
                                delivery_ms=int(s.get("deliveryDate") or 4133404800000))     # amendment 2 §3
    return out


def resolve_perps(coins, filters, n1_names):
    """spot-name coin -> (perp, scale): N1 config map first, else SYM / 1000SYM / 1000000SYM among TRADING perps."""
    out = {}
    for s in sorted(set(coins)):
        p = n1_names.get(s)
        if p not in filters:
            base = s[:-4]
            p = next((c for c in (s, f"1000{base}USDT", f"1000000{base}USDT") if c in filters), None)
        if p is None:
            out[s] = None
            continue
        out[s] = (p, 1e6 if p.startswith("1000000") and not s.startswith("1000000") else 1e3 if p.startswith("1000") and not s.startswith("1000") else 1.0)
    return out


class Public:
    """public market data from one host (mainnet public for plan mode, demo host for demo mode)."""

    def __init__(self, base=PUBLIC):
        self.base = base
        self.errors = []

    def get(self, path, **p):
        for k in range(3):
            r = http(self.base, "GET", path, p)
            if not (isinstance(r, dict) and r.get("_error")):
                return r
            if r.get("status") in (400, 404):
                break
            time.sleep(2 * (k + 1))
        self.errors.append(f"{path} {p.get('symbol', '')}: {r}")
        return None

    def exchange_info(self):
        return self.get("/fapi/v1/exchangeInfo")

    def prices(self, symbols):
        """mark price per perp (one call)."""
        r = self.get("/fapi/v1/premiumIndex") or []
        m = {x["symbol"]: float(x["markPrice"]) for x in r}
        return {s: m[s] for s in symbols if s in m and m[s] > 0}

    def high_since(self, symbols, since_ms, now_ms):
        """max high of CLOSED 1h bars with open time >= since (contract price)."""
        out = {}
        for s in symbols:
            k = self.get("/fapi/v1/klines", symbol=s, interval="1h", startTime=int(since_ms), limit=100)
            if not k:
                continue
            hs = [float(x[2]) for x in k if int(x[6]) < now_ms]
            if hs:
                out[s] = max(hs)
        return out


class Demo(Public):
    """demo account (orders allowed only here)."""

    def __init__(self):
        super().__init__(DEMO)
        self.key = os.getenv("BINANCE_FUT_DEMO_KEY", "")
        self.secret = os.getenv("BINANCE_FUT_DEMO_SECRET", "").encode()

    def signed(self, method, path, **p):
        return http(DEMO, method, path, p, self.key, self.secret, signed=True)

    def one_way(self):
        r = self.signed("GET", "/fapi/v1/positionSide/dual")
        assert not r.get("_error"), r
        return r["dualSidePosition"] is False

    def wallet_equity(self):
        r = self.signed("GET", "/fapi/v3/account")
        assert not r.get("_error"), r
        return float(r["totalMarginBalance"])

    def positions(self):
        r = self.signed("GET", "/fapi/v3/positionRisk")
        assert isinstance(r, list), r
        return {p["symbol"]: float(p["positionAmt"]) for p in r if float(p["positionAmt"]) != 0}

    def market(self, sym, qty, reduce_only, cid):
        p = dict(symbol=sym, side="BUY" if qty > 0 else "SELL", type="MARKET", quantity=fmt(abs(qty)), newClientOrderId=cid,
                 newOrderRespType="RESULT")
        if reduce_only:
            p["reduceOnly"] = "true"
        return self.signed("POST", "/fapi/v1/order", **p)

    def query(self, sym, cid):
        return self.signed("GET", "/fapi/v1/order", symbol=sym, origClientOrderId=cid)

    def confirmed_fill(self, r, sym, cid, tries=3, wait=1.0):
        """amendment 2 §4: (signed-abs qty, avg price) only for FILLED / PARTIALLY_FILLED with qty > 0 and price > 0; the order is
        queried up to `tries` times; None = not confirmed (the caller keeps the journal entry)."""
        for k in range(tries + 1):
            if not r.get("_error") and r.get("status") in ("FILLED", "PARTIALLY_FILLED") and float(r.get("executedQty") or 0) > 0 \
                    and float(r.get("avgPrice") or 0) > 0:
                return float(r["executedQty"]), float(r["avgPrice"])
            if k == tries:
                return None
            time.sleep(wait)
            r = self.query(sym, cid)

    def algo_fill(self, algo_id):
        """Query Algo Order: (status, actualQty or None, actualPrice or None)."""
        q = self.signed("GET", "/fapi/v1/algoOrder", algoId=algo_id)
        if q.get("_error"):
            return "MISSING", None, None
        aq, ap = float(q.get("actualQty") or 0), float(q.get("actualPrice") or 0)
        return q.get("algoStatus") or "MISSING", (aq if aq > 0 else None), (ap if ap > 0 else None)

    def open_algo(self):
        r = self.signed("GET", "/fapi/v1/openAlgoOrders")
        assert isinstance(r, list), r
        return r

    def funding_income(self, since_ms):
        r = self.signed("GET", "/fapi/v1/income", incomeType="FUNDING_FEE", startTime=int(since_ms), limit=1000)
        return r if isinstance(r, list) else []

    def prepare_symbol(self, sym, notes):
        """fresh symbol: CROSSED margin, leverage 2 (protocol §3). -4046 = already crossed; an open ISOLATED position stays."""
        r = self.signed("POST", "/fapi/v1/marginType", symbol=sym, marginType="CROSSED")
        if r.get("_error") and r.get("code") not in (-4046,):
            notes.append(f"{sym} marginType: {r.get('code')} {r.get('msg')}")
        r = self.signed("POST", "/fapi/v1/leverage", symbol=sym, leverage=2)
        if r.get("_error"):
            notes.append(f"{sym} leverage: {r.get('code')} {r.get('msg')}")


def fmt(x):
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return s if s else "0"


# ======================================================================= replay (laptop)
class SimExchange:
    """fills at the OPEN of the 1h bar after the cycle (local perp 1h files, contract prices); taker fee; real funding;
    tracks its own positions and cash, independently of the attribution ledger (for gate R1)."""

    def __init__(self, perp_dir, fee=0.00054):
        self.dir, self.fee = Path(perp_dir), fee
        self.bars, self.fund = {}, {}
        self.pos, self.cash, self.fills, self.errors = {}, 0.0, [], []

    def _bars(self, p, coin):
        if p not in self.bars:
            f = self.dir / f"{coin}_perp_1h.csv.gz"
            self.bars[p] = pd.read_csv(f, parse_dates=["timestamp"]).set_index("timestamp")[["open", "high", "low", "close"]] if f.exists() else None
            g = self.dir / f"{coin}_funding.csv"
            self.fund[p] = pd.read_csv(g, parse_dates=["time"]).sort_values("time") if g.exists() else None
        return self.bars[p]

    def bar(self, p, coin, t):
        b = self._bars(p, coin)
        if b is None or t not in b.index:
            return None
        return b.loc[t]

    def market(self, p, coin, qty, t_fill):
        b = self.bar(p, coin, t_fill)
        if b is None:
            self.errors.append(f"{p}: no bar at {t_fill}")
            return None
        px = float(b.open)
        self.pos[p] = self.pos.get(p, 0.0) + qty
        if abs(self.pos[p]) < 1e-12:
            self.pos.pop(p)
        self.cash -= qty * px + self.fee * abs(qty) * px
        self.fills.append((str(t_fill), p, qty, px))
        return px

    def funding_between(self, p, coin, t0, t1):
        """funding events in (t0, t1]: list of (time, rate, price at the event hour open)."""
        self._bars(p, coin)
        f = self.fund.get(p)
        if f is None:
            return []
        ev = f[(f.time > t0) & (f.time <= t1)]
        out = []
        for r in ev.itertuples():
            b = self.bar(p, coin, r.time.floor("h"))
            if b is not None:
                out.append((r.time, float(r.funding_rate), float(b.open)))
        return out

    def equity(self, price):
        return self.cash + sum(q * price[p] for p, q in self.pos.items() if p in price)
