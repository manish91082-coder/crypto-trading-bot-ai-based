"""Assembles TF_ATLAS_RANKING_28_OCT_2026.md from report_template.md + generated tables, and writes claims.json
(every number in the report tied to an atlas row / phys / chance value). Formatting only."""
import json, math
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
D = PROJ / "logs/tf_atlas_2026_10_28"
rows = pd.read_csv(D / "atlas_rows.csv")
ph = pd.read_csv(D / "atlas_phys.csv")
ch = pd.read_csv(D / "atlas_chance.csv")
claims = json.loads((D / "claims_tables.json").read_text(encoding="utf-8"))
V = {}


def R(study, method, tf=None, side=None, universe=None):
    q = (rows.study == study) & (rows.method == method)
    if tf:
        q &= rows.tf == tf
    if side:
        q &= rows.side == side
    if universe:
        q &= rows.universe == universe
    x = rows[q]
    assert len(x) == 1, (study, method, tf, side, universe, len(x))
    return x.iloc[0]


def put(key, r, field, kind, idx=None):
    if idx is None:
        v = float(r[field])
    else:
        v = float(json.loads(r["x_oos"])[idx])
    if kind == "pct1s":
        t, mult, tol = f"{v * 100:+.1f}%", 100, 0.05
    elif kind == "pct0":
        t, mult, tol = f"{v * 100:.0f}%", 100, 0.5
    elif kind == "pct1":
        t, mult, tol = f"{v * 100:.1f}%", 100, 0.05
    elif kind == "pct3s":
        t, mult, tol = f"{v * 100:+.3f}%", 100, 0.0005
    elif kind == "auc":
        t, mult, tol = f"{v:.3f}", 1, 0.0005
    elif kind == "f2":
        t, mult, tol = f"{v:+.2f}", 1, 0.005
    elif kind == "f2u":
        t, mult, tol = f"{v:.2f}", 1, 0.005
    else:
        raise ValueError(kind)
    V[key] = t
    c = {"id": f"n:{key}", "row_id": r["row_id"], "num": v * mult, "mult": mult, "text": t, "tol": tol}
    if idx is None:
        c.update(kind="row", field=field)
    else:
        c.update(kind="rowx", idx=idx)
    claims.append(c)


def putp(key, tf, measure, mult, f_, tol):
    x = ph[(ph.tf == tf) & (ph.measure == measure)]
    assert len(x) == 1, (tf, measure)
    v = float(x.value.iloc[0])
    t = f_.format(v * mult)
    V[key] = t
    claims.append({"id": f"n:{key}", "kind": "phys", "tf": tf, "measure": measure, "num": v * mult, "mult": mult, "text": t, "tol": tol})


def putc(key, study, tf, field):
    x = ch[(ch.study == study) & (ch.tf == tf)]
    v = float(x[field].iloc[0])
    t = f"{v * 100:.0f}%"
    V[key] = t
    claims.append({"id": f"n:{key}", "kind": "chance", "study": study, "tf": tf, "field": field, "num": v * 100, "mult": 100, "text": t, "tol": 0.5})


def putn(key, query):
    n = len(rows.query(query)) if query else len(rows)
    t = f"{n:,}"
    V[key] = t
    claims.append({"id": f"n:{key}", "kind": "count", "query": query, "num": float(n), "text": t, "tol": 0})


# physics
for k, tf, h in (("p1m", "1s-1m", "1m"), ("p5", "5m", "5m"), ("p15", "15m", "15m"), ("p30", "30m", "30m"), ("p1h", "1h", "1h"),
                 ("p4h", "4h", "4h"), ("p1d", "1d", "1d"), ("p3d", "3d", "3d"), ("p1w", "1w", "7d"), ("p1M", "1M", "28d")):
    putp(k, tf, f"p* futures taker at horizon {h}", 100, "{:.1f}%", 0.05)
putp("er1m", "1s-1m", "E|r| at horizon 1m", 100, "{:.3f}%", 0.0005)
putp("vr20", "1s-1m", "variance ratio sec q=20 (rule follow)", 1, "{:.2f}", 0.005)
putp("leg1", "intraday-turn", "share of leg gone at confirmation (theta 0.01)", 100, "{:.0f}%", 0.5)
putp("lag1", "intraday-turn", "median confirmation lag minutes (theta 0.01)", 1, "{:.0f}", 0.5)
# counts
putn("nrows", "")
for t in ("E2", "E3", "E4", "E5"):
    putn(f"n{t}", f"tier == '{t}'")
