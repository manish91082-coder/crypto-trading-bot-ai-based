"""Canonical 1D feature calculations shared by research and paper execution.

Keep the formula and rolling-window semantics in this module so the trained
model and the paper engine cannot silently drift apart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import MACRO_BTC_EMA_PERIOD


OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


def compute_1d_base_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all per-symbol 1D features except cross-asset relative momentum."""
    missing = set(OHLCV_COLUMNS).difference(df.columns)
    if missing:
        raise ValueError(f"1D feature input missing columns: {sorted(missing)}")

    out = df.copy()
    for column in OHLCV_COLUMNS:
        out[column] = pd.to_numeric(out[column], errors="raise")

    raw_values = out[list(OHLCV_COLUMNS)].to_numpy(dtype=float)
    if not np.isfinite(raw_values).all():
        raise ValueError("1D feature input contains non-finite OHLCV values")
    if (out["close"] <= 0).any() or (out["open"] <= 0).any():
        raise ValueError("1D feature input contains non-positive open/close prices")
    if (out["high"] < out[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("1D feature input violates OHLC high-price consistency")
    if (out["low"] > out[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("1D feature input violates OHLC low-price consistency")
    if (out["volume"] < 0).any():
        raise ValueError("1D feature input contains negative volume")

    out["Ret_1"] = out["close"].pct_change(1)
    out["Ret_3"] = out["close"].pct_change(3)
    out["Ret_5"] = out["close"].pct_change(5)

    bar_range = out["high"] - out["low"] + 1e-8
    out["Synthetic_Order_Flow"] = (out["close"] - out["open"]) / bar_range
    out["Upper_Wick_Ratio"] = (
        out["high"] - out[["open", "close"]].max(axis=1)
    ) / bar_range
    out["Lower_Wick_Ratio"] = (
        out[["open", "close"]].min(axis=1) - out["low"]
    ) / bar_range

    volume_mean = out["volume"].rolling(20).mean()
    volume_std = out["volume"].rolling(20).std()
    out["Vol_Z_Score"] = (out["volume"] - volume_mean) / (volume_std + 1e-8)

    tr1 = out["high"] - out["low"]
    tr2 = (out["high"] - out["close"].shift(1)).abs()
    tr3 = (out["low"] - out["close"].shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out["ATR_14"] = true_range.rolling(14).mean()
    out["ATR_Pct"] = out["ATR_14"] / (out["close"] + 1e-8)

    ema = out["close"].ewm(span=MACRO_BTC_EMA_PERIOD, adjust=False).mean()
    out["Dist_EMA_20_ATR"] = (out["close"] - ema) / (out["ATR_14"] + 1e-8)

    low_14 = out["low"].rolling(14).min()
    out["SL_Dist_Ratio"] = (
        out["close"] - (low_14 - 0.5 * out["ATR_14"])
    ) / (out["close"] + 1e-8)

    high_30 = out["high"].rolling(30).max()
    out["Pullback_Depth"] = (high_30 - out["close"]) / (high_30 + 1e-8)

    volume_sma20 = out["volume"].rolling(20).mean()
    out["Vol_Accum_Ratio"] = out["volume"] / (volume_sma20 + 1e-8)

    sma_200 = out["close"].rolling(200, min_periods=30).mean()
    std_200 = out["close"].rolling(200, min_periods=30).std()
    out["Regime_Z_Score"] = (out["close"] - sma_200) / (std_200 + 1e-8)

    atr_sma50 = out["ATR_14"].rolling(50, min_periods=14).mean()
    out["Volatility_Compression"] = out["ATR_14"] / (atr_sma50 + 1e-8)
    return out


def add_relative_momentum_vs_btc(
    df: pd.DataFrame, btc_df: pd.DataFrame
) -> pd.DataFrame:
    """Align BTC 5-candle return by timestamp; missing BTC matches remain NaN."""
    if "timestamp" not in df or "timestamp" not in btc_df:
        raise ValueError("Relative momentum requires timestamps for both assets")
    if "close" not in btc_df or "Ret_5" not in df:
        raise ValueError("Relative momentum requires close and Ret_5 columns")

    out = df.copy()
    btc = btc_df[["timestamp", "close"]].copy()
    btc["timestamp"] = pd.to_datetime(btc["timestamp"], errors="raise")
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="raise")
    if btc["timestamp"].duplicated().any():
        raise ValueError("BTC input contains duplicate timestamps")

    btc = btc.sort_values("timestamp")
    btc_ret5 = pd.Series(
        btc["close"].pct_change(5).to_numpy(),
        index=btc["timestamp"],
    )
    aligned_btc_returns = out["timestamp"].map(btc_ret5)
    out["Rel_Mom_vs_BTC"] = out["Ret_5"] - aligned_btc_returns
    return out
