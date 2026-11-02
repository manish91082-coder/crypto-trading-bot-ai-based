"""
Independent verifier for Step 30 (logs/strategy_1d_step30_breakout).
V1 hashes. V2 80 random MAIN events + 40 PRE events: the resistance level by brute force (unbroken k = 3 fractal high
above the close of d-1), the break, the BTC SMA200 regime by a plain mean, and the 10-day next-open net return.
V3 means recomputed from the event files; gates re-derived.
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import swing_study_1d as SS
import step13_unseen_coins_1d as S13
import step22_pre2020_exam_1d as S22
import step30_breakout_regime as S30

C = json.loads((S30.OUT / "claims.json").read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(folder, s):
    """The verified research loader (same 99 % wick clip as the pipeline)."""
    return SS.load_1d(s, folder / f"{s}_1d.csv")


def check(tag, folder, n):
    Ev = pd.read_csv(S30.OUT / f"events_{tag}.csv", parse_dates=["date"])
    btc = load(folder, "BTCUSDT")
    for r in Ev.sample(n, random_state=3).itertuples():
        d = load(folder, r.symbol)
        i = int(np.where(d.timestamp == r.date)[0][0])
        hi, cl, o = d.high.values, d.close.values, d.open.values
        best = np.nan
        c = i - 1
        for k in range(3, c - 2):
            if k + 3 > c:
                continue
            if hi[k] == hi[k - 3:k + 4].max() and hi[k] >= cl[c] and (cl[k + 3:c + 1] <= hi[k]).all():
                best = hi[k] if np.isnan(best) else min(best, hi[k])
        assert abs(best - r.level) < 1e-12 and cl[i] > best, (tag, r.symbol, r.date)
        nr = o[i + 11] / o[i + 1] * (1 - 0.0025) / (1 + 0.0025) - 1
        assert abs(nr - r.net) < 1e-12
        j = int(np.where(btc.timestamp == r.date)[0][0])
        on = j >= 199 and btc.close.values[j] > btc.close.values[j - 199:j + 1].mean()
        assert on == r.regime_on, (tag, r.date)
    return Ev


def main():
    assert sha(S30.OUT / S30.PROTO) == (S30.OUT / "PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    for t, h in C["events_sha256"].items():
        assert sha(S30.OUT / f"events_{t}.csv") == h
    print("[V1 PASS] hashes")
    check("MAIN", S13.UNI / "1d", 80)
    check("PRE", S22.PRE / "1d", 40)
    print("[V2 PASS] 120 events: level, break, regime and net re-derived with plain code")
    for t in ("MAIN", "MAIN_cost040", "PRE"):
        Ev = pd.read_csv(S30.OUT / f"events_{t}.csv")
        on = Ev[Ev.regime_on]
        assert abs(round(on.net.mean() * 100, 4) - C[t]["ON"]["net"]["mean_pct"]) < 1e-9
        assert abs(round(on.excess.mean() * 100, 4) - C[t]["ON"]["excess"]["mean_pct"]) < 1e-9
        print(f"   {t}: regime-ON n {len(on)}, mean net {on.net.mean()*100:.3f} %, excess {on.excess.mean()*100:.3f} %")
    M, Mc, Pp = C["MAIN"]["ON"], C["MAIN_cost040"]["ON"], C["PRE"]["ON"]
    g = dict(G1=M["net"]["mean_pct"] > 0 and M["net"]["ci_low_pct"] > 0, G2=M["excess"]["mean_pct"] > 0 and M["excess"]["ci_low_pct"] > 0,
             G3=Pp["net"]["mean_pct"] > 0 and Pp["excess"]["mean_pct"] > 0, G4=Mc["net"]["mean_pct"] > 0)
    assert all(C["gates"][k] == v for k, v in g.items())
    print(f"[V3 PASS] means and gates re-derived: {C['gates']}")


if __name__ == "__main__":
    main()
