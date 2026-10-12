import sys
import ctypes
from pathlib import Path
import time
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    MODELS_1D_POOLED_DIR,
    LOGS_DIR,
    SYMBOLS,
    INITIAL_CAPITAL,
    BINANCE_TAKER_FEE,
    FEATURE_COLS,
    MACRO_BTC_EMA_PERIOD,
    TP_ATR_MULT,
    SL_ATR_MULT,
    PARTIAL_TP_PCT
)
from features_1d import compute_1d_base_features, add_relative_momentum_vs_btc
from model_provenance import load_verified_production_model_paths
from strategy_signals import should_enter_spot_long
from risk_governor import RiskGovernor
from execution.binance_client import BinanceExecutionClient
from execution.order_manager import OrderManager

class PaperExecutionEngine:
    """
    Zero-Trust Real-Time Paper Trading & Binance Testnet Execution Engine.
    
    1. Fetches real-time daily candles directly from Binance via CCXT.
    2. Computes pure mathematical stationary features on closed candles (No retail indicators).
    3. Runs certified Pooled XGBoost models with Law #9 Macro BTC EMA 20 filter.
    4. Evaluates risk via Institutional RiskGovernor (drawdown damping, exposure caps).
    5. Dispatches fills to Binance Testnet or local persistent paper journal.
    6. Certified Law #6 Swing Runner architecture (75% TP at +3.0x ATR, trailing 25% Runner).
    """

    def __init__(
        self,
        initial_capital: float = INITIAL_CAPITAL,
        model_threshold: float = 0.44,
        mode: str = 'spot',
        use_testnet: bool = True
    ):
        self.initial_capital = initial_capital
        self.model_threshold = model_threshold
        self.mode = mode
        self.client = BinanceExecutionClient(use_testnet=use_testnet, is_futures=(mode == 'futures'))
        self.order_mgr = OrderManager(logs_dir=LOGS_DIR)
        self.scan_ledger_file = LOGS_DIR / "paper_scan_ledger.csv"
        
        # Dynamic wallet synchronization with Binance Testnet
        self.current_capital = self._calculate_current_capital()
        if self.client.has_credentials and self.current_capital > self.initial_capital:
            self.initial_capital = self.current_capital

        # Load Risk Governor
        self.risk_gov = RiskGovernor(
            initial_capital=self.initial_capital,
            base_risk_pct=0.05,
            max_concurrent_trades=3,
            max_portfolio_risk_pct=0.12,
            dd_tier_1=0.10,
            dd_tier_2=0.20,
            dd_tier_3=0.35,
            min_risk_pct=0.015
        )
        self.risk_gov.update_capital(self.current_capital)

        # Load only an explicitly promoted, hash-verified production model bundle.
        # Step 4 research candidates live in a separate directory and are never executable here.
        production_paths = load_verified_production_model_paths(
            MODELS_1D_POOLED_DIR,
            expected_feature_columns=FEATURE_COLS,
        )
        self.model_long = joblib.load(production_paths["Long"])
        self.model_short = joblib.load(production_paths["Short"])

    def _calculate_current_capital(self) -> float:
        """Calculate current equity dynamically from Binance Testnet or local paper wallet."""
        if self.client.has_credentials:
            try:
                bal = self.client.fetch_balance()
                if bal.get('mode') == 'TESTNET_LIVE_ACCOUNT':
                    usdt = float(bal.get('USDT', 0.0))
                    if usdt > 0:
                        return usdt
            except Exception:
                pass
        realized_total = 0.0
        if self.order_mgr.trade_log_file.exists():
            try:
                df = pd.read_csv(self.order_mgr.trade_log_file)
                if not df.empty and 'realized_pnl' in df.columns:
                    realized_total = df['realized_pnl'].sum()
            except Exception:
                pass
        return max(10.0, self.initial_capital + realized_total)

    def compute_live_features(self, ohlcv_dict: Dict[str, list], symbol: str) -> pd.DataFrame:
        """Compute live 1D features with the exact shared research formulas."""
        required = ["timestamp", "open", "high", "low", "close", "volume"]
        if symbol not in ohlcv_dict or not ohlcv_dict[symbol]:
            raise ValueError(f"No OHLCV candles supplied for {symbol}")

        df = pd.DataFrame(ohlcv_dict[symbol], columns=required)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="raise")
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        df = compute_1d_base_features(df)

        # Relative momentum is timestamp-joined, never silently filled with zero.
        if "BTCUSDT" not in ohlcv_dict or not ohlcv_dict["BTCUSDT"]:
            df["Rel_Mom_vs_BTC"] = np.nan
        else:
            btc_df = pd.DataFrame(ohlcv_dict["BTCUSDT"], columns=required)
            btc_df["timestamp"] = pd.to_datetime(btc_df["timestamp"], unit="ms", errors="raise")
            btc_df.sort_values("timestamp", inplace=True)
            btc_df.reset_index(drop=True, inplace=True)
            df = add_relative_momentum_vs_btc(df, btc_df)

        return df

    def scan_and_execute_cycle(self) -> Dict[str, Any]:
        """
        Execute one complete operational cycle across all 10 coins.
        1. Synchronizes live wallet funds.
        2. Updates and logs existing positions with live prices and unrealized PnL.
        3. Evaluates Macro BTC regime.
        4. Scans all 10 coins, prints an institutional scan table, and records every coin to paper_scan_ledger.csv.
        5. Computes transparent slot/fund allocation math and dispatches qualified orders.
        """
        cycle_time = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Update wallet balance
        bal_info = self.client.fetch_balance()
        if bal_info.get('mode') == 'TESTNET_LIVE_ACCOUNT' and bal_info.get('USDT', 0.0) > 0:
            self.current_capital = float(bal_info['USDT'])
            self.risk_gov.update_capital(self.current_capital)

        print("\n" + "=" * 125)
        print(f"LIVE TRADING CYCLE: {cycle_time} UTC | Mode: {self.mode.upper()} | Wallet Status: {bal_info.get('mode')}")
        print(f"FUNDS AUDIT: Available Free USDT = ${self.current_capital:,.2f} | Open Positions = {len(self.order_mgr.positions)} / 3 | Portfolio Drawdown = {self.risk_gov.current_drawdown*100:.2f}%")
        print("=" * 125)

        # 2. Update and Log Existing Positions
        closed_in_cycle = []
        if self.order_mgr.positions:
            print("\n--- [ACTIVE POSITIONS MONITOR] ---")
            print(f"{'Symbol':<10} | {'Side':<5} | {'Entry Price':>12} | {'Live Price':>12} | {'Unrlz PnL ($)':>14} | {'Trail SL':>12} | {'TP Target':>12} | {'Days Held':>9}")
            print("-" * 105)
            for pos in self.order_mgr.positions[:]:
                sym = pos['symbol']
                try:
                    live_price = self.client.fetch_ticker_price(sym)
                    entry_p = pos['entry_price']
                    unrlz = (live_price - entry_p) * pos['remaining_size'] if pos['direction'] == 'Long' else (entry_p - live_price) * pos['remaining_size']
                    unrlz_pct = ((live_price - entry_p) / entry_p * 100.0) if pos['direction'] == 'Long' else ((entry_p - live_price) / entry_p * 100.0)
                    tp_tgt = entry_p + TP_ATR_MULT * pos['atr'] if pos['direction'] == 'Long' else entry_p - TP_ATR_MULT * pos['atr']
                    days_held = (time.time() - pos.get('entry_timestamp', time.time())) / 86400.0

                    closed = self.order_mgr.update_positions_on_tick(sym, live_price)
                    if closed:
                        closed_in_cycle.extend(closed)
                        for c in closed:
                            self.current_capital += c['realized_pnl']
                            self.risk_gov.update_capital(self.current_capital)
                            print(f"  >>> [EXIT TRIGGERED] Closed {sym} | Reason: {c['exit_reason']} | Realized PnL: ${c['realized_pnl']:+.2f} <<<")
                    else:
                        print(f"{sym:<10} | {pos['direction']:<5} | ${entry_p:>11.4f} | ${live_price:>11.4f} | ${unrlz:>+7.2f} ({unrlz_pct:>+5.1f}%) | ${pos['sl']:>11.4f} | ${tp_tgt:>11.4f} | {days_held:>8.1f}d")
                except Exception as e:
                    print(f"  [WARN] Failed to update tick for {sym}: {e}")
            print("-" * 105)

        # 3. Fetch candles for all symbols (at least 100 daily candles for warmup)
        ohlcv_all = {}
        for sym in SYMBOLS:
            try:
                ohlcv_all[sym] = self.client.fetch_recent_ohlcv(sym, timeframe='1d', limit=100)
            except Exception as e:
                print(f"  [WARN] Could not fetch candles for {sym}: {e}")

        # 4. Macro Regime & Systemic Crash Check (Law #9)
        btc_bullish = False
        btc_crash = False
        btc_ret1 = 0.0
        if 'BTCUSDT' in ohlcv_all and len(ohlcv_all['BTCUSDT']) >= 25:
            btc_df = pd.DataFrame(ohlcv_all['BTCUSDT'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            btc_ema20 = btc_df['close'].ewm(span=MACRO_BTC_EMA_PERIOD, adjust=False).mean()
            btc_bullish = bool(btc_df['close'].iloc[-2] >= btc_ema20.iloc[-2])
            btc_ret1 = (btc_df['close'].iloc[-2] - btc_df['close'].iloc[-3]) / btc_df['close'].iloc[-3]
            btc_crash = bool(btc_ret1 <= -0.06)

        print(f"\n--- [10-COIN AI SCAN MATRIX] (Macro BTC Bullish: {btc_bullish} | 1D BTC Return: {btc_ret1*100:+.2f}% | Crash Active: {btc_crash}) ---")
        print(f"{'Symbol':<10} | {'Live Price':>12} | {'1D Change':>10} | {'P(Long)':>8} | {'P(Short)':>8} | {'Vol Accum':>10} | {'Grade':<9} | {'Decision / Reason'}")
        print("-" * 125)

        ledger_records = []
        candidates = []
        open_symbols = [p['symbol'] for p in self.order_mgr.positions]

        for symbol in SYMBOLS:
            if symbol not in ohlcv_all or len(ohlcv_all[symbol]) < 25:
                print(f"{symbol:<10} | {'N/A':>12} | {'N/A':>10} | {'---':>8} | {'---':>8} | {'---':>10} | {'---':<9} | Insufficient candle warmup data")
                continue

            live_price = self.client.fetch_ticker_price(symbol)
            candles = ohlcv_all[symbol]
            ret_1 = (candles[-1][4] - candles[-2][4]) / candles[-2][4] if len(candles) >= 2 else 0.0

            if symbol in open_symbols:
                print(f"{symbol:<10} | ${live_price:>11.4f} | {ret_1*100:>+9.2f}% | {'---':>8} | {'---':>8} | {'---':>10} | {'HOLDING':<9} | In Position (Monitoring Trailing Stop)")
                ledger_records.append({
                    'timestamp': cycle_time,
                    'symbol': symbol,
                    'live_price': live_price,
                    'return_1d_pct': round(ret_1 * 100, 2),
                    'p_long': None,
                    'p_short': None,
                    'vol_accum_ratio': None,
                    'setup_grade': 'HOLDING',
                    'decision': 'IN_POSITION',
                    'reason': 'Already holding active position',
                    'wallet_balance': self.current_capital,
                    'open_positions': len(self.order_mgr.positions)
                })
                continue

            if btc_crash:
                print(f"{symbol:<10} | ${live_price:>11.4f} | {ret_1*100:>+9.2f}% | {'---':>8} | {'---':>8} | {'---':>10} | {'BLOCKED':<9} | Halting new entries (Macro BTC Dump <= -6%)")
                continue

            try:
                df_feat = self.compute_live_features(ohlcv_all, symbol)
                completed_candle = df_feat.iloc[-2]
                feat_vals = completed_candle[FEATURE_COLS].to_numpy(dtype=float).reshape(1, -1)
                if not np.isfinite(feat_vals).all():
                    reason = "BLOCKED: non-finite/missing model features; verify candle warmup and BTC timestamp alignment"
                    print(f"{symbol:<10} | ${live_price:>11.4f} | {ret_1*100:>+9.2f}% | {'---':>8} | {'---':>8} | {'---':>10} | {'BLOCKED':<9} | {reason}")
                    ledger_records.append({
                        'timestamp': cycle_time,
                        'symbol': symbol,
                        'live_price': live_price,
                        'return_1d_pct': round(ret_1 * 100, 2),
                        'p_long': None,
                        'p_short': None,
                        'vol_accum_ratio': None,
                        'setup_grade': 'BLOCKED',
                        'decision': 'BLOCKED_INVALID_FEATURES',
                        'reason': reason,
                        'wallet_balance': self.current_capital,
                        'open_positions': len(self.order_mgr.positions)
                    })
                    continue

                p_long = float(self.model_long.predict_proba(feat_vals)[0][1])
                p_short = float(self.model_short.predict_proba(feat_vals)[0][1])
                atr = float(completed_candle['ATR_14'])
                v_ratio = float(completed_candle['Vol_Accum_Ratio'])
                sl_distance = SL_ATR_MULT * atr
                sl_dist_pct = (sl_distance / live_price) * 100.0

                # Calibrated setup quality grading
                if p_long >= 0.46 and sl_dist_pct <= 7.0 and v_ratio >= 1.0:
                    grade = "Grade A+"
                    q_mult = 1.40
                elif p_long >= 0.40 and sl_dist_pct <= 9.0:
                    if v_ratio >= 1.0:
                        grade = "Grade A"
                        q_mult = 1.00
                    else:
                        grade = "Grade C"
                        q_mult = 0.00
                elif p_long >= 0.38 and sl_dist_pct <= 12.0:
                    grade = "Grade B"
                    q_mult = 0.65
                else:
                    grade = "Grade C"
                    q_mult = 0.00

                can_enter = False
                reason = ""
                if self.mode == 'spot':
                    can_enter, reason = should_enter_spot_long(
                        probability=p_long,
                        threshold=self.model_threshold,
                        btc_bullish=btc_bullish,
                        relative_momentum=completed_candle.get('Rel_Mom_vs_BTC', float('nan')),
                        pullback_depth=completed_candle.get('Pullback_Depth', float('nan')),
                        stop_distance_ratio=completed_candle.get('SL_Dist_Ratio', float('nan')),
                        volume_accumulation_ratio=v_ratio,
                    )

                    if can_enter:
                        if q_mult > 0:
                            reason = f"CANDIDATE SELECTED ({grade}, Mult: {q_mult:.2f}x)"
                            sl = live_price - sl_distance
                            candidates.append({
                                'symbol': symbol,
                                'direction': 'Long',
                                'confidence': p_long,
                                'entry_price': live_price,
                                'sl': sl,
                                'atr': atr,
                                'grade': grade,
                                'q_mult': q_mult,
                                'sl_dist_pct': sl_dist_pct
                            })
                        else:
                            reason = f"Rejected: Toxic Trap / Grade C (Vol: {v_ratio:.2f})"
                else: # Futures mode
                    if p_long >= self.model_threshold and p_long >= p_short and q_mult > 0:
                        can_enter = True
                        reason = f"FUTURES LONG CANDIDATE ({grade})"
                        sl = live_price - sl_distance
                        candidates.append({
                            'symbol': symbol,
                            'direction': 'Long',
                            'confidence': p_long,
                            'entry_price': live_price,
                            'sl': sl,
                            'atr': atr,
                            'grade': grade,
                            'q_mult': q_mult,
                            'sl_dist_pct': sl_dist_pct
                        })
                    elif p_short >= self.model_threshold and p_short > p_long:
                        can_enter = True
                        reason = "FUTURES SHORT CANDIDATE"
                        sl = live_price + sl_distance
                        candidates.append({
                            'symbol': symbol,
                            'direction': 'Short',
                            'confidence': p_short,
                            'entry_price': live_price,
                            'sl': sl,
                            'atr': atr,
                            'grade': "Standard",
                            'q_mult': 1.00,
                            'sl_dist_pct': sl_dist_pct
                        })
                    else:
                        reason = f"Neutral: P_L({p_long:.3f}), P_S({p_short:.3f}) below threshold"

                print(f"{symbol:<10} | ${live_price:>11.4f} | {ret_1*100:>+9.2f}% | {p_long:>8.3f} | {p_short:>8.3f} | {v_ratio:>10.2f} | {grade:<9} | {reason}")
                ledger_records.append({
                    'timestamp': cycle_time,
                    'symbol': symbol,
                    'live_price': live_price,
                    'return_1d_pct': round(ret_1 * 100, 2),
                    'p_long': round(p_long, 4),
                    'p_short': round(p_short, 4),
                    'vol_accum_ratio': round(v_ratio, 2),
                    'setup_grade': grade,
                    'decision': 'CANDIDATE' if can_enter and q_mult > 0 else 'SKIPPED',
                    'reason': reason,
                    'wallet_balance': self.current_capital,
                    'open_positions': len(self.order_mgr.positions)
                })

            except Exception as e:
                print(f"{symbol:<10} | ${live_price:>11.4f} | {'ERROR':>10} | {'---':>8} | {'---':>8} | {'---':>10} | {'---':<9} | Scan error: {e}")

        print("-" * 125)

        # 5. Persist Scan Ledger to CSV on Disk
        if ledger_records:
            df_ledger = pd.DataFrame(ledger_records)
            hdr = not self.scan_ledger_file.exists()
            df_ledger.to_csv(self.scan_ledger_file, mode='a', header=hdr, index=False)

        # 6. Evaluate Candidates via Risk Governor and Execute
        candidates.sort(key=lambda c: c['confidence'], reverse=True)
        newly_opened = []

        for cand in candidates:
            decision = self.risk_gov.evaluate_entry(
                current_capital=self.current_capital,
                entry_price=cand['entry_price'],
                stop_loss=cand['sl'],
                open_trades=self.order_mgr.positions,
                atr=cand['atr'],
                quality_multiplier=cand['q_mult'],
                setup_grade=cand['grade']
            )

            if not decision.approved:
                print(f"  [RISK GOVERNOR REJECTION] {cand['symbol']} {cand['direction']}: {decision.reason}")
                continue

            position_size = decision.position_size
            notional = position_size * cand['entry_price']

            # Spot Realism enforcement (Law #7: Total Notional <= Capital)
            if self.mode == 'spot':
                slots_remaining = max(1, 3 - len(self.order_mgr.positions))
                base_slot = self.current_capital / slots_remaining
                target_notional = base_slot * cand['q_mult']
                target_notional = min(target_notional, self.current_capital * 0.95)

                if target_notional < 5.0 or self.current_capital < target_notional:
                    print(f"  [CAPITAL REJECTION] Insufficient free cash for spot slot: {cand['symbol']}")
                    continue

                position_size = target_notional / cand['entry_price']
                notional = target_notional

            print(f"\n>>> [EXECUTING ORDER DISPATCH TO BINANCE TESTNET] <<<")
            print(f"  Symbol: {cand['symbol']} | Direction: {cand['direction']} | AI Conf: {cand['confidence']:.3f} ({cand['grade']})")
            print(f"  Fund Sizing: Available = ${self.current_capital:,.2f} USDT | Target Notional = ${notional:,.2f} USDT")
            print(f"  Position Units: {position_size:.4f} {cand['symbol']} | Fill Ref: ${cand['entry_price']:.4f}")
            print(f"  Stop Loss: ${cand['sl']:.4f} (-{cand['sl_dist_pct']:.2f}%) | Portfolio Risk: ${decision.risk_amount:.2f} ({decision.risk_pct*100:.2f}%)")

            order_side = 'buy' if cand['direction'] == 'Long' else 'sell'
            order_res = self.client.execute_market_order(
                symbol=cand['symbol'],
                side=order_side,
                amount=position_size
            )

            pos = self.order_mgr.add_position(
                symbol=cand['symbol'],
                direction=cand['direction'],
                entry_price=order_res['fill_price'],
                position_size=position_size,
                risk_amount=decision.risk_amount,
                stop_loss=cand['sl'],
                atr=cand['atr']
            )
            newly_opened.append(pos)
            print(f"  Order Result: {order_res['status']} | Order ID: {order_res['order_id']} | Real Fill: ${order_res['fill_price']:.4f}")

        print("-" * 125)
        print(f"CYCLE SUMMARY: Completed at {cycle_time} | Open Positions: {len(self.order_mgr.positions)} / 3 | Free Cash: ${self.current_capital:,.2f} USDT\n")
        sys.stdout.flush()

        return {
            'timestamp': cycle_time,
            'capital': self.current_capital,
            'drawdown': self.risk_gov.current_drawdown,
            'open_positions': len(self.order_mgr.positions),
            'newly_opened': len(newly_opened),
            'closed_trades': len(closed_in_cycle)
        }

    def run_daemon(self, interval_seconds: int = 300):
        """Run continuous real-time execution loop with Windows Sleep Prevention."""
        print(f"\n==========================================================")
        print(f"STARTING LIVE PAPER EXECUTION DAEMON (Interval: {interval_seconds}s)")
        print(f"Zero-Trust Institutional Quant Engine Active | Mode: {self.mode.upper()}")
        print(f"Press Ctrl+C to safely pause execution.")
        print(f"==========================================================\n")

        # Windows OS Sleep Prevention (Keeps CPU/Network awake even if display turns off)
        if sys.platform == 'win32':
            try:
                ES_CONTINUOUS = 0x80000000
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_AWAYMODE_REQUIRED = 0x00000040
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
                )
                print(">>> [POWER MANAGEMENT] Windows Sleep Prevention Active: Screen can turn off safely, CPU & Bot will run 24/7. <<<\n")
            except Exception as e:
                print(f"[WARN] Failed to configure Windows sleep prevention: {e}\n")

        try:
            while True:
                summary = self.scan_and_execute_cycle()
                print(f"[{summary['timestamp']}] Capital: ${summary['capital']:.2f} | Open: {summary['open_positions']} | Sleeping {interval_seconds}s...")
                sys.stdout.flush()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n[INFO] Daemon paused safely. Positions persisted to disk.")
            sys.stdout.flush()
        finally:
            if sys.platform == 'win32':
                try:
                    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
                except Exception:
                    pass

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Zero-Trust Live Paper & Testnet Engine")
    parser.add_argument('--daemon', action='store_true', help="Run continuously in background daemon loop")
    parser.add_argument('--interval', type=int, default=300, help="Polling interval in seconds (default: 300s)")
    parser.add_argument('--capital', type=float, default=INITIAL_CAPITAL, help="Initial paper capital")
    parser.add_argument('--threshold', type=float, default=0.44, help="Pooled XGBoost confidence threshold (default: 0.44)")
    parser.add_argument('--mode', type=str, default='spot', choices=['spot', 'futures'], help="Execution mode (spot or futures)")
    args = parser.parse_args()

    engine = PaperExecutionEngine(
        initial_capital=args.capital,
        model_threshold=args.threshold,
        mode=args.mode,
        use_testnet=True
    )

    if args.daemon:
        engine.run_daemon(interval_seconds=args.interval)
    else:
        summary = engine.scan_and_execute_cycle()
        print("\n--- SINGLE CYCLE SUMMARY ---")
        for k, v in summary.items():
            print(f"  {k}: {v}")


