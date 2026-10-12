import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline_1d.step7_full_5year_governed_backtest import load_data_and_features
from config import INITIAL_CAPITAL, BINANCE_TAKER_FEE, TP_ATR_MULT, SL_ATR_MULT, BE_ATR_MULT, PARTIAL_TP_PCT, RUNNER_PCT, RUNNER_TRAILING_ATR, RUNNER_SL_LOCK_ATR
from risk_governor import RiskGovernor

def run_calibrated_audit(threshold_long=0.38):
    master_df, prices_ohlc, btc_bullish_map = load_data_and_features()
    
    # Load BTC raw for systemic crash check
    from config import DATA_RAW_DIR
    btc_raw = pd.read_csv(DATA_RAW_DIR / "BTCUSDT_1d_Raw_5Years.csv")
    btc_raw['timestamp'] = pd.to_datetime(btc_raw['timestamp'])
    btc_raw.sort_values('timestamp', inplace=True)
    btc_raw['btc_ret1'] = btc_raw['close'].pct_change(1)
    btc_crash_map = dict(zip(btc_raw['timestamp'], btc_raw['btc_ret1'] <= -0.06)) # -6% crash day
    
    unique_timestamps = sorted(master_df['timestamp'].unique())
    time_to_idx = {t: i for i, t in enumerate(unique_timestamps)}
    
    governor = RiskGovernor(
        initial_capital=INITIAL_CAPITAL,
        base_risk_pct=0.05,
        max_concurrent_trades=3,
        max_portfolio_risk_pct=0.12,
        dd_tier_1=0.10,
        dd_tier_2=0.20,
        dd_tier_3=0.35,
        min_risk_pct=0.015
    )
    
    current_cash = INITIAL_CAPITAL
    peak_mtm_equity = INITIAL_CAPITAL
    max_mtm_drawdown = 0.0
    
    open_trades = []
    closed_trades = []
    daily_records = []
    
    for t in unique_timestamps:
        curr_idx = time_to_idx[t]
        
        # 1. EXITS
        for trade in open_trades[:]:
            sym = trade['symbol']
            if t not in prices_ohlc[sym]:
                continue
                
            candle = prices_ohlc[sym][t]
            h, l, o, c = candle['high'], candle['low'], candle['open'], candle['close']
            atr = trade['atr']
            days_held = (t - trade['entry_time']).days
            
            closed = False
            exit_price = 0.0
            exit_reason = ""
            
            if trade['direction'] == 'Long':
                if l <= trade['sl']:
                    exit_price = trade['sl']
                    closed = True
                    exit_reason = 'Trailing Stop' if trade['secured'] else 'Stop Loss'
                else:
                    # Partial TP (+3.0x ATR)
                    if not trade['secured'] and h >= trade['entry_price'] + TP_ATR_MULT * atr:
                        tp_price = trade['entry_price'] + TP_ATR_MULT * atr
                        part_units = trade['position_size'] * PARTIAL_TP_PCT
                        part_proceeds = tp_price * part_units
                        part_fee = part_proceeds * BINANCE_TAKER_FEE
                        net_part_proceeds = part_proceeds - part_fee
                        part_cost = part_units * trade['entry_price']
                        part_pnl = net_part_proceeds - part_cost
                        
                        current_cash += net_part_proceeds
                        trade['allocated_capital'] -= part_cost
                        trade['realized_pnl'] += part_pnl
                        trade['position_size'] -= part_units
                        trade['risk_amount'] *= RUNNER_PCT
                        trade['secured'] = True
                        
                        trade['sl'] = max(trade['sl'], trade['entry_price'] + RUNNER_SL_LOCK_ATR * atr)
                        
                        if l <= trade['sl']:
                            exit_price = trade['sl']
                            closed = True
                            exit_reason = 'Trailing Stop'
                            
                    # Dynamic Trailing Stop for 25% Runner
                    if trade['secured'] and not closed:
                        trade['sl'] = max(trade['sl'], h - RUNNER_TRAILING_ATR * atr)
                        
                    # Breakeven SL (+1.5x ATR)
                    if not trade['secured'] and not closed and h >= trade['entry_price'] + BE_ATR_MULT * atr:
                        trade['sl'] = max(trade['sl'], trade['entry_price'])
                        
            if closed:
                exit_proceeds = exit_price * trade['position_size']
                exit_fee = exit_proceeds * BINANCE_TAKER_FEE
                net_exit_proceeds = exit_proceeds - exit_fee
                cost = trade['position_size'] * trade['entry_price']
                net_closing_pnl = net_exit_proceeds - cost
                current_cash += net_exit_proceeds
                
                total_trade_pnl = net_closing_pnl - trade['entry_fee']
                trade['realized_pnl'] += total_trade_pnl
                trade['exit_time'] = t
                trade['exit_price'] = exit_price
                trade['exit_reason'] = exit_reason
                trade['days_held'] = days_held
                
                governor.update_capital(current_cash)
                closed_trades.append(trade)
                open_trades.remove(trade)
                
        # 2. ENTRIES FOR T+1
        if curr_idx + 1 < len(unique_timestamps):
            next_t = unique_timestamps[curr_idx + 1]
            day_signals = master_df[master_df['timestamp'] == t]
            
            # Check systemic crash day
            is_btc_crash = btc_crash_map.get(t, False)
            if is_btc_crash:
                continue # Macro Crash Defense: No new longs on systemic dump days
                
            is_btc_bull = btc_bullish_map.get(t, False)
            
            candidates = []
            for _, row in day_signals.iterrows():
                sym = row['Symbol']
                if any(tr['symbol'] == sym for tr in open_trades):
                    continue
                if next_t not in prices_ohlc[sym]:
                    continue
                    
                p_l = row['p_long']
                
                # Dynamic Regime Alignment:
                # - If BTC is Bullish: allow any setup with p_l >= threshold_long
                # - If BTC is Consolidating/Neutral: allow if coin itself has relative momentum >= 0 OR p_l >= 0.40
                # - If BTC is Bearish: allow high-conviction setups or oversold turns
                can_enter = False
                if is_btc_bull:
                    if p_l >= threshold_long:
                        can_enter = True
                else:
                    if row['Rel_Mom_vs_BTC'] >= 0.0 and p_l >= threshold_long:
                        can_enter = True
                    elif p_l >= 0.42:
                        can_enter = True
                    elif p_l >= threshold_long and (row['Pullback_Depth'] >= 0.08 or row['SL_Dist_Ratio'] <= 0.065 or row['Vol_Accum_Ratio'] >= 1.05):
                        can_enter = True
                        
                if can_enter:
                    candidates.append({
                        'symbol': sym,
                        'direction': 'Long',
                        'confidence': p_l,
                        'atr': row['ATR_14'],
                        'vol_accum_ratio': row['Vol_Accum_Ratio'],
                        'pullback_depth': row['Pullback_Depth'],
                        'sl_dist_ratio': row['SL_Dist_Ratio'],
                        'entry_time': next_t,
                        'entry_price': prices_ohlc[sym][next_t]['open']
                    })
                    
            candidates.sort(key=lambda x: x['confidence'], reverse=True)
            
            for c in candidates:
                sl_distance = SL_ATR_MULT * c['atr']
                sl = c['entry_price'] - sl_distance
                sl_dist_pct = (sl_distance / c['entry_price']) * 100.0
                v_ratio = c['vol_accum_ratio']
                conf = c['confidence']
                
                # Calibrated Quality Grading
                if conf >= 0.46 and sl_dist_pct <= 7.0 and v_ratio >= 1.0:
                    grade = "Grade A+"
                    q_mult = 1.25
                elif conf >= 0.40 and sl_dist_pct <= 9.0:
                    grade = "Grade A"
                    q_mult = 1.00
                elif conf >= 0.38 and sl_dist_pct <= 12.0:
                    grade = "Grade B"
                    q_mult = 0.65
                else:
                    grade = "Grade C"
                    q_mult = 0.00
                    
                decision = governor.evaluate_entry(
                    current_capital=current_cash,
                    entry_price=c['entry_price'],
                    stop_loss=sl,
                    open_trades=open_trades,
                    atr=c['atr'],
                    quality_multiplier=q_mult,
                    setup_grade=grade
                )
                
                if not decision.approved:
                    continue
                    
                total_portfolio_equity = current_cash + sum(tr['allocated_capital'] for tr in open_trades)
                base_slot_cap = total_portfolio_equity / 3
                target_notional = base_slot_cap * q_mult
                target_notional = min(target_notional, current_cash * 0.95)
                
                if target_notional < 5.0 or current_cash < target_notional:
                    continue
                    
                position_size = target_notional / c['entry_price']
                notional = target_notional
                risk_amount = position_size * sl_distance
                current_cash -= notional
                allocated_cap = notional
                
                entry_fee = notional * BINANCE_TAKER_FEE
                current_cash -= entry_fee
                governor.update_capital(current_cash)
                
                open_trades.append({
                    'symbol': c['symbol'],
                    'direction': c['direction'],
                    'confidence': c['confidence'],
                    'grade': grade,
                    'quality_multiplier': q_mult,
                    'sl_dist_pct': round(sl_dist_pct, 2),
                    'entry_time': c['entry_time'],
                    'entry_price': c['entry_price'],
                    'sl': sl,
                    'atr': c['atr'],
                    'risk_amount': risk_amount,
                    'position_size': position_size,
                    'allocated_capital': allocated_cap,
                    'secured': False,
                    'realized_pnl': 0.0,
                    'entry_fee': entry_fee,
                    'risk_pct': decision.risk_pct
                })
                
        # 3. MTM EQUITY & DD
        floating_pnl = 0.0
        open_allocated = 0.0
        for tr in open_trades:
            sym = tr['symbol']
            curr_close = prices_ohlc[sym][t]['close']
            floating_pnl += (curr_close - tr['entry_price']) * tr['position_size']
            open_allocated += tr['allocated_capital']
            
        mtm_equity = current_cash + open_allocated + floating_pnl
        if mtm_equity > peak_mtm_equity:
            peak_mtm_equity = mtm_equity
        mtm_dd = (peak_mtm_equity - mtm_equity) / peak_mtm_equity if peak_mtm_equity > 0 else 0.0
        if mtm_dd > max_mtm_drawdown:
            max_mtm_drawdown = mtm_dd
            
        daily_records.append({
            'timestamp': t,
            'cash': current_cash,
            'mtm_equity': mtm_equity,
            'drawdown': mtm_dd,
            'open_positions': len(open_trades)
        })
        
    df_trades = pd.DataFrame(closed_trades)
    df_daily = pd.DataFrame(daily_records)
    
    n_tr = len(df_trades)
    wins = df_trades[df_trades['realized_pnl'] > 0] if n_tr > 0 else pd.DataFrame()
    losses = df_trades[df_trades['realized_pnl'] <= 0] if n_tr > 0 else pd.DataFrame()
    wr = (len(wins) / n_tr * 100.0) if n_tr > 0 else 0.0
    
    gross_win = wins['realized_pnl'].sum() if len(wins) > 0 else 0.0
    gross_loss = abs(losses['realized_pnl'].sum()) if len(losses) > 0 else 1e-8
    pf = gross_win / gross_loss
    total_pnl = df_trades['realized_pnl'].sum() if n_tr > 0 else 0.0
    final_eq = df_daily['mtm_equity'].iloc[-1]
    
    penny_check = abs((INITIAL_CAPITAL + total_pnl) - final_eq)
    
    print(f"Results for threshold_long = {threshold_long}:")
    print(f"  Total Trades:     {n_tr} ({n_tr/5.0:.1f}/yr, {n_tr/60.0:.1f}/mo)")
    print(f"  Wins/Losses:      {len(wins)} / {len(losses)} (Win Rate: {wr:.2f}%)")
    print(f"  Profit Factor:    {pf:.2f}")
    print(f"  Gross Profit:     ${gross_win:.2f} | Gross Loss: ${gross_loss:.2f}")
    print(f"  Total Realized:   ${total_pnl:+.2f}")
    print(f"  Final Equity:     ${final_eq:.2f} (Return: {((final_eq-120)/120)*100:+.2f}%)")
    print(f"  Max Drawdown:     {max_mtm_drawdown*100:.2f}%")
    print(f"  Penny Discrepancy: ${penny_check:.6f}")
    
    # Check Research vs Vault
    df_trades['exit_time'] = pd.to_datetime(df_trades['exit_time'])
    tr_research = df_trades[df_trades['exit_time'] <= '2024-12-31']
    tr_vault = df_trades[df_trades['exit_time'] > '2024-12-31']
    print(f"  Research Trades (2021-2024): {len(tr_research)} | Vault Trades (2025-2026): {len(tr_vault)}")
    
    return n_tr, wr, pf, final_eq, max_mtm_drawdown

if __name__ == '__main__':
    for th in [0.41, 0.42, 0.43, 0.44, 0.45]:
        print("--------------------------------------------------")
        run_calibrated_audit(threshold_long=th)
