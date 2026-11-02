# N2: regime overlay on the N1 portfolio (trial T16), pre-registered 2026-10-20, locked BEFORE any N1 result is known

**Parents.**
- N1 protocol `20ffc364…` (trial T15) and its simulator `src/research/n1_portfolio.py`. N2 imports it and adds only the regime multipliers.
- The research plan: `RESEARCH_COLLECTIVE_BRAIN_SATURATION_20_OCT_2026.md`, layer 1 (B1) and G2.

Research only. No orders, no money, nothing in production is touched.

**Base.**
- If N1 PASSES, the base is the N1 FINAL config (`claims_n1.json` `final_cfg`).
- If N1 FAILS, the base is K0 and N2 is a report only: no PASS claim is possible (N1 protocol §6).

## 1. Question
The sign of the trend P&L follows BTC's yearly direction (TFX-S: Spearman 0.71–0.89). Does a regime overlay that tilts the long sleeves (A, B) and the short sleeve (C) by the BTC regime raise portfolio Calmar and cut MTM-DD against the base, in both P1 and P2? The overlay must also beat a random regime path with the same persistence.

## 2. Regime inputs (point-in-time)
- **BTC daily bars.**
  - 2017-08-17 … 2019-12-31: `data/universe_pre2020/1h/BTCUSDT_1h_full.csv.gz`, resampled to 1D.
  - From 2020-01-01: the N1 1h cache (from `data/universe_hf/5m`), resampled to 1D.
- **Timing.** The regime used for an entry at time t is the one computed at the close of the last complete day before t (day floor(t) − 1), the same rule as the N1 overlays.

**Volatility factor (both variants):**
- σ̂_d = std of the 20 daily close-to-close BTC returns ending on day d.
- σ*_d = the expanding median of σ̂ up to day d (≥ 365 values, else m_vol = 1).
- m_vol = min(1, σ* / σ̂).

**g_min = 0.25.**

## 3. Variants (2 configurations = trial T16)
**R1, rule.**
- trend_d = EMA20 − EMA50 of the BTC daily close (the TFX EMAX definition).
- trend > 0 → g_L = m_vol and g_S = g_min · m_vol.
- Otherwise g_L = g_min · m_vol and g_S = m_vol.

**R2, statistical jump model (2 states).** Method: Nystrup, Lindström & Madsen (2020); Shu, Yu & Mulvey (2024) ⚠ (not re-verified here).

*Features* on BTC daily log returns r:
- the EWM downside deviation, halflife 10 and 21: sqrt(EWM(min(r, 0)²));
- the EWM Sortino ratio, halflife 10 and 21: EWM mean(r) / that downside deviation.

They are standardised with the training window's mean and std.

*Fit.*
- Monthly, at each month start, on all days before that month (from 2017-09-15, i.e. after a 4-week feature warm-up).
- Objective: min Σ‖x_t − μ_{s_t}‖² + λ · #jumps.
- Coordinate descent, alternating:
  - a dynamic-programming state path;
  - centroid means.
- 10 restarts from k-means++ seeds (seed 20261025 + restart) and 20 iterations; keep the lowest objective.
- **λ = 50, fixed and not tuned.**

*Online state for day d.* The same DP with the fitted centroids, run over the days from the training start to d. Day d's state is the last state of that path (filtered; no future data).

*Bull state* = the state whose training days have the higher mean r.
- Bull → g_L = m_vol, g_S = g_min · m_vol.
- Bear → g_L = g_min · m_vol, g_S = m_vol.

**Application (both).**
- At entry, the A and B sub-position weights are multiplied by g_L and the C weights by g_S. D is unchanged.
- Open positions are not resized, as in N1's unit-fixed positions.
- Then the N1 heat cap applies, if the base has it.

## 4. Gates (a variant PASSES only if all hold; if both pass, the higher dev Calmar is chosen)
- **Q1.** Dev Calmar > base dev Calmar, **and** dev MTM-DD < base dev MTM-DD.
- **Q2.** Calmar > base Calmar in P1 **and** in P2.
- **Q3 random-regime control.**
  - Dev Calmar > the 95th percentile of 100 runs in which the variant's own daily state path is circularly shifted by a uniform random offset of 30 … (n_days − 30) days (seed 20261025 + i).
  - This keeps the run lengths, the share of time in each state, and the m_vol path.
- **Q4 DSR ≥ 0.95** (monthly dev returns).
  - N = 14 + 5 + the N1 configuration count + 2.
  - The SR variance is that over the N1 configurations plus R1 and R2.
- **Q5 2018–19 out-of-time** (N1 G7 data and costs, run once): Calmar(variant) > Calmar(base) over 2018-04-17 … 2019-12-31.
- **Report only:**
  - every calendar year (return, MTM-DD) for the base, R1 and R2;
  - P3 (seen);
  - the share of days in the bull state;
  - the number of regime switches per year.

## 5. Outputs and verifier
- **Outputs.** `logs/research_n2_regime/`: `N2_results.csv`, `N2_years.csv`, `N2_random.csv`, `N2_states.csv` (daily g_L, g_S and state per variant), `claims_n2.json`, `run_log.txt`.
- **Verifier.** `src/audits/verify_n2.py`, own code:
  1. R1 states and m_vol recomputed from raw BTC data.
  2. The R2 DP path recomputed from the saved centroids for 5 random fit months; the online state for 100 random days; the objective is ≤ that of the k-means-only start.
  3. The portfolio weights of 200 random entries = the N1 weight × g; the dev Calmar of the chosen variant is recomputed from the ledger with the N1 verifier's accounting.
  4. Gates and SHAs.

Any change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.
