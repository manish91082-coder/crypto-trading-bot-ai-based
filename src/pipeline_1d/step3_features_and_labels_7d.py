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
    MAX_INACTIVITY_DAYS,
    TP_ATR_MULT,
    SL_ATR_MULT,
    BINANCE_TAKER_FEE,
    MACRO_BTC_EMA_PERIOD
)

RESEARCH_END = "2024-12-31"       # Strict Vault Rule: Only research period touched
EVENT_BARRIER_DAYS = 28          # Event-Driven Barrier: Gives natural room for swings to resolve
TP_MULT = TP_ATR_MULT             # Matches execution partial TP (+3.0x ATR)
SL_MULT = SL_ATR_MULT             # Matches execution initial SL (-1.5x ATR)
FEE_RATE = BINANCE_TAKER_FEE      # Binance VIP-0 Taker Fee (0.075%)

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
    Exact Triple-Barrier Labeling matching Unified Execution Rules:
    - Execution at T+1 Open.
    - TP = +3.0 * ATR, SL = -1.5 * ATR.
    - Max holding = HOLDING_DAYS (14 days inactivity window).
    - If neither hit within 14 days, evaluated at Day 14 Open net of fee.
    - Same-candle collision resolved pessimistically as LOSS.
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

    for i in range(n - EVENT_BARRIER_DAYS - 1):
        entry_idx = i + 1
        entry_price = opens[entry_idx]
        next_opens[i] = entry_price
        atr = atrs[i]

        if np.isnan(atr) or atr <= 0:
            continue

        # Long Barrier Targets
        long_tp = entry_price + (TP_MULT * atr)
        long_sl = entry_price - (SL_MULT * atr)

        # Short Barrier Targets
        short_tp = entry_price - (TP_MULT * atr)
        short_sl = entry_price + (SL_MULT * atr)

        # Simulate exactly up to EVENT_BARRIER_DAYS
        resolved_long = False
        resolved_short = False

        for d in range(1, EVENT_BARRIER_DAYS + 1):
            curr_idx = entry_idx + d
            if curr_idx >= n:
                break

            h = highs[curr_idx]
            l = lows[curr_idx]

            # Long Barrier Check
            if not resolved_long:
                hit_sl = (l <= long_sl)
                hit_tp = (h >= long_tp)
                if hit_sl and hit_tp:
                    # Pessimistic collision
                    labels_long[i] = 0
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
                    labels_short[i] = 0
                    resolved_short = True
                elif hit_sl:
                    labels_short[i] = 0
                    resolved_short = True
                elif hit_tp:
                    labels_short[i] = 1
                    resolved_short = True

            if resolved_long and resolved_short:
                break

        # Event Barrier Exit at Day 28 Open if unhit
        timeout_idx = min(entry_idx + EVENT_BARRIER_DAYS, n - 1)
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
    # Backwards compatibility aliases
    df['Label_Long_7d'] = labels_long
    df['Label_Short_7d'] = labels_short
    return df

def process_all_coins():
    print("=================================================================")
    print(f"STEP 3: {EVENT_BARRIER_DAYS}-DAY STATIONARY FEATURES & TRIPLE-BARRIER LABELING")
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
        # Drop the last EVENT_BARRIER_DAYS+1 rows where lookahead cannot be fully resolved
        clean_df = df.iloc[35:-(EVENT_BARRIER_DAYS + 1)].copy()

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

