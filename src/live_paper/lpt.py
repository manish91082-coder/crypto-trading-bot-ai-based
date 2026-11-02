"""LPT-1 (live paper trading desk, started 2026-10-29): intraday paper trading on LIVE market data with a 10,000 USDT paper account.
Protocol: logs/live_paper_lpt1_2026_10_29/LPT1_PROTOCOL_PREREGISTERED.md. NOTHING here sends an order to any exchange.
Data (read-only public endpoints reachable from this laptop; api.binance.com / fapi.binance.com time out here):
  spot     Binance spot via the official public mirror https://data-api.binance.vision (klines, bookTicker, depth, 24h ticker)
  futures  Bybit USDT linear perpetuals https://api.bybit.com (proxy for Binance USD-M: price, book, funding, OI, long/short)
Fills: market orders walk the LIVE order book (depth) at the moment of the order; stops / targets / time exits are filled by the
watcher at the live best bid / ask when it sees the level crossed (a stop is never filled at a better price than the book had).
Fees: deploy/fees.json, BNB taker (spot 0.075 %, futures 0.036 %) on every fill (book-walk already contains the impact).
Hard risk rules (enforced in code, not by memory): see RISK below.
Logs (append-only, each line carries the sha256 of the previous line = tamper-evident chain):
  decisions.jsonl  every decision BEFORE its outcome, with the snapshot sha and the reasoning
  fills.jsonl      every fill with the book it was filled against
  equity.csv       mark-to-market every minute
Usage:
  python src/live_paper/lpt.py snapshot [--top 15]              -> market snapshot (saved, sha printed) + compact table
  python src/live_paper/lpt.py order --mkt futures --sym SOLUSDT --side long --stop 150.2 --target 158 --risk 0.01 \
         --reason "..." --snap <sha>                            -> risk check, live book-walk fill, logged
  python src/live_paper/lpt.py close --id <pos id> --reason "..."  -> close at the live book
  python src/live_paper/lpt.py status                            -> account, open positions, today vs the 10 % goal
  python src/live_paper/lpt.py watch                             -> the watcher loop (background)"""
import argparse
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

PROJ = Path(__file__).resolve().parents[2]
LOG = PROJ / "logs/live_paper_lpt1_2026_10_29"
SNAP = LOG / "snapshots"
STATE = LOG / "state.json"
LOCK = LOG / "state.lock"
FEES = json.loads((PROJ / "deploy/fees.json").read_text(encoding="utf-8"))
FEE = {"spot": FEES["spot"]["bnb_taker"], "futures": FEES["futures_usdm"]["bnb_taker"]}
START_EQUITY = 10_000.0
RISK = dict(max_risk_per_trade=0.01, daily_loss_limit=0.03, max_open=3, max_gross_leverage=3.0, max_notional_share_spot=1.0,
            min_reward_risk=1.5, flat_by_utc="23:55", stop_required=True)
BIN = "https://data-api.binance.vision/api/v3"
BYB = "https://api.bybit.com/v5/market"
STABLE = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "BUSD", "EUR", "TRY", "BRL", "USD1", "XUSD", "RLUSD", "BFUSD", "USDE", "PAXG", "WBTC", "WBETH",
          "BNSOL", "AEUR", "EURI", "PYUSD", "U"}


# ------------------------------------------------------------------ helpers
def now_ms():
    return int(time.time() * 1000)


def iso(ms=None):
    return datetime.fromtimestamp((ms or now_ms()) / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


def get(url, params=None, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=8)
            r.raise_for_status()
            return r.json()
        except Exception as e:                                               # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(1 + i)


def append_chain(path, rec):
    """append one JSON line whose 'prev' is the sha256 of the previous line (tamper-evident)"""
    path = Path(path)
    prev = "GENESIS"
    if path.exists() and path.stat().st_size:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 65536))
            last = f.read().splitlines()[-1]
        prev = hashlib.sha256(last).hexdigest()
    rec = dict(rec, prev=prev)
    line = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return hashlib.sha256(line.encode()).hexdigest()


