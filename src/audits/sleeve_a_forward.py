"""PAPER-N1 sleeve A forward investigation (logs/paper_n1/SLEEVE_A_FORWARD_PROTOCOL_PREREGISTERED.md).
VM, daily: evaluates every ended forward window F1..F6 not yet evaluated (each once), runs the T3 fidelity test on it, writes
logs/paper_n1/sleeve_a_forward/F<k>.json, spot_F<k>.json and summary.json.
Usage: python src/audits/sleeve_a_forward.py [--ledger data/paper_n1/ledger.jsonl]"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
LOG = R_ / "logs" / "paper_n1"
OUT = LOG / "sleeve_a_forward"
PROTO = LOG / "SLEEVE_A_FORWARD_PROTOCOL_PREREGISTERED.md"
WTAB = LOG / "sleeve_a_check" / "all_windows.csv"
WTAB_SHA = "65d62d4ee8d1e56539b46cfbd3d50436a8918c93b35f2427ceac85b96bca03ed"
F0, W, K = pd.Timestamp("2026-10-24 04:00"), pd.Timedelta(hours=72), 6
CORE10 = json.loads((R_ / "deploy" / "paper_n1_config.json").read_text())["core10"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def get(url):
    for k in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "sleeve-a-forward"}), timeout=30).read())
        except Exception:                                    # noqa: BLE001 - network retry
            time.sleep(2 * (k + 1))
    raise RuntimeError(url)


def spot_opens(t0, t1):
    out = {}
    for c in CORE10:
        out[c] = {}
        for t in (t0, t1):
            ms = int(t.timestamp() * 1000)
            k = get(f"https://api.binance.com/api/v3/klines?symbol={c}&interval=4h&startTime={ms}&limit=1")
            assert k and int(k[0][0]) == ms, (c, t, k[:1])
            out[c][str(t)] = float(k[0][1])
    return out


def live_closes(ledger, t0, t1):
    out = []
    for line in Path(ledger).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        T = pd.Timestamp(r["T"])
        if not (t0 < T <= t1):
            continue
        for a in r["actions"]:
            if a["k"].startswith("A|") and a["a"] == "close":
                out.append(dict(k=a["k"], T=str(T), r=a["px"] / a["entry"] - 1))
    return out


def evaluate(k, ledger, wtab):
    t0, t1 = F0 + (k - 1) * W, F0 + k * W
    lc = live_closes(ledger, t0, t1)
    rec = dict(window=f"F{k}", start=str(t0), end=str(t1), ledger_sha256=sha(ledger), protocol_sha256=sha(PROTO), code_sha256=sha(__file__),
               n=len(lc), wins=sum(1 for c in lc if c["r"] > 0), closes=lc)
    if len(lc) < 20:
        rec.update(eligible=False, verdict="too few trades")
        return rec
    wr = rec["wins"] / len(lc)
    mr = sum(c["r"] for c in lc) / len(lc)
    sp = spot_opens(t0, t1)
    (OUT / f"spot_F{k}.json").write_text(json.dumps(dict(source="https://api.binance.com/api/v3/klines 4h open", data=sp), indent=1))
    M = sum(sp[c][str(t1)] / sp[c][str(t0)] - 1 for c in CORE10) / len(CORE10)
    el = wtab[(wtab.n >= 20) & wtab.M.notna()].copy()
    el["dist"] = (el.M - M).abs()
    m = max(30, math.ceil(0.2 * len(el)))
    comp = el.sort_values(["dist", "start"]).head(m)
    p_wr, p_ret = float((comp.win_rate <= wr).mean()), float((comp.mean_r <= mr).mean())
    fid = subprocess.run([sys.executable, str(R_ / "src" / "audits" / "verify_sleeve_a_check.py"), "fidelity", str(ledger), str(t0), str(t1)],
                         capture_output=True, text=True)
    (OUT / f"fidelity_F{k}.txt").write_text(fid.stdout + fid.stderr)
    suspect = fid.returncode != 0
    verdict = "records suspect" if suspect else ("consistent" if (p_wr >= 0.05 and p_ret >= 0.05) else "not consistent")
    rec.update(eligible=True, win_rate=wr, mean_r=mr, M_live=M, spot_sha256=sha(OUT / f"spot_F{k}.json"), n_eligible=len(el), n_comparable=m,
               comp_win_rate_median=float(comp.win_rate.median()), comp_mean_r_median=float(comp.mean_r.median()), p_wr=p_wr, p_ret=p_ret,
               fidelity_rc=fid.returncode, fidelity_tail=fid.stdout.strip().splitlines()[-3:], verdict=verdict)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="data/paper_n1/ledger.jsonl")
    a = ap.parse_args()
    assert sha(PROTO) == (LOG / "SLEEVE_A_FORWARD_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed"
    assert sha(WTAB) == WTAB_SHA, "backtest window table changed"
    ledger = R_ / a.ledger
    wtab = pd.read_csv(WTAB, parse_dates=["start"])
    OUT.mkdir(parents=True, exist_ok=True)
    lastT = max(pd.Timestamp(json.loads(l)["T"]) for l in ledger.read_text().splitlines() if l.strip())
    for k in range(1, K + 1):
        f = OUT / f"F{k}.json"
        if f.exists() or lastT < F0 + k * W:
            continue
        rec = evaluate(k, ledger, wtab)
        f.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
        print(f"F{k} evaluated: n {rec['n']} verdict {rec['verdict']} " + (f"p_wr {rec['p_wr']:.3f} p_ret {rec['p_ret']:.3f}" if rec.get("eligible") else ""))
    done = [json.loads((OUT / f"F{k}.json").read_text()) for k in range(1, K + 1) if (OUT / f"F{k}.json").exists()]
    elig = [d for d in done if d["eligible"]][:3]
    if len(elig) == 3:
        n_bad = sum(d["verdict"] != "consistent" for d in elig)
        susp = any(d["verdict"] == "records suspect" for d in elig)
        verdict = "confirmed inconsistent" if (n_bad >= 2 or susp) else "W1 was an extreme draw"
    elif len(done) == K:
        verdict = "insufficient"
    else:
        verdict = "pending"
    summ = dict(evaluated=[(d["window"], d["n"], d["verdict"]) for d in done], first3_eligible=[d["window"] for d in elig], verdict=verdict,
                protocol_sha256=sha(PROTO), files={d["window"]: sha(OUT / f"{d['window']}.json") for d in done})
    (OUT / "summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(f"sleeve A forward {pd.Timestamp.now('UTC')}: last ledger T {lastT}; {summ['evaluated']}; verdict {verdict}")


if __name__ == "__main__":
    main()
