# Step 23: code changes after the lock (2026-10-14T11:23:26Z)

## 1. G0a universe check, alignment bug in the CHECK only
- **Symptom:** the first run printed `a_universe_equals_step19: False` after 27 s. It was stopped before any model was trained; only universe sizes and the 4H-vs-1d cross-check had been printed.
- **Cause:** `zip(u19.symbol, u19.date[mask])` paired the full symbol column with a filtered date column, so the positions shifted.
- **Evidence that the universe itself is right:** a separate recomputation over 2021-01-01..2026-09-30 matched `universe_U.csv` exactly (41,980 = 41,980 coin-days, 0 differences either way).
- **Fix:** filter `u19` first, then zip. The universe code, features, labels, model and gates are unchanged.
d63de73fae03d85d90c960bd257f4be30062bbc194318e2110157fdd6774f5af *src/pipeline_1d/step23_4h_brain.py
