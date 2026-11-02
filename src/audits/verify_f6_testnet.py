"""
Independent verifier for the F6 operations test (logs/futures_testnet_f6). Needs the same env keys as the run (user-set).
O1 every action in the last run record is acknowledged (no "_error" response) or an explicit skip with a reason.
O2 every open sleeve short in the state has exactly one OPEN STOP_MARKET algo order (re-read from the API) with
   quantity = sleeve quantity and trigger = fill x 1.50 (tick-rounded); every open algo order belongs to a state short.
O3 exchange position amount per symbol = -(sum of sleeve quantities in the state), within one step size.
O4 (after a --drill-kill record) zero non-zero positions and zero open algo orders.
O5 every held symbol: marginType ISOLATED and leverage 1 (GET /fapi/v1/symbolConfig), protocol rule 4.
Usage: python verify_f6_testnet.py testnet|demo [--after-drill]
"""
import sys
import json
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "execution"):
    sys.path.insert(0, str(p))
import futures_testnet_f6 as Q


def main(env, after_drill):
    c = Q.Client(env)
    flt = Q.filters(c)
    runs = sorted((Q.OUT / "runs").glob(f"*_{env}.json"))
    assert runs, "no run record"
    rec = json.loads(runs[-1].read_text())
    for a in rec["actions"]:
        if a["action"] == "skip":
            assert a.get("reason"), a
        else:
            for key in ("resp", "stop_resp"):
                if key in a and a[key] is not None:
                    assert not a[key].get("_error"), (a["action"], a.get("symbol"), a[key])
    print(f"[O1 PASS] {runs[-1].name}: {len(rec['actions'])} actions acknowledged or skipped with a reason")
    algo = c.get("/fapi/v1/openAlgoOrders", signed=True)
    pos = {p["symbol"]: float(p["positionAmt"]) for p in c.get("/fapi/v3/positionRisk", signed=True)}
    if after_drill:
        assert rec["drill_kill"], "last record is not a drill"
        assert not algo and all(v == 0 for v in pos.values()), (algo, {k: v for k, v in pos.items() if v})
        print("[O4 PASS] after the kill drill: no positions, no open algo orders")
        return
    st = json.loads((Q.OUT / f"state_{env}.json").read_text())
    by_id = {int(o["algoId"]): o for o in algo}
    used, want = set(), {}
    for k, sl in st["sleeves"].items():
        for s, p in sl.items():
            o = by_id.get(int(p["algoId"])) if p.get("algoId") else None
            assert o is not None, (k, s, "no open stop")
            fl = flt[p["perp"]]
            assert o["orderType"] == "STOP_MARKET" and o["side"] == "BUY", o
            assert abs(float(o["quantity"]) - p["qty"]) < fl["step"] / 2, (s, o["quantity"], p["qty"])
            assert abs(float(o["triggerPrice"]) - Q.round_tick(p["fill"] * Q.STOP_X, fl["tick"])) < fl["tick"] / 2, (s, o["triggerPrice"], p["fill"])
            used.add(int(p["algoId"]))
            want[p["perp"]] = want.get(p["perp"], 0.0) - p["qty"]
    assert set(by_id) == used, ("open algo orders without a state short", set(by_id) - used)
    print(f"[O2 PASS] {len(used)} open shorts, each with exactly one correct STOP_MARKET algo order")
    for s, v in want.items():
        assert abs(pos.get(s, 0.0) - v) < flt[s]["step"], (s, pos.get(s), v)
    extra = {s: v for s, v in pos.items() if v != 0 and s not in want}
    assert not extra, ("exchange positions not in the state", extra)
    for s in want:                                   # O5 (2026-10-16): protocol rule 4 re-read from the exchange
        cfg = c.get("/fapi/v1/symbolConfig", signed=True, symbol=s)
        cfg = cfg[0] if isinstance(cfg, list) and cfg else cfg
        assert cfg.get("marginType") == "ISOLATED" and int(cfg.get("leverage")) == 1, (s, cfg)
    print(f"[O5 PASS] every held symbol is ISOLATED margin at leverage 1 ({len(want)} symbols, re-read via /fapi/v1/symbolConfig)")
    print(f"[O3 PASS] exchange positions equal the state for {len(want)} symbols; no extra positions")


if __name__ == "__main__":
    main(sys.argv[1], "--after-drill" in sys.argv)
