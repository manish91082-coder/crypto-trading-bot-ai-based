# ECO: a single 10,000 USDT ecosystem (1D AI system + PAPER-N1) on one Binance account. Pre-registered 2026-10-21, before any combined number is computed.

**Mandate (user, 2026-10-21).**
- One ecosystem on a budget of 10,000 USDT.
- One Binance account, managed internally.
- No 90-day wait.
- Claude decides the design.
- Same discipline as before: protocol + SHA lock, independent verifier, CODE_CHANGES after the lock, nothing faked.

**Scope.**
- Research (E-1, E-2) and laptop build/tests (E-3, E-4).
- The VM gets nothing in this protocol beyond plan mode (E-5).
- The demo cut-over (E-6), which retires the F6 cron, needs the user's separate yes.
- **No mainnet code path exists in this phase.**
- The 1D producers (Step16, 16B, F4) and PAPER-N1 are not modified; they are read only.
- `archive/` is not used.

**Facts this design is based on (checked 2026-10-21, `PLAN_SINGLE_ECOSYSTEM_21_OCT_2026.md` §1).**
- F6 needs one-way mode and holds 7 shorts on the demo account. 6 of them are also N1 sleeve-C shorts.
- 19 of 169 N1 perp legs are below the Binance min notional individually. After netting per coin, 0 of 23 are.
- VM: 2 vCPU, 3.3 GB RAM free.
- The public demo endpoints `demo-fapi.binance.com/fapi/v1/ping` and `demo-api.binance.com/api/v3/ping` answer HTTP 200.

## 1. Strategies (producers, unchanged)

| Id | Producer (as deployed) | Paper capital | Target extracted |
|---|---|---|---|
| S_1D | F4 line **LS_RS** (D1, H4, H1 sleeves; F7 rules: short stop × 1.50, 30-day cooldown) | 3 × 10,000 | `orders_<asof>.json` → `LS_RS` → per sleeve: longs {units}, shorts {units, entry, stop}; plus `pending` buy / sell / short / cover |
| S_N1 | PAPER-N1 (N1 K1 + X2 + 20% entry cap), `data/paper_n1` | 10,000 | `state.json` pos {sleeve, side, units, venue}; ledger last line (hash chain) |

- **Paper fraction of a strategy s in coin c:** f_{s,c} = Σ_positions side × |units| × p_c / Equity_s. Here p_c is the price used by the executor, and Equity_s is the strategy's own paper equity: F4 = sum of `equity_close` of the 3 sleeves; N1 = ledger equity.
- **S_1D pending actions.** F4 decisions made at a day's close are filled by the paper at the next bar.
  - The adapter applies `pending` the same way: positions in `sell` / `cover` → 0; `buy` / `short` → added.
  - Size: the F4 rule `invest × equity / n`. 50% of the sleeve equity per side over N_HOLD = 5 names, read from F2R constants, not retyped.
- **Integrity.**
  - The F4 orders file SHA must equal `orders_sha256` of the F4 ledger's last line.
  - The N1 ledger hash chain must verify, and its last line's T must be the state's `last_T`.
  - On a mismatch, that strategy is **frozen**: its current executed positions are kept, no new opens, alert.
- **Staleness.**
  - N1 is stale if its last T is more than 5 h before now.
  - F4 is stale if its last as-of is more than 2 days before today (UTC).
  - A stale strategy is frozen as above.

## 2. Allocation between strategies (decided by E-2, §5)

- **Eco equity.** E_eco = 10,000 USDT internal start. All P&L is attributed to the strategy and sleeve that caused it (attribution ledger).
- **Month-start sizing.** E_m = E_eco at the first cycle of the calendar month, as N1 does.
- **Coin target.** T_c = Σ_s a_s × E_m × f_{s,c}, with weights a_s from §5 (Σ a_s = 1).
- **Caps (applied after summing).**
  1. Per coin: |T_c| ≤ 0.20 × E_eco. A scaled coin is reduced proportionally across its contributors.
  2. Gross: Σ|T_c| ≤ 1.50 × E_eco, else all T scale down by one factor.

  Every scaling is logged.
- **Kill switch.**
  - Trigger: E_eco < (1 − K) × its running peak (marked hourly).
  - Action: close everything, set `halted`, and wait for a manual reset by the user.
  - K = max(0.30, 1.25 × the MTM-DD of the selected E-2 configuration in dev). It is computed by formula once E-2 is done and written to the claims.

## 3. Execution (netting executor)

