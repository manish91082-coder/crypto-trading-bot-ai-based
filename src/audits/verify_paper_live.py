"""Daily check of the forward PAPER-N1 ledger (VM or laptop copy). Usage: python verify_paper_live.py [root=data/paper_n1]
L1 hash chain + line hashes   L2 config SHA constant and == deploy/paper_n1_config.json   L3 code SHA constant (or listed changes)
L4 cycles on the 4h grid, no duplicates; gaps listed   L5 data errors listed (a cycle with > 5 errors = FAIL)   + equity / positions summary"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
root = Path(sys.argv[1]) if len(sys.argv) > 1 else R_ / "data" / "paper_n1"
root = root if root.is_absolute() else R_ / root
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


L = [json.loads(l) for l in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
prev, chain = "GENESIS", True
for r in L:
    body = {k: v for k, v in r.items() if k != "line_sha256"}
    chain &= r["prev_sha256"] == prev and hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == r["line_sha256"]
    prev = r["line_sha256"]
ok("L1", chain, f"{len(L)} cycles, hash chain intact")
cfg = hashlib.sha256((R_ / "deploy" / "paper_n1_config.json").read_bytes()).hexdigest()
ok("L2", {r["config_sha256"] for r in L} == {cfg}, f"config SHA constant = deploy/paper_n1_config.json ({cfg[:12]})")
codes = sorted({r["code_sha256"] for r in L})
ccf = R_ / "logs" / "paper_n1" / "CODE_CHANGES_AFTER_LOCK.md"      # amendment 1: every code SHA must be listed there
cc = ccf.read_text(encoding="utf-8") if ccf.exists() else ""
unl = [c[:12] for c in codes if c[:12] not in cc]
ok("L3", len(codes) == 1 or not unl, f"code SHA(s): {[c[:12] for c in codes]}; not listed in CODE_CHANGES: {unl}")
T = pd.to_datetime([r["T"] for r in L])
gaps = [str(a) for a, b in zip(T[:-1], T[1:]) if b - a != pd.Timedelta(hours=4)]
ok("L4", T.is_unique and all(t.hour % 4 == 0 and t.minute == 0 for t in T), f"cycles on the 4h grid; gaps after: {gaps[:10]}")
errs = [(r["T"], len(r["data_errors"])) for r in L if r["data_errors"]]
ok("L5", all(n <= 5 for _, n in errs), f"cycles with data errors: {errs[:10]}")
last = L[-1]
print(f"[INFO] last cycle {last['T']}: equity {last['equity']:.2f} (start 10000), positions {last['n_pos']}, gross {last['gross']:.3f}, "
      f"days {(T[-1] - T[0]).days}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
