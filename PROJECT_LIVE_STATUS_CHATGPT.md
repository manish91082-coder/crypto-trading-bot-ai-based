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
- **Main base SHA for current slice:** 61c316bd6da647409ad8e83473ad3785ce5502f8.
- **Merged model-promotion safety:** PR #4 merge commit 6f8765f6c18ecfdfee5fec7c3b37d3f7f4f4826; post-merge regression workflow passed on merge SHA and the subsequent main status update SHA. Step 4 writes to research candidates, not production. Paper engine requires a valid promoted manifest and SHA-verified model files.
- **1D strategy remains FAIL / live readiness NO-GO:** candidate scores remain below the 0.42 floor in the final-model research replay, all six final-model backtest configs produced zero trades, and three walk-forward XGBoost folds fail the documented >0.52 AUC criterion.
- **New issue confirmed in both Step 5 and paper engine:** in the non-bullish BTC regime, an unconditional `p_long >= 0.42` branch bypassed configured thresholds 0.44/0.46. This made the "threshold" comparisons dishonest in that regime. The current branch introduces a shared hard-threshold gate: every regime must pass the configured threshold; the bearish regime additionally requires non-negative relative momentum or the documented pullback/stop-distance/volume confluence.
- **Current branch:** `research/1d-oos-economic-replay`, PR not yet opened while exact-head validation is prepared.
- **OOS economics work:** Step 4 now writes fold-specific XGBoost predictions for every feature-complete timestamp; only resolved labels are used for AUC. A new research-only replay uses those fold-specific OOS scores, the existing Step 5 spot simulator, strict per-fold price cutoffs, and no entries in the last 14 fold days. It evaluates only the existing thresholds 0.42/0.44/0.46 and capital scenarios 120/10,000, does not choose a winner, and does not use holdout data.
- **Cost/claim limitations:** the economic diagnostic includes the Step 5 taker-fee model but not dynamic slippage, market impact, latency or partial-fill costs. It must not be called a complete net-profit acceptance or live readiness test.
- **Holdout rule:** 2025-01-01 through 2026-09-30 remains excluded from any fitting, OOS features/labels, model selection, threshold selection or economic replay. The raw reader in the new diagnostic stops at each fold's end before parsing later OHLCV fields.
- **Acceptance:** pending PR exact-head regression suite and research pipeline. Even if the pipeline executes successfully, strategy acceptance remains FAIL unless OOS evidence meets stated criteria; green Actions only proves deterministic execution/diagnostic integrity.
- **4H:** NOT STARTED. **USD 10,000 live readiness:** NO-GO. **Live signing/public broadcast:** BLOCKED.
- **Next exact action:** open the PR, inspect all focused tests and the completed OOS economic artifact, reconcile any simulation-accounting failures, and then decide the next research correction based only on recorded evidence.

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

### 2026-10-12 — merged feature parity CI confirmed
- Queried the completed post-merge Actions run `38260964537` for code merge SHA `83eba8840898146cff2ed43bd6f86560e3130d38`; conclusion: **success**. Logs show `Ran 10 tests` and `OK`.
- The latest `main` tip before this continuity refresh was `74fce94a4e9c2cda857b824772e20677c89210af`; that commit only refreshed this status file after the merge. The code merge itself is now verified by a successful post-merge run.
- This still does not run or certify the full multi-year trading backtest, independent exchange-data provenance, or $10,000 live execution. Next phase remains end-to-end 1D reproducibility and accounting reconciliation.

### 2026-10-12 — research-only reproducibility workflow authored
- Branch `fix/1d-reproducible-research` was created from main SHA `0d93fbcc38970a020372cbd97618ae33020e03e4`.
- Made `INITIAL_CAPITAL` environment-configurable with finite-positive validation, retaining USD 120 as the default.
- Updated `src/pipeline_1d/step3_features_and_labels_7d.py` to stream only rows through `2024-12-31`; it stops reading once the first post-cutoff timestamp is encountered and does not parse the holdout price/volume fields into the research dataframe.
- Updated `src/pipeline_1d/step4_pooled_walkforward_training.py` to fail closed unless all four temporal OOS folds have finite AUC/sample counts, save per-direction fold CSVs, and set XGBoost `n_jobs=1` for more deterministic reruns.
- Updated `src/pipeline_1d/step5_pooled_governed_backtest.py` to write every tested configuration's metrics, correctly named threshold-0.44 selected ledgers, spot and futures daily-equity ledgers, and MTM components (`cash + open_allocated_capital + floating_pnl`).
- Added `tests/test_1d_research_boundary.py` to prove the research loader stops before parsing post-cutoff prices and rejects unordered rows.
- Added `requirements-1d-research.txt` with fixed direct dependency versions and `src/audits/run_1d_research_reproducibility.py` to run the research chain, two capital scenarios, accounting checks, dependency capture, raw-data audit, hashes and before/after sealed-vault checksum checks.
- Added `.github/workflows/1d-research-reproducibility.yml`; it runs on PR to main or manual workflow dispatch, executes all focused tests and the bounded research-only chain, then uploads logs/ledgers/models/metrics/manifests.
- No CI verdict is claimed until the workflow actually executes on this branch. No 4H or live-trading code was changed in this slice.

