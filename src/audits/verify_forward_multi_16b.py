"""
Verifier for Step 16B (logs/forward_multi_16b/STEP16B_PROTOCOL_PREREGISTERED.md).
V1 protocol + code hash as locked.
V2 live code path on the live folders reproduces the research R6_AI / R24_AI scores and the Step 19 universe
   (as-of 2026-09-02 / 09-15 / 09-29; September models trained into a temporary folder).
V3 production October models reproduce R6_FROZEN / R24_FROZEN on 2018-19.
V4 paper engine with the research predictions reproduces the Step 27 MAIN 50 % sleeve finals.
V5 the --test run: files exist, their SHA256 match the test ledger, hash chain intact.
Usage: python verify_forward_multi_16b.py [V2 V3 V4 V5]   (default: all)
"""
import sys
import json
import hashlib
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution"):
    sys.path.insert(0, str(p))
import forward_multi_16b as FM
FM.RUNLOG = FM.LOG / "verify_run_log.txt"     # verifier messages never go into the forward run_log (audit 2026-10-16)
import forward_dryrun_1d as FD
import core_rows_1d as CR
import step13_unseen_coins_1d as S13
import step19_large_caps_1d as S19
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import step24_1h_brain as S24
import step27_combine as S27

TOL = 1e-9


def v1():
    lock = {ln.split()[1]: ln.split()[0] for ln in (FM.LOG / "PROTOCOL_SHA256.txt").read_text().splitlines()
            if ln.strip() and not ln.startswith("locked_utc")}
    lock = [lock["STEP16B_PROTOCOL_PREREGISTERED.md"], lock["src/execution/forward_multi_16b.py"]]
    assert FD.sha_file(FM.PROTO) == lock[0], "protocol changed after lock"
    code = FD.sha_file(FM.__file__)
    if code != lock[1]:
        assert (FM.LOG / "CODE_CHANGES_AFTER_LOCK.md").exists() and code in (FM.LOG / "CODE_CHANGES_AFTER_LOCK.md").read_text(), \
            "code changed after lock without a documented change"
    print(f"[V1 PASS] protocol {lock[0][:12]}, code {code[:12]} ({'as locked' if code == lock[1] else 'documented change'})")


def compare(mine, ref, col, what):
    m = mine.merge(ref[["symbol", "bar", col]], on=["symbol", "bar"], how="outer", indicator=True)
    assert (m._merge == "both").all(), f"{what}: symbol/bar sets differ: {m._merge.value_counts().to_dict()}"
    d = float(np.abs(m.score - m[col]).max())
    assert d < TOL, f"{what}: max diff {d}"
    return len(m), d


def v2():
    r6 = pd.read_csv(S23.OUT / "test_predictions_4h.csv", usecols=["symbol", "bar", "R6_AI"], parse_dates=["bar"])
    r24 = pd.read_csv(S24.OUT / "test_predictions_1h.csv", usecols=["symbol", "bar", "R24_AI"], parse_dates=["bar"])
    u19 = pd.read_csv(S19.OUT / "universe_U.csv", parse_dates=["date"])
    tmp = Path(tempfile.mkdtemp(prefix="v16b_models_"))
    for asof in ("2026-09-02", "2026-09-15", "2026-09-29"):
        a = pd.Timestamp(asof)
        Ute, sc, _, _, _ = FM.score_day(a, FD.LIVE1D, FD.LIVE1H, tmp)
        ref_u = set(u19[u19.date == a - pd.Timedelta(days=1)].symbol)
        assert set(Ute.symbol) == ref_u, f"{asof}: universe differs {set(Ute.symbol) ^ ref_u}"
        n4, d4 = compare(sc["h4_r6"][0][["symbol", "bar", "score"]], r6[r6.bar.dt.normalize() == a], "R6_AI", f"R6 {asof}")
        n1, d1 = compare(sc["h1_r24"][0][["symbol", "bar", "score"]], r24[r24.bar.dt.normalize() == a], "R24_AI", f"R24 {asof}")
        print(f"   {asof}: members {len(Ute)} = Step 19; R6 rows {n4} max diff {d4:.1e}; R24 rows {n1} max diff {d1:.1e}", flush=True)
    print("[V2 PASS] live code path reproduces the research R6 / R24 scores and the Step 19 universe")


def v3():
    asof = pd.Timestamp("2026-10-14")
    month = pd.Timestamp("2026-10-01")
    data_k, last_k, data_n, last_n, _ = CR.load_folder(FD.LIVE1D, FD.LIVE1H, asof)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    _, cand_train = FM.candidates(data_k, data_n)
    U22 = pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date"], parse_dates=["date"])
    for kind, mod, bars, col, f, hrs in (("h4_r6", S23, S23.bars_4h, "R6_FROZEN", "pre2020_predictions_4h.csv", 20),
                                         ("h1_r24", S24, S24.bars_1h, "R24_FROZEN", "pre2020_predictions_1h.csv", 23)):
        m, mp = FM.month_model(kind, month, data, last, cand_train, FD.LIVE1H, FD.MODELS, asof)
        btc = bars(S23.PRE1H / "BTCUSDT_1h_full.csv.gz").close
        R, _, _ = mod.build_rows(dict(pre=U22), S23.PRE1H, btc)
        P = R["pre"]
        P = P[(P.bar >= S23.PRE_START) & (P.bar <= S23.PRE_END + pd.Timedelta(hours=hrs))].reset_index(drop=True)
        P["score"] = m.predict_proba(P[mod.FEATS].values)[:, 1]
        ref = pd.read_csv(mod.OUT / f, usecols=["symbol", "bar", col], parse_dates=["bar"])
        n, d = compare(P[["symbol", "bar", "score"]], ref, col, kind)
        print(f"   {mp.name} ({FD.sha_file(mp)[:12]}): {n} rows of 2018-19, max diff {d:.1e}", flush=True)
    print("[V3 PASS] production October models = research frozen brains")


