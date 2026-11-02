"""Unit checks of PAPER-N1 amendment 1 and F4 amendment 1 (no network). Run: python src/audits/test_producer_amend1.py
P1 catch-up boundaries  P2 pending roll-forward / discard  P3 D close without a price  F1 F4 skip decision reads the ledger"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "execution"))
import paper_n1_portfolio as N

res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


T = pd.Timestamp("2026-10-22 12:00")
b = N.missed_boundaries("2026-10-22 00:00:00", T)
b2 = N.missed_boundaries("2026-10-10 00:00:00", T)
ok("P1", [str(x) for x in b] == ["2026-10-22 04:00:00", "2026-10-22 08:00:00", "2026-10-22 12:00:00"] and len(b2) == 12 and b2[-1] == T
   and N.missed_boundaries("2026-10-22 12:00:00", T) == [] and N.missed_boundaries(None, T) == [T],
   f"catch-up: 2 missed -> {len(b)} runs in order; 12-day gap capped at {len(b2)}; up to date -> none")
d = Path(tempfile.mkdtemp())
try:
    (d / "ledger.jsonl").write_text(json.dumps(dict(T="2026-10-22 08:00:00")) + "\n")
    (d / "state.json").write_text(json.dumps(dict(last_T="2026-10-22 04:00:00", tag="old")))
    (d / "state.json.pending").write_text(json.dumps(dict(last_T="2026-10-22 08:00:00", tag="new")))
    r1 = N.recover_pending(d); s1 = json.loads((d / "state.json").read_text())["tag"]
    (d / "state.json.pending").write_text(json.dumps(dict(last_T="2026-10-22 12:00:00", tag="newer")))
    r2 = N.recover_pending(d); s2 = json.loads((d / "state.json").read_text())["tag"]
    ok("P2", r1 == "rolled forward" and s1 == "new" and r2 == "discarded" and s2 == "new" and not (d / "state.json.pending").exists(),
       "pending state with its ledger line -> completed; pending without its ledger line -> discarded, state kept")
finally:
    shutil.rmtree(d)


class Src:                                   # a D-day cycle where the held D coin (DOGE, a real mapped perp) has no data at T
    n_req, errors = 0, []

    def klines(self, *a): return None
    def funding(self, *a): return []
    def perp_daily_qv(self, *a): return None


st = dict(cash=10_000.0, pos={"D|DOGEUSDT|1D|-1": dict(sleeve="D", side=1, entry=1.0, notional=100.0, units=100.0, venue="perp", t="2026-10-01",
                                                      last_px=1.2, fee=0.0)}, month="2026-10", E_m=10_000.0, last_T="2026-10-20 20:00:00", d_w={}, init_tfs=[])
TD = pd.Timestamp("2026-10-21 00:00")                       # (T - 1 d - 2020-02-01) % 5 == 0 ?
while ((TD - pd.Timedelta(days=1)) - N.D_ANCHOR).days % 5:
    TD += pd.Timedelta(days=1)
st["last_T"] = str(TD - pd.Timedelta(hours=4))
try:
    rec = N.cycle(Src(), st, TD)
    crashed = False
except KeyError:
    crashed = True
ok("P3", not crashed and "D|DOGEUSDT|1D|-1" not in st["pos"] and abs(st["cash"] - (10_000.0 + 100.0 * 0.2)) < 1e-9 and any("no price at T" in n for n in rec["notes"]),
   f"D close without a price on {TD.date()}: no crash, closed at last mark 1.2 (P&L +20), noted")
sys.path.insert(0, str(R_ / "src"))
import importlib.util
spec = importlib.util.spec_from_file_location("f4", R_ / "src" / "execution" / "forward_ls_f4.py")
F4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F4)
d = Path(tempfile.mkdtemp())
try:
    led = d / "ledger.csv"
    no_ledger = F4.already_logged("2026-10-21", led)
    pd.DataFrame([dict(asof="2026-10-20"), dict(asof="2026-10-21")]).to_csv(led, index=False)
    ok("F1", no_ledger is False and F4.already_logged("2026-10-21", led) and not F4.already_logged("2026-10-22", led),
       "F4 skip only when the ledger has the as-of row (an equity file alone no longer skips)")
finally:
    shutil.rmtree(d)
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
