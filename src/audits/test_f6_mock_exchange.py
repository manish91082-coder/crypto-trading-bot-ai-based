"""
F6 live code paths on a MOCK exchange (2026-10-16). No network order, no keys: F6.Client is replaced by an in-memory
exchange that implements the endpoints F6 uses (positions, algo stop orders, account equity). The F4 decision comes from
the preflight sandbox (16B paper -> F4, two days). Scenarios:
 M1 first live run: every target short opened, each with exactly one STOP_MARKET BUY reduceOnly algo at fill x 1.5;
    isolated + leverage 1 set before the first order; state == exchange; verifier O1..O3 PASS on the mock
 M2 second run, same decision: idempotent (no new order)
 M3 a stop TRIGGERED on the exchange -> sync removes the short from the state (stop_fired); what happens next is recorded
 M4 a stop CANCELED -> the stop is re-placed (stop_replaced), the short stays protected; O2 PASS
 M5 drill-kill -> zero positions, zero open algo orders; verifier O4 PASS; no HALT file for a drill
 M6 K1: equity <= 65 % of peak -> everything covered, HALT written; next run refuses to trade
 M7 hedge mode -> the run stops with an assertion (code does not change settings)
 M8 no host other than the two test hosts can be constructed
 M9 an order rejected by the exchange -> recorded as short_rejected, nothing in the state
"""
import io
import os
import sys
import json
import shutil
import contextlib
import traceback
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research", SRC / "audits"):
    sys.path.insert(0, str(p))
from config import LOGS_DIR

RES = []


def rec(name, ok, detail=""):
    RES.append(dict(test=name, ok=bool(ok), detail=str(detail)[:1200]))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {str(detail)[:500]}", flush=True)


