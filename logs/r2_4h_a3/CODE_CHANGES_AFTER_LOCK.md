# A3 changes after the protocol lock (49bd3f5e…)

**Coding bug (not a design change).**
- The DataFrame column `take` was read as `X.take`, which in pandas is the built-in `DataFrame.take` method, not the column.
- The first run crashed right after the main walk-forward fit, before any gate or result was computed or seen.
- The second run was stopped by hand, because one occurrence (`p3.take`) was still left.
- Every access is now `X["take"]`. Nothing else changed.
