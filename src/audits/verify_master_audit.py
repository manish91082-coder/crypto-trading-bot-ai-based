"""Independent verifier for the master audit (protocol logs/research_master_audit/MASTER_AUDIT_PROTOCOL_PREREGISTERED.md).

1. Part A: re-reads every locally sourced master-file number from its source and checks it.
2. Real funding for 300 random trades via its own loop (pandas masks, not searchsorted).
3. Own portfolio loop for G1 (f=0.5%, K=6) and G3-L1; final equity and maxDD must match to 1e-6.
4. Claims JSON vs CSVs, protocol/trades/funding SHAs.
"""
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parents[2]
A = R / "logs" / "research_master_audit"
LS = R / "logs" / "research_ladder_sessions"
PS = R / "logs" / "research_probe_scalein"
H = {"1h": 1.0, "4h": 4.0, "1D": 24.0}
res = []


def chk(name, ok, detail=""):
    res.append((name, "PASS" if ok else "FAIL", detail))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def within(x, lo, hi):
    return lo <= x <= hi


# ---------- Part A ----------
for f, pre in (("PLAN_NEXT_TARGET_R2_17_OCT_2026.md", "14714836"), ("RESEARCH_4H_TRADING_LONG_SHORT_17_OCT_2026.md", "0476ce8f"),
               ("FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md", "0531b065"), ("RESEARCH_AI_ARCHITECTURE_MULTI_TF_17_OCT_2026.md", "b7b18af2"),
               ("REPORT_LADDER_PATTERNS_SESSIONS_17_OCT_2026.md", "a6244819"), ("REPORT_PROBE_SCALEIN_LADDER_17_OCT_2026.md", "68cda951"),
               ("src/research/ladder_sessions.py", "6962deb9"), ("src/research/ladder_sessions_postlock.py", "ac7dd5bc"),
               ("src/audits/verify_ladder_sessions.py", "b17789ce"), ("src/research/probe_scalein.py", "52f49641"),
               ("src/audits/verify_probe_scalein.py", "263bea25"), ("deploy/crontab.txt", "1525e074"),
               ("logs/forward_ls_f4/CODE_CHANGES_AFTER_LOCK.md", "0831087b"),
               ("logs/research_ladder_sessions/LADDER_SESSIONS_PROTOCOL_PREREGISTERED.md", "e7ae067d"),
               ("logs/research_probe_scalein/PROBE_SCALEIN_PROTOCOL_PREREGISTERED.md", "90814d65")):
    s = sha(R / f)
    chk(f"A0 SHA {f}", s.startswith(pre), s[:8])

s1 = pd.read_csv(PS / "S1_summary.csv")


def m(tf, side, v, cost="base", col="mean_R"):
    return float(s1[(s1.tf == tf) & (s1.side == side) & (s1.variant == v) & (s1.cost == cost)][col].iloc[0])


for tf, side, val, nd in (("5m", "long", -0.12, 2), ("15m", "long", -0.05, 2), ("1h", "long", 0.03, 2), ("4h", "long", 0.106, 3),
                          ("4h", "short", 0.054, 3), ("1D", "long", 0.23, 2), ("1D", "short", 0.105, 3)):
    x = m(tf, side, "V0")
    chk(f"A3.4 V0 {tf} {side} = {val}", abs(round(x, nd) - val) < 1e-9 or abs(x - val) <= 0.5 * 10 ** -nd + 1e-9, f"{x:.4f}")
for tf, side, lo, hi in (("5m", "long", -0.08, -0.07), ("15m", "long", -0.04, -0.02), ("4h", "long", 0.076, 0.083),
                         ("4h", "short", 0.037, 0.045), ("1D", "long", 0.24, 0.28), ("1D", "short", 0.04, 0.05)):
    xs = [m(tf, side, v) for v in ("V1", "V2", "V3")]
    chk(f"A3.4 V1-V3 {tf} {side} in [{lo},{hi}]", all(within(round(x, 3), lo - 0.005, hi + 0.005) for x in xs), str([round(x, 3) for x in xs]))
