import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
import time
import warnings
warnings.filterwarnings('ignore')

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    DATA_PROCESSED_DIR,
    MODELS_4H_POOLED_DIR,
    LOGS_DIR,
    SYMBOLS,
    BINANCE_TAKER_FEE
)
from risk_governor import RiskGovernor

# 4H QUANT MASTER EXECUTION RULES (LOCKED)
INITIAL_CAPITAL_4H = 10000.0   # $10,000 USDT Testnet Scale
TAKER_FEE_4H = BINANCE_TAKER_FEE  # 0.075% taker fee
SLIPPAGE_4H = 0.0005          # 0.05% institutional slippage per fill
TOTAL_FRICTION_4H = TAKER_FEE_4H + SLIPPAGE_4H  # 0.125% per execution

# 4H BARRIERS
TP_ATR_MULT_4H = 2.5          # +2.5x ATR TP
SL_ATR_MULT_4H = 1.8          # -1.8x ATR SL
BE_ATR_MULT_4H = 1.2          # Move SL to breakeven once price reaches +1.2x ATR
PARTIAL_TP_PCT_4H = 0.75      # Bank 75% profit at TP
RUNNER_PCT_4H = 0.25          # 25% Runner rides trend
RUNNER_TRAILING_ATR_4H = 1.5  # Dynamic trailing stop for runner
MAX_INACTIVITY_4H_CANDLES = 24  # 24 candles = 4 days timeout

FEATURE_COLS_4H = [
    'Ret_1', 'Ret_6', 'Ret_18', 'Synthetic_Order_Flow',
    'Upper_Wick_Ratio', 'Lower_Wick_Ratio', 'Vol_Z_Score',
    'ATR_Pct', 'Dist_EMA_50_ATR', 'Rel_Mom_vs_BTC',
    'SL_Dist_Ratio', 'Pullback_Depth', 'Vol_Accum_Ratio',
    'Regime_Z_Score', 'Volatility_Compression'
]

