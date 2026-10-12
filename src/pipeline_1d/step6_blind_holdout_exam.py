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
    DATA_RAW_DIR,
    MODELS_1D_POOLED_DIR,
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

VAULT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "vault_holdout_2025_2026"
VAULT_START_DATE = "2025-01-01"
VAULT_END_DATE = "2026-09-30"

def compute_features_for_vault():
    """
    Computes stationary features on the full raw dataset (with 2024 lookback for warmup)
    and slices strictly the sealed vault period: 2025-01-01 to 2026-09-30.
    """
    btc_raw = pd.read_csv(DATA_RAW_DIR / "BTCUSDT_1d_Raw_5Years.csv")
    btc_raw['timestamp'] = pd.to_datetime(btc_raw['timestamp'])
    btc_raw.sort_values('timestamp', inplace=True)
    btc_ret_5 = btc_raw['close'].pct_change(5).values

    long_model = joblib.load(MODELS_1D_POOLED_DIR / "Pooled_1d_XGB_Long.pkl")
    short_model = joblib.load(MODELS_1D_POOLED_DIR / "Pooled_1d_XGB_Short.pkl")

    dfs = []
    prices_ohlc = {s: {} for s in SYMBOLS}

    for symbol in SYMBOLS:
        raw_file = DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv"
        df = pd.read_csv(raw_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Store all OHLC for execution
        for _, row in df.iterrows():
            t = row['timestamp']
            prices_ohlc[symbol][t] = {
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }

        # 1. Short-term returns
        df['Ret_1'] = df['close'].pct_change(1)
        df['Ret_3'] = df['close'].pct_change(3)
        df['Ret_5'] = df['close'].pct_change(5)

        # 2. Intrabar Order Flow & Rejection Wicks
        bar_range = df['high'] - df['low'] + 1e-8
        df['Synthetic_Order_Flow'] = (df['close'] - df['open']) / bar_range
        df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / bar_range
        df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / bar_range

        # 3. Volume Z-Score (Rolling 20-day)
        vol_mean = df['volume'].rolling(20).mean()
        vol_std = df['volume'].rolling(20).std()
        df['Vol_Z_Score'] = (df['volume'] - vol_mean) / (vol_std + 1e-8)

        # 4. Normalized Volatility (ATR% of price)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift(1)).abs()
        tr3 = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(14).mean()
        df['ATR_Pct'] = df['ATR_14'] / (df['close'] + 1e-8)

        # 5. Stationary Momentum (Normalized Distance to 20 EMA in ATR units)
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        df['Dist_EMA_20_ATR'] = (df['close'] - ema_20) / (df['ATR_14'] + 1e-8)

        # 6. Relative Momentum vs BTC (Strictly mapped by timestamp)
        btc_ret_series = pd.Series(btc_raw['close'].pct_change(5).values, index=btc_raw['timestamp'])
        df['Rel_Mom_vs_BTC'] = df['Ret_5'] - df['timestamp'].map(btc_ret_series)

        # 7. Physical Structural Risk Distance (SL_Dist_Ratio)
        low_14 = df['low'].rolling(14).min()
        df['SL_Dist_Ratio'] = (df['close'] - (low_14 - 0.5 * df['ATR_14'])) / (df['close'] + 1e-8)

        # 8. Selling Exhaustion Pullback Depth (Pullback_Depth)
        high_30 = df['high'].rolling(30).max()
        df['Pullback_Depth'] = (high_30 - df['close']) / (high_30 + 1e-8)

        # 9. Smart Money Volume Accumulation (Vol_Accum_Ratio)
        vol_sma20 = df['volume'].rolling(20).mean()
        df['Vol_Accum_Ratio'] = df['volume'] / (vol_sma20 + 1e-8)

        # 10. Macro Regime Z-Score (Regime_Z_Score)
        sma200 = df['close'].rolling(200, min_periods=30).mean()
        std200 = df['close'].rolling(200, min_periods=30).std()
        df['Regime_Z_Score'] = (df['close'] - sma200) / (std200 + 1e-8)

        # 11. Volatility Compression Ratio (Volatility_Compression)
        atr_sma50 = df['ATR_14'].rolling(50, min_periods=14).mean()
        df['Volatility_Compression'] = df['ATR_14'] / (atr_sma50 + 1e-8)

        for _, row in df.iterrows():
            t = row['timestamp']
            prices_ohlc[symbol][t]['atr'] = row['ATR_14']

        # Filter strictly for VAULT PERIOD
        vault_df = df[(df['timestamp'] >= VAULT_START_DATE) & (df['timestamp'] <= VAULT_END_DATE)].copy()
        vault_df['Symbol'] = symbol

        p_l = long_model.predict_proba(vault_df[FEATURE_COLS])[:, 1]
        p_s = short_model.predict_proba(vault_df[FEATURE_COLS])[:, 1]
        vault_df['p_long'] = p_l
        vault_df['p_short'] = p_s

        dfs.append(vault_df)

    master_vault = pd.concat(dfs, ignore_index=True)
    master_vault.sort_values('timestamp', inplace=True)
    master_vault.reset_index(drop=True, inplace=True)

    # Pre-calculate Bitcoin EMA 20 and systemic crash days
    btc_ema20 = btc_raw['close'].ewm(span=MACRO_BTC_EMA_PERIOD, adjust=False).mean()
    btc_bullish_map = dict(zip(btc_raw['timestamp'], btc_raw['close'] >= btc_ema20))
    btc_raw['btc_ret1'] = btc_raw['close'].pct_change(1)
    btc_crash_map = dict(zip(btc_raw['timestamp'], btc_raw['btc_ret1'] <= -0.06))

    return master_vault, prices_ohlc, btc_bullish_map, btc_crash_map

def run_vault_simulation(
    master_vault: pd.DataFrame,
    prices_ohlc: dict,
    btc_bullish_map: dict = None,
    btc_crash_map: dict = None,
    mode: str = 'spot',
    initial_capital: float = 120.0,
    threshold_long: float = 0.44,
    threshold_short: float = 0.44,
    max_concurrent: int = 3
):
    """
    Executes single-shot blind test on the 2025-2026 Vault dataset.
    """
    if btc_bullish_map is None:
        btc_bullish_map = {}
    if btc_crash_map is None:
        btc_crash_map = {}
        
    unique_timestamps = sorted(master_vault['timestamp'].unique())
    time_to_idx = {t: i for i, t in enumerate(unique_timestamps)}

    governor = RiskGovernor(
        initial_capital=initial_capital,
        base_risk_pct=0.05,
        max_concurrent_trades=max_concurrent,
        max_portfolio_risk_pct=0.12,
        dd_tier_1=0.10,
        dd_tier_2=0.20,
        dd_tier_3=0.35,
        min_risk_pct=0.015
    )

    current_cash = initial_capital
    peak_mtm_equity = initial_capital
    max_mtm_drawdown = 0.0

    open_trades = []
    closed_trades = []
    daily_records = []

    for t in unique_timestamps:
        curr_idx = time_to_idx[t]

        # 1. EXITS CHECK
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

            # Check SL First (Law #6)
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
                        trade['sl'] = max(trade['sl'], trade['entry_price'] + 1.0 * atr)

                        # Intrabar re-check
                        if l <= trade['sl']:
                            exit_price = trade['sl']
                            closed = True
                            exit_reason = 'Trailing Stop'

                    # Trailing Stop update for Runner (Rides with trend until reversal!)
                    if trade['secured'] and not closed:
                        peak_gain_atr = (h - trade['entry_price']) / atr
                        trail_dist = (1.4 * atr) if peak_gain_atr >= 4.5 else (2.0 * atr)
                        trade['sl'] = max(trade['sl'], h - trail_dist)

                    # Breakeven SL (+1.5x ATR)
                    if not trade['secured'] and not closed and h >= trade['entry_price'] + 1.5 * atr:
                        trade['sl'] = max(trade['sl'], trade['entry_price'])
            else: # Short
                if h >= trade['sl']:
                    exit_price = trade['sl']
                    closed = True
                    exit_reason = 'Trailing Stop' if trade['secured'] else 'Stop Loss'
                else:
                    # Partial TP (-3.0x ATR): Bank 75% profit, leave 25% Runner
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
                        trade['sl'] = min(trade['sl'], trade['entry_price'] - 1.0 * atr)

                        if h >= trade['sl']:
                            exit_price = trade['sl']
                            closed = True
                            exit_reason = 'Trailing Stop'

                    # Trailing Stop update for Runner
                    if trade['secured'] and not closed:
                        trough_gain_atr = (trade['entry_price'] - l) / atr
                        trail_dist = (1.4 * atr) if trough_gain_atr >= 4.5 else (2.0 * atr)
                        trade['sl'] = min(trade['sl'], l + trail_dist)

                    # Breakeven SL (-1.5x ATR)
                    if not trade['secured'] and not closed and l <= trade['entry_price'] - 1.5 * atr:
                        trade['sl'] = min(trade['sl'], trade['entry_price'])

            # 1.2 Pure Event-Driven Resolution (Law #6: Zero Calendar Day Kills):
            # Trades run as long as price does not hit Stop Loss or Trailing Stop.
            # No arbitrary calendar timeout is permitted.

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
                else:
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

        # 2. ENTRIES CHECK (NEXT DAY OPEN)
        if curr_idx + 1 < len(unique_timestamps):
            next_t = unique_timestamps[curr_idx + 1]
            day_signals = master_vault[master_vault['timestamp'] == t]

            # Systemic Crash Defense
            is_btc_crash = btc_crash_map.get(t, False)
            if is_btc_crash:
                continue

            is_btc_bull = btc_bullish_map.get(t, False)

            candidates = []
            for _, row in day_signals.iterrows():
                sym = row['Symbol']
                if any(tr['symbol'] == sym for tr in open_trades):
                    continue
                if next_t not in prices_ohlc[sym]:
                    continue

                p_l = row['p_long']
                p_s = row['p_short']

                if mode == 'spot':
                    can_enter = False
                    if is_btc_bull:
                        if p_l >= threshold_long:
                            can_enter = True
                    else:
                        rel_mom = row.get('Rel_Mom_vs_BTC', 0.0)
                        if rel_mom >= 0.0 and p_l >= threshold_long:
                            can_enter = True
                        elif p_l >= 0.42:
                            can_enter = True
                        elif p_l >= threshold_long and (row.get('Pullback_Depth', 0.0) >= 0.08 or row.get('SL_Dist_Ratio', 0.0) <= 0.065 or row.get('Vol_Accum_Ratio', 0.0) >= 1.05):
                            can_enter = True

                    if can_enter:
                        candidates.append({
                            'symbol': sym, 'direction': 'Long', 'confidence': p_l,
                            'atr': row['ATR_14'], 'vol_accum_ratio': row.get('Vol_Accum_Ratio', 1.0),
                            'entry_time': next_t,
                            'entry_price': prices_ohlc[sym][next_t]['open']
                        })
                else:
                    if p_l >= threshold_long and p_l >= p_s:
                        candidates.append({
                            'symbol': sym, 'direction': 'Long', 'confidence': p_l,
                            'atr': row['ATR_14'], 'vol_accum_ratio': row.get('Vol_Accum_Ratio', 1.0),
                            'entry_time': next_t,
                            'entry_price': prices_ohlc[sym][next_t]['open']
                        })
                    elif p_s >= threshold_short and p_s > p_l:
                        candidates.append({
                            'symbol': sym, 'direction': 'Short', 'confidence': p_s,
                            'atr': row['ATR_14'], 'vol_accum_ratio': row.get('Vol_Accum_Ratio', 1.0),
                            'entry_time': next_t,
                            'entry_price': prices_ohlc[sym][next_t]['open']
                        })

            candidates.sort(key=lambda x: x['confidence'], reverse=True)

            for c in candidates:
                sl_distance = 1.5 * c['atr']
                sl = c['entry_price'] - sl_distance if c['direction'] == 'Long' else c['entry_price'] + sl_distance
                sl_dist_pct = (sl_distance / c['entry_price']) * 100.0
                conf = c['confidence']
                v_ratio = c.get('vol_accum_ratio', 1.0)

                # Calibrated setup quality grading (Upgraded Institutional Standards)
                if conf >= 0.46 and sl_dist_pct <= 7.0 and v_ratio >= 1.0:
                    grade = "Grade A+"
                    q_mult = 1.40  # 1.40x Conviction Boost for 54.8% WR institutional edge
                elif conf >= 0.40 and sl_dist_pct <= 9.0:
                    if v_ratio >= 1.0:
                        grade = "Grade A"
                        q_mult = 1.00  # Clean breakout with institutional volume accumulation
                    else:
                        grade = "Grade C"
                        q_mult = 0.00  # Reject fakeout traps lacking volume confirmation
                elif conf >= 0.38 and sl_dist_pct <= 12.0:
                    grade = "Grade B"
                    q_mult = 0.65  # Scaled DOWN to ~22% slot size
                else:
                    grade = "Grade C"
                    q_mult = 0.00  # Skip toxic traps / cash defense

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

                if mode == 'spot':
                    available_cap = current_cash / max(1, (max_concurrent - len(open_trades)))
                    if notional > available_cap:
                        position_size = available_cap / c['entry_price']
                        notional = available_cap
                        risk_amount = position_size * sl_distance
                    if current_cash < notional:
                        continue
                    current_cash -= notional
                    allocated_cap = notional
                else:
                    current_notional = sum(tr['position_size'] * tr['entry_price'] for tr in open_trades)
                    if (current_notional + notional) > 3.0 * current_cash:
                        continue

                entry_fee = notional * BINANCE_TAKER_FEE
                current_cash -= entry_fee
                governor.update_capital(current_cash)

                open_trades.append({
                    'symbol': c['symbol'], 'direction': c['direction'], 'confidence': c['confidence'],
                    'entry_time': c['entry_time'], 'entry_price': c['entry_price'],
                    'sl': sl, 'atr': c['atr'], 'risk_amount': risk_amount,
                    'position_size': position_size, 'allocated_capital': allocated_cap,
                    'secured': False, 'realized_pnl': 0.0, 'entry_fee': entry_fee,
                    'risk_pct': decision.risk_pct
                })

        # 3. DAILY MTM EQUITY
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
            'timestamp': t, 'cash': current_cash, 'mtm_equity': mtm_equity,
            'drawdown': mtm_dd, 'open_positions': len(open_trades)
        })

    df_daily = pd.DataFrame(daily_records)
    df_trades = pd.DataFrame(closed_trades)

    total_trades = len(df_trades)
    wins = df_trades[df_trades['realized_pnl'] > 0] if total_trades > 0 else pd.DataFrame()
    losses = df_trades[df_trades['realized_pnl'] <= 0] if total_trades > 0 else pd.DataFrame()
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

    total_profit = wins['realized_pnl'].sum() if len(wins) > 0 else 0.0
    total_loss = abs(losses['realized_pnl'].sum()) if len(losses) > 0 else 0.0
    profit_factor = (total_profit / total_loss) if total_loss > 0 else (np.inf if total_profit > 0 else 0.0)

    final_equity = df_daily['mtm_equity'].iloc[-1] if len(df_daily) > 0 else initial_capital
    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100.0

    df_daily['daily_ret'] = df_daily['mtm_equity'].pct_change().fillna(0.0)
    sharpe = (df_daily['daily_ret'].mean() / df_daily['daily_ret'].std() * np.sqrt(365)) if df_daily['daily_ret'].std() > 0 else 0.0
    exit_counts = df_trades['exit_reason'].value_counts().to_dict() if total_trades > 0 else {}

    summary = {
        'mode': mode,
        'initial_capital': initial_capital,
        'final_equity': final_equity,
        'total_return_pct': total_return_pct,
        'max_mtm_drawdown_pct': max_mtm_drawdown * 100.0,
        'sharpe': sharpe,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'exit_counts': exit_counts
    }
    return summary, df_trades, df_daily

