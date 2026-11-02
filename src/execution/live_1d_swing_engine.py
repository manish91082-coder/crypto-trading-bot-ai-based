"""
1D Swing Live Engine (Step 5) -- SPOT, LONG-ONLY. Modes: 'replay' (historical, for verification),
'dryrun' (live public market data, NO orders, simulated fills) and 'testnet' (Binance SPOT TESTNET orders).
There is deliberately NO mainnet mode.

Design rule: the live engine re-uses the BACKTEST functions (swing_strategy_1d.build_signals / zigzag / sizing
formula) so live decisions are computed by the same code as the backtest (no train/serve skew).
Proof: audits/audit_live_1d_replay.py replays history day by day and must reproduce E.simulate() exactly.

Final 1D system (from Steps 3b / 4b):
  entry  : ZigZag K=4 up-leg confirmed on the coin AND BTC's latest ZigZag K=3 leg is UP (signal at daily close)
  stop   : entry - 1.5 x ATR14 (of the signal day); exchange-side stop order in testnet mode
  exit   : coin ZigZag K=4 down-leg confirmed -> sell at next open
  risk   : max 8 positions, slot = 80% equity / 8, 2% risk cap, 20% equity always kept in USDT,
           new entries paused 30 days after a 15% portfolio drawdown

Daily cycle (run once after the 00:00 UTC daily close, e.g. 00:05 UTC):
  1. sync stops that triggered during the last closed day
  2. end-of-day position update (highest high, days held, trailing if configured)
  3. exit decisions at the close (opposite leg / time / BTC exit)
  4. mark-to-market at the close -> drawdown-pause state
  5. entry candidates (ranked by 20-day momentum) if not paused
  6. execute: exits first, then entries sized with equity at the current (open) price; place stop orders
"""
import sys
import json
import time
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_strategy_1d as E
from config import LOGS_DIR, SYMBOLS

CFG = E.Config("ZZ", 4.0, True, 1.5, None, True, None, 8, 0.15, False)
RESERVE = 0.20
STOP_LIMIT_OFFSET = 0.01          # testnet STOP_LOSS_LIMIT: limit price 1% below the stop price
OUT = LOGS_DIR / "live_1d"


# ----------------------------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------------------------
def load_history(fetch_live: bool):
    """Local verified raw history (+ closed daily candles from Binance public data when fetch_live)."""
    data = E.load_universe()
    if not fetch_live:
        return data
    import ccxt
    ex = ccxt.binance({"enableRateLimit": True})
    today = pd.Timestamp.now('UTC').tz_localize(None).normalize()
    for s, df in data.items():
        last = df["timestamp"].max()
        since = int((last + pd.Timedelta(days=1)).timestamp() * 1000)
        rows = ex.fetch_ohlcv(f"{s[:-4]}/USDT", "1d", since=since, limit=1000)
        new = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        new["timestamp"] = pd.to_datetime(new["timestamp"], unit="ms")
        new = new[new["timestamp"] < today]                      # drop the still-forming candle
        if len(new):
            merged = pd.concat([df[["timestamp", "open", "high", "low", "close", "volume"]], new], ignore_index=True)
            gaps = merged["timestamp"].diff().dropna()
            assert (gaps == pd.Timedelta(days=1)).all(), f"{s}: gap between local history and live candles"
            tr = pd.concat([merged["high"] - merged["low"], (merged["high"] - merged["close"].shift(1)).abs(),
                            (merged["low"] - merged["close"].shift(1)).abs()], axis=1).max(axis=1)
            merged["ATR_14"] = tr.rolling(14).mean()
            data[s] = merged
    return data


# ----------------------------------------------------------------------------------------------
# Brokers
# ----------------------------------------------------------------------------------------------
class ReplayBroker:
    """Historical fills: market orders at the execution day's OPEN, stops via daily OHLC with the gap rule."""
    def __init__(self, data):
        self.data = {s: df.set_index("timestamp") for s, df in data.items()}

    def open_price(self, s, day):
        return float(self.data[s].loc[day, "open"])

    def buy(self, s, units, day, stop):
        return self.open_price(s, day), units, None

    def sell(self, s, units, day, stop_id=None):
        return self.open_price(s, day)

    def stop_triggered(self, s, pos, day):
        row = self.data[s].loc[day]
        if row["low"] <= pos["stop"]:
            return float(row["open"]) if row["open"] <= pos["stop"] else pos["stop"]
        return None


