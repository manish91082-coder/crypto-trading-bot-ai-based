# N5 code notes: choices where the protocol is silent (written BEFORE the official run)

1. **±inf as missing.** Some features hit a zero denominator:
   - donch: high20 = low20;
   - RSI: no losses in the window;
   - vol_z: std = 0;
   - whale ratio: 0 trades.

   The smoke test on a scratch copy crashed on `Input X contains infinity` in the logistic model. Infinite values are now set to NaN, i.e. treated as missing. The HGB handles NaN natively; L imputes the training median and sets the missing flag. The smoke test's numbers were not looked at; it only checked that the pipeline runs.
2. **The verifier's PIT replay (A1)** skips feature values that are non-finite in both the stored row and the replay. A replayed ±inf is compared against the stored NaN as "both missing".
