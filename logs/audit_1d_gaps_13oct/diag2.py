import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(r"E:\crypto trading bot ai based 9 oct 2026")
sys.path.insert(0, str(ROOT/"src")); sys.path.insert(0, str(ROOT/"src"/"pipeline_1d")); sys.path.insert(0, str(ROOT/"src"/"analytics")); sys.path.insert(0, str(ROOT/"src"/"execution"))
import swing_strategy_1d as E
import live_1d_swing_engine as L
OUT = Path(__file__).parent
data = E.load_universe()
cfg, R = L.CFG, L.RESERVE
print("CFG", cfg.key(), "reserve", R)
def m(tr, eq, cash, label):
    x = E.metrics(tr, eq, cash); x = {k: x[k] for k in ("trades","win_rate","profit_factor","final_equity","cagr_pct","max_dd_pct","sharpe")}
    print(label, x); return x
tr, eq, cash = E.simulate(data, cfg, start="2023-01-01", end="2026-09-30", reserve=R)
m(tr, eq, cash, "CONTINUOUS 2023-01-01..2026-09-30:")
print(tr.exit_reason.value_counts().to_dict())
eq["year"] = eq.date.dt.year
ye = eq.groupby("year").equity.last(); prev = pd.concat([pd.Series({2022: 10000.0}), ye]).shift(1).dropna()
print("year returns %:", ((ye / prev.loc[ye.index] - 1) * 100).round(2).to_dict())
# chain with walk-forward 2021 (+98.7634%) and 2022 (-15.17%) from B0 yearly file
yr = pd.read_csv(ROOT/"logs/strategy_1d_step4b/B0_reserve20_equal_yearly.csv")
print(yr[["test_year","OOS_return_exact"]].to_string(index=False))
g21 = (1 + yr.set_index("test_year").loc[[2021, 2022], "OOS_return_exact"]).prod()
final = 10000 * g21 * cash / 10000
print("CHAINED 2021-22 walk-forward x continuous 2023-26 final: %.2f" % final)
yrs = (pd.Timestamp("2026-09-30") - pd.Timestamp("2021-01-01")).days / 365.25
print("CAGR %.2f%%" % (((final / 10000) ** (1 / yrs) - 1) * 100))
tr.to_csv(OUT/"cont_2023_26_trades.csv", index=False); eq.to_csv(OUT/"cont_2023_26_equity.csv", index=False)
# hindsight: final config continuous over whole 2021-2026 (NOT a walk-forward claim)
tr2, eq2, cash2 = E.simulate(data, cfg, start="2021-01-01", end="2026-09-30", reserve=R)
m(tr2, eq2, cash2, "HINDSIGHT final cfg continuous 2021..2026-09:")
