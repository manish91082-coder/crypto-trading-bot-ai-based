"""E-4 failure tests for the ECO executor (protocol §7) + unit checks of the netting / attribution math.
Mock exchange in memory (deterministic); T8 uses the REAL public endpoints (no key). Run: python src/audits/test_eco_core.py"""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "eco"))
import eco_core as C
import eco_exchange as X
import eco_orchestrator as O

res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


class Crash(Exception):
    pass


class MockEnv:
    mode = "mock"

    def __init__(self):
        self.px = {"BTCUSDT": 100_000.0, "ETHUSDT": 4_000.0, "FETUSDT": 0.5}
        self.filt = {p: dict(step=0.001 if p != "FETUSDT" else 1.0, min_qty=0.001 if p != "FETUSDT" else 1.0, max_qty=1e9, tick=0.01,
                             min_notional=5.0) for p in self.px}
        self.pos, self.cash, self.orders, self.by_cid = {}, 0.0, [], {}
        self.fail_sym, self.crash_after_fill, self.last_error = None, False, None
        self.n1_data, self.f4_data, self.hi = None, None, {}
        self.disk = None
        self.algo = {}

    def notes(self):
        return []

    def n1(self, now):
        if isinstance(self.n1_data, Exception):
            raise self.n1_data
        if self.n1_data is None:
            raise C.Frozen("no n1")
        return self.n1_data

    def f4(self, now):
        if isinstance(self.f4_data, Exception):
            raise self.f4_data
        if self.f4_data is None:
            raise C.Frozen("no f4")
        return self.f4_data

    def filters(self):
        return self.filt

    def prices(self, perps):
        return {p: self.px[p] for p in perps if p in self.px}

    def prices_after(self):
        return dict(self.px)

    def highs(self, perps, since, now):
        return {p: self.hi[p] for p in perps if p in self.hi}

    def wallet(self):
        return None

    def positions(self):
        return dict(self.pos)

    def journal_written(self, st):
        self.disk = copy.deepcopy(st)

    def execute(self, o, cid):
        if o["perp"] == self.fail_sym:
            self.last_error = {"status": 400, "msg": "mock 400"}
            return None
        q, p = o["qty"], self.px[o["perp"]]
        self.pos[o["perp"]] = self.pos.get(o["perp"], 0.0) + q
        if abs(self.pos[o["perp"]]) < 1e-12:
            self.pos.pop(o["perp"])
        self.cash -= q * p + 0.00054 * abs(q) * p
        self.orders.append((o["perp"], q)); self.by_cid[cid] = (q, p)
        if self.crash_after_fill:
            raise Crash("crash after the fill, before the ledger write")
        return q, p

    def recover(self, j):
        return self.by_cid.get(j["cid"])

    def funding(self, held, since, now):
        return {}

    # ---- exchange stops (algo orders) in memory
    def stop_status(self, ex):
        """as Query Algo Order (amendment 2 §4): (algoStatus, actualQty or None, actualPrice or None)"""
        return {sid: (self.algo.get(e["algoId"], {}).get("status", "MISSING"), self.algo.get(e["algoId"], {}).get("aq"),
                      self.algo.get(e["algoId"], {}).get("ap")) for sid, e in ex.items()}

    def place_stop(self, spec):
        self.n_algo = getattr(self, "n_algo", 0) + 1
        self.algo[self.n_algo] = dict(spec, status="NEW")
        return self.n_algo

    def cancel_stop(self, e):
        a = self.algo.get(e["algoId"])
        if a and a["status"] == "NEW":
            a["status"] = "CANCELED"
        return True

    def fire(self, kind, perp):
        """the exchange triggers the open stop of this kind on perp at its trigger price"""
        for aid, a in self.algo.items():
            if a["status"] == "NEW" and a["kind"] == kind and a["perp"] == perp:
                q = a["qty"] if a["side"] == "BUY" else -a["qty"]
                if kind == "G":
                    q = -self.pos.get(perp, 0.0)
                self.pos[perp] = self.pos.get(perp, 0.0) + q
                if abs(self.pos[perp]) < 1e-12:
                    self.pos.pop(perp)
                self.cash -= q * a["trigger"] + 0.00054 * abs(q) * a["trigger"]
                a.update(status="FINISHED", aq=abs(q), ap=a["trigger"])          # filled at the trigger (as the old mock)
                return aid

    def equity(self):
        return self.cash + sum(q * self.px[p] for p, q in self.pos.items())


CFG = dict(capital=10_000.0, weights={"N1": 0.5, "1D": 0.5}, coin_cap=0.20, gross_cap=1.50, band_frac=0.0025, fee=0.00054,
           max_orders=40, kill_K=0.30, n1_perp_names={}, guard_D=0.50, guard_on=True)
NOW = pd.Timestamp("2026-10-22 10:50")


def n1_book(scale=1.0):
    # N1 paper: equity 10,000; BTC long 0.01 (1,000 USDT = 10%), ETH long 0.25 (10%), FET short 2,000 (10%)
    return 10_000.0, {"N1|A|BTCUSDT|4h|0": ("BTCUSDT", 1, 0.01 * scale, "perp"), "N1|A|ETHUSDT|4h|1": ("ETHUSDT", 1, 0.25 * scale, "perp"),
                      "N1|C|FETUSDT|4h|0": ("FETUSDT", -1, 2000.0 * scale, "perp")}, {}


