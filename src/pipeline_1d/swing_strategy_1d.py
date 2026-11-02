"""
1D Swing Strategy Engine (Step 3, extended in Step 6) -- SPOT, LONG-ONLY.

Execution model (fixed, not optimised):
  * Signals are computed from data up to day t's CLOSE; entries fill at day t+1 OPEN.
  * Friction per fill = taker fee 0.075% + slippage 0.05% (applied to every buy and sell).
  * Stop orders: if the day OPENS at/below the stop -> fill at the open (gap), else at the stop price;
    slippage is applied on top. The stop is checked from the entry day itself.
  * Daily bars do not show intraday order: on any day the stop is checked FIRST, then a partial take-profit
    target; every stop raise (trailing / breakeven / runner lock / structure) happens at the END of the day
    and can trigger from the next day on.
  * Spot realism: no shorts, no leverage. Each new position gets notional = (1-reserve) x equity / MAX_POSITIONS,
    capped by free cash above the reserve and by a 2% equity risk cap at the initial stop distance.
  * Equity is marked to market at every daily close.

Entry families (all causal):
  ZZ  : an ATR-ZigZag UP event (K) on day t (a confirmed swing low, or -- since Step 6.0 -- a failed down-leg flip)
  BO  : close[t] > highest high of the previous N days               (Donchian breakout)
  PB  : coin is in a confirmed up-leg (K=3); price pulled back >= R x ATR from the high made since the
        confirmation; entry when close[t] > high[t-1] (resumption)
Regime filter (optional): BTC's latest ZigZag event (K=3) is UP on day t.

Exit components (every position keeps the exit plan it was opened with):
  initial stop   'atr'  : entry - S x ATR(signal day)
                 'swing': confirmed swing low x (1 - 0.5%)                 (Step 6)
  trailing stop  highest high since entry - T x ATR(signal day)           (None = off)
  breakeven      stop -> entry once highest high >= entry + N x ATR       (Step 6)
  structure      stop -> new K=2 higher low x (1 - 0.5%)                  (Step 6)
  partial        sell a fraction at entry + N x ATR; then runner lock / runner trail (Step 6, config.py Law #6)
  inactivity     exit if the partial target was not reached within N days (Step 6)
  opposite leg   a ZigZag DOWN event (scale exit_k) on the coin -> exit next open
  time stop      after D days, if close < entry price -> exit next open (None = off)
"""
import sys
import itertools
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SRC_DIR / "analytics") not in sys.path:
    sys.path.insert(0, str(SRC_DIR / "analytics"))

from config import SYMBOLS, BINANCE_TAKER_FEE
import swing_study_1d as SS

INITIAL_CAPITAL = 10_000.0
SLIPPAGE = 0.0005
FRICTION = BINANCE_TAKER_FEE + SLIPPAGE      # 0.125% per fill
MAX_POSITIONS = 5
RISK_CAP = 0.02                              # max 2% of equity lost at the initial stop
REGIME_K = 3.0
PAUSE_DAYS = 30
PB_K = 3.0
SWING_BUFFER = 0.005                         # swing / structure stops sit 0.5% below the swing low
STRUCT_K = 2.0
_ZZ_CACHE = {}


def _df_key(df):
    return (id(df), len(df), str(df["timestamp"].iloc[-1]), float(df["close"].iloc[-1]), float(df["ATR_14"].iloc[-1]))


