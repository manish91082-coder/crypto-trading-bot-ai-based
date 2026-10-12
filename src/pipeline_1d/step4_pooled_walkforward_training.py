import sys
import os
import json
import importlib.metadata
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score
import joblib

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    DATA_PROCESSED_DIR,
    MODELS_1D_CANDIDATE_DIR,
    LOGS_DIR,
    SYMBOLS,
    FEATURE_COLS,
    PURGE_WINDOW_DAYS,
    LABEL_OBSERVATION_HORIZON_DAYS,
    MIN_WALK_FORWARD_OOS_AUC
)
from features_1d import validate_binary_target
from model_provenance import assess_candidate_promotion_status, sha256_file

def build_pooled_dataset():
    """Pools all 10 coins into a single unified dataset."""
    dfs = []
    for idx, sym in enumerate(SYMBOLS):
        f_path = DATA_PROCESSED_DIR / f"{sym}_1d_Features.csv"
        l_path = DATA_PROCESSED_DIR / f"{sym}_1d_Labeled.csv"

        df_f = pd.read_csv(f_path)
        df_l = pd.read_csv(l_path)

        df = pd.merge(df_f, df_l[['timestamp', 'Next_Open', 'Label_Long', 'Label_Short']], on='timestamp')
        df['Symbol'] = sym
        df['Coin_Code'] = idx
        dfs.append(df)

    pooled_df = pd.concat(dfs, ignore_index=True)
    pooled_df['timestamp'] = pd.to_datetime(pooled_df['timestamp'])
    pooled_df.sort_values('timestamp', inplace=True)
    pooled_df.reset_index(drop=True, inplace=True)
    return pooled_df

