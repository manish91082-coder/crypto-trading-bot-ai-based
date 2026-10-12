import csv
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipeline_1d.step3_features_and_labels_7d import load_research_period_csv


class ResearchBoundaryTests(unittest.TestCase):
    def test_loader_stops_before_parsing_post_cutoff_prices(self):
        columns = ["timestamp", "open", "high", "low", "close", "volume"]
        research_rows = [
            ["2024-12-30", "100", "102", "99", "101", "1000"],
            ["2024-12-31", "101", "103", "100", "102", "1100"],
        ]
        holdout_rows = [
            ["2025-01-01", "NOT_A_PRICE", "NOT_A_PRICE", "NOT_A_PRICE", "NOT_A_PRICE", "NOT_VOLUME"],
            ["2025-01-02", "NOT_A_PRICE", "NOT_A_PRICE", "NOT_A_PRICE", "NOT_A_PRICE", "NOT_VOLUME"],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "boundary.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                writer.writerows(research_rows + holdout_rows)

            result = load_research_period_csv(path)

        self.assertEqual(len(result), 2)
        self.assertEqual(result["timestamp"].max(), pd.Timestamp("2024-12-31"))
        self.assertTrue((result["timestamp"] <= pd.Timestamp("2024-12-31")).all())
        self.assertTrue(pd.api.types.is_numeric_dtype(result["close"]))

    def test_loader_rejects_duplicate_or_out_of_order_research_timestamps(self):
        columns = ["timestamp", "open", "high", "low", "close", "volume"]
        rows = [
            ["2024-12-31", "101", "103", "100", "102", "1100"],
            ["2024-12-30", "100", "102", "99", "101", "1000"],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unordered.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                writer.writerows(rows)

            with self.assertRaises(ValueError):
                load_research_period_csv(path)


if __name__ == "__main__":
    unittest.main()
