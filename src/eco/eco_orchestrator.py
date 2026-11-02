"""ECO orchestrator: one hourly cycle of the single 10,000 USDT ecosystem (protocol logs/eco/ECO_PROTOCOL_PREREGISTERED.md).
Modes:  plan   - public market data, NO orders; fills are assumed at the mark price (paper) so the state evolves
        demo   - orders to demo-fapi.binance.com only (keys from env); needs deploy/eco_config.json "demo_enabled": true
        replay - driven by src/eco/eco_replay.py (laptop), simulated fills
Amendment 2 (logs/eco/ECO_AMENDMENT_2_PREREGISTERED.md): complete kill + halted marking, last-price marking, delisting rule,
confirmed fills / stop fills, orphan stops, atomic state, funding on pre-order positions, max_orders by size.
Usage (VM cron, hourly at :50):  python src/eco/eco_orchestrator.py --mode plan --root data/eco"""
import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_core as C
import eco_exchange as X

PROJ = C.PROJ
CFG_F = PROJ / "deploy" / "eco_config.json"
PROTO = PROJ / "logs" / "eco" / "ECO_PROTOCOL_PREREGISTERED.md"


def new_state():
    return dict(held={}, suppressed={}, month=None, E_m=C.E0, k_m=1.0, eco_equity=C.E0, peak=C.E0, halted=None,
                last_cycle=None, last_acct_pnl=0.0, journal=[], frozen_syms=[], n_cycles=0, last_px={}, n_px_missing=0)


def marks(st, price, notes):
    """amendment 2 §2: current price where known, else the last seen price of a held perp (noted)."""
    lp = st.setdefault("last_px", {})
    lp.update({p: v for p, v in price.items() if v and v > 0})
    held_perps = {p for h in st["held"].values() for p in h["qty"]}
    miss = sorted(p for p in held_perps if p not in price)
    out = dict(price)
    for p in miss:
        if p in lp:
            out[p] = lp[p]
    if miss:
        notes.append(f"no price for held {miss}: marked at the last seen price {[(p, lp.get(p)) for p in miss]}")
    unmarked = [p for p in miss if p not in out]
    return out, miss, unmarked


def mark_equity(st, mk, notes):
    """move eco equity by the account P&L change since the last mark; None if a held perp has no price at all."""
    if any(p not in mk for h in st["held"].values() for p in h["qty"]):
        notes.append("a held perp has never had a price: equity not marked this cycle")
        return st["last_acct_pnl"]
    acct = C.equity_account(st["held"], mk)
    st["eco_equity"] += (acct - st["last_acct_pnl"]) / st["k_m"]
    st["last_acct_pnl"] = acct
    return acct


def stop_tuple(v):
    return (v, None, None) if isinstance(v, str) else tuple(v)


def recover_journal(env, st, cfg, notes):
    """write-ahead journal (T1) + amendment 2 §4: recovered fills are booked; orders still working stay in the journal."""
    pending = []
    for j in st.get("journal", []):
        r = env.recover(j)
        if r == "PENDING":
            notes.append(f"journal: {j['cid']} still working on the exchange -> kept")
            pending.append(j)
        elif r is not None:
            C.allocate_fill(j["ct"], st["held"], j["perp"], r[0], r[1], cfg["fee"])
            notes.append(f"journal: {j['cid']} recovered as filled {r[0]} @ {r[1]}")
        else:
            notes.append(f"journal: {j['cid']} not filled -> dropped")
    st["journal"] = list(pending)
    return pending


