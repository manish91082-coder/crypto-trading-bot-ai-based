"""ECO reset after a halt (amendment 2 §1). Run ONLY by the user.
  python src/eco/eco_reset.py --root data/eco --show
  python src/eco/eco_reset.py --root data/eco --reset --reason "why" --yes          halted -> None, peak -> current eco equity
  python src/eco/eco_reset.py --root data/eco --unfreeze BTCUSDT --reason "why" --yes   clear a fired guard of one symbol
Each change appends a ledger record (mode "reset"). The cycle lock is held while the state is changed."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_core as C
import eco_orchestrator as O

PROJ = C.PROJ


def show(st, exch):
    return dict(halted=st.get("halted"), eco_equity=st.get("eco_equity"), peak=st.get("peak"), guard_fired=st.get("guard_fired", {}),
                frozen_syms=st.get("frozen_syms", []), held_net=C.held_net(st["held"]), exchange_positions=exch,
                open_stops=len(st.get("stops", {})), journal=[j["cid"] for j in st.get("journal", [])])


def apply(st, reset=False, unfreeze=()):
    """the state change itself (tested in test_eco_core A2-4)."""
    done = []
    if reset and st.get("halted"):
        done.append(dict(halted_was=st["halted"], peak_was=st["peak"], peak_now=st["eco_equity"]))
        st["halted"], st["peak"] = None, st["eco_equity"]
    for p in unfreeze:
        if p in st.get("guard_fired", {}):
            done.append(dict(unfrozen=p, guard=st["guard_fired"].pop(p)))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/eco")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--unfreeze", nargs="*", default=[])
    ap.add_argument("--reason", default="")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--mode", choices=["plan", "demo"], default="plan")
    a = ap.parse_args()
    root = PROJ / a.root
    cfg = O.load_cfg()
    with O.Lock(root / "eco.lock"):
        st = json.loads((root / "state.json").read_text())
        env = O.LiveEnv(a.mode, cfg, root)
        print(json.dumps(show(st, env.positions()), indent=1, default=str))
        if a.show or not (a.reset or a.unfreeze):
            return
        assert a.yes and a.reason.strip(), "a reset needs --reason \"...\" and --yes (the user's decision)"
        done = apply(st, a.reset, a.unfreeze)
        if not done:
            print("nothing to change"); return
        rec = dict(T=str(O.pd.Timestamp.now("UTC").tz_localize(None).floor("s")), mode="reset", ok=True, reset=done, reason=a.reason,
                   eco_equity=st["eco_equity"], peak=st["peak"], halted=st["halted"], orders=[],
                   code_sha256=C.sha_f(Path(O.__file__)), core_sha256=C.sha_f(Path(C.__file__)), exchange_sha256=C.sha_f(Path(O.X.__file__)),
                   config_sha256=C.sha_f(O.CFG_F), protocol_sha256=C.sha_f(O.PROTO))
        C.append_ledger(root / "ledger.jsonl", rec)
        C.write_json_atomic(root / "state.json", st)
        print("reset written:", done)


if __name__ == "__main__":
    main()
