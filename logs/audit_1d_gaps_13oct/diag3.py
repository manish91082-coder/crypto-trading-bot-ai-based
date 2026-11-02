import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(r"E:\crypto trading bot ai based 9 oct 2026")
for p in ("src","src/pipeline_1d","src/analytics","src/execution"): sys.path.insert(0, str(ROOT/p))
import swing_strategy_1d as E, swing_study_1d as SS, live_1d_swing_engine as L
from config import SYMBOLS
print("SYMBOLS", SYMBOLS)
data = E.load_universe()
OUT = Path(__file__).parent
# 1) failed-confirmation state bug: after a popped pivot the internal trend flips but no event is emitted,
#    so the causal 'state' used by the BTC regime keeps the OLD direction.
def stale_days(df, k, kind_failed):
    ev = []; SS.zigzag_pivots(df, k, ev)
    up, dn, state = E.zigzag_event_flags(df, k)
    rows = []
    evs = sorted(ev, key=lambda e: e["confirm_idx"])
    for j, e in enumerate(evs):
        if not e["failed"] or e["kind"] != kind_failed: continue
        nxt = next((x["confirm_idx"] for x in evs[j+1:]), len(df)-1)
        # the failure moment = first day price crossed back through the pivot price after confirmation
        piv = df["low"].values[e["pivot_idx"]] if kind_failed == "L" else df["high"].values[e["pivot_idx"]]
        seg = range(e["confirm_idx"]+1, nxt+1)
        fail_day = next((i for i in seg if (df["low"].values[i] < piv if kind_failed=="L" else df["high"].values[i] > piv)), None)
        rows.append(dict(confirm=df.timestamp.iloc[e["confirm_idx"]].date(), fail_day=None if fail_day is None else df.timestamp.iloc[fail_day].date(),
                         next_event=df.timestamp.iloc[nxt].date(), stale_days=None if fail_day is None else nxt-fail_day,
                         move_after_fail_pct=None if fail_day is None else round((df.close.values[nxt]/df.close.values[fail_day]-1)*100,1)))
    return pd.DataFrame(rows)
print("\n[BTC K3] failed UP confirmations -> regime stays 'UP' while BTC is below the swing low:")
print(stale_days(data["BTCUSDT"], 3.0, "L").to_string(index=False))
print("\n[coins K4] failed DOWN confirmations -> price broke ABOVE the prior swing high but no UP event is emitted (missed entry):")
for s in SYMBOLS:
    d = stale_days(data[s], 4.0, "H")
    if len(d): print(s); print(d.to_string(index=False))
# 2) entry signals in 2023-26 that were NOT traded and why
cfg = L.CFG
sigs = E.build_signals(data, cfg)
cfg_noreg = E.Config(cfg.entry, cfg.param, False, cfg.stop_atr, cfg.trail_atr, cfg.opp_exit, cfg.time_stop, cfg.max_pos, cfg.dd_pause, cfg.btc_exit)
raw = E.build_signals(data, cfg_noreg)
tr = pd.read_csv(OUT/"cont_2023_26_trades.csv", parse_dates=["signal_date"])
legs = pd.read_csv(ROOT/"logs/swing_study_1d/swing_legs_1d.csv", parse_dates=["start_confirmed_date"])
L4 = legs[(legs.K==4.0)&(legs.direction=="Up")].set_index(["symbol","start_confirmed_date"])
rows=[]
for s in SYMBOLS:
    df = data[s]
    for i in np.where(raw[s]["sig"])[0]:
        d = df.timestamp.iloc[i]
        if d < pd.Timestamp("2023-01-01") or d > pd.Timestamp("2026-09-29"): continue
        st = "traded" if ((tr.symbol==s)&(tr.signal_date==d)).any() else ("blocked_by_BTC_regime" if not sigs[s]["sig"][i] else "not_filled(slots/pause/in_pos)")
        z = L4.loc[(s,d),"zigzag_capture_net_pct"] if (s,d) in L4.index else np.nan
        rows.append(dict(symbol=s, signal=d.date(), status=st, standalone_leg_trade_net_pct=z))
r = pd.DataFrame(rows)
print("\n2023-26 K4 up-confirmations:", len(r))
print(r.groupby("status").standalone_leg_trade_net_pct.agg(["size","count","mean","median"]).round(2))
r.to_csv(OUT/"signals_2023_26_status.csv", index=False)