def f4_book():
    dec = {"D1": dict(equity_close=10_000.0, longs={"BTCUSDT": dict(units=0.01, entry_time="x")}, sell=[], buy=["ETHUSDT"],
                      shorts={"FETUSDT": dict(units=4000.0, entry=0.5, stop=0.75, entry_time="y")}, cover=[], short=[])}
    eq, comps = C.parse_f4(dec)
    return eq, comps, {}


# ---------------- U: math ----------------
env = MockEnv(); env.n1_data = n1_book(); env.f4_data = f4_book()
st = O.new_state()
rec = O.cycle(env, st, CFG, NOW)
# expected targets (E_m 10,000): N1 a=0.5 -> BTC 500, ETH 500, FET -500 ; 1D a=0.5 of 10,000 paper: BTC 1,000 -> 500, ETH buy 0.1*10,000 -> 500, FET -2,000 -> -1,000
exp = {"BTCUSDT": (500 + 500) / 100_000, "ETHUSDT": (500 + 500) / 4_000, "FETUSDT": -(500 + 1000) / 0.5}
got = {p: env.pos.get(p, 0.0) for p in exp}
ok("U1", all(abs(got[p] - C.floor_step(exp[p], env.filt[p]["step"])) < 1e-9 for p in exp), f"netted positions {got} vs expected {exp}")
ok("U2", abs(C.equity_account(st["held"], env.px) - env.equity()) < 1e-6, f"attribution identity: comps {C.equity_account(st['held'], env.px):.6f} = exchange {env.equity():.6f}")
ok("U3", rec["reconcile_mismatch"] == {} and C.held_net(st["held"]) == env.pos, "held net == exchange after the cycle")
n_orders = len(env.orders)
rec2 = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
ok("U4", len(env.orders) == n_orders, f"second cycle with unchanged targets sends no order (band): {len(rec2['orders'])} orders")
# internal transfer: N1 closes BTC, 1D doubles BTC -> net unchanged, attribution moves internally, no order
env.n1_data = (10_000.0, {k: v for k, v in n1_book()[1].items() if "BTC" not in k}, {})
dec2 = {"D1": dict(equity_close=10_000.0, longs={"BTCUSDT": dict(units=0.02, entry_time="x"), "ETHUSDT": dict(units=0.25, entry_time="z")}, sell=[], buy=[],
                   shorts={"FETUSDT": dict(units=4000.0, entry=0.5, stop=0.75, entry_time="y")}, cover=[], short=[])}
env.f4_data = C.parse_f4(dec2) + ({},)
before = len(env.orders)
O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=2))
qb = {k: h["qty"].get("BTCUSDT", 0.0) for k, h in st["held"].items()}
ok("U5", len(env.orders) == before and abs(qb.get("N1|A|BTCUSDT|4h|0", 0.0)) < 1e-12 and abs(qb["1D|D1|L|BTCUSDT"] - 0.01) < 1e-12
   and abs(C.equity_account(st["held"], env.px) - env.equity()) < 1e-6, f"internal transfer without an order; BTC by component {qb}")
# funding: signed split
h = {"a": dict(qty={"X": 2.0}, cash=0.0, fees=0.0, funding=0.0, entry_px={}), "b": dict(qty={"X": -1.0}, cash=0.0, fees=0.0, funding=0.0, entry_px={})}
C.allocate_funding(h, "X", -10.0)          # net long 1 pays 10 => a (2) pays 20, b (-1) receives 10
ok("U6", abs(h["a"]["cash"] + 20) < 1e-12 and abs(h["b"]["cash"] - 10) < 1e-12, f"funding split by signed share {h['a']['cash']}, {h['b']['cash']}")
# caps
ct = {"x": dict(perp="BTCUSDT", notional_eco=3000.0, qty=0.03), "y": dict(perp="BTCUSDT", notional_eco=1000.0, qty=0.01),
      "z": dict(perp="ETHUSDT", notional_eco=-15000.0, qty=-3.75)}
sc = C.apply_caps(ct, 10_000.0, 0.20, 1.50)
net = {"BTCUSDT": ct["x"]["notional_eco"] + ct["y"]["notional_eco"], "ETHUSDT": ct["z"]["notional_eco"]}
ok("U7", abs(net["BTCUSDT"]) <= 2000 + 1e-9 and abs(net["ETHUSDT"]) <= 2000 + 1e-9 and abs(ct["x"]["notional_eco"] / ct["y"]["notional_eco"] - 3) < 1e-12,
   f"per-coin cap 20% applied proportionally {net}; scalings {sc}")
# stop suppression + release
env.hi = {"FETUSDT": 0.76}
O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=3))
fet_1d = st["held"].get("1D|D1|S|FETUSDT", {"qty": {}})["qty"].get("FETUSDT", 0.0)
ok("U8", "1D|D1|S|FETUSDT" in st["suppressed"] and abs(fet_1d) < 1e-12 and abs(env.pos["FETUSDT"] + 1000) < 1e-9,
   f"1D FET short stopped (high 0.76 >= 0.75): component {fet_1d}, net FET {env.pos.get('FETUSDT')} (N1 part stays)")
env.hi = {}
dec3 = copy.deepcopy(dec2); dec3["D1"]["shorts"] = {}
env.f4_data = C.parse_f4(dec3) + ({},)
O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=4))
ok("U9", "1D|D1|S|FETUSDT" not in st["suppressed"], "suppression released once F4 no longer lists the short")

