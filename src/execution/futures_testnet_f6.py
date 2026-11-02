"""
F6 futures TESTNET / DEMO executor for the long-short SHORT book (protocol: logs/futures_testnet_f6/F6_PROTOCOL_PREREGISTERED.md).
Operations test only. There is deliberately NO mainnet mode: only the two official non-money hosts below are accepted.
Usage:
  python futures_testnet_f6.py --mode plan                     (no keys, NO orders: prints what it would send)
  python futures_testnet_f6.py --mode testnet|demo             (keys from env, set by the user)
  python futures_testnet_f6.py --mode testnet|demo --drill-kill (kill-switch drill: cover all, cancel all algo orders)
"""
import os
import sys
import hmac
import json
import time
import math
import argparse
import hashlib
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from config import LOGS_DIR

BASES = {"testnet": "https://testnet.binancefuture.com", "demo": "https://demo-fapi.binance.com"}   # NO mainnet
ENV = {"testnet": "BINANCE_FUT_TESTNET", "demo": "BINANCE_FUT_DEMO"}
OUT = LOGS_DIR / "futures_testnet_f6"
F4 = LOGS_DIR / "forward_ls_f4"
PROTO = OUT / "F6_PROTOCOL_PREREGISTERED.md"
STOP_X, PER_SHORT, K1 = 1.50, 0.10, 0.35
COOLDOWN_DAYS = 30                                   # F7 rule, applied to stops that fired on the exchange
MAX_ORDERS, MAX_ORDER_FRAC, MAX_SHORTS = 40, 0.25, 15
CAP_SLEEVE = float(os.getenv("F6_CAP_SLEEVE", "1000"))
SLEEVES = ("D1", "H4", "H1")


