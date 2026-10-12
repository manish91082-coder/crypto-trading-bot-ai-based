import sys
from pathlib import Path
import pandas as pd
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    SYMBOLS,
    LABEL_OBSERVATION_HORIZON_DAYS,
    BE_ATR_MULT,
    TP_ATR_MULT,
    SL_ATR_MULT,
    MACRO_BTC_EMA_PERIOD
)

RESEARCH_END = "2024-12-31"       # Strict Vault Rule: Only research period touched
TP_MULT = TP_ATR_MULT             # Matches execution partial TP (+3.0x ATR)
SL_MULT = SL_ATR_MULT             # Matches execution initial SL (-1.5x ATR)

def compute_stationary_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineers stationary, normalized quant features.
    Strictly causal (no lookahead).
    """
    df = df.copy()
    
    # 1. Short-term returns
    df['Ret_1'] = df['close'].pct_change(1)
    df['Ret_3'] = df['close'].pct_change(3)
    df['Ret_5'] = df['close'].pct_change(5)

    # 2. Intrabar Order Flow & Rejection Wicks
    bar_range = df['high'] - df['low'] + 1e-8
    df['Synthetic_Order_Flow'] = (df['close'] - df['open']) / bar_range
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / bar_range
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / bar_range

    # 3. Volume Z-Score (Rolling 20-day)
    vol_mean = df['volume'].rolling(20).mean()
    vol_std = df['volume'].rolling(20).std()
    df['Vol_Z_Score'] = (df['volume'] - vol_mean) / (vol_std + 1e-8)

    # 4. Normalized Volatility (ATR% of price)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(14).mean()
    df['ATR_Pct'] = df['ATR_14'] / (df['close'] + 1e-8)

    # 5. Stationary Momentum (Normalized Distance to 20 EMA in ATR units)
    ema_20 = df['close'].ewm(span=MACRO_BTC_EMA_PERIOD, adjust=False).mean()
    df['Dist_EMA_20_ATR'] = (df['close'] - ema_20) / (df['ATR_14'] + 1e-8)

    # 6. Physical Structural Risk Distance (SL_Dist_Ratio)
    low_14 = df['low'].rolling(14).min()
    df['SL_Dist_Ratio'] = (df['close'] - (low_14 - 0.5 * df['ATR_14'])) / (df['close'] + 1e-8)

    # 7. Selling Exhaustion Pullback Depth (Pullback_Depth)
    high_30 = df['high'].rolling(30).max()
    df['Pullback_Depth'] = (high_30 - df['close']) / (high_30 + 1e-8)

    # 8. Smart Money Volume Accumulation (Vol_Accum_Ratio)
    vol_sma20 = df['volume'].rolling(20).mean()
    df['Vol_Accum_Ratio'] = df['volume'] / (vol_sma20 + 1e-8)

    # 9. Macro Regime Z-Score (Regime_Z_Score)
    sma200 = df['close'].rolling(200, min_periods=30).mean()
    std200 = df['close'].rolling(200, min_periods=30).std()
    df['Regime_Z_Score'] = (df['close'] - sma200) / (std200 + 1e-8)

    # 10. Volatility Compression Ratio (Volatility_Compression)
    atr_sma50 = df['ATR_14'].rolling(50, min_periods=14).mean()
    df['Volatility_Compression'] = df['ATR_14'] / (atr_sma50 + 1e-8)

    return df


def generate_triple_barrier_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Label outcomes observed within the configured initial evaluation window.

    Entry is at T+1 open. The entry candle is included because its movement occurs
    after the open fill. Initial stop is evaluated before target; a same-candle
    stop/target collision is pessimistically negative. The break-even stop is
    activated after +BE_ATR_MULT and is checked conservatively against that
    candle's opposite extreme.

    A target touch means the strategy's 75% partial take-profit event succeeded.
    A stop or break-even exit is negative after fees. If neither outcome resolves
    within the observation window, the label is censored (NaN), not fabricated
    from an arbitrary calendar-time exit. This window never closes a live runner.
    """
    df = df.copy()
    n = len(df)
    horizon = LABEL_OBSERVATION_HORIZON_DAYS

    labels_long = np.full(n, np.nan, dtype=float)
    labels_short = np.full(n, np.nan, dtype=float)
    next_opens = np.full(n, np.nan, dtype=float)

    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    atrs = df["ATR_14"].to_numpy(dtype=float)

    # Need one signal candle plus a complete horizon of post-entry candles.
    for i in range(max(0, n - horizon)):
        entry_idx = i + 1
        entry_price = opens[entry_idx]
        next_opens[i] = entry_price
        atr = atrs[i]

        if not np.isfinite(atr) or atr <= 0 or not np.isfinite(entry_price) or entry_price <= 0:
            continue

        long_target = entry_price + TP_MULT * atr
        long_stop = entry_price - SL_MULT * atr
        long_break_even_trigger = entry_price + BE_ATR_MULT * atr

        short_target = entry_price - TP_MULT * atr
        short_stop = entry_price + SL_MULT * atr
        short_break_even_trigger = entry_price - BE_ATR_MULT * atr

        long_resolved = False
        short_resolved = False

        # Include the entry candle (T+1) and observe exactly 'horizon' daily bars.
        for offset in range(horizon):
            idx = entry_idx + offset
            high = highs[idx]
            low = lows[idx]

            if not long_resolved:
                hit_stop = low <= long_stop
                hit_target = high >= long_target
                if hit_stop and hit_target:
                    labels_long[i] = 0.0
                    long_resolved = True
                elif hit_stop:
                    labels_long[i] = 0.0
                    long_resolved = True
                elif hit_target:
                    labels_long[i] = 1.0
                    long_resolved = True
                elif high >= long_break_even_trigger:
                    # Once +1.5 ATR is reached, the stop ratchets to entry.
                    long_stop = max(long_stop, entry_price)
                    # Conservative OHLC treatment: assume an activated stop can be hit.
                    if low <= long_stop:
                        labels_long[i] = 0.0
                        long_resolved = True

            if not short_resolved:
                hit_stop = high >= short_stop
                hit_target = low <= short_target
                if hit_stop and hit_target:
                    labels_short[i] = 0.0
                    short_resolved = True
                elif hit_stop:
                    labels_short[i] = 0.0
                    short_resolved = True
                elif hit_target:
                    labels_short[i] = 1.0
                    short_resolved = True
                elif low <= short_break_even_trigger:
                    short_stop = min(short_stop, entry_price)
                    if high >= short_stop:
                        labels_short[i] = 0.0
                        short_resolved = True

            if long_resolved and short_resolved:
                break

        # Unresolved examples intentionally remain NaN and are dropped from supervised training.

    df["Next_Open"] = next_opens
    df["Label_Long"] = labels_long
    df["Label_Short"] = labels_short
    # Legacy column names retained for downstream compatibility; they do not define the horizon.
    df["Label_Long_7d"] = labels_long
    df["Label_Short_7d"] = labels_short
    return df

