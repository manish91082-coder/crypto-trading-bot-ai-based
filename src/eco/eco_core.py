"""ECO core (protocol logs/eco/ECO_PROTOCOL_PREREGISTERED.md): producer adapters, allocator, netting, attribution, stops,
kill switch, hash-chained ledger. Exchange access lives in eco_exchange.py (plan / demo / replay); nothing here sends orders.

Units: a component holds a signed quantity in PERP CONTRACTS of its perp symbol (e.g. 1000SHIBUSDT); cash in USDT of the
account. Eco units = account USDT / k (k = account scale, fixed per month: CODE_NOTES note 2)."""
import hashlib
import json
import os
import shutil
from pathlib import Path

import numpy as np

PROJ = Path(__file__).resolve().parents[2]
E0 = 10_000.0


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def sha_f(p):
    return sha_b(Path(p).read_bytes())


# ======================================================================= producers (read only)
class Frozen(Exception):
    """a producer failed integrity / staleness: its strategy is frozen this cycle"""


def load_n1(root, now, max_age_h=5.0):
    """PAPER-N1: verify the ledger hash chain, state <-> last line; return (equity, {key: (coin, side, units, venue)}, info)."""
    root = Path(root)
    lines = [l for l in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    prev = "GENESIS"
    for l in lines:
        r = json.loads(l)
        body = {k: v for k, v in r.items() if k != "line_sha256"}
        if r["prev_sha256"] != prev or sha_b(json.dumps(body, sort_keys=True, default=str).encode()) != r["line_sha256"]:
            raise Frozen("N1 ledger hash chain broken")
        prev = r["line_sha256"]
    last = json.loads(lines[-1])
    st = json.loads((root / "state.json").read_text())
    if str(st.get("last_T")) != str(last["T"]):
        raise Frozen(f"N1 state last_T {st.get('last_T')} != ledger T {last['T']}")
    age = (np.datetime64(now) - np.datetime64(last["T"])) / np.timedelta64(1, "h")
    if age > max_age_h:
        raise Frozen(f"N1 stale: last T {last['T']} is {age:.1f} h old")
    pos = {"N1|" + k: (k.split("|")[1], int(p["side"]), abs(float(p["units"])), p["venue"]) for k, p in st["pos"].items()}
    return float(last["equity"]), pos, dict(T=last["T"], line_sha256=last["line_sha256"])


def load_f4(logdir, today, max_age_days=2, n_hold=5, invest=0.5):
    """F4 LS_RS: orders file must equal the ledger's orders_sha256. Returns (total paper equity, components, info).
    component key -> (coin, side, units or None, frac_of_sleeve or None, stop or None, sleeve, entry_time)"""
    import csv
    logdir = Path(logdir)
    with open(logdir / "ledger.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    r = rows[-1]
    if str(r.get("C1", "True")) != "True":                           # amendment 2 §7: F4 marks the day untrusted
        raise Frozen(f"F4 C1 = {r.get('C1')} for as-of {r['asof']}: LS numbers untrusted")
    f = logdir / "paper" / f"orders_{r['asof']}.json"
    if sha_f(f) != r["orders_sha256"]:
        raise Frozen("F4 orders file != F4 ledger orders_sha256")
    age = (np.datetime64(today, "D") - np.datetime64(r["asof"], "D")) / np.timedelta64(1, "D")
    if age > max_age_days:
        raise Frozen(f"F4 stale: as-of {r['asof']} is {age:.0f} days old")
    dec = json.loads(f.read_text()).get("LS_RS", {})
    return parse_f4(dec, n_hold, invest) + (dict(asof=r["asof"], line_sha256=r["line_sha256"]),)


def parse_f4(dec, n_hold=5, invest=0.5):
    """positions AFTER the pending decision (F4 fills it at the next bar open): longs - sell + buy, shorts - cover + short.
    New positions are sized by the F4 rule invest * sleeve equity / n_hold (fraction of the sleeve, units unknown yet)."""
    comps, eq = {}, 0.0
    for k in ("D1", "H4", "H1"):
        d = dec.get(k)
        if not d:
            continue
        e = float(d["equity_close"])
        eq += e
        for s, p in d.get("longs", {}).items():
            if s not in d.get("sell", []):
                comps[f"1D|{k}|L|{s}"] = (s, 1, float(p["units"]), None, None, k, p["entry_time"])
        for s in d.get("buy", []):
            comps[f"1D|{k}|L|{s}"] = (s, 1, None, invest * e / n_hold, None, k, "pending:" + str(d.get("decision_time")))
        for s, p in d.get("shorts", {}).items():
            if s not in d.get("cover", []):
                comps[f"1D|{k}|S|{s}"] = (s, -1, float(p["units"]), None, p.get("stop"), k, p["entry_time"])
        for s in d.get("short", []):
            comps[f"1D|{k}|S|{s}"] = (s, -1, None, invest * e / n_hold, None, k, "pending:" + str(d.get("decision_time")))
    return eq, comps


# ======================================================================= targets
def component_targets(a, Em, k, strategies, perp_of, price, suppressed):
    """-> {comp_key: dict(perp, qty_target (contracts), notional_eco, strategy, stop)}.
    strategies: {"N1": (equity, pos) , "1D": (equity, comps)}; price[perp] = perp contract price; perp_of[coin] = (perp, scale)."""
    out, skipped = {}, []
    for strat, (eq, comps) in strategies.items():
        if eq <= 0 or a.get(strat, 0.0) <= 0:
            continue
        for key, c in comps.items():
            coin = c[0]
            pm = perp_of.get(coin)
            if pm is None or pm[0] not in price:
                skipped.append((key, "no perp / no price"))
                continue
            perp, scale = pm
            px_spot = price[perp] / scale
            if strat == "N1":
                _, side, units, venue = c
                frac = side * units * px_spot / eq
                stop = None
            else:
                _, side, units, fs, stop, sleeve, et = c
                frac = side * (units * px_spot if units is not None else fs) / eq
            if key in suppressed:
                frac = 0.0
            notional_eco = a[strat] * Em * frac
            out[key] = dict(perp=perp, strategy=strat, notional_eco=notional_eco, qty=k * notional_eco / price[perp], stop=stop,
                            scale=scale, coin=coin)
    return out, skipped


def apply_caps(ct, E_eco, coin_cap, gross_cap):
    """per-symbol |net| <= coin_cap * E_eco (scale its components), then gross <= gross_cap * E_eco (one factor).
    Components marked frozen (frozen strategy: keep what is held) are never scaled (amendment 2 §7)."""
    net, scal = {}, []
    if E_eco <= 0:                                     # caps in % of a non-positive equity would flip signs: open nothing
        for c in ct.values():
            if not c.get("frozen"):
                c["notional_eco"] = 0.0; c["qty"] = 0.0
        return [("equity<=0", None, 0.0)]
    for key, c in ct.items():
        net[c["perp"]] = net.get(c["perp"], 0.0) + c["notional_eco"]
    for p, v in net.items():
        if abs(v) > coin_cap * E_eco:
            f = coin_cap * E_eco / abs(v)
            for c in ct.values():
                if c["perp"] == p and not c.get("frozen"):
                    c["notional_eco"] *= f; c["qty"] *= f
            net[p] = v * f
            scal.append(("coin", p, f))
    g = sum(abs(v) for v in net.values())
    if g > gross_cap * E_eco:
        f = gross_cap * E_eco / g
        for c in ct.values():
            if not c.get("frozen"):
                c["notional_eco"] *= f; c["qty"] *= f
        scal.append(("gross", None, f))
    return scal


# ======================================================================= netting + attribution
def floor_step(x, step):
    return np.floor(abs(x) / step + 1e-9) * step * np.sign(x)


def plan_orders(ct, held, exch_pos, filters, price, band_usdt, frozen_syms):
    """per symbol: desired = sum of component targets; delta vs EXCHANGE position; band rule; step / min checks.
    Returns orders [{perp, qty (signed, contracts), reduce_only}], skipped [(perp, reason)]."""
    want = {}
    for c in ct.values():
        want[c["perp"]] = want.get(c["perp"], 0.0) + c["qty"]
    for key, h in held.items():                      # components no longer targeted -> 0
        for p in h["qty"]:
            want.setdefault(p, 0.0)
    orders, skipped = [], []
    for p in sorted(want):
        if p in frozen_syms:
            skipped.append((p, "symbol frozen (reconcile mismatch)"))
            continue
        cur = exch_pos.get(p, 0.0)
        d = want[p] - cur
        fl = filters.get(p)
        if fl is None:
            skipped.append((p, "no exchange filters (not trading)"))
            continue
        flip = cur != 0 and np.sign(want[p]) != np.sign(cur) and want[p] != 0
        to_zero = want[p] == 0 and cur != 0
        q = floor_step(d, fl["step"])
        if to_zero:
            q = -cur                                   # close exactly what is open
        notional = abs(q) * price[p]
        if not (to_zero or flip) and abs(d) * price[p] < max(fl["min_notional"], band_usdt):
            if d != 0:
                skipped.append((p, f"inside band: |delta| {abs(d) * price[p]:.2f} USDT"))
            continue
        if abs(q) < fl["min_qty"] or (notional < fl["min_notional"] and not to_zero):
            skipped.append((p, f"below exchange minimum: qty {q}, notional {notional:.2f}"))
            continue
        reduce_only = cur != 0 and np.sign(q) == -np.sign(cur) and abs(q) <= abs(cur) + 1e-12
        orders.append(dict(perp=p, qty=float(q), reduce_only=bool(reduce_only)))
    return orders, skipped


def allocate_fill(ct, held, perp, filled_qty, px, fee):
    """split an executed signed quantity on `perp` across components by their signed gaps (target - held);
    components with no gap get nothing; if gaps cancel (internal transfer) they are crossed at px with no fee."""
    if filled_qty != 0 and not px > 0:
        raise ValueError(f"fill of {filled_qty} on {perp} at price {px}: refused (amendment 2 §4)")
    keys = sorted({k for k, c in ct.items() if c["perp"] == perp} | {k for k, h in held.items() if perp in h["qty"]})
    gap = {k: (ct[k]["qty"] if k in ct and ct[k]["perp"] == perp else 0.0) - held.get(k, {"qty": {}})["qty"].get(perp, 0.0) for k in keys}
    G = sum(gap.values())
    moves = {}
    if abs(G) > 1e-12 and filled_qty != 0:
        rho = filled_qty / G
        moves = {k: rho * g for k, g in gap.items() if g != 0}
    elif filled_qty == 0:
        P = sum(g for g in gap.values() if g > 0); Ng = -sum(g for g in gap.values() if g < 0)
        m = min(P, Ng)                                              # the matched part of opposite gaps crosses internally at px
        if m > 0:
            moves = {k: g * m / (P if g > 0 else Ng) for k, g in gap.items() if g != 0}
    tot_abs = sum(abs(v) for v in moves.values())
    exec_abs = abs(filled_qty)
    for k, dq in moves.items():
        h = held.setdefault(k, dict(qty={}, cash=0.0, fees=0.0, funding=0.0, entry_px={}))
        h["qty"][perp] = h["qty"].get(perp, 0.0) + dq
        f = fee * exec_abs * px * abs(dq) / tot_abs if tot_abs > 0 else 0.0
        h["cash"] -= dq * px + f
        h["fees"] += f
        if abs(h["qty"][perp]) < 1e-12:
            h["qty"].pop(perp); h["entry_px"].pop(perp, None)
        elif np.sign(dq) == np.sign(h["qty"][perp]):
            h["entry_px"][perp] = px                                  # last add price (stop basis for pending shorts)
    return moves


def allocate_funding(held, perp, amount):
    """amount (USDT, + received) on the NET position, split by SIGNED share q_i / net: each component pays exactly what its
    own position would (funding is linear in qty). net == 0 -> the exchange pays nothing; internal offsets are not booked."""
    hs = {k: h["qty"][perp] for k, h in held.items() if perp in h["qty"]}
    net = sum(hs.values())
    if abs(net) < 1e-12:
        return
    for k, q in hs.items():
        a = amount * q / net
        held[k]["cash"] += a; held[k]["funding"] += a


def held_net(held):
    net = {}
    for h in held.values():
        for p, q in h["qty"].items():
            net[p] = net.get(p, 0.0) + q
    return net


def equity_account(held, price):
    """account-USDT P&L of the ecosystem = sum over components of cash + qty * price (cash starts at 0)."""
    return sum(h["cash"] + sum(q * price[p] for p, q in h["qty"].items()) for h in held.values())


def check_stops(ct, held, high_since, suppressed):
    """1D short components: stop = F4 stop, else 1.50 x own fill (pending short). High of closed 1h bars since the last
    check >= stop -> suppress the component (target 0) until F4 no longer lists the position."""
    hits = []
    for key, c in ct.items():
        if c["strategy"] != "1D" or not key.startswith("1D|") or "|S|" not in key or key in suppressed:
            continue
        stop = c["stop"] * c["scale"] if c["stop"] else None          # F4 stop is in spot units -> contract price
        if stop is None:
            ep = held.get(key, {"entry_px": {}})["entry_px"].get(c["perp"])
            stop = 1.50 * ep if ep else None
        hi = high_since.get(c["perp"])
        if stop and hi is not None and hi >= stop:
            suppressed[key] = dict(stop=stop, high=hi)
            hits.append(key)
    return hits


def release_suppressed(suppressed, f4_comps):
    for key in list(suppressed):
        if key not in f4_comps:
            suppressed.pop(key)


# ======================================================================= exchange stops (amendment 1 §2, §3; CODE_NOTES 3)
def round_tick(x, tick):
    return float(np.round(x / tick) * tick)


def desired_stops(ct, held, filters, price, guard_ref, D, guard_on=True):
    """-> ({stop_id: spec}, notes). spec: perp, side (BUY/SELL), qty (>0), trigger, working, kind ('C' component / 'G' guard), key."""
    out, notes = {}, []
    net = held_net(held)
    by_perp = {}
    for k, h in held.items():
        if k.startswith("1D|") and "|S|" in k:
            for p, q in h["qty"].items():
                if q < 0:
                    by_perp.setdefault(p, []).append((k, q))
    for p, comps in by_perp.items():
        fl = filters.get(p)
        if fl is None:
            continue
        tot = sum(-q for _, q in comps)
        if not (net.get(p, 0.0) < 0 and -net[p] >= tot - fl["step"] / 2):
            notes.append(f"{p}: 1D-short stops virtual only (net {net.get(p, 0.0)} vs 1D shorts {-tot})")
            continue
        for k, q in comps:
            c = ct.get(k)
            st_ = c["stop"] * c["scale"] if c and c.get("stop") else None
            if st_ is None:
                ep = held[k]["entry_px"].get(p)
                st_ = 1.50 * ep if ep else None
            qq = float(np.floor(-q / fl["step"] + 1e-9) * fl["step"])
            if st_ is None or qq < fl["min_qty"]:
                notes.append(f"{k}: no exchange stop (stop {st_}, qty {qq})")
                continue
            out["C|" + k] = dict(perp=p, side="BUY", qty=qq, trigger=round_tick(st_, fl["tick"]), working="CONTRACT_PRICE", kind="C", key=k)
    if guard_on:
        for p, q in net.items():
            fl = filters.get(p)
            if fl is None or p not in price or abs(q) < fl["min_qty"]:
                continue
            side = 1 if q > 0 else -1
            ref = guard_ref.get(p)
            if ref is None or ref["side"] != side or abs(price[p] / ref["ref"] - 1) > 0.10:
                ref = dict(ref=price[p], side=side)
            guard_ref[p] = ref
            out["G|" + p] = dict(perp=p, side="SELL" if side == 1 else "BUY", qty=float(np.floor(abs(q) / fl["step"] + 1e-9) * fl["step"]),
                                 trigger=round_tick(ref["ref"] * (1 - side * D), fl["tick"]), working="MARK_PRICE", kind="G", key=p)
        for p in list(guard_ref):
            if p not in net:
                guard_ref.pop(p)
    return out, notes


def diff_stops(desired, existing, filters):
    """existing: {id: spec + algoId}. Same id with same qty (half a step) and trigger -> keep; else cancel / place."""
    cancel, place = [], []
    for i, e in existing.items():
        d = desired.get(i)
        if d is None or d["side"] != e["side"] or abs(d["qty"] - e["qty"]) >= filters.get(d["perp"], {"step": 1e-9})["step"] / 2 \
                or abs(d["trigger"] - e["trigger"]) > 1e-12 * max(1.0, abs(e["trigger"])):
            cancel.append(i)
    for i, d in desired.items():
        if i not in existing or i in cancel:
            place.append(i)
    return cancel, place


def book_triggered(st, sid, spec, fee, qty=None, px=None):
    """a stop that fired on the exchange: book min(executed qty, held) at the executed price (amendment 2 §4). qty / px None =
    the fallback of CODE_NOTES 3 (the full stop quantity at the trigger price)."""
    px = px if px else spec["trigger"]
    if spec["kind"] == "C":
        k, p = spec["key"], spec["perp"]
        h = st["held"].get(k)
        if h and p in h["qty"]:
            q = min(spec["qty"] if qty is None else qty, -h["qty"][p])
            ct = {k: dict(perp=p, qty=h["qty"][p] + q)}
            allocate_fill(ct, {k: h}, p, q, px, fee)
        st["suppressed"][k] = dict(stop=spec["trigger"], exchange_stop=True)
    else:
        p = spec["perp"]
        hs = {k: h for k, h in st["held"].items() if p in h["qty"]}
        tot = sum(h["qty"][p] for h in hs.values())
        q = -tot if qty is None else -float(np.sign(tot)) * min(qty, abs(tot))
        keep = (tot + q) / tot if tot else 0.0                            # a partial guard fill reduces every component pro rata
        ct = {k: dict(perp=p, qty=h["qty"][p] * keep) for k, h in hs.items()}
        allocate_fill(ct, hs, p, q, px, fee)
        st.setdefault("guard_fired", {})[p] = dict(trigger=spec["trigger"], px=px)


# ======================================================================= weights (ECO-W2, CODE_CHANGES 3)
def inv_vol_weight(r1, rn, month_start, lookback=126, lo=0.2, hi=0.8):
    """a_1D for the month: clip((1/s1) / (1/s1 + 1/sN), lo, hi) from the last `lookback` daily returns before month_start;
    0.5 while fewer than `lookback` exist (as in E-2)."""
    import pandas as pd
    a = r1[r1.index < month_start].dropna().iloc[-lookback:]
    b = rn[rn.index < month_start].dropna().iloc[-lookback:]
    if len(a) < lookback or len(b) < lookback:
        return 0.5
    x, y = 1 / a.std(ddof=1), 1 / b.std(ddof=1)
    return float(np.clip(x / (x + y), lo, hi))


def forward_returns(f4_ledger_csv, n1_ledger_jsonl):
    """daily forward paper returns: 1D from the F4 ledger LS_RS mix between consecutive as-of days; N1 from the last
    PAPER-N1 cycle of each UTC day. Missing days are skipped (no fill)."""
    import pandas as pd
    r1 = rn = pd.Series(dtype=float)
    if Path(f4_ledger_csv).exists():
        f = pd.read_csv(f4_ledger_csv, parse_dates=["asof"]).drop_duplicates("asof").set_index("asof").LS_RS.astype(float)
        r1 = (f / f.shift(1) - 1).dropna()
    if Path(n1_ledger_jsonl).exists():
        L = [json.loads(l) for l in Path(n1_ledger_jsonl).read_text(encoding="utf-8").splitlines() if l.strip()]
        n = pd.Series({pd.Timestamp(r["T"]): float(r["equity"]) for r in L})
        d = n.groupby(n.index.normalize()).last()
        rn = (d / d.shift(1) - 1).dropna()
    return r1, rn


# ======================================================================= ledger
def append_ledger(path, rec):
    path = Path(path)
    prev = "GENESIS"
    if path.exists() and path.stat().st_size:
        tail = path.read_text(encoding="utf-8").strip().splitlines()[-1]
        try:
            prev = json.loads(tail)["line_sha256"]
        except (ValueError, KeyError) as e:                                 # amendment 2 §5: never auto-repaired
            raise RuntimeError(f"ledger {path} last line is corrupt ({e}): restore it by hand from the Drive copy") from e
    rec = dict(rec, prev_sha256=prev)
    rec["line_sha256"] = sha_b(json.dumps(rec, sort_keys=True, default=str).encode())
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        fh.flush(); os.fsync(fh.fileno())
    return rec


def write_json_atomic(path, obj, keep_prev=True):
    """amendment 2 §5: the old file is copied to <stem>.prev.json, the new one goes to a temp file (fsync) and replaces the
    old in one os.replace, so the path always holds a complete version."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=1, default=str))
        fh.flush(); os.fsync(fh.fileno())
    if keep_prev and path.exists():
        shutil.copy2(path, path.with_name(path.stem + ".prev.json"))
    os.replace(tmp, path)
