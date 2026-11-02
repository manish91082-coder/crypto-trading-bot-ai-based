"""
M10 daily status + local backup (no GitHub, no network). Runs after the morning tasks (10:15 IST).
1. Status: for each scheduled task -> last run time / result / next run (Windows Task Scheduler via PowerShell);
   for each ledger -> did the expected as-of day get logged, on_time, C1 (F4), notes.
2. Writes logs/daily_status/status_<date>.md (Hindi summary at the top) and .json; appends one line to status_ledger.csv.
3. Backup: copies every ledger / protocol / paper / prediction / claims file of the forward logs into
   backups/<date>/ (same disk; a copy against accidental edits or deletion) and records each file's SHA256 in a manifest;
   verifies the copies by re-hashing them.
Usage: pythonw m10_daily_status.py
"""
import os
import sys
import json
import shutil
import hashlib
import subprocess
import traceback
from pathlib import Path

import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from config import LOGS_DIR

ROOT = LOGS_DIR.parent
OUT = LOGS_DIR / "daily_status"
BACKUP = ROOT / "backups"
TASKS = ["CryptoBot_Step2_CostSnapshot", "CryptoBot1D_ForwardDryRun", "CryptoBot16B_ForwardMulti", "CryptoBot_F4_LSPaper",
         "CryptoBot_N3_EVTMonitor", "CryptoBot_M4_OptionsCollector"]
BACKUP_GLOBS = ["forward_multi_16b/ledger.csv", "forward_multi_16b/*.md", "forward_multi_16b/*.txt", "forward_multi_16b/paper/*",
                "forward_multi_16b/predictions/*", "forward_ls_f4/ledger.csv", "forward_ls_f4/*.md", "forward_ls_f4/*.txt",
                "forward_ls_f4/paper/*", "forward_ls_f4/shadow_e11/*", "strategy_1d_step16_forward/ledger*.csv", "strategy_1d_step16_forward/predictions/*",
                "monitor_n3_evt/ledger.csv", "collector_m4_options/ledger.csv", "cost_study_step2/snapshots.csv",
                "cost_study_step2/*.md", "research_r1/*.md", "research_r1/*.txt", "research_r1/claims_*.json"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


LINUX_JOBS = ["Step2_CostSnapshot", "Step16_ForwardDryRun", "16B_ForwardMulti", "F4_LSPaper", "N3_EVTMonitor",
              "M4_OptionsCollector", "F6_DemoOps"]                 # cron job names of deploy/crontab.txt (cloud VM)


def task_info_linux():
    """cloud VM: the cron wrapper deploy/run_job.sh appends start / end / exit code per job to logs/cron_status/<job>.csv."""
    out = []
    for j in LINUX_JOBS:
        f = LOGS_DIR / "cron_status" / f"{j}.csv"
        if not f.exists():
            out.append(dict(name=j, state="Ready", last=None, result=267011, next="cron"))   # 267011 = not yet run
            continue
        d = pd.read_csv(f)
        out.append(dict(name=j, state="Ready", last=str(d.end_utc.iloc[-1]), result=int(d.exit_code.iloc[-1]), next="cron"))
    return out


def task_info():
    if os.name != "nt":
        return task_info_linux()
    ps = ("Get-ScheduledTask | Where-Object {$_.TaskName -like 'CryptoBot*'} | ForEach-Object { $i = Get-ScheduledTaskInfo $_.TaskName; "
          "[pscustomobject]@{name=$_.TaskName; state=[string]$_.State; last=[string]$i.LastRunTime; result=$i.LastTaskResult; next=[string]$i.NextRunTime} } "
          "| ConvertTo-Json")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=120)
    d = json.loads(r.stdout) if r.stdout.strip() else []
    return d if isinstance(d, list) else [d]


