# S2: code changes after the lock

## 1. D1: the pre-2020 rows lack the bookkeeping column "half"
- R6 and R24 ran as locked (both FAIL, verified). The first D1 run stopped BEFORE any model was trained, at `pre[train.columns]`: the main training rows carry a `half` column (A/B split label) that the pre-2020 rows do not have.
- Fix: `pre.reindex(columns=train.columns)`. `half` is NaN for pre rows. It is not a model feature, only used to select rows. Nothing else changed.
- Code SHA before: 01b1b5502d652cf78acab571f12b95e185188f49a0d18729b49ffd781d4dfc7e
- Code SHA after: ba93bb62a3d888a92b474d0246972b976034b736d71e8f1f536522b8ffa33bfc