class Lock:
    def __enter__(self):
        t0 = time.time()
        while True:
            try:
                self.fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.time() - t0 > 30:
                    raise RuntimeError("state lock held > 30 s")
                time.sleep(0.05)

    def __exit__(self, *a):
        os.close(self.fd)
        os.remove(LOCK)


def load_state():
    if not STATE.exists():
        return dict(cash=START_EQUITY, positions={}, next_id=1, day=None, day_start_equity=START_EQUITY, halted_day=None, realized=0.0,
                    fees=0.0, created=iso())
    return json.loads(STATE.read_text())


def save_state(s):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1))
    os.replace(tmp, STATE)


# ------------------------------------------------------------------ live market data
def book(mkt, sym, depth=50):
    """live order book: (bids, asks) as [[price, qty], ...] best first, and the exchange time"""
    if mkt == "spot":
        d = get(f"{BIN}/depth", dict(symbol=sym, limit=min(depth, 100)))
        return [[float(p), float(q)] for p, q in d["bids"]], [[float(p), float(q)] for p, q in d["asks"]], now_ms()
    d = get(f"{BYB}/orderbook", dict(category="linear", symbol=sym, limit=min(depth, 200)))["result"]
    return [[float(p), float(q)] for p, q in d["b"]], [[float(p), float(q)] for p, q in d["a"]], int(d["ts"])


def top(mkt, sym):
    if mkt == "spot":
        d = get(f"{BIN}/ticker/bookTicker", dict(symbol=sym))
        return float(d["bidPrice"]), float(d["askPrice"]), now_ms()
    d = get(f"{BYB}/tickers", dict(category="linear", symbol=sym))["result"]["list"][0]
    return float(d["bid1Price"]), float(d["ask1Price"]), now_ms()


def walk(levels, qty):
    """average fill price of a market order of qty against the levels (best first); None if the book is too thin"""
    left, cost = qty, 0.0
    for p, q in levels:
        take = min(left, q)
        cost += take * p
        left -= take
        if left <= 1e-12:
            return cost / qty
    return None


def klines(mkt, sym, interval, limit):
    if mkt == "spot":
        d = get(f"{BIN}/klines", dict(symbol=sym, interval=interval, limit=limit))
        k = pd.DataFrame(d, columns=["t", "o", "h", "l", "c", "v", "T", "qv", "n", "tbv", "tbq", "x"]).iloc[:, :11]
        for col in ["o", "h", "l", "c", "v", "qv", "tbv", "tbq"]:
            k[col] = k[col].astype(float)
        k["t"] = k.t.astype("int64")
        return k
    iv = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}[interval]
    d = get(f"{BYB}/kline", dict(category="linear", symbol=sym, interval=iv, limit=limit))["result"]["list"][::-1]
    k = pd.DataFrame(d, columns=["t", "o", "h", "l", "c", "v", "qv"])
    for col in ["o", "h", "l", "c", "v", "qv"]:
        k[col] = k[col].astype(float)
    k["t"] = k.t.astype("int64")
    return k


# ------------------------------------------------------------------ analyst: market snapshot
def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    return float(100 - 100 / (1 + up.iloc[-1] / max(dn.iloc[-1], 1e-12)))


def atr_pct(k, n=14):
    pc = k.c.shift(1)
    tr = pd.concat([k.h - k.l, (k.h - pc).abs(), (k.l - pc).abs()], axis=1).max(axis=1)
    return float(tr.ewm(alpha=1 / n, adjust=False).mean().iloc[-1] / k.c.iloc[-1])


