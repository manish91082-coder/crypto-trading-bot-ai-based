# Phase 2: code changes after the lock

## 1. Two structurally empty feature columns removed from the model input
- First run: G0 PASS (7,425 events; 7,203 = 97.0 % matched to Phase 1 legs; max factor difference 0.0). Then the first walk-forward model crashed inside sklearn's HGB binning ("window shape cannot be larger than input array shape").
- Cause: `c_htf_state_4h` and `c_htf_state_1h` are NaN for EVERY event. The protocol defines htf states "only for higher timeframes, NaN otherwise", and 4h / 1h are never higher than 4h / 8h / 12h / 1D. An all-NaN column carries no information and crashes the binning.
- Fix: these two columns are excluded from the model input. An assertion now checks that they are all NaN. All other 23 factors + tf_code are unchanged. No result (AUC, money) had been computed before the fix.
- Code SHA before (`src/research/swing_ai_phase2.py`, as locked): 163ede4d86431a35c219afb1955f14715e30f6175405e075be06d158afc2b1c0
  (The verifier, as locked and unchanged: 5803e0c0f31f6267a46ca5366171e797fd35ac5b530791de61be9b67ab27ae9f. Its SHA was printed here by the grep that wrote this file.)
- Code SHA after: 78ef419dee5af3061beeee313d3c81c2bf6c8d94baa9710b42ea7f819abbb138