class CCXTBroker:
    """dryrun: live public prices, simulated fills, no orders.  testnet: real Binance SPOT TESTNET orders."""
    def __init__(self, mode, data):
        import ccxt
        from dotenv import load_dotenv
        self.mode = mode
        self.data = {s: df.set_index("timestamp") for s, df in data.items()}
        self.pub = ccxt.binance({"enableRateLimit": True})
        self.ex = None
        if mode == "testnet":
            import os
            load_dotenv(SRC_DIR.parent / ".env")
            self.ex = ccxt.binance({"apiKey": os.getenv("BINANCE_API_KEY", ""), "secret": os.getenv("BINANCE_API_SECRET", ""),
                                    "enableRateLimit": True, "options": {"defaultType": "spot"}})
            self.ex.set_sandbox_mode(True)                      # hard-wired: testnet only
            assert "testnet" in self.ex.urls["api"]["public"], "refusing to run outside Binance TESTNET"
            self.ex.load_markets()

    def price(self, s):
        return float(self.pub.fetch_ticker(f"{s[:-4]}/USDT")["last"])

    def round_amount(self, s, units, px):
        if self.mode != "testnet":
            return units
        m = self.ex.market(f"{s[:-4]}/USDT")
        units = float(self.ex.amount_to_precision(m["symbol"], units))
        min_cost = (m.get("limits", {}).get("cost", {}) or {}).get("min") or 5.0
        return units if units * px >= min_cost else 0.0

    def buy(self, s, units, day, stop):
        px = self.price(s)
        units = self.round_amount(s, units, px)
        if units <= 0:
            return None, 0.0, None
        if self.mode == "dryrun":
            return px, units, None
        sym = f"{s[:-4]}/USDT"
        o = self.ex.create_order(sym, "market", "buy", units)
        fill = float(o.get("average") or px)
        filled = float(o.get("filled") or units)
        # Binance takes the commission in the bought coin unless paid in BNB -> protect only what we really hold
        free = float(self.ex.fetch_balance().get(s[:-4], {}).get("free", 0.0))
        filled = float(self.ex.amount_to_precision(sym, min(filled, free)))
        stop_px = float(self.ex.price_to_precision(sym, stop))
        lim_px = float(self.ex.price_to_precision(sym, stop * (1 - STOP_LIMIT_OFFSET)))
        so = self.ex.create_order(sym, "STOP_LOSS_LIMIT", "sell", float(self.ex.amount_to_precision(sym, filled)),
                                  lim_px, {"stopPrice": stop_px, "timeInForce": "GTC"})
        return fill, filled, so["id"]

    def sell(self, s, units, day, stop_id=None):
        px = self.price(s)
        if self.mode == "dryrun":
            return px
        sym = f"{s[:-4]}/USDT"
        if stop_id:
            try:
                self.ex.cancel_order(stop_id, sym)
            except Exception as e:                              # already filled/cancelled -> reconcile below
                print(f"[WARN] cancel stop {stop_id} {sym}: {e}")
        free = float(self.ex.fetch_balance().get(s[:-4], {}).get("free", 0.0))
        qty = float(self.ex.amount_to_precision(sym, min(units, free)))
        if qty <= 0:
            return px
        o = self.ex.create_order(sym, "market", "sell", qty)
        return float(o.get("average") or px)

    def stop_triggered(self, s, pos, day):
        if self.mode == "testnet" and pos.get("stop_id"):
            sym = f"{s[:-4]}/USDT"
            o = self.ex.fetch_order(pos["stop_id"], sym)
            if o["status"] == "closed":
                return float(o.get("average") or o.get("price"))
            # Fallback: a stop-LIMIT order can stay unfilled after a gap below its limit price.
            # If price is already at/below the stop, cancel it and sell at market.
            if self.price(s) <= pos["stop"]:
                return self.sell(s, pos["units"], day, pos["stop_id"])
            return None
        row = self.data[s].loc[day]                             # dryrun: same rule as the backtest on the closed candle
        if row["low"] <= pos["stop"]:
            return float(row["open"]) if row["open"] <= pos["stop"] else pos["stop"]
        return None


