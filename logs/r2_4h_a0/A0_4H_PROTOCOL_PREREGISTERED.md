# A0: 4H AI sleeve research protocol, pre-registered (2026-10-19)

**Scope.** This is the master protocol for the whole A-phase of R2: master Part 7, steps A1–A8, with the audit changes of Part 11.

**Lock.** It is locked with SHA256 (`A0_PROTOCOL_SHA256.txt`) before any A1 result is computed. Each step later gets its own short sub-protocol, which must cite this SHA and may only narrow this protocol, never widen it. Every change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.

**What this protocol is not.** It is research only:
- no orders and no money;
- the 1D cloud system and the laptop production files are not touched;
- `archive/` is not used.

**Sources (SHA):**
- `MASTER_INTEGRATED_RESEARCH_17_OCT_2026.md`, `07892372…`
- `REPORT_MASTER_AUDIT_18_OCT_2026.md`, `1c85575c…`
- `ERRATA_INDEX_R2_19_OCT_2026.md`

## 1. Question
On 4h bars, for long and short Binance USDT-M perpetuals (spot is used for longs only where it is cheaper):

**Q1 (A1).** Does any pre-registered rule signal earn at least **2× its trading cost** before any AI is added?

**Q2 (A3).** Can one pooled AI brain (B2-fast) choose which signals to take, and how big, so that net R per trade and portfolio Calmar rise above the take-all rule baseline? This must hold:
- after real costs and real funding;
- beyond shuffled-label and random-skip controls;
- without losing the tail winners.

**Q3 (A4).** Which exit and entry settings hold up on a plateau rather than at a single best point?

## 2. Data (fixed)
**Bars.** `data/universe_hf/5m/<coin>_5m_full.csv.gz` (UTC, left-closed), resampled to 5m, 15m, 1h, 4h and 1D exactly as in S6 (`probe_scalein.py`).

**Swings.** `data/derived/swing_anatomy/legs_all.parquet`, SHA `bbe7a4fd…`, K = 3. Its confirm-time features `c_*` were checked by reading the code on 2026-10-19:
- the ZigZag state is set at `confirm_idx`;
- the HTF state is looked up only from closed higher-TF bars (`state_lookup` uses end_time ≤ t).

They are still re-tested empirically in A2 (§8).

**Funding.** `data/futures_um/<coin>USDT_funding.csv`, the real history.

**Daily futures metrics.** `data/futures_info/<coin>USDT_metrics_daily.csv` (OI, long/short ratios, taker ratio; from 2020-09). Used only shifted by one full day, i.e. the value of day d is used from day d+1 00:00 UTC.

**Universe.**
- **Primary:** the 10 research coins BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LTC, LINK.
- **Expansion (M13, its own trial):** the coins in `data/universe_hf/5m` (296 files) that pass a point-in-time liquidity filter: median 30-day quote volume ≥ 50 M USDT on the perp at the signal time, using only data before the signal.

**Windows.**
- **Development:** signals with entry from 2020-02-01 to 2025-09-30.
  - Walk-forward monthly. The first test month is 2021-01, and training always uses only trades whose exit is before the test month starts.
  - P1 = 2020-02..2023-12 and P2 = 2024-01..2025-09 are reported separately.
- **Seen period P3** (2025-10..2026-09): reported separately and never used to choose anything. It was already looked at, so it is not a holdout.
- **Clean holdout:** forward data from 2026-10-17. It comes from the R2 forward recorder (`logs/forward_recorder_r2/`, protocol `3d9c9693…`), and A8 uses it only after the A5 freeze.
- **2018–19** (`data/universe_pre2020`): a spot-direction skill check only (D15).

## 3. Signals for A1 (4 rule signals = 4 trials)
All signals are evaluated at a 4h close and entered at the next 4h open.

| Id | Long | Short | Initial stop |
|---|---|---|---|
| **S-LAD** | swing low labelled HL while the last swing high is HH (UP ladder), known at confirm_time | swing high LH while the last swing low is LL (DOWN ladder) | pivot ∓ 0.5 ATR |
| **S-BRK** | 4h close > highest high of the previous 20 bars | close < lowest low of the previous 20 bars | entry ∓ 2 ATR(14) |
| **S-TRD** | close crosses above EMA(50) while EMA(50) > EMA(50) 6 bars earlier | mirror | entry ∓ 2 ATR(14) |
| **S-DTB** | swing low labelled HL directly after a double bottom (two lows within 0.5 ATR) | mirror for a double top | pivot ∓ 0.5 ATR |

