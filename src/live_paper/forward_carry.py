"""T2-CARRY (2026-11-02): forward paper test of cash-and-carry, protocol logs/carry_t2_2026_11_02/T2_PROTOCOL_PREREGISTERED.md. Long Binance spot + short Bybit
linear perp, equal entry notional, BTC and ETH, held continuously. Each run recomputes the whole position from public bars and funding history, so a laptop
outage loses nothing, then appends one hash-chained record and rewrites carry_series.csv. No orders are sent anywhere.
Usage: python src/live_paper/forward_carry.py"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lpt                                                                    # noqa: E402
import recover                                                                # noqa: E402

LOG = lpt.PROJ / "logs/carry_t2_2026_11_02"
FREEZE = LOG / "carry_freeze.json"
CHAIN = LOG / "carry_forward.jsonl"
SERIES = LOG / "carry_series.csv"
START = "2026-11-02T08:00:00Z"
END = "2027-01-31T08:00:00Z"
COINS = ("BTCUSDT", "ETHUSDT")
CAPITAL = 10_000.0
NOTIONAL = 2_500.0                                                            # per coin; capital = 2 x total notional
HOUR = 3_600_000
FUNDING_STEP = 8 * HOUR
N_EVENTS = 270
HURDLE_PCT = 0.188
MAX_DD_PCT = 2.0
MIN_MARGIN = 0.25


def ms(s):
    return int(pd.Timestamp(s).value // 10 ** 6)


def spot_1h(sym, t0, t1):
    out, cur = {}, t0
    while cur < t1:
        d = lpt.get(f"{lpt.BIN}/klines", dict(symbol=sym, interval="1h", startTime=cur, endTime=t1 - 1, limit=1000))
        if not d:
            break
        for x in d:
            out[int(x[0])] = float(x[1]), float(x[2]), float(x[3]), float(x[4])
        cur = int(d[-1][0]) + HOUR
    return out


def perp_1h(sym, t0, t1):
    out, end = {}, t1 - 1
    while end >= t0:
        d = lpt.get(f"{lpt.BYB}/kline", dict(category="linear", symbol=sym, interval="60", start=t0, end=end, limit=1000))["result"]["list"]
        if not d:
            break
        for x in d:
            out[int(x[0])] = float(x[1]), float(x[2]), float(x[3]), float(x[4])
        end = min(int(x[0]) for x in d) - 1
    return out


def funding(sym, t0, t1):
    out, end = {}, t1
    while end > t0:
        d = lpt.get(f"{lpt.BYB}/funding/history", dict(category="linear", symbol=sym, startTime=t0 + 1, endTime=end, limit=200))["result"]["list"]
        if not d:
            break
        for x in d:
            out[int(x["fundingRateTimestamp"])] = float(x["fundingRate"])
        if len(d) < 200:
            break
        end = min(int(x["fundingRateTimestamp"]) for x in d) - 1
    return {t: r for t, r in out.items() if t0 < t <= t1}


def coin_rows(sp, pp, fr, fs, ff, t0, t1, n=NOTIONAL):
    """hourly rows of one coin; sp / pp = {open_ms: (o, h, l, c)}, fr = {event_ms: rate}, closed bars only. A missing bar raises: nothing is filled in."""
    s0, p0 = sp[t0][0], pp[t0][0]
    qs, qp = n / s0, n / p0
    entry = n * (fs + ff)
    events = sorted(fr)
    last = max(t for t in sp if t in pp)
    rows, fc, i, nf = [], 0.0, 0, 0
    for t in range(t0, min(last + HOUR, t1), HOUR):
        s, p = sp[t], pp[t]
        close = t + HOUR
        while i < len(events) and events[i] <= close:
            tau = events[i]
            fc += fr[tau] * qp * pp[tau - tau % HOUR][0]
            nf += 1
            i += 1
        ex = fs * qs * s[3] + ff * qp * p[3]
        basis = qs * (s[3] - s0) - qp * (p[3] - p0)
        rows.append(dict(t=close, funding=fc, n_funding=nf, basis=basis, cost=entry + ex, pnl=basis + fc - entry - ex, margin=(n - qp * (p[1] - p0) + fc) / (qp * p[1])))
    return rows


def combine(per_coin, capital=CAPITAL):
    """C-MIX series: hours present on every coin; drawdown runs from the starting capital"""
    n = min(len(r) for r in per_coin.values())
    out, peak = [], capital
    for j in range(n):
        eq = capital + sum(r[j]["pnl"] for r in per_coin.values())
        peak = max(peak, eq)
        out.append(dict(t=per_coin[COINS[0]][j]["t"], equity=eq, dd=eq / peak - 1, margin=min(r[j]["margin"] for r in per_coin.values())))
    return out


def summarize(per_coin, mix):
    last = {c: r[-1] for c, r in per_coin.items()}
    return dict(hours=len(mix), last_close=mix[-1]["t"], equity=mix[-1]["equity"], net_pct=100 * (mix[-1]["equity"] / CAPITAL - 1), max_dd_pct=-100 * min(m["dd"] for m in mix),
                min_margin=min(m["margin"] for m in mix), n_funding={c: x["n_funding"] for c, x in last.items()}, funding={c: x["funding"] for c, x in last.items()},
                basis={c: x["basis"] for c, x in last.items()}, cost={c: x["cost"] for c, x in last.items()})


def verdict(s, complete):
    """the locked decision; before FORWARD_END only INTERIM, except the early margin FAIL"""
    if s["min_margin"] < MIN_MARGIN:
        return "FAIL (margin)"
    if not complete:
        return "INTERIM"
    if any(n != N_EVENTS for n in s["n_funding"].values()) or s["hours"] != 2160:
        return "INCONCLUSIVE"
    return "PASS" if s["net_pct"] > 0 and s["net_pct"] >= HURDLE_PCT and s["max_dd_pct"] < MAX_DD_PCT else "FAIL"


def main():
    t0, t1 = ms(START), ms(END)
    now = lpt.now_ms()
    if now < t0 + HOUR:
        print(f"T2-CARRY {lpt.iso()}  waiting for the first closed bar after {START}")
        return
    if not FREEZE.exists():
        raw = (lpt.PROJ / "deploy/fees.json").read_bytes()
        r = json.loads(raw)["rules"]
        FREEZE.write_text(json.dumps(dict(frozen_utc=lpt.iso(), start=START, end=END, fees_sha256=hashlib.sha256(raw).hexdigest(), fs=r["paper_spot_per_side"],
                                          ff=r["paper_futures_taker_per_side"]), indent=1), encoding="utf-8")
    fz = json.loads(FREEZE.read_text(encoding="utf-8"))
    recover.repair_log(CHAIN, lpt.iso()[:10], False)
    stop = min(now - now % HOUR, t1)                                          # closed hours only
    per = {}
    for c in COINS:
        per[c] = coin_rows(spot_1h(c, t0, stop), perp_1h(c, t0, stop + HOUR), funding(c, t0, stop), fz["fs"], fz["ff"], t0, t1)  # +1 bar: an event at stop needs that hour's open
    mix = combine(per)
    s = summarize(per, mix)
    v = verdict(s, stop >= t1)
    keys = ("t", "equity", "dd", "margin")
    body = "\n".join([",".join(keys + tuple(f"{c}_{k}" for c in COINS for k in ("pnl", "funding", "basis", "n_funding")))] +
                     [",".join([repr(m[k]) for k in keys] + [repr(per[c][j][k]) for c in COINS for k in ("pnl", "funding", "basis", "n_funding")]) for j, m in enumerate(mix)]) + "\n"
    tmp = SERIES.with_suffix(".tmp")
    tmp.write_bytes(body.encode("utf-8"))  # bytes, so Windows does not turn \n into \r\n and break the chained SHA
    tmp.replace(SERIES)
    lpt.append_chain(CHAIN, dict(utc=lpt.iso(), summary=s, verdict=v, series_sha256=hashlib.sha256(body.encode()).hexdigest()))
    print(f"T2-CARRY {lpt.iso()}  hours {s['hours']}  funding events {s['n_funding']}  equity {s['equity']:.2f}  net {s['net_pct']:+.3f}%  maxDD {s['max_dd_pct']:.3f}%  "
          f"margin {s['min_margin']:.3f}  {v}")


if __name__ == "__main__":
    main()
