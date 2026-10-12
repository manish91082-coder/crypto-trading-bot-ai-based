"""Run the research-only 1D pipeline and independently reconcile its ledgers.

The final-model step-5 replay is in-sample research/accounting evidence, not an
out-of-sample profitability certificate. The separate 2025-2026 vault is never
used for feature engineering, labels, fitting, simulations or threshold selection.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
from config import (
    DATA_PROCESSED_DIR, DATA_RAW_DIR, LOGS_DIR, MODELS_1D_POOLED_DIR, SYMBOLS,
    MIN_WALK_FORWARD_OOS_AUC,
)
from audits.audit_data_integrity import certify_1d_data_integrity
from audits.strategy_acceptance import evaluate_1d_research_gate

RESEARCH_END = pd.Timestamp("2024-12-31")
RAW_START = pd.Timestamp("2021-10-01")
RAW_END = pd.Timestamp("2026-09-30")
VAULT = ROOT / "data" / "vault_holdout_2025_2026"
REPORT = ROOT / "artifacts" / "1d_reproducibility"
CAPITALS = (120.0, 10000.0)
SELECTED = {
    "spot": "Spot Realism (Threshold 0.44 - High Edge)",
    "futures": "Futures Governed (Threshold 0.44 - High Edge)",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def tree_hashes(path: Path) -> dict[str, str]:
    files = sorted(p for p in path.glob("*.csv") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No CSV files found in {path}")
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in files}


def run(name: str, script: Path, log: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, str(script)], cwd=ROOT, env=env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )
    log.write_text(result.stdout, encoding="utf-8")
    print(result.stdout)
    if result.returncode:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}; see {log}")


def raw_audit() -> dict:
    result = {}
    for symbol in SYMBOLS:
        path = DATA_RAW_DIR / f"{symbol}_1d_Raw_5Years.csv"
        df = pd.read_csv(path)
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        if ts.isna().any() or ts.duplicated().any() or not ts.is_monotonic_increasing:
            raise ValueError(f"{path.name}: invalid, duplicate or unordered timestamps")
        if ts.iloc[0].normalize() != RAW_START or ts.iloc[-1].normalize() != RAW_END:
            raise ValueError(f"{path.name}: wrong dataset boundaries")
        expected = pd.date_range(RAW_START, RAW_END, freq="D")
        if len(ts) != len(expected) or not np.array_equal(ts.dt.normalize().to_numpy(), expected.to_numpy()):
            raise ValueError(f"{path.name}: daily series has a gap")
        prices = df[["open", "high", "low", "close", "volume"]].to_numpy(float)
        if not np.isfinite(prices).all():
            raise ValueError(f"{path.name}: non-finite OHLCV")
        if (prices[:, :4] <= 0).any() or (df["volume"] < 0).any():
            raise ValueError(f"{path.name}: invalid price or volume")
        if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any():
            raise ValueError(f"{path.name}: invalid highs")
        if (df["low"] > df[["open", "close", "high"]].min(axis=1)).any():
            raise ValueError(f"{path.name}: invalid lows")
        result[symbol] = {
            "sha256": sha(path), "rows": len(df),
            "start": str(ts.iloc[0].date()), "end": str(ts.iloc[-1].date()),
            "daily_cadence": "PASS", "ohlcv_geometry": "PASS",
        }
    return result


def research_samples() -> dict:
    out = {}
    for symbol in SYMBOLS:
        fp = DATA_PROCESSED_DIR / f"{symbol}_1d_Features.csv"
        lp = DATA_PROCESSED_DIR / f"{symbol}_1d_Labeled.csv"
        f = pd.read_csv(fp)
        l = pd.read_csv(lp)
        f["timestamp"] = pd.to_datetime(f["timestamp"], errors="raise")
        l["timestamp"] = pd.to_datetime(l["timestamp"], errors="raise")
        if f.empty or f["timestamp"].max() > RESEARCH_END or l["timestamp"].max() > RESEARCH_END:
            raise ValueError(f"{symbol}: feature/label output crosses the research cutoff")
        if len(f) != len(l) or not f["timestamp"].reset_index(drop=True).equals(l["timestamp"].reset_index(drop=True)):
            raise ValueError(f"{symbol}: feature/label rows do not align")
        entry = {"rows": len(f), "start": str(f.timestamp.min().date()), "end": str(f.timestamp.max().date())}
        for name in ("Label_Long", "Label_Short"):
            s = pd.to_numeric(l[name], errors="raise")
            if not set(s.dropna().unique()).issubset({0, 1, 0.0, 1.0}):
                raise ValueError(f"{symbol}: invalid target in {name}")
            entry[name] = {"resolved": int(s.notna().sum()), "censored": int(s.isna().sum())}
        out[symbol] = entry
    return out


def close(actual: float, expected: float, tol: float = 1e-6) -> bool:
    if np.isinf(actual) or np.isinf(expected):
        return actual == expected
    return bool(np.isclose(actual, expected, rtol=1e-7, atol=tol))


def reconcile(capital: float, dest: Path) -> dict:
    metrics = pd.read_csv(dest / "phase5_pooled_research_metrics.csv")
    if metrics.empty or not (pd.to_numeric(metrics.initial_capital) == capital).all():
        raise ValueError(f"Capital/metrics mismatch for scenario {capital:.0f}")
    summary = {}
    for mode, description in SELECTED.items():
        rows = metrics[metrics.description == description]
        if len(rows) != 1:
            raise ValueError(f"Expected one metric row for {description}")
        m = rows.iloc[0]
        daily_path = dest / f"phase5_pooled_{mode}_daily_equity_044.csv"
        trades_path = dest / f"phase5_pooled_{mode}_trades_044.csv"
        d = pd.read_csv(daily_path)
        d["timestamp"] = pd.to_datetime(d["timestamp"], errors="raise")
        if d.empty or (d.timestamp > RESEARCH_END).any():
            raise ValueError(f"{daily_path.name}: empty or beyond research cutoff")
        equity = pd.to_numeric(d.mtm_equity, errors="raise").to_numpy(float)
        cash = pd.to_numeric(d.cash, errors="raise").to_numpy(float)
        alloc = pd.to_numeric(d.open_allocated_capital, errors="raise").to_numpy(float)
        floating = pd.to_numeric(d.floating_pnl, errors="raise").to_numpy(float)
        identity_error = float(np.max(np.abs(equity - cash - alloc - floating)))
        if not np.isfinite(equity).all() or identity_error > 1e-6:
            raise ValueError(f"{daily_path.name}: MTM identity/non-finite failure")
        final_equity = float(equity[-1])
        if not close(final_equity, float(m.final_equity)):
            raise ValueError(f"{mode}: final equity disagrees with the daily ledger")
        peaks = np.maximum.accumulate(np.r_[capital, equity])[1:]
        dd = np.where(peaks > 0, (peaks - equity) / peaks, 0.0)
        max_dd = float(dd.max() * 100.0)
        if not close(max_dd, float(m.max_mtm_drawdown_pct)):
            raise ValueError(f"{mode}: drawdown disagrees with independent recomputation")

        trade_count, pnl_sum, wr, pf = 0, 0.0, 0.0, 0.0
        if trades_path.exists() and trades_path.stat().st_size > 1:
            t = pd.read_csv(trades_path)
            if not t.empty:
                pnl = pd.to_numeric(t["realized_pnl"], errors="raise")
                if not np.isfinite(pnl.to_numpy(float)).all():
                    raise ValueError(f"{trades_path.name}: non-finite PnL")
                trade_count, pnl_sum = len(t), float(pnl.sum())
                wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
                wr = float((pnl > 0).mean() * 100.0)
                gp, gl = float(wins.sum()), float(abs(losses.sum()))
                pf = gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0)
        if trade_count != int(m.total_trades) or not close(wr, float(m.win_rate)) or not close(pf, float(m.profit_factor)):
            raise ValueError(f"{mode}: trade count/win-rate/profit-factor ledger reconciliation failed")
        summary[mode] = {
            "description": description, "closed_trades": trade_count,
            "closed_trade_realized_pnl_sum": pnl_sum, "win_rate_pct": wr,
            "profit_factor": "Infinity" if np.isinf(pf) else pf,
            "initial_capital": capital, "final_mtm_equity": final_equity,
            "max_mtm_drawdown_pct": max_dd, "mtm_identity_max_abs_error": identity_error,
            "daily_start": str(d.timestamp.min().date()), "daily_end": str(d.timestamp.max().date()),
            "equity_sha256": sha(daily_path), "trades_sha256": sha(trades_path) if trades_path.exists() else None,
            "accounting": "PASS",
        }
    return {"initial_capital": capital, "modes": summary}


def main() -> None:
    if REPORT.exists():
        shutil.rmtree(REPORT)
    (REPORT / "logs").mkdir(parents=True)
    env_base = os.environ.copy()
    env_base["PYTHONPATH"] = str(SRC) + os.pathsep + env_base.get("PYTHONPATH", "")
    env_base.setdefault("OMP_NUM_THREADS", "1")
    env_base.setdefault("OPENBLAS_NUM_THREADS", "1")
    env_base.setdefault("MKL_NUM_THREADS", "1")

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        preflight = certify_1d_data_integrity()
    text = buffer.getvalue()
    (REPORT / "logs" / "data_integrity_preflight.log").write_text(text, encoding="utf-8")
    print(text)
    if not preflight:
        raise RuntimeError("Existing data-integrity certification failed")

    raw = raw_audit()
    (REPORT / "raw_data_structural_audit.json").write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")
    vault_before = tree_hashes(VAULT)

    run("Step 3 research-only features/labels",
        ROOT / "src/pipeline_1d/step3_features_and_labels_7d.py",
        REPORT / "logs/step3.log", env_base)
    samples = research_samples()
    (REPORT / "research_sample_counts.json").write_text(json.dumps(samples, indent=2, sort_keys=True), encoding="utf-8")

    run("Step 4 purged walk-forward training",
        ROOT / "src/pipeline_1d/step4_pooled_walkforward_training.py",
        REPORT / "logs/step4.log", env_base)
    folds = {}
    for direction in ("long", "short"):
        path = LOGS_DIR / f"step4_walkforward_{direction}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing fold report {path}")
        f = pd.read_csv(path)
        if len(f) != 4 or not np.isfinite(f[["LR_OOS_AUC", "XGB_OOS_AUC"]].to_numpy(float)).all():
            raise ValueError(f"{direction}: incomplete/non-finite purged OOS folds")
        shutil.copy2(path, REPORT / path.name)
        folds[direction] = {
            "folds": len(f), "periods": f.Period.tolist(),
            "train_samples": f.Train_Samples.astype(int).tolist(),
            "test_samples": f.Test_Samples.astype(int).tolist(),
            "target_positive_rate": f.Target_Positive_Rate.astype(float).tolist(),
            "lr_oos_auc": f.LR_OOS_AUC.astype(float).tolist(),
            "xgb_oos_auc": f.XGB_OOS_AUC.astype(float).tolist(),
            "xgb_probability_min": f.XGB_Prob_Min.astype(float).tolist(),
            "xgb_probability_median": f.XGB_Prob_Median.astype(float).tolist(),
            "xgb_probability_p90": f.XGB_Prob_P90.astype(float).tolist(),
            "xgb_probability_max": f.XGB_Prob_Max.astype(float).tolist(),
            "xgb_probability_count_ge_042": f.XGB_Prob_Count_GE_042.astype(int).tolist(),
            "xgb_probability_count_ge_044": f.XGB_Prob_Count_GE_044.astype(int).tolist(),
            "xgb_probability_count_ge_046": f.XGB_Prob_Count_GE_046.astype(int).tolist(),
        }

    model_hashes = {}
    for name in ("Pooled_1d_XGB_Long.pkl", "Pooled_1d_XGB_Short.pkl"):
        p = MODELS_1D_POOLED_DIR / name
        if not p.exists() or p.stat().st_size == 0:
            raise FileNotFoundError(f"Missing fitted model {p}")
        shutil.copy2(p, REPORT / name)
        model_hashes[name] = {"sha256": sha(p), "bytes": p.stat().st_size}

    results = {}
    output_names = (
        "phase5_pooled_research_metrics.csv",
        "phase5_pooled_spot_trades_044.csv",
        "phase5_pooled_spot_daily_equity_044.csv",
        "phase5_pooled_futures_trades_044.csv",
        "phase5_pooled_futures_daily_equity_044.csv",
        "phase5_model_probability_diagnostics.csv",
    )
    for capital in CAPITALS:
        label = f"capital_{int(capital)}"
        dest = REPORT / label
        env = env_base.copy()
        env["INITIAL_CAPITAL"] = str(capital)
        for filename in output_names:
            (LOGS_DIR / filename).unlink(missing_ok=True)
        run(f"Step 5 research replay, initial capital {capital:.0f}",
            ROOT / "src/pipeline_1d/step5_pooled_governed_backtest.py",
            REPORT / "logs" / f"step5_{label}.log", env)
        dest.mkdir()
        for filename in output_names:
            source = LOGS_DIR / filename
            if source.exists():
                shutil.copy2(source, dest / filename)
            elif "trades" in filename:
                continue
            else:
                raise FileNotFoundError(f"Missing required backtest output {source}")
        results[label] = reconcile(capital, dest)
        metrics = pd.read_csv(dest / "phase5_pooled_research_metrics.csv")
        results[label]["configuration_trade_counts"] = {
            str(row["description"]): int(row["total_trades"])
            for _, row in metrics.iterrows()
        }
        scores = pd.read_csv(dest / "phase5_model_probability_diagnostics.csv")
        if len(scores) != len(SYMBOLS):
            raise ValueError(f"{label}: expected score diagnostics for all symbols")
        results[label]["probability_diagnostics"] = {
            "symbols": int(len(scores)),
            "long_max_probability_global": float(scores["Long_Prob_Max"].max()),
            "short_max_probability_global": float(scores["Short_Prob_Max"].max()),
            "long_counts_ge_042": int(scores["Long_Count_GE_42"].sum()),
            "long_counts_ge_044": int(scores["Long_Count_GE_44"].sum()),
            "long_counts_ge_046": int(scores["Long_Count_GE_46"].sum()),
            "short_counts_ge_042": int(scores["Short_Count_GE_42"].sum()),
            "short_counts_ge_044": int(scores["Short_Count_GE_44"].sum()),
            "short_counts_ge_046": int(scores["Short_Count_GE_46"].sum()),
            "sha256": sha(dest / "phase5_model_probability_diagnostics.csv"),
        }

    configuration_counts = {
        scenario: details["configuration_trade_counts"]
        for scenario, details in results.items()
    }
    selected_spot_trades = {
        scenario: details["modes"]["spot"]["closed_trades"]
        for scenario, details in results.items()
    }
    strategy_gate = evaluate_1d_research_gate(
        fold_auc_by_direction={
            direction: details["xgb_oos_auc"]
            for direction, details in folds.items()
        },
        selected_spot_trades_by_capital=selected_spot_trades,
        configuration_trade_counts_by_scenario=configuration_counts,
        minimum_oos_auc=MIN_WALK_FORWARD_OOS_AUC,
    )
    (REPORT / "strategy_gate.json").write_text(
        json.dumps(strategy_gate, indent=2, sort_keys=True), encoding="utf-8"
    )

    vault_after = tree_hashes(VAULT)
    if vault_before != vault_after:
        raise RuntimeError("Sealed vault CSV hashes changed during the run")

    versions = {
        package: importlib.metadata.version(package)
        for package in ("numpy", "pandas", "scikit-learn", "scipy", "xgboost", "joblib")
    }
    manifest = {
        "reproducibility_status": "PASS",
        "strategy_acceptance_status": strategy_gate["research_gate_status"],
        "full_strategy_acceptance": strategy_gate["full_strategy_acceptance"],
        "scope": "research-only replay/accounting; in-sample Step 5 replay; no live readiness or untouched holdout profit claim",
        "git_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "research_end": str(RESEARCH_END.date()),
        "holdout_range": "2025-01-01 through 2026-09-30",
        "holdout_model_use": "not used for feature/label generation, fitting, simulation or threshold selection",
        "initial_capital_scenarios": list(CAPITALS),
        "raw_data_structural_audit": "PASS",
        "research_cutoff": "PASS",
        "walk_forward_oos_folds": folds,
        "strategy_gate": strategy_gate,
        "model_artifacts": model_hashes,
        "package_versions": versions,
        "vault_hashes_before": vault_before,
        "vault_hashes_after": vault_after,
        "vault_unchanged": True,
        "scenario_accounting": results,
        "live_readiness": "NO-GO",
        "live_signing": "BLOCKED",
        "public_broadcast": "BLOCKED",
    }
    (REPORT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    with (REPORT / "sha256_manifest.txt").open("w", encoding="utf-8") as out:
        for path in sorted(p for p in REPORT.rglob("*") if p.is_file() and p.name != "sha256_manifest.txt"):
            out.write(f"{sha(path)}  {path.relative_to(REPORT).as_posix()}\n")
    print("\n[DIAGNOSTIC COMPLETE] Reproducibility/accounting: PASS")
    print(f"[STRATEGY GATE] {strategy_gate['research_gate_status']}")
    for reason in strategy_gate["reasons"]:
        print(f"  - {reason}")
    print("[LIVE READINESS] NO-GO; holdout/live safety gates are not certified.")


if __name__ == "__main__":
    main()
