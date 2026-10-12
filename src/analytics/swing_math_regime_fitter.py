"""
High-Speed Vectorized Regime-Adaptive Swing Mathematics Optimization Engine (2021 - 2026)
Zero-Trust Ground-Level Mathematical Analysis Across All 10 Coins (18,000+ Candles)

Pre-computes all numpy arrays for instant execution (< 3 seconds total).
Tests:
- "Market bear ho ya bull ho ya sideways ho, candle day me market niche aata hai upar jata hai.
  Jab niche aata hai tab lena hai, matlab jab upar ke liye mudta hai tab enter hona hai.
  Jab upar jata hai aur niche mudta hai tab trade kaatna hai."
- Explores why raw bear dips fail and how regime-adaptive swing rules solve it.
- Permutations of Bull Dip-Buy vs Bear Relief-Bounce vs Sideways Range-Reversion.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import DATA_RAW_DIR, LOGS_DIR, SYMBOLS, BINANCE_TAKER_FEE, INITIAL_CAPITAL

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean().bfill()

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-8)
    rsi = 100 - (100 / (1 + rs))
    return rsi.bfill()

def prepare_coin_data():
    """Pre-computes all series and aligns timestamps into matrix/lookup dicts."""
    raw_dfs = {}
    for s in SYMBOLS:
        p = DATA_RAW_DIR / f"{s}_1d_Raw_5Years.csv"
        df = pd.read_csv(p)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        df.reset_index(drop=True, inplace=True)
        df['atr'] = compute_atr(df, 14)
        df['rsi'] = compute_rsi(df['close'], 14)
        df['sma200'] = df['close'].rolling(200, min_periods=30).mean()
        df['roll_high_5'] = df['high'].rolling(5, min_periods=2).max()
        df['roll_high_7'] = df['high'].rolling(7, min_periods=2).max()
        df['prev_high'] = df['high'].shift(1)
        df['prev_close'] = df['close'].shift(1)
        df['prev2_close'] = df['close'].shift(2)
        raw_dfs[s] = df
        
    all_timestamps = sorted(list(set.union(*[set(df['timestamp']) for df in raw_dfs.values()])))
    time_map = {t: i for i, t in enumerate(all_timestamps)}
    n_days = len(all_timestamps)
    
    # Pack into efficient arrays per coin
    packed_coins = {}
    for s in SYMBOLS:
        df = raw_dfs[s]
        c_open = np.full(n_days, np.nan)
        c_high = np.full(n_days, np.nan)
        c_low = np.full(n_days, np.nan)
        c_close = np.full(n_days, np.nan)
        c_atr = np.full(n_days, np.nan)
        c_rsi = np.full(n_days, np.nan)
        c_sma200 = np.full(n_days, np.nan)
        c_rh5 = np.full(n_days, np.nan)
        c_rh7 = np.full(n_days, np.nan)
        c_ph = np.full(n_days, np.nan)
        c_pc = np.full(n_days, np.nan)
        c_p2c = np.full(n_days, np.nan)
        
        for _, r in df.iterrows():
            idx = time_map[r['timestamp']]
            c_open[idx] = r['open']
            c_high[idx] = r['high']
            c_low[idx] = r['low']
            c_close[idx] = r['close']
            c_atr[idx] = r['atr']
            c_rsi[idx] = r['rsi']
            c_sma200[idx] = r['sma200']
            c_rh5[idx] = r['roll_high_5']
            c_rh7[idx] = r['roll_high_7']
            c_ph[idx] = r['prev_high']
            c_pc[idx] = r['prev_close']
            c_p2c[idx] = r['prev2_close']
            
        packed_coins[s] = {
            'open': c_open, 'high': c_high, 'low': c_low, 'close': c_close,
            'atr': c_atr, 'rsi': c_rsi, 'sma200': c_sma200,
            'rh5': c_rh5, 'rh7': c_rh7, 'ph': c_ph, 'pc': c_pc, 'p2c': c_p2c
        }
        
    return packed_coins, all_timestamps

def fast_simulate(
    packed_coins: Dict,
    n_days: int,
    bull_pb_atr: float,
    bull_confirm: str,
    bear_pb_atr: float,
    bear_rsi_max: float,
    bear_confirm: str,
    tp_bull: float,
    tp_bear: float,
    sl_mult: float,
    trailing_mult: float,
    max_concurrent: int = 3
):
    cash = INITIAL_CAPITAL
    open_trades = []
    closed_trades = []
    
    for t_idx in range(30, n_days - 1):
        # 1. Manage Exits
        for tr in open_trades[:]:
            s = tr['symbol']
            curr_h = packed_coins[s]['high'][t_idx]
            curr_l = packed_coins[s]['low'][t_idx]
            curr_c = packed_coins[s]['close'][t_idx]
            if np.isnan(curr_c):
                continue
                
            atr = tr['atr']
            days_held = t_idx - tr['entry_idx']
            closed = False
            exit_price = 0.0
            exit_reason = ""
            
            # SL check
            if curr_l <= tr['sl']:
                exit_price = tr['sl']
                closed = True
                exit_reason = 'Trailing SL' if tr['secured'] else 'Stop Loss'
            else:
                # TP check
                tp_target = tr['tp_target']
                if not tr['secured'] and curr_h >= (tr['entry_price'] + tp_target * atr):
                    tr['secured'] = True
                    tr['sl'] = max(tr['sl'], tr['entry_price'] + 0.5 * atr)
                    if curr_l <= tr['sl']:
                        exit_price = tr['sl']
                        closed = True
                        exit_reason = 'Trailing SL Post-TP'
                        
                # Dynamic Trailing Stop
                if tr['secured'] and not closed:
                    tr['sl'] = max(tr['sl'], curr_h - trailing_mult * atr)
                    
                # Inactivity timeout (14d)
                if not closed and days_held >= 14:
                    exit_price = curr_c
                    closed = True
                    exit_reason = 'Timeout (14d)'
                    
            if closed:
                proceeds = exit_price * tr['position_size']
                fee = proceeds * BINANCE_TAKER_FEE
                net_proceeds = proceeds - fee
                cost = tr['position_size'] * tr['entry_price']
                trade_pnl = net_proceeds - cost - tr['entry_fee']
                cash += net_proceeds
                
                tr['exit_idx'] = t_idx
                tr['exit_price'] = exit_price
                tr['net_pnl'] = trade_pnl
                tr['return_pct'] = (trade_pnl / cost) * 100.0
                tr['outcome'] = 'WIN' if trade_pnl > 0 else 'LOSS'
                tr['exit_reason'] = exit_reason
                tr['days_held'] = days_held
                
                closed_trades.append(tr)
                open_trades.remove(tr)
                
        # 2. Check Candidate Entries for Day t_idx + 1 Open
        if len(open_trades) < max_concurrent:
            available_slots = max_concurrent - len(open_trades)
            candidates = []
            next_idx = t_idx + 1
            
            for s in SYMBOLS:
                if any(tr['symbol'] == s for tr in open_trades):
                    continue
                d = packed_coins[s]
                c = d['close'][t_idx]
                o = d['open'][t_idx]
                h = d['high'][t_idx]
                l = d['low'][t_idx]
                atr = d['atr'][t_idx]
                rsi = d['rsi'][t_idx]
                sma200 = d['sma200'][t_idx]
                next_o = d['open'][next_idx]
                
                if np.isnan(c) or np.isnan(atr) or np.isnan(next_o):
                    continue
                    
                is_bull = (c >= sma200)
                triggered = False
                tp_target = tp_bull if is_bull else tp_bear
                regime_type = "BULL" if is_bull else "BEAR"
                conviction = 0.0
                
                if is_bull:
                    # Bull Market Dip-Buy
                    h5 = d['rh5'][t_idx]
                    pb = h5 - c
                    if pb >= (bull_pb_atr * atr):
                        if bull_confirm == 'break_prev_high':
                            triggered = (c > d['ph'][t_idx])
                        elif bull_confirm == 'two_higher_closes':
                            triggered = (c > d['pc'][t_idx] > d['p2c'][t_idx]) and (c > o)
                        elif bull_confirm == 'green_candle':
                            triggered = (c > o) and (c > d['pc'][t_idx])
                        conviction = (h5 - l) / atr
                else:
                    # Bear Market Relief Bounce
                    h7 = d['rh7'][t_idx]
                    pb = h7 - c
                    is_oversold = (rsi <= bear_rsi_max) or (pb >= (bear_pb_atr * atr))
                    if is_oversold:
                        if bear_confirm == 'green_candle':
                            triggered = (c > o) and (c > d['pc'][t_idx])
                        elif bear_confirm == 'break_prev_high':
                            triggered = (c > d['ph'][t_idx])
                        elif bear_confirm == 'hammer_or_engulf':
                            bar_range = h - l + 1e-8
                            lower_wick = (min(o, c) - l) / bar_range
                            triggered = (c > o) and (lower_wick >= 0.35 or c > d['ph'][t_idx])
                        conviction = 50.0 - rsi
                        
                if triggered:
                    candidates.append({
                        'symbol': s,
                        'regime': regime_type,
                        'tp_target': tp_target,
                        'atr': atr,
                        'conviction': conviction,
                        'entry_idx': next_idx,
                        'entry_price': next_o
                    })
                    
            candidates.sort(key=lambda x: x['conviction'], reverse=True)
            
            for cand in candidates[:available_slots]:
                alloc_capital = cash / float(max_concurrent - len(open_trades))
                if alloc_capital < 5.0:
                    continue
                ep = cand['entry_price']
                pos_size = alloc_capital / ep
                entry_fee = alloc_capital * BINANCE_TAKER_FEE
                cash -= (alloc_capital + entry_fee)
                
                open_trades.append({
                    'symbol': cand['symbol'],
                    'direction': 'Long',
                    'regime': cand['regime'],
                    'entry_idx': cand['entry_idx'],
                    'entry_price': ep,
                    'position_size': pos_size,
                    'allocated_capital': alloc_capital,
                    'atr': cand['atr'],
                    'tp_target': cand['tp_target'],
                    'sl': ep - (sl_mult * cand['atr']),
                    'secured': False,
                    'entry_fee': entry_fee
                })
                
    return closed_trades, cash

def main():
    print("==========================================================================")
    print("VECTORIZED REGIME-ADAPTIVE SWING MATHEMATICS (10 COINS, 5 YEARS)")
    print("Testing 100+ Formations of Per-Day Bottom-Dip Reversals")
    print("==========================================================================")
    
    packed_coins, all_timestamps = prepare_coin_data()
    n_days = len(all_timestamps)
    print(f"[+] Loaded & pre-vectorized data for 10 coins across {n_days} days.")
    
    grid = []
    for b_pb in [1.0, 1.4, 1.8]:
        for b_conf in ['green_candle', 'break_prev_high', 'two_higher_closes']:
            for bear_pb in [1.8, 2.5]:
                for bear_rsi in [35.0, 42.0]:
                    for bear_conf in ['green_candle', 'break_prev_high', 'hammer_or_engulf']:
                        for tp_bull in [3.0, 3.5]:
                            for tp_bear in [2.0, 2.5]:
                                grid.append({
                                    'bull_pb_atr': b_pb,
                                    'bull_confirm': b_conf,
                                    'bear_pb_atr': bear_pb,
                                    'bear_rsi_max': bear_rsi,
                                    'bear_confirm': bear_conf,
                                    'tp_bull': tp_bull,
                                    'tp_bear': tp_bear,
                                    'sl_mult': 1.5,
                                    'trailing_mult': 1.8
                                })
                                
    print(f"[+] Total Formations in Grid: {len(grid)}")
    
    results = []
    for idx, params in enumerate(grid):
        trades, final_cash = fast_simulate(
            packed_coins=packed_coins,
            n_days=n_days,
            bull_pb_atr=params['bull_pb_atr'],
            bull_confirm=params['bull_confirm'],
            bear_pb_atr=params['bear_pb_atr'],
            bear_rsi_max=params['bear_rsi_max'],
            bear_confirm=params['bear_confirm'],
            tp_bull=params['tp_bull'],
            tp_bear=params['tp_bear'],
            sl_mult=params['sl_mult'],
            trailing_mult=params['trailing_mult'],
            max_concurrent=3
        )
        
        n_tr = len(trades)
        if n_tr == 0:
            continue
            
        df_tr = pd.DataFrame(trades)
        wins = df_tr[df_tr['outcome'] == 'WIN']
        losses = df_tr[df_tr['outcome'] == 'LOSS']
        wr = (len(wins) / n_tr) * 100.0
        
        gross_win = wins['net_pnl'].sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses['net_pnl'].sum()) if len(losses) > 0 else 1e-8
        pf = gross_win / gross_loss
        total_pnl = df_tr['net_pnl'].sum()
        final_equity = INITIAL_CAPITAL + total_pnl
        net_ret_pct = (total_pnl / INITIAL_CAPITAL) * 100.0
        
        bull_tr = df_tr[df_tr['regime'] == 'BULL']
        bear_tr = df_tr[df_tr['regime'] == 'BEAR']
        
        bull_wr = (len(bull_tr[bull_tr['outcome'] == 'WIN']) / len(bull_tr)) * 100.0 if len(bull_tr) > 0 else 0.0
        bear_wr = (len(bear_tr[bear_tr['outcome'] == 'WIN']) / len(bear_tr)) * 100.0 if len(bear_tr) > 0 else 0.0
        bull_pnl = bull_tr['net_pnl'].sum() if len(bull_tr) > 0 else 0.0
        bear_pnl = bear_tr['net_pnl'].sum() if len(bear_tr) > 0 else 0.0
        
        results.append({
            'Config_ID': idx + 1,
            'Bull_PB': params['bull_pb_atr'],
            'Bull_Confirm': params['bull_confirm'],
            'Bear_PB': params['bear_pb_atr'],
            'Bear_RSI': params['bear_rsi_max'],
            'Bear_Confirm': params['bear_confirm'],
            'TP_Bull': params['tp_bull'],
            'TP_Bear': params['tp_bear'],
            'Total_Trades': n_tr,
            'Trades_Per_Year': round(n_tr / 5.0, 1),
            'Trades_Per_Month': round(n_tr / 60.0, 1),
            'Win_Rate_Pct': round(wr, 2),
            'Profit_Factor': round(pf, 2),
            'Initial_Capital': INITIAL_CAPITAL,
            'Final_Equity': round(final_equity, 2),
            'Net_Return_Pct': round(net_ret_pct, 2),
            'Bull_Trades': len(bull_tr),
            'Bull_WR': round(bull_wr, 1),
            'Bull_PnL': round(bull_pnl, 2),
            'Bear_Trades': len(bear_tr),
            'Bear_WR': round(bear_wr, 1),
            'Bear_PnL': round(bear_pnl, 2),
            'Avg_Days_Held': round(df_tr['days_held'].mean(), 1)
        })
        
    df_res = pd.DataFrame(results)
    df_res.sort_values(by=['Profit_Factor', 'Net_Return_Pct'], ascending=[False, False], inplace=True)
    df_res.reset_index(drop=True, inplace=True)
    
    out_csv = LOGS_DIR / "regime_adaptive_swing_grid_results.csv"
    df_res.to_csv(out_csv, index=False)
    print(f"\n[+] Evaluated {len(df_res)} Full Formations in seconds! Saved to: {out_csv.name}")
    
    print("\n==========================================================================")
    print("TOP 10 REGIME-ADAPTIVE SWING FORMATIONS (RANKED BY PROFIT FACTOR)")
    print("==========================================================================")
    for i, r in df_res.head(10).iterrows():
        print(f"Rank {i+1}: Config #{r['Config_ID']} | Bull_PB={r['Bull_PB']}x ({r['Bull_Confirm']}) | Bear_PB={r['Bear_PB']}x, RSI<={r['Bear_RSI']} ({r['Bear_Confirm']})")
        print(f"   Trades: {r['Total_Trades']} ({r['Trades_Per_Year']}/yr, {r['Trades_Per_Month']}/mo) | Win Rate: {r['Win_Rate_Pct']}% | Profit Factor: {r['Profit_Factor']}")
        print(f"   Return: {r['Net_Return_Pct']:+.2f}% ($120 -> ${r['Final_Equity']:.2f}) | Avg Days: {r['Avg_Days_Held']}")
        print(f"   Bull: {r['Bull_Trades']} trades, {r['Bull_WR']}% WR, PnL: ${r['Bull_PnL']:+.2f} | Bear: {r['Bear_Trades']} trades, {r['Bear_WR']}% WR, PnL: ${r['Bear_PnL']:+.2f}")
        print("   " + "-" * 75)

    # Save to Excel
    out_excel = LOGS_DIR / "REGIME_ADAPTIVE_SWING_OPTIMIZATION_5YEARS.xlsx"
    with pd.ExcelWriter(out_excel, engine='openpyxl') as writer:
        df_res.to_excel(writer, sheet_name='All_Formations', index=False)
        df_res.head(10).to_excel(writer, sheet_name='Top_10_Formations', index=False)
    print(f"[+] Saved Master Excel: {out_excel.name}")

if __name__ == '__main__':
    main()
