"""
F7: the F2 long-short engine (f2_longshort.sim_ls, copied unchanged) plus optional risk rules for the short book:
R1 protective stop (entry x stop, checked every bar before liquidation / funding; gap -> F2 liquidation rule on the open),
R2 cooldown after a stop / liquidation, and the report-only perp-age filter. All rules off = F2 exactly (gate G0).
Protocol: logs/strategy_f7_risk/F7_PROTOCOL_PREREGISTERED.md
"""
import numpy as np
import pandas as pd

CAP = 10_000.0
MMR = 0.005                       # maintenance margin rate: liquidated when margin + units*(entry - high) <= MMR * units * high


def sim_ls(rows, grid, decide, spot, perp, funding, invest_long, invest_short, n, keep, cost_long, cost_short,
           shortable=None, stop=None, stop_slip=0.01, cooldown_days=None, min_age_days=None):
    """
    rows:     DataFrame(symbol, t, score); t = decision time (a grid point); ranked high -> low (ties by symbol).
    grid:     DatetimeIndex of bar starts; decide: bool array (decision after the bar k closes; fills at bar k+1 open).
    spot:     {sym: (o, c, last_t)} arrays aligned to grid (o filled by previous close, c forward-filled), last_t = last real bar.
    perp:     {sym: (o, h, c, first_t, last_t)} aligned to grid, NaN where the perp had no bar.
    funding:  {sym: (event_time_ns sorted, rate, price_at_event)}.
    shortable: callable(sym, t) -> bool (default: perp bar exists at t).
    """
    by_t = {t: g.sort_values(["score", "symbol"], ascending=[False, True]).symbol.values for t, g in rows.groupby("t")}
    cash, pos, sh, trades, eq = CAP, {}, {}, [], []
    sell_o, buy_o, cover_o, short_o = [], [], [], []
    liq = 0
    gt = grid.values
    n_stop, n_cool_block, n_age_block = 0, 0, 0
    last_bad = {}                                                       # sym -> time of the last stop / liquidation exit

    def sell(s, price, t, why):
        nonlocal cash
        p = pos.pop(s)
        cash += p["units"] * price * (1 - cost_long)
        trades.append(dict(side="long", symbol=s, entry_time=p["t"], exit_time=t, reason=why, cost=p["cost"],
                           pnl=p["units"] * price * (1 - cost_long) - p["cost"]))

    def cover(s, price, t, why):
        nonlocal cash
        p = sh.pop(s)
        value = p["margin"] + p["units"] * (p["entry"] - price)          # isolated margin already holds the funding
        fee = p["units"] * price * cost_short if value > 0 else 0.0
        cash += max(value, 0.0) - fee
        trades.append(dict(side="short", symbol=s, entry_time=p["t"], exit_time=t, reason=why, cost=p["margin0"] + p["fee_in"],
                           pnl=max(value, 0.0) - fee - p["margin0"] - p["fee_in"], funding=p["funding"], entry_px=p["entry"], exit_px=price))

    for k, t in enumerate(grid):
        # ---- long book (research logic, unchanged order) ----
        for s in [s for s in pos if t > spot[s][2]]:
            sell(s, float(spot[s][1][np.searchsorted(gt, spot[s][2])]), t, "data_end")
        for s in sell_o:
            if s in pos:
                sell(s, spot[s][0][k], t, "rebalance_exit")
        # ---- short book: covers at the perp open ----
        for s in [s for s in sh if t > perp[s][4]]:
            cover(s, float(perp[s][2][np.searchsorted(gt, perp[s][4])]), t, "data_end")
        for s in cover_o:
            if s in sh and np.isfinite(perp[s][0][k]):
                cover(s, perp[s][0][k], t, "rebalance_exit")
        e0 = cash + sum(p["units"] * spot[s][0][k] for s, p in pos.items()) + \
            sum(p["margin"] + p["units"] * (p["entry"] - perp[s][0][k]) for s, p in sh.items() if np.isfinite(perp[s][0][k]))
        for s in buy_o:
            if s in pos or len(pos) >= n or t > spot[s][2] or not np.isfinite(spot[s][0][k]):
                continue
            a = min(invest_long * e0 / n, cash / (1 + cost_long))
            if a < 10:
                continue
            cash -= a * (1 + cost_long)
            pos[s] = dict(units=a / spot[s][0][k], cost=a * (1 + cost_long), t=t)
        for s in short_o:
            if s in sh or len(sh) >= n or s not in perp or not np.isfinite(perp[s][0][k]) or t > perp[s][4]:
                continue
            a = min(invest_short * e0 / n, cash / (1 + cost_short))
            if a < 10:
                continue
            cash -= a * (1 + cost_short)
            sh[s] = dict(units=a / perp[s][0][k], entry=perp[s][0][k], margin=a, margin0=a, fee_in=a * cost_short, t=t, funding=0.0)
        assert cash >= -1e-6
        # ---- inside the bar: liquidation, funding ----
        t_end = gt[k + 1] if k + 1 < len(gt) else gt[k] + (gt[k] - gt[k - 1])
        for s in list(sh):
            p = sh[s]
            hi = perp[s][1][k]
            if stop is not None:
                o = perp[s][0][k]
                if np.isfinite(o) and p["margin"] + p["units"] * (p["entry"] - o) <= MMR * p["units"] * o:   # gap through the stop
                    liq += 1
                    last_bad[s] = t
                    trades.append(dict(side="short", symbol=s, entry_time=p["t"], exit_time=t, reason="liquidation_gap",
                                       cost=p["margin0"] + p["fee_in"], pnl=-p["margin0"] - p["fee_in"], funding=p["funding"],
                                       entry_px=p["entry"], exit_px=o))
                    del sh[s]
                    continue
                sp_ = p["entry"] * stop
                px_ = o * (1 + stop_slip) if np.isfinite(o) and o >= sp_ else sp_ * (1 + stop_slip) if np.isfinite(hi) and hi >= sp_ else None
                if px_ is not None:
                    n_stop += 1
                    last_bad[s] = t
                    cover(s, px_, t, "stop")
                    continue
            if np.isfinite(hi) and p["margin"] + p["units"] * (p["entry"] - hi) <= MMR * p["units"] * hi:
                liq += 1
                last_bad[s] = t
                trades.append(dict(side="short", symbol=s, entry_time=p["t"], exit_time=t, reason="liquidation",
                                   cost=p["margin0"] + p["fee_in"], pnl=-p["margin0"] - p["fee_in"], funding=p["funding"],
                                   entry_px=p["entry"], exit_px=hi))
                del sh[s]
                continue
            if s in funding:
                et, rate, px = funding[s]
                a_, b_ = np.searchsorted(et, gt[k], "left"), np.searchsorted(et, t_end, "left")
                if b_ > a_:
                    f = float((p["units"] * px[a_:b_] * rate[a_:b_]).sum())     # short receives positive funding
                    p["margin"] += f                                              # isolated: settles into the position margin
                    p["funding"] += f
        eq.append(cash + sum(p["units"] * spot[s][1][k] for s, p in pos.items()) +
                  sum(p["margin"] + p["units"] * (p["entry"] - perp[s][2][k]) for s, p in sh.items()
                      if np.isfinite(perp[s][2][k])) +
                  sum(p["margin"] for s, p in sh.items() if not np.isfinite(perp[s][2][k])))
        sell_o, buy_o, cover_o, short_o = [], [], [], []
        if not decide[k]:
            continue
        ranked = list(by_t.get(t, []))
        rank = {s: i + 1 for i, s in enumerate(ranked)}
        kept = [s for s in pos if rank.get(s, 10 ** 9) <= keep]
        sell_o = [s for s in pos if s not in kept]
        buy_o = [s for s in ranked[:n] if s not in pos][:n - len(kept)]
        if invest_short > 0:
            rev = ranked[::-1]
            shortable_now = []
            for s in rev:
                if not (shortable(s, t) if shortable else (s in perp and np.isfinite(perp[s][2][k]))):
                    continue
                if cooldown_days is not None and s in last_bad and t < last_bad[s] + pd.Timedelta(days=cooldown_days):
                    n_cool_block += 1
                    continue
                if min_age_days is not None and perp[s][3] > t - pd.Timedelta(days=min_age_days):
                    n_age_block += 1
                    continue
                shortable_now.append(s)
            rrank = {s: i + 1 for i, s in enumerate(shortable_now)}
            kept_s = [s for s in sh if rrank.get(s, 10 ** 9) <= keep]
            cover_o = [s for s in sh if s not in kept_s]
            short_o = [s for s in shortable_now[:n] if s not in sh and s not in pos][:n - len(kept_s)]
    # the decision of the last bar (not filled inside the grid) and the book before the end-of-test close: for the
    # forward logs / testnet executor only; nothing below depends on it
    pending = dict(decision_time=str(grid[-1]) if decide[len(grid) - 1] else None, sell=list(sell_o), buy=list(buy_o),
                   cover=list(cover_o), short=list(short_o),
                   longs={s: dict(units=p["units"], entry_time=str(p["t"])) for s, p in pos.items()},
                   shorts={s: dict(units=p["units"], entry=p["entry"], stop=(p["entry"] * stop if stop else None), entry_time=str(p["t"]))
                           for s, p in sh.items()},
                   cooldown={s: str(v) for s, v in last_bad.items()})
    for s in list(pos):
        sell(s, spot[s][1][len(grid) - 1], grid[-1], "end_of_test")
    for s in list(sh):
        c_ = perp[s][2][len(grid) - 1]
        cover(s, float(c_) if np.isfinite(c_) else sh[s]["entry"], grid[-1], "end_of_test")
    tr = pd.DataFrame(trades)
    if len(tr):
        assert abs(CAP + tr.pnl.sum() - cash) < 1e-6 * max(1.0, cash), (CAP + tr.pnl.sum(), cash)
    return dict(final=cash, eq=pd.Series(eq, index=grid), trades=tr, liquidations=liq, stops=n_stop,
                cooldown_blocks=n_cool_block, age_blocks=n_age_block, pending=pending)