def zz(df: pd.DataFrame, k: float) -> dict:
    """Real-time ZigZag event arrays for one coin (cached). All arrays are causal (known at that day's close)."""
    key = (_df_key(df), float(k), SS.EMIT_FLIP_EVENTS)
    if key in _ZZ_CACHE:
        return _ZZ_CACHE[key]
    events = []
    SS.zigzag_pivots(df, k, events)
    n = len(df)
    up, dn, up_flip = np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool)
    up_ref, dn_ref = np.full(n, np.nan), np.full(n, np.nan)
    for e in sorted(events, key=lambda e: e["seq"]):
        i = e["confirm_idx"]
        if e["kind"] == "L":
            up[i], up_ref[i], up_flip[i] = True, e["ref_price"], e["flip"]
        else:
            dn[i], dn_ref[i] = True, e["ref_price"]
    state = np.zeros(n, int)                     # +1 last event was up, -1 down, 0 none yet
    cur = 0
    for i in range(n):
        if up[i] and dn[i]:
            same = [e for e in events if e["confirm_idx"] == i]
            if SS.EMIT_FLIP_EVENTS:
                later = max(same, key=lambda e: e["seq"])            # true emission order
            else:
                later = max(same, key=lambda e: e["pivot_idx"])      # exact pre-Step-6 rule
            cur = 1 if later["kind"] == "L" else -1
        elif up[i]:
            cur = 1
        elif dn[i]:
            cur = -1
        state[i] = cur
    out = dict(up=up, dn=dn, state=state, up_ref=up_ref, dn_ref=dn_ref, up_flip=up_flip, events=events)
    if len(_ZZ_CACHE) > 4000:
        _ZZ_CACHE.clear()
    _ZZ_CACHE[key] = out
    return out


def zigzag_event_flags(df: pd.DataFrame, k: float):
    """Boolean arrays: up_confirm[t], down_confirm[t] (real-time event days) and causal leg state."""
    z = zz(df, k)
    return z["up"], z["dn"], z["state"]


def btc_down_flags(data: dict) -> dict:
    """date -> True on days a BTC ZigZag(K=3) DOWN event happens (real-time, causal)."""
    return dict(zip(data["BTCUSDT"]["timestamp"], zz(data["BTCUSDT"], REGIME_K)["dn"]))


@dataclass(frozen=True)
class Config:
    entry: str                 # 'ZZ' | 'BO' | 'PB'
    param: float               # ZZ: K, BO: N days, PB: pullback R (ATR)
    regime: bool               # BTC up-leg filter
    stop_atr: float
    trail_atr: Optional[float]
    opp_exit: bool
    time_stop: Optional[int]
    # --- Step 3b risk layer (defaults = Step 3 behaviour) ---
    max_pos: int = 5                     # max simultaneous positions (slot = equity / max_pos)
    dd_pause: Optional[float] = None     # portfolio MTM drawdown that pauses NEW entries for PAUSE_DAYS
    btc_exit: bool = False               # exit all positions at next open when a BTC ZigZag(K=3) down event happens
    # --- Step 6 exit layer (defaults = Step 3b behaviour) ---
    exit_k: Optional[float] = None       # opposite-leg scale (None: ZZ -> its own K, BO/PB -> 3)
    stop_mode: str = "atr"               # 'atr' | 'swing'
    be_atr: Optional[float] = None
    struct_trail: bool = False
    partial_atr: Optional[float] = None
    partial_frac: float = 0.0
    runner_lock_atr: Optional[float] = None
    runner_trail_atr: Optional[float] = None
    inact_days: Optional[int] = None

    def key(self) -> str:
        base = (f"{self.entry}{self.param:g}|reg={int(self.regime)}|S={self.stop_atr:g}|T={self.trail_atr}"
                f"|opp={int(self.opp_exit)}|time={self.time_stop}")
        if (self.max_pos, self.dd_pause, self.btc_exit) != (5, None, False) or self.step6_extra():
            base += f"|mp={self.max_pos}|dd={self.dd_pause}|bx={int(self.btc_exit)}"
        if self.step6_extra():
            base += (f"|xk={self.exit_k}|sm={self.stop_mode}|be={self.be_atr}|st={int(self.struct_trail)}"
                     f"|pt={self.partial_atr}x{self.partial_frac:g}|rl={self.runner_lock_atr}|rt={self.runner_trail_atr}"
                     f"|in={self.inact_days}")
        return base

    def step6_extra(self) -> bool:
        return (self.exit_k, self.stop_mode, self.be_atr, self.struct_trail, self.partial_atr, self.partial_frac,
                self.runner_lock_atr, self.runner_trail_atr, self.inact_days) != (None, "atr", None, False, None, 0.0,
                                                                                    None, None, None)

    def resolved_exit_k(self) -> float:
        if self.exit_k is not None:
            return float(self.exit_k)
        return float(self.param) if self.entry == "ZZ" else 3.0

    def exit_plan(self) -> dict:
        """The per-position exit plan (what a position opened under this config keeps until it closes)."""
        return dict(stop_mode=self.stop_mode, stop_atr=self.stop_atr, trail_atr=self.trail_atr, opp_exit=self.opp_exit,
                    exit_k=self.resolved_exit_k(), time_stop=self.time_stop, be_atr=self.be_atr,
                    struct_trail=self.struct_trail, partial_atr=self.partial_atr, partial_frac=self.partial_frac,
                    runner_lock_atr=self.runner_lock_atr, runner_trail_atr=self.runner_trail_atr,
                    inact_days=self.inact_days)