# ---------------- T1 crash after fill, before the ledger ----------------
env = MockEnv(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off")
st = O.new_state()
env.crash_after_fill = True
try:
    O.cycle(env, st, CFG, NOW)
    crashed = False
except Crash:
    crashed = True
st = copy.deepcopy(env.disk)                     # what is on disk: the write-ahead state with the journal entry
env.crash_after_fill = False
n_before = list(env.orders)
O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
first = n_before[0][0]
ok("T1", crashed and sum(1 for p, _ in env.orders if p == first) == 1 and C.held_net(st["held"]) == env.pos
   and abs(C.equity_account(st["held"], env.px) - env.equity()) < 1e-6,
   f"crash after {first} fill: next cycle recovered it from the journal, {first} ordered once; held == exchange")

# ---------------- T2 lock ----------------
d = Path(tempfile.mkdtemp())
try:
    with O.Lock(d / "eco.lock"):
        try:
            with O.Lock(d / "eco.lock"):
                second = "entered"
        except RuntimeError:
            second = "refused"
    ok("T2", second == "refused" and not (d / "eco.lock").exists(), f"second concurrent run {second}; lock removed after the run")
finally:
    shutil.rmtree(d)

# ---------------- T3 stale producer ----------------
env = MockEnv(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, CFG, NOW)
held0 = copy.deepcopy(C.held_net(st["held"])); n0 = len(env.orders)
env.n1_data = C.Frozen("N1 stale: 6 h old")
env.px["BTCUSDT"] = 120_000.0
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
ok("T3", rec["frozen_strategies"].get("N1", "").startswith("N1 stale") and len(env.orders) == n0 and C.held_net(st["held"]) == held0,
   f"stale N1 frozen: holdings kept, no orders ({len(env.orders) - n0})")

# ---------------- T4 producer hash mismatch (real loaders on temp copies) ----------------
d = Path(tempfile.mkdtemp())
try:
    (d / "paper").mkdir()
    orders = {"LS_RS": {"D1": dict(equity_close=10_000.0, longs={}, shorts={}, sell=[], buy=[], cover=[], short=[])}}
    (d / "paper" / "orders_2026-10-21.json").write_text(json.dumps(orders))
    good = C.sha_f(d / "paper" / "orders_2026-10-21.json")
    pd.DataFrame([dict(asof="2026-10-21", orders_sha256=good, line_sha256="l1")]).to_csv(d / "ledger.csv", index=False)
    a_ok = C.load_f4(d, pd.Timestamp("2026-10-22"))[0] == 10_000.0
    (d / "paper" / "orders_2026-10-21.json").write_text(json.dumps(orders) + " ")
    try:
        C.load_f4(d, pd.Timestamp("2026-10-22")); f4_frozen = False
    except C.Frozen:
        f4_frozen = True
    n1d = d / "n1"; n1d.mkdir()
    l1 = dict(T="2026-10-22 08:00:00", equity=10_000.0, prev_sha256="GENESIS")
    l1["line_sha256"] = C.sha_b(json.dumps(l1, sort_keys=True, default=str).encode())
    (n1d / "ledger.jsonl").write_text(json.dumps(l1, sort_keys=True) + "\n")
    (n1d / "state.json").write_text(json.dumps(dict(last_T="2026-10-22 08:00:00", pos={})))
    n1_ok = C.load_n1(n1d, pd.Timestamp("2026-10-22 10:50"))[0] == 10_000.0
    l1["equity"] = 99_999.0
    (n1d / "ledger.jsonl").write_text(json.dumps(l1, sort_keys=True) + "\n")
    try:
        C.load_n1(n1d, pd.Timestamp("2026-10-22 10:50")); n1_frozen = False
    except C.Frozen:
        n1_frozen = True
    ok("T4", a_ok and f4_frozen and n1_ok and n1_frozen, "F4 orders altered -> Frozen; N1 ledger line altered -> Frozen (untouched files load)")
finally:
    shutil.rmtree(d)

# ---------------- T5 HTTP 400 on one symbol ----------------
env = MockEnv(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off"); env.fail_sym = "ETHUSDT"
st = O.new_state()
rec = O.cycle(env, st, CFG, NOW)
ok("T5", "ETHUSDT" not in env.pos and "BTCUSDT" in env.pos and "FETUSDT" in env.pos and any("ETHUSDT" in n for n in rec["notes"])
   and C.held_net(st["held"]) == env.pos, f"ETH order rejected (logged), BTC and FET proceed; held == exchange")

# ---------------- T6 exchange position != ledger ----------------
env = MockEnv(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, CFG, NOW)
env.pos["BTCUSDT"] += 0.5                                # someone changed the account by hand
n0 = len(env.orders)
env.n1_data = n1_book(scale=2.0)                         # targets change on every symbol
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
new = env.orders[n0:]
ok("T6", "BTCUSDT" in rec["reconcile_mismatch"] and not any(p == "BTCUSDT" for p, _ in new) and any(p == "ETHUSDT" for p, _ in new),
   f"BTC mismatch -> BTC frozen (no order), other symbols trade; orders {new}")

# ---------------- T7 kill switch ----------------
env = MockEnv(); env.n1_data = n1_book(scale=5.0); env.f4_data = C.Frozen("off")
st = O.new_state()
cfg7 = dict(CFG, coin_cap=1.0, gross_cap=5.0)
O.cycle(env, st, cfg7, NOW)
env.px = {"BTCUSDT": 30_000.0, "ETHUSDT": 1_000.0, "FETUSDT": 2.0}   # a crash against every position
rec = O.cycle(env, st, cfg7, NOW + pd.Timedelta(hours=1))
flat_after_kill = env.pos == {}
n0 = len(env.orders)
rec2 = O.cycle(env, st, cfg7, NOW + pd.Timedelta(hours=2))
ok("T7", st["halted"] is not None and flat_after_kill and len(env.orders) == n0 and rec2.get("halted"),
   f"kill switch: halted '{(st['halted'] or '')[:70]}...', book flat, next cycle sends nothing")

# ---------------- T8 real public endpoints: demo vs mainnet filters ----------------
try:
    fd = X.parse_filters(X.Public(X.DEMO).exchange_info())
    fm = X.parse_filters(X.Public(X.PUBLIC).exchange_info())
    syms = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT",
            "FETUSDT", "ONDOUSDT", "SUIUSDT", "UNIUSDT", "WLDUSDT", "NEARUSDT", "QNTUSDT", "1000BONKUSDT"]
    diff = {s: (fd.get(s), fm.get(s)) for s in syms if fd.get(s) != fm.get(s)}
    pxd = X.Public(X.DEMO).prices(syms)
    ok("T8", len(fd) > 100 and len(fm) > 100 and all(s in pxd for s in syms),
       f"demo host: {len(fd)} TRADING USDT perps, mainnet public {len(fm)}; mark prices for {len(pxd)}/{len(syms)} target symbols; "
       f"filter differences on target symbols: {diff if diff else 'none'}")
except Exception as e:                                                  # noqa: BLE001
    ok("T8", False, f"public endpoint error {e}")

# ---------------- S: exchange stops (amendment 1 §2, §3) ----------------
def openst(env, kind=None):
    return {aid: a for aid, a in env.algo.items() if a["status"] == "NEW" and (kind is None or a["kind"] == kind)}


env = MockEnv(); env.n1_data = n1_book(); env.f4_data = f4_book()
st = O.new_state()
rec = O.cycle(env, st, CFG, NOW)
cs = [a for a in openst(env, "C").values()]
gs = {a["perp"]: a for a in openst(env, "G").values()}
ok("S1", len(cs) == 1 and cs[0]["perp"] == "FETUSDT" and cs[0]["side"] == "BUY" and abs(cs[0]["trigger"] - 0.75) < 1e-12 and abs(cs[0]["qty"] - 2000) < 1e-9
   and set(gs) == set(env.pos) and abs(gs["BTCUSDT"]["trigger"] - 50_000) < 1e-6 and gs["BTCUSDT"]["side"] == "SELL"
   and abs(gs["FETUSDT"]["trigger"] - 0.75) < 1e-12 and gs["FETUSDT"]["working"] == "MARK_PRICE" and abs(gs["FETUSDT"]["qty"] - 3000) < 1e-9,
   f"1D FET short stop BUY 2000 @ 0.75 (F4 stop), guards on every net position at mark x (1 -/+ 0.5): {sorted((a['perp'], a['side'], a['qty'], a['trigger']) for a in gs.values())}")
n_algo = len(env.algo)
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
ok("S2", len(env.algo) == n_algo and rec["stops"]["placed"] == 0 and rec["stops"]["cancelled"] == 0, "unchanged book: no stop churn")
env.px["FETUSDT"] = 0.80
env.fire("C", "FETUSDT")                                     # the exchange stop of the 1D short fires
n_ord = len(env.orders)
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=2))
fet = {k: h["qty"].get("FETUSDT", 0.0) for k, h in st["held"].items() if "FET" in k}
ok("S3", "1D|D1|S|FETUSDT" in st["suppressed"] and abs(fet["1D|D1|S|FETUSDT"]) < 1e-12 and rec["reconcile_mismatch"] == {}
   and C.held_net(st["held"]) == env.pos and not any(p == "FETUSDT" and q < 0 for p, q in env.orders[n_ord:])
   and abs(C.equity_account(st["held"], env.px) - env.equity()) < 1e-6,
   f"fired 1D stop booked at its trigger, component suppressed, no re-short; FET by component {fet}; held == exchange")
