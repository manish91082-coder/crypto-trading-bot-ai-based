"""Independent verifier for the A1 correction (A0 amendment 2). Own code paths where possible.
C1 every 'new_realtime' trade marked failed_later: its pivot is a live confirmation (non-flip event) later flagged failed, and no
   final pivot (legs_all 4h K=3 start/end) has that pivot time+price
C2 every unexplained diff (new non-failed / old_only / changed gross) lies within 12 days of a same-candle tie in legs_all
C3 all new trades re-simulated with an own loop from 4h bars (gross, exit idx) to 1e-9
C4 trades identical to the original A1 outside the diff set (count and gross)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "research"))
import swing_anatomy_phase1 as SA       # data loading + the zigzag itself (the object under test is the timeline replay)

res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


C = R_ / "logs" / "r2_4h_a1" / "correction"
d = pd.read_csv(C / "signal_diff.csv", parse_dates=["entry_time"])
N = pd.read_parquet(C / "a1c_trades.parquet")
O = pd.read_parquet(R_ / "logs" / "r2_4h_a1" / "a1_trades.parquet")
legs = pd.read_parquet(R_ / "data" / "derived" / "swing_anatomy" / "legs_all.parquet", columns=["coin", "tf", "K", "start_time", "end_time", "start_price", "end_price"])
g4 = legs[(legs.tf == "4h") & (legs.K == 3.0)]

c1 = True
newf = d[(d.kind == "new_realtime") & (d.failed_later == True)]
for coin, gc in newf.groupby("coin"):
    h = SA.load_spliced(coin, "1h", [])
    b = SA.clip_atr(SA.agg(h, "4h"))[0]
    ev = []
    SA.SS.zigzag_pivots(b, 3.0, ev)
    et = SA.end_times("4h", b.timestamp.values)
    ts = b.timestamp.values
    failed = [e for e in ev if not e["flip"] and e["failed"]]
    finals = set(zip(g4[g4.coin == coin].start_time, g4[g4.coin == coin].start_price.round(8))) | \
        set(zip(g4[g4.coin == coin].end_time, g4[g4.coin == coin].end_price.round(8)))
    for r in gc.itertuples():
        hit = [e for e in failed if pd.Timestamp(et[e["confirm_idx"]]) == r.entry_time]
        good = bool(hit) and all((pd.Timestamp(ts[e["pivot_idx"]]), round(e["ref_price"], 8)) not in finals for e in hit)
        c1 &= good
ok("C1", c1 and len(newf) > 0, f"{len(newf)} new trades at later-failed pivots: each is a live confirmation flagged failed and absent from the final pivots")

ties = g4[g4.duplicated(["coin", "start_time"], keep=False)][["coin", "start_time"]]
odd = d[((d.kind == "new_realtime") & (d.failed_later != True)) | (d.kind == "old_only")]
chg = d[(d.kind == "same") & ((d.gross - d.gross_old).abs() > 1e-9)]
odd = pd.concat([odd, chg])
near = [bool(((ties[ties.coin == r.coin].start_time - r.entry_time).abs() <= pd.Timedelta(days=12)).any()) for r in odd.itertuples()]
ok("C2", all(near), f"{len(odd)} other differences (timing / spurious / changed gross): all within 12 days of a same-candle pivot tie: {sum(near)}/{len(near)}")


def sim(o, h, l, c, stop0, A):
    best = -np.inf
    for k in range(60):
        if k > 0:
            best = max(best, h[k - 1])
        tr = max(stop0, best - 3 * A)
        if l[k] <= tr:
            return k, min(o[k], tr)
    return 59, c[59]


key = ["signal", "coin", "side", "entry_time"]
newt = N.merge(d[d.kind == "new_realtime"][key], on=key)
mx, cache = 0.0, {}
for r in newt.itertuples():
    if r.coin not in cache:
        x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{r.coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
        x["timestamp"] = pd.to_datetime(x["timestamp"]); x = x.set_index("timestamp").sort_index()
        gg = x.groupby(x.index.floor("4h"))
        cache[r.coin] = pd.DataFrame(dict(open=gg.open.first(), high=gg.high.max(), low=gg.low.min(), close=gg.close.last())).dropna()
    b = cache[r.coin]
    e = b.index.get_loc(r.entry_time)
    s = 1 if r.side == "long" else -1
    o_, h_, l_, c_ = (s * b.open.values[e:e + 60], s * (b.high if s > 0 else b.low).values[e:e + 60],
                      s * (b.low if s > 0 else b.high).values[e:e + 60], s * b.close.values[e:e + 60])
    k, px = sim(o_, h_, l_, c_, o_[0] - r.R_price, r.atr)
    mx = max(mx, abs((px - o_[0]) / r.R_price - r.gross), abs(k - r.exit_idx))
ok("C3", mx < 1e-9 and len(newt) > 0, f"{len(newt)} new trades re-simulated with own loop: max |diff| {mx:.1e}")

same = d[d.kind == "same"]
diffset = set(map(tuple, odd[key].astype(str).values))
o2 = O.merge(N[key + ["gross"]], on=key, suffixes=("", "_n"))
o2 = o2[[tuple(map(str, t)) not in diffset for t in o2[key].values]]
ok("C4", len(o2) == len(O) - int((d.kind == "old_only").sum()) - len(chg) and np.abs(o2.gross - o2.gross_n).max() < 1e-12,
   f"{len(o2)} trades outside the diff set identical to the original A1 (gross max diff {np.abs(o2.gross - o2.gross_n).max():.1e})")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
