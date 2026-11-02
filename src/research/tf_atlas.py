"""ATLAS-TF-2026-10-28 builder (protocol logs/tf_atlas_2026_10_28/ATLAS_PROTOCOL_PREREGISTERED.md).

Reads ONLY stored result files of locked studies. Re-runs nothing. Every raw value of every row carries a locator
(file + csv key/column or json path) so the verifier can re-read it independently.
Outputs (logs/tf_atlas_2026_10_28/): atlas_rows.csv, atlas_ranked.csv, atlas_chance.csv, atlas_phys.csv, atlas_sources.csv
"""
import hashlib, json, math, re
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
L = PROJ / "logs"
OUT = L / "tf_atlas_2026_10_28"
FEE092 = 0.00092
ROWS, PHYS, USED = [], [], set()

# ---------------------------------------------------------------- locators
_csv_cache, _json_cache = {}, {}


def _csv(f):
    if f not in _csv_cache:
        _csv_cache[f] = pd.read_csv(PROJ / f, dtype=str, keep_default_na=False)
        USED.add(f)
    return _csv_cache[f]


def _json(f):
    if f not in _json_cache:
        _json_cache[f] = json.loads((PROJ / f).read_text(encoding="utf-8"))
        USED.add(f)
    return _json_cache[f]


def T(f, key, col):
    """Row of a whitespace-separated text table whose header line contains `col`."""
    return {"f": f, "txt": key, "col": col, "scale": 1.0}


def _txt(f):
    if f not in _csv_cache:
        lines = (PROJ / f).read_text(encoding="utf-8").splitlines()
        hi = next(i for i, l in enumerate(lines) if l.split()[:2] == ["tf", "direction"])
        hdr = lines[hi].split()
        rows = [l.split() for l in lines[hi + 1:] if len(l.split()) == len(hdr)]
        _csv_cache[f] = pd.DataFrame(rows, columns=hdr)
        USED.add(f)
    return _csv_cache[f]


def C(f, key, col, scale=1.0):
    return {"f": f, "key": key, "col": col, "scale": scale}


def J(f, path, scale=1.0):
    return {"f": f, "path": path, "scale": scale}


def K(value, why):
    return {"const": value, "why": why}


def CALC(op, *args, k=None):
    """Derived from other locators only: sub(a,b)=a-b; lin(a,b)=a+k*b; add(a)=a+k; flip(a)=max(a,1-a);
    efflo(a,lo,hi)= lo if a>=0.5 else 1-hi."""
    return {"calc": op, "args": list(args), "k": k}


def resolve(loc):
    if "const" in loc:
        return loc["const"]
    if "calc" in loc:
        a = [resolve(x) for x in loc["args"]]
        if any(v is None for v in a):
            return None
        a = [float(v) for v in a]
        op, k = loc["calc"], loc["k"]
        return {"sub": lambda: a[0] - a[1], "lin": lambda: a[0] + k * a[1], "add": lambda: a[0] + k,
                "flip": lambda: max(a[0], 1 - a[0]), "efflo": lambda: a[1] if a[0] >= 0.5 else 1 - a[2]}[op]()
    if "path" in loc:
        o = _json(loc["f"])
        for p in loc["path"]:
            o = o[p]
    else:
        d = _txt(loc["f"]) if "txt" in loc else _csv(loc["f"])
        if "txt" in loc:
            loc = {**loc, "key": loc["txt"]}
        m = np.ones(len(d), bool)
        for k, v in loc["key"].items():
            m &= d[k].values == str(v)
        if m.sum() != 1:
            raise ValueError(f"locator matched {m.sum()} rows: {loc}")
        o = d.loc[m, loc["col"]].iloc[0]
    if isinstance(o, (bool, np.bool_)) or o in ("True", "False", "true", "false"):
        return str(o).lower() == "true"
    if isinstance(o, str):
        if o == "":
            return None
        try:
            o = float(o)
        except ValueError:
            return o
    if isinstance(o, (int, float)) and loc.get("scale", 1.0) != 1.0:
        return float(o) * loc["scale"]
    return o


# ---------------------------------------------------------------- rules (shared definition with the verifier, re-coded there)
def apply_rule(rule, vals):
    if rule is None:
        return None
    v = vals.get(rule["field"])
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    op, thr = rule["op"], rule.get("thr")
    if op == ">":
        return bool(v > thr)
    if op == "<":
        return bool(v < thr)
    if op == "==":
        return bool(v == thr)
    if op == "in":
        return bool(v in thr)
    if op == "startswith":
        return bool(str(v).startswith(thr))
    if op == "true":
        return bool(v is True)
    raise ValueError(op)


