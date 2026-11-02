"""ECO alerts (amendment 2 §8). Reads the ECO ledger and the cron status files; appends NEW alerts to logs/eco/alerts.jsonl and,
only if the user has set ECO_TELEGRAM_TOKEN and ECO_TELEGRAM_CHAT in .env, sends them to that Telegram chat.
Usage (VM cron, hourly after the cycle):  python src/eco/eco_alerts.py [--root data/eco] [--now "2026-10-22 10:30"]
An alert is sent once per (kind, key); it is sent again only after the condition has cleared.
Amendment 3 (logs/eco/ECO_AMENDMENT_3_PREREGISTERED.md): DDX drawdown alarm (yellow / red, warning only) from
deploy/eco_dd_alarm.json, and the job-failure check covers every run_job.sh job of the installed crontab."""
import argparse
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_core as C

PROJ = C.PROJ
DD_CFG = PROJ / "deploy" / "eco_dd_alarm.json"
# amendment 3 §2: the 29 run_job.sh names of deploy/crontab.txt 13443469f4ec...
JOBS = ("16B_ForwardMulti", "ECO_Alerts", "ECO_Demo", "ECO_Demo_Verify", "ECO_Plan", "ECO_Shadow", "ECO_Shadow_Verify",
        "ECO_Tracking", "ECO_Verify", "EMO_Meter", "EMO_Verify", "F4_LSPaper", "FR2_Recorder", "FwdWatch", "FwdWatch_Verify",
        "LiqCollector_Verify", "LogShip", "M10_DailyStatus", "M4_OptionsCollector", "MK1", "MK1_Verify", "N3_EVTMonitor",
        "PaperN1", "PaperN1_Verify", "PaperSpotS1", "PaperSpotS1_Verify", "SleeveA_Forward", "Step16_ForwardDryRun",
        "Step2_CostSnapshot")


def _eq(r):
    e = r.get("eco_equity")
    return float(e) if isinstance(e, (int, float)) and not isinstance(e, bool) and math.isfinite(e) else None


def dd_status(L, now, cfg):
    """amendment 3 §1: running max drawdown of eco_equity since cfg start, the live age a, the band H* and the level.
    -> dict, or None when there is no equity at or after the start."""
    start = pd.Timestamp(cfg["start_utc"])
    rows = [(pd.Timestamp(r["T"]), _eq(r)) for r in L if r.get("mode") != "reset"]
    rows = [(t, e) for t, e in rows if e is not None]
    pre = [x for x in rows if x[0] < start]
    post = [x for x in rows if x[0] >= start]
    if not post:
        return None
    series = ([pre[-1]] if pre else []) + post
    peak, dd = series[0][1], 0.0
    for _, e in series:
        peak = max(peak, e)
        dd = max(dd, 1.0 - e / peak)
    a = math.floor((now - start) / pd.Timedelta(days=1))
    bands = sorted(cfg["bands"], key=lambda b: b["H"])
    band = next((b for b in bands if b["H"] >= a), bands[-1])
    level = None if a < 0 else "red" if dd > band["red_dd"] else "yellow" if dd > band["yellow_dd"] else "normal"
    return dict(dd=dd, base_T=str(series[0][0]), peak=peak, eq=series[-1][1], a=a, H=band["H"], yellow=band["yellow_dd"],
                red=band["red_dd"], level=level, n=len(series))