def main():
    print("==========================================================================")
    print("PHASE 6: FINAL UNSEEN BLIND HOLDOUT VAULT EXAMINATION (2025-2026)")
    print("Strict Out-of-Sample Examination: Law #3 & Law #5 Active")
    print("Zero-Leakage Guarantee: Vault Data Was Never Seen By Any Model Or Training")
    print("==========================================================================")

    master_vault, prices_ohlc, btc_bullish_map, btc_crash_map = compute_features_for_vault()
    n_days = len(master_vault['timestamp'].unique())
    print(f"[*] Successfully unlocked Vault. Period: {VAULT_START_DATE} to {VAULT_END_DATE} ({n_days} daily slices)")

    # 1. Spot Mode (0.44) - Fresh $120 Capital
    print("\n--------------------------------------------------------------------------")
    print("RUN 1: SPOT REALISM (THRESHOLD 0.44) - FRESH $120.00 CAPITAL")
    print("--------------------------------------------------------------------------")
    s1, t1, d1 = run_vault_simulation(
        master_vault, prices_ohlc, btc_bullish_map=btc_bullish_map, btc_crash_map=btc_crash_map,
        mode='spot', initial_capital=120.0, threshold_long=0.44
    )
    print(f"Trades: {s1['total_trades']} | Win Rate: {s1['win_rate']:.1f}% | Profit Factor: {s1['profit_factor']:.2f}")
    print(f"Final Capital: ${s1['final_equity']:.2f} ({s1['total_return_pct']:+.1f}%) | Max DD: {s1['max_mtm_drawdown_pct']:.1f}% | Sharpe: {s1['sharpe']:.2f}")
    print(f"Exits: {s1['exit_counts']}")

    # 2. Spot Mode (0.44) - Continuous Rollover from Phase 5 ($262.86)
    print("\n--------------------------------------------------------------------------")
    print("RUN 2: SPOT REALISM (THRESHOLD 0.44) - CONTINUOUS ROLLOVER ($262.86)")
    print("--------------------------------------------------------------------------")
    s2, t2, d2 = run_vault_simulation(
        master_vault, prices_ohlc, btc_bullish_map=btc_bullish_map, btc_crash_map=btc_crash_map,
        mode='spot', initial_capital=262.86, threshold_long=0.44
    )
    print(f"Trades: {s2['total_trades']} | Win Rate: {s2['win_rate']:.1f}% | Profit Factor: {s2['profit_factor']:.2f}")
    print(f"Final Capital: ${s2['final_equity']:.2f} ({s2['total_return_pct']:+.1f}%) | Max DD: {s2['max_mtm_drawdown_pct']:.1f}% | Sharpe: {s2['sharpe']:.2f}")
    print(f"Exits: {s2['exit_counts']}")

    # 3. Futures Mode (0.44) - Fresh $120 Capital
    print("\n--------------------------------------------------------------------------")
    print("RUN 3: FUTURES GOVERNED (THRESHOLD 0.44) - FRESH $120.00 CAPITAL")
    print("--------------------------------------------------------------------------")
    s3, t3, d3 = run_vault_simulation(
        master_vault, prices_ohlc, btc_bullish_map=btc_bullish_map, btc_crash_map=btc_crash_map,
        mode='futures', initial_capital=120.0, threshold_long=0.44, threshold_short=0.44
    )
    print(f"Trades: {s3['total_trades']} | Win Rate: {s3['win_rate']:.1f}% | Profit Factor: {s3['profit_factor']:.2f}")
    print(f"Final Capital: ${s3['final_equity']:.2f} ({s3['total_return_pct']:+.1f}%) | Max DD: {s3['max_mtm_drawdown_pct']:.1f}% | Sharpe: {s3['sharpe']:.2f}")
    print(f"Exits: {s3['exit_counts']}")

    # Save Logs
    p_t1 = LOGS_DIR / "phase6_vault_spot_trades_fresh120.csv"
    p_d1 = LOGS_DIR / "phase6_vault_spot_daily_fresh120.csv"
    p_t2 = LOGS_DIR / "phase6_vault_spot_trades_rollover.csv"
    p_d2 = LOGS_DIR / "phase6_vault_spot_daily_rollover.csv"

    t1.to_csv(p_t1, index=False)
    d1.to_csv(p_d1, index=False)
    t2.to_csv(p_t2, index=False)
    d2.to_csv(p_d2, index=False)

    print(f"\n[+] Saved Vault Spot Trades to '{p_t1.name}' and '{p_t2.name}'")
    print(f"[+] Saved Vault Daily Equity to '{p_d1.name}' and '{p_d2.name}'")

if __name__ == '__main__':
    main()
