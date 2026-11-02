"""Diagnostics on the verified B0 OOS trades (read-only). Every number is recomputed from raw CSVs."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"E:\crypto trading bot ai based 9 oct 2026")
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "src" / "analytics"))
import swing_study_1d as SS
from config import SYMBOLS

tr = pd.read_csv(ROOT / "logs/strategy_1d_step4b/B0_reserve20_equal_trades.csv",
                 parse_dates=["signal_date", "entry_date", "exit_date"])
FR = 0.00125
tr["ret_net"] = tr["pnl"] / tr["cost"] * 100
tr["hold"] = (tr["exit_date"] - tr["entry_date"]).dt.days
data = {s: SS.load_1d(s).set_index("timestamp") for s in SYMBOLS}

# independent re-check of each trade's P&L from raw prices (entry open, exit price) + friction
chk = tr["units"] * tr["exit_price"] * (1 - FR) - tr["units"] * tr["entry_price"] * (1 + FR)
assert (chk - tr["pnl"]).abs().max() < 1e-6, "pnl mismatch"
for _, r in tr.iterrows():
    assert np.isclose(data[r.symbol].at[r.entry_date, "open"], r.entry_price), "entry != raw open"

def block(df, name):
    w, l = df[df.pnl > 0], df[df.pnl <= 0]
    return dict(group=name, trades=len(df), win_rate=round(len(w) / len(df) * 100, 1),
                avg_win_pct=round(w.ret_net.mean(), 2), avg_loss_pct=round(l.ret_net.mean(), 2),
                payoff=round(w.ret_net.mean() / -l.ret_net.mean(), 2), expectancy_pct=round(df.ret_net.mean(), 2),
                pf=round(w.pnl.sum() / -l.pnl.sum(), 2), pnl_usd=round(df.pnl.sum(), 0), avg_hold=round(df.hold.mean(), 1))

print("=== A. overall / by year ===")
rows = [block(tr, "ALL")] + [block(g, str(y)) for y, g in tr.groupby("year")]
cur = tr[tr.entry_date >= "2023-01-01"]
rows.append(block(cur, "2023-26 (final config)"))
print(pd.DataFrame(rows).to_string(index=False))
print("\n=== B. by coin (2023-26 final config) ===")
print(pd.DataFrame([block(g, s) for s, g in cur.groupby("symbol")]).sort_values("pnl_usd").to_string(index=False))
print("\n=== C. exit reasons (2023-26) ===")
print(pd.DataFrame([block(g, s) for s, g in cur.groupby("exit_reason")]).to_string(index=False))

# D. MFE / giveback per trade (raw highs between entry and exit)
mfe, mae = [], []
for _, r in tr.iterrows():
    seg = data[r.symbol].loc[r.entry_date:r.exit_date]
    mfe.append((seg["high"].max() / r.entry_price - 1) * 100)
    mae.append((seg["low"].min() / r.entry_price - 1) * 100)
tr["mfe_pct"], tr["mae_pct"] = mfe, mae
tr["gross_pct"] = (tr.exit_price / tr.entry_price - 1) * 100
cur = tr[tr.entry_date >= "2023-01-01"].copy()
w = cur[cur.pnl > 0]
print("\n=== D. MFE / giveback (2023-26) ===")
print("winners: median MFE %.1f%%, median exit gain %.1f%%, median share of MFE kept %.2f"
      % (w.mfe_pct.median(), w.gross_pct.median(), (w.gross_pct / w.mfe_pct).median()))
print("sum over winners: MFE %.0f%% pts, kept %.0f%% pts" % (w.mfe_pct.sum(), w.gross_pct.sum()))
l = cur[cur.pnl <= 0]
print("losers: %d, of which MFE >= +5%% before losing: %d, MFE >= +10%%: %d"
      % (len(l), (l.mfe_pct >= 5).sum(), (l.mfe_pct >= 10).sum()))
print("losers median MFE %.1f%%, median MAE %.1f%%" % (l.mfe_pct.median(), l.mae_pct.median()))

# E. concentration
s = cur.sort_values("pnl", ascending=False)
tot = cur.pnl.sum()
print("\n=== E. concentration (2023-26) ===")
print("net pnl %.0f | top1 %.0f (%s %s) | top5 %.0f | top10 %.0f | sum of all losers %.0f"
      % (tot, s.pnl.iloc[0], s.symbol.iloc[0], s.entry_date.iloc[0].date(), s.pnl.head(5).sum(), s.pnl.head(10).sum(), l.pnl.sum()))
print(s.head(8)[["symbol", "entry_date", "exit_date", "ret_net", "mfe_pct", "pnl", "exit_reason"]].to_string(index=False))

# F. position within the hindsight K=4 swing leg
legs = pd.read_csv(ROOT / "logs/swing_study_1d/swing_legs_1d.csv", parse_dates=["start_date", "end_date"])
L4 = legs[(legs.K == 4.0) & (legs.direction == "Up")]
pos = []
for _, r in cur.iterrows():
    m = L4[(L4.symbol == r.symbol) & (L4.start_date <= r.entry_date) & (L4.end_date >= r.entry_date)]
    if len(m) != 1:
        continue
    g = m.iloc[0]
    rng = g.end_price - g.start_price
    pos.append(dict(symbol=r.symbol, entry_at=(r.entry_price - g.start_price) / rng,
                    exit_at=(r.exit_price - g.start_price) / rng, leg_move=g.move_pct, pnl=r.pnl))
pos = pd.DataFrame(pos)
print("\n=== F. where in the true (hindsight) K4 up-swing we enter/exit, 0=swing low 1=swing high (2023-26) ===")
print("matched %d/%d trades | median entry_at %.2f | median exit_at %.2f | median captured share %.2f"
      % (len(pos), len(cur), pos.entry_at.median(), pos.exit_at.median(), (pos.exit_at - pos.entry_at).median()))
pos.to_csv(Path(__file__).parent / "swing_position.csv", index=False)
tr.to_csv(Path(__file__).parent / "b0_trades_diag.csv", index=False)