def process_all_coins():
    print("=================================================================")
    print(f"STEP 3: {LABEL_OBSERVATION_HORIZON_DAYS}-CANDLE INITIAL-EVALUATION LABELING")
    print("Adversarial Anti-Overfitting Protocol: Law #6 Aligned")
    print("=================================================================")

    # 1. First load BTC to calculate cross-asset relative strength
    btc_raw = pd.read_csv(DATA_RAW_DIR / "BTCUSDT_1d_Raw_5Years.csv")
    btc_raw['timestamp'] = pd.to_datetime(btc_raw['timestamp'])
    btc_research = btc_raw[btc_raw['timestamp'] <= RESEARCH_END].sort_values('timestamp').reset_index(drop=True)
    btc_ret_5 = btc_research['close'].pct_change(5).values

    summary = []

    for symbol in SYMBOLS:
        raw_file = DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv"
        df = pd.read_csv(raw_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['timestamp'] <= RESEARCH_END].sort_values('timestamp').reset_index(drop=True)

        # Assert no data leakage past 2024
        assert df['timestamp'].max() <= pd.to_datetime(RESEARCH_END), "LEAKAGE: Research data touches 2025!"

        # Features
        df = compute_stationary_features(df)
        
        # Cross-Asset relative momentum vs BTC
        if len(df) == len(btc_ret_5):
            df['Rel_Mom_vs_BTC'] = df['Ret_5'] - btc_ret_5
        else:
            df['Rel_Mom_vs_BTC'] = df['Ret_5']

        # Labels (Exact matched horizon)
        df = generate_triple_barrier_labels(df)

        # Drop warmup rows (first 35 rows due to 30-day pullback depth and rolling indicators)
        # Remove rows without enough future candles to complete the configured observation window.
        clean_df = df.iloc[35:-LABEL_OBSERVATION_HORIZON_DAYS].copy()

        # Save clean features and labels to processed directory
        feat_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                     'Ret_1', 'Ret_3', 'Ret_5', 'Synthetic_Order_Flow',
                     'Upper_Wick_Ratio', 'Lower_Wick_Ratio', 'Vol_Z_Score',
                     'ATR_14', 'ATR_Pct', 'Dist_EMA_20_ATR', 'Rel_Mom_vs_BTC',
                     'SL_Dist_Ratio', 'Pullback_Depth', 'Vol_Accum_Ratio',
                     'Regime_Z_Score', 'Volatility_Compression']


        label_cols = ['timestamp', 'Next_Open', 'Label_Long', 'Label_Short', 'Label_Long_7d', 'Label_Short_7d']

        # Save both standard names and backwards compatibility names
        feat_out = DATA_PROCESSED_DIR / f"{symbol}_1d_Features.csv"
        label_out = DATA_PROCESSED_DIR / f"{symbol}_1d_Labeled.csv"
        feat_out_legacy = DATA_PROCESSED_DIR / f"{symbol}_1d_7d_Features.csv"
        label_out_legacy = DATA_PROCESSED_DIR / f"{symbol}_1d_7d_Labeled.csv"

        clean_df[feat_cols].to_csv(feat_out, index=False)
        clean_df[label_cols].to_csv(label_out, index=False)
        clean_df[feat_cols].to_csv(feat_out_legacy, index=False)
        clean_df[label_cols].to_csv(label_out_legacy, index=False)

        long_pos_rate = clean_df['Label_Long'].mean() * 100
        short_pos_rate = clean_df['Label_Short'].mean() * 100

        print(f"[*] Processed {symbol}: {len(clean_df)} candles | Long Pos Rate: {long_pos_rate:.1f}% | Short Pos Rate: {short_pos_rate:.1f}%")

        summary.append({
            'symbol': symbol,
            'clean_candles': len(clean_df),
            'start_date': clean_df['timestamp'].min().strftime('%Y-%m-%d'),
            'end_date': clean_df['timestamp'].max().strftime('%Y-%m-%d'),
            'long_win_rate_pct': long_pos_rate,
            'short_win_rate_pct': short_pos_rate
        })

    print("\n=================================================================")
    print("STEP 3 COMPLETED: UNIFIED ALIGNED FEATURES & LABELS GENERATED")
    print("=================================================================")

if __name__ == '__main__':
    process_all_coins()

