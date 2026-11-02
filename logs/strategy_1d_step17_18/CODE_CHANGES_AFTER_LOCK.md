# Code changes after the protocol lock (bug fixes only; design unchanged)

1. 2026-10-14: first run crashed in the helper `auc_ci` (TypeError: Series.to_period works on the index, not on date
   values) at the first AUC of the G1 sanity stage. No AUC or result had been printed. Fix: convert the dates with
   pd.DatetimeIndex(...).to_period("M").
2. 2026-10-14: the G1 pipeline check did its job and caught a bug. Veto sanity: planted AUC 0.5024, leak AUC 0.504
   (the leak feature IS the label's return, it must give ~1.0). Cause: `auc_ci` paired labels (coin order) with
   predictions (month order) by POSITION through boolean masks; the market table is date-ordered, so the market
   checks were unaffected (planted 0.5823, leak 0.9998). The run was stopped right after G1; no brain-skill or
   trading result had been produced. Fix: predictions are re-indexed onto the label rows (`p.reindex(y.index)`) with
   an assertion that none is missing. Trading code was not affected (it joins predictions by index).
