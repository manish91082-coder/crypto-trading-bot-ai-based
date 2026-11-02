# Step 30: daily resistance breakout, only in a pre-defined bull regime (pre-registered)

Locked before any Step 30 result. Code: `src/pipeline_1d/step30_breakout_regime.py`. Verifier: `src/audits/verify_step30_claims.py`.
No trading, no deploy, no GitHub.

## Background (verified earlier)
- After a daily or bigger resistance break, the 10-day excess return was +6 % to +11 % (CI above 0), but only in bull years:

  | Year | Excess |
  |---|---|
  | 2021 | +22.6 % |
  | 2022 | −6.4 % |
  | 2025 | −1.3 % |
  | 2026 | −3.3 % |

- That study used intrabar touches (high ≥ level + 1 ATR) and close-to-close returns, which are not directly tradable.
- Question: as a tradable rule, with the regime fixed in advance, after cost, does it make money and beat simply holding the same coins in the same regime?

## Universe and data
- **MAIN 2021-01-01..2026-09-30:**
  - the research test universe (reference 30 + half B, top 20 by 30-day USD volume, the Step 23 `daily_members`);
  - SHA-verified `data/universe_all/1d`.
- **PRE 2018-02-01..2019-12-31:** the Step 22 universe (`U_pre2020_predictions.csv` members), from `data/universe_pre2020/1d`.

## Rule (fixed)
**Daily resistance.** res[d−1] = the nearest UNBROKEN k = 3 fractal resistance above the close of day d−1. This uses the Phase 1 `sr_nearest`:
- a level is known 3 days after its bar;
- it is removed by the first close above it.

**Break event.** On day d, coin is a member of day d, and close[d] > res[d−1].

**Regime ON.** BTC close[d] > BTC 200-day SMA of closes up to d. This is a common bull filter, fixed now and not tuned.

**Trade.**
- Buy at open[d+1], sell at open[d+11] (10 days).
- 0.25 % per fill (stress: 0.40 %).
- Events whose exit is beyond the data end are excluded.

**Baseline (same days, same coins).** For every regime-ON day d with at least one event: the median 10-day return (open d+1 → open d+11, the same cost) of ALL members of day d.
- Event excess = event net − that day's member median net.

## Statistics
Mean net per trade and mean excess, each with a 95 % month-block bootstrap CI (2000 reps, seed 30), for:
- regime ON (the rule);
- regime OFF (report);
- ALL (report).

## Gates (all → PASS)
- **G1 MAIN:** regime-ON mean net > 0, CI low > 0.
- **G2 MAIN:** regime-ON mean excess > 0, CI low > 0.
- **G3 PRE:** regime-ON mean net > 0 AND mean excess > 0 (point estimates; PRE has few bull days, so its CI is reported only).
- **G4 MAIN at 0.40 % cost:** regime-ON mean net > 0.

**Decision:**
- PASS → candidate for the forward log as a shadow line (user decision). Its overlap with the AI sleeves is checked before any use.
- FAIL → reported.

## Limits stated now
- Overlapping trades: consecutive breaks of the same coin, and many coins on the same day. The month-block bootstrap only partly handles this.
- Per-trade statistics are not a portfolio. A portfolio test follows only on a PASS.
- The fill is at the next open; gaps are not modelled beyond that.
