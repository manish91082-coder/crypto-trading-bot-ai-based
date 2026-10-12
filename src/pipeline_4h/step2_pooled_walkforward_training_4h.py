import sys
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score
import joblib
import time

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    DATA_PROCESSED_DIR,
    MODELS_4H_POOLED_DIR,
    SYMBOLS
)

# 4H QUANT MASTER FEATURES
FEATURE_COLS_4H = [
    'Ret_1', 'Ret_6', 'Ret_18', 'Synthetic_Order_Flow',
    'Upper_Wick_Ratio', 'Lower_Wick_Ratio', 'Vol_Z_Score',
    'ATR_Pct', 'Dist_EMA_50_ATR', 'Rel_Mom_vs_BTC',
    'SL_Dist_Ratio', 'Pullback_Depth', 'Vol_Accum_Ratio',
    'Regime_Z_Score', 'Volatility_Compression'
]

PURGE_WINDOW_DAYS_4H = 8  # 48 candles = 8 days max holding purge window

def build_4h_pooled_research_dataset() -> pd.DataFrame:
    """Pools all 10 coins' Research Vault datasets (2021-2024) into a unified dataset."""
    dfs = []
    for idx, sym in enumerate(SYMBOLS):
        vault_path = DATA_PROCESSED_DIR / f"{sym}_4h_Research_Vault.csv"
        if not vault_path.exists():
            raise FileNotFoundError(f"Missing 4H Research Vault file: {vault_path}")

        df = pd.read_csv(vault_path)
        df['Symbol'] = sym
        df['Coin_Code'] = idx
        dfs.append(df)

    pooled_df = pd.concat(dfs, ignore_index=True)
    pooled_df['timestamp'] = pd.to_datetime(pooled_df['timestamp'])
    pooled_df = pooled_df.sort_values('timestamp').reset_index(drop=True)
    return pooled_df


def run_purged_walk_forward_evaluation_4h(pooled_df: pd.DataFrame, direction: str = 'Long'):
    """
    Executes expanding-window Purged Walk-Forward Cross-Validation on 4H candles.
    Enforces 8-day purge window (48 candles) to eliminate lookahead bias.
    Compares Capacity-Controlled Regularized XGBoost vs Logistic Regression Baseline.
    """
    label_col = f'Label_{direction}'
    print(f"\n--- PURGED WALK-FORWARD CROSS-VALIDATION: 4H {direction.upper()} (Purge Window = {PURGE_WINDOW_DAYS_4H} days) ---")

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

        # Train: all data strictly before (dt_start - PURGE_WINDOW_DAYS_4H)
        train_cutoff = dt_start - pd.Timedelta(days=PURGE_WINDOW_DAYS_4H)
        train_data = pooled_df[pooled_df['timestamp'] <= train_cutoff].dropna(subset=FEATURE_COLS_4H)
        test_data = pooled_df[(pooled_df['timestamp'] >= dt_start) & (pooled_df['timestamp'] <= dt_end)].dropna(subset=FEATURE_COLS_4H)

        X_train, y_train = train_data[FEATURE_COLS_4H], train_data[label_col]
        X_test, y_test = test_data[FEATURE_COLS_4H], test_data[label_col]

        if len(y_test.unique()) < 2:
            continue

        # 1. Baseline Model: Logistic Regression
        lr = LogisticRegression(max_iter=500, C=0.1, random_state=42)
        lr.fit(X_train, y_train)
        lr_probs = lr.predict_proba(X_test)[:, 1]
        lr_auc = roc_auc_score(y_test, lr_probs)

        # 2. Regularized XGBoost (Capacity controlled: depth 3, max_iter 120, reg_lambda 5.0)
        xgb_model = xgb.XGBClassifier(
            n_estimators=120,
            max_depth=3,
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

        # Quality check: High-confidence precision (P > 0.44)
        high_conf_mask = (xgb_probs >= 0.44)
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

        print(f"  [{name}] Train: {len(X_train):>5} | Test: {len(X_test):>5} | LR AUC: {lr_auc:.3f} | XGB OOS AUC: {xgb_auc:.3f} | P>=0.44 Precision: {high_conf_prec*100:5.1f}% ({high_conf_mask.sum():>4} trades)")

    df_folds = pd.DataFrame(fold_results)
    mean_xgb_auc = df_folds['XGB_OOS_AUC'].mean()
    mean_lr_auc = df_folds['LR_OOS_AUC'].mean()
    print(f"\n=> MEAN OUT-OF-SAMPLE AUC across all 4 folds: XGBoost = {mean_xgb_auc:.3f} | Logistic Baseline = {mean_lr_auc:.3f}")
    return df_folds


def train_and_save_final_4h_models(pooled_df: pd.DataFrame):
    """
    Trains final pooled 4H production models on the entire Research Vault (2021-2024, 69,280 samples)
    and saves to models/4h_pooled/.
    """
    print("\n=================================================================")
    print("TRAINING FINAL POOLED 4H PRODUCTION MODELS (69,280 SAMPLES, DEPTH 3, L2=5.0)")
    print("=================================================================")

    MODELS_4H_POOLED_DIR.mkdir(parents=True, exist_ok=True)

    for direction in ['Long', 'Short']:
        label_col = f'Label_{direction}'
        clean_df = pooled_df.dropna(subset=FEATURE_COLS_4H + [label_col])

        X = clean_df[FEATURE_COLS_4H]
        y = clean_df[label_col]

        model = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=3,
            learning_rate=0.03,
            reg_lambda=5.0,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
        model.fit(X, y)

        # Feature importances
        imp = pd.Series(model.feature_importances_, index=FEATURE_COLS_4H).sort_values(ascending=False)
        print(f"\n[4H POOLED {direction.upper()} MODEL] Feature Importances:")
        for feat, val in imp.items():
            print(f"  {feat:<25}: {val:.4f}")

        # Save model
        out_path = MODELS_4H_POOLED_DIR / f"Pooled_4h_XGB_{direction}.pkl"
        joblib.dump(model, out_path)
        print(f"[*] Successfully saved 4H production model: '{out_path.name}'")


def main():
    print("=" * 95)
    print("STEP 2: 4H POOLED WALK-FORWARD TRAINING & EVALUATION (2021-2024)")
    print(f"Institutional Zero-Trust Protocol | Purge Window = {PURGE_WINDOW_DAYS_4H} days (48 candles)")
    print("=" * 95)

    start_time = time.time()
    pooled_df = build_4h_pooled_research_dataset()
    print(f"Total 4H Research Vault Samples Across 10 Coins: {len(pooled_df):,} candles")
    print(f"Vault Date Range: {pooled_df['timestamp'].min().strftime('%Y-%m-%d %H:%M')} to {pooled_df['timestamp'].max().strftime('%Y-%m-%d %H:%M')}")

    # 1. Walk-forward cross validation on Long side
    df_long_folds = run_purged_walk_forward_evaluation_4h(pooled_df, direction='Long')

    # 2. Walk-forward cross validation on Short side
    df_short_folds = run_purged_walk_forward_evaluation_4h(pooled_df, direction='Short')

    # 3. Train and persist final production models
    train_and_save_final_4h_models(pooled_df)

    elapsed = time.time() - start_time
    print("\n" + "=" * 95)
    print(f"STEP 2 COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS")
    print("Models saved in: models/4h_pooled/Pooled_4h_XGB_Long.pkl & Pooled_4h_XGB_Short.pkl")
    print("=" * 95)

if __name__ == '__main__':
    main()