- S-LAD is identical to S6.
- S-BRK, S-TRD and S-DTB allow one open signal per coin and side: a new signal is ignored while the previous trade is open.

**Common exit** (S6, fixed for A1):
- trailing stop = best price − 3 ATR, checked every bar, with a gap fill at the open;
- time stop at 60 bars.

**Q1 gate (per signal and side):**
- mean gross R ≥ 2 × mean cost R, over the development window;
- **and** mean net R > 0 in both P1 and P2.

**Outcome.** If no signal-side passes, A-phase stops and a report is written. Otherwise A3 uses the passing signal-sides only.

## 4. Costs (fixed)
**Base (audit E4).** Futures taker 0.05% × 0.9 (BNB) = 0.045%, plus 0.009% spread and slippage = **0.054% per side**.

**Funding.** Real per-timestamp funding: a long pays a positive rate and a short receives it. The notional is the fill price, as in the audit.

**Spot long.** 0.085% per side, no funding.

**Every result is reported at:**
- base;
- 1.5× fees and spread;
- 2× fees and spread;
- optimistic (taker 0.04%, i.e. 0.045% per side);
- no BNB (0.054% → 0.059% per side).

**Stop slippage.** The risk formula assumes 1% (F7). In simulation, a stop fills at the stop price, or at the bar open when the open gaps through it. A4 additionally reports a stress case where every stop fill is 0.3% worse.

## 5. Labels and AI (A3, B2-fast)
**Unit.** One row per A1-passing signal, with features known at the signal time.

**Label.** `y = 1` if the trade's base net R (V0, real funding) > 0, else 0.

**Features (fixed list).**
- From `legs_all`: all `c_*` columns, plus `move_atr`, `bars`, `done_share_at_confirm` of the confirming leg.
- From the signal: the side, the ladder step count k (A4 of S5), and the retracement ratio of the last pullback.
- Daily futures metrics of day d−1: OI change over 1 and 7 days, top/global long-short ratios, taker ratio.
- The last funding rate known at the signal time.
- Nothing else.

**Model.** One pooled `HistGradientBoostingClassifier` (scikit-learn) across coins and both sides, with fixed hyperparameters:
- learning_rate 0.05, max_iter 300, max_leaf_nodes 15, min_samples_leaf 40, l2_regularization 1.0;
- early stopping off; random_state 20261019.

There is no tuning.

**Calibration.** Isotonic, fitted on the last 20% (by time) of each training window.

**Retraining.**
- Monthly, on an expanding window.
- Purge: only trades whose exit is before the test month.
- Embargo: 1 day.

**Decision rule (fixed).**
- Take the signal if p ≥ the training-window median p. This makes the take rate about 50% by construction, which keeps the take rate comparable across tests.
- Size multiplier m = clip((p − 0.5) / 0.1, 0.5, 1.5), applied to the base risk f.

## 6. Portfolio simulator (audit B2, fixed)
**Capital and risk.**
- 8,000 USDT; base risk f = 0.5% of realised equity.
- K = 6 open positions; one position per coin.
- Total notional ≤ 3 × equity, isolated margin.
- Per-coin minimum notional (BTC 50 with qty ≥ 0.001, ETH 20, LINK 20, others 5).

**Sizing.** Notional = f × m × E / (stop% + 1% + round-trip fee).

**Drawdown.** Reported both:
- realised (as in the audit);
- **mark-to-market**, with equity marked at every 4h close using the bar's close, plus the worst intrabar move for open positions.

**Rules not used** (audit verdicts):
- no DD-halving (E6);
- no loss-streak pause;
- no same-direction cap (N17);
- no K = 3 (N20).

**Correlation with 1D.** The 1D system's daily equity comes from `logs/strategy_1d_step27_combine/sleeves_MAIN_f*.csv`; the correlation of monthly returns is reported.

## 7. Controls and gates (A3/A5 pass only if ALL hold)
**G-A (skill).** Walk-forward AUC lies above the 95th percentile of 20 shuffled-label runs (labels permuted within coin-month), **and** the 95% bootstrap CI (coin-year blocks, 2,000 draws) of AUC − 0.5 lies above 0.

