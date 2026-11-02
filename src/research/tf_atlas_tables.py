"""Builds the markdown tables of TF_ATLAS_RANKING_28_OCT_2026.md from the atlas files, and the claims for every
number printed in them (logs/tf_atlas_2026_10_28/claims_tables.json). No new numbers: formatting only."""
import json, math
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
D = PROJ / "logs/tf_atlas_2026_10_28"
rk = pd.read_csv(D / "atlas_ranked.csv")
ph = pd.read_csv(D / "atlas_phys.csv")
ch = pd.read_csv(D / "atlas_chance.csv")
CLAIMS = []
TFS = ["1s-1m", "5m", "15m", "30m", "1h", "4h", "8h", "12h", "1d", "3d", "1w", "1M", "event", "intraday-turn"]
TF_HI = {"1s-1m": "1 सेकंड – 1 मिनट", "5m": "5 मिनट", "15m": "15 मिनट", "30m": "30 मिनट", "1h": "1 घंटा", "4h": "4 घंटे",
         "8h": "8 घंटे", "12h": "12 घंटे", "1d": "1 दिन", "3d": "3 दिन", "1w": "1 हफ़्ता", "1M": "1 महीना",
         "event": "बिना घड़ी वाले bars (Renko / volume / dollar / imbalance)", "intraday-turn": "दिन के अंदर के turns (आकार θ से, bar से नहीं)"}
COMP_HI = {"DIR": "दिशा (Direction)", "ENTRY": "Entry", "EXIT": "Exit", "SELECT": "Coin चुनना (Selection)", "RISK": "Risk / drawdown"}
NA = lambda v: v is None or (isinstance(v, float) and math.isnan(v))


def claim_row(row, field, mult, text, tol):
    CLAIMS.append({"id": f"{row.row_id}:{field}:{len(CLAIMS)}", "kind": "row", "row_id": row.row_id, "field": field,
                   "num": float(row[field]) * mult, "mult": mult, "text": text, "tol": tol})


def fmt(row, field, kind):
    v = row[field]
    if NA(v):
        return "—"
    if kind == "pct0":   # ratio -> percent, 0 dp
        t = f"{v * 100:.0f}%"; claim_row(row, field, 100, t, 0.5); return t
    if kind == "pct1":
        t = f"{v * 100:.1f}%"; claim_row(row, field, 100, t, 0.05); return t
    if kind == "pct3":
        t = f"{v * 100:+.3f}%"; claim_row(row, field, 100, t, 0.0005); return t
    if kind == "auc":
        t = f"{v:.3f}"; claim_row(row, field, 1, t, 0.0005); return t
    if kind == "f2":
        t = f"{v:+.2f}"; claim_row(row, field, 1, t, 0.005); return t
    if kind == "int":
        t = f"{int(round(v)):,}"; claim_row(row, field, 1, t, 0.5); return t
    raise ValueError(kind)


def xoos(row, unit="frac"):
    xs = json.loads(row["x_oos"])
    if not xs:
        return "—"
    if unit == "R":
        return ", ".join(f"{x:+.2f} R" for x in xs)
    if "Calmar" in str(row["note"]) and "x1 = P3 Calmar" in str(row["note"]):
        return ", ".join(f"{x:+.2f} (Calmar)" for x in xs)
    return ", ".join(f"{x * 100:+.1f}%" for x in xs)


def grid(row):
    c = ch[(ch.study == row["study"]) & (ch.tf == row["tf"])]
    if len(c) != 1 or NA(c.share_oos_gross_pos.iloc[0]):
        return "—"
    return f"{c.share_oos_gross_pos.iloc[0] * 100:.0f}% of {int(c.configs.iloc[0])}"


def yn(v):
    return "—" if NA(v) else ("हाँ" if str(v) == "True" else "नहीं")


