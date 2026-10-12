# PROJECT LIVE STATUS CHATGPT

> Canonical continuity file for the AI Crypto Trading Bot project. Read this file AND inspect the live GitHub `main` HEAD before every work slice. GitHub is the source of truth; a stored SHA is a checkpoint, not a substitute for reading the current branch tip.

## 1. Project lock

- **Canonical repository:** `manish91082-coder/crypto-trading-bot-ai-based`
- **Canonical branch:** `main`
- **Baseline HEAD before continuity tracking:** `6cfa466d27a44a30252cf969e760e0d271523a0f`
- **Initial status-file commit:** `39f12b3c38ac7f48e1d376994cc3d98676e61115`
- **Main SHA inspected immediately before this checkpoint refresh:** `b42ef00532cc185009396b50d5a208d1f8715e81`. This status-file edit itself creates a new commit; always re-read live HEAD after any write.
- **Work order:** fix and verify **1D first**, then fix and verify **4H**. Do not work on 4H strategy code until the 1D acceptance gate passes, except shared infrastructure defects that block 1D.
- **Capital target for research validation:** USD 10,000, configurable and traceable through configuration. A $10,000 backtest is not evidence of live readiness or future profitability.
- **Trading safety lock:** live signing and public transaction broadcast remain **BLOCKED**. Research/backtest and isolated paper simulations only until explicit safety gates are independently evidenced.
- **Business objective:** maximize *risk-adjusted net* profitability and minimize losses after applicable fees, slippage, market impact, gas/relay costs where applicable, limits, and failures. Never optimize gross return alone or represent historical results as guarantees.

## 2. Verified starting facts (evidence from inspected source)

1. `src/config.py` sets `INITIAL_CAPITAL = 120.0`, `MAX_INACTIVITY_DAYS = 14`, `PURGE_WINDOW_DAYS = 14`, and taker fee to `0.00075`.
2. `src/pipeline_1d/step3_features_and_labels_7d.py` sets `EVENT_BARRIER_DAYS = 28` while its docstring describes a 14-day maximum holding window. This is a **specification mismatch to resolve**, not a silently pre-decided patch: reconcile the actual execution/runner rules first, then derive the label horizon and purge/embargo consistently.
3. `src/pipeline_1d/step4_pooled_walkforward_training.py` uses the configured purge window for walk-forward folds. Review boundary semantics and label outcome windows before approving it.
4. The reviewed 1D paper execution path fetches daily candles. Training/live feature equivalence, warm-up windows, candle selection, fees, risk sizing, and order-failure behavior require tested parity.
5. The committed 1D five-year ledger previously inspected contains 175 closed trades and realized PnL of about **+$252.73 from $120**, with maximum drawdown about **31.52%**. Treat this as a repository artifact, not independently reproduced performance.
6. 4H issues reserved for the later phase: labels are generated before the research/holdout cutoff is applied; the holdout simulation has a start but no explicit declared end in the inspected script; the holdout was used to compare/select profiles; and the trade-PnL-implied final balance differs from the equity ledger by about $7.41.
7. GitHub status and Actions were queried for the inspected status-file commits. The latest query for `b42ef00532cc185009396b50d5a208d1f8715e81` returned zero commit statuses and zero workflow runs. The `.github/workflows` directory was not found. CI is **not verified green**.
8. Structural checks of committed OHLCV files do **not** establish authenticity against an independent official exchange source. Do not claim that independent data validation passed unless it is performed and evidence is saved.

## 3. Short execution plan

### Phase 0: establish each work slice
- Read current `main` HEAD, target files, relevant project rules/configuration, current tests and existing logs.
- Record exact evidence (path, symbols/lines or test output, SHA) before editing.
- Make one small, reviewable change set; never overwrite unrelated/legacy files or invent results.

