"""Daily check of the live ECO ledger (VM). Usage: python verify_eco_live.py [root=data/eco]
L1 hash chain   L2 protocol / config SHA constant and == files on disk; every config SHA listed in CODE_CHANGES
L3 failed cycles listed (> 2 in 24 h = FAIL)   L4 hourly cadence: gaps > 90 min listed (FAIL if any in the last 24 h)
L5 reconcile: no mismatch in the last 24 h; plan mode: book == paper
L6 caps on targets: per-symbol |net| <= coin_cap * E, gross <= gross_cap * E   L7 producers: frozen cycles in the last 24 h listed
Amendment 2 §8: L8 last record not halted   L9 attribution identity   L10 caps on HELD positions (+ one band)
L11 every code SHA (orchestrator, core, exchange) listed in CODE_CHANGES. Reset records (mode "reset") are chained, not cycles."""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
root = Path(sys.argv[1]) if len(sys.argv) > 1 else R_ / "data" / "eco"
root = root if root.is_absolute() else R_ / root
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


A = [json.loads(l) for l in (root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
prev, chain = "GENESIS", True
for r in A:
    body = {k: v for k, v in r.items() if k != "line_sha256"}
    chain &= r["prev_sha256"] == prev and hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == r["line_sha256"]
    prev = r["line_sha256"]
L = [r for r in A if r.get("mode") != "reset"]                  # cycles
resets = [r for r in A if r.get("mode") == "reset"]
ok("L1", chain, f"{len(A)} records ({len(L)} cycles, {len(resets)} resets), hash chain intact")
cfg_f, proto = R_ / "deploy" / "eco_config.json", R_ / "logs" / "eco" / "ECO_PROTOCOL_PREREGISTERED.md"
notes = (R_ / "logs" / "eco" / "CODE_CHANGES_AFTER_LOCK.md").read_text(encoding="utf-8")
cfgs = {r["config_sha256"] for r in L}
listed = all(c[:12] in notes for c in cfgs)                 # every config ever used must be listed in CODE_CHANGES
ok("L2", L[-1]["config_sha256"] == sha(cfg_f) and listed and {r["protocol_sha256"] for r in L} == {sha(proto)},
   f"config now {sha(cfg_f)[:12]} == last cycle; configs used {sorted(c[:12] for c in cfgs)} all listed in CODE_CHANGES: {listed}; "
   f"protocol {sha(proto)[:12]} constant")
T = pd.to_datetime([r["T"] for r in L])
last24 = T >= T[-1] - pd.Timedelta(hours=24)
fails = [(r["T"], (r.get("error") or "")[-120:]) for r in L if not r.get("ok")]
f24 = sum(1 for r, m in zip(L, last24) if m and not r.get("ok"))
ok("L3", f24 <= 2, f"failed cycles: {len(fails)} total, {f24} in the last 24 h; last {fails[-2:]}")
gaps = [(str(a), str(b)) for a, b in zip(T[:-1], T[1:]) if b - a > pd.Timedelta(minutes=90)]
g24 = [g for g in gaps if pd.Timestamp(g[1]) >= T[-1] - pd.Timedelta(hours=24)]
ok("L4", not g24, f"hourly cadence; gaps > 90 min: {gaps[-5:]}")
mm = [(r["T"], r["reconcile_mismatch"]) for r, m in zip(L, last24) if m and r.get("ok") and r.get("reconcile_mismatch")]
ok("L5", not mm, f"reconcile mismatches in the last 24 h: {mm[:3]}")
cfg = json.loads(cfg_f.read_text())
viol = []
for r in L:
    if not r.get("ok") or "price" not in r:
        continue
    E, k = r["eco_equity"], r["k_m"]
    st = r.get("targets_net", {})
    net = {p: q * r["price"].get(p, 0.0) / k for p, q in st.items()}
    for p, v in net.items():
        if abs(v) > cfg["coin_cap"] * E * 1.0001:
            viol.append((r["T"], p, round(v, 2)))
    if sum(abs(v) for v in net.values()) > cfg["gross_cap"] * E * 1.0001:
        viol.append((r["T"], "gross"))
ok("L6", not viol, f"targets within caps (coin {cfg['coin_cap']}, gross {cfg['gross_cap']}): violations {viol[:3]}")
fr = [(r["T"], r["frozen_strategies"]) for r, m in zip(L, last24) if m and r.get("ok") and r.get("frozen_strategies")]
ok("L7", len(fr) <= 6, f"cycles with a frozen producer in the last 24 h: {len(fr)} {fr[-2:]}")
# ---- amendment 2 §8
lastrec = A[-1]
ok("L8", not lastrec.get("halted"), f"last record {lastrec['T']} ({lastrec.get('mode')}): halted = {lastrec.get('halted')}")
idv = [(r["T"], round(sum(r["attribution"].values()) - r["acct_pnl"], 9)) for r in L
       if r.get("ok") and "attribution" in r and r.get("acct_pnl") is not None and abs(sum(r["attribution"].values()) - r["acct_pnl"]) > 1e-6]
n_id = sum(1 for r in L if r.get("ok") and "attribution" in r and r.get("acct_pnl") is not None)
ok("L9", not idv, f"attribution identity (sum of strategies == account P&L) on {n_id} cycles: violations {idv[:3]}")
hv, n_h = [], 0
for r in L:
    if not r.get("ok") or "held_net" not in r or "price" not in r:
        continue
    n_h += 1
    E, k = r["eco_equity"], r["k_m"]
    band = cfg["band_frac"] * E                                 # one band, in eco units
    px = dict(r["price"])
    hn = {p: q * px[p] / k for p, q in r["held_net"].items() if p in px}
    for p, v in hn.items():
        if abs(v) > cfg["coin_cap"] * E * 1.0001 + band:
            hv.append((r["T"], p, round(v, 2)))
    if sum(abs(v) for v in hn.values()) > cfg["gross_cap"] * E * 1.0001 + band * max(1, len(hn)):
        hv.append((r["T"], "gross"))
ok("L10", not hv, f"held positions within caps + band on {n_h} cycles (records with held_net): violations {hv[:3]}")
codes = {(k_, r[k_]) for r in A for k_ in ("code_sha256", "core_sha256", "exchange_sha256") if r.get(k_)}
unl = sorted({(k_, c[:12]) for k_, c in codes if c[:12] not in notes})
ok("L11", not unl, f"code SHAs used: {sorted({c[:12] for _, c in codes})}; not listed in CODE_CHANGES: {unl}")
okc = [r for r in L if r.get("ok") and "eco_equity" in r]
if okc:
    last = okc[-1]
    print(f"[INFO] last ok cycle {last['T']} mode {last['mode']}: eco equity {last['eco_equity']:.2f} (start 10000), weights {last.get('a')}, "
          f"symbols {last.get('n_symbols')}, gross {last.get('gross_eco', 0):.0f} USDT eco, orders this cycle {len(last.get('orders', []))}, "
          f"halted {last.get('halted')}, price fallbacks {last.get('px_missing', [])}, delisting {last.get('delisting', [])}")
    if last.get("stops"):
        print(f"[INFO] exchange stops (plan: would-be orders): open {last['stops']['n_open']} (guards {last['stops']['n_guard']}, 1D-short {last['stops']['n_component']})")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