def conditions(L, cron_dir, now, dd_cfg=DD_CFG):
    """-> {(kind, key): message} of the conditions that hold now."""
    out = {}
    cyc = [r for r in L if r.get("mode") != "reset"]
    if not cyc:
        return {("no_cycle", "-"): "no ECO cycle recorded yet"}
    try:
        s = dd_status(L, now, json.loads(Path(dd_cfg).read_text(encoding="utf-8")))
    except Exception as e:                                                  # noqa: BLE001 - fail loud as an alert
        out[("dd_alarm_off", "-")] = f"drawdown alarm not running: {dd_cfg} unreadable ({type(e).__name__})"
        s = None
    if s and s["level"] in ("yellow", "red"):
        out[(f"dd_{s['level']}", f"H{s['H']}")] = (
            f"drawdown {s['dd']:.2%} since {s['base_T']} (peak {s['peak']:.2f}, now {s['eq']:.2f}, age {s['a']} d) > "
            f"{s['level'].upper()} {s[s['level']]:.2%} (DDX B_ALL {'p95' if s['level'] == 'yellow' else 'p99'}, H* {s['H']} d); "
            f"warning only; no trade change; kill switch unchanged")
    last = cyc[-1]
    if (now - pd.Timestamp(last["T"])) > pd.Timedelta(hours=2):
        out[("no_cycle", "-")] = f"no ECO cycle for {(now - pd.Timestamp(last['T'])) / pd.Timedelta(hours=1):.1f} h (last {last['T']})"
    if L[-1].get("halted"):
        out[("halted", "-")] = f"HALTED: {L[-1]['halted']}"
    if not last.get("ok"):
        out[("failed_cycle", last["T"])] = f"cycle {last['T']} FAILED: {(last.get('error') or '')[-300:]}"
    if (last.get("n_px_missing") or 0) >= 2:
        out[("px_missing", ",".join(last.get("px_missing", [])))] = f"held perps without price for {last['n_px_missing']} cycles: {last.get('px_missing')}"
    fz = [r for r in cyc[-3:] if r.get("ok") and r.get("frozen_strategies")]
    if len(fz) >= 3:
        out[("frozen_strategy", ",".join(sorted(fz[-1]["frozen_strategies"])))] = f"producer frozen for 3 cycles: {fz[-1]['frozen_strategies']}"
    if last.get("reconcile_mismatch"):
        out[("mismatch", ",".join(sorted(last["reconcile_mismatch"])))] = f"reconcile mismatch (symbol frozen): {last['reconcile_mismatch']}"
    for n in last.get("notes", []) or []:
        if n.startswith("exchange stop G|") and "booked" in n:
            out[("guard_fired", n[:60])] = n
        if n.startswith("orphan ECO stop"):
            out[("orphan_stop", n[:60])] = n
    if last.get("delisting"):
        out[("delisting", ",".join(last["delisting"]))] = f"delisting announced on targeted / held perps (targets 0): {last['delisting']}"
    if last.get("held_not_trading"):
        out[("held_not_trading", ",".join(last["held_not_trading"]))] = f"held perps no longer trading (cannot be closed by code): {last['held_not_trading']}"
    if last.get("foreign_stops"):
        out[("foreign_stops", str(len(last["foreign_stops"])))] = f"foreign open algo orders on the demo account: {last['foreign_stops'][:5]}"
    for job in JOBS:
        f = Path(cron_dir) / f"{job}.csv"
        if f.exists():
            d = pd.read_csv(f)
            if len(d) and int(d.exit_code.iloc[-1]) != 0:
                out[(f"job_fail_{job}", str(d.start_utc.iloc[-1]))] = f"cron job {job} exit {int(d.exit_code.iloc[-1])} at {d.start_utc.iloc[-1]}"
    return out


def telegram(msg):
    tok, chat = os.getenv("ECO_TELEGRAM_TOKEN", ""), os.getenv("ECO_TELEGRAM_CHAT", "")
    if not (tok and chat):
        return "not configured (file only)"
    data = urllib.parse.urlencode(dict(chat_id=chat, text=msg[:3500])).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data), timeout=20) as r:
            return f"sent {r.status}"
    except Exception as e:                                                  # noqa: BLE001 - recorded, never fatal
        return f"send failed: {type(e).__name__}"


def load_ledger(root):
    f = root / "ledger.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def run(root, out_dir, cron_dir, now, send=telegram, dd_cfg=DD_CFG):
    L = load_ledger(root)
    cond = conditions(L, cron_dir, now, dd_cfg)
    sf = out_dir / "alerts_state.json"
    active = json.loads(sf.read_text()) if sf.exists() else []
    new = [k for k in cond if "|".join(k) not in active]
    out = []
    for k in new:
        msg = f"ECO {root.name} [{k[0]}] {cond[k]}"
        out.append(dict(T=str(now), kind=k[0], key=k[1], msg=msg, delivery=send(msg)))
    if out:
        with open(out_dir / "alerts.jsonl", "a", encoding="utf-8") as fh:
            for a in out:
                fh.write(json.dumps(a) + "\n")
    C.write_json_atomic(sf, sorted("|".join(k) for k in cond), keep_prev=False)
    return out, cond


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/eco")
    ap.add_argument("--now", default=None)
    a = ap.parse_args()
    now = pd.Timestamp(a.now) if a.now else pd.Timestamp.now("UTC").tz_localize(None)
    root = PROJ / a.root
    out_dir = PROJ / "logs" / "eco" / ("alerts" if root.name == "eco" else f"alerts_{root.name}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out, cond = run(root, out_dir, PROJ / "logs" / "cron_status", now)
    print(f"eco alerts {now}: {len(cond)} conditions active, {len(out)} new: {[a['msg'][:120] for a in out]}")
    try:                                                                    # amendment 3 §1: the dd line, alarm or not
        s = dd_status(load_ledger(root), now, json.loads(DD_CFG.read_text(encoding="utf-8")))
        print("dd -" if s is None else f"dd {s['dd']:.6f} age {s['a']} H* {s['H']} yellow {s['yellow']:.6f} red {s['red']:.6f} "
              f"level {s['level']} base {s['base_T']} n {s['n']}")
    except Exception as e:                                                  # noqa: BLE001 - already an alert condition
        print(f"dd alarm off: {type(e).__name__}")


if __name__ == "__main__":
    main()