env.px["BTCUSDT"] = 49_000.0
env.fire("G", "BTCUSDT")                                     # the guard of BTC fires (a >= 50% fall)
n_ord = len(env.orders)
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=3))
ok("S4", "BTCUSDT" in st["guard_fired"] and "BTCUSDT" not in C.held_net(st["held"]) and "BTCUSDT" not in env.pos
   and not any(p == "BTCUSDT" for p, _ in env.orders[n_ord:]) and abs(C.equity_account(st["held"], env.px) - env.equity()) < 1e-6,
   "guard fired: every BTC component booked to 0, BTC frozen (no re-entry), attribution == exchange")
# S5: N1 long FET bigger than the 1D short -> net long -> the component stop stays virtual
env = MockEnv(); env.f4_data = f4_book()
env.n1_data = (10_000.0, {"N1|A|FETUSDT|4h|0": ("FETUSDT", 1, 8000.0, "perp")}, {})
st = O.new_state()
rec = O.cycle(env, st, CFG, NOW)
ok("S5", not openst(env, "C") and any("virtual only" in n for n in rec["stops"]["notes"]) and env.pos.get("FETUSDT", 0) > 0,
   f"net FET long {env.pos.get('FETUSDT')}: no exchange stop for the 1D short component (virtual only, logged)")
# S6: kill switch -> book flat -> every stop cancelled
env = MockEnv(); env.n1_data = n1_book(scale=5.0); env.f4_data = C.Frozen("off")
st = O.new_state()
cfg7 = dict(CFG, coin_cap=1.0, gross_cap=5.0)
O.cycle(env, st, cfg7, NOW)
had = len(openst(env))
env.px = {"BTCUSDT": 60_000.0, "ETHUSDT": 2_400.0, "FETUSDT": 0.9}
O.cycle(env, st, cfg7, NOW + pd.Timedelta(hours=1))
ok("S6", had > 0 and st["halted"] and env.pos == {} and not openst(env) and st["stops"] == {}, f"kill switch: {had} stops before, 0 open after, book flat")

