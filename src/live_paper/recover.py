"""LPT-1 recovery after a power loss (2026-11-02). Run this BEFORE restarting the loops: a hard shutdown can leave state.json as NUL bytes and a
NUL tail on the append-only logs (Windows, no fsync). It repairs only what is provably safe:
  logs     trailing NUL bytes are cut, after a backup, and only if every remaining line parses and the hash chain holds; anything else aborts
  state    state.json is rebuilt from fills.jsonl + daily.jsonl, and only if no position is open (a lost open position must be looked at by hand)
The corrupt originals are kept next to the logs as *.corrupt_NUL_<date>. lpt.py stays untouched (locked by the LPT-1 protocol).
Usage: python src/live_paper/recover.py [--check]   (--check repairs nothing)"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402

LOGS = ["decisions.jsonl", "fills.jsonl", "daily.jsonl", "contexts.jsonl", "signals.jsonl", "snapshots.jsonl", "forward_r2.jsonl", "pred1/predictions.jsonl"]


def chain_ok(lines):
    prev = "GENESIS"
    for ln in lines:
        if json.loads(ln)["prev"] != prev:
            return False
        prev = hashlib.sha256(ln).hexdigest()
    return True


def repair_log(path, stamp, check):
    b = path.read_bytes() if path.exists() else b""
    s = b.rstrip(b"\0")
    if b"\0" in s or not chain_ok(s.splitlines()):
        sys.exit(f"ABORT {path.name}: damage is not a pure NUL tail, look at it by hand")
    if len(s) == len(b):
        return None
    msg = f"{path.name}: {len(b) - len(s)} trailing NUL bytes, {len(s.splitlines())} lines intact"
    if not check:
        shutil.copy2(path, path.with_name(f"{path.name}.corrupt_NUL_{stamp}"))
        path.write_bytes(s)
    return msg


def state_ok():
    try:
        s = json.loads(lpt.STATE.read_text())
        return isinstance(s, dict) and "cash" in s
    except (ValueError, OSError):
        return False


def rebuild_state(stamp, check):
    if state_ok():
        return None
    read = lambda f: [json.loads(x) for x in (lpt.LOG / f).read_text().splitlines()]  # noqa: E731
    fills, days, snap = read("fills.jsonl"), read("daily.jsonl"), read("snapshots.jsonl")
    op = {f["id"] for f in fills if f["kind"] == "OPEN"}
    cl = [f for f in fills if f["kind"] == "CLOSE"]
    if op != {f["id"] for f in cl}:
        sys.exit("ABORT state.json: a position was open at the shutdown, rebuild it by hand")
    cash = fills[-1]["cash"] if fills else lpt.START_EQUITY
    day = max(snap_day for snap_day in [json.loads(x)["utc"][:10] for x in (lpt.LOG / "decisions.jsonl").read_text().splitlines()])
    s = dict(cash=cash, positions={}, next_id=len(op) + 1, day=day, day_start_equity=days[-1]["end"] if days else lpt.START_EQUITY, halted_day=None,
             realized=sum(f["pnl_net"] for f in cl), fees=sum(f["fee"] for f in fills), created=snap[0]["utc"])
    if not check:
        if lpt.STATE.exists():
            shutil.copy2(lpt.STATE, lpt.STATE.with_name(f"state.json.corrupt_NUL_{stamp}"))
        lpt.save_state(s)
    return f"state.json rebuilt: cash {cash:.4f}, 0 positions, next_id {s['next_id']}, day {day}"


def main():
    check = "--check" in sys.argv
    stamp = lpt.iso()[:10]
    done = [m for m in (repair_log(lpt.LOG / f, stamp, check) for f in LOGS) if m]
    m = rebuild_state(stamp, check)
    if m:
        done.append(m)
    for x in done or ["nothing to repair"]:
        print(("WOULD FIX " if check and done else "FIXED " if done else "") + x)
    if done and not check:
        lpt.append_chain(lpt.LOG / "decisions.jsonl", dict(utc=lpt.iso(), kind="RECOVERY", reason="Power loss repair by recover.py: " + "; ".join(done),
                                                           plan="Restart watcher, PRED-1 and FWD-R2; context review before any trade."))


if __name__ == "__main__":
    main()
