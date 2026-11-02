"""
1D Swing-AI live engine (Step 7 system) -- SPOT, LONG-ONLY. Modes: 'replay' (history, for the audit), 'dryrun'
(live public data, NO orders) and 'testnet' (Binance SPOT TESTNET orders). There is deliberately NO mainnet mode.

The system (pre-registered, accepted in Step 7):
  * every real-time ZigZag up event (K=2/3/4) on a coin is a candidate entry (signal at the daily close);
  * 13 learned exit plans; one model per plan predicts log(1+net return) from causal swing-structure features;
  * the models are RE-TRAINED on the 1st of every month on all outcomes completed before that day (continuous learning);
  * trade = best plan if its prediction > 0, candidates ranked by prediction; the position keeps that plan;
  * risk: 20% USDT reserve, 8 slots of 80%/8, 2% risk cap, 15% portfolio drawdown -> no new entries for 30 days.

No train/serve skew: candidates, features, matrix, training and prediction are the Step 7 functions; positions use the
engine's E.open_position / E.intraday / E.close_exit_reason. audits/audit_live_1d_ai_replay.py proves that a day-by-day
replay reproduces the Step 7 backtest trades exactly and that live training reproduces the walk-forward predictions.

Daily cycle (after the 00:00 UTC close of day d):
  1. day d for every open position: exchange stop fills (testnet) / OHLC rule (replay, dryrun), partial target,
     end-of-day stop raises (breakeven / runner) -> the exchange stop order is replaced when the stop moved
  2. exit decisions at the close (opposite swing of the plan's scale, inactivity)
  3. mark-to-market + drawdown pause
  4. candidates of day d -> model of d's month -> decisions
  5. execute now (= next open): exits first, then entries with the same sizing as the backtest; stop orders placed
"""
import sys
import json
import time
import pickle
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import swing_strategy_1d as E
import step7_swing_ai_1d as S7
from live_1d_swing_engine import load_history, CCXTBroker, STOP_LIMIT_OFFSET
from config import LOGS_DIR

CFG = E.Config("ZZ", 4.0, False, 1.5, None, True, None, 8, 0.15, False)    # risk layer of the Step 7 portfolio
RESERVE = 0.20
OUT = LOGS_DIR / "live_1d_ai"
MODEL_DIR = OUT / "models"
F = E.FRICTION


# ----------------------------------------------------------------------------------------------
# Brokers
# ----------------------------------------------------------------------------------------------
class ReplayBroker:
    """History: market orders at the execution day's OPEN; stops and partials come from the daily OHLC (E.intraday)."""
    live = False

    def __init__(self, data):
        self.data = {s: df.set_index("timestamp") for s, df in data.items()}

    def price(self, s, day):
        return float(self.data[s].loc[day, "open"])

    def buy(self, s, units, day, stop):
        return self.price(s, day), units, None

    def sell(self, s, units, day, stop_id=None):
        return self.price(s, day)

    def replace_stop(self, s, units, stop, old_id):
        return None


class LiveBroker(CCXTBroker):
    """dryrun: public prices, simulated fills. testnet: real SPOT TESTNET orders (sandbox forced in CCXTBroker)."""

    @property
    def live(self):                       # dryrun: stops/partials filled by the OHLC rule exactly like the backtest
        return self.mode == "testnet"

    def price(self, s, day=None):
        return float(self.pub.fetch_ticker(f"{s[:-4]}/USDT")["last"])

    def replace_stop(self, s, units, stop, old_id):
        if self.mode != "testnet":
            return None
        sym = f"{s[:-4]}/USDT"
        if old_id:
            try:
                self.ex.cancel_order(old_id, sym)
            except Exception as e:
                print(f"[WARN] cancel stop {old_id} {sym}: {e}")
        free = float(self.ex.fetch_balance().get(s[:-4], {}).get("free", 0.0))
        qty = float(self.ex.amount_to_precision(sym, min(units, free)))
        if qty <= 0:
            return None
        o = self.ex.create_order(sym, "STOP_LOSS_LIMIT", "sell", qty,
                                 float(self.ex.price_to_precision(sym, stop * (1 - STOP_LIMIT_OFFSET))),
                                 {"stopPrice": float(self.ex.price_to_precision(sym, stop)), "timeInForce": "GTC"})
        return o["id"]

    def sell_qty(self, s, qty):
        """Market sell of part of a position (partial take-profit); the stop order is replaced by the caller."""
        if self.mode != "testnet":
            return self.price(s)
        sym = f"{s[:-4]}/USDT"
        q = float(self.ex.amount_to_precision(sym, qty))
        if q <= 0:
            return self.price(s)
        o = self.ex.create_order(sym, "market", "sell", q)
        return float(o.get("average") or self.price(s))

    def exchange_stop_fill(self, s, pos):
        if self.mode != "testnet" or not pos.get("stop_id"):
            return None
        o = self.ex.fetch_order(pos["stop_id"], f"{s[:-4]}/USDT")
        return float(o.get("average") or o.get("price")) if o["status"] == "closed" else None