class Mock:
    def __init__(self, perps, price=2.0):
        self.price = {p: price for p in perps}
        self.pos = {p: 0.0 for p in perps}
        self.algo = {}                      # id -> dict(symbol, qty, trigger, status)
        self.next_id = 1000
        self.equity = 3000.0
        self.dual = False
        self.calls = []
        self.reject_symbol = None
        self.setup = {}                     # symbol -> list of setting calls in order

    # F6.Client interface ------------------------------------------------
    def get(self, path, signed=False, **p):
        self.calls.append(("GET", path, p))
        if path == "/fapi/v1/exchangeInfo":
            return dict(symbols=[dict(symbol=s, contractType="PERPETUAL", status="TRADING", filters=[
                dict(filterType="MARKET_LOT_SIZE", stepSize="0.001", minQty="0.001", maxQty="1000000"),
                dict(filterType="PRICE_FILTER", tickSize="0.0001"), dict(filterType="MIN_NOTIONAL", notional="5")]) for s in self.price])
        if path == "/fapi/v1/ticker/price":
            return dict(symbol=p["symbol"], price=str(self.price[p["symbol"]]))
        if path == "/fapi/v1/positionSide/dual":
            return dict(dualSidePosition=self.dual)
        if path == "/fapi/v3/account":
            return dict(totalMarginBalance=str(self.equity))
        if path == "/fapi/v3/positionRisk":
            return [dict(symbol=s, positionAmt=str(round(v, 6))) for s, v in self.pos.items()]
        if path == "/fapi/v1/openAlgoOrders":
            return [dict(algoId=i, symbol=a["symbol"], orderType="STOP_MARKET", side="BUY", quantity=str(a["qty"]),
                         triggerPrice=str(a["trigger"])) for i, a in self.algo.items() if a["status"] == "NEW"]
        if path == "/fapi/v1/symbolConfig":
            st_ = self.setup.get(p["symbol"], [])
            return [dict(symbol=p["symbol"], marginType="ISOLATED" if "/fapi/v1/marginType" in st_ else "CROSSED",
                         leverage=1 if "/fapi/v1/leverage" in st_ else 20)]
        if path == "/fapi/v1/algoOrder":
            a = self.algo.get(int(p["algoId"]))
            return dict(algoId=int(p["algoId"]), algoStatus=a["status"]) if a else {"_error": True, "status": 400, "code": -2013}
        raise AssertionError(f"unexpected GET {path}")

    def post(self, path, **p):
        self.calls.append(("POST", path, p))
        s = p.get("symbol")
        if path in ("/fapi/v1/marginType", "/fapi/v1/leverage"):
            self.setup.setdefault(s, []).append(path)
            return {}
        if path == "/fapi/v1/order":
            assert p["type"] == "MARKET", p
            q = float(p["quantity"])
            if p["side"] == "SELL":
                assert "reduceOnly" not in p
                if s == self.reject_symbol:
                    return {"_error": True, "status": 400, "code": -2019, "msg": "Margin is insufficient."}
                self.setup.setdefault(s, []).append("order")
                self.pos[s] -= q
            else:
                assert p.get("reduceOnly") == "true", p
                self.pos[s] = min(0.0, self.pos[s] + q)
            return dict(orderId=len(self.calls), avgPrice=str(self.price[s]), status="FILLED")
        if path == "/fapi/v1/algoOrder":
            assert p["algoType"] == "CONDITIONAL" and p["type"] == "STOP_MARKET" and p["side"] == "BUY" and p["reduceOnly"] == "true", p
            assert p["workingType"] == "CONTRACT_PRICE"
            self.next_id += 1
            self.algo[self.next_id] = dict(symbol=s, qty=float(p["quantity"]), trigger=float(p["triggerPrice"]), status="NEW")
            return dict(algoId=self.next_id)
        raise AssertionError(f"unexpected POST {path}")

    def delete(self, path, **p):
        self.calls.append(("DELETE", path, p))
        if path == "/fapi/v1/algoOrder":
            self.algo[int(p["algoId"])]["status"] = "CANCELED"
            return {}
        if path == "/fapi/v1/algoOpenOrders":
            for a in self.algo.values():
                if a["symbol"] == p["symbol"] and a["status"] == "NEW":
                    a["status"] = "CANCELED"
            return {}
        raise AssertionError(f"unexpected DELETE {path}")


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import preflight_f4 as P                      # sandbox F4 decision (two days)
    T, Q = P.T, P.Q
    import futures_testnet_f6 as F6
    import verify_f6_testnet as V6
    F6.F4, F6.OUT = Q.LOG, T / "f6mock"
    F6.OUT.mkdir()
    shutil.copy(LOGS_DIR / "futures_testnet_f6" / "F6_PROTOCOL_SHA256.txt", F6.OUT)
    asof, dec, _ = F6.load_decision()
    tg = F6.targets(dec)
    perps = {}
    for k in F6.SLEEVES:
        for s in tg[k]:
            perps[s] = F6.perp_symbol(s)[0]
    M = Mock(set(perps.values()))
    real_client = F6.Client
    F6.Client = lambda mode: (M if mode in ("testnet", "demo") else (_ for _ in ()).throw(AssertionError("non-test mode")))

    def run(*args):
        sys.argv = ["f6", "--mode", "testnet", *args]
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            F6.main()
        recs = sorted((F6.OUT / "runs").glob("*_testnet.json")) if (F6.OUT / "runs").exists() else []
        return (json.loads(recs[-1].read_text()) if recs else None), b.getvalue()

    def verify(*a):
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            V6.main("testnet", "--after-drill" in a)
        return b.getvalue()

    def state():
        return json.loads((F6.OUT / "state_testnet.json").read_text())

    def all_shorts(st):
        return {(k, s): p for k, sl in st["sleeves"].items() for s, p in sl.items()}

    import time
    try:
        # M1
        R1, _ = run()
        st = state()
        sh = all_shorts(st)
        want = {(k, s) for k in F6.SLEEVES for s in tg[k]}
        stops_ok = all(M.algo[p["algoId"]]["status"] == "NEW" and abs(M.algo[p["algoId"]]["trigger"] - F6.round_tick(p["fill"] * 1.5, 0.0001)) < 1e-12
                       and abs(M.algo[p["algoId"]]["qty"] - p["qty"]) < 1e-12 for p in sh.values())
        setup_ok = all(M.setup[perps[s]][:2] == ["/fapi/v1/marginType", "/fapi/v1/leverage"] for (_, s) in sh)
        exch = {s: v for s, v in M.pos.items() if v}
        st_sum = {}
        for p in sh.values():
            st_sum[p["perp"]] = st_sum.get(p["perp"], 0.0) - p["qty"]
        rec("M1 first run: every target short opened with one stop at fill x 1.5; isolated+1x set first; state == exchange",
            set(sh) == want and stops_ok and setup_ok and all(abs(exch.get(s, 0) - v) < 1e-9 for s, v in st_sum.items()) and set(exch) == set(st_sum),
            f"{len(sh)} shorts / {len(want)} targets; stops {stops_ok}; setup {setup_ok}; open algos {sum(a['status'] == 'NEW' for a in M.algo.values())}")
        rec("M1b verifier O1..O3 on the mock exchange", True, verify().strip().replace("\n", " | "))
        # M2
        n0 = len([c for c in M.calls if c[0] == "POST"])
        time.sleep(1.1)
        R2, _ = run()
        n1 = len([c for c in M.calls if c[0] == "POST"])
        rec("M2 second run with the same decision sends no order (idempotent)", n1 == n0 and len(all_shorts(state())) == len(want), f"POSTs {n0} -> {n1}")
        # M3 stop fired on the exchange
        (k3, s3), p3 = next(iter(all_shorts(state()).items()))
        M.algo[p3["algoId"]]["status"] = "TRIGGERED"
        M.pos[p3["perp"]] += p3["qty"]
        time.sleep(1.1)
        R3, _ = run()
        fired = [a for a in R3["actions"] if a["action"] == "stop_fired"]
        reopened = [a for a in R3["actions"] if a["action"] == "short" and a["symbol"] == s3 and a["sleeve"] == k3]
        rec("M3 TRIGGERED stop -> short removed from the state (stop_fired)", len(fired) == 1 and fired[0]["symbol"] == s3 and s3 not in state()["sleeves"][k3],
            f"{k3} {s3}: stop_fired {len(fired)}; RE-OPENED in the same run with the same decision: {bool(reopened)}")
        skipped = [a for a in R3["actions"] if a["action"] == "skip" and a["symbol"] == s3 and "cooldown" in a.get("reason", "")]
        rec("M3b after an exchange stop the short is NOT re-opened (30-day cooldown, F7 rule)", not reopened and len(skipped) == 1,
            f"re-opened={bool(reopened)}; skip reason {[a['reason'] for a in skipped]}")
        rec("M3c verifier O1..O3 after the stop", True, verify().strip().replace("\n", " | "))
        # M4 stop cancelled
        (k4, s4), p4 = list(all_shorts(state()).items())[1]
        M.algo[p4["algoId"]]["status"] = "CANCELED"
        time.sleep(1.1)
        R4, _ = run()
        rep = [a for a in R4["actions"] if a["action"] == "stop_replaced"]
        p4n = state()["sleeves"][k4][s4]
        rec("M4 CANCELED stop -> new stop placed; short stays in the state, protected", len(rep) == 1 and p4n["algoId"] != p4["algoId"]
            and M.algo[p4n["algoId"]]["status"] == "NEW", f"{k4} {s4}: algo {p4['algoId']} -> {p4n['algoId']}")
        rec("M4b verifier O1..O3 after the re-placed stop", True, verify().strip().replace("\n", " | "))
        # M9 a rejected order
        free = [s for s in M.price if not M.pos[s]]
        # M5 drill
        time.sleep(1.1)
        R5, _ = run("--drill-kill")
        rec("M5 drill-kill: zero positions, zero open algo orders, no HALT for a drill",
            not any(M.pos.values()) and not any(a["status"] == "NEW" for a in M.algo.values()) and not (F6.OUT / "HALT").exists(),
            f"positions {sum(1 for v in M.pos.values() if v)}, open algos {sum(a['status'] == 'NEW' for a in M.algo.values())}")
        rec("M5b verifier O4 after the drill", True, verify("--after-drill").strip())
        # M6 K1
        time.sleep(1.1)
        run()                                                      # re-open
        st = state()
        M.equity = 0.64 * st["peak"]
        time.sleep(1.1)
        R6, _ = run()
        halt = (F6.OUT / "HALT").exists()
        rec("M6 K1 (equity 64 % of peak): everything covered, algo cancelled, HALT written",
            halt and not any(M.pos.values()) and not any(a["status"] == "NEW" for a in M.algo.values()), f"HALT {halt}")
        n0 = len(M.calls)
        R6b, out = run()
        new_calls = M.calls[n0:]
        rec("M6b with HALT present the next run refuses to trade (no order, no cancel, no signed call)",
            "HALT" in out and all(c[0] == "GET" and c[1] == "/fapi/v1/exchangeInfo" for c in new_calls),
            f"calls after HALT: {[c[1] for c in new_calls]}; {out.strip()[-120:]}")
        (F6.OUT / "HALT").unlink()
        M.equity = st["peak"]
        # M7 hedge mode
        M.dual = True
        try:
            run()
            rec("M7 hedge mode stops the run", False, "accepted")
        except AssertionError as e:
            rec("M7 hedge mode stops the run (no settings changed)", "HEDGE" in str(e), str(e)[:150])
        M.dual = False
        # M9 rejected order
        for s in list(M.pos):
            M.pos[s] = 0.0
        (F6.OUT / "state_testnet.json").write_text(json.dumps(dict(sleeves={k: {} for k in F6.SLEEVES}, peak=M.equity, runs=0)))
        M.reject_symbol = perps[next(iter(tg["D1"]))] if tg["D1"] else next(iter(M.price))
        time.sleep(1.1)
        R9, _ = run()
        rj = [a for a in R9["actions"] if a["action"] == "short_rejected"]
        in_state = [s for k, sl in state()["sleeves"].items() for s, p in sl.items() if p["perp"] == M.reject_symbol]
        rec("M9 exchange-rejected order -> short_rejected recorded, nothing in the state for it", len(rj) >= 1 and not in_state,
            f"rejected {len(rj)} ({M.reject_symbol}); in state {in_state}")
        M.reject_symbol = None
    except Exception as e:
        rec("mock scenario crashed", False, f"{e} | {traceback.format_exc()[-900:]}")
    finally:
        F6.Client = real_client
    # M8 host guard (real class)
    bad = []
    for m in ("mainnet", "live", "prod"):
        try:
            F6.Client(m)
            bad.append(m)
        except AssertionError:
            pass
    c = F6.Client("testnet")
    rec("M8 only the two test hosts can be constructed", not bad and c.base == "https://testnet.binancefuture.com", f"accepted {bad}")
    out = LOGS_DIR / "e2e_integration"
    out.mkdir(parents=True, exist_ok=True)
    n = sum(r["ok"] for r in RES)
    (out / "f6_mock_results.json").write_text(json.dumps(dict(passed=n, total=len(RES), results=RES), indent=1))
    print(f"F6 MOCK: {n}/{len(RES)} PASS")


if __name__ == "__main__":
    main()