# chance
putc("g15", "research_methods_bench", "15m", "share_oos_gross_pos")
putc("g1w", "research_btc_entry", "1w", "share_oos_gross_pos")
putc("g3d", "research_btc_entry", "3d", "share_oos_gross_pos")
putc("gev", "research_methods_bench", "event", "share_oos_gross_pos")
putc("np4pos", "research_nonprice", "4h", "share_oos_gross_pos")
putc("np1pos", "research_nonprice", "1h", "share_oos_gross_pos")
putc("np4med", "research_nonprice", "4h", "median_FCR092")
putc("np1med", "research_nonprice", "1h", "median_FCR092")
putc("micropos", "micro_momentum_2026", "1s-1m", "share_oos_gross_pos")
# rows
put("r24auc", R("strategy_1d_step24_1h", "R24 1h relative brain (skill)"), "auc", "auc")
r = R("strategy_1d_step24_1h", "R24 1h portfolio"); put("r24cagr", r, "net", "pct1s"); put("r24pre", r, None, "pct1s", 0)
put("r6auc", R("strategy_1d_step23_4h", "R6 4H relative brain (skill)"), "auc", "auc")
r = R("strategy_1d_step23_4h", "R6 4H portfolio"); put("r6cagr", r, "net", "pct1s"); put("r6pre", r, None, "pct1s", 0)
put("r5auc", R("strategy_1d_step19_largecap", "R5 in top-20 liquid coins (skill)"), "auc", "auc")
r = R("strategy_1d_step19_largecap", "R5 top-20 portfolio (80% invested)"); put("r5cagr", r, "net", "pct1s"); put("r5pre", r, None, "pct1s", 0)
r = R("research_n1_portfolio", "N1 multi-TF trend sleeves (4h-1D)"); put("n1pre", r, "net", "pct1s"); put("n1p3", r, None, "f2", 0); put("n1dev", r, "net_sel", "pct1s")
r = R("strategy_f7_risk", "F7 stops x1.5 + 30d cooldown (RS)"); put("f7cal", r, "calmar", "f2u"); put("f7dd", r, "maxdd", "pct0")
put("f7pre", r, None, "pct1s", 0); put("f7p3", r, None, "pct1s", 1); put("f7d", r, "net", "f2")
r = R("eco", "1D alone (LS_RS) inside ECO"); put("eco1dp3", r, "net", "pct1s"); put("eco1ddev", r, "net_sel", "pct1s")
r = R("eco", "ECO-W2: 1D LS_RS + N1, inverse-vol (live)"); put("ecop3", r, "net", "pct1s"); put("ecodev", r, "net_sel", "pct1s")
put("n1ecop3", R("eco", "N1 alone inside ECO"), "net", "pct1s")
put("b1auc", R("strategy_1d_step13_unseen", "B1 1-day relative (535 unseen coins)"), "auc", "auc")
put("pre5auc", R("strategy_1d_step22_pre2020", "frozen R5 brain on 2018-19 (skill)"), "auc", "auc")
put("exitauc", R("strategy_1d_step26_exit", "exit brain P(fall>5% in 24h)"), "auc", "auc")
put("mkt", R("strategy_1d_step17_18", "market brain (when to be out)"), "auc_lo", "auc")
TFX = "research_tf_edge_map"
r = R(TFX, "TFX EMAX", "1d", "long", "10 big coins"); put("ema1dmean", r, "gross", "pct1s"); put("ema1dmed", r, "gmed", "pct1s"); put("ema1dp3", r, None, "pct1s", 0)
put("ema8med", R(TFX, "TFX EMAX", "8h", "long", "10 big coins"), "gmed", "pct1s")
put("rsi8med", R(TFX, "TFX RSI", "8h", "long", "10 big coins"), "gmed", "pct1s")
put("rsi12med", R(TFX, "TFX RSI", "12h", "long", "10 big coins"), "gmed", "pct1s")
r = R(TFX, "TFX RSI", "1d", "long", "10 big coins"); put("rsi1dmed", r, "gmed", "pct1s"); put("rsi1dp3", r, None, "pct1s", 0)
put("rsi8altp3", R(TFX, "TFX RSI", "8h", "long", "liquid alts"), None, "pct1s", 0)
put("rsi12altp3", R(TFX, "TFX RSI", "12h", "long", "liquid alts"), None, "pct1s", 0)
put("bf1m", R("turn_detect_2026", "T3 P11_BollFade", "1s-1m"), "FCR092", "pct0")
put("mom5", R("research_root_cause", "simple MOM (10 coins)", "5m"), "hit", "pct1")
put("rev5", R("research_root_cause", "simple REV (10 coins)", "5m"), "hit", "pct1")
r = R("research_ladder_sessions", "double_bottom -> HH", "5m"); put("db5", r, "hit", "pct1"); put("db5b", r, "p_star", "pct1")
r = R("research_ladder_sessions", "double_top -> LL", "1d"); put("dt1d", r, "hit", "pct1"); put("dt1db", r, "p_star", "pct1")
r = R("research_sr_levels", "buy/sell at swing support (bounce)", "5m"); put("sr5", r, "hit", "pct1"); put("sr5b", r, "p_star", "pct1")
put("h2c", R("oracle_9m_2026", "10-day hand formula H2'-c V1-B"), "FCR092", "pct0")
put("sw4", R("research_swing_ai_phase2", "swing-rally AI 4h"), "auc", "auc")
put("sw8", R("research_swing_ai_phase2", "swing-rally AI 8h"), "auc", "auc")
put("t2best", R("turn_detect_2026", "T2 F15_eth_lead theta=0.005 f=0.25"), "auc", "auc")
put("s1", R("research_spot_sleeve", "spot timing S1"), "net", "f2")
put("dca", R("research_spot_dca", "spot DCA, averaging down, TP 10%, no stop"), "net", "pct1s")
put("vols", R("strategy_1d_step28_volsize", "volatility sizing"), "net", "f2")