# ----------------------------------------------------------------------------------------------
# Models (continuous learning: one model set per calendar month)
# ----------------------------------------------------------------------------------------------
def models_for(data, d):
    """Models of d's month, trained on outcomes completed before the 1st of that month (cached on disk)."""
    T = pd.Timestamp(d).normalize().replace(day=1)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    f = MODEL_DIR / f"models_{T:%Y-%m}.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    cands = S7.build_candidates(data, include_last=True)
    mx = S7.build_matrix(data, cands, end=d)
    models, log = S7.fit_models(mx, T)
    f.write_bytes(pickle.dumps(models))
    pd.DataFrame(log).to_csv(MODEL_DIR / f"training_log_{T:%Y-%m}.csv", index=False)
    print(f"[models] trained for {T:%Y-%m}: " + ", ".join(f"{r['plan']}={r['n_train']}" for r in log), flush=True)
    return models


def decisions_for_day(data, d, models):
    """(symbol, signal_idx) -> (score, plan_name, ref_low) for candidates of day d with a positive best prediction."""
    cands = S7.build_candidates(data, include_last=True)
    rows = cands[cands.signal_date == pd.Timestamp(d)]
    if rows.empty:
        return {}, rows
    P = S7.predict(models, rows)
    out = {}
    for ix, r in rows.iterrows():
        best = P.loc[ix].idxmax(skipna=True) if P.loc[ix].notna().any() else None
        if best is not None and P.loc[ix, best] > 0:
            out[(r.symbol, int(r.signal_idx))] = (float(P.loc[ix, best]), best, float(r.ref_low))
    return out, rows.assign(**{f"pred::{c}": P[c] for c in P.columns})


# ----------------------------------------------------------------------------------------------
# Engine (mirrors E.simulate_state step by step)
# ----------------------------------------------------------------------------------------------
def new_state(cash=E.INITIAL_CAPITAL):
    return dict(cash=cash, positions={}, peak_eq=cash, paused_until=None, trades=[], last_processed=None)


def _close(state, s, fill, why, day):
    p = state["positions"].pop(s)
    p["proceeds"] += p["units"] * fill * (1 - F)
    state["cash"] += p["units"] * fill * (1 - F)
    state["trades"].append(dict(symbol=s, signal_date=p["signal_date"], entry_date=p["entry_date"],
                                entry_price=p["entry_price"], plan=p["plan_name"], exit_date=str(pd.Timestamp(day).date()),
                                exit_price=fill, exit_reason=why, cost=p["cost"], pnl=p["proceeds"] - p["cost"],
                                partial_date=p.get("partial_date"), partial_price=p.get("partial_price")))