# ----------------------------------------------------------------------------------------------
# Data & causal signals
# ----------------------------------------------------------------------------------------------
def load_universe(symbols=None):
    SS.ANOMALIES.clear()
    data = {}
    for s in (symbols or SYMBOLS):
        data[s] = SS.load_1d(s)                  # same pre-flight asserts + bad-print guard as the study
    return data


def build_signals(data: dict, cfg: Config):
    """Per coin: entry signal array, swing reference low (for swing stops), 20-day change (ranking),
    down-event arrays for every exit scale and the K=2 higher-low array (structure trail)."""
    out = {}
    btc_state = None
    if cfg.regime:
        btc_state = pd.Series(zz(data["BTCUSDT"], REGIME_K)["state"], index=data["BTCUSDT"]["timestamp"])
    for s, df in data.items():
        n = len(df)
        ref = np.full(n, np.nan)
        if cfg.entry == "ZZ":
            z = zz(df, cfg.param)
            sig = z["up"].copy()
            ref = z["up_ref"]
        elif cfg.entry == "BO":
            prior_high = df["high"].shift(1).rolling(int(cfg.param)).max().values
            sig = df["close"].values > prior_high
        elif cfg.entry == "PB":
            z = zz(df, PB_K)
            up, state = z["up"], z["state"]
            sig = np.zeros(n, bool)
            hi, lo, cl, atr = df["high"].values, df["low"].values, df["close"].values, df["ATR_14"].values
            armed, run_high = False, np.nan
            for i in range(1, n):
                if up[i]:
                    armed, run_high = False, hi[i]
                if state[i] != 1:
                    armed, run_high = False, np.nan
                    continue
                run_high = hi[i] if np.isnan(run_high) else max(run_high, hi[i])
                if not armed and lo[i] <= run_high - cfg.param * atr[i]:
                    armed = True
                    continue                     # the pullback day itself cannot be the resumption day
                if armed and cl[i] > hi[i - 1]:
                    sig[i] = True
                    armed, run_high = False, hi[i]
        else:
            raise ValueError(cfg.entry)
        sig = sig & ~np.isnan(df["ATR_14"].values)
        if cfg.regime:
            reg = df["timestamp"].map(btc_state).fillna(0).values == 1
            sig = sig & reg
        mom20 = df["close"].pct_change(20).values
        k2 = zz(df, STRUCT_K)
        out[s] = dict(sig=sig, ref=ref, mom=mom20, opp=zz(df, cfg.resolved_exit_k())["dn"],
                      dn={k: zz(df, k)["dn"] for k in (2.0, 3.0, 4.0)},
                      k2_up_ref=np.where(k2["up"], k2["up_ref"], np.nan))
    return out


