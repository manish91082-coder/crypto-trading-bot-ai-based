"""
F6 technical ops drill on the Binance DEMO futures exchange (2026-10-16). NOT the protocol's official O1-O4 record:
the decision comes from the F4 preflight SANDBOX (technical test data of 2026-10-14), because the real F4 log has no
short decision yet (2026-10-15 = PAPER_START). Everything is written to logs/futures_testnet_f6/ops_drill_2026-10-16/.
Steps: demo run (opens the sandbox target shorts with stops) -> verifier O1..O3 -> second run (must send nothing)
-> drill-kill -> verifier O4 (zero positions, zero open algo orders). Keys: the user's environment variables only.
"""
import io
import sys
import shutil
import contextlib
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research", SRC / "audits"):
    sys.path.insert(0, str(p))
from config import LOGS_DIR

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    import preflight_f4 as P
import futures_testnet_f6 as F6
import verify_f6_testnet as V6

F6.F4 = P.Q.LOG
F6.OUT = LOGS_DIR / "futures_testnet_f6" / "ops_drill_2026-10-16"
F6.OUT.mkdir(parents=True, exist_ok=True)
shutil.copy(LOGS_DIR / "futures_testnet_f6" / "F6_PROTOCOL_SHA256.txt", F6.OUT)
print("sandbox decision:", P.T)


def run(*a):
    sys.argv = ["f6", "--mode", "demo", *a]
    F6.main()


import time
run()
V6.main("demo", False)
time.sleep(2)
run()                                            # same decision again: must send no new order
V6.main("demo", False)
time.sleep(2)
run("--drill-kill")
time.sleep(3)
V6.main("demo", True)
print("OPS DRILL DONE")
