"""
Independent verifier for the ladder + sessions study (protocol logs/research_ladder_sessions/...PREREGISTERED.md).
Own simple loops, no import of the study code. Checks:
 V1 4h and 1D (K=3, 10 coins): state shares by count and UP/DOWN retracement medians == A1 / A3.
 V2 pooled session mean (bps) for all 10 coins, 2020-01..2026-09 == B1 split 'all'; daily high/low session shares == B3.
 V3 claims JSON == CSV tables; protocol + legs SHA unchanged.
"""
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "research_ladder_sessions"
LEGS = ROOT / "data" / "derived" / "swing_anatomy" / "legs_all.parquet"
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "LTCUSDT", "LINKUSDT"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def v1(legs):
    A1, A3 = pd.read_csv(OUT / "A1_state_shares.csv"), pd.read_csv(OUT / "A3_retracements.csv")
    ok = True
    for tf in ("4h", "1D"):
        cnt = {"UP": 0, "DOWN": 0, "CONTRACTION": 0, "EXPANSION": 0}
        retr = {"UP": [], "DOWN": []}
        for coin in COINS:
            g = legs[(legs.coin == coin) & (legs.tf == tf) & (legs.K == 3.0)].sort_values("start_time")
            highs, lows, lh, ll = [], [], None, None
            states, typs, moves = [], [], []
            for d, sp, ep in zip(g.direction, g.start_price, g.end_price):
                if d == "Rally":
                    if highs:
                        lh = "HH" if ep > highs[-1] else "LH"
                    highs.append(ep)
                    typs.append("H")
                else:
                    if lows:
                        ll = "HL" if ep > lows[-1] else "LL"
                    lows.append(ep)
                    typs.append("L")
                moves.append(abs(ep - sp))
                s = None
                if lh and ll:
                    s = {"HHHL": "UP", "LHLL": "DOWN", "LHHL": "CONTRACTION", "HHLL": "EXPANSION"}[lh + ll]
                states.append(s)
                if s:
                    cnt[s] += 1
            for i in range(1, len(states)):
                if states[i] == "UP" and typs[i] == "L" and moves[i - 1] > 0:
                    retr["UP"].append(moves[i] / moves[i - 1])
                if states[i] == "DOWN" and typs[i] == "H" and moves[i - 1] > 0:
                    retr["DOWN"].append(moves[i] / moves[i - 1])
        tot = sum(cnt.values())
        for s, c in cnt.items():
            ref = A1[(A1.tf == tf) & (A1.state == s)].share_count.iloc[0]
            if abs(c / tot - ref) > 1e-12:
                ok = False
                print(f"V1 FAIL {tf} {s}: {c / tot} vs {ref}")
        for k in ("UP", "DOWN"):
            a = np.array(retr[k])
            a = a[(a > 0) & (a < 1)]
            ref = A3[(A3.tf == tf) & (A3.kind == k)]["median"].iloc[0]
            if abs(np.median(a) - ref) > 1e-9:
                ok = False
                print(f"V1 FAIL retr {tf} {k}: {np.median(a)} vs {ref}")
    print("V1", "PASS" if ok else "FAIL")
    return ok


def v2():
    B1, B3 = pd.read_csv(OUT / "B1_session_returns.csv"), pd.read_csv(OUT / "B3_daily_high_low_session.csv")
    sess_of = lambda h: "Asia" if h < 8 else "Europe" if h < 13 else "US" if h < 21 else "LateUS"
    per_coin, hl = [], {"high": {}, "low": {}}
    for coin in COINS:
        d = pd.read_csv(ROOT / "data" / "universe_all" / "1h" / f"{coin}_1h_full.csv.gz", parse_dates=["timestamp"])
        d = d[(d.timestamp >= "2020-01-01") & (d.timestamp < "2026-10-01")].sort_values("timestamp").reset_index(drop=True)
        r = np.log(d.close.values[1:] / d.close.values[:-1])
        t = d.timestamp.iloc[1:]
        df = pd.DataFrame(dict(day=t.dt.normalize().values, s=[sess_of(h) for h in t.dt.hour], r=r))
        per_coin.append(df.groupby(["day", "s"]).r.sum().rename(coin))
        d["day"] = d.timestamp.dt.normalize()
        for kind, col, fn in (("high", "high", "idxmax"), ("low", "low", "idxmin")):
            idx = getattr(d.groupby("day")[col], fn)()
            for h in d.loc[idx, "timestamp"].dt.hour:
                s = sess_of(h)
                hl[kind][s] = hl[kind].get(s, 0) + 1
    M = pd.concat(per_coin, axis=1)
    ok = True
    for s in ("Asia", "Europe", "US", "LateUS"):
        m = M.xs(s, level="s").mean(axis=1).mean() * 1e4
        ref = B1[(B1.split == "all") & (B1.sess == s)].mean_bps.iloc[0]
        if abs(m - ref) > 1e-9:
            ok = False
            print(f"V2 FAIL session {s}: {m} vs {ref}")
        for kind in ("high", "low"):
            share = hl[kind][s] / sum(hl[kind].values())
            refh = B3[B3.sess == s][kind].iloc[0]
            if abs(share - refh) > 1e-12:
                ok = False
                print(f"V2 FAIL {kind} {s}: {share} vs {refh}")
    print("V2", "PASS" if ok else "FAIL")
    return ok


def v3():
    c = json.loads((OUT / "claims_ladder_sessions.json").read_text())
    ok = c["protocol_sha256"] == sha(OUT / "LADDER_SESSIONS_PROTOCOL_PREREGISTERED.md") == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0]
    ok &= c["legs_sha256"] == sha(LEGS)
    A1, A3, B2, F = (pd.read_csv(OUT / f) for f in ("A1_state_shares.csv", "A3_retracements.csv", "B2_session_consistency.csv", "A6_fibonacci_test.csv"))
    for tf, v in c["up_share_K3"].items():
        ok &= abs(round(A1[(A1.tf == tf) & (A1.state == "UP")].share_count.iloc[0], 4) - v) < 1e-12
    for tf, v in c["retr_median_UP"].items():
        ok &= abs(round(A3[(A3.tf == tf) & (A3.kind == "UP")]["median"].iloc[0], 4) - v) < 1e-12
    for r in B2.itertuples():
        ok &= c["session_verdicts"][r.sess] == r.verdict
    n = int(((F.tf.isin(["5m", "15m", "1h", "4h", "1D", "1W"])) & (F.ci_lo > 0)).sum())
    ok &= c["fib_tfs_positive"] == n and c["fibonacci_clustering"] == (n >= 4)
    print("V3", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    legs = pd.read_parquet(LEGS, columns=["coin", "tf", "K", "direction", "start_time", "start_price", "end_price"])
    res = [v1(legs), v2(), v3()]
    print("ALL PASS" if all(res) else "SOME FAIL")