# ----------------------------------------------------------------------------------------------
# Position mechanics shared by the portfolio engine and the Step 7 single-trade simulator
# ----------------------------------------------------------------------------------------------
def open_position(symbol, signal_date, entry_date, entry_px, atr, swing_ref, plan, units=0.0, cost=0.0):
    """Returns the position dict, or None when the plan's stop is invalid for this entry."""
    if plan["stop_mode"] == "swing":
        if np.isnan(swing_ref):
            return None
        stop = swing_ref * (1 - SWING_BUFFER)
    else:
        stop = entry_px - plan["stop_atr"] * atr
    if stop <= 0 or stop >= entry_px:
        return None
    return dict(symbol=symbol, signal_date=signal_date, entry_date=entry_date, entry_price=entry_px, units=units,
                cost=cost, atr=atr, stop=stop, initial_stop=stop, high_since=entry_px, days=0, plan=plan,
                partial_done=False, proceeds=0.0)


def intraday(p, o, h, l, c, k2_ref):
    """One day for an open position. Returns list of fills [(kind, raw_price, units)] where kind is
    'partial' or an exit reason ('stop' / 'trail_stop' / 'gap_stop'). Updates the position in place."""
    pl = p["plan"]
    if l <= p["stop"]:
        raw = o if o <= p["stop"] else p["stop"]
        why = "gap_stop" if o <= p["stop"] else ("trail_stop" if p["stop"] > p["initial_stop"] else "stop")
        return [(why, raw, p["units"])]
    fills = []
    if pl["partial_atr"] is not None and not p["partial_done"]:
        target = p["entry_price"] + pl["partial_atr"] * p["atr"]
        if h >= target:
            q = p["units"] * pl["partial_frac"]
            fills.append(("partial", max(o, target), q))
            p["partial_done"] = True
    # end of day: highest high, age, stop raises (effective from the next day)
    p["high_since"] = max(p["high_since"], h)
    p["days"] += 1
    if pl["trail_atr"] is not None:
        p["stop"] = max(p["stop"], p["high_since"] - pl["trail_atr"] * p["atr"])
    if pl["be_atr"] is not None and p["high_since"] >= p["entry_price"] + pl["be_atr"] * p["atr"]:
        p["stop"] = max(p["stop"], p["entry_price"])
    if p["partial_done"]:
        if pl["runner_lock_atr"] is not None:
            p["stop"] = max(p["stop"], p["entry_price"] + pl["runner_lock_atr"] * p["atr"])
        if pl["runner_trail_atr"] is not None:
            p["stop"] = max(p["stop"], p["high_since"] - pl["runner_trail_atr"] * p["atr"])
    if pl["struct_trail"] and not np.isnan(k2_ref):
        s2 = k2_ref * (1 - SWING_BUFFER)
        if s2 < c:
            p["stop"] = max(p["stop"], s2)
    return fills


def close_exit_reason(p, close, dn_flags: dict, i):
    """Exit decision at the close (executed at the next open) or None."""
    pl = p["plan"]
    if pl["opp_exit"] and dn_flags[pl["exit_k"]][i]:
        return "opposite_leg"
    if pl["time_stop"] is not None and p["days"] >= pl["time_stop"] and close < p["entry_price"]:
        return "time_stop"
    if pl["inact_days"] is not None and not p["partial_done"] and p["days"] >= pl["inact_days"]:
        return "inactivity"
    return None


# ----------------------------------------------------------------------------------------------
# Portfolio simulation
# ----------------------------------------------------------------------------------------------
def new_state(cash=INITIAL_CAPITAL):
    return dict(cash=cash, positions={}, pending=[], pending_exit={}, peak_eq=cash, paused_until=None)


def simulate(data: dict, cfg: Config, start=None, end=None, signals=None, check_invariants=True, size_fn=None,
             reserve: float = 0.0):
    """Fresh run, flat at the end (old interface). Returns (trades, equity, final_cash)."""
    tr, eq, cash, _ = simulate_state(data, cfg, start, end, signals, check_invariants, size_fn, reserve)
    return tr, eq, cash


