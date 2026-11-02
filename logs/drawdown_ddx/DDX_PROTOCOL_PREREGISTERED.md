# DDX: drawdown control for the 1–7 day relative-strength family. Verified ledger of past trials + forward drawdown band for the live ECO. Locked 2026-10-27

**Request (user, 2026-10-27):** "do the suggestion you gave (drawdown control for 1–7 day relative strength), same discipline, ground-verified."

## 0. Pre-run inventory (done BEFORE this lock; stated honestly)
The suggestion in the fee-hurdle report §5 named "Step 19 DD 73%" as the open problem. Reading the project records before writing this protocol showed:
- That number is stale. Later trials already reduced the drawdown of the same relative-strength (RS) family:
  - F2 long-short (DD 30%);
  - F7 stops (DD 21%);
  - ECO-W2 combination with N1 (dev DD 11%), which is the configuration now live on the demo account.
- Most levers the suggestion named were already tested on the same 2021–26 data:
  - position size / exposure (Steps 21, 27);
  - volatility sizing (Step 28);
  - BTC hedge (R1 E1);
  - inverse-vol weights (R1 E4);
  - market gates (Steps 17, 20);
  - crash brain (Step 21);
  - exit brain (Step 26);
  - loss rules (master audit G3);
  - regime gate (N2);
  - safety sizing / catastrophe stop (N6 = T19);
  - profit lock (ECO-T4).
- The overfit audit S1 measured PBO 65% on this data.

**Consequence:** testing these levers again, or new variants of them, on the same 2021–26 data would be repeated data snooping. **This protocol therefore fits and selects NOTHING on historical data.** It has two descriptive parts:
- **A:** independent re-verification of every past drawdown trial from its own files;
- **B:** a forward drawdown/return band for the live ECO-W2 configuration, for use as the clean (forward) test.

## 1. Part A: verified ledger of past drawdown trials

**Rows (lever → evidence folder → items):**

| id | lever | folder | variant compared | equity file to recompute DD (column) |
|---|---|---|---|---|
| A01 | Step 19 base (RS top-20 long, 80%) | `logs/strategy_1d_step19_largecap` | `portfolio.AI` | `AI_equity.csv` (equity) |
| A02 | Steps 17/18 market + veto brain | `logs/strategy_1d_step17_18` | `portfolio.FULL` vs `R5_ONLY` | `FULL_equity.csv`, `R5_ONLY_equity.csv` |
| A03 | Step 20 large-cap market gate | `logs/strategy_1d_step20_largecap_gate` | `GATED` vs `UNGATED` | `GATED_equity.csv`, `UNGATED_equity.csv` |
| A04 | Step 21 crash brain | `logs/strategy_1d_step21_crash` | `ALARM` / `ALARM_CONTROL` vs `UNGATED` | `ALARM_equity.csv`, `ALARM_CONTROL_equity.csv` |
| A05 | Step 26 exit (tail) brain | `logs/strategy_1d_step26_exit` | `main.AI_VETO` vs `main.BASE` | `MAIN_2021_26_AI_VETO_daily_equity.csv` |
| A06 | Step 27 exposure f (D1 sleeve) | `logs/strategy_1d_step27_combine` | `decision_table.csv` rows mix=D1, f ∈ {1.0, 0.75, 0.5, 0.3} | `sleeves_MAIN_f{100,75,50,30}.csv` (D1) |
| A07 | Step 28 vol sizing | `logs/strategy_1d_step28_volsize` | `MAIN.VOL` vs `MAIN.FIXED_050` | `vol_path_MAIN.csv` (equity) |
| A08 | F2 long-short | `logs/strategy_f2_longshort` | `MAIN.AI_LS.mix` vs `MAIN.AI_LO.mix` | `equity_MAIN_AI_LS.csv`, `equity_MAIN_AI_LO.csv` (M_AI3) |
| A09 | F7 stop rules | `logs/strategy_f7_risk` | `MAIN.RS.mix` vs `MAIN.OFF_LS.mix` | `equity_MAIN_AI_RS.csv` (M_AI3) |
| A10 | R1 E1a/E1b BTC hedge | `logs/research_r1` | `results.E1a/E1b.result.mix` vs `baseline` | `equity_E1a.csv`, `equity_E1b.csv`, `equity_BASE_F7_RS.csv` (M_AI3) |
| A11 | R1 E4 inverse-vol weights | `logs/research_r1` | `results.E4.result.mix` vs `baseline` | `equity_E4.csv` (M_AI3) |
| A12 | ECO E-2 combination (W2, live) | `logs/eco` | `results["dev\|ECO-W2"]` vs `dev\|1D_alone`, `dev\|N1_alone`; also P3 | `data/derived/eco/e2_daily_series.parquet` |
| A13 | ECO-T4 profit lock | `logs/eco` | `claims_eco_t4.json` | claims only |
| A14 | Master-audit G3 loss rules (R2 rule portfolio, other system) | `logs/research_master_audit` | `claims_master_audit.json` | claims only |
| A15 | N2 regime gate (N1 system) | `logs/research_n2_regime` | `claims_n2.json` | claims only |
| A16 | N6 = T19 safety sizing / catastrophe stop (N1 system) | `logs/research_n6_safety_sizing` | `claims_n6.json` | claims only |