def halted_cycle(env, st, cfg, now):
    """amendment 2 §1: while halted, mark equity and close what is still open on the exchange (reduce-only, no limit)."""
    notes = ["HALTED: no opening orders until the user resets (src/eco/eco_reset.py)"]
    recover_journal(env, st, cfg, notes)
    filters = env.filters()
    held_perps = {p for h in st["held"].values() for p in h["qty"]}
    exch = env.positions()
    price = env.prices(held_perps | {p for p in exch if p in held_perps})
    mk, miss, _ = marks(st, price, notes)
    mark_equity(st, mk, notes)
    orders, oskip = C.plan_orders({}, st["held"], {p: q for p, q in exch.items() if p in held_perps}, filters, mk, 0.0, set())
    fills = []
    for i_o, o in enumerate(orders):
        o["reduce_only"] = True
        r = env.execute(o, f"ecoH{pd.Timestamp(now):%y%m%d%H%M}n{i_o}")
        if r is None:
            notes.append(f"halted close {o['perp']} {o['qty']} failed: {env.last_error}")
            continue
        C.allocate_fill({}, st["held"], o["perp"], r[0], r[1], cfg["fee"])
        fills.append(dict(perp=o["perp"], qty=r[0], px=r[1], reduce_only=True))
    mk2, _, _ = marks(st, env.prices_after(), notes) if fills else (mk, None, None)
    acct = mark_equity(st, mk2, notes)
    st["last_cycle"] = str(now)
    hn = C.held_net(st["held"])
    return dict(T=str(now), mode=env.mode, halted=st["halted"], orders=fills, skipped=oskip[:50], eco_equity=st["eco_equity"], peak=st["peak"],
                k_m=st["k_m"], acct_pnl=acct, held_net=hn, exch_before=exch, notes=notes + env.notes(),
                attribution={s: sum(h["cash"] + sum(q * mk2.get(p, 0.0) for p, q in h["qty"].items())
                                    for k_, h in st["held"].items() if k_.startswith(s + "|")) for s in ("N1", "1D")})


class Lock:
    """portable exclusive lock file (O_EXCL). A lock older than 50 min is stale (a crashed run) and is taken over, logged."""

    def __init__(self, path):
        self.path, self.note = Path(path), None

    def __enter__(self):
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            age = time.time() - self.path.stat().st_mtime
            if age < 50 * 60:
                raise RuntimeError(f"another ECO run holds the lock ({age:.0f} s old)")
            self.note = f"stale lock ({age:.0f} s) taken over"
            self.path.unlink()
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return self

    def __exit__(self, *a):
        self.path.unlink(missing_ok=True)