def simulate_state(data: dict, cfg: Config, start=None, end=None, signals=None, check_invariants=True, size_fn=None,
                   reserve: float = 0.0, state=None, liquidate_at_end=True, policy=None, exit_fn=None):
    """size_fn(symbol, signal_date) -> size multiplier (None = 1.0).
    reserve: fraction of MTM equity that must stay in cash; slots use (1-reserve) of equity.
    state: carried portfolio state (cash, positions, pending orders, DD-pause) for continuous multi-segment runs.
    policy(symbol, signal_idx, signal_date) -> None (skip) or (score, plan) : learned entry/exit choice (Step 7);
    candidates are then ranked by score instead of 20-day change.
    exit_fn(symbol, idx, position) -> True to exit at the next open (learned exit, Step 8); checked after the
    plan's own close exits."""
    sigs = signals if signals is not None else build_signals(data, cfg)
    dates = sorted(set().union(*[set(df["timestamp"]) for df in data.values()]))
    if start is not None:
        dates = [d for d in dates if d >= pd.Timestamp(start)]
    if end is not None:
        dates = [d for d in dates if d <= pd.Timestamp(end)]
    idx = {s: dict(zip(df["timestamp"], range(len(df)))) for s, df in data.items()}
    arr = {s: {c: df[c].values for c in ("open", "high", "low", "close", "ATR_14")} for s, df in data.items()}
    base_plan = cfg.exit_plan()

    st = state if state is not None else new_state()
    cash = st["cash"]
    cash_start = cash
    flows = 0.0                       # proceeds - costs inside this run (cash conservation check)
    max_pos = cfg.max_pos
    btc_dn = btc_down_flags(data) if cfg.btc_exit else {}
    peak_eq, paused_until = st["peak_eq"], st["paused_until"]
    positions, pending, pending_exit = st["positions"], st["pending"], st["pending_exit"]
    trades, equity_rows = [], []

    def close_pos(s, raw, why, d):
        nonlocal cash, flows
        p = positions.pop(s)
        got = p["units"] * raw * (1 - FRICTION)
        cash += got
        flows += got
        p["proceeds"] += got
        p.update(exit_date=d, exit_price=raw, exit_reason=why, pnl=p["proceeds"] - p["cost"])
        trades.append(p)

    for d in dates:
        # ---------- 1. fills at the open: exits first (frees cash), then entries ----------
        for s in list(pending_exit):
            if s in positions and d in idx[s]:
                close_pos(s, arr[s]["open"][idx[s][d]], pending_exit[s], d)
            pending_exit.pop(s, None)

        mtm_equity_open = cash + sum(p["units"] * arr[s]["open"][idx[s][d]] for s, p in positions.items() if d in idx[s])
        for s, si, plan in pending:
            if s in positions or len(positions) >= max_pos or d not in idx[s]:
                continue
            i = idx[s][d]
            entry_px = arr[s]["open"][i]
            atr = arr[s]["ATR_14"][si]
            p = open_position(s, data[s]["timestamp"].iloc[si], d, entry_px, atr, sigs[s]["ref"][si], plan)
            if p is None:
                continue
            stop_dist = (entry_px - p["stop"]) / entry_px
            mult = 1.0 if size_fn is None else float(size_fn(s, data[s]["timestamp"].iloc[si]))
            if mult <= 0:
                continue
            deployable_cash = cash - reserve * mtm_equity_open
            notional = min((1 - reserve) * mtm_equity_open / max_pos * mult, RISK_CAP * mult * mtm_equity_open / stop_dist,
                           deployable_cash / (1 + FRICTION))
            if notional < 10.0:                  # Binance min-notional order size is ~5-10 USDT
                continue
            p["units"] = notional / entry_px
            p["cost"] = notional * (1 + FRICTION)
            cash -= p["cost"]
            flows -= p["cost"]
            p.update(size_mult=mult, equity_at_entry=mtm_equity_open, cash_after_entry=cash)
            positions[s] = p
        pending = []

        # ---------- 2. intraday: stop first, then partial target; end-of-day stop raises ----------
        for s in list(positions):
            if d not in idx[s]:
                continue
            i = idx[s][d]
            p = positions[s]
            fills = intraday(p, arr[s]["open"][i], arr[s]["high"][i], arr[s]["low"][i], arr[s]["close"][i],
                             sigs[s]["k2_up_ref"][i])
            for kind, raw, q in fills:
                if kind == "partial":
                    got = q * raw * (1 - FRICTION)
                    cash += got
                    flows += got
                    p["proceeds"] += got
                    p["units"] -= q
                    p.update(partial_date=d, partial_price=raw, partial_units=q)
                else:
                    close_pos(s, raw, kind, d)

        # ---------- 3. close: exit signals for tomorrow's open ----------
        for s, p in positions.items():
            if d not in idx[s]:
                continue
            i = idx[s][d]
            why = close_exit_reason(p, arr[s]["close"][i], sigs[s]["dn"] if p["plan"]["exit_k"] in sigs[s]["dn"]
                                    else {p["plan"]["exit_k"]: sigs[s]["opp"]}, i)
            if why is None and exit_fn is not None and exit_fn(s, i, p):
                why = "ai_exit"
            if why:
                pending_exit[s] = why

        if cfg.btc_exit and btc_dn.get(d, False):
            for s in positions:
                pending_exit[s] = "btc_exit"

        # ---------- 4. close: new entry signals for tomorrow's open ----------
        mtm_close = cash + sum(p["units"] * arr[s]["close"][idx[s][d]] for s, p in positions.items() if d in idx[s])
        paused = False
        if cfg.dd_pause is not None:
            if paused_until is not None and d >= paused_until:
                paused_until, peak_eq = None, mtm_close          # pause over: drawdown measured from here
            peak_eq = max(peak_eq, mtm_close)
            if paused_until is None and (peak_eq - mtm_close) / peak_eq >= cfg.dd_pause:
                paused_until = d + pd.Timedelta(days=PAUSE_DAYS)
            paused = paused_until is not None
        cands = []
        for s in data:
            if d in idx[s] and s not in positions:
                i = idx[s][d]
                if policy is not None:
                    dec = policy(s, i, d)
                    if dec is not None:
                        score, plan = dec
                        cands.append((-score, s, i, plan))
                elif sigs[s]["sig"][i]:
                    m = sigs[s]["mom"][i]
                    cands.append((-(m if not np.isnan(m) else -9), s, i, base_plan))
        cands.sort(key=lambda x: (x[0], x[1]))
        pending = [] if paused else [(s, i, plan) for _, s, i, plan in cands]

        # ---------- 5. mark to market ----------
        mtm = mtm_close
        notional_open = mtm - cash
        if check_invariants:
            assert cash >= -1e-6, f"negative cash on {d}"
            assert notional_open <= mtm + 1e-6, f"leverage on {d}"
        equity_rows.append(dict(date=d, cash=cash, equity=mtm, open_positions=len(positions), paused=paused))

    if liquidate_at_end:
        # close what is still open at the last close (marked, fee applied) so the ledger is complete
        last = dates[-1]
        for s in list(positions):
            close_pos(s, arr[s]["close"][idx[s][last]], "end_of_test", last)
        pending, pending_exit = [], {}

    st.update(cash=cash, positions=positions, pending=pending, pending_exit=pending_exit, peak_eq=peak_eq,
              paused_until=paused_until)
    tr = pd.DataFrame(trades)
    eq = pd.DataFrame(equity_rows)
    if check_invariants:
        assert abs(cash_start + flows - cash) < 1e-6, "cash conservation failed"
        if state is None and liquidate_at_end and len(tr):
            # penny check: final cash == initial + sum of trade P&L
            assert abs(INITIAL_CAPITAL + tr["pnl"].sum() - cash) < 1e-6, "cash conservation failed"
    return tr, eq, cash, st