def features(sym):
    f = dict(sym=sym)
    m5 = klines("spot", sym, "5m", 600)
    h1 = klines("spot", sym, "1h", 300)
    d1 = klines("spot", sym, "1d", 60)
    c5, c1 = m5.c.values, h1.c.values
    p = float(c5[-1])
    f["price"] = p
    for lab, n in (("r15m", 3), ("r1h", 12), ("r4h", 48), ("r24h", 288)):
        f[lab] = p / c5[-1 - n] - 1
    f["atr5m"], f["atr1h"], f["atr1d"] = atr_pct(m5), atr_pct(h1), atr_pct(d1)
    t = now_ms()
    day0 = t // 86_400_000 * 86_400_000
    today = m5[m5.t >= day0]
    f["vwap_dist"] = p / ((today.qv.sum() / today.v.sum()) if today.v.sum() > 0 else p) - 1
    pdh, pdl = float(d1.h.iloc[-2]), float(d1.l.iloc[-2])
    f["pdh_dist"], f["pdl_dist"] = p / pdh - 1, p / pdl - 1
    f["day_open_dist"] = p / float(d1.o.iloc[-1]) - 1
    f["trend1h"] = int(np.sign(ema(c1, 20)[-1] - ema(c1, 50)[-1]))
    f["trend4h"] = int(np.sign(ema(c1, 80)[-1] - ema(c1, 200)[-1]))
    f["trend5m"] = int(np.sign(ema(c5, 20)[-1] - ema(c5, 50)[-1]))
    f["rsi5m"], f["rsi1h"] = rsi(c5[-200:]), rsi(c1[-200:])
    vol1h = m5.qv.values[-12:].sum()
    f["vol_ratio_1h"] = vol1h / (m5.qv.values[:-12].reshape(-1, 12).sum(1).mean() if len(m5) > 24 else vol1h)
    f["taker_buy_1h"] = m5.tbq.values[-12:].sum() / max(vol1h, 1e-9)
    b, a, _ = book("spot", sym, 50)
    f["spread_bps"] = (a[0][0] / b[0][0] - 1) * 1e4
    bq = sum(q * px for px, q in b if px >= b[0][0] * 0.995)
    aq = sum(q * px for px, q in a if px <= a[0][0] * 1.005)
    f["book_imb_50bp"] = (bq - aq) / max(bq + aq, 1e-9)
    try:
        tk = get(f"{BYB}/tickers", dict(category="linear", symbol=sym))["result"]["list"][0]
        f["fut_price"] = float(tk["lastPrice"])
        f["funding"] = float(tk["fundingRate"])
        f["basis_bps"] = (f["fut_price"] / p - 1) * 1e4
        oi = get(f"{BYB}/open-interest", dict(category="linear", symbol=sym, intervalTime="1h", limit=25))["result"]["list"]
        o = [float(x["openInterest"]) for x in oi]
        f["oi_chg_1h"], f["oi_chg_24h"] = o[0] / o[1] - 1, o[0] / o[-1] - 1
        ls = get(f"{BYB}/account-ratio", dict(category="linear", symbol=sym, period="1h", limit=1))["result"]["list"][0]
        f["ls_buy_ratio"] = float(ls["buyRatio"])
    except Exception:                                                        # noqa: BLE001  (no perp on Bybit -> spot only)
        f["fut_price"] = None
    return f


def universe(n):
    sys.path.insert(0, str(PROJ / "src/btc_alltf_r2"))
    from common import NOT_CRYPTO, LEV                                       # the project's stable / fiat / gold / stock-token list
    t = get(f"{BIN}/ticker/24hr")
    rows = [(x["symbol"], float(x["quoteVolume"])) for x in t if x["symbol"].endswith("USDT") and x["symbol"][:-4] not in STABLE
            and x["symbol"] not in NOT_CRYPTO and not x["symbol"].endswith(LEV)]
    rows.sort(key=lambda r: -r[1])
    return [s for s, _ in rows[:n]]