# ----------------------------------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------------------------------
def new_state(cash=E.INITIAL_CAPITAL):
    return dict(cash=cash, positions={}, peak_eq=cash, paused_until=None, trades=[])


def run_cycle(data, sigs, d, exec_day, state, broker, log=None):
    """Decisions at the CLOSE of day d, executed at exec_day (next open / now)."""
    F = E.FRICTION
    px = {s: df.set_index("timestamp") for s, df in data.items()} if not hasattr(broker, "data") else broker.data
    pos = state["positions"]

    # 1. stops during day d
    for s in list(pos):
        if d not in px[s].index:
            continue
        hit = broker.stop_triggered(s, pos[s], d)
        if hit is not None:
            p = pos.pop(s)
            state["cash"] += p["units"] * hit * (1 - F)
            reason = "gap_stop" if hit == float(px[s].loc[d, "open"]) and px[s].loc[d, "open"] <= p["stop"] else (
                "trail_stop" if p["stop"] > p["initial_stop"] else "stop")
            state["trades"].append(dict(symbol=s, signal_date=p["signal_date"], entry_date=p["entry_date"], entry_price=p["entry_price"],
                                        units=p["units"], exit_date=str(d.date()), exit_price=hit, exit_reason=reason,
                                        pnl=p["units"] * hit * (1 - F) - p["cost"]))
    # 2. end-of-day update
    for s, p in pos.items():
        if d in px[s].index:
            p["high_since"] = max(p["high_since"], float(px[s].loc[d, "high"]))
            p["days"] += 1
            if CFG.trail_atr is not None:
                p["stop"] = max(p["stop"], p["high_since"] - CFG.trail_atr * p["atr"])
    # 3. exit decisions at the close
    exits = {}
    btc_dn = E.btc_down_flags(data) if CFG.btc_exit else {}
    for s, p in pos.items():
        i = int(np.searchsorted(data[s]["timestamp"].values, np.datetime64(d)))
        if CFG.opp_exit and sigs[s]["opp"][i]:
            exits[s] = "opposite_leg"
        elif CFG.time_stop is not None and p["days"] >= CFG.time_stop and float(px[s].loc[d, "close"]) < p["entry_price"]:
            exits[s] = "time_stop"
    if CFG.btc_exit and btc_dn.get(d, False):
        exits = {s: "btc_exit" for s in pos}
    # 4. mark to market at the close + drawdown pause
    mtm_close = state["cash"] + sum(p["units"] * float(px[s].loc[d, "close"]) for s, p in pos.items())
    paused = False
    if CFG.dd_pause is not None:
        pu = None if state["paused_until"] is None else pd.Timestamp(state["paused_until"])
        if pu is not None and d >= pu:
            pu, state["peak_eq"] = None, mtm_close
        state["peak_eq"] = max(state["peak_eq"], mtm_close)
        if pu is None and (state["peak_eq"] - mtm_close) / state["peak_eq"] >= CFG.dd_pause:
            pu = d + pd.Timedelta(days=E.PAUSE_DAYS)
        state["paused_until"] = None if pu is None else str(pu.date())
        paused = pu is not None
    # 5. candidates
    cands = []
    if not paused:
        for s in data:
            ts = data[s]["timestamp"].values
            i = int(np.searchsorted(ts, np.datetime64(d)))
            if i < len(ts) and ts[i] == np.datetime64(d) and s not in pos and sigs[s]["sig"][i]:
                m = sigs[s]["mom"][i]
                cands.append((-(m if not np.isnan(m) else -9), s, i))
        cands.sort()
    if exec_day is None:
        return dict(exits=exits, candidates=[s for _, s, _ in cands], paused=paused, mtm_close=mtm_close)
    # 6a. execute exits
    for s, why in exits.items():
        p = pos.pop(s)
        fill = broker.sell(s, p["units"], exec_day, p.get("stop_id"))
        state["cash"] += p["units"] * fill * (1 - F)
        state["trades"].append(dict(symbol=s, signal_date=p["signal_date"], entry_date=p["entry_date"], entry_price=p["entry_price"],
                                    units=p["units"], exit_date=str(exec_day.date()), exit_price=fill, exit_reason=why,
                                    pnl=p["units"] * fill * (1 - F) - p["cost"]))
    # 6b. execute entries (sizing identical to E.simulate)
    opens = {s: (broker.open_price(s, exec_day) if isinstance(broker, ReplayBroker) else broker.price(s)) for s in list(pos) + [c[1] for c in cands]}
    eq_open = state["cash"] + sum(p["units"] * opens[s] for s, p in pos.items())
    for _, s, si in cands:
        if s in pos or len(pos) >= CFG.max_pos:
            continue
        entry_ref = opens[s]
        atr = float(data[s]["ATR_14"].iloc[si])
        stop = entry_ref - CFG.stop_atr * atr
        if stop <= 0:
            continue
        stop_dist = (entry_ref - stop) / entry_ref
        notional = min((1 - RESERVE) * eq_open / CFG.max_pos, E.RISK_CAP * eq_open / stop_dist,
                       (state["cash"] - RESERVE * eq_open) / (1 + F))
        if notional < 10.0:
            continue
        fill, units, stop_id = broker.buy(s, notional / entry_ref, exec_day, stop)
        if not units:
            continue
        cost = units * fill * (1 + F)
        state["cash"] -= cost
        pos[s] = dict(signal_date=str(pd.Timestamp(data[s]["timestamp"].iloc[si]).date()), entry_date=str(exec_day.date()),
                      entry_price=fill, units=units, cost=cost, atr=atr, stop=stop, initial_stop=stop,
                      high_since=fill, days=0, stop_id=stop_id)
    if log is not None:
        log.append(dict(decision_close=str(d.date()), exec_day=str(exec_day.date()), paused=paused,
                        exits=";".join(f"{k}:{v}" for k, v in exits.items()), candidates=";".join(s for _, s, _ in cands),
                        opened=";".join(s for s in pos if pos[s]["entry_date"] == str(exec_day.date())),
                        cash=round(state["cash"], 2), mtm_close=round(mtm_close, 2), open_positions=len(pos)))
    return state


