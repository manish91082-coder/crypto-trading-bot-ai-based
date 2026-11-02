"""PAPER-SPOT-S1 recorder (logs/paper_spot_s1/PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md). Paper only: public Binance spot data,
NO orders, no keys. Daily after 00:00 UTC: for every decision day D from the last recorded D + 1 to yesterday (catch-up),
in = close_D > SMA200(close up to D); fill at the open of D + 1; one hash-chained ledger line per D.
Usage: python src/execution/paper_spot_s1.py [--root data/paper_spot_s1] [--now "2026-10-26 00:15"]"""
import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
PROTO = R_ / "logs" / "paper_spot_s1" / "PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md"
SYM, N_SMA, FEE, CAPITAL, D0 = "BTCUSDT", 200, 0.00085, 1000.0, date(2026, 10, 25)   # fee amendment 2d9d1485: was 0.001
assert FEE == json.loads((R_ / "deploy" / "fees.json").read_text())["rules"]["paper_spot_per_side"], "fee differs from deploy/fees.json"
URL = f"https://api.binance.com/api/v3/klines?symbol={SYM}&interval=1d&limit=1000"


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def fetch():
    for k in range(5):
        try:
            return urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "paper-spot-s1"}), timeout=30).read()
        except Exception:                                    # noqa: BLE001 - network retry
            time.sleep(3 * (k + 1))
    raise RuntimeError("klines fetch failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/paper_spot_s1")
    ap.add_argument("--now", default=None)
    a = ap.parse_args()
    assert sha_b(PROTO.read_bytes()) == (PROTO.parent / "PAPER_SPOT_S1_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"
    root = R_ / a.root
    (root / "klines").mkdir(parents=True, exist_ok=True)
    now = datetime.fromisoformat(a.now).replace(tzinfo=timezone.utc) if a.now else datetime.now(timezone.utc)
    yesterday = now.date() - timedelta(days=1)
    lf, sf = root / "ledger.jsonl", root / "state.json"
    L = [json.loads(l) for l in lf.read_text().splitlines() if l.strip()] if lf.exists() else []
    last = L[-1] if L else None                            # the ledger is the source of truth; state.json only mirrors it (CODE_NOTES 1)
    st = dict(cash=last["cash"], qty=last["qty"], bench_units=last["bench_units"], last_D=last["D"]) if last else \
        dict(cash=CAPITAL, qty=0.0, bench_units=None, last_D=None)
    nxt = D0 if st["last_D"] is None else date.fromisoformat(st["last_D"]) + timedelta(days=1)
    if nxt > yesterday:
        print(f"paper spot S1 {now:%Y-%m-%d %H:%M}: nothing to do (next decision day {nxt})")
        return
    raw = fetch()
    kf = root / "klines" / f"{now:%Y%m%dT%H%M%S}.json"
    kf.write_bytes(raw)
    K = json.loads(raw)
    day = {datetime.fromtimestamp(k[0] / 1000, timezone.utc).date(): (float(k[1]), float(k[4]), int(k[6])) for k in K}
    now_ms = int(now.timestamp() * 1000)
    prev = L[-1]["line_sha256"] if L else "GENESIS"
    code = sha_b(Path(__file__).read_bytes())
    D = nxt
    while D <= yesterday:
        assert D in day and day[D][2] < now_ms, f"day {D} not closed in the response"
        assert D + timedelta(days=1) in day, f"no open for {D + timedelta(days=1)}"
        win = [D - timedelta(days=i) for i in range(N_SMA)]
        assert all(x in day for x in win), f"missing daily bars in the 200 days to {D}"
        close = day[D][1]
        sma = sum(day[x][1] for x in win) / N_SMA
        sig = close > sma
        px = day[D + timedelta(days=1)][0]
        action = "none"
        if sig and st["qty"] == 0:
            st["qty"] = st["cash"] * (1 - FEE) / px; st["cash"] = 0.0; action = "buy"
        elif not sig and st["qty"] > 0:
            st["cash"] = st["qty"] * px * (1 - FEE); st["qty"] = 0.0; action = "sell"
        if st["bench_units"] is None:
            st["bench_units"] = CAPITAL * (1 - FEE) / px
        rec = dict(D=str(D), fill_day=str(D + timedelta(days=1)), close_D=close, sma200=sma, signal=sig, action=action, px=px,
                   qty=st["qty"], cash=st["cash"], equity=st["cash"] + st["qty"] * px, bench_units=st["bench_units"], bench_equity=st["bench_units"] * px,
                   klines_file=kf.name, klines_sha256=sha_b(raw), code_sha256=code, protocol_sha256=sha_b(PROTO.read_bytes()),
                   run_utc=now.strftime("%Y-%m-%d %H:%M:%S"), prev_sha256=prev)
        rec["line_sha256"] = sha_b(json.dumps(rec, sort_keys=True).encode())
        with open(lf, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        prev = rec["line_sha256"]
        st["last_D"] = str(D)
        tmp = sf.with_suffix(".tmp"); tmp.write_text(json.dumps(st)); tmp.replace(sf)
        print(f"paper spot S1 D {D}: close {close:.2f} sma200 {sma:.2f} signal {sig} action {action} @ {px:.2f} equity {rec['equity']:.2f} "
              f"(BTC hold {rec['bench_equity']:.2f})")
        D += timedelta(days=1)


if __name__ == "__main__":
    main()
