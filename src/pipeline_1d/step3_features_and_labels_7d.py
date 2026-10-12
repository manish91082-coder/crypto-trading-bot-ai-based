import sys
import csv
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
from features_1d import compute_1d_base_features, add_relative_momentum_vs_btc

RESEARCH_END = "2024-12-31"       # Strict Vault Rule: Only research period touched


def load_research_period_csv(path: Path) -> pd.DataFrame:
    """Read rows only through the research cutoff; stop before processing holdout prices."""
    cutoff = pd.Timestamp(RESEARCH_END)
    records = []
    previous_timestamp = None
    required_columns = {"timestamp", "open", "high", "low", "close", "volume"}

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required_columns.issubset(set(reader.fieldnames)):
            raise ValueError(f"{path.name}: missing required OHLCV columns")

        for row in reader:
            timestamp = pd.to_datetime(row["timestamp"], errors="raise")
            if previous_timestamp is not None and timestamp <= previous_timestamp:
                raise ValueError(f"{path.name}: timestamps are duplicate or out of order at {timestamp}")
            if timestamp.normalize() > cutoff:
                # The first post-cutoff timestamp is a boundary sentinel only.
                # Its price/volume fields and all subsequent holdout rows are never loaded.
                break
            records.append(row)
            previous_timestamp = timestamp

    df = pd.DataFrame.from_records(records)
    if df.empty:
        raise ValueError(f"{path.name}: no research-period rows were read")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    for column in ("open", "high", "low", "close", "volume"):
        df[column] = pd.to_numeric(df[column], errors="raise")

    if df["timestamp"].max().normalize() != cutoff:
        raise ValueError(
            f"{path.name}: research data ends at {df['timestamp'].max()}, "
            f"not the required cutoff {RESEARCH_END}"
        )
    return df
TP_MULT = TP_ATR_MULT             # Matches execution partial TP (+3.0x ATR)
SL_MULT = SL_ATR_MULT             # Matches execution initial SL (-1.5x ATR)

def compute_stationary_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compatibility wrapper for the canonical shared 1D feature implementation."""
    return compute_1d_base_features(df)



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
    btc_research = load_research_period_csv(DATA_RAW_DIR / "BTCUSDT_1d_Raw_5Years.csv")
    btc_research.sort_values("timestamp", inplace=True)
    btc_research.reset_index(drop=True, inplace=True)

    summary = []

    for symbol in SYMBOLS:
        raw_file = DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv"
        df = load_research_period_csv(raw_file)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)

        # The streaming reader must never pass post-cutoff rows to feature/label calculations.
        assert df["timestamp"].max().normalize() == pd.to_datetime(RESEARCH_END), (
            "RESEARCH BOUNDARY FAILURE: input is missing final research candle"
        )

        # Features
        df = compute_stationary_features(df)
        
        # Cross-asset momentum is aligned to BTC by timestamp (missing matches remain NaN).
        df = add_relative_momentum_vs_btc(df, btc_research)

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