**Checks per row:**
- **A-SHA:** re-hash every `*PROTOCOL*PREREGISTERED.md` (and amendment) listed in the folder's SHA file. It must equal the stored SHA, and the claims file's `protocol_sha256` field where one exists. Code files listed in the same SHA files are re-hashed **report-only**: post-lock code changes are documented in each study's `CODE_CHANGES_AFTER_LOCK.md`.
- **A-DD:** where an equity file is listed, the max drawdown is recomputed:
  - formula: max over t of 1 − E_t / max_{s ≤ t} E_s, close-to-close on the file's rows, with the file's first value as the start;
  - tolerance: |recomputed − claimed| ≤ 0.01 percentage points (claims are rounded to 2 decimals). For ECO (unrounded claims) the tolerance is 1e-9 relative, with E0 = 10,000 prepended exactly as in `eco_e1_e2.py::wstats`;
  - final equity: recomputed the same way, within 0.01 USDT, or 1e-9 relative for unrounded claims.
- **A-DEC:** the study's own recorded decision (PASS / FAIL / INVALID / adopted / rejected) is copied verbatim from its claims file. No decision is re-made.

**Derived (report-only) columns, from the claimed numbers:** DD ratio (variant / its comparison) and final ratio (variant / its comparison).

**Mismatches:** any mismatch is reported as a mismatch with its size and is investigated. It is never silently fixed. No study's result is changed by this protocol.

## 2. Part B: forward drawdown/return band for ECO-W2

**Input:** `data/derived/eco/e2_daily_series.parquet`, columns `dev|ECO-W2` (2021-01-01 … 2025-09-30, 1,734 days) and `P3|ECO-W2` (2025-10-01 … 2026-09-30, 365 days). Each starts at E0 = 10,000.
- Daily return r_d = E_d / E_{d−1} − 1, with E_{−1} = 10,000 for each column's first day.
- Its SHA-256 is recorded in `input_manifest.csv` together with `deploy/eco_config.json`. `kill_K` = 0.3 is read from that config, not typed.

**Bases:**
- **B_ALL:** dev + P3 returns joined (2,099 days). This is the **primary** band, because it includes the recent weak year.
- **B_P3:** P3 only (365 days). This is the stress band: the most recent regime.
- **B_DEV:** dev only. Report-only. It is optimistic, because both producers were designed on it.