for tf, side, a, b in (("5m", "long", -1.05, -0.68), ("15m", "long", -0.98, -0.62), ("1h", "long", -0.93, -0.58), ("4h", "long", -0.91, -0.57),
                       ("4h", "short", -0.96, -0.59), ("1D", "long", -0.92, -0.43), ("1D", "short", -0.89, -0.58)):
    x0, x2 = m(tf, side, "V0", col="p05_R"), m(tf, side, "V2", col="p05_R")
    chk(f"A3.4 p05 {tf} {side} {a}->{b}", abs(round(x0, 2) - a) < 1e-9 and abs(round(x2, 2) - b) < 1e-9, f"{x0:.3f}->{x2:.3f}")
n1d = int(s1[(s1.tf == "1D") & (s1.side == "long") & (s1.variant == "V0") & (s1.cost == "base")].signals.iloc[0])
chk("A3.4 1D long n = 153", n1d == 153, str(n1d))
s5 = m("5m", "long", "V0", col="sum_R") + m("5m", "short", "V0", col="sum_R")
chk("A3.4 5m total ~ -12,000 R", within(s5, -12500, -11500), f"{s5:.0f}")
p3 = m("1D", "long", "V0", col="mean_R_P3")
p3v3 = m("1D", "long", "V3", col="mean_R_P3")
chk("A3.4 1D long P3 V0 ~ -0.36, V3 ~ 0", abs(p3 + 0.36) < 0.01 and abs(p3v3) < 0.05, f"{p3:.3f}, V3 {p3v3:.3f}")

tfs = """| 5m   | 709458 |  0.1248 |  0.2858 | -0.0265 |      -0.0079 | 0.9472 |       0.6817 |"""
txt = (R / "research_notes" / "AI ब्रेन टाइमफ्रेम सिंक अंतिम सत्यापन" / "internal_tf_stats.md").read_text(encoding="utf-8")
rows = {}
for line in txt.split("## Per coin")[0].splitlines():
    p = [x.strip() for x in line.strip("|").split("|")]
    if len(p) == 8 and p[0] in ("5m", "15m", "1h", "4h", "1D", "1W", "1M"):
        rows[p[0]] = dict(bars=int(p[1]), body=float(p[2]), vr=float(p[6]), cr=float(p[7]))
for tf, body, cr, vr in (("5m", 0.12, 68, 0.947), ("15m", 0.22, 38, 0.950), ("1h", 0.43, 20, 0.940), ("4h", 0.86, 10, 0.995),
                         ("1D", 2.33, 3.7, 0.942), ("1W", 6.69, 1.3, 1.18), ("1M", 16.7, 0.5, 1.24)):
    r_ = rows[tf]
    nd_b = len(str(body).split(".")[1])
    nd_c = len(str(cr).split(".")[1]) if "." in str(cr) else 0
    nd_v = len(str(vr).split(".")[1])
    ok = round(r_["body"], nd_b) == body and round(r_["cr"] * 100, nd_c) == cr and round(r_["vr"], nd_v) == vr
    chk(f"A3.2 TF {tf} body/cost/VR", ok, f"{r_['body']}/{r_['cr'] * 100:.2f}/{r_['vr']}")
chk("A3.2 1W 353 bars, 1M 81 bars", rows["1W"]["bars"] == 353 and rows["1M"]["bars"] == 81)

a1 = pd.read_csv(LS / "A1_state_shares.csv")
a1 = a1[a1.tf.isin(["5m", "15m", "1h", "4h", "1D"])]
up = a1[a1.state == "UP"].share_count
dn = a1[a1.state == "DOWN"].share_count
ce = a1[a1.state.isin(["CONTRACTION", "EXPANSION"])].groupby("tf").share_count.sum()
chk("A3.3 UP 31-36% (5m..1D)", within(up.min(), 0.305, 0.365) and within(up.max(), 0.305, 0.365), f"{up.min():.3f}-{up.max():.3f}")
chk("A3.3 DOWN 29-31% (5m..1D)", within(dn.min(), 0.285, 0.315) and within(dn.max(), 0.285, 0.315), f"{dn.min():.3f}-{dn.max():.3f}")
chk("A3.3 rest ~35%", within(ce.min(), 0.32, 0.39) and within(ce.max(), 0.32, 0.39), f"{ce.min():.3f}-{ce.max():.3f}")
a2 = pd.read_csv(LS / "A2_ladder_runs.csv")
a2 = a2[a2.tf.isin(["5m", "15m", "1h", "4h", "1D"])]
chk("A3.3 ~50% ladders 1 step (5m..1D)", within(a2.steps_1.min(), 0.40, 0.55) and within(a2.steps_1.max(), 0.40, 0.55),
    f"{a2.steps_1.min():.3f}-{a2.steps_1.max():.3f}")