def cmd_snapshot(a):
    SNAP.mkdir(parents=True, exist_ok=True)
    t = now_ms()
    syms = universe(a.top)
    if "BTCUSDT" not in syms:
        syms = ["BTCUSDT"] + syms
    F = []
    for s in syms:
        try:
            F.append(features(s))
        except Exception as e:                                               # noqa: BLE001
            F.append(dict(sym=s, error=str(e)[:120]))
    D = pd.DataFrame(F)
    up = (D.r24h > 0).mean() if "r24h" in D else np.nan
    snap = dict(utc=iso(t), ms=t, breadth_up24h=float(up), rows=F)
    raw = json.dumps(snap, sort_keys=True, default=float).encode()
    h = hashlib.sha256(raw).hexdigest()
    (SNAP / f"{iso(t).replace(':', '').replace('-', '')}_{h[:12]}.json").write_bytes(raw)
    append_chain(LOG / "snapshots.jsonl", dict(utc=iso(t), sha=h, n=len(F)))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    cols = ["sym", "price", "r15m", "r1h", "r4h", "r24h", "atr5m", "atr1h", "vwap_dist", "pdh_dist", "pdl_dist", "trend5m", "trend1h", "trend4h",
            "rsi5m", "rsi1h", "vol_ratio_1h", "taker_buy_1h", "book_imb_50bp", "spread_bps", "funding", "oi_chg_1h", "oi_chg_24h", "ls_buy_ratio"]
    V = D[[c for c in cols if c in D]].copy()
    for c in ["r15m", "r1h", "r4h", "r24h", "atr5m", "atr1h", "vwap_dist", "pdh_dist", "pdl_dist", "oi_chg_1h", "oi_chg_24h"]:
        if c in V:
            V[c] = (100 * V[c]).round(2)
    if "funding" in V:
        V["funding"] = (100 * V.funding).round(4)
    print(f"SNAPSHOT {iso(t)} sha {h}  breadth(24h up) {100 * up:.0f}%   (returns / atr / distances in %)")
    print(V.round(3).to_string(index=False))


# ------------------------------------------------------------------ account
def mark(s):
    """mark-to-market equity with live best bid/ask (exit side)"""
    eq = s["cash"]
    for pid, p in s["positions"].items():
        b, a, _ = top(p["mkt"], p["sym"])
        px = b if p["side"] == "long" else a
        eq += p["margin"] + p["dir"] * p["qty"] * (px - p["entry"])
    return eq


def roll_day(s):
    d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if s.get("day") != d:
        eq = mark(s) if s["positions"] else s["cash"]
        if s.get("day"):
            append_chain(LOG / "daily.jsonl", dict(day=s["day"], start=s["day_start_equity"], end=eq, ret=eq / s["day_start_equity"] - 1,
                                                    goal10=s["day_start_equity"] * 1.10, goal15=s["day_start_equity"] * 1.15))
        s["day"], s["day_start_equity"], s["halted_day"] = d, eq, None
    return s


def fill_market(mkt, sym, side_open_or_close, dirn, qty):
    """market order against the live book: buy walks the asks, sell walks the bids. returns (avg price, book top, book time)"""
    b, a, ts = book(mkt, sym, 200)
    buying = (dirn > 0) == (side_open_or_close == "open")
    lv = a if buying else b
    px = walk(lv, qty)
    if px is None:
        raise RuntimeError("book too thin for this size")
    return px, (b[0][0], a[0][0]), ts


