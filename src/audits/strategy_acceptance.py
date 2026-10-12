"""Research acceptance gates derived from the repository's documented criteria.

This module never certifies live readiness. A research gate failure is evidence to
fix; it must not be hidden by the fact that a simulation command exited successfully.
"""
from __future__ import annotations

from math import isfinite
from typing import Mapping, Sequence


def evaluate_1d_research_gate(
    fold_auc_by_direction: Mapping[str, Sequence[float]],
    selected_spot_trades_by_capital: Mapping[str, int],
    configuration_trade_counts_by_scenario: Mapping[str, Mapping[str, int]],
    minimum_oos_auc: float = 0.52,
) -> dict[str, object]:
    """Evaluate walk-forward AUC and whether the primary spot strategy can trade."""
    reasons: list[str] = []
    auc_failures: dict[str, list[dict[str, object]]] = {}
    for direction in ("long", "short"):
        scores = list(fold_auc_by_direction.get(direction, ()))
        if len(scores) != 4:
            auc_failures[direction] = [
                {"reason": "incomplete_fold_count", "observed": len(scores), "expected": 4}
            ]
            continue
        bad = [
            {"fold_index": i, "xgb_oos_auc": float(score)}
            for i, score in enumerate(scores)
            if not isfinite(float(score)) or float(score) <= minimum_oos_auc
        ]
        if bad:
            auc_failures[direction] = bad

    if auc_failures:
        reasons.append(
            f"walk-forward AUC criterion not met: every one of four folds per direction "
            f"must be > {minimum_oos_auc:.2f}"
        )

    spot_10k = int(selected_spot_trades_by_capital.get("capital_10000", 0))
    if spot_10k <= 0:
        reasons.append("primary $10,000 spot configuration produced zero closed trades")

    all_config_counts = [
        int(count)
        for counts in configuration_trade_counts_by_scenario.values()
        for count in counts.values()
    ]
    if all_config_counts and max(all_config_counts) == 0:
        reasons.append("all tested spot/futures thresholds produced zero trades in both capital scenarios")

    return {
        "research_gate_status": "FAIL" if reasons else "PASS",
        "minimum_oos_auc_required": float(minimum_oos_auc),
        "walk_forward_auc_gate": "FAIL" if auc_failures else "PASS",
        "walk_forward_auc_failures": auc_failures,
        "primary_spot_tradeability_gate": "FAIL" if spot_10k <= 0 else "PASS",
        "primary_spot_trades_at_10000": spot_10k,
        "all_configuration_trade_counts": {
            scenario: {name: int(count) for name, count in counts.items()}
            for scenario, counts in configuration_trade_counts_by_scenario.items()
        },
        "reasons": reasons,
        "full_strategy_acceptance": "NOT_CERTIFIED: sealed holdout/live gates are outside this research-only workflow",
    }