def cycle(env, st, cfg, now):
    """one cycle. env: plan/demo/replay environment. Returns the ledger record (state st is updated in place)."""
    notes, frozen = [], {}
    rec = dict(T=str(now), mode=env.mode)
    if st["halted"]:
        return halted_cycle(env, st, cfg, now)
    # ---- journal recovery (an order sent but the ledger not written: T1)
    pending = recover_journal(env, st, cfg, notes)     # amendment 2 §4: unconfirmed orders stay in the journal
    # ---- exchange stops placed earlier: fired / gone? (amendment 1 §3, CODE_NOTES 3) - booked BEFORE targets
    ex_stops = st.setdefault("stops", {})
    for sid, v in env.stop_status(ex_stops).items():
        s_, aq, ap = stop_tuple(v)
        if s_ in ("NEW", "OPEN", "WORKING"):
            continue
        if s_ in ("TRIGGERED", "FINISHED") and aq:
            C.book_triggered(st, sid, ex_stops[sid], cfg["fee"], aq, ap)
            notes.append(f"exchange stop {sid} {s_}: booked {aq} @ {ap or ex_stops[sid]['trigger']}" + ("" if ap else " (no actualPrice: trigger)"))
            ex_stops.pop(sid)
        elif s_ in ("TRIGGERING", "TRIGGERED"):                        # on its way / in the matching engine: decide next cycle
            notes.append(f"exchange stop {sid} {s_}, no fill yet: kept")
        elif s_ == "FINISHED":
            notes.append(f"exchange stop {sid} FINISHED without a fill: dropped, nothing booked")
            ex_stops.pop(sid)
        else:
            notes.append(f"exchange stop {sid} status {s_}: dropped, will be re-placed if still wanted")
            ex_stops.pop(sid)
    orphan = getattr(env, "algo_orphans", None)
    rec["foreign_stops"] = orphan(ex_stops, notes) if orphan else []
    # ---- producers
    strategies, f4_keys = {}, None
    try:
        eqn, posn, infn = env.n1(now)
        strategies["N1"] = (eqn, posn); rec["n1"] = infn
    except C.Frozen as e:
        frozen["N1"] = str(e)
    try:
        eqf, compf, inff = env.f4(now)
        strategies["1D"] = (eqf, compf); rec["f4"] = inff; f4_keys = set(compf)
    except C.Frozen as e:
        frozen["1D"] = str(e)
    rec["frozen_strategies"] = frozen
    # ---- market
    filters = env.filters()
    coins = {c[0] for _, comps in strategies.values() for c in comps.values()}
    perp_of = X.resolve_perps(coins, filters, cfg["n1_perp_names"])
    held_perps = {p for h in st["held"].values() for p in h["qty"]}
    need = {v[0] for v in perp_of.values() if v} | held_perps
    price = env.prices(need)
    # ---- month: sizing base and account scale (CODE_NOTES note 2)
    m = str(pd.Timestamp(now).to_period("M"))
    mk, miss, _ = marks(st, price, notes)
    st["n_px_missing"] = st.get("n_px_missing", 0) + 1 if miss else 0
    rec["px_missing"] = miss
    acct_pnl = mark_equity(st, mk, notes)
    st["peak"] = max(st["peak"], st["eco_equity"])
    if st["month"] != m:
        wallet = env.wallet()
        st["month"], st["E_m"] = m, st["eco_equity"]
        st["k_m"] = 1.0 if wallet is None else min(1.0, wallet / cfg["capital"])
        w = cfg["weights"]
        if w.get("mode") == "inverse_vol":
            r1, rn = env.return_history()
            a1 = C.inv_vol_weight(r1, rn, pd.Timestamp(m + "-01"), w["lookback"], w["clip"][0], w["clip"][1])
            st["a"] = {"1D": a1, "N1": 1.0 - a1}
        else:
            st["a"] = {"1D": float(w["1D"]), "N1": float(w["N1"])}
        notes.append(f"new month {m}: E_m {st['E_m']:.2f}, k_m {st['k_m']:.4f} (wallet {wallet}), weights {st['a']}")
    w_now = env.wallet() if env.mode == "demo" else None
    rec["k_now"] = w_now / cfg["capital"] if w_now is not None else None
    # ---- targets
    a = st["a"]
    ct, skipped = C.component_targets(a, st["E_m"], st["k_m"], strategies, perp_of, price, st["suppressed"])
    for s_ in frozen:                                   # frozen strategy: keep what is held, open nothing new
        for key, h in st["held"].items():
            if key.startswith(s_ + "|"):
                for p, q in h["qty"].items():
                    ct[key] = dict(perp=p, strategy=s_, notional_eco=q * mk.get(p, 0.0) / st["k_m"], qty=q, stop=None, scale=1.0, coin=None,
                                   frozen=True)
    # ---- delisting rule (amendment 2 §3): announced -> target 0; held but no longer trading -> noted (cannot trade)
    deli = sorted({c["perp"] for c in ct.values() if filters.get(c["perp"], {}).get("delivery_ms", X.FAR_DELIVERY_MS) < X.FAR_DELIVERY_MS}
                  | {p for p in held_perps if filters.get(p, {}).get("delivery_ms", X.FAR_DELIVERY_MS) < X.FAR_DELIVERY_MS})
    for c in ct.values():
        if c["perp"] in deli:
            c["qty"] = 0.0; c["notional_eco"] = 0.0
    dead = sorted(p for p in held_perps if p not in filters)
    if deli:
        notes.append(f"delisting announced (deliveryDate set): targets 0 on {deli}")
    if dead:
        notes.append(f"held perps no longer TRADING (settled / delisted), cannot be traded: {dead}")
    rec["delisting"], rec["held_not_trading"] = deli, dead
    # ---- stops (1D shorts), from the last closed 1h highs since the previous cycle
    short_perps = sorted({c["perp"] for k_, c in ct.items() if "|S|" in k_ and c["strategy"] == "1D"})
    since = pd.Timestamp(st["last_cycle"]) if st["last_cycle"] else pd.Timestamp(now) - pd.Timedelta(hours=1)
    highs = env.highs(short_perps, since, now)
    hits = C.check_stops(ct, st["held"], highs, st["suppressed"])
    for k_ in hits:
        ct[k_]["qty"] = 0.0; ct[k_]["notional_eco"] = 0.0
    if f4_keys is not None:
        C.release_suppressed(st["suppressed"], f4_keys)
    scal = C.apply_caps(ct, st["eco_equity"], cfg["coin_cap"], cfg["gross_cap"])
    # ---- kill switch
    killing = st["eco_equity"] < (1 - cfg["kill_K"]) * st["peak"]
    if killing:
        st["halted"] = f"kill switch {now}: eco equity {st['eco_equity']:.2f} < (1 - {cfg['kill_K']:.4f}) x peak {st['peak']:.2f}"
        ct = {}
        notes.append(st["halted"])
    # ---- reconcile (before orders)
    exch = env.positions()
    hn = C.held_net(st["held"])
    mism = {p: (exch.get(p, 0.0), hn.get(p, 0.0)) for p in set(exch) | set(hn)
            if abs(exch.get(p, 0.0) - hn.get(p, 0.0)) > filters.get(p, {"step": 1e-9})["step"] / 2 and p in (set(hn) | need)}
    foreign = {p: q for p, q in exch.items() if p not in hn and p not in need}
    frozen_syms = sorted(set(mism) | set(st.get("guard_fired", {})))      # guard fired -> frozen until the user resets (CODE_NOTES 3)
    busy = sorted({j["perp"] for j in pending})                          # an unconfirmed order still working: no second order
    if busy:
        notes.append(f"unconfirmed order still working on {busy}: no new order there this cycle")
    # ---- orders
    band = cfg["band_frac"] * st["k_m"] * st["eco_equity"]
    if killing:                                         # amendment 2 §1: close every held symbol, frozen ones too, no order limit
        orders, oskip = C.plan_orders({}, st["held"], {p: q for p, q in exch.items() if p in held_perps}, filters, mk, 0.0, set())
        for o in orders:
            o["reduce_only"] = True
        for p in sorted(set(frozen_syms) & held_perps):
            notes.append(f"kill: frozen {p} closed by the exchange qty {exch.get(p, 0.0)} (ledger {hn.get(p, 0.0)})")
    else:
        orders, oskip = C.plan_orders(ct, st["held"], exch, filters, mk, band, set(frozen_syms) | set(busy))
        orders.sort(key=lambda o: -abs(o["qty"]) * mk.get(o["perp"], 0.0))           # amendment 2 §7: largest first
        oskip += [(o["perp"], f"max_orders {cfg['max_orders']}: not sent this cycle") for o in orders[cfg["max_orders"]:]]
        orders = orders[: cfg["max_orders"]]
    # ---- funding (amendment 2 §6): booked BEFORE the orders, on the components that held the positions during the interval
    fund = env.funding(C.held_net(st["held"]), since, now)
    for p, amt in fund.items():
        C.allocate_funding(st["held"], p, amt)
    fills = []
    for i_o, o in enumerate(orders):
        cid = f"eco{pd.Timestamp(now):%y%m%d%H%M}n{i_o}"            # unique per order (an unconfirmed order no longer shares its id)
        j = dict(cid=cid, perp=o["perp"], qty=o["qty"], ct={k_: v for k_, v in ct.items() if v["perp"] == o["perp"]})
        st["journal"] = [j]
        env.journal_written(st)                                   # write-ahead: state with the journal entry hits disk first
        env.unconfirmed = False
        r = env.execute(o, cid)
        if r is None:
            notes.append(f"order {o['perp']} {o['qty']} failed: {env.last_error}")
            if getattr(env, "unconfirmed", False):         # sent but not confirmed: kept for recovery by its clientOrderId
                pending.append(j)
                notes.append(f"order {cid} not confirmed: kept in the journal, nothing booked")
            st["journal"] = list(pending)
            continue
        qty, px = r
        if killing:                                     # the ledger closes its own quantity; any exchange excess is noted, not attributed
            q_led = -C.held_net(st["held"]).get(o["perp"], 0.0)
            if abs(q_led - qty) > filters.get(o["perp"], {"step": 1e-9})["step"] / 2:
                notes.append(f"kill: {o['perp']} exchange closed {qty}, ledger held {-q_led}: the difference is not attributed")
            C.allocate_fill({}, st["held"], o["perp"], q_led, px, cfg["fee"])
        else:
            C.allocate_fill(ct, st["held"], o["perp"], qty, px, cfg["fee"])
        fills.append(dict(perp=o["perp"], qty=qty, px=px, reduce_only=o["reduce_only"]))
        st["journal"] = list(pending)
    # internal transfers on symbols without an order (matched opposite gaps)
    traded = {f["perp"] for f in fills}
    if killing:                                         # ledger positions the exchange no longer shows: closed in the ledger at the mark
        for p, q in C.held_net(st["held"]).items():
            if abs(exch.get(p, 0.0)) < filters.get(p, {"step": 1e-9})["step"] / 2 and p not in traded and p in mk:
                C.allocate_fill({}, st["held"], p, -q, mk[p], 0.0)
                notes.append(f"kill: {p} ledger {q} not on the exchange: closed in the ledger at mark {mk[p]} (not attributed to a fill)")
    pend_perps = {j["perp"] for j in pending}
    for p in ({c["perp"] for c in ct.values()} | held_perps) if not killing else set():
        if p not in traded and p in price and p not in frozen_syms and p not in pend_perps:
            C.allocate_fill(ct, st["held"], p, 0.0, price[p], cfg["fee"])
    # ---- book-keeping after fills
    price2, _, _ = marks(st, env.prices_after(), [])
    acct_after = mark_equity(st, price2, notes)
    # ---- exchange stops: desired vs existing (amendment 1 §2, §3)
    desired, snotes = C.desired_stops(ct, st["held"], filters, price2, st.setdefault("guard_ref", {}), cfg["guard_D"], cfg.get("guard_on", True))
    cancel, place = C.diff_stops(desired, ex_stops, filters)
    n_cancel = n_place = 0
    for sid in cancel:
        if env.cancel_stop(ex_stops[sid]):
            ex_stops.pop(sid); n_cancel += 1
        else:
            snotes.append(f"cancel {sid} failed: {env.last_error}")
    for sid in place:
        if sid in ex_stops:
            continue
        desired[sid]["cid"] = ("eco" + C.sha_b(f"{sid}|{now}".encode())[:24])[:36]     # amendment 2 §4: identifies ECO stops
        aid = env.place_stop(desired[sid])
        if aid is None:
            snotes.append(f"place {sid} failed: {env.last_error}")
            continue
        ex_stops[sid] = dict(desired[sid], algoId=aid); n_place += 1
    rec["stops"] = dict(n_open=len(ex_stops), placed=n_place, cancelled=n_cancel, n_guard=sum(1 for v in ex_stops.values() if v["kind"] == "G"),
                        n_component=sum(1 for v in ex_stops.values() if v["kind"] == "C"), notes=snotes[:30])
    st["last_cycle"] = str(now)
    st["frozen_syms"] = frozen_syms
    st["n_cycles"] += 1
    st["journal"] = list(pending)
    hn2 = C.held_net(st["held"])
    gross_eco = sum(abs(q) * price2.get(p, 0.0) for p, q in hn2.items()) / st["k_m"]
    tnet = {}
    for c in ct.values():
        tnet[c["perp"]] = tnet.get(c["perp"], 0.0) + c["qty"]
    rec.update(halted=st["halted"], targets_net=tnet, held_net=hn2, exch_before=exch, price=price, a=a, E_m=st["E_m"], k_m=st["k_m"], eco_equity=st["eco_equity"], peak=st["peak"], acct_pnl=acct_after,
               n_components=len(ct), n_symbols=len(hn2), gross_eco=gross_eco, orders=fills, skipped=oskip[:50] + skipped[:20],
               n_skipped=len(oskip) + len(skipped), caps=scal, stop_hits=hits, suppressed=sorted(st["suppressed"]),
               reconcile_mismatch=mism, foreign_positions=foreign, funding=fund, notes=notes + env.notes(),
               n_px_missing=st["n_px_missing"], pending_journal=[j["cid"] for j in pending],
               attribution={s: sum(h["cash"] + sum(q * price2.get(p, 0.0) for p, q in h["qty"].items())
                                   for k_, h in st["held"].items() if k_.startswith(s + "|")) for s in ("N1", "1D")})
    return rec


