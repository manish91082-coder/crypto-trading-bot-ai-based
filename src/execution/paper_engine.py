import sys
from pathlib import Path
import time
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

# Dynamic relative path setup
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import MODELS_1D_AGGRESSIVE_DIR, LOGS_DIR, SYMBOLS
from risk_governor import RiskGovernor
from execution.binance_client import BinanceExecutionClient
from execution.order_manager import OrderManager

class PaperExecutionEngine:
    """
    Zero-Trust Real-Time Paper Trading & Binance Testnet Execution Engine.
    
    1. Fetches real-time candles directly from Binance via CCXT.
    2. Computes pure mathematical features on live closed candles (No retail indicators).
    3. Runs trained XGBoost & Meta-Models for all 10 coins.
    4. Evaluates risk via Institutional RiskGovernor (drawdown scaling, exposure caps).
    5. Dispatches fills to Binance Testnet or local persistent paper journal.
    6. Trailing stops and trade closures execute continuously with disk persistence.
    """

    def __init__(
        self,
        initial_capital: float = 120.0,
        meta_threshold: float = 0.80,
        use_testnet: bool = True
    ):
        self.initial_capital = initial_capital
        self.meta_threshold = meta_threshold
        self.client = BinanceExecutionClient(use_testnet=use_testnet)
        self.order_mgr = OrderManager(logs_dir=LOGS_DIR)
        
        # Load Risk Governor
        self.risk_gov = RiskGovernor(
            initial_capital=initial_capital,
            base_risk_pct=0.05,
            max_concurrent_trades=3,
            max_portfolio_risk_pct=0.12,
            dd_tier_1=0.10,
            dd_tier_2=0.20,
            dd_tier_3=0.35,
            min_risk_pct=0.015
        )
        
        # Current Paper Capital
        self.current_capital = self._calculate_current_capital()
        self.risk_gov.update_capital(self.current_capital)

    def _calculate_current_capital(self) -> float:
        """Calculate current equity including realized PnL from closed trades."""
        realized_total = 0.0
        if self.order_mgr.trade_log_file.exists():
            try:
                df = pd.read_csv(self.order_mgr.trade_log_file)
                if not df.empty and 'realized_pnl' in df.columns:
                    realized_total = df['realized_pnl'].sum()
            except Exception:
                pass
        return max(10.0, self.initial_capital + realized_total)

    def compute_live_features(self, ohlcv_data: list) -> pd.DataFrame:
        """
        Transform raw Binance OHLCV candles into exact mathematical features.
        Zero lookahead bias.
        """
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.sort_values('timestamp', inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Returns
        df['Ret_1'] = df['close'].pct_change(1)
        df['Ret_3'] = df['close'].pct_change(3)
        df['Ret_5'] = df['close'].pct_change(5)

        # Synthetic Order Flow
        df['Synthetic_Order_Flow'] = (df['close'] - df['open']) / (df['high'] - df['low'] + 1e-8)

        # Volume Z-Score
        vol_mean = df['volume'].rolling(20).mean()
        vol_std = df['volume'].rolling(20).std()
        df['Vol_Z_Score'] = (df['volume'] - vol_mean) / (vol_std + 1e-8)

        # Trend Distances
        sma_50 = df['close'].rolling(50).mean()
        sma_200 = df['close'].rolling(200).mean()
        df['Dist_SMA_50'] = (df['close'] - sma_50) / (sma_50 + 1e-8)
        df['Dist_SMA_200'] = (df['close'] - sma_200) / (sma_200 + 1e-8)

        # ATR 14
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift(1)).abs()
        tr3 = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(14).mean()

        return df

    def scan_and_execute_cycle(self) -> Dict[str, Any]:
        """
        Execute one complete operational cycle across all 10 coins.
        1. Updates existing positions with live prices.
        2. Evaluates signals on latest completed candle.
        3. Sizes and opens new positions via RiskGovernor.
        """
        cycle_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{cycle_time}] Starting Paper Engine Cycle across 10 Coins...")
        
        # 1. Update Existing Positions
        closed_in_cycle = []
        for pos in self.order_mgr.positions[:]:
            sym = pos['symbol']
            try:
                live_price = self.client.fetch_ticker_price(sym)
                closed = self.order_mgr.update_positions_on_tick(sym, live_price)
                if closed:
                    closed_in_cycle.extend(closed)
                    for c in closed:
                        self.current_capital += c['realized_pnl']
                        self.risk_gov.update_capital(self.current_capital)
                        print(f"  [EXIT] Closed {sym} | Reason: {c['exit_reason']} | PnL: ${c['realized_pnl']:.2f}")
            except Exception as e:
                print(f"  [WARN] Failed to update tick for {sym}: {e}")

        # 2. Scan Signals for All Coins
        features = ['Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow', 'Vol_Z_Score', 'Dist_SMA_50', 'Dist_SMA_200']
        candidates = []

        open_symbols = [p['symbol'] for p in self.order_mgr.positions]

        for symbol in SYMBOLS:
            if symbol in open_symbols:
                continue

            try:
                # Fetch recent daily candles (220 candles needed for 200 SMA)
                ohlcv = self.client.fetch_recent_ohlcv(symbol, timeframe='1d', limit=220)
                if len(ohlcv) < 205:
                    continue

                df_feat = self.compute_live_features(ohlcv)
                # Last completed candle is iloc[-2] (iloc[-1] is currently active/uncompleted)
                completed_candle = df_feat.iloc[-2]

                X_input = pd.DataFrame([completed_candle[features].values], columns=features)

                # Check Long & Short Models
                for direction in ['Long', 'Short']:
                    model_path = MODELS_1D_AGGRESSIVE_DIR / f'{symbol}_1d_Temp_XGB_{direction}.pkl'
                    meta_path = MODELS_1D_AGGRESSIVE_DIR / f'{symbol}_1d_Temp_Meta_{direction}.pkl'
                    if not model_path.exists() or not meta_path.exists():
                        continue

                    model = joblib.load(model_path)
                    meta = joblib.load(meta_path)

                    p = model.predict_proba(X_input)[0][1]
                    meta_X = pd.DataFrame({
                        'Primary_Confidence': [p],
                        'Vol_Z_Score': [completed_candle['Vol_Z_Score']],
                        'Dist_SMA_200': [completed_candle['Dist_SMA_200']]
                    })
                    meta_conf = meta.predict_proba(meta_X)[0][1]

                    if meta_conf > self.meta_threshold:
                        live_price = self.client.fetch_ticker_price(symbol)
                        atr = float(completed_candle['ATR_14'])
                        sl = live_price - (1.5 * atr) if direction == 'Long' else live_price + (1.5 * atr)

                        candidates.append({
                            'symbol': symbol,
                            'direction': direction,
                            'confidence': meta_conf,
                            'entry_price': live_price,
                            'sl': sl,
                            'atr': atr
                        })

            except Exception as e:
                print(f"  [ERROR] Scanning {symbol}: {e}")

        # 3. Sort candidates by conviction and submit to Risk Governor
        candidates.sort(key=lambda c: c['confidence'], reverse=True)
        newly_opened = []

        for cand in candidates:
            decision = self.risk_gov.evaluate_entry(
                current_capital=self.current_capital,
                entry_price=cand['entry_price'],
                stop_loss=cand['sl'],
                open_trades=self.order_mgr.positions,
                atr=cand['atr']
            )

            if decision.approved:
                # Execute order through Binance client (Testnet or Live Paper)
                order_side = 'buy' if cand['direction'] == 'Long' else 'sell'
                order_res = self.client.execute_market_order(
                    symbol=cand['symbol'],
                    side=order_side,
                    amount=decision.position_size
                )

                # Register position in order manager
                pos = self.order_mgr.add_position(
                    symbol=cand['symbol'],
                    direction=cand['direction'],
                    entry_price=order_res['fill_price'],
                    position_size=decision.position_size,
                    risk_amount=decision.risk_amount,
                    stop_loss=cand['sl'],
                    atr=cand['atr']
                )
                newly_opened.append(pos)
                print(f"  [ENTRY] Opened {cand['direction']} on {cand['symbol']} @ {order_res['fill_price']:.2f} | Size: {decision.position_size:.4f} | Risk: {decision.risk_pct*100:.2f}% (${decision.risk_amount:.2f})")
            else:
                print(f"  [FILTER] {cand['symbol']} {cand['direction']} Rejected by Risk Governor: {decision.reason}")

        return {
            'timestamp': cycle_time,
            'capital': self.current_capital,
            'drawdown': self.risk_gov.current_drawdown,
            'open_positions': len(self.order_mgr.positions),
            'newly_opened': len(newly_opened),
            'closed_trades': len(closed_in_cycle)
        }

if __name__ == '__main__':
    engine = PaperExecutionEngine(initial_capital=120.0, meta_threshold=0.80, use_testnet=True)
    summary = engine.scan_and_execute_cycle()
    print("\n--- CYCLE SUMMARY ---")
    print(summary)
