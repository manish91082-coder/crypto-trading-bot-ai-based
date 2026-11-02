"""POST-HOC (report-only item of N1 that returned NaN in the run: Cf is NaN before a coin's listing and 0*NaN = NaN).
Recomputes the FINAL dev exposure from the saved ledger + equity: net notional per coin at every 1h close.
Gross = sum over coins of |net coin notional| / equity (one-way perp accounting). Does not change any gate."""
import json
from pathlib import Path
import numpy as np, pandas as pd
R_ = Path(__file__).resolve().parents[2]
O1 = R_ / "logs" / "research_n1_portfolio"; DR = R_ / "data" / "derived" / "n1"
cl = json.loads((O1 / "claims_n1.json").read_text())
L = pd.read_parquet(DR / f"trades_{cl['final_name']}.parquet"); L = L[L.w > 0]
eq = pd.read_parquet(DR / f"equity_{cl['final_name']}.parquet")
t = pd.DatetimeIndex(eq.t); H = len(t); curve = eq.equity.values
ms = np.flatnonzero(np.r_[True, t.month[1:] != t.month[:-1]])
Em = np.array([10_000.0 if s == 0 else curve[s - 1] for s in ms])
gross = np.zeros(H); longg = np.zeros(H); shortg = np.zeros(H); cmax = np.zeros(H)
for coin, g in L.groupby("coin"):
    b = pd.read_parquet(DR / "bars1h" / f"{coin}.parquet").close.reindex(t).ffill().fillna(0.0).values
    a = g.a.values.astype(int); E = np.minimum(g.E.values.astype(int), H)
    u = g.side.values * g.w.values / g.entry.values * Em[np.searchsorted(ms, a, side="right") - 1]
    d = np.zeros(H + 1); np.add.at(d, a, u); np.add.at(d, E, -u)
    net = np.cumsum(d[:-1]) * b
    gross += np.abs(net); longg += np.clip(net, 0, None); shortg += np.clip(-net, 0, None); cmax = np.maximum(cmax, np.abs(net))
r = dict(max_gross=float((gross / curve).max()), mean_gross=float((gross / curve).mean()), p95_gross=float(np.quantile(gross / curve, .95)),
         mean_long=float((longg / curve).mean()), mean_short=float((shortg / curve).mean()), max_coin_net=float((cmax / curve).max()))
pd.DataFrame([r]).to_csv(O1 / "N1_exposure_POSTHOC.csv", index=False); print(r)
