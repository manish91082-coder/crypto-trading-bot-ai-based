"""R2 forward recorder (protocol logs/forward_recorder_r2/FR_PROTOCOL_PREREGISTERED.md, SHA in FR_PROTOCOL_SHA256.txt).

PUBLIC Binance endpoints only: no keys, no orders. Stores byte-exact raw responses + a manifest per run, a state file and a
hash-chained ledger. Usage:
    python forward_recorder_r2.py --root <dir>      (local test: logs/forward_recorder_r2_localtest; cloud: data/forward_r2)
"""
import argparse
import gzip
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT_PROJ = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT_PROJ / "logs" / "forward_recorder_r2" / "FR_PROTOCOL_PREREGISTERED.md"
SPOT, FAPI = "https://api.binance.com", "https://fapi.binance.com"
SYMBOLS = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "DOTUSDT", "ENAUSDT", "ETHUSDT", "FILUSDT", "GTCUSDT", "HYPEUSDT",
           "INJUSDT", "LINKUSDT", "LTCUSDT", "NEARUSDT", "PUMPUSDT", "SANDUSDT", "SOLUSDT", "SUIUSDT", "TIAUSDT", "UNIUSDT",
           "WLDUSDT", "XRPUSDT", "ZECUSDT"]
MS = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
K_SERIES = ([("spot_klines", SPOT, "/api/v3/klines", iv) for iv in ("5m", "15m", "1h", "4h", "1d")]
            + [("perp_klines", FAPI, "/fapi/v1/klines", iv) for iv in ("1h", "4h")]
            + [("mark_klines", FAPI, "/fapi/v1/markPriceKlines", iv) for iv in ("1h", "4h")])
S_SERIES = [("oi_hist", "/futures/data/openInterestHist"), ("top_acct_ratio", "/futures/data/topLongShortAccountRatio"),
            ("top_pos_ratio", "/futures/data/topLongShortPositionRatio"),
            ("global_ratio", "/futures/data/globalLongShortAccountRatio"), ("taker_ratio", "/futures/data/takerlongshortRatio"),
            ("basis", "/futures/data/basis")]
K_BOOT = int(datetime(2026, 10, 17, tzinfo=timezone.utc).timestamp() * 1000)
S_BACK_MS = 29 * 86_400_000
S_FINAL_MS = 300_000            # a 5m statistic is kept only when ts + 5 min <= server time (finality margin)
S_SLEEP = 0.35                  # <= ~857 requests / 5 min on /futures/data (documented limit 1000 / 5 min)
LOCK_STALE_S = 3 * 3600


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha_bytes(Path(p).read_bytes())


def utc_now():
    return datetime.now(timezone.utc)


class Rec:
    def __init__(self, root, run_id):
        self.root = root
        self.dir = root / "raw" / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.files, self.errors, self.n_req, self.gaps = [], [], 0, []

    def get(self, base, path, params):
        url = base + path + "?" + urllib.parse.urlencode(params)
        for i, wait in enumerate((0, 2, 5, 10)):
            if wait:
                time.sleep(wait)
            try:
                self.n_req += 1
                with urllib.request.urlopen(url, timeout=60) as r:
                    return r.read()
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = f"{getattr(e, 'code', '')} {str(e)[:120]}"
                if getattr(e, "code", None) == 400:      # parameter error: retrying cannot help
                    break
        self.errors.append(dict(path=path, params=params, error=last))
        return None

    def save(self, name, raw, params, kept, ts_key):
        p = self.dir / f"{name}.json.gz"
        with gzip.GzipFile(p, "wb", mtime=0) as f:
            f.write(raw)
        e = dict(file=p.name, sha256=sha_file(p), raw_sha256=sha_bytes(raw), params=params, n_raw=None, n_kept=len(kept),
                 first=kept[0][ts_key] if kept else None, last=kept[-1][ts_key] if kept else None,
                 written_utc=utc_now().isoformat())
        try:
            j = json.loads(raw)
            e["n_raw"] = len(j) if isinstance(j, list) else 1
        except ValueError:
            pass
        self.files.append(e)
        return e


