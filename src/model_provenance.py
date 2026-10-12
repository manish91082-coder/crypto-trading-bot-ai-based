"""Model provenance and promotion gates for the 1D pipeline.

Research candidates and production models are deliberately separate. A candidate
may be rejected while remaining available for research diagnostics. The paper
engine can load only a matching, explicitly promoted production bundle.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from config import FEATURE_COLS, MIN_WALK_FORWARD_OOS_AUC

MODEL_FILENAMES = {
    "Long": "Pooled_1d_XGB_Long.pkl",
    "Short": "Pooled_1d_XGB_Short.pkl",
}
REQUIRED_PRODUCTION_GATES = (
    "walk_forward_auc",
    "untouched_holdout",
    "net_profit_after_costs",
    "accounting_reconciliation",
    "feature_parity",
)


def sha256_file(path: Path) -> str:
    """Return SHA256 for the exact file bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assess_candidate_promotion_status(
    fold_auc_by_direction: Mapping[str, Sequence[float]],
    minimum_oos_auc: float = MIN_WALK_FORWARD_OOS_AUC,
) -> dict[str, object]:
    """Reject candidates that miss any required fold; never auto-promote candidates."""
    reasons: list[str] = []
    expected_directions = ("Long", "Short")
    for direction in expected_directions:
        scores = list(fold_auc_by_direction.get(direction, ()))
        if len(scores) != 4:
            reasons.append(
                f"{direction}: expected four walk-forward folds, observed {len(scores)}"
            )
            continue
        for index, raw_score in enumerate(scores, start=1):
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = float("nan")
            if not math.isfinite(score) or score <= minimum_oos_auc:
                reasons.append(
                    f"{direction} fold {index}: OOS AUC {score!r} must be > {minimum_oos_auc:.3f}"
                )

    rejected = bool(reasons)
    return {
        "promotion_status": "REJECTED" if rejected else "PENDING_HOLDOUT_AND_REVIEW",
        "strategy_acceptance_status": "FAIL" if rejected else "PENDING",
        "minimum_oos_auc_required": float(minimum_oos_auc),
        "fold_auc_by_direction": {
            direction: [float(x) for x in fold_auc_by_direction.get(direction, ())]
            for direction in expected_directions
        },
        "rejection_reasons": reasons,
        "automatic_promotion": False,
    }


def load_verified_production_model_paths(
    model_dir: Path,
    expected_feature_columns: Sequence[str] = FEATURE_COLS,
) -> dict[str, Path]:
    """Fail closed unless an explicit production manifest matches model bytes and gates."""
    model_dir = Path(model_dir)
    manifest_path = model_dir / "production_model_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(
            "Paper execution BLOCKED: production_model_manifest.json is missing. "
            "Research candidates are not production models; complete promotion gates first."
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Paper execution BLOCKED: invalid production manifest: {exc}") from exc

    if manifest.get("schema_version") != 1:
        raise RuntimeError("Paper execution BLOCKED: unsupported production manifest schema")
    if manifest.get("artifact_type") != "production":
        raise RuntimeError("Paper execution BLOCKED: model manifest is not a production bundle")
    if manifest.get("promotion_status") != "PROMOTED":
        raise RuntimeError(
            f"Paper execution BLOCKED: model promotion status is {manifest.get('promotion_status')!r}"
        )
    if manifest.get("strategy_acceptance_status") != "PASS":
        raise RuntimeError("Paper execution BLOCKED: strategy acceptance is not PASS")
    if manifest.get("feature_columns") != list(expected_feature_columns):
        raise RuntimeError("Paper execution BLOCKED: production model feature order/schema mismatch")

    gates = manifest.get("validation_gates")
    if not isinstance(gates, dict):
        raise RuntimeError("Paper execution BLOCKED: validation_gates is missing")
    failing_gates = [
        gate for gate in REQUIRED_PRODUCTION_GATES
        if gates.get(gate) != "PASS"
    ]
    if failing_gates:
        raise RuntimeError(
            "Paper execution BLOCKED: required promotion gates are not PASS: "
            + ", ".join(failing_gates)
        )

    listed_models = manifest.get("models")
    if not isinstance(listed_models, dict):
        raise RuntimeError("Paper execution BLOCKED: production model hashes are missing")

    paths: dict[str, Path] = {}
    for direction, filename in MODEL_FILENAMES.items():
        path = model_dir / filename
        record = listed_models.get(filename)
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Paper execution BLOCKED: model artifact missing/empty: {filename}")
        if not isinstance(record, dict) or not isinstance(record.get("sha256"), str):
            raise RuntimeError(f"Paper execution BLOCKED: manifest hash missing for {filename}")
        actual_hash = sha256_file(path)
        if actual_hash != record["sha256"]:
            raise RuntimeError(f"Paper execution BLOCKED: SHA256 mismatch for {filename}")
        paths[direction] = path
    return paths
