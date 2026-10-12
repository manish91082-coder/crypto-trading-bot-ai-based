import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import FEATURE_COLS, MIN_WALK_FORWARD_OOS_AUC
from model_provenance import (
    MODEL_FILENAMES,
    assess_candidate_promotion_status,
    load_verified_production_model_paths,
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ModelPromotionGateTests(unittest.TestCase):
    def make_production_bundle(self, directory):
        models = {}
        for filename in MODEL_FILENAMES.values():
            path = directory / filename
            path.write_bytes(("fixture:" + filename).encode("utf-8"))
            models[filename] = {"sha256": sha256(path), "bytes": path.stat().st_size}
        gates = {
            "walk_forward_auc": "PASS",
            "untouched_holdout": "PASS",
            "net_profit_after_costs": "PASS",
            "accounting_reconciliation": "PASS",
            "feature_parity": "PASS",
        }
        manifest = {
            "schema_version": 1,
            "artifact_type": "production",
            "timeframe": "1d",
            "promotion_status": "PROMOTED",
            "strategy_acceptance_status": "PASS",
            "feature_columns": list(FEATURE_COLS),
            "validation_gates": gates,
            "models": models,
        }
        (directory / "production_model_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        return manifest

    def test_missing_production_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "manifest.json is missing"):
                load_verified_production_model_paths(Path(tmp))

    def test_rejected_candidate_cannot_be_loaded_as_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            manifest = self.make_production_bundle(directory)
            manifest["artifact_type"] = "research_candidate"
            manifest["promotion_status"] = "REJECTED"
            manifest["strategy_acceptance_status"] = "FAIL"
            (directory / "production_model_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "not a production bundle"):
                load_verified_production_model_paths(directory)

    def test_pending_candidate_cannot_be_auto_promoted(self):
        result = assess_candidate_promotion_status({
            "Long": [0.61, 0.60, 0.59, 0.63],
            "Short": [0.58, 0.59, 0.57, 0.62],
        })
        self.assertEqual(result["promotion_status"], "PENDING_HOLDOUT_AND_REVIEW")
        self.assertEqual(result["strategy_acceptance_status"], "PENDING")
        self.assertFalse(result["automatic_promotion"])

    def test_any_auc_at_or_below_required_floor_rejects_candidate(self):
        result = assess_candidate_promotion_status({
            "Long": [0.61, MIN_WALK_FORWARD_OOS_AUC, 0.59, 0.63],
            "Short": [0.58, 0.59, 0.57, 0.62],
        })
        self.assertEqual(result["promotion_status"], "REJECTED")
        self.assertEqual(result["strategy_acceptance_status"], "FAIL")
        self.assertTrue(result["rejection_reasons"])

    def test_incomplete_fold_set_rejects_candidate(self):
        result = assess_candidate_promotion_status({
            "Long": [0.61, 0.60, 0.59],
            "Short": [0.58, 0.59, 0.57, 0.62],
        })
        self.assertEqual(result["promotion_status"], "REJECTED")

    def test_production_bundle_requires_every_validation_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            manifest = self.make_production_bundle(directory)
            manifest["validation_gates"]["untouched_holdout"] = "PENDING"
            (directory / "production_model_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "untouched_holdout"):
                load_verified_production_model_paths(directory)

    def test_feature_order_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            manifest = self.make_production_bundle(directory)
            manifest["feature_columns"] = list(reversed(FEATURE_COLS))
            (directory / "production_model_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "feature order/schema mismatch"):
                load_verified_production_model_paths(directory)

    def test_model_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            manifest = self.make_production_bundle(directory)
            model_path = directory / MODEL_FILENAMES["Long"]
            model_path.write_bytes(b"tampered after manifest creation")
            (directory / "production_model_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "SHA256 mismatch"):
                load_verified_production_model_paths(directory)

    def test_valid_manifest_returns_both_verified_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.make_production_bundle(directory)
            paths = load_verified_production_model_paths(directory)
            self.assertEqual(set(paths), {"Long", "Short"})
            self.assertTrue(paths["Long"].is_file())
            self.assertTrue(paths["Short"].is_file())


if __name__ == "__main__":
    unittest.main()
