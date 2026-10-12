import sys
from pathlib import Path
import pandas as pd
import numpy as np
import time

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    SYMBOLS,
    BINANCE_TAKER_FEE
)

# 4H QUANT MASTER BARRIERS & PARAMETERS
RESEARCH_END = "2024-12-31 20:00:00"  # Strict Research Vault: Only 2021-2024 touched for training
EVENT_BARRIER_CANDLES = 48            # 48 candles = 8 days max holding evaluation window
TP_MULT = 2.5                         # Target: +2.5x ATR
SL_MULT = 1.8                         # Stop: -1.8x ATR
FEE_RATE = BINANCE_TAKER_FEE          # 0.075% taker fee per side

FEATURE_COLS_4H = [
    'Ret_1', 'Ret_6', 'Ret_18', 'Synthetic_Order_Flow',
    'Upper_Wick_Ratio', 'Lower_Wick_Ratio', 'Vol_Z_Score',
    'ATR_Pct', 'Dist_EMA_50_ATR', 'Rel_Mom_vs_BTC',
    'SL_Dist_Ratio', 'Pullback_Depth', 'Vol_Accum_Ratio',
    'Regime_Z_Score', 'Volatility_Compression'
]

def compute_4h_stationary_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes stationary, normalized quant features specifically calibrated for 4H candles.
    Strictly causal - zero lookahead bias.
    """
    df = df.copy()

    # 1. Returns (1 candle = 4h, 6 candles = 1d, 18 candles = 3d)
    df['Ret_1'] = df['close'].pct_change(1)
    df['Ret_6'] = df['close'].pct_change(6)
    df['Ret_18'] = df['close'].pct_change(18)

    # 2. Intrabar Order Flow & Rejection Wicks
    bar_range = df['high'] - df['low'] + 1e-8
    df['Synthetic_Order_Flow'] = (df['close'] - df['open']) / bar_range
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / bar_range
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / bar_range

    # 3. Volume Z-Score (Rolling 36 candles = 6 days)
    vol_mean = df['volume'].rolling(36).mean()
    vol_std = df['volume'].rolling(36).std()
    df['Vol_Z_Score'] = (df['volume'] - vol_mean) / (vol_std + 1e-8)

    # 4. Normalized Volatility (14-period ATR % of price)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(14).mean()
    df['ATR_Pct'] = df['ATR_14'] / (df['close'] + 1e-8)

    # 5. Distance to 50 EMA in ATR units (50 candles = ~8.33 days intermediate trend)
    ema_50 = df['close'].ewm(span=50, adjust=False).mean()
    df['Dist_EMA_50_ATR'] = (df['close'] - ema_50) / (df['ATR_14'] + 1e-8)

    # 6. Physical Structural Risk Distance
    low_18 = df['low'].rolling(18).min()
    df['SL_Dist_Ratio'] = (df['close'] - (low_18 - 0.5 * df['ATR_14'])) / (df['close'] + 1e-8)

    # 7. Pullback Depth from 36-candle rolling high
    high_36 = df['high'].rolling(36).max()
    df['Pullback_Depth'] = (high_36 - df['close']) / (high_36 + 1e-8)

    # 8. Volume Accumulation Ratio (Rolling 36 candles)
    vol_sma36 = df['volume'].rolling(36).mean()
    df['Vol_Accum_Ratio'] = df['volume'] / (vol_sma36 + 1e-8)

    # 9. Macro Regime Z-Score (200 candles = ~33.3 days)
    sma200 = df['close'].rolling(200, min_periods=50).mean()
    std200 = df['close'].rolling(200, min_periods=50).std()
    df['Regime_Z_Score'] = (df['close'] - sma200) / (std200 + 1e-8)

    # 10. Volatility Compression Ratio (ATR_14 vs 72-candle ATR average)
    atr_sma72 = df['ATR_14'].rolling(72, min_periods=14).mean()
    df['Volatility_Compression'] = df['ATR_14'] / (atr_sma72 + 1e-8)

    return df


def generate_4h_triple_barrier_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Exact 4H Triple-Barrier Labeling:
    - Execution at T+1 Open.
    - TP = +2.5 * ATR, SL = -1.8 * ATR.
    - Max holding = EVENT_BARRIER_CANDLES (48 candles = 8 days).
    - If neither hit within 48 candles, exit at Open net of taker fees (0.075% * 2).
    - Pessimistic collision resolution: If both high >= TP and low <= SL on the same 4H candle, label = 0 (Loss).
    """
    df = df.copy()
    n = len(df)

    labels_long = np.zeros(n, dtype=int)
    labels_short = np.zeros(n, dtype=int)
    next_opens = np.zeros(n, dtype=float)

    opens = df['open'].values
    highs = df['high'].values
    lows = df['low'].values
    atrs = df['ATR_14'].values

    for i in range(n - EVENT_BARRIER_CANDLES - 1):
        entry_idx = i + 1
        entry_price = opens[entry_idx]
        next_opens[i] = entry_price
        atr = atrs[i]

        if np.isnan(atr) or atr <= 0:
            continue

        long_tp = entry_price + (TP_MULT * atr)
        long_sl = entry_price - (SL_MULT * atr)

        short_tp = entry_price - (TP_MULT * atr)
        short_sl = entry_price + (SL_MULT * atr)

        resolved_long = False
        resolved_short = False

        for c in range(1, EVENT_BARRIER_CANDLES + 1):
            curr_idx = entry_idx + c
            if curr_idx >= n:
                break

            h = highs[curr_idx]
            l = lows[curr_idx]

            # Long Barrier Check
            if not resolved_long:
                hit_sl = (l <= long_sl)
                hit_tp = (h >= long_tp)
                if hit_sl and hit_tp:
                    labels_long[i] = 0  # Pessimistic collision
                    resolved_long = True
                elif hit_sl:
                    labels_long[i] = 0
                    resolved_long = True
                elif hit_tp:
                    labels_long[i] = 1
                    resolved_long = True

            # Short Barrier Check
            if not resolved_short:
                hit_sl = (h >= short_sl)
                hit_tp = (l <= short_tp)
                if hit_sl and hit_tp:
                    labels_short[i] = 0  # Pessimistic collision
                    resolved_short = True
                elif hit_sl:
                    labels_short[i] = 0
                    resolved_short = True
                elif hit_tp:
                    labels_short[i] = 1
                    resolved_short = True

            if resolved_long and resolved_short:
                break

        # Timeout Exit if unhit within 48 candles
        timeout_idx = min(entry_idx + EVENT_BARRIER_CANDLES, n - 1)
        timeout_price = opens[timeout_idx]

        if not resolved_long:
            net_long_return = (timeout_price - entry_price) / entry_price - (2 * FEE_RATE)
            labels_long[i] = 1 if net_long_return > 0 else 0

        if not resolved_short:
            net_short_return = (entry_price - timeout_price) / entry_price - (2 * FEE_RATE)
            labels_short[i] = 1 if net_short_return > 0 else 0

    df['Next_Open'] = next_opens
    df['Label_Long'] = labels_long
    df['Label_Short'] = labels_short
    return df


