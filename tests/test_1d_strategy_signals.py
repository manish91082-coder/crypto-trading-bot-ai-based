import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from strategy_signals import should_enter_spot_long


class SpotEntryThresholdTests(unittest.TestCase):
    def test_bull_regime_does_not_enter_below_configured_threshold(self):
        decision, _ = should_enter_spot_long(
            probability=0.423, threshold=0.44, btc_bullish=True,
            relative_momentum=0.1, pullback_depth=0.2,
            stop_distance_ratio=0.04, volume_accumulation_ratio=1.2,
        )
        self.assertFalse(decision)

    def test_bear_regime_does_not_bypass_threshold_with_old_042_fallback(self):
        decision, reason = should_enter_spot_long(
            probability=0.423, threshold=0.44, btc_bullish=False,
            relative_momentum=-0.1, pullback_depth=0.2,
            stop_distance_ratio=0.04, volume_accumulation_ratio=1.2,
        )
        self.assertFalse(decision)
        self.assertIn("configured threshold", reason)

    def test_bear_relative_momentum_requires_hard_threshold_first(self):
        decision, _ = should_enter_spot_long(
            probability=0.44, threshold=0.44, btc_bullish=False,
            relative_momentum=0.01, pullback_depth=0.01,
            stop_distance_ratio=0.2, volume_accumulation_ratio=0.5,
        )
        self.assertTrue(decision)

    def test_bear_negative_relative_momentum_requires_threshold_and_confluence(self):
        below_threshold, _ = should_enter_spot_long(
            probability=0.419, threshold=0.42, btc_bullish=False,
            relative_momentum=-0.01, pullback_depth=0.10,
            stop_distance_ratio=0.04, volume_accumulation_ratio=1.2,
        )
        no_confluence, _ = should_enter_spot_long(
            probability=0.44, threshold=0.44, btc_bullish=False,
            relative_momentum=-0.01, pullback_depth=0.01,
            stop_distance_ratio=0.20, volume_accumulation_ratio=0.5,
        )
        valid_confluence, _ = should_enter_spot_long(
            probability=0.44, threshold=0.44, btc_bullish=False,
            relative_momentum=-0.01, pullback_depth=0.10,
            stop_distance_ratio=0.20, volume_accumulation_ratio=0.5,
        )
        self.assertFalse(below_threshold)
        self.assertFalse(no_confluence)
        self.assertTrue(valid_confluence)

    def test_non_finite_probability_fails_closed(self):
        decision, reason = should_enter_spot_long(
            probability=float("nan"), threshold=0.42, btc_bullish=True,
            relative_momentum=0.0, pullback_depth=0.1,
            stop_distance_ratio=0.05, volume_accumulation_ratio=1.1,
        )
        self.assertFalse(decision)
        self.assertIn("BLOCKED", reason)


if __name__ == "__main__":
    unittest.main()
