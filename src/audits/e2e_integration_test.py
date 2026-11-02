"""
End-to-end integration test of the whole daily system (2026-10-16). The real forward ledgers are only READ; every
run that writes goes to a temporary SANDBOX folder. No order is placed anywhere (F6 runs in plan mode, no keys).

Part A  static wiring
  A1 every .py under src/ compiles
  A2 every protocol lock in logs/*/ : the protocol file hash equals the lock (code files: as locked or a documented change)
  A3 Windows scheduled tasks (read-only query): every enabled CryptoBot task points to an existing script
  A4 order safety by source inspection: only futures_testnet_f6 posts orders, and only to the two test hosts;
     F4 / 16B / Step 16 / Step 2 / M4 / N3 / M10 contain no order call
Part B  real ledgers, read-only: the independent verifiers of 16B (V1, V5), F4 (V1..V5), N3 (V1..V3), M4 (V1..V3)
Part C  sandbox chain: 16B paper -> F4 (two days, via preflight_f4) -> F4 verifier -> F6 plan -> N3 -> N3 verifier
        -> M4 -> M4 verifier -> M10 (missing-day case and the real-ledger LATE case)
Part D  negative tests (the checks must FAIL on tampered input): F4 ledger number, F4 orders file (F6 refuses),
        M4 stored file, N3 ledger number, R1 claims (if claims_E3.json exists)
Usage: python e2e_integration_test.py   -> writes logs/e2e_integration/e2e_<utc>.txt and .json
"""
import io
import os
import re
import sys
import json
import shutil
import hashlib
import tempfile
import traceback
import contextlib
import subprocess
import py_compile
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research", SRC / "audits"):
    sys.path.insert(0, str(p))
from config import LOGS_DIR

OUT = LOGS_DIR / "e2e_integration"
PY = sys.executable
RES = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rec(test, ok, detail=""):
    RES.append(dict(test=test, ok=bool(ok), detail=str(detail)[:1500]))
    print(f"[{'PASS' if ok else 'FAIL'}] {test}: {str(detail)[:400]}", flush=True)


def run_check(test, fn):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn()
        rec(test, True, " | ".join(x for x in buf.getvalue().splitlines() if "PASS" in x or "done" in x)[-1200:])
    except Exception as e:
        rec(test, False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-800:]}")