### Phase 1: 1D correctness (active; must finish first)
1. Reconcile label horizon, entry/exit timing, partial take-profit/runner logic, and inactivity rule from source and project rules. Make horizon and purge/embargo derive from the same authoritative configuration where appropriate; handle unresolved labels at dataset boundaries safely.
2. Make training and paper/live feature calculations consistent, including minimum periods, history/warm-up, feature order, NaN policy, and completed-candle selection. Add parity tests.
3. Verify temporal splits, symbol pooling, leakage/purge, model/data version traceability, risk sizing, capital/fee/slippage assumptions and order-failure fallbacks.
4. Add/run focused regression tests, then a deterministic end-to-end research backtest. Reconcile trade ledger, equity curve, net PnL, drawdown and starting/ending capital; store exact commands, outputs and source SHA.
5. Validate USD 10,000 as a configurable research scenario separately from the historical USD 120 outputs. Do not deploy real funds. Freeze only if all required gates pass; otherwise log the failing evidence and continue with the next smallest fix.

### Phase 2: 4H correctness (start only after Phase 1 passes)
1. Generate labels without crossing the research/validation boundary; apply full horizon-aware purge/embargo.
2. Put explicit start **and end** bounds on each split, prevent holdout use in profile/model selection, and use a genuinely untouched final evaluation period.
3. Reconcile every trade against equity/PnL calculations and all trading costs. Add focused tests and reproducible backtest evidence for the USD 10,000 scenario.
4. Confirm a 4H execution path exists and has feature/model parity before making any claim about 4H operational readiness.

### Phase 3: project-wide acceptance gate
- Audit cross-cutting configuration, dependencies, tests, model/data provenance, logs, dynamic provider/RPC handling where applicable, secrets/security, failure handling and documentation.
- Run all feasible tests from a clean environment; record unavailable/blocked checks explicitly.
- Add a CI workflow only when its commands/dependencies are evidence-based and executable; then verify the workflow result against the exact pushed SHA.
- Keep live signing/public broadcast disabled. Final status is PASS / FAIL / BLOCKED with evidence, never a confidence guess.

## 4. Non-negotiable operating constitution

- **Sequence:** INSPECT → VERIFY → DECIDE → PATCH → TEST → COMMIT/PUSH → VERIFY LIVE SHA → CHECK CI → UPDATE THIS FILE → NEXT.
- **Zero-trust evidence:** source code, generated reports, CSV ledgers and prior assistant statements are claims until independently recalculated or reproducibly tested. Preserve provenance.
- **No fabricated execution:** never claim a command ran, a test passed, a file was committed, a workflow succeeded, or a live trade filled without tool-returned evidence.
- **No drift:** this repository only; no other repo unless explicitly authorized. 1D before 4H. Do not silently change project objectives or trading rules. Resolve contradictions against repository rules and execution semantics before editing.
- **Dynamic configuration:** avoid duplicating strategy constants across code. Use a single authoritative config/environment interface, validate it at startup, and fail closed for invalid or missing critical values. Never commit secrets.
- **Risk-first objective:** optimize net, risk-adjusted performance with drawdown, downside tails, liquidity, trade frequency, concentration, fees/slippage and failure modes reported. Profit is not guaranteed.
- **Safe modes:** no real-money signing, no public broadcast, and no bypass of safety gates. Paper fallback must be labeled as paper and must never be mistaken for an exchange fill.
- **Efficient quality:** one small, testable slice per user command `next`; no sprawling audit detours. Test the relevant slice immediately. Expand checks only when evidence or regression risk requires it.
- **Continuity updates:** at the end of each meaningful work response, update this file with the last inspected HEAD, change/commit SHA, evidence/tests, gate status, blockers and exact next action. Re-read the current file SHA before updating it. Do not claim automatic background saving; updates happen when a Git-connected work action is actually executed.

## 5. Current checkpoint