- **Account and venue.**
  - One account, one-way mode (asserted; the code never changes it).
  - **Phase demo: every leg on USDT-M perpetuals.** That includes S_1D spot longs and N1 legs routed to spot by X2. The deviation (fee and funding vs the paper venue) is logged per leg.
  - No spot orders in this phase. Spot execution is a later protocol.
- **Margin.**
  - CROSSED, leverage setting 2 for symbols the executor opens fresh.
  - A symbol already holding an ISOLATED position (inherited from F6) keeps it until it is flat.
  - Economic exposure is controlled only by the caps in §2.
- **Account scale.**
  - k = min(1, account wallet equity / E_eco), measured each cycle.
  - Executed target = k × T_c. On a 10,000 USDT account k = 1.
  - P&L is reported both in account USDT and normalised to eco units (÷ k).
- **Orders.**
  - Δ_c = k × T_c − current net position notional (exchange `positionRisk`).
  - Trade only if |Δ_c| ≥ max(min_notional_c, 0.0025 × k × E_eco), or the target is 0 with a non-zero position, or the sign flips.
  - MARKET orders. A reduction that does not cross zero is `reduceOnly`.
  - Quantity floored to the step; a quantity below min qty or min notional is skipped and logged.
  - At most 40 orders per cycle (as F6).
- **Stops (S_1D shorts only; N1 has none by its protocol).**
  - Each S_1D short component carries the F4 stop price.
  - The executor checks it every hourly cycle against the last closed 1h high of the perp. If the high ≥ the stop, that component's contribution is set to 0 (suppressed) until F4's own state shows the position closed.
  - A pending short (in F4 `short`, not yet in `shorts`) has no F4 entry yet. Its stop is 1.50 × the executor's own fill price for that component, until F4 reports its entry; from then on F4's stop is used.
  - **No exchange stop orders in this phase.** Stated limitation: during a VM outage, no stop protection.
- **Attribution.** Each fill is split across contributors in proportion to their signed share of Δ_c. Fees are split the same way, and funding by position share at the funding time.
- **Reconcile.** After each cycle the ledger positions must equal the exchange net positions per symbol (tolerance one step).
  - A mismatch freezes that symbol (no orders) and raises an alert. It is not auto-fixed.
  - Positions on symbols the ecosystem does not target are reported, not touched.

## 4. Orchestration

- **One entry point** `src/eco/eco_orchestrator.py`, run by cron hourly at minute 50 (after PaperN1 at :41).
- **Order of work:** lock (`flock`) → load and verify producers → targets → caps → stops → executor → reconcile → hash-chained ledger line.
- A failing step stops the cycle **without orders**, and the ledger records the failure.
- **Modes:** `plan` (no keys, no orders), `replay` (laptop, simulated fills), `demo` (orders to `demo-fapi.binance.com` only).
- **Mainnet:** none.

## 5. E-2: combination backtest (trials ECO-W1, ECO-W2)

- **Series.**
  - S_1D = `logs/strategy_f7_risk/equity_MAIN_AI_RS.csv`, column M_AI3 (daily, 2021-01-01 … 2026-09-30).
  - S_N1 = the N1 FINAL (K1 + X2 + X3 + S2 cap) hourly curve, regenerated with the locked N1/N3/N6 code, taken at each day's last hour.
  - **E-1 gate before use:** the regeneration reproduces the claims of N6: dev Calmar 4.160747… to 1e-9, and P1 / P2 / P3.
- **Windows.**
  - dev 2021-01-01 … 2025-09-30;
  - P1 2021-01-01 … 2023-12-31;
  - P2 2024-01-01 … 2025-09-30;
  - P3 2025-10-01 … 2026-09-30 (report only).

  Each strategy is run (N1) or rebased (1D) from 10,000 at each window start.
- **Combination.** Daily portfolio return = Σ a_s,m × r_s,day, with a_s,m fixed for the calendar month (internal sub-accounts rebalanced at each month start, no cost charged for the internal rebalance, which moves no coins).
- **Candidates.**
  - **ECO-W1:** a = 0.5 / 0.5.
  - **ECO-W2:** inverse volatility. a_s,m ∝ 1 / σ_s, where σ_s is the std of daily returns over the 126 days before the month. 0.5 / 0.5 until 126 days exist. Weights clipped to [0.2, 0.8] and renormalised.
- **Reference.** The N1 FINAL alone on the same windows.
- **Acceptance (all required).**
  - (a) dev Calmar ≥ 0.90 × N1-alone dev Calmar;
  - (b) dev MTM-DD ≤ N1-alone dev MTM-DD;
  - (c) Calmar > 0 in P1 and in P2;
  - (d) DSR ≥ 0.95 on dev monthly returns, with N = 20 (A0 registry) + 5 (TFX N_eff) + 2 = 27 and the SR variance of the 3 series (W1, W2, N1 alone).
