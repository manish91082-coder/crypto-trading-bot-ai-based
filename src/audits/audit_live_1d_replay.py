"""
Zero-trust proof that the LIVE 1D engine makes exactly the backtest's decisions.
  L1  Replay the live daily cycle (ReplayBroker: fills at next open, stops via OHLC) over 2021-01-01..2026-09-30
      and compare every closed trade with E.simulate(CFG, reserve=20%) on the same window:
      symbol, signal/entry/exit dates, entry/exit prices, units, exit reason, P&L must be identical.
  L2  Live-data path safety: CCXTBroker refuses anything but Binance TESTNET (asserted in code; checked here by
      source inspection) and there is no mainnet mode.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import swing_strategy_1d as E
import live_1d_swing_engine as L


def l1(data):
    for start, end in [("2021-01-01", "2022-12-31"), ("2023-01-01", "2026-09-30")]:
        state, log = L.replay(data, start, end)
        rp = pd.DataFrame(state["trades"])
        bt, _, _ = E.simulate(data, L.CFG, start=start, end=end, reserve=L.RESERVE)
        bt = bt[bt["exit_reason"] != "end_of_test"].copy()
        for c in ("signal_date", "entry_date", "exit_date"):
            rp[c] = pd.to_datetime(rp[c])
            bt[c] = pd.to_datetime(bt[c])
        cols = ["symbol", "signal_date", "entry_date", "exit_date", "exit_reason"]
        a = rp.sort_values(["entry_date", "symbol"]).reset_index(drop=True)
        b = bt.sort_values(["entry_date", "symbol"]).reset_index(drop=True)
        assert len(a) == len(b), (len(a), len(b))
        pd.testing.assert_frame_equal(a[cols], b[cols])
        for c in ("entry_price", "exit_price", "units", "pnl"):
            assert np.allclose(a[c].values, b[c].values, rtol=1e-9, atol=1e-6), c
        print(f"[L1 PASS] {start}..{end}: {len(a)} closed trades -- live-cycle replay == backtest engine "
              f"(dates, prices, units, reasons, P&L); {len(log)} daily cycles")


def l2():
    src = (SRC_DIR / "execution" / "live_1d_swing_engine.py").read_text(encoding="utf-8")
    assert 'choices=["dryrun", "testnet"]' in src and "set_sandbox_mode(True)" in src
    assert 'assert "testnet" in self.ex.urls["api"]["public"]' in src
    assert "mainnet" not in src.replace("NO mainnet mode", "").replace("no mainnet mode", "")
    print("[L2 PASS] only 'dryrun' and 'testnet' modes exist; testnet client is sandbox-forced and URL-asserted")


if __name__ == "__main__":
    data = E.load_universe()
    l1(data)
    l2()
    print("LIVE 1D ENGINE REPLAY AUDIT PASSED")
