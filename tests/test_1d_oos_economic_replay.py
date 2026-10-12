import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audits.oos_economic_replay import build_fold_master, read_raw_through_cutoff


class OosEconomicReplayBoundaryTests(unittest.TestCase):
    def test_fold_master_masks_scores_after_last_horizon_safe_signal_date(self):
        dates = pd.date_range("2023-01-01", "2023-01-16", freq="D")
        market = pd.DataFrame({
            "timestamp": dates,
            "Symbol": ["BTCUSDT"] * len(dates),
            "open": np.full(len(dates), 100.0),
            "high": np.full(len(dates), 102.0),
            "low": np.full(len(dates), 99.0),
            "close": np.full(len(dates), 101.0),
            "volume": np.full(len(dates), 1000.0),
            "ATR_14": np.full(len(dates), 1.0),
            "Vol_Accum_Ratio": np.full(len(dates), 1.0),
            "Rel_Mom_vs_BTC": np.zeros(len(dates)),
            "Pullback_Depth": np.zeros(len(dates)),
            "SL_Dist_Ratio": np.full(len(dates), 0.1),
        })
        base = pd.DataFrame({
            "timestamp": dates,
            "Symbol": ["BTCUSDT"] * len(dates),
            "Fold": ["2023 H1"] * len(dates),
            "Direction": ["Long"] * len(dates),
            "OOS_Probability": np.full(len(dates), 0.45),
            "Label_Long": np.zeros(len(dates)),
        })
        short = base[["timestamp", "Symbol", "Fold", "OOS_Probability"]].copy()
        short["Direction"] = "Short"
        short["Label_Short"] = np.zeros(len(short))

        master, metadata = build_fold_master(
            market,
            base,
            short,
            pd.Timestamp("2023-01-01"),
            pd.Timestamp("2023-01-16"),
        )
        by_date = master.set_index("timestamp")
        self.assertTrue(np.isfinite(by_date.loc[pd.Timestamp("2023-01-01"), "p_long"]))
        self.assertTrue(np.isfinite(by_date.loc[pd.Timestamp("2023-01-02"), "p_long"]))
        self.assertTrue(by_date.loc[pd.Timestamp("2023-01-03"):,"p_long"].isna().all())
        self.assertEqual(metadata["last_allowed_signal_date"], "2023-01-02")

    def test_mismatched_long_short_oos_rows_are_rejected(self):
        dates = pd.date_range("2023-01-01", "2023-01-16", freq="D")
        market = pd.DataFrame({
            "timestamp": dates,
            "Symbol": ["BTCUSDT"] * len(dates),
            "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000.0,
            "ATR_14": 1.0, "Vol_Accum_Ratio": 1.0, "Rel_Mom_vs_BTC": 0.0,
            "Pullback_Depth": 0.0, "SL_Dist_Ratio": 0.1,
        })
        long = pd.DataFrame({
            "timestamp": dates, "Symbol": ["BTCUSDT"] * len(dates),
            "OOS_Probability": 0.45, "Label_Long": 0.0,
        })
        short = long.iloc[:-1].copy().rename(columns={"Label_Long": "Label_Short"})
        with self.assertRaisesRegex(ValueError, "sample keys do not match"):
            build_fold_master(
                market, long, short, pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-16")
            )

    def test_raw_stream_stops_before_parsing_post_cutoff_prices(self):
        import csv
        import tempfile

        columns = ["timestamp", "open", "high", "low", "close", "volume"]
        rows = [
            ["2023-01-01", "100", "102", "99", "101", "1000"],
            ["2023-01-02", "101", "103", "100", "102", "1100"],
            ["2023-01-03", "INVALID", "INVALID", "INVALID", "INVALID", "INVALID"],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "raw.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                writer.writerows(rows)
            df = read_raw_through_cutoff(path, pd.Timestamp("2023-01-02"))
        self.assertEqual(len(df), 2)
        self.assertEqual(df["timestamp"].max(), pd.Timestamp("2023-01-02"))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["close"]))


if __name__ == "__main__":
    unittest.main()
