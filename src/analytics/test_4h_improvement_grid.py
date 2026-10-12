import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline_4h.step3_5year_governed_backtest_4h import load_data_and_models_4h, run_4h_simulation

def test_grid():
    print("==========================================================================")
    print("4H SYSTEM IMPROVEMENT & ALPHA EXPANSION GRID OPTIMIZATION (2021-2026)")
    print("Testing Parameter Calibrations: Max Concurrent (4, 5, 6), Thresholds & Accumulation")
    print("==========================================================================")

    master_df, prices_ohlc, btc_bullish_map, btc_crash_map = load_data_and_models_4h()

    configs = [
        {"name": "Base Approved (393 Trades)", "mc": 4, "tl": 0.48, "ts": 0.52, "vol": 0.8, "sl_l": 7.5, "sl_s": 6.5},
        {"name": "Exp 1: Max Concurrent 5", "mc": 5, "tl": 0.48, "ts": 0.52, "vol": 0.8, "sl_l": 7.5, "sl_s": 6.5},
        {"name": "Exp 2: Max Concurrent 6", "mc": 6, "tl": 0.48, "ts": 0.52, "vol": 0.8, "sl_l": 7.5, "sl_s": 6.5},
        {"name": "Exp 3: Vol Accum 0.75 + MC 5", "mc": 5, "tl": 0.48, "ts": 0.52, "vol": 0.75, "sl_l": 7.5, "sl_s": 6.5},
        {"name": "Exp 4: Long 0.47, Short 0.51 + MC 5", "mc": 5, "tl": 0.47, "ts": 0.51, "vol": 0.8, "sl_l": 7.5, "sl_s": 6.5},
        {"name": "Exp 5: Tighter Trail (1.2x) on Runner + MC 5", "mc": 5, "tl": 0.48, "ts": 0.52, "vol": 0.8, "sl_l": 7.5, "sl_s": 6.5},
        {"name": "Exp 6: Vol Accum 0.70 + MC 6", "mc": 6, "tl": 0.48, "ts": 0.52, "vol": 0.70, "sl_l": 7.5, "sl_s": 6.5},
    ]

    results = []
    for c in configs:
        res = run_4h_simulation(
            master_df, prices_ohlc, btc_bullish_map, btc_crash_map,
            mode='bi_directional',
            threshold_long=c['tl'],
            threshold_short=c['ts'],
            max_concurrent=c['mc'],
            vol_accum_min=c['vol'],
            sl_cap_long=c['sl_l'],
            sl_cap_short=c['sl_s']
        )
        results.append({
            "Configuration": c['name'],
            "Max_Concurrent": c['mc'],
            "Threshold_L/S": f"{c['tl']}/{c['ts']}",
            "Vol_Accum": c['vol'],
            "Total_Trades": res['total_trades'],
            "Win_Rate_Pct": round(res['win_rate_pct'], 1),
            "Profit_Factor": round(res['profit_factor'], 2),
            "Net_Return_Pct": round(res['net_return_pct'], 2),
            "Final_Equity_USDT": round(res['final_equity'], 2),
            "Max_Drawdown_Pct": round(res['max_drawdown_pct'], 2),
            "Sharpe_Ratio": round(res['annualized_sharpe'], 2)
        })

    df_res = pd.DataFrame(results)
    print("\n" + "=" * 110)
    print(df_res.to_string(index=False))
    print("=" * 110)

if __name__ == '__main__':
    test_grid()
