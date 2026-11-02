"""Independent verifier for the R2 forward recorder (protocol logs/forward_recorder_r2/FR_PROTOCOL_PREREGISTERED.md).

Own implementation; it re-derives everything from the raw files (does not import the recorder).
Usage: python verify_forward_recorder_r2.py <root> [--replay N]
V1 ledger chain + line hashes + protocol SHA == lock     V2 every manifest file exists, SHA matches, manifest SHA == ledger
V3 replay: N random stored klines / funding rows re-fetched from the public API, must be equal (100 %)
V4 continuity of every K kline series from 2026-10-17 00:00 UTC; S missing 5m stamps counted (reported, not a failure)
V5 no look-ahead: kline close < run server time; S ts + 5 min <= server time; L snapshot time <= file write time
V6 no duplicate timestamps in any series across runs     V7 state.json == state recomputed from the raw files
"""
import gzip
import hashlib
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
LOCK = PROJ / "logs" / "forward_recorder_r2" / "FR_PROTOCOL_SHA256.txt"
IV = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
BOOT = int(datetime(2026, 10, 17, tzinfo=timezone.utc).timestamp() * 1000)
K_KL = {"spot_klines": ("https://api.binance.com", "/api/v3/klines"), "perp_klines": ("https://fapi.binance.com", "/fapi/v1/klines"),
        "mark_klines": ("https://fapi.binance.com", "/fapi/v1/markPriceKlines")}
S_NAMES = ["oi_hist", "top_acct_ratio", "top_pos_ratio", "global_ratio", "taker_ratio", "basis"]
results = []


def ok(tag, cond, msg):
    results.append((tag, bool(cond), msg))
    print(f"[{tag} {'PASS' if cond else 'FAIL'}] {msg}")


def h(b):
    return hashlib.sha256(b).hexdigest()


def fetch(u):
    """public GET with 3 retries (2 s, 5 s, 10 s); None if the network keeps failing (then the check FAILs, it never passes)."""
    for w in (0, 2, 5, 10):
        time.sleep(w)
        try:
            return json.loads(urllib.request.urlopen(u, timeout=60).read())
        except Exception:
            continue
    return None


def parse_name(fn):
    """file name -> (group, series key pieces) without using the recorder's code."""
    base = fn[:-len(".json.gz")]
    g, rest = base.split("_", 1)
    if g == "K":
        if rest.startswith("funding_"):
            sym = rest[len("funding_"):].rsplit("_p", 1)[0]
            return "KF", ("funding", sym, None)
        for nm in K_KL:
            if rest.startswith(nm + "_"):
                sym, ivp = rest[len(nm) + 1:].split("_", 1)
                return "KK", (nm, sym, ivp.rsplit("_p", 1)[0])
    if g == "S":
        for nm in sorted(S_NAMES, key=len, reverse=True):
            if rest.startswith(nm + "_"):
                return "S", (nm, rest[len(nm) + 1:].rsplit("_p", 1)[0], "5m")
    return "L", (rest, None, None)