### 2026-10-12 — reproducibility results and strategy-failure diagnosis
- Research-only workflow run 38262463632 on head a8ed19aa4c70f6866cc5731d46d8c3e6f5a18114 completed all steps and uploaded 24 artifacts. Runner artifact ZIP digest from GitHub: sha256:5f03f8030c8502ee5494ca71061fd73eb4c97887791829ef4e28bce47771c515.
- The report showed 1,139 samples per symbol from 2021-11-05 through 2024-12-17 after 35-row warm-up and 14-row censor window. Resolved and censored label counts are retained in the artifact.
- Fold OOS AUC evidence from that run: Long [0.6330786, 0.4169374, 0.5421262, 0.5023380]; Short [0.5288187, 0.6177276, 0.5067404, 0.5785655]. These do not satisfy the documented requirement that every fold exceed 0.52.
- Step 5 produced zero trades at thresholds 0.42, 0.44, 0.46 for Spot and Futures under both capital scenarios. Ledgers and arithmetic reconcile only because no trade was executed; this must never be read as a performance PASS.
- Added configurable MIN_WALK_FORWARD_OOS_AUC (default 0.52), src/audits/strategy_acceptance.py, tests for failed AUC/zero-trade gates, Step 4 probability/threshold diagnostics, Step 5 per-coin model-score distribution diagnostics, and a runner manifest separating reproducibility_status from strategy_acceptance_status.
- The research reproducibility workflow is designed to exit successfully when execution/accounting and artifacts are reproducible while marking strategy acceptance FAIL. This helps diagnose without concealing failure; no threshold is changed automatically.
- Exact latest-head workflow verdict has not yet been read at checkpoint time.

### 2026-10-12 — PR #3 merged; actual 1D strategy gate is FAIL
- Merged PR #3 as commit 3ec4226a60da62a4751bcd409dccd2e49b2ba8d5. The PR-head research reproducibility workflow passed on e1ec7a9067a40c471fdec16de32aa2d1708acab6; the post-merge focused regression workflow passed on merge SHA 3ec4226a60da62a4751bcd409dccd2e49b2ba8d5 in run 38263832075.
- The research-run manifest separates reproducibility_status=PASS from strategy_acceptance_status=FAIL and full_strategy_acceptance=NOT_CERTIFIED.
- Exact evidence: all six tested Step 5 threshold/config combinations generated zero trades in both capital scenarios; final models' global maximum scores were 0.3660297 Long and 0.3386222 Short, below the lowest entry threshold of 0.42.
- XGBoost OOS AUC did not meet the source-documented >0.52 criterion on all folds. Long: [0.6330786, 0.4169374, 0.5421262, 0.5023380]; Short: [0.5288187, 0.6177276, 0.5067404, 0.5785655].
- A test fixture error in revision 75210c2740d0323bda0dff1afce1ce749d7c8459 caused one strategy-gate regression test to fail; it was corrected at e1ec7a9067a40c471fdec16de32aa2d1708acab6 and all 15 tests passed.
- The earlier finished research run used research rows through 2024-12-31 and verified the separate vault CSV hashes were unchanged. It did not claim OOS profitability or live readiness.
- Next: inspect label/execution economic equivalence and create a research-only OOS net-return diagnostic. Do not lower thresholds or retune on the sealed holdout without evidence.

### 2026-10-12 — isolate unaccepted model candidates from paper execution
- Added `MODELS_1D_CANDIDATE_DIR = models/1d_pooled_candidate`; Step 4 writes candidate models here and leaves `models/1d_pooled` untouched.
- Step 4 writes a candidate manifest with model-file hashes, processed feature/label hashes, feature schema, training date span, horizon/purge values, package versions, fold AUCs and gate reasons. Any fold <= MIN_WALK_FORWARD_OOS_AUC yields `promotion_status=REJECTED`; an all-fold pass yields only `PENDING_HOLDOUT_AND_REVIEW`, never an automatic promotion.
- Step 5 and the research-only runner now use candidate paths exclusively, allowing diagnostics without overwriting model files used by paper execution.
- Added `src/model_provenance.py`; paper engine now loads production models only when `production_model_manifest.json` explicitly marks the bundle PROMOTED, strategy acceptance PASS, exact feature order, all required gates PASS and both model SHA256 digests valid.
- Added nine focused model-provenance/promotion tests. The current known candidate set fails the research gate, and no promoted production manifest is known. Blocking paper-engine startup in this state is intentional, not a claim that paper/trading is ready.
- This slice is on branch `fix/1d-model-promotion-gate`; exact-head CI has not yet been verified. No 4H changes made.