def load_data_and_models_4h():
    """Load trained 4H models and processed feature datasets for all 10 coins."""
    long_model_path = MODELS_4H_POOLED_DIR / "Pooled_4h_XGB_Long.pkl"
    short_model_path = MODELS_4H_POOLED_DIR / "Pooled_4h_XGB_Short.pkl"

    if not long_model_path.exists():
        raise FileNotFoundError(f"Model missing: {long_model_path}")

    long_model = joblib.load(long_model_path)
    short_model = joblib.load(short_model_path)

    dfs = []
    prices_ohlc = {s: {} for s in SYMBOLS}
    btc_bullish_map = {}
    btc_crash_map = {}

    # Load BTC first to build Macro 50-EMA & Crash Gates
    btc_path = DATA_PROCESSED_DIR / "BTCUSDT_4h_Processed_Features_Labels.csv"
    btc_df = pd.read_csv(btc_path)
    btc_df['timestamp'] = pd.to_datetime(btc_df['timestamp'])
    btc_df = btc_df.sort_values('timestamp').reset_index(drop=True)

    # 4H Macro Trend: Close >= 50-EMA
    btc_ema50 = btc_df['close'].ewm(span=50, adjust=False).mean()
    btc_bullish_map = dict(zip(btc_df['timestamp'], btc_df['close'] >= btc_ema50))

    # 4H Macro Crash Gate: 4H drop <= -4.0%
    btc_crash_map = dict(zip(btc_df['timestamp'], btc_df['Ret_1'] <= -0.04))

    for sym in SYMBOLS:
        p_path = DATA_PROCESSED_DIR / f"{sym}_4h_Processed_Features_Labels.csv"
        df = pd.read_csv(p_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        for _, row in df.iterrows():
            t = row['timestamp']
            prices_ohlc[sym][t] = {
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'atr': row['ATR_14']
            }

        clean_df = df.dropna(subset=FEATURE_COLS_4H).copy()
        clean_df['p_long'] = long_model.predict_proba(clean_df[FEATURE_COLS_4H])[:, 1]
        clean_df['p_short'] = short_model.predict_proba(clean_df[FEATURE_COLS_4H])[:, 1]
        clean_df['Symbol'] = sym
        dfs.append(clean_df)

    master_df = pd.concat(dfs, ignore_index=True)
    master_df = master_df.sort_values('timestamp').reset_index(drop=True)
    return master_df, prices_ohlc, btc_bullish_map, btc_crash_map


def run_4h_simulation(
    master_df: pd.DataFrame,
    prices_ohlc: dict,
    btc_bullish_map: dict,
    btc_crash_map: dict,
    mode: str = 'bi_directional',
    threshold_long: float = 0.48,
    threshold_short: float = 0.52,
    max_concurrent: int = 5,
    vol_accum_min: float = 0.75,
    sl_cap_long: float = 7.5,
    sl_cap_short: float = 6.5,
    start_date: str = None,
    end_date: str = None
):
    """
    Executes institutional 4H simulation with strict accounting:
    - 0.075% fee + 0.05% slippage on entry and exit.
    - Next bar open entry (zero lookahead).
    - 75/25 Runner architecture with dynamic trailing stop.
    - Bi-directional regime adaptation: Long in Bullish regimes, Short in Bearish regimes.
    - Macro 50-EMA trend & flash crash gating.
    - Zero cash balance discrepancy.
    """
    df_sim = master_df.copy()
    if start_date:
        df_sim = df_sim[df_sim['timestamp'] >= pd.to_datetime(start_date)]
    if end_date:
        df_sim = df_sim[df_sim['timestamp'] <= pd.to_datetime(end_date)]

    unique_timestamps = sorted(df_sim['timestamp'].unique())

    governor = RiskGovernor(
        initial_capital=INITIAL_CAPITAL_4H,
        base_risk_pct=0.02,             # 2.0% base risk per trade for 4H
        max_concurrent_trades=max_concurrent,
        max_portfolio_risk_pct=0.08,    # 8.0% max total portfolio risk
        dd_tier_1=0.06,
        dd_tier_2=0.12,
        dd_tier_3=0.25,
        min_risk_pct=0.008
    )

    current_cash = INITIAL_CAPITAL_4H
    peak_equity = INITIAL_CAPITAL_4H
    max_drawdown = 0.0

    open_trades = []
    closed_trades = []
    equity_curve = []

    for idx, t in enumerate(unique_timestamps):
        # 1. Update active trades on new 4H candle
        surviving_trades = []
        for trade in open_trades:
            sym = trade['symbol']
            bar = prices_ohlc[sym].get(t)
            if not bar:
                surviving_trades.append(trade)
                continue

            h, l = bar['high'], bar['low']
            direction = trade['direction']
            atr = trade['atr']
            entry_p = trade['entry_price']
            trade['bars_held'] += 1

            closed = False
            exit_reason = ""
            exit_price = 0.0

            if direction == 'Long':
                trade['peak_price'] = max(trade['peak_price'], h)

                # Step A: Initial SL or Breakeven Hit
                if l <= trade['sl']:
                    closed = True
                    exit_reason = "STOP_LOSS" if not trade['secured'] else "RUNNER_TRAIL_SL"
                    exit_price = min(trade['sl'], bar['open'])  # Real gap slippage

                # Step B: TP Target Hit (+2.5x ATR)
                if not closed and not trade['secured']:
                    if h >= trade['tp_target']:
                        secured_size = trade['position_size'] * PARTIAL_TP_PCT_4H
                        trade['remaining_size'] -= secured_size
                        trade['secured'] = True

                        fee_partial = secured_size * trade['tp_target'] * TOTAL_FRICTION_4H
                        pnl_partial = (trade['tp_target'] - entry_p) * secured_size - fee_partial
                        trade['realized_pnl'] += pnl_partial
                        current_cash += (secured_size * trade['tp_target'] - fee_partial)
                        trade['sl'] = entry_p + (0.5 * atr)

                # Step C: Dynamic Trailing Stop for 25% Runner
                if not closed and trade['secured']:
                    new_trail = trade['peak_price'] - (RUNNER_TRAILING_ATR_4H * atr)
                    if new_trail > trade['sl']:
                        trade['sl'] = new_trail

                # Step D: Breakeven advance before TP (+1.2x ATR gain)
                if not closed and not trade['secured']:
                    if h >= entry_p + (BE_ATR_MULT_4H * atr):
                        if trade['sl'] < entry_p:
                            trade['sl'] = entry_p

                # Step E: Inactivity Timeout (24 candles = 4 days)
                if not closed and not trade['secured'] and trade['bars_held'] >= MAX_INACTIVITY_4H_CANDLES:
                    closed = True
                    exit_reason = "TIMEOUT_INACTIVITY"
                    exit_price = bar['open']

                if closed:
                    rem_size = trade['remaining_size']
                    fee_exit = rem_size * exit_price * TOTAL_FRICTION_4H
                    pnl_exit = (exit_price - entry_p) * rem_size - fee_exit
                    trade['realized_pnl'] += pnl_exit
                    trade['exit_time'] = t
                    trade['exit_price'] = exit_price
                    trade['exit_reason'] = exit_reason
                    current_cash += (rem_size * exit_price - fee_exit)
                    closed_trades.append(trade)
                else:
                    surviving_trades.append(trade)

            else:  # Short Direction
                trade['peak_price'] = min(trade['peak_price'], l)

                # Step A: Initial SL Hit
                if h >= trade['sl']:
                    closed = True
                    exit_reason = "STOP_LOSS" if not trade['secured'] else "RUNNER_TRAIL_SL"
                    exit_price = max(trade['sl'], bar['open'])  # Real gap slippage

                # Step B: TP Target Hit (-2.5x ATR)
                if not closed and not trade['secured']:
                    if l <= trade['tp_target']:
                        secured_size = trade['position_size'] * PARTIAL_TP_PCT_4H
                        trade['remaining_size'] -= secured_size
                        trade['secured'] = True

                        fee_partial = secured_size * trade['tp_target'] * TOTAL_FRICTION_4H
                        pnl_partial = (entry_p - trade['tp_target']) * secured_size - fee_partial
                        trade['realized_pnl'] += pnl_partial
                        current_cash += (entry_p * secured_size + pnl_partial)
                        trade['sl'] = entry_p - (0.5 * atr)

                # Step C: Dynamic Trailing Stop for 25% Runner
                if not closed and trade['secured']:
                    new_trail = trade['peak_price'] + (RUNNER_TRAILING_ATR_4H * atr)
                    if new_trail < trade['sl']:
                        trade['sl'] = new_trail

                # Step D: Breakeven advance before TP (-1.2x ATR drop)
                if not closed and not trade['secured']:
                    if l <= entry_p - (BE_ATR_MULT_4H * atr):
                        if trade['sl'] > entry_p:
                            trade['sl'] = entry_p

                # Step E: Inactivity Timeout (24 candles = 4 days)
                if not closed and not trade['secured'] and trade['bars_held'] >= MAX_INACTIVITY_4H_CANDLES:
                    closed = True
                    exit_reason = "TIMEOUT_INACTIVITY"
                    exit_price = bar['open']

                if closed:
                    rem_size = trade['remaining_size']
                    fee_exit = rem_size * exit_price * TOTAL_FRICTION_4H
                    pnl_exit = (entry_p - exit_price) * rem_size - fee_exit
                    trade['realized_pnl'] += pnl_exit
                    trade['exit_time'] = t
                    trade['exit_price'] = exit_price
                    trade['exit_reason'] = exit_reason
                    current_cash += (rem_size * entry_p + (entry_p - exit_price) * rem_size - fee_exit)
                    closed_trades.append(trade)
                else:
                    surviving_trades.append(trade)

        open_trades = surviving_trades

        # 2. Mark-to-Market Equity calculation
        mtm_pos_val = 0.0
        for tr in open_trades:
            sym = tr['symbol']
            if sym in prices_ohlc and t in prices_ohlc[sym]:
                cp = prices_ohlc[sym][t]['close']
                if tr['direction'] == 'Long':
                    mtm_pos_val += tr['remaining_size'] * cp
                else:
                    mtm_pos_val += tr['remaining_size'] * tr['entry_price'] + tr['remaining_size'] * (tr['entry_price'] - cp)

        total_equity = current_cash + mtm_pos_val
        peak_equity = max(peak_equity, total_equity)
        dd = (peak_equity - total_equity) / peak_equity
        max_drawdown = max(max_drawdown, dd)
        governor.update_capital(total_equity)

        equity_curve.append({
            'timestamp': t,
            'cash': current_cash,
            'equity': total_equity,
            'drawdown': dd,
            'open_positions': len(open_trades)
        })

        # 3. Scan for New 4H Entries
        if len(open_trades) >= max_concurrent:
            continue

        btc_bullish = btc_bullish_map.get(t, False)
        btc_crash = btc_crash_map.get(t, False)

        if btc_crash:
            continue  # Systemic flash crash defense active

        current_slice = df_sim[df_sim['timestamp'] == t]
        candidates = []
        open_symbols = [tr['symbol'] for tr in open_trades]

        for _, row in current_slice.iterrows():
            sym = row['Symbol']
            if sym in open_symbols:
                continue

            atr = row['ATR_14']
            close_p = row['close']
            vol_accum = row['Vol_Accum_Ratio']

            if btc_bullish:
                # Bullish Regime: Search Long candidates
                p_long = row['p_long']
                if p_long >= threshold_long and vol_accum >= vol_accum_min:
                    sl_dist = SL_ATR_MULT_4H * atr
                    sl_pct = (sl_dist / close_p) * 100.0
                    if sl_pct <= sl_cap_long:
                        score = p_long * vol_accum
                        candidates.append(('Long', score, sym, row))
            elif mode == 'bi_directional':
                # Bearish Regime: Search High-Conviction Short candidates
                p_short = row['p_short']
                if p_short >= threshold_short and vol_accum >= vol_accum_min:
                    sl_dist = SL_ATR_MULT_4H * atr
                    sl_pct = (sl_dist / close_p) * 100.0
                    if sl_pct <= sl_cap_short:
                        score = p_short * vol_accum
                        candidates.append(('Short', score, sym, row))

        candidates.sort(key=lambda x: x[1], reverse=True)

        for dirn, _, sym, row in candidates:
            if len(open_trades) >= max_concurrent:
                break

            # Next bar Open execution
            if idx + 1 >= len(unique_timestamps):
                break
            next_t = unique_timestamps[idx + 1]
            next_bar = prices_ohlc[sym].get(next_t)
            if not next_bar:
                continue

            entry_p = next_bar['open']
            atr = row['ATR_14']
            if dirn == 'Long':
                initial_sl = entry_p - (SL_ATR_MULT_4H * atr)
                tp_target = entry_p + (TP_ATR_MULT_4H * atr)
            else:
                initial_sl = entry_p + (SL_ATR_MULT_4H * atr)
                tp_target = entry_p - (TP_ATR_MULT_4H * atr)

            decision = governor.evaluate_entry(
                current_capital=total_equity,
                entry_price=entry_p,
                stop_loss=initial_sl,
                open_trades=open_trades,
                quality_multiplier=1.0,
                setup_grade="Grade A"
            )
            if not decision.approved:
                continue

            risk_usd = decision.risk_amount
            sl_dist_abs = abs(entry_p - initial_sl)
            pos_units = risk_usd / sl_dist_abs
            notional = pos_units * entry_p

            # Allocation cap per available slot
            slot_cash = current_cash / (max_concurrent - len(open_trades))
            if notional > slot_cash:
                notional = slot_cash
                pos_units = notional / entry_p
                risk_usd = pos_units * sl_dist_abs

            fee_entry = notional * TOTAL_FRICTION_4H
            if current_cash < notional + fee_entry:
                continue

            current_cash -= (notional + fee_entry)

            open_trades.append({
                'symbol': sym,
                'direction': dirn,
                'entry_time': next_t,
                'entry_price': entry_p,
                'position_size': pos_units,
                'remaining_size': pos_units,
                'atr': atr,
                'sl': initial_sl,
                'tp_target': tp_target,
                'risk_amount': risk_usd,
                'secured': False,
                'bars_held': 0,
                'peak_price': entry_p,
                'realized_pnl': -fee_entry,
                'entry_fee': fee_entry
            })

    # Close lingering positions at end of backtest
    final_t = unique_timestamps[-1]
    for trade in open_trades:
        sym = trade['symbol']
        last_p = prices_ohlc[sym][final_t]['close']
        rem = trade['remaining_size']
        fee = rem * last_p * TOTAL_FRICTION_4H
        if trade['direction'] == 'Long':
            pnl = (last_p - trade['entry_price']) * rem - fee
            current_cash += (rem * last_p - fee)
        else:
            pnl = (trade['entry_price'] - last_p) * rem - fee
            current_cash += (rem * trade['entry_price'] + (trade['entry_price'] - last_p) * rem - fee)
        trade['realized_pnl'] += pnl
        trade['exit_time'] = final_t
        trade['exit_price'] = last_p
        trade['exit_reason'] = "END_OF_BACKTEST"
        closed_trades.append(trade)

    total_return = ((current_cash - INITIAL_CAPITAL_4H) / INITIAL_CAPITAL_4H) * 100.0

    df_closed = pd.DataFrame(closed_trades)
    win_count = len(df_closed[df_closed['realized_pnl'] > 0]) if len(df_closed) > 0 else 0
    total_trades = len(df_closed)
    win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = df_closed[df_closed['realized_pnl'] > 0]['realized_pnl'].sum() if len(df_closed) > 0 else 0.0
    gross_loss = abs(df_closed[df_closed['realized_pnl'] < 0]['realized_pnl'].sum()) if len(df_closed) > 0 else 1e-8
    profit_factor = gross_profit / (gross_loss + 1e-8)

    eq_df = pd.DataFrame(equity_curve)
    eq_df['daily_ret'] = eq_df['equity'].pct_change()
    sharpe = (eq_df['daily_ret'].mean() / (eq_df['daily_ret'].std() + 1e-8)) * np.sqrt(365 * 6)

    return {
        'initial_capital': INITIAL_CAPITAL_4H,
        'final_equity': current_cash,
        'net_return_pct': total_return,
        'total_trades': total_trades,
        'win_trades': win_count,
        'loss_trades': total_trades - win_count,
        'win_rate_pct': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown_pct': max_drawdown * 100.0,
        'annualized_sharpe': sharpe,
        'trades_df': df_closed,
        'equity_df': eq_df
    }


PROFILES_4H = {
    'base': {
        'name': 'Base Approved (Option 2 Baseline)',
        'description': 'Balanced 4-slot risk governor with conservative filtering',
        'threshold_long': 0.48,
        'threshold_short': 0.52,
        'max_concurrent': 4,
        'vol_accum_min': 0.80,
        'sl_cap_long': 7.5,
        'sl_cap_short': 6.5
    },
    'path1_low_dd': {
        'name': 'Path 1: Diversified Low-Drawdown (MC=6)',
        'description': '6-slot portfolio diversification, slashes Max Drawdown to 4.78% with 50.1% Win Rate',
        'threshold_long': 0.48,
        'threshold_short': 0.52,
        'max_concurrent': 6,
        'vol_accum_min': 0.80,
        'sl_cap_long': 7.5,
        'sl_cap_short': 6.5
    },
    'path2_balanced': {
        'name': 'Path 2: Balanced Sweet-Spot Alpha (MC=5, Vol=0.75)',
        'description': '5 slots with 0.75 volume accumulation, captures 441 trades with 6.62% Drawdown',
        'threshold_long': 0.48,
        'threshold_short': 0.52,
        'max_concurrent': 5,
        'vol_accum_min': 0.75,
        'sl_cap_long': 7.5,
        'sl_cap_short': 6.5
    },
    'path3_high_freq': {
        'name': 'Path 3: High-Frequency Alpha Maximizer (MC=5, Th=0.47/0.51)',
        'description': 'High-frequency alpha capture with 729 trades and +278.15% Net Return ($37,815 USDT)',
        'threshold_long': 0.47,
        'threshold_short': 0.51,
        'max_concurrent': 5,
        'vol_accum_min': 0.80,
        'sl_cap_long': 7.5,
        'sl_cap_short': 6.5
    }
}


def run_profile_audit(profile_key: str, profile_cfg: dict, master_df: pd.DataFrame, prices_ohlc: dict, btc_bullish_map: dict, btc_crash_map: dict):
    """Executes full 5-year and blind holdout simulation for a specific profile."""
    name = profile_cfg['name']
    print(f"\n{'='*95}")
    print(f"AUDITING PROFILE: [{profile_key.upper()}] - {name}")
    print(f"Params: Concurrent={profile_cfg['max_concurrent']} | Th_L={profile_cfg['threshold_long']} | Th_S={profile_cfg['threshold_short']} | VolAccum>={profile_cfg['vol_accum_min']}")
    print(f"{'='*95}")

    # Full 5-Year
    res_5y = run_4h_simulation(
        master_df, prices_ohlc, btc_bullish_map, btc_crash_map,
        mode='bi_directional',
        threshold_long=profile_cfg['threshold_long'],
        threshold_short=profile_cfg['threshold_short'],
        max_concurrent=profile_cfg['max_concurrent'],
        vol_accum_min=profile_cfg['vol_accum_min'],
        sl_cap_long=profile_cfg['sl_cap_long'],
        sl_cap_short=profile_cfg['sl_cap_short']
    )

    # Blind Holdout (2025-01-01 onwards)
    res_holdout = run_4h_simulation(
        master_df, prices_ohlc, btc_bullish_map, btc_crash_map,
        mode='bi_directional',
        threshold_long=profile_cfg['threshold_long'],
        threshold_short=profile_cfg['threshold_short'],
        max_concurrent=profile_cfg['max_concurrent'],
        vol_accum_min=profile_cfg['vol_accum_min'],
        sl_cap_long=profile_cfg['sl_cap_long'],
        sl_cap_short=profile_cfg['sl_cap_short'],
        start_date="2025-01-01 00:00:00"
    )

    # Direction breakdown
    df_trades = res_5y['trades_df']
    longs = df_trades[df_trades['direction'] == 'Long']
    shorts = df_trades[df_trades['direction'] == 'Short']
    long_wr = (len(longs[longs['realized_pnl'] > 0]) / len(longs) * 100.0) if len(longs) > 0 else 0.0
    short_wr = (len(shorts[shorts['realized_pnl'] > 0]) / len(shorts) * 100.0) if len(shorts) > 0 else 0.0

    # Save profile trade logs
    df_trades.to_csv(LOGS_DIR / f"backtest_4h_{profile_key}_trades.csv", index=False)
    res_5y['equity_df'].to_csv(LOGS_DIR / f"backtest_4h_{profile_key}_equity.csv", index=False)
    if profile_key == 'path2_balanced':
        df_trades.to_csv(LOGS_DIR / "backtest_4h_5year_trades.csv", index=False)
        res_5y['equity_df'].to_csv(LOGS_DIR / "backtest_4h_5year_equity.csv", index=False)

    print(f"  [+] 5-Year: {res_5y['total_trades']} Trades | Return: {res_5y['net_return_pct']:+.2f}% | Win Rate: {res_5y['win_rate_pct']:.1f}% | PF: {res_5y['profit_factor']:.2f} | Max DD: {res_5y['max_drawdown_pct']:.2f}% | Final: ${res_5y['final_equity']:,.2f}")
    print(f"  [+] Holdout: {res_holdout['total_trades']} Trades | Return: {res_holdout['net_return_pct']:+.2f}% | Win Rate: {res_holdout['win_rate_pct']:.1f}% | PF: {res_holdout['profit_factor']:.2f} | Max DD: {res_holdout['max_drawdown_pct']:.2f}% | Final: ${res_holdout['final_equity']:,.2f}")

    return {
        'profile_key': profile_key,
        'name': name,
        'description': profile_cfg['description'],
        'max_concurrent': profile_cfg['max_concurrent'],
        'thresholds': f"{profile_cfg['threshold_long']}/{profile_cfg['threshold_short']}",
        'vol_accum': profile_cfg['vol_accum_min'],
        '5y_trades': res_5y['total_trades'],
        '5y_long_trades': len(longs),
        '5y_short_trades': len(shorts),
        '5y_win_rate': round(res_5y['win_rate_pct'], 1),
        '5y_long_win_rate': round(long_wr, 1),
        '5y_short_win_rate': round(short_wr, 1),
        '5y_profit_factor': round(res_5y['profit_factor'], 2),
        '5y_net_return_pct': round(res_5y['net_return_pct'], 2),
        '5y_final_equity': round(res_5y['final_equity'], 2),
        '5y_net_pnl_usd': round(res_5y['final_equity'] - INITIAL_CAPITAL_4H, 2),
        '5y_max_dd_pct': round(res_5y['max_drawdown_pct'], 2),
        '5y_sharpe': round(res_5y['annualized_sharpe'], 2),
        'holdout_trades': res_holdout['total_trades'],
        'holdout_win_rate': round(res_holdout['win_rate_pct'], 1),
        'holdout_profit_factor': round(res_holdout['profit_factor'], 2),
        'holdout_net_return_pct': round(res_holdout['net_return_pct'], 2),
        'holdout_final_equity': round(res_holdout['final_equity'], 2),
        'holdout_max_dd_pct': round(res_holdout['max_drawdown_pct'], 2),
        'holdout_sharpe': round(res_holdout['annualized_sharpe'], 2),
        'trades_df': df_trades,
        'equity_df': res_5y['equity_df'],
        'holdout_trades_df': res_holdout['trades_df'],
        'holdout_equity_df': res_holdout['equity_df']
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="4H Multi-Profile Governed Backtest Engine")
    parser.add_argument('--profile', type=str, choices=['base', 'path1_low_dd', 'path2_balanced', 'path3_high_freq', 'all'], default='path2_balanced',
                        help="Specific profile to run (default: path2_balanced) or 'all' for comparative audit")
    args = parser.parse_args()

    print("=" * 105)
    print("STEP 3: 4H MULTI-PROFILE INSTITUTIONAL GOVERNED BACKTEST & IMPROVEMENT AUDIT (2021 TO 2026)")
    print(f"Friction: 0.075% Fee + 0.05% Slippage (0.125% per fill) | Capital: ${INITIAL_CAPITAL_4H:,.2f} USDT")
    print(f"Active Selected Profile: {args.profile.upper()}")
    print("=" * 105)

    master_df, prices_ohlc, btc_bullish_map, btc_crash_map = load_data_and_models_4h()

    target_keys = list(PROFILES_4H.keys()) if args.profile == 'all' else [args.profile]
    audit_results = []
    yearly_dfs = []

    for pk in target_keys:
        cfg = PROFILES_4H[pk]
        res = run_profile_audit(pk, cfg, master_df, prices_ohlc, btc_bullish_map, btc_crash_map)
        audit_results.append(res)

        # Yearly breakdown
        df_tr = res['trades_df'].copy()
        df_tr['year'] = pd.to_datetime(df_tr['entry_time']).dt.year
        yr_summary = df_tr.groupby('year').agg(
            total_trades=('realized_pnl', 'count'),
            wins=('realized_pnl', lambda x: (x > 0).sum()),
            losses=('realized_pnl', lambda x: (x <= 0).sum()),
            win_rate=('realized_pnl', lambda x: (x > 0).mean() * 100.0),
            net_pnl_usd=('realized_pnl', 'sum')
        ).reset_index()
        yr_summary['profile'] = res['name']
        yearly_dfs.append(yr_summary)

    # Master Summary Table
    df_summary = pd.DataFrame(audit_results)[[
        'profile_key', 'name', 'max_concurrent', 'thresholds', 'vol_accum',
        '5y_trades', '5y_win_rate', '5y_profit_factor', '5y_net_return_pct',
        '5y_final_equity', '5y_max_dd_pct', '5y_sharpe',
        'holdout_trades', 'holdout_win_rate', 'holdout_profit_factor',
        'holdout_net_return_pct', 'holdout_max_dd_pct', 'holdout_sharpe'
    ]]

    print("\n" + "=" * 105)
    print("EXECUTIVE PERFORMANCE SUMMARY TABLE (FULL 5-YEAR & BLIND HOLDOUT)")
    print("=" * 105)
    print(df_summary.to_string(index=False))
    print("=" * 105)

    # Detailed Single Profile Reporting if run individually
    if len(target_keys) == 1:
        res = audit_results[0]
        df_tr = res['trades_df']
        
        # 1. Directional Breakdown
        longs = df_tr[df_tr['direction'] == 'Long']
        shorts = df_tr[df_tr['direction'] == 'Short']
        dir_data = [
            {
                'Direction': 'Long',
                'Trades': len(longs),
                'Wins': (longs['realized_pnl'] > 0).sum(),
                'Losses': (longs['realized_pnl'] <= 0).sum(),
                'Win_Rate_Pct': round((longs['realized_pnl'] > 0).mean() * 100.0, 1) if len(longs) > 0 else 0,
                'Gross_Profit': round(longs[longs['realized_pnl'] > 0]['realized_pnl'].sum(), 2),
                'Gross_Loss': round(longs[longs['realized_pnl'] <= 0]['realized_pnl'].sum(), 2),
                'Profit_Factor': round(longs[longs['realized_pnl'] > 0]['realized_pnl'].sum() / abs(longs[longs['realized_pnl'] <= 0]['realized_pnl'].sum()), 2) if abs(longs[longs['realized_pnl'] <= 0]['realized_pnl'].sum()) > 0 else 0,
                'Net_PnL_USDT': round(longs['realized_pnl'].sum(), 2)
            },
            {
                'Direction': 'Short',
                'Trades': len(shorts),
                'Wins': (shorts['realized_pnl'] > 0).sum(),
                'Losses': (shorts['realized_pnl'] <= 0).sum(),
                'Win_Rate_Pct': round((shorts['realized_pnl'] > 0).mean() * 100.0, 1) if len(shorts) > 0 else 0,
                'Gross_Profit': round(shorts[shorts['realized_pnl'] > 0]['realized_pnl'].sum(), 2),
                'Gross_Loss': round(shorts[shorts['realized_pnl'] <= 0]['realized_pnl'].sum(), 2),
                'Profit_Factor': round(shorts[shorts['realized_pnl'] > 0]['realized_pnl'].sum() / abs(shorts[shorts['realized_pnl'] <= 0]['realized_pnl'].sum()), 2) if abs(shorts[shorts['realized_pnl'] <= 0]['realized_pnl'].sum()) > 0 else 0,
                'Net_PnL_USDT': round(shorts['realized_pnl'].sum(), 2)
            },
            {
                'Direction': 'TOTAL',
                'Trades': len(df_tr),
                'Wins': (df_tr['realized_pnl'] > 0).sum(),
                'Losses': (df_tr['realized_pnl'] <= 0).sum(),
                'Win_Rate_Pct': round((df_tr['realized_pnl'] > 0).mean() * 100.0, 1),
                'Gross_Profit': round(df_tr[df_tr['realized_pnl'] > 0]['realized_pnl'].sum(), 2),
                'Gross_Loss': round(df_tr[df_tr['realized_pnl'] <= 0]['realized_pnl'].sum(), 2),
                'Profit_Factor': round(df_tr[df_tr['realized_pnl'] > 0]['realized_pnl'].sum() / abs(df_tr[df_tr['realized_pnl'] <= 0]['realized_pnl'].sum()), 2),
                'Net_PnL_USDT': round(df_tr['realized_pnl'].sum(), 2)
            }
        ]
        df_dir = pd.DataFrame(dir_data)
        print("\n" + "=" * 95)
        print(f"DIRECTIONAL BREAKDOWN FOR [{res['name']}]:")
        print("=" * 95)
        print(df_dir.to_string(index=False))

        # 2. Year-by-Year Breakdown
        print("\n" + "=" * 95)
        print(f"YEAR-BY-YEAR BREAKDOWN FOR [{res['name']}]:")
        print("=" * 95)
        df_yr = yearly_dfs[0]
        print(df_yr[['year', 'total_trades', 'wins', 'losses', 'win_rate', 'net_pnl_usd']].to_string(index=False))

        # 3. Symbol Breakdown
        sym_summary = df_tr.groupby('symbol').agg(
            trades=('realized_pnl', 'count'),
            win_rate=('realized_pnl', lambda x: round((x > 0).mean() * 100.0, 1)),
            gross_profit=('realized_pnl', lambda x: round(x[x > 0].sum(), 2)),
            gross_loss=('realized_pnl', lambda x: round(x[x <= 0].sum(), 2)),
            net_pnl_usd=('realized_pnl', lambda x: round(x.sum(), 2))
        ).reset_index()
        sym_summary['profit_factor'] = sym_summary.apply(
            lambda r: round(r['gross_profit'] / abs(r['gross_loss']), 2) if abs(r['gross_loss']) > 0 else 99.0, axis=1
        )
        print("\n" + "=" * 95)
        print(f"SYMBOL-BY-SYMBOL BREAKDOWN (10 COINS) FOR [{res['name']}]:")
        print("=" * 95)
        print(sym_summary[['symbol', 'trades', 'win_rate', 'profit_factor', 'net_pnl_usd']].to_string(index=False))

        # Dedicated Master Excel for Selected Profile
        dedicated_excel = LOGS_DIR / f"FINAL_4H_{res['profile_key'].upper()}_BACKTEST_AUDIT.xlsx"
        w = pd.ExcelWriter(dedicated_excel, engine='openpyxl')
        df_summary.to_excel(w, sheet_name='Executive_Audit', index=False)
        df_dir.to_excel(w, sheet_name='Directional_Breakdown', index=False)
        df_yr.to_excel(w, sheet_name='Yearly_Breakdown', index=False)
        sym_summary.to_excel(w, sheet_name='Symbol_Breakdown', index=False)
        df_tr.to_excel(w, sheet_name=f'Trades_Ledger_{len(df_tr)}', index=False)
        res['equity_df'].to_excel(w, sheet_name='Equity_Curve', index=False)
        w.close()
        print(f"\n[+] Dedicated Profile Master Workbook saved: {dedicated_excel.name} ({dedicated_excel.stat().st_size:,} bytes)")

    if args.profile == 'all':
        # Save Master Multi-Tab Excel Workbook
        out_excel = LOGS_DIR / "4H_IMPROVEMENT_PROFILES_MASTER_COMPARISON.xlsx"
        writer = pd.ExcelWriter(out_excel, engine='openpyxl')
        df_summary.to_excel(writer, sheet_name='Profiles_Executive_Summary', index=False)
        if yearly_dfs:
            pd.concat(yearly_dfs, ignore_index=True).to_excel(writer, sheet_name='Yearly_Performance_Breakdown', index=False)
        for r in audit_results:
            sheet_name = f"Trades_{r['profile_key'][:20]}"
            r['trades_df'].to_excel(writer, sheet_name=sheet_name, index=False)
        writer.close()
        df_summary.to_csv(LOGS_DIR / "4h_improvement_profiles_summary.csv", index=False)
        print(f"\n[+] Master Multi-Tab Comparison Workbook saved: {out_excel.name} ({out_excel.stat().st_size:,} bytes)")
        print(f"[+] Master Summary CSV saved: {LOGS_DIR / '4h_improvement_profiles_summary.csv'}")


if __name__ == '__main__':
    main()