def run_purged_walk_forward_evaluation(pooled_df: pd.DataFrame, direction: str = 'Long'):
    """
    Executes expanding-window Purged Walk-Forward Cross-Validation.
    Compares Shallow XGBoost (depth 2) vs Logistic Regression Baseline.
    Purges the configured label observation window; censored unresolved labels are excluded from fitting.
    """
    label_col = f'Label_{direction}'
    print(f"\n--- RUNNING PURGED WALK-FORWARD EVALUATION: DIRECTION = {direction.upper()} (LABEL HORIZON = {LABEL_OBSERVATION_HORIZON_DAYS}d; PURGE = {PURGE_WINDOW_DAYS}d) ---")

    test_periods = [
        ('2023-01-01', '2023-06-30', '2023 H1'),
        ('2023-07-01', '2023-12-31', '2023 H2'),
        ('2024-01-01', '2024-06-30', '2024 H1'),
        ('2024-07-01', '2024-12-31', '2024 H2'),
    ]

    fold_results = []

    for t_start, t_end, name in test_periods:
        dt_start = pd.to_datetime(t_start)
        dt_end = pd.to_datetime(t_end)

        # Train: all data strictly before (dt_start - PURGE_WINDOW_DAYS)
        train_cutoff = dt_start - pd.Timedelta(days=PURGE_WINDOW_DAYS)
        train_data = pooled_df[pooled_df['timestamp'] < train_cutoff].dropna(subset=FEATURE_COLS + [label_col])
        test_data = pooled_df[(pooled_df['timestamp'] >= dt_start) & (pooled_df['timestamp'] <= dt_end)].dropna(subset=FEATURE_COLS + [label_col])

        X_train, y_train = train_data[FEATURE_COLS], train_data[label_col]
        X_test, y_test = test_data[FEATURE_COLS], test_data[label_col]

        try:
            validate_binary_target(y_train, f"{name} training fold")
            validate_binary_target(y_test, f"{name} test fold")
        except ValueError as exc:
            print(f"  [{name}] SKIPPED: {exc}")
            continue

        # 1. Baseline Model: Logistic Regression
        lr = LogisticRegression(max_iter=500, C=0.1, random_state=42)
        lr.fit(X_train, y_train)
        lr_probs = lr.predict_proba(X_test)[:, 1]
        lr_auc = roc_auc_score(y_test, lr_probs)

        # 2. Shallow Regularized XGBoost (Capacity controlled: Depth 2, L2=5.0)
        xgb_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=2,
            learning_rate=0.03,
            reg_lambda=5.0,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
            n_jobs=1
        )
        xgb_model.fit(X_train, y_train)
        xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
        xgb_auc = roc_auc_score(y_test, xgb_probs)
        if not np.isfinite(xgb_probs).all():
            raise RuntimeError(f"{name}: XGBoost produced non-finite OOS probabilities")

        high_conf_mask = (xgb_probs > 0.55)
        high_conf_prec = precision_score(y_test[high_conf_mask], np.ones(high_conf_mask.sum()), zero_division=0) if high_conf_mask.sum() > 0 else 0.0

        fold_results.append({
            'Period': name,
            'Train_Samples': len(X_train),
            'Test_Samples': len(X_test),
            'Target_Positive_Rate': float(y_test.mean()),
            'LR_OOS_AUC': lr_auc,
            'XGB_OOS_AUC': xgb_auc,
            'XGB_Prob_Min': float(np.min(xgb_probs)),
            'XGB_Prob_Median': float(np.median(xgb_probs)),
            'XGB_Prob_P90': float(np.quantile(xgb_probs, 0.90)),
            'XGB_Prob_Max': float(np.max(xgb_probs)),
            'XGB_Prob_Count_GE_042': int((xgb_probs >= 0.42).sum()),
            'XGB_Prob_Count_GE_044': int((xgb_probs >= 0.44).sum()),
            'XGB_Prob_Count_GE_046': int((xgb_probs >= 0.46).sum()),
            'High_Conf_Trades': int(high_conf_mask.sum()),
            'High_Conf_Precision': float(high_conf_prec)
        })

        print(f"  [{name}] Train: {len(X_train):>5} | Test: {len(X_test):>4} | Target+: {y_test.mean()*100:.1f}% | LR AUC: {lr_auc:.3f} | XGB AUC: {xgb_auc:.3f} | P50/P90/Max: {np.median(xgb_probs):.3f}/{np.quantile(xgb_probs,0.90):.3f}/{np.max(xgb_probs):.3f} | N>=.42/.44/.46: {(xgb_probs>=.42).sum()}/{(xgb_probs>=.44).sum()}/{(xgb_probs>=.46).sum()}")

    df_folds = pd.DataFrame(fold_results)
    if len(df_folds) != len(test_periods):
        observed = df_folds["Period"].tolist() if "Period" in df_folds.columns else []
        raise RuntimeError(
            f"{direction} walk-forward incomplete: expected {len(test_periods)} folds, "
            f"got {len(df_folds)} ({observed}). No incomplete CV result may be accepted."
        )
    metric_columns = ["LR_OOS_AUC", "XGB_OOS_AUC"]
    if df_folds[metric_columns].isna().any().any() or not np.isfinite(df_folds[metric_columns].to_numpy(dtype=float)).all():
        raise RuntimeError(f"{direction} walk-forward contains non-finite AUC results")
    if (df_folds[["Train_Samples", "Test_Samples"]] <= 0).any().any():
        raise RuntimeError(f"{direction} walk-forward contains empty train/test folds")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fold_path = LOGS_DIR / f"step4_walkforward_{direction.lower()}.csv"
    df_folds.to_csv(fold_path, index=False)
    print(f"[EVIDENCE] Saved all {len(df_folds)} {direction} walk-forward folds to {fold_path.name}")

    mean_xgb_auc = df_folds["XGB_OOS_AUC"].mean()
    mean_lr_auc = df_folds["LR_OOS_AUC"].mean()
    print(f"\n=> MEAN OOS AUC across all folds: XGBoost = {mean_xgb_auc:.3f} | Logistic Regression = {mean_lr_auc:.3f}")
    return df_folds

