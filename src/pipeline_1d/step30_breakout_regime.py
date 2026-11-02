"""
Step 30: daily resistance breakout in a pre-defined bull regime (BTC > SMA200), 10-day hold, after cost.
Protocol: logs/strategy_1d_step30_breakout/STEP30_PROTOCOL_PREREGISTERED.md (SHA256 locked before any result).
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import core_rows_1d as CR
import step13_unseen_coins_1d as S13
import step15_slow_relative_1d as S15
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import swing_anatomy_phase1 as P
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step30_breakout"
PROTO = "STEP30_PROTOCOL_PREREGISTERED.md"
HOLD, COST, STRESS, SEED = 10, 0.0025, 0.0040, 30
MAIN = (pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-30"))
PRE = (pd.Timestamp("2018-02-01"), pd.Timestamp("2019-12-31"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def net(o_in, o_out, cost):
    return o_out / o_in * (1 - cost) / (1 + cost) - 1


def events(data, last, members, start, end, cost):
    """Break events of member coins + the same-day member baseline (10-day returns, next-open entry)."""
    btc = data["BTCUSDT"]
    btc = btc[btc.timestamp <= last["BTCUSDT"]].set_index("timestamp").close
    regime = (btc > btc.rolling(200, min_periods=200).mean())
    mem = members[(members.date >= start) & (members.date <= end)]
    by_coin = {s: set(g.date) for s, g in mem.groupby("symbol")}
    fwd, ev = {}, []
    for s, days in by_coin.items():
        df = data[s]
        df = df[df.timestamp <= last[s]].reset_index(drop=True)
        sup, res = P.sr_nearest(df)
        ts, o, c = df.timestamp.values, df.open.values, df.close.values
        pos = {t: i for i, t in enumerate(pd.DatetimeIndex(ts))}
        for d in days:
            i = pos.get(d)
            if i is None or i < 1 or i + 1 + HOLD >= len(df):
                continue
            r = net(o[i + 1], o[i + 1 + HOLD], cost)
            fwd[(s, d)] = r
            if np.isfinite(res[i - 1]) and c[i] > res[i - 1]:
                ev.append(dict(symbol=s, date=d, level=res[i - 1], close=c[i], net=r))
    Ev = pd.DataFrame(ev)
    F = pd.DataFrame([dict(symbol=k[0], date=k[1], net=v) for k, v in fwd.items()])
    base = F.groupby("date").net.median()
    Ev["base"] = Ev.date.map(base)
    Ev["excess"] = Ev.net - Ev.base
    Ev["regime_on"] = Ev.date.map(regime).fillna(False).astype(bool)
    return Ev.sort_values(["date", "symbol"]).reset_index(drop=True)


def ci(x, months, reps=2000, seed=SEED):
    um = np.unique(months)
    idx = {m: np.where(months == m)[0] for m in um}
    rng = np.random.default_rng(seed)
    bs = [x[np.concatenate([idx[m] for m in rng.choice(um, len(um))])].mean() for _ in range(reps)]
    return dict(n=int(len(x)), mean_pct=round(float(x.mean() * 100), 4), ci_low_pct=round(float(np.percentile(bs, 2.5) * 100), 4),
                ci_high_pct=round(float(np.percentile(bs, 97.5) * 100), 4), win=round(float((x > 0).mean()), 4))


def summarize(Ev):
    out = {}
    for name, m in (("ON", Ev.regime_on), ("OFF", ~Ev.regime_on), ("ALL", Ev.regime_on | ~Ev.regime_on)):
        d = Ev[m]
        mo = d.date.dt.to_period("M").astype(str).values
        out[name] = dict(net=ci(d.net.values, mo), excess=ci(d.excess.values, mo),
                         years={int(y): round(float(g.net.mean() * 100), 3) for y, g in d.groupby(d.date.dt.year)})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    claims = dict(protocol_sha256=h_)
    split = pd.read_csv(S15.SPLIT)
    B = set(split[split.half == "B_confirm"].symbol)
    dk, lk, dn, ln, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", MAIN[1])
    data, last = {**dk, **dn}, {**lk, **ln}
    U = S23.daily_members(data, last, list(dk) + sorted(B & set(data)), 20, MAIN[0], MAIN[1])
    res = {}
    for tag, cost in (("MAIN", COST), ("MAIN_cost040", STRESS)):
        Ev = events(data, last, U, MAIN[0], MAIN[1], cost)
        Ev.to_csv(OUT / f"events_{tag}.csv", index=False)
        res[tag] = summarize(Ev)
        print(tag, json.dumps(res[tag]), flush=True)
    dk, lk, dn, ln, _ = S22.load_pre(S22.PRE / "1d", S22.PRE / "1h", S22.ASOF_PRE)
    data, last = {**dk, **dn}, {**lk, **ln}
    U22 = pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date"], parse_dates=["date"])
    Ev = events(data, last, U22, PRE[0], PRE[1], COST)
    Ev.to_csv(OUT / "events_PRE.csv", index=False)
    res["PRE"] = summarize(Ev)
    print("PRE", json.dumps(res["PRE"]), flush=True)
    claims.update(res)
    M, Mc, Pp = res["MAIN"]["ON"], res["MAIN_cost040"]["ON"], res["PRE"]["ON"]
    g = dict(G1=M["net"]["mean_pct"] > 0 and M["net"]["ci_low_pct"] > 0,
             G2=M["excess"]["mean_pct"] > 0 and M["excess"]["ci_low_pct"] > 0,
             G3=Pp["net"]["mean_pct"] > 0 and Pp["excess"]["mean_pct"] > 0,
             G4=Mc["net"]["mean_pct"] > 0)
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = "PASS" if all(g.values()) else "FAIL"
    claims["gates"] = g
    claims["events_sha256"] = {t: sha(OUT / f"events_{t}.csv") for t in ("MAIN", "MAIN_cost040", "PRE")}
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("GATES", json.dumps(g))


if __name__ == "__main__":
    main()
