# LPT-1: live intraday paper-trading desk, 10,000 USDT paper. Pre-registered 2026-10-29, before the first paper order

## 1. The request (user, chat, 2026-10-29, summarised)
- **Research from scratch:** how a master crypto trader or an AI would trade live, aiming for 10–15% daily compounding intraday on 10k USDT. Spot, futures or both; which factors; which methods; how much risk; what to do after a win and after a loss; how the top intraday winners learn; how decisions follow the current market.
- **Then run it:**
  - choose roles;
  - pull live market data;
  - paper-trade with own judgement and keep logs;
  - plan and decide freely;
  - do not stop before the goal;
  - only real, verified evidence, with no fakes, no hallucination and no rubber stamping.

## 2. What is known before the first trade (evidence, not opinion)
**Compounding arithmetic** (`research_math_output.txt`):
- 10%/day turns 10k into 174k in 30 days, 3.0 M in 60 days and about 1.3 × 10¹⁹ in a year.
- 15%/day turns it into 662k in 30 days.

**Perfect foresight** (a "god-mode" trader who is always on the right side of every bar whose move beats the round-trip fee; BTC futures, 1x, 2024-01 … 2026-09):

| Bar | Median day | Days ≥ +10% |
|---|---|---|
| 5m | +8.9% | 44% |
| 1h | +5.4% | 13% |
| 1d | +1.1% | 0.4% |

So 10%/day at 1x needs near-perfect prediction on short bars. Otherwise it needs leverage, and leverage multiplies losses the same way.

**Monte Carlo** (30 days, 5 trades/day, ±1R, fee 0.1R):

| Win rate | Risk per trade | P(average 10%/day reached) | P(a −50% drawdown) |
|---|---|---|---|
| 55% (already a strong edge) | 10% | 0.14% | 74% |
| 60% | 10% | 3.8% | 35% |
| any of 50–60% | 1% | 0 | 0 |

**Studies of real day traders:**
- **Brazil** (Chague, De-Losso, Giovannetti 2019/2020, mini-index futures, regulator data): 97% of those who day-traded 300+ days lost money; about 1% earned more than the minimum wage.
- **Taiwan** (Barber, Lee, Liu, Odean, Review of Asset Pricing 2020): the vast majority of day traders lose; aggregate performance is negative; 97% are likely to lose in future day trading.
- **Renaissance Medallion,** the best-documented track record: about 66% per **year** gross over 1988–2018.

**This project's own evidence:**
- no price-only rule beats fees below about 1 hour (oracle 9m, fee-hurdle map, BTC-ALLTF 1m–30m);
- non-price signals are real but smaller than fees (NP1–NP4);
- only 8h–1d trend formulas survive fees (TF atlas, ECO).

**Prior expectation written down now:** the 10–15%/day goal will almost certainly not be met on a sustained basis. The desk runs anyway, honestly, to measure what disciplined discretionary intraday trading actually does after fees. Every day's result is reported against the goal.

## 3. Roles (one person, separate duties; the code enforces the hard limits)
| Role | Duty |
|---|---|
| Data engineer | `lpt.py snapshot`: live public data, saved with sha256 (Binance spot mirror data-api.binance.vision; Bybit linear for futures context and futures prices) |
| Market analyst | reads the snapshot: regime (BTC trend, breadth), trend on 5m/1h/4h, ATR, VWAP, prior-day high/low, volume, taker flow, book imbalance, funding, OI change, long/short ratio |
| Strategist (decision maker) | picks a setup from the playbook (§5) or no trade, with a written reason, **before** the outcome |
| Risk manager (code) | rejects any order that breaks §4 |
| Execution (code) | market orders walk the live order book; stops and targets are filled by the watcher at the live best bid/ask once crossed |
| Journal / auditor | hash-chained logs (`decisions.jsonl`, `fills.jsonl`, `daily.jsonl`, `snapshots.jsonl`) and minute equity (`equity.csv`); an independent verifier re-checks fills against official 1m klines afterwards |

## 4. Hard risk rules (in `lpt.py`, RISK)
- **Per trade:** risk ≤ 1% of equity (stop distance × qty, plus fees). Every order has a stop. Reward/risk ≥ 1.5 when a target is given.
- **Limits:** at most 3 open positions; gross exposure ≤ 3× equity; spot is long only.
- **Daily loss limit −3%:** the watcher closes everything and no new trade is allowed that UTC day.
- **Flat by 23:55 UTC** (intraday).
- **Fees:** deploy/fees.json BNB taker (spot 0.075%, futures 0.036%) on every fill; futures funding from the Bybit funding history.

**Behaviour rules** (written; followed and logged by the strategist):
- After 2 losses in a row, pause 60 minutes.
- After −2% on the day, half size.
- No averaging down, and no moving a stop away from the price.
- No revenge trades; no size increase after wins beyond the 1% rule.

## 5. Playbook (the only setups the strategist may take)
| Setup | Conditions | Stop / target |
|---|---|---|
| A, trend pullback | 4h and 1h trend agree; price pulls back to the 1h EMA20 / VWAP area; 5m momentum turns back in the trend direction (RSI5m reset, taker flow agrees) | beyond the pullback swing, about 1× ATR1h; target the prior high/low or PDH/PDL, ≥ 1.5R |
| B, level break | close beyond the prior-day high/low or a clear range edge; volume ratio > 1.5, taker flow and OI agree | back inside the range; target ≥ 2R |
| C, flush reversal | move > 2× ATR1h in one direction within an hour; crowded positioning (long/short ratio or funding extreme); OI dropping (liquidations); RSI5m extreme | beyond the wick; target VWAP, ≥ 1.5R |

**No trade when:**
- the spread is > 5 bps or ATR1h < 0.3%;
- in the first 15 minutes after 00:00 UTC;
- within 30 minutes of a scheduled major US macro release (checked when known);
- the setup is not clearly one of A/B/C.

Doing nothing is a valid decision and is logged.

## 6. Evaluation (written before the results)
- **Daily:** start and end equity; return vs the +10% and +15% goals.
- **After every 20 closed trades and at day 14:**
  - net P&L after fees and funding;
  - win rate; mean R per trade; profit factor; max drawdown;
  - fees as a share of gross;
  - comparison with BTC buy-and-hold over the same window;
  - comparison with a random-entry baseline (same symbols, sides, stop/target distances and holding limit, entries at random minutes, recomputed from official 1m klines).
- **A claim of skill requires:** mean R > 0 with a one-sided t-test p ≤ 0.05 over ≥ 60 trades, **and** better than the random-entry baseline. Before that, results are descriptive only.
- **Independent verification:** every fill price is checked against the official 1m kline range of its minute (±spread), fees and funding are recomputed, the equity path is rebuilt, and the hash chain is validated.

## 7. Honest limits
- **Futures prices are Bybit linear perps,** a proxy, because Binance futures endpoints are blocked from this laptop. Fees are Binance's.
- **Paper fills** walk the real book at that moment but do not move it, and qty step / minimum notional are not enforced.
- **The watcher polls every ~3 s,** so a stop can fill worse than its level (realistic) but never better than the book.
- **Gaps:** if the laptop sleeps or the network fails, the watcher cannot act; such gaps are logged and reported, never hidden.
- **Not advice:** this is paper trading and research, not investment advice. No real order is sent anywhere.

मैं लाइसेंसशुदा वित्तीय सलाहकार नहीं हूँ।