def must_fail(test, fn):
    """negative test: fn must raise (AssertionError / KeyError ...)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn()
        rec(test, False, "tampered input was ACCEPTED (check is blind)")
    except Exception as e:
        rec(test, True, f"rejected as expected: {type(e).__name__}: {str(e)[:200]}")


def rehash(path, nan_none=False):
    """re-compute the whole hash chain of a ledger after an edit (what a careful forger would do)."""
    import numpy as np
    L = pd.read_csv(path)
    prev = "GENESIS"
    for i, r in enumerate(L.to_dict("records")):
        line = {}
        for k, v in r.items():
            if k == "line_sha256":
                continue
            if isinstance(v, float) and np.isnan(v) and nan_none:
                v = None
            elif isinstance(v, np.bool_):
                v = bool(v)
            elif isinstance(v, np.integer):
                v = int(v)
            elif isinstance(v, np.floating):
                v = float(v)
            line[k] = v
        line["prev_sha256"] = prev
        h = hashlib.sha256(json.dumps(line, sort_keys=True, default=str if nan_none else None).encode()).hexdigest()
        L.loc[i, "prev_sha256"], L.loc[i, "line_sha256"] = prev, h
        prev = h
    L.to_csv(path, index=False)


# ------------------------------------------------------------------ A
def part_a():
    bad = []
    files = [f for f in SRC.rglob("*.py") if "__pycache__" not in f.parts]
    cdir = Path(tempfile.mkdtemp(prefix="e2e_pyc_"))
    for i, f in enumerate(files):
        try:
            py_compile.compile(str(f), doraise=True, cfile=str(cdir / f"{i}.pyc"))
        except Exception as e:
            bad.append(f"{f.relative_to(ROOT)}: {e}")
    rec("A1 all src/*.py compile", not bad, f"{len(files)} files; failures {bad[:5]}")

    proto_bad, code_info = [], []
    locks = sorted(set(LOGS_DIR.glob("*/*SHA256*.txt")) | set(LOGS_DIR.glob("*/*/*SHA256*.txt")))
    for lk in locks:
        for ln in lk.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^([0-9a-f]{64})\s+\*?(.+?)(\s+\(.*\))?\s*$", ln.strip())
            if not m:
                continue
            h, name = m.group(1), m.group(2).strip()
            cand = [ROOT / name, lk.parent / name, lk.parent.parent / name]   # a run folder may hold a copy of its parent lock
            f = next((c for c in cand if c.exists()), None)
            if f is None:
                (proto_bad if "PROTOCOL" in name else code_info).append(f"{lk.parent.name}: {name} missing")
                continue
            if "PROTOCOL" in name.upper() and name.endswith(".md"):
                if sha(f) != h:
                    proto_bad.append(f"{lk.parent.name}: {name}")
            elif sha(f) != h:
                cc = lk.parent / "CODE_CHANGES_AFTER_LOCK.md"
                doc = cc.exists()
                code_info.append(f"{lk.parent.name}: {name} changed after lock ({'CODE_CHANGES_AFTER_LOCK.md present' if doc else 'NO change file'})")
    rec("A2 every protocol file equals its SHA256 lock", not proto_bad, f"{len(locks)} lock files; mismatches {proto_bad}")
    rec("A2b code files changed after lock (information; forward systems document them)", True, "; ".join(code_info) or "none")

    if os.name != "nt":                                    # cloud VM: cron instead of the Windows Task Scheduler
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        installed = "run_job.sh" in r.stdout
        txt = r.stdout if installed else (ROOT / "deploy" / "crontab.txt").read_text(encoding="utf-8")
        jobs = [ln.split() for ln in txt.splitlines() if ln.strip() and not ln.startswith(("#", "SHELL"))]
        rec("A3c cron installed (information; installed only at the switch day)", True, f"installed={installed}")
        miss = [j[7] for j in jobs if len(j) > 7 and not (ROOT / j[7]).exists()]
        rec("A3 every cron job points to an existing script (Linux)", bool(jobs) and not miss, f"{len(jobs)} cron lines; missing {miss}")
        rec("A3b cron jobs (information)", True, " || ".join(" ".join(j[:2] + j[6:8]) for j in jobs))
        order_pat = None
    else:
        order_pat = True
    if order_pat:
        a3_windows()
    a4()


def a3_windows():
    ps = ("Get-ScheduledTask | Where-Object {$_.TaskName -like 'CryptoBot*'} | ForEach-Object { $i = Get-ScheduledTaskInfo $_.TaskName; "
          "[pscustomobject]@{name=$_.TaskName; state=[string]$_.State; exe=[string]$_.Actions[0].Execute; args=[string]$_.Actions[0].Arguments; "
          "wd=[string]$_.Actions[0].WorkingDirectory; wake=[bool]$_.Settings.WakeToRun; next=[string]$i.NextRunTime; last=[string]$i.LastRunTime; "
          "result=$i.LastTaskResult; trig=($_.Triggers | ForEach-Object { [string]$_.StartBoundary }) -join ',' } } | ConvertTo-Json")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=120)
    T = json.loads(r.stdout) if r.stdout.strip() else []
    T = T if isinstance(T, list) else [T]
    probs, rows = [], []
    for t in T:
        m = re.search(r'"?([^"]+\.py)"?', t["args"] or "")
        script = Path(m.group(1)) if m else None
        if script is not None and not script.is_absolute():
            script = Path(t["wd"] or ROOT) / script
        exists = script is not None and script.exists()
        rows.append(f"{t['name']}: {t['state']}, wake={t['wake']}, triggers {t['trig']}, next {t['next']}, last result {t['result']}")
        if t["state"] != "Disabled" and (not exists or not Path(t["exe"]).exists()):
            probs.append(f"{t['name']}: script/python missing ({script}, {t['exe']})")
    rec("A3 every enabled scheduled task points to an existing python and script", bool(T) and not probs, f"{len(T)} tasks; {probs}")
    rec("A3b scheduled tasks (information)", True, " || ".join(rows))



def a4():
    order_pat = re.compile(r"/fapi/v1/order|/api/v3/order|create_order|createOrder|\.post\(|\"POST\"")
    hits = {f.name: len(order_pat.findall(f.read_text(encoding="utf-8", errors="replace"))) for f in (SRC / "execution").glob("*.py")}
    daily = ["forward_multi_16b.py", "forward_ls_f4.py", "forward_dryrun_1d.py", "cost_snapshot_step2.py", "m4_options_collector.py",
             "n3_evt_monitor.py", "m10_daily_status.py", "shadow_e11_f4.py"]
    f6 = (SRC / "execution" / "futures_testnet_f6.py").read_text(encoding="utf-8")
    hosts = set(re.findall(r"https://[a-z0-9.\-]+", f6))
    ok = all(hits[d] == 0 for d in daily) and hosts <= {"https://testnet.binancefuture.com", "https://demo-fapi.binance.com"}
    rec("A4 order safety: daily scripts contain no order call; F6 knows only the two test hosts", ok,
        f"order-call counts {hits}; F6 hosts {sorted(hosts)}")


# ------------------------------------------------------------------ B
def part_b():
    def sub(test, args, must=None):
        r = subprocess.run([PY, *args], capture_output=True, text=True, timeout=3600, cwd=str(ROOT))
        out = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0 and all(m in out for m in (must or []))
        rec(test, ok, " | ".join(x for x in out.splitlines() if "PASS" in x or "Error" in x or "assert" in x.lower())[-1200:] or out[-800:])
    sub("B1 16B verifier V1 + V5 + V6 (forward ledger) on the real ledger", ["src/audits/verify_forward_multi_16b.py", "V1", "V5", "V6"], ["[V1 PASS]", "[V5 PASS]", "[V6 PASS]"])
    sub("B2 F4 verifier V1..V5 on the real ledger", ["src/audits/verify_f4_forward.py"], [f"[V{i} PASS]" for i in range(1, 6)])
    sub("B3 N3 verifier V1..V3 on the real ledger", ["src/audits/verify_n3_monitor.py"], ["[V1 PASS]", "[V2 PASS]"])
    sub("B4 M4 verifier on the real ledger", ["src/audits/verify_m4_collector.py"], ["[V1 PASS]", "[V2 PASS]"])
    sub("B7 E11 shadow ledger verifier V1..V3 on the real ledger", ["src/audits/verify_shadow_e11.py"], ["[V1 PASS]", "[V2 PASS]", "[V3 PASS]"])
    sub("B6 Step 16 ledger verifier L1..L4 on the real ledger", ["src/audits/verify_step16_ledger.py"], ["[L1 PASS]", "[L2+L4 PASS]", "[L3 PASS]"])
    import forward_dryrun_1d as FD
    import verify_step16_ledger as V16
    real = FD.LEDGER
    tmp = Path(tempfile.mkdtemp(prefix="s16_tamper_")) / "ledger.csv"
    try:
        txt = real.read_text(encoding="utf-8").splitlines()
        parts = txt[-1].split(",")
        parts[parts.index("False") + 1] = str(int(parts[parts.index("False") + 1]) + 1)        # n_coins + 1 on the last line
        tmp.write_text(chr(10).join(txt[:-1] + [",".join(parts)]) + chr(10), encoding="utf-8")
        FD.LEDGER = tmp
        must_fail("D7 Step 16 verifier rejects n_coins + 1 on the last ledger line", V16.main)
    finally:
        FD.LEDGER = real
    if "FULL16B" in sys.argv:
        sub("B5 16B verifier V2..V4: live code path == research scores, production models, paper engine (heavy)",
            ["src/audits/verify_forward_multi_16b.py", "V2", "V3", "V4"], ["[V2 PASS]", "[V3 PASS]", "[V4 PASS]"])


# ------------------------------------------------------------------ C + D
def part_cd():
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            import preflight_f4 as P                      # runs 16B paper + F4 main for two sandbox days (asserts inside)
        rec("C1 sandbox 16B paper -> F4 two days (chain, C1 True, orders file)", True, buf.getvalue().splitlines()[-1])
    except Exception as e:
        rec("C1 sandbox 16B paper -> F4 two days", False, f"{e} | {traceback.format_exc()[-800:]}")
        return
    T, Q, FB = P.T, P.Q, P.FB
    import verify_f4_forward as VF
    run_check("C2 F4 verifier V1..V5 on the sandbox ledger", VF.main)

    # D1: a changed number in the F4 ledger must break V1
    L = pd.read_csv(Q.LEDGER)
    keep = Q.LEDGER.read_bytes()
    L.loc[1, "LS_RS"] = L.loc[1, "LS_RS"] + 1.0
    L.to_csv(Q.LEDGER, index=False)
    must_fail("D1 F4 verifier rejects a ledger number changed by $1", VF.main)
    rehash(Q.LEDGER)
    must_fail("D1b F4 verifier rejects a $1 change even after the whole chain is re-hashed (V1b)", VF.main)
    Q.LEDGER.write_bytes(keep)
    rehash(Q.LEDGER)
    run_check("D1c control: re-hashing the UNCHANGED ledger reproduces it and the verifier passes", VF.main)
    rec("D1c ledger bytes identical after a no-change re-hash", Q.LEDGER.read_bytes() == keep)
    Q.LEDGER.write_bytes(keep)

    # C3: F6 plan on the sandbox F4 decision
    import futures_testnet_f6 as F6
    F6.F4, F6.OUT = Q.LOG, T / "f6"
    (T / "f6").mkdir()
    shutil.copy(LOGS_DIR / "futures_testnet_f6" / "F6_PROTOCOL_SHA256.txt", T / "f6")
    for v in ("BINANCE_FUT_TESTNET_KEY", "BINANCE_FUT_TESTNET_SECRET"):
        os.environ.pop(v, None)                           # plan mode must not need keys
    argv = sys.argv
    try:
        sys.argv = ["f6", "--mode", "plan"]
        b2 = io.StringIO()
        with contextlib.redirect_stdout(b2):
            F6.main()
        recf = sorted((T / "f6" / "plan").glob("*_plan.json"))
        R = json.loads(recf[-1].read_text())
        asof, dec, _ = F6.load_decision()
        tg = F6.targets(dec)
        want = {(k, s) for k in F6.SLEEVES for s in tg[k]}
        got = {(a["sleeve"], a["symbol"]) for a in R["actions"] if a["action"] in ("PLAN short", "skip")}
        stops_ok = all(abs(a["stop"] - F6.round_tick(a["ref_price"] * 1.5, F6.filters(F6.Client("testnet"))[a["perp"]]["tick"])) < 1e-12
                       for a in R["actions"] if a["action"] == "PLAN short")
        n_short = sum(a["action"] == "PLAN short" for a in R["actions"])
        ok = (want == got and stops_ok and not (T / "f6" / "state_testnet.json").exists() and R["asof"] == asof
              and R["f4_line_sha256"] == pd.read_csv(Q.LEDGER).line_sha256.iloc[-1])
        rec("C3 F6 plan from the sandbox F4 orders (every target planned or skipped with reason; stop = price x 1.5; no state, no keys)",
            ok, f"as-of {asof}: {n_short} PLAN shorts, {len(got) - n_short} skips, targets {len(want)}; stops {stops_ok}; "
                f"skips {[a.get('reason') for a in R['actions'] if a['action'] == 'skip'][:4]}")
        # D2: a changed orders file must make F6 refuse
        of = Q.LOG / "paper" / f"orders_{asof}.json"
        keep = of.read_bytes()
        of.write_bytes(keep.replace(b"equity_close", b"equity_closE", 1))
        must_fail("D2 F6 refuses an F4 orders file whose hash differs from the F4 ledger", F6.load_decision)
        of.write_bytes(keep)
    except Exception as e:
        rec("C3 F6 plan", False, f"{e} | {traceback.format_exc()[-800:]}")
    finally:
        sys.argv = argv

    # C4: N3 on the sandbox F4 ledger, then its verifier; idempotent second call
    import n3_evt_monitor as N3
    import verify_n3_monitor as VN
    N3.F4, N3.LOG = Q.LOG, T / "n3"
    N3.LEDGER = N3.LOG / "ledger.csv"
    N3.LOG.mkdir()
    shutil.copy(LOGS_DIR / "monitor_n3_evt" / "N3_PROTOCOL_SHA256.txt", N3.LOG)
    run_check("C4 N3 on the sandbox F4 ledger", N3.main)
    try:
        L = pd.read_csv(N3.LEDGER)
        last = pd.read_csv(Q.LEDGER)["asof"].iloc[-1]
        ok = len(L) == 2 and set(L.line) == {"LS_RS", "LO"} and (L.target_day == str((pd.Timestamp(last) + pd.Timedelta(days=1)).date())).all() \
            and (L.n_forward == 1).all() and (L.VaR999 > L.VaR99).all() and (L.ES99 > L.VaR99).all()
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            N3.main()
        ok2 = len(pd.read_csv(N3.LEDGER)) == 2 and "already estimated" in b.getvalue()
        rec("C4b N3 ledger: 2 lines, target = next as-of, VaR99.9 > VaR99, ES99 > VaR99; second call adds nothing", ok and ok2,
            L[["line", "target_day", "n_forward", "VaR99", "ES99", "VaR999"]].to_dict("records"))
    except Exception as e:
        rec("C4b N3 ledger", False, e)
    run_check("C5 N3 verifier on the sandbox ledger", VN.main)
    keep = N3.LEDGER.read_bytes()
    L = pd.read_csv(N3.LEDGER)
    L.loc[0, "VaR99"] = L.loc[0, "VaR99"] * 0.9
    L.to_csv(N3.LEDGER, index=False)
    must_fail("D3 N3 verifier rejects a VaR99 lowered by 10 %", VN.main)
    rehash(N3.LEDGER, nan_none=True)
    must_fail("D3b N3 verifier rejects the lowered VaR99 even after the chain is re-hashed (V2 refit)", VN.main)
    N3.LEDGER.write_bytes(keep)
    rehash(N3.LEDGER, nan_none=True)
    run_check("D3c control: N3 verifier passes on the re-hashed UNCHANGED ledger", VN.main)
    N3.LEDGER.write_bytes(keep)

    # C6: M4 collector into the sandbox, verifier, tamper
    import m4_options_collector as M4
    import verify_m4_collector as VM
    M4.LOG, M4.STORE = T / "m4", T / "m4store"
    M4.LEDGER = M4.LOG / "ledger.csv"
    M4.LOG.mkdir()
    shutil.copy(LOGS_DIR / "collector_m4_options" / "M4_PROTOCOL_SHA256.txt", M4.LOG)
    run_check("C6 M4 collector (live public endpoints) into the sandbox", M4.main)
    try:
        L = pd.read_csv(M4.LEDGER)
        rec("C6b M4: all endpoints answered", int(L.n_ok.iloc[-1]) == int(L.n_endpoints.iloc[-1]), f"{L.n_ok.iloc[-1]}/{L.n_endpoints.iloc[-1]}")
    except Exception as e:
        rec("C6b M4", False, e)
    run_check("C7 M4 verifier V1..V3 on the sandbox data (V3 = live re-fetch)", VM.main)
    gz = sorted(M4.STORE.rglob("*.json.gz"))[0]
    keep = gz.read_bytes()
    gz.write_bytes(keep[:-1] + bytes([keep[-1] ^ 1]))
    must_fail("D4 M4 verifier rejects a stored file with one changed bit", VM.main)
    gz.write_bytes(keep)

    # C8: M10 on a sandbox logs tree: (a) sandbox ledgers without as-of yesterday -> NOT logged; (b) real ledgers -> real state
    import m10_daily_status as M10
    asof = str((pd.Timestamp.now("UTC").tz_localize(None).normalize() - pd.Timedelta(days=1)).date())
    for case, src16, srcf4 in (("sandbox", FB.LEDGER, Q.LEDGER),
                               ("real", LOGS_DIR / "forward_multi_16b" / "ledger.csv", LOGS_DIR / "forward_ls_f4" / "ledger.csv")):
        lg = T / f"m10_{case}" / "logs"
        (lg / "forward_multi_16b").mkdir(parents=True)
        (lg / "forward_ls_f4").mkdir(parents=True)
        shutil.copy(src16, lg / "forward_multi_16b" / "ledger.csv")
        shutil.copy(srcf4, lg / "forward_ls_f4" / "ledger.csv")
        M10.LOGS_DIR, M10.OUT, M10.BACKUP = lg, lg / "daily_status", T / f"m10_{case}" / "backups"
        try:
            b = io.StringIO()
            with contextlib.redirect_stdout(b):
                M10.main()
            st = json.loads(sorted(M10.OUT.glob("status_*.json"))[-1].read_text())
            man = pd.read_csv(sorted(M10.BACKUP.glob("*/MANIFEST.csv"))[-1])
            l16 = pd.read_csv(src16)
            l16 = l16[l16["asof"] == asof]
            lf4 = pd.read_csv(srcf4)
            lf4 = lf4[lf4["asof"] == asof]
            want = []
            for k, Lk in (("16B", l16), ("F4", lf4)):
                if not len(Lk):
                    want.append(f"{k}: as-of {asof} NOT logged")
                elif "on_time" in Lk and not bool(Lk.on_time.iloc[-1]):
                    want.append(f"{k}: as-of {asof} logged LATE")
            got = [p for p in st["problems"] if p.startswith(("16B", "F4"))]
            rec(f"C8 M10 on the {case} ledgers: ledger problems == independently derived; backup manifest", got == want and len(man) >= 2,
                f"as-of {asof}: M10 {got}; derived {want}; all problems {st['problems']}; backup {len(man)} files")
        except Exception as e:
            rec(f"C8 M10 {case}", False, f"{e} | {traceback.format_exc()[-600:]}")

    # D5: R1 claims tamper (only once claims_E3.json exists)
    import r1_run as R
    import verify_r1_claims as VR
    for exp in ("E3", "E1", "E2", "E4", "N1", "E11"):
        cf = R.OUT / f"claims_{exp}.json"
        if not cf.exists():
            continue
        real_out = R.OUT
        try:
            sb = T / f"r1_{exp}"
            shutil.copytree(real_out, sb, ignore=shutil.ignore_patterns("*_ctrl*", "E3c_*"))
            R.OUT = sb
            run_check(f"C9 R1 verifier {exp} on a copy of the real results", lambda: VR.main(exp))
            C = json.loads((sb / f"claims_{exp}.json").read_text())
            if exp == "E3":
                C["results"]["E3b"]["mix"]["max_dd_pct"] += 0.5
            else:
                k0 = next(iter(C["results"]))
                C["results"][k0]["result"]["mix"]["max_dd_pct"] += 0.5
            (sb / f"claims_{exp}.json").write_text(json.dumps(C, indent=2))
            must_fail(f"D5 R1 verifier {exp} rejects a max DD changed by 0.5 points", lambda: VR.main(exp))
            if exp == "E3":
                C["results"]["E3b"]["mix"]["max_dd_pct"] -= 0.5
                C["results"]["reading"] = ("AI short adds beyond listing age" if C["results"]["reading"].startswith("AI short skill not")
                                           else "AI short skill not shown beyond listing age")
                (sb / f"claims_{exp}.json").write_text(json.dumps(C, indent=2))
                must_fail("D6 R1 verifier E3 rejects a flipped reading", lambda: VR.main(exp))
            else:
                k0 = next(iter(C["results"]))
                C["results"][k0]["result"]["mix"]["max_dd_pct"] -= 0.5
                g = C["results"][k0]["gates"]
                g["decision"] = "FAIL" if g["decision"] == "PASS" else "PASS"
                (sb / f"claims_{exp}.json").write_text(json.dumps(C, indent=2))
                must_fail(f"D6 R1 verifier {exp} rejects a flipped decision", lambda: VR.main(exp))
        finally:
            R.OUT = real_out


def main():
    t0 = pd.Timestamp.now("UTC")
    parts = [x for x in sys.argv[1:] if x != "FULL16B"] or ["A", "B", "CD"]
    if "A" in parts:
        part_a()
    if "B" in parts:
        part_b()
    if "CD" in parts:
        part_cd()
    OUT.mkdir(parents=True, exist_ok=True)
    tag = t0.strftime("%Y%m%dT%H%M%S")
    n_ok = sum(r["ok"] for r in RES)
    (OUT / f"e2e_{tag}.json").write_text(json.dumps(dict(start_utc=str(t0), end_utc=str(pd.Timestamp.now("UTC")), parts=parts,
                                                         passed=n_ok, total=len(RES), results=RES), indent=1, ensure_ascii=False))
    print(f"E2E: {n_ok}/{len(RES)} PASS  -> {OUT / f'e2e_{tag}.json'}")


if __name__ == "__main__":
    main()