**Method:** stationary bootstrap (Politis–Romano).
- Mean block length L = 20 days: each next day continues the block with probability 1 − 1/L, otherwise it jumps to a uniform random start. Wrap-around is circular within the base.
- 10,000 paths per base and horizon; numpy `default_rng(20261027)`.
- Path order: for each base in the order ALL, P3, DEV, and each horizon in the order 30, 90, 180, 365, a fresh sub-stream from `rng.spawn`. Exact spawning is fixed in code.
- **Horizons H:** 30, 90, 180, 365 days.
- **Per path:**
  - equity_0 = 1; equity_t = Π(1 + r);
  - maxDD = max over t of 1 − equity_t / max_{s ≤ t} equity_s, including equity_0 = 1;
  - return = equity_H − 1.
- **Reported per base × H:**
  - maxDD percentiles 50, 75, 90, 95, 99;
  - return percentiles 1, 5, 25, 50, 75, 95;
  - P(maxDD ≥ kill_K);
  - P(return < 0).
- **Sensitivity (report-only):** L = 5 and L = 60 for B_ALL and B_P3.

**Historical rolling windows (deterministic, no randomness):**
- **Windows:** every start day of each base separately, and of B_ALL as one joined series. The join point is noted: P3 starts a fresh run, so only the returns are joined.
- **Statistics:** the max DD and return of each H-day window. The distribution of these: p50, p95 and max, plus the worst window's dates.

**Forward alarm thresholds (definition only; NOT deployed by this protocol):**
- **Age a:** for the live ECO, a is counted in full days from the first full demo day 2026-10-26.
- **Rule:** let H* be the smallest H ≥ a, capped at 365. The running max drawdown since 2026-10-26 is compared with the band:
  - YELLOW if it exceeds the B_ALL p95 maxDD at H*;
  - RED if it exceeds the B_ALL p99.
- **Deployment:** wiring this into `eco_alerts.py` needs the user's explicit yes, plus its own test.

**Part C (report-only, read-only):** if the VM can be reached, the ECO demo ledger's equity since 2026-10-26 is read without writing anything and compared with the band. Fewer than 7 full days is reported as "too early, information only".

## 3. Statements fixed in advance (no pass/fail; the wording depends only on numbers)
1. **Part A conclusion:**
   - "verified" if every A-SHA (protocol) and every A-DD check passes;
   - otherwise "verified except …", listing each mismatch.
2. **Kill switch:** if P(maxDD ≥ 0.30 within 365 d | B_ALL) is above 10%, the report says the 30% kill switch is a realistic event within a year. Otherwise it says the kill switch is a tail event (≤ 10%).
3. **Recent regime:** if the B_P3 median 365-day return is ≤ 0, the report says that, on the most recent year's behaviour, the live system's median expectation is no gain.
4. **Caveat (always stated):** both inputs are backtests of systems designed on 2021–26 data. Live costs and tracking (ECO E-3 tracking 1.20%) are not in them. Forward data is the only clean test.

## 4. Files
- **Code:** `src/research/drawdown_ddx.py`.
- **Independent verifier:** `src/audits/verify_drawdown_ddx.py`. It is separate code:
  - csv / json / pyarrow table reading and plain loops for drawdowns;
  - its own stationary bootstrap with a different seed (777).
  - Bootstrap tolerance: B_ALL and B_P3 p95 / p99 maxDD within 1.0 percentage point of the main run (Monte-Carlo agreement), and P(kill) within 1.0 point.
  - Deterministic numbers (ledger, rolling windows) must match exactly (1e-9).
- **Outputs (`logs/drawdown_ddx/`):** `ledger.csv`, `sha_checks.csv`, `band_bootstrap.csv`, `band_sensitivity.csv`, `rolling_windows.csv`, `alarm_thresholds.csv`, `input_manifest.csv`, `RESULTS.json`, `OUTPUT_SHA256.txt`, `verify_output.txt`, `CODE_NOTES.md`.
- **Report (Hindi):** `RESEARCH_DRAWDOWN_DDX_27_OCT_2026.md`.
- **Holdouts:** the micro-momentum 1s HOLD (2026-06 … 09) stays unopened. Nothing in this study touches the live VM except the read-only Part C.