- **Selection.** The acceptable candidate with the highest dev Calmar. If none is acceptable, a_1D = 0: the ecosystem trades S_N1 only, and S_1D stays as its shadow paper.
- **Report only:**
  - every calendar year;
  - P3;
  - the daily and monthly correlation of the two strategies;
  - BTC buy-and-hold;
  - the per-coin overlap of the two books (from E-3).
- **PBO** is not computed: 2 candidates give no meaningful CSCV. Stated.

## 6. E-3: replay (laptop; simulated fills; plumbing and tracking test, no performance claim)

- **Window:** 2026-09-01 … 2026-09-30, the window with authentic producer code for both strategies.
  - F4: `build_lines` from `forward_ls_f4.py` with the stored research predictions and the archive perp files (as its `--test`). It is run once per as-of day, giving that day's orders dict.
  - N1: `paper_n1_portfolio.py --replay 2026-08-01 2026-10-01` (warm-up August) into a scratch root.
- **Fills:** the open of the 1h bar after the cycle (perp 1h bars from `data/futures_um`), taker 0.054%, real funding. Exchange filters: an exchangeInfo snapshot saved with its SHA.
- **Gates.**

  | Gate | Condition |
  |---|---|
  | R1 | Attribution identity: Σ sleeve P&L = executor P&L to 1e-6 USDT every cycle |
  | R2 | Tracking: \|executor eco equity − Σ a_s × paper equity path (rebased)\| ≤ 1.0% of E0 at every day end |
  | R3 | Caps: after every cycle \|net_c\| ≤ 0.20 × E_eco + one band, and gross ≤ 1.50 × E_eco + one band |
  | R4 | Stops: every LS_RS short that F4 closed with reason `stop` in the window has the executor's component closed inside the same F4 bar (F4 bar start ≤ executor close time < F4 bar end + 1 h), or earlier, by a stop the executor saw first. Each case is listed. |
  | R5 | No order below the min qty or min notional; skipped deltas logged |
  | R6 | Determinism: two replays give identical ledger hashes |

## 7. E-4: failure tests (mock exchange in memory, plus real public demo endpoints)

| Test | Situation | Required behaviour |
|---|---|---|
| T1 | Crash after an order, before the ledger write | Next run reconciles from the exchange; no duplicate order |
| T2 | Two runs at once | The second exits on the lock; no orders |
| T3 | Stale producer | Frozen; no new opens |
| T4 | Producer hash mismatch | Frozen; no new opens |
| T5 | HTTP 400 on one symbol | Logged; other symbols proceed |
| T6 | Exchange position ≠ ledger | Symbol frozen; alert |
| T7 | Kill switch | Close everything; `halted`; later cycles send nothing until reset |
| T8 | Real public demo endpoints (no key): exchangeInfo, ticker, klines | Parsed filters equal mainnet public filters for the target symbols, or the differences are listed |

## 8. E-5 / E-6 (VM)

- **E-5:** plan mode, hourly, for ≥ 3 days.
  - Signed **read-only** calls with the user's existing demo keys from `.env`: account, `positionRisk`, `positionSide/dual`.
  - Gates: the daily verifier passes, and the plan's orders match a recomputation.
- **E-6:** needs the user's separate yes.
  - Disable the F6 cron lines, enable demo mode.
  - First cycle: reconcile mismatch 0.
- **Shadows:** F4, 16B and PaperN1 keep running unchanged.

## 9. Verifier `src/audits/verify_eco.py` (own code; does not import `src/eco`)

| Check | What it recomputes |
|---|---|
| V1 | E-1 reproduction: from the saved N1 FINAL curve, Calmar and DD per window, compared with the N6 claims |
| V2 | E-2 from the two saved daily series with its own weight code: every candidate's window stats, the acceptance booleans, the selection, DSR, K |
| V3 | 200 random replay cycles: targets from the saved producer inputs with its own fraction code; orders = band rule; caps |
| V4 | Attribution identity and tracking (R1, R2) from the replay ledger |
| V5 | SHAs: protocol lock, claims, code, ECO registry chain |

Changes after the lock go to `logs/eco/CODE_CHANGES_AFTER_LOCK.md`.

## 10. Trial registry

- **Registry:** `logs/eco/trial_registry_eco.csv`, hash-chained. Its genesis line links to the last line hash of `logs/r2_4h_a0/trial_registry.csv`.
- **Budget:** 4 trials, opened by the user's mandate of 2026-10-21. ECO-W1 and ECO-W2 are registered before E-2 runs.
