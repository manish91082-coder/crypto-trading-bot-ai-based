"""Research-only, fold-isolated OOS spot replay.

Uses only purged walk-forward predictions produced by Step 4 and repository raw
OHLCV read strictly through each fold end. The final 14 days of each fold are
not new-entry days, leaving the complete configured label horizon inside that
fold. Step 5's existing spot execution simulator supplies sizing, regime filters,
trailing behavior and taker-fee accounting. Slippage/impact are not modeled here,
so results are diagnostic and are NOT acceptance/live-readiness evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pipeline_1d.step5_pooled_governed_backtest as step5
from config import (
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    LABEL_OBSERVATION_HORIZON_DAYS,
    SYMBOLS,
)
from features_1d import compute_1d_base_features, add_relative_momentum_vs_btc

REPORT_ROOT = ROOT / "artifacts" / "1d_reproducibility"
OUT_DIR = REPORT_ROOT / "oos_economic_replay"
THRESHOLDS = (0.42, 0.44, 0.46)
CAPITALS = (120.0, 10000.0)
FOLDS = (
    ("2023 H1", "2023-01-01", "2023-06-30"),
    ("2023 H2", "2023-07-01", "2023-12-31"),
    ("2024 H1", "2024-01-01", "2024-06-30"),
    ("2024 H2", "2024-07-01", "2024-12-31"),
)
MARKET_COLUMNS = [
    "timestamp", "Symbol", "open", "high", "low", "close", "volume",
    "ATR_14", "Vol_Accum_Ratio", "Rel_Mom_vs_BTC",
    "Pullback_Depth", "SL_Dist_Ratio",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_raw_through_cutoff(path: Path, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Stream raw CSV rows only through cutoff; never parse post-cutoff OHLCV."""
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    records = []
    previous = None
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"{path.name}: missing required OHLCV columns")
        for row in reader:
            ts = pd.to_datetime(row["timestamp"], errors="raise")
            if ts.normalize() > cutoff.normalize():
                break
            if previous is not None and ts <= previous:
                raise ValueError(f"{path.name}: duplicate/out-of-order row at {ts}")
            records.append(row)
            previous = ts

    df = pd.DataFrame.from_records(records)
    if df.empty:
        raise ValueError(f"{path.name}: no rows read through {cutoff.date()}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="raise")
    if df["timestamp"].max().normalize() != cutoff.normalize():
        raise ValueError(
            f"{path.name}: source ended {df['timestamp'].max().date()}, "
            f"expected fold cutoff {cutoff.date()}"
        )
    expected = pd.date_range(df["timestamp"].iloc[0].normalize(), cutoff.normalize(), freq="D")
    if len(df) != len(expected) or not np.array_equal(
        df["timestamp"].dt.normalize().to_numpy(), expected.to_numpy()
    ):
        raise ValueError(f"{path.name}: daily price cadence incomplete through fold cutoff")
    return df


def load_fold_market(fold_start: pd.Timestamp, fold_end: pd.Timestamp) -> pd.DataFrame:
    """Recompute causal features from prices through this fold end only."""
    raw_by_symbol = {}
    for symbol in SYMBOLS:
        raw_by_symbol[symbol] = read_raw_through_cutoff(
            DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv",
            cutoff=fold_end,
        )

    btc_features = compute_1d_base_features(raw_by_symbol["BTCUSDT"])
    parts = []
    # Build features using no prices beyond the current fold's test end.
    for symbol in SYMBOLS:
        frame = compute_1d_base_features(raw_by_symbol[symbol])
        frame = add_relative_momentum_vs_btc(frame, btc_features)
        frame["Symbol"] = symbol
        parts.append(frame)

    market = pd.concat(parts, ignore_index=True)
    market["timestamp"] = pd.to_datetime(market["timestamp"], errors="raise")
    market = market[
        (market["timestamp"] >= fold_start - pd.Timedelta(days=200))
        & (market["timestamp"] <= fold_end)
    ].copy()
    market.sort_values(["timestamp", "Symbol"], inplace=True)
    market.reset_index(drop=True, inplace=True)
    if market.empty or market["timestamp"].max().normalize() != fold_end.normalize():
        raise ValueError(f"Fold market tape missing fold-end prices for {fold_end.date()}")
    missing = set(MARKET_COLUMNS).difference(market.columns)
    if missing:
        raise ValueError(f"Recomputed fold market tape missing columns: {sorted(missing)}")
    return market[MARKET_COLUMNS].copy()


def read_oos_predictions(direction: str, fold_name: str, fold_start: pd.Timestamp,
                         fold_end: pd.Timestamp) -> pd.DataFrame:
    slug = fold_name.lower().replace(" ", "_")
    path = ROOT / "logs" / f"step4_oos_predictions_{direction.lower()}_{slug}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing fold-specific OOS prediction evidence: {path.name}")
    df = pd.read_csv(path)
    required = {"timestamp", "Symbol", "Fold", "Direction", "OOS_Probability"}
    label_name = f"Label_{direction}"
    required.add(label_name)
    if not required.issubset(df.columns):
        raise ValueError(f"{path.name}: missing columns {sorted(required.difference(df.columns))}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    if df.duplicated(["timestamp", "Symbol"]).any():
        raise ValueError(f"{path.name}: duplicate symbol/timestamp OOS score")
    if not ((df["timestamp"] >= fold_start) & (df["timestamp"] <= fold_end)).all():
        raise ValueError(f"{path.name}: OOS prediction timestamp outside its named fold")
    if set(df["Fold"].unique()) != {fold_name} or set(df["Direction"].unique()) != {direction}:
        raise ValueError(f"{path.name}: direction/fold metadata does not match filename")
    scores = pd.to_numeric(df["OOS_Probability"], errors="raise").to_numpy(float)
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError(f"{path.name}: invalid OOS probabilities")
    labels = pd.to_numeric(df[label_name], errors="raise")
    if not set(labels.dropna().unique()).issubset({0, 1, 0.0, 1.0}):
        raise ValueError(f"{path.name}: non-binary resolved target")
    df[label_name] = labels
    return df


def build_fold_master(market: pd.DataFrame, long_preds: pd.DataFrame,
                      short_preds: pd.DataFrame, fold_start: pd.Timestamp,
                      fold_end: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    keys_long = set(zip(long_preds["timestamp"], long_preds["Symbol"]))
    keys_short = set(zip(short_preds["timestamp"], short_preds["Symbol"]))
    if keys_long != keys_short:
        raise ValueError("Long/Short OOS prediction sample keys do not match")

    combined = market.copy()
    score_keys = ["timestamp", "Symbol"]
    combined = combined.merge(
        long_preds[score_keys + ["OOS_Probability"]].rename(
            columns={"OOS_Probability": "p_long"}
        ),
        on=score_keys, how="left", validate="one_to_one",
    )
    combined = combined.merge(
        short_preds[score_keys + ["OOS_Probability"]].rename(
            columns={"OOS_Probability": "p_short"}
        ),
        on=score_keys, how="left", validate="one_to_one",
    )

    # No entries in warmup dates or in the last horizon days of a fold.
    last_entry_signal = fold_end - pd.Timedelta(days=LABEL_OBSERVATION_HORIZON_DAYS)
    entry_mask = (
        (combined["timestamp"] >= fold_start)
        & (combined["timestamp"] <= last_entry_signal)
    )
    combined.loc[~entry_mask, ["p_long", "p_short"]] = np.nan
    combined.sort_values(["timestamp", "Symbol"], inplace=True)
    combined.reset_index(drop=True, inplace=True)

    label_info = {
        "first_signal_date": str(fold_start.date()),
        "last_allowed_signal_date": str(last_entry_signal.date()),
        "fold_end_price_date": str(fold_end.date()),
        "horizon_days": int(LABEL_OBSERVATION_HORIZON_DAYS),
        "oos_prediction_rows_long": int(len(long_preds)),
        "oos_prediction_rows_short": int(len(short_preds)),
        "feature_rows_for_simulation": int(len(combined)),
        "potential_long_signal_rows_at_threshold": {},
        "resolved_label_rows_at_threshold": {},
        "positive_label_rate_at_threshold": {},
    }
    eligible = long_preds[
        (long_preds["timestamp"] >= fold_start)
        & (long_preds["timestamp"] <= last_entry_signal)
    ].copy()
    for threshold in THRESHOLDS:
        selected = eligible[eligible["OOS_Probability"] >= threshold]
        resolved = selected.dropna(subset=["Label_Long"])
        key = f"{threshold:.2f}"
        label_info["potential_long_signal_rows_at_threshold"][key] = int(len(selected))
        label_info["resolved_label_rows_at_threshold"][key] = int(len(resolved))
        label_info["positive_label_rate_at_threshold"][key] = (
            float(resolved["Label_Long"].mean()) if not resolved.empty else None
        )
    return combined, label_info


def enrich_trade_labels(trades: pd.DataFrame, long_preds: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    out = trades.copy()
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="raise")
    out["signal_timestamp"] = out["entry_time"] - pd.Timedelta(days=1)
    labels = long_preds[["timestamp", "Symbol", "Label_Long"]].rename(
        columns={"timestamp": "signal_timestamp", "Symbol": "symbol", "Label_Long": "oos_label_long"}
    )
    labels["signal_timestamp"] = pd.to_datetime(labels["signal_timestamp"], errors="raise")
    out = out.merge(labels, on=["signal_timestamp", "symbol"], how="left", validate="many_to_one")
    return out


def independently_check_daily_equity(daily: pd.DataFrame, capital: float) -> float:
    if daily.empty:
        raise ValueError("OOS simulation returned an empty daily equity ledger")
    required = {"timestamp", "cash", "open_allocated_capital", "floating_pnl",
                "mtm_equity", "drawdown", "open_positions"}
    if not required.issubset(daily.columns):
        raise ValueError(f"Daily ledger missing {sorted(required.difference(daily.columns))}")
    numeric_cols = ["cash", "open_allocated_capital", "floating_pnl", "mtm_equity"]
    matrix = daily[numeric_cols].apply(pd.to_numeric, errors="raise").to_numpy(float)
    if not np.isfinite(matrix).all():
        raise ValueError("OOS daily ledger contains non-finite accounting fields")
    err = float(np.max(np.abs(
        daily["mtm_equity"].to_numpy(float)
        - daily["cash"].to_numpy(float)
        - daily["open_allocated_capital"].to_numpy(float)
        - daily["floating_pnl"].to_numpy(float)
    )))
    if err > 1e-6:
        raise ValueError(f"OOS daily MTM identity mismatch: max absolute error={err}")
    if not np.isfinite(float(capital)) or capital <= 0:
        raise ValueError("Invalid starting capital")
    return err


def run() -> None:
    if OUT_DIR.exists():
        import shutil
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "trades").mkdir(parents=True)
    (OUT_DIR / "equity").mkdir(parents=True)
    summary_rows = []
    fold_metadata = {}

    for fold_name, start_text, end_text in FOLDS:
        start = pd.Timestamp(start_text)
        end = pd.Timestamp(end_text)
        long_preds = read_oos_predictions("Long", fold_name, start, end)
        short_preds = read_oos_predictions("Short", fold_name, start, end)
        market = load_fold_market(start, end)
        master, signal_info = build_fold_master(market, long_preds, short_preds, start, end)
        fold_key = fold_name.lower().replace(" ", "_")
        fold_metadata[fold_key] = signal_info

        prediction_keys = set(zip(long_preds["timestamp"], long_preds["Symbol"]))
        if not prediction_keys.issubset(set(zip(master["timestamp"], master["Symbol"]))):
            raise ValueError(f"{fold_name}: an OOS prediction is missing from the fold market tape")

        # Verify model-training features and independently recomputed raw-candle features
        # match for each scored row before the replay is trusted.
        raw_join = master.merge(
            long_preds[["timestamp", "Symbol", "ATR_14", "Vol_Accum_Ratio"]],
            on=["timestamp", "Symbol"], how="inner", suffixes=("_market", "_oos"),
            validate="one_to_one",
        )
        for column in ("ATR_14", "Vol_Accum_Ratio"):
            a = pd.to_numeric(raw_join[f"{column}_market"], errors="raise").to_numpy(float)
            b = pd.to_numeric(raw_join[f"{column}_oos"], errors="raise").to_numpy(float)
            if not np.allclose(a, b, rtol=1e-9, atol=1e-9, equal_nan=True):
                raise ValueError(f"{fold_name}: raw-recomputed {column} differs from Step 4 OOS input")

        price_lookup = {symbol: {} for symbol in SYMBOLS}
        for row in market.itertuples(index=False):
            price_lookup[getattr(row, "Symbol")][getattr(row, "timestamp")] = {
                "open": float(getattr(row, "open")),
                "high": float(getattr(row, "high")),
                "low": float(getattr(row, "low")),
                "close": float(getattr(row, "close")),
                "atr": float(getattr(row, "ATR_14")),
            }

        for capital in CAPITALS:
            # Step 5 simulator resolves capital via its module-level setting.
            step5.INITIAL_CAPITAL = float(capital)
            for threshold in THRESHOLDS:
                summary, trades, daily = step5.run_simulation(
                    master.copy(),
                    price_lookup,
                    mode="spot",
                    threshold_long=threshold,
                    threshold_short=threshold,
                    max_concurrent=3,
                )
                equity_error = independently_check_daily_equity(daily, capital)
                enriched = enrich_trade_labels(trades, long_preds)
                tag = f"{fold_key}_capital_{int(capital)}_threshold_{int(round(threshold*100))}"
                enriched.to_csv(OUT_DIR / "trades" / f"{tag}.csv", index=False)
                daily.to_csv(OUT_DIR / "equity" / f"{tag}.csv", index=False)

                realized_pnl = 0.0
                if not trades.empty:
                    realized_pnl = float(pd.to_numeric(trades["realized_pnl"], errors="raise").sum())
                    if not np.isfinite(pd.to_numeric(trades["realized_pnl"], errors="raise").to_numpy(float)).all():
                        raise ValueError(f"{tag}: non-finite realized trade PnL")
                summary_rows.append({
                    "fold": fold_name,
                    "fold_start": start_text,
                    "fold_end": end_text,
                    "last_allowed_signal_date": signal_info["last_allowed_signal_date"],
                    "starting_capital": float(capital),
                    "mode": "spot_long_only",
                    "configured_probability_threshold": float(threshold),
                    "potential_score_threshold_rows": signal_info["potential_long_signal_rows_at_threshold"][f"{threshold:.2f}"],
                    "resolved_label_rows_among_threshold_rows": signal_info["resolved_label_rows_at_threshold"][f"{threshold:.2f}"],
                    "positive_label_rate_among_resolved_threshold_rows": signal_info["positive_label_rate_at_threshold"][f"{threshold:.2f}"],
                    "closed_trades": int(len(trades)),
                    "closed_trade_realized_pnl_sum_net_of_step5_taker_fees": realized_pnl,
                    "final_mtm_equity": float(summary["final_equity"]),
                    "mtm_total_return_pct": float(summary["total_return_pct"]),
                    "max_mtm_drawdown_pct": float(summary["max_mtm_drawdown_pct"]),
                    "profit_factor": float(summary["profit_factor"]),
                    "win_rate_pct": float(summary["win_rate"]),
                    "max_open_positions": int(daily["open_positions"].max()),
                    "open_positions_at_fold_end": int(daily["open_positions"].iloc[-1]),
                    "daily_mtm_identity_max_abs_error": equity_error,
                    "includes_taker_fees": True,
                    "includes_dynamic_slippage_or_market_impact": False,
                    "strategy_acceptance": "NOT_CERTIFIED",
                })

    summary_frame = pd.DataFrame(summary_rows)
    if len(summary_frame) != len(FOLDS) * len(CAPITALS) * len(THRESHOLDS):
        raise RuntimeError("OOS economic replay output is incomplete")
    summary_path = OUT_DIR / "oos_economic_replay_summary.csv"
    summary_frame.to_csv(summary_path, index=False)
    (OUT_DIR / "fold_metadata.json").write_text(
        json.dumps(fold_metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "status": "COMPLETED_DIAGNOSTIC_ONLY",
        "git_sha": "recorded by enclosing GitHub Actions run",
        "scope": "step4 fold-specific OOS spot replay with Step5 simulator; not a production or strategy acceptance result",
        "research_data_only": True,
        "data_cutoff_per_fold": "raw OHLCV reader stops at each test fold end before parsing subsequent candle prices",
        "holdout_2025_2026_used": False,
        "fold_count": len(FOLDS),
        "thresholds": list(THRESHOLDS),
        "capital_scenarios": list(CAPITALS),
        "entry_signal_last_day_policy": "fold_end minus the configured label observation horizon; entries later in the fold are disabled",
        "feature_parity_check": "independently recomputed raw-derived ATR_14 and Vol_Accum_Ratio match scored OOS prediction rows",
        "costs_included": ["Step 5 Binance taker fee model"],
        "costs_excluded": ["dynamic slippage", "market impact", "latency/partial fill cost"],
        "candidate_selection": "no threshold is selected; all pre-existing thresholds are reported",
        "live_readiness": "NO-GO",
        "live_signing": "BLOCKED",
        "public_broadcast": "BLOCKED",
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    (OUT_DIR / "sha256_manifest.txt").write_text(
        "".join(
            f"{sha256_file(path)}  {path.relative_to(OUT_DIR).as_posix()}\n"
            for path in sorted(p for p in OUT_DIR.rglob("*") if p.is_file() and p.name != "sha256_manifest.txt")
        ),
        encoding="utf-8",
    )
    print(f"[OOS ECONOMIC REPLAY] COMPLETED_DIAGNOSTIC_ONLY rows={len(summary_frame)}")
    print("[OOS ECONOMIC REPLAY] No 2025-2026 holdout prices loaded; not strategy/live acceptance.")


if __name__ == "__main__":
    run()