# ---------------- X: cut-over adopt (amendment 1 §4.2) ----------------
import eco_cutover as CU
f6 = {"sleeves": {"D1": {"FETUSDT": dict(perp="FETUSDT", qty=200.0, fill=0.45, stop=0.675, algoId=1)}, "H4": {}, "H1": {"ETHUSDT": dict(perp="ETHUSDT", qty=0.05, fill=4100.0, stop=6150.0, algoId=2)}}}
env = MockEnv(); env.pos = {"FETUSDT": -200.0, "ETHUSDT": -0.05}
st = CU.adopt_state(f6, env.px, 5000.0, 10_000.0)
ok("X1", abs(C.equity_account(st["held"], env.px)) < 1e-9 and C.held_net(st["held"]) == env.pos and set(st["held"]) == {"1D|D1|S|FETUSDT", "1D|H1|S|ETHUSDT"},
   "adopted F6 shorts: components 1D|D1|S|FET, 1D|H1|S|ETH; held == account; P&L starts at 0 at the cut-over mark")
base_acct = env.equity()                                   # account value at the cut-over (positions, cash 0)
env.n1_data = n1_book(); env.f4_data = f4_book()
rec = O.cycle(env, st, CFG, NOW)
pnl_acct = env.equity() - base_acct
ok("X2", rec["reconcile_mismatch"] == {} and C.held_net(st["held"]) == env.pos and abs(C.equity_account(st["held"], env.px) - pnl_acct) < 1e-9
   and abs(st["held"].get("1D|H1|S|ETHUSDT", {"qty": {}})["qty"].get("ETHUSDT", 0.0)) < 1e-12 and pnl_acct < 0,
   f"first cycle after adoption: H1 ETH short (no longer in F4) closed, targets netted; held == account {env.pos}; "
   f"attribution P&L {C.equity_account(st['held'], env.px):.6f} == account P&L since cut-over {pnl_acct:.6f} (fees only)")


# ---------------- A2: amendment 2 (logs/eco/ECO_AMENDMENT_2_PREREGISTERED.md §9) ----------------
import subprocess
import eco_reset as RS


class MockEnv2(MockEnv):
    """MockEnv + hidden prices, unconfirmed fills, a funding rate and many symbols."""

    def __init__(self, n_extra=0):
        super().__init__()
        self.hide, self.unconfirm_sym, self.rate = set(), None, None
        for i in range(n_extra):
            p = f"S{i:02d}USDT"
            self.px[p] = 1.0
            self.filt[p] = dict(step=1.0, min_qty=1.0, max_qty=1e9, tick=0.0001, min_notional=5.0)

    def prices(self, perps):
        return {p: self.px[p] for p in perps if p in self.px and p not in self.hide}

    def prices_after(self):
        return {p: v for p, v in self.px.items() if p not in self.hide}

    def execute(self, o, cid):
        if o["perp"] == self.unconfirm_sym:                   # the exchange fills, the answer is NEW / qty 0
            q, p = o["qty"], self.px[o["perp"]]
            self.pos[o["perp"]] = self.pos.get(o["perp"], 0.0) + q
            self.cash -= q * p + 0.00054 * abs(q) * p
            self.orders.append((o["perp"], q)); self.by_cid[cid] = (q, p)
            self.last_error, self.unconfirmed = {"status": "NEW", "executedQty": "0"}, True
            return None
        return super().execute(o, cid)

    def funding(self, held, since, now):
        return {p: -q * self.px[p] * self.rate for p, q in held.items()} if self.rate else {}


def n1_many(n, units=lambda i: 300.0 + 10 * i):
    return 10_000.0, {f"N1|A|S{i:02d}USDT|4h|0": (f"S{i:02d}USDT", 1, units(i), "perp") for i in range(n)}, {}


cfgw = dict(CFG, coin_cap=1.0, gross_cap=50.0)
# A2-1 kill with a frozen (mismatched) symbol -> flat on the exchange
env = MockEnv2(); env.n1_data = n1_book(scale=5.0); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, cfgw, NOW)
env.pos["BTCUSDT"] += 0.01                                       # mismatch -> BTC frozen
env.px = {"BTCUSDT": 30_000.0, "ETHUSDT": 1_000.0, "FETUSDT": 2.0}
rec = O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=1))
ok("A2-1", st["halted"] and env.pos == {} and "BTCUSDT" in rec["reconcile_mismatch"] and any("kill: frozen BTCUSDT" in n for n in rec["notes"]),
   f"kill with BTC frozen by a mismatch: exchange flat {env.pos}, note {[n for n in rec['notes'] if 'kill: frozen' in n]}")
# A2-12 max_orders: 45 symbols -> 40 largest sent, 5 recorded; A2-2 kill with > 40 symbols -> flat in one cycle
env = MockEnv2(n_extra=45); env.n1_data = n1_many(45); env.f4_data = C.Frozen("off")
st = O.new_state()
rec = O.cycle(env, st, cfgw, NOW)
sent = [p for p, _ in env.orders]
mo = [p for p, why in rec["skipped"] if why.startswith("max_orders")]
ok("A2-12", len(sent) == 40 and len(mo) == 5 and set(mo) == {f"S{i:02d}USDT" for i in range(5)},
   f"45 orders needed: 40 sent (largest first), left for the next cycle: {mo}")
