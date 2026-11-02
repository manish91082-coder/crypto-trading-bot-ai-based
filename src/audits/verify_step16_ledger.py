"""
Verifier for the Step 16 forward ledger (logs/strategy_1d_step16_forward), added 2026-10-16 by the E2E test (no Step 16
verifier existed). Read-only.
L1 hash chain: every line_sha256 re-computed (csv strings mapped back to the json types used when hashing), prev links.
L2 every non-test line: prediction file, B1 / R5 model files and the protocol equal their recorded SHA256.
L3 link to 16B: every 16B forward line's step16_pred_sha256 equals the Step 16 prediction file of that as-of day.
L4 prediction file sanity: one row per symbol, date == as-of, p1 and p_r5 in [0, 1], n_coins == rows.
Limitation: the predictions are not re-computed here (that path is covered by the 16B verifier V2 and the replay files).
"""
import sys
import json
import hashlib
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution"):
    sys.path.insert(0, str(p))
import forward_dryrun_1d as FD
import forward_multi_16b as FB


def typed(v):
    if v in ("True", "False"):
        return v == "True"
    if v.lstrip("-").isdigit():
        return int(v)
    return v


def main():
    L = FD.read_ledger(FD.LEDGER)
    prev = "GENESIS"
    for r in L.to_dict("records"):
        line = {k: typed(v) for k, v in r.items() if k != "line_sha256" and not (k == "written_utc" and (v is None or v != v))}
        assert line["prev_sha256"] == prev, ("chain", r["asof"])
        assert FD.sha_bytes(json.dumps(line, sort_keys=True).encode()) == r["line_sha256"], ("line hash", r["asof"])
        prev = r["line_sha256"]
    print(f"[L1 PASS] {len(L)} Step 16 ledger lines: hash chain intact")
    for r in L.itertuples():
        f = FD.PRED / f"pred_{r.asof}.csv"
        assert FD.sha_file(f) == r.pred_sha256, (r.asof, "pred")
        assert FD.sha_file(FD.MODELS / r.model_file) == r.model_sha256 and FD.sha_file(FD.MODELS / r.model_r5_file) == r.model_r5_sha256, r.asof
        assert FD.sha_file(FD.LOG / "STEP16_PROTOCOL_PREREGISTERED.md") == r.protocol_sha256, r.asof
        p = pd.read_csv(f)
        assert len(p) == int(r.n_coins) and p.symbol.is_unique and (p.date == r.asof).all(), r.asof
        assert p.p1.between(0, 1).all() and p.p_r5.between(0, 1).all(), r.asof
    print(f"[L2+L4 PASS] prediction / model / protocol files match; one row per coin, date == as-of, probabilities in [0, 1]")
    n = 0
    if FB.LEDGER.exists():
        for r in pd.read_csv(FB.LEDGER).itertuples():
            if str(r.test) == "True":
                continue
            assert FD.sha_file(FD.PRED / f"pred_{r.asof}.csv") == r.step16_pred_sha256, (r.asof, "16B link")
            n += 1
    print(f"[L3 PASS] {n} 16B forward line(s) point to the exact Step 16 prediction file of their day")


if __name__ == "__main__":
    main()
