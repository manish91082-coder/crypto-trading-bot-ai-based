"""Read-only check of the F6 futures account (demo / testnet): host, position mode, balance, non-zero positions, open
algo orders. GET requests only; keys are read from the user's environment variables by F6.Client and never printed.
Usage: python f6_demo_account_check.py demo|testnet"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))
import futures_testnet_f6 as F

env = sys.argv[1] if len(sys.argv) > 1 else "demo"
c = F.Client(env)
print("host", c.base)
d = c.get("/fapi/v1/positionSide/dual", signed=True)
print("hedge mode (dualSidePosition):", d.get("dualSidePosition"), d if d.get("_error") else "")
a = c.get("/fapi/v3/account", signed=True)
if isinstance(a, dict) and a.get("_error"):
    print("account error:", a.get("status"), a.get("code"), a.get("msg"))
else:
    print("totalMarginBalance", a["totalMarginBalance"], "| availableBalance", a["availableBalance"])
p = c.get("/fapi/v3/positionRisk", signed=True)
print("non-zero positions:", [(x["symbol"], x["positionAmt"]) for x in p if float(x["positionAmt"]) != 0] if isinstance(p, list) else p)
o = c.get("/fapi/v1/openAlgoOrders", signed=True)
print("open algo orders:", len(o) if isinstance(o, list) else o)