def run_cycle(data, sigs, d, exec_day, state, broker, decide, log=None):
    px = broker.data
    pos = state["positions"]
    # 1. day d for every open position
    for s in list(pos):
        if d not in px[s].index:
            continue
        p = pos[s]
        row = px[s].loc[d]
        i = int(np.searchsorted(data[s]["timestamp"].values, np.datetime64(d)))
        ex_fill = broker.exchange_stop_fill(s, p) if broker.live else None
        old_stop = p["stop"]
        fills = E.intraday(p, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]),
                           sigs[s]["k2_up_ref"][i])
        if ex_fill is not None:                                  # testnet: the exchange stop really filled
            _close(state, s, ex_fill, "stop_exchange", d)
            continue
        for kind, raw, q in fills:
            if kind == "partial":
                fill = broker.sell_qty(s, q) if broker.live else raw
                p["proceeds"] += q * fill * (1 - F)
                state["cash"] += q * fill * (1 - F)
                p["units"] -= q
                p.update(partial_date=str(d.date()), partial_price=fill)
            else:
                fill = broker.sell(s, p["units"], d, p.get("stop_id")) if broker.live else raw
                _close(state, s, fill, kind, d)
        if s in pos and (p["stop"] != old_stop or any(k == "partial" for k, _, _ in fills)):
            p["stop_id"] = broker.replace_stop(s, p["units"], p["stop"], p.get("stop_id"))
    # 2. exit decisions at the close
    exits = {}
    for s, p in pos.items():
        if d in px[s].index:
            i = int(np.searchsorted(data[s]["timestamp"].values, np.datetime64(d)))
            why = E.close_exit_reason(p, float(px[s].loc[d, "close"]), sigs[s]["dn"], i)
            if why:
                exits[s] = why
    # 3. mark to market + drawdown pause (identical rule to the backtest)
    mtm_close = state["cash"] + sum(p["units"] * float(px[s].loc[d, "close"]) for s, p in pos.items())
    pu = None if state["paused_until"] is None else pd.Timestamp(state["paused_until"])
    if pu is not None and d >= pu:
        pu, state["peak_eq"] = None, mtm_close
    state["peak_eq"] = max(state["peak_eq"], mtm_close)
    if pu is None and (state["peak_eq"] - mtm_close) / state["peak_eq"] >= CFG.dd_pause:
        pu = d + pd.Timedelta(days=E.PAUSE_DAYS)
    state["paused_until"] = None if pu is None else str(pu.date())
    paused = pu is not None
    # 4. candidates of day d
    cands = []
    if not paused:
        for s in data:
            ts = data[s]["timestamp"].values
            i = int(np.searchsorted(ts, np.datetime64(d)))
            if i < len(ts) and ts[i] == np.datetime64(d) and s not in pos:
                dec = decide(s, i, d)
                if dec is not None:
                    cands.append((-dec[0], s, i, dec[1], dec[2]))
        cands.sort(key=lambda x: (x[0], x[1]))
    # 5. execute at exec_day: exits first, then entries
    for s, why in exits.items():
        p = pos[s]
        fill = broker.sell(s, p["units"], exec_day, p.get("stop_id"))
        _close(state, s, fill, why, exec_day)
    opens = {s: broker.price(s, exec_day) for s in list(pos) + [c[1] for c in cands]}
    eq_open = state["cash"] + sum(p["units"] * opens[s] for s, p in pos.items())
    opened = []
    for _, s, si, plan_name, ref in cands:
        if s in pos or len(pos) >= CFG.max_pos:
            continue
        entry_ref = opens[s]
        atr = float(data[s]["ATR_14"].iloc[si])
        p = E.open_position(s, str(pd.Timestamp(data[s]["timestamp"].iloc[si]).date()), str(pd.Timestamp(exec_day).date()),
                            entry_ref, atr, ref, S7.PLANS[plan_name])
        if p is None:
            continue
        stop_dist = (entry_ref - p["stop"]) / entry_ref
        notional = min((1 - RESERVE) * eq_open / CFG.max_pos, E.RISK_CAP * eq_open / stop_dist,
                       (state["cash"] - RESERVE * eq_open) / (1 + F))
        if notional < 10.0:
            continue
        fill, units, stop_id = broker.buy(s, notional / entry_ref, exec_day, p["stop"])
        if not units:
            continue
        p.update(entry_price=fill, units=units, cost=units * fill * (1 + F), stop_id=stop_id, plan_name=plan_name,
                 high_since=fill)
        state["cash"] -= p["cost"]
        pos[s] = p
        opened.append(f"{s}:{plan_name}")
    if log is not None:
        log.append(dict(decision_close=str(d.date()), exec_day=str(pd.Timestamp(exec_day).date()), paused=paused,
                        exits=";".join(f"{k}:{v}" for k, v in exits.items()),
                        candidates=";".join(f"{c[1]}:{c[3]}:{-c[0]:.4f}" for c in cands), opened=";".join(opened),
                        cash=round(state["cash"], 2), mtm_close=round(mtm_close, 2), open_positions=len(pos)))
    return state


def signals_with_refs(data):
    return E.build_signals(data, CFG)


def replay(data, start, end, pred):
    """Day-by-day replay of the live cycle with the walk-forward predictions table (audit)."""
    broker = ReplayBroker(data)
    sigs = signals_with_refs(data)
    table = {(r.symbol, int(r.signal_idx)): r for r in pred.itertuples()}

    def decide(s, i, d):
        r = table.get((s, i))
        if r is None or pd.isna(r.best_pred) or r.best_pred <= 0:
            return None
        return float(r.best_pred), r.best_plan, float(r.ref_low)

    dates = [d for d in sorted(set().union(*[set(df["timestamp"]) for df in data.values()]))
             if pd.Timestamp(start) <= d <= pd.Timestamp(end)]
    state, log = new_state(), []
    for k, d in enumerate(dates[:-1]):
        run_cycle(data, sigs, d, dates[k + 1], state, broker, decide, log)
    return state, log


