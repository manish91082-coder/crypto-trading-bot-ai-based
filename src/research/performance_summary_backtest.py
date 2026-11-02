"""Descriptive summary of the BACKTEST (2021-01-01..2026-09-30, research costs) for the user's questions: trade win rate,
average win / loss, risk-reward, monthly worst / average / best, and 12-month paths of $10,000 from every start month.
Systems: LO = spot long-only M_AI3 50 % (F7 OFF_LO, = Step 27) and RS = long-short with the F7 risk rules (F7 primary).
Uses the verified F7 engine and inputs (G0-reproduced); no new strategy, no gate. Output: logs/performance_summary/."""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import f7_run as R
import f7_risk as F
from config import LOGS_DIR
OUT = LOGS_DIR / "performance_summary"
OUT.mkdir(parents=True, exist_ok=True)
C = json.loads((R.OUT / "claims.json").read_text())["MAIN"]

I = R.load("MAIN")
res = {}
for name, inv_s, rules in (("LO", 0.0, {}), ("RS", R.F50, R.RS)):
    sl = {k: F.sim_ls(I["rows"]["AI"][k], I["grids"][k], I["decide"][k], I["spot"][k], I["perp"][k], I["fund"], R.F50, inv_s,
                      R.N_HOLD, R.KEEP, R.C_LONG, R.C_SHORT, **rules) for k in ("D1", "H4", "H1")}
    for k in sl:                                               # same engine + inputs as F7 -> must equal the verified finals
        ref = C["OFF_LO" if name == "LO" else "RS"]["sleeves"][k]["final"]
        assert abs(sl[k]["final"] - ref) < 0.01, (name, k, sl[k]["final"], ref)
    tr = pd.concat([v["trades"].assign(sleeve=k) for k, v in sl.items()], ignore_index=True)
    tr["ret"] = tr.pnl / tr.cost
    tr.to_csv(OUT / f"trades_{name}.csv", index=False)
    eq = pd.read_csv(R.OUT / f"equity_MAIN_AI_{'OFF_LO' if name == 'LO' else 'RS'}.csv", parse_dates=["date"]).set_index("date").M_AI3
    res[name] = (tr, eq)

def trade_stats(t):
    w, l = t[t.pnl > 0], t[t.pnl <= 0]
    return dict(trades=len(t), win_rate_pct=round(100 * len(w) / len(t), 1), avg_win_pct=round(100 * w.ret.mean(), 2),
                avg_loss_pct=round(100 * l.ret.mean(), 2), payoff_ratio=round(w.ret.mean() / -l.ret.mean(), 2),
                profit_factor=round(w.pnl.sum() / -l.pnl.sum(), 2), avg_trade_pct=round(100 * t.ret.mean(), 2))

out = {}
for name, (tr, eq) in res.items():
    o = dict(all=trade_stats(tr))
    for side in ("long", "short"):
        if (tr.side == side).any():
            o[side] = trade_stats(tr[tr.side == side])
    for k in ("D1", "H4", "H1"):
        o[f"sleeve_{k}"] = trade_stats(tr[tr.sleeve == k])
    me = eq.groupby(eq.index.to_period("M")).last()
    mr = (me / me.shift(1).fillna(10_000.0) - 1) * 100
    mr.to_csv(OUT / f"monthly_returns_{name}.csv", header=["ret_pct"])
    o["monthly"] = dict(months=len(mr), positive_pct=round(100 * (mr > 0).mean(), 1), mean_pct=round(mr.mean(), 2),
                        median_pct=round(mr.median(), 2), worst_pct=round(mr.min(), 2), worst_month=str(mr.idxmin()),
                        best_pct=round(mr.max(), 2), best_month=str(mr.idxmax()), p10_pct=round(mr.quantile(0.10), 2),
                        p90_pct=round(mr.quantile(0.90), 2))
    m2 = mr[mr.index >= pd.Period("2022-01")]
    o["monthly_excl_2021"] = dict(months=len(m2), positive_pct=round(100 * (m2 > 0).mean(), 1), mean_pct=round(m2.mean(), 2),
                                  median_pct=round(m2.median(), 2), worst_pct=round(m2.min(), 2), best_pct=round(m2.max(), 2))
    # 12-month paths of $10,000 starting at every month start with 12 full months after it
    g = (1 + mr / 100).values
    paths = np.array([10_000 * np.cumprod(g[i:i + 12]) for i in range(len(g) - 11)])
    starts = [str(mr.index[i]) for i in range(len(g) - 11)]
    q = lambda a, p: float(np.percentile(a, p))
    tbl = pd.DataFrame({"month": range(1, 13),
                        "worst": paths.min(0).round(0), "p10": [round(q(paths[:, m], 10)) for m in range(12)],
                        "median": [round(q(paths[:, m], 50)) for m in range(12)], "p90": [round(q(paths[:, m], 90)) for m in range(12)],
                        "best": paths.max(0).round(0)})
    tbl.to_csv(OUT / f"year_paths_{name}.csv", index=False)
    end12 = paths[:, -1]
    o["year_paths"] = dict(n_windows=len(paths), first_start=starts[0], last_start=starts[-1],
                           end12_worst=round(end12.min()), end12_worst_start=starts[int(end12.argmin())],
                           end12_median=round(float(np.median(end12))), end12_best=round(end12.max()),
                           end12_best_start=starts[int(end12.argmax())], share_end12_below_10k_pct=round(100 * (end12 < 10_000).mean(), 1),
                           worst_drawdown_inside_any_window_pct=round(100 * max(float(((np.maximum.accumulate(np.r_[10_000, p]) - np.r_[10_000, p]) / np.maximum.accumulate(np.r_[10_000, p])).max()) for p in paths), 1))
    o["year_2022_path"] = [round(x) for x in 10_000 * np.cumprod((1 + mr[(mr.index >= pd.Period("2022-01")) & (mr.index <= pd.Period("2022-12"))] / 100).values)]
    o["table"] = tbl.to_dict("records")
    out[name] = o
(OUT / "summary.json").write_text(json.dumps(out, indent=2, default=str))
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "table"} for k, v in out.items()}, indent=1, default=str))
for k in out:
    print(k); print(pd.DataFrame(out[k]["table"]).to_string(index=False))
