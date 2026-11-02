# Step 8 — AI that must PROVE it decides entries and exits (pre-registered 2026-10-13, before any Step 8 result)

Why Step 7 failed: its predictions had no out-of-sample relation to real outcomes (rank corr -0.03), it took 95% of
candidates, and a label-shuffled copy did as well. Its acceptance rule only looked at portfolio profit. Step 8 therefore
adds SKILL GATES that a fake / lucky / hard-coded model cannot pass.

## Universe (survivorship-free, primary)
30 coins (10 + 20 extended, incl. LUNA/FTT/EOS/MATIC). Each year trade only the point-in-time top 10 by trailing
365-day USDT volume (same rule as Step 6.4). Models learn from all 30 coins' history (more examples, all causal).
Spot, long-only, $10,000, fee 0.075% + slippage 0.05% per fill, 20% reserve, 8 slots, 2% risk cap, 15% DD pause.

## The AI decides two things
1. ENTRY brain — for every real-time swing up-event (K = 2/3/4) on a coin: probability that this is a RIGHT entry.
   Label (triple barrier from the next open): price reaches entry + 2 ATR before entry - 1.5 ATR within 30 days
   (both touched the same day = down first, conservative; neither = wrong entry). Label known on the touch / day 30.
2. EXIT brain — for every day an entry is open (up to 60 days): probability that EXITING NOW is right.
   Label (from the next open): price reaches -1 ATR before +1.5 ATR within 20 days (same-day both = down first;
   neither = hold was right).
Features: causal raw price/volume and swing-structure only (multi-scale returns, distance to recent highs/lows in ATR,
volume vs 30-day average, candle shape, swing events/ages of K2/K3/K4, swing leg sizes, BTC swing state and returns,
market breadth; exit brain adds the open trade's own state: gain, best gain, giveback, days held, entry probability).
Model: HistGradientBoostingClassifier (max_depth 3, 300 iters, lr 0.05, min_samples_leaf 100, l2 1.0).
CONTINUOUS LEARNING: both brains re-trained on the 1st of every month only on rows whose label was known before then.

## Trading policy (the AI decides; no hand-written entry/exit signal)
* Enter if P(right entry) >= the training base rate of right entries (i.e. better than average); rank by P.
* Exit at the next open if P(exit now right) >= max(0.5, training base rate).
* Safety only: catastrophic stop 1.5 ATR below entry, and a K4 opposite swing backstop (both also in the baseline).

## Skill gates (ALL measured out-of-sample, 2021-01..2026-09, monthly walk-forward)
G1 ENTRY skill: AUC >= 0.55, bootstrap 95% CI lower bound > 0.50, AND above the label-shuffled control's AUC;
   realised right-entry rate of the top prediction quintile > bottom quintile.
G2 EXIT skill: same four conditions for the exit brain.
G3 PORTFOLIO: on the point-in-time universe the AI system's Calmar > BASELINE (take every swing event, same stop +
   K4 backstop, no AI) AND > CONTROL (same pipeline with shuffled training labels).
Decision:
* all of G1, G2, G3 pass -> deploy the full AI to testnet;
* G1 + G3 pass with the entry brain only (exit = stop + K4 backstop) -> deploy entry-AI only;
* otherwise FAIL: nothing new is deployed, the failure is reported as is. No re-tuning after seeing OOS results;
  any change = a new protocol with a new number.

## Anti-drift / anti-false-claim rules (apply to every report from now on)
1. This file's SHA256 is recorded before running; every result file stores it.
2. Every number in the report is read from `claims.json` written by the pipeline; `verify_step8_claims.py` recomputes
   each claim from the raw output files and fails loudly on any mismatch.
3. A background process is called "running" only with proof: live PID + heartbeat younger than 30 minutes + exchange
   balances/orders matching the bot state (`health_check_1d.py`, run hourly by the scheduler, log kept).
4. Live model drift: every month the live models' AUC on newly completed live/backtest labels is logged; AUC < 0.52
   for 3 consecutive months = alert in the health log.