chk("A3.3 5+ steps 1-3% (5m..1D)", within(a2.steps_5plus.max(), 0, 0.035), f"{a2.steps_5plus.min():.3f}-{a2.steps_5plus.max():.3f}")
dn_mean = a2[a2.kind == "DOWN"].mean_steps.mean()
up_mean = a2[a2.kind == "UP"].mean_steps.mean()
chk("A3.3 down ladders shorter", dn_mean < up_mean, f"DOWN {dn_mean:.2f} < UP {up_mean:.2f}")
a3 = pd.read_csv(LS / "A3_retracements.csv")
a3 = a3[a3.tf.isin(["5m", "15m", "1h", "4h"])]
chk("A3.3 pullback median ~0.61, IQR ~45-77% (5m..4h)", within(a3["median"].median(), 0.58, 0.64) and
    within(a3.q25.min(), 0.42, 0.50) and within(a3.q75.max(), 0.74, 0.80),
    f"med {a3['median'].median():.3f}, q25 {a3.q25.min():.3f}-{a3.q25.max():.3f}, q75 {a3.q75.min():.3f}-{a3.q75.max():.3f}")
a5 = pd.read_csv(LS / "A5_double_top_bottom.csv")
a5b = pd.read_csv(LS / "A5b_unconditional_labels.csv").set_index("tf")
d = []
for x in a5[a5.tf.isin(["5m", "15m", "1h", "4h"])].itertuples():
    base = a5b.loc[x.tf, "p_LL_among_lows" if x.pattern == "double_top" else "p_HH_among_highs"]
    d.append((x.p_follow - base) * 100)
chk("A3.3 double top/bottom +3..9 pp (5m..4h)", within(min(d), 2.5, 9.5) and within(max(d), 2.5, 9.5), f"{min(d):.1f}..{max(d):.1f}")
a4 = pd.read_csv(LS / "A4_step_continuation.csv")
u4 = a4[(a4.tf == "4h") & (a4.kind == "UP") & (a4.k <= 3)].p_continue
chk("A3.3 4h UP continuation ~52% vs 48.7%", within(u4.min(), 0.515, 0.53) and abs(a5b.loc["4h", "p_HH_among_highs"] - 0.487) < 0.0005,
    f"{u4.min():.3f}-{u4.max():.3f}")
d4 = a4[(a4.tf == "4h") & (a4.kind == "DOWN") & (a4.k <= 2)].p_continue
chk("A3.3 [gap check] 4h DOWN continuation has NO edge vs LL base", d4.max() <= a5b.loc["4h", "p_LL_among_lows"] + 0.005,
    f"DOWN {d4.round(3).tolist()} vs base {a5b.loc['4h', 'p_LL_among_lows']:.3f} (master does not say this)")
b4 = pd.read_csv(LS / "B4_1h_swing_extremes_session.csv").set_index("sess")
chk("A3.3 US 39-43% of 1h swing turns", within(b4.loc["US", "swing_high"], 0.385, 0.435) and within(b4.loc["US", "swing_low"], 0.385, 0.435),
    f"{b4.loc['US', 'swing_high']:.3f}/{b4.loc['US', 'swing_low']:.3f}")
cm = json.loads((R / "logs" / "research_r2" / "fee_spread_check" / "commission_demo.json").read_text())
chk("A3.1 demo taker 0.04%, maker 0.02%", all(float(x["takerCommissionRate"]) == 0.0004 and float(x["makerCommissionRate"]) == 0.0002 for x in cm))
n = 40 / (0.03 + 0.01 + 0.00085)
chk("A3.1 40 USDT risk, 3% stop -> notional ~979", abs(n - 979) < 1, f"{n:.1f}")

# ---------- Part B: funding re-implementation ----------
t = pd.read_parquet(PS / "trades.parquet")
t = t[t.tf.isin(list(H))].reset_index(drop=True)
fund = {}
for c in t.coin.unique():
    f = pd.read_csv(R / "data" / "futures_um" / f"{c}_funding.csv")
    f["time"] = pd.to_datetime(f["time"])
    fund[c] = f