**G-B (money per trade).** Mean net R of AI-taken trades − mean net R of all signals: its bootstrap CI (same blocks) lies above 0, at base cost **and** at 1.5×.

**G-C (portfolio).** AI portfolio Calmar (MTM DD):
- exceeds the take-all baseline Calmar;
- **and** exceeds the 95th percentile of 100 random-skip portfolios with the same monthly take rate (seed 20261019 + i).

**G-D (tail).** The share of the top-decile winners (by net R, all signals) that the AI takes must be ≥ its overall take rate. That is, the AI must not drop big winners more often than a coin toss would.

**G-E (stability).**
- Net R > 0 and Calmar > baseline in both P1 and P2.
- P3 reported, not gated.

**G-F (overfitting).**
- Deflated Sharpe Ratio ≥ 0.95, using the number of trials used so far (§9).
- PBO < 0.30 by CSCV (16 blocks) over all A3/A4 configurations tried. It is computed once ≥ 4 configurations exist; before that it is reported as "not computable", never as a pass.

**G-G (cost).** Net > 0 at 1.5× and 2× costs; reported at the optimistic and no-BNB levels.

**G-H (diversification).** Monthly correlation with the 1D system ≤ 0.70, **or** the combined (50/50) Calmar > the better of the two alone.

**G-I (2018–19).** Spot-direction AUC > 0.5 with the CI lower bound > 0.48 (a sanity check, as in Step 22).

## 8. A2: knowledge store, ledger and leak checks (before A3 trains anything)
- Every feature row carries an `available_at`.
- A **replay test** rebuilds the features for 200 random signals from data truncated at `available_at`. They must equal the stored features exactly.
- A **leak canary**: a feature built from the next bar's return is added on purpose. The pipeline must flag it, through AUC > 0.9 or a replay mismatch.
- `df["asof"]` is used, never `.asof` (project rule).
- **Trial registry** `logs/r2_4h_a0/trial_registry.csv`: id, date, config hash, data SHAs, result hash. It is append-only and hash-chained.

## 9. Trial budget: 20 (master D14), planned allocation
| Step | Trials |
|---|---|
| A1 | S-LAD, S-BRK, S-TRD, S-DTB = 4 |
| A3 | main meta-label = 1; universe expansion (M13) = 1 |
| A4 | time stop 60 / 120 / none × trailing 3 / 4 ATR = 6; V2 test entry = 1; maker entry with fill model = 1 |
| A6 | AI exit = 1 |
| Reserve | 5 (each use is written to the registry before it is run) |

Every configuration evaluated counts, whatever its result.

## 10. A4 fill model for maker entries (M12)
- A post-only limit at the 4h open price, valid for ≤ 12 5m bars (1 hour).
- It fills only if a later 5m bar trades through the limit by at least one tick (low < limit for a buy).
- An unfilled order becomes a taker at the close of the 12th bar.
- Reported: the fill rate, and the mean net R of filled vs unfilled entries (adverse selection).

## 11. Live risk rules for later stages (fixed now; used from A7 on)
**Kill switch (M4).** Live or forward review, with no new entries until the user confirms, when MTM drawdown ≥ 2 × the A5 backtest MTM maxDD. There is no loss-streak alarm: a 27-trade losing streak is normal (audit B4).

**Operational alarms (L6), which trigger reduce-only plus an alert:**
- data age > 2 bars;
- reconcile mismatch;
- a missing stop;
- BNB balance < the fees needed for 30 days (M3);
- a funding interval change;
- a perp status other than TRADING.

**Global risk budget (M7).** The 4h sleeve's open risk is ≤ K × f = 3% of the sleeve's equity. The combined cap with the 1D system is set by the user before A9.

**Decay monitor (M10).** Rolling 6-month net R per trade, long and short separately. Review only.

## 12. Outputs and verification
- Each step writes: its sub-protocol + SHA; CSVs; `claims.json`; `run_log.txt`; `verify_log.txt` from an independent verifier with its own code; and a Hindi report.
- No step starts before the previous step's verifier is fully PASS and the user has seen the report.
- Real money (A9) needs the user's explicit "yes" and is outside this protocol.
