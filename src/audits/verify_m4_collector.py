"""
Verifier for the M4 collector (logs/collector_m4_options).
V1 protocol hash; ledger hash chain; every stored file's SHA256 equals the ledger.
V2 the latest day's summary re-derived from the raw files (DVOL close, option counts, quarterly basis sign/size sanity).
V3 (revised 2026-10-16) closed DVOL hours re-fetched from Deribit history (equal); each futures markPrice inside the Binance
   1m mark-price kline of its minute; options mark IV is NOT re-verifiable (no history; moves within minutes) -> V1/V2 only.
"""
import sys
import gzip
import json
import time
import hashlib
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC / "execution"))
import m4_options_collector as M


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    assert sha(M.PROTO.read_bytes()) == (M.LOG / "M4_PROTOCOL_SHA256.txt").read_text().split()[0]
    L = pd.read_csv(M.LEDGER)
    prev = "GENESIS"
    for r in L.to_dict("records"):
        line = {k: (int(v) if isinstance(v, np.integer) else v) for k, v in r.items() if k != "line_sha256"}
        assert r["prev_sha256"] == prev and sha(json.dumps(line, sort_keys=True).encode()) == r["line_sha256"], r["day"]
        prev = r["line_sha256"]
        for name, meta in json.loads(r["files"]).items():
            f = M.STORE / r["day"] / f"{name}.json.gz"
            assert sha(f.read_bytes()) == meta["sha256"], (r["day"], name)
    print(f"[V1 PASS] {len(L)} ledger lines; chain intact; every stored file matches its SHA256")
    last = L.iloc[-1]
    files = json.loads(last.files)
    raw = {n: json.loads(gzip.decompress((M.STORE / last.day / f"{n}.json.gz").read_bytes())) for n in files}
    summ = json.loads(last.summary)
    for c in ("BTC", "ETH"):
        if f"deribit_dvol_{c}" in raw:
            assert raw[f"deribit_dvol_{c}"]["result"]["data"][-1][4] == summ[f"dvol_{c}_close"]
        if f"deribit_options_{c}" in raw:
            assert len(raw[f"deribit_options_{c}"]["result"]) == summ[f"deribit_n_options_{c}"]
    assert len(raw["binance_options_mark"]) == summ["binance_n_options"]
    for k, v in summ.items():
        if k.startswith("basis_ann_"):
            assert -1.0 < v < 1.0, (k, v)                    # an annualised basis outside +-100 % would signal a parsing error
    print(f"[V2 PASS] {last.day}: DVOL, option counts and basis sanity re-derived from the raw files: {summ}")
    # V3 (revised 2026-10-16, E2E finding): checks that stay valid when the verifier runs hours after the collection
    run = pd.Timestamp(last.run_utc)
    n = 0
    for c in ("BTC", "ETH"):                                  # (a) DVOL history is immutable: the same hours must be equal
        rows = raw[f"deribit_dvol_{c}"]["result"]["data"]
        t0, t1 = rows[0][0], rows[-2][0]                      # the last (still open) hour may have moved; compare closed hours
        url = (f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={c}&start_timestamp={t0}"
               f"&end_timestamp={t1}&resolution=3600")
        live = {r[0]: r for r in json.loads(urllib.request.urlopen(url, timeout=30).read())["result"]["data"]}
        for r in rows[:-1]:
            if r[0] in live:
                assert [float(x) for x in live[r[0]][1:5]] == [float(x) for x in r[1:5]], (c, r[0], live[r[0]], r)
                n += 1
    m = 0
    for k, v in raw.items():                                  # (b) futures mark price inside the mark-price 1m kline of that minute
        if k.startswith("binance_premium_"):
            t = int(v["time"]) // 60000 * 60000
            url = f"https://fapi.binance.com/fapi/v1/markPriceKlines?symbol={v['symbol']}&interval=1m&startTime={t - 60000}&limit=3"
            wait = (t + 121_000) / 1000 - pd.Timestamp.now("UTC").timestamp()
            if wait > 0:                                      # the minute after the snapshot must be closed too
                time.sleep(wait)
            kl = json.loads(urllib.request.urlopen(url, timeout=30).read())
            assert kl, (v["symbol"], "no mark-price klines around the snapshot minute")
            lo, hi = min(float(k[3]) for k in kl), max(float(k[2]) for k in kl)      # +-1 minute (CODE_CHANGES 4)
            assert lo - 1e-9 <= float(v["markPrice"]) <= hi + 1e-9, (v["symbol"], v["markPrice"], [hi, lo])
            m += 1
    msg = f"[V3 PASS] {n} closed DVOL hours re-fetched and equal; {m} futures mark prices inside the 1m mark-price klines of minute -1..+1"
    # (c) removed 2026-10-16: Binance options mark IV has no history endpoint and moves by > 5 vol points within minutes
    #     on short-dated contracts (seen live: SOL-261030-122-C 0.625 -> 0.694); stored option files are protected by V1
    #     (SHA256) and V2 (counts) only. This limitation is stated in CODE_CHANGES_AFTER_LOCK.md section 3.
    print(msg)

if __name__ == "__main__":
    main()