rng = np.random.default_rng(7)
sample = t.iloc[rng.choice(len(t), 300, replace=False)]
G = None
import importlib.util
spec = importlib.util.spec_from_file_location("mp", R / "src" / "research" / "master_audit_portfolio.py")
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)
tt, _, _ = mp.prepare()
mx = 0.0
for i, x in sample.iterrows():
    fr = fund[x.coin]
    bar = pd.Timedelta(hours=H[x.tf])
    end = x.entry_time + (x.exit_idx + 1) * bar
    tot = 0.0
    for u, px, k in ast.literal_eval(x.V0_fills):
        st = x.entry_time + k * bar
        rr = fr[(fr.time > st) & (fr.time < end)].funding_rate.sum()
        tot += u * rr * px * (1 if x.side == "long" else -1) / x.R_price
    mx = max(mx, abs(tot - tt.loc[i, "V0_fundR"]))
chk("B funding 300 trades match < 1e-9", mx < 1e-9, f"max diff {mx:.2e}")


# ---------- Part B: own portfolio loop ----------
def own(dd=False):
    first = {c: fund[c].time.min() for c in fund}
    d = tt[(tt.tf == "4h")].copy()
    d = d[[e >= first[c] for e, c in zip(d.entry_time, d.coin)]].sort_values(["entry_time", "coin"])
    E, pk, op, curve = 8000.0, 8000.0, [], [8000.0]
    for x in d.itertuples():
        for o in sorted([o for o in op if o["end"] <= x.entry_time], key=lambda o: o["end"]):
            E += o["pnl"]; pk = max(pk, E); curve.append(E); op.remove(o)
        if any(o["coin"] == x.coin for o in op) or len(op) >= 6:
            continue
        f = 0.0025 if (dd and E <= 0.9 * pk) else 0.005
        N = f * E / (x.R_price / x.entry_px + 0.0109)
        if sum(o["N"] for o in op) + N > 3 * E:
            continue
        if N < {"BTCUSDT": 50, "ETHUSDT": 20, "LINKUSDT": 20}.get(x.coin, 5) or (x.coin == "BTCUSDT" and N / x.entry_px < 0.001):
            continue
        op.append(dict(end=x.end_time, coin=x.coin, N=N, pnl=N * x.V0_real * x.R_price / x.entry_px))
    for o in sorted(op, key=lambda o: o["end"]):
        E += o["pnl"]; curve.append(E)
    c = np.array(curve)
    return E, float((1 - c / np.maximum.accumulate(c)).max())


g1 = pd.read_csv(A / "G1_risk_concentration.csv").set_index("run").loc["4h_f0.005_K6"]
g3 = pd.read_csv(A / "G3_loss_rules.csv").set_index("run").loc["L1_dd_derisk"]
for name, ref, dd in (("G1 f0.5% K6", g1, False), ("G3 L1", g3, True)):
    E, mdd = own(dd)
    chk(f"B portfolio {name} own loop", abs(E - ref.final) < 1e-6 and abs(mdd - ref.maxdd) < 1e-6, f"{E:.4f} vs {ref.final:.4f}; dd {mdd:.6f}")

cl = json.loads((A / "claims_master_audit.json").read_text())
chk("claims protocol SHA = locked", cl["protocol_sha"] == (A / "PROTOCOL_SHA256.txt").read_text().split()[0] == sha(A / "MASTER_AUDIT_PROTOCOL_PREREGISTERED.md"))
chk("claims trades SHA", cl["trades_sha"] == sha(PS / "trades.parquet"))
chk("claims funding SHAs", all(sha(R / "data" / "futures_um" / f"{c}_funding.csv") == h for c, h in cl["funding_sha"].items()))
chk("claims G1 = CSV", abs(cl["G1_f0.005_K6"]["final"] - g1.final) < 1e-9 and abs(cl["L1"]["final"] - g3.final) < 1e-9)

out = "\n".join(f"{s:4}  {n}  {d}" for n, s, d in res)
nf = sum(s == "FAIL" for _, s, _ in res)
out += f"\n\nTOTAL {len(res)} checks, FAIL {nf}\n"
(A / "verify_log.txt").write_text(out, encoding="utf-8")
print(out)
import sys as _sys                                   # 2026-10-19: exit code reflects FAILs (was always 0)
_sys.exit(1 if nf else 0)
