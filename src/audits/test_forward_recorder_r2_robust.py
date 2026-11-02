"""Robustness tests T5-T9 for the R2 forward recorder (code change 3). Real public Binance data, 2 test symbols.
T5 downtime 3 days: run 1 pretends to run 3 days ago, run 2 runs now -> S paging over > 41 h, verifier all PASS
T6 crash BEFORE the ledger line (copy): last ledger line removed -> next run quarantines the orphan, restores the state of
   the last chained run, refetches; verifier all PASS, no duplicates
T7 crash AFTER the ledger line, before state.json replace (copy): stale state.json -> restored from state_after.json
T8 unit: a series older than the 29-day window gets a LOST note (network stubbed; logic only)
T9 guard: --test-server-offset-ms without --test-symbols is refused
Usage: python test_forward_recorder_r2_robust.py <scratch_dir>"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
REC = PROJ / "src" / "execution" / "forward_recorder_r2.py"
VER = PROJ / "src" / "audits" / "verify_forward_recorder_r2.py"
SYM = "BTCUSDT,ETHUSDT"
scratch = Path(sys.argv[1])
out = []


def run(args):
    p = subprocess.run([sys.executable] + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout + p.stderr).strip()


def check(t, c, m):
    out.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def ledger(root):
    L = (root / "ledger.csv").read_text().splitlines()
    return [dict(zip(L[0].split(","), l.split(","))) for l in L[1:]]


A = scratch / "rootA"
if A.exists():
    shutil.rmtree(A)
rc1, t1 = run([REC, "--root", A, "--test-symbols", SYM, "--test-server-offset-ms", -3 * 86_400_000, "--test-s-back-days", 5]); print(t1)
rc2, t2 = run([REC, "--root", A, "--test-symbols", SYM]); print(t2)
rv, tv = run([VER, A, "--replay", "30"]); print(tv)
L = ledger(A)
man2 = json.loads((A / "raw" / L[1]["run_id"] / "manifest.json").read_text())
pages = max(int(f["file"].rsplit("_p", 1)[1].split(".")[0]) for f in man2["files"] if f["file"].startswith("S_")) + 1
st1 = json.loads((A / "raw" / L[0]["run_id"] / "state_after.json").read_text())
s_keys1 = [k for k in st1 if k.split("|")[0] in ("oi_hist", "top_acct_ratio", "top_pos_ratio", "global_ratio", "taker_ratio", "basis")]
print(f"   run 1: http errors {L[0]['n_http_errors']}, S series with data {len(s_keys1)} of 12")
check("T5", rc1 == 0 and rc2 == 0 and rv == 0 and pages >= 2 and int(L[1]["n_rows_kept"]) > 5000
      and L[0]["n_http_errors"] == "0" and len(s_keys1) == 12,
      f"3-day downtime resumed: run 2 kept {L[1]['n_rows_kept']} rows, S pages per series up to {pages}; verifier exit {rv}")

B = scratch / "rootB"
if B.exists():
    shutil.rmtree(B)
shutil.copytree(A, B)
lines = (B / "ledger.csv").read_text().splitlines()
(B / "ledger.csv").write_text("\n".join(lines[:-1]) + "\n")           # crash before the run-2 ledger line was written
orphan = L[1]["run_id"]
rc3, t3 = run([REC, "--root", B, "--test-symbols", SYM]); print(t3)
rv, tv = run([VER, B, "--replay", "20"]); print(tv)
LB = ledger(B)
check("T6", rc3 == 0 and rv == 0 and (B / "raw_orphans" / orphan).exists() and "quarantined" in LB[-1]["notes"]
      and "restored" in LB[-1]["notes"],
      f"crash before ledger: orphan {orphan} quarantined, state restored from the last chained run, refetched; verifier exit {rv}")

C = scratch / "rootC"
if C.exists():
    shutil.rmtree(C)
shutil.copytree(A, C)
shutil.copy(C / "raw" / L[0]["run_id"] / "state_after.json", C / "state.json")   # crash before state.json replace
rc4, t4 = run([REC, "--root", C, "--test-symbols", SYM]); print(t4)
rv, tv = run([VER, C, "--replay", "20"]); print(tv)
LC = ledger(C)
check("T7", rc4 == 0 and rv == 0 and "restored" in LC[-1]["notes"],
      f"crash after ledger / stale state.json: restored from state_after.json, no duplicates; verifier exit {rv}")

spec = importlib.util.spec_from_file_location("fr", REC)
fr = importlib.util.module_from_spec(spec); spec.loader.exec_module(fr)
fr.SYMBOLS, fr.K_SERIES, fr.S_SERIES, fr.S_SLEEP = ["BTCUSDT"], [], [("oi_hist", "/futures/data/openInterestHist")], 0


class FakeRec:
    def __init__(self):
        self.files, self.errors, self.n_req, self.gaps = [], [], 0, []

    def get(self, base, path, params):
        return b"[]"

    def save(self, *a, **k):
        pass


srv = 1_800_000_000_000
notes = []
for name in ("_funding_loop_skip",):
    pass
st = {"oi_hist|BTCUSDT|5m": srv - 31 * 86_400_000}
orig_get = fr.Rec
fr_rec = FakeRec()
fr.SYMBOLS = ["BTCUSDT"]
try:
    fr.record(Path(scratch), "unit", srv, st, fr_rec, notes)
except Exception as e:
    notes.append(f"EXC {e}")
check("T8", any(n.startswith("LOST oi_hist|BTCUSDT|5m") for n in notes),
      f"series last stamp 31 days old -> LOST note: {[n for n in notes if n.startswith('LOST')][:1]}")

rc, t = run([REC, "--root", scratch / "rootG", "--test-server-offset-ms", -1000])
check("T9", rc != 0 and "allowed only together" in t and not (scratch / "rootG" / "ledger.csv").exists(),
      "offset without --test-symbols is refused before anything is written")
print(f"TOTAL {len(out)} tests, FAIL {out.count(False)}")
sys.exit(1 if False in out else 0)