def log(msg):
    OUT.mkdir(parents=True, exist_ok=True)
    line = f"[{pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}"
    with open(OUT / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Client:
    def __init__(self, mode):
        assert mode in BASES, "only testnet / demo exist"
        self.base = BASES[mode]
        assert self.base in ("https://testnet.binancefuture.com", "https://demo-fapi.binance.com"), "refusing a non-test host"
        self.key = os.getenv(ENV[mode] + "_KEY", "")
        self.secret = os.getenv(ENV[mode] + "_SECRET", "").encode()

    def _call(self, method, path, params=None, signed=False):
        params = dict(params or {})
        if signed:
            assert self.key and self.secret, f"keys missing: the user must set the environment variables for this mode"
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            q = urllib.parse.urlencode(params)
            q += "&signature=" + hmac.new(self.secret, q.encode(), hashlib.sha256).hexdigest()
        else:
            q = urllib.parse.urlencode(params)
        url = self.base + path + ("?" + q if q else "")
        assert url.startswith(self.base) and self.base in BASES.values()
        req = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": self.key} if signed else {})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                return {"_error": True, "status": e.code, **json.loads(body)}
            except Exception:
                return {"_error": True, "status": e.code, "msg": body[:300]}

    def get(self, path, signed=False, **p):
        return self._call("GET", path, p, signed)

    def post(self, path, **p):
        return self._call("POST", path, p, True)

    def delete(self, path, **p):
        return self._call("DELETE", path, p, True)


def filters(c):
    info = c.get("/fapi/v1/exchangeInfo")
    out = {}
    for s in info["symbols"]:
        if s.get("contractType") != "PERPETUAL" or s.get("status") != "TRADING":
            continue
        f = {x["filterType"]: x for x in s["filters"]}
        out[s["symbol"]] = dict(step=float(f["MARKET_LOT_SIZE"]["stepSize"]), min_qty=float(f["MARKET_LOT_SIZE"]["minQty"]),
                                max_qty=float(f["MARKET_LOT_SIZE"]["maxQty"]), tick=float(f["PRICE_FILTER"]["tickSize"]),
                                min_notional=float(f.get("MIN_NOTIONAL", {}).get("notional", 0)))
    return out


def floor_step(x, step):
    return math.floor(x / step + 1e-9) * step


def round_tick(x, tick):
    return round(round(x / tick) * tick, 10)


def fmt(x):
    return f"{x:.10f}".rstrip("0").rstrip(".")


def perp_symbol(sym):
    """research symbol -> (perp symbol, scale) via the F4 resolver (F1 list, else exchangeInfo)."""
    import forward_ls_f4 as Q
    return Q.perp_names([sym]).get(sym)


def load_decision():
    """The latest F4 day with an orders file; its hash must match the F4 ledger line."""
    L = pd.read_csv(F4 / "ledger.csv")
    r = L.iloc[-1]
    f = F4 / "paper" / f"orders_{r['asof']}.json"
    assert sha(f) == r.orders_sha256, "F4 orders file != F4 ledger"
    return r["asof"], json.loads(f.read_text()).get("LS_RS", {}), r   # PAPER_START day: no decision yet -> {}


def targets(dec):
    """per sleeve: {symbol: dict(paper_equity)} = paper open shorts - covers + new shorts."""
    out = {}
    for k in SLEEVES:
        d = dec.get(k)
        if not d:
            out[k] = {}
            continue
        keep = [s for s in d["shorts"] if s not in d["cover"]]
        out[k] = {s: d["equity_close"] for s in keep + list(d["short"])}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["plan", "testnet", "demo"], required=True)
    ap.add_argument("--drill-kill", action="store_true")
    a = ap.parse_args()
    assert sha(PROTO) == (OUT / "F6_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    env = "testnet" if a.mode == "plan" else a.mode
    c = Client(env)
    state_f = OUT / f"state_{env}.json"
    st = json.loads(state_f.read_text()) if state_f.exists() else dict(sleeves={k: {} for k in SLEEVES}, peak=None, runs=0)
    flt = filters(c)
    acts, notes = [], []
    live = a.mode != "plan"
    if live and (OUT / "HALT").exists() and not a.drill_kill:
        log("HALT file present -> refusing to trade (user must review and delete HALT)")
        return

    if live:
        dual = c.get("/fapi/v1/positionSide/dual", signed=True)
        assert not dual.get("_error"), dual
        assert dual["dualSidePosition"] is False, "account is in HEDGE mode: user must switch to one-way (code does not change settings)"
        acct = c.get("/fapi/v3/account", signed=True)
        assert not acct.get("_error"), acct
        equity = float(acct["totalMarginBalance"])
        st["peak"] = max(st["peak"] or equity, equity)
        kill = a.drill_kill or equity <= (1 - K1) * st["peak"]
        if kill:
            log(f"KILL ({'drill' if a.drill_kill else 'K1'}): equity {equity} peak {st['peak']}")
            for p in c.get("/fapi/v3/positionRisk", signed=True):
                amt = float(p["positionAmt"])
                if amt != 0:
                    r = c.post("/fapi/v1/order", symbol=p["symbol"], side="BUY" if amt < 0 else "SELL", type="MARKET",
                               quantity=fmt(abs(amt)), reduceOnly="true")
                    acts.append(dict(action="kill_close", symbol=p["symbol"], qty=abs(amt), resp=r))
                r = c.delete("/fapi/v1/algoOpenOrders", symbol=p["symbol"])
                acts.append(dict(action="kill_cancel_algo", symbol=p["symbol"], resp=r))
            st["sleeves"] = {k: {} for k in SLEEVES}
            if not a.drill_kill:
                (OUT / "HALT").write_text(f"K1 fired {pd.Timestamp.now('UTC')}: equity {equity} <= 65% of peak {st['peak']}\n")
            finish(c, a, st, state_f, acts, notes, None, live)
            return

        # 1. sync: stops that are no longer open
        open_algo = c.get("/fapi/v1/openAlgoOrders", signed=True)
        assert not isinstance(open_algo, dict) or not open_algo.get("_error"), open_algo
        open_ids = {int(o["algoId"]) for o in open_algo}
        for k in SLEEVES:
            for s, pos in list(st["sleeves"][k].items()):
                if pos.get("algoId") and int(pos["algoId"]) in open_ids:
                    continue
                q = c.get("/fapi/v1/algoOrder", signed=True, algoId=pos["algoId"]) if pos.get("algoId") else {}
                status = q.get("algoStatus")
                if status in ("TRIGGERED", "FINISHED"):                                  # the stop fired: the sleeve short is gone
                    notes.append(f"{k} {s}: stop algo {pos['algoId']} {status} -> closed by the stop")
                    acts.append(dict(action="stop_fired", sleeve=k, symbol=s, qty=pos["qty"], algo=q))
                    st["sleeves"][k].pop(s)
                    st.setdefault("cooldown", {k_: {} for k_ in SLEEVES})[k][s] = str(pd.Timestamp.now("UTC").date())   # F7: 30-day cooldown
                    continue
                # no live stop (CANCELED / EXPIRED / not found / never placed): the short must NOT stay unprotected
                stop = round_tick(pos["fill"] * STOP_X, flt[pos["perp"]]["tick"])
                rs = c.post("/fapi/v1/algoOrder", algoType="CONDITIONAL", symbol=pos["perp"], side="BUY", type="STOP_MARKET",
                            quantity=fmt(pos["qty"]), triggerPrice=fmt(stop), workingType="CONTRACT_PRICE", reduceOnly="true")
                notes.append(f"{k} {s}: stop algo {pos.get('algoId')} status {status} -> stop re-placed: {rs.get('algoId') or rs}")
                acts.append(dict(action="stop_replaced", sleeve=k, symbol=s, qty=pos["qty"], stop=stop, stop_resp=rs))
                if not rs.get("_error"):
                    pos["algoId"], pos["stop"] = rs.get("algoId"), stop

    asof, dec, f4line = load_decision()
    tg = targets(dec)
    n_orders = 0
    for k in SLEEVES:
        held = st["sleeves"][k]
        for s in [s for s in held if s not in tg[k]]:                                  # close
            pos = held[s]
            if live:
                r = c.post("/fapi/v1/order", symbol=pos["perp"], side="BUY", type="MARKET", quantity=fmt(pos["qty"]), reduceOnly="true")
                rc = c.delete("/fapi/v1/algoOrder", algoId=pos["algoId"]) if pos.get("algoId") else None
                acts.append(dict(action="cover", sleeve=k, symbol=s, qty=pos["qty"], resp=r, cancel_stop=rc))
                if not r.get("_error"):
                    del held[s]
            else:
                acts.append(dict(action="PLAN cover", sleeve=k, symbol=s, qty=pos["qty"]))
            n_orders += 1
        cd = st.setdefault("cooldown", {k_: {} for k_ in SLEEVES}).setdefault(k, {})
        for s, eq in tg[k].items():                                                    # open
            if s in held:
                continue
            if s in cd and pd.Timestamp.now("UTC").tz_localize(None) < pd.Timestamp(cd[s]) + pd.Timedelta(days=COOLDOWN_DAYS):
                acts.append(dict(action="skip", sleeve=k, symbol=s, reason=f"cooldown: exchange stop fired {cd[s]} (F7 30-day rule)"))
                continue
            nm = perp_symbol(s)
            if nm is None or nm[0] not in flt:
                acts.append(dict(action="skip", sleeve=k, symbol=s, reason="no perpetual on this environment"))
                continue
            perp, scale = nm
            fl = flt[perp]
            px = float(c.get("/fapi/v1/ticker/price", symbol=perp)["price"])
            notional = min(PER_SHORT * CAP_SLEEVE * eq / 10_000, MAX_ORDER_FRAC * CAP_SLEEVE)
            qty = floor_step(notional / px, fl["step"])
            if qty < fl["min_qty"] or qty * px < fl["min_notional"]:
                acts.append(dict(action="skip", sleeve=k, symbol=s, reason=f"below exchange minimum (qty {qty}, notional {qty * px:.2f})"))
                continue
            if n_orders >= MAX_ORDERS or sum(len(v) for v in st["sleeves"].values()) >= MAX_SHORTS:
                acts.append(dict(action="skip", sleeve=k, symbol=s, reason="order / position limit"))
                continue
            if not live:
                acts.append(dict(action="PLAN short", sleeve=k, symbol=s, perp=perp, qty=qty, ref_price=px,
                                 stop=round_tick(px * STOP_X, fl["tick"])))
                n_orders += 1
                continue
            for path, prm in (("/fapi/v1/marginType", dict(marginType="ISOLATED")), ("/fapi/v1/leverage", dict(leverage=1))):
                r = c.post(path, symbol=perp, **prm)
                if r.get("_error") and r.get("code") != -4046:                         # -4046: already isolated
                    notes.append(f"{perp} {path}: {r}")
            r = c.post("/fapi/v1/order", symbol=perp, side="SELL", type="MARKET", quantity=fmt(qty), newOrderRespType="RESULT")
            n_orders += 1
            if r.get("_error"):
                acts.append(dict(action="short_rejected", sleeve=k, symbol=s, resp=r))
                continue
            fill = float(r.get("avgPrice") or px)
            stop = round_tick(fill * STOP_X, fl["tick"])
            rs = c.post("/fapi/v1/algoOrder", algoType="CONDITIONAL", symbol=perp, side="BUY", type="STOP_MARKET",
                        quantity=fmt(qty), triggerPrice=fmt(stop), workingType="CONTRACT_PRICE", reduceOnly="true")
            n_orders += 1
            held[s] = dict(perp=perp, qty=qty, fill=fill, stop=stop, algoId=rs.get("algoId"), opened=str(pd.Timestamp.now("UTC")),
                           decision_asof=asof)
            acts.append(dict(action="short", sleeve=k, symbol=s, perp=perp, qty=qty, fill=fill, stop=stop, resp=r, stop_resp=rs))
            if rs.get("_error"):
                notes.append(f"{k} {s}: STOP NOT PLACED ({rs}) -> the next run re-places it; check now")
    finish(c, a, st, state_f, acts, notes, asof, live, f4line)


def finish(c, a, st, state_f, acts, notes, asof, live, f4line=None):
    recon = None
    if live:
        pr = {p["symbol"]: float(p["positionAmt"]) for p in c.get("/fapi/v3/positionRisk", signed=True)}
        want = {}
        for k in SLEEVES:
            for s, pos in st["sleeves"][k].items():
                want[pos["perp"]] = want.get(pos["perp"], 0.0) - pos["qty"]
        recon = {s: dict(exchange=pr.get(s, 0.0), state=v) for s, v in want.items()}
        extra = {s: v for s, v in pr.items() if v != 0 and s not in want}
        recon["_extra_exchange_positions"] = extra
        st["runs"] = st.get("runs", 0) + 1
        state_f.write_text(json.dumps(st, indent=1, default=str))
    rec = dict(time_utc=str(pd.Timestamp.now("UTC")), mode=a.mode, drill_kill=a.drill_kill, asof=asof,
               f4_line_sha256=(f4line.line_sha256 if f4line is not None else None), actions=acts, notes=notes, reconcile=recon,
               code_sha256=sha(__file__), protocol_sha256=sha(PROTO))
    f = OUT / ("plan" if not live else "runs") / f"{pd.Timestamp.now('UTC').strftime('%Y%m%dT%H%M%S')}_{a.mode}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rec, indent=1, default=str))
    log(f"{a.mode} run done: {len(acts)} actions, notes {len(notes)}, record {f.name}")


if __name__ == "__main__":
    main()