def process_all_coins_4h():
    print("=" * 95)
    print("STEP 1.2: 4H STATIONARY FEATURE ENGINEERING & TRIPLE-BARRIER LABELING")
    print(f"Barriers: TP = +{TP_MULT}x ATR | SL = -{SL_MULT}x ATR | Timeout = {EVENT_BARRIER_CANDLES} Candles | Fee = 0.075%")
    print("=" * 95)

    start_time = time.time()

    # 1. Load BTC raw data to compute cross-asset Relative Momentum vs BTC
    btc_raw = pd.read_csv(DATA_RAW_DIR / "BTCUSDT_4h_Raw_5Years.csv")
    btc_raw['timestamp'] = pd.to_datetime(btc_raw['timestamp'])
    btc_raw = btc_raw.sort_values('timestamp').reset_index(drop=True)
    btc_ret_6_map = dict(zip(btc_raw['timestamp'], btc_raw['close'].pct_change(6)))

    summary = []

    for sym in SYMBOLS:
        raw_file = DATA_RAW_DIR / f"{sym}_4h_Raw_5Years.csv"
        if not raw_file.exists():
            print(f"[ERROR] Missing raw file for {sym}")
            continue

        df = pd.read_csv(raw_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Compute 4H Features
        df_feat = compute_4h_stationary_features(df)

        # Cross-asset relative momentum vs BTC (1-day window = 6 candles)
        btc_perf = df_feat['timestamp'].map(btc_ret_6_map).fillna(0.0)
        df_feat['Rel_Mom_vs_BTC'] = df_feat['Ret_6'] - btc_perf

        # Generate Triple-Barrier Labels
        df_labeled = generate_4h_triple_barrier_labels(df_feat)

        # Drop warmup rows (first 200 candles for SMA200 calculation)
        df_clean = df_labeled.iloc[200:].copy().reset_index(drop=True)

        # Save Full Processed Dataset (5 Years)
        full_out_path = DATA_PROCESSED_DIR / f"{sym}_4h_Processed_Features_Labels.csv"
        df_clean.to_csv(full_out_path, index=False)

        # Save Research Vault Dataset (Training Period <= 2024-12-31)
        research_df = df_clean[df_clean['timestamp'] <= RESEARCH_END].copy()
        research_out_path = DATA_PROCESSED_DIR / f"{sym}_4h_Research_Vault.csv"
        research_df.to_csv(research_out_path, index=False)

        # Holdout Dataset (Blind Period > 2024-12-31)
        holdout_df = df_clean[df_clean['timestamp'] > RESEARCH_END].copy()

        long_pos_rate = df_clean['Label_Long'].mean() * 100.0
        short_pos_rate = df_clean['Label_Short'].mean() * 100.0

        summary.append({
            'Symbol': sym,
            'Total_Candles': len(df_clean),
            'Research_Rows': len(research_df),
            'Holdout_Rows': len(holdout_df),
            'Long_Win%': f"{long_pos_rate:.1f}%",
            'Short_Win%': f"{short_pos_rate:.1f}%",
            'Null_Count': df_clean[FEATURE_COLS_4H].isnull().sum().sum()
        })
        print(f"  [PROCESSED] {sym:<10} | Total: {len(df_clean):>5} (Research: {len(research_df):>5}, Holdout: {len(holdout_df):>5}) | Long Win: {long_pos_rate:5.1f}% | Short Win: {short_pos_rate:5.1f}%")

    sum_df = pd.DataFrame(summary)
    elapsed = time.time() - start_time

    print("\n" + "=" * 95)
    print("STEP 1.2 AUDIT EVIDENCE: 4H PROCESSED VAULT SUMMARY")
    print("=" * 95)
    print(sum_df.to_string(index=False))
    print("-" * 95)
    print(f"Total Feature Rows Generated Across 10 Coins: {sum_df['Total_Candles'].sum():,}")
    print(f"Research Vault Training Samples              : {sum_df['Research_Rows'].sum():,}")
    print(f"Blind Holdout Exam Samples                   : {sum_df['Holdout_Rows'].sum():,}")
    print(f"Execution Time                               : {elapsed:.2f} seconds")
    print("=" * 95)

if __name__ == '__main__':
    process_all_coins_4h()