- **Checkpoint date:** 2026-10-12 (Asia/Kolkata).
- **Verified current `main` HEAD before this status update:** `83eba8840898146cff2ed43bd6f86560e3130d38`.
- **1D label/purge correction:** merged in `6bacc94ddd5c2a1f72f8cf0a9c6a042bcc29931a`; five focused label tests passed on the PR head and merge commit.
- **1D feature parity correction:** PR [#2](https://github.com/manish91082-coder/crypto-trading-bot-ai-based/pull/2) merged as `83eba8840898146cff2ed43bd6f86560e3130d38`.
- **Focused tests:** 10/10 passed on code revision `e0cf247cb3fa7d42fd83840895a38ae4464488b1` in Actions run `38260712274`. The tested revision included both label tests and feature parity tests. A subsequent change before merge only updated this continuity file. A post-merge run on `83eba8840898146cff2ed43bd6f86560e3130d38` was queued/in progress at the latest check; do not call that exact post-merge run green until its conclusion is read.
- **Initial feature-test run:** run `38260700101` failed because the workflow did not install `joblib`; the workflow dependency list was corrected, then all 10 tests passed in run `38260712274`. The initial failure is recorded, not hidden.
- **Shared feature rules:** `src/features_1d.py` is the canonical per-symbol 1D feature implementation and timestamp-aligned BTC relative momentum calculation. The research pipeline and paper engine now call the same feature helper, matching rolling windows and warm-up behavior. Missing BTC alignment stays NaN, and paper predictions block on non-finite required inputs.
- **Training safety:** final pooled training refuses empty, non-binary or single-class resolved targets after censoring/purge. Fold evaluation skips invalid train/test targets.
- **1D status:** NOT ACCEPTED until post-merge CI is verified, the full reproducible research/backtest runs, and data/provenance and trade/equity reconciliation gates pass.
- **4H:** NOT STARTED for fixes; 1D remains first.
- **USD 10,000 live readiness:** NOT VERIFIED; **NO-GO**.
- **Live signing/public broadcast:** BLOCKED.
- **Next exact action:** verify the post-merge Actions result on `83eba8840898146cff2ed43bd6f86560e3130d38`; then run the deterministic 1D research/backtest chain from a clean environment and reconcile sample counts, trade ledger, equity, fees, final capital and drawdown before any acceptance claim.

## 6. Append-only work log

### 2026-10-12 — checkpoint initialized
- Evidence baseline: GitHub `main` HEAD `6cfa466d27a44a30252cf969e760e0d271523a0f`.
- Read `src/config.py`, `src/pipeline_1d/step3_features_and_labels_7d.py`, and `src/pipeline_1d/step4_pooled_walkforward_training.py` from that SHA.
- Verified the 14-day vs 28-day specification mismatch in source.
- No strategy code changed by this checkpoint. This status file records the plan and known gates only.

### 2026-10-12 — continuity file and CI state rechecked
- Created the status file on `main` in commit `39f12b3c38ac7f48e1d376994cc3d98676e61115`; subsequently updated it in commit `b42ef00532cc185009396b50d5a208d1f8715e81`.
- Read the committed file back from GitHub; the live branch HEAD was checked after each write.
- The status query for commit `b42ef00532cc185009396b50d5a208d1f8715e81` returned zero statuses and the Actions API returned zero workflow runs. This is **not** a passing CI result.
- No trading code changed. Next: bounded 1D label/execution/purge trace.

### 2026-10-12 — 1D label/purge correction submitted for verification
- Source-of-rule evidence: `docs/AI_Quant_Master_Rules.md` states the label target/horizon must mirror execution and forbids calendar timeout of a winning runner. `src/pipeline_1d/step7_full_5year_governed_backtest.py` and `src/execution/order_manager.py` also specify event-driven exits with no calendar timeout. User authorization in this conversation permits the requested, scoped correction despite the historical code-freeze note.
- In `src/config.py`, added validated `LABEL_OBSERVATION_HORIZON_DAYS` and made `PURGE_WINDOW_DAYS` configurable; a purge shorter than the observation horizon fails closed.
- In `src/pipeline_1d/step3_features_and_labels_7d.py`, removed synthetic timeout-price labels, mark unresolved samples as NaN, evaluate the entry candle, enforce pessimistic same-candle stop/target collisions, and account conservatively for the configured break-even stop.
- In `src/pipeline_1d/step4_pooled_walkforward_training.py`, exclude censored labels from both train/test folds and use a strict train cutoff to prevent samples whose label window touches the test boundary.
- Added `tests/test_1d_labeling.py` and `.github/workflows/1d-label-regression.yml`. GitHub Actions had returned zero runs immediately after workflow creation; successful execution is still pending.
- Work-branch commits: config `87446fec89008f275aa4f3f8ca7e06dfb8489136`; labels `96fbcbad3ac9ed718612189b020491d9d61232fe` and cleanup `60fd5d4727044f0a3b8084fb9d24ebb99e5a8be6`; walk-forward `7482fe17527bc63f9ee36350b8d5d6a1a8dc622f`; tests `7e7d2f51874d19bb25eaff3c865a111963575858`; workflow `6a1ecc02cf63a185c17b438d249ea55e5299a5ca`.
- No performance claims are changed or certified by this code correction. Full 1D pipeline acceptance remains blocked pending tests and end-to-end reproducibility.

### 2026-10-12 — first 1D correction merged and validated
- Opened PR #1 for the scoped 1D label/purge correction; it was merged by squash as `6bacc94ddd5c2a1f72f8cf0a9c6a042bcc29931a`.
- Five regression tests passed on PR head `997e0eb3f2dc2def39734c7604e38e996874db35` in Actions run `38259767487`; the same workflow passed on the merge commit in Actions run `38259889946`.
- Test cases: entry-candle TP evaluation; pessimistic same-candle stop/target collision; conservative break-even stop; unresolved-window censoring rather than timeout exit; incomplete-tail rows remain unlabeled.
- This verifies the focused label slice only. No full pipeline/backtest was run and no profitability/live-readiness claim is made.

### 2026-10-12 — 1D feature parity slice prepared
- Baseline `main` SHA inspected: `0d6e9f533f7069c47b7ee061a8fda882a8addf47`.
- Added `src/features_1d.py` as the canonical source for 1D base formulas and timestamp-aligned BTC relative momentum; raw OHLCV non-finite values and inconsistent OHLC values fail closed.
- Updated `src/pipeline_1d/step3_features_and_labels_7d.py` to use the canonical helper for research features.
- Updated `src/execution/paper_engine.py` to use the same helper, removed divergent rolling-window minimums, avoid zero-filling missing BTC returns, and block predictions for non-finite required features.
- Updated `src/pipeline_1d/step4_pooled_walkforward_training.py` to refuse final model fitting when no valid two-class target remains.
- Added `tests/test_1d_features.py` and extended the focused workflow dependencies for paper-engine parity tests.
- Relevant commits on work branch: shared feature engine `4f4570ae7d3f8bf59cddc5831860be85eb3daa92`; training wrapper `25831f2ad06b96a58c1bef4d2be7dabcf3874d43`; live shared use `190efc8b5bc8d2a2ea11746cf45163057de9a9ee`; target validation `6d923e12fb85d5a291143962ac76c053025529e0`; fail-closed final training `f01218f4956fd050402a755511d8200dcb4a172e`; live invalid-feature guard `1a6e7be0703a4cf5ec4604e5f4707eeaa838357e`; parity tests `bbebd0791b3e8f6d90607243a9b7c8964c265fea`; dependency update `e0cf247cb3fa7d42fd83840895a38ae4464488b1`.
- CI on the latest branch SHA is in progress at time of writing; no test pass is claimed for this slice yet.

### 2026-10-12 — feature parity correction merged
- PR #2 merged into `main` as `83eba8840898146cff2ed43bd6f86560e3130d38`; branch `main` was re-read and verified at this SHA before this status-file update.
- Exact tested code revision `e0cf247cb3fa7d42fd83840895a38ae4464488b1` passed all 10 focused tests in GitHub Actions run `38260712274`. Tests included label behavior, research/paper parity for every configured feature, missing BTC alignment, training warm-up windows, invalid OHLC, and invalid supervised targets.
- A prior run `38260700101` on a revision that added the new test but predated the dependency fix failed with `ModuleNotFoundError: No module named 'joblib'`. Workflow dependencies were then corrected and the next 10-test run passed. No failure was suppressed.
- The PR-head delta after the 10-test successful code SHA was only a `PROJECT_LIVE_STATUS_CHATGPT.md` checkpoint edit; this is verified by GitHub compare.
- Post-merge workflow `38260964537` for merge SHA `83eba8840898146cff2ed43bd6f86560e3130d38` was queued/in progress at the time of this checkpoint update; its final status must be fetched before calling post-merge CI green.
- No full 1D backtest or $10,000 live-readiness test was run in this slice.