def num(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


def derive(r, vals):
    net, cost = num(vals.get("net")), num(vals.get("cost"))
    gross = num(vals.get("gross"))
    if gross is None and net is not None and cost is not None:
        gross = net + cost
    r["gross"], r["net"], r["cost"] = gross, net, cost
    r["FCR"] = gross / cost if (gross is not None and cost) else None
    r["FCR092"] = gross / FEE092 if (gross is not None and r["unit"] == "frac") else None
    hit, ps = num(vals.get("hit")), num(vals.get("p_star"))
    r["hit"], r["p_star"] = hit, ps
    r["ACC_COVER"] = (hit - 0.5) / (ps - 0.5) if (hit is not None and ps is not None and r["acc_sym"] and ps != 0.5) else None
    for k in ("ci_lo", "n", "net_sel", "mblo", "auc", "auc_lo", "calmar", "cagr", "maxdd", "dcagr", "gmed"):
        r[k] = num(vals.get(k)) if not isinstance(vals.get(k), str) else None
    xs = [num(vals.get(k)) for k in ("x1", "x2", "x3")]
    xs = [x for x in xs if x is not None]
    r["x_oos"] = json.dumps(xs)
    r["ctrl"] = apply_rule(r["_ctrl"], vals)
    r["skill_sig"] = apply_rule(r["_skill"], vals)
    r["verdict_pass"] = apply_rule(r["_verdict"], vals)
    r["tier"] = tier(r, xs)


def tier(r, xs):
    net, role = r["net"], r["role"]
    oos_pos = net is not None and net > 0 and role == "OOS"
    if (r["verdict_pass"] is True and oos_pos and r["ci_lo"] is not None and r["ci_lo"] > 0
            and r["ctrl"] is True and all(x > 0 for x in xs)):
        return "E1"
    if oos_pos or (role == "UNFIT" and net is not None and net > 0 and r["mblo"] is not None and r["mblo"] > 0):
        return "E2"
    if r["skill_sig"] is True or r["ctrl"] is True:
        return "E3"
    if (r["net_sel"] is not None and r["net_sel"] > 0) or (role in ("SEL", "UNFIT") and net is not None and net > 0):
        return "E4"
    return "E5"


TF_NORM = {"1D": "1d", "1W": "1w", "1M": "1M", "1m": "1s-1m"}


def add(study, tf, comp, mtype, method, role, locs, *, side="", universe="BTC", unit="frac", note="",
        ctrl=None, skill=None, verdict=None, acc_sym=False, score=None):
    tf = TF_NORM.get(tf, tf)
    vals = {k: resolve(v) for k, v in locs.items()}
    r = dict(study=study, tf=tf, component=comp, mtype=mtype, method=method, side=side, universe=universe,
             role=role, unit=unit, note=note, acc_sym=acc_sym, _ctrl=ctrl, _skill=skill, _verdict=verdict)
    derive(r, vals)
    r["raw"] = json.dumps({k: (v if not isinstance(v, (np.floating,)) else float(v)) for k, v in vals.items()}, default=str)
    r["loc"] = json.dumps(locs)
    r["rules"] = json.dumps({"ctrl": ctrl, "skill": skill, "verdict": verdict})
    for k in ("_ctrl", "_skill", "_verdict"):
        r.pop(k)
    ROWS.append(r)


def phys(tf, measure, value_loc, source_note):
    tf = {"1D": "1d", "1W": "1w", "1m": "1s-1m"}.get(tf, tf)
    PHYS.append(dict(tf=tf, measure=measure, value=resolve(value_loc), loc=json.dumps(value_loc), note=source_note,
                     study=value_loc["f"].split("/")[1]))


# ---------------------------------------------------------------- adapters
def a_tfx():
    f, fm = "logs/research_tf_edge_map/TFX_cells.csv", "logs/research_tf_edge_map/S1_S4_cells_monthblock.csv"
    d, m = _csv(f), _csv(fm)
    mk = set(zip(m.uni, m.tf, m.family, m.side))
    for _, x in d.iterrows():
        key = {"uni": x.uni, "tf": x.tf, "family": x.family, "side": x.side}
        if (x.uni, x.tf, x.family, x.side) not in mk or x.gross_mean == "":
            continue
        locs = {"gross": C(f, key, "gross_mean"), "gmed": C(f, key, "gross_median"), "net": C(f, key, "net_taker_dev"), "n": C(f, key, "n_dev"),
                "cost": K(0.00108, "TFX protocol: perp taker round trip 0.108%"),
                "ci_lo": C(f, key, "net_taker_ci_lo"), "mblo": C(fm, key, "net_taker_mlo"),
                "exlo": C(fm, key, "excess_mlo")}
        if x.net_taker_P3 != "":
            locs["x1"] = C(f, key, "net_taker_P3")
        add("research_tf_edge_map", x.tf, "DIR", "TRADE", f"TFX {x.family}", "UNFIT", locs, side=x.side,
            universe={"U1": "10 big coins", "U2": "liquid alts"}[x.uni], ctrl={"field": "exlo", "op": ">", "thr": 0},
            note="dev 2020-01..2025-09 unfitted grid; x1 = P3 net; ctrl = month-block excess vs random CI-low > 0")


def a_bench():
    for b in ("batch1", "batch2"):
        f, g = f"logs/research_methods_bench/{b}_ranking.csv", f"logs/research_methods_bench/{b}_gates_all.csv"
        d = _csv(f)
        for _, x in d.iterrows():
            mt = re.search(r"_(15m|1h|4h)$", x.cfg)
            tf = mt.group(1) if mt else "event"
            key = {"cfg": x.cfg, "exit": x.exit}
            locs = {"net": C(f, key, "H_mean"), "n": C(f, key, "H_n"), "ci_lo": C(f, key, "H_ci_lo"),
                    "cost": K(FEE092, "fees.json futures taker round trip (bench primary cost; funding inside net)"),
                    "net_sel": C(f, key, "D_mean"), "x1": C(g, key, "m25"), "x2": C(g, key, "m26"),
                    "g3": C(g, key, "G3"), "edge": C(g, key, "edge")}
            add("research_methods_bench", tf, "DIR", "TRADE", f"{b} {x.cfg} {x.exit}", "OOS", locs,
                ctrl={"field": "g3", "op": "true"}, verdict={"field": "edge", "op": "true"},
                note="H = 2025-01..2026-09 holdout; x1/x2 = 2025 / 2026 means; G3 computed only for the top 20")


BTCE_TF = {"F2": None, "F3": None}


def btce_tf(cfg):
    m = re.search(r"_(1h|4h|24h|72h|7d|5m)_", cfg + "_")
    tok = {"12": "1h", "48": "4h", "288": "1d", "2016": "1w"}
    if cfg.startswith(("F2", "F3", "F6", "F8")) and m:
        return {"1h": "1h", "4h": "4h", "24h": "1d", "72h": "3d", "7d": "1w", "5m": "5m"}[m.group(1)]
    if cfg.startswith("F4") or cfg.startswith("F5"):
        n = re.search(r"_(12|48|288|2016)(_|$)", cfg).group(1)
        return tok[n]
    return {"F7": "1d", "F9": "1h", "F11": "8h", "F12": "30m"}.get(cfg.split("_")[0])


def a_btcentry():
    f, jf = "logs/research_btc_entry/all_configs_D_V.csv", "logs/research_btc_entry/BTC_ENTRY_RESULTS.json"
    d = _csv(f)
    fin = {(x["cfg"], x["set"]): i for i, x in enumerate(_json(jf)["finals"])}
    for _, x in d[d.cost == "fut"].iterrows():
        if x.cfg.split("_")[0] in ("F0", "F1"):
            continue
        tf = btce_tf(x.cfg)
        key = {"cfg": x.cfg, "set": x.set, "cost": "fut"}
        if (x.cfg, x.set) in fin:
            i = fin[(x.cfg, x.set)]
            locs = {"net": J(jf, ["finals", i, "H_mean"]), "n": J(jf, ["finals", i, "H_n"]),
                    "ci_lo": J(jf, ["finals", i, "H_ci95", 0]), "cost": K(FEE092, "fees.json futures taker"),
                    "net_sel": C(f, key, "D_mean"), "x1": J(jf, ["finals", i, "H_mean_2025"]),
                    "x2": J(jf, ["finals", i, "H_mean_2026"]), "x3": C(f, key, "V_mean"),
                    "ctrlp95": J(jf, ["finals", i, "H_ctrl_p95"]), "edge": J(jf, ["finals", i, "edge"])}
            # ctrl: H mean above the random-control 95th percentile -> encoded as difference
            locs["hm_minus_p95"] = CALC("sub", locs["net"], locs["ctrlp95"])
            add("research_btc_entry", tf, "DIR", "TRADE", f"{x.cfg} {x.set} (final)", "OOS", locs,
                ctrl={"field": "hm_minus_p95", "op": ">", "thr": 0}, verdict={"field": "edge", "op": "true"},
                note="final: H 2025-01..2026-09; x3 = V 2024")
        else:
            locs = {"net": C(f, key, "V_mean"), "n": C(f, key, "V_n"), "cost": K(FEE092, "fees.json futures taker"),
                    "net_sel": C(f, key, "D_mean"), "vse": C(f, key, "V_se")}
            locs["ci_lo"] = CALC("lin", locs["net"], locs["vse"], k=-1.96)
            add("research_btc_entry", tf, "DIR", "TRADE", f"{x.cfg} {x.set}", "OOS", locs,
                note="V = 2024 validation (selection used D 2020-23)")


def a_oracle():
    b = "logs/oracle_9m_2026/part_c/"
    for _, x in _csv(b + "c1_ranking.csv").iterrows():
        add("oracle_9m_2026", "1d", "DIR", "ACC", f"C1 {x.method}", "SEL",
            {"hit": C(b + "c1_ranking.csv", {"method": x.method}, "hit_rate"), "p_star": K(0.5, "day direction call: coin-flip line"),
             "n": C(b + "c1_ranking.csv", {"method": x.method}, "calls"), "bp": C(b + "c1_ranking.csv", {"method": x.method}, "binom_p")},
            ctrl={"field": "bp", "op": "<", "thr": 0.05}, acc_sym=True, note="2026 Jan-Sep, in-sample ranking")
    dc1 = _csv("logs/oracle_9m_2026/part_d/d_c1_context.csv")
    for _, x in dc1.iterrows():
        hc = "hit_rate"
        add("oracle_9m_2026", "1d", "DIR", "ACC", f"C1 {x[dc1.columns[0]]} (2020-25)", "OOS",
            {"hit": C("logs/oracle_9m_2026/part_d/d_c1_context.csv", {dc1.columns[0]: x[dc1.columns[0]]}, hc),
             "p_star": K(0.5, "coin-flip line")}, acc_sym=True, note="Part D context, 2020-2025")
    for _, x in _csv(b + "c2_ranking.csv").iterrows():
        add("oracle_9m_2026", "4h", "ENTRY", "ACC", f"C2 {x.trigger}", "SEL",
            {"hit": C(b + "c2_ranking.csv", {"trigger": x.trigger}, "p"), "p_star": K(0.546, "fees.json taker: +1% vs -1% break-even 54.6%"),
             "n": C(b + "c2_ranking.csv", {"trigger": x.trigger}, "events"), "wl": C(b + "c2_ranking.csv", {"trigger": x.trigger}, "wilson_lo")},
            ctrl={"field": "wl", "op": ">", "thr": 0.5}, acc_sym=True, note="2026; +1% before -1% within 4h")
    dc2 = _csv("logs/oracle_9m_2026/part_d/d_c2_context.csv")
    for _, x in dc2.iterrows():
        pc = "p" if "p" in dc2.columns else [c for c in dc2.columns if c.startswith("p")][0]
        add("oracle_9m_2026", "4h", "ENTRY", "ACC", f"C2 {x[dc2.columns[0]]} (2020-25)", "OOS",
            {"hit": C("logs/oracle_9m_2026/part_d/d_c2_context.csv", {dc2.columns[0]: x[dc2.columns[0]]}, pc),
             "p_star": K(0.546, "break-even 54.6%")}, acc_sym=True, note="Part D context")
    f = b + "c3_ranking.csv"
    for _, x in _csv(f).iterrows():
        cost = FEE092 if x["mode"] == "FUT" else 0.0017
        add("oracle_9m_2026", "4h", "DIR", "TRADE", f"C3 {x.cfg}", "SEL",
            {"net": C(f, {"cfg": x.cfg}, "mean_net_trade_pct", 0.01), "n": C(f, {"cfg": x.cfg}, "trades"),
             "cost": K(cost, "fees.json round trip of the config's mode"), "lb": C(f, {"cfg": x.cfg}, "lb95")},
            note="2026 in-sample ranking (6 entries/day)")
    f = b + "c3_exit_ranking.csv"
    for _, x in _csv(f).iterrows():
        add("oracle_9m_2026", "4h", "EXIT", "AGG", f"exit {x.gid}", "SEL",
            {"net": C(f, {"gid": x.gid}, "mean_of_cell_means_pct", 0.01), "cost": K(FEE092, "FUT cells")},
            note="mean of the 20 FUT cells using this exit")
    D = "logs/oracle_9m_2026/part_d/D_RESULTS.json"
    add("oracle_9m_2026", "4h", "DIR", "TRADE", "Part D lead FUT|RAND|R08|G12 (pre-declared)", "OOS",
        {"net": J(D, ["lead", "mean_net_trade_pct"], 0.01), "n": J(D, ["lead", "trades"]), "cost": K(FEE092, "FUT"),
         "ci_lo": J(D, ["lead", "lb95"], 0.01), "ps": J(D, ["lead", "passes"])}, verdict={"field": "ps", "op": "true"},
        note="2020-01..2025-12 (2,146 days), run once; ci_lo = per-day lb95")
    V = "logs/oracle_9m_2026/V1_RESULTS.json"
    for i, v in enumerate(_json(V)):
        add("oracle_9m_2026", "15m", "DIR", "TRADE", f"10-day hand formula H2'-c {v['variant']}", "OOS",
            {"net": J(V, [i, "mean_net_pct"], 0.01), "n": J(V, [i, "trades"]),
             "cost": K(0.0017 if v["variant"] == "V1-S" else FEE092, "fees.json: spot for V1-S, else futures taker"),
             "hit": J(V, [i, "win_rate"]), "p_star": J(V, [i, "breakeven_p"])},
            note="frozen formula from 10 manual days, tested on 272 new 2026 days; p_star = its own break-even win rate")


def a_green():
    f, dec, rc = "logs/green_candle_2026/metrics.csv", "logs/green_candle_2026/decision.json", "logs/green_candle_2026/random_control.csv"
    dj = _json(dec)
    for i, x in enumerate(dj):
        key = {"rule": x["rule"], "tf": x["tf"], "period": "P2025", "cost": "fut"}
        locs = {"net": C(f, key, "mean_net"), "n": C(f, key, "n"), "cost": K(FEE092, "fees.json futures taker"),
                "ci_lo": J(dec, [i, "P2025_ciB_lo"]), "x1": J(dec, [i, "FS26_mean"]),
                "net_sel": C(f, {"rule": x["rule"], "tf": x["tf"], "period": "JAN", "cost": "fut"}, "mean_net"),
                "rp": J(dec, [i, "P2025_rand_p"]), "cand": J(dec, [i, "candidate"])}
        add("green_candle_2026", x["tf"], "DIR", "TRADE", f"green {x['rule']}", "OOS", locs, side="long",
            ctrl={"field": "rp", "op": "<", "thr": 0.05}, verdict={"field": "cand", "op": "true"},
            note="P2025 = 2020-2025 pooled; x1 = Feb-Sep 2026; SEL = Jan 2026; CI = Bonferroni")


def a_micro():
    f = "logs/micro_momentum_2026/metrics.csv"
    d = _csv(f)
    for c in d[(d.cost == "fut") & (d.period == "VAL")].config:
        add("micro_momentum_2026", "1s-1m", "DIR", "TRADE", f"micro {c}", "OOS",
            {"net": C(f, {"config": c, "period": "VAL", "cost": "fut"}, "mean_net"),
             "n": C(f, {"config": c, "period": "VAL", "cost": "fut"}, "n"),
             "ci_lo": C(f, {"config": c, "period": "VAL", "cost": "fut"}, "ci95_lo"),
             "net_sel": C(f, {"config": c, "period": "DISC", "cost": "fut"}, "mean_net"),
             "cost": K(FEE092, "fees.json futures taker")}, side="long", note="VAL = Feb-May 2026; SEL = Jan 2026")


def a_turn():
    b = "logs/turn_detect_2026/"
    f = b + "T3_detectors_disc.csv"
    for _, x in _csv(f).iterrows():
        key = {"tf": x.tf, "det": x.det}
        add("turn_detect_2026", x.tf, "DIR", "TRADE", f"T3 {x.det}", "SEL",
            {"gross": C(f, key, "gross"), "net": C(f, key, "net_taker"), "n": C(f, key, "n_trades"),
             "cost": K(FEE092, "fees.json futures taker (= gross - net_taker)"), "z": C(f, key, "z")},
            ctrl={"field": "z", "op": ">", "thr": 3.5}, note="DISC Jan-May 2026; ctrl = z vs sign-null > 3.5 (protocol)")
    f, h = b + "T1_completion_disc.csv", b + "HOLD_T1_report.csv"
    for _, x in _csv(f).iterrows():
        key = {"theta": x.theta, "f": x.f}
        add("turn_detect_2026", "intraday-turn", "ENTRY", "TRADE", f"T1 enter at bounce theta={x.theta} f={x.f}", "SEL",
            {"gross": C(f, key, "gross"), "net": C(f, key, "net_taker"), "n": C(f, key, "n_trades"),
             "cost": K(FEE092, "taker"), "hit": C(f, key, "P_real"), "p_star": C(f, key, "p_star_taker"),
             "pn": C(f, key, "p_null"), "hold_p": C(h, key, "p_null")},
            ctrl={"field": "pn", "op": "<", "thr": 0.05},
            note="ACC_COVER not computed: asymmetric payoff (see CODE_NOTES)")
    f, h = b + "T2_auc_disc.csv", b + "HOLD_T2_feature_report.csv"
    hk = set(zip(_csv(h).theta, _csv(h).f, _csv(h).feature))
    for _, x in _csv(f).iterrows():
        key = {"theta": x.theta, "f": x.f, "feature": x.feature}
        locs = {"auc_raw": C(f, key, "auc"), "lo": C(f, key, "lo_bonf"), "hi": C(f, key, "hi_bonf"), "n": C(f, key, "n"),
                "real": C(f, key, "real")}
        # effect expressed as max(auc, 1-auc) with its matching bound
        locs["auc"] = CALC("flip", locs["auc_raw"])
        locs["auc_lo"] = CALC("efflo", locs["auc_raw"], locs["lo"], locs["hi"])
        if (x.theta, x.f, x.feature) in hk:
            locs["x_hold_auc"] = C(h, key, "auc_hold")
        add("turn_detect_2026", "intraday-turn", "ENTRY", "SKILL", f"T2 {x.feature} theta={x.theta} f={x.f}", "SEL", locs,
            skill={"field": "real", "op": "true"}, note="DISC AUC with Bonferroni (300 tests); HOLD AUC where carried")
    f = b + "T0_lag_cost_disc.csv"
    for _, x in _csv(f).iterrows():
        add("turn_detect_2026", "intraday-turn", "ENTRY", "TRADE", f"T0 follow confirmed turn theta={x.theta}", "SEL",
            {"gross": C(f, {"theta": x.theta}, "follow_gross"), "net": C(f, {"theta": x.theta}, "follow_net_taker"),
             "n": C(f, {"theta": x.theta}, "follow_trades"), "cost": K(FEE092, "taker")},
            note="entry after the turn is confirmed")
        phys("intraday-turn", f"share of leg gone at confirmation (theta {x.theta})", C(f, {"theta": x.theta}, "share_leg_gone_at_confirm_median"), "TURN T0")
        phys("intraday-turn", f"median confirmation lag minutes (theta {x.theta})", C(f, {"theta": x.theta}, "median_lag_min"), "TURN T0")


def a_np():
    b = "logs/research_nonprice/"
    tfm = {"1h": "1h", "4h": "4h", "24h": "1d"}
    v = _csv(b + "s1_V.csv")
    for _, x in v.iterrows():
        key = {"feature": x.feature, "h": x.h}
        add("research_nonprice", tfm[x.h], "DIR", "SKILL", f"NP1 IC {x.feature}", "OOS",
            {"t_ic": C(b + "s1_V.csv", key, "t_ic"), "t_ic_D": C(b + "s1_V.csv", key, "t_ic_D"), "conf": C(b + "s1_V.csv", key, "s1_confirmed")},
            skill={"field": "conf", "op": "true"}, note="IC; confirmed = |t| >= 3 in D and same sign |t| >= 2 in V 2024")
    f = b + "s2_summary.csv"
    s2 = _csv(f)
    for _, x in s2[s2.period == "V"].iterrows():
        key = {"feature": x.feature, "h": x.h, "period": "V"}
        add("research_nonprice", tfm[x.h], "DIR", "TRADE", f"NP S2 {x.feature}", "OOS",
            {"net": C(f, key, "mean_net_pct", 0.01), "n": C(f, key, "trades"), "cost": K(FEE092, "taker"),
             "net_sel": C(f, {"feature": x.feature, "h": x.h, "period": "D"}, "mean_net_pct", 0.01),
             "pass": C(f, key, "s2_pass")}, verdict={"field": "pass", "op": "true"}, note="V = 2024; funding inside net")
    for nm, f in (("NP2", b + "np2_dv_summary.csv"), ("NP3", b + "np3_dv_summary.csv")):
        d = _csv(f)
        for _, x in d[d.period == "V"].iterrows():
            tf = tfm[x.cfg.split("|")[0]]
            key = {"cfg": x.cfg, "period": "V"}
            locs = {"net": C(f, key, "mean_net_pct", 0.01), "n": C(f, key, "trades"),
                    "net_sel": C(f, {"cfg": x.cfg, "period": "D"}, "mean_net_pct", 0.01)}
            if nm == "NP3":
                locs["gross"] = C(f, key, "mean_gross_pct", 0.01)
                locs["cost"] = CALC("sub", locs["gross"], locs["net"])
            else:
                locs["cost"] = K(FEE092, "taker")
            add("research_nonprice", tf, "ENTRY" if nm == "NP3" else "DIR", "TRADE", f"{nm} {x.cfg}", "OOS", locs,
                note="V = 2024")
    f = b + "np4_summary.csv"
    for _, x in _csv(f).iterrows():
        add("research_nonprice", "1d", "DIR", "TRADE", f"NP4 premium-z {x.cfg}", "OOS",
            {"net": C(f, {"cfg": x.cfg}, "mean_net_pct", 0.01), "n": C(f, {"cfg": x.cfg}, "trades"), "cost": K(FEE092, "taker"),
             "ci_lo": C(f, {"cfg": x.cfg}, "lb_224", 0.01), "pass": C(f, {"cfg": x.cfg}, "passes")},
            verdict={"field": "pass", "op": "true"}, note="sealed holdout 2025-01..2026-09, opened once")


def a_root():
    f = "logs/research_root_cause/R3_accuracy.csv"
    d = _csv(f)
    for _, x in d[(d.period == "A") & (d.cost == "C2_fut_taker")].iterrows():
        key = {"h": x.h, "period": "A", "cost": "C2_fut_taker", "rule": x.rule}
        add("research_root_cause", x.h.replace("1d", "1d"), "DIR", "ACC", f"simple {x.rule} (10 coins)", "UNFIT",
            {"hit": C(f, key, "hit"), "p_star": C(f, key, "p_star"), "net": C(f, key, "mean_net"), "n": C(f, key, "n"),
             "x1": C(f, {**key, "period": "B"}, "mean_net")}, universe="10 big coins", acc_sym=True,
            note="A = 2020-01..2025-09, x1 = B (last year); taker cost of the study")
    f = "logs/research_root_cause/R2_random_entries.csv"
    d = _csv(f)
    for _, x in d[(d.period == "A") & (d.cost == "C2_fut_taker") & (d.exit == "end")].iterrows():
        phys(x.h, "random entry net per trade (10 coins, taker)", C(f, {"h": x.h, "period": "A", "cost": "C2_fut_taker", "exit": "end"}, "mean_net"), "root cause R2")
        phys(x.h, "share of moves beyond cost in OUR direction (random)", C(f, {"h": x.h, "period": "A", "cost": "C2_fut_taker", "exit": "end"}, "p_signed_gt_cost"), "root cause R2")


def a_phys():
    f = "logs/fee_hurdle_map/hurdle_map.csv"
    m = {"10s": "1s-1m", "30s": "1s-1m", "1m": "1s-1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d", "3d": "3d", "7d": "1w", "28d": "1M"}
    for _, x in _csv(f).iterrows():
        tf = m.get(x.horizon, x.horizon)
        phys(tf, f"E|r| at horizon {x.horizon}", C(f, {"horizon": x.horizon}, "E_abs_r"), "fee map")
        phys(tf, f"p* futures taker at horizon {x.horizon}", C(f, {"horizon": x.horizon}, "p_star_fut"), "fee map")
        phys(tf, f"p* maker at horizon {x.horizon}", C(f, {"horizon": x.horizon}, "p_star_maker"), "fee map")
    f = "logs/green_candle_2026/partA_jan2026.json"
    for tf in _json(f):
        phys(tf, "P(green|green) Jan 2026", J(f, [tf, "transition_probs", "P(G|G)"]), "green candle")
    f = "logs/turn_detect_2026/T4_summary_disc.csv"
    for _, x in _csv(f).iterrows():
        tf = "1s-1m" if x.unit == "sec" else {"1": "1s-1m", "5": "5m", "15": "15m", "30": "30m", "60": "1h", "240": "4h", "480": "8h", "1440": "1d"}.get(x.q, f"{x.q}min")
        phys(tf, f"variance ratio {x.unit} q={x.q} (rule {x.rule})", C(f, {"unit": x.unit, "q": x.q, "rule": x.rule}, "VR_phase0"), "TURN T4")


def a_probe():
    f = "logs/research_probe_scalein/S1_summary.csv"
    d = _csv(f)
    for _, x in d[d.cost == "base"].iterrows():
        key = {"tf": x.tf, "side": x.side, "cost": "base", "variant": x.variant}
        add("research_probe_scalein", x.tf, "DIR" if x.variant == "V0" else "ENTRY", "TRADE",
            f"ladder {'signal V0' if x.variant == 'V0' else 'probe/scale-in ' + x.variant}", "UNFIT",
            {"gross": C(f, key, "mean_gross_R"), "cost": C(f, key, "mean_cost_R"), "net": C(f, key, "mean_R"),
             "n": C(f, key, "entered"), "x1": C(f, key, "mean_R_P3")}, side=x.side, universe="10 coins", unit="R",
            note="R units (risk = stop distance); x1 = P3")


def a_ladder():
    f, fb = "logs/research_ladder_sessions/A5_double_top_bottom.csv", "logs/research_ladder_sessions/A5b_unconditional_labels.csv"
    ub = _csv(fb)
    for _, x in _csv(f).iterrows():
        base_col = "p_LL_among_lows" if x.pattern == "double_top" else "p_HH_among_highs"
        if x.tf not in set(ub.tf):
            continue
        add("research_ladder_sessions", x.tf, "DIR", "ACC", f"{x.pattern} -> {x.follow_label}", "UNFIT",
            {"hit": C(f, {"tf": x.tf, "pattern": x.pattern}, "p_follow"), "p_star": C(fb, {"tf": x.tf}, base_col),
             "n": C(f, {"tf": x.tf, "pattern": x.pattern}, "n"),
             "lift": CALC("sub", C(f, {"tf": x.tf, "pattern": x.pattern}, "p_follow"), C(fb, {"tf": x.tf}, base_col))},
            ctrl={"field": "lift", "op": ">", "thr": 0}, universe="10 coins",
            note="hit = next leg follows the pattern; p_star here = unconditional base rate (not a fee break-even)")
    f = "logs/research_ladder_sessions/A6_fibonacci_test.csv"
    for _, x in _csv(f).iterrows():
        add("research_ladder_sessions", x.tf, "ENTRY", "DESC", "Fibonacci retracement levels", "UNFIT",
            {"lift": C(f, {"tf": x.tf}, "fib_minus_control"), "lo": C(f, {"tf": x.tf}, "ci_lo")},
            skill={"field": "lo", "op": ">", "thr": 0}, universe="10 coins", note="share of turns at fib levels minus control")


def a_sr():
    f = "logs/research_sr_levels/results_table.csv"
    d = _csv(f)
    for _, x in d[d.part == "all"].iterrows():
        key = {"tf": x.tf, "side": x.side, "part": "all"}
        add("research_sr_levels", x.tf, "ENTRY", "ACC", f"buy/sell at swing {x.side} (bounce)", "UNFIT",
            {"hit": C(f, key, "bounce_real"), "p_star": C(f, key, "bounce_ctrl"), "n": C(f, key, "n_real"),
             "lo": C(f, key, "ci_low")}, ctrl={"field": "lo", "op": ">", "thr": 0}, universe="10 coins",
            note="p_star = bounce rate of control levels (not a fee break-even)")
    f = "logs/research_sr_levels/support_economics.csv"
    for _, x in _csv(f).iterrows():
        key = {"tf": x.tf, "side": x.side, "part": x.part}
        add("research_sr_levels", x.tf, "ENTRY", "TRADE", "support-bounce trade EV", "UNFIT",
            {"gross": C(f, key, "gross_ev_pct", 0.01), "net": C(f, key, "ev_minus_020", 0.01), "cost": K(0.0020, "study cost 0.20%")},
            universe="10 coins", note="study's own EV with 0.20% cost")


def a_extra():
    # swing anatomy: realizable follow of confirmed K=3 swings (PHYS, before costs; descriptive table)
    f = "logs/research_swing_anatomy/realizable_follow_zigzag_K3.txt"
    for _, x in _txt(f).iterrows():
        phys(x.tf, f"follow confirmed {x.direction}: mean realized ATR (before cost)", T(f, {"tf": x.tf, "direction": x.direction}, "realized_atr_mean"), "swing anatomy")
        phys(x.tf, f"follow confirmed {x.direction}: win share", T(f, {"tf": x.tf, "direction": x.direction}, "win_share"), "swing anatomy")
    # S/R + volume: forward return after a level break (all breaks), CI must exclude 0
    f = "logs/research_sr_volume/A4_fwd_after_break.csv"
    tfm = {"P1h": "1h", "P4h": "4h", "P1d": "1d", "P1D": "1d", "P1w": "1w", "P1W": "1w", "P1M": "1M"}
    for _, x in _csv(f).iterrows():
        key = {"family": x.family, "side": x.side}
        add("research_sr_volume", tfm.get(x.family, x.family), "DIR", "DESC", f"forward return after {x.side} break",
            "UNFIT", {"gross": C(f, key, "all_mean"), "lo": C(f, key, "all_ci_low"), "n": C(f, key, "all_n")},
            skill={"field": "lo", "op": ">", "thr": 0}, universe="10 coins", note="gross forward return after the break (no cost); skill = CI-low > 0")
    f = "logs/research_sr_volume/A2_volume_break.csv"
    for _, x in _csv(f).iterrows():
        key = {"family": x.family, "side": x.side}
        add("research_sr_volume", tfm.get(x.family, x.family), "ENTRY", "DESC", f"high- vs low-volume level ({x.side}): break-rate difference",
            "UNFIT", {"d": C(f, key, "diff"), "lo": C(f, key, "ci_low"), "hi": C(f, key, "ci_high")},
            skill={"field": "lo", "op": ">", "thr": 0}, universe="10 coins", note="negative = high-volume levels break LESS")
    # swing vs S/R: do S/R touches become swing turns more than control?
    f = "logs/research_swing_vs_sr/partB_table.csv"
    d = _csv(f)
    for _, x in d[d.comparison == "REAL_vs_CONTROL"].iterrows():
        key = {"swing_tf": x.swing_tf, "side": x.side, "comparison": "REAL_vs_CONTROL"}
        add("research_swing_vs_sr", x.swing_tf, "ENTRY", "ACC", f"S/R touch ({x.side}) -> becomes a swing turn",
            "UNFIT", {"hit": C(f, key, "mean_a"), "p_star": C(f, key, "mean_b"), "lo": C(f, key, "ci_low"), "n": C(f, key, "n_a")},
            ctrl={"field": "lo", "op": ">", "thr": 0}, universe="10 coins", note="p_star = control-level rate (not a fee break-even)")
    # S2 / S3: extra training data or features vs base brain (paired AUC difference)
    for folder, nm in (("research_s2_bear_training", "add 2017-19 bear data to training"), ("research_s3_futures_features", "add funding + basis features")):
        for brain, tf in (("D1", "1d"), ("R6", "4h"), ("R24", "1h")):
            f = f"logs/{folder}/claims_{brain}.json"
            add(folder, tf, "SELECT", "SKILL", f"{brain}: {nm}", "OOS",
                {"d": J(f, ["paired", "diff"]), "lo": J(f, ["paired", "ci_low"]), "vd": J(f, ["gates", "decision"])},
                skill={"field": "lo", "op": ">", "thr": 0}, verdict={"field": "vd", "op": "in", "thr": ["PASS"]},
                universe="many coins", note="paired AUC difference new - base; skill = CI-low > 0")
    # manual 10-day study: provenance row; its frozen formula is tested out-of-sample in the oracle V1 rows
    f = "logs/manual_day_study/day_10_check.txt"
    add("manual_day_study", "15m", "DIR", "DESC", "10-day hand analysis -> formula H2'-c (in-sample hypothesis)", "SEL",
        {}, note="no machine table of the in-sample trades; the formula's OOS test = oracle_9m_2026 'H2'-c' rows")


def a_skill1d():
    # (study folder, file, tf, component, method, role, locs-builder, rules)
    S = "logs/"
    def sk(folder, file, tf, comp, method, aucpath, lopath, ctrl_auc=None, role="OOS", note="", verdict=None, extra=None):
        f = S + folder + "/" + file
        locs = {"auc": J(f, aucpath), "auc_lo": J(f, lopath)}
        if ctrl_auc:
            locs["ctrl_auc"] = J(f, ctrl_auc)
        if extra:
            locs.update(extra)
        add(folder, tf, comp, "SKILL", method, role, locs, skill={"field": "auc_lo", "op": ">", "thr": 0.5},
            universe="many coins", note=note, verdict=verdict)

    def pf(folder, file, tf, comp, method, base, role="OOS", note="", verdict=None, extra=None, pct=True, ctrl=None):
        f = S + folder + "/" + file
        sc = 0.01 if pct else 1.0
        locs = {"net": J(f, base + ["cagr_pct" if pct else "cagr"], sc), "cagr": J(f, base + ["cagr_pct" if pct else "cagr"], sc),
                "maxdd": J(f, base + ["max_dd_pct" if pct else "mtm_dd"], sc), "calmar": J(f, base + ["calmar"])}
        if extra:
            locs.update(extra)
        add(folder, tf, comp, "PORT", method, role, locs, universe="many coins", note=note, verdict=verdict, ctrl=ctrl)

    v = lambda f, path, ok: ({"vd": J(S + f, path)}, {"field": "vd", "op": "in", "thr": ok})
    sk("strategy_1d_step8_ai", "claims.json", "1d", "ENTRY", "1D AI entry classifier", ["AI_entry_skill_members", "auc"], ["AI_entry_skill_members", "ci_low"])
    sk("strategy_1d_step8_ai", "claims.json", "1d", "EXIT", "1D AI exit classifier", ["AI_exit_skill_members", "auc"], ["AI_exit_skill_members", "ci_low"])
    sk("strategy_1d_step9_ai", "claims.json", "1d", "ENTRY", "1D AI entry + 1h flow", ["AI_entry_skill_members", "auc"], ["AI_entry_skill_members", "ci_low"])
    sk("strategy_1d_step9_ai", "claims.json", "1d", "EXIT", "1D AI exit + 1h flow", ["AI_exit_skill_members", "auc"], ["AI_exit_skill_members", "ci_low"])
    sk("strategy_1d_step10_ai", "claims.json", "1d", "SELECT", "path-2 h1 skill (1-day)", ["P2_h1_AI_skill", "auc"], ["P2_h1_AI_skill", "ci_low"], note="turnover kills it (report)")
    e, r = v("strategy_1d_step13_unseen/claims.json", ["gates", "decision"], ["PASS"])
    sk("strategy_1d_step13_unseen", "claims.json", "1d", "SELECT", "B1 1-day relative (535 unseen coins)", ["AI_B1_unseen", "auc"], ["AI_B1_unseen", "ci_low"], extra=e, verdict=r)
    pf("strategy_1d_step14_rule", "claims.json", "1d", "SELECT", "B1 trading rule on coin half B", ["B", "AI"], extra={"ci_lo": J(S + "strategy_1d_step14_rule/claims.json", ["B", "AI", "trade_ci_low_pct"], 0.01)})
    sk("strategy_1d_step15_slow", "claims.json", "1d", "SELECT", "R5 5-day relative brain", ["R5_AI_skill", "auc"], ["R5_AI_skill", "ci_low"])
    sk("strategy_1d_step15_slow", "claims.json", "1d", "SELECT", "R10 10-day relative brain", ["R10_AI_skill", "auc"], ["R10_AI_skill", "ci_low"])
    pf("strategy_1d_step15_slow", "claims.json", "1d", "SELECT", "R5 long-only portfolio", ["R5_portfolio", "AI"], ctrl={"field": "cc", "op": ">", "thr": 0},
       extra={"cc": CALC("sub", J(S + "strategy_1d_step15_slow/claims.json", ["R5_portfolio", "AI", "calmar"]), J(S + "strategy_1d_step15_slow/claims.json", ["R5_portfolio", "CONTROL", "calmar"])), "ci_lo": J(S + "strategy_1d_step15_slow/claims.json", ["R5_portfolio", "AI", "trade_ci_low_pct"], 0.01)})
    sk("strategy_1d_step17_18", "claims.json", "1d", "RISK", "market brain (when to be out)", ["market_AI_skill", "auc"], ["market_AI_skill", "ci_low"])
    sk("strategy_1d_step17_18", "claims.json", "1d", "SELECT", "veto brain (where not to trade)", ["veto_AI_skill", "auc"], ["veto_AI_skill", "ci_low"])
    sk("strategy_1d_step19_largecap", "claims.json", "1d", "SELECT", "R5 in top-20 liquid coins (skill)", ["AI_skill_U", "auc"], ["AI_skill_U", "ci_low"])
    pf("strategy_1d_step19_largecap", "claims.json", "1d", "SELECT", "R5 top-20 portfolio (80% invested)", ["portfolio", "AI"],
       ctrl={"field": "cc", "op": ">", "thr": 0},
       extra={"cc": CALC("sub", J(S + "strategy_1d_step19_largecap/claims.json", ["portfolio", "AI", "calmar"]), J(S + "strategy_1d_step19_largecap/claims.json", ["portfolio", "CONTROL", "calmar"])),"ci_lo": J(S + "strategy_1d_step19_largecap/claims.json", ["portfolio", "AI", "trade_ci_low_pct"], 0.01),
              "x1": J(S + "strategy_1d_step22_pre2020/claims.json", ["portfolio", "AI_80_none", "cagr_pct"], 0.01)},
       note="x1 = the same frozen brain on 2018-19 (Step 22)")
    for i, nm in ((0, "M_AI3 (1D+4H+1h sleeves) f=1.0"), (12, "M_AI3 f=0.5 (Step 27 pick)"), (2, "D1 sleeve alone f=1.0")):
        f27 = S + "strategy_1d_step27_combine/claims.json"
        add("strategy_1d_step27_combine", "1d", "SELECT", "PORT", nm, "OOS",
            {"net": J(f27, ["decision_table", i, "MAIN_cagr_pct"], 0.01), "cagr": J(f27, ["decision_table", i, "MAIN_cagr_pct"], 0.01),
             "calmar": J(f27, ["decision_table", i, "MAIN_calmar"]), "maxdd": J(f27, ["decision_table", i, "MAIN_max_dd_pct"], 0.01),
             "x1": J(f27, ["decision_table", i, "PRE_cagr_pct"], 0.01)}, universe="many coins",
            note="long-only sleeves; MAIN 2021-26; x1 = 2018-19")
    sk("strategy_1d_step20_largecap_gate", "claims.json", "1d", "RISK", "large-cap market gate", ["AI_skill", "auc"], ["AI_skill", "ci_low"])
    sk("strategy_1d_step21_crash", "claims.json", "1d", "RISK", "crash brain", ["AI_skill99", "auc"], ["AI_skill99", "ci_low"])
    sk("strategy_1d_step22_pre2020", "claims.json", "1d", "SELECT", "frozen R5 brain on 2018-19 (skill)", ["AI_skill_label_r5", "auc"], ["AI_skill_label_r5", "ci_low"])
    e, r = v("strategy_1d_step23_4h/claims.json", ["gates", "decision"], ["PASS_R6"])
    sk("strategy_1d_step23_4h", "claims.json", "4h", "SELECT", "R6 4H relative brain (skill)", ["R6_AI_skill", "auc"], ["R6_AI_skill", "ci_low"], extra={**e, "x_pre_auc": J(S + "strategy_1d_step23_4h/claims.json", ["R6_pre2020_skill", "auc"])}, verdict=r)
    pf("strategy_1d_step23_4h", "claims.json", "4h", "SELECT", "R6 4H portfolio", ["portfolio", "R6_AI"],
       extra={**e, "ci_lo": J(S + "strategy_1d_step23_4h/claims.json", ["portfolio", "R6_AI", "trade_ci_low_pct"], 0.01),
              "x1": J(S + "strategy_1d_step27_combine/claims.json", ["decision_table", 3, "PRE_cagr_pct"], 0.01)}, verdict=r,
       note="x1 = the same 4H sleeve on 2018-19 (Step 27 decision_table H4, f=1.0)")
    e, r = v("strategy_1d_step24_1h/claims.json", ["gates", "decision"], ["PASS_R24"])
    sk("strategy_1d_step24_1h", "claims.json", "1h", "SELECT", "R24 1h relative brain (skill)", ["R24_AI_skill", "auc"], ["R24_AI_skill", "ci_low"], extra=e, verdict=r)
    pf("strategy_1d_step24_1h", "claims.json", "1h", "SELECT", "R24 1h portfolio", ["portfolio", "R24_AI"], ctrl={"field": "cc", "op": ">", "thr": 0},
       note="x1 = the same 1h sleeve on 2018-19 (Step 27 decision_table H1, f=1.0)",
       extra={**e, "x1": J(S + "strategy_1d_step27_combine/claims.json", ["decision_table", 4, "PRE_cagr_pct"], 0.01),
              "cc": CALC("sub", J(S + "strategy_1d_step24_1h/claims.json", ["portfolio", "R24_AI", "calmar"]), J(S + "strategy_1d_step24_1h/claims.json", ["portfolio", "R24_CONTROL", "calmar"])), "ci_lo": J(S + "strategy_1d_step24_1h/claims.json", ["portfolio", "R24_AI", "trade_ci_low_pct"], 0.01)}, verdict=r)
    sk("strategy_1d_step24_1h", "claims.json", "1h", "SELECT", "R4 4-hour-horizon brain (skill)", ["R4_AI_skill", "auc"], ["R4_AI_skill", "ci_low"])
    pf("strategy_1d_step24_1h", "claims.json", "1h", "SELECT", "R4 4-hour-horizon portfolio", ["portfolio", "R4_AI"], extra={"ci_lo": J(S + "strategy_1d_step24_1h/claims.json", ["portfolio", "R4_AI", "trade_ci_low_pct"], 0.01)})
    sk("strategy_1d_step25_hf", "claims.json", "1h", "SELECT", "R24 + 15m/5m features (skill)", ["R24_HF_skill", "auc"], ["R24_HF_skill", "ci_low"])
    sk("strategy_1d_step26_exit", "claims.json", "1h", "EXIT", "exit brain P(fall>5% in 24h)", ["AI_skill99", "auc"], ["AI_skill99", "ci_low"], note="detects volatility, not direction; money FAIL")
    sk("strategy_1d_step29_srv", "claims.json", "1h", "SELECT", "R24 + S/R + volume features (skill)", ["R24_SRV_skill", "auc"], ["R24_SRV_skill", "ci_low"])
    sk("research_swing_ai_phase2", "claims.json", "4h", "ENTRY", "swing-rally AI 4h", ["per_tf", "4h", "auc", "auc"], ["per_tf", "4h", "auc", "ci_low"])
    sk("research_swing_ai_phase2", "claims.json", "8h", "ENTRY", "swing-rally AI 8h", ["per_tf", "8h", "auc", "auc"], ["per_tf", "8h", "auc", "ci_low"])
    sk("research_swing_ai_phase2", "claims.json", "12h", "ENTRY", "swing-rally AI 12h", ["per_tf", "12h", "auc", "auc"], ["per_tf", "12h", "auc", "ci_low"])
    sk("research_swing_ai_phase2", "claims.json", "1d", "ENTRY", "swing-rally AI 1D", ["per_tf", "1D", "auc", "auc"], ["per_tf", "1D", "auc", "ci_low"])
    f = S + "strategy_1d_step30_breakout/claims.json"
    add("strategy_1d_step30_breakout", "1d", "DIR", "TRADE", "1D resistance breakout + regime ON", "OOS",
        {"net": J(f, ["PRE", "ON", "net", "mean_pct"], 0.01), "n": J(f, ["PRE", "ON", "net", "n"]), "ci_lo": J(f, ["PRE", "ON", "net", "ci_low_pct"], 0.01),
         "net_sel": J(f, ["MAIN", "ON", "net", "mean_pct"], 0.01), "exlo": J(f, ["MAIN", "ON", "excess", "ci_low_pct"], 0.01)},
        universe="many coins", ctrl={"field": "exlo", "op": ">", "thr": 0}, note="SEL = 2021-26 (MAIN); OOS = 2018-19 (PRE)")
    f = S + "strategy_1d_step28_volsize/claims.json"
    add("strategy_1d_step28_volsize", "1d", "RISK", "PORT", "volatility sizing", "OOS",
        {"calmar": J(f, ["MAIN", "VOL", "calmar"]), "net": CALC("sub", J(f, ["MAIN", "VOL", "calmar"]), J(f, ["MAIN", "FIXED_050", "calmar"])),
         "dcagr": CALC("sub", J(f, ["MAIN", "VOL", "cagr_pct"], 0.01), J(f, ["MAIN", "FIXED_050", "cagr_pct"], 0.01)),
         "cagr": J(f, ["MAIN", "VOL", "cagr_pct"], 0.01), "maxdd": J(f, ["MAIN", "VOL", "max_dd_pct"], 0.01),
         "p95": J(f, ["MAIN", "SHUFFLED", "calmar_p95"]), "vd": J(f, ["gates", "decision"])},
        universe="many coins", verdict={"field": "vd", "op": "in", "thr": ["PASS"]}, note="modifier: net = Calmar change vs fixed 50% exposure")
    for nm, base, comp in (("F2 long-short (AI top long spot / bottom short perp)", ["MAIN", "AI_LS", "mix"], "SELECT"),):
        f = S + "strategy_f2_longshort/claims.json"
        add("strategy_f2_longshort", "1d", comp, "PORT", nm, "OOS",
            {"net": J(f, base + ["cagr_pct"], 0.01), "calmar": J(f, base + ["calmar"]), "maxdd": J(f, base + ["max_dd_pct"], 0.01),
             "vd": J(f, ["gates", "decision"])},
            universe="many coins", verdict={"field": "vd", "op": "in", "thr": ["PASS"]},
            note="2021-01..2026-09 walk-forward brains; rule chosen on this data (P3 inside)")
    f = S + "strategy_f7_risk/claims.json"
    add("strategy_f7_risk", "1d", "RISK", "PORT", "F7 stops x1.5 + 30d cooldown (RS)", "OOS",
        {"net": CALC("sub", J(f, ["MAIN", "RS", "mix", "calmar"]), J(f, ["MAIN", "OFF_LS", "mix", "calmar"])),
         "dcagr": CALC("sub", J(f, ["MAIN", "RS", "mix", "cagr_pct"], 0.01), J(f, ["MAIN", "OFF_LS", "mix", "cagr_pct"], 0.01)),
         "cagr": J(f, ["MAIN", "RS", "mix", "cagr_pct"], 0.01), "calmar": J(f, ["MAIN", "RS", "mix", "calmar"]), "maxdd": J(f, ["MAIN", "RS", "mix", "max_dd_pct"], 0.01),
         "x1": J(f, ["PRE", "RS", "mix", "cagr_pct"], 0.01), "x2": J(S + "research_1d_true_fee/TRUE_FEE_1D_RESULTS.json", ["R0_RS", "M_AI3", "p3_2025_10_on"]),
         "c_ctrl": J(f, ["MAIN", "RS_CONTROL", "mix", "calmar"]), "vd": J(f, ["gates", "decision"])},
        universe="many coins", verdict={"field": "vd", "op": "in", "thr": ["PASS"]},
        ctrl={"field": "c_ctrl", "op": "<", "thr": 0}, note="modifier of F2 LS: net = Calmar change; x1 = 2018-19 RS CAGR; x2 = P3 return; ctrl = shuffled-brain control Calmar < 0")
    f = S + "research_1d_true_fee/TRUE_FEE_1D_RESULTS.json"
    add("research_1d_true_fee", "1d", "SELECT", "PORT", "F7 RS at true fee (M_AI3 mix)", "OOS",
        {"net": J(f, ["R1_RS", "M_AI3", "cagr"]), "maxdd": J(f, ["R1_RS", "M_AI3", "maxdd"]), "calmar": J(f, ["R1_RS", "M_AI3", "calmar"]),
         "x1": J(f, ["R1_RS", "M_AI3", "p3_2025_10_on"])}, universe="many coins", note="re-run with fees.json costs; in-sample rule")
    f = S + "research_overfit_s1/claims.json"
    add("research_overfit_s1", "1d", "SELECT", "DESC", "overfit audit of the 1D research (PBO / DSR)", "SEL",
        {"pbo": J(f, ["PBO", "pbo"]), "dsr": J(f, ["DSR_M_AI3_f50", "N_series", "dsr"])}, universe="many coins",
        note="PBO 0.65 = 65% chance the chosen config is overfit")


def a_r1():
    S = "logs/research_r1/"
    for exp, key, comp, nm in (("E1", ["results", "E1a", "result", "mix"], "RISK", "E1a BTC hedge of the short book"),
                               ("E1", ["results", "E1b", "result", "mix"], "RISK", "E1b BTC hedge (full)"),
                               ("E2", ["results", "E2", "result", "mix"], "SELECT", "E2 short safety filters"),
                               ("E3", ["results", "E3b", "mix"], "SELECT", "E3 listing-age rule instead of AI shorts"),
                               ("E4", ["results", "E4", "result", "mix"], "RISK", "E4 inverse-vol weights + 30% cap"),
                               ("N1", ["results", "N1a", "result", "mix"], "SELECT", "N1a MAX/lottery filter"),
                               ("N1", ["results", "N1b", "result", "mix"], "SELECT", "N1b MAX/lottery filter"),
                               ("E11", ["results", "E11", "result", "mix"], "ENTRY", "E11 longs on USDT-M perps instead of spot")):
        f = S + f"claims_{exp}.json"
        F7 = "logs/strategy_f7_risk/claims.json"
        add("research_r1", "1d", comp, "PORT", nm, "OOS",
            {"net": CALC("sub", J(f, key + ["calmar"]), J(F7, ["MAIN", "RS", "mix", "calmar"])),
             "dcagr": CALC("sub", J(f, key + ["cagr_pct"], 0.01), J(F7, ["MAIN", "RS", "mix", "cagr_pct"], 0.01)),
             "cagr": J(f, key + ["cagr_pct"], 0.01), "calmar": J(f, key + ["calmar"]), "maxdd": J(f, key + ["max_dd_pct"], 0.01)},
            universe="many coins", note="modifier: net = Calmar change vs F7 RS base; dcagr = CAGR change; only E11 PASSED its study")


def a_r2():
    f = "logs/r2_4h_a1/correction/A1c_gate.csv"
    for _, x in _csv(f).iterrows():
        key = {"signal": x.signal, "side": x.side}
        add("r2_4h_a1", "4h", "DIR", "TRADE", f"A1 rule signal {x.signal}", "OOS",
            {"gross": C(f, key, "mean_gross"), "net": C(f, key, "mean_net"), "cost": CALC("sub", C(f, key, "mean_gross"), C(f, key, "mean_net")),
             "ci_lo": C(f, key, "ci_lo"), "n": C(f, key, "n_dev"), "x1": C(f, key, "net_P3"), "ps": C(f, key, "PASS")},
            side=x.side, universe="10 coins", unit="R", verdict={"field": "ps", "op": "true"},
            note="R units; corrected A1 (real-time pivots); dev 2020-02..2025-09 = first test of pre-defined signals; x1 = P3; no random control")
    for folder, fn, nm in (("r2_4h_a3", "claims_a3.json", "A3 AI take/skip on 4h signals"), ("r2_4h_t14", "claims_t14.json", "T14 AI take/skip on 120 coins")):
        f = f"logs/{folder}/{fn}"
        add(folder, "4h", "ENTRY", "SKILL", nm, "SEL",
            {"auc": J(f, ["auc_dev"]), "auc_lo": CALC("add", J(f, ["auc_ci_minus_half", 0]), k=0.5),
             "x1": J(f, ["p3", "ai_calmar"]), "vd": J(f, ["verdict"])},
            skill={"field": "auc_lo", "op": ">", "thr": 0.5}, verdict={"field": "vd", "op": "startswith", "thr": "PASS"}, universe="coins")
    f = "logs/r2_4h_a4/claims_a4.json"
    add("r2_4h_a4", "4h", "EXIT", "PORT", "A4 S-LAD long, exit 3 ATR / 60 bars", "OOS",
        {"calmar": J(f, ["final", "calmar"]), "net": J(f, ["final", "cagr"]), "maxdd": J(f, ["final", "mtm_dd"]),
         "pbo": J(f, ["pbo"]), "vd": J(f, ["verdict"])}, universe="10 coins",
        verdict={"field": "vd", "op": "startswith", "thr": "PASS"}, note="exit grid PBO 0.84 -> exit tuning = noise")
    add("r2_4h_a4", "4h", "ENTRY", "TRADE", "A4 maker entry (limit) on S-LAD", "OOS",
        {"net": J(f, ["maker_net_filled"]), "fill": J(f, ["maker_fill_rate"]), "x1": J(f, ["maker_net_unfilled"])},
        universe="10 coins", unit="R", note="R units; adopted by a hair")
    f = "logs/research_master_audit/claims_master_audit.json"
    add("research_master_audit", "4h", "DIR", "PORT", "rule signals 4h+1D, 0.5% risk, K=6", "SEL",
        {"calmar": J(f, ["G1_f0.005_K6", "calmar"]), "net": J(f, ["G1_f0.005_K6", "calmar"]), "maxdd": J(f, ["G1_f0.005_K6", "maxdd"])},
        universe="10 coins", note="net = Calmar (sign) on the audit window; signals were defined earlier on the same data")
    add("research_master_audit", "4h", "RISK", "PORT", "loss rule L1 (DD halving / pause)", "SEL",
        {"calmar": J(f, ["L1", "calmar"]), "net": CALC("sub", J(f, ["L1", "calmar"]), J(f, ["G1_f0.005_K6", "calmar"])),
         "p90": J(f, ["random_pause_calmar_p90"])}, universe="10 coins",
        note="random-pause Calmar p90 0.92 > L1 0.52")


def a_n():
    f = "logs/research_n1_portfolio/claims_n1.json"
    add("research_n1_portfolio", "4h", "DIR", "PORT", "N1 multi-TF trend sleeves (4h-1D)", "OOS",
        {"net": J(f, ["g7", "cagr"]), "cagr": J(f, ["g7", "cagr"]), "calmar": J(f, ["g7", "calmar"]), "maxdd": J(f, ["g7", "mtm_dd"]),
         "net_sel": J(f, ["final_dev", "cagr"]), "x1": J(f, ["calmar_windows", "P3"]), "vd": J(f, ["verdict"]),
         "c_minus_rp": CALC("sub", J(f, ["final_dev", "calmar"]), J(f, ["random_p95"]))},
        universe="10 coins", verdict={"field": "vd", "op": "startswith", "thr": "N1 PASS"},
        ctrl={"field": "c_minus_rp", "op": ">", "thr": 0},
        note="chosen on dev 2021-01..2025-09; OOS = 2018-19 (G7); x1 = P3 Calmar (sign); ctrl = dev Calmar above random-entry p95")
    for nm, folder, fn, cfg, comp, vpath, vthr in (
            ("N2 regime gate R1", "research_n2_regime", "claims_n2.json", "R1", "RISK", ["verdict"], "N2 PASS"),
            ("N3 X1 maker entry", "research_n3_execution", "claims_n3.json", "X1", "ENTRY", ["results", "X1", "passed"], None),
            ("N3 X2 spot/perp routing", "research_n3_execution", "claims_n3.json", "X2", "ENTRY", ["results", "X2", "passed"], None)):
        f = f"logs/{folder}/{fn}"
        add(folder, "4h", comp, "PORT", nm, "OOS",
            {"net": CALC("sub", J(f, ["calmar", f"{cfg}|P3"]), J(f, ["calmar", "base|P3"])), "calmar": J(f, ["calmar", f"{cfg}|P3"]),
             "net_sel": CALC("sub", J(f, ["calmar", f"{cfg}|dev"]), J(f, ["calmar", "base|dev"])),
             "vd": J(f, vpath)}, universe="10 coins",
            verdict={"field": "vd", "op": "startswith", "thr": vthr} if vthr else {"field": "vd", "op": "true"},
            note="modifier: net = Calmar change vs N1 base in P3 (report-only); net_sel = change on dev")
    f = "logs/research_n5_ai/claims_n5.json"
    add("research_n5_ai", "4h", "ENTRY", "DESC", "N5 AI meta-label (skip trades)", "OOS", {"vd": J(f, ["verdict"])},
        universe="10 coins", verdict={"field": "vd", "op": "startswith", "thr": "N5 PASS"})
    f = "logs/research_n6_safety_sizing/claims_n6.json"
    add("research_n6_safety_sizing", "4h", "RISK", "PORT", "T20 AI sizing", "OOS",
        {"net": CALC("sub", J(f, ["t20", "calmar_ai", "P3"]), J(f, ["t20", "calmar_base", "P3"])), "calmar": J(f, ["t20", "calmar_ai", "P3"]),
         "net_sel": CALC("sub", J(f, ["t20", "calmar_ai", "dev"]), J(f, ["t20", "calmar_base", "dev"])),
         "vd": J(f, ["t20", "verdict"])}, universe="10 coins", verdict={"field": "vd", "op": "startswith", "thr": "T20 PASS"},
        note="modifier: net = Calmar change vs base in P3; net_sel on dev")
    add("research_n6_safety_sizing", "4h", "RISK", "DESC", "T19 per-coin cap 0.20 (S2)", "OOS", {"vd": J(f, ["t19", "verdict"])},
        universe="10 coins", verdict={"field": "vd", "op": "startswith", "thr": "T19 safety adopted"})


def a_eco():
    f = "logs/eco/claims_eco_e2.json"
    for nm, k, tf, comp, uni in (("ECO-W2: 1D LS_RS + N1, inverse-vol (live)", "ECO-W2", "1d", "RISK", "many coins"),
                                 ("1D alone (LS_RS) inside ECO", "1D_alone", "1d", "SELECT", "many coins"),
                                 ("N1 alone inside ECO", "N1_alone", "4h", "DIR", "10 coins")):
        locs = {"net": J(f, ["results", f"P3|{k}", "cagr"]), "cagr": J(f, ["results", f"P3|{k}", "cagr"]),
                "calmar": J(f, ["results", f"P3|{k}", "calmar"]), "maxdd": J(f, ["results", f"P3|{k}", "mtm_dd"]),
                "net_sel": J(f, ["results", f"dev|{k}", "cagr"])}
        ver = None
        if k == "ECO-W2":
            locs["vd"] = J(f, ["verdict"])
            ver = {"field": "vd", "op": "startswith", "thr": "E-2: ECO-W2 adopted"}
        add("eco", tf, comp, "PORT", nm, "OOS", locs, universe=uni, verdict=ver,
            note="OOS = P3 2025-10..2026-09 (report-only); SEL = dev 2021-01..2025-09 where ECO was chosen")
    f = "logs/eco/claims_eco_t4.json"
    add("eco", "4h", "EXIT", "PORT", "ECO-T4 profit lock (break-even after +3 ATR)", "OOS",
        {"net": CALC("sub", J(f, ["results", "P3|T4"]), J(f, ["results", "P3|base"])), "calmar": J(f, ["results", "P3|T4"]),
         "net_sel": CALC("sub", J(f, ["results", "dev|T4"]), J(f, ["results", "dev|base"])), "vd": J(f, ["verdict"])}, universe="10 coins",
        verdict={"field": "vd", "op": "startswith", "thr": "ECO-T4 PASS"}, note="modifier: net = Calmar change vs base in P3; net_sel = change on dev (4.16 -> 3.62)")


def a_risk():
    f = "logs/drawdown_ddx/ledger.csv"
    d = _csv(f)
    for _, x in d[d.id == "A06"].iterrows():
        add("drawdown_ddx", "1d", "RISK", "DESC", f"exposure {x['item']} (D1 sleeve)", "OOS",
            {"maxdd": C(f, {"id": "A06", "item": x["item"], "role": x["role"]}, "recomputed_dd_pct", 0.01)}, universe="many coins",
            note="lower exposure cuts DD about proportionally (and profit)")


def a_spot():
    f = "logs/research_spot_sleeve/SPOT_SLEEVE_RESULTS.json"
    for s in ("S1", "S2", "S3", "S4", "S5", "S6"):
        locs = {"net": CALC("sub", J(f, ["base_holdout", s, "sharpe"]), J(f, ["base_holdout", "B0", "sharpe"])),
                "cagr": J(f, ["base_holdout", s, "cagr"]), "maxdd": J(f, ["base_holdout", s, "maxdd"]),
                "net_sel": CALC("sub", J(f, ["base_dev", s, "sharpe"]), J(f, ["base_dev", "B0", "sharpe"])),
                "cand": J(f, ["gates", s, "candidate"])}
        if s != "S5":
            locs["x1"] = CALC("sub", J(f, ["base_P0", s, "sharpe"]), J(f, ["base_P0", "B0", "sharpe"]))
        ctrl = None
        if s in _json(f)["controls_full"]:
            locs["pct"] = J(f, ["controls_full", s, "btc_leg_percentile" if s == "S2" else "percentile"])
            ctrl = {"field": "pct", "op": ">", "thr": 0.9}
        add("research_spot_sleeve", "1d", "DIR", "PORT", f"spot timing {s}", "OOS", locs, side="long",
            universe="BTC" if s in ("S1", "S3", "S4", "S6") else "coins", ctrl=ctrl,
            verdict={"field": "cand", "op": "true"}, note="vs BTC hold: net = Sharpe(rule) - Sharpe(BTC hold), holdout 2024-01..2026-09; x1 = same in 2018-19; ctrl = random-timing percentile > 0.90")
    f = "logs/research_spot_dca/SPOT_DCA_RESULTS.json"
    add("research_spot_dca", "1d", "ENTRY", "PORT", "spot DCA, averaging down, TP 10%, no stop", "OOS",
        {"net": J(f, ["P_holdout", "cagr"]), "maxdd": J(f, ["P_holdout", "maxdd"]), "net_sel": J(f, ["P_dev", "cagr"])},
        side="long", universe="679 coins")


def a_emo():
    f = "logs/emotion/EMO1_DEV_REPORT.json"
    add("emotion", "1d", "SELECT", "DESC", "EMO-1 candle-emotion cross-section", "SEL",
        {"sh_lo": J(f, ["sharpe_ci95", 0]), "ap": J(f, ["all_pass"])}, universe="25 coins",
        verdict={"field": "ap", "op": "true"}, note="dev Sharpe CI fully negative; closed FAIL")


# ---------------------------------------------------------------- run
def main():
    for fn in (a_tfx, a_bench, a_btcentry, a_oracle, a_green, a_micro, a_turn, a_np, a_root, a_phys, a_probe,
               a_ladder, a_sr, a_extra, a_skill1d, a_r1, a_r2, a_n, a_eco, a_risk, a_spot, a_emo):
        n0 = len(ROWS)
        fn()
        print(f"{fn.__name__}: {len(ROWS) - n0} rows")
    df = pd.DataFrame(ROWS)
    df.insert(0, "row_id", [f"R{i:05d}" for i in range(len(df))])
    df.to_csv(OUT / "atlas_rows.csv", index=False)
    rank(df).to_csv(OUT / "atlas_ranked.csv", index=False)
    chance(df).to_csv(OUT / "atlas_chance.csv", index=False)
    pd.DataFrame(PHYS).to_csv(OUT / "atlas_phys.csv", index=False)
    pd.DataFrame([{"path": f, "sha256": hashlib.sha256((PROJ / f).read_bytes()).hexdigest()} for f in sorted(USED)]).to_csv(OUT / "atlas_sources.csv", index=False)
    print("rows", len(df), "tiers", df.tier.value_counts().to_dict())


TIER_ORDER = {"E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5}


def score(r):
    if r["mtype"] in ("TRADE", "AGG"):
        return r["FCR092"] if r["unit"] == "frac" and pd.notna(r["FCR092"]) else r["FCR"]
    if r["mtype"] == "SKILL":
        return r["auc_lo"]
    if r["mtype"] == "ACC":
        return r["ACC_COVER"] if pd.notna(r["ACC_COVER"]) else (r["hit"] - r["p_star"] if pd.notna(r["hit"]) and pd.notna(r["p_star"]) else None)
    if r["mtype"] == "PORT":
        return r["calmar"]
    return None


def rank(df):
    d = df.copy()
    d["score"] = d.apply(score, axis=1)
    d["tier_n"] = d.tier.map(TIER_ORDER)
    d["n_sort"] = d.n.fillna(0)
    d = d.sort_values(["tf", "component", "mtype", "tier_n", "score", "n_sort"], ascending=[True, True, True, True, False, False], na_position="last")
    d["rank"] = d.groupby(["tf", "component", "mtype"]).cumcount() + 1
    return d.drop(columns=["tier_n", "n_sort"])


def chance(df):
    g = df[(df.mtype == "TRADE") & (df.role == "OOS") & df.net.notna()]
    rows = []
    for (s, tf), x in g.groupby(["study", "tf"]):
        if len(x) < 5:
            continue
        rows.append(dict(study=s, tf=tf, configs=len(x), share_oos_net_pos=float((x.net > 0).mean()),
                         share_oos_gross_pos=float((x.gross.dropna() > 0).mean()) if x.gross.notna().any() else None,
                         best_FCR092=float(x.FCR092.max()) if x.FCR092.notna().any() else None,
                         median_FCR092=float(x.FCR092.median()) if x.FCR092.notna().any() else None))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
