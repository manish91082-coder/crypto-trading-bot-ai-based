# ECO amendment 1: stops, outage guard, profit lock, cut-over, tracking check. Pre-registered 2026-10-22, before any of its numbers are computed.

**Parent.** `ECO_PROTOCOL_PREREGISTERED.md` (15a3c837…). Everything there stays in force unless changed here.

**Mandate.** The user, 2026-10-22, said to integrate `PLAN_CONTINUOUS_BRAIN_22_OCT_2026.md` into the ecosystem with the same discipline.

**Scope.**
- Research: §1 trial ECO-T4 and §2 a data check (not a trial).
- Code and tests: §3–§5.
- The demo cut-over (§4) runs only after the gate in §4.1.

## 1. Trial ECO-T4: break-even profit lock on the trend sleeves (A, C)

**Rule.** For every A and C trade (all TFs), with entry `en` and A = ATR14(TF) of the signal bar (the N1 K0 ATR):
1. **Arming hour h1.** The first 1h bar in [entry hour, signal exit) with a favourable excursion ≥ 3 × A. For a long that is high ≥ en + 3A; for a short, low ≤ en − 3A.
2. **Break-even hour h2.** The first 1h bar in [h1 + 1, signal exit) that touches `en`. For a long that is low ≤ en; for a short, high ≥ en.
3. **Fill.** For a long, min(1h open, en); for a short, max(1h open, en). This is the N1 stop-fill convention.
4. **Otherwise** the trade exits on its signal, unchanged.

B and D are unchanged.

**Base.** N1 FINAL (K1 + X2 + X3 + S2 cap), exactly the E-1 curves (dev Calmar 4.160747, P1 5.096377, P2 3.220073).

**Acceptance (all required).**
- (a) The Calmar with the profit lock beats the base in dev, in P1 and in P2.
- (b) DSR ≥ 0.95 on the dev monthly returns, with N = 28. The SR variance is that of the {base, T4} monthly Sharpe ratios.
- (c) The ECO combination (W2 rule, E-2 accounting) with the T4 N1 curve has a dev Calmar ≥ the adopted E-2 value (5.9827).

**Report only:**
- P3;
- the share of A/C trades armed and the share exited at break-even;
- the per-sleeve effect.

**If accepted:**
- The live ECO applies the same rule to N1 A/C components.
- It is checked on closed 1h bars every cycle, using the component's own fill as `en` and A taken from the N1 position's TF (the ATR at its entry bar). PAPER-N1 itself is not changed.
- The suppressed component is released when N1 closes that position.

**If not accepted:** nothing changes.

## 2. Outage guard (data check, not a trial)

**Purpose.** Protection while the VM is down. It is not a strategy stop.

**Rule.** For every coin with a non-zero net position:
- One exchange STOP_MARKET order, `closePosition`, on the demo host only.
- Trigger: the reference price × (1 − D) for a net long, × (1 + D) for a net short.
- The reference is the mark price when the order was placed. The order is replaced only when the mark has moved by more than 10% from the reference, or when the side of the net position flips.

**Choice of D.** It must almost never trigger in normal hourly operation.
- **The check:** count 1h perp bars in `data/futures_um` (all coins, 2020 … 2026-09) with high ≥ (1 + D) × previous close, or low ≤ (1 − D) × previous close.
- **Rule:** D = 0.50 if that share is ≤ 1e-4 of all coin-hours. Otherwise D = 0.60, and the same count is reported.
- **What this means:** with an hourly refresh, the guard can only fire on a move ≥ D within about one cycle, or during an outage.

## 3. Exchange stops for 1D shorts (the F7 rule, as F6 had it)

**Rule.**
- For every 1D short component with a stop S (F4 stop × scale, or 1.50 × its own fill while pending):
  - one STOP_MARKET algo order, `reduceOnly` BUY;
  - quantity = the component quantity, trigger S, `workingType` CONTRACT_PRICE;
  - placed only when the symbol's net position is short and |net| ≥ the sum of the 1D-short component quantities on that symbol;
  - otherwise the hourly virtual check (protocol §3) is the only stop, and this is logged.
- **Sync every cycle:**
  - quantity or stop changed → cancel and re-place;
  - algo status TRIGGERED / FINISHED → the component is treated as stopped (suppressed, as protocol §3);
  - order missing (cancelled or expired) → re-place.
- **Plan mode:** the same logic is computed and logged as "would place / cancel". Nothing is sent.

## 4. Demo cut-over (adopting F6)

### 4.1 Gate

All of the following, then the user's go in chat:
- ECO plan mode has run ≥ 72 cycles.
- `verify_eco_live` showed 7/7 on each of the last 3 days.
- The cut-over tool passes its mock tests.

### 4.2 Steps (tool `src/eco/eco_cutover.py`)

1. Run F6 `--mode plan` and record its view.
2. Remove the two F6 cron lines (backup first, diff = only those lines).
3. Read the demo account: the positions, and the open algo orders on F6's symbols.
4. Cancel the F6 algo stop orders on those symbols (`DELETE /fapi/v1/algoOpenOrders`).
5. Build the ECO demo state:
   - each F6 short becomes held by the 1D component `1D|<sleeve>|S|<symbol>` with its exchange quantity;
   - cash = quantity × mark at cut-over, so ECO equity starts at that moment;
   - `entry_px` = the F6 fill;
   - E0 stays 10,000 eco units, with k from the wallet.
6. The first demo cycle then nets every target against these positions and places the §3 and §2 stop orders.

### 4.3 Shadow and records

- **Shadow.** A second plan-mode instance (`data/eco_shadow`) uses the demo host's public data and the same producers and k. Both instances are recorded.
- **Kept.** The F6 state file stays and is renamed `state_demo_retired_<date>.json`. Nothing is deleted.

## 5. Tracking check TC (forward, replaces the R2 reading; not a trial)

**Daily (UTC):**
- d_day = the change of (demo eco equity − shadow eco equity) over the day, in eco units.
- d_cum = (demo − shadow) since the cut-over.

**Gate after 14 full days:**
- |d_day| ≤ 0.30% of E0 on ≥ 12 of 14 days;
- |d_cum| ≤ 1.0% of E0.

**Report:**
- slippage vs the decision mark;
- rejected orders;
- band skips;
- funding, demo vs public.

**Info only:** shadow vs the paper combination (the F4 / N1 timing effect), i.e. the R2 quantity measured forward.

**If the TC gate fails:** demo continues, and there is no real-money protocol until the cause is found and fixed.

## 6. Verifier additions (`src/audits/verify_eco.py`, own code)

| Check | What it recomputes |
|---|---|
| V6 | ECO-T4: 200 random A/C trades, arming and break-even recomputed from raw 5m → 1h with its own code; the acceptance booleans |
| V7 | Outage guard count, recomputed from the perp files |
| V8 | Mock tests for §3 stop sync and the §4 cut-over (in `test_eco_core.py`) |
