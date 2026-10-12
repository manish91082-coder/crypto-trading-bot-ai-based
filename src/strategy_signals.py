"""Shared 1D spot-entry signal gate used by research backtest and paper engine.

The configured probability threshold is a hard floor in every macro regime.
Bear regimes additionally require positive relative momentum or a documented
pullback/stop-distance/volume-confluence condition. This module makes that rule
testable so threshold variants cannot silently collapse to a fixed 0.42 floor.
"""
from __future__ import annotations

import math
from typing import Tuple


def should_enter_spot_long(
    probability: float,
    threshold: float,
    btc_bullish: bool,
    relative_momentum: float,
    pullback_depth: float,
    stop_distance_ratio: float,
    volume_accumulation_ratio: float,
) -> Tuple[bool, str]:
    """Return (decision, reason) for the existing long-only spot regime doctrine."""
    try:
        p = float(probability)
        floor = float(threshold)
    except (TypeError, ValueError):
        return False, "BLOCKED: probability/threshold is not numeric"

    if not math.isfinite(p) or not math.isfinite(floor) or not (0.0 <= floor <= 1.0):
        return False, "BLOCKED: probability/threshold is non-finite or outside [0, 1]"
    if p < floor:
        return False, f"Filtered: P({p:.3f}) < configured threshold {floor:.3f}"

    def finite_at_least(value: float, limit: float) -> bool:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(v) and v >= limit

    def finite_at_most(value: float, limit: float) -> bool:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(v) and v <= limit

    if bool(btc_bullish):
        return True, "Bull regime candidate: configured probability threshold met"

    if finite_at_least(relative_momentum, 0.0):
        return True, "Bear regime relative-momentum candidate: configured threshold met"

    pullback_confluence = (
        finite_at_least(pullback_depth, 0.08)
        or finite_at_most(stop_distance_ratio, 0.065)
        or finite_at_least(volume_accumulation_ratio, 1.05)
    )
    if pullback_confluence:
        return True, "Bear regime pullback/confluence candidate: configured threshold met"

    return False, "Filtered: bear regime requires relative momentum or documented confluence"