def v4():
    start, end = S27.PER["MAIN"]
    dk, lk, dn, ln, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", end)
    data, last = {**dk, **dn}, {**lk, **ln}
    d1 = pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"])
    h4 = pd.read_csv(S23.OUT / "test_predictions_4h.csv", usecols=["symbol", "bar", "R6_AI"], parse_dates=["bar"]).rename(columns={"R6_AI": "score"})
    h1 = pd.read_csv(S24.OUT / "test_predictions_1h.csv", usecols=["symbol", "bar", "R24_AI"], parse_dates=["bar"]).rename(columns={"R24_AI": "score"})
    cost_live, FM.COST = FM.COST, 0.0025                       # fee amendment 2: engine identity is tested at the research cost (Step 27 used 0.25 %)
    eq, _ = FM.paper_from_rows(start, end, d1, h4, h1, data, last, S13.UNI / "1h")
    FM.COST = cost_live
    ref = json.loads((S27.OUT / "claims.json").read_text())["sleeve_finals"]["MAIN_f50"]
    for k in ("D1", "H4", "H1"):
        got = float(eq[f"final_{k}"].iloc[-1])
        assert abs(got - ref[k]) < 0.01, f"{k}: {got} vs {ref[k]}"
        print(f"   {k}: {got:,.2f} = Step 27 {ref[k]:,.2f}")
    print(f"   M_AI3 mean of finals {np.mean([ref[k] for k in ('D1', 'H4', 'H1')]):,.2f}")
    print("[V4 PASS] paper engine = Step 27 research sleeves (50 %)")


def v5():
    base = FM.LOG / "test"
    led = pd.read_csv(base / "ledger_test.csv")
    prev = "GENESIS"
    for r in led.to_dict("records"):
        line = {k: v for k, v in r.items() if k != "line_sha256"}
        line = {k: (v.item() if hasattr(v, "item") else v) for k, v in line.items()}
        assert line["prev_sha256"] == prev
        assert FD.sha_bytes(json.dumps(line, sort_keys=True).encode()) == r["line_sha256"], f"line hash {r['asof']}"
        prev = r["line_sha256"]
    r = led.iloc[-1]
    for col, name in (("h4_sha256", "h4_r6"), ("h1_sha256", "h1_r24"), ("d1_sha256", "d1"), ("inputs_sha256", "inputs_1h")):
        assert FD.sha_file(base / "predictions" / f"{name}_{r["asof"]}.csv") == r[col], col
    for col, f in (("model_h4_sha256", r.model_h4), ("model_h1_sha256", r.model_h1)):
        assert FD.sha_file(FD.MODELS / f) == r[col], col
    print(f"[V5 PASS] test run as-of {r["asof"]}: {r.n_members} members, {r.n_h4_rows} R6 rows, {r.n_h1_rows} R24 rows, "
          f"{r.n_d1} D1 rows; file and model hashes match; chain of {len(led)} line(s) intact; notes {r.notes}")


def v6():
    """forward ledger (non-test): hash chain, every file hash, paper_M_AI3 == the last M_AI3 of the paper equity file (E2E 2026-10-16)."""
    if not FM.LEDGER.exists():
        print("[V6 SKIP] no forward ledger yet")
        return
    led = pd.read_csv(FM.LEDGER)
    prev = "GENESIS"
    for r in led.to_dict("records"):
        line = {k: (v.item() if hasattr(v, "item") else v) for k, v in r.items() if k != "line_sha256"}
        assert line["prev_sha256"] == prev, f"chain {r['asof']}"
        assert FD.sha_bytes(json.dumps(line, sort_keys=True).encode()) == r["line_sha256"], f"line hash {r['asof']}"
        prev = r["line_sha256"]
        a = r["asof"]
        for col, name in (("h4_sha256", "h4_r6"), ("h1_sha256", "h1_r24"), ("d1_sha256", "d1"), ("inputs_sha256", "inputs_1h")):
            assert FD.sha_file(FM.PRED / f"{name}_{a}.csv") == r[col], (a, col)
        for col, f in (("model_h4_sha256", r["model_h4"]), ("model_h1_sha256", r["model_h1"])):
            assert FD.sha_file(FD.MODELS / f) == r[col], (a, col)
        eqf = FM.PAPER / f"equity_{a}.csv"
        assert FD.sha_file(eqf) == r["paper_equity_sha256"], (a, "paper equity file")
        e = pd.read_csv(eqf)
        assert abs(round(float(e.M_AI3.iloc[-1]), 2) - float(r["paper_M_AI3"])) < 0.005, (a, e.M_AI3.iloc[-1], r["paper_M_AI3"])
        assert r["protocol_sha256"] == FD.sha_file(FM.PROTO), (a, "protocol")
    print(f"[V6 PASS] forward ledger: {len(led)} line(s), chain intact; prediction / input / model / paper files match; "
          f"paper_M_AI3 equals the paper equity file")


if __name__ == "__main__":
    todo = sys.argv[1:] or ["V1", "V2", "V3", "V4", "V5", "V6"]
    v1()
    for k in todo:
        if k != "V1":
            globals()[k.lower()]()