inv = pd.read_csv(D / "study_inventory.csv")
for key, q, n in (("ninv", "all", len(inv)), ("ninc", "yes", int((inv.include == "yes").sum())), ("nexc", "no", int((inv.include == "no").sum()))):
    V[key] = f"{n}"
    claims.append({"id": f"n:{key}", "kind": "inventory", "which": q, "num": float(n), "text": f"{n}", "tol": 0})
nsrc = len(pd.read_csv(D / "atlas_sources.csv"))
V["nsrc"] = f"{nsrc}"
claims.append({"id": "n:nsrc", "kind": "sources", "num": float(nsrc), "text": f"{nsrc}", "tol": 0})
g = ch[ch.study.isin(["research_methods_bench", "research_btc_entry"])]
for key, field, fn, mult in (("glo", "share_oos_gross_pos", "min", 100), ("ghi", "share_oos_gross_pos", "max", 100),
                             ("bestlo", "best_FCR092", "min", 100), ("besthi", "best_FCR092", "max", 100)):
    v = float(getattr(g[field], fn)()) * mult
    V[key] = f"{v:,.0f}%"
    claims.append({"id": f"n:{key}", "kind": "chance_agg", "field": field, "fn": fn, "studies": ["research_methods_bench", "research_btc_entry"],
                   "num": v, "mult": mult, "text": f"{v:,.0f}%", "tol": 0.5})