O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=1))
n_open = len(env.pos)
env.px = {p: (0.3 if p.startswith("S") else v) for p, v in env.px.items()}
O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=2))
ok("A2-2", n_open == 45 and st["halted"] and env.pos == {}, f"kill with {n_open} symbols: all closed in one cycle, exchange {env.pos}")
# A2-3 halted cycle: a close that failed at the kill is done by the next (halted) cycle; equity is marked
env = MockEnv2(); env.n1_data = n1_book(scale=5.0); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, cfgw, NOW)
env.px = {"BTCUSDT": 50_000.0, "ETHUSDT": 2_000.0, "FETUSDT": 0.65}; env.fail_sym = "ETHUSDT"      # ~33 % drawdown
O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=1))
left = dict(env.pos); env.fail_sym = None
env.px["BTCUSDT"] = 51_000.0
rec = O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=2))
ok("A2-3", "ETHUSDT" in left and env.pos == {} and rec.get("halted") and "eco_equity" in rec and all(o["reduce_only"] for o in rec["orders"])
   and abs(C.equity_account(st["held"], env.px) - env.equity()) < 1e-6,
   f"halted: ETH left open at the kill {left} was closed reduce-only by the halted cycle; equity marked {rec.get('eco_equity'):.2f}")
# A2-4 reset tool: halt and peak reset; the next cycle trades again and does not re-kill
done = RS.apply(st, reset=True)
rec = O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=3))
ok("A2-4", done and st["halted"] is None and not rec.get("halted") and abs(st["peak"] - max(done[0]["peak_now"], st["eco_equity"])) < 1e-9
   and len(env.pos) > 0, f"reset: peak {done[0]['peak_was']:.2f} -> {done[0]['peak_now']:.2f}; next cycle not halted, positions {sorted(env.pos)}")
# A2-5 missing price: last-price marking, the kill switch still fires
env = MockEnv2(); env.n1_data = n1_book(scale=5.0); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, cfgw, NOW)
env.hide = {"BTCUSDT"}
env.px.update(ETHUSDT=1_000.0, FETUSDT=2.0)
rec = O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=1))
ok("A2-5", st["halted"] and rec["px_missing"] == ["BTCUSDT"] and env.pos == {},
   f"BTC price missing: marked at its last price, kill fired on the other symbols ({(st['halted'] or '')[:60]}...), exchange flat")
# A2-6 delisting announced -> closed, not reopened
env = MockEnv2(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, CFG, NOW)
had = "ETHUSDT" in env.pos
env.filt["ETHUSDT"]["delivery_ms"] = int(pd.Timestamp("2026-10-25 09:00").value // 10**6)
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
rec2 = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=2))
ok("A2-6", had and "ETHUSDT" not in env.pos and rec["delisting"] == ["ETHUSDT"] and not any(o["perp"] == "ETHUSDT" for o in rec2["orders"]),
   f"ETH deliveryDate set: closed ({rec['delisting']}), not reopened next cycle")
# A2-7 market answer NEW / qty 0: journal kept, nothing booked; recovered next cycle
env = MockEnv2(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off"); env.unconfirm_sym = "ETHUSDT"
st = O.new_state()
rec = O.cycle(env, st, CFG, NOW)
kept = [j["perp"] for j in st["journal"]]
eth_booked = C.held_net(st["held"]).get("ETHUSDT", 0.0)
env.unconfirm_sym = None
rec2 = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
eth_orders = sum(1 for p, _ in env.orders if p == "ETHUSDT")
try:
    C.allocate_fill({}, {}, "X", 1.0, 0.0, 0.0); zero_refused = False
except ValueError:
    zero_refused = True


class FakeDemo(X.Demo):
    def __init__(self, answers):
        super().__init__(); self.answers = list(answers)

    def query(self, sym, cid):
        return self.answers.pop(0) if self.answers else {"status": "NEW", "executedQty": "0"}


new0 = {"status": "NEW", "executedQty": "0", "avgPrice": None}
f_ok = FakeDemo([{"status": "FILLED", "executedQty": "2", "avgPrice": "10.5"}]).confirmed_fill(new0, "X", "c", wait=0)
f_no = FakeDemo([]).confirmed_fill(new0, "X", "c", wait=0)
ok("A2-7", kept == ["ETHUSDT"] and eth_booked == 0.0 and C.held_net(st["held"]) == env.pos and eth_orders == 1 and zero_refused
   and f_ok == (2.0, 10.5) and f_no is None,
   f"NEW/0 answer: journal kept {kept}, nothing booked; next cycle recovered it, ETH ordered once, held == exchange; "
   f"fill at price 0 refused; confirmed_fill {f_ok} / {f_no}")
# A2-8 stop statuses
env = MockEnv2(); env.n1_data = n1_book(); env.f4_data = f4_book()
st = O.new_state()
O.cycle(env, st, CFG, NOW)
cid_ = next(i for i, a in env.algo.items() if a["kind"] == "C" and a["status"] == "NEW")
env.algo[cid_]["status"] = "TRIGGERING"
held0 = copy.deepcopy(C.held_net(st["held"]))
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
kept_trig = any(e["algoId"] == cid_ for e in st["stops"].values()) and C.held_net(st["held"]) == held0
env.algo[cid_]["status"] = "FINISHED"                                  # engine cancelled it: no fill
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=2))
dropped = not any(e["algoId"] == cid_ for e in st["stops"].values()) and C.held_net(st["held"]) == held0 and "1D|D1|S|FETUSDT" not in st["suppressed"]
cid2 = next(i for i, a in env.algo.items() if a["kind"] == "C" and a["status"] == "NEW")
env.pos["FETUSDT"] += 500.0; env.cash -= 500.0 * 0.70 + 0.00054 * 500 * 0.70
env.algo[cid2].update(status="FINISHED", aq=500.0, ap=0.70)              # partial fill of the 2000 stop at 0.70
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=3))
ok("A2-8", kept_trig and dropped and "1D|D1|S|FETUSDT" in st["suppressed"] and C.held_net(st["held"]) == env.pos
   and abs(C.equity_account(st["held"], env.px) - env.equity()) < 1e-6,
   "TRIGGERING kept, nothing booked; FINISHED without fill dropped, nothing booked; FINISHED actualQty 500 @ 0.70 booked; held == exchange")