def metrics(tr: pd.DataFrame, eq: pd.DataFrame, final_cash: float, initial: float = INITIAL_CAPITAL) -> dict:
    if eq.empty:
        return {}
    e = eq["equity"].values
    peak = np.maximum.accumulate(e)
    dd = (peak - e) / peak
    years = max((eq["date"].iloc[-1] - eq["date"].iloc[0]).days / 365.25, 1 / 365.25)
    ret = eq["equity"].pct_change().dropna()
    n = len(tr)
    wins = tr[tr["pnl"] > 0] if n else tr
    losses = tr[tr["pnl"] <= 0] if n else tr
    gl = -losses["pnl"].sum() if n else 0.0
    return dict(
        trades=n,
        win_rate=round(len(wins) / n * 100, 2) if n else 0.0,
        profit_factor=round(wins["pnl"].sum() / gl, 3) if gl > 0 else np.nan,
        final_equity=round(final_cash, 2),
        total_return_pct=round((final_cash / initial - 1) * 100, 2),
        cagr_pct=round(((final_cash / initial) ** (1 / years) - 1) * 100, 2) if final_cash > 0 else -100.0,
        max_dd_pct=round(dd.max() * 100, 2),
        sharpe=round(ret.mean() / ret.std() * np.sqrt(365), 3) if ret.std() > 0 else 0.0,
        exposure_pct=round((eq["open_positions"] > 0).mean() * 100, 1),
        avg_hold_days=round((tr["exit_date"] - tr["entry_date"]).dt.days.mean(), 1) if n else 0.0,
    )