def main(root, n_replay):
    root = Path(root)
    lock_sha = LOCK.read_text().split()[0]
    led = (root / "ledger.csv").read_text(encoding="utf-8").splitlines()
    head, rows = led[0].split(","), [l.split(",") for l in led[1:] if l.strip()]
    prev, chain_ok, proto_ok = "GENESIS", True, True
    for r in rows:
        d = dict(zip(head, r))
        chain_ok &= d["prev_sha256"] == prev and h(",".join(r[:-1]).encode()) == d["line_sha256"] and len(r) == len(head)
        proto_ok &= d["protocol_sha256"] == lock_sha
        prev = d["line_sha256"]
    ok("V1", chain_ok and proto_ok and rows, f"{len(rows)} ledger line(s): chain + line hashes intact={chain_ok}, protocol == lock={proto_ok}")

    series, v2, v5, notes5, lsnap = {}, True, True, [], 0
    folders = {p.name for p in (root / "raw").iterdir()}
    chained = [dict(zip(head, r))["run_id"] for r in rows]
    orphans = sorted(folders - set(chained))
    ok("V2a", not orphans and all(c in folders for c in chained),
       f"run folders == ledger run_ids ({len(chained)}); orphan folders (crashed run, quarantined at the next run) {orphans}")
    runs = [root / "raw" / c for c in chained if c in folders]
    for i, (rd, r) in enumerate(zip(runs, rows)):
        d = dict(zip(head, r))
        mp = rd / "manifest.json"
        v2 &= rd.name == d["run_id"] and h(mp.read_bytes()) == d["manifest_sha256"]
        sa = rd / "state_after.json"              # written from code change 3 on; older runs: state.json was hashed
        if sa.exists():
            v2 &= h(sa.read_bytes()) == d["state_sha256"]
        man = json.loads(mp.read_text())
        srv = man["server_ms"]
        for e in man["files"]:
            p = rd / e["file"]
            v2 &= p.exists() and h(p.read_bytes()) == e["sha256"]
            raw = gzip.decompress(p.read_bytes())
            v2 &= h(raw) == e["raw_sha256"]
            wt = int(datetime.fromisoformat(e["written_utc"]).timestamp() * 1000)
            g, (nm, sym, iv) = parse_name(e["file"])
            j = json.loads(raw)
            prm = e["params"]
            if g == "KK":
                kept = [x for x in j if x[0] >= prm["startTime"] and x[6] < srv]
                for x in kept:
                    if x[6] >= srv:
                        v5 = False
                series.setdefault((nm, sym, iv), []).extend((x[0], i, e["file"]) for x in kept)
            elif g == "KF":
                kept = [x for x in j if prm["startTime"] <= x["fundingTime"] <= srv]
                series.setdefault(("funding", sym, None), []).extend((x["fundingTime"], i, e["file"]) for x in kept)
            elif g == "S":
                kept = sorted({x["timestamp"] for x in j if prm["startTime"] <= x["timestamp"] and x["timestamp"] + 300_000 <= srv})
                series.setdefault((nm, sym, "5m"), []).extend((t, i, e["file"]) for t in kept)
            else:
                lsnap += 1
                tm = j.get("time") if isinstance(j, dict) else None
                if tm is not None and tm > wt:
                    v5 = False; notes5.append(e["file"])
            if g != "L" and len(kept) != e["n_kept"]:
                v2 = False
    ok("V2", v2, f"{len(runs)} run folder(s): every file exists, file / raw SHA256 match, n_kept re-derived, manifest SHA == ledger")
    ok("V5", v5, f"no look-ahead: all kept klines closed before the run's server time; {lsnap} live snapshots time <= write time {notes5[:3]}")

    v4, s_missing, v6 = True, {}, True
    for (nm, sym, iv), lst in series.items():
        ts = [t for t, _, _ in lst]
        if len(ts) != len(set(ts)):
            v6 = False
        ts = sorted(set(ts))
        if nm in K_KL and ts:
            step = IV[iv]
            if ts[0] != BOOT or any(b - a != step for a, b in zip(ts, ts[1:])):
                v4 = False
        if nm in S_NAMES and ts:
            s_missing[(nm, sym)] = sum((b - a) // 300_000 - 1 for a, b in zip(ts, ts[1:]))
    nk = sum(1 for k in series if k[0] in K_KL)
    tot_miss = sum(s_missing.values())
    ok("V4", v4, f"{nk} kline series continuous from 2026-10-17 00:00 UTC; S series: {len(s_missing)}, missing 5m stamps total {tot_miss} "
                 f"(max {max(s_missing.values()) if s_missing else 0}; Binance omits periods without trades)")
    ok("V6", v6, f"no duplicate timestamp in {len(series)} series across runs")

    st = json.loads((root / "state.json").read_text())
    re = {}
    for (nm, sym, iv), lst in series.items():
        if not lst:
            continue
        key = f"funding|{sym}" if nm == "funding" else f"{nm}|{sym}|{iv}"
        re[key] = max(t for t, _, _ in lst)
    ok("V7", st == re, f"state.json ({len(st)} keys) == state recomputed from raw files ({len(re)} keys)"
                        + ("" if st == re else f" diff {[k for k in set(st) | set(re) if st.get(k) != re.get(k)][:5]}"))

    if n_replay:
        rng = random.Random(int(rows[-1][0][:8]))
        cand = [(k, t) for k, lst in series.items() if k[0] in K_KL or k[0] == "funding" for t, _, _ in lst]
        stored = {}
        for rd in runs:
            man = json.loads((rd / "manifest.json").read_text())
            for e in man["files"]:
                g, key = parse_name(e["file"])
                if g in ("KK", "KF"):
                    j = json.loads(gzip.decompress((rd / e["file"]).read_bytes()))
                    for x in j:
                        stored[(key, x[0] if g == "KK" else x["fundingTime"])] = x
        pick = rng.sample(cand, min(n_replay, len(cand)))
        bad = []
        for (nm, sym, iv), t in pick:
            if nm == "funding":
                u = "https://fapi.binance.com/fapi/v1/fundingRate?" + urllib.parse.urlencode(dict(symbol=sym, startTime=t, limit=1))
            else:
                b, p = K_KL[nm]
                u = b + p + "?" + urllib.parse.urlencode(dict(symbol=sym, interval=iv, startTime=t, limit=1))
            live = fetch(u)
            time.sleep(0.15)
            if not live or live[0] != stored[((nm, sym, iv), t)]:
                bad.append((nm, sym, iv, t))
        ok("V3", not bad, f"replay: {len(pick)} random stored rows re-fetched from the public API, equal {len(pick) - len(bad)}/{len(pick)} {bad[:3]}")
        # V8 (added 2026-10-19 after T1, see CODE_CHANGES_AFTER_LOCK): a missing 5m S stamp must be truly absent at Binance
        paths = {"oi_hist": "openInterestHist", "top_acct_ratio": "topLongShortAccountRatio", "top_pos_ratio": "topLongShortPositionRatio",
                 "global_ratio": "globalLongShortAccountRatio", "taker_ratio": "takerlongshortRatio", "basis": "basis"}
        miss = []
        for (nm, sym, iv), lst in series.items():
            if nm in S_NAMES:
                ts = sorted({t for t, _, _ in lst})
                miss += [(nm, sym, t) for a, b in zip(ts, ts[1:]) for t in range(a + 300_000, b, 300_000)]
        now_ms = int(time.time() * 1000)
        miss = [m for m in miss if m[2] > now_ms - 29 * 86_400_000]
        pick = rng.sample(miss, min(60, len(miss))) if miss else []
        lost = []
        for nm, sym, t in pick:
            prm = dict(period="5m", limit=5, startTime=t - 300_000, endTime=t + 300_000)
            prm.update(dict(pair=sym, contractType="PERPETUAL") if nm == "basis" else dict(symbol=sym))
            live = fetch("https://fapi.binance.com/futures/data/" + paths[nm] + "?" + urllib.parse.urlencode(prm))
            time.sleep(0.35)
            if live is None or any(x["timestamp"] == t for x in live):
                lost.append((nm, sym, t))
        ok("V8", not lost, f"missing 5m S stamps: {len(miss)} inside the 30-day window, {len(pick)} re-queried, "
                           f"present at Binance (= lost by the recorder) {len(lost)} {lost[:3]}")
    n_fail = sum(not c for _, c, _ in results)
    print(f"TOTAL {len(results)} checks, FAIL {n_fail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--replay") + 1]) if "--replay" in sys.argv else 0
    sys.exit(main(sys.argv[1], n))
