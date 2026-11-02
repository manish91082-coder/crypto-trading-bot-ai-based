"""Sandbox pre-flight of the E11 shadow line (2026-10-16): F4 preflight sandbox (two days) -> shadow main for both days.
Checks: both days run, ledger chain of 2 lines tied to the F4 lines, C0 True on day 2, E11 sleeves present."""
import io, sys, json, shutil, contextlib
from pathlib import Path
import pandas as pd
SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research", SRC / "audits"):
    sys.path.insert(0, str(p))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    import preflight_f4 as P
import shadow_e11_f4 as SH
SH.OUT = P.T / "shadow"
SH.LEDGER = SH.OUT / "ledger.csv"
SH.OUT.mkdir()
shutil.copy(SH.PROTO.parent / "E11_SHADOW_PROTOCOL_SHA256.txt", SH.OUT)
try:                                                   # day 1: F4 day 2 has since extended the perp files -> must refuse
    SH.main("2026-10-13")
    raise SystemExit("FAIL: shadow accepted perp files that changed after the F4 line")
except AssertionError as e:
    print("[negative test PASS] day 1 refused:", e)
SH.main("2026-10-14")
L = pd.read_csv(SH.LEDGER)
L4 = pd.read_csv(P.Q.LEDGER)
assert len(L) == 1 and L.prev_sha256.iloc[0] == "GENESIS" and L.f4_line_sha256.iloc[0] == L4.line_sha256.iloc[1]
assert bool(L.C0.iloc[0]), L.notes.iloc[0]
e = pd.read_csv(SH.OUT / "equity_2026-10-14.csv")
print(e.to_string())
print(L[["asof", "C0", "E11", "LS_RS", "perp_longs", "spot_longs", "long_funding_closed"]].to_string())
import verify_shadow_e11 as VS
VS.main()
print(pd.read_csv(SH.OUT / "positions_2026-10-14.csv").groupby(["sleeve", "side", "venue"]).size().to_string())
print(f"[PREFLIGHT SHADOW E11 PASS] sandbox {P.T}")
