"""Real-time ZigZag pivot timeline (A0 amendment 2). Replays zigzag_pivots' event list: a confirmation pushes a pivot,
a flip (failure) pops the last one. Gives what a live system knew at any time T, without hindsight."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ladder_sessions as L
import swing_anatomy_phase1 as SA

K = 3.0


def bars4h(coin):
    h = SA.load_spliced(coin, "1h", [])
    return SA.clip_atr(SA.agg(h, "4h"))[0], h


def label_of(cur, kind, price):
    prev = next((p for p in reversed(cur) if p["kind"] == kind), None)
    if prev is None:
        return None
    return ("HH" if price > prev["price"] else "LH") if kind == "H" else ("HL" if price > prev["price"] else "LL")


def state_now(cur):
    lh = next((p["label"] for p in reversed(cur) if p["kind"] == "H" and p["label"] is not None), None)
    ll = next((p["label"] for p in reversed(cur) if p["kind"] == "L" and p["label"] is not None), None)
    return L.state_of(lh, ll)


class Timeline:
    """events in time order; .at(T) returns the live pivot list (copies) after all events with time <= T."""

    def __init__(self, b):
        ev = []
        SA.SS.zigzag_pivots(b, K, ev)
        self.et = SA.end_times("4h", b.timestamp.values)
        self.atr = b.ATR_14.values
        self.ev = sorted(ev, key=lambda e: e["seq"])
        self.times = np.array([self.et[e["confirm_idx"]] for e in self.ev])
        assert (np.diff(self.times.astype("int64")) >= 0).all(), "event times not monotone"
        self.failed_seq = {e["seq"] for e in self.ev if e.get("failed")}

    def walk(self):
        """yield (event, current list after applying it, state) for every event in order."""
        cur = []
        for e in self.ev:
            if e["flip"]:
                cur.pop()
            else:
                lab = label_of(cur, e["kind"], e["ref_price"])
                cur.append(dict(idx=e["pivot_idx"], kind=e["kind"], price=e["ref_price"], ci=e["confirm_idx"], label=lab,
                                seq=e["seq"], failed=e["seq"] in self.failed_seq))
            yield e, cur, state_now(cur)

    def at_many(self, Ts):
        """live list snapshot (list of dicts) and state for each T (Ts sorted ascending)."""
        out, cur, i = [], [], 0
        gen = self.walk()
        pending = next(gen, None)
        snap_cur, snap_state = [], None
        for T in Ts:
            t64 = np.datetime64(T)
            while pending is not None and self.times[i] <= t64:
                _, cur_, st_ = pending
                snap_cur, snap_state = [dict(p) for p in cur_], st_
                i += 1
                pending = next(gen, None)
            out.append((snap_cur, snap_state))
        return out


def swing_signals(coin, b, start, end):
    """S-LAD and S-DTB signals from the live timeline: list of (signal, side, known_time, pivot_price, atr, failed_later)."""
    tl = Timeline(b)
    sig = []
    for e, cur, st in tl.walk():
        if e["flip"]:
            continue
        p = cur[-1]
        kt = pd.Timestamp(tl.et[p["ci"]])
        A = tl.atr[p["ci"]]
        if not (start <= kt < end) or not np.isfinite(A) or A <= 0:
            continue
        if p["kind"] == "L" and p["label"] == "HL" and st == "UP":
            sig.append(("S-LAD", "long", kt, p["price"], A, p["failed"]))
        if p["kind"] == "H" and p["label"] == "LH" and st == "DOWN":
            sig.append(("S-LAD", "short", kt, p["price"], A, p["failed"]))
        same = [q for q in cur[:-1] if q["kind"] == p["kind"]]
        if same and len(cur) >= 2:
            a = same[-1]
            a_start = tl.atr[cur[-2]["idx"]]
            if np.isfinite(a_start) and abs(p["price"] - a["price"]) <= 0.5 * a_start:
                if p["kind"] == "L" and p["label"] == "HL":
                    sig.append(("S-DTB", "long", kt, p["price"], A, p["failed"]))
                if p["kind"] == "H" and p["label"] == "LH":
                    sig.append(("S-DTB", "short", kt, p["price"], A, p["failed"]))
    return sig, tl
