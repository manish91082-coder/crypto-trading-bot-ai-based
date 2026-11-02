"""Unit checks of PAPER-N1 amendment 2 (no network). Run: python src/audits/test_paper_amend2.py
C2a inactive held coin: not requested, closed at its last mark, noted   C2b perp_out: no new open, perp position closed at the
open, spot position kept   C2c exchangeInfo failure keeps the previous lists   C2d one listing call per UTC day; off in replay"""
import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "execution"))
import paper_n1_portfolio as N

res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def up_bars(T, freq, n, down=False):                         # a steady up (or down) trend: trend families are "on"
    idx = pd.date_range(end=T, periods=n, freq=freq)
    c = np.linspace(3.0, 1.0, n) if down else np.linspace(1.0, 3.0, n)
    return pd.DataFrame(dict(open=c, high=c * 1.01, low=c * 0.99, close=c * 1.002, volume=1.0), index=idx)


class Src:
    def __init__(self, coins, spot=None, perp=None, fail=False, liquid=()):
        self.n_req, self.errors, self.coins, self.req, self.calls, self.fail = 0, [], coins, set(), 0, fail
        self.liquid = set(liquid)
        self.spot, self.perp = spot or {}, perp or {}

    def klines(self, sym, interval, T, n):
        self.req.add(sym)
        if sym not in self.coins:
            return None
        return up_bars(T, {"4h": "4h", "1d": "1D", "1h": "1h"}[interval], min(n, 400), down=sym in self.liquid)

    def funding(self, *a): return []

    def perp_daily_qv(self, perp, T):
        self.req.add(perp)                                   # perp volume requests count as requests too
        if perp not in {N.PERP[c] for c in self.liquid}:
            return None
        return pd.Series(100e6, index=pd.date_range(end=T.floor("D") - pd.Timedelta(days=1), periods=30, freq="D"))

    def listing(self):
        self.calls += 1
        if self.fail:
            return None
        return ({c: self.spot.get(c, "TRADING") for c in set(N.CORE10) | set(N.U2X)},
                {N.PERP[c]: self.perp.get(c, ("TRADING", N.FAR_DELIVERY_MS)) for c in N.PERP})


def fresh(pos=None):
    return dict(cash=10_000.0, pos=pos or {}, month="2026-10", E_m=10_000.0, last_T="2026-10-24 00:00:00", d_w={}, init_tfs=[])


T = pd.Timestamp("2026-10-24 04:00")
inact = "SXPUSDT" if "SXPUSDT" in N.U2X else N.U2X[-1]
pos_a = {f"C|{inact}|4h|0": dict(sleeve="C", side=-1, entry=0.40, notional=50.0, units=-125.0, venue="perp", t="2026-10-21 04:00", last_px=0.30, fee=0.00054)}
liq = next(c for c in N.U2X if c != inact and c in N.PERP)       # a liquid, falling U2X coin: sleeve C opens, so the
st = fresh(copy.deepcopy(pos_a)); src = Src(["ADAUSDT", liq], spot={inact: "BREAK"}, liquid=[liq])   # liquid count runs
rec = N.cycle(src, st, T)
c_opens = sum(a["a"] == "open" and a["k"].startswith(f"C|{liq}|") for a in rec["actions"])
cl = [a for a in rec["actions"] if a["a"] == "close" and a["k"] == f"C|{inact}|4h|0"]
ok("C2a", c_opens > 0 and inact not in src.req and N.PERP[inact] not in src.req and not st["pos"].get(f"C|{inact}|4h|0") and len(cl) == 1 and cl[0]["why"] == "delist" and cl[0]["px"] == 0.30
   and abs(cl[0]["pnl"] - (-125.0 * (0.30 - 0.40))) < 1e-9 and any("delist close" in n for n in rec["notes"]) and inact in rec["delisting"]["inactive"],
   f"inactive {inact}: not requested (klines nor perp volume; C opens on {liq}: {c_opens}), closed 'delist' at last mark 0.30 (pnl {cl[0]['pnl'] if cl else None}), noted, listed")

coin = "ADAUSDT"
pos_b = {f"A|{coin}|4h|0": dict(sleeve="A", side=1, entry=1.0, notional=50.0, units=50.0, venue="spot", t="2026-10-21 04:00", last_px=1.0, fee=0.00085),
         f"A|{coin}|8h|0": dict(sleeve="A", side=1, entry=1.0, notional=50.0, units=50.0, venue="perp", t="2026-10-21 04:00", last_px=1.0, fee=0.00054)}
ctrl = fresh(); rc = N.cycle(Src([coin]), ctrl, T)
n_open_ctrl = sum(a["a"] == "open" and a["k"].split("|")[1] == coin for a in rc["actions"])
st = fresh(copy.deepcopy(pos_b)); rb = N.cycle(Src([coin], perp={coin: ("SETTLING", 1)}), st, T)
opens = [a for a in rb["actions"] if a["a"] == "open" and a["k"].split("|")[1] == coin]
closed = {a["k"]: a for a in rb["actions"] if a["a"] == "close"}
open_px = float(up_bars(T, "4h", 400).loc[T, "open"])
ok("C2b", n_open_ctrl > 0 and not opens and f"A|{coin}|8h|0" in closed and closed[f"A|{coin}|8h|0"]["why"] == "delist"
   and abs(closed[f"A|{coin}|8h|0"]["px"] - open_px) < 1e-12 and f"A|{coin}|4h|0" in st["pos"] and coin in rb["delisting"]["perp_out"],
   f"perp_out {coin}: control opens {n_open_ctrl} -> 0 opens; perp position closed 'delist' at the open {open_px:.6f}; spot position kept")

st = fresh(); st["delist"] = dict(day="2026-10-23", inactive=["SXPUSDT"], perp_out=["FTTUSDT"])
rc2 = N.cycle(Src([coin], fail=True), st, T)
ok("C2c", rc2["delisting"] == dict(day="2026-10-23", inactive=["SXPUSDT"], perp_out=["FTTUSDT"]) and any("exchangeInfo unavailable" in n for n in rc2["notes"]),
   f"listing failure: previous lists kept {rc2['delisting']}, noted")

st = fresh(); s1 = Src([coin])
for t in ("2026-10-24 04:00", "2026-10-24 08:00", "2026-10-24 12:00"):
    N.cycle(s1, st, pd.Timestamp(t))
c_same = s1.calls
N.cycle(s1, st, pd.Timestamp("2026-10-25 00:00"))


class NoListing(Src):
    listing = None


rep = N.Replay()
ok("C2d", c_same == 1 and s1.calls == 2 and not hasattr(rep, "listing") and N.delisting(rep, fresh(), T, []) == (set(), set(), "off"),
   f"listing calls: 3 cycles on one day -> {c_same}, next day -> {s1.calls}; Replay has no listing -> rule off")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