def config_grid_3b():
    """Step 3b: Step-3 grid x risk layer (max_pos 3/5/8, dd_pause None/15%/25%, btc_exit off/on)."""
    out = []
    for c in config_grid():
        for mp, dd, bx in itertools.product([3, 5, 8], [None, 0.15, 0.25], [False, True]):
            out.append(Config(c.entry, c.param, c.regime, c.stop_atr, c.trail_atr, c.opp_exit, c.time_stop, mp, dd, bx))
    return out


def config_grid():
    entries = [("ZZ", 2.0), ("ZZ", 3.0), ("ZZ", 4.0), ("BO", 20), ("BO", 55), ("PB", 1.0), ("PB", 2.0)]
    grid = []
    for (e, p), reg, s, t, opp, ts in itertools.product(entries, [False, True], [1.5, 2.5, 3.5],
                                                         [None, 3.0, 5.0], [False, True], [None, 20]):
        grid.append(Config(e, float(p), reg, s, t, opp, ts))
    return grid


def config_grid_6():
    """Step 6 (pre-registered): new ZZ exit variants. Family A = swing exits, Family B = config.py Law #6 runner."""
    out = []
    for k in (3.0, 4.0):
        for (sm, sa), xk, be, stt, mp in itertools.product([("atr", 1.5), ("atr", 2.5), ("swing", 1.5)],
                                                          [x for x in (2.0, 3.0, 4.0) if x <= k],
                                                          [None, 2.0], [False, True], [5, 8]):
            out.append(Config("ZZ", k, True, sa, None, True, None, mp, 0.15, False,
                              exit_k=None if xk == k else xk, stop_mode=sm, be_atr=be, struct_trail=stt))
        for opp, mp, frac in itertools.product([False, True], [5, 8], [0.75, 0.5]):
            out.append(Config("ZZ", k, True, 1.5, None, opp, None, mp, 0.15, False,
                              be_atr=1.5, partial_atr=3.0, partial_frac=frac, runner_lock_atr=1.0,
                              runner_trail_atr=2.0, inact_days=14))
    return out