def replay(data, start, end):
    """Day-by-day historical replay of the live cycle (used by the audit)."""
    broker = ReplayBroker(data)
    sigs = E.build_signals(data, CFG)
    dates = [d for d in sorted(set().union(*[set(df["timestamp"]) for df in data.values()]))
             if pd.Timestamp(start) <= d <= pd.Timestamp(end)]
    state, log = new_state(), []
    for k, d in enumerate(dates[:-1]):
        run_cycle(data, sigs, d, dates[k + 1], state, broker, log)
    # stops on the final day (positions stay open; the backtest closes them as 'end_of_test')
    last = dates[-1]
    for s in list(state["positions"]):
        hit = broker.stop_triggered(s, state["positions"][s], last)
        if hit is not None:
            p = state["positions"].pop(s)
            state["cash"] += p["units"] * hit * (1 - E.FRICTION)
            state["trades"].append(dict(symbol=s, signal_date=p["signal_date"], entry_date=p["entry_date"], entry_price=p["entry_price"],
                                        units=p["units"], exit_date=str(last.date()), exit_price=hit, exit_reason="stop",
                                        pnl=p["units"] * hit * (1 - E.FRICTION) - p["cost"]))
    return state, log


def live(mode):
    assert mode in ("dryrun", "testnet")
    OUT.mkdir(parents=True, exist_ok=True)
    state_file = OUT / f"state_{mode}.json"
    data = load_history(fetch_live=True)
    last_closed = min(df["timestamp"].max() for df in data.values())
    broker = CCXTBroker(mode, data)
    if state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        cash = E.INITIAL_CAPITAL
        if mode == "testnet":
            # the plan is a $10,000 account: never use more than that even if the testnet wallet holds more
            cash = min(float(broker.ex.fetch_balance().get("USDT", {}).get("free", 0.0)), E.INITIAL_CAPITAL)
        state = new_state(cash)
        state["last_processed"] = None
    if state.get("last_processed") == str(last_closed.date()):
        print(f"[{mode}] daily close {last_closed.date()} already processed -- nothing to do")
        return
    sigs = E.build_signals(data, CFG)
    now = pd.Timestamp.now('UTC').tz_localize(None)
    log = []
    run_cycle(data, sigs, last_closed, now, state, broker, log)
    state["last_processed"] = str(last_closed.date())
    state_file.write_text(json.dumps(state, indent=2, default=str))
    pd.DataFrame(log).to_csv(OUT / f"{mode}_decisions.csv", mode="a", index=False,
                             header=not (OUT / f"{mode}_decisions.csv").exists())
    print(f"[{mode}] processed close {last_closed.date()} at {now} UTC")
    print(pd.DataFrame(log).T.to_string(header=False))
    print(f"open positions: {list(state['positions'])} | cash {state['cash']:.2f} USDT | paused_until {state['paused_until']}")


