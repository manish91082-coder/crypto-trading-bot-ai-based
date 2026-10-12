import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline_1d.step3_features_and_labels_7d import (
    LABEL_OBSERVATION_HORIZON_DAYS,
    generate_triple_barrier_labels,
)


class TripleBarrierLabelTests(unittest.TestCase):
    def make_frame(self, length=None):
        if length is None:
            length = LABEL_OBSERVATION_HORIZON_DAYS + 3
        return pd.DataFrame({
            "open": np.full(length, 100.0),
            "high": np.full(length, 100.5),
            "low": np.full(length, 99.5),
            "close": np.full(length, 100.0),
            "volume": np.full(length, 1000.0),
            "ATR_14": np.full(length, 1.0),
        })

    def test_entry_candle_is_checked_after_t_plus_one_open(self):
        frame = self.make_frame()
        frame.loc[1, "high"] = 104.0  # 3 ATR target is reached on entry candle
        result = generate_triple_barrier_labels(frame)
        self.assertEqual(result.loc[0, "Label_Long"], 1.0)

    def test_same_candle_stop_and_target_collision_is_pessimistic(self):
        frame = self.make_frame()
        frame.loc[1, "high"] = 104.0
        frame.loc[1, "low"] = 98.0  # crosses the initial 1.5 ATR stop too
        result = generate_triple_barrier_labels(frame)
        self.assertEqual(result.loc[0, "Label_Long"], 0.0)
        self.assertEqual(result.loc[0, "Label_Short"], 0.0)

    def test_break_even_stop_is_checked_conservatively(self):
        frame = self.make_frame()
        frame.loc[1, "high"] = 102.0
        frame.loc[1, "low"] = 99.5
        result = generate_triple_barrier_labels(frame)
        self.assertEqual(result.loc[0, "Label_Long"], 0.0)

        frame = self.make_frame()
        frame.loc[1, "high"] = 100.5
        frame.loc[1, "low"] = 98.0
        result = generate_triple_barrier_labels(frame)
        self.assertEqual(result.loc[0, "Label_Short"], 0.0)

    def test_unresolved_example_is_censored_not_time_exited(self):
        horizon = LABEL_OBSERVATION_HORIZON_DAYS
        frame = self.make_frame(horizon + 3)
        outside_window_idx = 1 + horizon
        # A profitable price move appears only after the observation window.
        frame.loc[outside_window_idx, ["open", "high", "low", "close"]] = [
            120.0, 120.5, 119.5, 120.0
        ]
        result = generate_triple_barrier_labels(frame)
        self.assertTrue(pd.isna(result.loc[0, "Label_Long"]))
        self.assertTrue(pd.isna(result.loc[0, "Label_Short"]))

    def test_incomplete_tail_rows_are_not_assigned_default_losses(self):
        horizon = LABEL_OBSERVATION_HORIZON_DAYS
        frame = self.make_frame(horizon + 3)
        result = generate_triple_barrier_labels(frame)
        self.assertTrue(pd.isna(result.loc[len(frame) - horizon, "Label_Long"]))
        self.assertTrue(pd.isna(result.loc[len(frame) - 1, "Label_Short"]))


if __name__ == "__main__":
    unittest.main()
