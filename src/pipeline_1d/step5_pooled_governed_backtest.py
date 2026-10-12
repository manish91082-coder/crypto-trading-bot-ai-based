import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    DATA_PROCESSED_DIR,
    MODELS_1D_CANDIDATE_DIR,
    LOGS_DIR,
    SYMBOLS,
    INITIAL_CAPITAL,
    BINANCE_TAKER_FEE,
    FEATURE_COLS,
    MACRO_BTC_EMA_PERIOD,
    TP_ATR_MULT,
    SL_ATR_MULT,
    BE_ATR_MULT,
    PARTIAL_TP_PCT,
    RUNNER_PCT,
    RUNNER_TRAILING_ATR,
    RUNNER_SL_LOCK_ATR,
    MAX_INACTIVITY_DAYS
)
from risk_governor import RiskGovernor
from strategy_signals import should_enter_spot_long

def load_data_and_predict(threshold_long: float, threshold_short: float):
    """
    Loads processed features, applies the pooled XGBoost models, and generates clean signals.
    """
    long_model_path = MODELS_1D_CANDIDATE_DIR / "Pooled_1d_XGB_Long.pkl"
    short_model_path = MODELS_1D_CANDIDATE_DIR / "Pooled_1d_XGB_Short.pkl"
    
    if not long_model_path.exists() or not short_model_path.exists():
        raise FileNotFoundError("Research candidate models not found in models/1d_pooled_candidate/. Run Step 4 research candidate training first.")
        
    long_model = joblib.load(long_model_path)
    short_model = joblib.load(short_model_path)
    
    dfs = []
    score_diagnostics = []
    prices_ohlc = {s: {} for s in SYMBOLS}
    
    for sym in SYMBOLS:
        feat_path = DATA_PROCESSED_DIR / f"{sym}_1d_7d_Features.csv"
        if not feat_path.exists():
            raise FileNotFoundError(f"Feature file not found: {feat_path}")
            
        df = pd.read_csv(feat_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        # Populate OHLC price lookups for fast execution
        for _, row in df.iterrows():
            t = row['timestamp']
            prices_ohlc[sym][t] = {
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'atr': row['ATR_14']
            }
            
        clean_df = df.dropna(subset=FEATURE_COLS).copy()
        if clean_df.empty:
            raise RuntimeError(f"{sym}: no rows remain after feature warm-up/NaN filtering")
        p_long = long_model.predict_proba(clean_df[FEATURE_COLS])[:, 1]
        p_short = short_model.predict_proba(clean_df[FEATURE_COLS])[:, 1]
        if not np.isfinite(p_long).all() or not np.isfinite(p_short).all():
            raise RuntimeError(f"{sym}: model emitted non-finite probabilities")

        diagnostic = {
            'Symbol': sym,
            'Rows_With_Valid_Features': int(len(clean_df)),
        }
        for side, values in (('Long', p_long), ('Short', p_short)):
            diagnostic[f'{side}_Prob_Min'] = float(np.min(values))
            diagnostic[f'{side}_Prob_Median'] = float(np.median(values))
            diagnostic[f'{side}_Prob_P90'] = float(np.quantile(values, 0.90))
            diagnostic[f'{side}_Prob_Max'] = float(np.max(values))
            for threshold in (0.42, 0.44, 0.46, 0.52, 0.55):
                diagnostic[f'{side}_Count_GE_{int(round(threshold*100)):02d}'] = int((values >= threshold).sum())
        score_diagnostics.append(diagnostic)

        clean_df['p_long'] = p_long
        clean_df['p_short'] = p_short
        clean_df['Symbol'] = sym
        dfs.append(clean_df)
        
    diagnostics_df = pd.DataFrame(score_diagnostics)
    if len(diagnostics_df) != len(SYMBOLS):
        raise RuntimeError(f"Expected probability diagnostics for {len(SYMBOLS)} symbols; got {len(diagnostics_df)}")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    diagnostics_path = LOGS_DIR / "phase5_model_probability_diagnostics.csv"
    diagnostics_df.to_csv(diagnostics_path, index=False)
    print(f"[EVIDENCE] Saved model probability diagnostics to {diagnostics_path.name}")
    for side in ("Long", "Short"):
        count_columns = [f"{side}_Count_GE_{int(round(threshold*100)):02d}" for threshold in (0.42, 0.44, 0.46, 0.52, 0.55)]
        print(f"[SCORE DIAGNOSTIC] {side}: max probability across symbols={diagnostics_df[f'{side}_Prob_Max'].max():.4f}; counts >= 0.42/0.44/0.46/0.52/0.55={ [int(diagnostics_df[col].sum()) for col in count_columns] }")

    master_df = pd.concat(dfs, ignore_index=True)
    master_df.sort_values('timestamp', inplace=True)
    master_df.reset_index(drop=True, inplace=True)
    
    return master_df, prices_ohlc

def run_simulation(
    master_df: pd.DataFrame,
    prices_ohlc: dict,
    mode: str = 'futures', # 'spot' or 'futures'
    threshold_long: float = 0.44,
    threshold_short: float = 0.44,
    max_concurrent: int = 3
):
    """
    Executes Institutional Quant Simulation with Active Risk Governor.
    Modes:
      - 'spot': Long-Only, strictly Total Notional <= Capital (No margin, No shorting).
      - 'futures': Long & Short, sized by Risk Governor with leverage cap.
    """
    unique_timestamps = sorted(master_df['timestamp'].unique())
    
    governor = RiskGovernor(
        initial_capital=INITIAL_CAPITAL,
        base_risk_pct=0.05,
        max_concurrent_trades=max_concurrent,
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
    
    # Pre-map timestamp index for next open lookup
    time_to_idx = {t: i for i, t in enumerate(unique_timestamps)}
    
    # Pre-calculate Bitcoin 20-period EMA for Macro Trend Filter (Law #9)
    btc_closes = {t: prices_ohlc['BTCUSDT'][t]['close'] for t in prices_ohlc['BTCUSDT'] if t in prices_ohlc['BTCUSDT']}
    df_btc = pd.DataFrame(list(btc_closes.items()), columns=['timestamp', 'close']).sort_values('timestamp')
    df_btc['ema20'] = df_btc['close'].ewm(span=20, adjust=False).mean()
    btc_bullish = dict(zip(df_btc['timestamp'], df_btc['close'] >= df_btc['ema20']))
    
    for t in unique_timestamps:
        curr_idx = time_to_idx[t]
        
        # -------------------------------------------------------------
        # STEP 1: CHECK EXITS ON OPEN TRADES (CONSERVATIVE INTRABAR)
        # -------------------------------------------------------------
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
            
            # 1.1 Stop Loss Check (Always checked FIRST before time exit, fixing Mistake 4.5)
            if trade['direction'] == 'Long':
                if l <= trade['sl']:
                    exit_price = trade['sl']
                    closed = True
                    exit_reason = 'Trailing Stop' if trade['secured'] else 'Stop Loss'
                else:
                    # Partial TP (+3.0x ATR): Bank 75% profit, leave 25% Runner
                    if not trade['secured'] and h >= trade['entry_price'] + 3.0 * atr:
                        tp_price = trade['entry_price'] + 3.0 * atr
                        part_units = trade['position_size'] * 0.75
                        part_proceeds = tp_price * part_units
                        part_fee = part_proceeds * BINANCE_TAKER_FEE
                        net_part_proceeds = part_proceeds - part_fee
                        part_cost = part_units * trade['entry_price']
                        part_pnl = net_part_proceeds - part_cost
                        
                        if mode == 'spot':
                            current_cash += net_part_proceeds
                            trade['allocated_capital'] -= part_cost
                        else:
                            current_cash += part_pnl
                            
                        trade['realized_pnl'] += part_pnl
                        trade['position_size'] -= part_units
                        trade['risk_amount'] *= 0.25
                        trade['secured'] = True
                        
                        # Raise SL to Entry + 1.0x ATR for 25% Runner
                        trade['sl'] = max(trade['sl'], trade['entry_price'] + 1.0 * atr)
                        
                        # Conservative Intrabar check: Did Low in same bar hit new SL?
                        if l <= trade['sl']:
                            exit_price = trade['sl']
                            closed = True
                            exit_reason = 'Trailing Stop'
                            
                    # Trailing Stop update for Runner (Rides with trend until reversal!)
                    if trade['secured'] and not closed:
                        trade['sl'] = max(trade['sl'], h - 2.0 * atr)
                        
                    # Breakeven SL (+1.5x ATR)
                    if not trade['secured'] and not closed and h >= trade['entry_price'] + 1.5 * atr:
                        trade['sl'] = max(trade['sl'], trade['entry_price'])
                        
            else: # Short trade
                if h >= trade['sl']:
                    exit_price = trade['sl']
                    closed = True
                    exit_reason = 'Trailing Stop' if trade['secured'] else 'Stop Loss'
                else:
                    # Check Partial TP (-3.0x ATR): Bank 75% profit, leave 25% Runner
                    if not trade['secured'] and l <= trade['entry_price'] - 3.0 * atr:
                        tp_price = trade['entry_price'] - 3.0 * atr
                        part_units = trade['position_size'] * 0.75
                        part_fee = tp_price * part_units * BINANCE_TAKER_FEE
                        part_pnl = (trade['entry_price'] - tp_price) * part_units - part_fee
                        
                        current_cash += part_pnl
                        trade['realized_pnl'] += part_pnl
                        trade['position_size'] -= part_units
                        trade['risk_amount'] *= 0.25
                        trade['secured'] = True
                        
                        # Lower SL to Entry - 1.0x ATR for Runner
                        trade['sl'] = min(trade['sl'], trade['entry_price'] - 1.0 * atr)
                        
                        # Conservative Intrabar check: Did High in same bar hit new SL?
                        if h >= trade['sl']:
                            exit_price = trade['sl']
                            closed = True
                            exit_reason = 'Trailing Stop'
                            
                    # Trailing Stop update for Runner
                    if trade['secured'] and not closed:
                        trade['sl'] = min(trade['sl'], l + 2.0 * atr)
                        
                    # Breakeven SL (-1.5x ATR)
                    if not trade['secured'] and not closed and l <= trade['entry_price'] - 1.5 * atr:
                        trade['sl'] = min(trade['sl'], trade['entry_price'])
                        
            # 1.2 Pure Event-Driven Resolution (Law #6: Zero Calendar Day Kills):
            # Trades run as long as price does not hit Stop Loss or Trailing Stop.
            # No arbitrary calendar timeout is permitted.
                
            # Finalize closed trade
            if closed:
                if trade['direction'] == 'Long':
                    exit_proceeds = exit_price * trade['position_size']
                    exit_fee = exit_proceeds * BINANCE_TAKER_FEE
                    net_exit_proceeds = exit_proceeds - exit_fee
                    cost = trade['position_size'] * trade['entry_price']
                    net_closing_pnl = net_exit_proceeds - cost
                    if mode == 'spot':
                        current_cash += net_exit_proceeds
                    else:
                        current_cash += net_closing_pnl
                else: # Short
                    pnl = (trade['entry_price'] - exit_price) * trade['position_size']
                    exit_fee = exit_price * trade['position_size'] * BINANCE_TAKER_FEE
                    net_closing_pnl = pnl - exit_fee
                    current_cash += net_closing_pnl
                    
                total_trade_pnl = net_closing_pnl - trade['entry_fee']
                trade['realized_pnl'] += total_trade_pnl
                trade['exit_time'] = t
                trade['exit_price'] = exit_price
                trade['exit_reason'] = exit_reason
                trade['days_held'] = days_held
                
                governor.update_capital(current_cash)
                closed_trades.append(trade)
                open_trades.remove(trade)
                
        # -------------------------------------------------------------
        # STEP 2: CHECK CANDIDATE ENTRIES FOR TOMORROW (T+1 OPEN)
        # -------------------------------------------------------------
        if curr_idx + 1 < len(unique_timestamps):
            next_t = unique_timestamps[curr_idx + 1]
            day_signals = master_df[master_df['timestamp'] == t]
            
            candidates = []
            for _, row in day_signals.iterrows():
                sym = row['Symbol']
                # Skip if already holding a position in this asset
                if any(tr['symbol'] == sym for tr in open_trades):
                    continue
                if next_t not in prices_ohlc[sym]:
                    continue
                    
                p_l = row['p_long']
                p_s = row['p_short']
                
                # Spot mode: a hard configured probability floor applies in every regime.
                if mode == 'spot':
                    is_btc_bull = btc_bullish.get(t, False)
                    can_enter, _entry_reason = should_enter_spot_long(
                        probability=p_l,
                        threshold=threshold_long,
                        btc_bullish=is_btc_bull,
                        relative_momentum=row.get('Rel_Mom_vs_BTC', np.nan),
                        pullback_depth=row.get('Pullback_Depth', np.nan),
                        stop_distance_ratio=row.get('SL_Dist_Ratio', np.nan),
                        volume_accumulation_ratio=row.get('Vol_Accum_Ratio', np.nan),
                    )

                    if can_enter:
                        candidates.append({
                            'symbol': sym,
                            'direction': 'Long',
                            'confidence': p_l,
                            'atr': row['ATR_14'],
                            'vol_accum_ratio': row.get('Vol_Accum_Ratio', 1.0),
                            'entry_time': next_t,
                            'entry_price': prices_ohlc[sym][next_t]['open']
                        })
                else: # Futures mode: Long or Short
                    if p_l >= threshold_long and p_l >= p_s:
                        candidates.append({
                            'symbol': sym,
                            'direction': 'Long',
                            'confidence': p_l,
                            'atr': row['ATR_14'],
                            'vol_accum_ratio': row.get('Vol_Accum_Ratio', 1.0),
                            'entry_time': next_t,
                            'entry_price': prices_ohlc[sym][next_t]['open']
                        })
                    elif p_s >= threshold_short and p_s > p_l:
                        candidates.append({
                            'symbol': sym,
                            'direction': 'Short',
                            'confidence': p_s,
                            'atr': row['ATR_14'],
                            'vol_accum_ratio': row.get('Vol_Accum_Ratio', 1.0),
                            'entry_time': next_t,
                            'entry_price': prices_ohlc[sym][next_t]['open']
                        })
                        
            # Sort candidates by confidence descending
            candidates.sort(key=lambda x: x['confidence'], reverse=True)
            
            for c in candidates:
                sl_distance = 1.5 * c['atr']
                if c['direction'] == 'Long':
                    sl = c['entry_price'] - sl_distance
                else:
                    sl = c['entry_price'] + sl_distance
                    
                sl_dist_pct = (sl_distance / c['entry_price']) * 100.0
                conf = c['confidence']
                v_ratio = c.get('vol_accum_ratio', 1.0)

                # Calibrated setup quality grading
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

                # Evaluate via Risk Governor
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
                    
                position_size = decision.position_size
                risk_amount = decision.risk_amount
                notional = position_size * c['entry_price']
                allocated_cap = 0.0
                
                # Spot Constraint Enforcement (Law #7: Total Notional <= Capital)
                if mode == 'spot':
                    available_cap = current_cash / max(1, (max_concurrent - len(open_trades)))
                    if notional > available_cap:
                        # Cap position size so notional does not exceed available cash
                        position_size = available_cap / c['entry_price']
                        notional = available_cap
                        risk_amount = position_size * sl_distance
                    if current_cash < notional:
                        continue # Cannot afford trade without borrowing
                    current_cash -= notional
                    allocated_cap = notional
                else:
                    # Futures mode leverage cap: total notional exposure <= 3.0x capital
                    current_notional = sum(tr['position_size'] * tr['entry_price'] for tr in open_trades)
                    if (current_notional + notional) > 3.0 * current_cash:
                        continue
                        
                # Deduct Binance Taker Fee on Entry
                entry_fee = notional * BINANCE_TAKER_FEE
                current_cash -= entry_fee
                governor.update_capital(current_cash)
                
                open_trades.append({
                    'symbol': c['symbol'],
                    'direction': c['direction'],
                    'confidence': c['confidence'],
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
                
        # -------------------------------------------------------------
        # STEP 3: MARK-TO-MARKET DAILY EQUITY & DRAWDOWN (Mistake 4.6 fix)
        # -------------------------------------------------------------
        floating_pnl = 0.0
        open_allocated = 0.0
        for tr in open_trades:
            sym = tr['symbol']
            curr_close = prices_ohlc[sym][t]['close']
            if tr['direction'] == 'Long':
                floating_pnl += (curr_close - tr['entry_price']) * tr['position_size']
            else:
                floating_pnl += (tr['entry_price'] - curr_close) * tr['position_size']
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
            'open_allocated_capital': open_allocated,
            'floating_pnl': floating_pnl,
            'mtm_equity': mtm_equity,
            'drawdown': mtm_dd,
            'open_positions': len(open_trades)
        })
        
    df_daily = pd.DataFrame(daily_records)
    df_trades = pd.DataFrame(closed_trades)
    
    # Calculate performance metrics
    total_trades = len(df_trades)
    wins = df_trades[df_trades['realized_pnl'] > 0] if total_trades > 0 else pd.DataFrame()
    losses = df_trades[df_trades['realized_pnl'] <= 0] if total_trades > 0 else pd.DataFrame()
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    
    total_profit = wins['realized_pnl'].sum() if len(wins) > 0 else 0.0
    total_loss = abs(losses['realized_pnl'].sum()) if len(losses) > 0 else 0.0
    profit_factor = (total_profit / total_loss) if total_loss > 0 else (np.inf if total_profit > 0 else 0.0)
    
    final_equity = df_daily['mtm_equity'].iloc[-1] if len(df_daily) > 0 else INITIAL_CAPITAL
    total_return_pct = ((final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100.0
    
    # Annualized CAGR
    n_days = (unique_timestamps[-1] - unique_timestamps[0]).days if len(unique_timestamps) > 1 else 1
    n_years = max(0.1, n_days / 365.25)
    cagr = (((final_equity / INITIAL_CAPITAL) ** (1.0 / n_years)) - 1.0) * 100.0 if final_equity > 0 else -100.0
    
    # Daily Sharpe ratio
    df_daily['daily_ret'] = df_daily['mtm_equity'].pct_change().fillna(0.0)
    sharpe = (df_daily['daily_ret'].mean() / df_daily['daily_ret'].std() * np.sqrt(365)) if df_daily['daily_ret'].std() > 0 else 0.0
    
    # Exit breakdown
    exit_counts = df_trades['exit_reason'].value_counts().to_dict() if total_trades > 0 else {}
    
    summary = {
        'mode': mode,
        'threshold_long': threshold_long,
        'threshold_short': threshold_short,
        'initial_capital': INITIAL_CAPITAL,
        'final_equity': final_equity,
        'total_return_pct': total_return_pct,
        'cagr': cagr,
        'max_mtm_drawdown_pct': max_mtm_drawdown * 100.0,
        'sharpe': sharpe,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'exit_counts': exit_counts,
        'n_days': n_days
    }
    
    return summary, df_trades, df_daily

def main():
    print("==========================================================================")
    print("PHASE 5: ZERO-TRUST POOLED GOVERNED SYSTEM SIMULATION (10 COINS)")
    print("Research Period: 2021-10-21 to 2024-12-31 | Pre-Flight Data Certified")
    print("Models: Low-Capacity Pooled XGBoost (Depth 2, L2=5.0) | Active Risk Governor")
    print("==========================================================================")
    
    master_df, prices_ohlc = load_data_and_predict(threshold_long=0.44, threshold_short=0.44)
    print(f"[*] Loaded 10 Universal Coins. Total Evaluation Daily Slices: {len(master_df['timestamp'].unique())} days")
    
    # Evaluate across Modes & Thresholds
    results = []
    
    configs = [
        # Spot Mode: Long-Only, Notional <= Capital
        ('spot', 0.42, 0.42, 'Spot Realism (Threshold 0.42 - Active Swings)'),
        ('spot', 0.44, 0.44, 'Spot Realism (Threshold 0.44 - High Edge)'),
        ('spot', 0.46, 0.46, 'Spot Realism (Threshold 0.46 - Ultra Conviction)'),
        # Futures Mode: Long & Short, Leverage Capped
        ('futures', 0.42, 0.42, 'Futures Governed (Threshold 0.42 - Active Swings)'),
        ('futures', 0.44, 0.44, 'Futures Governed (Threshold 0.44 - High Edge)'),
        ('futures', 0.46, 0.46, 'Futures Governed (Threshold 0.46 - Ultra Conviction)'),
    ]
    
    best_spot_trades = None
    best_futures_trades = None
    best_spot_daily = None
    best_futures_daily = None
    
    for mode, th_l, th_s, desc in configs:
        summary, df_trades, df_daily = run_simulation(
            master_df, prices_ohlc, mode=mode, threshold_long=th_l, threshold_short=th_s
        )
        summary['description'] = desc
        results.append(summary)
        
        print(f"\n>>> CONFIG: {desc}")
        print(f"    Trades: {summary['total_trades']:>3} | Win Rate: {summary['win_rate']:>5.1f}% | PF: {summary['profit_factor']:>5.2f}")
        print(f"    Final Capital: ${summary['final_equity']:>8.2f} ({summary['total_return_pct']:>+6.1f}%) | CAGR: {summary['cagr']:>+6.1f}%")
        print(f"    Max Mark-to-Market DD: {summary['max_mtm_drawdown_pct']:>5.1f}% | Sharpe: {summary['sharpe']:>5.2f}")
        print(f"    Exits: {summary['exit_counts']}")
        
        if mode == 'spot' and th_l == 0.44:
            best_spot_trades = df_trades
            best_spot_daily = df_daily
        if mode == 'futures' and th_l == 0.44:
            best_futures_trades = df_trades
            best_futures_daily = df_daily
            
    # Persist actual metrics and selected 0.44 ledgers with truthful names.
    results_frame = pd.DataFrame(results)
    if not results_frame.empty:
        results_path = LOGS_DIR / "phase5_pooled_research_metrics.csv"
        results_frame.to_csv(results_path, index=False)
        print(f"\n[+] Saved all research configuration metrics to {results_path.name}")

    if best_spot_trades is not None:
        p_spot = LOGS_DIR / "phase5_pooled_spot_trades_044.csv"
        best_spot_trades.to_csv(p_spot, index=False)
        print(f"[+] Saved threshold-0.44 spot trade ledger to {p_spot.name}")

    if best_futures_trades is not None:
        p_fut = LOGS_DIR / "phase5_pooled_futures_trades_044.csv"
        best_futures_trades.to_csv(p_fut, index=False)
        print(f"[+] Saved threshold-0.44 futures trade ledger to {p_fut.name}")

    if best_spot_daily is not None:
        p_spot_daily = LOGS_DIR / "phase5_pooled_spot_daily_equity_044.csv"
        best_spot_daily.to_csv(p_spot_daily, index=False)
        print(f"[+] Saved spot MTM equity ledger to {p_spot_daily.name}")

    if best_futures_daily is not None:
        p_daily = LOGS_DIR / "phase5_pooled_futures_daily_equity_044.csv"
        best_futures_daily.to_csv(p_daily, index=False)
        print(f"[+] Saved futures MTM equity ledger to {p_daily.name}")

if __name__ == '__main__':
    main()