# ======================================================================= live environments (plan / demo)
class LiveEnv:
    def __init__(self, mode, cfg, root, host="public", k_from=None):
        self.mode, self.cfg, self.root, self.k_from = mode, cfg, Path(root), k_from
        self.pub = X.Public(X.DEMO if (mode == "demo" or host == "demo") else X.PUBLIC)
        self.demo = X.Demo() if mode == "demo" else None
        self.last_error, self._notes, self._px = None, [], {}
        self._filters = None

    def notes(self):
        return self._notes + self.pub.errors

    def n1(self, now):
        return C.load_n1(PROJ / self.cfg["n1_root"], now)

    def f4(self, now):
        return C.load_f4(PROJ / "logs" / "forward_ls_f4", pd.Timestamp(now).normalize())

    def filters(self):
        if self._filters is None:
            info = self.pub.exchange_info()
            assert info, "exchangeInfo failed"
            self._filters = X.parse_filters(info)
        return self._filters

    def prices(self, perps):
        self._px = self.pub.prices(perps)
        return self._px

    def prices_after(self):
        return self.pub.prices(set(self._px)) if self.mode == "demo" else self._px

    def highs(self, perps, since, now):
        return self.pub.high_since(perps, pd.Timestamp(since).floor("h").value // 10**6, pd.Timestamp(now).value // 10**6)

    def wallet(self):
        if self.demo:
            return self.demo.wallet_equity()
        if self.k_from:                                       # shadow (amendment 1 §4.3): the demo instance's k
            k = json.loads((PROJ / self.k_from / "state.json").read_text()).get("k_m", 1.0)
            return k * self.cfg["capital"]
        return None

    def return_history(self):
        """CODE_CHANGES 3: frozen backtest returns (SHA in the config) + forward paper returns after them."""
        hf = PROJ / self.cfg["weights"]["history"]
        assert C.sha_f(hf) == self.cfg["weights"]["history_sha256"], "weight history file changed"
        h = pd.read_csv(hf, parse_dates=["date"]).set_index("date")
        f1, fn = C.forward_returns(PROJ / "logs" / "forward_ls_f4" / "ledger.csv", PROJ / self.cfg["n1_root"] / "ledger.jsonl")
        r1 = pd.concat([h.r_1D.dropna(), f1[f1.index > h.index.max()]])
        rn = pd.concat([h.r_N1.dropna(), fn[fn.index > h.index.max()]])
        return r1, rn

    def positions(self):
        if self.demo:
            return self.demo.positions()
        st = json.loads((self.root / "state.json").read_text()) if (self.root / "state.json").exists() else new_state()
        return C.held_net(st["held"])                       # plan: the paper book is the "exchange"

    def journal_written(self, st):
        C.write_json_atomic(self.root / "state.json", st, keep_prev=False)

    def execute(self, o, cid):
        if self.mode == "plan":
            if o["perp"] not in self._px:                     # no current mark (e.g. delisted): not filled, retried next cycle
                self.last_error = "plan: no current mark price"
                return None
            return o["qty"], self._px[o["perp"]]             # paper fill at the mark price; nothing is sent
        if o["perp"] not in self.demo_prepared():
            self.demo.prepare_symbol(o["perp"], self._notes)
        r = self.demo.market(o["perp"], o["qty"], o["reduce_only"], cid)
        if r.get("_error") and r.get("status", 500) < 500:
            self.last_error = r                                 # rejected by the exchange: nothing was opened
            return None
        f = self.demo.confirmed_fill(r, o["perp"], cid)         # amendment 2 §4
        if f is None:
            self.last_error, self.unconfirmed = {"unconfirmed": r}, True
            return None
        return f[0] * np.sign(o["qty"]), f[1]

    def stop_status(self, ex):
        if self.mode == "plan":
            return {sid: "NEW" for sid in ex}
        self._open_algo = self.demo.open_algo()
        ids = {int(o["algoId"]) for o in self._open_algo}
        out = {}
        for sid, e in ex.items():
            out[sid] = ("NEW", None, None) if int(e["algoId"]) in ids else self.demo.algo_fill(e["algoId"])
        return out

    def algo_orphans(self, ex, notes):
        """amendment 2 §4: open ECO stops unknown to the state are cancelled; other open algo orders are reported (foreign)."""
        if self.mode == "plan":
            return []
        known = {int(e["algoId"]) for e in ex.values()}
        foreign = []
        for o in getattr(self, "_open_algo", None) or self.demo.open_algo():
            if int(o["algoId"]) in known:
                continue
            if str(o.get("clientAlgoId", "")).startswith("eco"):
                r = self.demo.signed("DELETE", "/fapi/v1/algoOrder", algoId=o["algoId"])
                notes.append(f"orphan ECO stop {o['algoId']} {o.get('symbol')} cancelled: {'ok' if not r.get('_error') else r}")
            else:
                foreign.append(dict(algoId=o["algoId"], symbol=o.get("symbol"), clientAlgoId=o.get("clientAlgoId")))
        if foreign:
            notes.append(f"foreign open algo orders (not ECO, left alone): {foreign[:10]}")
        return foreign

    def place_stop(self, spec):
        if self.mode == "plan":
            self._n_plan = getattr(self, "_n_plan", 0) + 1
            return f"plan-{self._n_plan}"
        r = self.demo.signed("POST", "/fapi/v1/algoOrder", algoType="CONDITIONAL", symbol=spec["perp"], side=spec["side"], type="STOP_MARKET",
                             quantity=X.fmt(spec["qty"]), triggerPrice=X.fmt(spec["trigger"]), workingType=spec["working"], reduceOnly="true",
                             clientAlgoId=spec["cid"])
        if r.get("_error") or not r.get("algoId"):
            self.last_error = r
            return None
        return r["algoId"]

    def cancel_stop(self, e):
        if self.mode == "plan":
            return True
        r = self.demo.signed("DELETE", "/fapi/v1/algoOrder", algoId=e["algoId"])
        if r.get("_error"):
            self.last_error = r
            return False
        return True

    def demo_prepared(self):
        return set(self.demo.positions())                    # a symbol with a position keeps its margin settings

    def recover(self, j):
        if self.mode == "plan":
            return None
        r = self.demo.query(j["perp"], j["cid"])
        if not r.get("_error") and r.get("status") == "NEW":
            return "PENDING"                                 # amendment 2 §4: still working -> stays in the journal
        f = self.demo.confirmed_fill(r, j["perp"], j["cid"], tries=0)
        return None if f is None else (f[0] * np.sign(j["qty"]), f[1])

    def funding(self, held, since, now):
        if self.mode == "plan":
            out = {}
            for p, q in held.items():                        # plan: public funding history, paid on the paper book
                r = self.pub.get("/fapi/v1/fundingRate", symbol=p, startTime=int(pd.Timestamp(since).value // 10**6) + 1,
                                 endTime=int(pd.Timestamp(now).value // 10**6))
                for e in r or []:
                    out[p] = out.get(p, 0.0) - q * float(e.get("markPrice") or self._px.get(p, 0.0)) * float(e["fundingRate"])
            return out
        out = {}
        for e in self.demo.funding_income(pd.Timestamp(since).value // 10**6):
            if int(e["time"]) <= pd.Timestamp(now).value // 10**6:
                out[e["symbol"]] = out.get(e["symbol"], 0.0) + float(e["income"])
        return out


def load_cfg():
    cfg = json.loads(CFG_F.read_text())
    cfg["weights"] = cfg["weights"]                        # fixed weights {"N1": a, "1D": 1 - a} (set from the E-2 claims)
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["plan", "demo"], required=True)
    ap.add_argument("--root", default="data/eco")
    ap.add_argument("--host", choices=["public", "demo"], default="public", help="plan mode: whose public market data")
    ap.add_argument("--k-from", default=None, help="plan shadow: take k from this ECO root's state")
    a = ap.parse_args()
    assert C.sha_f(PROTO) == (PROTO.parent / "ECO_PROTOCOL_SHA256.txt").read_text().split()[0], "ECO protocol changed"
    cfg = load_cfg()
    if a.mode == "demo":
        assert cfg.get("demo_enabled") is True, "demo mode is not enabled in deploy/eco_config.json (needs the user's yes, E-6)"
        assert (PROJ / a.root / "state.json").exists(), "demo mode starts only from the cut-over state (src/eco/eco_cutover.py)"
    root = PROJ / a.root
    root.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now("UTC").tz_localize(None).floor("min")
    with Lock(root / "eco.lock") as lk:
        sf = root / "state.json"
        try:
            st = json.loads(sf.read_text()) if sf.exists() else new_state()   # amendment 2 §5: a corrupt state = a failed record
            env = LiveEnv(a.mode, cfg, root, a.host, a.k_from)
            if env.demo:
                assert env.demo.one_way(), "account is in HEDGE mode: the user must switch to one-way (code does not change it)"
            rec = cycle(env, st, cfg, now)
            rec["ok"] = True
        except Exception:                                                 # noqa: BLE001 - recorded, no orders after the failure point
            rec = dict(T=str(now), mode=a.mode, ok=False, error=traceback.format_exc()[-2000:])
        if lk.note:
            rec.setdefault("notes", []).append(lk.note)
        rec["code_sha256"] = C.sha_f(Path(__file__)); rec["core_sha256"] = C.sha_f(Path(C.__file__))
        rec["exchange_sha256"] = C.sha_f(Path(X.__file__)); rec["config_sha256"] = C.sha_f(CFG_F); rec["protocol_sha256"] = C.sha_f(PROTO)
        C.append_ledger(root / "ledger.jsonl", rec)
        if rec.get("ok"):
            C.write_json_atomic(sf, st)
        print(f"eco {a.mode} {now}: ok {rec.get('ok')} equity {rec.get('eco_equity')} orders {len(rec.get('orders', []))} "
              f"frozen {rec.get('frozen_strategies')} mismatch {len(rec.get('reconcile_mismatch', {}))}")
        sys.exit(0 if rec.get("ok") else 1)


if __name__ == "__main__":
    main()
