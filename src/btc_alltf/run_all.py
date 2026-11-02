"""BTC-ALLTF study (2026-10-28): run every market x timeframe job of study.py into one time-stamped RUN folder.
Usage: python src/btc_alltf/run_all.py [--run <existing RUN dir to resume>] [--workers 2]
RUN folder: logs/btc_alltf_2026_10_28/RUN_<UTC start>/ with RUN_INFO.json (sha256 of the protocol, settings, code, inputs) and
<market>/<tf>/ per job. A job with DONE.json is skipped on resume. The big timeframes (1m, 5m) run alone (RAM)."""
import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
STUDY = PROJ / "logs/btc_alltf_2026_10_28"
CODE = ["src/btc_alltf/study.py", "src/btc_alltf/engine.py", "src/btc_alltf/engine.c", "src/btc_alltf/engine.dll",
        "src/btc_alltf/rules.py", "src/btc_alltf/ind.c", "src/btc_alltf/ind.dll", "src/btc_alltf/build_bars.py", "src/btc_alltf/run_all.py"]
LOCKED = ["logs/btc_alltf_2026_10_28/BTC_ALLTF_PROTOCOL_PREREGISTERED.md", "logs/btc_alltf_2026_10_28/STUDY_CONFIG.json"]
INPUTS = ["deploy/fees.json", "data/external/binance_public/clean/funding.parquet", "data/derived/btc_alltf/bars/BARS_MANIFEST.csv"]
SMALL = ["1y", "1mo", "1w", "1d", "8h", "4h", "1h", "30m", "15m"]
BIG = ["5m", "1m"]


def sha(p):
    h = hashlib.sha256()
    with open(PROJ / p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def job(run, m, tf):
    r = subprocess.run([sys.executable, str(PROJ / "src/btc_alltf/study.py"), "--market", m, "--tf", tf, "--run", str(run)],
                       capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    with open(run / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{pd.Timestamp.now('UTC'):%Y-%m-%d %H:%M:%S}] {m} {tf} exit {r.returncode}: {tail}\n")
        if r.returncode:
            f.write(r.stderr[-4000:] + "\n")
    print(f"{m} {tf} exit {r.returncode}: {tail}", flush=True)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    if a.run:
        run = Path(a.run)
    else:
        run = STUDY / f"RUN_{pd.Timestamp.now('UTC'):%Y-%m-%dT%H%MZ}"
        run.mkdir(parents=True)
        lock = (STUDY / "BTC_ALLTF_PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0]
        if lock != sha(LOCKED[0]):
            raise SystemExit("protocol SHA does not match its lock file")
        info = dict(started_utc=pd.Timestamp.now("UTC").isoformat(), protocol_lock=lock,
                    sha256={p: sha(p) for p in LOCKED + CODE + INPUTS})
        (run / "RUN_INFO.json").write_text(json.dumps(info, indent=1))
    jobs = [(m, tf) for tf in SMALL for m in ("spot", "futures")]
    with ThreadPoolExecutor(a.workers) as ex:
        rc = list(ex.map(lambda x: job(run, *x), jobs))
    for tf in BIG:
        for m in ("spot", "futures"):
            rc.append(job(run, m, tf))
    print(f"ALL JOBS FINISHED, non-zero exits {sum(1 for x in rc if x)}")


if __name__ == "__main__":
    main()