# A2-9 orphan / foreign algo orders (LiveEnv logic, fake demo account)
class FakeAlgo:
    def __init__(self):
        self.deleted = []

    def open_algo(self):
        return [dict(algoId=1, symbol="BTCUSDT", clientAlgoId="ecoabc"), dict(algoId=2, symbol="ETHUSDT", clientAlgoId="ecodef"),
                dict(algoId=3, symbol="FETUSDT", clientAlgoId="x_f6")]

    def signed(self, method, path, **p):
        self.deleted.append(p["algoId"]); return {}


le = O.LiveEnv.__new__(O.LiveEnv); le.mode = "demo"; le.demo = FakeAlgo(); le._open_algo = None
nts = []
foreign = le.algo_orphans({"G|BTCUSDT": dict(algoId=1)}, nts)
ok("A2-9", le.demo.deleted == [2] and [f["algoId"] for f in foreign] == [3], f"orphan eco stop 2 cancelled {le.demo.deleted}; foreign 3 left: {foreign}")
# A2-10 corrupt state -> failed record (no crash); atomic write keeps prev; corrupt ledger tail -> explicit error
d = Path(tempfile.mkdtemp(dir=R_ / "data"))
try:
    (d / "state.json").write_text('{"held": {')
    p_ = subprocess.run([sys.executable, str(R_ / "src" / "eco" / "eco_orchestrator.py"), "--mode", "plan", "--root", str(d)], capture_output=True, text=True)
    L_ = [json.loads(l) for l in (d / "ledger.jsonl").read_text().splitlines()]
    failed_rec = p_.returncode == 1 and len(L_) == 1 and L_[0]["ok"] is False and "JSONDecodeError" in L_[0]["error"] and (d / "state.json").read_text() == '{"held": {'
    C.write_json_atomic(d / "s2.json", {"v": 1}); C.write_json_atomic(d / "s2.json", {"v": 2})
    atomic = json.loads((d / "s2.json").read_text()) == {"v": 2} and json.loads((d / "s2.prev.json").read_text()) == {"v": 1}
    (d / "ledger.jsonl").write_text((d / "ledger.jsonl").read_text() + '{"broken')
    try:
        C.append_ledger(d / "ledger.jsonl", {"x": 1}); tail_err = False
    except RuntimeError:
        tail_err = True
    ok("A2-10", failed_rec and atomic and tail_err, f"corrupt state -> failed ledger record (exit {p_.returncode}), state untouched; "
       f"atomic write keeps .prev ({atomic}); corrupt ledger tail -> explicit error ({tail_err})")
finally:
    shutil.rmtree(d)
# A2-11 funding on pre-order positions
env = MockEnv2(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, CFG, NOW)
pre = dict(env.pos)
env.n1_data = n1_book(scale=2.0); env.rate = 0.001
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
exp_f = {p: -q * env.px[p] * 0.001 for p, q in pre.items()}
ok("A2-11", all(abs(rec["funding"][p] - exp_f[p]) < 1e-9 for p in exp_f) and env.pos != pre,
   f"funding on the positions held during the interval {({p: round(v, 4) for p, v in rec['funding'].items()})} (expected {({p: round(v, 4) for p, v in exp_f.items()})})")
# A2-13 frozen components are not scaled by the caps
env = MockEnv2(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, CFG, NOW)
h0 = copy.deepcopy(C.held_net(st["held"])); n0 = len(env.orders)
env.n1_data = C.Frozen("N1 stale")
rec = O.cycle(env, st, dict(CFG, coin_cap=0.02), NOW + pd.Timedelta(hours=1))
ok("A2-13", C.held_net(st["held"]) == h0 and len(env.orders) == n0, f"N1 frozen + coin cap 2%: frozen holdings unchanged, no orders; caps {rec['caps']}")
# A2-14 F4 C1 = False -> 1D frozen
d = Path(tempfile.mkdtemp())
try:
    (d / "paper").mkdir()
    (d / "paper" / "orders_2026-10-21.json").write_text(json.dumps({"LS_RS": {}}))
    pd.DataFrame([dict(asof="2026-10-21", C1=False, orders_sha256=C.sha_f(d / "paper" / "orders_2026-10-21.json"), line_sha256="l")]).to_csv(d / "ledger.csv", index=False)
    try:
        C.load_f4(d, pd.Timestamp("2026-10-22")); c1_frozen = False
    except C.Frozen as e:
        c1_frozen = "C1" in str(e)
    pd.DataFrame([dict(asof="2026-10-21", C1=True, orders_sha256=C.sha_f(d / "paper" / "orders_2026-10-21.json"), line_sha256="l")]).to_csv(d / "ledger.csv", index=False)
    c1_true_loads = C.load_f4(d, pd.Timestamp("2026-10-22"))[0] == 0.0
    ok("A2-14", c1_frozen and c1_true_loads, "F4 ledger C1 = False -> 1D frozen; C1 = True loads")
finally:
    shutil.rmtree(d)
