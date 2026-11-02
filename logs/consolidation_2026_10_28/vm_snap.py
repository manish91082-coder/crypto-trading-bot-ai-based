# Read-only VM snapshot for CONSOL-2026-10-28. Reads files and prints; writes nothing.
import csv, glob, gzip, hashlib, json, os, subprocess, datetime as dt
os.chdir("/opt/cryptobot")
now = dt.datetime.now(dt.timezone.utc)
def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
def sec(t):
    print(f"\n=== {t}")
sec("TIME"); print("utc_now", now.isoformat(timespec="seconds"))
sec("HOST"); print(sh("uptime")); print(sh("df -h / | tail -1")); print(sh("free -m | head -2"))
sec("CRONTAB"); print("crontab_l_sha256", sh("crontab -l | sha256sum").split()[0])
print("deploy_crontab_sha256", hashlib.sha256(open("deploy/crontab.txt","rb").read()).hexdigest())

sec("CRON_STATUS last 48h")
cut = now - dt.timedelta(hours=48)
for f in sorted(glob.glob("logs/cron_status/*.csv")):
    rows = list(csv.DictReader(open(f, newline="")))
    if not rows:
        print(os.path.basename(f), "empty"); continue
    keys = rows[0].keys()
    tk = next((k for k in keys if "start" in k.lower() or "time" in k.lower() or "utc" in k.lower()), None)
    ek = next((k for k in keys if "exit" in k.lower() or k.lower() in ("rc", "code")), None)
    recent, bad, last = 0, 0, rows[-1]
    for r in rows:
        try:
            t = dt.datetime.fromisoformat(r[tk].replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))
        except Exception:
            continue
        if t >= cut:
            recent += 1
            if str(r.get(ek, "0")).strip() not in ("0", ""):
                bad += 1
    print(f"{os.path.basename(f)[:-4]}: runs48h={recent} nonzero48h={bad} last_time={last.get(tk)} last_exit={last.get(ek)}")

def ledger(path):
    L = [json.loads(x) for x in open(path) if x.strip()]
    return L
sec("ECO_DEMO ledger")
for root in ("data/eco_demo", "data/eco_shadow"):
    L = ledger(f"{root}/ledger.jsonl")
    keys = list(L[-1].keys())
    print(root, "cycles", len(L), "keys", keys[:25])
    ek = next((k for k in ("eco_equity", "equity_eco", "equity") if k in L[-1]), None)
    if ek:
        eq = [float(x[ek]) for x in L if x.get(ek) is not None]
        peak, mdd = eq[0], 0.0
        for v in eq:
            peak = max(peak, v); mdd = max(mdd, 1 - v / peak)
        tk = next((k for k in ("ts_utc", "t_utc", "cycle_utc", "time_utc", "ts") if k in L[-1]), None)
        print(root, "first", L[0].get(tk), eq[0], "last", L[-1].get(tk), eq[-1], "peak", max(eq), "maxDD_pct", round(100 * mdd, 3))
    st = json.load(open(f"{root}/state.json"))
    print(root, "state halted", st.get("halted"), "state keys", list(st.keys())[:20])

sec("ECO_DEMO alerts tail")
for p in ("data/eco_demo/alerts.jsonl", "logs/eco/alerts.jsonl"):
    if os.path.exists(p):
        print(p, sh(f"wc -l < {p}")); print(sh(f"tail -3 {p}"))

sec("TC tracking")
print(sh("cat logs/eco/tracking/tc_daily.csv"))
print(sh("head -c 3000 logs/eco/tracking/tc_report.json"))

sec("SLEEVE_A forward")
print(sh("ls -la logs/paper_n1/sleeve_a_forward"))
for f in sorted(glob.glob("logs/paper_n1/sleeve_a_forward/*")):
    if f.endswith((".csv", ".json", ".txt", ".md")):
        print("--", f); print(sh(f"tail -c 2500 '{f}'"))

sec("PAPER_N1")
L = ledger("data/paper_n1/ledger.jsonl"); print("records", len(L)); print(json.dumps(L[-1])[:1500])

sec("PAPER_SPOT_S1")
L = ledger("data/paper_spot_s1/ledger.jsonl"); print("records", len(L)); print(json.dumps(L[0])[:600]); print(json.dumps(L[-1])[:900])

sec("MK1")
print(sh("cat data/eco_maker/mk1_summary.json | head -c 3000")); print("orders_rows", sh("wc -l < data/eco_maker/mk1_orders.csv"))

sec("FWD_WATCH")
print(sh("ls -la data/fwd_watch/out"))
for f in sorted(glob.glob("data/fwd_watch/out/*.json")):
    print("--", f); print(sh(f"head -c 2500 '{f}'"))

sec("LIQ collector")
print(sh("cat data/live_collect/liq/heartbeat.txt")); print(sh("tail -5 data/live_collect/liq/MANIFEST.csv"))
print("today_lines", sh("wc -l < data/live_collect/liq/2026-10-28.jsonl"))
print(sh("pgrep -af liq_collector | grep -v pgrep"))
print(sh("tail -3 data/live_collect/liq/sessions.log"))

sec("LOGSHIP code sha")
print(sh("sha256sum deploy/ship_logs_drive.py src/audits/verify_log_ship.py"))
sec("FEES live"); print(sh("sha256sum deploy/fees.json"))
