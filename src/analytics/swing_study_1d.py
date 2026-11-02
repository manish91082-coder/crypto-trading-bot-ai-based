"""
1D Swing Study (Step 2 of the 1D rebuild) -- research ledger, NOT a trading signal.

Objective swing definition (ATR ZigZag):
  * ATR_14 = 14-day simple mean of True Range (same formula as the 1D pipeline).
  * A pivot HIGH is confirmed on the first later day whose LOW is <= (running high - K x ATR_at_high).
  * A pivot LOW  is confirmed on the first later day whose HIGH is >= (running low + K x ATR_at_low).
  * If one candle both makes a new extreme AND crosses the reversal threshold, it only
    updates the extreme (the reversal needs a later candle) -- intrabar order is unknown.

Two kinds of columns are produced and kept strictly separate:
  * CAUSAL  : known at that day's close (pivot confirmations, days since confirmation).
  * HINDSIGHT (prefix 'HS_'): uses the future (which leg the day belongs to, leg end).
    HS_ columns are for study tables only and must never be used as model features.

Outputs (logs/swing_study_1d/):
  swing_legs_1d.csv           one row per swing leg, for K in K_LIST
  swing_daily_ledger_1d.csv   one row per coin per day (K = K_PRIMARY)
  swing_daily_market_1d.csv   one row per day across the 10 coins (K = K_PRIMARY)
  swing_summary_1d.csv        per K / coin / period / direction statistics
  SWING_STUDY_1D.xlsx         the same tables in one workbook
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, LOGS_DIR, SYMBOLS, BINANCE_TAKER_FEE

K_LIST = [2.0, 3.0, 4.0]
K_PRIMARY = 3.0
RESEARCH_END = pd.Timestamp("2024-12-31")  # data now starts 2020-01-01 (SOL 2020-08-11, DOT 2020-08-18)
OUT_DIR = LOGS_DIR / "swing_study_1d"
ANOMALY_WICK_PCT = 99.0   # wick > 99% beyond the body = bad print (e.g. LINKUSDT 2020-03-12 low 0.0001)
ANOMALIES = []
# Step 6.0 fix: when a confirmed swing FAILS, emit a 'flip' event in the new direction (the old code flipped the
# internal trend silently, so the causal state stayed in the old direction). False = exact old behaviour.
EMIT_FLIP_EVENTS = True


def load_1d(symbol: str, path=None) -> pd.DataFrame:
    df = pd.read_csv(path or DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    # Zero-trust pre-flight: crash loudly on bad data
    assert df["timestamp"].is_unique, f"{symbol}: duplicate timestamps"
    gaps = df["timestamp"].diff().dropna()
    assert (gaps == pd.Timedelta(days=1)).all(), f"{symbol}: calendar gaps present"
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all(), f"{symbol}: high < max(open,close)"
    assert (df["low"] <= df[["open", "close"]].min(axis=1)).all(), f"{symbol}: low > min(open,close)"
    # Bad-print guard: a wick more than ANOMALY_WICK_PCT beyond the candle body is treated as an
    # untradable print for this study (raw file untouched; every clipped candle is logged).
    body_lo = df[["open", "close"]].min(axis=1)
    body_hi = df[["open", "close"]].max(axis=1)
    bad_lo = (1 - df["low"] / body_lo) * 100 > ANOMALY_WICK_PCT
    bad_hi = (df["high"] / body_hi - 1) * 100 > ANOMALY_WICK_PCT
    for i in df.index[bad_lo | bad_hi]:
        ANOMALIES.append(dict(symbol=symbol, date=df.at[i, "timestamp"].date(), open=df.at[i, "open"],
                              high=df.at[i, "high"], low=df.at[i, "low"], close=df.at[i, "close"],
                              action=("low->body " if bad_lo[i] else "") + ("high->body" if bad_hi[i] else "")))
    df.loc[bad_lo, "low"] = body_lo[bad_lo]
    df.loc[bad_hi, "high"] = body_hi[bad_hi]
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    df["ATR_14"] = tr.rolling(14).mean()
    return df


def candle_ticks(df: pd.DataFrame):
    """
    Turn every daily candle into an ordered 4-tick path (standard OHLC path convention):
      bullish/flat candle (close >= open): open -> low  -> high -> close
      bearish candle      (close <  open): open -> high -> low  -> close
    This makes one sequential price series, so the ZigZag never has to guess the
    order of a candle's high and low (outside candles are handled consistently).
    """
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    bull = c >= o
    first = np.where(bull, l, h)
    second = np.where(bull, h, l)
    prices = np.column_stack([o, first, second, c]).ravel()
    candle = np.repeat(np.arange(len(df)), 4)
    return prices, candle


def zigzag_pivots(df: pd.DataFrame, k: float, events: list = None) -> list:
    """
    ATR ZigZag on the 4-tick path. Returns final pivots:
      dict(idx=candle index, tick, kind 'H'/'L', price, confirm_idx=candle of confirmation, ev)
    A reversal is confirmed when price moves K x ATR_14 (ATR of the pivot candle) against the
    running extreme. If price breaks beyond the pivot that STARTED the current leg without such a
    reversal, that start confirmation was a false signal: it is removed (failed=True) and the
    previous leg is extended -- unless the current leg already exceeded the previous swing, in
    which case its extreme is kept as a swing point.
    Every real-time confirmation is appended to `events` (with its later 'failed' outcome).
    """
    p, cnd = candle_ticks(df)
    atr = df["ATR_14"].values
    first_valid = int(np.argmax(~np.isnan(atr)))
    pivots = []
    if events is None:
        events = []

    def thr(t):
        return k * atr[cnd[t]]

    def flip(kind, t, fallback_t):
        # causal real-time event: the previous leg resumed; ref = the pivot that started that resumed leg
        if EMIT_FLIP_EVENTS:
            ref = pivots[-1]["price"] if pivots else float(p[fallback_t])
            events.append(dict(confirm_idx=int(cnd[t]), kind=kind, pivot_idx=int(cnd[t]), failed=False,
                               ref_price=float(ref), flip=True, seq=len(events)))

    def add(t, kind, conf_t):
        events.append(dict(confirm_idx=int(cnd[conf_t]), kind=kind, pivot_idx=int(cnd[t]), failed=False,
                           ref_price=float(p[t]), flip=False, seq=len(events)))
        pivots.append(dict(idx=int(cnd[t]), tick=t, kind=kind, price=float(p[t]),
                           confirm_idx=int(cnd[conf_t]), ev=len(events) - 1))

    t0 = first_valid * 4
    trend, hi_t, lo_t = 0, t0, t0
    for t in range(t0 + 1, len(p)):
        x = p[t]
        if trend == 0:
            if x > p[hi_t]:
                hi_t = t
            if x < p[lo_t]:
                lo_t = t
            if lo_t < t and x >= p[lo_t] + thr(lo_t):
                add(lo_t, "L", t)
                trend, hi_t = 1, t
            elif hi_t < t and x <= p[hi_t] - thr(hi_t):
                add(hi_t, "H", t)
                trend, lo_t = -1, t
        elif trend == 1:
            if x > p[hi_t]:
                hi_t = t
            elif x <= p[hi_t] - thr(hi_t):
                add(hi_t, "H", t)
                trend, lo_t = -1, t
            elif pivots and x < pivots[-1]["price"]:
                if len(pivots) >= 2 and p[hi_t] > pivots[-2]["price"]:
                    add(hi_t, "H", t)          # leg made a higher high -> keep it as a swing high
                else:
                    events[pivots.pop()["ev"]]["failed"] = True   # false up-leg signal
                    flip("H", t, hi_t)
                trend, lo_t = -1, t
        else:  # trend == -1
            if x < p[lo_t]:
                lo_t = t
            elif x >= p[lo_t] + thr(lo_t):
                add(lo_t, "L", t)
                trend, hi_t = 1, t
            elif pivots and x > pivots[-1]["price"]:
                if len(pivots) >= 2 and p[lo_t] < pivots[-2]["price"]:
                    add(lo_t, "L", t)          # leg made a lower low -> keep it as a swing low
                else:
                    events[pivots.pop()["ev"]]["failed"] = True   # false down-leg signal
                    flip("L", t, lo_t)
                trend, hi_t = 1, t
    return pivots


def verify_pivots(df: pd.DataFrame, pivots: list, symbol: str, k: float):
    """
    Independent check on the same tick path: pivots alternate, are in time order, and every
    leg runs exactly from the lowest to the highest tick between its two pivots.
    """
    p, _ = candle_ticks(df)
    for a, b in zip(pivots, pivots[1:]):
        assert a["kind"] != b["kind"], f"{symbol} K={k}: pivots do not alternate"
        assert b["tick"] > a["tick"], f"{symbol} K={k}: pivots not in time order"
        seg = p[a["tick"]:b["tick"] + 1]
        lo, hi = (a, b) if b["kind"] == "H" else (b, a)
        assert np.isclose(seg.max(), hi["price"]), f"{symbol} K={k}: swing high is not the leg maximum"
        assert np.isclose(seg.min(), lo["price"]), f"{symbol} K={k}: swing low is not the leg minimum"
        assert a["confirm_idx"] >= a["idx"], f"{symbol} K={k}: confirmation before pivot"
    tick_names = np.array(["open", "first", "second", "close"])
    for a in pivots:
        # the pivot must be one of that candle's own OHLC prices (tick position tells which)
        assert np.isclose(p[a["tick"]], a["price"]) and a["tick"] // 4 == a["idx"], f"{symbol} K={k}: pivot/tick mismatch"
        pos = tick_names[a["tick"] % 4]
        bull = df.at[a["idx"], "close"] >= df.at[a["idx"], "open"]
        if pos == "first":
            pos = "low" if bull else "high"
        elif pos == "second":
            pos = "high" if bull else "low"
        a["pivot_at"] = pos


def build_legs(df: pd.DataFrame, pivots: list, symbol: str, k: float) -> pd.DataFrame:
    rows = []
    fee_rt = 2 * BINANCE_TAKER_FEE
    for a, b in zip(pivots, pivots[1:]):
        direction = "Up" if a["kind"] == "L" else "Down"
        sign = 1 if direction == "Up" else -1
        move_pct = sign * (b["price"] / a["price"] - 1) * 100
        # Tradable view: you only KNOW the leg started on a's confirmation day -> enter next day's open
        entry_i = a["confirm_idx"] + 1
        exit_i = b["confirm_idx"] + 1  # follow-the-zigzag exit: next open after the opposite pivot is confirmed
        tradable = entry_i < len(df) and entry_i <= b["idx"]
        row = dict(
            K=k, symbol=symbol, direction=direction,
            start_date=df.at[a["idx"], "timestamp"].date(), end_date=df.at[b["idx"], "timestamp"].date(),
            start_price=a["price"], end_price=b["price"],
            duration_days=b["idx"] - a["idx"],
            start_pivot_at=a.get("pivot_at", ""),
            move_pct=round(move_pct, 3),
            move_in_atr=round(abs(b["price"] - a["price"]) / df.at[a["idx"], "ATR_14"], 2),
            start_confirmed_date=df.at[a["confirm_idx"], "timestamp"].date(),
            confirm_lag_days=a["confirm_idx"] - a["idx"],
            period="Research" if df.at[a["idx"], "timestamp"] <= RESEARCH_END else "Vault_2025_2026",
            tradable_after_confirm=tradable,
        )
        if tradable:
            e = df.at[entry_i, "open"]
            row["entry_next_open_after_confirm"] = e
            row["best_capture_pct"] = round(sign * (b["price"] / e - 1) * 100, 3)  # perfect exit at pivot (hindsight)
            if exit_i < len(df):
                x = df.at[exit_i, "open"]
                row["zigzag_exit_price"] = x
                row["zigzag_capture_net_pct"] = round(sign * (x / e - 1) * 100 - fee_rt * 100, 3)
            seg = df.iloc[entry_i:b["idx"] + 1]
            adverse = (seg["low"].min() / e - 1) * 100 if sign == 1 else -(seg["high"].max() / e - 1) * 100
            row["max_adverse_from_entry_pct"] = round(min(0.0, adverse), 3)
            row["share_of_leg_left_after_confirm"] = round(row["best_capture_pct"] / move_pct, 3) if move_pct else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def build_daily_ledger(df: pd.DataFrame, pivots: list, events: list, symbol: str) -> pd.DataFrame:
    d = df[["timestamp", "open", "high", "low", "close", "volume", "ATR_14"]].copy()
    d.insert(0, "symbol", symbol)
    d["ret_1d_pct"] = d["close"].pct_change() * 100
    d["ATR_pct"] = d["ATR_14"] / d["close"] * 100
    n = len(d)
    # CAUSAL columns
    d["confirmed_pivot_today"] = ""
    d["last_confirmed_leg"] = ""
    d["days_since_last_confirm"] = np.nan
    # every real-time confirmation (including ones that later failed) is causal information
    d["HS_confirm_later_failed"] = ""
    for e in events:
        d.at[e["confirm_idx"], "confirmed_pivot_today"] = "Low->Up leg" if e["kind"] == "L" else "High->Down leg"
        d.at[e["confirm_idx"], "HS_confirm_later_failed"] = "FAILED" if e["failed"] else "held"
    last_dir, last_c = "", None
    cmap = {e["confirm_idx"]: ("Up" if e["kind"] == "L" else "Down") for e in events}
    for i in range(n):
        if i in cmap:
            last_dir, last_c = cmap[i], i
        d.at[i, "last_confirmed_leg"] = last_dir
        if last_c is not None:
            d.at[i, "days_since_last_confirm"] = i - last_c
    # HINDSIGHT columns
    d["HS_is_pivot"] = ""
    d["HS_leg_direction"] = ""
    d["HS_leg_id"] = np.nan
    d["HS_day_in_leg"] = np.nan
    d["HS_leg_length_days"] = np.nan
    d["HS_leg_move_pct"] = np.nan
    for p in pivots:
        d.at[p["idx"], "HS_is_pivot"] = "SwingHigh" if p["kind"] == "H" else "SwingLow"
    for leg_id, (a, b) in enumerate(zip(pivots, pivots[1:])):
        direction = "Up" if a["kind"] == "L" else "Down"
        span = range(a["idx"], b["idx"])
        d.loc[list(span), "HS_leg_direction"] = direction
        d.loc[list(span), "HS_leg_id"] = leg_id
        d.loc[list(span), "HS_day_in_leg"] = [i - a["idx"] for i in span]
        d.loc[list(span), "HS_leg_length_days"] = b["idx"] - a["idx"]
        d.loc[list(span), "HS_leg_move_pct"] = round((b["price"] / a["price"] - 1) * 100, 3)
    d["period"] = np.where(d["timestamp"] <= RESEARCH_END, "Research", "Vault_2025_2026")
    return d


def summarize(legs: pd.DataFrame) -> pd.DataFrame:
    g = legs.groupby(["K", "symbol", "period", "direction"])
    s = g.agg(
        legs=("move_pct", "size"),
        avg_move_pct=("move_pct", "mean"),
        median_move_pct=("move_pct", "median"),
        avg_duration_days=("duration_days", "mean"),
        avg_confirm_lag_days=("confirm_lag_days", "mean"),
        tradable_legs=("tradable_after_confirm", "sum"),
        avg_best_capture_pct=("best_capture_pct", "mean"),
        avg_zigzag_capture_net_pct=("zigzag_capture_net_pct", "mean"),
        zigzag_win_rate=("zigzag_capture_net_pct", lambda x: (x.dropna() > 0).mean()),
        avg_share_left_after_confirm=("share_of_leg_left_after_confirm", "mean"),
    ).round(3).reset_index()
    return s


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_legs, daily, event_log = [], [], []
    for sym in SYMBOLS:
        df = load_1d(sym)
        for k in K_LIST:
            events = []
            piv = zigzag_pivots(df, k, events)
            verify_pivots(df, piv, sym, k)
            legs_k = build_legs(df, piv, sym, k)
            legs_k["failed_confirms_in_series"] = sum(e["failed"] for e in events)
            all_legs.append(legs_k)
            event_log.append(pd.DataFrame([dict(K=k, symbol=sym, confirm_date=df.at[e["confirm_idx"], "timestamp"].date(),
                                                pivot_date=df.at[e["pivot_idx"], "timestamp"].date(), kind=e["kind"],
                                                failed=e["failed"]) for e in events]))
            if k == K_PRIMARY:
                daily.append(build_daily_ledger(df, piv, events, sym))
        print(f"[OK] {sym}: {len(df)} days {df['timestamp'].min().date()} -> {df['timestamp'].max().date()} | pivots verified for K={K_LIST}")

    legs = pd.concat(all_legs, ignore_index=True)
    ledger = pd.concat(daily, ignore_index=True)
    summary = summarize(legs)

    # Market-wide daily view (K_PRIMARY)
    mkt = ledger.groupby("timestamp").agg(
        coins=("symbol", "size"),
        causal_up_legs=("last_confirmed_leg", lambda x: (x == "Up").sum()),
        causal_down_legs=("last_confirmed_leg", lambda x: (x == "Down").sum()),
        new_up_confirms=("confirmed_pivot_today", lambda x: (x == "Low->Up leg").sum()),
        new_down_confirms=("confirmed_pivot_today", lambda x: (x == "High->Down leg").sum()),
        HS_swing_lows_today=("HS_is_pivot", lambda x: (x == "SwingLow").sum()),
        HS_swing_highs_today=("HS_is_pivot", lambda x: (x == "SwingHigh").sum()),
        HS_coins_in_up_leg=("HS_leg_direction", lambda x: (x == "Up").sum()),
        HS_coins_in_down_leg=("HS_leg_direction", lambda x: (x == "Down").sum()),
    ).reset_index()

    pd.DataFrame(ANOMALIES).to_csv(OUT_DIR / "data_anomalies_clipped_1d.csv", index=False)
    print(f"Bad-print candles clipped for this study: {len(ANOMALIES)} -> {ANOMALIES}")
    ev = pd.concat(event_log, ignore_index=True)
    ev.to_csv(OUT_DIR / "swing_confirmation_events_1d.csv", index=False)
    print("\nReal-time confirmations and how many later FAILED (false signals):")
    print(ev.groupby("K")["failed"].agg(confirmations="size", failed="sum", failed_rate="mean").round(3).to_string())
    legs.to_csv(OUT_DIR / "swing_legs_1d.csv", index=False)
    ledger.to_csv(OUT_DIR / "swing_daily_ledger_1d.csv", index=False)
    mkt.to_csv(OUT_DIR / "swing_daily_market_1d.csv", index=False)
    summary.to_csv(OUT_DIR / "swing_summary_1d.csv", index=False)
    with pd.ExcelWriter(OUT_DIR / "SWING_STUDY_1D.xlsx", engine="openpyxl") as w:
        summary.to_excel(w, sheet_name="Summary", index=False)
        ev.to_excel(w, sheet_name="Confirmation_Events", index=False)
        legs.to_excel(w, sheet_name="Swing_Legs", index=False)
        mkt.to_excel(w, sheet_name="Daily_Market", index=False)
        ledger.to_excel(w, sheet_name="Daily_Ledger_All_Coins", index=False)

    # Console overview (all coins pooled)
    pool = legs.groupby(["K", "period", "direction"]).agg(
        legs=("move_pct", "size"), avg_move_pct=("move_pct", "mean"), avg_days=("duration_days", "mean"),
        avg_lag=("confirm_lag_days", "mean"), avg_best_capture=("best_capture_pct", "mean"),
        avg_zigzag_net=("zigzag_capture_net_pct", "mean"),
        zigzag_wr=("zigzag_capture_net_pct", lambda x: (x.dropna() > 0).mean()),
    ).round(2)
    print("\n" + pool.to_string())
    print(f"\nSaved to {OUT_DIR}")


if __name__ == "__main__":
    main()