def server_times(rec):
    out = {}
    for k, base, path in (("spot", SPOT, "/api/v3/time"), ("fapi", FAPI, "/fapi/v1/time")):
        t0 = time.time()
        b = rec.get(base, path, {})
        t1 = time.time()
        if b:
            st = json.loads(b)["serverTime"]
            out[k] = dict(server_ms=st, skew_ms=round(st - (t0 + t1) / 2 * 1000))
    return out


def record(root, run_id, server_ms, state, rec, notes):
    # ---- K series: closed klines / funding events after the last stored point
    for name, base, path, iv in K_SERIES:
        for s in SYMBOLS:
            key = f"{name}|{s}|{iv}"
            nxt = state.get(key, K_BOOT - MS[iv]) + MS[iv]
            page = 0
            while nxt + MS[iv] - 1 < server_ms:
                prm = dict(symbol=s, interval=iv, startTime=nxt, limit=1000)
                raw = rec.get(base, path, prm)
                if raw is None:
                    break
                rows = json.loads(raw)
                kept = [dict(t=r[0]) for r in rows if r[0] >= nxt and r[6] < server_ms]
                rec.save(f"K_{name}_{s}_{iv}_p{page}", raw, prm, kept, "t")
                if not kept:
                    break
                ts = [nxt] + [k["t"] for k in kept]
                miss = sum((b - a) // MS[iv] - 1 for a, b in zip(ts[1:], ts[2:])) + (kept[0]["t"] - nxt) // MS[iv]
                if miss:
                    rec.gaps.append(f"{key}: {miss} missing bars")
                state[key] = kept[-1]["t"]
                nxt = kept[-1]["t"] + MS[iv]
                page += 1
                if len(rows) < 1000:
                    break
    for s in SYMBOLS:
        key = f"funding|{s}"
        nxt = state.get(key, K_BOOT - 1) + 1
        page = 0
        while True:
            prm = dict(symbol=s, startTime=nxt, limit=1000)
            raw = rec.get(FAPI, "/fapi/v1/fundingRate", prm)
            if raw is None:
                break
            rows = json.loads(raw)
            kept = [dict(t=r["fundingTime"]) for r in rows if nxt <= r["fundingTime"] <= server_ms]
            rec.save(f"K_funding_{s}_p{page}", raw, prm, kept, "t")
            if not kept:
                break
            state[key] = kept[-1]["t"]
            nxt = kept[-1]["t"] + 1
            page += 1
            if len(rows) < 1000:
                break
    # ---- S series: 30-day-limited 5m statistics
    for name, path in S_SERIES:
        for s in SYMBOLS:
            key = f"{name}|{s}|5m"
            # cursor paging (change 1 after lock): the next request starts 1 ms after the last KEPT stamp, so no stamp is
            # skipped whatever the endpoint's window semantics (takerlongshortRatio returns floor(startTime) rows first)
            last = state.get(key)
            nxt = max(last + 1, server_ms - S_BACK_MS) if last is not None else server_ms - S_BACK_MS
            if last is not None and last + 300_000 < server_ms - S_BACK_MS:      # change 3: unrecoverable window
                notes.append(f"LOST {key}: {(server_ms - S_BACK_MS - last) // 300_000 - 1} stamps older than the 29-day window")
            page = 0
            while nxt + S_FINAL_MS <= server_ms:
                end = min(nxt + 500 * 300_000 - 1, server_ms)
                prm = dict(period="5m", limit=500, startTime=nxt, endTime=end)
                prm.update(dict(pair=s, contractType="PERPETUAL") if name == "basis" else dict(symbol=s))
                time.sleep(S_SLEEP)
                raw = rec.get(FAPI, path, prm)
                if raw is None:
                    break
                rows = json.loads(raw)
                kept = sorted({r["timestamp"] for r in rows if nxt <= r["timestamp"] and r["timestamp"] + S_FINAL_MS <= server_ms})
                rec.save(f"S_{name}_{s}_p{page}", raw, prm, [dict(t=t) for t in kept], "t")
                if kept:
                    state[key] = kept[-1]
                    nxt = kept[-1] + 1
                else:
                    nxt = end + 1
                page += 1
    # ---- L snapshots
    for s in SYMBOLS:
        for name, base, path, prm in (("premium", FAPI, "/fapi/v1/premiumIndex", dict(symbol=s)),
                                      ("oi_now", FAPI, "/fapi/v1/openInterest", dict(symbol=s)),
                                      ("perp_depth", FAPI, "/fapi/v1/depth", dict(symbol=s, limit=100)),
                                      ("spot_book", SPOT, "/api/v3/ticker/bookTicker", dict(symbol=s))):
            raw = rec.get(base, path, prm)
            if raw is not None:
                rec.save(f"L_{name}_{s}", raw, prm, [], "t")
    raw = rec.get(FAPI, "/fapi/v1/fundingInfo", {})
    if raw is not None:
        rec.save("L_fundingInfo_ALL", raw, {}, [], "t")
    raw = rec.get(FAPI, "/fapi/v1/exchangeInfo", {})
    if raw is not None:
        ei = json.loads(raw)
        sub = json.dumps(dict(serverTime=ei.get("serverTime"),
                              symbols=[x for x in ei["symbols"] if x["symbol"] in SYMBOLS]), sort_keys=True).encode()
        rec.save("L_exchangeInfo_23", sub, {"filtered_from_sha256": sha_bytes(raw)}, [], "t")
        listed = {x["symbol"]: x["status"] for x in ei["symbols"] if x["symbol"] in SYMBOLS}
        bad = {k: v for k, v in listed.items() if v != "TRADING"} | {k: "MISSING" for k in SYMBOLS if k not in listed}
        if bad:
            notes.append(f"perp status not TRADING: {bad}")


def recover(root, notes):
    """change 3: crash safety. Quarantine run folders without a ledger line; return the state of the last chained run."""
    led, sp = root / "ledger.csv", root / "state.json"
    lines = led.read_text(encoding="utf-8").splitlines() if led.exists() else []
    head = lines[0].split(",") if lines else []
    rows = [dict(zip(head, l.split(","))) for l in lines[1:] if l.strip()]
    chained = {r["run_id"] for r in rows}
    raw = root / "raw"
    for d in sorted(raw.iterdir()) if raw.exists() else []:
        if d.name not in chained:
            q = root / "raw_orphans"
            q.mkdir(exist_ok=True)
            d.rename(q / d.name)
            notes.append(f"orphan run folder {d.name} quarantined to raw_orphans (no ledger line: crashed run)")
    if not rows:
        if sp.exists():
            notes.append("state.json without any ledger line -> ignored")
        return {}
    last = rows[-1]
    if sp.exists() and sha_file(sp) == last["state_sha256"]:
        return json.loads(sp.read_text())
    sa = raw / last["run_id"] / "state_after.json"
    if sa.exists() and sha_file(sa) == last["state_sha256"]:
        notes.append(f"state.json did not match the last ledger line -> restored from {last['run_id']}/state_after.json")
        return json.loads(sa.read_text())
    raise SystemExit("state.json does not match the last ledger line and no valid state_after.json -> stop, manual check")


def main():
    global SYMBOLS, S_BACK_MS
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--test-symbols", default=None, help="TESTS ONLY: comma list replacing the frozen universe")
    ap.add_argument("--test-server-offset-ms", type=int, default=0,
                    help="TESTS ONLY (needs --test-symbols): pretend the run happens this many ms earlier (negative)")
    ap.add_argument("--test-s-back-days", type=float, default=None,
                    help="TESTS ONLY (needs --test-symbols): shorter S bootstrap window than 29 days")
    a = ap.parse_args()
    if (a.test_server_offset_ms or a.test_s_back_days) and not a.test_symbols:
        raise SystemExit("--test-server-offset-ms / --test-s-back-days are allowed only together with --test-symbols")
    if a.test_s_back_days:
        S_BACK_MS = int(a.test_s_back_days * 86_400_000)
    code_sha = sha_file(Path(__file__))
    root = Path(a.root)
    if not root.is_absolute():
        root = ROOT_PROJ / root
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "RUNNING.lock"
    notes = []
    if lock.exists():
        age = time.time() - lock.stat().st_mtime
        if age < LOCK_STALE_S:
            print(f"lock present ({age:.0f}s old) -> another run is active, exit without writing")
            return 0
        notes.append(f"stale lock ({age:.0f}s) removed")
        lock.unlink()
    lock.write_text(f"{os.getpid()} {utc_now().isoformat()}")
    try:
        if a.test_symbols:
            SYMBOLS = a.test_symbols.split(",")
            notes.append(f"TEST symbols override {SYMBOLS}" + (f"; TEST S bootstrap {a.test_s_back_days} d" if a.test_s_back_days else ""))
        start = utc_now()
        run_id = start.strftime("%Y%m%dT%H%M%SZ")
        sp = root / "state.json"
        state = recover(root, notes)
        before = dict(state)
        rec = Rec(root, run_id)
        st = server_times(rec)
        if "fapi" not in st or "spot" not in st:
            raise SystemExit("server time unavailable -> nothing recorded")
        server_ms = min(st["spot"]["server_ms"], st["fapi"]["server_ms"]) + a.test_server_offset_ms
        if a.test_server_offset_ms:
            notes.append(f"TEST server offset {a.test_server_offset_ms} ms")
        record(root, run_id, server_ms, state, rec, notes)
        sa = rec.dir / "state_after.json"
        sa.write_text(json.dumps(state, indent=1, sort_keys=True))
        man = dict(run_id=run_id, server_ms=server_ms, server=st, symbols=SYMBOLS, files=rec.files)
        mp = rec.dir / "manifest.json"
        mp.write_text(json.dumps(man, indent=1, sort_keys=True))
        led = root / "ledger.csv"
        prev = "GENESIS"
        if led.exists():
            last = [l for l in led.read_text().splitlines() if l.strip()][-1]
            prev = last.split(",")[-1]
        new_series = [k for k in state if k not in before]
        line = dict(run_id=run_id, start_utc=start.isoformat(), end_utc=utc_now().isoformat(), server_ms=server_ms,
                    skew_spot_ms=st["spot"]["skew_ms"], skew_fapi_ms=st["fapi"]["skew_ms"], manifest_sha256=sha_file(mp),
                    state_sha256=sha_file(sa), n_files=len(rec.files), n_rows_kept=sum(f["n_kept"] for f in rec.files),
                    n_requests=rec.n_req, n_http_errors=len(rec.errors), n_new_series=len(new_series),
                    n_kline_gaps=len(rec.gaps),
                    protocol_sha256=sha_file(PROTOCOL), code_sha256=code_sha,
                    notes=json.dumps(notes + rec.gaps[:20] + ([f"http_errors: {rec.errors[:5]}"] if rec.errors else []))
                    .replace(",", ";"),
                    prev_sha256=prev)
        body = ",".join(str(v) for v in line.values())
        line["line_sha256"] = sha_bytes(body.encode())
        first = not led.exists() or led.stat().st_size == 0
        with open(led, "a", encoding="utf-8") as f:
            if first:
                f.write(",".join(line.keys()) + "\n")
            f.write(",".join(str(v) for v in line.values()) + "\n")
        tmp = root / "state.json.tmp"                 # replaced only after the ledger line exists (atomic rename)
        tmp.write_text(sa.read_text())
        os.replace(tmp, sp)
        print(f"run {run_id}: {len(rec.files)} files, {line['n_rows_kept']} rows kept, {rec.n_req} requests, "
              f"{len(rec.errors)} http errors, notes {notes}")
    finally:
        lock.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
