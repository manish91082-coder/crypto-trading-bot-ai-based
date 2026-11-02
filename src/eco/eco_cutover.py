"""ECO demo cut-over (amendment 1 §4.2): adopt F6's demo shorts into the ECO demo state.
  python src/eco/eco_cutover.py --check            read-only: F6 state vs demo account, open algo orders, gate status
  python src/eco/eco_cutover.py --execute          (after the gate + the user's go; F6 cron lines must already be removed)
Demo host only. Writes data/eco_demo/state.json; renames the F6 state to state_demo_retired_<date>.json; deletes nothing."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_core as C
import eco_exchange as X
import eco_orchestrator as O

PROJ = C.PROJ
F6S = PROJ / "logs" / "futures_testnet_f6" / "state_demo.json"


def adopt_state(f6, mark, wallet, capital):
    """F6 state -> a fresh ECO state holding F6's shorts as 1D components; cash = qty x mark (equity starts now)."""
    st = O.new_state()
    for k, d in f6["sleeves"].items():
        for s, p in d.items():
            key = f"1D|{k}|S|{s}"
            q = -float(p["qty"])
            st["held"][key] = dict(qty={p["perp"]: q}, cash=-q * mark[p["perp"]], fees=0.0, funding=0.0, entry_px={p["perp"]: float(p["fill"])})
    st["adopted_from_f6"] = dict(time=str(pd.Timestamp.now("UTC")), wallet=wallet, n=len(st["held"]))
    return st


def check(demo):
    f6 = json.loads(F6S.read_text())
    want = {}
    for d in f6["sleeves"].values():
        for p in d.values():
            want[p["perp"]] = want.get(p["perp"], 0.0) - float(p["qty"])
    pos = demo.positions()
    opn = demo.signed("GET", "/fapi/v1/openAlgoOrders")
    algo_syms = sorted({o["symbol"] for o in opn}) if isinstance(opn, list) else opn
    same = {p: (want.get(p), pos.get(p)) for p in set(want) | set(pos) if abs(want.get(p, 0.0) - pos.get(p, 0.0)) > 1e-9}
    cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    f6_cron = [l for l in cron.splitlines() if "futures_testnet_f6.py" in l and not l.lstrip().startswith("#")]
    L = [json.loads(l) for l in (PROJ / "data" / "eco" / "ledger.jsonl").read_text().splitlines() if l.strip()] if (PROJ / "data" / "eco" / "ledger.jsonl").exists() else []
    n_ok = sum(1 for r in L if r.get("ok"))
    vf = PROJ / "logs" / "cron_status" / "ECO_Verify.csv"            # amendment 2 §7: the last 3 verifier runs, 3 days, all exit 0
    v = pd.read_csv(vf).tail(3) if vf.exists() else pd.DataFrame(columns=["start_utc", "exit_code"])
    verify_ok = len(v) == 3 and (v.exit_code == 0).all() and pd.to_datetime(v.start_utc).dt.date.nunique() == 3
    risk = demo.signed("GET", "/fapi/v3/positionRisk")
    margin = {p["symbol"]: p.get("marginType", "?") for p in risk if float(p["positionAmt"]) != 0} if isinstance(risk, list) else risk
    rep = dict(f6_positions=want, account_positions=pos, mismatch=same, open_algo_symbols=algo_syms, f6_cron_lines=len(f6_cron),
               plan_cycles_ok=n_ok, one_way=demo.one_way(), wallet=demo.wallet_equity(), verify_last3=v.to_dict("records"),
               margin_type=margin, margin_note="isolated symbols keep ISOLATED until their position is closed (code does not change them)")
    rep["gate"] = dict(positions_match=not same, plan_cycles_ge_72=n_ok >= 72, f6_cron_removed=not f6_cron, one_way=rep["one_way"],
                       verify_3_days_ok=bool(verify_ok))
    return rep, f6


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    demo = X.Demo()
    rep, f6 = check(demo)
    print(json.dumps(rep, indent=1, default=str))
    if a.check:
        return
    assert all(rep["gate"].values()), f"cut-over gate not met: {rep['gate']}"
    root = PROJ / "data" / "eco_demo"
    assert not (root / "state.json").exists(), "ECO demo state exists already"
    for s in sorted({p["perp"] for d in f6["sleeves"].values() for p in d.values()}):
        r = demo.signed("DELETE", "/fapi/v1/algoOpenOrders", symbol=s)
        print("cancel F6 algo orders", s, r)
    left = demo.signed("GET", "/fapi/v1/openAlgoOrders")
    assert isinstance(left, list) and not left, f"algo orders still open: {left}"
    mark = demo.prices([p["perp"] for d in f6["sleeves"].values() for p in d.values()])
    st = adopt_state(f6, mark, rep["wallet"], 10_000.0)
    root.mkdir(parents=True, exist_ok=True)
    C.write_json_atomic(root / "state.json", st, keep_prev=False)
    ret = F6S.with_name(f"state_demo_retired_{pd.Timestamp.now('UTC').date()}.json")
    F6S.rename(ret)
    print("adopted", st["adopted_from_f6"], "F6 state ->", ret.name)


if __name__ == "__main__":
    main()
