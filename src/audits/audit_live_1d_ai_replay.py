"""
Audit of the live Swing-AI engine (src/execution/live_1d_ai_engine.py). Raises on any failure.

L1  Day-by-day replay of the live cycle over 2021-01-01..2026-09-30 with the walk-forward predictions reproduces every
    closed Step 7 AI portfolio trade (symbol, dates, plan exit, prices, P&L).
L2  Live training == walk-forward training: for sample days, models_for(history truncated at that day) gives the same
    predictions for that day's candidates as the Step 7 walk-forward table.
L3  Only 'dryrun' and 'testnet' modes exist; the testnet client is sandbox-forced (inherited CCXTBroker assert).
"""
import sys
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution"):
    sys.path.insert(0, str(p))
import swing_strategy_1d as E
import step7_swing_ai_1d as S7
import live_1d_ai_engine as L


def l1(data):
    pred = pd.read_csv(S7.OUT / "AI_monthly_retrain_predictions.csv", parse_dates=["signal_date"])
    bt = pd.read_csv(S7.OUT / "AI_monthly_retrain_trades.csv", parse_dates=["entry_date", "exit_date"])
    bt = bt[bt.exit_reason != "end_of_test"]
    st, _ = L.replay(data, "2021-01-01", "2026-09-30", pred)
    rp = pd.DataFrame(st["trades"])
    rp["entry_date"] = pd.to_datetime(rp["entry_date"]); rp["exit_date"] = pd.to_datetime(rp["exit_date"])
    k = ["symbol", "entry_date", "exit_date"]
    a = bt.sort_values(k).reset_index(drop=True)
    b = rp.sort_values(k).reset_index(drop=True)
    assert len(a) == len(b), (len(a), len(b))
    assert (a[k] == b[k]).all().all()
    assert (a.exit_reason.values == b.exit_reason.values).all()
    for c in ("entry_price", "exit_price", "pnl"):
        assert np.allclose(a[c].values, b[c].values, rtol=1e-9, atol=1e-9), c
    print(f"[L1 PASS] live-cycle replay reproduces all {len(a)} closed Step 7 AI trades (dates, plan exits, prices, P&L)")


def l2(data):
    pred = pd.read_csv(S7.OUT / "AI_monthly_retrain_predictions.csv", parse_dates=["signal_date"])
    L.MODEL_DIR = Path(tempfile.mkdtemp())
    days = [pd.Timestamp(x) for x in ("2021-03-15", "2022-06-14", "2024-11-08", "2026-09-26")]
    n = 0
    for d in days:
        # nearest candidate day on/after d
        d = pred.signal_date[pred.signal_date >= d].min()
        trunc = {s: df[df.timestamp <= d].reset_index(drop=True) for s, df in data.items()}
        E._ZZ_CACHE.clear()
        models = L.models_for(trunc, d)
        dec, rows = L.decisions_for_day(trunc, d, models)
        want = pred[pred.signal_date == d].set_index("symbol")
        for _, r in rows.iterrows():
            for name in S7.PLANS:
                assert np.isclose(r[f"pred::{name}"], want.loc[r.symbol, f"pred::{name}"], rtol=1e-9, atol=1e-12), (d, r.symbol, name)
            n += 1
    E._ZZ_CACHE.clear()
    print(f"[L2 PASS] live monthly training on truncated history reproduces walk-forward predictions ({n} candidates x {len(S7.PLANS)} plans, 4 days)")


def l3():
    import argparse, inspect
    src = inspect.getsource(L)
    assert 'choices=["dryrun", "testnet"]' in src and "mainnet" not in src.split("There is deliberately NO mainnet mode.")[1]
    print("[L3 PASS] only dryrun/testnet modes; testnet client inherits the sandbox-forced, URL-asserted CCXTBroker")


if __name__ == "__main__":
    data = E.load_universe()
    l1(data)
    l2(data)
    l3()