def cmd_order(a):
    with Lock():
        s = roll_day(load_state())
        eq = mark(s)
        dirn = 1 if a.side == "long" else -1
        why = []
        if a.mkt == "spot" and dirn < 0:
            why.append("spot is long only")
        if s.get("halted_day") == s["day"]:
            why.append("daily loss limit hit: no new trades today")
        if eq / s["day_start_equity"] - 1 <= -RISK["daily_loss_limit"]:
            why.append("daily loss limit reached")
        if len(s["positions"]) >= RISK["max_open"]:
            why.append("max open positions")
        if a.risk > RISK["max_risk_per_trade"] + 1e-12:
            why.append(f"risk {a.risk} > max {RISK['max_risk_per_trade']}")
        b0, a0, _ = top(a.mkt, a.sym)
        ref = a0 if dirn > 0 else b0
        if (a.stop - ref) * dirn >= 0:
            why.append("stop on the wrong side of the price")
        if a.target is not None and (a.target - ref) * dirn <= 0:
            why.append("target on the wrong side of the price")
        stop_dist = abs(ref - a.stop)
        rr = abs(a.target - ref) / stop_dist if a.target else None
        if rr is not None and rr < RISK["min_reward_risk"]:
            why.append(f"reward/risk {rr:.2f} < {RISK['min_reward_risk']}")
        qty = (a.risk * eq) / (stop_dist + ref * 2 * FEE[a.mkt]) if stop_dist > 0 else 0
        notional = qty * ref
        gross = sum(p["qty"] * p["entry"] for p in s["positions"].values()) + notional
        if a.mkt == "spot" and notional > s["cash"]:
            qty = s["cash"] * 0.999 / ref; notional = qty * ref
        if gross > RISK["max_gross_leverage"] * eq:
            why.append(f"gross exposure {gross / eq:.2f}x > {RISK['max_gross_leverage']}x")
        dec = dict(utc=iso(), kind="OPEN_REQUEST", mkt=a.mkt, sym=a.sym, side=a.side, stop=a.stop, target=a.target, risk=a.risk, qty=qty,
                   notional=notional, equity=eq, ref_book=[b0, a0], rr=rr, snapshot=a.snap, reason=a.reason, rejected=why)
        append_chain(LOG / "decisions.jsonl", dec)
        if why:
            print("REJECTED by risk manager:", "; ".join(why)); return
        px, tb, bts = fill_market(a.mkt, a.sym, "open", dirn, qty)
        fee = FEE[a.mkt] * qty * px
        margin = qty * px if a.mkt == "spot" else qty * px / RISK["max_gross_leverage"]
        s["cash"] -= margin + fee
        s["fees"] += fee
        pid = f"P{s['next_id']:04d}"
        s["next_id"] += 1
        s["positions"][pid] = dict(id=pid, mkt=a.mkt, sym=a.sym, side=a.side, dir=dirn, qty=qty, entry=px, margin=margin, stop=a.stop,
                                   target=a.target, opened=iso(), fee_open=fee, reason=a.reason, risk=a.risk, equity_at_open=eq)
        save_state(s)
        append_chain(LOG / "fills.jsonl", dict(utc=iso(), book_ms=bts, kind="OPEN", id=pid, mkt=a.mkt, sym=a.sym, side=a.side, qty=qty, px=px,
                                               book_top=tb, fee=fee, cash=s["cash"]))
        print(f"FILLED {pid} {a.mkt} {a.sym} {a.side} qty {qty:.6g} @ {px:.6g} (book {tb[0]}/{tb[1]}), notional {qty * px:,.2f}, "
              f"fee {fee:.2f}, stop {a.stop}, target {a.target}, R:R {rr}")


