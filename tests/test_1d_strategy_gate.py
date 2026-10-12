import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audits.strategy_acceptance import evaluate_1d_research_gate


class OneDayStrategyGateTests(unittest.TestCase):
    def test_gate_fails_when_any_walk_forward_fold_misses_auc_floor(self):
        result = evaluate_1d_research_gate(
            fold_auc_by_direction={
                "long": [0.63, 0.51, 0.55, 0.54],
                "short": [0.61, 0.58, 0.57, 0.53],
            },
            selected_spot_trades_by_capital={
                "capital_120": 5,
                "capital_10000": 50,
            },
            configuration_trade_counts_by_scenario={
                "capital_120": {"spot": 5, "futures": 10},
                "capital_10000": {"spot": 50, "futures": 80},
            },
            minimum_oos_auc=0.52,
        )
        self.assertEqual(result["walk_forward_auc_gate"], "FAIL")
        self.assertEqual(result["research_gate_status"], "FAIL")

    def test_gate_fails_when_primary_10000_spot_replay_has_no_trades(self):
        result = evaluate_1d_research_gate(
            fold_auc_by_direction={
                "long": [0.63, 0.53, 0.55, 0.54],
                "short": [0.61, 0.58, 0.57, 0.53],
            },
            selected_spot_trades_by_capital={
                "capital_120": 0,
                "capital_10000": 0,
            },
            configuration_trade_counts_by_scenario={
                "capital_120": {"spot_042": 0, "spot_044": 0, "spot_046": 0, "futures": 0},
                "capital_10000": {"spot_042": 0, "spot_044": 0, "spot_046": 0, "futures": 0},
            },
            minimum_oos_auc=0.52,
        )
        self.assertEqual(result["primary_spot_tradeability_gate"], "FAIL")
        self.assertEqual(result["research_gate_status"], "FAIL")
        self.assertTrue(any("zero trades" in reason for reason in result["reasons"]))

    def test_research_gate_can_pass_without_claiming_live_readiness(self):
        result = evaluate_1d_research_gate(
            fold_auc_by_direction={
                "long": [0.63, 0.53, 0.55, 0.54],
                "short": [0.61, 0.58, 0.57, 0.53],
            },
            selected_spot_trades_by_capital={
                "capital_120": 5,
                "capital_10000": 50,
            },
            configuration_trade_counts_by_scenario={
                "capital_120": {"spot_042": 4, "spot_044": 5, "spot_046": 2, "futures_044": 10},
                "capital_10000": {"spot_042": 40, "spot_044": 50, "spot_046": 20, "futures_044": 80},
            },
            minimum_oos_auc=0.52,
        )
        self.assertEqual(result["research_gate_status"], "PASS")
        self.assertIn("NOT_CERTIFIED", result["full_strategy_acceptance"])


if __name__ == "__main__":
    unittest.main()