def ledger_status(asof):
    out = {}
    f16 = LOGS_DIR / "forward_multi_16b" / "ledger.csv"
    if f16.exists():
        L = pd.read_csv(f16)
        L = L[L["asof"] == asof]
        out["16B"] = dict(logged=bool(len(L)), on_time=bool(L.on_time.iloc[-1]) if len(L) else None,
                          notes=str(L.notes.iloc[-1])[:200] if len(L) else None)
    f4 = LOGS_DIR / "forward_ls_f4" / "ledger.csv"
    if f4.exists():
        L = pd.read_csv(f4)
        L = L[L["asof"] == asof]
        out["F4"] = dict(logged=bool(len(L)), on_time=bool(L.on_time.iloc[-1]) if len(L) else None,
                         C1=bool(L.C1.iloc[-1]) if len(L) else None, LS_RS=float(L.LS_RS.iloc[-1]) if len(L) else None,
                         LO=float(L.LO.iloc[-1]) if len(L) else None)
    n3 = LOGS_DIR / "monitor_n3_evt" / "ledger.csv"
    if n3.exists():
        L = pd.read_csv(n3)
        out["N3"] = dict(last_target=str(L.target_day.iloc[-1]), lines=int(len(L)))
    m4 = LOGS_DIR / "collector_m4_options" / "ledger.csv"
    if m4.exists():
        L = pd.read_csv(m4)
        out["M4"] = dict(last_day=str(L.day.iloc[-1]), ok=f"{L.n_ok.iloc[-1]}/{L.n_endpoints.iloc[-1]}")
    cs = LOGS_DIR / "cost_study_step2" / "snapshots.csv"
    if cs.exists():
        d = pd.read_csv(cs, usecols=["round_utc"])
        out["cost_rounds_total"] = int(d.round_utc.nunique())
    return out


def backup(day):
    dst = BACKUP / day
    man = []
    for g in BACKUP_GLOBS:
        for f in sorted(LOGS_DIR.glob(g)):
            if f.is_file():
                rel = f.relative_to(LOGS_DIR)
                t = dst / rel
                t.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, t)
                h = sha(f)
                assert sha(t) == h, f"backup copy differs: {rel}"
                man.append(dict(file=str(rel), sha256=h, bytes=f.stat().st_size))
    pd.DataFrame(man).to_csv(dst / "MANIFEST.csv", index=False)
    return len(man), sum(m["bytes"] for m in man)


def main():
    now = pd.Timestamp.now("UTC").tz_localize(None)
    asof = str((now.normalize() - pd.Timedelta(days=1)).date())
    tasks = task_info()
    led = ledger_status(asof)
    nb, size = backup(str(now.date()))
    problems = []
    for t in tasks:
        if t["name"] in TASKS + LINUX_JOBS and t["state"] != "Disabled" and t["result"] not in (0, 267009, 267011):   # 0 ok, 0x41301 running, 0x41303 not yet run
            problems.append(f"task {t['name']} last result {t['result']}")
    for k in ("16B", "F4"):
        if k in led and not led[k]["logged"]:
            problems.append(f"{k}: as-of {asof} NOT logged")
        elif k in led and led[k]["on_time"] is False:
            problems.append(f"{k}: as-of {asof} logged LATE")
    if "F4" in led and led["F4"]["logged"] and led["F4"]["C1"] is False:
        problems.append("F4: C1 FAIL (LO line != 16B paper)")
    OUT.mkdir(parents=True, exist_ok=True)
    rec = dict(run_utc=str(now), asof=asof, problems=problems, ledgers=led, tasks=tasks, backup_files=nb, backup_bytes=size)
    (OUT / f"status_{now.date()}.json").write_text(json.dumps(rec, indent=2, default=str))
    head = "✅ सब ठीक" if not problems else "⚠️ ध्यान दें: " + "; ".join(problems)
    md = [f"# रोज़ का status {now.date()} (as-of {asof})", "", f"**{head}**", "", "## Ledgers"]
    md += [f"- **{k}:** {v}" for k, v in led.items()]
    md += ["", "## Tasks"] + [f"- {t['name']}: state {t['state']}, last {t['last']}, result {t['result']}, next {t['next']}" for t in tasks]
    md += ["", f"## Backup: {nb} files ({size/1e6:.1f} MB) → backups/{now.date()}/ (हर copy का SHA256 मिलाया गया)"]
    (OUT / f"status_{now.date()}.md").write_text("\n".join(md), encoding="utf-8")
    pd.DataFrame([dict(run_utc=str(now), asof=asof, n_problems=len(problems), problems=json.dumps(problems, ensure_ascii=False),
                       backup_files=nb)]).to_csv(OUT / "status_ledger.csv", mode="a", index=False, header=not (OUT / "status_ledger.csv").exists())
    print(head)
    print(f"backup: {nb} files, {size/1e6:.1f} MB")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        with open(OUT / "run_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{pd.Timestamp.now('UTC')}] RUN FAILED\n{traceback.format_exc()}\n")
        sys.exit(1)
