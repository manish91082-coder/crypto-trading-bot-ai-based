# Step 11 run stopped on 2026-10-13 17:17 IST (recorded, not hidden)
The first gate G-sanity FAILED: the planted-signal feature (theoretical AUC ~0.60) was recovered at OOS AUC 0.5512
(required 0.57-0.63; Step 10's simpler training recovered 0.578). Per protocol section 5 all gates must pass, so the
Step 11 decision is FAIL_NOTHING_DEPLOYED regardless of the remaining results. The remaining ~4 hours of computation
were stopped. Evidence: logs/step11_run_stdout.txt ("sanity planted AUC 0.5512").
Diagnosis (method, not market): 80% bootstrap bagging + 1-year half-life time-decay weights reduce the effective
training data and weaken learning. No real-market outcome was looked at for this diagnosis.