def table(g, mt):
    out = []
    if mt in ("TRADE", "AGG"):
        out.append("| # | Tier | तरीका | study | side / coins | n | fee-कवरेज (gross ÷ fee) | net / trade | median trade (gross) | आगे की जाँच (P3 / OOS) | random से बेहतर? | study का फ़ैसला | उसी grid में gross > 0 |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in g.iterrows():
            fc = fmt(r, "FCR092", "pct0") if (r["unit"] == "frac" and not NA(r["FCR092"])) else (fmt(r, "FCR", "pct0") + " (R)" if not NA(r["FCR"]) else "—")
            net = fmt(r, "net", "pct3") if r["unit"] == "frac" else (fmt(r, "net", "f2") + " R" if not NA(r["net"]) else "—")
            gm = fmt(r, "gmed", "pct3") if not NA(r.get("gmed")) else "—"
            out.append(f"| {r['rank']} | {r['tier']} | {r['method']} | {r['study']} | {r['side'] if not NA(r['side']) else ''} {r['universe']} | "
                       f"{fmt(r, 'n', 'int')} | {fc} | {net} | {gm} | {xoos(r, r['unit'])} | {yn(r['ctrl'])} | {yn(r['verdict_pass'])} | {grid(r)} |")
    elif mt == "SKILL":
        out.append("| # | Tier | तरीका | study | AUC (असर) | AUC निचली सीमा | असर असली? | study का फ़ैसला |")
        out.append("|---|---|---|---|---|---|---|---|")
        for _, r in g.iterrows():
            out.append(f"| {r['rank']} | {r['tier']} | {r['method']} | {r['study']} | {fmt(r, 'auc', 'auc')} | {fmt(r, 'auc_lo', 'auc')} | {yn(r['skill_sig'])} | {yn(r['verdict_pass'])} |")
    elif mt == "ACC":
        out.append("| # | Tier | तरीका | study | सही % | ज़रूरी / आधार % | ज़रूरी बढ़त का कितना % मिला | n | असर असली? |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for _, r in g.iterrows():
            out.append(f"| {r['rank']} | {r['tier']} | {r['method']} | {r['study']} | {fmt(r, 'hit', 'pct1')} | {fmt(r, 'p_star', 'pct1')} | "
                       f"{fmt(r, 'ACC_COVER', 'pct0')} | {fmt(r, 'n', 'int')} | {yn(r['ctrl'])} |")
    elif mt == "PORT":
        out.append("| # | Tier | तरीका | study | OOS नतीजा | Calmar | max DD | चुनाव वाले data पर | और अनदेखे दौर | random/control से बेहतर? | study का फ़ैसला |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in g.iterrows():
            modifier = "modifier" in str(r["note"]) or "vs BTC hold" in str(r["note"]) or "net = Calmar" in str(r["note"])
            netf = fmt(r, "net", "f2") + (" (ΔCalmar)" if "Calmar change" in str(r["note"]) else (" (ΔSharpe vs hold)" if "Sharpe" in str(r["note"]) else " (Calmar)")) if modifier else fmt(r, "net", "pct1")
            sel = (fmt(r, "net_sel", "f2") if modifier else fmt(r, "net_sel", "pct1"))
            out.append(f"| {r['rank']} | {r['tier']} | {r['method']} | {r['study']} | {netf} | {fmt(r, 'calmar', 'f2')} | {fmt(r, 'maxdd', 'pct0')} | {sel} | {xoos(r)} | {yn(r['ctrl'])} | {yn(r['verdict_pass'])} |")
    else:  # DESC
        out.append("| # | Tier | तरीका | study | नोट |")
        out.append("|---|---|---|---|---|")
        for _, r in g.iterrows():
            out.append(f"| {r['rank']} | {r['tier']} | {r['method']} | {r['study']} | {r['note'] if not NA(r['note']) else ''} |")
    return out


MT_HI = {"TRADE": "trade नियम", "AGG": "exit की तुलना (औसत)", "SKILL": "skill (AUC / IC)", "ACC": "सही दिशा %", "PORT": "portfolio", "DESC": "विवरण"}
lines = []
for tf in TFS:
    x = rk[rk.tf == tf]
    if not len(x):
        continue
    lines.append(f"\n### {tf} — {TF_HI[tf]}\n")
    tiers = x.tier.value_counts().to_dict()
    lines.append("कुल rows: " + f"{len(x):,}" + "; tiers: " + ", ".join(f"{k} {tiers.get(k, 0)}" for k in ("E1", "E2", "E3", "E4", "E5")) + "\n")
    CLAIMS.append({"id": f"count:{tf}", "kind": "count", "query": f"tf == '{tf}'", "num": float(len(x)), "text": f"कुल rows: {len(x):,}", "tol": 0})
    for comp in ("DIR", "ENTRY", "EXIT", "SELECT", "RISK"):
        y = x[x.component == comp]
        if not len(y):
            continue
        lines.append(f"\n**{COMP_HI[comp]}**\n")
        for mt in ("TRADE", "ACC", "SKILL", "PORT", "AGG", "DESC"):
            z = y[y.mtype == mt].sort_values("rank")
            if not len(z):
                continue
            k = 5 if mt in ("TRADE",) else (6 if mt in ("PORT", "AGG") else 4)
            lines.append(f"\n*{MT_HI[mt]}*: {len(z):,} rows; ऊपर के {min(k, len(z))}:\n")
            lines += table(z.head(k), mt)
(D / "report_tables.md").write_text("\n".join(lines), encoding="utf-8")

# physics ladder
P = []
P.append("| Timeframe | BTC की औसत चाल | ज़रूरी सही दिशा (taker) | ज़रूरी सही दिशा (maker) | random entry net (10 coins, taker) | अगली candle भी green? (Jan 2026) | variance ratio (1 = random, < 1 = पलटता, > 1 = चलता रहता) | पुष्ट swing follow करने पर औसत (ATR, fee से पहले): rally / decline |")
P.append("|---|---|---|---|---|---|---|---|")


def pv(tf, measure, mult=1.0, fmt_="{:.1f}%"):
    r = ph[(ph.tf == tf) & (ph.measure == measure)]
    if len(r) != 1:
        return "—"
    v = float(r.value.iloc[0]) * mult
    t = fmt_.format(v)
    CLAIMS.append({"id": f"phys:{tf}:{measure}", "kind": "phys", "tf": tf, "measure": measure, "num": float(r.value.iloc[0]) * mult, "mult": mult, "text": t, "tol": 0.051 if "%" in fmt_ else 0.0051})
    return t


HZ = {"1s-1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d", "3d": "3d", "1w": "7d", "1M": "28d"}
VRQ = {"5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "240", "8h": "480", "1d": "1440"}
for tf in ("1s-1m", "5m", "15m", "30m", "1h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"):
    h = HZ.get(tf)
    er = pv(tf, f"E|r| at horizon {h}", 100, "{:.3f}%") if h else "—"
    pt = pv(tf, f"p* futures taker at horizon {h}", 100) if h else "—"
    pm = pv(tf, f"p* maker at horizon {h}", 100) if h else "—"
    rn = pv(tf, "random entry net per trade (10 coins, taker)", 100, "{:+.3f}%")
    gg = pv(tf, "P(green|green) Jan 2026", 100)
    vr = pv(tf, f"variance ratio min q={VRQ[tf]} (rule follow)", 1, "{:.2f}") if tf in VRQ else ("sec q=20: " + pv(tf, "variance ratio sec q=20 (rule follow)", 1, "{:.2f}") if tf == "1s-1m" else "—")
    fr = pv(tf, "follow confirmed Rally: mean realized ATR (before cost)", 1, "{:+.2f}")
    fd = pv(tf, "follow confirmed Decline: mean realized ATR (before cost)", 1, "{:+.2f}")
    P.append(f"| {tf} | {er} | {pt} | {pm} | {rn} | {gg} | {vr} | {fr} / {fd} |")
(D / "report_phys.md").write_text("\n".join(P), encoding="utf-8")

# chance table
Q = ["| study | timeframe | configs (OOS) | net > 0 वाले | **gross > 0 वाले** (50% = सिक्का) | सबसे अच्छा fee-कवरेज | median fee-कवरेज |", "|---|---|---|---|---|---|---|"]
for _, c in ch.iterrows():
    def cc(field, mult, f_):
        v = c[field]
        if NA(v):
            return "—"
        t = f_.format(v * mult)
        CLAIMS.append({"id": f"chance:{c.study}:{c.tf}:{field}", "kind": "chance", "study": c.study, "tf": c.tf, "field": field, "num": float(v) * mult, "mult": mult, "text": t, "tol": 0.5 if f_.endswith("%}") or "%" in f_ else 0.5})
        return t
    Q.append(f"| {c.study} | {c.tf} | {int(c.configs)} | {cc('share_oos_net_pos', 100, '{:.0f}%')} | {cc('share_oos_gross_pos', 100, '{:.0f}%')} | {cc('best_FCR092', 100, '{:.0f}%')} | {cc('median_FCR092', 100, '{:.0f}%')} |")
(D / "report_chance.md").write_text("\n".join(Q), encoding="utf-8")
(D / "claims_tables.json").write_text(json.dumps(CLAIMS, ensure_ascii=False, indent=0), encoding="utf-8")
print("tables lines", len(lines), "claims", len(CLAIMS))
