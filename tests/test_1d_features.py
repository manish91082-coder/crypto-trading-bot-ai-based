import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import FEATURE_COLS
from features_1d import (
    add_relative_momentum_vs_btc,
    compute_1d_base_features,
    validate_binary_target,
)
from pipeline_1d.step3_features_and_labels_7d import compute_stationary_features
from execution.paper_engine import PaperExecutionEngine


def candle_frame(length=260, base=100.0, volatility=1.0, volume_base=500.0):
    index = np.arange(length, dtype=float)
    close = base + index * 0.08 + 2.0 * np.sin(index / 7.0)
    open_price = close * (1.0 + 0.001 * np.sin(index / 3.0))
    high = np.maximum(open_price, close) + 0.5 * volatility
    low = np.minimum(open_price, close) - 0.5 * volatility
    volume = volume_base + (index % 11) * 7.0 + 10.0 * np.cos(index / 9.0)
    timestamps = pd.date_range("2021-01-01", periods=length, freq="D")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


def to_exchange_ohlcv(frame):
    timestamp_ms = frame["timestamp"].astype("int64") // 1_000_000
    return [
        [int(timestamp_ms.iloc[i]), float(frame["open"].iloc[i]),
         float(frame["high"].iloc[i]), float(frame["low"].iloc[i]),
         float(frame["close"].iloc[i]), float(frame["volume"].iloc[i])]
        for i in range(len(frame))
    ]


class OneDayFeatureParityTests(unittest.TestCase):
    def test_training_and_paper_features_match_for_every_model_feature(self):
        target = candle_frame(base=100.0, volatility=1.0, volume_base=500.0)
        btc = candle_frame(base=30000.0, volatility=20.0, volume_base=30000.0)

        research = compute_stationary_features(target)
        research = add_relative_momentum_vs_btc(research, btc)

        raw = {
            "ETHUSDT": to_exchange_ohlcv(target),
            "BTCUSDT": to_exchange_ohlcv(btc),
        }
        engine = PaperExecutionEngine.__new__(PaperExecutionEngine)
        paper = engine.compute_live_features(raw, "ETHUSDT")

        np.testing.assert_allclose(
            research[FEATURE_COLS].to_numpy(dtype=float),
            paper[FEATURE_COLS].to_numpy(dtype=float),
            rtol=0.0,
            atol=1e-12,
            equal_nan=True,
        )

    def test_missing_btc_alignment_is_not_silently_zero_filled(self):
        target = candle_frame()
        engine = PaperExecutionEngine.__new__(PaperExecutionEngine)
        paper = engine.compute_live_features(
            {"ETHUSDT": to_exchange_ohlcv(target)}, "ETHUSDT"
        )
        self.assertTrue(paper["Rel_Mom_vs_BTC"].isna().all())

    def test_canonical_rolling_windows_require_training_warmup(self):
        frame = candle_frame()
        result = compute_1d_base_features(frame)
        self.assertTrue(pd.isna(result.loc[12, "SL_Dist_Ratio"]))
        self.assertTrue(pd.isna(result.loc[28, "Pullback_Depth"]))
        self.assertTrue(np.isfinite(result.loc[29, "Pullback_Depth"]))
        self.assertTrue(np.isfinite(result.loc[29, "Regime_Z_Score"]))

    def test_invalid_ohlc_is_rejected(self):
        frame = candle_frame(length=40)
        frame.loc[10, "high"] = frame.loc[10, "low"] - 1.0
        with self.assertRaises(ValueError):
            compute_1d_base_features(frame)

    def test_training_target_fails_closed_for_empty_or_single_class_data(self):
        with self.assertRaises(ValueError):
            validate_binary_target([], "test")
        with self.assertRaises(ValueError):
            validate_binary_target([1, 1, 1], "test")
        validate_binary_target([0, 1, 0, 1], "test")


if __name__ == "__main__":
    unittest.main()