# A2-15 verifier: halt -> L8 FAIL without crashing; a good ledger passes L8-L11
d = Path(tempfile.mkdtemp())
try:
    shas = dict(config_sha256=C.sha_f(R_ / "deploy" / "eco_config.json"), protocol_sha256=C.sha_f(R_ / "logs" / "eco" / "ECO_PROTOCOL_PREREGISTERED.md"),
                code_sha256=C.sha_f(R_ / "src" / "eco" / "eco_orchestrator.py"), core_sha256=C.sha_f(R_ / "src" / "eco" / "eco_core.py"),
                exchange_sha256=C.sha_f(R_ / "src" / "eco" / "eco_exchange.py"))
    env = MockEnv2(); env.n1_data = n1_book(); env.f4_data = f4_book()
    st = O.new_state()
    for i in range(3):
        r = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=i)); r.update(ok=True, **shas)
        C.append_ledger(d / "ledger.jsonl", r)
    good = subprocess.run([sys.executable, str(R_ / "src" / "audits" / "verify_eco_live.py"), str(d)], capture_output=True, text=True)
    env.px = {"BTCUSDT": 30_000.0, "ETHUSDT": 1_000.0, "FETUSDT": 2.0}
    for i in (3, 4):
        r = O.cycle(env, st, dict(CFG, coin_cap=1.0, gross_cap=5.0), NOW + pd.Timedelta(hours=i)); r.update(ok=True, **shas)
        C.append_ledger(d / "ledger.jsonl", r)
    bad = subprocess.run([sys.executable, str(R_ / "src" / "audits" / "verify_eco_live.py"), str(d)], capture_output=True, text=True)
    g_ok = all(f"[{t} PASS]" in good.stdout for t in ("L8", "L9", "L10", "L11"))
    b_ok = bad.returncode == 1 and "[L8 FAIL]" in bad.stdout and "Traceback" not in bad.stderr and "[L9 PASS]" in bad.stdout
    ok("A2-15", g_ok and b_ok, f"good ledger: L8-L11 PASS ({g_ok}); halted ledger: L8 FAIL, no crash ({b_ok}) "
       f"{[l for l in (good.stdout + bad.stdout).splitlines() if 'FAIL]' in l][:4]} {bad.stderr[-300:]}")
finally:
    shutil.rmtree(d)


# A2-16 (re-audit) an order still working on the exchange (PENDING) blocks a second order on that symbol
env = MockEnv2(); env.n1_data = n1_book(); env.f4_data = C.Frozen("off"); env.unconfirm_sym = "ETHUSDT"
st = O.new_state()
O.cycle(env, st, CFG, NOW)
env.unconfirm_sym = None
env.recover = lambda j: "PENDING"
n_eth = sum(1 for p, _ in env.orders if p == "ETHUSDT")
rec = O.cycle(env, st, CFG, NOW + pd.Timedelta(hours=1))
ok("A2-16", [j["perp"] for j in st["journal"]] == ["ETHUSDT"] and sum(1 for p, _ in env.orders if p == "ETHUSDT") == n_eth
   and any("still working" in n for n in rec["notes"]), f"ETH order still working: kept in the journal, no second ETH order ({n_eth} sent)")
# A2-17 (re-audit) kill when the ledger holds a position the exchange no longer shows -> ledger flat too
env = MockEnv2(); env.n1_data = n1_book(scale=5.0); env.f4_data = C.Frozen("off")
st = O.new_state()
O.cycle(env, st, cfgw, NOW)
env.pos.pop("ETHUSDT")                                          # gone on the exchange (e.g. liquidated / closed by hand)
env.px.update(BTCUSDT=50_000.0, FETUSDT=0.9)
rec = O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=1))
ok("A2-17", st["halted"] and env.pos == {} and C.held_net(st["held"]) == {} and any("not on the exchange" in n for n in rec["notes"]),
   f"kill: ETH only in the ledger -> closed in the ledger at the mark (noted); ledger and exchange both flat")


# A2-18 alerts: a halted ledger + a failed verifier -> 2 alerts once (deduplicated); no Telegram keys -> file only
import eco_alerts as AL
d = Path(tempfile.mkdtemp())
try:
    env = MockEnv2(); env.n1_data = n1_book(scale=5.0); env.f4_data = C.Frozen("off")
    st = O.new_state()
    for i, pxs in enumerate((None, {"BTCUSDT": 30_000.0, "ETHUSDT": 1_000.0, "FETUSDT": 2.0})):
        if pxs:
            env.px = pxs
        r = O.cycle(env, st, cfgw, NOW + pd.Timedelta(hours=i)); r["ok"] = True
        C.append_ledger(d / "ledger.jsonl", r)
    (d / "cron").mkdir(); (d / "cron" / "ECO_Verify.csv").write_text("start_utc,end_utc,exit_code\n2026-10-22T01:55:01Z,2026-10-22T01:55:02Z,1\n")
    got = []
    o1, _ = AL.run(d, d, d / "cron", NOW + pd.Timedelta(hours=1, minutes=5), send=lambda m: got.append(m) or "test")
    o2, _ = AL.run(d, d, d / "cron", NOW + pd.Timedelta(hours=1, minutes=10), send=lambda m: got.append(m) or "test")
    kinds = sorted(a["kind"] for a in o1)
    ok("A2-18", kinds == ["halted", "job_fail_ECO_Verify"] and o2 == [] and len(got) == 2 and AL.telegram("x").startswith("not configured"),
       f"alerts: first run {kinds}, second run {len(o2)} new (deduplicated); without keys: file only")
finally:
    shutil.rmtree(d)

print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
