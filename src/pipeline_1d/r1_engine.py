"""
Round 1 engine: the F7 engine (f7_risk.sim_ls) copied, plus optional hooks. Protocol:
logs/research_r1/R1_PROTOCOL_PREREGISTERED.md. With every hook off it must reproduce F7 exactly (gate G0).
Hooks:
  hedge_w / freed_to_hedge   E1 / E2: BTCUSDT perp short hedge (notional = frac x invest_short x equity), stop x stop,
                             re-set at a decision when its notional drifts > hedge_drift from target, no cooldown.
  short_order(t, shortable, ranked, k) -> list   E2 filter / E3 / N1b / controls: reorder or filter the short candidates.
  long_block(t, ranked, k) -> set                N1: members not eligible for NEW long entries.
  weight_fn(side, t, targets, k) -> {sym: w}     E4: weights of the target set (kept + new) inside a leg.
  long_perp_ok(s, t, k) -> bool                  E11: open a NEW long on the perp (cost_short, funding paid, liquidation
                             on the bar low via perp_low) instead of spot.
"""
import numpy as np
import pandas as pd

CAP = 10_000.0
MMR = 0.005


def sim_ls(rows, grid, decide, spot, perp, funding, invest_long, invest_short, n, keep, cost_long, cost_short,
           shortable=None, stop=None, stop_slip=0.01, cooldown_days=None, min_age_days=None,
           hedge_w=0.0, hedge_sym="BTCUSDT", hedge_drift=0.25, freed_to_hedge=False,
           short_order=None, long_block=None, weight_fn=None, long_perp_ok=None, perp_low=None):
    by_t = {t: g.sort_values(["score", "symbol"], ascending=[False, True]).symbol.values for t, g in rows.groupby("t")}
    cash, pos, sh, trades, eq = CAP, {}, {}, [], []
    sell_o, buy_o, cover_o, short_o = [], [], [], []
    liq = 0
    gt = grid.values
    n_stop, n_cool_block, n_age_block = 0, 0, 0
    last_bad = {}
    hedge = None                                  # dict like a short position, on hedge_sym
    h_close_o, h_open_frac = False, None          # pending hedge orders (filled at the next bar open)
    n_hedge_stop, n_long_blocked, n_perp_longs, n_spot_longs = 0, 0, 0, 0
    alt_frac = 1.0 - hedge_w
    s_pnl = np.zeros(len(grid))                   # short book + hedge: mark-to-market P&L per bar (fees and funding included)
    s_prev = {}                                   # id(position) -> value at the previous mark

    def sell(s, price, t, why):
        nonlocal cash
        p = pos.pop(s)
        if p.get("venue") == "perp":
            value = p["margin"] + p["units"] * (price - p["entry"])
            fee = p["units"] * price * cost_short if value > 0 else 0.0
            cash += max(value, 0.0) - fee
            trades.append(dict(side="long", venue="perp", symbol=s, entry_time=p["t"], exit_time=t, reason=why,
                               cost=p["margin0"] + p["fee_in"], pnl=max(value, 0.0) - fee - p["margin0"] - p["fee_in"],
                               funding=p["funding"], entry_px=p["entry"], exit_px=price))
            return
        cash += p["units"] * price * (1 - cost_long)
        trades.append(dict(side="long", symbol=s, entry_time=p["t"], exit_time=t, reason=why, cost=p["cost"],
                           pnl=p["units"] * price * (1 - cost_long) - p["cost"]))

    def close_short(p, price, t, why, side, s):
        nonlocal cash
        value = p["margin"] + p["units"] * (p["entry"] - price)
        fee = p["units"] * price * cost_short if value > 0 else 0.0
        cash += max(value, 0.0) - fee
        s_pnl[min(np.searchsorted(gt, np.datetime64(t)), len(gt) - 1)] += max(value, 0.0) - fee - s_prev.pop(id(p), p["margin0"])
        trades.append(dict(side=side, symbol=s, entry_time=p["t"], exit_time=t, reason=why, cost=p["margin0"] + p["fee_in"],
                           pnl=max(value, 0.0) - fee - p["margin0"] - p["fee_in"], funding=p["funding"], entry_px=p["entry"], exit_px=price))

    def cover(s, price, t, why):
        close_short(sh.pop(s), price, t, why, "short", s)

    def open_short(s, a, k, t):
        nonlocal cash
        cash -= a * (1 + cost_short)
        s_pnl[k] -= a * cost_short                 # entry fee
        return dict(units=a / perp[s][0][k], entry=perp[s][0][k], margin=a, margin0=a, fee_in=a * cost_short, t=t, funding=0.0)

    def mark_long(s, p, i, which):
        if p.get("venue") == "perp":
            px_ = perp[s][which][i]
            return p["margin"] + p["units"] * (px_ - p["entry"]) if np.isfinite(px_) else p["margin"]
        return p["units"] * spot[s][1 if which == 2 else 0][i]

    def short_bar(p, s, k, t, side):
        """stop / liquidation / funding inside bar k for a short-type position. Returns a reason if it was closed."""
        nonlocal liq, n_stop, n_hedge_stop, cash
        hi = perp[s][1][k]
        t_end = gt[k + 1] if k + 1 < len(gt) else gt[k] + (gt[k] - gt[k - 1])
        if stop is not None:
            o = perp[s][0][k]
            if np.isfinite(o) and p["margin"] + p["units"] * (p["entry"] - o) <= MMR * p["units"] * o:
                liq += 1
                s_pnl[k] -= s_prev.pop(id(p), p["margin0"])
                trades.append(dict(side=side, symbol=s, entry_time=p["t"], exit_time=t, reason="liquidation_gap",
                                   cost=p["margin0"] + p["fee_in"], pnl=-p["margin0"] - p["fee_in"], funding=p["funding"],
                                   entry_px=p["entry"], exit_px=o))
                return "liq"
            sp_ = p["entry"] * stop
            px_ = o * (1 + stop_slip) if np.isfinite(o) and o >= sp_ else sp_ * (1 + stop_slip) if np.isfinite(hi) and hi >= sp_ else None
            if px_ is not None:
                if side == "hedge":
                    n_hedge_stop += 1
                else:
                    n_stop += 1
                close_short(p, px_, t, "stop", side, s)
                return "stop"
        if np.isfinite(hi) and p["margin"] + p["units"] * (p["entry"] - hi) <= MMR * p["units"] * hi:
            liq += 1
            s_pnl[k] -= s_prev.pop(id(p), p["margin0"])
            trades.append(dict(side=side, symbol=s, entry_time=p["t"], exit_time=t, reason="liquidation",
                               cost=p["margin0"] + p["fee_in"], pnl=-p["margin0"] - p["fee_in"], funding=p["funding"],
                               entry_px=p["entry"], exit_px=hi))
            return "liq"
        if s in funding:
            et, rate, px = funding[s]
            a_, b_ = np.searchsorted(et, gt[k], "left"), np.searchsorted(et, t_end, "left")
            if b_ > a_:
                f = float((p["units"] * px[a_:b_] * rate[a_:b_]).sum())
                p["margin"] += f
                p["funding"] += f
        return None

    for k, t in enumerate(grid):
        # ---- long book ----
        for s in [s for s in pos if (pos[s].get("venue") != "perp" and t > spot[s][2]) or (pos[s].get("venue") == "perp" and t > perp[s][4])]:
            if pos[s].get("venue") == "perp":
                sell(s, float(perp[s][2][np.searchsorted(gt, perp[s][4])]), t, "data_end")
            else:
                sell(s, float(spot[s][1][np.searchsorted(gt, spot[s][2])]), t, "data_end")
        for s in sell_o:
            if s in pos:
                if pos[s].get("venue") == "perp":
                    if np.isfinite(perp[s][0][k]):
                        sell(s, perp[s][0][k], t, "rebalance_exit")
                else:
                    sell(s, spot[s][0][k], t, "rebalance_exit")
        # ---- short book ----
        for s in [s for s in sh if t > perp[s][4]]:
            cover(s, float(perp[s][2][np.searchsorted(gt, perp[s][4])]), t, "data_end")
        for s in cover_o:
            if s in sh and np.isfinite(perp[s][0][k]):
                cover(s, perp[s][0][k], t, "rebalance_exit")
        # ---- hedge close ----
        if hedge is not None and t > perp[hedge_sym][4]:
            close_short(hedge, float(perp[hedge_sym][2][np.searchsorted(gt, perp[hedge_sym][4])]), t, "data_end", "hedge", hedge_sym)
            hedge = None
        if h_close_o and hedge is not None and np.isfinite(perp[hedge_sym][0][k]):
            close_short(hedge, perp[hedge_sym][0][k], t, "hedge_reset", "hedge", hedge_sym)
            hedge = None
        e0 = cash + sum(mark_long(s, p, k, 0) for s, p in pos.items()) + \
            sum(p["margin"] + p["units"] * (p["entry"] - perp[s][0][k]) for s, p in sh.items() if np.isfinite(perp[s][0][k]))
        if hedge is not None and np.isfinite(perp[hedge_sym][0][k]):
            e0 += hedge["margin"] + hedge["units"] * (hedge["entry"] - perp[hedge_sym][0][k])
        wl = weight_fn("long", t, list(pos) + list(buy_o), k) if (weight_fn and buy_o) else None
        for s in buy_o:
            if s in pos or len(pos) >= n:
                continue
            use_perp = bool(long_perp_ok and s in perp and np.isfinite(perp[s][0][k]) and t <= perp[s][4] and long_perp_ok(s, t, k))
            if not use_perp and (t > spot[s][2] or not np.isfinite(spot[s][0][k])):
                continue
            budget = invest_long * e0 * wl[s] if wl else invest_long * e0 / n
            if use_perp:
                a = min(budget, cash / (1 + cost_short))
                if a < 10:
                    continue
                cash -= a * (1 + cost_short)
                pos[s] = dict(units=a / perp[s][0][k], entry=perp[s][0][k], margin=a, margin0=a, fee_in=a * cost_short, t=t,
                              funding=0.0, venue="perp")
                n_perp_longs += 1
            else:
                a = min(budget, cash / (1 + cost_long))
                if a < 10:
                    continue
                cash -= a * (1 + cost_long)
                pos[s] = dict(units=a / spot[s][0][k], cost=a * (1 + cost_long), t=t)
                n_spot_longs += 1
        ws = weight_fn("short", t, list(sh) + list(short_o), k) if (weight_fn and short_o) else None
        for s in short_o:
            if s in sh or len(sh) >= n or s not in perp or not np.isfinite(perp[s][0][k]) or t > perp[s][4]:
                continue
            budget = invest_short * alt_frac * e0 * ws[s] if ws else invest_short * alt_frac * e0 / n
            a = min(budget, cash / (1 + cost_short))
            if a < 10:
                continue
            sh[s] = open_short(s, a, k, t)
        if h_open_frac is not None and hedge is None and h_open_frac > 0 and np.isfinite(perp[hedge_sym][0][k]) and t <= perp[hedge_sym][4]:
            a = min(invest_short * h_open_frac * e0, cash / (1 + cost_short))
            if a >= 10:
                hedge = open_short(hedge_sym, a, k, t)
                hedge["frac"] = h_open_frac
        assert cash >= -1e-6
        # ---- inside the bar ----
        t_end = gt[k + 1] if k + 1 < len(gt) else gt[k] + (gt[k] - gt[k - 1])
        for s in list(sh):
            r = short_bar(sh[s], s, k, t, "short")
            if r is not None:
                last_bad[s] = t
                del sh[s]
        if hedge is not None:
            if short_bar(hedge, hedge_sym, k, t, "hedge") is not None:
                hedge = None
        for s in [s for s in pos if pos[s].get("venue") == "perp"]:
            p = pos[s]
            lo = perp_low[s][k] if perp_low is not None and s in perp_low else np.nan
            if np.isfinite(lo) and p["margin"] + p["units"] * (lo - p["entry"]) <= MMR * p["units"] * lo:
                liq += 1
                trades.append(dict(side="long", venue="perp", symbol=s, entry_time=p["t"], exit_time=t, reason="liquidation",
                                   cost=p["margin0"] + p["fee_in"], pnl=-p["margin0"] - p["fee_in"], funding=p["funding"],
                                   entry_px=p["entry"], exit_px=lo))
                del pos[s]
                continue
            if s in funding:
                et, rate, px = funding[s]
                a_, b_ = np.searchsorted(et, gt[k], "left"), np.searchsorted(et, t_end, "left")
                if b_ > a_:
                    f = float((p["units"] * px[a_:b_] * rate[a_:b_]).sum())     # a long PAYS positive funding
                    p["margin"] -= f
                    p["funding"] -= f
        e_close = cash + sum(mark_long(s, p, k, 2) for s, p in pos.items()) + \
            sum(p["margin"] + p["units"] * (p["entry"] - perp[s][2][k]) for s, p in sh.items() if np.isfinite(perp[s][2][k])) + \
            sum(p["margin"] for s, p in sh.items() if not np.isfinite(perp[s][2][k]))
        if hedge is not None:
            c_h = perp[hedge_sym][2][k]
            e_close += hedge["margin"] + hedge["units"] * (hedge["entry"] - c_h) if np.isfinite(c_h) else hedge["margin"]
        for p_, s_ in [(p, s) for s, p in sh.items()] + ([(hedge, hedge_sym)] if hedge is not None else []):
            c_ = perp[s_][2][k]
            v_ = p_["margin"] + p_["units"] * (p_["entry"] - c_) if np.isfinite(c_) else p_["margin"]
            s_pnl[k] += v_ - s_prev.get(id(p_), p_["margin0"])
            s_prev[id(p_)] = v_
        eq.append(e_close)
        sell_o, buy_o, cover_o, short_o = [], [], [], []
        h_close_o, h_open_frac = False, None
        if not decide[k]:
            continue
        ranked = list(by_t.get(t, []))
        rank = {s: i + 1 for i, s in enumerate(ranked)}
        kept = [s for s in pos if rank.get(s, 10 ** 9) <= keep]
        sell_o = [s for s in pos if s not in kept]
        blocked = long_block(t, ranked, k) if long_block else set()
        n_long_blocked += sum(1 for s in ranked[:n] if s in blocked and s not in pos)
        elig = [s for s in ranked if s not in blocked]
        buy_o = [s for s in elig[:n] if s not in pos][:n - len(kept)]
        n_alt_target = n if alt_frac > 0 else 0
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
            if short_order:
                shortable_now = list(short_order(t, shortable_now, ranked, k))
            rrank = {s: i + 1 for i, s in enumerate(shortable_now)}
            kept_s = [s for s in sh if rrank.get(s, 10 ** 9) <= keep] if n_alt_target else []
            cover_o = [s for s in sh if s not in kept_s]
            short_o = [s for s in shortable_now[:n] if s not in sh and s not in pos][:n_alt_target - len(kept_s)] if n_alt_target else []
            frac = hedge_w
            if freed_to_hedge and n_alt_target:
                freed = n_alt_target - len(kept_s) - len(short_o)
                frac += alt_frac * max(freed, 0) / n_alt_target
            if frac > 0 and hedge_sym in perp:
                if hedge is None:
                    h_open_frac = frac
                else:
                    c_h = perp[hedge_sym][2][k]
                    target = invest_short * frac * e_close
                    if np.isfinite(c_h) and target > 0 and abs(hedge["units"] * c_h - target) / target > hedge_drift:
                        h_close_o, h_open_frac = True, frac
            elif hedge is not None:
                h_close_o = True
    pending = dict(decision_time=str(grid[-1]) if decide[len(grid) - 1] else None, sell=list(sell_o), buy=list(buy_o),
                   cover=list(cover_o), short=list(short_o), hedge_close=h_close_o, hedge_open_frac=h_open_frac,
                   longs={s: dict(units=p["units"], entry_time=str(p["t"]), venue=p.get("venue", "spot")) for s, p in pos.items()},
                   shorts={s: dict(units=p["units"], entry=p["entry"], stop=(p["entry"] * stop if stop else None), entry_time=str(p["t"]))
                           for s, p in sh.items()},
                   hedge=(dict(units=hedge["units"], entry=hedge["entry"]) if hedge else None),
                   cooldown={s: str(v) for s, v in last_bad.items()})
    last = len(grid) - 1
    for s in list(pos):
        if pos[s].get("venue") == "perp":
            c_ = perp[s][2][last]
            sell(s, float(c_) if np.isfinite(c_) else pos[s]["entry"], grid[-1], "end_of_test")
        else:
            sell(s, spot[s][1][last], grid[-1], "end_of_test")
    for s in list(sh):
        c_ = perp[s][2][last]
        cover(s, float(c_) if np.isfinite(c_) else sh[s]["entry"], grid[-1], "end_of_test")
    if hedge is not None:
        c_ = perp[hedge_sym][2][last]
        close_short(hedge, float(c_) if np.isfinite(c_) else hedge["entry"], grid[-1], "end_of_test", "hedge", hedge_sym)
    tr = pd.DataFrame(trades)
    if len(tr):
        assert abs(CAP + tr.pnl.sum() - cash) < 1e-6 * max(1.0, cash), (CAP + tr.pnl.sum(), cash)
    return dict(final=cash, eq=pd.Series(eq, index=grid), short_pnl=pd.Series(s_pnl, index=grid), trades=tr, liquidations=liq, stops=n_stop, hedge_stops=n_hedge_stop,
                cooldown_blocks=n_cool_block, age_blocks=n_age_block, long_blocked=n_long_blocked,
                perp_longs=n_perp_longs, spot_longs=n_spot_longs, pending=pending)