def close_pos(s, pid, reason, px_hint=None):
    p = s["positions"][pid]
    px, tb, bts = fill_market(p["mkt"], p["sym"], "close", p["dir"], p["qty"])
    fee = FEE[p["mkt"]] * p["qty"] * px
    pnl = p["dir"] * p["qty"] * (px - p["entry"])
    fund = 0.0
    if p["mkt"] == "futures":                                                # funding settlements between open and close (Bybit history)
        t0 = int(datetime.strptime(p["opened"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp() * 1000)
        h = get(f"{BYB}/funding/history", dict(category="linear", symbol=p["sym"], startTime=t0, endTime=now_ms(), limit=50))["result"]["list"]
        fund = sum(p["dir"] * float(x["fundingRate"]) * p["qty"] * p["entry"] for x in h if t0 < int(x["fundingRateTimestamp"]) <= now_ms())
    pnl -= fund
    s["cash"] += p["margin"] + pnl - fee
    s["fees"] += fee
    s["realized"] += pnl - fee - p["fee_open"]
    del s["positions"][pid]
    net = pnl - fee - p["fee_open"]
    append_chain(LOG / "fills.jsonl", dict(utc=iso(), book_ms=bts, kind="CLOSE", id=pid, mkt=p["mkt"], sym=p["sym"], side=p["side"], qty=p["qty"],
                                           px=px, book_top=tb, fee=fee, reason=reason, trigger_px=px_hint, entry=p["entry"], pnl_gross=pnl, funding=fund,
                                           pnl_net=net, r_multiple=net / (p["risk"] * p["equity_at_open"]), cash=s["cash"]))
    return px, net


def cmd_close(a):
    with Lock():
        s = roll_day(load_state())
        append_chain(LOG / "decisions.jsonl", dict(utc=iso(), kind="CLOSE_REQUEST", id=a.id, reason=a.reason))
        px, net = close_pos(s, a.id, "MANUAL: " + a.reason)
        save_state(s)
        print(f"CLOSED {a.id} @ {px:.6g} net {net:+.2f}")


def cmd_status(a):
    s = load_state()
    eq = mark(s)
    d0 = s["day_start_equity"]
    print(f"{iso()}  equity {eq:,.2f}  cash {s['cash']:,.2f}  realized {s['realized']:+,.2f}  fees {s['fees']:,.2f}  "
          f"day {s['day']} start {d0:,.2f}  today {100 * (eq / d0 - 1):+.2f}%  (goal +10% = {d0 * 1.1:,.2f}, +15% = {d0 * 1.15:,.2f})  "
          f"since start {100 * (eq / START_EQUITY - 1):+.2f}%")
    for pid, p in s["positions"].items():
        b, a_, _ = top(p["mkt"], p["sym"])
        px = b if p["side"] == "long" else a_
        print(f"  {pid} {p['mkt']} {p['sym']} {p['side']} qty {p['qty']:.6g} entry {p['entry']:.6g} now {px:.6g} "
              f"uPnL {p['dir'] * p['qty'] * (px - p['entry']):+.2f} stop {p['stop']} target {p['target']} opened {p['opened']}")


# ------------------------------------------------------------------ watcher (background)
def cmd_watch(a):
    last_eq_min, last_beat = 0, 0
    print(f"WATCH start {iso()}", flush=True)
    while True:
        try:
            with Lock():
                s = roll_day(load_state())
                for pid in list(s["positions"]):
                    p = s["positions"][pid]
                    b, a_, _ = top(p["mkt"], p["sym"])
                    exit_px = b if p["dir"] > 0 else a_
                    hit = None
                    if (exit_px - p["stop"]) * p["dir"] <= 0:
                        hit = "STOP"
                    elif p["target"] is not None and (exit_px - p["target"]) * p["dir"] >= 0:
                        hit = "TARGET"
                    elif datetime.now(timezone.utc).strftime("%H:%M") >= RISK["flat_by_utc"]:
                        hit = "FLAT_BY_DAY_END"
                    if hit:
                        px, net = close_pos(s, pid, hit, exit_px)
                        print(f"EVENT {iso()} {hit} {pid} {p['sym']} {p['side']} @ {px:.6g} net {net:+.2f}", flush=True)
                eq = mark(s)
                if eq / s["day_start_equity"] - 1 <= -RISK["daily_loss_limit"] and s.get("halted_day") != s["day"]:
                    s["halted_day"] = s["day"]
                    for pid in list(s["positions"]):
                        px, net = close_pos(s, pid, "DAILY_LOSS_LIMIT")
                    print(f"EVENT {iso()} DAILY LOSS LIMIT: all closed, no new trades today", flush=True)
                save_state(s)
            m = now_ms() // 60000
            if m != last_eq_min:
                last_eq_min = m
                with open(LOG / "equity.csv", "a", encoding="utf-8") as f:
                    f.write(f"{iso()},{eq:.4f},{len(s['positions'])},{s['day_start_equity']:.4f}\n")
            if now_ms() - last_beat >= a.beat * 60_000:
                last_beat = now_ms()
                print(f"BEAT {iso()} equity {eq:,.2f} today {100 * (eq / s['day_start_equity'] - 1):+.2f}% open {len(s['positions'])}", flush=True)
        except Exception as e:                                               # noqa: BLE001
            print(f"WARN {iso()} {type(e).__name__}: {str(e)[:160]}", flush=True)
        time.sleep(a.every)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("snapshot"); p.add_argument("--top", type=int, default=15)
    p = sp.add_parser("order")
    for k in ("mkt", "sym", "side", "reason", "snap"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--stop", type=float, required=True); p.add_argument("--target", type=float, default=None)
    p.add_argument("--risk", type=float, default=0.01)
    p = sp.add_parser("close"); p.add_argument("--id", required=True); p.add_argument("--reason", required=True)
    sp.add_parser("status")
    p = sp.add_parser("watch"); p.add_argument("--every", type=float, default=3.0); p.add_argument("--beat", type=float, default=15.0)
    a = ap.parse_args()
    LOG.mkdir(parents=True, exist_ok=True)
    {"snapshot": cmd_snapshot, "order": cmd_order, "close": cmd_close, "status": cmd_status, "watch": cmd_watch}[a.cmd](a)


if __name__ == "__main__":
    main()
