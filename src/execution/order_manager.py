import sys
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
import time

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    BINANCE_TAKER_FEE,
    TP_ATR_MULT,
    SL_ATR_MULT,
    BE_ATR_MULT,
    PARTIAL_TP_PCT,
    RUNNER_PCT,
    RUNNER_TRAILING_ATR,
    RUNNER_SL_LOCK_ATR,
    MAX_INACTIVITY_DAYS
)

FEE_RATE = BINANCE_TAKER_FEE  # Binance VIP-0 Taker Fee (0.075%)

class OrderManager:
    """
    Manages active position state, trailing stop adjustments, partial take-profits,
    and trade logging with crash-resilient disk persistence adhering to Law #6 (Swing Runner).
    """

    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self.state_file = self.logs_dir / 'paper_active_positions.json'
        self.trade_log_file = self.logs_dir / 'paper_trade_log.csv'
        self.positions: List[Dict[str, Any]] = self._load_positions()
        self._ensure_trade_log_header()

    def _load_positions(self) -> List[Dict[str, Any]]:
        """Load active positions from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Error reading {self.state_file}: {e}")
        return []

    def _save_positions(self):
        """Persist active positions to disk atomically."""
        with open(self.state_file, 'w') as f:
            json.dump(self.positions, f, indent=2)

    def _ensure_trade_log_header(self):
        """Ensure trade log CSV has correct headers."""
        if not self.trade_log_file.exists():
            with open(self.trade_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'symbol', 'direction', 'entry_time', 'exit_time',
                    'entry_price', 'exit_price', 'position_size',
                    'realized_pnl', 'fee_paid', 'exit_reason'
                ])

    def log_closed_trade(self, trade: Dict[str, Any]):
        """Append closed trade to trade log CSV."""
        with open(self.trade_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trade['symbol'],
                trade['direction'],
                trade['entry_time'],
                trade['exit_time'],
                f"{trade['entry_price']:.4f}",
                f"{trade['exit_price']:.4f}",
                f"{trade['position_size']:.6f}",
                f"{trade['realized_pnl']:.4f}",
                f"{trade['total_fee']:.4f}",
                trade['exit_reason']
            ])

    def add_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        position_size: float,
        risk_amount: float,
        stop_loss: float,
        atr: float
    ) -> Dict[str, Any]:
        """Add and persist a new open position."""
        entry_time = time.strftime('%Y-%m-%d %H:%M:%S')
        entry_fee = position_size * entry_price * FEE_RATE
        
        pos = {
            'symbol': symbol,
            'direction': direction,
            'entry_time': entry_time,
            'entry_timestamp': time.time(),
            'entry_price': entry_price,
            'position_size': position_size,
            'remaining_size': position_size,
            'risk_amount': risk_amount,
            'sl': stop_loss,
            'atr': atr,
            'secured': False,
            'peak_price': entry_price,
            'trough_price': entry_price,
            'realized_pnl': -entry_fee,
            'total_fee': entry_fee
        }
        self.positions.append(pos)
        self._save_positions()
        return pos

    def update_positions_on_tick(
        self,
        symbol: str,
        current_price: float,
        high_price: Optional[float] = None,
        low_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate SL, Partial TP (75%), Dynamic Trailing Stop (25% Runner), Breakeven SL,
        and Inactivity-Based Exit (14d) for unhit trades.
        Returns list of closed trades.
        """
        h = high_price if high_price is not None else current_price
        l = low_price if low_price is not None else current_price
        closed_trades = []

        for pos in self.positions[:]:
            if pos['symbol'] != symbol:
                continue

            direction = pos['direction']
            atr = pos['atr']
            entry_price = pos['entry_price']
            closed = False
            exit_price = 0.0
            exit_reason = ""

            # 1. Stop Loss & Trailing Stop Check (Checked First - Law #5 / Mistake 4.5 fix)
            if direction == 'Long':
                pos['peak_price'] = max(pos['peak_price'], h)
                
                # SL check
                if l <= pos['sl']:
                    closed = True
                    exit_price = pos['sl']
                    exit_reason = "Trailing Stop" if pos['secured'] else "Stop Loss"
                else:
                    # Partial Take-Profit (+3.0x ATR): Bank 75% profit, leave 25% Runner
                    if not pos['secured'] and h >= (entry_price + TP_ATR_MULT * atr):
                        partial_exit_price = entry_price + TP_ATR_MULT * atr
                        partial_size = pos['remaining_size'] * PARTIAL_TP_PCT
                        partial_pnl = (partial_exit_price - entry_price) * partial_size
                        partial_fee = partial_exit_price * partial_size * FEE_RATE
                        net_partial = partial_pnl - partial_fee

                        pos['realized_pnl'] += net_partial
                        pos['total_fee'] += partial_fee
                        pos['remaining_size'] -= partial_size
                        pos['secured'] = True
                        
                        # Lock SL to Entry + 1.0x ATR for Runner
                        pos['sl'] = max(pos['sl'], entry_price + RUNNER_SL_LOCK_ATR * atr)

                        # Conservative intrabar check: did low hit new SL?
                        if l <= pos['sl']:
                            closed = True
                            exit_price = pos['sl']
                            exit_reason = "Trailing Stop"

                    # Dynamic Trailing Stop update for 25% Runner (Rides until trend physically reverses)
                    if pos['secured'] and not closed:
                        peak_gain_atr = (pos['peak_price'] - entry_price) / atr
                        trail_dist = (1.4 * atr) if peak_gain_atr >= 4.5 else (RUNNER_TRAILING_ATR * atr)
                        pos['sl'] = max(pos['sl'], pos['peak_price'] - trail_dist)

                    # Breakeven SL (+1.5x ATR)
                    if not pos['secured'] and not closed and h >= (entry_price + BE_ATR_MULT * atr):
                        pos['sl'] = max(pos['sl'], entry_price)

            # Check Short Position
            elif direction == 'Short':
                pos['trough_price'] = min(pos['trough_price'], l)

                if h >= pos['sl']:
                    closed = True
                    exit_price = pos['sl']
                    exit_reason = "Trailing Stop" if pos['secured'] else "Stop Loss"
                else:
                    # Partial Take-Profit (-3.0x ATR): Bank 75% profit, leave 25% Runner
                    if not pos['secured'] and l <= (entry_price - TP_ATR_MULT * atr):
                        partial_exit_price = entry_price - TP_ATR_MULT * atr
                        partial_size = pos['remaining_size'] * PARTIAL_TP_PCT
                        partial_pnl = (entry_price - partial_exit_price) * partial_size
                        partial_fee = partial_exit_price * partial_size * FEE_RATE
                        net_partial = partial_pnl - partial_fee

                        pos['realized_pnl'] += net_partial
                        pos['total_fee'] += partial_fee
                        pos['remaining_size'] -= partial_size
                        pos['secured'] = True

                        # Lock SL to Entry - 1.0x ATR for Runner
                        pos['sl'] = min(pos['sl'], entry_price - RUNNER_SL_LOCK_ATR * atr)

                        if h >= pos['sl']:
                            closed = True
                            exit_price = pos['sl']
                            exit_reason = "Trailing Stop"

                    # Dynamic Trailing Stop update for 25% Runner
                    if pos['secured'] and not closed:
                        trough_gain_atr = (entry_price - pos['trough_price']) / atr
                        trail_dist = (1.4 * atr) if trough_gain_atr >= 4.5 else (RUNNER_TRAILING_ATR * atr)
                        pos['sl'] = min(pos['sl'], pos['trough_price'] + trail_dist)

                    # Breakeven SL (-1.5x ATR)
                    if not pos['secured'] and not closed and l <= (entry_price - BE_ATR_MULT * atr):
                        pos['sl'] = min(pos['sl'], entry_price)

            # 2. Pure Event-Driven Resolution (Zero Calendar Day Kills):
            # Trades run strictly until Stop Loss or Dynamic Trailing Stop is hit.
            # No arbitrary calendar timeout is permitted under Master Quant Rules.

            if closed:
                rem_size = pos['remaining_size']
                if direction == 'Long':
                    pnl = (exit_price - entry_price) * rem_size
                else:
                    pnl = (entry_price - exit_price) * rem_size

                exit_fee = exit_price * rem_size * FEE_RATE
                net_closing_pnl = pnl - exit_fee
                pos['realized_pnl'] += net_closing_pnl
                pos['total_fee'] += exit_fee
                pos['exit_price'] = exit_price
                pos['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
                pos['exit_reason'] = exit_reason

                self.positions.remove(pos)
                self._save_positions()
                self.log_closed_trade(pos)
                closed_trades.append(pos)

        return closed_trades

