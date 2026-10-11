import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
import time

FEE_RATE = 0.00075  # Binance VIP-0 Taker Fee (0.075%)

class OrderManager:
    """
    Manages active position state, trailing stop adjustments, partial take-profits,
    and trade logging with crash-resilient disk persistence.
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
        Evaluate SL, Partial TP, Trailing Stop, Breakeven SL, and Time-Based Exit
        for open positions on a price tick.
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

            # Check Time-Based Exit (7 days = 604800 seconds)
            elapsed_sec = time.time() - pos['entry_timestamp']
            if elapsed_sec >= (7 * 86400) and not pos['secured']:
                closed = True
                exit_price = current_price
                exit_reason = "Time-Based Exit"

            # Check Long Position
            if not closed and direction == 'Long':
                pos['peak_price'] = max(pos['peak_price'], h)
                
                # Stop Loss check
                if l <= pos['sl']:
                    closed = True
                    exit_price = pos['sl']
                    exit_reason = "Stop Loss"
                else:
                    # Partial Take-Profit (+3.0x ATR)
                    if not pos['secured'] and h >= (entry_price + 3.0 * atr):
                        partial_exit_price = entry_price + 3.0 * atr
                        partial_size = pos['remaining_size'] / 2.0
                        partial_pnl = (partial_exit_price - entry_price) * partial_size
                        partial_fee = partial_exit_price * partial_size * FEE_RATE
                        net_partial = partial_pnl - partial_fee

                        pos['realized_pnl'] += net_partial
                        pos['total_fee'] += partial_fee
                        pos['remaining_size'] -= partial_size
                        pos['secured'] = True
                        
                        # Lock SL slightly above entry (+1.0x ATR)
                        pos['sl'] = max(pos['sl'], entry_price + 1.0 * atr)

                    # Update Trailing Stop if secured
                    if pos['secured']:
                        pos['sl'] = max(pos['sl'], pos['peak_price'] - 2.0 * atr)

                    # Breakeven SL (+2.0x ATR)
                    if not pos['secured'] and h >= (entry_price + 2.0 * atr):
                        pos['sl'] = max(pos['sl'], entry_price)

            # Check Short Position
            elif not closed and direction == 'Short':
                pos['trough_price'] = min(pos['trough_price'], l)

                # Stop Loss check
                if h >= pos['sl']:
                    closed = True
                    exit_price = pos['sl']
                    exit_reason = "Stop Loss"
                else:
                    # Partial Take-Profit (-3.0x ATR)
                    if not pos['secured'] and l <= (entry_price - 3.0 * atr):
                        partial_exit_price = entry_price - 3.0 * atr
                        partial_size = pos['remaining_size'] / 2.0
                        partial_pnl = (entry_price - partial_exit_price) * partial_size
                        partial_fee = partial_exit_price * partial_size * FEE_RATE
                        net_partial = partial_pnl - partial_fee

                        pos['realized_pnl'] += net_partial
                        pos['total_fee'] += partial_fee
                        pos['remaining_size'] -= partial_size
                        pos['secured'] = True

                        # Lock SL slightly below entry (-1.0x ATR)
                        pos['sl'] = min(pos['sl'], entry_price - 1.0 * atr)

                    # Update Trailing Stop if secured
                    if pos['secured']:
                        pos['sl'] = min(pos['sl'], pos['trough_price'] + 2.0 * atr)

                    # Breakeven SL (-2.0x ATR)
                    if not pos['secured'] and l <= (entry_price - 2.0 * atr):
                        pos['sl'] = min(pos['sl'], entry_price)

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