### 2026-10-12 — candidate/production model separation verified
- Added `src/model_provenance.py`; introduced separate `MODELS_1D_CANDIDATE_DIR` and retained `MODELS_1D_POOLED_DIR` solely for production artifacts.
- Step 4 now writes candidate models and a hash-backed candidate manifest only to the candidate directory. It assesses all four XGBoost OOS AUC folds in both directions; any score <= 0.52 rejects the candidate, and even a complete passing set would only become PENDING_HOLDOUT_AND_REVIEW (never automatic promotion).
- Step 5 and the reproducibility runner now load candidate model files and record the candidate manifest; they do not overwrite production artifacts.
- Paper engine now checks an explicit production_model_manifest.json, PROMOTED status, strategy acceptance PASS, exact feature-column order, all required validation gates PASS, and model SHA256 matches before loading models. Missing/invalid approval blocks engine startup, as no model is currently accepted.
- Added nine tests for failed/missing/incomplete candidate evidence, manifest gates, feature order and hash checks, and valid manifest verification. Full suite passed 24 tests.
- Research workflow 38264701208 succeeded on code SHA ecf8cc660269f125ef6e19c00b0e5754c000ece2. Its exact log recorded candidate rejection: Long AUC 0.416937/0.502338 and Short AUC 0.506740 fail the >0.52 fold gate. Step 5 candidate replay still produced zero trades at every threshold in both capital scenarios; strategy status remains FAIL.
- No production models were overwritten and no 4H strategy code was changed.

### 2026-10-12 — PR #4 merged: rejected candidates isolated from execution
- PR #4 merged to main as `6f8765f6c18ecfdfee5fec7c3b37d3f7f4f4826f`.
- Exact PR-head SHA `7ccc6dcf032033c8eb6d05c0d3e713b56994f592` passed the full research-only workflow (Actions run `38264997404`) and the full focused test suite (24 tests). Artifact digest: `sha256:7d8dc5e3b7c2110875620a299a291a17b6db4ca5dbf747bbfa5b6b962824fc33`.
- Candidate model manifest reported REJECTED with these specific reasons: Long fold 2 AUC 0.4169373526 <= 0.52; Long fold 4 AUC 0.5023380387 <= 0.52; Short fold 3 AUC 0.5067403856 <= 0.52.
- Step 5 replay from candidate models produced zero trades in all six variants at both $120 and $10,000. Strategy gate remains FAIL, and no threshold was changed.
- Paper engine now refuses models unless an explicit production manifest proves promotion status, strategy acceptance PASS, all required gates PASS, exact feature order, and model SHA256 integrity. No such accepted manifest is currently verified.
- At this status update, post-merge action `38265233191` was still in progress; final run status remains to be checked separately.

### 2026-10-12 — add strict fold-isolated 1D OOS economic replay
- Added fold-specific OOS score ledgers from each expanding-window training model. Predictions are exported for every feature-complete timestamp in the fold; AUC/precision calculations remain limited to resolved labels.
- Added `src/audits/oos_economic_replay.py`: for each fold, it streams raw OHLCV only through that fold end, reconstructs causal shared features, verifies ATR_14 and Vol_Accum_Ratio parity against the OOS score ledger, and runs Step 5's long-only spot execution simulator.
- Signal entries are limited to the fold start through fold-end-minus-14-days, so no new signal requires prices from a later test fold. OOS threshold rows are reported individually at existing 0.42, 0.44, 0.46 settings; thresholds are not tuned.
- Per-fold, threshold and capital ledgers save trade outcomes joined to resolved target labels, daily MTM equity, net realized PnL per the Step 5 taker-fee model, end-of-fold open positions and accounting identity error.
- Diagnostic explicitly excludes dynamic slippage, market impact, latency and partial-fill cost. It cannot certify formal after-all-costs profitability or live readiness.
- Fixed a logic defect in both Step 5 and the paper engine: the bearish-regime unconditional 0.42 branch bypassed configured 0.44/0.46 thresholds. Both now use `src/strategy_signals.py` so the configured threshold is a hard floor; bearish entries additionally require relative momentum or documented confluence.
- Added focused regression tests for hard-threshold behavior and fold/holdout boundaries. Exact-head CI is pending.
