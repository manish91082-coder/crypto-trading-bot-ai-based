"""Read-only: margin type and leverage per symbol on the F6 futures account (GET /fapi/v1/symbolConfig).
Usage: python f6_demo_symbol_config.py demo|testnet SYM1 SYM2 ..."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))
import futures_testnet_f6 as F

c = F.Client(sys.argv[1])
for s in sys.argv[2:]:
    r = c.get("/fapi/v1/symbolConfig", signed=True, symbol=s)
    r = r[0] if isinstance(r, list) and r else r
    print(s, {k: r.get(k) for k in ("marginType", "leverage", "isAutoAddMargin")} if isinstance(r, dict) and not r.get("_error") else r)