def train_and_save_candidate_pooled_models(
    pooled_df: pd.DataFrame,
    fold_results_by_direction: dict[str, pd.DataFrame],
):
    """Train research candidates without overwriting production model artifacts."""
    candidate_dir = MODELS_1D_CANDIDATE_DIR
    candidate_dir.mkdir(parents=True, exist_ok=True)
    model_names = [
        "Pooled_1d_XGB_Long.pkl",
        "Pooled_1d_XGB_Short.pkl",
    ]
    for model_name in model_names:
        (candidate_dir / model_name).unlink(missing_ok=True)
    (candidate_dir / "candidate_model_manifest.json").unlink(missing_ok=True)

    print("\\n=================================================================")
    print("TRAINING 1D RESEARCH CANDIDATES (NOT PRODUCTION MODELS)")
    print("=================================================================")

    candidate_models = {}
    for direction in ("Long", "Short"):
        label_col = f"Label_{direction}"
        clean_df = pooled_df.dropna(subset=FEATURE_COLS + [label_col])
        y = clean_df[label_col]
        try:
            validate_binary_target(y, f"candidate {direction} model")
        except ValueError as exc:
            raise RuntimeError(
                f"Refusing to train candidate {direction} model: {exc}"
            ) from exc

        X = clean_df[FEATURE_COLS]
        model = xgb.XGBClassifier(
            n_estimators=120,
            max_depth=2,
            learning_rate=0.03,
            reg_lambda=5.0,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="logloss",
            n_jobs=1,
        )
        model.fit(X, y)

        importance = pd.Series(
            model.feature_importances_, index=FEATURE_COLS
        ).sort_values(ascending=False)
        print(f"\\n[RESEARCH CANDIDATE {direction.upper()}] Feature Importances:")
        for feature, value in importance.items():
            print(f"  {feature:<25}: {value:.4f}")

        out_path = candidate_dir / f"Pooled_1d_XGB_{direction}.pkl"
        joblib.dump(model, out_path)
        candidate_models[out_path.name] = {
            "sha256": sha256_file(out_path),
            "bytes": out_path.stat().st_size,
            "training_rows": int(len(clean_df)),
            "resolved_positive_rate": float(y.mean()),
        }
        print(f"[CANDIDATE ONLY] Saved {out_path.name}; production directory untouched.")

    auc_by_direction = {
        direction: folds["XGB_OOS_AUC"].astype(float).tolist()
        for direction, folds in fold_results_by_direction.items()
    }
    assessment = assess_candidate_promotion_status(
        auc_by_direction,
        minimum_oos_auc=MIN_WALK_FORWARD_OOS_AUC,
    )

    source_hashes = {}
    for symbol in SYMBOLS:
        for suffix in ("Features.csv", "Labeled.csv"):
            source_path = DATA_PROCESSED_DIR / f"{symbol}_1d_{suffix}"
            if not source_path.is_file():
                raise FileNotFoundError(
                    f"Cannot evidence candidate provenance; missing {source_path.name}"
                )
            source_hashes[source_path.name] = sha256_file(source_path)

    package_versions = {}
    for package in ("numpy", "pandas", "scikit-learn", "xgboost", "joblib"):
        package_versions[package] = importlib.metadata.version(package)

    manifest = {
        "schema_version": 1,
        "artifact_type": "research_candidate",
        "model_family": "pooled_xgboost",
        "timeframe": "1d",
        "promotion_status": assessment["promotion_status"],
        "strategy_acceptance_status": assessment["strategy_acceptance_status"],
        "automatic_promotion": False,
        "minimum_oos_auc_required": MIN_WALK_FORWARD_OOS_AUC,
        "walk_forward_auc_by_direction": assessment["fold_auc_by_direction"],
        "rejection_reasons": assessment["rejection_reasons"],
        "feature_columns": list(FEATURE_COLS),
        "label_observation_horizon_days": LABEL_OBSERVATION_HORIZON_DAYS,
        "purge_window_days": PURGE_WINDOW_DAYS,
        "training_data_start": str(pd.to_datetime(pooled_df["timestamp"]).min().date()),
        "training_data_end": str(pd.to_datetime(pooled_df["timestamp"]).max().date()),
        "git_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "model_files": candidate_models,
        "processed_data_sha256": source_hashes,
        "package_versions": package_versions,
        "production_artifacts_modified": False,
    }
    manifest_path = candidate_dir / "candidate_model_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_manifest = LOGS_DIR / "step4_candidate_model_manifest.json"
    log_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(f"[CANDIDATE GATE] {assessment['promotion_status']}")
    for reason in assessment["rejection_reasons"]:
        print(f"  [GATE EVIDENCE] {reason}")
    print(f"[EVIDENCE] Candidate manifest saved to {manifest_path.name}")
    return manifest

def main():
    print("=================================================================")
    print("STEP 4: POOLED MULTI-ASSET TRAINING & PURGED WALK-FORWARD CV")
    print(f"Zero-Trust Institutional Quant Standard (Purge = {PURGE_WINDOW_DAYS}d)")
    print("=================================================================")

    pooled_df = build_pooled_dataset()
    print(f"Total Pooled Samples across 10 Coins: {len(pooled_df)} candles")
    print(f"Date Range: {pooled_df['timestamp'].min().strftime('%Y-%m-%d')} to {pooled_df['timestamp'].max().strftime('%Y-%m-%d')}")

    # Evaluate Long side
    df_long_folds = run_purged_walk_forward_evaluation(pooled_df, direction='Long')

    # Evaluate Short side
    df_short_folds = run_purged_walk_forward_evaluation(pooled_df, direction='Short')

    # Train candidate artifacts only; never overwrite promoted production models.
    train_and_save_candidate_pooled_models(
        pooled_df,
        fold_results_by_direction={"Long": df_long_folds, "Short": df_short_folds},
    )

    print("\n=================================================================")
    print("STEP 4 COMPLETED: POOLED WALK-FORWARD EVALUATION & MODELS TRAINED")
    print("=================================================================")

if __name__ == '__main__':
    main()

