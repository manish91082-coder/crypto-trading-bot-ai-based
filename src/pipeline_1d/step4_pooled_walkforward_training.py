import sys
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
    MODELS_DIR,
    MODELS_1D_POOLED_DIR,
    SYMBOLS,
    FEATURE_COLS,
    PURGE_WINDOW_DAYS,
    LABEL_OBSERVATION_HORIZON_DAYS
)
from features_1d import validate_binary_target

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
            eval_metric='logloss'
        )
        xgb_model.fit(X_train, y_train)
        xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
        xgb_auc = roc_auc_score(y_test, xgb_probs)

        high_conf_mask = (xgb_probs > 0.55)
        high_conf_prec = precision_score(y_test[high_conf_mask], np.ones(high_conf_mask.sum()), zero_division=0) if high_conf_mask.sum() > 0 else 0.0

        fold_results.append({
            'Period': name,
            'Train_Samples': len(X_train),
            'Test_Samples': len(X_test),
            'LR_OOS_AUC': lr_auc,
            'XGB_OOS_AUC': xgb_auc,
            'High_Conf_Trades': high_conf_mask.sum(),
            'High_Conf_Precision': high_conf_prec
        })

        print(f"  [{name}] Train: {len(X_train):>5} | Test: {len(X_test):>4} | LR AUC: {lr_auc:.3f} | XGB OOS AUC: {xgb_auc:.3f} | Conf>0.55 Prec: {high_conf_prec*100:.1f}% ({high_conf_mask.sum()} trades)")

    df_folds = pd.DataFrame(fold_results)
    mean_xgb_auc = df_folds['XGB_OOS_AUC'].mean()
    mean_lr_auc = df_folds['LR_OOS_AUC'].mean()
    print(f"\n=> MEAN OOS AUC across all folds: XGBoost = {mean_xgb_auc:.3f} | Logistic Regression = {mean_lr_auc:.3f}")
    return df_folds

def train_and_save_final_pooled_models(pooled_df: pd.DataFrame):
    """
    Trains final pooled production models on the entire Research Period (up to 2024-12-31)
    with shallow depth 2 and strong L2 regularization.
    """
    print("\n=================================================================")
    print("TRAINING FINAL POOLED 1D PRODUCTION MODELS (DEPTH 2, L2=5.0)")
    print("=================================================================")

    for direction in ['Long', 'Short']:
        label_col = f'Label_{direction}'
        clean_df = pooled_df.dropna(subset=FEATURE_COLS + [label_col])
        y = clean_df[label_col]
        try:
            validate_binary_target(y, f"final pooled {direction} model")
        except ValueError as exc:
            raise RuntimeError(
                f"Refusing to train final pooled {direction} model: {exc}"
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
            eval_metric='logloss'
        )
        model.fit(X, y)

        # Feature importances
        imp = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
        print(f"\n[POOLED {direction.upper()} MODEL] Feature Importances:")
        for feat, val in imp.items():
            print(f"  {feat:<25}: {val:.4f}")

        # Save model
        out_path = MODELS_1D_POOLED_DIR / f"Pooled_1d_XGB_{direction}.pkl"
        joblib.dump(model, out_path)
        print(f"[*] Saved final production model to '{out_path.name}'")

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

    # Train and save production models
    train_and_save_final_pooled_models(pooled_df)

    print("\n=================================================================")
    print("STEP 4 COMPLETED: POOLED WALK-FORWARD EVALUATION & MODELS TRAINED")
    print("=================================================================")

if __name__ == '__main__':
    main()

