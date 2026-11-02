# NP3: the NP2 composites with maker (limit-order) execution and a conservative fill model; final test on the still-sealed H. Locked 2026-10-26

## Background
- **NP2** (SHA b6d8d754; verifier ALL PASS) selected nothing at the taker cost of 0.092% per round trip. Gross per trade was 0.00 … 0.08% at 4 h.
- **The maker fee** in `deploy/fees.json` is `futures_usdm.bnb_maker` = 0.018% per side, with no impact for a resting order. The taker side is `rules.paper_futures_taker_per_side` = 0.046% (fee + impact).
- **The question:** with maker execution, is anything left after the costs and after the adverse selection of limit fills?
- **H** (2025-01-01 … 2026-09-30) is still sealed.
- **Code:**
  - main `src/research/nonprice_np3.py`, stages `DV` and `H`. It reuses the NP2 panels and scores, imported from `nonprice_np2.py`, SHA recorded in the run log.
  - verifier `src/audits/verify_nonprice_np3.py`, independent.
- **Honesty note.** This is a third look at the same D / V periods, so V remains only a filter. H decides.

## Signals
The 24 NP2 configs: h ∈ {1h, 4h} × set ∈ {ALL, NODEPTH} × {EQ θ 0.15 / 0.20 / 0.25, RIDGE q 0.80 / 0.90 / 0.95}. Scores, signs, β and thresholds are exactly as in NP2; the ridge is fit on D.

## Execution (5m futures bars, `clean/fut5m.parquet`)

**Entry, maker**
- At decision time t, a limit order rests at P = close(t), on the signal side.
- It fills only if a 5m bar with open time in [t, t + 15 min) trades **through** P: low < P for a long, high > P for a short. Touching P is not enough.
- If there is no fill, there is **no trade**. Missed signals are counted.
- Entry price = P.

**Exit, two modes; each config × mode is one config, 48 in all**

| Mode | Rule | Exit cost per side |
|---|---|---|
| **XT** (taker) | exit at close(t + h) | 0.046% |
| **XM** (maker with fallback) | a limit at Q = close(t + h) on the exit side. It fills if a bar in [t + h, t + h + 15 min) trades through Q. Otherwise, a taker exit at the close of the bar ending t + h + 15 min | maker 0.018%, or 0.046% on fallback |

**Net** = side × (exit / P − 1) − entry cost (0.018%) − exit cost.

All costs are read from `fees.json`.

## DV stage (it writes `np3_dv_summary.csv` and `np3_selection.json`; H rows are never read)

**Reported per config and period:**
- signals, fills, fill rate;
- trades, win %;
- mean gross and mean net per trade, weekly-cluster t;
- total;
- months positive, worst month.

**Selection**, the same rule as NP2: candidates must have D mean net > 0, D t ≥ 2.0 **and** V mean net > 0. Up to 3 of them, ranked by D t, are selected. If there are none, H stays sealed.

## H stage, the same gate as NP2
1. mean net > 0, with the weekly-cluster lower bound at z = 2.39 > 0;
2. ≥ 13 of the 21 months positive;
3. the 2025 sum > 0 and the 2026 sum > 0.

**Outputs:** every trade, the daily table (every H day), the monthly table.

## Verifier
1. Recompute the fills, prices and nets of every DV trade from the raw 5m bars with its own code.
2. Recompute the summaries and the selection.
3. Check that no H row is read in DV.
4. Check that the costs come from `fees.json`.
