"""Offline test of the EMO meter (protocol §3): fake HTTP source with known numbers. Run: python src/audits/test_emotion_meter.py"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R_ / "src" / "eco"))
import eco_core as C
import emotion_meter as M

res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


NOW = pd.Timestamp("2026-10-22 12:20")
CUT = int(NOW.floor("h").value // 10**6)
H = 3_600_000


class Fake:
    """50 hourly rows ending with the still-open hour (timestamp == CUT), which the meter must ignore."""

    def __init__(self, k):
        self.k, self.errors = k, []                      # k: per-symbol scale of the series

    def get(self, path, **p):
        s = p.get("symbol")
        if path == "/fapi/v1/premiumIndex":
            return [dict(symbol=x, lastFundingRate=str(f)) for x, f in (("BTCUSDT", 0.0001), ("ETHUSDT", 0.0003), ("AAAUSDT", -0.0002), ("BADUSDT", 0.0))]
        if s == "BADUSDT":
            return None
        k = self.k[s]
        ts = [CUT - (49 - i) * H for i in range(50)]      # the last one == CUT (open hour)
        if path.endswith("openInterestHist"):
            return [dict(timestamp=t, sumOpenInterestValue=str(1000 * k * (1 + 0.01 * i) if t < CUT else 9e9)) for i, t in enumerate(ts)]
        if path.endswith("topLongShortPositionRatio"):
            return [dict(timestamp=t, longShortRatio=str(1.5 * k if t < CUT else 99)) for t in ts]
        if path.endswith("globalLongShortAccountRatio"):
            return [dict(timestamp=t, longShortRatio=str(2.0 * k if t < CUT else 99)) for t in ts]
        if path.endswith("takerlongshortRatio"):
            return [dict(timestamp=t, buySellRatio=str((1.1 if i % 2 else 0.9) * k if t < CUT else 99)) for i, t in enumerate(ts)]
        if path == "/fapi/v1/klines":
            out = []
            for i, t in enumerate(ts):
                o, c = 100 + i, 101 + i                       # body 1, range 4 -> wick share 0.75
                qv = 10.0 if i < 26 else 20.0                 # closed bars 1..48: bars 26..48 = last 23 + one at 25
                out.append([t, str(o), str(c + 1.5), str(o - 1.5), str(c), "0", t + H - 1, str(qv if t < CUT else 1e9)])
            return out
        raise AssertionError(path)


d = Path(tempfile.mkdtemp())
try:
    eco = d / "eco_ledger.jsonl"
    C.append_ledger(eco, dict(T="x", ok=True, held_net={"AAAUSDT": 1.0, "BADUSDT": 2.0}, targets_net={}))
    src = Fake({"BTCUSDT": 1.0, "ETHUSDT": 1.2, "AAAUSDT": 0.8})
    rec = M.run(src, eco, NOW)
    f = rec["features"]["BTCUSDT"]
    # hand calculation, closed rows only (timestamps < CUT): OI index 1..48 (the row at index 49 is the open hour)
    oi_last, oi_24 = 1000 * (1 + 0.01 * 48), 1000 * (1 + 0.01 * 24)
    tk = np.mean([np.log(1.1 if i % 2 else 0.9) for i in range(25, 49)])
    ok("E1", abs(f["oi_chg_24h"] - (oi_last / oi_24 - 1)) < 1e-12 and abs(f["retail_acct_ls"] - np.log(2.0)) < 1e-12
       and abs(f["top_pos_ls"] - np.log(1.5)) < 1e-12 and abs(f["smart_minus_retail"] - (np.log(1.5) - np.log(2.0))) < 1e-12
       and abs(f["taker_24h"] - tk) < 1e-12 and abs(f["funding"] - 0.0001) < 1e-15 and abs(f["wick_24h"] - 0.75) < 1e-12,
       f"features == hand calculation {({k: round(v, 6) for k, v in f.items()})}")
    qv = [10.0 if i < 26 else 20.0 for i in range(49)]
    vs = sum(qv[25:49]) / sum(qv[1:25]) - 1
    ok("E2", abs(f["vol_surprise"] - vs) < 1e-12 and abs(f["ret_24h"] - ((101 + 48) / (101 + 24) - 1)) < 1e-12
       and rec["last_ts"]["BTCUSDT"]["oi"] == CUT - H and rec["last_ts"]["BTCUSDT"]["kline"] == CUT - H,
       f"open hour excluded (last used row {pd.Timestamp(rec['last_ts']['BTCUSDT']['oi'], unit='ms')}); vol surprise {f['vol_surprise']:.4f}, ret {f['ret_24h']:.5f}")
    # ranks: oi_chg equal for all (ties -> 2/3 each); retail: AAA 0.8 < BTC 1.0 < ETH 1.2; taker log scales; funding AAA < BTC < ETH
    exp = {}
    for s, k in (("AAAUSDT", 0.8), ("BTCUSDT", 1.0), ("ETHUSDT", 1.2)):
        r = {"AAAUSDT": 1 / 3, "BTCUSDT": 2 / 3, "ETHUSDT": 1.0}[s]
        exp[s] = np.mean([2 / 3, r, r, r])
    ok("E3", set(rec["crowding"]) == set(exp) and all(abs(rec["crowding"][s] - exp[s]) < 1e-12 for s in exp)
       and rec["most_crowded_long"][0] == "ETHUSDT", f"crowding {rec['crowding']} == expected {exp}")
    ok("E4", rec["n_symbols"] == 4 and rec["n_ok"] == 3 and any(e.startswith("BADUSDT") for e in rec["errors"]) and "BADUSDT" not in rec["crowding"],
       f"BADUSDT failed -> listed in errors, left out of the ranks: {rec['errors']}")
    # verifier: a 3-hour ledger passes; a tampered score fails M3
    led = d / "emo"
    led.mkdir()
    psha = hashlib.sha256(M.PROTO.read_bytes()).hexdigest()
    eco2 = d / "eco2.jsonl"                                # no failing symbol (BADUSDT alone is 25 % > M4's 20 %)
    C.append_ledger(eco2, dict(T="x", ok=True, held_net={"AAAUSDT": 1.0}, targets_net={}))
    for i in range(3):
        r = M.run(src, eco2, NOW + pd.Timedelta(hours=i)); r.update(protocol_sha256=psha)
        C.append_ledger(led / "ledger.jsonl", r)
    g = subprocess.run([sys.executable, str(R_ / "src" / "audits" / "verify_emotion_live.py"), str(led)], capture_output=True, text=True)
    L = [json.loads(l) for l in (led / "ledger.jsonl").read_text().splitlines()]
    L[1]["crowding"]["BTCUSDT"] += 0.01
    body = {k: v for k, v in L[1].items() if k != "line_sha256"}; L[1]["line_sha256"] = C.sha_b(json.dumps(body, sort_keys=True, default=str).encode())
    L[2]["prev_sha256"] = L[1]["line_sha256"]
    body = {k: v for k, v in L[2].items() if k != "line_sha256"}; L[2]["line_sha256"] = C.sha_b(json.dumps(body, sort_keys=True, default=str).encode())
    (led / "ledger.jsonl").write_text("".join(json.dumps(x, sort_keys=True, default=str) + "\n" for x in L))
    b = subprocess.run([sys.executable, str(R_ / "src" / "audits" / "verify_emotion_live.py"), str(led)], capture_output=True, text=True)
    ok("E5", g.returncode == 0 and b.returncode == 1 and "[M3 FAIL]" in b.stdout and "[M1 PASS]" in b.stdout,
       f"verifier: good ledger exit {g.returncode}; re-chained tampered score -> M3 FAIL (chain still PASS) exit {b.returncode} {g.stderr[-200:]}")
finally:
    shutil.rmtree(d)
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