def safety_check(mode):
    """Between daily closes: record exchange-side stop fills and force-exit positions whose stop was gapped."""
    state_file = OUT / f"state_{mode}.json"
    if mode != "testnet" or not state_file.exists():
        return
    state = json.loads(state_file.read_text())
    if not state["positions"]:
        return
    broker = CCXTBroker(mode, {})
    now = pd.Timestamp.now("UTC").tz_localize(None)
    changed = False
    for s in list(state["positions"]):
        p = state["positions"][s]
        hit = broker.stop_triggered(s, p, now)
        if hit is not None:
            state["positions"].pop(s)
            state["cash"] += p["units"] * hit * (1 - E.FRICTION)
            state["trades"].append(dict(symbol=s, signal_date=p["signal_date"], entry_date=p["entry_date"],
                                        entry_price=p["entry_price"], units=p["units"], exit_date=str(now),
                                        exit_price=hit, exit_reason="stop_intraday",
                                        pnl=p["units"] * hit * (1 - E.FRICTION) - p["cost"]))
            changed = True
            print(f"[{now}] stop exit {s} @ {hit}")
    if changed:
        state_file.write_text(json.dumps(state, indent=2, default=str))


def _single_instance_lock(mode):
    """Exclusive OS file lock held for the process lifetime; a second daemon exits immediately."""
    import msvcrt
    OUT.mkdir(parents=True, exist_ok=True)
    fh = open(OUT / f"daemon_{mode}.lock", "a+")
    try:
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        print(f"[{pd.Timestamp.now('UTC')}] another {mode} daemon is already running -- exiting", flush=True)
        sys.exit(0)
    return fh


def daemon(mode, every_min=15):
    import ctypes
    import os
    _lock = _single_instance_lock(mode)          # noqa: F841 (kept open on purpose)
    print(f"daemon pid {os.getpid()}", flush=True)
    if sys.platform == "win32":                       # keep the PC awake while the bot runs (released on exit)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    print(f"daemon started: mode={mode}, check every {every_min} min", flush=True)
    while True:
        try:
            now = pd.Timestamp.now("UTC").tz_localize(None)
            st_file = OUT / f"state_{mode}.json"
            last = json.loads(st_file.read_text()).get("last_processed") if st_file.exists() else None
            yesterday = str((now.normalize() - pd.Timedelta(days=1)).date())
            if last != yesterday and now.hour * 60 + now.minute >= 5:   # new daily close available (after 00:05 UTC)
                live(mode)
            else:
                safety_check(mode)
            print(f"[heartbeat {now}] last_processed={last}", flush=True)
        except Exception as e:                           # never die silently: log and retry next round
            print(f"[ERROR {pd.Timestamp.now('UTC')}] {type(e).__name__}: {e}", flush=True)
        time.sleep(every_min * 60)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="1D swing engine: dryrun (no orders) or Binance SPOT TESTNET")
    ap.add_argument("--mode", choices=["dryrun", "testnet"], default="dryrun")
    ap.add_argument("--daemon", action="store_true", help="run forever: daily cycle after each close + stop safety checks")
    a = ap.parse_args()
    if a.daemon:
        # the daemon writes its own logs (shared-access append) so a second launch can log "already running"
        OUT.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(OUT / f"daemon_{a.mode}.log", "a", encoding="utf-8", buffering=1)
        sys.stderr = open(OUT / f"daemon_{a.mode}.err.log", "a", encoding="utf-8", buffering=1)
        daemon(a.mode)
    else:
        live(a.mode)
