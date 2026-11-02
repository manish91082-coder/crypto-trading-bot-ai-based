"""Independent verifier of PAPER-SPOT-S1 (logs/paper_spot_s1/PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md). Own code, plain loops.
Usage: python verify_paper_spot_s1.py [root=data/paper_spot_s1] [--fresh]   (--fresh: S5 compares with a new public fetch; VM only)
S1 chain / protocol / code SHAs listed  S2 each record from its saved klines file  S3 cash-qty-equity-benchmark replay from 1,000
S4 no decision day missing from 2026-10-25  S5 last 5 records vs a fresh fetch"""
import hashlib
import json
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
root = R_ / (args[0] if args else "data/paper_spot_s1")
LOGD = R_ / "logs" / "paper_spot_s1"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def h(b):
    return hashlib.sha256(b).hexdigest()


L = [json.loads(l) for l in (root / "ledger.jsonl").read_text().splitlines() if l.strip()]
prev, chain = "GENESIS", True
for r in L:
    body = {k: v for k, v in r.items() if k != "line_sha256"}
    chain &= r["prev_sha256"] == prev and h(json.dumps(body, sort_keys=True).encode()) == r["line_sha256"]
    prev = r["line_sha256"]
proto = h((LOGD / "PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md").read_bytes())
notes = (LOGD / "CODE_CHANGES_AFTER_LOCK.md").read_text(encoding="utf-8") if (LOGD / "CODE_CHANGES_AFTER_LOCK.md").exists() else ""
unl = sorted({r["code_sha256"][:12] for r in L if r["code_sha256"][:12] not in notes})
ok("S1", chain and all(r["protocol_sha256"] == proto for r in L) and not unl,
   f"{len(L)} records: chain {chain}, protocol {proto[:12]} constant, code SHAs not listed in CODE_CHANGES {unl}")
bad2 = []
for r in L:
    raw = (root / "klines" / r["klines_file"]).read_bytes()
    if h(raw) != r["klines_sha256"]:
        bad2.append((r["D"], "klines sha")); continue
    bars = {}
    for k in json.loads(raw):
        bars[datetime.fromtimestamp(k[0] / 1000, timezone.utc).date()] = (float(k[1]), float(k[4]))
    D = date.fromisoformat(r["D"])
    cl = [bars[D - timedelta(days=i)][1] for i in range(200)]
    sma = sum(cl) / 200.0
    sig = bars[D][1] > sma
    if bars[D][1] != r["close_D"] or abs(sma - r["sma200"]) > 1e-9 * sma or sig != r["signal"] or bars[D + timedelta(days=1)][0] != r["px"]:
        bad2.append((r["D"], bars[D][1], r["close_D"], sma, r["sma200"], sig, r["signal"]))
ok("S2", not bad2, f"{len(L)} records recomputed from their saved klines (close, SMA200, signal, fill open): mismatches {bad2[:3]}")
FEE = json.loads((R_ / "deploy" / "fees.json").read_text())["rules"]["paper_spot_per_side"]
cash, qty, bu, bad3 = 1000.0, 0.0, None, []
for r in L:
    px, act = r["px"], "none"
    if r["signal"] and qty == 0:
        qty = cash * (1 - FEE) / px; cash = 0.0; act = "buy"
    elif (not r["signal"]) and qty > 0:
        cash = qty * px * (1 - FEE); qty = 0.0; act = "sell"
    if bu is None:
        bu = 1000.0 * (1 - FEE) / px
    eq = cash + qty * px
    if act != r["action"] or abs(eq - r["equity"]) > 1e-9 * max(1, eq) or abs(bu * px - r["bench_equity"]) > 1e-9 * bu * px or abs(qty - r["qty"]) > 1e-15 * max(1, qty):
        bad3.append((r["D"], act, r["action"], eq, r["equity"]))
ok("S3", not bad3, f"replay from 1,000 USDT (fee {FEE:.5f} from deploy/fees.json): actions, equity, benchmark equal: mismatches {bad3[:3]}; last equity {L[-1]['equity'] if L else None}")
days = [date.fromisoformat(r["D"]) for r in L]
exp = [date(2026, 10, 25) + timedelta(days=i) for i in range(len(days))]
ok("S4", days == exp, f"decision days consecutive from 2026-10-25: {days[0] if days else None} .. {days[-1] if days else None} ({len(days)})")
if "--fresh" in sys.argv and L:
    k = json.loads(urllib.request.urlopen(urllib.request.Request("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=60",
                                                                 headers={"User-Agent": "verify-paper-spot-s1"}), timeout=30).read())
    fb = {datetime.fromtimestamp(x[0] / 1000, timezone.utc).date(): (float(x[1]), float(x[4])) for x in k}
    bad5 = [(r["D"]) for r in L[-5:] if fb[date.fromisoformat(r["D"])][1] != r["close_D"] or fb[date.fromisoformat(r["fill_day"])][0] != r["px"]]
    ok("S5", not bad5, f"last {len(L[-5:])} records: close_D and fill open == a fresh public fetch: mismatches {bad5}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