CARDS = """| Timeframe | दिशा (Direction) | Entry | Exit / Risk / Selection | फ़ैसला |
|---|---|---|---|---|
| **1s–1m** | Seconds में momentum असली है (20 सेकंड पर variance ratio {vr20}), पर औसत चाल {er1m} fee से छोटी है। ज़रूरी सही दिशा {p1m}, यानी असंभव। सबसे अच्छा नियम: 1m Bollinger fade, fee-कवरेज {bf1m} | लागू नहीं | लागू नहीं | **बंद** |
| **5m** | ज़रूरी {p5}। Simple momentum / reversal सही: {mom5} / {rev5}। Double bottom के बाद higher high {db5}, जबकि आधार {db5b} है: असली, पर सिर्फ़ descriptive, पैसे का test नहीं | Swing support पर bounce {sr5}, control {sr5b}, यानी control से कम। Probe/scale-in सब घाटे में | — | **कोई formula नहीं** |
| **15m** | ज़रूरी {p15}। Bench grid में gross > 0 सिर्फ़ {g15} (सिक्का)। 10 दिनों वाला hand formula 272 नए दिनों पर fee-कवरेज {h2c} | S/R bounce control से कम | — | **कोई formula नहीं** |
| **30m** | ज़रूरी {p30}। कुछ साबित नहीं | — | — | **कोई formula नहीं** |
| **1h** | ज़रूरी {p1h}। Order flow / OI / order book संकेत असली हैं (NP1), पर grid का median fee-कवरेज {np1med} | — | Exit brain AUC {exitauc}: यह volatility पहचानता है, दिशा नहीं। पैसे में FAIL। **Selection:** R24 AUC {r24auc}, पर long-only 2018–19 में {r24pre} | **Selection में skill है, timing में नहीं** |
| **4h** | ज़रूरी {p4h}। N1 trend sleeves: 2018–19 में {n1pre}, पर पिछले साल Calmar {n1p3}। Non-price composites: {np4pos} configs gross-positive, median fee-कवरेज {np4med} | Maker / limit entry का फ़ायदा छोटा है (N3 X1 FAIL: adverse selection)। Swing-rally AI AUC {sw4} | A4 exit tuning noise है (PBO 0.84)। Profit lock (ECO-T4) FAIL। **Selection:** R6 AUC {r6auc}, long-only 2018–19 में {r6pre} | **मिला-जुला।** Trend हिस्से का फ़ैसला forward जाँच (Sleeve A) से |
| **8h / 12h** | **RSI < 30 long**: बड़े coins पर median trade 8h {rsi8med}, 12h {rsi12med}। Liquid alts पर पिछले साल भी positive: 8h {rsi8altp3}, 12h {rsi12altp3}। Trend (EMA / Donchian) long का औसत ऊँचा है, पर median negative (8h EMA {ema8med}), यानी कुछ बड़े trades पर टिका | Swing-rally AI 8h AUC {sw8} | — | **सबसे मज़बूत direction formula।** N1 sleeve B में live |
| **1d** | ज़रूरी {p1d}। RSI long median {rsi1dmed}, पर पिछले साल {rsi1dp3}। Double top के बाद lower low {dt1d}, आधार {dt1db} (n 58)। Spot S1 (BTC > SMA200) का Sharpe hold से सिर्फ़ {s1} ज़्यादा। DCA बिना stop: holdout {dca} | Perp पर long (E11) Calmar बढ़ाता है | **F7 RS:** Calmar {f7cal}, 2018–19 में {f7pre}, पिछले साल {f7p3}। Stops से ΔCalmar {f7d}। Vol sizing {vols} (FAIL)। "कब बाहर रहना है" वाले brains fail (market brain AUC निचली सीमा {mkt}) | **Project का सबसे मज़बूत timeframe।** ECO में live |
| **3d / 1w / 1M** | ज़रूरी {p3d} / {p1w} / {p1M}। BTC-entry grid में gross > 0: {g3d} / {g1w}। Weekly trend long का औसत कुछ बड़े trades पर टिका | — | — | **गणित आसान है, पर सबूत कम** |
| **Event bars / दिन के अंदर turns** | Renko / volume bars grid में gross > 0: {gev}। 1% turn की पुष्टि तक {leg1} चाल निकल चुकी होती है ({lag1} मिनट) | Early-turn features: AUC ≤ {t2best} | — | **बंद** |"""
CARDS = CARDS.format(**V)
tpl = (D / "report_template.md").read_text(encoding="utf-8")
for k, v in V.items():
    tpl = tpl.replace("{{" + k + "}}", v)
tpl = tpl.replace("{{PHYS}}", (D / "report_phys.md").read_text(encoding="utf-8"))
tpl = tpl.replace("{{TABLES}}", (D / "report_tables.md").read_text(encoding="utf-8"))
tpl = tpl.replace("{{CHANCE}}", (D / "report_chance.md").read_text(encoding="utf-8"))
tpl = tpl.replace("{{CARDS}}", CARDS)
vf = D / "verify_output.txt"
vline = "देखें `verify_output.txt`।"
if vf.exists():
    last = [l for l in vf.read_text(encoding="utf-8").splitlines() if l.startswith("TOTAL")]
    vline = (last[-1] if last else vline) + " (mutation test: `mutation_test_output.txt`)।"
tpl = tpl.replace("{{VERIFY}}", vline)
left = [s for s in tpl.split("{{")[1:]]
assert not left, f"unfilled placeholders: {[s.split('}}')[0] for s in left][:10]}"
(PROJ / "TF_ATLAS_RANKING_28_OCT_2026.md").write_text(tpl, encoding="utf-8")
(D / "claims.json").write_text(json.dumps(claims, ensure_ascii=False, indent=0), encoding="utf-8")
print("report written; claims", len(claims))