def live(mode):
    assert mode in ("dryrun", "testnet")
    OUT.mkdir(parents=True, exist_ok=True)
    state_file = OUT / f"state_{mode}.json"
    data = load_history(fetch_live=True)
    d = min(df["timestamp"].max() for df in data.values())
    broker = LiveBroker(mode, data)
    if state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        cash = E.INITIAL_CAPITAL
        if mode == "testnet":
            cash = min(float(broker.ex.fetch_balance().get("USDT", {}).get("free", 0.0)), E.INITIAL_CAPITAL)
        state = new_state(cash)
    if state.get("last_processed") == str(d.date()):
        print(f"[{mode}] daily close {d.date()} already processed -- nothing to do")
        return
    models = models_for(data, d)
    dec, rows = decisions_for_day(data, d, models)
    if len(rows):
        rows.to_csv(OUT / f"{mode}_candidates.csv", mode="a", index=False, header=not (OUT / f"{mode}_candidates.csv").exists())
    sigs = signals_with_refs(data)
    now = pd.Timestamp.now("UTC").tz_localize(None)
    log = []
    run_cycle(data, sigs, d, now, state, broker,
              lambda s, i, day: (dec[(s, i)][0], dec[(s, i)][1], dec[(s, i)][2]) if (s, i) in dec else None, log)
    state["last_processed"] = str(d.date())
    state_file.write_text(json.dumps(state, indent=2, default=str))
    pd.DataFrame(log).to_csv(OUT / f"{mode}_decisions.csv", mode="a", index=False,
                             header=not (OUT / f"{mode}_decisions.csv").exists())
    print(f"[{mode}] processed close {d.date()} at {now} UTC")
    print(pd.DataFrame(log).T.to_string(header=False))
    print(f"open positions: {list(state['positions'])} | cash {state['cash']:.2f} USDT | paused_until {state['paused_until']}")


def safety_check(mode):
    """Between daily closes (testnet): record exchange stop fills; sell at market if a stop-limit was gapped."""
    state_file = OUT / f"state_{mode}.json"
    if mode != "testnet" or not state_file.exists():
        return
    state = json.loads(state_file.read_text())
    if not state["positions"]:
        return
    broker = LiveBroker(mode, {})
    now = pd.Timestamp.now("UTC").tz_localize(None)
    changed = False
    for s in list(state["positions"]):
        p = state["positions"][s]
        hit = broker.exchange_stop_fill(s, p)
        if hit is None and broker.price(s) <= p["stop"]:
            hit = broker.sell(s, p["units"], now, p.get("stop_id"))
        if hit is not None:
            _close(state, s, hit, "stop_intraday", now)
            changed = True
            print(f"[{now}] stop exit {s} @ {hit}", flush=True)
    if changed:
        state_file.write_text(json.dumps(state, indent=2, default=str))


def _single_instance_lock(mode):
    import msvcrt
    OUT.mkdir(parents=True, exist_ok=True)
    fh = open(OUT / f"daemon_{mode}.lock", "a+")
    try:
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        print(f"[{pd.Timestamp.now('UTC')}] another {mode} AI daemon is already running -- exiting", flush=True)
        sys.exit(0)
    return fh


def daemon(mode, every_min=15):
    import ctypes
    import os
    _lock = _single_instance_lock(mode)          # noqa: F841 (kept open on purpose)
    print(f"daemon pid {os.getpid()}", flush=True)
    if sys.platform == "win32":                   # keep the PC awake while the bot runs (released on exit)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    print(f"AI daemon started: mode={mode}, check every {every_min} min", flush=True)
    while True:
        try:
            now = pd.Timestamp.now("UTC").tz_localize(None)
            st_file = OUT / f"state_{mode}.json"
            last = json.loads(st_file.read_text()).get("last_processed") if st_file.exists() else None
            yesterday = str((now.normalize() - pd.Timedelta(days=1)).date())
            if last != yesterday and now.hour * 60 + now.minute >= 5:
                live(mode)
            else:
                safety_check(mode)
            print(f"[heartbeat {now}] last_processed={last}", flush=True)
        except Exception as e:                       # never die silently: log and retry next round
            print(f"[ERROR {pd.Timestamp.now('UTC')}] {type(e).__name__}: {e}", flush=True)
        time.sleep(every_min * 60)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="1D swing-AI engine: dryrun (no orders) or Binance SPOT TESTNET")
    ap.add_argument("--mode", choices=["dryrun", "testnet"], default="dryrun")
    ap.add_argument("--daemon", action="store_true")
    a = ap.parse_args()
    if a.daemon:
        OUT.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(OUT / f"daemon_{a.mode}.log", "a", encoding="utf-8", buffering=1)
        sys.stderr = open(OUT / f"daemon_{a.mode}.err.log", "a", encoding="utf-8", buffering=1)
        daemon(a.mode)
    else:
        live(a.mode)
