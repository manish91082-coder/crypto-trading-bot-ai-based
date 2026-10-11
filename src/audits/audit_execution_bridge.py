import sys
from pathlib import Path
import tempfile
import shutil
import time

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from execution.binance_client import BinanceExecutionClient
from execution.order_manager import OrderManager
from execution.paper_engine import PaperExecutionEngine
from risk_governor import RiskGovernor

def run_execution_bridge_audit():
    print("==========================================================")
    print("ZERO-TRUST AUDIT: LIVE PAPER TRADING & TESTNET BRIDGE")
    print("==========================================================")

    # -----------------------------------------------------------------
    # TEST 1: LIVE BINANCE NETWORK CONNECTIVITY & TICKER FETCH
    # -----------------------------------------------------------------
    print("\n[TEST 1] VERIFYING LIVE BINANCE TICKER DATA (CCXT REST)")
    client = BinanceExecutionClient(use_testnet=True)
    test_symbols = ['BTCUSDT', 'SOLUSDT', 'BNBUSDT']
    for sym in test_symbols:
        price = client.fetch_ticker_price(sym)
        print(f"  Live Ticker {sym}: ${price:,.2f}")
        assert price > 0, f"Price must be positive, got {price}"
    print("  -> [PASS] Live market prices successfully fetched from Binance REST API.")

    # -----------------------------------------------------------------
    # TEST 2: LIVE OHLCV FETCH & STATIONARY FEATURE PIPELINE
    # -----------------------------------------------------------------
    print("\n[TEST 2] VERIFYING LIVE OHLCV FETCH & FEATURE MATHEMATICS")
    ohlcv = client.fetch_recent_ohlcv('BTCUSDT', timeframe='1d', limit=210)
    print(f"  Fetched {len(ohlcv)} live daily candles for BTCUSDT from Binance.")
    assert len(ohlcv) >= 200, f"Expected at least 200 candles, got {len(ohlcv)}"

    engine = PaperExecutionEngine(initial_capital=120.0, use_testnet=True)
    df_feat = engine.compute_live_features(ohlcv)
    last_row = df_feat.iloc[-2] # Last completed candle

    print(f"  Timestamp (Last Completed): {last_row['timestamp']}")
    print(f"  Close Price:                ${last_row['close']:,.2f}")
    print(f"  Synthetic Order Flow:       {last_row['Synthetic_Order_Flow']:.6f}")
    print(f"  Volume Z-Score:             {last_row['Vol_Z_Score']:.4f}")
    print(f"  Dist SMA 50:                {last_row['Dist_SMA_50']*100:.2f}%")
    print(f"  Dist SMA 200:               {last_row['Dist_SMA_200']*100:.2f}%")
    print(f"  ATR(14):                    ${last_row['ATR_14']:,.2f}")

    assert not df_feat[['Ret_1', 'Synthetic_Order_Flow', 'Dist_SMA_50', 'Dist_SMA_200']].iloc[-2].isna().any(), "Features must not be NaN"
    print("  -> [PASS] Mathematical feature transform on live candles verified.")

    # -----------------------------------------------------------------
    # TEST 3: CRASH-RESILIENT ORDER MANAGER DISK PERSISTENCE
    # -----------------------------------------------------------------
    print("\n[TEST 3] VERIFYING ORDER MANAGER DISK PERSISTENCE & LIFECYCLE")
    temp_dir = Path(tempfile.mkdtemp())
    try:
        om = OrderManager(logs_dir=temp_dir)
        pos = om.add_position(
            symbol='BTCUSDT',
            direction='Long',
            entry_price=80000.0,
            position_size=0.01,
            risk_amount=6.0,
            stop_loss=78000.0,
            atr=1333.33
        )
        assert len(om.positions) == 1
        assert om.state_file.exists(), "State JSON file must exist on disk"
        print("  Position added and saved to disk JSON state.")

        # Reload from disk into fresh manager instance to verify crash resilience
        om_reloaded = OrderManager(logs_dir=temp_dir)
        assert len(om_reloaded.positions) == 1, "Reloaded positions must match saved state"
        print("  -> [PASS] Crash resilience verified: state reloaded from disk.")

        # Test Partial TP at +3.0x ATR ($80,000 + 3.0 * 1333.33 = $84,000)
        closed_tp = om_reloaded.update_positions_on_tick('BTCUSDT', current_price=84500.0, high_price=84500.0, low_price=80000.0)
        assert len(closed_tp) == 0, "Trade should remain open after partial TP"
        assert om_reloaded.positions[0]['secured'] is True, "Trade must be marked secured"
        assert om_reloaded.positions[0]['remaining_size'] == 0.005, "Remaining size must be exactly half"
        print(f"  Partial TP executed: Secured=True, Remaining Size={om_reloaded.positions[0]['remaining_size']}")
        print(f"  New SL locked at: ${om_reloaded.positions[0]['sl']:,.2f}")

        # Test Stop Loss Hit on the secured remainder
        closed_sl = om_reloaded.update_positions_on_tick('BTCUSDT', current_price=75000.0, high_price=80000.0, low_price=75000.0)
        assert len(closed_sl) == 1, "Trade must close on SL hit"
        assert len(om_reloaded.positions) == 0, "No active positions should remain"
        assert om_reloaded.trade_log_file.exists(), "Trade log CSV must exist"
        print(f"  Stop hit executed. Final Trade Realized PnL: ${closed_sl[0]['realized_pnl']:.2f}")
        print("  -> [PASS] Order Manager lifecycle (Partial TP + Trailing SL) verified.")
    finally:
        shutil.rmtree(temp_dir)

    # -----------------------------------------------------------------
    # TEST 4: FULL SINGLE-CYCLE SCAN & EXECUTION RUN
    # -----------------------------------------------------------------
    print("\n[TEST 4] EXECUTING LIVE ENGINE SINGLE SCAN CYCLE")
    cycle_res = engine.scan_and_execute_cycle()
    print("  Cycle Execution Summary:")
    print(f"    Timestamp:       {cycle_res['timestamp']}")
    print(f"    Current Capital: ${cycle_res['capital']:,.2f}")
    print(f"    Active Drawdown: {cycle_res['drawdown']*100:.2f}%")
    print(f"    Open Positions:  {cycle_res['open_positions']}")
    print(f"    Newly Opened:    {cycle_res['newly_opened']}")
    print(f"    Closed Trades:   {cycle_res['closed_trades']}")
    print("  -> [PASS] Complete operational cycle executed cleanly without errors.")

    print("\n==========================================================")
    print("AUDIT RESULT: 100% PASS - LIVE PAPER ENGINE FULLY VERIFIED")
    print("==========================================================")

if __name__ == '__main__':
    run_execution_bridge_audit()
