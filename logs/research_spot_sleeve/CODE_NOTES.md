# Spot sleeve study: code notes

These decisions were made while writing the code. **Each was made before the first run** (the one run's output is `run_stdout.txt`).

1. **S2 halves.** The two halves are two independent single-coin sleeves of 5,000 each (BTC SMA200, ETH SMA200), never rebalanced against each other. The control is run per leg.
2. **S5 rebalance.**
   - Every Tuesday open, holdings go to exact equal weights of the Monday target: the coins not in the target are sold, the overweight holdings are trimmed, and then the rest is bought with the cash.
   - The first draft had a 2% "no-churn" band and no trimming. That is not in the protocol, so it was removed before the run.
3. **Open trades.** A trade still open on the last day is valued at the last close and counted as a trade.
4. **Time in market.**
   - S1/S3/S4/S6: the share of days holding the coin.
   - S5: the share of Mondays with a non-empty target.
   - S2: the share of days where either leg is in.
5. **Speed fix before the run.** The shifted state is computed once per simulation; the first draft shifted it inside the daily loop. No behaviour change.
6. **Verifier note.** V3 checked 20 random Mondays; 11 of them had a non-empty S5 target, so the check is not trivial.
